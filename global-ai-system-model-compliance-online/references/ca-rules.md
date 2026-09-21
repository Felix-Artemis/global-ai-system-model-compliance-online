# 加州规则库：California AI Transparency Act（SB 1000 正式通过版，Enrolled）

效力提示：B&P Code和正式生效的实施规则属于强制性州法；“广泛接受的行业标准”、C2PA、NIST、行业框架或其他技术规范本身不是独立法定义务。引用这些材料时，统一标注“建议性良好实践/解释性材料（非独立法定义务）”，不得写成安全港或自动免责依据。

```yaml
last_verified: 2026-09-05
status: SB 1000 已通过待签署（Enrolled 2026-08-30 誊清；2026-09-02 下午3时提交州长）
next_recheck_before: 2026-12-04
```

> 核验日期：2026-09-05
> 来源层级：**官方 Enrolled 原文**——SB 1000 正式通过版（Enrolled）全文已打包至 `references/sources/CA-SB1000-enrolled.md`；现行法签署版仍见 `CA-SB942-chaptered.md`、`CA-AB853-chaptered.md`
> 官方来源：
> - SB 1000（2025–2026 会期，Enrolled 2026-08-30）：https://leginfo.legislature.ca.gov/faces/billHistoryClient.xhtml?bill_id=202520260SB1000
> - SB 942（2024, Ch. 291）：https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB942
> - AB 853（2025, Ch. 674）：https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260AB853
> 法典位置：Business and Professions Code, Division 8, Chapter 25（§§22757–22757.6）

---

## 〇、效力状态开关（★每次使用前必读，决定义务基准）

SB 1000 为 CAITA 修正案，**已通过议会、尚待州长签署**，属**紧急法案（urgency statute）**，一经签署或自动成为法律即**立即生效**。据此，本规则库**主存 SB 1000 生效版**，但**义务基准随签署状态切换**：

| 州长状态（联网核验后写死） | 现行有效义务基准 | SB 1000 处理 |
|---|---|---|
| **待签署**（窗口期内未行动） | SB 942 经 AB 853 修正（现行法） | 标注「前瞻、非现行」 |
| **已签署** | SB 1000 生效版 | 即时生效，SB 942 转历史对照 |
| **否决**（议会未推翻） | SB 942 经 AB 853 修正（现行法） | 标注「未通过、不适用」 |
| **超期未行动** | SB 1000 生效版 | 自动成为法律，即时生效 |

> **签署期限（加州宪法 Art. IV §10(b)(2)）**：SB 1000 属「9 月 1 日前通过、9 月 1 日后在州长手中」情形，州长须于 **2026-09-30** 前签署或否决，否则法案**自动成为法律**（加州无 pocket veto）。
> **当前状态（核验于 2026-09-05）**：待签署（Enrolled 2026-08-30；2026-09-02 提交州长）。**此状态下，现行有效义务仍以 SB 942 经 AB 853 修正为准**，SB 1000 生效版仅作前瞻变更提示；待签署或自动成为法律后，以 SB 1000 生效版为准。
> 报告生成时的处理规则见 `references/sb1000-diff.md` 与 SKILL.md 运行时指令。

---

## 一、生效时间线

| 节点 | 内容 | 依据 |
|------|------|------|
| 2026-08-02 | 全章生效（现行法，SB 942 经 AB 853 修正） | §22757.6（AB 853 修正） |
| 签署 / 2026-09-30 后自动 | **SB 1000 修订即时生效**（紧急法案） | SB 1000 SEC. 8 |
| 2027-01-01 | large online platform 义务生效 | §22757.3.1(c) |
| 2027-01-01 | GenAI hosting platform 义务生效 | §22757.3.2(b) |
| 2028-01-01 | capture device manufacturer 义务生效，仅适用于 2028-01-01 起**首次在州内生产销售**的设备 | §22757.3.3(c)及(a) |
| 2029-01-01 | 辅助技术字段（§22757.3(a)(1)(F)）生效；辅助技术限时豁免（§22757.5(b)）到期；§22757.4.1 专项罚则废止 | §22757.3(a)(1)(F)、§22757.5(b)、§22757.4.1(c) |

## 二、义务主体与义务清单（双轨：现行法 / SB 1000 生效版）

