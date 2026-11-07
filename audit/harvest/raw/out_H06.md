# Harvest H06 — digital twin: `digital_twin/` + `tests/test_digital_twin_*.py` (snapshot 2a88cc8)

## digital_twin/README.md
- SETTLED | digital_twin/README.md:12-14 | "Not `tests/machine.py`, does not import it, and is never imported by anything in `tests/`." | Twin/mock separation is a stated design rule; auditor should check no `tests/` module imports twin code except via the documented per-file `sys.path.insert` | area: TWIN | related: TEST.T05
- DRIFT | digital_twin/README.md:14 vs :369-371 | ":14 `build/generated_src:src:tests:frozen_modules:.frozen`" vs ":370 currently `src:tests:frozen_modules:.frozen`" | The same doc states two different MICROPYPATH values for `scripts/test.sh`; one is stale (and README says it is "set internally per test file") | area: DOC | -
- SETTLED | digital_twin/README.md:18-22 | "`Timer` fires for real on a wall-clock schedule via an internal `asyncio` task, not `_thread`" | Deliberate choice; Timer callbacks never pre-empt running code, so soft-IRQ/soft-callback-drop and preemption semantics of the real rp2 Timer are unmodelled | area: TWIN | covered-by: TWIN.T02
- ASSUME | digital_twin/README.md:20-22 | "every real `Timer` callback in this codebase is already trivial enough that true preemption buys nothing" | Justification rests on all callbacks staying trivial; unverified going forward | area: TWIN | related: TWIN.T09
- INVAR | digital_twin/README.md:22-25 | "`configure_wiring(plan)`, called once before any bus is constructed" | Ordering contract upheld by caller discipline | area: TWIN | related: TWIN.T12
- LIMIT | digital_twin/README.md:26-30 | "default `\"wozi\"` if neither `configure_wiring()`/`configure_i2c_wiring()` is ever called" | A caller that forgets wiring silently gets wozi's bus layout, not an error | area: TWIN | related: TWIN.T12
- MIRROR | digital_twin/README.md:30-35 | "`\"wozi\"` mirrors `sensortask_wozi.build_system()`'s own construction ... `\"dev\"` mirrors ... reversed layout" | Twin wiring profiles mirror each generated device's bus/address/IRQ-pin layout (SCD30 IRQ pin 8 vs 11); now derived from wiring-plan JSON | area: TWIN | related: TWIN.T12
- LIMIT | digital_twin/README.md:35-36 | "Any other address NAKs — a real bus with a fixed, known set of devices on it" | Twin buses model only the wired devices; unexpected-address behaviour is a NAK, not real-bus electrical behaviour | area: TWIN | -
- INVAR | digital_twin/README.md:36-41 | "the chip fake's own `rdy_pin` must be constructed with the same id the real driver's own IRQ `Pin` uses, or a simulated edge never reaches its handler" | Pin-id agreement between chip fake and driver is a convention; a mismatch silently loses IRQ edges | area: TWIN | -
- LIMIT | digital_twin/README.md:41-45 | "`I2C.log`/`SPI.log` (an ad-hoc introspection aid nothing in `tests/`/`digital_twin/` reads today) is bounded to the most recent 200 entries" | Unread introspection log, bounded after a real MemoryError leak; history truncation to 200 entries | area: TWIN | -
- ASSUME | digital_twin/README.md:46-48 | "one chip fake per sensor, each verified against its own datasheet in `datasheets/`" | Fidelity claim for all four fakes; only ISL29125 has a conformance probe | area: TWIN | related: TWIN.T01, TEST.S20
- LIMIT | digital_twin/README.md:48-50 | "`_scd30_chip.py`'s RDY pin fires a real rising edge on its own internal measurement-interval cadence" | RDY timing is a twin-internal cadence, not the chip's real conversion timing | area: TWIN | related: TWIN.T01
- LIMIT | digital_twin/README.md:50-52 | "explicit `save_state()`/on-construction load JSON persistence for its five NVM-backed settings" | SCD30 fake persists only the five NVM scalars | area: TWIN | related: TWIN.T10
- PLATFORM | digital_twin/README.md:53-68 | "`BOUTF` being read-to-clear contradicts the datasheet and was measured on real silicon" | ISL29125 fake encodes silicon-measured behaviours (destructive 0x08 read, BOUTF after reset, address-pointer walk to 0x0E, persistence counter reset on RGBTHF clear, active-low INT) that diverge from the datasheet (M.1.2/M.1.4) | area: TWIN | related: TWIN.T11
- ASSUME | digital_twin/README.md:53-56 | "high range's full scale is a deliberately non-nominal multiple of its low range's" | Deliberate fake non-nominal ratio so calibration has something to converge on; tests depend on it | area: TWIN | -
- RISK | digital_twin/README.md:72-75 | "dev's own `AsyFramManager.setup()` silently failed its device-ID check every twin run, caught and swallowed by its own broad `except Exception`" | A broad except in the FRAM manager hid a wrong-chip wiring bug in every twin run; the swallow pattern still exists | area: STOR | -
- WORKAROUND | digital_twin/README.md:76-88 | "a workaround for a confirmed, real dangling-pointer bug in the pinned MicroPython Unix port's `extmod/modselect.c`" | Poll-prewarm workaround for an upstream Unix-port bug; removal trigger: none stated (only "file upstream", :918-919) | area: TWIN | covered-by: TWIN.T07
- INVAR | digital_twin/README.md:79-84 | "Called as the first statement ... and at import by every `tests/` entry point that boots a `sensortask_*` module with real sockets ... before anything else in the process registers a poll object" | Call-order contract enforced only by convention in each entry point | area: TWIN | related: TWIN.T07
- ASSUME | digital_twin/README.md:83-88 | "scans upward from port 17400 across a 64-port window ... (28 of 30 concurrent prewarms; 0 of 30 with the scan), and port 0 is no alternative since this port has no `getsockname()`" | Single dated measurement; the 64-port window bounds concurrency (TEST_PARALLELISM) | area: TWIN | related: TEST.S21
- WORKAROUND | digital_twin/README.md:89-101 | "the calls stay wired in as defense in depth, not because the race is still reachable" | gc-unwedge workaround for SIGINT-in-gc_collect heap lock; root cause closed by `unix_kbd_intr` override (B.14.1); removal trigger: none stated | area: TWIN | covered-by: TWIN.T07
- ASSUME | digital_twin/README.md:91-92 | "Measured at ~5% on both `v1.28.0` and `v1.29.0`" | Dated measurement on the Unix port | area: TWIN | -
- INVAR | digital_twin/README.md:92-98 | "calls `unwedge_heap_after_interrupt()` first at **two** sites" | Both the `finally:` and the outer `except KeyboardInterrupt:` must call it first; convention only | area: TWIN | related: TWIN.T07
- MIRROR | digital_twin/README.md:102-104 | "a generic op-keyed fault-injection queue, mirroring `tests/machine.py`'s own `inject_fault()`/`_maybe_raise()` convention" | Fault API mirror between twin and mock tier | area: TWIN | related: TEST.T05
- MIRROR | digital_twin/README.md:105-106 | "independent, deliberately duplicated (not reused) copies of `tests/network.py`/`tests/neopixel.py`'s own fakes" | Deliberate duplication; the two copies can drift | area: TWIN | related: TWIN.T12, TEST.T05
- DRIFT | digital_twin/README.md:107-109 | "`WLAN.connect()` transitions to a successful, connected state immediately" | Contradicted by `network.py`'s 0.7 s async connect phase | area: DOC | covered-by: TWIN.S06
- LIMIT | digital_twin/README.md:109-112 | "It only fakes *connection state* — actual traffic (NTP/DNS/HTTP) goes through the real `socket` module ... reaches the real network" | Network fidelity: host Linux stack and the real internet stand in for CYW43/lwIP; no lwIP limits modelled | area: TWIN | covered-by: TWIN.T08
- ASSUME | digital_twin/README.md:112-114 | "`ifconfig()` reports a plausible static address ... harmless, since nothing in `src/` constructs a socket from that value" | Unverified-going-forward assumption about `src/` usage of `ifconfig()` | area: TWIN | -
- LIMIT | digital_twin/README.md:114-116 | "**AP-mode fidelity gap**: ... `ifconfig()[0]` reads `\"0.0.0.0\"` in AP mode instead of a realistic address" | Documented AP-mode infidelity | area: TWIN | related: TWIN.T03, TWIN.S05
- ASSUME | digital_twin/README.md:119-120 | "Every response it sees is `Connection: close` ... so it never needs keep-alive support" | Twin HTTP client relies on the server hook always closing; keep-alive paths untested at twin tier | area: TWIN | related: TEST.T17
- RISK | digital_twin/README.md:120-124 | "`parse_status_line(b\"\")` therefore raises `CeilingRefusedError`, an `OSError` subclass" | Any empty response (not only a ceiling refusal) is classified as a refusal by every caller's `except OSError` | area: TWIN | related: TEST.T17
- INVAR | digital_twin/README.md:125-128 | "the import sits inside `.json()`, so `_http_client` itself imports without `tests/` on the path (as `segfault_stress_repro.py` needs)" | Lazy-import placement is load-bearing for a tests/-free path; `.json()` depends on `tests/_strict_json.py` | area: TWIN | related: TEST.T17
- PLATFORM | digital_twin/README.md:125-126 | "the interpreter's own `json.loads()` accepts a missing or stray comma the browser rejects" | MicroPython json lenience fact (F.1) the oracle compensates for | area: PLAT | -
- LIMIT | digital_twin/README.md:129-133 | "`launch.py` — standalone, `src/`-free CLI demo ... Lighter and narrower in scope" | launch.py exercises raw bus reads only, not the real object graph | area: TWIN | related: TWIN.T11
- LIMIT | digital_twin/README.md:144-147 | "Every chip fake exposes a `.fault` (`FaultInjector`) surface for provoking a bus NAK/CRC-corruption/timeout on demand" | Fault vocabulary is limited to these op-level classes plus a blocking hang | area: TWIN | related: TWIN.T05
- SETTLED | digital_twin/README.md:151-156 | "needs **zero twin-awareness** — no `if` branch anywhere distinguishing real hardware from simulated" | Stated invariant for generated/src code; the swap is pure MICROPYPATH ordering | area: TWIN | -
- INVAR | digital_twin/README.md:181-191 | "`digital_twin` ... never together with plain `tests` on the same `MICROPYPATH`" | Same-named `machine`/`network`/`neopixel` modules would shadow each other; path discipline only | area: TWIN | -
- INVAR | digital_twin/README.md:183-188 | "`frozen_modules` is required here too ... Omitting it fails the run at import time with `ImportError: no module named 'frozen_html'`" | MICROPYPATH must carry `frozen_modules` | area: TWIN | -
- DRIFT | digital_twin/README.md:265 vs :183-188 | "MICROPYPATH=\"/tmp/twin_boot:src:digital_twin:ext:.frozen\"" | The generated-device example omits `frozen_modules`, which :183-188 says is required for `import frozen_html` | area: DOC | -
- LIMIT | digital_twin/README.md:193-195 | "`scripts/run_unix_port_integration.sh` is not part of `scripts/test.sh`'s own default `tests/test_*.py` glob loop" | Manual entry point is untested by the default loop | area: SCR | related: SCR.T04
- LIMIT | digital_twin/README.md:197-204 | "it defaults every state-persistence path to `None` (in-memory only) ... a manual run through that script is in-memory-only" | Manual twin runs do not exercise persistence unless paths are passed | area: TWIN | related: TWIN.T10
- SETTLED | digital_twin/README.md:205-210 | "There is no `--soak`/`--soak-cycles` flag any more — the automated HTTP+memory-trend soak check moved host-side" | Driver/DUT separation decision; only `gc.mem_free()` exits via `MEM_SAMPLE` lines | area: TWIN | -
- LIMIT | digital_twin/README.md:217-224 | "only ever starts the specific tasks each test needs (never the full `start_and_check_tasks()` supervisor)" | The in-suite integration tier never exercises the supervisor graph | area: TWIN | -
- LIMIT | digital_twin/README.md:225-230 | "masked by `tests/test_asy_webserver_service.py`'s own uniform fakes, which happened to return an already-flat shape" | Documents a mock-fidelity blind spot class (fakes returning a simplified shape); also historic narrative in docs (low) | area: TEST | related: TEST.T05
- PLATFORM | digital_twin/README.md:238-239 | "`buildgen` needs `tomllib`, which the MicroPython Unix port doesn't have" | Wiring plan must be produced host-side in CPython | area: GEN | -
- DRIFT | digital_twin/README.md:234 | "consuming a Session-3 `buildgen.generate.generate_device()`-generated module" | Retired session-numbering term in current doc (low) | area: DOC | -
- DRIFT | digital_twin/README.md:270-271 | "the same pattern `scripts/_digital_twin_ci_suite.py` already uses for the hand-written wozi module" | No hand-written wozi module exists any more (:256-257, L.2) | area: DOC | -
- LIMIT | digital_twin/README.md:270-275 | "asserting a real `GET` against five real REST endpoints all return 200" | Generated-boot test checks only five GET status codes per device | area: GEN | related: TEST.T18
- LIMIT | digital_twin/README.md:288-297 | "`_wire_uart_crossover()` ... joins their own ... `machine.UART` fakes with ... `attach_crossover_jumper()`, and swaps in the returned bounded `LinkPoller`s" | Twin UART is a fake crossover jumper with substituted pollers; no real UART timing/baud | area: TWIN | related: TWIN.T12
- MIRROR | digital_twin/README.md:288-291 | "a fourth, optional `\"uart\"` key (`{\"initiator_var\", \"responder_var\"}`, the two generated Python variable names" | Twin reads generated variable names from the plan: a buildgen↔twin contract without schema version | area: GEN | related: TWIN.T12
- SETTLED | digital_twin/README.md:301-304 | "only ever writes to disk on an **explicit** call — never automatically, to avoid unnecessary write cycles on an SSD-hosted state file" | Host-SSD wear decision; state survives only if the flush runs (abrupt kill loses it) | area: TWIN | covered-by: TWIN.T10
- INVAR | digital_twin/README.md:310, :341 | "`configure_fram_state_path(...)  # before constructing spi0`" / "`configure_scd30_state_path(...)  # before constructing i2c0`" | Ordering contract for state-path configuration | area: TWIN | related: TWIN.T10
- LIMIT | digital_twin/README.md:317-319 | "`tests/test_digital_twin_fram.py` ... constructing `FramChip` directly (that file never goes through `machine.SPI` at all)" | FRAM fake unit tests bypass the `machine.SPI` wiring path | area: TWIN | related: TWIN.T04
- ASSUME | digital_twin/README.md:321-328 | "16385 bytes for a real 0x2000-byte FRAM ... even with ~1.5MB of *total* `gc.mem_free()` still available" | Dated measurement justifying chunked (512 B) save/load | area: MEM | -
- ASSUME | digital_twin/README.md:332-336 | "confirmed against `src/asy_scd30_driver.py`'s own setter docstrings" | SCD30 NVM-persisted set confirmed against driver docstrings, not stated against the datasheet | area: TWIN | related: TWIN.T01
- LIMIT | digital_twin/README.md:354-358 | "**Known limitation: single-chip globals.** ... only ever persists the *last-wired* instance's NVM settings" | Multi-SCD30/multi-FRAM devices (both synthetic fixtures) persist only one instance | area: TWIN | related: TWIN.T10
- TODO | digital_twin/README.md:357-358 | "A real multi-instance-persistence fix is unscoped; no real device needs it today." | Deferred work | area: TWIN | -
- DRIFT | digital_twin/README.md:374-376 | "All tests are deterministic — no wall-clock waiting, except one short-period/generous-timeout smoke test" | Stale: twin test files wait on real wall-clock time well beyond that one smoke test (e.g. 9 s runs and a 75 s hold in `tests/test_digital_twin_bus_hazard_concurrency.py:185-227, 392`; 9 s in `tests/test_digital_twin_sensortask_integration.py:461`) | area: DOC | related: TEST.T04
- DRIFT | digital_twin/README.md:390, :408-412 | "same 14-run suite" / "17 for `wozi`, 18 for `dev`" | Hard-coded run/process counts that drift as the suite grows (low) | area: DOC | related: SCR.T04
- LIMIT | digital_twin/README.md:408-411 | "on a fixed port (`18080`, distinct from the manual entry point's `8080` default" | Fixed ports; concurrent suites collide | area: SCR | covered-by: SCR.T04
- SETTLED | digital_twin/README.md:412-420 | "The whole 14-run sequence itself runs twice ... at `--gc-threshold -1` ... and once at `32768`" | Zero-MemoryError at both GC stages, enforced by `_close_log_and_check_memory_safety()` | area: TWIN | related: TEST.T18
- LIMIT | digital_twin/README.md:420-422 | "a device without `bmp3xx` (4 of the 6 real devices) simply never faults/checks it" | Per-device fault matrix; coverage per driver depends on which devices wire it | area: TWIN | related: TWIN.T05
- INVAR | digital_twin/README.md:428-430 | "a plain `SIGTERM`/`terminate()` would skip `run_generic_integration.py`'s own FRAM/SCD30 flush" | Shutdown must be SIGINT for state to persist | area: TWIN | related: TWIN.T10
- ASSUME | digital_twin/README.md:443-446 | "`--fault` only ever produces bounded, immediately-raised `OSError`s, never an indefinite hang, so nothing here can actually block the event loop" | Run 3's watchdog-never-starves claim rests on the fault model, not on real bus behaviour | area: TWIN | related: TWIN.T05
- LIMIT | digital_twin/README.md:453-456 | "That makes this a much weaker claim than \"these never persist\", and one nothing re-checks against a *healthy* chip (BACKLOG.md)" | Run 4's SCD30/BMP3XX-read-0 claim is situational; the BACKLOG.md pointer names no item and none is found by grep | area: TWIN | -
- DRIFT | digital_twin/README.md:449-453 | "this line claiming otherwise — citing a Part A.7 that never said it — was the same stale assumption" | Historic correction narrative left in the doc (low) | area: DOC | -
- RISK | digital_twin/README.md:462-465 | "waiting on that warning is a host-speed race (it lands before the sample on an x86 runner, after it on the project's bench Pi4)" | Documents a removed host-speed-dependent check; pattern to watch in other runs | area: TWIN | -
- ASSUME | digital_twin/README.md:468-471 | "this suite counts `\"E\"`-typed history entries specifically, not the raw combined counter" | Run 5 depends on recovery notices being logged as `W`, never `E` | area: TWIN | -
- RISK | digital_twin/README.md:474-482 | "Measured here at roughly **1 abrupt restart in 8**. That loss is **accepted behavior** (project owner's call, 2026-09-11" | Accepted loss of FRAM log history on abrupt restart; run asserts all-or-nothing only | area: STOR | -
- ASSUME | digital_twin/README.md:487-489 | "measured **20/20** against the ~1-in-8 loss of run 5b's unpaused shutdown" | Single dated measurement for the mempause guarantee | area: STOR | -
- LIMIT | digital_twin/README.md:491-497 | "One fault per process rather than all at once is forced by the task-restart budget ... three drivers faulted together exhaust it" | Combined multi-driver faults are not tested in 5c | area: TWIN | related: TWIN.T05
- INVAR | digital_twin/README.md:497-502 | "`FRAM` is the one exemption ... `tests/_sensortask_scenarios.py` pins it as the only one" | The FRAM-log-in-memory exemption is test-pinned | area: STOR | -
- INVAR | digital_twin/README.md:503-507 | "a reset arriving before the loggers finish `setup()` is dropped by design and the restore then puts the old history straight back" | ResetErrors before setup completes is silently dropped (by design); test must poll first | area: CORE | -
- MIRROR | digital_twin/README.md:507-509 | "mirrored at the mock tier (`tests/test_fram_integration.py`) and on real silicon (`tests_hardware/flash/test_fram_storage.py`'s reset-race test)" | All-or-nothing restore claim held at three tiers | area: STOR | -
- WORKAROUND | digital_twin/README.md:519-527 | "`scripts/run_digital_twin_ci.sh` grants the built interpreter binary `CAP_NET_BIND_SERVICE` (via `setcap`, fresh on every invocation" | Privileged port 53 on a non-root host; removal trigger: none stated | area: SCR | covered-by: SCR.T07
- RISK | digital_twin/README.md:523-527 | "`asy_udp_socket.py`'s own `bind()` retry loop swallows the resulting `PermissionError` and gives up silently" | DNS server can silently never listen; no crash, no log-gate signal | area: NET | related: SCR.S06
- ASSUME | digital_twin/README.md:532-533 | "stays fully healthy past NTP's own 5s fetch timeout" | Copied timing constant from src/ | area: NET | -
- PLATFORM | digital_twin/README.md:534-540 | "real rp2040 `machine.I2C` calls have no `await` point (SPECIFICATION.md Part F.2), so a genuinely wedged real peripheral blocks the whole single-threaded interpreter" | Hang simulation relies on this platform fact; twin WDT window stated as 8000 ms | area: PLAT | related: TWIN.T02
- ASSUME | digital_twin/README.md:548-555 | "100, not wozi's original 40 ... confirmed directly, 2026-09-14 ... roughly 2.5x" | Dated calibration of soak warmup cycles | area: TWIN | -
- ASSUME | digital_twin/README.md:564-567 | "A CI `MemoryError` here (`allocating ~6100 bytes` on `GET /status`) ... fixed by `_http_client.py`'s `_read_exact()`/`_read_until_close()`" | Past MemoryError attributed to the test client's reads; fixed in the oracle | area: MEM | related: TEST.T17
- LIMIT | digital_twin/README.md:569-580 | "fires exactly that many simultaneous GETs ... A 1 s settle precedes **every** round" | Ceiling test runs over the host loopback stack (not lwIP) and depends on a fixed 1 s settle | area: TWIN | related: TWIN.T08
- SUPPRESS | digital_twin/README.md:592-602 | "Its `gc.collect()` is measurement instrumentation under Part I.4(e)'s narrow exception" | A `gc.collect()` in twin code justified as instrumentation; min=99808/max=1347104 measured 2026-09-14 without it | area: MEM | related: TEST.T03
- LIMIT | digital_twin/README.md:603-609 | "`UARTLink.wire_log` is unbounded by design, so a unit test ... every such test clears it itself" | Unbounded twin log; each test must clear it; runner clears it periodically | area: TWIN | -
- ASSUME | digital_twin/README.md:613-620 | "Confirmed 2026-09-14 ... reproduced with the UART tasks fully disabled — so it is settling proportional to module count" | Dated inference on warmup cause | area: TWIN | -
- ASSUME | digital_twin/README.md:622-640 | "sets the tolerance as a generous multiple of that ... it covers the observed worst case (5889 bytes) with room left" | Self-calibrating trend tolerance; numbers from dated measurements (1496-1964 B spread, 25 ms samples autocorrelated) | area: TWIN | -
- SETTLED | digital_twin/README.md:644-656 | "`_NO_PERSIST_WHEN_FRAM_FAULTED` is not \"these logs are in-memory\"" | Suite-table semantics; README names SCD30/BMP3XX but the suite's set also holds `isl29125` (`scripts/_digital_twin_ci_suite.py:79`) (low) | area: TWIN | -
- DRIFT | digital_twin/README.md:667-669 | "What is still missing is an elapsed-time budget well below the cap ... the suite is blind to the whole 5-15s band" | Contradicted by `scripts/_digital_twin_ci_suite.py:116, 273-281` (`_RESET_ERRORS_BUDGET_S = cap*0.8`, asserted) and BACKLOG.md:371 | area: DOC | -
- ASSUME | digital_twin/README.md:663-666 | "The value sits just **above** the server's own `outer_cap_s`, deliberately" | Timeout derived from a src/ constant; must move with it | area: TWIN | -
- LIMIT | digital_twin/README.md:673-680 | "`sgp40`/`scd30` (`writeto`/`readfrom_into`), `bmp3xx` (`readfrom_mem`/`writeto_mem`), `fram` (`write`/`readinto`) ... `wlan` has no `--hang` vocabulary" | Hang coverage is limited to these ops; no WLAN hang, no `writeto` hang for BMP3xx/ISL29125 | area: TWIN | related: TWIN.T05
- DRIFT | digital_twin/README.md:675-676 vs digital_twin/launch.py:71-80 | "`sgp40`/`scd30` (`writeto`/`readfrom_into`), `bmp3xx` (`readfrom_mem`/`writeto_mem`), `fram` (`write`/`readinto`)" | README's `--hang` op list omits `isl29125` (`readfrom_mem`/`writeto_mem`), which `_HANG_DEVICE_OPS` accepts (low) | area: DOC | -
- LIMIT | digital_twin/README.md:684-690 | "`configure_fault(\"isl29125:int_stuck_high\")` ... Reached from a test holding the chip object" | Stuck-INT fault is not reachable via `--fault`/`--hang` CLI; dev-only | area: TWIN | related: TWIN.T05
- WORKAROUND | digital_twin/README.md:692-708 | "`_arm()` now checks, before cancelling the previous `_countdown()` task, whether its own deadline had already elapsed" | Twin-internal compensation because the fake WDT is an asyncio task that cannot run during a real freeze | area: TWIN | related: TWIN.T02
- ASSUME | digital_twin/README.md:705-708 | "Run 10 giving the twin enough `--duration` (15s, not 0) for SGP40's own bus access — now queued behind BMP3xx's and SCD30's own FRAM-backed startup I/O" | Run 10 depends on boot ordering and a fixed duration | area: TWIN | -
- PLATFORM | digital_twin/README.md:712-717 | "`Stream.readexactly()` and `Stream.read(-1)` both accumulate with `r += r2` ... Confirmed by reading the pinned interpreter's own source" | asyncio stream allocation behaviour tied to the pinned version | area: PLAT | -
- PLATFORM | digital_twin/README.md:721-725 | "**`readinto()` can return `None`** ... must be retried; only a real `0` means the peer closed" | Stream API fact the client depends on | area: PLAT | -
- PLATFORM | digital_twin/README.md:726-730 | "`ext/microdot.py`'s `send_file()` hands the response a raw file stream, so `Response.complete()`'s automatic `Content-Length` never applies" | `GET /` has no Content-Length on Microdot v2.6.2 | area: REST | -
- ASSUME | digital_twin/README.md:732-739 | "(~7.5KB for the largest device's frozen website) ... **no real device ever holds one**" | Twin-client allocation vs device behaviour; `py/gc.c`'s collect-and-retry cited as platform fact | area: MEM | -
- ASSUME | digital_twin/README.md:741-745 | "`dev`'s own frozen website (7579 bytes, 168-483 bytes larger than the other five devices')" | Dated sizes that drift with the website | area: MEM | -
- INVAR | digital_twin/README.md:749-759 | "called once, early, ... before anything constructs a socket" | UDP shim call order; `scripts/test.sh` grants setcap unconditionally so the DNS test works | area: TWIN | related: TWIN.T07
- RISK | digital_twin/README.md:761-767 | "**Two different faults produce the identical message** ... Neither is a bug in the code under test." | An ambiguous failure message (missing setcap vs CPU starvation) | area: TEST | related: TEST.T04
- WORKAROUND | digital_twin/README.md:769-795 | "Works around three confirmed MicroPython-Unix-port-only `socket` quirks" | Tuple sockaddr rejection, `sendto()` (upstream #6924), raw `recvfrom()` struct; removal trigger: none stated | area: TWIN | covered-by: TWIN.T07
- PLATFORM | digital_twin/README.md:775-780 | "The real rp2/lwIP module (`extmod/modlwip.c`) accepts the plain tuple directly" | rp2 socket API fact that `src/` relies on | area: PLAT | -
- DRIFT | digital_twin/README.md:776-778 | "see `BACKLOG.md`'s \"Real-hardware verification gap\" entry for the full account" | BACKLOG.md:197 is now a closed stub pointing to `tests_hardware/README.md` (low) | area: DOC | -
- ASSUME | digital_twin/README.md:792-795 | "Every real call site ... already hands over an already-numeric address, so the `getaddrinfo()` calls here are always fast and local" | Shim assumes numeric addresses; a hostname would do a real DNS lookup | area: TWIN | -
- INVAR | digital_twin/README.md:799-801 | "**Required whenever a new sensor driver lands in `src/`** ... do it the same session the driver is promoted" | Review-only obligation (C.11 point 9) | area: TWIN | -
- INVAR | digital_twin/README.md:813-817 | "the step bound itself is a **not**-datasheet-derived physical-plausibility judgment call, document it as such" | Convention for chip-fake docstrings | area: TWIN | -
- INVAR | digital_twin/README.md:818-821 | "answering the *exact* raw transaction shape the real `*_I2C` driver class sends — confirmed directly against that file's own source, never assumed" | Chip fakes mirror driver transaction shapes, not datasheet only | area: TWIN | related: TWIN.T01
- MIRROR | digital_twin/README.md:824-827 | "add it to `buildgen/twin_wiring.py`'s own `FIXED_ADDRESSES` table too, matching the real driver's own hardcoded default address" | Copied address constant (driver ↔ buildgen table) | area: GEN | related: GEN (plan:1294)
- MIRROR | digital_twin/README.md:838-842 | "**Update `html/definitions/<device>.json`** ... skipping this step leaves the driver ... permanently invisible on the website" | New-driver obligation to the website definitions (review-only) | area: WEB | -
- LIMIT | digital_twin/README.md:844-850 | "`_wire_spi_device()`/`machine.SPI` currently wire **one fixed device per bus id** ... Not built now because no such driver exists yet" | No CS routing in the twin SPI; a second SPI device is unsupported | area: TWIN | related: DOC.S22
- DRIFT | digital_twin/README.md:854-856 | "same as `src/`/`tests/` - all three are expected to stay fully clean" / "`ruff check src tests digital_twin`" | CLAUDE.md now describes eight scopes; the command/count may be stale (low) | area: DOC | -
- DRIFT | digital_twin/README.md:861-863 | "`digital_twin/launch.py`/every `tests/test_digital_twin_*.py` are excluded from the main pass" | CLAUDE.md's list also names `run_generic_integration.py`/`segfault_stress_repro.py`; README's list is shorter (low) | area: DOC | -
- PLATFORM | digital_twin/README.md:869-872 | "no `socket.getsockname()`; `getaddrinfo()` returns a packed `sockaddr`; `asyncio` offers `Lock` and `Event` but no `Semaphore`; `os.environ` is missing" | Unix-port facts tied to the pinned build; `mem_info()` with any argument prints the full block map | area: PLAT | -
- LIMIT | digital_twin/README.md:876-881 | "**BMP3xx's fixed calibration block is not sourced from a real chip.**" | Hand-picked coefficients; real factory trim never exercised in the twin | area: TWIN | related: TWIN.S03
- LIMIT | digital_twin/README.md:882-885 | "`tests/_fram_chip_fake.py`'s own WEL-corruption-specific knobs (`drop_wren`, `disturb_write_autoclear`, ...) ... weren't reproduced here" | Twin FRAM fake lacks WEL fault knobs | area: TWIN | related: TWIN.T05, STOR.T03
- SETTLED | digital_twin/README.md:886-894 | "Deliberately kept hardcoded to `sensortask_wozi` ... never invoked by `scripts/run_digital_twin_ci.sh` or any `tests/test_*.py` file" | Manual-only stress tool, outside CI | area: TWIN | related: TWIN.T11
- PLATFORM | digital_twin/README.md:894-906 | "a dangling-pointer dereference at `extmod/modselect.c:132` ... `MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` ... defaults to 0 and is only turned on by the Unix port's own config" | Root cause and "rp2 unaffected" claim, re-verify on version bump | area: PLAT | related: TWIN.T07
- TODO | digital_twin/README.md:917-919 | "No separate upstream issue for this narrower residual case was found as of this check — worth filing one upstream ... as a future follow-up" | Unfiled upstream bug report | area: TWIN | -

## digital_twin/machine.py
- PLATFORM | digital_twin/machine.py:12 | "`_SPI_DMA_MIN_SIZE = 32  # ports/rp2/machine_spi.c's own dma_min_size_threshold`" | Copied rp2 port constant; must track the pinned source | area: PLAT | related: TWIN.T02
- MIRROR | digital_twin/machine.py:13-14 | "same \"keep last N\" convention print_log.py's own PrintLogHistory uses" | `_LOG_MAXLEN = 200` bounds I2C/SPI logs and the WDT log; older entries silently dropped | area: TWIN | -
- PLATFORM | digital_twin/machine.py:48-50 | "Real rp2 values (ports/rp2/machine_pin.c at v1.29.0: GPIO_PULL_UP 1, GPIO_PULL_DOWN 2)" | Version-pinned constants (also IRQ_FALLING 0x04/IRQ_RISING 0x08, uncommented) | area: PLAT | -
- LIMIT | digital_twin/machine.py:62-67 | "`if not isinstance(id, int): raise TypeError(...)` / `if not (0 <= id <= 28)`" | Twin Pin accepts only int ids 0-28; named/CYW43 pins (e.g. "LED") and any other real-port id rules are not modelled (low) | area: TWIN | -
- INVAR | digital_twin/machine.py:59-60 | "Test-only: real GPIO pins never \"reset\" between test functions the way this registry needs to for isolation" | Class-level Pin registry shared across tests in one process; isolation depends on each test calling `reset_registry()` | area: TEST | related: TEST.T07
- LIMIT | digital_twin/machine.py:84-89, 111-120 | "`self.pull = pull` ... `self._irq_hard = hard`" | Pull resistors never affect `value()`, and the `hard` flag is stored only: hard-IRQ context (no heap allocation, pre-emption) is unmodelled (low) | area: TWIN | related: TWIN.T02
- LIMIT | digital_twin/machine.py:126-137 | "drives a real electrical transition, firing the handler only when the direction matches" | Edge IRQs run the handler synchronously in the caller's context; no IRQ latency, bounce, floating/stuck line modelling | area: TWIN | related: TEST.T05
- MIRROR | digital_twin/machine.py:127-129 | "`tests/machine.py`'s trigger_irq() fires unconditionally - a deterministic unit test needs no edge fidelity; a twin does" | Deliberate mock↔twin divergence in edge semantics | area: TEST | covered-by: TEST.S15
- INVAR | digital_twin/machine.py:144-146 | "called once before i2c0/i2c1 are constructed" | `configure_random_source()` ordering; later calls do not reach already-built chips | area: TWIN | -
- LIMIT | digital_twin/machine.py:151-152, 163-167 | "`_current_scd30_chip`" / "`flush_scd30()`" | Single module-global chip: only the last-constructed SCD30 is ever flushed (README "single-chip globals") | area: TWIN | related: TWIN.T10
- INVAR | digital_twin/machine.py:164-165, 310-312 | "Called once, in a try/finally around asyncio.run(main())" / "why this must be explicit rather than a self-registered signal/atexit handler" | Persistence depends on every entry point wrapping `asyncio.run()` with both flushes | area: TWIN | covered-by: TWIN.T10
- SETTLED | digital_twin/machine.py:176-177 | "Replaces the whole plan outright, the same \"last configure_*() call before construction wins\" convention every hook here already uses" | Last-call-wins module-global configuration; calls after construction have no effect | area: TWIN | -
- INVAR | digital_twin/machine.py:185-194 | "Legacy sugar over configure_wiring(), kept for tests: no real entry point calls it" / "`open(f\"build/generated_src/sensortask_{profile}_wiring_plan.json\")`" | Relative path: works only when CWD is the repo root and generation already ran | area: TWIN | related: SCR.S07
- LIMIT | digital_twin/machine.py:199-204 | "Lazily defaults to wozi's generated plan the first time a caller constructs a bus without configuring wiring" | Silent wozi default for any unconfigured caller | area: TWIN | related: TWIN.T12
- SUPPRESS | digital_twin/machine.py:204 | "`# type: ignore[return-value]  # configure_i2c_wiring() above always sets it`" | mypy suppression resting on a control-flow claim | area: TWIN | -
- INVAR | digital_twin/machine.py:208-210, 231 | "the twin's hand-maintained chip-fake catalog, a new chip type still needing one written" | A driver without a fake raises `ValueError` at bus construction; catalog is hand-kept | area: TWIN | related: TWIN.T12
- PLATFORM | digital_twin/machine.py:250-252 | "Real rp2 I2C.deinit() exists only from 1.29, and even there the port's protocol slot is NULL - a silent no-op" | Version-specific platform fact (Part F.5.1) | area: PLAT | -
- LIMIT | digital_twin/machine.py:239-247 | "`self.freq = freq` / `self.timeout = timeout`" | I2C `freq`/`timeout` are stored and never honoured: zero transaction time, no clock stretching, no bus timeout, no SDA-stuck/arbitration faults (low) | area: TWIN | covered-by: TWIN.T02
- LIMIT | digital_twin/machine.py:253-254 | "`return sorted(self.devices.keys())`" | `scan()` lists exactly the wired fakes; real-bus ghost/missing addresses unmodelled | area: TWIN | related: TEST.S15
- LIMIT | digital_twin/machine.py:264-267 | "general call - every device may listen, tolerate silently" | General call reaches no chip fake, so chip reactions to it (e.g. SGP40/SCD30 soft reset) are unmodelled | area: TWIN | covered-by: TWIN.S02
- LIMIT | digital_twin/machine.py:259-283 | "`def writeto(self, address, buf, stop=True)`" | The `stop` flag (repeated-start) is logged but never changes chip behaviour (low) | area: TWIN | -
- LIMIT | digital_twin/machine.py:275-278 | "`buf[:] = data`" | Slice-assigning a fake's reply into a bytearray changes its length if the fake returns a different count; real hardware always fills `len(buf)` (low) | area: TWIN | -
- SUPPRESS | digital_twin/machine.py:265, 276, 277, 289, 293, 294, 403, 428, 745 | "`# type: ignore[call-overload]` / `[arg-type]` / `[index]` / `[index,arg-type]`" | Nine mypy suppressions on buffer-typed `object` parameters | area: TWIN | -
- INVAR | digital_twin/machine.py:302-304 | "src/ itself never calls this (zero twin-awareness anywhere in src/, per this step's own finish criteria)" | src/ must never reference twin hooks; convention | area: TWIN | -
- DRIFT | digital_twin/machine.py:302, 310, 917 | "by whatever entry point Step 5 writes" / "lets a Step 5 harness" | Retired step-session references; the entry point is `run_generic_integration.py` (low) | area: DOC | related: TEST.S24
- MIRROR | digital_twin/machine.py:317-318 | "`_DEV_FRAM_RDID = bytes([0x04, 0x7F, 0x48, 0x03])` ... `asy_fram_driver.py`'s own `_KNOWN_PRODUCT_IDS[0x40000]`, datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf p.10" | RDID constant copied from the driver table and datasheet | area: STOR | -
- ASSUME | digital_twin/machine.py:320-322 | "it's keyed by size as the best available proxy (unique today ...). Any size not listed falls back to FramChip's own default RDID" | A new FRAM size silently gets MB85RS64V's RDID (the same failure shape as the 2026-09-04 dev bug) | area: TWIN | -
- LIMIT | digital_twin/machine.py:326-336 | "`attachment = _current_wiring_plan()[\"spi\"].get(f\"spi{bus_id}\")`" | One SPI device per bus id, no chip-select routing; framing inferred from `write()` pairing | area: TWIN | covered-by: TWIN.S04
- PLATFORM | digital_twin/machine.py:368-371 | "1.29 added an RX-overrun check to rp2's SPI transfer path, reached only by READING 32+ bytes (Part F.5.2)" | Models a version-specific port behaviour; sticky and counted forms are twin knobs | area: PLAT | -
- PLATFORM | digital_twin/machine.py:384 | "real rp2 hardware SPI is MSB-first only" | Enforced in `init()` only; the constructor accepts `firstbit=LSB` unchecked (low) | area: PLAT | -
- PLATFORM | digital_twin/machine.py:398-399 | "Same NULL-slot no-op as I2C.deinit() above, and on rp2 SPI it has always been one" | Version-specific fact | area: PLAT | -
- LIMIT | digital_twin/machine.py:410-415, 427-431 | "`buf[:] = bytes(len(buf))`" / "`self.write(buffer_out); self.readinto(buffer_in)`" | SPI baud/mode never validated; `write_readinto` is two sequential half-duplex calls; an absent device reads zeros, not a floating-bus value (low) | area: TWIN | -
- PLATFORM | digital_twin/machine.py:417-418 | "Below DMA_MIN_SIZE_THRESHOLD (32 in ports/rp2/machine_spi.c) a transfer takes the blocking software path, which has no overrun check" | Port-internal behaviour, re-check on version bump | area: PLAT | -
- LIMIT | digital_twin/machine.py:435 | "`_UART_BITS_PER_BYTE = 10  # 8N1 on the wire`" | Wire time assumes 8N1 whatever `bits`/`parity`/`stop` are configured | area: TWIN | -
- INVAR | digital_twin/machine.py:436-439 | "Must comfortably exceed a whole stop-and-wait exchange's worth of frames" | `_UART_INFLIGHT_MAX = 4096` sized by convention to protocol frame sizes | area: UART | -
- MIRROR | digital_twin/machine.py:443-445 | "Same knobs and same semantics as tests/machine.py's own _LinkDirection (both are held to tests/_uart_link_contract.py)" | Mock/twin UART link contract; enforced by the shared contract tests | area: TEST | related: TEST.T05
- MIRROR | digital_twin/machine.py:482-484 | "Models the dev bench's permanent GP0<->GP9 / GP1<->GP8 jumper (dev_legacy/README.md)" | Twin topology mirrors a physical bench jumper (dev_legacy/README.md:54-60) | area: UART | -
- LIMIT | digital_twin/machine.py:497-499 | "`_LinkDirection(..., uart_a.baudrate)`" | Each direction is timed at the sender's baud; a baud mismatch between the ends (CLAUDE.md's "dead link that carries bytes") is unmodelled (low) | area: UART | -
- ASSUME | digital_twin/machine.py:500-502 | "A run longer than ticks_us()' period would need re-anchoring; no test comes close." | Unverified bound; `ticks_diff` is signed over half the ticks period, and manual/CI dev twin runs with a live link can run long | area: TWIN | covered-by: TWIN.T09
- ASSUME | digital_twin/machine.py:533-534 | "counted and dropped, never raised into the driver, which real hardware never does either" | Claim about rp2 UART overrun behaviour | area: UART | -
- LIMIT | digital_twin/machine.py:539-540 | "Called from each endpoint's own read path, so time only ever advances as the consumer actually runs" | Delivery is lazy (pumped by reads/ioctl), not interrupt-driven | area: TWIN | -
- LIMIT | digital_twin/machine.py:553-559 | "Blocks until every in-flight byte has landed" | `settle()` busy-waits with `time.sleep_us()`; a test-only seam that blocks the loop | area: TEST | -
- PLATFORM | digital_twin/machine.py:584 | "MicroPython's deque has no clear()" | Runtime fact | area: PLAT | -
- INVAR | digital_twin/machine.py:601-603 | "tests still swap .poller for a bounded stand-in (CLAUDE.md's known hang cause)" | CLAUDE.md rule that a UART poller double must be bounded, not `select.poll()` | area: TEST | -
- PLATFORM | digital_twin/machine.py:604-606 | "`_MP_STREAM_POLL = 3  # py/stream.h`" / "`_MAX_BUFFER_SIZE = 32766`" / "`_UART_INVERT_MASK = 3`" | Copied interpreter/port constants; the last two cite no source | area: PLAT | -
- ASSUME | digital_twin/machine.py:608-610 | "Real machine.UART() re-inits the peripheral rather than refusing, so a second instance on one id supersedes the first" | Port behaviour claim behind the supersede model; class-level `_live`/`superseded` shared across tests | area: UART | related: TEST.T07
- PLATFORM | digital_twin/machine.py:695-697 | "Real machine.UART.any() drains the RX FIFO before counting, so it never under-reports what a preceding POLLIN saw" | Port behaviour the driver's read clamp depends on | area: UART | -
- LIMIT | digital_twin/machine.py:701-703 | "these fakes serve what they hold and return, so the stall is counted here instead of taken" | Twin UART reads never block on `timeout_char` (F.5.8); a loop-blocking regression shows only via `would_have_blocked_bytes` (class-level) | area: UART | -
- LIMIT | digital_twin/machine.py:741-750 | "`if self.write_limit is not None: data = data[: self.write_limit]`" | TX side has no FIFO/`txbuf`/wire-time backpressure; `write()` returns immediately (low) | area: UART | -
- MIRROR | digital_twin/machine.py:756-758 | "Bounded select.poll() stand-in, identical in behaviour to tests/machine.py's own" | Duplicate poller in mock and twin; `ipoll()` ignores its timeout, `register()`/`unregister()` are no-ops | area: TEST | related: TEST.T05
- PLATFORM | digital_twin/machine.py:792-794 | "keeps real machine_timer_make_new()'s \"init helper only runs when the constructor was actually given settings\" behavior for a bare Timer()" | Port behaviour mirrored; `freq=` and other real Timer kwargs are not accepted (low) | area: PLAT | -
- LIMIT | digital_twin/machine.py:808-816 | "`await asyncio.sleep_ms(self.period)` / `self.callback(self)`" | Timer period drifts by callback+scheduling time each cycle; callbacks never run while the loop is blocked, unlike rp2 soft callbacks run by the scheduler; a callback exception ends the task (low) | area: TWIN | covered-by: TWIN.T09
- DRIFT | digital_twin/machine.py:828-830 vs :811-815 | "Skip the self-cancel: the old task returns on its own right after this callback does." | Old task returns only if the new `mode` is ONE_SHOT; a PERIODIC self-rearm keeps the old loop running alongside the new task (low) | area: TWIN | related: TWIN.T02
- PLATFORM | digital_twin/machine.py:828-829 | "a Task cannot cancel itself in MicroPython" | Runtime fact | area: PLAT | -
- PLATFORM | digital_twin/machine.py:835-838 | "RP2040 hard cap: 0xffffff / 2 / 1000 (ports/rp2/machine_wdt.c) ... 1.29 added a separate RP2350 branch" | WDT 8388 ms cap and id-0-only mirrored from v1.29.0 | area: PLAT | related: TWIN.T02
- LIMIT | digital_twin/machine.py:852-854 | "An asyncio countdown since the last feed() that records rather than acts" | Twin WDT never resets the process: post-watchdog-reset behaviour (reboot, reset cause) is not exercised; countdown cannot run during a real freeze | area: TWIN | covered-by: TWIN.T02
- WORKAROUND | digital_twin/machine.py:866-868 | "credit that already-elapsed window before cancelling it away, since real hardware can't un-reset itself retroactively" | Twin-internal compensation for the asyncio-based WDT; removal trigger: none stated | area: TWIN | -
- LIMIT | digital_twin/machine.py:899-913 | "`_shared_datetime: \"tuple[int, ...]\" = (2000, 1, 1, 0, 0, 0, 0, 0)`" | Twin RTC never advances and is not coupled to `time.time()`/`gmtime()` (host clock on the Unix port); on rp2 an RTC set moves `time`, so NTP-set clock jumps are unmodelled (inferred from code) | area: TWIN | covered-by: TWIN.T09
- ASSUME | digital_twin/machine.py:899-900 | "One physical peripheral - class-level shared state, matches real singleton hardware" | Class-level RTC state persists across tests in one process | area: TEST | related: TEST.T07
- LIMIT | digital_twin/machine.py:907-913 | "even on the set path, where real hardware returns nothing meaningful" | Set path returns the tuple; real call returns None | area: TWIN | covered-by: TWIN.S05
- LIMIT | digital_twin/machine.py:916-940 | "`class SimulatedRebootError(Exception)`" / "Real machine.reset() never returns; this twin cannot restart anything, so it raises instead." | Reset/bootloader raise an `Exception` subclass, so any broad `except Exception` in src/ swallows a simulated reset and keeps running code that never runs on hardware (low) | area: TWIN | related: TEST.S15

