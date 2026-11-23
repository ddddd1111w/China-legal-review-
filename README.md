# legal-review · 法律法规文库检索与合法性审查 Skill
# Legal Statute Library Retrieval & Legality Review Skill

> 中英对照版：中文在前，英文以引用块给出。Bilingual edition: Chinese first, English follows in blockquotes.

一个面向 LLM Agent 的**自包含法律技能（Skill）**：内置国家法律法规数据库现行有效文本，让模型在回答法律问题、做合法性审查时，**先检索原文、再引用条文、最后下结论**，而不是凭记忆"背法条"。

> A **self-contained legal skill for LLM agents**. It bundles the currently effective texts from China's national laws and regulations database, so the model **retrieves the actual text first, cites the provision second, and concludes last** — instead of reciting statutes from memory.

- 内置 **1550 篇**现行有效法规（宪法 7、法律 355、行政法规 612、监察法规 2、司法解释 574），约 **773.1 万字**，数据截至 **2026-11-14**<br>Bundles **1,550** effective instruments (7 Constitution & amendments, 355 laws, 612 administrative regulations, 2 supervisory regulations, 574 judicial interpretations), ≈ **7.73 million Chinese characters**, data as of **2026-11-14**
- 纯 Python 标准库实现，**零第三方依赖**，复制即可用<br>Pure Python standard library, **zero third-party dependencies**, copy-and-run
- 文库可随时**新增 / 替换 / 删除**，一条命令增量重建索引<br>Add, replace or remove instruments at any time; one command rebuilds the index incrementally
- 路径自适应：整个文件夹复制到任意电脑、任意目录均可运行，不写死绝对路径<br>Path-agnostic: the whole folder runs from any machine or directory, no hard-coded absolute paths
- 自带只读自检脚本，一条命令确认索引、检索、条号解析是否正常<br>Ships a read-only self-test that verifies the index, search and article parsing in one command
- 与具体模型无关，已在 **DeepSeek**、**智谱 GLM** 等通过 DSH（DeepSeek Harness）接入的模型上使用<br>Model-agnostic; used with models wired through DSH (DeepSeek Harness), including **DeepSeek** and **Zhipu GLM**

