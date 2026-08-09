from __future__ import annotations

import argparse
import re
from pathlib import Path

from evmbench.reporting import build_report, write_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a clean Markdown, JSON, and CSV report from graded EVMBench run groups."
    )
    parser.add_argument(
        "run_group_dirs",
        nargs="+",
        type=Path,
        help="One or more run-group directories. Later attempts replace earlier attempts for the same audit.",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Report folder name under reports/ (letters, numbers, dot, dash, and underscore only).",
    )
    parser.add_argument("--title", default=None, help="Markdown report title.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "reports",
        help="Parent output directory (default: reports/).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace the four generated files if this report already exists.",
    )
    args = parser.parse_args()
    if not SAFE_NAME.fullmatch(args.name):
        parser.error("--name must contain only letters, numbers, dot, dash, and underscore")
    try:
        report = build_report(args.run_group_dirs)
        output_dir = args.output_root / args.name
        write_report(
            output_dir,
            report,
            title=args.title or args.name.replace("-", " ").replace("_", " ").title(),
            force=args.force,
        )
    except (FileExistsError, ValueError) as error:
        parser.error(str(error))
    print(f"Wrote report to {output_dir}")


if __name__ == "__main__":
    main()
