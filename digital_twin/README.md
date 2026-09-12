# `digital_twin/` — hardware simulator for the wozi and dev prototypes

A set of fake `machine`/`network`/`neopixel` modules, sitting at the same raw I2C/SPI
bus-transaction mocking boundary `tests/machine.py` establishes for unit tests, but built for a
different purpose: real-time-firing `Timer`s and randomized-but-plausible sensor values, so the full
assembled `src/sensortask_wozi.py`/`src/sensortask_dev.py` prototypes can run under the real
MicroPython Unix-port interpreter and behave like they're attached to real hardware — not just
satisfy a hand-driven test double. See SPECIFICATION.md Part A.10 for how this fits into the rest of
the architecture, and Part C.11 point 9 for the per-driver "add a matching chip fake" requirement.

**Not `tests/machine.py`, does not import it, and is never imported by anything in `tests/`.**
Kept completely separate so nothing here can accidentally affect the deterministic unit-test suite
`scripts/test.sh` runs by default (`MICROPYPATH="src:tests:frozen_modules:.frozen"`).

## What's here

- `machine.py` — `Pin`/`I2C`/`SPI`/`Timer`/`WDT`/`RTC`. `Timer` fires for real on a wall-clock
  schedule via an internal `asyncio` task, not `_thread` (upstream's own `_thread.rst` docs state
  outright that it "is highly experimental and its API is not yet fully settled" — not a fit for
  load-bearing behavior here, and every real `Timer` callback in this codebase is already trivial
  enough that true preemption buys nothing). `I2C`/`SPI` wire one of two selectable bus-layout
  profiles (`configure_i2c_wiring("wozi" | "dev")`, called once before any bus is constructed —
  default `"wozi"` if never called, so every caller that predates this option keeps its exact prior
  behavior unchanged): `"wozi"` mirrors `sensortask_wozi.build_system()`'s own construction
  (`I2C(0, ...)` carries the SCD30 at `0x61`, `I2C(1, ...)` carries the SGP40 at `0x59` and BMP3xx at
  `0x77`), `"dev"` mirrors `sensortask_dev.build_system()`'s own reversed layout instead (`I2C(0,
  ...)` carries the BMP3xx at `0x77` alone, `I2C(1, ...)` carries the SCD30 at `0x61` — IRQ/RDY pin
  11, not wozi's 8 — and SGP40 at `0x59`); `SPI(0, ...)` carries the FRAM chip either way. Any other
  address NAKs — a real bus with a fixed, known set of devices on it, not an unbounded fixture. `Pin`
  identity is shared by id (`Pin(8)` constructed twice returns the same underlying pin state), since
  a real GPIO pin is one fixed physical resource and chip fakes and drivers may each construct their
  own `Pin` object for the same id — this is exactly why the two profiles' differing SCD30 IRQ pin
  numbers (8 vs. 11) matter: the chip fake's own `rdy_pin` must be constructed with the same id the
  real driver's own IRQ `Pin` uses, or a simulated edge never reaches its handler. `I2C.log`/
  `SPI.log` (an ad-hoc introspection aid nothing in `tests/`/`digital_twin/` reads today) is bounded
  to the most recent 200 entries (`_LOG_MAXLEN`) - an unbounded list here was a real memory leak,
  found once a run drove enough real transactions for the list's own backing-array growth to need a
  large contiguous reallocation that failed with a genuine `MemoryError` on a fragmented heap.
- `_sgp40_chip.py` / `_scd30_chip.py` / `_bmp3xx_chip.py` / `_isl29125_chip.py` — one chip fake per sensor, each verified
  against its own datasheet in `datasheets/` for the raw transaction shape and sensible value
  ranges. `_scd30_chip.py`'s RDY pin fires a real rising edge on its own internal measurement-
  interval cadence, exercising the real driver's normal IRQ-driven path. `_scd30_chip.py` also has
  explicit `save_state()`/on-construction load JSON persistence for its five NVM-backed settings
  (see "SCD30 persistence" below) — the same `state_path` design `_fram_chip.py` uses, applied to a
  handful of scalars instead of the whole memory image. `_isl29125_chip.py` is **dev-only** (wozi
  does not carry this sensor) and is the one fake that models a gain the driver has to *learn*: its
  high range's full scale is a deliberately non-nominal multiple of its low range's, so the
  driver's gain-ratio self-calibration converges on something real instead of on the constant it
  started from. It also models the destructive `0x08` status read (which clears `RGBTHF`
  and `CONVENF` and releases the INT line), `BOUTF` high at power-up but **not** after the `0x46`
  reset command (`simulate_brownout()` is the seam for a supply event, which raises it again), the
  flat address pointer that walks the whole `0x00`-`0x0E` map in one burst and then pads with
  zeros, reserved config bits reading back zero, per-resolution clipping at `(1 << bits) - 1`,
  and `set_illumination(lux, tint=(r, g, b))` so a scene can clip one channel while green stays
  mid-scale. Every one of those register-map behaviours was measured against the real part on
  2026-09-12 — see SPECIFICATION.md Part C's ISL29125 conformance notes. Its INT line is **active-low** (`simulate_edge(0)` to assert), the opposite of
  `_scd30_chip.py`'s RDY.
- `_fram_chip.py` — the FRAM chip's SPI opcode protocol (WREN/WRDI/RDSR/WRSR/READ/WRITE/RDID), plus
  explicit `save_state()`/on-construction load JSON persistence (see "FRAM persistence" below).
  Models both real chips this project ships: wozi's 8KB MB85RS64V (default) and dev's 256KB
  MB85RS2MTA (`configure_i2c_wiring("dev")` selects it via `rdid_response=`/`size=`) - `machine.py`'s
  `_wire_spi_device()` picking the wrong one regardless of wiring profile was a real bug (fixed
  2026-09-04): dev's own `AsyFramManager.setup()` silently failed its device-ID check every twin
  run, caught and swallowed by its own broad `except Exception`.
- `unix_port_poll_prewarm.py` — a workaround for a confirmed, real dangling-pointer bug in the
  pinned MicroPython Unix port's `extmod/modselect.c` (see "Known gaps / follow-ups" below
  for the full account; `extmod/modselect.c` took zero commits between `v1.28.0` and the current
  `v1.29.0` pin, so the account and the workaround both still stand verbatim). Called as the first
  statement of `run_wozi_integration.py`'s and `segfault_stress_repro.py`'s own `main()`, before
  anything else in the process registers a poll object.
- `unix_port_gc_unwedge.py` — its sibling for a second Unix-port quirk: a SIGINT landing inside
  `gc_collect()` leaves the GC heap permanently locked, so the shutdown flush dies with a
  misleading `MemoryError: ... heap is locked` on a heap that is mostly free. Measured at ~5% on
  both `v1.28.0` and `v1.29.0`, so not a version-bump regression. Both runners call
  `unwedge_heap_after_interrupt()` first in their `except KeyboardInterrupt:` handler — full
  mechanism and why `gc.collect()` (not `micropython.heap_unlock()`) is the fix: SPECIFICATION.md
  Part F.6.
- `_crc8.py` / `_fault_injection.py` — small shared helpers (CRC-8 for SGP40/SCD30's word protocol;
  a generic op-keyed fault-injection queue, mirroring `tests/machine.py`'s own
  `inject_fault()`/`_maybe_raise()` convention) used by more than one chip fake.
- `network.py` / `neopixel.py` — independent, deliberately duplicated (not reused) copies of
  `tests/network.py`/`tests/neopixel.py`'s own fakes, for full runtime independence from `tests/`.
  `network.py`'s one real behavioral difference: `WLAN.connect()` transitions to a successful,
  connected state immediately, so a live run's WiFi polling loop doesn't wait forever the way the
  unit-test fixture (deliberately inert, hand-driven by test code) would. It only fakes *connection
  state* — actual traffic (NTP/DNS/HTTP) goes through the real `socket` module, a genuine wrapper
  around the Unix port's own BSD sockets, so it transparently reaches the real network once
  "connected". `ifconfig()` reports a plausible static address rather than a discovered one (this
  MicroPython build's `socket.socket` has no `getsockname()`) — harmless, since nothing in `src/`
  constructs a socket from that value. **AP-mode fidelity gap**: `WLAN.active()`/`config()` don't
  simulate address assignment on hotspot activation, so `ifconfig()[0]` reads `"0.0.0.0"` in AP
  mode instead of a realistic address — real hardware's cyw43 driver does return a real IP here.
- `_http_client.py` — minimal hand-rolled HTTP/1.1 client over `asyncio.open_connection()`, used to
  drive real requests against `WebserverService` in Unix-port integration runs (no HTTP client
  library is frozen into the pinned Unix-port build). Every response it sees is `Connection: close`
  (`asy_webserver_service.py`'s own hook), so it never needs keep-alive support.
- `launch.py` — standalone, `src/`-free CLI demo (`micropython digital_twin/launch.py [options]`):
  brings up the same bus wiring `sensortask_wozi.build_system()` uses and periodically drives one
  real bus-level read per sensor, a `WLAN.connect()` attempt, and WDT feeding. `--fault
  DEVICE:OP[:TIMES]` drives each chip fake's existing `FaultInjector`/`raise_on` API. Lighter and
  narrower in scope than `run_wozi_integration.py` below, which boots the real object graph instead.
- `run_dev_integration.py` — the `dev`-variant sibling of `run_wozi_integration.py` below: same
  orchestrator shape (soak/fault-injection/`--duration`-forever), boots `sensortask_dev.build_system()`
  against `configure_i2c_wiring("dev")` instead. No dedicated wrapper script exists yet (see
  "Swapping the twin in" below for direct invocation).

Every chip fake exposes a `.fault` (`FaultInjector`) surface for provoking a bus NAK/CRC-corruption/
timeout on demand — off/clean by default. Same surface also carries `inject_hang()`/`maybe_hang()`,
a real blocking `time.sleep()` for simulating a genuinely wedged bus (see "Automated CI suite"
below's `--hang` section) — distinct from a bounded, immediately-raised fault.

## Swapping the twin in for a Unix-port run

`src/sensortask_wozi.py` needs **zero twin-awareness** — no `if` branch anywhere distinguishing real
hardware from simulated. The swap is pure `MICROPYPATH` ordering, the same mechanism
`tests/machine.py` already uses transparently for the unit-test suite. `run_wozi_integration.py`
also drives real HTTP over real sockets against the real `WebserverService` — never Microdot's
`app.dispatch_request()` bypass, the same "full HTTP" standard the real system meets. The dedicated
entry point, `scripts/run_unix_port_integration.sh`, does exactly this:

```bash
scripts/run_unix_port_integration.sh                      # just launch + serve forever, no flags
scripts/run_unix_port_integration.sh --soak                # bounded automated soak run, then serves forever
scripts/run_unix_port_integration.sh --soak --duration 0   # same, but exits right after the soak
scripts/run_unix_port_integration.sh --fault sgp40:writeto # manual fault-injection exploration
```

Under the hood (builds the toolchain, then builds the real `wozi` website into
`frozen_modules/frozen_html.py` via `scripts/build_website.sh wozi` — **not**
`scripts/build_frozen_html.sh`'s own `html_stub` default; this is the twin's normal, default
wiring, matching what a real deployed unit actually serves, not a placeholder — then runs
`digital_twin/run_wozi_integration.py` — the real orchestrator, not `boot_entry/wozi_boot.py`
directly, since it also needs to drive the soak/fault-injection/`--duration`-forever logic around
`sensortask_wozi.main()`, not just block on it):

```bash
MICROPYPATH="src:digital_twin:ext:frozen_modules:.frozen" <micropython-unix-port-binary> digital_twin/run_wozi_integration.py [flags]
```

`frozen_modules` is required here too (see `SPECIFICATION.md` Part A.9 for the full pipeline) —
`src/sensortask_wozi.py` does an unconditional module-level `import frozen_html`, which
resolves from that segment (see `scripts/build_frozen_html.sh`'s own comment for why it can't be
`.frozen` itself). Omitting it fails the run at import time with `ImportError: no module named
'frozen_html'` before any twin code ever runs. `digital_twin` sits between `src` and
`frozen_modules`/`.frozen` — never together with plain `tests` on the same `MICROPYPATH` (that would
let `tests/machine.py`/`tests/network.py`/`tests/neopixel.py` shadow this package's own same-named
modules, or vice versa, depending on ordering — the two are meant to never be on the same path at
once). This is a **separate** invocation from `scripts/test.sh`'s own
`"src:tests:frozen_modules:.frozen"` — `scripts/run_unix_port_integration.sh` is not part of
`scripts/test.sh`'s own default `tests/test_*.py` glob loop (it can run forever in `--duration`-
omitted/manual mode, which would hang that loop if it were discovered there instead).

`digital_twin/run_wozi_integration.py` reuses this file's own `launch.py`'s `parse_fault_spec()`/
`_parse_wifi_outcome()` directly (same device/op/wifi-outcome vocabulary), and defaults to
`--host localhost --port 8080` (browser-reachable) with FRAM/config state persisted to a fixed
location inside `digital_twin/` (`fram_state.json`/`config/`, both gitignored, written only on
explicit shutdown — never an ephemeral per-run path, unlike the automated test tiers below). A bare,
no-flags run just launches the real object graph and serves forever, the same as a real rp2040 boot
would — the automated soak check (`--soak`, or `--soak-cycles N` which implies it) is a specialty,
opted into explicitly rather than run by default. See `run_wozi_integration.py`'s `parse_args()`
for the full flag list, and its `_soak()`/`_MEM_TREND_*` comments for the soak methodology.

A second, lighter integration tier also landed alongside the full orchestrator:
`tests/test_digital_twin_sensortask_integration.py` builds the real `sensortask_wozi` object graph
against the real twin buses and drives real HTTP traffic against it (never `app.dispatch_request()`
bypass), but only ever starts the specific tasks each test needs (never the full
`start_and_check_tasks()` supervisor) — runs under `scripts/test.sh`'s own default loop like any
other test file (via the same per-file `sys.path.insert(0, "digital_twin")` trick every other
`tests/test_digital_twin_*.py` file already uses), giving fast, everyday regression coverage of the
twin+webserver wiring without needing the separate `MICROPYPATH` invocation above. It already found
and fixed one real, previously-undetected bug this way: `src/asy_webserver_service.py`'s
`_get_settings_flat()` never flattened `config_manager.make_dict()`'s real `{type_name: {field:
value}}` shape, so `/networking`/`/notification` always returned `{}` and `/system` silently
dropped its `ntp`-sourced fields — masked by `tests/test_asy_webserver_service.py`'s own uniform
fakes, which happened to return an already-flat shape. See `_flatten_cfg_values()` in
`src/asy_webserver_service.py` for the fix.

### Running the dev variant

`run_dev_integration.py` mirrors `run_wozi_integration.py` exactly — only the booted module and bus
wiring differ — but has no dedicated `scripts/run_*.sh` wrapper yet. Invoke it directly, building the
`dev` website first (`scripts/build_website.sh dev`, not `wozi`):

```bash
MICROPYPATH="src:digital_twin:ext:frozen_modules:.frozen" <micropython-unix-port-binary> digital_twin/run_dev_integration.py [flags]
```

Same flag vocabulary, same `frozen_modules`/`MICROPYPATH`-ordering requirements as
`run_wozi_integration.py` above. Only the dev profile wires the ISL29125 (`0x44` on `i2c1`,
INT on GPIO6), so it is also the only entry point where that driver runs at all.

`--isl29125-int-stuck-high` arms the one fault mode that is a persistent *behaviour* rather than a
queued exception: the bus keeps answering and conversions keep happening, but the INT line never
moves. That is the silent failure the driver's periodic range evaluation exists to survive, and
nothing in `_fault_injection.py` can express it — which is why it lives on the chip itself, as
`Isl29125Chip.configure_fault("isl29125:int_stuck_high")`.

### FRAM persistence

The FRAM twin reads back exactly what was written, including across process restarts, but only
ever writes to disk on an **explicit** call — never automatically, to avoid unnecessary write
cycles on an SSD-hosted state file. Any entry point that boots the real `sensortask_wozi` object
graph against the twin (`digital_twin/run_wozi_integration.py` is the real example) should:

```python
import asyncio
import machine  # digital_twin/machine.py, once MICROPYPATH is set as above