## digital_twin/_fault_injection.py
- MIRROR | digital_twin/_fault_injection.py:1 | "mirroring (independently of) `tests/machine.py`'s own `inject_fault()`/`_maybe_raise()` convention" | Two independent fault APIs held equal by convention only | area: TEST | related: TEST.T05
- LIMIT | digital_twin/_fault_injection.py:2 | "For chip-protocol-level faults (corrupted CRC, mid-transaction timeout) a bus fake can't express on its own; address-level NAK is handled generically by `machine.py`'s own `I2C` class" | Fault vocabulary: queued exceptions per op name plus hangs; no partial-transfer, clock-stretch, or electrical faults | area: TWIN | related: TWIN.T05
- PLATFORM | digital_twin/_fault_injection.py:3 | "real rp2040 `machine.I2C` calls are synchronous C-level HAL calls with no `await` point (SPECIFICATION.md Part F.2)" | Hang model relies on this; `time.sleep()` freezes every twin task incl. Timers and WDT countdown | area: PLAT | related: TWIN.T05
- DRIFT | digital_twin/_fault_injection.py:3 | "See `machine.WDT`'s own `_countdown()` for why this - not a bounded raise - is what actually risks starving" | 3-line docstring holds a ~700-char line (comment-cap evasion) | area: DOC | covered-by: TEST.S22
- LIMIT | digital_twin/_fault_injection.py:13-21 | "`self._queues.setdefault(op, []).extend([exc] * times)`" | One exception instance is re-raised for all `times` calls; faults are keyed by op name only, not by address/command, so a multi-command op cannot target one command (low) | area: TWIN | related: TWIN.T05
- INVAR | digital_twin/_fault_injection.py:18-32 | "`def maybe_raise(self, op)` / `def maybe_hang(self, op)`" | A fault fires only if each chip handler calls these hooks for that op; coverage per op is per-fake discipline (e.g. BMP3xx `handle_writeto` has no `maybe_hang`) | area: TWIN | covered-by: TWIN.T05

