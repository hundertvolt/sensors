# ISL29125 driver promotion — findings

Temporary working doc for the `python/IndividualDrivers/asy_isl29125_driver.py` → `src/`
promotion, following CLAUDE.md's step-session workflow. §1-§5 are the audit of the existing driver
against the real datasheet; §6 records the requirements the project owner has since settled, and
§7-§9 the design notes written against them. Nothing has been changed in the driver yet. Delete this
file once the promotion closes, migrating
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
- **Three independent implementations**, for cross-checking register semantics and design choices:
  `jposada202020/MicroPython_ISL29125` (our upstream), `sparkfun/ISL29125_Breakout`'s Arduino
  library, and **`RIOT-OS/RIOT`'s `drivers/isl29125/`** — unrelated lineages, which is precisely
  what makes them useful as second opinions. RIOT's is the most instructive: a production RTOS
  driver that already does the burst read, the 12-bit-to-16-bit shift and the range-to-lux scaling
  proposed in §7.1.
- **`tedyapo/arduino-VEML7700`**, as the reference implementation of Vishay's published auto-gain
  application note — the canonical treatment of this class of problem on a different sensor.

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

## 6. Settled requirements (project owner, this session)

These are decisions, not options. Everything below in §7 is designed against them.

1. **Every setting is API-settable and persisted.** No compile-time constants for anything a user
   might want to change.
2. **Resolution** — a plain value (12 or 16 bit). User's choice, not auto-managed.
3. **Range** — either a fixed value *or* `auto`. The **auto-range parameters are themselves
   API-settable**.
4. **Outputs** — **lux, RGB and HSB**, each *normalised over the full span*: over the fixed range
   when one is selected, over the whole auto-range span when auto is on.
5. **Interrupt** — used, with a **mandatory GPIO**, the same way `asy_scd30_driver.py` treats its
   RDY pin (`irq_pin: int` positional, `Pin(irq_pin, mode=Pin.IN)`, `ThreadSafeFlag`). Not optional,
   so §3.4's `None`-dereference disappears by construction rather than needing a guard.
6. **IR compensation** — an API parameter. The sensor is **openly exposed**: no IR-tinted cover.
7. **Register ownership is the driver's.** The sensor's hardware interrupts do not surface to the
   user at all; no interrupt-as-event notification is planned, and if one is ever added it is
   raised by software, not by exposing the INT pin or the threshold registers.
8. **RGB output is normalised 0-1.**
9. **HSB's low-light behaviour is accepted** — no log scaling, no validity flag needed.
10. **The API follows the same conventions as the other promoted drivers** (verified in §8.2).
11. **Measurement output is structured** — `RGB` and `HSB` are nested sub-objects, not flattened
    sibling keys.
12. **`OperationMode` is not exposed.** The driver sets and keeps `RED_GREEN_BLUE` itself.

Two consequences worth stating explicitly, because they change earlier reasoning in this doc:

- Since resolution stays user-selectable, the flicker finding (§7.2) is **documentation, not a
  design constraint** — the driver must let the user pick 12-bit and should say what it costs,
  not refuse it.
- Since the sensor is bare, the datasheet's p14 guidance ("not under IR tinted glass … b7 = '0'
  and B[5:0] … about 40 codes") is the applicable **default**, not p10's `0xBF`. `0xBF` remains
  reachable — it is just no longer the right default for this deployment.

## 7. Design notes against those requirements

### 7.1 The normalisation chain — the heart of "smooth and continuous"

Counts *must* jump 26.67× at a range switch; that is the gain changing, not a defect. Continuity
comes from never exposing counts. One chain, applied to every sample:

1. **Burst-read `0x09`-`0x0E` in one transaction** → coherent (green, red, blue), and §3.6 is fixed
   as a side effect. Register order is G, R, B.
2. **Resolution-normalise**: 12-bit values `<< 4` onto a common 0-65535 scale. Changing resolution
   then moves only the noise floor, never the reported magnitude.
3. **Dark-offset subtract** (`DDark` 1-5 counts, p3; only material on range 0 / 16-bit).
4. **Range-normalise to absolute** via `FS_lux / 65535` (`FS` = 375 or 10000) — using the
   **calibrated** gain ratio, not the nominal 26.67 (see §7.3). After this step every sample is on
   one absolute scale regardless of which range produced it.
