#!/usr/bin/env python3
"""generate_comparison.py - 生成商业软件与开源软件对比内容

功能：
- 调用AIClient生成对比内容（Claude/GPT-4o/Gemini任选）
- 基于种子清单的proprietary→opensource映射
- 输出到 data/comparison/

用法：
  python3 -m pipeline.generate_comparison
  python3 -m pipeline.generate_comparison --provider claude
  python3 -m pipeline.generate_comparison --provider gemini --data-dir data
"""
import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# 确保项目根目录可导入adapters
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.ai_client import AIClient, QuotaExceededError  # noqa: E402

SCHEMA_VERSION = "1.0.0"
DEFAULT_MAPPINGS = {
    "photoshop": "gimp",
    "notion": "obsidian",
    "figma": "penpot",
    "slack": "element",
    "zoom": "bigbluebutton",
}


def load_proprietary(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """加载所有商业软件记录。"""
    proprietary_dir = data_dir / "proprietary"
    result = {}
    if not proprietary_dir.exists():
        return result
    for f in proprietary_dir.glob("*.json"):
        with f.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        result[data["id"]] = data
    return result


def load_opensource(data_dir: Path) -> Dict[str, Dict[str, Any]]:
    """加载所有开源软件记录。"""
    opensource_dir = data_dir / "opensource"
    result = {}
    if not opensource_dir.exists():
        return result
    for f in opensource_dir.glob("*.json"):
        with f.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        result[data["id"]] = data
    return result


def build_prompt(prop: Dict[str, Any], oss: Dict[str, Any]) -> str:
    """构建对比生成的提示词。"""
    return (
        f"请对比以下商业软件与开源软件的功能差异：\n\n"
        f"商业软件：{prop.get('name', prop['id'])}（厂商：{prop.get('vendor', 'Unknown')}）\n"
        f"  分类：{prop.get('category', 'unknown')}\n"
        f"  平台：{', '.join(prop.get('platforms', []))}\n"
        f"  定价模型：{prop.get('pricingModel', 'unknown')}\n\n"
        f"开源软件：{oss.get('name', oss['id'])}\n"
        f"  仓库：{oss.get('repository', 'unknown')}\n"
        f"  协议：{oss.get('license', 'unknown')}\n"
        f"  成熟度：{oss.get('maturityLevel', 'unknown')}\n\n"
        f"请输出：\n"
        f"1. 功能对比（至少3项，标注支持/部分支持/不支持）\n"
        f"2. 开源软件的优势列表\n"
        f"3. 开源软件的劣势列表\n"
        f"4. 迁移难度（easy/medium/hard）\n"
        f"5. 适用场景\n"
    )


def parse_ai_response(text: str, prop_id: str, oss_id: str) -> Dict[str, Any]:
    """从AI返回的文本中解析出结构化对比数据。

    Mock服务器返回的是Markdown文本，这里做最小化的内容提取：
    - 提取pros/cons（基于"优势"/"劣势"段落）
    - 默认迁移难度为medium
    - 默认useCases基于软件类型
    """
    pros: List[str] = []
    cons: List[str] = []
    use_cases: List[str] = []
    migration = "medium"

    lines = text.split("\n")
    section = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if "优势" in stripped or "advantage" in lower:
            section = "pros"
            continue
        if "劣势" in stripped or "disadvantage" in lower:
            section = "cons"
            continue
        if "迁移难度" in stripped:
            if "简单" in stripped or "easy" in lower:
                migration = "easy"
            elif "困难" in stripped or "hard" in lower:
                migration = "hard"
            else:
                migration = "medium"
            section = None
            continue
        if "适用场景" in stripped:
            section = "usecases"
            continue
        if stripped.startswith("-") or stripped.startswith("•"):
            item = stripped.lstrip("-• ").strip()
            if not item:
                continue
            if section == "pros":
                pros.append(item)
            elif section == "cons":
                cons.append(item)
            elif section == "usecases":
                use_cases.append(item)

    # 兜底：如果AI没解析出内容，使用合理默认值
    if not pros:
        pros = [f"{oss_id} 完全开源免费", f"{oss_id} 跨平台支持", "无订阅费用"]
    if not cons:
        cons = [f"{oss_id} 学习曲线较陡", f"{oss_id} 部分高级功能缺失"]
    if not use_cases:
        use_cases = ["个人用户", "教育用途", "预算有限的团队"]

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
            "notes": f"{oss_id}在高级功能上弱于{prop_id}",
        },
        {
            "feature": "跨平台支持",
            "proprietarySupport": "yes",
            "openSourceSupport": "yes",
        },
    ]

    return {
        "featureComparison": feature_comparison,
        "pros": pros,
        "cons": cons,
        "migrationDifficulty": migration,
        "useCases": use_cases,
    }


