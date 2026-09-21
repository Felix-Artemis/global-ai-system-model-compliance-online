# 欧盟规则库：AI Act三层接口（透明度、系统/模型、相邻法）

范围提示：本文件主要提供AI Act透明度、GPAI和Digital Omnibus速查；系统层高风险决策树、GDPR/PLD/CDSM/ePrivacy和美国第三层资料分别见统一 Skill 的其他引用文件。AI Act条文属于强制性法规；指南、FAQ、CoP和标准统一标注为“欧盟建议的良好实践/解释性材料（非独立法定义务）”。

```yaml
last_verified: 2026-08-19
status: 现行有效（含Digital Omnibus修订，Reg. (EU) 2026/1744，OJ L 24.7.2026）
next_recheck_before: 2026-11-17
```

> 来源层级（全部为官方一手文本，原件见 `references/sources/`）：
> - Regulation (EU) 2024/1689（AI Act）：**官方OJ原文**（OJ L, 12.7.2024，ELI: reg/2024/1689/oj，已下载PDF逐字核对Art. 50、Art. 99(4)(g)、Recital 134）
> - Regulation (EU) 2026/1744（Digital Omnibus on AI，2026-07-08通过，OJ L 24.7.2026）：**官方OJ原文**（sources/EU-Digital-Omnibus-Reg-2026-1744.pdf）
> - Code of Practice on Transparency of AI-Generated Content（2026-06-10发布）：**官方原文PDF**（sources/EU-CoP-Transparency-Code-of-Practice.pdf）
> - Commission Opinion C(2026) 4839（2026-07-08，准则充分性评估）：**官方原文**（sources/EU-CoP-Commission-Opinion-C2026-4839.pdf）
> - AI Board充分性评估结论：**官方原文**（sources/EU-CoP-AIBoard-Adequacy-Conclusion.pdf）
> - 委员会Art. 50指南 C(2026) 5054（2026-07-20内容批准）：**官方原文**（sources/EU-Art50-Guidelines-C2026-5054.pdf + 批准通讯PDF）

---

## 一、定义（Art. 3 Definitions，官方原文）

> 本节收录 EU AI Act Article 3 与本 skill 相关的定义原文。**粗体条目**为角色判定与义务触发中高频引用项。中文标题为辅助说明，定义文本以官方 OJ 英文原文为准。

For the purposes of this Regulation, the following definitions apply:

**(1) ‘AI system’** means a machine-based system that is designed to operate with varying levels of autonomy and that may exhibit adaptiveness after deployment, and that, for explicit or implicit objectives, infers, from the input it receives, how to generate outputs such as predictions, content, recommendations, or decisions that can influence physical or virtual environments;

(2) ‘risk’ means the combination of the probability of an occurrence of harm and the severity of that harm;

**(3) ‘provider’** means a natural or legal person, public authority, agency or other body that develops an AI system or a general-purpose AI model or that has an AI system or a general-purpose AI model developed and places it on the market or puts the AI system into service under its own name or trademark, whether for payment or free of charge;

**(4) ‘deployer’** means a natural or legal person, public authority, agency or other body using an AI system under its authority except where the AI system is used in the course of a personal non-professional activity;

(5) ‘authorised representative’ means a natural or legal person located or established in the Union who has received and accepted a written mandate from a provider of an AI system or a general-purpose AI model to, respectively, perform and carry out on its behalf the obligations and procedures established by this Regulation;

**(6) ‘importer’** means a natural or legal person located or established in the Union that places on the market an AI system that bears the name or trademark of a natural or legal person established in a third country;

**(7) ‘distributor’** means a natural or legal person in the supply chain, other than the provider or the importer, that makes an AI system available on the Union market;

(8) ‘operator’ means a provider, product manufacturer, deployer, authorised representative, importer or distributor;

**(9) ‘placing on the market’** means the first making available of an AI system or a general-purpose AI model on the Union market;

**(10) ‘making available on the market’** means the supply of an AI system or a general-purpose AI model for distribution or use on the Union market in the course of a commercial activity, whether in return for payment or free of charge;

**(11) ‘putting into service’** means the supply of an AI system for first use directly to the deployer or for own use in the Union for its intended purpose;

(12) ‘intended purpose’ means the use for which an AI system is intended by the provider, including the specific context and conditions of use, as specified in the information supplied by the provider in the instructions for use, promotional or sales materials and statements, as well as in the technical documentation;

(13) ‘reasonably foreseeable misuse’ means the use of an AI system in a way that is not in accordance with its intended purpose, but which may result from reasonably foreseeable human behaviour or interaction with other systems, including other AI systems;

