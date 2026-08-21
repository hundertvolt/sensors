# `digital_twin/` — hardware simulator for the wozi prototype

A set of fake `machine`/`network`/`neopixel` modules, sitting at the same raw I2C/SPI
bus-transaction mocking boundary `tests/machine.py` establishes for unit tests, but built for a
different purpose: real-time-firing `Timer`s and randomized-but-plausible sensor values, so the full
assembled `src/sensortask_wozi.py` prototype can run under the real MicroPython Unix-port
interpreter and behave like it's attached to real hardware — not just satisfy a hand-driven test
double. See SPECIFICATION.md Part A.10 for how this fits into the rest of the architecture, and
Part C.11 point 9 for the per-driver "add a matching chip fake" requirement.

**Not `tests/machine.py`, does not import it, and is never imported by anything in `tests/`.**
Kept completely separate so nothing here can accidentally affect the deterministic unit-test suite
`scripts/test.sh` runs by default (`MICROPYPATH="src:tests:frozen_modules:.frozen"`).

## What's here

- `machine.py` — `Pin`/`I2C`/`SPI`/`Timer`/`WDT`/`RTC`. `Timer` fires for real on a wall-clock
  schedule via an internal `asyncio` task, not `_thread` (upstream's own `_thread.rst` docs state
  outright that it "is highly experimental and its API is not yet fully settled" — not a fit for
  load-bearing behavior here, and every real `Timer` callback in this codebase is already trivial
  enough that true preemption buys nothing). `I2C`/`SPI` wire the real "wozi" variant's bus layout
  exactly, mirroring `sensortask_wozi.build_system()`'s own construction: `I2C(0, ...)` carries the SCD30 at `0x61`, `I2C(1, ...)`
  carries the SGP40 at `0x59` and BMP3xx at `0x77`, `SPI(0, ...)` carries the FRAM chip. Any other
  address NAKs — a real bus with a fixed, known set of devices on it, not an unbounded fixture. `Pin`
  identity is shared by id (`Pin(8)` constructed twice returns the same underlying pin state), since
  a real GPIO pin is one fixed physical resource and chip fakes and drivers may each construct their
  own `Pin` object for the same id.
- `_sgp40_chip.py` / `_scd30_chip.py` / `_bmp3xx_chip.py` — one chip fake per sensor, each verified
  against its own datasheet in `datasheets/` for the raw transaction shape and sensible value
  ranges. `_scd30_chip.py`'s RDY pin fires a real rising edge on its own internal measurement-
  interval cadence, exercising the real driver's normal IRQ-driven path. `_scd30_chip.py` also has
  explicit `save_state()`/on-construction load JSON persistence for its five NVM-backed settings
  (see "SCD30 persistence" below) — the same `state_path` design `_fram_chip.py` uses, applied to a
  handful of scalars instead of the whole memory image.
- `_fram_chip.py` — the MB85RS64V FRAM chip's SPI opcode protocol (WREN/WRDI/RDSR/WRSR/READ/WRITE/
  RDID), plus explicit `save_state()`/on-construction load JSON persistence (see "FRAM persistence"
  below).
- `unix_port_poll_prewarm.py` — a workaround for a confirmed, real dangling-pointer bug in the
  pinned MicroPython v1.28.0 Unix port's `extmod/modselect.c` (see "Known gaps / follow-ups" below
  for the full account). Called as the first statement of `run_wozi_integration.py`'s and
  `segfault_stress_repro.py`'s own `main()`, before anything else in the process registers a poll
  object.
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
  constructs a socket from that value.
