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

---

# Results — 2026-09-14, bench Pi4, real dev hardware

Firmware rebuilt from this branch (`scripts/build_firmware.py dev`, 91% flash) and flashed with
`picotool load -x -v` after `mpremote bootloader`; the littlefs filesystem is untouched by a UF2
load, which is what made §0's migration a real test rather than a fresh-config boot.

**One code change was needed before anything could run — see "Finding 1" below.**

## 0. Config migration — PASS (with a documentation correction)

First boot after flashing logged `CFGMGR_ISL29125 = [W4, W4, W5]`, and the ISL29125 log stayed at
its pre-flash count (7 → 7 over uptime 12 → 59), i.e. the new firmware logged nothing of its own.
Second boot after reboot: `CFGMGR_ISL29125` clean, config rewrite persisted.

**The §0 table above is incomplete in two ways** (both documentation gaps, not firmware defects —
the migration did the right thing):

- `AutoRangePersist` was **also** removed, alongside the three keys listed. It is folded into the
  same W5 rewrite, so it changes no count.
- `GainRatio` was **added** in the same branch (it moved out of FRAM into config, `f05f82d`). The
  old config file had no such key, so it defaults with its own `wrnno=4`. **That is the second W4** —
  the expected first boot is `W4, W4, W5`, not `W4, W5`.

Persisted config after migration: `AutoRangeThresh 85.0`, `GainRatio 26.666666`, the four removed
keys gone.

## 1.1 / 1.3 Derived switch-down point and renumbered warnings — PASS (2 runs)

`pytest tests_hardware/flash/test_sensor_accuracy.py -k isl29125 --allow-neopixel-sweep`:
**4 passed** twice (698.09s, 698.20s). Two further direct runs of the envelope script for numbers:

- **range switches across the full envelope: 2** (bound is 4; chatter would be dozens) — both runs
- returned to the low range at ambient (`dn level=0 lux≈1.06 range=375`), both ranges used
- **zero `E`-type entries**; log is `('W', 12)` only
- **`W12` present** at hard saturation and **`W13` absent** — the renumbering reached real firmware
- no `W10`/`W11`, as expected for a clean run
- cross-range continuity at level 4: **11.4%** and **11.0%** (was 11.5% on 2026-09-13 — unchanged)
- 12bit vs 16bit on one static scene: 0.7% / 0.4%

## 1.2 Fixed 2-cycle settle — PASS, and the fast path re-measured

`isl29125_real_irq_edge.py`, three runs: **elapsed 2.73 s / 2.71 s / 2.71 s**, all interrupt-led
(periodic fallback 30 s). Against `FAST_PATH_DEADLINE_S = 6.0` that is 2.2× headroom, and it sits
just under the doc's own ~3030 ms arithmetic worst case. `config1_restart=yes` and
`persist_unit=rgb_cycles` both reproduced in all three.

**The `500–800 ms` figure in SPECIFICATION.md Part C.11.1.3 is not the comparable number.** It was
taken when PRST came from a config value; PRST is derived from `SampleInterv` now, and this script
sets `SampleInterv = TRIGGER_SEC = 30`, which buys the largest PRST the part offers (8 cycles,
2424 ms). The settle doubling accounts for ~303 ms of the change, the PRST derivation for the rest.
The INT still leads decisively, so this is not the design finding §1.2 warned about.

The 606 ms settle is directly visible in the driver's own debug output (`settle discard 605/606`).

## 1.4 Bench tier — PASS (2 runs)

All three tests, twice: **3 passed** in 95.58 s and 94.93 s, including
`test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value` (its first run since
the rewrite) and both `assert_module_error_log_empty` calls.

## 2.1 A real sandwich calibration — PASS. First time on real silicon.

Run as an isolated device script rather than over REST: the dev REST LED route
(`PUT /notification {"lightCmdLED": ...}`) goes through `request_signal()`, which produces a signal
*pattern* — measured drifting 106 → 77 → 42 lx — and a sandwich's dominant error is exactly the
scene moving. A device script holds the pixel genuinely stationary.

