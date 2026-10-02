#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律文库增量同步脚本（legal-review skill 专用）

功能：
  1. 扫描文库分类目录（01-宪法 … 05-司法解释）下的 .docx / .doc
  2. .docx  用 Python 标准库 zipfile + XML 解析抽取正文（无需安装任何第三方包）
     .doc   调用同目录 convert_doc.ps1（Word/WPS COM）批量转为临时 .docx 后统一解析
  3. 为每部法律生成带元数据头的纯文本到 _text/<分类>/<同名>.txt
  4. 增量：按源文件 SHA1 判断新增/变更，未变化的文件跳过
  5. 重建索引 _text/index.json、标题速查 _text/titles.json、分类导航 _text/library-map.md

用法：
  python sync_library.py                # 增量同步
  python sync_library.py --full         # 全量重建（忽略缓存）
  python sync_library.py --root "D:\\other\\法律知识库"   # 临时指定文库根目录
  python sync_library.py --no-doc       # 跳过旧版 .doc

更新法律文本的标准操作：
  - 新增法律：把 .docx/.doc 放进对应分类目录，然后运行本脚本
  - 替换新版：用同名（或新日期）文件覆盖/放入分类目录，然后运行本脚本
  - 删除旧版：从分类目录删除源文件后运行本脚本，_text 中对应文本与索引会自动清理
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# 同目录共享模块：路径自适应（支持 skill 自带 library/ 或任意外部文库）
from legal_common import SCRIPT_DIR, force_utf8, resolve_paths

force_utf8()

# ---------------------------------------------------------------- 基础配置

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

CAT_FLXZ = {
    "01-宪法": "宪法",
    "02-法律": "法律",
    "03-行政法规": "行政法规",
    "04-监察法规": "监察法规",
    "05-司法解释": "司法解释",
}


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- docx 解析

def extract_docx(docx_path: Path) -> str:
    """从 .docx 抽取纯文本，按段落换行。仅使用标准库。"""
    with zipfile.ZipFile(docx_path) as z:
        names = z.namelist()
        if "word/document.xml" not in names:
            raise RuntimeError("压缩包内缺少 word/document.xml，可能不是有效 docx")
        xml_bytes = z.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    lines: list[str] = []
    for para in root.iter(W_NS + "p"):
        buf: list[str] = []
        for node in para.iter():
            tag = node.tag
            if tag == W_NS + "t":
                buf.append(node.text or "")
            elif tag == W_NS + "tab":
                buf.append("\t")
            elif tag in (W_NS + "br", W_NS + "cr"):
                buf.append("\n")
        text = "".join(buf).strip()
        if text:
            lines.append(text)
    body = "\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


# ---------------------------------------------------------------- .doc 转换

def convert_docs_via_word(jobs: list[tuple[Path, Path]]) -> dict[str, str]:
    """
    调用 convert_doc.ps1 批量把 .doc 转成临时 .docx。
    jobs: [(doc_path, tmp_docx_path), ...]
    返回 {doc_path字符串: "" 或 错误信息}
    """
    result: dict[str, str] = {}
    if not jobs:
        return result
    ps1 = SCRIPT_DIR / "convert_doc.ps1"
    jobs_file = SCRIPT_DIR / "_convert_jobs.json"
    payload = [{"doc": str(d), "docx": str(x)} for d, x in jobs]
    # PS 5.1 需要 BOM 才能正确按 UTF-8 读取中文路径
    jobs_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8-sig")
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(ps1), "-JobsFile", str(jobs_file)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
        )
        stdout = proc.stdout or ""
        for line in stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                r = json.loads(line)
                result[r["doc"]] = "" if r.get("ok") else r.get("error", "未知错误")
            except json.JSONDecodeError:
                continue
        if proc.returncode != 0 and not result:
            for d, _ in jobs:
                result[str(d)] = f"PowerShell 转换失败(退出码{proc.returncode}): {proc.stderr[:200]}"
    except subprocess.TimeoutExpired:
        for d, _ in jobs:
            result.setdefault(str(d), "Word COM 转换超时（>900秒）")
    except FileNotFoundError:
        for d, _ in jobs:
            result.setdefault(str(d), "系统找不到 powershell")
    finally:
        jobs_file.unlink(missing_ok=True)
    for d, _ in jobs:
        result.setdefault(str(d), "未收到转换结果")
    return result


