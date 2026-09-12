# ISL29125 — function-level action list and reference layer

Companion to `ISL29125_PROMOTION_PLAN.md`. The plan decides *what* the driver must do and *where*
the work lands; this document decides *which function does it*, and answers the same ten questions
for every one of them:

> which single function, in which file, for what purpose, with what expected functionality, which
> failure modes, how each failure is handled, which modules are downstream (is every behaviour
> covered), which are upstream (are all expectations met), what is logged at which level, and what
> has to be true before the function counts as complete.

It is also the **reference layer**: every claim below is tied to the datasheet page/table, to the
`src/` file that already does the same thing, or to an external implementation or vendor document
read this session. §5 collects those sources and records what each one actually settled, including
two places where the published forms of the same formula disagree in sign and one where a widely
copied matrix has two different "correct" roundings.

**Still specification.** Nothing here is code, and no code is to be written from it until the
project owner says so — §13's open questions are inputs to five of the functions below.

**Status of the numbers in this document.** Every register address, bit position, timing figure
and register default is from FN8424 Rev 3.00 (`datasheets/isl29125/`), cited inline. Every
"convention" claim is from a file in `src/`, cited by name. Where neither exists, the entry says
so and gives the reasoning instead — those are the places a reviewer should push hardest.

---

## 0. How to read this document

### 0.1 The entry format

Each function gets one block. The ten fields are always in the same order and always present; a
field that genuinely has no content says **none**, never nothing at all, because an empty failure-
mode list is a claim, not an omission.

| Field | What it holds |
|---|---|
| **Where** | File, class, exact signature |
| **Purpose** | One sentence. If it needs two, the function is doing two things |
| **Functionality** | The observable contract, step by step |
| **Failure modes** | Everything that can go wrong, including the ones that cannot raise |
| **Handling** | What the function does about each, and what the caller sees |
| **Downstream** | What it calls, and whether every behaviour of those callees is accounted for |
| **Upstream** | Who calls it, and whether their expectations are met |
| **Logging** | Level + `errno`/`wrnno`, from §2/§3 |
| **Done when** | The checkable completion criteria, including the named tests |

### 0.2 The layers, and the raise/never-raise contract

`SPECIFICATION.md` Part C.2 fixes three classes, and Part C.7 fixes which of them may raise. This
is the single most load-bearing rule in the whole document, because it decides where every
`try`/`except` below sits:

| Layer | Class | May raise? | Evidence |
|---|---|---|---|
| 3 | `ISL29125_Reader(SensorReaderConfig)` | **Never.** Every call into layer 2 is wrapped and logged | `asy_bmp3xx_driver.py` reader methods, 22 of 22 |
| 2 | `ISL29125_I2C` | **Yes, deliberately** — a bus fault is an exception, not a `None` | `BMP3XX_I2C._read()` raising `OSError`/`ValueError` |
| 2 | `ISL29125_DeviceSession(Lockable)` | n/a — `Lockable.__aexit__` swallows a double release | `base_classes.py:32-51` |
| 1 | `asy_i2c_driver.I2CDevice` | Mixed: returns `None` on a malformed request, **propagates `OSError`** from the real bus | `asy_i2c_driver.py:81-104` (`get_register_struct` returns `None`), `_readfrom_mem` (raises) |

Layer 1's mixed contract is the trap. `get_register_struct()` returns `None` for a malformed
format string but lets a NAK/timeout `OSError` straight through, so **every layer-2 read must
check for `None` *and* be inside a caller that expects a raise**. `BMP3XX_I2C._get_osr_setting()`
is the existing worked example: `if osr is None: raise OSError(...)`. Every read in §4.3 follows
it.

### 0.3 Naming, fixed before any code exists

Per `ISL29125_PROMOTION_PLAN.md` §14.3 conventions 8 and 9, and settled here so the tests can be
written against the names:

| Thing | Name | Convention |
|---|---|---|
| Reader internals | `_init_isl()` / `_read_isl()` / `_store_isl()` | 8 (`bmp`/`scd`/`sgp`) |
| Protocol object on the reader | `self.isl` | 9 |
| Device session inside the protocol class | `self.i2c_isl29125` | 9 |
| Module name constant | `_NAME = const("ISL29125")` | C.2 |
| Namedtuple | `ISL29125` + `_FIELDS` | C.2, convention 5 |
| Auto-range schema entries | `_VAL_AR_UP`, `_VAL_AR_DOWN`, `_VAL_AR_SETTLE`, `_VAL_AR_PERSIST`, `_VAL_AR_DWELL` | §14.4 rule 1 |
| Other schema entries | `_VAL_SI`, `_VAL_RES`, `_VAL_RA`, `_VAL_RNG`, `_VAL_ICO`, `_VAL_ICA`, `_VAL_FC`, `_VAL_RESETCAL` | 6 |
| Maintenance getter | `get_mem_status()` | matches `SGP40_Reader.get_mem_status()` exactly |

`get_mem_status()` is worth pausing on: SGP40 already has a method of that name returning
`(last_backup, restored_from)`, consumed by `sensortask_dev.py`'s `_sgp_maintenance_status()`.
Reusing the name — returning `(gain_ratio, cal_ts)` — means `_isl_maintenance_status()` is a
copy of the SGP40 one with two words changed, which is exactly what "made of the same material"
means in practice.

---

## 1. Inventory — every function, one line each

**109 functions across 12 source files**, of which 98 are new and 11 are edits to existing
functions. Counted so the plan's estimate of the work is a number rather than an impression.
Test files are not in this count — they are §6.

### 1.1 `src/math_helpers.py` — 5 new, pure, bus-free (§14.4 rule 2)

| # | Function | New/edit |
|---|---|---|
| M1 | `rgb_to_hsb(red, green, blue)` | new |
| M2 | `rgb_to_xyz(red, green, blue)` | new |
| M3 | `chromaticity_xy(x_val, y_val, z_val)` | new |
| M4 | `cct_mccamy(chroma_x, chroma_y)` | new |
| M5 | `ema_step(previous, sample, coefficient)` | new — Part G.2 catalogue entry (§7.8) |

### 1.2 `src/asy_isl29125_driver.py` — module level, 5 new pure helpers

| # | Function | Purpose in one clause |
|---|---|---|
| F1 | `_decode_rgb_burst(raw)` | 6 bytes → `(green, red, blue)` counts |
| F2 | `_normalise_triple(green, red, blue, resolution, dark_offset)` | 12-bit shift + dark subtract + clamp |
| F3 | `_counts_to_lux(count, full_scale, gain_correction)` | counts → absolute lux |
| F4 | `_fraction_to_counts(fraction)` | % of full scale → threshold counts, in float |
| F5 | `_is_bus_fault_pattern(counts, status)` | all-ones triple + implausible status byte |

### 1.3 `src/asy_isl29125_driver.py` — `ISL29125_Reader`, 58 new

| # | Function | Group |
|---|---|---|
| R1 | `__init__` | lifecycle |
| R2 | `_init_isl()` | lifecycle |
| R3 | `read_loop()` | lifecycle |
| R4 | `_read_isl()` | read path |
| R5 | `_store_isl(results)` | read path |
| R6 | `_read_sensor_dict()` | config |
| R7 | `_handle_status(status)` | read path |
| R8 | `_recover_brownout()` | self-healing |
| R9 | `_evaluate_range(green_counts, saturated)` | auto-range |
| R10 | `_switch_range(target_range)` | auto-range |
| R11 | `_settle_wait()` | auto-range |
| R12 | `_learn_gain_ratio(green_counts)` | calibration |
| R13 | `_load_gain_ratio()` | calibration |
| R14 | `_persist_gain_ratio()` | calibration |
| R15 | `_clear_gain_ratio()` | calibration |
| R16 | `_base_trigger()` | timing |
| R17-R29 | 13 × `_push_<field>()` | config push |
| R30-R42 | 13 × `set_<field>()`, including `set_trigger_secs()` and `reset_gain_calibration()` | setter |
| R43-R47 | 5 × `get_<field>()` | getter (`_get_callbacks`) |
| R48-R49 | `start_asy_read()` / `start_asy_trigger()` | task starters |
| R50-R51 | `start_timer()` / `stop_timer()` | timer |
| R52-R53 | `get_task_starters()` / `get_timer_starters()` | registration |
| R54-R56 | `get_data()` / `get_dict_data()` / `get_dict_cfg()` | data |
| R57-R58 | `get_error_counter()` / `get_mem_status()` | data |

(The 13 pushes, 13 setters and 5 getters are specified as three tables in §4.3 rather than 31
near-identical blocks — they differ only in the field they carry and the `errno` they log.)

### 1.4 `src/asy_isl29125_driver.py` — `ISL29125_DeviceSession` (1) and `ISL29125_I2C` (15 new)

| # | Function |
|---|---|
| D1 | `ISL29125_DeviceSession.__init__(i2c_device)` — verbatim from C.2's snippet |
| P1 | `__init__(i2c, address=0x44)` |
| P2 | `setup()` |
| P3 | `reset()` |
| P4 | `_read_byte(register)` |
| P5 | `_encode_shadow()` |
| P6 | `_write_shadow(first_register)` |
| P7 | `configure(**fields)` |
| P8 | `set_thresholds(low_counts, high_counts)` |
| P9 | `read_counts()` |
| P10 | `read_status()` |
| P11 | `clear_brownout()` |
| P12 | `get_config_snapshot()` |
| P13 | `get_device_id()` |
| P14 | `time_to_settle_ms()` |
| P15 | `cycle_ms()` |

### 1.5 Everything outside the driver

| # | Function | File | New/edit |
|---|---|---|---|
| S1 | `_isl_maintenance_status()` | `src/sensortask_dev.py` | new |
| S2 | `build_system()` | `src/sensortask_dev.py` | edit |
| S3 | `_collect_error_sources()` / `_collect_level_setters()` / `_collect_task_starters()` / `_collect_timer_starters()` | `src/sensortask_dev.py` | edit ×4 |
| T1-T9 | `Isl29125Chip.*` | `digital_twin/_isl29125_chip.py` | new ×9 |
| T10 | `_wire_i2c_devices()` | `digital_twin/machine.py` | edit |
| W1 | `resolveFieldValue()` | `js/definitions.js` | edit |
| W2 | `validateDefinitions()` | `js/definitions.js` | edit |
| W3 | `jitterInPlace()` | `js/mock-server.js` | edit |
| W4 | `applySensorQuirksForGet()` | `js/mock-server.js` | edit |
| W5 | `formatFieldValue()` | `js/field-format.js` | edit **only if §13 q6 lands on option (b)** |
| H1-H4 | `_main()` in four `tests_hardware/device_scripts/` files | real hardware | new ×4 |

---

## 2. `errno` / `wrnno` allocation — final, and registered before any code

`SPECIFICATION.md` Part C.7 reserves 1-9 for `base_classes.py`; every driver starts at 10, and
`api_response.py`'s 99 is the ceiling to stay under (§11.2). Part C.7.1's table gains this row,
**before** the driver is written (§14.2 item 3), not after.

The allocation deliberately mirrors `asy_bmp3xx_driver.py`'s shape — lifecycle first, then
get/set pairs in adjacent numbers, then the paths unique to this device.

| `errno` | Path | Analogue |
|---|---|---|
| 10 | `_init_isl()`: `ISL29125_I2C.setup()` raised | BMP3xx 10, SCD30 10, SGP40 10 |
| 11 | `_read_isl()`: the periodic read cycle raised | 11 in all three |
| 12 | `_init_isl()`: persisted config unreadable at init | BMP3xx 12 |
| 13 | `_init_isl()`: applying persisted config to the chip raised | BMP3xx 13 |
| 14 | `_store_isl()`: float config batch unreadable at store-time | BMP3xx 14 |
| 15 / 16 | `get_resolution()` / `set_resolution()` | BMP3xx 15/16 pattern |
| 17 / 18 | `get_range()` / `set_range()` | " |
| 19 / 20 | `get_ir_comp_offset()` / `set_ir_comp_offset()` | " |
| 21 / 22 | `get_ir_comp_adjust()` / `set_ir_comp_adjust()` | " |
| 23 / 24 | `get_autorange_persist()` / `set_autorange_persist()` | " |
| 25 | `set_trigger_secs()`: value invalid | BMP3xx 21 |
| 26 | `set_filter_coefficient()`: value invalid | — |
| 27 | any of the four software auto-range knobs rejected (range or cross-field) — message names the field | — |
| 28 | `_read_sensor_dict()`: batched live snapshot read failed | BMP3xx 22 |
| 29 | `_switch_range()`: threshold burst write raised | — |
| 30 | `_switch_range()`: `CONFIG1` burst write raised | — |
| 31 | `_read_isl()`: status-byte read raised | — |
| 32 | `_read_isl()`: bus-fault pattern confirmed by a failed device-ID re-read | — |
| 33 | `_recover_brownout()`: re-applying the shadow raised | — |
| 34 | `configure()` path: shadow burst write raised, outside a range switch | — |
| 35 | `_load_gain_ratio()`: FRAM chunk read failed | SGP40 13 |
| 36 | `_persist_gain_ratio()`: FRAM chunk write failed | SGP40 14 |
| 37 | `_clear_gain_ratio()`: FRAM chunk clear failed | SGP40 15 |

| `wrnno` | Occurrence | Why a warning and not an error |
|---|---|---|
| 10 | `BOUTF` seen set; configuration re-applied, one cycle discarded | Recovered by design (§9.3) — must not feed the leaky bucket, or a flickering supply reboots the node |
| 11 | No stored gain ratio found at init; nominal 26.67 in use | Expected on a fresh unit; SGP40's `wrnno=10` "No backup found!" is the exact precedent |
| 12 | Stored gain ratio present but has no timestamp, or is older than the configured age | SGP40 `wrnno` 11/12 |
| 13 | A learned ratio was outside the plausible band and rejected | Calibration declined to move; measurement unaffected |
| 14 | All three channels clipped while already on the high range | The scene genuinely exceeds the part; nothing the driver can do, but the consumer must know |
| 15 | The periodic path made a range decision the INT path should have made first, N times running | **Requirement 17's silent-failure detector** — this is what turns "the interrupt is dead" from invisible into visible |

`wrnno=15` is new in this document. Requirement 17 makes the periodic evaluation a safety net; it
says nothing about *noticing* that the net is carrying the load. A counter that increments when
the periodic path finds a crossing with no preceding INT, and warns once per N (proposal: 5)
consecutive occurrences, costs one integer and makes a dead interrupt line diagnosable from
`GET /status`'s `errcount` alone — which is precisely the FRAM-persisted evidence CLAUDE.md tells
the next session to read before clearing anything.

---

## 3. Logging levels — what is logged where

Levels are `print_log.py`'s: `err` (1), `wrn` (2), `one` (3), `evt` (4), `all` (5). The rule the
three drivers follow, stated because no document states it:

| Level | Used for | Existing evidence |
|---|---|---|
| `err_s(..., errno=)` | Anything that fails and is counted | `_read_bmp()`, `_read_scd()`, every setter forward |
| `err(...)` | A failure with no history entry (construction-time, before `setup()`) | `start_timer()`'s `"Could not start timer:"`, SGP40's `"FRAM backup storage allocation failed!"` |
| `wrn_s(..., wrnno=)` | Recovered or expected-but-notable | SGP40 `"No backup found!"` |
| `one(...)` | Once-per-lifecycle milestones | `"initialized"`, `"Setting sensor config at startup."` |
| `evt(...)` | Per-cycle events worth seeing at debug 4 | `"sensor trigger"`, `"Interrupt Start Trigger"`, `"Backup trigger."` |
| `all(...)` | Per-cycle data-flow noise | `"read"`, `"data stored"` |

Applied to this driver, the complete list — every occurrence, one row each:

