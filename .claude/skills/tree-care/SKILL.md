---
name: tree-care
description: Set up, check and clean a working tree of this repository and the host around it. Use it when a session starts in a fresh or unfamiliar tree, before the first check run of a session, when a check refuses to start (no venv, wrong uv, no Node, missing Unix port or generated inputs, a held port), when installing a tier (generic, flash, bench), when disk space runs low or worktrees, caches and logs pile up, and before a clean-chroot leg. It reads readiness in seconds (scripts/_preflight.sh) and reports and clears space safely (scripts/_tidy.sh).
---

# Tree care: set up, check, clean

README.md "Install from scratch" and "Dev environment setup" are the reference; this is the short path and the two
helpers. The `work-routines` skill runs the checks, `bench-routines` the board.

## Is this tree ready? `scripts/_preflight.sh [--bench]`

One line per fact, `OK`, `WARN` or `FAIL`, each with its fix, in about two seconds and touching nothing: the uv pin,
an active venv that is this tree's own (`lint.sh` and `typecheck.sh` refuse any other), Python 3.11+, Node at
`.nvmrc`'s major and `node_modules`, the Unix-port binary (`scripts/_unix_port.sh check standard`) and its port-53
capability, the generated inputs a single test file needs, `typings/`, free disk, and port locks held by another
runner. `--bench` adds the bench variables and one MicroPython board on USB, with no board contact. Exit 1 on any
`FAIL`. Run it first in every new session and after any failure that names a missing tool.

## Set up

- One command per tier, each a superset of the one before: `uv run toolchain/setup_toolchain.py env --tier generic`
  (Python and website dependencies, Playwright's Chromium, the toolchain and its Unix-port builds), `--tier flash`
  (USB access and the board), `--tier bench` (the bridge and access point; passwordless sudo first, see
  `tests_hardware/README.md` "Prerequisites").
- `uv` must be exactly the version `pyproject.toml`'s `required-version` names; any other refuses to run. A host whose
  global `uv` differs keeps the pinned one outside the worktree (e.g. `~/.local/uv-0.13.7/bin`), first on PATH.
- Then `source .venv/bin/activate` in this tree. A second worktree gets its own `uv sync` and venv: the lint and type
  scripts refuse a venv that belongs to another tree.
- The host tier needs `node` on PATH; after `env` installs it, put its folder on PATH before `scripts/test.sh`.
- Generated inputs: `scripts/test.sh` rebuilds both on every run, a single-file run does not; alone, `uv run
  scripts/_generate_sensortask_modules.py` and `scripts/build_website.sh <device>` (test.sh uses the first device).
- `uv run toolchain/setup_toolchain.py test` re-verifies an installed toolchain offline in a few minutes; `setup
  --clean` rebuilds its build folders without re-cloning.
- A clean-chroot leg follows README.md "Build-environment verification" as written, in a real checkout, not a copied
  worktree (test.sh's checkout-write guard needs its own `.git`); its `env --tier generic` step installs the pinned Node.
  Run one leg at a time: legs share a network namespace but not a port-lock directory. A chroot's folders are root-only,
  so a glob into one runs inside `sudo -n bash -c`: in your own shell it expands to nothing. Check `/proc/mounts` before
  `rm -rf` of a chroot.

## Clean up: `scripts/_tidy.sh`

With no option it only reports: free space, the sizes of `build/`, `build/archive/`, `digital_twin_ci_logs/`,
`logs/`, `node_modules/`, `.venv/`, `typings/`, the cache count, untracked files that are not ignored, every
worktree (one marked `prunable` has lost its folder) and the check-log runs. It deletes only what you name:

- `--caches`: `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `tests/_tmp`.
- `--check-logs DAYS`: `scripts/_run_checks.sh` runs older than DAYS days.
- `--prune-worktrees`: `git worktree prune`, the records of worktrees whose folder is gone.

It never deletes evidence (`build/archive/`, `digital_twin_ci_logs/`, `logs/`), the venv, `node_modules` or the
toolchain. Never `rm -rf build/` by hand: `build/archive/` is the runners' evidence. Evidence goes only after it is copied out or no longer needed, and by hand; each runner keeps its newest
three archives on its own. A worktree you made is removed with `git worktree remove <path>` once its branch is merged
or abandoned, never with `rm -rf` while git still records it.

## Keep the repository lean

- Commit no logs, consoles, FRAM dumps or build output: they stay in git-ignored `logs/` or `build/`.
- Append to a long-lived record instead of rewriting it: a 3.5 MB hand-back rewritten 54 times left about 114 MB of
  blob versions in history.
- `rm` only literal paths, and look at what a path holds before deleting it. A variable in a `cp` or `rm` is checked as
  non-empty first: an empty `"$A".` copies or removes the current directory.
