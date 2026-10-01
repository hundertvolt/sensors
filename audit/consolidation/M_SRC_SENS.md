# A-C merge SRC_SENS (HEAD ff2e004)

Files: `src/asy_spi_driver.py`, `src/asy_i2c_driver.py`, `src/voc_algorithm.py`, `src/asy_neopixel_driver.py`,
`src/asy_notification_service.py`, `src/asy_bmp3xx_driver.py`, `src/asy_scd30_driver.py`, `src/asy_sgp40_driver.py`,
`src/asy_isl29125_driver.py`. Inputs: `site_index.json` (128 actions) plus every action whose Site or Change edits one of
these files without naming it by path (grep of the action files for the file names and for the classes/identifiers they
define; 83 such actions read, of which the ones that edit a site here are merged below and listed in the ledger).

**Conventions used by every merged change below.**
- Names: a merged change landing in U11 or later is written with the names U10 leaves (A.U10.18 `bus_lock`/
  `session_lock`; A.U10.35 private attributes; A.U10.38 class names; A.U10.39/A.U10.40 keys and `_VAL_` names; A.U10.43
  unit suffixes; A.U10.44 starter/loop names; A.U10.37 module names `asy_base_classes`, `asy_config_manager`,
  `asy_crc_checks`, `asy_print_log`). Where a text quoted from an action uses the HEAD name, the post-U10 name applies.
- Member order: A.U10.33 reorders every class to D.15 in U10 (last U10 change per file). Every member a later unit adds
  is inserted at its D.15 position (A.U10.47's convention check keeps it; noted once here, not per change).
- Catalog codes: the numbers are A.U2.01's; each module logs through its own `_ERR_<NAME>`/`_WRN_<NAME>` constants
  (A.U2.04). New shared warning numbers settled here (Resolved in M.SRC_SENS.043): W11 `DERIVED_DOMAIN` (A.U15.24),
  W14 `DEVICE_RECOVERY`, W15 `BUS_RECOVERY` (A.U10.R01); A.U18.15's `SOCKET_TEARDOWN` takes W12.
- Broad handlers: every `except Exception`/`except BaseException` without a closing bare `raise` in these files gains
  `report_if_fatal(e)` as its first statement in U30 (A.U30.19), after every other unit's edit of the same handler —
  one merged change per file, listed last in the file's section.
- Comment cap: every comment block a merged change writes is ≤ 3 prose lines (CLAUDE.md); where constituents' texts
  would exceed it together, the merged text below is the capped one.
- Version stamps: a comment in these files that states a MicroPython fact names the SPECIFICATION.md Part F section,
  not a version number (the version lives in Part F.5, which A.SDEP.08 re-stamps at every pin move).

## src/asy_spi_driver.py

### M.SRC_SENS.001 Module comment: bool contract, raise sites, no stamp
- **From**: A.U13.08 (header), A.SDEP.08 (`:5` "since 1.29" stamp), A.SDEP.17 (W26 re-check of the wrapper comments)
- **Site**: `src/asy_spi_driver.py:4-6` (comment block after the docstring)
- **Change**: stage U0 (A.SDEP.08 (4), A.SDEP.17 W26): the EIO-on-32+-byte-read fact and the `deinit()` fact are
  re-read at the new pin; a changed fact is corrected in F.5/F.5.1 and here, else unchanged. Stage U13 (final text,
  three lines): "# RP2040 SPI has no ACK/NAK. An uninitialized bus is a False return from every transfer, configure()
  and session_begin(), never a raise; a 32+ byte READ can raise OSError(EIO) on an RX overrun and it propagates. Raise
  sites: SPECIFICATION.md Part F.5." (A.U13.08's text with its "(1.29)" stamp dropped per the conventions).
- **Resolved**: A.U13.08's "(1.29)" vs A.SDEP.08's re-stamp — no stamp in code, the version lives in F.5 (conventions;
  CLAUDE.md "Platform target": facts live in Part F).
- **Unit**: U0 (re-check), U13 (text)
- **Depends**: A.SDEP.08; M.SRC_SENS.003
- **Blast carried by**: F.5/F.5.1 re-stamp → A.SDEP.21 (SPEC cluster); comment cap → `tests_scripts/test_comment_block_cap.py` unchanged
- **Kind**: doc

### M.SRC_SENS.002 Tag the CS settle; one standing check for synchronous waits
- **From**: A.U8.19 (`_CS_SETTLE_US` tag, rule rows), AC_NOTES 5 (standing check owed?)
- **Site**: `src/asy_spi_driver.py:17-20`
- **Change**: the constant keeps its comment and value and gains the tag line `# @tunable spi.cs_settle_us = 2`
  (A.U8.01 grammar) directly above `_CS_SETTLE_US = const(2)`. AC_NOTES 5 decision (agent, 2026-10-01): a standing
  guard is owed (OR111.a (2): every rule keeps a guard): `loop.sync_wait_max_us`'s "Checked by" becomes
  `tests_scripts/test_src_sleep_forms.py` (A.U31.19), extended by one case — an AST scan of `src/` fails on any
  `time.sleep`, `time.sleep_ms` or `time.sleep_us` call outside two named exceptions: `asy_spi_driver.py`'s
  `time.sleep_us(_CS_SETTLE_US)` (session begin/end) and `asy_i2c_driver.py`'s boot-time bus clear (M.SRC_SENS.008, a
  bounded synchronous clock-out that runs inside the fed boot batch before any task exists); the code-review lens stays
  in addition. The Part N row's Dependants gain the boot clear with its bound.
- **Resolved**: AC_NOTES 5 asked A-C whether a standing check is owed; settled by OR111.a (2) (every rule keeps a
  guard) — agent decision, listed for the OR2.c review.
- **Unit**: U8 (tag and rows); U31 (the check case, with A.U31.19)
- **Depends**: A.U8.01, A.U31.19
- **Blast carried by**: Part N rows `spi.cs_settle_us`, `loop.sync_wait_max_us` → A.U8.19 (SPEC cluster) plus GAP-1
  (the check case and the boot-clear Dependant, TSC/SPEC); SPEC F.3 sentence → A.U8.19
- **Kind**: code, rule

### M.SRC_SENS.003 `SPI`: bus lock, bool transfers, availability, deinit
- **From**: A.U10.18 (`async_lock` → `bus_lock`), A.U10.17 (lock reason), A.U10.45 (`:66` message), A.U13.08
  (bool returns, `configure()`), A.U13.09 (`available`), A.U13.15 (`configure()` comment), A.U13.16 (`deinit()` bool),
  A.U24.23 (blast only: `firstbit=_SPI.MSB` stays symbolic)