> **义务基准切换（★每次使用前必读，与「〇、效力状态开关」一致）**：
> - **待签署/否决期**：报告正文义务详述用 **「现行法义务清单」（SB 942 经 AB 853 修正，见下方）**；SB 1000 修订点**集中**列一个「SB 1000 前瞻变更提示」块（逐条「现行→前瞻」对照，见 `references/sb1000-diff.md`），标注「待签署、未生效」，**不得散落正文逐条挂〔SB 1000 修订〕角标**。
> - **已签署/超期自动成为法律**：报告正文改按 **「SB 1000 生效版义务清单」（下方 ### 1–5）**，SB 942 转历史对照。

### 现行法义务清单（SB 942 经 AB 853 修正）——待签署期正文基准

> 术语译法以 `references/glossary.md` 为准。以下条文据 SB 942（Ch. 291）＋ AB 853（Ch. 674）合并现行文本逐字转述（逐字依据 `references/sources/CA-SB942-chaptered.md`、`CA-AB853-chaptered.md`）。

#### A1. Covered provider（受管辖的提供者）

**定义（§22757.1(d)）**：创建、编码或以其他方式生产生成式人工智能系统，且该系统**月访问量或用户超过 1,000,000（100万）**、并在加州地理边界内公开可访问的主体。

**GenAI 系统定义（§22757.1(f)）**：能生成衍生合成内容（含文本、图像、视频、音频）的 AI。**注意：定义含文本，但下述实质义务条款（§22757.2、§22757.3）仅适用于图像、视频、音频或其组合，不含纯文本输出**（纯文本豁免提示见下方 SB 1000 版 §22757.1(g) 说明，两版一致）。

**义务清单**：

| 义务 | 内容 | 条文锚点 |
|------|------|----------|
| 免费 AI 检测工具 | 供用户评估图/视/音频内容是否由其 GenAI 系统创建或改动；输出检测到的 system provenance data；**不得输出检测到的 personal provenance data**；公开可访问（可设合理限制防安全风险）；支持上传内容或 URL；支持含 API 的免访问网站调用 | §22757.2(a)(1)–(6) |
| 工具反馈与隐私限制 | 收集用户反馈改进工具；不得收集/保留工具用户的个人信息（提交反馈且 opt-in 的除外，且仅用于改进工具）；不得超期保留提交内容；不得保留个人来源数据 | §22757.2(b)(c) |
| **显式披露（manifest）选项** | 应当**向用户提供选项**，在图像/视频/音频（或组合）内容中纳入显式披露：①标识为 AI 生成内容 ②清晰、显著、适合媒介、理性人可理解 ③永久或极难移除 | §22757.3(a)(1)–(3) |
| 隐式披露（latent） | 应当在 AI 生成图像/视频/音频内容中纳入隐式披露：①传达（直接或经永久链接）提供者名称、GenAI 系统名称与版本号、创建/改动时间日期、唯一标识符 ②可被 AI 检测工具检得 ③符合广泛接受的行业标准 ④永久或极难移除 | §22757.3(b)(1)–(4) |
| 被许可方合同传导 | 许可时**以合同要求**被许可人维持系统纳入隐式披露的能力；知悉被许可人修改致其不再能纳入披露的，**96 小时内撤销许可**；被许可人在许可撤销后应停止使用 | §22757.3(c)(1)–(3) |

> **本清单不含**辅助技术（assistive technology）条款、**不含**禁止虚假辅助技术陈述（§22757.3(d)）——此二者均为 SB 1000 新增，现行法没有。

> **现行法口径的「多原因不触发分层表述」**（待签署期正文用，与 SB 1000 版 §1.1 规则同理但门槛不同）：主导原因（主体门槛）=「月访问量/用户未达 100 万（§22757.1(d)）→不构成 covered provider，全章义务不触发」；层级抗辩（输出模态）=「退一步，即便构成 covered provider，纯文本输出亦不落入 §22757.2/§22757.3（限图像/视频/音频）义务范围」。SB 1000 生效后，主导原因才改为「不在加州公开可访问（§22757.1(e)）」（见下方 §1.1）。

#### A2. Large online platform / GenAI hosting platform / Capture device manufacturer

