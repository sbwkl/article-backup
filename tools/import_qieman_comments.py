#!/usr/bin/env python3
"""抓取且慢文章评论，精选后附到原文底部。

用法:
    python3 tools/import_qieman_comments.py            # 处理最近 30 天
    python3 tools/import_qieman_comments.py --days 7
    python3 tools/import_qieman_comments.py --dry-run
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_wiki import INVESTORS  # noqa: E402

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
BASE = "https://qieman.com/pmdj/v2"
AUTHOR_ID = "793413"
START = "<!-- qieman-comments:start -->"
END = "<!-- qieman-comments:end -->"
PAGE_SIZE = 100

LOTTERY = re.compile(
    r"求中|抽我|抽中|中奖|中个|选我|求抽|抽奖|杯子|大闸蟹|蟹券|中一次|求福利"
    r"|许愿|求求|希望中|给我中|接好运|逢考必过|锦鲤"
    r"|分母|每人一个|凑个|参战|先得|能中就好|中就好了|中不中|中没中|想要一个"
    r"|(希望|求|有幸)[^，。！!]{0,6}中签|幸运儿|好运气|好运|命中概率"
)
INVEST = re.compile(
    r"估值|仓位|买入|卖出|加仓|减仓|网格|红利|医药|医疗|消费|科技|债|黄金|A股|美股"
    r"|港股|中概|恒生|创业板|科创|上证|沪深|标普|纳指|回撤|配置|定投|长赢|波段|PE"
    r"|PB|年化|利率|汇率|周期|建仓|止盈|止损|对冲|持仓|分红|股息|ROE|利润|财报|GDP"
    r"|通胀|通缩|加息|降息|美联储|央行|流动性|成交量|换手|支撑|压力|趋势|均线|基本面"
    r"|宏观|再平衡|养老|保险|杠杆|融资|抄底|追高|割肉|套牢|解套|浮盈|浮亏|净值|申购"
    r"|赎回|ETF|LOF|QDII|FOF|可转债|打新|原油|白银|期货|期权|蓝筹|宽基|红利低波"
    r"|中证|全指|恒科|下跌|上涨|反弹|回调|新高|新低",
    re.I,
)
GREETING = re.compile(
    r"^(谢谢|感谢|多谢|感恩|辛苦了?|老大好|E大好|益达好|周末愉快|节日快乐|早上好"
    r"|晚上好|支持|赞同|点赞|打卡|签到|学习了|受教了?|收藏了?|马克|mark|顶|赞|好"
    r"|好的|收到|明白|明白了|是的|确实|同意|哈哈+|😄|👍|❤️|🙏|👌)[。！!~～,，.。\s]*$",
    re.I,
)


def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def fetch_pages(path, params):
    out = {}
    page = 1
    while True:
        q = urllib.parse.urlencode({**params, "pageNum": page, "pageSize": PAGE_SIZE})
        items = fetch(f"{BASE}{path}?{q}&sortType=new")
        if not items:
            break
        for it in items:
            out[it["id"]] = it
        if len(items) < PAGE_SIZE:
            break
        page += 1
        time.sleep(0.12)
    return list(out.values())


def is_author(c):
    return str(c.get("brokerUserId")) == AUTHOR_ID


def valuable(c, min_len=12):
    text = (c.get("content") or "").strip()
    if not text or GREETING.match(text) or LOTTERY.search(text):
        return False
    return len(text) >= min_len and bool(INVEST.search(text))


def download_image(url, assets):
    name = Path(urllib.parse.urlparse(url).path).name
    if not name:
        return None
    if not Path(name).suffix:
        name += ".jpg"
    dst = assets / name
    if not dst.exists():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            dst.write_bytes(r.read())
    return name


def render_images(images, assets, download=True):
    if not images or not download:
        return ""
    lines = []
    for url in images:
        try:
            name = download_image(url, assets)
        except Exception:
            continue
        if name:
            lines.append(f"![](assets/comments/{name})")
    return "\n\n" + "\n\n".join(lines) if lines else ""


def who(c):
    loc = c.get("ipLocation") or ""
    tag = "（作者）" if is_author(c) else (f"（{loc}）" if loc else "")
    return f"{c.get('userName') or '匿名'}{tag}"


def render_section(title, post_date, total, parents, replies, assets, download=True):
    shown = len(parents) + sum(len(replies.get(p["id"], [])) for p in parents)
    lines = [
        START,
        "",
        "---",
        "",
        "",
        f"# {title} · 评论区（{post_date}）",
        "",
        f"> 评论区归档：{date.today().isoformat()} 抓取于且慢社区，原帖共 {total} 条互动，"
        f"精选 {shown} 条（作者发言、作者回复及其他投资相关评论）。",
        "",
    ]
    for p in sorted(parents, key=lambda c: c["createdAt"]):
        lines.append(f"## {who(p)} · {p.get('likeNum', 0)} 赞")
        lines.append("")
        text = (p.get("content") or "").strip()
        lines.append(text + render_images(p.get("images"), assets, download))
        lines.append("")
        for r in sorted(replies.get(p["id"], []), key=lambda c: c["createdAt"]):
            to = r.get("toUserName")
            suffix = f"（回复 {to}）" if to and to != r.get("userName") else ""
            lines.append(
                f"> **{who(r)}**{suffix} · {r.get('likeNum', 0)} 赞："
                f"{(r.get('content') or '').strip()}{render_images(r.get('images'), assets, download)}"
            )
            lines.append("")
    lines.append(END)
    return "\n".join(lines)


def process_post(post, assets, dry_run):
    pid = post["id"]
    comments = fetch_pages("/community/comment/list", {"postId": pid})
    if not comments:
        return 0, 0

    total = len(comments) + sum(c.get("commentNum") or 0 for c in comments)
    included = {}
    for c in comments:
        if is_author(c) or valuable(c):
            included[c["id"]] = c
        elif c.get("authorEngaged") and (c.get("content") or "").strip():
            included[c["id"]] = c

    replies = {}
    for c in comments:
        need = c.get("authorEngaged") or (c["id"] in included and c.get("commentNum"))
        if not need:
            continue
        rs = fetch_pages("/community/reply/list", {"commentId": c["id"]})
        keep = [
            r for r in rs
            if is_author(r) or (c["id"] in included and valuable(r, min_len=10))
        ]
        if keep:
            replies[c["id"]] = keep
            included.setdefault(c["id"], c)

    parents = [included[i] for i in included]
    if not parents:
        return total, 0

    section = render_section(
        post["title"], post["date"], total, parents, replies, assets, download=not dry_run
    )
    if not dry_run:
        text = post["path"].read_text(encoding="utf-8").rstrip()
        if START in text:
            text = text[: text.index(START)].rstrip()
        post["path"].write_text(text + "\n\n" + section + "\n", encoding="utf-8")
    shown = len(parents) + sum(len(v) for v in replies.values())
    return total, shown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = INVESTORS["etf"]
    src = cfg["src"] / "qieman.com"
    assets = src / "assets" / "comments"
    if not args.dry_run:
        assets.mkdir(parents=True, exist_ok=True)
    cutoff = date.today() - timedelta(days=args.days)

    posts = []
    for f in sorted(src.glob("*.md")):
        m = re.match(r"^【(\d{8})】(.*)$", f.stem)
        if not m:
            continue
        d = date(int(m.group(1)[:4]), int(m.group(1)[4:6]), int(m.group(1)[6:]))
        if d < cutoff:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        pm = re.search(r"postId=(\d+)", text)
        if not pm:
            continue
        tm = re.search(r'^title: "(.*)"$', text, re.M)
        title = (tm.group(1) if tm else m.group(2)).replace('\\"', '"')
        posts.append({"id": pm.group(1), "date": d.isoformat(), "title": title, "path": f})

    print(f"检查 {len(posts)} 篇（{cutoff} 起）")
    total_all = shown_all = with_comments = 0
    for i, p in enumerate(posts, 1):
        total, shown = process_post(p, assets, args.dry_run)
        if total:
            with_comments += 1
        total_all += total
        shown_all += shown
        if total:
            print(f"  [{i}/{len(posts)}] {p['date']} 互动 {total} 精选 {shown} {p['title'][:30]}")
    print(f"完成：有评论 {with_comments} 篇，互动总数 {total_all}，精选 {shown_all} 条")


if __name__ == "__main__":
    main()
