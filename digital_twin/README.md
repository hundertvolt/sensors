# `digital_twin/` — hardware simulator for any buildgen-generated device

A set of fake `machine`/`network`/`neopixel` modules, sitting at the same raw I2C/SPI
bus-transaction mocking boundary `tests/machine.py` establishes for unit tests, but built for a
different purpose: real-time-firing `Timer`s and randomized-but-plausible sensor values, so a full
assembled, buildgen-generated `sensortask_<device>.py` module — any of the 6 real devices, or the two
mandatory synthetic fixtures — can run under the real MicroPython Unix-port interpreter and behave
like it's attached to real hardware, not just satisfy a hand-driven test double. See
SPECIFICATION.md Part A.10 for how this fits into the rest of the architecture, and Part C.11 point 9
for the per-driver "add a matching chip fake" requirement.

**Not `tests/machine.py`, does not import it, and is never imported by anything in `tests/`.**
Kept completely separate so nothing here can accidentally affect the deterministic unit-test suite
`scripts/test.sh` runs by default (`MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen"`).

## What's here

- `machine.py` — `Pin`/`I2C`/`SPI`/`Timer`/`WDT`/`RTC`. `Timer` fires for real on a wall-clock
  schedule via an internal `asyncio` task, not `_thread` (upstream's own `_thread.rst` docs state
  outright that it "is highly experimental and its API is not yet fully settled" — not a fit for
  load-bearing behavior here, and every real `Timer` callback in this codebase is already trivial
  enough that true preemption buys nothing). `I2C`/`SPI` wire per a generic **wiring plan**
  (`configure_wiring(plan)`, called once before any bus is constructed — a plain
  `{"buses": {...}, "spi": {...}}` dict in the exact shape `buildgen.twin_wiring.compute_twin_wiring()`
  produces from a device's own TOML/`DeviceModel`, see "Booting a generated device" below).
  `configure_i2c_wiring("wozi" | "dev")` still exists as pure sugar over it, lazily loading
  `build/generated_src/sensortask_<profile>_wiring_plan.json` (buildgen-generated, no hand-typed
  literal — default `"wozi"` if neither `configure_wiring()`/`configure_i2c_wiring()` is ever called,
  so every caller that predates `configure_wiring()` keeps its exact prior behavior unchanged):
  `"wozi"` mirrors
  `sensortask_wozi.build_system()`'s own construction (`I2C(0, ...)` carries the SCD30 at `0x61`,
  `I2C(1, ...)` carries the SGP40 at `0x59` and BMP3xx at `0x77`), `"dev"` mirrors
  `sensortask_dev.build_system()`'s own reversed layout instead (`I2C(0, ...)` carries the BMP3xx at
  `0x77` alone, `I2C(1, ...)` carries the SCD30 at `0x61` — IRQ/RDY pin 11, not wozi's 8 — and SGP40
  at `0x59`); `SPI(0, ...)` carries the FRAM chip either way. Any other address NAKs — a real bus
  with a fixed, known set of devices on it, not an unbounded fixture. `Pin`
  identity is shared by id (`Pin(8)` constructed twice returns the same underlying pin state), since
  a real GPIO pin is one fixed physical resource and chip fakes and drivers may each construct their
  own `Pin` object for the same id — this is exactly why the two profiles' differing SCD30 IRQ pin
  numbers (8 vs. 11) matter: the chip fake's own `rdy_pin` must be constructed with the same id the
  real driver's own IRQ `Pin` uses, or a simulated edge never reaches its handler. `I2C.log`/
  `SPI.log` (an ad-hoc introspection aid nothing in `tests/`/`digital_twin/` reads today) is bounded
  to the most recent 200 entries (`_LOG_MAXLEN`) - an unbounded list here was a real memory leak,
  found once a run drove enough real transactions for the list's own backing-array growth to need a
  large contiguous reallocation that failed with a genuine `MemoryError` on a fragmented heap.
- `_sgp40_chip.py` / `_scd30_chip.py` / `_bmp3xx_chip.py` / `_isl29125_chip.py` — one chip fake per
  sensor, each verified against its own datasheet in `datasheets/` for the raw transaction shape and
  sensible value ranges. `_scd30_chip.py`'s RDY pin fires a real rising edge on its own internal
  measurement-interval cadence, exercising the real driver's normal IRQ-driven path. `_scd30_chip.py`
  also has explicit `save_state()`/on-construction load JSON persistence for its five NVM-backed
  settings (see "SCD30 persistence" below) — the same `state_path` design `_fram_chip.py` uses,
  applied to a handful of scalars instead of the whole memory image. `_isl29125_chip.py` is
  **dev-only** (`wozi` does not carry this sensor) and is the one fake whose high range's full scale
  is a deliberately non-nominal multiple of its low range's, so the driver's user-triggered
  gain-ratio calibration (SPECIFICATION.md Part M.1.5) has something real to converge on instead of
  the nominal constant it starts from. It also models the destructive `0x08` status read (which
  clears `RGBTHF`, `CONVENF` and `BOUTF` and releases the INT line — `BOUTF` being read-to-clear
  contradicts the datasheet and was measured on real silicon, see SPECIFICATION.md Part M.1.2),
  `BOUTF` high at power-up but **not** after the `0x46` reset command (`simulate_brownout()` is the
  seam for a supply event, which raises it again), the flat address pointer that walks the whole
  `0x00`-`0x0E` map in one burst and then pads with zeros, reserved config bits reading back zero,
  per-resolution clipping at `(1 << bits) - 1`, and `set_illumination(lux, tint=(r, g, b))` so a
  scene can clip one channel while green stays mid-scale. Every one of those register-map behaviours
  was measured against the real part — see SPECIFICATION.md Parts C.11.1, M.1.2 and M.1.4 for the
  divergences those runs found, the subtlest being that the threshold **persistence counter**
  restarts when `RGBTHF` is cleared, not on every status read, and a fake that reset it on every read
  makes the interrupt unreachable at the driver's own default sampling rate. Its INT line is
  **active-low** (`simulate_edge(0)` to assert), the opposite of `_scd30_chip.py`'s RDY.
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
  statement of `run_generic_integration.py`'s and `segfault_stress_repro.py`'s own `main()`, and at
  import by every `tests/` entry point that boots a `sensortask_*` module with real sockets (the
  sensortask, bus-hazard, UART-link, real-website, construction and webserver-concurrency files), before
  anything else in the process registers a poll object. Its listener scans upward from port 17400
  across a 64-port window rather than binding one fixed port, and fails loudly naming the window if
  none binds: `scripts/test.sh` runs usable cores x 1-4 files at once (`TEST_PARALLELISM`
  overrides), so a fixed port made concurrent imports die
  with `EADDRINUSE` (28 of 30 concurrent prewarms; 0 of 30 with the scan), and port 0 is no
  alternative since this port has no `getsockname()`.
