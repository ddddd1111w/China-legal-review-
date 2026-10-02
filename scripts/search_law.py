#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律文库检索脚本（legal-review skill 专用）

用法总览：
  python search_law.py status                                文库与索引状态
  python search_law.py titles [关键词...] [--cat 分类] [--all] [--limit N]
                                                             按标题查法律（默认仅最新版）
  python search_law.py info  法律名关键词...                  查看某部法律的元数据/版本
  python search_law.py search 关键词... [--cat 分类] [--law 法律名] [--any] [--regex] [--limit N]
                                                             全文检索条文（默认多关键词为“且”）
  python search_law.py get  法律名关键词... [--article 条号]  读取目录/全文/指定条文
                                                             （--article 支持 12、十二、12-15）

输出为纯文本（UTF-8），所有结论均可按给出的 txt_rel 路径用文件工具打开原文核对。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# 同目录共享模块：路径自适应（支持 skill 自带 library/ 或任意外部文库）
from legal_common import force_utf8, resolve_paths

force_utf8()

ARTICLE_RE = re.compile(r"第\s*[一二三四五六七八九十百千万零〇两\d]+\s*条")
# 条头：行首“第X条”，兼容“第X条之一”，条号后可直接跟全角空格/标点/正文
ARTICLE_HEAD_RE = re.compile(r"^第\s*[一二三四五六七八九十百千万零〇两\d]+\s*条(?:之[一二三四五六七八九十])?")
CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百千万零〇两\d]+[章节编]")
CN_NUM = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9}


def die(msg: str):
    sys.exit(f"[错误] {msg}\n请先运行 sync_library.py 构建索引，或检查 scripts/library_config.json 的 library_root。")


def load_env():
    cfg = resolve_paths()
    root = cfg["root"]
    text_dir = cfg["text_dir"]
    index_path = text_dir / "index.json"
    if not index_path.exists():
        die(f"索引不存在: {index_path}")
    records = json.loads(index_path.read_text(encoding="utf-8"))
    return cfg, root, text_dir, records


def txt_path_of(root: Path, rec: dict) -> Path:
    # txt_rel 相对文库根，形如 _text\02-法律\xxx.txt
    return root / rec["txt_rel"].replace("\\", "/")


def cn_to_int(s: str) -> int | None:
    s = s.strip().replace(" ", "")
    if s.isdigit():
        return int(s)
    if not s:
        return None
    total = 0
    section = 0
    num = 0
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in CN_NUM:
            num = CN_NUM[ch]
        elif ch in units:
            u = units[ch]
            if u == 10000:
                section = (section + (num or 1)) * u if ch == "万" and num == 0 and section == 0 else section + num
                section = (section or num or 1) * u if ch == "万" else section
                total += section
                section = 0
            else:
                section += (num or 1) * u
            num = 0
        i += 1
    return total + section + num if (total + section + num) else None


def article_num(text: str) -> int | None:
    """从'第X条'提取条号数值。"""
    m = ARTICLE_RE.search(text)
    if not m:
        return None
    inner = m.group(0)[1:-1].strip()
    return cn_to_int(inner)


