# Sensor driver specification

Extracted from the three drivers that reached `src/` first (`asy_scd30_driver.py`,
`asy_bmp3xx_driver.py`, `asy_sgp40_driver.py`) plus the shared infrastructure they all build on
(`base_classes.py`, `asy_i2c_driver.py`/`asy_spi_driver.py`, `config_manager.py`, `print_log.py`,
`system_service.py`). This is the shared contract a *new* driver should follow — not a rehash of
`src/README.md`'s promotion checklist (correctness/exception-safety/typing bar every file must
clear), but the architecture and interface shape the checklist is applied *to*. Read both: this
file for "what shape does the code take," `src/README.md` for "how do I know it's good enough."

Writing a new driver should need only this file, the sensor's own datasheet, and the design
decisions in section 11 below — everything else here is already decided by precedent.

## 1. Layered architecture

Three layers, strictly one-directional (each layer only calls the one below it):

```
sensortask-*.py               (per-device integration: wires Readers to REST routes, task supervisor)
        |
*_Reader(SensorReader[Config]) (this file's layer 3 - asyncio task/config/data-distribution;
        |                       never raises; owns one *_I2C or *_SPI instance)
        |
*_I2C / *_SPI                  (this file's layer 2 - chip protocol: registers/commands, CRC,
        |                       compensation math; raises on real failure)
        |
I2CDevice / SPIDevice           (project-wide bus wrapper, asy_i2c_driver.py/asy_spi_driver.py -
        |                       not sensor-specific, never touched by a new driver)
        |
machine.I2C / machine.SPI      (MicroPython hardware bus)
```

A new driver adds exactly layers 2 and 3 (one new file, e.g. `asy_<sensor>_driver.py`) plus a
`_Reader` wiring block in the relevant `sensortask-*.py`. Layers below that are shared,
already-promoted infrastructure — don't reimplement bus handling.

## 2. File & naming conventions

One file per sensor: `asy_<sensor>_driver.py`. Within it:

- `_NAME = const("<SENSOR>")` — the dict key used everywhere this driver identifies itself:
  `get_dict_data()`/`get_dict_cfg()`/`get_error_counter()`'s returned dict, and every
  `self.pr.err_s(_NAME, ...)`/`wrn_s(_NAME, ...)` call.
- `<SENSOR> = namedtuple("<SENSOR>", (...))` — the measurement result shape, always ending in a
  `TS` (timestamp) field. Field names become the keys `make_dict()` (config_manager.py) exposes
  over the config dict pipeline — see section 6.
- `_VAL_<ABBREV> = const((("<FieldName>", "<type>", default, min, max, special),))` — one schema
  tuple per config field (section 5). `<ABBREV>` is a short mnemonic (`_VAL_SI`, `_VAL_POV`, ...),
  concatenated with `+` wherever a full schema is needed (`_VAL_SI + _VAL_POV + ...`).
- `<Sensor>_DeviceSession(Lockable)` — pure boilerplate, identical shape in all three drivers:
  ```python
  class <Sensor>_DeviceSession(Lockable):
      def __init__(self, i2c_device: I2CDevice) -> None:
          super().__init__()
          self.i2c_device = i2c_device
  ```
  Copy this verbatim (swap `I2CDevice`/`SPIDevice` as needed) — don't invent a variant shape.
- `<Sensor>_I2C` (or `_SPI`) — layer 2, protocol class. `<Sensor>_Reader` — layer 3, framework
  class. Constructor parameter order for `*_Reader` (match exactly, even when a sensor doesn't
  need every parameter): bus handle first (`i2c: I2C`), then sensor-specific addressing/pins
  (`address`, `irq_pin`, ...), then `trigger_sec: int = <n>`, `max_i2c_err: int = 5`, then (only
  if `SensorReaderConfig`, see section 4.3) `cfg_path: str = ""`, then `fram:
  AsyFramManager | None = None`, `history_length: int = 10`, `debug: int | None = None`.

## 3. Layer 2: `*_I2C`/`*_SPI` protocol class

