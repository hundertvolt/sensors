# R5 close unit PIN: the releases made during execution, moved (A.SDEP.25) (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `pin_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. The action: `audit/actions/SUPP_deps.md`
A.SDEP.25, and the family actions it names (A.SDEP.03-A.SDEP.10), the workaround re-checks (A.SDEP.11-A.SDEP.19) and
the records (A.SDEP.21); read them filtered. The pin table: `S/u35r/r5/HANDBACK_W2.md` item U01 (2026-11-10). Code: int
`S/wt-u35int` at 3bee346e. Unit W1a writes at the same time (tests/, digital_twin/, fakes/, scripts/, tests_scripts/,
pyproject.toml's `[tool.mypy]` overrides and `[tool.ruff]` per-file ignores): you own the pins and locks, and the fixes
the new tool versions demand.

## Owner (verbatim)
- 2026-09-30 (OR129.a (1)): "a short second check at B5 (U37) catches releases made during execution".
- 2026-11-10 14:57:50: "We still are at 40. Do (A), finish as planned".
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"

## Your work (worktree `S/wt-pin`, branch `audit/pin` from 3bee346e; create it; commit locally, never push)
1. Move every pin the table marks "would move" to its newest stable release, re-checked on the day: mypy, ruff, pytest,
   coverage, zizmor, types-pyserial (`pyproject.toml` `[dependency-groups]`, `uv.lock` by `uv lock`), uv's
   `required-version` and every place that names uv's version, Node (`.nvmrc`, `engines`, `@types/node`, the
   installer's expectations), the npm lock (vitest, eslint, globals, html-validate, playwright, stylelint 18 and its
   standard config 41, by `npm install`). MicroPython and its submodules, the stubs, Microdot, freezefs, picotool and the
   Actions stay: nothing newer.
2. Each family's action and workaround re-check (A.SDEP.03-A.SDEP.19) for what moved: a new ruff or mypy finding is
   fixed at its site (never a new ignore without the reason its rule needs; `select = ["ALL"]` stays); a stylelint or
   eslint major's config change follows its migration notes; a Playwright Chromium change reaches the CI install. After
   any uv.lock change, check the installed ruff and mypy versions against the pins (CLAUDE.md's uv.lock rule).
3. The records: A.SDEP.21's, BACKLOG's running list of build-environment changes since the chroot legs were last
   satisfied (one line per family moved), and every doc line that names a moved version. CLAUDE.md's MicroPython
   "Last run" line stays (MicroPython did not move).

## Never
Never move MicroPython or anything that rebuilds the firmware image. Never touch the shared venv `S/wt-base/.venv`,
`S/tc-c`, `S/tc-int` or `/root/pico-toolchain`: make your own venv (`UV_PROJECT_ENVIRONMENT=S/wt-pin/.venv`) and your
own Node under `S/u35r/r5/ftmp_pin/`, and run your checks with them (S/u35/lead/run.sh sets the shared ones: copy it
into your scratch with yours instead). The fetch steps (`uv lock`, `uv sync`, `npm install`, a Node download) need the
network: run only those outside the namespace. Never weaken a check or add a blanket ignore. Never edit `ext/`; never
read `arduino/` (`':!arduino'` in every git grep and git log); never open `/root/.claude/`; no hardware. Credential
filter as common_r1 says. Scratch only under `S/u35r/r5/ftmp_pin/`. While `S/u35/lead/heavy.lock` exists: reading,
editing, fetching and single test files that bind no port only.

## Checks and hand-back
With your venv and Node: `lint_direct.sh`'s passes, the three mypy passes, npm lint, typecheck and unit tests, the
Playwright smoke if its version moved; then, under `S/u35/lead/heavy.lock` holding `pin` (wait while it exists; `rm`
it, literal path, its own command), `scripts/test.sh` at -1 (PICO_TOOLCHAIN_DIR=S/tc-c) once. One commit; budget about
1.5 % of the week. Hand back: `S/u35r/r5/HANDBACK_PIN.md` (at most 40 lines: the moved table, per tool what its new
version demanded and where, anything you held back and why), your commit, one line per headline result, and last
"nothing of mine is running".
