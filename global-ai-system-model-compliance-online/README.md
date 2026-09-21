# Global AI System/Model Compliance

这是现有合规 Skill 的说明文档。它的唯一有效内部名称和安装目录名都是
`global-ai-system-model-compliance`，界面默认提示使用
`$global-ai-system-model-compliance`。`ai-transparency-compliance` 只表示旧版迁移历史，不应继续作为可发现、
可调用或并行安装的 Skill。

当前包版本见 `SKILL.md` 的 `metadata.version`（本次为 2.5.1）；资料截点见
`metadata.knowledge_cutoff`。法律效力和适用日期仍以运行时本地索引及最新欧盟官方文本为准。问卷路线清单
`assets/questionnaire-route.json` 本次为 2.5.1。

## 这项 Skill 做什么

它面向具体的 AI 平台、产品、模型、API、App、SaaS、硬件或内部部署场景。Skill 先让业务人员用白话
回答可观察事实，再把事实映射到三层风险路径，输出：

1. 直接显示在对话正文中的中文自然语言结论、建议、待办和最严重后果；
2. 现行法律、未来生效日期、官方依据和待人工复核事项；
3. 可供系统留存的结构化 JSON 和审计字段。Markdown 报告和 JSON 是审计附件，不能代替对话正文的业务说明。

它不是一般性数据跨境审计，也不替代律师、主管机关、数据保护机构、合格评定机构或正式法律意见。
GDPR、CCPA/CPRA、跨境传输、版权、产品责任和终端设备规则，只有在事实显示它们与本次 AI 平台的
输入、输出、日志、附件、备份、供应商或远程访问有关时才作为附属筛查。

## 三层评估边界

| 层级 | 优先回答的问题 | 结果应说明 |
|---|---|---|
| 第一层：透明度核心 | 中国大陆、欧盟、美国加州是否需要交互告知、可见标识、机器可读标记或来源凭证 | 谁在什么场景做什么、怎样测试和留证、未处理的最严重后果 |
| 第二层：EU AI Act | 系统是否可能属于不可接受风险或高风险；模型是否可能属于 GPAI 或系统性风险 | 初步路径、角色、现行或未来义务、上线阻断项 |
| 第三层：AI 平台附属筛查 | 本平台的数据流、控制者/处理者/子处理者、跨境机制、美国敏感数据、版权和产品规则接口 | 仅针对本平台的补证清单和相邻风险提示 |

透明度是第一核心。EU AI Act 系统层和模型层是第二核心。第三层不能反过来变成脱离 AI 平台的通用
隐私或跨境项目。

## 评估模式和进度

每次新评估首轮只发送 `P0`，让用户选择：

- 轻量版初步评估：只收集普通业务人员能观察的事实，用来发现透明度红线、明显 EU AI Act 路径和升级理由；
- 全量版完整评估：按实际触发范围收集三层事实、证据和整改信息；
- 不确定：按轻量版继续，记录为已提交但待内部核实。

模式题 `P0` 独立完成后，才发送公开范围入口 `P1` 至 `P4` 四步。四步入口收齐并完成后台登记后锁定路线：

- 轻量版固定为 `LT1`、`LT2` 两组；每组固定 5 题，整条路线固定 10 题。`LT1` 为 `P5`、`B1`、`B2`、`B3`、`C1`，`LT2` 为 `C2`、`C3`、`D0`、`E0`、`F0`。后五题分别覆盖透明度、欧盟系统线索、模型线索和 AI 平台附属数据线索；`P2`、`P3` 只控制全量版详细组，不改变轻量版题数；
- 全量版固定保留透明度核心 `T1` 至 `T3`，再按事实启用系统、模型和附属筛查，锁定为 3 至 7 组；
- 正常新轮次发送 2 至 8 题，只有补漏或纠正冲突时才发送 1 题；
- 每轮明确显示总组数、当前组、已完成组和剩余组。已选择“不确定”的题目算已提交，不再重复提问，但会进入待核清单。

全量版的 `P6` 是资料能力门控，只有用户明确选择“可以查看或协调核对技术、数据或合同资料”时，才展开
技术细节；其他选择继续业务主线，并把细节列为补证，不要求业务人员猜测服务器、密钥、模型权重或法律角色。

用户明确更正答案时，直接采用新答案并记录 `revision`、来源和时间；只有模式尚未明确时才提供模式选择，不能
把更正后的事实静默混入旧路线或重复询问已提交的题目。

## 业务交互和结果要求

- 问题按组发送，不一次加载整份问卷；每个选项单独一行，问题和选项不使用星号字符。
- 每组问题之后给业务自测表，必须使用渲染器生成的公开行；选项单独以 `-` 开头一行，不能用分号串接，表头最后一列固定为“填写注释（给业务部门）”。
- 业务可见标签使用“模式题”“第1步”至“第4步”“开始问题”或“第1题”（同一条消息保持一致）以及“资料深度问题”，不显示内部 `P`、`R` 或路线键；路线锁定后的首行固定写出总组数、当前组、已完成组、剩余组和本轮待答题数。
- 业务只填写事实，不判断“禁止性实践”“高风险”“GPAI”“控制者”或“处理者”。不清楚时直接选“不确定”。
- 报告正文先用自然语言告诉业务部门现在应做什么、是否暂缓上线、谁需要补什么，以及不处理的最严重后果；法律依据集中放在后段。
- 轻量版只能输出“初步风险提示”，不得输出无条件“合规”或“可上线”。全量版在关键事实、官方版本或强制义务未核实时，也不得给无条件合规结论。
- 机器可读透明度要单独说明告知、元数据/凭证、验证接口、转码和转发后的保持性测试，以及标识失效时的补标、阻断或告知措施。C2PA、XMP、EXIF、JSON 字段和数字水印只是工程选项，不是法律唯一格式。