# ---------------------------------------------------------------- 元数据

FNAME_DATE_RE = re.compile(r"^(.*?)_(\d{8})\.(docx|doc)$", re.I)


def parse_filename(fname: str) -> tuple[str, str]:
    m = FNAME_DATE_RE.match(fname)
    if m:
        raw_date = m.group(2)
        d = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        return m.group(1).strip(), d
    return Path(fname).stem.strip(), ""


def load_manifest(cfg: dict) -> dict[str, dict]:
    """按 actual_file（文件名）建立官方元数据索引。"""
    mf = cfg["root"] / cfg.get("manifest", "_manifests/final_manifest.json")
    if not mf.exists():
        return {}
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[警告] manifest 读取失败，将改用文件名解析元数据: {e}")
        return {}
    return {item.get("actual_file", ""): item for item in data if item.get("actual_file")}


def title_key(title: str) -> str:
    """归一化标题：去掉括号注释与空白，用于同法多版本归组。"""
    t = re.sub(r"[（(][^（）()]*[）)]", "", title)
    return re.sub(r"\s+", "", t)


def build_txt_header(meta: dict) -> str:
    lines = [
        f"# {meta['title']}",
        "",
        f"- 法律层级：{meta.get('flxz') or meta.get('category') or ''}",
        f"- 制定机关：{meta.get('org') or '（未标注，多为用户补充文件）'}",
        f"- 公布日期：{meta.get('publish_date') or '（未标注）'}",
        f"- 施行日期：{meta.get('effective_date') or '（未标注）'}",
        f"- 文库分类：{meta.get('category') or ''}",
        f"- 来源文件：{meta.get('source_file') or ''}",
    ]
    if meta.get("user_added"):
        lines.append("- 备注：用户自行补充文件，元数据由文件名解析，请核对原文")
    lines += ["", "---", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- 主流程

def main() -> int:
    ap = argparse.ArgumentParser(description="法律文库增量同步")
    ap.add_argument("--full", action="store_true", help="全量重建，忽略已有缓存")
    ap.add_argument("--root", help="临时指定文库根目录（优先于 config）")
    ap.add_argument("--no-doc", action="store_true", help="跳过旧版 .doc 文件")
    args = ap.parse_args()

    cfg = resolve_paths(args.root)
    root: Path = cfg["root"]
    text_dir: Path = cfg["text_dir"]
    text_dir.mkdir(exist_ok=True)
    tmp_dir = text_dir / ".tmp_docx"
    index_path = text_dir / "index.json"

    manifest = load_manifest(cfg)

    old_index: dict[str, dict] = {}
    if index_path.exists() and not args.full:
        try:
            for item in json.loads(index_path.read_text(encoding="utf-8")):
                old_index[item["source_file"]] = item
        except Exception:
            old_index = {}

    # 1) 扫描源文件 ----------------------------------------------------
    sources: list[Path] = []
    for cat in cfg["categories"]:
        cat_dir = root / cat
        if not cat_dir.exists():
            print(f"[警告] 分类目录不存在，跳过: {cat_dir}")
            continue
        for p in cat_dir.iterdir():
            if p.is_file() and p.suffix.lower() in (".docx", ".doc") and not p.name.startswith("~$"):
                sources.append(p)
    print(f"[扫描] 发现源文件 {len(sources)} 个")

    # 2) 计算哈希，确定待转换清单 --------------------------------------
    records: list[dict] = []
    pending_docx: list[Path] = []   # 需要抽文本的 docx（原生或转换后）
    pending_doc: list[tuple[Path, Path, dict]] = []
    failures: list[tuple[str, str]] = []

    for src in sources:
        cat = src.parent.name
        rel = f"{cat}\\{src.name}"
        digest = sha1_of(src)
        cached = old_index.get(rel)
        rec = {
            "title": "", "category": cat, "flxz": CAT_FLXZ.get(cat, cat),
            "org": "", "publish_date": "", "effective_date": "",
            "source_file": rel, "txt_rel": f"_text\\{cat}\\{src.stem}.txt",
            "sha1": digest, "chars": 0, "user_added": False,
        }
        official = manifest.get(src.name)
        if official:
            # category 始终使用分类目录名（01-宪法 … 05-司法解释）；
            # 官方更细的法律性质（法律解释/修正案等）进 flxz
            rec.update({
                "title": official.get("title", ""),
                "org": official.get("zdjgName", ""),
                "publish_date": official.get("gbrq", ""),
                "effective_date": official.get("sxrq", ""),
                "flxz": official.get("flxz") or rec["flxz"],
            })
            if official.get("bbbs"):
                rec["bbbs"] = official["bbbs"]
        else:
            title, fdate = parse_filename(src.name)
            rec["title"] = title
            rec["publish_date"] = fdate
            rec["effective_date"] = fdate
            rec["user_added"] = True

        if cached and cached.get("sha1") == digest and (root / cached["txt_rel"]).exists() and not args.full:
            rec["chars"] = cached.get("chars", 0)
            rec["user_added"] = cached.get("user_added", rec["user_added"])
            records.append(rec)
            continue

        if src.suffix.lower() == ".docx":
            pending_docx.append(src)
            records.append(rec)
        else:
            if args.no_doc:
                if cached:
                    rec["chars"] = cached.get("chars", 0)
                    records.append(rec)
                else:
                    failures.append((rel, "按 --no-doc 跳过的 .doc，尚无文本"))
                continue
            tmp_docx = tmp_dir / cat / (src.stem + ".docx")
            pending_doc.append((src, tmp_docx, rec))
            records.append(rec)

    # 3) .doc 先经 Word COM 转临时 docx --------------------------------
    doc_errors: dict[str, str] = {}
    if pending_doc:
        print(f"[转换] {len(pending_doc)} 个旧版 .doc，启动 Word/WPS 批量转换（可能需要一两分钟）…")
        jobs = [(src, tmp) for src, tmp, _ in pending_doc]
        doc_errors = convert_docs_via_word(jobs)
        ok_n = sum(1 for e in doc_errors.values() if not e)
        print(f"[转换] .doc 成功 {ok_n}/{len(jobs)}")

    # 4) 抽取正文并写 txt ----------------------------------------------
    rec_by_src = {r["source_file"]: r for r in records}
    todo: list[tuple[Path, Path | None, dict]] = [(p, p, rec_by_src[f"{p.parent.name}\\{p.name}"]) for p in pending_docx]
    for src, tmp, rec in pending_doc:
        err = doc_errors.get(str(src), "")
        rel = rec["source_file"]
        if err:
            failures.append((rel, f".doc 转换失败: {err}"))
            continue
        if not tmp.exists():
            failures.append((rel, ".doc 转换后未找到临时 docx"))
            continue
        todo.append((src, tmp, rec))

    n_new = 0
    n_fail = len(failures)
    for src, readable, rec in todo:
        rel = rec["source_file"]
        try:
            body = extract_docx(readable)
            if len(body) < 20:
                raise RuntimeError(f"抽取文本过短（{len(body)}字），文件可能损坏或为扫描件")
            header = build_txt_header(rec)
            out_path = root / rec["txt_rel"]  # txt_rel 相对文库根（_text/<分类>/...）
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(header + body + "\n", encoding="utf-8")
            rec["chars"] = len(body)
            n_new += 1
        except Exception as e:
            failures.append((rel, f"文本抽取失败: {e}"))

    # 转换成功后清理临时 docx
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # 5) 剔除失败项，清理孤立 txt --------------------------------------
    fail_rels = {rel for rel, _ in failures}
    records = [r for r in records if r["source_file"] not in fail_rels]

    valid_txt = {r["txt_rel"] for r in records}
    removed = 0
    for cat in cfg["categories"]:
        d = text_dir / cat
        if not d.exists():
            continue
        for txt in d.glob("*.txt"):
            rel = f"_text\\{cat}\\{txt.name}"
            if rel not in valid_txt:
                txt.unlink()
                removed += 1

    # 6) 同法多版本归组，标记最新版 ------------------------------------
    groups: dict[str, list[dict]] = {}
    for r in records:
        groups.setdefault(title_key(r["title"]), []).append(r)
    for key, grp in groups.items():
        grp.sort(key=lambda x: (x.get("publish_date") or "", x["source_file"]), reverse=True)
        for i, r in enumerate(grp):
            r["is_latest"] = (i == 0)
            r["version_count"] = len(grp)
            r["title_key"] = key

    records.sort(key=lambda x: (x["category"], x["title"], x.get("publish_date") or ""), reverse=False)

    # 7) 写索引 --------------------------------------------------------
    index_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    titles = [{
        "title": r["title"],
        "title_key": r["title_key"],
        "category": r["category"],
        "flxz": r["flxz"],
        "org": r["org"],
        "publish_date": r["publish_date"],
        "effective_date": r["effective_date"],
        "is_latest": r["is_latest"],
        "version_count": r["version_count"],
        "user_added": r["user_added"],
        "txt_rel": r["txt_rel"],
    } for r in records]
    (text_dir / "titles.json").write_text(json.dumps(titles, ensure_ascii=False, indent=2), encoding="utf-8")

    write_library_map(cfg, records)

    # 8) 报告 ----------------------------------------------------------
    cat_count: dict[str, int] = {}
    latest_count = 0
    user_count = 0
    for r in records:
        cat_count[r["category"]] = cat_count.get(r["category"], 0) + 1
        latest_count += 1 if r["is_latest"] else 0
        user_count += 1 if r["user_added"] else 0
    print("\n================ 同步报告 ================")
    print(f"文库根目录 : {root}")
    for cat in cfg["categories"]:
        print(f"  {cat}: {cat_count.get(cat, 0)} 篇")
    print(f"有效文本合计: {len(records)} 篇（其中不同法律最新版 {latest_count} 部，用户补充 {user_count} 篇）")
    print(f"本次新生成/更新: {n_new} 篇；清理孤立文本: {removed} 个")
    if failures:
        print(f"失败 {len(failures)} 个：")
        for rel, err in failures:
            print(f"  ✗ {rel}  -> {err}")
    print(f"索引文件: {index_path}")
    print("==========================================")
    return 1 if failures else 0


def write_library_map(cfg: dict, records: list[dict]) -> None:
    """生成供模型浏览的分类导航 library-map.md。"""
    lines = [
        "# 法律文库分类导航（自动生成，请勿手改）",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 数据口径：国家法律法规数据库现行有效文本 + 用户补充文件",
        f"- 使用方法：先按本导航定位法律名称，再用 `search_law.py` 检索具体条文；标【旧版】者为已被新文本取代的历史版本，引用时以最新版为准",
        "",
    ]
    by_cat: dict[str, list[dict]] = {}
    for r in records:
        by_cat.setdefault(r["category"], []).append(r)

    for cat in cfg["categories"]:
        items = by_cat.get(cat, [])
        latest = sorted([r for r in items if r["is_latest"]], key=lambda x: x["title"])
        old = [r for r in items if not r["is_latest"]]
        lines += [f"## {cat}（最新版 {len(latest)} 部，另有历史版本 {len(old)} 篇）", ""]
        for r in latest:
            tag = "〖补充〗" if r["user_added"] else ""
            date = r["publish_date"] or "日期未标注"
            lines.append(f"- {tag}{r['title']}（{date}）")
        if old:
            lines.append("")
            lines.append("<details><summary>历史版本（引用前请先核对是否已有更新文本）</summary>")
            lines.append("")
            for r in sorted(old, key=lambda x: x["title"]):
                lines.append(f"- 【旧版】{r['title']}（{r['publish_date'] or '日期未标注'}）")
            lines.append("")
            lines.append("</details>")
        lines.append("")

    out = cfg["text_dir"] / "library-map.md"
    out.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
