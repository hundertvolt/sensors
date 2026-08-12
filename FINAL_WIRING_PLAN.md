# Final Wiring Plan — Stage 1 standalone `sensortask-wozi` rewrite

Temporary planning doc, same lifecycle class as `WIRING_CONTRACT.md`/the retired `AUDIT_PLAN.md`:
this is the **global list** for the whole "final wiring-up" effort — ideas, goals, documentation
links, and the criteria that make the five steps' open ends meet when combined into one working
prototype. Deleted once all five steps below have merged back and the large post-merge audit
closes; whatever in here is still true and permanent at that point migrates into CLAUDE.md/
SPECIFICATION.md/`WIRING_CONTRACT.md` instead of staying here, exactly as `AUDIT_PLAN.md`'s own
findings did.

**Goal**: the first technically complete framework setup able to operate on a real RP2040-based
sensor arrangement — *same top-level features* as today's deployed units, just more
consistent/stable (CLAUDE.md's standing working agreement), not a feature change. Scope for this
whole effort stays a **prototype**: `improved-quality/sensortask-wozi.py` (the one deployed
variant, "wozi") only, not the other three variants, and not the future build-script generator
that would turn a setup-definition file into every variant's `sensortask-*.py`/website pair —
this effort must not block that generator (see "Generator-readiness constraint" below) but does
not build it.

## Where the new code actually lives

`improved-quality/sensortask-wozi.py` (755 lines today) is explicitly **read-only reference** for
this whole effort — "a declaration of intention" (owner, confirmed directly), not a file any of
the five steps edits. CLAUDE.md's hard rule already forbids editing `improved-quality/` source
without a scoped, severity-justified owner authorization, and none of the five steps below need
one: nothing here is a bug fix to that file, it's a rewrite that lands somewhere else.

That "somewhere else" is settled by a concrete technical constraint, not a style preference:
Step 5 requires running the finished prototype under the real MicroPython Unix-port interpreter
(`scripts/test.sh`'s `MICROPYPATH="src:tests:.frozen"`) — `improved-quality/` is not on that path
and never will be, so a file that stays there is structurally untestable under this project's own
test infrastructure. The prototype therefore gets built fresh as **`src/sensortask_wozi.py`**
(underscore, matching every other `src/` module's importable-identifier naming, vs. the legacy
hyphenated filename that was itself always renamed to the generic `sensortask.py` at freeze time —
see `build-wozi.sh`) — a new file, informed by the reference but not derived from it mechanically.
`improved-quality/sensortask-wozi.py` itself is untouched by any of the five steps.

Two more locations are settled the same way, by direct precedent already in the docs:

- The generic webserver/API service (Step 2) is **`src/asy_webserver_service.py`** —
  BACKLOG.md's own "Microdot hardening design" entry already names this module and location.
- The digital-twin simulator (Step 3) is **not** `tests/machine.py` (explicit owner instruction —
  don't modify or reuse it) and **not** `src/` either (it's test/dev tooling, not production
  firmware code that ever gets frozen into a real build). It needs its own new top-level location
  (e.g. `digital_twin/`) with its own opt-in `MICROPYPATH` wiring for Step 5's integration run,
  kept separate from the `src:tests:.frozen` set every existing unit test already relies on so
  this doesn't disturb `tests/machine.py`-based tests. Step 3's own session should settle the
  exact directory name and how Step 5 wires it in; this doc only fixes that it's a new location,
  not a repurposing of an existing one.

## Branch / session structure

One branch per step below, sequential, each merged back before the next starts, each branching
off the previous step's merged tip:

```
main
 └─ claude/framework-wiring-rest-api-hx99v7   (this branch — global prep, PR #31)
     └─ Step 1 branch  → merge back into claude/framework-wiring-rest-api-hx99v7
         └─ Step 2 branch  → merge back
             └─ Step 3 branch  → merge back
                 └─ Step 4 branch  → merge back
                     └─ Step 5 branch  → merge back
                                          └─ large audit, then PR #31 → main
```

Suggested branch names (each step's session can rename if it finds a better one, but should stay
inside this scheme so the sequencing is legible from branch names alone):

1. `claude/step1-wiring-construction`
2. `claude/step2-webserver-api-service`
3. `claude/step3-digital-twin-simulator`
4. `claude/step4-website-placeholder`
5. `claude/step5-unix-port-integration`

Each step's PR targets the *previous* branch (not `main`) — only the final, already-open PR #31
(`claude/framework-wiring-rest-api-hx99v7` → `main`) ever targets `main`, once Step 5 merges and
the large audit closes.

## Per-step-session workflow (owner-specified, mandatory for every step below)

Every one of the five step sessions follows this sequence, reproduced here so a fresh session
starting cold on a step branch has it without needing this conversation's history:

1. **Refine and extend this doc's section for your step** into your own, more detailed list:
   ideas, goals, documentation links, and the criteria that must be fulfilled for *your branch* to
   finish. Do your own research (datasheets, current MicroPython/Microdot docs, the legacy driver
   code, `improved-quality/sensortask-wozi.py` as reference) — don't just restate this doc.
2. **Ask 10 top-level clarifying questions**: what needs deciding, the realistic options, and the
   consequences of each. Resolve as much as possible yourself first from project context, internal
   docs, and legacy code before asking — but a genuinely blocking or architecturally significant
   decision is always fair to raise, at any point, not just this round.
3. **Write the full set of unit tests first** (TDD), covering the criteria your own refined list
   settled on.
4. **Write the implementation** against those tests — refine until every test passes and the
   result is lean and efficient, not just "technically satisfies the tests."
5. **Add unit tests for the resulting functional code**, maximizing coverage the same way
   `src/math_helpers.py`'s suite already does for its own file.
6. **Stop and report back to the owner before doing anything more** — merging, starting the next
   step, or any scope beyond what was just built is not this session's call.

A step session can come back to the owner with a blocking question at any point in this sequence,
not only at the end — but the expectation is to have tried project context, docs, and legacy code
as a reference first.

## Original scoping discussion (verbatim record)

The five steps above are a restructured, resolved-conclusions rewrite of the ten clarifying
questions asked at the very start of this effort and the owner's answers to them. Kept here
verbatim, not re-summarized again, because summarizing already lost one fact once: an earlier
first-draft task list (session-local, never committed) said the construction/wiring restructure
would be "implemented in `improved-quality/sensortask-wozi.py`" — wrong per "Where the new code
actually lives" above, and a symptom of exactly the kind of drift that happens when only a
compressed conclusion survives. If anything below and the step sections above ever disagree, the
step sections above win — they're the reconciled version — but this record is the fallback for
recovering *why*, and for anything a later compression pass might have dropped without anyone
noticing.

1. **Scope of "API setup" moving out of `sensortask.py`.** *Answer*: "The scope matters with regard
   to the future plan of creating the sensortask* files automatically. I could imagine a setup like
   giving the webserver wrapper a bunch of sensor data callbacks, a bunch of system state callbacks
   etc... maybe with some names, so it can automatically construct a canonical JSON for the API —
   would be a good scope. Still to be decided which values to wrap in a single endpoint with a
   structured JSON and which ones to get their own endpoint." — the registration-API shape in Step 2
   is settled; **which values land in the single structured status endpoint vs. get their own route
   is not** — still a real open sub-decision for Step 2's own session to make (fair game for one of
   its own 10 questions).
2. **Website placeholder strategy.** *Answer*: "Just stubs for whatever website endpoints will be
   created in (1). The API will significantly change compared to the legacy state." — matches Step
   4's "stub only" framing; the real `html_raw/wozi/` content stays untouched, referenced only.
3. **Unix-port hardware-simulation fidelity.** *Answer*: "let's take a) the digital twin. Some
   sensible in-range arbitrary or random values, and keep it separated from the unit tests for not
   breaking anything there accidentally." — settled, this is Step 3.
4. **System-status endpoint shape/scope, including bus-layer participation.** *Answer*: "Keep the
   buses as they are. DNSServer may be extended by an error counter - it makes sense that every
   module which uses persisted (RAM or FRAM) logging also gets an error counter." — the general rule
   behind Step 1's `get_error_counter()` gap-closing (not just `DNSServer` — the same audit also
   found `NeopixelDriver` missing it).
5. **Real RP2040 firmware build — in scope?** *Answer*: "Real RP2040 build also in this scope.
   Unix-build verification is first, but once that runs, we will try on the real target (manually)."
   — still true of the *overall* effort; predates the five-branch restructuring, so "in scope" here
   means "part of this whole effort," not "one of the five branches" — it's sequenced after all five
   merge, per "Out of scope for all five steps" below. Not a contradiction, just a later finish line.
6. **How far to take "generator-friendly" now vs. later.** *Answer*: "The automated generator shall
   not result in any additional quasi-constant variables which are once set at boot time and from
   then on are constant but consuming memory. So setting it up in the sense of having a template
   with empty constructor calls and the generator filling these calls with lists of callbacks (or
   whatever is appropriate) should do." — the "generator-readiness constraint" in Step 2, worded
   precisely: the objection is specifically to *memory-consuming* quasi-constant globals on a
   memory-constrained target, not to named globals in general.
7. **`@app.errorhandler` registration — bundle in or defer?** *Answer*: "this is fully in scope of
   the Microdot wrapper writing, therefore yes, we will do in this scope." — settled, in Step 2.
8. **Priority order / how to detect the best point to split into a new session.** *Answer*: "Your
   steps are already ordered in good priority. How will we be able to detect the best point to start
   a new session in case it grows too much?" — never answered in words at the time; **now resolved
   structurally, not verbally**, by the five-branch-per-step scheme itself: each step *is* its own
   session by construction, so there's no separate "when to split" judgment call left to make.
9. **Is `improved-quality/sensortask-wozi.py`'s current construction order authoritative, or does it
   need active fixing?** *Answer*: "Confirmed. All content of improved_quality/sensortask_wozi.py can
   be regarded as a declaration of intention, not necessarily complete, and a collection of comments
   and adaptations in the course of prior refactoring. So no need to work around it, structure it in
   the most efficient way for a constrained system like the RP2040." — the basis for "Where the new
   code actually lives" above: the reference file is intent, not a constraint to preserve mechanically.
10. **Verification bar / TDD sequencing.** *Answer*: "We will do the unit tests here as well. With
    'come later' I meant that we will first create an extensive ordered action list. Once that list,
    not actual code work, is complete and additional information was fetched / gathered, we will
    create a whole bunch of unit tests in the sense of test driven development and do some discussion
    and decision rounds before." — the origin of the "per-step-session workflow" above.

## The five steps

### Step 1 — Construction/wiring restructure

**Goal**: turn `improved-quality/sensortask-wozi.py`'s flat, synchronous, module-level
construction sequence into `src/sensortask_wozi.py`'s async-safe equivalent, preserving every
piece of runtime behavior the reference file establishes.

**Known findings to carry in** (already resolved by prior research this session, not open
questions for Step 1 to re-litigate):

- `WIRING_CONTRACT.md`'s central finding: the sync-`__init__`/async-`setup()` pattern
  (`SPECIFICATION.md` Part C.13) means `bmp_reader`, `sgp_reader`, and `notify_service` each need
  an added `await x.setup()` call that isn't in the reference file — this breaks the flat
  top-level-statement shape and forces some async wrapping (an `async def main()`-style boot
  sequence, most likely) for at least everything from the first `await`ed step onward.