## digital_twin/_crc8.py
- SETTLED | digital_twin/_crc8.py:1 | "deliberately not importing `src/crc_checks.py`'s own CRC8, so a bug shared between the twin's response-building and the driver's validation can't hide" | Deliberate independent reimplementation | area: TWIN | -
- MIRROR | digital_twin/_crc8.py:1-3 | "Sensirion polynomial 0x31, init 0xFF" | Must equal the datasheet CRC and `src/crc_checks.py`; no golden vector cited here | area: TWIN | related: TEST.S20

## digital_twin/_sgp40_chip.py
- DRIFT | digital_twin/_sgp40_chip.py:1 | "answers `asy_sgp40_driver.py`'s exact word-oriented protocol (serial-number/self-test/general-call-reset/measure-raw)" | General call never reaches the fake (`machine.py:266`) and the fake has no reset handling | area: TWIN | covered-by: TWIN.S02
- ASSUME | digital_twin/_sgp40_chip.py:32-34 | "`min_raw: int = 26000, max_raw: int = 34000`" | Module docstring calls these "datasheet-ranged"; no page cited (low) | area: TWIN | related: TWIN.T01
- ASSUME | digital_twin/_sgp40_chip.py:41-43 | "Not datasheet-derived (min_raw/max_raw are)" | Step bound is a judgment call | area: TWIN | -
- LIMIT | digital_twin/_sgp40_chip.py:46 | "`self._pending_reply = bytes(3)`" | A read before any command returns zero bytes with an invalid CRC, not a NAK (low) | area: TWIN | -
- LIMIT | digital_twin/_sgp40_chip.py:62-65 | "`reply = word(0x0000) + word(word1) + word(word2)`" | Serial number's first word is always 0x0000 | area: TWIN | -
- LIMIT | digital_twin/_sgp40_chip.py:66-67 | "`reply = word(0xD400)  # datasheet Table 13: high byte 0xD4 = all tests passed`" | Self-test always passes; no execution time for self-test or measurement | area: TWIN | covered-by: TWIN.S02
- LIMIT | digital_twin/_sgp40_chip.py:68-71 | "`elif len(data) == 8 and data[0:2] == _CMD_MEASURE_RAW:`" | Compensation words' CRCs unchecked and compensation has no effect on the raw value | area: TWIN | covered-by: TWIN.S02
- ASSUME | digital_twin/_sgp40_chip.py:72-75 | "Unrecognized command - real hardware would simply not respond usefully; keep whatever was already pending rather than raising" | A wrong command code from a driver is silently accepted (e.g. heater-off) and a stale reply re-served; real NAK behaviour unmodelled | area: TWIN | related: TWIN.T01
- LIMIT | digital_twin/_sgp40_chip.py:78-81 | "`return (self._pending_reply + bytes(nbytes))[:nbytes]`" | Repeated reads re-serve the last reply; reads during a measurement never NAK | area: TWIN | related: TWIN.S02
- LIMIT | digital_twin/_sgp40_chip.py:55-57 | "Flip the trailing CRC byte of the last word in the reply" | CRC corruption knob hits only the last word's CRC | area: TWIN | -

