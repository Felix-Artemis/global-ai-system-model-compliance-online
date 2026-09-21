#!/usr/bin/env python3
"""Check business self-check answers for mutually exclusive selections.

The checker accepts a completed Markdown table, a JSON assessment containing
``questionnaire_responses``, or simple ``P1: ...``/``C3: ...`` text lines.
It does not decide legal applicability.  It only makes unresolved and
contradictory self-check answers visible before they are converted into an
assessment.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


QUESTION_KEY = re.compile(
    r"^(?:第\s*)?([A-LPR]\d+)(?:\s*行)?\s*(?:(?:改为|修改为)\s*|[:：-]\s*)?(.*)$",
    re.I,
)
ROW_REVISION = re.compile(r"^第\s*(\d+)\s*行\s*(?:(?:改为|修改为)\s*|[:：-]\s*)(.*)$", re.I)
KEY_ONLY = re.compile(r"^[A-LPR]\d+$", re.I)
PUBLIC_STEP = re.compile(r"^(?:第\s*([1-5])\s*步|步骤\s*([1-5]))(?:\s*[:：-]\s*)?(.*)$", re.I)
MODE_LABEL = re.compile(r"^模式题(?:\s*[:：-]\s*)?(.*)$", re.I)
UNCERTAIN_PHRASES = (
    "不确定",
    "待核实",
    "事实待核实",
    "unknown",
    "uncertain",
    "尚未决定",
    "尚未确定",
)
EXCLUSIVE_PHRASES = (
    "均未完成",
    "以上均无",
    "以上都没有",
    "没有模型",
    "没有机制",
    "无生成内容",
    "还没有",
    "暂不评估",
    "仅服务器端",
    "none",
    "not applicable",
)
SEPARATOR_RE = re.compile(r"[,，;；、/|]+")
CHOICE_SEPARATOR_RE = re.compile(r"[;；|\r\n]+")
NOTE_LABEL_RE = re.compile(r"^(?:备注|说明|补充|原因|背景|证据|依据|自由注释|note|comment)\s*[:：]", re.I)

# A business answer is intentionally bounded.  The maintained questionnaire is
# designed for facts and evidence pointers, not for pasting entire contracts or
# logs.  A hard limit also keeps the checker predictable when it is called from
# an agent or a CI job.
MAX_INPUT_CHARS = 40_000

# These are the questions exposed by the maintained business table.  Keeping
# the list here lets text/JSON submissions be checked even when they do not
# include the Markdown table itself.  The renderer still remains the source of
# truth for the wording shown to business users.
KNOWN_KEYS = {
    "P0", "P1", "P2", "P3", "P4", "P5", "P6",
    "R1", "R2", "R3", "R4",
    "A1", "A2", "A3", "A4",
    "B1", "B2", "B3", "B4",
    "C1", "C2", "C3", "C4", "C5",
    "D0", "D1", "D2", "D3", "D4",
    "E0", "E1", "E2", "E3", "E4", "E5",
    "F0", "F1", "F2", "F3", "F4", "F5",
    "G1", "G2", "G3",
    "H1", "H2", "H3", "H4",
    "I1", "I2", "I3",
    "J1", "J2", "J3", "J4",
    "K1", "K2",
    "L1", "L2",
}

# Business rows are numbered from the first data row, not from the physical
# Markdown line.  This supports replies such as “第7行改为不确定” without
# making the business user translate a visible row back to an internal key.
BUSINESS_ROW_ORDER = (
    "P0", "P1", "P2", "P3", "P4", "P5", "P6",
    "A1", "A2", "A3", "A4",
    "B1", "B2", "B3", "B4",
    "C1", "C2", "C3", "C4", "C5",
    "D0", "D1", "D2", "D3", "D4",
    "E0", "E1", "E2", "E3", "E4", "E5",
    "F0", "F1", "F2", "F3", "F4", "F5",
    "G1", "G2", "G3",
    "H1", "H2", "H3", "H4",
    "I1", "I2", "I3",
    "J1", "J2", "J3", "J4",
    "K1", "K2",
    "L1", "L2",
)

# Outer modes are deliberately explicit for itemized questions: their option
# text often contains the words “单选” for one child field.
ITEMIZED_KEYS = {
    "P4",
    "R1", "R4", "A1", "A2", "A3", "B4", "C3", "C4", "C5", "D1", "D2", "D4",
    "E0", "E1", "E2", "E3", "E4", "E5", "F0", "F2", "F3", "F4", "F5", "G1", "G2", "G3",
    "H1", "H4", "I2", "J4", "K2",
}
SINGLE_KEYS = {"P0", "P2", "P3", "P5", "P6", "R2", "R3", "A4", "C1", "J3"}
SINGLE_OPTION_MARKERS: dict[str, tuple[str, ...]] = {
    "P0": ("轻量版初步评估", "全量版评估", "不确定"),
    "P2": ("只看AI内容透明度", "透明度加欧盟产品或系统", "透明度加模型来源", "透明度、系统和模型", "不确定"),
    "P3": (
        "只做透明度",
        "不做附属筛查",
        "暂不做附属筛查",
        "只做已选核心范围",
        "顺便简要提示",
        "一起做",
        "附属筛查暂不确定",
        "不确定",
    ),
    "P5": ("我们自己的网页或应用", "客户的网页或应用", "两种情况都有", "内部后台", "系统接口", "其他", "还不确定"),
    "P6": ("可以，我能查看", "可以", "目前只能回答", "只能回答", "不确定"),
    "R2": ("有欧洲", "有欧盟", "目前只有中国大陆", "目前没有发现欧盟连接点", "没有欧盟连接点", "不确定"),
    "R3": ("只调用第三方模型接口", "本公司能下载", "没有模型", "仅固定规则", "本项目使用", "有文件证明本项目没有模型", "不确定"),
    "A4": ("只看报告日", "同时看试点或上线日", "只做未来准备", "不确定"),
    "C1": ("公开传播", "仅签约客户", "两者都有", "混合", "个人单独使用", "个人独立使用", "没有内容传播", "无生成内容", "不确定"),
    "J3": ("已核对许可", "仅核对robots", "有部分核查", "没有核查", "不确定"),
}
SINGLE_CANONICAL_OPTIONS: dict[str, tuple[str, ...]] = {
    "P0": ("轻量版初步评估", "全量版评估", "不确定，先按轻量版初步评估"),
    "P2": ("只看AI内容透明度", "透明度加欧盟产品或系统的使用方式", "透明度加模型来源和使用方式", "透明度、系统和模型都看"),
    "P3": (
        "只做透明度",
        "不做附属筛查",
        "暂不做附属筛查",
        "只做已选核心范围，不做附属筛查",
        "透明度之外顺便提示个人信息、跨境传输、版权等附属事项",
        "一起做与本AI平台有关的附属筛查",
        "附属筛查暂不确定",
    ),
    "P5": ("在我们自己的网页或应用里", "在客户的网页或应用里", "两种情况都有", "只在内部后台使用", "只通过系统接口连接且还不知道最终展示位置", "其他"),
    "P6": ("可以，我能查看或协调核对这些资料", "目前只能回答产品页面和业务流程", "不确定，先只按业务事实评估"),
    "R2": ("有欧盟提供、部署或客户使用", "没有欧盟连接点且有文件证据", "目前只有中国大陆和其他地区且有地区清单"),
    "R3": ("只调用第三方模型接口，不下载或改动权重", "本公司能下载、改动或自行训练至少一个模型", "没有模型或仅固定规则"),
    "A4": ("只看报告日已经适用的要求", "同时看试点或上线日前后可能开始适用的要求", "只做未来准备"),
    "C1": ("仅签约客户或内部", "个人单独使用且不公开", "没有内容传播"),
    "J3": ("已核对许可和权利人保留", "只核对网站抓取设置", "有部分核查", "没有核查"),
}

MULTI_OPTION_MARKERS: dict[str, tuple[str, ...]] = {
    "P1": ("中国大陆", "美国", "欧盟", "尚未确定"),
    "B1": ("文本", "图像", "音频", "视频", "三维", "虚拟场景", "数字人", "内容检测", "分析", "推荐", "规则检索", "其他", "没有内容输出", "不确定"),
    "B2": ("聊天对话", "输入文字", "输入提示词", "模板", "按钮", "后台处理", "纯API", "摄像头", "麦克风", "位置", "其他", "不确定"),
    "B3": ("普通消费者", "未成年人", "员工", "求职者", "学生", "患者", "残障人士", "借款人", "保险客户", "公共服务申请人", "执法", "移民", "司法", "企业员工", "不特定公众", "仅内部人员", "其他", "不确定"),
    "D0": ("强迫", "欺骗", "操纵", "儿童", "残障", "经济困难", "长期行为评分", "人脸", "声音", "推断", "工作场所", "学校", "情绪", "远程识别", "招聘", "教育", "信贷", "保险", "医疗", "福利", "执法", "移民", "司法", "嵌入设备", "可能伤人", "以上都没有", "不确定"),
    "D3": ("学校", "职业培训", "教育", "招聘", "排班", "员工管理", "就业", "公共服务", "私人服务", "福利", "保险", "信贷", "医疗", "关键基础设施", "执法", "移民", "边境", "庇护", "司法", "选举", "民主", "以上都没有", "以上均无", "不确定"),
    "F1": ("姓名", "邮箱", "电话", "账号", "订单", "序列号", "聊天文本", "语音", "图像", "健康", "残障", "生物识别", "位置", "设备标识", "未成年人", "支付", "财务", "员工数据", "其他", "不确定"),
    "H2": ("收集告知", "访问", "知情", "删除", "更正", "限制", "退出", "全局隐私控制", "GPC", "服务提供商合同", "服务合同", "安全措施", "均未完成", "不确定"),
    "H3": ("美国人", "居民", "精确位置", "健康", "基因", "生物识别", "财务", "未成年人", "政府", "关键基础设施", "受关注国家", "受关注实体", "数据经纪", "供应商", "云服务", "雇佣", "投资", "其他", "不确定"),
    "I1": ("独立软件", "SaaS", "云服务", "嵌入硬件", "固件", "模型权重", "软件包", "咨询服务", "不确定"),
    "I3": ("制造商", "组件供应商", "进口商", "授权代表", "分销商", "履约服务商", "保险安排", "其他", "不确定"),
    "J1": ("自有内容", "获得许可", "公开网页", "订阅数据库", "客户上传", "第三方数据集", "抓取但许可不明", "其他", "不确定"),
    "J2": ("抓取", "复制", "训练", "微调", "再训练", "RAG", "缓存", "展示片段", "输出传播", "删除", "退出机制", "其他", "不确定"),
    "K1": ("Cookie", "SDK", "像素", "广告", "分析标识", "设备指纹", "本地存储", "麦克风", "摄像头", "仅服务器端处理", "其他", "不确定"),
    "L1": ("模型错误", "偏见", "不公平", "数据泄露", "版权投诉", "标识被移除", "客户滥用", "监管问询", "人身", "财产损害", "严重事件报告流程", "暂停", "回滚", "通知流程", "没有发生且有台账", "不确定"),
    "L2": ("模型", "提示词版本", "训练数据清单", "发布审批", "变更评估", "运行日志", "用户投诉", "供应商审计", "下游通知", "均未完成", "不确定"),
    "D4": ("风险测试", "训练或输入数据检查", "技术说明", "自动日志", "使用说明", "人工复核", "准确性", "质量流程", "权益影响评估", "外部检查", "上线后监测", "严重事件", "均未完成", "部分完成", "不确定"),
    "C3": ("页面", "对话", "AI提示", "生成内容", "文字标签", "图标", "水印", "来源信息", "是", "否", "不确定"),
}

# Multiple response rows are meaningful for these questions.  Other duplicate
# question keys are treated as unresolved corrections unless “改为” is used.
REPEATABLE_QUESTION_KEYS = {
    "B4", "C5", "E1", "E2", "E4", "E5", "F2", "F3", "G1", "G2", "G3", "H4",
}

# Each tuple is ``(stable field id, business-facing name, accepted aliases)``.
# Only labels are used for completeness.  Explanatory prose cannot accidentally
# satisfy a required field merely because it mentions the same word.
REQUIRED_ITEMIZED_FIELDS: dict[str, tuple[tuple[str, str, tuple[str, ...]], ...]] = {
    "P4": (
        ("product_description", "产品一句话", ("产品一句话", "产品描述", "产品是什么", "product_description")),
        ("target_users", "主要客户或使用者", ("主要客户或使用者", "客户或使用者", "最终用户", "target_users")),
    ),
    "R1": (
        ("cn_transparency", "中国大陆透明度", ("中国大陆透明度", "cn_transparency")),
        ("eu_transparency", "欧盟透明度", ("欧盟透明度", "eu_transparency")),
        ("ca_transparency", "美国加州透明度", ("美国加州透明度", "加州透明度", "california_transparency", "ca_transparency")),
        ("eu_system", "欧盟用途和系统事实页", ("欧盟AIAct系统层", "欧盟人工智能法案系统层", "欧盟系统层", "欧盟用途和系统事实页", "eu_system")),
        ("eu_model", "欧盟模型使用事实页", ("欧盟AIAct模型层", "欧盟人工智能法案模型层", "欧盟模型层", "欧盟模型使用事实页", "eu_model")),
        ("platform_dataflow", "AI平台数据流事实页", ("AI平台数据流及相邻规则", "人工智能平台数据流及相邻规则", "AI平台数据流事实页", "数据流及相邻规则", "platform_dataflow")),
    ),
    "R4": (
        ("personal_information", "个人信息或可识别信息", ("个人信息或可识别信息", "个人信息", "可识别信息", "personal_information", "personal information")),
        ("california_resident", "California居民信息", ("California居民信息", "California居民", "加州居民信息", "加州居民", "california_resident", "california residents")),
        ("cross_border_access", "境外接收、远程查看、备份或再传输", ("境外实体或人员可接收远程查看备份或再传输", "第三国接收远程访问或再传输", "第三国访问", "境外访问", "远程访问", "cross_border_access")),
        ("terminal_access", "Cookie、SDK、像素或设备读写", ("CookieSDK像素或设备读写", "Cookie、SDK、像素或其他终端设备读写", "Cookie或SDK", "终端设备读写", "设备读写", "terminal_access")),
    ),
    "A1": (
        ("project", "项目代号", ("项目代号", "项目名称", "project")),
    ),
    "A2": (
        ("audience", "使用对象", ("使用对象", "使用人群", "audience")),
        ("delivery", "提供方式", ("提供方式", "投放方式", "交付方式", "delivery")),
        (
            "cn_connection",
            "中国大陆地区连接事实",
            ("中国大陆地区连接事实", "中国大陆连接事实", "中国大陆", "cn_connection"),
        ),
        (
            "eu_connection",
            "欧盟地区连接事实",
            ("欧盟地区连接事实", "欧盟连接事实", "欧盟", "eu_connection"),
        ),
        (
            "ca_connection",
            "美国加州地区连接事实",
            ("美国加州地区连接事实", "美国加州连接事实", "美国加州", "加州", "ca_connection"),
        ),
        (
            "other_regions",
            "其他国家或地区",
            ("其他国家或地区", "其他地区", "other_regions"),
        ),
    ),
    "B4": (
        ("model_or_function", "模型或功能", ("模型或功能", "模型功能", "model_or_function")),
        ("output_origin", "输出起点", ("输出起点", "起点", "output_origin")),
        ("recipient_entity", "接收方实体", ("接收方实体", "接收实体", "recipient_entity")),
        ("recipient_country", "接收国家", ("接收国家", "recipient_country")),
        ("shown_to_person", "是否最终给自然人看", ("是否最终给自然人看", "最终展示给自然人", "最终展示", "shown_to_person")),
        ("display_party", "展示方", ("展示方", "display_party")),
        ("downstream_reuse", "下游下载、转发或嵌入", ("下游是否可下载转发或嵌入", "下载转发或嵌入", "下游再传播", "downstream_reuse")),
        ("notice_marker_party", "谁显示提示或保留标记", ("谁实际显示提示或保留标记", "显示提示或保留标记", "告知责任", "披露责任", "标记保持责任", "交互告知责任", "生成内容披露责任", "机器可读标记保持责任", "notice_marker_party")),
        ("marker_removal", "客户能否删除或覆盖标记", ("客户能否删除或覆盖标记", "客户可移除标记", "删除或覆盖标记", "marker_removal")),
        ("evidence_date", "证据名称和日期", ("证据名称和日期", "证据日期", "evidence_date")),
    ),
    "C3": (
        ("interaction_notice", "页面或对话中的AI提示", ("页面或对话中是否明确提示正在使用AI", "页面提示", "对话提示", "AI提示", "interaction_notice")),
        ("visible_label", "生成内容上的文字标签、图标或水印", ("生成内容上是否有文字标签图标或水印", "生成内容", "生成内容标识", "内容标识", "文字标签", "图标或水印", "可见标识", "visible_label")),
        ("machine_source_known", "是否知道文件或系统接口有来源信息", ("是否知道下载文件或系统接口中带有可由软件读取的来源信息", "文件或系统接口", "软件读取的来源信息", "来源信息", "machine_source_known")),
    ),
    "C4": (
        ("cn_reach", "中国大陆投放事实", ("中国大陆投放", "中国大陆", "中国", "cn_reach")),
        ("eu_reach", "欧盟投放事实", ("欧盟投放", "欧盟", "eu_reach")),
        ("ca_reach", "美国加州可访问事实", ("美国加州", "California", "加州", "ca_reach")),
        ("display_path", "各地区的展示位置", ("各地区是在我们自己的页面客户页面还是其他位置看到AI功能和提示", "展示位置", "页面", "display_path")),
    ),
    "D1": (
        ("manipulation", "诱导、欺骗或强迫", ("1", "诱导欺骗或强迫", "操纵或欺骗", "manipulation")),
        ("vulnerability", "利用处境弱点", ("2", "利用处境弱点", "利用脆弱性", "脆弱性", "vulnerability")),
        ("social_scoring", "长期行为评分和差别待遇", ("3", "长期行为评分", "社会评分", "社会信用", "social_scoring")),
        ("biometrics", "生物特征推断或无差别抓取", ("4", "生物特征", "生物数据", "人脸图像", "biometrics")),
        ("emotion_or_remote_id", "工作或学校情绪推测及远程识别", ("5", "情绪", "情感", "远程识别", "emotion_or_remote_id")),
        ("predictive_law_enforcement", "预测性执法或重大公共判断", ("6", "预测谁可能犯罪", "预测性执法", "执法边境司法", "predictive_law_enforcement")),
    ),
    "D2": (
        ("embedded_product", "是否嵌入设备或受管产品", ("是否嵌入设备机械医疗器械交通工具或防护产品", "嵌入设备", "embedded_product")),
        ("physical_harm", "失效是否影响物理或人身安全", ("失效是否可能影响物理安全或人身", "物理安全", "人身安全", "physical_harm")),
        ("patient_impact", "是否影响患者诊断、治疗或监测", ("是否直接影响患者诊断治疗或监测", "患者诊断治疗或监测", "patient_impact")),
        ("external_review", "是否有外部检查或合格文件", ("是否已有外部机构检查或产品合格文件", "外部检查", "产品合格文件", "external_review")),
        ("product_details", "产品名称、版本和AI功能", ("设备或产品名称版本和AI功能", "产品名称版本和AI功能", "product_details")),
        ("review_body", "外部检查机构名称", ("外部检查机构名称", "外部机构名称", "review_body")),
    ),
    "E0": (
        ("source", "AI能力来源", ("来源", "AI能力来源", "外部AI服务", "自行训练或改造", "source")),
        ("task_range", "任务范围", ("任务范围", "多种任务", "固定任务", "task_range")),
    ),
    "E2": (
        ("training_goal", "训练目标决定方", ("训练目标", "training_goal")),
        ("weights", "权重访问、下载或改动方", ("权重访问下载或改动", "模型权重", "weights")),
        ("fine_tuning", "微调或再训练决定方", ("微调或再训练", "微调决定", "fine_tuning")),
        ("brand", "对外品牌或名称", ("品牌或名称", "对外品牌", "brand")),
        ("delivery", "提供方式", ("提供方式", "投放方式", "delivery")),
        ("redistribution", "是否再分发", ("是否再分发", "再分发", "redistribution")),
        ("license", "许可证和限制", ("许可证和限制", "许可证", "license")),
        ("change_review", "重大版本变更评估", ("重大版本变更评估", "重大修改", "版本变更", "change_review")),
        ("evidence_date", "证据名称和日期", ("证据名称和日期", "证据日期", "evidence_date")),
    ),
    "E4": (
        ("training_compute", "训练计算量", ("训练计算量", "训练算力", "training_compute")),
        ("coverage", "用户或覆盖人数", ("用户或覆盖人数", "覆盖人数", "用户覆盖", "coverage")),
        ("capability_tests", "能力和安全测试", ("能力和安全测试", "能力测试", "capability_tests")),
        ("incidents", "滥用、事故或投诉", ("滥用事故或投诉", "事故", "投诉", "incidents")),
        ("regulator_notice", "监管或AI Office通知", ("监管或AIOffice通知", "指定情况", "监管通知", "regulator_notice")),
    ),
    "E3": (
        ("model_version", "模型代号和版本", ("模型代号和版本", "模型版本", "model_version")),
        ("capabilities", "真实任务能力", ("真实任务能力", "实际能完成哪些任务", "多种任务", "固定任务", "capabilities")),
        ("deployment_status", "投放或原型状态", ("投放或原型状态", "投放状态", "研究或原型", "deployment_status")),
        ("sample_evidence", "能力样例和证据名称", ("能力样例和证据名称", "能力样例", "证据名称", "sample_evidence")),
    ),
    "F0": (
        ("identifiable_information", "能识别个人的信息", ("是否接收能识别个人的信息", "能识别个人的信息", "identifiable_information")),
        ("sensitive_information", "健康、声音、人脸、位置、财务或未成年人信息", ("是否可能接收健康声音人脸位置财务或未成年人信息", "健康声音人脸位置财务或未成年人信息", "sensitive_information")),
        ("overseas_access", "境外接收、远程查看或备份", ("是否有境外公司或人员接收远程查看或备份数据", "境外接收远程查看或备份", "overseas_access")),
        ("external_service", "外部AI或云服务处理", ("是否使用外部AI或云服务处理这些数据", "外部AI或云服务", "external_service")),
    ),
    "F3": (
        ("purpose", "为什么使用信息", ("为什么使用信息", "处理目的", "目的", "用途", "purpose")),
        ("entity_country", "实体名称和国家", ("实体名称和国家", "实体", "国家", "entity_country")),
        ("purpose_decider", "谁决定用途", ("谁决定用途", "谁决定为什么使用", "决定目的", "purpose_decider")),
        ("means_decider", "谁按指令操作", ("谁按指令操作", "谁决定怎样使用", "决定方式", "means_decider")),
        ("client_instruction", "是否按客户书面指令", ("是否按客户书面指令", "客户书面指令", "client_instruction")),
        ("subcontracting", "谁再委托服务商", ("谁再委托服务商", "是否再委托其他服务商", "再委托", "subcontracting")),
        ("access", "谁能访问哪些数据", ("谁能访问哪些数据", "访问哪些数据", "access")),
        ("contract", "合同或指令名称", ("合同或指令名称", "合同", "指令名称", "contract")),
    ),
    "F4": (
        ("sensitive_data", "敏感信息", ("特殊类别数据", "敏感信息", "敏感数据", "sensitive_data")),
        ("automated_decision", "自动化重大结果", ("自动化重大决定", "自动决定", "automated_decision")),
        ("human_override", "人工能否改变结果", ("人工能真实改变", "人工是否能实际改变结果", "human_override")),
    ),
    "G1": (
        ("flow_id", "稳定数据流编号", ("稳定数据流编号", "数据流编号", "流编号", "flow_id")),
        ("sender", "发送方实体和国家", ("发送方实体和国家", "发送方", "sender")),
        ("recipient", "接收方实体和国家", ("接收方实体和国家", "接收方", "recipient")),
        ("remote_support", "远程支持国家", ("远程支持国家", "远程支持", "remote_support")),
        ("backup", "备份或灾备国家", ("备份或灾备国家", "备份国家", "backup")),
        ("subprocessors", "分包商", ("分包商", "上游模型方", "云服务商", "subprocessors")),
        ("access", "谁能看到哪些数据", ("谁能看到", "访问权限", "access")),
        ("purpose", "数据用途", ("数据用途", "purpose")),
        ("onward_transfer", "再传输", ("再传输", "onward_transfer")),
        ("key_controller", "密钥控制者", ("密钥由谁控制", "密钥控制者", "key_controller")),
        ("evidence_date", "证据名称和日期", ("证据名称和日期", "证据日期", "evidence_date")),
    ),
    "G2": (
        ("flow_id", "稳定数据流编号", ("稳定数据流编号", "数据流编号", "流编号", "flow_id")),
        ("mechanism_document", "跨境文件或依据", ("目的地保护决定", "标准合同", "集团内部规则", "正式保障", "例外使用记录", "普通商业合同", "没有相关文件", "不确定", "mechanism_document")),
        ("document_details", "文件名称、日期和覆盖范围", ("文件名称签署日期和覆盖范围", "签署日期", "覆盖范围", "document_details")),
    ),
    "G3": (
        ("flow_id", "稳定数据流编号", ("稳定数据流编号", "数据流编号", "流编号", "flow_id")),
        ("country_risk", "数据实际去往的国家及政府访问风险调查", ("数据实际去往的国家", "目的国政府访问风险", "风险调查", "TIA", "country_risk")),
        ("encryption", "加密", ("加密", "encryption")),
        ("key_separation", "密钥隔离", ("密钥隔离", "key_separation")),
        ("pseudonymisation", "假名化", ("假名化", "pseudonymisation")),
        ("minimisation", "数据最小化", ("数据最小化", "最小化", "minimisation")),
        ("access_separation", "访问隔离", ("访问隔离", "access_separation")),
        ("onward_restrictions", "再传输限制", ("再传输限制", "onward_restrictions")),
        ("evidence_date", "报告名称和日期", ("报告名称和日期", "证据日期", "evidence_date")),
    ),
    "H1": (
        ("ca_data", "California居民数据", ("California居民数据", "加州居民数据", "ca_data")),
        ("threshold", "企业规模和门槛事实", ("企业规模和门槛事实", "门槛", "年度收入", "数据量", "threshold")),
        ("client_instruction", "是否按客户指令服务", ("是否按客户指令提供服务", "客户指令", "client_instruction")),
        ("sale_share", "出售或广告共享", ("是否出售或为定向广告共享", "出售", "共享", "sale_share")),
        ("sensitive", "敏感个人信息", ("敏感个人信息", "SPI", "sensitive")),
        ("children", "儿童数据", ("儿童", "children")),
        ("gpc", "全局隐私控制", ("全局隐私控制", "GPC", "gpc")),
    ),
    "K2": (
        ("choice_ui", "是否显示允许或拒绝选项", ("是否显示允许或拒绝选项", "是否显示同意或拒绝选项", "显示允许或拒绝", "显示同意或拒绝", "允许或拒绝选项", "同意或拒绝选项", "choice_ui")),
        ("refusal_function", "拒绝后核心功能能否运行", ("拒绝后核心功能能否运行", "拒绝后核心功能", "refusal_function")),
        ("write_timing", "读写发生时点", ("读写发生时点", "读写时点", "用户请求前后", "write_timing")),
        ("communication_without", "不读写能否完成通信", ("不读写能否完成通信", "不读写时能否完成", "communication_without")),
        ("target_country", "目标国家", ("目标国家", "target_country")),
        ("record_time", "允许或拒绝记录时间", ("允许或拒绝记录时间", "同意记录时间", "记录时间", "record_time")),
        ("evidence", "平台证据", ("平台证据", "证据", "evidence")),
    ),
}

# Older answer files used A1 for project contacts and the launch date. Keep
# those labels parseable for audit/migration, but do not make them required or
# publish them in the current questionnaire. A legacy launch date can be
# inherited as an existing fact when the assessment is migrated to A3.
OPTIONAL_LEGACY_ITEMIZED_FIELDS: dict[
    str, tuple[tuple[str, str, tuple[str, ...]], ...]
] = {
    "A1": (
        ("product_owner", "产品负责人", ("产品负责人", "product_owner")),
        ("technical_owner", "技术负责人", ("技术负责人", "technical_owner")),
        (
            "legal_owner",
            "隐私或法务联系人",
            ("隐私或法务联系人", "隐私/法务联系人", "法务联系人", "legal_owner"),
        ),
        ("launch_date", "计划上线日期", ("计划上线日期", "上线日期", "launch_date")),
    ),
}


def normalize_text(value: Any) -> str:
    """Normalize full-width input while retaining the user's language."""

    return unicodedata.normalize("NFKC", str(value or "")).replace("\u00a0", " ").strip()


