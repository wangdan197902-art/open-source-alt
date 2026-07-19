#!/usr/bin/env python3
"""generate_image_meta.py - 生成配图元数据（不实际生成图片）

功能：
- 为每个商业软件生成截图元数据（仅元数据，不调用图片生成API）
- 输出到 data/image-meta/{software}-screenshot.json
- 元数据符合 image-meta.schema.json

用法：
  python3 -m pipeline.generate_image_meta
  python3 -m pipeline.generate_image_meta --data-dir data
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SCHEMA_VERSION = "1.0.0"

# 每个商业软件的截图描述模板
SCREENSHOT_TEMPLATES = {
    "photoshop": {
        "prompt": "Adobe Photoshop工作界面截图，展示工具栏、图层面板、画布与图像编辑功能",
        "altText": "Adobe Photoshop图像编辑界面截图",
    },
    "notion": {
        "prompt": "Notion工作区界面截图，展示文档编辑、数据库视图与侧边栏导航",
        "altText": "Notion工作区界面截图",
    },
    "figma": {
        "prompt": "Figma设计界面截图，展示画布、设计面板、图层与协作光标",
        "altText": "Figma设计界面截图",
    },
    "slack": {
        "prompt": "Slack工作区界面截图，展示频道列表、消息流与协作功能",
        "altText": "Slack团队协作界面截图",
    },
    "zoom": {
        "prompt": "Zoom视频会议界面截图，展示参会者画面、控制栏与聊天功能",
        "altText": "Zoom视频会议界面截图",
    },
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


def build_image_meta_record(software_id: str, prop: Dict[str, Any]) -> Dict[str, Any]:
    """构建符合image-meta.schema.json的记录。"""
    template = SCREENSHOT_TEMPLATES.get(
        software_id,
        {
            "prompt": f"{prop.get('name', software_id)}工作界面截图",
            "altText": f"{prop.get('name', software_id)}界面截图",
        },
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return {
        "id": f"{software_id}-screenshot",
        "type": "screenshot",
        "prompt": template["prompt"],
        "modelUsed": "mock-gemini-pro-vision",  # 占位：实际图片未生成
        "url": f"https://ossaf.local/images/screenshots/{software_id}.png",
        "altText": template["altText"],
        "licenseInfo": "fair-use-for-comparison",
        "reviewStatus": "pending",
        "metadata": {
            "created": today,
            "width": 1920,
            "height": 1080,
            "softwareId": software_id,
            "actualImageGenerated": False,  # 标记：仅元数据，未实际生成图片
        },
        "_meta": {
            "source": "ai-generated-metadata",
            "schema_version": SCHEMA_VERSION,
            "unverified_fields": ["url", "modelUsed"],
            "confidence": "medium",
        },
    }


def run_generate(data_dir: Path) -> List[Dict[str, Any]]:
    """生成所有配图元数据。"""
    print("=" * 70)
    print("🖼️  OSSAF Pipeline - Step 4: 生成配图元数据")
    print("=" * 70)
    print("  ⚠️  注意：本步骤仅生成元数据，不实际生成图片")

    proprietary = load_proprietary(data_dir)
    if not proprietary:
        print("❌ data/proprietary/ 为空，请先运行 collect_proprietary")
        return []

    image_meta_dir = data_dir / "image-meta"
    image_meta_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for sid, prop in proprietary.items():
        record = build_image_meta_record(sid, prop)
        out_path = image_meta_dir / f"{sid}-screenshot.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        results.append(record)
        print(f"  ✅ {sid}: {out_path.name} (altText='{record['altText']}')")

    print(f"\n📊 生成结果：{len(results)}条配图元数据")
    print("  💡 提示：实际图片需后续通过图片生成API或人工截图补充")
    return results


def main():
    parser = argparse.ArgumentParser(description="OSSAF Pipeline - 生成配图元数据")
    parser.add_argument("--data-dir", default="data", help="数据目录")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    results = run_generate(data_dir)
    print(f"\n✅ 配图元数据生成完成：{len(results)}条")


if __name__ == "__main__":
    main()
