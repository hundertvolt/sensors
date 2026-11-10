# CLAUDE.md

Operating rules and working agreements for AI sessions in this repo, each with one short reason.
Facts and specifications live in SPECIFICATION.md (its Part 0 states the design principles every
rule here serves), orientation and recipes in README.md, open work in BACKLOG.md. README.md's
"Further reading" is the one map of every supporting document; it is not duplicated here.

## Datasheets

The datasheets for every chip this codebase drives are the private submodule
`hundertvolt/datasheets` at `datasheets/` (`git submodule update --init datasheets`; its folders:
SPECIFICATION.md Part A.6). Read the datasheet first for any hardware-interaction claim and cite its
page, section or table; training memory is never a source. A missing document is named, and work
continues from the next-best primary source (the vendor's reference code or documentation), the
finding marked open until the owner supplies it (owner, 2026-09-25).

## Platform target

**The concrete facts** — MicroPython 1.29.0/RP2040 specifics (the legacy units run 1.24.1), what the
audit of the `v1.29.0` pin found (Part F.5), the WDT 8388ms cap, RP2040 hardware specs, the
soft-Timer-callback-drop gotcha, the `[x] * n` segfault range, `Timer.init()`'s `OSError(ENOMEM)`
case, the `MemoryError`-isn't-an-`OSError`-subclass rule, `struct.pack()`'s silent truncation —
**live in `SPECIFICATION.md`'s Part F (Platform Target & MicroPython Runtime Facts).** Read Part F
before any platform-facing code work; don't rely on memory of it, and don't re-derive these from
training memory or general Python knowledge: they are checked against the pinned MicroPython source.

Three standing practices:

- **Always check current MicroPython and Microdot documentation before asserting how an API
  behaves** — never training-data memory for either, since both change between releases.
- **Whenever the owner moves the pinned MicroPython version (owner, 2026-09-26: the pin moves only on
  the owner's call), and periodically otherwise, re-check every MicroPython-facing code construct
  against the current pinned version's own source, the current rp2 port documentation, and
  MicroPython developer-forum/issue-tracker findings** — not just "is this still correct," but
  specifically "is there now a newer/better/more-complete way to do this that a stale construct is
  missing out on" (a newly widened set of types accepted by `micropython.const()`, say, or real
  `asyncio`-level timeout support where there was none). The practice (owner, 2026-10-05)
  repeats every time `toolchain/versions.toml`'s MicroPython `ref` moves and covers every Part F fact
  and upstream file:line citation, the stub release, every item ruled out last time, and
  `toolchain/micropython_overrides.py`'s anchor checks (SPECIFICATION.md Part B.14) — each
  `verify_*()` there fails loudly on its own if its anchor text drifted, but re-reading the real
  mechanism behind each anchor, not just whether the literal string still matches, is part of the
  practice. For the
  `modlwip_eagain` override it also asks, patch by patch, whether the new pin carries a real upstream
  fix: micropython issue 19704 (PRs 19705/19708) for the EAGAIN patch, a listener close that skips
  lwIP's forbidden callbacks and a `listen()` that stores its backlog size only after allocating the
  queue for the two listener patches (SPECIFICATION.md B.14.4). A fixed patch is removed, not
  re-anchored, and the override goes with its last patch (owner, 2026-09-30; owner, 2026-10-26).
  The last pin move, 1.28.0 → 1.29.0, is SPECIFICATION.md Part F.5's record; the last re-check,
  2026-10-06, found no newer stable MicroPython release than `v1.29.0`.
- **Every external dependency is refreshed as one step, not only MicroPython** (owner, 2026-09-30:
  "Check all external dependencies for updates - both modules, repos and tooling, just
  everything."): the vendored `ext/` code (only as an unmodified upstream tag or commit), the stub
  packages, every Python and npm tool with its lock, Node, the GitHub Actions pins and every other
  fetched source. Read each update's changelog and the diff of the parts this repo uses; fix what
  breaks with no regression at every level and both GC stages; take the fixes the project profits
  from; and re-check every standing workaround in SPECIFICATION.md Part F.9, removing it for the
  clean form where upstream fixed it. Pins stay pinned; the bullet above runs whenever the
  MicroPython ref moves.

## Hard rules

- **An owner-authorised exception to a hands-off rule** (agent, 2026-07-30): for a
  severity-justified fix the owner can authorise a scoped exception to a "don't touch" rule in this
  file — the precedent is the `ConfigManager`/`LockedValue` wrong-module-import fix. It still
  requires the owner's explicit authorization each time, scoped narrowly to the specific fix, not a
  general license, and it never reaches the legacy tree, whose later rule admits no work of any kind
  (owner, 2026-09-11).
- **`src/` is where files land once they're fully reviewed and tested** — formula/logic
  correctness checked, input validation and exception-safety audited, unit tests written and
  passing (see "Code quality tooling" below and SPECIFICATION.md Part E). **SPECIFICATION.md Part K is
  the one checklist** for what "fully reviewed and tested" actually requires — apply it to every file
  that makes this move; it applies Part D's quality bar. **For a new sensor driver
  specifically, SPECIFICATION.md Part C is the shared architecture/interface spec** extracted from
  the drivers already in `src/` — what shape the code should take (layering, naming, error
  handling, config schema, ...). Treat `src/` files as normal, freely-editable code.
- **Whenever a new file is added to `src/`, run a bird's-eye-view scan over the whole
  content of `src/`** — not just the new file in isolation — to check it against SPECIFICATION.md Part
  0's design principles, and that the coding guidelines and Part K's checklist (its API consistency
  within a file and across the project, and its check against current MicroPython, included) actually
  hold consistently
  across every file there, not just that the new file individually passes review on its own. **This
  scan also covers `SPECIFICATION.md` Part G's shared-primitive catalog and discovery procedure**
  (numeric validation/coercion, callback dispatch guarding, response envelopes, locked state,
  logging, and — for anything website-facing — the `src/`↔`js/` cross-language mirror obligation):
  before writing any new function/module, check Part G's catalog first for an existing primitive to
  reuse or model on, and re-run Part G.3's grep-for-the-shape check across the codebase as part of
  this same scan, not as a separate pass. A consistency discrepancy (naming, ordering, signatures,
  uniform behaviour) is fixed directly and logged (owner, 2026-09-25: 'Change, don't flag, if not
  according.'); a formula or behaviour discrepancy follows Part D.1's flag-first path.
- **Do not "fix" `legacy/firmware/modules/_boot.py`'s `import sensortask.py`** (literal `.py` in
  the import statement) without testing on real hardware first. It works reliably today, yet the
  import machinery says it should not: traced through the pinned source at 1.28 and re-verified at
  1.29.0, a plain `import sensortask` is unambiguously the correct form and the dotted one should
  raise, because it requires "sensortask" to resolve as a package (SPECIFICATION.md F.1 has the trace).
  **That does not make the file safe to change** — the trace is against 1.28/1.29, while the legacy
  units run 1.24.1, whose import machinery was never separately verified. So the *mechanism* is
  answered and the *rule* stands unchanged: changing it blind risks breaking every deployed unit's
  autostart, and extrapolating from a different version's source is exactly the blind change this
  rule exists to prevent. The dev bench never flashes the legacy build, so any such test runs on one
  of the owner's own legacy units, as the owner's operation (owner, 2026-09-26).
- **`legacy/firmware/python/CommonDrivers/microdot.py` is vendored third-party code.** Part of
  the reference-only legacy tree: never edited (legacy rule below). It is upstream commit `482ab6d`
  (#251), byte-identical to it: an untagged snapshot four commits after `v2.0.6`, before `v2.0.7` —
  unmodified, just old (compared against upstream commit 482ab6d, 2026-09-30). A legacy unit
  moves forward only by the owner's reflash with fresh setup, following the reflash runbook, never
  by editing this copy. **`ext/microdot.py` is the same policy applied to the refactor
  target**: a plain, unmodified vendored copy of upstream Microdot (pinned to tag `v2.7.0` and
  verified byte-identical to it on 2026-10-06), with upstream's own stubs vendored byte-identical at
  `ext/typings/microdot/` under the same policy (owner, 2026-10-01). No
  edits, no restyling, ever (agent, 2026-09-25) — any behavior change needed is handled by
  wrapping/calling it from our own code (see "Microdot / REST layer" below), never by touching these
  files. `src/` and `ext/` are copied flat into one directory and frozen together for the refactored
  firmware build, which is why they live at the same directory depth in the repo.
- **The UART message protocol (`src/asy_uart_comm.py`) is a two-implementation contract with its C
  peer on the Arduino** — its wire format, accept/reject rules and recovery timings are not this
  repo's to change unilaterally, so **every change to it gets an entry in `UART_C_PORT_CHANGELOG.md`**,
  Class A ("must be mirrored in C") or Class B ("no C impact"), the second logged too so a future
  session doesn't re-derive it. The contract and the owner's rulings on it (scope, flag-days, the
  untouched wire format, the out-of-band parameters, the role model, the bench-only link):
  SPECIFICATION.md Part J (J.1, J.2, J.6); the exerciser's exception: SPECIFICATION.md D.3.
- **`dev` meets every device's bar**: its generated config is held to the same standard as every
  device's; a quirk is a defect (owner, 2026-09-26).
- **A device's result counts only from its own build on its own hardware.** Every device is built
  from its own `devices/<device>.toml` and no build is special: "There is nothing special for any of
  the builds (apart from some well contained exceptions for dev, which is somewhat special)" (owner,
  2026-10-02). `dev` is the bench rig, the only unit a session flashes and bench-tests; a passing
  dev-bench result holds for the shared mechanisms every device's code uses (I2C/SPI/WiFi/webserver/
  etc.), provided the code under test is genuinely dev's own build (its own pins and config via its
  own entry point). Another device's image flashed onto the bench is an invalid test by construction —
  it tests nothing, and is not repeated (owner, 2026-09-03, `5730e72`, paraphrase). Every other
  device's correctness comes from the mock, twin and unit tiers and its own build, and a unit moves to
  new firmware only by the owner's own reflash (owner, 2026-09-26, paraphrase).
