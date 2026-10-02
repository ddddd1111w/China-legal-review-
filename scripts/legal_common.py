#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
legal-review skill 共享路径与配置解析（sync_library.py / search_law.py 共用）。

可移植设计：skill 文件夹整体复制到任意机器、任意目录后均可直接运行，不写死绝对路径。

文库根目录定位优先级：
  1. 命令行 --root "..."（仅 sync_library.py 支持）
  2. 环境变量 LEGAL_REVIEW_LIBRARY（目录绝对路径）
  3. scripts/library_config.json 的 library_root：
       - 绝对路径原样使用（适合把文库放在 skill 外部）；
       - 相对路径相对“本 skill 根目录”解析（默认 "library"，即 skill 自带文库）；
  4. 默认 <skill根>/library
"""

import json
import os
import re
import sys
from pathlib import Path

# scripts/ 的上一级即 skill 根（含 SKILL.md 的目录）
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SCRIPT_DIR / "library_config.json"

DEFAULT_CATEGORIES = [
    "01-宪法",
    "02-法律",
    "03-行政法规",
    "04-监察法规",
    "05-司法解释",
]


def force_utf8() -> None:
    """Windows 控制台默认 cp936，强制标准流按 UTF-8 输出，避免中文乱码。"""
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def load_raw_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(f"[致命错误] 找不到配置文件: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def resolve_library_root(cfg: dict, cli_root: str | None = None) -> Path:
    raw = (
        cli_root
        or os.environ.get("LEGAL_REVIEW_LIBRARY")
        or cfg.get("library_root")
        or "library"
    )
    p = Path(raw).expanduser()
    if not p.is_absolute():
        # 相对路径锚定 skill 根目录，而不是进程的当前工作目录
        p = SKILL_DIR / p
    p = p.resolve()
    if not p.exists():
        sys.exit(
            f"[致命错误] 文库根目录不存在: {p}\n"
            f"解决办法（任选其一）：\n"
            f"  1) 把法规文件夹放到 {SKILL_DIR / 'library'}；\n"
            f"  2) 编辑 {CONFIG_PATH}，把 library_root 改为文库实际绝对路径；\n"
            f"  3) 设置环境变量 LEGAL_REVIEW_LIBRARY 指向文库根目录。"
        )
    return p


def resolve_paths(cli_root: str | None = None) -> dict:
    """读配置并解析出 root / text_dir / categories / manifest 路径，返回增强后的 cfg。"""
    cfg = load_raw_config()
    root = resolve_library_root(cfg, cli_root)
    cfg["root"] = root
    cfg["text_dir"] = root / cfg.get("text_subdir", "_text")

    cats = cfg.get("categories")
    if not cats:
        # 配置未列分类时，自动发现文库根下形如 “01-xxx” 的分类目录
        cats = sorted(
            d.name
            for d in root.iterdir()
            if d.is_dir() and re.match(r"^\d{2}[-_]", d.name)
        )
    cfg["categories"] = cats or DEFAULT_CATEGORIES
    return cfg
