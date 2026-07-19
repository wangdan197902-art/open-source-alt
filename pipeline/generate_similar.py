#!/usr/bin/env python3
"""generate_similar.py - 生成类似软件推荐Mock数据

功能：
- 为每个商业软件推荐5个类似软件（同类别）
- 每个软件20种语言的描述
- 总数据量：500软件 × 20语言 = 10,000条
- 输出到 data/similar/{software_id}-{lang}.json

用法：
  python3 -m pipeline.generate_similar
  python3 -m pipeline.generate_similar --data-dir data
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

SCHEMA_VERSION = "1.0.0"

# 20种目标语言（不含 en 源语言）
LANGUAGES = [
    "zh", "ja", "ko", "es",
    "de", "fr", "pt", "it", "ru", "ar",
    "nl", "pl", "tr", "id", "vi", "th",
    "hi", "bn", "ms", "uk",
]

# 每个软件推荐的类似软件数量
SIMILAR_COUNT = 5

# 多语言模板（title/desc 中支持 {name} 占位符）
LANGUAGE_TEMPLATES = {
    "zh": {
        "similar_title": "类似 {name} 的软件",
        "similar_desc": "以下是与 {name} 类似的软件推荐列表，供您参考选择。",
    },
    "ja": {
        "similar_title": "{name} に似たソフトウェア",
        "similar_desc": "以下は {name} に似たソフトウェアのおすすめリストです。",
    },
    "ko": {
        "similar_title": "{name} 와(과) 유사한 소프트웨어",
        "similar_desc": "다음은 {name} 와(과) 유사한 추천 소프트웨어 목록입니다.",
    },
    "es": {
        "similar_title": "Software similar a {name}",
        "similar_desc": "A continuación se muestra una lista de software similar a {name}.",
    },
    "de": {
        "similar_title": "Ähnliche Software wie {name}",
        "similar_desc": "Nachfolgend finden Sie eine Liste ähnlicher Software wie {name}.",
    },
    "fr": {
        "similar_title": "Logiciels similaires à {name}",
        "similar_desc": "Voici une liste de logiciels similaires à {name}.",
    },
    "pt": {
        "similar_title": "Software similar ao {name}",
        "similar_desc": "Abaixo está uma lista de softwares similares ao {name}.",
    },
    "it": {
        "similar_title": "Software simile a {name}",
        "similar_desc": "Di seguito è riportato un elenco di software simili a {name}.",
    },
    "ru": {
        "similar_title": "Программное обеспечение, похожее на {name}",
        "similar_desc": "Ниже приведен список программ, похожих на {name}.",
    },
    "ar": {
        "similar_title": "برامج مشابهة لـ {name}",
        "similar_desc": "فيما يلي قائمة بالبرامج المشابهة لـ {name}.",
    },
    "nl": {
        "similar_title": "Software vergelijkbaar met {name}",
        "similar_desc": "Hieronder staat een lijst met software vergelijkbaar met {name}.",
    },
    "pl": {
        "similar_title": "Oprogramowanie podobne do {name}",
        "similar_desc": "Poniżej znajduje się lista oprogramowania podobnego do {name}.",
    },
    "tr": {
        "similar_title": "{name} ile benzer yazılımlar",
        "similar_desc": "Aşağıda {name} ile benzer yazılımların bir listesi bulunmaktadır.",
    },
    "id": {
        "similar_title": "Perangkat lunak yang mirip dengan {name}",
        "similar_desc": "Berikut adalah daftar perangkat lunak yang mirip dengan {name}.",
    },
    "vi": {
        "similar_title": "Phần mềm tương tự {name}",
        "similar_desc": "Dưới đây là danh sách các phần mềm tương tự {name}.",
    },
    "th": {
        "similar_title": "ซอฟต์แวร์ที่คล้ายกับ {name}",
        "similar_desc": "ด้านล่างนี้คือรายการซอฟต์แวร์ที่คล้ายกับ {name}",
    },
    "hi": {
        "similar_title": "{name} के समान सॉफ़्टवेयर",
        "similar_desc": "नीचे {name} के समान सॉफ़्टवेयर की सूची दी गई है।",
    },
    "bn": {
        "similar_title": "{name} এর অনুরূপ সফ্টওয়্যার",
        "similar_desc": "নিচে {name} এর অনুরূপ সফ্টওয়্যারের একটি তালিকা দেওয়া হলো।",
    },
    "ms": {
        "similar_title": "Perisian serupa dengan {name}",
        "similar_desc": "Berikut ialah senarai perisian yang serupa dengan {name}.",
    },
    "uk": {
        "similar_title": "Програмне забезпечення, схоже на {name}",
        "similar_desc": "Нижче наведено список програм, схожих на {name}.",
    },
}


def load_proprietary_catalog(data_dir: Path) -> List[Dict[str, Any]]:
    """加载商业软件目录。"""
    catalog_path = data_dir / "proprietary_catalog.json"
    if not catalog_path.exists():
        print(f"❌ catalog 不存在: {catalog_path}")
        return []
    with catalog_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_similar_index(catalog: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """按类别构建软件索引，便于快速查找同类软件。

    返回: {category: [software, ...]}
    """
    index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for sw in catalog:
        cat = sw.get("category", "unknown")
        index[cat].append(sw)
    return index


def find_similar_software(
    software: Dict[str, Any],
    catalog_index: Dict[str, List[Dict[str, Any]]],
    count: int = SIMILAR_COUNT,
) -> List[Dict[str, Any]]:
    """从同类软件中找出与给定软件最相似的其他软件。

    选择策略：
    1. 优先选择同类别软件（按字母顺序确保稳定）
    2. 排除自身
    3. 不够 5 个时，从其他类别补充

    返回 5 个软件的基本信息（id/name/similarity）。
    """
    sid = software["id"]
    category = software.get("category", "unknown")
    same_cat = [s for s in catalog_index.get(category, []) if s["id"] != sid]

    # 同类软件按 id 排序，保证稳定
    same_cat_sorted = sorted(same_cat, key=lambda x: x["id"])

    selected = same_cat_sorted[:count]

    # 不够 5 个时，从其他类别按字母顺序补充
    if len(selected) < count:
        deficit = count - len(selected)
        other_cats = sorted(
            [c for c in catalog_index.keys() if c != category]
        )
        for cat in other_cats:
            if deficit <= 0:
                break
            for s in sorted(catalog_index[cat], key=lambda x: x["id"]):
                if s["id"] != sid and s not in selected:
                    selected.append(s)
                    deficit -= 1
                    if deficit <= 0:
                        break

    # 构建 similar software 列表，similarity 基于位置递减
    similar_list: List[Dict[str, Any]] = []
    n = len(selected)
    for i, sw in enumerate(selected):
        # similarity 范围 0.95 → 0.70，按排名递减
        if n > 1:
            similarity = round(0.95 - (i / (n - 1)) * 0.25, 2)
        else:
            similarity = 0.95
        similar_list.append({
            "id": sw["id"],
            "name": sw.get("name", sw["id"]),
            "similarity": similarity,
        })
    return similar_list


def build_similar_record(
    software: Dict[str, Any],
    lang: str,
    similar_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """构建单条类似软件记录。"""
    sid = software["id"]
    sname = software.get("name", sid)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    templates = LANGUAGE_TEMPLATES.get(lang, LANGUAGE_TEMPLATES["zh"])
    title = templates["similar_title"].format(name=sname)
    description = templates["similar_desc"].format(name=sname)

    return {
        "id": f"{sid}-similar-{lang}",
        "softwareId": sid,
        "lang": lang,
        "title": title,
        "description": description,
        "similarSoftware": similar_list,
        "reviewStatus": "pending",
        "aiGenerated": True,
        "metadata": {
            "created": today,
            "sourceLang": "en",
        },
        "_meta": {
            "source": "ai-generated-mock",
            "schema_version": SCHEMA_VERSION,
            "unverified_fields": ["description", "similarSoftware"],
            "confidence": "medium",
        },
    }


def write_one_similar(
    out_dir: Path,
    software: Dict[str, Any],
    lang: str,
    similar_list: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """生成并写入单条类似软件数据，返回记录。"""
    record = build_similar_record(software, lang, similar_list)
    out_path = out_dir / f"{software['id']}-{lang}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return record


def run_generate_similar(data_dir: Path) -> List[Dict[str, Any]]:
    """生成所有类似软件数据（500×20=10,000条）。"""
    print("=" * 70)
    print("📋 OSSAF Pipeline - Step 7: 生成类似软件数据")
    print("=" * 70)

    catalog = load_proprietary_catalog(data_dir)
    if not catalog:
        print("❌ proprietary_catalog.json 为空，请先运行 collect_proprietary")
        return []

    out_dir = data_dir / "similar"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 预构建类别索引（一次构建，多次复用）
    catalog_index = build_similar_index(catalog)

    # 为每个软件预先计算 similar 列表（避免并发中重复计算）
    print(f"  软件数: {len(catalog)} | 语言数: {len(LANGUAGES)}")
    total = len(catalog) * len(LANGUAGES)
    print(f"  预期产出: {total} 条类似软件数据")

    t0 = time.time()

    # 为每个软件预计算 similar 列表
    similar_map: Dict[str, List[Dict[str, Any]]] = {}
    for sw in catalog:
        similar_map[sw["id"]] = find_similar_software(sw, catalog_index)

    # 构造所有任务
    tasks = [
        (out_dir, sw, lang, similar_map[sw["id"]])
        for sw in catalog
        for lang in LANGUAGES
    ]

    results: List[Dict[str, Any]] = []

    # 并发写入
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(write_one_similar, *task) for task in tasks
        ]
        for fut in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="生成类似软件",
            unit="条",
        ):
            results.append(fut.result())

    elapsed = time.time() - t0
    print(f"\n  ⏱️  耗时: {elapsed:.2f}s")
    print(f"  📊 生成结果: {len(results)}/{total} 条")
    print(f"  📁 输出目录: {out_dir}")
    return results


def main():
    parser = argparse.ArgumentParser(description="OSSAF Pipeline - 生成类似软件数据")
    parser.add_argument("--data-dir", default="data", help="数据目录")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    results = run_generate_similar(data_dir)
    print(f"\n✅ 类似软件数据生成完成: {len(results)} 条")


if __name__ == "__main__":
    main()
