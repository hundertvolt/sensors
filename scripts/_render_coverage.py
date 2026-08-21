#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["coverage"]
# ///
"""Merges the raw per-test-file line-hit JSON dumps written by tests/_coverage_runner.py (run under the MicroPython Unix port) into a single coverage.py CoverageData file, then lets coverage.py render the HTML/XML/markdown reports from it - the second half of the collect/render split described in SPECIFICATION.md Part E.5 ("Coverage").
Self-contained via `uv run` (like toolchain/setup_toolchain.py) rather than a pyproject.toml dev dependency: scripts/test.sh --coverage works standalone with only `uv` installed, without requiring `uv sync`/an activated venv first."""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import coverage


def merge_raw_dumps(raw_dir: str, repo_root: str) -> dict[str, list[int]]:
    merged: dict[str, set[int]] = {}
    raw_files = sorted(glob.glob(os.path.join(raw_dir, "*.json")))
    if not raw_files:
        raise SystemExit(f"No raw coverage dumps found in {raw_dir}")

    for raw_file in raw_files:
        with open(raw_file) as f:
            per_file_hits: dict[str, list[int]] = json.load(f)
        for rel_path, lines in per_file_hits.items():
            abs_path = os.path.join(repo_root, rel_path)
            merged.setdefault(abs_path, set()).update(lines)

    return {path: sorted(lines) for path, lines in merged.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", required=True, help="Directory of *.json line-hit dumps from tests/_coverage_runner.py")
    parser.add_argument("--src-dir", default="src", help="Directory whose *.py files anchor the report scope (default: src)")
    parser.add_argument("--html-dir", default="htmlcov", help="Output directory for the HTML report (default: htmlcov)")
    parser.add_argument("--xml-file", default="coverage.xml", help="Output path for the Cobertura XML report (default: coverage.xml)")
    parser.add_argument("--markdown-file", default="coverage_summary.md", help="Output path for a markdown summary table (default: coverage_summary.md)")
    parser.add_argument("--data-file", default=".coverage", help="coverage.py data file to write (default: .coverage)")
    args = parser.parse_args()

    repo_root = os.getcwd()
    merged_hits = merge_raw_dumps(args.raw_dir, repo_root)

    data_path = os.path.join(repo_root, args.data_file)
    if os.path.exists(data_path):
        os.remove(data_path)
    data = coverage.CoverageData(basename=data_path)
    data.add_lines(merged_hits)
    data.write()

    # Anchoring the report to every src/*.py file (not just ones a raw dump happened to mention)
    # is what makes an entirely untested src/ file show up as a real 0% row instead of silently
    # not appearing in the report at all -- confirmed directly against coverage.py's own morfs=
    # handling.
    src_files = sorted(os.path.abspath(p) for p in glob.glob(os.path.join(repo_root, args.src_dir, "*.py")))

    cov = coverage.Coverage(data_file=data_path)
    cov.load()
    cov.report(morfs=src_files)
    cov.html_report(morfs=src_files, directory=os.path.join(repo_root, args.html_dir))
    cov.xml_report(morfs=src_files, outfile=os.path.join(repo_root, args.xml_file))
    with open(os.path.join(repo_root, args.markdown_file), "w") as f:
        cov.report(morfs=src_files, output_format="markdown", file=f)

    print(f"\nHTML report:     {args.html_dir}/index.html")
    print(f"Cobertura XML:   {args.xml_file}")
    print(f"Markdown summary: {args.markdown_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