(14) ‘safety component’ means a component of a product or of an AI system which fulfils a safety function for that product or AI system, or the failure or malfunctioning of which endangers the health and safety of persons or property; for the purposes of this definition, a component fulfils a safety function where its intended purpose is to prevent or mitigate risks to health and safety of persons or property;

(14a) ‘micro, small and medium-sized enterprise’ or ‘SME’ means a micro, small or medium-sized enterprise as defined in Article 2 of the Annex to Recommendation 2003/361/EC;

(14b) ‘small mid-cap enterprise’ or ‘SMC’ means a small mid-cap enterprise as defined in point (2) of the Annex to Recommendation (EU) 2025/1099;

(15) ‘instructions for use’ means the information provided by the provider to inform the deployer of, in particular, an AI system’s intended purpose and proper use;

(16) ‘recall of an AI system’ means any measure aiming to achieve the return to the provider or taking out of service or disabling the use of an AI system made available to deployers;

(17) ‘withdrawal of an AI system’ means any measure aiming to prevent an AI system in the supply chain being made available on the market;

(18) ‘performance of an AI system’ means the ability of an AI system to achieve its intended purpose;

(19) ‘notifying authority’ means the national authority responsible for setting up and carrying out the necessary procedures for the assessment, designation and notification of conformity assessment bodies and for their monitoring;

(20) ‘conformity assessment’ means the process of demonstrating whether the requirements set out in Chapter III, Section 2 relating to a high-risk AI system have been fulfilled;

(21) ‘conformity assessment body’ means a body that performs third-party conformity assessment activities, including testing, certification and inspection;

(22) ‘notified body’ means a conformity assessment body notified in accordance with this Regulation and other relevant Union harmonisation legislation;

(23) ‘substantial modification’ means a change to an AI system after its placing on the market or putting into service which is not foreseen or planned in the initial conformity assessment carried out by the provider and as a result of which the compliance of the AI system with the requirements set out in Chapter III, Section 2 is affected or results in a modification to the intended purpose for which the AI system has been assessed;

(24) ‘CE marking’ means a marking by which a provider indicates that an AI system is in conformity with the requirements set out in Chapter III, Section 2 and other applicable Union harmonisation legislation providing for its affixing;

(25) ‘post-market monitoring system’ means all activities carried out by providers of AI systems to collect and review experience gained from the use of AI systems they place on the market or put into service for the purpose of identifying any need to immediately apply any necessary corrective or preventive actions;

(26) ‘market surveillance authority’ means the national authority carrying out the activities and taking the measures pursuant to Regulation (EU) 2019/1020;

(27) ‘harmonised standard’ means a harmonised standard as defined in Article 2(1), point (c), of Regulation (EU) No 1025/2012;

(28) ‘common specification’ means a set of technical specifications as defined in Article 2, point (4) of Regulation (EU) No 1025/2012, providing means to comply with certain requirements established under this Regulation;

(29) ‘training data’ means data used for training an AI system through fitting its learnable parameters;

(30) ‘validation data’ means data used for providing an evaluation of the trained AI system and for tuning its non-learnable parameters and its learning process in order, inter alia, to prevent underfitting or overfitting;

(31) ‘validation data set’ means a separate data set or part of the training data set, either as a fixed or variable split;

(32) ‘testing data’ means data used for providing an independent evaluation of the AI system in order to confirm the expected performance of that system before its placing on the market or putting into service;

(33) ‘input data’ means data provided to or directly acquired by an AI system on the basis of which the system produces an output;

(34) ‘biometric data’ means personal data resulting from specific technical processing relating to the physical, physiological or behavioural characteristics of a natural person, such as facial images or dactyloscopic data;

(35) ‘biometric identification’ means the automated recognition of physical, physiological, behavioural, or psychological human features for the purpose of establishing the identity of a natural person by comparing biometric data of that individual to biometric data of individuals stored in a database;

(36) ‘biometric verification’ means the automated, one-to-one verification, including authentication, of the identity of natural persons by comparing their biometric data to previously provided biometric data;

(37) ‘special categories of personal data’ means the categories of personal data referred to in Article 9(1) of Regulation (EU) 2016/679, Article 10 of Directive (EU) 2016/680 and Article 10(1) of Regulation (EU) 2018/1725;

(38) ‘sensitive operational data’ means operational data related to activities of prevention, detection, investigation or prosecution of criminal offences, the disclosure of which could jeopardise the integrity of criminal proceedings;

**(39) ‘emotion recognition system’** means an AI system for the purpose of identifying or inferring emotions or intentions of natural persons on the basis of their biometric data;

**(40) ‘biometric categorisation system’** means an AI system for the purpose of assigning natural persons to specific categories on the basis of their biometric data, unless it is ancillary to another commercial service and strictly necessary for objective technical reasons;

