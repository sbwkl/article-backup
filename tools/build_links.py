#!/usr/bin/env python3
"""生成 wiki 索引：主题页 / 时间线 / 来源说明 / 主题地图 / 主页。

wiki 不再保存文章存根，所有链接直接指向原始归档。
用法:
    python3 tools/build_links.py etf
    python3 tools/build_links.py jjc
    python3 tools/build_links.py all --prune
"""
import argparse
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_wiki import INVESTORS, ROOT, get_themes, yaml_str  # noqa: E402

FM_RE = re.compile(r"^---\n(.*?)\n---", re.S)
KEY_RE = re.compile(r"^([A-Za-z_]+):[ \t]*(.*)$", re.M)
QUOTED_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')

SOURCE_DIRS = {
    "etf": {
        "qieman.com": "且慢社区",
        "mp.weixin.qq.com": "公众号",
        "weibo.com": "微博",
        "且慢发车": "发车",
    },
    "jjc": {"mp.weixin.qq.com": "公众号"},
}


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        v = v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return v


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(text)
    meta = {}
    if m:
        for k, v in KEY_RE.findall(m.group(1)):
            meta[k] = v
    return meta


def scan(cfg, dirs):
    items = []
    for folder, label in dirs.items():
        d = cfg["src"] / folder
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            meta = read_frontmatter(p)
            raw_theme = meta.get("theme", "")
            themes = [t.replace('\\"', '"') for t in QUOTED_RE.findall(raw_theme)]
            items.append({
                "path": p,
                "rel": p.relative_to(ROOT).as_posix(),
                "source": label,
                "date": meta.get("date", "").strip(),
                "title": unquote(meta.get("title", "")) or p.stem,
                "themes": themes,
            })
    items.sort(key=lambda x: (x["date"] or "0000", x["rel"]))
    return items


def link(page_dir: Path, target: Path, title: str):
    rel = os.path.relpath(target, page_dir).replace(os.sep, "/")
    safe = title.replace("[", "\\[").replace("]", "\\]")
    return f"[{safe}](<{rel}>)"


def build_one(key, cfg, prune=False):
    name = cfg["name"]
    vault = cfg["src"] / "wiki"
    themes = get_themes(cfg)
    items = scan(cfg, SOURCE_DIRS[key])
    theme_dir = vault / "10-主题"
    index_dir = vault / "00-索引"
    theme_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    (vault / "30-语录").mkdir(exist_ok=True)

    by_theme = defaultdict(list)
    for it in items:
        known = [t for t in it["themes"] if t in themes]
        it["themes"] = known
        for t in known:
            by_theme[t].append(it)

    # 主题页
    for i, t in enumerate(themes, 1):
        rows = sorted(by_theme[t], key=lambda x: x["date"])
        lines = [
            "---",
            f"title: {yaml_str(t)}",
            "type: 主题",
            "---",
            "",
            f"# {t}",
            "",
            f"> 共 {len(rows)} 篇。",
            "",
            "## 金句",
            "",
            "## 核心观点",
            "",
            "## 相关文章",
            "",
        ]
        for it in reversed(rows):
            lines.append(
                f"- {it['date'] or '—'}　{link(theme_dir, it['path'], it['title'])}　`{it['source']}`"
            )
        (theme_dir / f"{i:02d}-{t}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 时间线
    lines = [f"# {name} · 时间线\n", f"共 {len(items)} 篇。按发布日期倒序。\n"]
    cur = None
    for it in reversed(items):
        year = (it["date"] or "未知")[:4]
        if year != cur:
            lines.append(f"\n## {year}\n")
            cur = year
        lines.append(
            f"- {it['date'] or '—'}　{link(index_dir, it['path'], it['title'])}　`{it['source']}`"
        )
    (index_dir / "时间线.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 来源说明
    src_counts = Counter(it["source"] for it in items)
    sl = [f"# {name} · 来源说明\n", "| 来源 | 篇数 | 目录 |", "| --- | --- | --- |"]
    for folder, label in SOURCE_DIRS[key].items():
        sl.append(f"| {label} | {src_counts.get(label, 0)} | `{folder}/` |")
    (index_dir / "来源说明.md").write_text("\n".join(sl) + "\n", encoding="utf-8")

    # 主题地图
    maplines = [f"# {name} · 主题地图\n", f"共 {len(themes)} 个一级主题。\n"]
    for i, t in enumerate(themes, 1):
        maplines.append(f"{i}. [[10-主题/{i:02d}-{t}\\|{t}]]　`{len(by_theme[t])}`")
    (index_dir / "主题地图.md").write_text("\n".join(maplines) + "\n", encoding="utf-8")

    # 主页
    home = [f"# {name} · 知识库\n", "## 导览\n"]
    home.append("- [[00-索引/主题地图\\|主题地图]]")
    home.append("- [[00-索引/时间线\\|时间线]]")
    home.append("- [[00-索引/来源说明\\|来源说明]]\n")
    home.append("## 一级主题\n")
    for i, t in enumerate(themes, 1):
        home.append(f"{i}. [[10-主题/{i:02d}-{t}\\|{t}]]　`{len(by_theme[t])}`")
    home.append("\n## 文章归档\n")
    for folder, label in SOURCE_DIRS[key].items():
        c = src_counts.get(label, 0)
        home.append(f"- `{folder}/`（{label} {c} 篇）")
    (vault / "主页.md").write_text("\n".join(home) + "\n", encoding="utf-8")

    if prune:
        art = vault / "20-文章"
        if art.exists():
            shutil.rmtree(art)
            print(f"[{name}] 已删除 20-文章 存根")

    print(
        f"[{name}] 文章 {len(items)} 篇，主题归属 {sum(len(v) for v in by_theme.values())} 条，"
        f"主题页 {len(themes)} 个"
    )
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("investor", choices=[*INVESTORS, "all"])
    ap.add_argument("--prune", action="store_true", help="删除 20-文章 存根目录")
    args = ap.parse_args()
    keys = list(INVESTORS) if args.investor == "all" else [args.investor]
    for k in keys:
        build_one(k, INVESTORS[k], args.prune)


if __name__ == "__main__":
    main()