5. **Derive the three outputs** from that absolute triple.

Steps 1, 2 and 4 are exactly what `RIOT-OS/RIOT`'s `drivers/isl29125/isl29125.c` does (burst read
of 6 bytes, `resfactor` shift for 12-bit, `luxfactor = range_FS / 65535.0`) — independent
confirmation, from a production RTOS driver, that this is the right shape.

### 7.2 Resolution is a flicker/speed trade, and must be labelled as one

16-bit integration is 101 ms = exactly 5 x 20 ms (50 Hz) = 6 x 16.67 ms (60 Hz), which is *why*
p6 says it "rejects 50Hz and 60Hz power line as well as florescent flicker noise", and p14's Noise
Rejection section states the integration time must be an integer multiple of the AC period. 12-bit
is ~6.3 ms (derived — only the 16-bit figure is specified; AN1910 would confirm) and is a multiple
of neither, so it forfeits flicker rejection under any mains-driven lighting. 12-bit buys ~16x
faster conversion. Both are legitimate; the API should make the trade visible rather than pick for
the user.

### 7.3 Gain-ratio calibration removes the residual step

26.67x is nominal. The real per-device ratio differs, and that error *is* the visible step at each
transition. Self-calibration is cheap: when the light sits in the overlap band, take one reading in
each range, compute the true ratio, low-pass it, persist it to FRAM. Without this, auto-range is
smooth-ish; with it, smooth.

### 7.4 Hue and saturation are continuous for free; brightness is not

All three channels share one `RNG` bit and one resolution, so any common scale factor cancels out of
the R:G:B ratios. **H and S are therefore invariant across range and resolution changes** — no
blending, no correction. Only **B** carries the magnitude and needs the §7.1 chain.

Two caveats:

- The invariance breaks near the dark floor, because the dark offset is *additive*: below some
  count floor the ratios distort and H/S should be reported as unreliable rather than as noise.
- **HSB from sensor RGB is "sensor HSB", not colorimetric HSB.** The ISL's R/G/B spectral responses
  (Figure 2) are not sRGB primaries; mapping to a device-independent space needs the 3x3 transform
  of Eq. 1, whose coefficients the datasheet says must be characterised per optomechanical design.
  Uncalibrated HSB is still perfectly useful for *relative* colour (shifts, trends, warm-vs-cool),
  and should be labelled as such rather than presented as a colorimetric measurement.

There is also a scaling choice for **B**: normalised 0-1 over the full auto-range span makes it
continuous but leaves a dim room reading ~0.003, i.e. almost no usable resolution. Reporting B in
lux, or on a log scale, keeps it legible. Open — see §8.

### 7.5 Lux without calibration coefficients

Eq. 2's `CYR`/`CYG`/`CYB` are explicitly system-specific. The defensible zeroth-order estimate is
**green-channel-based**, since the ISL's green response approximates the CIE Y curve (Figures 2 and
13) — which is also why green is the right channel to base range decisions on. RIOT applies the
same per-channel `luxfactor` to R, G and B, yielding "per-channel lux-equivalent" rather than true
photopic lux; that is the pragmatic uncalibrated approach and is worth copying, provided the
reported **lux** figure comes from green alone and the RGB triple is labelled lux-equivalent.

Note p3's calibration note 5: production test calibrates irradiance "to produce the same DATA count
against an illuminance level of 130 lux fluorescent light" — the anchor point for any later
correction.

### 7.6 Auto-range driven by the threshold interrupt

Set the high threshold at the switch-up point, the low threshold at the switch-down point,
`INTSEL` = green, `PRST` = 4 or 8. INT then fires exactly when a range change is needed, and the
persistence counter performs transient rejection **in hardware** — the anti-chatter mechanism that
would otherwise be software. Saturation (65535, clipped) forces an immediate switch-up without
waiting for any filter: react fast to bright, slowly to dark, so a camera flash does not drag the
range down for the next minute.

After every range change, **discard at least one full R-G-B cycle** (~303 ms at 16-bit) — the
conversion in flight when `RNG` flips is invalid. The datasheet specifies no settling time; this is
inference, and a real gap.

Thresholds should be **set in lux at the API and converted to counts internally** (RIOT does this,
though its `(uint16_t)(65535 / max_range)` integer division truncates 6.55 to 6 — a cautionary
example: do the scaling in float).

