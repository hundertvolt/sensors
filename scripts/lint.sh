#!/usr/bin/env bash
# Every non-type lint pass: ruff over the eight scopes plus the generated device modules, shellcheck over scripts/,
# actionlint + zizmor over the workflows, the method-assign guard and the gc-site checker - all stay fully clean.
# `ruff format` is unused (agent, 2026-07-13).
set -euo pipefail

usage="Usage: scripts/lint.sh - no arguments; needs the project venv active (uv sync && source .venv/bin/activate)"
if [ "$#" -gt 0 ]; then
    if [ "$#" -eq 1 ] && { [ "$1" = "-h" ] || [ "$1" = "--help" ]; }; then
        echo "$usage"
        exit 0
    fi
    echo "error: unknown argument $1 - $usage" >&2
    exit 2
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_require_venv.sh
require_project_venv ruff shellcheck actionlint zizmor
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_require_python.sh
require_python311
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_summary_block.sh
summary_unit checks

status=0
# Each check is recorded by name after its own block, never inside one: the guard is extracted and run alone by
# tests_scripts/test_lint_sh.py, with only `status` defined.
_check_begin() {
    _status_before="$status"
    status=0
}
_check_end() {
    if [ "$status" -eq 0 ]; then
        summary_add passed "$1"
    else
        summary_add failed "$1"
    fi
    [ "$_status_before" -eq 0 ] || status=1
}

# The generated device modules are linted like src/, so they are written first, from the venv just checked.
_check_begin
uv run --no-sync scripts/_generate_sensortask_modules.py || status=1
_check_end generation

_check_begin
ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts build/generated_src || status=1
_check_end ruff

# scripts/ only: the legacy tree (legacy/, its legacy/firmware/build-*.sh included) is never in a lint scope
# (CLAUDE.md legacy rule).
_check_begin
shellcheck scripts/*.sh || status=1
_check_end shellcheck

# Catches workflow expression/context typos that otherwise only surface as a broken CI run.
_check_begin
actionlint || status=1
_check_end actionlint

# GitHub Actions security audit: token permissions, credential persistence, action pinning.
# --offline drops the two audits needing the GitHub API, so this behaves identically with or
# without network - in CI, in the clean chroot and on a dev box. Config: .github/zizmor.yml.
_check_begin
zizmor --offline .github/ || status=1
_check_end zizmor

# grep_guard RULE MESSAGE GREP_ARGS...: a match prints the hits and fails, no match passes, and a grep that could not
# search (exit 2: an unreadable tree, a bad pattern) fails too - a guard that did not look never reads as clean.
grep_guard() {
    local rule="$1" message="$2" rc=0
    shift 2
    grep "$@" || rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "$message" >&2
        status=1
    elif [ "$rc" -ge 2 ]; then
        echo "error: lint.sh could not search ($*, grep exit $rc) - the $rule guard did not look" >&2
        status=1
    fi
}

# mypy cannot express this rule, because it only ever sees a suppression that is already written:
# tests/ and digital_twin/ legitimately monkeypatch methods, shipped src/ never may (owner,
# 2026-09-10), full reasoning in CLAUDE.md's "Code quality tooling".
_check_begin
grep_guard method-assign "error: src/ must never suppress method-assign - reassigning a method on shipped firmware code is the defect, not the type error." -rn "type: ignore\[[^]]*method-assign" src/
_check_end "method-assign guard"

# gc.collect()/gc.threshold() sites: one AST checker, every allowed site named there (SPECIFICATION.md I.4(e)/(f.1)).
_check_begin
python3 scripts/_check_gc_collect_sites.py || status=1
_check_end "gc sites"

# summary_print returns the code it printed; the run exits with it.
summary_status=0
summary_print "scripts/lint.sh" "$status" || summary_status=$?
exit "$summary_status"