def public_step_key(step_number: str | int, context: Any = "") -> str:
    """Map scope-entry labels while accepting legacy numbered tables.

    The current public table labels P0 as ``模式题`` and P1-P4 as four
    numbered scope steps.  Content markers still take precedence, so old
    tables using the former five-step numbering remain parseable.
    """

    number = int(step_number)
    text = normalize_text(context)
    compact = compact_text(text)
    if "轻量版初步评估" in text or "全量版评估" in text:
        return "P0"
    # Current public labels are Mode + four scope steps.  Prefer the
    # question's visible wording over generic words such as “欧盟” that may
    # appear inside another step's options.
    if any(marker in text for marker in ("这次先想了解哪一类问题", "只看AI内容透明度", "欧盟产品或系统", "模型来源", "系统和模型都看")):
        return "P2"
    if any(marker in text for marker in ("透明度之外是否顺便提示", "附属筛查", "顺便提示个人信息", "顺便简要提示")):
        return "P3"
    if any(marker in compact for marker in ("请用一句话说清产品是什么给谁用", "产品一句话", "主要客户或使用者", "产品是什么给谁用")):
        return "P4"
    if any(marker in text for marker in ("本次咨询要看哪些地区", "中国大陆", "美国", "欧盟", "尚未确定")):
        return "P1"
    # With no semantic context, use the current public numbering.  Number 5
    # remains accepted for legacy five-step tables and maps to the product
    # description row.
    return {1: "P1", 2: "P2", 3: "P3", 4: "P4", 5: "P4"}[number]


