# UART promotion → buildgen migration: scope, research, and worklist

**Status**: temporary planning document, written by the orchestrating session on 2026-09-13 for a
spun-off implementation session. Delete this file once the migration is complete and its durable
facts have been folded into `BACKLOG.md`/`CLAUDE.md`/`SPECIFICATION.md`/`digital_twin/README.md`
as appropriate — same lifecycle `UART_C_PORT_CHANGELOG.md` already follows for a different reason
(see CLAUDE.md's own doc-lifecycle working agreement).

**This is step (1) of CLAUDE.md's step-session workflow** ("refine the task's own scope into a
detailed list... doing real research first"), done by the orchestrating session so the
implementation session can start at step (2) (clarifying questions) rather than re-deriving all of
this from scratch. It is a map, not a spec — several design points below are flagged as open and
are exactly the kind of thing step (2) should either resolve from what's here or raise back to the
owner.

## 0. Why this exists

`main` picked up a full UART promotion (protocol module + driver update + real-hardware
validation) while this repo's `claude/automated-build-chain-nuzumw` branch was independently
migrating every device's construction from hand-written `src/sensortask_<device>.py` files to the
`buildgen/` TOML→codegen pipeline (see BUILD_CHAIN_PLAN.md). The UART work was written entirely
against the *pre-buildgen* shape: it hand-edits `src/sensortask_dev.py`'s module-level globals
directly. That file no longer exists on this branch — every device's `sensortask_<device>.py` is
now generated at build time from `devices/<device>.toml` (`scripts/_generate_sensortask_modules.py`
→ `buildgen.generate`). The task is to bring the UART promotion's *complete, already-proven*
functionality and test coverage onto this branch, expressed the buildgen way, not to redesign or
re-validate the protocol itself.

## 1. Hard boundaries — settled elsewhere, not this session's call

- **The C-port reconciliation is explicitly out of scope.** `UART_C_PORT_CHANGELOG.md` and the
  BACKLOG.md entry about it describe a *separate*, future session's job (importing and verifying
  the Arduino-side C implementation). Don't touch either beyond carrying them forward unmodified.
- **No real sensor behind the link.** BACKLOG.md ("UART sensor integration") and CLAUDE.md both
  record an owner-confirmed decision: the protocol module stays standalone; no BME688/BSEC or any
  other chip is wired behind it. Preserve that — the buildgen instance is a bench link exerciser,
  not a sensor driver, even though it will sit in the same `[[instance]]` TOML shape sensors use.
- **The wire protocol itself (`src/asy_uart_comm.py`'s `const()` values, framing, recovery
  timings) is a two-implementation contract** (CLAUDE.md, new "UART message protocol" bullet).
  This migration must not change any of it — it's a structural port (new construction path, same
  driver code) — so no `UART_C_PORT_CHANGELOG.md` entry should be needed. If the migration finds a
  reason to touch `asy_uart_comm.py`'s or `asy_uart_driver.py`'s actual logic (not just how they're
  imported/constructed), stop and flag it rather than deciding unilaterally; that would be a Class
  A change needing the changelog and likely the owner's input.
- **`wozi` never gets a UART instance** — CLAUDE.md is explicit: "`dev` carries two instances
  across its permanent crossover jumper and `wozi` carries none — wozi is never physically
  flashed, so wiring it there would add an untestable peripheral." Only `devices/dev.toml` changes.