## digital_twin/_scd30_chip.py
- ASSUME | digital_twin/_scd30_chip.py:1 | "datasheet-ranged random CO2/temperature/humidity" | Defaults 400-2000 ppm, 15-30 C, 20-70 %RH are room values, not the datasheet's measurement range (low) | area: TWIN | related: TWIN.T01
- ASSUME | digital_twin/_scd30_chip.py:42 | "`_FIRMWARE_VERSION = 0x0342  # plausible fixed value ... - never checked by the driver`" | Claim about driver behaviour | area: TWIN | -
- ASSUME | digital_twin/_scd30_chip.py:81-84 | "*_step: NOT datasheet-derived (the min/max above are) - a physical-plausibility judgment call" | Step bounds are judgment calls | area: TWIN | -
- DRIFT | digital_twin/_scd30_chip.py:98-100, :223 | "which the class docstring explains staying unpersisted" / "see class docstring" | `Scd30Chip` has no class docstring; the module docstring (:1-2) is the only one (low) | area: DOC | -
- LIMIT | digital_twin/_scd30_chip.py:110-128 | "`except ValueError: return  # malformed/truncated file - leave settings at their factory-fresh defaults`" | Corrupt state silently resets to defaults; a non-dict JSON would raise on `.get()` (low) | area: TWIN | covered-by: TWIN.T10
- LIMIT | digital_twin/_scd30_chip.py:130-143 | "`with open(self.state_path, \"w\") as f: json.dump(...)`" | Non-atomic save; an interrupted flush leaves a truncated file that reloads as defaults (low) | area: TWIN | related: TWIN.T10
- LIMIT | digital_twin/_scd30_chip.py:145-165 | "`self._timer.init(period=self._measurement_interval_s * 1000, ...)`" | Readings and RDY edges are produced whether or not continuous measurement was started; interval 0 gives a 0 ms periodic timer | area: TWIN | covered-by: TWIN.S01
- LIMIT | digital_twin/_scd30_chip.py:172-175 | "`pass  # no persistent chip-side state modeled that a reset would need to clear`" | Stop-continuous and soft reset are no-ops | area: TWIN | covered-by: TWIN.S01
- LIMIT | digital_twin/_scd30_chip.py:177-195 | "`arg = (data[2] << 8) | data[3]`" | Argument CRC (data[4]) never checked; no range validation of interval/altitude/offset/pressure | area: TWIN | covered-by: TWIN.S01
- ASSUME | digital_twin/_scd30_chip.py:183 | "re-arm at the new cadence, matching real hardware" | Unverified claim of real re-arm timing | area: TWIN | -
- PLATFORM | digital_twin/_scd30_chip.py:193, :223 | "volatile readback always reports 400 regardless (real hardware quirk)" | FRC readback quirk encoded in the fake | area: SENS | -
- LIMIT | digital_twin/_scd30_chip.py:196 | "Unrecognized shape - real hardware would just not respond usefully." | Wrong-length commands are silently ignored | area: TWIN | related: TWIN.T01
- LIMIT | digital_twin/_scd30_chip.py:158-163, 198-228 | "`reply = self._buffer`" | Compensation settings (pressure, altitude, temp offset, ASC, FRC) never affect readings; reading when not ready re-serves the stale buffer; unknown read gives zero bytes with bad CRC | area: TWIN | related: TWIN.T01
- LIMIT | digital_twin/_scd30_chip.py:206-208 | "`reply = reply[:2] + bytes([reply[2] ^ 0xFF]) + reply[3:]`" | Measurement corruption knob hits only the first word's CRC | area: TWIN | -

## digital_twin/_bmp3xx_chip.py
- LIMIT | digital_twin/_bmp3xx_chip.py:1-2 | "Calibration block is hand-picked, not real-chip data" | Factory-trim variety never exercised | area: TWIN | related: TWIN.S03
- LIMIT | digital_twin/_bmp3xx_chip.py:21, 176-177 | "`_BMP390_CHIP_ID = 0x60`" | Docstring names BMP388/BMP390 but only BMP390's ID is served; BMP388 (0x50) path unexercised | area: TWIN | covered-by: TWIN.S03
- ASSUME | digital_twin/_bmp3xx_chip.py:62-86 | "`for _ in range(20):` / `for _ in range(40):`" | Newton inversion converges in a fixed iteration count across the range (README :876-881 says verified) | area: TWIN | -
- ASSUME | digital_twin/_bmp3xx_chip.py:107-109 | "Not datasheet-derived (the min/max above are)" | Step bounds are judgment calls; 950-1050 hPa/15-30 C are narrower than the datasheet range (low) | area: TWIN | -
- ASSUME | digital_twin/_bmp3xx_chip.py:116-118 | "The ADC burst stays all-zero until the first forced trigger computes one, as real hardware has nothing to report before its first conversion" | Unverified reset value of data registers (low) | area: TWIN | -
- LIMIT | digital_twin/_bmp3xx_chip.py:149-157 | "`self.fault.maybe_raise(\"writeto\")`" | Zero-byte ACK probe has no `maybe_hang`; a history note says its absence once crashed every boot | area: TWIN | covered-by: TWIN.S03
- INVAR | digital_twin/_bmp3xx_chip.py:154-156 | "Nothing else in this driver calls plain writeto(), every register access going through writeto_mem()" | Fake answers only the empty probe on `writeto`; a future plain `writeto` from the driver would be silently ignored | area: TWIN | -
- LIMIT | digital_twin/_bmp3xx_chip.py:162-168 | "`if data and data[0] == _CONTROL_FORCED_MODE: self._trigger_measurement()`" | Conversion is instant (no conversion time, status data-ready at once); OSR/IIR stored but never affect timing or noise; only exact 0x13 triggers | area: TWIN | related: TWIN.T01
- LIMIT | digital_twin/_bmp3xx_chip.py:169-171 | "any other register: real hardware would just silently accept/ignore it too." | Soft reset resets status only (OSR/config kept); unknown-register behaviour assumed | area: TWIN | -
- LIMIT | digital_twin/_bmp3xx_chip.py:178-191 | "`elif reg_addr == _REGISTER_ERR: reply = bytes([0x00])`" | ERR register always 0 (fatal/cmd/conf errors unmodelled); reads at other offsets return zeros, no auto-increment across the register map | area: TWIN | related: TWIN.T01

## digital_twin/_fram_chip.py
- DRIFT | digital_twin/_fram_chip.py:1-2 | "answers `asy_fram_driver.py`'s exact opcode/CS-session shape" | The fake never sees CS; session framing is inferred from `write()` pairing | area: TWIN | covered-by: TWIN.S04
- SETTLED | digital_twin/_fram_chip.py:2 | "independently reimplemented, not shared with `tests/_fram_chip_fake.py`" | Deliberate duplication of the FRAM fake across mock and twin | area: TWIN | related: TEST.T05
- MIRROR | digital_twin/_fram_chip.py:22 | "`_DEFAULT_RDID = bytes([0x04, 0x7F, 0x03, 0x02])  # real MB85RS64V device ID (datasheets/fram/)`" | Datasheet constant copied | area: STOR | -
- MIRROR | digital_twin/_fram_chip.py:24-27 | "matches src/asy_fram_driver.py's own _ADDR_16BIT_MAX exactly" | Copied address-width threshold (2- vs 3-byte address) | area: STOR | -
- ASSUME | digital_twin/_fram_chip.py:67 | "the '{\"size\": N, \"memory_hex\": \"' prefix is always well under this" | 128-char header read assumes the file's own format | area: TWIN | -
- LIMIT | digital_twin/_fram_chip.py:57-94 | "`if idx == -1: return  # malformed/unrecognized file - leave self.memory at its blank default`" | The file's `size` field is ignored (a state file from another chip size loads partially); corrupt file silently yields a blank chip | area: TWIN | covered-by: TWIN.T10
- LIMIT | digital_twin/_fram_chip.py:102-106 | "`with open(self.state_path, \"w\") as f:`" | Non-atomic save; a truncated file reloads as a partial image with a zero tail (low) | area: TWIN | related: TWIN.T10
- LIMIT | digital_twin/_fram_chip.py:112-120 | "data phase of a previously-opened WRITE (opcode+address arrived in the prior call)" | A single write carrying opcode+address+data loses the data; writes past the end grow the buffer; no wraparound | area: TWIN | covered-by: TWIN.S04
- PLATFORM | digital_twin/_fram_chip.py:117, :129 | "WEL auto-clears at the CS rising edge after WRITE recognition" | Datasheet behaviour modelled per call pair, not per CS edge | area: STOR | related: TWIN.T04
- LIMIT | digital_twin/_fram_chip.py:126-129 | "`self.status = (data[1] & ~_WEL_BIT) | (self.status & _WEL_BIT)`" | Status-register block-protect (BP) bits and WP/WPEN are stored but never enforced on writes (low) | area: TWIN | related: STOR.T03
- LIMIT | digital_twin/_fram_chip.py:147-155 | "`buf[:] = self.memory[self._pending_addr : self._pending_addr + n]`" | Reads past the end return a short slice (bytearray shrinks) instead of wrapping; readinto without a pending op returns zeros | area: TWIN | covered-by: TWIN.S04

