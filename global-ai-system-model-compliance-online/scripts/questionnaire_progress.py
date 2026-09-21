#!/usr/bin/env python3
"""Calculate a stable, business-facing questionnaire route and progress.

The route is deliberately separate from the legal assessment. This module
only answers three operational questions: whether the plain-language
entry steps are complete, which small triggered groups are in the route, and
which questions in the current group still need an answer.

Answers may arrive over several conversation turns. A blank or conflicting
row is never treated as a negative fact, and a later group being answered does
not hide an incomplete earlier group.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ROUTE_PATH = ROOT / "assets" / "questionnaire-route.json"
CHECKER_PATH = ROOT / "scripts" / "check_business_answers.py"


def load_checker() -> Any:
    """Load the shared parser without requiring it to be installed as a package."""

    spec = importlib.util.spec_from_file_location("business_answer_checker", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载业务答案检查器")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def answer_text(row: dict[str, Any]) -> str:
    """Flatten the supported answer representations for display and matching."""

    parts: list[str] = []
    answer = row.get("answer") or row.get("answer_text") or ""
    if answer:
        parts.append(str(answer))
    selected = row.get("selected") or []
    if isinstance(selected, list):
        for item in selected:
            if isinstance(item, dict):
                item = item.get("value", item.get("label", ""))
            if isinstance(item, list):
                parts.extend(str(value) for value in item)
            elif item:
                parts.append(str(item))
    fields = row.get("fields")
    if fields not in (None, "", [], {}):
        parts.append(json.dumps(fields, ensure_ascii=False, sort_keys=True))
    return "；".join(parts).strip()


def is_submitted(row: dict[str, Any]) -> bool:
    """Return whether a row contains any user-supplied value."""

    return bool(answer_text(row))


def contains(text: str, *phrases: str) -> bool:
    return any(phrase in text for phrase in phrases)


def _key(row: dict[str, Any]) -> str:
    return str(row.get("question_key", "")).strip().upper()


def _rows_for_key(rows: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return [row for row in rows if _key(row) == key]


def _last_row(rows: Iterable[dict[str, Any]], key: str) -> dict[str, Any] | None:
    matching = _rows_for_key(rows, key)
    if not matching:
        return None
    # A text answer using “第N行改为” is an explicit replacement. Keep the
    # replacement as the route input while retaining older rows for audit.
    revisions = [row for row in matching if row.get("revision")]
    return (revisions or matching)[-1]


def _unknown_text(text: str) -> bool:
    return bool(re.search(r"不确定|尚未确定|待核实|无法确认|不知道", text))


def _whole_unknown(text: str) -> bool:
    """Recognise a whole-row unknown without treating explanatory notes as one."""

    compact = re.sub(r"[\s：:，,；;。.!！?？]+", "", text)
    return compact in {"不确定", "尚未确定", "待核实", "无法确认", "不知道"} or compact.startswith("不确定先")


def _whole_not_applicable(text: str) -> bool:
    compact = re.sub(r"[\s：:，,；;。.!！?？]+", "", text)
    return compact.startswith("不适用") and len(compact) > len("不适用")


def _audience_hint(text: str) -> bool:
    """A friendly one-sentence P4 answer can include its audience implicitly."""

    return bool(
        re.search(
            r"面向|最终用户|用户是|用户为|客户是|客户为|消费者|客户|员工|求职者|学生|患者|公众|内部人员|内部使用",
            text,
        )
    )


def _p4_missing_fields(checker: Any, row: dict[str, Any]) -> list[str]:
    """Use the shared field parser, with a narrow natural-language P4 shortcut."""

    entries = checker.field_entries("P4", row)
    missing = list(checker.itemized_completeness("P4", entries, row))
    text = answer_text(row)
    # Businesses often shorten the visible label to “产品”.  Treat that
    # narrow alias like “产品一句话” here; the shared final checker can still
    # request the canonical label when it validates a final submission.
    if "产品一句话" in missing and any(
        str(entry.get("display_label", "")).strip() in {"产品", "产品名称"}
        for entry in entries
    ):
        missing.remove("产品一句话")
    # “面向消费者的客服助手” is a valid business fact sentence even when
    # it has no explicit “主要客户或使用者:” label. Do not generalise this
    # shortcut to other itemized questions.
    if "主要客户或使用者" in missing and _audience_hint(text):
        missing.remove("主要客户或使用者")
    return missing


def _row_state(checker: Any, row: dict[str, Any], key: str) -> dict[str, Any]:
    """Classify one row for progress, without making a legal finding."""

    text = answer_text(row)
    submitted = bool(text)
    mode = checker.expected_mode(key, str(row.get("mode", "")))
    conflicts: list[str] = []
    unknown = _unknown_text(text)
    missing_fields: list[str] = []
    if mode == "itemized":
        entries = checker.field_entries(key, row)
        conflicts.extend(checker.itemized_conflicts(key, entries))
        unknown_fields = checker.itemized_unknown_fields(key, entries)
        if key == "P4":
            unknown_fields = [
                field for field in unknown_fields
                if str(field).strip() not in {"产品", "产品名称"}
            ]
        if unknown_fields:
            conflicts.append("未知分项字段：" + "、".join(unknown_fields))
        if key == "P4":
            missing_fields = _p4_missing_fields(checker, row)
        else:
            missing_fields = list(checker.itemized_completeness(key, entries, row))
        whole_pending = _whole_unknown(text) or _whole_not_applicable(text)
        # An explicit unknown/N/A-with-reason answer is a submitted fact for a
        # detailed row, but remains pending for assessment. It is never sent
        # again merely because the fact still needs internal verification.
        complete = submitted and not conflicts and (
            not missing_fields or whole_pending
        )
        if submitted and not entries and not whole_pending and key != "P4":
            conflicts.append("未识别到明确分项")
            complete = False
    else:
        selected = row.get("selected") or []
        answer = str(row.get("answer", "") or "")
        if selected:
            selections = checker._selected_values(selected, key, mode)
        elif mode == "single":
            selections = checker.single_parts(answer, key)
        else:
            selections = checker.multi_parts(answer, key)
        result = checker.classify(answer, selections, key)
        conflicts.extend(result.get("conflicts", []))
        if mode == "single" and len(selections) > 1:
            conflicts.append("单选题出现多个选项")
        if submitted and not selections and mode in {"single", "multi"}:
            conflicts.append("未识别到明确选项")
        complete = submitted and not conflicts
    explicit_status = str(row.get("conflict_status", "") or "").lower()
    if explicit_status in {"conflict", "conflicting", "invalid"}:
        conflicts.append("答案标记为冲突，需先更正")
    elif explicit_status in {"pending", "uncertain"}:
        unknown = True
    if conflicts:
        complete = False
    return {
        "submitted": submitted,
        "complete": complete,
        "unknown": unknown,
        "conflicts": list(dict.fromkeys(conflicts)),
        "missing_fields": missing_fields,
        "text": text,
    }


def _key_state(checker: Any, rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    # An explicit “第N行改为” row replaces the older answer for progress and
    # conflict checks.  The raw rows are still retained by the caller for
    # audit history; a blank revision intentionally clears the prior answer.
    effective_for_key = getattr(checker, "effective_rows_for_key", None)
    matching = (
        effective_for_key(rows, key)
        if callable(effective_for_key)
        else _rows_for_key(rows, key)
    )
    active = [row for row in matching if is_submitted(row)]
    if not active:
        return {
            "submitted": False,
            "complete": False,
            "unknown": False,
            "conflicts": [],
            "missing_fields": [],
            "row_count": 0,
        }
    # Repeatable questions (one row per model, flow, or content path) are
    # complete only when every supplied row is valid. At least one row is
    # required; an empty repeated question remains missing.
    row_states = [_row_state(checker, row, key) for row in active]
    conflicts = [item for state in row_states for item in state["conflicts"]]
    unknown = any(state["unknown"] for state in row_states)
    missing_fields = list(dict.fromkeys(
        item for state in row_states for item in state["missing_fields"]
    ))
    repeatable = key in getattr(checker, "REPEATABLE_QUESTION_KEYS", set())
    if not repeatable and len(active) > 1:
        # The shared checker allows an explicit revision row. Otherwise a
        # duplicate non-repeatable answer is unresolved, not “last one wins”.
        effective = [row for row in active if not row.get("revision")]
        if len(effective) > 1:
            conflicts.append(f"题号{key}重复出现；请保留一版并写明更正记录")
    complete = all(state["complete"] for state in row_states) and not conflicts
    return {
        "submitted": True,
        "complete": complete,
        "unknown": unknown,
        "conflicts": list(dict.fromkeys(conflicts)),
        "missing_fields": missing_fields,
        "row_count": len(active),
    }


def _canonical_p2(text: str) -> str:
    if _unknown_text(text):
        return "uncertain"
    if "透明度、系统和模型" in text or (
        ("系统" in text or "产品" in text) and "模型" in text
    ):
        return "system_and_model"
    if "欧盟产品或系统" in text or "系统的使用方式" in text:
        return "system"
    if "模型来源" in text or "模型的使用方式" in text:
        return "model"
    if "只看AI内容透明度" in text or "只看 AI 内容透明度" in text:
        return "transparency_only"
    return "unknown"


def _canonical_p3(text: str) -> str:
    if _unknown_text(text):
        return "uncertain"
    if contains(text, "不做附属筛查", "暂不做附属筛查", "不评估附属筛查", "不看附属筛查"):
        return "transparency_only"
    if "只做已选核心范围" in text:
        return "transparency_only"
    if contains(text, "顺便", "一起做", "附属筛查"):
        return "ancillary"
    if "只做透明度" in text:
        return "transparency_only"
    return "unknown"


def _canonical_mode(text: str) -> str:
    """Return the selected assessment mode; uncertainty defaults to light."""

    if "全量版" in text or text.strip().lower() == "full":
        return "full"
    if "轻量版" in text or _unknown_text(text) or text.strip().lower() == "light":
        return "light"
    return "unknown"


def evaluation_mode(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> tuple[str, str]:
    """Resolve mode, retaining old answer files that predate P0."""

    p0 = answer_text(_last_row(rows, str(manifest.get("mode_step", "P0"))) or {})
    canonical = _canonical_mode(p0)
    if canonical != "unknown":
        return canonical, "explicit"
    if any(_last_row(rows, key) is not None for key in ("P1", "P2", "P3", "P4")):
        return str(manifest.get("legacy_missing_mode", "full")), "legacy_default"
    return "unknown", "missing"


def technical_detail_enabled(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> bool:
    """Open advanced detail only after an explicit affirmative P6 answer."""

    gate = str(manifest.get("question_policy", {}).get("technical_detail_gate_key", "P6"))
    text = answer_text(_last_row(rows, gate) or {})
    return bool(text) and (
        text.strip() == "可以"
        or contains(text, "可以，我能查看", "可以核对", "能查看或协调核对")
    )


def _route_choice_conflicts(rows: list[dict[str, Any]]) -> list[str]:
    """Catch a pasted full-table P3 branch that widens P2 implicitly."""

    p2 = answer_text(_last_row(rows, "P2") or {})
    p3 = answer_text(_last_row(rows, "P3") or {})
    if not p2 or not p3:
        return []
    p2_choice = _canonical_p2(p2)
    stale_branch = contains(
        p3,
        "还看欧盟产品或系统或模型使用",
        "欧盟产品或系统或模型使用",
    )
    if stale_branch and p2_choice not in {"system_and_model", "uncertain"}:
        return [
            "第3步与第2步不一致：附属事项问题不能替代第2步的欧盟系统或模型选择；请先更正路线"
        ]
    return []


def route_flags(rows: list[dict[str, Any]]) -> tuple[bool, bool, bool]:
    """Return ``(system, model, ancillary)`` for compatibility with callers."""

    p2 = answer_text(_last_row(rows, "P2") or {})
    p3 = answer_text(_last_row(rows, "P3") or {})
    p2_choice = _canonical_p2(p2)
    include_system = p2_choice in {"system", "system_and_model", "uncertain"}
    include_model = p2_choice in {"model", "system_and_model", "uncertain"}
    include_ancillary = _canonical_p3(p3) in {"ancillary", "uncertain"}
    return include_system, include_model, include_ancillary


def route_selection(rows: list[dict[str, Any]], manifest: dict[str, Any] | None = None) -> dict[str, str]:
    """Expose stable option IDs for the route lock and audit trail."""

    p1 = answer_text(_last_row(rows, "P1") or {})
    p2 = answer_text(_last_row(rows, "P2") or {})
    p3 = answer_text(_last_row(rows, "P3") or {})
    mode, mode_source = evaluation_mode(rows, manifest or {})
    return {
        "assessment_mode": mode,
        "mode_source": mode_source,
        "regions": p1 or "unknown",
        "consultation_focus": _canonical_p2(p2),
        "ancillary_scope": _canonical_p3(p3),
    }


def selected_groups(
    manifest: dict[str, Any], flags: tuple[bool, bool, bool], rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    include_system, include_model, include_ancillary = flags
    enabled = {
        "always": True,
        "include_system": include_system,
        "include_model": include_model,
        "include_ancillary": include_ancillary,
    }
    mode, _source = evaluation_mode(rows, manifest)
    templates = (
        manifest.get("light_group_templates", [])
        if mode == "light"
        else manifest.get("full_group_templates", manifest.get("group_templates", []))
    )
    advanced = technical_detail_enabled(rows, manifest)
    technical_keys = {
        str(key).upper() for key in manifest.get("technical_detail_keys", [])
    }
    selected: list[dict[str, Any]] = []
    for original in templates:
        if not enabled.get(original.get("condition", ""), False):
            continue
        key_conditions = {
            str(key).upper(): condition
            for key, condition in original.get("key_conditions", {}).items()
        }

        def active(key: Any) -> bool:
            normalized = str(key).upper()
            if mode == "full" and normalized in technical_keys and not advanced:
                return False
            condition = key_conditions.get(normalized)
            return condition is None or enabled.get(condition, False)

        group = dict(original)
        group["keys"] = [str(key).upper() for key in original.get("keys", []) if active(key)]
        group["rounds"] = [
            [str(key).upper() for key in current if active(key)]
            for current in original.get("rounds", [])
        ]
        group["rounds"] = [current for current in group["rounds"] if current]
        if group["keys"]:
            selected.append(group)
    return selected


def public_entry_keys(manifest: dict[str, Any]) -> list[str]:
    """Return the four business-facing scope-entry keys.

    ``entry_steps`` intentionally retains P0 for route/signature compatibility
    with older answer files.  P0 is the separate mode question, so progress
    shown to a business user must count only P1-P4 as the scope entry.
    """

    mode_key = str(manifest.get("mode_step", "P0")).upper()
    configured = manifest.get("public_entry_steps")
    if isinstance(configured, list) and configured:
        candidates = [str(key).upper() for key in configured]
    else:
        candidates = [
            str(key).upper()
            for key in manifest.get("entry_steps", [])
            if str(key).upper() != mode_key
        ]
    entry_keys = {str(key).upper() for key in manifest.get("entry_steps", [])}
    # Ignore accidental mode-key duplication or keys outside the internal
    # entry contract; this keeps an old/minimal manifest usable.
    return list(dict.fromkeys(
        key for key in candidates if key in entry_keys and key != mode_key
    ))


def validate_public_entry_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate the public mode/scope split when a manifest declares it."""

    entry_keys = [str(key).upper() for key in manifest.get("entry_steps", [])]
    mode_key = str(manifest.get("mode_step", "P0")).upper()
    expected = [key for key in entry_keys if key != mode_key]
    configured = manifest.get("public_entry_steps")
    if configured is not None:
        actual = [str(key).upper() for key in configured]
        if actual != expected:
            raise ValueError(
                "public_entry_steps必须是去除独立模式题后的P1至P4范围入口"
            )
        rounds = manifest.get("public_entry_rounds")
        if rounds is not None:
            flattened = [
                str(key).upper()
                for current in rounds
                if isinstance(current, list)
                for key in current
            ]
            if flattened != actual:
                raise ValueError("public_entry_rounds必须逐题覆盖P1至P4且不得重复")
    return {
        "valid": True,
        "mode_step": mode_key,
        "mode_question_count": 1,
        "public_entry_steps": public_entry_keys(manifest),
        "public_entry_question_count": len(public_entry_keys(manifest)),
    }


