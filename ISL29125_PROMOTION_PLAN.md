# ISL29125 driver promotion — findings

Temporary working doc for the `python/IndividualDrivers/asy_isl29125_driver.py` → `src/`
promotion, following CLAUDE.md's step-session workflow. §1-§5 are the audit of the existing driver
against the real datasheet; §6 records the requirements the project owner has since settled, §7-§9
the design notes written against them, §10 the bench rig, §11 the full integration map, §12 the
prerequisites and standing obligations, §13 every question that was open and how it was
answered, and §14 the quality bar.

**Companion document**: [`ISL29125_FUNCTION_SPEC.md`](ISL29125_FUNCTION_SPEC.md) takes the
decisions below down to the level of individual functions — which function, in which file, its
purpose, expected behaviour, failure modes and handling, upstream/downstream contracts, logging
level and `errno`, and its completion criteria — with the datasheet/implementation/web reference
layer behind each choice and the test specification for all six tiers. Read this file for *what*
and *why*; read that one for *which function* and *how it is proven*.

Nothing has been changed in the driver yet. Delete this
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
- **A second full pass over the datasheet, plus a web re-scan of how others use this part**
  (2026-09-12), to check for capabilities the first pass missed. It found four: CCT as a specified
  output (§7.11), the conversion restart on a `CONFIG1` write (§4, §7.6), burst writes across the
  consecutive config registers (§8.7), and IR compensation's coupling to the full scale (§7.9). It
  also corrected the auto-range switch-point arithmetic (§7.6) and turned up the community
  all-channels-`0xFFFF` failure signature that the saturation fast-path has to survive.
- **A second pass over the integration surface** (2026-09-12): every file in the repo that names
  an existing sensor was enumerated and opened, and every claim already written in §11 was checked
  against the file it names. Six rows were wrong rather than merely incomplete, and two more
  requirements came out of it — §11's own "Second pass" preamble lists the corrections, §11.13
  cross-checks §6 against §11 in both directions, and §13's questions 6-8 are the discrepancies
  it surfaced between existing files.

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
  compensation value. It make High range reach more than 10,000 lux."* So the deployed value is
  datasheet-endorsed for what it was chosen for; only the naming and the reachable range are wrong.

**On whether to keep `0xBF` as the default — resolved, and the answer is no** (this supersedes an
earlier revision of this section, which argued for preserving it under CLAUDE.md's
"verify against proven field behaviour" rule). That rule protects *proven* field behaviour, and
there is none here: the ISL29125 has only ever run one config-and-read smoke test (§4), never a
measurement anyone checked. Two independent reasons now point the other way — see §6's consequences
and §7.9. `0xBF` stays reachable through the API and remains the right choice behind IR-tinted
glass or when >10 000 lux of headroom is wanted; it is simply not the right *default* for a bare
sensor whose lux output is scaled against the nominal 10 000 lux full scale.

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
  rather than on threshold crossing (Table 13, p11) — an alternative sampling strategy to the 1 s
  timer. **Decided against, see §7.6:** the sample interval is ≥ 1 s against a ≤ 303 ms cycle, the
  data registers are double buffered, and INT is wanted for the auto-range thresholds instead. The
  bit stays 0.
- **A write to `CONFIG1` restarts the conversion cycle.** Table 7 (p10) defines the `SYNC` = 0 case
  as *"ADC start at I²C write 0x01"*. So every `CONFIG1` write — including a read-modify-write that
  changes nothing — aborts the conversion in flight and starts a fresh one. Two consequences, both
  exploited in §7.6 and §8.7: the settle window after a range switch becomes **deterministic**
  rather than guessed, and the driver must never re-assert `CONFIG1` on a timer, because that would
  destroy every cycle it touches. *Strongly implied but terse — one table row, no supporting prose —
  so verify on the bench before depending on the restart for timing.*
- **`CONVENF` (`0x08` B1) and `RGBCF` (`0x08` B5:4) are not exposed.** These report
  conversion-complete and which channel is currently converting (Tables 17, 19, p12). Either would
  let a reader avoid sampling across a conversion boundary.
- **Reading the flag register is destructive.** `get_interrupt_triggered()` (line 230) reads
  `0x08`, which per p11 clears both the status bit and the INT pin. So the "did it trigger?" query
  destroys the state it reports, and cannot be polled idempotently. Any test written against this
  needs to know that. (The same is true of `_set_bits` on `0x08` in `setup()`, whose
  read-modify-write performs a read of `0x08` as a side effect — benign there, since it immediately
  follows an explicit `clear_register_flag()`.)
- **After an interrupt, the count that triggered it has a deadline.** p6: *"If the user needs to
  read the ADC count that triggers the interrupt, the reading should be done before the data
  registers are refreshed by the following conversions."* That is one conversion of that channel —
  ~101 ms at 16-bit. It bounds the acceptable latency of the soft (`hard=False`) IRQ path: past
  that, the interrupt still says *what* happened, but the sample that caused it is gone. Not fatal
  for auto-range, which only needs the direction, but it does mean the handler must not sit behind
  a long `await`.
- **`INTSEL = 00` disables the interrupt entirely**, and that is the dev default
  (`ISLInterruptAssignment: 0`). So the whole IRQ path is dormant on the bench rig as configured —
  worth knowing before writing hardware tests that expect an interrupt to fire.
- **INT is open-drain and needs a pull-up — and the driver should enable the internal one
  regardless.** See §7.12; the short version is that the chip has none, the SparkFun breakout has a
  hard-wired 10 kΩ, and `Pin.PULL_UP` is the right default either way.
- **Raw counts are exposed with no range/resolution annotation.** The REST payload
  (`sensortask-dev.py:306`) returns `Red`/`Green`/`Blue` as bare ADC counts. Those are not
  comparable across a `ISLSensingRange` or `ISLAdcResolution` change (375 lux vs 10 000 lux full
  scale; 16-bit vs 12-bit), and the datasheet's lux conversion (Eq. 2, p14) requires the range as a
  multiplier. A consumer of the API cannot currently interpret the numbers. Whether to add lux
  conversion, or simply to report the active range alongside the counts, is a design question.
- **Dark count is 1-5 counts typ** on range 0 (`DDark`, p3). No offset handling. Probably fine;
  noted for completeness.
- **The three channels do not share a full-scale irradiance.** p3 gives Range 0 full scale as
  Green = 18, Red = 20, Blue = 30 µW/cm² (at 565/620/485 nm). Equal counts therefore do **not** mean
  equal irradiance, and a broadband white source will not read R = G = B. Quantitative backing for
  §7.4's "sensor RGB, not colorimetric RGB" caveat — see §7.10 for why the driver should not try to
  correct it.
- **CCT is a specified output of this part, and nothing in the driver produces it.** p3 lists
  *Corrected Color Temperature Accuracy, ±5 %* as an electrical specification, and p15's references
  point at the Planckian locus and CIE 1931. This is the largest genuinely unexploited capability
  the audit found — see §7.11.
- **The ISL29125 has never been bench-tested.** `dev_legacy/README.md`'s "Confirmed working" list
  (2026-08-28) covers Neopixel, SCD30, SGP40, BMP3xx, MPRLS, FRAM and the UART crossover — the
  ISL29125 is wired (I2C1, GPIO6) but absent from that list, and the project owner has confirmed
  the device only ever ran a single config-and-read smoke test. So unlike every other promotion
  there is **no proven field behaviour** for this device to check new behaviour against — see §6
  for what that rules out.

## 5. Datasheet defects, so nobody re-chases them

FN8424 Rev 3.00 contradicts itself in six places. Recording them here because each one looks like
a code bug on first reading.

1. **Data registers are marked `RW`** in Table 1 (p9) and Table 20 (p13), but p13's own prose says
   "two 8-bit **read-only** registers". They are ADC outputs; `RW` is a typo.
2. **Status register `0x08` is marked `RO`** in Table 15 (p12), yet p12's own `BOUTF` text requires
   clearing it "by an I2C write command". The write is intended; the `RO` is the error. SparkFun's
   `reset()` corroborates the register reading back `0x00` after a software reset, which suggests
   the explicit brownout clear in our `setup()` is belt-and-braces rather than strictly required —
   harmless either way.
3. **Table 14 (p12) mislabels every threshold row.** The mnemonics are swapped — "Low Threshold -
   High byte" carries `THH[7:0]` and "High Threshold - Low byte" carries `THL[7:0]` — *and* every
   high-byte row is given bit indices `[7:0]` instead of `[15:8]`. Table 1 (p9) gets all of it
   right. Addresses are unambiguous, so nothing is actually in doubt; the table is just wrong.
   Table 20 (p13) has the same disease in the data registers: rows 13 and 14 are named "RED Data"
   while carrying `BLUE[...]` bits, and `BLUE[0]`/`BLUE[8]` are spelled `RED[0]`/`RED[8]`. Both
   tables also carry the caption "CONFIGURATION-3", copy-pasted from Table 10.
4. **The interrupt-clear register is named inconsistently**: p11 says "the 8-bit Device Register
   byte **(0x08)** transfer", p12 says "the 8-bit **(00h)** command register transfer". p11 is the
   one consistent with the surrounding text, with SparkFun's implementation, and with our driver's
   observed field behaviour.

5. **The power-up state is given three different ways.** p6's Power-On Reset section says the part
   *"will power up into Standby mode"*; p10's operating-mode section says *"The device powers up on
   a disable mode"*; and Table 1/Table 4 give `CONFIG1` a default of `0x00`, whose B2:0 = `000` is
   **Power-Down**, not Standby (`100`). Standby and Power-Down differ in supply current (29 µA vs
   0.5 µA, p3) but not in behaviour that matters here — neither converts — so §9.3's conclusion is
   unaffected. Do not read the prose as evidence that a reset device is in mode `100`.
6. **`0x08`'s `RGBCF` field is spelled `GRBCF` in the register map** (Table 1, p9) and `RGBCF`
   everywhere else (Table 15, Table 19, the p12 prose). Same field.

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
13. **`CCT` is part of the output.** Accepted as an addition to lux/RGB/HSB (§7.11), with the
    placeholder-matrix and low-light-floor caveats it carries.
14. **Auto-range is fully tunable through the API** — switch points, hardware transient rejection,
    settle margin, a software down-direction dwell, and a command to discard the learned gain
    ratio (§8.3). The learned ratio itself is calibration state, not a setting (§7.3).

**Four more, added by a completeness pass over this list** (asked for explicitly; each is a
behaviour the driver must have that none of 1-14 actually states, and the last one is a genuine
hole in the design rather than a restatement):

15. **Logging and error history follow the promoted-driver pattern in full** — a `PrintLog` per
    module plus one per its `ConfigManager` (`CFGMGR_ISL29125`), a FRAM-backed error history when
    a `fram=` is supplied and a plain in-RAM one when it is not, the `_error_check()` leaky bucket,
    and its own `errno`/`wrnno` range in Part C.7.1's table. Implied by 10, but it is the single
    largest block of shared machinery and worth naming.
16. **The driver is self-healing and never reports a stale value as fresh.** Concretely: `BOUTF`
    set means the chip lost its configuration, so re-apply the whole shadow and discard a cycle
    (§9.3); startup tolerates transient I²C failure on the same leaky-bucket terms as steady state
    (closing §3.5's asymmetry); and a sample the driver cannot prove is current is reported as
    `None`, never as the last reading with a new timestamp (§3.8).
17. **Auto-range must not depend on the interrupt alone.** *This one is a real gap, found while
    checking this list.* Every design note so far routes the range decision through the threshold
    INT. But if that line never asserts — a missing pull-up, a broken jumper, a mis-set `INTSEL` —
    auto-range simply freezes on whatever range it started on, silently, and the only symptom is
    saturated or near-zero readings that look like a sensor fault. The fix costs nothing: the
    driver already reads a full sample every `SampleInterv`, so it evaluates the same switch
    condition on that sample too. The interrupt becomes the *fast* path (sub-second reaction with
    hardware persistence) and the periodic read the *guaranteed* one. Both use the same thresholds,
    the same `AutoRangeDwell` and the same settle wait, so they cannot fight.
18. **Scope is the `dev` variant only.** `wozi` does not carry this sensor and is not to be
    changed — see §11's non-targets, which matters because most of the integration surface has a
    wozi twin of every dev file.

**Two more, added by the second completeness pass** (this one worked backwards — from the
integration surface in §11 to the requirements — which is why these were invisible the first
time round):

19. **Every emitted value carries a declared unit and a declared precision.** Found by following
    requirement 8 into the renderer: `js/field-format.js`'s `formatFieldValue()` ends in a bare
    `String(value)`, and **no driver in `src/` rounds any output** (one `round()` exists in all of
    `src/`, and it is an `asyncio.sleep()` argument). Today that is invisible because SCD30/BMP3xx
    emit one or two derived floats each. This driver emits eight, six of them normalised or
    angular, so a hue of `217.43859649122808` would go straight to the page. The *requirement* is
    that the precision is a decided, tested property of each field rather than an artefact of
    binary floating point. **Both halves are now settled**: the values are §8.4's
    units-and-precision table, and *where* the rounding happens was §13 question 6, decided by
    the project owner as option (b) — a `decimals` hint on the readonly field, honoured by
    `formatFieldValue()`. The driver rounds nothing, so all four drivers stay identical to each
    other.
20. **Construction and `setup()` must complete on a bus where the chip never answers.** Not a
    restatement of 16: 16 is about a chip that is present and misbehaving, this is about one that
    is absent for the whole run. It is not hypothetical — `tests/test_sensortask_dev.py` builds
    the entire dev object graph against `tests/machine.py`'s generic dict-of-registers fake, which
    has no ISL29125 registers in it, and `build_system()` has no per-sensor try/except. Every
    existing driver already satisfies this; it is stated because it is the one property that, if
    missed, breaks the whole dev test file rather than just the new one.

**What "satisfied" means for all twenty of these is §14**, which sets the quality bar: the written
standards each requirement has to clear, plus the fourteen conventions the three existing drivers
share that no document states — the ones a new file fails by omission rather than by
contradiction.

**One standing consequence, stated once because it recurs**: CLAUDE.md's rule to *"verify against
the legacy driver's own actually-proven field behaviour"* has **no purchase for this device**. The
ISL29125 has only ever run a single config-and-read smoke test (§4) — the project owner has
confirmed there is nothing to preserve on those grounds. So wherever this doc weighs "but the
deployed code does X", X is evidence of intent at most, never of proven behaviour. That is what
settled the IR default below, and it applies equally to naming, defaults and API shape: the
promoted driver follows the project's current conventions, not the legacy driver's.

Two further consequences worth stating explicitly, because they change earlier reasoning in this
doc:

- Since resolution stays user-selectable, the flicker finding (§7.2) is **documentation, not a
  design constraint** — the driver must let the user pick 12-bit and should say what it costs,
  not refuse it.
- Since the sensor is bare, the datasheet's p14 guidance ("not under IR tinted glass … b7 = '0'
  and B[5:0] … about 40 codes") is the applicable **default**, not p10's `0xBF`. `0xBF` remains
  reachable — it is just no longer the right default for this deployment. **A second, independent
  reason has since been found** (§7.9): IR compensation moves the *effective full scale*, and
  `0xBF` is the setting that pushes range 1 furthest past the nominal 10 000 lux the lux
  normalisation is scaled against. 40 codes keeps the scale closest to nominal. Both reasons point
  the same way, which closes the question — see §3.2 for the superseded argument.

## 7. Design notes against those requirements

### 7.1 The normalisation chain — the heart of "smooth and continuous"

Counts *must* jump 26.67× at a range switch; that is the gain changing, not a defect. Continuity
comes from never exposing counts. One chain, applied to every sample:

1. **Burst-read `0x09`-`0x0E` in one transaction** → coherent (green, red, blue), and §3.6 is fixed
   as a side effect. Register order is G, R, B. **Mechanically this needs care on the promoted bus
   layer**: `get_register_struct()` returns `unpacked[0]` only (`src/asy_i2c_driver.py:101`), so
   passing `"<HHH"` would silently discard red and blue. The working form is
   `get_register_struct(0x09, "6s")` — the return type union already includes `bytes` — with
   `struct.unpack("<HHH", ...)` done in the driver.
2. **Resolution-normalise**: 12-bit values `<< 4` onto a common 0-65535 scale. Changing resolution
   then moves only the noise floor, never the reported magnitude.
3. **Dark-offset subtract** (`DDark` 1-5 counts, p3; only material on range 0 / 16-bit).
4. **Range-normalise to absolute** via `FS_lux / 65535` (`FS` = 375 or 10000) — using the
   **calibrated** gain ratio, not the nominal 26.67 (see §7.3). After this step every sample is on
   one absolute scale regardless of which range produced it. **The datasheet confirms this exact
   mapping**, which is worth more than the RIOT cross-check: p1's feature list gives
   "Range 0 = 5.7m lux to 375 lux" and "Range 1 = 0.152 lux to 10,000 lux", and 375/65535 =
   5.72 mlux, 10000/65535 = 0.1526 lux. The LSB *is* FS/65535, linearly, on both ranges.
5. **Derive the three outputs** from that absolute triple.

Steps 1, 2 and 4 are exactly what `RIOT-OS/RIOT`'s `drivers/isl29125/isl29125.c` does (burst read
of 6 bytes, `resfactor` shift for 12-bit, `luxfactor = range_FS / 65535.0`) — independent
confirmation, from a production RTOS driver, that this is the right shape.