- The **FRAM chunk-order determinism rule** (`SPECIFICATION.md` Part A.4) must survive this
  restructure exactly: `SystemService` → `SGP40_Reader` (its own error log) → `SGP40_Reader` (VOC
  backup chunk) → `NeopixelDriver` → `NotificationCoordinator` — five chunks, not four; corrected
  during Step 1's own session after confirming `SGP40_Reader`'s own logger is already FRAM-backed
  (`WIRING_CONTRACT.md` item 8) — in that relative order, regardless of `await`s introduced around
  them. `WIRING_CONTRACT.md` is the living reference for this — **update it**, don't let it drift,
  once Step 1's actual construction order is decided.
- Two modules are missing `get_error_counter()` despite persisting logs via `PrintLogHistory`:
  `captive_dns.py`'s `DNSServer` and `src/asy_neopixel_driver.py`'s `NeopixelDriver`. Every other
  promoted module already exposes it with the standard
  `{"<NAME>": {"ErrCount", "ErrNum", "ErrType"}}` shape. Step 2's aggregation endpoint needs this
  gap closed everywhere it touches, so it belongs in Step 1 (construction-time module completeness)
  rather than being rediscovered in Step 2.
- Bus construction stays as-is (`asy_i2c_driver.I2C`/`asy_spi_driver.SPI` wrapping
  `machine.I2C`/`machine.SPI` unchanged) — owner-confirmed, not something to redesign here.

**Doc links**: `WIRING_CONTRACT.md` (the whole document), `SPECIFICATION.md` Part A.4 (FRAM
determinism), Part C.13 (setup()-gate pattern), Part C generally (driver/service architecture
shape), CLAUDE.md's platform-target Part F pointers (soft-Timer-drop, `Timer.init()` `ENOMEM`,
`[x]*n` segfault range — all relevant to anything touching `Timer`/list-construction during boot).

**Criteria for this step to finish**: `src/sensortask_wozi.py` exists, constructs every module the
reference file constructs, in FRAM-chunk-preserving order, with every needed `await setup()` call
in place; `DNSServer`/`NeopixelDriver` both expose `get_error_counter()`; `WIRING_CONTRACT.md`
updated to describe the *new* construction order as current, not the old flat one; full unit-test
coverage per the workflow above (construction-order tests, FRAM-chunk-order tests, boot-sequence
tests using `tests/machine.py`, not the digital twin — Step 1 has no dependency on Step 3).

