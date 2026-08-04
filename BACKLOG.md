# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

## Refactor targets not yet done

- **Bare `except:` is forbidden in refactored code** (`except Exception:` or narrower required).
  Ruff's E722 is already enabled, so existing bare excepts in `improved-quality/` show as tracked
  findings rather than being silenced — eliminating them is still real refactor work.
- **No CI firmware-build stage yet.** Blocked on genericizing `build-*.sh`'s hardcoded
  `/home/nico/rpi_pico/...` path and the `py-include` symlink (see "Deferred" below) — needs to
  land before/alongside this.
- **Mypy shall be configured to disallow `Any` types** (owner-specified, not yet implemented). The
  closest existing option is `disallow_any_explicit`; `pyproject.toml` deliberately stops short of
  it and the other `--strict`-only checks today. Blast-radius check done: `Any` appears ~29 times
  across `src/`/`tests/`, almost entirely in test-file monkeypatch/wrapper classes duck-typing a
  real MicroPython object rather than reimplementing its interface — turning this on will need a
  real typing strategy for those wrappers (e.g. `Protocol` classes matching just the overridden
  methods, plus `__getattr__` delegation) worked out first, not just a flag flip.
- **FRAM bus-recovery is only partially wired up.** `asy_fram_driver.py`'s own `src/` promotion
  added device-identification/write-protect verification, but there's still no periodic/triggered
  re-probe policy (`verify_present()`/`get_write_protected()`/`set_write_protected()` have zero
  callers anywhere) and no task supervisor for FRAM specifically. Whoever wires this up must wrap
  the calls in the same `try/except Exception` discipline this file's other methods already use —
  `asy_fram_driver.py` doesn't catch its own inherited `RuntimeError` path on these three itself.
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
  now fixed; see DRIVER_SPEC.md section 7 for the settled forward-logging convention every driver
  now follows. The broader "no gaps, no deadlock/starvation" audit itself is still open.)
- **Common driver error classes across sensors — future direction, not designed or implemented
  yet.** Each driver currently defines and reports its own `errno`/`wrnno` values independently
  (see DRIVER_SPEC.md section 7); the one exception is `errno=10` ("initial setup failed"), which
  all three drivers already use for the same situation by independent convergence rather than by
  any enforced scheme. Project owner's stated direction: keep per-driver definition/reporting (not
  a single shared enum), but predefine a small set of common error *classes* so the same number
  means the same or an equivalent condition across different drivers, beyond just the one
  already-consistent case. No scheme (numbering ranges, category list, how a driver opts in)
  designed yet.
- **Neopixel warning-flash sequencing and the task-supervisor error-budget counter** are both
  behaviorally correct and intentional as designed, but flagged by the owner as implementable more
  efficiently — worth a cleaner implementation in the refactor without changing observed behavior.
