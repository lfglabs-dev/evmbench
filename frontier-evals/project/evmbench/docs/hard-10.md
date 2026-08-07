# Hard-10 subset

## Scope

This repository's executable unit is an **audit**: `EVMbench.get_audit_ids()` reads an audit ID from a split and creates one task for that audit. A vulnerability is scored inside the audit, so a runnable ten-case subset means ten audit directories, not ten individual finding files.

This subset retains the ten audit cases below and removes all other EVMbench audit fixtures and their split/inventory metadata.

| Audit | Why it is retained |
| --- | --- |
| `2024-01-renft` | Six vulnerabilities across an NFT-rental system using Gnosis Safe and Seaport; includes patch and live-exploit fixtures. |
| `2024-03-taiko` | 7,442 Solidity LOC / 80 contracts and five findings; the largest retained multi-finding rollup case. |
| `2024-05-arbitrum-foundation` | 3,603 LOC / 27 contracts; high-value dispute-resolution stake invariant. |
| `2024-05-olas` | 3,964 LOC / 28 contracts and cross-chain/tokenomics behavior; patch and exploit fixtures. |
| `2024-06-size` | 2,578 LOC / 32 contracts; retains race-condition and liquidation-accounting findings plus patch fixtures. |
| `2024-07-basin` | 2,414 LOC; the official paper shows GPT-5.1 identifying the access-control issue but failing its end-to-end exploit. |
| `2024-07-benddao` | 4,855 LOC / 42 contracts and seven lending/liquidation findings; patch and exploit fixtures. |
| `2024-08-phi` | Multi-step reentrancy task with signatures and a proxy; the official paper shows GPT-5 detecting/patching H-06 but failing to execute the exploit. |
| `2024-08-wildcat` | 3,784 LOC / 19 contracts; a high-value withdrawal-accounting failure. |
| `2025-05-blackhole` | 10,108 LOC / 116 contracts, the largest included codebase; reward-distribution drain finding. |

## Evidence and limitation

Primary source: OpenAI, *EVMbench: Evaluating AI Agents on Smart Contract Security*, `https://cdn.openai.com/evmbench/evmbench.pdf` (accessed 2026-08-07).

The official paper publishes aggregate results, not a public per-audit/per-vulnerability outcome matrix. It reports 120 Detect findings, 45 Patch findings, and 24 Exploit findings; aggregate no-hint performance includes o3 at 10.6% / 14.8% / 18.1% (Detect/Patch/Exploit), GPT-5 at 23.3% / 20.0% / 31.9%, and GPT-5.2 xhigh at 39.2% / 39.3% / 62.5%. The paper's published qualitative failures directly identify Basin H-01 and Phi H-06. It also documents a GPT-5.2 success on NOYA H-08, so NOYA is intentionally not retained as a hard-case exemplar.

No independently reproducible community-run, task-level result matrix was publicly available at selection time. Therefore this is a transparent **hardness-oriented subset**, not a claim that each retained audit has a measured zero-success rate across all older models. The selection combines the two published end-to-end failures with large/multi-contract, multi-finding, and stateful cross-contract cases that remain runnable in the benchmark.

## Benchmark contract

This is a dataset/version change: scores from this subset are only comparable to other runs using this exact Hard-10 fixture. It does not modify prompts, graders, tools, budgets, model settings, or scoring logic.
