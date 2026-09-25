# Harvest — TWIN: Digital twin

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 25, INVAR 50, MIRROR 21, LIMIT 150, RISK 4, ASSUME 75, PLATFORM 3, WORKAROUND 20, SUPPRESS 11, TODO 3, OPENQ 1, DRIFT 4, NOTE 1 — 368 items.


## src/asy_uart_link_driver.py

- **TWIN.N001** MIRROR · `src/asy_uart_link_driver.py:57-60` — "public: the digital twin reaches the
  underlying machine fake through it... see digital_twin/run_generic_integration.py's
  _wire_uart_crossover()" — Public attribute shape relied on by
  `digital_twin/run_generic_integration.py:262-282` · [H02]

## tests/_digital_twin_construction_scenarios.py

- **TWIN.N002** WORKAROUND · `tests/_digital_twin_construction_scenarios.py:16-18` — "the Unix port's
  pollfds growth corrupts non-fd entries already in it, a segfault rather than a failure" —
  `prewarm_poll_set()` must run before any poll registration; Unix-port defect; removal trigger none
  stated · related: TWIN.T07 · [H03]
- **TWIN.N003** WORKAROUND · `tests/_digital_twin_construction_scenarios.py:20-23` — "Must run before
  AsyUDPSocket is constructed" — `patch_asy_udp_socket_for_unix_port()` import-order obligation,
  duplicated from `test_digital_twin_sensortask_integration.py`; removal trigger none stated · related:
  TWIN.T07 · [H03]

## tests/_webserver_concurrency_scenarios.py

- **TWIN.N004** INVAR · `tests/_webserver_concurrency_scenarios.py:96-98` — "every twin I2C/SPI
  construction reads the shared machine._wiring_plan global (Part L.4), where the last call before
  construction wins" — `configure_wiring()` must immediately precede each `build_system()` in a
  multi-device process · [H03]

## digital_twin/README.md

- **TWIN.N005** SETTLED · `digital_twin/README.md:12-14` — "Not `tests/machine.py`, does not import it,
  and is never imported by anything in `tests/`." — Twin/mock separation is a stated design rule;
  auditor should check no `tests/` module imports twin code except via the documented per-file
  `sys.path.insert` · related: TEST.T05 · [H06]
- **TWIN.N006** SETTLED · `digital_twin/README.md:18-22` — "`Timer` fires for real on a wall-clock
  schedule via an internal `asyncio` task, not `_thread`" — Deliberate choice; Timer callbacks never
  pre-empt running code, so soft-IRQ/soft-callback-drop and preemption semantics of the real rp2 Timer
  are unmodelled · covered-by: TWIN.T02 · [H06]
- **TWIN.N007** ASSUME · `digital_twin/README.md:20-22` — "every real `Timer` callback in this codebase
  is already trivial enough that true preemption buys nothing" — Justification rests on all callbacks
  staying trivial; unverified going forward · related: TWIN.T09 · [H06]
- **TWIN.N008** INVAR · `digital_twin/README.md:22-25` — "`configure_wiring(plan)`, called once before
  any bus is constructed" — Ordering contract upheld by caller discipline · related: TWIN.T12 · [H06]
- **TWIN.N009** LIMIT · `digital_twin/README.md:26-30` — "default `\"wozi\"` if neither
  `configure_wiring()`/`configure_i2c_wiring()` is ever called" — A caller that forgets wiring silently
  gets wozi's bus layout, not an error · related: TWIN.T12 · [H06]
- **TWIN.N010** MIRROR · `digital_twin/README.md:30-35` — "`\"wozi\"` mirrors
  `sensortask_wozi.build_system()`'s own construction ... `\"dev\"` mirrors ... reversed layout" — Twin
  wiring profiles mirror each generated device's bus/address/IRQ-pin layout (SCD30 IRQ pin 8 vs 11); now
  derived from wiring-plan JSON · related: TWIN.T12 · [H06]
- **TWIN.N011** LIMIT · `digital_twin/README.md:35-36` — "Any other address NAKs — a real bus with a
  fixed, known set of devices on it" — Twin buses model only the wired devices; unexpected-address
  behaviour is a NAK, not real-bus electrical behaviour · [H06]
- **TWIN.N012** INVAR · `digital_twin/README.md:36-41` — "the chip fake's own `rdy_pin` must be
  constructed with the same id the real driver's own IRQ `Pin` uses, or a simulated edge never reaches
  its handler" — Pin-id agreement between chip fake and driver is a convention; a mismatch silently
  loses IRQ edges · [H06]
- **TWIN.N013** LIMIT · `digital_twin/README.md:41-45` — "`I2C.log`/`SPI.log` (an ad-hoc introspection
  aid nothing in `tests/`/`digital_twin/` reads today) is bounded to the most recent 200 entries" —
  Unread introspection log, bounded after a real MemoryError leak; history truncation to 200 entries ·
  [H06] ⟨quote not matched at the anchor⟩
- **TWIN.N014** ASSUME · `digital_twin/README.md:46-48` — "one chip fake per sensor, each verified
  against its own datasheet in `datasheets/`" — Fidelity claim for all four fakes; only ISL29125 has a
  conformance probe · related: TWIN.T01, TEST.S20 · [H06]
- **TWIN.N015** LIMIT · `digital_twin/README.md:48-50` — "`_scd30_chip.py`'s RDY pin fires a real rising
  edge on its own internal measurement-interval cadence" — RDY timing is a twin-internal cadence, not
  the chip's real conversion timing · related: TWIN.T01 · [H06]
- **TWIN.N016** LIMIT · `digital_twin/README.md:50-52` — "explicit `save_state()`/on-construction load
  JSON persistence for its five NVM-backed settings" — SCD30 fake persists only the five NVM scalars ·
  related: TWIN.T10 · [H06]
- **TWIN.N017** PLATFORM · `digital_twin/README.md:53-68` — "`BOUTF` being read-to-clear contradicts the
  datasheet and was measured on real silicon" — ISL29125 fake encodes silicon-measured behaviours
  (destructive 0x08 read, BOUTF after reset, address-pointer walk to 0x0E, persistence counter reset on
  RGBTHF clear, active-low INT) that diverge from the datasheet (M.1.2/M.1.4) · related: TWIN.T11 ·
  [H06]
- **TWIN.N018** ASSUME · `digital_twin/README.md:53-56` — "high range's full scale is a deliberately
  non-nominal multiple of its low range's" — Deliberate fake non-nominal ratio so calibration has
  something to converge on; tests depend on it · [H06]
- **TWIN.N019** WORKAROUND · `digital_twin/README.md:76-88` — "a workaround for a confirmed, real
  dangling-pointer bug in the pinned MicroPython Unix port's `extmod/modselect.c`" — Poll-prewarm
  workaround for an upstream Unix-port bug; removal trigger: none stated (only "file upstream",
  :918-919) · covered-by: TWIN.T07 · [H06]
- **TWIN.N020** INVAR · `digital_twin/README.md:79-84` — "Called as the first statement ... and at
  import by every `tests/` entry point that boots a `sensortask_*` module with real sockets ... before
  anything else in the process registers a poll object" — Call-order contract enforced only by
  convention in each entry point · related: TWIN.T07 · [H06]
- **TWIN.N021** ASSUME · `digital_twin/README.md:83-88` — "scans upward from port 17400 across a 64-port
  window ... (28 of 30 concurrent prewarms; 0 of 30 with the scan), and port 0 is no alternative since
  this port has no `getsockname()`" — Single dated measurement; the 64-port window bounds concurrency
  (TEST_PARALLELISM) · related: TEST.S21 · [H06]
- **TWIN.N022** WORKAROUND · `digital_twin/README.md:89-101` — "the calls stay wired in as defense in
  depth, not because the race is still reachable" — gc-unwedge workaround for SIGINT-in-gc_collect heap
  lock; root cause closed by `unix_kbd_intr` override (B.14.1); removal trigger: none stated ·
  covered-by: TWIN.T07 · [H06]
- **TWIN.N023** ASSUME · `digital_twin/README.md:91-92` — "Measured at ~5% on both `v1.28.0` and
  `v1.29.0`" — Dated measurement on the Unix port · [H06]
- **TWIN.N024** INVAR · `digital_twin/README.md:92-98` — "calls `unwedge_heap_after_interrupt()` first
  at **two** sites" — Both the `finally:` and the outer `except KeyboardInterrupt:` must call it first;
  convention only · related: TWIN.T07 · [H06]
- **TWIN.N025** MIRROR · `digital_twin/README.md:102-104` — "a generic op-keyed fault-injection queue,
  mirroring `tests/machine.py`'s own `inject_fault()`/`_maybe_raise()` convention" — Fault API mirror
  between twin and mock tier · related: TEST.T05 · [H06]
- **TWIN.N026** MIRROR · `digital_twin/README.md:105-106` — "independent, deliberately duplicated (not
  reused) copies of `tests/network.py`/`tests/neopixel.py`'s own fakes" — Deliberate duplication; the
  two copies can drift · related: TWIN.T12, TEST.T05 · [H06]
- **TWIN.N027** LIMIT · `digital_twin/README.md:109-112` — "It only fakes *connection state* — actual
  traffic (NTP/DNS/HTTP) goes through the real `socket` module ... reaches the real network" — Network
  fidelity: host Linux stack and the real internet stand in for CYW43/lwIP; no lwIP limits modelled ·
  covered-by: TWIN.T08 · [H06]
- **TWIN.N028** ASSUME · `digital_twin/README.md:112-114` — "`ifconfig()` reports a plausible static
  address ... harmless, since nothing in `src/` constructs a socket from that value" —
  Unverified-going-forward assumption about `src/` usage of `ifconfig()` · [H06]
- **TWIN.N029** LIMIT · `digital_twin/README.md:114-116` — "**AP-mode fidelity gap**: ...
  `ifconfig()[0]` reads `\"0.0.0.0\"` in AP mode instead of a realistic address" — Documented AP-mode
  infidelity · related: TWIN.T03, TWIN.S05 · [H06]
- **TWIN.N030** ASSUME · `digital_twin/README.md:119-120` — "Every response it sees is `Connection: close`
  ... so it never needs keep-alive support" — Twin HTTP client relies on the server hook always closing;
  keep-alive paths untested at twin tier · related: TEST.T17 · [H06]
- **TWIN.N031** RISK · `digital_twin/README.md:120-124` — "`parse_status_line(b\"\")` therefore raises
  `CeilingRefusedError`, an `OSError` subclass" — Any empty response (not only a ceiling refusal) is
  classified as a refusal by every caller's `except OSError` · related: TEST.T17 · [H06]
- **TWIN.N032** INVAR · `digital_twin/README.md:125-128` — "the import sits inside `.json()`, so
  `_http_client` itself imports without `tests/` on the path (as `segfault_stress_repro.py` needs)" —
  Lazy-import placement is load-bearing for a tests/-free path; `.json()` depends on
  `tests/_strict_json.py` · related: TEST.T17 · [H06]
- **TWIN.N033** LIMIT · `digital_twin/README.md:129-133` — "`launch.py` — standalone, `src/`-free CLI
  demo ... Lighter and narrower in scope" — launch.py exercises raw bus reads only, not the real object
  graph · related: TWIN.T11 · [H06]
- **TWIN.N034** LIMIT · `digital_twin/README.md:144-147` — "Every chip fake exposes a `.fault`
  (`FaultInjector`) surface for provoking a bus NAK/CRC-corruption/timeout on demand" — Fault vocabulary
  is limited to these op-level classes plus a blocking hang · related: TWIN.T05 · [H06]
- **TWIN.N035** SETTLED · `digital_twin/README.md:151-156` — "needs **zero twin-awareness** — no `if`
  branch anywhere distinguishing real hardware from simulated" — Stated invariant for generated/src
  code; the swap is pure MICROPYPATH ordering · [H06]
- **TWIN.N036** INVAR · `digital_twin/README.md:181-191` — "`digital_twin` ... never together with plain
  `tests` on the same `MICROPYPATH`" — Same-named `machine`/`network`/`neopixel` modules would shadow
  each other; path discipline only · [H06]
- **TWIN.N037** INVAR · `digital_twin/README.md:183-188` — "`frozen_modules` is required here too ...
  Omitting it fails the run at import time with `ImportError: no module named 'frozen_html'`" —
  MICROPYPATH must carry `frozen_modules` · [H06]
- **TWIN.N038** LIMIT · `digital_twin/README.md:197-204` — "it defaults every state-persistence path to
  `None` (in-memory only) ... a manual run through that script is in-memory-only" — Manual twin runs do
  not exercise persistence unless paths are passed · related: TWIN.T10 · [H06]
- **TWIN.N039** SETTLED · `digital_twin/README.md:205-210` — "There is no `--soak`/`--soak-cycles` flag
  any more — the automated HTTP+memory-trend soak check moved host-side" — Driver/DUT separation
  decision; only `gc.mem_free()` exits via `MEM_SAMPLE` lines · [H06]
- **TWIN.N040** LIMIT · `digital_twin/README.md:217-224` — "only ever starts the specific tasks each
  test needs (never the full `start_and_check_tasks()` supervisor)" — The in-suite integration tier
  never exercises the supervisor graph · [H06]
- **TWIN.N041** LIMIT · `digital_twin/README.md:288-297` — "`_wire_uart_crossover()` ... joins their own
  ... `machine.UART` fakes with ... `attach_crossover_jumper()`, and swaps in the returned bounded
  `LinkPoller`s" — Twin UART is a fake crossover jumper with substituted pollers; no real UART
  timing/baud · related: TWIN.T12 · [H06]
- **TWIN.N042** SETTLED · `digital_twin/README.md:301-304` — "only ever writes to disk on an
  **explicit** call — never automatically, to avoid unnecessary write cycles on an SSD-hosted state
  file" — Host-SSD wear decision; state survives only if the flush runs (abrupt kill loses it) ·
  covered-by: TWIN.T10 · [H06]
- **TWIN.N043** INVAR · `digital_twin/README.md:310, :341` — "`configure_fram_state_path(...) # before constructing spi0`"
  / "`configure_scd30_state_path(...) # before constructing i2c0`" — Ordering contract for state-path
  configuration · related: TWIN.T10 · [H06]
- **TWIN.N044** LIMIT · `digital_twin/README.md:317-319` — "`tests/test_digital_twin_fram.py` ...
  constructing `FramChip` directly (that file never goes through `machine.SPI` at all)" — FRAM fake unit
  tests bypass the `machine.SPI` wiring path · related: TWIN.T04 · [H06]
