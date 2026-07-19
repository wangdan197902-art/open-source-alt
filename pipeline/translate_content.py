#!/usr/bin/env python3
"""translate_content.py - 多语言翻译

功能：
- 调用AIClient将商业软件描述翻译到20语种（zh/ja/ko/es/de/fr/pt/it/ru/ar/nl/pl/tr/id/vi/th/hi/bn/ms/uk）
- 输出到 data/translation/{software}-{lang}.json
- 5个商业软件 × 20语种 = 100条翻译记录

用法：
  python3 -m pipeline.translate_content
  python3 -m pipeline.translate_content --provider openai
  python3 -m pipeline.translate_content --provider gemini --data-dir data
"""
import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.ai_client import AIClient, QuotaExceededError  # noqa: E402

SCHEMA_VERSION = "1.0.0"
# 目标语言列表（不含 en 源语言；en 作为源语言单独处理）
LANGUAGES = [
    "zh", "ja", "ko", "es",
    "de", "fr", "pt", "it", "ru", "ar",
    "nl", "pl", "tr", "id", "vi", "th",
    "hi", "bn", "ms", "uk",
]
LANGUAGE_NAMES = {
    "zh": "简体中文",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français",
    "pt": "Português",
    "it": "Italiano",
    "ru": "Русский",
    "ar": "العربية",
    "nl": "Nederlands",
    "pl": "Polski",
    "tr": "Türkçe",
    "id": "Bahasa Indonesia",
    "vi": "Tiếng Việt",
    "th": "ไทย",
    "hi": "हिन्दी",
    "bn": "বাংলা",
    "ms": "Bahasa Melayu",
    "uk": "Українська",
}

# 默认源文本（每个商业软件的简短描述，作为翻译输入）
DEFAULT_SOURCE_TEXTS = {
    "photoshop": "Adobe Photoshop is a professional image editing software developed by Adobe, widely used for photo retouching, digital art, and graphic design.",
    "notion": "Notion is an all-in-one workspace that combines notes, databases, collaboration, and project management for teams and individuals.",
    "figma": "Figma is a collaborative interface design tool that enables real-time teamwork on design projects in the browser.",
    "slack": "Slack is a team communication platform that organizes conversations into channels, integrates with workplace tools, and supports file sharing.",
    "zoom": "Zoom is a video conferencing platform offering meetings, webinars, and online collaboration features for businesses and individuals.",
}


def load_source_texts(data_dir: Path) -> Dict[str, str]:
    """加载每个商业软件的源描述文本。

    优先从data/proprietary/{id}.json的metadata.description读取，
    若不存在则使用DEFAULT_SOURCE_TEXTS中的默认描述。
    """
    proprietary_dir = data_dir / "proprietary"
    sources: Dict[str, str] = {}
    if proprietary_dir.exists():
        for f in proprietary_dir.glob("*.json"):
            with f.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            sid = data["id"]
            desc = (data.get("metadata") or {}).get("description") if isinstance(
                data.get("metadata"), dict
            ) else None
            sources[sid] = desc or DEFAULT_SOURCE_TEXTS.get(sid, data.get("name", sid))
    return sources


def build_prompt(source_text: str, target_lang: str) -> str:
    """构建翻译提示词。"""
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    return (
        f"请将以下英文文本翻译为{target_name}，保持简洁专业：\n\n"
        f"{source_text}\n\n"
        f"只输出译文，不要添加任何解释。"
    )


def build_translation_record(
    software_id: str,
    target_lang: str,
    source_text: str,
    translated_text: str,
    translator_model: str,
    confidence_score: float,
) -> Dict[str, Any]:
    """构建符合translation.schema.json的记录。"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()

    return {
        "id": f"{software_id}-{target_lang}",
        "sourceTextHash": source_hash,
        "targetLang": target_lang,
        "translatedText": translated_text,
        "translatorModel": translator_model,
        "confidenceScore": confidence_score,
        "reviewStatus": "pending",
        "metadata": {
            "created": today,
            "sourceLang": "en",
            "softwareId": software_id,
        },
        "_meta": {
            "source": "ai-generated",
            "schema_version": SCHEMA_VERSION,
            "unverified_fields": ["translatedText"],
            "confidence": "medium",
        },
    }


async def translate_one(
    client: AIClient,
    source_text: str,
    target_lang: str,
) -> tuple[str, str, float]:
    """翻译单条文本，返回 (译文, 模型, 置信度)。"""
    prompt = build_prompt(source_text, target_lang)
    try:
        resp = await client.generate(prompt, max_tokens=500)
        text = resp.text.strip()
        # Mock服务器返回的可能包含markdown，做简单清理
        if text.startswith("#"):
            text = "\n".join(text.split("\n")[1:]).strip()
        # 置信度基于响应长度合理性
        confidence = 0.9 if len(text) > 5 else 0.5
        return text, resp.model, confidence
    except QuotaExceededError as exc:
        print(f"  ❌ 配额耗尽：{exc}")
        raise
    except Exception as exc:
        print(f"  ⚠️  AI调用失败，使用兜底译文：{exc}")
        # 兜底：源文本就是英文，en直接返回，其他语种简单标注
        if target_lang == "en":
            return source_text, f"fallback-{client.provider}", 0.6
        fallback_text = f"[{target_lang}] {source_text}"
        return fallback_text, f"fallback-{client.provider}", 0.3


async def run_translate(
    data_dir: Path,
    provider: str,
    software_ids: List[str],
) -> List[Dict[str, Any]]:
    """执行全部翻译任务。"""
    print("=" * 70)
    print("🌐 OSSAF Pipeline - Step 3: 多语言翻译")
    print("=" * 70)
    print(f"  Provider: {provider}")
    print(f"  软件数: {len(software_ids)} | 语种数: {len(LANGUAGES)}")
    print(f"  预期产出: {len(software_ids) * len(LANGUAGES)} 条翻译")

    source_texts = load_source_texts(data_dir)
    if not source_texts:
        print("❌ 未能加载任何源文本，请先运行 collect_proprietary")
        return []

    client = AIClient(provider=provider)
    translation_dir = data_dir / "translation"
    translation_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for sid in software_ids:
        source_text = source_texts.get(sid)
        if not source_text:
            print(f"  ⏭️  跳过：{sid} 无源文本")
            continue

        print(f"\n  🔄 翻译 {sid}（源文本长度={len(source_text)}）...")
        for lang in LANGUAGES:
            translated, model, confidence = await translate_one(client, source_text, lang)
            record = build_translation_record(
                sid, lang, source_text, translated, model, confidence
            )
            out_path = translation_dir / f"{sid}-{lang}.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            results.append(record)
            print(f"    ✅ {lang}: {out_path.name} (model={model}, conf={confidence:.2f})")

    print(f"\n📊 翻译结果：{len(results)}/{len(software_ids) * len(LANGUAGES)} 条")
    return results


def main():
    parser = argparse.ArgumentParser(description="OSSAF Pipeline - 多语言翻译")
    parser.add_argument(
        "--provider",
        default="claude",
        choices=["claude", "openai", "gemini", "agnes"],
        help="AI提供方（默认claude）",
    )
    parser.add_argument("--data-dir", default="data", help="数据目录")
    parser.add_argument(
        "--software",
        nargs="*",
        default=None,
        help="指定要翻译的软件ID列表（默认全部）",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    software_ids = args.software or list(DEFAULT_SOURCE_TEXTS.keys())
    results = asyncio.run(run_translate(data_dir, args.provider, software_ids))
    print(f"\n✅ 翻译完成：{len(results)}条")


if __name__ == "__main__":
    main()