- **Three legacy REST wire-format/protocol conventions had no direct 1:1 equivalent in the new
  schema-driven setter dispatch (`base_classes.py`'s `_set_dict_cfg`/`api_response.py`'s
  `handle_set_cmd`) — found while auditing the new mechanism against `python/CommonDrivers/
  api_helpers.py`'s actual legacy behavior (not just against its own internal design). All three
  were raised with and confirmed by the project owner directly; all three are now settled (kept
  here as the record of what changed from legacy and why, not as open questions):**
  - **Settled: BMP3xx's `PressOvers`/`TempOvers`/`FiltCoeff` wire format is deliberately the raw
    value, not the legacy index.** The legacy `modules/sensortask-wozi.py` REST handler (`setBMP`)
    accepted a **0-5 (OSR) / 0-7 (IIR) index** and converted it server-side via
    `update_valid_json(..., weight_fct=lambda x: 2**x, ...)` (or `2**x - 1` for IIR) into the real
    oversampling multiplier / filter coefficient before validating/persisting/pushing it. The new
    `_VAL_POV`/`_VAL_TOV`/`_VAL_FC` schema (`asy_bmp3xx_driver.py`) validates the **raw multiplier/
    coefficient value directly** against `_OSR_SETTINGS`/`_IIR_SETTINGS` (confirmed correct against
    the real BMP388 datasheet's OSR/IIR tables — see `datasheets/bmp3xx/bst-bmp388-ds001.pdf` sec
    3.4.1/3.4.3, Table 6-8), with no index-to-value conversion step anywhere in the new path.
    **Owner-confirmed this is the intended, final wire format** — a deliberate, accepted breaking
    change from the legacy index-based API, not an oversight to fix. Nothing further to do here.
  - **Settled: the legacy pipeline's global "empty string on the wire means leave this field
    unchanged" convention is deliberately abandoned, replaced by "an omitted key means don't
    change."** `update_valid_json()` (the legacy per-field validator) special-cased
    `json_in[json_key] == ""` as `"Unchanged"` (skip) for *every* field of *every* type, on *every*
    endpoint — letting a client always resend a full payload and blank out only the fields it
    didn't want touched. `type_or_range_error()`/`ConfigManager.write_config()` have no such global
    bypass, and **this is intentional, not a gap**: `_set_dict_cfg` already only ever touches keys
    actually present in its `data` argument (`for key, value in data.items()`) — an absent key is
    never validated, never reported, never persisted, never pushed. **This existing behavior is
    already the full equivalent the owner agreed to** — a client that wants to leave a field
    untouched omits its key from the request body entirely, rather than sending `""`. No code
    change was needed; the mechanism already existed by construction. Whichever REST route(s) get
    built on top of `handle_set_cmd()` should build its request body from only the keys the client
    actually sent (already how every test in `test_setter_microdot_integration.py`/
    `test_api_response.py` constructs `data`), not synthesize a full payload the way
    `init_json_from_cfg()` used to.
  - **Settled and implemented: legacy's `cmd_keys` mechanism (a command-only, non-persisted field
    reported alongside real config fields in the same response, e.g. SGP40's `SGPResetVOC` →
    `sgp_reader.reset_voc()`) is replaced by reusing the schema's existing "special-alone" field
    convention** (`check_cfg_get_default`'s `def=None` + non-tuple `special` — already used for
    SCD30's `AmbPres`), owner-confirmed as the intended shape. `asy_sgp40_driver.py`'s
    `_VAL_RESET = (("SGPResetVOC", "bool", None, None, None, True),)` is included in the schema
    passed to `super().__init__()` (so `get_cfg_schema()`/`_set_dict_cfg()` validate and dispatch
    it like any real field), with a push callback (`_push_reset_voc`) registered to `reset_voc()`.
    No new mechanism was needed in `base_classes.py`/`config_manager.py` at all — two already-
    existing, already-tested behaviors combine to produce exactly the right semantics:
    `type_or_range_error`'s `"bool"` branch ignores `special` entirely (a longstanding, deliberate
    asymmetry), so both `True`/`False` are always structurally valid; and
    `ConfigManager.write_config()`'s `not use_value` branch for a special-alone field always
    reports `"Valid"`, never `"Unchanged"` (no previous stored value to compare against) — so the
    push callback reliably re-fires on *every* request, matching `reset_voc()`'s repeatable-trigger
    contract, not just an ordinary field's "only push on an actual change" default. See
    DRIVER_SPEC.md section 5.2.1 for the full pattern (including the one consequence a driver using
    this must handle: `get_dict_cfg()` must keep excluding the field from its own read, since
    `ConfigManager.get_dict()` is all-or-nothing and the field is never in `_cache`).