> 此三主体义务经 SB 1000 **未作修订**，现行法清单与 SB 1000 生效版**实质内容一致**，正文引用以 SB 1000 版对应小节（下方 ### 2、3、4）为准。注意定义条编号差异：现行法下 GenAI hosting platform 为 §22757.1(g)、large online platform 为 §22757.1(h)、capture device 为 §22757.1(b)(c)；SB 1000 重编号后为 §22757.1(h)(i)(c)(d)。实质义务条文（§22757.3.1/.3.2/.3.3）不变。

#### A3. 罚则（现行法，§22757.4）

| 项目 | 内容 |
|------|------|
| 罚款 | 违反本章者按**每次违规 5,000 美元**计（§22757.4(a)(1)） |
| 按日计罚 | covered provider、large online platform、capture device manufacturer 违规的，每日视为独立违规（§22757.4(b)） |
| **被许可方禁令救济** | 就被许可人违反 §22757.3(c)(3) 停止使用义务，可诉请禁令救济及合理律师费与成本（§22757.4(c)） |
| 执法主体 | 检察长、市检察官、郡法律顾问 |

> **注意**：现行法 §22757.4(c) 为「被许可方禁令救济」；SB 1000 删除该款并改为「过渡条款」，另新增 (d) 排除虚假辅助技术陈述（见下方「四、罚则与执法」）。

#### A4. 豁免（现行法，§22757.5）——五类

本章不适用于任何仅提供**非用户生成的电子游戏、电视、流媒体、电影或互动体验**的产品、服务、网站或应用。

#### A5. 生效（现行法，§22757.6）

本章于 **2026-08-02** 生效（AB 853 由原 2026-01-01 延后）。

---

> **以下 ### 1–5 为 SB 1000 生效版义务清单（生效后正文基准）**；待签署期正文用上面的现行法清单。术语译法以 `references/glossary.md` 为准，条文均据 SB 1000 Enrolled 逐字原文转述。

### 1. Covered provider（受管辖的提供者）

**定义（§22757.1(e)，SB 1000 修订）**：创建、编码或以其他方式生产生成式人工智能系统，且该系统**在加州地理边界内公开可访问**的主体。**SB 1000 已删除「月访问量或用户超过 100 万」门槛**，适用范围从头部企业扩张至几乎所有在加州可公开访问的 GenAI 系统提供者。

**GenAI 系统定义（§22757.1(g)）**：能生成衍生合成内容（含文本、图像、视频、音频）的 AI。**注意：定义含文本，但下述实质义务条款（§22757.2、§22757.3）全部仅适用于图像、视频、音频或其组合，不含纯文本输出。**

> **§22757.1(e) 原文**："Covered provider" means a person that creates, codes, or otherwise produces a generative artificial intelligence system that is publicly accessible within the geographic boundaries of the state.
>
> **⚠️ 纯文本提供者实质义务豁免（写作时主动提示）**：§22757.2（披露验证工具）与§22757.3（隐式披露）的义务对象均为"image, video, or audio content, or content that is any combination thereof"，**不含纯文本输出**。因此：仅生成文本的 GenAI 系统（如纯文本 LLM/代码生成），即便构成 covered provider，也不触发§22757.2/§22757.3 实质义务（因义务对象不含文本）。报告生成时，凡判定为 covered provider 的主体，应主动核对其输出模态——若仅含文本，应在加州节明确标注"虽构成 covered provider，但§22757.2/§22757.3 义务因输出为纯文本而不触发"，避免误列义务。

**义务清单**：