**Done** (this session): all of the above landed — `src/sensortask_wozi.py`'s `build_system()`,
`boot_entry/wozi_boot.py`, `get_error_counter()` on `DNSServer`/`NeopixelDriver`,
`tests/test_sensortask_wozi.py` (16 tests), `WIRING_CONTRACT.md` rewritten in place, the
`max_i2c_err` → `max_module_error` rename, and the full existing test suite re-verified green.
See the "Refined plan" subsection below for the design decisions this took, and its own trailing
note on the one real behavior finding (`AsyConnTime`'s `start_hotspot_timeout_watcher`) surfaced
along the way. **Also done, added later in the same session per explicit owner follow-up
direction** (not part of the original Step 1 scope above, but landed inside this step's session
rather than deferred): the "never insist on FRAM" audit (every FRAM-backed error log/persistence
path already degraded gracefully to plain RAM when `fram=None`; added one regression test
constructing the whole object graph against a simulated dead FRAM chip) and live, persisted,
range-checked debug-level setting via a boot-time-collected registry of each module's own
`set_level()` — see the `watchdog`/`debug` split bullet below and `WIRING_CONTRACT.md`'s "Debug
level" section for the full design and the rejected `SharedLevel` alternative.

**What Step 2 needs from this step**: every long-lived module Step 1 constructs must be reachable
(directly or via a bound method) from wherever `src/sensortask_wozi.py` ends up handing things to
the webserver service — Step 1 does not need to invent the registration API shape itself (that's
Step 2's job), just make sure nothing it builds makes registration harder (e.g. no module that's
only reachable through a closure Step 2 can't get a reference to).

**Refined plan — resolved via project-owner Q&A this session** (supersedes/extends the above
where the two differ; kept as its own subsection rather than rewritten in place so the original
findings above stay legible as the starting point):

- **File layout — two files, not one.** `src/sensortask_wozi.py` stays the single testable module
  ("Where the new code actually lives" above), but it gets **no top-level blocking call** — no
  bare `asyncio.run(main())` at module scope. Instead it exposes `async def build_system() ->
  <components>` (pure construction + the setup()-batch below, no task loop) and `async def main()`
  (calls `build_system()`, then `start_timers()`/`start_and_check_tasks()`, matching the reference
  file's own `main()` shape). A test can `import sensortask_wozi` and call `build_system()`
  directly without ever blocking. The actual "importing this triggers boot forever" behavior the
  real firmware needs (matching what `modules/_boot.py`'s `import sensortask.py` expects today)
  moves to a new, separate, minimal file — **`boot_entry/wozi_boot.py`** (new top-level folder,
  self-explanatory name, not `src/` or `tests/`): `import asyncio; from sensortask_wozi import
  main; asyncio.run(main())`, a handful of lines, nothing else. Owner-confirmed: this is new code
  in a new location, not an edit to any legacy file, and `modules/_boot.py`'s own import mechanism
  itself stays untouched (CLAUDE.md's hard rule) — how `boot_entry/wozi_boot.py` eventually gets
  frozen/wired into a real build is Step 5's "full Unix-port integration"/assembly job, not Step
  1's; Step 1 only needs the file to exist and be correct in isolation.
- **No Microdot, no routes, no `frozen_html` import in Step 1.** Confirmed: `app = Microdot()` and
  every `@app.get/put` handler stay reference-only in `improved-quality/sensortask-wozi.py` for
  Step 2 to reimplement as the registration-based service — copying them into `src/sensortask_wozi.py`
  now would be wasted work under a paradigm Step 2 replaces wholesale. Same for `import frozen_html`
  (Step 4's job to give that import something real).
- **Object graph stays bare module-level globals**, matching the legacy file's own shape — no
  wrapper dataclass/NamedTuple container. Confirmed this isn't in tension with the
  "generator-readiness" constraint (BACKLOG.md/Step 2's own concern): that constraint is about
  Step 2's *callback-registration* API not emitting many quasi-constant globals per field: it
  doesn't reach this dozen-or-so core singleton references, which have to live somewhere in memory
  regardless of how they're named.
- **`await x.setup()` batching, resolved by dependency analysis, not by default:** the four
  `setup()` calls in play are actually **three independent domains**, not one: (1)
  `AsyFramManager.setup()` — real FRAM-chip SPI readiness, gates any FRAM chunk read/write; (2)
  each module's own `PrintLogHistoryStore.setup()` (`self.pr.setup()`) — FRAM-backed error-log
  persistence, depends on (1) but already runs safely later, inside each module's own task, in the
  existing reference file; not something Step 1 needs to add or reorder. (3) `ConfigManager.setup()`
  (via `SensorReaderConfig.setup()`, called on `sgp_reader`/`bmp_reader`/`notify_service`) — reads
  each module's own local JSON config file, **entirely independent of FRAM** and of each other; this
  is what WIRING_CONTRACT.md's finding is actually about. Between the three new (3)-domain calls and
  the one existing (1)-domain call (`fram.setup()`), there is no real cross-dependency requiring
  interleaving. There **is** one hard, real ordering constraint, though, found by reading
  `asy_notification_service.py` directly: `NotificationCoordinator.setup()`'s own docstring says
  "call after `finalize()`, before any task starter runs" — its `self.cfgmgr` doesn't exist until
  `finalize()`'s delayed `super().__init__()` runs, so `await notify_service.setup()` immediately
  after `notify_service = NotificationCoordinator(...)` (before `register()`×3/`finalize()`) would be
  an outright bug, not just a style choice. **Resolution: grouped/batched, not interleaved** — one
  dedicated async phase, positioned exactly where the reference file's existing `async_onetime`
  list already sits (after all synchronous construction, including `notify_service`'s
  `register()`/`finalize()`, before `start_timers()`), in fixed order `fram.setup()` →
  `sgp_reader.setup()` → `bmp_reader.setup()` → `notify_service.setup()` (fram first, matching its
  existing position; the three new ones appended in their own construction order). This is the one
  scheme applied consistently, per the "don't mix schemes" instruction — no setup() call happens
  interleaved with construction anywhere in the file.
- **`_MAX_I2C_ERR` → `_MAX_MODULE_ERROR` rename, now in scope and project-wide** (previously
  deliberately deferred per `SPECIFICATION.md` C.2/BACKLOG.md — owner has now explicitly authorized
  it). Touches: `base_classes.py` (`SensorReader.__init__`'s `max_i2c_err` param and
  `self.max_i2c_err` attribute, plus every internal reference), every module that takes/forwards it
  (`asy_wifi_service.py`, `asy_ntp_client.py`, `asy_sgp40_driver.py`, `asy_bmp3xx_driver.py`,
  `asy_scd30_driver.py`, `asy_notification_service.py`), and every test file constructing these
  objects with `max_i2c_err=`. Rename to `max_module_error`/`_MAX_MODULE_ERROR` (mirrors the
  owner's own suggested name exactly). Mechanical but wide; done as part of Step 1's implementation
  pass since `src/sensortask_wozi.py`'s own top-level constant is exactly where this originates.
- **Constants organization**: every module-level constant in the new file (the renamed
  `_MAX_MODULE_ERROR`, DNS/NTP timeouts, hotspot timing, etc.) grouped together in one clearly
  readable block, since a future generator script is expected to fill/edit these — values copied
  verbatim from the reference file, no re-tuning.
- **`watchdog`/`debug` split**: `watchdog = WDT(timeout=8000)` constructed directly in
  `build_system()`, hardcoded, no injection point (owner: "must be hardcoded so no error ever can
  circumvent it"). `debug` seeds each module's constructor as before, but — per explicit owner
  follow-up direction later in this same session — it's no longer construction-time-only: it's now
  live-settable and persisted via `SystemService.set_debug_level()`/`config_SYSTEM.cfg`, broadcast
  to every module's logger through a boot-time-collected registry of `set_level()` bound methods
  (`SystemService.set_level_setters()`, populated by `sensortask_wozi.py`'s
  `_collect_level_setters()`), not a shared/live-read value on `PrintLog` itself — see
  `WIRING_CONTRACT.md`'s "Debug level" section for the full design, the concurrency-safety
  verification, and the rejected `SharedLevel` alternative. Landed inside Step 1's own scope rather
  than deferred to Step 2, since the owner asked for it directly in-session.
- **`WIRING_CONTRACT.md` maintenance**: rewritten in place once the new construction order lands
  (owner-confirmed), not kept alongside the old flat description.
- **Task/timer starter collection uses each module's own `get_task_starters()`/`get_timer_starters()`
  uniformly, not the reference file's hand-copied bound-method list — a real finding, not a style
  choice.** Confirmed by direct comparison: `AsyConnTime.get_task_starters()` includes
  `start_hotspot_timeout_watcher` (the task backing `hotspot_time_min`'s actual timeout behavior),
  which the reference file's own hand-written `task_starters` list in `main()` never starts.
  `src/sensortask_wozi.py` now starts it. Flagged here rather than silently carried forward or
  silently dropped, per CLAUDE.md's discrepancy-flagging convention — worth a second look if a real
  deployed unit's hotspot-timeout behavior is ever compared before/after this rewrite.

### Step 2 — Generic webserver/API service

**Goal**: move the Microdot wrapper (startup, stability/restart control, route construction) out
of `src/sensortask_wozi.py` entirely into `src/asy_webserver_service.py`, as a **registration-based
service** — modules hand it named sensor-data/system-state callback groups, and it auto-constructs
the canonical REST/JSON surface, including one regularly-structured system-status endpoint
aggregating every module's `get_error_counter()` output.

**Known findings to carry in**:

- BACKLOG.md's "Microdot hardening design" is settled, not-yet-implemented, **and simplified from
  its original sketch by an owner decision this session** (see "Owner decisions on the 10 questions"
  below for the full derivation — BACKLOG.md itself is updated to match): composition around
  `asyncio.start_server()` (never call `app.start_server()`/`app.shutdown()` directly), a
  reader/writer timeout-wrapping proxy for per-call reads/writes, **plus one outer
  `asyncio.wait_for()` wrapping the entire per-connection `handle_request()` call** (new — this is
  what actually bounds a paced/Slowloris-shaped client, which per-call timeouts alone cannot, and it
  also covers a hang inside `dispatch_request()`/route-handler logic itself, which per-call stream
  timeouts never touched), per-connection open-count tracking (`LockedCounter`-style, decremented in
  a `finally`) driving a **reject-when-full** rule (silently close any new connection while at the
  ceiling — no accept, no response written) instead of accepting-then-restarting. **No bespoke
  whole-server-restart mechanism** — reject-when-full plus the outer cap already bound every
  connection's resource usage and lifetime, so the webserver's own task just gets registered as an
  ordinary task in `start_and_check_tasks()` like every other module (unchanged from the original
  sketch); the existing generic supervisor/watchdog-escalation machinery is the only restart path,
  same as everywhere else in the codebase — nothing bespoke to build on top of it. Read the whole
  BACKLOG.md entry, including its "verify before implementing" `asyncio.wait_for()` note and its
  "confirmed boundary" analysis of `handle_request()`'s shape (nothing inside `dispatch_request()`
  ever touches the transport, so the proxy alone is sufficient — no separate route-handler-level
  wrapping needed; the new outer cap wraps `handle_request()` as a whole, so it already covers
  `dispatch_request()` too).
- The concurrent-socket/TCP-PCB ceiling the reject-when-full rule's connection-count threshold must
  sit under is **confirmed at 5** (`MEMP_NUM_TCP_PCB`'s rp2-port default, `lwipopts_common.h` — see
  BACKLOG.md's now-resolved companion open question). Pick a real-margin threshold below that, not
  at it.
- `ext/microdot.py` (vendored, unmodified, pinned to `v2.6.2`) is hands-off — any behavior change
  happens by wrapping/calling it from `asy_webserver_service.py`, never by editing the vendored file
  itself. See CLAUDE.md's hard rule and `SPECIFICATION.md` Part A.5 for exactly what Microdot
  already guarantees per-request (blanket exception catch, the one real gap in `Response.write()`)
  versus what this project's layer still has to add — no `@app.errorhandler` is registered anywhere
  today; this step is also where that gets added (see BACKLOG's "REST/error-handling layer" entry
  right above the hardening design for the specific 400/404/405/413/500 + JSON-serializability
  requirements).
- **Generator-readiness constraint** (owner-specified): the registration API must not require the
  future per-variant build-script generator to emit many individually-named quasi-constant globals.
  The right shape is a small number of constructor/register calls, each filled with a *list* of
  callbacks — e.g. one call registering all of one module's status getters, not one named global
  per field. This doesn't block anything about this step's own design, it's a shape constraint on
  the registration API itself.

**Doc links**: BACKLOG.md's "Microdot hardening design" and "REST/error-handling layer" entries in
full, `SPECIFICATION.md` Part A.5, `ext/microdot.py` (read directly for exact call sites — grep for
every `reader.`/`writer.`/`stream.` method the proxy needs to forward, don't guess the list),
`src/system_service.py` (`start_and_check_tasks()` is the existing supervisor this service's restart
task plugs into unchanged).

**Criteria for this step to finish**: `src/asy_webserver_service.py` exists; registration API
matches the generator-readiness shape above; every route the reference file has today
(`/net/*`, `/time/*`, `/sensors/*`, `/led/*`, `/system/*`, plus static routes) is reachable through
it with identical response shapes; `@app.errorhandler` wired for at least 400/404/405/413/500;
per-call timeout-wrapped proxy + the outer per-connection wall-clock cap + open-count tracking +
reject-when-full all implemented and soak-tested (100+ start/wedge/reclaim cycles under the Unix
port, `gc.mem_free()` flat) — no bespoke restart mechanism to soak-test, since the webserver task
participates in the existing generic `start_and_check_tasks()` supervisor unchanged, the same as
every other module; full unit-test coverage, test doubles for reader/writer are step-driven fakes
only (never a real `select.poll()` — see CLAUDE.md's CI-hang-investigation note for exactly why).

**Refined plan — this session's own research, before the owner Q&A round** (extends the above;
kept as its own subsection per Step 1's precedent, so the original scoping stays legible as the
starting point):

- **Doc-currency check done this session (CLAUDE.md's standing instruction, not skipped)**:
  upstream `miguelgrinberg/microdot`'s latest release is still `v2.6.1`/`v2.6.2` (May 2026) as of
  this check — no newer tag, and no timeout-related feature has landed since BACKLOG.md's own
  research confirmed "zero timeout occurrences anywhere in `microdot.py`." The vendored
  `ext/microdot.py` pin is current; the hardening-design's premise (Microdot itself will never grow
  this feature upstream in a way we could just adopt) still holds. MicroPython's own `asyncio` docs
  (latest + v1.25.0, both checked) confirm `asyncio.wait_for()`/`wait_for_ms()` is the documented,
  intended mechanism for bounding a stream read, raising `asyncio.TimeoutError` on expiry — matches
  the design sketch's assumption, nothing to revise there.
- **Correction (implementation session, Step 2): the "`asyncio.TimeoutError` is an `OSError`
  subclass" claim below was wrong — confirmed directly against the pinned `v1.28.0`
  `extmod/asyncio/core.py` source (`class TimeoutError(Exception): pass`, immediately next to
  `class CancelledError(BaseException): pass`), not just re-derived from documentation. `asyncio`'s
  own `TimeoutError` is a **plain `Exception`**, unrelated to `OSError`/`errno`. Concretely, this
  means `handle_request()` wraps `Request.create()` in `except OSError as exc: ... else: raise`
  *then* `except Exception as exc: print_exception(exc)` (no re-raise) — a per-call proxy timeout
  raised during the **read** phase (request line/headers/body, all inside `Request.create()`) hits
  the *second* clause, not the first, and is therefore **silently absorbed by Microdot itself**,
  which then writes its own ordinary (aborted-request, still-200/400-shaped) response and closes the
  connection normally — the opposite of what the superseded paragraph below claimed. The **write**
  phase is different: `handle_request()`'s second try/except (around `res.write()`/`writer.aclose()`)
  only has an `except OSError` clause, no generic `except Exception` fallback, so a per-call proxy
  timeout occurring there *does* propagate out to our own `serve()` wrapper unmuted, same for the
  **outer** per-connection `asyncio.wait_for()` wrapping the whole `handle_request()` call (its own
  cancellation-driven `TimeoutError` is unaffected by any of this — see
  `src/asy_webserver_service.py`'s own `_serve()`/`_TimeoutStreamProxy` comments for the full,
  current, implemented behavior). Net effect versus the superseded paragraph's assumption: a
  read-phase per-call reclaim is **not** silently dropped — Microdot answers with an ordinary
  response and closes cleanly, same treatment as the already-settled `EOFError` case just below in
  section G item 2. Because Microdot itself never tells our wrapper this happened, the actual
  decision-8 "warn on every per-call reclaim" telemetry has to be logged from *inside* the
  reader/writer proxy itself, at the point of the timeout, not by catching a propagated exception in
  `serve()` — implemented that way. The superseded paragraph is kept below, struck through in spirit
  but left intact rather than deleted, since BACKLOG.md's own design-sketch text it was correcting
  (step 2's "Microdot's existing `except Exception as exc: print_exception(exc)` ... already handles
  this correctly") turns out to have been right all along; this correction restores that original
  reading rather than introducing a new one.
- ~~**One concrete new finding from this check, worth folding into the design before implementation
  starts**: `asyncio.TimeoutError` **is** an `OSError` subclass (`errno=110`, `ETIMEDOUT`) on
  MicroPython, not a bare `Exception` — and `errno 110` is **not** in `ext/microdot.py`'s own
  `MUTED_SOCKET_ERRORS` list (`[32, 54, 104, 128]`). Concretely: `handle_request()` wraps
  `Request.create()` in `except OSError as exc: if exc.errno in MUTED_SOCKET_ERRORS: pass else:
  raise` — a timeout raised by our proxy's wrapped `readline()`/`readexactly()` call (reached from
  inside `Request.create()`) is an unmuted `OSError`, so Microdot's own catch **re-raises it out of
  `handle_request()` entirely**, rather than quietly resolving to a 400 response the way a non-`OSError`
  would. This means our own `serve()` wrapper (the one calling `await app.handle_request(...)`, per
  the design sketch's step 1) **must** itself catch this — it is the expected, common-case outcome
  for a wedged/slow-going-silent client, not a rare edge case — and treat it exactly like the design
  sketch's step 6 already says any wrapper-level failure should be treated: log via `pr.wrn_s`/`err_s`
  and let that one connection's task end, `finally`-decrementing the open-connection counter. Nothing
  in the settled design actually assumed otherwise, but this is worth stating explicitly rather than
  discovering it mid-implementation: **the timeout path does not flow through Microdot's own
  error-response machinery at all** (no 5xx ever gets written back — the socket is simply abandoned
  the way a genuinely dead TCP peer would be), which is the correct behavior for this failure mode
  (matching a real client timeout), not a gap to fix.~~
- **Resolved myself, not asked below** (context/legacy code already settles these):
  - The webserver service's own diagnostics need a plain `PrintLog` (`self.pr`), not a full
    `SensorReaderConfig`/`ConfigManager` — BACKLOG.md is explicit that "this module's own safety
    constants deliberately have no config schema/REST surface," so it has no config file to load and
    no `setup()`-gate need; it follows `NeopixelDriver`'s/`SCD30_Reader`'s shape (`self.pr` only, no
    `cfgmgr`), not `SGP40_Reader`'s. It still needs a `get_error_counter()` (so it participates in the
    aggregation it itself serves) and a `get_task_starters()` (the restart-capable server task) —
    `sensortask_wozi.py`'s `_collect_level_setters()`/`_collect_task_starters()`/
    `_collect_timer_starters()` all need one more entry each once this module is wired in; that edit
    to the already-merged `src/sensortask_wozi.py` is in scope for this step (it's a freely-editable
    `src/` file, not `improved-quality/`).
  - Every registered callback is async — matches literally every existing `get_dict_data()`/
    `get_dict_cfg()`/`get_error_counter()`/setter method in the whole codebase; no case for accepting
    sync callables and building `invoke_handler`-style dual dispatch to support them.
  - `abort()`/`HTTPException` is only ever needed for Microdot's own built-in triggers (413 from
    `max_content_length`, plus whatever `@app.errorhandler(404)`/`(405)` we register to shape their
    bodies) — no route handler in the reference file ever calls `abort()` today, they all return an
    `ar.make_response()`-shaped dict directly, including for validation failures. The new registration
    layer should keep that convention rather than introducing a second error-reporting path.

**What Step 4 needs from this step**: a defined extension point for static/frozen content —
whatever shape `register_static_routes()`-or-equivalent takes, Step 4 should only need to supply
content plus a freezefs build step, not touch webserver internals.

**Endpoint design — decided by the project owner ahead of the dedicated webserver-integration
session** (this is a design decision, not yet an implementation — the actual `asy_webserver_service.py`
build, including the registration API's exact call signatures, is explicitly deferred to that
session; this subsection is the settled contract it starts from):

- **Six external endpoints, replacing the legacy `/net/*`, `/time/*`, `/sensors/*`, `/led/*`,
  `/system/*`**: `/measurements`, `/sensors`, `/networking`, `/system`, `/status`, `/notification`.
  Legacy `/time/*` splits across `/system` (GMTOffset/DSTOffset — local-time *interpretation*) and
  `/networking` (NTP_Host/NTP_Offset_S/NTP_Interv_H — sync *mechanics*).
- **Clean live-vs-settings split, no endpoint mixes the two**: `/measurements` and `/status` are
  the only two live-data endpoints (fully live, no persisted settings in either); `/sensors`,
  `/networking`, `/system`, `/notification` are pure settings (fully persisted config, no live
  telemetry in any of them). This moved `Connected`/`IP`/`Rssi`/`Wifi_Uptime`/NTP sync state out of
  `/networking` and `NotificationCoordinator`'s `Triggered`/`TS`/`pauseTime` out of `/notification`
  — both now live under `/status` instead.
- **GET shapes**:
  - `/measurements` → `{"SCD30": {...}, "SGP40": {...}, "BMP3XX": {...}}` — one entry per sensor
    reader in a plain list at init (see "Registration style" below), `get_dict_data()` each.
  - `/sensors` → same per-sensor sub-structure as `/measurements`, `get_dict_cfg()` each.
  - `/networking` → flat settings only: `SSID, PW(masked), Country, Hostname, LedWifiOn, NTP_Host,
    NTP_Offset_S, NTP_Interv_H`.
  - `/system` → flat settings only: `DebugLevel, GMTOffset, DSTOffset`.
  - `/notification` → flat settings only: `OnH, OnM, OffH, OffM, FlashBri, Interv, FlashDur,
    AutoOn, WarnCO2, WarnVOC, WarnHum`.
  - `/status` → live-only, sub-structured with top-level keys named after the settings endpoints
    they mirror:
    ```
    {
      "networking": {WifiUptime, Mode, Connected, IP, IPv4, Subnet, Gateway, DNS, Rssi,
                     NtpSynced, NtpLastSyncAge, NtpLastSync},
      "system":     {SysUptime, BootSignature, MemPaused, LocalTime: {...}, UtcTime: {...}},
      "sensors":    {"SGP40": {BackupTS, RestoreTS}},   // only sensors with maintenance data
      "notification": {Triggered, TS, PauseTime},
      "errcount":   {"<Name>": {"counter": int, "history": [{"num": int, "type": "N"|"E"|"W"}, ...]}}
                    // one entry per module + one per ConfigManager ("CFGMGR_<name>"); "history"
                    // present wherever that module's logger actually persists ErrNum/ErrType entries
    }
    ```
- **PUT shapes — one sparse JSON per endpoint, no `cmd` envelope** (replaces
  `parse_cmd_request()`'s allowed-command-list pattern for these six routes): any field present is
  applied, any field/sub-object omitted is left untouched, unknown fields are ignored — the same
  permissive strategy `ConfigManager.write_config()`/`_set_dict_cfg()` already use internally, now
  extended to be the *only* strategy at the HTTP layer too.
  - `/measurements` — no PUT.
  - `/sensors` — `{"SCD30": {<any subset of TempOffs,MeasInt,AmbPres,Altitude,ForceCalRef,SelfCal,
    ContMeas>}, "SGP40": {<any subset of BackupPeriod,BackupMaxAge,WaitTimeNTP,SGPResetVOC>},
    "BMP3XX": {<any subset of the 8 fields>}}` — any sensor key or field can be omitted; a single
    field for a single sensor, all fields for one sensor, or all fields for all sensors are equally
    valid in one call.
  - `/networking` — `{<any subset of SSID,PW,Country,Hostname,LedWifiOn,NTP_Host,NTP_Offset_S,
    NTP_Interv_H>}`.
  - `/system` — `{<any subset of DebugLevel,GMTOffset,DSTOffset>, "SystemCmd":
    "reboot"|"bootloader"|"mempause"}` — `SystemCmd` optional, still strictly enum-validated (the
    "safe, non-accidental enum" property of the old `content` field is kept, just folded into the
    same JSON body instead of a separate `cmd`-wrapper route). `mempause`'s duration stays the
    legacy **fixed 300s**, not client-supplied — no companion duration field.
  - `/status` — `{"ResetErrors": true}` only, for now (absent/false is a no-op) — resets every
    module's error counter *and* history in one global action, not scoped per-module.
  - `/notification` — `{"lightCmdLED": {"r":.., "g":.., "b":.., "t":..}, "PauseTime": int, <any
    subset of OnH,OnM,OffH,OffM,FlashBri,Interv,FlashDur,AutoOn,WarnCO2,WarnVOC,WarnHum>}` —
    `lightCmdLED` nested, everything else flat top-level, all optional.
- **GET copy-safety, checked directly against `src/print_log.py`/`src/config_manager.py`, no new
  locking needed**: `get_dict_data()` (via `config_manager.make_dict()`), `ConfigManager.get_dict()`,
  and `PrintLogHistory.get_log()` already build a brand-new dict/list of copied scalar values on
  every call, with no `await` in the middle of that construction — MicroPython's cooperative,
  non-preemptive scheduling (CLAUDE.md Part F) means a synchronous stretch of code with no `await`
  can't be interleaved by another coroutine, so these snapshots are already atomic and independent
  of anything that happens afterward; no caller ever gets a live reference into `_cache`/`history`.
  `ConfigManager.config_lock` (an `asyncio.Lock`) exists and is used, but only inside
  `write_config()`, to serialize concurrent *writers* against each other (its own comment already
  documents why readers don't need it: the commit step `self._cache = new_cache` is a single
  reference swap with no `await` before it). **One known, pre-existing exception, not introduced by
  this design and not fixed by it**: `SCD30_Reader.get_dict_cfg()` (entirely) and three of
  `BMP3xx_Reader.get_dict_cfg()`'s fields (`PressOvers`/`TempOvers`/`FiltCoeff`) are live
  hardware-readback fields — their callback does `await` a real I2C transaction mid-dict-construction,
  so a concurrent config write interleaving between two such awaited reads could produce one response
  with a mix of pre- and post-write values across fields. This is a torn-read-across-fields
  characteristic already present in those two drivers today, unrelated to "a reference to mutable
  state leaking out" (each individual field value is still a fresh read, never a stale reference) —
  flagged for awareness, not treated as something this endpoint redesign needs to fix.
- **Registration style — everything supplied as lists at init, generator-fillable**: the
  constructor/registration surface `src/asy_webserver_service.py` exposes must, per module, be
  "append this module (or its relevant bound methods) to the right list" — never a new named global
  per field or per module. This mirrors `_collect_task_starters()`/`_collect_timer_starters()`/
  `_collect_level_setters()`'s existing shape exactly (uniform lists, even where a given variant
  only has one or two real entries), so a future per-variant generator only ever needs to know "does
  this variant have module X" and append accordingly — it never needs to know anything about field
  names or endpoint shapes.
- **Known gaps — now resolved by owner decision, not just flagged**:
  - `SCD30_Reader`'s setter shape (question 4): confirmed from `base_classes.py`/`asy_scd30_driver.py`
    directly — `SensorReaderConfig._set_dict_cfg()` (the generic setter every other sensor reuses)
    is fundamentally built around a `ConfigManager`-backed persist-then-push pattern, and
    `SCD30_Reader` extends the bare `SensorReader` (no `cfgmgr`) by design: its own `_VAL_*` schema
    tuples (`_VAL_TO`/`_VAL_MI`/`_VAL_AP`/`_VAL_ALT`/`_VAL_CAL`/`_VAL_SC`) already carry an explicit
    comment — "these params are stored on the sensor itself, not cached locally" — and it already
    has one individually-named async setter per field (`set_measurement_interval`,
    `set_ambient_pressure`, etc.), just no schema-driven *dispatcher* over them. **Decided**: add a
    new, SCD30-local generic setter to `asy_scd30_driver.py` itself, structurally mirroring
    `_set_dict_cfg()`'s sparse-dict/per-field-validate-against-schema/dispatch-by-name shape, but
    with no persistence step at all — no `cfgmgr`, no `_set_mgr_cfg()`, no local JSON file; each
    validated field calls straight through to its already-existing individual setter method (a real
    I2C write to the chip), matching "according to other sensors" (same schema-driven shape) while
    respecting "don't add any persisted config" (nothing gets locally cached/written to a file).
    `ContMeas` stays the one field this schema can't cover (no `_VAL_*` entry exists for it, same
    reason as today: the SCD30 can't report whether continuous measurement is running) — keeps its
    own bespoke handling in the webserver layer, not silently forced into the schema.
  - `reset_error_counter()` gap on `NeopixelDriver`/`DNSServer`/`ConfigManager` (question 5):
    confirmed present on `base_classes.py` (`SensorReader`/`SensorReaderConfig`), `SystemService`,
    `AsyFramManager`, `NotificationCoordinator` already; missing on these three. **Decided**: close
    it inline as part of Step 2's own implementation pass (not retroactively folded back into Step
    1) — the owner's framing was explicitly "it does not matter how, as long as it is added lean and
    consistently," so mirror each module's own existing `reset()`/counter-clearing shape (matching
    how Step 1 added `get_error_counter()` to the same two of these three modules) rather than
    inventing a new shared mixin/pattern for it.

**Detailed TDD action list — collected from this session's endpoint-design discussion plus
BACKLOG.md's "Microdot hardening design"/"REST/error-handling layer" entries and `SPECIFICATION.md`
Part A.5** (this is the concrete, expanded version of "Criteria for this step to finish" above —
the implementation session should write tests against this list before writing any
`asy_webserver_service.py` code, per the per-step-session workflow's TDD ordering). Every line is a
test to write, not yet a test that exists.

**Status: `tests/test_asy_webserver_service.py` written (65 tests)** — the per-step-session
workflow's step 3, done ahead of any `src/asy_webserver_service.py` code (none exists yet; every
test here is expected to fail at import time until the implementation session creates that module —
correct TDD "red" state, not a bug). Sections A-E are covered at full checklist depth. Section F is
covered for F.1/F.2/F.5/F.6/F.7 at full depth and F.8/F.9 at a lighter, representative depth (F.9's
full 100+-cycle soak belongs in a slower, separately-invoked pass, not this file's default fast
run). All connection-lifecycle tests use hand-scripted fake reader/writer doubles (`_ScriptedReader`/
`_HangingReader`/`_ClosedReader`/`_ScriptedWriter`), never a real `select.poll()`, per decision 10
and the CI-hang-fix precedent. Because the endpoint-design decision above deliberately left the
registration API's exact call signatures to the implementation session, this test file had to commit
to one concrete shape in order to be written at all — documented in full in the test file's own
module docstring: a `WebserverService(app, sensors=, settings=, system_cmd=, notification_led=,
status_sources=, maintenance_sensors=, error_sources=, ...)` constructor plus a small
`SettingsGroup(module, fields, post_fct=, post_asy_fct=)` registration record (generalizing the
existing `_wifi_field_schema()` per-route field-scoping convention to every settings endpoint, since
e.g. `/system` and `/networking` each combine field subsets from more than one underlying module).
The implementation session should build to this shape, refining only where writing the real code
reveals a genuine problem with it — not treat it as unreviewable.

**Status update (implementation session): `src/asy_webserver_service.py` written, all 65 tests
green under the real MicroPython Unix-port interpreter** (`ruff`/`mypy` clean on both files too).
Built to the invented API contract above essentially unchanged (`WebserverService`/`SettingsGroup`
as documented). Two categories of genuine problem surfaced while implementing, both resolved per
this section's own "refining only where writing the real code reveals a genuine problem" allowance
rather than left as silent workarounds:
- **MicroPython doesn't support `await` inside a comprehension** (confirmed directly: a bare dict-
  comprehension containing `await module.get_dict_data() for ...` raises `SyntaxError: 'await'
  outside function` at import time, unlike CPython) — every such comprehension in the implementation
  is a plain `for` loop instead.
- **The `asyncio.TimeoutError`-is-an-`OSError`-subclass claim above was wrong** — see the correction
  inserted right after it (same session, same finding) for the full, source-confirmed explanation
  and its consequences for `_serve()`'s exception handling and where decision 8's per-reclaim warning
  actually has to be logged from. Three tests' own expectations were corrected in place to match the
  now-confirmed real behavior (`test_f2_content_length_larger_than_body_sent_then_silence_times_out`,
  `test_f2_trickled_request_line_is_reclaimed_by_the_outer_cap_not_a_single_per_call_timeout`, and
  the already-noted EOF-mid-body test) — each carries its own comment explaining the correction.
  Also fixed one test-only bug found in the same pass, unrelated to the TimeoutError finding:
  `test_b_deeply_nested_json_body_degrades_to_a_clean_rejection_not_a_hard_fault` built its malformed
  body via `json.dumps()` on a real 2000-deep nested Python object, which recurses exactly as deeply
  as the `json.loads()` the test meant to exercise and blew the recursion limit in the test's own
  setup code before ever reaching the code under test — fixed by building the raw JSON text directly
  via string repetition (`b"[" * depth + b"1" + b"]" * depth`) instead.

Not yet done as part of this pass (unchanged from before): wiring `WebserverService` into
`src/sensortask_wozi.py`'s `build_system()` with the real drivers (SCD30's own schema-driven setter,
the `reset_error_counter()` gap-closing on `NeopixelDriver`/`DNSServer`/`ConfigManager`, and the
real `SettingsGroup`/`status_sources`/`system_cmd`/`notification_led` registrations) — this module's
own test suite deliberately stays independent of that wiring (uniform fakes throughout, per the
endpoint-design decision that real per-module wiring is the caller's concern, not this module's).

**A. Endpoint contract tests** (per endpoint, against the settled GET/PUT shapes above):
- [ ] `/measurements` GET returns the merged 3-sensor dict; empty sensor list registered → empty
      dict, not a crash (registration-list edge case, see C below).
- [ ] `/sensors` GET mirrors `/measurements`' per-sensor structure with config fields.
- [ ] `/sensors` PUT: empty body `{}` → no-op, all fields unchanged; single field for one sensor;
      all fields for one sensor; all fields for all sensors; unknown sensor key ignored; unknown
      field within a known sensor ignored (matches `_set_dict_cfg`'s existing per-field
      `"Invalid"`, not a whole-request failure); `SCD30`'s `ContMeas`/`SGP40`'s `SGPResetVOC`
      round-trip as ordinary fields, no `cmd` wrapper.
- [ ] `/networking` GET is flat settings only — no `Connected`/`IP`/`Rssi` present.
- [ ] `/networking` PUT: partial-field update triggers only the relevant post-write hook
      (`reconnect_wifi`/`ntp_force_sync`), not both, when only one module's fields are present.
- [ ] `/system` GET is flat `{DebugLevel, GMTOffset, DSTOffset}` only.
- [ ] `/system` PUT: settings-only body (no `SystemCmd`) applies settings and takes no lifecycle
      action; `SystemCmd` present with an invalid/non-enum value is rejected without side effects;
      each of `reboot`/`bootloader`/`mempause` fires the right `sysfunct` call; `mempause` always
      uses the fixed 300s, never a client-supplied duration.
- [ ] `/status` GET returns exactly the `networking`/`system`/`sensors`/`notification`/`errcount`
      sub-structure, no settings fields anywhere in it; `sensors` sub-key omits any sensor with no
      maintenance data (today: only `SGP40` present).
- [ ] `/status` PUT: `{}` and `{"ResetErrors": false}` are both no-ops; `{"ResetErrors": true}`
      resets every module's counter *and* history in one call.
- [ ] `/notification` GET is flat settings only — no `Triggered`/`TS`/`PauseTime`.
- [ ] `/notification` PUT: `lightCmdLED` nested sub-object round-trips independently of the flat
      top-level fields in the same body; a body with only `PauseTime` doesn't touch the notify
      schedule fields and vice versa.

**B. Cross-endpoint sparse-JSON PUT semantics** (one shared test matrix, run against every settings
endpoint so the convention is actually uniform, not just true by accident per-endpoint):
- [ ] Missing field/sub-object at any level → left untouched (not reset to default).
- [ ] Unknown top-level key, unknown nested key, unknown sensor name → silently ignored, no error
      surfaced (matches `ConfigManager.write_config()`'s existing per-key `"Invalid"` handling).
- [ ] Wrong top-level JSON type (array, string, number, `null` instead of an object) → clean
      rejection, not a crash inside the dispatch layer.
- [ ] Wrong type for a known field (string where int expected, etc.) → per-field rejection, doesn't
      abort the rest of the request's other valid fields.
- [ ] Malformed/undecodable JSON body entirely → same `request.json`-raises handling
      `api_response.py`'s `parse_cmd_request()` already does today (still relevant even though the
      `cmd` envelope itself is gone — `request.json`'s own failure mode doesn't change).
- [ ] Duplicate keys in the raw JSON text (undefined-order behavior) — confirm what MicroPython's
      `json` module actually does (last-wins is the CPython behavior; verify, don't assume) and
      write the test against the confirmed behavior, not an assumption.
- [ ] Deeply nested / recursive JSON body — confirm MicroPython's `json.loads()` has a sane
      recursion bound on this platform (embedded stack is small; this is a real crash vector, not
      theoretical) and that hitting it degrades to a clean rejection, not a hard fault.
- [ ] Body at/near `max_content_length` — boundary-tested both just under and just over.

**C. Registration API tests** (generator-readiness shape — lists at init):
- [ ] A list with zero entries for any registration group (e.g. no sensors registered) produces a
      well-formed empty response, not an exception.
- [ ] A list with one entry behaves identically whether supplied via the list-based API or
      hand-constructed — no special-casing "one module" vs "many."
- [ ] Registering the same module twice (a generator bug, not an expected real case) — **decided**:
      last-registration-wins, not by adding any dedup/guard code but simply because the natural,
      simplest implementation (loop over the registered list, write each entry's dict under its own
      name key: `for item in items: result[item.name] = ...`) already behaves that way by
      construction — chosen specifically because it's the option needing zero extra code, per the
      owner's "whichever comes with least effort/complexity" framing. Test confirms this fall-out
      behavior, it isn't a feature to implement separately.

**D. Error aggregation / reset tests**:
- [ ] `/status`'s `errcount` includes one entry per module *and* one per `ConfigManager` instance
      (`CFGMGR_<name>`), built from the same registry list used elsewhere (mirrors
      `_collect_level_setters()`'s "every logger, including nested `cfgmgr.pr`" shape).
- [ ] `"counter"` is always present; `"history"` is present exactly when the underlying logger
      actually persists `ErrNum`/`ErrType` entries — test both a populated and an all-zero history.
- [ ] `ResetErrors` calls `reset_error_counter()` on every module in the same registry — including
      `NeopixelDriver`/`DNSServer`/`ConfigManager` now that the coverage gap above is resolved
      (added inline this step, per the "known gaps" resolution above).
- [ ] A `reset_error_counter()` call on one module never affects another module's counter/history.
- [ ] The webserver service's own `errcount` entry accumulates a **warning** (`pr.wrn_s`, not
      `pr.err_s`) every time a connection is reclaimed via the per-call timeout or the outer
      per-connection cap — decided in response to "would be good to see when a connection ran into a
      timeout even without a full restart, warning in that case, no error." This is real, useful
      telemetry that survives dropping the whole-server-restart mechanism (question 1/8's
      resolution below): a rising warning count in `/status.errcount.<WebserverModuleName>` is what
      operational visibility into "clients are timing out" looks like now, in place of the
      restart-count field a bespoke restart mechanism would otherwise have surfaced.

**E. GET snapshot/copy-safety tests** (regression coverage for the "full copy, no live references"
finding above):
- [ ] For at least one settings endpoint, interleave a concurrent PUT with a GET in the test event
      loop and assert the GET response is never a mix of pre- and post-write field values (should
      hold everywhere except the already-flagged `SCD30`/`BMP3xx` live-readback fields).
- [ ] A dedicated **characterization test** (expected to demonstrate the known gap, not to pass
      cleanly) for `SCD30_Reader`/`BMP3xx_Reader`'s torn-read behavior — documents the gap in a
      runnable form so a future fix (see the new BACKLOG.md entry) has a red test to turn green,
      instead of the gap being only prose.
- [ ] Mutating a list/dict returned from any getter (`get_dict_data`/`get_dict_cfg`/
      `get_error_counter`) never affects the module's own internal state on a subsequent call.

**F. Connection-lifecycle robustness — "must all self-heal"** (this is the deep-networking testing
the owner asked for; grouped by where in a connection's life each scenario happens. **Updated after
section G's source research and the owner's decisions on the 10-question round** — every item below
reflects the simplified reject-when-full + per-call-timeout + outer-cap scheme, not the original
threshold-restart sketch; see "Owner decisions on the 10 questions" below for the full derivation
of each change):

*F.1 — Before/at accept:*
- [ ] Client opens a TCP connection and sends nothing, ever (the actual 2026-08-03 incident shape)
      → reclaimed by the per-call timeout, open-count decremented, no leak.
- [ ] Client opens then immediately closes (RST or FIN) before sending any bytes → clean
      decrement, no exception escapes the connection task.
- [ ] Rapid connect/disconnect churn (many short-lived connections in quick succession) → counter
      stays accurate, no double-decrement, no drift.
- [ ] Legitimate concurrent connections at/near the TCP-PCB ceiling (5) → all accepted and served
      normally up to the ceiling; the next one, while still at the ceiling, is silently closed
      (decision 3 — reject-when-full, no response written) purely because of count, never because of
      anything about that connection itself; confirms genuinely healthy load never gets torn down or
      degraded, just briefly refused until a slot frees.
- [ ] A connection refused only because the ceiling was momentarily full succeeds immediately on
      retry once any other connection's slot frees (via normal completion or a timeout reclaim) —
      confirms "reject when full" is a transient backpressure signal, not a standing failure.

*F.2 — Mid-request, headers/request-line:*
- [ ] **Resolved, now a concrete test**: a client trickling the request line/headers one byte at a
      time, each byte arriving just under the per-call timeout, stays alive far longer than any
      single per-call timeout would suggest — but is still reclaimed once the new **outer
      per-connection wall-clock cap** (wrapping the whole `handle_request()` call, decision 2) is
      exceeded, regardless of how the client paces its trickle. This is the concrete Slowloris test;
      see F.7 for the dedicated multi-connection version.
- [ ] Malformed request line/headers (garbage bytes, bad HTTP version, oversized header) → Microdot's
      own parsing failure path exercised, connection closed cleanly, no crash. Confirmed from source
      (`ext/microdot.py`'s `Request.create()`/`handle_request()`): a truncated/malformed request line
      already degrades safely via `handle_request()`'s own blanket `except Exception` catch — no
      extra handling needed on our side for this specific shape, only test coverage confirming it.
- [ ] `Content-Length` larger than the body actually sent, then the client goes silent → the
      `readexactly()` proxy call times out the same as any other wedge (or is caught by the outer
      cap if it's paced rather than fully silent).
- [ ] `Content-Length` exceeding `max_content_length` → confirmed `@app.errorhandler(413)` fires
      with the project's shaped response, connection still closes/decrements cleanly.
- [ ] Body genuinely truncated (client sends FIN mid-body, not just going silent) → **resolved,
      source-confirmed**: MicroPython's `Stream.readexactly()` raises `EOFError` on an early clean
      peer close (`extmod/asyncio/stream.py`, `v1.28.0`) — not an `OSError` subclass, so it needs its
      own explicit `except EOFError` arm in the `serve()` wrapper, alongside the existing
      `TimeoutError`/`OSError` handling, treated the same defensive way (log via `pr.wrn_s`, end this
      one connection's task, `finally`-decrement the counter).

*F.3 — Mid-request, JSON body:* covered by section B above (sparse-JSON semantics under malformed/
adversarial input), applied per-endpoint.

*F.4 — Mid-response, write phase:*
- [ ] Client disconnects while the server is mid-write of a large response body (e.g. `/status`
      with a long error history) → `awrite()`/`drain()` hits the wrapped timeout, the outer
      per-connection cap (both now cover this phase too, since it wraps `handle_request()` as a
      whole, not just the request-reading half), or an immediate `OSError` (broken pipe/
      `ECONNRESET`) — handled the same defensive way as every other wrapper-level failure, exercises
      `SPECIFICATION.md` A.5's flagged `Response.write()` gap directly, not just noting it exists.
- [ ] A route handler's return value fails JSON serialization (raw bytes, `NaN`/`Infinity` float,
      an accidentally-circular structure) → caught, logged with enough detail to identify the
      offending endpoint/module, answered with the consolidated error shape instead of a bare
      crash.
- [ ] Worst-case `/status` response size (longest configured error history across every module) →
      measure `gc.mem_free()` before/after under the Unix port; confirm building the full response
      dict before serialization doesn't spike memory unacceptably on a constrained device. Confirmed
      unrelated to the outer-cap addition (question 9) — a capped connection still has to build and
      hold the same full response dict either way, so this test's bar doesn't change.

*F.5 — After response / close:*
- [ ] Normal close: counter decrements exactly once, connection task actually exits (never a
      zombie task invisible to `start_and_check_tasks()`).
- [ ] **Resolved, no longer an open question**: `ext/microdot.py`'s `handle_request()` calls
      `Request.create()` → `dispatch_request()` → writes the response → unconditionally
      `await writer.aclose()`s, exactly once per accepted connection — this vendored Microdot has
      **no HTTP keep-alive support at all**. One connection is always exactly one request; the
      per-call-vs-per-request timeout-scope question collapses (they're the same thing by
      construction). Per decision 7 ("do whatever is in accordance with the official protocol
      spec"): `ext/microdot.py`'s `Response.write()` sends a literal `HTTP/1.0` status line, and
      HTTP/1.0's spec default is already non-persistent, so nothing is *required* here — but per
      RFC 7230 §6.6's recommendation for a server that intends to close after responding (most
      relevant if a client sent `Connection: keep-alive`, the legacy HTTP/1.0 extension), add an
      explicit `Connection: close` response header via Microdot's own supported `after_request` hook
      (no edit to the vendored file needed) so any keep-alive-aware client gets an unambiguous
      signal instead of relying on it to notice the socket closing.
- [ ] `Connection: close` is present on every response, including error responses (400/404/405/
      413/500), not just the happy path.
- [ ] Double-close paths (our own `finally` plus any cleanup Microdot itself already does) don't
      raise or double-decrement the open-connection counter.

*F.6 — Concurrency / resource-ceiling behavior* (renamed from "whole-server restart" — **decision
1**: that mechanism is dropped, see "Owner decisions" below for the full reasoning; this section now
tests the reject-when-full + outer-cap scheme's concurrency behavior directly, with no restart step
anywhere in it):
- [ ] N simultaneous wedged/slow-trickle connections, up to the ceiling, are each independently
      reclaimed by their own outer-cap timeout — no coordination between them, no shared state
      beyond the open-connection counter, no whole-server action ever triggered by their number.
- [ ] Immediately after each reclaim, the freed slot is available to a new connection right away —
      confirms there's no artificial cooldown/grace-period gap between a reclaim and the next accept
      (unlike the old design's restart grace period, which no longer exists).
- [ ] Pathological repeated rewedging (a broken/hostile client immediately reconnecting and
      rewedging right after each reclaim) — **resolved**: worst case is bounded to "ceiling slots
      occupied for at most one outer-cap duration, repeatedly," which can never grow unbounded and
      never needs `_TASK_FAIL_MAX` escalation, since no single mechanism (task, counter, or timer)
      is shared across attempts the way a whole-server restart would have been. Test confirms this
      bound holds under sustained rewedging, not just a single cycle.
- [ ] A secondary hard bound on the per-connection cleanup path itself: force a fake `aclose()`/
      `wait_closed()` call to hang past the outer cap and confirm the connection task still ends
      (doesn't leak past a further grace bound) — the per-connection analogue of the old design's
      "harder timeout" idea, now scoped to one connection instead of the whole server, since there's
      no whole-server object left to force-close.

*F.7 — Adversarial/malformed-input shapes* (LAN-only device, but cheap defensive discipline):
- [ ] Extremely long URL path/query string.
- [ ] Unknown path → confirmed `404` handler, shaped response, not a bare crash.
- [ ] Wrong HTTP method on a known path → confirmed `405` handler.
- [ ] Path-traversal-looking or trailing-garbage segments on a known route.
- [ ] Dedicated Slowloris-shaped simulation (many connections, up to the ceiling, each trickling
      single bytes) → confirms every one of them is independently reclaimed by the outer cap within
      a bounded time, and that new legitimate connections can be accepted again as each slot frees —
      the concrete multi-connection version of F.2's single-connection Slowloris test.

*F.8 — Server startup edge cases:*
- [ ] `asyncio.start_server()` failing to bind (e.g. port already in use from an unclean previous
      instance, `OSError(EADDRINUSE)`) — **resolved, source-confirmed**: `start_server()`
      (`extmod/asyncio/stream.py`) already sets `SO_REUSEADDR` before `bind()`, so a clean
      close-then-rebind of our own listening socket won't hit `EADDRINUSE` against itself; a genuine
      conflict would need a second, different process holding the port, unrealistic on this
      single-application device. Ordinary task-retry (`start_and_check_tasks()`'s existing behavior)
      is sufficient — test confirms the retry path is actually reached, not that anything special
      needs building.
- [ ] Webserver task starting before the WiFi interface has actually associated — **resolved,
      source-confirmed**: `start_server()` calls `socket.getaddrinfo(host, port)` where
      `host='0.0.0.0'` is an IP literal (no DNS resolution, no blocking on network-not-ready); the
      lwIP/socket layer doesn't require an active WiFi association to bind/listen — the socket just
      sits idle until routing/IP is actually up. No special-casing needed; test confirms the
      webserver task starts and stays alive when launched before WiFi association completes.

*F.9 — Supervisor integration / soak (capstone tests for this whole section):*
- [ ] A webserver task that genuinely dies (e.g. an unhandled exception escaping the accept loop
      itself, not an ordinary per-connection reclaim) is picked up and restarted by
      `start_and_check_tasks()` through the real, unmocked supervisor path — the only restart path
      that exists for this module now, same as every other.
- [ ] Repeated webserver-task failures reach `_TASK_FAIL_MAX` and escalate to the existing
      watchdog-starve fallback exactly like any other supervised task — no special-casing.
- [ ] The soak test already specified in BACKLOG.md's design sketch step 5, adapted to the
      simplified scheme: 100+ start/wedge/reclaim cycles under the Unix port (no restart step in the
      normal case), `gc.mem_free()` flat throughout, and the webserver task's own supervised-restart
      count staying at zero across the whole run — confirming the task itself never actually needs
      the generic supervisor's intervention under sustained wedge/reclaim load, only under a
      genuinely forced failure (the two bullets above) — the pass/fail bar this whole section builds
      toward.

**G. Open design questions this action list surfaced — all six now resolved by direct source
research** (owner direction: "most of them can be solved by documentation or code research by you,
so go ahead," plus a standing simplicity mandate for the whole connection-handling scheme — *"If
all connections/sockets are in use, just don't accept new ones. If a connection is stale or
inactive for a settable timeout, drop it and free resources. Never wedge indefinitely."* Every
finding below is sourced directly from the pinned `v1.28.0` MicroPython tag's
`extmod/asyncio/stream.py` (fetched verbatim, not recalled from training data — CLAUDE.md's
doc-currency rule) and from `ext/microdot.py` itself, not inferred):

1. **Per-call timeout vs. per-request wall-clock cap — resolved: need both, and the reason is now
   concrete, not hypothetical.** Confirmed by reading `ext/microdot.py`'s `handle_request()`
   directly (line ~1397-1419): it calls `Request.create()` once, dispatches once, writes the
   response, then unconditionally `await writer.aclose()`s — **one request per accepted
   connection, always**, no loop back to read a second request (see item 3 below — this also
   settles keep-alive). Given that shape, a per-call inactivity timeout on `readline()`/
   `readexactly()` (BACKLOG's original design) does **not** defeat a paced Slowloris client: each
   trickled byte arriving just under the per-call timeout resets it indefinitely, and the
   "reject when full" rule only bounds *how many* such clients can wedge at once (up to the
   connection-count ceiling), not *how long* any one of them wedges. **Resolution**: add one more
   mechanism, not a replacement — wrap the *entire* per-connection `handle_request()` call in a
   single outer `asyncio.wait_for(..., OUTER_CAP)`, independent of and in addition to the existing
   per-call wrapping. The outer cap is what actually satisfies "never wedge indefinitely"
   regardless of activity pattern; the per-call timeouts remain useful for reclaiming a genuinely
   silent connection well before the outer cap expires. (Exact `OUTER_CAP`/per-call values are a
   real tuning decision — see the fresh question list below, this isn't picking numbers.)
2. **`readexactly()`'s early-close behavior — resolved: raises `EOFError`, confirmed from source,
   distinct from the `TimeoutError`/`OSError` path.** `extmod/asyncio/stream.py`'s `Stream.
   readexactly()`:
   ```python
   async def readexactly(self, n):
       r = b""
       while n:
           yield core._io_queue.queue_read(self.s)
           r2 = self.s.read(n)
           if r2 is not None:
               if not len(r2):
                   raise EOFError
               r += r2
               n -= len(r2)
       return r
   ```
   A clean peer close mid-body (socket read returns `b""` with bytes still outstanding) raises
   `EOFError` — not an `OSError` subclass, so it will **not** be caught by the already-specified
   `except OSError` handling and must get its own explicit `except EOFError` arm in the `serve()`
   wrapper, treated the same defensive way (log, end this one connection's task, `finally`-decrement
   the counter). **One extra finding worth folding in**: `Stream.readline()` behaves differently on
   early close — it does **not** raise anything; it just returns whatever partial bytes were
   buffered (possibly with no trailing `\n`) the moment the underlying read returns empty. Checked
   against `ext/microdot.py`'s own `Request._safe_readline()`/`Request.create()` (line ~387-421):
   `Request.create()` already wraps its `readline()`-driven request-line/header parsing in a
   blanket `except Exception` (via `handle_request()`'s own outer catch, per `SPECIFICATION.md`
   A.5's already-documented guarantee), so a truncated request line unpacking into too-few values
   (`method, url, http_version = line.split()` on a partial line) already degrades safely today
   with no extra code needed on our side — good confirmation, not a new gap.
3. **HTTP keep-alive — resolved: not supported by this vendored Microdot at all.** Same
   `handle_request()` read as item 1: one connection is always exactly one request, then an
   unconditional close. There is no per-connection request loop anywhere in `ext/microdot.py`.
   This collapses the per-connection-vs-per-request timeout-scope question entirely — they're the
   same thing by construction, nothing to revisit before implementation.
4. **In-flight connections during a whole-server restart — resolved: completely unaffected,
   confirmed from source.** `extmod/asyncio/stream.py`'s `Server.close()` only does `self.state =
   True; self.task.cancel()` — `self.task` is the `_serve()` *accept loop* coroutine. Its
   `except core.CancelledError` handler closes the *listening* socket and returns; nothing else
   happens. Each accepted connection's handler, though, was spawned independently via `core.
   create_task(cb(s2s, s2s))` inside that same accept loop — a **separate, unrelated task** with no
   parent/child relationship to the server task. Cancelling or awaiting the server task neither
   cancels nor waits on any already-running connection task. **Conclusion**: a restart (closing and
   reopening the listening socket) never tears down a legitimate in-flight connection — it keeps
   running on its own until it finishes normally or hits its own per-call/outer-cap timeout.
5. **Repeat-rewedge-after-restart backoff — resolved: structurally unnecessary once items 1+4 are
   both in place, though this reframes rather than just answers the original question.** With (a)
   "reject when full" bounding concurrent wedged connections to the connection-count ceiling, and
   (b) the new outer per-connection wall-clock cap from item 1 guaranteeing every connection —
   wedged or not — is force-reclaimed within a bounded time regardless of how it's being kept
   alive, the system can no longer accumulate an unbounded backlog no matter how fast a hostile
   client reconnects and rewedges: worst case is the ceiling's worth of slots occupied for at most
   one outer-cap duration, repeatedly. **This changes the shape of BACKLOG's "Microdot hardening
   design" more than it was expected to** — see the fresh question list below (whether the
   whole-server-restart mechanism is still worth keeping at all is now a live question, not
   settled by this finding alone, so it's not silently rewritten in BACKLOG.md here).
6. **Bind failure (`EADDRINUSE`) and pre-network-up startup — resolved: neither needs distinct
   handling from the existing task-retry path.** `extmod/asyncio/stream.py`'s `start_server()`
   already does `s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)` **before** `s.bind(...)`
   — so our own clean restart-rebind (closing our own listening socket, then calling `asyncio.
   start_server()` again) will not hit `EADDRINUSE` against our own just-closed socket; a genuine
   conflict would require a second, different process holding the port, which isn't a realistic
   shape on this single-application embedded device. Pre-network-up startup: `start_server()` calls
   `socket.getaddrinfo(host, port)` where `host='0.0.0.0'` is an IP literal, not a hostname, so no
   DNS resolution (and no blocking-on-network-not-ready) occurs; binding/listening at the lwIP/
   socket layer doesn't require an active WiFi association — the listening socket simply sits idle
   until routing/IP is actually up, at which point real clients can reach it with no restart
   needed. Ordinary task-retry (already the existing behavior for any task failure) is sufficient
   for both cases — no special-casing needed for either.

**Step 2's 10 clarifying questions — revisited** (per the per-step-session workflow's step 2; the
original "Original scoping discussion" 10-item Q&A above predates the five-branch restructuring and
every item in it that touched Step 2 is now settled — item 1's residue ("which values land in the
single structured status endpoint vs. get their own route") by the Endpoint Design subsection
above, items 2/3/5 by not being Step 2's concern at all, items 4/6/7/9/10 by direct settlement
already recorded inline, item 8 structurally by the branch-per-step scheme itself — so none of the
original ten survive as open questions for this step specifically. Section G's six questions are
also now resolved (immediately above). This is accordingly a fresh round, not a continuation,
padded back to ten with what's left genuinely undecided after all of the above):

1. **Keep or drop BACKLOG's whole-server-restart backstop?** Section G item 5's finding: with
   "reject when full" plus the new outer per-connection wall-clock cap, every connection — wedged
   or not — is force-reclaimed within bounded time and the connection count can never exceed the
   ceiling. The original reason for a threshold-triggered whole-server restart (an accumulating
   backlog the per-call timeouts alone couldn't reclaim) no longer applies once the outer cap
   exists.
   - *Option A — drop it.* Simpler, fewer moving parts (matches "the scheme shall be simple"),
     removes an entire task-supervisor-integration surface (shrinks F.6/F.9 substantially).
   - *Option B — keep it as pure defense-in-depth.* Guards against a class of bug the outer cap
     itself can't self-heal (e.g. a leak in the connection-counter's own bookkeeping, or a future
     bug in the outer-cap wrapper) — but means writing and soak-testing a mechanism expected to
     never fire under normal operation.
2. **Outer per-connection wall-clock cap and per-call timeout values.** Given item 1 above needs
   both mechanisms regardless of the restart decision — what are sensible numbers for each, and
   should the outer cap be one global constant for every endpoint, or does `/status`'s
   worst-case response (longest configured error history across every module, per action-list item
   F.4) need a longer allowance than a small settings PUT? Real deployed-unit WiFi conditions
   should inform this, not a guess.
3. **Capacity-rejection behavior when at the connection-count ceiling.** Silently close the new
   connection immediately (cheapest, no risk of the rejection path itself becoming a new wedge
   vector, matches "just don't accept new ones" literally), or accept briefly and write a real
   `503`-shaped response first (more informative to a well-behaved client or monitoring tool, but
   costs the exact accept-and-hold behavior the "don't accept" rule is meant to avoid)?
4. **`SCD30_Reader`'s setter shape** (the first "known gap" already flagged above) — no generic
   `_set_dict_cfg`-style method exists today, individual named methods only. Add a schema-driven
   generic setter to `asy_scd30_driver.py` itself (consistent with every other sensor driver,
   reusable outside the webserver too), or keep a bespoke per-field dispatch table local to the
   webserver layer just for this one sensor?
5. **`reset_error_counter()` gap on `NeopixelDriver`/`DNSServer`/`ConfigManager`** (the second
   "known gap" already flagged above) — same category of completeness gap Step 1 closed for
   `get_error_counter()` on the first two of these three. Does closing it belong retroactively in
   Step 1 (construction-time module completeness, its own established precedent), or is it fine to
   add inline during Step 2's own implementation pass, since Step 2 is the first real consumer of
   `/status`'s `ResetErrors`?
6. **Duplicate registration in the "lists at init" registration API.** A generator bug, not a real
   runtime case, but the action list (section C) already requires a *defined, tested* behavior
   rather than accidental behavior. Last-registration-wins, first-registration-wins, or hard
   rejection (raise at registration time, catching a generator bug immediately instead of silently
   misbehaving at runtime — arguably the most useful of the three for exactly this failure mode)?
7. **`Connection: close` response header.** Every connection is unconditionally closed after its
   one response regardless of what any header claims (section G item 3). Worth explicitly setting
   this header anyway for protocol-correctness/clarity to a well-behaved client, or genuinely
   unnecessary busywork given the actual socket behavior already enforces it?
8. **Webserver restart-count visibility in `/status`** (only a live question if item 1 above keeps
   the restart mechanism) — surfaced as its own `errcount`-style entry (the module already needs
   `get_error_counter()`/`get_task_starters()` per the settled design, so the plumbing exists), or
   kept purely internal/log-only with no REST-visible trace?
9. **Does the outer-cap addition (item 1/2) change anything about `/status`'s worst-case-size
   memory measurement** (action-list item F.4's `gc.mem_free()` check)? An outer-capped connection
   still has to build and hold the full response dict in memory before writing it either way, so
   this is likely a "no, unrelated" — but worth a deliberate one-line confirmation before
   implementation rather than an assumed no.
10. **Does the digital twin (Step 3) need to simulate degraded/slow network conditions at all** for
    Step 2's own connection-lifecycle tests to be meaningful under the Unix port, or are those tests
    entirely satisfiable with hand-scripted fake reader/writer doubles (per the existing
    `_StepPoller`-style precedent from `test_asy_uart_driver.py`'s CI-hang fix) without needing
    Step 3 at all? Worth settling now since it affects whether any of Step 2's F-section tests have
    an undeclared dependency on Step 3 landing first.

**Owner decisions on the 10 questions — resolved, with derived consequences** (answered in full;
every design/test-list section above has already been updated to match — this subsection is the
single place the *decision plus reasoning* lives, so it doesn't have to be reconstructed from the
scattered inline edits):

1. **Whole-server-restart backstop — dropped.** Owner's own framing: keep it only if some class of
   error could escape the reject-when-full + outer-cap scheme; otherwise drop it, since the generic
   "restart if stopped" supervisor (`start_and_check_tasks()`) already applies to this module like
   every other. Traced through concretely, nothing escapes: (a) per-connection resource/timing
   failures (silence, Slowloris trickle, a hang inside `dispatch_request()`/route-handler logic) are
   now fully bounded by the outer per-connection cap, which covers the *entire* `handle_request()`
   call, not just stream I/O — this is strictly more coverage than the old restart mechanism had,
   since `dispatch_request()` was never in scope for per-call stream timeouts either way; (b) the one
   failure mode neither the old restart *nor* the new outer cap can actually help with is a truly
   synchronous, no-`await`, hardware-level stall (the same class CLAUDE.md's I2C-wedge policy already
   settles as "the hardware watchdog is the accepted backstop, not a software fix to chase") — if
   that ever happens, it stalls the *entire* event loop, including whatever task would have detected
   the restart threshold and driven the restart itself, so the old mechanism was never actually a
   working backstop for that specific case either. Net: dropping it loses no real coverage, and the
   webserver's own task already gets the generic supervisor's restart-then-escalate treatment simply
   by being registered in `start_and_check_tasks()`'s list, exactly like every other module — nothing
   bespoke needed. **BACKLOG.md's "Microdot hardening design" entry updated to match** (see below).
2. **Outer-cap/per-call timeout values — one global constant, hardcoded at init, reality-checked
   later.** Both values become constructor parameters to the webserver service (not internal-only
   constants), but per the owner's direction they still land as **fixed values supplied once at
   construction time**, grouped with `src/sensortask_wozi.py`'s other hardware-related fixed
   constants (mirrors `_MAX_MODULE_ERROR`/DNS/NTP timeout placement from Step 1's "Constants
   organization" precedent, and the WDT/mempause "hardcoded, not REST-exposed" precedent) — never a
   per-route or per-endpoint value. Start with sensible defaults sized around worst-case *legitimate*
   conditions (weak WiFi, larger transfers), explicitly flagged as needing a real reality-check
   against actual deployed-unit network behavior before being trusted (Step 5's soak/real-hardware
   phase is the natural point to revisit them, not a number to get exactly right now).
3. **Capacity-rejection — silent close, as originally sketched.** No 503 response; a new connection
   arriving while at the ceiling is simply not accepted (or accepted-and-immediately-closed with zero
   bytes exchanged) — cheapest, and doesn't risk the rejection path itself becoming a resource
   consumer, matching "just don't accept new ones" literally.
4. **SCD30 setter shape — schema-driven dispatch, no persistence layer.** See the "Known gaps"
   resolution above for the full mechanism (a new SCD30-local generic setter mirroring
   `_set_dict_cfg()`'s shape but calling straight through to the sensor's existing individual setter
   methods, no `cfgmgr`/local file).
5. **`reset_error_counter()` gap — closed inline during Step 2.** Not retroactively folded into Step
   1; added lean and consistent with each module's own existing shape, per the owner's explicit "it
   does not matter how" framing.
6. **Duplicate registration — last-wins, by construction, zero extra code.** The simplest possible
   per-item loop already behaves this way; deliberately not adding a dedup/guard check, since that
   would cost more code for no benefit the owner asked for.
7. **`Connection: close` header — added, per official protocol guidance.** `ext/microdot.py` speaks
   HTTP/1.0 (confirmed from `Response.write()`'s literal status line), whose spec default is already
   non-persistent — but RFC 7230 §6.6 recommends a server that intends to close after responding say
   so explicitly, especially relevant to a client that requested the legacy HTTP/1.0
   `Connection: keep-alive` extension (which Microdot ignores outright, closing regardless). Added via
   an `after_request` hook, not by touching the vendored file.
8. **Webserver restart-count visibility — becomes its own `errcount` entry, repurposed as a
   timeout-warning counter.** With no bespoke restart mechanism left (decision 1), there's no
   restart count to surface — but the owner's actual underlying want ("see when a connection ran
   into a timeout even without a full restart, as a warning") is fully served by the webserver
   module's own `get_error_counter()` entry accumulating a `pr.wrn_s()` warning on every per-call or
   outer-cap reclaim. Arguably better observability than a restart counter would have given, since it
   now fires on the first sign of trouble, not only once a whole-server threshold was crossed.
9. **`/status` worst-case memory measurement — confirmed unrelated to the outer-cap addition**, no
   change to that test's design.
10. **Step 2's own tests stay independent of Step 3's digital twin.** Confirmed: the twin is for
    manual/integration testing (Step 5), deliberately kept separate from the unit-test set; Step 2's
    F-section connection-lifecycle tests use hand-scripted fake reader/writer doubles exclusively
    (matching the `_StepPoller` precedent), with no dependency on Step 3 landing first.

### Step 3 — Digital-twin hardware simulator

**Goal**: a new module, sitting at the same `machine`-module raw-bus-transaction mocking boundary
`tests/machine.py` already establishes for unit tests (not modified, not reused, not a higher-level
driver stand-in), but built for a different purpose: real-time-firing `Timer`s and sensible
in-range random simulated sensor values, so Step 5 can run the whole assembled prototype under the
Unix port and see it behave like it's actually attached to hardware, not just satisfy a hand-driven
test double.

**Known findings to carry in**:

- `tests/machine.py`'s `Timer` fake only fires on manual `.trigger()` — deliberately, since it's
  scoped to deterministic unit tests. The digital twin needs its own `Timer` that actually fires on
  a wall-clock schedule (e.g. backed by a real thread or asyncio-driven scheduler under the Unix
  port), which is exactly why it can't just be `tests/machine.py` with one method changed — it's a
  different fake with different goals, hence the owner's explicit "separate, new module" framing.
- Per-sensor value ranges must come from `datasheets/` (SGP40, SCD30, BMP3xx PDFs) — read them
  directly for realistic operating ranges, don't rely on general training-data familiarity with
  these parts (CLAUDE.md's standing datasheet rule).
- Bus wiring stays untouched (owner-confirmed) — the twin only needs to answer the same raw
  I2C/SPI transactions `tests/machine.py` already answers for these three sensors, just with
  randomized-but-plausible bytes instead of hand-scripted fixture values, and on a live timer
  instead of manual stepping.

**Doc links**: `tests/machine.py` (read-only reference for the transaction shapes to match — grep
each `_Sgp40Sensor`/`_Scd30Sensor`/`_Bmp3xxSensor`-equivalent fixture already in the file for the
exact byte-level protocol each chip expects), `datasheets/` (SGP40/SCD30/BMP3xx PDFs — read first
for any register-map or value-range claim), BACKLOG.md's "Owner requirement for the final wiring
stage" entry (the origin of this whole requirement).

**Criteria for this step to finish**: new module built at a location outside both `src/` and
`tests/` (see "Where the new code actually lives" above); drives all three sensors' real I2C/SPI
transaction shapes with real-time-firing timers; produces values that stay in each datasheet's
documented sensible range; fully unit-tested (deterministic tests of the twin's own transaction
responses, not flaky wall-clock-timing assertions); does not touch `tests/machine.py` at all.

**What Step 5 needs from this step**: a documented, minimal way to swap the twin in for a Unix-port
run (most likely `MICROPYPATH`/`sys.path` ordering, matching how `tests/machine.py` is already
picked up transparently by existing tests) — `src/sensortask_wozi.py` itself should need zero
twin-awareness, no `if` branch anywhere distinguishing real hardware from simulated.

### Step 4 — Website placeholder scaffold

**Goal**: the full mechanical structure for serving the config/status website — gzip → freezefs
(`--on-import mount`) → frozen Python module → Microdot static-route serving — wired end to end
with **stub placeholder content only** ("Hello world"-shaped), not the real site. Real website
content is explicitly out of scope for this whole effort.

**Known findings to carry in**:

- `ext/freezefs/` is already vendored this session (freezefs 2.4, unmodified, MIT-licensed,
  committed to this branch). Current CLI:
  `python -m freezefs <infolder> <outfile.py> --on-import mount --target /<mount> [--overwrite always]`
  — **do not pass `--compress`**: it switches to on-device `deflate`-module decompression, which is
  incompatible with this project's existing approach (pre-gzip the files by hand, serve them with
  Microdot's `send_file(..., compressed=True, file_extension='.gz')`, which only sets the
  `Content-Encoding` header and never decompresses on-device). Mixing the two would mean double
  encoding or a broken `Content-Encoding` claim.
- The legacy `build-wozi.sh` pipeline (`cp` → `gzip -9` → `freezefs` → assemble into the firmware
  build) is the structural reference, even though its exact freezefs invocation
  (`python3 -m freezefs -s html frozen_html.py`) is stale against freezefs 2.4's current CLI (no
  `-s` flag anymore) — follow the pipeline's *shape*, not its literal command line.
- `html_raw/wozi/index.html` (and its sibling config pages) is the real site's actual content —
  useful as a reference for what fields/routes the real site eventually needs, but **not** what
  gets built this step; the stub replaces it with placeholder content that exercises the same
  pipeline.
- `improved-quality/sensortask-wozi.py` currently has `import frozen_html` at the top with no
  backing module — this step is what finally gives that import something real to resolve to (in
  `src/sensortask_wozi.py`'s equivalent import, not by editing the reference file).

**Doc links**: `build-wozi.sh` (pipeline shape), `ext/freezefs/archive.py` (current CLI/behavior —
read directly rather than trusting the stale legacy script), `ext/freezefs/ffsmount.py` (what
actually runs on-device, ~1KB RAM per the freezefs README), `html_raw/wozi/` (reference content,
not to be built for real).

**Criteria for this step to finish**: a placeholder `html_raw`-equivalent stub folder, a build step
that gzips it and runs it through `freezefs --on-import mount` (no `--compress`), a frozen module
importable under both the real build and the Unix port, and Step 2's static-route extension point
actually serving it (verify at least one stub route returns the right bytes with the right
`Content-Encoding` header); unit/integration-tested under the Unix port.

### Step 5 — Full Unix-port integration

**Goal**: assemble Steps 1-4's output into one working `src/sensortask_wozi.py` prototype, run it
end to end under the real MicroPython Unix-port interpreter with Step 3's digital twin standing in
for physical hardware, and verify it as close to real-target behavior as this project's tooling
allows without actual silicon — this is the concrete fulfillment of BACKLOG.md's "Owner requirement
for the final wiring stage" entry.

**Criteria for this step to finish**: a full boot-to-steady-state run under `scripts/test.sh`'s
interpreter (or an equivalent dedicated integration entry point, if the digital twin's
`MICROPYPATH` wiring needs to stay separate from the plain unit-test set — Step 3/5's own sessions
settle that) with no unhandled exceptions, the task supervisor never escalating to watchdog-starve
under normal simulated conditions, every REST endpoint from Step 2 reachable and returning
correctly-shaped data sourced from the twin's simulated readings, the Step 4 website stub served
correctly, and a soak run (matching Step 2's own soak-test bar) showing stable memory over time;
integration-level tests added following `tests/test_setter_microdot_integration.py`'s existing
pattern of exercising real dispatch without a real socket.

## Out of scope for all five steps

- Real website content (stub only, see Step 4).
- The future per-variant build-script generator itself (only its constraints are honored, per
  "Generator-readiness constraint" above).
- The other three deployed variants (arzi/neu×3) — this prototype is `wozi` only.
- Real-hardware build genericization and physical-hardware verification — comes after all five
  steps merge back and the large audit closes, not a branch of its own inside this scheme.
- Editing `improved-quality/sensortask-wozi.py`, `ext/microdot.py`, or `tests/machine.py`.
