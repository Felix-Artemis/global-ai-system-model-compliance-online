---
title: 美国数据层（CCPA/CPRA 与敏感数据跨境限制）
status: operational-reference
last_verified: 2026-09-09
scope: third-layer-data-flow
---

# 美国数据层：加州隐私法与敏感数据跨境限制

本文件供统一大 Skill 的第三层调用。第三层围绕 AI 平台的实际数据流，和第一层（中国大陆、欧盟、加州 AI 透明度义务）及第二层（欧盟 AI Act 系统/模型层）并行。它不是美国所有隐私法的完整汇编。

## 一、效力分层和核验门禁

| 材料 | 状态 | 在报告中的用法 |
|---|---|---|
| California Consumer Privacy Act，Cal. Civ. Code §§1798.100–1798.199（经 CPRA 修订的现行法） | 强制性州法 | 满足适用门槛时使用“应当”，列为法定义务 |
| California Privacy Rights Act（CPRA，2020 年选民通过，主要自 2023-01-01 适用）及 CPPA 最终规则，Cal. Code Regs. tit. 11, §§7000–7304（以加州官方现行文本为准） | 强制性州法/实施规则 | 规则是具有约束力的实施性法规；在法条和规则冲突时注明并核对最新文本 |
| Executive Order 14117 (2024-02-28) | 总统行政命令（对联邦行政部门有约束力） | 不把行政命令本身写成一般私营企业禁令；用于解释 DOJ 规则的政策来源 |
| DOJ Data Security Program，28 C.F.R. Part 202（最终规则 2025-01-08 发布；2025-04-08 生效；规则一般合规日期为 2025-10-08，个别条款须以现行文本核对） | 强制性联邦行政法规 | 适用于受管辖的“受限数据交易”和相关主体；不得泛化为所有跨境传输禁令 |
| FTC Act §5，15 U.S.C. §45；COPPA，15 U.S.C. §§6501–6506及16 C.F.R. Part 312 | 强制性联邦法（按事实触发） | 欺骗性/不公平隐私做法、13 岁以下儿童在线数据；需另行核验业务是否受管辖 |
| NIST Privacy Framework、NIST AI RMF、CPPA/FTC 博客、C2PA 等 | 建议性良好实践/解释性或技术材料，非独立法定义务 | 只能作为建议控制措施或证据组织方法，不是安全港、也不自动免责 |
| 美国联邦综合隐私法或 ADPPA 等提案、未生效州法草案 | 拟议/未生效 | 仅作前瞻监测，不能作为当前合规结论依据 |

使用前应当核验：加州立法官网（leginfo.legislature.ca.gov）、CPPA（cppa.ca.gov）现行规则、eCFR（ecfr.gov/current/title-28/chapter-II/part-202）和 Federal Register 最终规则。若本文件和官方最新原文不一致，报告应当暂停确定性结论，标记“待核实法律状态”，并按较严格路径发出风险警示。

## 二、CCPA/CPRA 适用范围

### 2.1 “业务（business）”门槛

AI 产品在加州运营、向加州居民提供服务或从加州居民收集个人信息时，应当先核对经营主体是否是 CCPA §1798.140(d) 所称业务。现行门槛为满足下列任一条件（金额和人数门槛须按当年法条及 CPPA 规则复核）：

1. 年度总收入超过法定金额门槛（现行法通常表述为 25,000,000 美元，并可能按法定机制调整）；
2. 每年买卖或共享达到法定数量的消费者、家庭或设备的个人信息（CPRA 后通常为 100,000；应当核对当年口径及“出售/共享”定义）；
3. 年度收入至少一半来自出售或共享个人信息。

“业务”门槛不是只看公司注册地。海外公司、集团内品牌、平台运营方和通过 SDK/广告技术收集信息的主体应当根据收集对象、商业目的和控制关系逐一判断。未达到门槛的主体不应据此声称“无美国隐私义务”：FTC Act、COPPA、州消费者保护法、合同和数据安全义务仍可能适用。

