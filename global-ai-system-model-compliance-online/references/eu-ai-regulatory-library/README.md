# Online EU AI regulatory library

This distribution intentionally contains no legislation, guidance, snapshots,
or local source database. Use the bundled downloader to create a local cache
from EU institutional sources before making a legal assessment.

From the Skill root:

```text
python3 scripts/fetch_official_sources.py --dry-run
python3 scripts/fetch_official_sources.py --profile core
python3 scripts/fetch_official_sources.py --profile all
```

The downloader writes to `references/eu-ai-regulatory-library/corpus/` and
`metadata/`, keeps dated superseded copies, records URL/status/hash metadata,
and refuses non-EU hosts. It does not use news articles, search results,
commercial databases, or unofficial mirrors. A failed URL is recorded for
manual review and is never replaced with an empty file or summary.

The `core` profile retrieves the AI Act, Digital Omnibus, legislative history,
and the current Annex I expressions. The `all` profile also retrieves the
listed official guidance, Codes of Practice, templates, FAQs, standardisation
materials, and directly connected interface-law texts. Publication dates,
legal status, OJ citations, and final-versus-draft classification must still
be checked against the current EUR-Lex record before relying on a conclusion.