- **TWIN.N045** ASSUME · `digital_twin/README.md:332-336` — "confirmed against
  `src/asy_scd30_driver.py`'s own setter docstrings" — SCD30 NVM-persisted set confirmed against driver
  docstrings, not stated against the datasheet · related: TWIN.T01 · [H06]
- **TWIN.N046** LIMIT · `digital_twin/README.md:354-358` — "**Known limitation: single-chip globals.**
  ... only ever persists the *last-wired* instance's NVM settings" — Multi-SCD30/multi-FRAM devices
  (both synthetic fixtures) persist only one instance · related: TWIN.T10 · [H06]
- **TWIN.N047** TODO · `digital_twin/README.md:357-358` — "A real multi-instance-persistence fix is
  unscoped; no real device needs it today." — Deferred work · [H06]
- **TWIN.N048** SETTLED · `digital_twin/README.md:412-420` — "The whole 14-run sequence itself runs
  twice ... at `--gc-threshold -1` ... and once at `32768`" — Zero-MemoryError at both GC stages,
  enforced by `_close_log_and_check_memory_safety()` · related: TEST.T18 · [H06]
- **TWIN.N049** LIMIT · `digital_twin/README.md:420-422` — "a device without `bmp3xx` (4 of the 6 real
  devices) simply never faults/checks it" — Per-device fault matrix; coverage per driver depends on
  which devices wire it · related: TWIN.T05 · [H06]
- **TWIN.N050** INVAR · `digital_twin/README.md:428-430` — "a plain `SIGTERM`/`terminate()` would skip
  `run_generic_integration.py`'s own FRAM/SCD30 flush" — Shutdown must be SIGINT for state to persist ·
  related: TWIN.T10 · [H06]
- **TWIN.N051** ASSUME · `digital_twin/README.md:443-446` — "`--fault` only ever produces bounded,
  immediately-raised `OSError`s, never an indefinite hang, so nothing here can actually block the event
  loop" — Run 3's watchdog-never-starves claim rests on the fault model, not on real bus behaviour ·
  related: TWIN.T05 · [H06]
- **TWIN.N052** LIMIT · `digital_twin/README.md:453-456` — "That makes this a much weaker claim than
  \"these never persist\", and one nothing re-checks against a *healthy* chip (BACKLOG.md)" — Run 4's
  SCD30/BMP3XX-read-0 claim is situational; the BACKLOG.md pointer names no item and none is found by
  grep · [H06]
- **TWIN.N053** RISK · `digital_twin/README.md:462-465` — "waiting on that warning is a host-speed race
  (it lands before the sample on an x86 runner, after it on the project's bench Pi4)" — Documents a
  removed host-speed-dependent check; pattern to watch in other runs · [H06]
- **TWIN.N054** ASSUME · `digital_twin/README.md:468-471` — "this suite counts `\"E\"`-typed history
  entries specifically, not the raw combined counter" — Run 5 depends on recovery notices being logged
  as `W`, never `E` · [H06]
- **TWIN.N055** LIMIT · `digital_twin/README.md:491-497` — "One fault per process rather than all at
  once is forced by the task-restart budget ... three drivers faulted together exhaust it" — Combined
  multi-driver faults are not tested in 5c · related: TWIN.T05 · [H06]
- **TWIN.N056** ASSUME · `digital_twin/README.md:548-555` — "100, not wozi's original 40 ... confirmed
  directly, 2026-09-14 ... roughly 2.5x" — Dated calibration of soak warmup cycles · [H06]
- **TWIN.N057** LIMIT · `digital_twin/README.md:569-580` — "fires exactly that many simultaneous GETs
  ... A 1 s settle precedes **every** round" — Ceiling test runs over the host loopback stack (not lwIP)
  and depends on a fixed 1 s settle · related: TWIN.T08 · [H06]
- **TWIN.N058** LIMIT · `digital_twin/README.md:603-609` — "`UARTLink.wire_log` is unbounded by design,
  so a unit test ... every such test clears it itself" — Unbounded twin log; each test must clear it;
  runner clears it periodically · [H06]
- **TWIN.N059** ASSUME · `digital_twin/README.md:613-620` — "Confirmed 2026-09-14 ... reproduced with
  the UART tasks fully disabled — so it is settling proportional to module count" — Dated inference on
  warmup cause · [H06]
- **TWIN.N060** ASSUME · `digital_twin/README.md:622-640` — "sets the tolerance as a generous multiple
  of that ... it covers the observed worst case (5889 bytes) with room left" — Self-calibrating trend
  tolerance; numbers from dated measurements (1496-1964 B spread, 25 ms samples autocorrelated) · [H06]
- **TWIN.N061** SETTLED · `digital_twin/README.md:644-656` — "`_NO_PERSIST_WHEN_FRAM_FAULTED` is not
  \"these logs are in-memory\"" — Suite-table semantics; README names SCD30/BMP3XX but the suite's set
  also holds `isl29125` (`scripts/_digital_twin_ci_suite.py:79`) (low) · [H06]
- **TWIN.N062** ASSUME · `digital_twin/README.md:663-666` — "The value sits just **above** the server's
  own `outer_cap_s`, deliberately" — Timeout derived from a src/ constant; must move with it · [H06]
- **TWIN.N063** LIMIT · `digital_twin/README.md:673-680` — "`sgp40`/`scd30` (`writeto`/`readfrom_into`),
  `bmp3xx` (`readfrom_mem`/`writeto_mem`), `fram` (`write`/`readinto`) ... `wlan` has no `--hang`
  vocabulary" — Hang coverage is limited to these ops; no WLAN hang, no `writeto` hang for
  BMP3xx/ISL29125 · related: TWIN.T05 · [H06]
- **TWIN.N064** LIMIT · `digital_twin/README.md:684-690` —
  "`configure_fault(\"isl29125:int_stuck_high\")` ... Reached from a test holding the chip object" —
  Stuck-INT fault is not reachable via `--fault`/`--hang` CLI; dev-only · related: TWIN.T05 · [H06]
- **TWIN.N065** WORKAROUND · `digital_twin/README.md:692-708` — "`_arm()` now checks, before cancelling
  the previous `_countdown()` task, whether its own deadline had already elapsed" — Twin-internal
  compensation because the fake WDT is an asyncio task that cannot run during a real freeze · related:
  TWIN.T02 · [H06]
- **TWIN.N066** ASSUME · `digital_twin/README.md:705-708` — "Run 10 giving the twin enough `--duration`
  (15s, not 0) for SGP40's own bus access — now queued behind BMP3xx's and SCD30's own FRAM-backed
  startup I/O" — Run 10 depends on boot ordering and a fixed duration · [H06]
- **TWIN.N067** INVAR · `digital_twin/README.md:749-759` — "called once, early, ... before anything
  constructs a socket" — UDP shim call order; `scripts/test.sh` grants setcap unconditionally so the DNS
  test works · related: TWIN.T07 · [H06]
- **TWIN.N068** WORKAROUND · `digital_twin/README.md:769-795` — "Works around three confirmed
  MicroPython-Unix-port-only `socket` quirks" — Tuple sockaddr rejection, `sendto()` (upstream #6924),
  raw `recvfrom()` struct; removal trigger: none stated · covered-by: TWIN.T07 · [H06]
- **TWIN.N069** ASSUME · `digital_twin/README.md:792-795` — "Every real call site ... already hands over
  an already-numeric address, so the `getaddrinfo()` calls here are always fast and local" — Shim
  assumes numeric addresses; a hostname would do a real DNS lookup · [H06]
- **TWIN.N070** INVAR · `digital_twin/README.md:799-801` — "**Required whenever a new sensor driver
  lands in `src/`** ... do it the same session the driver is promoted" — Review-only obligation (C.11
  point 9) · [H06]
- **TWIN.N071** INVAR · `digital_twin/README.md:813-817` — "the step bound itself is a
  **not**-datasheet-derived physical-plausibility judgment call, document it as such" — Convention for
  chip-fake docstrings · [H06]
- **TWIN.N072** INVAR · `digital_twin/README.md:818-821` — "answering the *exact* raw transaction shape
  the real `*_I2C` driver class sends — confirmed directly against that file's own source, never
  assumed" — Chip fakes mirror driver transaction shapes, not datasheet only · related: TWIN.T01 · [H06]
- **TWIN.N073** LIMIT · `digital_twin/README.md:844-850` — "`_wire_spi_device()`/`machine.SPI` currently
  wire **one fixed device per bus id** ... Not built now because no such driver exists yet" — No CS
  routing in the twin SPI; a second SPI device is unsupported · related: DOC.S22 · [H06]
- **TWIN.N074** LIMIT · `digital_twin/README.md:876-881` — "**BMP3xx's fixed calibration block is not
  sourced from a real chip.**" — Hand-picked coefficients; real factory trim never exercised in the twin
  · related: TWIN.S03 · [H06]
- **TWIN.N075** LIMIT · `digital_twin/README.md:882-885` — "`tests/_fram_chip_fake.py`'s own
  WEL-corruption-specific knobs (`drop_wren`, `disturb_write_autoclear`, ...) ... weren't reproduced
  here" — Twin FRAM fake lacks WEL fault knobs · related: TWIN.T05, STOR.T03 · [H06]
- **TWIN.N076** SETTLED · `digital_twin/README.md:886-894` — "Deliberately kept hardcoded to
  `sensortask_wozi` ... never invoked by `scripts/run_digital_twin_ci.sh` or any `tests/test_*.py` file"
  — Manual-only stress tool, outside CI · related: TWIN.T11 · [H06]
- **TWIN.N077** TODO · `digital_twin/README.md:917-919` — "No separate upstream issue for this narrower
  residual case was found as of this check — worth filing one upstream ... as a future follow-up" —
  Unfiled upstream bug report · [H06]

## digital_twin/machine.py

- **TWIN.N078** MIRROR · `digital_twin/machine.py:13-14` — "same \"keep last N\" convention
  print_log.py's own PrintLogHistory uses" — `_LOG_MAXLEN = 200` bounds I2C/SPI logs and the WDT log;
  older entries silently dropped · [H06]
- **TWIN.N079** LIMIT · `digital_twin/machine.py:62-67` — "`if not isinstance(id, int): raise TypeError(...)`
  / `if not (0 <= id <= 28)`" — Twin Pin accepts only int ids 0-28; named/CYW43 pins (e.g. "LED") and
  any other real-port id rules are not modelled (low) · [H06]
- **TWIN.N080** LIMIT · `digital_twin/machine.py:84-89, 111-120` — "`self.pull = pull` ...
  `self._irq_hard = hard`" — Pull resistors never affect `value()`, and the `hard` flag is stored only:
  hard-IRQ context (no heap allocation, pre-emption) is unmodelled (low) · related: TWIN.T02 · [H06]
- **TWIN.N081** LIMIT · `digital_twin/machine.py:126-137` — "drives a real electrical transition, firing
  the handler only when the direction matches" — Edge IRQs run the handler synchronously in the caller's
  context; no IRQ latency, bounce, floating/stuck line modelling · related: TEST.T05 · [H06]
- **TWIN.N082** INVAR · `digital_twin/machine.py:144-146` — "called once before i2c0/i2c1 are
  constructed" — `configure_random_source()` ordering; later calls do not reach already-built chips ·
  [H06]
- **TWIN.N083** LIMIT · `digital_twin/machine.py:151-152, 163-167` — "`_current_scd30_chip`" /
  "`flush_scd30()`" — Single module-global chip: only the last-constructed SCD30 is ever flushed (README
  "single-chip globals") · related: TWIN.T10 · [H06]
- **TWIN.N084** INVAR · `digital_twin/machine.py:164-165, 310-312` — "Called once, in a try/finally
  around asyncio.run(main())" / "why this must be explicit rather than a self-registered signal/atexit
  handler" — Persistence depends on every entry point wrapping `asyncio.run()` with both flushes ·
  covered-by: TWIN.T10 · [H06]
- **TWIN.N085** SETTLED · `digital_twin/machine.py:176-177` — "Replaces the whole plan outright, the
  same \"last configure_*() call before construction wins\" convention every hook here already uses" —
  Last-call-wins module-global configuration; calls after construction have no effect · [H06]
- **TWIN.N086** INVAR · `digital_twin/machine.py:185-194` — "Legacy sugar over configure_wiring(), kept
  for tests: no real entry point calls it" /
  "`open(f\"build/generated_src/sensortask_{profile}_wiring_plan.json\")`" — Relative path: works only
  when CWD is the repo root and generation already ran · related: SCR.S07 · [H06]
- **TWIN.N087** LIMIT · `digital_twin/machine.py:199-204` — "Lazily defaults to wozi's generated plan
  the first time a caller constructs a bus without configuring wiring" — Silent wozi default for any
  unconfigured caller · related: TWIN.T12 · [H06]
- **TWIN.N088** SUPPRESS · `digital_twin/machine.py:204` — "`# type: ignore[return-value] # configure_i2c_wiring() above always sets it`"
  — mypy suppression resting on a control-flow claim · [H06]
- **TWIN.N089** INVAR · `digital_twin/machine.py:208-210, 231` — "the twin's hand-maintained chip-fake
  catalog, a new chip type still needing one written" — A driver without a fake raises `ValueError` at
  bus construction; catalog is hand-kept · related: TWIN.T12 · [H06]
- **TWIN.N090** LIMIT · `digital_twin/machine.py:239-247` — "`self.freq = freq` / `self.timeout = timeout`"
  — I2C `freq`/`timeout` are stored and never honoured: zero transaction time, no clock stretching, no
  bus timeout, no SDA-stuck/arbitration faults (low) · covered-by: TWIN.T02 · [H06] ⟨quote not matched
  at the anchor⟩
- **TWIN.N091** LIMIT · `digital_twin/machine.py:253-254` — "`return sorted(self.devices.keys())`" —
  `scan()` lists exactly the wired fakes; real-bus ghost/missing addresses unmodelled · related:
  TEST.S15 · [H06]
- **TWIN.N092** LIMIT · `digital_twin/machine.py:264-267` — "general call - every device may listen,
  tolerate silently" — General call reaches no chip fake, so chip reactions to it (e.g. SGP40/SCD30 soft
  reset) are unmodelled · covered-by: TWIN.S02 · [H06]
- **TWIN.N093** LIMIT · `digital_twin/machine.py:259-283` — "`def writeto(self, address, buf, stop=True)`"
  — The `stop` flag (repeated-start) is logged but never changes chip behaviour (low) · [H06] ⟨quote not
  matched at the anchor⟩