(41) ‘remote biometric identification system’ means an AI system for the purpose of identifying natural persons, without their active involvement, typically at a distance through the comparison of a person’s biometric data with the biometric data contained in a reference database;

(42) ‘real-time remote biometric identification system’ means a remote biometric identification system, whereby the capturing of biometric data, the comparison and the identification all occur without a significant delay, comprising not only instant identification, but also limited short delays in order to avoid circumvention;

(43) ‘post-remote biometric identification system’ means a remote biometric identification system other than a real-time remote biometric identification system;

(44) ‘publicly accessible space’ means any publicly or privately owned physical place accessible to an undetermined number of natural persons, regardless of whether certain conditions for access may apply, and regardless of the potential capacity restrictions;

(45) ‘law enforcement authority’ means:
(a) any public authority competent for the prevention, investigation, detection or prosecution of criminal offences or the execution of criminal penalties, including the safeguarding against and the prevention of threats to public security; or
(b) any other body or entity entrusted by Member State law to exercise public authority and public powers for the purposes of the prevention, investigation, detection or prosecution of criminal offences or the execution of criminal penalties, including the safeguarding against and the prevention of threats to public security;

(46) ‘law enforcement’ means activities carried out by law enforcement authorities or on their behalf for the prevention, investigation, detection or prosecution of criminal offences or the execution of criminal penalties, including safeguarding against and preventing threats to public security;

(47) ‘AI Office’ means the Commission’s function of contributing to the implementation, monitoring and supervision of AI systems and general-purpose AI models, and AI governance, provided for in Commission Decision of 24 January 2024; references in this Regulation to the AI Office shall be construed as references to the Commission;

(48) ‘national competent authority’ means a notifying authority or a market surveillance authority; as regards AI systems put into service or used by Union institutions, agencies, offices and bodies, references to national competent authorities or market surveillance authorities in this Regulation shall be construed as references to the European Data Protection Supervisor;

(49) ‘serious incident’ means an incident or malfunctioning of an AI system that directly or indirectly leads to any of the following:
(a) the death of a person, or serious harm to a person’s health;
(b) a serious and irreversible disruption of the management or operation of critical infrastructure;
(c) the infringement of obligations under Union law intended to protect fundamental rights;
(d) serious harm to property or the environment;

(50) ‘personal data’ means personal data as defined in Article 4, point (1), of Regulation (EU) 2016/679;

(51) ‘non-personal data’ means data other than personal data as defined in Article 4, point (1), of Regulation (EU) 2016/679;

(52) ‘profiling’ means profiling as defined in Article 4, point (4), of Regulation (EU) 2016/679;

(53) ‘real-world testing plan’ means a document that describes the objectives, methodology, geographical, population and temporal scope, monitoring, organisation and conduct of testing in real-world conditions;

(54) ‘sandbox plan’ means a document agreed between the participating provider and the competent authority describing the objectives, conditions, timeframe, methodology and requirements for the activities carried out within the sandbox;

(55) ‘AI regulatory sandbox’ means a controlled framework set up by a competent authority which offers providers or prospective providers of AI systems the possibility to develop, train, validate and test, where appropriate in real-world conditions, an innovative AI system, pursuant to a sandbox plan for a limited time under regulatory supervision;

(56) ‘AI literacy’ means skills, knowledge and understanding that allow providers, deployers and affected persons, taking into account their respective rights and obligations in the context of this Regulation, to make an informed deployment of AI systems, as well as to gain awareness about the opportunities and risks of AI and possible harm it can cause;

(57) ‘testing in real-world conditions’ means the temporary testing of an AI system for its intended purpose in real-world conditions outside a laboratory or otherwise simulated environment, with a view to gathering reliable and robust data and to assessing and verifying the conformity of the AI system with the requirements of this Regulation and it does not qualify as placing the AI system on the market or putting it into service within the meaning of this Regulation, provided that all conditions laid down in Article 57 or 60 are fulfilled;

(58) ‘subject’, for the purpose of real-world testing, means a natural person who participates in testing in real-world conditions;

(59) ‘informed consent’ means a subject’s freely given, specific, unambiguous and voluntary expression of his or her willingness to participate in a particular testing in real-world conditions, after having been informed of all aspects of the testing that are relevant to the subject’s decision to participate;

**(60) ‘deep fake’** means AI-generated or manipulated image, audio or video content that resembles existing persons, objects, places, entities or events and would falsely appear to a person to be authentic or truthful;