def _assert_safe_text(value: Any, context: str = "答案") -> None:
    """Reject invisible control characters that can corrupt parsing or logs."""

    if not isinstance(value, str):
        return
    if any(unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in value):
        raise ValueError(f"{context}包含不可见控制字符（例如 NUL），请删除后重新提交")


def _assert_input_size(text: str) -> None:
    if len(text) > MAX_INPUT_CHARS:
        raise ValueError(
            f"答案文件过长（{len(text):,} 个字符，当前上限为 {MAX_INPUT_CHARS:,}）；"
            "请只填写本次自测事实和证据名称，不要粘贴完整合同、日志或大段附件"
        )


def _walk_safe_values(value: Any, context: str = "答案") -> None:
    """Check decoded JSON too, because escaped NULs are invisible in the file."""

    if isinstance(value, str):
        _assert_safe_text(value, context)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk_safe_values(item, f"{context}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _walk_safe_values(key, f"{context}字段名")
            _walk_safe_values(item, f"{context}.{key}")


def compact_text(value: Any) -> str:
    # Punctuation is presentation in field labels (including full-width
    # Chinese punctuation), not part of their stable identity.
    return re.sub(r"[\s\u3000,，、;；:：/|]+", "", normalize_text(value)).lower()


def _strip_trailing_punctuation(value: str) -> str:
    return re.sub(r"[。．.!！?？]+$", "", value.strip())


def _is_explicit_uncertain(value: Any) -> bool:
    """Whether a value itself selects an unresolved/unknown state.

    This intentionally does not search arbitrary prose.  A note such as
    ``证据还没有整理`` must not turn a confirmed answer in another field into
    a contradictory selection.
    """

    text = _strip_trailing_punctuation(normalize_text(value)).lower()
    if not text:
        return False
    patterns = (
        r"^不确定(?:\s*[（(].*[）)])?$",
        r"^不确定\s*[,，;；:]\s*先.+$",
        r"^unknown$",
        r"^uncertain$",
        r"^待核实(?:\s*[（(].*[）)])?$",
        r"^事实待核实(?:\s*[（(].*[）)])?$",
        r"^尚未决定(?:\s*[（(].*[）)])?$",
        r"^待补材料$",
        r"^无数据(?:\s*/\s*不确定)?$",
        r"^未核实$",
    )
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def _is_uncertain_prose(value: Any) -> bool:
    """Recognize common business-language uncertainty in a standalone answer."""

    text = _strip_trailing_punctuation(normalize_text(value)).lower()
    return bool(re.match(r"^(?:不知道|不清楚|尚未确认|还没(?:看|核对|拿到)|无法确认|未核实|待核实|暂未决定)", text))


def _is_explicit_exclusive(value: Any, question_key: str = "") -> bool:
    """Whether a value selects a row-level exclusive option.

    Phrases such as ``没有机器可读来源信息`` are descriptive facts, not the
    C3 option ``还没有``.  Only exact option-like forms are treated as
    exclusive here.
    """

    text = _strip_trailing_punctuation(normalize_text(value)).lower()
    if not text:
        return False
    compact = re.sub(r"\s+", "", text)
    exact_prefixes = (
        "均未完成", "以上均无", "以上都没有", "没有模型", "没有机制",
        "无生成内容", "没有内容输出", "没有内容传播", "还没有",
        "暂不评估", "仅服务器端", "notapplicable", "none",
        "没有相关文件",
    )
    if any(compact == prefix.lower() or compact.startswith(prefix.lower() + "（") or compact.startswith(prefix.lower() + "(") for prefix in exact_prefixes):
        return True
    # A bare “没有” is an option; a sentence beginning “没有……但……” is a
    # factual description and is deliberately not exclusive.
    return compact in {"没有", "无", "no"}


def contains_uncertain(value: str) -> bool:
    """Backward-compatible broad phrase helper for callers outside the checker."""

    lowered = normalize_text(value).lower()
    return any(phrase.lower() in lowered for phrase in UNCERTAIN_PHRASES)


def contains_exclusive(value: str) -> bool:
    return _is_explicit_exclusive(value)


def nonempty_parts(answer: str) -> list[str]:
    return [part.strip() for part in SEPARATOR_RE.split(normalize_text(answer)) if part.strip()]


def _looks_like_marker(segment: str, question_key: str) -> bool:
    """Return true when a segment is an explicit answer option, not a note."""

    text = _strip_trailing_punctuation(normalize_text(segment))
    if not text:
        return False
    if NOTE_LABEL_RE.match(text):
        return False
    key = question_key.upper().strip()
    markers = SINGLE_OPTION_MARKERS.get(key, ()) + MULTI_OPTION_MARKERS.get(key, ())
    compact = compact_text(text)
    if _is_explicit_uncertain(text) or _is_uncertain_prose(text) or _is_explicit_exclusive(text):
        return True
    if re.match(r"^(?:是|否|有|无|yes|no)(?:$|[且，,：:（(])", text, re.I):
        return True
    if markers:
        for marker in markers:
            if compact == compact_text(marker):
                return True
            # Some business answers naturally add a short qualifier to an
            # option, e.g. “有欧盟客户使用”.
            if compact.startswith(compact_text(marker)) and len(compact) <= len(compact_text(marker)) + 24:
                return True
    for marker in MULTI_OPTION_MARKERS.get(key, ()):
        marker_compact = compact_text(marker)
        if marker_compact and (compact == marker_compact or (compact.startswith(marker_compact) and len(compact) <= len(marker_compact) + 24)):
            return True
    return False


def _is_canonical_option(value: Any, question_key: str, mode: str) -> bool:
    """Return whether a non-itemized value matches a maintained option.

    ``single_parts`` and ``multi_parts`` historically retained an arbitrary
    first segment so a free-form note could be shown to the caller.  That is
    useful for itemized facts but unsafe for a closed single/multi-choice row:
    ``P0: 随便写`` must not become a valid mode selection.  Keep the matching
    rules (short qualifiers and explicit uncertainty) in one place and use
    this helper as the final gate for known closed-choice questions.
    """

    key = question_key.upper().strip()
    text = _strip_trailing_punctuation(normalize_text(value))
    if not text:
        return False
    if _is_explicit_uncertain(text) or _is_uncertain_prose(text) or _is_explicit_exclusive(text):
        return True
    if mode == "single":
        markers = SINGLE_CANONICAL_OPTIONS.get(key, ()) + SINGLE_OPTION_MARKERS.get(key, ())
    else:
        markers = MULTI_OPTION_MARKERS.get(key, ())
    compact = compact_text(text)
    for marker in markers:
        marker_compact = compact_text(marker)
        if not marker_compact:
            continue
        if compact == marker_compact:
            return True
        # Business users often append a short factual qualifier to an option,
        # such as “有欧盟客户使用”.  Keep the existing bounded suffix rule.
        if compact.startswith(marker_compact) and len(compact) <= len(marker_compact) + 24:
            return True
    return False


def _split_note(value: str) -> tuple[str, str]:
    """Split an answer value from a labelled free-form note."""

    text = normalize_text(value)
    if not text:
        return "", ""
    # A note marker after a choice is never another choice.  Keep the note in
    # the returned tuple for audit display, but omit it from classification.
    match = re.search(r"(?:^|[;；\n])\s*(?:备注|说明|补充|原因|背景|证据|依据|自由注释|note|comment)\s*[:：]", text, re.I)
    if match:
        before = text[:match.start()].rstrip(" ;；\n")
        note = text[match.end():].strip()
        return before, note
    return text, ""


def _choice_values_from_value(value: Any, question_key: str = "") -> list[str]:
    """Extract explicit choices from a scalar/list field value."""

    if isinstance(value, dict):
        if "value" in value:
            return _choice_values_from_value(value.get("value"), question_key)
        if "selected" in value:
            return _choice_values_from_value(value.get("selected"), question_key)
        return []
    if isinstance(value, (list, tuple)):
        result: list[str] = []
        for item in value:
            result.extend(_choice_values_from_value(item, question_key))
        return result
    text = normalize_text(value)
    if not text:
        return []
    text, _note = _split_note(text)
    # Explicit slash/semicolon alternatives are choices only when each part
    # looks like an option.  Ordinary prose remains one value and is later
    # reported as an extraction task rather than misclassified.
    parts = [p.strip() for p in re.split(r"[;；/]+", text) if p.strip()]
    if len(parts) > 1 and all(_looks_like_marker(p, question_key) for p in parts):
        return parts
    return [text]


def single_parts(answer: str, question_key: str = "") -> list[str]:
    """Return explicit single-choice selections; labelled notes are ignored."""

    text = normalize_text(answer)
    if not text:
        return []
    key = question_key.upper().strip()
    # Inspect explicit choice separators before accepting a canonical option
    # as a prefix.  Otherwise an answer such as “有欧盟连接点；目前只有
    # 中国大陆” would silently discard the second, conflicting selection.
    separated = [part.strip() for part in re.split(r"[;；|\n]+", text) if part.strip()]
    if len(separated) > 1:
        separated_choices = []
        for part in separated:
            choice, _note = _split_note(part)
            if _looks_like_marker(choice, key):
                separated_choices.append(choice)
        if len(separated_choices) > 1:
            return separated_choices
    # Prefer a complete known option before splitting punctuation.  This keeps
    # the natural comma in “有欧盟提供、部署或客户使用” inside the option.
    for option in SINGLE_CANONICAL_OPTIONS.get(key, ()):
        if compact_text(text).startswith(compact_text(option)):
            return [option]
    # Semicolon/newline are conventional choice separators.  Comma and ideographic
    # comma are considered separators only if every resulting part is an option.
    rough = [part.strip() for part in re.split(r"[;；|\n]+", text) if part.strip()]
    if len(rough) == 1:
        comma_parts = [part.strip() for part in re.split(r"[,，、]+", rough[0]) if part.strip()]
        if len(comma_parts) > 1 and all(_looks_like_marker(p, question_key) for p in comma_parts):
            rough = comma_parts
        elif len(comma_parts) > 1:
            recognized = [part for part in comma_parts if _looks_like_marker(part, question_key)]
            if recognized:
                # One explicit option followed by an unlabelled sentence is
                # an answer plus a note, not two selected options.
                rough = recognized
    explicit: list[str] = []
    for index, part in enumerate(rough):
        choice, _note = _split_note(part)
        if _looks_like_marker(choice, question_key):
            explicit.append(choice)
        elif index == 0 and not explicit and not NOTE_LABEL_RE.match(part):
            # A free-form first segment is retained so the caller can report a
            # missing/unknown option, but later prose is treated as a note.
            explicit.append(choice)
    # Known single-choice rows are closed sets.  Do not let the legacy
    # free-form-first-segment fallback turn arbitrary text into a selection.
    if key in SINGLE_KEYS or key in SINGLE_CANONICAL_OPTIONS:
        return [value for value in explicit if _is_canonical_option(value, key, "single")]
    return explicit


def _consume_compact_prefix(text: str, compact_prefix: str) -> str:
    """Remove a whitespace-insensitive prefix while preserving the value text."""

    consumed = 0
    end = 0
    for index, char in enumerate(text):
        if char.isspace() or char in "\u3000,，、;；:=：/|":
            continue
        consumed += len(char)
        end = index + 1
        if consumed >= len(compact_prefix):
            return text[end:]
    return ""


def _known_field_prefix(question_key: str, part: str) -> tuple[str, str] | None:
    """Recognize ``字段 是`` answers where the business omitted a colon."""

    compact = compact_text(part)
    aliases: list[tuple[str, str]] = []
    for field_key, _display, field_aliases in _parse_field_alias_map(question_key):
        aliases.extend((field_key, compact_text(alias)) for alias in field_aliases if compact_text(alias))
    for field_key, alias in sorted(aliases, key=lambda item: len(item[1]), reverse=True):
        if compact.startswith(alias) and len(compact) > len(alias):
            remainder = _consume_compact_prefix(part, alias).strip(" \t\u3000:=：-．.、")
            if remainder:
                return part[: len(part) - len(_consume_compact_prefix(part, alias))].strip(), remainder
    return None


def itemized_parts(answer: str, question_key: str = "") -> list[tuple[str, str]]:
    """Return ``(label, value)`` pairs without treating the whole row as one choice."""

    text = normalize_text(answer)
    parts = [part.strip() for part in re.split(r"[\r\n;；]+", text) if part.strip()]
    result: list[tuple[str, str]] = []
    for part in parts:
        match = re.match(r"^(?:[-•]\s*)?(?P<label>[^:=：]{1,120})\s*[:=：]\s*(?P<value>.*)$", part)
        if match:
            result.append((match.group("label").strip(), match.group("value").strip()))
            continue
        numbered = re.match(r"^(?:[-•]\s*)?(?P<label>[1-9]\d*)\s*[.．、)）:-]\s*(?P<value>.+)$", part)
        if numbered:
            result.append((numbered.group("label"), numbered.group("value").strip()))
            continue
        prefix = _known_field_prefix(question_key, part) if question_key else None
        if prefix:
            result.append(prefix)
        else:
            result.append(("", part))
    return result


def expected_mode(question_key: str, advertised: str = "") -> str:
    key = question_key.upper().strip()
    if key in ITEMIZED_KEYS:
        return "itemized"
    if key in SINGLE_KEYS:
        return "single"
    return infer_mode(advertised)


def _field_alias_map(question_key: str) -> list[tuple[str, str, tuple[str, ...]]]:
    return list(REQUIRED_ITEMIZED_FIELDS.get(question_key.upper(), ()))


def _parse_field_alias_map(question_key: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """Return current fields plus legacy labels accepted only for migration."""

    key = question_key.upper()
    return list(REQUIRED_ITEMIZED_FIELDS.get(key, ())) + list(
        OPTIONAL_LEGACY_ITEMIZED_FIELDS.get(key, ())
    )


def _canonical_field(question_key: str, label: Any) -> str:
    """Map a business label to a stable field key without legal inference."""

    text = normalize_text(label)
    compact = compact_text(text)
    # Repeated-row prefixes are identifiers, not part of the field name.
    compact_without_prefix = re.sub(
        r"^(?:链路(?:[一二三四五六七八九十]+|\d+)|模型(?:[一二三四五六七八九十]+|\d+|[A-Za-z][A-Za-z0-9_.-]*)|流(?:[一二三四五六七八九十]+|\d+|[A-Za-z][A-Za-z0-9_.-]*)|第?\d+号?)",
        "",
        compact,
        flags=re.I,
    )
    # A repeated-record prefix is only stripped when it is followed by a
    # separator or a known field alias.  This prevents the legitimate field
    # label “模型或功能” from being mistaken for record “模型”.
    if compact_without_prefix == compact and compact.startswith("模型"):
        compact_without_prefix = compact
    for field_key, _display, aliases in _parse_field_alias_map(question_key):
        for alias in aliases:
            alias_compact = compact_text(alias)
            # Search the complete label first.  This handles natural labels
            # such as “模型A训练目标” and “流EU-US-01发送方”; the record prefix
            # is separately retained as record_id.
            if alias_compact and alias_compact in compact:
                return field_key
            if alias_compact and alias_compact in compact_without_prefix:
                return field_key
    if compact_without_prefix:
        return "__unknown__"
    return "__unlabelled__"


def _record_id(label: Any) -> str:
    text = normalize_text(label)
    match = re.match(
        r"^(?P<record>链路(?:[一二三四五六七八九十]+|\d+)|模型(?:[一二三四五六七八九十]+|\d+|[A-Za-z][A-Za-z0-9_.-]*)|流(?:[一二三四五六七八九十]+|\d+|[A-Za-z][A-Za-z0-9_.-]*)|第?\d+号?)",
        text,
        re.I,
    )
    return compact_text(match.group("record")) if match else "default"


def _strip_record_prefix(label: str) -> str:
    return re.sub(
        r"^(?:链路(?:[一二三四五六七八九十]+|\d+)|模型(?:[一二三四五六七八九十]+|\d+|[A-Za-z][A-Za-z0-9_.-]*)|流(?:[一二三四五六七八九十]+|\d+|[A-Za-z][A-Za-z0-9_.-]*)|第?\d+号?)",
        "",
        normalize_text(label),
        flags=re.I,
    ).strip(" ：:.-")


def _flatten_field_object(question_key: str, value: Any, record: str = "default") -> list[dict[str, Any]]:
    """Flatten dict/list field encodings used by JSON questionnaire answers."""

    entries: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            entries.extend(_flatten_field_object(question_key, item, record))
        return entries
    if isinstance(value, dict):
        if "field" in value or "field_key" in value:
            label = value.get("field", value.get("field_key", ""))
            item_record = value.get("record_id", value.get("row", value.get("item", record)))
            raw_value = value.get("value", value.get("answer", value.get("selected", "")))
            entries.append({
                "label": normalize_text(label),
                "value": raw_value,
                "record_id": normalize_text(item_record) or "default",
                "note": normalize_text(value.get("note", value.get("comment", ""))),
                "evidence": normalize_text(value.get("evidence", "")),
            })
            return entries
        if "value" in value and len(value) <= 5:
            entries.append({
                "label": "",
                "value": value.get("value"),
                "record_id": record,
                "note": normalize_text(value.get("note", value.get("comment", ""))),
                "evidence": normalize_text(value.get("evidence", "")),
            })
            return entries
        # A nested mapping is commonly {"链路一": {"展示方": "客户"}}.
        for label, child in value.items():
            if isinstance(child, dict) and not ("value" in child or "field" in child or "field_key" in child):
                nested_record = normalize_text(label) or record
                for nested in _flatten_field_object(question_key, child, nested_record):
                    # Nested objects use the outer key as a record identifier,
                    # while the inner property remains the field label.
                    if nested.get("record_id") in {"default", ""}:
                        nested["record_id"] = nested_record
                    entries.append(nested)
            else:
                entries.append({
                    "label": normalize_text(label),
                    "value": child,
                    "record_id": record,
                    "note": "",
                    "evidence": "",
                })
        return entries
    entries.append({"label": "", "value": value, "record_id": record, "note": "", "evidence": ""})
    return entries


def _entries_from_strings(question_key: str, values: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not isinstance(values, list):
        values = [values]
    for raw in values:
        if isinstance(raw, dict):
            entries.extend(_flatten_field_object(question_key, raw))
            continue
        text = normalize_text(raw)
        if not text:
            continue
        # A selected item may itself contain multiple labelled fields.  For
        # ordinary multi-choice rows, retain the whole option as an unlabelled
        # value instead of treating its punctuation as field names.
        if question_key.upper() not in ITEMIZED_KEYS:
            entries.append({"label": "", "value": text, "record_id": "default", "note": "", "evidence": ""})
            continue
        for label, value in itemized_parts(text, question_key):
            if label:
                entries.append({
                    "label": label,
                    "value": value,
                    "record_id": _record_id(label),
                    "note": "",
                    "evidence": "",
                })
            else:
                choice, note = _split_note(value)
                entries.append({"label": "", "value": choice, "record_id": "default", "note": note, "evidence": ""})
    return entries


def field_entries(question_key: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return structured field entries, preferring explicit JSON structure."""

    key = question_key.upper().strip()
    fields = row.get("fields")
    if fields not in (None, "", [], {}):
        entries = _flatten_field_object(key, fields)
    elif row.get("selected"):
        entries = _entries_from_strings(key, row.get("selected"))
    else:
        entries = _entries_from_strings(key, [row.get("answer", "")])
    legacy_keys = {
        field_key
        for field_key, _display, _aliases in OPTIONAL_LEGACY_ITEMIZED_FIELDS.get(key, ())
    }
    for entry in entries:
        entry["field_key"] = _canonical_field(key, entry.get("label", ""))
        entry["display_label"] = normalize_text(entry.get("label", "")) or entry["field_key"]
        entry["record_id"] = normalize_text(entry.get("record_id", "default")) or "default"
        entry["legacy_input_only"] = entry["field_key"] in legacy_keys
    # P4 is intentionally friendly to a bare one-sentence reply.  If the
    # business does not add field labels, treat the first sentence as the
    # product description and leave the audience field pending.
    if key == "P4":
        unlabelled = [entry for entry in entries if entry.get("field_key") == "__unlabelled__"]
        if unlabelled:
            first = True
            for entry in unlabelled:
                if first:
                    entry["field_key"] = "product_description"
                    entry["display_label"] = "产品一句话"
                    first = False
                else:
                    entry["field_key"] = "target_users"
                    entry["display_label"] = "主要客户或使用者"
        # P4 is deliberately business-friendly: a natural sentence such as
        # “面向消费者的智能客服助手” contains both the product and audience
        # facts even when no field labels were typed.  Add an audit-only
        # audience entry so strict final checking does not force a rigid form.
        present_fields = {entry.get("field_key") for entry in entries}
        combined = normalize_text(row.get("answer") or row.get("answer_text") or "")
        audience_hint = re.search(
            r"面向|最终用户|用户是|用户为|客户是|客户为|消费者|客户|员工|求职者|学生|患者|公众|内部人员|内部使用",
            combined,
        )
        if "target_users" not in present_fields and audience_hint:
            entries.append(
                {
                    "label": "主要客户或使用者",
                    "value": combined,
                    "record_id": "default",
                    "note": "自然语言受众事实",
                    "evidence": "",
                    "field_key": "target_users",
                    "display_label": "主要客户或使用者",
                }
            )
    return entries


def _answer_state(value: Any, question_key: str = "") -> str:
    text = normalize_text(value)
    if not text:
        return "blank"
    choice, _note = _split_note(text)
    if _is_explicit_uncertain(choice) or _is_uncertain_prose(choice):
        return "unknown"
    if _is_explicit_exclusive(choice, question_key):
        return "exclusive"
    compact = compact_text(choice)
    if compact in {"是", "yes", "有", "适用", "已完成", "已实现", "纳入评估"} or compact.startswith("是且") or compact.startswith("有且"):
        return "positive"
    if compact in {"否", "no", "不适用", "未完成", "未实现", "否且有证据", "事实为否且有证据"} or compact.startswith("否且"):
        return "negative"
    if compact in {"部分完成", "部分", "评估中", "planned", "partial"}:
        return "partial"
    return "definite"


def _entry_choice_values(entry: dict[str, Any], question_key: str) -> list[str]:
    values = _choice_values_from_value(entry.get("value"), question_key)
    return values or ([normalize_text(entry.get("value"))] if normalize_text(entry.get("value")) else [])


def multi_parts(answer: Any, question_key: str = "") -> list[str]:
    """Split a multi-choice answer while keeping free-form notes intact."""

    if isinstance(answer, (list, tuple)):
        result: list[str] = []
        for item in answer:
            result.extend(multi_parts(item, question_key))
        return result
    text = normalize_text(answer)
    if not text:
        return []
    choice_text, _note = _split_note(text)
    # Semicolons/newlines are the table's explicit choice separators.  A
    # Chinese comma is accepted when all fragments resemble options; otherwise
    # it remains part of a natural-language fact description.
    parts = [p.strip() for p in re.split(r"[;；|\n]+", choice_text) if p.strip()]
    if len(parts) == 1:
        comma_parts = [p.strip() for p in re.split(r"[,，、]+", parts[0]) if p.strip()]
        marker_set = MULTI_OPTION_MARKERS.get(question_key.upper(), ())
        if len(comma_parts) > 1 and (
            all(_looks_like_marker(p, question_key) for p in comma_parts)
            or (marker_set and all(any(compact_text(marker) in compact_text(p) for marker in marker_set) for p in comma_parts))
        ):
            parts = comma_parts
    recognized = [part for part in parts if _looks_like_marker(part, question_key)]
    # Known multi-choice rows are closed sets.  Returning an arbitrary prose
    # fragment here would make ``P1: 随便写`` look like a definite answer.  An
    # explicit unknown expression is recognised above and remains valid.
    if question_key.upper().strip() in MULTI_OPTION_MARKERS:
        return [part for part in recognized if _is_canonical_option(part, question_key, "multi")]
    # For an unlisted/inferred multi row retain the historical behaviour; the
    # caller may still use the free-form value as a fact description.
    return recognized or parts


def itemized_conflicts(question_key: str, entries: list[dict[str, Any]]) -> list[str]:
    """Check unknown/negative/positive conflicts within one field and row."""

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in entries:
        if entry.get("field_key") in {"__unlabelled__", "__unknown__"}:
            continue
        groups.setdefault((entry.get("record_id", "default"), entry["field_key"]), []).append(entry)
    conflicts: list[str] = []
    for (record, field), items in groups.items():
        values: list[str] = []
        states: list[str] = []
        for item in items:
            for value in _entry_choice_values(item, question_key):
                values.append(value)
                states.append(_answer_state(value, question_key))
        if not values:
            continue
        nonblank_states = [state for state in states if state != "blank"]
        has_unknown = "unknown" in nonblank_states
        has_definite = any(state not in {"unknown", "blank"} for state in nonblank_states)
        has_exclusive = "exclusive" in nonblank_states
        if has_unknown and has_definite:
            conflicts.append(f"{field}（{record}）：不确定不能与确定选项并选")
        elif has_exclusive and len(set(nonblank_states)) > 1:
            conflicts.append(f"{field}（{record}）：否定或暂缓选项不能与其他选项并选")
        elif len(items) > 1:
            if len(set(states)) > 1:
                conflicts.append(f"{field}（{record}）：同一分项同时填写了多个互斥状态")
            else:
                conflicts.append(f"{field}（{record}）：同一分项重复填写；请保留一项")
    return conflicts


def itemized_completeness(question_key: str, entries: list[dict[str, Any]], row: dict[str, Any] | None = None) -> list[str]:
    """Find omitted required fields; absence is incomplete, never a negative fact."""

    key = question_key.upper()
    required = _field_alias_map(key)
    if not required:
        return []
    # R1 is automatically registered.  A blank row is therefore valid; once
    # the business supplies explicit entries, require all six exactly once.
    if key == "R1" and not entries:
        return []
    present = {entry.get("field_key") for entry in entries if entry.get("field_key") != "__unlabelled__"}
    missing = [display for field_key, display, _aliases in required if field_key not in present]
    if key == "D1" and not missing:
        # Six numbered rows can have labels “1” through “6”; the canonical map
        # already handles those labels, so no prose-length shortcut is needed.
        return []
    return missing


def itemized_unknown_fields(question_key: str, entries: list[dict[str, Any]]) -> list[str]:
    """Return labels that are not part of the published business table.

    A custom label is not treated as a harmless extension: the checker cannot
    know whether it replaces a required fact, so it must be corrected or
    explicitly mapped before assessment.
    """

    if not _field_alias_map(question_key):
        return []
    labels = sorted({
        normalize_text(entry.get("display_label") or entry.get("label"))
        for entry in entries
        if entry.get("field_key") == "__unknown__"
        and normalize_text(entry.get("display_label") or entry.get("label"))
    })
    return labels


def classify(answer: Any = "", selected: list[str] | None = None, question_key: str = "") -> dict[str, Any]:
    """Classify explicit choices only; free-form notes are intentionally ignored."""

    if selected:
        values = []
        for value in selected:
            values.extend(multi_parts(value, question_key) if question_key.upper() not in SINGLE_KEYS else single_parts(value, question_key))
    else:
        values = single_parts(answer, question_key) if question_key.upper() in SINGLE_KEYS else multi_parts(answer, question_key)
    values = [normalize_text(value) for value in values if normalize_text(value)]
    key = question_key.upper().strip()
    if key in SINGLE_KEYS or key in SINGLE_CANONICAL_OPTIONS:
        values = [value for value in values if _is_canonical_option(value, key, "single")]
    elif key in MULTI_OPTION_MARKERS:
        values = [value for value in values if _is_canonical_option(value, key, "multi")]
    states = [_answer_state(value, question_key) for value in values]
    has_unknown = "unknown" in states
    has_exclusive = "exclusive" in states
    has_definite = any(state not in {"unknown", "exclusive", "blank"} for state in states)
    conflicts: list[str] = []
    if has_unknown and has_definite:
        conflicts.append("不确定不能与确定选项并选")
    if has_exclusive and len(states) > 1:
        conflicts.append("否定或暂缓选项不能与其他选项并选")
    return {
        "blank": not bool(values),
        "uncertain": has_unknown,
        "exclusive": has_exclusive,
        "selected": values,
        "conflicts": conflicts,
    }


def _selected_values(selected: Any, question_key: str, mode: str) -> list[str]:
    """Normalize JSON selections, including label/value objects, for checking."""

    if not isinstance(selected, list):
        return []
    values: list[str] = []
    for item in selected:
        if isinstance(item, dict):
            item = item.get("value", item.get("label", item.get("selected", "")))
            parsed = single_parts(item, question_key) if mode == "single" else multi_parts(item, question_key)
            if parsed and any(_looks_like_marker(value, question_key) or _is_explicit_uncertain(value) for value in parsed):
                values.extend(parsed)
            continue
        if isinstance(item, (list, tuple)):
            values.extend(_selected_values(list(item), question_key, mode))
            continue
        if mode == "single":
            values.extend(single_parts(item, question_key))
        else:
            values.extend(multi_parts(item, question_key))
    return values


def infer_mode(options: str) -> str:
    options = normalize_text(options)
    lowered = options.lower()
    # “分项填写” is the outer mode; child fields may themselves be single or
    # multi choice and must not change the row-level mode.
    if "分项填写" in options or "分项单选" in options or "itemized" in lowered:
        return "itemized"
    if "单选" in options or "single" in lowered:
        return "single"
    return "multi"


def _split_markdown_cells(line: str) -> list[str]:
    r"""Split a Markdown table row while honoring escaped ``\|`` values."""

    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    content = stripped[1:]
    if content.endswith("|") and not content.endswith("\\|"):
        content = content[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in content:
        if char == "|" and not escaped:
            cells.append("".join(current).replace(r"\|", "|" ).strip())
            current = []
            escaped = False
            continue
        current.append(char)
        if char == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    cells.append("".join(current).replace(r"\|", "|").strip())
    return cells


def parse_markdown(text: str) -> list[dict[str, Any]]:
    _assert_input_size(text)
    _assert_safe_text(text)
    rows: list[dict[str, Any]] = []
    expected_columns: int | None = None
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _split_markdown_cells(line)
        if not cells:
            continue
        display_key = normalize_text(cells[0])
        mode_match = MODE_LABEL.fullmatch(display_key)
        friendly_match = PUBLIC_STEP.fullmatch(display_key)
        if mode_match:
            friendly_key = "P0"
        elif friendly_match:
            friendly_key = public_step_key(
                friendly_match.group(1) or friendly_match.group(2),
                "；".join(cells[1:4]),
            )
        else:
            friendly_key = "P5" if display_key == "开始问题" else ""
        parsed_key = friendly_key or (display_key.upper() if KEY_ONLY.fullmatch(display_key) else "")
        if expected_columns is None and not parsed_key:
            if normalize_text(cells[0]).startswith("题号") or normalize_text(cells[0]).lower() in {"question", "question key"}:
                expected_columns = len(cells)
            elif len(cells) not in {5, 8}:
                raise ValueError(
                    f"Markdown 第{line_number}行含未转义的竖线或列数错误：识别到{len(cells)}列；答案中的竖线必须写成\\|"
                )
            continue
        if not parsed_key:
            continue
        if expected_columns is None:
            expected_columns = len(cells)
        if expected_columns not in {5, 8}:
            raise ValueError(
                f"Markdown 第{line_number}行列数为{expected_columns}，当前业务表仅支持5列公开表或8列主表；答案中的竖线必须写成\\|"
            )
        if len(cells) != expected_columns:
            raise ValueError(
                f"Markdown 第{line_number}行含未转义的竖线或列数错误：识别到{len(cells)}列，表头为{expected_columns}列；请在答案中的竖线前加\\"
            )
        if len(cells) < 4:
            raise ValueError(f"Markdown 第{line_number}行缺少业务答案列")
        key = parsed_key
        rows.append(
            {
                "question_key": key,
                "mode": expected_mode(key, cells[2]),
                "answer": cells[3],
                "line": line_number,
                "source": "markdown",
            }
        )
    return rows


def parse_json(value: Any) -> list[dict[str, Any]]:
    _walk_safe_values(value)
    if isinstance(value, dict):
        responses = value.get("questionnaire_responses", value.get("responses", []))
    else:
        responses = value
    if not isinstance(responses, list):
        raise ValueError("JSON must contain a questionnaire_responses list")
    rows: list[dict[str, Any]] = []
    for index, response in enumerate(responses, 1):
        if not isinstance(response, dict):
            raise ValueError(f"response {index} is not an object")
        key = normalize_text(response.get("question_key", "")).upper()
        if not key:
            raise ValueError(f"response {index} has no question_key")
        selected = response.get("selected", [])
        if not isinstance(selected, list):
            raise ValueError(f"response {key} selected must be a list")
        rows.append(
            {
                "question_key": key,
                "mode": normalize_text(response.get("mode", "multi")),
                "answer": normalize_text(response.get("answer_text", "")),
                "selected": selected,
                "fields": response.get("fields"),
                "conflict_status": response.get("conflict_status"),
                "correction_note": response.get("correction_note", ""),
                "revision": bool(response.get("revision", False)),
                "row_number": response.get("row_number"),
                "line": index,
                "source": "json",
            }
        )
    return rows


def parse_text(text: str) -> list[dict[str, Any]]:
    _assert_input_size(text)
    _assert_safe_text(text)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        normalized_line = normalize_text(line)
        revision = ROW_REVISION.match(normalized_line)
        if revision:
            row_number = int(revision.group(1))
            if row_number < 1 or row_number > len(BUSINESS_ROW_ORDER):
                raise ValueError(f"第{row_number}行超出当前业务表范围（1-{len(BUSINESS_ROW_ORDER)}）")
            key = BUSINESS_ROW_ORDER[row_number - 1]
            answer = revision.group(2).strip()
            rows.append({
                "question_key": key,
                "mode": expected_mode(key),
                "answer": answer,
                "line": line_number,
                "source": "text-revision",
                "revision": True,
                "row_number": row_number,
            })
            continue
        mode_label = MODE_LABEL.match(normalized_line)
        if mode_label:
            answer = mode_label.group(1).strip()
            key = "P0"
            rows.append(
                {
                    "question_key": key,
                    "mode": expected_mode(key),
                    "answer": answer,
                    "line": line_number,
                    "source": "public-step",
                }
            )
            continue
        step = PUBLIC_STEP.match(normalized_line)
        if step:
            step_number = step.group(1) or step.group(2)
            answer = step.group(3).strip()
            key = public_step_key(step_number, answer)
            rows.append(
                {
                    "question_key": key,
                    "mode": expected_mode(key),
                    "answer": answer,
                    "line": line_number,
                    "source": "public-step",
                }
            )
            continue
        if normalized_line.startswith("开始问题"):
            answer = normalized_line[len("开始问题") :].lstrip(" ：:.-")
            rows.append(
                {
                    "question_key": "P5",
                    "mode": expected_mode("P5"),
                    "answer": answer,
                    "line": line_number,
                    "source": "public-step",
                }
            )
            continue
        match = QUESTION_KEY.match(normalized_line)
        if not match:
            continue
        key, answer = match.groups()
        rows.append(
            {
                "question_key": normalize_text(key).upper(),
                "mode": expected_mode(key),
                "answer": answer.strip(),
                "line": line_number,
                "source": "text",
            }
        )
    return rows


def load_rows(path: Path, fmt: str) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    _assert_input_size(text)
    _assert_safe_text(text)
    if fmt == "auto":
        if path.suffix.lower() == ".json":
            fmt = "json"
        elif any(line.lstrip().startswith("|") for line in text.splitlines()):
            fmt = "markdown"
        else:
            fmt = "text"
    if fmt == "json":
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            raise
        _walk_safe_values(decoded)
        return parse_json(decoded)
    if fmt == "markdown":
        return parse_markdown(text)
    return parse_text(text)


def _latest_answer_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    """Return the effective answer for an entry key while retaining revisions."""

    matching = effective_rows_for_key(rows, key)
    if not matching:
        return None
    return matching[-1]


def effective_rows_for_key(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """Return rows that remain effective for one question key.

    A row parsed from ``第N行改为`` is an explicit replacement.  Once such a
    row exists, the latest revision is the only row used for validation and
    progress; earlier rows stay in the caller's raw list for audit history.
    This also makes a blank revision intentionally clear an older answer.
    """

    matching = [
        row for row in rows
        if normalize_text(row.get("question_key", "")).upper() == key.upper()
    ]
    revisions = [row for row in matching if row.get("revision")]
    return [revisions[-1]] if revisions else matching


def effective_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the complete effective submission while retaining raw history."""

    latest_revision_index: dict[str, int] = {}
    for index, row in enumerate(rows):
        if row.get("revision"):
            latest_revision_index[normalize_text(row.get("question_key", "")).upper()] = index
    return [
        row
        for index, row in enumerate(rows)
        if latest_revision_index.get(normalize_text(row.get("question_key", "")).upper(), index) == index
    ]


def entry_route_conflicts(rows: list[dict[str, Any]]) -> list[str]:
    """Detect a P2/P3 route choice that cannot be interpreted consistently.

    The public master table keeps the full P3 option set for maintenance, while
    the conversation shows only the branch relevant to P2.  A pasted full table
    can therefore contain a stale branch; flag it before a route is locked.
    """

    p2_row = _latest_answer_row(rows, "P2")
    p3_row = _latest_answer_row(rows, "P3")
    if not p2_row or not p3_row:
        return []
    p2 = normalize_text(p2_row.get("answer") or p2_row.get("answer_text") or "")
    p3 = normalize_text(p3_row.get("answer") or p3_row.get("answer_text") or "")
    if not p2 or not p3:
        return []
    p2_transparency_only = (
        "只看AI内容透明度" in p2 or "只看 AI 内容透明度" in p2
    )
    stale_system_branch = any(
        phrase in p3
        for phrase in (
            "还看欧盟产品或系统或模型使用",
            "欧盟产品或系统或模型使用",
            "透明度、系统和模型",
        )
    )
    if p2_transparency_only and stale_system_branch:
        return [
            "P3与P2不一致：P2只看AI内容透明度时，P3不能选择欧盟产品或系统或模型分支；请改为只做透明度、暂不做附属筛查、顺便简要提示附属事项或不确定"
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answers", type=Path, help="completed Markdown, JSON, or text answer file")
    parser.add_argument("--format", choices=("auto", "markdown", "json", "text"), default="auto")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON only")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="允许分组渐进提交；仍拒绝互斥选项、未知题号和未知分项",
    )
    args = parser.parse_args()
    try:
        rows = load_rows(args.answers, args.format)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot parse answers: {exc}", file=sys.stderr)
        return 2

    # Keep the raw submission for audit counts, but validate only the latest
    # explicit revision for each question.  Older rows remain available to the
    # caller through ``load_rows`` and are reported as superseded metadata.
    raw_rows = rows
    rows = effective_rows(raw_rows)
    effective_ids = {id(row) for row in rows}
    superseded_rows = [
        {
            "question_key": normalize_text(row.get("question_key", "")).upper(),
            "line": row.get("line"),
            "source": row.get("source"),
        }
        for row in raw_rows
        if id(row) not in effective_ids
    ]

    findings: list[dict[str, Any]] = []
    pending_verification_keys: set[str] = set()
    seen: dict[str, int] = {}
    if not rows:
        findings.append({
            "question_key": "",
            "line": None,
            "source": args.format,
            "blank": True,
            "conflicts": ["未识别到任何题号或答案"],
            "answer": "",
            "selected": [],
        })
    for row in rows:
        key = normalize_text(row.get("question_key", "")).upper()
        seen[key] = seen.get(key, 0) + 1
        row_findings: list[str] = []
        if key not in KNOWN_KEYS:
            row_findings.append("未知题号，请核对当前业务自测表")
        mode = expected_mode(key, str(row.get("mode", "")))
        selected = row.get("selected") or []
        answer = normalize_text(row.get("answer", ""))
        # Itemized answers are checked independently per child field.  The
        # row-level value may legitimately contain both confirmed and unknown
        # fields, so do not run the multi-choice rule over the concatenation.
        if mode == "itemized":
            entries = field_entries(key, row)
            whole_unknown = _is_explicit_uncertain(answer) or _is_uncertain_prose(answer)
            result = {
                "blank": not bool(answer) and not bool(entries),
                "uncertain": whole_unknown,
                "exclusive": False,
                "selected": selected,
                "conflicts": [],
            }
            row_findings.extend(itemized_conflicts(key, entries))
            if whole_unknown or any(
                _answer_state(value, key) == "unknown"
                for entry in entries
                for value in _entry_choice_values(entry, key)
            ):
                pending_verification_keys.add(key)
            unknown_fields = itemized_unknown_fields(key, entries)
            if unknown_fields:
                row_findings.append(
                    "未知分项字段：" + "、".join(unknown_fields)
                    + "；请使用表格中的字段名，不要自行新增字段"
                )
            # R1 is auto-created by the agent.  A blank R1 row is acceptable,
            # but any explicit R1 fields must cover the fixed six exactly once.
            missing = itemized_completeness(key, entries, row)
            if missing and not whole_unknown and not (key == "R1" and not entries):
                row_findings.append("缺少必填分项：" + "、".join(missing))
            # An unlabelled narrative cannot establish a required field.  For
            # non-critical itemized rows it is retained as a pending fact, not
            # silently treated as a valid selection.
            if answer and not entries and not whole_unknown:
                row_findings.append("未识别到明确分项；请按字段填写，无法判断的字段填‘不确定’")
            result["blank"] = not bool(entries) and not bool(answer)
        else:
            # For JSON, selected is authoritative.  For text/Markdown, only
            # explicit option-like fragments are classified; labelled notes do
            # not participate in choice conflict detection.
            if selected:
                selections = _selected_values(selected, key, mode)
            else:
                selections = single_parts(answer, key) if mode == "single" else multi_parts(answer, key)
            result = classify(answer, selections, key)
            if result.get("uncertain"):
                pending_verification_keys.add(key)
            if (answer or selected) and not selections and mode in {"single", "multi"}:
                row_findings.append("未识别到明确选项；请从业务自测表选择，无法确认时填‘不确定’")
        if mode == "single":
            selections = _selected_values(selected, key, mode) if selected else single_parts(answer, key)
            if len(selections) > 1:
                row_findings.append("单选题出现多个选项")
            # A single-choice answer can contain a trailing free-form note;
            # classify only the first explicit option and leave the note for
            # the audit trail.
        row_findings.extend(result["conflicts"])
        # R1 is auto-registered and may legitimately have an empty business
        # answer.  Every other empty answer remains incomplete.
        is_auto_r1_blank = key == "R1" and result["blank"] and not answer and not selected and not row.get("fields")
        if (result["blank"] and not is_auto_r1_blank) or row_findings:
            findings.append(
                {
                    "question_key": key,
                    "line": row.get("line"),
                    "source": row.get("source"),
                    "blank": result["blank"],
                    "conflicts": row_findings,
                    "answer": answer,
                    "selected": result["selected"],
                }
            )

    for key, count in seen.items():
        duplicate_rows = [row for row in rows if normalize_text(row.get("question_key", "")).upper() == key]
        # Explicit correction syntax is a replacement, not a second answer.
        effective_count = sum(1 for row in duplicate_rows if not row.get("revision"))
        if count > 1 and effective_count > 1 and key not in REPEATABLE_QUESTION_KEYS:
            for item in findings:
                if item.get("question_key") == key:
                    item["conflicts"].append(f"题号重复出现{count}次；请保留一版并写明更正记录")
            if not any(item.get("question_key") == key for item in findings):
                findings.append({
                    "question_key": key,
                    "line": None,
                    "source": "duplicate-check",
                    "blank": False,
                    "conflicts": [f"题号重复出现{count}次；请保留一版并写明更正记录"],
                    "answer": "",
                    "selected": [],
                })

    route_conflicts = entry_route_conflicts(rows)
    if route_conflicts:
        findings.append(
            {
                "question_key": "P3",
                "line": next(
                    (row.get("line") for row in rows if normalize_text(row.get("question_key", "")).upper() == "P3"),
                    None,
                ),
                "source": "route-check",
                "blank": False,
                "conflicts": route_conflicts,
                "answer": normalize_text((_latest_answer_row(rows, "P3") or {}).get("answer", "")),
                "selected": [],
            }
        )

    # A missing field is a normal state while the agent is collecting a group.
    # It remains an error for a final submission, but it must not be presented
    # as a contradictory business answer during incremental collection.
    def is_incomplete_issue(message: str, item: dict[str, Any]) -> bool:
        if item.get("blank"):
            return True
        return any(
            message.startswith(prefix)
            for prefix in (
                "缺少必填分项：",
                "未识别到明确分项；",
                "请补充事实或证据",
            )
        )

    incomplete_count = 0
    hard_conflict_count = 0
    for item in findings:
        item["incomplete"] = False
        item["hard_conflicts"] = []
        for message in item.get("conflicts", []):
            if is_incomplete_issue(message, item):
                item["incomplete"] = True
            else:
                item["hard_conflicts"].append(message)
        if item["incomplete"]:
            incomplete_count += 1
        hard_conflict_count += len(item["hard_conflicts"])

    report = {
        "answers_file": str(args.answers),
        "questions_seen": len(raw_rows),
        "effective_questions_seen": len(rows),
        "superseded_rows": superseded_rows,
        "pending_verification_count": len(pending_verification_keys),
        "pending_verification_keys": sorted(pending_verification_keys),
        "blank_answers": sum(1 for item in findings if item["blank"]),
        "conflict_count": hard_conflict_count,
        "incomplete_count": incomplete_count,
        "findings": findings,
        "status": "conflict" if hard_conflict_count else ("incomplete" if findings else "ok"),
    }
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"问题数: {report['questions_seen']}; 空白: {report['blank_answers']}; "
            f"冲突: {report['conflict_count']}; 待内部核实: {report['pending_verification_count']}"
        )
        for item in findings:
            label = "待补" if item.get("incomplete") and not item.get("hard_conflicts") else ("空白" if item["blank"] else "冲突")
            details = "；".join(item["conflicts"]) or "请补充事实或证据"
            print(f"{item['question_key']}（第{item['line']}行，{label}）：{details}")
        print(f"状态: {report['status']}")
    # Blank, incomplete, malformed or conflicting answers must be corrected
    # before they can feed a legal assessment.
    # During a live conversation, an answered subset is useful state even if
    # required fields in the same row are still missing.  Keep all findings in
    # the JSON/audit output, but let the caller continue when explicitly asked
    # for incremental mode.  Final assessment generation should omit this flag.
    # Incremental mode permits only incomplete rows.  A real contradiction,
    # unknown question, duplicate, or unknown field still requires correction.
    if args.allow_incomplete:
        return 1 if hard_conflict_count else 0
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