- **TWIN.N094** LIMIT · `digital_twin/machine.py:275-278` — "`buf[:] = data`" — Slice-assigning a fake's
  reply into a bytearray changes its length if the fake returns a different count; real hardware always
  fills `len(buf)` (low) · [H06]
- **TWIN.N095** SUPPRESS · `digital_twin/machine.py:265, 276, 277, 289, 293, 294, 403, 428, 745` — "`# type: ignore[call-overload]`
  / `[arg-type]` / `[index]` / `[index,arg-type]`" — Nine mypy suppressions on buffer-typed `object`
  parameters · [H06] ⟨quote not matched at the anchor⟩
- **TWIN.N096** INVAR · `digital_twin/machine.py:302-304` — "src/ itself never calls this (zero
  twin-awareness anywhere in src/, per this step's own finish criteria)" — src/ must never reference
  twin hooks; convention · [H06]
- **TWIN.N097** ASSUME · `digital_twin/machine.py:320-322` — "it's keyed by size as the best available
  proxy (unique today ...). Any size not listed falls back to FramChip's own default RDID" — A new FRAM
  size silently gets MB85RS64V's RDID (the same failure shape as the 2026-09-04 dev bug) · [H06]
- **TWIN.N098** LIMIT · `digital_twin/machine.py:326-336` — "`attachment = _current_wiring_plan()[\"spi\"].get(f\"spi{bus_id}\")`"
  — One SPI device per bus id, no chip-select routing; framing inferred from `write()` pairing ·
  covered-by: TWIN.S04 · [H06]
- **TWIN.N099** LIMIT · `digital_twin/machine.py:410-415, 427-431` — "`buf[:] = bytes(len(buf))`" /
  "`self.write(buffer_out); self.readinto(buffer_in)`" — SPI baud/mode never validated; `write_readinto`
  is two sequential half-duplex calls; an absent device reads zeros, not a floating-bus value (low) ·
  [H06] ⟨quote not matched at the anchor⟩
- **TWIN.N100** LIMIT · `digital_twin/machine.py:435` — "`_UART_BITS_PER_BYTE = 10 # 8N1 on the wire`" —
  Wire time assumes 8N1 whatever `bits`/`parity`/`stop` are configured · [H06]
- **TWIN.N101** ASSUME · `digital_twin/machine.py:500-502` — "A run longer than ticks_us()' period would
  need re-anchoring; no test comes close." — Unverified bound; `ticks_diff` is signed over half the
  ticks period, and manual/CI dev twin runs with a live link can run long · covered-by: TWIN.T09 · [H06]
- **TWIN.N102** LIMIT · `digital_twin/machine.py:539-540` — "Called from each endpoint's own read path,
  so time only ever advances as the consumer actually runs" — Delivery is lazy (pumped by reads/ioctl),
  not interrupt-driven · [H06]
- **TWIN.N103** LIMIT · `digital_twin/machine.py:808-816` — "`await asyncio.sleep_ms(self.period)` /
  `self.callback(self)`" — Timer period drifts by callback+scheduling time each cycle; callbacks never
  run while the loop is blocked, unlike rp2 soft callbacks run by the scheduler; a callback exception
  ends the task (low) · covered-by: TWIN.T09 · [H06] ⟨quote not matched at the anchor⟩
- **TWIN.N104** DRIFT · `digital_twin/machine.py:828-830 vs :811-815` — "Skip the self-cancel: the old
  task returns on its own right after this callback does." — Old task returns only if the new `mode` is
  ONE_SHOT; a PERIODIC self-rearm keeps the old loop running alongside the new task (low) · related:
  TWIN.T02 · [H06]
- **TWIN.N105** LIMIT · `digital_twin/machine.py:852-854` — "An asyncio countdown since the last feed()
  that records rather than acts" — Twin WDT never resets the process: post-watchdog-reset behaviour
  (reboot, reset cause) is not exercised; countdown cannot run during a real freeze · covered-by:
  TWIN.T02 · [H06]
- **TWIN.N106** WORKAROUND · `digital_twin/machine.py:866-868` — "credit that already-elapsed window
  before cancelling it away, since real hardware can't un-reset itself retroactively" — Twin-internal
  compensation for the asyncio-based WDT; removal trigger: none stated · [H06]
- **TWIN.N107** LIMIT · `digital_twin/machine.py:899-913` — "`_shared_datetime: \"tuple[int, ...]\" = (2000, 1, 1, 0, 0, 0, 0, 0)`"
  — Twin RTC never advances and is not coupled to `time.time()`/`gmtime()` (host clock on the Unix
  port); on rp2 an RTC set moves `time`, so NTP-set clock jumps are unmodelled (inferred from code) ·
  covered-by: TWIN.T09 · [H06]
- **TWIN.N108** LIMIT · `digital_twin/machine.py:907-913` — "even on the set path, where real hardware
  returns nothing meaningful" — Set path returns the tuple; real call returns None · covered-by:
  TWIN.S05 · [H06]
- **TWIN.N109** LIMIT · `digital_twin/machine.py:916-940` — "`class SimulatedRebootError(Exception)`" /
  "Real machine.reset() never returns; this twin cannot restart anything, so it raises instead." —
  Reset/bootloader raise an `Exception` subclass, so any broad `except Exception` in src/ swallows a
  simulated reset and keeps running code that never runs on hardware (low) · related: TEST.S15 · [H06]

## digital_twin/_fault_injection.py

- **TWIN.N110** LIMIT · `digital_twin/_fault_injection.py:2` — "For chip-protocol-level faults
  (corrupted CRC, mid-transaction timeout) a bus fake can't express on its own; address-level NAK is
  handled generically by `machine.py`'s own `I2C` class" — Fault vocabulary: queued exceptions per op
  name plus hangs; no partial-transfer, clock-stretch, or electrical faults · related: TWIN.T05 · [H06]
- **TWIN.N111** LIMIT · `digital_twin/_fault_injection.py:13-21` — "`self._queues.setdefault(op, []).extend([exc] * times)`"
  — One exception instance is re-raised for all `times` calls; faults are keyed by op name only, not by
  address/command, so a multi-command op cannot target one command (low) · related: TWIN.T05 · [H06]
- **TWIN.N112** INVAR · `digital_twin/_fault_injection.py:18-32` — "`def maybe_raise(self, op)` / `def maybe_hang(self, op)`"
  — A fault fires only if each chip handler calls these hooks for that op; coverage per op is per-fake
  discipline (e.g. BMP3xx `handle_writeto` has no `maybe_hang`) · covered-by: TWIN.T05 · [H06] ⟨quote
  not matched at the anchor⟩

## digital_twin/_crc8.py

- **TWIN.N113** SETTLED · `digital_twin/_crc8.py:1` — "deliberately not importing `src/crc_checks.py`'s
  own CRC8, so a bug shared between the twin's response-building and the driver's validation can't hide"
  — Deliberate independent reimplementation · [H06]
- **TWIN.N114** MIRROR · `digital_twin/_crc8.py:1-3` — "Sensirion polynomial 0x31, init 0xFF" — Must
  equal the datasheet CRC and `src/crc_checks.py`; no golden vector cited here · related: TEST.S20 ·
  [H06]

## digital_twin/_sgp40_chip.py

- **TWIN.N115** DRIFT · `digital_twin/_sgp40_chip.py:1` — "answers `asy_sgp40_driver.py`'s exact
  word-oriented protocol (serial-number/self-test/general-call-reset/measure-raw)" — General call never
  reaches the fake (`machine.py:266`) and the fake has no reset handling · covered-by: TWIN.S02 · [H06]
- **TWIN.N116** ASSUME · `digital_twin/_sgp40_chip.py:32-34` — "`min_raw: int = 26000, max_raw: int = 34000`"
  — Module docstring calls these "datasheet-ranged"; no page cited (low) · related: TWIN.T01 · [H06]
- **TWIN.N117** ASSUME · `digital_twin/_sgp40_chip.py:41-43` — "Not datasheet-derived (min_raw/max_raw
  are)" — Step bound is a judgment call · [H06]
- **TWIN.N118** LIMIT · `digital_twin/_sgp40_chip.py:46` — "`self._pending_reply = bytes(3)`" — A read
  before any command returns zero bytes with an invalid CRC, not a NAK (low) · [H06]
- **TWIN.N119** LIMIT · `digital_twin/_sgp40_chip.py:62-65` — "`reply = word(0x0000) + word(word1) + word(word2)`"
  — Serial number's first word is always 0x0000 · [H06]
- **TWIN.N120** LIMIT · `digital_twin/_sgp40_chip.py:66-67` — "`reply = word(0xD400) # datasheet Table 13: high byte 0xD4 = all tests passed`"
  — Self-test always passes; no execution time for self-test or measurement · covered-by: TWIN.S02 ·
  [H06]
- **TWIN.N121** LIMIT · `digital_twin/_sgp40_chip.py:68-71` — "`elif len(data) == 8 and data[0:2] == _CMD_MEASURE_RAW:`"
  — Compensation words' CRCs unchecked and compensation has no effect on the raw value · covered-by:
  TWIN.S02 · [H06]
- **TWIN.N122** ASSUME · `digital_twin/_sgp40_chip.py:72-75` — "Unrecognized command - real hardware
  would simply not respond usefully; keep whatever was already pending rather than raising" — A wrong
  command code from a driver is silently accepted (e.g. heater-off) and a stale reply re-served; real
  NAK behaviour unmodelled · related: TWIN.T01 · [H06]
- **TWIN.N123** LIMIT · `digital_twin/_sgp40_chip.py:78-81` — "`return (self._pending_reply + bytes(nbytes))[:nbytes]`"
  — Repeated reads re-serve the last reply; reads during a measurement never NAK · related: TWIN.S02 ·
  [H06]
- **TWIN.N124** LIMIT · `digital_twin/_sgp40_chip.py:55-57` — "Flip the trailing CRC byte of the last
  word in the reply" — CRC corruption knob hits only the last word's CRC · [H06]

## digital_twin/_scd30_chip.py

- **TWIN.N125** ASSUME · `digital_twin/_scd30_chip.py:1` — "datasheet-ranged random
  CO2/temperature/humidity" — Defaults 400-2000 ppm, 15-30 C, 20-70 %RH are room values, not the
  datasheet's measurement range (low) · related: TWIN.T01 · [H06]
- **TWIN.N126** ASSUME · `digital_twin/_scd30_chip.py:42` — "`_FIRMWARE_VERSION = 0x0342 # plausible fixed value ... - never checked by the driver`"
  — Claim about driver behaviour · [H06]
- **TWIN.N127** ASSUME · `digital_twin/_scd30_chip.py:81-84` — "*_step: NOT datasheet-derived (the
  min/max above are) - a physical-plausibility judgment call" — Step bounds are judgment calls · [H06]
- **TWIN.N128** LIMIT · `digital_twin/_scd30_chip.py:110-128` — "`except ValueError: return # malformed/truncated file - leave settings at their factory-fresh defaults`"
  — Corrupt state silently resets to defaults; a non-dict JSON would raise on `.get()` (low) ·
  covered-by: TWIN.T10 · [H06]
- **TWIN.N129** LIMIT · `digital_twin/_scd30_chip.py:130-143` — "`with open(self.state_path, \"w\") as f: json.dump(...)`"
  — Non-atomic save; an interrupted flush leaves a truncated file that reloads as defaults (low) ·
  related: TWIN.T10 · [H06]
- **TWIN.N130** LIMIT · `digital_twin/_scd30_chip.py:145-165` —
  "`self._timer.init(period=self._measurement_interval_s * 1000, ...)`" — Readings and RDY edges are
  produced whether or not continuous measurement was started; interval 0 gives a 0 ms periodic timer ·
  covered-by: TWIN.S01 · [H06] ⟨quote not matched at the anchor⟩
- **TWIN.N131** LIMIT · `digital_twin/_scd30_chip.py:172-175` — "`pass # no persistent chip-side state modeled that a reset would need to clear`"
  — Stop-continuous and soft reset are no-ops · covered-by: TWIN.S01 · [H06]
- **TWIN.N132** LIMIT · `digital_twin/_scd30_chip.py:177-195` — "`arg = (data[2] << 8) — data[3]`" |
  Argument CRC (data[4]) never checked; no range validation of interval/altitude/offset/pressure ·
  covered-by: TWIN.S01 · [H06]
- **TWIN.N133** ASSUME · `digital_twin/_scd30_chip.py:183` — "re-arm at the new cadence, matching real
  hardware" — Unverified claim of real re-arm timing · [H06]
- **TWIN.N134** LIMIT · `digital_twin/_scd30_chip.py:196` — "Unrecognized shape - real hardware would
  just not respond usefully." — Wrong-length commands are silently ignored · related: TWIN.T01 · [H06]
- **TWIN.N135** LIMIT · `digital_twin/_scd30_chip.py:158-163, 198-228` — "`reply = self._buffer`" —
  Compensation settings (pressure, altitude, temp offset, ASC, FRC) never affect readings; reading when
  not ready re-serves the stale buffer; unknown read gives zero bytes with bad CRC · related: TWIN.T01 ·
  [H06]
- **TWIN.N136** LIMIT · `digital_twin/_scd30_chip.py:206-208` — "`reply = reply[:2] + bytes([reply[2] ^ 0xFF]) + reply[3:]`"
  — Measurement corruption knob hits only the first word's CRC · [H06]

## digital_twin/_bmp3xx_chip.py

- **TWIN.N137** LIMIT · `digital_twin/_bmp3xx_chip.py:1-2` — "Calibration block is hand-picked, not
  real-chip data" — Factory-trim variety never exercised · related: TWIN.S03 · [H06]
- **TWIN.N138** LIMIT · `digital_twin/_bmp3xx_chip.py:21, 176-177` — "`_BMP390_CHIP_ID = 0x60`" —
  Docstring names BMP388/BMP390 but only BMP390's ID is served; BMP388 (0x50) path unexercised ·
  covered-by: TWIN.S03 · [H06]
- **TWIN.N139** ASSUME · `digital_twin/_bmp3xx_chip.py:62-86` — "`for _ in range(20):` / `for _ in range(40):`"
  — Newton inversion converges in a fixed iteration count across the range (README :876-881 says
  verified) · [H06] ⟨quote not matched at the anchor⟩
