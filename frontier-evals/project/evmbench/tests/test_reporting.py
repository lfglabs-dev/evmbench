from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evmbench.reporting import build_report, write_report


def _write_attempt(
    group: Path,
    *,
    audit_id: str,
    run_id: str,
    score: int,
    max_score: int,
    started_at: float,
    passed: list[bool],
    usage: dict[str, int] | None,
    submission: bool = True,
) -> None:
    run_dir = group / run_id
    (run_dir / "logs").mkdir(parents=True)
    (run_dir / "submission").mkdir()
    vulnerabilities = [
        {
            "vulnerability_id": f"H-{index:02d}",
            "score": int(found),
            "max_score": 1,
            "passed": found,
        }
        for index, found in enumerate(passed, start=1)
    ]
    grade: dict[str, Any] = {
        "component": "test",
        "grade": {
            "evmbench_result": {
                "audit_id": audit_id,
                "score": score,
                "max_score": max_score,
                "details": {"vulnerability_results": vulnerabilities},
            }
        },
    }
    (run_dir / "run.log").write_text(repr(grade) + "\n")
    (run_dir / "metadata.json").write_text(
        json.dumps({"time_start": started_at, "runtime_in_seconds": 12.5})
    )
    event: dict[str, Any]
    if usage is None:
        event = {"type": "turn.failed", "error": {"message": "provider error"}}
    else:
        event = {"type": "turn.completed", "usage": usage}
    (run_dir / "logs/agent.log").write_text(json.dumps(event) + "\n")
    if submission:
        (run_dir / "submission/audit.md").write_text("# Report\n")


def test_build_report_selects_latest_attempt_and_preserves_missing_usage(tmp_path: Path) -> None:
    first = tmp_path / "first-group"
    retry = tmp_path / "retry-group"
    _write_attempt(
        first,
        audit_id="audit-a",
        run_id="audit-a_old",
        score=0,
        max_score=1,
        started_at=1,
        passed=[False],
        usage=None,
        submission=False,
    )
    _write_attempt(
        retry,
        audit_id="audit-a",
        run_id="audit-a_new",
        score=1,
        max_score=1,
        started_at=2,
        passed=[True],
        usage={
            "input_tokens": 100,
            "cached_input_tokens": 40,
            "output_tokens": 10,
            "total_tokens": 110,
        },
    )

    report = build_report([first, retry])

    assert report["score"] == 1
    assert report["max_score"] == 1
    assert report["attempts"] == 2
    assert report["retries"] == 1
    assert report["per_audit"][0]["selected_run_id"] == "audit-a_new"
    assert report["vulnerabilities"][0]["outcome"] == "found"
    assert report["usage"]["attempts_without_usage"] == 1
    assert report["usage"]["totals"]["uncached_input_tokens"] == 60
    assert report["usage"]["totals"]["total_tokens"] == 110
    assert report["usage"]["totals"]["reasoning_output_tokens"] is None


def test_write_report_creates_clean_bundle_and_requires_force(tmp_path: Path) -> None:
    group = tmp_path / "group"
    _write_attempt(
        group,
        audit_id="audit-a",
        run_id="audit-a_run",
        score=1,
        max_score=1,
        started_at=1,
        passed=[True],
        usage={
            "input_tokens": 10,
            "cached_input_tokens": 4,
            "output_tokens": 2,
            "total_tokens": 12,
        },
    )
    report = build_report([group])
    output = tmp_path / "reports/example"

    write_report(output, report, title="Example", force=False)

    assert sorted(path.name for path in output.iterdir()) == [
        "README.md",
        "per_audit.csv",
        "report.json",
        "vulnerabilities.csv",
    ]
    assert "Score: 1/1" in (output / "README.md").read_text()
    with pytest.raises(FileExistsError):
        write_report(output, report, title="Example", force=False)
    write_report(output, report, title="Updated", force=True)
    assert (output / "README.md").read_text().startswith("# Updated")
