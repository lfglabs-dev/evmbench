# ruff: noqa: S603, PT009
"""Offline checks for single-skill staging and the Codex launcher.

Run from the repository root with:
    python3 backend/worker_runner/test_single_skill.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = ROOT / 'backend' / 'worker_runner'
PREPARE = RUNNER_DIR / 'prepare-skill'
RUNNER = RUNNER_DIR / 'run_codex_detect.sh'
STAGING = RUNNER_DIR / 'active_skill'
DETECT = RUNNER_DIR / 'detect.md'
INIT = ROOT / 'backend' / 'docker' / 'worker' / 'init.py'


class SingleSkillTestCase(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(STAGING, ignore_errors=True)

    def prepare(self, selection: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(PREPARE), selection], capture_output=True, text=True, check=False)

    def test_raw_mode_installs_nothing(self) -> None:
        result = self.prepare('raw')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(STAGING.exists())

    def test_valid_package_stages_resources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'audit-method'
            (source / 'references').mkdir(parents=True)
            (source / 'scripts').mkdir()
            (source / 'SKILL.md').write_text('---\nname: audit-method\n---\nUse the method.\n', encoding='utf-8')
            (source / 'references' / 'guide.md').write_text('guide\n', encoding='utf-8')
            (source / 'scripts' / 'helper.py').write_text('print("helper")\n', encoding='utf-8')

            result = self.prepare(str(source))

        self.assertEqual(result.returncode, 0, result.stderr)
        metadata = json.loads((STAGING / 'metadata.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['name'], 'audit-method')
        self.assertEqual((STAGING / 'package' / 'references' / 'guide.md').read_text(encoding='utf-8'), 'guide\n')
        self.assertTrue((STAGING / 'package' / 'scripts' / 'helper.py').is_file())

        spec = importlib.util.spec_from_file_location('evmbench_worker_init_test', INIT)
        if spec is None or spec.loader is None:
            self.fail('unable to load worker init module')
        httpx_stub = types.ModuleType('httpx')
        httpx_stub.__dict__['AsyncClient'] = object
        loguru_stub = types.ModuleType('loguru')
        loguru_stub.__dict__['logger'] = types.SimpleNamespace(info=lambda _: None)
        sys.modules['httpx'] = httpx_stub
        sys.modules['loguru'] = loguru_stub
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.__dict__['ACTIVE_SKILL_DIR'] = STAGING
        module.__dict__['ACTIVE_SKILL_PACKAGE_DIR'] = STAGING / 'package'
        module.__dict__['ACTIVE_SKILL_METADATA_PATH'] = STAGING / 'metadata.json'
        with tempfile.TemporaryDirectory() as home:
            installed_name = module._install_active_skill(home=Path(home))  # noqa: SLF001
            installed = Path(home) / '.codex' / 'skills' / 'audit-method'
            self.assertEqual(installed_name, 'audit-method')
            self.assertEqual((installed / 'references' / 'guide.md').read_text(encoding='utf-8'), 'guide\n')
            self.assertTrue((installed / 'scripts' / 'helper.py').is_file())

    def test_missing_malformed_and_multi_skill_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / 'missing'
            malformed = root / 'malformed'
            malformed.mkdir()
            multi = root / 'multi'
            (multi / 'nested').mkdir(parents=True)
            (multi / 'SKILL.md').write_text('---\nname: multi\n---\n', encoding='utf-8')
            (multi / 'nested' / 'SKILL.md').write_text('nested\n', encoding='utf-8')

            for invalid in (missing, malformed, multi):
                result = self.prepare(str(invalid))
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(STAGING.exists(), f'stale stage survived: {invalid}')


class LauncherTestCase(unittest.TestCase):
    def run_launcher(self, active_skill: str | None) -> tuple[Path, bytes]:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            logs = home / 'logs'
            submission = home / 'submission'
            bin_dir = home / 'bin'
            bin_dir.mkdir()
            stub = bin_dir / 'codex'
            stub.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                'if [[ "$1" == login ]]; then exit 0; fi\n'
                'test "$1" = exec\n'
                'printf \'{"vulnerabilities": []}\\n\' > "$SUBMISSION_DIR/audit.md"\n',
                encoding='utf-8',
            )
            stub.chmod(0o755)
            env = os.environ | {
                'AGENT_DIR': str(home), 'SUBMISSION_DIR': str(submission), 'LOGS_DIR': str(logs),
                'OPENAI_API_KEY': 'test-token', 'CODEX_API_KEY': 'test-token', 'CODEX_MODEL': 'stub',
                'EVM_BENCH_DETECT_MD': str(DETECT), 'PATH': f'{bin_dir}:{os.environ["PATH"]}',
            }
            if active_skill:
                skill_md = home / '.codex' / 'skills' / active_skill / 'SKILL.md'
                skill_md.parent.mkdir(parents=True)
                skill_md.write_text('complete skill contents\n', encoding='utf-8')
                env['EVM_BENCH_ACTIVE_SKILL_NAME'] = active_skill
            result = subprocess.run([str(RUNNER)], env=env, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((submission / 'audit.md').is_file())
            return home, (home / 'AGENTS.md').read_bytes()

    def test_raw_prompt_is_byte_identical(self) -> None:
        _, rendered = self.run_launcher(None)
        self.assertEqual(rendered, DETECT.read_bytes())

    def test_active_skill_is_mandatory_without_model_call(self) -> None:
        _, rendered = self.run_launcher('audit-method')
        text = rendered.decode('utf-8')
        self.assertIn('You MUST read the complete `SKILL.md` before auditing', text)
        self.assertIn('.codex/skills/audit-method/SKILL.md', text)
        self.assertIn('remain authoritative if they conflict', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
