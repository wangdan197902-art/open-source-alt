#!/usr/bin/env python3
"""run_all.py - 一键运行整个内容生产管道

按顺序执行8个Pipeline步骤：
  Step 1: collect_proprietary       - 采集商业软件（MVP硬上限）
  Step 2: generate_comparison       - 生成对比内容
  Step 3: translate_content         - 多语言翻译
  Step 4: generate_image_meta       - 生成配图元数据
  Step 5: review_content            - 内容审核
  Step 6: generate_use_cases        - 生成使用场景Mock数据
  Step 7: generate_similar          - 生成类似软件Mock数据
  Step 8: generate_alternative_list - 生成替代方案列表Mock数据

任一步骤失败将中止管道并输出错误摘要。

用法：
  python3 -m pipeline.run_all
  python3 -m pipeline.run_all --provider claude
  python3 -m pipeline.run_all --provider gemini --data-dir data
"""
import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.collect_proprietary import (  # noqa: E402
    MAX_PROPRIETARY_COUNT,
    collect as collect_proprietary,
)
from pipeline.generate_comparison import (  # noqa: E402
    DEFAULT_MAPPINGS,
    run_generate as run_generate_comparison,
)
from pipeline.generate_image_meta import run_generate as run_generate_image_meta  # noqa: E402
from pipeline.review_content import run_review  # noqa: E402
from pipeline.translate_content import (  # noqa: E402
    DEFAULT_SOURCE_TEXTS,
    LANGUAGES,
    run_translate,
)
from pipeline.generate_use_cases import run_generate_use_cases  # noqa: E402
from pipeline.generate_similar import run_generate_similar  # noqa: E402
from pipeline.generate_alternative_list import run_generate_alternative_list  # noqa: E402


def banner(text: str, char: str = "=") -> None:
    """打印横幅。"""
    line = char * 70
    print(f"\n{line}")
    print(f"  {text}")
    print(f"{line}")