def split_articles(body: str) -> list[dict]:
    """
    把法律正文切成结构块：章标题 + 条文。
    返回 [{"kind":"chapter"/"article"/"other", "no":int|None, "title":str, "text":str}]
    说明：部分文本开头目录也列条号，以最后一个“第一条”条头作为正文起点。
    """
    raw_lines = [l.strip() for l in body.splitlines()]
    # 定位正文起点：最后一个行首“第一条”
    first_article_positions = [i for i, l in enumerate(raw_lines)
                               if l and ARTICLE_HEAD_RE.match(l) and article_num(l[:12]) == 1]
    start = first_article_positions[-1] if first_article_positions else 0
    if start > 0:
        prologue = "\n".join(l for l in raw_lines[:start] if l).strip()
    else:
        prologue = ""

    blocks: list[dict] = []
    if prologue:
        blocks.append({"kind": "other", "no": None, "title": "", "text": prologue})
    cur_chapter = ""

    for line in raw_lines[start:]:
        if not line:
            continue
        if line.startswith("#") or line == "---" or line.startswith("- ") or line.startswith("<!--"):
            continue  # 跳过元数据头
        if CHAPTER_RE.match(line) and not ARTICLE_HEAD_RE.match(line):
            cur_chapter = line
            blocks.append({"kind": "chapter", "no": None, "title": line, "text": line})
            continue
        m = ARTICLE_HEAD_RE.match(line)
        if m:
            head = m.group(0)
            sub = None
            sm = re.search(r"之([一二三四五六七八九十])", head)
            if sm:
                sub = cn_to_int(sm.group(1))
            blocks.append({"kind": "article", "no": article_num(head), "sub": sub,
                           "title": head, "text": line, "chapter": cur_chapter})
        elif blocks and blocks[-1]["kind"] == "article":
            blocks[-1]["text"] += "\n" + line
        elif blocks and blocks[-1]["kind"] == "other":
            blocks[-1]["text"] += "\n" + line
        else:
            blocks.append({"kind": "other", "no": None, "title": "", "text": line})
    return blocks


def load_body(root: Path, rec: dict) -> str:
    p = txt_path_of(root, rec)
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8", errors="replace")
    # 去掉元数据头（第一个 --- 之后）
    parts = text.split("\n---\n", 1)
    return parts[1] if len(parts) == 2 else text


def match_law(records: list[dict], name_parts: list[str], cat: str | None, latest_only=True) -> list[dict]:
    key = "".join(name_parts)
    out = []
    for r in records:
        if cat and r["category"] != cat:
            continue
        if latest_only and not r.get("is_latest", True):
            continue
        title_compact = re.sub(r"[\s（）()]", "", r["title"])
        if key in title_compact or all(p in r["title"] for p in name_parts):
            out.append(r)
    out.sort(key=lambda r: (abs(len(r["title"]) - len(key)), r["title"]))
    return out


def fmt_meta(r: dict) -> str:
    return (f"《{r['title']}》\n"
            f"  层级/分类：{r['flxz']} / {r['category']}\n"
            f"  制定机关：{r.get('org') or '未标注'}\n"
            f"  公布日期：{r.get('publish_date') or '未标注'}    施行日期：{r.get('effective_date') or '未标注'}\n"
            f"  版本：{'最新版' if r.get('is_latest', True) else '【旧版】'}（同法文本 {r.get('version_count', 1)} 篇）"
            f"{'  〖用户补充〗' if r.get('user_added') else ''}\n"
            f"  文本路径：{r['txt_rel']}")


# ---------------------------------------------------------------- 子命令

