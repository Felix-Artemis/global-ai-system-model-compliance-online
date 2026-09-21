#!/usr/bin/env python3
"""Lint a natural-language report against the local legal-effect metadata.

The assessment JSON remains the machine-readable source of law classification;
the report is intentionally checked separately so a prose edit cannot silently
turn a voluntary Code of Practice, guidance document or standard into a
mandatory legal requirement.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


GOOD_PRACTICE_LABEL = "欧盟建议的良好实践/解释性材料（非独立法定义务）"
VOLUNTARY_STANDARD_LABEL = "自愿性标准"
GOOD_PRACTICE_TYPES = {"official_guidance", "cop"}
NON_BINDING_TYPES = GOOD_PRACTICE_TYPES | {"voluntary_standard"}
COMMON_FORBIDDEN_WORDING = (
    "必须遵守",
    "强制遵守",
    "强制性义务",
    "视为法定义务",
    "作为法定义务",
    "安全港",
    "自动免责",
    "当然免责",
    "合规推定",
)
CONFORMITY_PRESUMPTION = "符合性推定"
LIGHT_COMPLETE_WORDING = (
    "总体状态",
    "总体风险",
    "上线状态",
    "可上线",
    "可以上线",
    "能够上线",
    "已上线",
    "已合规",
    "完全合规",
    "总体合规",
    "合规结论",
    "合规状态",
    "compliant",
    "launch_decision",
    "risk_level",
    "go_with_conditions",
)
DOWNGRADE_WORDING = (
    "只是建议",
    "仅建议",
    "属于建议",
    "不是必须",
    "无需遵守",
    "可以不遵守",
    "可不遵守",
    "自愿遵守",
    "可选义务",
    "optional obligation",
    "merely guidance",
    "just guidance",
)
CURRENT_BINDING_TYPES = {"binding_law", "delegated_act", "implementing_act"}

# A report should be allowed to warn that a voluntary instrument is not a
# safe-harbour or automatic exemption.  Match the assertion, rather than the
# bare word, so a negated warning is not treated as an endorsement.
NEGATION_PREFIXES = (
    "不是",
    "并非",
    "不构成",
    "不属于",
    "不得视为",
    "不得作为",
    "不能作为",
    "不会构成",
    "不会自动",
    "不能自动",
    "不应视为",
    "不应作为",
    "不输出",
    "不能据此认定",
    "不得据此认定",
    "不得写成",
    "不能写成",
    "不应写成",
    "不会",
)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("assessment must be a JSON object")
    return value


def law_terms(law: dict[str, Any]) -> list[str]:
    terms = [
        str(law.get("id", "")),
        str(law.get("name", "")),
        str(law.get("citation", "")),
        str(law.get("celex", "")),
        str(law.get("eli", "")),
    ]
    source = str(law.get("source_type", ""))
    if source == "cop":
        terms.extend(("Code of Practice", "CoP", "守则"))
    elif source == "official_guidance":
        terms.extend(("guidance", "指南"))
    elif source == "voluntary_standard":
        terms.extend(("standard", "标准"))
    return [term for term in terms if term]


def is_negated(line: str, phrase: str, start: int) -> bool:
    """Return whether a forbidden term is explicitly negated nearby."""

    prefix = line[max(0, start - 80):start].rstrip()
    if start > 0 and line[start - 1] in "不未无非":
        return True
    if any(prefix.endswith(item) for item in NEGATION_PREFIXES):
        return True
    # A negator in an earlier sentence or clause must not suppress a later
    # affirmative claim.  This matters for light reports, which necessarily
    # contain wording such as “尚未覆盖” before their final recommendation.
    clause = re.split(
        r"(?:[。；;，,！？!?\n]|(?:但是|然而|不过|却)|\b(?:but|however)\b)",
        prefix,
        flags=re.I,
    )[-1]
    return bool(
        re.search(
            r"(?:不得|不能|不应|不可|禁止|避免|不能据此|不得据此|不宜|尚不能|尚未|"
            r"无法|未能|不构成|不代表|不等于|不意味着)"
            r"[^。；;，,！？!?\n]{0,45}$",
            clause,
            re.I,
        )
        or re.search(
            r"(?:not|cannot|can't|never|without)\s+(?:[a-z]+\s+){0,4}$",
            clause,
            re.I,
        )
    )


def forbidden_occurrences(line: str, phrase: str) -> list[int]:
    """Find positive uses of a forbidden legal-effect phrase."""

    result: list[int] = []
    offset = 0
    lowered = line.lower()
    needle = phrase.lower()
    while True:
        index = lowered.find(needle, offset)
        if index < 0:
            break
        if not is_negated(line, phrase, index):
            result.append(index)
        offset = index + len(needle)
    return result


def valid_harmonised_standard_presumption(text: str) -> bool:
    """Accept only a narrow, sourced statement of conformity presumption.

    Harmonised standards remain voluntary.  An OJ citation may nevertheless
    trigger a presumption for the legal requirements actually covered by that
    citation.  The prose must carry all of those limits in the same paragraph
    or table row so a detached sentence cannot look like whole-product
    compliance or a safe harbour.
    """

    lower = text.lower()
    has_oj = bool(re.search(r"(?:\boj\b|official\s+journal|欧盟官方公报)", text, re.I))
    has_basis = bool(
        re.search(r"(?:article\s*40|art\.?\s*40|第\s*40\s*条|具体产品法|相关产品法)", text, re.I)
    )
    has_scope_limit = any(
        phrase in lower
        for phrase in (
            "覆盖的要求",
            "覆盖的具体要求",
            "覆盖范围内",
            "对应要求范围内",
            "适用范围内",
            "限定于",
            "仅覆盖",
            "具体要求",
            "covered requirements",
            "within the scope",
            "limited to",
        )
    )
    has_limit_word = any(phrase in lower for phrase in ("可能", "仅", "限于", "may"))
    return has_oj and has_basis and has_scope_limit and has_limit_word


def resolved_mode(assessment: dict[str, Any], override: str | None = None) -> str:
    """Resolve the report branch without making old records invalid."""

    if override in {"light", "full"}:
        return override
    record = assessment.get("assessment", {})
    candidates: list[Any] = []
    if isinstance(record, dict):
        candidates.extend((record.get("mode"), record.get("delivery_mode")))
    candidates.extend((assessment.get("mode"), assessment.get("delivery_mode")))
    for value in candidates:
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"light", "lightweight", "轻量版", "轻量版初步评估"}:
                return "light"
            if normalized in {"full", "complete", "全量版", "全量版评估"}:
                return "full"
    return "full"


def _paragraphs(text: str) -> list[tuple[int, str]]:
    """Return non-empty paragraphs with their first source line number."""

    result: list[tuple[int, str]] = []
    start = 1
    current: list[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip():
            if not current:
                start = number
            current.append(line)
        elif current:
            result.append((start, " ".join(current)))
            current = []
    if current:
        result.append((start, " ".join(current)))
    return result


def _positive(text: str, phrase: str) -> bool:
    """Match an assertion while allowing nearby negated warnings."""

    return bool(forbidden_occurrences(text, phrase))


def _contains_any_positive(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_positive(text, phrase) for phrase in phrases)


def _positive_bare_compliance(text: str) -> bool:
    """Detect an unqualified “合规” claim while allowing risk warnings."""

    for match in re.finditer(r"合规", text):
        start = match.start()
        if start > 0 and text[start - 1] in "不未无非":
            continue
        prefix = text[max(0, start - 40):start]
        if re.search(
            r"(?:不能据此认定|不得据此认定|尚不能确认|不应认定|不能写成|不得写成|"
            r"不能给出|不得给出|不应给出|无法给出|未能给出|不能认定|不得认定|"
            r"不构成|不代表|不等于|不意味着)\s*$",
            prefix,
        ):
            continue
        # Business-facing preliminary reports often need to say that the
        # position is uncertain.  These qualifiers are not a conclusion that
        # the system is compliant; keep them available for risk triage while
        # continuing to reject bare or affirmative compliance claims.
        if re.search(
            r"(?:不一定|不确定是否|可能|或许|尚不|尚未确认|尚未核实|待核(?:实|验)?|待确认|无法确认|未能确认)\s*$",
            prefix,
        ):
            continue
        suffix = text[match.end():match.end() + 8]
        if re.match(
            r"(?:风险|问题|性风险|待核|可能|尚不能|不能|无法|未能|不一定|不等于|不代表|不构成|"
            r"(?:结论|状态)?\s*(?:尚不能|不能|无法|未能|待核|待确认|尚未确认|尚未核实))",
            suffix,
        ):
            continue
        return True
    return False


def _positive_complete_claim(text: str, phrase: str) -> bool:
    """Detect an affirmative complete-report marker with uncertainty allowed."""

    lowered = text.casefold()
    needle = phrase.casefold()
    offset = 0
    while True:
        start = lowered.find(needle, offset)
        if start < 0:
            return False
        if not is_negated(text, phrase, start):
            suffix = text[start + len(phrase):start + len(phrase) + 48]
            if not re.match(
                r"\s*(?:[：:]\s*)?(?:尚不能|不能|无法|未能|待核(?:实|验)?|待确认|"
                r"尚未确认|尚未核实|不一定|可能|不构成|不代表|不等于)",
                suffix,
                re.I,
            ):
                return True
        offset = start + max(1, len(phrase))


def _related(text: str, law: dict[str, Any]) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in law_terms(law))


def _first_marker_line(report: str, patterns: tuple[str, ...]) -> int | None:
    for number, line in enumerate(report.splitlines(), 1):
        if any(re.search(pattern, line, re.I) for pattern in patterns):
            return number
    return None


def _has_launch_status(report: str) -> bool:
    """Require an actual status value, not a stray mention of “上线”."""

    return bool(
        re.search(
            r"(?:总体状态|上线状态|给业务的结论|当前结论)\s*[：:]?\s*"
            r"(?:暂缓上线|有条件上线|暂不能确认|可上线|不能上线|暂停|hold|go|go_with_conditions)",
            report,
            re.I,
        )
        or re.search(
            r"(?:当前|现阶段|目前)\s*(?:暂缓上线|有条件上线|暂不能确认|可上线|不能上线|暂停)",
            report,
            re.I,
        )
    )


def _mode_structure_errors(report: str, mode: str, strict: bool) -> list[str]:
    """Check the business-facing branch without parsing the whole template."""

    errors: list[str] = []
    if not report.strip():
        return ["报告正文为空；必须直接给出业务结论和下一步"]

    conclusion_line = _first_marker_line(
        report,
        (r"给业务的结论", r"一页结论", r"上线状态", r"总体状态", r"初步风险提示"),
    )
    legal_line = _first_marker_line(report, (r"法律依据", r"法律原文", r"法源"))
    if legal_line is not None and conclusion_line is not None and legal_line < conclusion_line:
        errors.append("报告顺序错误：给业务的自然语言结论必须先于集中法律依据")

    if mode == "light":
        # A light report can mention that a complete conclusion is unavailable,
        # but cannot make the conclusion itself.  Negated wording is exempt.
        for phrase in LIGHT_COMPLETE_WORDING:
            if _positive_complete_claim(report, phrase):
                errors.append(f"轻量版不得输出完整结论或上线判断：{phrase}")
        # “不合规风险/合规风险待核” is a useful warning for a business team;
        # only predicate-like uses of the bare word “合规” are complete claims.
        if _positive_bare_compliance(report):
            errors.append("轻量版不得把结果写成无条件合规")
        if strict:
            required = (
                ("初步风险提示", r"初步风险提示"),
                ("已发现风险线索", r"已发现风险线索|风险线索"),
                ("待内部核实", r"待内部核实|待核"),
                ("尚未覆盖", r"尚未覆盖|未覆盖"),
                ("最严重后果", r"最严重后果|最严重可能后果"),
                ("升级建议", r"升级建议|升级全量版|下一步"),
            )
            for label, pattern in required:
                if not re.search(pattern, report, re.I):
                    errors.append(f"轻量版报告缺少业务段落：{label}")
        return errors

    if strict:
        if conclusion_line is None or conclusion_line == _first_marker_line(report, (r"初步风险提示",)):
            errors.append("全量版必须有单独的给业务结论或一页结论，并写明上线状态")
        if not _has_launch_status(report):
            errors.append("全量版必须用自然语言写出上线状态")
        if not re.search(r"建议|待办|下一步|整改|完成标准", report, re.I):
            errors.append("报告必须给出业务可执行的建议或待办")
        if not re.search(r"最严重|后果|罚款|停止使用|禁止投放|监管调查|人身|财产损害", report, re.I):
            errors.append("报告必须说明不处理的最严重可能后果")
        if conclusion_line is not None:
            body = " ".join(report.splitlines()[conclusion_line:conclusion_line + 8])
            if len(body.strip()) < 20 or not re.search(r"[\u4e00-\u9fffA-Za-z]", body):
                errors.append("给业务的结论必须是完整自然语言，而不是只有条号或机器字段")
    return errors


def lint(
    assessment: dict[str, Any],
    report: str,
    *,
    mode: str | None = None,
    strict: bool = False,
) -> list[str]:
    """Return report wording and delivery-contract errors.

    ``strict=False`` preserves the small legal-effect regression fixtures used
    during migration.  New generated assessments carry ``assessment.mode`` and
    callers should pass ``--strict`` for the complete business-delivery gate.
    Light-mode restrictions are always enforced because a light report must
    never be mistaken for a launch decision.
    """

    errors: list[str] = []
    laws = assessment.get("laws", [])
    if not isinstance(laws, list):
        laws = []
    law_records = [law for law in laws if isinstance(law, dict)]
    non_binding = [law for law in law_records if law.get("source_type") in NON_BINDING_TYPES]
    good_practice = [law for law in non_binding if law.get("source_type") in GOOD_PRACTICE_TYPES]
    standards = [law for law in non_binding if law.get("source_type") == "voluntary_standard"]
    mandatory = [
        law for law in law_records
        if law.get("source_type") in CURRENT_BINDING_TYPES
        and law.get("binding") is True
        and law.get("legal_status") == "current"
    ]

    if good_practice and GOOD_PRACTICE_LABEL not in report:
        errors.append("报告缺少效力标签：" + GOOD_PRACTICE_LABEL)
    if standards and VOLUNTARY_STANDARD_LABEL not in report:
        errors.append("报告缺少效力标签：" + VOLUNTARY_STANDARD_LABEL)

    paragraphs = _paragraphs(report)
    for line_number, paragraph in paragraphs:
        related_good_practice = [law for law in good_practice if _related(paragraph, law)]
        related_standards = [law for law in standards if _related(paragraph, law)]
        if not related_good_practice and not related_standards:
            continue
        for phrase in COMMON_FORBIDDEN_WORDING:
            if _positive(paragraph, phrase):
                errors.append(
                    f"第{line_number}行附近把非约束性材料写成强制/免责依据：{phrase}"
                )
        if related_good_practice and _positive(paragraph, CONFORMITY_PRESUMPTION):
            errors.append(f"第{line_number}行附近把CoP或指南写成符合性推定依据")
        if related_standards and _positive(paragraph, CONFORMITY_PRESUMPTION):
            if not valid_harmonised_standard_presumption(paragraph):
                errors.append(
                    f"第{line_number}行附近声称标准产生符合性推定，但未同时限定OJ引用、第40条或产品法依据及覆盖要求范围"
                )

    # A label and the operative assertion are often separated by headings,
    # tables or line breaks.  Once a non-binding instrument is named anywhere
    # in the report, scan the complete text as one logical document as well.
    # This closes the easy “label in the legal section, mandatory claim in the
    # recommendation section” bypass while retaining the negation allowance.
    if non_binding and any(_related(report, law) for law in non_binding):
        flattened = report
        for phrase in COMMON_FORBIDDEN_WORDING:
            if _positive(flattened, phrase):
                errors.append(f"报告全文把非约束性材料写成强制/免责依据：{phrase}")
        if good_practice and _positive(flattened, CONFORMITY_PRESUMPTION):
            errors.append("报告全文把CoP或指南写成符合性推定依据")
        if standards and _positive(flattened, CONFORMITY_PRESUMPTION) and not valid_harmonised_standard_presumption(flattened):
            errors.append("报告全文声称标准产生符合性推定，但缺少OJ/第40条或产品法依据及范围限制")

    # A binding law cannot be downgraded to a suggestion merely because the
    # report puts the wording in a different paragraph from the citation.
    for line_number, paragraph in paragraphs:
        related_mandatory = [law for law in mandatory if _related(paragraph, law)]
        if not related_mandatory:
            continue
        for phrase in DOWNGRADE_WORDING:
            if _positive(paragraph, phrase):
                errors.append(
                    f"第{line_number}行附近把强制性法规降级为建议或可选项：{phrase}"
                )
        if re.search(r"(?:属于|(?<!不)是|仅为|只是)\s*建议(?:性材料|或指南|义务)?", paragraph, re.I):
            errors.append(f"第{line_number}行附近把强制性法规写成建议材料")
        if re.search(r"(?:不具|没有|不产生).{0,12}(?:约束力|强制力)", paragraph, re.I):
            errors.append(f"第{line_number}行附近否定强制性法规的约束力")

    if mandatory and any(_related(report, law) for law in mandatory):
        flattened = report
        for phrase in DOWNGRADE_WORDING:
            if _positive(flattened, phrase):
                errors.append(f"报告全文把强制性法规降级为建议或可选项：{phrase}")

    errors.extend(_mode_structure_errors(report, resolved_mode(assessment, mode), strict))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assessment", type=Path, help="assessment JSON containing law source_type values")
    parser.add_argument("report", type=Path, help="natural-language Markdown or text report")
    strict_group = parser.add_mutually_exclusive_group()
    strict_group.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        help="enforce business-facing conclusion, recommendation and consequence sections (default)",
    )
    strict_group.add_argument(
        "--legacy",
        dest="strict",
        action="store_false",
        help="run only legal-effect wording checks for a pre-mode legacy report",
    )
    parser.set_defaults(strict=True)
    parser.add_argument(
        "--mode",
        choices=("light", "full"),
        help="override the delivery mode for a legacy assessment",
    )
    args = parser.parse_args()
    try:
        assessment = load_json(args.assessment)
        report = args.report.read_text(encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot load report inputs: {exc}", file=sys.stderr)
        return 2
    errors = lint(assessment, report, mode=args.mode, strict=args.strict)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: report legal-effect wording passes the non-binding-material lint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
