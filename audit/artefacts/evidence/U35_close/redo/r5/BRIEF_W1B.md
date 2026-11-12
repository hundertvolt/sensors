# R5 close unit W1b: the D.15 member order beyond `src/`, by hand, and its check widened (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `w1b_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. The rule: SPECIFICATION.md D.15
(read it filtered: `grep -n "^## D.15"`, then that section only). Its check: `tests_scripts/test_code_conventions.py`
`d15_key()`, `_starter_role()`, `_import_time_names()`, `member_order()` and the `modules` fixture (src/ plus the
generated modules only today). Your row: `S/u35r/r5/CLOSE_STATUS.tsv` P09. Code: int `S/wt-u35int` at 886f8af0. You are
the only writing unit; the lead's gate runs in `S/wt-u35int` (never write there).

## Owner (verbatim)
- 2026-09-29 (OR96, the order's scope): "Concerning the function sorting: 1. a 2. a but not the unit tests themselves".
- 2026-10-27: "Option d is fine" (the sweep and the all-scope check at the close).
- 2026-11-10 14:57:50: "We still are at 40. Do (A), finish as planned" ((A): every close item by hand, this ~150-file
  sweep included; (B), the reorder by a throwaway script, was not chosen).
- 2026-11-09 22:27:31: "... Lean, functional, no losses, no gaps, efficient by smart design appropriate for limited
  devices like the rp2".

## Scope (the lead's reading of OR96 and D.15; apply it, do not re-decide it)
Every Python module in `tests/`, `digital_twin/`, `fakes/`, `buildgen/`, `toolchain/`, `scripts/`, `tests_scripts/`,
`tests_hardware/`, plus `js/*.js`: class members and the module-level function list, ordered by D.15's key exactly as
`d15_key()` computes it (dunders, then private, then public; Starters, Getters, Setters, Others; alphabetical within).
"The unit tests themselves" are out: in `tests/test_*.py`, `tests_scripts/test_*.py`, `tests_hardware/**/test_*.py`
and `tests_js/*.test.js` the module-level function list stays as it is (the tests and the helpers beside them); classes
defined in those files are ordered. `src/` is already checked; `ext/`, `legacy/`, `python/`, `arduino/` and the
generated modules are out. D.15's import-time exception applies as `_import_time_names()` computes it.

## Your work (worktree `S/wt-w1b`, branch `audit/w1b` from 886f8af0; create it; commit locally, never push)
1. Reorder by hand (Edit moves, not a generating script): a pure move per D.15's last paragraph, comments travelling
   with their code, no body, decorator, docstring or statement text changed; a topical heading whose block the order
   splits apart is removed, never left above methods it no longer labels; role headings stay (D.15).
2. Verify every touched file with an AST comparison you write in your scratch (never committed): the same set of
   definitions, each `ast.dump()` identical, and the non-definition statements in the same order. Report the count.
3. Widen `member_order()`'s inputs to the scopes above (the `modules` fixture or a second fixture; the leanest that
   holds), with the test-file rule as one condition. `js/`: order by hand; no JS check is added (no new mechanism
   without a source): D.15's last sentence names what is machine-checked (the Python scopes) and that `js/` is held by
   review. Update that one SPEC sentence, and the scope sentence if it still says "the test functions" (it becomes the
   module-level function list of those test files).
4. The empty `_PENDING_ASSERTS` and the code that reads it (`_asserts_by_function`, the pending branch of
   `no_assert()`) go (A.U37.02: an empty allow-list goes with its loader).

## Never
No renames, no body edits, no new helper modules, no behaviour change; never weaken a check. Never edit `ext/`; never
read `arduino/` (`':!arduino'` in every git grep and git log); never open `/root/.claude/`; no hardware. Credential
filter as common_r1 says. Scratch only under `S/u35r/r5/ftmp_w1b/`. While `S/u35/lead/heavy.lock` exists: reading,
editing and single test files that bind no port only.

## Checks and hand-back
`S/u23/rebuild.sh` your worktree; `lint_direct.sh` (through `S/u35/lead/run.sh`, which now sets uv 0.13.7, Node 26 and
the re-synced venv); the three mypy passes; `uv run pytest tests_scripts/test_code_conventions.py` plus every
tests_scripts test reading a file you touched; npm lint, typecheck and unit tests for `js/`; the AST comparison over
every touched file; then, under `S/u35/lead/heavy.lock` holding `w1b` (wait while it exists; `rm` it, literal path,
its own command), `scripts/test.sh` at -1 (PICO_TOOLCHAIN_DIR=S/tc-c) once. One commit; budget about 4 % of the week.
Hand back: `S/u35r/r5/HANDBACK_W1B.md` (at most 40 lines: files reordered per scope, the AST comparison's count, the
check's change, anything held back and why), your commit, one line per headline result, and last "nothing of mine is
running".