def cmd_status(args, cfg, root, text_dir, records):
    cats: dict[str, int] = {}
    latest = 0
    user = 0
    total_chars = 0
    for r in records:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
        latest += 1 if r.get("is_latest") else 0
        user += 1 if r.get("user_added") else 0
        total_chars += r.get("chars", 0)
    idx_mtime = datetime.fromtimestamp((text_dir / "index.json").stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    print(f"文库根目录：{root}")
    print(f"索引生成时间：{idx_mtime}")
    print(f"文本总字数：约 {total_chars/10000:.1f} 万字")
    for cat in cfg["categories"]:
        print(f"  {cat}: {cats.get(cat, 0)} 篇")
    print(f"合计 {len(records)} 篇文本，其中不同法律的最新版 {latest} 部，用户补充 {user} 篇")
    print(f"分类导航：{text_dir / 'library-map.md'}")


def cmd_titles(args, cfg, root, text_dir, records):
    kws = args.keywords or []
    n = 0
    for r in records:
        if not args.all and not r.get("is_latest", True):
            continue
        if args.cat and r["category"] != args.cat:
            continue
        if kws and not all(k in r["title"] for k in kws):
            continue
        tag = "〖补充〗" if r.get("user_added") else ""
        old = "" if r.get("is_latest", True) else " 【旧版】"
        print(f"[{r['category']}] {tag}{r['title']}（{r.get('publish_date') or '日期未标注'}）{old}")
        n += 1
        if n >= args.limit:
            break
    print(f"\n共 {n} 部" + ("（达到 --limit 上限）" if n >= args.limit else ""))


def cmd_info(args, cfg, root, text_dir, records):
    hits = match_law(records, args.name, args.cat, latest_only=False)
    if not hits:
        die(f"标题匹配不到法律：{' '.join(args.name)}")
    # 归组同标题 key 的全部版本
    keys = {h["title_key"] for h in hits[:3]}
    group = [r for r in records if r["title_key"] in keys]
    group.sort(key=lambda r: r.get("publish_date") or "", reverse=True)
    for r in group:
        print(fmt_meta(r))
        print("-" * 60)


def compile_patterns(keywords, use_regex, use_any):
    if use_regex:
        return [re.compile(k) for k in keywords]
    return [re.compile(re.escape(k)) for k in keywords]


def cmd_search(args, cfg, root, text_dir, records):
    kws = args.keywords
    if not kws:
        die("search 至少需要一个关键词")
    pats = compile_patterns(kws, args.regex, args.any)

    scope = records
    if args.law:
        scope = match_law(records, [args.law], args.cat, latest_only=False)
        if not scope:
            die(f"法律名匹配不到：{args.law}")
    elif args.cat:
        scope = [r for r in records if r["category"] == args.cat]
    # 默认只检索最新版文本，避免旧法条文干扰
    if not args.all_versions:
        scope = [r for r in scope if r.get("is_latest", True)]

    results = []  # (score, rec, block)
    for rec in scope:
        body = load_body(root, rec)
        if not body:
            continue
        # 文件级预筛（AND 时所有词都要在文件内出现）
        if not args.any:
            if not all(p.search(body) for p in pats):
                continue
        elif not any(p.search(body) for p in pats):
            continue
        blocks = split_articles(body)
        title_hit = sum(1 for p in pats if p.search(rec["title"]))
        for blk in blocks:
            if blk["kind"] not in ("article", "other"):
                continue
            text = blk["text"]
            counts = [len(p.findall(text)) for p in pats]
            if args.any:
                hit = sum(c for c in counts if c > 0)
                if hit == 0:
                    continue
                score = hit * 3 + sum(counts)
            else:
                if any(c == 0 for c in counts):
                    continue
                score = sum(counts) * 3
            if blk["kind"] == "article":
                score += 2
            score += title_hit * 15
            results.append((score, rec, blk))

    results.sort(key=lambda x: x[0], reverse=True)
    if not results:
        print("未检索到包含全部关键词的条文。建议：\n  1) 换用更短的关键词；加 --any 改为任一命中；\n"
              "  2) 先用 titles 命令确认法律名称；\n  3) 加 --all-versions 同时检索历史版本。")
        return

    shown_law = set()
    n = 0
    for score, rec, blk in results:
        if n >= args.limit:
            break
        if rec["txt_rel"] not in shown_law:
            print("=" * 78)
            print(f"《{rec['title']}》 [{rec['category']}] {('最新版' if rec.get('is_latest', True) else '【旧版】')}  路径: {rec['txt_rel']}")
            shown_law.add(rec["txt_rel"])
        chapter = blk.get("chapter", "")
        if chapter:
            print(f"  〔{chapter}〕")
        text = blk["text"]
        if len(text) > 800:
            # 长条文截取首个关键词周边
            m = pats[0].search(text)
            center = m.start() if m else 0
            s = max(0, center - 300)
            e = min(len(text), center + 500)
            text = ("……" if s else "") + text[s:e] + ("……" if e < len(blk["text"]) else "")
        for line in text.splitlines():
            print("  " + line)
        print()
        n += 1
    print(f"共 {len(results)} 处命中，已展示前 {n} 处（--limit 调整数量，--law 限定法律，--all-versions 含旧版）")


def cmd_get(args, cfg, root, text_dir, records):
    hits = match_law(records, args.name, args.cat, latest_only=True)
    if not hits:
        old = match_law(records, args.name, args.cat, latest_only=False)
        if old:
            print("[提示] 仅匹配到旧版文本，将展示旧版（请核对是否已有新文本）：")
            hits = old
        else:
            die(f"标题匹配不到法律：{' '.join(args.name)}")
    rec = hits[0]
    body = load_body(root, rec)
    blocks = split_articles(body)
    print(fmt_meta(rec))
    print("=" * 78)

    if not args.article:
        # 输出结构目录 + 条文数 + 前几条
        chapters = [b for b in blocks if b["kind"] == "chapter"]
        arts = [b for b in blocks if b["kind"] == "article"]
        if chapters:
            print("【目录结构】")
            for c in chapters:
                print("  " + c["title"])
            print(f"\n共 {len(arts)} 条。用 --article 条号 读取具体条文，例如 --article 12 或 --article 12-15；\n"
                  f"或用 search 命令按关键词检索。以下为开头内容预览：\n")
        preview = "\n".join(b["text"] for b in blocks[:6] if b["kind"] in ("article", "other", "chapter"))
        print(preview[:1500] + ("……" if len(preview) > 1500 else ""))
        return

    # 解析条号：支持 12、十二、12-15，以及逗号/顿号分隔的多段，如 44,45,63-65
    spec = args.article.replace("第", "").replace("条", "").strip()
    ranges: list[tuple[int, int]] = []
    for part in re.split(r"[,，、;；]", spec):
        part = part.strip()
        if not part:
            continue
        if re.search(r"[-－~至到]", part):
            a, b = re.split(r"[-－~至到]", part, maxsplit=1)
            lo, hi = cn_to_int(a.strip()), cn_to_int(b.strip())
        else:
            lo = hi = cn_to_int(part)
        if lo is None:
            print(f"[错误] 无法解析条号“{part}”（原始输入 {args.article}）。支持形式：63、六十三、63-65、9,44,63。")
            return
        if hi is None:
            hi = lo
        ranges.append((lo, hi))
    if not ranges:
        die(f"无法解析条号: {args.article}")

    def in_ranges(n: int) -> bool:
        return any(a <= n <= b for a, b in ranges)

    cur_chapter = ""
    found = 0
    for b in blocks:
        if b["kind"] == "chapter":
            cur_chapter = b["title"]
        if b["kind"] == "article" and b["no"] is not None and in_ranges(b["no"]):
            if cur_chapter:
                print(f"〔{cur_chapter}〕")
            print(b["text"])
            print()
            found += 1
    if not found:
        want = "、".join(f"第{a}条" if a == b else f"第{a}至{b}条" for a, b in ranges)
        print(f"[提示] 未找到 {want}，该文件可能用其他编号方式（如'一、'），请改用 search 检索。")


# ---------------------------------------------------------------- 入口

def main():
    ap = argparse.ArgumentParser(description="法律文库检索（legal-review）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    p_t = sub.add_parser("titles")
    p_t.add_argument("keywords", nargs="*")
    p_t.add_argument("--cat")
    p_t.add_argument("--all", action="store_true", help="包含旧版文本")
    p_t.add_argument("--limit", type=int, default=200)

    p_i = sub.add_parser("info")
    p_i.add_argument("name", nargs="+")
    p_i.add_argument("--cat")

    p_s = sub.add_parser("search")
    p_s.add_argument("keywords", nargs="+")
    p_s.add_argument("--cat")
    p_s.add_argument("--law", help="限定法律名称（模糊匹配）")
    p_s.add_argument("--any", action="store_true", help="任一关键词命中（默认全部命中）")
    p_s.add_argument("--regex", action="store_true", help="关键词按正则处理")
    p_s.add_argument("--all-versions", action="store_true", help="同时检索旧版文本")
    p_s.add_argument("--limit", type=int, default=20)

    p_g = sub.add_parser("get")
    p_g.add_argument("name", nargs="+")
    p_g.add_argument("--cat")
    p_g.add_argument("--article", help="条号，如 12、十二、12-15")

    args = ap.parse_args()
    cfg, root, text_dir, records = load_env()
    {
        "status": cmd_status,
        "titles": cmd_titles,
        "info": cmd_info,
        "search": cmd_search,
        "get": cmd_get,
    }[args.cmd](args, cfg, root, text_dir, records)


if __name__ == "__main__":
    main()