(61) ‘widespread infringement’ means any act or omission contrary to Union law protecting the interest of individuals, which:
(a) has harmed or is likely to harm the collective interests of individuals residing in at least two Member States other than the Member State in which:
(i) the act or omission originated or took place;
(ii) the provider concerned, or, where applicable, its authorised representative is located or established; or
(iii) the deployer is established, when the infringement is committed by the deployer;
(b) has caused, causes or is likely to cause harm to the collective interests of individuals and has common features, including the same unlawful practice or the same interest being infringed, and is occurring concurrently, committed by the same operator, in at least three Member States;

(62) ‘critical infrastructure’ means critical infrastructure as defined in Article 2, point (4), of Directive (EU) 2022/2557;

**(63) ‘general-purpose AI model’** means an AI model, including where such an AI model is trained with a large amount of data using self-supervision at scale, that displays significant generality and is capable of competently performing a wide range of distinct tasks regardless of the way the model is placed on the market and that can be integrated into a variety of downstream systems or applications, except AI models that are used for research, development or prototyping activities before they are placed on the market;

(64) ‘high-impact capabilities’ means capabilities that match or exceed the capabilities recorded in the most advanced general-purpose AI models;

(65) ‘systemic risk’ means a risk that is specific to the high-impact capabilities of general-purpose AI models, having a significant impact on the Union market due to their reach, or due to actual or reasonably foreseeable negative effects on public health, safety, public security, fundamental rights, or the society as a whole, that can be propagated at scale across the value chain;

**(66) ‘general-purpose AI system’** means an AI system which is based on a general-purpose AI model and which has the capability to serve a variety of purposes, both for direct use as well as for integration in other AI systems;

(67) ‘floating-point operation’ means any mathematical operation or assignment involving floating-point numbers, which are a subset of the real numbers typically represented on computers by an integer of fixed precision scaled by an integer exponent of a fixed base;

**(68) ‘downstream provider’** means a provider of an AI system, including a general-purpose AI system, which integrates an AI model, regardless of whether the AI model is provided by themselves and vertically integrated or provided by another entity based on contractual relations.

## 一（之二）、GPAI provider 的「开发」概念与业务形态（C(2025) 7719 final 官方指南）

> 本节依据欧委会《Commission Guidelines on the scope of the obligations for providers of general-purpose AI models》（C(2025) 7719 final，2025-11-19）官方原文编写，原件见 `references/sources/EU-GPAI-Guidelines-C2025-7719-final.pdf`。本节内容用于角色判定阶段对「是否构成GPAI provider」的细化判断，须与AI Act Art. 3(3)法条原文一并引用。

### 1. provider 三要件与「开发」含义

Art. 3(3)要求provider**同时满足**三项要件：①开发或委托开发AI系统/GPAI模型；②将其投放市场或投入使用；③以自己的名称或商标进行。仅有开发行为而未以自己名义投放市场/投入使用者，不构成该模型/系统的provider（可能构成上游技术支持方或下游deployer）。

「develops」与「has … developed」并列表述，覆盖两种典型情形：

| 情形 | 官方说明 | 指南锚点 |
|------|----------|----------|
| 自研并投放市场 | actor A 自己训练/开发GPAI模型并投放市场，A为provider | §3.1.1(49) |
| 委托/主导开发 | actor A 委托actor B按其指示开发模型，A以自己的名义/商标投放市场，A仍为provider；判断标准为「under whose authority a model is trained」 | §3.1.1(49)；AI Act Service Desk FAQ |
| 上传至第三方托管仓库 | actor A 开发模型后上传至actor C运营的在线仓库（如Hugging Face），只要A以自己名义投放市场，A仍为provider，C仅为托管方 | §3.1.1(49) |
| 协作/财团开发 | 通常由协作/财团的协调者为provider，或协作/财团本身作为provider，须个案评估 | §3.1.1(49) |

> **官方原文（§3.1.1(49)）**："If actor A has a general-purpose AI model developed on its behalf by actor B and actor A places that model on the market, then actor A is the provider. If actor A develops a general-purpose AI model and uploads it to an online repository hosted by actor C, then actor A is the provider. In case of collaborative or consortium arrangements, usually the coordinator of the collaborative or the consortium is the provider. Alternatively, the collaborative or the consortium might be the provider. This must be assessed on a case-by-case basis."

### 2. GPAI 模型「投放市场」的形态（非穷尽列举）

指南基于Recital 97，明确GPAI模型可通过多种形态「投放市场/使其可得」，共9种典型形态：

1. 软件库或包（software libraries or packages）；
2. 应用程序编程接口（API）；
3. 通过公共目录、中心或仓库（public directories, hubs or repositories）直接下载；
4. 实体拷贝（physical copies）；
5. 云计算服务（cloud computing services）；
6. 复制到客户自有基础设施（copying to customer-owned infrastructure）；
7. 集成进聊天机器人并通过网页界面提供；
8. 集成进移动应用并通过应用商店提供；
9. 用于影响第三人或欧盟境内自然人权利的内部流程。

