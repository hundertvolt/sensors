# Read-only diagnosis: unit tests that fail only on the bench Pi (lead, 2026-11-05)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `pio_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Your worktree: `S/wt-pionly`
(detached at `5f763f25`, a throwaway; run `S/u23/rebuild.sh S/wt-pionly` first).

## The failures
Round 1's step 4a runs `scripts/test.sh` on the bench Pi 4 (aarch64, Debian trixie, 16 test files at once). Three runs
there, each with one different failure; every one passes here at both GC stages:
1. `tests/test_asy_uart_driver.py::test_two_concurrent_cancellers_both_return`, `AssertionError` at `:970`
   (`assert second_result is True`), 1 of 3 runs. Full output: `S/u35r/bench/test_asy_uart_driver_20261105T124309Z.log`.
2. `tests/test_sensortask.py` with `TEST_DEVICE=wozi`: `FAIL test_only_the_api_writes_the_scd30: AssertionError:
   (4, 3, 2)`, 1 of 3 runs.
3. `tests/test_sensortask.py` with `TEST_DEVICE=dev` passed only on attempt 2/3 once (its first attempt's output is not
   here).
The bench's run summaries are in `S/u35r/bench/HANDBACK_1320.md` (large: grep it).

## What to answer, for each
1. The assumption in the test or the code that a slower, more loaded host breaks (an ordering, a real-time bound, a
   shared-state leak between test functions), with file:line.
2. Reproduce it here if you can, with load or CPU limits (for example `taskset` to one core while other test files
   run). Multi-process load runs take the heavy slot: check `S/u35/lead/heavy.lock` is absent, touch it, run, `rm` it as
   its own command; while another holds it, read instead.
3. Classify: (a) a firmware defect a slow board can meet, (b) a test assumption, (c) other. Propose the minimal fix
   in a sentence; write no fix.

## Limits
Read-only: write only your hand-back and scratch files under `S/wt-pionly/ftmp/` (deleted before you hand back). Light
runs, at most ten. Budget about 0.6 % of the week; hand back by 15:30 UTC.

## Hand-back
`S/u35r/bench/HANDBACK_PIONLY.md`, at most 25 lines, and return its path. Last line: "nothing of mine is running".
