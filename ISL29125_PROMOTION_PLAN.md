# ISL29125 driver promotion — findings

Temporary working doc for the `python/IndividualDrivers/asy_isl29125_driver.py` → `src/`
promotion, following CLAUDE.md's step-session workflow. This is **step 1 output only**: an audit of
the existing driver against the real datasheet. No implementation decisions are settled here, and
nothing has been changed in the driver. Delete this file once the promotion closes, migrating
anything permanent into `SPECIFICATION.md` (the established pattern — see README.md's "Further
reading" for the list of planning docs already retired that way).

## Sources this audit used

- **Datasheet**: `datasheets/isl29125/REN_isl29125_DST_20151201_1.pdf` — Renesas (ex-Intersil)
  FN8424 **Rev 3.00, Jan 13 2017**. Every register claim below cites a page/table from this PDF,
  read directly rather than reconstructed.
- **The driver itself**: `python/IndividualDrivers/asy_isl29125_driver.py` (570 lines).
- **Its bus layer**: `python/IndividualDrivers/asy_i2c_driver.py` (legacy `I2C`/`I2CDevice`) — and
  `src/asy_i2c_driver.py`, the promoted replacement it would move onto.
- **Its wiring**: `dev_legacy/sensortask-dev.py`, `html_raw/dev/sensorconfig.html`,
  `python/CommonDrivers/api_helpers.py`, `python/CommonDrivers/async_manager.py`.
- **MicroPython source at both relevant tags** (`v1.26.0` deployed, `v1.29.0` target), cloned and
  read for `int.to_bytes()`, `struct.pack()` and `Pin.irq()` semantics rather than relied on from
  memory, per CLAUDE.md's standing rule.
- **Two independent implementations**, for cross-checking register semantics only:
  `jposada202020/MicroPython_ISL29125` (our upstream) and `sparkfun/ISL29125_Breakout`'s Arduino
  library (unrelated lineage — the value of it is precisely that it is a second opinion).

Two things the datasheet does **not** contain, which stay open: the **12-bit integration time**
(only the 16-bit figure, 101 ms typ, is specified) and the **lux-conversion coefficients**
(`CYR`/`CYG`/`CYB` in Eq. 2 are described as system-dependent and must be characterised per
optomechanical design). Both are said to live in **AN1910** ("Enhancing RGB Sensitivity and
Conversion Time") and **AN1914**, which we do not have and which could not be fetched from a
session (see "Datasheet acquisition" below).

## 1. What the driver is, and the ideas inside it

Two layers, cleanly split, matching the shape every other reader in this repo uses.

### `ISL29125` (line 293) — the chip layer

A thin async register wrapper. Every accessor goes through one of four helpers (`_get_bits`,
`_set_bits`, `_get_reg`, `_set_reg`, lines 546-570), each of which takes the shared bus lock for
exactly one transaction via `async with self.i2c_device`. Setters validate against a tuple of
allowed constants and raise `ValueError` otherwise.

### `ISL29125_Reader` (line 64) — the task layer

This is the project's own code, with no upstream equivalent, and it carries the real design ideas:

1. **Timer-driven sampling with a software divider.** A single hardware `Timer` at a fixed 1000 ms
   period (line 112) sets a `ThreadSafeFlag`; `_base_trigger` (line 136) counts those ticks and
   only fires the real `trigger_event` every `ISLSampleInterv` seconds. So the sample interval is
   reconfigurable at runtime without touching the timer. Every other reader in the tree does the
   same, and `timer_sequencer()` in `sensortask-dev.py` staggers all the readers' timer starts
   across the base period so their callbacks don't pile onto one tick.
2. **A hardware-interrupt path, separate from the sampling path.** `Pin.irq(IRQ_FALLING)` → a
   second `ThreadSafeFlag` → `_interrupt_handler` (line 149), which reads the colours and hands
   them to a user callback. This is the only reader in the repo with a genuine
   threshold-alarm capability, and it is the most interesting thing in the file.
3. **Self-healing interrupt recovery.** `_base_trigger` (line 140) checks once per second whether
   the INT pin is asserted while no handler is waiting, and clears the flag if so. **This is a
   deliberate and correct compensation for a real platform hazard**: `Pin.irq()` on rp2 defaults to
   `hard=False` (verified in `ports/rp2/machine_pin.c:456-462` at v1.29.0), and a soft IRQ can be
   dropped when the scheduler queue is full — the same class of gotcha CLAUDE.md already records
   for soft `Timer` callbacks. Without this, one dropped edge would wedge the interrupt path
   permanently, because INT stays low until the flag register is read and therefore no further
   falling edge can ever occur. **Preserve this behaviour through the promotion.**
4. **A three-tier auto-clear policy** on `ISLInterruptAutoClear`: `-1` = never clear in the handler
   (leave it to the 1 s self-heal), `0` = clear immediately after the callback, `>0` = wait that
   many ms, then clear. The `>0` case sets `irq_waiting` so the self-heal doesn't race it.
5. **A leaky-bucket error counter** (lines 213-228): each failed read increments a local `err_cnt`,
   each good read decrements it, and exceeding `max_i2c_err` (5) returns from the coroutine —
   which the supervisor in `sensortask-dev.py` (line 780) treats as a task death, restarts, and
   escalates to a system reset if it keeps happening. A separate `TimeCounterManager` counts
   failures cumulatively for `GET /status`.
6. **Snapshot handoff** via `DataManager(4)` holding `[red, green, blue, timestamp]` under a lock,
   so the REST layer never reads a half-updated tuple.

## 2. Datasheet conformance — what is correct

Checked register by register. **All of the following are right**, and should survive the promotion
unchanged:

| Item | Driver | Datasheet | |
|---|---|---|---|
| I²C address | `0x44` (line 300) | "hard-wired as 1000100" (p15) = `0x44` | ✅ |
| Device ID | expects `0x7D` (line 306) | `0x7D`, RO (p9, Table 2) | ✅ |
| Reset | write `0x46` to `0x00` (line 313) | "Write 46h to register 0x00 in the WRITE ONLY" (p9) | ✅ |
| Operation mode | `_CONFIG1` B2:0, 8 values (line 358) | Table 4 (p10) | ✅ |
| Sensing range | `_CONFIG1` B3 (line 381) | `RNG`, Table 5 (p10) | ✅ |
| ADC resolution | `_CONFIG1` B4 (line 405) | `BITS`, Table 6 (p10) | ✅ |
| IR comp adjust | `_CONFIG2` B5:0, 0-63 (line 441) | `ALSCC[5:0]`, Table 8 (p10) | ✅ bits |
| Interrupt assignment | `_CONFIG3` B1:0 (line 466) | `INTSEL`, Table 11 (p11) | ✅ |
| Persist control | `_CONFIG3` B3:2 (line 541) | `PRST`, Table 12 (p11) | ✅ |
| Low threshold | `0x04`, 16-bit LE (line 499) | `0x04`/`0x05` low/high byte (Table 1) | ✅ |
| High threshold | `0x06`, 16-bit LE (line 483) | `0x06`/`0x07` low/high byte (Table 1) | ✅ |
| Colour registers | R=`0x0B`, G=`0x09`, B=`0x0D` (line 324) | Table 1 (p9) | ✅ |
| Interrupt flag | `0x08` B0 (line 504) | `RGBTHF`, Table 16 (p12) | ✅ |
| Brownout clear | write 0 to `0x08` B2 (line 310) | `BOUTF` defaults HIGH, "should be reset to LOW … by an I2C write command during the initial configuration" (p12) | ✅ |
| Flag clear by read | reads `0x08` (line 543) | "automatically cleared at the end of the 8-bit Device Register byte (0x08) transfer" (p11) | ✅ |

Also correct, and worth stating because they are easy to get wrong:

- **Endianness.** `set_register_struct` hardcodes `to_bytes(..., "little")` and
  `get_register_struct` uses `struct.unpack("H", ...)` (native = little-endian on rp2040). Both
  therefore put the low byte at the lower register address, which is what Table 1 specifies. The
  two arrive at the same answer by different routes, which is a latent portability trap but not a
  live bug.
- **Bit-field writes preserve neighbours.** Every `_set_bits` is a read-modify-write, so setting
  the operation mode does not clobber `RNG`/`BITS`/`SYNC` in the same register. In particular
  `SYNC` (`_CONFIG1` B5) is never written and stays 0 after reset, which is required — see §4.
- **Sample interval vs. conversion time.** In RGB 16-bit mode a full three-channel cycle costs
  ~3 × 101 ms ≈ 303 ms (`tINT`, p3). The minimum configurable interval is 1 s, so the driver never
  outruns the sensor.
- **Bus speed.** Both dev I²C buses run at 50 kHz; the part allows up to 500 kHz (p3, p4).

## 3. Confirmed defects

Ordered by how much they matter. None of these are speculative — each was traced to the line and,
where platform behaviour was involved, to MicroPython's own source.

### 3.1 `get_ir_compensation()` can never report "off" — type-confusion bug

`ISL29125_Reader.get_ir_compensation()` (line 262):

```python
IrComp = await self.isl.get_ir_compensation()
if IrComp == 0:
    return -1
return await self.isl.get_ir_compensation_value()
```

But `ISL29125.get_ir_compensation()` (line 411) returns a **string** — `values[ircomp]`, i.e.
`"IR_OFF"` or `"IR_ON"`. `"IR_OFF" == 0` is always `False`, so the `-1` branch is **dead code** and
the getter always returns the adjust value. The `-1` sentinel that the whole config schema is built
around is unreadable. This is a genuine bug, not a style issue, and it is invisible today only
because the dev UI shows the value as free text.

### 3.2 IR compensation B7 is mislabelled as an enable when it is an offset

`_CONFIG2` B7 is named `IR_OFF`/`IR_ON` in the driver (lines 46-47, 411-431). The datasheet (p10,
§Configuration-2, and Table 9 p11) is explicit:

> B7 is "IR Comp Offset" and B[5:0] is "IR Comp Adjust" … **B7 = '0' + B[5:0] is the effective IR
> compensation from 0 to 63 codes and B7 set to '1' + B[5:0] the effective IR compensation is from
> 106 to 169.**

Table 9 gives B7 a light-weight of **106**. It is an additive offset, not an enable. SparkFun name
the same bit `CFG2_IR_OFFSET_ON/OFF` — "selects upper or lower range of IR filtering" —
independently confirming the reading.

Two consequences:

- **The effective range 1-63 is unreachable through the API.** `ISL29125_Reader.set_ir_compensation`
  (line 254) maps *any* non-negative value to `B7=1`, so every in-range request lands in the
  106-169 band. Only the `-1` path produces `B7=0`, and it forces the adjust value to 0.
- **The deployed register value is nevertheless the right one.** The dev default
  `ISLIrCompensation: 63` programs `B7=1, B[5:0]=63` → register `0xBF` → effective 169. The
  datasheet's own recommendation (p10) is: *"Recommended to set BF at register 0x02 to max out IR
  compensation value. It make High range reach more than 10,000 lux."* So the field behaviour is
  correct and datasheet-endorsed; only the naming and the reachable range are wrong. Per CLAUDE.md's
  "verify against proven field behaviour" rule, **the promotion should preserve `0xBF` as the
  default register value** while fixing the semantics.

### 3.3 Threshold validation is off by one, and the failure mode is version-dependent

`set_high_threshold`/`set_low_threshold` (lines 484, 500) validate `0 <= value <= 65536`. The
thresholds are 16-bit (Table 1, high threshold default `0xFFFF`), so the maximum is **65535**.
`sensortask-dev.py` (lines 514, 516) repeats the same `65536` bound in the REST validation.

What happens on 65536 depends on which bus layer the driver sits on, and this matters for the
promotion because the two differ:

- **Legacy path** (`python/IndividualDrivers/asy_i2c_driver.py`): `set_register_struct` uses
  `value.to_bytes(size, "little")`. Verified in MicroPython source at **both** tags — v1.26.0
  (`py/objint.c`, `mp_raise_msg(&mp_type_OverflowError, "buffer too small")`) and v1.29.0
  (`py/objint_impl.h:41`, `"value would overflow a %d byte buffer"`) — this **raises
  `OverflowError`**. The REST layer's `set_sensor_value` (`api_helpers.py:199`) catches it with a
  bare `except:` and reports `"Failed"`, so it degrades gracefully rather than crashing.
- **Promoted path** (`src/asy_i2c_driver.py`): `set_register_struct` uses `struct.pack(reg_format,
  value)`. Verified in `py/binary.c:470-480` at v1.29.0, whose own comment reads *"overflow checks
  are disabled in this code path"* — it calls `mp_obj_int_get_truncated()` and **silently truncates
  to 0**.

So moving this driver onto `src/asy_i2c_driver.py` **converts a loud, caught failure into a silent
wrong write**: a threshold of 65536 would become 0, i.e. the minimum instead of the intended
maximum. The fix is the `65535` bound, but the divergence itself is worth recording — it applies to
every driver that migrates, not just this one.

*(This corrects a claim made earlier in this session's conversation, where the `struct.pack`
truncation was attributed to the legacy threshold setter. The legacy setter raises; only the
promoted bus layer truncates.)*

### 3.4 `_base_trigger` dereferences `irq_pin` unconditionally

Line 140: `if (self.irq_pin.value() == 0) and not self.irq_waiting:`. But `irq_pin` defaults to
`None` (line 65) and is only assigned a `Pin` when the caller passes one (lines 82-84). With no
interrupt pin, the very first timer tick raises `AttributeError`, killing the task; the supervisor
restarts it, it dies again, and after `_TASK_FAIL_MAX` the system reboots in a loop. Latent today
only because `sensortask-dev.py` always passes `irq_pin=6`. A promoted driver used without the IRQ
wiring would hit this immediately.

### 3.5 Startup is far less fault-tolerant than steady state

`read_isl29125` (line 164) returns `False` on *any single* startup problem — a failed `setup()`, a
failed config write, or an invalid config read — whereas the steady-state loop tolerates
`max_i2c_err` (5) consecutive failures. Because the supervisor restarts the coroutine and
`setup()` re-issues a **device reset**, one transient I²C glitch during boot costs a full sensor
reset, and a run of them reboots the node. The asymmetry looks unintentional.

### 3.6 The R/G/B triple is not a coherent snapshot

`get_colors()` (line 324) issues **three separate locked I²C transactions**. Each individual
16-bit read is safe — the datasheet states the registers are double buffered (p13), so no tearing
within a channel — but the ADC converts the three channels sequentially and "conversion continues
without stopping" (p6). A conversion boundary landing between two of the three reads yields a
triple mixed from two different cycles. With ~303 ms per cycle and ~1 ms of reads, this is
uncommon, not impossible.

The device supports burst reads with auto-incrementing addresses (p8, "BURST READ"), so
`0x09`-`0x0E` can be fetched in **one** transaction — giving a coherent snapshot *and* cutting
three bus round trips to one. Note the register order is G, R, B, so a single `"<HHH"` read unpacks
as `(green, red, blue)`.

### 3.7 Getter/setter type asymmetry across the config API

Every enumerated getter returns a **display string** (`"RED_GREEN_BLUE"`, `"LUX_10K"`,
`"RES_16BITS"`, `"IC1"`, …) while the matching setter takes an **int**. `GET /sensors/config`
therefore returns values that `PUT /sensors/cmd` will not accept.

This is *not* currently breaking the UI: `html_raw/dev/sensorconfig.html` renders these into
read-only `<span>` elements (line 171 etc.) beside a separate numeric `<input>`, so the string is
deliberately the human-readable form. But it does have real costs: `set_sensor_value`'s
read-back-on-failure fallback (`api_helpers.py:204`) cannot be wired for any of these fields, and
the round-trip symmetry that `SPECIFICATION.md` Part D.10 asks for does not hold. Whether to keep
strings, return ints, or return both is a design question for §6.

### 3.8 Smaller items

- **`get_high_threshold`'s docstring (line 472) describes the *low* threshold** — copied verbatim
  from the low-threshold docstring, including "If the ALS value crosses below or is equal to the
  lower threshold". Inherited from upstream. (The datasheet does the same thing on p12, which is
  probably where upstream got it.)
- **`_set_reg` assigns a return value that is always `None`** (line 568) — harmless dead code.
- **`set_bits` in the legacy bus layer does not mask `value`** before OR-ing it in, so an
  out-of-range value corrupts adjacent bits. Every ISL call site validates first, so it is guarded
  here — but `src/asy_i2c_driver.py` masks, so this hazard disappears on promotion anyway.
- **No validation on `set_trigger_secs` (line 124) or `set_irq_auto_clear` (line 118).** The REST
  layer bounds them (1-3600 and -1-3600000), but direct callers are unguarded. The auto-clear
  case is the sharper one: a large value makes `_interrupt_handler` sit in `asyncio.sleep_ms()` for
  up to an hour with `irq_waiting` set, which also suppresses the 1 s self-heal — interrupts are
  effectively dead for that period.
- **`STANDBY`/`POWERDOWN` modes are selectable but produce no conversions**, and the driver will
  keep reporting the last (now stale) register contents with a fresh timestamp. No guard, no
  annotation.

## 4. Datasheet facts the driver does not currently act on

Not bugs — capabilities and constraints that a promoted driver should at least decide about
explicitly.

- **`SYNC` (`_CONFIG1` B5) must stay 0.** When set, "the INT pin becomes an input pin" and a rising
  edge on it starts conversion (p6, p10, Table 7). The driver uses INT as an MCU **input**, so
  enabling SYNC would break the interrupt path entirely. It is 0 after reset and no code writes it,
  so this holds today by construction — but it is worth an explicit note (and arguably an explicit
  write) so a later change cannot silently flip it.
- **`CONVEN` (`_CONFIG3` B4) is not exposed.** Setting it makes INT assert on conversion-complete
  rather than on threshold crossing (Table 13, p11). That is an alternative, potentially better
  sampling strategy than the 1 s timer — read exactly when data is fresh — and it is the natural
  answer to §3.6 as well.
- **`CONVENF` (`0x08` B1) and `RGBCF` (`0x08` B5:4) are not exposed.** These report
  conversion-complete and which channel is currently converting (Tables 17, 19, p12). Either would
  let a reader avoid sampling across a conversion boundary.
- **Reading the flag register is destructive.** `get_interrupt_triggered()` (line 230) reads
  `0x08`, which per p11 clears both the status bit and the INT pin. So the "did it trigger?" query
  destroys the state it reports, and cannot be polled idempotently. Any test written against this
  needs to know that. (The same is true of `_set_bits` on `0x08` in `setup()`, whose
  read-modify-write performs a read of `0x08` as a side effect — benign there, since it immediately
  follows an explicit `clear_register_flag()`.)
- **`INTSEL = 00` disables the interrupt entirely**, and that is the dev default
  (`ISLInterruptAssignment: 0`). So the whole IRQ path is dormant on the bench rig as configured —
  worth knowing before writing hardware tests that expect an interrupt to fire.
- **INT is open-drain and needs an external pull-up.** The driver constructs
  `Pin(irq_pin, mode=Pin.IN)` (line 83) with no `PULL_UP`. The datasheet's reference circuit
  (Figures 1 and 15) shows R4 = 2.7 kΩ-10 kΩ pulling INT to VDD, so this is correct *provided* the
  dev board has that resistor. `dev_legacy/README.md` records the pin (GPIO6) but not the pull-up.
  **Unverified — flagging rather than assuming.** If it is absent, `Pin.PULL_UP` would be the fix.
- **Raw counts are exposed with no range/resolution annotation.** The REST payload
  (`sensortask-dev.py:306`) returns `Red`/`Green`/`Blue` as bare ADC counts. Those are not
  comparable across a `ISLSensingRange` or `ISLAdcResolution` change (375 lux vs 10 000 lux full
  scale; 16-bit vs 12-bit), and the datasheet's lux conversion (Eq. 2, p14) requires the range as a
  multiplier. A consumer of the API cannot currently interpret the numbers. Whether to add lux
  conversion, or simply to report the active range alongside the counts, is a design question.
- **Dark count is 1-5 counts typ** on range 0 (`DDark`, p3). No offset handling. Probably fine;
  noted for completeness.
- **The ISL29125 has never been bench-tested.** `dev_legacy/README.md`'s "Confirmed working" list
  (2026-08-28) covers Neopixel, SCD30, SGP40, BMP3xx, MPRLS, FRAM and the UART crossover — the
  ISL29125 is wired (I2C1, GPIO6) but absent from that list. Unlike the other promotions, there is
  no prior real-hardware evidence for this device to check new behaviour against.

## 5. Datasheet defects, so nobody re-chases them

FN8424 Rev 3.00 contradicts itself in four places. Recording them here because each one looks like
a code bug on first reading.

1. **Data registers are marked `RW`** in Table 1 (p9) and Table 20 (p13), but p13's own prose says
   "two 8-bit **read-only** registers". They are ADC outputs; `RW` is a typo.
2. **Status register `0x08` is marked `RO`** in Table 15 (p12), yet p12's own `BOUTF` text requires
   clearing it "by an I2C write command". The write is intended; the `RO` is the error. SparkFun's
   `reset()` corroborates the register reading back `0x00` after a software reset, which suggests
   the explicit brownout clear in our `setup()` is belt-and-braces rather than strictly required —
   harmless either way.
3. **The high-threshold rows in Table 14 (p12) are labelled `THL[...]`**, the same mnemonic as the
   low threshold. Table 1 gets it right (`THH`). Addresses are unambiguous; only the mnemonic is
   wrong.
4. **The interrupt-clear register is named inconsistently**: p11 says "the 8-bit Device Register
   byte **(0x08)** transfer", p12 says "the 8-bit **(00h)** command register transfer". p11 is the
   one consistent with the surrounding text, with SparkFun's implementation, and with our driver's
   observed field behaviour.

Also worth flagging: the p12 prose block introduced as covering *both* the lower (`0x04`/`0x05`)
and higher (`0x06`/`0x07`) interrupt registers only ever describes lower-threshold behaviour. This
is the origin of the docstring defect in §3.8.

## 6. Open questions for the project owner

Genuinely architectural, in rough order of how much they change the work:

1. **IR compensation API shape.** Keep the current single `ISLIrCompensation` key with a `-1`
   sentinel (fix the semantics internally, preserve `0xBF`), or split into an honest
   `ISLIrCompOffset` (0/1) + `ISLIrCompAdjust` (0-63)? The split makes the 1-63 band reachable and
   matches the datasheet, but changes the REST schema and the dev HTML, and needs a migration
   story for existing config files carrying `-1`.
2. **Getter return type** (§3.7). Strings are currently display-only and the UI depends on them.
   Options: keep strings, switch to ints and move the label mapping into `js/`, or return both.
   This is the one that most affects Part D.10 consistency across `src/`.
3. **Sampling strategy.** Keep the 1 s software-divided timer, or move to `CONVEN` +
   conversion-complete interrupts? The latter is more faithful to the device, fixes §3.6 for free,
   and would make this the first reader in the tree driven by the sensor rather than by a timer —
   which is also an argument against it, on consistency grounds.
4. **Lux conversion.** Report raw counts as now (but annotate the active range), or implement Eq. 2?
   Real conversion needs per-system `CYR`/`CYG`/`CYB` coefficients that the datasheet says must be
   characterised optically and which we do not have.
5. **Should the interrupt path be promoted at all?** It is dev-rig-only, dormant by default
   (`INTSEL = 00`), never bench-tested, and no wozi variant uses it. Promoting it means owning
   hardware test coverage for it; dropping it loses a genuinely interesting capability.

## 7. Known prerequisites and standing obligations

- `BACKLOG.md:519-522` already flags `asy_i2c_driver.py`'s `readfrom_mem()` → `readfrom_mem_into()`
  zero-copy change as *"worth doing before `asy_isl29125_driver.py` … is migrated"*, naming this
  driver as its one plausible future caller.
- The device shares **I2C1** with SCD30 and SGP40 on the dev rig, so CLAUDE.md's standing bus-hazard
  rule applies in full: coverage across all four tiers (mock, digital twin, flash, bench) per
  `SPECIFICATION.md` Part C.8.
- A **digital-twin chip fake** is required for any new sensor driver (`SPECIFICATION.md` Part C.11
  point 9, `digital_twin/README.md`). It will need to model the destructive flag-register read and
  the sequential conversion cycle to be useful for the interrupt path.
- **Licensing** is settled and needs no new work: upstream is
  `jposada202020/MicroPython_ISL29125`, MIT, © 2023 Jose D. Montoya, archived Dec 2024, and our
  file is a restructure. On promotion the `THIRD_PARTY_LICENSES.md` entry moves from "Shipped but
  not promoted" to "Restructured/rewritten, attribution retained". One **separate, pre-existing**
  question stays open there: upstream's `i2c_helpers.py` carries an explicit "Based on
  `adafruit_register.i2c_struct`/`i2c_bits`, © 2016 Adafruit Industries, MIT" notice, while
  `src/asy_i2c_driver.py` — which exposes the same four-operation API — carries no attribution at
  all. By the standard already applied to `asy_fram_driver.py` it may warrant a similar note.

## Datasheet acquisition

`renesas.com`, `intersil.com` and every mirror host (DigiKey, Mouser, AllDataSheet, Arrow, Farnell,
`web.archive.org`) are blocked by the session egress policy, and no reachable GitHub repository
vendors the PDF. The project owner supplied it directly. **AN1910 and AN1914 are still missing**
and would have to be supplied the same way — AN1910 in particular would settle the 12-bit
integration time, which the datasheet leaves unspecified.
