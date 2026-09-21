#!/usr/bin/env python3
"""Render the business-facing self-check table without internal columns."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "assets" / "business-self-check-table.md"
DEFAULT_OUTPUT = ROOT / "assets" / "business-self-check-table-public.md"
DEFAULT_ROUTE = ROOT / "assets" / "questionnaire-route.json"
MODE_KEYS = ("P0",)
ENTRY_KEYS = ("P1", "P2", "P3", "P4")
INTERNAL_KEYS = {"R1", "R2", "R3", "R4"}
PUBLIC_LABELS = {
    "P0": "模式题",
    "P1": "第1步",
    "P2": "第2步",
    "P3": "第3步",
    "P4": "第4步",
    "P5": "开始问题",
    "P6": "资料深度问题",
}
GROUPS = {
    # R is retained as a backwards-compatible command alias, but it renders
    # the public scope entry instead of exposing internal R rows.
    "R": ENTRY_KEYS,
    "MODE": MODE_KEYS,
    "ENTRY": ENTRY_KEYS,
    "START": ("P5",),
    "A": ("A1", "A2", "A3", "A4"),
    "B": ("B1", "B2", "B3", "B4"),
    "C": ("C1", "C2", "C3", "C4", "C5"),
    "D": ("D0", "D1", "D2", "D3", "D4"),
    "E": ("E0", "E1", "E2", "E3", "E4", "E5"),
    "F": ("F0", "F1", "F2", "F3", "F4", "F5"),
    "G": ("G1", "G2", "G3"),
    "H": ("H1", "H2", "H3", "H4"),
    "I": ("I1", "I2", "I3"),
    "J": ("J1", "J2", "J3", "J4"),
    "K": ("K1", "K2"),
    "L": ("L1", "L2"),
}

# Route groups are maintained in questionnaire-route.json.  These aliases let
# callers request a round without exposing the internal R1-R4 registration
# rows; the keys are resolved from the manifest at render time.
ROUTE_GROUP_IDS = {"LT1", "LT2"} | {f"T{number}" for number in range(1, 8)}
P3_OPTIONS = {
    "transparency_only": (
        "单选（根据上一步选择）: 只做透明度；暂不做附属筛查；透明度之外顺便提示个人信息、跨境传输、版权等附属事项；不确定"
    ),
    "system": (
        "单选（根据上一步选择）: 只做已选核心范围，不做附属筛查；一起做与本AI平台有关的个人信息、跨境传输、版权、消费者保护、产品责任和Cookie附属筛查；附属筛查暂不确定；不确定"
    ),
    "model": (
        "单选（根据上一步选择）: 只做已选核心范围，不做附属筛查；一起做与本AI平台有关的个人信息、跨境传输、版权、消费者保护、产品责任和Cookie附属筛查；附属筛查暂不确定；不确定"
    ),
    "system_and_model": (
        "单选（根据上一步选择）: 只做已选核心范围，不做附属筛查；一起做与本AI平台有关的个人信息、跨境传输、版权、消费者保护、产品责任和Cookie附属筛查；附属筛查暂不确定；不确定"
    ),
    "uncertain": (
        "单选（根据上一步选择）: 只做透明度或已选核心范围；暂不做附属筛查；透明度之外顺便提示个人信息、跨境传输、版权等附属事项；一起做与本AI平台有关的附属筛查；不确定"
    ),
}


def normalize_requested_key(value: str) -> str:
    """Accept friendly entry aliases while keeping stable internal keys."""

    normalized = value.strip().upper()
    aliases = {
        "MODE": "P0",
        "ENTRY1": "P0",
        "ENTRY2": "P1",
        "ENTRY3": "P2",
        "ENTRY4": "P3",
        "ENTRY5": "P4",
        "STEP1": "P0",
        "STEP2": "P1",
        "STEP3": "P2",
        "STEP4": "P3",
        "STEP5": "P4",
    }
    return aliases.get(normalized, normalized)


def split_row(line: str) -> list[str]:
    """Split a master row, preserving escaped pipes in business text."""

    content = line.strip().strip("|")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in content:
        if char == "|" and not escaped:
            cells.append("".join(current).replace(r"\|", "|").strip())
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


def normalize_p2_choice(value: str | None) -> str:
    """Map a P2 answer or stable option id to one route branch."""

    text = str(value or "").strip()
    if text in P3_OPTIONS:
        return text
    if "不确定" in text or "尚未确定" in text:
        return "uncertain"
    if "透明度、系统和模型" in text:
        return "system_and_model"
    if "欧盟产品或系统" in text or "系统的使用方式" in text:
        return "system"
    if "模型来源" in text or "模型的使用方式" in text:
        return "model"
    if "只看AI内容透明度" in text or "只看 AI 内容透明度" in text:
        return "transparency_only"
    if not text:
        return "uncertain"
    raise ValueError("无法识别第2步路线；请传入 transparency_only、system、model、system_and_model 或 uncertain")


_PAREN_PAIRS = {"（": "）", "(": ")", "［": "］", "[": "]"}


def _split_semicolons_outside_parentheses(value: str) -> list[str]:
    """Split option text without breaking nested sub-option parentheses."""

    closing = set(_PAREN_PAIRS.values())
    stack: list[str] = []
    parts: list[str] = []
    current: list[str] = []
    for char in value:
        if char in _PAREN_PAIRS:
            stack.append(_PAREN_PAIRS[char])
        elif char in closing and stack and char == stack[-1]:
            stack.pop()
        if char in {"；", ";"} and not stack:
            item = "".join(current).strip()
            if item:
                parts.append(item)
            current = []
            continue
        current.append(char)
    item = "".join(current).strip()
    if item:
        parts.append(item)
    return parts


def _format_nested_option_text(value: str) -> str:
    """Turn semicolon-separated parenthesized sub-options into nested lines."""

    for opening, closing in _PAREN_PAIRS.items():
        start = value.find(opening)
        if start < 0:
            continue
        depth = 0
        end = -1
        for index in range(start, len(value)):
            char = value[index]
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    end = index
                    break
        if end < 0:
            continue
        inner = value[start + 1:end]
        inner_parts = _split_semicolons_outside_parentheses(inner)
        if len(inner_parts) > 1:
            inner_rendered = "<br>  - " + "<br>  - ".join(
                _format_nested_option_text(item) for item in inner_parts
            )
        else:
            inner_rendered = _format_nested_option_text(inner)
        return (
            value[:start]
            + opening
            + inner_rendered
            + closing
            + _format_nested_option_text(value[end + 1:])
        )
    return value


def format_option_list(value: str, key: str) -> str:
    """Render every business choice or requested field as a visible list."""

    match = re.match(r"^((?:单选|多选|分项填写).*?)[：:]\s*(.+)$", value.strip())
    if not match:
        raise ValueError(f"row {key} must use '题型：选项1；选项2' option syntax")
    heading, option_text = match.groups()
    options = _split_semicolons_outside_parentheses(option_text)
    if not options:
        raise ValueError(f"row {key} has no business-facing option or requested field")
    return f"{heading}：<br>- " + "<br>- ".join(
        _format_nested_option_text(item) for item in options
    )


def _load_route_manifest(path: Path = DEFAULT_ROUTE) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取问卷路线文件：{exc}") from exc


def _read_p2_answer(path: Path) -> str:
    """Read a P2 answer from a text, Markdown, or small JSON answer file."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"无法读取第2步答案文件：{exc}") from exc
    if path.suffix.lower() == ".json":
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"第2步答案文件不是有效JSON：{exc}") from exc
        responses = decoded.get("questionnaire_responses", decoded.get("responses", [])) if isinstance(decoded, dict) else decoded
        if isinstance(responses, list):
            for response in responses:
                if isinstance(response, dict) and str(response.get("question_key", "")).upper() == "P2":
                    selected = response.get("selected") or []
                    answer = response.get("answer_text") or response.get("answer") or ""
                    if selected:
                        answer = "；".join(
                            str(item.get("value", item.get("label", ""))) if isinstance(item, dict) else str(item)
                            for item in selected
                        )
                    return str(answer)
    match = re.search(r"(?im)^\s*(?:P2|第\s*2\s*步)\s*[:：-]\s*(.+?)\s*$", text)
    if match:
        return match.group(1).strip()
    raise ValueError("第2步答案文件中没有找到P2或第2步答案")


