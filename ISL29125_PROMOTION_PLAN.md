# ISL29125 driver promotion — findings

Temporary working doc for the `python/IndividualDrivers/asy_isl29125_driver.py` → `src/`
promotion, following CLAUDE.md's step-session workflow. §1-§5 are the audit of the existing driver
against the real datasheet; §6 records the requirements the project owner has since settled, §7-§9
the design notes written against them, §10 the bench rig, and §12 the questions still open.
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
is ~6.3 ms (derived — only the 16-bit figure is specified; AN1910 would confirm) and is a multiple
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
ratio is one float in a FRAM chunk, not a config field, and **`ResetRangeCal`** is the command-only
bool that throws it away and relearns from nominal. §8.3 spells out what conforming to C.5.2.1
actually obliges the driver to do.

Deliberately **no** on/off switch for the learning itself. The ratio is a device constant — it
converges and stays there — not an environmental adaptation that could wander, so "stop learning"
solves nothing that `ResetRangeCal` does not.

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
the anti-chatter mechanism that would otherwise be software. Saturation (65535, clipped) forces an
immediate switch-up without waiting for any filter: react fast to bright, slowly to dark, so a
passing shadow does not cost a range change and a change back. The "slowly to dark" half is
`AutoRangeDwell`, because `PRST` cannot be made asymmetric — §8.3 has the reasoning.

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
samples. What remains inferred is only whether the restart is exact; §4 flags it for bench
confirmation.

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
Since this driver adopts the same command-only-bool pattern for `ResetRangeCal` (§7.3, §8.3), it
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
| `RangeAuto` | bool | True | — | auto vs. fixed range |
| `Range` | int | 10000 | {375, 10000} | `CONFIG1` B3, used when `RangeAuto` is false |
| `AutoRangeUp` | float | 85.0 | 50.0-95.0 % FS | switch-up threshold |
| `AutoRangeDown` | float | **1.5** | **0.2-3.0** % FS | switch-down threshold |
| `AutoRangeSettle` | int | 1 | 1-10 cycles | full cycles waited after a switch |
| `AutoRangePersist` | int | 4 | {1, 2, 4, 8} | `CONFIG3` `PRST` — hardware transient rejection |
| `AutoRangeDwell` | float | 10.0 | 0.0-300.0 s | minimum time on the high range before a switch **down** |
| `ResetRangeCal` | bool | — | command-only | discard the learned gain ratio and relearn (§7.3) |
| `IrCompOffset` | int | 0 | {0, 1} | `CONFIG2` B7 (adds 106) |
| `IrCompAdjust` | int | 40 | 0-63 | `CONFIG2` B5:0 |
| `FiltCoeff` | float | -1.0 | -1.0-1.0 | output EMA; <= 0 disables (legacy SHTC3/MPRLS precedent) |

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
  `ResetRangeCal` covers the only real need.

#### `ResetRangeCal` against the project's own rule for command-only fields

`SPECIFICATION.md` Part C.5.2.1 is prescriptive here, so this is conformance, not a design choice.
Four obligations, all of which the driver has to honour and none of which is obvious from the
schema row alone:

1. **Shape**: `_VAL_RESETCAL = const((("ResetRangeCal", "bool", None, None, None, True),))` — a
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

**Naming.** Unprefixed, per the 29-of-30 majority in `src/` (§8.2) — `_NAME = "ISL29125"` already
namespaces it. `ResetRangeCal` rather than a bare `ResetRangeCal` because §7.11 leaves a second
calibration plausible (a per-unit colour matrix), and `Cal` alone would then say nothing about
which one. It is one character longer than the longest existing field name, which is not a style
break.

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

`namedtuple("ISL29125", ("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "CCT", "Range", "TS"))`

- `Lux` — absolute, green-channel-derived (§7.5).
- `CCT` — relative colour temperature in K, or `None` below the low-light floor (§7.11).
- `Red`/`Green`/`Blue` — **normalised 0-1** over the full span: the fixed range when one is
  selected, the whole auto-range span when auto is on.