## 法律效力和资料库

本 ZIP 是无内置数据库版本。它不包含 `corpus/`、网页快照、法律原文摘录或 `sources.jsonl` 初始库；欧盟资料 URL 固定在 `scripts/fetch_official_sources.py` 中。首次评估前运行：

```text
python3 scripts/fetch_official_sources.py --dry-run
python3 scripts/fetch_official_sources.py --profile core
```

如需指南、CoP、FAQ、接口法和标准化入口，再运行 `--profile all`。脚本只允许欧盟官方主机名，下载结果写入本地 `references/eu-ai-regulatory-library/`，失败项写入报告并保留待人工复核状态。该联网版与完整版使用同一个 Skill 内部名称，不应与完整版同时安装为两个可发现目录；它只是没有预置资料的分发方式。

已生效的条例、指令及其转置法和正式决定属于强制性法律。Commission、AI Office、AI Board、Service Desk
指南、FAQ 和 Code of Practice 统一标为“欧盟建议的良好实践/解释性材料（非独立法定义务）”，不能写成
安全港、自动免责或全面合规推定。标准通常自愿；只有在 Official Journal 正式引用且覆盖范围吻合时，才另行
核验其可能产生的符合性推定。

EU 结论按以下顺序检索本地资料：

1. 运行 `scripts/fetch_official_sources.py --profile core` 或 `--profile all`；
2. `references/eu-ai-regulatory-library/metadata/sources.jsonl` 中本次生成的记录；
3. 下载后的 EUR-Lex Official Journal、最新 consolidated text 和 Annex I 文件；
4. 与问题直接相关的指南、FAQ、CoP 和标准化材料。

欧盟法律库的基准版本包括 AI Act 原始文本 CELEX `32024R1689`、现行合并文本
CELEX `02024R1689-20260727`、Digital Omnibus Regulation (EU) 2026/1744（CELEX `32026R1744`），以及
COM(2025) 836 和相关立法程序材料。Annex I 以 2026/1744 修订后的 20 项矩阵为准；Directive 2006/42/EC
只作为历史或过渡资料。每个结论仍必须回到本地记录的 EUR-Lex Official Journal、ELI、版本日期和适用状态。

不能用新闻稿、搜索摘要、律师文章、商业数据库或非官方镜像填补缺口。下载失败要记录官方 URL、原因、日期和
下一步人工获取建议；未来义务必须同时写官方适用日期和现在可准备的材料。

## 本地部署和维护

从 ZIP 更新时，将解压后的 Skill 根目录安装到
`~/.codex/skills/global-ai-system-model-compliance`（如环境设置了 `CODEX_HOME`，使用其 `skills` 子目录）。
若存在旧安装 `~/.codex/skills/ai-transparency-compliance`，先把它移出有效 `skills` 目录并保留为日期备份，再安装
新版本；不要让新旧目录同时处于可发现状态，也不要建立 `-v2` 等平行 Skill。确认唯一有效安装目录根部存在
`SKILL.md`，并重新加载 Codex 的 Skill 列表。

业务调用示例：

```text
使用 $global-ai-system-model-compliance 评估这个 AI 平台。先让我选择轻量版、全量版或不确定，再按组提问，并在每组后给业务自测表。
```

维护人员从 Skill 根目录运行：

```text
python3 -B scripts/render_business_table.py --check
python3 -B scripts/check_business_answers.py path/to/business-answers.md --json
python3 -B scripts/questionnaire_progress.py path/to/business-answers.md --json
python3 -B scripts/validate_business_message.py path/to/business-message.md --json
# 路线锁定后的消息还要强制检查首行总组数、当前组、已完成、剩余和本轮待答题数
python3 -B scripts/validate_business_message.py path/to/locked-business-message.md --locked-route --json
python3 -B scripts/validate_assessment.py path/to/assessment.json --report path/to/report.md
python3 -B scripts/lint_report.py path/to/assessment.json path/to/report.md
python3 -B scripts/fetch_official_sources.py --profile all --dry-run
```

`--dry-run` 只列出官方 URL，不联网、不写文件。实际下载后要查看
`references/eu-ai-regulatory-library/metadata/last-fetch-report.json` 中的失败项、内容类型和 SHA-256；资料库统计会变化，不能把成功 HTTP 响应直接当作法律效力结论。

## 主要文件

| 用途 | 文件 |
|---|---|
| Skill 主指令 | `SKILL.md` |
| 业务问卷和路由 | `assets/questionnaire.md`、`assets/questionnaire-route.json` |
| 业务自测表 | `assets/business-self-check-table.md`、`assets/business-self-check-table-public.md` |
| 业务消息格式检查 | `scripts/validate_business_message.py` |
| 报告和机器结果 | `assets/report-template.md`、`assets/assessment-schema.json` |
| 规则和角色参考 | `references/ai-platform-assessment.md`、`references/role-mapping.md`、各法域规则文件 |
| EU 权威资料库 | `references/eu-ai-regulatory-library/` |
| 资料库地图与覆盖报告 | `references/eu-ai-regulatory-library/metadata/source-map.md`、`coverage-matrix.md` |
| 详细使用教程 | [使用说明与操作指南](使用说明与操作指南.md) |

本 Skill 的法律资料截点和缺口都可能变化。真实上线或发布前，重新运行只读索引并核对 EUR-Lex Official Journal、
最新 consolidated version、目标成员国转置法和相关主管机关页面。
