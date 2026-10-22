#!/usr/bin/env python3
"""从且慢抓取 ETF 拯救世界的新文章，写入原始归档。

用法:
    python3 tools/import_qieman.py            # 抓取并写入
    python3 tools/import_qieman.py --dry-run  # 只打印，不写文件
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_wiki import INVESTORS, clean_filename, frontmatter  # noqa: E402

API = (
    "https://qieman.com/pmdj/v2/community/space/userCenterPost/list"
    "?pageNum={page}&pageSize=100&postType=1&spaceUserId={uid}"
)
SPACE_ID = "793413"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
POST_URL = "https://qieman.com/content/content-detail?postId={id}"


def fetch(page):
    req = urllib.request.Request(
        API.format(page=page, uid=SPACE_ID), headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def existing_urls(src):
    urls = set()
    for p in src.glob("*.md"):
        t = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^source_url:[ \t]*(.*)$", t, re.M)
        if m:
            urls.add(m.group(1).strip())
    return urls


def first_title(content):
    for block in content.get("contents") or []:
        if block.get("contentType") != 1:
            continue
        for line in (block.get("detail") or "").splitlines():
            line = line.strip()
            if line:
                return line.rstrip("。").strip()
    return ""


def download(url, assets):
    name = Path(urllib.parse.urlparse(url).path).name
    if not name:
        return None
    if not Path(name).suffix:
        name += ".png"
    dst = assets / name
    if not dst.exists():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            dst.write_bytes(r.read())
    return name


def render(content, assets, title):
    parts = []
    for block in content.get("contents") or []:
        typ = block.get("contentType")
        detail = (block.get("detail") or "").strip()
        if typ == 1 and detail:
            parts.append(detail)
        elif typ == 2 and detail:
            name = download(detail, assets)
            if name:
                parts.append(f"![](assets/{name})")
    body = "\n\n".join(parts).strip()
    if not body:
        body = title
    return body


def write_post(src, assets, cfg, title, day, body, post_id):
    out = src / f"【{day.replace('-', '')}】{clean_filename(title)}.md"
    n = 1
    while out.exists():
        n += 1
        out = src / f"【{day.replace('-', '')}】{clean_filename(title)} ({n}).md"
    text = frontmatter(
        title, day, "且慢社区", POST_URL.format(id=post_id), cfg["author"], "[来源/且慢社区]"
    )
    out.write_text(text + body + "\n", encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("investor", nargs="?", default="etf", choices=["etf"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = INVESTORS[args.investor]
    src = cfg["src"] / "qieman.com"
    assets = src / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    known = existing_urls(src)

    days = []
    for p in src.glob("【*.md"):
        m = re.match(r"【(\d{8})】", p.name)
        if m:
            days.append(m.group(1))
    cutoff = (
        date(int(max(days)[:4]), int(max(days)[4:6]), int(max(days)[6:]))
        - timedelta(days=3)
        if days
        else date(2000, 1, 1)
    )

    new = []
    page = 1
    while True:
        items = fetch(page)
        if not items:
            break
        oldest = None
        for it in items:
            day = it["createdAt"][:10]
            oldest = day
            url = POST_URL.format(id=it["id"])
            if url in known:
                continue
            if date.fromisoformat(day) < cutoff:
                continue
            new.append((it, day))
        if oldest and date.fromisoformat(oldest) < cutoff:
            break
        page += 1
        if page > 20:
            break

    new.sort(key=lambda x: x[0]["createdAt"])
    print(f"发现 {len(new)} 篇新文章")
    for it, day in new:
        title = first_title(it["content"]) or f"且慢动态 {day}"
        print(f"  {day} {title}")
        if args.dry_run:
            continue
        body = render(it["content"], assets, title)
        path = write_post(src, assets, cfg, title, day, body, it["id"])
        print(f"    -> {path.relative_to(cfg['src'].parent)}")


if __name__ == "__main__":
    main()