员工、求职者和企业联系人数据的历史性 CCPA 临时豁免不应当作为默认前提；应当按现行 Civil Code 和 CPPA 规则核对是否仍有特定豁免及其范围。

### 2.2 地域和个人信息

CCPA 的消费者是加州居民的自然人。个人信息包括能够直接或间接识别、关联、描述、合理关联或合理链接到消费者或家庭的信息；在合理可能与个人关联时，设备标识、在线标识符、IP、推断画像、客服对话、语音和上传附件通常应当作为待保护个人信息核验。去标识化、聚合数据只有在持续满足法定控制和不重新识别条件时才可按相应例外处理。

### 2.3 敏感个人信息（SPI）

CPRA §1798.140(ae) 的敏感个人信息类别包括（以现行条文为准）：

- 社会安全号、驾驶证/州身份证、护照等精确身份凭证；
- 精确地理位置；
- 账户登录、财务账户、银行卡信息及与凭证组合的信息；
- 种族或族裔、宗教或哲学信仰、工会会籍；
- 邮件、电子邮件和短信内容（企业并非预期收件人的内容）；
- 遗传数据；用于唯一识别个人的生物识别信息；
- 健康信息、性生活或性取向信息；
- 其他由法条或 CPPA 规则明确加入的类别。

客服自由文本、录音、图片和附件可能夹带 SPI；“客户说了健康问题”不应当被模型自动当作普通数据。业务应当提供字段样例、标签规则和抽样结果。SPI 并非绝对禁止处理，但消费者可行使“限制使用和披露敏感个人信息”权利，且目的、告知、最小化、安全与合同控制应当能被证明。

## 三、业务角色和合同边界

### 3.1 业务（business）

决定收集目的和方式、直接与消费者交互、运营 AI 平台或将信息用于训练/广告/画像的主体，通常是 CCPA 业务。集团内多个主体共同决定目的时，应当检查是否构成共同业务或需要分别履行告知与响应责任。

### 3.2 服务提供商和承包商

服务提供商/承包商不是仅凭合同名称确定。合同和实际行为应当满足 CCPA/CPRA 对目的限定、禁止出售/共享、不得为自身商业目的使用、不得将个人信息与从其他来源取得的信息组合（除法定例外）、删除/返还、协助响应消费者请求、审计和安全等要求。外部大模型 API、云托管、日志/监控和人工质检商应当逐个绘制为供应商或分包商，并保留 DPA/CCPA service-provider 条款、数据流和子处理者清单。

若供应商使用输入或输出训练自有模型、建立跨客户画像、投放广告或向第三方出售数据，不能仅因签了“服务提供商”合同就维持该角色；应当按实际用途重新判断出售/共享、披露和独立业务责任。

### 3.3 法条原文锚点（英文）

以下是便于脚注定位的短引文，不替代官方现行文本；正式报告应当从加州立法官网或 eCFR 复制完整条文并记录版本日期。

- Cal. Civ. Code §1798.100(a)（收集时告知）：“A business that controls the collection of a consumer's personal information shall, at or before the point of collection, inform consumers of … the categories of personal information to be collected and the purposes for which the categories of personal information shall be used.”
- Cal. Civ. Code §1798.120(a)（出售/共享退出）：“A consumer shall have the right, at any time, to direct a business that sells or shares personal information about the consumer to third parties not to sell or share the consumer's personal information.”
- Cal. Civ. Code §1798.121(a)（SPI 限制）：“A consumer shall have the right, at any time, to direct a business that collects sensitive personal information about the consumer to limit its use of the consumer's sensitive personal information to that use which is necessary to perform the services or provide the goods reasonably expected by an average consumer who requests those goods or services.”
- Cal. Civ. Code §1798.140(ae)（SPI 定义）：“‘Sensitive personal information’ means … [the categories enumerated in the subdivision].” 完整类别、例外和法定编号应当以现行条文为准。
- 28 C.F.R. Part 202（DOJ Data Security Program）：规则中的“prohibited transactions”“restricted transactions”“government-related data”“bulk sensitive personal data”定义和阈值具有技术性，正式报告应当逐项引用对应 §202 条款，不得用本短引文概括替代。

