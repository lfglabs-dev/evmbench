# EVMBench Hard-10 — raw Codex / Sandboxed gpt-5.6-sol low

Canonical final score: **18/35 (51.43%)**. Nine primary jobs produced valid submissions; Wildcat's original attempt did not, so only that failed job was retried. The retry produced a valid report and independently preserved Wildcat's 0/1 score. Harness rollout failures: 0; audit-job retries: 1.

## Scores

| Audit | Score |
|---|---:|
| 2024-01-renft | 6/6 |
| 2024-03-taiko | 4/5 |
| 2024-05-arbitrum-foundation | 1/1 |
| 2024-05-olas | 2/2 |
| 2024-06-size | 3/4 |
| 2024-07-basin | 1/2 |
| 2024-07-benddao | 1/7 |
| 2024-08-phi | 0/6 |
| 2024-08-wildcat | 0/1 |
| 2025-05-blackhole | 0/1 |

## All 35 gold vulnerability outcomes

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

Found: 18. Missed: 17. Scoring ambiguities: 0. False positives are unavailable because EVMBench's gold scorer does not canonically label extra findings.

## Usage and estimated cost

Exact full-run token and cost totals are unavailable. Codex emitted cumulative usage for 8/11 agent attempts. Phi and Blackhole ended with a terminal provider 502 after writing valid reports; original Wildcat ended likewise before persisting its report and was retried once. Usage for those three failed attempts was not emitted. Judge usage was also not emitted. The measured audit-agent lower bound is: input 9,027,103; cached input 8,236,032; uncached input 791,071; output including reasoning 62,091; total 9,089,194. Reasoning-token and cache-write-token splits are unavailable, not zero.

Using the requested illustrative prices, the known 8-attempt lower-bound estimate is **$9.936101**. Formula: uncached input × $5/M + cached input × $0.50/M + cache writes × $6.25/M + output including reasoning × $30/M. This is not an exact bill: three failed-attempt usages, all judge usage, and cache writes are unavailable, and provider billing configuration was not independently confirmed.

API attempts: 360 total. Breakdown: `{"/v1/chat/completions": {"200": 35}, "/v1/responses": {"200": 236, "502": 89}}`.

## Durations

Benchmark wall clock: 2486 seconds (2026-08-07T23:33:35Z to 2026-08-08T00:15:01Z).

| Audit | Agent seconds | End-to-end seconds (approx.) |
|---|---:|---:|
| 2024-01-renft | 360.02 | 377.28 |
| 2024-03-taiko | 360.02 | 370.58 |
| 2024-05-arbitrum-foundation | 420.02 | 427.97 |
| 2024-05-olas | 240.01 | 248.57 |
| 2024-06-size | 780.06 | 788.40 |
| 2024-07-basin | 300.05 | 307.89 |
| 2024-07-benddao | 240.01 | 249.13 |
| 2024-08-phi | 300.02 | 308.27 |
| 2024-08-wildcat | 180.02 | 186.68 |
| 2025-05-blackhole | 360.02 | 369.41 |

## Errors and validity caveats

- Three attempts (Phi, original Wildcat, Blackhole) received terminal Sandboxed/Cloudflare 502 responses. Phi and Blackhole had valid reports; original Wildcat did not persist one and was the only audit retried. The retry also scored 0/1. Usage for all three failed attempts is unavailable, a material provider-reliability caveat.
- The first launch stopped before starting any audit because `gpt-5.6-sol` was absent from a static context-window map. It was corrected and the single canonical 10-job run then completed.
- Blackhole's declared benchmark source commit currently has an Algebra interface compile mismatch. The build retained the declared source and allowed the compile warm-up to fail; the audit and scorer still ran. This is a validity caveat.
- Agent containers needed network reachability to the host proxy. Codex web search was disabled, but Docker egress was not independently isolated.
- The 10 audit images were built natively for this ARM64 host; source/audit inputs, prompts, tools, timeouts, and scoring behavior were otherwise canonical.

See the sibling JSON files for judge reasoning, per-job status, exact sanitized transport errors, usage availability, durations, retries, hashes, and image IDs.
