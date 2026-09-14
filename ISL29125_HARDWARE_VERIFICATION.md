# ISL29125 — what still needs real hardware

Temporary file, like `UART_C_PORT_CHANGELOG.md`: delete it once every item below is either green or
re-filed into BACKLOG.md. It exists so a session with the bench Pi4 can execute exactly this list
without re-deriving it from the branch diff.

**Branch**: `claude/isl29125-driver-promotion-fqn9zr` (PR #75).
**Prerequisite for every item**: the project owner's go-ahead given *in that session's own
conversation* (CLAUDE.md's standing gate), and firmware **rebuilt from this branch** — the bench
board's current image predates the 2026-09-14 changes below.
**Read first**: `tests_hardware/README.md` (prerequisites, env vars, the `--allow-neopixel-sweep`
gate, the NeoPixel rig geometry) and CLAUDE.md's FRAM rule — read `GET /status`'s `errcount`
**before** any `ResetErrors`.

---

## 0. Do this before anything else: the config migration

**This will break two bench tests on the first boot and it is not a defect.** The board's persisted
`config_ISL29125.cfg` was written by the old schema. Three keys were removed and one renamed:

| Old key | Status |
|---|---|
| `AutoRangeUp` | renamed → `AutoRangeThresh` (same 50.0–95.0 band, same 85.0 default) |
| `AutoRangeDown` | removed — derived as `AutoRangeThresh / 53.333` |
| `AutoRangeSettle` | removed — fixed at 2 conversion cycles |

`ConfigManager.read_config()` migrates this automatically, and says so in its log:

- `AutoRangeThresh` is absent → `wrnno=4` ("has error or is missing, using default"), default applied
- `AutoRangeUp` / `AutoRangeDown` / `AutoRangeSettle` are left over → `wrnno=5` ("Removed invalid
  keys from config file"), and the file is rewritten

So on the **first** boot after flashing, `CFGMGR_ISL29125` carries W4 and W5.
`tests_hardware/bench/test_sensor_config_push_over_real_hardware.py` asserts
`assert_module_error_log_empty(dut_ip, "CFGMGR_ISL29125")` and will fail against that.

**Procedure**: flash → boot once → confirm the two warnings are exactly W4 and W5 and nothing else →
reboot. `CFGMGR_*` loggers are RAM-only (CLAUDE.md), so the second boot starts clean and the bench
tier can run. **Record what the first boot actually logged before rebooting** — if it carries
anything beyond W4/W5, that is a real finding, not migration noise.

**What this verifies**: that a deployed unit survives a schema change without hand-editing its
config. Nothing in the mock or twin tiers covers a real file on real flash.

---

## 1. New on 2026-09-14 — never executed on hardware

### 1.1 The derived switch-down point

`AutoRangeDown` is gone; `_down_thresh()` returns `AutoRangeThresh / 53.333`. **The threshold
register value actually written on a range switch changed**: at the default `AutoRangeThresh = 85`
the low threshold is now **1044 counts** (1.594 % of full scale), where it was 983 (1.5 %). The
auto-range loop on real silicon has never run against the new number.

Run, with `--allow-neopixel-sweep`:

- `tests_hardware/flash/test_sensor_accuracy.py::test_isl29125_mechanisms_hold_across_the_whole_illumination_envelope`
- `tests_hardware/flash/test_sensor_accuracy.py::test_isl29125_survives_recombined_realistic_lighting_scenarios`

Must hold: at most 4 switches across a full up-and-down (chatter would be dozens), the return to the
low range at ambient, both ranges used, zero `E`-type entries.

**If it chatters**, that is the finding this item exists for — report the switch count and the levels
it oscillated between; do not widen `MAX_SWITCHES`.

### 1.2 The fixed 2-cycle settle window

`AutoRangeSettle` is gone; `_SETTLE_CYCLES = 2`. **The settle after every CONFIG1 write doubled**:
606 ms at 16 bit (was 303 ms), 38 ms at 12 bit. This is the highest-risk change here, because two
hardware scripts carry wall-clock budgets sized against the old window:

- `isl29125_real_irq_edge.py`'s `FAST_PATH_DEADLINE_S = 6.0`. Worst case is now PRST = 8 (2424 ms)
  plus the settle (606 ms) ≈ 3030 ms, so 6.0 s still has ~2× headroom — but that is arithmetic, not
  a measurement. **Report the actual `elapsed_s` the script prints.**
- `isl29125_mechanism_envelope.py`'s `SETTLE_S = 4.5` per level. Should still be ample; confirm no
  level reports a stale sample.

**Also re-measure the fast path itself.** The "6 of 6 interrupt-led, 500–800 ms" figure in
SPECIFICATION.md Part C.11.1.3 was taken with a 1-cycle settle. Re-run the same six forced crossings
and record interrupt-led vs periodic-led and the latency spread. If the INT no longer leads, the
settle is eating the window and that is a design finding, not a test to relax.

### 1.3 The renumbered warnings

`wrnno` is now a contiguous 10–13, and brownout was split from shadow divergence:

| Now | Meaning | Was |
|---|---|---|
| 10 | brownout recovered | 10 (shared) |
| 11 | chip config diverged from the shadow, re-applied | 10 (shared) |
| 12 | saturated on the high range | 14 |
| 13 | periodic path decided five range switches running (dead-INT detector) | 15 |

The device scripts now assert `("W", 12)` **present** at hard saturation and `("W", 13)` **absent**.
Those assertions have never executed. A pass here is what proves the renumbering reached the real
firmware rather than only the source.

W11 is opportunistic — nothing forces a shadow divergence — so a clean run simply shows neither 10
nor 11. Do not try to provoke one.

### 1.4 The bench tier end to end

After the migration reboot in §0:

- `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py::test_isl29125_resolution_and_ir_compensation_push_over_real_rest_and_readback`
- `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py::test_isl29125_calibrate_command_push_over_real_rest`
- `tests_hardware/bench/test_rest_endpoints_over_sta.py::test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value`

The third is the one to watch: it was rewritten when the gain ratio stopped living in FRAM, and it
pins `GainRatio` as an ordinary config value across a real power cycle. It has not run since that
rewrite.

Both `assert_module_error_log_empty(dut_ip, "ISL29125")` calls are deliberate — the old
`allowed_warnings=(13, 16)` allowance is gone, and would now be worse than useless, since **13 has
been reused** for a live warning.

---

## 2. Carried over — the one thing never proven on any hardware

### 2.1 A real sandwich calibration run (BACKLOG 22)

The mock and twin tiers cover this end to end, including the measured-then-applied error shrink. The
flash and bench tiers assert only that the trigger is accepted, that the applied ratio does not move,
and that `GainMeas` is present. **No real chip has ever measured a sandwich.**

A sandwich is three legs — this range, the other range, then this range again — because the dominant
error is the scene moving between the two readings, and a pair alone cannot tell a real ratio from a
light that changed.

Procedure, under the NeoPixel rig:

1. Park the pixel at a level **inside the overlap band** — bright enough to clear the dark floor on
   the low range, dim enough not to clip it. `OVERLAP_LEVEL = 4` in `isl29125_mechanism_envelope.py`
   (~150 lx on this rig, ~40 % of the low range's full scale) is the known-good setting.
2. Leave `RangeAuto` on. Let it settle.
3. `PUT /sensors {"ISL29125": {"ISLCalibrate": true}}` — must return `"Valid"`.
4. Poll `GET /measurements` and watch `ISL29125.GainMeas`.

What must hold:

- `GainMeas` goes from `null` to a number, and lands inside 20.0–34.0.
- It **converges**: three consecutive stable sandwiches within 1 % of each other end the run early
  (`_CAL_CONVERGE_N = 3`, `_CAL_CONVERGE_TOL = 0.01`). Record the sequence, not just the final value.
- `GET /sensors`'s `GainRatio` **does not move**. The driver never writes its own config; that is the
  property that keeps every flash write on the REST path.
- The run is bounded: `_CAL_WINDOW_MS = 120000`, so it stops within two minutes either way. The
  candidate then stays readable for ten minutes (`_CAL_HOLD_MS = 600000`) and clears.

Then close the loop, which is the half nothing has ever exercised:

5. `PUT /sensors {"ISL29125": {"GainRatio": <the measured value>}}`.
6. Re-run the envelope script's cross-range continuity measurement (one stationary light, read
   pinned to each range in turn with `RangeAuto` off). The step should be **smaller** than the 11.5 %
   recorded at nominal 26.67 on 2026-09-13.
7. Restore `GainRatio` to what it was, so the bench is left as found.

**Expect a level-dependent answer, and record the level.** SPECIFICATION.md Part C.11.4 has the
measurements: this part's true ratio varies ~28 at ambient to ~22 near full scale, so a value
measured in the overlap band is not "this unit's ratio", it is its ratio at that level. That is a
recorded property of the part, not an open question — one device and no reference meter means there
is nothing to decide — so record the level as evidence that adds to C.11.4's table, not as input to
a pending call.

**Also try a refusal**, since absence-as-signal is the whole feedback mechanism: park the pixel
outside the overlap band (dark, or full white) and start a run. `GainMeas` must stay `null` and the
ISL error log must stay **empty** — a refused measurement is reported by absence, deliberately never
by a `wrnno`.

---

## 3. What does *not* need re-running

- The mock, twin and website tiers — all green in CI on this branch.
- `test_the_isl29125_mock_answers_the_bus_exactly_as_the_real_chip_does` — the protocol layer's
  register map did not change; only reader-level policy did. Cheap, so run it anyway as a canary.
- The PRST derivation itself (SPECIFICATION.md Part C.11.1.3) — already measured on the bench.
  §1.2's re-measurement is about the *settle*, not about PRST.

---

## Reporting

Append results here rather than only in the session transcript: for each item, what ran, what it
printed, and whether it passed. Anything that fails is a finding to diagnose, not a bound to widen —
`tests_hardware/README.md`'s "a hardware test that depends on an unstated rig condition" pattern
(six instances so far) is the trap to check yourself against before concluding the driver is wrong.
