#!/usr/bin/env python3
"""generate_hugo_content.py - 将 data/ 下的 JSON 数据转换为 Hugo content/ 下的 Markdown 文件

功能：
- 读取 data/use_cases/, data/similar/, data/alternative_list/ 下的 JSON 文件
- 转换为 content/{lang}/下的 Markdown 文件：
    * content/{lang}/use-cases/{software_id}-{scenario}.md
    * content/{lang}/similar/{software_id}.md
    * content/{lang}/alternatives/{software_id}.md
- 保留已存在的 content/{lang}/alternatives/{software_id}.md（不覆盖已审核内容）
- 使用 ThreadPoolExecutor 并发写入

用法：
  python3 scripts/generate_hugo_content.py
  python3 scripts/generate_hugo_content.py --max-workers 20
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 20 种目标语言（与 data/ 数据一致；en 不在数据中，由人工审核内容承载）
LANGUAGES = [
    "zh", "ja", "ko", "es",
    "de", "fr", "pt", "it", "ru", "ar",
    "nl", "pl", "tr", "id", "vi", "th",
    "hi", "bn", "ms", "uk",
]


def now_iso() -> str:
    """当前UTC日期 (YYYY-MM-DD)。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# =============================================================================
# Markdown 生成函数
# =============================================================================