def _entry_status(
    checker: Any, rows: list[dict[str, Any]], manifest: dict[str, Any]
) -> dict[str, Any]:
    entry_keys = list(manifest["entry_steps"])
    mode_key = str(manifest.get("mode_step", "P0")).upper()
    public_keys = public_entry_keys(manifest)
    states = {key: _key_state(checker, rows, key) for key in entry_keys}
    mode, mode_source = evaluation_mode(rows, manifest)
    if mode_source == "legacy_default" and mode_key in states and not states[mode_key]["submitted"]:
        states[mode_key] = {
            "submitted": True,
            "complete": True,
            "unknown": False,
            "conflicts": [],
            "missing_fields": [],
            "row_count": 0,
            "legacy_default": True,
        }
    submitted = [key for key in entry_keys if states[key]["submitted"]]
    complete = [key for key in entry_keys if states[key]["complete"]]
    # "complete" is the route-readiness state: an explicit "不确定" answer
    # is syntactically complete and keeps the route moving, but it is not a
    # confirmed business fact.  Keep that distinction visible to the user.
    confirmed = [
        key
        for key in entry_keys
        if states[key]["complete"]
        and not states[key]["unknown"]
        and not states[key]["conflicts"]
        and not states[key]["missing_fields"]
    ]
    pending_verification = [
        key
        for key in entry_keys
        if states[key]["complete"] and states[key]["unknown"]
    ]
    needs_correction = [
        key
        for key in entry_keys
        if states[key]["submitted"] and not states[key]["complete"]
    ]
    missing_steps = [key for key in entry_keys if not states[key]["submitted"]]
    missing_fields: dict[str, list[str]] = {
        key: states[key]["missing_fields"]
        for key in entry_keys
        if states[key]["submitted"] and states[key]["missing_fields"]
    }
    conflicts = [
        f"{key}：{message}"
        for key in entry_keys
        for message in states[key]["conflicts"]
    ]
    route_conflicts = getattr(checker, "entry_route_conflicts", lambda _rows: [])(rows)
    # The shared checker owns the canonical route message.  Keep the local
    # check only as a compatibility fallback for injected/minimal checkers, so
    # one stale branch does not produce two near-duplicate prompts.
    conflicts.extend(route_conflicts or _route_choice_conflicts(rows))
    step_statuses = []
    for index, key in enumerate(entry_keys, 1):
        state = states[key]
        if not state["submitted"]:
            status = "not_received"
        elif states[key]["conflicts"]:
            status = "conflict"
        elif key in confirmed:
            status = "complete"
        elif key in pending_verification:
            status = "submitted_uncertain"
        elif state["missing_fields"]:
            status = "received_needs_completion"
        else:
            status = "conflict"
        state["status"] = status
        state["step_number"] = index
        step_statuses.append(
            {
                "step_number": index,
                "question_key": key,
                "status": status,
                "submitted": state["submitted"],
                "complete": state["complete"],
                "confirmed": key in confirmed,
                "unknown": state["unknown"],
                "missing_fields": list(state["missing_fields"]),
                "conflicts": list(state["conflicts"]),
                "legacy_default": bool(state.get("legacy_default")),
            }
        )
    unresolved = [key for key in entry_keys if key in needs_correction or key in missing_steps]
    if mode_key in unresolved:
        current_pending = [mode_key]
    else:
        current_pending = [key for key in entry_keys if key in unresolved and key != mode_key]

    def _summary(keys: list[str]) -> dict[str, Any]:
        selected = [states[key] for key in keys if key in states]
        submitted_keys = [key for key in keys if states[key]["submitted"]]
        complete_keys = [key for key in keys if states[key]["complete"]]
        confirmed_keys = [
            key
            for key in keys
            if states[key]["complete"]
            and not states[key]["unknown"]
            and not states[key]["conflicts"]
            and not states[key]["missing_fields"]
        ]
        pending_keys = [
            key for key in keys if states[key]["complete"] and states[key]["unknown"]
        ]
        correction_keys = [
            key for key in keys if states[key]["submitted"] and not states[key]["complete"]
        ]
        missing_keys = [key for key in keys if not states[key]["submitted"]]
        pending_fields = {
            key: list(states[key]["missing_fields"])
            for key in keys
            if states[key]["submitted"] and states[key]["missing_fields"]
        }
        unresolved_keys = list(dict.fromkeys(correction_keys + missing_keys))
        return {
            "keys": list(keys),
            "submitted_keys": submitted_keys,
            "complete_keys": complete_keys,
            "confirmed_keys": confirmed_keys,
            "pending_verification_keys": pending_keys,
            "correction_keys": correction_keys,
            "missing_keys": missing_keys,
            "unresolved_keys": unresolved_keys,
            "submitted": len(submitted_keys),
            "complete": len(complete_keys),
            "confirmed": len(confirmed_keys),
            "pending_verification": len(pending_keys),
            "received_needs_completion": len(correction_keys),
            "not_received": len(missing_keys),
            "total": len(keys),
            "remaining": max(len(keys) - len(complete_keys), 0),
            "submission_remaining": max(len(keys) - len(complete_keys), 0),
            "missing_fields": pending_fields,
            "conflicts": list(dict.fromkeys(
                f"{key}：{message}"
                for key in keys
                for message in states[key]["conflicts"]
            )),
            "state_count": len(selected),
        }

    public_summary = _summary(public_keys)
    mode_summary = _summary([mode_key]) if mode_key in states else _summary([])
    public_current_pending = []
    # Do not present the scope-entry counter as active until the separate mode
    # question has been answered (or legacy mode was auto-derived).
    if states.get(mode_key, {}).get("complete"):
        public_current_pending = [
            key for key in public_keys if key in unresolved
        ]
    public_step_statuses = []
    status_by_key = {item["question_key"]: item for item in step_statuses}
    for index, key in enumerate(public_keys, 1):
        item = dict(status_by_key.get(key, {"question_key": key}))
        item["step_number"] = index
        public_step_statuses.append(item)
    mode_step_status = status_by_key.get(mode_key)
    return {
        "states": states,
        "entry_submitted": len(submitted),
        "entry_complete": len(complete),
        "entry_confirmed": len(confirmed),
        "entry_received_needs_completion": len(needs_correction),
        "entry_pending_verification": len(pending_verification),
        "pending_verification_entry_keys": pending_verification,
        "entry_not_received": len(missing_steps),
        "entry_total": len(entry_keys),
        "assessment_mode": mode,
        "mode_source": mode_source,
        "missing_entry": missing_steps,
        "missing_entry_fields": missing_fields,
        "entry_conflicts": list(dict.fromkeys(conflicts)),
        "entry_step_statuses": step_statuses,
        "entry_current_step": current_pending[0] if current_pending else None,
        "entry_current_step_number": (
            entry_keys.index(current_pending[0]) + 1 if current_pending else None
        ),
        "entry_round_question_keys": current_pending,
        # Public progress deliberately separates P0 from the four scope
        # questions.  Keep the legacy entry_* fields above unchanged for
        # callers that use them to validate route signatures.
        "mode_step": mode_key,
        "mode_total": mode_summary["total"],
        "mode_submitted": mode_summary["submitted"],
        "mode_complete": mode_summary["complete"],
        "mode_confirmed": mode_summary["confirmed"],
        "mode_pending_verification": mode_summary["pending_verification"],
        "mode_not_received": mode_summary["not_received"],
        "mode_remaining_steps": mode_summary["remaining"],
        "mode_status": (
            mode_step_status.get("status") if mode_step_status else "not_received"
        ),
        "mode_step_status": mode_step_status,
        "public_entry_steps": public_keys,
        "public_entry_total": public_summary["total"],
        "public_entry_submitted": public_summary["submitted"],
        "public_entry_complete": public_summary["complete"],
        "public_entry_confirmed": public_summary["confirmed"],
        "public_entry_pending_verification": public_summary["pending_verification"],
        "public_entry_received_needs_completion": public_summary["received_needs_completion"],
        "public_entry_not_received": public_summary["not_received"],
        "public_entry_remaining_steps": public_summary["remaining"],
        "public_entry_submission_remaining": public_summary["submission_remaining"],
        "public_entry_remaining_fields": sum(
            len(fields) for fields in public_summary["missing_fields"].values()
        ),
        "public_entry_missing": public_summary["missing_keys"],
        "public_entry_missing_fields": public_summary["missing_fields"],
        "public_entry_conflicts": public_summary["conflicts"],
        "public_entry_step_statuses": public_step_statuses,
        "public_entry_current_step": (
            public_current_pending[0] if public_current_pending else None
        ),
        "public_entry_current_step_number": (
            public_keys.index(public_current_pending[0]) + 1
            if public_current_pending
            else None
        ),
        "public_entry_round_question_keys": public_current_pending,
        "public_entry_progress": public_summary,
        "mode_progress": mode_summary,
    }