| 义务 | 内容 | 条文锚点 |
|------|------|----------|
| 免费披露验证工具 | 供用户评估图/视/音频内容是否由其 GenAI 系统创建或改动（**轻微修改除外**）；输出检测到的 system provenance data；原则上**不得**输出检测到的 personal information（用户明示同意的例外）；公开可访问（可设合理限制防安全风险或恶意滥用）；支持上传内容或 URL；支持含 API 的技术免访问网站调用 | §22757.2(a)(1)-(6) |
| 工具反馈与个人信息限制 | 收集用户反馈改进工具；不得收集、使用、保留、出售、共享或以其他方式提供源自工具用户或经工具处理内容的个人信息，超出为遵守本章严格必要范围（与 opt-in 用户沟通的除外）；**新增**：不得以用户提供超出严格必要个人信息为条件限制访问 GenAI 系统或工具 | §22757.2(b)(c)(d) |
| 第三方工具（新增） | 可通过第三方披露验证工具履行义务（符合本条、与隐式披露兼容、界面清晰显著可及） | §22757.2(e) |
| 隐式披露（latent disclosure） | 技术可行范围内，应当在**任何**图/视/音频（或其组合）内容中纳入（创建或改动、轻微修改除外），传达：①提供者名称 ②GenAI 系统名称与版本信息 ③创建/改动时间日期 ④唯一标识符 ⑤是否由该系统创建或改动 ⑥（2029-01-01 起）是否主要设计用作辅助技术；永久或极难移除或篡改；与披露验证工具兼容；符合或可互操作于广泛认可的行业标准 | §22757.3(a)(1)-(4) |
| 被许可方合同传导（重构） | 许可时**通知**被许可人本章义务；知悉可识别的被许可人修改系统致其不再合规的，**72 小时**内终止授权或通知整改；收到通知的被许可人应整改或停止使用/提供，并于 96 小时内报告；提供者未获报告或报告显示未整改的，向总检察长报告；**无监控/调查义务** | §22757.3(b)(1)-(5) |
| 禁止虚假辅助技术陈述（新增） | 不得虚假陈述 GenAI 系统主要设计用作辅助技术 | §22757.3(d) |

> **脚注原文块（SB 1000 Enrolled 原文，写脚注时直接引用英文原文＋条号）**：
>
> **§22757.2(a)(1)-(6)**："(a) A covered provider shall make available a disclosure verification tool at no cost to the user that meets all of the following criteria: (1) The tool allows a user to assess whether image, video, or audio content, or content that is any combination thereof, was created or altered, except by minor modification, by the covered provider's GenAI system. (2) The tool outputs any system provenance data that is detected in the content. (3)(A) Except as provided in subparagraph (B), the tool does not output any personal information that is detected in the content. (B) The tool may output personal information that is detected in the content if the user to whom the personal information pertains expressly consents, clearly and conspicuously in plain language, to including personal information specified by the user in the content pursuant to a notice that does both of the following: (i) Informs the user of the personal information that may be output by the tool. (ii) Informs the user that once personal information is embedded into provenance data and exported, the information becomes part of the file's permanent digital footprint and cannot be retracted from copies already in circulation. (4)(A) Subject to subparagraph (B), the tool is publicly accessible. (B) A covered provider may impose reasonable limitations on access to the tool to prevent, or respond to, demonstrable risks to the security or integrity of its GenAI system or to prevent misuse of the tool for malicious purposes. (5) The tool allows a user to upload content or provide a uniform resource locator (URL) linking to online content. (6) The tool supports technology, including an application programming interface, that allows a user to invoke the tool without visiting the covered provider's internet website."
>
> **§22757.2(c)(d)(e)**："(c)(1) Except as provided in paragraph (2), a covered provider shall not collect, use, retain, sell, share, or otherwise make available personal information derived either from a user of the covered provider's AI disclosure verification tool or from any content processed by the disclosure verification tool beyond what is strictly necessary to comply with this chapter. (2) A covered provider may collect, retain, or use personal information for the sole purpose of communicating with a user that opts into being contacted by the covered provider. (d) A covered provider shall not make access to the covered provider's GenAI system or disclosure verification tool contingent upon a user providing personal information beyond what is strictly necessary to comply with this chapter. (e) A covered provider may satisfy the requirements of this section by directing a user to a third-party disclosure verification tool that is all of the following: (1) In compliance with this section. (2) Compatible with latent disclosures included in content produced or altered by the covered provider's GenAI system. (3) Clearly and conspicuously accessible through the user interface of the covered provider's GenAI system."
>
> **§22757.3(a)**："(a) To the extent it is technically feasible, a covered provider shall include a latent disclosure that meets all of the following criteria in any image, video, or audio content, or content that is any combination thereof, created or altered, except by minor modification, by the covered provider's GenAI system: (1) The disclosure conveys all of the following information, either directly or through a link to a permanent internet website: (A) The name of the covered provider. (B) The name and version information of the GenAI system that created or altered the content. (C) The time and date of the content's creation or alteration. (D) A unique identifier. (E) Whether the GenAI system created or altered the content. (F) On and after January 1, 2029, whether the GenAI system is designed to primarily function as assistive technology. (2) The disclosure is permanent or extraordinarily difficult to remove or tamper with. (3) The disclosure is compatible with the covered provider's disclosure verification tool. (4) The disclosure is compliant or interoperable with widely recognized industry standards."
>
> **§22757.3(b)(c)(d)**："(b)(1) If a covered provider licenses its GenAI system to a third party, the covered provider shall, when it provides the license, notify the licensee of the licensee's obligations under this chapter. (2) If a covered provider knows that an identifiable third-party licensee modified a licensed GenAI system such that it no longer complies with this chapter, the covered provider shall do either of the following: (A) Terminate the licensee's authorization to use the GenAI system within 72 hours of discovering the licensee's action. (B) Notify the licensee of both of the following within 72 hours of discovering the licensee's action: (i) The licensee's noncompliance. (ii) The requirement to report noncompliance with paragraph (3) to the Attorney General pursuant to paragraph (4). (3) A third-party licensee that receives a notice under paragraph (2) shall modify the licensed GenAI system to be in compliance with this chapter or cease using or making available the licensed GenAI system, including a copy or modified version of the GenAI system and shall report which of those actions it took to the covered provider within 96 hours of receipt of the notice. (4) If a covered provider does not receive a report pursuant to paragraph (3) or if a covered provider receives a report from a third-party licensee indicating that the third-party licensee did not, pursuant to paragraph (3), modify or cease using or making available the licensed GenAI system, the covered provider shall report the third-party licensee's noncompliance with paragraph (3) to the Attorney General. (5) This subdivision does not require a covered provider to monitor, investigate, or otherwise inquire into a third-party licensee's use or modification of a licensed GenAI system. (c) The Attorney General shall establish a mechanism to receive reports from covered providers submitted to the Attorney General pursuant to this section. (d) A covered provider shall not falsely represent that a GenAI system is designed to primarily function as assistive technology."