| Occurrence | Level | Code |
|---|---|---|
| FRAM gain-ratio chunk allocation failed in `__init__` | `err` | — (no history yet; `pr.setup()` has not run) |
| Chip setup failed | `err_s` | 10 |
| "initialized" | `one` | — |
| "Setting sensor config at startup." | `one` | — |
| Stored gain ratio restored, with its age | `one` | — |
| No stored gain ratio / stale / untimestamped | `wrn_s` | 11, 12 |
| Read trigger fired (timer or INT) | `evt` | — |
| Which source fired it, once the status byte is decoded | `all` | — |
| Sample read | `all` | — |
| Data stored | `all` | — |
| Range switch decided, with from/to and the deciding count | `evt` | — |
| Settle discard in progress | `all` | — |
| Switch-down suppressed by `AutoRangeDwell` | `all` | — |
| Gain ratio updated, with old → new | `evt` | — |
| Gain ratio rejected as implausible | `wrn_s` | 13 |
| `ISLResetCal` fired, calibration discarded | `one` | — |
| Brownout detected, configuration re-applied | `wrn_s` | 10 |
| Saturated on the high range | `wrn_s` | 14 |
| Periodic path caught a crossing the INT missed, ×5 | `wrn_s` | 15 |
| Every read/write/setter failure | `err_s` | 11, 15-37 |

Two rules worth stating because they are easy to get wrong:

- **Nothing in the auto-range or brownout paths increments the leaky bucket.** `_error_check()` is
  called exactly once per `read_loop()` cycle with the read results (§14.2 item 5). A range switch
  and a brownout recovery are *successful* operations; only the I²C failures inside them are
  errors, and those surface through the results tuple anyway.
- **A dark room is not a fault.** `CCT = None` below the low-light floor (§7.11) is a normal
  output. It is logged at `all`, never as a warning, and — see §4.2's `_read_isl()` — it must
  never enter the tuple handed to `_error_check()`.

---

## 4. Function specifications

### 4.1 `src/math_helpers.py` — the pure colour maths

All five follow the file's existing contract verbatim: `float | None` in, `float | None` (or a
tuple of them) out, **never raises**, a `_<NAME>_MIN`/`_MAX` domain-constant pair per function,
and the formula's source cited in a comment (Part D.1). They are in `math_helpers.py` rather than
the driver because they are device-independent and because that makes them testable with no bus
at all, which is what Part D.12's parameter/boundary/NaN-inf matrix needs.

**One deliberate deviation from the file's shape, flagged rather than slipped in.** Every existing
function returns a single float. `rgb_to_hsb()` returns a 3-tuple. The reason is correctness, not
convenience: H, S and B are all derived from the same `max`/`min` of the same triple, and three
separate entry points would recompute them and could — with a caller that interleaved a config
change — return a mutually inconsistent triple. `rgb_to_xyz()` has the same argument. If the
project owner prefers three single-value functions, the cost is three passes and a consistency
caveat; recorded here so the choice is visible.

---

#### M1 `rgb_to_hsb(red, green, blue) -> tuple[float, float, float] | None`

- **Where**: `src/math_helpers.py`, module level.
- **Purpose**: convert a normalised 0-1 sensor-RGB triple to hue (0-360°), saturation (0-1) and
  brightness (0-1).
- **Functionality**: standard HSV/HSB hexcone conversion. `v = max(r,g,b)`; `c = v - min(r,g,b)`;
  `s = 0.0 if v == 0 else c / v`; hue from which channel is max, `0.0` when `c == 0` (grey has no
  hue, and returning `None` there would be wrong — grey is a valid colour). Hue is wrapped into
  `[0, 360)` exactly once, at the end.
- **Failure modes**: any input `None`; any input outside `[0, 1]` (the caller's normalisation is
  supposed to guarantee it, so an out-of-range value means the chain above is broken); NaN, which
  compares false against everything and would silently pick the wrong max branch; `c == 0`
  (grey — not a failure, an edge case that must not divide).
- **Handling**: `None` in → `None` out. Out-of-domain → `None` (domain constants `_HSB_IN_MIN =
  0.0`, `_HSB_IN_MAX = 1.0`). NaN → caught by the same range test, since `not (0.0 <= nan <= 1.0)`
  is `True` — the file's existing functions rely on exactly this and it is the reason the range
  check comes before the arithmetic. Grey → `(0.0, 0.0, v)`. No `try` needed around the
  arithmetic: after the range gate, every operation is total.
- **Downstream**: none (pure). Every behaviour of `max`/`min` on floats is accounted for by the
  NaN gate.
- **Upstream**: `ISL29125_Reader._store_isl()`. Its expectation is a total function that never
  raises and never returns a partially-valid tuple — met.
- **Logging**: none. `math_helpers.py` has no logger, by design: the caller decides whether a
  `None` is worth reporting.
- **Done when**: unit tests cover the six hue sectors, the grey case, the three primaries at
  exactly 0/1, out-of-range in each argument, `None` in each argument, NaN and ±inf, and
  round-trip monotonicity of hue against a rotating input. Part D.12's matrix, applied.

---

#### M2 `rgb_to_xyz(red, green, blue) -> tuple[float, float, float] | None`

- **Where**: `src/math_helpers.py`.
- **Purpose**: map a normalised RGB triple into CIE 1931 XYZ using a **documented placeholder**
  matrix, as the first half of the CCT calculation (§7.11).
- **Functionality**: one 3×3 multiply with the sRGB/Rec.709 D65 coefficients held as module
  constants. **No gamma decode** — the sensor's output is linear in irradiance, so applying the
  sRGB transfer function (which exists to undo display encoding) would be a straight error. That
  is worth a comment in the code, because every copy of this matrix found on the web arrives
  attached to a gamma step.
- **Failure modes**: any input `None`; out of `[0, 1]`; NaN. The coefficient set being wrong for
  this sensor is not a failure mode — it is a known, documented inaccuracy (§7.11), and the
  function's own comment has to say so, since a reader who does not know will eventually "fix" it.
- **Handling**: as M1 — `None`/out-of-domain/NaN → `None`; the multiply itself is total.
- **Downstream**: none.
- **Upstream**: `_store_isl()` via M3/M4. Expectation: total, never raises — met.
- **Logging**: none.
- **Done when**: tested against three hand-computed vectors (pure R, pure G, pure B at 1.0, which
  reproduce the matrix columns exactly), the all-zero input, and the D.12 matrix. Plus one test
  that **pins the coefficients as literals** — see §5.3's note on the two different published
  roundings; a test that recomputes the matrix from primaries would pass against either and
  therefore proves nothing.

---

#### M3 `chromaticity_xy(x_val, y_val, z_val) -> tuple[float, float] | None`

- **Where**: `src/math_helpers.py`.
- **Purpose**: `x = X/(X+Y+Z)`, `y = Y/(X+Y+Z)` — the step that makes CCT range- and
  resolution-invariant (§7.4, §7.11).
- **Functionality**: one sum, two divisions.
- **Failure modes**: `None` input; **`X+Y+Z == 0`** (total darkness — the real one, and the whole
  reason this is its own function rather than three lines inside M4); a negative sum, which cannot
  come from M2 with in-range inputs but can from a hand-supplied test value; NaN.