> **官方原文（§3.1.2(51)）**："A general-purpose AI model can be placed on the market or put into service in a variety of ways, such as through software libraries or packages, application programming interfaces (APIs), direct downloads through public directories, hubs or repositories, physical copies, cloud computing services, copying to customer-owned infrastructure, integration into a chatbot made available through a web interface, integration into a mobile application made available through an app store, or internal processes affecting third parties or natural persons in the Union."

### 3. 下游修改导致「新provider」的阈值

下游经营者对GPAI模型进行修改后，可能自身成为该模型的provider。触发条件为：修改导致模型的generality、capabilities或systemic risk发生**显著变化**（significant change）。指南给出的**指标性标准**：修改所用训练算力超过原模型训练算力的三分之一。

具体算力阈值：

| 原模型类型 | 指标性算力阈值 | 依据 |
|------------|----------------|------|
| 具有系统性风险的GPAI模型 | > 1/3 × 10^25 FLOP | §3.2(60) ＋ Art. 52(1) 系统性风险算力门槛 |
| 不具有系统性风险的GPAI模型 | > 1/3 × 10^23 FLOP | §3.2(60) ＋ Art. 51(1) 通用模型算力门槛 |

> **官方原文（§3.2(60)）**："To determine whether a modification is significant, an indicative criterion in this respect is that the training compute used for the modification is greater than a third of the training compute of the original model, being 10^25 FLOP in the case of a general-purpose AI model with systemic risk and 10^23 FLOP in the case of a general-purpose AI model which is not general-purpose AI model with systemic risk."

### 4. 判断「谁修改了模型」的核心抓手：控制模型权重

在API微调等场景中，**谁控制模型权重**（control over the model's weights）是判断修改由谁完成、从而谁构成新provider的重要因素。

> **官方原文（§3.2 footnote 13）**："An important factor in this assessment may be who has the control over the model's weights, for example, in case of fine-tuning via API."

### 5. 与下游AI系统provider的衔接

按Art. 3(68)，将GPAI模型集成进AI系统并以自己名义投放市场的主体，构成该AI系统的downstream provider，须承担该系统层面的义务（包括Art. 50透明度义务）。上游GPAI provider与下游系统provider的义务边界：上游负责模型层义务（如Art. 52、53及随模型提供的文档/合规信息），下游负责系统层面义务；下游可依赖上游已实施的机器可读标记方案，但须确保该方案符合Art. 50(2)，且不免除下游证明自身合规的责任（委员会Art. 50指南§4.2.1(74)段）。

## 二、适用时间（经Omnibus修订后，官方实施时间轴核对）

| 节点 | 内容 | 依据 |
|------|------|------|
| 2026-08-02 | Art. 50透明度义务开始适用（含执法启动） | Art. 113（Omnibus未改动该日期）；委员会官方timeline |
| 2026-12-02 | 过渡期届满：2026-08-02**前**已投放市场的生成合成内容的AI系统（含GPAI），应当在此前完成Art. 50(2)合规 | **Omnibus新增Art. 111(4)**（Reg. 2026/1744第(40)项(b)目，OJ原文逐字核对） |
| 2026-12-02 | 新增禁止条款适用（非自愿性深度伪造、CSAM相关，Art. 5(1)(ba)(bb)、(1a)(1b)） | Omnibus修订Art. 113第三段(a)点 |
| 2027-02-02 | 行为准则Measure 3.4：水印检测机制最低互操作方案落地节点 | CoP Section 1 M3.4；AI Board评估结论 |

> Omnibus要点（Recital 38）：为Art. 50(2)标记义务设**四个月过渡期**，仅惠及2026-08-02前已投放市场的系统；之后新投放的系统无宽限。

## 二、Art. 50义务清单（OJ原文逐字核对；50(7)按Omnibus修订后文本）

### Provider（提供者）

| 义务 | 内容与例外 | 条文锚点 |
|------|------------|----------|
| 交互告知 | 与自然人直接交互的AI系统，应当设计为使相对人获知正在与AI交互；对合理知情、观察、审慎的自然人显而易见者除外；刑事侦查等法定授权系统除外（公众报案用途除外） | Art. 50(1) |
| 合成内容机器可读标记 | 生成合成音频、图像、视频或**文本**内容的AI系统（**含GPAI系统**），输出应当以机器可读格式标记且可检测为人工生成/篡改；技术方案应当在技术可行范围内有效、可互操作、稳健、可靠；例外：标准编辑辅助功能、未实质改变deployer提供输入数据或其语义、刑事侦查授权 | Art. 50(2) |

