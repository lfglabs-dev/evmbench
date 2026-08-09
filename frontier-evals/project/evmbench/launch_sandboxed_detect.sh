#!/usr/bin/env bash
# Run EVMbench detect evaluations through the local static-key OAI sandbox.
# No provider credential is stored here: STATIC is resolved only by local oai-proxy.
set -euo pipefail

export OPENAI_API_KEY=STATIC
export OPENAI_BASE_URL="${EVM_BENCH_SANDBOX_HOST_URL:-http://127.0.0.1:8084/v1}"
# Agent workers run in Docker, so they must address the proxy through Docker Desktop.
export OAI_PROXY_BASE_URL="${EVM_BENCH_SANDBOX_DOCKER_URL:-http://host.docker.internal:8084}"

args=(
  evmbench.audit_split=detect-tasks
  evmbench.mode=detect
  evmbench.apply_gold_solution=False
  evmbench.log_to_run_dir=True
  evmbench.hint_level=none
  evmbench.solver=evmbench.nano.solver.EVMbenchSolver
  evmbench.solver.agent_id=codex-gpt-5.6-sol
  evmbench.solver.judge_model=gpt-5.6-sol
  evmbench.solver.judge_reasoning_effort=low
  evmbench.solver.disable_internet=False
  evmbench.solver.timeout=36000
  evmbench.n_tries=1
  runner.concurrency=2
  runner.recorder=nanoeval.json_recorder:json_recorder
)

if [[ -n "${EVM_BENCH_ACTIVE_SKILL_PATH:-}" ]]; then
  args+=("evmbench.solver.active_skill_path=${EVM_BENCH_ACTIVE_SKILL_PATH}")
fi

exec uv run python -m evmbench.nano.entrypoint "${args[@]}" "$@"