- **Handling**: sum `<= _CHROMA_SUM_MIN` (proposal: `1e-12`, not `0.0`, so a denormal does not
  produce a `1e300` chromaticity) → `None`. The low-light *policy* floor is **not** here — it is
  in the driver, expressed in counts (§7.11's 64-count proposal), because it is a device fact.
  This function only refuses the arithmetic that cannot be done at all.
- **Downstream**: none.
- **Upstream**: `_store_isl()`. Expectation: `None` rather than a division error — met.
- **Logging**: none.
- **Done when**: tested at the zero sum, just above and below `_CHROMA_SUM_MIN`, with a known
  illuminant vector (D65 → x≈0.3127, y≈0.3290, which is a real external check rather than a
  self-consistent one), and the D.12 matrix.

---

#### M4 `cct_mccamy(chroma_x, chroma_y) -> float | None`

- **Where**: `src/math_helpers.py`.
- **Purpose**: McCamy's 1992 cubic approximation of correlated colour temperature from
  chromaticity.
- **Functionality**: `n = (x - 0.3320) / (0.1858 - y)`, then
  `CCT = 449n³ + 3525n² + 6823.3n + 5520.33`.
- **Failure modes**: `None` input; **`y == 0.1858`** exactly, the epicentre singularity — a real
  division-by-zero, not a theoretical one, because it is a plausible chromaticity; a result
  outside McCamy's usable span, which the formula happily produces as a number with no indication
  that it is meaningless; NaN.
- **Handling**: guard `abs(0.1858 - y) < _CCT_EPICENTRE_EPS` → `None`. Clamp-or-reject on the
  output: **reject**, returning `None` outside `_CCT_MIN = 2000.0` / `_CCT_MAX = 12500.0` (§7.11),
  because a clamped 12500 would be indistinguishable from a real 12500. Domain gate on the inputs
  at `[0, 1]` for both.
- **Downstream**: none.
- **Upstream**: `_store_isl()`. Expectation: `None` is a legitimate, expected result and is
  already inside the declared measurement-value union — met.
- **Logging**: none.
- **Done when**: tested at the epicentre, either side of it, at both span limits, against two
  published (x, y) → CCT pairs, **and — see §5.3 — against the sign-flipped form of the same
  formula, asserting both give the same answer**. That last test is the one that stops a future
  reader "correcting" the coefficients to the other published variant.

---

#### M5 `ema_step(previous, sample, coefficient) -> float | None`

- **Where**: `src/math_helpers.py`. **Part G.2 catalogue entry** — §7.8 found this shape inline in
  the legacy SHTC3/MPRLS readers and nowhere in `src/`; promoting it is a Part G extension, and
  the catalogue must be updated in the same commit or the next driver duplicates it again.
- **Purpose**: the project's single first-order exponential moving average.
- **Functionality**: `previous + coefficient * (sample - previous)`. `coefficient <= 0` means
  "filter off" and returns `sample` unchanged — the legacy convention, kept so `FiltCoeff = -1.0`
  keeps meaning what it means today. `previous is None` returns `sample` (first sample seeds the
  filter).
- **Failure modes**: `sample is None`; `coefficient > 1.0`, which makes the filter overshoot and
  ring; NaN in either value, which poisons `previous` permanently — the nastiest one, because a
  single NaN sample would make every later output NaN for the lifetime of the task.
- **Handling**: `sample is None` → `None` (nothing to filter, and the caller must not advance its
  stored state). `coefficient` outside `(0.0, 1.0]` → treated as off, returning `sample`, rather
  than rejected: the schema already bounds it to `[-1.0, 1.0]`, so this is defence in depth. NaN
  `sample` → `None`, via an explicit `sample != sample` test, which is the only way to catch it
  before it enters the state.
- **Downstream**: none.
- **Upstream**: the gain-ratio learner (R12) and, if §13 q6 lands there, the output filter. Both
  expect a value they can store as the new `previous` — met, since every non-`None` return is
  finite.
- **Done when**: tested for the off path, the seeding path, convergence to a constant input within
  a stated number of steps, the NaN-poisoning case explicitly, and the D.12 matrix. Part G.2's
  catalogue table carries a row for it.

---

### 4.2 `src/asy_isl29125_driver.py` — module-level pure helpers

These are chip-specific, so per §14.4 rule 2 they stay in the driver rather than moving to
`math_helpers.py`. They are module-level rather than methods so the unit tests can reach them
without constructing a reader — `base_classes.py`'s own `_checked_write_results()` and
`print_log.py`'s module-level helpers are the precedent for a private module function in `src/`.

---

#### F1 `_decode_rgb_burst(raw) -> tuple[int, int, int] | None`

- **Where**: module level.
- **Purpose**: turn the six bytes read from `0x09` into `(green, red, blue)` counts.
- **Functionality**: `struct.unpack("<HHH", raw)`, returned in register order. **The register
  order is G, R, B** (Table 1 p9, and Table 20 p13 mislabels it — §5 defect 3), so the function
  returns green first and its name says so. Rejects anything that is not exactly 6 bytes.
- **Failure modes**: `raw` is `None` (layer 1 returned `None` for a malformed format); `raw` is
  not `bytes`; wrong length; `struct.error`/`ValueError` from a malformed buffer.
- **Handling**: every one of them → `None`. The caller (P9) turns `None` into a raised `OSError`,
  because at the protocol layer a read that produced nothing is a bus fault. Splitting it this way
  keeps the pure function pure and testable.
- **Downstream**: `struct.unpack`. Its MicroPython behaviour is the one to check: `unpack` on a
  short buffer raises, it does not pad — the length check makes that unreachable.
- **Upstream**: `ISL29125_I2C.read_counts()` only.
- **Logging**: none (pure).
- **Done when**: tested with a known 6-byte pattern proving the G/R/B order and little-endian
  byte order, with 0/5/7-byte inputs, with `None`, with a `bytearray` and a `memoryview` (both
  legitimate from layer 1), and with the all-`0xFF` pattern that F5 later has to recognise.

---

#### F2 `_normalise_triple(green, red, blue, *, resolution_bits, dark_offset) -> tuple[int, int, int]`

- **Where**: module level.
- **Purpose**: step 2 and step 3 of §7.1's chain — put 12-bit and 16-bit readings on one 0-65535
  scale and remove the additive dark offset.
- **Functionality**: if `resolution_bits == 12`, `value << 4` (RIOT's `resfactor`, confirmed
  verbatim in §5.2); then subtract `dark_offset`; then clamp at 0. Returns ints, not floats — the
  scale conversion to lux happens in F3, and keeping counts integral means the saturation and
  threshold comparisons downstream are exact.
- **Failure modes**: a count above 65535 (impossible from a 16-bit read, possible from a test);
  `dark_offset` larger than the count, which without the clamp produces a negative count and then
  a negative lux; a `resolution_bits` value that is neither 12 nor 16.
- **Handling**: clamp to `[0, 65535]` after the subtract. An unknown `resolution_bits` is treated
  as 16 (no shift) — the conservative choice, because shifting when you should not have inflates
  every reading 16×, whereas not shifting when you should have only under-reports; and the schema
  already restricts the field to `{12, 16}`, so this is unreachable in production.
- **Downstream**: none.
- **Upstream**: `_read_isl()`. Expects exactness for the saturation test — met, because the clamp
  is at 65535 and the shift is integral.
- **Logging**: none.
- **Done when**: tested at both resolutions, at the 12-bit maximum (4095 → 65520, **not** 65535 —
  the shift cannot reach full scale, and any saturation test that assumes it can is wrong at
  12-bit; this is a real trap and gets its own test), with a dark offset exceeding the count, and
  with the unknown-resolution fallback.

---

#### F3 `_counts_to_lux(count, full_scale, gain_correction) -> float`

- **Where**: module level.
- **Purpose**: step 4 of §7.1 — counts to absolute lux, using the *calibrated* gain rather than
  the nominal 26.67.
- **Functionality**: `count * (full_scale / 65535.0) * gain_correction`. `full_scale` is 375.0 or
  10000.0 (p1's own feature list, cross-checked in §7.1: 375/65535 = 5.72 mlux and 10000/65535 =
  0.1526 lux match the datasheet's stated per-LSB figures exactly). `gain_correction` is 1.0 on
  the low range and `nominal_ratio / learned_ratio` on the high range — so the low range is the
  reference and the learned ratio only ever corrects the high one. Fixing which range is the
  reference matters: correcting both would make the absolute scale drift with the calibration.
- **Failure modes**: `gain_correction` of 0 or negative from a corrupted FRAM value; a `full_scale`
  that is neither of the two constants.
- **Handling**: the function is total and does no validation — **the validation belongs at the
  boundary**, in `_load_gain_ratio()` (R13), which is the only place an untrusted ratio enters.
  That is a deliberate split: putting a plausibility gate in the hot path would run it on every
  sample for a value that changes once a day. The function's comment must say where the gate is.
- **Downstream**: none.
- **Upstream**: `_read_isl()`, three times per cycle.
- **Logging**: none.
- **Done when**: tested against both full scales at count 0, 1, 65535, and against the datasheet's
  own two LSB figures to 3 significant figures — an external check, not a self-consistent one.

---

#### F4 `_fraction_to_counts(fraction) -> int`

- **Where**: module level.
- **Purpose**: convert an auto-range switch point expressed as a percentage of full scale into the
  threshold register value.
- **Functionality**: `int(round(fraction * 0.01 * 65535.0))`, clamped to `[0, 65535]`.
- **Failure modes**: **integer truncation** — RIOT does `(uint16_t)(65535 / max_range)` and
  truncates 6.55 to 6, a 9% error (§7.6 calls it out as a cautionary example). NaN/inf fraction.
  A fraction outside `[0, 100]`.
- **Handling**: do the whole computation in float and round once at the end, which is the entire
  reason this is a named function instead of an inline expression. Clamp the result. NaN → 0 via
  the clamp's own comparison ordering, which must be written so that NaN lands somewhere defined
  rather than propagating into `int()` (where MicroPython raises `ValueError`) — so the guard is
  explicit, not incidental.
- **Downstream**: none.
- **Upstream**: `_switch_range()`.
- **Logging**: none.
- **Done when**: a test asserts `_fraction_to_counts(85.0) == 55705` and
  `_fraction_to_counts(1.5) == 983` (the two schema defaults, and the second is the one §7.6's
  arithmetic depends on), plus the NaN/inf/out-of-range cases, plus an explicit regression test
  named for the RIOT truncation trap.

---

#### F5 `_is_bus_fault_pattern(counts, status) -> bool`

- **Where**: module level.
- **Purpose**: distinguish genuine optical saturation from a dead bus reading all-ones (§7.6).
- **Functionality**: returns `True` only when **all three** counts are exactly 65535 **and** the
  status byte is implausible. "Implausible" is precise: `0x08`'s B7:B6 and B3 are reserved and
  read zero (Table 15, p12), so `status & 0xC8 != 0` is impossible on a working part. `0xFF`
  satisfies it; so does any other pattern with a reserved bit set.
- **Failure modes**: a false positive — a genuinely saturated white scene *and* a corrupted status
  byte in the same cycle, which would discard a real sample; a false negative — a bus fault that
  happens to return a plausible status byte, which would drive the range up and leave it there.
  Both are inherent to a heuristic and neither can be designed away without a second transaction.
- **Handling**: the *caller* resolves it rather than this function: on `True`, `_read_isl()`
  re-reads the device ID (`0x00` → `0x7D`, p9 Table 2) and only then treats the cycle as a bus
  fault. So the heuristic decides whether to spend one extra transaction, never what the answer
  is. That makes the false-positive cost one wasted read and the false-negative cost bounded by
  the leaky bucket.
- **Downstream**: none.
- **Upstream**: `_read_isl()`.
- **Logging**: none here; the caller logs `errno=32` if the ID re-read confirms the fault, and
  `wrnno=14` if it turns out to be real saturation on the high range.
- **Done when**: tested with all-ones + `0xFF`, all-ones + a valid status, two-of-three at 65535
  (must be `False` — a real saturated scene with one unsaturated channel), and the 12-bit case
  where the normalised maximum is 65520 and this can therefore never fire at all (worth an
  explicit test, because it means the fast path behaves differently at 12-bit and that has to be
  a known property rather than a surprise).

---

### 4.3 `ISL29125_Reader` — the task/config layer

Before the individual functions, three structural decisions this document has to make, because
the plan does not and every function below depends on them.

**(a) One flag, one waiter.** MicroPython's own documentation (v1.29.0 `docs/library/asyncio.rst`,
read this session — §5.3) states that a `ThreadSafeFlag` *"may only be waited on by a single task
at a time"*, and that `wait()` *"returns immediately"* if the flag is already set. The driver has
two trigger sources — the 1 s timer divider and the INT pin — and `SCD30_Reader` solves the same
problem with two flags and two tasks (`start_trigger_event` waited by `scd_init_irq()`,
`irq_trigger_event` waited by `read_loop()`). This driver uses the same two-flag/two-task shape,
but with the roles that fit its own hardware:

| Flag | Set by | Waited by | Meaning |
|---|---|---|---|
| `base_trigger_event` | the 1 s `Timer` callback | `_base_trigger()` | one tick of the software divider |
| `read_event` | `_base_trigger()` (interval elapsed) **and** the pin IRQ handler | `read_loop()` | do a full read cycle now |

Two setters on one flag is safe and is what makes requirement 17 work: the INT is the fast path,
the timer is the guaranteed one, and they **coalesce** rather than racing — because a set with no
waiter is remembered, an INT arriving mid-cycle causes exactly one extra cycle afterwards, not a
lost event and not a queue. The read loop then asks the status byte *which* it was, rather than
inferring it from which flag fired.

**(b) A stuck-low INT cannot storm the loop.** The handler is edge-triggered
(`Pin.IRQ_FALLING`), and reading `0x08` clears the flag and releases the pin (p11). A line held
low by a fault therefore produces exactly one falling edge and then nothing — the failure mode is
silence, which is what requirement 17 and `wrnno=15` exist for, not a flood.

**(c) `_error_check()` must not see a legitimately-`None` field.** `base_classes.py:214` counts a
failure when **any** element of the tuple it is given is `None`. `CCT` is `None` in a dark room by
design (§7.11), and `Hue`/`Sat` are reported as unreliable near the dark floor (§7.4). If the
namedtuple were passed to `_error_check()`, a dim room would increment the leaky bucket every
cycle and restart the task at `max_module_error`. So `_read_isl()` returns a **narrow results
tuple** — `(green, red, blue, timestamp)`, the four things whose absence really is a failed read —
and `_store_isl()` builds the wide namedtuple separately. `BMP3xx_Reader` already splits it this
way (`BMPResults` is 3-tuple, `BMP3XX` is a 4-field namedtuple); here the split is not stylistic,
it is load-bearing.

---

#### R1 `__init__(self, i2c, irq_pin, trigger_sec=1, max_module_error=5, cfg_path="", fram=None, fram_ntp_callback=None, history_length=10, debug=None)`

- **Where**: `ISL29125_Reader`, first method.
- **Purpose**: construct the whole object graph — protocol layer, config manager, logger, both
  FRAM chunks, the trigger machinery — without touching the bus.
- **Functionality**: `super().__init__(...)` with the ten-field namedtuple's all-`None` instance,
  `_NAME`, and the concatenated `_VAL_*` schema; `self.isl = ISL29125_I2C(i2c, address=address)`;
  `self.irq_pin = Pin(irq_pin, mode=Pin.IN, pull=Pin.PULL_UP)` (§7.12 — the one place this driver
  deliberately differs from SCD30); the two `ThreadSafeFlag`s and the `Timer()`; `LockedValue` for
  the trigger period; the gain-ratio FRAM chunk via `fram.get_timestamped_chunk(...)`; and the 13
  `_push_callbacks` / 5 `_get_callbacks` registrations.
- **Argument-order note**: C.2 fixes `(i2c, irq_pin, ...)` positionally, matching `SCD30_Reader`.
  The keyword is **`fram=`**, not `fram_storage=` — §13 question 7's recommendation; if the owner
  decides otherwise this is the one line that changes.
- **Failure modes**: FRAM chunk allocation returns `None` or raises (out of space, manager not
  valid); `Pin()` raising on a bad pin id; the `Timer()` allocation; a `trigger_sec` outside the
  schema range. **Not** a failure mode: the chip being absent — nothing here talks to the bus.
- **Handling**: the chunk allocation is wrapped in a broad `try`/`except Exception` setting
  `self.ts_storage = None`, with the *exact* justification `asy_sgp40_driver.py:104-113` gives —
  `__init__` runs before any task supervisor exists to catch an escape. A `None` chunk degrades to
  "no persisted calibration", never to a failed construction. `Pin`/`Timer` are left unguarded,
  matching all three drivers: a bad pin id is a wiring bug in `sensortask_dev.py`, caught by the
  dev test file at construction, not a runtime condition.
- **Downstream**: `SensorReaderConfig.__init__` (creates `ConfigManager` + logger — no I/O),
  `ISL29125_I2C.__init__` (creates the session — no I/O), `AsyFramManager.get_timestamped_chunk()`
  (pure bookkeeping, safe before `setup()` per C.13). Every one of those is I/O-free, which is
  what makes requirement 20 hold.
- **Upstream**: `sensortask_dev.build_system()`, and `tests/test_sensortask_dev.py`, which builds
  the whole graph against a fake with no ISL registers in it. **Requirement 20 is satisfied here
  or nowhere.**
- **Logging**: `pr.err("FRAM calibration storage allocation failed!")` — plain `err`, no `errno`,
  because `pr.setup()` has not run and a history write would be discarded with a diagnostic
  anyway (`print_log.py:194`).
- **Done when**: constructing with `fram=None`, with a manager that refuses allocation, and
  against `tests/machine.py`'s register-less fake all succeed and perform zero bus transactions —
  asserted on the I2C fake's own wire log, not by inspection.

---

#### R2 `_init_isl(self) -> bool`

- **Where**: `ISL29125_Reader`.
- **Purpose**: one-shot startup — logger, chip, stored configuration, stored calibration — run
  again from scratch on every task-supervisor restart.
- **Functionality**, in order, matching `_init_bmp()` step for step:
  1. `await self.pr.setup()` (required before any logged error persists);
  2. `self._err_cnt_internal = 0`;
  3. `await self.isl.setup()` inside `try` → `errno=10`, return `False`;
  4. `pr.one("Setting sensor config at startup.")`;
  5. read the int batch and the float batch from `cfgmgr` (`_N_INT_CFG`, `_N_FLOAT_CFG`) →
     `errno=12`, return `False` on a short or `None` result;
  6. `await self.set_trigger_secs(...)` — never fails the init, same reasoning as BMP3xx's own
     comment (a bad stored interval is a software knob, not a reason to give up);
  7. one `await self.isl.configure(...)` applying resolution, range, IR compensation and persist
     **in a single burst** → `errno=13`, return `False`;
  8. `await self._load_gain_ratio()` — never fails the init (see R13);
  9. if auto-range is on, `await self._switch_range(self._active_range)` to arm the thresholds for
     the range it is starting on — **easy to miss**: without it the part boots with both
     thresholds at their `0x0000` power-on default and the INT path is dead until the first
     switch;
  10. `pr.one("initialized")`, return `True`.
- **Failure modes**: chip absent or silent; device ID mismatch; a corrupt config file; FRAM
  unreadable; a stored value the schema accepts but the chip rejects; **startup transients** —
  §3.5 records that the legacy driver was far less tolerant at startup than in steady state, and
  requirement 16 says that asymmetry has to go.
- **Handling**: every step that can raise is individually wrapped with its own `errno`. Returning
  `False` breaks `read_loop()`, which ends the task, which `system_service.py`'s supervisor
  restarts — so a transient failure retries on the same leaky-bucket terms as steady state, which
  is exactly what requirement 16 asks for. No retry loop inside this function: the supervisor
  *is* the retry loop, and adding a second one would double the error budget invisibly.
- **Downstream**: `pr.setup()` (never raises), `ISL29125_I2C.setup()` (may raise — wrapped),
  `cfgmgr.get_int_values`/`get_float_values` (return `None`, never raise — length-checked),
  `_load_gain_ratio()` (never raises), `_switch_range()` (never raises, logs its own errnos).
  All four behaviours accounted for.
- **Upstream**: `read_loop()` only. Its expectation is a plain `bool` and no raise — met.
- **Logging**: `errno` 10, 12, 13; `pr.one` twice; `wrnno` 11/12 come from `_load_gain_ratio()`.
- **Done when**: tests cover each of the three failure exits, the successful path's exact
  transaction sequence (device ID → reset → BOUTF clear → shadow burst → threshold burst), the
  "config file missing" path, and a restart after a failure leaving no state behind
  (`_err_cnt_internal` back to 0, shadow re-applied from config, not from the previous run).

---

#### R3 `read_loop(self) -> bool`

- **Where**: `ISL29125_Reader`. The task `start_asy_read()` creates.
- **Purpose**: the driver's whole steady-state lifecycle.
- **Functionality**:
  ```
  if not await self._init_isl(): return False
  while True:
      await self.read_event.wait()
      self.pr.evt("sensor trigger")
      results = await self._read_isl()
      if not await self._error_check(results): return False
      await self._store_isl(results)
  ```
  Identical in shape to all three existing drivers — deliberately, because §14.2 item 5 requires
  `_error_check()` exactly once per cycle and the auto-range machinery must not grow a second
  counter beside it. Everything this driver adds happens *inside* `_read_isl()`.
- **Failure modes**: `_init_isl()` returning `False`; the error budget exhausted; a raise escaping
  `_read_isl()` or `_store_isl()` (which would kill the task with a traceback rather than a clean
  restart).
- **Handling**: the first two return `False` and let the supervisor restart the task. The third
  must be impossible by construction — that is the reader layer's never-raise contract, and the
  test for it is an injected raise at every layer-2 entry point, asserting the loop survives.
- **Downstream**: `_init_isl()`, `_read_isl()`, `_error_check()`, `_store_isl()`.
- **Upstream**: `system_service.py`'s supervisor, generically via `get_task_starters()`. It
  expects a task that either runs forever or ends cleanly, and that a `MemoryError` is caught
  (Part I) — met, since the supervisor catches `Exception` and `MemoryError` is one.
- **Logging**: `pr.evt("sensor trigger")`; everything else is delegated.
- **Done when**: a test drives N cycles through the fake and asserts exactly N `_error_check()`
  calls; another asserts the loop exits `False` after `max_module_error` consecutive failed reads
  and not before; another injects a raise from each of the four callees and asserts no traceback
  escapes.

---

#### R4 `_read_isl(self) -> ISLResults`

- **Where**: `ISL29125_Reader`. **The centre of the driver** — everything the promotion adds runs
  here.
- **Purpose**: acquire one coherent sample, decide the range, and maintain the calibration.
- **Functionality**, in order:
  1. `timestamp = time.mktime(time.gmtime())` **first**, as all three drivers do (so the timestamp
     is the read's start, and a slow read cannot make a stale sample look fresh);
  2. if a settle deadline is pending, `await self._settle_wait()` and log the discard at `all`;
  3. `status = await self.isl.read_status()` — one destructive read of `0x08` that carries
     `RGBTHF`, `CONVENF`, `BOUTF` and `RGBCF` together (§7.7), so the interrupt cause, the
     brownout flag and the conversion state cost one transaction between them;
  4. `brownout, threshold_fired = self._handle_status(status)`; if `brownout`, run
     `_recover_brownout()` and **return an all-`None` result for this cycle** — the chip was in
     power-down, so whatever is in the data registers is not a measurement;
  5. `counts = await self.isl.read_counts()` → `_normalise_triple(...)`;
  6. saturation/bus-fault discrimination via `_is_bus_fault_pattern()`, with the device-ID re-read
     on a hit (§7.6);
  7. `_evaluate_range(green, saturated)` → if it returns a target, `_switch_range()` it and mark
     the sample as the last one on the old range (it is still valid — the switch takes effect for
     the *next* cycle);
  8. `_learn_gain_ratio(green)` when the reading sits in the overlap band (§7.3);
  9. `pr.all("read")`; return `(green, red, blue, timestamp)`.
- **Failure modes**: any bus transaction raising; the status read succeeding but the data read
  failing (a torn cycle); a brownout mid-cycle; all-ones from a dead bus; the settle wait being
  invalidated by a concurrent config write (see R11); a `RGBCF` value saying a conversion is
  mid-flight — which the design explicitly does **not** act on, because the data registers are
  double-buffered and "the data is always valid" (p13, §7.6).
- **Handling**: one `try` around the whole sequence, `except Exception` → all four results `None`,
  `errno=11`, exactly as `_read_bmp()`/`_read_scd()` do. Inner paths that must be distinguishable
  get their own errno *and re-raise nothing* (`errno=31` status read, `errno=32` confirmed bus
  fault, `errno=29`/`30` inside the switch). A brownout is **not** an error: `wrnno=10`, results
  `None`, and the cycle is skipped — which does mean the leaky bucket sees one `None` cycle, and
  that is correct: the driver genuinely has no sample, and one increment against a budget of 5 is
  the right cost for a recovered brownout.
- **Downstream**: P10 `read_status()`, P9 `read_counts()`, P13 `get_device_id()`, F2/F5, R7-R12.
  Every callee's raise path is inside the outer `try`; every callee's `None` path is checked at
  the call site.
- **Upstream**: `read_loop()` expects a fixed-length tuple whose `None`-ness means "failed read" —
  met by the narrow 4-tuple (see (c) above).
- **Logging**: `all` for "read"; `errno` 11/29/30/31/32; `wrnno` 10/14/15; `evt` for a range
  decision.
- **Done when**: tests exist for a clean cycle, a bus fault at each of the three transactions, a
  brownout cycle, a saturated cycle on each range, an all-ones cycle with a good and a bad device
  ID re-read, a cycle during settle, and — the one that proves requirement 17 — a cycle where the
  INT never fired but the count is past the switch point, asserting the range still moves.

---

#### R5 `_store_isl(self, results) -> None`

- **Where**: `ISL29125_Reader`.
- **Purpose**: turn the narrow results tuple into the ten-field measurement namedtuple, applying
  the derived maths and the output filter.
- **Functionality**: bail out unchanged if any element is `None` (all three drivers open this way);
  read the float config batch (`FiltCoeff`) → `errno=14` on failure, falling back to the schema
  defaults rather than returning; convert each channel with `_counts_to_lux()`; normalise RGB to
  0-1 over the active full scale (requirement 8); `Lux` from green alone (§7.5); `rgb_to_hsb()`;
  `rgb_to_xyz()` → `chromaticity_xy()` → `cct_mccamy()`, gated by the green-count low-light floor;
  apply `ema_step()` to the filtered outputs if `FiltCoeff > 0`; `await self._set_meas_data(...)`;
  `pr.all("data stored")`.
- **Failure modes**: config batch unreadable; a maths helper returning `None` (expected, not a
  failure); the filter state poisoned by a NaN (M5 handles it); **the `Range` field's meaning** —
  see the open question below.
- **Handling**: `None` from any helper is stored as `None` in that field and nowhere else; one
  `None` never blanks the rest of the tuple. The config-read fallback mirrors `_store_bmp()`'s
  `comp_values = [0.0, ...]` pattern exactly.
- **Downstream**: M1-M5, F3, `_set_meas_data()` (never raises), `cfgmgr.get_float_values()`
  (returns `None`, never raises).
- **Upstream**: `read_loop()`; and through `get_data()`/`get_dict_data()`, the webserver and the
  website. Their expectation is that every field is one of `int | float | str | bool | None` —
  met.
- **Logging**: `errno=14`; `pr.all("data stored")`.
- **Done when**: a table-driven test walks known count triples to expected Lux/RGB/HSB/CCT values
  computed by hand, including the low-light floor boundary in both directions, the filter on and
  off, and the config-read-failure fallback.

> **New open question (q9), raised not fixed.** `Range` is both a **config field** (the fixed
> range selected when `RangeAuto` is off, §8.3) and a **measurement field** (the range actually
> active, §8.4). They live in different groups so the JSON is unambiguous, but they share a label
> in the UI and a name in the code, and under auto-range they routinely disagree — which is the
> normal case, not an error state. Recommendation: keep the config field as `Range` and rename the
> measurement field to **`RangeAct`**, which is 8 characters and reads correctly in
> `js/render.js`'s flattened form. This is the project owner's call; every table in this document
> says `Range` so that a rename is one substitution.

---

#### R6 `_read_sensor_dict(self) -> dict[str, ...]`

- **Where**: `ISL29125_Reader`. Passed as `get_dict_cfg(callback=...)`, convention 11.
- **Purpose**: report what the **chip** currently holds for the five hardware-backed config
  fields, as opposed to what the config file says.
- **Functionality**: one `await self.isl.get_config_snapshot()` — a single 3-byte burst read of
  `0x01`-`0x03` under one device-session lock — decoded into `Resolution`, `Range`,
  `IrCompOffset`, `IrCompAdjust`, `AutoRangePersist`.
- **The shadow-model resolution, decided here.** §8.7 says the shadow is authoritative and the
  driver "never reads the config registers back to modify them". That rule is about the
  read-modify-write hazard, and it does not forbid a **read-only** snapshot: Table 7 (p10) makes
  only a *write* to `0x01` restart the conversion, so the read costs one transaction and nothing
  else. Reading the real registers rather than reporting the shadow is strictly better, because it
  is the only thing in the driver that can detect the shadow and the chip having diverged — which
  is the failure `BOUTF` exists for and the one a shadow can never see by looking at itself.
- **Failure modes**: the burst read raising or returning `None`; **the `Range` disagreement** —
  under auto-range the chip's `RNG` bit is the auto-range machinery's choice, not the user's
  setting, so reporting it as the value of the `Range` *config* field would overwrite the user's
  stored preference in the displayed config.
- **Handling**: one `try`/`except` returning `dict.fromkeys(..., None)` with `errno=28` —
  `_read_sensor_dict()` must catch rather than leaving it to `_get_dict_cfg()`'s own guard, for
  the reason `asy_bmp3xx_driver.py:141-148` records: the outer guard skips the whole dict update
  and leaves the fields showing persisted values as if they were live. For the `Range` field:
  **when `RangeAuto` is true, omit `Range` from the returned dict** so `_get_dict_cfg()` keeps the
  persisted value, and report the active range through the measurement field where it belongs.
- **Downstream**: P12 `get_config_snapshot()`.
- **Upstream**: `_get_dict_cfg()` (`base_classes.py:181`), which already wraps the call and warns
  on unknown keys (`wrnno=1`) — so the returned keys must exactly match `name_cfg(_VAL_*)` for the
  five fields, or every `GET /sensors` logs a warning.
- **Logging**: `errno=28`.
- **Done when**: tested for the clean path, the raise path (asserting the five keys come back
  `None` and errno 28 is recorded), the auto-range omission of `Range`, and a key-name test
  asserting no `wrnno=1` warning is produced.

---

#### R7 `_handle_status(self, status) -> tuple[bool, bool]`

- **Where**: `ISL29125_Reader`. Pure (no `await`), so it is directly testable.
- **Purpose**: decode the one status byte into the two facts the read path needs.
- **Functionality**: returns `(brownout, threshold_fired)` from `BOUTF` (`0x08` B2, Table 18 p12)
  and `RGBTHF` (B0, Table 16 p12). `CONVENF` (B1) and `RGBCF` (B5:4) are decoded into `all`-level
  log output only — deliberately not acted on (§7.6 closed `CONVEN`; `RGBCF` is redundant against
  double-buffered data registers).
- **Failure modes**: a reserved bit set (B7:B6, B3) — the same implausibility F5 uses; `status`
  arriving as something other than an int from layer 1.
- **Handling**: a non-int is treated as "no flags" and left to the read path's own fault
  discrimination; reserved bits set are reported to the caller through F5 rather than decided
  here, so there is exactly one place that owns the bus-fault verdict.
- **Downstream**: none.
- **Upstream**: `_read_isl()`.
- **Logging**: none directly (the caller logs).
- **Done when**: a table test over all 256 byte values asserting the two booleans, plus the
  non-int case.

---

#### R8 `_recover_brownout(self) -> bool`

- **Where**: `ISL29125_Reader`.
- **Purpose**: §9.3's self-heal — the chip has been through power-down, so its entire
  configuration is `0x00` and it is not converting.
- **Functionality**: re-apply the whole shadow in one burst (`configure()` with no changes, which
  writes `CONFIG1`-`CONFIG3`), re-arm both thresholds, clear `BOUTF` by writing it low, set the
  settle deadline (the `CONFIG1` write restarted the cycle), return `True`.
- **Failure modes**: the re-apply raising; `BOUTF` failing to clear (a persistent brownout, i.e. a
  supply that is still sagging) — in which case every cycle would re-run this and log a warning,
  which is a flood;   the chip being genuinely gone.
- **Handling**: `errno=33` on a raise, returning `False` and letting the cycle count as a failed
  read. Against the flood: `wrnno=10` is logged on the **transition** into the recovered state
  only — a `self._brownout_seen` latch cleared when a subsequent cycle reads `BOUTF` low — so a
  sagging supply produces one warning and one entry per genuine event, not one per second.
- **Downstream**: P7 `configure()`, P8 `set_thresholds()`, P11 `clear_brownout()`.
- **Upstream**: `_read_isl()` step 4.
- **Logging**: `wrnno=10` on the transition; `errno=33` on failure.
- **Done when**: the twin's chip fake can be forced into the post-brownout state
  (`CONFIG1 = 0x00`, `BOUTF` high) and a test asserts the driver rewrites all three config bytes,
  re-arms the thresholds, clears the flag, discards one cycle, logs exactly one warning across
  repeated recovery, and resumes correct readings.

---

#### R9 `_evaluate_range(self, green_counts, *, saturated) -> int | None`

- **Where**: `ISL29125_Reader`. Pure except for reading `self`'s settings; **no I/O**, which is
  what lets the INT path and the periodic path share it (requirement 17).
- **Purpose**: decide whether the range should change, and to what.
- **Functionality**:
  - on the **low** range: switch up if `saturated`, or if `green_counts >= _fraction_to_counts(AutoRangeUp)`;
  - on the **high** range: switch down if `green_counts <= _fraction_to_counts(AutoRangeDown)`
    **and** `AutoRangeDwell` seconds have elapsed since the last switch up;
  - never switch while a settle deadline is pending;
  - never switch when `RangeAuto` is false;
  - returns the target range constant, or `None` for "stay".
- **Failure modes**: chatter, if the schema's cross-field constraint `d ≤ u/(2r)` is violated
  (§7.6's arithmetic); an immediate switch back after a switch, if the settle guard is missing;
  a switch-down triggered by a passing shadow, which `AutoRangeDwell` exists to prevent; `dwell`
  arithmetic wrapping — `time.ticks_ms()` wraps at 2³⁰ on MicroPython and **must** be compared
  with `time.ticks_diff()`, never by subtraction (Part F; every existing driver uses
  `ticks_diff`).
- **Handling**: the cross-field constraint is enforced on **write** (see the push table, `errno=27`),
  so this function can assume it. The settle and dwell guards are explicit early returns. Ticks
  arithmetic is `ticks_diff` throughout.
- **Downstream**: F4 only.
- **Upstream**: `_read_isl()`, on every cycle — both the INT-driven one and the periodic one. That
  is the whole of requirement 17: there is no separate interrupt-only decision path to get out of
  step with this one.
- **Logging**: none here (the caller logs the decision at `evt`), except that the caller
  increments the `wrnno=15` counter when this returns a target while `threshold_fired` was false.
- **Done when**: a pure-function test sweeps counts across both switch points in both directions
  and asserts no state in which an up-decision is immediately followed by a down-decision at the
  same illumination (the chatter proof, run at the schema's default `u`/`d` **and** at its
  worst legal pair); plus settle, dwell and `RangeAuto=False` guard tests.

---

#### R10 `_switch_range(self, target_range) -> bool`

- **Where**: `ISL29125_Reader`.
- **Purpose**: execute a range change: new thresholds, new `RNG` bit, new settle deadline, dwell
  bookkeeping.
- **Functionality**: compute the new threshold pair for the *target* range (§7.6: on the low range
  `high = u·65535, low = 0`; on the high range `low = d·65535, high = 0xFFFF` — only one crossing
  is meaningful per range and arming both would be arming a threshold on the wrong gain scale);
  write them as one 4-byte burst at `0x04`; then `configure(range=target)`, which is the
  `CONFIG1` write that both changes the gain and restarts the conversion cycle; record
  `self._last_switch_ms` and `self._active_range`.
- **Ordering matters**: thresholds first, `RNG` second. The other order leaves a window in which
  the new gain is live against the old thresholds, which on a bright-to-dim transition fires an
  immediate spurious interrupt.
- **Failure modes**: either write raising; a partial application (thresholds written, `RNG` not),
  which leaves the hardware in the window just described; the settle deadline not being set, which
  would let the next cycle read mid-conversion data.
- **Handling**: `errno=29` for the threshold write, `errno=30` for the `CONFIG1` write; on the
  partial-application case the function returns `False` **without** updating `_active_range`, so
  the next cycle re-evaluates and retries the whole switch — idempotent by construction, because
  both writes are absolute values, not increments. The settle deadline is **not** set here: it is
  set by `configure()` itself (see P7), so it cannot be forgotten by a caller and it is refreshed
  by *any* writer of `CONFIG1`, including a concurrent config push.
- **Downstream**: P8, P7, F4.
- **Upstream**: `_read_isl()` and `_init_isl()` step 9.
- **Logging**: `evt` with from/to and the deciding count; `errno` 29/30.
- **Done when**: a wire-log test asserts the exact two transactions in the exact order with the
  exact bytes for both directions; a failure-injection test asserts a retry on the next cycle
  after a partial application; and the twin-tier continuity test (§6.4) sees no step in reported
  lux across the switch beyond the stated tolerance.

---

#### R11 `_settle_wait(self) -> None`

- **Where**: `ISL29125_Reader`.
- **Purpose**: discard the conversion that a `CONFIG1` write aborted (§7.6).
- **Functionality**: `await asyncio.sleep_ms(remaining)` where `remaining` comes from
  `self.isl.time_to_settle_ms()`, itself derived from the deadline `configure()` set and the
  resolution-dependent cycle time (~303 ms at 16-bit, ~19 ms at 12-bit — the latter derived, not
  specified, §7.2). Re-checks the deadline after waking, because a concurrent config write may
  have pushed it out.
- **Failure modes**: the deadline being extended repeatedly by a stream of config writes, which
  would starve the read loop; the sleep being longer than the sample interval, which at 16-bit and
  `SampleInterv = 1` it is not (303 ms < 1 s) but at a future shorter interval could be; question 1
  in §13 — if a `CONFIG1` write turns out **not** to restart the cycle, this wait is simply
  unnecessary, never wrong.
- **Handling**: a bounded loop (at most `AutoRangeSettle` full cycles, the schema field that
  exists exactly for this) rather than an open `while deadline_pending`. Past the bound the driver
  proceeds and lets the reading stand — a possibly-stale sample is better than a starved loop, and
  the bucket will catch a persistent problem.
- **Downstream**: P14 `time_to_settle_ms()`, `asyncio.sleep_ms`.
- **Upstream**: `_read_isl()` step 2.
- **Logging**: `all`.
- **Done when**: tested for the normal wait, the bound, the re-extension case, and both
  resolutions; and the twin asserts no glitch sample is reported in the cycle after a switch.

---

#### R12 `_learn_gain_ratio(self, green_counts) -> None`

- **Where**: `ISL29125_Reader`.
- **Purpose**: §7.3's self-calibration — replace the nominal 26.67 with the device's real ratio,
  because that error *is* the visible step at each transition.
- **Functionality**: when the illumination sits in the overlap band (bright enough to be well
  above the dark floor on the low range, dim enough not to clip it — in practice the band around
  the switch point), take one reading on each range within the same quiet period, compute
  `ratio = lux_high_counts_equivalent / lux_low_counts_equivalent`, low-pass it with
  `ema_step(previous_ratio, sample_ratio, _GAIN_EMA_COEFF)` and persist it (R14) at most once per
  configured period.
- **Failure modes**: learning from a *changing* scene, which produces a ratio that is really a
  brightness change — the dominant error source and the reason the two readings must be adjacent
  and the result low-passed hard; a ratio far from nominal, which means something else is wrong;
  the extra range switch this needs costing two settle windows; learning during the settle window
  itself; runaway drift if the EMA coefficient is too high.
- **Handling**: **plausibility gate** — accept only `_GAIN_RATIO_MIN = 20.0` to
  `_GAIN_RATIO_MAX = 34.0` (nominal 26.67 ±~25%), reject with `wrnno=13` otherwise. Never learn
  while a settle is pending, while `RangeAuto` is false, or within `AutoRangeDwell` of a switch.
  The EMA coefficient is a module constant, not a config field — §8.3 declined a learning on/off
  switch and the same reasoning applies to its rate.
- **Downstream**: M5, R14, P9/P7 (for the paired reading).
- **Upstream**: `_read_isl()` step 8.
- **Logging**: `evt` old → new; `wrnno=13` on rejection.
- **Done when**: the twin's chip fake carries a deliberately **non-nominal** per-instance ratio
  (§11.5) and a test asserts the learned value converges towards it within a bounded number of
  sweeps, that `ISLResetCal` returns it to nominal and it re-converges, and that a scene changing
  during the paired reading does not move the ratio outside the plausible band.

---

#### R13 `_load_gain_ratio(self) -> None` · R14 `_persist_gain_ratio(self) -> None` · R15 `_clear_gain_ratio(self) -> bool`

- **Where**: `ISL29125_Reader`. Specified together because they are one mechanism and their
  failure handling is symmetric. `asy_sgp40_driver.py`'s `_run_restore()`/`_run_backup()` are the
  line-by-line precedent, including the `require_ntp` handling.
- **Purpose**: keep the learned ratio across reboots, with the timestamp that makes
  `_isl_maintenance_status()` able to say *when* it was learned.
- **Functionality**: the chunk is an `AsyFramTimestampedChunk` holding one float plus CRC32.
  `read_into(buf)` returns `(ok, ts, age)`; `write_into(buf, require_ntp=...)` returns
  `(ntp_synced, ts, ok)`; `clear()` returns a bool. The float is packed with `struct.pack("<f", …)`
  — **4 bytes, not 8**: MicroPython's `float` is single-precision on rp2 by default, and a `"<d"`
  would waste half the chunk and misrepresent the precision actually stored.
- **Failure modes**: no chunk (allocation failed in `__init__` — `self.ts_storage is None`); no
  stored data (fresh unit); CRC mismatch; a stored value outside the plausible band (a corrupted
  chunk that still passes CRC because it was written by something else — the isolated-driver
  overwrite hazard CLAUDE.md documents for FRAM); NTP not yet synced, so a write would carry no
  timestamp; the FRAM being paused.
- **Handling**: **every one of them degrades to "use nominal 26.67"**, never to a failed init and
  never to a raise. `wrnno=11` for "nothing stored", `wrnno=12` for "no timestamp / too old",
  `errno=35/36/37` for a real read/write/clear failure. The plausibility gate is applied **on
  load**, not only on learn — that is the boundary where an untrusted value enters (see F3's note
  on why the hot path does not re-check).
- **Downstream**: `AsyFramTimestampedChunk` (never raises — `asy_fram_manager.py`'s own contract),
  `struct.pack`/`unpack`.
- **Upstream**: `_init_isl()`, `_learn_gain_ratio()`, `reset_gain_calibration()`,
  `get_mem_status()`.
- **Logging**: as above.
- **Done when**: `tests/test_fram_integration.py`-style round-trip coverage: write → read → same
  value; CRC corruption → nominal + warning; absent chunk → nominal, no crash, no errno; a value
  outside the band → rejected on load; and a real-hardware round trip across a reboot
  (§6.7's `reboot_persist_*` pair).

---

#### R16 `_base_trigger(self) -> None`

- **Where**: `ISL29125_Reader`. The task `start_asy_trigger()` creates.
- **Purpose**: divide the 1 s hardware timer down to `SampleInterv`, exactly as
  `BMP3xx_Reader._base_trigger()` does.
- **Functionality**: `while True: await self.base_trigger_event.wait(); counter += 1; if counter >=
  await self.trigger_period.get_value(): self.read_event.set(); counter = 0`.
- **Failure modes**: §3.4's legacy bug — the legacy ISL version of this dereferenced `irq_pin`
  unconditionally and crashed when it was `None`. Requirement 5 makes the pin mandatory, so the
  bug cannot recur; this function does not touch the pin at all.
- **Handling**: none needed — the function has no failure path. Copying BMP3xx's version verbatim
  is the right move and the comment should say it is deliberate.
- **Downstream**: `LockedValue.get_value()` (never raises).
- **Upstream**: `system_service.py` via `get_task_starters()`.
- **Logging**: none (the read loop logs the trigger).
- **Done when**: a test asserts N ticks produce exactly `N // SampleInterv` read events, and that
  changing `SampleInterv` live takes effect on the next boundary without losing the count.

---

#### R17-R29 The thirteen `_push_<field>()` wrappers

One shape, thirteen instances, so one specification with a table rather than thirteen blocks.

- **Where**: `ISL29125_Reader`, registered in `__init__` as
  `self._push_callbacks[name_cfg(_VAL_X)] = self._push_x`.
- **Purpose**: the live-effect half of `_set_dict_cfg()` (Part C.5.2) — apply a newly persisted
  value to the running driver.
- **Functionality**: `if type(value) is not int: return False` (or `float`/`bool`), then delegate
  to the public setter and return its bool. `type(...) is not int` rather than `isinstance` is the
  existing form in all three drivers and is deliberate — `isinstance(True, int)` is `True` in
  Python, so a bool would slip through an `isinstance` check into an int field.
- **Failure modes**: wrong type; a value the schema accepted but the hardware or a cross-field
  rule rejects; an exception from the setter (impossible — setters never raise).
- **Handling**: return `False`, which makes `_set_dict_cfg()` mark the field `"Failed"` and run
  `_recover_failed_push()`. The one exception is `ISLResetCal` — see below.
- **Downstream**: the public setters.
- **Upstream**: `base_classes.SensorReaderConfig._set_dict_cfg()`, which passes the **coerced**
  value, not the caller's raw one (`base_classes.py:329`), so no push wrapper needs to re-coerce.
- **Logging**: the setters log; the wrappers do not.

| Field | Push target | Live effect | `_get_callbacks`? | Notes |
|---|---|---|---|---|
| `SampleInterv` | `set_trigger_secs` | divider only | no | software knob, no read-back — BMP3xx's precedent |
| `Resolution` | `set_resolution` | `CONFIG1` B4 | **yes** | restarts the conversion; sets a settle deadline |
| `RangeAuto` | `set_range_auto` | arms/disarms the state machine | no | not a chip bit; on `False` it applies the stored `Range` |
| `Range` | `set_range` | `CONFIG1` B3 | **yes, conditional** | read-back suppressed while `RangeAuto` (R6) |
| `AutoRangeUp` | `set_autorange_up` | thresholds on next switch | no | cross-field checked |
| `AutoRangeDown` | `set_autorange_down` | thresholds on next switch | no | **cross-field: rejected unless `d ≤ u/53.33`** |
| `AutoRangeSettle` | `set_autorange_settle` | settle bound | no | |
| `AutoRangePersist` | `set_autorange_persist` | `CONFIG3` `PRST` | **yes** | chip-backed |
| `AutoRangeDwell` | `set_autorange_dwell` | dwell floor | no | |
| `IrCompOffset` | `set_ir_comp_offset` | `CONFIG2` B7 | **yes** | shifts the lux scale (§7.9) |
| `IrCompAdjust` | `set_ir_comp_adjust` | `CONFIG2` B5:0 | **yes** | as above |
| `FiltCoeff` | `set_filter_coefficient` | output EMA | no | `<= 0` disables |
| `ISLResetCal` | `reset_gain_calibration` | discards calibration | **no, by design** | see below |

**`ISLResetCal`'s four obligations** (Part C.5.2.1, listed in §8.3 and restated here as function
contracts because three of them are properties of *this* wrapper):

1. the schema entry is special-alone: `(("ISLResetCal", "bool", None, None, None, True),)`;
2. `get_dict_cfg()` is called with a **narrower** field list that excludes it, or
   `ConfigManager.get_dict()` raises `KeyError` on a key it never persisted;
3. **the wrapper returns `True` whenever the type check passes**, regardless of whether there was
   anything to discard — a recalibration that finds no stored ratio has not *failed*, and
   returning `False` would trigger `_recover_failed_push()` on a field that cannot be recovered.
   `reset_voc()` and SCD30's inverted `ContMeas` are the two existing instances of this trap;
4. no `_get_callbacks` entry: `_recover_failed_push()` skips command-only fields anyway
   (`base_classes.py:355`), so one would be dead code.

- **Done when**: every row has a test asserting push → hardware effect (byte-exact on the wire
  where there is one); the cross-field rejection has its own test in both directions; and
  `ISLResetCal` has the repeatable-trigger test — fire it twice in a row and assert `"Valid"`
  both times, which is the property obligation 3 protects.

---

#### R30-R42 The setters, R43-R47 the getters

- **Where**: `ISL29125_Reader`, public.
- **Purpose**: the "selected low-level driver forwards" layer both SCD30 and BMP3xx have — each
  one wraps a protocol call so that a transient bus fault on a REST-triggered set stays visible in
  the sensor's own error history rather than vanishing into a bare `False`.
- **Functionality**: `try: await self.isl.<op>(...) except Exception as e: await
  self.pr.err_s("<message>", e, errno=<n>); return False` / `return None` for a getter. Nothing
  else. Any validation that the schema cannot express (the cross-field rule; `int(value)` on a
  `float | int` union) happens here, before the call, with the same `(TypeError, ValueError,
  OverflowError)` catch `set_trigger_secs()` uses — and `OverflowError` is in that tuple because
  `int(float('inf'))` raises it rather than `ValueError` on MicroPython, which
  `asy_bmp3xx_driver.py:324` confirms was verified against the real interpreter.
- **Failure modes**: bus fault; invalid value; cross-field violation; `±inf`/NaN.
- **Handling**: as above; the errno per §2.
- **Downstream**: the protocol layer (may raise — wrapped).
- **Upstream**: the push wrappers, the webserver's PUT path via `_set_dict_cfg()`, and
  `_recover_failed_push()` for the five getters.
- **Logging**: one `errno` each, per §2's get/set pairs.
- **Done when**: each has a raise-injection test asserting `False`/`None` out and the right errno
  recorded; the five getters additionally have a test asserting that an out-of-schema value read
  back from a misbehaving chip is rejected by `_recover_failed_push()`'s own validation
  (`base_classes.py:371`) rather than persisted.

---

#### R48-R58 Registration, data access and the nested override

- **`start_asy_read()` / `start_asy_trigger()`**: `evtloop.create_task(...)`, verbatim from
  BMP3xx. Two tasks, matching the two-flag design in (a).
- **`start_timer()`**: `Timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda _b:
  self.base_trigger_event.set())` inside `try/except (OSError, MemoryError)` → `pr.err("Could not
  start timer:", e)` (alarm-pool exhaustion, Part F/Part I); **then** wire the pin IRQ:
  `self.irq_pin.irq(trigger=self.irq_pin.IRQ_FALLING, handler=lambda _b: self.read_event.set())`.
  Falling, not rising — the INT is active-low open-drain (p6). Soft IRQ (`hard=False`, the
  default); the handler allocates nothing, which is what makes that safe either way, and the
  project has no `hard=True` anywhere (C.9).
- **`stop_timer()`**: `self.trigger_timer.deinit()`. Note `Timer.deinit()` **is** real on rp2,
  unlike `I2C`/`SPI` `deinit()` (Part F.5.1).
- **`get_task_starters()` / `get_timer_starters()`**: the C.9 contract; two starters and one
  timer starter.
- **`get_data()`**: `await self._get_meas_data()` with the same `# type: ignore[return-value]`
  narrowing comment all three drivers carry.
- **`get_dict_data()`**: **the one genuine override** (§8.6, §14.4 rule 4). Builds the nested
  body explicitly rather than through `make_dict()`, because `_asdict()`/`_fields` are unavailable
  at rp2's ROM level (`config_manager.py`'s own comment). Declared return type widens to
  `dict[str, dict[str, Any]]`; `asy_webserver_service.py`'s `_ModuleLike.get_dict_data()` is
  already `-> dict[str, Any]`, so nothing upstream changes.
- **`get_dict_cfg()`**: `self._get_dict_cfg(_NAME, <schema minus ISLResetCal>,
  callback=self._read_sensor_dict)`.
- **`get_error_counter()`**: `await self.pr.get_log()`.
- **`get_mem_status()`**: returns `(gain_ratio, cal_ts)`; consumed by
  `sensortask_dev._isl_maintenance_status()`.

**Done when**: `get_dict_data()` has a test asserting the exact nested shape; a second asserting
`_stream_dict_response()` serialises it correctly and does not re-wrap it
(`tests/test_asy_webserver_service.py`, §11.7); and `get_dict_cfg()` has a test asserting
`ISLResetCal` is absent from the result and that its presence would have raised.

---

### 4.4 `ISL29125_DeviceSession` and `ISL29125_I2C` — the protocol layer

`ISL29125_DeviceSession(Lockable)` is **D1** and is three lines copied verbatim from Part C.2's
snippet — `__init__(self, i2c_device)` storing `self.i2c_device` after `super().__init__()`. It is
boilerplate, not a design surface, and every multi-transaction sequence below opens
`async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:` — device session first, bus second,
the fixed lock order Part C.8 audits (reversing it risks a real deadlock).

This layer **may raise**, and does: a read that returns `None` from layer 1 is converted into an
`OSError` here rather than propagated as a `None`, because the reader's `try` blocks are written
around exceptions and a silent `None` would reach the maths.

---

#### P1 `__init__(self, i2c, address=0x44)`

- **Purpose**: build the session and initialise the shadow.
- **Functionality**: `self.i2c_isl29125 = ISL29125_DeviceSession(I2CDevice(i2c, address))`; the
  three shadow field values set to their post-reset defaults (`CONFIG1 = 0x00`, `CONFIG2 = 0x00`,
  `CONFIG3 = 0x00` — Table 1 p9); `self._settle_until_ms = 0`. **No I/O** (requirement 20).
- **Failure modes**: none — `I2CDevice.__init__` only stores references and borrows the bus lock.
- **Handling**: n/a.
- **Downstream/Upstream**: `I2CDevice`; `ISL29125_Reader.__init__`.
- **Logging**: none — this layer has no logger, by design (`asy_i2c_driver.py`'s own row in Part
  C.7.1: every failure surfaces to exactly one upstream owner).
- **Done when**: a construction test asserts an empty wire log.
- **Address note**: `0x44` is hard-wired (p15, "1000100") — there is no address-select pin, so the
  parameter exists only for test injection, exactly as BMP3xx's does.

#### P2 `setup(self) -> None`

- **Purpose**: bring an unknown chip to a known, configured, converting state.
- **Functionality**, in order, with each step's justification:
  1. `await i2c.setup()` — layer 1's zero-byte ACK probe;
  2. `get_device_id()` → must be `0x7D` (p9 Table 2), else `RuntimeError` — the same shape as
     BMP3xx's `"Failed to find BMP3XX! Chip ID …"`;
  3. `reset()` (P3);
  4. `clear_brownout()` — `BOUTF` is high at power-up and must be written low (p12);
  5. `configure(mode=RED_GREEN_BLUE, int_select=GREEN, sync=0, conven=0, …)` — one burst setting
     all three config bytes. `SYNC` must stay 0 or the INT pin becomes an *input* and the whole
     interrupt path inverts (p6/p10 Table 7, §4); writing it explicitly rather than relying on the
     reset default is the point, so a later change cannot flip it silently.
- **Failure modes**: no ACK (`ValueError` from `_probe_for_device`); wrong/absent device ID; the
  reset not taking; a write failing mid-sequence leaving a half-configured chip.
- **Handling**: all of them raise, which is this layer's contract; `_init_isl()` catches with
  `errno=10`. Half-configured is safe because the next restart re-runs the whole sequence from the
  device ID, and every write is an absolute value.
- **Downstream**: P3, P11, P7, P13.
- **Upstream**: `_init_isl()` only.
- **Done when**: wire-log tests for the exact sequence; a wrong-ID test; a NAK test; and a test
  that `SYNC` and `CONVEN` are both 0 in the byte actually written.

#### P3 `reset(self) -> None`

- **Purpose**: the datasheet's software reset.
- **Functionality**: write `0x46` to register `0x00` (p9 — the "write only" reset path), then
  verify `CONFIG1`/`CONFIG2`/`CONFIG3`/`STATUS` all read `0x00`, which is what SparkFun's own
  `reset()` does (§5.2) and is the only available confirmation that the command landed. Reset the
  shadow to the same zeros so shadow and chip agree.
- **Failure modes**: the write being ignored on a marginal bus; the read-back not clearing; a
  chip that ACKs but is not an ISL29125.
- **Handling**: raise `RuntimeError` if the four registers do not read zero. Note the datasheet
  does **not** specify a post-reset settle time (unlike BMP3xx's documented 2 ms) — so the verify
  read *is* the settle, and if it proves flaky on the bench a fixed delay is the fix, recorded
  here so it is a known gap rather than a surprise.
- **Downstream**: layer 1 `set_register_struct`/`get_register_struct`.
- **Upstream**: `setup()`.
- **Done when**: wire-log test of the write and the four verifies; a fake that refuses to clear
  produces the raise.

#### P4 `_read_byte(self, register) -> int`

- **Purpose**: the one-byte read every other method builds on.
- **Functionality**: `get_register_struct(register, "B")`, `None` → `raise OSError(...)`,
  non-`int` → `raise OSError(...)`.
- **Failure modes / Handling**: as stated — this function exists precisely so that layer 1's
  mixed `None`/raise contract is normalised in exactly one place.
- **Done when**: `None` and wrong-type returns both raise, with the register number in the
  message.

#### P5 `_encode_shadow(self) -> bytes`

- **Purpose**: pure — turn the stored field values into the three config bytes.
- **Functionality**: `CONFIG1` = mode (B2:0) | `RNG` (B3) | `BITS` (B4) | `SYNC` (B5, always 0);
  `CONFIG2` = `IrCompOffset` (B7) | `IrCompAdjust` (B5:0); `CONFIG3` = `INTSEL` (B1:0) | `PRST`
  (B3:2) | `CONVEN` (B4, always 0). Every field masked to its width before shifting.
- **Failure modes**: an out-of-range field value corrupting a neighbouring bit — the exact hazard
  layer 1's own `set_bits()` guards against by masking, copied here.
- **Handling**: mask, never validate-and-raise: validation belongs at the setter boundary, and a
  pure encoder that can raise would make `configure()`'s failure modes ambiguous.
- **Done when**: a table test of field combinations → expected bytes, including every reserved
  bit asserted zero, and a test that an over-wide field cannot disturb its neighbour.

#### P6 `_write_shadow(self, first_register) -> None` · P7 `configure(self, **fields) -> None`

- **Purpose**: §8.7's single write path.
- **Functionality**: `configure()` updates the named shadow fields, calls `_encode_shadow()`,
  decides the **minimal burst**: if `CONFIG1`'s byte changed, write all three from `0x01`
  (`set_register_struct(0x01, "3s", bytes((c1, c2, c3)))`); if only `CONFIG2`/`CONFIG3` changed,
  write two from `0x02`, which avoids restarting the conversion for an IR-compensation change;
  if nothing changed, write nothing. When `CONFIG1` **was** written, set
  `self._settle_until_ms = ticks_add(ticks_ms(), self.cycle_ms())`.
- **Why the deadline lives here**: any writer of `CONFIG1` restarts the conversion (Table 7), and
  there are three of them — the range switch, a resolution push, and the brownout recovery.
  Putting the deadline in the function that does the write makes it impossible for a caller to
  forget, and automatically refreshes it when a config push lands during a settle window. That is
  the correctness fix for the case R11 re-checks after waking.
- **Failure modes**: the burst write raising; `struct.pack` silently truncating (Part F — it does
  **not** raise on MicroPython, unlike CPython), which is why the value passed is already `bytes`
  of the exact length rather than an int; a partial burst (not possible — one I²C transaction).
- **Handling**: raise on a bus fault; the `bytes` form removes the truncation risk structurally.
- **Downstream**: layer 1 `set_register_struct`, which takes a single value but accepts `bytes`
  (`asy_i2c_driver.py:130-147`) — the `"3s"`/`"2s"` trick §8.7 identified.
- **Upstream**: `setup()`, `_switch_range()`, the resolution/IR/persist setters,
  `_recover_brownout()`.
- **Done when**: byte-exact wire-log tests for the three-byte, two-byte and no-op cases; a test
  that an IR-only change does **not** touch `0x01` and does **not** set a settle deadline; and a
  test that a `CONFIG1` change does both.

#### P8 `set_thresholds(self, low_counts, high_counts) -> None`

- **Purpose**: arm the auto-range hysteresis window.
- **Functionality**: one 4-byte burst at `0x04` — `struct.pack("<HH", low, high)` — covering
  `0x04`-`0x07` (Table 1 p9; note Table 14's row labels are wrong, §5 defect 3, and the addresses
  are what matter).
- **Failure modes**: a count outside `0-65535`; the bus write raising; byte-order confusion, which
  Table 14's mislabelling actively invites.
- **Handling**: clamp before packing (the caller's F4 already does, this is defence in depth);
  raise on a bus fault. Endianness is pinned by `"<HH"` and by a test with asymmetric values, so a
  swap cannot pass.
- **Done when**: a wire-log test with `low != high` and both bytes distinguishable
  (e.g. `0x1234`/`0xABCD`), proving low-byte-first at the lower address.

#### P9 `read_counts(self) -> tuple[int, int, int]`

- **Purpose**: §7.1 step 1 — one coherent burst, which is also the fix for §3.6.
- **Functionality**: `get_register_struct(0x09, "6s")` under one device-session lock, then F1.
  **Not `"<HHH"`** — `get_register_struct()` returns `unpacked[0]` only
  (`asy_i2c_driver.py:100`), so a three-value format silently discards red and blue. This is the
  single most likely implementation mistake in the whole driver and it fails silently, so the test
  for it is named after the trap.
- **Failure modes**: short read; `None`; bus raise; the triple straddling two conversion cycles
  (channels convert sequentially — the burst removes bus-side tearing, not conversion-side; §7.6
  states this plainly and it is a documented property, not a defect).
- **Handling**: `None`/short → `OSError`; bus raise propagates.
- **Done when**: a test asserting all three channels come back distinct and in G/R/B order, and a
  regression test named for the `"<HHH"` trap asserting the format string actually used is `"6s"`.

#### P10 `read_status(self) -> int` · P11 `clear_brownout(self) -> None`

- **Purpose**: read the flag byte; clear `BOUTF`.
- **Functionality**: `_read_byte(0x08)`; and a write to `0x08` with `BOUTF` low. **The read is
  destructive** — it clears `RGBTHF` and releases the INT pin (p11, §4) — so it happens exactly
  once per cycle, in `_read_isl()` step 3, and nothing else in the driver may read `0x08` "just to
  check". That is a hard invariant: a second reader would silently consume another module's
  interrupt state.
- **Failure modes**: the destructive read being called twice in a cycle (a code defect, not a
  runtime one); the `RO` marking in Table 15 suggesting the write is illegal (it is not — §5
  defect 2, and p12's own `BOUTF` text requires it).
- **Handling**: the invariant is enforced by a test that counts `0x08` reads per cycle, not by a
  runtime guard.
- **Done when**: that counting test exists, plus a twin-level test that reading the status really
  does release the fake's INT line.

#### P12 `get_config_snapshot(self) -> tuple[int, int, int, int, int]`

- **Purpose**: convention 11's single batched live read-back, and the only mechanism that can
  detect shadow-vs-chip divergence.
- **Functionality**: one 3-byte burst read at `0x01` under one device-session lock, decoded to
  `(resolution, range_fs, ir_offset, ir_adjust, persist)`.
- **Failure modes**: bus raise; `None`; a reserved/invalid encoding in a field (e.g. a mode that
  is not 5), which means the chip has lost its configuration.
- **Handling**: raise on the first two. On the third, **return the decoded values anyway** and let
  the reader compare — the divergence is information, and swallowing it here would hide exactly
  what this function is for. (The brownout path is the one that acts on it.)
- **Done when**: a test asserting one transaction, not three; a decode table test; and a
  divergence test where the fake's registers are changed behind the driver's back and the
  snapshot reports the chip's values, not the shadow's.

#### P13 `get_device_id(self) -> int` · P14 `time_to_settle_ms(self) -> int` · P15 `cycle_ms(self) -> int`

- `get_device_id()`: `_read_byte(0x00)`; used by `setup()` and by the bus-fault confirmation in
  `_read_isl()`.
- `time_to_settle_ms()`: `max(0, ticks_diff(self._settle_until_ms, ticks_ms()))` — `ticks_diff`,
  never subtraction (Part F).
- `cycle_ms()`: `303` at 16-bit (3 × 101 ms `tINT`, p3), `19` at 12-bit (3 × ~6.3 ms, **derived**
  — only the 16-bit figure is specified, §7.2; AN1910 would confirm, §13 q3). The derivation is a
  comment on the constant, not a hidden assumption.
- **Done when**: both resolutions return the documented values; a ticks-wrap test drives
  `ticks_ms()` past the wrap boundary and asserts `time_to_settle_ms()` stays sane.

---

### 4.5 `src/sensortask_dev.py` — wiring

#### S1 `_isl_maintenance_status() -> dict[str, Any]`

- **Where**: module level, beside `_sgp_maintenance_status()`.
- **Purpose**: feed `WebserverService(maintenance_sensors=…)`.
- **Functionality**: `assert isl_reader is not None`; `gain_ratio, cal_ts = await
  isl_reader.get_mem_status()`; `return {"GainRatio": gain_ratio, "CalTS": cal_ts}`. Three lines,
  the same three `_sgp_maintenance_status()` has.
- **Key names are not free**: `js/render.js`'s `groupValuesFrom()` flattens `/status`'s `sensors`
  object one level into `<Sensor>_<Field>`, so these become `ISL29125_GainRatio` and
  `ISL29125_CalTS`, and `html/definitions/dev.json` must name them exactly that (§11.1).
- **Failure modes**: called before `build_system()` (the `assert`, matching the file's existing
  style); `get_mem_status()` raising (it cannot — reader layer).
- **Logging**: none; the webserver logs a failed status source (`WEBSERVER errno=6`).
- **Done when**: `tests/test_sensortask_dev.py` asserts `set(body["sensors"].keys()) ==
  {"SGP40", "ISL29125"}` and that both keys appear in the flattened form.

#### S2 `build_system()` — the construction edit

- **Purpose**: construct and wire the reader.
- **Functionality**: one construction line plus six registrations (error sources ×2, level setters
  ×2, `sensors=`, `maintenance_sensors=`, the setup batch, task and timer starters).
- **The one non-obvious constraint, and it is a hard one.** The `AsyFramManager` is a bump
  allocator: **instantiation order is on-chip layout**. Chunks 1-7 are allocated today by
  `sysfunct`, `sgp_reader` (2 and 3), `bmp_reader`, `scd_reader`, `pixel` and `notify_service`, in
  that order. The ISL reader owns chunks **8 and 9**, so it must be constructed **after
  `notify_service.finalize()`** and before the `WebserverService(...)` call. Constructing it
  anywhere earlier shifts every later chunk's address, which on a dev board that has already run
  means every persisted error log and the VOC backup are silently reinterpreted at the wrong
  offset — CLAUDE.md's own warning about FRAM evidence, in its most damaging form. The comment in
  the file must say this, not just the section number.
- **Failure modes**: wrong construction position (above); passing `i2c0` instead of `i2c1` (the
  ISL is on i2c1 with SCD30 and SGP40, `dev_legacy/sensortask-dev.py:137`); forgetting
  `fram_ntp_callback=ntp.ntp_issynced`, which silently produces untimestamped calibration writes;
  omitting `await isl_reader.setup()` from the batch, which leaves `cfgmgr` invalid and every
  config read failing.
- **Handling**: all four are caught by tests, not by runtime guards — see §6.2's dev-file list.
- **Done when**: the five literal assertions §11.7 enumerates are updated **because the expected
  value moved**, and the new ones (i2c1, `irq_pin=6` with `PULL_UP`, two error sources, two level
  setters, nine chunks in the documented sub-order) exist.

#### S3 The four `_collect_*()` edits

One line each: `isl_reader` and `isl_reader.cfgmgr` into `_collect_error_sources()` and
`_collect_level_setters()`; `isl_reader.get_task_starters()` and `.get_timer_starters()` into the
other two. `_collect_error_sources()` is the one that moves the `/status` `errcount` count from 17
to 19 — asserted literally in the dev test and mirrored in `html/definitions/dev.json`'s
`modules[]` list, which is the only place the website learns the enumeration.

---

### 4.6 `digital_twin/_isl29125_chip.py` — the chip fake

Required, not optional (Part C.11 point 9), and in the same session as the promotion. Shape
follows `_scd30_chip.py` (which owns a pin) and `_bmp3xx_chip.py` (which is register-addressed) —
this fake needs both halves.

| # | Function | Contract |
|---|---|---|
| T1 | `__init__(random_source=None, int_pin=None, min_lux=…, max_lux=…, lux_step=…, gain_ratio=…, *, auto_refresh=True)` | `FaultInjector` as `self.fault`; the **per-instance gain ratio deliberately non-nominal** (e.g. 25.9) so §7.3's calibration has something real to learn; datasheet-sourced min/max, judgment-call `*_step` with the same comment `_scd30_chip.py` carries |
| T2 | `_produce_new_reading()` | random-walk the modelled illumination, apply the active range's gain and the 12-bit truncation, write the double-buffered G/R/B registers, set `RGBCF` |
| T3 | `_update_int()` | compare green against the armed thresholds; on a crossing set `RGBTHF` and `int_pin.simulate_edge(0)`; honour the `int_stuck_high` fault by updating the flag but **not** the pin |
| T4 | `handle_writeto(data)` | answer layer 1's zero-byte ACK probe — `_bmp3xx_chip.py:151`'s comment records what happens without it (an `AttributeError` on every boot) |
| T5 | `handle_writeto_mem(reg, data)` | `0x00 = 0x46` → full reset; `0x01` accepts 1-3 bytes (the burst) and **restarts the conversion**; `0x02`/`0x03`; `0x04`-`0x07` thresholds; `0x08` write clears `BOUTF` |
| T6 | `handle_readfrom_mem(reg, n)` | `0x00` → `0x7D`; `0x01`-`0x03` → the real stored bytes; `0x08` → the flag byte **and then clear `RGBTHF` + release the pin** (destructive, p11); `0x09`-`0x0E` → the 6-byte burst |
| T7 | `set_illumination(lux)` | the test seam the twin-tier sweep drives (§6.4) |
| T8 | `_start_timer()` | optional periodic refresh, matching `_scd30_chip.py`'s `auto_refresh` |
| T9 | `configure_fault(op)` | the `isl29125:int_stuck_high` mode requirement 17 needs — **nothing today provides it**, and without it requirement 17's periodic path is untestable at the tier that would catch a regression (§11.5) |

Two properties of the fake that are load-bearing and must be commented in it, because a later
reader will otherwise "fix" them:

- **`digital_twin/machine.py`'s `Pin` is a per-id registry singleton**, so the `Pin(6)` the fake
  holds and the `Pin(6)` the driver constructs are the same object. That is what makes
  `simulate_edge()` reach the driver's handler at all.
- **`CONFIG1`'s power-on value is `0x00` and `BOUTF` starts high**, so a freshly constructed fake
  is in the post-brownout state on purpose. A twin test that expects readings before the driver
  has configured the chip is asserting the wrong thing.

**T10, `digital_twin/machine.py::_wire_i2c_devices()`**: one line —
`0x44: Isl29125Chip(int_pin=Pin(6, mode=Pin.IN), random_source=_random_source)` in the **dev**
profile's `bus_id == 1` dict, beside `0x61`/`0x59`. Wozi's branch is untouched (requirement 18).

---

### 4.7 `js/` — the website functions

| # | Function | Change | Failure mode it must not have |
|---|---|---|---|
| W1 | `resolveFieldValue()` in `js/definitions.js` | walk an optional `path` array before the flat `key` lookup | a `path` that is present but does not resolve must yield `null` (→ `—`), never `undefined` leaking into `formatFieldValue()` as `"undefined"` |
| W2 | `validateDefinitions()` in `js/definitions.js` | accept and validate `path`: array of non-empty strings, only on `readonly` fields | silently accepting a malformed `path` and failing in the browser |
| W3 | `jitterInPlace()` in `js/mock-server.js` | recurse one level deeper than the two `jitterEachSensorGroup()` walks today | mangling or skipping the third level, which shows as a static nested value |
| W4 | `applySensorQuirksForGet()` in `js/mock-server.js` | omit `ISLResetCal` from GET readback, as it already does for `ContMeas`/`SGPResetVOC` | a command field echoing back a value and looking persisted |
| W5 | `formatFieldValue()` in `js/field-format.js` | **conditional on §13 q6** — honour an optional `decimals` hint instead of ending at `String(value)` | a hue rendered as `217.43859649122808` |

W1-W4 are required by requirement 11 and are not optional. W5 is requirement 19 and depends on a
decision that is not this document's to make; the recommendation stays option (b), because it
fixes all four sensors at once and leaves the drivers consistent with each other.

Per Part G's `src/`↔`js/` mirror obligation, each of these lands with its `tests_js/`
counterpart in the same commit (§6.6).

---

### 4.8 `tests_hardware/device_scripts/` — the four real-hardware entry points

Each is a standalone MicroPython script with an `async def _main()` and a final `asyncio.run(_main())`,
printing exactly one `RESULT: PASS …` / `RESULT: FAIL …` line — the shape
`scd30_real_irq_edge.py` establishes, which the flash-tier pytest wrappers parse.

| # | Script | Proves |
|---|---|---|
| H1 | `isl29125_plausibility_read.py` | one real reading inside datasheet-sourced bounds; lux > 0 under room light, RGB in 0-1, HSB coherent, CCT either `None` or inside the span |
| H2 | `isl29125_same_device_rw_concurrency.py` | a config write interleaved with a read cycle produces neither a torn triple nor a lost write — CLAUDE.md's standing four-tier rule |
| H3 | `isl29125_real_irq_edge.py` | a genuine falling edge on GP6 drives the read path faster than the periodic fallback; **and settles §13 questions 1 and 2** (does a `CONFIG1` write restart the cycle; does `PRST` count channels or cycles) by timing them directly |
| H4 | `isl29125_autorange_sweep.py` | §10's NeoPixel rig — continuity, hysteresis, settle, saturation fast path, H/S/CCT invariance, gain-ratio convergence |

H4 needs an opt-in gate of its own (a `pytest_addoption()` flag in `tests_hardware/conftest.py`
plus a `KNOWN_PERMANENT_SKIPS` entry in `scripts/_require_clean_hardware_run.sh`), because it
depends on physical geometry a normal bench run cannot assume — §11.9. All four need the project
owner's go-ahead **in the session that runs them**.

---

## 5. Reference layer

### 5.1 Register map → the function that owns it

Every register this driver touches, the datasheet location for it, and the **single** function
allowed to touch it. One owner per register is the property that makes the shadow model safe.

| Register | Name | Datasheet | Owner | Read | Write |
|---|---|---|---|---|---|
| `0x00` | Device ID / reset | p9, Table 2 | P13 / P3 | `get_device_id()` | `reset()` writes `0x46` |
| `0x01` | `CONFIG1` (mode B2:0, `RNG` B3, `BITS` B4, `SYNC` B5) | p10, Tables 4-7 | P7 | P12 snapshot only | `configure()` only |
| `0x02` | `CONFIG2` (`IrCompOffset` B7, `ALSCC` B5:0) | p10, Table 8 | P7 | P12 snapshot only | `configure()` only |
| `0x03` | `CONFIG3` (`INTSEL` B1:0, `PRST` B3:2, `CONVEN` B4) | p11, Tables 11-13 | P7 | P12 snapshot only | `configure()` only |
| `0x04`/`0x05` | Low threshold | p9 Table 1 (Table 14's labels are wrong — §5 defect 3) | P8 | never | `set_thresholds()` only |
| `0x06`/`0x07` | High threshold | as above | P8 | never | `set_thresholds()` only |
| `0x08` | Status (`RGBTHF` B0, `CONVENF` B1, `BOUTF` B2, `RGBCF` B5:4) | p12, Tables 15-19 | P10 / P11 | **exactly once per cycle, destructive** | `clear_brownout()` only |
| `0x09`-`0x0E` | Green, Red, Blue data (in that order) | p9 Table 1; p13 Table 20 mislabels rows | P9 | one 6-byte burst | never |

Registers deliberately **not** used, with the reason, so nobody adds them later without reading
why: `SYNC` (would invert the INT pin into an input, p6/p10); `CONVEN` (would mux conversion-done
onto the pin the thresholds need, §7.6); `RGBCF` (redundant — the data registers are
double-buffered, p13); `CONVENF` (same).

### 5.2 What the other implementations do, and where we deliberately differ

Four independent implementations were read. The table is the cross-check; the notes after it are
the places this driver knowingly departs.

| Behaviour | Legacy `python/IndividualDrivers/` | Upstream `jposada202020/MicroPython_ISL29125` | SparkFun Arduino lib | RIOT-OS `drivers/isl29125` | **This driver** |
|---|---|---|---|---|---|
| Data read | three separate 16-bit reads | per-channel | per-channel `read16()` | **one 6-byte burst** from `0x09` | one 6-byte burst |
| 12-bit handling | none | none | none | **`<< 4` (`resfactor`)** | `<< 4` (F2) |
| Counts → lux | none | none | none | **`range_FS / 65535.0`** | same, plus the learned gain (F3) |
| Threshold scaling | raw counts via API | raw counts | raw counts | `(uint16_t)(65535 / max_range)` — **truncates** | float scaling, rounded once (F4) |
| Identity check | `0x7D` | `0x7D` | `0x7D`, refuses on mismatch | — | `0x7D`, raises |
| Reset verify | none | none | **verifies `CONFIG1-3` + status read `0x00`** | — | same as SparkFun (P3) |
| `BOUTF` | cleared once at setup | — | — | — | **checked every cycle, re-applies config** (§9.3) |
| Auto-range | none | none | none | none | full state machine |
| CCT | none | none | none | none | McCamy (M4) |

Three departures worth stating outright:

1. **RIOT is the only prior art for the normalisation chain**, and this driver copies its shape
   (burst, `resfactor`, `luxfactor`) deliberately — independent confirmation from a production
   RTOS driver is worth more than agreeing with three libraries that all read per-channel.
2. **Nobody does auto-range or CCT.** Both are this driver's own, which is why §6's twin-tier
   tests carry more weight than usual: there is no reference implementation to differential-test
   against.
3. **RIOT's threshold truncation is a bug worth naming.** `65535 / 375` in integer arithmetic is
   174, not 174.76; the same expression pattern truncates 6.55 to 6 in the other direction. F4
   exists as a named function so this cannot recur here, and its test is named after it.

### 5.3 Documentation checked on the web this session, and what each settled

CLAUDE.md makes checking current MicroPython/Microdot documentation a standing requirement rather
than a one-off, and the plan's four unobtainable Renesas application notes are recorded in §13
q3. What was reachable this session:

| Source | What it settled | Consequence here |
|---|---|---|
| MicroPython **v1.29.0** `docs/library/asyncio.rst` (repo, since `docs.micropython.org` is blocked by the egress policy) | `ThreadSafeFlag` *"may only be waited on by a single task at a time"*; `wait()` *"returns immediately"* if already set; the flag is auto-reset on return | The two-flag/two-task design in §4.3(a), and the fact that an INT arriving mid-cycle **coalesces** into exactly one extra cycle instead of being lost |
| MicroPython **v1.29.0** `docs/library/machine.Pin.rst` | `IRQ_FALLING` exists; `hard=True` *"may not allocate memory"* and *"not all ports support"* it; `pull` accepts `PULL_UP` on an input | `Pin(6, mode=Pin.IN, pull=Pin.PULL_UP)` + `IRQ_FALLING`, soft IRQ, handler that only calls `flag.set()` |
| `RIOT-OS/RIOT` `drivers/isl29125/isl29125.c` | Burst read of 6 bytes from the green low byte; `resfactor` shift; `luxfactor = range_FS / 65535.0`; the integer-truncated threshold scaling | §5.2's row-by-row comparison; F2/F3/F4 |
| `sparkfun/SparkFun_ISL29125_Breakout_Arduino_Library` | Reset writes `0x46` to the device-ID register and then **verifies `CONFIG1-3` and status all read `0x00`**; init refuses on an ID mismatch | P3's verify step — the only available confirmation the reset landed, since the datasheet specifies no post-reset settle time |
| `colour-science/colour` `temperature/mccamy1992.py` | Implements `n = (x − 0.3320) / (y − 0.1858)` with **`CCT = −449n³ + 3525n² − 6823.3n + 5520.33`** | **The two published forms are algebraically identical**, not contradictory: flipping the denominator's sign flips `n`, which flips the sign of the odd-power terms. §7.11's all-positive form with `(0.1858 − y)` and this one give the same answer. M4 keeps §7.11's form and gets a test asserting both agree — precisely so a future reader does not "correct" one into the other and change nothing but the reviewer's confidence |
| IEC 61966-2-1 sRGB matrix, via the W3C CSS Color 4 discussion of it | The widely copied `0.4124564 / 0.3575761 / 0.1804375 …` rounding and the more precisely derived `0.41239080 / 0.35758434 / 0.18048079 …` **differ in the 6th decimal**, and the CSS WG corrected its own published matrices over exactly this | M2 pins whichever set is chosen as **literal constants with a source comment**, and its test asserts the literals — because a test that recomputes the matrix from primaries would pass against either |
| `adafruit/Adafruit_CircuitPython_TCS34725` | A comparable colour sensor computes CCT as `3810 × (B/R) + 1391` (AMS DN40), not via chromaticity | Recorded as the alternative approach and **not** adopted: it is fitted to that part's own filters, so it would be no more calibrated here than McCamy and considerably less defensible |

One negative result worth recording so it is not re-attempted: `docs.micropython.org`,
`en.wikipedia.org` and `brucelindbloom.com` are all blocked by this session's egress policy. The
MicroPython facts above came from the pinned tag's own `docs/` in the repository, which is the
better source anyway; the colour-science constants came from a published implementation rather
than from the primary standard, and that limitation is stated in M2's own entry.

### 5.4 Platform facts this driver depends on (`SPECIFICATION.md` Part F)

Read before writing, not recalled:

| Fact | Where it bites |
|---|---|
| `struct.pack()` **silently truncates** on MicroPython instead of raising | P7 passes `bytes` of exact length, never an int for a multi-byte format |
| `int(float('inf'))` raises `OverflowError`, not `ValueError` | every setter's catch tuple is `(TypeError, ValueError, OverflowError)` |
| `time.ticks_ms()` wraps; only `ticks_diff()`/`ticks_add()` are valid | R9's dwell, R11's settle, P14 |
| `machine.I2C.deinit()` is a **silent no-op** on rp2 even in 1.29 | nothing in this driver may rely on releasing a bus |
| `Timer.deinit()` **is** real | `stop_timer()` |
| `Timer.init()` can raise `OSError(ENOMEM)` on alarm-pool exhaustion | `start_timer()`'s `(OSError, MemoryError)` guard |
| `MemoryError` is not an `OSError` subclass | caught explicitly wherever `OSError` is |
| Soft timer/IRQ callbacks can be dropped under load | the periodic path is a *divider*, so a dropped tick delays a sample rather than losing the schedule; and requirement 17's periodic evaluation is what keeps a dropped INT from being permanent |
| `time.mktime(time.gmtime())` is only a true round trip under `TZ=UTC` on the Unix port | every test asserting a timestamp runs under `scripts/test.sh`, which exports it |
| `namedtuple._asdict()`/`_fields` are unavailable at rp2's ROM level | `get_dict_data()`'s nested body is written out explicitly |

---

## 6. Test specification — every tier

Six tiers apply to this driver. Part E fixes how the Python ones run (the real MicroPython Unix
port, `tests/microtest.py`, one process per file, mock only the raw bus transaction — E.4);
CLAUDE.md fixes that bus-hazard coverage spans four of them; Part C.11 point 9 makes the twin
mandatory.

| Tier | Runs | Gate | What it can prove |
|---|---|---|---|
| 1. Mock/unit | `scripts/test.sh`, every commit | CI `unit-tests` | logic, bit packing, error paths, byte-exact wire sequences |
| 2. Digital twin | `scripts/test.sh` + `run_dev_integration.py` | CI `unit-tests` / `digital-twin-e2e` | the real object graph against a stateful chip model — auto-range, interrupts, brownout |
| 3. Website | `npm test` | CI web tier | the nested rendering path and the PUT matrix |
| 4. Flash (real HW) | `tests_hardware/flash/` | owner go-ahead | the chip really answers, the IRQ really fires, timings |
| 5. Bench (real HW) | `tests_hardware/bench/` | owner go-ahead | the full HTTP stack, config push over the air, heap cost |
| 6. Manual (real HW) | `tests_hardware/manual/` | owner + a human | anything needing a physical reference or a judgement call |

### 6.1 Tier 1 — `tests/test_asy_isl29125_driver.py` (new, the largest single file)

Grouped by what they prove, with the function each covers. Names are the real test names, in the
file's `test_<what>_<expectation>()` style.

**Pure helpers (no bus at all)** — M1-M5, F1-F5:
- `test_rgb_to_hsb_covers_all_six_hue_sectors()`, `…_returns_zero_hue_for_grey()`,
  `…_rejects_out_of_range_and_nan()`
- `test_rgb_to_xyz_reproduces_the_matrix_columns_for_pure_primaries()`,
  `test_rgb_to_xyz_coefficients_are_the_pinned_literals()` (§5.3's two-roundings trap)
- `test_chromaticity_xy_returns_none_at_zero_sum()`, `…_matches_d65_for_a_known_vector()`
- `test_cct_mccamy_returns_none_at_the_epicentre()`, `…_rejects_outside_the_valid_span()`,
  `test_cct_mccamy_agrees_with_the_sign_flipped_published_form()`
- `test_ema_step_is_a_passthrough_when_disabled()`, `…_seeds_from_none()`,
  `…_never_stores_a_nan()`
- `test_decode_rgb_burst_returns_green_red_blue_in_register_order()`,
  `…_rejects_short_and_none()`
- `test_normalise_triple_shifts_only_at_12_bit()`,
  `test_normalise_triple_12_bit_maximum_is_65520_not_65535()` (the saturation trap)
- `test_counts_to_lux_matches_the_datasheet_lsb_figures()`
- `test_fraction_to_counts_does_not_truncate_like_the_riot_driver()`
- `test_is_bus_fault_pattern_needs_all_three_channels_and_a_reserved_bit()`

**Protocol layer against `tests/machine.py`** — P1-P15, byte-exact wire logs:
- `test_setup_sequence_is_id_reset_brownout_config()`, `…_raises_on_wrong_device_id()`,
  `…_writes_sync_and_conven_as_zero()`
- `test_read_counts_uses_a_six_byte_burst_not_three_halfwords()` (named for the `"<HHH"` trap)
- `test_configure_writes_three_bytes_only_when_config1_changed()`,
  `…_writes_two_bytes_from_0x02_for_an_ir_only_change()`, `…_sets_the_settle_deadline_only_on_a_config1_write()`
- `test_set_thresholds_is_one_four_byte_burst_little_endian()`
- `test_status_register_is_read_exactly_once_per_cycle()`
- `test_get_config_snapshot_is_one_transaction_and_reports_the_chip_not_the_shadow()`
- `test_every_protocol_read_raises_rather_than_returning_none()`

**Reader lifecycle** — R1-R3:
- `test_construction_performs_no_bus_transactions()` (**requirement 20**)
- `test_construction_survives_a_fram_manager_that_refuses_allocation()`
- `test_init_returns_false_and_logs_errno_10_when_the_chip_is_absent()` (+ 12, 13)
- `test_init_arms_the_thresholds_for_the_starting_range()`
- `test_read_loop_calls_error_check_exactly_once_per_cycle()`
- `test_read_loop_exits_after_max_module_error_consecutive_failures()`
- `test_no_exception_escapes_the_reader_layer()` — parametrised over every layer-2 entry point

**Read path and outputs** — R4-R7, R11:
- `test_read_returns_a_narrow_results_tuple_without_cct()` (**the `_error_check` trap, §4.3(c)**)
- `test_a_dark_room_never_increments_the_error_counter()` — the same trap, from the outside
- `test_store_produces_the_documented_nested_body()`
- `test_cct_is_none_below_the_low_light_floor_and_present_above_it()`
- `test_hue_and_saturation_are_invariant_across_a_resolution_change()` (§7.4)
- `test_output_filter_applies_only_when_filtcoeff_is_positive()`

**Auto-range** — R9, R10:
- `test_switch_up_on_saturation_without_waiting_for_persistence()`
- `test_switch_points_do_not_chatter_at_the_schema_defaults()` and `…_at_the_worst_legal_pair()`
- `test_switch_down_is_suppressed_inside_the_dwell_window()`
- `test_thresholds_are_written_before_the_range_bit()`
- `test_a_partial_switch_is_retried_on_the_next_cycle()`
- `test_no_sample_is_reported_during_the_settle_window()`
- `test_the_periodic_path_switches_range_when_the_interrupt_never_fires()` (**requirement 17**)
- `test_a_periodic_only_switch_warns_after_five_consecutive_occurrences()` (`wrnno=15`)

**Calibration** — R12-R15:
- `test_gain_ratio_round_trips_through_the_fram_chunk()`
- `test_a_corrupt_or_implausible_stored_ratio_falls_back_to_nominal_with_a_warning()`
- `test_reset_cal_clears_the_chunk_and_returns_valid_twice_in_a_row()` (C.5.2.1 obligation 3)
- `test_learning_is_skipped_during_settle_and_dwell()`

**Config surface** — R6, R17-R47:
- one push test per field (13), one setter failure-injection test per errno
- `test_autorange_down_is_rejected_when_it_violates_the_cross_field_constraint()`
- `test_range_readback_is_suppressed_while_autorange_is_on()`
- `test_get_dict_cfg_excludes_the_command_only_field()`
- `test_a_failed_push_recovers_through_the_getter_then_the_snapshot_then_the_default()`

**Brownout** — R8:
- `test_brownout_reapplies_the_whole_configuration_and_discards_one_cycle()`
- `test_repeated_brownout_warns_once_per_event_not_once_per_cycle()`
- `test_brownout_does_not_feed_the_leaky_bucket_beyond_its_own_lost_cycle()`

### 6.2 Tier 1 — the existing files that change

| File | Change |
|---|---|
| `tests/test_sensortask_dev.py` | The five literal assertions §11.7 enumerates (seven→nine chunks **and the test's own name and comment**, 17→19 errcount, `{"SGP40"}`→`{"SGP40","ISL29125"}`, three `assert_sensor_payload_not_self_wrapped()` sets), plus new assertions for `i2c1`, `irq_pin=6` with `PULL_UP`, two error sources, two level setters, the task/timer starters, and **the construction position** (chunks 8-9 last) |
| `tests/test_digital_twin_machine.py` | dispatch for `0x44` on dev `bus_id == 1` |
| `tests/test_asy_webserver_service.py` | a two-level measurement value serialises through `_stream_dict_response()` and is not re-wrapped |
| `tests/test_setter_microdot_integration.py` | the ISL through real Microdot routes, including the repeatable command-only trigger |
| `tests/test_bus_hazard_multi_device.py` | **mock-tier bus hazards** — same-device read-vs-write, cross-device interleaving with SCD30/SGP40 on i2c1, address/command sweep |
| `tests/test_sensortask_wozi.py`, `test_digital_twin_sensortask_integration.py`, `test_digital_twin_real_website_integration.py` | **non-targets** — their seven-chunk/three-sensor assertions must stay exactly as they are; the divergence is the point |

### 6.3 Tier 2 — `tests/test_digital_twin_isl29125.py` (new)

Deterministic unit tests of the fake in isolation, matching the three existing
`test_digital_twin_{sgp40,scd30,bmp3xx}.py`: register dispatch, the destructive `0x08` read
releasing the pin, `BOUTF` high at construction, the `CONFIG1 = 0x00` power-on state, the 12-bit
truncation, the per-instance non-nominal gain ratio, and the `int_stuck_high` fault suppressing
the edge while data keeps moving.

### 6.4 Tier 2 — integration, and the continuity test that matters most

`tests/test_digital_twin_run_dev_integration.py` already boots the whole real dev graph, so the
chip fake must exist and answer or that file stops passing — it is the twin tier's real gate here
(§11.5). Extend it with:

- **the continuity sweep**: drive `set_illumination()` up through the switch point and back down,
  assert reported lux is monotonic and has **no step at the transition beyond a stated
  tolerance**. This is the one test that proves §7.1's chain and §7.3's calibration together, and
  it is the CI-every-commit version of the NeoPixel rig;
- **hysteresis**: park the illumination at the switch point and assert the range does not
  oscillate over N cycles;
- **H/S/CCT invariance**: hold a colour ratio, sweep brightness across the switch, assert hue,
  saturation and CCT hold still (§7.4, §7.11);
- **requirement 17 end to end**: enable `isl29125:int_stuck_high` and assert the range still
  tracks, on the periodic path alone, and that `wrnno=15` appears;
- **gain-ratio convergence**: repeated sweeps move the learned ratio towards the fake's own
  non-nominal value; `ISLResetCal` returns it to nominal and it re-converges.

`tests/test_digital_twin_bus_hazard_concurrency.py` gains the ISL in its "every sensor still
produced real data under concurrent load" assertions. `scripts/_digital_twin_ci_suite.py` stays
**wozi-only** — §13 q8, recorded in BACKLOG.md rather than closed here.

### 6.5 Tier 3 — `tests_js/`

| File | Case |
|---|---|
| `definitions.test.js` | `path` resolution; validation of a malformed `path`; **plus the gap §11.8 found — run `validateDefinitions()` against `html/definitions/dev.json`, which nothing does today** |
| `templates.test.js` | a nested readonly field renders its value, not `[object Object]` |
| `render.test.js` | change-comparison for `path`-bearing fields; `ISLResetCal` always resubmitted (`dispatch`) |
| `mock-server.test.js` | deeper jitter; `ISLResetCal` omitted from GET |
| `mock-server-put-matrix.test.js` | **automatic, not optional** — it already iterates every writable field in both shipped devices, so the skip logic must stop treating dev as a duplicate of wozi and `mockdata/dev.json` must carry a valid current value for every ISL field |

### 6.6 Tier 4 — flash (real hardware, dev bench, owner go-ahead)

| Where | What |
|---|---|
| `tests_hardware/bus_topology.py` | `DEV_TOPOLOGY` `port_id=1` gains `I2CDeviceSpec("ISL29125", 0x44)`; `KNOWN_ADDRESSES` gains `0x44` — two lines, and the autodetect sweep picks it up |
| `flash/test_sensor_accuracy.py` | registers H1 (plausibility) and, behind its flag, H4 (sweep) |
| `flash/test_bus_concurrency.py` | registers H2 and the cross-device pairing with SCD30/SGP40 |
| H3 via its own flash entry | the real IRQ edge, **and the two datasheet questions §13 q1/q2 leaves open** |

Two real-hardware constraints apply and are not negotiable (Part C.8's standing rule): a
concurrency test exercising persisted config constructs the **protocol layer** directly, never the
`*_Reader`, so it cannot touch the RP2040's flash filesystem; and the ISL has no on-chip NVM at
all (§9.1 — the config registers are volatile), so the "at most one real write per group" budget
does not bind here. That is a genuine simplification worth stating: this is the first promoted
sensor whose configuration costs nothing to rewrite.

**Before any of this runs**, CLAUDE.md's FRAM rule applies in its sharpest form: an
isolated-driver device script builds its own `AsyFramManager` over the same chip, and the
allocator is deterministic, so its first chunk **is** production's first chunk. Read the
FRAM-persisted error logs before running these scripts, and treat any log found afterwards as
suspect unless you know what has been run against that board.

### 6.7 Tier 5 — bench (real hardware, full HTTP stack, owner go-ahead)

| File | What |
|---|---|
| `bench/test_rest_endpoints_over_sta.py` | the `ISL29125` group appears in `/measurements`, `/sensors` and `/status`, in the nested shape |
| `bench/test_sensor_config_push_over_real_hardware.py` | a real `PUT /sensors` changes resolution/IR compensation and the read-back snapshot follows |
| `bench/test_bus_concurrency_under_api_load.py` | the ISL under concurrent HTTP load on i2c1 alongside SCD30/SGP40 |
| `bench/test_memory_stress_bench.py` | the extra module's heap cost counted (Part I) |
| `tests_hardware/device_scripts/reboot_persist_*.py` | the gain-ratio chunk survives a real reboot with its timestamp |

### 6.8 Tier 6 — manual

`tests_hardware/manual/manual_sensor_accuracy.py` gains an ISL entry for the half of the NeoPixel
work that needs a human: absolute-ish lux against a reference meter, and the geometry check.
§10 is explicit that absolute lux and CCT against a WS2812 are **meaningless** — three narrow LED
lines are not an illuminant — so what this tier records is a documented setup and a repeatability
figure, not an accuracy claim.

### 6.9 Coverage matrix — function against tier

`●` = covered directly, `○` = exercised indirectly, `—` = not applicable at that tier.

| Function group | 1 mock | 2 twin | 3 web | 4 flash | 5 bench | 6 manual |
|---|---|---|---|---|---|---|
| M1-M5 colour/EMA maths | ● | ○ | — | ○ | ○ | ○ |
| F1-F5 pure driver helpers | ● | ○ | — | ○ | ○ | — |
| R1 construction / req. 20 | ● | ● | — | ○ | ○ | — |
| R2-R3 init, read loop | ● | ● | — | ● | ● | — |
| R4-R5 read + derive | ● | ● | — | ● | ● | ● |
| R6 live config read-back | ● | ● | ○ | ● | ● | — |
| R7-R8 status, brownout | ● | ● | — | ○ | — | — |
| R9-R11 auto-range | ● | ● | — | ● | ○ | ● |
| R12-R15 calibration + FRAM | ● | ● | — | ● | ○ | ● |
| R16 trigger divider | ● | ● | — | ● | ○ | — |
| R17-R47 config surface | ● | ○ | ● | ○ | ● | — |
| R48-R58 registration/data | ● | ● | ● | ○ | ● | — |
| P1-P15 protocol layer | ● | ● | — | ● | ○ | — |
| S1-S3 dev wiring | ● | ● | — | ○ | ● | — |
| T1-T10 chip fake | ● | ● | — | — | — | — |
| W1-W5 website | — | — | ● | — | ○ | — |
| Bus hazards | ● | ● | — | ● | ● | — |

Two cells are worth reading twice. **R7-R8 (brownout) has no flash-tier coverage** — inducing a
real brownout on the bench means interfering with the supply, which is not something a test
script should do; the twin models it instead, and the flash tier only confirms `BOUTF` reads back
as expected after a power cycle. **W1-W5 has no mock-tier coverage** because it is JavaScript; the
Part G mirror obligation is what ties the two languages together, and it is satisfied by the
`tests_js/` column, not by a Python test.

---

## 7. What "complete" means

### 7.1 Per function — the generic bar

A function in this document is complete when all seven hold. They are the same seven for every
entry, which is why the per-function "Done when" lines only state the *specific* additions.

1. It does one thing, and its name says which.
2. Its contract matches its layer: the reader never raises, the protocol layer raises rather than
   returning a silent `None`, the pure helpers are total.
3. Every failure mode listed in its entry has a handling line, and every handling line has a test
   that reaches it.
4. Its logging matches §2/§3 — right level, right `errno`/`wrnno`, registered in Part C.7.1's
   table **before** the code was written.
5. `ruff` (`select = ["ALL"]`, project exceptions) and all three `mypy --strict` passes report
   zero findings on it, with no per-file ignore beyond the `FBT001` row the other three drivers
   carry, and no `# type: ignore[method-assign]` anywhere in `src/` (a `lint.sh` grep guard fails
   the gate on that one).
6. Its comments obey CLAUDE.md's 3-line header cap; anything longer moved into
   `SPECIFICATION.md`, `digital_twin/README.md` or `DEVICE_REFERENCE.md` with a pointer left
   behind.
7. Its datasheet-derived constants carry the page/table citation inline (convention 13).

### 7.2 Per file — the gates

| File | Gate |
|---|---|
| `src/math_helpers.py` | Part D.12's parameter/boundary/NaN-inf matrix on all five; Part G.2's catalogue carries the `ema_step()` row |
| `src/asy_isl29125_driver.py` | §14.2's nine acceptance items, all of Part D, and D.16 last — the file **moves into `src/` only once everything else passes**, it does not land first and get fixed after |
| `src/sensortask_dev.py` | the dev test file green, including the five moved literal assertions and the construction-position assertion |
| `digital_twin/_isl29125_chip.py` | `digital_twin/README.md`'s five-step "adding a chip fake" completed, including the README edits |
| `js/*` | `npm test` green, including the PUT matrix's newly generated dev cases and the dev definitions validation that did not exist before |
| `tests_hardware/*` | scripts written and registered; the opt-in flag and its `KNOWN_PERMANENT_SKIPS` entry exist so an expected skip does not read as a failure; **not run without the owner's go-ahead in that session** |
| Docs | Part A.4, the new dev construction-order section, C.7.1's row, C.8's device list, Part G's catalogue, Part H.5/H.6 (including the "nearly identical field content" sentence that stops being true), README's two places, `DEVICE_REFERENCE.md`, `THIRD_PARTY_LICENSES.md`, BACKLOG.md |

### 7.3 Ordering — what has to exist before what

Not a schedule, a dependency order. Several of these are only discoverable by getting them wrong.

1. **Part C.7.1's errno row and the `_VAL_*` schema** — before any code, because both are
   referenced by every function and renumbering later touches every test.
2. **`math_helpers.py`'s five functions and their tests** — pure, no dependencies, and they make
   the driver's own tests shorter.
3. **The chip fake** — before the driver's integration tests, and arguably before the driver:
   writing the fake forces every register interaction to be decided, which is most of the design.
4. **The protocol layer**, against the fake and against `tests/machine.py`.
5. **The reader**, in the order R1 → R2/R3 → R4/R5 → R7/R8 → R9-R11 → R12-R15 → the config
   surface. Auto-range before calibration, because calibration needs a working range switch.
6. **`sensortask_dev.py`** — and the moment this lands, `tests/test_sensortask_dev.py` and
   `tests/test_digital_twin_run_dev_integration.py` both go red until they are updated. That is
   expected and it is why the construction edit comes after the driver is green in isolation, not
   before.
7. **The website**, which can proceed in parallel with 4-6 since it only needs the agreed shapes.
8. **Real-hardware scripts**, last, and only with the go-ahead.
9. **The bird's-eye scan over all of `src/`** (CLAUDE.md), then the documentation, then D.16's
   move — with any discrepancy the scan surfaces **reported, not fixed**.

### 7.4 The definition of done for the whole promotion

Everything in §14.5, unchanged, plus the one line this document adds: **every function in §1's
inventory has an entry in §4 and at least one `●` in §6.9's matrix.** A function that appears in
the code but in neither is either undiscovered scope or dead code, and both are findings.

---

## 8. Questions this layer inherits, and the one it adds

§13's eight questions are unchanged and five of them still gate implementation. Their effect on
*this* document:

| § 13 | Effect on the function list |
|---|---|
| q1 `CONFIG1` restart | P7's settle deadline and R11 are conservative either way — this gates optimisation, not correctness. H3 settles it |
| q2 `PRST` units | changes `AutoRangePersist`'s effective time constant by 3×, nothing structural. H3 settles it |
| q3 missing app notes | P15's 12-bit cycle time stays derived; M2's matrix stays a documented placeholder |
| q4 keep the nesting | if "no", W1-W3 disappear and `get_dict_data()` stops being an override — the single largest structural swing in this document |
| q5 `mockdata/dev.json` orphans | no function effect |
| q6 output rounding | decides whether W5 exists, or whether `_store_isl()` gains a `_quantise()` seam. **Specified so it is one change either way**: the driver emits full precision today and the seam is a single call site |
| q7 `fram=` vs `fram_storage=` | one keyword in R1 |
| q8 twin CI suite dev leg | no function effect; §6.4 assumes "no" and records the asymmetry |

**And one new question, q9, raised by writing this down** (§4.5's box): `Range` is both a config
field and a measurement field, and under auto-range they routinely disagree — which is normal, not
an error. Recommendation: rename the measurement field to **`RangeAct`**. Every table here says
`Range` so the change is one substitution.

Two smaller things surfaced while writing and are decided here rather than raised, because
neither is a discrepancy between existing files — they are new-code choices with a clear better
answer, and both are recorded so a reviewer can disagree on the record:

- **`rgb_to_hsb()`/`rgb_to_xyz()` return tuples**, where every existing `math_helpers.py` function
  returns a single float. Reason: the components share one `max`/`min` and must be mutually
  consistent (§4.1).
- **`get_config_snapshot()` reads the chip rather than reporting the shadow** (§4.4 P12). Reason:
  it is the only mechanism that can detect shadow-vs-chip divergence, a read of `0x01` does not
  restart the conversion (only a write does, Table 7), and §8.7's rule is about the
  read-modify-write hazard, which a read-only snapshot does not create.