### 7.2 Resolution is a flicker/speed trade, and must be labelled as one

16-bit integration is 101 ms = exactly 5 x 20 ms (50 Hz) = 6 x 16.67 ms (60 Hz), which is *why*
p6 says it "rejects 50Hz and 60Hz power line as well as florescent flicker noise", and p14's Noise
Rejection section states the integration time must be an integer multiple of the AC period. 12-bit
is ~6.3 ms — derived, but on the datasheet's own terms rather than by analogy: p6 states the
integration time is set by *"an internal oscillator and the n-bit (n = 12, 16) counter inside the
ADC"*, so the specified 101 ms 16-bit figure scales by 2⁻⁴. It is a multiple
of neither, so it forfeits flicker rejection under any mains-driven lighting. 12-bit buys ~16x
faster conversion. Both are legitimate; the API should make the trade visible rather than pick for
the user.

### 7.3 Gain-ratio calibration removes the residual step

26.67x is nominal. The real per-device ratio differs, and that error *is* the visible step at each
transition. Self-calibration is cheap: when the light sits in the overlap band, take one reading in
each range, compute the true ratio, low-pass it, persist it to FRAM. Without this, auto-range is
smooth-ish; with it, smooth. It is the single most influential number for transition quality, so
it is worth doing properly rather than trusting the nominal figure.

**Where the learned value lives — the project already has a rule for this.** `SPECIFICATION.md`
Part C.5.2.1 defines the *command-only trigger field*, and `asy_sgp40_driver.py` is its worked
example: learned state goes into a timestamped FRAM chunk (`AsyFramChunkTimestampedBuffer`), the
*policy* around it is ordinary config fields (`BackupPeriod`, `BackupMaxAge`, `WaitTimeNTP`), and a
special-alone `"bool"` field wired through `_push_callbacks` discards it. Mapped across: the gain
ratio is one float in a FRAM chunk, not a config field, and **`ISLResetCal`** is the command-only
bool that throws it away and relearns from nominal. §8.3 spells out what conforming to C.5.2.1
actually obliges the driver to do.

Deliberately **no** on/off switch for the learning itself. The ratio is a device constant — it
converges and stays there — not an environmental adaptation that could wander, so "stop learning"
solves nothing that `ISLResetCal` does not.

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

There was also a scaling choice for **B**: normalised 0-1 over the full auto-range span makes it
continuous but leaves a dim room reading ~0.003, i.e. almost no usable resolution. **Settled** —
requirements 8 and 9: RGB is 0-1, `Bri` follows from that, and the low-light behaviour is accepted.
`Lux` is the field to read when magnitude matters; `Bri` is there for completeness of the HSB
triple, not as the brightness measurement.

**The denominator, spelled out, because it is the one number the whole continuity argument rests
on.** Requirement 4 says *"over the whole auto-range span when auto is on"*, and that is
**10 000 lux — the union of both ranges — not the range currently active**. The 0.003 above is
that arithmetic and nothing else: a 30 lux dim room over a 10 000 lux span. Dividing by the
*active* full scale instead would make `R`/`G`/`B`/`Bri` jump by the gain ratio (~26.67×) at every
switch, which is precisely the discontinuity §7.1 exists to remove — the values would be
continuous in `Lux` and stepped in every other field. With `RangeAuto` **false** the denominator
is the selected fixed range (375 or 10 000), because then there is no span to be continuous
across. One consequence worth stating: under auto-range the low range's own 0-375 lux window only
ever occupies the bottom 3.75 % of the normalised scale, by design.

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

`INTSEL` = green, `PRST` = `AutoRangePersist`. The chip fires INT whenever the green count leaves
the window `[low, high]`, and the persistence counter performs transient rejection **in hardware** —
the anti-chatter mechanism that would otherwise be software. Saturation forces an
immediate switch-up without waiting for any filter: react fast to bright, slowly to dark, so a
passing shadow does not cost a range change and a change back. The "slowly to dark" half is
`AutoRangeDwell`, because `PRST` cannot be made asymmetric — §8.3 has the reasoning.

**`PRST` counts RGB cycles, not channel integrations — resolved** (this was §13 question 2).
Table 12 (p11) calls its unit an *"integration cycle"* and p12's threshold text says the same, but
the ambiguity dissolves once `INTSEL` is taken into account: the threshold comparison is made
against **one** selected channel, and that channel converts exactly once per R-G-B cycle, so
"an 'X-consecutive' number of interrupt" (p11) can only accumulate at one per cycle. SparkFun's
own tutorial describes the same field as *"N consecutive readings above the threshold"*. So
`AutoRangePersist` = 4 is 4 × 303 ms ≈ 1.2 s at 16-bit and ≈ 76 ms at 12-bit. If a bench run ever
shows the other reading, the effect is that hardware rejection is **3× faster** than documented,
which is safe in the up direction and irrelevant in the down direction (`AutoRangeDwell` owns
that one) — so nothing in the design is conditional on this.

**Which channel decides, and what "saturated" means.** Two different things, and an earlier
revision ran them together:

- **The hardware fast path is green, and only green** — `INTSEL` has one channel and §8.3 declines
  to make it selectable, because green is both the photopic proxy and the basis of the reported
  lux.
- **The software decision is the maximum of the three channels** — proposed by the resolution
  pass and **confirmed by the project owner**. Requirement 17's periodic
  evaluation has all three counts in hand, and the output is a *colour* triple: a clipped red with
  green at 40 % of full scale still destroys `Hue`, `Sat` and `CCT`. Deciding on green alone would
  leave that scene un-ranged, and the §10 NeoPixel rig drives exactly it (a saturated primary).
  Using the maximum in **both** directions is what keeps it stable: switch up when
  `max ≥ AutoRangeUp`, switch down only when `max ≤ AutoRangeDown`. Deciding "up" on the maximum
  but "down" on green alone would oscillate — a red-dominant scene switches up, green lands below
  the down threshold, `AutoRangeDwell` expires, and it switches back.
  The hardware path stays a strict subset of this rule: the INT can only ever *wake* the loop
  early, never make the decision, so the two cannot disagree.
- **Saturation is tested on the raw counts, against the resolution's own maximum** — 4095 at
  12-bit, 65535 at 16-bit — *before* the `<< 4` normalisation, never against 65535 afterwards. A
  12-bit reading normalises to at most 4095 << 4 = **65520**, so a post-normalisation `== 65535`
  test can never fire at 12-bit and the fast path would be silently dead there. Any channel at its
  maximum counts as saturated.

**Only one threshold is live at a time, and which one depends on the range.** An earlier phrasing
here ("high threshold at the switch-up point, low threshold at the switch-down point") reads as if
both are armed together; they cannot usefully be, because the two switch points live on different
gain scales. On the **low** range there is nowhere more sensitive to go, so only an up-crossing
matters: `high` = `u`·65535, `low` = 0. On the **high** range only a down-crossing matters:
`low` = `d`·65535, `high` = 0xFFFF. Each range switch therefore rewrites both threshold registers —
one 4-byte burst write (§8.7), issued in the same handler that flips `RNG`. Two edge cases, both
benign: on the low range, total darkness (count = 0) satisfies the datasheet's "below **or equal
to** the lower threshold" and raises an interrupt the handler simply clears, since no switch is
possible; on the high range, a clipped 65535 does not exceed a `high` of 0xFFFF, so parking it
there raises nothing spurious.

Thresholds should be **set in lux at the API and converted to counts internally** (RIOT does this,
though its `(uint16_t)(65535 / max_range)` integer division truncates 6.55 to 6 — a cautionary
example: do the scaling in float).

**`CONVEN` is not needed, and the open question about it is closed.** The remaining reason to want
conversion-done was freshness. But the sample interval is ≥ 1 s against a ≤ 303 ms cycle, the data
registers are double buffered so "the data is always valid" (p13), and `RGBCF` (`0x08` B5:4) already
says which channel is mid-conversion if the driver ever wants to check. So a plain burst read at any
moment yields three values none of which is more than one cycle old — inside the timestamp's own
one-second resolution. (That is an *age* guarantee, not a coherence one: the channels convert
sequentially, so the triple can still straddle two cycles. The burst read removes the bus-side
tearing §3.6 is about; `CONVEN` would not have removed the rest either.) Setting `CONVEN` would only mux a second event source onto the pin we want for the
thresholds. It stays 0 — and the unresolved "does conversion-done fire per channel or per RGB
cycle?" question no longer needs bench time.

**The settle window is deterministic, not guessed.** An earlier revision of this section recorded
"discard at least one full R-G-B cycle, the datasheet specifies no settling time, this is inference"
as a real gap. Table 7 (p10) closes most of it: with `SYNC` = 0 the ADC *starts* on an I²C write to
`0x01`, so the write that flips `RNG` also restarts the cycle. The first valid sample is therefore
one full cycle after the write — ~303 ms at 16-bit, ~19 ms at 12-bit (3 × the ~6.3 ms derived in
§7.2) — and the driver can simply wait that long rather than discarding an unknown number of
samples. What remains inferred is only whether the restart is exact — and there is now independent
corroboration: the mainline Linux IIO driver (`drivers/iio/light/isl29125.c`) writes `CONFIG1` and
then unconditionally `msleep(101)` — one whole `tINT` — before it will read data, which is only
sensible if the write restarts the integration. Between Table 7 and that, §13 question 1 is
treated as **answered yes**; a bench check could only ever *remove* a wait, never add one, so it
no longer gates anything.

#### The switch points must clear the range ratio, and the first proposal did not

Let `r` = FS_high / FS_low = 10000/375 = **26.67**. Switch **up** when the reading exceeds `u` of
the current (low-range) full scale; switch **down** when it falls below `d` of the current
(high-range) full scale. Immediately after a switch-up the same light reads `u/r` of the high
range, so the no-chatter condition is `u/r > d`, and for real margin `u/r ≥ 2d`, i.e.

> **`d ≤ u / (2r)`** — with `u` = 85 %, that is `d ≤ 1.59 %`.

The schema first proposed in §8.3 had `u` = 85 % and **`d` = 3.0 %**, which fails it: 85 % of 375 lux
is 319 lux, and 3.0 % of 10 000 lux is 300 lux, so a switch-up lands just 6 % above the switch-down
point and the loop chatters on noise alone. Corrected default: **`d` = 1.5 %**, giving a hysteresis
band of 150 lux → 319 lux and a 2.1× margin. The reverse direction is comfortable either way: after
a switch-down the reading sits at `d·r` = 40 % of the low range, far below `u`. Resolution is not a
constraint at the decision point — 150 lux is ~983 counts on range 1's 0.1526 lux LSB. The
constraint is cross-field, so the driver enforces it; the schema cannot (§8.3).

#### Saturation is not the only way to read 65535

A bus fault reads back as all-ones, and the community failure reports for this part are exactly
that: all three channels stuck at `0xFFFF`, under any light, usually alongside a failed init. So
the saturation fast-path must not fire on a dead bus — it would drive the range up and stay there.
Cheap discriminator, no extra transaction: real saturation on a colour source almost never pins
*all three* channels to exactly 65535 at once, and the status byte (`0x08`) is read on the same
interrupt anyway — `0x08` reading `0xFF` is impossible for a register whose B7:B6 and B3 are
reserved-zero. Treat all-three-exactly-65535 **plus** an implausible status byte as a bus fault for
the error counter, not as a range-up trigger; re-read the device ID (`0x7D`) to confirm.

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

An earlier revision ended here with a caution about `CONVEN`: the datasheet never says whether
conversion-done fires per channel or per R-G-B cycle, and per channel at 12-bit that would be
~160 interrupts/s on a soft IRQ path. **Moot now** — §7.6 decided against `CONVEN` on other
grounds, so the bit stays 0 and the question never has to be answered.

### 7.8 Reusable primitives

The first-order EMA used by the legacy SHTC3/MPRLS readers
(`tc = tc_old + FiltCoeff * (tc - tc_old)`, with `<= 0` meaning off) is the existing precedent for
output smoothing, currently inline in each driver rather than shared. `src/math_helpers.py` has no
filter primitive today, and `SPECIFICATION.md` Part G's catalogue lists none — so promoting this
one into a shared primitive is a Part G extension the auto-range work should make, not duplicate.
(BMP3xx's `FiltCoeff` is the *sensor's* on-chip IIR, not a software filter — different thing,
same name.)

### 7.9 IR compensation moves the full scale — the one coupling nobody expected

`IrComp` is not an independent knob. p10: *"Recommended to set BF at register 0x02 to max out IR
compensation value. **It make High range reach more than 10,000 lux.**"* Figure 14 (p14) plots the
same thing directly — "system measurement range (lux)" against "compensation adjustment (% range)",
spanning roughly 2 000 to 11 000 lux across the sweep, for three illuminants whose curves cross at
the correct setting.

So the `FS_lux` constant in §7.1 step 4 is nominal *at one compensation setting*, and changing IR
compensation rescales every lux and every lux-denominated auto-range threshold. Two honest options:

1. **Hold `FS_lux` at the nominal 375/10 000 and document the coupling.** Changing `IrComp` then
   trades lux accuracy for IR rejection and headroom, visibly.
2. **Carry a per-setting scale factor.** Correct, but deriving it needs the p14 procedure with A,
   F2 and D65 reference illuminants, which we do not have and cannot fake with a NeoPixel (§10).

**Recommendation: option 1.** It is the only one we can actually substantiate, and it makes the
default choice matter more, not less — which is the second reason 40 codes beats `0xBF` (§6).
Worth stating in the field's own help text, not just here: *changing IR compensation shifts the lux
scale.*

### 7.10 The raw triple is not white-balanced, and the driver should not pretend otherwise

p3 gives Range 0 full scale as Green = 18, Red = 20, **Blue = 30 µW/cm²**. Blue needs ~1.7× the
irradiance of green to reach the same count, so a broadband white source reads blue-deficient. It
is tempting to divide each channel by its own full-scale irradiance and call the result balanced —
**don't**. Those three numbers are responsivities at three specific monochromatic wavelengths
(565/620/485 nm, note 5 p3), not integrals over a broadband source, so the "correction" would be
right only for a source made of exactly those three lines. A real white-balance needs the 3×3 of
Eq. 1, characterised per optomechanical design, which the datasheet is explicit about.