machine.configure_fram_state_path("digital_twin_fram_state.json")  # before constructing spi0
try:
    asyncio.run(main())
finally:
    machine.flush_fram()
```

Omitting `configure_fram_state_path()` (or passing `None`) runs the FRAM twin in-memory only, which
is what every unit test in `tests/test_digital_twin_fram.py` does by constructing `FramChip`
directly (that file never goes through `machine.SPI` at all).

**`save_state()`/`_load_state()` stream the memory image in fixed-size chunks (512 bytes / 1024 hex
chars), never materializing one contiguous string for the whole buffer.** Found via a real
`MemoryError` during baseline verification: `json.dump({"memory_hex": bytes(self.memory).hex()})`
needs one contiguous ~2x-size-byte allocation (16385 bytes for a real 0x2000-byte FRAM) - reproduced
deterministically after a few seconds of the real task supervisor running (real asyncio churn
fragments the heap) even with ~1.5MB of *total* `gc.mem_free()` still available, since MicroPython's
GC coalesces freed blocks but never relocates live ones. Chunked reads/writes only ever need one
small chunk contiguous at a time.

### SCD30 persistence

Real SCD30 hardware persists five settings in its own onboard NVM across a power cycle:
measurement interval, ambient-pressure compensation, altitude compensation, temperature offset, and
automatic self-calibration enable (confirmed against `src/asy_scd30_driver.py`'s own setter
docstrings, each marked "NVM-persisted — survives reset() and power cycles"). The twin mirrors this
with the same explicit-flush design as FRAM persistence above — never automatic — but only for
those five settings; the live CO2/temperature/humidity readings always restart fresh on a new
process, matching what a real power cycle does to the sensor's in-flight measurement state:

```python
machine.configure_scd30_state_path("digital_twin_scd30_state.json")  # before constructing i2c0
try:
    asyncio.run(main())
