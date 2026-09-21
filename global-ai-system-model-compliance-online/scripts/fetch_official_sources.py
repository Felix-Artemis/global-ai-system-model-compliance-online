#!/usr/bin/env python3
"""Download the EU AI regulatory source set from EU institutional hosts only.

This file is the URL manifest for the database-free distribution. It creates
a local, auditable cache but never treats a failed download as legal content.
Existing files are preserved with a dated superseded suffix before replacement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "references" / "eu-ai-regulatory-library"
CORPUS = LIBRARY / "corpus"
META = LIBRARY / "metadata"

ALLOWED_HOSTS = {
    "eur-lex.europa.eu", "publications.europa.eu", "op.europa.eu",
    "data.europa.eu", "commission.europa.eu", "ec.europa.eu",
    "digital-strategy.ec.europa.eu", "ai-act-service-desk.ec.europa.eu",
    "edpb.europa.eu", "edps.europa.eu", "enisa.europa.eu",
    "cencenelec.eu",
}

ANNEX = (
    "02009L0048-20260829", "02013L0053-20131228", "02014L0033-20260530",
    "02014L0034-20260530", "02014L0053-20260530", "02014L0068-20260530",
    "02016R0424-20260529", "02016R0425-20260529", "02016R0426-20260529",
    "02017R0745-20260719", "02017R0746-20250110", "02008R0300-20260802",
    "02013R0168-20260802", "02013R0167-20260802", "02014L0090-20260802",
    "02016L0797-20260802", "02018R0858-20260802", "02019R2144-20260802",
    "02018R1139-20260802", "02023R1230-20260727",
)

CORE = [
    ("ai-act-original", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689", "legislation/CELEX-32024R1689-original.html"),
    ("ai-act-consolidated", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02024R1689-20260727", "legislation/CELEX-02024R1689-20260727-consolidated.html"),
    ("ai-omnibus", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32026R1744", "legislation/CELEX-32026R1744-final.html"),
    ("ai-omnibus-pdf", "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32026R1744", "legislation/CELEX-32026R1744-final.pdf"),
    ("ai-omnibus-procedure", "https://eur-lex.europa.eu/procedure/EN/2025_359", "legislative-history/Procedure-2025-0359-COD.html"),
    ("com-2025-836", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52025PC0836", "legislative-history/COM-2025-836.html"),
    ("swd-2025-836", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52025SC0836", "legislative-history/SWD-2025-836.html"),
    ("machinery-2023-1230", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R1230", "legislation/CELEX-32023R1230.html"),
    ("uas-2018-1139", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32018R1139", "legislation/CELEX-32018R1139.html"),
    ("machinery-directive-history", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32006L0042", "legislation/CELEX-32006L0042-historical.html"),
]

ALL_EXTRA = [
    ("ai-definition-guidance", "https://digital-strategy.ec.europa.eu/en/library/ai-system-definition", "guidance/ai-system-definition-page.html"),
    ("article-5-guidance", "https://digital-strategy.ec.europa.eu/en/library/second-draft-general-purpose-ai-code-practice", "guidance/article-5-and-ai-act-guidance-page.html"),
    ("article-50-guidance", "https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content", "guidance/article-50-transparency-code-page.html"),
    ("gpai-code", "https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai", "codes-of-practice/gpai-code-page.html"),
    ("service-desk", "https://ai-act-service-desk.ec.europa.eu/en", "guidance/ai-act-service-desk-page.html"),
    ("gdpr", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679", "interface-law/CELEX-32016R0679.html"),
    ("copyright-directive", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019L0790", "interface-law/CELEX-32019L0790.html"),
    ("eprivacy", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32002L0058", "interface-law/CELEX-32002L0058.html"),
    ("data-act", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2854", "interface-law/CELEX-32023R2854.html"),
    ("cra", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847", "interface-law/CELEX-32024R2847.html"),
    ("product-liability", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024L2853", "interface-law/CELEX-32024L2853.html"),
    ("market-surveillance", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R1020", "interface-law/CELEX-32019R1020.html"),
    ("standardisation-request", "https://ec.europa.eu/transparency/documents-register/detail?ref=C(2025)3871", "standardisation/C-2025-3871-page.html"),
]

def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def official(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme in {"http", "https"} and any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def annex_urls() -> list[tuple[str, str, str]]:
    result = []
    for expression in ANNEX:
        result.extend([
            (f"annex-{expression}-html", f"https://publications.europa.eu/resource/celex/{expression}.ENG.xhtml", f"annex-i/current/{expression}.html"),
            (f"annex-{expression}-pdf", f"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:{expression}", f"annex-i/current/{expression}.pdf"),
            (f"annex-{expression}-formex", f"https://publications.europa.eu/resource/celex/{expression}.ENG.fmx4", f"annex-i/current/{expression}.xml"),
        ])
    return result

def manifest(profile: str) -> list[tuple[str, str, str]]:
    items = list(CORE)
    if profile == "all":
        items += ALL_EXTRA
    items += annex_urls()
    return items

def safe_rel(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe local path: {path}")
    return candidate

def fetch(item: tuple[str, str, str], dry_run: bool) -> dict:
    item_id, url, relative = item
    if not official(url):
        raise ValueError(f"blocked non-EU URL: {url}")
    target = CORPUS / safe_rel(relative)
    record = {"id": item_id, "source_url": url, "local_path": str(target.relative_to(LIBRARY)), "retrieved_at_utc": timestamp()}
    if dry_run:
        record["status"] = "planned"
        return record
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Global-AI-System-Model-Compliance/online"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
            record["http_status"] = getattr(response, "status", 200)
            record["content_type"] = response.headers.get("Content-Type", "")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        record["status"] = "failed"
        record["error"] = str(exc)
        return record
    if target.exists():
        dated = target.with_name(target.name + f".superseded-{datetime.now(timezone.utc):%Y-%m-%dT%H%M%SZ}")
        target.replace(dated)
        record["superseded_path"] = str(dated.relative_to(LIBRARY))
    target.write_bytes(data)
    record["status"] = "downloaded"
    record["sha256"] = sha256(data)
    return record

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("core", "all"), default="core")
    parser.add_argument("--dry-run", action="store_true", help="list official URLs without network access")
    args = parser.parse_args()
    records = []
    for item in manifest(args.profile):
        try:
            records.append(fetch(item, args.dry_run))
        except Exception as exc:
            records.append({"id": item[0], "source_url": item[1], "status": "blocked", "error": str(exc)})
    if not args.dry_run:
        META.mkdir(parents=True, exist_ok=True)
        (META / "sources.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
        (META / "last-fetch-report.json").write_text(json.dumps({"checked_at_utc": timestamp(), "profile": args.profile, "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"profile": args.profile, "dry_run": args.dry_run, "count": len(records), "failed": sum(r.get("status") in {"failed", "blocked"} for r in records), "records": records}, ensure_ascii=False, indent=2))
    return 0 if not any(r.get("status") in {"failed", "blocked"} for r in records) else 2

if __name__ == "__main__":
    raise SystemExit(main())