- `unix_port_gc_unwedge.py` — its sibling for a second Unix-port quirk: a SIGINT landing inside
  `gc_collect()` leaves the GC heap permanently locked, so the shutdown flush dies with a
  misleading `MemoryError: ... heap is locked` on a heap that is mostly free. Measured at ~5% on
  both `v1.28.0` and `v1.29.0`, so not a version-bump regression. `run_generic_integration.py`
  calls `unwedge_heap_after_interrupt()` first at **two** sites: unconditionally at the top of
  `main()`'s own `finally:` block (which itself calls `flush_fram()`/`flush_scd30()`, so it needs
  the same guard) and again in the outer `except KeyboardInterrupt:` handler around
  `asyncio.run()` (reached instead of the first site whenever the interrupt lands while `main()`'s
  own coroutine is suspended rather than currently running, so it never enters that `finally:` at
  all) — full mechanism and why `gc.collect()` (not `micropython.heap_unlock()`) is the fix:
  SPECIFICATION.md Part F.6, whose amendment records that `toolchain/micropython_overrides.py`'s
  `unix_kbd_intr` override (Part B.14.1) has since closed the root SIGINT-safety gap this quirk
  came from — the calls stay wired in as defense in depth, not because the race is still reachable.
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
  (`asy_webserver_service.py`'s own hook), so it never needs keep-alive support. A connection
  refused at the webserver's ceiling is closed without a response, and the peer sees either an RST
  or a clean FIN (kernel TCP state `src/` does not choose): `parse_status_line(b"")` therefore raises
  `CeilingRefusedError`, an `OSError` subclass, so every caller's `except OSError` treats both shapes
  as the refusal they are, while a non-empty malformed status line still raises `ValueError`.
  `.json()` checks every body with `tests/_strict_json.py` first, since the interpreter's own
  `json.loads()` accepts a missing or stray comma the browser rejects (SPECIFICATION.md Part F.1);
  the import sits inside `.json()`, so `_http_client` itself imports without `tests/` on the path
  (as `segfault_stress_repro.py` needs); only `.json()` requires it.
- `launch.py` — standalone, `src/`-free CLI demo (`micropython digital_twin/launch.py [options]`):
  brings up the same bus wiring `sensortask_wozi.build_system()` uses and periodically drives one
  real bus-level read per sensor, a `WLAN.connect()` attempt, and WDT feeding. `--fault
  DEVICE:OP[:TIMES]` drives each chip fake's existing `FaultInjector`/`raise_on` API. Lighter and
  narrower in scope than `run_generic_integration.py` below, which boots the real object graph instead.
- `run_generic_integration.py` — boots **any** `sensortask_<device>` module (most usefully a
  freshly-`buildgen.generate.generate_device()`-generated one), for any real device, against a
  `--wiring-plan` JSON file, resolving the module via `__import__(--module)` instead of a static
  `import sensortask_wozi`. The single, fully-capable entry point every automated tier below drives
  now (SPECIFICATION.md Part L.4 retired the two former device-specific wrappers,
  `run_wozi_integration.py`/`run_dev_integration.py`, once this file gained their own soak/state-
  persistence machinery too and became CI's real per-device driver) — see "Booting a generated
  device" below for the general mechanism and "Swapping the twin in" for the default-device
  (`wozi`) walkthrough.

Every chip fake exposes a `.fault` (`FaultInjector`) surface for provoking a bus NAK/CRC-corruption/
timeout on demand — off/clean by default. Same surface also carries `inject_hang()`/`maybe_hang()`,
a real blocking `time.sleep()` for simulating a genuinely wedged bus (see "Automated CI suite"
below's `--hang` section) — distinct from a bounded, immediately-raised fault.

## Swapping the twin in for a Unix-port run

The generated `sensortask_wozi.py` (built fresh by `buildgen` from `devices/wozi.toml` — no static
copy is committed any more, SPECIFICATION.md Part L.2) needs **zero
twin-awareness** — no `if` branch anywhere distinguishing real hardware from simulated. The swap is
pure `MICROPYPATH` ordering, the same mechanism `tests/machine.py` already uses transparently for
the unit-test suite. `run_generic_integration.py` also drives real HTTP over real sockets against
the real `WebserverService` — never Microdot's `app.dispatch_request()` bypass, the same "full
HTTP" standard the real system meets. The dedicated entry point, `scripts/run_unix_port_integration.sh`,
does exactly this — for `wozi` by default, or any real device via `--device`:

```bash
scripts/run_unix_port_integration.sh                       # wozi: just launch + serve forever, no flags
scripts/run_unix_port_integration.sh --device dev           # dev, same shape
scripts/run_unix_port_integration.sh --fault sgp40:writeto  # manual fault-injection exploration
```

Under the hood (builds the toolchain, generates every device's `sensortask_<device>.py` +
`sensortask_<device>_wiring_plan.json` into `build/generated_src/` via
`scripts/_generate_sensortask_modules.py` — see "Booting a generated device" below for the general
mechanism this is built on — then builds the real website for the chosen device into
`frozen_modules/frozen_html.py` via `scripts/build_website.sh <device>`, matching what a real
deployed unit serves — then runs
`digital_twin/run_generic_integration.py --module sensortask_<device> --wiring-plan
build/generated_src/sensortask_<device>_wiring_plan.json --device <device>` — the real orchestrator,
not the generated boot entry directly, since it also needs to drive the soak/fault-injection/
`--duration`-forever logic around `<module>.main()`, not just block on it):

```bash
MICROPYPATH="build/generated_src:src:digital_twin:ext:frozen_modules:.frozen" <micropython-unix-port-binary> digital_twin/run_generic_integration.py --module sensortask_wozi --wiring-plan build/generated_src/sensortask_wozi_wiring_plan.json --device wozi [flags]
```

`build/generated_src` is listed first so `import sensortask_<device>` resolves to the freshly
buildgen-generated module, not any same-named file that might otherwise be found later on this
path — no static `src/sensortask_<device>.py` exists any more. `frozen_modules` is required here too
(see `SPECIFICATION.md` Part A.9 for the full pipeline) — the generated module does an
unconditional module-level `import frozen_html`, which resolves from that segment (see
`scripts/build_frozen_html.sh`'s own comment for why it can't be `.frozen` itself). Omitting it
fails the run at import time with `ImportError: no module named 'frozen_html'` before any twin code
ever runs. `digital_twin` sits between `src` and `frozen_modules`/`.frozen` — never together with
plain `tests` on the same `MICROPYPATH` (that would let `tests/machine.py`/`tests/network.py`/
`tests/neopixel.py` shadow this package's own same-named modules, or vice versa, depending on
ordering — the two are meant to never be on the same path at once). This is a **separate**
invocation from `scripts/test.sh`'s own `"build/generated_src:src:tests:frozen_modules:.frozen"` —
`scripts/run_unix_port_integration.sh` is not part of `scripts/test.sh`'s own default
`tests/test_*.py` glob loop (it can run forever in `--duration`-omitted/manual mode, which would
hang that loop if it were discovered there instead).

`digital_twin/run_generic_integration.py` reuses this file's own `launch.py`'s `parse_fault_spec()`/
`_parse_wifi_outcome()` directly (same device/op/wifi-outcome vocabulary). Unlike the two now-
retired device-specific wrappers, it defaults every state-persistence path to `None` (in-memory
only) rather than a fixed on-disk default — `scripts/run_unix_port_integration.sh` passes no
explicit `--fram-state-path`/`--scd30-state-path`, so a manual run through that script is
in-memory-only unless you pass them yourself; `scripts/_digital_twin_ci_suite.py` passes its own
fixed paths explicitly instead, since its own persistence-across-a-real-reboot checks depend on
them. Defaults to `--host localhost --port 8080` (browser-reachable). A bare, no-flags run just
launches the real object graph and serves forever, the same as a real rp2040 boot would. There is
no `--soak`/`--soak-cycles` flag any more — the automated HTTP+memory-trend soak check moved
host-side (SPECIFICATION.md's "Driver/DUT process separation" Part): the twin only exposes the one
piece of itself a host-side driver genuinely cannot get any other way, `gc.mem_free()`, via the
opt-in `--mem-sample-interval-ms N` flag (prints `MEM_SAMPLE <time.time()> <gc.mem_free()>` lines
to its own stdout on that cadence; unset by default, no sampling). See
`run_generic_integration.py`'s `parse_args()` for the full flag list, and
`scripts/_digital_twin_ci_suite.py`'s Run 11 (`_run_11_soak()`) for the actual soak methodology —
now a plain host-side HTTP-cycling loop parsing those `MEM_SAMPLE` lines back out of the twin's
captured log, the same pattern `_would_have_triggered_count()` already used for the watchdog
counter.

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

### Booting a generated device

`run_generic_integration.py` boots **any** device — not just wozi/dev — by consuming a Session-3
`buildgen.generate.generate_device()`-generated module directly, replacing
`configure_i2c_wiring("wozi"|"dev")`'s 2-profile enum with a wiring plan derived from that device's
own TOML (SPECIFICATION.md Part L.4 has the full design account). Two things have to
be produced **host-side, in a plain CPython process**, before this file's own MicroPython process can
even start — `buildgen` needs `tomllib`, which the MicroPython Unix port doesn't have:

```python
from pathlib import Path
import json
from buildgen.generate import generate_device
from buildgen.twin_wiring import compute_twin_wiring

generated = generate_device(Path("tests_scripts/buildgen_fixtures/novel_combo.toml"), Path("src"), Path("ext"))
# In tests_scripts/buildgen_fixtures/ for the two synthetic fixtures - devices/ for a real one.
Path("/tmp/twin_boot/sensortask_novel_combo.py").write_text(generated.module_source)
Path("/tmp/twin_boot/wiring_plan.json").write_text(json.dumps(compute_twin_wiring(generated.model)))
```

Then the MicroPython process, with the generated module's own directory placed **first** on
`MICROPYPATH` (so `import sensortask_novel_combo` resolves to the freshly-generated file, not any
same-named file that might otherwise be found elsewhere on this path — every real device is
generated exactly the same way now, including `wozi`/`dev`; no device has a hand-written
`sensortask_<device>.py` any more, SPECIFICATION.md Part L.2. `scripts/test.sh`/
`scripts/run_unix_port_integration.sh`/`scripts/run_digital_twin_ci.sh` all generate into the fixed
`build/generated_src/` directory via `scripts/_generate_sensortask_modules.py` rather than a fresh
temp directory per run, purely because those callers need `wozi`'s/`dev`'s modules to exist at a
predictable path before any test file runs; every other import the generated module itself needs,
e.g. `asy_i2c_driver`, still falls through to `src/`):

```bash
MICROPYPATH="/tmp/twin_boot:src:digital_twin:ext:.frozen" <micropython-unix-port-binary> \
    digital_twin/run_generic_integration.py --module sensortask_novel_combo \
    --wiring-plan /tmp/twin_boot/wiring_plan.json --device novel_combo --host 127.0.0.1 --port 8080
```

`tests_scripts/test_digital_twin_generated_boot.py` does exactly this (via `subprocess.Popen`, the
same pattern `scripts/_digital_twin_ci_suite.py` already uses for the hand-written wozi module) for
all 6 real devices (`wozi`, `dev`, `arzi`, `klkizi`, `grkizi`, `schlafzi`) plus both mandatory
synthetic fixtures (`novel_combo.toml`, `multi_instance.toml`), asserting a real `GET` against five
real REST endpoints all return 200 — the first point in this initiative a generated module has
actually been *run*, not just `ast.parse()`d.
`run_generic_integration.py`'s own fault/hang chip lookup (`_collect_chips()`) is the generalized
form of the retired `run_wozi_integration.py`'s/`run_dev_integration.py`'s hardcoded
`{"scd30": sensortask_wozi.i2c0._i2c.devices[0x61], ...}` dict — it walks the same wiring plan
`configure_wiring()` was given instead of a hand-picked `i2c0`/`i2c1` literal.

`launch.py` is left alone, for the same "different, static-demo use case" reason its own module
docstring already gives (a `src/`-free raw-bus-read demo, no `sensortask_*` import at all).
`run_wozi_integration.py`/`run_dev_integration.py` themselves are gone (SPECIFICATION.md Part L.4): once this file gained their own soak machinery too, both were pure duplication with
nothing left only they could do — `scripts/run_digital_twin_ci.sh`'s own per-device CI matrix and
every `tests/test_digital_twin_*.py` file that used to hardcode one of them now drive this file
instead, for every real device including wozi/dev.

`compute_twin_wiring()`'s plan carries a fourth, optional `"uart"` key (`{"initiator_var",
"responder_var"}`, the two generated Python variable names — `None`/absent for any device with no
`uart_link` instance, i.e. every device but `dev`) alongside `"buses"`/`"spi"`. Unlike those two,
this key is consumed *after* construction, not by `machine.configure_wiring()` itself:
`_wire_uart_crossover()` (called from `main()` right after `_wait_until_built()`) reads the two
already-built `UartLinkExerciser` instances off the booted module by name, joins their own
`asy_uart_driver.UART`'s underlying `machine.UART` fakes with the already-existing
`attach_crossover_jumper()`, and swaps in the returned bounded `LinkPoller`s — the exact generic,
wiring-plan-JSON-driven replacement for what `run_dev_integration.py` used to do by hand
(hardcoded to `sensortask_dev.uart0`/`uart1`) before it was retired above.

### FRAM persistence

The FRAM twin reads back exactly what was written, including across process restarts, but only
ever writes to disk on an **explicit** call — never automatically, to avoid unnecessary write
cycles on an SSD-hosted state file. Any entry point that boots a real `sensortask_<device>` object
graph against the twin (`digital_twin/run_generic_integration.py` is the real example) should:

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
same convention as FRAM. Both `digital_twin/run_generic_integration.py` and `digital_twin/launch.py`
default to in-memory-only for both FRAM/SCD30 (`--fram-state-path`/`--scd30-state-path` opt in
explicitly) — `scripts/_digital_twin_ci_suite.py` is the one caller that supplies real, fixed on-disk
paths, for its own persistence-across-a-real-reboot checks.

**Known limitation: single-chip globals.** `machine.py`'s `_current_scd30_chip`/`flush_scd30()`
(and the equivalent FRAM pair) each track exactly one chip instance. A device wired with more than
one SCD30 (both mandatory synthetic fixtures) only ever persists the *last-wired* instance's NVM
settings across a simulated reboot — every other twin behavior for such a device is unaffected. A
real multi-instance-persistence fix is unscoped; no real device needs it today.

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
job in `.github/workflows/ci.yml`, run once per real device via that job's own `strategy.matrix`
(SPECIFICATION.md Part L.4, mirroring `firmware-build-verify`'s own precedent). See
`SPECIFICATION.md`'s "Digital twin" section (Part A.10) for the full architectural account of what
it checks and why; this section is the practical how-to.

```bash
scripts/run_digital_twin_ci.sh          # wozi (default): clean -> build -> test, same as CI runs it
scripts/run_digital_twin_ci.sh dev      # any other real device: same 14-run suite, that device's own module
```

**Clean**: removes any leftover `digital_twin/fram_state.json`/`digital_twin/scd30_state.json`/
`digital_twin/config/` before starting — every run begins from a genuinely blank twin, not
whatever a previous local run or CI job happened to leave behind.

**Build**: builds the MicroPython Unix port (if not already cached at `$PICO_TOOLCHAIN_DIR`, same
convention as `scripts/test.sh`/`scripts/run_unix_port_integration.sh`), generates every real
device's own `sensortask_<device>.py` + wiring-plan JSON into `build/generated_src/`
(`scripts/_generate_sensortask_modules.py`), and the real website for the chosen device into
`frozen_modules/frozen_html.py` (`scripts/build_website.sh <device>`). Must succeed before any
test phase runs.

**Test**: hands off to `scripts/_digital_twin_ci_suite.py --device <device>`, a self-contained
`uv run` CPython script (stdlib-only — no `uv sync` needed) that drives
`digital_twin/run_generic_integration.py` as a real subprocess, over real HTTP/UDP (`http.client`/
`socket`, not `_http_client.py` — this script runs under CPython, not the twin's own MicroPython
process), through a sequence of real subprocess runs (14: runs 1-11 plus 5b/5c, sub-runs of run 5, and
11b; 5c itself spawns one process per bus-attached driver plus one, so the subprocess total is
device-dependent - 17 for `wozi`, 18 for `dev`, one more if run 11's soak retries) on a fixed port (`18080`, distinct from
the manual entry point's `8080` default, so both can run side by side without colliding). **The
whole 14-run sequence itself runs twice, not just once** — `main()` calls `run_suite()`
once at `--gc-threshold -1` (MicroPython's own real reactive-only default) and once at `32768` (the
project's chosen value, matching every real firmware boot), each pass writing its own subdirectory
under `digital_twin_ci_logs/` (`gc_threshold_neg1/`, `gc_threshold_32768/`). This is CLAUDE.md's/
SPECIFICATION.md Part I.4(e)'s standing rule applied to the *entire* suite, not just the soak
check (run 11, below) — every run in every pass must pass with zero `MemoryError`s (caught-and-
logged included) under the real default before the same suite is trusted under the chosen
threshold; `_close_log_and_check_memory_safety()` enforces this automatically on every subprocess
shutdown, not just run 11's own explicit trend check. The bus-fault matrix in runs 3/4 is derived
from that device's own real wiring plan, never a hardcoded driver list — a device without `bmp3xx`
(4 of the 6 real devices) simply never faults/checks it:

1. **Baseline boot** — walk every `GET` endpoint (`/measurements`, `/sensors`, `/networking`,
   `/system`, `/notification`, `/status`, `/`), then `PUT` a setting on each of
   `/system` (`DebugLevel=5`), `/notification` (`WarnCO2=1800`), `/sensors`
   (`SCD30.MeasInt=4`), `/networking` (`Hostname`), and `/status` (`ResetErrors`) — every route
   that accepts `PUT`. Shut down cleanly (`SIGINT`, matching the documented Ctrl-C path — a plain
   `SIGTERM`/`terminate()` would skip `run_generic_integration.py`'s own FRAM/SCD30 flush) and confirm
   the state files actually landed on disk.
2. **Real reboot, settings persistence** — a fresh subprocess against the *same* persisted state
   (no clean step in between — the whole point is testing what survives). Confirms every setting
   from run 1 is still there after a genuine process restart, and that the now-persisted
   `DebugLevel=5` produces real, multi-module verbose log output (`print_log.py`'s
   `print(name, *args)` convention — checked for known `_NAME` prefixes like `SYSTEM`/`SGP40`/
   `SCD30`/`WEBSERVER`) from the very start of boot, not just after a later `PUT`.
3. **Reboot with a sustained/high-repeat-count ("permanent") bus-fault matrix** — `--fault` on
   every bus-level error-counted module *this device actually has* at once (derived from its own
   real wiring plan, SPECIFICATION.md Part L.4 - `scd30:writeto:500`, `sgp40:writeto:500`,
   `fram:write:500` always, plus `bmp3xx:readfrom_mem:500` only for wozi/dev). Confirms every
   endpoint stays at `200` (graceful degradation under sustained failure, not just a single blip),
   every module's error counter climbs, and — via `run_generic_integration.py`'s own unconditional
   shutdown line — that the (simulated) watchdog **never** starves despite the sustained failures.
   This is the expected, correct outcome under the current architecture: `--fault` only ever
   produces bounded, immediately-raised `OSError`s, never an indefinite hang, so nothing here can
   actually block the event loop long enough to matter — see run 10 below for the one scenario that can.
4. **Reboot fault-free — what must reset, and that every faulted bus comes back** — whichever of
   SCD30/BMP3XX this device actually has must read back `0`, and every bus-attached sensor must
   produce real readings again after a run in which every bus, the FRAM included, was faulted
   throughout. **Not** because those two logs are in-memory: they are FRAM-backed like every other
   (`fram=fram` in the generated module), and this line claiming otherwise — citing a Part A.7 that
   never said it — was the same stale assumption the suite's own `_IN_MEMORY_ERROR_DRIVERS` carried
   until both were corrected. They read `0` for a narrower, situational reason: run 3 faults
   `fram:write` dead for its whole duration, so nothing either of them logged could ever reach the
   chip. That makes this a much weaker claim than "these never persist", and one nothing re-checks
   against a *healthy* chip (BACKLOG.md). FRAM itself is deliberately excluded from the sweep for a
   different reason: its dual-block+CRC self-healing read correctly detects run 3's torn chunk and
   logs a genuine, fresh entry on this run's own boot — the driver working as designed, not data
   surviving. This run also deliberately does **not** claim SGP40's
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
   satisfies all-or-nothing), which is exactly the hole the old run 4 check had.
   **The sweep is device-wide, not SGP40-only** (2026-09-18): every bus-fault-injectable driver
   this device wires gets its own chip-healthy bounded fault, each in its own process, chained onto
   the previous link's persisted state — so each link is itself a restore check and the final
   fault-free reboot then verifies every faulted row exactly. One fault per process rather than all
   at once is forced by the task-restart budget (SPECIFICATION.md Part C.4.1): three drivers
   faulted together exhaust it and the *device* reboots itself mid-run, which is not the commanded
   reboot this run exists to test. The final boot also sweeps every *other* registered error source for loss
   (`SYSTEM`/`NOTIFY`/`NTP`/`WEBSERVER`/`DNSSRV`, every `CFGMGR_*`, `dev`'s two `uart_link`
   instances): a fresh entry from that boot is legitimate, a missing one never is. `FRAM` is the
   one exemption — `AsyFramManager` builds a plain `PrintLogHistory`, since the store cannot
   persist its own failure history through itself, and
   `tests/_sensortask_scenarios.py` pins it as the only one from the real object graph.
   5c also confirms
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
8. **Reboot fault-free** — WIFI's own persistence-correctness check (FRAM-backed since WP1, same
   all-or-nothing abrupt-restart guarantee as SGP40's run 5b — restored count must be `0` or the
   full scripted-failure count, never partial), plus configures an unreachable NTP host
   (`192.0.2.1`, RFC 5737 TEST-NET-1) for run 9.
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
11. **Clean soak run — host-driven, not a twin-side `--soak` flag.** A fresh clean-boot twin
    subprocess is armed with `--mem-sample-interval-ms` only (no `--soak`/`--soak-cycles` — that
    flag doesn't exist any more); the *host* (this script's own `_run_11_soak()`, plain CPython)
    drives 100 warmup cycles then 20 measured cycles of the same
    `/measurements`/`/sensors`/`/networking`/`/system`/`/notification`/`/status`/`/` endpoint sweep
    directly over HTTP (100, not wozi's original 40 - `dev`'s two extra wired `uart_link` instances
    mean more one-time post-boot settling, confirmed directly, 2026-09-14: `gc.mem_free()` plateaus
    for both devices given enough idle wall-clock time after boot, `dev`'s own curve just needing
    roughly 2.5x wozi's own before it does; 100 gives every device real room to finish settling
    before the measured window starts), checks zero HTTP failures and `would_have_triggered_count ==
    0`, then parses
    the twin's own captured `MEM_SAMPLE <time.time()> <gc.mem_free()>` log lines (`gc.mem_free()`
    has no REST route and no other way out of the process — SPECIFICATION.md's "Driver/DUT process
    separation" Part) and computes the same early-quarter-vs-late-quarter memory-trend check the
    twin used to run on itself (`_mem_trend()`, unit-tested directly in
    `tests_scripts/test_digital_twin_ci_suite_soak.py` — no live subprocess needed for that half).
    Run 11 gets its real-default and chosen-threshold passes from the whole suite running once per
    `gc_threshold`, like every run. The check is host-side because an in-DUT loop contaminates the
    resources it measures (SPECIFICATION.md's "Driver/DUT process separation" Part; no `gc.collect()`
    propping up a result, Part I.4(e)). A CI `MemoryError` here (`allocating ~6100 bytes` on
    `GET /status`) is the standing example of the owner's rule that a threshold is never the fix: its
    root cause was the client's growth-by-concatenation reads, fixed by `_http_client.py`'s
    `_read_exact()`/`_read_until_close()` (one right-sized buffer per `fetch()`).

    **Run 11b — the full connection ceiling under real simultaneous load** (`_run_11b_full_ceiling_
    concurrency()`). A fresh twin; the host reads the device's own ceiling through buildgen's
    `device_max_connections()` (`devices/<device>.toml`, else `src/`'s default) and fires exactly
    that many simultaneous GETs cycling over `/sensors`, `/status`, `/measurements`, `/networking` and
    `/system`, three rounds, from CPython threads on
    a barrier with one real socket each — every one must be served `200` with a body that parses as
    a JSON object, the twin must still serve afterwards and shut down
    cleanly, and the suite's own no-`MemoryError` log check applies at both thresholds. A 1 s settle
    precedes **every** round, the first included: a slot is released only after the close is awaited
    (SPECIFICATION.md H.7.1), and the readiness probe's own connection is still counted when round 0
    would otherwise start. Driven from a separate process because an in-process client measures its
    own buffers (SPECIFICATION.md Part E.9).

Each run's subprocess stdout/stderr is captured to `digital_twin_ci_logs/run<N>_*.log` (gitignored;
uploaded as a CI build artifact via the `digital-twin-e2e` job's own `if: always()` upload step, so
a failure's full boot log is inspectable from the Actions run itself, not just the pass/fail
summary). The suite exits non-zero if any check fails, failing the CI job.

### What `run_generic_integration.py` keeps in-process, and why

Almost every request-driving and response-observing job moved host-side (SPECIFICATION.md's
"Driver/DUT process separation"). Two things could not, and both are deliberate:

- **`--mem-sample-interval-ms`** — `gc.mem_free()` exists only inside this process's own heap and
  deliberately has no REST route. It samples on a fixed wall-clock timer rather than once per
  host-driven cycle, because the host has no way to signal "a cycle finished" without adding the
  very channel this design avoids, and a denser stream is at least as sensitive to a real trend.
  Each line is timestamped off the same wall clock the host reads, so the host selects the samples
  inside its own window — the same way it scrapes the watchdog counter from stdout, never by
  calling back in. Its `gc.collect()` is measurement instrumentation under Part I.4(e)'s narrow
  exception, not a pressure workaround: on a fixed timer, reaching no webserver or driver, it
  cannot mask a real `MemoryError`. Verified by removing it (2026-09-14) — the trend check got
  *worse*, swinging min=99808/max=1347104 on a healthy run, a false positive from incidental
  reactive-GC timing.
- **The `wire_log` clearer.** `UARTLink.wire_log` is unbounded by design, so a unit test with
  direct object access can assert exactly what crossed the wire, and every such test clears it
  itself. This process has no such access — it boots the twin as a subprocess and never reads the
  log — so left alone it grows for as long as the link carries traffic, the exerciser firing every
  second regardless of HTTP activity. That is what made Run 11's memory trend fail for `dev`, the
  only device with a wired pair, while `wozi` stayed flat. Clearing it changes nothing
  over-the-wire: nothing in the request path or `asy_uart_comm.py` ever reads it back.

### Run 11's two calibrated numbers

**`_SOAK_WARMUP_CYCLES = 100`, not wozi's original 40.** `dev`'s two extra `uart_link` instances
mean more one-time post-boot settling — module-level caches and config-derived structures
populated once, the same asymptotically-decaying-then-flat shape wozi's boot shows on a smaller
scale, not an unbounded leak. Confirmed 2026-09-14: `gc.mem_free()` plateaus for both devices given
enough idle wall clock, wozi's curve flattening well inside 40 cycles' worth and dev's needing
roughly 2.5x that, reproduced with the UART tasks fully disabled — so it is settling proportional
to module count, not UART traffic. 100 gives every device room to finish before the measured
window starts.

**The memory-trend tolerance is self-calibrating, and a scaling law is why.** The original
calibration — five 100-cycle soaks, 25-sample quarters, trend deltas of +2623, +796, -410, +1729,
-116 bytes — gave a flat 8192-byte tolerance, about 3.1x the worst magnitude and scattered around
zero. Porting that forward as `8192 * sqrt(25/quarter)` assumed a trend's standard error shrinks
with `1/sqrt(quarter_size)`, as it would for independent samples. It does not, and CI kept tripping
it on a different device each time.

Measured directly: sliding a 206-sample window across a region 20+ seconds past all settling and
visibly flat in the raw trace, the trend statistic's own standard deviation came in at 1496-1964
bytes — 3.4-4.5x what the formula predicts at this quarter size, because consecutive 25ms
`gc.mem_free()` samples are heavily autocorrelated. More samples buy far less noise reduction than
independent-sample statistics assume, so the formula tightened fastest exactly where it had to be
loosest.

`_mem_trend()` now measures the spread *within* each quarter, decoupled from the early-vs-late
difference the trend itself measures — so a genuine leak's decline cannot inflate the tolerance
meant to catch it — and sets the tolerance as a generous multiple of that. Self-calibrating per
device, run and quarter size, with no constant to re-derive, and it covers the observed worst case
(5889 bytes) with room left.

### Two suite-table subtleties worth reading before changing one

**`_NO_PERSIST_WHEN_FRAM_FAULTED` is not "these logs are in-memory".** It was named and described
that way once and the claim was false: SCD30, SGP40 and BMP3XX are all FRAM-backed. What makes
SCD30/BMP3XX reset to 0 in Run 3 is situational — that run faults `fram:write`, so the chip is dead
for its whole duration and nothing they logged could reach it. The property is "with FRAM faulted,
nothing persisted", a much weaker claim, which is why Run 5b/5c exist to make the chip-healthy one
for every bus-attached driver the device wires.

`fram` is deliberately absent from that set even though its own log genuinely is in-memory-only.
Run 3's `fram:write` fault can leave a chunk's status byte stuck mid-write, and the dual-block+CRC
self-healing read every restore goes through correctly detects and logs that as a fresh FRAM-level
entry on Run 4's next boot — confirmed directly, the same history reappearing on a fresh process.
That is not old data surviving (BMP3XX/SCD30 correctly show 0) and not a defect: self-healing
detecting real torn state is the driver working.

**`_RESET_ERRORS_TIMEOUT_S` is derived, not chosen.** `PUT /status {"ResetErrors": true}` resets
every registered source in turn, and each FRAM-backed one pays a real chunk write — 10+ of them on
`dev`, which is why it exceeds `_http()`'s plain 5s default. The first two CI runs on `dev` failed
on exactly that one call, at both gc thresholds, and nothing else.

The value sits just **above** the server's own `outer_cap_s`, deliberately: below it a legitimate
slow reset reads as a client timeout, and at or above it the client timeout can never fire at all,
since the server aborts first — so the suite observes the server's own diagnosable abort instead of
a bare "something took too long". The earlier flat 20.0 was inert for that reason, and also sat
above the 15s the real web UI gives up at. What is still missing is an elapsed-time budget well
below the cap: this is a backstop, not a performance assertion, and the suite is blind to the whole
5-15s band (BACKLOG item 24, which carries the real-hardware measurements).

### `--hang` (real bus hangs, distinct from `--fault`)

`digital_twin/launch.py --hang DEVICE:OP:SECONDS[:TIMES]` (also accepted by
`digital_twin/run_generic_integration.py`) queues a real, blocking `time.sleep(SECONDS)` before the
next `TIMES` (default 1) calls to that op proceed — `sgp40`/`scd30` (`writeto`/`readfrom_into`),
`bmp3xx` (`readfrom_mem`/`writeto_mem`), `fram` (`write`/`readinto`). Unlike `--fault` (a bounded,
immediately-raised `OSError` — the driver's own normal error path), this genuinely freezes the
whole interpreter for real wall-clock seconds, the only way to simulate a truly wedged bus rather
than a bus that merely errors. `wlan` has no `--hang` vocabulary — its faults are a synchronous
`raise_on[]` check, not a bus transaction with a real HAL call underneath.

### `Isl29125Chip.configure_fault()` (a persistent behaviour, not a queued exception)

The one fault mode that is neither a bounded `OSError` nor a freeze: with
`configure_fault("isl29125:int_stuck_high")` the bus keeps answering and conversions keep happening,
but the INT line never moves. That is the silent failure the driver's periodic range evaluation
exists to survive, and nothing in `_fault_injection.py` can express it, so it lives on the chip
itself rather than behind a `--fault`/`--hang` flag. An unknown mode raises rather than no-opping.
Reached from a test holding the chip object (`tests/test_digital_twin_isl29125*.py`); `dev` is the
only device that wires the part at all.

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

### `_http_client.py`'s read paths (why neither one uses `Stream.read()`)

The twin's own HTTP client reads bodies two ways, and both avoid the obvious call for the same
reason: `extmod/asyncio/stream.py`'s `Stream.readexactly()` and `Stream.read(-1)` both accumulate
with `r += r2` on every partial read — a fresh, larger contiguous object per read, the previous one
abandoned. Over a several-KB body arriving in several TCP reads that is several progressively
bigger allocate-copy-discard cycles per fetch, which is exactly what fragments this heap under
repeated soak cycles. Confirmed by reading the pinned interpreter's own source, not inferred.

- **Sized (`Content-Length`) →** one right-sized `bytearray` filled through `Stream.readinto()`,
  which does a single non-accumulating read per call and so has to be looped. One allocation per
  fetch, made once the final size is known. **`readinto()` can return `None`** — poll said
  readable, the read still came back empty, the race `Stream.read()`'s own retry loop exists to
  ride out. It reaches this caller directly and must be retried; only a real `0` means the peer
  closed. Conflating the two reads as an intermittent, environment-dependent false `EOFError`
  under scheduling jitter, which a quiet sandbox rarely reproduces. This file's first version did.
- **Unsized (`GET /`, the frozen website) →** `ext/microdot.py`'s `send_file()` hands the response
  a raw file stream, so `Response.complete()`'s automatic `Content-Length` never applies and
  `Connection: close` plus EOF is how the response ends. This is the live path for that route, not
  a rare fallback. Fixed-size chunks collected in a list and joined once, rather than one bigger
  contiguous copy per read.

The final `b"".join(chunks)` is still one whole-body allocation (~7.5KB for the largest device's
frozen website). That is fine for a caller that needs the bytes, but **no real device ever holds
one**: a browser assembles the body from Microdot's own 1KB `send_file_buffer_size` chunks over the
wire. A caller that only checks `status_code` takes `_drain_until_close()` instead — SPECIFICATION.md
Part I.4(g), relieve the pressure at its source rather than paper over an avoidable allocation with
a GC-policy change. No explicit `gc.collect()` belongs anywhere near this: `py/gc.c`'s `gc_alloc()`
already runs a full collect-and-retry before it ever raises `MemoryError`, so a stale response's
garbage is reclaimed exactly when an allocation needs the room.

That distinction was found by a real CI failure, and is the reason `_drain_until_close()` exists:
`dev`'s own frozen website (7579 bytes, 168-483 bytes larger than the other five devices') tipped
that one allocation over a fragmented-heap edge at `gc.threshold(-1)` where the slightly smaller
sites did not. The fix was calling the draining sibling from the hot soak loop — not shrinking the
site, and not reaching for a threshold.

### `_unix_port_udp_addr_shim.py` (real UDP round trips under the Unix port)

`patch_asy_udp_socket_for_unix_port()` — called once, early, as `run_generic_integration.py`'s own
`main()` does (right after `prewarm_poll_set()`, before anything constructs a socket) — also called
the same way, module-level before `import sensortask_wozi`, by `tests/
test_digital_twin_sensortask_integration.py` (its own hotspot/DNS section drives a genuine UDP round
trip against the real `captive_dns.py` `DNSServer` the same way `run_generic_integration.py`'s run 7
does — see that test's own comment). That same test also needs the real privileged port 53 itself
to actually be bindable, same as run 7 — `scripts/test.sh` now grants the built interpreter binary
`CAP_NET_BIND_SERVICE` unconditionally (mirroring `scripts/run_digital_twin_ci.sh`'s own identical
grant, see that script's own comment for the full mechanism/rationale), not just
`run_digital_twin_ci.sh`, since this test now runs as part of the plain unit-tests suite too, not
only the separate digital-twin-e2e job.

> **Two different faults produce the identical message** `"real hotspot activation never started the
> real DNSServer task"`, and telling them apart costs one command. Running that file directly with
> the interpreter instead of through `scripts/test.sh` skips the `setcap` grant, so `DNSServer`'s
> `bind()` to port 53 fails and the task never starts — check `getcap` on the binary before drawing
> any conclusion from a standalone run. The other cause is plain CPU starvation exhausting the
> assertion's own budget (README.md's `TEST_PARALLELISM` entry), which needs no missing capability at all. Neither is a
> bug in the code under test.

Works
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
   and add a new `_<name>_chip.py` alongside `_scd30_chip.py`/`_sgp40_chip.py`/`_bmp3xx_chip.py`/
   `_isl29125_chip.py`, matching their established shape:
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
2. Wire it into `machine.py`'s `_build_i2c_chip()`: add an `if driver == "<name>":` branch
   constructing the new chip fake (the wiring plan itself — which bus, which address — is already
   generic and needs no per-chip code; see "Booting a generated device" above). If the chip's real
   I2C address is hardwired (no TOML `address` field — `buildgen.buildspec.FIXED_ADDRESS_DRIVERS`),
   add it to `buildgen/twin_wiring.py`'s own `FIXED_ADDRESSES` table too, matching the real driver's
   own hardcoded default address. Nothing else to wire by hand for `"wozi"`/`"dev"`:
   `configure_i2c_wiring()` loads its plan from `devices/wozi.toml`/`dev.toml` via generation, so a
   driver promoted for either device is picked up automatically the next time
   `scripts/_generate_sensortask_modules.py` runs.
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

## Harness pitfalls

- **Unix-port facts that break a harness written by habit** (confirmed against the pinned build):
  no `socket.getsockname()`; `getaddrinfo()` returns a packed `sockaddr`; `asyncio` offers `Lock`
  and `Event` but no `Semaphore`; `os.environ` is missing, so read `os.getenv()`; and
  `micropython.mem_info()` with any argument prints the full block map.

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
  automated test tiers can't (a genuine repro crashes the whole interpreter process). Deliberately
  kept hardcoded to `sensortask_wozi`, not generalized to `run_generic_integration.py`'s own
  `--module`/`--wiring-plan` mechanism (SPECIFICATION.md Part L.4): its target bug is a
  device-independent MicroPython Unix-port interpreter bug, unrelated to any device's own sensor
  wiring, and it's never invoked by `scripts/run_digital_twin_ci.sh` or any `tests/test_*.py` file
  — so no CI-coverage concern applies to it. Run
  manually, same `MICROPYPATH` as `run_generic_integration.py`. Its target bug is root-caused and
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