> **Art. 50(1) 纯API/机器对机器（M2M）调用场景**：provider仅以API/接口/M2M方式向其他系统提供生成合成内容、自身无与自然人直接交互的界面时，Art. 50(1)交互告知义务**不触发**（无与自然人直接交互）；但若下游deployer将该API输出呈现于与自然人交互的界面（如下游App的对话窗口），则由该deployer承担Art. 50(1)告知义务。报告在判定provider自身Art. 50(1)不触发时，应自动补此提示，避免下游义务落空。

### Deployer（部署者）

| 义务 | 内容与例外 | 条文锚点 |
|------|------------|----------|
| 情感识别/生物特征分类告知 | 使自然人暴露于此两类系统的，告知被暴露者；个人数据处理应当符合GDPR等；刑事侦查例外 | Art. 50(3) |
| 深度伪造披露 | 生成/篡改构成deep fake的图、音、视频内容，应当披露系人工生成/篡改；刑事侦查例外；**艺术例外**：构成明显艺术、创作、讽刺、虚构或类似作品/节目的，披露义务限于以不妨碍作品展示或欣赏的适当方式披露生成/篡改内容的存在 | Art. 50(4)第1-2项 |
| 公共利益文本披露 | 生成/篡改的文本**为向公众通报公共利益事项而发布**的，应当披露系AI生成/篡改；刑事侦查例外；**编辑责任例外**：经人工审核或编辑控制、且有自然人或法人承担出版编辑责任的，不适用 | Art. 50(4)第3项 |

### 横向要求

- 上述信息披露应当清晰、可区分，最迟于**首次交互或接触时**提供，符合无障碍要求（Art. 50(5)）
- 不影响第三章高风险系统要求，不影响联盟或成员国法律对deployer的其他透明度义务（Art. 50(6)）
- **Art. 50(7)（Omnibus修订后文本，OJ原文逐字核对）**：委员会应鼓励促进联盟层面行为准则的制定；委员会在**最大程度考虑AI Board意见**后，按Art. 56(6)程序评估遵守准则是否足以确保Art. 50(2)/(4)合规；认为准则不充分时，可依Art. 98(2)审查程序通过实施法案制定共同规则。**原"以实施法案批准准则"的授权已删除。**

> **脚注原文块（AI Act Art. 50，OJ原文逐字，写脚注时直接引用英文原文＋条号；完整文本另存 `sources/EU-AIAct-Art50-excerpt.md`）**：
>
> **Art. 50(1)**："Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural persons concerned are informed that they are interacting with an AI system, unless this is obvious from the point of view of a natural person who is reasonably well-informed, observant and circumspect, taking into account the circumstances and the context of use. This obligation shall not apply to AI systems authorised by law to detect, prevent, investigate or prosecute criminal offences, subject to appropriate safeguards for the rights and freedoms of third parties, unless those systems are available for the public to report a criminal offence."
>
> **Art. 50(2)**："Providers of AI systems, including general-purpose AI systems, generating synthetic audio, image, video or text content, shall ensure that the outputs of the AI system are marked in a machine-readable format and detectable as artificially generated or manipulated. Providers shall ensure their technical solutions are effective, interoperable, robust and reliable as far as this is technically feasible, taking into account the specificities and limitations of various types of content, the costs of implementation and the generally acknowledged state of the art, as may be reflected in relevant technical standards. This obligation shall not apply to the extent the AI systems perform an assistive function for standard editing or do not substantially alter the input data provided by the deployer or the semantics thereof, or where authorised by law to detect, prevent, investigate or prosecute criminal offences."
>
> **Art. 50(3)**："Deployers of an emotion recognition system or a biometric categorisation system shall inform the natural persons exposed thereto of the operation of the system, and shall process the personal data in accordance with Regulations (EU) 2016/679 and (EU) 2018/1725 and Directive (EU) 2016/680, as applicable. This obligation shall not apply to AI systems used for biometric categorisation and emotion recognition, which are permitted by law to detect, prevent or investigate criminal offences, subject to appropriate safeguards for the rights and freedoms of third parties, and in accordance with Union law."
>
> **Art. 50(4)**："Deployers of an AI system that generates or manipulates image, audio or video content constituting a deep fake, shall disclose that the content has been artificially generated or manipulated. This obligation shall not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offence. Where the content forms part of an evidently artistic, creative, satirical, fictional or analogous work or programme, the transparency obligations set out in this paragraph are limited to disclosure of the existence of such generated or manipulated content in an appropriate manner that does not hamper the display or enjoyment of the work. Deployers of an AI system that generates or manipulates text which is published with the purpose of informing the public on matters of public interest shall disclose that the text has been artificially generated or manipulated. This obligation shall not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences or where the AI-generated content has undergone a process of human review or editorial control and where a natural or legal person holds editorial responsibility for the publication of the content."
>
> **Art. 50(5)**："The information referred to in paragraphs 1 to 4 shall be provided to the natural persons concerned in a clear and distinguishable manner at the latest at the time of the first interaction or exposure. The information shall conform to the applicable accessibility requirements."

