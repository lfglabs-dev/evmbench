# EVMBench reports

Generated benchmark reports live in named subdirectories here. Each report is self-contained and includes:

- `README.md` — human-readable score, audit, vulnerability, and usage tables
- `report.json` — the same data in a stable machine-readable format
- `per_audit.csv` — one row per selected audit result
- `vulnerabilities.csv` — one row per scored vulnerability

Use `scripts/report_results.py` as documented in the project README. Raw model transcripts and credentials are deliberately not copied into reports.

Published reports may also include a `details/` directory containing sanitized run provenance such as configuration, environment, cost, retry, error, and smoke-test records.
