#!/usr/bin/env python3
"""Phase 1: 把原始文章归档转换为 Obsidian vault 结构。

用法:
    python3 tools/build_wiki.py etf            # 处理 ETF拯救世界
    python3 tools/build_wiki.py etf --only weixin
    python3 tools/build_wiki.py jjc            # 处理 金渐成

产出:
    <投资人>/wiki/20-文章/<来源>/YYYY-MM-DD 标题.md
    <投资人>/wiki/20-文章/<来源>/_assets/...(图片)
"""
import argparse
import base64
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify

ROOT = Path(__file__).resolve().parent.parent

INVESTORS = {
    "etf": {
        "name": "ETF拯救世界",
        "author": "ETF拯救世界",
        "themes": "etf",
        "src": ROOT / "ETF拯救世界",
        "sources": {
            "weixin": "公众号",
            "qieman": "且慢社区",
            "weibo": "微博",
            "fache": "发车",
        },
    },
    "jjc": {
        "name": "金渐成",
        "author": "金渐成",
        "themes": "jjc",
        "src": ROOT / "金渐成",
        "sources": {
            "weixin": "公众号",
        },
    },
}

ILLEGAL = r'[\\/:*?"<>|\n\r\t]'


def sanitize_folder(name: str) -> str:
    """复现原站图片文件夹的命名规则: 去标点/空格, 转小写, 保留中英文数字。"""
    out = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
    return "".join(out)


def clean_filename(name: str) -> str:
    name = re.sub(ILLEGAL, "_", name).strip().strip(".")
    name = re.sub(r"\s+", " ", name)
    return name[:120] or "untitled"


def yaml_str(s: str) -> str:
    s = (s or "").replace('"', '\\"').replace("\n", " ")
    return f'"{s}"'


def parse_date_title(stem: str):
    """从文件名解析 (date, title)。支持 【YYYYMMDD】 / [YYYYMMDD] / 无日期。"""
    m = re.match(r"^[【\[](\d{8})[】\]]\s*(.*)$", stem)
    if m:
        d = m.group(1)
        date = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        title = m.group(2).strip().strip("_").strip()
        return date, title or stem
    return None, stem.strip().strip("_").strip() or stem


def frontmatter(title, date, source, url, author, tags):
    lines = ["---"]
    lines.append(f"title: {yaml_str(title)}")
    lines.append(f"date: {date or ''}")
    lines.append(f"source: {yaml_str(source)}")
    lines.append(f"source_url: {url or ''}")
    lines.append(f"author: {yaml_str(author)}")
    lines.append(f"theme: []")
    lines.append(f"tags: {tags}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


_SEEN = {}


def write_note(out_dir: Path, date, title, text):
    stem = clean_filename((f"{date} " if date else "") + title)
    key = (str(out_dir), stem)
    dup = _SEEN.get(key, 0)
    _SEEN[key] = dup + 1
    if dup:
        stem = f"{stem} ({dup + 1})"
    path = out_dir / f"{stem}.md"
    path.write_text(text, encoding="utf-8")
    return path


def copy_tree(src: Path, dst: Path):
    if src.exists():
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)


# ---------------------------------------------------------------- 公众号
IMG_LINK = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")


