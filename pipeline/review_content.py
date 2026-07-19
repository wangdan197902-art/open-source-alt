#!/usr/bin/env python3
"""review_content.py - 内容审核

功能：
- 扫描所有 data/ 下的JSON内容文件
- 使用Pydantic模型（schemas模块）校验Schema合规性
- 自动审核通过符合Schema的内容（reviewStatus → approved）
- 标记问题内容为"pending"，记录原因
- 输出审核报告到 data/review_report.json

用法：
  python3 -m pipeline.review_content
  python3 -m pipeline.review_content --data-dir data
  python3 -m pipeline.review_content --strict  # 严格模式（不自动通过）
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError  # noqa: E402

from schemas import (  # noqa: E402
    Comparison,
    ImageMeta,
    OpenSource,
    Proprietary,
    Translation,
)

SCHEMA_VERSION = "1.0.0"

# 目录到Pydantic模型的映射
DIR_MODEL_MAP = {
    "proprietary": Proprietary,
    "opensource": OpenSource,
    "comparison": Comparison,
    "translation": Translation,
    "image-meta": ImageMeta,
}


def validate_record(record: Dict[str, Any], model_cls) -> tuple[bool, Optional[str]]:
    """校验单条记录是否符合Schema。"""
    try:
        model_cls.model_validate(record)
        return True, None
    except ValidationError as exc:
        return False, str(exc)


def review_file(json_path: Path, data_dir: Path, strict: bool) -> Dict[str, Any]:
    """审核单个JSON文件，返回审核结果。"""
    rel_path = json_path.relative_to(data_dir)
    parts = rel_path.parts
    category = parts[0] if len(parts) > 1 else "unknown"

    result = {
        "file": str(rel_path),
        "category": category,
        "schema_valid": False,
        "error": None,
        "previous_status": None,
        "new_status": None,
        "changed": False,
    }

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        result["error"] = f"JSON解析失败: {exc}"
        result["new_status"] = "pending"
        return result

    if not isinstance(data, dict) or "reviewStatus" not in data:
        result["error"] = "缺少reviewStatus字段，跳过"
        return result

    result["previous_status"] = data.get("reviewStatus")
    model_cls = DIR_MODEL_MAP.get(category)
    if model_cls is None:
        result["error"] = f"未知目录类别：{category}"
        result["new_status"] = data.get("reviewStatus", "pending")
        return result

    valid, err = validate_record(data, model_cls)
    result["schema_valid"] = valid
    if not valid:
        result["error"] = err
        result["new_status"] = "pending"
        # 写回pending状态
        if data.get("reviewStatus") != "pending":
            data["reviewStatus"] = "pending"
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            result["changed"] = True
        return result

    # Schema合规：自动通过（除非严格模式）
    if strict:
        result["new_status"] = data.get("reviewStatus", "pending")
        return result

    if data.get("reviewStatus") != "approved":
        data["reviewStatus"] = "approved"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        result["changed"] = True
    result["new_status"] = "approved"
    return result


def run_review(data_dir: Path, strict: bool) -> Dict[str, Any]:
    """执行全部审核。"""
    print("=" * 70)
    print("🔍 OSSAF Pipeline - Step 5: 内容审核")
    print("=" * 70)
    print(f"  模式: {'严格（不自动通过）' if strict else '自动通过Schema合规内容'}")

    results: List[Dict[str, Any]] = []
    for json_file in sorted(data_dir.rglob("*.json")):
        if json_file.name == "seed_manifest.json":
            continue
        if json_file.name == "review_report.json":
            continue
        result = review_file(json_file, data_dir, strict)
        results.append(result)

        status_icon = "✅" if result["schema_valid"] else "❌"
        change_icon = "📝" if result["changed"] else "  "
        print(
            f"  {status_icon}{change_icon} {result['file']} "
            f"[{result['previous_status']} → {result['new_status']}]"
        )
        if result["error"] and not result["schema_valid"]:
            err_short = result["error"].split("\n")[0][:120]
            print(f"        错误: {err_short}")

    # 统计
    total = len(results)
    valid = sum(1 for r in results if r["schema_valid"])
    invalid = total - valid
    approved = sum(1 for r in results if r["new_status"] == "approved")
    pending = sum(1 for r in results if r["new_status"] == "pending")
    changed = sum(1 for r in results if r["changed"])

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strictMode": strict,
        "summary": {
            "total": total,
            "schemaValid": valid,
            "schemaInvalid": invalid,
            "approved": approved,
            "pending": pending,
            "changed": changed,
        },
        "details": results,
        "_meta": {
            "source": "pipeline-review",
            "schema_version": SCHEMA_VERSION,
            "confidence": "high",
        },
    }

    report_path = data_dir / "review_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("📊 审核报告汇总")
    print("=" * 70)
    print(f"  总文件数:    {total}")
    print(f"  Schema合规:  {valid}")
    print(f"  Schema违规:  {invalid}")
    print(f"  Approved:    {approved}")
    print(f"  Pending:     {pending}")
    print(f"  本次变更:    {changed}")
    print(f"  报告路径:    {report_path}")

    if invalid > 0:
        print(f"\n⚠️  有 {invalid} 个文件Schema违规，请检查后再构建")
    else:
        print("\n✅ 所有文件Schema合规")

    return report


def main():
    parser = argparse.ArgumentParser(description="OSSAF Pipeline - 内容审核")
    parser.add_argument("--data-dir", default="data", help="数据目录")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式：不自动通过Schema合规内容，仅校验",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    report = run_review(data_dir, args.strict)
    # 若有Schema违规，以非0退出
    if report["summary"]["schemaInvalid"] > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
