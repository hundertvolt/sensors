# Fix unit: the test-side defects step 4b found on round 1's final image (lead, 2026-11-05; host-side code only)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `harn2_`), then `S/u35r/bench/ROOT_CAUSES_20261105.md` items 12 and 13 (the
bench session's diagnosis; item 13's table is your list). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Its paths and line numbers are from
the bench branch, whose tree outside `audit/` equals yours: check each anchor anyway. `tests_hardware/README.md` is the
harness's own reference. The bench's inferences are leads, not facts: confirm each from the code, the pinned
MicroPython source (`S/tc-int/micropython/`, read only) or the datasheet (`datasheets/`) before you change anything.

## Why it matters
The bench reruns the affected flash-tier tests by `PYTEST_K` on day 2, on the same image. Nothing here may need a new
image. Hand back by 20:30 UTC.

## Your work, in this order (worktree `S/wt-harn2`, branch `audit/harn2`, at `767f0d79`; commit locally, never push)
One commit per item.
1. **Held SDA** (`test_a_held_sda_line…`): `_stuck_errno` probes with `writeto(address, b"")`. Confirm in the pinned
   `ports/rp2/machine_i2c.c` that a zero-length transfer takes the software path and so cannot see a held SDA; then
   probe with a 1-byte transfer on the hardware path. Prefer a read, which writes no register; if the addressed
   chip's datasheet gives a 1-byte read a side effect, say so and pick the harmless form.
2. **BMP3xx general call** (`test_bmp3xx_alone…`): `before` is read before the reader's first forced read. Confirm from
   the BMP3xx datasheet that the enable bits stay set after a forced conversion; then take `before` after one read.
3. **FRAM erase** (`test_fram_erase_blanks…`, `test_an_erase…[mempause]`, and `test_fram_erase_racing…` if it is the
   same wait): `_RESET_WAIT_MS` runs from the command's answer, so it can end before the reset fires. Start it at the
   `reset` fact. Confirm the order from the script and the figures item 13 gives.
4. **The runner's `flash()`** (item 12's last paragraph): edit the copy `S/u35r/bench/round1.sh` (`round1.py` beside it
   is its helper, read only). After `picotool load -x`, send the kick that clears the AP's stale station entry once the
   board has dropped off USB, reusing the harness's `kick_after_reset()` or the same `Bench` call it makes; and make
   the `/system` reads in `final_image()` and `gc_image()` wait long enough for the measured worst case (about 9.5
   minutes after a stale entry). `shellcheck` the copy. The lead commits it to the bench branch.
5. **The board fixture's skip** (item 13, "The first 4b attempt"; diagnosis first): the board reset at 16:44:30, just
   as a session started, and `is_reachable()` failed. Read `Board.is_reachable()` and everything a session start does
   to the board before that call: can our own code reset it there (mpremote's soft reset, a raw-REPL entry stopping
   main.py), and does anything wait for its network afterwards? Write a fix only if the code shows the reset is ours
   and the wait is missing, and then make it a wait for the board as `kick_after_reset()` does, never a blind retry.
   Otherwise report what you found; the bench has been asked for the reset reason.

## Not yours
The twin conformance rows (`digital_twin/` stays as it is), the heap, VOC and C-stack readings, the `/status` 500s, the
UART failures and the CRC16 row: list nothing about them unless your reading turns up a fact the lead needs.

## Tests
These tests run against a board, which this session never touches. Where an item's logic can be pinned host-side
(`tests_scripts/test_bench_harness_helpers.py` and its kind), its test comes first, seen red on `767f0d79`, then green.
Where it cannot, say so for that item. A device script you change gets the main mypy pass and, if the twin can run it
(`digital_twin/run_device_script.py`), one twin run; `pytest tests_hardware --collect-only -q` must still collect
every test.

## Checks (light runs only, at most twelve; no gate, no whole tier)
`S/u35/lead/lint_direct.sh`; the three mypy passes as common_r1 says (link removed afterwards); every tests_scripts file
you touched, plus `tests_scripts/test_comment_block_cap.py`; the collect-only run. The heavy slot is the lead's until
about 18:30 UTC: no twin run before `S/u35/lead/heavy.lock` is gone, and take it as common_r1 says.

## Limits
- Write only `tests_hardware/` (the files the items name, plus `harness.py` or `conftest.py` as a fix needs),
  `tests_scripts/`, and the copy `S/u35r/bench/round1.sh`. Never `src/`, `buildgen/`, `devices/`, `digital_twin/`.
- The smallest form: no new options, flags or config. Budget about 1 % of the week.

## Hand-back
`S/u35r/bench/HANDBACK_HARN2.md`, at most 30 lines, and return its path: per item the commit (or the copy's change),
lines in and out, what confirmed the cause, its test (red, then green) or why there is none; the checks. Last line:
"nothing of mine is running".