So: keep the raw ratios, and label the output **sensor RGB**, as §7.4 already concluded. This
section is the quantitative backing for that label, and the reason not to add a `WhiteBal` knob
that could not be set correctly.

### 7.11 CCT — the specified feature the driver never produced

This is the largest gap the re-scan found. p3 specifies *Corrected Color Temperature Accuracy
±5 %* (Illuminant A at 300 lux) as an **electrical specification**, and p15's references list the
Planckian locus and CIE 1931 explicitly. Renesas also publishes a standalone "ISL29125 CCT
calculation" document. CCT is what this part is *for* in its own application list ("industrial/
commercial LED lighting color management", "ambient light color detection/correction"), and none of
the three reference implementations we compared against computes it either.

It is also nearly free here:

- **Range- and resolution-invariant.** CCT depends only on chromaticity, i.e. on the R:G:B ratios,
  so it inherits §7.4's invariance exactly as H and S do. It needs none of the §7.1 normalisation
  chain — only step 1 (the coherent burst read) and step 3 (the dark-offset subtract, which *is*
  load-bearing here because an additive offset distorts ratios).
- **Two short formulas.** RGB → XYZ by a 3×3 (Eq. 1), then `x = X/(X+Y+Z)`, `y = Y/(X+Y+Z)`, then
  McCamy's cubic: `n = (x − 0.3320)/(0.1858 − y)`, `CCT = 449n³ + 3525n² + 6823.3n + 5520.33`.
- **It fits the existing value contract.** `None` is already in every promoted driver's declared
  measurement-value union, so "not determinable" needs no new type.

The honest caveats, both of which go in the field's help text rather than being designed away:

- **The 3×3 must be a documented placeholder.** Eq. 1's coefficients are per-system by the
  datasheet's own statement, and the ±5 % spec presupposes a characterised one. Use the Rec.709/
  sRGB D65 matrix as the stand-in, keep it a module constant (a 3×3 is not nine config fields), and
  say plainly that the output is a *relative, uncalibrated* colour temperature — repeatable and
  monotonic, not a colorimeter reading. A per-unit matrix is the calibration hook if absolute
  accuracy is ever wanted.
- **CCT needs a low-light floor, even though HSB does not.** The project owner accepted HSB's
  low-light behaviour, but chromaticity noise grows much faster than hue noise: near the 1-5 count
  dark floor the denominator `X+Y+Z` collapses and McCamy's `n` diverges. Report `CCT` as `None`
  below a documented green-count floor (proposal: 64 counts on the resolution-normalised scale,
  ~13× the worst-case dark count) and when `n` lands outside McCamy's valid ~2 000-12 500 K span.
  This is a new decision, not a walk-back of the accepted HSB behaviour.

**Accepted by the project owner** (requirement 13). The two caveats above are not negotiable
extras — they are what makes the number honest, so both belong in the field's help text where the
consumer of the API will see them, not only here.

### 7.12 The INT pull-up — settled from the schematics

Three separate questions, each with a definite answer.

**Does the chip have an internal pull-up? No, and it cannot.** p6 is unambiguous: *"The active low
interrupt pin is an open-drain pull-down configuration."* Open-drain means the pin can only pull
low; the high level has to come from somewhere else. The reference circuit (Figures 1 and 15) shows
that somewhere as R4 = 2.7 kΩ-10 kΩ to VDD. Nothing the driver writes can change this.

**Does the dev board already have one? Yes — confirmed.** The project owner has confirmed directly
that INT on the dev board is connected *and pulled up*, on GP6 / physical pin 9. That is the same
class of evidence `dev_legacy/README.md` already records for the UART crossover jumper, and it is
now recorded the same way, in that file's own device table.

This matches the hardware independently: SparkFun's Eagle schematic for the ISL29125 breakout
(`Hardware/SparkFun_ISL29125_Breakout.sch`, read directly) carries **R4 = 10 kΩ from `!INT` to
3V3**, wired straight through — *not* behind the solder jumper. `SJ2` only breaks R2/R3, the
SDA/SCL pull-ups, which is the usual "remove my I²C pull-ups when several boards share the bus"
jumper. So on that breakout the pull-up is present and cannot be disconnected, which is consistent
with what the owner measured.

The board's own software corroborates the rest of the wiring: `dev_legacy/sensortask-dev.py:137`
constructs `ISL29125_Reader(i2c1, …, irq_pin=6, …)` with a real `islIrqCallback` registered
(line 101), and `i2c1` is `(1, scl=15, sda=14, 50 kHz)` — the same bus as SGP40 (line 134) and
SCD30 (line 133). That is evidence of intent and of the pin assignment, not of the resistor; the
owner's confirmation is what settles the resistor.

**Should the driver enable the rp2040's internal pull-up? Yes, unconditionally.** The Pico W
datasheet gives RP2040's on-chip pull-ups as ~50 kΩ (RUN) and nominally 60 kΩ (SWDIO/SWCLK), so the
GPIO pad pull-up is in that class. (The RP2040 datasheet itself is **not** in `datasheets/` — this
is the closest primary source the repo holds, and it is the same on-chip structure.) Enabling it
is right in both worlds:

- **With the external 10 kΩ present** it is harmless — two resistors in parallel, dominated by the
  10 kΩ, ~6 % stronger pull and a few µA more sink current while INT is asserted.
- **Without it** the driver still works. At ~60 kΩ into the tens of pF of a short jumper, the
  rising edge settles in single-digit microseconds against an interrupt that stays asserted for
  milliseconds at least. An earlier revision of this section called 60 kΩ a "degraded mode" on
  timing grounds; that was wrong — timing is not the issue here at all.

So: `Pin(irq_pin, mode=Pin.IN, pull=Pin.PULL_UP)`. Nothing needs to be added to the dev board —
the internal pull-up is belt-and-braces there, and the value of enabling it unconditionally is that
the driver also works on a board that lacks the resistor. If one ever does, 4.7 kΩ or 10 kΩ is
worth fitting for **noise immunity, not speed**: a 60 kΩ pull-up on a jumper wire is far easier to
drag down by capacitive coupling than a 10 kΩ one, and a spurious falling edge on this line is not
cosmetic — it is a bogus auto-range decision.

Worth noting for the convention scan: no other promoted driver's interrupt pin uses `PULL_UP` —
SCD30's RDY line is push-pull, so bare `Pin.IN` is correct there. This is a real difference between
the parts, not a divergence to reconcile.

## 8. Resulting API shape

### 8.1 What the settled requirements remove

"Register ownership is the driver's; the sensor's hardware interrupts are not user-visible" deletes
**four of the ten legacy config keys** outright — they become internal driver state:

`ISLInterruptAssignment`, `ISLInterruptHighThres`, `ISLInterruptLowThres`,
`ISLInterruptAutoClear`.

`INTSEL` and both threshold registers are how auto-range gets its hardware hysteresis (§7.6), so
they are the mechanism, not a setting. A fifth, `ISLPersistentControl` (`PRST`), was listed here in
an earlier revision and has been **put back** as `AutoRangePersist` — it sets how long a light
change must persist before the range moves, which is an auto-range parameter in the sense
requirement 3 means, not plumbing (§8.3). No user-facing event/notification is planned; if
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

**One discrepancy surfaced while checking this, reported rather than fixed** (CLAUDE.md's
"flag, don't silently change" rule for cross-file inconsistency). Of the 30 config field names in
`src/`, exactly one carries a device prefix: `asy_sgp40_driver.py`'s **`SGPResetVOC`**. Every other
field across BMP3xx, SCD30, SGP40, the notification service and the WiFi service is unprefixed.
Since this driver adopts the same command-only-bool pattern for `ISLResetCal` (§7.3, §8.3), it
would be easy to carry the prefix across with it — it does not. Note that `SPECIFICATION.md`
Part C.5.2.1 quotes `SGPResetVOC` by name, but as the worked example of the *mechanism*; nothing
in it makes the prefix part of the convention. Whether `SGPResetVOC` is a deliberate exception (it
is the only *command* rather than *setting* in `src/`, and a bare `ResetVOC` may have read
ambiguously in the UI) or simple drift is for the project owner to settle; nothing here changes
that file.

**This closes §3.7 (the string-getter asymmetry) as a decision, not a question**: enumerated
settings are ints with allowed-value tuples, and the human-readable labels move to `js/`, which
Part G's cross-language mirror obligation requires anyway.

### 8.3 Proposed config schema

| Field | Type | Default | Allowed / range | Effect |
|---|---|---|---|---|
| `SampleInterv` | int | 1 | 1-3600 s | software timer divider |
| `Resolution` | int | 16 | {12, 16} | `CONFIG1` B4 |
| `RangeAuto` | bool | True | — | auto vs. fixed range; also arms (`01`) or disarms (`00`) `INTSEL` |
| `Range` | int | 10000 | {375, 10000} | `CONFIG1` B3, used when `RangeAuto` is false |
| `AutoRangeUp` | float | 85.0 | 50.0-95.0 % FS | switch-up threshold |
| `AutoRangeDown` | float | **1.5** | **0.2-3.0** % FS | switch-down threshold |
| `AutoRangeSettle` | int | 1 | 1-10 cycles | full conversion cycles discarded after any `CONFIG1` write |
| `AutoRangePersist` | int | 4 | {1, 2, 4, 8} | `CONFIG3` `PRST` — hardware transient rejection, in RGB cycles (§7.6) |
| `AutoRangeDwell` | float | 10.0 | 0.0-300.0 s | minimum time on the high range before a switch **down** |
| `ISLResetCal` | bool | — | command-only | discard the learned gain ratio and relearn (§7.3) |
| `IrCompOffset` | int | 0 | {0, 1} | `CONFIG2` B7 (adds 106) |
| `IrCompAdjust` | int | 40 | 0-63 | `CONFIG2` B5:0 |
| `FiltCoeff` | float | -1.0 | -1.0-1.0 | output EMA; <= 0 disables (legacy SHTC3/MPRLS precedent) |

Three properties of that table that are decisions rather than description, and are easy to read
past:

- **`AutoRangeSettle` is a multiplier, not a flag.** The settle deadline is
  `AutoRangeSettle × cycle_ms()` — requirement 14 calls this knob the *settle margin*, so a value
  of 5 must actually discard five cycles, not set a one-cycle deadline five times.
- **`RangeAuto = False` disarms the interrupt at the chip**, by writing `INTSEL = 00`
  ("No Interrupt", Table 11 p11) rather than by parking the thresholds. Parking them cannot fully
  disarm: the datasheet fires on *"below **or equal to** the lower threshold"*, so a low threshold
  of `0x0000` still interrupts in total darkness. With `INTSEL = 00` the fixed-range mode runs
  purely off the software divider, and the read rate is then exactly one per `SampleInterv`.
  Writing it touches `CONFIG3` only, so it costs a 2-byte burst at `0x02` and no conversion
  restart (§8.7).
- **The EMA steps once per read cycle, not once per second.** Under auto-range an INT can add a
  cycle, so `FiltCoeff`'s effective time constant is a lower bound, not a fixed number of seconds.
  With `RangeAuto` false it is exact, by the bullet above.

#### Why `AutoRangeDwell` exists, and what was deliberately not added

`PRST` is the hardware's transient rejection, and it is the wrong tool for half the job. It is one
2-bit field applied to *both* threshold crossings, so it cannot be asymmetric — and auto-range
wants asymmetry: switch **up** fast so a brightening scene never clips, switch **down** slowly so a
passing shadow does not cost a range change, a settle discard, and then a change back. `PRST`'s
maximum of 8 integration cycles is also short for the down direction: 0.8 s or 2.4 s at 16-bit
depending on whether Table 12 counts the 101 ms channel integration or the ~303 ms RGB cycle (the
datasheet does not say which), and 50-150 ms at 12-bit. Either way it is nowhere near the tens of
seconds a room wants. `AutoRangeDwell` is the software half: a floor on how long the driver stays
on the high range before honouring a down-crossing. `0.0` disables it and leaves the behaviour
purely hardware-driven.

Four knobs were considered and **declined**, recorded so they are not re-proposed:

- **A tunable saturation threshold.** Clipping is clipping — 65535 is not a policy. A knob here
  could only ever be set wrong.
- **A selectable auto-range decision channel (`INTSEL`).** Green is both the photopic proxy (§7.5)
  and the basis of the reported lux. Pointing the range decision at red or blue would let the
  range and the value it scales disagree.
- **Separate up/down hardware persistence.** Physically impossible — `PRST` is one field.
  `AutoRangeDwell` is the answer instead.
- **An on/off switch for gain-ratio learning.** See §7.3: the ratio is a device constant, so
  `ISLResetCal` covers the only real need.
- **A settable dark offset.** `DDark` is specified (p3, Electrical Specifications: typ 1, max 5
  counts at Range 0) — it is a property of the part, and a user-supplied value could only ever be
  wrong. It is a module constant; see the table below.

#### Which numbers are config fields, which are constants, and which are learned

Requirement 1 says *"no compile-time constants for anything a user might want to change"*. It
needs one clarification to be applicable, and §7.3 already made it implicitly when it put the gain
ratio in FRAM rather than in the schema: the requirement governs **preferences**. A number is

- a **config field** if a user could reasonably prefer a different value;
- a **module constant** if it is a property of the device or of the maths;
- **learned state** (a FRAM chunk) if the driver derives it at run time.

Stated so the five constants this design introduces are declared rather than discovered in review:

| Constant | Value | Class | Source, and why it is not a field |
|---|---|---|---|
| `_DARK_COUNTS` | 1 | device | `DDark` typ 1 / max 5 counts (p3). Subtracted before every ratio; the typical value is the honest default and the maximum is 0.03 lux on range 0 |
| `_CCT_FLOOR_COUNTS` | 64 | device | §7.11 — ~13× the worst-case dark count, i.e. the level below which a 5-count additive error moves a channel ratio by more than ~8 % |
| `_GAIN_EMA_COEFF` | 0.1 | maths | the learning filter's own time constant; §7.3 declined an on/off switch for the learning for the same reason |
| `_GAIN_RATIO_MIN` / `_MAX` | 20.0 / 34.0 | device | a plausibility gate around the nominal 26.67 (= 10 000 / 375). Bounds on a device characteristic, not a preference |
| the 3×3 RGB→XYZ matrix | sRGB / Rec.709 D65 | system | nine floats cannot be a `ConfigSchema` field, and p13's Eq. 1 says the coefficients *"will be changed respectively depending on the system setup"*. It is a documented placeholder and the calibration hook (§7.11); a per-unit matrix belongs in `BACKLOG.md` at promotion time, not in the schema |

The same page also supplies the vendor's own lux equation — Eq. 2,
`Ev = (CYR·Red + CYG·Green + CYB·Blue) × Range` — which places §7.5's green-only estimate exactly:
it is Eq. 2 with `CYG` set by the FS/65535 scaling and `CYR = CYB = 0`. That is worth knowing
because it means a later characterisation *fills in two coefficients* rather than replacing the
formula.

#### `ISLResetCal` against the project's own rule for command-only fields

`SPECIFICATION.md` Part C.5.2.1 is prescriptive here, so this is conformance, not a design choice.
Four obligations, all of which the driver has to honour and none of which is obvious from the
schema row alone:

