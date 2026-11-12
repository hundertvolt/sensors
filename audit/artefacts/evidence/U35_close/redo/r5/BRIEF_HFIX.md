# R5 unit hfix: every reset that leaves the board for later tests kicks the bench AP (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `hfix_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `tests_hardware/harness.py`'s
`kick_after_reset()`, `kick_then_reset()` and `BenchBridge.kick_all_stations()`, and how the bench tier builds its
bridge (`tests_hardware/bench/conftest.py`, `tests_hardware/conftest.py`). The reset tests' kick (bench,
2026-11-06): the bench AP keeps a reset board's stale entry for about 60 s, which blocks the rejoin, so the board
falls back to its hotspot.

## Owner ruling behind this unit (2026-11-06 12:10:44 UTC, verbatim)
"Harness: Option A"

## The bench's evidence (relay of 12:00:52, its reading)
Run 9 10m on image d3f10239: step 9's test passed but its session-end wait timed out after 90 s ("No route to host"),
as the damaged-config session's did. 10a and 10m: the soak runner collects flash then bench in one session; the
flash tests end on `board.hard_reset()` with no kick, the board goes to its hotspot (FRAM: WIFI W38/W79 pairs grew
over the session), and the bench half's three tests ERROR in setup at `bench/conftest.py:86` `check_image` (one fetch,
no wait). `flash/test_..._single_core_timing_headroom_holds_under_normal_full_task_load` ran most of its 600 s window
in hotspot ("Permanently no WLAN connection" early, "WLAN connection established" only near the end), and failed on
"an unexpected mid-soak reboot" about 30 s after its own hard reset; the reason was overwritten before anyone read it.

## Your work (worktree `S/wt-hfix`, branch `audit/hfix`, at int `03793ef9`; create it; commit locally, never push)
1. One harness helper used by every reset that leaves the board for later tests or for a session-end check (the flash
   tier's `leave_board_serving`, the session start/end and repair resets in `tests_hardware/conftest.py`, the soak's
   own resets): reset, then kick the bench AP's stations when a bench bridge is configured for this session's host;
   a plain reset otherwise (a flash-only rig, `--twin`). Decide from the same configuration the bench tier reads,
   never from a guess; say in one line how.
2. The bench session's image check (`check_image`'s caller, the `board_image` fixture) waits for the board to serve,
   with a deadline, instead of one fetch.
3. The headroom soak starts its window only once the board serves on STA (Mode STA), with a deadline; the soak's claim
   is the normal full task load, which hotspot mode is not.
4. A soak that detects an unexpected reboot reads the board's ResetReason at once and puts it in its failure message.
Keep each to the smallest change; restructure nothing.

## Never
No hardware: `tests_hardware` runs only with `--collect-only` or `--twin`. Never edit `src/`, `ext/`; never read
`arduino/`; never open `/root/.claude/`. Never weaken a check, never a skip; a wait polls for its state with a deadline.
Never print, copy or write any Wi-Fi credential or the hotspot fallback password.

## Rules for the text
Text outside `audit/` cites no audit IDs, unit names or finding numbers. A choice carries "(agent, 2026-11-06)" or the
owner ruling it follows. Comment-block and line rules as CLAUDE.md states them (3 prose lines, a line over 120 counts
twice).

## Checks
`S/u35/lead/lint_direct.sh`; the three mypy passes; `--collect-only` on bench and flash, with and without
`--allow-persistence-write`; `--twin` for any changed flash test that runs there; `tests_scripts` whole, once, under
`S/u35/lead/heavy.lock` as common_r1 says.

## Limits
Write only `tests_hardware/` (and its README where a documented behaviour changes). One commit. Budget about 0.5 % of
the week. Hand back by 13:30 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_HFIX.md`, at most 15 lines, and return its path: per item the file:line and one line on what
changed; the bench's `PYTEST_K` for anything it should rerun; lines in and out; each check with its result. Last line:
"nothing of mine is running".