finally:
    machine.flush_scd30()
```

Omitting `configure_scd30_state_path()` (or passing `None`) runs the SCD30 twin in-memory only,
same convention as FRAM. `digital_twin/run_wozi_integration.py` is the only entry point that
defaults to a persistent file (`digital_twin/scd30_state.json`, next to its own
`digital_twin/fram_state.json` default, both gitignored) — `digital_twin/launch.py` keeps its own
pre-existing in-memory-only default for both (`--fram-state-path`/`--scd30-state-path` opt in
explicitly): the persistent-by-default behavior is deliberately specific to the manual/end-to-end
entry point, not the twin's own standalone demo launcher.

## Running the twin's own tests

Its unit tests live in `tests/test_digital_twin_*.py` (matching every other `src/` module's own
test-file convention), but reach this package via a per-file `sys.path.insert(0, "digital_twin")` —
the same confirmed-safe pattern `tests/test_setter_microdot_integration.py` already uses for
`ext/microdot.py` — rather than a `scripts/test.sh`/`MICROPYPATH` change, so they run under the
exact same default invocation as every other test file:

```bash
scripts/test.sh   # discovers and runs them like any other tests/test_*.py - MICROPYPATH is set
                   # internally per test file (currently "src:tests:frozen_modules:.frozen"),
                   # not read from the calling shell's environment