### 3.4 出售（sell）与共享（share）

“出售”不局限于现金；为金钱或其他有价值对价向第三方披露个人信息可能构成出售。“共享”主要针对跨情境行为广告等目的的披露，即使没有金钱对价也可能触发。向模型供应商传送客服内容是否属于出售/共享，取决于对价、供应商是否仅按指示处理、广告/画像用途及 CPPA 规则中的业务安排；没有合同和实际用途证据时，按较严格的出售/共享风险路径处理。

可出售/共享时，业务应当提供“Do Not Sell or Share My Personal Information”机制、适用的 Global Privacy Control（GPC）信号处理、未成年人选择加入流程，并在隐私政策中说明类别、目的、第三方类别和权利。不要把“跨境”自动等同“出售”，也不要把“没有付款”自动等同“不是出售”。

## 四、消费者权利和系统功能要求

在适用范围内，业务应当建立可用的请求入口、身份核验、法定时限、拒绝理由和记录。至少核验以下权利：

消费者请求通常应当在收到后 45 日内答复；在必要时可按 §1798.130 延长一次（通常再延长 45 日），并应当及时告知消费者延期理由。具体时限、身份核验和重复请求例外以现行法及 CPPA 规则为准。

| 权利 | AI 平台常见问题 | 需要的证据 |
|---|---|---|
| 知情/访问（know/access） | 处理了哪些提示词、附件、日志、画像、推断和共享记录 | 数据目录、检索脚本、响应样本 |
| 删除 | 模型日志、向量库、备份、供应商副本是否可删除；法律例外是什么 | 删除工作流、供应商确认、例外记录 |
| 更正 | 账户资料、客服摘要、知识库中的错误信息 | 更正接口、传播范围、回归测试 |
| 退出出售或共享 | 广告 SDK、分析器、模型供应商的二次用途 | GPC/退出信号日志、供应商开关 |
| 限制使用 SPI | 健康、精确位置、生物识别或账户凭证出现在对话/附件 | SPI 发现规则、目的白名单、限制信号 |
| 不受歧视 | 行使权利后不得降低服务或差别定价，除法定例外 | 价格/服务测试、政策和申诉记录 |
| 未成年人选择加入 | 13 岁以下需监护人同意；13–16 岁出售/共享的选择加入规则 | 年龄和同意流程、家长证据 |

自动化拒绝、推荐、画像和客服升级如果对消费者产生重大影响，还应当并行核验 CCPA/CPRA ADMT 规则、反歧视法及其他州法。ADMT 规则的最终文本、适用日期和豁免可能变化；在未从 CPPA 官方规则确认前，不得写成“已触发的统一 ADMT 权利”，应列为“待核法律状态”。

## 五、告知、最小化和安全

业务应当在收集时提供易懂的隐私告知，说明收集类别、目的、保留期限或确定期限的方法、出售/共享和权利入口；目的改变、训练用途、跨情境广告或新增供应商时应当更新告知并判断是否需要重新取得选择加入。不得收集与已告知目的不合理相关的字段，也不应当以提供超出严格必要个人信息为使用 AI 工具的条件。

应当实施与风险相称的安全措施：访问分级、密钥和凭证隔离、传输/存储加密、提示词和附件脱敏、租户隔离、供应商最小权限、日志保留和删除、模型训练数据隔离、漏洞/事件响应。CCPA 不给出一套可自动免责的技术标准；NIST 或 C2PA 等只能标为“建议性良好实践/解释性材料（非独立法定义务）”。

加州数据泄露导致特定个人信息暴露时，需另行核验 Civil Code §1798.150 私人诉权、§1798.82 通知和其他适用的州/联邦通知法；不能以已取得同意或使用 API 作为免责。