- **TWIN.N140** ASSUME · `digital_twin/_bmp3xx_chip.py:107-109` — "Not datasheet-derived (the min/max
  above are)" — Step bounds are judgment calls; 950-1050 hPa/15-30 C are narrower than the datasheet
  range (low) · [H06]
- **TWIN.N141** ASSUME · `digital_twin/_bmp3xx_chip.py:116-118` — "The ADC burst stays all-zero until
  the first forced trigger computes one, as real hardware has nothing to report before its first
  conversion" — Unverified reset value of data registers (low) · [H06]
- **TWIN.N142** LIMIT · `digital_twin/_bmp3xx_chip.py:149-157` — "`self.fault.maybe_raise(\"writeto\")`"
  — Zero-byte ACK probe has no `maybe_hang`; a history note says its absence once crashed every boot ·
  covered-by: TWIN.S03 · [H06]
- **TWIN.N143** INVAR · `digital_twin/_bmp3xx_chip.py:154-156` — "Nothing else in this driver calls
  plain writeto(), every register access going through writeto_mem()" — Fake answers only the empty
  probe on `writeto`; a future plain `writeto` from the driver would be silently ignored · [H06]
- **TWIN.N144** LIMIT · `digital_twin/_bmp3xx_chip.py:162-168` — "`if data and data[0] == _CONTROL_FORCED_MODE: self._trigger_measurement()`"
  — Conversion is instant (no conversion time, status data-ready at once); OSR/IIR stored but never
  affect timing or noise; only exact 0x13 triggers · related: TWIN.T01 · [H06]
- **TWIN.N145** LIMIT · `digital_twin/_bmp3xx_chip.py:169-171` — "any other register: real hardware
  would just silently accept/ignore it too." — Soft reset resets status only (OSR/config kept);
  unknown-register behaviour assumed · [H06]
- **TWIN.N146** LIMIT · `digital_twin/_bmp3xx_chip.py:178-191` — "`elif reg_addr == _REGISTER_ERR: reply = bytes([0x00])`"
  — ERR register always 0 (fatal/cmd/conf errors unmodelled); reads at other offsets return zeros, no
  auto-increment across the register map · related: TWIN.T01 · [H06]

## digital_twin/_fram_chip.py

- **TWIN.N147** DRIFT · `digital_twin/_fram_chip.py:1-2` — "answers `asy_fram_driver.py`'s exact
  opcode/CS-session shape" — The fake never sees CS; session framing is inferred from `write()` pairing
  · covered-by: TWIN.S04 · [H06]
- **TWIN.N148** SETTLED · `digital_twin/_fram_chip.py:2` — "independently reimplemented, not shared with
  `tests/_fram_chip_fake.py`" — Deliberate duplication of the FRAM fake across mock and twin · related:
  TEST.T05 · [H06]
- **TWIN.N149** ASSUME · `digital_twin/_fram_chip.py:67` — "the '{\"size\": N, \"memory_hex\": \"'
  prefix is always well under this" — 128-char header read assumes the file's own format · [H06]
- **TWIN.N150** LIMIT · `digital_twin/_fram_chip.py:57-94` — "`if idx == -1: return # malformed/unrecognized file - leave self.memory at its blank default`"
  — The file's `size` field is ignored (a state file from another chip size loads partially); corrupt
  file silently yields a blank chip · covered-by: TWIN.T10 · [H06]
- **TWIN.N151** LIMIT · `digital_twin/_fram_chip.py:102-106` — "`with open(self.state_path, \"w\") as f:`"
  — Non-atomic save; a truncated file reloads as a partial image with a zero tail (low) · related:
  TWIN.T10 · [H06]
- **TWIN.N152** LIMIT · `digital_twin/_fram_chip.py:112-120` — "data phase of a previously-opened WRITE
  (opcode+address arrived in the prior call)" — A single write carrying opcode+address+data loses the
  data; writes past the end grow the buffer; no wraparound · covered-by: TWIN.S04 · [H06]
- **TWIN.N153** LIMIT · `digital_twin/_fram_chip.py:126-129` — "`self.status = (data[1] & ~_WEL_BIT) — (self.status & _WEL_BIT)`"
  | Status-register block-protect (BP) bits and WP/WPEN are stored but never enforced on writes (low) ·
  related: STOR.T03 · [H06]
- **TWIN.N154** LIMIT · `digital_twin/_fram_chip.py:147-155` — "`buf[:] = self.memory[self._pending_addr : self._pending_addr + n]`"
  — Reads past the end return a short slice (bytearray shrinks) instead of wrapping; readinto without a
  pending op returns zeros · covered-by: TWIN.S04 · [H06]

## digital_twin/_isl29125_chip.py

- **TWIN.N155** ASSUME · `digital_twin/_isl29125_chip.py:62-63` — "`_CYCLE_MS_12BIT = 19 # 3 x ~6.3ms: p6 makes tINT an n-bit counter on one oscillator, so 101 x 2**-4`"
  — 12-bit cycle time derived, not measured; twin uses typical values, no oscillator spread · [H06]
- **TWIN.N156** ASSUME · `digital_twin/_isl29125_chip.py:73-76, 86-89` — "min/max are datasheet-derived
  (p1: range 0 reaches 375 lux, range 1 reaches 10000)" — Defaults are 5-9000 lux, not the cited
  datasheet endpoints (low) · [H06]
- **TWIN.N157** ASSUME · `digital_twin/_isl29125_chip.py:90-93` — "Deliberately NOT the nominal
  10000/375 = 26.67 ... which on real silicon it always does" — Fake ratio 25.9 is a chosen value; the
  claim about silicon is from M.1.5/M.1.6 · [H06]
- **TWIN.N158** INVAR · `digital_twin/_isl29125_chip.py:21-25, 96-100` — "the Pin(6) here and the Pin(6)
  the driver constructs are the SAME object" / "The line idles HIGH ... Without this it starts
  electrically asserted" — Depends on Pin registry identity and on the constructor driving the line high
  first · [H06]
- **TWIN.N159** LIMIT · `digital_twin/_isl29125_chip.py:152-164` — "Clipping is MODELLED, not clamped
  away" — Linear lux-to-count model with tint weights; no spectral/IR response; dark counts only in the
  low range · related: TWIN.T11 · [H06]
- **TWIN.N160** LIMIT · `digital_twin/_isl29125_chip.py:176-179` — "RGBCF reports which channel the next
  conversion is on; rotated so it is never a constant" — RGBCF is an approximation, not real conversion
  sequencing · [H06]
- **TWIN.N161** LIMIT · `digital_twin/_isl29125_chip.py:229-235` — "A persistent behavioural MODE,
  deliberately not a FaultInjector entry" — Only `int_stuck_high` exists; floating/stuck-low/bouncing
  INT unmodelled · related: TWIN.T05 · [H06]
- **TWIN.N162** LIMIT · `digital_twin/_isl29125_chip.py:239-242` — "I2CDevice.setup()'s zero-byte ACK
  probe" — `handle_writeto` has no `maybe_hang` (the `--hang` vocabulary offers only
  `readfrom_mem`/`writeto_mem` for ISL29125) · related: TWIN.T05 · [H06]
- **TWIN.N163** LIMIT · `digital_twin/_isl29125_chip.py:253-281` — "The address pointer auto-increments
  (p7), so one burst can carry 1-3 config bytes." — A burst starting in CONFIG stops at CONFIG3 and one
  in the threshold block stops at 0x07; bytes that on silicon would continue into the next block are
  dropped (low) · [H06]
- **TWIN.N164** ASSUME · `digital_twin/_isl29125_chip.py:288` — "any other register: real hardware
  silently accepts and ignores it too." — Unverified · [H06]

## digital_twin/_http_client.py

- **TWIN.N165** ASSUME · `digital_twin/_http_client.py:2` — "Every response it sees carries `Connection: close`,
  so no keep-alive support is needed." — Oracle depends on a server-side hook · related: TEST.T17 ·
  [H06]
- **TWIN.N166** INVAR · `digital_twin/_http_client.py:20-23` — "or b\"\" when read_body=False drained
  the response instead of materializing it - .json() must not be called on that" — Caller discipline ·
  [H06]
- **TWIN.N167** ASSUME · `digital_twin/_http_client.py:25-27` — "Every body this client decodes is a
  JSON object" — `.json()` typed as dict · [H06]
- **TWIN.N168** WORKAROUND · `digital_twin/_http_client.py:29-31, :35` — "Its stub types the argument
  AnyStr, refusing bytearray - a stub gap only" / "`# type: ignore[type-var]`" — Suppression for a stub
  defect; removal trigger: none stated · [H06]
- **TWIN.N169** INVAR · `digital_twin/_http_client.py:32` — "here, not at the top: tests/ is absent from
  a standalone twin's path" — Lazy-import placement is load-bearing · [H06]

## digital_twin/_unix_port_udp_addr_shim.py

- **TWIN.N170** WORKAROUND · `digital_twin/_unix_port_udp_addr_shim.py:1-3` — "Workaround for three
  confirmed MicroPython-Unix-port-only `socket` quirks" — Removal trigger: none stated · covered-by:
  TWIN.T07 · [H06]
- **TWIN.N171** INVAR · `digital_twin/_unix_port_udp_addr_shim.py:3` — "Call
  `patch_asy_udp_socket_for_unix_port()` once, early, before constructing any `AsyUDPSocket`." —
  Call-order contract · [H06]
- **TWIN.N172** SUPPRESS · `digital_twin/_unix_port_udp_addr_shim.py:74-76` — "`# type: ignore[method-assign]`"
  — Three method-assign suppressions (twin scope, allowed) · [H06]
- **TWIN.N173** SUPPRESS · `digital_twin/_unix_port_udp_addr_shim.py:15` — "`# type: ignore[no-redef] # no-op at runtime either way`"
  — Runtime `cast` fallback · [H06]
- **TWIN.N174** ASSUME · `digital_twin/_unix_port_udp_addr_shim.py:53-57` — "The native family field ...
  `struct.unpack(\"<H\", addr[0:2])`" — "Native" field read as little-endian: assumes a little-endian
  host (low) · [H06]

## digital_twin/unix_port_gc_unwedge.py

- **TWIN.N175** WORKAROUND · `digital_twin/unix_port_gc_unwedge.py:1-2` — "has since closed the root
  cause - this module stays wired in as defense in depth only" — Removal trigger: none stated ·
  covered-by: TWIN.T07 · [H06]

## digital_twin/unix_port_poll_prewarm.py

- **TWIN.N176** WORKAROUND · `digital_twin/unix_port_poll_prewarm.py:1-2` — "Workaround for a confirmed
  MicroPython Unix-port-only `extmod/modselect.c` segfault (traced at v1.28.0; that file is unchanged at
  the current v1.29.0 pin)" — Removal trigger: none stated · covered-by: TWIN.T07 · [H06]
- **TWIN.N177** INVAR · `digital_twin/unix_port_poll_prewarm.py:2, :49` — "Call `prewarm_poll_set()` as
  the very first statement of any entry point" / "Must run before any other code registers a poll
  object." — Order contract, convention only · related: TWIN.T07 · [H06]
- **TWIN.N178** LIMIT · `digital_twin/unix_port_poll_prewarm.py:19-21` — "~28x the real peak: every
  device's max_connections is 6, and the hardest burst any tier drives is max(12, 3 x 6) = 18 clients
  ... A raised threshold, not a fix" — Beyond 512 registered fds the bug returns; the margin rests on
  copied figures · related: TWIN.T07 · [H06]
- **TWIN.N179** ASSUME · `digital_twin/unix_port_poll_prewarm.py:21` — "~45ms at startup" — Single
  measurement · [H06]
- **TWIN.N180** SUPPRESS · `digital_twin/unix_port_poll_prewarm.py:48` — "`# noqa: ANN401 - a packed sockaddr here, a tuple under CPython`"
  — Lint suppression · [H06]

## digital_twin/network.py

- **TWIN.N181** ASSUME · `digital_twin/network.py:30-33` — "Real association plus DHCP takes low
  single-digit seconds in the field. This sits under _poll_sta_connect_status()'s 5s budget" —
  `_CONNECT_DELAY_S = 0.7` is tied to a src/ budget; real connect timing and slow-connect paths
  unmodelled · related: TWIN.T03 · [H06]
- **TWIN.N182** LIMIT · `digital_twin/network.py:35-37` — "`_CONNECTED_IFCONFIG = (\"192.168.1.42\", ...)`"
  — Static address, module-level country/hostname state shared across tests · related: TEST.T07 · [H06]
- **TWIN.N183** LIMIT · `digital_twin/network.py:57-73` — "`def __init__(self, if_id: int)`" — Every
  `WLAN(...)` is a fresh object with its own state (real rp2 returns a per-interface singleton); STA and
  AP share no radio state (low) · related: TWIN.T03 · [H06]
- **TWIN.N184** LIMIT · `digital_twin/network.py:86-105` — "An exhausted queue falls back to
  always-succeeds" — Outcomes are only scripted success/fail codes; no spontaneous link loss, no CYW43
  `isconnected()` false positive, constant RSSI -50 · related: TWIN.T03 · [H06]
- **TWIN.N185** LIMIT · `digital_twin/network.py:145-147` — "`def config(self, **kwargs: object) -> None: # recorded verbatim, never inspected`"
  — AP-mode config unvalidated; query form `config('param')` unsupported · covered-by: TWIN.S05 · [H06]

## digital_twin/neopixel.py

- **TWIN.N186** ASSUME · `digital_twin/neopixel.py:1-2` — "real `NeoPixel.write()` is a single busy-wait
  call with no return value/error path" — Platform claim; the fake does not model the busy-wait duration
  or colour byte order · covered-by: TWIN.T11 · [H06]
- **TWIN.N187** LIMIT · `digital_twin/neopixel.py:6-9` — "found by the same audit rather than by
  reproducing a failure here" — `writes` bounded to 200 · [H06]

## digital_twin/launch.py

- **TWIN.N188** MIRROR · `digital_twin/launch.py:1, :369-375` — "brings up the same bus/peripheral
  wiring `sensortask_wozi.build_system()` uses" / "`I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)` ...
  `chips = {\"scd30\": i2c0.devices[0x61], ...}`" — Hand-typed wozi pins, WDT timeout and addresses that
  must track `devices/wozi.toml`; nothing checks them · related: TWIN.T11 · [H06]
