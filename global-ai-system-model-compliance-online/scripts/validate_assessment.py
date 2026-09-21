#!/usr/bin/env python3
"""Validate a three-layer AI compliance assessment locally.

Usage: python validate_assessment.py assessment.json [--schema assessment-schema.json]
The validator never performs network access. It uses jsonschema when installed and
always performs cross-reference and conservative-uncertainty checks itself.  When
jsonschema is unavailable, the bundled fallback covers every keyword currently
used by the local schema and emits a high-priority warning; an unsupported future
schema keyword fails validation closed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "assets" / "assessment-schema.json"

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$",
    re.IGNORECASE,
)

# Validation and annotation keywords used by the bundled schema.  If the
# schema later gains a keyword that this fallback does not understand, local
# validation fails closed instead of silently accepting weaker constraints.
FALLBACK_SCHEMA_KEYWORDS = {
    "$schema", "$id", "$ref", "$defs", "title", "description", "default",
    "type", "required", "properties", "additionalProperties", "items",
    "minItems", "maxItems", "uniqueItems", "contains", "allOf", "anyOf",
    "oneOf", "minLength", "maxLength", "pattern", "format", "enum", "const",
}


def is_iso_date(value: Any) -> bool:
    if not isinstance(value, str) or not ISO_DATE_RE.fullmatch(value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def is_iso_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not RFC3339_RE.fullmatch(value):
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00").replace("z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def assessment_mode(data: dict[str, Any]) -> str:
    """Return the locked delivery mode, preserving the legacy default.

    Early assessment files pre-date the explicit mode field and were always
    rendered as full assessments.  New files store ``assessment.mode``.  The
    top-level fallback is intentionally accepted by the semantic validator so
    a migration can be diagnosed without silently treating a light report as
    a full one; the JSON schema still documents the canonical nested field.
    """

    assessment = data.get("assessment", {})
    candidates: list[Any] = []
    if isinstance(assessment, dict):
        candidates.extend((assessment.get("mode"), assessment.get("delivery_mode")))
    candidates.extend((data.get("mode"), data.get("delivery_mode")))
    for candidate in candidates:
        if isinstance(candidate, str):
            value = candidate.strip().casefold()
            if value in {"light", "lightweight", "轻量版", "轻量版初步评估"}:
                return "light"
            if value in {"full", "complete", "全量版", "全量版评估"}:
                return "full"
    # Compatibility rule for records written before P0/mode was introduced.
    return "full"


def normalized_reference(value: Any) -> str:
    """Normalize a legal/evidence reference for conservative matching."""

    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.casefold())


def article_numbers(value: Any) -> set[int]:
    """Extract article numbers without treating years or CELEX digits as articles."""

    if not isinstance(value, str):
        return set()
    numbers: set[int] = set()
    patterns = (
        r"\barticles?\s*\.?\s*(\d+)(?:\s*(?:[-\u2013]|to)\s*(\d+))?",
        r"\bart\s*\.?\s*(\d+)(?:\s*(?:[-\u2013]|to)\s*(\d+))?",
        r"第\s*(\d+)\s*条(?:\s*(?:[-\u2013]|至)\s*第?\s*(\d+)\s*条)?",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, value, re.IGNORECASE):
            first = int(match.group(1))
            last = int(match.group(2) or first)
            # Article ranges in the corpus are short; cap expansion so a
            # malformed string cannot allocate an unbounded set.
            if 0 <= last - first <= 200:
                numbers.update(range(first, last + 1))
            else:
                numbers.add(first)
    return numbers


def law_reference_matches(reference: Any, law: dict[str, Any]) -> bool:
    """Return whether a legal-basis string identifies the linked law.

    Assessments commonly use either a stable local law id (``law-ai-act``), a
    short name (``GDPR Art. 44``), or a CELEX/ELI citation.  A bare arbitrary
    string must not pass merely because the obligation has a ``law_id``.
    """

    ref = normalized_reference(reference)
    if not ref:
        return False
    candidates: list[str] = []
    # Free-form notes are intentionally excluded: they are explanatory audit
    # text, not a legal identifier and must not be enough to validate a basis.
    for key in ("id", "name", "citation", "celex", "eli", "source_url"):
        value = law.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(normalized_reference(value))
    # If the reference names a specific article, the linked law's own
    # citation must contain the same article number.  Otherwise a short law
    # name such as “GDPR” would make any unrelated article appear valid.
    referenced_articles = article_numbers(reference)
    if referenced_articles:
        linked_articles: set[int] = set()
        # Only the structured citation is authoritative for this comparison;
        # free-form notes may mention unrelated articles or implementation
        # guidance and must not make a mismatched legal basis pass.
        linked_articles.update(article_numbers(law.get("citation")))
        if not linked_articles or not referenced_articles.issubset(linked_articles):
            return False
    # Article-only strings are deliberately not accepted as a fallback.  An
    # article number without the linked law name, identifier or citation can
    # silently point at the wrong instrument (for example, “Art. 50” attached
    # to a GDPR obligation).  Generated records must therefore carry a
    # law-specific anchor; the caller may still use a short name plus article,
    # such as “GDPR Art. 44-46”, which matches the candidates above.
    if any(
        ref == candidate
        or (len(ref) >= 5 and ref in candidate)
        or (len(candidate) >= 4 and candidate in ref)
        for candidate in candidates
    ):
        return True
    return False


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _matches_type(instance: Any, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(instance, dict)
    if schema_type == "array":
        return isinstance(instance, list)
    if schema_type == "string":
        return isinstance(instance, str)
    if schema_type == "boolean":
        return isinstance(instance, bool)
    if schema_type == "number":
        return not isinstance(instance, bool) and isinstance(instance, (int, float))
    if schema_type == "integer":
        return not isinstance(instance, bool) and isinstance(instance, int)
    if schema_type == "null":
        return instance is None
    return False


def unsupported_schema_keywords(schema: Any, path: str = "$") -> list[str]:
    """Return schema keywords the built-in validator cannot enforce."""

    if isinstance(schema, bool):
        return []
    if not isinstance(schema, dict):
        return [f"{path}: schema node is not an object or boolean"]
    errors = [
        f"{path}: unsupported schema keyword {key!r}"
        for key in schema
        if key not in FALLBACK_SCHEMA_KEYWORDS
    ]
    for container in ("properties", "$defs"):
        children = schema.get(container, {})
        if isinstance(children, dict):
            for key, child in children.items():
                errors.extend(unsupported_schema_keywords(child, f"{path}.{container}.{key}"))
    for keyword in ("items", "contains", "additionalProperties"):
        child = schema.get(keyword)
        if isinstance(child, (dict, bool)):
            errors.extend(unsupported_schema_keywords(child, f"{path}.{keyword}"))
    for keyword in ("allOf", "anyOf", "oneOf"):
        children = schema.get(keyword, [])
        if isinstance(children, list):
            for index, child in enumerate(children):
                errors.extend(unsupported_schema_keywords(child, f"{path}.{keyword}[{index}]"))
    return errors


def _valid_uri(value: str) -> bool:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if not parsed.scheme:
        return False
    if parsed.scheme in {"http", "https"}:
        return bool(parsed.netloc)
    return bool(parsed.netloc or parsed.path)


def basic_validate(
    instance: Any,
    schema: dict[str, Any] | bool,
    path: str = "$",
    root_schema: dict[str, Any] | None = None,
) -> list[str]:
    """Validate every assertion keyword used by the bundled schema."""

    if schema is True:
        return []
    if schema is False:
        return [f"{path}: value is rejected by schema"]
    root_schema = root_schema or schema
    ref = schema.get("$ref")
    if ref and ref.startswith("#/"):
        target: Any = root_schema
        try:
            for part in ref[2:].split("/"):
                decoded = part.replace("~1", "/").replace("~0", "~")
                target = target[decoded]
        except (KeyError, TypeError):
            return [f"{path}: unresolved schema reference {ref!r}"]
        return basic_validate(instance, target, path, root_schema)
    errors: list[str] = []

    # Enforce the full set of assertion keywords currently used by the local
    # schema. unsupported_schema_keywords() prevents silent degradation if the
    # schema later adopts another keyword.
    declared_type = schema.get("type")
    allowed_types = declared_type if isinstance(declared_type, list) else [declared_type]
    allowed_types = [candidate for candidate in allowed_types if isinstance(candidate, str)]
    schema_type: str | None = None
    if allowed_types:
        schema_type = next(
            (candidate for candidate in allowed_types if _matches_type(instance, candidate)),
            None,
        )
        if schema_type is None:
            expected = allowed_types[0] if len(allowed_types) == 1 else f"one of {allowed_types}"
            return [f"{path}: expected {expected}"]
    if "anyOf" in schema:
        branches = schema["anyOf"]
        if not any(not basic_validate(instance, branch, path, root_schema) for branch in branches):
            errors.append(f"{path}: does not match anyOf")
    if "oneOf" in schema:
        matches = sum(not basic_validate(instance, branch, path, root_schema) for branch in schema["oneOf"])
        if matches != 1:
            errors.append(f"{path}: does not match exactly one oneOf branch")
    if "allOf" in schema:
        for branch in schema["allOf"]:
            errors.extend(basic_validate(instance, branch, path, root_schema))

    if schema_type == "object":
        if not isinstance(instance, dict):
            return [f"{path}: expected object"]
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        unknown_keys = [key for key in instance if key not in properties]
        if additional is False:
            errors.extend(f"{path}.{key}: unknown property" for key in unknown_keys)
        elif isinstance(additional, dict):
            for key in unknown_keys:
                errors.extend(basic_validate(instance[key], additional, f"{path}.{key}", root_schema))
        for key, subschema in properties.items():
            if key in instance:
                errors.extend(basic_validate(instance[key], subschema, f"{path}.{key}", root_schema))
    elif schema_type == "array":
        if not isinstance(instance, list):
            return [f"{path}: expected array"]
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: expected at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: expected at most {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen: set[str] = set()
            for index, value in enumerate(instance):
                marker = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
                if marker in seen:
                    errors.append(f"{path}[{index}]: duplicate array item")
                seen.add(marker)
        for i, value in enumerate(instance):
            errors.extend(basic_validate(value, schema.get("items", {}), f"{path}[{i}]", root_schema))
        if "contains" in schema and not any(not basic_validate(value, schema["contains"], f"{path}[*]", root_schema) for value in instance):
            errors.append(f"{path}: expected an item matching contains")
    elif schema_type == "string":
        if not isinstance(instance, str):
            errors.append(f"{path}: expected string")
        else:
            if len(instance) < schema.get("minLength", 0):
                errors.append(f"{path}: string is shorter than minLength")
            if "maxLength" in schema and len(instance) > schema["maxLength"]:
                errors.append(f"{path}: string is longer than maxLength")
            if "pattern" in schema and not re.search(schema["pattern"], instance):
                errors.append(f"{path}: string does not match pattern")
            fmt = schema.get("format")
            if fmt == "date":
                if not is_iso_date(instance):
                    errors.append(f"{path}: invalid ISO date")
            elif fmt == "date-time":
                if not is_iso_datetime(instance):
                    errors.append(f"{path}: invalid ISO date-time")
            elif fmt == "uri" and not _valid_uri(instance):
                errors.append(f"{path}: invalid URI")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum")
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected {schema['const']!r}")
    return errors


def semantic_validate(data: dict[str, Any], strict: bool | None = None) -> tuple[list[str], list[str]]:
    """Run cross-field checks that JSON Schema cannot express.

    ``strict`` is retained as an explicit API/CLI switch for callers that need
    to distinguish an audit gate from a migration lint.  Records with the
    explicit ``assessment.mode`` field opt into the strict gate automatically;
    pre-mode records keep the historical semantic behavior unless a caller
    passes ``strict=True``.  This lets old evidence fixtures be migrated while
    ensuring every newly generated assessment is conservative by default.
    """
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["$: assessment must be an object"], warnings

    assessment_record = data.get("assessment", {})
    mode_declared = isinstance(assessment_record, dict) and any(
        key in assessment_record for key in ("mode", "delivery_mode")
    )
    if strict is None:
        strict = mode_declared or any(
            key in data for key in ("mode", "delivery_mode")
        )

    def collection(name: str) -> list[Any]:
        value = data.get(name, [])
        return value if isinstance(value, list) else []

    assessment = data.get("assessment", {})
    if not isinstance(assessment, dict):
        assessment = {}
    if not is_iso_datetime(assessment.get("created_at")):
        errors.append("assessment.created_at: must be a valid RFC3339 date-time")
    if not is_iso_date(assessment.get("knowledge_cutoff")):
        errors.append("assessment.knowledge_cutoff: must be a valid ISO date")

    def check_unique_ids(items: Any, label: str) -> None:
        if not isinstance(items, list):
            return
        seen: set[str] = set()
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if not nonempty(item_id):
                errors.append(f"{label}[{index}]: id must be a non-empty string")
                continue
            if item_id in seen:
                errors.append(f"{label}: duplicate id {item_id!r}")
            seen.add(item_id)

    for collection_name in ("facts", "laws", "roles", "obligations", "risks", "actions", "evidence"):
        check_unique_ids(data.get(collection_name, []), collection_name)

    if strict:
        # A completely empty object can satisfy the structural schema while
        # conveying no business fact at all.  Treat it as a migration/incomplete
        # record, never as a completed assessment.
        substantive = any(
            isinstance(data.get(name), list) and bool(data.get(name))
            for name in ("facts", "questionnaire_responses", "evidence", "data_flows")
        )
        if not substantive and not (
            isinstance(assessment_record, dict) and assessment_record.get("incomplete") is True
        ):
            errors.append(
                "assessment: strict validation requires at least one business fact, questionnaire response, data flow or evidence record"
            )

    def index_by_id(collection_name: str) -> dict[str, dict[str, Any]]:
        collection = data.get(collection_name, [])
        if not isinstance(collection, list):
            return {}
        return {
            str(item["id"]): item
            for item in collection
            if isinstance(item, dict) and nonempty(item.get("id"))
        }

    laws = index_by_id("laws")
    facts = index_by_id("facts")
    roles = index_by_id("roles")
    obligations = index_by_id("obligations")
    risks = index_by_id("risks")
    actions = index_by_id("actions")
    evidence = index_by_id("evidence")

    # Future dates are a first-class audit record.  A future law may be listed
    # as a warning, but it cannot disappear simply because the caller selected
    # “current obligations only”.
    scope = data.get("scope", {})
    if not isinstance(scope, dict):
        scope = {}
    future_dates = scope.get("future_effective_dates", [])
    if not isinstance(future_dates, list):
        errors.append("scope.future_effective_dates: expected a list")
        future_dates = []
    future_law_ids: set[str] = set()
    for index, item in enumerate(future_dates):
        if not isinstance(item, dict):
            errors.append(f"scope.future_effective_dates[{index}]: expected an object")
            continue
        law_id = item.get("law_id")
        if not isinstance(law_id, str) or law_id not in laws:
            errors.append(f"scope.future_effective_dates[{index}]: unknown law_id {law_id!r}")
        else:
            future_law_ids.add(law_id)
        if not is_iso_date(item.get("effective_from")):
            errors.append(f"scope.future_effective_dates[{index}]: invalid effective_from")
        if not nonempty(item.get("preparation_action")):
            errors.append(f"scope.future_effective_dates[{index}]: preparation_action is required")
        if not is_iso_date(item.get("review_date")):
            errors.append(f"scope.future_effective_dates[{index}]: review_date is required")

    future_laws_without_dates = {
        str(law.get("id"))
        for law in collection("laws")
        if isinstance(law, dict) and law.get("legal_status") == "future" and law.get("id")
    } - future_law_ids
    for law_id in sorted(future_laws_without_dates):
        errors.append(f"law {law_id}: future law must have a scope.future_effective_dates record")

    unknown_choices = (
        "不确定", "待核实", "事实待核实", "尚未决定", "unknown", "uncertain",
    )
    exclusive_choices = {
        "没有", "否", "否且有证据", "均未完成", "以上均无", "以上都没有", "暂不评估",
        "无生成内容", "没有模型", "没有机制", "none", "no", "not applicable", "n/a",
    }

    def choice_kind(value: Any) -> str:
        normalized = str(value).strip().casefold()
        if any(
            normalized == token
            or normalized.startswith(token + suffix)
            for token in unknown_choices
            for suffix in (" ", "(", "（", ":", "：", "-", "，", ",")
        ):
            return "unknown"
        if normalized in exclusive_choices:
            return "exclusive"
        return "definite"

    def option_conflict(selected: list[Any], mode: str) -> str | None:
        """Return a deterministic conflict reason for self-check selections."""

        normalized = list(dict.fromkeys(
            str(item).strip() for item in selected if str(item).strip()
        ))
        if mode == "single" and len(normalized) > 1:
            return "single-choice question has more than one selected option"
        kinds = {choice_kind(item) for item in normalized}
        if "unknown" in kinds and len(normalized) > 1:
            return "uncertain option cannot be combined with a definite option"
        if "exclusive" in kinds and len(normalized) > 1:
            return "none/deferred option cannot be combined with another option"
        return None

    def add_itemized_field(
        grouped: dict[str, dict[str, Any]],
        field: Any,
        raw_value: Any,
        child_mode: Any,
        owner: str,
    ) -> list[str]:
        field_errors: list[str] = []
        label = str(field).strip()
        if not label:
            return [f"{owner}: itemized selection must identify a non-empty field"]
        mode = str(child_mode or "multi")
        if mode not in {"single", "multi"}:
            field_errors.append(f"{owner} field {label!r}: mode must be single or multi")
            mode = "multi"
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        values = [str(value).strip() for value in values if value is not None and str(value).strip()]
        if not values:
            field_errors.append(f"{owner} field {label!r}: value is blank; use an explicit unknown option")
        key = label.casefold()
        group = grouped.setdefault(key, {"label": label, "mode": mode, "values": []})
        if group["mode"] != mode:
            field_errors.append(f"{owner} field {label!r}: conflicting child modes")
        group["values"].extend(values)
        return field_errors

    def itemized_conflicts(response: dict[str, Any], owner: str) -> list[str]:
        grouped: dict[str, dict[str, Any]] = {}
        findings: list[str] = []
        selected = response.get("selected", [])
        if not isinstance(selected, list):
            return [f"{owner}: selected must be an array"]
        for entry in selected:
            if isinstance(entry, dict):
                findings.extend(add_itemized_field(
                    grouped,
                    entry.get("field"),
                    entry.get("value"),
                    entry.get("mode", "multi"),
                    owner,
                ))
                continue
            match = re.match(r"^\s*([^:：]+?)\s*[:：]\s*(.*?)\s*$", str(entry))
            if not match:
                findings.append(
                    f"{owner}: legacy itemized selection {entry!r} has no field label; use field/value"
                )
                continue
            findings.extend(add_itemized_field(
                grouped, match.group(1), match.group(2), "multi", owner
            ))

        fields = response.get("fields")
        if fields is not None and not isinstance(fields, dict):
            findings.append(f"{owner}: fields must be an object")
        elif isinstance(fields, dict):
            for field, answer in fields.items():
                if isinstance(answer, dict):
                    raw_value = answer.get("value", answer.get("selected"))
                    child_mode = answer.get("mode", "multi")
                else:
                    raw_value = answer
                    child_mode = "multi"
                findings.extend(add_itemized_field(
                    grouped, field, raw_value, child_mode, owner
                ))

        # Backward-compatible fallback for an itemized answer that predates
        # selected/fields.  Only labelled segments are interpreted; free-form
        # notes are never scanned for option words.
        if not grouped and nonempty(response.get("answer_text")):
            for segment in re.split(r"[;\uff1b\r\n]+", response["answer_text"]):
                match = re.match(r"^\s*([^:：]+?)\s*[:：]\s*(.*?)\s*$", segment)
                if match:
                    findings.extend(add_itemized_field(
                        grouped, match.group(1), match.group(2), "multi", owner
                    ))
            if not grouped:
                findings.append(f"{owner}: itemized answer_text has no labelled field/value segments")
        if not grouped:
            findings.append(f"{owner}: itemized response must contain at least one field/value")

        for group in grouped.values():
            reason = option_conflict(group["values"], group["mode"])
            if reason:
                findings.append(f"{owner} field {group['label']!r}: {reason}")
        return findings

    responses = collection("questionnaire_responses")
    for response in responses:
        if not isinstance(response, dict):
            continue
        owner = f"questionnaire response {response.get('question_key')}"
        mode = response.get("mode", "multi")
        if mode == "itemized":
            reasons = itemized_conflicts(response, owner)
        else:
            selected = response.get("selected", [])
            reasons = []
            if not isinstance(selected, list) or not selected:
                # ``selected`` is structurally required by the schema, but an
                # empty list is still an unanswered business question.  Do not
                # let it masquerade as a completed self-check.
                reasons.append(f"{owner}: selected must contain at least one option")
            if isinstance(selected, list) and any(isinstance(item, dict) for item in selected):
                reasons.append(f"{owner}: structured field/value selections require mode=itemized")
            reason = option_conflict(selected if isinstance(selected, list) else [], str(mode))
            if reason:
                reasons.append(f"{owner}: {reason}")
        for reason in reasons:
            errors.append(reason)
            if response.get("conflict_status") != "resolved":
                warnings.append(f"{reason}; request correction before assessment")
        if reasons and response.get("conflict_status") == "resolved":
            errors.append(f"{owner}: conflict_status=resolved but selections still conflict")

    required_layers = {
        "layer1_ai_transparency",
        "layer2_eu_ai_act_system_model",
        "layer3_dataflow_adjacent",
    }
    layer_results = collection("layer_results")
    seen_layers = [
        item.get("layer") for item in layer_results
        if isinstance(item, dict) and isinstance(item.get("layer"), str)
    ]
    if set(seen_layers) != required_layers or len(seen_layers) != len(required_layers):
        errors.append(
            "layer_results: exactly one result is required for each of the three fixed layers"
        )
    raw_scope_layers = scope.get("layers", [])
    scope_layers = {
        value for value in raw_scope_layers
        if isinstance(value, str)
    } if isinstance(raw_scope_layers, list) else set()
    if scope_layers != required_layers:
        errors.append(
            "scope.layers: all three fixed layers must be recorded; use not_assessed for a deferred layer"
        )

    def action_layers(action: dict[str, Any]) -> set[str]:
        explicit = action.get("layer")
        if nonempty(explicit):
            return {str(explicit)}
        inferred: set[str] = set()
        for ref in action.get("related_obligation_ids", []) or []:
            if not isinstance(ref, str):
                continue
            layer = obligations.get(ref, {}).get("layer")
            if nonempty(layer):
                inferred.add(str(layer))
        for ref in action.get("related_risk_ids", []) or []:
            if not isinstance(ref, str):
                continue
            layer = risks.get(ref, {}).get("layer")
            if nonempty(layer):
                inferred.add(str(layer))
        return inferred

    for item in layer_results:
        if not isinstance(item, dict):
            continue
        layer = item.get("layer")
        owner = f"layer result {layer}"
        if item.get("status") == "not_assessed" and not nonempty(item.get("notes")):
            errors.append(f"{owner}: not_assessed requires a reason in notes")
        if item.get("status") in {"not_ready", "high_risk", "insufficient_information"} and item.get("risk_level") in {"low", "info"}:
            errors.append(f"{owner}: status and risk_level are inconsistent")
        for field, known, label in (
            ("obligation_ids", obligations, "obligation"),
            ("risk_ids", risks, "risk"),
            ("action_ids", actions, "action"),
        ):
            values = item.get(field, [])
            if not isinstance(values, list):
                continue
            for ref in values:
                if not isinstance(ref, str) or not ref.strip():
                    errors.append(f"{owner}: invalid {label} reference {ref!r}")
                    continue
                entity = known.get(ref)
                if entity is None:
                    errors.append(f"{owner}: unknown {label} reference {ref!r}")
                    continue
                entity_layers = action_layers(entity) if label == "action" else {entity.get("layer")}
                entity_layers.discard(None)
                entity_layers.discard("")
                if not entity_layers:
                    errors.append(
                        f"{owner}: {label} {ref!r} has no determinable layer"
                    )
                elif len(entity_layers) > 1:
                    errors.append(
                        f"{owner}: {label} {ref!r} spans multiple layers {sorted(entity_layers)}"
                    )
                elif layer not in entity_layers:
                    errors.append(
                        f"{owner}: {label} {ref!r} belongs to {next(iter(entity_layers))!r}"
                    )

    # Every stable data-flow number must carry the GDPR role chain and the
    # transfer audit fields.  Empty arrays are not an auditable answer: use an
    # explicit value such as “none_identified” or “not_applicable”.
    flow_numbers: set[str] = set()
    incomplete_transfer_flows: list[dict[str, Any]] = []
    transfer_issue_reasons: dict[str, list[str]] = {}

    # These markers are deliberately kept separate from ordinary free-text
    # values.  A business answer such as "待核实" is a valid pending answer,
    # but it cannot be used as proof that a transfer role or recipient has been
    # identified in a strict, launch-ready assessment.
    unresolved_transfer_markers = {
        "unknown", "uncertain", "待核实", "不确定", "事实待核实", "尚未决定",
        "未确认", "未明确", "待确认", "tbd", "n/a?",
    }
    explicit_no_subprocessor_markers = {
        "none", "none_identified", "no subprocessor", "no subprocessors",
        "无", "无子处理者", "未使用子处理者", "不适用", "not_applicable",
    }

    def transfer_marker(value: Any) -> str:
        return str(value).strip().casefold()

    def is_unresolved_transfer_value(value: Any) -> bool:
        normalized = transfer_marker(value)
        if not normalized:
            return True
        return normalized in unresolved_transfer_markers or any(
            normalized.startswith(prefix + suffix)
            for prefix in unresolved_transfer_markers
            for suffix in (" ", "(", "（", ":", "：", "-", ",", "，")
        )

    def is_explicit_role_entry(value: Any) -> bool:
        """Recognise a role ID or an explicit role label, never a vendor name."""

        if not nonempty(value):
            return False
        if str(value) in roles:
            return True
        normalized = transfer_marker(value)
        role_terms = (
            "controller", "processor", "subprocessor", "joint controller",
            "data controller", "data processor", "数据控制者", "数据处理者",
            "共同控制者", "子处理者", "控制者", "处理者",
        )
        return any(term in normalized for term in role_terms)

    def looks_like_cross_border(flow: dict[str, Any]) -> bool:
        """Conservatively identify a flow requiring transfer review.

        A positive remote-access answer is enough to require the review.  For
        flows without that answer, explicit third-country/foreign destination
        wording is treated as a trigger.  We intentionally do not infer a
        country from a vendor or model brand name.
        """

        if flow.get("remote_access") in {"yes", "unknown"}:
            # Unknown remote access is itself a transfer trigger for the strict
            # path.  A platform cannot establish that a flow stays in the EEA
            # merely by leaving the vendor's access architecture unanswered.
            return True
        text = " ".join(str(value) for value in flow.get("destinations", [])).casefold()
        markers = (
            "第三国", "境外", "海外", "跨境", "远程访问", "remote", "overseas",
            "cross-border", "outside eu", "non-eea", "united states", "u.s.",
            "us model", "美国", "中国", "india", "singapore", "japan", "korea",
        )
        return any(marker in text for marker in markers)

    def transfer_issues(flow: dict[str, Any]) -> list[str]:
        if not looks_like_cross_border(flow):
            return []
        issues: list[str] = []
        mechanism = flow.get("transfer_mechanism", [])
        if not isinstance(mechanism, list):
            issues.append("transfer mechanism is not a list")
            mechanism = []
        meaningful_mechanisms = {
            str(item).strip().casefold()
            for item in mechanism
            if nonempty(item)
        } - {"unknown", "none", "not_applicable"}
        if not meaningful_mechanisms:
            issues.append("no identified transfer mechanism")
        if flow.get("tia_status") != "completed":
            issues.append("TIA is not completed")
        if strict:
            remote_access = flow.get("remote_access")
            if remote_access == "unknown":
                issues.append("remote_access is unknown; verify every support, backup and administrator path")

            destinations = flow.get("destinations", [])
            if not isinstance(destinations, list) or not destinations:
                issues.append("recipient/destination is not identified")
            elif any(is_unresolved_transfer_value(item) for item in destinations):
                issues.append("recipient/destination contains an unresolved value")

            role_entries = flow.get("controller_processor_roles", [])
            if not isinstance(role_entries, list) or not role_entries:
                issues.append("controller/processor role chain is not identified")
            else:
                explicit_roles = [item for item in role_entries if is_explicit_role_entry(item)]
                if not explicit_roles:
                    issues.append("controller/processor role chain is not explicit")
                for role_id in explicit_roles:
                    if str(role_id) in roles:
                        role_record = roles[str(role_id)]
                        if role_record.get("determination") in {"unknown", "conditional"}:
                            issues.append(f"role {role_id!r} is unresolved")
                if any(is_unresolved_transfer_value(item) for item in role_entries):
                    issues.append("controller/processor role chain contains an unresolved value")

            subprocessors = flow.get("subprocessors", [])
            if not isinstance(subprocessors, list) or not subprocessors:
                issues.append("subprocessor chain is not identified")
            elif all(is_unresolved_transfer_value(item) for item in subprocessors):
                # An explicit statement that there are no subprocessors is
                # acceptable; an unanswered placeholder is not.
                if not any(transfer_marker(item) in explicit_no_subprocessor_markers for item in subprocessors):
                    issues.append("subprocessor chain is unresolved")

            recipient_control = flow.get("recipient_control")
            if recipient_control in {None, "unknown", "not_applicable"}:
                issues.append("recipient control role is unknown")
        # A completed TIA cannot cure the absence of a lawful transfer tool.
        # Conversely, an identified tool without a completed TIA remains an
        # open verification item for a third-country AI platform flow.
        return issues
    for flow in collection("data_flows"):
        if not isinstance(flow, dict):
            continue
        number = flow.get("flow_number")
        if not nonempty(number):
            errors.append(f"data flow {flow.get('id')}: flow_number is required")
        elif number in flow_numbers:
            errors.append(f"data_flows: duplicate flow_number {number!r}")
        else:
            flow_numbers.add(str(number))
        for field in ("controller_processor_roles", "subprocessors", "transfer_mechanism", "evidence_ids"):
            value = flow.get(field)
            if not isinstance(value, list) or not value or any(not nonempty(entry) for entry in value):
                errors.append(f"data flow {flow.get('id')}: {field} must explicitly record a non-empty value")
        flow_evidence = flow.get("evidence_ids", [])
        if isinstance(flow_evidence, list):
            for ref in flow_evidence:
                if not isinstance(ref, str) or ref not in evidence:
                    errors.append(
                        f"data flow {flow.get('id')}: unknown evidence reference {ref!r}"
                    )
        if flow.get("remote_access") == "unknown" and flow.get("tia_status") == "completed":
            errors.append(f"data flow {flow.get('id')}: completed TIA cannot coexist with unknown remote_access")
        if any(item in {"unknown", "none", "not_applicable"} for item in flow.get("transfer_mechanism", [])) and flow.get("tia_status") == "completed":
            warnings.append(f"data flow {flow.get('id')}: mechanism is unknown/none; verify the completed TIA record")
        issues = transfer_issues(flow)
        if issues:
            incomplete_transfer_flows.append(flow)
            transfer_issue_reasons[str(flow.get("id"))] = issues

    def refs(items: list[str], known: dict[str, Any], label: str, owner: str) -> None:
        if items is None:
            return
        if not isinstance(items, list):
            errors.append(f"{owner}: {label} references must be an array")
            return
        for ref in items:
            if not isinstance(ref, str) or not ref.strip():
                errors.append(f"{owner}: invalid {label} reference {ref!r}")
            elif ref not in known:
                errors.append(f"{owner}: unknown {label} reference {ref!r}")

    for fact in collection("facts"):
        if not isinstance(fact, dict):
            continue
        if fact.get("status") in {"unknown", "pending_verification", "contradictory"} and fact.get("uncertainty_policy") not in {"strict_default", "conditional", "block_until_verified"}:
            errors.append(f"fact {fact.get('id')}: unresolved fact needs uncertainty_policy")
        if fact.get("status") in {"unknown", "pending_verification", "contradictory"} and fact.get("strict_assumption") is not True:
            errors.append(f"fact {fact.get('id')}: unresolved fact must set strict_assumption=true")
        refs(fact.get("source_evidence_ids", []), evidence, "evidence", f"fact {fact.get('id')}")
        if fact.get("status") == "confirmed":
            value = fact.get("value")
            has_value = value is not None and (
                not isinstance(value, str) or bool(value.strip())
            ) and (
                not isinstance(value, (list, dict, tuple, set)) or bool(value)
            )
            source_ids = fact.get("source_evidence_ids", [])
            has_evidence = isinstance(source_ids, list) and any(nonempty(item) for item in source_ids)
            if not has_value and not has_evidence:
                errors.append(
                    f"fact {fact.get('id')}: confirmed fact needs a value or source evidence"
                )
        selected = fact.get("selected_options")
        if isinstance(selected, list):
            fact_owner = f"fact {fact.get('id')}"
            if fact.get("selection_mode") == "itemized":
                errors.extend(itemized_conflicts({"selected": selected}, fact_owner))
            else:
                if any(isinstance(item, dict) for item in selected):
                    errors.append(
                        f"{fact_owner}: structured field/value selections require selection_mode=itemized"
                    )
                reason = option_conflict(selected, fact.get("selection_mode", "multi"))
                if reason:
                    errors.append(f"{fact_owner}: {reason}")
        if fact.get("status") in {"unknown", "pending_verification", "contradictory"}:
            if not fact.get("verification_owner"):
                errors.append(f"fact {fact.get('id')}: unresolved fact needs verification_owner")
            if not fact.get("required_evidence"):
                errors.append(f"fact {fact.get('id')}: unresolved fact needs required_evidence")
            if not isinstance(fact.get("launch_blocker"), bool):
                errors.append(f"fact {fact.get('id')}: unresolved fact needs launch_blocker=true/false")

    for law in collection("laws"):
        if not isinstance(law, dict):
            continue
        source = law.get("source_type")
        label = law.get("normativity_label")
        binding = law.get("binding")
        if source in {"official_guidance", "cop"} and label != "欧盟建议的良好实践/解释性材料":
            errors.append(f"law {law.get('id')}: guidance/CoP must be labelled as EU recommended good practice/interpretive material")
        if source == "voluntary_standard" and label != "自愿性标准":
            errors.append(f"law {law.get('id')}: voluntary standard has incorrect normativity label")
        if source in {"binding_law", "delegated_act", "implementing_act"} and label != "强制性法规":
            errors.append(f"law {law.get('id')}: enacted EU/CN/US law must be labelled as mandatory law")
        if source in {"binding_law", "delegated_act", "implementing_act"} and binding is not True:
            errors.append(f"law {law.get('id')}: enacted law must have binding=true")
        if source == "secondary" and label != "二手资料":
            errors.append(f"law {law.get('id')}: secondary source must be labelled as secondary material")
        if source in {"official_guidance", "cop", "voluntary_standard"} and binding:
            errors.append(f"law {law.get('id')}: non-binding guidance/standard cannot have binding=true")
        if source == "secondary" and binding:
            errors.append(f"law {law.get('id')}: secondary material cannot have binding=true")
        if source == "proposal" or law.get("legal_status") == "draft":
            if binding is True:
                errors.append(
                    f"law {law.get('id')}: proposal/draft cannot be marked binding=true"
                )
            if label == "强制性法规":
                errors.append(
                    f"law {law.get('id')}: proposal/draft cannot use the mandatory-law label"
                )
        if law.get("legal_status") in {"future", "draft", "unknown"}:
            warnings.append(f"law {law.get('id')}: legal status is {law.get('legal_status')}; do not state as current law")
        if law.get("legal_status") in {"superseded", "expired"}:
            warnings.append(f"law {law.get('id')}: legal status is {law.get('legal_status')}; it cannot support a current mandatory conclusion")

    for role in collection("roles"):
        if not isinstance(role, dict):
            continue
        refs(role.get("fact_ids", []), facts, "fact", f"role {role.get('id')}")
        if role.get("determination") == "confirmed":
            for field in ("fact_ids", "definition_anchors", "duty_anchors"):
                values = role.get(field)
                if not isinstance(values, list) or not values or any(not nonempty(item) for item in values):
                    errors.append(
                        f"role {role.get('id')}: confirmed role needs non-empty {field}"
                    )
        if role.get("determination") in {"unknown", "conditional"} and not role.get("strict_trigger"):
            errors.append(f"role {role.get('id')}: unresolved role must carry strict_trigger=true")

    for obligation in collection("obligations"):
        if not isinstance(obligation, dict):
            continue
        oid = obligation.get("id")
        law_id = obligation.get("law_id")
        audit_fields = {
            "legal_basis": obligation.get("legal_basis"),
            "effect_type": obligation.get("effect_type"),
            "effective_date": obligation.get("effective_date"),
            "responsible_role_ids": obligation.get("responsible_role_ids"),
            "consequence": obligation.get("consequence"),
            "gap": obligation.get("gap"),
            "completion_criteria": obligation.get("completion_criteria"),
            "verification_owner": obligation.get("verification_owner"),
            "required_evidence": obligation.get("required_evidence"),
            "launch_blocker": obligation.get("launch_blocker"),
        }
        for field, value in audit_fields.items():
            if field in {"legal_basis", "responsible_role_ids", "required_evidence"}:
                if not isinstance(value, list) or not value or any(not nonempty(entry) for entry in value):
                    errors.append(f"obligation {oid}: {field} is required for auditability")
            elif field == "launch_blocker":
                if not isinstance(value, bool):
                    errors.append(f"obligation {oid}: launch_blocker must be true or false")
            elif field == "effective_date":
                if not is_iso_date(value):
                    errors.append(f"obligation {oid}: effective_date must be an ISO date")
            elif not nonempty(value):
                errors.append(f"obligation {oid}: {field} is required for auditability")
        if not isinstance(law_id, str) or law_id not in laws:
            errors.append(f"obligation {oid}: unknown law_id {law_id!r}")
        refs(obligation.get("responsible_role_ids", []), roles, "role", f"obligation {oid}")
        refs(obligation.get("evidence_required", []), evidence, "evidence", f"obligation {oid}")
        refs(obligation.get("required_evidence", []), evidence, "evidence", f"obligation {oid}")
        legal_basis = obligation.get("legal_basis", [])
        linked_law = laws.get(law_id, {}) if isinstance(law_id, str) else {}
        if isinstance(legal_basis, list):
            for basis in legal_basis:
                if not law_reference_matches(basis, linked_law):
                    errors.append(
                        f"obligation {oid}: legal_basis reference {basis!r} does not match law {law_id!r}"
                    )
        app = obligation.get("applicability", {})
        if not isinstance(app, dict):
            errors.append(f"obligation {oid}: applicability must be an object")
            app = {}
        refs(app.get("trigger_fact_ids", []), facts, "fact", f"obligation {oid}")
        law = linked_law
        if law.get("source_type") == "proposal" or law.get("legal_status") == "draft":
            if obligation.get("effect_type") == "binding_law":
                errors.append(
                    f"obligation {oid}: proposal/draft law cannot create binding_law effect"
                )
            if obligation.get("normativity") == "mandatory":
                errors.append(
                    f"obligation {oid}: proposal/draft law cannot create mandatory normativity"
                )
        if law.get("source_type") in {"official_guidance", "cop", "voluntary_standard"} and obligation.get("normativity") == "mandatory":
            errors.append(f"obligation {oid}: guidance/CoP/standard cannot create mandatory normativity")
        if law.get("source_type") == "secondary" and (
            obligation.get("effect_type") == "binding_law" or obligation.get("normativity") == "mandatory"
        ):
            errors.append(f"obligation {oid}: secondary material cannot support a current mandatory obligation")
        if law.get("legal_status") in {"superseded", "expired", "draft", "future", "unknown"} and (
            obligation.get("effect_type") == "binding_law" or obligation.get("normativity") == "mandatory"
        ):
            errors.append(
                f"obligation {oid}: non-current law {law_id!r} cannot support a current mandatory obligation"
            )
        if obligation.get("effect_type") == "eu_good_practice" and obligation.get("normativity") == "mandatory":
            errors.append(f"obligation {oid}: eu_good_practice cannot have mandatory normativity")
        if obligation.get("effect_type") == "binding_law" and obligation.get("normativity") != "mandatory":
            errors.append(f"obligation {oid}: binding law must have mandatory normativity")
        trigger_fact_ids = app.get("trigger_fact_ids", [])
        if not isinstance(trigger_fact_ids, list):
            trigger_fact_ids = []
        unresolved = any(
            isinstance(fid, str)
            and facts.get(fid, {}).get("status")
            in {"unknown", "pending_verification", "contradictory"}
            for fid in trigger_fact_ids
        )
        if unresolved:
            if app.get("status") == "applicable":
                errors.append(f"obligation {oid}: unresolved trigger fact cannot yield unconditional applicable status")
            if app.get("uncertainty_treatment") not in {"strict_default_warning", "conditional_obligation", "block_until_verified"}:
                errors.append(f"obligation {oid}: unresolved trigger needs conditional/strict-default treatment")
            if app.get("strict_default_applied") is not True:
                errors.append(f"obligation {oid}: unresolved trigger must set strict_default_applied=true")
        needs_verification = (
            app.get("status") in {"unknown", "conditional"}
            or obligation.get("status") in {"needs_verification", "blocked"}
        )
        if needs_verification:
            if not obligation.get("verification_owner"):
                errors.append(f"obligation {oid}: unresolved obligation needs verification_owner")
            required_evidence = obligation.get("required_evidence") or obligation.get("evidence_required")
            if not required_evidence:
                errors.append(f"obligation {oid}: unresolved obligation needs required_evidence")
            if not isinstance(obligation.get("launch_blocker"), bool):
                errors.append(f"obligation {oid}: unresolved obligation needs launch_blocker=true/false")

    for control in collection("transparency_controls"):
        if not isinstance(control, dict):
            continue
        refs(control.get("evidence_ids", []), evidence, "evidence", f"transparency control {control.get('id')}")
        if not isinstance(control.get("content_types"), list) or not control.get("content_types"):
            errors.append(f"transparency control {control.get('id')}: at least one content type is required")
        if control.get("status") == "implemented" and control.get("persistence_test_status") != "passed":
            errors.append(f"transparency control {control.get('id')}: implemented control needs a passed persistence test")
        if control.get("status") in {"partial", "planned", "not_implemented", "unknown"}:
            if not control.get("failure_handling"):
                errors.append(
                    f"transparency control {control.get('id')}: incomplete control needs failure_handling"
                )
            if not control.get("persistence_test_scope"):
                errors.append(
                    f"transparency control {control.get('id')}: incomplete control needs persistence_test_scope"
                )

    for risk in collection("risks"):
        if not isinstance(risk, dict):
            continue
        refs(risk.get("impacted_law_ids", []), laws, "law", f"risk {risk.get('id')}")
        refs(risk.get("basis", []), obligations | facts, "obligation/fact", f"risk {risk.get('id')}")

    for action in collection("actions"):
        if not isinstance(action, dict):
            continue
        refs(action.get("related_obligation_ids", []), obligations, "obligation", f"action {action.get('id')}")
        refs(action.get("related_risk_ids", []), risks, "risk", f"action {action.get('id')}")
        refs(action.get("evidence_ids", []), evidence, "evidence", f"action {action.get('id')}")
        linked_layers = {
            item.get("layer")
            for ref in action.get("related_obligation_ids", []) or []
            if isinstance(ref, str)
            for item in [obligations.get(ref, {})]
            if nonempty(item.get("layer"))
        } | {
            item.get("layer")
            for ref in action.get("related_risk_ids", []) or []
            if isinstance(ref, str)
            for item in [risks.get(ref, {})]
            if nonempty(item.get("layer"))
        }
        if len(linked_layers) > 1:
            errors.append(
                f"action {action.get('id')}: related obligations/risks span multiple layers {sorted(linked_layers)}"
            )
        if nonempty(action.get("layer")):
            mismatches = linked_layers - {action.get("layer")}
            if mismatches:
                errors.append(
                    f"action {action.get('id')}: layer {action.get('layer')!r} conflicts with related layer(s) {sorted(mismatches)}"
                )
        if action.get("blocks_launch") is True and action.get("status") in {"open", "in_progress", "blocked"}:
            action_evidence = action.get("evidence_ids")
            if not isinstance(action_evidence, list) or not any(nonempty(item) for item in action_evidence):
                errors.append(
                    f"action {action.get('id')}: open launch-blocking action needs evidence_ids"
                )

    # A mitigated/non-blocking risk must not coexist with an unfinished action
    # that still declares the same risk blocks launch.  Otherwise a report can
    # silently present the risk as closed while its required control remains
    # outstanding.
    for risk in collection("risks"):
        if not isinstance(risk, dict) or risk.get("status") != "mitigated" or risk.get("blocking") is not False:
            continue
        risk_id = risk.get("id")
        for action in collection("actions"):
            if not isinstance(action, dict):
                continue
            related = action.get("related_risk_ids", [])
            if risk_id in related and action.get("status") in {"open", "in_progress", "blocked"} and action.get("blocks_launch") is True:
                errors.append(
                    f"risk {risk_id}: mitigated/non-blocking conflicts with open launch-blocking action {action.get('id')}"
                )

    conclusion = data.get("conclusion", {})
    if not isinstance(conclusion, dict):
        conclusion = {}
    mode = assessment_mode(data)
    unresolved_ids = {
        str(fact["id"])
        for fact in collection("facts")
        if isinstance(fact, dict)
        and fact.get("status") in {"unknown", "pending_verification", "contradictory"}
        and nonempty(fact.get("id"))
    }
    raw_listed_unknowns = conclusion.get("unknown_fact_ids", [])
    if isinstance(raw_listed_unknowns, list):
        listed_unknowns = {
            value for value in raw_listed_unknowns
            if isinstance(value, str)
        }
        for value in raw_listed_unknowns:
            if not isinstance(value, str):
                errors.append(f"conclusion: unknown_fact_ids contains non-string value {value!r}")
    else:
        listed_unknowns = set()
    missing_unknowns = unresolved_ids - listed_unknowns
    if missing_unknowns:
        errors.append(f"conclusion: unknown_fact_ids omits unresolved facts {sorted(missing_unknowns)}")
    extra_unknowns = listed_unknowns - unresolved_ids
    if extra_unknowns:
        confirmed_or_resolved = extra_unknowns & set(facts)
        nonexistent = extra_unknowns - set(facts)
        if confirmed_or_resolved:
            errors.append(
                "conclusion: unknown_fact_ids includes facts that are not unresolved "
                f"{sorted(confirmed_or_resolved)}"
            )
        if nonexistent:
            errors.append(
                f"conclusion: unknown_fact_ids includes nonexistent facts {sorted(nonexistent)}"
            )
    # Blocking references are an auditable contract, not free-form labels.  A
    # launch gate must point to an open risk/action/obligation/fact that really
    # declares itself blocking; otherwise a report can hide an unresolved issue
    # by using a made-up identifier or by listing a closed item.
    raw_blocking = conclusion.get("blocking_issue_ids", [])
    if not isinstance(raw_blocking, list):
        errors.append("conclusion: blocking_issue_ids must be an array")
        raw_blocking = []
    blocking_entities = {
        **{key: ("risk", value) for key, value in risks.items()},
        **{key: ("action", value) for key, value in actions.items()},
        **{key: ("obligation", value) for key, value in obligations.items()},
        **{key: ("fact", value) for key, value in facts.items()},
    }
    for issue_id in raw_blocking:
        if not isinstance(issue_id, str) or issue_id not in blocking_entities:
            errors.append(f"conclusion: blocking_issue_ids contains unknown id {issue_id!r}")
            continue
        kind, entity = blocking_entities[issue_id]
        enforce_open_state = bool(strict) or conclusion.get("launch_decision") in {"go", "go_with_conditions"}
        if kind == "risk":
            if enforce_open_state and (entity.get("blocking") is not True or entity.get("status") in {"mitigated", "accepted"}):
                errors.append(f"conclusion: blocking risk {issue_id!r} is not open and blocking")
        elif kind == "action":
            if enforce_open_state and (entity.get("blocks_launch") is not True or entity.get("status") not in {"open", "in_progress", "blocked"}):
                errors.append(f"conclusion: blocking action {issue_id!r} is not an open launch blocker")
        elif kind == "obligation":
            if enforce_open_state and (entity.get("launch_blocker") is not True or entity.get("status") in {"complete", "not_applicable"}):
                errors.append(f"conclusion: blocking obligation {issue_id!r} is not an outstanding launch blocker")
        elif kind == "fact":
            if enforce_open_state and (entity.get("launch_blocker") is not True or entity.get("status") not in {"unknown", "pending_verification", "contradictory"}):
                errors.append(f"conclusion: blocking fact {issue_id!r} is not an unresolved launch blocker")

    raw_unverified_materials = conclusion.get("unverified_materials", [])
    if not isinstance(raw_unverified_materials, list):
        errors.append("conclusion: unverified_materials must be an array")
    else:
        for material_id in raw_unverified_materials:
            if not isinstance(material_id, str) or material_id not in evidence:
                errors.append(
                    f"conclusion: unverified_materials contains unknown evidence id {material_id!r}"
                )

    # Keep an open blocking risk/action from disappearing merely because the
    # conclusion's list is empty.  This is especially important for generated
    # reports that otherwise say “compliant” or “go”.
    open_blocking_risks = [
        risk for risk in collection("risks")
        if isinstance(risk, dict)
        and risk.get("blocking") is True
        and risk.get("status") in {"open", "unknown"}
    ]
    open_blocking_actions = [
        action for action in collection("actions")
        if isinstance(action, dict)
        and action.get("blocks_launch") is True
        and action.get("status") in {"open", "in_progress", "blocked"}
    ]
    if strict and (open_blocking_risks or open_blocking_actions) and (
        conclusion.get("overall_status") in {"compliant", "conditionally_compliant"}
        or conclusion.get("launch_decision") in {"go", "go_with_conditions"}
    ):
        errors.append(
            "conclusion: open blocking risks/actions are incompatible with a compliant or launch-ready conclusion"
        )

    unresolved_roles = [
        role for role in collection("roles")
        if isinstance(role, dict) and role.get("determination") in {"unknown", "conditional"}
    ]
    if strict and unresolved_roles and (
        conclusion.get("overall_status") in {"compliant", "conditionally_compliant"}
        or conclusion.get("launch_decision") in {"go", "go_with_conditions"}
    ):
        errors.append(
            "conclusion: unresolved controller/provider/deployer role cannot support a launch-ready conclusion"
        )
    if unresolved_ids and conclusion.get("overall_status") == "compliant":
        errors.append("conclusion: unconditional compliant status is not allowed while material facts remain unresolved")
    if conclusion.get("overall_status") == "compliant" and conclusion.get("launch_decision") == "hold":
        errors.append("conclusion: compliant status conflicts with launch_decision=hold")
    overall = conclusion.get("overall_status")
    launch = conclusion.get("launch_decision")
    risk_level = conclusion.get("risk_level")

    # A structural record can otherwise claim ``compliant/go`` while carrying
    # only a token fact and an unconnected evidence item.  A launch-ready
    # conclusion is therefore an auditable assertion, not merely an enum
    # value: it needs a current mandatory legal anchor, a confirmed business
    # fact, a determined role, coverage for each fixed layer, and an evidence
    # chain through the obligations.  Incomplete/hold records remain usable
    # for staged questionnaire collection and migration.
    launch_ready_claim = (
        overall in {"compliant", "conditionally_compliant"}
        or launch in {"go", "go_with_conditions"}
    )
    if strict and launch_ready_claim:
        confirmed_facts = [
            fact for fact in collection("facts")
            if isinstance(fact, dict)
            and fact.get("status") == "confirmed"
            and (
                (fact.get("value") is not None and (
                    not isinstance(fact.get("value"), str)
                    or bool(fact.get("value").strip())
                ))
                or any(nonempty(ref) for ref in fact.get("source_evidence_ids", []) or [])
            )
        ]
        if not confirmed_facts:
            errors.append(
                "conclusion: launch-ready conclusion requires at least one confirmed business fact with a value or evidence"
            )

        current_binding_laws = {
            str(law.get("id")): law
            for law in collection("laws")
            if isinstance(law, dict)
            and law.get("legal_status") == "current"
            and law.get("binding") is True
            and law.get("source_type") in {"binding_law", "delegated_act", "implementing_act"}
            and nonempty(law.get("id"))
        }
        if not current_binding_laws:
            errors.append(
                "conclusion: launch-ready conclusion requires at least one current binding law record"
            )

        confirmed_roles = {
            str(role.get("id")): role
            for role in collection("roles")
            if isinstance(role, dict)
            and role.get("determination") == "confirmed"
            and nonempty(role.get("id"))
        }
        if not confirmed_roles:
            errors.append(
                "conclusion: launch-ready conclusion requires at least one confirmed legal/business role"
            )

        layer_records = {
            item.get("layer"): item
            for item in layer_results
            if isinstance(item, dict) and nonempty(item.get("layer"))
        }
        covered_obligation_ids: set[str] = set()
        for layer in sorted(required_layers):
            result = layer_records.get(layer)
            if not isinstance(result, dict):
                errors.append(f"layer result {layer}: launch-ready conclusion has no layer record")
                continue
            if result.get("status") not in {"compliant", "conditionally_compliant"}:
                errors.append(
                    f"layer result {layer}: launch-ready conclusion requires an assessed compliant or conditionally_compliant status"
                )
            if result.get("risk_level") in {"critical", "high", "unknown"} and result.get("status") in {"compliant", "conditionally_compliant"}:
                errors.append(
                    f"layer result {layer}: launch-ready conclusion cannot carry risk_level={result.get('risk_level')!r}"
                )
            obligation_ids = result.get("obligation_ids", [])
            if not isinstance(obligation_ids, list):
                obligation_ids = []
            valid_obligations = [
                str(item) for item in obligation_ids
                if isinstance(item, str) and item in obligations
            ]
            covered_obligation_ids.update(valid_obligations)
            if not valid_obligations:
                errors.append(
                    f"layer result {layer}: launch-ready conclusion needs at least one linked obligation; record an explicit not_applicable obligation when no duty is triggered"
                )

        if not covered_obligation_ids:
            errors.append(
                "conclusion: launch-ready conclusion requires an obligation-to-law coverage chain; empty obligation arrays are not an assessment"
            )

        current_binding_obligations = []
        referenced_evidence_ids: set[str] = set()
        for oid in sorted(covered_obligation_ids):
            obligation = obligations.get(oid, {})
            if not isinstance(obligation, dict):
                continue
            law_id = obligation.get("law_id")
            law = laws.get(law_id, {}) if isinstance(law_id, str) else {}
            if (
                isinstance(law, dict)
                and law.get("legal_status") == "current"
                and law.get("binding") is True
                and law.get("source_type") in {"binding_law", "delegated_act", "implementing_act"}
            ):
                current_binding_obligations.append(obligation)

            role_ids = obligation.get("responsible_role_ids", [])
            if not isinstance(role_ids, list) or not role_ids:
                errors.append(f"obligation {oid}: launch-ready coverage needs responsible role IDs")
            else:
                for role_id in role_ids:
                    role = roles.get(role_id) if isinstance(role_id, str) else None
                    if not isinstance(role, dict):
                        continue
                    if role.get("determination") != "confirmed":
                        errors.append(
                            f"obligation {oid}: launch-ready coverage requires confirmed responsible role {role_id!r}"
                        )

            required_ids = obligation.get("required_evidence", [])
            evidence_ids = obligation.get("evidence_required", [])
            if isinstance(required_ids, list):
                referenced_evidence_ids.update(
                    str(ref) for ref in required_ids if isinstance(ref, str) and ref in evidence
                )
            if isinstance(evidence_ids, list):
                referenced_evidence_ids.update(
                    str(ref) for ref in evidence_ids if isinstance(ref, str) and ref in evidence
                )
            if not required_ids and not evidence_ids:
                errors.append(
                    f"obligation {oid}: launch-ready coverage needs at least one evidence reference"
                )

            if launch == "go" or overall == "compliant":
                if obligation.get("status") not in {"complete", "not_applicable"}:
                    errors.append(
                        f"obligation {oid}: compliant/go conclusion requires status=complete or not_applicable"
                    )
                applicability = obligation.get("applicability", {})
                if isinstance(applicability, dict) and applicability.get("status") in {"unknown", "conditional"}:
                    errors.append(
                        f"obligation {oid}: compliant/go conclusion cannot rely on unknown or conditional applicability"
                    )

        if not current_binding_obligations:
            errors.append(
                "conclusion: launch-ready conclusion requires at least one covered obligation linked to a current binding law"
            )
        if not referenced_evidence_ids:
            errors.append(
                "conclusion: launch-ready conclusion requires evidence references attached to covered obligations"
            )
        if launch == "go":
            unverified_required = [
                ref for ref in sorted(referenced_evidence_ids)
                if evidence.get(ref, {}).get("verification_status") != "verified"
            ]
            if unverified_required:
                errors.append(
                    "conclusion: go requires verified evidence for every covered obligation; "
                    f"unverified evidence={unverified_required}"
                )

    all_layers_not_assessed = (
        len(layer_results) == 3
        and all(
            isinstance(item, dict) and item.get("status") == "not_assessed"
            for item in layer_results
        )
    )
    unassessed_layers = [
        item for item in layer_results
        if isinstance(item, dict) and item.get("status") == "not_assessed"
    ]
    if strict and unassessed_layers and (
        overall in {"compliant", "conditionally_compliant"}
        or launch in {"go", "go_with_conditions"}
    ):
        errors.append(
            "conclusion: a not_assessed layer cannot support a launch-ready conclusion"
        )
    if all_layers_not_assessed and overall == "compliant" and launch == "go":
        errors.append(
            "conclusion: all three layers are not_assessed; compliant + go requires completed layer assessments"
        )
    if incomplete_transfer_flows and (
        overall in {"compliant", "conditionally_compliant"}
        or launch in {"go", "go_with_conditions"}
    ):
        flow_ids = [str(flow.get("id")) for flow in incomplete_transfer_flows]
        reason_summary = {
            flow_id: transfer_issue_reasons.get(flow_id, [])
            for flow_id in flow_ids
        }
        errors.append(
            "conclusion: explicit remote access with no transfer mechanism or unfinished TIA; "
            "cross-border AI-platform flows with an incomplete transfer mechanism/TIA "
            f"for {flow_ids} cannot be compliant or launch-ready; "
            f"unresolved flow checks={reason_summary}; create a flow-specific risk/action and hold launch"
        )
    if strict and incomplete_transfer_flows:
        layer3_blocking_risks = [
            risk for risk in collection("risks")
            if isinstance(risk, dict)
            and risk.get("layer") == "layer3_dataflow_adjacent"
            and risk.get("blocking") is True
        ]
        layer3_blocking_actions = [
            action for action in collection("actions")
            if isinstance(action, dict)
            and action.get("blocks_launch") is True
            and action.get("layer", "layer3_dataflow_adjacent") == "layer3_dataflow_adjacent"
            and action.get("status") in {"open", "in_progress", "blocked"}
        ]
        if not layer3_blocking_risks and not layer3_blocking_actions:
            errors.append(
                "data_flows: unfinished transfer mechanism/TIA requires a layer3 blocking risk or launch-blocking action"
            )
    if launch == "go" and overall in {"not_ready", "high_risk", "insufficient_information"}:
        errors.append("conclusion: go is incompatible with not_ready/high_risk/insufficient_information")
    if launch == "go" and risk_level in {"critical", "high", "unknown"}:
        errors.append("conclusion: go requires risk_level low or medium after verification")
    if launch == "go" and conclusion.get("blocking_issue_ids"):
        errors.append("conclusion: go cannot have blocking_issue_ids")
    if launch == "go" and unresolved_ids:
        errors.append("conclusion: go cannot be issued while facts remain unresolved")
    if launch == "hold" and overall in {"compliant", "conditionally_compliant"}:
        errors.append("conclusion: hold is incompatible with a compliant overall status")
    if overall == "conditionally_compliant" and launch == "go":
        errors.append("conclusion: conditionally_compliant must use go_with_conditions or hold")
    if mode == "light":
        if overall in {"compliant", "conditionally_compliant"}:
            errors.append("conclusion: light assessment cannot issue a complete compliance conclusion")
        if launch in {"go", "go_with_conditions"}:
            errors.append("conclusion: light assessment cannot issue a launch decision")
        if risk_level in {"low", "medium"}:
            errors.append("conclusion: light assessment cannot assign a reassuring risk level")
    if isinstance(assessment_record, dict) and assessment_record.get("incomplete") is True and (
        overall in {"compliant", "conditionally_compliant"}
        or launch in {"go", "go_with_conditions"}
    ):
        errors.append("assessment.incomplete=true cannot support a launch-ready conclusion")
    if future_dates:
        warnings_text = " ".join(str(item) for item in conclusion.get("future_law_warnings", []))
        for law_id in sorted(future_law_ids):
            if law_id not in warnings_text:
                errors.append(f"conclusion.future_law_warnings: missing warning for future law {law_id}")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline validator for three-layer AI compliance assessments")
    parser.add_argument("assessment", type=Path)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--report", type=Path, help="optional natural-language report to run legal-effect wording lint")
    strict_group = parser.add_mutually_exclusive_group()
    strict_group.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        help="enforce launch-gate checks (default)",
    )
    strict_group.add_argument(
        "--legacy",
        dest="strict",
        action="store_false",
        help="use permissive migration checks for a pre-mode legacy record",
    )
    parser.set_defaults(strict=True)
    parser.add_argument(
        "--report-mode",
        choices=("light", "full"),
        help="override the report delivery mode when linting a legacy assessment",
    )
    args = parser.parse_args()
    try:
        data = load(args.assessment)
        schema = load(args.schema)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load input: {exc}", file=sys.stderr)
        return 2
    errors: list[str] = []
    try:
        import jsonschema  # type: ignore
    except ImportError:
        unsupported = unsupported_schema_keywords(schema)
        if unsupported:
            errors.extend(unsupported)
            print(
                "HIGH PRIORITY WARNING: jsonschema not installed and the bundled schema uses unsupported keywords; validation failed closed",
                file=sys.stderr,
            )
        else:
            errors.extend(basic_validate(data, schema))
            print(
                "HIGH PRIORITY WARNING: jsonschema not installed; used built-in validator covering all keywords in this bundled schema",
                file=sys.stderr,
            )
    else:
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as exc:
            errors.append(f"schema: invalid Draft 2020-12 schema: {exc.message}")
        else:
            validator = jsonschema.Draft202012Validator(
                schema,
                format_checker=jsonschema.FormatChecker(),
            )
            errors.extend(
                f"{'.'.join(map(str, error.path)) or '$'}: {error.message}"
                for error in sorted(validator.iter_errors(data), key=str)
            )
    try:
        semantic_errors, warnings = semantic_validate(
            data if isinstance(data, dict) else {},
            strict=True if args.strict else None,
        )
    except Exception as exc:
        semantic_errors, warnings = [f"semantic validation could not complete: {exc}"], []
    errors.extend(semantic_errors)
    if args.report:
        try:
            from lint_report import lint as lint_report_text
            report_text = args.report.read_text(encoding="utf-8")
            errors.extend(
                lint_report_text(
                    data if isinstance(data, dict) else {},
                    report_text,
                    mode=args.report_mode,
                    strict=args.strict,
                )
            )
        except OSError as exc:
            errors.append(f"report: cannot read report file: {exc}")
        except Exception as exc:  # keep the validator's failure explicit
            errors.append(f"report: lint failed: {exc}")
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {args.assessment} conforms to the three-layer assessment schema and conservative decision rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