- **The legacy tree is reference-only, forever — it never gets work of any kind** (owner,
  2026-09-11). `legacy/firmware/` (the legacy units' firmware tree: `legacy/firmware/python/`,
  `legacy/firmware/modules/`, `legacy/firmware/html_raw/`, the four `legacy/firmware/build-*.sh`,
  `legacy/firmware/update_and_install.txt`) and `legacy/dev_drivers/` (the dev unit's 2026-08-27
  snapshot), described in `legacy/README.md`, exist to be *read*: what the owner's legacy units
  (MicroPython 1.24.1) actually do, and how a driver behaved in the field. Nothing in this repo's
  quality apparatus is ever extended to them — no lint/typecheck scope, no CI build stage, no
  shellcheck cleanup, no tests, no refactor. The one change it ever got is its byte-identical move
  into `legacy/` (owner, 2026-09-25). It may run in a scratch directory as a published-value
  reference, nothing committed (owner, 2026-09-26). A finding *about* legacy code is worth recording
  only when it explains current behavior; it is never a to-do. Don't propose closing any of these
  gaps — the gap is the decision. `legacy/firmware/modules/_boot.py`'s `import sensortask.py`
  (above) is this same rule applied to one specific file, not an exception to it.
  `tests_scripts/test_legacy_paths.py` fails on any current file naming a pre-move path.
  This does **not** contradict SPECIFICATION.md Part E's testing requirements, which describe what the
  refactored code must have: the rule is "never test
  the legacy code (`legacy/`)", not "defer all tests".
- **Don't touch `sensors/config.json`-equivalent files or commit any real credentials.** A
  `.gitignore` covers per-device config/build artifacts, but still be deliberate about what you
  stage. **The one known real credential already in this repo** is the hotspot fallback password: the default of
  `HotspotPW` in `src/asy_wifi_service.py` and of every `devices/*.toml`'s `hotspot_password`,
  copied into the reference-only legacy tree and into tests pinned to that default; accepted
  permanently as a known limitation under the trusted-home-LAN threat model (owner, 2026-09-26;
  first accepted 'for now', owner 2026-07-13, `b64857d`). SPECIFICATION.md A.11 lists every place
  and the history-scan result.
- **A wedged I2C bus or sensor recovers through the recovery ladder, smallest blast radius first —
  retry, the participant's own reset, bus clear and controller re-init, task restart, reboot, the
  hardware watchdog last** (owner, 2026-09-30); a transfer in flight cannot be interrupted, so the
  ladder acts after it returns an error, and a call that never returns is the watchdog's — the
  current state, until a genuine non-blocking alternative reliably exists (owner, 2026-07-24; BACKLOG
  deferred goal). Full ladder and which waits can be timeout-wrapped: SPECIFICATION.md Part F.2.
- **The same backstop applies to a WiFi link stuck in a CYW43-firmware-level `isconnected()` false
  positive — a power cycle/`hard_reset()` stays the recovery, because the owner judged an
  independent reachability probe not worth its complexity (owner, 2026-09-04, `655e4f9`, paraphrase;
  confirmed 2026-09-26).** It is safe: every flash write follows an API action — an accepted PUT that
  changed a value, or the `SystemCmd` `"resetconfig"` — or is a config file's one setup write at boot
  (next rule), so a device whose API is unreachable has no write of its own
  in flight. Full reasoning and real bench-hardware timing data are in SPECIFICATION.md Part F.2.
- **The firmware writes a limited-endurance store only on a user or API action** (owner, 2026-09-26:
  'never write without user / api interaction as a standing rule'). The flash filesystem is written
  only through `ConfigManager`: on an accepted PUT that changed a value, flushed off the request path;
  by the `SystemCmd` `"resetconfig"`, which deletes the config files; and at most once per config file
  per boot, in its `setup()` — an absent file's defaults (owner, 2026-10-01) or the repair of a
  readable but damaged one, an unreadable file never being overwritten. The SCD30's NVM is written
  only on an accepted PUT that changed a value or by a command the PUT carries (`AmbPres`,
  `ForceCalRef` and `ContMeas` always execute). Nothing re-runs a write on its own — no timer, retry
  or cross-boot flag. FRAM is outside this rule. Full account: SPECIFICATION.md C.7.3 and F.2.