def _state_status(state: dict[str, Any]) -> str:
    """Map an internal row state to a stable, user-facing status label."""

    if not state.get("submitted"):
        return "not_received"
    if (
        state.get("complete")
        and not state.get("unknown")
        and not state.get("conflicts")
        and not state.get("missing_fields")
    ):
        return "complete"
    return "received_needs_completion"


def _backend_registration_status(
    checker: Any,
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, Any]:
    """Build the hidden R1-R4 registration gate without exposing its keys.

    R1-R4 are registration records, not extra business questions.  The agent
    derives them from the four public entry answers unless an explicit,
    structured internal record is supplied.  This gives the route a real
    backend gate while keeping the business conversation at four plain
    entry steps.
    """

    keys = [str(key).upper() for key in manifest.get("backend_registration_keys", [])]
    if not keys:
        return {
            "registration_total": 0,
            "registration_collected": 0,
            "registration_confirmed": 0,
            "registration_received_needs_completion": 0,
            "registration_not_received": 0,
            "registration_remaining": 0,
            "registration_ready": True,
            "registration_conflicts": [],
            "records": [],
            "signature_values": {},
        }

    entry_states = entry.get("states", {})
    dependency_map = {
        "R1": list(manifest.get("entry_steps", [])),
        "R2": ["P1", "P4"],
        "R3": ["P2"],
        "R4": ["P3"],
    }
    records: list[dict[str, Any]] = []
    conflicts: list[str] = []
    # Route signatures represent scope, not whether an evidence field was
    # later filled in.  This keeps a confirmed route stable while facts move
    # from reported to verified.
    selection = route_selection(rows)
    canonical_entry = _canonical_entry_for_signature(rows, manifest)
    signature_values: dict[str, str] = {
        "R1": "three_layers_registered",
        "R2": canonical_entry.get("P1", selection.get("regions", "unknown")),
        "R3": selection.get("consultation_focus", "unknown"),
        "R4": selection.get("ancillary_scope", "unknown"),
    }
    for key in keys:
        explicit = _key_state(checker, rows, key)
        has_explicit = explicit.get("submitted", False)
        deps = dependency_map.get(key, list(manifest.get("entry_steps", [])))
        if has_explicit:
            state = explicit
            source = "internal_submission"
            reason = "使用已提交的后台登记记录。"
            collected = bool(state.get("complete")) and not bool(state.get("conflicts"))
            status = _state_status(state) if collected else "received_needs_completion"
            if state.get("conflicts"):
                conflicts.extend(f"{key}：{item}" for item in state["conflicts"])
        else:
            dep_states = [entry_states.get(dep, {}) for dep in deps]
            ready = bool(dep_states) and all(state.get("complete", False) for state in dep_states)
            any_submitted = any(state.get("submitted", False) for state in dep_states)
            any_pending = any(state.get("unknown", False) for state in dep_states)
            collected = ready
            status = (
                "received_needs_completion"
                if ready and any_pending
                else "complete"
                if ready
                else "received_needs_completion"
                if any_submitted
                else "not_received"
            )
            source = "auto_registration"
            reason = (
                "由公开入口答案自动建立；不确定事实保留待核状态。"
                if ready
                else "等待对应公开入口步骤完整收齐。"
            )
        records.append(
            {
                "registration_key": key,
                "status": status,
                "collected": collected,
                "confirmed": status == "complete",
                "source": source,
                "depends_on": deps,
                "reason": reason,
            }
        )

    collected_count = sum(1 for record in records if record["collected"])
    confirmed_count = sum(1 for record in records if record["confirmed"])
    pending_count = sum(
        1 for record in records if record["status"] == "received_needs_completion"
    )
    missing_count = sum(1 for record in records if record["status"] == "not_received")
    return {
        "registration_total": len(records),
        "registration_collected": collected_count,
        "registration_confirmed": confirmed_count,
        "registration_received_needs_completion": pending_count,
        "registration_not_received": missing_count,
        "registration_remaining": len(records) - collected_count,
        "registration_ready": collected_count == len(records) and not conflicts,
        "registration_conflicts": list(dict.fromkeys(conflicts)),
        "records": records,
        "signature_values": signature_values,
    }