Owns one `*_DeviceSession`, a pre-allocated scratch buffer (`self._buffer`/
`self._command_buffer`, sized once in `__init__`, reused every call — no per-call allocation,
per `src/README.md` section 4), and any chip-specific cached state (SCD30's last-read
temperature/humidity/CO2; SGP40's `VOCAlgorithm` instance).

**Contract: raises on any real failure — this is the layer that does *not* return sentinels.**

- A real bus/protocol failure — I2C `OSError` (NAK, timeout, device gone), a CRC mismatch, an
  out-of-range register bit-field, a malformed argument — propagates as an exception
  (`OSError`/`RuntimeError`/`ValueError`, chosen for what actually went wrong). This matches
  `src/README.md` section 2's raw-bus-call carve-out.
- **This carve-out's actual fault surface is bus-specific — verify against the real bus driver's
  own docstring, don't assume I2C's shape transfers to SPI.** `asy_i2c_driver.py`'s methods raise
  `OSError` on a real transaction fault; `asy_spi_driver.py`'s `write()`/`readinto()` **cannot
  raise at all** on rp2 (no ACK/NAK concept, confirmed against `extmod/machine_spi.c`) —
  `write_readinto()` is the one SPI exception, and it's a caller-input `ValueError` (mismatched
  buffer lengths), not a hardware fault, already caught and turned into `None` inside
  `asy_spi_driver.py` itself. A new SPI-bus sensor driver therefore has a different exception
  surface at this layer than an I2C one — check the concrete bus wrapper before assuming either
  shape.
- `setup()` performs identity verification (chip-ID register read for BMP3xx, CRC-valid
  firmware-version read for SCD30, serial-number + self-test read for SGP40) and raises if the
  sensor doesn't respond as expected — this is deliberate: a misconfigured bus fails loudly once
  at boot rather than producing a driver that silently degrades every later call.
