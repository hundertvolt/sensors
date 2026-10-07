#!/usr/bin/env bash
# Every non-type lint pass in one place: ruff over the eight scopes CLAUDE.md's "Code quality
# tooling" lists, shellcheck over scripts/, actionlint + zizmor over the workflows. All stay fully
# clean. Lint only - `ruff format` is unused (agent, 2026-07-13; pyproject.toml's [tool.ruff]).
#
# Assumes `uv sync` has been run and its venv is active: every tool here installs from
# pyproject.toml's [dependency-groups].
set -euo pipefail

usage="Usage: scripts/lint.sh - no arguments; needs the project venv active (uv sync && source .venv/bin/activate)"
if [ "$#" -gt 0 ]; then
    if [ "$#" -eq 1 ] && { [ "$1" = "-h" ] || [ "$1" = "--help" ]; }; then
        echo "$usage"
        exit 0
    fi
    echo "$usage" >&2
    exit 2
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_summary_block.sh
summary_unit checks

status=0
# Each check is recorded by name after its own block, never inside one: the guard blocks below are
# extracted and run alone by tests_scripts/test_lint_sh.py, with only `status` defined.
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

_check_begin
ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts || status=1
_check_end ruff

# scripts/ only: the legacy tree (legacy/, its legacy/firmware/build-*.sh included) is never in a
# lint scope (CLAUDE.md legacy rule).
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

# mypy cannot express this rule, because it only ever sees a suppression that is already written:
# tests/ and digital_twin/ legitimately monkeypatch methods, shipped src/ never may (owner,
# 2026-09-10), full reasoning in CLAUDE.md's "Code quality tooling".
_check_begin
if grep -rn "type: ignore\[[^]]*method-assign" src/; then
    echo "error: src/ must never suppress method-assign - reassigning a method on shipped firmware code is the defect, not the type error." >&2
    status=1
fi
_check_end "method-assign guard"

# `gc.collect()` is confined to the two one-time boot lists - asy_system_service.py's task-starter loop
# and the setup batch buildgen/codegen.py emits - and nothing else (SPECIFICATION.md Part I.4(f.1);
# digital_twin/ and tests/ are out of scope there, per I.4(e) and Part F.6).
#
# tests_scripts/test_gc_collect_sites.py asserts the same thing structurally, by enclosing function;
# this grep is the fast path that fails the gate before the suite runs.
_check_begin
if grep -rn --include="*.py" "gc\.collect(" src/ | grep -v "^src/asy_system_service.py:"; then
    echo "error: gc.collect() in src/ is confined to asy_system_service.py's task-starter list (SPECIFICATION.md Part I.4(f.1))." >&2
    status=1
fi
if grep -rn --include="*.py" "gc\.collect(" buildgen/ | grep -v "^buildgen/codegen.py:"; then
    echo "error: gc.collect() in buildgen/ is confined to codegen.py's emitted boot batch (SPECIFICATION.md Part I.4(f.1))." >&2
    status=1
fi
_check_end "gc.collect sites"

# summary_print returns the code it printed; the run exits with it.
summary_status=0
summary_print "scripts/lint.sh" "$status" || summary_status=$?
exit "$summary_status"