def _canonical_entry_for_signature(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    region_order = {"中国大陆": 0, "美国": 1, "欧盟": 2, "尚未确定": 3}
    for key in manifest["entry_steps"]:
        text = answer_text(_last_row(rows, key) or {})
        if key == str(manifest.get("mode_step", "P0")):
            result[key] = evaluation_mode(rows, manifest)[0]
        elif key == "P1":
            # P1 is a multi-select. Canonicalise its option order so a later
            # reply such as “美国；欧盟” does not look like a route change
            # when the earlier reply said “欧盟；美国”.
            regions = [
                region for region in region_order
                if region in text
            ]
            result[key] = "；".join(sorted(set(regions), key=region_order.get)) or text
        elif key == "P2":
            result[key] = _canonical_p2(text)
        elif key == "P3":
            result[key] = _canonical_p3(text)
        else:
            result[key] = re.sub(r"\s+", " ", text).strip()
    return result


def _route_signature(
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    groups: list[dict[str, Any]],
    backend_registration: dict[str, Any] | None = None,
) -> str:
    mode, _mode_source = evaluation_mode(rows, manifest)
    source_templates = (
        manifest.get("light_group_templates", [])
        if mode == "light"
        else manifest.get("full_group_templates", manifest.get("group_templates", []))
    )
    template_by_id = {
        str(group.get("id", "")): group for group in source_templates
    }
    payload = {
        "questionnaire_version": manifest.get("version", "unknown"),
        "assessment_mode": mode,
        "entry": _canonical_entry_for_signature(rows, manifest),
        "groups": [group["id"] for group in groups],
        "question_slots": {
            group["id"]: [
                str(key).upper()
                for key in template_by_id.get(group["id"], group).get("keys", [])
            ]
            for group in groups
        },
    }
    if backend_registration is not None:
        # Certainty changes should update the audit record, but should not
        # silently change the selected questionnaire scope.  Include only the
        # scope-relevant registration values in the route signature.
        payload["backend_registration_scope"] = backend_registration.get(
            "signature_values", {}
        )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _group_rounds(group: dict[str, Any]) -> list[list[str]]:
    rounds = group.get("rounds")
    if isinstance(rounds, list) and rounds:
        return [[str(key).upper() for key in current if key] for current in rounds]
    keys = [str(key).upper() for key in group.get("keys", [])]
    return [keys]


def _group_detail(
    checker: Any,
    rows: list[dict[str, Any]],
    group: dict[str, Any],
    group_number: int,
    activate: bool = False,
) -> dict[str, Any]:
    keys = [str(key).upper() for key in group.get("keys", [])]
    states = {key: _key_state(checker, rows, key) for key in keys}
    rounds = _group_rounds(group)
    round_details: list[dict[str, Any]] = []
    next_keys: list[str] = []
    next_round = None
    prior_rounds_complete = True
    assigned_keys: list[str] = []
    unassigned_keys: list[str] = []
    prior_supplied = False
    for round_number, round_keys in enumerate(rounds, 1):
        supplied = any(states[key]["submitted"] for key in round_keys)
        # The first round of the current group is sent when the preceding
        # groups are complete. A later round is sent once its preceding round
        # is complete, or as soon as a saved answer proves it was already
        # sent. Future rounds remain unassigned rather than appearing as
        # unanswered questions.
        assigned = supplied or (prior_rounds_complete and (activate or prior_supplied))
        missing = [key for key in round_keys if assigned and not states[key]["complete"]]
        conflicts = [key for key in round_keys if states[key]["conflicts"]]
        if assigned:
            assigned_keys.extend(round_keys)
        else:
            unassigned_keys.extend(round_keys)
        if assigned and missing and next_round is None:
            next_round = round_number
            next_keys = missing
        round_details.append(
            {
                "round_number": round_number,
                "question_keys": round_keys,
                "assigned": assigned,
                "missing_keys": missing,
                "unassigned_keys": [] if assigned else round_keys,
                "conflicting_keys": conflicts if assigned else [],
                "complete": assigned and not missing,
            }
        )
        prior_rounds_complete = assigned and not missing
        prior_supplied = prior_supplied or supplied
    submitted = [key for key in keys if states[key]["submitted"]]
    conflicting = [key for key in keys if states[key]["conflicts"]]
    pending_unknown = [key for key in keys if states[key]["unknown"]]
    assigned_set = set(assigned_keys)
    missing_fields = {
        key: states[key]["missing_fields"]
        for key in keys
        if key in assigned_set and states[key]["missing_fields"]
    }
    complete = all(states[key]["complete"] for key in keys)
    assigned_missing = [
        key for key in assigned_keys if not states[key]["complete"]
    ]
    return {
        "group_number": group_number,
        "id": group["id"],
        "title": group["title"],
        "total_questions": len(keys),
        "submitted_questions": len(submitted),
        "missing_keys": assigned_missing,
        "all_missing_keys": [key for key in keys if not states[key]["complete"]],
        "assigned_keys": assigned_keys,
        "unassigned_keys": unassigned_keys,
        "conflicting_keys": [key for key in conflicting if key in assigned_set],
        "pending_unknown_keys": [key for key in pending_unknown if key in assigned_set],
        "missing_fields": missing_fields,
        "next_round": next_round,
        "next_question_keys": next_keys,
        "rounds": round_details,
        "complete": complete,
    }


def _omitted_themes(
    manifest: dict[str, Any],
    flags: tuple[bool, bool, bool],
    mode: str = "full",
) -> dict[str, dict[str, Any]]:
    include_system, include_model, include_ancillary = flags
    reasons = manifest.get("omitted_theme_reasons", {})
    if mode == "light":
        # LT2 always asks one short fact question for each second/third-layer
        # theme.  Keep the result honest by distinguishing that triage from
        # the optional full-detail groups selected by P2/P3.
        return {
            "system": {
                "included": True,
                "detail_included": include_system,
                "triage_key": "D0",
                "reason": (
                    "轻量版已通过D0完成系统线索初筛；"
                    "全量系统详细题已纳入。"
                    if include_system
                    else "轻量版已通过D0完成系统线索初筛；全量系统详细题本次未选择。"
                ),
            },
            "model": {
                "included": True,
                "detail_included": include_model,
                "triage_key": "E0",
                "reason": (
                    "轻量版已通过E0完成模型线索初筛；"
                    "全量模型详细题已纳入。"
                    if include_model
                    else "轻量版已通过E0完成模型线索初筛；全量模型详细题本次未选择。"
                ),
            },
            "ancillary": {
                "included": True,
                "detail_included": include_ancillary,
                "triage_key": "F0",
                "reason": (
                    "轻量版已通过F0完成AI平台附属线索初筛；"
                    "全量附属详细题已纳入。"
                    if include_ancillary
                    else "轻量版已通过F0完成AI平台附属线索初筛；全量附属详细题本次未选择。"
                ),
            },
        }
    return {
        "system": {
            "included": include_system,
            "reason": "已触发并纳入本次路线。" if include_system else reasons.get("system", "未触发"),
        },
        "model": {
            "included": include_model,
            "reason": "已触发并纳入本次路线。" if include_model else reasons.get("model", "未触发"),
        },
        "ancillary": {
            "included": include_ancillary,
            "reason": "已触发并纳入本次路线。" if include_ancillary else reasons.get("ancillary", "未触发"),
        },
    }


def validate_light_route_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate the fixed lightweight route before calculating progress.

    The lightweight questionnaire is intentionally a stable ten-slot contract:
    two groups, five business-facing questions in each group, and no
    scope-dependent key filtering.  Keeping this check next to the route
    calculator prevents a future manifest edit from silently reintroducing the
    old three-to-six-question LT2 branch.
    """

    groups = manifest.get("light_group_templates")
    if not isinstance(groups, list) or len(groups) != 2:
        raise ValueError("轻量版路线必须恰好包含LT1和LT2两组")
    ids = [str(group.get("id", "")).upper() for group in groups]
    if ids != ["LT1", "LT2"]:
        raise ValueError("轻量版路线题组必须按LT1、LT2顺序定义")
    policy = manifest.get("question_policy", {})
    per_group = int(policy.get("light_mode_questions_per_group", 5))
    expected_total = int(policy.get("light_mode_total_question_slots", per_group * len(groups)))
    if per_group != 5 or expected_total != 10:
        raise ValueError("轻量版固定题量配置必须是每组5题、总计10题")
    seen: list[str] = []
    details: list[dict[str, Any]] = []
    for group in groups:
        keys = [str(key).upper() for key in group.get("keys", [])]
        rounds = group.get("rounds")
        if len(keys) != per_group:
            raise ValueError(f"轻量版{group.get('id', '')}必须恰好有{per_group}题")
        if len(set(keys)) != len(keys):
            raise ValueError(f"轻量版{group.get('id', '')}含重复题号")
        if group.get("key_conditions"):
            raise ValueError(f"轻量版{group.get('id', '')}不得按范围条件改变题数")
        if not isinstance(rounds, list) or not rounds:
            raise ValueError(f"轻量版{group.get('id', '')}必须定义轮次")
        flattened = [str(key).upper() for current in rounds for key in current]
        if flattened != keys:
            raise ValueError(f"轻量版{group.get('id', '')}的rounds必须逐题且只出现一次")
        seen.extend(keys)
        details.append({"id": str(group.get("id", "")), "question_count": len(keys), "keys": keys})
    if len(seen) != expected_total or len(set(seen)) != expected_total:
        raise ValueError("轻量版两组题号必须合计10个且不得重复")
    return {
        "valid": True,
        "groups": details,
        "questions_per_group": per_group,
        "total_question_slots": expected_total,
    }


def _possible_group_counts(manifest: dict[str, Any]) -> tuple[int, int]:
    """Return the minimum and maximum route sizes before entry is locked.

    The four entry answers determine whether the optional system, model and
    ancillary groups are assigned.  Showing the range while the entry is
    incomplete is more honest than displaying a guessed total; once the entry
    is complete ``calculate`` returns the exact locked total.
    """

    light = manifest.get("light_group_templates", [])
    full = manifest.get("full_group_templates", manifest.get("group_templates", []))
    light_count = len(light) if light else 0
    always = sum(1 for group in full if group.get("condition") == "always")
    optional = sum(1 for group in full if group.get("condition") != "always")
    candidates = [value for value in (light_count, always, always + optional) if value]
    return (min(candidates), max(candidates)) if candidates else (0, 0)


def _entry_progress_fields(entry: dict[str, Any]) -> dict[str, Any]:
    """Expose explicit step/field counters for a business-facing progress UI."""

    total = int(entry.get("entry_total", 0))
    complete = int(entry.get("entry_complete", 0))
    confirmed = int(entry.get("entry_confirmed", complete))
    submitted = int(entry.get("entry_submitted", 0))
    corrections = int(
        entry.get("entry_received_needs_completion", max(submitted - confirmed, 0))
    )
    pending_verification = int(entry.get("entry_pending_verification", 0))
    not_received = int(entry.get("entry_not_received", max(total - submitted, 0)))
    missing_steps = list(entry.get("missing_entry", []))
    missing_fields = dict(entry.get("missing_entry_fields", {}))
    field_count = sum(len(fields) for fields in missing_fields.values())
    remaining = max(total - complete, 0)
    submission_remaining = max(total - complete, 0)
    public_total = int(entry.get("public_entry_total", max(total - 1, 0)))
    public_complete = int(entry.get("public_entry_complete", max(complete - 1, 0)))
    public_confirmed = int(
        entry.get("public_entry_confirmed", max(confirmed - 1, 0))
    )
    public_submitted = int(
        entry.get("public_entry_submitted", max(submitted - 1, 0))
    )
    public_corrections = int(entry.get("public_entry_received_needs_completion", 0))
    public_pending = int(entry.get("public_entry_pending_verification", 0))
    public_not_received = int(
        entry.get("public_entry_not_received", max(public_total - public_submitted, 0))
    )
    public_remaining = int(
        entry.get("public_entry_remaining_steps", max(public_total - public_complete, 0))
    )
    public_submission_remaining = int(
        entry.get("public_entry_submission_remaining", public_remaining)
    )
    public_missing_fields = dict(entry.get("public_entry_missing_fields", {}))
    public_field_count = int(
        entry.get(
            "public_entry_remaining_fields",
            sum(len(fields) for fields in public_missing_fields.values()),
        )
    )
    return {
        # ``entry_remaining_steps`` remains route-compatible: it counts rows
        # that have not yet been syntactically answered. The separate
        # confirmation counter includes answers such as “不确定”.
        "entry_remaining": remaining,
        "entry_remaining_steps": remaining,
        "entry_remaining_confirmation_steps": submission_remaining,
        "entry_submission_remaining": submission_remaining,
        "entry_remaining_fields": field_count,
        "entry_confirmed": confirmed,
        "entry_received_needs_completion": corrections,
        "entry_pending_verification": pending_verification,
        "entry_not_received": not_received,
        # P0 is a separate mode question.  These public counters are the
        # values shown to business users for the subsequent four-step scope
        # entry; legacy entry_* counters remain available for compatibility.
        "mode_step": entry.get("mode_step", "P0"),
        "mode_total": int(entry.get("mode_total", 1)),
        "mode_submitted": int(entry.get("mode_submitted", 0)),
        "mode_complete": int(entry.get("mode_complete", 0)),
        "mode_confirmed": int(entry.get("mode_confirmed", 0)),
        "mode_pending_verification": int(entry.get("mode_pending_verification", 0)),
        "mode_not_received": int(entry.get("mode_not_received", 1)),
        "mode_remaining_steps": int(entry.get("mode_remaining_steps", 1)),
        "mode_status": entry.get("mode_status", "not_received"),
        "mode_step_status": entry.get("mode_step_status"),
        "public_entry_steps": list(
            entry.get("public_entry_steps", ["P1", "P2", "P3", "P4"])
        ),
        "public_entry_total": public_total,
        "public_entry_submitted": public_submitted,
        "public_entry_complete": public_complete,
        "public_entry_confirmed": public_confirmed,
        "public_entry_received_needs_completion": public_corrections,
        "public_entry_pending_verification": public_pending,
        "public_entry_not_received": public_not_received,
        "public_entry_remaining_steps": public_remaining,
        "public_entry_submission_remaining": public_submission_remaining,
        "public_entry_remaining_fields": public_field_count,
        "public_entry_missing": list(entry.get("public_entry_missing", [])),
        "public_entry_missing_fields": public_missing_fields,
        "public_entry_conflicts": list(entry.get("public_entry_conflicts", [])),
        "public_entry_step_statuses": list(
            entry.get("public_entry_step_statuses", [])
        ),
        "public_entry_current_step": entry.get("public_entry_current_step"),
        "public_entry_current_step_number": entry.get(
            "public_entry_current_step_number"
        ),
        "public_entry_round_question_keys": list(
            entry.get("public_entry_round_question_keys", [])
        ),
        "entry_progress": {
            "total_steps": total,
            "completed_steps": confirmed,
            "route_ready_steps": complete,
            "submitted_steps": submitted,
            "received_needs_completion_steps": corrections,
            "pending_verification_steps": pending_verification,
            "not_received_steps": not_received,
            "remaining_steps": remaining,
            "remaining_confirmation_steps": submission_remaining,
            "submission_remaining_steps": submission_remaining,
            "remaining_fields": field_count,
            "missing_steps": missing_steps,
            "missing_fields": missing_fields,
            "current_step": entry.get("entry_current_step"),
            "current_step_number": entry.get("entry_current_step_number"),
            "current_round_question_keys": list(
                entry.get("entry_round_question_keys", [])
            ),
            "step_statuses": list(entry.get("entry_step_statuses", [])),
        },
        "mode_progress": dict(entry.get("mode_progress", {})),
        "public_entry_progress": dict(entry.get("public_entry_progress", {})),
    }


def _route_progress_fields(group_details: list[dict[str, Any]], total: int) -> dict[str, Any]:
    """Expose both group progress and question-slot progress.

    Future rounds are counted in ``remaining_question_slots`` because the
    route is already locked, while ``assigned_remaining_question_slots`` only
    counts questions that have actually been sent.  This lets the conversation
    say how much work remains without pretending that an unsent round was
    already assigned to the business team.
    """

    remaining_all = sum(len(group.get("all_missing_keys", [])) for group in group_details)
    remaining_assigned = sum(len(group.get("missing_keys", [])) for group in group_details)
    unassigned = sum(len(group.get("unassigned_keys", [])) for group in group_details)
    rounds = [round_detail for group in group_details for round_detail in group.get("rounds", [])]
    current_detail = next((group for group in group_details if not group.get("complete")), None)
    current_round = current_detail.get("next_round") if current_detail else None
    current_round_count = len(current_detail.get("rounds", [])) if current_detail else 0
    current_round_questions = len(current_detail.get("next_question_keys", [])) if current_detail else 0
    completed_rounds = sum(1 for round_detail in rounds if round_detail.get("complete"))
    assigned_remaining_rounds = sum(
        1
        for round_detail in rounds
        if round_detail.get("assigned") and not round_detail.get("complete")
    )
    completed_slots = max(
        sum(int(group.get("total_questions", 0)) for group in group_details) - remaining_all,
        0,
    )
    return {
        "total_question_slots": sum(int(group.get("total_questions", 0)) for group in group_details),
        "completed_question_slots": completed_slots,
        "remaining_question_slots": remaining_all,
        "assigned_remaining_question_slots": remaining_assigned,
        "unassigned_question_slots": unassigned,
        "total_rounds": len(rounds),
        "completed_rounds": completed_rounds,
        "remaining_rounds": len(rounds) - completed_rounds,
        "assigned_remaining_rounds": assigned_remaining_rounds,
        "current_round": current_round,
        "current_group_rounds": current_round_count,
        "current_round_question_slots": current_round_questions,
        "route_progress": {
            "total_groups": total,
            "completed_groups": sum(1 for group in group_details if group.get("complete")),
            "remaining_groups": sum(1 for group in group_details if not group.get("complete")),
            "total_question_slots": sum(int(group.get("total_questions", 0)) for group in group_details),
            "completed_question_slots": completed_slots,
            "remaining_question_slots": remaining_all,
            "assigned_remaining_question_slots": remaining_assigned,
            "total_rounds": len(rounds),
            "completed_rounds": completed_rounds,
            "remaining_rounds": len(rounds) - completed_rounds,
            "assigned_remaining_rounds": assigned_remaining_rounds,
            "current_round": current_round,
            "current_group_rounds": current_round_count,
            "current_round_question_slots": current_round_questions,
        },
    }


def _render_template(
    template: str | None, values: dict[str, Any], fallback: str
) -> str:
    """Render a manifest template while retaining compatibility with old manifests."""

    if not template:
        return fallback
    try:
        return str(template).format(**values)
    except (KeyError, IndexError, ValueError):
        return fallback


def format_entry_progress(
    result: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    locked_total: int | None = None,
) -> str:
    """Build the business-facing progress line used before route locking.

    P0 is a standalone mode question.  The public scope counter therefore
    reports P1-P4 as four steps, while the legacy ``entry_*`` counters remain
    available to callers that still treat P0-P4 as one internal contract.
    """

    total = int(result.get("entry_total", 0))
    route_ready = int(result.get("entry_complete", 0))
    # Fall back to the legacy five-row values when formatting an old result
    # object that predates public_entry_* fields.
    public_default_total = (
        len(public_entry_keys(manifest))
        if manifest is not None
        else max(total - 1, 0)
    )
    public_total = int(result.get("public_entry_total", public_default_total))
    public_route_ready = int(
        result.get("public_entry_complete", max(route_ready - 1, 0))
    )
    public_confirmed = int(
        result.get("public_entry_confirmed", max(int(result.get("entry_confirmed", route_ready)) - 1, 0))
    )
    public_submitted = int(
        result.get("public_entry_submitted", max(int(result.get("entry_submitted", 0)) - 1, 0))
    )
    public_corrections = int(
        result.get("public_entry_received_needs_completion", 0)
    )
    public_pending_verification = int(
        result.get("public_entry_pending_verification", 0)
    )
    public_not_received = int(
        result.get(
            "public_entry_not_received",
            max(public_total - public_submitted, 0),
        )
    )
    public_remaining = int(
        result.get(
            "public_entry_remaining_steps",
            max(public_total - public_route_ready, 0),
        )
    )
    public_submission_remaining = int(
        result.get("public_entry_submission_remaining", public_remaining)
    )
    public_fields = int(result.get("public_entry_remaining_fields", 0))
    mode_status = str(result.get("mode_status", "not_received"))
    mode_status_text = {
        "complete": "已确认",
        "submitted_uncertain": "已提交，待内部核实",
        "received_needs_completion": "已提交，还需补充",
        "conflict": "需要更正",
        "not_received": "尚未提交",
    }.get(mode_status, "待核对")
    if manifest is not None:
        minimum, maximum = _possible_group_counts(manifest)
        template = manifest.get("entry_progress_message_template")
    else:
        minimum = int(result.get("possible_min_groups", 0))
        maximum = int(result.get("possible_max_groups", 0))
        template = result.get("entry_progress_message_template")
    scope_start_note = (
        "（模式题完成后开始）"
        if mode_status not in {"complete", "submitted_uncertain"}
        else ""
    )
    fallback = (
        f"模式题：{mode_status_text}；范围入口共 {public_total} 步{scope_start_note}；"
        f"已确认 {public_confirmed} 步；"
        f"已提交待内部核实 {public_pending_verification} 步；"
        f"尚未提交 {public_not_received} 步；"
        f"还需提交或更正 {public_submission_remaining} 步"
        + (f"，其中 {public_fields} 个字段" if public_fields else "")
        + "。"
    )
    values = {
        "entry_total": total,
        "entry_complete": int(result.get("entry_confirmed", route_ready)),
        "entry_confirmed": int(result.get("entry_confirmed", route_ready)),
        "entry_route_ready": route_ready,
        "entry_submitted": int(result.get("entry_submitted", 0)),
        "entry_pending": int(result.get("entry_received_needs_completion", 0)),
        "entry_received_needs_completion": int(
            result.get("entry_received_needs_completion", 0)
        ),
        "entry_pending_verification": int(
            result.get("entry_pending_verification", 0)
        ),
        "entry_not_received": int(
            result.get("entry_not_received", max(total - int(result.get("entry_submitted", 0)), 0))
        ),
        # Keep the legacy placeholder available to older manifests.  The
        # current manifest uses the explicit public counters below.
        "entry_remaining": int(result.get("entry_remaining_steps", max(total - route_ready, 0))),
        "entry_confirmation_remaining": int(result.get("entry_submission_remaining", max(total - route_ready, 0))),
        "entry_submission_remaining": int(result.get("entry_submission_remaining", max(total - route_ready, 0))),
        "entry_remaining_fields": int(result.get("entry_remaining_fields", 0)),
        "mode_status": mode_status_text,
        "mode_status_code": mode_status,
        "mode_total": int(result.get("mode_total", 1)),
        "mode_submitted": int(result.get("mode_submitted", 0)),
        "mode_complete": int(result.get("mode_complete", 0)),
        "mode_confirmed": int(result.get("mode_confirmed", 0)),
        "mode_pending_verification": int(result.get("mode_pending_verification", 0)),
        "mode_not_received": int(result.get("mode_not_received", 1)),
        "mode_remaining_steps": int(result.get("mode_remaining_steps", 1)),
        "public_entry_total": public_total,
        "public_entry_complete": public_route_ready,
        "public_entry_confirmed": public_confirmed,
        "public_entry_submitted": public_submitted,
        "public_entry_received_needs_completion": public_corrections,
        "public_entry_pending_verification": public_pending_verification,
        "public_entry_not_received": public_not_received,
        "public_entry_remaining_steps": public_remaining,
        "public_entry_submission_remaining": public_submission_remaining,
        "public_entry_remaining_fields": public_fields,
        "possible_min_groups": minimum,
        "possible_max_groups": maximum,
    }
    # Only use a template that understands the split counters.  This avoids a
    # stale manifest or injected template reintroducing the old combined
    # five-row entry wording.
    if template and "{public_entry_total}" in str(template):
        line = _render_template(template, values, fallback)
    else:
        line = fallback
    if scope_start_note and "模式题完成后开始" not in line:
        line = line.replace(
            f"范围入口共 {public_total} 步",
            f"范围入口共 {public_total} 步{scope_start_note}",
            1,
        )
    if locked_total is not None:
        # Once the route is locked, do not keep showing the pre-lock estimate.
        # An uncertain entry fact can remain pending without changing the
        # locked number of questionnaire groups.
        line = re.sub(
            r"主题组总数会在入口确认后锁定，预计为\s*\d+\s*至\s*\d+\s*组问卷。?",
            "",
            line,
        ).strip()
        line += f"本次路线已锁定为 {locked_total} 组问卷；待核事实不会被重复追问。"
    elif minimum and maximum and "轻量版" not in line and "预计" not in line:
        line += f"主题组总数会在入口确认后锁定，预计为 {minimum} 至 {maximum} 组问卷。"
    return line


def format_route_progress(
    result: dict[str, Any], manifest: dict[str, Any] | None = None
) -> str:
    """Build the exact locked-route progress line for a conversation turn."""

    total = int(result.get("total_groups", result.get("total_questionnaires", 0)))
    completed = int(result.get("completed_groups", result.get("completed_questionnaires", 0)))
    remaining = int(
        result.get("remaining_groups", result.get("remaining_questionnaires", max(total - completed, 0)))
    )
    current = result.get("current_group")
    current_label = "已完成" if current is None else str(current)
    template = manifest.get("progress_message_template") if manifest else result.get(
        "progress_message_template"
    )
    fallback = (
        f"本次共需完成 {total} 组问卷；当前{('已完成' if current is None else '第 ' + str(current) + ' 组')}；"
        f"已完成 {completed} 组；还剩 {remaining} 组问卷。"
    )
    line = _render_template(
        template,
        {
            "total_groups": total,
            "total_questionnaires": total,
            "completed_groups": completed,
            "completed_questionnaires": completed,
            "current_label": "已完成" if current is None else f"第 {current} 组",
            "current_group": current_label,
            "current_questionnaire": current_label,
            "remaining_groups": remaining,
            "remaining_questionnaires": remaining,
        },
        fallback,
    )
    # Older route manifests may use “组” without saying these are
    # questionnaires.  Add the explicit noun once so the business team knows
    # how many fixed questionnaire groups remain.
    if "问卷" not in line:
        line = line.replace("组。", "组问卷。", 1)
    assigned = int(result.get("assigned_remaining_question_slots", 0))
    all_remaining = int(result.get("remaining_question_slots", assigned))
    current_round = result.get("current_round")
    current_group_rounds = int(result.get("current_group_rounds", 0))
    current_round_questions = int(result.get("current_round_question_slots", assigned))
    remaining_rounds = int(result.get("remaining_rounds", 0))
    if all_remaining:
        if current_round is not None and current_group_rounds:
            line += (
                f"当前组第 {current_round} / {current_group_rounds} 轮，本轮待答 {current_round_questions} 题；"
                f"整条路线还剩 {remaining_rounds} 个小轮、{all_remaining} 个题号。"
            )
        elif assigned != all_remaining:
            line += f"本轮待答 {current_round_questions} 题；已发送轮次还剩 {assigned} 题；整条路线还剩 {all_remaining} 个题号。"
        else:
            line += f"本轮待答 {current_round_questions} 题；整条路线还剩 {all_remaining} 个题号。"
    else:
        line += f"本轮待答 {current_round_questions} 题；整条路线的题目已全部收到回答。"
    return line


def calculate(
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    checker: Any | None = None,
    locked_signature: str | None = None,
    locked_total_groups: int | None = None,
) -> dict[str, Any]:
    """Calculate entry state, route, and group progress.

    ``checker`` is injectable for unit tests; normal callers can omit it.
    """

    checker = checker or load_checker()
    light_route_contract = validate_light_route_contract(manifest)
    public_entry_contract = validate_public_entry_contract(manifest)
    known_keys = set(manifest.get("entry_steps", []))
    known_keys.update(manifest.get("backend_registration_keys", []))
    all_templates = (
        list(manifest.get("light_group_templates", []))
        + list(manifest.get("full_group_templates", manifest.get("group_templates", [])))
    )
    for template in all_templates:
        known_keys.update(str(key).upper() for key in template.get("keys", []))
    unknown_keys = sorted({
        key for key in (_key(row) for row in rows)
        if key and key not in known_keys
    })
    if unknown_keys:
        entry = _entry_status(checker, rows, manifest)
        entry_fields = _entry_progress_fields(entry)
        backend = _backend_registration_status(checker, rows, manifest, entry)
        possible_min, possible_max = _possible_group_counts(manifest)
        entry_fields.update(
            {
                "possible_min_groups": possible_min,
                "possible_max_groups": possible_max,
            }
        )
        entry_fields["entry_progress_message"] = format_entry_progress(
            {**entry, **entry_fields}, manifest
        )
        return {
            "status": "input_conflict",
            "input_conflicts": ["未知题号：" + "、".join(unknown_keys)],
            "message": "答案含有当前路线不存在的题号；请先核对题号，不会据此推断事实。",
            **{key: value for key, value in entry.items() if key != "states"},
            **entry_fields,
            "backend_registration": backend,
            "registration_total": backend["registration_total"],
            "registration_collected": backend["registration_collected"],
            "registration_remaining": backend["registration_remaining"],
            "public_entry_contract": public_entry_contract,
        }
    entry = _entry_status(checker, rows, manifest)
    entry_fields = _entry_progress_fields(entry)
    backend = _backend_registration_status(checker, rows, manifest, entry)
    possible_min, possible_max = _possible_group_counts(manifest)
    entry_fields.update(
        {
            "possible_min_groups": possible_min,
            "possible_max_groups": possible_max,
        }
    )
    entry_fields["entry_progress_message"] = format_entry_progress(
        {**entry, **entry_fields}, manifest
    )
    if entry["entry_conflicts"]:
        return {
            "status": "entry_conflict",
            **{key: value for key, value in entry.items() if key != "states"},
            **entry_fields,
            "backend_registration": backend,
            "registration_total": backend["registration_total"],
            "registration_collected": backend["registration_collected"],
            "registration_remaining": backend["registration_remaining"],
            "public_entry_contract": public_entry_contract,
            "message": "首屏答案有冲突；请先更正后再锁定本次路线，不会据此推断事实。",
        }
    if entry["entry_complete"] < entry["entry_total"]:
        pending_parts = [
            key + "（" + "、".join(fields) + "）"
            for key, fields in entry["missing_entry_fields"].items()
        ]
        pending_parts.extend(entry["missing_entry"])
        detail = "；还需补：" + "、".join(pending_parts) if pending_parts else ""
        return {
            "status": "entry_incomplete",
            **{key: value for key, value in entry.items() if key != "states"},
            **entry_fields,
            "backend_registration": backend,
            "registration_total": backend["registration_total"],
            "registration_collected": backend["registration_collected"],
            "registration_remaining": backend["registration_remaining"],
            "public_entry_contract": public_entry_contract,
            "message": f"入口步骤尚未完整收齐{detail}；提交后才锁定本次问卷路线。",
        }

    # The public four-step entry is mirrored by four hidden registration
    # records.  Explicit internal records with conflicts or missing fields
    # block the lock and remain visible in machine-readable output.
    if not backend["registration_ready"]:
        pending_count = sum(
            1
            for record in backend.get("records", [])
            if record.get("status") != "complete"
        )
        conflict_count = len(backend.get("registration_conflicts", []))
        registration_detail = (
            f"{max(pending_count, conflict_count, 1)} 项后台登记记录需要补充或更正"
        )
        return {
            "status": "registration_incomplete",
            **{key: value for key, value in entry.items() if key != "states"},
            **entry_fields,
            "backend_registration": backend,
            "registration_total": backend["registration_total"],
            "registration_collected": backend["registration_collected"],
            "registration_remaining": backend["registration_remaining"],
            "public_entry_contract": public_entry_contract,
            "message": (
                "路线核对记录尚未全部收齐；请先补充或更正："
                + registration_detail
                + "。路线总组数暂不锁定。"
            ),
        }

    flags = route_flags(rows)
    mode, mode_source = evaluation_mode(rows, manifest)
    groups = selected_groups(manifest, flags, rows)
    group_details: list[dict[str, Any]] = []
    previous_groups_complete = True
    for index, group in enumerate(groups, 1):
        detail = _group_detail(
            checker,
            rows,
            group,
            index,
            activate=previous_groups_complete,
        )
        group_details.append(detail)
        previous_groups_complete = detail["complete"]
    completed = sum(1 for group in group_details if group["complete"])
    current_group = next(
        (group["group_number"] for group in group_details if not group["complete"]),
        None,
    )
    current_detail = next(
        (group for group in group_details if group["group_number"] == current_group),
        None,
    )
    total = len(groups)
    group_unknown_keys = {
        key
        for group in group_details
        for key in group["pending_unknown_keys"]
    }
    entry_unknown_keys = {
        str(item.get("question_key", ""))
        for item in entry.get("entry_step_statuses", [])
        if item.get("unknown")
    }
    unknown_items = len(group_unknown_keys | entry_unknown_keys)
    pending_verification_keys = sorted(group_unknown_keys | entry_unknown_keys)
    signature = _route_signature(rows, manifest, groups, backend)
    route_fields = _route_progress_fields(group_details, total)
    route_change_applied = False
    if locked_signature is not None:
        previous = str(locked_signature).strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", previous):
            return {
                "status": "route_lock_conflict",
                "message": "已锁定路线签名格式无效；请保留上一次脚本输出的64位签名，不要重新猜测路线。",
                "previous_route_signature": locked_signature,
                "route_signature": signature,
                "total_groups": total,
                "completed_groups": completed,
                "current_group": current_group,
                "remaining_groups": total - completed,
                "total_questionnaires": total,
                "completed_questionnaires": completed,
                "remaining_questionnaires": total - completed,
                **route_fields,
                "backend_registration": backend,
                }
        explicit_scope_revision = any(
            bool(row.get("revision")) and _key(row) in set(manifest.get("entry_steps", []))
            for row in rows
        )
        if previous != signature and explicit_scope_revision:
            route_change_applied = True
        elif previous != signature:
            if locked_total_groups is not None:
                conflict_detail = (
                    f"当前锁定路线仍按 {locked_total_groups} 组保留；"
                    f"候选路线的 {total} 组仅供核对，当前已完成和剩余组数暂不重算。"
                )
            else:
                conflict_detail = (
                    "原锁定总组数未随签名提供；当前已完成和剩余组数暂不显示，"
                    f"候选路线的 {total} 组仅供核对。"
                )
            return {
                "status": "route_lock_conflict",
                "message": "入口答案或触发主题出现未标明为更正的变化；请用“改为”提交明确修订，避免把重复答案误当成范围变更。",
                "previous_route_signature": previous,
                "route_signature": signature,
                "entry_changes_after_lock": True,
                "old_total_groups": locked_total_groups,
                "new_total_groups": total,
                "locked_total_groups": locked_total_groups,
                "total_groups": locked_total_groups,
                # These values describe the newly computed candidate route,
                # not the previously locked route.  Do not mix them: an
                # expanded candidate may have more completed groups than the
                # old route and would otherwise yield negative remaining
                # counts.
                "completed_groups": None,
                "current_group": None,
                "remaining_groups": None,
                "total_questionnaires": locked_total_groups,
                "completed_questionnaires": None,
                "remaining_questionnaires": None,
                "message_detail": conflict_detail,
                "progress_unavailable_reason": "candidate_route_not_old_locked_route",
                "backend_registration": backend,
                }
            # The caller must explicitly acknowledge a scope change.  The
            # candidate total is reported for the new route, but is never
            # silently applied to the locked conversation.
    locked_entry_progress_message = format_entry_progress(
        {**entry, **entry_fields}, manifest, locked_total=total
    )
    return {
        "status": "route_locked",
        "route_locked": True,
        "route_change_applied": route_change_applied,
        "previous_route_signature": str(locked_signature).strip().lower() if route_change_applied and locked_signature else None,
        **{key: value for key, value in entry.items() if key != "states"},
        **entry_fields,
        "entry_progress_message": locked_entry_progress_message,
        "route_selection": route_selection(rows, manifest),
        "assessment_mode": mode,
        "mode_source": mode_source,
        "technical_detail_enabled": technical_detail_enabled(rows, manifest),
        "include_system": flags[0],
        "include_model": flags[1],
        "include_ancillary": flags[2],
        "total_groups": total,
        "completed_groups": completed,
        "current_group": current_group,
        "remaining_groups": total - completed,
        "total_questionnaires": total,
        "completed_questionnaires": completed,
        "remaining_questionnaires": total - completed,
        **route_fields,
        "backend_registration": backend,
        "registration_total": backend["registration_total"],
        "registration_collected": backend["registration_collected"],
        "registration_confirmed": backend["registration_confirmed"],
        "registration_remaining": backend["registration_remaining"],
        "unknown_items": unknown_items,
        "pending_verification_count": unknown_items,
        "pending_verification_keys": pending_verification_keys,
        "groups": group_details,
        "next_question_keys": current_detail["next_question_keys"] if current_detail else [],
        "next_round": current_detail["next_round"] if current_detail else None,
        "omitted_themes": _omitted_themes(manifest, flags, mode),
        "omitted_details": {
            "reason": manifest.get("omitted_detail_reasons", {}).get(
                "light_mode" if mode == "light" else "technical_gate_not_enabled",
                "",
            )
            if mode == "light" or not technical_detail_enabled(rows, manifest)
            else "",
            "technical_detail_keys": list(manifest.get("technical_detail_keys", [])),
        },
        "route_signature": signature,
        "light_route_contract": light_route_contract,
        "public_entry_contract": public_entry_contract,
        "fact_record": manifest.get("fact_record_schema", {}),
        "progress_message": format_route_progress(
            {
                "total_groups": total,
                "completed_groups": completed,
                "current_group": current_group,
                "remaining_groups": total - completed,
                **route_fields,
            },
            manifest,
        ),
    }


def _print_entry_progress(result: dict[str, Any]) -> None:
    def public_entry_label(key: str) -> str:
        # P0 is shown as a standalone mode question; P1-P4 are the four
        # scope-entry steps shown after mode selection.
        labels = {"P0": "模式题", "P1": "第1步", "P2": "第2步", "P3": "第3步", "P4": "第4步"}
        if str(key).upper() in labels:
            return labels[str(key).upper()]
        return "开始问题" if str(key).upper() == "P5" else str(key)

    def status_label(status: str) -> str:
        return {
            "complete": "已确认",
            "submitted_uncertain": "已提交，待内部核实",
            "received_needs_completion": "已提交，还需补充",
            "conflict": "需要更正",
            "not_received": "尚未提交",
        }.get(status, "待核对")

    def print_step_detail() -> None:
        mode_status = result.get("mode_step_status")
        if mode_status:
            print(
                "模式题状态："
                + status_label(str(mode_status.get("status", "")))
            )
        statuses = result.get("public_entry_step_statuses") or []
        if statuses:
            rendered = "；".join(
                f"{public_entry_label(item.get('question_key', ''))}{status_label(str(item.get('status', '')))}"
                for item in statuses
            )
            print("范围入口逐步状态：" + rendered)
        mode_complete = int(result.get("mode_complete", 0))
        if not mode_complete:
            if mode_status and str(mode_status.get("status", "")) == "not_received":
                print("当前待答：模式题。")
            return
        current_number = result.get("public_entry_current_step_number")
        current_keys = result.get("public_entry_round_question_keys") or []
        if current_number is not None:
            questions = "、".join(public_entry_label(key) for key in current_keys)
            print(
                f"当前范围入口第 {current_number} / {result.get('public_entry_total', 4)} 步；"
                + (f"本轮问题：{questions}。" if questions else "本轮暂无待答问题。")
            )

    if result.get("status") == "input_conflict":
        print(result.get("message", "已锁定路线发生变化，请先确认入口答案。"))
        if result.get("previous_route_signature"):
            print("已锁定路线签名：" + str(result["previous_route_signature"]))
        if result.get("route_signature"):
            print("当前计算签名：" + str(result["route_signature"]))
        if result.get("input_conflicts"):
            print("先更正：" + "；".join(str(item) for item in result["input_conflicts"]))
        if result.get("entry_total") is not None:
            print(format_entry_progress(result))
            print_step_detail()
        return
    if result.get("status") == "route_lock_conflict":
        print(result.get("message", "已锁定路线发生变化，请先确认入口答案。"))
        if result.get("previous_route_signature"):
            print("已锁定路线签名：" + str(result["previous_route_signature"]))
        if result.get("route_signature"):
            print("当前计算签名：" + str(result["route_signature"]))
        if result.get("message_detail"):
            print(result["message_detail"])
        if (
            result.get("total_groups") is not None
            and result.get("completed_groups") is not None
            and result.get("remaining_groups") is not None
        ):
            print(format_route_progress(result))
        elif result.get("locked_total_groups") is not None:
            # The old route is authoritative, but its per-group completion
            # cannot be recomputed from a changed entry without silently
            # mixing candidate-route answers.  Still show the fixed total so
            # the business team always knows the scope currently in force.
            print(
                "当前锁定路线总组数："
                f"{result['locked_total_groups']} 组问卷；"
                "已完成组数和剩余组数暂不重算，待路线冲突确认后恢复显示。"
            )
        else:
            print("当前进度总组数：原锁定总数未知；候选路线总数仅供核对，不计入进度。")
        if result.get("new_total_groups") is not None:
            print(f"候选路线总组数（仅供核对）：{result['new_total_groups']}。")
        return
    if result.get("status") == "registration_incomplete":
        # Keep the internal registration keys out of the business view while
        # still giving an actionable count for the route gate.
        print(result.get("message", "路线核对记录尚未全部收齐；路线总组数暂不锁定。"))
        total = int(result.get("registration_total", 0))
        collected = int(result.get("registration_collected", 0))
        remaining = int(result.get("registration_remaining", max(total - collected, 0)))
        print(
            f"路线核对进度：已收齐 {collected} / {total} 项；"
            f"还需补充或更正 {remaining} 项；路线总组数尚未锁定。"
        )
        print(format_entry_progress(result))
        print_step_detail()
        return
    message = str(result.get("message", ""))
    message = re.sub(r"P([0-4])", lambda match: public_entry_label("P" + match.group(1)), message)
    print(message)
    print(format_entry_progress(result))
    print_step_detail()
    missing_entry = result.get("missing_entry") or []
    if missing_entry:
        print("待提交入口：" + "、".join(public_entry_label(key) for key in missing_entry))
    if result.get("missing_entry_fields"):
        print(
            "待补字段："
            + "；".join(
                public_entry_label(key) + "（" + "、".join(fields) + "）"
                for key, fields in result["missing_entry_fields"].items()
            )
        )
    if result.get("entry_conflicts"):
        conflicts = []
        for conflict in result["entry_conflicts"]:
            text = str(conflict)
            text = re.sub(r"P([0-4])", lambda match: public_entry_label("P" + match.group(1)), text)
            conflicts.append(text)
        print("先更正冲突：" + "；".join(conflicts))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answers", type=Path, help="业务答案 Markdown、JSON 或逐题文本")
    parser.add_argument("--format", choices=("auto", "json", "markdown", "text"), default="auto")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="明确按会话渐进模式输出部分进度；最终评估仍须运行严格答案检查",
    )
    parser.add_argument(
        "--locked-signature",
        help="传入上一轮锁定的64位路线签名；变化时只报告路线冲突，不改变本次总组数",
    )
    parser.add_argument(
        "--locked-total-groups",
        type=int,
        help="与上一轮路线签名一起保存的旧锁定总组数；冲突时仅该数用于当前进度",
    )
    args = parser.parse_args()
    try:
        checker = load_checker()
        rows = checker.load_rows(args.answers, args.format)
        manifest = json.loads(ROUTE_PATH.read_text(encoding="utf-8"))
        result = calculate(rows, manifest, checker, args.locked_signature, args.locked_total_groups)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"ERROR: 无法计算问卷进度：{exc}", file=sys.stderr)
        return 2
    status = result.get("status")
    if status == "route_locked":
        exit_code = 0
    elif status in {"entry_incomplete", "registration_incomplete"}:
        exit_code = 0 if args.allow_incomplete else 1
    else:
        exit_code = 1
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return exit_code
    if result["status"] != "route_locked":
        _print_entry_progress(result)
        return exit_code
    current = result["current_group"]
    print("入口进度：" + (result.get("entry_progress_message") or format_entry_progress(result)))
    if result.get("route_change_applied"):
        print("已按明确的更正记录更新路线；这次更正本身就是确认，不再要求二次确认。")
    print(result.get("progress_message") or format_route_progress(result))
    if result["next_question_keys"]:
        labels = [
            "开始问题" if key == "P5" else ("资料深度问题" if key == "P6" else key)
            for key in result["next_question_keys"]
        ]
        print("当前轮待答题：" + "、".join(labels))
    if result["unknown_items"]:
        print(f"其中有 {result['unknown_items']} 项待内部核实；这些答案已经提交，不会重复追问，也不等于否定。")
    for group in result["groups"]:
        state = "已完成" if group["complete"] else "待完成"
        print(
            f"第 {group['group_number']} 组 {group['title']}：{state}，"
            f"已提交 {group['submitted_questions']} / {group['total_questions']} 题"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