### 1.1 多原因不触发的分层表述规则（★强制）

当不触发结论同时具备两类原因时，报告须**分层表述**，禁止并列为等价原因：
- **主导原因（主体门槛）管辖全章适用性**：如「该 GenAI 系统不在加州地理边界内公开可访问 → 不构成 covered provider，全章义务不触发」。此为前提性、决定全章是否适用的原因，须首先写明。**（SB 1000 删除 100 万月活门槛后，covered provider 的主体门槛已从「100 万月活」变为「加州公开可访问」；"月活未达 100 万"不再是主导原因，改为"不在加州公开可访问"。）**
- **层级抗辩（输出模态不在义务范围）**：如「退一步，即便构成 covered provider，本案纯文本输出亦不落入§22757.2/§22757.3（限图像/视频/音频）义务范围」。此为退一步的防守性理由，仅在已先判定构成 covered provider 时才具有独立意义，须置于主导原因之后。

> ⚠️ **禁止写法**：「（纯文本且非 covered provider）」此类括号并列——它抹去主次，误导读者以为「纯文本」是主导原因。正确写法见上。

### 2. Large online platform（大型网络平台）——2027-01-01 生效

**定义（§22757.1(i)(1)）**：公众可见的社交媒体平台、文件分享平台、大规模消息平台或独立搜索引擎，向未创作/协作创作内容的用户分发内容，**过去 12 个月独立月用户超 200 万**。排除宽带接入服务与电信服务（§22757.1(i)(2)）。Mass messaging platform 指可同时向超 100 用户分发内容的直接消息平台（§22757.1(j)）。

**义务清单（§22757.3.1(a)(b)）**：
(1) 检测平台上分发内容中是否嵌入或附有**符合成熟标准制定组织广泛采纳规范**的来源数据；
(2) 提供用户界面披露 system provenance data 可用性，清晰显著展示内容真实性/来源/修改历史信息，至少含：来源数据是否可用、创建或实质改变内容的 GenAI 系统或采集设备名称（如适用）、数字签名是否可用；
(3) 允许用户以便捷方式查验全部可用 system provenance data（界面直接展示/提供含来源数据的下载/提供链接，三选一即可）；
(4) 技术可行范围内，不得明知而剥离内容中符合广泛采纳规范的 system provenance data 或数字签名。

