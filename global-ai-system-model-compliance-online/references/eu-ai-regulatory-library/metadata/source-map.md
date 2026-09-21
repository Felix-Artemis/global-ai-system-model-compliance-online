# Online library source map

This package deliberately has no bundled legal corpus. The authoritative URL
manifest is executable code in `scripts/fetch_official_sources.py`.

Retrieval order after download:

1. EUR-Lex Official Journal and current consolidated expressions.
2. Publications Office XHTML, PDF and FORMEX expressions.
3. Commission, AI Office, AI Board, EDPB/EDPS and Service Desk guidance.
4. Official Code of Practice pages, clearly marked as voluntary good practice.
5. Official standardisation requests and OJ references; never infer a binding
   duty from a draft or an uncited standard.

The downloader creates `corpus/`, `metadata/sources.jsonl` and
`metadata/last-fetch-report.json` at runtime. The generated records contain
the source URL, retrieval time, HTTP result, local path and SHA-256 where a
file was obtained. Failed or unavailable official manifestations remain
explicit gaps for human review.
