#!/usr/bin/env python3
"""Validate the formatting contract for a business-visible questionnaire message."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


INTERNAL_KEY_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:P[0-6]|R[1-4]|LT[1-2]|T[1-7])(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
OPTION_PREFIX_RE = re.compile(r"^(?:单选|多选|分项填写)")
HEADER_FIRST_RE = re.compile(r"^(?:题号|步骤或题号)")
HEADER_FACT_RE = re.compile(r"^要确认的事实")
HEADER_OPTIONS_RE = re.compile(r"^可复制选项")
LOCKED_HEADER_RE = re.compile(
    r"^本次共需完成\s*(?P<total>\d+)\s*组问卷；"
    r"当前(?:(?:第\s*(?P<current>\d+)\s*组)|已完成)；"
    r"已完成\s*(?P<completed>\d+)\s*组；"
    r"还剩\s*(?P<remaining>\d+)\s*组问卷。"
)
ROUND_RE = re.compile(r"本轮待答\s*(?P<count>\d+)\s*题")


def split_row(line: str) -> list[str]:
    """Split a Markdown row while preserving escaped vertical bars."""

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


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{1,}:?", cell.strip()) for cell in cells)


def _first_nonempty_line(lines: list[str]) -> tuple[int, str]:
    for line_number, line in enumerate(lines, 1):
        if line.strip():
            return line_number, line.strip()
    return 0, ""


def _validate_locked_progress(
    lines: list[str],
    text: str,
    error: Any,
    locked_route: bool | None,
) -> None:
    """Enforce the public locked-route progress contract when requested.

    Unlocked mode messages (the mode question and the four entry steps) do not
    need a group counter.  Once a caller marks a message as locked, however,
    the progress line must be the first visible line and its counters must be
    complete and arithmetically consistent.
    """

    first_line_number, first_line = _first_nonempty_line(lines)
    marker_re = re.compile(r"(?:本次共需完成|当前第|已完成\s*\d+\s*组|还剩\s*\d+\s*组|本轮待答)")
    inferred_locked = bool(LOCKED_HEADER_RE.match(first_line)) or bool(
        marker_re.search(first_line)
    )
    enforce = inferred_locked if locked_route is None else locked_route
    if not enforce:
        return

    if not first_line_number:
        error("progress", 1, "锁定路线消息必须先显示路线进度")
        return

    header = LOCKED_HEADER_RE.match(first_line)
    if not header:
        later_header_line = next(
            (
                line_number
                for line_number, line in enumerate(lines, 1)
                if line_number != first_line_number and LOCKED_HEADER_RE.match(line.strip())
            ),
            None,
        )
        if later_header_line is not None:
            error(
                "progress_position",
                later_header_line,
                "路线进度必须是消息首个非空行",
            )
        if first_line_number != 1:
            error("progress_position", first_line_number, "路线进度必须是消息首行")
        error(
            "progress",
            first_line_number,
            "路线锁定后首行必须完整写出总组数、当前组、已完成组数和剩余组数",
        )
    else:
        total = int(header.group("total"))
        completed = int(header.group("completed"))
        remaining = int(header.group("remaining"))
        current = header.group("current")
        if total < 1:
            error("progress_consistency", first_line_number, "总组数必须为正数")
        if completed < 0 or remaining < 0:
            error("progress_consistency", first_line_number, "已完成组数和剩余组数不能为负数")
        if total != completed + remaining:
            error(
                "progress_consistency",
                first_line_number,
                "总组数必须等于已完成组数加剩余组数",
            )
        if current is not None and not 1 <= int(current) <= total:
            error("progress_consistency", first_line_number, "当前组必须落在总组数范围内")
        if current is None and remaining != 0:
            error("progress_consistency", first_line_number, "只有剩余组数为0时才能显示当前已完成")

    round_match = ROUND_RE.search(text)
    if not round_match:
        error("progress", first_line_number, "路线锁定后必须写出本轮待答题数")
    elif int(round_match.group("count")) < 0:
        error("progress_consistency", first_line_number, "本轮待答题数不能为负数")


def validate(
    text: str,
    source: str = "<input>",
    locked_route: bool | None = None,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []

    def error(category: str, line: int, message: str, column: int | None = None) -> None:
        item: dict[str, Any] = {"category": category, "line": line, "message": message}
        if column is not None:
            item["column"] = column
        errors.append(item)

    lines = text.splitlines()
    for line_number, line in enumerate(lines, 1):
        for marker in ("*", "_"):
            position = line.find(marker)
            if position >= 0:
                error("forbidden_marker", line_number, f"业务消息不得包含{marker}字符", position + 1)
        match = INTERNAL_KEY_RE.search(line)
        if match:
            error("internal_key", line_number, f"业务消息暴露内部题号或路线键：{match.group(0)}", match.start() + 1)

    _validate_locked_progress(lines, text, error, locked_route)

    tables_checked = 0
    rows_checked = 0
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        header = split_row(lines[index])
        if len(header) < 5:
            index += 1
            continue
        if not (
            HEADER_FIRST_RE.match(header[0])
            and HEADER_FACT_RE.match(header[1])
            and HEADER_OPTIONS_RE.match(header[2])
            and header[3].strip() == "业务答案"
        ):
            index += 1
            continue
        tables_checked += 1
        if header[4].strip() != "填写注释（给业务部门）":
            error("header", index + 1, "业务自测表最后一列必须是“填写注释（给业务部门）”")
        index += 1
        if index < len(lines) and lines[index].lstrip().startswith("|"):
            separator = split_row(lines[index])
            if is_separator(separator):
                index += 1
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            cells = split_row(lines[index])
            if is_separator(cells):
                index += 1
                continue
            if len(cells) != 5:
                error("row_width", index + 1, f"业务自测表数据行应为5列，实际为{len(cells)}列")
                index += 1
                continue
            rows_checked += 1
            option_cell = cells[2].strip()
            if not OPTION_PREFIX_RE.match(option_cell):
                error("option_type", index + 1, "可复制选项列必须以单选、多选或分项填写开头")
            if "<br>- " not in option_cell:
                error("option_list", index + 1, "每个可选项必须单独以“-”开头一行，使用<br>- 格式")
            if ";" in option_cell or "；" in option_cell:
                error("option_separator", index + 1, "可复制选项不得用分号串接，必须逐行列出")
            index += 1

    if tables_checked == 0:
        error("missing_table", 1, "业务消息必须包含业务自测表及完整表头")
    return {
        "status": "ok" if not errors else "invalid",
        "source": source,
        "tables_checked": tables_checked,
        "rows_checked": rows_checked,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", help="Markdown消息文件；使用-从标准输入读取")
    parser.add_argument("--json", action="store_true", dest="json_output", help="输出机器可读JSON")
    parser.add_argument(
        "--locked-route",
        action="store_true",
        help="将消息按已锁定路线检查首行进度；缺少完整进度时失败",
    )
    args = parser.parse_args(argv)
    source = "<stdin>" if args.message == "-" else args.message
    try:
        text = sys.stdin.read() if args.message == "-" else Path(args.message).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"无法读取业务消息：{exc}", file=sys.stderr)
        return 2
    result = validate(text, source, locked_route=True if args.locked_route else None)
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["status"] == "ok":
        print(f"OK: {source} 业务消息格式通过（{result['tables_checked']}个表、{result['rows_checked']}行）")
    else:
        for item in result["errors"]:
            location = f"第{item['line']}行"
            if "column" in item:
                location += f"第{item['column']}列"
            print(f"ERROR [{item['category']}] {location}: {item['message']}", file=sys.stderr)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