Three in-band runs at `OVERLAP_LEVEL = 4` (~138 lx on the 375 range, ~24 100 green counts, ~37% of
that range's full scale):

| Run | Candidate sequence | Converged on |
|---|---|---|
| 1 | 24.012 → 23.916 → 24.131 | 24.131 |
| 2 | 23.703 → 23.841 → 23.915 | 23.915 |
| 3 | 24.128 → 24.046 → 23.869 | 23.869 |

Every run converged early on `_CAL_CONVERGE_N = 3` within ~6–8 s, well inside `_CAL_WINDOW_MS`.
All nine candidates land in 23.70–24.13 (1.8% spread), inside the required 20.0–34.0.
`GET /sensors`'s `GainRatio` read **26.666666 before and after** — the driver never writes its own
config, so every flash write stays on the REST path.

**Level recorded, per BACKLOG 20**: ~24.0 at ~37% of the low range's full scale. Consistent with
that item's ~28-at-ambient to ~22-near-full-scale trend. One device, still PARKED.

**The refusal works as designed**: with the pixel parked dark, the candidate sequence is empty and
the ISL error log stays **empty** — refusal reported by absence, never by a `wrnno`.

**Closing the loop (step 6)** — re-running the envelope's continuity measurement with the measured
ratio applied instead of the nominal:

| Applied ratio | Cross-range continuity step at level 4 |
|---|---|
| 26.667 (nominal) | **11.4%** / 11.0% |
| 23.96 (measured) | **0.4%** |

A ~28× reduction. This is the half of the mechanism nothing had ever exercised.

---

## Finding 1 — three device scripts could never initialise the driver (fixed in this session)

`isl29125_plausibility_read.py`, `isl29125_lighting_scenarios.py` and `isl29125_real_irq_edge.py`
prime `reader.cfgmgr._cache` by hand, and none of them was updated when `f05f82d` added `GainRatio`
to the schema. `_init_isl()` fetches `_VAL_AR_THRESH + _VAL_AR_DWELL + _VAL_FC + _VAL_GR` and
length-checks the result against `_N_FLOAT_CFG = 4`; with only three keys present the check fails,
`errno=12` is logged and init returns False — so the read chain never starts and **no sample ever
arrives**.

Symptom was `samples=0`, `lux=1000000000.0..-1.0`, "the read chain stalled", and
"sensor not responding or not wired to i2c1" — all of which read like a dead sensor or bad wiring.
`isl29125_mechanism_envelope.py` already had the key, which is exactly why it was the one ISL test
that passed. Fix: add `"GainRatio": 10000 / 375` to the three primed caches, matching the envelope
script. All four caches now carry an identical 10-key set — every schema key except `ISLCalibrate`,
which is a write-only command trigger init never reads. No stale keys remain in any of them.

## Finding 2 — the calibration band gate and the range decision use different quantities

Not changed, reported only. `_evaluate_range()` decides on `max(counts)` (the **peak** channel,
deliberately — see its own comment), while `_maybe_calibrate()`'s overlap-band gate tests
**`green_counts`**, both against `fraction_to_counts(_down_thresh())` ≈ 1044 counts.

For a strongly-coloured scene the two disagree. This rig's WS2812 white is blue-dominant, so at
~153 lx approached from *above*, peak stays above 1044 (auto-range correctly holds the high range)
while green sits at ~1006, below the band's lower edge — and calibration refuses for the entire
120 s window, logging "scene outside the overlap band, waiting" ~35 times. Reproduced twice.

Approached from *below* (dark first) the same light settles on the 375 range, where green is
~24 000 counts, and calibration converges immediately. **So §2.1's procedure above needs one extra
step: park the pixel dark and let auto-range settle onto the low range before raising it to the
overlap level.** Whether the gate should use peak for consistency with the range decision is a
design question for the owner, not something to change from the bench.
