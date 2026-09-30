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
  — they do: M.SRC_SENS.03x driver sites call `get_register_bytes()` and test the bool; stage U13 = A.U13.07 + A.U13.10 +
  A.U10.45 + A.U10.31, stage U30 = A.U30.07 + A.U30.21)
- **Depends**: M.SRC_SENS.009 (the view)
- **Blast carried by**: driver call sites → M.SRC_SENS.034 (BMP3XX), M.SRC_SENS.069/070 (ISL29125); tests
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
  asserts (`"No I2C device"`) → A.U10.45 (TEST_UNIT, HW_DEV grep); driver callers → M.SRC_SENS.03x-07x
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
  `self._read_event`, `results = await self._read_bmp()`, `if not await self._error_check(results): return`, `await
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

