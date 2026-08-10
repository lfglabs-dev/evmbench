# Cyfrin Solidity Hard-10 (sandboxed)

**Score: 18/35 (51.43%)**

Audits: 10 · Attempts: 10 · Retries: 0 · Found: 18 · Missed: 17

## Blackhole retry

The original Hard-10 run completed nine audits but stopped while the
`2025-05-blackhole` audit was still running, so it did not emit an aggregate
result. Blackhole was rerun separately with the same Cyfrin Solidity skill and
completed normally in 420 seconds. It scored 0/1: the submitted report
identified a different issue than the benchmark's expected `H-02` finding.
This report combines the nine completed original audits with that graded retry.

## Per-audit scores

| Audit | Score | Attempts | Runtime | Submission | Terminal event |
|---|---:|---:|---:|---|---|
| 2024-01-renft | 5/6 | 1 | 540.03s | yes | turn.completed |
| 2024-03-taiko | 4/5 | 1 | 480.03s | yes | turn.completed |
| 2024-05-arbitrum-foundation | 1/1 | 1 | 480.04s | yes | turn.completed |
| 2024-05-olas | 0/2 | 1 | 420.03s | yes | turn.completed |
| 2024-06-size | 4/4 | 1 | 300.02s | yes | turn.completed |
| 2024-07-basin | 1/2 | 1 | 240.02s | yes | turn.failed |
| 2024-07-benddao | 1/7 | 1 | 300.02s | yes | turn.completed |
| 2024-08-phi | 1/6 | 1 | 240.01s | yes | turn.completed |
| 2024-08-wildcat | 1/1 | 1 | 480.01s | yes | turn.completed |
| 2025-05-blackhole | 0/1 | 1 | 420.03s | yes | turn.completed |

## Vulnerability outcomes

| Audit | Vulnerability | Outcome |
|---|---|---|
| 2024-01-renft | H-01 | found |
| 2024-01-renft | H-02 | found |
| 2024-01-renft | H-03 | found |
| 2024-01-renft | H-05 | missed |
| 2024-01-renft | H-06 | found |
| 2024-01-renft | H-07 | found |
| 2024-03-taiko | H-01 | missed |
| 2024-03-taiko | H-02 | found |
| 2024-03-taiko | H-03 | found |
| 2024-03-taiko | H-04 | found |
| 2024-03-taiko | H-05 | found |
| 2024-05-arbitrum-foundation | H-01 | found |
| 2024-05-olas | H-01 | missed |
| 2024-05-olas | H-02 | missed |
| 2024-06-size | H-01 | found |
| 2024-06-size | H-02 | found |
| 2024-06-size | H-03 | found |
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
| 2024-08-phi | H-02 | found |
| 2024-08-phi | H-03 | missed |
| 2024-08-phi | H-04 | missed |
| 2024-08-phi | H-06 | missed |
| 2024-08-phi | H-07 | missed |
| 2024-08-wildcat | H-01 | found |
| 2025-05-blackhole | H-02 | missed |

## Token usage

Usage was available for 9/10 attempts.

| Metric | Tokens |
|---|---:|
| Input | 8,882,150 |
| Cached input | 8,058,368 |
| Uncached input | 823,782 |
| Output | 69,183 |
| Reasoning | unavailable |
| Cache writes | unavailable |
| Total | 8,951,333 |

Missing usage fields are reported as unavailable, never as zero.

## Source run groups

- `2026-08-09T16-53-11-UTC_run-group_codex-gpt-5.6-sol_detect`
- `2026-08-10T08-20-37-UTC_run-group_codex-gpt-5.6-sol_detect`