## digital_twin/_isl29125_chip.py
- PLATFORM | digital_twin/_isl29125_chip.py:27-64 | "`_DEVICE_ID = 0x7D  # datasheet FN8424 Rev 3.00 p9, Table 2`" | Register map, masks and timings cite a specific datasheet revision | area: SENS | -
- ASSUME | digital_twin/_isl29125_chip.py:43-46 | "Reserved bits read back ZERO ... (measured on real silicon 2026-09-12: writing 0xFF reads back 3f/bf/1f)" | Single dated silicon measurement | area: SENS | -
- ASSUME | digital_twin/_isl29125_chip.py:62-63 | "`_CYCLE_MS_12BIT = 19  # 3 x ~6.3ms: p6 makes tINT an n-bit counter on one oscillator, so 101 x 2**-4`" | 12-bit cycle time derived, not measured; twin uses typical values, no oscillator spread | area: TWIN | -
- ASSUME | digital_twin/_isl29125_chip.py:73-76, 86-89 | "min/max are datasheet-derived (p1: range 0 reaches 375 lux, range 1 reaches 10000)" | Defaults are 5-9000 lux, not the cited datasheet endpoints (low) | area: TWIN | -
- ASSUME | digital_twin/_isl29125_chip.py:90-93 | "Deliberately NOT the nominal 10000/375 = 26.67 ... which on real silicon it always does" | Fake ratio 25.9 is a chosen value; the claim about silicon is from M.1.5/M.1.6 | area: TWIN | -
- INVAR | digital_twin/_isl29125_chip.py:21-25, 96-100 | "the Pin(6) here and the Pin(6) the driver constructs are the SAME object" / "The line idles HIGH ... Without this it starts electrically asserted" | Depends on Pin registry identity and on the constructor driving the line high first | area: TWIN | -
- LIMIT | digital_twin/_isl29125_chip.py:152-164 | "Clipping is MODELLED, not clamped away" | Linear lux-to-count model with tint weights; no spectral/IR response; dark counts only in the low range | area: TWIN | related: TWIN.T11
- PLATFORM | digital_twin/_isl29125_chip.py:172 | "Register order is GREEN, RED, BLUE (p9, Table 1) - Table 20's own row labels are wrong." | Datasheet defect claim | area: SENS | -
- LIMIT | digital_twin/_isl29125_chip.py:176-179 | "RGBCF reports which channel the next conversion is on; rotated so it is never a constant" | RGBCF is an approximation, not real conversion sequencing | area: TWIN | -
- PLATFORM | digital_twin/_isl29125_chip.py:212-215 | "Measured on real silicon: 0x08 reads 0x00 straight after the 0x46 reset" | Silicon-measured divergence from Table 15 (M.1.2) | area: SENS | -
- LIMIT | digital_twin/_isl29125_chip.py:229-235 | "A persistent behavioural MODE, deliberately not a FaultInjector entry" | Only `int_stuck_high` exists; floating/stuck-low/bouncing INT unmodelled | area: TWIN | related: TWIN.T05
- LIMIT | digital_twin/_isl29125_chip.py:239-242 | "I2CDevice.setup()'s zero-byte ACK probe" | `handle_writeto` has no `maybe_hang` (the `--hang` vocabulary offers only `readfrom_mem`/`writeto_mem` for ISL29125) | area: TWIN | related: TWIN.T05
- LIMIT | digital_twin/_isl29125_chip.py:253-281 | "The address pointer auto-increments (p7), so one burst can carry 1-3 config bytes." | A burst starting in CONFIG stops at CONFIG3 and one in the threshold block stops at 0x07; bytes that on silicon would continue into the next block are dropped (low) | area: TWIN | -
- PLATFORM | digital_twin/_isl29125_chip.py:283-286 | "Table 15 marks 0x08 \"RO\", but p12's own BOUTF text requires an I2C write to clear it - the marking is a datasheet defect" | Datasheet-defect interpretation | area: SENS | -
- ASSUME | digital_twin/_isl29125_chip.py:288 | "any other register: real hardware silently accepts and ignores it too." | Unverified | area: TWIN | -
- PLATFORM | digital_twin/_isl29125_chip.py:290-309 | "measured on real silicon, a 16-byte read from 0x00 returns id, CONFIG1-3, both thresholds, status and all six data bytes" / "it does NOT roll over to 0x00" | Silicon-measured pointer behaviour | area: SENS | -
- PLATFORM | digital_twin/_isl29125_chip.py:310-320 | "The counter restarts when the flag is CLEARED, not on every status read (measured; Part M.1.2)" | Silicon-measured persistence-counter behaviour that the driver depends on | area: SENS | -

## digital_twin/_http_client.py
- ASSUME | digital_twin/_http_client.py:2 | "Every response it sees carries `Connection: close`, so no keep-alive support is needed." | Oracle depends on a server-side hook | area: TWIN | related: TEST.T17
- INVAR | digital_twin/_http_client.py:20-23 | "or b\"\" when read_body=False drained the response instead of materializing it - .json() must not be called on that" | Caller discipline | area: TWIN | -
- ASSUME | digital_twin/_http_client.py:25-27 | "Every body this client decodes is a JSON object" | `.json()` typed as dict | area: TWIN | -
- WORKAROUND | digital_twin/_http_client.py:29-31, :35 | "Its stub types the argument AnyStr, refusing bytearray - a stub gap only" / "`# type: ignore[type-var]`" | Suppression for a stub defect; removal trigger: none stated | area: TWIN | -
- INVAR | digital_twin/_http_client.py:32 | "here, not at the top: tests/ is absent from a standalone twin's path" | Lazy-import placement is load-bearing | area: TWIN | -
- MIRROR | digital_twin/_http_client.py:48-59 | "the same case tests_hardware/http_client.py's CEILING_CLOSE covers by including http.client.BadStatusLine" | Refusal classification mirrored in the hardware client | area: TEST | related: TEST.T17
- RISK | digital_twin/_http_client.py:66-72 | "or an EOF-truncated readline() (b\"\") from a connection that closed mid-headers" | A connection cut mid-headers is accepted as a complete header block; a body-less truncated response can pass (low) | area: TEST | related: TEST.T17
- LIMIT | digital_twin/_http_client.py:141-181 | "`content_length = headers.get(\"Content-Length\")`" | No timeout inside `fetch()`; case-sensitive header lookup; no chunked transfer-encoding support (low) | area: TEST | related: TEST.T16
- PLATFORM | digital_twin/_http_client.py:150-152 | "reader/writer are the same underlying Stream object on this build ... close() is a no-op here, the socket only actually closes via wait_closed()" | Build-specific asyncio stream fact | area: PLAT | -
- PLATFORM | digital_twin/_http_client.py:75-82 | "readinto() does one queue_read()+readinto() pair with no retry loop, so a spurious None ... must be retried" | Pinned asyncio stream behaviour | area: PLAT | -

## digital_twin/_unix_port_udp_addr_shim.py
- WORKAROUND | digital_twin/_unix_port_udp_addr_shim.py:1-3 | "Workaround for three confirmed MicroPython-Unix-port-only `socket` quirks" | Removal trigger: none stated | area: TWIN | covered-by: TWIN.T07
- INVAR | digital_twin/_unix_port_udp_addr_shim.py:3 | "Call `patch_asy_udp_socket_for_unix_port()` once, early, before constructing any `AsyUDPSocket`." | Call-order contract | area: TWIN | -
- LIMIT | digital_twin/_unix_port_udp_addr_shim.py:25-27, 74-76 | "`asy_udp_socket.AsyUDPSocket._connect = _patched_connect`" | Twin tests exercise patched `_connect`/`sendto`/`recvfrom`; the production plain-tuple address path is only exercised on hardware | area: NET | -
- SUPPRESS | digital_twin/_unix_port_udp_addr_shim.py:74-76 | "`# type: ignore[method-assign]`" | Three method-assign suppressions (twin scope, allowed) | area: TWIN | -
- SUPPRESS | digital_twin/_unix_port_udp_addr_shim.py:15 | "`# type: ignore[no-redef]  # no-op at runtime either way`" | Runtime `cast` fallback | area: TWIN | -
- ASSUME | digital_twin/_unix_port_udp_addr_shim.py:33-35 | "this project is IPv4-only (AsyUDPSocket's own addr type)" | IPv6 addresses pass through unnormalised | area: NET | -
- ASSUME | digital_twin/_unix_port_udp_addr_shim.py:41-43 | "Every real call site already hands over a numeric (host, port) tuple, so this getaddrinfo() is always local and never a DNS query" | A hostname would make the shim do a blocking real DNS lookup | area: NET | -
- ASSUME | digital_twin/_unix_port_udp_addr_shim.py:53-57 | "The native family field ... `struct.unpack(\"<H\", addr[0:2])`" | "Native" field read as little-endian: assumes a little-endian host (low) | area: TWIN | -

## digital_twin/unix_port_gc_unwedge.py
- WORKAROUND | digital_twin/unix_port_gc_unwedge.py:1-2 | "has since closed the root cause - this module stays wired in as defense in depth only" | Removal trigger: none stated | area: TWIN | covered-by: TWIN.T07
- PLATFORM | digital_twin/unix_port_gc_unwedge.py:9-11 | "gc.collect() is the recovery and the only one that works ... heap_unlock() is not a substitute" | Depends on `py/gc.c` lock-depth internals of the pinned version | area: PLAT | -
- ASSUME | digital_twin/unix_port_gc_unwedge.py:13-15 | "a collection at shutdown costs nothing and allocates nothing" | Justifies an unconditional `gc.collect()` outside the CLAUDE.md boot-confined sites (twin scope) | area: MEM | related: TEST.T03

## digital_twin/unix_port_poll_prewarm.py
- WORKAROUND | digital_twin/unix_port_poll_prewarm.py:1-2 | "Workaround for a confirmed MicroPython Unix-port-only `extmod/modselect.c` segfault (traced at v1.28.0; that file is unchanged at the current v1.29.0 pin)" | Removal trigger: none stated | area: TWIN | covered-by: TWIN.T07
- INVAR | digital_twin/unix_port_poll_prewarm.py:2, :49 | "Call `prewarm_poll_set()` as the very first statement of any entry point" / "Must run before any other code registers a poll object." | Order contract, convention only | area: TWIN | related: TWIN.T07
- PLATFORM | digital_twin/unix_port_poll_prewarm.py:4-7 | "asyncio.core is a private implementation module (the whole point here is reaching into its _io_queue)" | Depends on private asyncio internals (`_core._io_queue.poller`); `# type: ignore[import-not-found]` | area: PLAT | -
- LIMIT | digital_twin/unix_port_poll_prewarm.py:19-21 | "~28x the real peak: every device's max_connections is 6, and the hardest burst any tier drives is max(12, 3 x 6) = 18 clients ... A raised threshold, not a fix" | Beyond 512 registered fds the bug returns; the margin rests on copied figures | area: TWIN | related: TWIN.T07
- ASSUME | digital_twin/unix_port_poll_prewarm.py:21 | "~45ms at startup" | Single measurement | area: TWIN | -
- MIRROR | digital_twin/unix_port_poll_prewarm.py:23-26 | "Its own band, clear of test_digital_twin_http_client.py's canned servers at 18099-18103" | Port bands coordinated by hand across files | area: TEST | related: TEST.S21
- PLATFORM | digital_twin/unix_port_poll_prewarm.py:25, :31-33 | "SO_REUSEADDR does not let two live listeners share a port (that is SO_REUSEPORT)" / "the Unix port exposes no getsockname()" | Host/port facts behind the port scan | area: PLAT | -
- ASSUME | digital_twin/unix_port_poll_prewarm.py:51-70 | "Grow asyncio's shared `select.poll()` pollfds array to `ceiling` slots via real loopback connections, then release them" | Relies on the pollfds array never shrinking after unregister (an implementation detail of modselect.c) | area: PLAT | related: TWIN.T07
- SUPPRESS | digital_twin/unix_port_poll_prewarm.py:48 | "`# noqa: ANN401 - a packed sockaddr here, a tuple under CPython`" | Lint suppression | area: TWIN | -

## digital_twin/network.py
- DRIFT | digital_twin/network.py:2 vs digital_twin/README.md:107-109 | "`connect()` transitions through realistic phases over a short real delay rather than resolving instantly" | Code docstring contradicts README's "immediately" | area: DOC | covered-by: TWIN.S06
- ASSUME | digital_twin/network.py:30-33 | "Real association plus DHCP takes low single-digit seconds in the field. This sits under _poll_sta_connect_status()'s 5s budget" | `_CONNECT_DELAY_S = 0.7` is tied to a src/ budget; real connect timing and slow-connect paths unmodelled | area: TWIN | related: TWIN.T03
- LIMIT | digital_twin/network.py:35-37 | "`_CONNECTED_IFCONFIG = (\"192.168.1.42\", ...)`" | Static address, module-level country/hostname state shared across tests | area: TWIN | related: TEST.T07
- PLATFORM | digital_twin/network.py:42, :50 | "extmod/modnetwork.c: exactly 2 BYTES, else ValueError" / "MICROPY_PY_NETWORK_HOSTNAME_MAX_LEN, in bytes" | Copied port limits | area: PLAT | -
- LIMIT | digital_twin/network.py:57-73 | "`def __init__(self, if_id: int)`" | Every `WLAN(...)` is a fresh object with its own state (real rp2 returns a per-interface singleton); STA and AP share no radio state (low) | area: TWIN | related: TWIN.T03
- DRIFT | digital_twin/network.py:71 | "Test/Step-5-run fault injection" | Retired step-session term (low) | area: DOC | -
- LIMIT | digital_twin/network.py:86-105 | "An exhausted queue falls back to always-succeeds" | Outcomes are only scripted success/fail codes; no spontaneous link loss, no CYW43 `isconnected()` false positive, constant RSSI -50 | area: TWIN | related: TWIN.T03
- PLATFORM | digital_twin/network.py:109-112 | "cyw43_ll_wifi_join()'s -CYW43_EINVAL" / "real driver: unchecked copy past a 32-byte field" | Silicon-driver limits; an over-long SSID raises `AssertionError` only in the twin | area: NET | -
- INVAR | digital_twin/network.py:111-112 | "SSID over 32 bytes reached connect() - overflows cyw43's last_ssid_joined on silicon" | src/ must validate SSID length before `connect()`; the twin's assertion is the only guard at this tier | area: NET | -
- LIMIT | digital_twin/network.py:145-147 | "`def config(self, **kwargs: object) -> None:  # recorded verbatim, never inspected`" | AP-mode config unvalidated; query form `config('param')` unsupported | area: TWIN | covered-by: TWIN.S05

## digital_twin/neopixel.py
- ASSUME | digital_twin/neopixel.py:1-2 | "real `NeoPixel.write()` is a single busy-wait call with no return value/error path" | Platform claim; the fake does not model the busy-wait duration or colour byte order | area: TWIN | covered-by: TWIN.T11
- MIRROR | digital_twin/neopixel.py:1 | "Independent copy from `tests/neopixel.py`, not shared." | Deliberate duplicate fake | area: TEST | related: TEST.T05
- LIMIT | digital_twin/neopixel.py:6-9 | "found by the same audit rather than by reproducing a failure here" | `writes` bounded to 200 | area: TWIN | -

## digital_twin/typecheck.ini
- MIRROR | digital_twin/typecheck.ini:23-24 | "Same strictness as the root [tool.mypy], synced by hand (INI has no include)" | Hand-synced config | area: SCR | covered-by: SCR.T15
- ASSUME | digital_twin/typecheck.ini:5-6 | "Confirmed empirically: excluding digital_twin from the main pass alone did not fix its attribute resolution" | Single empirical claim | area: SCR | -
- ASSUME | digital_twin/typecheck.ini:8-10 | "digital_twin first so the twin's modules win ... No name collides (B.15)" | `mypy_path` also carries `tests` (for `_strict_json`), relying on path order to keep `tests/machine.py` shadowed | area: SCR | related: SCR.T15
- INVAR | digital_twin/typecheck.ini:9 | "typecheck.sh generates it first" | Pass depends on `build/generated_src/` existing | area: SCR | -