- `Hue`/`Sat`/`Bri` — `Bri` follows from RGB being 0-1, so it is 0-1 too. In a dim room that lands
  near 0.003; the project owner has accepted that behaviour, so no log scaling and no low-light
  validity flag.
- **Naming**: in the flat namedtuple HSB's brightness must not be spelled `B` — it would collide
  with blue. `Red`/`Green`/`Blue` + `Hue`/`Sat`/`Bri` keeps both triples unambiguous. The nested
  response body (§8.6) dissolves the collision anyway, so the flat tuple is an internal carrier and
  its names need only be unique, not pretty.
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
              "CCT": <float|null>,
              "Range": <375|10000>,
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
  then `ResetRangeCal` and watch it converge again from nominal.
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

## 11. Known prerequisites and standing obligations

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
  not promoted" to "Restructured/rewritten, attribution retained". One **separate, pre-existing**
  question stays open there: upstream's `i2c_helpers.py` carries an explicit "Based on
  `adafruit_register.i2c_struct`/`i2c_bits`, © 2016 Adafruit Industries, MIT" notice, while
  `src/asy_i2c_driver.py` — which exposes the same four-operation API — carries no attribution at
  all. By the standard already applied to `asy_fram_driver.py` it may warrant a similar note.

## 12. What is still open

Everything else in this doc is settled. These are not.

1. **Does a `CONFIG1` write really restart the conversion cycle?** (§4, Table 7.) The design uses
   it for deterministic settling (§7.6) and avoids periodic re-asserts because of it (§9.3).
   Both remain *safe* if it turns out not to restart — the waits are conservative either way — so
   this gates optimisation, not correctness. Bench check.
2. **Does `PRST` count channel integrations or full RGB cycles?** (§8.3.) Changes
   `AutoRangePersist`'s effective time constant by 3× and nothing else; `AutoRangeDwell` covers the
   down direction regardless. Bench check, or AN1910.
3. **`SGPResetVOC` is the only device-prefixed config field in `src/`** (§8.2). Reported, not
   touched — the project owner decides whether it is a deliberate exception or drift.
4. **AN1910, AN1914, AN1591 and the Renesas "ISL29125 CCT calculation" note are all unobtainable**
   from a session. AN1910 would settle the 12-bit integration time (currently derived, §7.2) and
   question 2 above; the CCT note would replace §7.11's placeholder matrix with the vendor's own.
   Neither blocks the promotion; both would improve it.

Closed during this pass, recorded so they are not reopened: `CCT` is in (requirement 13); the
auto-range tuning surface is settled and the four rejected knobs are listed with reasons (§8.3);
the INT pull-up is resolved — present on the dev board, confirmed by the project owner and
corroborated by SparkFun's schematic, with `Pin.PULL_UP` enabled by default regardless (§7.12); the IR-compensation default is 40 codes with `B7` = 0 (§6, §7.9); whether `CONVEN`
fires per channel or per cycle is moot since `CONVEN` stays 0 (§7.6); and the `CONFIG1`
read-modify-write hazard is designed out rather than mitigated (§8.7).

## Datasheet acquisition

`renesas.com`, `intersil.com` and every mirror host (DigiKey, Mouser, AllDataSheet, Arrow, Farnell,
`web.archive.org`) are blocked by the session egress policy, and no reachable GitHub repository
vendors the PDF. The project owner supplied it directly. **AN1910 and AN1914 are still missing**
and would have to be supplied the same way, along with **AN1591** (the ISL290XX evaluation
hardware/software manual) and the standalone Renesas **"ISL29125 CCT calculation"** note found
during the re-scan. AN1910 in particular would settle the 12-bit integration time, which the
datasheet leaves unspecified; the CCT note would replace §7.11's placeholder colour matrix.