## 三、Digital Omnibus on AI（Reg. (EU) 2026/1744）对Art. 50的修订（OJ原文核对）

| 修订点 | 内容 | 锚点 |
|--------|------|------|
| 新增Art. 111(4) | 2026-08-02前投放市场的合成内容生成系统（含GPAI），采取必要步骤在**2026-12-02**前符合Art. 50(2) | Reg. 2026/1744 Art. 1第(40)项(b) |
| 替换Art. 50(7) | 见上节；删除委员会以实施法案批准准则的授权 | Reg. 2026/1744 Art. 1第(20)项 |
| Recital明确准则法律效果 | Art. 50(7)、56(6)项下准则**法律效果有限，尤其不构成合规推定（no presumption of conformity）** | Reg. 2026/1744 Recital（OJ原文） |
| 修订Art. 113 | 新增深度伪造/CSAM禁止条款2026-12-02适用；Art. 50适用日2026-08-02**未变** | Reg. 2026/1744 Art. 1第(40)项 |

## 四、行为准则（Code of Practice on Transparency of AI-Generated Content）

**基本信息**：2026-06-10发布，38页，自愿签署。

**充分性评估结论（双轨均已通过，官方原文核对）**：
- 委员会：**Commission Opinion C(2026) 4839（2026-07-08）**——准则充分覆盖Art. 50(2)、(4)、(5)义务并促进其有效实施。
- AI Board：**充分性评估结论（2026-07-09通过）**——Section 1与Section 2均充分覆盖Art. 50(2)、(4)、(5)；称准则为"截至2026年7月唯一经评估为充分的欧盟全境实操工具"。
- 两份评估按Omnibus修订前程序作出；官方确认其在Omnibus生效后**继续有效**（结论一致前提下）（Commission Opinion第(5)段、Board结论原文）。

**⚠️ 法律效果（重要更正，官方原文确认）**：签署并遵守准则可用于**证明（demonstrate）合规**，但**不构成合规的确凿证据（conclusive evidence），也不产生合规推定（presumption of conformity）**。市场监督机关仍保留调查签署者是否实际落实准则承诺的权力（Board结论、Commission Opinion、Omnibus Recital三处一致）。——此前版本"合规推定"表述有误，以此为准。

**义务层级三层（will/encouraged/may，判定以原文动词为准）**：

CoP 对每条 Measure 以动词区分签署承诺或建议的强度，但这些层级都属于“欧盟建议的良好实践/解释性材料”，不是独立法定义务。报告应把它们与 Art.50 法定表分开，并保留原文动词：

- **will＝签署方自愿承诺**：表示签署方在签署准则时承诺采取该措施，可能用于说明其如何实施 Art.50，但不会因为使用 will 就转化为对所有主体适用的强制性法规义务。正文应写“签署方承诺/拟采取”，不得改写为法定“应当”。
- **encouraged＝建议采用**：表示准则鼓励签署方采用的做法，不具有法律强制力。正文可写“宜考虑/建议采用”。
- **may＝可选做法**：表示准则允许签署方自行选择的做法，不具有法律强制力。正文可写“可以作为可选实践”。

**判定规则（★强制，防层级误判）**：判定每条 Measure 层级时，应读取 `references/sources/EU-CoP-Transparency-Code-of-Practice.txt`（由同目录 `EU-CoP-Transparency-Code-of-Practice.pdf` 提取、已持久化于 skill 包内，优先读取以免重复转换 PDF；如需核对原文版式/措辞可回看对应 .pdf），按该 Measure 的动词措辞（will/encouraged/may）判定，不得凭记忆或凭下方速查表转述。下方 Section 1/2 表格仅作速查索引，层级以原文动词为准。

**Section 1：Provider规则（对应Art. 50(2)和(5)）——标记与检测**

| Commitment | Measures |
|------------|----------|
| C1 标记AI生成/篡改内容 | M1.1机器可读标记技术（多层方案：元数据+水印至少两层；自由文本/封闭环境可单层）；M1.2标记不被移除；M1.3溯源信息透明（可选）；M1.4可感知标记功能（可选） |
| C2 标记检测 | M2.1标记检测机制；M2.2取证式检测机制（可选）；M2.3检测结果清晰可及披露；M2.4素养支持（可选） |
| C3 标记与检测方案要求 | M3.1有效性；M3.2可靠性；M3.3稳健性；M3.4互操作性（分阶段：开放元数据标准即时启用，水印检测最低互操作方案**2027-02-02**前落地）；M3.5推进技术前沿（可选） |
| C4 测试、验证与合规 | M4.1合规流程；M4.2测试验证监测；M4.3培训；M4.4与市场监督机关合作 |

