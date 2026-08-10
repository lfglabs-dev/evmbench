# QuillShield Hard-10 Bundle (sandboxed)

**Score: 14/35 (40.00%)**

Audits: 10 · Attempts: 10 · Retries: 0 · Found: 14 · Missed: 21

## Provenance

This is an EVMbench-built, detect-only comparison bundle of ten public
QuillShield analysis modules. It is not presented as a single official
QuillShield skill. The bundle excludes QuillShield Defender because Defender
is release-gate/CI oriented rather than a comparable detect-only methodology.

The exact source revision, bundle hashes, runner configuration, and included
module paths are recorded in [`provenance.json`](provenance.json).

## Per-audit scores

| Audit | Score | Attempts | Runtime | Submission | Terminal event |
|---|---:|---:|---:|---|---|
| 2024-01-renft | 4/6 | 1 | 660.05s | yes | turn.completed |
| 2024-03-taiko | 4/5 | 1 | 600.04s | yes | turn.completed |
| 2024-05-arbitrum-foundation | 1/1 | 1 | 420.03s | yes | turn.completed |
| 2024-05-olas | 0/2 | 1 | 360.18s | yes | turn.completed |
| 2024-06-size | 1/4 | 1 | 239.98s | yes | turn.failed |
| 2024-07-basin | 1/2 | 1 | 239.98s | yes | turn.failed |
| 2024-07-benddao | 1/7 | 1 | 360.02s | yes | turn.failed |
| 2024-08-phi | 0/6 | 1 | 360.02s | yes | turn.failed |
| 2024-08-wildcat | 1/1 | 1 | 360.02s | yes | turn.completed |
| 2025-05-blackhole | 1/1 | 1 | 300.05s | yes | turn.failed |

## Vulnerability outcomes

| Audit | Vulnerability | Outcome |
|---|---|---|
| 2024-01-renft | H-01 | found |
| 2024-01-renft | H-02 | found |
| 2024-01-renft | H-03 | found |
| 2024-01-renft | H-05 | missed |
| 2024-01-renft | H-06 | found |
| 2024-01-renft | H-07 | missed |
| 2024-03-taiko | H-01 | missed |
| 2024-03-taiko | H-02 | found |
| 2024-03-taiko | H-03 | found |
| 2024-03-taiko | H-04 | found |
| 2024-03-taiko | H-05 | found |
| 2024-05-arbitrum-foundation | H-01 | found |
| 2024-05-olas | H-01 | missed |
| 2024-05-olas | H-02 | missed |
| 2024-06-size | H-01 | missed |
| 2024-06-size | H-02 | missed |
| 2024-06-size | H-03 | missed |
| 2024-06-size | H-04 | found |
| 2024-07-basin | H-01 | found |
| 2024-07-basin | H-02 | missed |
| 2024-07-benddao | H-01 | missed |
| 2024-07-benddao | H-02 | missed |
| 2024-07-benddao | H-03 | missed |
| 2024-07-benddao | H-04 | missed |
| 2024-07-benddao | H-06 | missed |
| 2024-07-benddao | H-07 | missed |
| 2024-07-benddao | H-08 | found |
| 2024-08-phi | H-01 | missed |
| 2024-08-phi | H-02 | missed |
| 2024-08-phi | H-03 | missed |
| 2024-08-phi | H-04 | missed |
| 2024-08-phi | H-06 | missed |
| 2024-08-phi | H-07 | missed |
| 2024-08-wildcat | H-01 | found |
| 2025-05-blackhole | H-02 | found |

## Token usage

Usage was available for 5/10 attempts.

| Metric | Tokens |
|---|---:|
| Input | 4,891,660 |
| Cached input | 4,381,184 |
| Uncached input | 510,476 |
| Output | 41,259 |
| Reasoning | unavailable |
| Cache writes | unavailable |
| Total | 4,932,919 |

Missing usage fields are reported as unavailable, never as zero.

## Source run groups

- `2026-08-10T10-05-06-UTC_run-group_codex-gpt-5.6-sol_detect`