## 六、美国敏感数据跨境和政府访问限制

### 6.1 CCPA 与一般跨境传输

CCPA/CPRA 本身通常不要求像 GDPR 第五章那样取得“充分性决定”或使用 SCC，也没有对所有向境外供应商传输个人信息的一般性地域禁令。但跨境数据流仍可能触发：

- 收集时告知、目的限制、出售/共享退出和 SPI 限制；
- 服务提供商/承包商合同和子处理者管理；
- 合理安全、保留/删除、消费者请求响应；
- FTC Act §5 的隐私声明与实际做法一致性；
- 对特定行业、州或儿童数据的额外规则。

“数据中心在美国”不等于没有跨境传输：外部模型在境外处理、境外运维人员远程访问、境外备份/灾备、境外监控或再传输，均应当记录为数据流节点。

### 6.2 DOJ Data Security Program（DSP）

DOJ 28 C.F.R. Part 202 依据 EO 14117 建立对“受限数据交易”的联邦限制。该规则针对美国政府相关数据和美国人的大规模敏感个人数据，重点关注向“受关注国家（countries of concern）”或受关注国家人员提供访问、控制或利用的交易。受关注国家清单和术语应当以 Part 202 最新文本核对；现行框架通常包括中华人民共和国（含香港、澳门）、古巴、伊朗、朝鲜、俄罗斯和委内瑞拉。不得仅因公司有中国股东、使用中国云或员工国籍就断言已违法，必须识别具体交易、数据类别、数量阈值、接收方和例外。

规则将交易按类型和风险区分，可能包括：数据经纪交易、供应商/服务协议、雇佣协议、投资协议，以及涉及政府相关数据的交易；部分交易被禁止，部分交易只有在合同、资安措施、报告/记录等条件满足时才允许。普通商业服务、个人通信或其他例外的范围和阈值很具体，必须逐项对照 28 C.F.R. §§202.201–202.408（以现行 eCFR 为准）。

DSP 自测至少收集：

1. 数据是否来自美国居民或美国政府相关地点/人员；
2. 是否包含精确地理位置、健康、金融、身份凭证、生物识别/遗传/其他人类组学、个人通信、登录信息等敏感类别；
3. 过去 12 个月人数/设备/记录量及是否达到规则对应的 bulk threshold；
4. 接收方、最终受益人、远程访问人员、分包商、云区和再传输路径；
5. 交易类型（API、托管、支持、训练、数据许可、投资、雇佣或数据经纪）；
6. 是否存在政府相关数据、国防/关键基础设施联系、受关注国家控制/所有/指示或受制裁主体；
7. 适用的豁免、许可、合同安全措施、报告和记录保存证据。

在上述事实任何一项不确定时，报告应当使用条件式：“若该交易属于 Part 202 规定的受限数据交易且不适用例外，则应当按禁止或受限路径暂停/整改”；同时把数据量、接收方控制关系、访问权限和豁免依据列为上线阻断前的核实事项。不得输出“跨境传输不受美国法限制”的无条件结论。

### 6.3 其他联邦和州限制的筛查

AI 平台如处理儿童数据、健康数据、生物识别、金融账户、雇佣/教育记录、精确位置或政府数据，应当分别筛查 COPPA、HIPAA（如属于 covered entity/business associate）、GLBA、FCRA、FERPA、加州 CMIA（如适用）、州健康数据法和数据泄露通知法。华盛顿州 My Health My Data Act、内华达/科罗拉多等州法可能对健康数据、出售和地理围栏设置额外限制；这些规则不能在没有确认州、数据类别和主体角色的情况下概括为“全国适用”。

## 七、机器可读自测字段

主 Skill 可将下列字段作为第三层问卷的输入键；答案为“不确定”时按最严格规则处理并生成待核项：