### 7.7 Register ownership, and a correction

With auto-range on, the driver **owns** `INTSEL` and both threshold registers. A user-facing
threshold alarm therefore cannot be served by the same hardware registers at the same time. The
clean resolution is that the user's alarm is expressed **in lux** and evaluated **in software** off
the normalised stream, which is the better API anyway — the user should not be writing raw counts.

**Correcting an earlier claim in this session**: the conflict between polling `CONVENF` for
conversion-done and using `RGBTHF` for threshold alarms is *not* a hard either/or. Both flags live
in the same byte `0x08` (Table 15: B0 `RGBTHF`, B1 `CONVENF`), so a **single status read
distinguishes which event fired**. `CONVEN` and `INTSEL` do mux onto one INT pin, but the status
byte disambiguates them.

One caution if `CONVEN` is used: the datasheet does not say whether conversion-done fires per
channel or per R-G-B cycle. Per channel at 12-bit that is up to ~160 interrupts/s, which is a real
load on a soft IRQ. Unspecified — verify on hardware before relying on it.

### 7.8 Reusable primitives

The first-order EMA used by the legacy SHTC3/MPRLS readers
(`tc = tc_old + FiltCoeff * (tc - tc_old)`, with `<= 0` meaning off) is the existing precedent for
output smoothing, currently inline in each driver rather than shared. `src/math_helpers.py` has no
filter primitive today, and `SPECIFICATION.md` Part G's catalogue lists none — so promoting this
one into a shared primitive is a Part G extension the auto-range work should make, not duplicate.
(BMP3xx's `FiltCoeff` is the *sensor's* on-chip IIR, not a software filter — different thing,
same name.)

## 8. Resulting API shape

### 8.1 What the settled requirements remove

"Register ownership is the driver's; the sensor's hardware interrupts are not user-visible" deletes
**five of the ten legacy config keys** outright — they become internal driver state:

`ISLInterruptAssignment`, `ISLInterruptHighThres`, `ISLInterruptLowThres`,
`ISLInterruptAutoClear`, `ISLPersistentControl`.

`INTSEL`, `PRST` and both threshold registers are how auto-range gets its hardware hysteresis
(§7.6), so they are the mechanism, not a setting. No user-facing event/notification is planned; if
one is ever wanted it is raised in software off the normalised stream, in lux, never by exposing
raw counts or the INT pin.

### 8.2 Convention check — verified, not assumed

"Compliant to the whole system as other drivers do" was checked directly against `src/`:

- Promoted drivers subclass **`SensorReaderConfig`** (`base_classes.py:244`), which supplies the
  data lock, logger, FRAM-backed error history and the `_get_dict_cfg`/`_set_dict_cfg` machinery.
- Config is a **`ConfigSchema`** tuple of `(name, type, default, min, max, special)` records
  (`config_manager.py:36-44`), assembled from one `_VAL_*` `const()` per field.
- **Discrete settings are `"int"` with an allowed-value tuple in the 6th slot**, not a min/max
  range — `_VAL_POV`/`_VAL_TOV`/`_VAL_FC` in `asy_bmp3xx_driver.py:78-80` are exactly this, and
  `asy_bmp3xx_driver.py:76` records that a plain min/max was the *old*, wrong shape here.
- `"bool"` fields are established (`AutoOn`, `SelfCal`, `LedWifiOn`).
- **No promoted driver has a single `"str"`-typed config field.** Verified by grep across every
  `src/asy_*_driver.py`.
- Live-effect fields register a `_push_callbacks[name_cfg(_VAL_X)]`; those with a hardware
  read-back also register a `_get_callbacks[...]` for `_set_dict_cfg`'s failed-push recovery chain
  (Part C.5.2). Software-only knobs (a timer divider) deliberately have no `_get_callbacks` entry.
- Field names carry **no device prefix** — `_NAME = "BMP3XX"` namespaces them, so the legacy
  `ISLSampleInterv` becomes `SampleInterv`.

**This closes §3.7 (the string-getter asymmetry) as a decision, not a question**: enumerated
settings are ints with allowed-value tuples, and the human-readable labels move to `js/`, which
Part G's cross-language mirror obligation requires anyway.

### 8.3 Proposed config schema

