#!/usr/bin/env bash
# Run one comparable free-skill condition of the EVMbench Hard-10 suite.
set -euo pipefail

condition="${1:---list}"
eval_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_dir="$(cd "$eval_dir/../../.." && pwd)"
skill_cache="$workspace_dir/.context/evmbench-free-skills"

usage() {
  cat <<'EOF'
Usage: scripts/run_free_skill_benchmark.sh <condition>

Conditions:
  raw
  cyfrin-solidity
  pashov-solidity-auditor
  quill-behavioral-state-analysis
  quill-dos-griefing-analysis
  quill-external-call-safety
  quill-input-arithmetic-safety
  quill-oracle-flashloan-analysis
  quill-proxy-upgrade-safety
  quill-reentrancy-pattern-analysis
  quill-semantic-guard-analysis
  quill-signature-replay-analysis
  quill-state-invariant-detection
EOF
}

if [[ "$condition" == "--list" || "$condition" == "-h" || "$condition" == "--help" ]]; then
  usage
  exit 0
fi

source_url=""
checkout_name=""
skill_relative_path=""
case "$condition" in
  raw) ;;
  cyfrin-solidity)
    source_url="https://github.com/Cyfrin/solskill.git"
    checkout_name="cyfrin-solskill"
    skill_relative_path="skills/solidity"
    ;;
  pashov-solidity-auditor)
    source_url="https://github.com/pashov/skills.git"
    checkout_name="pashov-skills"
    skill_relative_path="solidity-auditor"
    ;;
  quill-*)
    source_url="https://github.com/quillai-network/qs_skills.git"
    checkout_name="quillshield-skills"
    skill_name="${condition#quill-}"
    skill_relative_path="plugins/$skill_name/skills/$skill_name"
    ;;
  *)
    echo "Unknown condition: $condition" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ "$condition" != "raw" ]]; then
  checkout_path="$skill_cache/$checkout_name"
  if [[ ! -d "$checkout_path/.git" ]]; then
    mkdir -p "$skill_cache"
    git clone --depth 1 "$source_url" "$checkout_path"
  fi

  skill_path="$checkout_path/$skill_relative_path"
  if [[ ! -f "$skill_path/SKILL.md" ]]; then
    echo "Expected skill package is unavailable: $skill_path" >&2
    exit 1
  fi
  export EVM_BENCH_ACTIVE_SKILL_PATH="$skill_path"
else
  unset EVM_BENCH_ACTIVE_SKILL_PATH || true
fi

run_root="$eval_dir/runs/free-skills/$condition"
mkdir -p "$run_root"
exec "$eval_dir/launch_sandboxed_detect.sh" "evmbench.runs_dir=$run_root"