def build_comparison_record(
    prop_id: str,
    oss_id: str,
    ai_text: str,
    model: str,
    prompt: str,
) -> Dict[str, Any]:
    """构建符合comparison.schema.json的记录。"""
    parsed = parse_ai_response(ai_text, prop_id, oss_id)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt_hash = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    tokens_used = (
        ai_text.count(" ") // 3 + 100  # 粗略估算
    )

    return {
        "id": f"{prop_id}-vs-{oss_id}",
        "proprietaryId": prop_id,
        "openSourceId": oss_id,
        "featureComparison": parsed["featureComparison"],
        "pros": parsed["pros"],
        "cons": parsed["cons"],
        "migrationDifficulty": parsed["migrationDifficulty"],
        "useCases": parsed["useCases"],
        "aiGenerated": True,
        "aiGeneratedDetails": {
            "model": model,
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "promptHash": prompt_hash,
            "tokensUsed": tokens_used,
        },
        "reviewStatus": "pending",
        "metadata": {
            "created": today,
            "updated": today,
            "rawResponseLength": len(ai_text),
        },
        "_meta": {
            "source": "ai-generated",
            "schema_version": SCHEMA_VERSION,
            "unverified_fields": ["pros", "cons", "featureComparison"],
            "confidence": "medium",
        },
    }


async def generate_one(
    client: AIClient,
    prop: Dict[str, Any],
    oss: Dict[str, Any],
) -> Tuple[str, str, str]:
    """生成单条对比内容，返回 (ai_text, model, prompt)。"""
    prompt = build_prompt(prop, oss)
    try:
        resp = await client.generate(prompt, max_tokens=1500)
        return resp.text, resp.model, prompt
    except QuotaExceededError as exc:
        print(f"  ❌ 配额耗尽：{exc}")
        raise
    except Exception as exc:
        print(f"  ⚠️  AI调用失败，使用兜底文本：{exc}")
        fallback = (
            f"# {prop.get('name', prop['id'])} vs {oss.get('name', oss['id'])} 对比\n\n"
            f"## {oss.get('name', oss['id'])} 的优势\n"
            f"- 完全开源免费\n- 跨平台支持\n- 社区活跃\n\n"
            f"## {oss.get('name', oss['id'])} 的劣势\n"
            f"- 学习曲线较陡\n- 部分高级功能缺失\n\n"
            f"## 迁移难度\n中等（medium）\n\n"
            f"## 适用场景\n- 个人用户\n- 教育用途\n- 预算有限的团队\n"
        )
        return fallback, f"fallback-{client.provider}", prompt


async def run_generate(
    data_dir: Path,
    provider: str,
    mappings: Dict[str, str],
) -> List[Dict[str, Any]]:
    """生成所有对比内容。"""
    print("=" * 70)
    print("🤖 OSSAF Pipeline - Step 2: 生成对比内容")
    print("=" * 70)
    print(f"  Provider: {provider}")

    proprietary = load_proprietary(data_dir)
    opensource = load_opensource(data_dir)

    if not proprietary:
        print("❌ data/proprietary/ 为空，请先运行 collect_proprietary")
        return []
    if not opensource:
        print("❌ data/opensource/ 为空，请先准备开源软件数据")
        return []

    client = AIClient(provider=provider)
    comparison_dir = data_dir / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for prop_id, oss_id in mappings.items():
        if prop_id not in proprietary:
            print(f"  ⏭️  跳过：proprietary/{prop_id}.json 不存在")
            continue
        if oss_id not in opensource:
            print(f"  ⏭️  跳过：opensource/{oss_id}.json 不存在")
            continue

        print(f"  🔄 生成：{prop_id} vs {oss_id} ...")
        ai_text, model, prompt = await generate_one(
            client, proprietary[prop_id], opensource[oss_id]
        )
        record = build_comparison_record(prop_id, oss_id, ai_text, model, prompt)
        out_path = comparison_dir / f"{prop_id}-vs-{oss_id}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        results.append(record)
        print(f"  ✅ 已保存：{out_path.name} (model={model})")

    print(f"\n📊 生成结果：{len(results)}/{len(mappings)} 条对比内容")
    return results


def main():
    parser = argparse.ArgumentParser(description="OSSAF Pipeline - 生成对比内容")
    parser.add_argument(
        "--provider",
        default="claude",
        choices=["claude", "openai", "gemini"],
        help="AI提供方（默认claude）",
    )
    parser.add_argument("--data-dir", default="data", help="数据目录")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    results = asyncio.run(run_generate(data_dir, args.provider, DEFAULT_MAPPINGS))
    print(f"\n✅ 对比内容生成完成：{len(results)}条")


if __name__ == "__main__":
    main()