- **TWIN.N189** INVAR · `digital_twin/launch.py:1, :370-372` — "Standalone, `src/`-free CLI launcher" —
  Never calls `configure_wiring()`, so bus construction lazily opens
  `build/generated_src/sensortask_wozi_wiring_plan.json`: it needs generation to have run first ·
  related: TWIN.T11 · [H06]
- **TWIN.N190** WORKAROUND · `digital_twin/launch.py:2` — "`parse_args()` is hand-rolled (the vendored
  `argparse` lacks `action=\"append\"`/`choices=`)" — Platform library gap; removal trigger: none stated
  · [H06]
- **TWIN.N191** MIRROR · `digital_twin/launch.py:22-30, 71-80` — "`_FAULT_DEVICE_OPS = {...}`" /
  "`_HANG_DEVICE_OPS = {...}`" — Op vocabulary must match the op names each chip fake's handlers pass to
  `maybe_raise`/`maybe_hang`; shared with `run_generic_integration.py` · related: TWIN.T05 · [H06]
- **TWIN.N192** LIMIT · `digital_twin/launch.py:26-27` — "dev-only; this launcher's own fixed wiring
  below has no ISL29125, so only run_generic_integration.py can actually apply one" — ISL29125 faults
  unreachable from launch.py · [H06]
- **TWIN.N193** LIMIT · `digital_twin/launch.py:57-61, 194-197` — "`network.WLAN.raise_on` has no repeat
  limit of its own, the fault stays armed until cleared" — WLAN faults are permanent for the process:
  transient WiFi faults not expressible from the CLI · related: TWIN.T05 · [H06]
- **TWIN.N194** SETTLED · `digital_twin/launch.py:72-74` — "\"wlan\" has no real blocking call for
  time.sleep() to stand in for ... so it's deliberately not part of this vocabulary" — No WLAN hang (a
  blocking CYW43 call is unmodelled) · [H06]
- **TWIN.N195** ASSUME · `digital_twin/launch.py:84-86` — "TIMES defaults to 1, since real hardware gets
  one 8388ms window before the WDT resets it" — Rationale ties a CLI default to the WDT cap · [H06]
- **TWIN.N196** INVAR · `digital_twin/launch.py:208-213` — "A name in the vocabulary above is not the
  same as a chip this run wired" — Unwired device raises `ValueError` (enforced) · [H06]
- **TWIN.N197** MIRROR · `digital_twin/launch.py:216-219` — "Reproduces asy_bmp3xx_driver.py's own
  _read_coefficients()/compensation math independently ... same shape
  tests/test_digital_twin_bmp3xx.py's own _decode_temp_pressure()/_forward()" — Third copy of the BMP3xx
  compensation formula (driver, test, launcher) · [H06]
- **TWIN.N198** ASSUME · `digital_twin/launch.py:278` — "MEASURE_RAW, datasheet's own no-compensation
  example" — Hard-coded SGP40 command bytes from the datasheet · [H06]
- **TWIN.N199** INVAR · `digital_twin/launch.py:426-432` — "main()'s own `finally` cannot be relied on
  to run first, so unwedge before either flush" — Order of unwedge and flushes in the interrupt path ·
  related: TWIN.T07 · [H06]
- **TWIN.N200** LIMIT · `digital_twin/launch.py:294-298, 413` — "`if not no_wdt_feed: watchdog.feed()`"
  — `--no-wdt-feed` only yields a count; the twin never resets (low) · [H06]

## digital_twin/run_generic_integration.py

- **TWIN.N201** INVAR · `digital_twin/run_generic_integration.py:24` — "deliberately reused, not
  reimplemented - see digital_twin/README.md" — Shares launch.py's parsers; the two CLIs must agree ·
  [H06]
- **TWIN.N202** LIMIT · `digital_twin/run_generic_integration.py:31, :346` — "`_CONFIG_DIR = \"digital_twin/config/\"`"
  — Config state lives at a fixed repo-relative path shared with other suites · covered-by: SCR.S09 ·
  [H06]
- **TWIN.N203** MIRROR · `digital_twin/run_generic_integration.py:36-39, :425-428` — "The same value and
  one-time placement the real firmware boot entry uses" — `gc.threshold(32768)` copied by hand from the
  generated boot entry · covered-by: SCR.S10 · [H06]
- **TWIN.N204** SUPPRESS · `digital_twin/run_generic_integration.py:99` — "`__hash__ = None # type: ignore[assignment]`"
  — mypy suppression for the unhashable idiom · [H06]
- **TWIN.N205** INVAR · `digital_twin/run_generic_integration.py:148-152` — "\"\" means in-memory only,
  matches machine.configure_fram_state_path(None)'s own documented meaning" — CLI convention · [H06]
- **TWIN.N206** LIMIT · `digital_twin/run_generic_integration.py:194-196` — "A multi-instance driver is
  also keyed \"driver_nameext\"; the plain key stays, first instance winning, since the fault vocabulary
  only speaks plain driver names" — `--fault`/`--hang` can only reach the first instance of a
  multi-instance driver · related: TWIN.T05 · [H06]
- **TWIN.N207** INVAR · `digital_twin/run_generic_integration.py:202-216` — "`if bus is None or bus._i2c is None:`
  / `chip = bus._spi.device`" — Reaches into private attributes of `src/` bus wrappers and generated
  variable names · related: TWIN.T12 · [H06] ⟨quote not matched at the anchor⟩
- **TWIN.N208** LIMIT · `digital_twin/run_generic_integration.py:298-308` —
  "`_WIRE_LOG_CLEAR_INTERVAL_MS = 5000`" — `wire_log` still grows for up to 5 s of traffic between
  clears · [H06]
- **TWIN.N209** SUPPRESS · `digital_twin/run_generic_integration.py:319-325` — "`except OSError: pass # already exists`"
  — Every mkdir `OSError` (not only EEXIST) is swallowed (low) · [H06]
- **TWIN.N210** INVAR · `digital_twin/run_generic_integration.py:330-335` — "Must run before anything
  else in the process registers a poll object" / "Must also run before anything constructs a real
  AsyUDPSocket" — Entry-point call order · related: TWIN.T07 · [H06]
- **TWIN.N211** SUPPRESS · `digital_twin/run_generic_integration.py:404-408` — "A real SIGINT can be
  re-delivered while this cleanup await is still in flight." — `KeyboardInterrupt` swallowed during
  cleanup · [H06]
- **TWIN.N212** INVAR · `digital_twin/run_generic_integration.py:389-395, :432-437` — "unwedge first
  rather than only in the outer handler" / "this is the only cleanup that runs at all" — Two cleanup
  sites, both must unwedge before flushing · related: TWIN.T07 · [H06]
- **TWIN.N213** LIMIT · `digital_twin/run_generic_integration.py:401-403` — "`main_task.cancel()`" —
  Cancelling the generated `main()` does not cancel its sibling tasks (no parent/child tracking,
  CLAUDE.md known hang #2); shutdown relies on process exit · [H06]

## digital_twin/segfault_stress_repro.py

- **TWIN.N214** SETTLED · `digital_twin/segfault_stress_repro.py:1-6` — "Manual, deliberately-aggressive
  concurrency stress tool for the (now root-caused and fixed ...) ... Hardcoded (README.md)." —
  Manual-only tool kept after the fix; no tier executes it · related: TWIN.T11 · [H06]
- **TWIN.N215** INVAR · `digital_twin/segfault_stress_repro.py:13-14` — "`import machine` / `import sensortask_wozi`"
  — No `configure_wiring()` call: relies on the lazy wozi default plan in `build/generated_src/` · [H06]
  ⟨quote not matched at the anchor⟩
- **TWIN.N216** LIMIT · `digital_twin/segfault_stress_repro.py:79-92` — "`prewarm_poll_set(port=port + 1000)`"
  — Unlike the other entry points it applies no UDP shim, no unwedge handler and no `gc.threshold()`
  (runs at the Unix default) (low) · [H06]
- **TWIN.N217** SUPPRESS · `digital_twin/segfault_stress_repro.py:103-106` — "`except (asyncio.CancelledError, Exception): pass`"
  — All exceptions during cleanup swallowed · [H06]
- **TWIN.N218** SUPPRESS · `digital_twin/segfault_stress_repro.py:111` — "`# type: ignore[arg-type]`" —
  mypy suppression on untyped opts dict · [H06]

## tests/test_digital_twin_bmp3xx.py

- **TWIN.N219** MIRROR · `tests/test_digital_twin_bmp3xx.py:1-2, 20-57` — "round-trips exactly through
  the real driver's own compensation formula" — The test uses its own copy of the formula
  (`_decode_temp_pressure()`/`_forward()`), not the driver's; a driver formula change would not reach it
  · [H06]
- **TWIN.N220** ASSUME · `tests/test_digital_twin_bmp3xx.py:110-112` — "well above the ~1e-4 worst-case
  quantization error this introduces, but still tight enough to prove the inversion is real" — Tolerance
  rationale · [H06]
- **TWIN.N221** LIMIT · `tests/test_digital_twin_bmp3xx.py:72-75` — "`assert reply[0] in (0x50, 0x60) # BMP384/BMP388 vs BMP390`"
  — Accepts either ID though the fake only ever serves 0x60; BMP388 path untested · related: TWIN.S03 ·
  [H06]
- **TWIN.N222** ASSUME · `tests/test_digital_twin_bmp3xx.py:214-215` — "real hardware would just
  silently accept/ignore it too" — Unverified claim encoded as a test expectation · [H06]

## tests/test_digital_twin_bus_hazard_concurrency.py

- **TWIN.N223** INVAR · `tests/test_digital_twin_bus_hazard_concurrency.py:17-19` — "growing the Unix
  port's pollfds array corrupts non-fd poll objects already in it, which is a segfault, not a test
  failure" — Prewarm must precede the imports · related: TWIN.T07 · [H06]
- **TWIN.N224** LIMIT · `tests/test_digital_twin_bus_hazard_concurrency.py:112-127, 185-227` — "Mid-run,
  not before or after: the point is a full ceiling of REST work landing while the sensor tasks are
  genuinely mid-transaction" — Twin bus transactions take zero time and never await, so interleaving can
  occur only between awaits; only wozi and dev are booted here (other four devices get no twin
  concurrency run in this file) · related: TWIN.T08 · [H06]
- **TWIN.N225** LIMIT · `tests/test_digital_twin_bus_hazard_concurrency.py:154-156` —
  "SGP40_I2C._reset()'s general-call broadcast ... must actually have fired at least once" — Asserts
  only the bus-log entry; no chip fake reacts to a general call · covered-by: TWIN.S02 · [H06]
- **TWIN.N226** RISK · `tests/test_digital_twin_bus_hazard_concurrency.py:177-178` — "wozi's own
  SGP40+BMP3xx-on-i2c1 pairing can never be confirmed on real hardware ... so this twin run is its
  actual verification" — wozi's bus grouping rests on the twin tier alone · [H06]
- **TWIN.N227** LIMIT · `tests/test_digital_twin_bus_hazard_concurrency.py:364-370` — "its
  shared_bus_log check assumes a short window that never wraps the twin I2C fake's bounded log deque" —
  Log-based assertions break on long runs because `I2C.log` keeps only 200 entries; this test takes ~75
  s · related: TEST.T04 · [H06]

## tests/test_digital_twin_fram.py

- **TWIN.N228** ASSUME · `tests/test_digital_twin_fram.py:80-82` — "still behaves like a real bus
  transaction rather than raising - zero-filled, not garbage/untouched" — Encodes an unverified claim
  about real MISO content · [H06]
- **TWIN.N229** LIMIT · `tests/test_digital_twin_fram.py:219-237` — "a malformed/unrecognized file ...
  must degrade to a blank chip, not raise" / "must leave the rest of memory at its blank default" —
  Silent-degrade on corrupt/truncated state is the tested contract · covered-by: TWIN.T10 · [H06]

## tests/test_digital_twin_isl29125.py

- **TWIN.N230** LIMIT · `tests/test_digital_twin_isl29125.py:2` — "Real-time INT-pin scheduling is
  exercised only through the synchronous set_illumination()/_produce_new_reading() hooks here" —
  Real-time behaviour is tested elsewhere only · [H06]
- **TWIN.N231** MIRROR · `tests/test_digital_twin_isl29125.py:425-427` — "Register-map behaviours
  measured against real silicon - see tests_hardware/README.md's probe." — Twin expectations tied to the
  C.11.1 conformance probe · related: TEST.S20 · [H06]
- **TWIN.N232** ASSUME · `tests/test_digital_twin_isl29125.py:420-422` — "3 x ~6.3ms, derived from p6's
  n-bit-counter model" — 12-bit cycle time is derived, not measured · [H06]

## tests/test_digital_twin_isl29125_autorange.py

- **TWIN.N233** LIMIT · `tests/test_digital_twin_isl29125_autorange.py:2` — "none of which any mock-tier
  test can prove because none of them has a chip whose gain actually changes" — Auto-range
  continuity/hysteresis/calibration proven only at twin tier (and NeoPixel rig) · related: TEST.T15 ·
  [H06]
- **TWIN.N234** LIMIT · `tests/test_digital_twin_isl29125_autorange.py:68-70` — "AutoRangeDwell defaults
  to 10 s ... The dwell itself is covered at tier 1" — Twin tests run with dwell 0; the default dwell is
  never exercised end to end here · [H06]
- **TWIN.N235** ASSUME · `tests/test_digital_twin_isl29125_autorange.py:123-125` — "4% covers the whole
  uncalibrated error budget: the nominal 26.67 against this unit's real 25.9 is a 2.96% high-range
  overstatement" — Tolerance tied to the fake's chosen ratio · [H06]
- **TWIN.N236** ASSUME · `tests/test_digital_twin_isl29125_autorange.py:253-255` — "Two cycles (606ms at
  16 bit) keeps the window inside the 1s SampleInterv" — Timing assumption tying fake cycle time to
  driver sample interval · [H06]

## tests/test_digital_twin_machine.py

- **TWIN.N237** INVAR · `tests/test_digital_twin_machine.py:178-180` — "A later \"fix\" returning fresh
  objects would break the whole interrupt path with nothing else failing." — Pin identity is
  load-bearing; guarded by this test · [H06]
- **TWIN.N238** LIMIT · `tests/test_digital_twin_machine.py:201-203` —
  "configure_fram_state_path()/flush_fram(), which has no dedicated wiring test either" — FRAM
  persistence hooks lack a wiring test · related: TWIN.T10 · [H06]