## digital_twin/launch.py
- MIRROR | digital_twin/launch.py:1, :369-375 | "brings up the same bus/peripheral wiring `sensortask_wozi.build_system()` uses" / "`I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)` ... `chips = {\"scd30\": i2c0.devices[0x61], ...}`" | Hand-typed wozi pins, WDT timeout and addresses that must track `devices/wozi.toml`; nothing checks them | area: TWIN | related: TWIN.T11
- INVAR | digital_twin/launch.py:1, :370-372 | "Standalone, `src/`-free CLI launcher" | Never calls `configure_wiring()`, so bus construction lazily opens `build/generated_src/sensortask_wozi_wiring_plan.json`: it needs generation to have run first | area: TWIN | related: TWIN.T11
- WORKAROUND | digital_twin/launch.py:2 | "`parse_args()` is hand-rolled (the vendored `argparse` lacks `action=\"append\"`/`choices=`)" | Platform library gap; removal trigger: none stated | area: TWIN | -
- MIRROR | digital_twin/launch.py:22-30, 71-80 | "`_FAULT_DEVICE_OPS = {...}`" / "`_HANG_DEVICE_OPS = {...}`" | Op vocabulary must match the op names each chip fake's handlers pass to `maybe_raise`/`maybe_hang`; shared with `run_generic_integration.py` | area: TWIN | related: TWIN.T05
- LIMIT | digital_twin/launch.py:26-27 | "dev-only; this launcher's own fixed wiring below has no ISL29125, so only run_generic_integration.py can actually apply one" | ISL29125 faults unreachable from launch.py | area: TWIN | -
- LIMIT | digital_twin/launch.py:57-61, 194-197 | "`network.WLAN.raise_on` has no repeat limit of its own, the fault stays armed until cleared" | WLAN faults are permanent for the process: transient WiFi faults not expressible from the CLI | area: TWIN | related: TWIN.T05
- SETTLED | digital_twin/launch.py:72-74 | "\"wlan\" has no real blocking call for time.sleep() to stand in for ... so it's deliberately not part of this vocabulary" | No WLAN hang (a blocking CYW43 call is unmodelled) | area: TWIN | -
- ASSUME | digital_twin/launch.py:84-86 | "TIMES defaults to 1, since real hardware gets one 8388ms window before the WDT resets it" | Rationale ties a CLI default to the WDT cap | area: TWIN | -
- INVAR | digital_twin/launch.py:208-213 | "A name in the vocabulary above is not the same as a chip this run wired" | Unwired device raises `ValueError` (enforced) | area: TWIN | -
- MIRROR | digital_twin/launch.py:216-219 | "Reproduces asy_bmp3xx_driver.py's own _read_coefficients()/compensation math independently ... same shape tests/test_digital_twin_bmp3xx.py's own _decode_temp_pressure()/_forward()" | Third copy of the BMP3xx compensation formula (driver, test, launcher) | area: TWIN | -
- ASSUME | digital_twin/launch.py:278 | "MEASURE_RAW, datasheet's own no-compensation example" | Hard-coded SGP40 command bytes from the datasheet | area: TWIN | -
- PLATFORM | digital_twin/launch.py:351-356 | "MicroPython's `random` has no instantiable Random class, unlike CPython" | Runtime fact; conflicts with `machine.py:28`'s "or a seeded random.Random" framing of the injection seam (low) | area: PLAT | -
- INVAR | digital_twin/launch.py:426-432 | "main()'s own `finally` cannot be relied on to run first, so unwedge before either flush" | Order of unwedge and flushes in the interrupt path | area: TWIN | related: TWIN.T07
- LIMIT | digital_twin/launch.py:294-298, 413 | "`if not no_wdt_feed: watchdog.feed()`" | `--no-wdt-feed` only yields a count; the twin never resets (low) | area: TWIN | -