1. **Shape**: `_VAL_RESETCAL = const((("ISLResetCal", "bool", None, None, None, True),))` — a
   *special-alone* field, `default=None` with a single-value `special`. Validated and reported,
   never persisted. `"bool"` never inspects `special`, so both values are always accepted, and a
   special-alone write always reports `"Valid"` — which is exactly what makes it a *repeatable*
   trigger rather than a one-shot.
2. **`get_dict_cfg()` needs its own narrower field list**, excluding this field.
   `ConfigManager.get_dict()` is all-or-nothing and would `KeyError` on a key that was never
   persisted. Easy to miss, and it fails at runtime rather than at type-check time.
3. **The push wrapper must report success unconditionally once the type check passes.** A push
   callback's return means "push succeeded/failed"; a recalibration that finds nothing to discard
   has not *failed*. Part C.5.2.1 names `reset_voc()` and SCD30's inverted `ContMeas` as the two
   existing instances of exactly this trap.
4. **No `_get_callbacks` entry.** `_recover_failed_push()` skips command-only fields by design;
   registering a getter for one would be dead code at best.

**Naming — and this resolves §8.2's open discrepancy.** The project owner's call is a prefixed
`ISLReset…` form, which turns what looked like drift into a coherent rule:

> **A command-only trigger field carries the device prefix; an ordinary persisted setting does
> not.** `SGPResetVOC` and `ISLResetCal` are 2 of 2; the 29 persisted settings across BMP3xx,
> SCD30, SGP40, the notification service and the WiFi service are 29 of 29 unprefixed.

That is a real distinction rather than an accident. A setting is read back inside its own
`_NAME`-keyed group, where a prefix would be redundant — whereas a command is a verb the caller
fires and never reads back (`get_dict_cfg()` deliberately omits it, obligation 2 above), so the
prefix is what says *which device* is being commanded at the point of use. Nothing in `src/`
changes: `SGPResetVOC` keeps its name and now has a reason rather than an exception. **§8.2's
finding is closed as a rule, not left as a question.**

`ISLResetCal` matches `SGPResetVOC` in shape (`<PREFIX>Reset<WHAT>`) and length (11), well inside
the existing 12-character maximum.

Three further notes on the shape, all of which changed during this pass:

- **`AutoRangeDown`'s default and bounds were wrong in the first proposal.** 3.0 % chatters against
  an 85 % switch-up — §7.6 does the arithmetic. 1.5 % is the corrected default and 3.0 % is now the
  *ceiling*, not the default.
- **The cross-field constraint is `AutoRangeDown ≤ AutoRangeUp / 53.33`** (i.e. `u/(2r)` with
  `r` = 26.67). `FieldSchema`'s per-field min/max cannot express a relation between two fields, so
  the driver validates it on push and rejects the write, the same way it has to reject any other
  combination the schema can't see.
- **`AutoRangePersist` is added.** It was originally folded away with the other interrupt fields in
  §8.1 as "mechanism, not setting". But `PRST` is the *transient-rejection time constant* of the
  auto-range loop — how many integration cycles a light change must persist before the range moves
  (p6's own camera-flash example) — which is exactly the kind of auto-range parameter requirement 3
  says is API-settable. It is a hardware knob serving a user-visible behaviour, not plumbing.

IR compensation stays **two fields** rather than one: the effective scale is 0-63 and 106-169 with
a gap at 64-105, so no single contiguous range can express it honestly. Its help text must carry
§7.9's warning that changing it shifts the lux scale.

### 8.4 Proposed measurement fields

`namedtuple("ISL29125", ("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "CCT", "RangeAct", "TS"))`

- `Lux` — absolute, green-channel-derived (§7.5).
- `CCT` — relative colour temperature in K, or `None` below the low-light floor (§7.11).
- `Red`/`Green`/`Blue` — **normalised 0-1** over the full span: the fixed range when one is
  selected, the whole auto-range span (10 000 lux) when auto is on — §7.4's denominator paragraph,
  which is the one place this must not be read as "the active range".
- `Hue`/`Sat`/`Bri` — `Bri` follows from RGB being 0-1, so it is 0-1 too. In a dim room that lands
  near 0.003; the project owner has accepted that behaviour, so no log scaling and no low-light
  validity flag.
- **Naming**: in the flat namedtuple HSB's brightness must not be spelled `B` — it would collide
  with blue. `Red`/`Green`/`Blue` + `Hue`/`Sat`/`Bri` keeps both triples unambiguous. The nested
  response body (§8.6) dissolves the collision anyway, so the flat tuple is an internal carrier and
  its names need only be unique, not pretty.
- `RangeAct` — the full-scale range **the reported sample was taken on**, which is not always the
  range currently programmed: a cycle that ends in a switch-up still reports a sample acquired on
  the old gain (§7.6), so the two differ for exactly one reading each time. It belongs in the
  measurement tuple rather than the config dict because under auto-range it is an output, not a
  setting. Note it is **not** needed to interpret `Red`/`Green`/`Blue` — the span normalisation
  above already makes those range-independent. What it is for is diagnostics: it says which gain,
  and therefore which noise floor and which LSB, produced the numbers, and it is what the twin's
  continuity test and the bench sweep assert against.
- **The name is `RangeAct`, not `Range`** — this closes the question the function spec raised
  (q9). `Range` is already a *config* field (the fixed range selected when `RangeAuto` is off),
  the two routinely disagree under auto-range, and that disagreement is the normal case rather
  than an error. Nothing in the stack breaks on a shared name — they live in different response
  bodies — but a settings page and a measurements page showing "Range: 375" and "Range: 10000"
  at the same moment is a support call waiting to happen.

#### Units and precision — requirement 19 in a table

Requirement 19 asks that each emitted value carries a *declared* unit and a *declared* precision.
The units below go in `html/definitions/dev.json`'s `unit` field; the decimals are the rendering
precision is carried by the `decimals` hint §13 question 6 settled. The numbers are decided
here rather than falling out of binary floating point:

| Field | Unit | Decimals | Why that many |
|---|---|---|---|
| `Lux` | `lx` | 2 | 0.01 lx is inside the dark-count spread on range 0 (`DDark` 1-5 counts = 0.006-0.03 lx) and 15× finer than range 1's own 0.1526 lx LSB |
| `RGB.R` / `.G` / `.B` | — | 4 | 1e-4 of the 10 000 lux span is 1 lux. Finer is available in `Lux`, which §7.4 already names as the field to read when magnitude matters |
| `HSB.H` | `°` | 1 | 0.1° is 1/3600 of the circle — below the hue noise at any count level where hue is meaningful at all |
| `HSB.S` | — | 3 | a 0-1 ratio of ratios; three digits is the point where the dark-offset residual dominates |
| `HSB.B` | — | 4 | same scale and same denominator as RGB, so the same precision |
| `CCT` | `K` | 0 | the part's own CCT accuracy is ±5 % (p3) — at 2 856 K that is ±143 K, so a decimal would be three orders of magnitude inside the error bar |
| `RangeAct` | `lx` | 0 | one of exactly two integers |
| `TS` | `s` | 0 | `time.mktime(time.gmtime())`, 1 s resolution, as in all three existing drivers |

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
Python module touched. Note `make_dict()`'s own comment records that `_asdict()`/`_fields` are
unavailable on rp2 (ROM level `EXTRA_FEATURES`, below the `EVERYTHING` they need), so the nested
build is written out explicitly rather than derived from the namedtuple.

#### But the website is flat-keyed, and that is the real cost — correcting this section

An earlier revision of §8.6 concluded "cheap rather than cross-cutting" full stop. That holds for
the **Python** side and is wrong about the **website**, which the audit had not yet reached. Three
concrete places assume a measurement group is a flat map of scalars:

- **`js/definitions.js`'s `resolveFieldValue()`** does `currentValues[field.key]` — a single flat
  lookup, and the one function both rendering and change-comparison go through. Given
  `{"RGB": {"R": …}}` it returns the sub-object, which `formatFieldValue()` renders as
  `[object Object]`.
- **`js/mock-server.js`'s `jitterEachSensorGroup()`** walks exactly two levels
  (`bySensor` → sensor → numeric leaves); its own comment says so. A third level is skipped or
  mangled.
- **`js/templates.js`'s `composite` kind is not the answer.** It exists for the `lightCmdLED` PUT
  body: its sub-inputs are always rendered empty with no value binding, so it is a write-only
  widget, not nested readonly display.

The fix is small and belongs in one place: give a readonly `FieldDef` an optional **`path`**
(`{"key": "R", "path": ["RGB", "R"], …}`) and have `resolveFieldValue()` walk it, with
`jitterInPlace()` recursing. That
is one function each in `definitions.js` and `mock-server.js`, plus the schema documentation in
Part H — and, per CLAUDE.md's Part G `src/`↔`js/` mirror obligation, mirrored tests in
`tests_js/definitions.test.js`, `templates.test.js` and `mock-server.test.js`. §11 lists each file.

**Cheaper than this section first estimated, checked since**: `validateDefinitions()` does not
inspect field-level keys at all — it validates `schemaVersion`, `device.id`, `landingSection`,
`defaultPollIntervalMs`, then per section its `key`/`label`/`rest.get`/`pollGroup` and only that
each group's `fields` is an array. A new optional `FieldDef` key therefore needs **no** validator
change to be accepted; extending it to *check* `path` is optional hardening, worth doing but not
part of the cost of the decision. The schema's major version does not move either (`path` is
additive, and `SUPPORTED_SCHEMA_MAJOR` gates only the major).

The alternative — flattening the output to `R`/`G`/`B`/`Hue`/`Sat`/`Bri` — costs nothing but gives
up requirement 11. **Decided by the project owner: keep the nesting and make the renderer
change** (§13 q4), since `path` is generally useful and every future structured reading gets it
for free.

Proposed response body:

```
{"ISL29125": {"Lux": <float>,
              "RGB": {"R": <0-1>, "G": <0-1>, "B": <0-1>},
              "HSB": {"H": <0-360>, "S": <0-1>, "B": <0-1>},
              "CCT": <float|null>,
              "RangeAct": <375|10000>,
              "TS": <epoch>}}
```

Nesting also dissolves the naming collision flagged in §8.4: `RGB.B` and `HSB.B` are unambiguous
once they sit in separate sub-objects, so both triples keep their conventional single-letter names.

### 8.7 One write path: shadow bytes, burst-written

Three separate findings converge on the same implementation, so it is worth stating once as a
decision rather than three times as consequences.

- `CONFIG1`/`CONFIG2`/`CONFIG3` are **consecutive** (`0x01`-`0x03`), and the part supports burst
  writes with an auto-incrementing address pointer (p7).
- Every `set_bits()` is a **read-modify-write**, and `CONFIG1` now has two writers — auto-range
  (`RNG`) and the API (`BITS`) — so an RMW can silently lose a concurrent change (§9.2c).
- Every write to `CONFIG1` **restarts the conversion cycle** (Table 7, §4), so writes to it should
  be few and deliberate.

So: the driver holds a **shadow copy of all three config bytes**, never reads them back to modify
them, and applies changes as one burst write of whole bytes. The RMW hazard disappears by
construction — there is no read to race — and a full reconfiguration costs one transaction instead
of up to six. Mechanically this works through the promoted bus layer unchanged, with the same
`"Ns"` trick the burst read needs: `set_register_struct(0x01, "3s", bytes((c1, c2, c3)))`, since
`set_register_struct()` takes a single value but accepts `bytes` (`src/asy_i2c_driver.py:130-147`).

Two refinements:

- **Write from `0x02` when `CONFIG1` is unchanged.** An IR-compensation change alone should not
  restart the conversion cycle, so a 2-byte burst at `0x02` is the right form for it. Only
  range/resolution/mode changes pay the restart.
- **The shadow is authoritative, not a cache.** It is never refreshed from the device except on
  the one path that matters: `BOUTF` set means the chip lost its configuration, so the driver
  re-writes the shadow *to* the device (§9.3) rather than reading the device's state *into* it.

The thresholds (`0x04`-`0x07`) are likewise consecutive, so a range switch's new threshold pair is
one 4-byte burst write, not four single writes.

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
conversion in flight when a config bit changes is invalid. Wait one full R-G-B cycle (~303 ms at
16-bit, ~19 ms at 12-bit) after any write that changes `RNG`, `BITS` or the IR compensation. For
`CONFIG1` writes this window is **deterministic rather than inferred**: Table 7 says the write
itself restarts the conversion (§7.6), so the first valid sample is exactly one cycle later. An IR
change writes only `CONFIG2`, which does not restart, so there the one-cycle wait remains a
conservative inference.

**b) `tWC` has a symbol but no value.** Figure 4 (p5) labels an I²C write-cycle time `tWC`, and p7
warns that *"during the internal write cycle, the device inputs are disabled and the SDA line is in
a high impedance state, so the device will not respond to any requests from the master."* But no
`tWC` figure appears in any spec table — checked p3 and p4. So a transaction issued immediately
after a write can legitimately NACK. The driver should treat an `OSError` in the window right after
a config write as a retryable condition, not as a bus fault that feeds the error counter. At 50 kHz
with the project's per-transaction locking this is unlikely to bite, but it is unbounded by
specification rather than known-safe.

**c) `CONFIG1` now has two writers.** Auto-range writes `RNG` (B3) continuously while an API call
can write `BITS` (B4) — same register, and every `set_bits()` is a read-modify-write. Each RMW is
individually lock-protected, but that does not help: auto-range can read `CONFIG1`, the user's
write can land, and auto-range can then write back its stale copy, silently losing the resolution
change. The legacy design never hit this because nothing wrote `CONFIG1` on its own. This is a
consequence of adding auto-range, not a pre-existing defect. **Resolved by §8.7's shadow-byte
burst write** — with no read in the write path there is no stale copy to lose, and the same change
removes five bus transactions and the incidental conversion restarts that per-field RMWs cause.

### 9.3 The flip side of volatility: a brownout silently disables the sensor

Volatile means no wear, and it equally means **no persistence**. `Table 1` gives `CONFIG1` a
power-on default of `0x00`, whose B2:0 = `000` is **Power-Down** per Table 4. (p6's prose says
"Standby" and p10's says "a disable mode" instead — §5 defect 5 — but all three agree on the part
that matters: no conversions.) So after any brownout the chip stops converting entirely, and a
driver that keeps reading data registers would report the last stale values, with a fresh
timestamp, indefinitely.

The datasheet provides the detector: `BOUTF` (`0x08` B2), *"Power-down or Brownout occurred"*
(Table 18, p12), default HIGH at power-up and cleared by writing it LOW.

So the driver should **check `BOUTF` periodically, and on finding it set, re-apply the full
configuration** (mode, range, resolution, IR compensation, thresholds) and clear it again — the
same self-healing posture the existing 1 s interrupt self-heal already takes (§1, item 3). The legacy
driver clears `BOUTF` once at setup and never looks at it again, so a mid-life brownout would go
unnoticed.

This also folds in cleanly: the status register is already read on every interrupt, and `BOUTF`
sits in the same byte as `RGBTHF` and `CONVENF` (§7.7), so the check costs no extra transaction.

**Re-apply on `BOUTF`, never on a timer.** The tempting simplification — just rewrite the config
every few seconds and never worry about it — is wrong here, because a `CONFIG1` write restarts the
conversion cycle (Table 7, §4). A periodic re-assert would abort a cycle every time it fired, and
at a short enough period the ADC would never complete one. `BOUTF` is the trigger; the re-apply is
the §8.7 burst write of the shadow bytes, followed by clearing `BOUTF` and discarding one cycle.

One consequence for the error counter: a brownout that trips `BOUTF` is a *recovered* event, not an
I²C failure. It should be logged (the FRAM-backed per-module log is exactly the place — CLAUDE.md's
rule about reading those before clearing them applies here) but not fed to the leaky bucket that
escalates to a task restart, or a flickering supply would reboot the node instead of healing it.

