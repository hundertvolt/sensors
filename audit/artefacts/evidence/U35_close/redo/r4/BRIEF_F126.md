# FINDINGS 12.6: classify one red test (lead, 2026-11-05; read-only diagnosis, no fix)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Read `S/u35r/r1/common_r1.md`
first (binding; labels `f126_`). Your worktree: `S/wt-f126` (detached at the integration head `3c402f85`, a
throwaway: nothing in it is merged).

## The finding
In a tree with the ISL29125 module removed, dev's i2c1 holds only the SCD30 and the SGP40, and
`tests/test_digital_twin_held_i2c_line.py` fails on dev at both GC stages, deterministically, with microtest's
"reset reached without a catch" (`tests/microtest.py:49`). The failing test is most likely
`test_a_slave_holding_scl_at_runtime_gets_a_clear_that_pulses_nothing_then_one_controller_rebuild` (it picks the
busiest bus). No device in the full tree has that bus pairing.

## What to answer
1. Reproduce it in `S/wt-f126`: remove only dev's ISL29125 `[[instance]]` (and what buildgen then insists on), run
   `S/u23/rebuild.sh S/wt-f126`, then the file with `TEST_DEVICE=dev` at both GC stages. Say which test fails.
2. Find the root cause: which code path reaches a reset (`machine.reset()`, the watchdog model, the supervisor),
   and why the ISL29125's presence avoids it.
3. Classify it:
   - (a) a real gap: a real board whose bus holds those two chips would reset on a held SCL where the design says the
     bus clear and the controller rebuild recover it (SPECIFICATION.md F.2, I2C recovery);
   - (b) a test assumption that holds only with a third reader on the bus (for example its timing, or its pick); or
   - (c) an artefact of the strip that the full tree cannot reach.
   Give the evidence (file:line, the log lines) for the class.

## Limits
- Write only in `S/wt-f126` and your hand-back. No fix, no commit anywhere else.
- Light runs only, at most six; no gate, no whole tier (the host's heavy slot belongs to another unit).
- Budget: about 0.4 % of the week.

## Hand-back
`S/u35r/r4/HANDBACK_F126.md`, at most 20 lines, and return its path. Last line: "nothing of mine is running".