- **TWIN.N239** LIMIT · `tests/test_digital_twin_machine.py:272-274` — "an id nothing wires ... write()
  is logged and silently dropped, readinto() zero-fills the buffer" — Unwired SPI bus silently answers
  zeros · [H06]
- **TWIN.N240** LIMIT · `tests/test_digital_twin_machine.py:475-484` — "re-.init() the SAME Timer object
  from inside that object's currently-firing callback ... the just-fired ONE_SHOT alarm already being
  consumed" — Regression covers only a ONE_SHOT self-rearm; a PERIODIC self-rearm is untested · related:
  TWIN.T02 · [H06]
- **TWIN.N241** LIMIT · `tests/test_digital_twin_machine.py:518-520` — "The one live-timing test in this
  whole package ... not a precise-cadence assertion" — Timer cadence accuracy is never asserted ·
  covered-by: TWIN.T09 · [H06]

## tests/test_digital_twin_machine_uart.py

- **TWIN.N242** LIMIT · `tests/test_digital_twin_machine_uart.py:46-48` — "assert a floor well under
  that but far above zero, so the test is about the mechanism, not the exact clock" — Wire-time accuracy
  only loosely asserted · [H06]

## tests/test_digital_twin_real_website_integration.py

- **TWIN.N243** LIMIT · `tests/test_digital_twin_real_website_integration.py:1-3` — "the Unix-port
  counterpart to scripts/build_firmware.py's real ARM build, which can only be compiled here, never
  executed" — The frozen firmware image is never executed by any tier · related: SCR.T10 · [H06]
- **TWIN.N244** SETTLED · `tests/test_digital_twin_real_website_integration.py:121-134` — "\"wozi\" is
  hardcoded deliberately, not a stale device-specific leftover ... picking wozi ... once is complete
  coverage rather than a gap" — Only wozi's frozen website runs under the Unix port here; other five
  sites rely on buildgen tests · [H06]

## tests/test_digital_twin_run_generic_integration.py

- **TWIN.N245** LIMIT · `tests/test_digital_twin_run_generic_integration.py:192-193` —
  "parse_fault_spec()'s own vocabulary (launch.py) can only ever address a driver by its plain name,
  never per-instance" — Per-instance fault targeting impossible · related: TWIN.T05 · [H06]
- **TWIN.N246** LIMIT · `tests/test_digital_twin_run_generic_integration.py:227-229` — "main()'s real
  supervisor leaves several background tasks running after main_task.cancel(), the orphaned-task
  memory-pressure problem" — Only one end-to-end boot test allowed per process because of orphaned tasks
  · [H06]

## tests/test_digital_twin_scd30.py

- **TWIN.N247** LIMIT · `tests/test_digital_twin_scd30.py:2` — "Real-time RDY-pin scheduling is
  exercised only via the synchronous _produce_new_reading() hook here" — Real-time path tested elsewhere
  · [H06]
- **TWIN.N248** ASSUME · `tests/test_digital_twin_scd30.py:81-83` — "matching a real device silently
  accepting these" — Stop/soft-reset acceptance claim · covered-by: TWIN.S01 · [H06]

## tests/test_digital_twin_sensortask_integration.py

- **TWIN.N249** SETTLED · `tests/test_digital_twin_sensortask_integration.py:1-3` — "Deliberately
  wozi-only - SPECIFICATION.md Part E.2.1 says why." — Middle tier boots only wozi · [H06]
- **TWIN.N250** LIMIT · `tests/test_digital_twin_sensortask_integration.py:425-439, 461-463` —
  "Deliberately does NOT drive this through main()/start_and_check_tasks()" / "just over the hardcoded
  8000ms WDT timeout" — Watchdog check uses its own 1 s feed loop, so it detects only stalls approaching
  8 s; the real supervisor's feed path is not the one under test · [H06]
- **TWIN.N251** LIMIT · `tests/test_digital_twin_sensortask_integration.py:610-612` — "currently
  \"0.0.0.0\" - a twin-fidelity gap, see digital_twin/README.md - not a real product bug" — DNS answer
  is the AP-mode 0.0.0.0 address in the twin · related: TWIN.S05 · [H06]

## tests/test_digital_twin_sgp40.py

- **TWIN.N252** ASSUME · `tests/test_digital_twin_sgp40.py:137-139` — "no crash - real hardware would
  just not respond usefully either" — Unknown-command behaviour asserted without silicon evidence ·
  related: TWIN.T01 · [H06]

## tests/test_digital_twin_uart_link.py

- **TWIN.N253** LIMIT · `tests/test_digital_twin_uart_link.py:353-355, 440-442` — "The twin records
  every delivered byte in an unbounded wire_log ... it is the harness growing, not the driver" — Twin
  instrumentation distorts heap measurements unless cleared · [H06]

## tests/test_digital_twin_unix_port_gc_unwedge.py

- **TWIN.N254** LIMIT · `tests/test_digital_twin_unix_port_gc_unwedge.py:17-29` — "The wedged state
  itself ... is deliberately NOT constructed here: it is unreachable from Python." — The recovery is
  only tested on the healthy path; the real reproduction is historical · related: TWIN.T07 · [H06]

## tests/test_digital_twin_webserver_concurrency_{arzi,dev,grkizi,klkizi,schlafzi,wozi}.py

- **TWIN.N255** INVAR · `tests/test_digital_twin_webserver_concurrency_wozi.py:10-12 (same in all six)`
  — "First, before the library boots a device and bursts real connections at it: pollfds growth is a
  Unix-port segfault otherwise" — Import-time prewarm order · related: TWIN.T07 · [H06]

## tests_hardware/manual/manual_sensor_accuracy.py

- **TWIN.N256** LIMIT · `tests_hardware/manual/manual_sensor_accuracy.py:20` — "The digital twin's own
  README explicitly flags its calibration block as 'not sourced from a real chip'" — Twin fidelity gap:
  BMP compensation only validated by this manual check. · related: TWIN.T01 · [H07]

## tests_hardware/README.md

- **TWIN.N257** LIMIT · `tests_hardware/README.md:397-405` — "it raises a `FileNotFoundError` naming the
  path rather than skipping" — Conformance probe needs a built Unix port; disagreements decided "never
  from the fake". · related: TEST.S20 · [H08]

## scripts/run_unix_port_integration.sh

- **TWIN.N258** SETTLED · `scripts/run_unix_port_integration.sh:6-8` — "the twin needs its own
  MICROPYPATH with no \"tests\" segment (digital_twin/README.md's \"never together\" rule)" — The twin
  must never share test.sh's module path. · related: SCR.T04 · [H09]
- **TWIN.N259** LIMIT · `scripts/run_unix_port_integration.sh:24-26` — "There is no --soak flag any
  more: the HTTP+memory-trend soak check moved host-side" — Soak only exists as the suite's Run 11. ·
  [H09]

## scripts/_digital_twin_ci_suite.py

- **TWIN.N260** LIMIT · `scripts/_digital_twin_ci_suite.py:45-48` — "A loose set on purpose - some
  modules are not guaranteed to log at all in these short runs" — Verbose-log check only confirms
  logging flows, pins no module's output. · [H09]
- **TWIN.N261** MIRROR · `scripts/_digital_twin_ci_suite.py:61-62` — "_NTP_ERRNO_NO_REPLY = 21 #
  asy_ntp_client.py's own no-reply errno" — Hand copy of an `src/` errno. · related: GEN.T06 · [H09]