def route_group_keys(
    group_id: str,
    round_number: int | None = None,
    route_manifest: dict | None = None,
) -> list[str]:
    """Return keys for a route group, optionally selecting one small round."""

    manifest = route_manifest or _load_route_manifest()
    normalized = str(group_id).strip().upper()
    route_groups = (
        list(manifest.get("light_group_templates", []))
        + list(manifest.get("full_group_templates", manifest.get("group_templates", [])))
    )
    groups = {str(group.get("id", "")).upper(): group for group in route_groups}
    group = groups.get(normalized)
    if group is None:
        raise ValueError(f"未知路线题组：{group_id}")
    rounds = group.get("rounds")
    if round_number is None:
        keys = group.get("keys", [])
    else:
        if not isinstance(round_number, int) or round_number < 1:
            raise ValueError("round 必须是正整数")
        if not isinstance(rounds, list) or round_number > len(rounds):
            raise ValueError(f"题组{normalized}没有第{round_number}轮")
        keys = rounds[round_number - 1]
    result = [str(key).upper() for key in keys]
    if len(result) > 8:
        raise ValueError(f"题组{normalized}当前轮有{len(result)}道题，超过每轮8题上限；请拆分路线文件")
    return result


def render(
    source: Path,
    keys: list[str] | None = None,
    max_rows: int | None = None,
    p2_choice: str | None = None,
) -> str:
    lines = source.read_text(encoding="utf-8").splitlines()
    table_lines = [line for line in lines if line.startswith("|")]
    if len(table_lines) < 3:
        raise ValueError("master self-check table is missing its Markdown rows")

    header = split_row(table_lines[0])
    expected = [
        "题号",
        "要确认的事实（白话）",
        "可复制选项（单选/多选/分项填写）",
        "业务答案",
        "完整性状态",
        "触发范围和角色（agent填写）",
        "建议证据",
        "填写注释（给业务部门）",
    ]
    if header != expected:
        raise ValueError("master self-check table columns changed; review the renderer")

    output = [
        "# 业务自测表（业务可见版）",
        "",
        "请只填写“业务答案”列。模式题先选择轻量版或全量版，确认后不会重复询问，除非你主动更改；随后范围入口共4步。可以直接写步骤或题号和答案，也可以粘贴修改后的表格；不知道就填“不确定”，不要猜。“不确定”是有效提交，会进入待核清单但不会被当成未答。每轮只发送当前小组的行。",
        "",
        "| 步骤或题号 | 要确认的事实（白话） | 可复制选项（单选/多选/分项填写） | 业务答案 | 填写注释（给业务部门） |",
        "|---|---|---|---|---|",
    ]
    selected_keys = {normalize_requested_key(key) for key in keys} if keys else None
    if selected_keys and selected_keys & INTERNAL_KEYS:
        raise ValueError("R1至R4是后台登记行，不能发送；请使用--group ENTRY或业务题号")
    rendered_rows = 0
    found_keys: set[str] = set()
    p2_branch = normalize_p2_choice(p2_choice)
    for line in table_lines[2:]:
        cells = split_row(line)
        if len(cells) != 8:
            raise ValueError(f"unexpected self-check row width: {cells[:1]}")
        key = cells[0].strip().upper()
        if key in INTERNAL_KEYS:
            continue
        if selected_keys is not None and key not in selected_keys:
            continue
        rendered_rows += 1
        if max_rows is not None and rendered_rows > max_rows:
            raise ValueError(f"本轮最多渲染{max_rows}道题；请拆分题号或题组")
        if key == "P3":
            cells[2] = P3_OPTIONS[p2_branch]
        if not re.search(r"单选|多选|分项填写", cells[2]):
            raise ValueError(f"row {cells[0]} must declare 单选、多选 or 分项填写")
        cells[2] = format_option_list(cells[2], key)
        if not cells[7]:
            raise ValueError(f"row {cells[0]} is missing its business-facing note")
        display_key = PUBLIC_LABELS.get(key, cells[0])
        kept = (display_key, cells[1], cells[2], cells[3], cells[7])
        if any(char in "*_" for char in "".join(kept)):
            raise ValueError(f"row {cells[0]} contains a forbidden * or _ marker")
        output.append("| " + " | ".join(kept) + " |")
        found_keys.add(key)
    if selected_keys is not None:
        missing = sorted(selected_keys - found_keys)
        if missing:
            raise ValueError("未知题号：" + "、".join(missing))
    if selected_keys is not None and not rendered_rows:
        raise ValueError("没有匹配到要渲染的题号")
    rendered = "\n".join(output) + "\n"
    if any(char in rendered for char in "*_"):
        raise ValueError("business-facing table contains a forbidden * or _ marker")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--group",
        choices=sorted(set(GROUPS) | ROUTE_GROUP_IDS),
        help="只渲染一个题组，例如 --group C；首题使用 --group MODE；入口使用 --group ENTRY；轻量路线用LT1至LT2，全量路线用T1至T7",
    )
    parser.add_argument("--keys", help="只渲染指定题号，逗号分隔；每轮最多8题")
    parser.add_argument("--round", dest="round_number", type=int, help="路线题组的轮次，从1开始；每轮最多8题")
    parser.add_argument(
        "--p2-choice",
        "--p2",
        dest="p2_choice",
        help="按第2步选择渲染P3：transparency_only、system、model、system_and_model 或 uncertain",
    )
    parser.add_argument(
        "--p2-answers",
        "--route-answers",
        dest="p2_answers",
        type=Path,
        help="从已有答案文件读取P2选择，再渲染P3分支",
    )
    parser.add_argument("--route-manifest", type=Path, default=DEFAULT_ROUTE, help="路线JSON文件")
    parser.add_argument("--max-rows", type=int, help="限制本轮题数，默认按组/题号选择时为8")
    args = parser.parse_args()
    if args.group and args.keys:
        parser.error("--group和--keys只能选一个")
    if args.round_number is not None and not args.group:
        parser.error("--round必须和路线题组--group T1至T7一起使用")
    if args.round_number is not None and args.group not in ROUTE_GROUP_IDS:
        parser.error("--round只能用于路线题组LT1至LT2或T1至T7")
    if args.p2_choice and args.p2_answers:
        parser.error("--p2-choice和--p2-answers只能选一个")
    keys: list[str] | None = None
    route_manifest = _load_route_manifest(args.route_manifest)
    if args.group in ROUTE_GROUP_IDS:
        keys = route_group_keys(args.group, args.round_number, route_manifest)
    elif args.group:
        keys = list(GROUPS[args.group])
    elif args.keys:
        keys = [item.strip().upper() for item in args.keys.split(",") if item.strip()]
    if keys and len(keys) > 8:
        parser.error("每轮最多渲染8道题，请拆分题号")
    max_rows = args.max_rows
    if keys and max_rows is None:
        max_rows = 8
    if max_rows is not None and max_rows < 1:
        parser.error("--max-rows必须为正整数")
    p2_choice = args.p2_choice
    if args.p2_answers:
        p2_choice = _read_p2_answer(args.p2_answers)
    content = render(args.source, keys=keys, max_rows=max_rows, p2_choice=p2_choice)
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != content:
            raise SystemExit("business-facing self-check table is stale")
        print(f"OK: {args.output} is current and omits internal assessment columns")
        return 0
    args.output.write_text(content, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
