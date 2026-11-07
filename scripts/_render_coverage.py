#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["coverage==7.16.2"]
# ///
"""Renders the Unix-port coverage dumps (tests/_coverage_runner.py's JSON) into coverage.py data, then HTML and a
markdown summary for one traced directory (SPECIFICATION.md E.5)."""

import argparse
import json
from pathlib import Path

import coverage


def anchor_files(repo_root: str, src_dir: str) -> list[str]:
    # Anchoring the report to every .py file under src_dir (subdirectories included), not only
    # those a raw dump happened to mention, is what makes an entirely untested file appear as a
    # real 0% row rather than not at all - confirmed against coverage.py's own morfs= handling.
    return sorted(str(path.absolute()) for path in Path(repo_root, src_dir).glob("**/*.py"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", required=True, help="Directory of *.json line-hit dumps from tests/_coverage_runner.py")
    parser.add_argument("--src-dir", default="src", help="Directory whose *.py files, subdirectories included, anchor the report scope (default: src)")
    parser.add_argument("--html-dir", default="htmlcov", help="Output directory for the HTML report (default: htmlcov)")
    parser.add_argument("--markdown-file", default="coverage_summary.md", help="Output path for a markdown summary table (default: coverage_summary.md)")
    parser.add_argument("--data-file", default=".coverage", help="coverage.py data file to write (default: .coverage)")
    args = parser.parse_args()

    repo_root = Path.cwd()
    merged_hits = merge_raw_dumps(args.raw_dir, repo_root)

    data_path = repo_root / args.data_file
    data_path.unlink(missing_ok=True)
    data = coverage.CoverageData(basename=str(data_path))
    data.add_lines(merged_hits)
    data.write()

    src_files = anchor_files(str(repo_root), args.src_dir)

    cov = coverage.Coverage(data_file=str(data_path))
    cov.load()
    cov.report(morfs=src_files)
    cov.html_report(morfs=src_files, directory=str(repo_root / args.html_dir))
    with (repo_root / args.markdown_file).open("w", encoding="utf-8") as f:
        cov.report(morfs=src_files, output_format="markdown", file=f)

    print(f"\nHTML report:     {args.html_dir}/index.html")
    print(f"Markdown summary: {args.markdown_file}")
    return 0


def merge_raw_dumps(raw_dir: str, repo_root: Path) -> dict[str, list[int]]:
    merged: dict[str, set[int]] = {}
    raw_files = sorted(Path(raw_dir).glob("*.json"))
    if not raw_files:
        raise SystemExit(f"No raw coverage dumps found in {raw_dir}")

    for raw_file in raw_files:
        with raw_file.open(encoding="utf-8") as f:
            per_file_hits: dict[str, list[int]] = json.load(f)
        for rel_path, lines in per_file_hits.items():
            merged.setdefault(str(repo_root / rel_path), set()).update(lines)

    return {path: sorted(lines) for path, lines in merged.items()}


if __name__ == "__main__":
    raise SystemExit(main())