def make_front_matter(params: Dict[str, Any]) -> str:
    """生成 YAML front matter。"""
    lines = ["---"]
    for key, value in params.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, (int, float)):
            lines.append(f"{key}: {value}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            # 字符串：用双引号包裹，转义内部双引号
            safe = str(value).replace('"', '\\"')
            lines.append(f'{key}: "{safe}"')
    lines.append("---")
    return "\n".join(lines)


def generate_use_case_md(record: Dict[str, Any]) -> str:
    """生成 use-case Markdown 文件内容。"""
    software_id = record.get("softwareId", "unknown")
    scenario = record.get("scenario", "unknown")
    title = record.get("title", f"{software_id} {scenario} use case")
    description = record.get("description", "")
    details = record.get("useCaseDetails", {}) or {}
    industry = details.get("industry", "")

    # tags 包含 software_id, scenario, industry 以便生成 taxonomy term pages
    tag_list = [software_id, scenario]
    if industry:
        tag_list.append(industry)

    # categories 包含 industry（如果有）
    cat_list = []
    if industry:
        cat_list.append(industry)

    front_matter_params = {
        "title": title,
        "date": now_iso(),
        "draft": False,
        "description": description,
        "aiGenerated": True,
        "reviewStatus": record.get("reviewStatus", "pending"),
        "softwareId": software_id,
        "scenario": scenario,
        "type": "use-case",
        "use-case": [scenario],  # 关联 use-case taxonomy
        "tags": tag_list,
    }
    if cat_list:
        front_matter_params["categories"] = cat_list

    body_lines = [
        f"# {title}",
        "",
        f"**{description}**",
        "",
        f"## Use Case Details",
        "",
        f"- **Industry**: {details.get('industry', '—')}",
        f"- **Users**: {details.get('users', '—')}",
        f"- **Workflow**: {details.get('workflow', '—')}",
        f"- **Benefits**: {details.get('benefits', '—')}",
        "",
        f"## Software",
        "",
        f"View [Open Source Alternatives for {software_id}](../../alternatives/{software_id}/) and [Similar Software to {software_id}](../../similar/{software_id}/).",
        "",
    ]

    return make_front_matter(front_matter_params) + "\n\n" + "\n".join(body_lines)


def generate_similar_md(record: Dict[str, Any]) -> str:
    """生成 similar Markdown 文件内容。"""
    software_id = record.get("softwareId", "unknown")
    title = record.get("title", f"Software similar to {software_id}")
    description = record.get("description", "")
    similar_list = record.get("similarSoftware", []) or []

    # 提取相似软件的 ID 列表，作为 similar-tax taxonomy 的 terms
    # 注：frontmatter 字段名必须使用 plural 形式（similar-tax），与 hugo.toml 配置一致
    similar_term_ids = []
    for item in similar_list:
        sim_id = item.get("softwareId") or item.get("id")
        if sim_id:
            similar_term_ids.append(sim_id)

    front_matter_params = {
        "title": title,
        "date": now_iso(),
        "draft": False,
        "description": description,
        "aiGenerated": True,
        "reviewStatus": record.get("reviewStatus", "pending"),
        "softwareId": software_id,
        "type": "similar-software",
        "tags": [software_id, "similar-software"],
        "similar-tax": similar_term_ids,  # 关联 similar-tax taxonomy（plural 形式）
    }

    body_lines = [
        f"# {title}",
        "",
        f"**{description}**",
        "",
        "## Similar Software",
        "",
        "| Software | Similarity |",
        "|----------|-----------|",
    ]
    for item in similar_list:
        name = item.get("name", "—")
        sim = item.get("similarity", 0)
        # 相似度百分比
        body_lines.append(f"| {name} | {sim * 100:.0f}% |")
    body_lines.append("")
    body_lines.append(f"## Software")
    body_lines.append("")
    body_lines.append(f"View [Open Source Alternatives for {software_id}](../../alternatives/{software_id}/).")
    body_lines.append("")

    return make_front_matter(front_matter_params) + "\n\n" + "\n".join(body_lines)


def generate_alternative_list_md(record: Dict[str, Any]) -> str:
    """生成 alternatives Markdown 文件内容。"""
    software_id = record.get("softwareId", "unknown")
    title = record.get("title", f"Open Source Alternatives to {software_id}")
    description = record.get("description", "")
    alternatives = record.get("alternatives", []) or []

    front_matter_params = {
        "title": title,
        "date": now_iso(),
        "draft": False,
        "description": description,
        "aiGenerated": True,
        "reviewStatus": record.get("reviewStatus", "pending"),
        "softwareId": software_id,
        "type": "alternative-list",
        "tags": [software_id, "alternative-list"],
    }

    body_lines = [
        f"# {title}",
        "",
        f"**{description}**",
        "",
        "## Open Source Alternatives",
        "",
        "| Open Source Software | Match Score | Reason |",
        "|---------------------|-------------|--------|",
    ]
    for alt in alternatives:
        name = alt.get("opensourceName", "—")
        score = alt.get("matchScore", 0)
        reason = alt.get("reason", "—")
        # 转义表格中的管道符
        reason_safe = reason.replace("|", "\\|")
        body_lines.append(f"| {name} | {score * 100:.0f}% | {reason_safe} |")
    body_lines.append("")
    body_lines.append("## Related Pages")
    body_lines.append("")
    body_lines.append(f"- [Similar Software to {software_id}](../../similar/{software_id}/)")
    body_lines.append("")

    return make_front_matter(front_matter_params) + "\n\n" + "\n".join(body_lines)


# =============================================================================
# 文件写入函数
# =============================================================================

def write_markdown_file(path: Path, content: str) -> None:
    """原子写入 Markdown 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def process_use_case(json_path: Path, content_dir: Path) -> Tuple[str, bool, str]:
    """处理单个 use_case JSON 文件，生成 Markdown。"""
    try:
        with json_path.open("r", encoding="utf-8") as f:
            record = json.load(f)
        software_id = record.get("softwareId", "unknown")
        scenario = record.get("scenario", "unknown")
        lang = record.get("lang", "unknown")
        if lang not in LANGUAGES:
            return (json_path.name, False, f"unsupported lang: {lang}")
        out_path = content_dir / lang / "use-cases" / f"{software_id}-{scenario}.md"
        md = generate_use_case_md(record)
        write_markdown_file(out_path, md)
        return (f"{lang}/use-cases/{software_id}-{scenario}.md", True, "")
    except Exception as exc:
        return (json_path.name, False, str(exc))


def process_similar(json_path: Path, content_dir: Path) -> Tuple[str, bool, str]:
    """处理单个 similar JSON 文件，生成 Markdown。"""
    try:
        with json_path.open("r", encoding="utf-8") as f:
            record = json.load(f)
        software_id = record.get("softwareId", "unknown")
        lang = record.get("lang", "unknown")
        if lang not in LANGUAGES:
            return (json_path.name, False, f"unsupported lang: {lang}")
        out_path = content_dir / lang / "similar" / f"{software_id}.md"
        md = generate_similar_md(record)
        write_markdown_file(out_path, md)
        return (f"{lang}/similar/{software_id}.md", True, "")
    except Exception as exc:
        return (json_path.name, False, str(exc))


def process_alternative_list(json_path: Path, content_dir: Path) -> Tuple[str, bool, str]:
    """处理单个 alternative_list JSON 文件，生成 Markdown。

    保留已存在的 content/{lang}/alternatives/{software_id}.md，不覆盖。
    """
    try:
        with json_path.open("r", encoding="utf-8") as f:
            record = json.load(f)
        software_id = record.get("softwareId", "unknown")
        lang = record.get("lang", "unknown")
        if lang not in LANGUAGES:
            return (json_path.name, False, f"unsupported lang: {lang}")
        out_path = content_dir / lang / "alternatives" / f"{software_id}.md"
        # 跳过已存在文件（保留人工审核的内容）
        if out_path.exists():
            return (f"{lang}/alternatives/{software_id}.md (skipped: exists)", True, "")
        md = generate_alternative_list_md(record)
        write_markdown_file(out_path, md)
        return (f"{lang}/alternatives/{software_id}.md", True, "")
    except Exception as exc:
        return (json_path.name, False, str(exc))


# =============================================================================
# 索引文件生成
# =============================================================================

USE_CASES_INDEX_BODY = """# Use Cases

Browse use case scenarios for commercial software. Each page describes how a software product is used in a specific context (professional, educational, or personal), including the industry, target users, workflow, and benefits.
"""

SIMILAR_INDEX_BODY = """# Similar Software

Browse similar software recommendations. Each page lists commercial software products that are similar to a given software, along with a similarity score to help you compare options.
"""

ALTERNATIVES_INDEX_BODY_EN = """# Commercial Software Alternatives

Browse commercial software and their open source alternatives. Each page lists recommended open source replacements with match scores and reasons.
"""

ALTERNATIVES_INDEX_BODY_ZH = """# 商业软件替代方案

浏览商业软件及其开源替代方案。每个页面列出推荐的开源替代品，附匹配分数和推荐理由。
"""


def ensure_section_indexes(content_dir: Path) -> int:
    """为所有语言创建/更新 section _index.md 文件，返回创建数量。"""
    created = 0
    # 所有语言（包括 en）
    all_langs = ["en"] + LANGUAGES
    for lang in all_langs:
        lang_dir = content_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)

        # 语言根 _index.md（如果不存在则创建一个最小的）
        lang_index = lang_dir / "_index.md"
        if not lang_index.exists():
            lang_title = {
                "en": "OSSAF - Open Source Alternative Finder",
                "zh": "OSSAF - 开源软件替代品查找器",
                "ja": "OSSAF - オープンソース代替ソフトウェア検索",
                "ko": "OSSAF - 오픈소스 대체 소프트웨어 찾기",
                "es": "OSSAF - Buscador de Alternativas de Código Abierto",
            }.get(lang, "OSSAF - Open Source Alternative Finder")
            lang_desc = {
                "en": "Find open source alternatives to commercial software",
                "zh": "查找商业软件的开源替代方案",
                "ja": "商用ソフトウェアのオープンソース代替を見つける",
                "ko": "상용 소프트웨어의 오픈소스 대안 찾기",
                "es": "Encuentra alternativas de código abierto al software comercial",
            }.get(lang, "Find open source alternatives to commercial software")
            fm = make_front_matter({
                "title": lang_title,
                "description": lang_desc,
                "aiGenerated": True,
                "reviewStatus": "approved",
            })
            lang_index.write_text(fm + "\n\nWelcome to OSSAF!\n", encoding="utf-8")
            created += 1

        # use-cases section index
        uc_dir = lang_dir / "use-cases"
        uc_dir.mkdir(parents=True, exist_ok=True)
        uc_index = uc_dir / "_index.md"
        if not uc_index.exists():
            fm = make_front_matter({
                "title": "Use Cases" if lang == "en" else "使用场景",
                "description": "Browse use case scenarios for commercial software." if lang == "en" else "浏览商业软件的使用场景。",
                "aiGenerated": True,
                "reviewStatus": "approved",
            })
            uc_index.write_text(fm + "\n\n" + USE_CASES_INDEX_BODY, encoding="utf-8")
            created += 1

        # similar section index
        sim_dir = lang_dir / "similar"
        sim_dir.mkdir(parents=True, exist_ok=True)
        sim_index = sim_dir / "_index.md"
        if not sim_index.exists():
            fm = make_front_matter({
                "title": "Similar Software" if lang == "en" else "类似软件",
                "description": "Browse similar software recommendations." if lang == "en" else "浏览类似软件推荐。",
                "aiGenerated": True,
                "reviewStatus": "approved",
            })
            sim_index.write_text(fm + "\n\n" + SIMILAR_INDEX_BODY, encoding="utf-8")
            created += 1

        # alternatives section index（仅当不存在时创建；en/zh/ja/ko/es 已有）
        alt_dir = lang_dir / "alternatives"
        alt_dir.mkdir(parents=True, exist_ok=True)
        alt_index = alt_dir / "_index.md"
        if not alt_index.exists():
            body = ALTERNATIVES_INDEX_BODY_ZH if lang != "en" else ALTERNATIVES_INDEX_BODY_EN
            fm = make_front_matter({
                "title": "商业软件替代方案" if lang != "en" else "Commercial Software Alternatives",
                "description": "查找商业软件的开源替代方案" if lang != "en" else "Find open source alternatives to commercial software",
                "aiGenerated": True,
                "reviewStatus": "approved",
            })
            alt_index.write_text(fm + "\n\n" + body, encoding="utf-8")
            created += 1

    return created


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


def process_directory(
    data_dir: Path,
    subdir: str,
    content_dir: Path,
    processor,
    max_workers: int,
    label: str,
) -> Tuple[int, int]:
    """并发处理目录下的所有 JSON 文件。"""
    src_dir = data_dir / subdir
    if not src_dir.exists():
        print(f"  ⚠️  目录不存在: {src_dir}")
        return (0, 0)

    json_files = sorted(src_dir.glob("*.json"))
    total = len(json_files)
    if total == 0:
        print(f"  ⚠️  目录为空: {src_dir}")
        return (0, 0)

    print(f"\n📂 {label}: {total} 个 JSON 文件")
    ok = 0
    fail = 0
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(processor, jf, content_dir): jf
            for jf in json_files
        }
        for future in as_completed(futures):
            _id, success, err = future.result()
            done += 1
            if success:
                ok += 1
            else:
                fail += 1
                if fail <= 3:
                    print(f"\n  ❌ {_id}: {err}")
            if done % 500 == 0 or done == total:
                print_progress(done, total, label)
    t1 = time.time()
    print(f"  ⏱️  {label} 耗时: {t1 - t0:.1f}s, 成功 {ok}, 失败 {fail}")
    return (ok, fail)


def main():
    parser = argparse.ArgumentParser(
        description="OSSAF Hugo Content 生成器 - 将 data/ 下的 JSON 转换为 content/ 下的 Markdown"
    )
    parser.add_argument("--data-dir", default="data", help="数据目录（默认 data）")
    parser.add_argument("--content-dir", default="content", help="内容输出目录（默认 content）")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=20,
        help="并发写入线程数（默认 20）",
    )
    args = parser.parse_args()

    data_dir = (PROJECT_ROOT / args.data_dir).resolve() if not Path(args.data_dir).is_absolute() else Path(args.data_dir)
    content_dir = (PROJECT_ROOT / args.content_dir).resolve() if not Path(args.content_dir).is_absolute() else Path(args.content_dir)

    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    content_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🚀 OSSAF Hugo Content 生成器")
    print("=" * 70)
    print(f"  数据目录: {data_dir}")
    print(f"  内容目录: {content_dir}")
    print(f"  并发数: {args.max_workers}")
    print(f"  支持语言: {len(LANGUAGES)} 种非英文")

    t_start = time.time()

    # 1. 生成 section _index.md 文件
    print("\n🗂️  [1/4] 创建 section 索引文件...")
    idx_created = ensure_section_indexes(content_dir)
    print(f"  ✅ 创建/确认 {idx_created} 个 _index.md 文件")

    # 2. 处理 use_cases
    print("\n🌐 [2/4] 处理 use_cases 数据...")
    uc_ok, uc_fail = process_directory(
        data_dir, "use_cases", content_dir, process_use_case, args.max_workers, "use-cases"
    )

    # 3. 处理 similar
    print("\n🔁 [3/4] 处理 similar 数据...")
    sim_ok, sim_fail = process_directory(
        data_dir, "similar", content_dir, process_similar, args.max_workers, "similar"
    )

    # 4. 处理 alternative_list
    print("\n🔀 [4/4] 处理 alternative_list 数据...")
    alt_ok, alt_fail = process_directory(
        data_dir, "alternative_list", content_dir, process_alternative_list, args.max_workers, "alternatives"
    )

    t_end = time.time()
    total_time = t_end - t_start

    # ====================== 红绿灯测试报告 ======================
    print("\n" + "=" * 70)
    print("📊 红绿灯测试 - Hugo Content 生成报告")
    print("=" * 70)

    total_ok = uc_ok + sim_ok + alt_ok
    total_fail = uc_fail + sim_fail + alt_fail
    expected = 30000 + 10000 + 10000

    print(f"\n[1] 文件数验证:")
    print(f"    use-cases:    成功 {uc_ok}, 失败 {uc_fail} (期望 30,000)")
    print(f"    similar:      成功 {sim_ok}, 失败 {sim_fail} (期望 10,000)")
    print(f"    alternatives: 成功 {alt_ok}, 失败 {alt_fail} (期望 10,000)")
    print(f"    索引文件:     创建/确认 {idx_created} 个 _index.md")
    if uc_ok == 30000 and sim_ok == 10000 and alt_ok == 10000:
        print("    ✅ PASS: 内容文件数量符合预期")
    else:
        print("    ❌ FAIL: 内容文件数量异常")

    print(f"\n[2] 性能验证:")
    print(f"    总耗时: {total_time:.1f}s ({total_time / 60:.1f}min)")
    if total_time <= 600:
        print(f"    ✅ PASS: ≤ 10 分钟")
    else:
        print(f"    ❌ FAIL: 超过 10 分钟")

    print(f"\n[3] 成功率:")
    print(f"    总成功: {total_ok}/{expected}")
    if total_fail == 0:
        print(f"    ✅ PASS: 全部成功")
    else:
        print(f"    ❌ FAIL: 有 {total_fail} 个失败")

    print(f"\n[4] 输出目录:")
    print(f"    - {content_dir}/{{lang}}/use-cases/*.md")
    print(f"    - {content_dir}/{{lang}}/similar/*.md")
    print(f"    - {content_dir}/{{lang}}/alternatives/*.md")
    print("=" * 70)


if __name__ == "__main__":
    main()
