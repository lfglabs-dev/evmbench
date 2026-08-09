from __future__ import annotations

import ast
import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPORT_FILENAMES = ("README.md", "report.json", "per_audit.csv", "vulnerabilities.csv")
TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens")


@dataclass(frozen=True)
class Attempt:
    audit_id: str
    run_id: str
    run_group: str
    score: float
    max_score: float
    started_at: float
    runtime_seconds: float | None
    submission_present: bool
    terminal_event: str | None
    usage: Mapping[str, int] | None
    vulnerabilities: tuple[Mapping[str, Any], ...]


def _find_grade(run_log: Path) -> Mapping[str, Any] | None:
    for line in reversed(run_log.read_text(errors="replace").splitlines()):
        if "'grade':" not in line:
            continue
        try:
            payload = ast.literal_eval(line)
        except (SyntaxError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        grade = payload.get("grade")
        if isinstance(grade, dict) and isinstance(grade.get("evmbench_result"), dict):
            return grade
    return None


def _agent_result(agent_log: Path) -> tuple[str | None, Mapping[str, int] | None]:
    terminal_event = None
    usage = None
    if not agent_log.is_file():
        return terminal_event, usage
    for line in agent_log.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        if event_type in {"turn.completed", "turn.failed"}:
            terminal_event = str(event_type)
        raw_usage = event.get("usage")
        if event_type == "turn.completed" and isinstance(raw_usage, dict):
            usage = {
                key: value
                for key, value in raw_usage.items()
                if isinstance(key, str) and isinstance(value, int)
            }
    return terminal_event, usage


def _metadata(run_dir: Path) -> tuple[float, float | None]:
    metadata_path = run_dir / "metadata.json"
    if not metadata_path.is_file():
        return run_dir.stat().st_mtime, None
    try:
        metadata = json.loads(metadata_path.read_text())
    except (json.JSONDecodeError, OSError):
        return run_dir.stat().st_mtime, None
    started_at = metadata.get("time_start")
    runtime = metadata.get("runtime_in_seconds")
    return (
        float(started_at) if isinstance(started_at, (int, float)) else run_dir.stat().st_mtime,
        float(runtime) if isinstance(runtime, (int, float)) else None,
    )


def load_attempts(run_group_dirs: Sequence[Path]) -> list[Attempt]:
    attempts: list[Attempt] = []
    for run_group in run_group_dirs:
        if not run_group.is_dir():
            raise ValueError(f"Run-group directory not found: {run_group}")
        for run_log in sorted(run_group.glob("*/run.log")):
            grade = _find_grade(run_log)
            if grade is None:
                continue
            result = grade["evmbench_result"]
            audit_id = result.get("audit_id")
            if not isinstance(audit_id, str):
                continue
            run_dir = run_log.parent
            started_at, runtime = _metadata(run_dir)
            terminal_event, usage = _agent_result(run_dir / "logs/agent.log")
            details = result.get("details")
            raw_vulnerabilities = details.get("vulnerability_results", []) if isinstance(details, dict) else []
            vulnerabilities = tuple(item for item in raw_vulnerabilities if isinstance(item, dict))
            attempts.append(
                Attempt(
                    audit_id=audit_id,
                    run_id=run_dir.name,
                    run_group=run_group.name,
                    score=float(result.get("score", 0)),
                    max_score=float(result.get("max_score", 0)),
                    started_at=started_at,
                    runtime_seconds=runtime,
                    submission_present=any(
                        path.is_file() and path.stat().st_size > 0
                        for path in (run_dir / "submission").glob("*")
                    ),
                    terminal_event=terminal_event,
                    usage=usage,
                    vulnerabilities=vulnerabilities,
                )
            )
    if not attempts:
        raise ValueError("No graded EVMBench attempts found in the supplied run groups")
    return attempts


def _selected_attempts(attempts: Sequence[Attempt]) -> list[Attempt]:
    selected: dict[str, Attempt] = {}
    for attempt in sorted(attempts, key=lambda item: (item.started_at, item.run_id)):
        selected[attempt.audit_id] = attempt
    return [selected[audit_id] for audit_id in sorted(selected)]


def _normalize_number(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def _usage_summary(attempts: Sequence[Attempt]) -> dict[str, Any]:
    available = [attempt.usage for attempt in attempts if attempt.usage is not None]
    totals: dict[str, int | None] = {}
    for field in TOKEN_FIELDS:
        totals[field] = (
            sum(usage[field] for usage in available)
            if available and all(field in usage for usage in available)
            else None
        )
    cached = totals["cached_input_tokens"]
    input_tokens = totals["input_tokens"]
    totals["uncached_input_tokens"] = (
        input_tokens - cached
        if isinstance(input_tokens, int) and isinstance(cached, int)
        else None
    )
    totals["total_tokens"] = (
        input_tokens + totals["output_tokens"]
        if isinstance(input_tokens, int) and isinstance(totals["output_tokens"], int)
        else None
    )
    optional_fields = ("reasoning_output_tokens", "cache_write_tokens")
    for field in optional_fields:
        totals[field] = (
            sum(usage[field] for usage in available)
            if available and all(field in usage for usage in available)
            else None
        )
    return {
        "attempts_with_usage": len(available),
        "attempts_without_usage": len(attempts) - len(available),
        "complete": len(available) == len(attempts),
        "totals": totals,
    }


def build_report(run_group_dirs: Sequence[Path]) -> dict[str, Any]:
    attempts = load_attempts(run_group_dirs)
    selected = _selected_attempts(attempts)
    total_score = sum(attempt.score for attempt in selected)
    total_max_score = sum(attempt.max_score for attempt in selected)
    vulnerabilities: list[dict[str, Any]] = []
    for attempt in selected:
        for vulnerability in attempt.vulnerabilities:
            passed = bool(vulnerability.get("passed", False))
            vulnerabilities.append(
                {
                    "audit_id": attempt.audit_id,
                    "vulnerability_id": str(vulnerability.get("vulnerability_id", "unknown")),
                    "outcome": "found" if passed else "missed",
                    "score": vulnerability.get("score"),
                    "max_score": vulnerability.get("max_score"),
                }
            )
    attempt_counts: dict[str, int] = {}
    for attempt in attempts:
        attempt_counts[attempt.audit_id] = attempt_counts.get(attempt.audit_id, 0) + 1
    per_audit = [
        {
            "audit_id": attempt.audit_id,
            "score": _normalize_number(attempt.score),
            "max_score": _normalize_number(attempt.max_score),
            "score_percentage": attempt.score / attempt.max_score * 100 if attempt.max_score else None,
            "attempts": attempt_counts[attempt.audit_id],
            "selected_run_id": attempt.run_id,
            "selected_run_group": attempt.run_group,
            "runtime_seconds": attempt.runtime_seconds,
            "submission_present": attempt.submission_present,
            "terminal_event": attempt.terminal_event,
        }
        for attempt in selected
    ]
    return {
        "schema_version": 1,
        "source_run_groups": [path.name for path in run_group_dirs],
        "score": _normalize_number(total_score),
        "max_score": _normalize_number(total_max_score),
        "score_percentage": total_score / total_max_score * 100 if total_max_score else None,
        "audits": len(selected),
        "attempts": len(attempts),
        "retries": len(attempts) - len(selected),
        "found": sum(item["outcome"] == "found" for item in vulnerabilities),
        "missed": sum(item["outcome"] == "missed" for item in vulnerabilities),
        "per_audit": per_audit,
        "vulnerabilities": vulnerabilities,
        "usage": _usage_summary(attempts),
    }


def _display(value: object) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def render_markdown(report: Mapping[str, Any], title: str) -> str:
    percentage = report.get("score_percentage")
    percentage_text = f"{percentage:.2f}%" if isinstance(percentage, (int, float)) else "unavailable"
    lines = [
        f"# {title}",
        "",
        f"**Score: {_display(report['score'])}/{_display(report['max_score'])} ({percentage_text})**",
        "",
        (
            f"Audits: {report['audits']} · Attempts: {report['attempts']} · "
            f"Retries: {report['retries']} · Found: {report['found']} · Missed: {report['missed']}"
        ),
        "",
        "## Per-audit scores",
        "",
        "| Audit | Score | Attempts | Runtime | Submission | Terminal event |",
        "|---|---:|---:|---:|---|---|",
    ]
    for item in report["per_audit"]:
        runtime = item["runtime_seconds"]
        runtime_text = f"{runtime:.2f}s" if isinstance(runtime, (int, float)) else "unavailable"
        lines.append(
            f"| {item['audit_id']} | {_display(item['score'])}/{_display(item['max_score'])} | "
            f"{item['attempts']} | {runtime_text} | {'yes' if item['submission_present'] else 'no'} | "
            f"{item['terminal_event'] or 'unavailable'} |"
        )
    lines.extend(
        [
            "",
            "## Vulnerability outcomes",
            "",
            "| Audit | Vulnerability | Outcome |",
            "|---|---|---|",
        ]
    )
    for item in report["vulnerabilities"]:
        lines.append(f"| {item['audit_id']} | {item['vulnerability_id']} | {item['outcome']} |")
    usage = report["usage"]
    totals = usage["totals"]
    lines.extend(
        [
            "",
            "## Token usage",
            "",
            f"Usage was available for {usage['attempts_with_usage']}/{report['attempts']} attempts.",
            "",
            "| Metric | Tokens |",
            "|---|---:|",
            f"| Input | {_display(totals['input_tokens'])} |",
            f"| Cached input | {_display(totals['cached_input_tokens'])} |",
            f"| Uncached input | {_display(totals['uncached_input_tokens'])} |",
            f"| Output | {_display(totals['output_tokens'])} |",
            f"| Reasoning | {_display(totals['reasoning_output_tokens'])} |",
            f"| Cache writes | {_display(totals['cache_write_tokens'])} |",
            f"| Total | {_display(totals['total_tokens'])} |",
            "",
            "Missing usage fields are reported as unavailable, never as zero.",
            "",
            "## Source run groups",
            "",
        ]
    )
    lines.extend(f"- `{path}`" for path in report["source_run_groups"])
    return "\n".join(lines) + "\n"


def _csv_text(rows: Iterable[Mapping[str, Any]], fieldnames: Sequence[str]) -> str:
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def write_report(output_dir: Path, report: Mapping[str, Any], *, title: str, force: bool) -> None:
    existing = [output_dir / name for name in REPORT_FILENAMES if (output_dir / name).exists()]
    if existing and not force:
        raise FileExistsError(
            f"Report already exists at {output_dir}; pass --force to replace its generated files"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "README.md").write_text(render_markdown(report, title))
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (output_dir / "per_audit.csv").write_text(
        _csv_text(
            report["per_audit"],
            ("audit_id", "score", "max_score", "score_percentage", "attempts", "runtime_seconds", "submission_present", "terminal_event", "selected_run_id", "selected_run_group"),
        )
    )
    (output_dir / "vulnerabilities.csv").write_text(
        _csv_text(
            report["vulnerabilities"],
            ("audit_id", "vulnerability_id", "outcome", "score", "max_score"),
        )
    )
