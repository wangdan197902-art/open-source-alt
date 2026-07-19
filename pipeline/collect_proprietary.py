#!/usr/bin/env python3
"""collect_proprietary.py - 采集商业软件信息

功能：
- 优先从 data/proprietary_catalog.json 批量读取商业软件信息
- 支持从Mock服务器或种子数据 fallback
- 输出到 data/proprietary/

数据源优先级：
1. data/proprietary_catalog.json（500条批量目录）
2. Mock服务器（AlternativeTo API的supported_ids列表）
3. data/seed_manifest.json（种子清单）
4. data/proprietary/*.json（已存在的数据）

用法：
  python3 -m pipeline.collect_proprietary
  python3 -m pipeline.collect_proprietary --data-dir data
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx

# =============================================================================
# 商业软件数量上限（可通过环境变量 OSSAF_MAX_PROPRIETARY 配置，默认500）
# =============================================================================
MAX_PROPRIETARY_COUNT = int(os.getenv("OSSAF_MAX_PROPRIETARY", "500"))


SCHEMA_VERSION = "1.0.0"
SUPPORTED_SOFTWARE = ["photoshop", "notion", "figma", "slack", "zoom"]


def load_seed_manifest(data_dir: Path) -> Dict[str, Any]:
    """加载种子清单。"""
    manifest_path = data_dir / "seed_manifest.json"
    if not manifest_path.exists():
        return {}
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_catalog(data_dir: Path) -> List[Dict[str, Any]]:
    """从 data/proprietary_catalog.json 批量读取商业软件目录。

    返回 catalog 中的全部记录（最多 MAX_PROPRIETARY_COUNT 条）。
    若 catalog 不存在或为空，返回空列表，由调用方降级到其他数据源。
    """
    catalog_path = data_dir / "proprietary_catalog.json"
    if not catalog_path.exists():
        return []
    try:
        with catalog_path.open("r", encoding="utf-8") as f:
            catalog = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"⚠️  proprietary_catalog.json 读取失败: {exc}")
        return []
    if not isinstance(catalog, list):
        print(f"⚠️  proprietary_catalog.json 格式异常（非数组）")
        return []
    return catalog[:MAX_PROPRIETARY_COUNT]


def fetch_mock_supported_ids(base_url: str) -> List[str]:
    """从Mock服务器根端点拉取支持的软件ID列表。"""
    try:
        resp = httpx.get(f"{base_url}/", timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        # AlternativeTo路由的supported_ids（在/apis中）
        for api in data.get("endpoints", {}).get("apis", []):
            if api.get("name") == "AlternativeTo" and "supported_ids" in api:
                return api["supported_ids"]
        return []
    except Exception as exc:
        print(f"⚠️  Mock服务器不可用({base_url}): {exc}")
        return []


def build_proprietary_record(
    software_id: str,
    manifest: Dict[str, Any],
    catalog_entry: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """根据软件ID构建符合proprietary.schema.json的记录。

    优先级：
    1. 复用已存在的 data/proprietary/{id}.json
    2. 从 catalog_entry（proprietary_catalog.json 中的条目）构建
    3. 基于内置 name_map/vendor_map 等构建最小化记录（reviewStatus=pending）
    """
    proprietary_dir = manifest.get("_data_dir")
    existing_path = (
        proprietary_dir / f"{software_id}.json"
        if proprietary_dir
        else Path(f"data/proprietary/{software_id}.json")
    )
    if existing_path.exists():
        with existing_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 优先使用 catalog 数据构建（保留 catalog 的 reviewStatus/aiGenerated 等字段）
    if catalog_entry and catalog_entry.get("id") == software_id:
        record = dict(catalog_entry)  # 浅拷贝，避免污染原 catalog
        # 规范化 metadata（确保 created/updated 存在）
        metadata = dict(record.get("metadata") or {})
        metadata.setdefault("created", today)
        metadata.setdefault("updated", today)
        record["metadata"] = metadata
        # 确保 _meta 存在并标注 schema_version
        meta = dict(record.get("_meta") or {})
        meta.setdefault("source", "proprietary-catalog")
        meta.setdefault("schema_version", SCHEMA_VERSION)
        meta.setdefault("unverified_fields", [])
        meta.setdefault("confidence", "high")
        record["_meta"] = meta
        return record

    # 构建最小化记录（仅用于Pipeline首次填充）
    name_map = {
        "photoshop": "Adobe Photoshop",
        "notion": "Notion",
        "figma": "Figma",
        "slack": "Slack",
        "zoom": "Zoom",
    }
    vendor_map = {
        "photoshop": "Adobe",
        "notion": "Notion Labs Inc.",
        "figma": "Figma Inc.",
        "slack": "Slack Technologies",
        "zoom": "Zoom Communications",
    }
    category_map = {
        "photoshop": "image-editing",
        "notion": "note-taking",
        "figma": "design-collaboration",
        "slack": "team-communication",
        "zoom": "video-conferencing",
    }
    url_map = {
        "photoshop": "https://www.adobe.com/products/photoshop.html",
        "notion": "https://www.notion.so",
        "figma": "https://www.figma.com",
        "slack": "https://slack.com",
        "zoom": "https://zoom.us",
    }
    pricing_map = {
        "photoshop": "subscription",
        "notion": "freemium",
        "figma": "freemium",
        "slack": "freemium",
        "zoom": "freemium",
    }
    platforms_map = {
        "photoshop": ["Windows", "macOS"],
        "notion": ["Web", "Windows", "macOS", "iOS", "Android"],
        "figma": ["Web", "Windows", "macOS"],
        "slack": ["Web", "Windows", "macOS", "Linux", "iOS", "Android"],
        "zoom": ["Web", "Windows", "macOS", "Linux", "iOS", "Android"],
    }

    return {
        "id": software_id,
        "name": name_map.get(software_id, software_id.title()),
        "vendor": vendor_map.get(software_id, "Unknown"),
        "category": category_map.get(software_id, "unknown"),
        "officialUrl": url_map.get(software_id, f"https://example.com/{software_id}"),
        "pricingModel": pricing_map.get(software_id, "subscription"),
        "platforms": platforms_map.get(software_id, ["Web"]),
        "trademarkStatus": "reviewed",
        "reviewStatus": "pending",
        "aiGenerated": False,
        "metadata": {"created": today, "updated": today},
        "_meta": {
            "source": "manual-seed",
            "schema_version": SCHEMA_VERSION,
            "unverified_fields": [],
            "confidence": "high",
        },
    }


def collect(data_dir: Path, base_url: str = "http://127.0.0.1:8765") -> List[Dict[str, Any]]:
    """采集商业软件信息。"""
    print("=" * 70)
    print("📥 OSSAF Pipeline - Step 1: 采集商业软件信息")
    print("=" * 70)
    print(f"   MAX_PROPRIETARY_COUNT = {MAX_PROPRIETARY_COUNT}")

    manifest = load_seed_manifest(data_dir)
    manifest["_data_dir"] = data_dir / "proprietary"

    # 优先从 proprietary_catalog.json 批量读取
    catalog = load_catalog(data_dir)
    catalog_map: Dict[str, Dict[str, Any]] = {entry["id"]: entry for entry in catalog if "id" in entry}

    if catalog:
        print(f"📦 从 proprietary_catalog.json 读取到 {len(catalog)} 条记录")
        software_ids = [entry["id"] for entry in catalog]
    else:
        # 降级：从Mock服务器拉取支持的ID列表，再降级到种子清单
        print("⚠️  proprietary_catalog.json 不可用，降级到 Mock 服务器")
        software_ids = fetch_mock_supported_ids(base_url)
        if not software_ids:
            print("⚠️  降级：使用种子清单中的commercialSoftware列表")
            software_ids = manifest.get("commercialSoftware", SUPPORTED_SOFTWARE)

    print(f"📋 候选软件数量: {len(software_ids)}")

    # 上限检查（可配置，默认500）
    if len(software_ids) > MAX_PROPRIETARY_COUNT:
        print(
            f"⚠️  候选{len(software_ids)}个 > MAX_PROPRIETARY_COUNT={MAX_PROPRIETARY_COUNT}，截断"
        )
        software_ids = software_ids[:MAX_PROPRIETARY_COUNT]

    proprietary_dir = data_dir / "proprietary"
    proprietary_dir.mkdir(parents=True, exist_ok=True)

    collected = []
    for sid in software_ids:
        record = build_proprietary_record(sid, manifest, catalog_entry=catalog_map.get(sid))
        # 移除临时字段
        manifest.pop("_data_dir", None)
        out_path = proprietary_dir / f"{sid}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        collected.append(record)
        print(f"  ✅ {sid}: {record['name']} ({record['vendor']}) → {out_path.name}")

    print(f"\n📊 采集结果: {len(collected)}/{MAX_PROPRIETARY_COUNT}")
    if len(collected) >= MAX_PROPRIETARY_COUNT:
        print(f"⚠️  已达上限 {MAX_PROPRIETARY_COUNT}（可通过环境变量 OSSAF_MAX_PROPRIETARY 调整）")
    return collected


def main():
    parser = argparse.ArgumentParser(description="OSSAF Pipeline - 采集商业软件")
    parser.add_argument("--data-dir", default="data", help="数据目录")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Mock服务器地址（默认读 OSSAF_API_BASE_URL 或 http://127.0.0.1:8765）",
    )
    args = parser.parse_args()

    base_url = args.base_url or os.getenv("OSSAF_API_BASE_URL", "http://127.0.0.1:8765")
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    collected = collect(data_dir, base_url)
    print(f"\n✅ 采集完成：{len(collected)}个商业软件")


if __name__ == "__main__":
    main()