## 10. The NeoPixel as a range-sweep source (project owner's suggestion)

Pointing the board's own NeoPixel at the ISL29125 gives something no ambient light source does:
**a stimulus the device under test controls**, repeatable to the LSB, sweepable on demand through
both ranges and across the switch point. That is precisely the stimulus the auto-range work needs
and cannot otherwise get — you cannot ask a room to ramp from 10 lux to 2 000 lux on a schedule.

**What it can actually validate** (all of it relative, none of it absolute):

- **Continuity across a range switch** — the headline requirement. Sweep up through the switch
  point, then down through it, and assert that reported lux has no step at the transition beyond a
  stated tolerance. This is the one test that proves §7.1's chain and §7.3's gain-ratio calibration.
- **Hysteresis / no chatter** — park the level right at the switch point and hold. The range must
  not oscillate. Directly exercises §7.6's corrected `u`/`d` arithmetic and `AutoRangePersist`.
- **Settle discard** — assert no glitch sample appears in the cycle after a switch (§7.6).
- **Saturation fast-path** — jump from dim to full scale in one step; the range must move up
  immediately rather than waiting out the persistence counter.
- **Hue/saturation invariance** — hold a colour, sweep brightness across the switch point, assert
  H and S stay put (§7.4). The cleanest possible test of that claim, and a NeoPixel is well suited
  to it since it can hold a fixed ratio while scaling all three channels. `CCT` should hold still
  across the same sweep for the same reason (§7.11) — its *absolute* value against an LED is
  meaningless, but its *stability* through a range switch is exactly what the test is for.
- **Gain-ratio convergence** — run the sweep repeatedly and watch the learned ratio settle (§7.3),
  then `ISLResetCal` and watch it converge again from nominal.
- **Monotonicity** of lux against LED level, in both ranges.

**What it cannot validate, and must not be read as validating.** Three reasons, each independent:

1. **The WS2812 is PWM-dimmed**, at a rate variously specified as ≥400 Hz and 2 kHz depending on
   the die revision. At 16-bit (101 ms) the ADC integrates over 40-200 PWM periods, so residual
   ripple is negligible. **At 12-bit (~6.3 ms) it covers only ~2.5 periods at 400 Hz**, which
   produces tens of percent of beat-frequency ripple. A 12-bit sweep against this source will look
   noisy, *and that noise is the LED, not the driver* — record it here so nobody chases it. It is
   also, incidentally, a neat demonstration of §7.2's flicker-rejection argument on real hardware.
2. **Its spectrum is three narrow LED lines**, nothing like an illuminant. Absolute lux and CCT
   against it are meaningless (§7.10 explains why the per-channel full-scale figures do not rescue
   this), and the p14 IR-compensation procedure — which needs A, F2 and D65 — cannot be run with it
   at all.
3. **Level is not linear in lux.** Assert monotonic, never linear.

**Practical constraints for whoever writes it:**

- The NeoPixel is already owned by `asy_neopixel_driver.py` and driven by
  `asy_notification_service.py`. A sweep must go through the existing override/arbitration path,
  not write the pixel directly, or the two will fight mid-test.
- Geometry is the repeatability limit. Figure 6's radiation pattern falls off well before ±90°, so
  a hand-held LED gives a different answer every run; fix the spacing and alignment mechanically
  and record it, or the sweep is only good within a single session.
- One WS2812 at a few centimetres comfortably exceeds range 0's 375 lux full scale, so both ranges
  and the transition are reachable. Distance sets the span — that is the knob to tune, not
  brightness.
- Tier and gate: this is `tests_hardware/` bench-tier work on the dev board, so it needs the
  project owner's go-ahead in the session that runs it (CLAUDE.md). The same sweep should be
  modelled in the digital twin's chip fake so the identical continuity assertions run in CI on
  every commit, with the bench run as confirmation rather than as the only coverage.

## 11. Integration map — where to integrate what

Scanned by taking each of `bmp3xx`/`sgp40`/`scd30` in turn and following every reference across
the repo, then reading the authoritative checklists the project already keeps
(`SPECIFICATION.md` Part C.11, `digital_twin/README.md`'s "Adding a new chip fake"). Grouped by
area; each row is a file and what it needs.

**Scope**: the `dev` variant only (requirement 18). Every `wozi` counterpart below is an explicit
**non-target**.

**Second pass.** This map was rebuilt once more from the other direction — every file in the repo
that so much as names an existing sensor was enumerated and opened, and every claim already in
this section was checked against the file it names rather than against memory of it. Six rows were
**wrong**, not merely incomplete, and they are corrected in place below rather than appended to:

1. The FRAM cost is **two** chunks, not one (§11.1) — so dev goes to **nine**, not eight.
2. `scripts/_digital_twin_ci_suite.py` only ever boots `run_wozi_integration.py`, so every edit
   §11.5 proposed to it would have been inert (§11.5).
3. `tests/test_digital_twin_sensortask_integration.py` and
   `tests/test_digital_twin_real_website_integration.py` are **wozi-only files** — non-targets,
   where §11.7 listed them as work (§11.7).
4. `SPECIFICATION.md` Part A.7 is titled *"`src/sensortask_wozi.py` construction order"* and has no
   dev counterpart at all, so this needs a **new** section, not an edit to an existing one (§11.11).
5. The `tests_js` PUT matrix already imports `html/definitions/dev.json` **and**
   `mockdata/dev.json` and iterates every writable field it finds — so the mockdata refresh is
   mandatory and automatic, not the optional tidy-up §11.6/§13 treated it as (§11.8).
6. `js/render.js` and `js/field-format.js` were missing from the website row entirely, and both
   are on the path requirement 11's nesting has to travel (§11.6).

Everything else below was confirmed against the file. Where a row now reads "**verified, no
change**", that means the file was actually opened and the reason recorded — not that it was
skipped.

### 11.1 The driver and its wiring (`src/`)

| File | What |
|---|---|
| `src/asy_isl29125_driver.py` | **New.** Two classes per Part C.2: `ISL29125_I2C` (chip protocol, `Lockable` device session) and `ISL29125_Reader(SensorReaderConfig)` (trigger timer, read loop, auto-range state machine, error counting, config schema, FRAM-backed gain-ratio chunk). |
| `src/sensortask_dev.py` | Import + module-global + construction in `build_system()`; `_collect_error_sources()` (**two** entries: `isl_reader`, `isl_reader.cfgmgr`); `_collect_level_setters()` (same two, `.pr.set_level`); `WebserverService(sensors=…)`; `maintenance_sensors=` (a `_isl_maintenance_status()` alongside `_sgp_maintenance_status()`); `await isl_reader.setup()` in the setup batch; `_collect_task_starters()`; `_collect_timer_starters()`. Four details the second pass pinned down — see below the table. |
| `src/sensortask_wozi.py` | **Non-target.** |

**Four details in that row, settled against the real file.**

- **The maintenance keys are `ISL29125_GainRatio` and `ISL29125_CalTS`.** `js/render.js`'s
  `groupValuesFrom()` flattens `/status`'s `sensors` object one level into `<Sensor>_<Field>`
  keys, and `html/definitions/dev.json` addresses them that way (`SGP40_BackupTS` /
  `SGP40_RestoreTS` are the only two that exist today). So `_isl_maintenance_status()` returns
  `{"GainRatio": …, "CalTS": …}` and the definitions file names them prefixed. Not a free choice.
- **`await isl_reader.setup()` really does belong in the batch.** Part A.7 records that
  `scd_reader.setup()` is deliberately *not* in it, "no local config" being the reason. The ISL
  has a `ConfigManager` of its own, so it follows `sgp_reader`/`bmp_reader`, not `scd_reader`.
- **The timestamped chunk needs the NTP callback**, which is a second constructor argument, not a
  free consequence of passing `fram=`: `SGP40_Reader(fram_storage=fram,
  fram_ntp_callback=ntp.ntp_issynced, …)` is the only existing precedent, and
  `AsyFramManager.get_timestamped_chunk()` takes the callback positionally.
- **GP6 is free on dev** — confirmed against `build_system()`'s own pin assignments (i2c0 13/12,
  i2c1 15/14, spi0 2/3/4 + CS 5, SCD30 RDY 11, NeoPixel 18). No conflict to design around.

**A naming discrepancy this surfaces, to raise rather than resolve unilaterally.** `SGP40_Reader`
spells its FRAM argument `fram_storage=`, while `BMP3xx_Reader`/`SCD30_Reader`/`NeopixelDriver`/
`NotificationCoordinator`/`SystemService` all spell it `fram=` — and `SGP40_Reader` then forwards
it to the base class *as* `fram=`. The ISL is the first driver since to need both a FRAM-backed
error log and a chunk of its own, so it is the first to have to pick a side. Part D.10 (API
consistency across the project) makes this a real finding, and CLAUDE.md's "report a discrepancy,
do not silently fix it" made it the project owner's call, not this document's: §13 question 7,
answered `fram=` with `SGP40_Reader` left exactly as it is.

**The FRAM chunk position is a hard constraint, not a style choice.** `AsyFramManager` is a bump
allocator: instantiation order *is* on-chip layout, and Part A.7 records the seven-chunk order as
one that "must stay in this relative order". `SPECIFICATION.md`'s "FRAM chunk determinism rule"
requires every chunk-owning construction to be unconditional and fixed-position. So
`isl_reader` must be constructed **after** `notify_service` (chunk 7) — not in the natural reading
position beside the other sensors, which would shift chunks 5-7 and silently invalidate every
existing error log on the dev board's FRAM. That is exactly the evidence CLAUDE.md warns has
already been destroyed once. One out-of-place construction plus a comment saying why; dev and
wozi then still share an identical chunks 1-7.

**Corrected by the second pass: it takes chunks 8 *and* 9, not chunk 8.** Requirement 15 asks for
a FRAM-backed error history and §7.3 asks for a persisted gain ratio, and those are two separate
allocations — exactly as SGP40 already holds chunks 2 *and* 3 (error log, then VOC backup), both
allocated inside its own `__init__` in that sub-order. So the ISL follows the same sub-order:
**chunk 8 = error log, chunk 9 = timestamped gain ratio**, dev ends at **nine** chunks, and wozi
stays at seven. Capacity is a non-issue (dev's MB85RS2MTA is 256KB against wozi's 8KB), but the
count is not cosmetic — it is asserted literally, see §11.7.

### 11.2 Shared `src/` surfaces

| File | What |
|---|---|
| `src/asy_i2c_driver.py` | Module docstring line 2 lists every I2C driver that uses it by name (verified: `asy_scd30_driver.py`, `asy_sgp40_driver.py`, `asy_bmp3xx_driver.py`) — add this one. No code change: the burst read (`"6s"`) and burst write (`"3s"`/`"4s"`) both work through the existing API (§7.1, §8.7). |
| `src/api_response.py` | Nothing. Its `_ERRNO_UNHANDLED_DISPATCH = 99` sentinel is deliberately above every driver's range; check the new range stays below it. |
| `src/asy_notification_service.py` | **Nothing** — no light-based notification signal is planned. Listed because it is where a future one would register. |

### 11.3 Persistence and config

