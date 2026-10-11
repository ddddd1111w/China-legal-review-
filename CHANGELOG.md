# Changelog

## 2026-10-03 — 审查修复（b77e026 及本次追加）

### P1（承诺与实现不符）
- **Python 3.9 兼容**：三个 .py 加 `from __future__ import annotations`（PEP 604 注解在 3.9 延迟求值）。已代码级验证全仓无运行时联合类型（isinstance/cast/模块级别名均未用 PEP604）。
- **POSIX 路径断裂**：sync_library.py 的 txt_rel/source_file/孤立清理/缓存键全部改正斜杠；旧索引载入时归一化 `\` → `/`（防 Windows 端旧缓存被判孤立导致全库 txt 误删）。实测重跑：1514 篇缓存 100% 命中、0 误删、0 重生成。

### P2
- 条号解析失败分支改 `sys.exit(1)`（原 print+return 退出码 0）。
- `titles` 默认 `--limit` 200 → 50。
- 新增 check_cat()：`--cat` 不存在时 stderr 警告（不再静默空结果）。
- SKILL.md §2 补 `--regex`、多段条号 `9,44,63`、"优先 --cat/--law 限定范围"；§7 补 Word 卡死/`--no-doc` 与 selftest 条目。
- sync_library.py user_added 不再回读缓存（文件进官方 manifest 后立即纠正标注）。
- report-template.md 末尾孤立代码围栏删除。

### 新增
- `scripts/selftest.py`：只读冒烟自检（7 项，沙箱内可跑），全部通过退出码 0。

### 验证记录
- 损坏 docx：临时根实测 → 点名报告 `File is not a zip file`、不产出 txt、exit 1、清单外文件正确标〖用户补充〗。
- 已知环境限制：本机 Word COM 启动即挂起（未激活/首启阻塞），`.doc` 转换在此机器不可用；sync 有 900 秒超时保护，会记失败并 exit 1，存量 51 个 .doc 已在缓存中不受影响。
- 挂起：.doc COM 实机转换、WSL sync（本机无对应环境）。

## 2026-10-02 之前
- 初始版本：国家法律法规数据库 1514 部（约 751.5 万字）+ 检索/审查脚本 + references。
