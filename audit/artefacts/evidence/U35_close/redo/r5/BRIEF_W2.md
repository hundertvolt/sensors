# R5 close unit W2: the docs and release items the close list holds open (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all: SPECIFICATION.md, CLAUDE.md, BACKLOG.md,
README.md, `devices/` and `audit/` are never viewed unfiltered; label `w2_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Your rows, with their evidence:
`S/u35r/r5/CLOSE_STATUS.tsv` (U01, P08, B40, N05, N03, U04 (6), P06, P05, P04, S03). The release items' actions:
`audit/actions/U37.md` A.U37.10-A.U37.12 (from :290; filtered). FINDINGS 12.90, 12.95, 12.168, 12.171. Code: int
`S/wt-u35int` at 651af010. Unit W1a writes at the same time (tests/, digital_twin/, fakes/, scripts/, pyproject.toml,
the .ini files, most of tests_scripts/, BACKLOG's B01 and B37 items, SPEC's fidelity row 222 and Part N
`udp.poll_idle_ms`): yours are the files named below.

## Owner (verbatim)
- 2026-11-10 14:57:50: "We still are at 40. Do (A), finish as planned".
- Working agreement (CLAUDE.md): documentation holds current state, targets and rules, not the path that got there.

## Your work (worktree `S/wt-w2`, branch `audit/w2` from 651af010; create it; commit locally, never push)
1. U01: every pin in `toolchain/versions.toml` and the stub pins against its newest stable release (MicroPython,
   Microdot, pico-sdk, the tools); re-date CLAUDE.md's "Last run" line only if nothing moves. A pin that would move is
   not moved: report it with its release and what it would reopen (a new MicroPython reopens the image).
2. BACKLOG: P08 (the build-environment bullet, about :379-383, to FINDINGS 12.90/12.95's state, plus 226be25f's single
   apt install), B40 (about :241-251: no code 4 exists, `src/asy_system_service.py:86-98`; the bench test expects 2),
   N05 (about :79-80: `supervisor_scan_timing.py` and its flash test exist). README: N03/U04 (6), "Further reading"
   names every tracked skill under `.claude/skills/`.
3. P06: README's Release section from A.U37.12's list, measured against legacy, the pins named; short, current fact.
4. P05: the release version (A.U37.11: `buildgen/version.py`, `tests_scripts/test_buildgen_version.py`,
   `mockdata/samples.json`, SPEC L.7, README). The number waits for the owner (the lead forwards it): do everything
   else first, P05 last; if the number has not come by your hand-back, leave P05 and say so.
5. P04 + S03: the golden fixtures at the release point (A.U37.10): commit the generated JSON for every device under
   `tests_scripts/golden/` and `tests_scripts/fixtures/api_reference/`; `test_stored_config_golden.py` and
   `test_api_reference.py` compare against them and name the regenerate command on a mismatch. These three test files
   are yours whole, their import-placement entries included (module-level imports, `_PENDING` entries dropped).

## Never
Never change a rule's meaning, an owner quote's words, a number's value or a `src/` code line. Never move a pin. Never
edit `ext/`; never read `arduino/` (`':!arduino'` in every git grep and git log); never open `/root/.claude/`; no
hardware. Credential filter as common_r1 says; the hotspot fallback literal is never printed, copied or written.
Scratch only under `S/u35r/r5/ftmp_w2/`. While `S/u35/lead/heavy.lock` exists: reading, editing and single test files
that bind no port only.

## Checks and hand-back
Every tests_scripts test that reads a file you touched; `lint_direct.sh`; the host mypy pass; then, under
`S/u35/lead/heavy.lock` holding `w2` (wait while it exists; `rm` it, literal path, its own command), `uv run pytest
tests_scripts` once and `S/u23/rebuild.sh` plus the firmware build for `dev` (imageFreeBytes against 651af010). One
commit; budget about 1.5 % of the week. Hand back: `S/u35r/r5/HANDBACK_W2.md` (at most 40 lines: per item what changed,
U01's pin table, whether P05 is done), your commit, one line per headline result, and last "nothing of mine is running".
