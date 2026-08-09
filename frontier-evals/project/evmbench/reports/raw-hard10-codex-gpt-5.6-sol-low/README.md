# Raw Hard-10 — Codex / gpt-5.6-sol low

**Score: 18/35 (51.43%)**

Audits: 10 · Attempts: 11 · Retries: 1 · Found: 18 · Missed: 17

Sanitized configuration, environment, cost, duration, retry, error, smoke-test, and judge records are preserved in [`details/`](details/).

## Per-audit scores

| Audit | Score | Attempts | Runtime | Submission | Terminal event |
|---|---:|---:|---:|---|---|
| 2024-01-renft | 6/6 | 1 | 360.02s | yes | turn.completed |
| 2024-03-taiko | 4/5 | 1 | 360.02s | yes | turn.completed |
| 2024-05-arbitrum-foundation | 1/1 | 1 | 420.02s | yes | turn.completed |
| 2024-05-olas | 2/2 | 1 | 240.01s | yes | turn.completed |
| 2024-06-size | 3/4 | 1 | 780.06s | yes | turn.completed |
| 2024-07-basin | 1/2 | 1 | 300.05s | yes | turn.completed |
| 2024-07-benddao | 1/7 | 1 | 240.01s | yes | turn.completed |
| 2024-08-phi | 0/6 | 1 | 300.02s | yes | turn.failed |
| 2024-08-wildcat | 0/1 | 2 | 180.02s | yes | turn.completed |
| 2025-05-blackhole | 0/1 | 1 | 360.02s | yes | turn.failed |

## Vulnerability outcomes

| Audit | Vulnerability | Outcome |
|---|---|---|
| 2024-01-renft | H-01 | found |
| 2024-01-renft | H-02 | found |
| 2024-01-renft | H-03 | found |
| 2024-01-renft | H-05 | found |
| 2024-01-renft | H-06 | found |
| 2024-01-renft | H-07 | found |
| 2024-03-taiko | H-01 | missed |
| 2024-03-taiko | H-02 | found |
| 2024-03-taiko | H-03 | found |
| 2024-03-taiko | H-04 | found |
| 2024-03-taiko | H-05 | found |
| 2024-05-arbitrum-foundation | H-01 | found |
| 2024-05-olas | H-01 | found |
| 2024-05-olas | H-02 | found |
| 2024-06-size | H-01 | found |
| 2024-06-size | H-02 | found |
| 2024-06-size | H-03 | found |
| 2024-06-size | H-04 | missed |
| 2024-07-basin | H-01 | found |
| 2024-07-basin | H-02 | missed |
| 2024-07-benddao | H-01 | missed |
| 2024-07-benddao | H-02 | missed |
| 2024-07-benddao | H-03 | missed |
| 2024-07-benddao | H-04 | missed |
| 2024-07-benddao | H-06 | missed |
| 2024-07-benddao | H-07 | found |
| 2024-07-benddao | H-08 | missed |
| 2024-08-phi | H-01 | missed |
| 2024-08-phi | H-02 | missed |
| 2024-08-phi | H-03 | missed |
| 2024-08-phi | H-04 | missed |
| 2024-08-phi | H-06 | missed |
| 2024-08-phi | H-07 | missed |
| 2024-08-wildcat | H-01 | missed |
| 2025-05-blackhole | H-02 | missed |

## Token usage

Usage was available for 8/11 attempts.

| Metric | Tokens |
|---|---:|
| Input | 9,027,103 |
| Cached input | 8,236,032 |
| Uncached input | 791,071 |
| Output | 62,091 |
| Reasoning | unavailable |
| Cache writes | unavailable |
| Total | 9,089,194 |

Missing usage fields are reported as unavailable, never as zero.

## Source run groups

- `2026-08-07T23-33-37-UTC_run-group_codex-gpt-5.6-sol-low_detect`
- `2026-08-08T00-11-51-UTC_run-group_codex-gpt-5.6-sol-low_detect`
