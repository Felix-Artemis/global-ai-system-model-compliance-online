#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 global-ai-system-model-compliance skill 生成的报告（.docx）末尾「批注（判断过程、思路与假设）」
章节转换为 **真实 Word 批注（comments / 气泡）**，并从正文移除该章节。

适用场景：当报告终极交付物为 .docx 时调用，使判断过程/假设/规则适用说明不出现在正文，
而是作为 Word 右侧批注气泡呈现，便于法务直接交付干净正文、内部复核时查看批注。

用法（命令行）：
    python annotations_to_docx_comments.py <report.docx> [--author "合规分析"]
    处理为原地覆盖；如需保留原文件可先复制。

用法（函数）：
    from annotations_to_docx_comments import convert_docx_annotations
    convert_docx_annotations("report.docx", author="合规分析")

依赖：python-docx >= 0.8
"""

import re
import sys
import argparse
from datetime import datetime, timezone

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsmap, qn
from docx.opc.part import Part, XmlPart
from docx.opc.packuri import PackURI

W = nsmap['w']
COMMENTS_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments'
COMMENTS_CT = 'application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml'

# 批注章节标题（位于文档末尾）的关键字，用于定位并裁掉该章节
ANNOTATION_HEADING_KEY = '批注（判断过程'

# 解析用：将「### N. 标题」作为一条批注的切分
SUBSECTION_RE = re.compile(r'^###\s+\d+\.\s*(.+?)\s*$', re.MULTILINE)


# ---------------------------------------------------------------------------
# 1. 解析批注章节的 Markdown 文本为 (title, body) 列表
# ---------------------------------------------------------------------------
def parse_annotations(md_text: str):
    """从批注章节的 markdown 文本中提取每条批注 (title, body)。"""
    entries = []
    # 切分：以 ### 数字. 标题 为界
    matches = list(SUBSECTION_RE.finditer(md_text))
    if not matches:
        # 没有子标题，整段作为一条
        body = md_text.strip()
        if body:
            entries.append(('批注', body))
        return entries
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        body = md_text[start:end].strip()
        entries.append((title, body))
    return entries


# ---------------------------------------------------------------------------
# 2. 从 docx 正文抽取并移除批注章节（按标题段落结构切分为多条批注）
# ---------------------------------------------------------------------------
def _para_all_text(el):
    return ''.join(t.text or '' for t in el.findall('.//' + qn('w:t')))


def _is_heading(el):
    if el.tag != qn('w:p'):
        return None
    pPr = el.find(qn('w:pPr'))
    if pPr is None:
        return None
    pStyle = pPr.find(qn('w:pStyle'))
    if pStyle is None:
        return None
    val = pStyle.get(qn('w:val')) or ''
    return val if val.lower().startswith('heading') else None


def extract_and_strip_annotations(doc: Document):
    """定位「批注（判断过程...」标题，将其后所有 body 子元素切分为
    [(title, body_text), ...] 并从正文移除。返回条目列表。"""
    body = doc.element.body
    children = list(body)
    start = None
    for i, el in enumerate(children):
        if el.tag != qn('w:p'):
            continue
        if ANNOTATION_HEADING_KEY in _para_all_text(el):
            start = i
            break
    if start is None:
        return []
    removed = children[start:]
    entries = []
    cur_title = None
    cur_body = []
    for el in removed:
        hval = _is_heading(el)
        txt = _para_all_text(el)
        if hval is not None:
            if cur_title is None:
                # 第一条标题是「批注（判断过程...）」容器，跳过
                cur_title = '__chapter__'
                continue
            if cur_title != '__chapter__':
                entries.append((cur_title, _para_all_text(cur_body) if not cur_body else _join_body(cur_body)))
            cur_title = txt
            cur_body = []
        else:
            cur_body.append(el)
    if cur_title not in (None, '__chapter__') and cur_body:
        entries.append((cur_title, _join_body(cur_body)))
    elif not entries and removed:
        entries.append(('批注', _join_body(removed)))
    # 真正从正文移除
    for el in removed:
        body.remove(el)
    # 过滤空条目
    entries = [(t.strip(), b.strip()) for t, b in entries if (t.strip() or b.strip())]
    return entries


def _join_body(elements):
    """把若干段落/表格元素拼成文本（表格逐格拼接）。"""
    parts = []
    for el in elements:
        if el.tag == qn('w:tbl'):
            for tc in el.findall('.//' + qn('w:tc')):
                parts.append(_para_all_text(tc))
        else:
            parts.append(_para_all_text(el))
    return '\n'.join(p for p in parts if p)


# ---------------------------------------------------------------------------
# 3. 获取或创建 comments 部件，并确保批注所需样式存在
# ---------------------------------------------------------------------------
def get_or_create_comments_part(doc: Document):
    document_part = doc.part
    for rel in document_part.rels.values():
        if rel.reltype == COMMENTS_REL:
            return rel.target_part
    # 创建新部件
    from lxml import etree
    package = document_part.package
    comments_uri = PackURI('/word/comments.xml')
    comments_el = parse_xml('<w:comments xmlns:w="%s"/>' % W)
    comments_part = XmlPart(comments_uri, COMMENTS_CT, comments_el, package)
    document_part.relate_to(comments_part, COMMENTS_REL)
    # 注册内容类型（override）
    try:
        package.content_types.add_override(comments_uri, COMMENTS_CT)
    except Exception:
        pass
    return comments_part


def ensure_comment_styles(doc: Document):
    """确保 CommentReference（字符）与 CommentText（段落）样式存在。"""
    styles_root = doc.styles.element
    existing = {s.get(qn('w:styleId')) for s in styles_root.findall(qn('w:style'))}
    needed = {
        'CommentReference': ('character', 'annotation reference'),
        'CommentText': ('paragraph', 'annotation text'),
    }
    for sid, (type_, name) in needed.items():
        if sid in existing:
            continue
        style = parse_xml(
            '<w:style xmlns:w="%s" w:type="%s" w:styleId="%s">'
            '<w:name w:val="%s"/></w:style>' % (W, type_, sid, name)
        )
        styles_root.append(style)


# ---------------------------------------------------------------------------
# 4. 在指定段落上挂一条批注（气泡）
# ---------------------------------------------------------------------------
def add_comment(doc: Document, comments_part, anchor_para, cid: int,
                title: str, body: str, author: str):
    p = anchor_para._p
    # (a) 在段落开头插入 commentRangeStart
    crs = parse_xml('<w:commentRangeStart xmlns:w="%s" w:id="%d"/>' % (W, cid))
    p.insert(0, crs)
    # (b) 在段落末尾插入 commentRangeEnd + 引用 run
    cre = parse_xml('<w:commentRangeEnd xmlns:w="%s" w:id="%d"/>' % (W, cid))
    ref_run = parse_xml(
        '<w:r xmlns:w="%s"><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>'
        '<w:commentReference w:id="%d"/></w:r>' % (W, cid)
    )
    p.append(cre)
    p.append(ref_run)
    # (c) 写入 comments 部件
    comment = parse_xml('<w:comment xmlns:w="%s" w:id="%d" w:author="%s" '
                        'w:date="%s" w:initials="%s"/>' % (
                            W, cid, author,
                            datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                            author[:4]))
    c_p = parse_xml('<w:p xmlns:w="%s"><w:pPr><w:pStyle w:val="CommentText"/></w:pPr>'
                   '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (W, _esc(title + '\n\n' + body)))
    comment.append(c_p)
    comments_part.element.append(comment)


def _esc(s: str) -> str:
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


# ---------------------------------------------------------------------------
# 5. 锚点定位：把每条批注挂到相关章节标题上（找不到则挂文档末尾）
# ---------------------------------------------------------------------------
ANCHOR_RULES = [
    (('角色判定', '回填确认'), ['画像摘要与角色判定', '角色判定']),
    (('前置判断', '主体判定'), ['义务总览', '规则体系总览', '义务主体与义务内容', '义务主体']),
    (('假设',), ['分法域义务详述', '义务主体与义务内容', '义务主体']),
    (('特定规则', 'B8', 'SB 1000', '标识义务体系化', '落地建议对应关系'),
     ['效力核验记录', '落地建议']),
]


def find_anchor(doc: Document, title: str):
    body = doc.element.body
    paras = body.findall(qn('w:p'))
    # 先在标题里找
    for p in paras:
        txt = ''.join(t.text or '' for t in p.findall('.//' + qn('w:t')))
        for keys, anchors in ANCHOR_RULES:
            if any(k in title for k in keys):
                if any(a in txt for a in anchors):
                    return p
    # 找不到匹配锚点 → 返回 None，由调用方兜底到文档末尾
    return None


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def convert_docx_annotations(docx_path: str, author: str = '合规分析') -> int:
    """把 docx 末尾批注章节转为真实 Word 批注。返回新增批注条数。"""
    doc = Document(docx_path)
    ensure_comment_styles(doc)
    entries = extract_and_strip_annotations(doc)
    if not entries:
        # 没有批注章节，无需处理
        return 0
    comments_part = get_or_create_comments_part(doc)
    all_paras = doc.element.body.findall(qn('w:p'))
    last_para = all_paras[-1] if all_paras else None
    for cid, (title, body) in enumerate(entries):
        anchor_el = find_anchor(doc, title)
        if anchor_el is None:
            anchor_el = last_para
        add_comment(doc, comments_part, _wrap_para(doc, anchor_el), cid, title, body, author)
    doc.save(docx_path)
    return len(entries)


def _wrap_para(doc, p_element):
    # 把底层 lxml 元素包成 python-docx Paragraph 以便操作
    from docx.text.paragraph import Paragraph
    return Paragraph(p_element, doc)


def main():
    ap = argparse.ArgumentParser(description='将报告末尾批注章节转为 Word 真实批注')
    ap.add_argument('docx', help='报告 .docx 路径')
    ap.add_argument('--author', default='合规分析', help='批注作者名')
    args = ap.parse_args()
    n = convert_docx_annotations(args.docx, author=args.author)
    print('已转换 %d 条批注为 Word 批注气泡。' % n)


if __name__ == '__main__':
    main()
