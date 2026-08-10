---
name: quillshield-hard10-bundle
description: Combined QuillShield smart-contract security methodology for EVMbench Hard-10. Use for a complete Solidity vulnerability-discovery audit spanning behavioral state, DoS and griefing, external calls, arithmetic and input validation, oracles and flash loans, proxies, reentrancy, semantic guards, signature replay, and state invariants.
---

# QuillShield Hard-10 Bundle

Use this single bundled skill for the complete audit. The original QuillShield
analysis modules are preserved under `modules/`, with their supporting material
under `references/<module>/`.

## Required workflow

1. Read every file in `modules/` before beginning the audit. Treat each as a
   complementary analysis pass, not an optional alternative.
2. Use `behavioral-state-analysis.md` first to map the protocol, state, value
   flows, roles, invariants, and relevant attack surfaces.
3. Run the remaining specialized modules against that map. Skip only a check
   whose prerequisite is demonstrably absent, and record it as N/A internally.
4. When a module points to a reference, read the corresponding file in
   `references/<module>/`. Relative links in the module files have been
   rewritten for this bundle.
5. Cross-check overlapping hypotheses before reporting. Submit only
   evidence-backed, exploitable findings in the format required by EVMbench.

## Included modules

- `modules/behavioral-state-analysis.md`
- `modules/dos-griefing-analysis.md`
- `modules/external-call-safety.md`
- `modules/input-arithmetic-safety.md`
- `modules/oracle-flashloan-analysis.md`
- `modules/proxy-upgrade-safety.md`
- `modules/reentrancy-pattern-analysis.md`
- `modules/semantic-guard-analysis.md`
- `modules/signature-replay-analysis.md`
- `modules/state-invariant-detection.md`

The QuillShield Defender release-gate plugin is intentionally not included: it
targets deployment and CI/CD release readiness rather than comparable
detect-only vulnerability discovery for Hard-10.