- **A follow-up, full function-by-function re-audit of `python/CommonDrivers/api_helpers.py` (2026-08-04)
  against `base_classes.py`/`config_manager.py`/`api_response.py` found two more points worth
  recording, plus confirmed neither existing `api_helpers.py` copy can be deleted yet:**
  - **Confirmed, no gap: legacy's `"switch"` dtype (`update_valid_json`'s `"On"`/`"Off"` string
    convention, converted via `toSwitch()`/`to_switch()`) has no equivalent in
    `config_manager.py`'s `type_or_range_error()` — and needs none.** Every promoted bool field
    (`asy_scd30_driver.py`'s `SelfCal`, `asy_sgp40_driver.py`'s `SGPResetVOC`,
    `asy_wifi_service.py`'s `LedWifiOn`) already uses schema type `"bool"` end-to-end, sent/received
    as a native JSON `true`/`false`, not an `"On"`/`"Off"` string — already implemented and exercised
    by real tests (not something newly changed by this audit), just not previously called out
    explicitly as a legacy convention with no direct equivalent. Nothing to do here.
  - **Settled and implemented: `set_sensor_value()`'s getter/previous-config/default
    failure-recovery chain is reintroduced as `base_classes.py`'s `_recover_failed_push()`, called
    from `_set_dict_cfg()` whenever a push callback fails.** Owner-confirmed intent (2026-08-04):
    the mechanism exists so the persisted config always ends up holding a *valid* value even after a
    failed live push, not a value the client requested but that never actually reached the sensor.
    Adapted to the new architecture's realities rather than ported 1:1, since persist-first (an
    already-settled ordering — see its own comment) means the "previous stored config" rung no
    longer exists by the time a push fails unless it's captured first:
    - `_set_dict_cfg()` snapshots each requested field's pre-write value (via `_get_mgr_cfg`) *before*
      persisting, so that rung survives the overwrite.
    - A new, optional per-field registry, `self._get_callbacks` (mirrors `self._push_callbacks`'
      registration shape exactly), lets a driver plug in a live sensor read-back where one exists -
      this is the new mechanism replacing legacy's caller-supplied `getter` function argument.
    - On push failure, `_recover_failed_push()` tries, in order: the live getter (if registered),
      else the pre-write snapshot, else the schema's own `def` value (no separate `default=` argument
      needed anymore, unlike legacy - the schema already carries a canonical default per field) - then
      writes the recovered value straight back through `_set_mgr_cfg` (bypassing `_push_callbacks`
      entirely, so a persistently-failing push can't loop).
    - Confirmed scope, matching `set_sensor_value`'s own gate exactly: only fields whose *this-request*
      push actually failed enter the chain - untouched/unchanged fields never did in legacy either.
      A command-only/special-alone field (`check_cfg_get_default`'s `use_value=False`) skips the
      chain entirely, mirroring legacy's own `cmd_keys` exclusion - there is nothing to persist-correct
      for a field that's never in `ConfigManager`'s `_cache` to begin with.
    - The field's caller-visible status in the returned dict stays `"Failed"` regardless of whether
      the correction succeeded - matches legacy exactly (the client is told the truth about their
      request; the persisted-value repair happens silently underneath).
    See `tests/test_base_classes.py`'s dedicated recovery-chain tests for coverage of every rung
    (getter wins, getter raises falls to snapshot, first-ever-request falls to default, special-alone
    exclusion, snapshot-read exception, correction-write exception) - `src/base_classes.py` is at
    100% line coverage including this method.
  - **`python/CommonDrivers/api_helpers.py` (deployed legacy) stays as-is, permanently out of
    scope** — owner-confirmed (2026-08-04): it's `from api_helpers import *`-imported by all four
    deployed `modules/sensortask-*.py` files, and the deployed codebase itself isn't being touched by
    this refactor. `improved-quality/api_helpers.py` (the WIP typed copy) is being actively migrated
    away from under a scoped, owner-authorized exception to the usual "don't edit
    `improved-quality/` source" hard rule (see the next item) - once
    `improved-quality/sensortask-wozi.py` no longer imports from it, it becomes deletable.
- **No `@app.errorhandler` registrations exist anywhere yet** (confirmed: neither
  `improved-quality/sensortask-wozi.py` nor the deployed `python/CommonDrivers/`-based app
  registers any). See CLAUDE.md's "Microdot / REST layer" section for what Microdot itself already
  guarantees (every route-handler exception, including `MemoryError`, is already caught per-request
  and can't crash the server) versus what's still missing at our own layer. The base-class/
  `api_response.py` setter+response-envelope consolidation this depended on is now done (see
  DRIVER_SPEC.md section 5) — `handle_set_cmd()` already provides its own defense-in-depth
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
- **Microdot hardening design (webserver robustness) — plan settled, not yet implemented.** Triggered
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
  - Defense shape: **layered** — per-connection timeout as the primary defense, plus whole-server
    restart as a backstop for anything the per-connection layer misses (e.g. a hang inside Microdot's
    own routing/dispatch logic, not just stream I/O).
  - Detection signal: **per-connection open-count leak tracking only** — no active self-test/loopback
    probe, no unconditional periodic restart. Both were offered and explicitly not chosen — don't
    re-add either as "obviously also worth having" without asking again.
  - Timeout sizing: **generous**, tuned around worst-case legitimate conditions (weak WiFi, larger
    page transfers) — a wedged connection may tie up its socket a while longer before reclaim, but a
    slow legitimate client is never the one getting cut off.
  - Tunables (timeouts, concurrent-connection threshold, restart grace period): **hardcoded internal
    constants, not REST/config-exposed** — same treatment as `WDT` timeout / `_TASK_FAIL_MAX` today,
    so nothing (including a REST caller) can accidentally weaken the safety net.

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
  4. Whole-server restart: when the open-count stays at/above a threshold (set with real margin below
     RP2040/lwIP's actual concurrent-socket ceiling — **that ceiling itself isn't known/verified yet,
     see companion open question below**) for longer than a grace period (avoid overreacting to a
     brief legitimate burst), close our own `Server` object (`server.close()` + `await
     server.wait_closed()`) so the outer task returns on its own — no forced `task.cancel()` needed in
     the common case. Register this webserver-starter in the *existing* `start_and_check_tasks()` task
     list like any other task; once it actually returns/dies, requirement "graceful restart" and
     "last-resort watchdog escalation" (via `task_errors`/`_TASK_FAIL_MAX`/`_force_watchdog_starve`)
     are already fully handled by `system_service.py`'s existing, tested supervisor — **no new restart
     or watchdog-escalation machinery needs to be built**, only that the webserver task needs to
     become capable of actually dying, which is exactly the gap steps 1-3 close. A secondary, harder
     timeout that force-cancels the outer server task if `close()`/`wait_closed()` doesn't return
     within a further grace period is the belt-and-suspenders fallback in case that assumption doesn't
     hold on real hardware.
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

  **Companion open question this design surfaces (not previously tracked)**: the actual concurrent-
  socket/TCP-PCB ceiling for MicroPython's rp2 port (lwIP-backed) isn't verified anywhere in this
  repo — needed to set a real-margin threshold for step 4 above. Check the port's own `lwipopts.h`/
  current MicroPython rp2-port docs directly rather than assuming a number from general lwIP
  knowledge.

  Suggested module name/location once implementation starts: `asy_webserver_service.py` in `src/`,
  matching `asy_wifi_service.py`/`asy_ntp_client.py`'s naming and the "every module owns its own
  schema" convention — though per the tunable-exposure decision above, this module's own safety
  constants deliberately have no config schema/REST surface.
- **Rough sequencing, not a committed plan**: (1) dev/build environment setup (genericized
  `build-*.sh`/toolchain paths) — everything else touching CI/firmware depends on this; (2) the
  structural patterns above (per-sensor config, generalized error-counter bookkeeping) are largely
  done; (3) bus/sensor error-recovery robustness items above, which build on that structure; (4)
  remaining tooling/CI (the firmware-build stage) — mypy/ruff/stubs/Unix-port-tests were pulled
  forward out of this order already, once `math_helpers.py` cleared the `src/` bar, and that's now
  standing practice for every new file, not a one-off.

## Open questions (need owner input or further investigation)

1. **A task-level restart of `asy_wifi_service.py`'s `wlan_connect()` would silently undo permanent
   WLAN deactivation**, though only through an essentially unreachable trigger path — flagged for
   owner awareness, not fixed. `_conn_phase == _PHASE_DEACTIVATED`'s branch in `wlan_connect()`'s
   main loop (`asy_wifi_service.py`, the `while True:` body) never returns — it just logs and
   sleeps — so the task can only die while deactivated via an exception escaping that trivial
   log-and-sleep branch, which no realistic MicroPython call there would raise. *If* that ever
   happened, though, `_reset_wlan_connect_state()` (called at the top of every fresh `wlan_connect()`
   invocation) only special-cases `_PHASE_HOTSPOT` staying as-is — any other phase, including
   `_PHASE_DEACTIVATED`, gets reset to `_PHASE_STA_SEEKING`, silently re-enabling WLAN. CLAUDE.md
   documents "a physical power-cycle is the accepted recovery path" for this deliberate safety
   feature, which a task-level supervisor restart (distinct from a full device reboot) would
   contradict if it were ever reachable. **Confirmed not a promotion regression**: the legacy
   `python/CommonDrivers/async_connect.py`'s `wlanConnect()` has the identical shape —
   `wlan_deactivated` is a local variable reset to `False` at the top of every fresh call, so a
   restarted legacy task would behave the same way. Owner call needed on whether this
   vanishingly-unlikely edge case is worth hardening (e.g. `_reset_wlan_connect_state()` also
   special-casing `_PHASE_DEACTIVATED`) or left as-is, matching decades of uneventful legacy field
   behavior.
2. `modules/_boot.py`'s `import sensortask.py` (literal `.py`) — works reliably on real hardware,
   but MicroPython's documented freeze/import behavior says it should raise `ModuleNotFoundError`.
   Mechanism genuinely unresolved. **Do not "fix" without testing on real hardware first.**
   Addressed during the refactor, not before.
3. Config-schema migration is a real data-loss risk on the *current deployed* codebase —
   `ConfigManager` overwrites the entire config file with hardcoded defaults the moment one key is
   missing, so a firmware update adding a config key could silently wipe WiFi credentials/tuned
   values. **Decided: not patched on the current codebase** — accepted (reconfigure via web UI
   after a key-adding update). The refactor's per-sensor config model avoids this failure mode
   structurally, not by patching the current global-JSON codebase.
4. MicroPython version target vs. upstream drift — deployed units run 1.26; upstream stable is
   1.28.0 as of the last check. **Decided**: deployed code stays pinned to 1.26 until a deliberate
   reflash campaign; the refactor is where the version target moves forward. 1.27→1.28 rp2-port
   changes checked so far look RP2350-specific, not RP2040-breaking, but not exhaustively checked
   against every module — re-check whenever the refactor picks a landing version.
5. SCD30 `ForceCalRef` field procedure isn't written down anywhere — a real maintenance routine
   exists (confirmed by owner) but the actual steps (reference concentration, exposure
   conditions/timing, frequency) still need capturing from the owner.
6. Does `config_manager.py`'s `write_config()` need long-block-lock-style coordination? Its
   `open()`+`json.dump()` has no yield point, the same shape `__init__`'s read path had before the
   cache-elimination redesign closed *that* concern. Whether a real RP2040 littlefs write of a
   small config file is fast enough not to matter is a hardware-timing question this dev
   environment can't verify — needs either a real-hardware measurement or an owner call on wiring
   it in proactively. **Note**: `get_long_block_lock()` itself has since been removed entirely (see
   CLAUDE.md's "Long-blocking operations" hard rule) — this question was never about that specific
   lock instance, and removing it neither resolves nor forecloses this question. Answering "yes"
   here would mean designing a fresh coordination mechanism at that time, not reusing or
   resurrecting anything already removed.
7. Real-hardware verification gap for `asy_udp_socket.py`/`captive_dns.py`: every UDP-layer claim
   (POLLERR/POLLHUP delivery, truncation, connected-socket source filtering) is verified against the
   MicroPython Unix port's socket implementation, not real rp2/lwIP — no rp2 hardware was available
   to test against. If a deployed unit ever shows UDP behavior diverging from what's
   tested/documented in the driver, this is the first place to look. Considered closing via a
   standalone on-device verification script — judged too hypothetical to chase for now.
8. BMP390's own datasheet isn't in `datasheets/bmp3xx/` (only BMP384/BMP388 are) — its `0x60` chip
   ID and assumed-identical register map/IIR table couldn't be verified against a real BMP390
   datasheet. Needs the owner to add the datasheet to close this.
9. Whether a hot-unplugged/replugged I2C or SPI sensor fully recovers is only field-tested at the
    task-death-and-respawn level (the whole `*_Reader` task dies and gets restarted by the
    supervisor) — never confirmed as *complete* recovery of the underlying bus/device state itself.
    Owner-flagged as "may be incomplete," to revisit/harden during the refactor rather than assume
    solved.
10. **Cross-file naming discrepancy found during a fresh consistency scan of `src/`** (flagged per
    this file's own "bird's-eye-view scan" policy, not silently fixed): `asy_wifi_service.py`'s
    `class asy_conn_time(SensorReaderConfig):` and `asy_ntp_client.py`'s
    `class asy_ntp_client(SensorReaderConfig):` are snake_case, matching their own module's
    filename — every other class in `src/` (`BMP3xx_Reader`, `SCD30_Reader`, `SGP40_Reader`,
    `ConfigManager`, `PrintLog`, `AsyFramManager`, `DNSServer`, `AsyUDPSocket`, `SystemService`,
    `LockedValue`, ...) is PascalCase and deliberately doesn't share its module's exact name. Likely
    inherited from the pre-refactor code's `asy_conn_time()` (a plain coroutine function, not a
    class, in `python/CommonDrivers/async_connect.py`) for continuity during promotion, not an
    oversight — but renaming now would touch every import/instantiation site (production
    `sensortask-wozi.py`/`neopixel_signal.py`, several test files), a real blast-radius decision
    similar in shape to the already-deferred `max_i2c_err` rename. Needs an owner call on whether to
    rename (and to what) or accept the mismatch permanently, not a unilateral fix.
11. ~~Does MicroPython's `asyncio.start_server()` isolate each accepted connection in its own
    Task?~~ **Resolved: yes, confirmed directly against source.** Checked
    `extmod/asyncio/stream.py` in the pinned toolchain checkout (`/root/pico-toolchain/micropython`,
    `v1.28.0` — matches the refactor's own forward version target, not the deployed-only 1.26 pin;
    see CLAUDE.md's "Platform target"): `Server._serve()`'s accept loop calls
    `core.create_task(cb(s2s, s2s))` for every accepted connection (line 174) — each connection gets
    its own independent Task, the same isolation CPython's `asyncio.start_server()` gives. Consequence
    for the one confirmed gap in Microdot's own per-request safety net (a non-`OSError` exception
    escaping `Response.write()`/`handle_request()` — see CLAUDE.md's "Microdot / REST layer"): only
    that one client's connection Task is affected; the outer `_serve()` accept loop and the rest of
    the Microdot server keep running unaffected. "Microdot restarts itself when it crashes" (via
    `system_service.py`'s existing task supervisor) stays a backstop for a fully-dead server task,
    not something made load-bearing by this gap.

## Deferred / explicitly out-of-scope work

- **Rename `max_i2c_err`** (`base_classes.py`'s `SensorReaderConfig`/`SensorReader` constructor
  parameter, and every promoted driver/service's own constructor that forwards it) to something
  bus-agnostic — confirmed by the owner it's a generically-useful "consecutive-failure streak
  before giving up and restarting the task" threshold via `_error_check()`, not literally about
  I2C, and both `asy_wifi_service.py` and `asy_ntp_client.py` (neither has an I2C bus) already rely
  on it under that misleading name. Deliberately not renamed yet (owner's own framing: "we will
  rename it later in another context") — touches every promoted driver/service's constructor
  signature and every test file that constructs one, a wider blast radius than any one promotion
  pass.
- **HTML/frontend automation & consistency** — known hand-written/brittle, not a priority; revisit
  after the Python-side refactor.
- **UART sensor integration** — `asy_uart_driver.py` is promoted to `src/` but deliberately not
  wired into any `sensortask-*.py`; `asy_uart_comm.py` (its one real consumer) is its own separate,
  still out-of-scope promotion. Unused by any deployed config — wiring it in is after the refactor
  of already-deployed features, not before.
- **Config-duplication centralization** — same keys hand-kept in sync across `_DEFAULT_CONFIG`, the
  REST handler, and the HTML form. Owned by the refactor: each promoted `*_Reader`'s own `_VAL_*`
  schema tuple + `get_dict_cfg()`/`get_dict_data()` is the intended single source, not fully wired
  end-to-end yet (`sensortask-wozi.py` itself predates the per-sensor-config model — see "Refactor
  targets not yet done" above).
- **`dev` config quirks** (e.g. LED/Neopixel REST routes referencing an uninstantiated object) —
  bench rig only, not bugs to fix.
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
  behavior itself is intentional (see CLAUDE.md), just undocumented for whoever configures a unit.
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
