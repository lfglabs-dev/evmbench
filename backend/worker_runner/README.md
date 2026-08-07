# Worker runner assets

This folder contains the repo-owned assets that define the detect-only worker behavior.

The worker image copies this directory into the container at `/opt/evmbench/worker_runner/`.

## Files

- `detect.md`: the full instructions prompt copied to `$HOME/AGENTS.md` inside the worker container.
- `model_map.json`: maps UI model keys (sent as `AGENT_ID`) to Codex model IDs.
- `run_codex_detect.sh`: runs Codex once and ensures `submission/audit.md` was created.
- `prepare-skill`: validates and stages one local third-party skill package for the next worker-image build.

## Selecting one audit skill

The worker can compare the raw EVMbench prompt against **one** local audit-skill package at a time. It never downloads, vendors, or resolves third-party skill repositories automatically.

From the repository root, stage the desired mode before building the worker image:

```bash
# Raw baseline: no benchmark skill is copied or installed.
make prepare-skill SKILL=raw

# One local skill directory. It must have one root SKILL.md.
make prepare-skill SKILL=/absolute/path/to/specific-skill
```

The equivalent direct command is:

```bash
./backend/worker_runner/prepare-skill raw
./backend/worker_runner/prepare-skill /absolute/path/to/specific-skill
```

The selected package is staged in the gitignored `worker_runner/active_skill/` directory. A valid package has exactly one `SKILL.md`, located at the package root; nested `SKILL.md` files, missing roots, symlinks, and invalid skill names are rejected before a worker image can be built. Supporting files such as `references/` and helper scripts are copied with the package.

When staged, the worker image installs it at `$HOME/.codex/skills/<skill-name>`, logs its name and (when the source is in Git) its revision, and appends a mandatory instruction to the generated `AGENTS.md`. That instruction requires Codex to read the complete skill and apply its methodology, while EVMbench scope and JSON submission rules remain authoritative.

## Editing guidelines

- Prefer updating `detect.md` rather than hardcoding prompts in Python.
- Keep `model_map.json` in sync with the model options in the frontend.
- If you change where these files live in the image, update `backend/docker/worker/Dockerfile` and `backend/docker/worker/init.py`.