def run_pipeline(data_dir: Path, provider: str, strict_review: bool) -> Dict[str, Any]:
    """运行完整Pipeline，返回步骤执行摘要。"""
    banner("OSSAF Content Pipeline - 一键运行", "🚀")
    print(f"  数据目录: {data_dir}")
    print(f"  AI Provider: {provider}")
    print(f"  严格审核: {strict_review}")
    print(f"  MVP硬上限: MAX_PROPRIETARY_COUNT={MAX_PROPRIETARY_COUNT}")

    overall_start = time.time()
    summary: Dict[str, Any] = {
        "steps": [],
        "success": False,
        "totalElapsedSec": 0.0,
    }

    def step(name: str, status: str, elapsed: float, count: int, error: str = "") -> None:
        summary["steps"].append(
            {
                "name": name,
                "status": status,
                "elapsedSec": round(elapsed, 2),
                "count": count,
                "error": error,
            }
        )

    # =========================================================================
    # Step 1: 采集商业软件
    # =========================================================================
    banner("Step 1/8: 采集商业软件（collect_proprietary）", "📥")
    t0 = time.time()
    try:
        proprietary = collect_proprietary(data_dir)
        elapsed = time.time() - t0
        step("collect_proprietary", "ok", elapsed, len(proprietary))
        print(f"  ⏱️  耗时: {elapsed:.2f}s | 产出: {len(proprietary)}条")
    except Exception as exc:
        elapsed = time.time() - t0
        step("collect_proprietary", "failed", elapsed, 0, str(exc))
        print(f"  ❌ 失败({elapsed:.2f}s): {exc}")
        summary["totalElapsedSec"] = round(time.time() - overall_start, 2)
        _print_summary(summary)
        return summary

    # =========================================================================
    # Step 2: 生成对比内容
    # =========================================================================
    banner("Step 2/8: 生成对比内容（generate_comparison）", "🤖")
    t0 = time.time()
    try:
        comparisons = asyncio.run(
            run_generate_comparison(data_dir, provider, DEFAULT_MAPPINGS)
        )
        elapsed = time.time() - t0
        step("generate_comparison", "ok", elapsed, len(comparisons))
        print(f"  ⏱️  耗时: {elapsed:.2f}s | 产出: {len(comparisons)}条")
    except Exception as exc:
        elapsed = time.time() - t0
        step("generate_comparison", "failed", elapsed, 0, str(exc))
        print(f"  ❌ 失败({elapsed:.2f}s): {exc}")
        summary["totalElapsedSec"] = round(time.time() - overall_start, 2)
        _print_summary(summary)
        return summary

    # =========================================================================
    # Step 3: 多语言翻译
    # =========================================================================
    banner(f"Step 3/8: 多语言翻译（translate_content, {len(LANGUAGES)}语种）", "🌐")
    t0 = time.time()
    try:
        software_ids = list(DEFAULT_SOURCE_TEXTS.keys())
        translations = asyncio.run(
            run_translate(data_dir, provider, software_ids)
        )
        elapsed = time.time() - t0
        step("translate_content", "ok", elapsed, len(translations))
        print(f"  ⏱️  耗时: {elapsed:.2f}s | 产出: {len(translations)}条")
    except Exception as exc:
        elapsed = time.time() - t0
        step("translate_content", "failed", elapsed, 0, str(exc))
        print(f"  ❌ 失败({elapsed:.2f}s): {exc}")
        summary["totalElapsedSec"] = round(time.time() - overall_start, 2)
        _print_summary(summary)
        return summary

    # =========================================================================
    # Step 4: 生成配图元数据
    # =========================================================================
    banner("Step 4/8: 生成配图元数据（generate_image_meta）", "🖼️ ")
    t0 = time.time()
    try:
        image_metas = run_generate_image_meta(data_dir)
        elapsed = time.time() - t0
        step("generate_image_meta", "ok", elapsed, len(image_metas))
        print(f"  ⏱️  耗时: {elapsed:.2f}s | 产出: {len(image_metas)}条")
    except Exception as exc:
        elapsed = time.time() - t0
        step("generate_image_meta", "failed", elapsed, 0, str(exc))
        print(f"  ❌ 失败({elapsed:.2f}s): {exc}")
        summary["totalElapsedSec"] = round(time.time() - overall_start, 2)
        _print_summary(summary)
        return summary

    # =========================================================================
    # Step 5: 内容审核
    # =========================================================================
    banner("Step 5/8: 内容审核（review_content）", "🔍")
    t0 = time.time()
    try:
        report = run_review(data_dir, strict_review)
        elapsed = time.time() - t0
        approved = report["summary"]["approved"]
        step("review_content", "ok", elapsed, approved)
        print(f"  ⏱️  耗时: {elapsed:.2f}s | 通过: {approved}条")
    except Exception as exc:
        elapsed = time.time() - t0
        step("review_content", "failed", elapsed, 0, str(exc))
        print(f"  ❌ 失败({elapsed:.2f}s): {exc}")
        summary["totalElapsedSec"] = round(time.time() - overall_start, 2)
        _print_summary(summary)
        return summary

    # =========================================================================
    # Step 6: 生成使用场景Mock数据（500软件×3场景×20语言=30,000条）
    # =========================================================================
    banner("Step 6/8: 生成使用场景数据（generate_use_cases）", "📋")
    t0 = time.time()
    try:
        use_cases = run_generate_use_cases(data_dir)
        elapsed = time.time() - t0
        step("generate_use_cases", "ok", elapsed, len(use_cases))
        print(f"  ⏱️  耗时: {elapsed:.2f}s | 产出: {len(use_cases)}条")
    except Exception as exc:
        elapsed = time.time() - t0
        step("generate_use_cases", "failed", elapsed, 0, str(exc))
        print(f"  ❌ 失败({elapsed:.2f}s): {exc}")
        summary["totalElapsedSec"] = round(time.time() - overall_start, 2)
        _print_summary(summary)
        return summary

    # =========================================================================
    # Step 7: 生成类似软件Mock数据（500软件×20语言=10,000条）
    # =========================================================================
    banner("Step 7/8: 生成类似软件数据（generate_similar）", "📋")
    t0 = time.time()
    try:
        similar = run_generate_similar(data_dir)
        elapsed = time.time() - t0
        step("generate_similar", "ok", elapsed, len(similar))
        print(f"  ⏱️  耗时: {elapsed:.2f}s | 产出: {len(similar)}条")
    except Exception as exc:
        elapsed = time.time() - t0
        step("generate_similar", "failed", elapsed, 0, str(exc))
        print(f"  ❌ 失败({elapsed:.2f}s): {exc}")
        summary["totalElapsedSec"] = round(time.time() - overall_start, 2)
        _print_summary(summary)
        return summary

    # =========================================================================
    # Step 8: 生成替代方案列表Mock数据（500软件×20语言=10,000条）
    # =========================================================================
    banner("Step 8/8: 生成替代方案列表数据（generate_alternative_list）", "📋")
    t0 = time.time()
    try:
        alternative_lists = run_generate_alternative_list(data_dir)
        elapsed = time.time() - t0
        step("generate_alternative_list", "ok", elapsed, len(alternative_lists))
        print(f"  ⏱️  耗时: {elapsed:.2f}s | 产出: {len(alternative_lists)}条")
    except Exception as exc:
        elapsed = time.time() - t0
        step("generate_alternative_list", "failed", elapsed, 0, str(exc))
        print(f"  ❌ 失败({elapsed:.2f}s): {exc}")
        summary["totalElapsedSec"] = round(time.time() - overall_start, 2)
        _print_summary(summary)
        return summary

    summary["success"] = True
    summary["totalElapsedSec"] = round(time.time() - overall_start, 2)
    _print_summary(summary)
    return summary


def _print_summary(summary: Dict[str, Any]) -> None:
    """打印Pipeline执行摘要。"""
    banner("Pipeline 执行摘要", "📊")
    for s in summary["steps"]:
        icon = "✅" if s["status"] == "ok" else "❌"
        print(
            f"  {icon} {s['name']:<25} {s['status']:<8} "
            f"{s['elapsedSec']:>6.2f}s  产出={s['count']}"
        )
        if s["error"]:
            print(f"      错误: {s['error']}")
    print(f"\n  总耗时: {summary['totalElapsedSec']}s")
    print(f"  整体状态: {'✅ 成功' if summary['success'] else '❌ 失败'}")
    if summary["success"]:
        print("\n  💡 下一步：运行 `python3 -m pipeline.pre_build_check` 进行构建前预检")


def main():
    parser = argparse.ArgumentParser(description="OSSAF Pipeline - 一键运行整个管道")
    parser.add_argument(
        "--provider",
        default="claude",
        choices=["claude", "openai", "gemini"],
        help="AI提供方（默认claude）",
    )
    parser.add_argument("--data-dir", default="data", help="数据目录")
    parser.add_argument(
        "--strict-review",
        action="store_true",
        help="严格审核模式（不自动通过Schema合规内容）",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    summary = run_pipeline(data_dir, args.provider, args.strict_review)
    sys.exit(0 if summary["success"] else 1)


if __name__ == "__main__":
    main()