| Field | Type | Default | Allowed / range | Effect |
|---|---|---|---|---|
| `SampleInterv` | int | 1 | 1-3600 s | software timer divider |
| `Resolution` | int | 16 | {12, 16} | `CONFIG1` B4 |
| `RangeAuto` | bool | True | — | auto vs. fixed range |
| `Range` | int | 10000 | {375, 10000} | `CONFIG1` B3, used when `RangeAuto` is false |
| `AutoRangeUp` | float | 85.0 | 50.0-95.0 % FS | switch-up threshold |
| `AutoRangeDown` | float | 3.0 | 0.5-20.0 % FS | switch-down threshold |
| `AutoRangeSettle` | int | 1 | 1-10 cycles | conversions discarded after a switch |
| `IrCompOffset` | int | 0 | {0, 1} | `CONFIG2` B7 (adds 106) |
| `IrCompAdjust` | int | 40 | 0-63 | `CONFIG2` B5:0 |
| `FiltCoeff` | float | -1.0 | -1.0-1.0 | output EMA; <= 0 disables (legacy SHTC3/MPRLS precedent) |

IR compensation stays **two fields** rather than one: the effective scale is 0-63 and 106-169 with
a gap at 64-105, so no single contiguous range can express it honestly. `AutoRangeUp` must exceed
`AutoRangeDown` by more than the range ratio or the switch chatters — a cross-field constraint the
schema's per-field validation cannot express, so the driver has to enforce it.

### 8.4 Proposed measurement fields

`namedtuple("ISL29125", ("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "Range", "TS"))`

- `Lux` — absolute, green-channel-derived (§7.5).
- `Red`/`Green`/`Blue` — **normalised 0-1** over the full span: the fixed range when one is
  selected, the whole auto-range span when auto is on.
- `Hue`/`Sat`/`Bri` — `Bri` follows from RGB being 0-1, so it is 0-1 too. In a dim room that lands
  near 0.003; the project owner has accepted that behaviour, so no log scaling and no low-light
  validity flag.
- **Naming**: HSB's brightness must not be spelled `B` — it would collide with blue. `Red`/`Green`/
  `Blue` + `Hue`/`Sat`/`Bri` keeps both triples unambiguous.
- `Range` — the *active* range. It belongs in the measurement tuple rather than the config dict,
  because under auto-range it is an output, not a setting, and without it a consumer cannot tell
  which span the normalised values were taken against.

### 8.5 `OperationMode` is dropped — decided

Not exposed. Lux, RGB and HSB all need three channels, so anything but `RED_GREEN_BLUE` (`0b101`)
leaves every derived output undefined, and `POWERDOWN`/`STANDBY` produce no conversions while the
driver would keep reporting stale registers with a fresh timestamp (§3.8). The 56 µA -> 0.5 µA
saving buys nothing on a mains-powered node. The driver sets mode 5 at setup and **re-asserts it
whenever it finds the chip has lost it** (§9.3).

### 8.6 Nested output — cheaper than it looks

The current shared shape is exactly two levels: `make_dict()` (`config_manager.py:87`) turns a flat
namedtuple into `{TypeName: {field: value}}`, and every promoted driver annotates
`get_dict_data() -> dict[str, dict[str, int | float | str | bool | None]]`.

Three things make the nested form cheap rather than cross-cutting:

- **The webserver's own protocol is already wide enough.** `_ModuleLike.get_dict_data()` is
  declared `-> dict[str, Any]` (`asy_webserver_service.py:44`), so the consuming side needs no
  change at all.
- **The serialiser already handles it.** `_stream_dict_response()` does `json.dumps(v)` per
  top-level value (`asy_webserver_service.py:166`), so a nested value serialises correctly today.
  Part I's memory bound is unaffected: this module's response is a small fixed set of numbers, not
  something that grows with device configuration.
- **There is already precedent for nesting on the config side** — `_flatten_cfg_values()`
  (`asy_webserver_service.py:177`) exists precisely because `get_dict_cfg()` may return either
  shape.

So the ISL driver **overrides `get_dict_data()`** and builds the nested dict itself rather than
going through `make_dict()`, declaring the wider return type. No shared contract change, no other
module touched. Note `make_dict()`'s own comment records that `_asdict()`/`_fields` are unavailable
on rp2 (ROM level `EXTRA_FEATURES`, below the `EVERYTHING` they need), so the nested build is
written out explicitly rather than derived from the namedtuple.

