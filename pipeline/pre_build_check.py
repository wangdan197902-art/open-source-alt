#!/usr/bin/env python3
"""pre_build_check.py - Hugo构建前预检（Pipeline阻断核心）

功能：
- 扫描所有data/目录下的JSON文件
- 检查reviewStatus字段
- 任一非approved则exit 1

用法：
  python3 -m pipeline.pre_build_check
  python3 -m pipeline.pre_build_check --ignore-review  # 绕过（有警告）
"""
import sys
import json
import argparse
from pathlib import Path


def check_review_status(data_dir: Path, ignore_review: bool = False) -> bool:
    """检查所有JSON文件的reviewStatus"""
    all_approved = True
    checked = 0
    rejected = 0

    for json_file in data_dir.rglob("*.json"):
        if json_file.name == "seed_manifest.json":
            continue

        try:
            with open(json_file) as f:
                data = json.load(f)

            if isinstance(data, dict) and "reviewStatus" in data:
                checked += 1
                status = data["reviewStatus"]
                if status != "approved":
                    rejected += 1
                    all_approved = False
                    print(f"❌ {json_file.relative_to(data_dir)} - reviewStatus: {status}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  {json_file.relative_to(data_dir)} - 解析失败: {e}")

    print(f"\n📊 检查结果: {checked}个文件, {rejected}个未通过")

    if not all_approved:
        if ignore_review:
            print("⚠️  --ignore-review 已启用，跳过阻断（开发模式）")
            print("⚠️  警告：未审核内容将进入构建，请确保仅用于本地开发！")
            return True
        else:
            print("❌ Pipeline阻断：存在未审核内容，请先审核或使用--ignore-review")
            return False

    print("✅ 所有内容已审核通过，可以构建")
    return True


def main():
    parser = argparse.ArgumentParser(description="OSSAF Hugo构建前预检")
    parser.add_argument("--ignore-review", action="store_true", help="绕过审核检查（开发模式）")
    parser.add_argument("--data-dir", default="data", help="数据目录")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    if check_review_status(data_dir, args.ignore_review):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