def process_weixin(cfg, only=None):
    name = cfg["name"]
    src = cfg["src"] / "mp.weixin.qq.com"
    vault = cfg["src"] / "wiki"
    out_dir = vault / "20-文章" / "公众号"
    assets_dir = out_dir / "_assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(src.glob("*.md"))
    n = 0
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        url, author = "", cfg["author"]
        body = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm, body = parts[1], parts[2]
                for line in fm.splitlines():
                    if line.startswith("source:"):
                        url = line.split(":", 1)[1].strip()
                    elif line.startswith("author:"):
                        author = line.split(":", 1)[1].strip() or author
        date, title = parse_date_title(f.stem)
        # 优先用正文一级标题
        m = re.search(r"^#\s+(.+)$", body, re.M)
        if m:
            title = m.group(1).strip()
        # 去掉 Excerpt 引用块
        body = re.sub(r"^>\s*##\s*Excerpt\s*\n(>.*\n)*", "", body, flags=re.M)
        body = body.strip()

        # 图片链接重写
        folder_cache = {}

        def repl(mm):
            alt, link = mm.group(1), mm.group(2)
            if link.startswith(("http://", "https://", "data:")):
                return mm.group(0)
            decoded = urllib.parse.unquote(link)
            parts = decoded.split("/")
            if len(parts) < 2:
                return mm.group(0)
            folder, filename = parts[-2], parts[-1]
            sfolder = sanitize_folder(folder)
            if sfolder not in folder_cache:
                s = src / folder
                if not s.exists():
                    cand = [d for d in src.iterdir() if d.is_dir() and sanitize_folder(d.name) == sfolder]
                    s = cand[0] if cand else None
                if s and s.exists():
                    dst = assets_dir / sfolder
                    copy_tree(s, dst)
                    folder_cache[sfolder] = True
                else:
                    folder_cache[sfolder] = False
            if folder_cache[sfolder]:
                return f"![{alt}](./_assets/{sfolder}/{filename})"
            return mm.group(0)

        body = IMG_LINK.sub(repl, body)

        fm = frontmatter(title, date, "公众号", url, author, "[来源/公众号]")
        write_note(out_dir, date, title, fm + body + "\n")
        n += 1
    print(f"[公众号] {n} 篇 -> {out_dir}")


# ---------------------------------------------------------------- 且慢
LOCAL_IMG = re.compile(r"(!\[[^\]]*\]\()([^)\s]+?\.(?:png|jpe?g|gif|webp))\)", re.I)


def process_qieman(cfg):
    name = cfg["name"]
    src = cfg["src"] / "qieman.com"
    vault = cfg["src"] / "wiki"
    out_dir = vault / "20-文章" / "且慢社区"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src.glob("*.md"))

    def fix_link(link):
        if link.startswith(("http://", "https://", "data:")):
            return None
        decoded = urllib.parse.unquote(link)
        candidates = [decoded]
        parts = decoded.split("/")
        if len(parts) > 1:
            candidates.append("assets/" + parts[-1])
        for c in candidates:
            srcfile = src / c
            if srcfile.exists():
                dst = out_dir / "_assets" / c
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    shutil.copy2(srcfile, dst)
                return "./_assets/" + c
        return None

    for f in files:
        raw = f.read_text(encoding="utf-8", errors="replace")
        date, title = parse_date_title(f.stem)
        if raw.lstrip().startswith("<"):
            soup = BeautifulSoup(raw, "html.parser")
            for img in soup.find_all("img"):
                fixed = fix_link(img.get("src", ""))
                if fixed:
                    img["src"] = fixed
            body = markdownify(str(soup), heading_style="ATX").strip()
        else:
            body = raw.strip()

        def repl(mm):
            fixed = fix_link(mm.group(2))
            return f"{mm.group(1)}{fixed})" if fixed else mm.group(0)

        body = LOCAL_IMG.sub(repl, body)
        fm = frontmatter(title, date, "且慢社区", "", cfg["author"], "[来源/且慢社区]")
        write_note(out_dir, date, title, fm + body + "\n")
    print(f"[且慢] {len(files)} 篇 -> {out_dir}")