> **§22757.3.1(a) 原文**：「(a) A large online platform shall do all of the following: (1) Detect whether any provenance data that is compliant with widely adopted specifications adopted by an established standards-setting body is embedded into or attached to content distributed on the large online platform. (2)(A) Provide a user interface to disclose the availability of system provenance data that reliably indicates that the content was generated or substantially altered by a GenAI system or captured by a capture device. (B) The user interface required by this paragraph shall make clearly and conspicuously available to users information sufficient to identify the content's authenticity, origin, or history of modification, including, but not limited to, all of the following: (i) Whether provenance data is available. (ii) The name of the GenAI system or capture device that created or substantially altered the content, if applicable. (iii) Whether any digital signatures are available. (3) Allow a user to inspect all available system provenance data that is compliant with widely adopted specifications adopted by an established standards-setting body in an easily accessible manner…」

### 3. GenAI hosting platform（生成式人工智能系统托管平台）——2027-01-01 生效

**定义（§22757.1(h)）**：供加州居民下载 GenAI 系统**源代码或模型权重**的网站或应用，不论是否有偿。定义未区分自有模型与第三方模型——开发者在自持站点提供**自有**模型权重下载，字面同样落入定义（公开下载即视为加州居民可达）。

**义务（§22757.3.2(a)）**：不得**明知**而提供未按§22757.3 设置披露的 GenAI 系统。

> 文本细节：定义条款用"GenAI hosting platform"，义务条款用"GenAI system hosting platform"，系立法文本措辞不一致，指向同一主体。

> **§22757.3.2(a) 原文**：「(a) A GenAI system hosting platform shall not knowingly make available a GenAI system that does not place disclosures pursuant to Section 22757.3.」

> **⚠️ 报告撰写区分（★强制，与门禁⑬/㉒协同）**：GenAI hosting platform 属「已落入定义、义务待生效」状态——现行法定义（§22757.1(h)）即可判定构成，但§22757.3.2 义务**延缓至 2027-01-01 生效**。报告须将其与「covered provider 主体资格未达之不触发」**分列**，单列标注「已适用、义务待生效（2027-01-01）」，**不得并列为同一「当前不触发」**。同理适用于 large online platform（§22757.3.1，2027-01-01）、capture device manufacturer（§22757.3.3，2028-01-01）——三者定义均已可落入、仅义务延缓。SB 1000 前瞻变更提示仅附着 covered provider 类（定义已变），不得外溢至 hosting platform / large online platform / capture device manufacturer 类（其定义不受 SB 1000 影响）。

### 4. Capture device manufacturer（采集设备制造商）——2028-01-01 生效

**定义（§22757.1(c)(d)）**：生产在加州销售的采集设备（可录制照片、音频、视频的设备，含相机、带摄像头/麦克风的手机、录音设备）的主体；**纯组装商除外**（仅从事采集设备组装者不属于制造商，§22757.1(d)(2)）。

**义务（§22757.3.3(a)，限 2028-01-01 起首次在州内生产销售的设备）**：
(1) 向用户提供在采集内容中加入隐式披露的选项，披露传达：制造商名称、设备名称与版本号、创建/改变时间日期；
(2) **默认**在设备采集内容中嵌入隐式披露。
仅应当在技术可行且符合广泛采纳规范的范围内遵守（§22757.3.3(b)）。

> 规制方向提示：该义务是为**真实内容**嵌入来源数据（证明"真"），与标记 AI 生成内容方向相反。

> **§22757.3.3(a) 原文**：「(a) A capture device manufacturer shall, with respect to any capture device the capture device manufacturer first produced for sale in the state on or after January 1, 2028, do both of the following: (1) Provide a user with the option to include a latent disclosure in content captured by the capture device that conveys all of the following information: (A) The name of the capture device manufacturer. (B) The name and version number of the capture device that created or altered the content. (C) The time and date of the content's creation or alteration. (2) Embed latent disclosures in content captured by the device by default.」

### 5. 第三方被许可方

- 许可时，covered provider 应通知被许可人本章义务（§22757.3(b)(1)）。
- 被许可人修改系统致其不再合规、且收到通知的，应整改或停止使用/提供（含副本或修改版），并于 96 小时内报告（§22757.3(b)(3)）。

## 三、豁免（SB 1000 修订）

