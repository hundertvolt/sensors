# CLAUDE.md

Operating constraints and architecture reference for AI sessions working in this repo. See
README.md for human-facing orientation, and README.md's "Further reading" section for the
complete map of every other supporting doc in the repo (BACKLOG.md's open-questions/deferred-work
list included) — that section is the single place the list is kept, not duplicated here.

## Datasheets

Full detail (folder contents, the "read the PDF first" rule, what to do when one's missing): see
SPECIFICATION.md Part A.6. Short version: `datasheets/` holds real datasheet PDFs for the chips
this codebase drives — read them first for any hardware-interaction claim, and say so explicitly
if one you need isn't there rather than falling back to web search/training memory.

## Platform target

**The concrete facts** — MicroPython 1.26/RP2040 specifics, what the 1.29 pin changed (Part F.5),
the WDT 8388ms cap, RP2040 hardware specs, the soft-Timer-callback-drop gotcha, the `[x] * n`
segfault range, `Timer.init()`'s `OSError(ENOMEM)` case, the
`MemoryError`-isn't-an-`OSError`-subclass rule, `struct.pack()`'s silent truncation — **live in
`SPECIFICATION.md`'s Part F (Platform Target & MicroPython Runtime Facts).** Read Part F before
any platform-facing code work; don't rely on memory of it, and don't re-derive these from training
memory or general Python knowledge — they were confirmed against real MicroPython source, not
assumed.

Two standing AI-session practices (not facts, kept here since they're instructions, not
information):

- **Always check current MicroPython and Microdot documentation before asserting how an API
  behaves** — do not rely on training-data memory for either. This has already caught real
  discrepancies once; treat it as a standing requirement for every session, not a one-time step.
- **Whenever the pinned MicroPython version changes (and periodically otherwise), re-check every
  MicroPython-facing code construct against the current pinned version's own source, the current
  rp2 port documentation, and MicroPython developer-forum/issue-tracker findings** — not just "is
  this still correct," but specifically "is there now a newer/better/more-complete way to do this
  that a stale construct is missing out on." Examples of the kind of thing this is meant to catch:
  a newly widened set of types accepted by `micropython.const()`, or real `asyncio`-level
  timeout/cancellation support being added to something that previously had none (e.g.
  `socket.getaddrinfo()` — see SPECIFICATION.md Part F.2 for its current
  can't-be-timeout-wrapped status, which is exactly the kind of fact a version bump could change
  and silently invalidate). This is a standing practice, not a one-time pass — repeat it every time
  `toolchain/versions.toml`'s MicroPython `ref` moves. **Last run: 1.28.0 → 1.29.0, 2026-09-10;
  results in SPECIFICATION.md Part F.5** — including what it found (`I2C`/`SPI` `deinit()` are
  no-ops on rp2, a new `OSError(EIO)` raise site on 32+ byte SPI reads) and what it ruled out
  (`extmod/asyncio/` byte-identical between the tags, so `getaddrinfo()`'s status is unchanged).

## Hard rules

- **`improved-quality/` (the refactor's WIP staging directory) has been fully retired and
  deleted.** Every file it ever held was either promoted into `src/` once fully reviewed/tested,
  or — its last remaining file, `sensortask-wozi.py` — confirmed fully superseded by
  `src/sensortask_wozi.py` + `src/asy_webserver_service.py` (construction/wiring and REST routing
  both independently rebuilt there, more generically, with real gaps in the old file fixed along
  the way — e.g. `conn.setup()`/`ntp.setup()` were never called anywhere in the old flow) and
  removed outright, not just left in place. Its old "don't edit source files without a scoped
  owner exception" rule no longer has anything to apply to; the one precedent it set (the
  `ConfigManager`/`LockedValue` wrong-module-import fix) stays as a precedent for any future
  severity-justified exception to a similar "don't touch this WIP/vendored code" rule elsewhere in
  this file (see the `python/CommonDrivers/microdot.py`/`ext/microdot.py` vendoring rule and the
  `modules/_boot.py` rule below), not something that needs a live `improved-quality/` to reapply.
- **`src/` is where files land once they're fully reviewed and tested** — formula/logic
  correctness checked, input validation and exception-safety audited, unit tests written and
  passing (see "Code quality tooling" below and SPECIFICATION.md Part E). **SPECIFICATION.md Part D
  is the full checklist** for what "fully reviewed and tested" actually requires — apply it to
  every file that makes this move, not just whichever ones already have. **For a new sensor driver
  specifically, SPECIFICATION.md Part C is the shared architecture/interface spec** extracted from
  the drivers already in `src/` — what shape the code should take (layering, naming, error
  handling, config schema, ...), separate from Part D's "is it good enough to move" checklist.
  Treat `src/` files as normal, freely-editable code — nothing in this repo is read-only WIP
  context anymore.
- **Whenever a new file is added to `src/`, run a bird's-eye-view scan over the whole
  content of `src/`** — not just the new file in isolation — to check that the coding guidelines
  and `SPECIFICATION.md` Part D's checklist (including its D.10 "API consistency, within a file and
  across the project" and D.9 "Check against current MicroPython" items) actually hold consistently
  across every file there, not just that the new file individually passes review on its own. **This
  scan also covers `SPECIFICATION.md` Part G's shared-primitive catalog and discovery procedure**
  (numeric validation/coercion, callback dispatch guarding, response envelopes, locked state,
  logging, and — for anything website-facing — the `src/`↔`js/` cross-language mirror obligation):
  before writing any new function/module, check Part G's catalog first for an existing primitive to
  reuse or model on, and re-run Part G.3's grep-for-the-shape check across the codebase as part of
  this same scan, not as a separate pass. **If the scan surfaces a discrepancy — one file diverging
  from another, or from a guideline — do not silently fix it.** Report it and discuss how to resolve
  it before changing anything, the same "flag, don't silently change" treatment Part D.1 already
  gives formula/behavior discrepancies, applied here to cross-file consistency instead.
- **Do not "fix" `modules/_boot.py`'s `import sensortask.py`** (literal `.py` in the import
  statement) without testing on real hardware first. It works reliably today; MicroPython's
  documented freeze/import behavior says the module should be named `sensortask` with the
  extension stripped, so this *looks* like it should raise `ModuleNotFoundError` — the mechanism
  is genuinely unresolved (see BACKLOG.md #1). Changing it blind risks breaking every deployed
  unit's autostart.
- **`python/CommonDrivers/microdot.py` is vendored third-party code.** Don't restyle or "clean
  up" it; if you need to change its behavior, treat that as a deliberate fork decision, not
  routine editing. **It is not, however, current** — an earlier note here claimed it matched
  current upstream exactly; re-checked against every upstream tag on 2026-09-10, it's an
  *untagged snapshot between `v2.0.1` and `v2.1.0`* (it carries v2.1.0's `functools.partial`
  dispatch, `max_age is not None`, `.gz` extension handling and the `URLPattern`
  `segments`/`regex` rewrite, but not the rest), leaving it ~441 lines behind the `v2.6.2` that
  `ext/microdot.py` pins. Unmodified relative to that snapshot, as far as can be told — no local
  fork, just old. Bringing the *deployed* tree forward is a reflash-campaign decision, not a
  drive-by edit (BACKLOG.md). **`ext/microdot.py` is the same policy applied to the refactor
  target**: a plain, unmodified vendored copy of upstream Microdot (pinned to tag `v2.6.2` and
  verified byte-identical to it on 2026-09-10), replacing the
  `improved-quality/microdot.py` copy that had drifted into an unintentional fork (removed). No
  edits, no restyling, ever — any behavior change needed is handled by wrapping/calling it from our
  own code (see "Microdot / REST layer" below), never by touching this file. `src/` and `ext/` are
  copied flat into one directory and frozen together for the refactored firmware build, which is why
  they live at the same directory depth in the repo.
- **The UART message protocol (`src/asy_uart_comm.py`, promoted) has a second
  implementation in C on the Arduino peer — so its wire format, accept/reject rules and recovery
  timings are a two-implementation contract, not this repo's to change unilaterally.** The protocol
  itself is specified in SPECIFICATION.md Part J; **every change made to it gets an entry in
  `UART_C_PORT_CHANGELOG.md`** (a temporary file, deleted once the C side is imported and
  reconciled), classified as protocol-level ("must be mirrored in C") or Python-internal ("no C
  impact") — the second class is logged too, so a future session doesn't re-derive it. Prefer a
  protocol-level change that only tightens *receiver* validation over one that alters emitted bytes:
  the former keeps a mixed-version pair working, the latter is a coordinated flag-day needing the
  owner's decision. **The C side's conformance is expected but unverified** — it mirrors the Python
  implementation's intended behavior, but may not share every known flaw and may have its own, so
  every Class A entry must be re-verified against the real C source once it lands. **It is, however,
  prototypical — exactly like this repo's legacy Python — with no device in the field running it**
  (owner, 2026-09-11), so no change recorded in the changelog can break a live pair: both sides are
  reflashed together at reconciliation, and the flag-day framing above describes an obligation to
  record, not a deployment risk to weigh. Real hardware running the C side exists and can be
  connected to the dev board, making the promoted module testable against the genuine second
  implementation rather than only against itself over the bench crossover jumper. **The protocol's
  parameters (`payload_size`, `timeout`, baud) stay fixed by out-of-band agreement** — owner
  decision, 2026-09-11: no version or capability negotiation is to be added, so a mismatched pair
  is diagnosed (it looks like a dead link that nonetheless carries bytes), never negotiated. Two
  further standing facts: the module is **standalone/self-contained** (its BME688/BSEC first use case is out
  of scope and constrains nothing), and it is **strictly initiator/responder, never a symmetric
  peer** — there is no collision arbitration, so simultaneous initiation is out of contract.
  **`dev` carries two instances across its permanent crossover jumper and `wozi` carries none** —
  wozi is never physically flashed, so wiring it there would add an untestable peripheral. The
  protocol's own wire constants and recovery timings live in `src/asy_uart_comm.py` as `const()`
  values; a change to any of them is Class A by definition.
- **`dev` config is a bench rig only** — its quirks (e.g. LED/Neopixel REST routes referencing an
  object that's never instantiated) are explicitly out of scope. Don't fix them as if they were
  bugs.
- **WoZi is the exemplary/base variant the whole `src/` promotion is built and validated against —
  it is never physically flashed or bench-tested; only the dev board is, and only ever will be.**
  WoZi's own correctness is established entirely through the mock/twin/unit-test suite (`tests/`),
  which stays the source of truth for it and is unaffected by any real-hardware work. The dev bench
  exists solely to physically validate the underlying shared mechanisms (I2C/SPI/WiFi/webserver/
  etc.) that wozi's own code also uses — **a passing dev-bench result is treated as valid for wozi
  too**, provided the code actually under test is genuinely dev-native (dev's own correct pins/
  config via its own entry point), never wozi's own hardcoded build forced onto dev hardware. That
  specific mismatch (`scripts/build_firmware.py wozi` — wozi's hardcoded pins — flashed onto the dev
  bench) produced two false "bugs" once (see BACKLOG.md's "Per-variant `sensortask-*.py` generator" entry) — it
  isn't a shortcut for testing wozi, it's testing nothing at all, and must not be repeated.
- **The legacy tree is reference-only, forever — it never gets work of any kind** (project owner,
  2026-09-11). `python/`, `modules/` and the four `build-*.sh` scripts exist to be *read*: to check
  what the deployed system actually does, and how a driver behaved in the field. Nothing in this
  repo's quality apparatus is ever extended to them — no lint/typecheck scope, no CI build stage,
  no shellcheck cleanup, no tests, no refactor. A finding *about* legacy code is worth recording
  only when it explains current behavior; it is never a to-do. Don't propose closing any of these
  gaps — the gap is the decision. `modules/_boot.py`'s `import sensortask.py` (above) is this same
  rule applied to one specific file, not an exception to it.
  **On tests specifically**, since that half predates the rest: the agreed plan is to understand
  the current system first, confirm what is already promoted into `src/`, and write tests as part
  of that refactor. This does **not** contradict SPECIFICATION.md Part E's testing requirements —
  those describe what the *refactored* code must eventually have, and `src/math_helpers.py` +
  `tests/test_math_helpers.py` were the first instance of exactly that. The rule is "never test
  the old `python/`/`modules/` code", not "defer all tests".
- **Don't touch `sensors/config.json`-equivalent files or commit any real credentials.** A
  `.gitignore` covers per-device config/build artifacts, but still be deliberate about what you
  stage. **The one known real credential already in this repo**: a hardcoded hotspot fallback
  password, present in both `python/CommonDrivers/async_connect.py` (deployed, pre-refactor) and
  `src/asy_wifi_service.py` (promoted) — accepted risk (only exploitable by someone in physical
  WiFi range of a unit that's already lost its real WiFi), not something to "fix" by
  rotating/removing without the project owner's direction. `improved-quality/async_connect.py`
  itself was removed once its functionality was fully promoted to `src/asy_wifi_service.py`/
  `asy_ntp_client.py`/`asy_dns_client.py` — no import in the repo referenced it anymore.
- **For a genuinely wedged I2C bus/sensor, the hardware watchdog is the accepted backstop, not a
  software fix to chase** — settled, don't re-propose an I2C-level timeout mechanism; full
  reasoning (including why `socket.getaddrinfo()` belongs in this same bucket, and which calls
  genuinely *can* be timeout-wrapped) is in SPECIFICATION.md Part F.2.
- **The same backstop applies to a WiFi link stuck in a CYW43-firmware-level `isconnected()` false
  positive — a power cycle/`hard_reset()` is a deliberately stable, intended recovery feature, not
  a fallback to fix away.** Confirmed inherently safe: every real flash write is reachable only
  through the REST PUT path, so a device whose API is unreachable structurally cannot have a write
  in flight. Settled, don't propose an independent reachability-probe mechanism; full reasoning and
  real bench-hardware timing data are in SPECIFICATION.md Part F.2 (BACKLOG.md keeps only a closed
  pointer, open question 6).
- **Don't wrap every `asyncio` primitive call in `try`/`except` against a theoretical internal
  `MemoryError` as a blanket policy** — see SPECIFICATION.md Part F.2 for the full rule and its
  narrow exception.
- **Adafruit-derived driver code is fair game to restructure/rewrite** (keeping attribution) —
  unlike `python/CommonDrivers/microdot.py`/`ext/microdot.py`, which stay hands-off/vendored (see
  above). Full note: SPECIFICATION.md Part F.4.
- **Long-blocking operations must not stall timing-sensitive work** — standing design principle
  for all new code; full reasoning (including the retired `get_long_block_lock()` mechanism) is in
  SPECIFICATION.md Part F.3.
- **`asy_uart_driver.py` and `asy_uart_comm.py` may never block the asyncio loop — not even in a
  wait state.** They may time out and handle it; they may not wait synchronously (project owner,
  2026-09-11). This is sharper than F.3's general principle and is easy to violate by accident:
  `machine.UART.read()/readinto()` wait out `timeout_char` for every byte asked for that has not
  arrived yet, inside `mp_event_handle_nowait()`, which never yields — so a plain "read the whole
  frame after `POLLIN`" holds the loop for the frame's entire wire time (measured: 4.4ms per
  53-byte frame at 115200 baud). The fix needs **both** a clamp to `uart.any()` and a real yield
  between rounds; the clamp alone is *worse*, because `ready()` returns `True` with no `await` and
  the block simply moves into a Python loop. Full account and the measured before/after:
  SPECIFICATION.md Part F.5.8 — which also states why this must **not** be generalised to
  `asy_i2c_driver.py`/`asy_spi_driver.py`, whose peripherals expose no partial-read API to clamp to
  (that case stays F.2's watchdog backstop).
- **A new bus-facing (I2C/SPI) device gets bus-hazard test coverage across all four test tiers that
  apply to it — never forget this** (project owner's explicit, standing direction): same-device
  read-vs-write concurrency, cross-device interleaving if it shares a bus in either variant, and an
  address/command sweep, in `tests/test_bus_hazard_multi_device.py` (mock), `tests/
  test_digital_twin_bus_hazard_concurrency.py` (digital twin), `tests_hardware/flash/
  test_bus_concurrency.py` + `tests_hardware/bus_topology.py` (real hardware, dev bench), and
  `tests_hardware/bench/test_bus_concurrency_under_api_load.py` (real hardware, full HTTP stack).
  Full checklist, plus the two real-hardware write-safety constraints any new device's own on-chip
  NVM or the RP2040's own flash filesystem must respect: SPECIFICATION.md Part C.8's own standing
  rule, right after its general-call hazard finding.
- **A session needs the project owner's go-ahead, given directly in that session's own
  conversation, before running anything against real hardware** (any `mpremote` command, `nmcli`/
  `iw`/`iptables` call, `picotool`, or `tests_hardware/`'s own suite runners) — a go-ahead given to
  a different session, or to an earlier session that already ended, does not carry over; if there's
  any doubt whether the current conversation actually has it, ask first rather than assume. Once
  granted, it covers the rest of that same conversation — real-hardware work spanning multiple
  turns doesn't need to be re-confirmed turn by turn. `tests_hardware/README.md` is the durable
  technical reference (prerequisites, environment variables, safety facts like the
  `--allow-flash-cycle`/long-soak opt-in gates and the hotspot role-reversal scenario's stage-6
  permanent-WLAN-deactivation risk) for what a session with that go-ahead actually needs to know —
  this rule is just the standing gate for whether to start at all.
- **A destructive test of the bench host's own network/access config (tearing down `br0`/its
  slaves, revoking `dialout`, anything that can cut the very connection a session is using to reach
  the host) must keep a recovery dead-man's-switch continuously armed for the entire risk window —
  never touch live network state with none armed.** Confirmed the hard way (2026-09-04): a one-shot
  timer consumed by an earlier dry run gave zero protection to the real run that followed, costing
  the bench Pi4's own SSH access. Full incident account, the recovery script, and the validated
  arm/verify/disarm pattern: SPECIFICATION.md Part B.13.
- **The bench Pi4's `br0` bridge must always present `eth0`'s own real hardware MAC, never a
  NetworkManager-synthesized one — pin it via `bridge.mac-address`, always, on every bridge
  creation.** A synthesized bridge MAC can drift across the bridge's own lifetime, silently
  orphaning the router's static DHCP reservation. Full incident account and the fix (both in
  `ensure_bench_bridge()` and `dev_legacy/README.md`'s manual recipe): SPECIFICATION.md Part B.13.
- **Memory-safety discipline: catch→degrade→restart→watchdog, `gc`-default-first, always applied —
  not only once something has already broken.** Any new function/module that holds, builds, or grows
  an allocation whose size isn't a small, provably-fixed constant follows the same standing ladder
  every existing module already mostly follows: catch `(OSError, MemoryError)` and degrade locally
  where a concrete risk exists; never let that bubble into an unguarded crash of an otherwise-healthy
  request/task; trust `system_service.py`'s task supervisor to restart a task that still dies (already
  confirmed to catch `MemoryError` too — it's a direct `Exception` subclass, not nested under
  `OSError`); let the hardware watchdog be the final backstop once restarts alone aren't keeping up.
  Any new stress/hammer test for such code must pass with `gc.threshold(-1)` (MicroPython's own real
  default) *before* it's ever run with the project's chosen `gc.threshold(32768)` — a threshold is
  defense in depth on top of an already-safe design, never the fix for a design that still needs one
  big contiguous allocation somewhere. A REST GET route whose response dict can grow with device
  configuration/registration count (not a small, fixed handful of keys) streams it via
  `asy_webserver_service.py`'s `_stream_dict_response()` instead of returning the dict directly for
  Microdot to `json.dumps()` in one shot. Full research findings, the complete hotspot catalog (what
  needed fixing vs. what was reviewed and found already safe), and the full scheme: SPECIFICATION.md
  Part I.
- **When investigating any unexpected real-hardware error or reset — read the FRAM-persisted
  per-module error logs (`GET /status`'s `errcount`, the FRAM-backed subset: SGP40/BMP3XX/SCD30/
  SYSTEM/NEOPIXEL/NOTIFY per SPECIFICATION.md Part A.7's seven-chunk layout; WIFI/NTP/every
  `CFGMGR_*` logger are RAM-only and don't survive a reboot) BEFORE issuing any `PUT /status
  {"ResetErrors": true}` call or otherwise clearing state.** This is the one piece of real
  diagnostic evidence a reboot itself doesn't erase, and clearing it is irreversible — confirmed the
  hard way (2026-09-08): a single real `WDT_RESET` was investigated down to "GC ruled out, cause
  otherwise undetermined" and closed as a singular, not-systematically-reproducible event without
  ever checking whether a FRAM-backed module had logged something right before it — by the time
  this was thought of, ordinary bench cleanup (`ResetErrors`, run several times since as routine
  hygiene) had already overwritten every FRAM-backed log's history, permanently losing whatever
  evidence might have existed. The same check applies inside the digital twin
  (`digital_twin/_fram_chip.py` models the same chunked FRAM layout) — check before clearing there
  too, not just on real hardware. **One caveat, found the hard way (2026-09-11): this rule assumes
  a board that has been running normally.** An isolated-driver device script builds its own
  `AsyFramManager` over the same chip, and the allocator is deterministic, so its first chunk *is*
  production's first chunk — a flash/bench-tier run overwrites the real error logs, and a script
  leaving a well-formed chunk behind fabricates a plausible-looking one (a seeded `errno=5` read
  back as SYSTEM's `"Task N ended with exception"`, chased down as if real). Before treating a
  FRAM-backed log as evidence, check what has been run against that board;
  `tests_hardware/README.md` has the full mechanism.

## Working agreements

- Long-term goal: fully understand the current (production) system in detail, then check what's
  already been addressed/promoted well into `src/`. The refactor should end up
  with the *same top-level features*, just more consistent/stable — not a feature change.
- When a fact in this file or BACKLOG.md turns out to be stale (version drift, changed upstream
  API, etc.), update the doc in the same session rather than silently working around the
  discrepancy.
- **Documentation contains current state, future targets, and rules/agreements — not the historic
  path that got there.** BACKLOG.md is active working memory (open questions, deferred work,
  in-flux decisions), not an append-only log of bugs found and fixed in already-shipped, tested
  code; once an item is resolved, it comes out, migrated to CLAUDE.md/README.md if it's a
  permanent fact worth keeping, or simply dropped if it was process narrative with no forward
  value. This already had to be corrected once (a merge re-accumulated ~800 lines of per-file
  "bug found, fixed" narrative in BACKLOG.md) — treat pruning history back out as routine
  maintenance whenever an item resolves, not a one-off cleanup.
- **Every module gets exactly one header comment block — module/function/class `"""..."""`
  docstrings in Python, the equivalent leading `/** ... */`/`//` block in JS — capped at 3 lines,
  prefer fewer: a concise header, not an essay. This applies to all code in the repo, not just
  Python — `js/`, `tests_js/`, `html/style.css`, `digital_twin/`, everything.** Inline comments
  (`#` in Python, `//`/inline `/** */` in JS) have no hard numeric cap, but stay disciplined: a few
  short, genuinely load-bearing WHY notes next to the line they explain, never a multi-paragraph
  block of narrative reasoning. Load-bearing detail that doesn't fit that bar moves to: the
  relevant `SPECIFICATION.md` Part if the fact is architectural and reused elsewhere (leave a short
  pointer in the header block, the same "Moved to `SPECIFICATION.md` Part X" pattern this file
  itself already uses — website-facing facts go to Part H specifically),
  `digital_twin/README.md` for anything `digital_twin/`-specific, or a
  short comment right next to the code it explains otherwise — never dropped outright. Applied
  repo-wide across `src/`, `digital_twin/`, `tests/`, `js/`, `tests_js/` in one pass (project
  owner's direction); keep new code to this bar too.
- Prefer flagging genuinely ambiguous/architecturally significant decisions to the project owner
  over guessing — several open questions in BACKLOG.md exist precisely because the code's actual
  intent wasn't obvious from reading it alone.
- When changing a sensor driver's behavior, verify against the legacy driver's own actually-proven
  field behavior, not just judged correct against internal code-review logic in isolation.
- **Step-session workflow, standing practice for any substantial unit of refactor/audit work**
  (originated during the `improved-quality/` → `src/` wiring effort's five-plus-one step sessions,
  still the expected shape for a comparable future unit of work — a new driver promotion, a new
  audit pass, etc.): (1) refine the task's own scope into a detailed list — goals, doc links, and
  the criteria that make the branch/session done — doing real research first (datasheets, current
  MicroPython/Microdot docs, legacy driver code) rather than restating a one-line ask; (2) ask up to
  10 top-level clarifying questions (what needs deciding, the realistic options, the consequences of
  each), resolving as much as possible from project context/internal docs/legacy code first, but
  raising a genuinely blocking or architecturally significant decision at any point, not only in
  this round; (3) write the full set of unit tests first (TDD) against the criteria the refined
  scope settled on; (4) write the implementation against those tests, refining until every test
  passes and the result is lean, not just "technically satisfies the tests"; (5) add unit tests for
  the resulting functional code, maximizing coverage; (6) stop and report back to the project owner
  before doing anything more — merging, starting the next unit of work, or any scope beyond what was
  just built is not the session's own call. A session can come back with a blocking question at any
  point in this sequence, not only at the end.

## Code quality tooling

- **Config lives in root `pyproject.toml`** (ruff/mypy/pytest/uv, dev-tooling only — the shipped
  code stays frozen-bytecode-only, not restructured into an installable package). Run manually via
  `scripts/lint.sh` (ruff + shellcheck + actionlint + zizmor), `scripts/typecheck.sh` (mypy), and
  `scripts/test.sh` (unit tests, under a real MicroPython Unix-port interpreter — see below and
  SPECIFICATION.md Part E); `lint.sh`/`typecheck.sh` assume those tools are already on `PATH` (e.g.
  an activated `uv sync`-created venv). **Every tool is a `[dependency-groups] dev` entry, so
  `uv sync` — and therefore `toolchain/setup_toolchain.py env --tier {generic,flash,bench}`, which
  runs it — installs all of them automatically; nothing is installed by hand.** All are **pinned**,
  for the same reason ruff is: `select = ["ALL"]`-style opt-in-to-everything configs turn an
  unpinned upgrade into a hard CI failure on a rule nobody chose.
- **Wired into CI** via `.github/workflows/ci.yml` (GitHub Actions). **Each tool is its own job/
  stage**, so a failure names the tool directly instead of a shared "lint" job going red:
  `lint-and-typecheck` (ruff + mypy), `shellcheck`, `actionlint`, `zizmor`, plus the test/build
  stages (`unit-tests`, `digital-twin-e2e`, `firmware-build-verify`) and the web tier. Note
  `unit-tests` keeps `needs: lint-and-typecheck` (the standing hang backstop below); the other lint
  stages run in parallel and gate nothing, so one of them failing no longer silently skips the
  whole test suite.
- **`zizmor` audits the GitHub Actions workflows themselves** — `GITHUB_TOKEN` scope, checkout
  credential persistence, action pinning: the one part of the supply chain ruff/mypy can't see.
  Policy config is `.github/zizmor.yml` (only `unpinned-uses` is configured — `actions/*` may be
  tag-pinned, everything third-party must be SHA-pinned; every other audit runs at its default).
  Always invoked `--offline`, which skips the two audits needing the GitHub API, so it behaves
  identically in CI, on a dev box, and in the clean-chroot recipe below. **`self-repository` is
  deliberately `disable: true`** — it wants `uses: $/.github/...` (GitHub's July-2026 syntax) and
  actionlint 1.7.12 rejects that as invalid, so the two gates cannot both be satisfied; revisit
  when actionlint learns it. **Adding a SHA-pinned third-party action means bumping that SHA by
  hand** — no Dependabot is configured.
- **Scope is eight directories**: `src/`, `tests/`, `digital_twin/`, `boot_entry/`, `toolchain/`,
  `scripts/`, `tests_scripts/` and `tests_hardware/`. The pre-refactor deployed
  codebase (`python/`, `modules/`) has no lint/type config yet; extending scope there is a separate
  future decision, not assumed by this setup. All eight are expected to stay fully clean — every
  scope in this setup is fully-reviewed, freely-editable code (see "Hard rules" above), not WIP;
  there's no tracked-debt scope left to compare `digital_twin/` against since `improved-quality/`
  was deleted (see "Hard rules" above). `digital_twin/`'s own
  type-check is a **separate** mypy invocation (`digital_twin/typecheck.ini`, run unconditionally by
  `scripts/typecheck.sh` regardless of its own args) rather than folded into the main
  `[tool.mypy]` pass — mypy resolves each bare `machine`/`network`/`neopixel` module name to exactly
  one file per run, so this package's own hardware fakes and the real `typings/` board stubs can
  never both be checked correctly in one invocation. `digital_twin/machine.py`/`network.py`/
  `neopixel.py` (a straight `Duplicate module named "machine"` collision with `tests/machine.py`
  otherwise — confirmed directly, not the softer resolution-priority hijack `tests/network.py`'s own
  exclude guards against) and `digital_twin/launch.py`/`run_wozi_integration.py`/`run_dev_integration.py`/
  `segfault_stress_repro.py`/every `tests/test_digital_twin_*.py` (attr-
  defined noise on every twin-only API the real board stub doesn't declare, e.g.
  `WDT.would_have_triggered_count`, `WLAN.script_connect_outcomes()` — confirmed directly, including
  one real `mypy src tests`-only finding this design caught that a from-scratch `mypy` run missed)
  are therefore excluded from the main `[tool.mypy]` pass and checked correctly by the dedicated
  pass instead — see `pyproject.toml`'s own `[tool.mypy]` exclude comment and
  `digital_twin/typecheck.ini`'s own docstring for the full account.
- **Unit tests run under a real MicroPython Unix-port interpreter, not pytest/CPython** — "as close
  to the real environment as possible" means the actual runtime, not CPython plus MicroPython-
  flavored stubs — see SPECIFICATION.md Part E.1 ("Why not pytest"). `scripts/test.sh` builds that
  interpreter on first run (`toolchain/setup_toolchain.py`'s `setup` — building/verifying the
  Unix port is just part of what `setup`/`test` already do, there's no separate `unix`
  subcommand — cached under `$PICO_TOOLCHAIN_DIR`) and shells out to it once per `tests/test_*.py`
  file; see SPECIFICATION.md Part E.3 for the full rationale and the minimal `test_*`-function runner
  (`tests/microtest.py`) used in place of CPython's `unittest`. This is specifically about `src/`'s
  own MicroPython-target code — `tests_scripts/` (pytest, real CPython) covers the host-only build
  tooling instead (`scripts/build_frozen_html.sh`, `scripts/build_website.sh`, `scripts/
  build_firmware.py`), none of which are MicroPython-target code, so the real-interpreter rationale
  above doesn't apply to them; see `tests_scripts/conftest.py`'s own docstring. `scripts/test.sh`
  runs both: the MicroPython suite as described above, plus `uv run pytest tests_scripts` as one
  more step before it. `tests_scripts/` is in lint/typecheck scope, like
  `scripts/`/`toolchain/` (the dev-tooling scripts these tests exercise) — all three are checked by
  `host_typecheck.ini`'s real-CPython pass, not the MicroPython one, and carry the same
  `per-file-ignores` block `tests/` does.
- **`scripts/test.sh --coverage` reports `src/` line coverage; it never gates anything** — no
  threshold is enforced anywhere, by design (confirmed directly, not a placeholder for a future
  gate). Since `coverage.py` only runs under CPython while `src/` only ever runs
  under the real MicroPython Unix-port interpreter, collection (`tests/_coverage_runner.py`,
  `sys.settrace` inside MicroPython) and rendering (`scripts/_render_coverage.py`, a second
  self-contained `uv run` script, under CPython) are two separate stages glued together through
  `coverage.py`'s own `CoverageData` API — see SPECIFICATION.md Part E.5 ("Coverage") for the full
  pipeline. The Unix port binary is always built with `MICROPY_PY_SYS_SETTRACE=1`
  (`build_unix_port()` in `toolchain/setup_toolchain.py`) — an inert hook check when unused, not a
  behavior change, confirmed directly — so plain `scripts/test.sh` and `--coverage` share one
  binary; `ports/rp2`'s firmware build never gets this flag. CI
  (`.github/workflows/ci.yml`) runs it as a non-gating step: a markdown summary goes to that run's
  GitHub Actions Job Summary (not the repo's main page), the HTML report is a downloadable build
  artifact (GitHub doesn't render it inline), and the Cobertura XML uploads to Codecov — which
  needs this repo registered at codecov.io plus a token/OIDC setup that hasn't happened yet, so
  that upload currently no-ops. Locally, `--coverage` only prints the output paths; nothing opens
  automatically. See README.md's "Test coverage" section for the full user-facing rundown.
- **Standing backstop: hanging tests are never allowed.** `scripts/test.sh`/`ci.yml` enforce a
  per-file `timeout`+retry, `stdbuf -oL -eL` line buffering, and `needs: lint-and-typecheck` job
  sequencing regardless of any specific hang's root cause — keep all three even after a specific
  hang is fixed. **The `needs:` edge is for SEQUENCING only — `unit-tests` and
  `firmware-build-verify` carry `if: ${{ !cancelled() }}` so they still run when the job they
  follow fails.** `needs:` alone also implies success-gating, which was never chosen here (that
  job's own comment says the sequencing "isn't required" for the hang) and is actively harmful: a
  red `lint-and-typecheck` silently SKIPS every Python test lane. That is not hypothetical — it is
  why `unit-tests`, `digital-twin-e2e` and `firmware-build-verify` had never once run on the branch
  that introduced `select = ["ALL"]`, and it concealed that for the branch's whole life. Keep the
  sequencing; never restore the gating. `digital-twin-e2e` is the deliberate exception — its
  `needs: unit-tests` comment states fail-fast as the actual intent, so it stays gated.
- **Known hang cause, fixed**: a MicroPython Unix-port `select.poll()`/`ioctl()` call against a
  non-fd Python object (e.g. `tests/machine.py`'s pure-Python fake-stream `ioctl()`) never detects
  readiness on GitHub Actions runners specifically (not reproducible locally) — any test awaiting a
  stream read/write with `timeout_ms=-1` through that real-poll path hangs forever.
  `test_asy_uart_driver.py` hit this via `asy_uart_driver.py`'s `ready()`'s `timeout_ms=-1` branch;
  fixed by switching every such test to the bounded `_StepPoller` test double already used
  elsewhere in that file. **Rule: any test double for `uart.poller` (or an equivalent fake-stream
  object) must be a bounded fake like `_StepPoller`, never backed by a real `select.poll()`.** Don't
  re-diagnose this specific symptom as a new code bug if it recurs elsewhere.
- **Known hang cause #2, fixed**: a digital-twin integration test that drives the real
  `sensortask_wozi.build_system()`/`start_and_check_tasks()` task graph to a clean, non-cancelled
  completion (e.g. a bounded `--soak` run finishing normally, not via timeout) leaves its ~18
  independently-`create_task()`-spawned sibling tasks (WiFi, sensor readers, the webserver, ...)
  parked in the shared, process-wide asyncio task queue after the test's own coroutine returns —
  `Task.cancel()` on the one task a test explicitly awaits (`main_task` in
  `digital_twin/run_wozi_integration.py`) never cascades to those siblings, since MicroPython's
  asyncio has no parent/child task tracking. `tests/test_*.py` files run one Unix-port process per
  file (see `scripts/test.sh`'s own comment) sharing one process-wide task queue across every test
  function in that file, so this only ever surfaced as the *whole process* hanging at exit after the
  last test's own "N/N passed" line printed — not a per-test symptom, and easy to mistake for an
  unrelated infra issue. Fixed in `tests/microtest.py`: `run()` now always calls `sys.exit()`
  (0 on an all-pass run, 1 on any failure) instead of only exiting on failure — this forces the
  process down immediately regardless of what's still parked in the task/IO queue, rather than
  relying on the interpreter's own idle-detection ever reaching zero pending tasks. This is exactly
  the same "explicit tracked-task-list + cancel-all in `finally`" shape `digital_twin/launch.py`'s
  own `main()` already used for its own (much smaller, self-spawned) task list — the one difference
  is `run_wozi_integration.py` drives the real, much larger `system_service.py`-supervised task
  graph, which isn't reachable/trackable from outside that module, making a blanket forced-exit the
  more robust fix than trying to enumerate and cancel every sibling task individually. Surfaced by
  the `system_service.py` `_timer_sequencer()` Timer-GC fix above: before that fix, `start_timers()`
  hung forever, so `start_and_check_tasks()` never even got called and no sibling tasks ever
  existed to leak — the soak test's own bounded-completion path was previously unreachable.
- **Known segfault cause, fixed**: a **nested `asyncio.run()` while any other task is still parked
  in the shared task queue segfaults the MicroPython Unix port** - it does not raise the
  `RuntimeError: asyncio.run() cannot be called from a running event loop` CPython would. `run()`
  installs a fresh event loop and task queue; the outer loop's already-queued tasks then belong to
  the replaced queue, and resuming the outer loop walks freed pointers. Reduced to a 12-line
  reproducer (`create_task()` a parked sleeper, then `asyncio.run()` inside the running coroutine),
  and **not** load-, heap-size- or timing-dependent: it is deterministic and uncatchable, so
  `microtest.py`'s own `except Exception` never sees it and the file simply dies mid-run with no
  summary line. **Rule: a test helper that calls `asyncio.run()` (this repo's `run()` wrappers in
  `tests/_uart_comm_harness.py` and friends, and anything calling `hazard_pair()`/`build_pair()`
  style builders that run their own setup) must only ever be called from synchronous test-function
  scope, never from inside a coroutine** - build the fixture at the top of the test, then pass it
  into the one coroutine `run()` drives. Audited across `tests/`, `digital_twin/` and `src/`: no
  other call site does this. Don't re-diagnose a test file that segfaults partway through with no
  `N/N passed` line as a memory bug in the code under test.
- **Known intermittent-`MemoryError` cause #2, fixed**: a real SIGINT landing inside a
  `gc_collect()` leaves the MicroPython Unix port's heap **permanently locked** — the stuck
  `GC_COLLECT_FLAG` makes every later allocation fail with `MemoryError: memory allocation failed,
  heap is locked`, on a heap that is mostly free. Measured at ~5% of interrupts on Unix ports built
  from both `v1.28.0` and `v1.29.0`, so **not** a version-bump regression; it surfaced as one failed
  `Run 4: clean shutdown (exit code 1)` in `scripts/run_digital_twin_ci.sh`. Fixed by
  `digital_twin/unix_port_gc_unwedge.py`, called first in both twin runners'
  `except KeyboardInterrupt:` handlers. **The recovery is `gc.collect()`, not
  `micropython.heap_unlock()`** — the two lock states need opposite recoveries and the obvious one
  is wrong here. Full mechanism and evidence: SPECIFICATION.md Part F.6. Don't re-diagnose a
  "heap is locked" `MemoryError` at twin shutdown as a project memory bug.
- **Known intermittent-`MemoryError` cause, fixed**: `scripts/test.sh` runs every `tests/test_*.py`
  file as one Unix-port process for all its test functions, sharing one heap — a file whose several
  heaviest tests each build the whole real `sensortask_wozi.build_system()` object graph (one test
  builds it twice) could exhaust the interpreter's 2MB default heap roughly 1 run in 3, depending on
  MicroPython's own non-deterministic test-function run order. Fixed with `-X heapsize=8M` (verified
  10/10 clean runs) — a Unix-port-only test-harness setting, unrelated to the real rp2040's own RAM
  budget. Don't re-diagnose a flaky `MemoryError` in a heavy test file as a new code bug before
  checking this flag is still in place.
- **Local test runs pin `$TZ=UTC` (Unix port only).** The Unix port's `time.mktime()`
  (`ports/unix/modtime.c`) calls the host's real libc `mktime()`, which interprets its input as
  **local time** per the process's `$TZ` — unlike the deployed rp2 firmware, whose
  `ports/rp2/datetime_patch.c` overrides this with `shared/timeutils`' pure, TZ-agnostic epoch
  arithmetic. `src/`'s `time.mktime(time.gmtime())` "current UTC timestamp" idiom is therefore only
  a true no-op round trip under `TZ=UTC`; not a production bug — real hardware has no `$TZ` concept.
  `scripts/test.sh` exports `TZ=UTC` before invoking the Unix-port binary for exactly this reason.
  Don't diagnose a consistent (not intermittent) failure in a live-clock assertion as a new code bug
  before checking the runner's `$TZ`.
- **`ruff format` is deliberately not used anywhere** — line breaks are hand-chosen throughout this
  codebase; `line-length = 320` (ruff's own ceiling) plus an `E501` ignore keep this a non-issue even
  if `format` is ever run by accident. Lint rule selection (`E`/`F`/`W`/`I`/`UP`/`B`) is stricter
  than ruff's default but well short of enabling everything.
- **Bare `except:` (E722) is intentionally left enabled**, unlike the old `improved-quality/pycheck.sh`
  — the project owner wants ruff to flag existing bare excepts as a tracked to-do, not silence them
  before they're fixed (test-driven-development framing, confirmed directly).
- **Union type annotations: always PEP 604 `X | Y` (and `X | None`), never `typing.Union[...]`.**
  Confirmed safe at runtime on both the deployed 1.26 pin and the refactor's 1.29.0 target by
  testing directly against the pinned Unix-port interpreter (`int | None` in an unquoted, executed
  annotation works with no import needed) — MicroPython parses but never evaluates annotation
  expressions at all, so this isn't even a runtime-support question, just a style one. `typing.Union`
  needs `from typing import Union`, which isn't guarded by `TYPE_CHECKING` in every file that still
  uses it and would raise `ImportError` on-device if actually reached at runtime — one more reason
  `|` is strictly better here, not just newer. This is already machine-enforced: ruff's `UP007` rule
  (part of the enabled `UP` selection) flags every `Union[...]` as a finding. `src/` and `tests/`
  are already 100% `|`-style with zero `Union[...]` occurrences. The
  `Union[...]` usages that do exist today are confined to `python/` (deployed, frozen, no lint
  config at all) — leave those alone under the usual out-of-scope-editing hard rule; don't drive-by
  "fix" `Union` → `|` in a file you're not otherwise promoting/refactoring.
- **mypy runs full `--strict`, minus exactly one flag.** All three configs set `strict = true`
  (spelled that way, not as the individual flags, so a deliberate mypy version bump surfaces any
  newly added strict check as a finding to decide on), plus `no_implicit_optional`/`warn_unreachable`
  which aren't part of `--strict`. **The one exemption is `no_implicit_reexport`, and only in the
  `[tool.mypy]` pass** — `tests/` mocks by reassigning a module's imported names
  (`asy_ntp_client.time = FakeTime()`, `asy_udp_socket.socket = ...`), which is the project's actual
  mocking mechanism since MicroPython has no `unittest.mock`; enforcing the flag would mean 175
  inline ignores in `tests/` or adding `__all__`/re-export aliases to shipped `src/` modules purely
  to satisfy a test-only check. `digital_twin/typecheck.ini` and `host_typecheck.ini` both run
  `--strict` with that flag ON. One further narrow exemption lives in a central
  `[[tool.mypy.overrides]]` block: `disallow_untyped_decorators` is off for
  `tests/test_setter_microdot_integration.py`, the only file that registers real Microdot routes —
  vendored `ext/microdot.py` is unannotated and must never be edited, so its `@app.get()`/`@app.put()`
  decorators make every handler they wrap "untyped" no matter how well the handler itself is
  annotated. Does **not** disable the `assignment` error code — the old `improved-quality/mypy.ini`
  did, though that was never a deliberate choice.
- **`method-assign` stays globally enabled, and `src/` must never suppress it** (project owner's
  direction). `tests/` and `digital_twin/` reassign methods to mock them — that IS the project's
  mocking mechanism, MicroPython having no `unittest.mock` — and each of those ~157 sites carries
  its own inline `# type: ignore[method-assign]` rather than a central `[[tool.mypy.overrides]]`
  exemption, deliberately: a scope-wide override would stop marking the individual real sites.
  Shipped firmware code has no business reassigning a method at all, so a suppression appearing in
  `src/` is the defect, not the type error. mypy itself cannot express that rule (it only ever sees
  a suppression already written), so `scripts/lint.sh` enforces it with a grep guard that fails the
  lint gate. `src/` carries zero of these today; keep it that way rather than silencing a finding.
- **`# noqa: E402` belongs only on files with a real statement before their imports.** Several
  `tests/` files must set `sys.path` before importing the module under test, and ruff **exempts
  `sys.path` manipulation from E402 outright** (verified directly, 2026-09-10) — so those files
  need no suppression. What does trigger it is any *other* statement first, e.g.
  `test_digital_twin_sensortask_integration.py`'s `patch_asy_udp_socket_for_unix_port()` call, and
  only those files carry the `# noqa`. This is not an inconsistency to tidy up: adding the
  suppression to a `sys.path`-only file makes `RUF100` (unused-noqa, live via `select = ["ALL"]`)
  fail the lint gate, so the two groups genuinely have to differ.
- **A merge that touches `uv.lock` can silently bypass the tool pins — always re-verify after
  one.** `uv.lock` is a plain text file, so git merges it line by line: a branch that pins the
  tools and a branch that only refreshes versions produce a lock carrying **one side's
  `specifier = "=="` metadata and the other side's resolved `[[package]] version` blocks**. That
  file is self-contradictory, and neither guard catches it — `uv lock --check` compares
  `pyproject.toml` against the lock's *manifest* section only, never the manifest against the
  *resolved* versions, so it exits 0; and `uv sync` installs from the resolved blocks, so the venv
  silently gets a version the pin forbids. Confirmed directly here (2026-09-10): merging main's
  external-module refresh produced a lock reading `ruff specifier = "==0.15.21"` next to
  `ruff version = "0.16.6"`, `uv lock --check` passed, and `uv sync` installed 0.16.6 — under
  `select = ["ALL"]` that is exactly the unchosen-rule hard-fail the pin exists to prevent (it
  surfaced 174 `CPY001` findings). **After any merge that touches `uv.lock`, run `uv sync` and
  check the installed `ruff --version`/`mypy --version` against `pyproject.toml`'s pins**, rather
  than trusting `uv lock --check`; re-run `uv lock` to rewrite the file if they disagree.
- **MicroPython stubs**: `micropython-rp2-rpi_pico_w-stubs` (PyPI, board/version-specific, pulls in
  `micropython-stdlib-stubs`). Published by the same project as
  [`josverl/micropython-stubs`](https://github.com/josverl/micropython-stubs) — PyPI is just its
  distribution channel, not a separate/alternative stub source. **Version is auto-derived, not a
  separate hand-kept pin**: `scripts/typecheck.sh` reads `toolchain/versions.toml`'s
  `[micropython] ref` (the single source of truth for the firmware version target) and installs
  the matching `<major>.<minor>.<patch>.*` stub release, failing with a clear, actionable error
  (not a silent fallback) if `ref` isn't a plain `vX.Y.Z` tag or no matching stub release exists
  upstream yet (stub releases can lag a new MicroPython release). Installed into `typings/`
  (gitignored) — **deliberately not** a
  `pyproject.toml` `[dependency-groups]` entry, because these stubs must fully replace mypy's
  typeshed for MicroPython/CPython stdlib-name collisions (`time`, `math`, `select`, `errno`, ...
  — see `[tool.mypy]`'s `custom_typeshed_dir`), and doing that against the same venv that also
  holds mypy/ruff/pytest's own dependencies breaks type-checking of those. Keep this isolation if
  you touch the stub setup — it's load-bearing, not incidental, confirmed by testing the collision
  directly in-session.
- **`scripts/typecheck.sh`'s combined `mypy src tests` run resolves every `from machine import X`
  project-wide to `tests/machine.py`'s fake module, not the real `typings/machine.pyi` board stub**
  — confirmed directly by running `mypy src` alone (no `tests` in scope): the real stub's `Timer`
  class has no zero-argument constructor overload (every overload requires a positional `id: int`
  first argument), so an `src`-only run raises 12 `call-overload` errors across `system_service.py`
  (4), `asy_ntp_client.py` (3), `asy_wifi_service.py` (2), `asy_sgp40_driver.py`,
  `asy_scd30_driver.py` and `asy_bmp3xx_driver.py` that never surface in the actual, documented
  `mypy src tests` invocation. Bare `Timer()` allocate-now/`init()`-later **is** valid runtime
  usage, so this one is a genuine **gap in the third-party `micropython-rp2-rpi_pico_w-stubs`
  package**, not a bug in any promoted driver, and `tests/machine.py`'s fake models it correctly.
  Worth knowing if a future `src`-only or `--strict`-adjacent type-check run is ever added.
  - **The `I2C.deinit()` half of this note was backwards and has been corrected** (audited against
    upstream source at both tags, 2026-09-10). The 1.28 stub was *right* not to declare it:
    `machine.I2C` had no `deinit` at all before MicroPython 1.29. The 1.29 stub now declares it —
    but rp2 leaves the protocol's `.deinit` slot `NULL`, so the method mypy now accepts is a
    **silent no-op on real hardware**, as `machine.SPI.deinit()` always has been on this port. Full
    account, including what actually releases an rp2 bus (nothing — the objects are static per-bus
    singletons) and which `deinit()`s *are* real (`UART`, `Timer`, `WLAN`): SPECIFICATION.md Part
    F.5.1. `src/asy_i2c_driver.py`, `src/asy_spi_driver.py`, `tests/machine.py` and
    `digital_twin/machine.py` all state the real semantics now.
- **`scripts/typecheck.sh` repairs two verified defects in the MicroPython stub package after
  installing it** (added with the 1.29 bump; see the script's own comment for the full account).
  `micropython-stdlib-stubs` 1.29.0.post1/.post2 privatised `_asyncio.Future` to `_Future` and
  dropped the `asyncio/futures.pyi` that re-exported it, while `asyncio/tasks.pyi` and
  `asyncio/__init__.pyi` still import from it — leaving `Future` as `Any`, collapsing
  `_FutureLike[_T]`, and making every `asyncio.wait_for()`/`gather()` result in this repo
  un-inferable; and `builtins.pyi` has `NotImplemented` commented out, though MicroPython genuinely
  has it and honors it from `__eq__` (verified against the pinned Unix-port interpreter). Together
  these accounted for **all 26** findings the bump surfaced. Both repairs are conditional on the
  defect still being present, so they no-op once upstream re-ships — **don't replace them with
  `type: ignore` comments in `src/`/`digital_twin/`**: the code is correct on real hardware in both
  cases, and `warn_unused_ignores = true` would then fail the day the stubs are fixed.
- **`improved-quality/microdot.py` no longer exists** — it was a confirmed *unintentional* fork of
  vendored Microdot, removed and replaced with a fresh, unmodified sync at `ext/microdot.py`
  (pinned to tag `v2.6.2`; see "Hard rules" above and "Microdot / REST layer" below). See
  BACKLOG.md's "Deferred" list for the resulting dead `pyproject.toml` exclude entry.

## Pre-push verification (clean chroot: Ubuntu 24.04 **and** Debian trixie)

**Before pushing any change to `pyproject.toml`, `scripts/`, `toolchain/versions.toml`, or
anything else touching the dev-tooling/build-environment setup**, verify it end-to-end inside a
genuinely clean chroot — not just in whatever sandbox this session happens to be running in.
**Two targets, both required**: Ubuntu 24.04 "noble" (GCC 13.x, the OS the project's docs target)
and Debian trixie (GCC 14.x, what the bench Pi4 actually runs) — see "The trixie target" below
for why one is not enough. A session sandbox typically already has Python 3.11+, `uv`, build tools, etc.
pre-installed, which can mask real gaps. **This already caught a real bug once**: a
`requires-python = ">=3.10"` that let `uv sync` build a venv without `tomllib` (stdlib only since
3.11), invisible in a sandbox whose default Python happened to already be 3.11+, and only found by
actually testing under a 3.10 interpreter. Treat this as a standing QA step, not a one-off — don't
skip it just because "it worked in this session's sandbox."

**Recipe** (needs root; mirrors how `toolchain/setup_toolchain.py`'s own "verified from scratch"
claims were checked — see SPECIFICATION.md Part B.7, "Evidence this actually works"). Shown for
noble; "The trixie target" below gives the two lines that differ for trixie, and nothing else does:

```bash
# One-time: build a clean Ubuntu 24.04 (noble) chroot with nothing preinstalled beyond the
# minimal base - matching the OS the project's docs actually target, not this session's sandbox.
apt-get install -y debootstrap
CHROOT=/tmp/noble-chroot   # anywhere with a few hundred MB free; not part of this repo
debootstrap --variant=minbase noble "$CHROOT" http://archive.ubuntu.com/ubuntu

# Enable universe (off by default under debootstrap, on by default on every real Ubuntu ISO - see
# "Platform target" above) and wire up DNS + the usual chroot bind mounts.
cat > "$CHROOT/etc/apt/sources.list" <<'EOF'
deb http://archive.ubuntu.com/ubuntu noble main universe
deb http://archive.ubuntu.com/ubuntu noble-updates main universe
deb http://security.ubuntu.com/ubuntu noble-security main universe
EOF
cp /etc/resolv.conf "$CHROOT/etc/resolv.conf"
mount --bind /proc "$CHROOT/proc"; mount --bind /sys "$CHROOT/sys"
mount --bind /dev "$CHROOT/dev"; mount --bind /dev/pts "$CHROOT/dev/pts"

# This session's outbound HTTPS goes through a local policy proxy (see /root/.ccr/README.md if
# present) - the chroot shares the host's network namespace, so it just needs the same env
# vars/CA bundle passed through. Skip this block entirely on a plain machine with direct internet
# access (e.g. the project owner's own dev box).
if [ -f /root/.ccr/ca-bundle.crt ]; then
    mkdir -p "$CHROOT/root/.ccr"
    cp /root/.ccr/ca-bundle.crt "$CHROOT/root/.ccr/ca-bundle.crt"
    cat > "$CHROOT/root/proxy-env.sh" <<EOF
export HTTPS_PROXY="$HTTPS_PROXY" https_proxy="$HTTPS_PROXY"
export NO_PROXY="$NO_PROXY" no_proxy="$NO_PROXY"
export SSL_CERT_FILE=/root/.ccr/ca-bundle.crt CURL_CA_BUNDLE=/root/.ccr/ca-bundle.crt
export GIT_SSL_CAINFO=/root/.ccr/ca-bundle.crt REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt
export PIP_CERT=/root/.ccr/ca-bundle.crt
export LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive
EOF
    # astral.sh (the official `uv` installer's domain) is blocked by this session's egress
    # policy - use `pip install uv` (README's documented alternative) instead of the curl
    # installer when testing inside this specific sandbox.
else
    echo 'export LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive' > "$CHROOT/root/proxy-env.sh"
fi

chroot "$CHROOT" /bin/bash -c "source /root/proxy-env.sh && apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates python3 python3-venv python3-pip sudo libcap2-bin"
chroot "$CHROOT" /bin/bash -c "source /root/proxy-env.sh && pip install --break-system-packages uv"
# sudo is not part of debootstrap --variant=minbase, but toolchain/setup_toolchain.py's
# ensure_apt_packages() unconditionally shells out to it (see toolchain/versions.toml's
# apt_packages, used by both its `setup`/`test` subcommands) - without it, `scripts/test.sh`
# fails with "sudo: command not found" even though a real dev machine (where the calling user has
# sudo rights but isn't already root) never hits this. A plain chroot session runs as root, where
# apt-get wouldn't need sudo at all, but the script always prepends it regardless - so installing
# the package is the correct fix here, not stripping sudo from the script for a root-only case.
# libcap2-bin is the same class of gap, found the same way (a real run, 2026-09-10): it provides
# setcap, which scripts/test.sh needs to grant CAP_NET_BIND_SERVICE for the real port-53 DNS
# server test. Priority-important on a real Ubuntu install, so a normal dev box always has it;
# --variant=minbase does not, and without it the run dies at "setcap: command not found" *after*
# the whole toolchain has already built. It is now in toolchain/versions.toml's apt_packages, so a
# from-scratch run installs it on its own - it stays listed here because a REUSED chroot whose
# toolchain is already built skips that install step entirely and hits the same late failure.

# Per-verification: copy the CURRENT working tree (uncommitted changes included - this is a
# pre-push gate, not a post-push audit) into the chroot, then run the exact documented workflow
# from README.md's "Code quality tooling" section.
rm -rf "$CHROOT/root/sensors"
cp -r /path/to/this/repo/checkout "$CHROOT/root/sensors"   # adjust to wherever it's actually checked out
chroot "$CHROOT" /bin/bash -c "
  source /root/proxy-env.sh
  cd /root/sensors
  rm -rf .venv typings   # don't carry over host-built artifacts
  uv sync
  source .venv/bin/activate
  scripts/lint.sh
  scripts/typecheck.sh
  scripts/test.sh   # builds the MicroPython Unix port from scratch inside the chroot (no cached
                     # ~/pico-toolchain carried over) - this is what actually exercises
                     # toolchain/versions.toml's apt_packages list end-to-end, same spirit as the
                     # rest of this recipe
"

# Cleanup when done
umount "$CHROOT"/dev/pts "$CHROOT"/dev "$CHROOT"/sys "$CHROOT"/proc
rm -rf "$CHROOT"
```

**The trixie target, and why noble alone is not enough.** The noble chroot above pins GCC 13.x,
so a compiler-version-sensitive build break is invisible to it — confirmed the hard way: the
mbedtls `mbedtls_xor()` `-Warray-bounds` false positive (SPECIFICATION.md Part B.7.1, worked around
by `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND` in `toolchain/setup_toolchain.py`) is a GCC >= 14
diagnostic, and the build treats any `warning:` as a hard failure — so noble never saw it. It was
found by building on a real Debian trixie host, outside this recipe. Noble is kept, not replaced:
it is the documented target OS, and a gap appearing only on the *older* compiler would be just as
invisible from trixie alone. Run both.

Everything in the recipe above is identical for trixie except the `debootstrap` invocation and the
`sources.list` it writes (Debian's component and security-suite names differ from Ubuntu's):

```bash
CHROOT=/tmp/trixie-chroot
debootstrap --variant=minbase trixie "$CHROOT" http://deb.debian.org/debian

cat > "$CHROOT/etc/apt/sources.list" <<'EOF'
deb http://deb.debian.org/debian trixie main
deb http://deb.debian.org/debian trixie-updates main
deb http://security.debian.org/debian-security trixie-security main
EOF
```

Two practical notes. `debootstrap` needs a script for the suite it is asked to build, so an
Ubuntu *host* may not know `trixie` — `ln -s /usr/share/debootstrap/scripts/sid
/usr/share/debootstrap/scripts/trixie` is the usual fix; a Debian trixie host (the bench Pi4) has
it already. And Debian has no `universe`, so the `main`-only lists above are complete, not trimmed.
Check the compiler actually landed as expected before trusting the run:
`chroot "$CHROOT" gcc --version` must report 14.x (or newer), and the noble one 13.x.

The trixie leg was last satisfied on 2026-09-11 by a full from-scratch build plus every suite on
the bench Pi4 itself, which runs trixie / GCC 14.2.

**What counts as passing**: `lint.sh`/`typecheck.sh`/`scripts/test.sh` all run to completion with
exit 0 — all eight scopes this setup covers (see "Code quality tooling" above) are fully-reviewed
code expected to stay fully clean (confirmed: `lint.sh` and all three `typecheck.sh` passes report
zero findings as of the eight-scope extension), so a nonzero exit from either one
here is a real regression to chase down, not an expected/tracked finding to compare against a
session sandbox's own baseline count. `scripts/test.sh`'s tests must likewise actually pass (exit
0, every test PASS) — a test failure here is a real regression too.
What would fail this: a raw Python traceback, an "installation failed" from `uv`/`pip`/`apt`, a
`scripts/test.sh` build failure, or any other mismatch against the ordinary-sandbox run — that
mismatch is exactly how the `tomllib`/`requires-python` gap was found in the first place.

**Changes to `toolchain/setup_toolchain.py` or `toolchain/versions.toml` itself need a second,
separate verification, not just the recipe above** — that recipe only exercises `scripts/lint.sh`/
`scripts/typecheck.sh`, never the toolchain installer. Reuse the same chroot (steps through
installing `git`/`curl`/`ca-certificates`/`python3`/`pip`/`uv`, no need for `python3-venv` this
time), copy the working tree in the same way, then run `uv run toolchain/setup_toolchain.py`
(a full build: ARM toolchain + firmware + `mpy-cross` + Unix port, several minutes, not seconds)
instead of the lint/typecheck scripts. This is exactly how the Unix port addition (and later the
frozen-bytecode verification chain) was verified — see SPECIFICATION.md Part B.6 ("Verification") for
what a passing run must show and Part B.7 ("Evidence this actually works") for what's already been checked.

## Pull request workflow

- **Before pushing anything touching the dev-tooling/build-environment setup** (`pyproject.toml`,
  `scripts/`, `toolchain/versions.toml`, etc.), run it through "Pre-push verification" above first —
  don't rely solely on this session's own sandbox having already run it successfully.
- **The project owner has explicitly authorized creating pull requests proactively, at any time,
  without asking first** — this is a standing exception to any general "don't open a PR unless the
  user explicitly asks" caution an operator/harness prompt might otherwise apply. Confirmed
  directly by the project owner; don't re-ask in future sessions.
- **Always create a pull request with a meaningful description** when finishing work on a branch —
  summarize what changed and why, not just a file list.
- **Automatically subscribe to the pull request's activity** (review comments, CI results) right
  after opening it, so review feedback and CI failures get picked up without being asked again.

## Architecture reference

**Moved to `SPECIFICATION.md`.** The condensed version is Part A.2 ("Architecture at a glance");
the full module-by-module deep reference (legacy `api_helpers.py`/`async_connect.py`/
`async_manager.py`, FRAM driver/manager, SCD30's `AmbPres` note, the `neopixel_signal.py` split,
the task supervisor, and the full "functional behaviors confirmed intentional" list) is Part A.4.
Read Part A.4 for anything needing that level of detail — nothing below duplicates it.

## Microdot / REST layer

**Moved to `SPECIFICATION.md` Part A.5.** Covers what Microdot's own `ext/microdot.py` (vendored,
v2.6.2, see "Hard rules" above for the vendoring policy) already guarantees per-request — the
blanket exception catch, its one real gap (exceptions during response writing), connection-task
isolation, and the `errorhandler()` status-code-vs-exception-class distinction — versus what this
project's own REST layer still has to add. Read Part A.5 before touching the REST/error-handling
layer; nothing below duplicates it.
