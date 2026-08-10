#!/usr/bin/env bash
# Materialize the comparable QuillShield analysis skills as one Codex skill.
set -euo pipefail

if [[ "$#" -ne 2 ]]; then
  echo "Usage: $0 <quillshield-checkout> <bundle-output-dir>" >&2
  exit 2
fi

checkout_path="$1"
bundle_path="$2"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

modules=(
  behavioral-state-analysis
  dos-griefing-analysis
  external-call-safety
  input-arithmetic-safety
  oracle-flashloan-analysis
  proxy-upgrade-safety
  reentrancy-pattern-analysis
  semantic-guard-analysis
  signature-replay-analysis
  state-invariant-detection
)

if [[ ! -d "$checkout_path/.git" ]]; then
  echo "QuillShield checkout is unavailable: $checkout_path" >&2
  exit 1
fi

tmp_path="${bundle_path}.tmp.$$"
trap 'rm -rf "$tmp_path"' EXIT
rm -rf "$tmp_path"
install -d "$tmp_path/modules" "$tmp_path/references"

for module in "${modules[@]}"; do
  source_path="$checkout_path/plugins/$module/skills/$module"
  if [[ ! -f "$source_path/SKILL.md" ]]; then
    echo "Expected QuillShield module is unavailable: $source_path" >&2
    exit 1
  fi

  # The evaluator accepts one root SKILL.md only. Module guidance remains
  # verbatim in ordinary Markdown files and its supporting references keep a
  # module-specific directory so similarly named files cannot collide.
  cp "$source_path/SKILL.md" "$tmp_path/modules/$module.md"
  if [[ -d "$source_path/references" ]]; then
    cp -R "$source_path/references" "$tmp_path/references/$module"
    perl -0pi -e "s#\\{baseDir\\}/references/#../references/$module/#g" \
      "$tmp_path/modules/$module.md"
  fi
done

cp "$script_dir/quillshield-hard10-bundle-SKILL.md" "$tmp_path/SKILL.md"

rm -rf "$bundle_path"
mv "$tmp_path" "$bundle_path"
trap - EXIT