## digital_twin/run_generic_integration.py
- DRIFT | digital_twin/run_generic_integration.py:1 | "most usefully a Session-3 `buildgen.generate.generate_device()`-generated one" | Retired session-numbering term (low) | area: DOC | -
- DRIFT | digital_twin/run_generic_integration.py:1-2 | "This file's own fault/hang chip lookup is the generalized form of `run_wozi_integration.py`'s..." | Very long docstring lines (comment-cap evasion) and references to retired runners | area: DOC | covered-by: TEST.S22
- INVAR | digital_twin/run_generic_integration.py:24 | "deliberately reused, not reimplemented - see digital_twin/README.md" | Shares launch.py's parsers; the two CLIs must agree | area: TWIN | -
- LIMIT | digital_twin/run_generic_integration.py:31, :346 | "`_CONFIG_DIR = \"digital_twin/config/\"`" | Config state lives at a fixed repo-relative path shared with other suites | area: TWIN | covered-by: SCR.S09
- DRIFT | digital_twin/run_generic_integration.py:32-34, :96-98, :311-313 | "unlike run_wozi_integration.py/run_dev_integration.py's own static imports" / "See both call sites' own comments in run_wozi_integration.py" | References to deleted files; :312-313 points readers at a file that no longer exists | area: DOC | covered-by: TEST.S24
- MIRROR | digital_twin/run_generic_integration.py:36-39, :425-428 | "The same value and one-time placement the real firmware boot entry uses" | `gc.threshold(32768)` copied by hand from the generated boot entry | area: TWIN | covered-by: SCR.S10
- SUPPRESS | digital_twin/run_generic_integration.py:99 | "`__hash__ = None  # type: ignore[assignment]`" | mypy suppression for the unhashable idiom | area: TWIN | -
- INVAR | digital_twin/run_generic_integration.py:148-152 | "\"\" means in-memory only, matches machine.configure_fram_state_path(None)'s own documented meaning" | CLI convention | area: TWIN | -
- LIMIT | digital_twin/run_generic_integration.py:194-196 | "A multi-instance driver is also keyed \"driver_nameext\"; the plain key stays, first instance winning, since the fault vocabulary only speaks plain driver names" | `--fault`/`--hang` can only reach the first instance of a multi-instance driver | area: TWIN | related: TWIN.T05
- PLATFORM | digital_twin/run_generic_integration.py:198-199 | "MicroPython dicts do not preserve insertion order as CPython's do" | Runtime fact the chip lookup depends on | area: PLAT | -
- INVAR | digital_twin/run_generic_integration.py:202-216 | "`if bus is None or bus._i2c is None:` / `chip = bus._spi.device`" | Reaches into private attributes of `src/` bus wrappers and generated variable names | area: TWIN | related: TWIN.T12
- INVAR | digital_twin/run_generic_integration.py:253-255 | "webserver is the last module build_system() assigns before its own grouped await x.setup() batch" | Readiness signal depends on generated-module assignment order (buildgen codegen); faults are applied only after this point, racing the boot setup batch | area: GEN | related: TWIN.T12
- LIMIT | digital_twin/run_generic_integration.py:263-265 | "Without it the twin models a dev board whose jumper is missing, and the exerciser spends the run timing out" | UART wiring depends on the plan's `uart` key and on private `uart._uart`/`poller` attributes | area: UART | related: TWIN.T12
- SUPPRESS | digital_twin/run_generic_integration.py:288-295 | "and an instrumentation-only gc.collect()" | `gc.collect()` in the twin sampler under the I.4(e) narrow exception | area: MEM | related: TEST.T03
- LIMIT | digital_twin/run_generic_integration.py:298-308 | "`_WIRE_LOG_CLEAR_INTERVAL_MS = 5000`" | `wire_log` still grows for up to 5 s of traffic between clears | area: TWIN | -
- SUPPRESS | digital_twin/run_generic_integration.py:319-325 | "`except OSError: pass  # already exists`" | Every mkdir `OSError` (not only EEXIST) is swallowed (low) | area: TWIN | -
- INVAR | digital_twin/run_generic_integration.py:330-335 | "Must run before anything else in the process registers a poll object" / "Must also run before anything constructs a real AsyUDPSocket" | Entry-point call order | area: TWIN | related: TWIN.T07
- MIRROR | digital_twin/run_generic_integration.py:356-360, :373 | "`module.main(cfg_path=_CONFIG_DIR, web_host=config.host, web_port=config.port)`" / "`assert module.conn is not None and module.watchdog is not None`" | Contract with the generated module's `main()` signature and variable names | area: GEN | related: TWIN.T12
- SUPPRESS | digital_twin/run_generic_integration.py:404-408 | "A real SIGINT can be re-delivered while this cleanup await is still in flight." | `KeyboardInterrupt` swallowed during cleanup | area: TWIN | -
- INVAR | digital_twin/run_generic_integration.py:389-395, :432-437 | "unwedge first rather than only in the outer handler" / "this is the only cleanup that runs at all" | Two cleanup sites, both must unwedge before flushing | area: TWIN | related: TWIN.T07
- LIMIT | digital_twin/run_generic_integration.py:401-403 | "`main_task.cancel()`" | Cancelling the generated `main()` does not cancel its sibling tasks (no parent/child tracking, CLAUDE.md known hang #2); shutdown relies on process exit | area: TWIN | -

## digital_twin/segfault_stress_repro.py
- SETTLED | digital_twin/segfault_stress_repro.py:1-6 | "Manual, deliberately-aggressive concurrency stress tool for the (now root-caused and fixed ...) ... Hardcoded (README.md)." | Manual-only tool kept after the fix; no tier executes it | area: TWIN | related: TWIN.T11
- SUPPRESS | digital_twin/segfault_stress_repro.py:4-6, :54-55 | "a MemoryError at higher concurrency is a distinct outcome this also reports" | `MemoryError` caught and counted as a result rather than a failure | area: MEM | -
- INVAR | digital_twin/segfault_stress_repro.py:13-14 | "`import machine` / `import sensortask_wozi`" | No `configure_wiring()` call: relies on the lazy wozi default plan in `build/generated_src/` | area: TWIN | -
- LIMIT | digital_twin/segfault_stress_repro.py:79-92 | "`prewarm_poll_set(port=port + 1000)`" | Unlike the other entry points it applies no UDP shim, no unwedge handler and no `gc.threshold()` (runs at the Unix default) (low) | area: TWIN | -
- SUPPRESS | digital_twin/segfault_stress_repro.py:92 | "`gc.collect()`" | Manual collect before the hammer rounds (twin tool) | area: MEM | related: TEST.T03
- SUPPRESS | digital_twin/segfault_stress_repro.py:103-106 | "`except (asyncio.CancelledError, Exception): pass`" | All exceptions during cleanup swallowed | area: TWIN | -
- SUPPRESS | digital_twin/segfault_stress_repro.py:111 | "`# type: ignore[arg-type]`" | mypy suppression on untyped opts dict | area: TWIN | -

## tests/test_digital_twin_bmp3xx.py
- MIRROR | tests/test_digital_twin_bmp3xx.py:1-2, 20-57 | "round-trips exactly through the real driver's own compensation formula" | The test uses its own copy of the formula (`_decode_temp_pressure()`/`_forward()`), not the driver's; a driver formula change would not reach it | area: TWIN | -
- ASSUME | tests/test_digital_twin_bmp3xx.py:110-112 | "well above the ~1e-4 worst-case quantization error this introduces, but still tight enough to prove the inversion is real" | Tolerance rationale | area: TWIN | -
- LIMIT | tests/test_digital_twin_bmp3xx.py:72-75 | "`assert reply[0] in (0x50, 0x60)  # BMP384/BMP388 vs BMP390`" | Accepts either ID though the fake only ever serves 0x60; BMP388 path untested | area: TWIN | related: TWIN.S03
- LIMIT | tests/test_digital_twin_bmp3xx.py:151-157 | "would violate the default 1.0/5.0 bounds - proves the override took" | Step-override test cannot fail (scripted deltas lie inside both bounds) | area: TEST | covered-by: TEST.S03
- PLATFORM | tests/test_digital_twin_bmp3xx.py:161-162 | "asy_bmp3xx_driver.py's own _read() rejects anything outside 300-1250 hPa / -40-85 degC (datasheet sec 1, Table 2)" | Datasheet range the fake's defaults must stay inside | area: SENS | -
- ASSUME | tests/test_digital_twin_bmp3xx.py:214-215 | "real hardware would just silently accept/ignore it too" | Unverified claim encoded as a test expectation | area: TWIN | -

## tests/test_digital_twin_bus_hazard_concurrency.py
- INVAR | tests/test_digital_twin_bus_hazard_concurrency.py:17-19 | "growing the Unix port's pollfds array corrupts non-fd poll objects already in it, which is a segfault, not a test failure" | Prewarm must precede the imports | area: TWIN | related: TWIN.T07
- SUPPRESS | tests/test_digital_twin_bus_hazard_concurrency.py:22-25 | "`# noqa: E402 - must follow the prewarm above, which is the point of it`" | Three E402 suppressions | area: TEST | -
- MIRROR | tests/test_digital_twin_bus_hazard_concurrency.py:50-52 | "`_next_port = 19400  # own range, avoids TIME_WAIT/port collision with the 19100+ range`" | Hand-coordinated port bands across test files | area: TEST | related: TEST.S21
- INVAR | tests/test_digital_twin_bus_hazard_concurrency.py:81-86 | "A new driver added to a device's own i2c1 needs an entry here before it gets this generic check - see the fail-loud assert there." | `_I2C_DRIVER_HEALTH_FIELD` must grow per driver; enforced by an assert at :167-168 | area: TEST | -
- LIMIT | tests/test_digital_twin_bus_hazard_concurrency.py:112-127, 185-227 | "Mid-run, not before or after: the point is a full ceiling of REST work landing while the sensor tasks are genuinely mid-transaction" | Twin bus transactions take zero time and never await, so interleaving can occur only between awaits; only wozi and dev are booted here (other four devices get no twin concurrency run in this file) | area: TWIN | related: TWIN.T08
- LIMIT | tests/test_digital_twin_bus_hazard_concurrency.py:154-156 | "SGP40_I2C._reset()'s general-call broadcast ... must actually have fired at least once" | Asserts only the bus-log entry; no chip fake reacts to a general call | area: TWIN | covered-by: TWIN.S02
- PLATFORM | tests/test_digital_twin_bus_hazard_concurrency.py:161 | "str.removeprefix() isn't used here since it's unproven under this MicroPython target" | Unverified runtime capability | area: PLAT | -
- RISK | tests/test_digital_twin_bus_hazard_concurrency.py:177-178 | "wozi's own SGP40+BMP3xx-on-i2c1 pairing can never be confirmed on real hardware ... so this twin run is its actual verification" | wozi's bus grouping rests on the twin tier alone | area: TWIN | -
- RISK | tests/test_digital_twin_bus_hazard_concurrency.py:233-235 | "wozi is never physically flashed, so this twin run is FRAM's only fault-then-recovery verification for it" | Single-tier verification for wozi FRAM recovery | area: STOR | -
- LIMIT | tests/test_digital_twin_bus_hazard_concurrency.py:255-257, 276-277 | "FRAM_SPI._write() has no try/except of its own (unlike the I2C drivers); a SPI-level failure propagates raw" | Documents a src/ layering fact; protection lives in AsyFramManager | area: STOR | -
- INVAR | tests/test_digital_twin_bus_hazard_concurrency.py:260-262 | "verify_present() self-acquires that (non-reentrant) lock internally" | Caller must not hold the FRAM lock around `verify_present()` | area: STOR | -
- SETTLED | tests/test_digital_twin_bus_hazard_concurrency.py:322-323 | "A persistent one degrades to None instead of propagating, and leaves the chunk marked BUSY by design - destructive readout" | By-design behaviour of the FRAM manager | area: STOR | -
- LIMIT | tests/test_digital_twin_bus_hazard_concurrency.py:353-355 | "A single disconnect, not repeated flapping: the ESTABLISHED retry branch is a genuine, non-fast-forwardable 60s sleep" | Repeated WiFi flapping is not covered at the twin tier (bench only) | area: NET | -
- LIMIT | tests/test_digital_twin_bus_hazard_concurrency.py:364-370 | "its shared_bus_log check assumes a short window that never wraps the twin I2C fake's bounded log deque" | Log-based assertions break on long runs because `I2C.log` keeps only 200 entries; this test takes ~75 s | area: TWIN | related: TEST.T04
- MIRROR | tests/test_digital_twin_bus_hazard_concurrency.py:412-414, 442-447, 473-475 | "Twin-tier parity for the chunk-level gating the mock tier proves against a fake bus and the flash tier against the real chip" | Same FRAM gating claims held at mock, twin and flash tiers | area: STOR | -
- SETTLED | tests/test_digital_twin_bus_hazard_concurrency.py:442-444 | "the accepted, intended behavior ... _read_chunk() has to WRITE a transient busy marker before reading, so write protection gates read() as well as write()" | Accepted behaviour | area: STOR | -
- SETTLED | tests/test_digital_twin_bus_hazard_concurrency.py:502-507 | "AsyFramManager.__init__ sets _pause = False and nothing restores it from FRAM, so the pause is RAM-only." | Pause does not survive reboot (by design) | area: STOR | -

## tests/test_digital_twin_construction_{arzi,dev,grkizi,klkizi,schlafzi,wozi}.py
- LIMIT | tests/test_digital_twin_construction_wozi.py:1-6 (same in all six) | "one of six wrappers over the shared tests/_digital_twin_construction_scenarios.py library (SPECIFICATION.md Part E.2.1)" | The six wrappers hold no test logic; all coverage (and its prewarm/UDP-shim setup) lives in the scenario library outside this partition | area: TEST | related: TEST.S04

## tests/test_digital_twin_fram.py
- SETTLED | tests/test_digital_twin_fram.py:1 | "independently reimplemented, not sharing tests/_fram_chip_fake.py" | Deliberate duplicate FRAM fakes | area: TEST | related: TEST.T05
- ASSUME | tests/test_digital_twin_fram.py:80-82 | "still behaves like a real bus transaction rather than raising - zero-filled, not garbage/untouched" | Encodes an unverified claim about real MISO content | area: TWIN | -
- LIMIT | tests/test_digital_twin_fram.py:193-195 | "This test is not about fragmentation, which no unit test reproduces deterministically" | The MemoryError the chunking fixed has no deterministic regression test | area: MEM | -
- INVAR | tests/test_digital_twin_fram.py:245-247 | "it is temporarily shrunk to 1 to force a straddle" | Module constant monkeypatched and restored in `finally` | area: TEST | -
- LIMIT | tests/test_digital_twin_fram.py:219-237 | "a malformed/unrecognized file ... must degrade to a blank chip, not raise" / "must leave the rest of memory at its blank default" | Silent-degrade on corrupt/truncated state is the tested contract | area: TWIN | covered-by: TWIN.T10
- DRIFT | tests/test_digital_twin_fram.py:303-308 | "SPECIFICATION.md Part L.4: _decode_addr() used to always read exactly 2 address bytes ... discovered via a real digital-twin CI failure" | Historic bug narrative in a test comment (low) | area: DOC | -

## tests/test_digital_twin_generic_wiring.py
- INVAR | tests/test_digital_twin_generic_wiring.py:14 | "digital_twin/ must precede tests/ here" | sys.path order discipline per file | area: TEST | -
- INVAR | tests/test_digital_twin_generic_wiring.py:183-190 | "machine._wiring_plan being process-global state that later tests mutate" | Shared mutable module state across tests; each test must reset it | area: TEST | related: TEST.T07

## tests/test_digital_twin_http_client.py
- ASSUME | tests/test_digital_twin_http_client.py:51-52 | "asy_webserver_service.py's own _mark_connection_close() always sets this on the response too - this client never implements keep-alive" | Oracle relies on server hook | area: TEST | related: TEST.T17
- MIRROR | tests/test_digital_twin_http_client.py:81-83 | "as tests_hardware/http_client.py's CEILING_CLOSE does by including http.client.BadStatusLine" | Refusal classification mirrored across the twin and hardware clients | area: TEST | related: TEST.T17
- RISK | tests/test_digital_twin_http_client.py:92-94 | "a ValueError there escaped as a test failure under a burst big enough to make FIN-without-bytes the common outcome rather than RST" | Refusal shape depends on kernel TCP behaviour | area: TEST | -
- PLATFORM | tests/test_digital_twin_http_client.py:123-135, 175-179 | "Stream.readinto() can legitimately return None right after poll() said the socket was readable" | Pinned asyncio stream behaviour the client depends on | area: PLAT | -
- DRIFT | tests/test_digital_twin_http_client.py:249 | "_soak() and _wait_until_serving() never look at a fetched body" | `_soak()` no longer exists anywhere in the repo (soak moved host-side) (low) | area: DOC | related: TEST.S24
- LIMIT | tests/test_digital_twin_http_client.py:313-317 | "not a claim about src/asy_webserver_service.py's behavior - that is the twin integration suite's job" | Smoke test against a hand-built server only | area: TEST | -
- MIRROR | tests/test_digital_twin_http_client.py (canned servers) vs digital_twin/unix_port_poll_prewarm.py:23 | "clear of test_digital_twin_http_client.py's canned servers at 18099-18103" | Fixed ports 18099-18103 coordinated by hand | area: TEST | related: TEST.S21

## tests/test_digital_twin_isl29125.py
- LIMIT | tests/test_digital_twin_isl29125.py:2 | "Real-time INT-pin scheduling is exercised only through the synchronous set_illumination()/_produce_new_reading() hooks here" | Real-time behaviour is tested elsewhere only | area: TWIN | -
- SUPPRESS | tests/test_digital_twin_isl29125.py:58 | "`# type: ignore[arg-type]`" | mypy suppression on the chip factory | area: TEST | -
- PLATFORM | tests/test_digital_twin_isl29125.py:122-131 | "measured on real silicon (2026-09-12) ... Measured 2026-09-13 on a just-powered board: 0x08 read 0x04, a second read 0x00 ... This CONTRADICTS p12" | Single dated silicon measurements encoded as test expectations | area: SENS | -
- MIRROR | tests/test_digital_twin_isl29125.py:425-427 | "Register-map behaviours measured against real silicon - see tests_hardware/README.md's probe." | Twin expectations tied to the C.11.1 conformance probe | area: TWIN | related: TEST.S20
- ASSUME | tests/test_digital_twin_isl29125.py:420-422 | "3 x ~6.3ms, derived from p6's n-bit-counter model" | 12-bit cycle time is derived, not measured | area: TWIN | -

## tests/test_digital_twin_isl29125_autorange.py
- LIMIT | tests/test_digital_twin_isl29125_autorange.py:2 | "none of which any mock-tier test can prove because none of them has a chip whose gain actually changes" | Auto-range continuity/hysteresis/calibration proven only at twin tier (and NeoPixel rig) | area: TWIN | related: TEST.T15
- LIMIT | tests/test_digital_twin_isl29125_autorange.py:68-70 | "AutoRangeDwell defaults to 10 s ... The dwell itself is covered at tier 1" | Twin tests run with dwell 0; the default dwell is never exercised end to end here | area: TWIN | -
- SUPPRESS | tests/test_digital_twin_isl29125_autorange.py:95-96 | "No strict= (ruff B905): MicroPython's zip() rejects it" / "`# noqa: B905`" | Platform-forced lint suppression | area: TEST | -
- PLATFORM | tests/test_digital_twin_isl29125_autorange.py:95, 106-107 | "MicroPython's zip() rejects it" / "No star-unpacking in a list display: MicroPython rejects it outright" | Runtime language gaps (RUF005 exemption) | area: PLAT | -
- ASSUME | tests/test_digital_twin_isl29125_autorange.py:123-125 | "4% covers the whole uncalibrated error budget: the nominal 26.67 against this unit's real 25.9 is a 2.96% high-range overstatement" | Tolerance tied to the fake's chosen ratio | area: TWIN | -
- ASSUME | tests/test_digital_twin_isl29125_autorange.py:253-255 | "Two cycles (606ms at 16 bit) keeps the window inside the 1s SampleInterv" | Timing assumption tying fake cycle time to driver sample interval | area: TWIN | -

## tests/test_digital_twin_launch.py
- MIRROR | tests/test_digital_twin_launch.py:220-225, 252-256 | "duration must clear both network.py's _CONNECT_DELAY_S (0.7s) ... and _sensor_loop()'s 2.0s poll interval" | Test durations coupled to twin timing constants | area: TEST | related: TEST.T04
- ASSUME | tests/test_digital_twin_launch.py:216, 261 | "only 0.5s, well under the 8000ms WDT timeout" | Smoke-test wall-clock bounds | area: TEST | -

## tests/test_digital_twin_machine.py
- INVAR | tests/test_digital_twin_machine.py:19-21 | "digital_twin/ must precede tests/ here specifically so `machine` resolves to the twin's own fake" | Per-file sys.path order discipline | area: TEST | -
- INVAR | tests/test_digital_twin_machine.py:178-180 | "A later \"fix\" returning fresh objects would break the whole interrupt path with nothing else failing." | Pin identity is load-bearing; guarded by this test | area: TWIN | -
- LIMIT | tests/test_digital_twin_machine.py:201-203 | "configure_fram_state_path()/flush_fram(), which has no dedicated wiring test either" | FRAM persistence hooks lack a wiring test | area: TWIN | related: TWIN.T10
- LIMIT | tests/test_digital_twin_machine.py:272-274 | "an id nothing wires ... write() is logged and silently dropped, readinto() zero-fills the buffer" | Unwired SPI bus silently answers zeros | area: TWIN | -
- PLATFORM | tests/test_digital_twin_machine.py:319-320, 329-330 | "Confirmed directly against the pinned v1.29.0 ports/rp2/machine_wdt.c source" | WDT id/cap facts pinned to v1.29.0 | area: PLAT | -
- ASSUME | tests/test_digital_twin_machine.py:350-355 | "a granularity close to its period races it, the observed count depending on scheduling" | Timing-sensitive test design (5 ms vs 150 ms) | area: TEST | related: TEST.T04
- LIMIT | tests/test_digital_twin_machine.py:475-484 | "re-.init() the SAME Timer object from inside that object's currently-firing callback ... the just-fired ONE_SHOT alarm already being consumed" | Regression covers only a ONE_SHOT self-rearm; a PERIODIC self-rearm is untested | area: TWIN | related: TWIN.T02
- LIMIT | tests/test_digital_twin_machine.py:518-520 | "The one live-timing test in this whole package ... not a precise-cadence assertion" | Timer cadence accuracy is never asserted | area: TWIN | covered-by: TWIN.T09

## tests/test_digital_twin_machine_uart.py
- MIRROR | tests/test_digital_twin_machine_uart.py:1-3 | "Re-runs tests/_uart_link_contract.py's shared bodies against the twin backend, so the twin and mock link models can differ in fidelity but never in semantics" | Mock↔twin UART contract, test-enforced | area: TEST | related: TEST.T05
- ASSUME | tests/test_digital_twin_machine_uart.py:29-31 | "Real machine.UART() re-inits the peripheral rather than refusing" | Port behaviour claim | area: UART | -
- LIMIT | tests/test_digital_twin_machine_uart.py:46-48 | "assert a floor well under that but far above zero, so the test is about the mechanism, not the exact clock" | Wire-time accuracy only loosely asserted | area: TWIN | -

## tests/test_digital_twin_network_neopixel.py
- MIRROR | tests/test_digital_twin_network_neopixel.py:1 | "neopixel.py is a near-verbatim duplicate of tests/neopixel.py, already proven correct there - this file only locks in its basic shape" | Duplicate fake; shape-only test | area: TEST | related: TEST.T05
- PLATFORM | tests/test_digital_twin_network_neopixel.py:326-327, 352, 358 | "Mirrors extmod/modnetwork.c: country() takes exactly 2 BYTES, hostname() at most 32" / "65 bytes: cyw43_ll_wifi_join()'s -CYW43_EINVAL" / "33 bytes would overflow the driver's SSID buffer" | Port/driver limits copied into the fake | area: PLAT | -

## tests/test_digital_twin_poll_prewarm.py
- PLATFORM | tests/test_digital_twin_poll_prewarm.py:16-17 | "getaddrinfo() returns a packed sockaddr on this port, not the (host, port) tuple CPython gives" | Unix-port fact | area: PLAT | -
- SUPPRESS | tests/test_digital_twin_poll_prewarm.py:74, 78 | "`# type: ignore[attr-defined, assignment]  # deliberate monkeypatch`" | Monkeypatching the module's `socket` | area: TEST | -
- ASSUME | tests/test_digital_twin_poll_prewarm.py:36-38 | "two files calling prewarm_poll_set() within the same ~45ms window both bound one fixed port" | Dated failure analysis | area: TEST | -
- INVAR | tests/test_digital_twin_poll_prewarm.py:21-22, 102-103, 136-137 | "The helper tests scan a band of their own" / "Never a silent fallback onto some other port" / "18099-18103 belong to test_digital_twin_http_client.py" | Port band allocation by convention | area: TEST | related: TEST.S21

## tests/test_digital_twin_real_website_integration.py
- LIMIT | tests/test_digital_twin_real_website_integration.py:1-3 | "the Unix-port counterpart to scripts/build_firmware.py's real ARM build, which can only be compiled here, never executed" | The frozen firmware image is never executed by any tier | area: TWIN | related: SCR.T10
- SUPPRESS | tests/test_digital_twin_real_website_integration.py:19-21 | "`# noqa: E402`" | Three E402 suppressions after the prewarm | area: TEST | -
- MIRROR | tests/test_digital_twin_real_website_integration.py:23-25 | "Mirrors asy_wifi_service.py's own _PHASE_STA_SEEKING/_PHASE_HOTSPOT values ... keep in sync with asy_wifi_service.py's own definitions" | Copied `const()` values | area: TEST | -
- MIRROR | tests/test_digital_twin_real_website_integration.py:45-47 | "Own port range (19300+)" | Port band coordination | area: TEST | related: TEST.S21
- ASSUME | tests/test_digital_twin_real_website_integration.py:69-74 | "Measured directly against this file's real twin fakes: consistently ready within ~400ms, so 1.0s keeps a ~2.5x margin" | Fixed sleep sized from a measurement | area: TEST | related: TEST.T04
- SUPPRESS | tests/test_digital_twin_real_website_integration.py:95 | "`# type: ignore[no-any-return]`" | mypy suppression | area: TEST | -
- SETTLED | tests/test_digital_twin_real_website_integration.py:121-134 | "\"wozi\" is hardcoded deliberately, not a stale device-specific leftover ... picking wozi ... once is complete coverage rather than a gap" | Only wozi's frozen website runs under the Unix port here; other five sites rely on buildgen tests | area: TWIN | -
- LIMIT | tests/test_digital_twin_real_website_integration.py:200-201 | "No real WiFi task is started - conn._conn_phase is set directly instead" | Hotspot redirect tested via a private-state seam | area: TEST | -
- ASSUME | tests/test_digital_twin_real_website_integration.py:304-306 | "A real browser opens two connections per page load after bundling/inlining (Part H.7)" | Browser behaviour assumption sizing the burst | area: WEB | -

## tests/test_digital_twin_run_generic_integration.py
- DRIFT | tests/test_digital_twin_run_generic_integration.py:2 | "The smoke test reuses the hand-written sensortask_wozi module" | No hand-written module exists; also a ~700-char docstring line | area: DOC | covered-by: TEST.S24
- MIRROR | tests/test_digital_twin_run_generic_integration.py:108-112 | "32768 matches buildgen.codegen.generate_boot_entry_source()'s own real-firmware boot entry" | Test pins a copied constant | area: TEST | covered-by: SCR.S10
- DRIFT | tests/test_digital_twin_run_generic_integration.py:137-138, 221 | "replaces run_wozi_integration.py's/run_dev_integration.py's own hardcoded ..." / "the retired run_wozi_integration.py's own test used" | References to retired runners | area: DOC | covered-by: TEST.S24
- LIMIT | tests/test_digital_twin_run_generic_integration.py:192-193 | "parse_fault_spec()'s own vocabulary (launch.py) can only ever address a driver by its plain name, never per-instance" | Per-instance fault targeting impossible | area: TWIN | related: TWIN.T05
- LIMIT | tests/test_digital_twin_run_generic_integration.py:227-229 | "main()'s real supervisor leaves several background tasks running after main_task.cancel(), the orphaned-task memory-pressure problem" | Only one end-to-end boot test allowed per process because of orphaned tasks | area: TWIN | -

## tests/test_digital_twin_scd30.py
- LIMIT | tests/test_digital_twin_scd30.py:2 | "Real-time RDY-pin scheduling is exercised only via the synchronous _produce_new_reading() hook here" | Real-time path tested elsewhere | area: TWIN | -
- ASSUME | tests/test_digital_twin_scd30.py:81-83 | "matching a real device silently accepting these" | Stop/soft-reset acceptance claim | area: TWIN | covered-by: TWIN.S01
- PLATFORM | tests/test_digital_twin_scd30.py:107-109, :150 | "volatile readback always 400 regardless of the last value applied" / "cleared the instant it was read (Interface Description 1.4.4)" | Sensor-specific facts encoded in tests | area: SENS | -
- LIMIT | tests/test_digital_twin_scd30.py:202-210 | "would violate the default 50.0/1.0/3.0 bounds - proves the override took" | Step-override test cannot fail | area: TEST | covered-by: TEST.S03
- PLATFORM | tests/test_digital_twin_scd30.py:227-228 | "CO2 accuracy-guaranteed 400-10'000ppm, humidity 0-100%RH, temperature -40-70 degC" | Datasheet ranges the defaults must sit inside | area: SENS | -

## tests/test_digital_twin_sensortask_integration.py
- SETTLED | tests/test_digital_twin_sensortask_integration.py:1-3 | "Deliberately wozi-only - SPECIFICATION.md Part E.2.1 says why." | Middle tier boots only wozi | area: TWIN | -
- SUPPRESS | tests/test_digital_twin_sensortask_integration.py:32-38 | "`# noqa: E402`" | Six E402 suppressions | area: TEST | -
- INVAR | tests/test_digital_twin_sensortask_integration.py:85-90 | "configure_wiring() explicitly, every call ... MicroPython's globals() does not preserve definition order" | Test order is undefined; shared `machine._wiring_plan` must be reset per test | area: TEST | related: TEST.T07
- ASSUME | tests/test_digital_twin_sensortask_integration.py:98-104 | "consistently ready within ~400ms, so 1.0s keeps a ~2.5x margin" | Fixed sleep from a measurement | area: TEST | related: TEST.T04
- WORKAROUND | tests/test_digital_twin_sensortask_integration.py:128-136 | "since this build's socket may not support settimeout()" / "sendto() rejects a plain (host, port) tuple here" | Test-side Unix-port socket quirks; removal trigger: none stated | area: TEST | -
- DRIFT | tests/test_digital_twin_sensortask_integration.py:178-179, 184-186, 415-417 | "see the \"Construction across every real device\" section near the end of this file" | No such section exists in this file any more (moved to `tests/_digital_twin_construction_scenarios.py`, E.2.1) | area: DOC | -
- LIMIT | tests/test_digital_twin_sensortask_integration.py:229-231 | "The exact values cannot be cross-checked against buildgen from a MicroPython-run test" | `build` field checked for shape only | area: TEST | -
- INVAR | tests/test_digital_twin_sensortask_integration.py:286-288 | "a nested asyncio.run() call here segfaulted the real interpreter instead of raising a clean error" | CLAUDE.md nested-`asyncio.run()` rule | area: TEST | related: TEST.T06
- LIMIT | tests/test_digital_twin_sensortask_integration.py:425-439, 461-463 | "Deliberately does NOT drive this through main()/start_and_check_tasks()" / "just over the hardcoded 8000ms WDT timeout" | Watchdog check uses its own 1 s feed loop, so it detects only stalls approaching 8 s; the real supervisor's feed path is not the one under test | area: TWIN | -
- RISK | tests/test_digital_twin_sensortask_integration.py:429-431 | "those orphaned references starved the Unix-port heap - a real MemoryError once, and a hard segfault once" | Orphaned-task hazard in shared-process tests | area: TEST | -
- SUPPRESS | tests/test_digital_twin_sensortask_integration.py:505, 530 | "`# type: ignore[method-assign]`" | Two method-assign suppressions (only instances in twin tests) | area: TEST | -
- SUPPRESS | tests/test_digital_twin_sensortask_integration.py:543-546, 627, 705, 779 | "a known failure mode on this file's shared heap otherwise, where orphaned task references starved a later build_system() with a real MemoryError before this collect() was added" | `gc.collect()` added to prevent a MemoryError in tests | area: MEM | covered-by: TEST.S11
- ASSUME | tests/test_digital_twin_sensortask_integration.py:575-577 | "Eight, not one, so the transition does not depend on WHEN the seeding below lands ... (MEASUREMENTS archive 7C)" | Timing-window workaround in test design | area: TEST | related: TEST.T04
- LIMIT | tests/test_digital_twin_sensortask_integration.py:610-612 | "currently \"0.0.0.0\" - a twin-fidelity gap, see digital_twin/README.md - not a real product bug" | DNS answer is the AP-mode 0.0.0.0 address in the twin | area: TWIN | related: TWIN.S05
- ASSUME | tests/test_digital_twin_sensortask_integration.py:663-666, 694, 735, 772 | "No public \"init done\" flag exists to poll, so this is a plain, generously-bounded sleep." | Fixed 2.5 s sleep for SGP40 init | area: TEST | related: TEST.T04
- LIMIT | tests/test_digital_twin_sensortask_integration.py:789-790 | "the command's duration is a hardcoded 300s no client can shorten, so the unpause half is driven through the same SystemService call" | Auto-unpause after `mempause` is not exercised end to end | area: CORE | -

## tests/test_digital_twin_sgp40.py
- SETTLED | tests/test_digital_twin_sgp40.py:5-7 | "digital_twin/ is not on scripts/test.sh's MICROPYPATH, deliberately kept separate from the unit-test set" | Per-file sys.path insertion convention | area: TEST | -
- ASSUME | tests/test_digital_twin_sgp40.py:49-50 | "exact content is opaque to the real driver (only word[0] is checked)" | Claim about driver behaviour | area: SENS | -
- ASSUME | tests/test_digital_twin_sgp40.py:137-139 | "no crash - real hardware would just not respond usefully either" | Unknown-command behaviour asserted without silicon evidence | area: TWIN | related: TWIN.T01

## tests/test_digital_twin_uart_link.py
- SUPPRESS | tests/test_digital_twin_uart_link.py:24-26 | "`# noqa: E402`" | Three E402 suppressions | area: TEST | -
- INVAR | tests/test_digital_twin_uart_link.py:67-69 | "a real select.poll() never re-checks a Python object's ioctl(), so readiness would never be seen" | Bounded poller rule (CLAUDE.md known hang) | area: TEST | -
- LIMIT | tests/test_digital_twin_uart_link.py:86-91 | "Drives the responder's own UART_Comm.uart_listen() directly rather than UartLinkExerciser's real listen-loop task, deliberately" | Real listen-loop task not exercised in this file | area: UART | -
- SETTLED | tests/test_digital_twin_uart_link.py:147-148 | "payload_size and timeout are out-of-band agreements that must match on both ends, and nothing is negotiated" | CLAUDE.md owner decision restated | area: UART | -
- INVAR | tests/test_digital_twin_uart_link.py:173-175 | "AsyFramManager is a bump-pointer allocator, so instantiation order IS the on-chip layout and an inserted chunk would turn every persisted log into garbage" | Construction order is a persistence contract | area: STOR | -
- SUPPRESS | tests/test_digital_twin_uart_link.py:166, 273 | "`# type: ignore[union-attr]`" | mypy suppressions | area: TEST | -
- ASSUME | tests/test_digital_twin_uart_link.py:284-285 | "timeout is sized well above the measured worst-case collection pause" | Relies on a measured GC pause on the host, not rp2 | area: UART | -
- SUPPRESS | tests/test_digital_twin_uart_link.py:296, 361, 370, 401, 452, 461 | "`gc.collect()`" | Six manual collects in tests (forced-GC scenario, leak measurements, churn recovery) | area: MEM | related: TEST.T03, TEST.S11
- LIMIT | tests/test_digital_twin_uart_link.py:353-355, 440-442 | "The twin records every delivered byte in an unbounded wire_log ... it is the harness growing, not the driver" | Twin instrumentation distorts heap measurements unless cleared | area: TWIN | -
- LIMIT | tests/test_digital_twin_uart_link.py:377-379, 475 | "The bound is generous - this asserts \"no per-transfer leak\", not an allocation budget" / "`assert leaked < 8192`" | Absolute heap-delta bound | area: MEM | covered-by: TEST.S12
- SUPPRESS | tests/test_digital_twin_uart_link.py:399 | "`except MemoryError:  # the pressure this test exists to create`" | Deliberately induced and swallowed MemoryError inside the unit tier, next to the MemoryError log gate | area: MEM | related: TEST.T18
- SUPPRESS | tests/test_digital_twin_uart_link.py:411-413 | "MicroPython has no `await` inside a comprehension, so ruff's suggested rewrite does not compile" / "`# noqa: PERF401`" | Platform-forced lint suppression | area: TEST | -
- SETTLED | tests/test_digital_twin_uart_link.py:426-428 | "Run under MicroPython's own default (no proactive collection) as well as the project's 32768" | Both GC stages exercised in-test | area: MEM | -

## tests/test_digital_twin_unix_port_gc_unwedge.py
- LIMIT | tests/test_digital_twin_unix_port_gc_unwedge.py:17-29 | "The wedged state itself ... is deliberately NOT constructed here: it is unreachable from Python." | The recovery is only tested on the healthy path; the real reproduction is historical | area: TWIN | related: TWIN.T07
- PLATFORM | tests/test_digital_twin_unix_port_gc_unwedge.py:20-22 | "gc.collect() clears the stuck collect flag but not heap_lock()'s depth counter, and heap_unlock() does the reverse" | py/gc.c internals | area: PLAT | -

## tests/test_digital_twin_webserver_concurrency_{arzi,dev,grkizi,klkizi,schlafzi,wozi}.py
- LIMIT | tests/test_digital_twin_webserver_concurrency_wozi.py:1-2 (same in all six) | "one of six wrappers over the shared tests/_webserver_concurrency_scenarios.py library (Part E.2.1)" | Wrappers hold no logic; coverage lives outside this partition | area: TEST | -
- INVAR | tests/test_digital_twin_webserver_concurrency_wozi.py:10-12 (same in all six) | "First, before the library boots a device and bursts real connections at it: pollfds growth is a Unix-port segfault otherwise" | Import-time prewarm order | area: TWIN | related: TWIN.T07
- SUPPRESS | tests/test_digital_twin_webserver_concurrency_wozi.py:14 (same in all six) | "`# noqa: E402 - must follow the prewarm`" | Six E402 suppressions | area: TEST | -

## Coverage
| file | comment/doc lines read | items |
|---|---|---|
| digital_twin/README.md | 919 (full text) | 117 |
| digital_twin/_bmp3xx_chip.py | 19 | 10 |
| digital_twin/_crc8.py | 3 | 2 |
| digital_twin/_fault_injection.py | 8 | 6 |
| digital_twin/_fram_chip.py | 29 | 11 |
| digital_twin/_http_client.py | 45 | 10 |
| digital_twin/_isl29125_chip.py | 100 | 17 |
| digital_twin/_scd30_chip.py | 25 | 14 |
| digital_twin/_sgp40_chip.py | 14 | 10 |
| digital_twin/_unix_port_udp_addr_shim.py | 19 | 8 |
| digital_twin/launch.py | 41 | 14 |
| digital_twin/machine.py | 167 | 61 |
| digital_twin/neopixel.py | 8 | 3 |
| digital_twin/network.py | 25 | 10 |
| digital_twin/run_generic_integration.py | 67 | 21 |
| digital_twin/segfault_stress_repro.py | 14 | 7 |
| digital_twin/typecheck.ini | 13 | 4 |
| digital_twin/unix_port_gc_unwedge.py | 8 | 3 |
| digital_twin/unix_port_poll_prewarm.py | 24 | 9 |
| tests/test_digital_twin_bmp3xx.py | 39 | 6 |
| tests/test_digital_twin_bus_hazard_concurrency.py | 112 | 17 |
| tests/test_digital_twin_construction_arzi.py | 2 | 0 |
| tests/test_digital_twin_construction_dev.py | 2 | 0 |
| tests/test_digital_twin_construction_grkizi.py | 2 | 0 |
| tests/test_digital_twin_construction_klkizi.py | 2 | 0 |
| tests/test_digital_twin_construction_schlafzi.py | 2 | 0 |
| tests/test_digital_twin_construction_wozi.py | 2 | 1 |
| tests/test_digital_twin_fram.py | 58 | 6 |
| tests/test_digital_twin_generic_wiring.py | 32 | 2 |
| tests/test_digital_twin_http_client.py | 88 | 6 |
| tests/test_digital_twin_isl29125.py | 101 | 5 |
| tests/test_digital_twin_isl29125_autorange.py | 102 | 6 |
| tests/test_digital_twin_launch.py | 45 | 2 |
| tests/test_digital_twin_machine.py | 88 | 8 |
| tests/test_digital_twin_machine_uart.py | 19 | 3 |
| tests/test_digital_twin_network_neopixel.py | 34 | 2 |
| tests/test_digital_twin_poll_prewarm.py | 26 | 4 |
| tests/test_digital_twin_real_website_integration.py | 79 | 9 |
| tests/test_digital_twin_run_generic_integration.py | 61 | 5 |
| tests/test_digital_twin_scd30.py | 66 | 5 |
| tests/test_digital_twin_sensortask_integration.py | 275 | 16 |
| tests/test_digital_twin_sgp40.py | 30 | 3 |
| tests/test_digital_twin_uart_link.py | 97 | 13 |
| tests/test_digital_twin_unix_port_gc_unwedge.py | 26 | 2 |
| tests/test_digital_twin_webserver_concurrency_arzi.py | 5 | 0 |
| tests/test_digital_twin_webserver_concurrency_dev.py | 5 | 0 |
| tests/test_digital_twin_webserver_concurrency_grkizi.py | 5 | 0 |
| tests/test_digital_twin_webserver_concurrency_klkizi.py | 5 | 0 |
| tests/test_digital_twin_webserver_concurrency_schlafzi.py | 5 | 0 |
| tests/test_digital_twin_webserver_concurrency_wozi.py | 5 | 3 |

Notes: the construction and webserver-concurrency wrappers are identical except for the device name, so each set has one grouped item cited against its wozi file. Code outside comments was also read for every digital_twin/*.py file in full, and for tests where a comment needed context. The keyword and suppression grep across the partition found nothing beyond what is recorded.

## Totals per kind
| kind | count |
|---|---|
| LIMIT | 134 |
| ASSUME | 77 |
| INVAR | 56 |
| PLATFORM | 52 |
| MIRROR | 38 |
| SUPPRESS | 29 |
| DRIFT | 29 |
| SETTLED | 22 |
| WORKAROUND | 12 |
| RISK | 11 |
| TODO | 2 |
| OPENQ | 0 |
| **total** | **462** |

## Top 10
1. LIMIT digital_twin/machine.py:899-913: the twin RTC never advances and is not coupled to `time.time()`/`gmtime()` (the host clock). NTP-set clock jumps and RTC-driven time are unmodelled. Related: TWIN.T09, NET.T11.
2. LIMIT digital_twin/machine.py:852-854: the twin WDT only records and never resets the process, so reboot-after-watchdog behaviour is never exercised. Related: README:692-708 late-feed workaround.
3. DRIFT digital_twin/machine.py:828-830: the self-rearm comment says the old task returns on its own, but with a PERIODIC re-init the old loop keeps running, so the timer may double-fire. The regression test covers ONE_SHOT only (tests/test_digital_twin_machine.py:475-484).
4. LIMIT digital_twin/machine.py:916-940: `SimulatedRebootError` subclasses `Exception`, so a broad `except Exception` in src/ swallows a simulated `reset()`.
5. ASSUME digital_twin/machine.py:500-502: "no test comes close" to the `ticks_us` period. UART-link wire time rests on signed `ticks_diff` from a fixed epoch, and long dev twin runs (manual or CI) may exceed half the period.
6. ASSUME/LIMIT digital_twin/_sgp40_chip.py:72-75 and _scd30_chip.py:177-196: the fakes silently accept unrecognised commands and never check argument CRCs, so a wrong command code from a driver passes at the twin tier.
7. DRIFT digital_twin/README.md:667-669: README says the suite has no elapsed-time budget for ResetErrors, but `scripts/_digital_twin_ci_suite.py:116, 273-281` asserts `_RESET_ERRORS_BUDGET_S`.
8. RISK tests/test_digital_twin_bus_hazard_concurrency.py:177-178 and :233-235: wozi's i2c1 grouping and its FRAM fault recovery are verified only by this twin run. Twin I2C transactions take zero time (see the LIMIT at :112-127).
9. DRIFT tests/test_digital_twin_sensortask_integration.py:178-179, 184-186, 415-417: these point to a "Construction across every real device" section that no longer exists in the file.
10. LIMIT digital_twin/README.md:354-358 and run_generic_integration.py:194-196: single-chip persistence globals, and `--fault`/`--hang` reach only the first instance of a multi-instance driver. Multi-instance devices are only partly covered.