- **Site**: `src/asy_spi_driver.py:33-97` (`SPI`)
- **Change**: end state —
  `__init__`: `self.bus_lock = asyncio.Lock()` with the trailing reason "# serialises the SPI peripheral: every CS
  session holds it" (A.U10.17). `init()` unchanged. `deinit(self) -> bool`: body unchanged plus `return True` on both
  paths; comment (≤ 3 lines) "machine.SPI.deinit() does NOT deactivate the rp2 bus - forwarded for portability, it cannot
  fail at the pinned version (Part F.5.1), so this returns True; dropping self._spi is what makes the wrapper report the
  bus unavailable." New read-only `@property available -> bool: return self._spi is not None` (A.U13.09).
  `configure(...) -> bool`: comment "# Called only from SPIDevice.session_begin() (which __aenter__ also uses), with the
  bus lock held by the caller; an uninitialized bus is a False return (see the module comment)." (A.U13.15); `if not
  self.bus_lock.locked(): raise RuntimeError("acquire the bus lock first")` (A.U10.45's text, A.U10.18's name) stays
  first; `if self._spi is None: return False`; `self._spi.init(...)`; `return True`. The HEAD `RuntimeError("SPI bus not
  initialized - call init() first")` raise goes (A.U13.08). `write() -> bool`, `readinto() -> bool`: `False` when
  `self._spi is None`, `True` after the transfer; the EIO comment on `readinto()` stays. `write_readinto() -> bool`:
  `False` for no bus or the length-mismatch `ValueError`, `True` after a transfer; its comment's "turned into None" →
  "turned into False".
- **Resolved**: A.U13.08 moves the not-initialised check after the lock check ("the lock-not-held `RuntimeError`
  stays (caller error)"): kept in that order. Stage split: A.U10.18's rename lands with its FRAM/UART users in U10.
- **Unit**: stage U10 (`bus_lock` name + reason + the lock message); stage U13 (bool contract, `available`,
  `deinit()`, comments)
- **Depends**: A.U10.17, A.U10.18 (repo-wide rename, U10); A.U13.09's FRAM half (U16 cluster) reads `available`
- **Blast carried by**: `asy_fram_driver.py` users of `async_lock`/transfer returns → A.U10.18, A.U13.09 (SRC_CORE);
  tests `tests/test_asy_spi_driver.py:48-78, 89-122, 151-160, 205-218, 427-440` → A.U13.08/A.U13.16 (TEST_UNIT);
  `tests/test_asy_fram_driver.py:823-842`, `tests/test_asy_fram_manager.py:1409-1436` → A.U13.08/A.U13.09; SPEC C.3
  `:1561-1565` → A.U13.08 (SPEC); C.8 lock names → A.U10.18 (SPEC); four tiers: no wire change (A.U13.08 blast)
- **Kind**: code

### M.SRC_SENS.004 `SPIDevice`: session entry, glitch-free CS, bool, private config
- **From**: A.U10.18 (`asy_lock` kwarg → `session_lock`), A.U13.03 (CS `value=`), A.U13.08 (session/transfer bools),
  A.U10.21 (`setup() -> bool`), A.U10.35 (`cs_active_value`, `polarity`, `bits` private), A.U10.31 (none: the two
  quoted annotations name `TYPE_CHECKING` symbols), A.U10.33 (D.15 order)
- **Site**: `src/asy_spi_driver.py:100-213` (`SPIDevice`)
- **Change**: end state — `__init__`: `super().__init__(session_lock=self.spi.bus_lock)`; the configuration attributes
  are private: `_cs_active_value`, `_baudrate`, `_polarity`, `_phase`, `_bits`, `_firstbit` (A.U10.35's three plus their
  three siblings, see Resolved); `self.cs_pin` → `self._cs_pin`; `self.spi` and `self.initialized` stay public (the FRAM
  driver reads `spi.available`; A.U10.22's gate reads `initialized`). `session_begin() -> bool`: the not-set-up
  `RuntimeError` stays; `if not self.spi.configure(...): return False` before CS is asserted (CS stays inactive); else
  assert, settle, `return True`; the `except BaseException` deassert-and-raise stays. `__aenter__`: calls
  `session_begin()` and ignores its `False` (the session holds the lock and every transfer then returns `False`);
  release-on-raise becomes `self.session_lock.release()`. `setup(self) -> bool`: `self._cs_pin.init(self._cs_pin.OUT,
  value=not self._cs_active_value)` with the comment "# value= sets the level before the pad becomes an output: no CS
  glitch."; `self.initialized = True`; `return True`. `write_sync/readinto_sync/write_readinto_sync` and the async
  `write/readinto/write_readinto` return the bus's `bool`.
- **Resolved**: A.U10.35 privatises three of six sibling configuration attributes (the three tests read); the other
  three (`baudrate`, `phase`, `firstbit`) have no reader outside the class at HEAD (grep over `src/`, `digital_twin/`,
  `tests_hardware/device_scripts/`), so G10/R07 "private by default" and D.10 in-class consistency make all six private
  — agent decision, OR2.c review list. `cs_pin` likewise (no product reader).
- **Unit**: stage U10 (renames, private attributes); stage U13 (bool contract, `value=`, `setup() -> bool`)
- **Depends**: M.SRC_SENS.003; A.U10.18 (`Lockable` param rename in `asy_base_classes.py`, SRC_CORE)
- **Blast carried by**: fakes `tests/machine.py`/`digital_twin/machine.py` `Pin.init(value=)` → A.U13.03 blast (TEST_HELP,
  TWIN: A.U24.16, A.U25.05); new L1 CS-glitch recorder test → A.U13.03 (TEST_UNIT); `test_aenter_…`/`session_begin` tests
  → A.U13.08; readers of the private names in tests → A.U10.35 (TEST_UNIT); co-land `asy_fram_driver.py:395-396` WP pin
  `init(OUT, value=)` → A.U13.03/U16 (SRC_CORE); SPEC C.3 → A.U13.08
- **Kind**: code

### M.SRC_SENS.005 SPI imports follow the module renames
- **From**: A.U10.37 (module renames; its Change covers "every importer")
- **Site**: `src/asy_spi_driver.py:15`
- **Change**: `from base_classes import Lockable` → `from asy_base_classes import Lockable`. The `TYPE_CHECKING` block
  (`Literal`, `Self`) is unchanged. No broad handler needs A.U30.19's call here: both `except BaseException:` blocks end
  in a bare `raise` (A.U30.19 (2)'s exemption).
- **Resolved**: —
- **Unit**: U10
- **Depends**: A.U10.37
- **Blast carried by**: every other importer → A.U10.37 (SRC_CORE)
- **Kind**: code

## src/asy_i2c_driver.py

### M.SRC_SENS.006 Module docstring and comment: one contract, the rungs, no stale list
- **From**: A.U13.07 (comment `:4-6`), A.U13.R01 (6) (one added line), A.U5.14 (the "one difference" note in the
  header), adherence (the docstring's driver list names three of the four I2C drivers)
- **Site**: `src/asy_i2c_driver.py:1-6`
- **Change**: docstring → "Async wrapper around machine.I2C: bus-level primitives (I2C) plus a per-device, lock-scoped
  wrapper (I2CDevice) used by every I2C sensor driver." (the three-name list goes: ISL29125 was missing, and a list of
  users goes stale). Comment block → exactly three lines: "# A non-hardware failure (uninitialized bus, out-of-range
  field, malformed format) is None or False, never a raise; a real OSError propagates, and one-time setup (__init__/
  init(), the probe) may raise. clear()/recover() are the ladder's bus rungs, under the bus lock (SPECIFICATION.md F.2)."
  A.U5.14's "the combined methods take whole buffers" note moves to `writeto_then_readfrom()` (M.SRC_SENS.012).
- **Resolved**: A.U13.07's three-line text plus A.U13.R01's added line plus A.U5.14's note would make a four-to-five-line
  block (CLAUDE.md 3-line cap): merged into the three lines above, A.U5.14's note placed at its method.
- **Unit**: U13
- **Depends**: M.SRC_SENS.010, M.SRC_SENS.012
- **Blast carried by**: comment cap check (`tests_scripts/test_comment_block_cap.py`, unchanged)
- **Kind**: doc

### M.SRC_SENS.007 Imports and module constants: probe settle, clear, status bits
- **From**: A.U10.37 (import), A.U8.13 (`_PROBE_SETTLE_S` tag), A.U31.12 (→ `_PROBE_SETTLE_MS`), A.U13.R01 (2)
  (`_CLEAR_HALF_PERIOD_US`, `_CLEAR_PULSES`, `_REC_*`), A.U14.17 (a) (the boot clear's `time.sleep_us`), adherence
  (LEAD/R24 sequence wrap for `recoveries`, AC_NOTES 17)
- **Site**: `src/asy_i2c_driver.py:8-19`
- **Change**: imports gain `import time`; `from base_classes import Lockable` → `from asy_base_classes import
  COUNTER_CAP, Lockable` (`COUNTER_CAP` is A.U10.01's). Constants after `_SCRATCH_SIZE` (unchanged): `# @tunable
  i2c.probe_settle_ms = 100` / `_PROBE_SETTLE_MS = const(100)`; `# @tunable i2c.clear_half_period_us = 5` /
  `_CLEAR_HALF_PERIOD_US = const(5)` with its comment "# 100 kHz clock-out, the SCD30's ceiling (Interface Description
  p.2)"; `_CLEAR_PULSES = const(9)` "# one byte plus its acknowledge: an I2C protocol constant"; `_DEFAULT_TIMEOUT_US =
  const(50000)` "# rp2's machine.I2C default timeout (Part F.5.1): the SCL-release bound when none is configured";
  the status bits `_REC_SDA_LOW = const(1)`, `_REC_SDA_STUCK = const(2)`, `_REC_SCL_HELD = const(4)`,
  `_REC_NO_CONTROLLER = const(8)` under one comment line "# Bus-recovery status bits returned by clear()/recover() and
  the boot clear (SPECIFICATION.md C.3)".
- **Resolved**: A.U8.13 names `_PROBE_SETTLE_S = const(0.1)`; A.U31.12 renames it to integer milliseconds — the merged
  constant is A.U31.12's (U31's conflict table row 1). `_DEFAULT_TIMEOUT_US` is new here: A.U13.R01 uses rp2's 50,000 µs
  default in two places (boot and runtime clear) — one named constant (OR24 one material).
- **Unit**: stage U8 (tag, as `_PROBE_SETTLE_S`); stage U13 (clear constants, import); stage U31 (ms rename)
- **Depends**: A.U8.01, A.U10.01, A.U10.37
- **Blast carried by**: Part N rows `i2c.probe_settle_ms`, `i2c.clear_half_period_us` → A.U8.13/A.U13.R01 (SPEC);
  F.3 `hold.i2c_probe` → A.U31.01 (SPEC)
- **Kind**: code

### M.SRC_SENS.008 Boot-time bus clear before the controller exists
- **From**: A.U14.17 option (a) (settled by OR113.a (1), AC_NOTES 15), A.U13.R01 (2) (status mask, per-pulse SCL
  wait, `PULL_UP`, `OPEN_DRAIN`)
- **Site**: `src/asy_i2c_driver.py` new module function after the constants (before `class I2C`)
- **Change**: `def _clear_bus(scl_pin: int, sda_pin: int, timeout_us: int) -> int:` — builds `Pin(sda_pin,
  Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)` and `Pin(scl_pin, Pin.OPEN_DRAIN, value=1, pull=Pin.PULL_UP)` (rp2 emulates
  open drain by direction, `ports/rp2/mphalport.h:158-168`; a `Pin()` without `pull` drops the pull-ups,
  `machine_pin.c:299-306`); returns 0 at once if SDA reads high; otherwise sets `_REC_SDA_LOW` and clocks SCL up to
  `_CLEAR_PULSES` times, `time.sleep_us(_CLEAR_HALF_PERIOD_US)` per half period, stopping once SDA reads high; after
  releasing SCL on every pulse and on the STOP's SCL-high it waits for SCL to read high, bounded by `timeout_us`
  (`time.ticks_diff(time.ticks_us(), start) < timeout_us`; a stretched pulse clocks nothing, as MicroPython's own
  soft I2C waits, `extmod/machine_i2c.c:52-65`); SCL still low at the bound → `status | _REC_SCL_HELD`, return; ends
  with a STOP (SDA low while SCL high, then released); SDA still low after the last pulse → `| _REC_SDA_STUCK`. One
  comment (≤ 3 lines): "# Frees a slave holding SDA mid-byte: up to nine SCL pulses then a STOP, before the controller
  owns the pins (owner, 2026-09-30: clear at boot; F.2). Synchronous on purpose: it runs once per bus inside the fed
  boot batch, before any task exists." Allocates only the two `Pin` objects of the call (temporary).
- **Resolved**: A.U14.17 (a) vs its old "never at runtime" head: overtaken by OR113.a (SUPP_recovery conflicts row 1) —
  the runtime clear is `clear()`/`recover()`'s (M.SRC_SENS.010); `_clear_bus()` gains the status mask and the SCL wait
  (row 1). The timeout parameter is added here (A.U13.R01 bounds each wait by "the stored bus timeout", which does not
  exist yet when `__init__` calls this before `init()`).
- **Unit**: U13 (A.U14.17 (a)'s code half co-lands with A.U13.R01 in U13; its F.2 doc half is U14's)
- **Depends**: M.SRC_SENS.007; fakes: `tests/machine.py` `Pin` `OPEN_DRAIN`, scripted input levels, value log (A.U24.16),
  twin `Pin` `OPEN_DRAIN` (A.U25.05)
- **Blast carried by**: construction sites (generated `build_system()`, device scripts constructing
  `asy_i2c_driver.I2C`) → A.U14.17 (a) blast (signature unchanged); L1 pulse cases → A.U13.R01's L1 list (TEST_UNIT);
  SPEC F.2 text → A.U14.R01 (SPEC); DEVICE_REFERENCE operator line → A.U14.17/U36 (DOCS); BACKLOG hardware row →
  A.U14.17 (DOCS); `loop.sync_wait_max_us` Dependant → M.SRC_SENS.002/GAP-1
- **Kind**: code

### M.SRC_SENS.009 `I2C` construction, init and deinit
- **From**: A.U10.18 (`bus_lock`), A.U10.17 (lock reason), A.U13.R01 (1) (`_args`, `recoveries`,
  `_boot_clear_status`), A.U14.17 (a) (boot call), A.U30.21 (1) (scratch view), A.U13.16 (`deinit() -> bool`), A.U14.04
  (DONE-AT-HEAD: `init()` passes no `timeout` it was not given), A.SDEP.08/A.SDEP.17 (`:183` stamp), A.U10.33 (order)
- **Site**: `src/asy_i2c_driver.py:22-37, 163-186`
- **Change**: `__init__` end state, in this order: `self._i2c: _I2C | None = None`; `self.bus_lock = asyncio.Lock()` with
  reason "# serialises the I2C peripheral: every device session on this bus holds it"; the scratch comment (unchanged,
  extended per A.U30.21: "…and one long-lived view of it, so a read slices instead of wrapping") with
  `self._scratch = bytearray(_SCRATCH_SIZE)` and `self._scratch_view = memoryview(self._scratch)`; `self.recoveries = 0`
  (a wrap-by-design sequence, see M.SRC_SENS.010); `self._boot_clear_status = _clear_bus(scl_pin, sda_pin,
  _DEFAULT_TIMEOUT_US if timeout is None else timeout)`; `self.init(port_id, scl_pin, sda_pin, frequency, timeout)`.
  `init()`: first `self._args = (port_id, scl_pin, sda_pin, frequency, timeout)` (a fixed 5-tuple, replaced, never
  grown), then today's body (it never clears; the runtime clear is `clear()`/`recover()`'s). `deinit(self) -> bool`:
  body plus `return True` on both paths; comment (≤ 3 lines) "machine.I2C.deinit() does NOT deactivate the rp2 bus -
  forwarded for portability, it cannot fail at the pinned version (Part F.5.1), so this returns True; dropping self._i2c
  is what makes the wrapper report the bus unavailable." (the HEAD "hard MicroPython 1.29 floor" clause is the F.5.1
  fact the pointer names; A.SDEP.08's U0 re-check reads it there).
- **Resolved**: A.U13.16's comment says "on 1.29"; the conventions put the version in F.5.1.
- **Unit**: stage U10 (`bus_lock` name and reason, with A.U10.18's repo-wide users); stage U13 (the rest); stage U30
  (the scratch view)
- **Depends**: M.SRC_SENS.007, M.SRC_SENS.008; A.U10.18
- **Blast carried by**: `tests/test_asy_i2c_driver.py:40-58, 563-568` (`deinit() is True`) → A.U13.16; tests reading
  `._i2c` identity after a recovery → A.U13.R01; fakes keep per-id state across constructions → A.U24.20/A.U25.03
  (TEST_HELP, TWIN); `tests/test_bus_hazard_multi_device.py`/twin lock names → A.U10.18
- **Kind**: code

### M.SRC_SENS.010 `I2C.clear()`, `recover()` and the boot-clear report
- **From**: A.U13.R01 (3)-(5), adherence (LEAD/R24 counter form for `recoveries`, AC_NOTES 17)
- **Site**: `src/asy_i2c_driver.py` new methods after `init()`/`deinit()` (D.15 position)
- **Change**: as A.U13.R01 (3)-(5) states, with `self.async_lock` read as `self.bus_lock`, and one structural
  precision: a private `async def _clear_locked(self) -> int` performs steps (a) SCL wait (bounded by `self._args[4]` or
  `_DEFAULT_TIMEOUT_US` when `None`, sleeping `asyncio.sleep_ms(1)` against a `time.ticks_diff()` deadline), (b) the
  awaiting pulse/STOP sequence of M.SRC_SENS.008 (same constants and step order), (c) both pins back to
  `Pin(pin, Pin.ALT, pull=Pin.PULL_UP, alt=Pin.ALT_I2C)`, and returns the status; `async def clear(self) -> int` = under
  `async with self.bus_lock:` `status = await self._clear_locked()`, one `recoveries` step, return; `async def
  recover(self) -> int` = under one bus-lock hold `status = await self._clear_locked()`, then `try: self.init(*self._args)`
  `except (OSError, ValueError): status |= _REC_NO_CONTROLLER` (`_i2c` left `None`), one `recoveries` step, return;
  `def take_boot_clear_status(self) -> int` returns `self._boot_clear_status` and zeroes it. Every `recoveries` step is
  the conditional wrap `self.recoveries = self.recoveries + 1 if self.recoveries < COUNTER_CAP else 0` (compared for
  equality only, A.U10.R01), with the trailing comment "# a wrap-by-design sequence: compared for equality only".
- **Resolved**: A.U13.R01 writes `self.recoveries += 1` inside `clear()`'s step (c) and again "once for the whole call"
  in `recover()`, which calls the same body — the step moves out of `_clear_locked()` so each public call steps exactly
  once, as its L1 case requires ("each call increments `recoveries` once"). The unbounded `+= 1` breaks LEAD/R24 (OR103
  "No unbounded counters anywhere"); AC_NOTES 17 fixes the form: conditional wrap at `COUNTER_CAP`.
- **Unit**: U13
- **Depends**: M.SRC_SENS.007-009; A.U10.01 (`COUNTER_CAP`)
- **Blast carried by**: callers `SensorReader._recover_bus()`, `_init_failed()`, `_init_done()` → A.U10.R01 (SRC_CORE);
  L1 clear/recover/boot-status cases (incl. a new one: `recoveries` at `COUNTER_CAP` steps to 0) → A.U13.R01 (TEST_UNIT;
  the wrap case is GAP-2); four-tier coverage of the bus rung → A.U13.R02 (TEST_UNIT, TWIN, HW_DEV, HW_BENCH); fakes
  `ALT`/`ALT_I2C`/`alt=`, per-id state → A.U24.16/A.U24.20/A.U25.03/A.U25.05; SPEC C.3, F.5.1, G.2, Part N →
  A.U13.R01/A.U14.R01 (SPEC)
- **Kind**: code

### M.SRC_SENS.011 Register helpers: one scratch view, bytes/into reads, bool writes
- **From**: A.U30.21 (1) (`_read_into_scratch()` slices the held view), A.U13.02 (doc-only: I.2 figure; no code),
  A.U13.10 (`get_register_bytes()`), A.U30.07 (1) (`get_register_into()`), A.U13.07 (`set_bits()`/
  `set_register_struct()` → bool), A.U10.45 (`:159` except order), A.U10.31 (`:49` quoted annotation)
- **Site**: `src/asy_i2c_driver.py:39-161`
- **Change**: `_bytes_to_int(mem_value: bytes | memoryview, …)` unquoted. `_read_into_scratch()`: `view =
  self._scratch_view[:nbytes]` when `nbytes <= _SCRATCH_SIZE`, else `memoryview(bytearray(nbytes))[:nbytes]` (the
  oversized fallback, unchanged in effect); its comment keeps "valid only until the next read on this bus". New
  `get_register_bytes(self, address, reg_addr, length, addrsize=None) -> bytes | None` after `get_register_struct()`:
  `None` for no bus or `length <= 0`, else `bytes(self._read_into_scratch(self._i2c, address, reg_addr, length,
  addrsize))`. New `get_register_into(self, address, reg_addr, buf, addrsize=None) -> bool` beside it: `False` for no bus
  or `len(buf) == 0`, else `readfrom_mem_into(address, reg_addr, buf[, addrsize=])` straight into `buf` and `True`; a
  bus `OSError` propagates from both. `set_bits() -> bool`: `False` for no bus or an out-of-range field, `True` after
  `_writeto_mem()`. `set_register_struct() -> bool`: `False` for no bus or a pack failure (`except (TypeError,
  ValueError)`, alphabetical), `True` after the write. `get_bits()`/`get_register_struct()` unchanged (`None` contract).
- **Resolved**: A.U13.10 and A.U30.07 add sibling helpers and A.U30.21 changes the one they share (U30 cross-unit note
  6): one change, order-independent. After A.U30.07, `get_register_bytes()` serves four driver sites (BMP3XX
  `_read_register()`, ISL29125 `_read_byte()`, `get_config_snapshot()`, `reset()`); its per-call `bytes` copy is a
  temporary, accepted by OR110.a (3).
- **Unit**: U30 (the latest; A.U13.07/A.U13.10's parts may land in U13 as stage 1 if U15's driver changes need them first
  — they do: the driver sites (M.SRC_SENS.048, M.SRC_SENS.086) call `get_register_bytes()` and test the bool; stage U13 = A.U13.07 + A.U13.10 +
  A.U10.45 + A.U10.31, stage U30 = A.U30.07 + A.U30.21)
- **Depends**: M.SRC_SENS.009 (the view)
- **Blast carried by**: driver call sites → M.SRC_SENS.048 (BMP3XX), M.SRC_SENS.057 (SCD30),
  M.SRC_SENS.068/069 (SGP40), M.SRC_SENS.086 (ISL29125); tests
  `tests/test_asy_i2c_driver.py` bool/`None` asserts and new helper cases → A.U13.07/A.U13.10/A.U30.07/A.U30.21
  (TEST_UNIT); I.2 rows and A.U13.02's sentence (as amended by A.U30.21) → A.U30.02/A.U13.02 (SPEC); SPEC G.2 I2C entry →
  A.U13.01/A.U13.10/A.U30.07 (SPEC); four tiers wire-identical → A.U13.10/A.U30.07/A.U30.21 blasts
- **Kind**: code

### M.SRC_SENS.012 Transfers: bool results, whole-buffer fast path, no range params
- **From**: A.U13.07 (`readfrom_into()`/`writeto_then_readfrom()` → bool), A.U30.21 (2) (whole-buffer fast path),
  A.U5.14 (drop `out_start`/`out_end`/`in_start`/`in_end`)
- **Site**: `src/asy_i2c_driver.py:194-250`
- **Change**: `readfrom_into(...) -> bool`: `False` when `self._i2c is None`; the buffer is passed as it is when
  `start == 0 and end in (None, len(buf))`, else `memoryview(buf)[start:end]`; `True` after the transfer. `writeto()`
  keeps its `int | None` return and gains the same whole-buffer fast path (a `str` input is converted to `bytes` first,
  as today). `writeto_then_readfrom(self, address, buffer_out, buffer_in, *, out_stop=True, in_stop=True) -> bool`:
  `return self.writeto(address, buffer_out, stop=out_stop) is not None and self.readfrom_into(address, buffer_in,
  stop=in_stop)`; comment (≤ 3 lines) keeps the repeated-start sentence and gains "The combined form takes whole
  buffers; pass a memoryview slice for a region (Part G.2 buffer handoff)."
- **Resolved**: —
- **Unit**: stage U5 (A.U5.14 signature); stage U13 (bool); stage U30 (fast path)
- **Depends**: M.SRC_SENS.009
- **Blast carried by**: tests `tests/test_asy_i2c_driver.py:69-98, 140, 417, 479-490, 571-586, 993` → A.U13.07; the nine
  calls passing no range → A.U5.14 (unchanged); identity/partial-view L1 → A.U30.21; driver callers of `readinto`/
  `write` → M.SRC_SENS.013
- **Kind**: code

### M.SRC_SENS.013 `I2CDevice`: session lock, probe setup, bool forwarders
- **From**: A.U10.18 (`asy_lock` kwarg → `session_lock`), A.U10.21 (`setup(self) -> bool`, `probe` goes), A.U8.13 +
  A.U31.12 (probe settle), A.U10.45 (`:269` message), A.U13.07 (forwarders return the bus bool; `write()` → bool),
  A.U13.10 + A.U30.07 (forwarders), A.U5.14 (`write_then_readinto()` signature), A.U10.33 (order)
- **Site**: `src/asy_i2c_driver.py:253-368`
- **Change**: `__init__`: `super().__init__(session_lock=self.i2c.bus_lock)`; comment unchanged. `_probe_for_device()`:
  `await asyncio.sleep_ms(_PROBE_SETTLE_MS)` before and in the `finally`; `raise ValueError(f"no I2C device at address:
  {self.device_address:#x}") from None`; `raise RuntimeError("I2C bus not initialized")` unchanged. `setup(self) ->
  bool`: `await self._probe_for_device()`; `return True` (the probe's raise stays the documented setup raise, A.U10.21).
  New forwarders `get_register_bytes(reg_addr, length, addrsize=None) -> bytes | None` and `get_register_into(reg_addr,
  buf, addrsize=None) -> bool` (as `get_register_struct()` forwards). `set_bits()`, `set_register_struct()`,
  `readinto()`, `write_then_readinto()` return the bus method's `bool`; `write()` returns `self.i2c.writeto(...) is not
  None`. `write_then_readinto(self, buffer_out, buffer_in, *, out_stop=True, in_stop=True) -> bool`.
- **Resolved**: —
- **Unit**: stage U5 (signature); stage U10 (lock kwarg, message); stage U13 (bools, `setup()`, `get_register_bytes()`);
  stage U30 (`get_register_into()`); stage U31 (ms settle)
- **Depends**: M.SRC_SENS.011, M.SRC_SENS.012; A.U10.18 (`Lockable` param)
- **Blast carried by**: device scripts and tests calling `setup(probe=…)` (none at HEAD, A.U10.21 grep); message
  asserts (`"No I2C device"`) → A.U10.45 (TEST_UNIT, HW_DEV grep); driver callers → M.SRC_SENS.048, M.SRC_SENS.057,
  M.SRC_SENS.068, M.SRC_SENS.069, M.SRC_SENS.086
- **Kind**: code

## src/voc_algorithm.py

### M.SRC_SENS.014 Module docstring names the reachable reference
- **From**: A.U12.15 (docstring), A.U34.04 (blast: `:1-3` header unchanged), A.U34.07 (blast: the file already has
  the SPDX order), A.U36.542 (its catalog names the file's Sensirion casing as the named exception — no code edit)
- **Site**: `src/voc_algorithm.py:5-8`
- **Change**: docstring → A.U12.15's three lines verbatim ("Sensirion's VOC Index algorithm (fixed-point Q16.16), a
  literal port of DFRobot's Python translation of the archived Sensirion/embedded-sgp C source; its successor is
  Sensirion/gas-index-algorithm (name map and differences: SPECIFICATION.md Part F.4). Every method returns a value,
  never raises."). The SPDX lines `:1-3` stay as they are.
- **Resolved**: —
- **Unit**: U12
- **Depends**: A.U12.12, A.U12.13 (F.4 states their results)
- **Blast carried by**: SPEC F.4 text (name map, provenance of the constant-for-constant check, the 16383 deviation) →
  A.U12.15 (SPEC); SPEC C.2 `:1510-1511` tag → A.U0.40 (SPEC); THIRD_PARTY_LICENSES entry → A.U34.04 (DOCS)
- **Kind**: doc

### M.SRC_SENS.015 Constants: int32 sentinels, small-int uptime limit
- **From**: A.U12.11 (`_FIX16_MINIMUM`/`_FIX16_OVERFLOW`), A.U12.13 (`…__FIX16_MAX`)
- **Site**: `src/voc_algorithm.py:40-43`
- **Change**: `_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX = const(16383)` preceded by A.U12.13's three-line
  comment ("# 16383, not the C reference's 32767: keeps both uptime counters below rp2's small-int limit (F16(16382) <
  2**30). Both feed only sigmoids that are constant from 10223 s, so the output is unchanged (agent, 2026-09-29).");
  `_FIX16_MINIMUM = const(-0x80000000)` and `_FIX16_OVERFLOW = const(-0x80000000)` with one comment line "# INT32_MIN,
  as the C fix16_t reads 0x80000000". `_FIX16_MAXIMUM`, `_FIX16_ONE`, `_FIX16_FRACTION_MAX` unchanged.
- **Resolved**: —
- **Unit**: U12
- **Depends**: —
- **Blast carried by**: A.U10.05's counter check exemptions and the uptime assertion → A.U12.13 blast into A.U10.05 (TSC);
  `tests/test_voc_algorithm.py:338-383` expectations → A.U12.11 (TEST_UNIT); SPEC F.4 → A.U12.15
- **Kind**: code

### M.SRC_SENS.016 Fix16 helpers wrap to int32 as the C `fix16_t`
- **From**: A.U12.11
- **Site**: `src/voc_algorithm.py:210-317` (`_fix16_mul`, `_fix16_div`, `_fix16_sqrt`, `_fix16_exp`) and a new
  module-level function
- **Change**: exactly A.U12.11's Change: new module-level `def _int32(value: int) -> int:` (in-range test first, then
  mask and sign) with its comment "C's fix16_t is int32: every helper takes and returns it wrapped (agent,
  2026-09-29)."; each helper wraps its inputs (`inarg0 = _int32(int(inarg0))` …); `_fix16_mul` returns `_int32(result)`;
  `_fix16_div`'s `bit <<= 1` → `bit = (bit << 1) & 0xFFFFFFFF` and `result = _int32(quotient)` before the sign step;
  `_fix16_sqrt`/`_fix16_exp` wrap their input. Operation order and names unchanged (the literal-port rule).
- **Resolved**: OR109.a (1) accepts per-sample temporary heap ints; `_int32()`'s masking path allocates only for an
  out-of-range value (a temporary) — nothing survives a sample (OR110.a (1)).
- **Unit**: U12
- **Depends**: M.SRC_SENS.015
- **Blast carried by**: reference vectors and L1 cases → A.U12.11/A.U12.12 (TEST_UNIT); release-note line (OR101.a) →
  A.U12.11 via U37 (DOCS)
- **Kind**: code

### M.SRC_SENS.017 Persisted state: `"<32q"`, range-checked restore, narrow handlers
- **From**: A.U12.14 (format, range check, clamp, comment), A.U11.09 (the same `"<"` at `:141`; the VOC half is
  A.U12.14's by its own text), A.U0.41 (`pack_into` owner-tag comment), A.U30.19 (the two `except Exception:` handlers)
- **Site**: `src/voc_algorithm.py:95-176` (`DFRobot_vocalgorithmParams.pack_into()`, `unpack_from()`)
- **Change**: `pack_into()`: first line a comment "# Every field is frozen, the uptime_gamma/uptime_gating learning
  counters included (owner-confirmed, 2026-07-21)"; format `"<32q"`; handler `except (OverflowError, TypeError,
  ValueError): return False` (see Resolved). `unpack_from()`: format `"<32q"`; handler `except (MemoryError, TypeError,
  ValueError): return False`; then A.U12.14's `for value in values: if not -0x80000000 <= value <= 0x7FFFFFFF: return
  False` before the assignment, the unchanged 32-name assignment, then the two uptime fields `= min(field, limit)` with
  `limit = (_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX - _VOCALGORITHM_SAMPLING_INTERVAL) * _FIX16_ONE`; one comment
  line "# Restored values must be int32 like the C state; uptimes above the small-int limit (an older build's backup)
  are clamped."
- **Resolved**: A.U30.19 requires `report_if_fatal(e)` as the first statement of every broad handler, which would make
  this pure algorithm module import `asy_base_classes` — no other ALGO module does (`math_helpers.py`, `crc_checks.py`
  catch named exception tuples only, D.10 one material). The two handlers are narrowed to the exceptions `struct`
  raises for these calls (a wrong or short buffer; `MemoryError` for the unpack's result tuple, which has a real
  alternative flow — a failed restore starts fresh, SPEC I.4(a) criterion as A.U30.01 states it); a stack-exhaustion
  `RuntimeError` then propagates to the SGP40 read path, whose broad handler records it (A.U30.19's goal holds). Agent
  decision, 2026-10-01, OR2.c review list.
- **Unit**: U12 (A.U12.14, A.U11.09, A.U0.41's comment); the narrowing lands with A.U30.19 in U30 as stage 2
- **Depends**: M.SRC_SENS.015; A.U12.11, A.U12.12 (field-range test sequence)
- **Blast carried by**: `tests/test_voc_algorithm.py:52` (`"<32q"`), new L1 range/clamp/byte-order/field-range cases →
  A.U12.14 (TEST_UNIT); `tests/test_asy_sgp40_driver.py:2262-2265` comment → A.U12.14; A.U30.19's L0
  `tests_scripts/test_fatal_report_sites.py` sees no broad handler here (none remain) → A.U30.19 (TSC); SPEC G3/R12
  layout text → U16 (SPEC)
- **Kind**: code

### M.SRC_SENS.018 The literal port keeps its member order
- **From**: A.U10.33 (lists `voc_algorithm.py:55 DFRobot_vocalgorithmParams` and `:181 VOCAlgorithm` "only if U12's
  literal-port verdict, G3/R10, allows reordering a Sensirion port")
- **Site**: `src/voc_algorithm.py:55, :181`
- **Change**: none — the two classes are not reordered.
- **Resolved**: G3/R10 as A.U12.15 records it: the port traces its reference 1:1 ("literal-port rule … the named
  exception to the Adafruit rule", agent, 2026-07-21); a D.15 reorder would break the operation-order diff against
  the C source that A.U12.12's vectors and A.U12.15's F.4 text rely on. A.U10.33's condition is therefore not met.
- **Unit**: U10 (no edit)
- **Depends**: —
- **Blast carried by**: A.U10.47's convention check must exempt this file from the D.15 order rule, as it exempts its
  casing → GAP-3 (TSC)
- **Kind**: rule

## src/asy_neopixel_driver.py

### M.SRC_SENS.019 Module docstring and comment: current arbitration, owner tag, no history
- **From**: A.U9.02 (header line 2), A.U0.39 (`:5` owner tag, L04), adherence (docstring line 3 "Promoted from
  improved-quality/neopixel_signal.py … (see CLAUDE.md/BACKLOG.md)": history in permanent text and a pointer to no
  existing text — CLAUDE.md working agreement "docs hold current state", G9/R12)
- **Site**: `src/asy_neopixel_driver.py:1-6`
- **Change**: docstring → "Pure NeoPixel LED hardware service: overlay switch/toggle, a dimmed ramp-up/ramp-down
  signal, and internal (`request_signal()`, waits for a running signal up to a deadline) / external (`led_signal()`,
  refused at once while a signal is queued or running) arbitration for the one shared physical pixel." (line 3 goes).
  Comment → "# No config schema (owner, 2026-08-05). Also satisfies the WiFi service's LEDControl Protocol via `on()`/
  `off()`/`toggle()`." (the file name pointer `asy_wifi_service.py's` becomes the service name, which survives
  A.U10.38's rename).
- **Resolved**: —
- **Unit**: U9 (A.U9.02's header text); the owner tag and the history removal land with it (A.U0.39 is a U0 comment
  edit on the same line; merged into U9's text — the tag is in the U9 text from the start)
- **Depends**: M.SRC_SENS.026
- **Blast carried by**: — (comments only; comment cap unchanged)
- **Kind**: doc

### M.SRC_SENS.020 Imports and typing names
- **From**: A.U10.37 (`print_log` → `asy_print_log`), A.U5.01/A.U5.02 (`LogConfig`, `DEFAULT_LOG`), A.U22.04 (`Any`,
  `Callable` out; `TaskStarter`/`ErrorSource` in), A.U10.38 (`AsyFramManager` → `FRAMManager`), A.U9.04 (`import time`)
- **Site**: `src/asy_neopixel_driver.py:8-26`
- **Change**: runtime imports `import asyncio`, `import time`, `import neopixel`, `from machine import Pin`, `from
  micropython import const`, `from asy_print_log import DEFAULT_LOG, LogConfig, PrintLogHistory, make_logger`.
  `TYPE_CHECKING` block: `from asy_base_classes import ErrorSource, TaskStarter, TimerStarter` and `from asy_print_log import
  ErrorLog`; the `Callable`, `Any` and `AsyFramManager` imports go (no parameter names the FRAM manager after A.U5.02).
- **Resolved**: —
- **Unit**: U22 (A.U22.04's typing is the latest; A.U10.37/A.U5.02's import edits land in their units as stages: U5
  `LogConfig`; U10 module name; U22 typing)
- **Depends**: A.U10.46 (aliases), A.U5.01
- **Blast carried by**: `pyproject.toml` baseline list → A.U22.04/A.U8.24 (TOOL)
- **Kind**: code

### M.SRC_SENS.021 Module constants, tags and the wiring tag
- **From**: A.U8.12 (`led.min_signal_s`, `led.refresh_hz_default`, `led.overlay_brightness_default`), A.U17.27
  (`_NEOPIXEL_FREQ_HZ`, `_LED_OVERL_BRI`), A.U9.06 (`_MAX_SIGNAL_S`), A.U9.04 (`_SIGNAL_WAIT_MS`, tag
  `led.signal_wait_ms`), A.U9.07 (dropped: superseded by A.U17.27, its own Depends), A.U5.03 (`@wiring` target `log`),
  A.U10.38 (`FRAMManager` in the tag)
- **Site**: `src/asy_neopixel_driver.py:28-33`
- **Change**: in order: `_NAME = const("NEOPIXEL")`; `# @tunable led.min_signal_s = 0.1` / `_MIN_SIGNAL_S =
  const(0.1)  # floor for a signal's ramp duration; also the non-finite fallback`; `_MAX_SIGNAL_S = const(60.0)  # the
  REST ceiling of t (buildgen's LED command bound, legacy led_cmd())` (API domain, untagged); `# @tunable
  led.refresh_hz = 20` / `_NEOPIXEL_FREQ_HZ = const(20)`; `# @tunable led.overlay_brightness = 50` / `_LED_OVERL_BRI =
  const(50)`; `# @tunable led.signal_wait_ms = 120000` / `_SIGNAL_WAIT_MS = const(120000)` with A.U9.04's reason line
  ("twice the longest signal: a late frame schedule never drops a queued flash; the deadline only guards a signal task
  that never restarts"). The wiring comment and tag: "# One optional live cross-instance dependency (SPECIFICATION.md
  Parts C.14 and L.4): the FRAM store its logger writes to, passed as log=." / `# @wiring fram_target FRAMManager log
  optional kwarg`.
- **Resolved**: A.U8.12 tags the two HEAD constructor defaults as `…_default`; A.U17.27 turns them into fixed values,
  so "default" no longer describes them: the IDs become `led.refresh_hz` and `led.overlay_brightness` (agent,
  2026-10-01, OR2.c list). A.U9.07's `_DEFAULT_FREQ_HZ` and refusal are not written (A.U17.27 supersedes it: a
  constant cannot be unusable).
- **Unit**: U17 (the latest constituent touching these lines after U9's `_MAX_SIGNAL_S`/`_SIGNAL_WAIT_MS` stage and
  U8's tag stage); stages: U5 (the `@wiring` target), U8 (tags on today's names), U9 (`_MAX_SIGNAL_S`,
  `_SIGNAL_WAIT_MS`), U10 (`FRAMManager`), U17 (fixed constants and renamed IDs)
- **Depends**: A.U8.01; M.SRC_SENS.023
- **Blast carried by**: Part N rows (`led.*`, the two renamed IDs, `led.signal_wait_ms`'s basis and its Dependant "frame
  period 50 ms (derived)") → A.U8.12/A.U9.04/A.U31.13 plus GAP-4 (the ID rename, SPEC); generated
  `NeopixelDriver(...)` passes neither parameter → A.U17.27; `buildgen` tag readers → A.U5.03/A.U10.38 (GEN)
- **Kind**: code

### M.SRC_SENS.022 One sanitiser where a signal request enters
- **From**: A.U9.06 (`_clamp_byte()`, new `_signal_values()`), A.U10.31 (`"int | float"` unquoted/retyped),
  A.U24.62 (blast: the bool-versus-int comment wording is its test-side action)
- **Site**: `src/asy_neopixel_driver.py:36-40` and a new module function after it
- **Change**: as A.U9.06 writes: `_clamp_byte(value: object) -> int` (non-`int`/`float` → 0; the `(ValueError,
  OverflowError)` catch for NaN/±inf stays, sorted `(OverflowError, ValueError)` per A.U10.45); `_signal_values(r:
  object, g: object, b: object, t: object) -> list[int | float] | None` (`None` for a non-numeric value; clamped bytes;
  `dur` floored at `_MIN_SIGNAL_S` for non-finite or short, capped at `_MAX_SIGNAL_S`).
- **Resolved**: —
- **Unit**: U9
- **Depends**: M.SRC_SENS.021
- **Blast carried by**: L1 sanitiser cases and the `:567-570` comment → A.U9.06 (TEST_UNIT); fake fidelity (TypeError
  for a float, int truncation) → A.U24.25/A.U25.21
- **Kind**: code

### M.SRC_SENS.023 `NeopixelDriver.__init__`: log config, fixed values, private state
- **From**: A.U5.02 (`(neopixel_pin, log)`), A.U17.27 (fixed values), A.U9.02 (`ext_rgbt`, `ext_start_signal` go),
  A.U9.04 (`start_signal_lock` goes), A.U10.17 (lock reason), A.U10.18 (`led_overl_lock` → `_overlay_lock`), A.U10.35
  (`pixel`, `start_signal_event`, `led_overl_bri`, `led_overl_on` private), A.U31.13 (`_frame_ms`)
- **Site**: `src/asy_neopixel_driver.py:43-68`
- **Change**: `def __init__(self, neopixel_pin: int, log: LogConfig = DEFAULT_LOG) -> None:` —
  `self.pr: PrintLogHistory = make_logger(log, _NAME)`; `self.name = _NAME` (comment kept); `self._pixel =
  neopixel.NeoPixel(Pin(neopixel_pin, Pin.OUT), 1, bpp=3)`; `self._rgbt: list[int | float] = [0, 0, 0, 0.1]`;
  `self._start_signal_event = asyncio.Event()`; `self._overlay_lock = asyncio.Lock()` with the reason "# serialises the
  pixel and its write() between the overlay and a signal ramp"; `self._overlay_start = asyncio.ThreadSafeFlag()`;
  `self._overlay_bri = _LED_OVERL_BRI`; `self._overlay_rgb: tuple[int, int, int] = (0, 0, 0)`; `self._overlay_on =
  False`; `self._neopixel_freq = _NEOPIXEL_FREQ_HZ`; `self._frame_ms = 1000 // _NEOPIXEL_FREQ_HZ` (50 ms, exact).
- **Resolved**: one name stem for the overlay state: A.U10.18 writes `_overlay_lock` while A.U10.35's mechanical rule
  would give `_led_overl_bri`/`_led_overl_on` beside it; D.10 in-file consistency → `_overlay_*` for all five (agent,
  2026-10-01). `rgbt`, `led_overl_start`, `led_overl_rgb` have no outside reader → private by default (G10/R07).
  A.U17.27 keeps the frequency and brightness as instance attributes (product state the ramp and overlay read); A.U31.13
  replaces `neopixel_dt` with `_frame_ms`.
- **Unit**: stage U5 (signature, `log`), stage U9 (`ext_*`, `start_signal_lock` removed), stage U10 (lock and attribute
  names, reason), stage U17 (fixed values), stage U31 (`_frame_ms`)
- **Depends**: M.SRC_SENS.020, M.SRC_SENS.021
- **Blast carried by**: generated construction → A.U5.03 (GEN); tests `tests/test_asy_neopixel_driver.py:31-35` and the
  five integration files setting frequency/period/brightness after construction → A.U17.27 (their attribute names
  become `_neopixel_freq`/`_frame_ms`/`_overlay_bri` → A.U10.35's reader renames plus GAP-5 for the stem choice,
  TEST_UNIT); `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:74-77` and `isl29125_lighting_scenarios.py:82`
  → A.U10.35 (HW_DEV) with the `_overlay_*` names (GAP-5)
- **Kind**: code

### M.SRC_SENS.024 `NeopixelDriver.setup()`: the logger in the boot batch
- **From**: A.U10.10 (new `setup()`), A.U10.21 (`-> bool`)
- **Site**: `src/asy_neopixel_driver.py` new method (D.15 position)
- **Change**: `async def setup(self) -> bool: return await self.pr.setup()` (the logger's own `setup()` returns
  `initialized` after A.U10.21).
- **Resolved**: —
- **Unit**: U10
- **Depends**: A.U10.21's `PrintLogHistory*.setup()` return (SRC_CORE)
- **Blast carried by**: generated batch `await neopixel.setup()` and `needs_setup` → A.U10.10 (GEN); tests
  `tests/test_asy_neopixel_driver.py:453-464` → A.U10.10 (TEST_UNIT)
- **Kind**: code

### M.SRC_SENS.025 Overlay task, starters and fan-in methods
- **From**: A.U22.01 (a) (overlay task re-applies on (re)start), A.U10.44 (`_led_overl_signal` → `_overlay_loop`,
  starters), A.U9.02 (the external watcher, its starter and list entry go), A.U22.04 (types), A.U10.31 (unquote),
  A.U11.31 (`reset_error_counter() -> bool`)
- **Site**: `src/asy_neopixel_driver.py:70-123`
- **Change**: `async def _overlay_loop(self) -> None`: `self._overlay_start.set()` once before `while True:` (a
  (re)started task re-applies the current overlay), then as today with the private names (`_overlay_lock`,
  `_clamp_byte(self._overlay_bri)`, `_overlay_on`, `_overlay_rgb`, `_pixel`). `_led_ext_signal_starter()` and
  `start_asy_ext_cmd_watcher()` go. Starters: `def start_asy_overlay(self) -> asyncio.Task[None]` over
  `_overlay_loop()`, `def start_asy_signal(self) -> asyncio.Task[None]` over `_signal_loop()`. `get_task_starters(self)
  -> list[TaskStarter]: return [self.start_asy_overlay, self.start_asy_signal]`. `get_timer_starters(self) ->
  list[TimerStarter]` (comment kept). `get_error_sources(self) -> list[ErrorSource]` (comment kept; "see this module's
  own docstring" → "no schema, see the module comment"). `get_loggers(self) -> list[PrintLogHistory]` (unquoted).
  `async def reset_error_counter(self) -> bool: return await self.pr.reset()`.
- **Resolved**: A.U10.44's map names the overlay/signal starters; the external-watcher starter has no name because
  A.U9.02 removes it first (A.U10.44 Depends A.U9.02).
- **Unit**: stage U9 (watcher removed), stage U10 (names), stage U11 (bool reset), stage U22 (overlay re-apply, typing)
- **Depends**: M.SRC_SENS.023; A.U10.46 (`TimerStarter` alias)
- **Blast carried by**: `tests/test_asy_neopixel_driver.py:653-658` (two starters) → A.U9.02; starter-name users in tests
  → A.U10.44; L1/L2 restart cases → A.U22.01 (TEST_UNIT, TWIN); `_put_status()`/`ResetErrors` → A.U11.31 (SRC_NET);
  SPEC A.4 NeoPixel paragraph → A.U22.01/A.U9.02/A.U9.05/A.U9.06 (SPEC)
- **Kind**: code

### M.SRC_SENS.026 `led_signal()`: refused at once while busy
- **From**: A.U9.02, A.U9.06
- **Site**: `src/asy_neopixel_driver.py:137-143`
- **Change**: `def led_signal(self, r: int, g: int, b: int, t: float) -> bool:` — `values = _signal_values(r, g, b,
  t)`; `None` → `return False`; `if self._start_signal_event.is_set(): self.pr.evt("External LED command refused:
  busy."); return False`; `self._rgbt = values`; `self._start_signal_event.set()`; `return True` (no `await`, so no lock).
- **Resolved**: —
- **Unit**: U9 (prerequisite of A.U9.03's generated REST LED callback, U9)
- **Depends**: M.SRC_SENS.022
- **Blast carried by**: `buildgen/codegen.py:555` → A.U9.03 (GEN); `js/mock-server.js` refusal mirror → A.U9.03 (GEN/
  WEB); tests `tests/test_asy_neopixel_driver.py:333-372`, `tests/test_notification_neopixel_integration.py:133-154`
  → A.U9.02 (TEST_UNIT); `pyproject.toml:88-89` ASYNC110 reason → A.U9.02/A.U28.27 (TOOL)
- **Kind**: code

### M.SRC_SENS.027 `request_signal()`: bounded wait, frame-period poll
- **From**: A.U9.04, A.U9.06, A.U31.13
- **Site**: `src/asy_neopixel_driver.py:145-153`
- **Change**: `async def request_signal(self, r: int, g: int, b: int, t: float) -> bool:` — `values = _signal_values(…)`,
  `None` → `return False`; `deadline = time.ticks_add(time.ticks_ms(), _SIGNAL_WAIT_MS)`; `while
  self._start_signal_event.is_set():` — past the deadline `self.pr.evt("Internal LED command dropped: signal still
  busy.")`, `return False`; else `await asyncio.sleep_ms(self._frame_ms)`; then `self._rgbt = values`,
  `self._start_signal_event.set()`, `return True`. The `start_signal_lock` is gone (no await between the final check and
  the set).
- **Resolved**: A.U9.04 writes the poll as `asyncio.sleep(self.neopixel_dt)` (a float sleep); A.U31.13 makes it
  `sleep_ms(self._frame_ms)` (U31 conflict table) — the merged end state is A.U31.13's.
- **Unit**: stage U9 (A.U9.04 with a float `sleep(self.neopixel_dt)`, lock removal — A.U10.17 in U10 relies on the lock
  being gone); stage U31 (`sleep_ms`)
- **Depends**: M.SRC_SENS.022, M.SRC_SENS.023
- **Blast carried by**: caller `NotificationService._trigger_signal()` (unchanged; waits at most `_SIGNAL_WAIT_MS`) →
  A.U9.04; L1 deadline/driven-time cases → A.U9.04 (TEST_UNIT); Part N row → A.U9.04 (SPEC)
- **Kind**: code

### M.SRC_SENS.028 Signal task: defined start, clean ramp, dark and free on any end
- **From**: A.U9.05 (`try/finally`), A.U9.06 (duration handling moves to the sanitiser), A.U10.10 (`pr.setup()` leaves
  the task), A.U22.01 (b) (overlay restored at start) and (c) (the `finally` order, merged into A.U9.05 by A.U22.01's own
  Depends), A.U31.13 (frame sleeps), A.U10.44 (`neopixel_signal` → `_signal_loop`)
- **Site**: `src/asy_neopixel_driver.py:155-187`
- **Change**: `async def _signal_loop(self) -> None:` — `self._pixel[0] = (0, 0, 0)`; `self._pixel.write()`;
  `self._overlay_start.set()` (restores the overlay after a restart); `while True:` `await
  self._start_signal_event.wait()`; `self.pr.evt("Signal started.")`; `try:` `t = self._rgbt[3]`; `steps = max(int(t *
  0.5 * self._neopixel_freq), 1)`; `steps_inv = 1.0 / steps`; `r_s = self._rgbt[0] * steps_inv` (likewise g, b — values
  are clean, A.U9.06); `async with self._overlay_lock:` the two ramp loops with `await asyncio.sleep_ms(self._frame_ms)`
  per step; `finally:` `self._start_signal_event.clear()`, `self._overlay_start.set()`, `self._pixel[0] = (0, 0, 0)`,
  `self._pixel.write()` (no `await` in the `finally`, so the overlay task writes after the black frame). The HEAD
  in-lock black write and `clear()` move into the `finally`.
- **Resolved**: A.U22.01 (c) reorders A.U9.05's `finally` (slot freed before the pixel is touched) — settled by
  A.U22.01's Depends ("A-C merges (c) into A.U9.05"). The ramp's per-frame arithmetic (three floats and a tuple per 50 ms
  frame) is a temporary, collectable allocation (OR110.a (3)); A.U30.02 catalogs it (A.U31.13 co-land note).
- **Unit**: stage U9 (A.U9.05 with (c)'s order, A.U9.06, float sleeps), stage U10 (`pr.setup()` out, name), stage U22
  ((b)), stage U31 (`sleep_ms`)
- **Depends**: M.SRC_SENS.023, M.SRC_SENS.024
- **Blast carried by**: ramp/cancel/restart L1-L2 cases → A.U9.05/A.U22.01 (TEST_UNIT, TWIN); I.2 row → A.U30.02
  (SPEC); SPEC A.4 → A.U9.05/A.U22.01 (SPEC)
- **Kind**: code

## src/asy_notification_service.py

### M.SRC_SENS.029 Module docstring and comment: current construction, no history
- **From**: A.U5.06 (the `:5` "Registration is staged: register() … finalize()" comment describes removed methods),
  adherence (docstring line 3 "Promoted from improved-quality/neopixel_signal.py … (see CLAUDE.md/BACKLOG.md)": history
  and a pointer to no existing text, G9/R12)
- **Site**: `src/asy_notification_service.py:1-5`
- **Change**: docstring → "Generic threshold-triggered LED notification signalling: `NotificationSignal` (per-condition
  data holder) and `NotificationService` (shared sleep window, interval, `AutoOn`, flash brightness and duration). Drives
  an LED through `request_signal_cb`, decoupled from any concrete LED implementation." Comment → "# Signals are passed
  at construction; a refused one is printed at once and persisted by setup()."
- **Resolved**: —
- **Unit**: U10 (the class name is A.U10.38's; A.U5.06's construction change lands in U5 with the comment's second
  sentence, the docstring's class name follows in U10)
- **Depends**: M.SRC_SENS.033
- **Blast carried by**: —
- **Kind**: doc

### M.SRC_SENS.030 Imports, typing names and the stub-workaround trigger
- **From**: A.U10.37 (module names), A.U10.38 (`AsyFramManager` → `FRAMManager`, gone here), A.U5.01/A.U5.02
  (`LogConfig`), A.U5.11 (`ValueRef`), A.U9.09 (`TickSeconds` replaces `LockedCounter`), A.U10.06 (`utc_now`),
  A.U22.04 (`Coroutine`/`Any` out, `Awaitable` in, `TaskStarter`), A.U27.03 + A.SDEP.15 (`_TicksMs` comment trigger)
- **Site**: `src/asy_notification_service.py:7-46`
- **Change**: runtime imports: `asyncio`, `time`, `namedtuple`, `const`, `from asy_base_classes import
  SensorReaderConfig, TickSeconds, report_if_fatal, utc_now` (`report_if_fatal` joins in U30), `from asy_config_manager import make_dict, name_cfg, schema_names`,
  `from asy_print_log import DEFAULT_LOG, LogConfig`. `TYPE_CHECKING` block: `from collections.abc import Awaitable,
  Callable`; `from typing import Protocol`; the `_TicksMs` import with its comment → "# The stubs' only name for a
  ticks_ms() value is private (_mpy_shed); _next_sleep_ms()'s t0 is one. Removal trigger: SPECIFICATION.md B.15.";
  `from asy_base_classes import TaskStarter, TimerStarter, ValueRef`; `from asy_config_manager import ConfigSchema`;
  `from asy_print_log import ErrorLog`; `_LocalTime` unchanged; `_ValueSource.get_data(self) -> object` (A.U22.04). The
  `AsyFramManager` import goes (no parameter names it after A.U5.02/A.U5.06). A.SDEP.15's U0 re-check decides whether
  the private-name workaround still exists at the new stubs (a stub release that drops it fails the main pass).
- **Resolved**: —
- **Unit**: U27 (latest; stages: U5 `LogConfig`/`ValueRef`, U9 `TickSeconds`, U10 module names and `utc_now`, U22
  typing, U27 the trigger comment)
- **Depends**: A.U10.02 (`TickSeconds`), A.U10.06 (`utc_now`), A.U5.11 (`ValueRef` in `asy_base_classes.py`),
  A.U10.46 (aliases)
- **Blast carried by**: SPEC B.15 workaround list → A.U27.03 (SPEC); `pyproject.toml` ANN401 entry → A.U22.04 (TOOL)
- **Kind**: code

### M.SRC_SENS.031 Module constants, catalog names and wiring tags
- **From**: A.U2.17 + A.U2.04 (`_ERR_`/`_WRN_` block), A.U8.12 (`notify.loop_tick_s`, `notify.min_sleep_s`,
  `notify.cfg_fail_interval_s`), A.U31.14 (ms/int forms), A.U9.08 (`_ERR_SOURCE` use), A.U5.03 (`@wiring … log`),
  A.U10.38 (`FRAMManager`)
- **Site**: `src/asy_notification_service.py:48-55`
- **Change**: after the imports, one block: `_ERR_CALLBACK = const(14)`, `_ERR_SOURCE = const(15)`,
  `_WRN_NOTIFY_NAME_COLLISION = const(44)`, `_WRN_NOTIFY_SCHEMA_SHAPE = const(45)` (46/47 retired, not declared);
  `_MAX_OVERRIDE_TIME = const(3600)`, `_NAME = const("NOTIFY")`; `# @tunable notify.loop_tick_s = 1` / `_LOOP_TICK_S =
  const(1)`; `# @tunable notify.min_sleep_ms = 100` / `_MIN_SLEEP_MS = const(100)`; `# @tunable
  notify.cfg_fail_interval_s = 600` / `_CFG_FAIL_INTERVAL_S = const(600)`. Wiring comment unchanged in substance, tags
  `# @wiring signal_sink NeopixelDriver request_signal required attr` and `# @wiring fram_target FRAMManager log optional
  kwarg`.
- **Resolved**: A.U8.12's float `_MIN_SLEEP_S = const(0.1)`/`const(600.0)` vs A.U31.14's int ms/s — A.U31.14's (U31
  conflict table row 1).
- **Unit**: stages U2 (catalog block), U5 (tag target), U8 (tags as float seconds), U10 (class name in tag), U31 (final
  int forms)
- **Depends**: A.U2.01 (catalog), A.U8.01
- **Blast carried by**: Part N rows renamed → A.U8.12/A.U31.14 (SPEC); mock NOTIFY errcount row → A.U2.21 (WEB/GEN);
  `tests/test_asy_notification_service.py` (12), `tests/test_notification_fram_integration.py` (6) numbers → A.U2.17
  (TEST_UNIT); A.U22.03's withdrawal keeps `notify.loop_tick_s` (OR126.a (4))
- **Kind**: code

### M.SRC_SENS.032 Schema block, comments and `@web` tags
- **From**: A.U10.34 (`_DefaultSignalSink` docstring → comment), A.U9.11 + A.U0.38 V17 (`:68-70`), A.U36.544 (`:82`
  L.5 → H.5.1), A.U5.06 (`:80-82` "registered per signal at runtime", `:99-100` "finalize() assembles"), A.U10.39
  (`_VAL_` names; concatenation comment), A.U10.40 (`Interv` → `FlashInterval`), A.U20.25 (concatenations must evaluate at
  build: no change here), A.U9.01 (`AutoOn` help), adherence (`:84-85` "the hand-written definitions established it":
  history)
- **Site**: `src/asy_notification_service.py:58-101`
- **Change**: `_DefaultSignalSink`: the docstring becomes a comment under the class line "# The wiring-defaults
  mechanism (SPECIFICATION.md Part L.6.2), opted into via [instance.wiring].signal_sink = {default = true}: a no-op LED
  sink for a notification setup that should blink no LED." (its method comment stays). `:68-70` → A.U9.11's text: "# Own
  schema; config keys carry no "Led" prefix (`WarnCO2`, not `LedWarnCO2`): the new API is the only reference (owner,
  2026-09-26), SPECIFICATION.md A.4. Ranges and defaults mirror legacy's REST bounds." `_VAL_INTERV` →
  `_VAL_FLASH_INTERVAL = const((("FlashInterval", "float", 300.0, 60.0, 3600.0, None),))`; the other seven names already
  equal their keys in upper snake case. `:80-82` → "# WarnCO2/WarnVOC/WarnHum come with each signal passed at
  construction, not as _VAL_* constants here, so their web metadata is generator-owned (buildgen's warn-signal
  catalog) - no per-device fact this file could tag (Part H.5.1)." `:84-85` → "# Literal submitGroup ("autoConfig"),
  not the "self" sentinel the sensors use: a singleton service has nothing to disambiguate." Tags: `AutoOn`'s
  description → "Active from Auto On to Auto Off; an On time later than the Off time runs overnight (e.g. 22:00 to
  06:00)."; `# @web Interv …` → `# @web FlashInterval …` (label unchanged). The three aggregates `:96-101` keep their
  concatenation form under one comment "# Concatenations of the field tuples: const() cannot fold them. The constructor
  appends one field per signal to _VAL_OWN_SCHEMA." (the HEAD "stays const()-folded" claim is false and goes).
- **Resolved**: A.U0.38 V17 and A.U9.11 rewrite `:68-70` differently — A.U9.11's wording is taken (its Blast: "A-C merges
  onto this action's wording, which follows G3/R69's 'accepted debt goes'").
- **Unit**: U10 (latest of U0/U5/U9/U10; A.U36.544's pointer lands with it — the target H.5.1 exists at HEAD)
- **Depends**: A.U10.40 (key map), M.SRC_SENS.033
- **Blast carried by**: `FlashInterval` consumers (js, mock data, tests, generated definitions) → A.U10.40 (WEB, GEN,
  TEST_UNIT); `html/definitions/*.json` help text → A.U9.01/A.U6.04 (GEN); SPEC A.4 notification paragraph → A.U9.01
  (SPEC); buildgen concatenation evaluator → A.U20.25/A.U20.12 (GEN)
- **Kind**: code, doc

### M.SRC_SENS.033 `NotificationSignal` and construction-time `NotificationService`
- **From**: A.U5.11 (`value: ValueRef`), A.U22.02 + A.U23.37 (`last_value`, `triggered` go), A.U10.35 (`triggered`:
  superseded by the removal), A.U5.06 (signals at construction; `register()`/`finalize()`/`_finalized` go), A.U5.02
  (`log`), A.U10.38 (`NotificationCoordinator` → `NotificationService`), A.U9.09 (`_pause`), A.U2.17 (W44/W45 names),
  A.U22.04 (callback types), A.U10.39 (`cfg_schema` → `_cfg_schema`)
- **Site**: `src/asy_notification_service.py:110-173, 247-316`
- **Change**: `NotificationSignal(name, value: ValueRef, field_schema, color, *, above=True)` stores `name`, `value`,
  `field_schema`, `color`, `above` (the HEAD comment `:122-124` → "# A reference to the producer plus the field to read
  off its get_data() result (Part C.14): never a wrapping getter."; the `:130-132` comment and both attributes go).
  `class NotificationService(SensorReaderConfig)`: `__init__(self, request_signal_cb: Callable[[int, int, int, float],
  Awaitable[bool]], local_time_callback: Callable[[], Awaitable[_LocalTime | None]], signals:
  tuple[NotificationSignal, ...], cfg_path: str = "", log: LogConfig = DEFAULT_LOG)` — validates each signal in order as
  `register()` does at HEAD (schema shape → W45, name collision against the own schema and the accepted ones → W44),
  prints a refusal at once (`print()`-level console line through the pre-logger path A.U5.06 names) and buffers
  `(message, wrnno)` in `self._pending_wrn`; then `super().__init__(NOTIFY(Triggered=False, TS=None), _NAME,
  combined_schema, max_module_error=0, cfg_path=cfg_path, log=log)`; `self._request_signal_cb`,
  `self._local_time_callback`, `self._registered` (the accepted tuple), `self._pause = TickSeconds(count_down=True)`,
  `self._auto_active = True`. `register()`, `finalize()`, `_finalized`, `_reject_registration()`'s late/again codes and
  every `if not self._finalized` guard (`get_data`, `get_dict_data`, `get_dict_cfg`, `get_error_counter`, `setup`,
  `reset_error_counter`, both loops) go; `get_data()` keeps `# Narrows to this Reader's concrete NOTIFY - see
  SPECIFICATION.md C.4.2's get_data() convention.` directly above `return await self._get_meas_data()  # type:
  ignore[return-value]`; `get_dict_data()` uses `name=self.name`; `get_dict_cfg()` → `self._get_dict_cfg(self.name,
  self._cfg_schema)`; `get_error_counter()` → `return await self.pr.get_log()`; the `reset_error_counter()` override
  goes (the inherited one returns the reset's bool, A.U11.31). `async def setup(self) -> bool:` `ok = await
  super().setup()`; then each buffered refusal `await self.pr.wrn_s(msg, wrnno=code)` (the buffer emptied); `return ok`.
- **Resolved**: (1) A.U11.31 gives the not-finalised early return `True` "until A.U5.06 removes the guard" — the guard
  is removed, so the override is not needed. (2) A.U28.30 asks a reason for the `:251` ignore; with the guard gone the
  C.4.2 comment sits directly above the ignored line, which A.U28.30's form rule accepts — no trailing reason added.
  (3) A.U10.21 "a class whose `__init__` refuses … returns `False`": a refused signal is one warning on an otherwise
  ready service (A.U5.06 "the object is fully usable immediately"), so `setup()` returns the config store's validity
  (agent reading of the two actions, OR2.c list). (4) A.U10.35's privatisation of `triggered` is superseded by its
  removal (A.U22.02's Depends).
- **Unit**: U10 (class name; stages U5 construction/`ValueRef`/`log`, U9 `_pause`, U10 name/`_cfg_schema`, U11 reset
  override gone with the guard, U22 attributes and typing)
- **Depends**: M.SRC_SENS.030, M.SRC_SENS.031; A.U5.02 (`SensorReaderConfig` signature), A.U10.21
- **Blast carried by**: generated `_notification_lines()` (signals as an argument, `ValueRef`) → A.U5.06/A.U5.11 (GEN);
  tests (116 `register`/`finalize` lines, `make_signal()`, `:682, :815-816, :833-834, :856-870`) → A.U5.06/A.U5.11/
  A.U22.02 (TEST_UNIT); A.U10.35's site list loses `triggered` → A.U22.02; SPEC C.4.3 `:1693-1698`, C.4, A.7 steps 12/16,
  C.14.3 → A.U5.06 (SPEC)
- **Kind**: code

### M.SRC_SENS.034 `_next_sleep_ms()`, the retired `_now()`, and the two callback guards
- **From**: A.U31.14 (`_next_sleep_secs()` → `_next_sleep_ms()`), A.U10.43 (`_next_sleep_s()`: superseded by A.U31.14),
  A.U10.06 (`_now()` goes; `utc_now()`), A.U14.26 (`_now()`'s handler → `except MemoryError`: dropped, see Resolved),
  A.U2.17 (e12/e13 → 14 CALLBACK), A.U30.19 (`report_if_fatal`), A.U22.04 (types)
- **Site**: `src/asy_notification_service.py:175-231`
- **Change**: `def _next_sleep_ms(self, interv: float, t0: _TicksMs) -> int:` (comment kept, reworded "the floor kick
  in" unchanged) `return max(round(interv * 1000) - time.ticks_diff(time.ticks_ms(), t0), _MIN_SLEEP_MS)`. `_now()` goes;
  `_store_notif_data()` → `await self._set_meas_data(NOTIFY(any_triggered, utc_now()))`. `_safe_local_time()`: `except
  Exception as e: report_if_fatal(e); await self.pr.err_s("local_time_callback failed:", e, errno=_ERR_CALLBACK); return
  None`. `_trigger_signal()`: same shape with `"request_signal_cb failed:"` and `_ERR_CALLBACK`.
- **Resolved**: A.U10.06 (no `try` at the timestamp) and A.U14.26 (1) (`except MemoryError` at the `_now()`-shaped
  sites) conflict; ruled for A.U10.06 by V.U18.R10 (U18 register fix 10, A.U18.25's Depends; U30 cross-unit note 1).
  A.U10.43's `_next_sleep_s()` is overtaken by A.U31.14's `_next_sleep_ms()` (U31 conflict table row 7).
- **Unit**: stages U2 (numbers), U10 (`utc_now`), U30 (`report_if_fatal`), U31 (`_next_sleep_ms`)
- **Depends**: A.U10.06, A.U30.19
- **Blast carried by**: `tests/test_asy_notification_service.py:1256-1279` → A.U31.14; `:1440-1498` (`_now()` overflow
  tests) go → A.U10.06 (TEST_UNIT); `_FastAsyncSleep` gains `sleep_ms` → A.U31.14/A.U24.49 (TEST_HELP)
- **Kind**: code

### M.SRC_SENS.035 `_check_one()`: value reference, numeric guard, one entry per event
- **From**: A.U5.11 (`notif.value.source`/`.field`), A.U9.08 (non-numeric and NaN), A.U22.02/A.U23.37 (no attribute
  writes), A.U2.17 (e10 → 15 SOURCE), A.U3.05 (threshold read failure → console), A.U30.19
- **Site**: `src/asy_notification_service.py:194-221`
- **Change**: `async def _check_one(self, notif: NotificationSignal) -> bool:` — `source: _ValueSource =
  notif.value.source` (annotated local narrows the untyped namedtuple field, C.4.2 idiom); `try: data = await
  source.get_data(); value: object = getattr(data, notif.value.field, None)` `except Exception as e: report_if_fatal(e);
  await self.pr.err_s(notif.name, "Value read failed:", e, errno=_ERR_SOURCE); return False`; `if value is None: return
  False`; `if type(value) not in (int, float, bool): await self.pr.err_s(notif.name, "Value not numeric:",
  type(value).__name__, errno=_ERR_SOURCE); return False`; `if value != value: return False  # NaN never triggers`;
  `thresholds = await self.cfgmgr.get_float_values(notif.field_schema)`; `None` → `self.pr.err(notif.name, "Threshold
  config read failed!")`, `return False` (the config store persisted the cause, A.U3.05); `threshold = thresholds[0]`;
  `numeric_value = float(value)` (cannot raise now; comment → "# float() cannot raise here: value is numeric."); return
  the comparison.
- **Resolved**: A.U9.08 writes `notif.last_value = None`/`notif.triggered = False` in its new branches — dropped with
  the attributes (A.U22.02's Depends). `bool` counts as numeric (A.U9.08 "(`bool` counts as `int`)") — written as an
  explicit type set because MicroPython's `bool` is not an `int` subclass (`py/objbool.c:87-96`, A.U11.S01).
- **Unit**: stages U2, U3, U5, U9 (numeric guard, with the attribute writes already absent), U22, U30
- **Depends**: M.SRC_SENS.033
- **Blast carried by**: tests `:768-801`, `:873-893` (`"abc"`, `[1]`, `"1800"` rows), `FakeValue` typing → A.U9.08
  (TEST_UNIT); catalog row 15 wording "raised or returned a non-numeric field" → A.U9.08 into A.U2.01 (GEN)
- **Kind**: code

### M.SRC_SENS.036 Starters, the pause task and the override API
- **From**: A.U10.44 (`start_asy_monitor`/`_monitor_loop`, `start_asy_pause`/`_pause_loop`), A.U9.09 (measured pause),
  A.U8.12 (`_LOOP_TICK_S`), A.U22.03 (WITHDRAWN, OR126.a (4): the one-second round stays), A.U22.04 (types)
- **Site**: `src/asy_notification_service.py:233-245, 269-274, 317-330`
- **Change**: `start_asy_monitor(self) -> asyncio.Task[None]` over `_monitor_loop()`; `start_asy_pause(self) ->
  asyncio.Task[None]` over `_pause_loop()`; `get_task_starters(self) -> list[TaskStarter]`; `get_timer_starters(self) ->
  list[TimerStarter]`. `async def get_override_led(self) -> int: return self._pause.read()`; `async def
  set_override_led(self, secs: int) -> None: self._pause.restart(min(max(secs, 0), _MAX_OVERRIDE_TIME))`.
  `async def _pause_loop(self) -> None:` `self._auto_active = True`; `while True:` `secs = self._pause.read()`; the two
  `_auto_active` transitions as today; `await asyncio.sleep(_LOOP_TICK_S)`.
- **Resolved**: A.U22.03 withdrawn by the owner (OR126.a (4)) — not merged.
- **Unit**: stages U8 (tag), U9 (`_pause`), U10 (names), U22 (types)
- **Depends**: M.SRC_SENS.033; A.U10.02
- **Blast carried by**: generated `_notification_pause_callback()`/`_notification_status()` (unchanged signatures) →
  A.U9.09; tests `:1133-1230`, twin `:349-390`, bench `:115-141`, `tests_hardware/README.md:1236-1237`,
  `asy_webserver_service.py:100, :550` comments → A.U9.09 (TEST_UNIT, TWIN, HW_BENCH, SRC_NET); starter-name users →
  A.U10.44
- **Kind**: code

### M.SRC_SENS.037 `_monitor_loop()`: midnight window, one log path, ms sleeps
- **From**: A.U9.01 (`_in_window()`), A.U10.10 (`pr.setup()` leaves the task), A.U3.02 (`cfg_failing`, `repeat=` go),
  A.U3.05 (the config-read warning → console), A.U8.12/A.U31.14 (`_CFG_FAIL_INTERVAL_S`, `sleep_ms`), A.U5.06 (guard
  and `_flush_pending_registration_warnings()` go: `setup()` persists refusals), A.U10.44 (name)
- **Site**: `src/asy_notification_service.py:332-376` and a new module function
- **Change**: new module function `_in_window(on_min: int, off_min: int, cur_min: int) -> bool` exactly as A.U9.01
  writes. `async def _monitor_loop(self) -> None:` — no setup, no guard; the comment `:337-339` stays; `while True:` `t0 =
  time.ticks_ms()`; the three config reads; on any failure `interv = _CFG_FAIL_INTERVAL_S` and `self.pr.err("Error reading
  own configuration!")` (console; `ConfigManager` persisted the cause); else the window test `if _in_window(on_min_of_day,
  off_min_of_day, cur_min_of_day):`, the per-signal loop with `await asyncio.sleep_ms(round(flash_dur * 2000))` after a
  triggered flash, `await self._store_notif_data(any_triggered=any_triggered)`; `await
  asyncio.sleep_ms(self._next_sleep_ms(interv, t0))`.
- **Resolved**: A.U3.02 (the `cfg_failing` flag) and A.U3.05 ("NTP `:225` and NOTIFY `:355` … A.U3.05 makes them console
  lines") agree: the line becomes a console print, the flag and `repeat=` go.
- **Unit**: stages U3 (log), U5 (flush moved to `setup()`), U8 (constant), U9 (window), U10 (setup out, name), U31
  (sleeps)
- **Depends**: M.SRC_SENS.031, M.SRC_SENS.033, M.SRC_SENS.034
- **Blast carried by**: `_in_window()` table, one-cycle and L2 window tests → A.U9.01 (TEST_UNIT, TWIN); config-failure
  tests `:665-686, :1350-1407` → A.U3.05 (TEST_UNIT); DEVICE_REFERENCE window bullet → A.U9.01 (DOCS); SPEC A.4 → A.U9.01
- **Kind**: code

## src/asy_bmp3xx_driver.py

### M.SRC_SENS.038 SPDX header order and docstring sources
- **From**: A.U34.07 (header order), A.U15.25 (1) (docstring line 7), A.U10.38 (class name in line 6), A.U28.35 (blast:
  `:7`'s `datasheets/bmp3xx/` citation stays valid after the submodule move)
- **Site**: `src/asy_bmp3xx_driver.py:1-8`
- **Change**: header → "# SPDX-FileCopyrightText: 2018 Carter Nelson for Adafruit Industries" / "#
  SPDX-License-Identifier: MIT" / "# From adafruit_bmp3xx (CircuitPython), restructured for asyncio + MicroPython - see
  THIRD_PARTY_LICENSES.md." Docstring line 6 names `BMP3XX_Reader`; line 7 → "Verified against BST-BMP384-DS003,
  BST-BMP388-DS001, BST-BMP390-DS002 and the self-test note BST-MPS-AN006 (datasheets/bmp3xx/); one register map, chip
  ID 0x50 (BMP384/388) or 0x60 (BMP390)."
- **Resolved**: —
- **Unit**: U34 (latest; A.U15.25's line lands in U15, A.U10.38's name in U10, as stages)
- **Depends**: A.U34.03/A.U34.05/A.U34.06 (entries the L0 check reads)
- **Blast carried by**: L0 `tests_scripts/test_third_party_attribution.py` → A.U34.07 (TSC); K.9 text → A.U34.07 (SPEC);
  `pyproject.toml` CPY001 reason → A.U28.32 (TOOL)
- **Kind**: doc

### M.SRC_SENS.039 Imports and the typing block
- **From**: A.U10.37, A.U15.40 (`Lockable` import goes, `DeviceSession` in), A.U15.26 (`type_or_range_error`), A.U10.06
  (`utc_now`), A.U5.01 (`LogConfig`), A.U15.43 (`Any`/`Callable` out, starter aliases), A.U5.02 (the FRAM manager import
  goes), A.U30.19 (`report_if_fatal`), A.U12.08 (the helper it calls is renamed in `math_helpers.py`)
- **Site**: `src/asy_bmp3xx_driver.py:10-33`
- **Change**: runtime: `asyncio`, `time`, `namedtuple`, `from struct import unpack`, `from machine import Timer`,
  `const`, `import math_helpers`, `from asy_i2c_driver import I2C, I2CDevice`, `from asy_base_classes import
  DeviceSession, LockedValue, SensorReaderConfig, report_if_fatal, utc_now`, `from asy_config_manager import make_dict,
  name_cfg, type_or_range_error`, `from asy_print_log import DEFAULT_LOG, LogConfig`. `TYPE_CHECKING`: `from
  asy_base_classes import TaskStarter, TimerStarter`; `from asy_print_log import ErrorLog`.
- **Resolved**: —
- **Unit**: U15 (stages U5 `LogConfig`, U10 module names/`utc_now`, U30 `report_if_fatal`)
- **Depends**: A.U10.37, A.U10.46, A.U15.40, A.U10.06
- **Blast carried by**: `pyproject.toml` baseline list → A.U15.43 (TOOL)
- **Kind**: code

### M.SRC_SENS.040 Constants: register bit, catalog names, waits, the fixed sea level
- **From**: A.U2.10 (`_ERR_CMD` → `_REG_ERR_CMD_BIT`; numbers), A.U2.04 (`_ERR_`/`_WRN_` block), A.U15.24 (W11),
  A.U15.25 (5)/(8) (`_CMD_RDY_TIMEOUT_MS`, `_MEAS_TIMEOUT_MS` comments), A.U8.07 (tags; `_STATUS_POLL_S`,
  `_RESET_SETTLE_S`), A.U31.11 (→ `_STATUS_POLL_MS = 2`, `_RESET_SETTLE_MS = 3`), A.U10.43 (`_MIN/_MAX_TRIGGER_SECS` →
  `_S`), adherence (`sea_level_pressure` has no writer after A.U10.21: see Resolved)
- **Site**: `src/asy_bmp3xx_driver.py:36-72`
- **Change**: `_REG_ERR_CMD_BIT = const(0x02)` (comment unchanged). After the imports the catalog block:
  `_ERR_INIT = const(10)`, `_ERR_READ = const(11)`, `_ERR_CHIP_GET = const(12)`, `_ERR_CHIP_SET = const(13)`,
  `_ERR_BAD_ARG = const(21)`, `_WRN_DERIVED_DOMAIN = const(11)`. `# @tunable bmp3xx.cmd_rdy_timeout_ms = 50` /
  `_CMD_RDY_TIMEOUT_MS = const(50)  # cmd_rdy is set whenever no command is executing (DS001 4.3.3); the datasheet gives
  no bound, so 50 ms bounds a bus fault (agent)`; `# @tunable bmp3xx.meas_timeout_ms = 300` / `_MEAS_TIMEOUT_MS =
  const(300)  # ~150 ms worst case at x32/x32 (3.9.2 typical + Table 22 max margin); 300 ms bounds a stuck STATUS`;
  `# @tunable bmp3xx.status_poll_ms = 2` / `_STATUS_POLL_MS = const(2)`; `# @tunable bmp3xx.reset_settle_ms = 3` /
  `_RESET_SETTLE_MS = const(3)  # one tick more than the datasheet's 2 ms: sleep_ms() may wake up to 1 ms early`;
  `_SEA_LEVEL_PRESSURE_HPA = const(1013.25)  # ISA standard sea-level pressure, get_pressure_altitude()'s base`;
  `_MIN_TRIGGER_S = const(1)`, `_MAX_TRIGGER_S = const(3600)`.
- **Resolved**: A.U8.07's float-second names vs A.U31.11's integer milliseconds → A.U31.11's (U31 conflict row 1).
  `sea_level_pressure`: A.U10.21 removes `setup()`'s only writer and A.U10.35 privatises the attribute, leaving a
  private value that is never written after construction and a `<= 0` guard in `get_altitude()` no input reaches — the
  value becomes this named constant and the guard goes (G5/R54 unreachable branch, OR46.a (2); agent, 2026-10-01, OR2.c
  list).
- **Unit**: stages U2 (bit rename, catalog block), U8 (tags on float names), U10 (`_S` suffix), U15 (comments, W11,
  sea level), U31 (ms constants)
- **Depends**: A.U2.01, A.U8.01
- **Blast carried by**: Part N rows → A.U8.07/A.U31.11 (SPEC); test copies of the constants → A.U24.01/A.U24.02
  (TEST_UNIT); `tests/test_asy_bmp3xx_driver.py` number asserts (30 lines) → A.U2.10; the `get_altitude` guard test (if
  any: `grep sea_level_pressure tests/`) → GAP-6 (TEST_UNIT)
- **Kind**: code

### M.SRC_SENS.041 Schema, tag block and value domains
- **From**: A.U10.39 (`_VAL_` names), A.U10.40 (keys `SampleInterval`, `PresOvers`, `PresOffset`, `SeaLevelOffset`),
  A.U15.23 (`MeanAtmTemp` −40), A.U15.40 (3) (`_N_*` stays right after `_VAL_*`), A.U20.27 (4) (`@web-group` labels
  "BMP3xx"), A.U6.19 (`TS` tag `format=epoch`, no unit), A.U10.43 (`@limits trigger_s`), A.U5.03 + A.U10.38
  (`@wiring fram_target FRAMManager log optional kwarg`)
- **Site**: `src/asy_bmp3xx_driver.py:74-120`
- **Change**: `_VAL_SAMPLE_INTERVAL = const((("SampleInterval", "int", 2, _MIN_TRIGGER_S, _MAX_TRIGGER_S, None),))`;
  `_VAL_PRES_OVERS` (`"PresOvers"`), `_VAL_TEMP_OVERS`, `_VAL_FILT_COEFF`, `_VAL_PRES_OFFSET` (`"PresOffset"`),
  `_VAL_TEMP_OFFSET`, `_VAL_SEA_LEVEL_OFFSET` (`"SeaLevelOffset"`), `_VAL_MEAN_ATM_TEMP = const((("MeanAtmTemp", "float",
  15.0, -40.0, 50.0, None),))` with "# Lower bound: the barometric helper's domain, -40 degC (BMP388/390 operating
  range)."; `_N_INT_CFG`/`_N_FLOAT_CFG` directly after them (their comments name the new keys). Tags: both `@web-group`
  labels "BMP3xx — Pressure, Temperature"; the field tags carry the new keys; `# @web TS … kind=readonly
  label="Timestamp" format=epoch`. The wiring comment keeps its text with "passed as log=" and the tag `# @wiring
  fram_target FRAMManager log optional kwarg`; `# @limits trigger_s 1..3600` (comment: "bounds kept in sync with
  _MIN/_MAX_TRIGGER_S by hand").
- **Resolved**: —
- **Unit**: U20 (latest: the labels); stages U5, U6, U10, U15
- **Depends**: A.U10.40 (map), A.U6.19 (`format` key), A.U20.27
- **Blast carried by**: generated definitions and `html/definitions/*.json` (`MeanAtmTemp` min, labels, keys) →
  A.U15.23/A.U20.27/A.U6.04 (GEN); mock data, js, tests using the old keys → A.U10.40; `tests/test_asy_bmp3xx_driver.py:
  991-1014` test-local copies → A.U24.01/A.U15.23; release-note line → A.U15.23 via U37 (DOCS); stored-config repair of
  [−50, −40) values → `ConfigManager.setup()` (A.U15.23 blast, no action needed)
- **Kind**: code

### M.SRC_SENS.042 `BMP3XX_Reader` construction
- **From**: A.U5.02 (`(i2c, address, trigger_s, max_module_error, name_ext, cfg_path, log)`), A.U10.38 (class name),
  A.U10.43 (`trigger_s`), A.U10.35 (private attributes), A.U27.03 + A.SDEP.15 (bare `Timer()` comment trigger), A.U15.R03
  (`_recovery_bus`), A.U15.40 (divider attributes set here), A.U10.25 (registrations stay in `__init__`: holds), A.U10.39
  (`name_cfg(_VAL_…)` names)
- **Site**: `src/asy_bmp3xx_driver.py:125-168`
- **Change**: `class BMP3XX_Reader(SensorReaderConfig)`; `__init__(self, i2c: I2C, address: int = 0x77, trigger_s: int =
  1, max_module_error: int = 5, name_ext: str = "", cfg_path: str = "", log: LogConfig = DEFAULT_LOG)`;
  `super().__init__(BMP3XX(None, None, None, None), _NAME, <the eight _VAL_ tuples>, max_module_error=max_module_error,
  name_ext=name_ext, cfg_path=cfg_path, log=log)`; `self._bmp = BMP3XX_I2C(i2c, address=address)`; `self._recovery_bus =
  i2c`; `self._base_trigger_event`, `self._read_event` (ThreadSafeFlag); the Timer comment → "# Bare Timer() is valid on
  rp2 (id defaults to -1); the stub requires an id. Removal trigger: SPECIFICATION.md B.15." then `self._trigger_timer =
  Timer()`; `self._trigger_period = LockedValue(init_value=int(trigger_s))`; `self._trigger_counter = 0`; the push/get
  registrations as today with the renamed `_VAL_` names and `_push_trigger_s`.
- **Resolved**: A.U15.40's shared `_trigger_loop()` in `SensorReader` reads the divider attributes the subclass sets; with
  A.U10.35 they are the private names above (one set of names for both drivers that divide).
- **Unit**: U15 (stages U5 signature, U10 names, U27 comment)
- **Depends**: M.SRC_SENS.039-041; A.U10.R01 (`_recovery_bus` slot in `SensorReader`)
- **Blast carried by**: generated construction → A.U5.03/A.U10.43 (GEN); tests constructing the reader and reading the
  attributes → A.U5.02/A.U10.35 (TEST_UNIT); device scripts (`bmp3xx_plausibility_read.py`, …) → A.U5.02/A.U10.35
  (HW_DEV); SPEC B.15 → A.U27.03 (SPEC)
- **Kind**: code

### M.SRC_SENS.043 `_read_bmp()`, `_store_bmp()`: one timestamp, captured config, domain warning
- **From**: A.U10.06 (`utc_now()` before the `try`; store guard on values only), A.U15.22 (2) (`_cycle_comp` captured
  before the first await), A.U15.24 (W11 `DERIVED_DOMAIN`), A.U12.08 (`altitude_baro` → `pressure_at_height`), A.U3.05
  (the config-read line → console), A.U2.10 (numbers), A.U30.19
- **Site**: `src/asy_bmp3xx_driver.py:185-196, 227-249`
- **Change**: `__init__` gains `self._cycle_comp: list[float] = [0.0, 0.0, 0.0, 15.0]` (overwritten in place, never
  reallocated). `_read_bmp()`: `timestamp = utc_now()`; `comp = await self.cfgmgr.get_float_values(<the four float
  _VAL_ tuples>)`; on a failed read `self.pr.err("Error reading config data!")` (console) and the fallback
  `[0.0, 0.0, 0.0, 15.0]` copied into `self._cycle_comp` element-wise, else the four values copied in; then `try:
  pressure, temperature = await self._bmp.get_pressure_and_temperature()`, `self.pr.all("read")` `except Exception as e:
  report_if_fatal(e); pressure = temperature = None; await self.pr.err_s("Read failed:", e, errno=_ERR_READ)`; return
  `(pressure, temperature, timestamp)`. `_store_bmp()`: returns without storing when `results[0]` or `results[1]` is
  `None` (the timestamp may be `None` before the first sync); `p_comp = results[0] - self._cycle_comp[0]`, `t_comp =
  results[1] - self._cycle_comp[1]`; if `not _OP_PRESS_MIN_HPA <= p_comp <= _OP_PRESS_MAX_HPA`: `slp = None` and `await
  self.pr.wrn_s("PresOffset moves the pressure outside 300-1250 hPa; sea-level pressure not computed:", p_comp,
  wrnno=_WRN_DERIVED_DOMAIN)`, else `slp = math_helpers.pressure_at_height(p_comp, -self._cycle_comp[2],
  self._cycle_comp[3])`; store `BMP3XX(p_comp, t_comp, slp, results[2])`.
- **Resolved**: (1) Shared wrnno 11: A.U15.24 (`DERIVED_DOMAIN`) and A.U18.15 (`SOCKET_TEARDOWN`) both claim it
  (SUPP_recovery conflicts row 7, "A-C assigns 11 to one and 12 to the other"): U15 lands before U18, so
  `DERIVED_DOMAIN` = 11, `SOCKET_TEARDOWN` = 12; A.U10.R01's W14/W15 keep their numbers (agent, 2026-10-01). (2)
  A.U15.22's capture moves the config read ahead of the conversion; A.U10.06 puts the timestamp before the `try` — both
  hold: timestamp, capture, then the conversion.
- **Unit**: stages U2, U3, U10, U12 (helper name), U15, U30
- **Depends**: M.SRC_SENS.040, M.SRC_SENS.041; A.U12.08, A.U2.01 (W11 row)
- **Blast carried by**: L1 staleness/capture/domain cases → A.U15.22/A.U15.24/A.U10.06 (TEST_UNIT); catalog row W11 and
  W12 → A.U15.24 and A.U18.15 into A.U2.01 (GEN, SRC_NET: GAP-7 for the number); SPEC C.4.2/M.4/C.7.1 → A.U15.22/
  A.U15.24/A.U2.22 (SPEC)
- **Kind**: code

### M.SRC_SENS.044 `_init_bmp()`, the stored-config re-apply and the participant rung
- **From**: A.U15.R03 (`_apply_stored_config()`, `_recover_device()`, `_init_failed()`/`_init_done()`), A.U10.10
  (`pr.setup()` leaves), A.U10.21 (`self._bmp.setup()` takes no parameters), A.U3.05 (config read → console), A.U2.10
  (numbers), A.U11.27 (`_set_lock` held by the rung), A.U30.19
- **Site**: `src/asy_bmp3xx_driver.py:198-225` and two new methods
- **Change**: `_apply_stored_config(self) -> int` (new, the HEAD `:209-223` body): a failed config read →
  `self.pr.err("Error reading config data!")` (console), `return 1`; `await self.set_trigger_s(cfg_values[0])`; the three
  chip writes in `try`, on failure `report_if_fatal(e)`, `await self.pr.err_s("Error setting config data:", e,
  errno=_ERR_CHIP_SET)`, `return 2`; `return 0`; comment "# 0 applied, 1 config unreadable (no bus rung), 2 a chip write
  failed". `_init_bmp()`: `self._err_cnt_internal = 0`; `try: await self._bmp.setup()` `except Exception as e:
  report_if_fatal(e); await self.pr.err_s("Error in initial setup:", e, errno=_ERR_INIT); await self._init_failed();
  return False`; `self.pr.one("Setting sensor config at startup.")`; `code = await self._apply_stored_config()`; `if
  code == 2: await self._init_failed()`; `if code: return False`; `await self._init_done()`; `self.pr.one("initialized")`;
  `return True`. `_recover_device(self) -> bool`: `async with self._set_lock:` `try: await self._bmp.reset()` `except
  Exception as e: report_if_fatal(e); await self.pr.err_s("Soft reset failed:", e, errno=_ERR_CHIP_SET); return False`;
  `return await self._apply_stored_config() == 0`.
- **Resolved**: A.U15.R03 (3) calls `_init_failed()` "before the chip-write failure (errno 13 …/`_apply_stored_config()`'s
  errno-13 branch)"; `_apply_stored_config()` also runs inside `_recover_device()`, where calling `_init_failed()` (a
  controller rung) from inside the participant rung would nest two ladder steps. So the helper returns a code and only
  `_init_bmp()` calls `_init_failed()` for a chip-write failure (agent precision of A.U15.R03, OR2.c list).
- **Unit**: U15 (stages U2, U3, U10 as for M.SRC_SENS.043; U30 handler)
- **Depends**: M.SRC_SENS.042; A.U10.R01, A.U13.R01, A.U11.27
- **Blast carried by**: streak tests `tests/test_asy_bmp3xx_driver.py:1400-1411, 1977-1988` and the new rung cases →
  A.U15.R03/A.U10.R01 (TEST_UNIT); four tiers of the mid-operation reset → A.U15.R03 (TEST_UNIT, TWIN incl.
  `_bmp3xx_chip.py` reset values A.U25.13, HW_DEV `bmp3xx_same_device_rw_concurrency.py`); SPEC A.4 → A.U15.R03
- **Kind**: code

### M.SRC_SENS.045 Push callbacks, trigger setter and the shared divider
- **From**: A.U15.26 (`set_trigger_secs()` via `type_or_range_error()`), A.U10.43 (`set_trigger_s`,
  `_push_trigger_s`), A.U15.40 (2) (`_base_trigger()` goes → `SensorReader`'s shared divider), A.U10.44 (divider named
  `_trigger_loop`), A.U2.10 (21 → `_ERR_BAD_ARG`)
- **Site**: `src/asy_bmp3xx_driver.py:251-278, 347-359`
- **Change**: `_push_trigger_s()` (body as HEAD, calls `set_trigger_s`); the three other push callbacks unchanged.
  `_base_trigger()` goes. `async def set_trigger_s(self, value: float) -> bool:` `is_error, secs =
  type_or_range_error(value, _VAL_SAMPLE_INTERVAL[0])`; on `is_error`: `await self.pr.err_s("Error setting trigger
  interval:", value, errno=_ERR_BAD_ARG)`, `return False`; `await self._trigger_period.set_value(secs)`; `return True`.
- **Resolved**: A.U15.40 names the shared coroutine `_divide_trigger()`; A.U10.44 (U10, earlier) names every task
  coroutine `_<what>_loop` and maps `_base_trigger` → `_trigger_loop` — the shared primitive takes A.U10.44's name
  (`SensorReader._trigger_loop()`), and `start_asy_trigger()` creates it (agent, 2026-10-01; routed to SRC_CORE as
  GAP-8).
- **Unit**: U15 (stage U10: `_base_trigger` → `_trigger_loop` rename in place, removed in U15)
- **Depends**: M.SRC_SENS.041, M.SRC_SENS.042
- **Blast carried by**: `tests/test_asy_bmp3xx_driver.py:868-930` (`45.7` → `False`, NaN/inf, `True`) → A.U15.26
  (TEST_UNIT); `_base_trigger` test callers → A.U15.40; SPEC M.4 sentence → A.U15.26 (SPEC)
- **Kind**: code

### M.SRC_SENS.046 Starters, timer arm and the reader loop
- **From**: A.U10.12 (`get_trigger_starters()`), A.U15.41 (arm failure wakes and ends the task), A.U10.44 (names),
  A.U15.43 (`_read_loop() -> None`, starter types)
- **Site**: `src/asy_bmp3xx_driver.py:280-306, 385-394`
- **Change**: `start_asy_read(self) -> asyncio.Task[None]` over `_read_loop()`; `start_asy_trigger(self) ->
  asyncio.Task[None]` over `self._trigger_loop()`; `start_timer()`: `self._trigger_timer.init(period=1000,
  mode=Timer.PERIODIC, callback=lambda _b: self._base_trigger_event.set())` in `try`, `except (MemoryError, OSError) as
  e: self._timer_failed(e, self._base_trigger_event)` with A.U15.41's comment "# Alarm pool exhausted (ENOMEM) or no
  memory: wake the waiting task, which logs it and ends; its restart re-arms."; `get_task_starters(self) ->
  list[TaskStarter]: return [self.start_asy_read, self.start_asy_trigger]`; `get_trigger_starters(self) ->
  list[TimerStarter]: return [self.start_timer]`; `get_timer_starters(self) -> list[TimerStarter]: return []`;
  `stop_timer()` unchanged. `async def _read_loop(self) -> None:` `if not await self._init_bmp(): return`; the loop with
  `self._read_event`, `results = await self._read_bmp()`, `if not await self._error_check(results, condition=results[0] is None):
  return` (M.SRC_SENS.089), `await
  self._store_bmp(results)`.
- **Resolved**: —
- **Unit**: U15 (stage U10: A.U10.12 split and A.U10.44 names)
- **Depends**: M.SRC_SENS.045; A.U10.12, A.U15.41 (helpers in `SensorReader`)
- **Blast carried by**: generated collectors → A.U10.12 (GEN); `tests/test_asy_bmp3xx_driver.py:1759, 1818-1841, 1820`
  → A.U10.12/A.U15.41 (TEST_UNIT); `read_loop()) is False` asserts → A.U15.43
- **Kind**: code

### M.SRC_SENS.047 Reader getters/setters: catalog numbers, handlers, config snapshot
- **From**: A.U2.10 (e15/17/19/22 → 12, e16/18/20 → 13), A.U30.19, A.U15.43 (types)
- **Site**: `src/asy_bmp3xx_driver.py:170-183, 308-383`
- **Change**: `_read_sensor_dict()` and the three `get_*` forwarders log `errno=_ERR_CHIP_GET`; the three `set_*`
  forwarders `errno=_ERR_CHIP_SET`; each `except Exception as e:` starts with `report_if_fatal(e)`; `get_data()`/
  `get_dict_data()`/`get_dict_cfg()`/`get_error_counter()` unchanged but for the renamed `_VAL_` names and `self._bmp`.
- **Resolved**: —
- **Unit**: U30 (stage U2 numbers)
- **Depends**: M.SRC_SENS.040
- **Blast carried by**: number asserts → A.U2.10 (TEST_UNIT)
- **Kind**: code

### M.SRC_SENS.048 `BMP3XX_I2C`: session, conversion wait, own burst buffer, bool bus results
- **From**: A.U15.40 (1) (`DeviceSession`, `BMP3xx_DeviceSession` goes), A.U10.38 (its rename to
  `BMP3XX_DeviceSession`: superseded by A.U15.40), A.U10.35 (`_i2c_bmp3xx`, `sea_level_pressure`), A.U31.11
  (`_wait_time` goes), A.U30.07 (3) (`_pt_burst`), A.U15.25 (3) (conversion wait), A.U31.11 (its `sleep_ms` form),
  A.U13.09 (`:436, :507, :621, :641`, `_wait_status_bits`, `:644`), A.U13.10 (`_read_register()` via
  `get_register_bytes()`; its `:445-447` site is superseded by A.U30.07), A.U10.45 (`:502, :619, :628` messages),
  A.U27.03 (`:424-426` comment trigger), A.U15.27 (`get_pressure_altitude()`), A.U10.21 (`setup()`), A.U2.10
  (`_REG_ERR_CMD_BIT`), A.U10.31 (unquote `"BMP3xx_DeviceSession"`, `"tuple[int, int, int]"`), A.U15.25 (6) (coefficient
  comment)
- **Site**: `src/asy_bmp3xx_driver.py:397-646`
- **Change**: `BMP3xx_DeviceSession` goes. `__init__(self, i2c: I2C, address: int = 0x77)`: `self._i2c_bmp3xx =
  DeviceSession(I2CDevice(i2c, address))`; `self._pt_burst = bytearray(_PT_BURST_LEN)`; no `_wait_time`, no
  `sea_level_pressure`. `_get_osr_setting()`: its `:424-426` comment → "# The stub types indexing a const() tuple as Any;
  the int annotation narrows it. Removal trigger: SPECIFICATION.md B.15." `_read()` (one device-session hold): read the
  OSR byte (`get_register_struct(_REGISTER_OSR, "B")`; `None` → `OSError("I2C bus not initialized")`; a reserved
  encoding raises `OSError` as `_get_osr_setting()` does), `wait_us = 939 + 2000 * (_OSR_SETTINGS[osr_p] +
  _OSR_SETTINGS[osr_t])`; the forced-mode write `if not await i2c.set_register_struct(_REGISTER_CONTROL, "B", 0x13): raise
  OSError("I2C bus not initialized")`; `await asyncio.sleep_ms((wait_us + 999) // 1000)` with A.U15.25's three-line
  comment; `_wait_status_bits(session, _STATUS_DATA_READY, _MEAS_TIMEOUT_MS)`; the burst `if not await
  i2c.get_register_into(_REGISTER_PRESSUREDATA, self._pt_burst): raise OSError("I2C bus not initialized")` and `adc_p`/
  `adc_t` from `self._pt_burst` inside the same `async with` (no await between; one comment line says so); the float
  compensation after it unchanged. `_read_register()`: `value = await i2c.get_register_bytes(register, length)`; `None`
  → `OSError("I2C bus not initialized")`. `_set_osr_setting()`: `ValueError(f"oversampling must be one of:
  {_OSR_SETTINGS}")`; `if not await i2c.set_bits(…): raise OSError("I2C bus not initialized")`. `_read_coefficients()`
  comment → A.U15.25 (6)'s text. `_wait_status_bits(self, session: DeviceSession, mask, timeout_ms)`: `status is None` →
  `raise OSError("I2C bus not initialized")` before the ready test; `await asyncio.sleep_ms(_STATUS_POLL_MS)`.
  `get_altitude()` → `get_pressure_altitude()` using `_SEA_LEVEL_PRESSURE_HPA` (the `<= 0` guard goes).
  `get_config_snapshot() -> tuple[int, int, int]` (unquoted). `set_filter_coefficient()`: `ValueError(f"filter
  coefficient must be one of: {_IIR_SETTINGS}")`; bool-checked `set_bits`. `async def setup(self) -> bool:` probe, chip
  ID (`RuntimeError(f"failed to find BMP3XX, chip ID {hex(chip_id)}")`), coefficients, `reset()`, `return True`.
  `reset()`: bool-checked CMD write, `await asyncio.sleep_ms(_RESET_SETTLE_MS)`, `err is None` → `OSError("I2C bus not
  initialized")`, `err & _REG_ERR_CMD_BIT` → `RuntimeError("reset command rejected (ERR_REG cmd_err set)")`.
- **Resolved**: A.U15.25's L1 expects `0.128939 s` through `asyncio.sleep`; A.U31.11 makes it `sleep_ms(129)` (U31
  conflict row 2). A.U13.10's BMP burst site is replaced by A.U30.07's driver-owned buffer (U30 note 6). A.U10.38's
  session rename is moot (A.U15.40 removes the class).
- **Unit**: U31 (latest; stages U2, U10 (names, messages), U13 (bool bus results, `get_register_bytes`), U15 (session,
  wait, rename, sea level), U27 (comment), U30 (burst buffer))
- **Depends**: M.SRC_SENS.011, M.SRC_SENS.013, M.SRC_SENS.040; A.U15.40's `DeviceSession`
- **Blast carried by**: `tests/test_asy_bmp3xx_driver.py` read-path, `:185-209` `_BadBurstRead`, `:298-307`, `:351-364`,
  `:584-619`, `:798-812`, `:1541`, `:1857-1858` → A.U15.25/A.U30.07/A.U13.09/A.U13.10/A.U15.27/A.U10.21 (TEST_UNIT);
  `tests/_bus_hazard_catalog.py` `seed_bmp_ready(chip_id=)`, `_exercise_bmp3xx` (`get_pressure_altitude`),
  `test_bus_hazard_multi_device.py:114` per-ID loop → A.U15.25/A.U15.27 (TEST_HELP, TEST_UNIT); four tiers → A.U15.25
  blast; SPEC M.4 rows → A.U15.05/A.U15.25/A.U31.11 (SPEC); `bmp3xx_plausibility_read.py:24` comment → A.U15.40 (HW_DEV)
- **Kind**: code

### M.SRC_SENS.089 A pre-sync `TS` of `None` is not a failed read
- **From**: adherence finding (A.U10.06 × `SensorReader._error_check()`); A.U10.06 (a pre-sync sample is published with
  `TS` `None`), A.U15.22 (4) (ISL29125's `condition` precedent), A.U3.03/A.U10.R01 (what a counted failure costs)
- **Site**: `src/asy_bmp3xx_driver.py:392` (`_read_loop()`'s streak call); the same call in SCD30 (M.SRC_SENS.090),
  SGP40 (M.SRC_SENS.091) and ISL29125 (M.SRC_SENS.083)
- **Change**: `if not await self._error_check(results, condition=results[0] is None): return` with one comment line "#
  A failed read clears every measured value; TS alone is None until the first NTP sync, which is no failure." The
  rule for all four readers: the streak counts a cycle only when its first measured value is `None` (each reader's
  failure path clears all of them together), never for the trailing `TS`.
- **Resolved**: A.U10.06 makes `utc_now()` return `None` until the NTP client's first sync and publishes the sample
  with `TS` `None`, but `_error_check()` counts a cycle failed when ANY result element is `None`
  (`base_classes.py:221`) and all four readers carry `TS` last in that tuple — so every pre-sync cycle (every boot
  before Wi-Fi and NTP, every twin run: the twin never syncs) would climb the recovery ladder (device reset, bus clear)
  and end the task. No action carries it (grep `_error_check` with `utc_now`/`TS` over `audit/actions/`: none). The
  merged state follows A.U10.06's own stated intent ("a sample taken before the first sync is published"): the reader
  says what a failure is through the existing `condition` keyword; `_error_check()` and WIFI's `(None,)` call stay
  as they are. Agent decision (2026-10-01), OR2.c list; the alternative — `_error_check()` testing `results[0] is
  None` for every caller — is SRC_CORE's to prefer instead (GAP-15).
- **Unit**: U10 (with A.U10.06: from that unit on a `TS` can be `None`)
- **Depends**: A.U10.06
- **Blast carried by**: L1 per reader "a pre-sync read steps no streak and publishes its values with `TS` `None`" and
  the twin boot suites (no NTP) → GAP-15 (TEST_UNIT, TWIN); SPEC C.7 `_error_check()` bullet → GAP-15 (SPEC)
- **Kind**: code

## src/asy_scd30_driver.py

### M.SRC_SENS.049 Docstring and imports: plain guard, no shim, config reader
- **From**: A.U15.02 (plain import guard; `cast`, `T`, `TypeVar` go), A.U15.43 (`Any`/`Coroutine`/`Callable` out),
  A.U10.37, A.U15.40 (`Lockable` goes, `DeviceSession` in), A.U15.12 (`SensorReaderConfig` replaces `SensorReader`),
  A.U4.04 (`compare_before_write`, `schema_dict`/`type_or_range_error` as the rewrite uses them), A.U30.05 (`unpack`
  goes), A.U10.06 (`utc_now`; `time` becomes unused), A.U5.02 (the runtime `AsyFramManager` import goes), A.U30.19,
  adherence (docstring line 6 lists the five data fields; A.U15.12 adds two)
- **Site**: `src/asy_scd30_driver.py:5-41`
- **Change**: docstring line 6 → "…; SCD30_Reader runs the read loop plus an IRQ-pin self-healing trigger, and publishes
  the readings with wet bulb, dew point and the forced-recalibration readiness code (see SPECIFICATION.md Part C)." Imports:
  `asyncio`, `math`, `namedtuple`, `from struct import unpack_from`, `from machine import Pin, Timer`, `const`,
  `math_helpers`, `from asy_i2c_driver import I2C, I2CDevice`, `from asy_base_classes import DeviceSession,
  SensorReaderConfig, report_if_fatal, utc_now`, `from asy_config_manager import compare_before_write, make_dict,
  name_cfg, type_or_range_error`, `from asy_crc_checks import CRC8`, `from asy_print_log import DEFAULT_LOG, LogConfig`
  (plus the result-word constants of A.U19.16). Guard: `try: from typing import TYPE_CHECKING` / `except ImportError:
  TYPE_CHECKING = False`. `TYPE_CHECKING` block: `from asy_base_classes import TaskStarter, TimerStarter`; `from
  asy_config_manager import CfgValue, ConfigSchema, FieldSchema`; `from asy_print_log import ErrorLog`.
- **Resolved**: A.U15.02 co-lands with A.U15.43 (`:26-41`), A.U15.01 and A.U13.09 — one import block.
- **Unit**: U15 (stages U10 module names, U19 result words, U30 `report_if_fatal`)
- **Depends**: A.U4.01 (`compare_before_write()`), A.U15.40, A.U10.46
- **Blast carried by**: `tests_scripts/test_strip_type_checking.py:96-98` comment → A.U15.02 (TSC); BACKLOG `:765-767`
  clause → A.U15.02/U36 (DOCS); SPEC C.4.2/C.10 → A.U15.02 (SPEC)
- **Kind**: code

### M.SRC_SENS.050 Constants: address, ranges, waits, catalog names, apply order, module order
- **From**: A.U15.28 (`_SCD30_DEFAULT_ADDR` → `_SCD30_ADDR`), A.U15.40 (3) (limit constants above the `_VAL_*` block),
  A.U15.01 (range constants), A.U8.07 + A.U31.09 (wait constants and tags, ms), A.U2.11 + A.U2.04 (catalog block), A.U4.04
  (`_APPLY_ORDER`), A.U4.05 (`_temp_offset_ticks()`), A.U15.09 (`_CONT_MEAS_FIELD`), A.U15.12 (1) (FRC schema tuples)
- **Site**: `src/asy_scd30_driver.py:44-89`
- **Change**: order (A.U15.40 (3)): address and command constants; the limit constants (`_MEAS_INTERVAL_MIN` …
  `_WORD_CRC_BYTES`, `:72-85` moved here); A.U15.01's `_CO2_MIN_PPM`…`_HUM_MAX_PCT` under its comment; the waits `# @tunable
  scd30.cmd_response_wait_ms = 50` / `_CMD_RESPONSE_WAIT_MS = const(50)`, `# @tunable scd30.asc_enable_wait_ms = 10` /
  `_ASC_ENABLE_WAIT_MS = const(10)`, `# @tunable scd30.soft_reset_wait_ms = 2500` / `_SOFT_RESET_WAIT_MS = const(2500)`,
  `# @tunable scd30.start_trigger_period_ms = 500` / `_START_TRIGGER_PERIOD_MS = const(500)`; the catalog block
  `_ERR_INIT = const(10)`, `_ERR_READ = const(11)`, `_ERR_CHIP_GET = const(12)`, `_ERR_CHIP_SET = const(13)`,
  `_ERR_BAD_ARG = const(21)`; `_SCD30_ADDR = const(0x61)  # Interface Description 1.1.1: the address is fixed` ; then the
  `_VAL_*` block (M.SRC_SENS.051), `_CONT_MEAS_FIELD` with A.U15.09's exact three-line comment, `_APPLY_ORDER =
  const(("TempOffset", "MeasInterval", "AmbPres", "Altitude", "ForceCalRef", "SelfCal"))` (A.U4.04's order in A.U10.40's
  keys; a tuple of literals `const()` folds); module function `_temp_offset_ticks(offset: float) -> int: return
  int(offset * 100 + 0.5)` with the comment "# Nearest 0.01 degC tick, not truncation: in float32 130 of the 2001
  two-decimal inputs land one tick low when truncated (offset is validated >= 0 first)."
- **Resolved**: A.U8.07's float-second constants → A.U31.09's integer ms (U31 conflict row 1). A.U4.04's `_APPLY_ORDER`
  lands in U4 with the HEAD keys; A.U10.40's rename script updates the tuple in U10.
- **Unit**: stages U2, U4, U8, U10, U15, U31
- **Depends**: A.U2.01, A.U8.01
- **Blast carried by**: Part N rows → A.U8.07/A.U31.09 (SPEC); twin/test address readers → A.U20.28 (GEN) and A.U35.19
  (TEST_UNIT); release-note line D4.61 → A.U4.05 via U37 (DOCS)
- **Kind**: code

### M.SRC_SENS.051 Schema, tags and requirements
- **From**: A.U10.39/A.U10.40 (`_VAL_TEMP_OFFSET` `TempOffset`, `_VAL_MEAS_INTERVAL` `MeasInterval`, `_VAL_AMB_PRES`,
  `_VAL_ALTITUDE`, `_VAL_FORCE_CAL_REF`, `_VAL_SELF_CAL`), A.U15.12 (1)-(2) (`FRCNoise`/`FRCRate`/`FRCWindow` tuples and
  tags, `FRCState`/`FRCWait` measurement tags), A.U15.11 (ForceCalRef/SelfCal descriptions and their source comment),
  A.U15.44 (Altitude help), A.U23.23 (`ignoredWhenSet=AmbPres`), A.U6.17 (`alwaysExecuted=true` on AmbPres, ForceCalRef,
  ContMeas), A.U23.16 (`defaultValue=true` goes from ContMeas), A.U15.09 (ContMeas comment), A.U6.19 (`TS` epoch),
  A.U36.514 (`:106` "(Part L.5)" → "(Part L.6.4)"), A.U15.10 + A.U10.43 (`@limits trigger_s 1..1800`), A.U5.03 +
  A.U10.38 (`@wiring fram_target FRAMManager log optional kwarg`)
- **Site**: `src/asy_scd30_driver.py:57-112`
- **Change**: the six chip tuples with the new names/keys (defaults `None`, bounds unchanged); the FRC tuples
  `_VAL_FRC_NOISE = const((("FRCNoise", "float", 20.0, 1.0, 500.0, None),))`, `_VAL_FRC_RATE = const((("FRCRate",
  "float", 10.0, 0.1, 1000.0, None),))`, `_VAL_FRC_WINDOW = const((("FRCWindow", "int", 60, 20, 3600, None),))` with the
  comment "# FRC readiness settings: noise floor 2 x the repeatability (owner, 2026-09-29: 1-2 x); rate and window
  provisional until measured on the bench (agent, 2026-09-29)." Tags (one line each): `AmbPres … alwaysExecuted=true`;
  `Altitude … description="Only used while Ambient Pressure is 0; a pressure value overrides it." ignoredWhenSet=AmbPres`;
  the source comment "# Interface Description 1.4.6 and its FRC section (p14), Low Power Mode note (6 min / 5
  intervals), Field Calibration note (the configured interval)." above `ForceCalRef … description="A calibration run,
  carried out on every Apply. Only valid after continuous measurement at the configured interval for 6 minutes or 5
  intervals, whichever is longer, in stable air of known CO2 (400-2000 ppm). FRC Readiness shows when that holds."
  alwaysExecuted=true`; `SelfCal … description="Needs 7 days of uninterrupted power with at least 1 hour of fresh air every
  day; a power loss in the first 7 days restarts the search."`; the three FRC setting tags (A.U15.12 (2)); `ContMeas`'s
  tag without `defaultValue`, with `alwaysExecuted=true`; measurement tags gain `FRCState` and `FRCWait` (A.U15.12's text)
  and `TS … format=epoch` (no unit). `:105-107` comment's "(Part L.5)" → "(Part L.6.4)"; the two `@requires` lines
  unchanged; `# @wiring fram_target FRAMManager log optional kwarg`; new `# @limits trigger_s 1..1800` under the two-line
  comment of A.U15.10 ("# Stuck-pin fallback reads after 2 * trigger_s ticks of 500 ms: at least one full second, at
  most the chip's longest measurement interval (agent, 2026-09-29).").
- **Resolved**: The `Altitude` tag line carries A.U15.44's description and A.U23.23's key together (both name the other,
  "same tag line"). `ContMeas`: A.U6.17 adds `alwaysExecuted=true` and A.U23.16 removes `defaultValue=true` on the same
  line — both apply.
- **Unit**: U23 (latest; stages U6, U10, U15, U36b's pointer)
- **Depends**: A.U6.17 (key), A.U6.19 (key), A.U23.23 (key), A.U15.12
- **Blast carried by**: generated definitions and `html/definitions/*.json` (descriptions, `alwaysExecuted`,
  `ignoredWhenSet`, FRC fields, keys) → A.U15.11/A.U15.12/A.U15.44/A.U6.17/A.U23.16/A.U23.23/A.U6.04 (GEN); page warning,
  unset toggle → A.U23.16/A.U23.23 (WEB); mock data rows → A.U15.12/A.U10.40 (WEB); `tests_scripts/test_buildgen_limits.py`
  and `test_buildgen_validate.py` limit cases → A.U15.10 (TSC); `test_buildgen_web_tag.py:409` field set → A.U15.12
- **Kind**: code

### M.SRC_SENS.052 `SCD30_Reader`: a config reader with a RAM-only config log
- **From**: A.U15.12 (1), (3), (6) (`SensorReaderConfig`, `cfg_path`, FRC state), AC_NOTES 13 + the U15 lead note
  (`CFGMGR_SCD30` RAM-only), A.U4.03 (its "SCD30 cannot become a `SensorReaderConfig`" note: superseded for the three FRC
  keys, U15 register fix 13), A.U5.02 (constructor tail), A.U10.43 (`trigger_s`, `trigger_half_ticks`), A.U10.35 (private
  attributes), A.U15.R01 (1) (`_recovery_bus`), A.U10.38 (class name kept)
- **Site**: `src/asy_scd30_driver.py:118-145`
- **Change**: `class SCD30_Reader(SensorReaderConfig)`; `__init__(self, i2c: I2C, irq_pin: int, trigger_s: int = 3,
  max_module_error: int = 5, name_ext: str = "", cfg_path: str = "", log: LogConfig = DEFAULT_LOG)`;
  `super().__init__(SCD30(None, None, None, None, None, None, None, None), _NAME, _VAL_FRC_NOISE + _VAL_FRC_RATE +
  _VAL_FRC_WINDOW, max_module_error=max_module_error, name_ext=name_ext, cfg_path=cfg_path, log=log,
  cfg_log=LogConfig(None, log.history_length, log.debug))` with the comment "# CFGMGR_SCD30 stays RAM-only: no extra FRAM
  chunk for the FRC settings (owner, 2026-09-29)."; `self._scd = SCD30_I2C(i2c)`; `self._recovery_bus = i2c`;
  `self._irq_pin = Pin(irq_pin, mode=Pin.IN)`; `self._base_trigger_event`, `self._read_event`; `self._start_trigger_timer
  = Timer()` under the bare-Timer comment of M.SRC_SENS.042; `self._trigger_half_ticks = 2 * int(trigger_s)`;
  `self._scd_timer_triggers = 0`; the FRC state of A.U15.12 (3) (`_frc_interval_s`, `_frc_count`, `_frc_idle_ticks`,
  `_frc_measuring`, the window sums as floats, `_frc_verdict`), all RAM-only.
- **Resolved**: The lead note (AC_NOTES 13): the three settings are file-stored config, their logger RAM-only; A.U15.12's
  "brings its own `CFGMGR_SCD30` FRAM chunk" is superseded. `SensorReaderConfig` has no way today to give its
  `ConfigManager` a different logging config than the module's own: the `cfg_log` parameter is new — routed to SRC_CORE
  (GAP-9, A.U5.02's `SensorReaderConfig` signature).
- **Unit**: U15 (stages U5 tail, U10 names)
- **Depends**: M.SRC_SENS.049-051; A.U5.02, GAP-9
- **Blast carried by**: generated construction (`cfg_path=`), `buildgen/definitions.py:97` → `True` with the RAM-only
  companion, setup batch → A.U15.12 (6) (GEN); SPEC A.7 chunk order: no `CFGMGR_SCD30` chunk (wozi's count unchanged),
  CLAUDE.md FRAM list's named exception → GAP-10 (SPEC, DOCS: A.U15.12's blast still says "wozi 17 chunks");
  `tests/_sensortask_scenarios.py:222-223` (one chunk, not two) → GAP-10 (TEST_HELP); `tests/test_asy_scd30_driver.py`
  `make_reader()` with `cfg_path` → A.U15.12 (TEST_UNIT)
- **Kind**: code

### M.SRC_SENS.053 SCD30 config I/O through the chip store and the file store
- **From**: A.U4.04 (`_get_mgr_cfg()`/`_set_mgr_cfg()`, `_snapshot_dict()`; `_set_dict_cfg()`/`_read_sensor_dict()` go),
  A.U15.09 (ContMeas via `_CONT_MEAS_FIELD`), A.U4.05 (`resolution={"TempOffset": _temp_offset_ticks}`), A.U15.12 (1)
  (FRC keys routed to the file store; nine-key schema; merged `get_dict_cfg()`; a chip-key snapshot failure refuses the
  whole body), A.U19.16 (result-word constants), A.U11.S02 (the `dispatch` annotation goes with the rewrite), A.U2.11
  (12/21)
- **Site**: `src/asy_scd30_driver.py:147-159, 244-298`
- **Change**: module function `_snapshot_dict(snap: tuple[float, int, int, int, int, bool]) -> dict[str, CfgValue]` (the
  six chip keys). `_get_mgr_cfg(self, cfg)`: chip keys from one `get_config_snapshot()` (a failure logs
  `_ERR_CHIP_GET` and yields `None` for them), FRC keys from `await super()._get_mgr_cfg(<FRC part>)`. `_set_mgr_cfg(self,
  data, cfg_vals)`: exactly A.U4.04 (1)-(6) for the chip keys (snapshot first; failure → `(False, {})`, nothing written,
  one `_ERR_CHIP_GET`; `ContMeas` out of `data`; `compare_before_write(rest, cfg_vals, current, always=("AmbPres",
  "ForceCalRef"), resolution={"TempOffset": _temp_offset_ticks})`, each Invalid key logged `_ERR_BAD_ARG`; writes in
  `_APPLY_ORDER` through the `set_*` forwarders, a failed one → `FAILED`; `ContMeas` last: `is_error, flag =
  type_or_range_error(value, _CONT_MEAS_FIELD)`, `is_error` → `INVALID` (logged 21), `flag` True → `VALID` (no write),
  False → `stop_continuous_measurement(value=False)` → `VALID`/`FAILED`), plus A.U15.12's routing: the FRC keys go to
  `await super()._set_mgr_cfg(<FRC part>, <FRC schema>)` and their results are merged; a body with any chip key whose
  snapshot fails is refused as a whole, FRC keys included (OR89.a (6)); a body of FRC keys only takes no snapshot; a
  successful `MeasInterval` write updates `_frc_interval_s` and calls `_frc_reset()`, a successful `AmbPres` write calls
  `_frc_reset()` and sets `_frc_measuring = True`, a successful `ContMeas=false` sets it `False`, resets and republishes
  (A.U15.12 (4)). `get_dict_cfg()` → `await self._get_dict_cfg(self.name, <nine-key schema>)` (no callback);
  `get_cfg_schema()` returns the nine-key schema (the comment `:252-254` → "# The nine keys a PUT may carry: six stored
  on the chip, three in the config file.").
- **Resolved**: A.U4.03/A.U4.04 wrote the chip store for a plain `SensorReader`; A.U15.12 makes the reader a
  `SensorReaderConfig` — U15 register fix 13 settles the composition (chip store for six keys, file for three).
  `always=` stays in the firmware: A.U4.04 calls it "the stopgap until U6 derives the never-Unchanged
  class from `@web` tags", but the tags are comments the firmware never reads (L.6.4), so A.U6.17's derivation serves
  the website and tests only and the backend keeps its own tuple; the two are pinned against each other by an L0 check
  (the tuple equals the SCD30 fields tagged `alwaysExecuted=true`, `ContMeas` aside) — GAP-11 (TSC). Agent reading,
  OR2.c list.
- **Unit**: U15 (stages U4 chip store with the HEAD base class; U19 result words)
- **Depends**: A.U4.01, A.U4.03 (write path on `SensorReader`), A.U11.27 (`_set_lock` around it), M.SRC_SENS.052
- **Blast carried by**: `asy_webserver_service._put_sensors()` (unchanged call) → A.U4.04 (SRC_NET); tests
  `tests/test_asy_scd30_driver.py:950-1115` and the new L1/L2 cases, `tests/test_setter_microdot_integration.py:686-760`,
  `_sensortask_scenarios.py:898-905`, twin `:394-411`, `tests_js/live-backend-put-matrix.test.js` → A.U4.04/A.U15.09/
  A.U15.12 (TEST_UNIT, TEST_HELP, TWIN, WEB); `tests_hardware/manual/manual_persistence.py:36-48` → A.U4.04 (HW_BENCH);
  SPEC C.4.3/C.4.4/C.5.2/A.4/A.8 → A.U4.04/A.U15.12 (SPEC)
- **Kind**: code

### M.SRC_SENS.054 `_init_scd()`: first-start comment, interval cache, the participant rung
- **From**: A.U15.04 (comment), A.U10.10 (`pr.setup()` leaves), A.U15.R01 (2)-(3) (`_recover_device()`,
  `_init_failed()`/`_init_done()`), A.U15.12 (3)-(4) (interval read, `_frc_reset()`), A.U2.11, A.U30.19
- **Site**: `src/asy_scd30_driver.py:161-172` and a new method
- **Change**: `_init_scd()`: comment → A.U15.04's "# Continuous measurement is never started here: the first
  ambient-pressure PUT starts it, and the chip keeps it across power cycles (SPECIFICATION.md A.4; owner, 2026-09-26).";
  `self._err_cnt_internal = 0`; `try: await self._scd.setup(); self._frc_interval_s = await
  self._scd.get_measurement_interval()` `except Exception as e: report_if_fatal(e); await self.pr.err_s("Error in initial
  setup:", e, errno=_ERR_INIT); await self._init_failed(); return False`; `self._frc_reset()`; `await self._init_done()`;
  `self.pr.one("initialized")`; `return True`. `_recover_device(self) -> bool`: A.U15.R01 (2) (under `self._set_lock`,
  `await self._scd.reset()`, failure → `_ERR_CHIP_SET`, `False`; else `True`).
- **Resolved**: —
- **Unit**: U15 (stages U2, U10; U30 handler)
- **Depends**: M.SRC_SENS.052, M.SRC_SENS.057; A.U10.R01, A.U13.R01
- **Blast carried by**: streak/rung tests `tests/test_asy_scd30_driver.py:1286-1331` and new cases, notification
  integration `ErrCount`s → A.U15.R01/A.U3.03 (TEST_UNIT); four tiers (L3 `bus_concurrency_cross_device_scd30_sgp40.py`
  reset step) → A.U15.R01 (HW_DEV); twin CI Runs 3/4/5c → A.U15.R01/A.U13.R01 (SCR); SPEC A.4 → A.U15.04/A.U15.R01
- **Kind**: code

### M.SRC_SENS.055 Read, store, republish and the stuck-pin task
- **From**: A.U10.06 (timestamp outside the `try`; guard on values), A.U15.12 (3)-(4) (new-data bool, FRC steps,
  `_republish()`, idle ticks), A.U15.03 (saturating tick count, comment), A.U10.43 (`_trigger_half_ticks`), A.U15.41
  (arm failure; re-arm on restart), A.U10.44 (`start_asy_irq`/`_irq_loop`, `_read_loop`), A.U10.12 (the 500 ms tick stays
  a timer starter), A.U8.07/A.U31.09 (`_START_TRIGGER_PERIOD_MS`), A.U15.43 (`-> None`, types), A.U2.11, A.U30.19
- **Site**: `src/asy_scd30_driver.py:174-235, 399-420`
- **Change**: `_read_scd()`: `timestamp = utc_now()`; the FRC config values read once (A.U15.22's capture rule, A.U15.12
  (4)); `try: new_data = await self._scd.read_measurement(); co2 = …; …` `except Exception as e: report_if_fatal(e);
  co2 = temperature = humidity = None; new_data = False; await self.pr.err_s("Read failed:", e, errno=_ERR_READ)`;
  returns the results tuple and `new_data` beside it. `_store_scd()`: returns when any of CO2/Temp/Hum is `None`; stores
  `SCD30(CO2, Temp, Hum, WetBulb, DewPoint, FRCState, FRCWait, TS)` with the FRC step of A.U15.12 (4) on new data only.
  `start_timer()`: `self._start_trigger_timer.init(period=_START_TRIGGER_PERIOD_MS, …)` in `try`, `except (MemoryError,
  OSError) as e: self._timer_failed(e, self._base_trigger_event)` (A.U15.41's comment); the IRQ arm unchanged.
  `get_task_starters(self) -> list[TaskStarter]: return [self.start_asy_read, self.start_asy_irq]`;
  `get_timer_starters(self) -> list[TimerStarter]: return [self.start_timer]` (no trigger starter: SCD30 reads on its own
  data-ready edge, A.U10.12). `_read_loop(self) -> None`: init, then per trigger `self._scd_timer_triggers = 0`, read,
  `_error_check` with M.SRC_SENS.090's condition, store; `return` where HEAD returns `False`. `_irq_loop(self) -> None`: first `if self._timer_error is
  not None: self._timer_error = None; self.start_timer()` (A.U15.41 re-arm); `while True: await
  self._base_trigger_event.wait()`; `if await self._timer_fault(): return`; `if self._irq_pin.value() == 1 and
  self._scd_timer_triggers < self._trigger_half_ticks: self._scd_timer_triggers += 1` with A.U15.03's trailing comment
  ("# ticks with the pin high since the last read, not necessarily consecutive; capped at the threshold"); the FRC idle
  tick step and republish (A.U15.12 (4)); the `>=` test and `read_event.set()` as today.
- **Resolved**: A.U15.03 (saturate at `trigger_half_sec`) and A.U10.43 (rename to `trigger_half_ticks`) co-land on the
  same lines. A.U15.41 re-arms inside `scd_init_irq()`, which A.U10.44 renames `_irq_loop()`.
- **Unit**: U15 (stages U8/U31 period constant, U10 names/split, U30 handler)
- **Depends**: M.SRC_SENS.052, M.SRC_SENS.057; A.U15.12's `SensorReader._republish()` (SRC_CORE)
- **Blast carried by**: tests `tests/test_asy_scd30_driver.py:668-702, 726-786` and the FRC/staleness/saturation L1
  cases, L2 `tests/test_digital_twin_scd30.py` → A.U15.03/A.U15.12/A.U15.22/A.U15.41 (TEST_UNIT, TWIN); SPEC C.9.1/M.2 →
  A.U10.14/A.U15.03/A.U15.12 (SPEC)
- **Kind**: code

### M.SRC_SENS.056 Reader forwarders: catalog numbers and handlers
- **From**: A.U2.11 (e14/16/18/20/22/24 → 12, e13/15/17/19/21/23/25 → 13), A.U30.19, A.U15.27 (SCD30 keeps
  `get_altitude()`/`set_altitude()`: no change), A.U15.43 (types)
- **Site**: `src/asy_scd30_driver.py:300-397, 422-435`
- **Change**: each forwarder logs `_ERR_CHIP_GET` or `_ERR_CHIP_SET`; each `except Exception as e:` starts with
  `report_if_fatal(e)`; `get_data()`/`get_dict_data()`/`get_error_counter()` unchanged but for `self._scd`.
- **Resolved**: —
- **Unit**: U30 (stage U2 numbers)
- **Depends**: M.SRC_SENS.050
- **Blast carried by**: number asserts `tests/test_asy_scd30_driver.py` (8), `tests/test_setter_microdot_integration.py:734,
  858-864`, `tests/test_notification_scd30_integration.py:211-216` → A.U2.11 (TEST_UNIT)
- **Kind**: code

### M.SRC_SENS.057 `SCD30_I2C`: fixed address, own session, range gate, copy-free decode
- **From**: A.U15.28 (no `address`), A.U15.40 (session), A.U10.35 (`_i2c_scd30`), A.U30.05 (`_words`, decode), A.U15.01
  (range gate, cached offset ticks), A.U15.02 (annotated locals), A.U13.09 (`:470, :480, :484, :608`), A.U31.09 (waits),
  A.U10.45 (`"CRC generation failed!"`), A.U15.08 (`AmbPres` comment), A.U4.05 (`set_temperature_offset()`), A.U10.21
  (`setup() -> bool`), A.U15.12 (4) (`read_measurement() -> bool`), A.U10.31 (unquote the snapshot annotation)
- **Site**: `src/asy_scd30_driver.py:438-630`
- **Change**: `SCD30_DeviceSession` goes. `__init__(self, i2c_bus: I2C)`: `self._i2c_scd30 =
  DeviceSession(I2CDevice(i2c_bus, _SCD30_ADDR))`; `self._buffer = bytearray(18)`; `self._words = bytearray(12)  # the six
  data words without their CRC bytes`; `self.crc = CRC8()`; the three cached readings; `self._temp_offset_ticks = 0`.
  `_send_dev_command()`: `RuntimeError("CRC generation failed")`; `if not await i2c.write(self._buffer, end=end_byte):
  raise OSError("I2C bus not initialized")`; `await asyncio.sleep_ms(_CMD_RESPONSE_WAIT_MS)`. `_read_dev_register()`:
  bool-checked write and readinto (`OSError("I2C bus not initialized")`), `await asyncio.sleep_ms(_CMD_RESPONSE_WAIT_MS)`,
  CRC check, `value: int = unpack_from(">H", self._buffer)[0]`, `return value`. `get_config_snapshot() -> tuple[float,
  int, int, int, int, bool]`. `set_self_calibration_enabled()`: `await asyncio.sleep_ms(_ASC_ENABLE_WAIT_MS)`.
  `set_ambient_pressure()`: comment → A.U15.08's "0x0010 starts continuous measurement, whose on/off status the chip keeps
  in NVM (Interface Description 1.4.1); whether the pressure value itself persists is undocumented." plus the NaN/
  truncation sentence (≤ 3 lines). `set_temperature_offset()`: sends `_temp_offset_ticks(offset)`, then
  `self._temp_offset_ticks = <those ticks>` after the write succeeded; its comment names the float32 reason (A.U4.05).
  `async def setup(self) -> bool:` probe, firmware-version read, `reset()`, `self._temp_offset_ticks = await
  self._read_register(_CMD_SET_TEMPERATURE_OFFSET)`, `return True`. `reset()`: `await
  asyncio.sleep_ms(_SOFT_RESET_WAIT_MS)`. `read_measurement(self) -> bool`: not-ready → `return False`; bool-checked
  `readinto` (`:608`); CRC loop; the copy-free decode of A.U30.05 (`for i in range(6)` into `self._words`, `co2,
  temperature, humidity = unpack_from(">fff", self._words)` as annotated locals, one comment line); the finiteness raise;
  A.U15.01's range raise `ValueError(f"reading outside measurement range (co2={co2}, t={temperature}, rh={humidity})")`
  with the temperature half `_TEMP_MIN_C <= temperature + self._temp_offset_ticks / 100 <= _TEMP_MAX_C`; the comment
  `:624-625` gains "and a finite value outside the datasheet ranges is rejected the same way"; the three cache
  assignments; `return True`.
- **Resolved**: A.U15.02 writes `co2: float = unpack(...)[0]` for each float; A.U30.05 replaces the slice decode with one
  `unpack_from(">fff", self._words)` into annotated locals (its Depends names A.U15.02) — A.U30.05's form. A.U15.01's
  offset cache lives on `SCD30_I2C`, updated by `set_temperature_offset()` after a successful write (A.U4.05's ticks).
- **Unit**: U31 (latest; stages U4 (offset rounding), U8 (waits named), U10 (names, message), U13 (bool bus results),
  U15 (address, session, range gate, bool read, shim), U30 (decode))
- **Depends**: M.SRC_SENS.011, M.SRC_SENS.013, M.SRC_SENS.050
- **Blast carried by**: tests `tests/test_asy_scd30_driver.py:91-105, 166-186, 397-, 434-451, 454-457` and new L1 cases
  (ranges, decode set, bus-down) → A.U15.01/A.U30.05/A.U13.09/A.U31.09/A.U15.22 (TEST_UNIT); every scripted `setup()`
  queue gains one register frame → A.U15.01 (TEST_UNIT, TEST_HELP `_bus_hazard_catalog.py:174-196`); twin chip answers
  0x5403 → A.U15.01 (TWIN); `FastAsyncSleep` `sleep_ms` → A.U31.09/A.U24.49 (TEST_HELP); four tiers → A.U15.01 blast;
  SPEC M.2 → A.U15.05/A.U15.08/A.U31.09 (SPEC); release note D4.62 → A.U15.01 via U37
- **Kind**: code

### M.SRC_SENS.090 SCD30: a pre-sync `TS` of `None` is not a failed read
- **From**: M.SRC_SENS.089's rule
- **Site**: `src/asy_scd30_driver.py:407` (`_read_loop()`)
- **Change**: `if not await self._error_check(results, condition=results[0] is None): return` with M.SRC_SENS.089's
  comment line.
- **Resolved**: see M.SRC_SENS.089.
- **Unit**: U10
- **Depends**: M.SRC_SENS.089
- **Blast carried by**: → GAP-15 (TEST_UNIT, TWIN, SPEC)
- **Kind**: code

## src/asy_sgp40_driver.py

### M.SRC_SENS.058 Imports, typing block and the backup group type
- **From**: A.U10.37, A.U15.40 (`Lockable` out, `DeviceSession` in), A.U5.11 (`ValueRef`, `SgpBackup`), A.U10.06
  (`utc_now`; `time` becomes unused), A.U15.43 (`Any`/`Coroutine`/`Callable` out; `_ValueSource.get_data() -> object`),
  A.U10.38 (`AsyFramChunkTimestampedBuffer` → `FRAMChunkTimestampedBuffer`), A.U15.14 (`type_or_range_error`), A.U5.01,
  A.U30.19
- **Site**: `src/asy_sgp40_driver.py:10-42`
- **Change**: runtime imports `asyncio`, `math`, `namedtuple`, `from struct import unpack_from`, `from machine import
  Timer`, `const`, `from asy_i2c_driver import I2CDevice`, `from asy_base_classes import DeviceSession,
  SensorReaderConfig, report_if_fatal, utc_now`, `from asy_config_manager import make_dict, name_cfg,
  type_or_range_error`, `from asy_crc_checks import CRC8, CRC32`, `from asy_print_log import DEFAULT_LOG, LogConfig`,
  `from voc_algorithm import VOCAlgorithm`. Module-level `SgpBackup = namedtuple("SgpBackup", ("store", "ntp_synced"))`
  (the generated `build_system()` imports it from this module; `ValueRef` is `asy_base_classes`'s). `TYPE_CHECKING`:
  `from typing import Protocol`; `from asy_base_classes import TaskStarter, TimerStarter, ValueRef`; `from
  asy_fram_manager import FRAMChunkTimestampedBuffer`; `from asy_i2c_driver import I2C`; `from asy_print_log import
  ErrorLog`, `FieldSchema` from `asy_config_manager`; `_ValueSource.get_data(self) -> object`.
- **Resolved**: A.U5.11 does not say where `SgpBackup` lives; it is SGP40-specific, so it is this module's (generated
  code imports the SGP40 driver anyway) — agent placement.
- **Unit**: U15 (stages U5, U10, U30)
- **Depends**: A.U5.11, A.U15.40, A.U10.46
- **Blast carried by**: generated `backup=SgpBackup(…)` import line → A.U5.11 (GEN); `pyproject.toml:283` ANN401 entry →
  A.U15.43 (TOOL)
- **Kind**: code

### M.SRC_SENS.059 Constants, catalog names, command waits, module order
- **From**: A.U8.13 (`_FRAM_VERIFY_MINS`, `_BACKUP_COUNTER_MAX` tags), A.U8.07 (`_MEASURE_WAIT_MS`,
  `_SERIAL_READ_WAIT_MS`, `_SELF_TEST_WAIT_MS`, `_GENERAL_CALL_RESET_WAIT_S`), A.U2.13 + A.U2.04 (catalog block),
  A.U15.17 (3) (W34 renamed `SGP_BACKUP_AGE`), A.U15.14 (tick bounds, compensation records), A.U15.18 (`_NO_TIMESTAMP`),
  A.U15.19 (`_VOC_SETTLED_SAMPLES`), A.U15.28 (`_SGP40_ADDR`), A.U15.R02 + A.U31.10 (`_CMD_HEATER_OFF`,
  `_HEATER_OFF_MAX_MS`), A.U15.40 (3) (`_N_*` right after `_VAL_*`)
- **Site**: `src/asy_sgp40_driver.py:44-59`
- **Change**: `# @tunable sgp40.fram_verify_mins = 60` / `_FRAM_VERIFY_MINS = const(60)` (its two-line comment kept);
  `_MAX_NTP_WAITTIME = const(600)`; `# @tunable sgp40.backup_counter_max = 100000` / `_BACKUP_COUNTER_MAX =
  const(100000)`; `_SELF_TEST_PASS = const(0xD4)`; the waits `# @tunable sgp40.measure_wait_ms = 100` /
  `_MEASURE_WAIT_MS = const(100)  # >3x the datasheet's 30 ms maximum (Table 8)`, `# @tunable sgp40.serial_read_wait_ms =
  3` / `_SERIAL_READ_WAIT_MS = const(3)`, `# @tunable sgp40.self_test_wait_ms = 500` / `_SELF_TEST_WAIT_MS = const(500)`,
  `# @tunable sgp40.general_call_reset_wait_s = 1` / `_GENERAL_CALL_RESET_WAIT_S = const(1)`; `_CMD_HEATER_OFF =
  b"\x36\x15"` (a bytes literal, not `const()`), `_HEATER_OFF_MAX_MS = const(1)  # datasheet Table 8 maximum`;
  `_SGP40_ADDR = const(0x59)  # datasheet 4.2: the address is fixed`; `_NO_TIMESTAMP = const(0)` with A.U15.18's comment;
  `_VOC_SETTLED_SAMPLES = const(86400)  # 24 h learning time at the fixed 1 s period (Info Note VOC Index)`;
  `_T_TICKS_MIN_C = const(-45.0)`, `_T_TICKS_MAX_C = const(130.0)`, `_RH_TICKS_MAX = const(100.0)`; the catalog block
  `_ERR_INIT = const(10)`, `_ERR_READ = const(11)`, `_ERR_CHIP_SET = const(13)`, `_ERR_SOURCE = const(15)`,
  `_ERR_SGP_ALGO_STATE = const(58)`, `_WRN_SGP_RESTORED_NO_TS = const(33)`, `_WRN_SGP_BACKUP_AGE = const(34)`,
  `_WRN_SGP_WRITTEN_NO_TS = const(35)`.
- **Resolved**: A.U8.07's wait names are integer ms already except the general-call wait, an int of seconds, which the
  float-sleep rule allows (A.U31.10 keeps it). The heater-off bound is untagged (a datasheet fact, A.U15.R02).
- **Unit**: U15 (stages U2 catalog, U8 tags, U31 heater-off ms form lands with A.U15.R02 in U15 as written by A.U31.10)
- **Depends**: A.U2.01 (row 34 rename), A.U8.01
- **Blast carried by**: Part N rows → A.U8.07/A.U8.13 (SPEC); `tests/test_asy_sgp40_driver.py:2330-2333` mirror site →
  A.U8.07 (TEST_UNIT); catalog row 34 → A.U15.17 into A.U2.01 (GEN)
- **Kind**: code

### M.SRC_SENS.060 Schema, tags, wiring and value-wiring
- **From**: A.U10.39/A.U10.40 (`_VAL_BACKUP_PERIOD`, `_VAL_BACKUP_MAX_AGE`, `_VAL_WAIT_TIME_NTP`, `SGPResetVOC` →
  `ResetVOC`/`_VAL_RESET_VOC`), A.U15.17 (5) (special slot `0`), A.U15.19 (`VOCState` field tag), A.U6.19 (`TS` epoch),
  A.U6.20 (`BackupTS`/`RestoreTS` tags with the special values), A.U15.18 (`0` = no timestamp), A.U5.11 (tags), A.U5.03 +
  A.U10.38, A.U15.16 (holds: both value-wiring tags stay `required`), adherence (`:79-85` comments: "for historical
  reasons", "used to be one whole-object comp_source … generalized" — history, G9/R12)
- **Site**: `src/asy_sgp40_driver.py:51-97`
- **Change**: `_VAL_BACKUP_PERIOD = const((("BackupPeriod", "int", 1, 0, 1440, 0),))`, `_VAL_BACKUP_MAX_AGE =
  const((("BackupMaxAge", "int", 7200, 0, 10080, 0),))`, `_VAL_WAIT_TIME_NTP = const((("WaitTimeNTP", "int", 30, 0, 600,
  0),))` (0 in the special slot: an in-range value with a meaning, C.5), `_N_STORAGE_CFG`/`_N_SETUP_CFG` directly after
  them, `_VAL_RESET_VOC = const((("ResetVOC", "bool", None, None, None, True),))` with its comment (key renamed). Tags:
  the three `special:0=…` texts stay; `# @web ResetVOC …` (was `SGPResetVOC`); measurement tags `VOC`, `Raw`, then
  `# @web VOCState section=measurements submitGroup=self kind=readonly label="VOC Algorithm" description="0 blackout
  (first 46 samples, index 0), 1 learning (fresh start, first 24 h), 2 settled, 3 restored from backup (first 24 h after
  the restore)."`, `# @web TS … kind=readonly label="Timestamp" format=epoch`; A.U6.20's two status tags `# @web BackupTS
  section=status submitGroup=maintenance kind=readonly format=epoch label="SGP40 Last Backup" special:null="None since
  boot" special:0="No timestamp"` and the same for `RestoreTS` (label "SGP40 Restore Timestamp"). Wiring: `:79-85` →
  "# Live cross-instance dependencies (SPECIFICATION.md Parts C.14 and L.4): the optional FRAM store (its logger's and,
  through backup=, the VOC backup's), and two per-value compensation references (Part L.6.3), each wireable from any
  instance exposing a matching field." with `# @wiring fram_target FRAMManager log optional kwarg`; `# @requires
  bus.frequency<=400000` and its comment unchanged; `:93-95` comment kept in substance ("Both are required, so an SGP40
  with no compensation data at all opts in explicitly through a `_Default*`."), tags `# @value-wiring temperature_source
  temperature required` and `# @value-wiring humidity_source humidity required`.
- **Resolved**: `<NO_TS>` of A.U6.20 is A.U15.18's `0` (A.U6.20's Depends on U15).
- **Unit**: U15 (stages U5 wiring/value-wiring, U6 tags (A.U6.20 lands after A.U15.18: U6 < U15 — A.U6.20 writes its
  special with the recommended `0`, which A.U15.18 then confirms), U10 keys/names)
- **Depends**: A.U5.11, A.U6.19, A.U6.20, A.U10.40
- **Blast carried by**: generated definitions (status rows from tags, `VOCState`, keys, specials) →
  A.U6.20/A.U15.19/A.U6.04 (GEN); `buildgen/definitions.py:208-210` comment example → A.U15.17 (GEN); value-wiring grammar
  (`buildgen/value_wiring.py`, `codegen.py`) → A.U5.11 (GEN); mock data `VOCState`, `RestoreTS` → A.U15.18/A.U15.19
  (WEB); SPEC C.5/H.5/L.6.3/M.3 → A.U15.17/A.U5.11/A.U36.537 (SPEC); DEVICE_REFERENCE SGP40 text → A.U15.17 (DOCS)
- **Kind**: code

### M.SRC_SENS.061 The compensation defaults as comment-explained classes
- **From**: A.U10.34 (`_DefaultTemperatureSource`/`_DefaultHumiditySource` docstrings → comments)
- **Site**: `src/asy_sgp40_driver.py:99-126`
- **Change**: each docstring becomes a `#` block directly under the `class` line with the same text trimmed to three
  lines (`_DefaultTemperatureSource`: "# Part L.6.2's wiring-defaults mechanism, opted into via [instance.wiring].
  temperature_source = {default = true, temperature = 25}: a constant compensation fallback when no live temperature
  source is wired."; `_DefaultHumiditySource`: "# The same mechanism for relative humidity; 50 %RH matches measure_raw()'s
  datasheet default (Table 9)."). Bodies unchanged; `get_data() -> _ConstValue` unquoted (A.U10.31: `_ConstValue` is a
  runtime name).
- **Resolved**: —
- **Unit**: U10
- **Depends**: —
- **Blast carried by**: `buildgen` reads class names, not docstrings (A.U10.34's check) → no GEN change
- **Kind**: code

### M.SRC_SENS.062 `SGP40_Reader` construction and its state
- **From**: A.U5.11 (`(i2c, temperature, humidity, backup=None, max_module_error=5, name_ext="", cfg_path="",
  log=DEFAULT_LOG)`), A.U0.40 (`:158` tag), A.U0.41 (`:191-192` tag), A.U3.02 (`_no_ts_episode` goes), A.U10.35 (private
  attributes), A.U15.17 (4) (`_restore_waiting`, `_ntp_synced` from `backup`), A.U15.19 (`_voc_samples`,
  `_voc_restored`), A.U15.R02 (`_recovery_bus`), A.U10.25 (registration stays in `__init__`: holds), A.U27.03 (bare
  `Timer()` comment), A.U30.19 (the allocation guard)
- **Site**: `src/asy_sgp40_driver.py:129-194`
- **Change**: `super().__init__(SGP40(None, None, None, None), _NAME, <BP + BMAX + WT + RESET_VOC>,
  max_module_error=max_module_error, name_ext=name_ext, cfg_path=cfg_path, log=log)`; `self._sgp = SGP40_I2C(i2c)`;
  `self._recovery_bus = i2c`; the registration comment → "# ResetVOC is command-only (see _VAL_RESET_VOC above) -
  registered like every other module's live-push field (agent, 2026-08-04: constant at runtime, no per-call plumbing),
  just never persisted."; `self._read_event`; the bare-Timer comment then `self._trigger_timer = Timer()`;
  `self._backup_counter = 0`; `self._voc_init = 0`, `self._voc_write = 0`; `self._restore_waiting = False`;
  `self._voc_samples = 0`, `self._voc_restored = False`; `self._temperature: ValueRef = temperature`, `self._humidity:
  ValueRef = humidity` (the four `*_source`/`*_field` attributes go; the `:168-170` comment → "# References to each
  producer and the field to read off its get_data() result (Part C.14): the two may be one instance or two."); backup:
  `if backup is None: self._ts_storage = None; self._ntp_synced = None` else `self._ntp_synced = backup.ntp_synced` and
  `try: self._ts_storage = backup.store.get_timestamped_chunk(VOCAlgorithm.get_params_memsize(), backup.ntp_synced,
  crc=CRC32())` `except Exception as e: report_if_fatal(e); self._ts_storage = None` (the broad-on-purpose comment kept),
  `None` → the console line; `self._last_backup`, `self._restored_from` (`int | None`, `None`); `self._reset_pending =
  False` (HEAD `reset`, no reader outside the class: private by default); the reset sub-part comment (A.U0.41, ≤ 3
  lines): "# Two independent sub-parts of a pending reset, tracked separately since they can complete on different cycles
  (see reset_voc()/_read_sgp()); both start done. Never drop a reset, never redo the whole thing, never give up retrying
  (owner, 2026-07-22, `90ced2b`, 'verbatim in spirit')." then the two flags.
- **Resolved**: A.U10.35 lists nine attributes of this class; `reset` has no outside reader either — G10/R07 private by
  default (agent, OR2.c list, same reading as M.SRC_SENS.004). The `_ntp_synced` reference replaces A.U15.17's
  `fram_ntp_callback` (A.U5.11's `backup.ntp_synced`, named in A.U15.17's own text).
- **Unit**: U15 (stages U0 tags (text merged here), U3, U5, U10, U27, U30)
- **Depends**: M.SRC_SENS.058-060
- **Blast carried by**: generated construction (`temperature=ValueRef(…)`, `backup=SgpBackup(…)`) → A.U5.11 (GEN); tests
  and device scripts constructing the reader (`sgp40_fram_backup_restore.py`, `sgp40_voc_algorithm_quality.py:47-56`) →
  A.U5.11 (TEST_UNIT, HW_DEV); attribute readers → A.U10.35
- **Kind**: code

### M.SRC_SENS.063 Backup schedule, restore and backup write
- **From**: A.U15.17 (1)-(4) (`_verify_every()`, WaitTimeNTP 0, age check, no per-second re-read), A.U16.18 (bool-first
  unpack; negative age expired — the same condition as A.U15.17 (3)), A.U15.18 (`_NO_TIMESTAMP`), A.U3.02 (W35 on every
  untimestamped backup; `_no_ts_episode`/`repeat=` go), A.U3.09 (`:251-254, :373-377, :426-429` → console), A.U3.05
  (`:206, :348` config reads → console), A.U2.13 (numbers), adherence (`:231-232` "(see module docstring)" points to text
  the docstring does not hold)
- **Site**: `src/asy_sgp40_driver.py:196-234, 342-361, 363-446`
- **Change**: module function `_verify_every(backup_period_min: int) -> int: return max(1, int(math.ceil((10 *
  _FRAM_VERIFY_MINS) / backup_period_min) * 0.1))` with A.U15.17 (1)'s comment; `_init_sgp()` and `_run_backup()` call it.
  `_check_storage()`: a failed config read → `self.pr.err("Error reading config data!")` (console) and the early return;
  `:231-232` comment → "# Explicit unpack-then-repack so mypy sees a real 3-tuple without a typing.cast (C.4.2)." The
  storage part of `_init_sgp()`: a failed read → console line, `return False`; `if cfg_values[0] > 0: await
  self._ts_storage.set_verify(_verify_every(cfg_values[0]))`; `wait = min(cfg_values[1], _MAX_NTP_WAITTIME)`;
  `self._voc_init = max(1, wait)` ("# 0 = never wait: one restore attempt on the first cycle, as legacy");
  `self._voc_write = wait`; `self._restore_waiting = False`. `_run_restore()`: at the top (after the argument guard) `if
  self._restore_waiting and self._voc_init > 0 and not await self._ntp_synced(): return False`; `res, ts, age = await
  self._ts_storage.read_into(buf)`; no backup → `self.pr.wrn("No backup found!")` (console), `self._voc_init = 0`, return
  `False`; `ts is None` → `wrn_s("Backup loaded without timestamp", wrnno=_WRN_SGP_RESTORED_NO_TS)`, `ts =
  _NO_TIMESTAMP`; `age is None` with `_voc_init > 0` → `self._restore_waiting = True`, the NTP-wait event, return
  `False`; otherwise `self._voc_init = 0`, `self._restore_waiting = False`, and `if age < 0 or (cfg_values[1] > 0 and age >
  60 * cfg_values[1]): await self.pr.wrn_s("Backup age out of range (too old, or dated in the future)",
  wrnno=_WRN_SGP_BACKUP_AGE); return False`; `self._restored_from = ts`; `return True`. `_run_backup()`: verify period
  through `_verify_every()`; `res, ntp_synced, ts = await self._ts_storage.write_into(buf, require_ntp=require_ntp)`; a
  failed write → `self.pr.err("Write error during backup!")` (console; the FRAM layer persisted the cause); the two
  `_no_ts_episode` lines go; the untimestamped branch `await self.pr.wrn_s("Backup written without timestamp.",
  wrnno=_WRN_SGP_WRITTEN_NO_TS)` every time.
- **Resolved**: A.U15.17 (3) and A.U16.18 write the same negative-age condition at `:390` — one `if`. A.U3.09 and
  A.U2.13 agree: w10/e14/e15 print, the FRAM manager persists.
- **Unit**: U16 (latest: A.U16.18's unpack order co-lands with the FRAM manager's return-shape change; stages U2, U3,
  U15)
- **Depends**: M.SRC_SENS.062; A.U16.18 (FRAM side, SRC_CORE), A.U3.04 (FRAM persists the cause)
- **Blast carried by**: L1/L2 backup cases (`_verify_every` table, WaitTimeNTP 0, −60 s age, single re-read, first-boot
  blank chunk, blackout skip) → A.U15.17/A.U16.18/A.U3.09 (TEST_UNIT, TWIN); `tests/test_asy_sgp40_driver.py:1055-1056`
  stub order → A.U16.18; W13 tests → A.U3.02; BACKLOG `:362-365` → A.U3.02 (DOCS); SPEC C.7.1 SGP40 row → A.U2.22 (SPEC)
- **Kind**: code

### M.SRC_SENS.064 `_read_sgp()`: timestamp, checked compensation, VOC state
- **From**: A.U10.06 (timestamp before the `try`), A.U15.14 (finite check through the primitive, first in the `try`),
  A.U5.11 (reference reads), A.U15.19 (`VOCState`), A.U3.09 (`:251-254` clear failure → console), A.U2.13 (18 → 15,
  16/17 → 58), A.U30.19
- **Site**: `src/asy_sgp40_driver.py:236-328`
- **Change**: the reset block as today (private names), the FRAM clear failure → `self.pr.err("Error clearing FRAM!")`
  (console). Compensation read: `t_src: _ValueSource = self._temperature.source`, `h_src: _ValueSource =
  self._humidity.source`; `try: temp_data = await t_src.get_data(); hum_data = await h_src.get_data()` `except Exception as
  e: report_if_fatal(e); await self.pr.err_s("Compensation data read failed:", e, errno=_ERR_SOURCE); temp_val, hum_val =
  None, None` `else:` the two `getattr(…, <ref>.field, None)` reads (`temp_val: object`, `hum_val: object`). The `None`
  branch as today, returning `SGP40(None, None, None, None), False, False`. `timestamp = utc_now()` (before the `try`);
  `try:` first `is_error_t, t = type_or_range_error(temp_val, _COMP_T_FIELD)`, `is_error_h, h = type_or_range_error(hum_val,
  _COMP_RH_FIELD)`, either → `raise ValueError(f"compensation value not a finite number (t={temp_val!r},
  rh={hum_val!r})")`; then the reset bookkeeping, `measure_index_and_raw(temperature=t, relative_humidity=h, …)` (the
  `float()` comment goes, its reason is the check above), the VOC-state step of A.U15.19 (resets at
  `reset_for_measure` → 0/False and `deserialized` → 0/True, then `if self._voc_samples < _VOC_SETTLED_SAMPLES:
  self._voc_samples += 1`, then `voc_state` = 0 if `voc_index == 0`, 2 if settled, 3 if restored, else 1); deserialize/
  serialize failures `errno=_ERR_SGP_ALGO_STATE`; `except Exception as e: report_if_fatal(e);` … `errno=_ERR_READ`; return
  `SGP40(voc_index, raw, voc_state, timestamp)` (`voc_state = None` on the failure path). `_COMP_T_FIELD: FieldSchema =
  ("Temp", "float", None, -1.0e30, 1.0e30, None)` and `_COMP_RH_FIELD` (A.U15.14) sit in the constants block.
- **Resolved**: A.U15.14 puts the finite check "as the first statement inside the existing `try` (before the reset
  bookkeeping)"; A.U10.06 moves the timestamp before the `try` — both hold. OR109.a (1): the per-sample floats and
  tuples here are temporaries (accepted).
- **Unit**: U15 (stages U2, U3, U5, U10, U30)
- **Depends**: M.SRC_SENS.062, M.SRC_SENS.068
- **Blast carried by**: L1 NaN/inf/`True` and lost-reset regression, VOCState cases → A.U15.14/A.U15.19 (TEST_UNIT); L2
  `tests/test_digital_twin_sgp40.py` → A.U15.19 (TWIN); every `SGP40(` tuple in tests gains the field → A.U15.19
- **Kind**: code

### M.SRC_SENS.065 `_init_sgp()`, the store guard and the participant rung
- **From**: A.U10.10 (`pr.setup()` leaves), A.U15.R02 (3) (`_init_failed()`/`_init_done()`), A.U15.R02 (2)
  (`_recover_device()`), A.U15.41 (re-arm at `_init_sgp()`'s start), A.U10.06 (store guard on values), A.U2.13, A.U30.19
- **Site**: `src/asy_sgp40_driver.py:330-340, 448-452` and a new method
- **Change**: `_init_sgp()`: `if self._timer_error is not None: self._timer_error = None; self.start_timer()` first; then
  the counters zeroed; `try: await self._sgp.setup()` `except Exception as e: report_if_fatal(e); await
  self.pr.err_s("Error in initial setup:", e, errno=_ERR_INIT); await self._init_failed(); return False`; no storage →
  `await self._init_done()`, `self.pr.one("initialized without storage")`, `return True`; the storage part of
  M.SRC_SENS.063; `await self._init_done()` before the final success return. `_store_sgp()`: returns when `data.VOC is None
  or data.Raw is None` (the `TS` may be `None` before the first sync). `_recover_device(self) -> bool`: `try: await
  self._sgp.turn_heater_off()` `except Exception as e: report_if_fatal(e); await self.pr.err_s("Heater-off failed:", e,
  errno=_ERR_CHIP_SET); return False`; `return True` (the VOC algorithm state untouched).
- **Resolved**: A.U15.R02 as corrected per AC_NOTES 31 (V.U25 on twin Run 5): the correction concerns the twin CI's
  expected counts (SCR), not this code — the code is as written.
- **Unit**: U15 (stages U2, U10, U30)
- **Depends**: M.SRC_SENS.062, M.SRC_SENS.068; A.U10.R01, A.U13.R01
- **Blast carried by**: SGP40 streak tests `:369-443, 505-510, 585-589` and new rung cases → A.U15.R02/A.U10.R01
  (TEST_UNIT); four tiers of the heater-off (L1 hazard, L2 twin with the 0x3615 branch, L3 sweep and
  `bus_concurrency_cross_device_scd30_sgp40.py` step) → A.U15.R02 (TEST_UNIT, TWIN A.U25, HW_DEV); twin CI expected
  counts (`_BOUNDED_FAULT_COUNT`, Run 5) → A.U15.R02 as corrected by AC_NOTES 31 (SCR); SPEC C.8/A.4 → A.U15.R02/A.U15.15
- **Kind**: code

### M.SRC_SENS.066 Push callback, starters, getters, `reset_voc()` and the loop
- **From**: A.U15.21 (push guard goes), A.U10.12 (trigger starter), A.U15.41 (arm failure wakes the read task; the loop
  checks), A.U10.44 (`_read_loop`), A.U15.43 (`-> None`, types), A.U0.35 (`:508` tag), A.U10.39/A.U10.40 (names)
- **Site**: `src/asy_sgp40_driver.py:454-533`
- **Change**: `_push_reset_voc()`: `await self.reset_voc(flag=value is True)`; `return True` (the comment `:455-457`
  keeps its "always reports success" reason, ≤ 3 lines). `start_asy_read(self) -> asyncio.Task[None]` over
  `_read_loop()`; `start_timer()` with `except (MemoryError, OSError) as e: self._timer_failed(e, self._read_event)` and
  A.U15.41's comment; `get_task_starters(self) -> list[TaskStarter]: return [self.start_asy_read]`;
  `get_trigger_starters(self) -> list[TimerStarter]: return [self.start_timer]`; `get_timer_starters(self) ->
  list[TimerStarter]: return []`. `get_mem_status()` returns `self._last_backup, self._restored_from`. `get_dict_cfg()`
  names the renamed tuples (its comment names `ResetVOC`). `reset_voc()`: "(project-wide decision)" → "(owner,
  2026-09-26)"; `self._reset_pending = True`. `_read_loop(self) -> None`: init; `while True: await
  self._read_event.wait()`; `if await self._timer_fault(): return`; the cycle as today with M.SRC_SENS.091's condition; `return` for
  HEAD's `return False`.
- **Resolved**: —
- **Unit**: U15 (stages U0 tag, U10 names/split)
- **Depends**: M.SRC_SENS.062-065; A.U15.41 helpers (SRC_CORE)
- **Blast carried by**: `tests/test_asy_sgp40_driver.py:563, 616-637, 1266, 2299` → A.U15.21/A.U10.12/A.U15.43
  (TEST_UNIT); generated collectors → A.U10.12 (GEN)
- **Kind**: code

### M.SRC_SENS.067 `SGP40_I2C` construction and the VOC algorithm at construction
- **From**: A.U15.28 (no `address`), A.U15.40 (session; `SGP40_DeviceSession` goes), A.U10.35 (`_i2c_sgp40`), A.U15.13
  (2) (`_reply_buffer = bytearray(9)`), A.U30.04 (algorithm built in `__init__`), A.U12.18 (the shared `_measure_command`
  stays; staged inside the hold)
- **Site**: `src/asy_sgp40_driver.py:536-553, 634-662`
- **Change**: `__init__(self, i2c: I2C)`: `self._i2c_sgp40 = DeviceSession(I2CDevice(i2c, _SGP40_ADDR))`; the two command
  buffers as today; `self._reply_buffer = bytearray(9)` with "# Sized for the longest reply, the 3-word serial number
  (datasheet Table 8)"; `self.crc = CRC8()`; `self._measure_command` as today; `self._voc_algorithm = VOCAlgorithm()` and
  `self._voc_algorithm.vocalgorithm_init()`. `measure_index_and_raw()`: the lazy `if … is None` block goes; `reset=True`
  keeps `vocalgorithm_reset()`.
- **Resolved**: —
- **Unit**: U30 (stages U10 name, U15 session/address/buffer)
- **Depends**: M.SRC_SENS.059
- **Blast carried by**: `tests/test_asy_sgp40_driver.py:329, 770-776, 1244, 1601, 1629` and the new construction case →
  A.U30.04 (TEST_UNIT); boot contiguity bounds and the flash `≤ 100,000 B` survivors figure → A.U30.04 (TSC, HW_DEV; phase C
  re-reads); I.2 row → A.U30.02 (SPEC)
- **Kind**: code

### M.SRC_SENS.068 One exchange: staged command, restored buffer, word reads without lists
- **From**: A.U12.18 (`_measure_in_session()`, fill inside the hold), A.U15.13 (1) (`try/finally` restore), (2) (serial
  read of three words, no `None` paths), A.U30.06 (`_exchange()`/`_read_word()`/`_read_words()`), A.U31.10 (the `:574` half
  is A.U30.06's `sleep_ms`), A.U8.07 (wait constants; the `delay_ms=10` default goes), A.U13.09 (`:573, :576` writes/reads
  bool-checked), A.U15.14 (tick helpers), A.U0.41 (`:598` tag), A.U15.40 (session annotation), A.U10.45 (messages)
- **Site**: `src/asy_sgp40_driver.py:555-632`
- **Change**: `async def _exchange(self, sgp40: DeviceSession, delay_ms: int, words: int) -> None:` — `replylen = words *
  3`; `if replylen > len(self._reply_buffer): raise ValueError("reply longer than the reply buffer")`; `async with
  sgp40.i2c_device as i2c: if not await i2c.write(self._command_buffer): raise OSError("I2C bus not initialized")`; `await
  asyncio.sleep_ms(delay_ms)`; `async with sgp40.i2c_device as i2c: if not await i2c.readinto(self._reply_buffer,
  end=replylen): raise OSError("I2C bus not initialized")`; the CRC loop raising `RuntimeError("CRC check failed while
  reading data")`. `# The per-sample read: one word decoded in place, no list, tuple or float.` `async def _read_word(self,
  sgp40, delay_ms: int) -> int:` `await self._exchange(sgp40, delay_ms, 1)`; `return (self._reply_buffer[0] << 8) |
  self._reply_buffer[1]`. `async def _read_words(self, sgp40, delay_ms: int, count: int) -> list[int]:` `_exchange()` then
  the list from `unpack_from(">H", self._reply_buffer, 3 * i)` (serial number only, once at setup). `_celsius_to_ticks()`/
  `_relative_humidity_to_ticks()`: A.U15.14's clamp-then-round form (no mask), the comment keeping the Table 10 points and
  "Rounds to nearest (matching _relative_humidity_to_ticks below) rather than truncating (owner, 2026-07-22,
  paraphrase); clamped to Table 10's range, never wrapped." (≤ 3 lines). `async def _measure_in_session(self, sgp40:
  DeviceSession) -> int:` ("# Caller holds self._i2c_sgp40.") `self._command_buffer = self._measure_command`; `try: return
  await self._read_word(sgp40, _MEASURE_WAIT_MS)` `finally: self._command_buffer = self._default_command_buffer`.
  `get_raw(self) -> int`: `async with self._i2c_sgp40 as sgp40: return await self._measure_in_session(sgp40)`.
  `measure_raw(self, temperature=25, relative_humidity=50) -> int | None`: `async with self._i2c_sgp40 as sgp40:` "#
  Staged inside the session: an await before the hold would let another caller overwrite the shared command (owner,
  2026-09-29: no races)." then the memoryview fill, both `crc.add_into()` (each `return None` on failure) and `return
  await self._measure_in_session(sgp40)`.
- **Resolved**: A.U15.13 reshapes `_read_word_from_command()`; A.U30.06 (written onto A.U15.13's shape, U30 note 7)
  splits it into `_exchange()`/`_read_word()`/`_read_words()` — the merged end state is A.U30.06's split with A.U15.13's
  buffer size, raise and alias fix, and A.U12.18's staging. OR109.a (0): every per-call input kept in the shared
  `_measure_command` is written inside the device-session hold.
- **Unit**: U30 (stages U8 constants, U10 messages, U12 staging, U13 bool checks, U15 restore/serial/clamp, U30 split)
- **Depends**: M.SRC_SENS.011, M.SRC_SENS.013, M.SRC_SENS.059, M.SRC_SENS.067
- **Blast carried by**: four tiers of the race fix — L1 `tests/test_bus_hazard_multi_device.py:356-377` (A.U24.74), L2
  twin case, L3 `sgp40_same_device_concurrent_sessions.py` + flash leg, L4 unchanged → A.U12.18 (TEST_UNIT, TWIN, HW_DEV);
  alias regression (D4.53), 9-byte serial read, word-2 CRC → A.U15.13 (TEST_UNIT, TWIN `_sgp40_chip.py` corrupt-next hook
  A.U25); `_NoneReadWord`/`fake_read_word` tests → A.U15.13/A.U30.06; `sleep_ms` patches → A.U30.06/A.U24.49; Table 10
  edge cases → A.U15.14; SPEC C.8/G.2 sentences → A.U12.18 (SPEC); release notes D4.53/D4.55 → U37
- **Kind**: code

### M.SRC_SENS.069 General-call reset, heater-off command and identity checks
- **From**: A.U13.09 (`_reset()`'s `acked`), A.U8.07 (`_GENERAL_CALL_RESET_WAIT_S`), A.U15.R02 (1) + A.U31.10
  (`turn_heater_off()`), A.U15.13 (2) (`initialize()`), A.U0.28 (`:670-671` tag; superseded by A.U15.13's text), A.U10.21
  (`setup() -> bool`), A.U10.45 (messages), A.U15.15 (C.8 doc only)
- **Site**: `src/asy_sgp40_driver.py:585-593, 664-694` and a new method
- **Change**: `_reset()`: `acked: int | None = 0`; under session and bus `try: acked = i2c.i2c.writeto(0x00, b"\x06")`
  `except OSError: pass`; `if acked is None: raise OSError("I2C bus not initialized")`; `await
  asyncio.sleep(_GENERAL_CALL_RESET_WAIT_S)` (comment unchanged). `async def turn_heater_off(self) -> None:` under
  `async with self._i2c_sgp40 as sgp40, sgp40.i2c_device as i2c:` `if not await i2c.write(_CMD_HEATER_OFF): raise
  OSError("I2C bus not initialized")`; then outside the locks `await asyncio.sleep_ms(_HEATER_OFF_MAX_MS + 1)  # one tick
  more than the datasheet bound: sleep_ms() may wake up to 1 ms early`. `async def setup(self) -> bool:` probe,
  `initialize()`, `return True`. `initialize()`: header comment → A.U15.13's "# Identity per datasheet 3.3-3.4: three
  CRC-checked serial words with legacy's word-0 check, and the self-test's 0xD4 high byte (Table 13). No feature-set
  check: the datasheet documents none (owner, 2026-07-21)."; serial via `_read_words(sgp40, _SERIAL_READ_WAIT_MS, 3)`;
  word-0 check with A.U15.13's comment and `RuntimeError("serial number does not match")`; self-test via
  `_read_word(sgp40, _SELF_TEST_WAIT_MS)`, `(self_test >> 8) != _SELF_TEST_PASS` → `RuntimeError("self test failed")`;
  `await self._reset()`. The two `None` raises go (A.U15.13).
- **Resolved**: A.U0.28 (U0) and A.U15.13 (U15) both rewrite the `:670-671` comment; A.U15.13's text carries the owner
  tag A.U0.28 adds (and the Table 8 fact), so it is the merged text. A.U13.09 applies its "a `False` write is the
  driver's bus-fault shape" rule to every write; the new heater-off write follows it (completeness, same rule).
- **Unit**: U15 (stages U8, U10, U13; A.U31.10's form is written directly in U15)
- **Depends**: M.SRC_SENS.068
- **Blast carried by**: identity/serial tests → A.U15.13 (TEST_UNIT); address sweep gains `turn_heater_off` →
  A.U15.R02 (TEST_HELP `_bus_hazard_catalog.py:216-226`); general-call hazard tests → A.U15.15 (TEST_UNIT); SPEC M.3 →
  A.U15.05/A.U15.13 (SPEC)
- **Kind**: code


### M.SRC_SENS.091 SGP40: a pre-sync `TS` of `None` is not a failed read
- **From**: M.SRC_SENS.089's rule
- **Site**: `src/asy_sgp40_driver.py:530` (`_read_loop()`)
- **Change**: `if not await self._error_check(data, condition=compensated and data[0] is None): return` with
  M.SRC_SENS.089's comment line.
- **Resolved**: see M.SRC_SENS.089; the `compensated` gate (a cycle without compensation counts nothing) is kept.
- **Unit**: U10
- **Depends**: M.SRC_SENS.089
- **Blast carried by**: → GAP-15 (TEST_UNIT, TWIN, SPEC)
- **Kind**: code

## src/asy_isl29125_driver.py

### M.SRC_SENS.070 Header, docstring and imports
- **From**: A.U34.07 (SPDX order), A.U10.37 (module names), A.U15.40 (`Lockable` out, `DeviceSession` in), A.U10.06
  (`utc_now`), A.U5.01/A.U5.02 (`LogConfig`; the FRAM manager import goes with `fram=`), A.U10.38 (`FRAMManager`: moot
  here, the import goes), A.U15.43 + A.U10.46 (`Any`/`Callable` out; `JsonDict`, starter aliases), A.U15.31 + AC_NOTES 17
  (`COUNTER_CAP`), A.U30.19 (`report_if_fatal`), A.U10.31 (unquote annotations naming no `TYPE_CHECKING` symbol,
  31 in this file), A.SDEP.15 (stage U0 re-check of the stub workarounds, W08-W11)
- **Site**: `src/asy_isl29125_driver.py:1-34`, and every annotation in the file (A.U10.31)
- **Change**: `:1-3` → "# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya" / "# SPDX-License-Identifier: MIT"
  / "# From MicroPython_ISL29125, rewritten for asyncio + this driver shape - see THIRD_PARTY_LICENSES.md." (A.U34.07).
  Docstring unchanged. Runtime imports: `asyncio`, `struct`, `time`, `namedtuple`, `from machine import Pin, Timer`,
  `const`, `import math_helpers`, `from asy_i2c_driver import I2CDevice`, `from asy_base_classes import COUNTER_CAP,
  DeviceSession, LockedValue, SensorReaderConfig, report_if_fatal, utc_now`, `from asy_config_manager import name_cfg,
  type_or_range_error`, `from asy_print_log import DEFAULT_LOG, LogConfig`. The `TYPE_CHECKING` shim stays;
  under it: `from asy_base_classes import JsonDict, TaskStarter, TimerStarter`; `from asy_i2c_driver import I2C`; `from
  asy_config_manager import ConfigSchema`; `from asy_print_log import ErrorLog`. A.U10.31: every quoted annotation that
  names no `TYPE_CHECKING` symbol is unquoted (`"tuple[bool, bool]"`, `"list[float]"`, `"tuple[int, int, int]"`,
  `"bytes | bytearray | memoryview | None"`, `"int | float | str | bool | None"`, `"asyncio.Task[None]"`, …);
  `"ISLResults"`, `"I2C"`, `"ConfigSchema"`, `"ErrorLog"`, `"JsonDict"` and the starter aliases stay quoted.
- **Resolved**: —
- **Unit**: U15 (stages U0 re-check, U5 `LogConfig`, U10 names/unquoting/`utc_now`, U30 `report_if_fatal`, U34 header)
- **Depends**: A.U10.37, A.U10.46, A.U15.40, A.U10.06, A.U10.01
- **Blast carried by**: L0 `tests_scripts/test_third_party_attribution.py` → A.U34.07 (TSC); `pyproject.toml` baseline
  list → A.U15.43 (TOOL); SPEC B.15 list → A.U27.03 (SPEC)
- **Kind**: code

### M.SRC_SENS.071 Constants: registers, tags, bounds, catalog names, fixed address
- **From**: A.U15.37 (`_REGISTER_CONFIG3` goes), A.U36.544 (`:58` "Part C" → M.1.3), A.U0.35 (`:90` actor tag), A.U0.28
  (`:98` owner tag), A.U8.13 (ten tunables tagged), A.U10.43 (`_MIN/_MAX_TRIGGER_S`), A.U15.35 (`_MAX_DWELL_MS`), A.U15.28
  (`_ISL29125_ADDR`), A.U2.12 + A.U2.04 + A.U2.01 (catalog block), A.U15.30 (the `_SETTLE_CYCLES` comment points at the
  Table 7 reading)
- **Site**: `src/asy_isl29125_driver.py:37-117`
- **Change**: `_REGISTER_CONFIG3` and its comment go. `:58` → `_CONFIG3_CONVEN = const(0x10)  # p11, Table 13 - kept 0,
  see SPECIFICATION.md M.1.3`. `:90-91` → "# Device/maths constants, not config fields (agent classification,
  2026-09-14) - requirement 1 (SPECIFICATION.md / # Part M.1.1) governs preferences, and none of these is one." (two
  lines). `:98` → "# Calibration is a bounded, user-started run, never a background schedule (owner, 2026-09-13): the
  driver only ever / # READS GainRatio, so nothing it does can write the flash (SPECIFICATION.md Part M.1.5)." (two
  lines). Tag lines directly above each tuned constant (values unchanged, basis from each constant's own comment per
  A.U8.13): `# @tunable isl29125.cct_floor_counts = 64`, `# @tunable isl29125.gain_ratio_min = 20.0`, `# @tunable
  isl29125.gain_ratio_max = 34.0`, `# @tunable isl29125.cal_window_ms = 120000`, `# @tunable isl29125.cal_hold_ms =
  600000`, `# @tunable isl29125.cal_converge_n = 3`, `# @tunable isl29125.cal_converge_tol = 0.01`, `# @tunable
  isl29125.cal_stability_tol = 0.02`, `# @tunable isl29125.settle_cycles = 2`, `# @tunable
  isl29125.settle_wait_max_rounds = 2`, `# @tunable isl29125.periodic_only_warn_at = 5`. `_SETTLE_CYCLES`'s trailing
  comment → "conversions discarded after a CONFIG1 write, fixed - see configure()". `_MIN_TRIGGER_S = const(1)`,
  `_MAX_TRIGGER_S = const(3600)`; after `_MAX_DWELL_S`: `_MAX_DWELL_MS = const(300000)  # _MAX_DWELL_S in ms, the
  stored-tick bound of _evaluate_range()`. `_ISL29125_ADDR = const(0x44)  # hard-wired "1000100" (FN8424 p15): a second
  part needs another bus`. The catalog block: `_ERR_INIT = const(10)`, `_ERR_READ = const(11)`, `_ERR_CHIP_GET =
  const(12)`, `_ERR_CHIP_SET = const(13)`, `_ERR_BAD_ARG = const(21)`, `_ERR_ISL_STATUS_READ = const(55)`,
  `_ERR_ISL_BUS_FAULT = const(56)`, `_WRN_ISL_BROWNOUT = const(30)`, `_WRN_ISL_DIVERGED = const(31)`,
  `_WRN_ISL_PERIODIC_ONLY = const(32)`.
- **Resolved**: A.U0.35's text "Device/maths constants, not config fields (agent classification, 2026-09-14)" and the
  existing M.1.1 pointer fit two lines together (3-line cap). Datasheet facts rechecked: p15 "internally hard-wired as
  1000100" (`dstxt/isl29125…:1139`; p7 `:477` says the same), Table 7 (`:786-789`).
- **Unit**: U15 (stages U0 tags in comments, U2 catalog block, U8 tunable tags, U10 `_S` names, U36 citation — each lands
  in its own unit on the same lines)
- **Depends**: A.U2.01, A.U8.01
- **Blast carried by**: Part N rows and M.1.4/M.1.5 citations → A.U8.13 (SPEC); test copies `tests/test_asy_isl29125_driver.py:
  38-42` → A.U24.01 (TEST_UNIT); twin test copies → A.U25.49 (TEST_UNIT/TSC); `_ISL29125_ADDR` read by
  `buildgen` → A.U20.28 (GEN); catalog rows 55/56/30-32 → A.U2.01 (GEN); 61 number asserts in
  `tests/test_asy_isl29125_driver.py`, `tests/test_digital_twin_isl29125_autorange.py:96`, device scripts
  `isl29125_mechanism_envelope.py:217, 221`, `isl29125_lighting_scenarios.py:204, 336`, `tests_hardware/README.md:215,
  227, 247` → A.U2.12 (TEST_UNIT, HW_DEV, DOCS)
- **Kind**: code

### M.SRC_SENS.072 Schema, tags, fields and the `CalLight` output
- **From**: A.U10.39 (`_VAL_` names), A.U10.40 (keys `SampleInterval`, `IRCompOffset`, `IRCompAdjust`, `Calibrate`),
  A.U15.22 (3) (`_N_STORE_CFG` goes), A.U15.36 (`CalLight` field and tag), A.U6.19 (`TS` tag), A.U23.16 (the
  `defaultValue` key leaves the grammar — its grep missed this tag), A.U5.03 + A.U10.38 (`@wiring`), A.U10.43
  (`@limits trigger_s`), A.U15.40 (3) (module order holds)
- **Site**: `src/asy_isl29125_driver.py:111-194`
- **Change**: `_VAL_SAMPLE_INTERVAL = const((("SampleInterval", "int", 1, _MIN_TRIGGER_S, _MAX_TRIGGER_S, None),))`,
  `_VAL_RESOLUTION`, `_VAL_RANGE_AUTO`, `_VAL_RANGE`, `_VAL_AUTO_RANGE_THRESH`, `_VAL_AUTO_RANGE_DWELL`,
  `_VAL_IR_COMP_OFFSET` (`"IRCompOffset"`), `_VAL_IR_COMP_ADJUST` (`"IRCompAdjust"`), `_VAL_FILT_COEFF`, `_VAL_GAIN_RATIO`,
  `_VAL_CALIBRATE = const((("Calibrate", "bool", None, None, None, True),))`; comments keep their text with the new key
  names ("_VAL_POV" → "_VAL_PRES_OVERS"). `_N_INT_CFG`/`_N_FLOAT_CFG` comments name the new keys; `_N_BOOL_CFG`'s →
  "RangeAuto ALONE - Calibrate is command-only (see _VAL_CALIBRATE above)"; `_N_STORE_CFG` goes. Tags: field names
  `SampleInterval`, `IRCompOffset`, `IRCompAdjust`, `Calibrate`; the `Calibrate` tag loses ` defaultValue=false`
  (otherwise unchanged, `dispatch=true` stays). Namedtuple and `_FIELDS`: `CalLight` between `GainMeas` and `TS`;
  `ISL29125(None, …)` gains one `None`. After the `GainMeas` tag: `# @web CalLight section=measurements
  submitGroup=self kind=readonly label="Calibration Light" description="0 not applicable now (fixed range, or the range
  is changing), 1 suitable for Calibrate Gain Ratio, 2 too dark, 3 too bright."`. `TS` tag → `# @web TS
  section=measurements submitGroup=self kind=readonly label="Timestamp" format=epoch decimals=0`. Wiring comment "passed
  directly as this driver's own log= kwarg" and `# @wiring fram_target FRAMManager log optional kwarg`. Limits comment
  "bounds kept in sync with _MIN/_MAX_TRIGGER_S by hand …" and `# @limits trigger_s 1..3600`. The `ISLResults`
  comment (`:167-169`) → "# Elements 3 and 4 travel WITH the sample - the range the lux conversion divides by, the span
  the normalised outputs do - never read back at store time; the last is the cycle's UTC timestamp." (its "ANY element"
  clause goes with M.SRC_SENS.089's condition).
- **Resolved**: A.U23.16 removes `defaultValue` from the tag grammar on a grep that found only SCD30's `ContMeas`; this
  tag carries it too, so it goes here in U23 or the build fails — the website behaviour of a dispatch toggle with no GET
  value is WEB's (GAP-12).
- **Unit**: U23 (latest: the `defaultValue` removal); stages U6 (`TS`), U10 (names, keys, suffix), U15 (`CalLight`,
  `_N_STORE_CFG`)
- **Depends**: A.U10.40 (map), A.U6.19 (`format` key), A.U11.34 (A.U15.36's Depends)
- **Blast carried by**: generated definitions (`html/definitions/dev.json` `CalLight`, renamed keys) → A.U15.36/A.U10.40/
  A.U6.04 (GEN); `mockdata/dev.json` `"CalLight": 1` and renamed keys, js label/colour → A.U15.36/A.U10.40/A.U23.20
  (WEB); `tests/test_asy_isl29125_driver.py:1068` key set, `tests_scripts/test_measurement_field_tuple_agreement.py`,
  A.U24.57's nested-body test (`CalLight` flat) → A.U15.36/A.U24.57 (TEST_UNIT, TSC); SPEC M.1.5 code table →
  A.U15.36 (SPEC); the dispatch toggle's rendering without `defaultValue` → GAP-12 (WEB); `@web-group` inventory →
  A.U20.26 (TSC, unchanged pairs)
- **Kind**: code

### M.SRC_SENS.073 `ISL29125_Reader` construction and its state
- **From**: A.U5.02 (`(i2c, irq_pin, *, trigger_s, irq_pull_up, max_module_error, name_ext, cfg_path, log)`), A.U15.28
  (`address` goes), A.U10.43 (`trigger_s`), A.U10.35 (`_isl`, `_base_trigger_event`, `_read_event`, `_trigger_timer`,
  `_trigger_period`, `_trigger_counter`), A.U27.03 + A.SDEP.15 (Timer comment), A.U15.R04 (3) (`_recovery_bus`), A.U3.14
  (`_brownout_seen` goes), A.U15.22 (3)-(4) (`_filt_coeff`, `_cycle_filter`, `_unsettled_cycle`), A.U15.31 (comment
  `:254-256`), A.U15.32 (`_int_held`), A.U15.R05 (its once-per-episode flag), A.U15.33 (`_threshold_lock`), A.U15.36
  (`_last_cal_light`), A.U10.39/A.U10.43 (registrations), A.U10.25 (registrations stay in `__init__`: holds), A.U10.40
  (comment `:282-284`)
- **Site**: `src/asy_isl29125_driver.py:197-288`
- **Change**: `__init__(self, i2c: "I2C", irq_pin: int, *, trigger_s: int = 1, irq_pull_up: bool = True,
  max_module_error: int = 5, name_ext: str = "", cfg_path: str = "", log: LogConfig = DEFAULT_LOG)`;
  `super().__init__(ISL29125(<13 × None>), _NAME, <the eleven _VAL_ tuples>, max_module_error=max_module_error,
  name_ext=name_ext, cfg_path=cfg_path, log=log)`; `self._isl = ISL29125_I2C(i2c)`; `self._recovery_bus = i2c`; the
  pull-up comment and `self.irq_pin` unchanged; `self._base_trigger_event`, `self._read_event` (ThreadSafeFlags, comment
  unchanged); the Timer comment → "# Bare Timer() is valid on rp2 (id defaults to -1); the stub requires an id. Removal
  trigger: SPECIFICATION.md B.15." then `self._trigger_timer = Timer()`; `self._trigger_period =
  LockedValue(init_value=int(trigger_s))`; `self._trigger_counter = 0`. State, in HEAD order with: `_brownout_seen`
  gone; `self._int_held = False` with "# INTSEL parked because the peak rule overrules the green window it watches
  (see _read_isl())."; `self._int_rearmed = False` with "# One INT re-arm per dead-line episode; cleared by the next
  interrupt-led decision."; `self._threshold_lock = asyncio.Lock()` with "# Serialises every threshold/range writer:
  derive the counts, write, commit."; `self._last_cal_light = 0` next to `_last_overrange` (comment: "The CalLight
  code for the most recent stored sample, set once per read cycle like Overrange."); the `_reconciled_write_failures`
  comment → "# The protocol layer's failed-write sequence as of the last reconciliation - see / #
  _verify_after_failed_write(). Starts level with it, so a clean boot reconciles nothing."; after `_gain_ratio`:
  `self._filt_coeff = -1.0` and `self._cycle_filter = -1.0` ("# FiltCoeff, cached like the other software knobs, and
  the value this cycle captured (schema default: off)."), `self._unsettled_cycle = False`. Registrations with the new
  `_VAL_` names; `_push_trigger_s`; the `:282-284` comment says "Calibrate is command-only".
- **Resolved**: A.U5.02 counts 9 parameters with `address`; A.U15.28 removes it first (A.U5.02's own note) — 8, inside
  `max-args` (A.U5.17), so no exemption. The shared divider reads `_base_trigger_event`/`_read_event`/
  `_trigger_period`/`_trigger_counter` (M.SRC_SENS.045's settlement: one set of private names for both dividing
  drivers).
- **Unit**: U15 (stages U5 signature, U10 names, U27 comment)
- **Depends**: M.SRC_SENS.070-072; A.U10.R01 (`_recovery_bus` slot)
- **Blast carried by**: generated construction (no `address=`, `trigger_s=`, `log=`) → A.U5.03/A.U10.43 (GEN); tests
  constructing the reader or reading the renamed attributes (`make_protocol(address=_ADDR)`, `reader.isl`, …) →
  A.U15.28/A.U5.02/A.U10.35 (TEST_UNIT); `tests/_bus_hazard_catalog.py:323`, `tests/test_bus_hazard_multi_device.py`
  → A.U15.28 (TEST_HELP, TEST_UNIT); device scripts `isl29125_*` → A.U5.02/A.U10.35/A.U10.39 (HW_DEV); SPEC B.15 →
  A.U27.03
- **Kind**: code

### M.SRC_SENS.074 `_init_isl()`: restart resets, cached filter, the init rungs
- **From**: A.U10.10 (`pr.setup()` leaves), A.U15.34 (resets), A.U15.22 (3) (`_filt_coeff` from the init batch), A.U3.05
  (config read → console), A.U2.12 (numbers), A.U15.R04 (3) (`_init_failed()`/`_init_done()`), A.U10.43
  (`set_trigger_s`), A.U10.39 (names), A.U10.21 (`setup()` returns `True` or raises), A.U30.19
- **Site**: `src/asy_isl29125_driver.py:292-348`
- **Change**: first lines (A.U15.34): `self._err_cnt_internal = 0`; `self._filtered[0] = self._filtered[1] =
  self._filtered[2] = None` (in place); `self._irq_fired = False`; `self._periodic_only_switches = 0`; `self._int_held =
  False`; `self._int_rearmed = False`. `try: await self._isl.setup()` `except Exception as e: report_if_fatal(e); await
  self.pr.err_s("Error in initial setup:", e, errno=_ERR_INIT); await self._init_failed(); return False`. Config batch
  with the new `_VAL_` names; a failed or short read → `self.pr.err("Error reading config data!")` (console, the config
  store persisted the cause) and `return False` (no rung). The `:319-320` comment → "# set_trigger_s() never raises (logs
  BAD_ARG, keeps the previous value) - a bad stored / # SampleInterval is a pure software timing knob, not a reason to
  fail this whole init attempt."; `await self.set_trigger_s(int_values[0])`; `self._ar_thresh, self._ar_dwell_s,
  self._filt_coeff = float_values[0], float_values[1], float_values[2]`; the rest as HEAD; the configure `except
  Exception as e: report_if_fatal(e); await self.pr.err_s("Error setting config data:", e, errno=_ERR_CHIP_SET); await
  self._init_failed(); return False`; `if self._range_auto: await self._switch_range(self._active_range)` (comment kept);
  `await self._init_done()`; `self.pr.one("initialized")`; `return True`.
- **Resolved**: A.U15.34's resets "after `pr.setup()`" open the function once A.U10.10 moves `pr.setup()` to the boot
  batch (A.U15.34's Depends). `_int_rearmed` (A.U15.R05's flag) joins the reset list: an episode never outlives the
  task — agent addition, OR2.c list. Kept on purpose, as A.U15.34 states: `_reconciled_write_failures`, the calibration
  run and candidate, `_last_switch_ms`, the cached knobs.
- **Unit**: U15 (stages U2, U3, U10; U30 handlers)
- **Depends**: M.SRC_SENS.073; A.U10.R01, A.U13.R01, A.U10.10
- **Blast carried by**: L1 restart cases (filter, `_irq_fired`) → A.U15.34 (TEST_UNIT); SPEC M.1.2 "State across a task
  restart" table (gains `_int_held` and the re-arm flag rows) → A.U15.34/A.U15.R04 (SPEC); config-read tests
  `tests/test_asy_isl29125_driver.py:875` → A.U3.05 (TEST_UNIT); streak tests `:953, :2539` → A.U15.R04/A.U10.R01
- **Kind**: code

### M.SRC_SENS.075 `_read_isl()`: timestamp, unsettled discard, INT parking, CalLight code
- **From**: A.U10.06 (`utc_now()` before the `try`; the `except` keeps it), A.U15.22 (3)-(4) (filter capture; unsettled
  discard), A.U15.32 (park and re-arm), A.U15.36 (per-cycle code), A.U3.14 (every brownout warns: through
  M.SRC_SENS.076), A.U2.12 (55, 56, 11), A.U0.16 (the decision comment is `_evaluate_range()`'s), A.U30.19
- **Site**: `src/asy_isl29125_driver.py:368-431`
- **Change**: `async def _read_isl(self) -> "ISLResults":` `self._unsettled_cycle = False`; `timestamp = utc_now()`; the
  five value locals `None`; `try:` `await self._verify_after_failed_write()` (comment kept); `if
  self._isl.time_to_settle_ms() > 0:` `await self._settle_wait()`; `if self._isl.time_to_settle_ms() > 0:` (one comment
  line: "# Past the bound the data may come from the previous CONFIG1: discard the cycle, count nothing.")
  `self._unsettled_cycle = True`; `return None, None, None, None, None, timestamp`. Capture block as HEAD plus
  `self._cycle_filter = self._filt_coeff`. Status read: `except Exception as e: report_if_fatal(e); await
  self.pr.err_s("Status read failed:", e, errno=_ERR_ISL_STATUS_READ); return None, None, None, None, None, timestamp`.
  `irq_fired, self._irq_fired = self._irq_fired, False`; `brownout, threshold_fired = self._handle_status(status)`; `if
  brownout:` (comment kept) `await self._recover_brownout()`; `return None, None, None, None, None, timestamp`. The
  bus-fault branch logs `errno=_ERR_ISL_BUS_FAULT` and returns the same shape. `counts, saturated = …`; `target =
  self._evaluate_range(counts, saturated=saturated)`; `if target is not None:` HEAD body; `elif self._range_auto:`
  `if self._int_held:` `if self._green_in_window(counts[0]): await self._set_int_armed(armed=True)` `elif
  threshold_fired and irq_fired: await self._set_int_armed(armed=False)` with A.U15.32's three-line comment on this
  block. `_last_overrange` as HEAD; `self._last_cal_light = 0 if not sample_range_auto or target is not None else
  self._band_code(counts[0])`; `await self._measure_gain_ratio(counts[0])`; `self.pr.all("read")`; `green, red, blue =
  counts`. Outer `except Exception as e: report_if_fatal(e); green = red = blue = sample_range = sample_span = None;
  await self.pr.err_s("Read failed:", e, errno=_ERR_READ)`; return the six. New helpers: `def
  _green_in_window(self, green: int) -> bool:` — high range `fraction_to_counts(self._down_thresh()) < green`, low range
  `0 < green < fraction_to_counts(self._ar_thresh)` (the window the active range arms; one comment line "Strictly
  inside: on the low range a 0 threshold still fires on 'below or equal' (FN8424 p12)."); `async def
  _set_int_armed(self, *, armed: bool) -> None:` `try: await self._isl.configure(threshold_interrupt=armed)` `except
  Exception as e: report_if_fatal(e); await self.pr.err_s("Error setting the interrupt select:", e,
  errno=_ERR_CHIP_SET); return` then `self._int_held = not armed` (no await between the write's return and the flag).
- **Resolved**: A.U15.32 re-arms "each read cycle … as soon as green lies inside the window the active range arms" and
  parks when a flagged crossing gets no decision; the merged block tests both only on a cycle with no switch decided
  (`target is None`), so the window is the one the chip is armed with — agent precision, OR2.c list. The one
  flag-and-INTSEL writer is `_set_int_armed()` plus `set_range_auto(True)` (M.SRC_SENS.080). Fact checked: "If the ALS
  value crosses below or is equal to the lower threshold, an interrupt is asserted" (`dstxt/isl29125…:877`); "outside
  the user's programmed window" (`:398-410`), both p12.
- **Unit**: U15 (stages U2, U10 timestamp; U30 handlers)
- **Depends**: M.SRC_SENS.073, M.SRC_SENS.076, M.SRC_SENS.078, M.SRC_SENS.081, M.SRC_SENS.089; A.U10.06
- **Blast carried by**: L1 park/re-arm/darkness/interleave cases and L2 red-dominant scene → A.U15.32 (TEST_UNIT, TWIN);
  unsettled-discard case → A.U15.22; CalLight edge cases and L2 dark/mid/bright → A.U15.36; four tiers of the CONFIG2-3
  burst → A.U15.32 blast (TEST_UNIT, TWIN, HW_DEV, HW_BENCH); SPEC M.1.4 parking sentence, release note D4.66 →
  A.U15.32 (SPEC, DOCS via U37); pre-sync L1 (values published, TS `None`) → A.U10.06 (TEST_UNIT)
- **Kind**: code

### M.SRC_SENS.076 Brownout, re-applied configuration and the participant rung
- **From**: A.U3.14 (latch goes; every brownout warns), A.U15.R04 (1)-(2) (`_reapply_configuration()`,
  `_recover_device()`), A.U2.12 (w10 → 30, e33 → 13), A.U30.19
- **Site**: `src/asy_isl29125_driver.py:465-479`; new `_reapply_configuration()`, `_recover_device()`
- **Change**: `async def _recover_brownout(self) -> bool:` `await self.pr.wrn_s("Brownout detected - re-applying the whole
  configuration.", wrnno=_WRN_ISL_BROWNOUT)`; `return await self._reapply_configuration()`. `async def
  _reapply_configuration(self) -> bool:` `try: await self._isl.configure(force=True); await self._isl.clear_brownout()`
  `except Exception as e: report_if_fatal(e); await self.pr.err_s("Error re-applying configuration:", e,
  errno=_ERR_CHIP_SET); return False`; `if self._range_auto: await self._switch_range(self._active_range)  # never
  raises; logs its own`; `return True`. `async def _recover_device(self) -> bool: return await
  self._reapply_configuration()` with "# Participant rung: re-configuration from the shadow; the 0x46 reset stays
  setup()'s (task restart)."
- **Resolved**: BMP3XX's and SCD30's rungs hold `_set_lock` (A.U11.27) because they re-apply the stored file config a PUT
  may be half-way through persisting; this rung re-applies the shadow, which every writer mutates and writes inside one
  session hold (`configure()`), and `_switch_range()` runs under `_threshold_lock` — so no `_set_lock` here (A.U15.R04's
  race statement; agent reading, OR2.c list). A forced re-apply keeps a parked INT parked (the shadow holds INTSEL 00),
  so `_int_held` and the chip agree.
- **Unit**: U15 (stage U3 latch removal; U30 handler)
- **Depends**: M.SRC_SENS.080 (`_switch_range()`), A.U10.R01
- **Blast carried by**: `tests/test_asy_isl29125_driver.py:1566-1595` (one slot, `ErrCount == 5`) and the RF175 case →
  A.U3.14/A.U3.03 (TEST_UNIT); rung cases (no-brownout re-apply, raising burst, no `recover()` on config-read failure)
  and the mid-operation hazard case → A.U15.R04 (TEST_UNIT, TWIN); twin Run 5c (`settled > 0`) holds → A.U15.R04 (SCR);
  SPEC `:6675-6678` → A.U3.14/A.U3.10 (SPEC); SPEC M.1.2 restart row → A.U15.R04
- **Kind**: code

### M.SRC_SENS.077 Silent helper catches print; the dead-INT re-arm
- **From**: A.U15.29 (`_device_id_answers()`, `_verify_after_failed_write()`), A.U15.32 (the detector pauses while
  parked), A.U15.R05 (one re-arm per episode), A.U2.12 (w13 → 32), A.U30.19
- **Site**: `src/asy_isl29125_driver.py:433-455, 481-493`
- **Change**: `_device_id_answers()`: `except Exception as e: report_if_fatal(e); self.pr.err("Device-ID re-read
  failed:", e); return False` (comment kept). `_verify_after_failed_write()`: `except Exception as e: report_if_fatal(e);
  self.pr.err("Config read-back for reconciliation failed, retried next cycle:", e); return` (the trailing comment
  goes into the message). `_note_decision_source()`: `if self._int_held: return` first, with "# Parked on purpose: a
  periodic-led decision is by design now, not a dead line."; `if threshold_fired: self._periodic_only_switches = 0;
  self._int_rearmed = False; return`; the count as HEAD; at the threshold, after `self._periodic_only_switches = 0`,
  `await self.pr.wrn_s(…, wrnno=_WRN_ISL_PERIODIC_ONLY)`, then `if not self._int_rearmed: self._int_rearmed = True;
  await self._rearm_interrupt()`. New `async def _rearm_interrupt(self) -> None:` `try: await
  self._isl.configure(force=True)` `except Exception as e: report_if_fatal(e); await self.pr.err_s("Error re-arming the
  interrupt:", e, errno=_ERR_CHIP_SET); return`; `await self._write_thresholds(self._active_range)` (logs its own).
- **Resolved**: A.U15.R05 adds no second persisted entry for the event (OR56.a (1)): the wrnno 32 is it; a failed
  re-arm logs its own CHIP_SET.
- **Unit**: U15 (stage U2 numbers; U30 handlers)
- **Depends**: M.SRC_SENS.080 (`_write_thresholds()`)
- **Blast carried by**: L1 console-only ID/reconciliation cases → A.U15.29 (TEST_UNIT); re-arm L1/L2 → A.U15.R05
  (TEST_UNIT, TWIN); wrnno-13 → 32 asserts → A.U2.12
- **Kind**: code

### M.SRC_SENS.078 `_store_isl()`: captured filter, values-only guard, CalLight
- **From**: A.U15.22 (3) (per-sample config read goes), A.U10.06 (guard on values only), A.U15.36 (`CalLight`)
- **Site**: `src/asy_isl29125_driver.py:495-543`
- **Change**: guard `if green is None or red is None or blue is None or sample_range is None or sample_span is None:
  return` (the timestamp may be `None` before the first sync). `:500-507` (the FiltCoeff read, its errno-14 fallback
  and comment) go; `filter_coefficient = self._cycle_filter`. The stored tuple gains `CalLight=self._last_cal_light`
  after `GainMeas`; `TS=timestamp`.
- **Resolved**: —
- **Unit**: U15 (stage U10 guard)
- **Depends**: M.SRC_SENS.072, M.SRC_SENS.075
- **Blast carried by**: `tests/test_asy_isl29125_driver.py:1149-1175` goes, tests calling `_store_isl()` directly rely on
  `_cycle_filter`'s default → A.U15.22 (TEST_UNIT); store-guard tests with a `None` timestamp → A.U10.06
- **Kind**: code

### M.SRC_SENS.079 `_evaluate_range()` and `_settle_wait()`: owner tag, dwell horizon
- **From**: A.U0.16 (comment), A.U15.35 (stored tick bounded), A.U15.22 (4) (`_settle_wait()` comment)
- **Site**: `src/asy_isl29125_driver.py:569-589, 614-623`
- **Change**: comment `:570-572` → "# Decides on the PEAK of all three channels in both directions (owner, 2026-09-12):
  hardware / # is green-only (one INTSEL channel), but the output is a colour triple. Peak-up with green-down / #
  oscillates - a red-dominant scene switches up, then back once the dwell ends." High-range branch: `now =
  time.ticks_ms()`; `elapsed = time.ticks_diff(now, self._last_switch_ms)`; `if elapsed > _MAX_DWELL_MS:
  self._last_switch_ms = time.ticks_add(now, -_MAX_DWELL_MS)` with "# Keeps the stored tick within the largest dwell,
  far inside ticks_diff()'s 2**29 ms horizon."; then `if peak > …: return None`; the dwell test `if elapsed <
  int(self._ar_dwell_s * 1000)`. `_settle_wait()` comment → "# Bounded rather than an open `while pending`: concurrent
  config writes can keep pushing the / # deadline out; past the bound the cycle is discarded, never published, so the
  loop cannot / # starve and nothing stale is reported."
- **Resolved**: A.U15.35 places the bound "before the `peak >` test"; `elapsed` is computed once and reused by the dwell
  test (clamping it too is harmless: every dwell ≤ `_MAX_DWELL_MS`).
- **Unit**: U15 (stage U0 comment)
- **Depends**: M.SRC_SENS.071
- **Blast carried by**: SPEC `:4463`, `:6781` → A.U0.16 (SPEC); Ticks30 crossing case (c) → A.U15.35 with A.U14.34's
  helper (TEST_UNIT); `:1291-1310` comment → A.U15.22 (TEST_UNIT)
- **Kind**: code

### M.SRC_SENS.080 One locked threshold writer; setters rewrite chip thresholds
- **From**: A.U15.33 (`_threshold_lock`, `_write_thresholds()`, setters), A.U15.S01 (paired with M.SRC_SENS.086), A.U15.32
  (`set_range_auto(True)` clears the flag), A.U2.12 (29/30/38/16/27 → 13/21)
- **Site**: `src/asy_isl29125_driver.py:591-612` (`_switch_range()`), `:932-946` (`set_resolution()`), `:961-979`
  (`set_range_auto()`), `:981-988` (`set_autorange_thresh()`)
- **Change**: `async def _write_thresholds_locked(self, range_fs: int, ar_thresh: float) -> bool:` (caller holds
  `_threshold_lock`) — HEAD `:596-599` with `ar_thresh` in place of `self._ar_thresh` and `_down_thresh()` computed from
  it; `except Exception as e: report_if_fatal(e); await self.pr.err_s("Error writing auto-range thresholds:", e,
  errno=_ERR_CHIP_SET); return False`; `return True`. `async def _write_thresholds(self, range_fs: int, ar_thresh: float
  | None = None) -> bool:` `async with self._threshold_lock:` `value = self._ar_thresh if ar_thresh is None else
  ar_thresh`; `if not await self._write_thresholds_locked(range_fs, value): return False`; `if ar_thresh is not None:
  self._ar_thresh = ar_thresh`; `return True`. `_down_thresh()` gains a parameter default (`ar_thresh: float | None =
  None`, `None` → `self._ar_thresh`). `_switch_range()`: its comment kept; the whole body under `async with
  self._threshold_lock:` — `if not await self._write_thresholds_locked(target_range, self._ar_thresh): return False`;
  the range-bit write `except Exception as e: report_if_fatal(e); …errno=_ERR_CHIP_SET` (comment kept); the two
  updates. `set_resolution()`: configure failure `errno=_ERR_CHIP_SET`; after `_reapply_persist(...)`, `await
  self._write_thresholds(self._active_range)` whatever `_range_auto` is, with "# The registers compare the RAW ADC value,
  so a resolution change rescales them, armed or not."; `return True` (the `if self._range_auto: _switch_range` goes).
  `set_range_auto()`: after the arming write in the `flag` branch `self._int_held = False` (no await between);
  `errno=_ERR_CHIP_SET`; rest as HEAD. `set_autorange_thresh()`: `thresh = await self._checked_cfg(value,
  _VAL_AUTO_RANGE_THRESH)`; `None` → `False`; `return await self._write_thresholds(self._active_range,
  ar_thresh=float(thresh))`; its comment → "# The down point follows automatically; the cache changes only once the
  chip's registers took the value, so a failed push restores a consistent persisted value."
- **Resolved**: A.U15.33 leaves a failed threshold write in `set_resolution()` unspecified; it stays as HEAD's (logged,
  `True` returned: the resolution itself landed and a later switch or re-arm rewrites the registers) — agent reading,
  OR2.c list. Lock order `_set_lock` → `_threshold_lock` → device session → bus lock (a PUT reaches
  `_threshold_lock` from inside `_set_lock`; nothing takes `_set_lock` inside `_threshold_lock`) — the C.8 lock table
  gains the new lock (GAP-13). OR109.a (0) holds: every derived per-call input (counts from `_ar_thresh`, the scale
  from `_resolution`) is derived inside the hold that writes it.
- **Unit**: U15 (stage U2 numbers; U30 handlers)
- **Depends**: M.SRC_SENS.086 (`set_thresholds()` scales inside the session); M.SRC_SENS.082 (`_checked_cfg()`)
- **Blast carried by**: fixed-mode resolution tests and `set_autorange_thresh` cache-only tests gain the burst, new L1
  race cases → A.U15.33 (TEST_UNIT); four tiers (one 4-byte write per setter call) → A.U15.33/A.U15.S01 blast (TEST_UNIT,
  TWIN, HW_DEV, HW_BENCH); SPEC M.1.4 derived-down-point sentence → A.U15.33; SPEC `:6737-6739`, DR `:66-69` →
  A.U0.33/A.U0.36 (SPEC, DOCS); C.8 table → GAP-13
- **Kind**: code

### M.SRC_SENS.081 Calibration: one band test, bounded candidate tick
- **From**: A.U15.36 (`_band_code()`), A.U15.35 (`_measured_ratio()` clears; `_cal_until_ms` stated), A.U2.12 (35 → 11),
  A.U30.02/A.U30.03 (`_cal_recent` listed as bounded: no edit), A.U30.19
- **Site**: `src/asy_isl29125_driver.py:627-714`
- **Change**: new `def _band_code(self, green_counts: int) -> int:` `lo = self._isl.fraction_to_counts(self._down_thresh())`;
  `hi = self._isl.fraction_to_counts(self._ar_thresh)`; `if green_counts <= lo: return 2`; `if green_counts >= hi:
  return 3`; `return 1`, with "# The calibration band: 1 inside the overlap, 2 too dark, 3 too bright (the CalLight
  codes, SPECIFICATION.md M.1.5)." `_measure_gain_ratio()`: after the window check a one-line comment "#
  _cal_until_ms is compared only while _calibrating, which ends at this 2-minute window."; `:640` → `if
  self._band_code(green_counts) != 1:`. `_read_on()`: `except Exception as e: report_if_fatal(e); await
  self.pr.err_s("Paired gain-ratio reading failed:", e, errno=_ERR_READ)`. `_measured_ratio()`: `if self._cal_meas is
  None: return None`; `if time.ticks_diff(time.ticks_ms(), self._cal_meas_until_ms) >= 0: self._cal_meas = None; return
  None` (comment → "# None once the hold expires, and the candidate goes, so the stored tick is never compared again.");
  `return self._cal_meas`.
- **Resolved**: —
- **Unit**: U15 (stage U2; U30 handler)
- **Depends**: M.SRC_SENS.080 (`_down_thresh()`)
- **Blast carried by**: band-edge L1 cases → A.U15.36; Ticks30 crossing case (b) and `:3083` → A.U15.35 (TEST_UNIT);
  I.2 allocation rows → A.U30.02 (SPEC); allow-list entries → A.U30.03 (TSC)
- **Kind**: code

### M.SRC_SENS.082 Config read-back, divergence and the two numeric helpers
- **From**: A.U15.30 (`:717-719` comment), A.U2.12 (28 → 12; w11 → 31; 34 → 13; 24 → 13; `_snapshot_field(index,
  what)`; `_checked_cfg(value, schema)`), A.U15.38 (1) (the isinstance arm goes), A.U11.S01 (the validator's slot
  type), A.U10.43 (`_reapply_persist(trigger_s)`), A.U10.39 (names), A.U30.19
- **Site**: `src/asy_isl29125_driver.py:716-788`
- **Change**: `_read_sensor_dict()` comment → "# Reads the real registers rather than the shadow - the only thing that
  can detect the two / # diverging. A read of 0x01 is not the write Table 7 names, so a read-only snapshot starts
  nothing / # and creates no read-modify-write hazard."; its `except Exception as e: report_if_fatal(e); …
  errno=_ERR_CHIP_GET`; the `dict.fromkeys` keys through the new `_VAL_` names; return type `dict[str, int | float |
  str | bool | None]` unquoted. `_check_divergence()`: `wrnno=_WRN_ISL_DIVERGED`; `except Exception as e:
  report_if_fatal(e); … errno=_ERR_CHIP_SET`. `async def _snapshot_field(self, index: int, what: str) -> int | None:`
  logs `errno=_ERR_CHIP_GET` after `report_if_fatal(e)`. `async def _checked_cfg(self, value: int | float, schema:
  "ConfigSchema") -> int | float | None:` comment `:768-770` kept; `is_error, coerced = type_or_range_error(value,
  schema[0])`; `if is_error: await self.pr.err_s("Error setting", schema[0][0], "- out of range:", value,
  errno=_ERR_BAD_ARG); return None`; `checked: int | float = coerced`; `return checked` (`:772-774` go).
  `_reapply_persist(self, trigger_s: int)`: `except Exception as e: report_if_fatal(e); … errno=_ERR_CHIP_SET`.
- **Resolved**: A.U15.38 (1) removes the arm as unreachable; A.U11.S01 keeps it as narrowing (SUPP_coverage A-C note
  1) — settled by the lead's L1 answer "no" (2026-09-30, SUPP_coverage open points): "A.U15.38 (1) stands"; a
  never-firing check is dead code, narrowing belongs at the type level. The annotated local narrows while the
  validator's slot is `Any`; if A.U11.S01 types it `CfgValue`, the type-level fix is the validator's to provide (an
  honest per-kind return), never an `isinstance()` here — routed with the finding that M.SRC_CORE.047 still writes
  A.U11.S01's never-true `type()` checks into `type_or_range_error()` against the same ruling (GAP-14).
- **Unit**: U15 (stages U2, U10; U30 handlers)
- **Depends**: A.U11.S01 (slot type, SRC_CORE)
- **Blast carried by**: `tests/test_asy_isl29125_driver.py:2878-2890` goes → A.U15.38 (TEST_UNIT); E.5.1 rows → A.U35.41
  (SPEC); SPEC M.1.4 settle bullet → A.U15.30 (SPEC); number asserts → A.U2.12
- **Kind**: code

### M.SRC_SENS.083 Push callbacks, starters, timer arm and the reader loop
- **From**: A.U10.43 (`_push_trigger_s`), A.U15.40 (2) (`_base_trigger()` goes), A.U10.44 (`start_asy_trigger()` creates
  the shared `_trigger_loop()`; `_read_loop`), A.U10.12 (`get_trigger_starters()`), A.U15.41 (arm failure), A.U15.43 +
  A.U10.46 (types), A.U15.22 (4) (`condition`), M.SRC_SENS.089 (the pre-sync rule)
- **Site**: `src/asy_isl29125_driver.py:350-357, 798-872, 1041-1050`
- **Change**: `_base_trigger()` goes. `_push_trigger_s()` calls `set_trigger_s`; the other push callbacks unchanged
  (unquoted annotation). `start_asy_read(self) -> asyncio.Task[None]` over `self._read_loop()`; `start_asy_trigger(self)
  -> asyncio.Task[None]` over `self._trigger_loop()`. `start_timer()`: `self._trigger_timer.init(period=1000,
  mode=Timer.PERIODIC, callback=lambda _b: self._base_trigger_event.set())` in `try`, `except (MemoryError, OSError) as
  e: self._timer_failed(e, self._base_trigger_event)` with "# Alarm pool exhausted (ENOMEM) or no memory: wake the
  waiting task, which logs it and ends; its restart re-arms."; the pin IRQ arm and its comment unchanged (not a Timer;
  a re-arm on restart re-registers the same handler). `get_task_starters(self) -> "list[TaskStarter]"`;
  `get_trigger_starters(self) -> "list[TimerStarter]": return [self.start_timer]`; `get_timer_starters(self) ->
  "list[TimerStarter]": return []`; `stop_timer()` uses `self._trigger_timer`. `async def _read_loop(self) -> None:` `if
  not await self._init_isl(): return`; the loop on `self._read_event`; `results = await self._read_isl()`; `if not
  await self._error_check(results, condition=results[0] is None and not self._unsettled_cycle): return`; `await
  self._store_isl(results)`.
- **Resolved**: the divider's shared name is `_trigger_loop()` (M.SRC_SENS.045, GAP-8).
- **Unit**: U15 (stage U10: A.U10.12 split, A.U10.44 names, M.SRC_SENS.089's condition)
- **Depends**: M.SRC_SENS.073; A.U10.12, A.U15.41, A.U15.40 (helpers in `SensorReader`)
- **Blast carried by**: generated trigger-starter collector → A.U10.12 (GEN); `tests/test_asy_isl29125_driver.py:2396,
  2412` and `_base_trigger` callers → A.U15.41/A.U10.12/A.U15.40 (TEST_UNIT); `isl29125_mechanism_envelope.py:205-206`
  → A.U10.44 (HW_DEV); `read_loop()) is False` asserts → A.U15.43
- **Kind**: code

### M.SRC_SENS.084 Reader getters and setters: numbers, cached filter, nested body
- **From**: A.U2.12 (getter numbers via `_snapshot_field`; setter 16/18/20/22 → 13; 25/26/27 → 21 via `_checked_cfg`),
  A.U15.22 (3) (`set_filter_coefficient()` caches), A.U19.16 (the `:1026` "Failed" comment: rewritten here), A.U15.36 +
  A.U10.46 + A.U15.43 (`get_dict_data() -> "JsonDict"` with `CalLight`), A.U10.43 (`set_trigger_s`), A.U10.39/A.U10.40
  (names, comment `:899-900`), A.U30.19
- **Site**: `src/asy_isl29125_driver.py:876-1039`
- **Change**: `get_dict_data(self) -> "JsonDict"`: body as HEAD plus `"CalLight": data.CalLight` after `"GainMeas"`.
  `get_dict_cfg()`: comment says "Calibrate is deliberately absent"; the ten `_VAL_` names. `get_resolution()` …
  `get_ir_comp_adjust()` → `self._snapshot_field(<index>, "<what>")`. `async def set_trigger_s(self, value: float) ->
  bool:` `trigger_s = await self._checked_cfg(value, _VAL_SAMPLE_INTERVAL)`; `None` → `False`; `await
  self._trigger_period.set_value(int(trigger_s))`; `return await self._reapply_persist(int(trigger_s))`.
  `set_range()`, `set_ir_comp_offset()`, `set_ir_comp_adjust()`: `except Exception as e: report_if_fatal(e); …
  errno=_ERR_CHIP_SET`. `set_autorange_dwell()`, `set_gain_ratio()`: `_checked_cfg(value, <schema>)`.
  `set_filter_coefficient()`: `coeff = await self._checked_cfg(value, _VAL_FILT_COEFF)`; `None` → `False`;
  `self._filt_coeff = float(coeff)`; `return True`; comment → "# Caches the coefficient like the other software knobs;
  the read cycle captures it with the range and resolution." `start_calibration()` unchanged. (`set_resolution()`,
  `set_range_auto()`, `set_autorange_thresh()`: M.SRC_SENS.080.)
- **Resolved**: —
- **Unit**: U15 (stages U2, U10; U30 handlers)
- **Depends**: M.SRC_SENS.082
- **Blast carried by**: `tests/test_asy_isl29125_driver.py:1127-1146` holds → A.U15.22; nested-body/tuple test →
  A.U24.57 (TEST_UNIT); number asserts → A.U2.12; `JsonDict` alias → A.U10.46 (SRC_CORE)
- **Kind**: code

### M.SRC_SENS.085 `ISL29125_I2C` construction: fixed address, shared session, sequence
- **From**: A.U15.28 (no `address`), A.U15.40 (1) (`ISL29125_DeviceSession` goes), A.U10.35 (`_i2c_isl29125`), A.U10.38
  (session rename moot), A.U30.07 (2) (`_rgb_burst`), A.U15.31 + AC_NOTES 17 (conditional wrap), A.U15.34
  (`_dark_offset()` comment)
- **Site**: `src/asy_isl29125_driver.py:1053-1103, 1151-1154, 1377`
- **Change**: `ISL29125_DeviceSession` goes. `__init__(self, i2c: "I2C") -> None:` `self._i2c_isl29125 =
  DeviceSession(I2CDevice(i2c, _ISL29125_ADDR))` (the `:1065-1066` comment goes: the constant carries it);
  `self._rgb_burst = bytearray(_DATA_BURST_LEN)`; the shadow fields as HEAD; the `_write_failures` comment → "# Bumped
  whenever a shadow write raises: a wrap-by-design sequence (wraps at COUNTER_CAP) / # the reader compares for
  equality - saturating it would freeze reconciliation." `configure()`'s `:1377` → `self._write_failures =
  self._write_failures + 1 if self._write_failures < COUNTER_CAP else 0`. `write_failures()` comment → "# The
  failed-shadow-write sequence (compared for equality only). The chip is the authority / # after one, because the burst
  may have landed in part - see configure()'s own roll-back." `_dark_offset()` comment gains a third line "# DDark is
  specified in 16-bit counts (FN8424 p3), so it is subtracted after the 12-bit shift." (the first two lines kept,
  shortened to fit: "DDark is specified at range 0 only (p3), where it is material: the same dark current is / ~1/26.67
  count on the high range, so subtracting one there would remove real signal.").
- **Resolved**: A.U15.31's `& _SEQ_MASK` step allocates at the wrap (2**30 is a heap int on rp2) — AC_NOTES 17 replaces
  it with the conditional wrap at the shared `COUNTER_CAP`; no `_SEQ_MASK` constant. Datasheet: "Electrical
  Specifications … 16-bit ADC operation, unless otherwise specified", DDark 1/5 counts at range 0
  (`dstxt/isl29125…:198-211`).
- **Unit**: U15 (stage U10 attribute name; U30 buffer)
- **Depends**: M.SRC_SENS.071, M.SRC_SENS.013; A.U15.40, A.U10.01
- **Blast carried by**: wrap L1 case (`_write_failures = COUNTER_CAP` → 0, next cycle reconciles) → A.U15.31
  (TEST_UNIT); U35's L0 counter check lists the sequence → A.U15.31 (TSC); SPEC M.1.3 sequence clause → A.U15.31 (SPEC);
  `tests/test_asy_isl29125_driver.py:138-140` → A.U15.28 (TEST_UNIT); twin chip keys on 0x44 unchanged
- **Kind**: code

### M.SRC_SENS.086 Protocol reads and writes: bool bus, own burst, scale in session
- **From**: A.U13.07 + A.U13.09 (`:1136, :1172, :1413, :1434`), A.U13.10 (`_read_byte`, `get_config_snapshot`, `reset`
  via `get_register_bytes()`; its `read_counts` site superseded by A.U30.07), A.U30.07 (2) (burst into `_rgb_burst`;
  `unpack_from`), A.U15.S01 (scale inside the hold), A.U10.45 (`:1407` message), A.U10.21 (`setup() -> bool`), A.U15.30
  (`:1380-1382`), A.U15.35 (`time_to_settle_ms()`), A.U15.38 (2) (`encode_shadow()` try goes), A.U27.03 (`:1284`
  comment), A.U10.43 (`persist_for_interval(trigger_s)`), A.U10.35 (session attribute)
- **Site**: `src/asy_isl29125_driver.py:1105-1448`
- **Change**: every `async with self.i2c_isl29125 as isl` → `self._i2c_isl29125`. `_decode_rgb_burst()`: `green, red,
  blue = struct.unpack_from("<HHH", raw)` (no `bytes()` copy; the rest as HEAD). `_read_byte()`: comment → "# One
  register byte; None from the bus layer means no bus, raised so every caller's error path logs it."; `raw = await
  i2c.get_register_bytes(register, 1)`; `if raw is None: raise OSError("I2C bus not initialized")`; `return raw[0]`.
  `_write_shadow_locked()`: `if not await i2c.set_register_struct(first_register, f"{len(payload)}s", payload): raise
  OSError("I2C bus not initialized")`. `get_config_snapshot()`: `raw = await
  i2c.get_register_bytes(_REGISTER_CONFIG1, _CONFIG_BURST_LEN)`; `None` → the same raise; `return raw`.
  `set_thresholds()`: its comment gains "Scaled inside the session: the resolution shadow may change while this waits
  for the lock." (the block rewritten to three lines: "# Both counts arrive on the 16-bit scale and are rescaled to the
  active resolution (the registers / # compare RAW values); an omitted high_counts parks the up-crossing. Scaled inside
  the session: / # the resolution shadow may change while this waits for the lock."); `async with self._i2c_isl29125 as
  isl, isl.i2c_device as i2c:` then `:1165-1170` inside it, then `if not await
  i2c.set_register_struct(_REGISTER_THRESHOLDS, "4s", packed): raise OSError("I2C bus not initialized")`.
  `persist_for_interval(self, trigger_s: int)`; `:1284`'s trailing comment → "# const() tuple typed Any by the stub; the
  annotation narrows it. Removal trigger: SPECIFICATION.md B.15." (own line above). `time_to_settle_ms()`: `remaining =
  time.ticks_diff(self._settle_until_ms, time.ticks_ms())`; `if remaining <= 0: self._settle_until_ms =
  time.ticks_ms(); return 0` with "# A passed deadline moves up to now, so the stored tick never ages past the ticks
  horizon."; `return remaining`. `encode_shadow()`: `prst = _PRST_SETTINGS.index(self._persist)` without the `try`
  (comment `:1296-1298` kept). `configure()`: `:1380-1382` → "# Table 7 starts the ADC at an I2C write to 0x01 and
  leaves open whether a conversion in flight / # restarts, so every CONFIG1 writer arms the settle deadline where the
  write happens; outside / # the lock: timing bookkeeping only." `read_counts()`: the `:1386-1388` comment goes; `async
  with … as i2c:` `if not await i2c.get_register_into(_REGISTER_DATA, self._rgb_burst): raise OSError("I2C bus not
  initialized")`; `counts = self._decode_rgb_burst(self._rgb_burst)` in the same block with "# Filled and decoded under
  one hold: the buffer is this instance's own."; `if counts is None: raise OSError("unexpected RGB data burst read
  result")` with "# Narrows the Optional; a fixed 6-byte buffer always decodes." `verify_device_id()`:
  `RuntimeError(f"failed to find ISL29125, device ID {hex(device_id)}")`. `clear_brownout()`: bool-checked write,
  same raise. `async def setup(self) -> bool:` HEAD body, `return True`. `reset()`: bool-checked CMD write; `config =
  await i2c.get_register_bytes(_REGISTER_CONFIG1, _CONFIG_BURST_LEN)`; `config is None` → `OSError("I2C bus not
  initialized")`; `any(config)` → the HEAD `RuntimeError`; shadow reset as HEAD.
- **Resolved**: A.U13.10's `read_counts()` site → A.U30.07's own buffer (U30 note; same as BMP3XX, M.SRC_SENS.048). The
  kept `counts is None` re-check is the Optional narrowing A.U35.41's convention keeps with a comment (agent,
  2026-09-30), not a lead-L1 "unreachable check" — it narrows a return type, not a validated value.
- **Unit**: U30 (latest: burst buffer); stages U10 (names, message, `setup()`), U13 (bool bus,
  `get_register_bytes()`), U15 (session, scale, comments, settle tick, `encode_shadow()`), U27 (comment)
- **Depends**: M.SRC_SENS.011, M.SRC_SENS.013, M.SRC_SENS.085; A.U15.40
- **Blast carried by**: `tests/test_asy_isl29125_driver.py:192-210` hold, `:2599-2611` `silent_none` retargets, `:2605`,
  `:704-711` comment → A.U13.10/A.U30.07 (TEST_UNIT); bus-down L1 (ISL writes raise) → A.U13.09; `set_thresholds` race
  L1 → A.U15.S01; `:2896-2906` goes → A.U15.38; Ticks30 case (a), `:652-662` rewrite → A.U15.35/A.U14.34; message
  asserts ("Failed to find") → A.U10.45 (TEST_UNIT, HW_DEV); test comment `:634-636` → A.U15.30 (TEST_UNIT); four tiers
  (wire-identical; the threshold write unchanged in shape) → A.U30.07/A.U15.S01 blasts; SPEC C.8 derived-value clause
  → A.U12.18 + A.U15.S01 (SPEC, SUPP_coverage A-C note 6); SPEC G.2 `get_register_into()` → A.U30.07
- **Kind**: code

### M.SRC_SENS.087 Broad handlers report fatal errors first
- **From**: A.U30.19
- **Site**: every `except Exception as e:` in `src/asy_isl29125_driver.py` without a closing bare `raise`
- **Change**: in U30, after every earlier edit, each such handler starts with `report_if_fatal(e)`: `_init_isl()` (×2),
  `_read_isl()` (status read, outer), `_device_id_answers()`, `_set_int_armed()`, `_reapply_configuration()`,
  `_verify_after_failed_write()`, `_rearm_interrupt()`, `_write_thresholds_locked()`, `_switch_range()` (range bit),
  `_read_on()`, `_read_sensor_dict()`, `_check_divergence()`, `_snapshot_field()`, `_reapply_persist()`,
  `set_resolution()`, `set_range()`, `set_range_auto()`, `set_ir_comp_offset()`, `set_ir_comp_adjust()` — 20, as at
  HEAD after the brownout handler became `_reapply_configuration()`'s and two new ones joined. `configure()`'s rollback
  handler ends in a bare `raise` and is left as is; `_decode_rgb_burst()`'s `(TypeError, ValueError)` is not broad.
- **Resolved**: the per-entry texts above already show the call; this entry is the U30 landing list.
- **Unit**: U30
- **Depends**: A.U30.19 (`report_if_fatal()` in `asy_base_classes`)
- **Blast carried by**: the L0 handler scan and C-stack L1 → A.U30.19 (TSC, TEST_UNIT)
- **Kind**: code

### M.SRC_SENS.088 D.15 member order
- **From**: A.U10.33 (both classes reordered, AST-verified), A.U10.47 (the convention check keeps later inserts in place)
- **Site**: `src/asy_isl29125_driver.py` `ISL29125_Reader`, `ISL29125_I2C`
- **Change**: U10 reorders both classes to D.15 (last U10 change in the file); every method the later units add
  (`_green_in_window`, `_set_int_armed`, `_reapply_configuration`, `_recover_device`, `_rearm_interrupt`,
  `_write_thresholds_locked`, `_write_thresholds`, `_band_code`) is inserted at its D.15 position.
- **Resolved**: —
- **Unit**: U10
- **Depends**: —
- **Blast carried by**: A.U10.47's check (TSC)
- **Kind**: code

### M.SRC_SENS.092 Four comments state the reason, not the history
- **From**: adherence finding (CLAUDE.md "Documentation contains current state … not the historic path"; G9/R12)
- **Site**: `src/asy_isl29125_driver.py:250-252`, `:1128-1131`, `:1280-1282`, `:1337-1339`
- **Change**: `:250-252` → "# The Overrange output field for the most recent stored sample, set once per read cycle in /
  # _read_isl() and read back by _store_isl(): a transient, always-current status belongs in the / # measurement
  output, not the error log (C.7.1)." `:1128-1131` → "# The caller already holds both the device-session and bus locks,
  so this takes none of its / # own: re-acquiring the session lock here would let a concurrent reader see a mutated
  shadow / # against an unwritten chip." `:1280-1282` → "# PRST is DERIVED: the largest transient rejection whose window
  still closes inside one / # sample interval, so the chip always raises RGBTHF before the periodic re-check decides; a
  / # hand-set PRST can leave the fast path structurally dead (Part M.1.4)." `:1337-1339` → "# Validate-mutate-write
  (-rollback) runs under ONE hold of the device-session lock, not just / # the final write (Part C.8): a shadow mutated
  outside it would let a concurrent matches_shadow() / # see a change the chip has not taken - a false divergence
  report."
- **Resolved**: "It used to be wrnno=12", "is exactly the gap that let …", "Configuring it by hand left …" and "Mutating
  the shadow before acquiring it let …" narrate past states; each reason is kept in present tense, same length (agent,
  2026-10-01, OR2.c list).
- **Unit**: U15 (with the other ISL29125 comment edits)
- **Depends**: —
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` (src scope) stays green — no carrier needed
- **Kind**: doc

## Gaps for other clusters

- **GAP-1 (TSC, SPEC)**: `tests_scripts/test_src_sleep_forms.py` (A.U31.19) gains the case M.SRC_SENS.002 defines — an AST
  scan failing on any `time.sleep`/`sleep_ms`/`sleep_us` in `src/` outside the two named exceptions (SPI CS settle, the
  boot bus clear of M.SRC_SENS.008); Part N `loop.sync_wait_max_us` names that file as "Checked by" and gains the boot
  clear as a Dependant with its bound.
- **GAP-2 (TEST_UNIT)**: A.U13.R01's L1 list gains `I2C.recoveries` at `COUNTER_CAP` stepping to 0 (M.SRC_SENS.010,
  AC_NOTES 17).
- **GAP-3 (TSC)**: A.U10.47's convention check exempts `src/voc_algorithm.py` from the D.15 member order, as it already
  exempts the file's casing (M.SRC_SENS.018: a literal port keeps the upstream operation order).
- **GAP-4 (SPEC)**: Part N IDs `led.refresh_hz_default` → `led.refresh_hz`, `led.overlay_brightness_default` →
  `led.overlay_brightness` (M.SRC_SENS.021), with every Dependant row that names them.
- **GAP-5 (TEST_UNIT, HW_DEV)**: readers of the NeoPixel overlay state use the `_overlay_*` stem (M.SRC_SENS.023), not
  A.U10.35's mechanical `_led_overl_*`: `tests/test_asy_neopixel_driver.py`, the five notification/NeoPixel integration
  files, `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:74-77`, `isl29125_lighting_scenarios.py:82`.
- **GAP-6 (TEST_UNIT)**: a test pinning BMP3XX `get_altitude()`'s `sea_level_pressure <= 0` guard (if any: `grep
  sea_level_pressure tests/`) goes; the method is `get_pressure_altitude()` on `_SEA_LEVEL_PRESSURE_HPA`
  (M.SRC_SENS.040/048).
- **GAP-7 (SRC_NET, GEN)**: A.U18.15's `SOCKET_TEARDOWN` takes wrnno 12; 11 is `DERIVED_DOMAIN` (M.SRC_SENS.043, SUPP_recovery
  conflicts row 7); A.U2.01's catalog rows follow.
- **GAP-8 (SRC_CORE)**: the shared divider on `SensorReader` is `_trigger_loop()` (A.U10.44's scheme), not A.U15.40's
  `_divide_trigger()`; SPEC G.2 and the `tests/test_base_classes.py` case follow (M.SRC_SENS.045).
- **GAP-9 (SRC_CORE)**: `SensorReaderConfig` gains a `cfg_log` parameter (A.U5.02's signature) so SCD30's `ConfigManager`
  logs RAM-only while the module logger stays FRAM-backed (AC_NOTES 13, M.SRC_SENS.052).
- **GAP-10 (SPEC, DOCS, TEST_HELP)**: no `CFGMGR_SCD30` FRAM chunk — SPEC A.7 chunk layout, CLAUDE.md's FRAM-logger list
  (named exception), A.U15.12's blast "wozi 17 chunks" is stale; `tests/_sensortask_scenarios.py:222-223` expects one
  chunk (M.SRC_SENS.052).
- **GAP-11 (TSC)**: an L0 check pins SCD30's backend `always=` tuple against the fields tagged `alwaysExecuted=true`
  (`ContMeas` aside) (M.SRC_SENS.053).
- **GAP-12 (WEB)**: A.U23.16's grep found `defaultValue` only on SCD30's `ContMeas`; `asy_isl29125_driver.py:159` carries
  `defaultValue=false` on the `ISLCalibrate` (→ `Calibrate`) dispatch toggle. It goes with the grammar key
  (M.SRC_SENS.072); A.U23.16's owner decides how a dispatch toggle with no GET value renders (today "Off" through the
  default; OR94 "don't change the current look" suggests keeping Off) and its `tests_js` cases.
- **GAP-13 (SPEC, TSC)**: A.U10.16's C.8 lock table gains `ISL29125_Reader._threshold_lock` (taken inside `_set_lock`,
  before the device session; M.SRC_SENS.080), and its resolver must match A.U10.35's private session attributes
  `self._i2c_<chip>` — it is written for `self.i2c_<chip>`.
- **GAP-14 (SRC_CORE, SRC_NET, GEN)**: M.SRC_CORE.047 writes A.U11.S01's never-true `type(check_val) is not int/float`
  checks into `type_or_range_error()`, and A.U11.S01 still adds the webserver pause and generated LED-callback checks,
  against the lead's L1 answer (SUPP_coverage, 2026-09-30: "a narrowing check that can never fire is runtime code and
  dead code … the fix is at the type level"); A.U15.38 (1) stands here (M.SRC_SENS.082). The validator's typing needs
  a type-level form (e.g. an honest per-kind return) that `_checked_cfg()`'s annotated local can take.
- **GAP-15 (SRC_CORE, TEST_UNIT, TWIN, SPEC)**: after A.U10.06 a reader's `TS` is `None` until the first NTP sync, and
  `_error_check()` counts any `None` as a failed cycle — every pre-sync cycle would climb the recovery ladder and end
  the task (twin runs never sync). M.SRC_SENS.089-091 and 083 pass `condition=results[0] is None`. Carried nowhere
  else: SPEC C.7's `_error_check()` bullet ("the reader's condition excludes the trailing `TS`"); L1 per reader (a
  pre-sync read steps no streak and publishes `TS` `None`); the twin boot suites expect no sensor-task restart without
  NTP. SRC_CORE may instead make `_error_check()` test `results[0] is None` for every caller (WIFI's `(None,)` holds) —
  the reader conditions then go.
- **GAP-16 (SPEC)**: SPEC M.1.2's "State across a task restart" table (A.U15.34) gains the INT re-arm flag of A.U15.R05
  (reset at restart, M.SRC_SENS.074) beside `_int_held`.
- **GAP-17 (TSC, SRC_CORE; lead decision)**: G5/R14 (agent rank) says every class with an async `setup()` gates on
  `self.initialized`, and A.U10.22's L0 check enforces it, but no action adds the gate where it is missing. In these
  files only `SPIDevice` has one; `I2CDevice`, `BMP3XX_I2C`, `SCD30_I2C`, `SGP40_I2C`, `ISL29125_I2C`, `NeopixelDriver`
  (its `setup()` is new, A.U10.10) and `NotificationService` have none (grep `initialized` at HEAD), so the check fails
  when it lands. Two readings: (a) the protocol classes build everything in `__init__` and their `setup()` only probes
  and configures the chip, so no half-built object exists — A.U10.22 names them as exempt, as it names
  `ConfigManager.valid`; (b) each gets a gate, which needs ungated private variants of the methods `setup()` itself
  calls (`verify_device_id()`, `reset()`, `configure()`, …). Recommended (a) for the five protocol classes and
  `I2CDevice`, a gate for `NeopixelDriver`/`NotificationService` if their `setup()` builds state; no merged change here
  until the lead picks one.

## Adherence findings

- `src/asy_spi_driver.py`: comment cap → M.SRC_SENS.001 (≤ 3 lines); version stamps in code → removed, Part F owns them
  (M.SRC_SENS.001); private by default → three unread config attributes and `cs_pin` join A.U10.35's three
  (M.SRC_SENS.004); synchronous sleep rule keeps a guard → M.SRC_SENS.002/GAP-1. No other breach.
- `src/asy_i2c_driver.py`: stale docstring list (three of four I2C drivers) → M.SRC_SENS.006; LEAD/R24 counter form for
  `recoveries` → conditional wrap (M.SRC_SENS.010, AC_NOTES 17); boot clear is a bounded synchronous wait → registered
  (M.SRC_SENS.002/008). Memory: per-call `bytes` from `get_register_bytes()` is an accepted temporary (OR110.a (3)).
- `src/voc_algorithm.py`: broad handlers in a pure ALGO module → narrowed to the `struct` exceptions (M.SRC_SENS.017);
  D.15 reorder would break the literal port → no reorder, GAP-3 (M.SRC_SENS.018). Per-sample fix16 churn is the accepted
  temporary class (OR109.a (1)).
- `src/asy_neopixel_driver.py`: history in the docstring ("Promoted from improved-quality/…") → M.SRC_SENS.019; one
  name stem for overlay state (D.10) → M.SRC_SENS.023.
- `src/asy_notification_service.py`: history in the docstring and in `:84-85` ("the hand-written definitions
  established it") → M.SRC_SENS.029/032.
- `src/asy_bmp3xx_driver.py`: `sea_level_pressure` never written after A.U10.21 and its `<= 0` guard unreachable →
  named constant, guard removed (M.SRC_SENS.040, G5/R54); pre-sync `TS` counted as failure → M.SRC_SENS.089.
- `src/asy_scd30_driver.py`: docstring lists five data fields, A.U15.12 adds two → M.SRC_SENS.049; pre-sync `TS` →
  M.SRC_SENS.090. SCD30 NVM writes stay behind the wear gates: the merged changes add no NVM write (A.U15.01's range
  gate and A.U15.12's FRC state read only; `set_*` NVM paths unchanged, `persistence_write`/`scd30_extra_write` markers
  untouched).
- `src/asy_sgp40_driver.py`: "for historical" comments `:79-85` → M.SRC_SENS.060; dangling "(see module docstring)"
  `:231-232` → M.SRC_SENS.063; pre-sync `TS` → M.SRC_SENS.091.
- `src/asy_isl29125_driver.py`: four past-tense history comments → M.SRC_SENS.092; `defaultValue` left on a tag after
  the grammar drops it → M.SRC_SENS.072/GAP-12; shared-buffer staging before the hold (OR109.a (0)) → none left
  (A.U15.S01 + A.U15.33, M.SRC_SENS.080/086); no-growth memory (OR110.a) → `_filtered` reset in place, `_cal_recent`
  bounded by `_CAL_CONVERGE_N` (A.U30.02's listed case), new state is scalar; test-only parameter (OR36) → `address`
  removed; pre-sync `TS` → M.SRC_SENS.083/089.
- G5/R14 readiness gate (A.U10.22's L0 check): missing on seven classes in these files, no action adds it → GAP-17
  (lead decision; no merged change until then).
- All nine files: no `ext/` or legacy edit; no credential; no UART file (no changelog entry); no `method-assign`
  suppression; no permanent text citing an audit ID; every bus-facing change names its four tiers in the constituent
  blast; no hardware step (all L3/L4 items are the constituents' phase-C runs under the owner's go-ahead).

## Owner questions

None. Every conflict met in these files is settled by an owner row, the register, AC_NOTES, a lead note or a later
verifier item (cited in each Resolved); the remaining choices are agent-rank and listed below for the OR2.c review.

## Agent decisions for the OR2.c review

1. M.SRC_SENS.002 — a standing guard for synchronous sleeps in `src/`, two named exceptions (AC_NOTES 5, OR111.a (2)).
2. M.SRC_SENS.004 — all six `SPIDevice` configuration attributes and `cs_pin` private, not only the three tests read.
3. M.SRC_SENS.017 — `voc_algorithm.py`'s two handlers narrowed to `struct`'s exceptions instead of importing
   `report_if_fatal` into a pure ALGO module.
4. M.SRC_SENS.018 — no D.15 reorder of the literal VOC port (GAP-3).
5. M.SRC_SENS.021 — Part N IDs drop `_default` once the values are fixed (GAP-4).
6. M.SRC_SENS.023 — one `_overlay_*` stem for the NeoPixel overlay state (GAP-5).
7. M.SRC_SENS.033 — `NotificationService.setup()` returns the config store's validity; a refused signal is a warning.
8. M.SRC_SENS.040 — BMP3XX sea-level pressure becomes a named constant, its unreachable guard goes.
9. M.SRC_SENS.043 — W11 `DERIVED_DOMAIN`, W12 `SOCKET_TEARDOWN` (GAP-7).
10. M.SRC_SENS.044 — `_apply_stored_config()` returns a code; only `_init_bmp()` calls `_init_failed()`.
11. M.SRC_SENS.045/083 — the shared divider takes A.U10.44's name `_trigger_loop()` (GAP-8).
12. M.SRC_SENS.053 — SCD30's `always=` stays in the firmware, pinned to the tags by an L0 check (GAP-11).
13. M.SRC_SENS.058 — the placement of the SGP40 backup group type.
14. M.SRC_SENS.062 — SGP40 `reset` private by default.
15. M.SRC_SENS.074 — the INT re-arm flag is reset at task restart (GAP-16).
16. M.SRC_SENS.075 — INT park and re-arm are tested only on cycles with no range switch; one `_set_int_armed()` writer.
17. M.SRC_SENS.076 — the ISL29125 participant rung takes no `_set_lock` (it re-applies the shadow, not the file).
18. M.SRC_SENS.080 — a failed threshold rewrite in `set_resolution()` is logged and the setter still reports success.
19. M.SRC_SENS.086 — the `counts is None` Optional re-check stays under A.U35.41's convention.
20. M.SRC_SENS.089-091 — a pre-sync `TS` of `None` is not a failed read, through each reader's `condition` (GAP-15).
21. M.SRC_SENS.092 — four ISL29125 comments restated in present tense.

## Ledger

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.SDEP.08 | M.SRC_SENS.001, M.SRC_SENS.009 |
| A.SDEP.15 | M.SRC_SENS.030, M.SRC_SENS.042, M.SRC_SENS.070, M.SRC_SENS.073 |
| A.U0.16 | M.SRC_SENS.075, M.SRC_SENS.079 |
| A.U0.28 | M.SRC_SENS.069, M.SRC_SENS.071 (its `asy_sgp40_driver.py:670-671` part superseded by A.U15.13's text, M.SRC_SENS.069) |
| A.U0.35 | M.SRC_SENS.066, M.SRC_SENS.071 |
| A.U0.38 | M.SRC_SENS.032 |
| A.U0.39 | M.SRC_SENS.019 |
| A.U0.40 | M.SRC_SENS.062 |
| A.U0.41 | M.SRC_SENS.017, M.SRC_SENS.062, M.SRC_SENS.068 |
| A.U10.06 | M.SRC_SENS.030, M.SRC_SENS.034, M.SRC_SENS.039, M.SRC_SENS.043, M.SRC_SENS.049, M.SRC_SENS.055, M.SRC_SENS.058, M.SRC_SENS.064, M.SRC_SENS.065, M.SRC_SENS.070, M.SRC_SENS.075, M.SRC_SENS.078, M.SRC_SENS.089 |
| A.U10.10 | M.SRC_SENS.024, M.SRC_SENS.028, M.SRC_SENS.037, M.SRC_SENS.044, M.SRC_SENS.054, M.SRC_SENS.065, M.SRC_SENS.074 |
| A.U10.12 | M.SRC_SENS.046, M.SRC_SENS.055, M.SRC_SENS.066, M.SRC_SENS.083 |
| A.U10.17 | M.SRC_SENS.003, M.SRC_SENS.009, M.SRC_SENS.023 |
| A.U10.34 | M.SRC_SENS.032, M.SRC_SENS.061 |
| A.U11.31 | M.SRC_SENS.025 |
| A.U11.S01 | M.SRC_SENS.082 (its ISL29125 arm-keeping half not taken: lead L1 ruling; GAP-14) |
| A.U12.11 | M.SRC_SENS.015, M.SRC_SENS.016 |
| A.U12.13 | M.SRC_SENS.015 |
| A.U12.14 | M.SRC_SENS.017 |
| A.U12.15 | M.SRC_SENS.014 |
| A.U12.18 | M.SRC_SENS.067, M.SRC_SENS.068 |
| A.U13.02 | M.SRC_SENS.011 |
| A.U13.03 | M.SRC_SENS.004 |
| A.U13.07 | M.SRC_SENS.006, M.SRC_SENS.011, M.SRC_SENS.012, M.SRC_SENS.013, M.SRC_SENS.086 |
| A.U13.08 | M.SRC_SENS.001, M.SRC_SENS.003, M.SRC_SENS.004 |
| A.U13.09 | M.SRC_SENS.003, M.SRC_SENS.048, M.SRC_SENS.057, M.SRC_SENS.068, M.SRC_SENS.069, M.SRC_SENS.086 |
| A.U13.10 | M.SRC_SENS.011, M.SRC_SENS.013, M.SRC_SENS.048, M.SRC_SENS.086 (its BMP3XX/ISL29125 burst sites superseded by A.U30.07, M.SRC_SENS.048/086) |
| A.U13.15 | M.SRC_SENS.003 |
| A.U13.16 | M.SRC_SENS.003, M.SRC_SENS.009 |
| A.U13.R01 | M.SRC_SENS.006, M.SRC_SENS.007, M.SRC_SENS.008, M.SRC_SENS.009, M.SRC_SENS.010 |
| A.U14.17 | M.SRC_SENS.007, M.SRC_SENS.008, M.SRC_SENS.009 |
| A.U14.26 | M.SRC_SENS.034 (its `except MemoryError` at the timestamp dropped per V.U18.R10) |
| A.U15.01 | M.SRC_SENS.050, M.SRC_SENS.057 |
| A.U15.02 | M.SRC_SENS.049, M.SRC_SENS.057 |
| A.U15.03 | M.SRC_SENS.055 |
| A.U15.04 | M.SRC_SENS.054 |
| A.U15.08 | M.SRC_SENS.057 |
| A.U15.09 | M.SRC_SENS.050, M.SRC_SENS.051, M.SRC_SENS.053 |
| A.U15.10 | M.SRC_SENS.051 |
| A.U15.11 | M.SRC_SENS.051 |
| A.U15.12 | M.SRC_SENS.049, M.SRC_SENS.050, M.SRC_SENS.051, M.SRC_SENS.052, M.SRC_SENS.053, M.SRC_SENS.054, M.SRC_SENS.055, M.SRC_SENS.057 |
| A.U15.13 | M.SRC_SENS.067, M.SRC_SENS.068, M.SRC_SENS.069 |
| A.U15.14 | M.SRC_SENS.058, M.SRC_SENS.059, M.SRC_SENS.064, M.SRC_SENS.068 |
| A.U15.17 | M.SRC_SENS.059, M.SRC_SENS.060, M.SRC_SENS.062, M.SRC_SENS.063 |
| A.U15.18 | M.SRC_SENS.059, M.SRC_SENS.060, M.SRC_SENS.063 |
| A.U15.19 | M.SRC_SENS.059, M.SRC_SENS.060, M.SRC_SENS.062, M.SRC_SENS.064 |
| A.U15.21 | M.SRC_SENS.066 |
| A.U15.22 | M.SRC_SENS.043, M.SRC_SENS.072, M.SRC_SENS.073, M.SRC_SENS.074, M.SRC_SENS.075, M.SRC_SENS.078, M.SRC_SENS.079, M.SRC_SENS.083, M.SRC_SENS.084, M.SRC_SENS.089 |
| A.U15.23 | M.SRC_SENS.041 |
| A.U15.24 | M.SRC_SENS.040, M.SRC_SENS.043 |
| A.U15.25 | M.SRC_SENS.038, M.SRC_SENS.040, M.SRC_SENS.048 |
| A.U15.26 | M.SRC_SENS.039, M.SRC_SENS.045 |
| A.U15.27 | M.SRC_SENS.048, M.SRC_SENS.056 |
| A.U15.28 | M.SRC_SENS.050, M.SRC_SENS.057, M.SRC_SENS.059, M.SRC_SENS.067, M.SRC_SENS.071, M.SRC_SENS.073, M.SRC_SENS.085 |
| A.U15.29 | M.SRC_SENS.077 |
| A.U15.30 | M.SRC_SENS.071, M.SRC_SENS.082, M.SRC_SENS.086 |
| A.U15.31 | M.SRC_SENS.070, M.SRC_SENS.073, M.SRC_SENS.085 (form per AC_NOTES 17: conditional wrap at `COUNTER_CAP`, no `_SEQ_MASK`) |
| A.U15.32 | M.SRC_SENS.073, M.SRC_SENS.075, M.SRC_SENS.077, M.SRC_SENS.080 |
| A.U15.33 | M.SRC_SENS.073, M.SRC_SENS.080 |
| A.U15.34 | M.SRC_SENS.074, M.SRC_SENS.085 |
| A.U15.35 | M.SRC_SENS.071, M.SRC_SENS.079, M.SRC_SENS.081, M.SRC_SENS.086 |
| A.U15.36 | M.SRC_SENS.072, M.SRC_SENS.073, M.SRC_SENS.075, M.SRC_SENS.078, M.SRC_SENS.081, M.SRC_SENS.084 |
| A.U15.37 | M.SRC_SENS.071 |
| A.U15.38 | M.SRC_SENS.082, M.SRC_SENS.086 |
| A.U15.40 | M.SRC_SENS.039, M.SRC_SENS.041, M.SRC_SENS.042, M.SRC_SENS.045, M.SRC_SENS.048, M.SRC_SENS.049, M.SRC_SENS.050, M.SRC_SENS.057, M.SRC_SENS.058, M.SRC_SENS.059, M.SRC_SENS.067, M.SRC_SENS.068, M.SRC_SENS.070, M.SRC_SENS.072, M.SRC_SENS.083, M.SRC_SENS.085 (A.U10.38's session-class renames moot) |
| A.U15.41 | M.SRC_SENS.046, M.SRC_SENS.055, M.SRC_SENS.065, M.SRC_SENS.066, M.SRC_SENS.083 |
| A.U15.44 | M.SRC_SENS.051 |
| A.U15.R01 | M.SRC_SENS.052, M.SRC_SENS.054 |
| A.U15.R02 | M.SRC_SENS.059, M.SRC_SENS.062, M.SRC_SENS.065, M.SRC_SENS.069 (as corrected per AC_NOTES 31) |
| A.U15.R03 | M.SRC_SENS.042, M.SRC_SENS.044 |
| A.U15.R04 | M.SRC_SENS.073, M.SRC_SENS.074, M.SRC_SENS.076 |
| A.U15.R05 | M.SRC_SENS.073, M.SRC_SENS.077 |
| A.U15.S01 | M.SRC_SENS.080, M.SRC_SENS.086 |
| A.U16.18 | M.SRC_SENS.063 |
| A.U17.27 | M.SRC_SENS.021, M.SRC_SENS.023 |
| A.U2.10 | M.SRC_SENS.040, M.SRC_SENS.043, M.SRC_SENS.044, M.SRC_SENS.045, M.SRC_SENS.047, M.SRC_SENS.048 |
| A.U2.11 | M.SRC_SENS.050, M.SRC_SENS.053, M.SRC_SENS.054, M.SRC_SENS.055, M.SRC_SENS.056 |
| A.U2.12 | M.SRC_SENS.071, M.SRC_SENS.074, M.SRC_SENS.075, M.SRC_SENS.076, M.SRC_SENS.077, M.SRC_SENS.080, M.SRC_SENS.081, M.SRC_SENS.082, M.SRC_SENS.084 |
| A.U2.13 | M.SRC_SENS.059, M.SRC_SENS.063, M.SRC_SENS.064, M.SRC_SENS.065 |
| A.U2.17 | M.SRC_SENS.031, M.SRC_SENS.033, M.SRC_SENS.034, M.SRC_SENS.035 |
| A.U20.27 | M.SRC_SENS.041 |
| A.U22.01 | M.SRC_SENS.025, M.SRC_SENS.028 (part (c) merged into A.U9.05, M.SRC_SENS.028) |
| A.U22.02 | M.SRC_SENS.033, M.SRC_SENS.035 |
| A.U22.03 | dropped (WITHDRAWN, OR126.a (4): the one-second round stays; recorded in M.SRC_SENS.036) |
| A.U22.04 | M.SRC_SENS.020, M.SRC_SENS.025, M.SRC_SENS.030, M.SRC_SENS.033, M.SRC_SENS.034, M.SRC_SENS.036 |
| A.U23.16 | M.SRC_SENS.051, M.SRC_SENS.072 |
| A.U23.23 | M.SRC_SENS.051 |
| A.U24.01 | dropped here (no `src/` edit: test-side `src_const()` reads of driver constants, TEST_UNIT; named in the blasts of M.SRC_SENS.040, M.SRC_SENS.071) |
| A.U24.57 | dropped here (no `src/` edit: L0/L1 tests reading `get_dict_data()`, TSC/TEST_UNIT; `CalLight` is a flat leaf, M.SRC_SENS.072/084) |
| A.U27.03 | M.SRC_SENS.030, M.SRC_SENS.042, M.SRC_SENS.048, M.SRC_SENS.062, M.SRC_SENS.073, M.SRC_SENS.086 |
| A.U3.02 | M.SRC_SENS.037, M.SRC_SENS.062, M.SRC_SENS.063 |
| A.U3.05 | M.SRC_SENS.035, M.SRC_SENS.037, M.SRC_SENS.043, M.SRC_SENS.044, M.SRC_SENS.063, M.SRC_SENS.074 |
| A.U3.09 | M.SRC_SENS.063, M.SRC_SENS.064 |
| A.U3.14 | M.SRC_SENS.073, M.SRC_SENS.075, M.SRC_SENS.076 |
| A.U30.04 | M.SRC_SENS.067 |
| A.U30.05 | M.SRC_SENS.049, M.SRC_SENS.057 |
| A.U30.06 | M.SRC_SENS.068 |
| A.U30.07 | M.SRC_SENS.011, M.SRC_SENS.013, M.SRC_SENS.048, M.SRC_SENS.085, M.SRC_SENS.086 |
| A.U30.21 | M.SRC_SENS.009, M.SRC_SENS.011, M.SRC_SENS.012 |
| A.U31.09 | M.SRC_SENS.050, M.SRC_SENS.055, M.SRC_SENS.057 |
| A.U31.10 | M.SRC_SENS.059, M.SRC_SENS.068, M.SRC_SENS.069 |
| A.U31.11 | M.SRC_SENS.040, M.SRC_SENS.048 |
| A.U31.13 | M.SRC_SENS.023, M.SRC_SENS.027, M.SRC_SENS.028 |
| A.U31.14 | M.SRC_SENS.031, M.SRC_SENS.034, M.SRC_SENS.037 |
| A.U34.07 | M.SRC_SENS.014, M.SRC_SENS.038, M.SRC_SENS.070 |
| A.U35.11 | dropped here (test-only, `tests/test_asy_bmp3xx_driver.py`, TEST_UNIT; the product site is already one session hold, M.SRC_SENS.048) |
| A.U35.19 | dropped here (test-only, TEST_UNIT/TEST_HELP; it reads the address constants M.SRC_SENS.050/059/071 create) |
| A.U36.514 | M.SRC_SENS.051 |
| A.U4.04 | M.SRC_SENS.049, M.SRC_SENS.050, M.SRC_SENS.053 |
| A.U4.05 | M.SRC_SENS.050, M.SRC_SENS.053, M.SRC_SENS.057 |
| A.U5.06 | M.SRC_SENS.029, M.SRC_SENS.032, M.SRC_SENS.033, M.SRC_SENS.037 |
| A.U5.11 | M.SRC_SENS.030, M.SRC_SENS.033, M.SRC_SENS.035, M.SRC_SENS.058, M.SRC_SENS.060, M.SRC_SENS.062, M.SRC_SENS.064 |
| A.U5.14 | M.SRC_SENS.006, M.SRC_SENS.012, M.SRC_SENS.013 |
| A.U6.19 | M.SRC_SENS.041, M.SRC_SENS.051, M.SRC_SENS.060, M.SRC_SENS.072 |
| A.U6.20 | M.SRC_SENS.060 |
| A.U8.07 | M.SRC_SENS.040, M.SRC_SENS.050, M.SRC_SENS.055, M.SRC_SENS.059, M.SRC_SENS.068, M.SRC_SENS.069 |
| A.U8.12 | M.SRC_SENS.021, M.SRC_SENS.031, M.SRC_SENS.036, M.SRC_SENS.037 |
| A.U8.13 | M.SRC_SENS.007, M.SRC_SENS.013, M.SRC_SENS.059, M.SRC_SENS.071 |
| A.U8.19 | M.SRC_SENS.002 |
| A.U9.01 | M.SRC_SENS.032, M.SRC_SENS.037 |
| A.U9.02 | M.SRC_SENS.019, M.SRC_SENS.023, M.SRC_SENS.025, M.SRC_SENS.026 |
| A.U9.04 | M.SRC_SENS.020, M.SRC_SENS.021, M.SRC_SENS.023, M.SRC_SENS.027 |
| A.U9.05 | M.SRC_SENS.028 |
| A.U9.06 | M.SRC_SENS.021, M.SRC_SENS.022, M.SRC_SENS.026, M.SRC_SENS.027, M.SRC_SENS.028 |
| A.U9.07 | dropped (superseded by A.U17.27, its own Depends; recorded in M.SRC_SENS.021) |
| A.U9.08 | M.SRC_SENS.031, M.SRC_SENS.035 |
| A.U9.09 | M.SRC_SENS.030, M.SRC_SENS.033, M.SRC_SENS.036 |
| A.U9.11 | M.SRC_SENS.032 |

Actions outside `site_index.json` whose text edits a site here (found by the identifier grep), merged:

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.SDEP.17 | M.SRC_SENS.001, M.SRC_SENS.009 |
| A.U10.18 | M.SRC_SENS.003, M.SRC_SENS.004, M.SRC_SENS.009, M.SRC_SENS.013, M.SRC_SENS.023 |
| A.U10.21 | M.SRC_SENS.004, M.SRC_SENS.013, M.SRC_SENS.024, M.SRC_SENS.040, M.SRC_SENS.044, M.SRC_SENS.048, M.SRC_SENS.057, M.SRC_SENS.069, M.SRC_SENS.074, M.SRC_SENS.086 |
| A.U10.25 | M.SRC_SENS.042, M.SRC_SENS.062, M.SRC_SENS.073 |
| A.U10.31 | M.SRC_SENS.004, M.SRC_SENS.011, M.SRC_SENS.022, M.SRC_SENS.025, M.SRC_SENS.048, M.SRC_SENS.057, M.SRC_SENS.070 |
| A.U10.33 | M.SRC_SENS.004, M.SRC_SENS.009, M.SRC_SENS.013, M.SRC_SENS.018, M.SRC_SENS.088 |
| A.U10.35 | M.SRC_SENS.004, M.SRC_SENS.023, M.SRC_SENS.033, M.SRC_SENS.042, M.SRC_SENS.048, M.SRC_SENS.052, M.SRC_SENS.057, M.SRC_SENS.062, M.SRC_SENS.067, M.SRC_SENS.073, M.SRC_SENS.085, M.SRC_SENS.086 |
| A.U10.37 | M.SRC_SENS.005, M.SRC_SENS.007, M.SRC_SENS.020, M.SRC_SENS.030, M.SRC_SENS.039, M.SRC_SENS.049, M.SRC_SENS.058, M.SRC_SENS.070 |
| A.U10.38 | M.SRC_SENS.020, M.SRC_SENS.021, M.SRC_SENS.030, M.SRC_SENS.031, M.SRC_SENS.033, M.SRC_SENS.038, M.SRC_SENS.041, M.SRC_SENS.042, M.SRC_SENS.048, M.SRC_SENS.051, M.SRC_SENS.052, M.SRC_SENS.058, M.SRC_SENS.060, M.SRC_SENS.070, M.SRC_SENS.072, M.SRC_SENS.085 |
| A.U10.39 | M.SRC_SENS.032, M.SRC_SENS.033, M.SRC_SENS.041, M.SRC_SENS.042, M.SRC_SENS.051, M.SRC_SENS.060, M.SRC_SENS.066, M.SRC_SENS.072, M.SRC_SENS.073, M.SRC_SENS.074, M.SRC_SENS.082, M.SRC_SENS.084 |
| A.U10.40 | M.SRC_SENS.032, M.SRC_SENS.041, M.SRC_SENS.051, M.SRC_SENS.060, M.SRC_SENS.066, M.SRC_SENS.072, M.SRC_SENS.073, M.SRC_SENS.084 |
| A.U10.43 | M.SRC_SENS.034, M.SRC_SENS.040, M.SRC_SENS.041, M.SRC_SENS.042, M.SRC_SENS.045, M.SRC_SENS.051, M.SRC_SENS.052, M.SRC_SENS.055, M.SRC_SENS.071, M.SRC_SENS.072, M.SRC_SENS.073, M.SRC_SENS.074, M.SRC_SENS.082, M.SRC_SENS.083, M.SRC_SENS.084, M.SRC_SENS.086 |
| A.U10.44 | M.SRC_SENS.025, M.SRC_SENS.028, M.SRC_SENS.036, M.SRC_SENS.037, M.SRC_SENS.045, M.SRC_SENS.046, M.SRC_SENS.055, M.SRC_SENS.066, M.SRC_SENS.083 |
| A.U10.45 | M.SRC_SENS.003, M.SRC_SENS.011, M.SRC_SENS.013, M.SRC_SENS.048, M.SRC_SENS.057, M.SRC_SENS.068, M.SRC_SENS.069, M.SRC_SENS.086 |
| A.U10.46 | M.SRC_SENS.070, M.SRC_SENS.083, M.SRC_SENS.084 |
| A.U10.47 | M.SRC_SENS.088 |
| A.U10.R01 | M.SRC_SENS.089 |
| A.U11.09 | M.SRC_SENS.017 |
| A.U11.27 | M.SRC_SENS.044 |
| A.U11.S02 | M.SRC_SENS.053 |
| A.U12.08 | M.SRC_SENS.039, M.SRC_SENS.043 |
| A.U14.04 | M.SRC_SENS.009 |
| A.U15.15 | M.SRC_SENS.069 |
| A.U15.16 | M.SRC_SENS.060 |
| A.U15.43 | M.SRC_SENS.039, M.SRC_SENS.046, M.SRC_SENS.047, M.SRC_SENS.049, M.SRC_SENS.055, M.SRC_SENS.056, M.SRC_SENS.058, M.SRC_SENS.066, M.SRC_SENS.070, M.SRC_SENS.083, M.SRC_SENS.084 |
| A.U19.16 | M.SRC_SENS.053, M.SRC_SENS.084 |
| A.U2.01 | M.SRC_SENS.071 |
| A.U2.04 | M.SRC_SENS.031, M.SRC_SENS.040, M.SRC_SENS.050, M.SRC_SENS.059, M.SRC_SENS.071 |
| A.U20.25 | M.SRC_SENS.032 |
| A.U23.37 | M.SRC_SENS.033, M.SRC_SENS.035 |
| A.U24.23 | M.SRC_SENS.003 |
| A.U24.62 | M.SRC_SENS.022 |
| A.U28.35 | M.SRC_SENS.038 |
| A.U3.03 | M.SRC_SENS.089 |
| A.U30.02 | M.SRC_SENS.081 |
| A.U30.03 | M.SRC_SENS.081 |
| A.U30.19 | M.SRC_SENS.017, M.SRC_SENS.034, M.SRC_SENS.035, M.SRC_SENS.039, M.SRC_SENS.043, M.SRC_SENS.044, M.SRC_SENS.047, M.SRC_SENS.049, M.SRC_SENS.054, M.SRC_SENS.055, M.SRC_SENS.056, M.SRC_SENS.058, M.SRC_SENS.062, M.SRC_SENS.064, M.SRC_SENS.065, M.SRC_SENS.070, M.SRC_SENS.074, M.SRC_SENS.075, M.SRC_SENS.076, M.SRC_SENS.077, M.SRC_SENS.081, M.SRC_SENS.082, M.SRC_SENS.084, M.SRC_SENS.087 |
| A.U31.12 | M.SRC_SENS.007, M.SRC_SENS.013 |
| A.U34.04 | M.SRC_SENS.014 |
| A.U36.542 | M.SRC_SENS.014 |
| A.U36.544 | M.SRC_SENS.032, M.SRC_SENS.071 |
| A.U4.03 | M.SRC_SENS.052 |
| A.U5.01 | M.SRC_SENS.020, M.SRC_SENS.030, M.SRC_SENS.039, M.SRC_SENS.058, M.SRC_SENS.070 |
| A.U5.02 | M.SRC_SENS.020, M.SRC_SENS.023, M.SRC_SENS.030, M.SRC_SENS.033, M.SRC_SENS.039, M.SRC_SENS.042, M.SRC_SENS.049, M.SRC_SENS.052, M.SRC_SENS.070, M.SRC_SENS.073 |
| A.U5.03 | M.SRC_SENS.021, M.SRC_SENS.031, M.SRC_SENS.041, M.SRC_SENS.051, M.SRC_SENS.060, M.SRC_SENS.072 |
| A.U6.17 | M.SRC_SENS.051 |

The other 143 grep hits name these files only in Why/Blast text or as an unchanged caller and edit no site here (read, no row needed beyond this list): A.C.15, A.S0930.13, A.S0930.17, A.S0930.32, A.SDEP.10, A.SDEP.16, A.U0.07, A.U1.03, A.U1.20, A.U1.25, A.U10.01, A.U10.05, A.U10.16, A.U10.22, A.U10.27, A.U10.28, A.U10.30, A.U11.14, A.U11.24, A.U11.34, A.U11.S03, A.U12.01, A.U12.04, A.U12.06, A.U12.07, A.U12.12, A.U13.01, A.U13.11, A.U14.06, A.U14.10, A.U14.14, A.U14.28, A.U14.34, A.U14.35, A.U15.05, A.U15.07, A.U15.20, A.U16.02, A.U16.05, A.U16.06, A.U16.17, A.U16.19, A.U16.20, A.U16.22, A.U16.S01, A.U19.12, A.U2.06, A.U2.07, A.U2.09, A.U20.06, A.U20.08, A.U20.12, A.U20.20, A.U20.21, A.U20.26, A.U20.28, A.U24.02, A.U24.07, A.U24.08, A.U24.16, A.U24.20, A.U24.21, A.U24.25, A.U24.29, A.U24.32, A.U24.37, A.U24.38, A.U24.39, A.U24.42, A.U24.49, A.U24.59, A.U24.61, A.U24.67, A.U24.73, A.U24.76, A.U24.78, A.U25.05, A.U25.07, A.U25.10, A.U25.12, A.U25.13, A.U25.16, A.U25.17, A.U25.21, A.U25.36, A.U25.45, A.U25.49, A.U26.06, A.U26.07, A.U26.32, A.U26.41, A.U26.44, A.U27.30, A.U28.27, A.U28.28, A.U28.30, A.U3.01, A.U3.04, A.U3.12, A.U31.01, A.U31.05, A.U32.01, A.U32.04, A.U32.05, A.U34.03, A.U34.10, A.U35.12, A.U35.13, A.U35.16, A.U35.17, A.U35.18, A.U35.20, A.U35.41, A.U35.44, A.U35.55, A.U36.022, A.U36.506, A.U36.520, A.U36.537, A.U36.546, A.U4.02, A.U4.06, A.U4.07, A.U5.17, A.U5.18, A.U7.25, A.U8C.05, A.U8C.09, A.U8C.10, A.U8C.11, A.U8C.12, A.U8C.120, A.U8C.14, A.U8C.15, A.U8C.16, A.U8C.18, A.U8C.35, A.U8C.36, A.U8C.37, A.U8C.38, A.U8C.39, A.U8C2.02, A.U9.10.
