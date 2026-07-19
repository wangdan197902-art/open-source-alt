#!/usr/bin/env python3
"""generate_mock_catalog.py - 批量生成500软件×20语言的Mock数据

功能：
- 基于 data/proprietary_catalog.json 和 data/opensource_catalog.json
- 为500个商业软件生成20语言Mock翻译数据（共500×20=10,000条）
- 为500个商业软件生成对比数据（共500条）
- 为500个商业软件生成图片元数据（共500条）
- 所有Mock数据标注 reviewStatus="pending" + aiGenerated=true
- 使用 ThreadPoolExecutor(max_workers=20) 并发写入
- 目标运行时间 ≤ 10 分钟

输出目录：
- data/translation/{software_id}-{lang}.json          (10,000条)
- data/comparison/{proprietary_id}-vs-{opensource_id}.json (500条)
- data/image-meta/{software_id}-screenshot.json       (500条)

用法：
  python3 scripts/generate_mock_catalog.py
  python3 scripts/generate_mock_catalog.py --data-dir data --max-workers 20
"""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_VERSION = "1.0.0"

# 20种目标语言（与 pipeline/translate_content.py 保持一致）
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

# 翻译模板（每种语言一个简单 Mock 模板）
# 实际 Mock 数据：[Mock lang] {name} 是由 {vendor} 开发的 {category} 软件。
TRANSLATION_TEMPLATE = "[Mock {lang_name}] {name} is a {category} software developed by {vendor}. {description}"