**Section 2：Deployer规则（对应Art. 50(4)和(5)）——深度伪造与发布文本标识**

| Commitment | Measures |
|------------|----------|
| C1 深度伪造与发布文本披露 | M1.1设计规范（含Annex 1欧盟统一图标）；M1.2位置规范；M1.3自愿参与准则项下task force |
| C2 内部流程 | M2.1内部合规流程；M2.2意识与素养；M2.3复核、反馈与机关合作 |
| C3 艺术创作类作品披露 | 建议采用情境化披露；仍需满足Art.50(4)/(5)法定底线的主体，应当以法律文本为依据自行核对 |
| C4 发布文本的人工审核与编辑控制 | 准则建议签署方区分媒体编辑责任和其他发布流程；是否承担法定义务仍以Art.50(4)及适用法律为准 |

**附件**：Annex 1为公开可用的欧盟统一图标（EU icon）。
**复核机制**：AI Office至少每两年推动准则更新；Board重点监督M3.4互操作性进展，不足时可建议修订准则或提请委员会制定共同规则。

## 五、委员会Art. 50指南（C(2026) 5054，2026-07-20内容批准）

**状态**：指南内容已经Commission Communication C(2026) 5054批准；**正式通过待全语种版本齐备，自正式通过时起适用**（批准通讯原文）。引用时注意此状态。

**关键解释要点（官方原文核对）**：

| 要点 | 内容 | 章节锚点 |
|------|------|----------|
| 第三国provider管辖 | provider在欧盟外设立的，其AI系统输出在欧盟境内使用即受约束；但**偶然、不可预见或未经授权的下游使用本身不触发**义务（不妨碍监管机关认定其输出不合规） | §2.3 第(10)段 |
| 开源边界 | Art. 2(12)：自由开源许可下发布的AI**系统**原则上游离于AI Act范围之外，**但落入Art. 50透明度义务（及Art. 5禁止、高风险）的除外**——即开源AI系统在Art. 50范围内仍应当合规；自由开源的**组件**（不构成AI系统的软件/数据/模型/工具/服务）provider不受Art. 50约束 | §2.4.3 第(23)-(24)段 |
| 编辑责任例外两要件 | 公共利益文本披露例外的两个**累积**要件：(i)文本经人工审核或编辑控制（人工审核=具备相关知识的专业人员对内容实质的审慎检视，事实核查为最低要求；拼写检查等表面形式审查不构成）；(ii)有自然人或法人承担出版编辑责任 | §6.2.3 第(133)-(135)段 |
| 指南本身的性质 | 实务指引，协助监管机关与provider/deployer一致、有效、合比例、统一地合规；不替代法条 | 批准通讯 |

## 六、罚则（OJ原文逐字核对）

| 项目 | 内容 | 条文锚点 |
|------|------|----------|
| 违反Art. 50透明度义务 | 行政罚款上限**1,500万欧元**或上一财年全球年营业总额**3%**，以较高者为准 | Art. 99(4)(g) |
| SME宽减 | 对中小企业（含初创），取金额与比例两者中**较低者** | Art. 99(6) |
| 执法主体 | 成员国市场监督机关；AI Office（其专属管辖的系统）；EDPS（欧盟机构作为provider/deployer时） | 委员会Quick Facts（官方网页） |

## 七、Recital要点（OJ官方文本核对）

- Recital 134（关联Art. 50）：深度伪造披露义务及艺术例外、公共利益文本披露及编辑责任例外的立法理由。**无**"反虚假信息行为准则签署者"表述（该表述见于立法草案阶段，未入最终文本）。
- Recital 135：准则应当支持检测机制可及、价值链协作、公众有效区分AI生成内容的实操安排（充分性评估标准依据）。

## 八、效力核验要点（触发复核时查）

1. EUR-Lex查Reg. 2024/1689是否有新勘误/修正条例（Omnibus已落地为Reg. 2026/1744，后续留意后续修正）
2. Art. 50指南**正式通过版本**是否发布（现为内容批准版C(2026) 5054，正式通过后更新）
3. 行为准则：签署名单更新、准则修订（至少每两年评估更新）、M3.4互操作方案进展（2027-02-02节点）
4. 成员国配套处罚立法动态（Art. 99(2)）
