# Fix unit: the controller rung that no reader runs (lead, 2026-11-05; owner, 12:04 UTC: "Option A")

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `rung_`), `S/u35r/r4/HANDBACK_F126.md` (the diagnosis) and
SPECIFICATION.md F.2's I2C ladder paragraph (from "**The I2C ladder, per sensor**"). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## The defect
`src/asy_base_classes.py`'s `_recover_bus()` skips a bus rung whenever the bus's one `recoveries` count moved since
the reader's episode began (`:573`, `:606`), whichever rung moved it (`asy_i2c_driver.py:258` clear, `:307`
recover). So when the reader that ran the clear stops failing, every other reader on the bus also skips the controller
rung at its 4th failure, and no rebuild runs. F.2's rule, which the code must meet: "Each rung fires at most once per
failure episode - a bus rung once per bus, whichever reader on it reaches it first".

## Your work, in order (worktree `S/wt-rung`, branch `audit/rung`, at `3c402f85`; commit locally, never push)
1. **Tests first.** Each one must fail on the current code (show the red run), then pass.
   - Mock tier (`tests/test_asy_base_classes.py`, or the file that already tests `_recover_bus`): two readers on one
     bus; A runs the clear and then stops failing; B, at its 4th failure, runs the controller rung. Also: once one
     reader has rebuilt the controller, another reader's 4th failure in the same episode does not rebuild again.
   - Twin tier: make `tests/test_digital_twin_held_i2c_line.py`'s runtime held-SCL test independent of which reader
     reads first (the diagnosis' 500 ms shift is one way to show the case). Keep what it asserts today.
2. **The fix, in its smallest form.** One idea that holds: the bus also counts its controller rebuilds, and a reader
   skips the controller rung only if a rebuild ran since its episode began (a rebuild clears too, so the clear rung's
   check can stay as it is). Keep the wrap-by-design counter pattern and `tests_scripts/test_counter_steps.py` green.
   No change to logged texts, error numbers, config or anything the website reads.
3. Update the comments at the changed lines (3-line cap). SPECIFICATION.md F.2 already states the rule; change it only
   if a sentence there turns out wrong.

## Checks (light runs only; at most ten; the lead runs the gate)
- Rebuild (`S/u23/rebuild.sh S/wt-rung`), then at both GC stages: `tests/test_asy_base_classes.py`,
  `tests/test_asy_i2c_driver.py`, `tests/test_asy_scd30_driver.py`, `tests/test_asy_isl29125_driver.py`,
  `tests/test_digital_twin_bus_hazard_concurrency.py`, `tests/test_digital_twin_hot_replug.py`, and
  `tests/test_digital_twin_held_i2c_line.py` with `TEST_DEVICE` set to each of dev, wozi and one more device that has
  an I2C bus with more than one reader. No `MemoryError` or "memory allocation failed" in any log.
- `tests_scripts/test_counter_steps.py` and `tests_scripts/test_comment_block_cap.py`; `S/u35/lead/lint_direct.sh`;
  the three mypy passes as common_r1 describes (the typings link removed afterwards).

## Limits
- Write only `src/asy_base_classes.py`, `src/asy_i2c_driver.py`, the tests above, and their fakes if one models the
  counter (`tests/_sensortask_scenarios.py`, `digital_twin/` only where a fake mirrors `recoveries`).
- The bench waits for this: aim to hand back by about 13:30 UTC. Budget about 1 % of the week.

## Hand-back
`S/u35r/r5/HANDBACK_RUNG.md`, at most 25 lines, and return its path: the commits, lines in and out per file, the red
then green runs, the checks' results, and anything listed rather than done. Last line: "nothing of mine is running".