**§22757.5(a)**：本章不适用于任何仅提供**非用户生成电子游戏**的产品、服务、互联网网站或应用程序。**SB 1000 将豁免由「电子游戏、电视、流媒体、电影或互动体验」五类收窄为仅「电子游戏」**，电视、流媒体、电影、互动体验提供者不再豁免。

**§22757.5(b)（新增）**：**2029-01-01 前**，本章不适用于主要设计用作辅助技术的 GenAI 系统。

> **§22757.5 原文**："(a) This chapter does not apply to any product, service, internet website, or application that provides exclusively non-user-generated videogames. (b) Before January 1, 2029, this chapter does not apply to a GenAI system that is designed to primarily function as assistive technology."

## 四、罚则与执法（SB 1000 修订）

### 1. 一般罚则（§22757.4）

| 项目 | 内容 |
|------|------|
| 罚款 | 违反本章者按**每次违规 5,000 美元**计（§22757.4(a)(1)） |
| 按日计罚 | covered provider、large online platform、capture device manufacturer 违规的，**每日视为独立违规**（§22757.4(b)）。注意：GenAI hosting platform**未被列入**按日计罚列举 |
| 胜诉方费用 | 胜诉原告可获合理律师费与成本（§22757.4(a)(2)） |
| 过渡条款（新增） | 新法生效前提起、且所称行为在新法下已不违法的诉讼不再维持（§22757.4(c)） |
| 罚则划分（新增） | 本条不适用于违反 §22757.3(d)（虚假辅助技术陈述）之情形（§22757.4(d)） |
| 执法主体 | 检察长（Attorney General）、市检察官（city attorney）、郡法律顾问（county counsel） |

> **§22757.4 原文**："(a)(1) A violator of this chapter shall be liable for a civil penalty in the amount of five thousand dollars ($5,000) per violation to be collected in a civil action filed by the Attorney General, a city attorney, or a county counsel. (2) A prevailing plaintiff in an action brought pursuant to this subdivision shall be entitled to all reasonable attorney's costs and fees. (b) Each day that a covered provider, large online platform, or capture device manufacturer is in violation of this chapter shall be deemed a discrete violation. (c) A civil action brought under this section before the effective date of the act adding this subdivision shall not be maintained if the alleged conduct does not violate this chapter on and after the effective date of the act adding this subdivision. (d) This section does not apply with respect to a violation of subdivision (d) of Section 22757.3."

### 2. 虚假辅助技术陈述专项罚则（§22757.4.1，SB 1000 新增）

| 项目 | 内容 |
|------|------|
| 罚款 | 违反 §22757.3(d)（虚假辅助技术陈述）者按**每次违规 50,000 美元**计（一般违规的 10 倍），由检察长、市检察官或郡法律顾问提起民事诉讼收取 |
| 按日计罚 | covered provider 违反的，每日视为独立违规 |
| 胜诉方费用 | 胜诉原告可获合理律师费与成本 |
| 存续期 | 本条存续至 **2029-01-01**，届期废止（与 §22757.5(b) 豁免到期同步，届时辅助技术系统转入常规隐式披露监管） |

> **§22757.4.1 原文**："(a)(1) A violator of subdivision (d) of Section 22757.3 shall be liable for a civil penalty in the amount of fifty thousand dollars ($50,000) per violation to be collected in a civil action filed by the Attorney General, a city attorney, or a county counsel. (2) A prevailing plaintiff in an action brought pursuant to this subdivision shall be entitled to all reasonable attorney's costs and fees. (b) Each day that a covered provider is in violation of this section shall be deemed a discrete violation. (c) This section shall remain in effect until January 1, 2029, and as of that date is repealed."

## 五、效力核验要点（每次使用前复核）

1. **SB 1000 签署状态**（监控点）：州长是否已于 2026-09-30 前签署/否决；超期则自动成为法律。来源：leginfo 法案历史页 https://leginfo.legislature.ca.gov/faces/billHistoryClient.xhtml?bill_id=202520260SB1000
2. leginfo 上 B&P Code §§22757–22757.6 是否有新修正案（2026 会期后续法案）。
3. AI Omnibus 之外的联邦层面立法（如联邦 AI 披露法案）是否抢占（preemption）动态。
4. C2PA 等标准组织规范更新是否影响「广泛采纳规范」的认定。