# ---------------------------------------------------------------- 微博
POST_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\]\s*\((https?://[^)]+)\)\s*$", re.M)
IMG_RE = re.compile(r'<img[^>]*src="data:image/([a-zA-Z]+);base64,([^"]+)"[^>]*/?>')


def process_weibo(cfg):
    name = cfg["name"]
    src = cfg["src"] / "weibo.com"
    vault = cfg["src"] / "wiki"
    out_dir = vault / "20-文章" / "微博"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(src.glob("*.md"))
    if not files:
        return
    for f in files:
        raw = f.read_text(encoding="utf-8", errors="replace")
        ym = f.stem  # 202001
        month_dir = out_dir / "_assets" / ym
        counter = [0]

        def repl_img(mm):
            ext, data = mm.group(1), mm.group(2)
            ext = {"jpeg": "jpg", "png": "png", "gif": "gif", "webp": "webp"}.get(ext.lower(), ext.lower())
            month_dir.mkdir(parents=True, exist_ok=True)
            counter[0] += 1
            fn = f"{ym}-{counter[0]:03d}.{ext}"
            try:
                (month_dir / fn).write_bytes(base64.b64decode(data))
            except Exception:
                return ""
            return f"![](./_assets/{ym}/{fn})"

        raw = IMG_RE.sub(repl_img, raw)
        raw = raw.replace("<br />", "\n").replace("<br/>", "\n")
        raw = re.sub(r"<[^>]+>", "", raw)

        # 组装为按月笔记, 每条微博一个小节
        date = f"{ym[:4]}-{ym[4:6]}-01"
        lines = []
        pos = 0
        matches = list(POST_RE.finditer(raw))
        if not matches:
            lines.append(raw.strip())
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
            content = raw[m.end():end].strip()
            lines.append(f"## {m.group(1)} {m.group(2)}\n\n{content}\n")
        body = "\n".join(lines)
        fm = frontmatter(f"微博存档 {ym[:4]}-{ym[4:6]}", date, "微博", "", cfg["author"], "[来源/微博]")
        write_note(out_dir, None, f"微博存档 {ym[:4]}-{ym[4:6]}", fm + body + "\n")
    print(f"[微博] {len(files)} 个月 -> {out_dir}")


# ---------------------------------------------------------------- 发车
def process_fache(cfg):
    name = cfg["name"]
    src = cfg["src"] / "且慢发车"
    vault = cfg["src"] / "wiki"
    out_dir = vault / "20-文章" / "发车"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(src.glob("*.md"))
    for f in files:
        raw = f.read_text(encoding="utf-8", errors="replace").strip()
        date, title = parse_date_title(f.stem)
        fm = frontmatter(title, date, "发车", "", cfg["author"], "[来源/发车]")
        write_note(out_dir, date, title, fm + raw + "\n")
    print(f"[发车] {len(files)} 篇 -> {out_dir}")


SOURCE_FUNCS = {
    "weixin": process_weixin,
    "qieman": process_qieman,
    "weibo": process_weibo,
    "fache": process_fache,
}

THEMES = [
    "投资世界观与指数哲学",
    "风险、波动与极限生存",
    "估值、周期与位置",
    "资产配置与家庭财务",
    "定投、150份与长赢计划",
    "仓位、情绪与舒适区",
    "买卖策略与网格",
    "认知、人性与知行合一",
    "财富、消费与财务自由",
    "人生哲学、健康与幸福",
    "家庭、教育与亲密关系",
    "社会、历史与信息批判",
    "学习、写作与长期主义",
]

THEMES_JJC = [
    "美股投资与全球配置",
    "科技巨头与AI浪潮",
    "宏观、美元与利率",
    "交易纪律、仓位与负成本",
    "港股、A股与中国资产",
    "房产、土地与实物资产",
    "教育与亲子成长",
    "家庭、婚姻与代际关系",
    "健康、情绪与生活节奏",
    "创业、生意与助农",
    "认知、人性与决策",
    "社会、历史与时代观察",
    "年度总结与人生阶段",
]

THEME_SETS = {"etf": THEMES, "jjc": THEMES_JJC}


def get_themes(cfg):
    return THEME_SETS.get(cfg.get("themes", "etf"), THEMES)

FM_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def read_meta(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(text)
    meta = {"date": "", "source": "", "title": path.stem}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
    return meta


def build_indices(cfg):
    name = cfg["name"]
    themes = get_themes(cfg)
    vault = cfg["src"] / "wiki"
    art = vault / "20-文章"
    (vault / "00-索引").mkdir(parents=True, exist_ok=True)
    (vault / "10-主题").mkdir(parents=True, exist_ok=True)
    (vault / "30-语录").mkdir(parents=True, exist_ok=True)

    entries = []
    counts = {}
    for src_dir in sorted(p for p in art.iterdir() if p.is_dir()):
        srcname = src_dir.name
        n = 0
        for md in sorted(src_dir.glob("*.md")):
            meta = read_meta(md)
            rel = f"20-文章/{srcname}/{md.stem}"
            entries.append((meta["date"], srcname, md.stem, rel))
            n += 1
        counts[srcname] = n

    # 时间线
    entries.sort(key=lambda e: e[0] or "0000")
    lines = [f"# {name} · 时间线\n", f"共 {len(entries)} 篇。按发布日期倒序。\n"]
    cur_year = None
    for date, srcname, stem, rel in reversed(entries):
        year = (date or "未知")[:4]
        if year != cur_year:
            lines.append(f"\n## {year}\n")
            cur_year = year
        title = stem.split(" ", 1)[1] if " " in stem else stem
        lines.append(f"- {date or '—'}　[[{rel}\\|{title}]]　`{srcname}`")
    (vault / "00-索引" / "时间线.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 来源说明
    sl = [f"# {name} · 来源说明\n", "| 来源 | 篇数 | 目录 |", "| --- | --- | --- |"]
    for s, c in counts.items():
        sl.append(f"| {s} | {c} | `20-文章/{s}/` |")
    sl.append("")
    (vault / "00-索引" / "来源说明.md").write_text("\n".join(sl), encoding="utf-8")

    # 主题页骨架 + 主题地图
    maplines = [f"# {name} · 主题地图\n", f"共 {len(themes)} 个一级主题。\n"]
    for i, t in enumerate(themes, 1):
        nn = f"{i:02d}-{t}"
        (vault / "10-主题" / f"{nn}.md").write_text(
            f"---\ntitle: {yaml_str(t)}\ntype: 主题\n---\n\n# {t}\n\n> 待 Phase 2 填充：金句 / 核心观点 / 相关文章双链。\n\n## 金句\n\n## 核心观点\n\n## 相关文章\n",
            encoding="utf-8",
        )
        maplines.append(f"{i}. [[10-主题/{nn}\\|{t}]]")
    (vault / "00-索引" / "主题地图.md").write_text("\n".join(maplines) + "\n", encoding="utf-8")

    # 主页
    home = [f"# {name} · 知识库\n"]
    home.append("## 导览\n")
    home.append("- [[00-索引/主题地图\\|主题地图]]")
    home.append("- [[00-索引/时间线\\|时间线]]")
    home.append("- [[00-索引/来源说明\\|来源说明]]\n")
    home.append("## 一级主题\n")
    for i, t in enumerate(themes, 1):
        home.append(f"{i}. [[10-主题/{i:02d}-{t}\\|{t}]]")
    home.append("\n## 文章归档\n")
    for s, c in counts.items():
        home.append(f"- `20-文章/{s}/`（{c} 篇）")
    (vault / "主页.md").write_text("\n".join(home) + "\n", encoding="utf-8")
    print(f"[索引] 时间线/来源/主题地图/主页 已生成；文章 {len(entries)} 篇")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("investor", choices=list(INVESTORS))
    ap.add_argument("--only", help="只处理某个来源 key")
    args = ap.parse_args()

    cfg = INVESTORS[args.investor]
    keys = [args.only] if args.only else list(cfg["sources"])
    for k in keys:
        fn = SOURCE_FUNCS.get(k)
        if not fn:
            print(f"未知来源 {k}", file=sys.stderr)
            continue
        fn(cfg)
    if not args.only:
        build_indices(cfg)


if __name__ == "__main__":
    main()