- `_http_client.py` — minimal hand-rolled HTTP/1.1 client over `asyncio.open_connection()`, used to
  drive real requests against `WebserverService` in Unix-port integration runs (no HTTP client
  library is frozen into the pinned Unix-port build). Every response it sees is `Connection: close`
  (`asy_webserver_service.py`'s own hook), so it never needs keep-alive support.
- `launch.py` — standalone, `src/`-free CLI demo (`micropython digital_twin/launch.py [options]`):
  brings up the same bus wiring `sensortask_wozi.build_system()` uses and periodically drives one
  real bus-level read per sensor, a `WLAN.connect()` attempt, and WDT feeding. `--fault
  DEVICE:OP[:TIMES]` drives each chip fake's existing `FaultInjector`/`raise_on` API. Lighter and
  narrower in scope than `run_wozi_integration.py` below, which boots the real object graph instead.

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

Under the hood (builds the toolchain + `frozen_modules/frozen_html.py` the same way `scripts/
test.sh` does, then runs `digital_twin/run_wozi_integration.py` — the real orchestrator, not
`boot_entry/wozi_boot.py` directly, since it also needs to drive the soak/fault-injection/
`--duration`-forever logic around `sensortask_wozi.main()`, not just block on it):

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
convention as `scripts/test.sh`/`scripts/run_unix_port_integration.sh`) and
`frozen_modules/frozen_html.py`. Must succeed before any test phase runs.

**Test**: hands off to `scripts/_digital_twin_ci_suite.py`, a self-contained `uv run` CPython
script (stdlib-only — no `uv sync` needed) that drives `digital_twin/run_wozi_integration.py` as a
real subprocess, over real HTTP/UDP (`http.client`/`socket`, not `_http_client.py` — this script
runs under CPython, not the twin's own MicroPython process), through eleven real, sequential
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
4. **Reboot fault-free — bus-fault persistence-correctness sweep** — checks *both* directions for
   every module run 3 faulted: SGP40's count should have persisted (FRAM-backed,
   `PrintLogHistoryStore` — see `src/print_log.py`); SCD30/BMP3XX/FRAM's counts should have reset to
   `0` (in-memory-only by design — SPECIFICATION.md Part A.7). A bug in either direction is real and
   would be caught here.
5. **Clean boot, a small *bounded* fault** (`sgp40:writeto:3`, not sustained) — the other half of
   the self-healing story run 3 alone can't show: not just "doesn't crash while still broken," but
   "comes back once the fault clears." Confirms the real error count stops climbing once the 3
   queued failures are exhausted (a driver's own "recovered" notice is itself logged as a warning,
   not an error — this suite counts `"E"`-typed history entries specifically, not the raw combined
   counter, to avoid mistaking a recovery notice for a new failure) and that measurements resume.
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

### `_unix_port_udp_addr_shim.py` (real UDP round trips under the Unix port)

`patch_asy_udp_socket_for_unix_port()` — called once, early, as `run_wozi_integration.py`'s own
`main()` does (right after `prewarm_poll_set()`, before anything constructs a socket) — works
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
   bus id (`0` or `1`) the real wiring puts it on (cross-check `src/sensortask_wozi.py`'s
   `build_system()` for the real pin/address assignment), or add a new `if id == N:` branch if it
   lands on a bus id neither SCD30 nor SGP40/BMP3xx already use.
3. Add `tests/test_digital_twin_<name>.py` — deterministic unit tests of the chip fake in isolation
   (no real `machine.I2C` involved, matching every existing `tests/test_digital_twin_{sgp40,scd30,
   bmp3xx}.py`) — then extend `tests/test_digital_twin_machine.py`'s own dispatch tests if the new
   chip shares a bus id those tests already probe.
4. Update this file's "What's here" list (the bus-wiring bullet above) to mention the new chip, and
   consider whether `digital_twin/launch.py`'s own `_sensor_loop()`/`_FAULT_DEVICE_OPS` should read
   from it too.

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
  MicroPython v1.28.0 Unix port — growing the shared asyncio poller's `pollfds` array (needed once
  concurrently-registered fds cross a multiple of 4) unconditionally repoints every
  already-registered poll object's `pollfd` field at the new buffer, including non-fd poll objects
  whose `pollfd` is legitimately `NULL`, corrupting it into a small garbage pointer the next
  `poll()` call dereferences. Confirmed compiled out of real rp2 firmware entirely
  (`MICROPY_PY_SELECT_POSIX_OPTIMISATIONS`, the macro gating this code path, defaults to 0 and is
  only turned on by the Unix port's own config — rp2 defines no override, and its non-optimized
  poll object has no `pollfd` field or array to grow at all) — real hardware was never affected.
  Fixed by `unix_port_poll_prewarm.py` (see "What's here" above and that module's own comments for
  the pre-warming mechanism itself).