```

All tests are deterministic — no wall-clock waiting, except one short-period/generous-timeout smoke
test in `tests/test_digital_twin_machine.py` (`test_timer_fires_for_real_on_a_short_period`) that
proves the real-time scheduling mechanism itself works at all, not a precise-cadence assertion.

## Automated CI suite

`scripts/run_digital_twin_ci.sh` turns the manual on-demand walkthrough above (fresh boot, every
GET/PUT endpoint, `DebugLevel=5` verbose logging, bus fault injection, settings/error persistence
across a real reboot, soak) into an automated, CI-gating check — wired in as the `digital-twin-e2e`
job in `.github/workflows/ci.yml`. See `SPECIFICATION.md`'s "Digital twin" section (Part A.10) for
the full architectural account of what it checks and why; this section is the practical how-to.

```bash
scripts/run_digital_twin_ci.sh   # clean -> build -> test, same as CI runs it
```

**Clean**: removes any leftover `digital_twin/fram_state.json`/`digital_twin/scd30_state.json`/
`digital_twin/config/` before starting — every run begins from a genuinely blank twin, not
whatever a previous local run or CI job happened to leave behind.

**Build**: builds the MicroPython Unix port (if not already cached at `$PICO_TOOLCHAIN_DIR`, same
convention as `scripts/test.sh`/`scripts/run_unix_port_integration.sh`) and the real `wozi` website
into `frozen_modules/frozen_html.py` (`scripts/build_website.sh wozi`, not the `html_stub`
placeholder). Must succeed before any test phase runs.

**Test**: hands off to `scripts/_digital_twin_ci_suite.py`, a self-contained `uv run` CPython
script (stdlib-only — no `uv sync` needed) that drives `digital_twin/run_wozi_integration.py` as a
real subprocess, over real HTTP/UDP (`http.client`/`socket`, not `_http_client.py` — this script
runs under CPython, not the twin's own MicroPython process), through thirteen real, sequential
subprocess runs on a fixed port (`18080`, distinct from the manual entry point's `8080` default, so
both can run side by side without colliding):

1. **Baseline boot** — walk every `GET` endpoint (`/measurements`, `/sensors`, `/networking`,
   `/system`, `/notification`, `/status`, `/`), then `PUT` a setting on each of
   `/system` (`DebugLevel=5`), `/notification` (`WarnCO2=1800`), `/sensors`
   (`SCD30.MeasInt=4`), `/networking` (`Hostname`), and `/status` (`ResetErrors`) — every route
   that accepts `PUT`. Shut down cleanly (`SIGINT`, matching the documented Ctrl-C path — a plain
   `SIGTERM`/`terminate()` would skip `run_wozi_integration.py`'s own FRAM/SCD30 flush) and confirm
   the state files actually landed on disk.
2. **Real reboot, settings persistence** — a fresh subprocess against the *same* persisted state
   (no clean step in between — the whole point is testing what survives). Confirms every setting
   from run 1 is still there after a genuine process restart, and that the now-persisted
   `DebugLevel=5` produces real, multi-module verbose log output (`print_log.py`'s
   `print(name, *args)` convention — checked for known `_NAME` prefixes like `SYSTEM`/`SGP40`/
   `SCD30`/`WEBSERVER`) from the very start of boot, not just after a later `PUT`.
3. **Reboot with a sustained/high-repeat-count ("permanent") bus-fault matrix** — `--fault` on
   every bus-level error-counted module at once (`scd30:writeto:500`, `sgp40:writeto:500`,
   `bmp3xx:readfrom_mem:500`, `fram:write:500`). Confirms every endpoint stays at `200` (graceful
   degradation under sustained failure, not just a single blip), every module's error counter
   climbs, and — via `run_wozi_integration.py`'s own unconditional shutdown line — that the
   (simulated) watchdog **never** starves despite the sustained failures. This is the expected,
   correct outcome under the current architecture: `--fault` only ever produces bounded,
   immediately-raised `OSError`s, never an indefinite hang, so nothing here can actually block the
   event loop long enough to matter — see run 10 below for the one scenario that can.
4. **Reboot fault-free — what must reset, and that every faulted bus comes back** —
   SCD30/BMP3XX/FRAM's counts must have reset to `0` (in-memory-only by design — SPECIFICATION.md
   Part A.7), and all three sensors must produce real readings again after a run in which every
   bus, the FRAM included, was faulted throughout. This run deliberately does **not** claim SGP40's
   FRAM-backed history survived run 3 — it cannot, because run 3's own matrix faults `fram:write`,
   so the chip is unwritable for that whole run. The check that used to stand here (`counter > 0`)
   was unsound twice over: `counter` counts `"W"` as well as `"E"`, so it was only ever satisfied by
   a *fresh* warning from this run's own boot, and waiting on that warning is a host-speed race
   (it lands before the sample on an x86 runner, after it on the project's bench Pi4). The real
   persistence claim lives in run 5b instead.
5. **Clean boot, a small *bounded* fault** (`sgp40:writeto:3`, not sustained) — the other half of
   the self-healing story run 3 alone can't show: not just "doesn't crash while still broken," but
   "comes back once the fault clears." Confirms the real error count stops climbing once the 3
   queued failures are exhausted (a driver's own "recovered" notice is itself logged as a warning,
   not an error — this suite counts `"E"`-typed history entries specifically, not the raw combined
   counter, to avoid mistaking a recovery notice for a new failure) and that measurements resume.
   **5b. Reboot straight onto run 5's state, fault-free — the restore is all-or-nothing.** Run 5
   left exactly three `"E"` entries on a *healthy* chip, write-through (`print_log.py`'s
   `_store_err()` writes on every push — there is no deferred flush to race), so they should come
   back. But run 5 shut down abruptly, and that can catch a chunk write in flight: both status bytes
   go to `_STATUS_BUSY` before the payload is touched, so an interrupted write leaves them there,
   `PrintLogHistoryStore.setup()`'s `_read()` then fails, and its `_write()` fallback stores the
   empty ring. Measured here at roughly **1 abrupt restart in 8**. That loss is **accepted
   behavior** (project owner's call, 2026-09-11 — no recovery scheme wanted for a reboot that
   catches the chip mid-operation), so this run asserts the invariant that does hold
   unconditionally: the restore is all-or-nothing, never partial and never garbled, which is the
   dual-block + CRC + busy-flag protocol's actual job.
   **5c. A commanded reboot, taken with storage paused — the case that must never lose anything.**
   Production's own `system_service._reboot()` pauses permanent storage before it resets, precisely
   so no FRAM chunk operation can be in flight across the restart; `PUT /system {"SystemCmd":
   "mempause"}` is that same pause over REST. With it held, none of `_write()`/`_read()`/`clear()`
   can start, no status byte can be left `_STATUS_BUSY`, and the restore is deterministic —
   measured **20/20** against the ~1-in-8 loss of run 5b's unpaused shutdown. This is what makes
   the pair sound: 5b alone would pass even if persistence never worked at all (an empty ring
   satisfies all-or-nothing), which is exactly the hole the old run 4 check had. 5c also confirms
   the pause itself does *not* survive the reboot (RAM-only by design) and that a `ResetErrors` PUT
   genuinely clears the restored history on the chip — issued only *after* polling for the restore,
   because a reset arriving before the loggers finish `setup()` is dropped by design and the
   restore then puts the old history straight back. The same all-or-nothing claim is mirrored at the
   mock tier (`tests/test_fram_integration.py`) and on real silicon
   (`tests_hardware/flash/test_fram_storage.py`'s reset-race test).
6. **Clean boot, configure a real SSID** (persisted) — needed for run 7's genuine STA-connect-
   failure cycle, not the `SSID==""` unconfigured shortcut.
7. **Reboot with 5 scripted `"no access point found"` WiFi outcomes** — drives the real STA →
   hotspot-fallback state machine (`conn_fail_to_hotspot=5`), starts the real `DNSServer`, and
   confirms it actually answers a real UDP DNS query sent from outside the process — not just that
   the internal state flipped. Only possible because of
   `digital_twin/_unix_port_udp_addr_shim.py` — see its own module docstring and the "`_unix_port_udp_addr_shim.py`"
   section below for the three Unix-port-only `socket` quirks it works around, entirely from
   twin-side code, with `src/` left untouched and correct for real hardware. `src/captive_dns.py`'s
   `DNSServer` binds the real, privileged port 53 unconditionally (correct for real hardware, which
   has no user/privilege concept at all) — `scripts/run_digital_twin_ci.sh` grants the built
   interpreter binary `CAP_NET_BIND_SERVICE` (via `setcap`, fresh on every invocation, since a
   cached toolchain archive doesn't preserve it) precisely so this run works when the job itself
   isn't root, e.g. a GitHub Actions runner. Without it, `asy_udp_socket.py`'s own `bind()` retry
   loop swallows the resulting `PermissionError` and gives up silently — the DNS server never
   raises, never crashes the process, it just never starts listening, so no amount of waiting fixes
   it. Confirmed directly: two real CI failures here were a timeout-budget red herring; the actual
   fix was the capability grant, not a longer wait.
8. **Reboot fault-free** — WIFI's own persistence-correctness check (in-memory-only, should reset
   to `0`), plus configures an unreachable NTP host (`192.0.2.1`, RFC 5737 TEST-NET-1) for run 9.
9. **Reboot with NTP permanently unreachable** — the other "network connections" real-world case.
   Confirms the webserver stays fully healthy past NTP's own 5s fetch timeout, not just eventually.
10. **The dedicated watchdog-backstop case** — a real, *blocking* (`time.sleep()`, not
    `asyncio.sleep()`) hang inside a chip fake's handler (`--hang sgp40:writeto:12`), genuinely
    freezing the whole interpreter past the 8000ms WDT window. `digital_twin/_fault_injection.py`'s
    `FaultInjector.inject_hang()`/`maybe_hang()` is what makes this possible — real rp2040
    `machine.I2C` calls have no `await` point (SPECIFICATION.md Part F.2), so a genuinely wedged
    real peripheral blocks the whole single-threaded interpreter, not just one asyncio task; a real
    blocking sleep is the only way this twin can reproduce that specific failure mode faithfully.
    Confirms the process survives and exits cleanly, and — the one thing sustained-but-bounded
    errors (run 3) cannot demonstrate — that the watchdog backstop itself actually engages
    (`would_have_triggered_count >= 1`), matching CLAUDE.md's own settled "hardware watchdog is the
    accepted backstop" rule for a genuinely wedged bus.
11. **Dedicated clean soak run** — a fresh `--soak --soak-cycles 20 --duration 0` run against a
    freshly-wiped twin, checked for a clean exit and a printed `PASS` summary (see
    `run_wozi_integration.py`'s own `_soak()` for the memory-trend methodology).

Each run's subprocess stdout/stderr is captured to `digital_twin_ci_logs/run<N>_*.log` (gitignored;
uploaded as a CI build artifact via the `digital-twin-e2e` job's own `if: always()` upload step, so
a failure's full boot log is inspectable from the Actions run itself, not just the pass/fail
summary). The suite exits non-zero if any check fails, failing the CI job.

### `--hang` (real bus hangs, distinct from `--fault`)

`digital_twin/launch.py --hang DEVICE:OP:SECONDS[:TIMES]` (also accepted by
`digital_twin/run_wozi_integration.py`) queues a real, blocking `time.sleep(SECONDS)` before the
next `TIMES` (default 1) calls to that op proceed — `sgp40`/`scd30` (`writeto`/`readfrom_into`),
`bmp3xx` (`readfrom_mem`/`writeto_mem`), `fram` (`write`/`readinto`). Unlike `--fault` (a bounded,
immediately-raised `OSError` — the driver's own normal error path), this genuinely freezes the
whole interpreter for real wall-clock seconds, the only way to simulate a truly wedged bus rather
than a bus that merely errors. `wlan` has no `--hang` vocabulary — its faults are a synchronous
`raise_on[]` check, not a bus transaction with a real HAL call underneath.

### `WDT._arm()`'s late-feed backstop

A real `--hang` freezes the whole interpreter, so every asyncio task — including `WDT`'s own
pending `_countdown()` sleep — sits unable to run for the hang's full real duration. Once the
interpreter unfreezes, `system_service.py`'s periodic `feed()` (its own check interval is
deliberately shorter than any real watchdog `timeout`) can win the race to run before
`_countdown()`'s own already-expired `sleep_ms()` gets its turn, since both became ready at the
same moment. A plain cancel-and-restart in `_arm()` would silently erase that already-elapsed
deadline — real hardware can't un-reset itself just because a feed arrived right after it should
already have fired. `_arm()` now checks, before cancelling the previous `_countdown()` task,
whether its own deadline had already elapsed; if so it credits the would-have-triggered event
itself, exactly once per elapsed window, before rearming — `_countdown()` still owns the normal,
not-yet-hung case, so this is purely the "a feed arrived too late" backstop, not a second counting
path. `run10_watchdog_hang_backstop.log`'s check depends on this same fix and on
`scripts/_digital_twin_ci_suite.py`'s Run 10 giving the twin enough `--duration` (15s, not 0) for
SGP40's own bus access — now queued behind BMP3xx's and SCD30's own FRAM-backed startup I/O on the
shared FRAM SPI bus — to actually reach its hung `writeto` before the run exits.

### `_unix_port_udp_addr_shim.py` (real UDP round trips under the Unix port)

`patch_asy_udp_socket_for_unix_port()` — called once, early, as `run_wozi_integration.py`'s own
`main()` does (right after `prewarm_poll_set()`, before anything constructs a socket) — also called
the same way, module-level before `import sensortask_wozi`, by `tests/
test_digital_twin_sensortask_integration.py` (its own hotspot/DNS section drives a genuine UDP round
trip against the real `captive_dns.py` `DNSServer` the same way `run_wozi_integration.py`'s run 7
does — see that test's own comment). That same test also needs the real privileged port 53 itself
to actually be bindable, same as run 7 — `scripts/test.sh` now grants the built interpreter binary
`CAP_NET_BIND_SERVICE` unconditionally (mirroring `scripts/run_digital_twin_ci.sh`'s own identical
grant, see that script's own comment for the full mechanism/rationale), not just
`run_digital_twin_ci.sh`, since this test now runs as part of the plain unit-tests suite too, not
only the separate digital-twin-e2e job. Works
around three confirmed MicroPython-Unix-port-only `socket` quirks that otherwise make a real UDP
round trip (DNS, NTP) impossible under this harness, entirely from twin-side code:

1. `bind()`/`connect()` reject `AsyUDPSocket`'s own plain `(host: str, port: int)` tuple with
   `TypeError: object with buffer protocol required` — the Unix port's `socket` module
   (`ports/unix/modsocket.c`) requires a pre-resolved buffer-protocol sockaddr instead. The real
   rp2/lwIP module (`extmod/modlwip.c`) accepts the plain tuple directly (confirmed by reading both
   C sources side by side, not just the type stub — see `BACKLOG.md`'s "Real-hardware verification
   gap" entry for the full account), so this is genuinely two different implementations, not one
   port being stricter about the same contract - the plain-tuple form `AsyUDPSocket` (correctly)
   always passes is required for real hardware, not a bug to fix in `src/`.
2. `sendto()` has this exact same requirement (`micropython/micropython#6924` is specifically about
   this method) — but its destination address is a per-call argument (a DNS/NTP client's ephemeral
   reply address, learned dynamically), not the constructor-time address point 1 already covers.
