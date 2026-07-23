# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

## Refactor targets not yet done

- **Bare `except:` is forbidden in refactored code** (`except Exception:` or narrower required).
  Ruff's E722 is already enabled, so existing bare excepts in `improved-quality/` show as tracked
  findings rather than being silenced — eliminating them is still real refactor work.
- **No CI firmware-build stage yet.** Blocked on genericizing `build-*.sh`'s hardcoded
  `/home/nico/rpi_pico/...` path and the `py-include` symlink (see "Deferred" below) — needs to
  land before/alongside this.
- **Mypy shall be configured to disallow `Any` types** (owner-specified, not yet implemented). The
  closest existing option is `disallow_any_explicit`; `pyproject.toml` deliberately stops short of
  it and the other `--strict`-only checks today. Blast-radius check done: `Any` appears ~29 times
  across `src/`/`tests/`, almost entirely in test-file monkeypatch/wrapper classes duck-typing a
  real MicroPython object rather than reimplementing its interface — turning this on will need a
  real typing strategy for those wrappers (e.g. `Protocol` classes matching just the overridden
  methods, plus `__getattr__` delegation) worked out first, not just a flag flip.
- **Per-driver REST config setters are a known gap, deliberately not closed sensor-by-sensor.**
  `get_dict_cfg()` gives every `*_Reader` a generic, schema-driven way to *read back* its config;
  there's no equivalent generic *write* path — each REST handler still calls `set_*` methods one
  field at a time by hand, and several config values accepted by a REST handler (SGP40's
  `BackupPeriod`/`BackupMaxAge`/`WaitTimeNTP`) have no setter on the driver at all, so the write is
  a silent no-op against real hardware. Deferred on purpose until all three sensors (SCD30/SGP40/
  BMP3xx) were promoted to `src/` — **that's now done** — so a single consolidated generic-setter
  mechanism can be designed once across all of them (applies to `config_manager.py`'s own
  `ConfigManager` too: typed getters exist, no matching typed setters, only untyped
  `write_config(dict, schema)`).
- **FRAM bus-recovery is only partially wired up.** `asy_fram_driver.py`'s own `src/` promotion
  added device-identification/write-protect verification, but there's still no periodic/triggered
  re-probe policy (`verify_present()` has zero callers anywhere) and no task supervisor for FRAM
  specifically — `asy_fram_manager.py`'s own promotion didn't add this wiring (out of scope for a
  quality audit).
- **No standardized timeout/cancellation mechanism yet for blocking calls that genuinely can be
  timeout-wrapped** (`socket.getaddrinfo()`, FRAM SPI transactions — anything that isn't a raw
  blocking `machine.I2C` call mid-transaction, which can't be interrupted regardless; see CLAUDE.md
  for why that case is different and already decided). Each such call currently uses its own
  bespoke approach rather than one consistent mechanism applied everywhere.
- **Bus concurrency (`asyncio.Lock` + `async with`) needs a coverage audit** — no gaps, no
  deadlock/starvation. The `*_DeviceSession(Lockable)` pattern (an outer per-sensor lock around a
  whole write-then-read transaction, `asyncio.sleep(0)` yield between phases) is the pattern to
  verify/extend, not start from scratch. (The one concrete gap this audit had already turned up —
  SCD30's low-level getter/setter forwards not logging via `self.pr.err_s()`, unlike BMP3xx's — is
  now fixed; see DRIVER_SPEC.md section 7 for the settled forward-logging convention every driver
  now follows. The broader "no gaps, no deadlock/starvation" audit itself is still open.)
- **Common driver error classes across sensors — future direction, not designed or implemented
  yet.** Each driver currently defines and reports its own `errno`/`wrnno` values independently
  (see DRIVER_SPEC.md section 7); the one exception is `errno=10` ("initial setup failed"), which
  all three drivers already use for the same situation by independent convergence rather than by
  any enforced scheme. Project owner's stated direction: keep per-driver definition/reporting (not
  a single shared enum), but predefine a small set of common error *classes* so the same number
  means the same or an equivalent condition across different drivers, beyond just the one
  already-consistent case. No scheme (numbering ranges, category list, how a driver opts in)
  designed yet — out of scope until config setters (above) are done.
- **Network/WiFi and Neopixel config still share one ad hoc top-level `ConfigManager`** in
  `sensortask-wozi.py` (confirmed intentional intermediate state, not finished) — every sensor now
  has its own per-device `SensorReaderConfig`-based config file; this cross-cutting config still
  needs its own clearly-scoped global home instead of an implicit grab-bag.
- **Neopixel warning-flash sequencing and the task-supervisor error-budget counter** are both
  behaviorally correct and intentional as designed, but flagged by the owner as implementable more
  efficiently — worth a cleaner implementation in the refactor without changing observed behavior.
- **`sensortask-wozi.py`'s own task-supervisor loop in `main()`** still never calls the real
  `start_and_check_tasks()`/`get_task_starters()` `system_service.py` now provides — it hand-rolls
  its own loop instead. Same file's `sysfunct.start_timers(timer_starters, 1000)` call also passes
  a second positional argument `start_timers()` has never accepted. Pre-existing, not touched by
  any driver promotion so far.
- **`improved-quality/microdot.py` is a confirmed *unintentional* fork of vendored Microdot**
  (owner-confirmed). Action when refactor work resumes: revert it to match upstream exactly, no
  behavioral additions ever. Not touched now (`improved-quality/` source stays out of routine
  editing) — distinct from `python/CommonDrivers/microdot.py`, which still matches upstream.
- **Rough sequencing, not a committed plan**: (1) dev/build environment setup (genericized
  `build-*.sh`/toolchain paths) — everything else touching CI/firmware depends on this; (2) the
  structural patterns above (per-sensor config, generalized error-counter bookkeeping) are largely
  done; (3) bus/sensor error-recovery robustness items above, which build on that structure; (4)
  remaining tooling/CI (the firmware-build stage) — mypy/ruff/stubs/Unix-port-tests were pulled
  forward out of this order already, once `math_helpers.py` cleared the `src/` bar, and that's now
  standing practice for every new file, not a one-off.