> 本仓库仅提供检索工具与公开法规文本，**不构成法律意见**。使用前请务必阅读文末[免责条款](#免责条款--disclaimer)。
>
> This repository provides a retrieval tool and public statutory texts only. It **does not constitute legal advice**. Read the [Disclaimer](#免责条款--disclaimer) before use.

---

## 目录 · Table of Contents

- [它能做什么 · What It Does](#它能做什么--what-it-does)
- [目录结构 · Project Layout](#目录结构--project-layout)
- [安装 · Installation](#安装--installation)
- [快速开始 · Quick Start](#快速开始--quick-start)
- [检索命令速查 · Command Reference](#检索命令速查--command-reference)
- [更新文库 · Updating the Library](#更新文库--updating-the-library)
- [使用外部文库 · Using an External Library](#使用外部文库--using-an-external-library)
- [工作原理 · How It Works](#工作原理--how-it-works)
- [数据来源与时效 · Data Source & Currency](#数据来源与时效--data-source--currency)
- [版本与更新记录 · Version & Changelog](#版本与更新记录--version--changelog)
- [能力边界 · Scope & Limitations](#能力边界--scope--limitations)
- [免责条款 · Disclaimer](#免责条款--disclaimer)
- [许可证 · License](#许可证--license)

---

## 它能做什么 · What It Does

1. **合法性审查 / 法制审核**：对规范性文件、红头文件、行政行为、执法决定、行政处罚/许可/强制案件、合同、制度文稿，按"主体·权限·程序·事实·依据·内容·形式"七维度逐项比对法条，给出五级结论（合法 / 不合法 / 部分不合法 / 存在法律风险 / 无法判断）并套用审查意见书模板。

   > **Legality review / legal-affairs vetting.** For normative documents, official "red-header" documents, administrative acts, enforcement decisions, penalty/permit/coercion cases, contracts and internal policies, the skill checks each item against statutory text across seven dimensions — subject, authority, procedure, facts, legal basis, substance, form — and returns a five-level finding (lawful / unlawful / partly unlawful / legally risky (insufficient basis) / undeterminable) using a review-opinion template.

2. **法律问题咨询**：按"定法 → 定条 → 读原文"检索，给出结论、依据链（法名＋条号＋原文要点＋施行日期）与风险提示，自动处理效力位阶、新旧法、特别法、溯及力等冲突规则。

   > **Legal Q&A.** Follows a "identify the statute → locate the article → read the text" path, then gives a conclusion, a citation chain (statute name + article number + gist of the text + effective date) and risk notes, handling hierarchy of norms, old-vs-new law, lex specialis and retroactivity rules.

3. **条文检索与核对**：标题查找、全文关键词检索、按条号精读、版本比对，所有结论都可回溯到本地原文。

   > **Provision retrieval and verification.** Title lookup, full-text keyword search, article-level reading and version comparison; every conclusion traces back to local source text.

模型被要求**只引用从文库中实际检索到的条文原文，严禁凭记忆引用法条**。

> The model is instructed to **cite only text actually retrieved from the library — never from memory**.

## 目录结构 · Project Layout

```
legal-review/
├── SKILL.md                  # 技能入口 / skill entry (frontmatter + instructions)
├── README.md                 # 本说明 / this file (humans only; the loader ignores it)
├── CHANGELOG.md              # 版本与文库更新记录 / version & library changelog
├── LICENSE                   # 脚本 MIT；法规文本公有领域 / MIT for code; statutes are public domain
├── .gitignore
├── scripts/                  # 可直接运行的脚本（标准库，零依赖）/ runnable scripts, stdlib only
│   ├── search_law.py         # 检索 / 精读（只读）/ search & read (read-only)
│   ├── sync_library.py       # 文库增量同步 / incremental library sync
│   ├── selftest.py           # 只读冒烟自检（7 项）/ read-only smoke test (7 checks)
│   ├── legal_common.py       # 共享路径解析 / shared path resolution
│   ├── convert_doc.ps1       # 旧版 .doc 转 .docx（仅 Windows）/ legacy .doc → .docx (Windows)
│   └── library_config.json   # 文库位置配置 / library location config
├── references/               # 模型按需加载的方法论与模板 / methodology & templates, loaded on demand
│   ├── review-methodology.md # 七步审查法、七维度表、执法审查要点 / 7-step method, 7 dimensions
│   ├── conflict-rules.md     # 位阶、新旧法/特别法、冲突裁决、溯及力 / hierarchy, conflicts, retroactivity
│   └── report-template.md    # 审查意见书 / 法制审核意见 / 答复模板 / opinion templates
└── library/                  # 自带文库（自包含）/ bundled library
    ├── 01-宪法/ … 05-司法解释/   # 原始 Word 文本，唯一数据源 / source .docx, the single source of truth
    ├── _manifests/final_manifest.json  # 官方元数据 / official metadata
    └── _text/                    # 脚本生成物，勿手改 / generated, do not edit
        ├── index.json           # 全量索引 / full index
        ├── titles.json          # 标题速查 / title lookup
        ├── library-map.md       # 分类导航 / category map
        └── <分类>/*.txt         # 带元数据头的纯文本 / plain text with metadata header
```

## 安装 · Installation

本 Skill 面向 [DSH（DeepSeek Harness）](https://www.deepseek.com/) 的文件系统技能机制，加载器会扫描技能根目录下的 `<技能名>/SKILL.md`，并通过文件监视**热发现**，新增技能无需重启。

> This skill targets the file-system skill mechanism of [DSH (DeepSeek Harness)](https://www.deepseek.com/). The loader scans `<skill-name>/SKILL.md` under the skills root and **hot-discovers** new skills via file watching — no restart needed.

1. 下载 / 克隆本仓库，得到 `legal-review` 文件夹（保持文件夹名不变）。

   > Download or clone this repository to get a `legal-review` folder (keep the folder name).

2. 把整个 `legal-review` 文件夹放进 DSH 的技能根目录：

   > Put the whole `legal-review` folder into the DSH skills root:

   - **Windows（默认 DSH_HOME）**：`%USERPROFILE%\.dsh\skills\`
   - **Windows（自定义 DSH_HOME，如 `D:\ai\.dsh`）**：`D:\ai\.dsh\skills\`
   - **macOS / Linux**：`~/.dsh/skills/`

   即最终路径形如 `...\.dsh\skills\legal-review\SKILL.md`。

   > The final path looks like `...\.dsh\skills\legal-review\SKILL.md`.

3. 环境要求：Windows / macOS / Linux 上装有 **Python 3.9+** 且命令行可调用 `python`。解析 `.docx` 无需第三方包；仅收录旧版 `.doc` 时，Windows 下调用本机 Word / WPS 自动转换。

   > Requirements: **Python 3.9+** available as `python` on Windows, macOS or Linux. No third-party package is needed to parse `.docx`; legacy `.doc` files are converted through local Word / WPS on Windows.

4. 自带文库已包含生成好的 `_text` 索引，**开箱即用，无需先跑同步**。装完建议跑一次自检。

   > The bundled library already ships with a generated `_text` index — **works out of the box, no sync needed**. Running the self-test once after installation is recommended.

用 Git 安装（便于后续 `git pull` 更新）／ Install with Git (easier to update later):

```bash
cd <your-skills-dir>
git clone <repository-url> legal-review
```

## 快速开始 · Quick Start

在 DSH 网页端 / 客户端中／ In the DSH web or desktop client:

- **自动触发**：直接提出任务，例如“帮我审查这份行政处罚告知书的程序是否合法”“行政拘留要不要告知听证权？依据第几条？”“这份规范性文件能不能设定罚款？”。模型会自动加载本技能，调用检索脚本并引用原文作答。

  > **Automatic triggering.** Just state the task, e.g. "review whether the procedure in this penalty notice is lawful", "must a hearing right be notified before administrative detention? Which article?", "can this normative document set fines?". The skill loads itself, runs the retrieval scripts and answers with quoted text.

- **手动触发**：输入 `/legal-review` 强制启用。

  > **Manual triggering.** Type `/legal-review` to force-enable the skill.

- **切换模型**：在 DSH 模型选择处切换 DeepSeek、智谱 GLM 等即可，技能逻辑与模型无关；若某模型不可用，先在 DSH 设置中配置对应服务商的 API Key。

  > **Switching models.** Pick DeepSeek, Zhipu GLM, etc. in DSH; the skill logic is model-independent. If a model is unavailable, configure that provider's API key in DSH settings first.

首次可让模型运行 `status` 确认文库就绪（把 `<SKILL>` 替换为技能实际所在绝对路径，即加载时给出的 Base directory）／ Ask the model to run `status` once to confirm the library is ready (replace `<SKILL>` with the actual absolute Base directory):

```powershell
python "<SKILL>\scripts\search_law.py" status
```

环境自检（只读，不修改任何文件，7 项全通过退出码为 0）／ Self-test (read-only, touches nothing, exit code 0 when all 7 checks pass):

```powershell
python "<SKILL>\scripts\selftest.py"
```

## 检索命令速查 · Command Reference

所有命令均在 `scripts/` 下，用 Python 运行；路径含中文请加引号。

> All commands live in `scripts/` and run with Python; quote paths that contain Chinese characters.

| 目的 / Purpose | 命令 / Command |
|---|---|
| 文库状态 / 统计 · Library status | `python search_law.py status` |
| 按名称找法律 · Find by title | `python search_law.py titles 行政处罚` |
| 查看元数据 / 版本 · Metadata / versions | `python search_law.py info 行政处罚法` |
| 全文检索条文 · Full-text search | `python search_law.py search 听证 行政拘留` |
| 读某条原文 · Read one article | `python search_law.py get 行政处罚法 --article 63` |
| 读结构与预览 · Structure & preview | `python search_law.py get 行政强制法` |

常用参数／ Common flags:

- `titles` / `search`：`--cat 02-法律` 限分类、`--all` / `--all-versions` 含旧版、`--limit N`<br>`--cat` to limit a category, `--all` / `--all-versions` to include superseded versions, `--limit N`
- `search`：多关键词默认“且”，`--any` 改“或”，`--law 治安管理处罚法` 限定某部法，`--regex` 正则<br>Multiple keywords are AND by default; `--any` switches to OR; `--law` restricts to one statute; `--regex` enables regex
- `get --article`：支持 `63`、`六十三`、`63-65`（范围）、`9,44,63`（逗号/顿号多段）<br>Accepts `63`, `六十三` (Chinese numerals), `63-65` (range), `9,44,63` (multiple articles)

## 更新文库 · Updating the Library

原始 Word 文件是**唯一数据源**，`_text` 与索引全部由脚本生成。设计上支持随时增量更新：

> The source Word files are the **single source of truth**; `_text` and the index are fully generated. Incremental updates are supported at any time:

1. **新增**：把 `.docx`（或旧版 `.doc`）放入 `library/` 下对应分类目录。文件名建议 `法律全称_公布日期yyyyMMdd.docx`（如 `中华人民共和国XX法_20260101.docx`），脚本据此解析标题与日期。清单内文件按官方元数据入库；清单外文件标注〖补充〗提示人工核对。

   > **Add.** Drop a `.docx` (or legacy `.doc`) into the matching category folder under `library/`. Name it `Full Title_yyyyMMdd.docx` (e.g. `中华人民共和国XX法_20260101.docx`); the script parses title and date from it. Files listed in the official manifest get official metadata; others are tagged 〖supplement〗 for manual verification.

2. **替换为新版**：把新版 Word 放入分类目录（同名覆盖或新日期文件名均可）；脚本按公布日期自动归组，检索默认只返回最新版，旧版保留并标记【旧版】可追溯。旧版若已失效，直接删除其源文件即可。

   > **Replace with a newer version.** Put the new Word file into the category folder (overwrite or use a new date in the filename). Versions are grouped by promulgation date; search returns only the latest by default, while older ones are kept and marked 【old】 for traceability. If the old version is no longer in force, delete its source file.

3. **删除**：从分类目录删除对应 Word 源文件。

   > **Delete.** Remove the corresponding Word source file from the category folder.

4. 运行增量同步（仅处理新增 / 变更 / 删除，通常几秒完成）／ Run the incremental sync (only new/changed/deleted files, usually seconds):

   ```powershell
   python "<SKILL>\scripts\sync_library.py"
   ```

   - 全量重建加 `--full`；跳过旧版 `.doc` 加 `--no-doc`。<br>Add `--full` to rebuild everything; `--no-doc` to skip legacy `.doc` files.
   - 同步会自动：抽取正文、写入元数据头、同法新旧版本归组、重建 `index.json` / `titles.json` / `library-map.md`、清理已删除源文件对应的文本。<br>Sync automatically extracts text, writes metadata headers, groups versions, rebuilds `index.json` / `titles.json` / `library-map.md`, and cleans up text for deleted sources.

5. 同步完成后即可检索，**无需重启 DSH**；不要手工编辑 `_text` 内文件（下次同步会被覆盖）。

   > Search works immediately after sync — **no DSH restart needed**. Do not hand-edit files under `_text`; they are overwritten on the next sync.

> 也可以直接让对话中的模型帮你做：把法规文件发它并说"加入法律文库后同步"。
>
> You can also delegate this to the model: send the file and say "add it to the law library and sync".

## 使用外部文库 · Using an External Library

默认使用技能自带的 `library/`（自包含、零配置）。若希望把更大的文库放在技能外部，三种方式任选，优先级从高到低：

> By default the bundled `library/` is used (self-contained, zero config). To keep a larger library outside the skill, pick any of the three options below, in descending priority:

1. 同步时临时指定：`python sync_library.py --root "D:\其它\法律文库"`；<br>Pass it at sync time: `python sync_library.py --root "D:\other\law-library"`;
2. 设置环境变量 `LEGAL_REVIEW_LIBRARY` 指向文库根目录（对检索与同步同时生效）；<br>Set the `LEGAL_REVIEW_LIBRARY` environment variable to the library root (affects both search and sync);
3. 编辑 `scripts/library_config.json`，把 `library_root` 改为文库绝对路径（相对路径则相对技能根目录解析）。<br>Edit `scripts/library_config.json` and set `library_root` to an absolute path (relative paths resolve against the skill root).

外部文库需包含同样的 `01-宪法` 等分类目录；首次使用先运行一次 `sync_library.py` 生成 `_text` 与索引。

> An external library must contain the same category folders (`01-宪法` etc.). Run `sync_library.py` once to generate `_text` and the index.

## 工作原理 · How It Works

- `.docx` 用 Python 标准库 `zipfile` + `xml.etree` 直接解析 `word/document.xml`，无需 python-docx；旧版 `.doc` 在 Windows 下经 `convert_doc.ps1` 调用 Word / WPS COM 批量转换。<br>`.docx` is parsed directly from `word/document.xml` using the standard library (`zipfile` + `xml.etree`) — no python-docx required. Legacy `.doc` files are batch-converted through Word / WPS COM on Windows via `convert_doc.ps1`.
- 每部法规范文切成"章标题 + 条文"结构，以行首"第X条"（兼容"第X条之一"）为条头，并跳过开头目录，保证条号定位准确。<br>Each statute is split into "chapter heading + article" structures, using a leading "第X条" (including "第X条之一") as the article head, skipping the table of contents so article numbers resolve correctly.
- 同标题法规按公布日期归组并标记最新版；检索默认只查最新文本，审查历史行为时可显式包含旧版。<br>Same-titled instruments are grouped by promulgation date and flagged with the latest version; search defaults to the latest text, and old versions can be included explicitly when reviewing historical conduct.
- `legal_common.py` 以脚本自身位置锚定技能根目录，再按 `--root` → 环境变量 → 配置 → 自带 `library/` 的顺序定位文库，因此整个技能文件夹可任意移动 / 复制。<br>`legal_common.py` anchors the skill root to the script's own location and resolves the library in the order `--root` → env var → config → bundled `library/`, so the whole folder can be moved or copied anywhere.

## 数据来源与时效 · Data Source & Currency

- 文本来源：国家法律法规数据库 <https://flk.npc.gov.cn>，采集口径为"现行有效"，**数据截至 2026-11-14**。<br>Source: the National Database of Laws and Regulations <https://flk.npc.gov.cn>, scoped to "currently effective", **data as of 2026-11-14**.
- 构成：宪法 7 篇、法律 355 篇、行政法规 612 篇、监察法规 2 篇、司法解释 574 篇，合计 1550 篇（其中同一法律的不同版本 64 篇，不同法律最新版 1486 部），约 773.1 万字。<br>Composition: 7 Constitution & amendments, 355 laws, 612 administrative regulations, 2 supervisory regulations, 574 judicial interpretations — 1,550 texts in total (64 superseded versions plus 1,486 latest versions), ≈ 7.73 million Chinese characters.
- 元数据（法律性质、制定机关、公布 / 施行日期）取自官方清单 `_manifests/final_manifest.json`；清单外用户自行补充的文件由文件名解析并标注〖补充〗。<br>Metadata (nature, enacting body, promulgation / effective dates) comes from the official manifest `_manifests/final_manifest.json`; user-added files outside the manifest are parsed from filenames and tagged 〖supplement〗.
- 法律会被修订或废止，**内置文本可能滞后**。正式使用前请通过官方渠道核对所引法规是否仍为现行有效版本，并按上文流程替换新文本。<br>Statutes get amended or repealed, so **bundled texts may lag behind**. Before formal use, verify through official channels that the cited instrument is still in force, and replace the text as described above.

## 版本与更新记录 · Version & Changelog

| 项目 / Item | 当前状态 / Status |
|---|---|
| 技能版本 · Skill version | 文库数据版 2026-11-14 · library snapshot 2026-11-14 |
| 文库规模 · Library size | 1550 篇 / 约 773.1 万字 · 1,550 texts / ≈ 7.73M characters |
| 最近同步 · Last sync | 2026-11-23（并入 2026-10-24、2026-11-14 两轮更新，新增 36 件）· merged the 2026-10-24 and 2026-11-14 rounds, 36 new instruments |
| 运行依赖 · Runtime | Python 3.9+（标准库，无第三方包）· Python 3.9+, stdlib only |

历史更新明细（含新增法规清单、数据勘误）见 [CHANGELOG.md](CHANGELOG.md)。

> Detailed history (new instruments, data errata) is in [CHANGELOG.md](CHANGELOG.md).

## 能力边界 · Scope & Limitations

- 内置文库**仅含国家级文本**（宪法、法律、行政法规、监察法规、司法解释），**不含地方性法规、部门规章、地方政府规章、党内法规、军事法规、国际条约及港澳台地区法律**，也不含各类规范性文件。审查对象引用这类依据时，需另行提供官方文本，模型会明确标注"不在文本库核验范围"。<br>The library covers **national-level texts only** (Constitution, laws, administrative regulations, supervisory regulations, judicial interpretations). It **excludes local regulations, ministerial rules, local government rules, Party regulations, military regulations, international treaties, the law of Hong Kong/Macao/Taiwan, and all normative documents**. If a reviewed document relies on such sources, supply the official text separately; the model will flag it as "outside the verification scope of this library".
- 审查意见一般不直接宣告文件 / 行为无效，而是指出冲突与依据，提出纠正、撤销、补正、重新履行程序或提请有权机关处理的建议。<br>Review opinions generally do not declare a document or act void; they identify the conflict and its basis, and recommend correction, revocation, supplementation, re-running the procedure, or referral to the competent authority.
- 检索能力受关键词选择、条文切分质量、文本完整性影响，**检索不到依据 ≠ 无依据**，需换关键词、查上位法或补充材料后复核。<br>Retrieval quality depends on keyword choice, text segmentation and completeness. **No hit does not mean no basis** — retry with other keywords, check higher-level norms, or supply more material.

## 免责条款 · Disclaimer

**请在使用前完整阅读本节。下载、安装、运行本技能，或使用其脚本、文库、参考文档及由此生成的任何内容，即视为您已阅读、理解并同意接受以下全部条款。如不同意，请立即停止使用并删除本技能。**

> **Read this section in full before use.** By downloading, installing or running this skill, or by using its scripts, library, reference documents or any output derived from them, you confirm that you have read, understood and accepted all clauses below. If you do not agree, stop using it immediately and delete it.

**1. 不构成法律意见 · Not Legal Advice**

本技能是**技术工具**，其输出（包括检索到的条文、模型生成的分析、审查意见、风险提示、结论与建议）均为自动化处理结果，**不构成法律意见、法律咨询意见或专业判断**，不具有任何法律效力。任何依据本技能输出作出的决定，均不应视为已获得法律专业支持。

> This skill is a **technical tool**. Its output — retrieved provisions, model-generated analysis, review opinions, risk notes, conclusions and recommendations — is the product of automated processing and **does not constitute legal advice, legal consultation or professional judgment**, and has no legal effect. No decision based on this output should be regarded as legally supported.

**2. 不替代专业法律服务 · No Substitute for Professional Legal Services**

本技能不能替代执业律师、公职律师、公司律师、法律顾问、法制审核机构、行政复议机关、司法机关、公证机构、司法鉴定机构或其它有权机关依法定程序作出的专业判断与正式文书。涉及诉讼、仲裁、行政处罚、行政许可、行政强制、刑事风险、重大合同、公司治理、知识产权、涉外交易等事项，**应当委托具备相应资质的专业人士处理**。

> This skill cannot replace the professional judgment and formal documents produced, under statutory procedures, by practicing lawyers, government or in-house counsel, legal-affairs review bodies, administrative reconsideration organs, judicial organs, notary offices, forensic appraisal institutions or other competent authorities. For litigation, arbitration, administrative penalties, permits, coercive measures, criminal exposure, major contracts, corporate governance, intellectual property or cross-border transactions, **engage qualified professionals**.

**3. 不得作为唯一依据 · Not a Sole Basis**

本技能输出的条文、结论与意见**不得作为下列行为的唯一依据**：作出行政处罚、行政强制、行政许可等执法决定；提起或应对诉讼、仲裁；出具正式法律意见书、法制审核意见；签署合同或作出重大商业决策；向监管机关报送材料。上述场景必须以**官方公布文本**为准，并履行法定程序、留存书面证据。

> Output from this skill **must not be the sole basis** for: enforcement decisions such as penalties, coercive measures or permits; filing or defending litigation or arbitration; issuing formal legal opinions or legal-affairs review opinions; signing contracts or making material business decisions; or submissions to regulators. In all such cases the **officially published text** governs, and statutory procedures and written evidence must be observed.

**4. 文本时效性、完整性与准确性 · Currency, Completeness and Accuracy**

（1）内置文本采集于国家法律法规数据库，**数据截至 2026-11-14**，此后公布、修订、废止、修正的法规不在库内，库内文本亦可能因数据库更新、版本替换而滞后。

> (1) Texts were captured from the national database and are **current as of 2026-11-14**. Instruments promulgated, amended, repealed or corrected after that date are not included, and included texts may lag behind database updates or version replacements.

（2）文库**不含**地方性法规、自治条例和单行条例、部门规章、地方政府规章、军事法规、党内法规、国际条约、各类指导性案例与规范性文件，以及港澳台地区法律。

> (2) The library **excludes** local regulations, autonomous ordinances and separate regulations, ministerial rules, local government rules, military regulations, Party regulations, international treaties, guiding cases and normative documents of all kinds, and the law of Hong Kong, Macao and Taiwan.

（3）文本经程序化抽取与切分，**可能出现条号错位、段落丢失、格式串行、字符错误、旧版未及时清理**等情形；`.doc` 转换依赖本机 Word/WPS，转换失败或被跳过时相关法规可能缺失。

> (3) Texts are extracted and segmented programmatically, so **misnumbered articles, dropped paragraphs, merged formatting, character errors or uncleaned superseded versions** may occur. `.doc` conversion depends on local Word/WPS; if it fails or is skipped, the affected instruments may be missing.

（4）当本技能输出与官方文本不一致时，**一律以官方文本为准**（全国人大及其常委会公报、国务院公报、最高人民法院与最高人民检察院公布文本、国家法律法规数据库 <https://flk.npc.gov.cn> 等）。

> (4) Where output conflicts with the official text, **the official text prevails** (Gazette of the NPC and its Standing Committee, State Council Gazette, texts published by the Supreme People's Court and Supreme People's Procuratorate, the national database <https://flk.npc.gov.cn>, etc.).

**5. 模型输出固有风险 · Inherent LLM Risks**

大语言模型存在**幻觉、条号错引、条文拼接、过度概括、时效混淆、对事实的误读**等固有缺陷。本技能通过"强制检索原文"降低此类风险，但**不能消除**。使用者应对每一条被引用的法条自行核对名称、条号、款项、施行日期与现行有效性，不得直接采信模型生成的条文内容或结论。

> Large language models suffer from **hallucination, misattributed article numbers, spliced provisions, overgeneralization, date confusion and misreading of facts**. Forcing retrieval of source text reduces — but **cannot eliminate** — these risks. Verify every cited provision yourself: name, article, paragraph, effective date and current validity. Do not rely directly on model-generated text or conclusions.

**6. 无任何担保 · No Warranty**

本技能按**"现状"（AS IS）**提供，不附带任何明示或默示的担保，包括但不限于：适销性、特定用途适用性、准确性、完整性、及时性、不侵权、无病毒、不中断、无错误。作者与贡献者**不承诺**本技能能满足您的特定需求，也不承诺任何缺陷会被修复。

> This skill is provided **"AS IS"**, without any express or implied warranty, including but not limited to merchantability, fitness for a particular purpose, accuracy, completeness, timeliness, non-infringement, freedom from viruses, uninterrupted operation or absence of errors. The authors and contributors **do not warrant** that it meets your requirements or that any defect will be fixed.

**7. 责任限制 · Limitation of Liability**

在适用法律允许的最大范围内，作者、贡献者及分发者**不对**因使用或无法使用本技能而产生的任何**直接、间接、附带、特殊、惩罚性、示范性或后果性损失**承担责任，包括但不限于：利润损失、业务中断、数据丢失、商誉损害、行政处罚、诉讼败诉、赔偿责任、刑事责任风险、第三方索赔及合理的律师费。**即使已被告知上述损失的可能性**，亦不承担责任。若部分法域不允许排除或限制某些责任，则本条款在该法域内按法律允许的最大限度适用。

> To the maximum extent permitted by applicable law, the authors, contributors and distributors **shall not be liable** for any **direct, indirect, incidental, special, punitive, exemplary or consequential damages** arising from the use of, or inability to use, this skill, including but not limited to lost profits, business interruption, data loss, loss of goodwill, administrative penalties, adverse litigation outcomes, indemnity obligations, criminal exposure, third-party claims and reasonable legal fees — **even if advised of the possibility of such damages**. Where a jurisdiction does not allow the exclusion or limitation of certain liabilities, this clause applies to the fullest extent permitted there.

**8. 使用者义务 · User Obligations**

使用者承诺：（1）自行核验所有引用条文的准确性与时效性；（2）在正式场景中取得专业人士或有权机关的复核；（3）遵守《中华人民共和国保守国家秘密法》《中华人民共和国数据安全法》《中华人民共和国个人信息保护法》《中华人民共和国网络安全法》等法律法规；（4）**不得**将本技能用于违法目的、规避法律监管、伪造法律依据、误导他人或从事不正当竞争；（5）因自身使用行为产生的全部后果自行承担。

> You agree to: (1) verify the accuracy and currency of every cited provision yourself; (2) obtain professional or competent-authority review before formal use; (3) comply with the PRC Law on Guarding State Secrets, Data Security Law, Personal Information Protection Law, Cybersecurity Law and other applicable laws; (4) **not** use this skill for unlawful purposes, to evade regulatory oversight, to fabricate legal bases, to mislead others or for unfair competition; and (5) bear all consequences of your own use.

**9. 保密与信息安全 · Confidentiality and Information Security**

本技能脚本**在本地运行**，不主动上传您的文书或检索记录。但请注意：（1）在对话中使用本技能时，您输入的内容会经由所接入的模型服务商按其服务条款处理，可能涉及跨境传输或用于服务改进；（2）**涉密文件、国家秘密、工作秘密、商业秘密、个人隐私、敏感个人信息**不得提交至不符合相应保密与合规要求的环境；（3）使用者应自行评估所用模型服务、网络环境、终端设备的安全性与合规性。

> The scripts run **locally** and do not upload your documents or search history on their own. However: (1) when used in a chat, your input is processed by the connected model provider under its terms of service, possibly involving cross-border transfer or service improvement; (2) **classified documents, state secrets, work secrets, trade secrets, personal privacy and sensitive personal information** must not be submitted to environments that do not meet the corresponding confidentiality and compliance requirements; (3) you must assess the security and compliance of the model service, network and devices you use.

**10. 知识产权 · Intellectual Property**

（1）`scripts/`、`references/`、`SKILL.md` 等代码与文档采用 MIT 许可证（见 [LICENSE](LICENSE)）。（2）`library/` 内法律法规文本为国家机关依《中华人民共和国著作权法》第五条公布的官方文件，不适用著作权法保护，其内容的权威解释权归制定机关。（3）本技能为**非官方**项目，与全国人大常委会、国务院、最高人民法院、最高人民检察院、司法部及国家法律法规数据库运营方**无隶属、合作或授权关系**；不得以任何方式宣称本技能为官方产品或代表官方立场。

> (1) Code and documentation in `scripts/`, `references/` and `SKILL.md` are licensed under MIT (see [LICENSE](LICENSE)). (2) Statutory texts in `library/` are official documents published under Article 5 of the PRC Copyright Law and are not protected by copyright; authoritative interpretation rests with the enacting body. (3) This is an **unofficial** project with **no affiliation, partnership or authorization** from the NPC Standing Committee, the State Council, the Supreme People's Court, the Supreme People's Procuratorate, the Ministry of Justice or the operator of the national database. Do not present it as an official product or as representing official positions.

**11. 条款变更与可分割性 · Changes and Severability**

作者有权随时修改本免责条款，修改后的条款自仓库更新之日起生效。若本条款任何部分被认定无效或不可执行，其余部分仍完全有效；该无效部分应在法律允许范围内作最接近原意的解释。

> The authors may revise this disclaimer at any time; revisions take effect when the repository is updated. If any part is held invalid or unenforceable, the remaining parts stay in full force, and the invalid part shall be interpreted as closely as permitted to its original intent.

**12. 适用法律与争议解决 · Governing Law and Disputes**

本条款的订立、效力、解释、履行及争议解决适用**中华人民共和国法律**（为本条款之目的，不含香港特别行政区、澳门特别行政区及台湾地区法律）。因本技能产生的争议，双方应友好协商解决；协商不成的，提交作者所在地有管辖权的人民法院诉讼解决。

> The formation, validity, interpretation, performance and dispute resolution of these terms are governed by the **laws of the People's Republic of China** (excluding, for this purpose, the laws of the Hong Kong SAR, the Macao SAR and the Taiwan region). Disputes shall first be resolved through friendly negotiation; failing that, they shall be submitted to the competent people's court at the authors' location.

---

**一句话总结：这是一个帮你"查得准、引得对"的检索工具，不是一个能替你担责的法律顾问。凡是要签字、要盖章、要上法庭、要下处罚决定的地方，请让人来负责。**

> **In one sentence: this is a retrieval tool that helps you find and cite the right text — not a legal adviser that shares your liability. Wherever a signature, a seal, a courtroom or a penalty decision is involved, let a human be responsible.**

## 许可证 · License

- 脚本与方法论文档（`scripts/`、`references/`、`SKILL.md` 等）采用 [MIT License](LICENSE)。<br>Code and methodology documents (`scripts/`, `references/`, `SKILL.md`, etc.) are under the [MIT License](LICENSE).
- `library/` 内的法律法规文本为国家机关依《中华人民共和国著作权法》第五条公开的官方文件，不适用著作权法保护，详见 [LICENSE](LICENSE) 文末说明。<br>Statutory texts in `library/` are official documents published under Article 5 of the PRC Copyright Law and are not protected by copyright; see the notes at the end of [LICENSE](LICENSE).