- **`MemoryError` handling follows one criterion** — a function with a true graceful-degradation
  alternative catches and degrades; one that is doomed without memory lets the task end for the
  supervisor to restart; `asyncio` primitives are never blanket-wrapped (owner, 2026-09-25, asked,
  paraphrase, to confirm an audit method that caught a theoretical `MemoryError` only against a
  concrete threat and never blanket-wrapped `asyncio` primitives: 'This is only true if the function
  experiencing the MemoryError is doomed to fail on memory error (restarting the task or stalling
  the system into a watchdog reset is the only remedy then anyway) - but if the function has a true
  alternative flow for graceful degradation on expectable memory errors, this indeed shall be
  implemented'). SPECIFICATION.md Part I.4(a).
- **Adafruit-derived driver code is fair game to restructure/rewrite** (keeping attribution)
  (owner, 2026-07-13, `b64857d`) — unlike `legacy/firmware/python/CommonDrivers/microdot.py`/
  `ext/microdot.py`, which stay hands-off/vendored (see above). Full note: SPECIFICATION.md
  Part F.4.
- **Long-blocking operations must not stall timing-sensitive work** — standing design principle
  for all new code; full reasoning (including the retired `get_long_block_lock()` mechanism) is in
  SPECIFICATION.md Part F.3.
- **Boot latency is not a metric to optimise for its own sake** (owner, 2026-09-16, the owner's
  background as migrated by `abe4009f`, paraphrase). These devices run for months between reboots,
  and a short period of API unavailability right after one is normal for any networked device — a
  multi-second one-time delay at boot is not itself a problem. What *is* a problem is approaching
  the hardware watchdog's own timeout while the one-time boot `setup()` batch runs, which is what
  `SystemService.feed_watchdog()` exists to prevent (SPECIFICATION.md Part A.7/G.2). Don't "fix" a
  slow boot by trimming that batch, reordering it for speed, or otherwise treating its wall-clock
  cost as a defect — the accepted target is "does not starve the watchdog," not "boots fast."
  Each inter-feed boot stretch is a row of SPECIFICATION.md Part F.3's table, its margin in the
  Part N row that row cites.
- **`asy_uart_driver.py` and `asy_uart_comm.py` may never block the asyncio loop — not even in a
  wait state.** They may time out and handle it; they may not wait synchronously (project owner,
  2026-09-11). This is sharper than F.3's general principle and is easy to violate by accident:
  `machine.UART.read()/readinto()` wait out `timeout_char` for every byte asked for that has not
  arrived yet, inside `mp_event_handle_nowait()`, which never yields — so a plain "read the whole
  frame after `POLLIN`" holds the loop for the frame's entire wire time (measured: 4.4ms per
  53-byte frame at 115200 baud), which is why the driver never calls `machine.UART`'s receive side.
  The fix needs **both** a clamp to the bytes already received on every read — the DMA receive
  ring's fill level (owner, 2026-10-05) — and a real yield between rounds; the clamp alone is
  *worse*, because `ready()` returns `True` with no `await` and the block simply moves into a Python
  loop. The yield lives in `ready()` itself, which every read loop goes through, so the invariant is
  one guarantee in one place rather than a per-call-site obligation. **The mirror-image failure is
  just as forbidden** (agent, 2026-09-11, extending the owner's rule): `ready()` polls, so a
  listener waiting on traffic that may never come must not idle at the transaction rate — an
  instance takes a second, slower `poll_idle_ms` for a wait with no deadline (Part F.5.9). Full
  account and the measured before/after: SPECIFICATION.md Parts F.5.8 and F.5.9 — F.5.8 also states
  why this must **not** be generalised to `asy_i2c_driver.py`/`asy_spi_driver.py`, whose peripherals
  expose no partial-read API to clamp to (that case stays F.2's watchdog backstop).
- **A new device on a shared resource — an I2C/SPI bus and every other shared resource (locks, FRAM,
  the config file, sockets, the heap) — gets hazard test coverage across all four test tiers that
  apply to it — never forget this** (owner, 2026-09-03, `da3a5b5`: 'note down to never forget this';
  every shared resource, owner, 2026-09-26): same-device read-vs-write concurrency, cross-device
  interleaving if it shares a bus on any device, and an address/command sweep, at the mock, twin,
  flash and bench levels. The files per level, the full checklist and the two real-hardware
  write-safety constraints any new device's own on-chip NVM or the RP2040's own flash filesystem must
  respect are SPECIFICATION.md Part C.8's standing rule — the one list, not restated here.
- **Least wear in the production code: the central wear rule, ahead of the test rule below**
  (owner, 2026-10-22: "The least wear rule is even more important for the production code than for
  the tests, as it will run potentially for years. This is something to be added to our pillars, a
  completely central important rule."). Every write the firmware makes to a limited-endurance store,
  the RP2040's flash filesystem (each littlefs file create, write, rename or remove) and the SCD30's
  on-chip NVM, is the fewest the job needs: a file is written directly, once per change, with no
  temporary or sibling file and no rename or copy step, and an unchanged value is never written
  (compare-before-write, SPECIFICATION.md G.2). FRAM writes are not wear (owner, 2026-09-26). A
  change that adds, multiplies or reshapes such a write, in `src/`, buildgen's templates, the
  generated modules or a test, is the owner's question and is never decided on the owner's behalf
  (owner, 2026-10-22: "a condition strictly to be avoided by rule and nothing you were allowed to
  decide without even asking"). `tests_scripts/test_firmware_write_sites.py` pins every flash and
  SCD30-NVM write site in `src/` and every device's generated modules by file, function and
  construct, so a new, moved or vanished site fails as the owner's decision; it reads constructs,
  so an aliased `open` or a command passed through a local is beyond it (SPECIFICATION.md D.3).
- **No test may inflict avoidable wear on real hardware — the host's own SSD included, not just the
  target's flash/NVM** (project owner's explicit, standing direction, 2026-09-17). FRAM writes are
  not wear (owner, 2026-09-26: 'FRAM writes do not count as wear.'). On the target every operation
  that spends a limited-endurance write cycle sits behind a default-off marker with a tracked budget:
  `flash_cycle` (`--allow-flash-cycle`, "reflashes the board (flash wear)"), `persistence_write`
  (`--allow-persistence-write`) for any real write to the SCD30's on-chip NVM or the RP2040's flash
  filesystem (a dispatch-only PUT persists nothing and is outside the gate), `scd30_extra_write`
  (`--allow-scd30-extra-write`) AND-gated on top for the up to 12 further SCD30 NVM writes its four
  tests own (with both flags up to 13 owned writes per session on `dev`'s SCD30, and at most one
  start command; owner, 2026-10-21: "option a", asked "Cap the SCD30 NVM writes the extra-write flag
  admits?", option (a) keeping what the tests carry), and `soak_duration` (`--soak-duration`) and
  `multi_day_rollover` (`--allow-multi-day-rollover`); their budgets: `tests_hardware/README.md`. The
  gate deselects rather than skips, so the hardware verdict (`scripts/_hardware_verdict.py`) lists
  every deselected test with its flag: "clean" there means "everything that ran, passed", not
  "everything ran". **The gate covers the write a test OWNS, not one it is merely reached through** (owner's
  clarification, 2026-09-18): a persisting write that *is* the thing under test is optional and
  belongs behind the marker, while one that is a shared **prerequisite** — a fixture forcing a mode
  many tests then exercise, a recovery path — stays unmarked and allowed, since gating it would
  deselect the very tests it exists to enable. A boot on a fresh filesystem writes each config
  file once with its defaults; a test that boots one reaches those writes as a prerequisite, never
  as the write under test, so they stay unmarked (owner, 2026-10-01). The console-starvation bench
  test spends two flash writes it owns and runs only behind the persistence-write flag (owner,
  2026-10-02, paraphrase). The choice the flag offers is
  therefore "test everything and accept the higher wear" versus "test everything that matters and
  keep wear as low as it can go", never "spend zero";
  `tests_scripts/test_persistence_write_marker_completeness.py`
  pins the prerequisite set by name so a new one is triaged against that rule rather than joining it
  silently. **The same lens applies to host I/O**: a test must not generate mass filesystem churn,
  and an invariant is proven *structurally* — assert the property the current code must hold —
  never by brute-forcing a scale large enough to reproduce a symptom. `tests/test_tmp_scratch.py` is
  the example: it records a full `TmpScratch` lifecycle's `os` calls and asserts none reads the
  shared root, where building 400,000 directories to show the same cost 396 MB of disk writes per
  run (`/proc/diskstats`).
- **A session needs the project owner's go-ahead, given directly in that session's own
  conversation (owner, 2026-09-25), before running anything against real hardware** (any `mpremote` command, `nmcli`/
  `iw`/`iptables` call, `picotool`, or `tests_hardware/`'s own suite runners) — a go-ahead given to
  a different session, or to an earlier session that already ended, does not carry over; if there's
  any doubt whether the current conversation actually has it, ask first rather than assume. Once
  granted, it covers the rest of that same conversation — real-hardware work spanning multiple
  turns doesn't need to be re-confirmed turn by turn. `tests_hardware/README.md` is the durable
  technical reference (prerequisites, environment variables, safety facts like the
  `--allow-flash-cycle`/long-soak opt-in gates and the hotspot role-reversal scenario's stage-6
  fallback (a failed credential reopens the DUT's hotspot once, then its silent mode)) for what a
  session with that go-ahead actually needs to know — this rule is just the standing gate for
  whether to start at all.
- **A destructive test of the bench host's own network/access config (tearing down `br0`/its
  slaves, revoking `dialout`, anything that can cut the very connection a session is using to reach
  the host) must keep a recovery dead-man's-switch continuously armed (owner, 2026-09-26) for the
  entire risk window — never touch live network state with none armed.** A one-shot timer already
  spent by an earlier dry run protects nothing, so the switch is armed and verified for each risk
  window. `env --tier bench` arms one itself around
  every bridge change it makes: verified armed before the change, disarmed only once `br0` has an
  address and the default route, left armed when the change fails. The recovery script and the arm,
  verify, disarm pattern: SPECIFICATION.md Part B.13.
- **The bench Pi4's `br0` bridge must always present `eth0`'s own real hardware MAC, never a
  NetworkManager-synthesized one — pin it via `bridge.mac-address`, always, on every bridge
  creation.** (observed on the bench, 2026-09-04, `28c5d8e`; B.13) A synthesized bridge
  MAC can drift across the bridge's own lifetime, silently orphaning the router's static DHCP
  reservation. `ensure_bench_bridge()` and `tests_hardware/README.md`'s manual recipe both pin it
  (SPECIFICATION.md Part B.13).
- **Memory-safety discipline: design for zero `MemoryError`s first, catch→degrade→restart→watchdog
  as a last-resort backstop, `gc`-default-first, always applied — not only once something has
  already broken.** A caught `MemoryError` that merely didn't crash anything is a design defect to
  fix at its source, never a passing result; the whole suite passes first at `gc.threshold(-1)` with
  zero `MemoryError`s, caught-and-logged included, then at the shipped `gc.threshold(32768)`; every
  memory gate matches `MemoryError` OR `memory allocation failed`; the firmware calls no
  `gc.collect()`, and outside it a collect only sets a measurement baseline or keeps a collection out
  of a window about to be timed. The scheme, the owner's rulings on it, the gates and the allowed
  sites: SPECIFICATION.md Part I (I.4).
- **When investigating any unexpected real-hardware error or reset — read the FRAM-persisted
  per-module error logs (`GET /status`'s `errcount`, its FRAM-backed subset)
  BEFORE issuing any `PUT /status {"ResetErrors": true}` call or otherwise clearing state.** (agent,
  2026-09-25) Which loggers are FRAM-backed follows the implicit FRAM-wiring rule: on a
  device whose TOML wires `fram_target`, every module built after `fram` logs into it, each
  `SensorReaderConfig`'s own `CFGMGR_<name>` logger included, except `CFGMGR_SCD30`, which stays
  RAM-only (owner, 2026-09-29, on the FRC settings: 'no extra FRAM chunk'); each device's resulting
  set: SPECIFICATION.md Part A.7. This is the one piece of real diagnostic evidence a reboot itself
  doesn't erase, and clearing it is irreversible. The same
  check applies inside the digital twin (`digital_twin/_fram_chip.py` models the same chunked FRAM
  layout) — check before clearing there too, not just on real hardware. **One caveat: this rule
  assumes a board that has been running normally.** An isolated-driver
  device script builds its own `FRAMManager` over the same chip, and the allocator is
  deterministic, so its first chunk *is* production's first chunk — a flash/bench-tier run
  overwrites the real error logs, and a script leaving a well-formed chunk behind under the
  production owner's name fabricates a plausible-looking one (test data, not firmware evidence).
  Before
  treating a FRAM-backed log as evidence, check what has been run against that board; `tests_hardware/README.md` has the full mechanism.

## Working agreements

- Long-term goal: fully understand the current (production) system in detail, then check what's
  already been addressed/promoted well into `src/`. The refactor should end up with the *same
  top-level features* (owner, 2026-07-13; restated 2026-09-25: 'My expectation is that the current
  features remains across the changes done here'), just more consistent/stable — not a feature
  change.
- **Change classes** (owner, 2026-09-25). A consistency discrepancy — naming, ordering, signatures,
  uniform behaviour of equivalent code — is changed directly, with every consumer of a public
  interface in the same change, and named in the commit message (owner: 'Change, don't flag, if not
  according.'). A formula or behaviour defect proven by a datasheet or the specification is fixed with
  a regression test for the correct behaviour and the proof in the commit message (SPECIFICATION.md
  E.2.2); anything less clear is entered in BACKLOG.md's owner-question list, not changed. A fact in a
  doc or a code comment that contradicts the code — this file's and BACKLOG.md's included (version
  drift, a changed upstream API) — is corrected in the same session, never silently worked around.
  Drift in a recorded rule or owner decision is not reworded: it goes to that list with its history
  (the original wording and intent, what it drifted to), and the work follows the rule as it stands
  unless that breaks a test or the build, which is recorded there too.
- **Documentation contains current state, future targets, and rules/agreements — not the historic
  path that got there** (owner, 2026-09-25: 'Only facts, agreements, rules and technical explanations
  are desirable.'): each rule keeps one short technical reason and its "(owner, date)", a measured
  number stays only as a rule's evidence, and incident stories, "this used to be" and who found what
  go. BACKLOG.md is active working memory (open questions, deferred work,
  in-flux decisions), not an append-only log of bugs found and fixed in already-shipped, tested
  code; once an item is resolved, it comes out — its facts to SPECIFICATION.md, its rules to this
  file, or simply dropped if it was process narrative with no forward value. Pruning history back out
  is routine
  maintenance whenever an item resolves, not a one-off cleanup.
- **Decision records (owner, 2026-09-26: the five prevention rules, answered '4. yes')**: (1) every
  decision statement names actor and date, "(owner, YYYY-MM-DD)" or "(agent, YYYY-MM-DD)"; decision
  vocabulary without an actor is not written; (2) an owner decision quotes the owner's words and the
  question, in the commit message and the doc; a paraphrase is marked "paraphrase"; an agent
  recommendation stays the agent's even when accepted; (3) compaction, migration, proofreading and
  comment-cap edits never change actor, qualifier ("for now", "until …"), scope or foreclosure — the
  commit says "no meaning change" or names the change; (4) an owner question is asked in session or
  entered in BACKLOG.md's one owner-question list with its date, numbered, a decision in at most 10
  words, then its options each with its consequence, describing effects per device and bus;
  "flagged for the owner", "owner's call" and "revisit" appear nowhere else, and nothing cites a
  temporary plan by section or number; (5) `tests_scripts/test_decision_vocabulary.py` and
  `tests_scripts/test_citations.py` fail on actorless decision vocabulary and on citations to
  missing files, headings or numbered decisions (existing text allow-listed until rewritten; the
  list only shrinks). No owner trace never means the owner did not decide; the most recent owner
  decision wins (owner, 2026-09-26: 'in case of changes by myself take my most recent decision').
  A decision also names the facts it rests on; when one is shown false, the decision goes back to
  its maker with the new facts, neither kept nor overridden silently. A measurement names its
  condition (idle or loaded, which case, silicon or Unix port), and a budget row names its real
  consumers, read from the code (agent, 2026-11-07).
- **An owner question comes after the principles are checked at every level; what they leave
  genuinely open is flagged to the owner, never guessed** (owner, 2026-11-07:
  "check the whole situation against our pillars, which you should already have done before even
  asking me"): its subject is checked against SPECIFICATION.md Parts 0 and D at each level 0.1
  names, and what that check answers is not asked; a cost in it carries its context — the lock or
  bus it holds, under which load, who waits meanwhile (D.8) — never an isolated figure
  (agent, 2026-11-07).
- **Every file opens with exactly one header comment block, and every comment block — header or
  inline — keeps to three prose lines, prefer fewer** (owner, 2026-09-14, re-confirmed 2026-09-18;
  every file of every language, owner, 2026-09-26): a concise header and a few short, genuinely
  load-bearing WHY notes next to the line they explain, never a multi-paragraph block of narrative
  reasoning — Python, shell, JS, CSS, HTML and the config files (`pyproject.toml`, `ci.yml` and the
  composite actions, `zizmor.yml`, the TOMLs and INIs, `eslint.config.js`, the JSONC `tsconfig*.json`)
  alike. Python's per-function form is SPECIFICATION.md D.11's. Load-bearing detail that doesn't fit
  moves to its home — the relevant `SPECIFICATION.md` Part if the fact is architectural and reused
  elsewhere, leaving a short pointer (website-facing facts go to Part H),
  `digital_twin/README.md` for anything `digital_twin/`-specific, or a
  short comment right next to the code it explains — never dropped outright. Comments and logged
  strings are English (agent, 2026-11-05: the legacy code it is promoted from carries German comments).
  **Exempt, being data rather than
  commentary** (the prose introducing each is not): the machine-read tag lines `# @web`, `#
  @web-group`, `# @wiring`, `# @value-wiring`, `# @limits` and `# @requires`, buildgen's input, one
  line per field by construction (SPECIFICATION.md Part L.6.4), `# @tunable` (`// @tunable` in JS),
  the tunable register's (Part N), and `# @include`, the device-script renderer's
  (`tests_hardware/harness.py`; owner, 2026-10-26: "These lines are not comments, they count as
  productive code."); JSDoc `@typedef`/`@param`/`@returns` annotations, since `npm run typecheck`
  really checks them with `tsc` (`js/definitions.js`'s `@typedef` run is a type declaration, not a
  comment); and PEP 723 inline script metadata, the `# /// script` … `# ///` block every `uv run`
  script carries, which `uv` itself reads. **How a block is counted**: prose lines only; a bare `#`
  line, a
  blank line inside a docstring and a `# ----` divider rule (four or more dashes) separate paragraphs
  rather than joining them, while a rule of `=`, `~`, `*` or `#` is prose; a docstring's own lone
  `"""` line is punctuation; a tag line leaves the count line by line, the other lines of its block
  still counting; PEP 723 lines are punctuation only between `# /// script` and the closing `# ///`;
  a line counts as its stripped length over 120 characters, rounded up, so a paragraph packed onto
  one long line counts by its length (owner, 2026-10-21: "6: c", asked "Count a long comment line as
  several?", option (c) "the same at 120 characters"); and a trailing comment annotates its own code
  line, so it never starts a block.
  `tests_scripts/test_comment_block_cap.py` gates exactly that at zero for Python and shell in all
  eight scopes and the generated device modules, and checks every file's header is there: a module
  docstring in Python (ruff's D100/D104 fail a module or package without one too), a comment after the
  shebang in shell, a leading comment in JS, CSS, YAML, TOML and INI, a comment after the doctype in
  `html/index.html`. JS (JSDoc `@param`/`@returns`
  continuation lines not being commentary), CSS and the config files keep their content cap
  review-enforced (a titled `# ---- X ----` banner counts as a prose line; only a bare rule is
  punctuation).
- **Legacy parity means no lost function.** When `src/` or generated code behaves differently from
  the legacy firmware, the difference counts as explained only as an adaptation to the promoted scheme
  with no functional loss, or as a recorded owner decision — a session agent's own decision does not
  count (owner, 2026-09-26: "It's really about functional losses which were forgotten along the way.
  2. Explained: adapted to our promoted scheme without functional losses, recorded decisions I took
  (not the session agent)."). Parity is with legacy's evident intent: where legacy code defeats its
  own intent through a bug, the intent is the requirement and the bug a legacy defect (owner,
  2026-09-26: "The basis was intended as I described and your finding was a bug in that code, not a
  contradiction."). When changing a sensor driver's behavior, verify against the legacy driver's own
  actually-proven field behavior, not just judged correct against internal code-review logic in
  isolation (owner, 2026-07-22, `110f3db`, paraphrase); the owner holds every unit, so a difference is
  weighed by its function, never by an unreachable fleet (owner, 2026-09-26). Where a legacy driver
  proved nothing in service — the ISL29125's only ran a smoke test — parity is with its evident intent
  wherever the owner's list does not decide (SPECIFICATION.md M.1).
- **Workflow for substantial work** (owner, 2026-09-26: 'superseded by the workflow description
  recorded in this session earlier, but quite close to option a'; paraphrase of the workflow
  recorded 2026-09-25/26): research and cross-check first — code, docs, datasheets, external
  sources, harvest (owner, 2026-09-25: 'cross-check them … very important with external sources like
  repos, documentation, datasheets'); owner questions only at requirement recording and in a
  consolidation run, never during execution (owner, 2026-09-25: 'at the recording of the
  requirements … or at the pre-work consolidation and extension run'); tests first, then the
  implementation, then coverage tests; a 'pause' is a self-set sync point — commit, push, the full
  local suite at both GC stages, CI green watched through event hooks only, a status note — not a
  wait for the owner (owner, 2026-09-25; owner, 2026-09-26: 'stop timed checks. Do hooks only.'); no
  owner stop-points inside a unit, the report comes at its end (owner, 2026-09-26); an unforeseen
  decision during execution is never asked: take the more conservative, more easily reversible
  option grounded in sources, and log it as decided on the owner's behalf for review; hardware and
  out-of-scope items are parked (owner, 2026-09-25); an apparent contradiction with an owner
  requirement is a fine-tuning question, not a conflict (owner, 2026-09-25: 'they surely are not.
  Such cases always mean that there is a topic to be fine tuned'); a CI failure is a flake only if
  the provider confirms an outage and one re-run with no code change passes (owner, 2026-09-25: 'Do
  not ignore any test or run failures').
- **A failing test is a regression to fix; a test changes only mechanically, never in its goal**
  (owner, 2026-09-25: "So if any test fails, fix the regression and do not try to work around." and
  "Adapting tests to firmware changes is only allowed for mechanical corrections, but not for
  changing the actual test goal."). An expectation is corrected only where datasheet or
  specification proof shows it pinned a defect, together with a regression test for the correct
  behaviour: SPECIFICATION.md E.2.2.
- **Every runner ends with the same summary block** — one PASS/FAIL line, its counts, the failures
  named and the exit code (owner, 2026-09-25; SPECIFICATION.md E.10) — and a gate's verdict is read
  from its exit status or that block, never from a truncated view of its output such as `| tail`; a
  missing or empty verdict is a failure (agent, 2026-09-24).
- **Closing a piece of work** (owner, 2026-09-26, on the pre-merge instructions: "The examples
  contain general project style and quality requirements, so they should be treated as one essential
  part of the big picture - and of course live on in the project docs, but depending on which scope,
  a significant portion will land in the specifications"): its temporary files — communication
  files, temp storage, session-limited items, session-only test code — are persisted to their single
  source of truth, crosslinked, checked for staleness, then removed completely; every issue it opened
  is closed, solved first by reasoning, project rules and standards, similar solutions in the project
  and research (repos, forums, docs); and every agreed-but-deferred item whose trigger is met is swept
  in and done. The quality bar and the test standard it closes against are SPECIFICATION.md Part D
  (D.12 for unit tests) and Part E; an owner question takes the decision-records rule's form (4).
- **Work split across subagents: small blocks, fresh agents** (owner, 2026-10-20). The question
  (owner, 2026-10-20): a week's measured cost was about 81 % agents re-reading their own long
  conversations, mostly from single assignments of 100-320 turns; proposed smaller blocks, each a
  fresh agent. The owner's answers: '81% of re-reading really is much, try to improve here as you
  suggested. But don't cut back on quality or depth ever.'; 'Generally, only (if at all) reuse
  agents if their history is directly relevant for their upcoming work. If you decide to reuse an
  agent for such reasons, tell it to compact their context window before starting.'; 'And yes, do
  smaller packing and try to use fresh agents in most cases.'; 'Apply that as a standing rule for
  future work.' So work is packed into blocks of roughly 60-80 tool calls at file-group seams, each
  a fresh agent starting from the previous block's written record and the tree; an agent is reused
  only where its history directly serves the next block, and is told to compact first; a follow-up
  goes to a fresh agent by default. Agents batch independent calls, read a run's exit code and
  summary and every part of its log that is not green in full, read files by site, and wait for a
  run in one blocking call. Nothing here drops a check, a run, a read a step needs or evidence: the
  last block of a piece of work runs its complete checks over all of its files.

## Code quality tooling

- **Config lives in root `pyproject.toml`** (ruff/mypy/pytest/uv, dev-tooling only — the shipped
  code stays frozen-bytecode-only, not restructured into an installable package). Run manually via
  `scripts/lint.sh` (ruff + shellcheck + actionlint + zizmor), `scripts/typecheck.sh` (mypy), and
  `scripts/test.sh` (unit tests, under a real MicroPython Unix-port interpreter — see below and
  SPECIFICATION.md Part E); `lint.sh`/`typecheck.sh` refuse to run outside the synced project venv
  (`scripts/_require_venv.sh`: the venv active, `uv sync --locked --check` clean, every tool resolving
  inside it; `tests_scripts/test_require_venv_sh.py` pins it). **Every tool is a `[dependency-groups] dev` entry, so
  `uv sync` — and therefore `toolchain/setup_toolchain.py env --tier {generic,flash,bench}`, which
  runs it — installs all of them automatically; nothing is installed by hand.** All are **pinned**,
  for the same reason ruff is: `select = ["ALL"]`-style opt-in-to-everything configs turn an
  unpinned upgrade into a hard CI failure on a rule nobody chose.
- **Wired into CI** via `.github/workflows/ci.yml` (GitHub Actions). **Each tool is its own job/
  stage**, so a failure names the tool directly instead of a shared "lint" job going red:
  `lint-and-typecheck` (ruff + mypy), `shellcheck`, `actionlint`, `zizmor`, the `devices` job that derives the device
  matrices from `devices/*.toml`, plus the test/build stages (`unit-tests`, `unit-tests-gc-threshold`, `unit-tests-coverage`, `digital-twin-e2e`,
  `firmware-build-verify`) and the
  web tier. `unit-tests` keeps `needs: lint-and-typecheck` (the standing hang backstop below); the
  other lint stages run in parallel and gate nothing, so one of them failing does not skip the test
  suite. `unit-tests-coverage` is the plain pass's own instrumented sibling, its own job so a coverage
  run's wall-clock cost (roughly the same again) never sits
  on the critical path `digital-twin-e2e`/`firmware-build-verify` wait on. **Its coverage number is
  advisory but its test result is not** (owner, 2026-09-22): it is the only job that runs
  `build-settrace`, so a failure unique to that binary would otherwise go unseen. The three exit codes
  and what CI does with each: SPECIFICATION.md Part E.5.3.
- **`zizmor` audits the GitHub Actions workflows themselves** — `GITHUB_TOKEN` scope, checkout
  credential persistence, action pinning: the one part of the supply chain ruff/mypy can't see.
  Policy config is `.github/zizmor.yml`: `unpinned-uses` has a policy — `actions/*` may be
  tag-pinned, everything third-party is pinned to a commit SHA (never a tag object) with an
  exact-version comment — and `self-repository` is disabled (below); every other audit runs at its
  default.
  Always invoked `--offline`, which skips the two audits needing the GitHub API, so it behaves
  identically in CI, on a dev box, and in the clean-chroot recipe (README.md). **`self-repository` is
  deliberately `disable: true`** — it wants `uses: $/.github/...` (GitHub's July-2026 syntax) and
  actionlint 1.7.12 rejects that as invalid, so the two gates cannot both be satisfied (agent,
  2026-09-10, `bfaf4c6`): re-enable when actionlint accepts `uses: $/…` (checked at each actionlint
  pin bump). **Adding a SHA-pinned third-party action means bumping that SHA by
  hand** — no Dependabot is configured.
- **Scope is eight directories**: `src/`, `tests/`, `digital_twin/`, `buildgen/` (the
  device-TOML-to-firmware-module generator, SPECIFICATION.md Part L.4), `toolchain/`, `scripts/`,
  `tests_scripts/` and `tests_hardware/`, plus the generated `build/generated_src/` in ruff and the
  main mypy pass (`lint.sh` and `typecheck.sh` generate it first, so a finding there is fixed in
  `buildgen/`, never suppressed in the output). A new file in a scope joins ruff and mypy (and, if
  MicroPython-target, the Unix-port tests) from its first commit (agent, 2026-07-22),
  and so does every new generator, validator or host module (owner, 2026-09-10,
  `fc6afbe`: 'add all build scripts to the full CI'). The legacy tree (`legacy/`) is never in any
  lint, type or CI scope (legacy rule above). All eight stay fully clean
  (`tests_scripts/test_lint_type_scopes.py` checks the scopes). mypy runs three passes, because it
  resolves each module name to one file per run: the main `[tool.mypy]` pass over MicroPython-target
  code against the board stubs (`tests_hardware/` only by its `device_scripts/`),
  `digital_twin/typecheck.ini` over the twin and its hardware fakes, and `host_typecheck.ini` over
  the CPython host tooling. Every file excluded from one pass is checked by another, and
  `typecheck.sh` checks `tests/network.py`, `tests_scripts/conftest.py` and
  `tests_hardware/bench/conftest.py` alone after the three: SPECIFICATION.md Part B.15.
- **Unit tests run under a real MicroPython Unix-port interpreter, not pytest/CPython** — the actual
  runtime, not CPython with MicroPython-flavoured stubs (SPECIFICATION.md Part E.1, "Why not
  pytest"). `scripts/test.sh` builds it on first run through `toolchain/setup_toolchain.py`'s
  `setup`, cached under `$PICO_TOOLCHAIN_DIR`, and runs each `tests/test_*.py` file in its own
  process with `tests/microtest.py` as the runner (E.3). The host-side build chain (`scripts/`,
  `toolchain/`, `buildgen/`) and `tests_hardware/`'s host code are CPython, tested by
  `tests_scripts/` under pytest, which `scripts/test.sh` launches first and backgrounds at the reactive
  default (E.1), and linted and type-checked like everything else (owner, 2026-09-10, `fc6afbe`: 'add all build
  scripts to the full CI'), through `host_typecheck.ini`'s pass. `pyproject.toml`'s per-file block
  lists every ruff exemption with its reason, MicroPython-run and host code each in their own group
  (SPECIFICATION.md Part D.6); `tests_scripts/test_ruff_exemptions_live.py` fails on an entry that no
  longer fires.
- **`scripts/test.sh --coverage` reports line coverage and never gates** — no threshold exists
  anywhere and none is planned (agent, 2026-09-25); its test result does gate (SPECIFICATION.md Part
  E.5.3), and the pipeline and its outputs are Part E.5. **Three Unix-port binaries are built**:
  `build-standard`, without `MICROPY_PY_SYS_SETTRACE`, is the rig every plain run uses, and
  `build-settrace`, with it, is `--coverage`'s alone (owner, 2026-09-21); `build-lwip` (owner,
  2026-09-30), the standard variant over loopback lwIP with the firmware's own patched `modlwip.c`
  (B.14.4), runs `tests/lwip_host/` alone. The firmware never carries the settrace flag. Every runner
  asks the binary its flavour through `scripts/_unix_port.sh`, whose `ensure` reruns setup when the
  binary is missing or reports another flavour, the `toolchain-record.json` is missing, or an input
  hash in it differs from this tree's file, so a long-lived toolchain dir rebuilding its Unix ports
  once is not a bug; an allocation figure taken under `--coverage` is inflated 4-5x (Part E.5.2). CI
  runs the instrumented rerun as its own job, `unit-tests-coverage`, since `timeout-minutes` gates a
  whole job and would otherwise cancel a suite that had already passed.
- **A third party's momentary outage must never read as a red test result** (owner, 2026-09-26).
  `uv run` builds the whole `dev` group first, and `actionlint-py` downloads its binary inside its
  own build backend, so one bad response there would fail a lane on a healthy tree. Every CI job
  that syncs runs `scripts/uv_sync_retried.sh` (`uv sync --locked`, three attempts) first — in
  `unit-tests` as the toolchain action's first step, ahead of `scripts/test.sh` — every hardware
  runner runs it before its hardware step, and `setup_toolchain.py`'s `run_retried()` matches it.
  Don't simplify the retry away; a test lane red with no test named in its summary is read from the
  `uv`/build output first.
- **Standing backstop: hanging tests are never allowed.** `scripts/test.sh`/`ci.yml` enforce a
  per-file `timeout`+retry, `stdbuf -oL -eL` line buffering, and `needs: lint-and-typecheck` job
  sequencing regardless of any specific hang's root cause — keep all three even after a specific
  hang is fixed. The per-file `timeout` sends SIGINT first, which microtest turns into an `ABORT`
  line naming the hung test with its traceback; `--kill-after` stays the hard stop, and a file it
  kills past its timeout (exit 137) is retried like a timeout (124). Only a timeout is retried, twice,
  in every test runner (owner, 2026-10-20: "Simply put, do the consistent rule adaptation to tests
  only and only for those running into timeout."); an event retry keeps its own recorded count
  (SPECIFICATION.md E.3.1's timeout retry rule). **The `needs:` edge is for
  SEQUENCING only — `unit-tests`, `unit-tests-gc-threshold`, `firmware-build-verify` and
  `web-unit-tests` carry `if: ${{ !cancelled() }}` so they still run when the job they follow
  fails.** (agent, 2026-09-10, `6564ccd`) `needs:` alone also
  implies success-gating, which was never chosen here (that job's own comment says the sequencing
  "isn't required" for the hang) and would let a red `lint-and-typecheck` silently skip every Python
  test lane, hiding that the tests never ran. Keep the sequencing; never restore the gating.
  `digital-twin-e2e`, `unit-tests-coverage`, `web-put-matrix` and
  `web-cross-browser-smoke` stay success-gated, each job's comment stating why;
  `tests_scripts/test_ci_workflow.py` fails on an edge that has neither.
- **Known hang cause: any test double for `uart.poller`, or an equivalent fake-stream object, is a
  bounded fake like `_StepPoller`, never backed by a real `select.poll()`.** A real poll watches the
  descriptor a fake's fileno query answers — fd 0, the test's stdin, for a fake answering 0, which
  never turns ready on GitHub Actions runners — so a `timeout_ms=-1` wait hangs forever
  (SPECIFICATION.md F.7). Both machine fakes answer `EINVAL` as rp2 does, and `tests/machine.py` fails
  the test whose real poll queried a fake UART. Don't re-diagnose this symptom as a new code bug.
- **Known hang cause #2: `tests/microtest.py`'s `run()` always ends with `sys.exit()`** (0 on an
  all-pass run, 1 on any failure). MicroPython's asyncio has no parent/child task tracking, so the
  sibling tasks a generated module's task graph spawns stay parked in the file's one task queue, and
  without the forced exit the process hangs after its closing "P/T passed" line (SPECIFICATION.md
  E.3, E.8); keep it.
- **Known segfault cause: a nested `asyncio.run()` while any other task is still parked segfaults
  the MicroPython Unix port**, deterministically and uncatchably, instead of raising CPython's
  `RuntimeError` (mechanism: SPECIFICATION.md Part F.1). **Rule: a test helper that drives a
  coroutine (`tests/_async_harness.py`'s `run()`/`run_timed()`, the one `asyncio.run()` caller in
  `tests/`, and anything calling a `hazard_pair()`-style builder that runs its own setup) must only
  ever be called from synchronous test-function scope, never from inside a coroutine** - build the
  fixture at the top of the test, then pass it into the one coroutine `run()` drives. The harness
  refuses a nested call with a `RuntimeError` naming that fix, and `tests_scripts/test_microtest.py`
  fails on any other `asyncio.run()` in `tests/`. Awaiting a finished task again after its data was
  cleared segfaults the same way (F.1), so the harness's reap and `cancel()` pass over such a task.
  Don't re-diagnose a file that dies with no closing `P/T passed` line, or with `Segmentation fault`
  in a reap, as a memory bug in the code under test.
- **Known intermittent-`MemoryError` cause #2: don't re-diagnose a "heap is locked" `MemoryError` at
  twin shutdown as a project memory bug.** It is a SIGINT that landed inside `gc_collect()`
  (SPECIFICATION.md Part F.6); the `unix_kbd_intr` override (next bullet) closes it in every binary
  this tooling builds, so the twin's heap-unwedge helper was retired (owner, 2026-09-26). If it
  recurs, check the override is applied first; Part F.6 keeps the mechanism and how to restore the
  helper.
- **Known intermittent `digital-twin-e2e` shutdown flake: don't re-diagnose a shutdown-only exit
  code 1 at `gc.threshold=32768` (with or without a garbled traceback) as a new project bug before
  confirming the SIGINT-delivery override is still actually being applied.** The Unix port's default
  SIGINT handling raises from the signal handler and can corrupt VM state;
  `toolchain/micropython_overrides.py`'s `apply_unix_kbd_intr_override()` forces the deferred path
  (`MICROPY_ASYNC_KBD_INTR=0`) for every build (SPECIFICATION.md Part B.14: the mechanism and the
  re-verification checklist for a MicroPython version bump). A twin that serves on past its SIGINT
  is a different MicroPython defect, which is why twins end through their stop file (Part F.6.1).
- **Known intermittent-`MemoryError` cause: every test file runs with an explicit `-X heapsize`**, a
  Unix-port test-harness setting unrelated to the rp2040's RAM: each file is one process sharing one
  heap, and its heaviest tests build whole generated object graphs (SPECIFICATION.md Part E.3.1 the
  reason, Part N's `l1.unix_heapsize` row the value). Don't re-diagnose a flaky `MemoryError` in a
  heavy test file as a new code bug before checking the flag is still in place — and don't raise it
  as a fix; a per-file heap override hiding a symptom is never used (agent, 2026-09-17; kept as
  agent design by the owner, 2026-09-26).
- **Local test runs pin `$TZ=UTC` (Unix port only).** The Unix port's `time.mktime()` reads its
  input as local time through the host's libc and `$TZ`, unlike rp2's TZ-agnostic epoch arithmetic,
  so `src/`'s `time.mktime(time.gmtime())` idiom round-trips only under UTC; `scripts/test.sh`
  exports it. Don't diagnose a consistent (not intermittent) failure in a live-clock assertion as a
  new code bug before checking the runner's `$TZ`.
- **Two suites that both bind real ports run one after the other, never together.** `scripts/test.sh`'s
  MicroPython tier and `npm test`'s live-tier twins both serve real HTTP and a real port-53 DNS
  server, so run together a test reaches the *other* suite's listener: a 200/404 mix
  (`AssertionError: [200, 404, 200, 404, 'rejected', 'rejected']`), an empty body, a 404 for a page
  that plainly exists — what a broken static mount or a bad merge would produce; don't re-diagnose
  it as either. A per-port lock enforces it (`scripts/_port_lock.sh`, `tests_js/_port_lock.js`): an
  unrelated second suite fails at once with `port <port> is held by <runner> (pid <pid>) - run the
  suites one after the other (CLAUDE.md)`. Which runner holds which port, the owner chain and the
  lock file: SPECIFICATION.md Part E.1. `scripts/test.sh`'s own backgrounded `tests_scripts/`
  tier overlaps it safely: its HTTP ports are ephemeral, and a booted twin's captive DNS on 53
  degrades to "not connected" rather than failing the boot.
- **Tuned values carry `@tunable` and a Part N row, both changed in the same change** (owner,
  2026-09-25: 'updated on changing parameters or whenever such parameter is added').
- **`ruff format` is not used anywhere** (agent, 2026-07-13) — line breaks are hand-chosen throughout this
  codebase; `line-length = 320` (ruff's own ceiling) plus an `E501` ignore keep this a non-issue even
  if `format` is ever run by accident. Lint rule selection is `select = ["ALL"]` — every non-preview
  rule ruff ships, narrowed only by an explicitly justified `ignore` list (`pyproject.toml`'s
  `[tool.ruff.lint]`, where each exclusion carries its own reasoning). That opt-in-to-everything
  choice is exactly why ruff is pinned: an unpinned upgrade would hard-fail CI on a rule nobody
  chose.
- **Bare `except:` (E722) stays enabled** (owner, 2026-07-13, `c0dfd20`, paraphrase: flag bare
  excepts rather than silence them): every one it flagged has been fixed, none remains in any lint
  scope, and the rule keeps it that way.
- **Union type annotations: always PEP 604 `X | Y` (and `X | None`), never `typing.Union[...]`.**
  MicroPython parses but never evaluates annotation expressions (tested against the pinned Unix-port
  interpreter: an unquoted, executed `int | None` works with no import needed), so `|` is safe on
  every target, while `typing.Union` needs `from typing import Union`, which raises `ImportError`
  on-device wherever no `TYPE_CHECKING` guard covers it. ruff's `UP007` rule (part of the enabled `UP`
  selection) flags every `Union[...]` as a finding. The `Union[...]` usages that exist are confined to
  the legacy tree (`legacy/`; reference-only, never linted) — leave those alone, and don't drive-by
  "fix" `Union` → `|` in a file you're not otherwise promoting/refactoring.
- **mypy runs full `--strict` plus `disallow_any_explicit`, minus exactly one flag.** All three
  configs set `strict = true`
  (spelled that way, not as the individual flags, so a deliberate mypy version bump surfaces any
  newly added strict check as a finding to decide on), plus `no_implicit_optional`/`warn_unreachable`
  which aren't part of `--strict`, `disallow_any_explicit` (owner, 2026-09-28: "do it in this audit";
  each pass's shrinking per-module baseline is BACKLOG.md's open item), and the `ignore-without-code`
  error code in all three, so a bare
  `# type: ignore` is itself an error. **The one exemption is `no_implicit_reexport`, and only in the
  `[tool.mypy]` pass** — `tests/` mocks by reassigning a module's imported names
  (`asy_ntp_client.time = FakeTime()`, `asy_udp_socket.socket = ...`), which is the project's actual
  mocking mechanism since MicroPython has no `unittest.mock`; enforcing the flag would mean an inline
  ignore at every such site in `tests/` or `__all__`/re-export aliases in shipped `src/` modules
  purely
  to satisfy a test-only check. `digital_twin/typecheck.ini` and `host_typecheck.ini` both run
  `--strict` with that flag ON. The `assignment` error code is not disabled.
- **`method-assign` stays globally enabled, and `src/` must never suppress it** (owner,
  2026-09-10). `tests/` and `digital_twin/` reassign methods to mock them — that IS the project's
  mocking mechanism, MicroPython having no `unittest.mock` — and each such site carries its own
  inline `# type: ignore[method-assign]` rather than a central `[[tool.mypy.overrides]]`
  exemption, deliberately: a scope-wide override would stop marking the individual real sites.
  Shipped firmware code has no business reassigning a method at all, so a suppression appearing in
  `src/` is the defect, not the type error. mypy itself cannot express that rule (it only ever sees
  a suppression already written), so `scripts/lint.sh` enforces it with a grep guard that fails the
  lint gate, and fails it too when grep cannot search (exit 2), so a guard that did not look never
  reads as clean. `src/` carries zero of these today; keep it that way rather than silencing a finding.
- **`# noqa: E402` belongs only on files with a real statement before their imports.** Several
  `tests/` files must set `sys.path` before importing the module under test, and ruff **exempts
  `sys.path` manipulation from E402 outright** (verified directly, 2026-09-10) — so those files
  need no suppression. What does trigger it is any *other* statement first, e.g.
  `test_digital_twin_sensortask_integration.py`'s `patch_asy_udp_socket_for_unix_port()` call, and
  only those files carry the `# noqa`. This is not an inconsistency to tidy up: adding the
  suppression to a `sys.path`-only file makes `RUF100` (unused-noqa, live via `select = ["ALL"]`)
  fail the lint gate, so the two groups genuinely have to differ.
- **A merge resolved by taking one side wholesale hides test/source mismatches — run every tier
  after it.** An auto-merged test file next to an `--ours`-resolved source file raises no conflict,
  then fails against source that lacks the feature it pins.
- **A merge that touches `uv.lock` can silently bypass the tool pins — always re-verify after
  one.** Git merges the lock line by line, so a pinning branch and a version-refreshing branch can
  leave one side's `specifier = "=="` next to the other side's resolved `[[package]] version`;
  `uv lock --check` compares only `pyproject.toml` with the lock's manifest and exits 0, and
  `uv sync` installs the resolved version the pin forbids. **After any merge that touches
  `uv.lock`, run `uv sync` and check the installed `ruff --version`/`mypy --version` against
  `pyproject.toml`'s pins**, re-running `uv lock` if they disagree; `tests_scripts/test_tool_pins.py`
  fails on exactly that disagreement.
- **MicroPython stubs**: `micropython-rp2-rpi_pico_w-stubs`, which pulls in
  `micropython-stdlib-stubs` (PyPI, published by
  [`josverl/micropython-stubs`](https://github.com/josverl/micropython-stubs)). **The post-releases
  are pinned exactly in `toolchain/versions.toml`'s `[stubs]` (`board`, `stdlib`) and move with
  every MicroPython bump** (owner, 2026-10-02, paraphrase: the stub version moves with every
  MicroPython bump, enforced by a check): `scripts/typecheck.sh` refuses a pin whose X.Y.Z is not
  `[micropython] ref`'s or a `ref` that isn't a plain `vX.Y.Z` tag, fails by name when a pinned
  release does not exist upstream, and records the installed versions in `typings/.stub-spec` (a
  missing or different record wipes `typings/` first). They install into `typings/` (gitignored),
  not the dev group: they replace mypy's typeshed (`[tool.mypy]`'s `custom_typeshed_dir`), which
  would break type-checking of the venv's own tools. Keep that isolation.
- **`scripts/typecheck.sh`'s combined `mypy src tests` run resolves every `from machine import X`
  to `tests/machine.py`'s fake, not the `typings/machine.pyi` board stub.** The stub's `Timer` lacks
  the zero-argument constructor rp2 has, so a `src`-only (or standalone
  `tests_hardware/device_scripts`) run reports `call-overload` at every bare `Timer()`: a gap in the
  third-party stubs, not a driver bug, listed with its removal trigger in SPECIFICATION.md Part B.15.
  The 1.29 stub's `I2C.deinit()`/`SPI.deinit()` are silent no-ops on rp2 (Part F.5.1).
- **`scripts/typecheck.sh` repairs the stub package's two verified defects after installing it** —
  `asyncio.Future`, privatised to `_Future` with the `asyncio/futures.pyi` that re-exported it
  dropped, and `builtins.pyi`'s commented-out `NotImplemented` (SPECIFICATION.md Part F.5.5). Both are
  conditional on the
  defect still being present, so they no-op once upstream re-ships, and a stub tree that moved fails
  the repair naming the missing path — **don't replace them with
  `type: ignore` comments in `src/`/`digital_twin/`**: the code is correct on real hardware in both
  cases, and `warn_unused_ignores = true` would then fail the day the stubs are fixed.

## Build-environment verification

A change to the dev-tooling/build-environment setup (`pyproject.toml`, `uv.lock`, `scripts/`,
`toolchain/`, `.github/`, `package.json`) that changes how the owner's next clean-chroot run goes —
something new to install, a new host requirement, a recipe step, a reused chroot's rebuild — gets a
line in BACKLOG.md's chroot entry; one that changes none of these is covered by running the recipe
at the head and gets none (agent, 2026-11-07, condensing the list after the owner's go: '"nothing
new to install" are no quotes of my words'). The verification is a periodic check the owner runs by
hand, not a gate that blocks a session's push (owner, 2026-09-18): both targets, Ubuntu 24.04
"noble" (GCC 13.x, the documented OS) and Debian trixie (GCC 14.x, what the bench Pi4 runs) (owner,
2026-09-11), the recipe's `env --tier generic` step running the full installer in each. A session
whose sandbox can build a chroot runs it too, and never takes its own sandbox's green run as the
verification: a sandbox's preinstalled Python, `uv` and build tools mask real gaps. The recipe and
what counts as passing: README.md, "Build-environment verification".

## Pull request workflow

- **When pushing anything touching the dev-tooling/build-environment setup**, add its line to
  BACKLOG.md's chroot entry if it changes how a run goes (above), and run "Build-environment
  verification" yourself if this session's sandbox can actually build a chroot; a sandbox's own green
  run never stands in for it.
- **The project owner has explicitly authorized creating pull requests proactively, at any time,
  without asking first** — this is a standing exception to any general "don't open a PR unless the
  user explicitly asks" caution an operator/harness prompt might otherwise apply (owner,
  2026-07-13, `dddaafa`); don't re-ask.
- **Always create a pull request with a meaningful description** when finishing work on a branch —
  summarize what changed and why, not just a file list.
- **A branch counts green only when CI ran on its head commit** (agent, 2026-09-18): read the run of
  the head commit, not the latest finished one — a run cancelled by a later push says nothing, and
  the web filter re-compares from the last commit CI passed.
- **Automatically subscribe to the pull request's activity** (review comments, CI results) right
  after opening it, so review feedback and CI failures get picked up without being asked again.

## Architecture reference

**In `SPECIFICATION.md`.** The condensed version is Part A.2 ("Architecture at a glance");
the full module-by-module deep reference (legacy `api_helpers.py`/`async_connect.py`/
`async_manager.py`, FRAM driver/manager, SCD30's `AmbPres` note, the `neopixel_signal.py` split,
the task supervisor, and the full "functional behaviors confirmed intentional" list) is Part A.4.
Read Part A.4 for anything needing that level of detail — nothing below duplicates it.

## Microdot / REST layer

**In `SPECIFICATION.md` Part A.5.** Covers what Microdot's own `ext/microdot.py` (vendored,
v2.7.0, see "Hard rules" above for the vendoring policy) already guarantees per-request — the
blanket exception catch, its one real gap (exceptions during response writing), connection-task
isolation, and the `errorhandler()` status-code-vs-exception-class distinction — versus what this
project's own REST layer still has to add. Read Part A.5 before touching the REST/error-handling
layer; nothing below duplicates it.