Proposed response body:

```
{"ISL29125": {"Lux": <float>,
              "RGB": {"R": <0-1>, "G": <0-1>, "B": <0-1>},
              "HSB": {"H": <0-360>, "S": <0-1>, "B": <0-1>},
              "Range": <375|10000>,
              "TS": <epoch>}}
```

Nesting also dissolves the naming collision flagged in §8.4: `RGB.B` and `HSB.B` are unambiguous
once they sit in separate sub-objects, so both triples keep their conventional single-letter names.

## 9. The chip's write model — no wear, but no persistence either

### 9.1 Confirmed: config registers are volatile, rewriting them is free

The datasheet says it directly. Of the byte-write sequence (p7): *"The ISL29125 then begins an
internal write cycle of the data to the **volatile memory**."* There is no EEPROM, no NVM, no
write-endurance figure anywhere in FN8424 — because there is nothing non-volatile to wear out.
Rewriting `CONFIG1`/`CONFIG2`/`CONFIG3` is an SRAM-cell write, as often as wanted.

This is worth stating explicitly because **the same is not true of every sensor in this repo**:
`BACKLOG.md` records that `asy_scd30_driver.py`'s persistent NVM setters have no published
write-cycle endurance figure, and are safe today only because every one of them is REST-triggered
and never called from a boot path or a periodic loop. The ISL29125 carries no such constraint, so
auto-range is free to rewrite `RNG` as often as the light demands.

### 9.2 Three caveats, only one of which is the expected one

**a) Measurement glitches — the expected one, and real.** The ADC integrates continuously, so the
conversion in flight when a config bit changes is invalid. Discard at least one full R-G-B cycle
(~303 ms at 16-bit) after any write that changes `RNG`, `BITS` or the IR compensation. No settling
time is specified; this is inference (§7.6).

**b) `tWC` has a symbol but no value.** Figure 4 (p5) labels an I²C write-cycle time `tWC`, and p7
warns that *"during the internal write cycle, the device inputs are disabled and the SDA line is in
a high impedance state, so the device will not respond to any requests from the master."* But no
`tWC` figure appears in any spec table — checked p3 and p4. So a transaction issued immediately
after a write can legitimately NACK. The driver should treat an `OSError` in the window right after
a config write as a retryable condition, not as a bus fault that feeds the error counter. At 50 kHz
with the project's per-transaction locking this is unlikely to bite, but it is unbounded by
specification rather than known-safe.

**c) `CONFIG1` now has two writers.** Auto-range writes `RNG` (B3) continuously while an API call
can write `BITS` (B4) — same register, and every `_set_bits` is a read-modify-write. Each RMW is
individually lock-protected, but that does not help: auto-range can read `CONFIG1`, the user's
write can land, and auto-range can then write back its stale copy, silently losing the resolution
change. The legacy design never hit this because nothing wrote `CONFIG1` on its own. Fix: the
driver keeps a **shadow copy of `CONFIG1`** and writes whole bytes, or routes every `CONFIG1` write
through one owner. This is a consequence of adding auto-range, not a pre-existing defect.

### 9.3 The flip side of volatility: a brownout silently disables the sensor

Volatile means no wear, and it equally means **no persistence**. `Table 1` gives `CONFIG1` a
power-on default of `0x00` — and `0x00` in bits B2:0 is **Power-Down**. So after any brownout the
chip stops converting entirely, and a driver that keeps reading data registers would report the
last stale values, with a fresh timestamp, indefinitely.

The datasheet provides the detector: `BOUTF` (`0x08` B2), *"Power-down or Brownout occurred"*
(Table 18, p12), default HIGH at power-up and cleared by writing it LOW.

So the driver should **check `BOUTF` periodically, and on finding it set, re-apply the full
configuration** (mode, range, resolution, IR compensation, thresholds) and clear it again — the
same self-healing posture the existing 1 s interrupt self-heal already takes (§1.3). The legacy
driver clears `BOUTF` once at setup and never looks at it again, so a mid-life brownout would go
unnoticed.

This also folds in cleanly: the status register is already read on every interrupt, and `BOUTF`
sits in the same byte as `RGBTHF` and `CONVENF` (§7.7), so the check costs no extra transaction.

## 10. Known prerequisites and standing obligations

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