3. `recvfrom()` hands back the raw 16-byte packed C `struct sockaddr_in` as a plain `bytes` object,
   not the `(ip: str, port: int)` tuple `lwip_socket_recvfrom()` returns on real hardware and
   `captive_dns.py`'s own subnet check expects — confirmed directly against a real captured reply,
   not just the C source (this build's actual behavior differs from what a first look at
   `modsocket.c`'s own separate `socket.sockaddr()` utility function would suggest).

The patch pre-resolves via `socket.getaddrinfo()` before `bind()`/`connect()`/`sendto()` (same
pattern `unix_port_poll_prewarm.py`'s `prewarm_poll_set()` already uses for a different call site)
and unpacks `recvfrom()`'s raw struct into the shape production code expects. Every real call site
this project has (`captive_dns.py`'s `"0.0.0.0"`, `asy_ntp_client.py`'s already-DNS-resolved NTP
server IP via `asy_dns_client.py`) already hands over an already-numeric address, so the
`getaddrinfo()` calls here are always fast and local, never a real DNS lookup.

## Adding a new chip fake

**Required whenever a new sensor driver lands in `src/`** (see `SPECIFICATION.md` C.11's own
checklist item for this — do it the same session the driver is promoted, not deferred) — the
digital twin exists to track the *whole* real driver portfolio, not just the three sensors it
started with. For a new **I2C** sensor this is a small, mechanical addition:

1. Read the sensor's own datasheet first (`CLAUDE.md`'s standing "read the PDF first" rule, `datasheets/`)
   and add a new `_<name>_chip.py` alongside `_scd30_chip.py`/`_sgp40_chip.py`/`_bmp3xx_chip.py`,
   matching their established shape:
   - a `FaultInjector` (`self.fault`, see `_fault_injection.py`) for provoking a bus NAK/
     CRC-corruption/timeout on demand;
   - a `random_source` constructor seam (default `None` → falls back to the real `random` module)
     so tests can script deterministic values, and `digital_twin/launch.py --seed` can reseed every
     chip's walk from one shared source (via `machine.configure_random_source()` or the simpler
     `random.seed()` `launch.py` itself actually uses — see that file's own comment for why);
   - datasheet-sourced `min_*`/`max_*` range constructor arguments, plus the bounded-random-walk
     `*_step` bound every existing chip fake now uses (draw the initial value at construction,
     step-and-clamp on every later reading) — the step bound itself is a **not**-datasheet-derived
     physical-plausibility judgment call, document it as such in the docstring, same as the three
     existing chips do;
   - `handle_writeto()`/`handle_readfrom_into()` (word/CRC-framed protocols like SCD30/SGP40) or
     `handle_writeto_mem()`/`handle_readfrom_mem()` (register-addressed protocols like BMP3xx's)
     answering the *exact* raw transaction shape the real `*_I2C` driver class sends — confirmed
     directly against that file's own source, never assumed.
2. Wire it into `machine.py`'s `_wire_i2c_devices()`: add the new chip to the `dict` for whichever
   bus id (`0` or `1`) the real wiring puts it on, under the matching `_i2c_wiring_profile` branch
   (`"wozi"` or `"dev"` — cross-check `src/sensortask_wozi.py`'s/`src/sensortask_dev.py`'s own
   `build_system()` for the real pin/address assignment, since the two profiles put sensors on
   different buses), or add a new `if id == N:` branch if it lands on a bus id neither profile
   already uses on that bus.
3. Add `tests/test_digital_twin_<name>.py` — deterministic unit tests of the chip fake in isolation
   (no real `machine.I2C` involved, matching every existing `tests/test_digital_twin_{sgp40,scd30,
   bmp3xx}.py`) — then extend `tests/test_digital_twin_machine.py`'s own dispatch tests if the new
   chip shares a bus id those tests already probe.
4. Update this file's "What's here" list (the bus-wiring bullet above) to mention the new chip, and
   consider whether `digital_twin/launch.py`'s own `_sensor_loop()`/`_FAULT_DEVICE_OPS` should read
   from it too.
5. **Update `html/definitions/<device>.json`** for every device the new driver's fields should
   appear on (`SPECIFICATION.md` Part H.5/H.7, Part C.11 point 9) — the website has no
   other place a new sensor's fields get wired in, so skipping this step leaves the driver fully
   working (real chip fake, real REST endpoint, twin-tested) but permanently invisible on the
   website until someone remembers to come back and add it by hand.

**A new SPI sensor is not automatically supported yet if it would share an already-occupied SPI bus
id with the FRAM chip.** `_wire_spi_device()`/`machine.SPI` currently wire **one fixed device per
bus id** (matching the wozi prototype's own single-FRAM-on-`spi0` reality) — real multi-device SPI
chip-select is bit-banged by the caller (`asy_spi_driver.py`'s `SPIDevice`, not `machine.SPI`
itself), so a future twin `SPI.write()`/`readinto()` would need to start routing by which CS `Pin`
is currently asserted low, the way `machine.I2C` already routes by address. Not built now because no
such driver exists yet — flagged here rather than left to surprise whoever adds the first one.

## Code quality tooling

`digital_twin/` is in `pyproject.toml`'s ruff/mypy scope, same as `src/`/`tests/` - all three are
expected to stay fully clean, with no tracked-debt exemption anywhere in scope.
`scripts/lint.sh` covers it directly (`ruff check src tests digital_twin`).
`scripts/typecheck.sh` runs it as a **second, separate** mypy invocation
(`digital_twin/typecheck.ini`, always run regardless of `"$@"`) rather than folding it into the
main `[tool.mypy]` pass - mypy resolves each bare `machine`/`network`/`neopixel` module name to
exactly one file per run, so this package's own fakes and the real board stubs (`typings/`) can
never both be checked correctly in one invocation. `digital_twin/machine.py`/`network.py`/
`neopixel.py` and `digital_twin/launch.py`/every `tests/test_digital_twin_*.py` are excluded from
the main pass for exactly this reason (see `pyproject.toml`'s own `[tool.mypy]` exclude comment for
the full account, including a real `mypy src tests`-only finding this design caught) and checked
correctly by the dedicated pass instead - see `digital_twin/typecheck.ini`'s own docstring.

## Known gaps / follow-ups for later sessions

- **BMP3xx's fixed calibration block is not sourced from a real chip.** It's a real-shaped,
  hand-picked set of raw coefficient bytes, verified directly (by inverting the real cubic
  compensation formula — temperature inversion is quadratic, pressure then linear in raw ADC once
  temperature is known) to round-trip cleanly through the real compensation formula across this
  twin's whole sensible range — not literal factory-trim data off actual silicon, which this
  project doesn't have access to.
- **Fault injection is a bus/chip-level generic queue, not a fine-grained per-condition simulator.**
  `tests/_fram_chip_fake.py`'s own WEL-corruption-specific knobs (`drop_wren`,
  `disturb_write_autoclear`, ...) were purpose-built for `FRAM_SPI`'s own defense-in-depth unit
  tests (already covered by `tests/test_asy_fram_driver.py`) and weren't reproduced here.
- **`segfault_stress_repro.py`** is a manual, deliberately-aggressive concurrency-stress CLI tool —
  fires many concurrent HTTP clients against the real assembled system, exercising a scenario the
  automated test tiers can't (a genuine repro crashes the whole interpreter process) — run
  manually, same `MICROPYPATH` as `run_wozi_integration.py`. Its target bug is root-caused and
  fixed, not open: a dangling-pointer dereference at `extmod/modselect.c:132` in the pinned
  MicroPython Unix port (traced at `v1.28.0`, and `extmod/modselect.c` is unchanged at the current
  `v1.29.0` pin) — growing the shared asyncio poller's `pollfds` array (needed once
  concurrently-registered fds cross a multiple of 4) unconditionally repoints every
  already-registered poll object's `pollfd` field at the new buffer, including non-fd poll objects
  whose `pollfd` is legitimately `NULL`, corrupting it into a small garbage pointer the next
  `poll()` call dereferences. Confirmed compiled out of real rp2 firmware entirely
  (`MICROPY_PY_SELECT_POSIX_OPTIMISATIONS`, the macro gating this code path, defaults to 0 and is
  only turned on by the Unix port's own config — rp2 defines no override, and its non-optimized
  poll object has no `pollfd` field or array to grow at all) — real hardware was never affected.
  Fixed by `unix_port_poll_prewarm.py` (see "What's here" above and that module's own comments for
  the pre-warming mechanism itself).
  **Related upstream prior art, not the same bug**: the general shape of this — `pollfds`
  reallocation leaving stale pointers in already-registered `poll_obj_t`s — was filed as
  [micropython/micropython#12887](https://github.com/micropython/micropython/issues/12887) ("Use
  After Free at modselect.c:151", CVE-2023-7152) and fixed by
  [PR #12895](https://github.com/jimmo/micropython/commit/8b24aa36ba978eafc6114b6798b47b7bfecdca26)
  (merged into the 1.22.0 milestone, long before this project's pin). Verified directly
  against `extmod/modselect.c` at the real `v1.28.0` tag, and re-checked at `v1.29.0` (zero commits
  to that file between the two): that fix's pointer-update loop only skips
  a poll object when the map slot itself is empty (`if (!poll_obj) continue;`) — it does not skip a
  poll object whose `pollfd` field is legitimately `NULL` (the non-fd/stream-wrapper case this
  project hit), so it still runs pointer arithmetic on that `NULL` and corrupts it. No separate
  upstream issue for this narrower residual case was found as of this check — worth filing one
  upstream (with `segfault_stress_repro.py` as a ready-made repro) as a future follow-up.
