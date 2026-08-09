# Free-skill benchmark prompts

Run one prompt in one fresh Conductor worktree on the branch that contains
`launch_sandboxed_detect.sh` and `scripts/run_free_skill_benchmark.sh`.
The runner downloads a public skill source into that worktree's ignored
`.context/evmbench-free-skills/` cache and uses the local OAI sandbox.

Do not start another condition in the same worktree. Keep the launched process
alive, monitor it to completion, and generate a report from its run group. The
skill sources are free, but each run consumes sandbox model quota.

## Raw baseline

```text
Use the latest repository state in this fresh worktree to run the raw EVMbench
Hard-10 baseline through the local OAI sandbox. Do not change source code or
stage a skill. Run `cd frontier-evals/project/evmbench &&
scripts/run_free_skill_benchmark.sh raw`. Monitor it to completion, generate a
report named raw-hard10-sandboxed, and summarize its run-group path, score, and
failed audits. Do not commit results.
```

## Skill conditions

For each condition below, send this exact prompt to a fresh agent after
replacing `<condition>` once:

```text
Use the latest repository state in this fresh worktree to run only the
`<condition>` free skill against EVMbench Hard-10 through the local OAI
sandbox. Do not modify source code or run another condition. Run
`cd frontier-evals/project/evmbench &&
scripts/run_free_skill_benchmark.sh <condition>`. Keep the process alive and
monitor it to completion. Generate a report named `<condition>-hard10-sandboxed`
and summarize its run-group path, score, and failed audits. Do not commit
results.
```

Copy the template once for each of these conditions:

- `cyfrin-solidity`
- `pashov-solidity-auditor`
- `quill-behavioral-state-analysis`
- `quill-dos-griefing-analysis`
- `quill-external-call-safety`
- `quill-input-arithmetic-safety`
- `quill-oracle-flashloan-analysis`
- `quill-proxy-upgrade-safety`
- `quill-reentrancy-pattern-analysis`
- `quill-semantic-guard-analysis`
- `quill-signature-replay-analysis`
- `quill-state-invariant-detection`

Cyfrin BattleChain, Pashov Fizz/X-Ray, and QuillShield Defender are excluded: they target deployment, fuzz harnesses, pre-audit readiness, or release gates rather than comparable detect-only vulnerability discovery.