## Open questions (need owner input or further investigation)

1. `modules/_boot.py`'s `import sensortask.py` (literal `.py`) — works reliably on real hardware,
   but MicroPython's documented freeze/import behavior says it should raise `ModuleNotFoundError`.
   Mechanism genuinely unresolved. **Do not "fix" without testing on real hardware first.**
   Addressed during the refactor, not before.
2. Config-schema migration is a real data-loss risk on the *current deployed* codebase —
   `ConfigManager` overwrites the entire config file with hardcoded defaults the moment one key is
   missing, so a firmware update adding a config key could silently wipe WiFi credentials/tuned
   values. **Decided: not patched on the current codebase** — accepted (reconfigure via web UI
   after a key-adding update). The refactor's per-sensor config model avoids this failure mode
   structurally, not by patching the current global-JSON codebase.
3. MicroPython version target vs. upstream drift — deployed units run 1.26; upstream stable is
   1.28.0 as of the last check. **Decided**: deployed code stays pinned to 1.26 until a deliberate
   reflash campaign; the refactor is where the version target moves forward. 1.27→1.28 rp2-port
   changes checked so far look RP2350-specific, not RP2040-breaking, but not exhaustively checked
   against every module — re-check whenever the refactor picks a landing version.
4. SCD30 `ForceCalRef` field procedure isn't written down anywhere — a real maintenance routine
   exists (confirmed by owner) but the actual steps (reference concentration, exposure
   conditions/timing, frequency) still need capturing from the owner.
5. Does `config_manager.py`'s `write_config()` need `get_long_block_lock()` coordination? Its
   `open()`+`json.dump()` has no yield point, the same shape `__init__`'s read path had before the
   cache-elimination redesign closed *that* concern. Whether a real RP2040 littlefs write of a
   small config file is fast enough not to matter is a hardware-timing question this dev
   environment can't verify — needs either a real-hardware measurement or an owner call on wiring
   it in proactively.
6. `get_ambient_pressure()`'s read-back (SCD30) reuses the same command word used to *set* it —
   matches every sibling getter's pattern and the legacy driver, but neither Sensirion's own
   `embedded-scd` reference driver nor their `python-i2c-scd30` driver treats that command as
   readable (their own worked examples/command classes only show a write path for it). Not proven
   broken — legacy behavior, uneventful field use — but never confirmed against an authoritative
   source either. **Resolved by owner: leave as-is**, no alternate documented read-back exists to
   switch to regardless; recorded so it isn't re-investigated from scratch.
7. Real-hardware verification gap for `asy_udp_socket.py`/`captive_dns.py`: every UDP-layer claim
   (POLLERR/POLLHUP delivery, truncation, connected-socket source filtering) is verified against the
   MicroPython Unix port's socket implementation, not real rp2/lwIP — no rp2 hardware was available
   to test against. If a deployed unit ever shows UDP behavior diverging from what's
   tested/documented in the driver, this is the first place to look. Considered closing via a
   standalone on-device verification script — judged too hypothetical to chase for now.
8. BMP390's own datasheet isn't in `datasheets/bmp3xx/` (only BMP384/BMP388 are) — its `0x60` chip
   ID and assumed-identical register map/IIR table couldn't be verified against a real BMP390
   datasheet. Needs the owner to add the datasheet to close this.

## Deferred / explicitly out-of-scope work

- **HTML/frontend automation & consistency** — known hand-written/brittle, not a priority; revisit
  after the Python-side refactor.
- **UART sensor integration** (`asy_uart.py`/`asy_uart_comm.py`, unused by any deployed config) —
  after the refactor of already-deployed features, not before.