- **TWIN.N262** MIRROR · `scripts/_digital_twin_ci_suite.py:72-82` — "_NO_PERSIST_WHEN_FRAM_FAULTED =
  frozenset({\"scd30\", \"bmp3xx\", \"isl29125\"})" — Hand-kept driver sets (`_MEASUREMENT_DRIVERS`,
  `_NO_PERSIST_WHEN_FRAM_FAULTED`, `_PERSISTED_ERROR_MODULES`) whose reasons live in
  digital_twin/README.md. · related: GEN.T06 · [H09]
- **TWIN.N263** MIRROR · `scripts/_digital_twin_ci_suite.py:99-106` — "_WIFI_SCRIPTED_FAILURES = 5 #
  asy_wifi_service.py's conn_fail_to_hotspot" — Hand copies of `src/` thresholds (hotspot fallback
  count, supervisor 3-restart budget, episode rule's 1 slot). · related: GEN.T06 · [H09]
- **TWIN.N264** ASSUME · `scripts/_digital_twin_ci_suite.py:122-125` — "100, not wozi's original 40:
  dev's two extra uart_link instances mean more one-time post-boot settling" — Soak warmup length from
  one measurement. · [H09]
- **TWIN.N265** ASSUME · `scripts/_digital_twin_ci_suite.py:134-137` — "consecutive 25ms gc.mem_free()
  samples are heavily autocorrelated" — Trend tolerance (3 x quarter pstdev) grounded in a README
  measurement. · [H09]
- **TWIN.N266** INVAR · `scripts/_digital_twin_ci_suite.py:295-308` — "TOLERANT: answers {} for a
  /status it could not parse" / "STRICT, for assertion sites: raises" — Assertions must use the strict
  reader; convention only. · related: TEST.T17 · [H09]
- **TWIN.N267** ASSUME · `scripts/_digital_twin_ci_suite.py:383-385` — "the bench Pi4 needs ~8s where an
  x86 runner needs ~2s" — Host-speed figures motivating poll-not-sleep. · related: TEST.T04 · [H09]
- **TWIN.N268** INVAR · `scripts/_digital_twin_ci_suite.py:487-489` — "SIGINT, not SIGTERM/terminate():
  run_generic_integration.py's own graceful-shutdown path (FRAM/SCD30 flush) only runs on
  KeyboardInterrupt" — Shutdown contract with the twin runner. · related: SCR.T04 · [H09]
- **TWIN.N269** LIMIT · `scripts/_digital_twin_ci_suite.py:840-842` — "three at once exhaust the
  task-restart budget and the device reboots itself mid-run" — Faults must be applied one per process;
  simultaneous multi-driver faults are not tested in Run 5c. · [H09]
- **TWIN.N270** WORKAROUND · `scripts/_digital_twin_ci_suite.py:944-946` — "Only possible because of
  _unix_port_udp_addr_shim.py, which works around three Unix-port socket quirks" — Twin-side shim for
  Unix-port UDP quirks; removal trigger: none stated. · related: TWIN.T07 · [H09]
- **TWIN.N271** ASSUME · `scripts/_digital_twin_ci_suite.py:962-967` — "the interpreter lacked
  CAP_NET_BIND_SERVICE, so the bind to port 53 silently failed" — Run 7 depends on setcap; a failed bind
  is silent. Timeout left at 90 s. · related: SCR.S06 · [H09]
- **TWIN.N272** ASSUME · `scripts/_digital_twin_ci_suite.py:987-988` — "This once asserted counter==0,
  under a pre-WP1 in-memory-only assumption real CI never exercised" — Record of a stale assertion
  corrected. (low) · [H09]
- **TWIN.N273** SETTLED · `scripts/_digital_twin_ci_suite.py:1000-1001` — "192.0.2.1: RFC 5737
  TEST-NET-1, guaranteed non-routable" — NTP-unreachable scenario relies on TEST-NET-1 staying
  non-routable on the runner. · [H09]
- **TWIN.N274** ASSUME · `scripts/_digital_twin_ci_suite.py:1042-1044` — "--duration 15, not 0: SGP40's
  first bus access now queues behind BMP3xx's and SCD30's own FRAM startup I/O" — Run 10's duration
  tuned to boot ordering. · [H09]
- **TWIN.N275** RISK · `scripts/_digital_twin_ci_suite.py:1176-1182` — "One retry, a second fully
  independent boot, separates a residual bad draw from a real leak" — Soak memory-trend verdict is
  retried once; HTTP/WDT/shutdown failures are never retried. · related: SCR.T04 · [H09]
- **TWIN.N276** LIMIT · `scripts/_digital_twin_ci_suite.py:1264-1266` — "Neopixel and notification never
  appear, being GPIO-only" — Fault matrix covers only bus-attached drivers; uart_link instances are not
  fault-injected. · related: TWIN.T05 · [H09]

## toolchain/versions.toml

- **TWIN.N277** PLATFORM · `toolchain/versions.toml:41-52` — "MEMP_NUM_TCP_PCB = 9" — lwIP limits apply
  to the firmware only; the twin runs on the host Linux stack and models none of them. · related:
  TWIN.T08 · [H09]

## pyproject.toml

- **TWIN.N278** SUPPRESS · `pyproject.toml:291-303` — "ANN401, category 6 - a dynamically __import__()ed
  module ... has no static type" — digital_twin/run_generic_integration.py,
  tests_scripts/test_buildgen_twin_wiring.py, three tests scenario libraries: ANN401. · [H09]

## tests_scripts/test_buildgen_twin_wiring.py

- **TWIN.N279** ASSUME · `tests_scripts/test_buildgen_twin_wiring.py:29-31` — "digital_twin/machine.py
  has no MicroPython-only import at module scope (only individual method bodies do)" — Importing the
  twin's `machine` under CPython depends on this convention; nothing enforces it · related: TWIN.T12 ·
  [H10]
- **TWIN.N280** MIRROR · `tests_scripts/test_buildgen_twin_wiring.py:103-105` — "the two sides are
  hand-kept in sync for one fixed driver set" — Twin chip fakes (`_build_i2c_chip()`) and
  `BUS_ATTACHED_DRIVERS` are hand-synced; mismatch fails loud only when reached · related: TWIN.T12 ·
  [H10]
- **TWIN.N281** LIMIT · `tests_scripts/test_buildgen_twin_wiring.py:50` —
  "@pytest.mark.parametrize(\"device\", [\"wozi\", \"dev\"])" — Load-and-apply end-to-end check covers
  wozi/dev only · [H10]

## tests_scripts/test_digital_twin_boot_contiguity.py

- **TWIN.N282** LIMIT · `tests_scripts/test_digital_twin_boot_contiguity.py:46-48` — "Twin units (32 B
  blocks, x86-64) and twin-only - the board's own tripwire stays the hardware test." — 64-bit Unix-port
  heap, not rp2; results do not transfer numerically to silicon · covered-by: TWIN.T06 · [H10]

## tests_scripts/test_digital_twin_ci_suite_ceiling.py

- **TWIN.N283** LIMIT · `tests_scripts/test_digital_twin_ci_suite_ceiling.py:19-42` — "read the request,
  answer nothing - the reject-when-full shape" — Run 11b is tested against CPython `http.server` fakes
  and fully stubbed spawn/wait/shutdown; the real twin/Microdot refusal is exercised only by the live CI
  suite · related: SCR.T04 · [H10]
- **TWIN.N284** INVAR · `tests_scripts/test_digital_twin_ci_suite_ceiling.py:126-127` — "The README's
  bar is \"served 200 with a parsed body\"" — Run 11b must fail a 200 without parseable JSON · [H10]

## tests_scripts/test_digital_twin_ci_suite_errcount.py

- **TWIN.N285** MIRROR · `tests_scripts/test_digital_twin_ci_suite_errcount.py:100-134` — "the two
  tables are hand-kept separately, and a driver present in one but not the other raises mid-run" — Twin
  CI suite tables `_BUS_FAULT_OPS`, `_DRIVER_ERRCOUNT_NAME`, `_NO_PERSIST_WHEN_FRAM_FAULTED`,
  `_MEASUREMENT_DRIVERS`, `_IN_MEMORY_ONLY_ERROR_SOURCES`, `_PERSISTED_ERROR_MODULES` are hand-kept;
  cross-checked here and outward against i2c/spi drivers of the real device set · covered-by: GEN.T06 ·
  [H10]
- **TWIN.N286** LIMIT · `tests_scripts/test_digital_twin_ci_suite_errcount.py:125-127` — "which let the
  ISL29125 be absent from all of them and silently skipped from the day it shipped" — Past silent
  coverage gap; the outward check is scoped to i2c/spi only · [H10]
- **TWIN.N287** SETTLED · `tests_scripts/test_digital_twin_ci_suite_errcount.py:328-333` — "SGP40 is the
  one measurement driver outside the reset-to-0-with-FRAM-faulted set ... two halves of one decision" —
  Deliberate SGP40 asymmetry in the twin suite's persistence assertions · [H10]
- **TWIN.N288** INVAR · `tests_scripts/test_digital_twin_ci_suite_errcount.py:140-142,172-173` — "{} for
  an unreadable /status reads as counter 0 with an empty history ... as Runs 4, 5c and 8 all did" —
  Vacuous-pass class: tolerant `_errcount()` for polling vs strict
  `_errcount_required()`/`_errcount_all()` for assertions · related: TEST.T01 · [H10]
- **TWIN.N289** INVAR · `tests_scripts/test_digital_twin_ci_suite_errcount.py:251-252` — "Run 4 keeps
  `entry.get(\"counter\", -1) == 0` rather than a bare `== 0`" — Fail-closed default pinned because it
  looks like a typo · [H10]

## tests_scripts/test_digital_twin_ci_suite_soak.py

- **TWIN.N290** LIMIT · `tests_scripts/test_digital_twin_ci_suite_soak.py:2-3` — "Host-driven request
  cycling itself is exercised end to end by scripts/run_digital_twin_ci.sh ... not re-mocked here" —
  Only the parsing/trend arithmetic is unit-tested · [H10]

## tests_scripts/test_digital_twin_generated_boot.py

- **TWIN.N291** LIMIT · `tests_scripts/test_digital_twin_generated_boot.py:43-47` — "No real static
  content is needed - this suite never requests \"/\"" — Boots with a stub `frozen_html`; smoke = 5 GETs
  expecting 200 + JSON object; no PUT, no static route · [H10]
- **TWIN.N292** ASSUME · `tests_scripts/test_digital_twin_generated_boot.py:31-41` — "boot-to-first-200
  lands between ~4.5s and ~6.3s across the six real devices, dev slowest" — `_TWIN_DURATION_S = 15`/`_BOOT_TIMEOUT_S = 30`
  sized from a dated measurement · related: PERF.T06 · [H10]

## tests_scripts/test_twin_never_needs_tests_on_its_path.py

- **TWIN.N293** INVAR · `tests_scripts/test_twin_never_needs_tests_on_its_path.py:1-3,17-20` —
  "_http_client.HttpResponse.json() imports tests/_strict_json lazily, and the twin's own MICROPYPATH
  carries no tests/" — Only digital_twin/_http_client.py may import `_strict_json`, lazily; no twin
  module may call `.json()` · [H10]
- **TWIN.N294** LIMIT · `tests_scripts/test_twin_never_needs_tests_on_its_path.py:27-31,24-25` — "Every
  MICROPYPATH the twin is started with, from the two places that set one." — Only
  scripts/_digital_twin_ci_suite.py and run_unix_port_integration.sh are scanned;
  test_digital_twin_generated_boot.py's and tests_js' twin launches set their own MICROPYPATH unscanned;
  only top-level digital_twin/*.py; `.json()` detection is by method name with no args · related:
  TWIN.T11 · [H10]
- **TWIN.N295** SETTLED · `tests_scripts/test_twin_never_needs_tests_on_its_path.py:51-52` — "If tests/
  is ever added to it, this guard is obsolete rather than failing - delete it then, do not widen it." —
  Stated removal condition for the guard · [H10]

## tests_js/_live_twin_command.js

- **TWIN.N296** MIRROR · `tests_js/_live_twin_command.js:67-70` — "\"\", // in-memory only - see
  digital_twin/README.md's \"FRAM persistence\" section for this convention" — empty state path =
  in-memory, a digital_twin/ CLI convention · [H11]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **TWIN.N297** LIMIT · `SPECIFICATION.md:209-213` — "every tier's write check stops at the driver's own
  guard ... Both chip fakes stop at the driver guard and cannot prove this." — Only the flash tier
  proves BP0|BP1 refusal; mock/twin fakes cannot. · related: HW.S07 · [H12]

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)

- **TWIN.N298** LIMIT · `SPECIFICATION.md:512-520` — "every number above is a digital-twin measurement
  ... `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time" — Twin cannot
  measure FRAM wire time under contention. · related: TWIN.T04 · [H12]

## SPECIFICATION.md Part A.10 (Digital twin, 655-686)

- **TWIN.N299** INVAR · `SPECIFICATION.md:663-667` — "any new module joins the digital twin, provided it
  can form a complete chain ... A module that can't yet complete the chain stays out until the missing
  piece exists" — Review-only obligation; deferral allowed. · [H12]
- **TWIN.N300** ASSUME · `SPECIFICATION.md:669-673` — "a `strategy.matrix` over all 6 real device
  variants ... through its 14-run suite" — Dated counts (6 devices, 14 runs). · covered-by: DOC.T08 ·
  [H12]
- **TWIN.N301** WORKAROUND · `SPECIFICATION.md:681-684` — "three confirmed Unix-port-only `socket`
  quirks ... worked around entirely from twin-side code (`digital_twin/_unix_port_udp_addr_shim.py`)" —
  Unix-port defect workaround; removal trigger none stated. · related: TWIN.T07 · [H12]

## SPECIFICATION.md Part B.14.1 (`unix_kbd_intr`, 1116-1213)

- **TWIN.N302** LIMIT · `SPECIFICATION.md:1145-1150` — "`unwedge_heap_after_interrupt()` patches that
  one specific downstream symptom, but does nothing for an interrupt landing mid some *other*
  non-reentrant operation" — Twin helper's scope limit; kept as defence in depth. · covered-by: TWIN.T07
  · [H12]

## SPECIFICATION.md Part C.4 (Layer 3 Reader, 1624-1697)

- **TWIN.N303** ASSUME · `SPECIFICATION.md:1656-1658` — "a test that needs several drivers to log a
  chip-healthy error gives each its own process ... (Run 5c; measured both ways)" — Test design
  constrained by the reboot budget. · [H12]

## SPECIFICATION.md Part C.11 / C.11.1 (Design decisions; conformance probe, 2310-2353)

- **TWIN.N304** LIMIT · `SPECIFICATION.md:2327-2329` — "A new SPI sensor sharing an already-occupied SPI
  bus id with the FRAM chip is not automatically supported by the twin's single-device-per-bus-id
  wiring." — Twin fidelity gap for shared SPI buses. · related: DOC.S22 · [H12]
- **TWIN.N305** INVAR · `SPECIFICATION.md:2325-2333` — "Digital-twin extension — required, not optional
  ... Do this the same session as promotion ... Also update `html/definitions/<device>.json` ... Same
  session, not deferred." — Review-only promotion obligations; definitions hand-update contradicts
  K.4/K.8. · covered-by: DOC.S03 · [H12]
- **TWIN.N306** LIMIT · `SPECIFICATION.md:2337-2344` — "A chip fake drifts from the part it models
  silently: every test still passes, because the tests and the fake share the same wrong assumption." —
  Stated fake-fidelity risk; guard exists only for ISL29125. · covered-by: TEST.S20 · [H12]

## SPECIFICATION.md Part E.6 / E.6.1-E.6.6 (Shared behaviours, real-hardware tier, 3090-3225)

- **TWIN.N307** LIMIT · `SPECIFICATION.md:3161-3162` — "The RP2040's own hotspot/AP mode is untestable
  in the digital twin (no AP-mode DHCP/second-radio model)." — Twin fidelity gap. · related: TWIN.S05 ·
  [H12]

## SPECIFICATION.md Part E.7 (Twin soak wall clock measures GC timing, 3229-3269)

- **TWIN.N308** ASSUME · `SPECIFICATION.md:3240-3253` — "Measured on the dev variant (2026-09-11) ...
  44.07 / 58.43 / 61.49 s" — Dated measurement against a retired runner. · [H12]
- **TWIN.N309** SETTLED · `SPECIFICATION.md:3257-3261` — "Never bisect a twin soak's runtime to a code
  change." — Do-not-re-diagnose rule. · [H12]

## SPECIFICATION.md Part E.8 (Measurement traps, 3271-3362)

- **TWIN.N310** LIMIT · `SPECIFICATION.md:3288-3299` — "The twin's `UARTLink.wire_log` is unbounded ...
  Fixed by giving `run_generic_integration.py` its own periodic clearer (`_wire_log_clearer()`, every
  5s" — Twin fake grows without bound; mitigated by clearer. · [H12]
- **TWIN.N311** LIMIT · `SPECIFICATION.md:3309-3317` — "A 64-bit twin doubles dicts, lists and frames
  but not strings ... a non-frozen one spends ~541 KB on imports ... an unthrottled twin serves 50-100x
  faster than the board" — Twin heap/throughput infidelity. · covered-by: TWIN.T06 · [H12]

## SPECIFICATION.md Part E.9 (Driver/DUT process separation, 3364-3421)

- **TWIN.N312** INVAR · `SPECIFICATION.md:3366-3372` — "Anything that can run outside the digital twin's
  own MicroPython process without losing coverage must run outside it." — Standing rule; review-only. ·
  [H12]
- **TWIN.N313** INVAR · `SPECIFICATION.md:3374-3378` — "Get it out through the narrowest possible
  channel (a log line on a fixed timer ... `_mem_sampler()`)" — DUT-side exception. · [H12]
- **TWIN.N314** ASSUME · `SPECIFICATION.md:3404-3406` — "two independent `wozi` boots in a row,
  3298/2854 and 4361/2847 bytes" — Dated measurement. · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **TWIN.N315** LIMIT · `SPECIFICATION.md:3555-3558` — "`asyncio.run()`'s `KeyboardInterrupt` handling
  has a real gap ... its own `try`/`finally` never runs" — Upstream asyncio gap; twin `__main__` blocks
  compensate with an outer synchronous cleanup. · [H13]
- **TWIN.N316** WORKAROUND · `SPECIFICATION.md:3557-3558` — "`digital_twin/`'s `__main__` blocks re-run
  cleanup from plain synchronous code in an outer `except KeyboardInterrupt:`" — Workaround for the
  asyncio.run SIGINT gap; removal trigger none stated. · [H13]

## SPECIFICATION.md Part F.5.1 — I2C/SPI deinit no-ops

- **TWIN.N317** LIMIT · `SPECIFICATION.md:3706-3708` — "One deliberate divergence stays: both fakes hand
  back a **fresh object** per construction rather than a singleton" — Deliberate fake fidelity gap. ·
  related: TEST.T05 · [H13]

## SPECIFICATION.md Part F.5.2 — rp2 SPI RX-overrun EIO

- **TWIN.N318** MIRROR · `SPECIFICATION.md:3716-3719` — "modeled at the bus level in
  `tests/machine.py`'s SPI fake and in `digital_twin/machine.py`'s (`rx_overrun` ...
  `rx_overrun_remaining` ... `inject_fault()`" — Two fakes must reproduce the ≥32-byte, read-only
  condition. · related: TWIN.T05 · [H13]
- **TWIN.N319** LIMIT · `SPECIFICATION.md:3719-3722` — "The twin's chip-level `_fram_chip.py`
  `FaultInjector` ... cannot express the size threshold below, so a 1-byte status-register read would
  raise there when real hardware could not" — Twin fault injector over-approximates this fault. ·
  related: TWIN.T05 · [H13]

## SPECIFICATION.md Part F.6 — SIGINT during gc_collect() wedges the Unix-port heap

- **TWIN.N320** PLATFORM · `SPECIFICATION.md:4052-4065` — "measured at the same ~5% rate on Unix ports
  built from both `v1.28.0` and `v1.29.0` ... `MemoryError: memory allocation failed, heap is locked`" —
  Unix-port-only upstream race (stuck `GC_COLLECT_FLAG`). · related: TWIN.T07 · [H13]
- **TWIN.N321** WORKAROUND · `SPECIFICATION.md:4067-4076` — "**The recovery is `gc.collect()`, and only
  `gc.collect()`.** ... **`micropython.heap_unlock()` is not a substitute**" —
  `digital_twin/unix_port_gc_unwedge.py`; removal trigger: none — kept as defence in depth after the
  root-cause fix (4117-4121). · related: TWIN.T07 · [H13]
- **TWIN.N322** ASSUME · `SPECIFICATION.md:4069-4070` — "Verified 3/3 on captured failures." —
  Small-sample verification. · [H13]
- **TWIN.N323** ASSUME · `SPECIFICATION.md:4095-4101` — "**This was not reproduced locally** ... offered
  as the one concrete, source-confirmed gap ... not as a confirmed root cause" — The `grkizi` `exit code -9`
  failure's cause is unconfirmed. · [H13]
- **TWIN.N324** SETTLED · `SPECIFICATION.md:4107-4121` — "**Amendment (2026-09-15): the root cause above
  is now closed** ... `unwedge_heap_after_interrupt()`'s three call sites are kept, deliberately, as
  defense in depth" — Do-not-remove marker; call sites `digital_twin/run_generic_integration.py:395, 435`,
  `digital_twin/launch.py:432`. · related: TWIN.T07 · [H13]
- **TWIN.N325** LIMIT · `SPECIFICATION.md:4122-4126` — "they still prove the *shutdown paths themselves*
  stay correct, just not this specific recovery branch within them" — The unwedge branch is no longer
  exercised by any real interrupt. · related: TWIN.T07 · [H13]

## SPECIFICATION.md Part H.7 — Digital twin integration / connection ceiling

- **TWIN.N326** LIMIT · `SPECIFICATION.md:4600-4605` — "The ordinary twin runs on the Unix port, which
  has **no lwIP at all** ... **cannot** validate a PCB ceiling ... an ad-hoc instrument, never a gate" —
  Twin fidelity gap for connection limits. · covered-by: TWIN.T08 · [H13]

## SPECIFICATION.md Part I.4 — Multi-stage memory-error scheme, (a)-(e)

- **TWIN.N327** SETTLED · `SPECIFICATION.md:5044-5058` — "**One narrow, evidence-backed exception**:
  `digital_twin/run_generic_integration.py`'s `_mem_sampler()` calls `gc.collect()` ... don't re-flag it
  without new evidence" — Do-not-reflag marker for the sampler's collect. · related: TEST.T03 · [H13]
- **TWIN.N328** ASSUME · `SPECIFICATION.md:5052-5055` — "measured on a genuinely healthy `wozi` run:
  `min=99808, max=1347104` across 20 cycles, a false-positive \"trend declined by 413990 bytes\" against
  an 18318-byte tolerance" — Single dated measurement justifying the exception. · [H13]

## SPECIFICATION.md Part I.4 — (f), (f.1), (g)

- **TWIN.N329** LIMIT · `SPECIFICATION.md:5112-5116` — "Bounds are derived from the measured worst case
  with margin and are **twin-only**. The board ... does **not** reproduce the twin's two headline ratios
  at its own fill" — Boot-contiguity bounds are not a silicon property. · related: TWIN.T06, HW.T16 ·
  [H13]

## SPECIFICATION.md Part K.5 — Digital twin

- **TWIN.N330** INVAR · `SPECIFICATION.md:5802` — "A chip fake is **required, not optional**, the same
  session as promotion (C.11 item 9)" — Process rule. · related: TWIN.T01 · [H13]

## SPECIFICATION.md Part L.4 — Generator pipeline

- **TWIN.N331** ASSUME · `SPECIFICATION.md:6284-6285` — "No hand-typed wiring literal exists anywhere."
  — Absolute claim; the FIXED_ADDRESSES/RDID tables above are hand-typed wiring facts. · related:
  TWIN.T12 · [H13]
- **TWIN.N332** LIMIT · `SPECIFICATION.md:6293-6295` — "**Known twin limitation**: `machine.py`'s
  single-chip SCD30/FRAM globals only persist the *last-wired* instance's NVM state across a simulated
  reboot on a multi-instance device" — Twin fidelity gap for multi-instance devices. · related: TWIN.T10
  · [H13]

## SPECIFICATION.md Part M.1.2 — Measured chip behaviour

- **TWIN.N333** MIRROR · `SPECIFICATION.md:6643` — "`digital_twin/_isl29125_chip.py` models every row" —
  Chip fake ↔ measured behaviour table. · related: TWIN.T01 · [H13]

## CLAUDE.md

- **TWIN.N334** INVAR · `CLAUDE.md:385-387` — "The same check applies inside the digital twin" —
  Convention only. · related: TWIN.T10 · [H14]
- **TWIN.N335** ASSUME · `CLAUDE.md:668-669` — "Measured at ~5% of interrupts on Unix ports built from
  both `v1.28.0` and `v1.29.0`" — Measurement. · [H14]
- **TWIN.N336** WORKAROUND · `CLAUDE.md:670-680` — "`unix_port_gc_unwedge.py`'s calls now stay wired in
  purely as defense in depth" — Superseded by the root fix; still wired into digital_twin/launch.py:20
  and run_generic_integration.py:28. Removal trigger: none stated. · covered-by: TWIN.T07 · [H14]

## README.md

- **TWIN.N337** ASSUME · `README.md:430-431` — "every real device is fully supported end-to-end via
  `--device`" — The four generated devices' definitions never pass the real validator or renderer; the
  live PUT matrix and cross-browser smoke are wozi-only. · related: WEB.T12, TEST.S19 · [H14]
- **TWIN.N338** DRIFT · `README.md:614-467 vs 579-582, 614-619 (agent cited README.md:465-467 vs 579-582, 614-619)`
  — "default in-memory only" vs "letting its `finally` block flush the FRAM twin's state to disk" and
  "`digital_twin/scd30_state.json`, this entry point's own default persisted path" —
  run_generic_integration.py defaults both paths to None (:124-125, 146-152), and
  scripts/run_unix_port_integration.sh:78 passes neither. The walkthrough's FRAM/SCD30-survives-restart
  steps don't hold without the flags. · related: TWIN.T10 · [H14] ⟨re-anchored: quote found at line 614⟩
- **TWIN.N339** MIRROR · `README.md:468-469` — "`--gc-threshold N` — override the boot-time
  `gc.threshold()` (default `32768`, matching every real firmware boot)" — Hand-copied constant
  (run_generic_integration.py:39). Twin launches run only at 32768 outside the CI suite. · covered-by:
  SCR.S10 (related TEST.T18) · [H14]
- **TWIN.N340** LIMIT · `README.md:470-472` — "the twin's own only remaining contribution to the
  memory-trend soak check below" — Heap trend is sampled on the 64-bit Unix-port heap. · related:
  TWIN.T06 · [H14]
- **TWIN.N341** SETTLED · `README.md:474-478` — "There is no standalone `--soak` flag any more - the
  automated HTTP+memory-trend soak check moved host-side" — SPEC E.9; Run 11. · [H14]
- **TWIN.N342** LIMIT · `README.md:504-507` — "This standalone launcher is twin-only (no `src/` import)"
  — `digital_twin/launch.py` exercises only the fakes. · related: TWIN.T11 · [H14]
- **TWIN.N343** ASSUME · `README.md:510-514` — "drives `digital_twin/run_generic_integration.py` through
  fourteen sequential runs ... soak at both `gc.threshold()` configurations" — Verified: Runs 1-11 plus
  5b, 5c and 11b (scripts/_digital_twin_ci_suite.py:633-1111, :1240), per pass at -1 and 32768 (:1310).
  · related: SCR.T04 · [H14]
- **TWIN.N344** LIMIT · `README.md:579-582` — "a hard `kill`/`pkill` skips that cleanup" — Twin state is
  flushed only at clean shutdown. · covered-by: TWIN.T10 · [H14]
- **TWIN.N345** ASSUME · `README.md:621-624` — "the affected sensor's reader task should fail, log it,
  and recover on its own once the fault count is exhausted" — Expected recovery, asserted but not
  demonstrated here. · related: TWIN.T05 · [H14]
- **TWIN.N346** ASSUME · `README.md:636-639` — "`machine.reset()` raises `SimulatedResetError` instead,
  which is expected and harmless ... so the same process keeps serving afterward" — The supervisor's
  reboot branch returns out of `main()` ~4 s before the reset. That the twin keeps serving afterwards is
  asserted, not shown. · related: XCUT.S11, TWIN.T02 · [H14]

## BACKLOG.md

- **TWIN.N347** ASSUME · `BACKLOG.md:311-314` — "not a predictor of real-hardware cost in either
  direction" — Twin `ResetErrors` timings are a harness baseline only. · related: TWIN.T06 · [H15]
- **TWIN.N348** SETTLED · `BACKLOG.md:611-616` — "must never be bisected to a code change" — Twin soak
  wall clock is GC-timing-driven; budget sits above the observed range. · related: TEST.T04 · [H15]
- **TWIN.N349** ASSUME · `BACKLOG.md:750-753` — "the Unix port's allocator/heap behavior isn't
  guaranteed identical to rp2040's real one" — Twin "no leak" conclusion may not transfer. · related:
  TWIN.T06 · [H15]
- **TWIN.N350** TODO · `BACKLOG.md:868-871` — "Still open: the NTP-outage-x-bus-load fault recombination
  has no twin/mock-tier equivalent" — Adding bus load to twin Run 9 is the named extension; "not chased
  yet". · [H15]

## HEAP_FRAGMENTATION_MEASUREMENTS.md (current, 393 lines; owning area HW)

- **TWIN.N351** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:97-100` — "mem_alloc() deltas undercount
  silently when a collection fires inside the window." — Once understated a figure 3.9x; identity check
  + oversize heap required. · [H15]
- **TWIN.N352** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:190-195` — "The twin's fakes allocate where
  the board's C objects do not." — Fake FRAM 262,144 B image, `SPI.write`'s `bytes(buf)`+log tuple,
  Timer/WDT fakes, WLAN call-log deque (804 B). · related: TWIN.T06 · [H15]
- **TWIN.N353** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:196-199` — "The twin hides write-phase
  failures unless told not to." — A `MemoryError` after headers only reaches `err_s`, silent at default
  debug. · related: TEST.T18 · [H15]
- **TWIN.N354** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:215-219` — "Absolute bytes do not ... so it
  also ranks allocation walls wrongly." — 64-bit twin; quantitative serving work needs the 32-bit twin.
  · related: TWIN.T06 · [H15]
- **TWIN.N355** ASSUME · `HEAP_FRAGMENTATION_MEASUREMENTS.md:223-232` — "Last derived: ~455k bare on the
  flag-free binary, 508k under the probe to build_system(), 560k to the starter list" — Dated
  calibration (~44 % fill [HW]); must be re-derived after any binary/manifest/object-graph change. ·
  [H15]
- **TWIN.N356** ASSUME · `HEAP_FRAGMENTATION_MEASUREMENTS.md:234-238` — "the 32-bit twin bracketed at
  560k-600k, archive §7Q.9" — Serving calibration: 2,324 B lwIP cost per connection; CPU-quota
  throttling; unthrottled twin optimistic near the wall. · related: TWIN.T08 · [H15]
- **TWIN.N357** SETTLED · `HEAP_FRAGMENTATION_MEASUREMENTS.md:295-296` — "Both frozen twins are ad-hoc
  instruments, never a committed build variant or CI gate (owner, 2026-09-23)." — · [H15]
- **TWIN.N358** LIMIT · `HEAP_FRAGMENTATION_MEASUREMENTS.md:298-311` — "Scratchpad tools, rebuilt from
  these descriptions when needed" — `probe.py`, `fgraph.py`, `sweep.py`, `twin_wrap.py`… are not
  committed. · [H15]

## Commit messages (chronological)

- **TWIN.N359** LIMIT · `commit 51d0c21` — "a new SPI sensor sharing an already-occupied bus id with the
  FRAM chip is NOT supported by the twin's current single-device-per-bus-id wiring" — Twin fidelity gap
  for multi-device SPI. · tracked: digital_twin/README.md:846-847, SPECIFICATION.md:2329 | related:
  TWIN.T* · [H17]
- **TWIN.N360** LIMIT · `commit 4839c54` — "Left a few reported gaps alone deliberately: BMP3xx's
  Newton-solver divide-by-zero guards (unreachable ...), launch.py's run-forever branch" — Deliberately
  uncovered twin branches. · status: by design (low) | - · [H17]
- **TWIN.N361** LIMIT · `commit 00e8e46` — "the MicroPython Unix port's \"standard\" build rejects a
  plain (host, port) tuple in connect()/bind()/sendto() (micropython/micropython#6924) ... NTP/DNS
  simply cannot be verified end-to-end under the Unix port at all" — Twin/Unix-port fidelity gap for UDP
  call sites; later worked around by a test-only patch (patch_asy_udp_socket_for_unix_port). · tracked:
  CLAUDE.md (`patch_asy_udp_socket_for_unix_port()` mention) / digital_twin README; upstream-issue
  removal trigger none stated | related: TWIN.T* · [H17]
- **TWIN.N362** WORKAROUND · `commit 54d451a` — "it only prevents the underlying MicroPython Unix-port
  bug from recurring as long as real peak concurrent poll registrations never exceed the pre-warmed
  ceiling" — extmod/modselect.c Unix-port poll-growth segfault worked around by pre-warming to 512
  slots; residual risk is a numeric ceiling. Removal trigger: none stated (upstream fix). · tracked:
  digital_twin/unix_port_poll_prewarm.py:19,48-49 | covered-by: TWIN.T07 · [H17]
- **TWIN.N363** ASSUME · `commit b3495d8` — "The new 8192-byte tolerance (~3.1x the largest observed
  magnitude) is sized from this real data" — Soak memory-trend tolerance from five 100-cycle runs; later
  revised (SPECIFICATION.md:3403-3407 sqrt scaling). · tracked: SPECIFICATION.md:3403-3407 | related:
  TWIN.T*, MEM.T* · [H17]
- **TWIN.N364** WORKAROUND · `commit dfb8975` — "digital_twin/_unix_port_udp_addr_shim.py, which works
  around three confirmed MicroPython-Unix-port-only socket quirks" — Twin-only shim for Unix-port UDP
  sockaddr shapes; removal trigger none stated. · tracked: digital_twin/README.md | related: TWIN.T07 ·
  [H17]
- **TWIN.N365** OPENQ · `commit f7ceab8` — "the residual bug unix_port_poll_prewarm.py works around
  looks like a narrower, still-unfiled edge case rather than a duplicate" — Upstream MicroPython
  modselect edge case was never reported upstream; the workaround has no removal trigger. · status:
  UNTRACKED (no issue filed / no follow-up recorded) | related: TWIN.T07 · [H17]
- **TWIN.N366** LIMIT · `commit dcb007d` — "network.py's AP-mode ifconfig() fidelity gap (real address
  not simulated on hotspot activation)" — Twin fidelity gap. · tracked: digital_twin/README.md (per
  commit) | related: TWIN.T* · [H17]
- **TWIN.N367** NOTE(RULE) · `commit 7cf989d` — "never bisect a twin soak's runtime to a code change ...
  count the operation instead"; budget raised to 120s — Workaround: liveness-only budget. · tracked:
  SPEC Part E.7 | - · [H17]
- **TWIN.N368** WORKAROUND · `commit b275efb` — "Two gc.collect() calls in
  digital_twin/_http_client.py's fetch()" — gc.collect() as MemoryError fix. · status: done-in
  a5fca11/a3b1a6e/5c76c37 (right-sized reads, no gc.collect()) | related: MEM.T* · [H17]
