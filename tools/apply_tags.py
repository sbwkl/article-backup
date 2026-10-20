#!/usr/bin/env python3
"""Phase 2/3: 把主题标签写回笔记 frontmatter，并生成主题页。

用法:
    # tags.json: {"20-文章/公众号/2020-01-01 xxx": ["02","05"], ...}
    python3 tools/apply_tags.py etf tags.json
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_wiki import INVESTORS, THEMES, get_themes, yaml_str  # noqa: E402
FM_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def norm_theme(x, num2name, name2num):
    x = str(x).strip()
    if x in num2name:
        return num2name[x]
    if x in name2num:
        return x
    if x.zfill(2) in num2name:
        return num2name[x.zfill(2)]
    return None


def set_theme(path: Path, themes):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(text)
    if not m:
        return False
    fm = m.group(1)
    items = ", ".join(yaml_str(t) for t in themes)
    newline = f"theme: [{items}]"
    if re.search(r"^theme:.*$", fm, re.M):
        fm2 = re.sub(r"^theme:.*$", newline, fm, flags=re.M)
    else:
        fm2 = fm + "\n" + newline
    path.write_text(f"---\n{fm2}\n---" + text[m.end():], encoding="utf-8")
    return True


def regen_theme_pages(vault: Path, themes):
    theme_map = {t: [] for t in themes}
    art = vault / "20-文章"
    for md in art.rglob("*.md"):
        if "_assets" in md.parts:
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        m = FM_RE.match(text)
        if not m:
            continue
        meta = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        raw = meta.get("theme", "")
        ts = re.findall(r'"([^"]+)"', raw) or re.findall(r"[^\[\],\s]+", raw.strip("[]"))
        ts = [t for t in ts if t in theme_map]
        if not ts:
            continue
        rel = md.relative_to(vault).with_suffix("").as_posix()
        for t in ts:
            theme_map[t].append((meta.get("date", ""), rel, meta.get("title", md.stem), meta.get("source", "")))

    for i, t in enumerate(themes, 1):
        nn = f"{i:02d}-{t}"
        items = sorted(theme_map.get(t, []), key=lambda e: e[0])
        lines = [
            "---",
            f"title: {yaml_str(t)}",
            "type: 主题",
            "---",
            "",
            f"# {t}",
            "",
            f"> 共 {len(items)} 篇。",
            "",
            "## 金句",
            "",
            "## 核心观点",
            "",
            "## 相关文章",
            "",
        ]
        for date, rel, title, src in reversed(items):
            lines.append(f"- {date or '—'}　[[{rel}\\|{title}]]　`{src}`")
        (vault / "10-主题" / f"{nn}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def regen_maps(vault: Path, counts_by_theme: dict, src_counts: dict, name: str, themes):
    lines = [f"# {name} · 主题地图\n", f"共 {len(themes)} 个一级主题。\n"]
    for i, t in enumerate(themes, 1):
        nn = f"{i:02d}-{t}"
        lines.append(f"{i}. [[10-主题/{nn}\\|{t}]]　`{counts_by_theme.get(t, 0)}`")
    (vault / "00-索引" / "主题地图.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    home = [f"# {name} · 知识库\n"]
    home.append("## 导览\n")
    home.append("- [[00-索引/主题地图\\|主题地图]]")
    home.append("- [[00-索引/时间线\\|时间线]]")
    home.append("- [[00-索引/来源说明\\|来源说明]]\n")
    home.append("## 一级主题\n")
    for i, t in enumerate(themes, 1):
        home.append(f"{i}. [[10-主题/{i:02d}-{t}\\|{t}]]　`{counts_by_theme.get(t, 0)}`")
    home.append("\n## 文章归档\n")
    for s, c in src_counts.items():
        home.append(f"- `20-文章/{s}/`（{c} 篇）")
    (vault / "主页.md").write_text("\n".join(home) + "\n", encoding="utf-8")


def main():
    inv, tags_file = sys.argv[1], sys.argv[2]
    cfg = INVESTORS[inv]
    vault = Path(__file__).resolve().parent.parent / "wiki" / cfg["name"]
    data = json.loads(Path(tags_file).read_text(encoding="utf-8"))

    themes = get_themes(cfg)
    num2name = {f"{i:02d}": t for i, t in enumerate(themes, 1)}
    name2num = {t: f"{i:02d}" for i, t in enumerate(themes, 1)}

    tagged = {}
    for rel, codes in data.items():
        rel = rel.removesuffix(".md")
        names = [norm_theme(x, num2name, name2num) for x in codes]
        names = [n for n in names if n]
        md = vault / "20-文章" / f"{rel}.md"
        if not md.exists():
            print(f"  缺失: {rel}")
            continue
        set_theme(md, names)
        tagged[rel] = names

    regen_theme_pages(vault, themes)

    from collections import Counter

    theme_counts = Counter()
    for names in tagged.values():
        for t in names:
            theme_counts[t] += 1
    src_counts = {}
    art = vault / "20-文章"
    for d in sorted(p for p in art.iterdir() if p.is_dir()):
        src_counts[d.name] = len(list(d.glob("*.md")))
    regen_maps(vault, theme_counts, src_counts, cfg["name"], themes)
    print(f"已写回 {len(tagged)} 篇，主题页/主题地图/主页已重建")


if __name__ == "__main__":
    main()