```yaml
us_data_layer:
  california_resident_data: [yes, no, unknown]
  ccpa_business_threshold:
    revenue_over_statutory_threshold: [yes, no, unknown]
    pii_records_or_devices_over_threshold: [yes, no, unknown]
    half_revenue_from_sale_or_share: [yes, no, unknown]
  data_categories:
    ordinary_personal_information: [yes, no, unknown]
    sensitive_personal_information: [yes, no, unknown]
    children_under_13: [yes, no, unknown]
    age_13_to_16_sale_or_share: [yes, no, unknown]
    government_related_data: [yes, no, unknown]
  purposes: [service_delivery, model_training, analytics, cross_context_ads, sale, share, other, unknown]
  role: [business, service_provider, contractor, third_party, unknown]
  vendor_reuses_for_own_purpose: [yes, no, unknown]
  global_privacy_control_supported: [yes, no, unknown]
  consumer_rights_workflow: [complete, partial, absent, unknown]
  transfer:
    outside_us_processing_or_access: [yes, no, unknown]
    countries_of_concern_link: [yes, no, unknown]
    recipient_control_or_direction: [yes, no, unknown]
    remote_access_or_subprocessor: [yes, no, unknown]
    transaction_type: [api, hosting, support, training, licensing, brokerage, employment, investment, other, unknown]
  dsp_bulk_threshold_and_exception_review: [cleared, restricted, prohibited, not_applicable, unknown]
  evidence: [privacy_notice, contracts, data_map, access_logs, volume_calculation, tia_or_security_review, consent_records, other]
```

## 八、输出规则和待办事项

报告至少分列以下结论：

1. CCPA/CPRA 主体门槛：已确认适用、已确认不适用、或待核；
2. 数据类别和用途：普通个人信息、SPI、儿童数据、政府相关数据分别判断；
3. 角色和合同：业务/服务提供商/承包商/第三方及出售或共享风险；
4. 跨境：一般 CCPA 数据流与 DSP 受限交易分开；不能用一项结论替代另一项；
5. 消费者权利、告知、GPC、删除/更正、SPI 限制、安全和供应商控制的待办；
6. DSP 的禁止/受限/例外路径、需补的交易和数量证据；
7. 法律状态：强制性现行法、拟议/未来规则、建议性材料各自标注。

对于不确定事实，使用：“事实未核实；若成立则适用……；按最严格路径，责任部门应在上线前完成……”。关键门槛、接收方控制关系、政府相关数据、bulk threshold 或豁免无法证明时，综合结论不得写成“合规”，可写“暂不能确认/有条件上线/暂缓上线”。

## 九、官方来源

- California Legislative Information, CCPA/CPRA：<https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division=3.&part=4.&lawCode=CIV&title=1.81.5>
- California Privacy Protection Agency, regulations and rulemaking：<https://cppa.ca.gov/regulations/>
- California Code of Regulations, Title 11, Division 6：<https://govt.westlaw.com/calregs/>
- FTC Act §5, 15 U.S.C. §45：<https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title15-section45>
- COPPA, 15 U.S.C. §§6501–6506：<https://uscode.house.gov/view.xhtml?path=/prelim@title15/chapter91>
- Executive Order 14117：<https://www.federalregister.gov/documents/2024/03/01/2024-04573/preventing-access-to-americans-bulk-sensitive-personal-data-and-united-states-government-related-data-by>
- DOJ Data Security Program, 28 C.F.R. Part 202 (eCFR)：<https://www.ecfr.gov/current/title-28/chapter-II/part-202>
- DOJ final rule, Federal Register (2025-01-08)：<https://www.federalregister.gov/documents/2025/01/08/2024-31486/preventing-access-to-us-sensitive-personal-data-and-government-related-data-by-countries-of-concern-or-covered-persons>
- NIST Privacy Framework（建议性）：<https://www.nist.gov/privacy-framework>

本文件不构成法律意见。美国规则更新频繁；最终报告应当记录核验日期、官方文本版本、未解决的事实和法律争议。
