#!/usr/bin/env bash
# Every non-type lint pass in one place: ruff over the eight scopes CLAUDE.md's "Code quality
# tooling" lists, shellcheck over scripts/, actionlint + zizmor over the workflows. All stay fully
# clean. Lint only - `ruff format` is deliberately unused (pyproject.toml's [tool.ruff]).
#
# Assumes `uv sync` has been run and its venv is active: every tool here installs from
# pyproject.toml's [dependency-groups].
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

status=0

ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts || status=1

# scripts/ only, deliberately NOT the four legacy build-*.sh at the repo root: those belong to the
# same pre-refactor generation as python//modules/ and are out of lint scope by the same standing
# decision (they carry 28 findings of their own, including no shebang at all - see BACKLOG.md).
shellcheck scripts/*.sh || status=1

# Catches workflow expression/context typos that otherwise only surface as a broken CI run.
actionlint || status=1

# GitHub Actions security audit: token permissions, credential persistence, action pinning.
# --offline drops the two audits needing the GitHub API, so this behaves identically with or
# without network - in CI, in the clean chroot and on a dev box. Config: .github/zizmor.yml.
zizmor --offline .github/ || status=1

# mypy cannot express this rule, because it only ever sees a suppression that is already written:
# tests/ and digital_twin/ legitimately monkeypatch methods, shipped src/ never may. Owner's
# direction, full reasoning in CLAUDE.md's "Code quality tooling".
if grep -rn "type: ignore\[[^]]*method-assign" src/; then
    echo "error: src/ must never suppress method-assign - reassigning a method on shipped firmware code is the defect, not the type error." >&2
    status=1
fi

# `gc.collect()` is confined to the two one-time boot lists - system_service.py's task-starter loop
# and the setup batch buildgen/codegen.py emits - and nothing else (SPECIFICATION.md Part I.4(f.1);
# digital_twin/ and tests/ are out of scope there, per I.4(e) and Part F.6).
#
# tests_scripts/test_gc_collect_sites.py asserts the same thing structurally, by enclosing function;
# this grep is the fast path that fails the gate before the suite runs.
if grep -rn --include="*.py" "gc\.collect(" src/ | grep -v "^src/system_service.py:"; then
    echo "error: gc.collect() in src/ is confined to system_service.py's task-starter list (SPECIFICATION.md Part I.4(f.1))." >&2
    status=1
fi
if grep -rn --include="*.py" "gc\.collect(" buildgen/ | grep -v "^buildgen/codegen.py:"; then
    echo "error: gc.collect() in buildgen/ is confined to codegen.py's emitted boot batch (SPECIFICATION.md Part I.4(f.1))." >&2
    status=1
fi

exit "$status"