| File | What |
|---|---|
| `config_ISL29125.cfg` | **New at runtime**, not committed — one JSON file per sensor, written by `ConfigManager` under `cfg_path`. Already covered by `.gitignore`'s `config_*.cfg` rule; no change needed there. |
| FRAM chunks 8 and 9 | Both allocated inside `ISL29125_Reader.__init__`, in that sub-order: the base class's own error-log chunk first, then `get_timestamped_chunk()` for the gain ratio (one float plus CRC, `CRC32()` like SGP40's). The timestamped variant is what lets `_isl_maintenance_status()` report *when* the ratio was learned, and it is why the constructor needs an NTP-sync callback as well as the manager (§11.1). Both must degrade to `None` on allocation failure rather than raising — `__init__` runs before any task supervisor exists to catch it (`asy_sgp40_driver.py`'s own guard is the precedent). |

### 11.4 Error/warning numbering

| File | What |
|---|---|
| `SPECIFICATION.md` Part C.7.1 table | **New row** for `asy_isl29125_driver.py` (`ISL29125`). Start at `errno=10` (base reserves 1-9), reuse `10=init`, `11=periodic read`, `12=config read at init`, `13=config write at init`, then the setter/getter pairs, then the auto-range/calibration/brownout paths. **The authoritative allocation is the function spec's §2** (errno 10-38, wrnno 10-15); this row is a pointer, not a second list. Two things it used to get wrong: the setters are *not* one errno per push callback (the four software auto-range knobs share `errno=27`, and the five hardware-backed fields take get/set pairs), and there is **no `wrnno` for a settle discard** — a settle wait is a planned, successful part of a range switch and is logged at `all`, not as a warning. |

### 11.5 Digital twin

Driven by `digital_twin/README.md`'s own five-step "Adding a new chip fake", which Part C.11
point 9 makes mandatory in the same session as the promotion.

| File | What |
|---|---|
| `digital_twin/_isl29125_chip.py` | **New.** `FaultInjector` (`self.fault`), `random_source` seam, datasheet-sourced min/max plus a documented (non-datasheet) random-walk step bound, and `handle_readfrom_mem()`/`handle_writeto_mem()` answering the exact register-addressed shape `ISL29125_I2C` sends. Must model: the destructive `0x08` read (clears `RGBTHF` **and** the INT pin), `BOUTF` high at power-up, `CONFIG1`'s power-on `0x00`, the sequential G→R→B conversion with `RGBCF`, double-buffered data registers, the 26.67× range gain with a deliberately *non-nominal* per-instance ratio (so the §7.3 calibration has something real to learn), and 12-bit truncation. |
| `digital_twin/machine.py` | `_wire_i2c_devices()`: add `0x44: Isl29125Chip(int_pin=Pin(6, mode=Pin.IN), …)` to the **`dev` profile's `bus_id == 1`** dict, beside `0x61`/`0x59`. The existing `Pin.simulate_edge()` is exactly the mechanism the active-low INT needs (`simulate_edge(0)` on a threshold crossing, `simulate_edge(1)` when `0x08` is read) — the same seam `_scd30_chip.py` already uses for its RDY line. |
| `digital_twin/README.md` | "What's here" bus-wiring bullet; the dev-variant section. |
| `digital_twin/launch.py` | **Optional / non-target.** It mirrors wozi's wiring only. If a dev profile is ever added there, `_FAULT_DEVICE_OPS` and `_sensor_loop()` gain an `isl29125` entry. |
| `digital_twin/run_dev_integration.py` | On-disk state (a `--isl29125-state-path` mirroring `--scd30-state-path`) is **not** needed: the gain ratio lives in the FRAM chunk, which the twin already persists via `--fram-state-path`. What it may need is a fault spec covering requirement 17's failure mode — see below. |
| `scripts/_digital_twin_ci_suite.py` | **Corrected: nothing, and that is a finding.** The suite hard-codes `run_wozi_integration.py` as the subprocess it drives (its own docstring, and the `cmd = [micropython_bin, "digital_twin/run_wozi_integration.py", …]` it builds), so the ISL never boots inside it. Adding `"ISL29125"` to `_VERBOSE_LOG_PREFIXES`/`_PERSISTED_ERROR_MODULES` would be dead configuration. See the note below the table. |
| `digital_twin/run_dev_integration.py` (again) | This, not the CI suite, is the twin's dev entry point — it boots the real `sensortask_dev` graph. The ISL therefore enters it **automatically** the moment `build_system()` constructs one, which promotes the chip fake from "required by policy" to "required or `tests/test_digital_twin_run_dev_integration.py`'s existing bounded end-to-end smoke test stops passing". |

**Two consequences of the CI-suite finding.**

- **The twin-tier end-to-end coverage for this sensor comes from the dev runner and the dev unit
  tests, not from the wozi CI suite.** That is a deliberate gap, not an oversight to close in this
  promotion: parametrising `_digital_twin_ci_suite.py` over both entry points is a rewrite of a
  700-line harness that today hard-codes wozi's module set, ports, fault specs and expected error
  modules. Recommendation: leave it wozi-only, and record the asymmetry in `BACKLOG.md` so the
  next person does not read the absence as an accident. (§13, question 8.)
- **Requirement 17 needs a fault mode nothing currently provides: an INT line that never
  asserts.** The interrupt-freezes-silently hole is exactly what requirement 17 exists to close,
  so the chip fake must be able to *not* pull the line — a constructor flag or a `FaultInjector`
  op (`isl29125:int_stuck_high`) that suppresses `simulate_edge()` while the conversion data keeps
  moving. Without it the requirement's periodic-read path is untestable at the tier that would
  actually catch a regression. Worth noting `digital_twin/machine.py`'s `Pin` is a **per-id
  registry singleton**, so the `Pin(6)` the chip fake holds and the `Pin(6)` the driver constructs
  are the same object — which is what makes the whole mechanism work, and is worth a comment in
  the fake so nobody "fixes" it later.

### 11.6 Website (`html/`, `js/`, `mockdata/`)

| File | What |
|---|---|
| `html/definitions/dev.json` | **The single place the website learns about a sensor.** Its `status`→`errcount` group carries an explicit 17-entry `modules[]` list, which becomes **19**. `measurements` → a new `ISL29125` group (`Lux`, the nested RGB and HSB fields, `CCT`, `RangeAct`, `TS`), each with the `unit` and rendering precision §8.4's table fixes. `sensors` → a new `ISL29125` group with all 13 config fields: `enum` for `Resolution`/`Range`/`AutoRangePersist`/`IrCompOffset`, `number` (`float: true` where fractional) for the rest, `toggle` for `RangeAuto`, and `toggle` + `dispatch: true` + `defaultValue` for `ISLResetCal`. `status` → `sensors` group gains the two maintenance keys. |
| `js/definitions.js` | `resolveFieldValue()` learns the optional `path` walk; `validateDefinitions()` validates `path` and `decimals`; the `FieldDef` typedef gains both keys. Required by requirement 11 (`path`) and requirement 19 (`decimals`) — see §8.6 and §13 q4/q6. Note *accepting* either key needs no validator change (it does not inspect field-level keys today) and the schema major stays 1; the validation is added because the file's own contract is to fail loudly on a malformed definitions file rather than in the browser. |
| `js/mock-server.js` | `jitterInPlace()`/`jitterEachSensorGroup()` recurse one level deeper; `applySensorQuirksForGet()` omits `ISLResetCal` the way it already omits `ContMeas`/`SGPResetVOC`. |
| `js/render.js` | **Added by the second pass.** Two places touch the shapes this driver introduces. `groupValuesFrom()` hands the whole `data[group.key]` object to the renderer for `measurements`, which is what makes the `path` walk in `definitions.js` sufficient rather than needing a second unwrap here — **verified, no change**. Its `status`/`sensors` branch is the `<Sensor>_<Field>` flattener the maintenance keys must match (§11.1) — also no change, but the naming is not free. Its `collectGroupBody()` PUT path only ever sees the flat `sensors` group, so nesting never reaches it. |
| `js/field-format.js` | **Added by the second pass; the question it carried is now decided.** `formatFieldValue()` handles `null` already (renders `—`), so a `None` CCT is fine with no change. But every numeric field ends at a bare `String(value)`, and no driver in `src/` rounds anything — so eight unrounded floats per reading would render at full binary precision. **§13 q6 lands on option (b)**: honour an optional `decimals` hint — a sibling of the existing `format: "gmtimestruct"` dispatch — applied to numbers only, after the `null`/`mask`/`enum` branches and before the final `String(value)`. The drivers keep full precision and stay identical to each other; the per-field values are §8.4's table. All four sensors can adopt it later at the cost of one key each. |
| `js/templates.js` | The `readonly` kind is the only one these fields use and it renders through `formatFieldValue()` — **verified, no change**, provided `resolveFieldValue()` has already resolved the `path`. |
| `js/app.js`, `js/main.js` | **Verified, no change.** `app.js`'s `KNOWN_DEVICES` already contains `"dev"`; `main.js` is the production entry and has no device switch at all. |
| `mockdata/dev.json` | Replace the **stale legacy `ISL29125` blocks that are already there** — `measurements` still carries raw `Red`/`Green`/`Blue` counts, `sensorsConfig` still carries the ten `OperationMode`/`Interrupt*` keys §8.1 deletes. `status.errcount` already lists `ISL29125` and `CFGMGR_ISL29125`, so that part is done; `status.sensors` needs the two new maintenance keys. **Not optional** — `tests_js/mock-server-put-matrix.test.js` reads this file and `html/definitions/dev.json` together and generates a case per writable field, so a definitions entry with no matching mock value is a failing test, not a cosmetic gap (§11.8). (It also carries orphan `SHTC3`/`MPRLS` entries for sensors the refactored dev does not have. **§13 q5 is decided: leave them** — `tests_js/mock-server-put-matrix.test.js`'s `DEV_UNIQUE_GROUPS` keeps the same two names under the project owner's 2026-09-08 direction, and these blocks are the data half of that placeholder.) |
| `html/index.html`, `html/style.css` | Nothing — both are generic; a `.composite-fields`-style rule is only needed if the `path` change introduces new markup, which it should not. |
| `html_raw/dev/*` | **Non-target.** `SPECIFICATION.md` (Part H.1) records legacy `html_raw/` as deliberately not updated — accepted debt. |
| `html/definitions/wozi.json`, `mockdata/wozi.json` | **Non-targets.** |

### 11.7 Unit tests (`tests/`, real MicroPython Unix port)

| File | What |
|---|---|
| `tests/test_asy_isl29125_driver.py` | **New.** The bulk of the work: register packing, the burst read/write, the normalisation chain, the auto-range state machine (both the INT path and requirement 17's periodic path), hysteresis and dwell, settle discard, saturation vs. bus-fault discrimination, gain-ratio learning and `ISLResetCal`, brownout re-apply, HSB/CCT maths incl. the low-light `None`, every schema field's validation, the cross-field `AutoRangeDown ≤ AutoRangeUp/53.33` rejection, and the command-only field's four Part C.5.2.1 obligations. |
| `tests/machine.py` | **Verified, no change.** The I2C fake is a generic dict-of-registers double; `Pin.__init__` already accepts `pull`; and `IRQ_FALLING = 0x04` is defined with the default trigger mask covering both edges, despite the comment noting SCD30 only uses rising. Nothing to extend. |
| `tests/test_digital_twin_isl29125.py` | **New.** Deterministic unit tests of the chip fake in isolation, matching the three existing `test_digital_twin_{sgp40,scd30,bmp3xx}.py`. |
| `tests/test_digital_twin_machine.py` | Extend the dispatch tests for the new address on dev `bus_id == 1`. |
| `tests/test_bus_hazard_multi_device.py` | Mock-tier bus hazards — same-device read-vs-write, cross-device interleaving with SCD30/SGP40, address/command sweep. **CLAUDE.md standing rule, all four tiers.** |
| `tests/test_digital_twin_bus_hazard_concurrency.py` | Twin-tier equivalent; add the ISL to the "every sensor still produced real data under concurrent load" assertions. |
| `tests/test_sensortask_dev.py` | **The heaviest single file, and the second pass found exactly what changes.** Five existing assertions break the moment the reader is constructed, all of them literal: `test_fram_chunk_allocation_order_matches_the_documented_seven_chunk_sequence()` asserts `calls == ["chunk", "chunk", "timestamped", "chunk", "chunk", "chunk", "chunk"]` — it gains `"chunk", "timestamped"` and **its own name and section comment stop being true** (seven → nine); `len(body["errcount"]) == 17` → 19, and the comment calling it a "16-owner enumeration" → 18; `set(body["sensors"].keys()) == {"SGP40"}` → `{"SGP40", "ISL29125"}`; and three `assert_sensor_payload_not_self_wrapped(…, {"SCD30", "BMP3XX", "SGP40"})` calls (`/measurements`, `/sensors`, `/status`) each gain `"ISL29125"`. Plus the new work: `assert_named_modules_constructed()`'s tuple gains `"isl_reader"`, `test_fram_chunks_are_all_successfully_allocated_not_out_of_memory()` gains its two chunks, and new assertions for `i2c1`, `irq_pin=6` with `PULL_UP`, the two error sources and two level setters, and the task/timer starters. |
| `tests/test_digital_twin_sensortask_integration.py` | **Corrected: non-target.** Despite the neutral filename it imports `sensortask_wozi` and drives only that graph — its two `assert_sensor_payload_not_self_wrapped()` calls stay at three sensors. The dev-side equivalent of this coverage is `tests/test_sensortask_dev.py`'s own three calls, above. |
| `tests/test_digital_twin_run_dev_integration.py` | **More than "only if".** Its bounded end-to-end `main()` smoke test boots the whole real dev graph against the twin, so the chip fake must exist and answer or this file fails — it is the twin tier's real gate for this sensor (§11.5). Extend it with the requirement-17 scenario if the INT fault mode lands here. |
| `tests/test_asy_webserver_service.py` | The nested `get_dict_data()` return is a new shape for `_stream_dict_response()` — add a case proving a two-level value serialises correctly and is not re-wrapped. |
| `tests/test_setter_microdot_integration.py` | It drives real readers through real Microdot routes; add the ISL for the schema-driven setter path, and specifically for the command-only field's repeatable-trigger semantics. |
| `tests/test_digital_twin_real_website_integration.py` | **Corrected: non-target.** It pre-registers `frozen_website_wozi` and boots `sensortask_wozi`; its only mention of dev is an assertion that `/definitions/dev.json` is *not* served, which stays true. Same for `tests/test_website_build_integration.py`. **The gap this exposes is real though**: no test anywhere boots the dev website, and `js/definitions.js`'s validator never runs against `html/definitions/dev.json` — see §11.8. |
| `tests/test_config_manager.py`, `tests/test_base_classes.py`, `tests/test_print_log.py`, `tests/test_crc_checks.py`, `tests/test_fram_integration.py`, `tests/test_ntp_fram_system_integration.py`, `tests/_shared_rest_roundtrip.py` | **Verified, no change.** Each was opened: every sensor name in them is a comment, a docstring example or a `PrintLog(name="SGP40")`-style label, never an enumeration of the real registry. `test_ntp_fram_system_integration.py` imports all three readers but builds its own fixtures rather than the dev graph. |
| `tests/test_sensortask_wozi.py`, `tests/test_digital_twin_run_wozi_integration.py`, `tests/test_digital_twin_launch.py` | **Non-targets.** `test_sensortask_wozi.py` carries the same seven-chunk and three-sensor assertions and they must stay exactly as they are — the divergence is the point. |

### 11.8 Website tests (`tests_js/`, Node)

| File | What |
|---|---|
| `tests_js/definitions.test.js` | The `path` resolution and its validation. |
| `tests_js/templates.test.js` | A nested readonly field renders its value, not `[object Object]`; and the `decimals` hint — `formatFieldValue()` has no test file of its own and is covered here today, so the rounding cases go here too (a hue at 1 dp, a CCT at 0 dp, `null` still `—`, a non-number untouched, and a field with no `decimals` behaving exactly as now, so the other three sensors cannot regress). |
| `tests_js/render.test.js` | Change-comparison still works for `path`-bearing fields; `ISLResetCal` is always resubmitted (`dispatch`). |
| `tests_js/mock-server.test.js` | Deeper jitter; `ISLResetCal` omitted from GET readback. |
| `tests_js/mock-server-put-matrix.test.js` | **Corrected: not an optional new case — an automatic one.** It already imports `html/definitions/dev.json` and `mockdata/dev.json` and builds a case per writable field in *both* shipped devices, keeping dev's through `DEV_UNIQUE_GROUPS`, a set that **already contains `"ISL29125"`**. Its own header says the mechanism is kept "for when dev gains its own unique sensor(s) later" — this is that sensor. So no filter logic changes: what changes is that the filter starts matching, its header comment ("currently matches zero of dev's real groups") goes stale and must be rewritten, and `mockdata/dev.json` must carry a valid current value for every ISL field or the generated cases fail. |
| **A gap, not a file** | Nothing anywhere runs `js/definitions.js`'s `validateDefinitions()` against `html/definitions/dev.json`. `definitions.test.js` loads `wozi.json`; the PUT matrix imports dev's JSON raw, with no validation. So a malformed dev definitions file ships and only fails in a browser. Adding the ISL group is the moment to close this — a one-line addition to `definitions.test.js` covering both shipped devices. |
| `tests_js/live-backend-put-matrix.test.js`, `_live_matrix_command.js`, `_live_twin_command.js` | These drive `run_wozi_integration.py`. **Non-targets** unless a dev-twin variant is added. |
| `scripts/cross_browser_smoke.mjs` | Same — wozi-driven, non-target. |

### 11.9 Real-hardware tests (`tests_hardware/`)

All of this needs the project owner's go-ahead in the session that runs it (CLAUDE.md).

| File | What |
|---|---|
| `tests_hardware/bus_topology.py` | `DEV_TOPOLOGY`'s `port_id=1` device tuple gains `I2CDeviceSpec("ISL29125", 0x44)`; `KNOWN_ADDRESSES` gains `0x44: "ISL29125"`. Two lines, and the autodetect sweep picks it up from there. |
| `tests_hardware/device_scripts/isl29125_plausibility_read.py` | **New**, matching `scd30_plausibility_read.py`/`bmp3xx_plausibility_read.py`. |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py` | **New**, matching the existing per-device pair. |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py` | **New**, matching `scd30_real_irq_edge.py` — and the natural place to settle §13's `CONFIG1`-restart and `PRST`-units questions. |
| `tests_hardware/device_scripts/isl29125_autorange_sweep.py` | **New** — the NeoPixel rig of §10. The one test no other sensor has an analogue of, and the second pass found it needs more than a script: it depends on physical geometry (an LED aimed at the sensor) that a normal bench run has no way to assume. So it needs an **opt-in gate** of its own, like the three that already exist — a `pytest_addoption()` flag in `tests_hardware/conftest.py`, plus an entry in `scripts/_require_clean_hardware_run.sh`'s `KNOWN_PERMANENT_SKIPS` for when the flag is absent, so an expected skip does not read as a failure. The alternative is `tests_hardware/manual/`, which exists for exactly this "needs a human and a physical reference" shape — recommended for the accuracy half, with the automated sweep staying in `flash/` behind the flag. |
| `tests_hardware/flash/test_bus_concurrency.py`, `flash/test_sensor_accuracy.py` | Flash-tier registration of the scripts above. |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py`, `bench/test_rest_endpoints_over_sta.py`, `bench/test_sensor_config_push_over_real_hardware.py`, `bench/test_memory_stress_bench.py` | Bench-tier: the new group appears in the REST surface, its settings push over real hardware, and the extra module's heap cost is counted. |
| `tests_hardware/README.md` | Document the new scripts, the new opt-in flag, and the NeoPixel rig's own physical setup (geometry matters, §10). |
| `tests_hardware/conftest.py`, `scripts/_require_clean_hardware_run.sh` | **Added by the second pass** — the opt-in flag and its expected-skip entry, per the row above. |
| `tests_hardware/manual/manual_sensor_accuracy.py` | Candidate home for the "against a real reference" half of the NeoPixel work, alongside the BMP388 entry already there. |

### 11.10 Build and tooling

| File | What |
|---|---|
| `scripts/build_firmware.py` | **Nothing.** It freezes `src/*.py` wholesale; only the three reserved names (`microdot.py`, `main.py`, `frozen_html.py`) would collide. |
| `boot_entry/dev_boot.py` | Check — likely nothing, it calls `sensortask_dev.main()`. |
| `pyproject.toml` | A `[tool.ruff.lint.per-file-ignores]` row for `src/asy_isl29125_driver.py` if it takes a boolean positional (`FBT001`), as all three existing drivers do. `N801` is already globally allowed, so `ISL29125_I2C` is fine. |
| `build-dev.sh` and the other three `build-*.sh` | **Non-targets, permanently** — CLAUDE.md's legacy hard rule. |

### 11.11 Documentation

| File | What |
|---|---|
| `SPECIFICATION.md` Part A.7 | **Corrected: a new section, not an edit.** A.7 is titled *"`src/sensortask_wozi.py` construction order and dependency graph"* and documents wozi only — dev's order lives nowhere but `sensortask_dev.py`'s own inline comments. A.7 even says outright that its order "and `i2c0`'s SCD30-specific `timeout=200000`, are wozi's own". So this needs a dev counterpart (an A.7.1, or a dev block inside A.7) recording the **nine**-chunk order and the out-of-position `isl_reader` construction — and an explicit statement that wozi stays at seven. |
| `SPECIFICATION.md` Part A.4 | Module-by-module reference entry. |
| `SPECIFICATION.md` Part C.7.1 | The errno/wrnno row (§11.4). |
| `SPECIFICATION.md` Part C.8 | Bus-hazard/locking: the ISL joins i2c1's device list. |
| `SPECIFICATION.md` Part G | Any shared primitive this work promotes — the EMA filter (§7.8) is the concrete candidate, and it must be added to the catalogue rather than duplicated. |
| `SPECIFICATION.md` Part H | The definitions-file schema gains `path` (H.5); H.6's dispatch-only field list gains `ISLResetCal`. **Plus one claim that stops being true**: H.5 ends "See `wozi.json`/`dev.json` for worked examples — nearly identical field content (same three drivers); only `device.id`/`displayName` and I2C bus pairing differ". After this promotion the two files differ by a whole sensor, and that sentence is exactly the kind of stale cross-reference the second pass was asked to find. |
| `README.md` | Two places, not one. (a) The device table's `dev` row currently reads "SCD30, SGP40, BMP388 — **same drivers as wozi**, different I2C bus pairing" — that clause has to go, not just gain a fourth name. (b) The "Further reading" entry for **this document**, which already carries its own disposal instruction: *"Temporary by design — delete it when the promotion closes, migrating anything permanent into `SPECIFICATION.md` first"*. Closing the promotion means executing that, not leaving the plan behind as a second source of truth. |
| `DEVICE_REFERENCE.md` | A user-facing section on the ISL's own easily-conflated values — the IR-compensation/lux-scale coupling (§7.9) and "sensor RGB is not colorimetric RGB" (§7.10) are exactly the SGP40-backup-style traps this file exists for. |
| `THIRD_PARTY_LICENSES.md` | Move the entry from "Shipped but not promoted" to "Restructured/rewritten, attribution retained" (§12). |
| `BACKLOG.md` | Close the `readfrom_mem_into()` item if done; record anything deferred. |
| `CLAUDE.md` | Only if a new standing rule comes out of this. |
| `dev_legacy/README.md` | Already updated with the INT wiring; add the ISL to "Confirmed working" once the bench run passes. |

### 11.12 The one cross-cutting obligation that is easy to miss

CLAUDE.md: **whenever a new file is added to `src/`, run a bird's-eye scan over the whole of
`src/`** — Part D.10 API consistency, Part D.9 current-MicroPython check, and Part G's
shared-primitive catalogue and grep-for-the-shape discovery. And: *"if the scan surfaces a
discrepancy, do not silently fix it — report it and discuss."* This pass has already produced one
such finding (the config-field prefix question, §8.2), and the second pass produced three more
(§13's questions 6-8: output rounding, the `fram_storage=`/`fram=` split, and the twin CI suite's
wozi-only scope). All four are written up as questions rather than as changes, which is how the
rule is meant to work.

### 11.13 Cross-check: every requirement against the places that realise it

Asked for explicitly — do §6 and §11 match, and is each complete with respect to the other. Run
in both directions. **Forwards** (requirement → where it lands) is the table; **backwards** (an
integration row with no requirement behind it) is the note after it.

| Req | Where it is actually realised | Complete? |
|---|---|---|
| 1 settings persisted | §11.1 schema · §11.3 `config_ISL29125.cfg` · §11.6 definitions · §11.7 schema tests · §11.8 PUT matrix | yes |
| 2 Resolution | schema field + `enum` in definitions | yes |
| 3 Range / auto | schema fields; twin fake must model the 26.67× gain to exercise it | yes |
| 4 outputs normalised over the span | §11.1 driver · §11.6 measurements group · §7.4's denominator paragraph, which fixes the span at 10 000 lux under auto-range | yes |
| 5 mandatory INT GPIO | §11.1 `irq_pin=6, PULL_UP` · §11.5 twin `Pin(6)` + `simulate_edge()` · §11.7 `tests/machine.py` (verified) · §11.9 `isl29125_real_irq_edge.py` | yes — all four tiers |
| 6 IR compensation | two schema fields | yes |
| 7 registers stay the driver's; no INT surfaced | **a negative requirement, and it is testable**: no `Interrupt*`/threshold field in the definitions file, none in the schema, `asy_notification_service.py` untouched, and the stale legacy `Interrupt*` keys deleted from `mockdata/dev.json` | yes |
| 8 RGB 0-1 | §11.6 — and the display half was **missing** until the second pass; now requirement 19 | now yes |
| 9 HSB low-light accepted | `DEVICE_REFERENCE.md` (§11.11) — a documentation obligation, not a code one | yes |
| 10 project conventions | §11.12 bird's-eye scan · §8.2/§8.3 | yes |
| 11 structured output | §11.6 `path` in `definitions.js` · `render.js`/`templates.js` verified · §11.7 `_stream_dict_response()` case · §11.8 three JS tests | yes |
| 12 no `OperationMode` | deleting the stale mock block is the only place it still exists | yes |
| 13 CCT | measurements group; `null` already renders as `—` (verified) | yes |
| 14 auto-range tunable | schema · PUT matrix · §11.9 NeoPixel rig | yes |
| 15 logging / FRAM / errno | §11.3 chunks 8+9 · §11.4 errno row · errcount lists in **three** places: `html/definitions/dev.json` (17→19), `tests/test_sensortask_dev.py` (17→19), `mockdata/dev.json` (already present) | yes, after the second pass corrected the chunk count |
| 16 self-healing, never stale | driver · twin fake must model `BOUTF` and the destructive `0x08` read · unit tests | yes |
| 17 auto-range not INT-alone | driver's periodic path · unit tests both paths · **and a twin fault mode that suppresses the edge**, which the second pass found nothing provides (§11.5) | now yes |
| 18 dev only | every `wozi` row marked non-target; `tests/test_sensortask_wozi.py`'s seven-chunk and three-sensor assertions must stay untouched | yes |
| 19 declared unit and precision | **§8.4's units-and-precision table** (the values) · §11.6 `field-format.js`'s `decimals` hint (the mechanism, §13 q6 option (b)) · definitions `unit` + `decimals` metadata · `tests_js/` mirror | yes |
| 20 constructs on an absent chip | §11.7 `tests/test_sensortask_dev.py` (the generic mock has no ISL registers) | yes |

**Backwards.** Three integration rows exist for reasons no requirement states, and that is
correct rather than a gap — they are project obligations, not device behaviour:
`THIRD_PARTY_LICENSES.md` (attribution), `BACKLOG.md` (the `readfrom_mem_into()` prerequisite),
and §11.12's bird's-eye scan. Everything else in §11 traces to a requirement above.

**Two structural observations from running the cross-check**, neither of which changes a
requirement:

- Requirements 4, 8, 11, 13 and 19 all converge on **one output path** — driver → namedtuple →
  `get_dict_data()` → `_stream_dict_response()` → `resolveFieldValue()` → `formatFieldValue()`.
  Five requirements, one chain, and the second pass found two of its six links (`render.js`,
  `field-format.js`) had never been examined. A single end-to-end test that walks the whole chain
  for one nested field is worth more than five isolated ones.
- Requirements 15 and 18 interact in a way nothing else does: 15 adds FRAM chunks, 18 says dev
  only, and the result is the **first permanent divergence between the two variants' FRAM
  layouts**. Every doc and test that currently says "seven chunks" has to learn that the number is
  per-variant. That is three files (`SPECIFICATION.md` A.7, `tests/test_sensortask_dev.py`
  including a test *name*, and `sensortask_dev.py`'s own comments) and it is the single
  easiest thing in this whole plan to get half-right.

## 12. Known prerequisites and standing obligations

- `BACKLOG.md:519-522` already flags `asy_i2c_driver.py`'s `readfrom_mem()` → `readfrom_mem_into()`
  zero-copy change as *"worth doing before `asy_isl29125_driver.py` … is migrated"*, naming this
  driver as its one plausible future caller.
- The device shares **I2C1** with SCD30 and SGP40 on the dev rig — `dev_legacy/sensortask-dev.py`
  builds all three on the same `i2c1` object (lines 133, 134, 137; `i2c1 = I2C(1, scl=15, sda=14,
  50 kHz)` at line 127) — so CLAUDE.md's standing bus-hazard rule applies in full: coverage across
  all four tiers (mock, digital twin, flash, bench) per `SPECIFICATION.md` Part C.8. The INT line
  is GP6 / physical pin 9, pulled up (§7.12).
- A **digital-twin chip fake** is required for any new sensor driver (`SPECIFICATION.md` Part C.11
  point 9, `digital_twin/README.md`). It will need to model the destructive flag-register read and
  the sequential conversion cycle to be useful for the interrupt path.
- **Licensing** is settled and needs no new work: upstream is
  `jposada202020/MicroPython_ISL29125`, MIT, © 2023 Jose D. Montoya, archived Dec 2024, and our
  file is a restructure. On promotion the `THIRD_PARTY_LICENSES.md` entry moves from "Shipped but
  not promoted" to "Restructured/rewritten, attribution retained". **The promoted file also needs
  its own two-line SPDX header above the module docstring** — all three existing drivers carry
  one and §14.3 records the exact shape; this document had not mentioned it before the quality
  pass. One **separate, pre-existing** question stays open there: upstream's `i2c_helpers.py` carries an explicit "Based on
  `adafruit_register.i2c_struct`/`i2c_bits`, © 2016 Adafruit Industries, MIT" notice, while
  `src/asy_i2c_driver.py` — which exposes the same four-operation API — carries no attribution at
  all. By the standard already applied to `asy_fram_driver.py` it may warrant a similar note.

## 13. What was open, and how each was answered

**Nothing in this document is open any more.** Nine questions were raised across it and its
companion; six were closed by research and the remaining three by the project owner directly.
They are kept here, with their evidence, so that none of them is reopened by a later reader who
only sees the conclusion.

### Answered by the project owner

4. **Keep the nested measurement output** — yes. `RGB` and `HSB` stay sub-objects (requirement
   11), and the website gains the optional `path` walk (§8.6). Cheaper than first costed:
   `validateDefinitions()` does not inspect field-level keys, so `path` is *accepted* with no
   validator change and `SUPPORTED_SCHEMA_MAJOR` does not move; the validation is added anyway,
   because that file's contract is to fail loudly rather than in the browser.
5. **Leave `mockdata/dev.json`'s orphan `SHTC3`/`MPRLS` blocks alone.** They are the data half of
   the placeholder `tests_js/mock-server-put-matrix.test.js` keeps in `DEV_UNIQUE_GROUPS` under
   the owner's own 2026-09-08 direction — *"keep this mechanism as-is for when dev gains its own
   unique sensor(s) later, not to prune it now."* They generate no test cases while nothing in
   the definitions names them. (The stale `ISL29125` blocks in the same file are a different
   matter and are replaced either way, §11.8.)
6. **Rounding is option (b)**: a `decimals` hint on the readonly field, honoured by
   `formatFieldValue()`. The driver rounds nothing, so all four drivers stay identical to each
   other, and the fix is available to the other three for one key each. The per-field values are
   §8.4's units-and-precision table. Two things make (b) the cheap option in practice:
   `formatFieldValue()` already dispatches on a display-only hint (`format: "gmtimestruct"`), and
   `js/mock-server.js` already rounds its own jitter to two decimals — the renderer is currently
   the only layer that does not round.

**One more decision, made in the same round**: the auto-range software decision uses the **peak
of the three channels** in both directions, not green alone (§7.6). Proposed by the resolution
pass, confirmed by the project owner.

### Answered by research

1. **A `CONFIG1` write does restart the conversion cycle.** Table 7 (p10) gives "ADC start at I2C
   write 0x01" for `SYNC` = 0, and the mainline Linux IIO driver
   (`drivers/iio/light/isl29125.c`) writes the mode byte and then unconditionally `msleep(101)`,
   one whole `tINT`, before reading — which is only sensible under that reading. §7.6 records
   both. A bench check could only ever *remove* a wait.
2. **`PRST` counts full RGB cycles**, not channel integrations. Not from new wording but from
   `INTSEL`: the comparison is made against one selected channel, which converts once per cycle,
   so consecutive interrupt conditions can only accumulate at one per cycle (§7.6). Worst case if
   a bench run disagrees is that hardware rejection is 3× faster than documented — safe up,
   irrelevant down.
3. **AN1910, AN1914, AN1591 and the Renesas "ISL29125 CCT calculation" note remain
   unobtainable** — `renesas.com` is blocked by this session's egress proxy (retried and refused
   at the proxy, not by the site), no mirror carries Intersil application notes, and the other
   "AN1910" hits are NXP's and Microchip's unrelated documents of the same number. **Both things
   they were wanted for are settled without them**: the 12-bit cycle time derives from p6's own
   *"internal oscillator and the n-bit (n = 12, 16) counter"* statement (§7.2), and the CCT
   matrix cannot come from a vendor note at all, since p13 says the coefficients *"will be
   changed respectively depending on the system setup"* (§7.11, §8.3). Downgraded from a gate to
   a nice-to-have.
7. **`fram=`.** `SensorReaderConfig.__init__`'s own parameter is spelled `fram`
   (`base_classes.py:157`, `:252`); BMP3xx and SCD30 pass `fram=`; `SGP40_Reader` is 1 of 4 and
   forwards it as `fram=fram_storage` (`asy_sgp40_driver.py:85`), so even the outlier reaches the
   base class under the majority spelling. `SGP40_Reader` keeps its own spelling; nothing in
   `src/` changes.
8. **No dev leg for the twin CI suite, not in this promotion.**
   `scripts/_digital_twin_ci_suite.py` names `run_wozi_integration.py` in seven places, including
   its subprocess command line, its banner matching and its SIGINT handling — parametrising it is
   a harness rewrite, not a flag. The dev runner plus
   `tests/test_digital_twin_run_dev_integration.py` cover the same ground for this sensor. Record
   the asymmetry in `BACKLOG.md` at promotion time, because the next dev-only device inherits the
   hole.
9. **The measurement field is `RangeAct`** (§8.4), its meaning pinned to "the range the *reported
   sample* was taken on" — which is what the sample-carried range in the results tuple makes
   available. The config field keeps `Range`.

Closed earlier and recorded so they are not reopened: `CCT` is in (requirement 13); the
auto-range tuning surface is settled and the rejected knobs are listed with reasons (§8.3); the
INT pull-up is resolved — present on the dev board, confirmed by the project owner and
corroborated by SparkFun's schematic, with `Pin.PULL_UP` enabled by default regardless (§7.12);
the config-field naming question is closed as a *rule* (device prefix marks a command, not a
setting — §8.3), so `SGPResetVOC` stays as it is and needs no decision; the IR-compensation
default is 40 codes with `B7` = 0 (§6, §7.9); whether `CONVEN` fires per channel or per cycle is
moot since `CONVEN` stays 0 (§7.6); and the `CONFIG1` read-modify-write hazard is designed out
rather than mitigated (§8.7).

## 14. Quality bar — what "done" means for this driver

Four standards, set by the project owner:

> Fully according to the specification document · fully according to general project practice,
> style, patterns and guidelines · an integral part, looking like the other sensor drivers look,
> all made of the same material, nothing missing or contradicting · same naming, coding and
> implementation conventions.

The first two are **written down** and this section points at them rather than restating them —
a copy would drift. The second two are mostly **not** written down: they live in the three drivers
already in `src/`, and a new file fails them by omission, not by contradiction. So §14.3 is the
substance here — the conventions all three drivers follow that no document states, each with the
evidence that it is a convention rather than a coincidence.

### 14.1 The written standards, and what each governs

| Where | Governs | What it demands here |
|---|---|---|
| `SPECIFICATION.md` Part C.1-C.13 | The shape of a sensor driver | The whole file. C.2 naming, C.3 the protocol layer, C.4 the reader layer, C.5 the schema, C.7 errors, C.8 locking, C.9 timer/task/IRQ, C.10 typing, C.11 the nine decisions, C.13 the readiness gate |
| Part D.0-D.16 | The promotion gate | Every item, in order. **D.16 is literally "move the file into `src/`, only once all of the above is actually done and passing"** — the file does not land first and get fixed after |
| Part E.1-E.6 | Testing | Real MicroPython Unix port, `tests/microtest.py`, mock only the raw bus transaction (E.4) |
| Part G.1-G.3 | Shared primitives | Check the G.2 catalogue **before** writing any helper; extend the catalogue rather than duplicate (§7.8's EMA filter is the concrete case) |
| Part H.5/H.6 | The website | The definitions file is the only place the site learns about a sensor |
| Part I | Memory safety | catch → degrade → restart → watchdog; `gc`-default-first for any new stress test |
| Part F | Platform facts | Read before any platform-facing claim; do not re-derive from general Python knowledge |
| `CLAUDE.md` hard rules | Everything else | The 3-line docstring cap, four-tier bus-hazard coverage, the bird's-eye `src/` scan on every new file, "report a discrepancy, do not silently fix it", no `method-assign` suppression in `src/` |

Two of these have teeth beyond a review comment: `scripts/lint.sh` fails the gate on a
`# type: ignore[method-assign]` anywhere in `src/`, and `ruff` runs `select = ["ALL"]` with the
project's exceptions — so a convention nobody notices in review still stops the build.

### 14.2 Acceptance checklist, bound to this driver

Checkable, not aspirational. Each line is either true of the finished file or it is not.

1. `src/asy_isl29125_driver.py` holds **three classes**: `ISL29125_Reader(SensorReaderConfig)`,
   `ISL29125_DeviceSession(Lockable)`, `ISL29125_I2C`. The middle one is copied verbatim from
   C.2's snippet — it is boilerplate, not a design surface. *(The plan named the first and third
   but never the second; C.2 requires it and all three drivers have one.)*
2. `_NAME = const("ISL29125")` and `namedtuple("ISL29125", …)` carry the **identical** string,
   defined next to each other (C.2 makes this a "must, always").
3. Every config field is a `_VAL_<ABBREV>` 6-tuple; every `errno`/`wrnno` is registered in Part
   C.7.1's table before the code is written, not after.
4. The reader raises nothing. The protocol layer may raise; every call into it from the reader is
   wrapped and logged through `err_s()`/`wrn_s()` — never a bare `except Exception: return None`
   (C.7).
5. `_error_check()` is called exactly once per `read_loop()` cycle, and the auto-range machinery
   does **not** invent a second failure counter beside it.
6. No new shared helper exists that Part G.2 already names. The colour maths and the EMA filter
   are the two candidates, and §14.4 decides where each goes.
7. `mypy --strict` and `ruff` report **zero** findings on the file, with no per-file ignore beyond
   the `FBT001` row the other three drivers already carry (and only if it actually takes a boolean
   positional).
8. The four-tier bus-hazard coverage exists (mock, twin, flash, bench) — CLAUDE.md's standing rule,
   not a nice-to-have.
9. The bird's-eye scan over all of `src/` has been run and its findings reported, not silently
   fixed.

### 14.3 Conventions all three drivers follow that no document states

Found by reading `asy_bmp3xx_driver.py`, `asy_scd30_driver.py` and `asy_sgp40_driver.py` end to
end and diffing their structure. Each row records how many of the three follow it — 3/3 is a
convention, 2/3 needs a reason.

| # | Convention | Evidence | This driver |
|---|---|---|---|
| 1 | **File section order is fixed**: SPDX block → module docstring → stdlib imports → `machine`/`micropython` → project imports → the `typing` guard → `if TYPE_CHECKING:` → chip constants → `_VAL_*` → `_N_*` → `_NAME` → namedtuple + `_FIELDS` → classes | 3/3 | follow exactly |
| 2 | **The `_Reader` class comes first in the file, before `_DeviceSession` and `_I2C`** — layer 3 before layer 2, the reverse of the layer numbering | 3/3 (reader at line 98/93/67, protocol at 378/428/449) | follow — this one reads like a mistake if you do not know it is deliberate |
| 3 | **An SPDX two-line copyright block sits *above* the module docstring** for any file derived from third-party code, naming the original and pointing at `THIRD_PARTY_LICENSES.md` | 3/3, all Adafruit-derived | **required, and the plan had not mentioned it**: upstream here is `jposada202020/MicroPython_ISL29125`, MIT, © 2023 Jose D. Montoya. `SPDX-FileCopyrightText` + `SPDX-License-Identifier: MIT` |
| 4 | **The module docstring is a 3-line template**: (1) what the chip is and what this driver does, (2) the two class names and their roles + "see SPECIFICATION.md Part C", (3) "Verified against …" naming the datasheet under `datasheets/` | 3/3 | follow; line 3 cites `datasheets/isl29125/REN_isl29125_DST_20151201_1.pdf`, FN8424 Rev 3.00 |
| 5 | **`_FIELDS` duplicates the namedtuple's field names as a `const`**, with the comment *"kept in sync with `<X>`'s own fields above"* — because mypy's namedtuple plugin only infers field names from a literal at the call site, so the tuple cannot be factored out | 3/3, identical comment wording | follow, with the ten-field tuple of §8.4 |
| 6 | **`_VAL_<ABBREV>` uses the initials of the field name** (`SampleInterv`→`SI`, `SeaLevelOffs`→`SLO`, `BackupMaxAge`→`BMAX`) | 3/3, 18 fields | see §14.4 — this one **breaks** here |
| 7 | **`_N_<THING>_CFG = const(n)`** names the expected length of every batched `get_*_values()` read, so the batch and its unpack cannot drift | 3/3 (`_N_INT_CFG`, `_N_FLOAT_CFG`, `_N_STORAGE_CFG`, `_N_SETUP_CFG`) | follow |
| 8 | **`_init_<abbr>()` / `_read_<abbr>()` / `_store_<abbr>()`** is the reader's internal triple, `<abbr>` being the chip's 3-letter short name | 3/3 (`bmp`/`scd`/`sgp`) | `_init_isl()` / `_read_isl()` / `_store_isl()` |
| 9 | **`self.<abbr>` holds the protocol object on the reader; `self.i2c_<fullname>` holds the device session inside the protocol class** | 3/3 (`self.bmp` + `self.i2c_bmp3xx`, `self.scd`, `self.sgp` + `self.i2c_sgp40`) | `self.isl` and `self.i2c_isl29125` |
| 10 | **Nested `async with` for a multi-transaction sequence**: `async with self.i2c_<x> as <x>, <x>.i2c_device as i2c:` — device session first, bus second | 3/3 | follow; the burst read and the three-byte config burst each need it |
| 11 | **Live config readback is one batched `get_config_snapshot()` on the protocol class, called by `_read_sensor_dict()` on the reader**, which is then passed as `get_dict_cfg(callback=…)`. Explicitly *not* three independent `get_*()` calls — BMP3xx's own comment records that the naive version had a torn-read window | 2/3 (SGP40 has no chip-side config at all, C.4.4) | **follow** — the ISL's config *is* chip registers, and the shadow-byte model of §8.7 makes the snapshot almost free |
| 12 | **`async def setup()` on the protocol class**, plus `reset()` where the chip has one | 3/3 setup, 2/3 reset | both — the ISL has a real reset (`0x46`→`0x00`) |
| 13 | **Every chip constant carries a datasheet citation as a trailing comment** (`# datasheet sec 4.3.2`, `# Table 13, high byte only`) | 3/3 | follow; §2's conformance table already has the page/table for every register |
| 14 | **Pure, reusable physical maths lives in `math_helpers.py`**, with `float \| None` in and out, a `_<NAME>_MIN`/`_MAX` domain-constant pair per function, and the domain's source cited | 2/3 import it; SGP40's two chip-specific tick conversions stay local as `@staticmethod` | see §14.4 |

### 14.4 Where this driver has no precedent, and the rule chosen for each

Five places where "look at how the others did it" returns nothing, because this is the first
driver of its kind in the project. Each needs a decision made deliberately rather than by default.

1. **`_VAL_` abbreviations collide.** Thirteen config fields against BMP3xx's eight, and five of
   them start `AutoRange` — `AutoRangeUp`/`AutoRangeDown`/`AutoRangeSettle`/`AutoRangePersist`/
   `AutoRangeDwell` all reduce to `AR*` under convention 6, and `AutoRangeDown` vs `AutoRangeDwell`
   collide outright at `ARD`. **Rule**: keep the initials scheme for the **eight** non-auto-range
   fields, and give the auto-range five a `_VAL_AR_<WORD>` form (`_VAL_AR_UP`, `_VAL_AR_DOWN`,
   `_VAL_AR_SETTLE`, `_VAL_AR_PERSIST`, `_VAL_AR_DWELL`). It reads as the same scheme with one
   extra level, which is what a reader of the other three files would expect, and it groups the
   batch that is always read together.
   **Three of those eight are abbreviations rather than initials, and that is deliberate**:
   `Resolution`, `Range` and `RangeAuto` all reduce to `R`/`RA`, so the function spec's §0.3 fixes
   them as `_VAL_RES`, `_VAL_RNG` and `_VAL_RA`, with `_VAL_RESETCAL` spelled out because
   `ISLResetCal` initials to `IRC` — one character from `IrComp`'s `_VAL_ICO`/`_VAL_ICA`. Recorded
   here so the deviation is a decision rather than a reviewer's finding: convention 6 is followed
   where it discriminates and abbreviated where it does not.
2. **Colour maths has no home yet.** RGB→HSB, RGB→XYZ→xy and McCamy's CCT cubic are pure,
   total, reusable functions over floats — exactly the shape of `wet_bulb_temperature()` and
   `dew_point()`. **Rule**: they go in `math_helpers.py`, `float | None` in and out, with
   `_CCT_X_MIN`-style domain constants and the source cited per D.1 (CIE 1931 for the matrix,
   McCamy 1992 for the cubic). The chip-specific parts — count-to-lux scaling, the 12-bit `<<4`
   normalisation — stay in the driver, mirroring how SGP40 keeps `_celsius_to_ticks()` local.
   This also makes them unit-testable without a bus, which the D.12 matrix needs.
3. **First falling-edge interrupt.** SCD30's RDY is rising-only; the ISL's INT is active-low
   open-drain. Both fakes already define `IRQ_FALLING` and accept `pull=`, so nothing needs
   extending — but `asy_scd30_driver.py` is the shape to copy for the `ThreadSafeFlag` +
   self-healing re-arm, not a new mechanism.
4. **First driver whose measurement output is not flat.** Nothing in `src/` returns a nested
   measurement dict today. **Rule**: the nesting stops at the transport boundary — the namedtuple
   stays flat (§8.4), `make_dict()` keeps its one-level contract, and the nesting is built where
   the response is shaped. Anything else would make this driver's data model a special case in
   `base_classes.py`, which D.10 forbids.
5. **First permanent divergence between the two variants.** Covered in §11.1/§11.13: dev reaches
   nine FRAM chunks while wozi stays at seven. **Rule**: the divergence is documented in the same
   commit that creates it — `SPECIFICATION.md`'s new dev section, `sensortask_dev.py`'s own
   comment, and the renamed chunk-order test — never left to be inferred from the code.

### 14.5 How it is verified, and against what baseline

Not "it looks right". D.14 requires the commands actually run and the output read:

- `scripts/lint.sh` and `scripts/typecheck.sh` — all three mypy passes — must report **zero**
  findings, which is the current state of all eight scopes, so any nonzero result is this work's
  regression and not a pre-existing one.
- `scripts/test.sh` — every test passes under the real Unix-port interpreter, including the
  existing dev-variant assertions §11.7 lists as needing updates. A changed assertion must be
  changed because the *expected* value moved, never to make a failure go away.
- `npm test` for the website tier, including the PUT matrix that now generates real cases for this
  sensor.
- `scripts/run_digital_twin_ci.sh` stays green — it is wozi-only (§11.5), so it is a regression
  check here, not coverage.
- The pre-push chroot verification (both noble and trixie) applies only if the toolchain or build
  configuration is touched; a driver plus its tests does not trigger it.
- **`git diff --stat` against `wozi`'s own files must be empty.** Requirement 18 in a form that
  can actually be checked.

## 15. Status — implemented, pending the project owner's review

Everything this plan calls for is built, and every tier except real hardware is running and
passing: `tests/test_asy_isl29125_driver.py` (147), `tests/test_digital_twin_isl29125.py` (28),
`tests/test_digital_twin_isl29125_autorange.py` (14), plus the updated dev/webserver/bus-hazard/
setter/twin-machine suites and the whole `tests_js` tier. `ruff` and all three `mypy --strict`
passes are clean. The real-hardware tier is **written and registered but never run** — that needs
the project owner's go-ahead in the session that runs it (CLAUDE.md), which this session does not
have.

Where the code ends up differing from the two planning documents — including **three places where
the specification was wrong and would have shipped a real bug** — is recorded in
`ISL29125_FUNCTION_SPEC.md` §9 rather than being edited back into either document in place. Read
that section before this one is retired.

**Both planning documents stay for now.** README's "Further reading" entry says to delete them
when the promotion closes, migrating anything permanent into `SPECIFICATION.md` first. That
migration has happened (Part A.4, A.7.1, C.7.1, C.8, G.2, H.5/H.6, plus `DEVICE_REFERENCE.md`,
`THIRD_PARTY_LICENSES.md` and `README.md`), but the promotion is not closed until the owner has
reviewed it and the real-hardware tier has actually run — so deleting them is the owner's call,
not this session's.

## Datasheet acquisition

`renesas.com`, `intersil.com` and every mirror host (DigiKey, Mouser, AllDataSheet, Arrow, Farnell,
`web.archive.org`) are blocked by the session egress policy, and no reachable GitHub repository
vendors the PDF. The project owner supplied it directly. **AN1910 and AN1914 are still missing**
and would have to be supplied the same way, along with **AN1591** (the ISL290XX evaluation
hardware/software manual) and the standalone Renesas **"ISL29125 CCT calculation"** note found
during the re-scan. AN1910 in particular would settle the 12-bit integration time, which the
datasheet leaves unspecified; the CCT note would replace §7.11's placeholder colour matrix.