- **Config-duplication centralization** — same keys hand-kept in sync across `_DEFAULT_CONFIG`, the
  REST handler, and the HTML form. Owned by the refactor: each promoted `*_Reader`'s own `_VAL_*`
  schema tuple + `get_dict_cfg()`/`get_dict_data()` is the intended single source, not fully wired
  end-to-end yet (`sensortask-wozi.py` itself predates the per-sensor-config model — see "Refactor
  targets not yet done" above).
- **`dev` config quirks** (e.g. LED/Neopixel REST routes referencing an uninstantiated object) —
  bench rig only, not bugs to fix.
- **Dev/build environment setup**: toolchain installer is done (`toolchain/setup_toolchain.py`, see
  `toolchain/README.md`/README.md's "Toolchain setup"). **Still not done**: doesn't yet genericize
  `build-*.sh`'s hardcoded `/home/nico/rpi_pico/...` path or the `py-include` symlink — the next
  step, and now a real near-term prerequisite for the firmware-build CI stage.
  `update_and_install.txt` re-verified against current upstream docs — structurally still accurate,
  but missing the pico-sdk 2.0.0+ picotool major.minor version-matching requirement (already applies
  today) and the full apt package list. An official one-shot alternative exists
  ([`raspberrypi/pico-setup`](https://github.com/raspberrypi/pico-setup)'s `pico_setup.sh`), worth
  considering as a base.
- **No end-user reference for Neopixel LED colors/patterns exists** — confirmed intentional
  single-LED dual-duty design, but no legend anywhere. Worth adding, low priority.
- **FRAM SGP40 "0 = disabled" backup/staleness semantics need user-facing documentation** — the
  behavior itself is intentional (see CLAUDE.md), just undocumented for whoever configures a unit.

## `src/` promotion findings

File-by-file review comparing `improved-quality/` against legacy equivalents (or reading cold where
there's no legacy equivalent), against `src/README.md`'s checklist. Real bugs, decisions, and
deferred items below — process narrative (review-pass counts, "verified lint/typecheck/tests clean"
after every change) is omitted; assume every change below was lint/type/test-clean before landing.
Current total: 976 tests across 16 `tests/test_*.py` files (verify via
`grep -c '^def test_' tests/test_*.py` if this looks stale).

### `math_helpers.py`

First file promoted. `wet_bulb_temperature`'s humidity lower bound was `0.5%`; Stull (2011) only
validates down to `5%` — real bug, fixed. `altitude_baro`'s 300–1250 hPa / -40–85°C range comes
from the BMP388/390 datasheet (its only caller), not the barometric formula itself. 45 tests.

### `crc_checks.py`

Correctness verified against Sensirion's own datasheet test vectors, CRC-16/CCITT-FALSE, and
CRC-32/MPEG-2 standards. Exception handling narrowed to `ValueError` specifically. Missing
negative-value/length guards added. A table-driven (256-entry LUT) implementation was considered as
a speed optimization and declined — real usage here is small buffers (2–3 byte sensor CRC8, modest
FRAM chunks), not worth the ~1KB RAM cost; revisit if a future caller pushes larger buffers through.
66 tests.

### `asy_i2c_driver.py`

First hardware-touching file promoted — established the "raw bus-transaction calls may propagate
`OSError` uncaught" carve-out (`src/README.md` section 2): a real transaction failure is allowed to
propagate out of the low-level bus driver rather than being swallowed, matching every Reader's
pattern of wrapping a whole read/write sequence in its own `try/except`.

Real bugs found and fixed: `I2C.deinit()` never called the real `machine.I2C.deinit()` (only dropped
the Python reference) — fixed to match `asy_spi_driver.py`'s already-correct pattern. `set_bits()`
took a separate `endian` param independent of its own `lsb_first`, and `set_register_struct()` took
one instead of deriving byte order from `reg_format`'s own prefix — both could silently disagree
with the read-side byte order for a multi-byte register (no current caller had `reg_width>1` to
trigger it); dropped the separate param from both. `set_bits()` shifted `value` into the register
without masking to `num_bits` width first — a wide `value` could corrupt bits above the field; fixed
via a shared `_bitmask()` helper. `writeto_then_readfrom()`/`write_then_readinto()` had one shared
`stop` param for both legs, unable to express the standard repeated-start register-read pattern
(write without stop, read with stop) — split into independent `out_stop`/`in_stop`, defaults
unchanged. `get_register_struct("")` (or any zero-data-field format) raised an uncaught `IndexError`
indexing `struct.unpack()`'s empty result — fixed by checking non-empty before indexing.
`set_register_struct()`'s `value` was `int`-only but `get_register_struct()` returns
`int | float | bytes` — `struct.pack()` raises `TypeError` for a mismatch, previously uncaught;
widened `value` to `int | float | bytes | bytearray`, catch `TypeError` too. `writeto()`'s
`str`-buffer path raised an uncaught `ValueError` for any Unicode codepoint above 255; now caught,
returns `None`.

Other changes: `get_bits()`/`set_bits()` gained a range guard (previously unguarded). `scan()`/
`writeto()` widened to return `None` instead of magic defaults (`[]`/`0`) when the bus isn't
initialized, matching the project's "`None` = no data" convention — `I2CDevice` and the sensor
drivers don't check these yet (flagged, no current caller relies on the old defaults either). Byte-
order/range-guard logic extracted into shared `_bytes_to_int()`/`_bitfield_range_ok()`/`_bitmask()`
helpers. Confirmed real RP2040 I2C error codes for `tests/machine.py`'s fault injection: hardware I2C
only raises `OSError(EIO)` (NAK/bus fault) or `OSError(ETIMEDOUT)` (bus-busy/clock-stretch) — never
`ENODEV`, which is `SoftI2C`-specific. Documented (not fixed): MicroPython's `struct.pack` silently
zero-pads/truncates on a value/argument-count mismatch instead of raising, unlike CPython.

Deferred, flagged not fixed: `get_bits`/`set_bits`/`get_register_struct` still call the allocating
`readfrom_mem()` rather than zero-copy `readfrom_mem_into()` — no real callers yet besides the
not-yet-migrated `asy_isl29125_driver.py`; worth doing before that migration.

77 tests.

### `asy_spi_driver.py`

SPI's fault surface is materially different from I2C's, confirmed against MicroPython source
(`extmod/machine_spi.c`, `ports/rp2/machine_spi.c`): real hardware SPI `write()`/`readinto()` have
**no error return at all** — cannot raise, full stop, not merely "in practice, let it propagate" the
way I2C's carve-out works. `write_readinto()` is the one exception (`ValueError` for mismatched
buffer lengths — a caller-input mistake, caught and turned into `None`).

Real bugs found and fixed: **`SPIDevice.__aenter__` leaked the bus lock and left the CS pin stuck
asserted permanently** whenever it raised *after* acquiring the lock (`configure()` raising on a
deinitialized bus, or task cancellation during the post-assert settle sleep) — since `__aenter__`
itself raises, `async with` never calls `__aexit__`. Present in the original hand-rolled file too. A
stuck-asserted CS blocks every other device sharing the bus. Fixed: wrapped the post-lock-acquire
steps in `try/except BaseException` that deasserts CS and releases the lock before re-raising.
`SPIDevice.__aenter__` had no guard against being reached before `setup()` ran — `Pin.value(x)` calls
`gpio_put()` unconditionally regardless of direction, so entering before `setup()` wouldn't raise, it
would silently fail to ever assert CS on real hardware. Fixed with an `uninitialized` flag checked at
entry. The original file was literally unimportable on the real interpreter (`ImportError: no module
named 'typing'`) — resolved with zero typing-only imports needed.

Other changes: `write()`/`readinto()` narrowed from `int | None` to plain `None` (confirmed via
source they always return `None` on this port). `SPIDevice` converted to subclass `Lockable`,
matching `I2CDevice`. `configure()`'s `RuntimeError`-on-unlocked-call kept as a programmer-error
guard (not converted to `None`) since `asy_fram_driver.py`'s `FRAM_SPI` is a live caller.
`tests/machine.py` extended with `class SPI` + real `Pin.init()`/`.value()` readback.

43 tests. Baseline check: full-scope lint findings dropped by exactly this file's own 3 pre-existing
findings, no regression elsewhere.

### `base_classes.py` + `config_manager.py` + `print_log.py`

Promoted together — `base_classes.py`'s `SensorReader`/`SensorReaderConfig` depend on both.

**Real bugs found in `config_manager.py`** (pre-existed in `base_classes_old.py`, never exercised
end-to-end before): `cfg_from_str()`/`str_cfg()`'s `cfg_vals[1:-2]` (should be `[1:-1]`) stripped one
character too many off the `"|...|"`-wrapped schema string — always dropped the final `}`, so
`json.loads()` always raised and `cfg_from_str()` always returned `{}`; since `ConfigManager.__init__`
bails when that's empty, **`ConfigManager.valid` could never become `True` for any real caller** —
every `SensorReaderConfig`-based sensor's persistent config storage was silently, completely
non-functional. Fixed. `check_cfg_get_default()`'s self-check of a schema's `"special"` sentinel
called `type_or_range_error(..., check_special=use_value)` with `use_value=False` in exactly the case
being checked — forced the special value through the full min/max range check instead of its own
bypass, judging real, already-in-use schema constants (e.g. `AmbPres`) as invalid. Masked by the bug
above (never actually reached). Fixed: always pass `check_special=True` to this self-check.
`get_bool_values()`'s conversion-failure detection was silently broken — `bool(v)` never raises for
any input, so a corrupted/wrong-typed on-disk bool value silently coerced instead of signaling
invalid; fixed with an explicit `isinstance(v, bool)` guard. `write_config()`'s special-only-key
branch never called `type_or_range_error` on the submitted value at all — confirmed with owner ("the
sentinel value shall always be valid if it matches its definition") — fixed: moved the call before
the `not use_value` branch so it always runs.

**`print_log.py` bugs found and fixed**: `PrintLogHistoryStore._write()`/`_read()`'s `try:` block
started too late — `get_buffer()`/`get_data_buf()`/`read_into()` were called before the `try:` began,
breaking the "never raises" contract; widened both `try` blocks to cover their entire bodies.
`_store_err()`/`reset()`'s "not initialized" guard's `return` was conditioned on `self.level`, not
just `self.initialized` — with logging **off** (production default), calling `err_s()`/`wrn_s()`/
`reset()` before `setup()` loaded persisted state silently overwrote real FRAM-persisted history with
a fresh default, backwards from the guard's intent. Fixed. `PrintLogHistory.__init__` didn't clamp
`history_length` — a negative value reaches `deque([_NO_ERR] * history_length, history_length)`,
which raises on real MicroPython; clamped to `≥0`.

**Real bugs in `base_classes.py`**: `LockableBuffer.__init__` only guarded `data_end > size` — a
negative `size`/`data_start`/`data_length` wasn't checked (`bytearray(-1)` raises `MemoryError` on
MicroPython, wrapping to a huge unsigned allocation); guarded all three the same way. Later widened:
an astronomically large but non-negative `size` can still raise `MemoryError`/`OverflowError` — a
real risk since `asy_fram_manager.py` allocates a fresh `LockableBuffer` on every FRAM read/write over
an indefinite uptime; wrapped in `try/except (MemoryError, OverflowError)`. `SensorReader.
reset_error_counter()` only reset `self.pr`'s persisted history, not `self._err_cnt_internal` (the
separate consecutive-failure streak) — now resets both.

**Schema representation replaced**: pipe-delimited-JSON-string `const()` → `const()`-wrapped-tuple
`const()`. The old encoding existed only to get `const()`'s RAM-zero-cost property back when
`const()` couldn't fold anything but ints; MicroPython 1.26.0 added float/tuple folding, so a plain
tuple gets the same zero-cost property with no string parsing. New shape: each field a plain
positional 6-tuple `(name, type, def, min, max, special)`, concatenated with `+`.

**Blocking-I/O redesign, owner-directed**: `get_dict`/`_get_values`/`write_config`'s synchronous file
I/O blocked the event loop with no yield point inside `async def` methods, and wasn't purely a
one-time boot cost (`asy_bmp3xx_driver.py`'s `read_loop()` calls a config getter every `SampleInterv`
cycle). Redesigned: read the config file once at `__init__`, cache it, serve all reads from cache;
`write_config` builds changes into a working copy and only assigns `self._cache` after the file write
actually succeeds. **Deliberate consequence**: reads no longer detect the config file being
deleted/corrupted out-of-band after a valid `__init__` — `_cache` is now the sole source of truth,
and a later `write_config` silently *repairs* an externally-corrupted file from `_cache`. Accepted
given this device is the file's only writer.

70 tests (`base_classes.py`), 140 (`config_manager.py`), 46 (`print_log.py`).

### `asy_fram_driver.py`

Driver for the FRAM chip (Fujitsu MB85RS64V, Adafruit's 8KB SPI FRAM breakout), under
`asy_fram_manager.py`. Verified against the real datasheet (DS501-00015) and Adafruit's own
`Adafruit_FRAM_SPI` reference driver.

`setup()`'s RDID check validates manufacturer ID/continuation code/product ID against real hardware
— any mismatch raises `OSError`. `_write()` confirms the write-enable latch actually set via `RDSR`
after `WREN` before issuing `WRITE`, and re-verifies after `WRDI`, retrying once before only warning
on a stuck `WEL`. `set_write_protected()` does the same around `WRSR`. `WP` pin is active-low;
`set_write_protected()` deasserts `WP` before every `WRSR` and only restores the target level after
readback-confirmed success, so a leftover-low `WP` can never self-lock a later unprotect call.
`WPEN`/`BP0`/`BP1` are nonvolatile — `setup()` re-syncs `_wp` from a real `RDSR` rather than trusting
the constructor's `wp=` placeholder. `verify_present()` (a cheap re-probe for a future health-check/
retry policy) bounds its own lock-wait with a 1.0s timeout, degrading to `False` rather than hanging.
Exception contract: exactly three deliberate raise paths (`__init__`'s bad-pin `ValueError`,
`setup()`'s identification `OSError`, `SPIDevice.__aenter__`'s caller-ordering `RuntimeError`) —
everything else returns `False`/`None`.

**Known gaps, kept for future use (owner-confirmed)**: `get_write_protected()`/
`set_write_protected()`/`verify_present()` have zero callers in `asy_fram_manager.py` today —
whoever wires up FRAM's own bus-recovery/re-probe policy (see "Refactor targets not yet done") must
wrap them in the same `try/except Exception` discipline this file's other methods already use, since
this driver doesn't catch its own inherited `RuntimeError` path itself. `get_size()` has zero callers
anywhere (kept as plausible future capacity getter).

46 tests.

### `asy_fram_manager.py`

Central FRAM storage manager: a bump-pointer chunk allocator (`get_chunk()`/`get_timestamped_chunk()`)
on top of `asy_fram_driver.py`'s `FRAM_SPI`, giving each chunk dual-copy redundancy, CRC-checked
self-healing reads, and a status-byte busy/idle protocol that detects a write torn by power loss.
Contract: never raises; every method returns `False`/`None` (or an all-`None`/`False` tuple for the
timestamped variant).

Chunk layout: `[Data 0][Status 0-1][Status 0-2][Data 1][Status 1-1][Status 1-2]` — a bump allocator,
so a device's own lifetime call order fixes its on-chip layout, which must stay identical across
firmware versions for existing stored data to keep decoding. `_op_lock` (one per chunk) serializes
that chunk's own `write()`/`read()`/`clear()` end to end; `fram`'s own shared lock only serializes one
block operation at a time, released between a chunk's block 0 and block 1, so different chunks' block
operations may still interleave in that gap (a single chunk's own operations cannot).

**Deliberate, owner-confirmed design points**: "both blocks valid but different data" is a hard
failure, not a guess — there's no generation counter to say which block is newer, so a write torn
between blocks must be reported as corruption. The busy/idle protocol brackets *reads* too (not just
writes) — MB85RS64V reads are destructively read internally, so a power loss mid-read is as real a
risk as mid-write. `get_chunk()`/`get_timestamped_chunk()` reject `size == 0` unconditionally before
any CRC/capacity logic runs — a chunk storing nothing is never sensible. `AsyFramTimestampedChunk.
write()`/`write_into()` return `(ntp_synced, utc, success)` — `success` is the *third* element, not
first, unlike every other bool-returning method in this file; this is the real, in-use shape
(`asy_sgp40_driver.py` already unpacks it this way), not to be silently reordered.

**Known gaps (owner-confirmed)**: `get_crc_buf()`/`get_size()` (both chunk classes) have zero callers
anywhere. `asy_fram_driver.py`'s own write-protect/verify methods still have zero callers from this
manager.

89 tests + 10 (`tests/test_fram_integration.py`, full-stack integration down to the simulated raw SPI
bus, including two `SensorReader`s sharing one manager and the same manager backing two structurally
different chunk types across a simulated reboot).

### `system_service.py`

Generic system-housekeeping service shared by every `sensortask-*.py` device file (uptime, boot
signature, reboot/reboot-to-bootloader, storage pause, staggered timer-startup sequencing, the task
supervisor loop).

Real gaps found and fixed: `status_counter()`'s NTP-synced branch called `time.mktime(time.gmtime())`
completely unguarded — raises `OverflowError` past rp2's ~2037 32-bit epoch range; extracted into
`_ntp_boot_signature()`, falling back to the same random-signature-after-timeout path as "never
synced" on either failure. The caller-supplied `ntp_is_synced()` callback and every driver-supplied
task/timer starter were called with no exception guard — a single misbehaving driver could kill the
whole supervisor task; wrapped in `try/except Exception`. `_timer_sequencer()` indexed `timers
[counter]` with no bounds check — an empty timer-starter list raised `IndexError` on the very first
call; `start_timers()` now short-circuits to `self.timers_running.set()` for an empty list instead.

**`machine.Timer`/`machine.WDT` verified directly against real rp2 source** (`ports/rp2/machine_timer.c`/
`machine_wdt.c`), not assumed: bare `Timer()` never allocates (safe); `Timer.deinit()` is safe
unconditionally; **`Timer.init()` raises `OSError(ENOMEM)` if the alarm pool is exhausted** — a real,
confirmed path, unguarded in three places (`_timer_sequencer()`'s chained timer, `pause_permanent_
storage()`'s auto-unpause timer, `reboot_system()`/`reboot_bootloader()`'s reset timer). Fixed each:
the sequencer falls through to setting `timers_running` on failure; the pause auto-undoes itself; the
reboot path sets a `_force_watchdog_starve` flag (checked alongside the existing task-error-budget
condition) so the watchdog stops being fed and the device resets anyway within its own timeout.
`WDT.feed()` is a bare register write, confirmed it cannot raise. A fourth, identically-shaped gap
(`start_uptime_timer()`'s own `.init()` call) was found in a later pass and fixed the same way as
`pause_permanent_storage()`'s graceful-degradation precedent (owner's choice, since a safe substitute
exists — log and keep running; only uptime/boot-signature stay unresolved that boot).

**Soft `Timer` callbacks can be silently dropped by MicroPython's scheduler, not just delayed** —
see CLAUDE.md's Platform target notes for the mechanism. Two call sites in this file rely on a
scheduled callback eventually running with no other safeguard: `reboot_system()`/
`reboot_bootloader()`'s one-shot reset timer, and `_timer_sequencer()`'s chained one-shot timers via
`start_timers()`'s `await self.timers_running.wait()`. A bounded-timeout mitigation was drafted for
both and explicitly rejected by the owner (see CLAUDE.md) — recorded here too so it isn't
re-proposed for these specific call sites without knowing it was already considered.

**Boot signature's `-1`/`1` sentinel replaced with `None`** (owner-confirmed design): the field exists
purely so an outside observer can detect that *this* device rebooted, by polling and watching for the
value to change once resolved — not for cross-device correlation or as a real timestamp. Moved from
`LockedValue(1)` to `LockedCounter(init_value=None, max_val=0xFFFFFFFF)`, reusing the existing
"`None` = not yet resolved" primitive rather than adding one. Confirmed directly against
`ports/rp2/mpconfigport.h`/pico-sdk source that RP2040's `random` module auto-seeds every boot from
genuine physical entropy (Ring Oscillator + leftover RAM + microsecond timer via `pico_rand`), not a
fixed compile-time constant, so the random fallback's own uniqueness holds.

`tests/machine.py` extended with fake `Timer`/`WDT`/`reset()`/`bootloader()`; every constructed
`Timer` self-registers into a class-level list so test code can `.trigger()` even an unstored,
fire-and-forget instance, matching real fire-and-forget IRQ usage.

58 tests.

### `asy_udp_socket.py` + `captive_dns.py`

Async, non-blocking UDP wrapper around one `socket.socket` (cooperative `select.poll` loop, since
MicroPython's `asyncio` has no built-in UDP-readiness primitive). Two callers: `async_connect.py`'s
NTP client and `captive_dns.py`'s `DNSServer`.

Real bugs found and fixed: **the class could not actually send or receive anything** — `sendto()`/
`write()`/`recvfrom()` each started with `if self.sock is None: return None`, but `self.sock` is only
ever created inside `_connect()`, itself only called from `ready()`, which those same three methods
called *after* that guard — every call short-circuited before `ready()` ever ran, permanently. Fixed
by removing the premature checks. `write_and_recvfrom()`'s retry loop returned unconditionally after
the first iteration — `tries` never actually retried; fixed to loop until a response arrives or
`tries` is exhausted. `_connect()`'s retry budget was whole-object-lifetime, not per-call — once
exhausted, every future call permanently short-circuited to "not connected"; fixed so exhaustion tears
the socket down for a genuinely fresh next attempt. An invalid `mode` caused **a genuine,
unrecoverable lockup** — the retry loop's dead `else` branch set `connected = False` but never
incremented `tries` or awaited anything, spinning forever with zero yield points, starving every other
task on the single-core cooperative scheduler including whatever feeds the watchdog. Fixed: `mode` is
now validated eagerly in `__init__`, raising `ValueError` immediately. A malformed `addr` (right tuple
shape, wrong element types) or wrong-typed `conn_tries` each raised an uncaught `TypeError` bypassing
every `except OSError:` in the file — validated eagerly too. `MemoryError` is not an `OSError`
subclass in MicroPython (confirmed) — every existing `except OSError:` was blind to allocation
failure; widened to `(OSError, MemoryError)` throughout. `disconnect()` could get permanently stuck
mid-teardown if `poller.unregister()` raised before `sock.close()`/state-clearing ran — fixed to clear
state eagerly first, each step independently guarded.

**Mutation-bypass and concurrency findings**: post-construction mutation of `addr`/`conn_tries`
reintroduced the same uncaught-exception bugs through a different door — stored as
`_addr`/`_mode`/`_conn_tries` (naming signal only, not enforced) and every touching `except` clause
also catches `TypeError` now, so the object self-heals regardless of how it got into a bad state. A
`disconnect()` concurrent with an in-flight `_connect()` retry crashed with an uncaught
`AttributeError` — closed with a per-instance `asyncio.Lock` serializing `_connect()`'s setup/retry
phase against both itself (a second caller now joins the first's in-flight attempt rather than getting
a premature `None`) and `disconnect()`. Verified directly, both directions, that cancellation while
holding vs. waiting on this new lock still propagates and releases cleanly. `ready()`'s own `mask`/
`timeout_ms`/`wait_time_ms` parameters and `write_and_recvfrom()`'s own `tries` parameter had the same
unguarded-caller-input shape as the `__init__` fixes above — fixed the same way (validated/wrapped,
degrades instead of crashing).

**Confirmed by direct testing, not fixed (documented contract, not a bug)**: a datagram larger than
the `recvfrom()` buffer is truncated with zero error and zero signal — MicroPython's `socket` module
has no `recvmsg()`/`MSG_TRUNC`; callers must size buffers generously (both real callers already do).
Connected (`mode="client"`) sockets get kernel-level source filtering for free — a third-party socket
sending to a connected client's address from an unexpected source is never delivered; `mode="server"`
sockets are unconnected and get no such filtering (`captive_dns.py` didn't check `addr` at all before
its own fix below). `ready()`'s `wait_time_ms` default of `0` busy-polled ~180× more than necessary
while idle — changed default to `20`ms.

**`captive_dns.py` fixes (owner-authorized exception to the "don't edit `improved-quality/`" hard
rule)**: `DNSServer.run()` now takes a `netmask` alongside `server_ip` and rejects any request whose
source address doesn't fall in the AP's own subnet — a captive-portal DNS server has no legitimate
reason to answer a query from off its own AP. `DNSQuery.__init__` parsed the raw datagram with no
bounds checking — a datagram shorter than 13 bytes or truncated mid-label raised an uncaught
`IndexError`/`UnicodeError`, stalling the entire DNS server (and every client waiting on it) for 3
seconds per bad packet via the loop's own broad `except Exception: ... sleep(3)`. Fixed: wrapped in
`try/except (IndexError, UnicodeError): self.domain = ""`, reusing the existing "don't respond"
sentinel.

62 tests (`asy_udp_socket.py`; `captive_dns.py` isn't promoted to `src/`, verified via throwaway
scratchpad repro scripts instead, per the "tests belong once code is promoted" convention).

### `asy_scd30_driver.py`

`SCD30_Reader` extends plain `SensorReader` (not `SensorReaderConfig`), deliberately — the SCD30 has
no local config file; its 6 configurable fields (`TempOffs`/`MeasInt`/`AmbPres`/`Altitude`/
`ForceCalRef`/`SelfCal`) live in the sensor's own NVM and are read back live via `get_dict_cfg()`'s
callback path. No `ContMeas` (continuous-measurement-running) schema entry exists because the sensor
has no command to query that — only whether *data* is ready, a different question.

Real bugs found and fixed: `get_CO2()`/`get_temperature()`/`get_relative_humidity()` each
independently re-checked the data-ready flag and cleared the cache on "not ready" — but the flag
clears the instant it's read, so only the *first* of the three sequential calls per cycle ever saw
"ready"; Temperature/Humidity came back `None` on every successful read. Fixed by factoring the
data-ready-check-and-fetch into one `read_measurement()` call made exactly once per cycle; the three
getters are now pure cache reads with no I2C of their own. `set_ambient_pressure()`/`set_altitude()`
truncated via `int(...)` before validating the range — `int(-0.5) == 0`, so any value in `(-1, 0)`
silently passed through as the "disable" sentinel `0` instead of being rejected; fixed to validate
first. `set_altitude()`/`set_temperature_offset()`/`set_forced_recalibration_reference()` had no (or
only partial) input validation despite this file's own schema tuples already documenting the real
valid ranges; fixed to match. `reset()` slept only 0.2s after the soft-reset command — the Interface
Description documents boot-up as < 2s; fixed to 2.5s (margin, since this path also runs on every
failure-triggered restart). `setup()` had no device-identity check beyond the generic bus-level ACK
probe, unlike its siblings (BMP3xx checks chip-ID, SGP40 self-tests) — owner decided to add one:
`setup()` now reads the firmware-version register (CRC-validated) before `reset()`, the value itself
unchecked (no documented valid-version set exists) since a successful CRC-valid read is itself the
identity signal.

**Investigated, left as-is (owner-confirmed)**: a not-ready read leaving the cache untouched (rather
than clearing it) matches the legacy driver's own proven field behavior — an earlier attempt to clear
on not-ready was reverted; a rare not-ready blip shouldn't count as an error the caller has to recover
from. No published NVM write-cycle endurance figure exists for any persistent setter in this file
(checked every available Sensirion doc) — safe today only because every one is REST-triggered, never
called from a boot path or periodic loop; don't add a periodic/high-frequency caller without
reconsidering this.

**Standing principle from this review**: a proposed behavior change needs to be re-verified against
the legacy driver's own actually-proven field behavior, not just judged correct against internal
code-review logic in isolation.

59 tests.

### `asy_bmp3xx_driver.py`

Reviewed for quality/style and, per explicit owner request, reliability against genuine I2C bus
disturbance — units must recover communication without manual intervention. Verified directly against
Bosch's `BST-BMP388-DS001`/`BST-BMP384-DS003` datasheets and `BMP3_SensorAPI` (Bosch's official
reference driver).

**Reliability fixes**: `_read()`'s forced-mode data-ready poll was unbounded — a bus disturbance
corrupting `STATUS` into never reporting ready would hang the read task forever; bounded with a
300ms timeout (generous margin over the datasheet's ~129ms worst case at x32/x32 oversampling).
`reset()` was a blind, unverified `CMD` register write — now matches Bosch's own reference sequence
(wait `cmd_rdy`, settle 2ms, verify acceptance via `ERR_REG`'s `cmd_err` bit). `_read()` had no sanity
check on computed pressure/temperature — unlike SCD30/SGP40 (CRC8-framed), BMP3xx's plain register
protocol has no CRC at all, so a single bit flip was previously undetectable; now rejects a reading
outside the datasheet's own -40..85°C / 300..1250 hPa range. `set_pressure_oversampling()`/
`set_temperature_oversampling()` shared the `OSR` register's bit-fields via a hand-rolled, non-atomic
read-then-write pair — migrated to `asy_i2c_driver.py`'s shared `get_bits`/`set_bits` API, atomic
against the scheduler. The six low-level oversampling/filter-coefficient forwards swallowed every
exception silently — now logged via `self.pr.err_s()`, so a transient bus fault on a REST-triggered
config change is visible in the sensor's own error history.

**`_read_bmp()` triggered two independent physical measurements per read cycle, not one** —
`get_pressure()`/`get_temperature()` each independently call `_read()` (a full trigger→poll→
burst-read→compensate cycle that already computes *both* values together), and `_read_bmp()` called
both back-to-back, discarding half of each result and re-triggering a whole new conversion for the
other value. Predates the refactor entirely (present in the original deployed driver too). Beyond
doubling bus traffic, the stored pressure/temperature pair were never actually simultaneous — up to a
whole conversion cycle apart. Fixed by adding `get_pressure_and_temperature()` (one `_read()` call,
both values).

**`_IIR_SETTINGS` didn't match either BMP384 or BMP388's datasheet** — coded as powers of two `(0, 2,
4, 8, 16, 32, 64, 128)`, but the datasheet documents `2^index - 1`: `(0, 1, 3, 7, 15, 31, 63, 127)`.
Corroborated by three independent sources (Bosch's own reference driver, the Linux kernel's IIO
driver, both datasheets) before fixing, since this changes real output. Traced to Adafruit's own
CircuitPython BMP3XX library having the exact same wrong tuple — likely origin. It "worked, somewhat"
because the wrong tuple still had 8 entries, so `.index()` always resolved to a valid hardware
encoding; before the fix, `set_filter_coefficient(1)` (a real, correct coefficient) raised
`ValueError`, while `set_filter_coefficient(128)` silently applied actual coefficient 127. **Fixed
everywhere this bug appeared, per explicit owner instruction**: `src/asy_bmp3xx_driver.py`,
`python/IndividualDrivers/asy_bmp3xx_driver.py` (deployed), `modules/sensortask-wozi.py` +
`improved-quality/sensortask-wozi.py`'s REST handler (`weight_fct=lambda x: 2**x` → `2**x - 1`,
dropping the now-unneeded `special_val=[0]` bypass), and `html_raw/wozi/sensorconfig.html`'s
user-facing label. `BMPTempOvers`/`BMPPressOvers`'s own `2**x` formula is correct as-is (oversampling
really is power-of-two) — only `BMPFiltCoeff` needed the fix.

**`SampleInterv`'s bound was corrected twice**: first set to 1-600s (owner-specified), then reverted
to 1-3600s after a consistency check found 1-3600 is the range actually enforced by the deployed,
working production REST handler for this exact field (`modules/sensortask-wozi.py` and every sibling
sensor's own sample-interval field in `sensortask-dev.py`) — a 600s ceiling would have silently
started rejecting an already-deployed device's stored value between 601-3600. The bounds-checking
mechanism itself (previously entirely absent) is a genuine fix; only the ceiling constant was wrong.

**Known local-verification gap, unchanged**: BMP390's own datasheet isn't in `datasheets/bmp3xx/` —
see Open Questions above.

68 tests.

### `asy_sgp40_driver.py` + `voc_algorithm.py`

Promoted together — `asy_sgp40_driver.py`'s `measure_index_and_raw()` is `voc_algorithm.py`'s only
real caller. Verified against the SGP40 datasheet (v1.2 Feb 2022) and Sensirion's original VOC
algorithm C reference (`Sensirion/embedded-sgp`).

**Real bugs found and fixed**: `_reset()`'s general-call soft reset was a confirmed real bug — the
datasheet (Table 17) documents `soft_reset` as a single data byte `0x06` addressed to the reserved
general-call address `0x00`; the code instead wrote *two* bytes to the SGP40's own address, never
touching `0x00` at all. Cross-checked against DFRobot's independent driver, which has the identical
bug — propagated Adafruit → DFRobot → this project, never previously verified against the datasheet.
Fixed to a real general call, still tolerating a NAK (not every device needs to acknowledge one).
**Shared-bus blast-radius checked before landing**: `sensortask-wozi.py` puts SGP40 on the same
physical bus as BMP3xx (wozi) and SCD30 (dev) — neither sibling's datasheet documents general-call
support, so both simply won't ACK it, which the fix's existing NAK-tolerance already handles; verified
negligible impact. `initialize()`'s self-test check compared the *whole* returned word against
`0xD400` — datasheet Table 13 is explicit only the high byte is the pass/fail marker (the low byte is
documented "ignore", not guaranteed zero); inherited verbatim from the deployed driver (and from
Adafruit's own library, same bug, same wording) — fixed to `(self_test[0] >> 8) != 0xD4`.
`initialize()` also dropped a "check feature set" step entirely — confirmed the command isn't in
Sensirion's real command table at all, and has a live upstream Adafruit issue reporting it rejects
real hardware unpredictably; removed. `get_raw()`'s post-measurement read delay was 500ms against the
datasheet's documented 25-30ms — a real, ongoing 16x-oversized cost on a 1Hz hot path; fixed to 100ms.
`_init_sgp()` wrote `self.err_cnt_internal` (no underscore) instead of `base_classes.py`'s real
`self._err_cnt_internal` — same bug class as SCD30's own (found independently), leaving the real
consecutive-failure counter never reset across a restart; fixed. `_read_sgp()` called the
caller-supplied `comp_callback()` unwrapped — the only caller-supplied callback in this codebase not
wrapped in `try/except`, unlike every analogous one elsewhere; fixed, falls back to `[None, None]`
("no compensation data") on failure. `_celsius_to_ticks()`/`_relative_humidity_to_ticks()` rounded
differently from each other (humidity to-nearest, temperature truncated toward zero) — never
"wrong vs. datasheet" (the datasheet's own worked examples all divide evenly either way), but
inconsistent; owner's direction: make both round to nearest, the more accurate choice.

**Reset redesign, per explicit owner direction** ("never drop a reset, don't redo work already done,
never give up, every path leads to defined behavior"): a pending reset now tracks two independent
sub-parts — `_reset_fram_cleared` and `_reset_algo_applied` — since they can complete on different
cycles (e.g. FRAM clear fails once while the software reset already succeeded). `_read_sgp()` only
attempts whichever sub-part hasn't yet succeeded, and `self.reset` only clears once both are confirmed
done in the same cycle, on both the success and exception path.

**Confirmed correct, not changed**: `initialize()`'s remaining `serialnumber[0] != 0x0000` check isn't
documented by the datasheet or replicated by any other reference driver checked — an unverified
assumption inherited from Adafruit, kept as-is (observed working on deployed hardware) per the same
don't-change-hardware-facing-behavior-without-real-hardware-access caution as `_boot.py`'s
`sensortask.py` import. `voc_algorithm.py`'s FRAM restore intentionally dumps/restores the algorithm's
*entire* 32-field internal state rather than Sensirion's own narrower `get_states()`/`set_states()` —
owner-confirmed deliberate: keeps a resumed state internally self-consistent regardless of real gap
length (this project's backups can span days via `BackupMaxAge`), and age-gating is this driver's own
job, not the algorithm's.

`tests/machine.py`'s fake `machine.I2C` gained a `read_queue` (a FIFO of byte strings, mirroring the
fake SPI's own) — the existing fake had no way to script a response to a `readfrom_into()` call at
all, which this word-oriented command/response protocol needs.

69 tests (`asy_sgp40_driver.py`), 28 (`voc_algorithm.py`).

## Consolidation-session integration fixes (sensortask-wozi.py)

Once all three sensor drivers above were promoted together, `improved-quality/sensortask-wozi.py`'s
own construction/wiring needed reconciling to their current constructors (owner-authorized, scoped
narrowly to mechanical fixes with a single unambiguous right answer, not a broader rewrite):
`SCD30_Reader.get_default_cfg()`/`SGP40_Reader.get_default_cfg()` calls removed from the shared
`cfgmgr` merge (neither method exists — SGP40 owns a private config file, SCD30 has none at all);
`BMP3xx_Reader`'s constructor call fixed (was passing the shared `cfgmgr` where `address: int`
belongs); `/system/status`'s `SCD30_ErrCnt`/`SGP40_ErrCnt`/`BMP388_ErrCnt` now all correctly extract
`["<NAME>"]["ErrCount"]` from each driver's `get_error_counter()` dict instead of comparing the whole
dict via `> 0` (same bug, same fix, across all three — `BMP388_ErrCnt` was fixed first during
`asy_bmp3xx_driver.py`'s own promotion; `SCD30_ErrCnt`/`SGP40_ErrCnt` followed once SCD30/SGP40 landed
too). `SGP40_Reader`'s FRAM-chunk-based per-sensor memory-error counters (`get_mem_error_counters()`)
no longer exist — replaced with `AsyFramManager.get_error_counter()`'s single chip-wide `FRAM_ErrCnt`,
a real REST JSON schema change (field removal/rename) forced by the architectural supersession, not
optional.
