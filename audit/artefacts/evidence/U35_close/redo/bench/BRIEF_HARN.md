# Fix unit: the bench harness defects round 1 found (lead, 2026-11-05; host-side code only)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `harn_`), then `S/u35r/bench/ROOT_CAUSES_20261105.md` (the bench session's
diagnosis, items 1-7 and the `_seed()` row of item 10). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Its paths and line numbers are from
the bench branch; your tree matches it in every file you touch, but check each anchor. `tests_hardware/README.md` is
the harness's own reference.

## Why it matters
Round 1's bench runs 4b and run 5 start at about 17:30 UTC on this harness. Items 1 and 2 each lost a run's results
once (a board left in BOOTSEL for 13 minutes; 84 tests failing in setup during a hotspot window). Hand back by
15:30 UTC.

## Your work, in this order (worktree `S/wt-harn`, branch `audit/harn`, at `5f763f25`; commit locally, never push)
One commit per item, so the lead can take them separately.
1. **picotool retry** (item 1): the single try in `tests_hardware/flash/test_system_commands.py` and
   `tests_hardware/bench/test_system_commands_over_rest.py` retries as `reflash()` does, through the existing
   `_retryable_picotool_exit()`. Reuse it; no second retry loop if one helper can serve all three.
2. **Kick timing** (item 2): the kick that clears the AP's stale station entry is sent after the slow command's own
   reset (the USB drop), not at its reply, at the sites item 2 names. One shared helper; `bench_control.py`'s existing
   workaround is the model. The log-check setup cascade item 2 mentions is not your work: list it.
3. **Serial conflict** (item 3): `recover_by_reset` must not reset while `observe_during`'s tail holds the port; the
   raise keeps the original failure as its cause.
4. **No tests_scripts test reaches a board** (item 4): the two tests in `tests_scripts/test_tests_hardware_run_record.py`
   load the conftest, whose session fixtures act on any attached board. Make that impossible in the smallest form, for
   these two and any other test that runs `tests_hardware` the same way (look for them).
5. **Soft-reset channel comparison** (item 5): compare the channel sets, not the lists.
6. **The `build()` feed** (item 6): `_Sender.build` feeds the watchdog as `finished()` does.
7. **`_serving_status`** (item 7): a reading counts only from a boot whose `BootSignature` differs from the one read
   before the command.
8. **`_seed()`** (item 10's row, inferred by the bench): confirm or refute from the script and the timings it cites
   (60 FRAM writes against the 8 s watchdog). Fix as item 6 only if confirmed; otherwise list it.

## Tests
These run against a board, which this session never touches. Where an item's logic can be pinned host-side
(`tests_scripts/test_bench_harness_helpers.py` and its kind), its test comes first, seen red on `5f763f25`, then green.
Where it cannot, say so for that item; `tests_hardware --collect-only` must still collect every test. A device script
you change gets the main mypy pass (it is in its scope) and, if the twin can run it (`digital_twin/run_device_script.py`),
one twin run.

## Checks (light runs only, at most twelve; no gate, no whole tier)
`S/u35/lead/lint_direct.sh`; the three mypy passes as common_r1 says (link removed afterwards); every tests_scripts file
you touched, plus `tests_scripts/test_comment_block_cap.py`; `pytest tests_hardware --collect-only -q`.

## Limits
- Write only `tests_hardware/` (the files the items name, plus `harness.py`, `bench_control.py`, `conftest.py` as a fix
  needs) and `tests_scripts/`. Never `src/`, `buildgen/`, `devices/`, `digital_twin/`: round 1's image is frozen.
- The smallest form: no new options, flags or config. Budget about 1.5 % of the week.

## Hand-back
`S/u35r/bench/HANDBACK_HARN.md`, at most 30 lines, and return its path: per item the commit, lines in and out, its test
(red, then green) or why there is none; the checks; anything listed. Last line: "nothing of mine is running".