def now_iso() -> str:
    """当前UTC日期 (YYYY-MM-DD)。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def now_iso_timestamp() -> str:
    """当前UTC ISO时间戳。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_catalogs(data_dir: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """加载 proprietary_catalog.json 和 opensource_catalog.json。

    返回 (proprietary_list, opensource_list, opensource_by_proprietary_id)
    其中 opensource_by_proprietary_id 将 opensource 记录按 proprietaryAlternativeId 索引。
    """
    prop_path = data_dir / "proprietary_catalog.json"
    os_path = data_dir / "opensource_catalog.json"

    if not prop_path.exists():
        print(f"❌ 文件不存在: {prop_path}")
        sys.exit(1)
    if not os_path.exists():
        print(f"❌ 文件不存在: {os_path}")
        sys.exit(1)

    with prop_path.open("r", encoding="utf-8") as f:
        proprietary = json.load(f)
    with os_path.open("r", encoding="utf-8") as f:
        opensource = json.load(f)

    if not isinstance(proprietary, list) or not isinstance(opensource, list):
        print("❌ catalog 文件格式异常（应为数组）")
        sys.exit(1)

    # 建立 proprietaryId -> opensource 记录 的映射
    os_by_prop = {}
    for entry in opensource:
        prop_id = entry.get("proprietaryAlternativeId")
        if prop_id:
            os_by_prop[prop_id] = entry

    return proprietary, opensource, os_by_prop


# =============================================================================
# 记录构建函数
# =============================================================================

def build_translation_record(prop: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """构建翻译记录（符合 translation.schema.json）。"""
    software_id = prop["id"]
    name = prop.get("name", software_id)
    vendor = prop.get("vendor", "Unknown")
    category = prop.get("category", "unknown")
    description = prop.get("description", "")
    lang_name = LANGUAGE_NAMES.get(lang, lang)

    # 源文本（英文 description）
    source_text = (
        f"{name} is a {category} software developed by {vendor}. {description}"
    ).strip()

    # Mock 译文：直接基于模板生成（不调用真实 AI）
    translated_text = TRANSLATION_TEMPLATE.format(
        lang_name=lang_name,
        name=name,
        category=category,
        vendor=vendor,
        description=description,
    )

    source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()

    return {
        "id": f"{software_id}-{lang}",
        "sourceTextHash": source_hash,
        "targetLang": lang,
        "translatedText": translated_text,
        "translatorModel": "agnes-2.0-flash-mock",
        "confidenceScore": 0.9,
        "reviewStatus": "pending",
        "metadata": {
            "created": now_iso(),
            "sourceLang": "en",
            "softwareId": software_id,
        },
        "_meta": {
            "source": "ai-generated-mock",
            "schema_version": SCHEMA_VERSION,
            "unverified_fields": ["translatedText"],
            "confidence": "medium",
        },
    }


def build_comparison_record(prop: Dict[str, Any], oss: Dict[str, Any]) -> Dict[str, Any]:
    """构建对比记录（符合 comparison.schema.json）。"""
    prop_id = prop["id"]
    oss_id = oss["id"]
    prop_name = prop.get("name", prop_id)
    oss_name = oss.get("name", oss_id)

    # Mock featureComparison（3项基础对比）
    feature_comparison = [
        {
            "feature": "核心功能",
            "proprietarySupport": "yes",
            "openSourceSupport": "yes",
        },
        {
            "feature": "高级功能",
            "proprietarySupport": "yes",
            "openSourceSupport": "partial",
            "notes": f"{oss_name} 在高级功能上弱于 {prop_name}",
        },
        {
            "feature": "跨平台支持",
            "proprietarySupport": "yes",
            "openSourceSupport": "yes",
        },
    ]

    pros = [
        f"{oss_name} 完全开源免费",
        f"{oss_name} 跨平台支持",
        "无订阅费用",
        "社区活跃",
    ]
    cons = [
        f"{oss_name} 学习曲线较陡",
        "部分高级功能缺失",
        "企业级支持有限",
    ]
    use_cases = ["个人用户", "教育用途", "预算有限的团队", "开源爱好者"]

    prompt = (
        f"对比 {prop_name} 与 {oss_name}（mock 生成）"
    )
    prompt_hash = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    return {
        "id": f"{prop_id}-vs-{oss_id}",
        "proprietaryId": prop_id,
        "openSourceId": oss_id,
        "featureComparison": feature_comparison,
        "pros": pros,
        "cons": cons,
        "migrationDifficulty": "medium",
        "useCases": use_cases,
        "aiGenerated": True,
        "aiGeneratedDetails": {
            "model": "agnes-2.0-flash-mock",
            "generatedAt": now_iso_timestamp(),
            "promptHash": prompt_hash,
            "tokensUsed": 200,
        },
        "reviewStatus": "pending",
        "metadata": {
            "created": now_iso(),
            "updated": now_iso(),
            "rawResponseLength": 0,
        },
        "_meta": {
            "source": "ai-generated-mock",
            "schema_version": SCHEMA_VERSION,
            "unverified_fields": ["pros", "cons", "featureComparison"],
            "confidence": "medium",
        },
    }


def build_image_meta_record(prop: Dict[str, Any]) -> Dict[str, Any]:
    """构建图片元数据记录（符合 image-meta.schema.json）。"""
    software_id = prop["id"]
    name = prop.get("name", software_id)

    return {
        "id": f"{software_id}-screenshot",
        "type": "screenshot",
        "prompt": f"{name} 工作界面截图，展示主要功能与操作面板（Mock 生成）",
        "modelUsed": "agnes-2.0-flash-mock",
        "url": f"https://ossaf.local/images/screenshots/{software_id}.png",
        "altText": f"{name} 界面截图",
        "licenseInfo": "fair-use-for-comparison",
        "reviewStatus": "pending",
        "aiGenerated": True,
        "metadata": {
            "created": now_iso(),
            "width": 1920,
            "height": 1080,
            "softwareId": software_id,
            "actualImageGenerated": False,
        },
        "_meta": {
            "source": "ai-generated-mock",
            "schema_version": SCHEMA_VERSION,
            "unverified_fields": ["url", "modelUsed"],
            "confidence": "medium",
        },
    }


# =============================================================================
# 写入函数（线程安全）
# =============================================================================

def write_json_file(path: Path, data: Dict[str, Any]) -> None:
    """将 JSON 数据写入文件（原子写入：先写临时文件再重命名）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def write_translation(prop: Dict[str, Any], lang: str, translation_dir: Path) -> Tuple[str, bool, str]:
    """生成并写入单个翻译文件。"""
    try:
        record = build_translation_record(prop, lang)
        out_path = translation_dir / f"{prop['id']}-{lang}.json"
        write_json_file(out_path, record)
        return (f"{prop['id']}-{lang}", True, "")
    except Exception as exc:
        return (f"{prop['id']}-{lang}", False, str(exc))


def write_comparison(prop: Dict[str, Any], oss: Dict[str, Any], comparison_dir: Path) -> Tuple[str, bool, str]:
    """生成并写入单个对比文件。"""
    try:
        record = build_comparison_record(prop, oss)
        out_path = comparison_dir / f"{prop['id']}-vs-{oss['id']}.json"
        write_json_file(out_path, record)
        return (f"{prop['id']}-vs-{oss['id']}", True, "")
    except Exception as exc:
        return (f"{prop['id']}-vs-{oss['id']}", False, str(exc))


def write_image_meta(prop: Dict[str, Any], image_meta_dir: Path) -> Tuple[str, bool, str]:
    """生成并写入单个图片元数据文件。"""
    try:
        record = build_image_meta_record(prop)
        out_path = image_meta_dir / f"{prop['id']}-screenshot.json"
        write_json_file(out_path, record)
        return (f"{prop['id']}-screenshot", True, "")
    except Exception as exc:
        return (f"{prop['id']}-screenshot", False, str(exc))


# =============================================================================
# 主流程
# =============================================================================

def print_progress(done: int, total: int, label: str, bar_width: int = 30) -> None:
    """打印进度条。"""
    pct = done / total if total else 1.0
    filled = int(pct * bar_width)
    bar = "█" * filled + "─" * (bar_width - filled)
    sys.stdout.write(
        f"\r  {label}: [{bar}] {done}/{total} ({pct * 100:.1f}%) "
    )
    sys.stdout.flush()
    if done >= total:
        sys.stdout.write("\n")


def generate_all(
    data_dir: Path,
    proprietary: List[Dict[str, Any]],
    os_by_prop: Dict[str, Dict[str, Any]],
    max_workers: int,
) -> Dict[str, int]:
    """并发生成全部 Mock 数据。"""
    translation_dir = data_dir / "translation"
    comparison_dir = data_dir / "comparison"
    image_meta_dir = data_dir / "image-meta"

    translation_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)
    image_meta_dir.mkdir(parents=True, exist_ok=True)

    # 构建任务列表
    translation_tasks: List[Tuple[Dict[str, Any], str]] = []
    for prop in proprietary:
        for lang in LANGUAGES:
            translation_tasks.append((prop, lang))

    comparison_tasks: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    skipped_comparisons = 0
    for prop in proprietary:
        oss = os_by_prop.get(prop["id"])
        if oss:
            comparison_tasks.append((prop, oss))
        else:
            skipped_comparisons += 1

    image_meta_tasks: List[Dict[str, Any]] = list(proprietary)

    total_translations = len(translation_tasks)
    total_comparisons = len(comparison_tasks)
    total_image_metas = len(image_meta_tasks)
    grand_total = total_translations + total_comparisons + total_image_metas

    print(f"\n📋 任务规划:")
    print(f"  - 翻译文件: {total_translations} 条（{len(proprietary)}软件 × {len(LANGUAGES)}语言）")
    print(f"  - 对比文件: {total_comparisons} 条（跳过 {skipped_comparisons} 个无开源对应的项）")
    print(f"  - 图片元数据: {total_image_metas} 条")
    print(f"  - 总计: {grand_total} 条")
    print(f"  - 并发: max_workers={max_workers}")
    print()

    stats = {"translation_ok": 0, "translation_fail": 0,
             "comparison_ok": 0, "comparison_fail": 0,
             "image_meta_ok": 0, "image_meta_fail": 0}

    # ====================== 1. 翻译文件 ======================
    print("🌐 [1/3] 生成翻译文件...")
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(write_translation, prop, lang, translation_dir): (prop, lang)
            for prop, lang in translation_tasks
        }
        for future in as_completed(futures):
            _id, ok, err = future.result()
            done += 1
            if ok:
                stats["translation_ok"] += 1
            else:
                stats["translation_fail"] += 1
                if stats["translation_fail"] <= 3:
                    print(f"\n  ❌ {_id}: {err}")
            if done % 200 == 0 or done == total_translations:
                print_progress(done, total_translations, "翻译")
    t1 = time.time()
    print(f"  ⏱️  翻译耗时: {t1 - t0:.1f}s")

    # ====================== 2. 对比文件 ======================
    print("\n🤖 [2/3] 生成对比文件...")
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(write_comparison, prop, oss, comparison_dir): (prop, oss)
            for prop, oss in comparison_tasks
        }
        for future in as_completed(futures):
            _id, ok, err = future.result()
            done += 1
            if ok:
                stats["comparison_ok"] += 1
            else:
                stats["comparison_fail"] += 1
                if stats["comparison_fail"] <= 3:
                    print(f"\n  ❌ {_id}: {err}")
            if done % 50 == 0 or done == total_comparisons:
                print_progress(done, total_comparisons, "对比")
    t1 = time.time()
    print(f"  ⏱️  对比耗时: {t1 - t0:.1f}s")

    # ====================== 3. 图片元数据 ======================
    print("\n🖼️  [3/3] 生成图片元数据...")
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(write_image_meta, prop, image_meta_dir): prop
            for prop in image_meta_tasks
        }
        for future in as_completed(futures):
            _id, ok, err = future.result()
            done += 1
            if ok:
                stats["image_meta_ok"] += 1
            else:
                stats["image_meta_fail"] += 1
                if stats["image_meta_fail"] <= 3:
                    print(f"\n  ❌ {_id}: {err}")
            if done % 50 == 0 or done == total_image_metas:
                print_progress(done, total_image_metas, "图片元数据")
    t1 = time.time()
    print(f"  ⏱️  图片元数据耗时: {t1 - t0:.1f}s")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="OSSAF Mock Catalog 生成器 - 批量生成500×20语言的Mock数据"
    )
    parser.add_argument("--data-dir", default="data", help="数据目录（默认 data）")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=20,
        help="并发写入线程数（默认 20）",
    )
    args = parser.parse_args()

    data_dir = (PROJECT_ROOT / args.data_dir).resolve() if not Path(args.data_dir).is_absolute() else Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    print("=" * 70)
    print("🚀 OSSAF Mock Catalog 生成器")
    print("=" * 70)
    print(f"  数据目录: {data_dir}")
    print(f"  并发数: {args.max_workers}")

    proprietary, opensource, os_by_prop = load_catalogs(data_dir)
    print(f"\n📥 已加载:")
    print(f"  - proprietary_catalog.json: {len(proprietary)} 条")
    print(f"  - opensource_catalog.json: {len(opensource)} 条")
    print(f"  - proprietaryId → opensource 映射: {len(os_by_prop)} 条")

    t_start = time.time()
    stats = generate_all(data_dir, proprietary, os_by_prop, args.max_workers)
    t_end = time.time()
    total_time = t_end - t_start

    # ====================== 红绿灯测试报告 ======================
    print("\n" + "=" * 70)
    print("📊 红绿灯测试 - Mock Catalog 生成报告")
    print("=" * 70)

    total_ok = sum(v for k, v in stats.items() if k.endswith("_ok"))
    total_fail = sum(v for k, v in stats.items() if k.endswith("_fail"))

    print(f"\n[1] 文件数验证:")
    print(f"    翻译文件: 成功 {stats['translation_ok']}, 失败 {stats['translation_fail']} (期望 10,000)")
    print(f"    对比文件: 成功 {stats['comparison_ok']}, 失败 {stats['comparison_fail']} (期望 500)")
    print(f"    图片元数据: 成功 {stats['image_meta_ok']}, 失败 {stats['image_meta_fail']} (期望 500)")
    if stats["translation_ok"] == 10000 and stats["comparison_ok"] >= 500 and stats["image_meta_ok"] == 500:
        print("    ✅ PASS: 文件数量符合预期")
    else:
        print("    ❌ FAIL: 文件数量异常")

    print(f"\n[2] 性能验证:")
    print(f"    总耗时: {total_time:.1f}s ({total_time / 60:.1f}min)")
    if total_time <= 600:
        print(f"    ✅ PASS: ≤ 10 分钟")
    else:
        print(f"    ❌ FAIL: 超过 10 分钟")

    print(f"\n[3] 成功率:")
    print(f"    总成功: {total_ok}/{total_ok + total_fail}")
    if total_fail == 0:
        print(f"    ✅ PASS: 全部成功")
    else:
        print(f"    ❌ FAIL: 有 {total_fail} 个失败")

    print(f"\n[4] 输出目录:")
    print(f"    - {data_dir / 'translation'}")
    print(f"    - {data_dir / 'comparison'}")
    print(f"    - {data_dir / 'image-meta'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