- **`asy_uart_driver.py`/`asy_uart_comm.py` must never block the asyncio loop, not even in a wait
  state** (CLAUDE.md) — already true of the promoted code; just don't introduce a new call path
  that violates it (e.g. don't wrap either in something that adds a synchronous wait).
- **Known segfault hazard**: a test helper that calls `asyncio.run()` (this repo's `run()`
  wrappers, `tests/_uart_comm_harness.py`'s pattern) must only ever be invoked from synchronous
  test-function scope, never from inside a running coroutine (CLAUDE.md, "Known segfault cause,
  fixed"). Keep this invariant in any new/adapted test.

## 2. What already exists on `main` and needs to be brought over

Diverged from this branch's merge-base (`03192a5`) at `origin/main`'s tip (`348be6d`). Full file
list (`git diff --stat 03192a5..origin/main`):

**Pure ports — promoted code, no buildgen dependency, should merge in close to as-is:**
- `src/asy_uart_driver.py` (455 lines) — the async `machine.UART` wrapper. Constructor:
  `UART(port_id, tx_pin, rx_pin, baudrate=9600, bits=8, parity=None, stop=1, rxbuf=256, txbuf=256,
  timeout=0, timeout_char=1, invert=0, poll_wait_ms=20, poll_idle_ms=None, crc=None, framing=None)`.
- `src/asy_uart_comm.py` (1138 lines) — the point-to-point message protocol, `UART_Comm` class.
  Constructor: `UART_Comm(uart, role, payload_size=48, timeout=1000, get_callback=None,
  set_callback=None, message_callback=None, fram=None, history_length=10, debug=None, name="UART",
  logger=None)`. `role` is `ROLE_INITIATOR`/`ROLE_RESPONDER` (module constants). Has `async def
  setup()`, and (confirmed by reading `src/sensortask_dev.py`'s own usage) `get_task_starters()`
  returns `[]` for an initiator and the listen-loop starter for a responder — "the role decides the
  task set, and an initiator that listened would mean both ends initiate." Also has
  `get_timer_starters()`/`get_error_sources()`/`get_loggers()`, matching every other constructed
  module's convention (SPECIFICATION.md Part C). **Not** a `SensorReader`/`SensorReaderConfig`
  subclass (owner direction, per its own module docstring) — matters for
  `buildgen/driver_registry.py`'s resolution, see §4.
- `src/framing_codecs.py` (149 lines) — pluggable frame codec `asy_uart_driver.py` reads/writes
  through (pass-through default + COBS).
- `digital_twin/machine.py`'s UART additions (~350 new lines): a full `UART(io.IOBase)` fake, a
  `UARTLink`/`_LinkDirection` byte-level crossover model with real wire-time scheduling and fault
  knobs (drop/corrupt/truncate/delay/duplicate/noise), a bounded `LinkPoller` (never a real
  `select.poll()` — CLAUDE.md's known CI-hang cause), and `attach_crossover_jumper(fake_a, fake_b)`
  → `(UARTLink, LinkPoller, LinkPoller)`. **This is already fully built and generic — it does not
  know about "dev" or any device by name.** It only needs *wiring up* from the buildgen side (§5).
- `tests/machine.py`'s equivalent additions (333 lines) — the same fake, held to the same contract
  via `tests/_uart_link_contract.py`, for the mock (non-twin) test tier.
- `tests/_uart_comm_harness.py`, `tests/_uart_link_contract.py` — shared test infrastructure, reused
  across mock/hazard/twin tiers. Port as-is.
- `tests/test_asy_uart_driver.py` (+912 lines), `tests/test_asy_uart_comm.py` (2124 lines, new),
  `tests/test_framing_codecs.py` (200 lines, new), `tests/test_uart_comm_hazard.py` (1290 lines,
  new), `tests/test_machine_uart_link.py` (203 lines, new), `tests/test_digital_twin_machine_uart.py`
  (114 lines, new) — all exercise `src/asy_uart_driver.py`/`asy_uart_comm.py`/`framing_codecs.py`
  and the two fake `machine.py`s directly. None of these need buildgen/`sensortask_dev` at all —
  port them close to verbatim.
- `tests_hardware/device_scripts/uart_crossover_exchange.py`, `uart_crossover_recovery.py`,
  `uart_idle_poll_rate.py`, `uart_link_under_concurrent_system_load.py`,
  `uart_read_never_blocks_the_loop.py` — every one is documented as an "isolated-driver device
  script" that **constructs the two `UART_Comm` instances directly, never through
  `sensortask_dev`'s task graph**. These need no buildgen changes at all — port as-is.
- `tests_hardware/flash/test_uart_crossover.py`, `tests_hardware/bench/test_uart_link_under_api_load.py`
  — real-hardware automated tiers; the bench one specifically exercises the link "under the full
  production HTTP stack," so it likely does depend on a real `sensortask_dev`-equivalent firmware
  build (i.e. the buildgen-generated one) being flashed. Read both fully before deciding whether
  either needs adaptation for the new construction path — they may only need updated import paths
  or none at all, since `scripts/build_firmware.py` freezes all of `src/*.py` regardless of how
  `sensortask_dev.py` itself was produced.
- `UART_C_PORT_CHANGELOG.md`, `SPECIFICATION.md` Part J (UART Message Protocol, starts ~line 2775
  on main) — carry forward unmodified; Part J is the protocol reference, read it before touching
  `asy_uart_comm.py`/`asy_uart_driver.py` at all.
- `pyproject.toml`'s 2-line addition — `ANN401` per-file ignores for
  `tests/test_asy_uart_comm.py`/`tests/_uart_comm_harness.py`. Port directly.

**Needs real design work — the actual point of this migration:**
- `src/sensortask_dev.py`'s UART section (hand-written on `main`; **does not exist on this
  branch** — buildgen generates `sensortask_dev.py` now). This is where the real work is: turning
  its module-level globals/functions into something `buildgen/codegen.py` can emit. Full inventory
  of what it does today, read directly from `main` (`git show origin/main:src/sensortask_dev.py`):
  - Two `asy_uart_driver.UART` instances: `uart0 = UART(0, 0, 1, baudrate=115200, rxbuf=512,
    txbuf=512, poll_wait_ms=2, poll_idle_ms=50)` (tx=GP0, rx=GP1) and `uart1 = UART(1, 8, 9, ...)`
    (tx=GP8, rx=GP9) — the bench's permanent GP0↔GP9/GP1↔GP8 crossover jumper
    (`dev_legacy/README.md`).
  - `uart_initiator = UART_Comm(uart0, ROLE_INITIATOR, payload_size=48, timeout=1000, debug=debug,
    name="UART_INIT")` — no callbacks (an initiator only ever asks).
  - `uart_responder = UART_Comm(uart1, ROLE_RESPONDER, payload_size=48, timeout=1000,
    get_callback=_uart_get_callback, set_callback=_uart_set_callback,
    message_callback=_uart_message_callback, debug=debug, name="UART_RESP")`.
  - Application-level "exerciser" logic, today loose module-level globals/functions with no
    reusable shape: two bench-only command ids (`_UART_CMD_BANNER=0x01`, `_UART_CMD_ECHO=0x02`), a
    fixed banner string, a GET/SET/message callback trio implementing "answer a banner request,
    echo back whatever was last SET," a periodic `_uart_exercise_loop()` (the initiator asks for
    the banner once a second — "nothing else on a live system ever initiates one"), and two
    counters (`uart_transfers`/`uart_failures`) surfaced through `/status` as a `("UARTLINK",
    _uart_link_maintenance)` `maintenance_sensors` entry.
  - Both instances flow through the *generic* collector functions
    (`_collect_error_sources()`/`_collect_level_setters()`/`_collect_task_starters()`/
    `_collect_timer_starters()`, all of which already iterate a `modules` tuple uniformly) — only
    the exercise-loop task starter is bolted on as an extra, hand-written lambda
    (`+ [lambda: asyncio.create_task(_uart_exercise_loop())]`), since it isn't owned by either
    `UART_Comm` instance itself.
  - `await uart_initiator.setup()` / `await uart_responder.setup()` in the setup-await sequence.
- `digital_twin/run_dev_integration.py`'s UART addition (41 lines) — after `_wait_until_built()`,
  calls `machine.attach_crossover_jumper(sensortask_dev.uart0._uart, sensortask_dev.uart1._uart)`
  and swaps in the returned bounded `LinkPoller`s. This is hand-written glue for the
  hand-written `sensortask_dev`; once `sensortask_dev.py` is buildgen-generated, this wiring should
  move into the generic digital-twin wiring-plan mechanism (§5) rather than staying as bespoke code
  in the integration-test runner, the same way `digital_twin/machine.py`'s `configure_wiring()`
  already generically wires I2C/SPI from `compute_twin_wiring()`'s JSON output instead of a
  hand-written per-device `if` chain.
- `tests/test_digital_twin_run_dev_integration.py` (53 lines), `tests/test_sensortask_dev.py` (156
  lines), `tests/test_digital_twin_uart_link.py` (483 lines, new), `tests/test_ticks_rollover.py`
  (58 lines) — all reference `sensortask_dev` module-level names directly (`sensortask_dev.uart0`,
  etc.) or exercise the full built graph; these need to be re-pointed at whatever the
  buildgen-generated module's actual attribute names turn out to be (should be `uart0`/`uart1`/
  the two instance labels buildgen derives from the TOML, e.g. `uart_comm`/`uart_comm_<name_ext>` —
  see §4's naming question).
- `html/definitions/dev.json`'s 6-line addition — **this file is buildgen-generated on this
  branch** (`buildgen/definitions.py`, driven by `# @web`/`# @web-group` tags on `src/` files —
  confirmed by reading `buildgen/definitions.py`'s docstring and `buildgen/web_tag.py`). The two
  new fields (`UARTLINK_Transfers`, `UARTLINK_Failures`, both `section=measurements`) and two new
  debug-level entries (`UART_INIT`, `UART_RESP`) must come from `@web`/`@web-group` tags on
  whichever `src/` module ends up owning the exerciser logic (§4), following the exact pattern
  `src/asy_sgp40_driver.py`'s own `BackupTS`/`RestoreTS` maintenance fields already use — read that
  file's `@web-group`/`@web` tags before designing the new ones. Don't hand-edit
  `html/definitions/dev.json` directly; find (or add) the mechanism that makes it fall out of the
  generator.

## 3. What already exists in `buildgen/` on this branch (recap for the implementing session)

Read these directly rather than trusting only this summary — they will change under the
implementation anyway:

- `buildgen/model.py` — `[[instance]]` parsing; `InstanceSpec.fields`/`.wiring`; nothing UART-
  specific needed here, the shape is already generic.
- `buildgen/buildspec.py` — **the one hand-maintained per-driver table**
  (`REQUIRED_TOML_FIELDS`/`OPTIONAL_TOML_FIELDS`/`ALLOWED_INSTANCE_FIELDS`/`BUS_ATTACHED_DRIVERS`/
  `ADDRESS_CAPABLE_DRIVERS`/`FIXED_ADDRESS_DRIVERS`). A new driver needs a row added by hand — its
  own module docstring says so explicitly.
- `buildgen/driver_registry.py` — resolves `driver = "<name>"` to a `src/` class via the
  `asy_<name>_driver.py` → `*_Reader` convention, AST-parsed, with an explicit `_OVERRIDES` table
  for the three drivers that can't follow it (`fram`→`AsyFramManager`, `neopixel`→`NeopixelDriver`,
  `notification`→`NotificationCoordinator`) because none is a `SensorReader`/`SensorReaderConfig`
  subclass. `UART_Comm` is in the same boat (owner-confirmed "never a subclass") — whatever module
  ends up as the buildgen driver almost certainly needs an `_OVERRIDES` entry, not the AST-scan
  path. `_class_needs_setup()`'s fallback (any own `async def setup`) already covers a non-Reader
  service correctly, as it does for `AsyFramManager` today.
- `buildgen/pico_gpio.py` — the real Pico W GPIO↔peripheral map, transcribed from the datasheet
  (`datasheets/RP-008312-DS-2-pico-w-datasheet.pdf`, Figure 2). Has `I2C_ROLE`/`SPI_ROLE` tables
  and `WIRELESS_RESERVED_GPIOS`. **A UART pin-role table does not exist yet.** RP2040 UART0/UART1
  TX/RX pin-mux pairs need transcribing from the same datasheet figure — `src/asy_uart_driver.py`'s
  own module comment already names the two legal pairs used today (UART1: GP24/GP25; UART0:
  GP28/GP29) and separately notes the dev bench actually uses GP0/GP1 (UART0) and GP8/GP9 (UART1) —
  **read the datasheet directly to build the full table**, the way `I2C_ROLE`/`SPI_ROLE` were
  built, rather than assuming these four pins are the only legal ones. `gpio_exists()`'s
  wireless-reserved-pin exclusion applies uniformly already; a `UART_ROLE` table only needs to add
  the peripheral-function check on top, exactly parallel to `_BUS_PIN_ROLE`'s existing shape in
  `buildgen/validate.py`.
- `buildgen/validate.py` — `_VALID_BUS_IDS`/`_BUS_WIRE_FIELDS`/`_BUS_ALLOWED_FIELDS`/
  `_BUS_PIN_ROLE`/`_check_bus_tables()`/`_check_gpio_collisions()` are the exact mechanism a new
  `"uart"` bus kind plugs into — `_VALID_BUS_IDS` would gain `"uart0": "uart", "uart1": "uart"`,
  `_BUS_WIRE_FIELDS["uart"] = ("tx_pin", "rx_pin")`, plus wherever `baudrate` (and optionally
  `rxbuf`/`txbuf`/`poll_wait_ms`/`poll_idle_ms`) belongs — as bus-table fields (parallel to i2c's
  `frequency`) or as instance fields. **Open question, flagged for the implementing session's own
  step (2)**: unlike i2c/spi, a UART "bus" here is never shared by more than one instance (it's a
  point-to-point peripheral, not a multi-drop bus) — decide whether modeling it as a `[bus.uart0]`
  table is the right fit at all, or whether `tx_pin`/`rx_pin`/`baudrate`/etc. belong directly on the
  `[[instance]]` table instead (more like `neopixel`'s bare `pin` field than like `scd30`'s
  `bus`-attached shape). Recommendation to weigh: reusing `[bus.*]` gets GPIO-collision checking,
  the existing `_check_all_buses_used()` orphan check, and matches how `fram` already sits
  bus-attached on `spi0` — but it also drags in `_BUS_ALLOWED_FIELDS`/`_check_bus_tables()`'s
  i2c/spi-shaped assumptions (e.g. `"cs_pin declared on a bus table" is rejected` — fine for UART
  too, just confirm nothing else i2c/spi-specific leaks in). Either choice is buildable; pick one
  and be consistent, and say which in the eventual PR description.
- `buildgen/graph.py` — construction-order topological sort, entirely generic over
  `wiring_schema`/`@wiring` tags already. No changes anticipated unless the two UART instances need
  an explicit dependency on each other (see next bullet) or on `fram` (they don't take a `fram=`
  kwarg on `main` — confirmed by reading `src/sensortask_dev.py`'s construction call directly, and
  independently by SPECIFICATION.md's Part A.7 excerpt quoted in the diff: "no `fram=`... the
  protocol itself carries no application semantics").
- **Do the two instances need to reference each other in generated code at all?** On `main`, no —
  `uart_initiator`/`uart_responder` are each constructed independently; only the *digital twin*
  needs to know they're a pair (to call `attach_crossover_jumper()`). Real firmware code has no
  in-code "peer" reference — the link exists only on the physical wire. Recommendation: don't add a
  `@wiring`-style peer reference between the two `[[instance]]` entries; instead let the digital
  twin's wiring-plan JSON (§5) name the pairing directly (e.g. by bus id or by role), which is both
  simpler and matches the real-hardware code shape (no peer object needed there either).
- `buildgen/codegen.py` — `_build_call()`'s per-driver `if driver == "...":` branches are where the
  actual `UART_Comm(...)`/`asy_uart_driver.UART(...)` construction calls need a new branch (or two:
  bus construction, parallel to the existing `i2c`/`spi` branch in `_emit_build_system()`'s bus
  loop, plus instance construction). `_emit_collectors()`'s four collector functions
  (`_collect_error_sources/_collect_level_setters/_collect_task_starters/_collect_timer_starters`)
  **already generically iterate every constructed instance** except `fram` — a new UART instance
  needs zero changes there, it just needs to land in the `modules` list, which it will automatically
  once it's a normal `[[instance]]`. The one genuinely bespoke thing `main`'s hand-written file does
  — appending `_uart_exercise_loop()`'s task starter outside the generic per-module loop — needs an
  equivalent hook; whether that's a special-cased `if "uart_crossover" in have:` append (matching
  the existing `sgp40`-specific `maintenance_sensors` special-case already in `_emit_webserver()`)
  or something the new module's own `get_task_starters()` can already express (if the exerciser
  class embeds the periodic loop as one more entry in its *own* `get_task_starters()` return list,
  no codegen special-case is needed at all — this is almost certainly the cleaner design, see §4).
  `_emit_webserver()`'s `maintenance_sensors=` line needs the same kind of extension the `sgp40`
  branch already demonstrates, for the `UARTLINK` stats — or, better, `WebserverService`'s existing
  registration mechanism might already generalize (check `maintenance_sensors=` isn't itself
  `sgp40`-specific plumbing, just a hardcoded single-entry tuple in codegen today).
- `buildgen/twin_wiring.py` — `compute_twin_wiring(model)` returns
  `{"device", "buses": {...}, "spi": {...}}`, consumed by `digital_twin/machine.py`'s
  `configure_wiring()`. This needs a third key (e.g. `"uart"`) describing each UART instance's
  bus id/pins/baudrate/role, **plus which two instances are the crossover pair** so
  `configure_wiring()` can call the *already-existing* `attach_crossover_jumper()` between the
  fakes it constructs for `uart0`/`uart1` — no new code is needed in `digital_twin/machine.py`
  itself for the link mechanism (`UART`/`UARTLink`/`attach_crossover_jumper`/`LinkPoller` are
  already fully built and generic, per §2); only `configure_wiring()`'s dict-driven construction
  path needs to grow a UART branch that calls what already exists. This is also where
  `digital_twin/run_dev_integration.py`'s current hand-written
  `attach_crossover_jumper(sensortask_dev.uart0._uart, sensortask_dev.uart1._uart)` call (§2)
  should retire in favor of the generic mechanism, the same way `_LEGACY_WIRING_PLANS` was
  eliminated in favor of generated JSON earlier on this branch (see BUILD_CHAIN_PLAN.md's Session
  5/recent commit `27bce9c` — the exact same "hand-written → generated" shift, one layer up).
- `buildgen/generate.py`/`buildgen/frozen_modules.py` — the top-level `generate_device()`
  entry point and frozen-module manifest; skim for anything hardcoding the current 6-driver set
  before assuming a 7th driver needs no changes here.
- `buildgen/web_tag.py`/`buildgen/definitions.py` — read fully before designing the new
  `@web`/`@web-group` tags (§2's `html/definitions/dev.json` bullet).

## 4. The central design question: what is the new buildgen driver?

Two real objects need constructing per instance (`asy_uart_driver.UART` + `UART_Comm`), plus
bench-only application logic with no home in either promoted module (banner/echo callbacks,
counters, the exercise loop). Options, for the implementing session's own step (2) to settle:

**Option A — one new `src/` module wraps both.** A class (e.g. `UartLinkExerciser` — bikeshed the
name) that constructs its own `asy_uart_driver.UART` and `UART_Comm` internally given
`tx_pin`/`rx_pin`/`role`/etc., exposes `setup()`/`get_task_starters()`/`get_timer_starters()`/
`get_error_sources()`/`get_loggers()` (delegating most to its inner `UART_Comm`, adding its own
exercise-loop starter only for the initiator role), and a maintenance-status method
(`Transfers`/`Failures`) `@web`-tagged the sgp40 way. This is a single buildgen driver
(`driver = "uart_crossover"` or similar), resolved via `driver_registry._OVERRIDES` (not a
`SensorReader` subclass), with two `[[instance]]` entries distinguished by `role`/`name_ext`. This
is "the crossover UART link module [that] must still be created" the task refers to — BACKLOG.md's
own "Auto-builder" entry already names this exact gap and calls it deliberately unresolved,
recorded as an open design question for "the integration session," i.e. this one:
> "whether the auto-builder's selection model wants the variant entry point to carry the link (as
> it does now), or a separate selectable `uart_crossover` unit... **no file, no code and no
> placeholder** added here for it."
Recommendation: Option A, with the new module owning ALL of the exercise-loop/callback/counter
logic that's currently loose globals in `src/sensortask_dev.py`. This keeps `UART_Comm` itself
untouched (still standalone, still no application semantics — CLAUDE.md's own invariant) while
giving buildgen exactly one thing to construct per instance, matching every other driver's shape.

**Option B — codegen constructs `UART_Comm` directly** (no new wrapping class), with the
banner/echo/counter logic staying as generated inline code in `sensortask_dev.py` (mirroring what
`_notification_lines()` already does for notification's per-signal wiring — bespoke generated
statements, not a reusable class). Cheaper to build but reintroduces exactly the
"code that can't be unit-tested independent of a full generated device" problem the `src/`
promotion process (SPECIFICATION.md Part D) exists to avoid, and duplicates logic if a future
device (or synthetic buildgen-fixture test) ever wants a second crossover pair. Not recommended,
but listed since it's the more minimal option if Option A's `@web`/task-starter integration proves
harder than expected.

Either way: this new/changed code needs to go through the **same `src/` promotion bar** as
everything else (SPECIFICATION.md Part D's checklist — formula correctness, exception-safety,
unit tests, `# @wiring`/`# @web` tags as needed) — it is not exempt just because it's "just test
glue." It is real firmware code that ships in every dev build.

## 5. Digital twin wiring — concretely

1. `buildgen/twin_wiring.py`: extend `compute_twin_wiring()`'s output with the new UART facts
   (tx/rx pins, baudrate, role, and enough to identify the crossover pair — e.g. group by a shared
   `link` name, or simply "the one initiator + the one responder this device declares," matching
   dev's own reality that there is exactly one pair).
2. `digital_twin/machine.py`'s `configure_wiring(plan)`: add a branch that, given the new key,
   constructs two `UART` fakes at the declared pins/baud (mirroring how `_wire_i2c_devices()`/
   `_wire_spi_device()` already do this for i2c/spi) and calls the **already-existing**
   `attach_crossover_jumper()` between them, assigning the returned `LinkPoller`s the same way
   `run_dev_integration.py` does today by hand. Zero new *mechanism* — this is pure wiring.
3. Retire `digital_twin/run_dev_integration.py`'s hand-written `attach_crossover_jumper(...)` call
   (§2) once step 2 makes it redundant — same shift `_LEGACY_WIRING_PLANS`'s removal (commit
   `27bce9c`) already made for I2C/SPI on this branch: hand-wired → generated-JSON-driven.
4. Re-point `tests/test_digital_twin_uart_link.py`/`test_digital_twin_run_dev_integration.py` at
   the buildgen-generated `sensortask_dev` module's real attribute names once those exist.

## 6. Test-coverage obligations (CLAUDE.md's standing bus-hazard rule + "biting" requirement)

CLAUDE.md: "A new bus-facing (I2C/SPI) device gets bus-hazard test coverage across all four test
tiers that apply to it — never forget this." UART is bus-facing in the same sense; `main` already
built the tier structure this rule asks for (`tests/test_uart_comm_hazard.py` for mock,
`tests/test_digital_twin_uart_link.py`/`test_digital_twin_machine_uart.py` for twin,
`tests_hardware/flash/test_uart_crossover.py` + `tests_hardware/device_scripts/uart_*` for real
hardware, `tests_hardware/bench/test_uart_link_under_api_load.py` for the full-stack bench tier).
**The obligation here is porting all four tiers over working, not building them from nothing** —
but confirm each one still actually tests something once the construction path changes, and extend
coverage for whatever buildgen-specific surface is new:
- `tests_scripts/test_buildgen_*.py`-style tests for the new schema: a `test_buildgen_validate.py`
  (or wherever the existing bus/GPIO-collision tests live) needs cases for the new `uart0`/`uart1`
  bus kind — GPIO-role rejection (wrong pin for TX/RX), a bogus `uart2`, missing `tx_pin`/`rx_pin`,
  a `role` value outside `{"initiator","responder"}`, and — the standard "biting" bar this repo
  holds itself to (per the user's own instruction: tests that bite, not merely execute) — a real
  assertion that codegen's `_build_call()` output constructs the objects with the *exact* args
  `dev.toml` declares, not just "it didn't crash."
  - Fixture coverage: extend `tests_scripts/buildgen_fixtures/*.toml` (or add a new synthetic
    fixture) exercising the UART driver the same way `novel_combo.toml`/`multi_instance.toml`
    already do for sensors — per this repo's own standing pattern (`test_buildgen_definitions.py`,
    `test_buildgen_twin_wiring.py`), a synthetic fixture proves generality beyond the one real
    device that happens to use this driver today.
- `tests_scripts/test_buildgen_twin_wiring.py`-style coverage for the new `compute_twin_wiring()`
  key.
- Full local+CI verification exactly like the earlier audit on this branch already established:
  `scripts/lint.sh`, `scripts/typecheck.sh` (all three passes —
  `[tool.mypy]`/`digital_twin/typecheck.ini`/`host_typecheck.ini`), `scripts/test.sh`, and — since
  `dev.toml` is one of the 6 real device TOMLs already covered by CI's device-matrix
  build/twin-e2e/firmware-build-verify stages (see this branch's own recent verification work) —
  confirm `dev`'s own CI legs still pass with the new instances included.
- Real hardware: **do not run anything against real hardware without the project owner's
  go-ahead given directly in that session's own conversation** (CLAUDE.md's standing rule) — the
  flash/bench tiers can be ported and left ready to run, but must not actually be executed against
  the dev bench without asking first, even though `main`'s own commit history shows this exact
  hardware validation was already done once (2026-09-11, on the pre-buildgen code path) and is
  reasonable to expect will need re-confirming against the buildgen-generated firmware.

## 7. Suggested worklist (not a rigid order — the implementing session's own step (3)/(4)/(5) TDD
   pass should drive the real sequencing)

1. Branch off `claude/automated-build-chain-nuzumw` (already done by the orchestrating session —
   confirm you're on the right branch before starting).
2. Merge `origin/main` into the new branch to bring in every file listed in §2 (expect real
   conflicts in `CLAUDE.md`, `BACKLOG.md`, `SPECIFICATION.md`, `.github/workflows/ci.yml`,
   `tests/machine.py`, `digital_twin/machine.py` — both branches independently edited these; the
   `unit-tests-coverage` CI-job-split bullet in particular appears to have landed independently on
   both sides already, so expect near-duplicate content to reconcile, not a clean apply). Resolve
   conflicts by keeping both sides' *distinct* facts; where the same fact was recorded twice,
   prefer the more complete/accurate version and drop the duplicate.
3. Remove/adapt whatever main's merge reintroduces that conflicts with this branch's
   already-established buildgen invariants — most importantly, `main`'s hand-written
   `src/sensortask_dev.py` must not survive the merge as a real file (this branch's whole premise,
   per CLAUDE.md's hard rule, is that no device's `sensortask_<device>.py` is ever committed to
   `src/`) — treat it as reference material to read (via `git show`/the pre-merge commit), then
   delete, not as a file to keep.
4. Datasheet research: build the UART pin-role table for `buildgen/pico_gpio.py` (§3).
5. Design + implement the new `src/` module (§4, Option A recommended) with its own unit tests
   first (TDD, per the step-session workflow) — formula/behavior correctness, exception-safety,
   the full SPECIFICATION.md Part D checklist, before it's ever wired into buildgen.
6. Extend `buildgen/buildspec.py`/`driver_registry.py`/`validate.py`/`pico_gpio.py`/`codegen.py`/
   `twin_wiring.py` per §3/§5, with buildgen-level tests alongside each change (not batched at the
   end) — this repo's own `tests_scripts/test_buildgen_*.py` files are the model to follow.
7. Add the two `[[instance]]` entries (+ bus table(s), if Option A from §3's open question keeps
   the `[bus.*]` shape) to `devices/dev.toml` only.
8. Wire the digital twin per §5; retire `run_dev_integration.py`'s hand-written jumper call.
9. Port every test file from §2's "needs real design work" list, re-pointed at the new module/
   generated attribute names; port the "pure ports" list closer to verbatim.
10. `@web`/`@web-group` tag the new module so `html/definitions/dev.json` regenerates with the two
    `UARTLINK_*` fields (verify via `scripts/build_website.sh`/`buildgen/definitions.py`'s own CLI,
    not by hand-editing the JSON).
11. Full local verification (lint/typecheck/test, all 6 device TOMLs still build+test clean,
    generated `dev` output diffed/sanity-checked) before pushing.
12. Push, open a **draft PR with base branch `claude/automated-build-chain-nuzumw`** (not `main` —
    this branch's own open PR #58 targets `main`; the new branch's PR nests inside that stack), and
    subscribe to its activity per the standing PR-babysitting rules.
13. Report back per CLAUDE.md's step-session workflow step (6) — do not merge, do not start
    unrelated follow-on work, stop and let the owner decide next steps.
14. Delete this planning file once its content is no longer needed as a live reference (either
    folded into BACKLOG.md/the PR description, or simply superseded by the finished code) —
    matching `UART_C_PORT_CHANGELOG.md`'s own stated fate for the same reason.

## 8. Done criteria

- `devices/dev.toml` declares the UART crossover link entirely in TOML (pins, baud, role) — no
  hardcoded pin numbers or protocol parameters left in generated-code templates beyond what
  codegen already treats as per-driver defaults for every other driver.
- Generated `sensortask_dev.py` (via `scripts/_generate_sensortask_modules.py`) constructs the link
  exactly as `main`'s hand-written version did (same pins, same baud, same payload_size/timeout),
  verified by a real test, not just code review.
- Digital twin boots `dev` with a working, generically-wired crossover link — no
  device-name-specific code left in `digital_twin/run_dev_integration.py` for this.
- All four bus-hazard test tiers pass for the new instances (§6).
- `wozi` is completely unaffected — no UART instance, no changed generated output for it.
- `scripts/lint.sh`/`scripts/typecheck.sh`/`scripts/test.sh` all exit 0; all 6 device TOMLs still
  build and test clean via CI's existing matrices.
- `html/definitions/dev.json` regenerates with the two new fields via the `@web` mechanism, not a
  hand-edit.
- No change to `asy_uart_comm.py`'s/`asy_uart_driver.py`'s actual protocol behavior; if one turns
  out to be necessary, it's flagged to the owner rather than made unilaterally, and
  `UART_C_PORT_CHANGELOG.md` gets the entry.
- PR opened against `claude/automated-build-chain-nuzumw`, draft, subscribed, with a description
  that states which of §3's open design questions (bus-table-vs-instance-fields for UART pins;
  Option A vs B for the new module) were chosen and why.
