#!/usr/bin/env python3
"""generate_alternative_list.py - 生成开源替代方案列表Mock数据

功能：
- 为每个商业软件列出对应的开源替代品（基于opensource_catalog的proprietaryAlternativeId）
- 每个软件20种语言的描述
- 总数据量：500软件 × 20语言 = 10,000条
- 输出到 data/alternative_list/{software_id}-{lang}.json

用法：
  python3 -m pipeline.generate_alternative_list
  python3 -m pipeline.generate_alternative_list --data-dir data
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

# 每个商业软件最多列出的开源替代品数量
MAX_ALTERNATIVES = 5

# 多语言模板（title/desc 中支持 {name} 占位符；reason 中支持 {category} 占位符）
LANGUAGE_TEMPLATES = {
    "zh": {
        "alt_title": "{name} 的开源替代方案",
        "alt_desc": "以下是 {name} 的开源替代方案列表，可免费使用且社区活跃。",
        "reason_primary": "官方推荐的开源替代品，功能与 {name} 高度匹配",
        "reason_secondary": "同类开源软件，可作为备选方案",
    },
    "ja": {
        "alt_title": "{name} のオープンソース代替方案",
        "alt_desc": "以下は {name} のオープンソース代替方案のリストです。無料で利用でき、コミュニティも活発です。",
        "reason_primary": "公式推奨のオープンソース代替品で、{name} と機能が高度に一致",
        "reason_secondary": "同カテゴリのオープンソースソフトウェアで、代替案として利用可能",
    },
    "ko": {
        "alt_title": "{name} 의 오픈소스 대안",
        "alt_desc": "다음은 {name} 의 오픈소스 대안 목록입니다. 무료로 사용할 수 있고 커뮤니티가 활성화되어 있습니다.",
        "reason_primary": "공식 추천 오픈소스 대안으로 {name} 과 기능이高度로 일치",
        "reason_secondary": "같은 카테고리의 오픈소스 소프트웨어로 대안으로 사용 가능",
    },
    "es": {
        "alt_title": "Alternativas de código abierto para {name}",
        "alt_desc": "A continuación se muestra una lista de alternativas de código abierto para {name}, gratuitas y con comunidad activa.",
        "reason_primary": "Alternativa de código abierto recomendada oficialmente, altamente compatible con {name}",
        "reason_secondary": "Software de código abierto de la misma categoría, disponible como opción alternativa",
    },
    "de": {
        "alt_title": "Open-Source-Alternativen zu {name}",
        "alt_desc": "Nachfolgend finden Sie eine Liste von Open-Source-Alternativen zu {name}, die kostenlos sind und eine aktive Community haben.",
        "reason_primary": "Offiziell empfohlene Open-Source-Alternative, stark kompatibel mit {name}",
        "reason_secondary": "Open-Source-Software derselben Kategorie, als Alternative verfügbar",
    },
    "fr": {
        "alt_title": "Alternatives open-source pour {name}",
        "alt_desc": "Voici une liste d'alternatives open-source pour {name}, gratuites avec une communauté active.",
        "reason_primary": "Alternative open-source officiellement recommandée, hautement compatible avec {name}",
        "reason_secondary": "Logiciel open-source de même catégorie, disponible comme alternative",
    },
    "pt": {
        "alt_title": "Alternativas de código aberto para {name}",
        "alt_desc": "Abaixo está uma lista de alternativas de código aberto para {name}, gratuitas e com comunidade ativa.",
        "reason_primary": "Alternativa de código aberto oficialmente recomendada, altamente compatível com {name}",
        "reason_secondary": "Software de código aberto da mesma categoria, disponível como alternativa",
    },
    "it": {
        "alt_title": "Alternative open source per {name}",
        "alt_desc": "Di seguito è riportato un elenco di alternative open source per {name}, gratuite e con community attiva.",
        "reason_primary": "Alternativa open source ufficialmente consigliata, altamente compatibile con {name}",
        "reason_secondary": "Software open source della stessa categoria, disponibile come alternativa",
    },
    "ru": {
        "alt_title": "Открытые альтернативы для {name}",
        "alt_desc": "Ниже приведен список открытых альтернатив для {name}, бесплатных и с активным сообществом.",
        "reason_primary": "Официально рекомендованная открытая альтернатива, высоко совместимая с {name}",
        "reason_secondary": "Открытое ПО той же категории, доступное как альтернатива",
    },
    "ar": {
        "alt_title": "بدائل مفتوحة المصدر لـ {name}",
        "alt_desc": "فيما يلي قائمة بالبدائل مفتوحة المصدر لـ {name}، مجانية ومجتمع نشط.",
        "reason_primary": "بديل مفتوح المصدر موصى به رسميًا، متوافق تمامًا مع {name}",
        "reason_secondary": "برنامج مفتوح المصدر من نفس الفئة، متاح كبديل",
    },
    "nl": {
        "alt_title": "Open-source alternatieven voor {name}",
        "alt_desc": "Hieronder staat een lijst met open-source alternatieven voor {name}, gratis en met actieve community.",
        "reason_primary": "Officieel aanbevolen open-source alternatief, sterk compatibel met {name}",
        "reason_secondary": "Open-source software van dezelfde categorie, beschikbaar als alternatief",
    },
    "pl": {
        "alt_title": "Alternatywy open-source dla {name}",
        "alt_desc": "Poniżej znajduje się lista alternatyw open-source dla {name}, darmowych z aktywną społecznością.",
        "reason_primary": "Oficjalnie polecana alternatywa open-source, wysoć zgodna z {name}",
        "reason_secondary": "Oprogramowanie open-source tej samej kategorii, dostępne jako alternatywa",
    },
    "tr": {
        "alt_title": "{name} için açık kaynak alternatifler",
        "alt_desc": "Aşağıda {name} için açık kaynak alternatiflerin bir listesi bulunmaktadır. Ücretsizdir ve aktif topluluğu vardır.",
        "reason_primary": "Resmi olarak önerilen açık kaynak alternatifi, {name} ile高度 uyumlu",
        "reason_secondary": "Aynı kategorideki açık kaynak yazılım, alternatif olarak kullanılabilir",
    },
    "id": {
        "alt_title": "Alternatif open-source untuk {name}",
        "alt_desc": "Berikut adalah daftar alternatif open-source untuk {name}, gratis dengan komunitas aktif.",
        "reason_primary": "Alternatif open-source yang direkomendasikan secara resmi, sangat kompatibel dengan {name}",
        "reason_secondary": "Perangkat lunak open-source dari kategori yang sama, tersedia sebagai alternatif",
    },
    "vi": {
        "alt_title": "Các giải pháp thay thế mã nguồn mở cho {name}",
        "alt_desc": "Dưới đây là danh sách các giải pháp thay thế mã nguồn mở cho {name}, miễn phí và có cộng đồng tích cực.",
        "reason_primary": "Giải pháp thay thế mã nguồn mở được đề xuất chính thức, tương thích cao với {name}",
        "reason_secondary": "Phần mềm mã nguồn mở cùng danh mục, có sẵn như một giải pháp thay thế",
    },
    "th": {
        "alt_title": "ทางเลือกโอเพ่นซอร์สสำหรับ {name}",
        "alt_desc": "ด้านล่างนี้คือรายการทางเลือกโอเพ่นซอร์สสำหรับ {name} ฟรีและมีชุมชนที่ใช้งานอยู่",
        "reason_primary": "ทางเลือกโอเพ่นซอร์สที่แนะนำอย่างเป็นทางการ เข้ากันได้สูงกับ {name}",
        "reason_secondary": "ซอฟต์แวร์โอเพ่นซอร์สในหมวดหมู่เดียวกัน มีให้เลือกใช้เป็นทางเลือก",
    },
    "hi": {
        "alt_title": "{name} के लिए ओपन-सोर्स विकल्प",
        "alt_desc": "नीचे {name} के लिए ओपन-सोर्स विकल्पों की सूची दी गई है, निःशुल्क और सक्रिय समुदाय के साथ।",
        "reason_primary": "आधिकारिक रूप से अनुशंसित ओपन-सोर्स विकल्प, {name} के साथ अत्यधिक संगत",
        "reason_secondary": "समान श्रेणी का ओपन-सोर्स सॉफ़्टवेयर, विकल्प के रूप में उपलब्ध",
    },
    "bn": {
        "alt_title": "{name} এর জন্য ওপেন-সোর্স বিকল্প",
        "alt_desc": "নিচে {name} এর জন্য ওপেন-সোর্স বিকল্পগুলির একটি তালিকা দেওয়া হলো, বিনামূল্যে এবং সক্রিয় কমিউনিটি সহ।",
        "reason_primary": "অফিসিয়ালি সুপারিশকৃত ওপেন-সোর্স বিকল্প, {name} এর সাথে অত্যন্ত সামঞ্জস্যপূর্ণ",
        "reason_secondary": "একই বিভাগের ওপেন-সোর্স সফ্টওয়্যার, বিকল্প হিসাবে উপলব্ধ",
    },
    "ms": {
        "alt_title": "Alternatif sumber terbuka untuk {name}",
        "alt_desc": "Berikut ialah senarai alternatif sumber terbuka untuk {name}, percuma dengan komuniti aktif.",
        "reason_primary": "Alternatif sumber terbuka yang disyorkan secara rasmi, serasi tinggi dengan {name}",
        "reason_secondary": "Perisian sumber terbuka dari kategori yang sama, tersedia sebagai alternatif",
    },
    "uk": {
        "alt_title": "Відкриті альтернативи для {name}",
        "alt_desc": "Нижче наведено список відкритих альтернатив для {name}, безкоштовних з активною спільнотою.",
        "reason_primary": "Офіційно рекомендована відкрита альтернатива, високо сумісна з {name}",
        "reason_secondary": "Відкрите ПЗ тієї ж категорії, доступне як альтернатива",
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


def load_opensource_catalog(data_dir: Path) -> List[Dict[str, Any]]:
    """加载开源软件目录。"""
    catalog_path = data_dir / "opensource_catalog.json"
    if not catalog_path.exists():
        print(f"❌ catalog 不存在: {catalog_path}")
        return []
    with catalog_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_alternative_index(
    opensource_catalog: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """构建 {proprietary_id: opensource} 映射（基于 proprietaryAlternativeId）。

    返回: {proprietary_id: opensource_entry}
    """
    index: Dict[str, Dict[str, Any]] = {}
    for os_sw in opensource_catalog:
        pid = os_sw.get("proprietaryAlternativeId")
        if pid:
            index[pid] = os_sw
    return index


def build_opensource_category_index(
    opensource_catalog: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """按类别构建开源软件索引。

    返回: {category: [opensource, ...]}
    """
    index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for os_sw in opensource_catalog:
        cat = os_sw.get("category", "unknown")
        index[cat].append(os_sw)
    return index


def find_alternatives(
    software: Dict[str, Any],
    primary_map: Dict[str, Dict[str, Any]],
    category_index: Dict[str, List[Dict[str, Any]]],
    max_count: int = MAX_ALTERNATIVES,
) -> List[Dict[str, Any]]:
    """查找商业软件的开源替代品。

    策略：
    1. 优先包含 primary_map 中映射的开源软件（matchScore=0.95）
    2. 同类别下的其他开源软件作为次选（matchScore 0.70~0.85）
    3. 总数不超过 max_count（默认 5）

    返回: [{opensourceId, opensourceName, matchScore, reason_key}, ...]
    其中 reason_key 用于后续根据语言生成 reason 文本（"primary" 或 "secondary"）。
    """
    sid = software["id"]
    category = software.get("category", "unknown")
    alternatives: List[Dict[str, Any]] = []

    # 主选：基于 proprietaryAlternativeId 映射的开源软件
    primary = primary_map.get(sid)
    if primary:
        alternatives.append({
            "opensourceId": primary["id"],
            "opensourceName": primary.get("name", primary["id"]),
            "matchScore": 0.95,
            "reason_key": "primary",
        })

    # 次选：同类别下的其他开源软件（排除已选作主选的）
    same_cat = [
        s for s in category_index.get(category, [])
        if not primary or s["id"] != primary["id"]
    ]
    same_cat_sorted = sorted(same_cat, key=lambda x: x["id"])

    # 计算 matchScore：0.85 → 0.70 递减
    secondary_count = max_count - len(alternatives)
    for i, os_sw in enumerate(same_cat_sorted[:secondary_count]):
        if secondary_count > 1:
            score = round(0.85 - (i / (secondary_count - 1)) * 0.15, 2)
        else:
            score = 0.85
        alternatives.append({
            "opensourceId": os_sw["id"],
            "opensourceName": os_sw.get("name", os_sw["id"]),
            "matchScore": score,
            "reason_key": "secondary",
        })

    return alternatives


def build_alternative_list_record(
    software: Dict[str, Any],
    lang: str,
    alternatives: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """构建单条开源替代方案列表记录。"""
    sid = software["id"]
    sname = software.get("name", sid)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    templates = LANGUAGE_TEMPLATES.get(lang, LANGUAGE_TEMPLATES["zh"])
    title = templates["alt_title"].format(name=sname)
    description = templates["alt_desc"].format(name=sname)

    # 构建 alternatives 列表（含本地化的 reason 文本）
    alt_list: List[Dict[str, Any]] = []
    for alt in alternatives:
        reason_template = templates[f"reason_{alt['reason_key']}"]
        reason = reason_template.format(name=sname)
        alt_list.append({
            "opensourceId": alt["opensourceId"],
            "opensourceName": alt["opensourceName"],
            "matchScore": alt["matchScore"],
            "reason": reason,
        })

    return {
        "id": f"{sid}-alternatives-{lang}",
        "softwareId": sid,
        "lang": lang,
        "title": title,
        "description": description,
        "alternatives": alt_list,
        "reviewStatus": "pending",
        "aiGenerated": True,
        "metadata": {
            "created": today,
            "sourceLang": "en",
        },
        "_meta": {
            "source": "ai-generated-mock",
            "schema_version": SCHEMA_VERSION,
            "unverified_fields": ["description", "alternatives"],
            "confidence": "medium",
        },
    }


def write_one_alternative_list(
    out_dir: Path,
    software: Dict[str, Any],
    lang: str,
    alternatives: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """生成并写入单条替代方案列表数据，返回记录。"""
    record = build_alternative_list_record(software, lang, alternatives)
    out_path = out_dir / f"{software['id']}-{lang}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return record


def run_generate_alternative_list(data_dir: Path) -> List[Dict[str, Any]]:
    """生成所有开源替代方案列表数据（500×20=10,000条）。"""
    print("=" * 70)
    print("📋 OSSAF Pipeline - Step 8: 生成替代方案列表数据")
    print("=" * 70)

    catalog = load_proprietary_catalog(data_dir)
    if not catalog:
        print("❌ proprietary_catalog.json 为空，请先运行 collect_proprietary")
        return []

    opensource_catalog = load_opensource_catalog(data_dir)
    if not opensource_catalog:
        print("❌ opensource_catalog.json 为空，请检查数据")
        return []

    out_dir = data_dir / "alternative_list"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 预构建索引
    primary_map = build_alternative_index(opensource_catalog)
    category_index = build_opensource_category_index(opensource_catalog)

    print(f"  商业软件数: {len(catalog)} | 开源软件数: {len(opensource_catalog)}")
    print(f"  主映射条目数: {len(primary_map)} | 语言数: {len(LANGUAGES)}")
    total = len(catalog) * len(LANGUAGES)
    print(f"  预期产出: {total} 条替代方案列表数据")

    t0 = time.time()

    # 为每个软件预计算 alternatives 列表
    alt_map: Dict[str, List[Dict[str, Any]]] = {}
    for sw in catalog:
        alt_map[sw["id"]] = find_alternatives(sw, primary_map, category_index)

    # 构造所有任务
    tasks = [
        (out_dir, sw, lang, alt_map[sw["id"]])
        for sw in catalog
        for lang in LANGUAGES
    ]

    results: List[Dict[str, Any]] = []

    # 并发写入
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(write_one_alternative_list, *task) for task in tasks
        ]
        for fut in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="生成替代方案",
            unit="条",
        ):
            results.append(fut.result())

    elapsed = time.time() - t0
    print(f"\n  ⏱️  耗时: {elapsed:.2f}s")
    print(f"  📊 生成结果: {len(results)}/{total} 条")
    print(f"  📁 输出目录: {out_dir}")
    return results


def main():
    parser = argparse.ArgumentParser(description="OSSAF Pipeline - 生成替代方案列表数据")
    parser.add_argument("--data-dir", default="data", help="数据目录")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    results = run_generate_alternative_list(data_dir)
    print(f"\n✅ 替代方案列表数据生成完成: {len(results)} 条")


if __name__ == "__main__":
    main()
