# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

## Refactor targets not yet done

- **`boot_entry/` isn't in `pyproject.toml`'s lint/typecheck `files` scope yet.** Step 1 added
  `boot_entry/wozi_boot.py` (the real, deliberately-separate blocking-import firmware entry point
  for `src/sensortask_wozi.py` - see that module's own docstring and `FINAL_WIRING_PLAN.md`'s Step
  1 refined plan). Manually confirmed clean today (`ruff check boot_entry/wozi_boot.py` and
  `mypy boot_entry/wozi_boot.py --config-file pyproject.toml` both pass under the existing config),
  but it's not part of `scripts/lint.sh`/`scripts/typecheck.sh`/CI's default scan until
  `pyproject.toml`'s `files`/scan scope is extended to include it - deliberately not done as part
  of this same pass, since any `pyproject.toml` change needs CLAUDE.md's "Pre-push verification"
  chroot recipe run first, and one three-line file didn't seem to warrant that on its own. Fold
  this in next time `pyproject.toml` is touched for another reason anyway (same framing as the
  already-tracked `improved-quality/microdot.py` exclude-entry cleanup below).
- **Bare `except:` is forbidden in refactored code** (`except Exception:` or narrower required).
  Ruff's E722 is already enabled, so existing bare excepts in `improved-quality/` show as tracked
  findings rather than being silenced — eliminating them is still real refactor work.
- **No CI firmware-build stage yet.** Blocked on genericizing `build-*.sh`'s hardcoded
  `/home/nico/rpi_pico/...` path and the `py-include` symlink (see "Deferred" below) — needs to
  land before/alongside this.
- **Mypy shall be configured to disallow `Any` types** (owner-specified, not yet implemented). The
  closest existing option is `disallow_any_explicit`; `pyproject.toml` deliberately stops short of
  it and the other `--strict`-only checks today. Blast-radius check (re-run, not stale): `Any`
  appears ~190 times across 47 files in `src/`/`tests/` today. A large share is still test-file
  monkeypatch/wrapper classes duck-typing a real MicroPython object rather than reimplementing its
  interface, but a real, growing share is now legitimate `src/`-side usage too (`print_log.py`'s
  variadic logging methods, `config_manager.py`'s generic value-checking helpers, opaque
  `ticks_ms()`-typed values) — turning this on will need both a typing strategy for the test
  wrappers (e.g. `Protocol` classes matching just the overridden methods, plus `__getattr__`
  delegation) and a decision on how to type the genuinely-variadic/opaque `src/` cases, not just a
  flag flip.
- **FRAM bus-recovery is only partially wired up.** `asy_fram_driver.py`'s own `src/` promotion
  added device-identification/write-protect verification, but there's still no periodic/triggered
  re-probe policy — `verify_present()` and `set_write_protected()` have zero callers anywhere;
  `get_write_protected()` has exactly one, `_write()`'s own write-protection gate, which isn't a
  re-probe of anything — and no task supervisor for FRAM specifically. Whoever wires this up must wrap
  the calls in the same `try/except Exception` discipline this file's other methods already use —
  `asy_fram_driver.py` doesn't catch its own inherited `RuntimeError` path on these three itself.
