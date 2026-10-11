#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""legal-review 只读冒烟自检。

用法：
    python scripts/selftest.py [--root 文库根目录]

只读操作（status/titles/search/get），不写任何文件，可在沙箱内运行。
全部通过退出码 0；任一失败退出码 1，并打印 ✗ 行定位问题。
"""
from __future__ import annotations

import os
import subprocess
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
SEARCH = os.path.join(SCRIPT_DIR, "search_law.py")


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SEARCH, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=SKILL_DIR,
    )


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="legal-review 只读冒烟自检")
    ap.add_argument("--root", help="临时指定文库根目录（传给 search_law.py）")
    args = ap.parse_args()
    env_extra = ["--root", args.root] if args.root else []

    results: list[tuple[bool, str, str]] = []  # (ok, name, detail)

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((ok, name, detail))
        print(("  ✅ " if ok else "  ✗ ") + name + (f"（{detail}）" if detail else ""))

    # 1. 索引存在且非空
    r = run("titles", "--limit", "3", *env_extra)
    check("titles 可用且索引存在", r.returncode == 0 and len(r.stdout.strip()) > 0,
          f"EC={r.returncode}")

    # 2. search 命中
    r = run("search", "--cat", "02-法律", "治安管理", *env_extra)
    check("search --cat 命中", r.returncode == 0 and "命中" in r.stdout, f"EC={r.returncode}")

    # 3. get 单条
    r = run("get", "宪法", "--article", "33", *env_extra)
    check("get 单条（宪法 33）", r.returncode == 0 and "第三十三条" in r.stdout, f"EC={r.returncode}")

    # 4. get 多段（宪法匹配到修正案（2018年），无 82 条，故用监察法实施条例）
    r = run("get", "监察法实施条例", "--article", "82,85", *env_extra)
    check("get 多段（82,85）", r.returncode == 0 and "第八十二条" in r.stdout, f"EC={r.returncode}")

    # 5. 坏条号 → exit 1
    r = run("get", "宪法", "--article", "8x9y", *env_extra)
    check("坏条号退出码 1", r.returncode == 1, f"EC={r.returncode}")

    # 6. 不存在的 --cat → exit 0 且 stderr 警告
    r = run("titles", "--cat", "09-不存在", *env_extra)
    check("坏 --cat 有警告且 EC=0",
          r.returncode == 0 and "分类不存在" in r.stderr, f"EC={r.returncode}")

    # 7. 检索不到 ≠ 无依据：空结果正常退出
    r = run("search", "--cat", "01-宪法", "量子力学", *env_extra)
    check("空结果正常退出（EC=0）", r.returncode == 0, f"EC={r.returncode}")

    n_ok = sum(1 for ok, _, _ in results if ok)
    print(f"\n自检结果：{n_ok}/{len(results)} 通过")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