- Every multi-transaction sequence that must not be interleaved by another coroutine (e.g.
  write-command-then-read-reply into a shared buffer) holds the `*_DeviceSession`'s own lock for
  the whole sequence — `async with self.i2c_<sensor> as dev: async with dev.i2c_device as i2c: ...`
  nested twice if the sequence itself needs two separate bus transactions with a delay between
  them (see `SCD30_I2C._read_dev_register`'s write-then-sleep-then-readinto).
- Compensation/calibration math (BMP3xx's coefficient decode, SGP40's tick conversions) lives
  here, cited against the datasheet section it implements (see `src/README.md` section 1 and
  section 11 below).
- Datasheet-documented operating-range checks belong here too, where the raw ADC/compensated
  value is available — reject and raise rather than returning an implausible value silently (see
  BMP3xx's pressure/temperature range check on every `_read()`).

## 4. Layer 3: `*_Reader(SensorReader | SensorReaderConfig)`

**Contract: never raises.** Every public method returns a well-defined sentinel (`None`/`False`/
an all-`None` namedtuple) on failure — this is the boundary past which nothing from layer 2
propagates uncaught. Every call into the layer-2 protocol object is wrapped in its own
`try/except Exception`, logged via `self.pr.err_s(_NAME, "...", e, errno=N)` (never a bare
`except:` — see CLAUDE.md's bare-except tracked-finding note) before degrading to the sentinel.

### 4.1 `read_loop()` skeleton (identical shape across all three drivers)

```python
async def read_loop(self) -> bool:
    if not await self._init_<sensor>():
        return False
    while True:
        await self.trigger_event.wait()
        self.pr.evt(_NAME, "sensor trigger")
        results = await self._read_<sensor>()
        if not await self._error_check(results, _NAME):
            return False
        await self._store_<sensor>(results)
```

Returning `False` from `read_loop()` (init failure or `_error_check` giving up) is the task
supervisor's restart signal (`system_service.py`'s `start_and_check_tasks()` treats a done task
the same whether it returned or raised — but returning cleanly is the contract here, not raising
out of the task).

- **`_init_<sensor>()`**: `await self.pr.setup()` first (required before any logged error/warning
  persists), `self._err_cnt_internal = 0`, then `try: await self.<protocol>.setup() except
  Exception as e: await self.pr.err_s(_NAME, "Error in initial setup:", e, errno=10); return
  False`. If the driver has `SensorReaderConfig`-backed hardware config (oversampling, filter
  coefficient, ...), push the stored config values into the sensor here too, after protocol
  setup succeeds.
- **`_read_<sensor>()`**: `timestamp = time.mktime(time.gmtime())` captured before the read; the
  whole protocol-layer call sequence wrapped in one `try/except Exception`, on failure every
  field (including `timestamp`) reset to `None` together and logged via
  `self.pr.err_s(_NAME, "Lesefehler:", e, errno=N)`. Returns a plain tuple of optionals (a
  driver-local `*Results` type alias under `TYPE_CHECKING`), not the sensor's own namedtuple —
  that conversion happens in `_store_<sensor>()`.
- **`_store_<sensor>()`**: if any field that must be present is `None`, return without storing
  (don't overwrite the last-known-good cached reading with partial data). Otherwise build the
  sensor's namedtuple — computing any derived fields (wet-bulb, dew point, altitude) via
  `math_helpers` here — and call `await self._set_meas_data(...)`.

### 4.2 Data-access contract (same 3(+1) methods, every driver)

```python
async def get_data(self) -> <Sensor>:                                            # cached last-good reading
async def get_dict_data(self) -> dict[str, dict[str, ...]]:                      # make_dict(await self.get_data())
async def get_dict_cfg(self) -> dict[str, dict[str, ...]]:                       # schema + optional live readback
async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:  # await self.pr.get_log(_NAME)
```

`get_data()`'s return type can't be narrowed with `typing.cast()` inside the base class (no
runtime presence — see section 9), so the concrete override either re-declares the concrete
return type and relies on the base's `NamedTuple` annotation being compatible (BMP3xx/SGP40:
`# type: ignore[return-value]` with a comment), or uses a driver-local no-op `cast()` shim
(SCD30). **These two approaches coexist today — flagged, not resolved, see section 12.**

### 4.3 `SensorReader` vs. `SensorReaderConfig`

This is a real per-sensor decision, not boilerplate — pick based on where the sensor's config
values actually live:

- **`SensorReaderConfig`** (BMP3xx, SGP40): the sensor has values that need a locally-cached,
  file-backed schema (`config_<name>.cfg`) — software-only knobs with no sensor-side counterpart
  (SGP40's `BackupPeriod`), and/or sensor-adjustable settings that reset on power-cycle and must
  be reapplied at every `_init_<sensor>()` (BMP3xx's oversampling/filter coefficient, which the
  chip itself doesn't persist across a soft reset).
- **Plain `SensorReader`** (SCD30): every "config-like" value the sensor exposes is stored in the
  sensor's own NVM and durable across power cycles — nothing to cache locally, so
  `get_dict_cfg()`'s `callback` does all the work (every field is a live I2C readback) and no
  `ConfigManager`/`config_<name>.cfg` exists at all for this sensor. See CLAUDE.md's SCD30
  `AmbPres` note for why this is deliberate, not a gap.

A sensor could plausibly need both kinds of fields at once (some NVM-persisted, some
software-only) — none of the three current drivers hit this case, so there's no established
pattern for it yet; treat it as an open design question if it comes up (flag to the project
owner rather than guessing, per CLAUDE.md's working agreement).

### 4.4 `get_dict_cfg()`'s `callback` parameter

`_get_dict_cfg(name, cfg_vals, callback=None)` (`base_classes.py`) merges the config manager's
stored values with an optional callback's live sensor readback. Only pass `callback=` for fields
that have a real, independent live-sensor source of truth to reconcile against — a field backed
only by the local schema cache needs no callback entry, its stored value is already authoritative.
(BMP3xx passes a callback covering 3 of its 8 fields — oversampling ×2 + filter coefficient, the
only ones the sensor itself reports back; SGP40 passes no callback at all, since all 3 of its
fields are pure software knobs; SCD30 — no `SensorReaderConfig`, see 4.3 — passes a callback
covering *all* its fields, since none have any other storage.)

## 5. Config schema system (`config_manager.py`)

Each field is a 6-tuple: `(name: str, type: "int"|"float"|"str"|"bool", default, min, max,
special)`. `special` is a sentinel value that bypasses the min/max range check via
`type_or_range_error`'s `check_special` — use it for an "unset"/"disabled" value that's outside
the field's normal operating range (e.g. SCD30's `AmbPres` field uses `special=0` for "ambient
pressure compensation not yet set" — see CLAUDE.md). A field with `default=None` and a non-`None`
`special` is a "special-alone" field: valid but never written to the JSON file — used for a
field that's entirely sensor-managed with no meaningful local default at all.

One JSON file per sensor: `config_<name>.cfg` (written by `SensorReaderConfig.__init__` via
`ConfigManager(cfg_path + "config_" + name + ".cfg", default_vals, self.pr)`). Loaded once at
`ConfigManager.__init__`, cached in `self._cache`, and only re-synced to disk by
`write_config()` — every `get_*` call reads the cache directly, no per-call file I/O.

**Config setters wired to REST endpoints are explicitly out of scope for a driver's initial
promotion** (project owner's stated decision, see CLAUDE.md) — the schema, `ConfigManager`, and
`write_config()` all already exist generically; what's deferred is the per-driver REST
handler wiring a config *setter* through `api_helpers.py`'s validate→apply→persist pipeline.
Getters (`get_dict_cfg()`) are expected from every driver; setters are a later, separate pass.

## 6. Data model (`config_manager.py`'s `make_dict()`)

`make_dict(nt: NamedTuple) -> dict[str, dict[str, ...]]` turns a sensor's namedtuple into
`{<TypeName>: {field: value, ...}}` via `repr()`-parsing — **not** `_fields`/`_asdict()`, because
MicroPython's `collections.namedtuple` implementation doesn't provide either. Don't assume
CPython namedtuple introspection is available; this is why `make_dict()` exists at all instead of
every driver writing its own `_asdict()`-based dict conversion.

## 7. Error handling & logging contract (`print_log.py`, `base_classes.py`)

- `self.pr` is a `PrintLogHistory` (in-memory, bounded `deque`) or `PrintLogHistoryStore`
  (FRAM-backed, survives reboot) depending on whether the `Reader`'s `fram` constructor argument
  was given — chosen automatically inside `SensorReader.__init__`, transparent to everything
  above it. A new driver never picks between the two itself.
- Log-level methods: `pr.one`/`pr.evt`/`pr.all` (sync, unconditional print gated on level, no
  history entry) for informational/trace messages; `pr.err_s`/`pr.wrn_s` (async, `await` required
  — they persist to `self.history`/FRAM) for anything that should count against
  `get_error_counter()`'s reported `ErrCount`/`ErrNum`/`ErrType`.
- `errno=`/`wrnno=` are small positive integers, unique *within one driver's own `_NAME` log
  stream* — there's no project-wide registry and none is planned; BMP3xx's numbering (10=init,
  11-14=config read/write, 15-20=oversampling/filter forwards, 21=trigger-interval) is a
  representative pattern (sequential, grouped by the method that raises it) worth following for a
  new driver, not a fixed convention to match number-for-number.
- `_error_check(results, name, condition=True) -> bool` (`base_classes.py`) is the shared
  consecutive-failure-streak counter every `read_loop()` calls once per cycle with that cycle's
  results tuple — returns `False` (give up, triggers task-supervisor restart) once
  `self._err_cnt_internal` exceeds `max_i2c_err`; decrements the streak back down on a good read.
  `condition` lets a driver suppress counting a "failure" that isn't really the sensor's fault
  (SGP40 passes `condition=compensated` — a `None` result from a missing compensation callback
  isn't a sensor failure).
- **Whether a per-field get/set forward (section 4.4-adjacent — `get_pressure_oversampling()`
  style thin wrappers around the protocol layer) logs via `self.pr.err_s()` on failure is
  currently inconsistent between drivers** — BMP3xx's forwards do; SCD30's/SGP40's plain
  `try/except Exception: return None` forwards don't. This is a known, already-tracked
  discrepancy (see BACKLOG.md's bus-concurrency-audit item), not a new one — a new driver should
  follow BMP3xx's logged-forward pattern until/unless the project owner decides otherwise.

## 8. Concurrency & locking model

Two independent lock layers, both needed:

1. **Bus lock** (`I2C.async_lock`/`SPI.async_lock`, one per physical bus instance) — held by
   every `I2CDevice`/`SPIDevice` on that bus (they share the *same* lock object, passed in via
   `Lockable.__init__(asy_lock=...)`), serializing *any* single transaction against every other
   device sharing the bus.
2. **Device-session lock** (`*_DeviceSession(Lockable)`, its own independent
   `asyncio.Lock()`) — serializes a *multi-transaction sequence* belonging to one logical
   operation (e.g. SCD30's write-then-sleep-then-read for one register) against a *different*
   coroutine trying to start its own sequence on the same sensor mid-way through — without this,
   two coroutines could interleave and corrupt the shared per-sensor scratch buffer even though
   each individual bus transaction is itself already serialized by lock 1.

Pattern: `async with self.i2c_<sensor> as dev:` (acquires lock 2) wrapping one or more
`async with dev.i2c_device as i2c:` blocks (acquires lock 1 for just that one transaction) —
see any `*_I2C` class's multi-step methods for the concrete nesting.

## 9. Timer/task/IRQ integration contract

- Every `Reader`/service class exposes both:
  ```python
  def get_task_starters(self) -> list[Callable[[], asyncio.Task[Any]]]: ...
  def get_timer_starters(self) -> list[Callable[[], None]]: ...
  ```
  even if trivially one-element lists — `system_service.py`'s `start_and_check_tasks()`/
  `start_timers()` discover and supervise every driver generically through these, never by name.
- Triggering a periodic read uses `machine.Timer` (default **soft**, no `hard=True` anywhere in
  this codebase) whose callback only ever calls `.set()` on an `asyncio.ThreadSafeFlag` — never
  `time.sleep()`, never business logic, inside a Timer callback. The read loop's own
  `while True: await self.trigger_event.wait(); ...` is what actually does the work, woken by the
  flag. This is the only safe way to wake a waiting coroutine from a callback context that isn't
  itself running inside the event loop.
- **Use `Timer.PERIODIC`, not `Timer.ONE_SHOT`, for anything that must keep firing** — see
  CLAUDE.md's soft-Timer-callback-drop gotcha: a soft callback can be silently dropped if
  MicroPython's fixed-depth scheduler queue is full, with no exception anywhere in that chain. A
  periodic timer self-heals on its next tick; a one-shot timer that gets dropped never fires
  again. SCD30's IRQ self-heal task (`scd_init_irq`) exists specifically to work around its data-
  ready *pin* being missed/stuck, illustrating the same "assume a signal can be silently lost,
  build in a self-healing re-check" principle at the hardware-IRQ level too — the equivalent
  `Pin.irq()` pattern (`handler=lambda b: self.irq_trigger_event.set()`) if a new driver uses an
  interrupt pin, not just a Timer.
- A driver needing more than one periodic rate (BMP3xx: 1 Hz base tick divided down by
  `trigger_period` to the user-configured interval) runs a second small `_base_trigger()` task
  that counts base ticks and sets the "real" `trigger_event` once the configured interval is
  reached — rather than reprogramming the `Timer`'s own period at runtime.

## 10. Typing conventions

Already stated generally in `src/README.md` section 6 — the sensor-driver-specific instances:

- `TYPE_CHECKING` guarded via `try/except ImportError: TYPE_CHECKING = False`, never an
  unconditional `from typing import ...`.
- PEP 604 `X | None` everywhere; never `typing.Union`.
- `typing.cast()` has no runtime presence on MicroPython — see section 4.2 for the two
  approaches currently in use (flagged as unresolved, section 12).
- A driver-local `*Results` tuple-of-optionals type alias (`SCDResults`, `BMPResults`) is
  declared under `if TYPE_CHECKING:`, used only as `_read_<sensor>()`'s return annotation — it's
  a plain tuple, not a `NamedTuple`, since it's an internal intermediate shape, not the public
  data model (section 6 covers that).

## 11. Design decisions a new driver must make (datasheet + judgment, not precedent)

Everything above is already decided by the existing three drivers. What's genuinely new per
sensor:

1. **Bus**: I2C or SPI — determines which protocol-layer exception surface applies (section 3).
2. **Identity check**: what does `setup()` verify before trusting the sensor is really there
   (chip-ID register, firmware-version CRC, serial-number + self-test, ...) — per the datasheet's
   own documented identification mechanism.
3. **Config location** (section 4.3): does each adjustable value live in the sensor's own NVM
   (→ no local schema, live readback only) or is it a software-only/volatile-on-power-cycle
   setting (→ `SensorReaderConfig` + schema)?
4. **Derived fields**: does this sensor's raw reading need `math_helpers`-style derived
   computation (wet-bulb, dew point, altitude, ...), and if so what's the formula's own
   authoritative source and valid domain (`src/README.md` section 1)?
5. **Operating-range validation**: what does the datasheet document as the valid measurement
   range, and where's the right layer to reject an out-of-range reading — protocol layer (BMP3xx,
   no CRC framing so a bit-flip is otherwise undetectable) vs. relying on CRC/self-test alone
   (SCD30/SGP40, which do have per-transaction CRC framing)?
6. **Trigger rate**: fixed (SGP40's VOC algorithm needs an exact 1 Hz cadence) or user-configurable
   (BMP3xx's `SampleInterv`, SCD30's on-chip `MeasInt`)?
7. **FRAM/persistence needs**: does this sensor have state worth surviving a reboot beyond the
   generic error-history logging every driver gets for free (SGP40's VOC-algorithm-state backup
   is the only current example — a much larger addition than most sensors will need)?
8. **Errno/wrnno numbering**: pick a sequential scheme grouped by failing method, scoped to this
   driver's own `_NAME` stream (section 7) — no cross-driver registry to consult or update.

## 12. Known open inconsistencies (flagged, not resolved by this document)

Per CLAUDE.md's "flag, don't silently fix" rule — these are real, verified differences between
the three existing drivers that this spec deliberately does not adjudicate:

- **`typing.cast()` narrowing** (section 4.2): SCD30 defines a local no-op `cast()` shim guarded
  by the same `try/except ImportError` pattern as `TYPE_CHECKING`; BMP3xx/SGP40 instead use
  `# type: ignore[return-value]` with an explanatory comment. Both are runtime-safe; they're
  simply different styles for the same problem, introduced independently across the three
  original promotion sessions.
- **Per-field get/set forward error logging** (section 7): BMP3xx's forwards log via
  `self.pr.err_s()` on failure; SCD30's/SGP40's don't. Already tracked in BACKLOG.md, not new
  here — restated because it's directly relevant to "what should a new driver's forwards do."

Neither blocks writing a new driver — pick BMP3xx's version of each (the more recently settled,
more informative one) per this spec's section 4.2/7 guidance — but reconciling the two existing
drivers that diverge is a separate, still-open piece of work (goal 3 of the consolidation
session that produced this document), not something this spec resolves by fiat.

## 13. Testing

Covered fully by `tests/README.md` ("Hardware-touching files: mock at the raw bus-transaction
level only") — restated as the one sensor-driver-specific summary: mock `tests/machine.py`'s
raw `readfrom_mem`/`writeto_mem`/`readfrom_into`/`writeto`/`scan` only, letting the real
`*_I2C`/`*_Reader` logic (bit-packing, CRC, locking, error paths) run against a real
dict-of-registers fake. `src/README.md` section 12's parameter-combination/boundary/NaN-inf
coverage requirements apply to any pure-computation helper a new driver adds (compensation math,
tick conversion) the same as they do to `math_helpers.py`.