- **Every deliberate system reset (reboot, bootloader entry, or a deliberate watchdog-starve
  give-up) must pause FRAM operations first and give it a brief wait before the reset actually
  happens** — a real risk (mid-write/mid-read power loss, MB85RS64V reads are destructively
  read internally per `SPECIFICATION.md` Part A.4) that a reset triggered while a FRAM transaction is
  in flight could corrupt data, same class of concern as the dual-copy/status-byte design
  `asy_fram_manager.py` already guards against for power loss but not specifically for a
  self-triggered reset racing an in-progress transaction. Owner-flagged as important for the final
  wiring-up of this refactor's task/reset plumbing, likely needing rework across several files, not
  just one. **Current state, confirmed by reading `system_service.py` directly**: `_reboot()`
  (backing both `reboot_system()`/`reboot_bootloader()`) already calls `self.storage_pause(True)`
  before arming the `_RESET_DELAY`-second (4s) delayed reset timer, and already does so before the
  `_force_watchdog_starve` fallback too (armed when the reset timer itself can't be allocated) - so
  the one existing deliberate-reset path already pauses-then-waits. Confirmed via grep that
  `machine.reset()`/`machine.bootloader()`/`WDT()` have no other call site anywhere in `src/` or
  `improved-quality/` today. What's still open: (1) explicitly verifying this is genuinely
  sufficient "wait" (the `_RESET_DELAY` timer path is clearly bounded; the watchdog-starve path's
  effective wait is just however long is left before the 8s-capped `WDT` fires on its own, not an
  explicit deliberate pause - worth confirming that's actually enough margin for FRAM's own
  in-flight transaction time), and (2) making sure this invariant is *actively preserved*, not just
  true by chance, as more of the refactor's task/reset wiring lands - a future reset/reboot call
  site added anywhere other than through `SystemService._reboot()` would silently reintroduce the
  gap.
- **No standardized timeout/cancellation mechanism yet for blocking calls that genuinely can be
  timeout-wrapped** (FRAM SPI transactions, `src/asy_udp_socket.py`'s own `select.poll`-driven
  `ready()`/`write_and_recvfrom()` — anything that isn't a raw blocking `machine.I2C` call
  mid-transaction, which can't be interrupted regardless; see CLAUDE.md's "wedged I2C bus" hard
  rule for why that case is different and already decided, and why `socket.getaddrinfo()` turned
  out to belong in the *can't* bucket instead and is gone from this codebase entirely now). Each
  remaining call currently uses its own bespoke approach rather than one consistent mechanism
  applied everywhere.
- **Bus concurrency (`asyncio.Lock` + `async with`) needs a coverage audit** — no gaps, no
  deadlock/starvation. The `*_DeviceSession(Lockable)` pattern (an outer per-sensor lock around a
  whole write-then-read transaction, `asyncio.sleep(0)` yield between phases) is the pattern to
  verify/extend, not start from scratch. (The one concrete gap this audit had already turned up —
  SCD30's low-level getter/setter forwards not logging via `self.pr.err_s()`, unlike BMP3xx's — is
  now fixed; see `SPECIFICATION.md` Part C.7 for the settled forward-logging convention every driver
  now follows. The broader "no gaps, no deadlock/starvation" audit itself is still open.)
- **`SCD30_Reader.get_dict_cfg()` (entirely) and three of `BMP3xx_Reader.get_dict_cfg()`'s fields
  (`PressOvers`/`TempOvers`/`FiltCoeff`) can return a torn read across fields.** Both go through
  `base_classes.py`'s `_get_dict_cfg(..., callback=...)` live-hardware-readback path, which `await`s
  a real I2C transaction *between* reading individual fields rather than snapshotting all of them at
  once — if a concurrent config write (`_set_dict_cfg`/`ConfigManager.write_config()`) lands in that
  window, the one returned dict can mix pre-write and post-write values across fields. Every other
  `get_dict_cfg()`/`get_dict_data()`/`get_error_counter()` call in the codebase is safe by
  construction (no `await` in the middle of building the returned dict, so MicroPython's
  cooperative/non-preemptive scheduling already makes the snapshot atomic) — this is the one place
  that isn't. Found while checking GET-response copy-safety for the new REST endpoint design
  (`FINAL_WIRING_PLAN.md`'s Step 2 "Endpoint design" subsection); not a reference/aliasing bug (each
  individual field value is still a fresh read, never a stale pointer into mutable state), and not
  introduced by that design — pre-existing in both drivers today. No fix designed yet (candidates:
  hold each driver's own bus/device lock across the whole `get_dict_cfg()` call, or snapshot all
  live fields with a single batched read before building the dict) — flagged for whoever picks this
  up, not scheduled.
- **Common driver error classes across sensors — future direction, not designed or implemented
  yet.** Each driver currently defines and reports its own `errno`/`wrnno` values independently
  (see `SPECIFICATION.md` Part C.7); the one exception is `errno=10` ("initial setup failed"), which
  all three drivers already use for the same situation by independent convergence rather than by
  any enforced scheme. Project owner's stated direction: keep per-driver definition/reporting (not
  a single shared enum), but predefine a small set of common error *classes* so the same number
  means the same or an equivalent condition across different drivers, beyond just the one
  already-consistent case. No scheme (numbering ranges, category list, how a driver opts in)
  designed yet.
- **The task-supervisor error-budget counter** is behaviorally correct and intentional as designed,
  but flagged by the owner as implementable more efficiently — worth a cleaner implementation in
  the refactor without changing observed behavior. (Neopixel warning-flash sequencing was the other
  half of this item - resolved by the `src/asy_neopixel_driver.py`/`src/asy_notification_service.py`
  promotion, see `SPECIFICATION.md` Part A.4.)
- **No `@app.errorhandler` registrations exist anywhere yet** (confirmed: neither
  `improved-quality/sensortask-wozi.py` nor the deployed `python/CommonDrivers/`-based app
  registers any). See `SPECIFICATION.md` Part A.5 for what Microdot itself already
  guarantees (every route-handler exception, including `MemoryError`, is already caught per-request
  and can't crash the server) versus what's still missing at our own layer. The base-class/
  `api_response.py` setter+response-envelope consolidation this depended on is now done (see
  `SPECIFICATION.md` Part C.5) — `handle_set_cmd()` already provides its own defense-in-depth
  try/except around one endpoint's dispatch, returning the consolidated `{"res": "ERR", ...}` shape
  via `make_response()`. What's still missing is wiring an actual `@app.errorhandler` registration
  into the real, live Microdot app in `improved-quality/sensortask-wozi.py` — out of scope for this
  pass under CLAUDE.md's hard rule on editing `improved-quality/` source without a scoped,
  project-owner-authorized exception. Concrete work once that wiring pass happens:
  - A catch-all `@app.errorhandler(Exception)` that logs via our own `pr.err_s(...)` (Microdot's own
    default `print_exception()` never reaches `PrintLog`/FRAM) and returns the consolidated
    `{"res": "ERR", ...}` reply shape — the single seam where "any internal or external error must
    be answered with an appropriate REST reply" actually gets satisfied for the whole app, not
    per-handler.
  - Explicit handlers for at least 400/404/405/413/500 so Microdot's bare default text bodies
    (`'Not found', 404` etc.) never reach a client unshaped.
  - A decision on whether route handlers use `abort()`/`HTTPException` (resolved via the
    status-code error-handler path) or always return our own error dict directly — mixing both
    without care means two different reply shapes for the same kind of error.
  - Any registered handler must itself be defensive: a second exception raised inside an error
    handler is swallowed silently by Microdot (falls back to a bare generic 500) rather than
    crashing, but that also means a bug in the handler silently loses whatever it was trying to do
    (e.g. the logging call itself).
  - Whatever a route handler returns must stay JSON-serializable end to end (ties to the
    native-JSON-types rework already in progress) — a non-serializable value fails inside
    `Response.__init__`'s `json.dumps()`, which Microdot still contains (falls into the same
    generic-500 path) but silently masks the real cause as a generic error unless our own handler
    logs it.
- **Microdot hardening design (webserver robustness) — implemented.** `src/asy_webserver_service.py`
  (FINAL_WIRING_PLAN.md's Step 2) implements this design in full, including the 100+-cycle soak test
  and the real wiring into `src/sensortask_wozi.py`'s `build_system()` — see that doc's own Step 2
  status updates for what landed and the two real findings made along the way (the
  `asyncio.TimeoutError`-isn't-an-`OSError` correction, and the `conn`/`ntp` `cfgmgr.setup()` gap).
  The rest of this entry is kept as the original design record/incident writeup, not because any of
  it is still open.

  Triggered
  by a real incident: on 2026-08-03, `sensortask-arzi`/`sensortask-neu` (legacy, pre-refactor) both
  went permanently REST-API-unreachable for hours with the watchdog never firing, root-caused to
  vendored `python/CommonDrivers/microdot.py`'s `Request.create()`/`Response.write()` having zero
  read/write timeout anywhere on the per-connection stream (`stream.readline()`/`readexactly()`/
  `awrite()`/`drain()`) — a client that opens a TCP connection and then goes silent (matches that
  day's independently-observed network flakiness) leaves that connection's task parked on an `await`
  forever: alive from asyncio's point of view, invisible to `start_and_check_tasks()`'s `.done()`
  check, costing zero CPU, so the main loop/watchdog-feed keeps running fine while the wedged
  connection permanently occupies one of RP2040/lwIP's small fixed socket-pool slots. Confirmed
  against live upstream `miguelgrinberg/microdot` (`main` branch) this isn't a vendoring gap fixable
  by upgrading: current Microdot has zero "timeout" occurrences anywhere in `microdot.py`. Its
  changelog shows a "socket read timeout to abort incomplete requests" *did* exist (v1.2.2,
  2023-03-03; refined v1.3.1) but predates v2.0.0's (2023-12-22) "asyncio is now the core
  implementation" redesign and was never reimplemented for the asyncio server — a standing upstream
  gap for 2+ years, not something a version bump resolves. `improved-quality/sensortask-wozi.py` has
  the identical unwrapped `app.start_server()` call, so this isn't fixed on the refactor branch
  either yet.

  **Decided (owner, 2026-08-03) — don't re-litigate without new information:**
  - Scope: **refactor-only** (`src/`, `improved-quality/`, future `sensortask-*.py`). Legacy
    `python/CommonDrivers/` stays untouched under the standing "don't edit without authorization"
    rule — accepted as residual risk until the refactor replaces it, *not* proposed for a scoped
    backport despite today's real outage.
  - Detection signal: **per-connection open-count leak tracking only** — no active self-test/loopback
    probe, no unconditional periodic restart. Both were offered and explicitly not chosen — don't
    re-add either as "obviously also worth having" without asking again.
  - Timeout sizing: **generous**, tuned around worst-case legitimate conditions (weak WiFi, larger
    page transfers) — a wedged connection may tie up its socket a while longer before reclaim, but a
    slow legitimate client is never the one getting cut off.
  - Tunables (per-call timeout, the outer per-connection wall-clock cap below, concurrent-connection
    ceiling): **hardcoded internal constants, not REST/config-exposed** — same treatment as `WDT`
    timeout / `_TASK_FAIL_MAX` today, so nothing (including a REST caller) can accidentally weaken
    the safety net. Supplied at construction time, grouped with `src/sensortask_wozi.py`'s other
    fixed hardware-related constants (see `FINAL_WIRING_PLAN.md`'s Step 2 for the exact placement).

  **Defense shape — revised (owner, per-connection-only, supersedes the original "layered" plan
  below): no whole-server-restart mechanism.** The original plan paired a per-connection timeout
  (primary defense) with a whole-server restart as backstop for anything the per-connection layer
  might miss — e.g. a hang inside Microdot's own routing/dispatch logic, not just stream I/O.
  Resolved directly, not just asserted: adding one **outer** `asyncio.wait_for()` wrapping the
  *entire* per-connection `handle_request()` call (not just the individual stream reads/writes)
  already covers that exact gap — `dispatch_request()` sits inside `handle_request()`, so a hang
  there is now caught the same way a silent/Slowloris-paced client is. The one failure class neither
  the per-connection cap nor the old whole-server restart can actually help with is a truly
  synchronous, no-`await` hardware-level stall — CLAUDE.md's already-settled I2C-wedge policy ("the
  hardware watchdog is the accepted backstop, not a software fix to chase") applies here unchanged:
  if the event loop itself stalls, whatever task would have driven a threshold-triggered restart
  stalls with it, so the old mechanism was never really a working backstop for that case either.
  Net: **reject-when-full** (silently refuse a new connection at the open-count ceiling, no accept)
  plus **two layers of per-connection timeout** (per-call stream timeouts, and the new outer cap) is
  the whole scheme — the webserver's own task is still registered as an ordinary task in
  `start_and_check_tasks()` (step 4 below, unchanged), so it still gets the existing generic
  supervisor's restart-then-escalate treatment for the one thing that actually can end it (its own
  task genuinely dying), the same as every other module — nothing bespoke on top of that. Full
  derivation and the connection-count ceiling's new role as the reject-when-full threshold (not a
  restart threshold): `FINAL_WIRING_PLAN.md`'s Step 2, "Owner decisions on the 10 questions," #1.

  **Design sketch (composition, not subclassing or editing Microdot):**
  1. Don't call `app.start_server()`/`app.shutdown()` at all. Call `asyncio.start_server()` ourselves
     with our own `serve(reader, writer)` callback (the same primitive Microdot's own `start_server()`
     uses internally), keeping the returned `Server` object under our control for restart. This keeps
     the *only* real coupling point to Microdot's internals down to one clearly-scoped call —
     `await app.handle_request(wrapped_reader, wrapped_writer)` — `app` itself (the `Microdot()`
     instance with all its `@app.get/put/...`-registered routes) is reused unchanged across restarts,
     since routes live in `app.url_map`, independent of the transport object being replaced.
  2. Before calling `handle_request`, wrap the real `reader`/`writer` in a thin proxy (our own class)
     forwarding every method Microdot's code actually calls on them (`readline`, `readexactly`,
     `awrite`, `aclose`, `close`, `wait_closed`, `get_extra_info` — enumerate exhaustively by grepping
     `python/CommonDrivers/microdot.py` for every `reader.`/`writer.`/`stream.` call site, not
     guessed), each wrapped in its own `asyncio.wait_for(..., _CONN_TIMEOUT_S)`. A timeout raises an
     ordinary exception from inside the proxy call (not a cancellation reaching into Microdot's own
     code) — Microdot's existing `except Exception as exc: print_exception(exc)` around
     `Request.create()` already handles this correctly (aborts the request, still runs the normal
     `writer.aclose()` cleanup path), so this deliberately sidesteps needing to know how MicroPython's
     `asyncio.CancelledError` interacts with a broad `except Exception` inside a cancelled task's
     frame, rather than resolving that uncertainty. **Verify before implementing**: confirm on the
     real Unix-port interpreter that `asyncio.wait_for()` wrapping a stream read that never becomes
     ready actually raises `TimeoutError` promptly rather than hanging (should hold — MicroPython's
     stream reads yield through the scheduler's IOQueue, a real coroutine boundary, unlike the
     wedged-I2C case CLAUDE.md already rules out) — this is the one load-bearing runtime-behavior
     assumption the whole design rests on; check it first.
  3. Our `serve()` wrapper increments a `LockedCounter`-style open-connection count on accept,
     decrements it in a `finally` regardless of outcome (timeout, success, exception) — the count must
     never leak even if `handle_request` misbehaves in some new way not anticipated here.
  4. **Reject-when-full, not whole-server restart** (revised — see "Defense shape" above): once the
     open-count sits at/above a ceiling set with real margin below RP2040/lwIP's actual
     concurrent-socket ceiling (**confirmed at 5**, see companion open question below), silently
     decline any further connection — no accept, no response written — until a slot frees. No grace
     period, no threshold-crossing-for-a-duration logic, and no `Server.close()`/restart step at all:
     each already-accepted connection is independently bounded by its own per-call timeouts plus the
     new outer per-connection `wait_for()` (step 2 above, now wrapping the whole `handle_request()`
     call, not just the stream reads/writes it wraps today), so nothing ever needs a whole-server
     action to reclaim. Register this webserver-starter in the *existing* `start_and_check_tasks()`
     task list like any other task regardless — if the task itself ever genuinely dies (not an
     ordinary per-connection reclaim, but e.g. an unhandled exception escaping the accept loop),
     "graceful restart" and "last-resort watchdog escalation" (via
     `task_errors`/`_TASK_FAIL_MAX`/`_force_watchdog_starve`) are already fully handled by
     `system_service.py`'s existing, tested supervisor — no new restart or watchdog-escalation
     machinery needed for that case either.
  5. Soak-test before trusting this in the field: repeated (100s+) start/wedge/reclaim/restart cycles
     under the Unix-port interpreter checking `gc.mem_free()` stays flat, matching this project's
     existing "never trust a resource-lifecycle claim without directly testing it" standard (FRAM
     `LockableBuffer` clamp-then-allocate, `AsyUDPSocket`'s self-healing `_connect()`, etc.). Test
     doubles for the reader/writer must be step-driven fakes, never anything backed by a real
     `select.poll()` — this is exactly the CI-hang class already root-caused and fixed once in
     `test_asy_uart_driver.py` (see "CI hang investigation" above); don't reintroduce it here.
  6. New module follows the project's existing "never raises" convention throughout (see
     `base_classes.py`/`system_service.py` module docstrings) — any failure inside the wrapper itself
     (not just inside Microdot) degrades to logging via `pr.err_s`/`wrn_s` and treating that one
     connection as expendable, never propagates out of the connection task.

  **Confirmed boundary (cross-checked against the concurrent setter-dispatch/`api_response.py` work,
  PR #26, by reading `ext/microdot.py` v2.6.2's actual source, not assumed)**: `handle_request()`'s
  shape is exactly `req = await Request.create(...)` → `res = await self.dispatch_request(req)` →
  `await res.write(writer)` — every unbounded stream read/write (`Request.create()`'s
  `_safe_readline`/`readexactly`, `Response.write()`'s `awrite`) sits strictly *before* or *after*
  `dispatch_request()`, never inside it. `dispatch_request()`'s route-handler invocation only ever
  touches an already-fully-materialized `Request` (headers/body fully read by the time
  `Request.create()` returns) and produces a `Response` with no socket I/O of its own — verified
  directly for `src/api_response.py`'s `parse_cmd_request()`/`handle_set_cmd()` and
  `base_classes.py`'s `_set_dict_cfg()`, none of which touch the transport, so none of this PR's new
  setter-dispatch/response-envelope code is exposed to (or needs to defend against) the incident.
  Two direct payoffs for this design once implementation starts:
  - Step 1's claim that `await app.handle_request(wrapped_reader, wrapped_writer)` is the *only* real
    coupling point to Microdot's internals is now verified, not just architecturally assumed — the
    reader/writer proxy from step 2 is sufficient on its own; no route-handler/`dispatch_request()`-
    level wrapping is ever needed alongside it.
  - `tests/test_setter_microdot_integration.py`'s existing pattern of dispatching via
    `app.dispatch_request(req)` on a hand-built `Request` (bypassing `Request.create()`/
    `handle_request()`/`start_server()` entirely) is the *correct* boundary for testing route-
    handler/business logic, not a coverage gap it should be extended to close — a hang-simulating
    fake stream belongs exclusively to this future module's own step 5 soak test above, never to
    that integration test file.

  **Companion open question this design surfaces — resolved**: the concurrent-socket/TCP-PCB ceiling
  for MicroPython's rp2 port (lwIP-backed) is **5**, from `MEMP_NUM_TCP_PCB`'s default (rp2's own
  `lwipopts_common.h` defines no override for it at the pinned v1.28.0 tag — confirmed by fetching the
  file directly and grepping for the macro, not assumed from general lwIP knowledge; only
  `MEMP_NUM_UDP_PCB` is overridden there). This is the real-margin ceiling the reject-when-full
  threshold in step 4 above must sit comfortably below — see `FINAL_WIRING_PLAN.md`'s Step 2 for where
  this number is actually consumed.

  Module name/location: `src/asy_webserver_service.py`, matching `asy_wifi_service.py`/
  `asy_ntp_client.py`'s naming and the "every module owns its own schema" convention — though per the
  tunable-exposure decision above, this module's own safety constants deliberately have no config
  schema/REST surface.
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
   Addressed during the refactor's final wire-up, not before.
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
4. Does `config_manager.py`'s `write_config()` need long-block-lock-style coordination? **Decided
   by the project owner: no** — a write is fast enough not to matter, and it never happens on its
   own/automatically anyway (only ever triggered by a real user interaction via the REST layer),
   which also matters separately for not wearing out the flash with unnecessary writes. No
   coordination mechanism needed. **Note**: `get_long_block_lock()` itself was already removed
   entirely before this was decided (see CLAUDE.md's "Long-blocking operations" hard rule) — this
   decision doesn't resurrect it.
5. Real-hardware verification gap for `asy_udp_socket.py`/`captive_dns.py`: every UDP-layer claim
   (POLLERR/POLLHUP delivery, truncation, connected-socket source filtering) is verified against the
   MicroPython Unix port's socket implementation, not real rp2/lwIP — no rp2 hardware was available
   to test against. If a deployed unit ever shows UDP behavior diverging from what's
   tested/documented in the driver, this is the first place to look. **Explicitly deferred by the
   project owner**: on-device verification is real future work, not something to chase in the
   current session.
   **Sharper root cause confirmed (Step 5 re-audit session)**: this isn't just an abstract
   "untested on real silicon" gap — it's now confirmed structural. A real, standalone reproduction
   (a fresh `AsyUDPSocket("127.0.0.1", 123)` client against a real local UDP responder, and the raw
   `socket.socket().connect()` call underneath it) showed the MicroPython Unix port's "standard"
   build's `connect()`/`bind()`/`sendto()` reject a plain `(host: str, port: int)` tuple outright
   with `TypeError: object with buffer protocol required` — a known, long-standing Unix-port-only
   quirk (`micropython/micropython#6924`) that `tests/test_asy_udp_socket.py` already found and
   works around in its own test helpers (`make_addr()`/`resolve_addr()`, which pre-resolve via
   `socket.getaddrinfo()` before ever constructing an `AsyUDPSocket`). The real production call
   sites — `asy_ntp_client.py`'s `_fetch_ntp_reply()`, `asy_dns_client.py`'s `resolve_ipv4()`,
   `captive_dns.py`'s own `AsyUDPSocket(("0.0.0.0", 53), ...)` — never do this pre-resolution; they
   pass a plain tuple straight through, exactly matching `typings/socket.pyi`'s real-rp2-hardware
   `_Address` contract (`tuple[str, int] | ...`), which is correct and required for real hardware.
   Net effect: `_connect()`'s own broad `except (OSError, MemoryError, TypeError)` silently swallows
   this `TypeError` as an ordinary "peer unreachable" failure, so **under the Unix port specifically,
   every real NTP sync and every real DNS resolution attempt fails 100% of the time, unconditionally,
   regardless of network reachability** — confirmed directly by pointing a fully-connected,
   correctly-configured digital-twin run's `NTP_Host` at a real, working local UDP NTP responder on
   `127.0.0.1:123` (bypassing this sandbox's own separate outbound-network restriction entirely) and
   observing the sync attempt still fail with `NTP Invalid NTP time received!` every cycle, with zero
   packets ever reaching the responder. **Not a bug and not something to fix in `src/`**: this is
   exactly the class of thing CLAUDE.md's own "don't edit `src/` only to make the twin run" owner
   constraint rules out — the production code is already correct for the real target. It does mean
   the earlier "NTP round-trip couldn't be verified end-to-end because this sandbox's network policy
   blocks UDP/123" framing (`FINAL_WIRING_PLAN.md`'s Step 5 baseline-verification session) understated
   the gap: even a sandbox with full, unrestricted internet access could not have verified this code
   path under the Unix port either. Real rp2 hardware remains the only way to verify NTP/DNS's actual
   UDP transport — same conclusion this entry already reached, now reached from a direct
   reproduction instead of an absence of one.
6. `digital_twin/run_wozi_integration.py`'s `_soak()` memory-flat check
   (`_MEM_FLAT_TOLERANCE_BYTES = 4096`) — **re-investigated in a follow-up session, and the earlier
   "just a slow warm-up transient, will stabilize" framing is wrong.** A fresh, much longer
   diagnostic (400 cycles across every endpoint, then an isolated 300-cycle run hitting only the
   static `/` page) showed a **real, continuous, never-plateauing decline** — not the bounded ±15KB
   noise band the original 100-cycle read suggested. Root-cause investigation (full account below)
   found this is genuinely HTTP-independent (a zero-HTTP idle run declines identically) and driven
   by the real background task graph (SCD30/SGP40/BMP3xx measurement polling), not by anything in
   the webserver/Microdot layer, which tested completely clean in isolation at every layer (routing,
   sockets, `asyncio.wait_for()`, and every combination). **Confirmed, attributed contributors**:
   SCD30's own real read-and-store cycle (~500 bytes/sec of a ~870 bytes/sec idle total) and
   SGP40+BMP3xx's own read-and-store cycles (~130 bytes/sec combined) — real, reproducible, but not
   yet pinpointed past "the shared I2C-read → `_set_meas_data()` → log-call cascade", since every
   individual piece tested in isolation (`_produce_new_reading()` alone, `Pin.irq()`/`simulate_edge()`
   dispatch alone, `PrintLogHistory`'s own bounded-deque append) came back clean. **A residual
   ~245 bytes/sec floor persists even with every real `machine.Timer` starter in the whole system
   disabled** (SCD30/SGP40/BMP3xx read-cycle timers, WiFi's counter timer, NTP's timer + counter
   timer, `system_service.py`'s own uptime timer — the complete, grep-confirmed list of every
   `Timer(...)`/`.init(period=...)` call site in `src/`). The leading hypothesis during that session
   was `digital_twin/machine.py`'s own `WDT.feed()` → `_arm()`, which cancels and recreates its
   countdown `asyncio.Task` on every single `feed()` call (twin-only code — real hardware's
   `machine.WDT.feed()` is just a register write) — isolated alone it showed zero leak, but with
   every other Timer starter disabled and only the real 2-second-interval `feed()` call left active,
   it exactly reproduced the residual, which read as confirmation. **A rewrite avoiding the task
   churn entirely (a single long-lived polling task instead of cancel-and-recreate) was implemented,
   fully test-compatible (36/36 existing `test_digital_twin_machine.py` tests passed unmodified),
   but a rigorous same-script A/B re-test (identical monkeypatches, only the WDT implementation
   swapped) showed the exact same residual with the fix in place — the hypothesis was wrong, and a
   further test proved the entire `start_and_check_tasks()` supervisor-loop body (feed calls *and*
   task `.done()` checks) contributes nothing: replacing it with a bare `while True: await
   asyncio.sleep(2)` reproduced the same numbers.** The WDT rewrite was reverted rather than kept as
   a misleading "fix" for a cause it doesn't actually address. **The ~245 bytes/sec floor's real
   source remains unidentified** — every named Timer-driven and task-`.done()`-driven candidate in
   `src/` has been ruled out by direct isolation, which means continued `gc.mem_free()`-delta
   bisection via monkeypatching individual starters has run out of remaining candidates to try; the
   next step needs a different technique (e.g. the repo's own `sys.settrace`-based coverage
   infrastructure adapted for allocation attribution, or a MicroPython-level heap/object census
   rather than a before/after byte-count delta) to localize further. **Do not loosen
   `_MEM_FLAT_TOLERANCE_BYTES` based on this investigation** — the decline is real, not noise, and
   loosening the tolerance would just hide a genuine, still-open problem. Whether this is purely a
   digital-twin artifact (plausible given the confirmed contributors trace to twin-only chip-fake/
   `Pin` mechanics so far) or has any real-hardware-relevant component is itself unresolved and
   should be established before deciding whether a `src/` fix is ever warranted.
   **Owner decision: this becomes its own dedicated Step 6, run in a separate session immediately
   after this branch merges into the wire-up branch.** That session's two required outcomes for
   *this* memory-decline finding: (1) positively confirm this cannot happen on real RP2040 hardware
   (not just "the confirmed contributors look twin-only" — actually establish it), and (2) find and
   fix the digital-twin-side root cause regardless, including the still-unidentified ~245 bytes/sec
   floor. Use whatever tooling and however many tests that takes — not scoped to `gc.mem_free()`-
   delta bisection alone if that's run out of road, per this entry's own last paragraph.

   **Step 6 scope was subsequently widened by the owner to a full self-healing-system audit, not
   just this one memory-decline finding.** Now that the framework is fully wired up end-to-end, the
   owner wants Step 6 to systematically go after the whole class of failure modes that matter most
   in a long-running, self-healing embedded system — reasoned as: the *worst* failures in such a
   system aren't the loud immediate ones, they're the ones that let it keep running while doing the
   wrong thing, or that only show up after days/weeks of uptime. **Required categories** (owner-
   specified, plus two flagged during the discussion and accepted into scope):
     - Rare corner cases (owner-specified)
     - Memory leaks (owner-specified) — this entry's own finding is the first concrete instance
     - Race conditions on concurrent/repetitive calls, or on system startup (owner-specified)
     - Silent failure masking — an overly broad `except` or a retry loop that swallows a real error
       and keeps running while producing subtly wrong data or silently skipping work, with nothing
       ever signaling it happened; worse than a crash, since a crash at least trips the watchdog and
       gets noticed
     - Cascading recovery storms — the self-healing/retry logic itself becoming the failure, e.g.
       every unit hammering a simultaneous reconnect/resync after a shared outage (WiFi, NTP)
       instead of backing off. **First concrete instance, found during the Step 5 re-audit
       session's own official end-to-end run**: `captive_dns.py`'s `DNSServer.run()` loop calls
       `self.udps.recvfrom(4096)` (default `timeout_ms=-1`, wait forever) and, on `(None, None)`,
       just logs a warning and loops straight back to another `recvfrom()` call - no backoff, no
       retry cap, no give-up condition of its own. Under a real assembled end-to-end run in AP/
       hotspot-fallback mode (no SSID configured), the underlying `AsyUDPSocket`'s own `bind()`
       never actually succeeded (see open question #5's own sharper NTP finding just above for
       why, on the Unix port specifically), so `recvfrom()` returned `(None, None)` immediately on
       every call - `_RETRY_BACKOFF_S=0.5s` throttles each individual failed `_connect()` attempt,
       but nothing throttles the outer `run()` loop's own repeat rate on top of that, so real,
       measured output was ~5 `wrn_s()` log lines/second, continuously, for the DNS server task's
       entire lifetime (147 lines over one ~30s bounded run - confirmed directly, not estimated).
       Contrast `asy_ntp_client.py`'s own sync-retry path, which is properly bounded
       (`_NTP_SYNC_RETRIES=3`, `_NTP_RETRY_INTERV=15s` between attempts, then gives up and lets the
       task supervisor restart the whole task) - `captive_dns.py`'s loop has no equivalent shape.
       Whether this is reachable on real rp2 hardware too (a genuine, persistent `bind()` failure
       there - e.g. resource exhaustion - isn't inherently impossible, just far rarer than the
       Unix-port quirk that reliably triggers it here) is unresolved; either way the missing-backoff
       *shape* is real and worth fixing regardless of what triggers it. Deliberately not
       hand-patched in the re-audit session that found it - a real fix needs to decide bounded-retry
       semantics (how many attempts, what backoff curve, does it ever retry again after giving up)
       the same deliberate way `asy_ntp_client.py`'s own retry design already was, not a quick patch
       mid-tangent - left for Step 6's own "fix" step to do properly, per its required methodology
       below. Also worth noting: this spam was previously silent (invisible) before the
       baseline-verification session's own fix to `asy_wifi_service.py`'s `wlan_connect()` (missing
       `await self.dns_server.pr.setup()` - see `FINAL_WIRING_PLAN.md`'s Step 5 section) - that fix
       was correct and necessary (real logging now works at all for this module) but had the side
       effect of making this pre-existing retry-loop gap audible for the first time.
     - `time.ticks_ms()`/`time.ticks_diff()` rollover (~12.4 days at the RP2040's ms resolution) —
       a long-running-specific timing-correctness class distinct from the above, worth checking
       explicitly across every use site rather than assuming `ticks_diff()` is used everywhere it
       needs to be (a raw subtraction anywhere in the timing code would silently misbehave only
       after many days of uptime, exactly the kind of bug this audit is meant to catch)
     - Task/timer resource leaks as distinct from raw memory bytes — an `asyncio.Task` or
       `machine.Timer` that isn't cancelled/deinitialized on a retry or reconnect path can leave a
       duplicate background loop running (double reads, double log lines, doubled I2C traffic)
       without necessarily showing up as a `gc.mem_free()` decline
   **Required methodology per category** (owner-specified, four steps, all required — no category is
   done after only the first or second):
     1. **Look it through** — static analysis of the wired-up system for the mistakes/oversights/bad
        patterns that lead to each category (e.g. every `except`/retry site, every task/timer
        lifecycle, every concurrent-entry code path, every raw `ticks_ms()` subtraction).
     2. **Check, don't just look** — directly exercise the actual code running on the MicroPython
        Unix port against each category; static reading alone doesn't satisfy this step.
     3. **Fix** — don't let a confirmed issue persist; this is a fix-it session, not a
        catalog-and-defer session (this entry's own still-open ~245 bytes/sec floor is exactly the
        kind of thing Step 6 exists to close out, not re-document again).
     4. **Secure** — write extensive and/or soak tests specifically targeting each category, so a
        regression in any of these classes gets caught automatically going forward, not just this
        once.
   Not yet scoped: which categories apply where across `src/`, `improved-quality/`, and
   `digital_twin/` (the digital-twin-only vs. real-hardware-relevant distinction this entry's own
   memory finding already had to make); Step 6's own session should establish that per category
   rather than assume uniform scope.

   **Step 6 is not the same thing as the whole five-step effort's "large post-merge audit"**
   (confirmed directly by the project owner) — see `FINAL_WIRING_PLAN.md`'s "Branch / session
   structure" section for the precise relationship: Step 6 is its own dedicated session/branch,
   forked from and merged back into the trunk the same way every step above was; the large audit is
   a separate, later pass conducted directly on the trunk itself, after Step 6 (and anything else
   still open) has also landed there, gating `claude/framework-wiring-rest-api-hx99v7` → `main`
   (PR #31).
7. **The real MicroPython Unix-port interpreter itself segfaults under heavy concurrent connection
   load against the real assembled system** — found while investigating a real user-reported
   `OSError: [Errno 104] ECONNRESET` crash in `digital_twin/run_wozi_integration.py`'s own soak (that
   specific crash is fixed — `_soak()` now records a connection failure instead of letting it
   propagate and crash the whole diagnostic run, matching how the real server itself already
   tolerates a rejected/reset connection gracefully; see `FINAL_WIRING_PLAN.md`'s own session note
   for the fix and the closed test-coverage gap that let it through unnoticed). Firing 8 concurrent
   clients × 15 requests each (well beyond `WebserverService`'s own `max_connections=3` ceiling, to
   probe whether exceeding it explains the ECONNRESET) reproduced a real interpreter segfault twice
   in a row (confirmed directly via `dmesg`: `micropython[PID]: segfault at ... in micropython[...]`),
   not a catchable Python-level exception — no amount of `_soak()`/`_http_client.py` exception
   handling can prevent this, since it crashes the whole process unconditionally. Not yet root-caused
   at all (interpreter/C-level, not Python-level - out of this session's reach) and not confirmed to
   be what the original ECONNRESET report actually hit (repeated plain sequential-soak runs in this
   session's own sandbox never reproduced the user's report at all, despite several attempts - the
   segfault needed deliberately aggressive, unrealistic concurrency the soak's own strictly-sequential
   traffic pattern would never generate on its own). Real, reproducible, and serious enough to flag
   prominently even though it's tangential to what was being chased - folding into the same dedicated
   Step 6 session above (both are memory/robustness issues in the same digital-twin integration
   surface) makes more sense than a third separate investigation.

## Deferred / explicitly out-of-scope work

- **`pyproject.toml`'s mypy `exclude` list still has a dead regex entry for
  `improved-quality/microdot.py`** (removed — see `SPECIFICATION.md` Part A.5), matching
  nothing today, harmless but worth deleting (along with its now-dangling "see its own module
  docstring" comment) next time `pyproject.toml` is touched for another reason — not urgent enough
  to be the sole reason to trigger CLAUDE.md's "Pre-push verification" chroot recipe on its own.
- **HTML/frontend automation & consistency** — known hand-written/brittle, not a priority; revisit
  after the Python-side refactor. Concretely stale now: the frontend still sends the pre-migration
  `setSGP`/`setBMP` field names/formats (see `SPECIFICATION.md` Part C.5.3's wire-format note) — not
  updated to match.
- **UART sensor integration** — `asy_uart_driver.py` is promoted to `src/` but deliberately not
  wired into any `sensortask-*.py`; `asy_uart_comm.py` (its one real consumer) is its own separate,
  still out-of-scope promotion. Unused by any deployed config — wiring it in is after the refactor
  of already-deployed features, not before.
- **Owner requirement for the final wiring stage (not in this audit's scope, recorded here for
  when Stage 1 actually happens)**: every `sensortask-*.py` built as part of the real rewrite needs
  a full Unix-port equivalent, runnable on a local computer, with whatever hardware is physically
  unavailable there mocked at the lowest level of bus data exchange (i.e. the same mocking
  boundary `tests/README.md`/`tests/machine.py` already establish for unit tests — fake
  `machine.I2C`/`machine.SPI`/etc. byte-level transactions, not higher-level driver stand-ins) so
  the whole wired-together sensortask can be exercised as close to the real target as possible
  without physical hardware. `WIRING_CONTRACT.md`'s Stage-1 study is the natural place this lands
  once that rewrite starts. **Fulfilled**: `digital_twin/` (Step 3 of `FINAL_WIRING_PLAN.md`'s
  five-step effort) is the lowest-level-mocking module this requirement calls for, and has landed.
  The concrete fulfillment — actually running the whole wired-together `src/sensortask_wozi.py`
  against it end to end — is Step 5's own explicit goal; done in this session (not yet merged — see
  `FINAL_WIRING_PLAN.md`'s Step 5 section for the full detail). Once Step 5 merges and the whole
  five-step effort's large post-merge audit closes, this entry should come out per this file's own
  stated resolved-item policy.
- **Config-duplication centralization** — same keys hand-kept in sync across `_DEFAULT_CONFIG`, the
  REST handler, and the HTML form. Owned by the refactor: each promoted `*_Reader`'s own `_VAL_*`
  schema tuple + `get_dict_cfg()`/`get_dict_data()` is the intended single source, not fully wired
  end-to-end yet (`sensortask-wozi.py` itself predates the per-sensor-config model — see "Refactor
  targets not yet done" above).
- **`dev` config quirks** (e.g. LED/Neopixel REST routes referencing an uninstantiated object) —
  bench rig only, not bugs to fix.
- **Adafruit/DFRobot vendor attribution was dropped during `src/` promotion.** `asy_bmp3xx_driver.py`/
  `asy_scd30_driver.py`/`asy_sgp40_driver.py` no longer carry the Adafruit `SPDX-FileCopyrightText`/
  MIT-license header their legacy `python/IndividualDrivers/` originals have. `voc_algorithm.py` is
  subtler: its own docstring and `SPECIFICATION.md` F.4 both describe it as a direct port of
  Sensirion's C reference, but the retained class name `DFRobot_vocalgorithmParams`
  (byte-identical to the legacy file) shows the real intermediate is DFRobot's own MIT-licensed
  Python translation, whose attribution was never carried forward either — a provenance correction
  is needed alongside the missing header, not just the header alone. Owner explicitly deferred
  fixing this — no priority yet, kept here so it isn't lost.
- **`improved-quality/sensortask-wozi.py` has the same task/session-narrative-comment problem the
  rest of `src/` was already swept for** — pervasive dated migration-narrative comments, a
  TODO/stale-comment combo, one leftover `DRIVER_SPEC.md section 7` reference, and no module-level
  docstring (every `src/` file has one). Left untouched deliberately: out of scope under CLAUDE.md's
  hard rule on editing `improved-quality/` source without a scoped, owner-authorized exception, and
  explicitly deferred by the owner to its own future session rather than bundled into this one.
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
  behavior itself is intentional (see `SPECIFICATION.md` Part A.4), just undocumented for whoever configures a unit.
- **`asy_wifi_service.py`'s getters hide two opposite locking contracts under one shape**:
  `network_available()` requires the caller to already hold `wifi_mode_lock` (documented in-line),
  while `get_wlan_ifconfig()`/`get_dns_server_ip()`/`get_wlan_rssi()`/`wlan_isconnected()` assume the
  *caller does not* hold it (checking `.locked()` defensively instead). This exact mismatch already
  caused one real bug (a fixed `get_dns_server_ip()` always returning `None`) — the underlying
  inconsistency itself is unfixed, flagged as worth a naming/typing convention if a third such
  callback is ever added, not urgent enough to redesign now.
- **`config_manager.py`'s `make_dict()` has a `repr()`-parsing quirk with non-scalar fields**: it
  splits a namedtuple's `repr()` on `"("`/`","`, so a field whose own value contains one of those
  characters corrupts the result — a nested-tuple-valued field truncates every subsequent field out
  of the returned dict silently, and a list-valued field (comma inside `[...]`) produces a garbage
  key that collapses the whole dict to all-`None` via the outer `except Exception`. Dormant today —
  every current config namedtuple (`SGP40`/`BMP3XX`/`NTP`/`SCD30`/`WIFI`) is flat scalar fields only
  — but a real landmine for whoever adds a list/nested-tuple config field next; check this function
  first if a promoted driver's config read-back silently comes back wrong/empty after such a change.
- **`config_manager.py`'s three defensive `TypeError`/`AttributeError` catches** (non-string
  filename, non-iterable `keys`, non-dict `data` passed to `write_config()`) are currently dead
  weight — nothing in `src/`/`improved-quality/` calls these with malformed input today. Owner's
  stated rationale for keeping them anyway: once the Microdot REST layer feeds real (untrusted)
  request data into these paths, they stop being defensive-only and become load-bearing. Revisit
  once that wiring exists, not before.
- **Whole-system integration test scope** (a scoping item from the now-closed `src/` audit — recorded
  here since it's future test-writing work, not a current-state fact `SPECIFICATION.md` documents).
  Today's integration tests are all pairwise-or-triple chains (FRAM+notification,
  notification+neopixel, notification+SCD30 (both its WarnCO2 and WarnHum signals),
  notification+SGP40 (WarnVOC), NTP+FRAM+system, NTP+WiFi+DNS, setter+Microdot) — real
  and valuable, but none exercises the *actual* multi-module wiring shape `WIRING_CONTRACT.md`
  documents. Chains genuinely missing coverage, to write once Stage 1's real `sensortask-wozi.py`
  successor exists to exercise them against (most can't be meaningfully tested *before* that, since
  today's `improved-quality/sensortask-wozi.py` construction sequence is still fully synchronous —
  see `WIRING_CONTRACT.md`'s "New structural fallout" section for why):
  - **Full boot-sequence chain**: `conn` → `ntp` → `sysfunct` → every reader → `pixel` →
    `notify_service`, constructed in the real order, verifying FRAM chunk determinism holds
    end-to-end (not just per-component) and that every `SensorReaderConfig` subclass's new
    `await x.setup()` call actually lands before its first real config read.
  - **Task-supervisor restart, end-to-end**: `system_service.py`'s `start_and_check_tasks()`
    actually restarting a failed reader task drawn from the real, full registered task list (today's
    coverage exercises individual readers' own give-up behavior, never the supervisor discovering
    and restarting one through `get_task_starters()` against the real wiring).
  - **WiFi hotspot/DNS/LED chain**: `conn`'s hotspot-mode `DNSServer` task lifecycle plus
    `pixel`'s WiFi-status LED (`conn.set_ext_led(pixel)`) through a real mode transition, not just
    `captive_dns.py`/`asy_wifi_service.py` pairwise.
  - **SGP40 VOC-backup reboot-survival, full chain**: FRAM chunk 2 write → simulated reboot → real
    restore, through the actual `sgp_reader`/`fram` construction order, not a synthetic chunk.
  - **Multi-sensor REST read aggregation**: `/sensors/status`/`/sensors/config`'s real
    `get_dict_data()`/`get_dict_cfg()` merge across all three readers through Microdot end-to-end —
    today's `setter+Microdot` integration test only covers the write path for one driver at a time.
- **`asy_i2c_driver.py`'s `get_bits`/`set_bits`/`get_register_struct` still call the allocating
  `readfrom_mem()` rather than zero-copy `readfrom_mem_into()`** — no real caller needs the
  zero-copy path yet, but worth doing before `asy_isl29125_driver.py` (its one plausible future
  caller) is migrated.
- **`captive_dns.py`'s root-domain query (a single zero-length label, `.`) can't be told apart from
  a failed parse** — both produce `domain == ""`, so `response()` returns `None` for both,
  contradicting the module's own docstring claim that every on-subnet query gets an answer. No real
  captive-portal probe ever queries the bare root, so this is a documented gap, not an active fix.
- **`asy_scd30_driver.py`'s persistent NVM setters have no published write-cycle endurance figure**
  (checked every available Sensirion doc) — safe today only because every setter is REST-triggered,
  never called from a boot path or periodic loop. Don't add a periodic/high-frequency caller
  without reconsidering this.
- **`asy_wifi_service.py`'s 60s STA-retry branch holds `wifi_mode_lock` for up to a minute**, and
  `asy_ntp_client.py`'s sync task waits on that same shared lock — NTP sync can be delayed up to a
  minute during active WLAN instability. A priority-inversion-shaped cost worth having in view, not
  a correctness bug; not acted on.
- **Firmware build script should strip `if TYPE_CHECKING:` blocks from its temp frozen-copy, not
  the real `src`/`ext` files.** `mpy-cross` does not dead-code-eliminate `if TYPE_CHECKING:` the way
  it does an `if micropython.const(0):` branch — confirmed empirically (compiled real `src/*.py` +
  `ext/microdot.py` with this repo's own `mpy-cross`): the guarded imports/Protocol classes/type
  aliases fully survive into the `.mpy` bytecode (their qstrs included) since `TYPE_CHECKING` is a
  plain runtime-checked global, not a compile-time constant. Stripping these blocks (via an `ast`
  transform: parse → drop `if TYPE_CHECKING:`/its defining `try/except ImportError` header → re-parse
  the unparsed output as a validity check → hand that to `mpy-cross`) saved ~3.6KB across the 22
  files promoted to `src/` at the time of this measurement (108,339 → 104,748 bytes total; `src/`
  has since grown past 22 files, so a re-run today would save more, not less) — all still compiled
  clean. Safe specifically
  because nothing on this platform ever does runtime annotation introspection (no `typing` module,
  no `get_type_hints()` on-device) — the guarded names are only ever reached via string-literal
  forward-ref annotations that MicroPython never evaluates anyway, so deleting the block changes
  nothing observable. Directly grows the Pico W littlefs partition, which is whatever flash remains
  after the firmware image (see `SPECIFICATION.md` Part F.1). This prototype has not been committed
  to the repo — reimplement as a proper `scripts/`-housed step when the build script itself
  gets built, matching only a bare `TYPE_CHECKING`/`mod.TYPE_CHECKING` test (leave any compound
  condition untouched rather than guess) and sanity-`ast.parse()`-checking its own output before
  compiling.
