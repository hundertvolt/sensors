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
(`scripts/test.sh`'s `MICROPYPATH="src:tests:frozen_modules:.frozen"` — the `frozen_modules`
segment was added in Step 4) — `improved-quality/` is not on that path and never will be, so a file
that stays there is structurally untestable under this project's own test infrastructure. The
prototype therefore gets built fresh as **`src/sensortask_wozi.py`**
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

One branch per step below, sequential. Every step branches off `claude/framework-wiring-rest-api-hx99v7`
(the trunk) at its then-current tip, and merges directly back into that same trunk branch before the
next step starts — **not** into the previous step's own now-stale branch. `claude/framework-wiring-rest-api-hx99v7`
is the one accumulating branch every step both forks from and lands on:

```
main
 └─ claude/framework-wiring-rest-api-hx99v7   (the trunk — global prep, PR #31)
     ├─ Step 1 branch  → merge back into claude/framework-wiring-rest-api-hx99v7
     ├─ Step 2 branch  (forked from the post-Step-1 trunk tip) → merge back into the trunk
     ├─ Step 3 branch  (forked from the post-Step-2 trunk tip) → merge back into the trunk
     ├─ Step 4 branch  (forked from the post-Step-3 trunk tip) → merge back into the trunk
     └─ Step 5 branch  (forked from the post-Step-4 trunk tip) → merge back into the trunk
                                                                    └─ large audit, then PR #31 → main
```

**The "large audit" in the diagram above is a separate, later effort from Step 6, not the same
thing** (confirmed directly by the project owner, after an earlier session's own recap of Step 6
left this genuinely ambiguous — both are described as happening "after Step 5 merges into the
trunk," which reads as one step without this clarification). Step 6 (`BACKLOG.md`'s open question
#6 — the full self-healing-system failure-mode audit: rare corner cases, memory leaks, race
conditions, silent failure masking, cascading recovery storms, `ticks_ms()` rollover, task/timer
resource leaks) is its own dedicated session, following the same branch-and-merge-back-into-trunk
pattern every step above already uses — forked from the trunk once Step 5 has landed there, merged
back into the trunk when done, the same way Steps 1-5 each were. The "large audit" is a distinct,
later pass conducted directly on the trunk branch itself (not a forked step branch of its own)
after Step 6 (and anything else still open) has *also* landed on the trunk — it is the final gate
before `claude/framework-wiring-rest-api-hx99v7` → `main` (PR #31) opens, not a stand-in for Step 6
and not satisfied by Step 6 alone.

Suggested branch names (each step's session can rename if it finds a better one, but should stay
inside this scheme so the sequencing is legible from branch names alone):

1. `claude/step1-wiring-construction`
2. `claude/step2-webserver-api-service`
3. `claude/step3-digital-twin-simulator`
4. `claude/step4-website-placeholder`
5. `claude/step5-unix-port-integration`

Each step's PR targets `claude/framework-wiring-rest-api-hx99v7` directly (not `main`, and not the
previous step's own branch) — only the final, already-open PR #31
(`claude/framework-wiring-rest-api-hx99v7` → `main`) ever targets `main`, once Step 5 merges and
the large audit closes. **This was ambiguous in an earlier revision of this diagram** — the
indentation there read as a cascading chain (each step merging into the previous step's own
branch), and Step 3's session followed that literal reading, fast-forwarding
`claude/step2-webserver-api-service` instead of the trunk. The trunk was fast-forwarded to pick up
Step 3's work after the fact (clean, since it was a strict ancestor — no conflicts). Steps 4 and 5:
branch from and merge back into `claude/framework-wiring-rest-api-hx99v7` directly, per this
corrected diagram, not per any previous step's own branch.

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

**Done** (this session, across two passes — see "Status update (implementation session)" and
"Status update (follow-up session)" below for the full detail): every criterion above is met.
`src/asy_webserver_service.py` exists and is wired into `src/sensortask_wozi.py`'s `build_system()`
against real driver objects (not test fakes); the 100+-cycle soak test passes with `gc.mem_free()`
flat; `src/asy_webserver_service.py` is at 99% line coverage; the detailed TDD action list
(sections A-G below) was the actual source list implemented against, not aspirational — its
individual `[ ]` boxes are left unchecked as an as-authored planning artifact (this whole document
is deleted post-merge per its own stated lifecycle at the top of the file, so nothing here is meant
to be a permanent, retroactively-curated audit trail) rather than a sign the work is outstanding.
PR #33 (`claude/step2-webserver-api-service` → `claude/framework-wiring-rest-api-hx99v7`, per this
doc's own "Branch / session structure" section above) opened, CI-green (`lint-and-typecheck`/
`unit-tests` both passing, after one real `ruff` finding — `UP037`, an unnecessary quoted local-
variable annotation in `SCD30_Reader._set_dict_cfg()` introduced this session, since local
annotations are never evaluated at runtime and don't need the quoting `TYPE_CHECKING`-only imports
require on function signatures — caught by CI, fixed, verified clean locally, re-pushed), and merged
back into `claude/framework-wiring-rest-api-hx99v7`.

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

Not yet done as part of that pass (closed in a later session — see "Status update (follow-up
session)" below): wiring `WebserverService` into `src/sensortask_wozi.py`'s `build_system()` with
the real drivers, the soak test, and coverage-maximizing tests.

**Status update (follow-up session): the three items above are done.**

- **`reset_error_counter()` gap-closing** on `NeopixelDriver`/`DNSServer`/`ConfigManager` (each a
  one-line `await self.pr.reset()`, mirroring the shape every other module already has), plus a
  `.name` attribute added to every registrable module (`SensorReader.__init__` itself for the six
  subclasses that already pass `name=`, and one line each on `NeopixelDriver`/`DNSServer`/
  `ConfigManager`/`AsyFramManager`/`SystemService`) — needed because `asy_webserver_service.py`'s
  `_index_by_name()` keys every registration list on `item.name`, and no real driver had a top-level
  `.name` attribute before this (only `self.pr.name`), a gap that would have surfaced as an
  `AttributeError` the moment any real module was registered.
- **SCD30's schema-driven `_set_dict_cfg()`** landed in `asy_scd30_driver.py` per the plan's own
  "known gaps" resolution above: no persistence, each validated field dispatches straight to its
  existing individual setter, `ContMeas` handled directly inside this same method (not as a
  webserver-layer special case) so `asy_webserver_service.py` stays fully sensor-agnostic.
- **`SystemService` grew `get_dict_cfg()`/`_set_dict_cfg()`** (new, not in the original plan text) so
  `/system`'s `DebugLevel` field fits the same `SettingsGroup` shape as every other settings
  endpoint, without special-casing it in the webserver layer; `set_debug_level()` is now a thin
  wrapper over the new `_set_dict_cfg()`, behavior-preserving (verified against the existing test
  suite, including the "still pushes on `Unchanged`" case).
- **Real wiring**: `src/sensortask_wozi.py`'s `build_system()` now constructs a real `Microdot()` app
  and `WebserverService` once every module it registers exists (right after `conn.set_ext_led(pixel)`,
  the same cross-wiring point Step 1 already used) — `sensors=` (SCD30/BMP3xx/SGP40), `settings=`
  (mirroring the legacy setNetwork/setWiFiLED field-scoping split for `conn`, `ntp`'s NTP fields with
  `post_asy_fct=ntp.ntp_force_sync`, `sysfunct`'s `DebugLevel`, `ntp`'s GMTOffset/DSTOffset, and
  `notify_service`'s full combined schema read dynamically via `cm.schema_names()`), `system_cmd=`
  (dispatches to `sysfunct.reboot_system()`/`reboot_bootloader()`/`pause_permanent_storage(300)`),
  `notification_led=` (unpacks the `{r,g,b,t}` payload into `pixel.request_signal()`),
  `status_sources=`/`maintenance_sensors=` (new small callback functions in `sensortask_wozi.py`
  reading real live state off `conn`/`ntp`/`sysfunct`/`fram`/`notify_service`/`sgp_reader`), and
  `error_sources=` (a new `_collect_error_sources()` helper, the same 16-owner enumeration
  `_collect_level_setters()` already uses). The webserver's own task is appended to
  `_collect_task_starters()`'s returned list and its logger to `_collect_level_setters()`'s registry,
  same pattern as every other module.
  - **Deliberately not FRAM-backed**: unlike every other FRAM-chunk-owning module, `WebserverService`
    gets no `fram=` — it logs a warning on *every* per-call/outer-cap connection reclaim (decision 8),
    a rate a flaky/hostile client could drive far higher than any sensor's rare-hardware-fault log
    ever sees; persisting that to FRAM risked real wear-leveling pressure for no benefit this
    module's own diagnostics need. This also keeps WIRING_CONTRACT.md's five-chunk FRAM allocation
    order (Step 1) exactly as documented — no sixth chunk.
  - **Real bug found and fixed while wiring**, not part of the original Step 1/2 scope: `conn`
    (`AsyConnTime`) and `ntp` (`AsyNtpClient`) are `SensorReaderConfig` subclasses under the same
    sync-`__init__`/async-`setup()` pattern as `sgp_reader`/`bmp_reader`/`notify_service`, but nothing
    anywhere in the previously-constructed system ever called their own `cfgmgr.setup()` — confirmed
    directly (a write to `conn`'s config failed with `"Failed"`, `ConfigManager.write_config()`'s own
    `not self.valid` guard, until the fix). Neither `asy_wifi_service.py`'s `wlan_connect()` nor
    `asy_ntp_client.py`'s own task methods call `cfgmgr.setup()` internally either, so this was a real
    hole in Step 1's construction sequence, just never exercised by a real config-write path until
    this session's webserver PUT-route tests. Fixed by adding `await conn.setup()`/`await ntp.setup()`
    to the grouped setup() batch, positioned after `sysfunct`/`fram`'s already-fixed slots and before
    `sgp_reader`/`bmp_reader`/`notify_service` (matching their own real construction order, which
    precedes fram/sysfunct).
  - **"This service's own entry"** (the registration-API docstring's own contract, never actually
    implemented in the first implementation pass): `WebserverService` can't register itself into its
    own not-yet-constructed `error_sources` list, so `_build_errcount()` now adds a `"WEBSERVER"` entry
    directly from `self.pr.get_log()` instead, and `_put_status`'s `ResetErrors` handling calls
    `self.reset_error_counter()` alongside every registered module's own.
- **Soak test**: `tests/test_asy_webserver_service.py`'s F.9 test now runs the full 100+-cycle soak
  the finish criteria called for (20 warm-up cycles, then 120 measured cycles mixing wedged and
  well-formed connections at the `max_connections` ceiling), asserting `gc.mem_free()` stays flat
  (within a fixed tolerance) in addition to the connection-counter invariant the earlier 40-cycle
  stand-in already checked.
- **Coverage**: `src/asy_webserver_service.py` went from 93% to 99% line coverage (the one remaining
  miss, its module-level `_NAME = const("WEBSERVER")` line, is a `micropython.const()`
  compile-time-folding artifact of `sys.settrace`-based coverage collection, not a real gap — several
  other `_NAME = const(...)` lines project-wide show the same false-negative). New tests added:
  `_TimeoutStreamProxy.close()`/`wait_closed()` direct coverage, `_serve()`'s `EOFError`/`OSError`/
  generic-`Exception` branches (exercised by monkeypatching `app.handle_request()` directly, since
  the real Microdot integration structurally can't reach them - see those branches' own comments),
  `_close_writer()`'s exception-swallowing path, `_run()`/`_start_serving()` (a real
  `asyncio.start_server()` bound to an ephemeral loopback port), and malformed-body rejections for
  `/sensors` and `/status` PUT. `tests/test_sensortask_wozi.py` gained a new "Webserver wiring"
  section (17 tests) exercising the real registrations end-to-end - every settings group's post-hook,
  `SystemCmd` dispatch through the real (faked) `machine.reset()`/`machine.bootloader()`, the real
  `/status` shape, and `ResetErrors` against a real module's history.

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

**Refined plan — this session's own research, before the owner Q&A round** (extends the above per
Step 1/2's precedent; kept as its own subsection so the original scoping stays legible as the
starting point):

- **Protocol facts confirmed directly from `src/asy_sgp40_driver.py`/`asy_scd30_driver.py`/
  `asy_bmp3xx_driver.py` and their existing test files (`tests/test_asy_sgp40_driver.py` et al.),
  not assumed**:
  - **SGP40** (address `0x59`): word-oriented, no register addressing — `writeto()` a 2-byte command
    (optionally + compensation words), `readfrom_into()` a CRC-8-protected reply (`tests/machine.py`'s
    `I2C.read_queue` FIFO models this shape already). `initialize()` reads serial number (word[0]
    must be `0x0000`) then self-test (`0xD4xx` = pass, low byte ignored — a real driver bug the
    existing tests already regression-guard). `measure_raw()`/`get_raw()` return a 16-bit
    `SRAW_VOC` tick value. General-call reset is a single `0x06` byte to address `0x00`, not the
    device's own address.
  - **SCD30** (address `0x61`): word-oriented 16-bit commands, CRC-8-protected, via
    `readfrom_mem`-style register access built on the same command/response shape. `read_measurement()`
    polls `_CMD_GET_DATA_READY` then reads an 18-byte burst (`_CMD_READ_MEASUREMENT`): three
    big-endian `float32`s (CO2/temperature/humidity), each split into two CRC-8-protected 16-bit
    words. Also has an IRQ pin (`Pin.irq()`) the reader wires as a self-healing secondary trigger,
    alongside its own 500ms-periodic polling `Timer` — the twin's fake `Pin` needs a working
    `irq()`/edge-trigger path too, not just I2C.
  - **BMP3xx** (address `0x77`): register-addressed (`readfrom_mem`/`writeto_mem`), no CRC framing
    at all. `setup()` checks `CHIPID` register (`0x50`/`0x60`) then soft-resets. A read triggers
    forced-mode conversion (write `0x13` to `CONTROL`), polls `STATUS` for the data-ready bits, then
    burst-reads 6 raw ADC bytes (3 pressure + 3 temperature) from `0x04`. Compensation uses 11
    pressure + 3 temperature calibration coefficients read once from a 21-byte block at `0x31`
    (`asy_bmp3xx_driver.py`'s own `_read_coefficients()` has the exact unpack format and the
    per-coefficient scaling divisors) via a **cubic** polynomial (`asy_bmp3xx_driver.py:398-434`) —
    reproduced here since it's what makes this sensor's twin implementation meaningfully harder than
    the other two: producing *raw ADC bytes* that decode to a chosen target pressure/temperature
    means either inverting that cubic (solvable in closed form for a fixed calibration set, since
    temperature only needs a quadratic inversion and pressure is then linear in `adc_p` once
    temperature is known) or picking one fixed, plausible calibration-coefficient set once (e.g.
    reads real coefficients off a real chip once, hardcodes them, treats them as constant across
    a twin run) and doing the same closed-form inversion against target hPa/°C values, or simplest
    of all: skip the raw-ADC round-trip entirely and special-case the fake `readfrom_mem`/
    `writeto_mem` handlers for BMP3xx's exact register addresses so the *specific* driver-visible
    outputs (pressure, temperature, calibration block) come out plausible without ever running the
    inverse math for real — this only works because nothing else in the codebase reads BMP3xx's raw
    register bytes directly, only through this one driver. Flagged as one of the 10 questions below
    (value-generation strategy) since it changes how much of the driver's real math the twin actually
    exercises.
  - Every sensor's I2C `writeto(addr, b"")` zero-byte probe (`I2CDevice._probe_for_device()`,
    `asy_i2c_driver.py:241-253`) must ACK for these three addresses specifically — the twin's fake
    `I2C` should default to NAKing (`OSError(errno.EIO)`) any address it doesn't recognize, the
    opposite default from `tests/machine.py`'s open-bus-unless-explicitly-NAKed model, since a twin
    standing in for real hardware should behave like a real bus with only three real devices on it,
    not an unbounded fixture a test primes per-call.
- **Value ranges, read directly from the datasheet PDFs (CLAUDE.md's standing rule), not
  training-data recall**:
  - **SGP40** (`datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf`, v1.2 Feb 2022, Table 1):
    `SRAW_VOC` 0–65'535 ticks (clean-air baseline in the existing test fixtures sits around
    28'000–31'000, consistent with the datasheet's own sensitivity figures); VOC Index 1–500 (the
    processed value `voc_algorithm.py` derives from raw — the twin only ever needs to supply raw
    ticks, never a VOC Index directly, since the algorithm itself runs unmocked in the real driver).
  - **SCD30** (`datasheets/scd30/Sensirion_CO2_Sensors_SCD30_Datasheet.pdf`, Tables 1–3): CO2
    accuracy-guaranteed range 400–10'000 ppm (I2C measurement range extends to 40'000 but accuracy
    is undocumented above 10'000 — sensible-indoor-plausible values should stay well inside
    400–10'000, e.g. an 400–2000 ppm typical band with occasional excursions); humidity 0–100 %RH
    (sensible indoor band roughly 20–70 %RH); temperature −40–70 °C (sensible indoor band roughly
    15–30 °C).
  - **BMP3xx**: already confirmed directly in `asy_bmp3xx_driver.py`'s own operating-range check
    (`_read()`'s `300.0 <= pressure_hpa <= 1250.0 and -40.0 <= temperature <= 85.0`, itself sourced
    from "datasheet sec 1, Table 2") — sensible values should stay well inside that, e.g.
    950–1050 hPa / 15–30 °C for a plausible indoor/near-sea-level reading, since values outside the
    driver's own range check would make the twin's own output get rejected by the very driver it's
    supposed to be feeding.
- **Timer backing mechanism — asyncio-task-scheduled, not `_thread`.** `tests/machine.py`'s own
  docstring already confirms the Unix port's real `machine` module has no `Timer` at all
  (`PinBase`/`Signal`/`mem8`/`mem16`/`mem32`/`idle`/`time_pulse_us` only), so the twin's fake
  `Timer` is the only thing that can make `period=`/`callback=` fire on a real wall-clock schedule
  under the Unix port. Checked current MicroPython docs per CLAUDE.md's standing instruction:
  `docs.micropython.org` itself is blocked by this session's network egress policy, but the raw
  doc source (`_thread.rst`, fetched directly from the upstream GitHub repo) states outright that
  `_thread` "is highly experimental and its API is not yet fully settled" — not a page that's
  merely light on Unix-port specifics, an explicit "don't build load-bearing behavior on this"
  signal from upstream itself. Combined with this codebase's own standing single-threaded
  asyncio-cooperative design principle (CLAUDE.md/SPECIFICATION.md Part F.3 — "long-blocking
  operations must not stall timing-sensitive work", the retired `get_long_block_lock()` reasoning),
  a real OS thread is the wrong tool here anyway: every real `Timer` callback in this codebase is
  already trivial (`lambda b: event.set()`-shaped, setting a `ThreadSafeFlag` or incrementing a
  counter), so nothing about the twin's fidelity goal actually needs true preemption. Proposed
  mechanism: the twin's `Timer.init(period=, mode=, callback=)` spawns (`asyncio.get_event_loop().
  create_task(...)`) a small internal coroutine that `asyncio.sleep_ms(period)`s (looping if
  `PERIODIC`) then invokes `callback(self)` directly — same call signature real hardware uses,
  just scheduled cooperatively instead of from a real IRQ. `deinit()` cancels that task. This keeps
  the twin's entire implementation inside the same single-event-loop model the rest of the
  assembled prototype already runs under for Step 5's integration run, with no new threading-safety
  surface to reason about.
- **Randomization/determinism split.** The step's own finish criteria require the twin's *unit
  tests* to be deterministic (no flaky wall-clock assertions) while the twin's *live* behavior (the
  whole point of Step 5's run) needs to look genuinely randomized. Resolution: each sensor-fake
  object takes an injectable random source (a small callable/object defaulting to the real `random`
  module's functions) — tests inject a fixed-sequence fake source to assert exact byte-level
  protocol shaping (CRC bytes, byte order, register content) deterministically, while a live Step 5
  run uses the real default. This mirrors this codebase's existing "inject the seam, don't special-
  case test vs. prod" convention (e.g. `fram_ntp_callback`, `comp_callback`) rather than introducing
  a new one.
- **FRAM is a real open question, not obviously in scope.** `WIRING_CONTRACT.md`'s current
  construction order unconditionally wires `fram = AsyFramManager(spi0, ...)` into `build_system()`,
  and three modules (`sysfunct`, `sgp_reader`, `pixel`, `notify_service`) depend on FRAM chunks
  existing and `fram.setup()` succeeding for a real boot-to-steady-state run (Step 5's criterion) to
  complete without unhandled exceptions. But FINAL_WIRING_PLAN.md's own Step 3 scope, and
  BACKLOG.md's origin entry, both name only the three *sensor* chips. `tests/_fram_chip_fake.py`
  already plays this same "answer the real chip's own transaction shape" role for FRAM's SPI bus in
  unit tests, sitting on top of `tests/machine.py`'s fake `SPI` the same way this twin's sensor
  fakes sit on top of its own fake `I2C` — structurally the closest existing precedent for how a
  twin-side FRAM fake could be built, but it isn't itself restricted the way `tests/machine.py` is,
  so reusing it (or a twin-owned equivalent modeled on it) is a live option, not a hard blocker.
  Raised as question 3 below rather than assumed either way.
- **What the twin's `machine.py` needs to cover, beyond the three sensors.** Since `MICROPYPATH`
  resolves whole modules, not per-symbol, a twin `machine.py` used for a real Step 5 run has to be a
  complete stand-in for everything `src/`'s modules import from `machine` — not just `I2C`, but
  `Pin` (SCD30's IRQ), `Timer` (all three sensors' trigger timers plus `system_service.py`'s own
  timer sequencer), `WDT`, and `RTC` (`asy_ntp_client.py`). `UART`/`SPI` are only needed here if
  FRAM is in scope (question 3) — no other `src/` module Step 1-3 constructs touches either.
  `network`/`neopixel` (needed for `AsyConnTime`/`NeopixelDriver`) are separate, non-datasheet-backed
  fakes with existing unrestricted precedents already in `tests/` (`tests/network.py`,
  `tests/neopixel.py`) — reusing those directly for Step 5's run (rather than duplicating them into
  `digital_twin/`) seems like the natural boundary, but confirming that split explicitly is question
  4 below rather than assumed.
- **No CI-integrated live smoke test.** The finish criteria's "not flaky wall-clock-timing
  assertions" reads as a deliberate exclusion of any test that waits on real elapsed time inside the
  normal `scripts/test.sh` run. A short-period/generous-timeout live test (e.g. a 20ms period with a
  2s `asyncio.wait_for` bound, checking the callback fires *at least once*) is a different, much
  lower-risk shape than a strict timing assertion and is proposed as the one exception — covering
  "does the scheduling mechanism actually work at all," not "does it fire at a precise cadence" —
  but whether even that belongs in the default `scripts/test.sh` run or a separate, explicitly
  invoked check (mirroring Step 2's own soak test being separate from the fast default run) is
  question 5 below.

**Owner decisions on the clarifying-question round (11 questions asked, not 10 — the FRAM answer's
own "read back what was written to it... along restarts" raised two more, folded in as follow-ups
rather than deferred, per the workflow's "fair game at any point" allowance)**:

1. **Module name/location: `digital_twin/`**, matching the plan's own suggested name.
2. **Timer backing: asyncio-task-scheduled sleep loop**, not `_thread` — per the plan's own
   research above (`_thread` is upstream-confirmed "highly experimental").
3. **FRAM: in scope.** The twin answers FRAM's SPI transactions and must read back exactly what
   was written, including across process restarts.
4. **FRAM flush trigger: explicit `save_state()`/`flush()` call**, not a self-registered
   signal/`atexit` handler — whatever entry point Step 5 writes wraps `asyncio.run(main())` in
   `try/finally` and calls it on the way out. No reliance on MicroPython Unix-port signal-handling
   behavior this project hasn't verified.
5. **FRAM persisted-file format: JSON**, matching every other persisted-state file in this codebase
   (`ConfigManager` et al.) — not the illustrative "pickle" wording from the original answer, which
   isn't a reliably-available MicroPython module; raw bytes hex/base64-encoded into a JSON value.
   Written only on an explicit flush, never per-write, per the owner's own "don't do unnecessary
   write cycles" framing (SSD-hosted file).
6. **BMP3xx values: invert the real cubic compensation formula against one fixed, hardcoded,
   real-shaped calibration-coefficient block** — solves backward (temperature inversion is
   quadratic, pressure then linear in raw ADC) to produce raw ADC bytes that decode to a chosen
   target pressure/temperature. Exercises the real driver's own compensation math end-to-end.
7. **Fault injection: built in now, configurable**, not deferred — each sensor twin (and the FRAM
   twin) gets an injection surface (NAK/CRC-corruption/timeout-shaped, mirroring
   `tests/machine.py`'s own `inject_fault()`/`nak_addresses`/`busy` conventions where it makes
   sense) so a Step 5 run can also exercise the real drivers' error-handling/retry paths, not just
   the clean-read path. Off/clean by default; a constructor-level toggle turns it on.
8. **Twin's own unit tests: `tests/test_digital_twin_*.py`**, matching every other `src/` module's
   test-file convention (`scripts/test.sh` already discovers `tests/test_*.py` uniformly — no new
   test-running infrastructure). The module itself still lives in `digital_twin/`.
9. **Value evolution: independent random-in-range per read**, not a smoothed random-walk/drift
   model — matches the owner's own original framing literally, no extra state machine.
10. **Live-run seeding: supported.** The injectable-random-source seam every sensor twin needs for
    deterministic unit tests also accepts a real seeded `random.Random()` for a live Step 5 run, so
    a specific interesting/failing run can be reproduced on demand.
11. **`network`/`neopixel` fakes: duplicated into `digital_twin/`, not reused from `tests/`** — full
    independence from `tests/` at Step 5 runtime, at the cost of two near-identical copies to keep
    in sync going forward (accepted cost, owner's explicit choice over the reuse recommendation).

**`network.py` refinement, after the initial implementation pass (owner follow-up, same session)**:
the first cut made `WLAN.connect()` resolve to a connected state instantly - the owner's actual
intent was broader: simulate a successful connection through every real phase with reasonable
timing, and for actual data traffic, rely on the host computer's own real network. Investigated and
resolved: `network.WLAN` only ever gates the connection *state* `asy_wifi_service.py` polls
(`status()`/`isconnected()`) - real NTP/DNS/webserver traffic goes through the separate `socket`
module, confirmed to be a genuine wrapper around the host's real BSD sockets on the Unix port
(`src/asy_udp_socket.py`'s own `socket.socket(...)` call) - so once this twin reports "connected",
real traffic already reaches the real internet with nothing further to build. Rebuilt
`connect()` to transition `STAT_IDLE -> STAT_CONNECTING -> STAT_GOT_IP` over a real ~0.7s delay
(asyncio-task-scheduled, comfortably inside `asy_wifi_service.py`'s own ~5s/10-poll budget) instead
of resolving instantly. `ifconfig()` was meant to report the host's own real outbound address
(discovered via the standard no-packets-sent UDP-connect-then-getsockname trick) but this
MicroPython build's `socket.socket` has no `getsockname()` at all (confirmed directly against the
built interpreter) - reverted to a plausible static address instead, since nothing in `src/` ever
constructs a socket from its own `ifconfig()` result anyway (only logs/serves it for diagnostics).

**Done (this session)**: all of Step 3's criteria met. `digital_twin/` (own top-level directory,
per the owner's own naming choice) contains `machine.py` (`Pin`/`I2C`/`SPI`/`Timer`/`WDT`/`RTC`,
`Timer` firing for real via an internal `asyncio` task rather than `_thread`), `_sgp40_chip.py`/
`_scd30_chip.py`/`_bmp3xx_chip.py` (one datasheet-verified chip fake per sensor, wired onto the
real wozi bus layout - `I2C(0,...)`→SCD30@0x61, `I2C(1,...)`→SGP40@0x59+BMP3xx@0x77), `_fram_chip.py`
(MB85RS64V SPI protocol plus explicit `save_state()`/on-construction-load JSON persistence),
`_crc8.py`/`_fault_injection.py` (small shared helpers), `network.py`/`neopixel.py` (independent
duplicates of `tests/network.py`/`tests/neopixel.py`, per the owner's explicit choice), and its own
`README.md` documenting the `MICROPYPATH="src:digital_twin:.frozen"` swap-in for Step 5. 77 unit
tests across `tests/test_digital_twin_{machine,sgp40,scd30,bmp3xx,fram,network_neopixel}.py`, all
green under the real MicroPython Unix-port interpreter (v1.28.0, built fresh this session), all
deterministic except one short-period/generous-timeout smoke test proving the real-time Timer
scheduling mechanism itself works. `ruff check digital_twin/ tests/test_digital_twin_*.py` clean;
`mypy src tests` (the existing committed scope, which already sweeps up the new test files since
they live in `tests/`) has zero findings beyond a known, documented gap - `digital_twin/` itself
isn't yet on `mypy_path`, so imports from it can't resolve under the *existing* config (see
`digital_twin/README.md`'s "Known gaps" section for the full explanation and what extending scope
would need). Confirmed the full pre-existing test suite (every `tests/test_*.py` file this session
didn't add) still passes/fails exactly as it did before this session started - `tests/machine.py`
and every other pre-existing file untouched.

**Pre-existing, unrelated failures found while re-running the full suite (not fixed - out of this
step's scope, flagged per CLAUDE.md's discrepancy convention)**: `tests/test_sensortask_wozi.py`'s
`test_webserver_system_put_debug_level_propagates_to_every_logger` and
`tests/test_system_service.py`'s `test_set_debug_level_persists_and_calls_every_registered_setter`/
`test_one_bad_setter_does_not_stop_the_rest_of_the_registry` fail consistently (reproduced 3x, not
flaky) on a clean checkout of this branch, with no changes from this session touching either file
or anything they import - confirmed via `git status`/`git diff --stat` showing only
`FINAL_WIRING_PLAN.md` and new `digital_twin/`/`tests/test_digital_twin_*.py` files. All three
failures cluster around debug-level/logger-registry propagation, suggesting one shared root cause
rather than three independent bugs - worth a dedicated look in a future session, not diagnosed
further here since it's unrelated to Step 3's own scope.

**Round 2 — the owner flagged that this step skipped the mandatory per-step "come back between
borders" workflow (questions → refresh the action list → TDD → maximize coverage, stopping to
report after each), even though the work itself landed correctly. Resuming properly from the
"questions" border, using everything already learned above.**

**Additional clarifying questions asked (10, top-level decision/options/consequences style) and the
owner's answers**:

1. **Sensor value evolution: switch from independent per-read random draws (round 1's decision #9)
   to a bounded random walk.** *Chosen.* Each new reading steps by a small bounded delta from the
   previous one instead of redrawing uniformly across the whole configured range — supersedes round
   1's decision #9 outright (the owner's original literal framing is overridden by this explicit
   follow-up choice).
2. **WDT: real crash-on-timeout enforcement vs. staying inert.** *Chosen: inert tracking, but with a
   notification that a real watchdog would have fired.* Neither of the two offered options exactly —
   own answer: keep feed()-only, non-terminating semantics (no process crash/exit), but add an
   observable signal (event log / counter / optional callback) the instant an elapsed-without-feed
   window would have tripped a real hardware reset, so a Step 5 run can detect and report "the
   watchdog would have saved us here" without actually taking down the interpreter.
3. **`machine.reset()`/`bootloader()` semantics.** *Chosen: raise a catchable, distinguishable
   exception* rather than staying inert or actually terminating the process — leaves a future Step 5
   harness free to catch it and simulate a soft reboot, without forcing that harness's design now.
4. **WiFi connect-failure realism.** *Chosen: add scriptable failure phases* (`STAT_NO_AP_FOUND`/
   `STAT_WRONG_PASSWORD`/`STAT_CONNECT_FAIL`) as a first-class, opt-in outcome `connect()` can
   resolve to after the same phased delay used for success — not just raw exception injection.
5. **I2C/SPI bus transaction timing.** *Chosen: keep instant* (current behavior) — no simulated
   per-transaction latency added.
6. **Time acceleration for long-duration runs.** *Chosen: wall-clock only* (current behavior) — no
   configurable time-scale factor.
7. **Cross-sensor (BMP3xx/SCD30 temperature) correlation.** *Chosen: keep independent per-chip*
   randomization (current behavior) — no shared-environment coupling.
8. **`pyproject.toml` ruff/mypy scope extension to cover `digital_twin/`.** *Chosen: extend scope
   now* (overrides round 1's "defer" default) — accepting the full clean-Ubuntu-24.04-chroot
   pre-push verification this requires per CLAUDE.md before anything gets pushed.
9. **Fault-injection granularity** (Nth-call targeting / queued multi-exception sequences).
   *Chosen: keep single-arm* (current `inject_fault(op, exc, times=1)` semantics) — no change.
10. **The two pre-existing, unrelated test failures** found during round 1's full-suite re-run
    (`test_sensortask_wozi.py`/`test_system_service.py`, debug-level/logger-registry propagation).
    *Chosen: fix now, as an aside* — overrides round 1's "leave flagged" default.

**Refreshed action list (post-Q&A, before any code/tests change) — this is the "border" being
reported back on before starting the TDD step**:

- **A. Sensor value evolution → bounded random walk** (`_sgp40_chip.py`/`_scd30_chip.py`/
  `_bmp3xx_chip.py`). Each chip fake keeps its existing `min_*`/`max_*` datasheet-sourced range
  arguments unchanged (those stay datasheet-backed), but adds a small **not** datasheet-derived
  (physical-plausibility judgment call, called out as such in the docstring — datasheets bound
  sensor capability, not real-world minute-to-minute environmental change rate) `*_step` bound per
  tracked value: SCD30's CO2/temperature/humidity (three independently-walking values, one
  `Scd30Chip._produce_new_reading()` call per step — its existing periodic-Timer/manual-test-hook
  call site is unchanged, only what happens inside changes from "fresh draw" to "step from last"),
  BMP3xx's temperature/pressure (walked once per forced-mode conversion trigger — i.e. inside
  whatever handler currently reacts to the real `CONTROL`-register `0x13` forced-mode write, *not*
  on a timer, since BMP3xx has none), SGP40's raw VOC ticks (walked once per `measure_raw`-shaped
  command, matching its existing per-command read cycle). Initial value: a uniform draw within
  `[min,max]` at construction (unchanged), only subsequent values switch to stepping. Clamp every
  step to `[min,max]` (a walk must not escape the configured/datasheet-informed band). Existing
  `corrupt_next_*` fault-injection flags stay orthogonal — they corrupt whatever the walk just
  produced, not the walk mechanism itself. The existing `random_source`/seed injection seam is
  reused unchanged for the walk's per-step delta draws (same reproducibility guarantee round 1
  already built).
- **B. WDT → inert tracking + "would have triggered" notification** (`machine.py`). Before
  implementing: verify (against real `ports/rp2/machine_wdt.c` source or current upstream docs, not
  assumption — CLAUDE.md's standing "check real MicroPython behavior" rule) exactly what real
  `WDT(timeout=N)` does for `N` above the confirmed 8388ms RP2040 hard cap (SPECIFICATION.md
  F.1) — raises, clamps, or silently accepts — and match that exact behavior in the twin rather than
  guessing. Add an internal `asyncio`-task-scheduled monitor (mirroring `Timer`'s own established
  mechanism in this same file) that tracks time since the last `feed()`; when a `feed()`-free window
  would exceed `timeout`, record the event (`would_have_triggered_count` increments,
  `would_have_triggered_log` gets an entry, an optional constructor-supplied `on_would_trigger(wdt)`
  callback fires if provided) without terminating anything, then keeps monitoring so a long-unfed
  stretch can notify more than once. No new public "disable" API — real hardware genuinely can't
  disable an armed WDT, and each twin `WDT`'s background task dies naturally when its owning
  `asyncio.run()` event loop closes at the end of a test, matching `Timer`'s existing cleanup story.
- **C. `reset()`/`bootloader()` → catchable, distinguishable exceptions** (`machine.py`). Add a
  `SimulatedReboot(Exception)` base with two subclasses, `SimulatedReset`/`SimulatedBootloaderEntry`,
  exported from the module. `reset()`/`bootloader()` keep incrementing their existing module-level
  counters (useful even though the call never returns — a future Step 5 harness catching the
  exception can still inspect "how many times did this happen") and then raise the matching
  exception. No other file in this session's scope calls either function today, so this is a
  behavior-only change with nothing else to update.
- **D. WiFi → scriptable connect-failure phases** (`network.py`). Add `WLAN.script_connect_outcomes(
  outcomes: list[int])`, a FIFO consumed one entry per *completed* (not cancelled) `_run_connect()`
  resolution; empty/exhausted queue defaults to today's always-succeeds behavior, preserving every
  existing test unchanged. On a scripted failure outcome, `_status` is set to that value,
  `_connected` stays `False`, and `_ifconfig` stays/reverts to the unconfigured
  `("0.0.0.0", ...)` tuple (mirroring never-connected state) — matching real driver expectations that
  a failure status means no address was ever obtained. A `disconnect()` that cancels a pending
  `_run_connect()` task must **not** consume a queued outcome (the attempt never completed, so
  nothing was "used"). Re-verify against `src/asy_wifi_service.py`'s own polling loop (already read
  this session) that this status-persistence shape is actually what its retry/backoff logic expects,
  since the entire point of this feature is exercising that logic realistically.
- **E. Extend `pyproject.toml`'s ruff/mypy scope to `digital_twin/`** — the heaviest item this
  round, several concrete sub-steps, all needed before anything gets pushed:
  1. Add `digital_twin` to `[tool.mypy]`'s `files` list.
  2. Determine (empirically, by actually running mypy, not by assuming symmetry with `tests/`)
     whether `digital_twin/machine.py`/`network.py`/`neopixel.py` need the same
     `tests/network\.py$`-style `exclude` treatment to stop them winning module resolution
     project-wide over the real `typings/` stubs — note that `tests/machine.py` and
     `tests/neopixel.py` are conspicuously *not* excluded today despite superficially the same
     bare-top-level-module-name shape as the already-excluded `tests/network.py`, so this needs
     actually checking, not copy-pasting the existing exclude list's shape onto three new paths.
     Do **not** add `digital_twin` to `mypy_path` — doing so would risk reintroducing the exact
     project-wide resolution hijack the existing `tests/network.py` exclude comment documents,
     this time from `digital_twin/`'s own copies.
  3. Add `digital_twin` to `scripts/lint.sh`'s hardcoded `ruff check improved-quality src tests`
     line (it does not pick up new top-level directories automatically).
  4. Decide, and if yes update, whether `.github/workflows/ci.yml`'s `lint-and-typecheck` job
     (which explicitly gates on `ruff check src tests` / `scripts/typecheck.sh src tests`, bypassing
     `pyproject.toml`'s own `files` default specifically to keep `improved-quality/`'s pre-existing
     findings from failing CI) should add `digital_twin` to that same explicit gate now that it's a
     real quality-checked scope — leaning yes, since the owner's choice was "extend scope now," but
     flagging explicitly since `ci.yml` wasn't itself one of the files named in CLAUDE.md's
     pre-push-verification trigger list, only implied by "anything else touching the
     dev-tooling/build-environment setup."
  5. Run `scripts/lint.sh`/`scripts/typecheck.sh` locally and reconcile against whatever
     `digital_twin/`'s existing ad hoc `ruff check digital_twin/ ...`/manual `mypy` runs already
     found this session (documented in the "Done" note above) — confirm no new config-crash errors,
     document the finding count the same way round 1 did.
  6. **Run the full clean-Ubuntu-24.04-chroot pre-push verification recipe from CLAUDE.md's
     "Pre-push verification" section end-to-end** before pushing anything from this round — this
     touches `pyproject.toml` (and likely `scripts/lint.sh`/`ci.yml`), which is exactly what that
     recipe exists to gate.
- **F. Fix the two pre-existing, unrelated test failures** (`tests/test_sensortask_wozi.py`'s
  `test_webserver_system_put_debug_level_propagates_to_every_logger`,
  `tests/test_system_service.py`'s `test_set_debug_level_persists_and_calls_every_registered_setter`/
  `test_one_bad_setter_does_not_stop_the_rest_of_the_registry`) — not yet root-caused, only observed
  failing. Concrete steps: reproduce each in isolation, read the failing assertions and trace the
  actual propagation path through `src/system_service.py`'s debug-level/logger-registry code (all
  three cluster around one area, plausibly one shared root cause per round 1's own note), apply the
  minimal correct fix, add/adjust unit tests covering the actual bug (not just re-asserting the
  existing expectation), then re-run the full suite to confirm both the fix and no new regressions.
  This is real `src/` behavior work, permitted freely under CLAUDE.md's "`src/` is freely editable"
  rule — the only reason it wasn't done in round 1 was scope discipline, now explicitly lifted by
  the owner for this specific pair of failures.
- **No further action needed** for items 5–7, 9 above (bus timing, time acceleration, cross-sensor
  correlation, fault-injection granularity) — all confirmed to stay exactly as round 1 already built
  them.

**A gap the owner flagged directly (not from the 10-question round): there was no way to actually
*start* the twin.** Everything built so far is importable Python modules — real value for Step 5's
eventual integration, but nothing runnable on its own, and no way to pick simulation options (e.g.
"with or without bus error simulation") without hand-editing a script. Two follow-up clarifying
questions resolved the design (own decision/options/consequences round, not counted against the
original 10 since it's a new topic the owner raised mid-session):

1. **What a "bus error simulation" toggle should actually mean.** *Chosen: just expose the existing
   scripted fault-injection API via the CLI* — not a new ambient/probabilistic "randomly flaky bus"
   mode. No new twin-side mechanism; the CLI only arms the same `inject_fault()`/`raise_on` calls a
   test already can, from the command line instead of from Python.
2. **How much of the system the launcher should bring up.** *Chosen: twin-only standalone demo* —
   confirms the launcher stays inside Step 3's own boundary (no `src/` import at all), matching
   every other "whatever entry point Step 5 writes" deferral already in this plan; Step 5's own
   entry point reuses the same configuration functions, it just also imports
   `src/sensortask_wozi.py` afterward, which this launcher deliberately does not.

- **G. `digital_twin/launch.py` — a standalone CLI launcher/demo for the twin itself.** Runnable
  directly (`micropython digital_twin/launch.py [options]`); brings up the same bus/peripheral
  wiring `src/sensortask_wozi.py`'s real `build_system()` uses (same pin numbers/frequencies, so the
  demo is faithful to the real construction — confirmed directly against that file's own
  `WDT(timeout=8000)`/`I2C(0, 13, 12, frequency=50000)`/`I2C(1, 19, 18, frequency=50000)`/
  `SPI(0, 2, 3, 4)` lines), applies CLI-selected configuration, then runs a small built-in `asyncio`
  loop that periodically performs one real bus-level read per sensor (going through actual
  `readfrom_into`/`readfrom_mem`/`writeto_mem` calls shaped like the real drivers', not just
  inspecting each chip fake's internal state — so the demo genuinely exercises the same path Step 5
  will) and prints the decoded result, attempts one `WLAN.connect()` and prints its phase
  transitions, and feeds the `WDT` on its own short timer (unless suppressed). Flags:
  - `--seed INT` — seeds one shared `random.Random(seed)` used for every sensor value walk (omit for
    real unseeded randomness); reuses the existing per-chip `random_source` injection seam unchanged.
  - `--fram-state-path PATH` — wraps `machine.configure_fram_state_path()`; omitted means today's
    default (in-memory only, no persistence).
  - `--fault DEVICE:OP[:TIMES]` (repeatable) — arms one scripted fault via the target device's
    existing `FaultInjector`/`raise_on`, e.g. `--fault scd30:readfrom_into:2`. `DEVICE` ∈
    `{sgp40, scd30, bmp3xx, fram, wlan}`; `OP` must be one of that device's already-recognized
    op-strings (documented in `--help` and cross-referenced against each `tests/test_digital_twin_*`
    file's own usage); `TIMES` defaults to `1`. Always raises a plausible `OSError(errno.EIO, ...)`
    for I2C/SPI devices, matching this codebase's own real-fault convention — no generic
    exception-type mini-language, since bus faults are essentially always `OSError`-shaped here.
  - `--wifi-outcome {success,no_ap,wrong_password,connect_fail}` (repeatable, in call order) —
    pre-scripts `WLAN.script_connect_outcomes()` (item D above) before the demo's own `connect()`.
  - `--no-wdt-feed` — deliberately never feeds the `WDT`, to manually exercise/observe item B's
    would-have-triggered notification.
  - `--duration SECONDS` — exit cleanly after this many seconds instead of running until
    `Ctrl-C`/`KeyboardInterrupt`; needed for both scripted smoke-testing of the launcher itself and
    convenient manual use.
  - Startup banner prints the resolved configuration; a `try`/`finally` around the loop calls
    `machine.flush_fram()` on the way out and prints a short summary (readings observed, WiFi
    outcome reached, WDT-notification count) — mirrors the documented Step-5 entry-point pattern
    from `digital_twin/README.md`, exercised directly here instead of only described.
  - Argument parsing and fault-spec parsing are each factored into small, pure, directly-testable
    functions (`parse_args(argv) -> LaunchConfig`, a fault-spec parser) with only a thin
    `if __name__ == "__main__":` glue calling into them — the loop itself is driven by a `main()`
    coroutine so tests can `asyncio.wait_for(main(config), timeout)` it directly, same shape as
    `tests/test_digital_twin_machine.py`'s own Timer smoke test. Before committing to hand-rolling
    the parser: check whether `argparse` is actually available/reliable on the pinned Unix-port
    build; fall back to a small hand-rolled flag loop (consistent with this package's existing
    preference for not depending on modules that may not be frozen into the test binary,
    `tests/microtest.py`'s own hand-rolled runner being the precedent) if not.
  - New test file: `tests/test_digital_twin_launch.py` — deterministic tests of `parse_args()`/the
    fault-spec parser (valid flags, malformed `--fault`/`--wifi-outcome` values raise a clear error),
    plus one short-`--duration`/fixed-`--seed` end-to-end smoke test of `main()` itself (generous
    `asyncio.wait_for` bound, same "does the mechanism work at all" spirit as the existing Timer/WLAN
    live-timing tests, not a precise-behavior assertion).

**Sufficiency check — is this whole action list (round 1 + round 2 A–G) actually enough for the twin
to operate?** Checked directly against `src/`'s real import surface rather than re-asserting round
1's own claims:

- **Confirmed complete `machine` coverage.** Grepped every `from machine import ...` across all of
  `src/`: `Pin`, `Timer`, `SPI`, `I2C`, `WDT`, `RTC`, `bootloader`, `reset` — plus `UART`
  (`asy_uart_driver.py`). Checked `sensortask_wozi.py`'s own `build_system()` construction lines
  directly: it builds `WDT`, two `I2C`s, and one `SPI` — never a `UART`. So `UART` is confirmed, not
  assumed, unneeded for this step/Step 5's stated wozi-variant scope; every symbol the wozi build
  path actually touches is already in `digital_twin/machine.py`. No gap.
- **Confirmed complete `network`/`neopixel` coverage.** Grepped for `import network`/`import
  neopixel` project-wide in `src/` — only `asy_wifi_service.py` and `asy_neopixel_driver.py`
  respectively, both already covered.
- **Checked a real candidate gap and ruled it out: does anything construct `network.WLAN(if_id)`
  more than once expecting the same object back**, the way `digital_twin/machine.py`'s `Pin` already
  has to support for SCD30's shared IRQ pin (real hardware's `WLAN(if_id)` is a singleton per
  interface, but `digital_twin/network.py`'s `WLAN.__init__` has no registry — a fresh instance every
  call)? Grepped every `WLAN(`/`STA_IF`/`AP_IF` use in `src/`: exactly two construction sites, both
  in `asy_wifi_service.py`'s `_select_wifi_mode()`, both immediately assigned to the same
  `self.wlan` — used for switching between STA and AP (hotspot) mode, where getting a fresh handle
  on a mode switch is the semantically correct behavior, not a bug the twin needs to reproduce.
  Confirmed not a gap.
- **New forward note for whoever builds Step 5 (not actionable now, flagged so it isn't a surprise
  later)**: item C makes `machine.reset()`/`bootloader()` raise instead of staying inert.
  `system_service.py` imports both (as `system_reset`/`system_bootloader`) from a real, reachable
  code path (SPECIFICATION.md's own WDT/reboot-timer notes). Once Step 5 actually wires the twin
  under the real prototype, that path's `SimulatedReboot` must be caught somewhere in Step 5's own
  entry point/harness, or the first real "reboot" action (a REST route, the reboot-timer sequencer)
  will crash the whole Step 5 process instead of just being observed — arguably the *correct*
  behavior (loudly surfacing "a reboot happened" rather than silently no-opping), but it must be a
  deliberate, documented expectation Step 5's session designs around, not an unpleasant surprise.
- **The one real operational gap found — no runnable entry point at all — is exactly what item G
  above now closes.** Everything else checked (FRAM chunk-allocation determinism, SPI chip-select
  handling via `SPIDevice`'s own bit-banged `Pin`, `RTC`'s class-level singleton state, `Timer`'s
  general-purpose sufficiency for `system_service.py`'s sequencer) traces back to already-built,
  already-tested twin behavior — no further gaps found there.
- **Verdict**: round 1 + round 2's A–G is sufficient for the twin *itself* to operate as a
  standalone, configurable simulator — which is this step's actual, stated goal. It is deliberately
  **not**, and was never meant to be, sufficient for a full end-to-end Step 5 run of the real
  assembled prototype against the twin — that remains correctly out of this step's scope, with the
  one concrete new dependency above (catching `SimulatedReboot`) now on record for that future
  session to account for.

**TDD step (A–D, F, G) — done.** Owner go-ahead received; tests written first (red) then implemented
against (green) for every item below, each verified passing (repeatedly, to catch timing flakiness)
before moving to the next. Item E (pyproject.toml/ruff/mypy scope + the chroot pre-push recipe) is
still untouched, deliberately deferred per the border above.

- **A — bounded random walk, implemented.** `_scd30_chip.py`/`_bmp3xx_chip.py`/`_sgp40_chip.py` each
  gained a `*_step` constructor parameter (`co2_step=50.0`/`temp_step=1.0`/`hum_step=3.0` for SCD30;
  `temp_step_c=1.0`/`pressure_step_hpa=5.0` for BMP3xx; `raw_step=1000` for SGP40 — all non-datasheet
  judgment calls, documented as such in each file) and now draw the initial value at construction,
  stepping-and-clamping on every subsequent reading instead of a fresh independent draw. Existing
  `_FixedRandom`-based tests updated mechanically (construction's 3/2/1 initial values followed by
  the step call's own delta draws — zeroed where a test's assertions are about the *value*, not the
  walk); new dedicated tests added per chip for: initial draw without a reading produced, stepping
  from the previous value, min/max clamping, and constructor-configurable step bounds. 23/17/17
  tests passing (scd30/bmp3xx/sgp40 respectively).
- **B — WDT, implemented, with a real-hardware finding.** Read `ports/rp2/machine_wdt.c` directly
  from this session's own cached MicroPython v1.28.0 checkout (`$PICO_TOOLCHAIN_DIR/micropython`)
  rather than assuming: real `WDT(timeout=N)` raises `ValueError("timeout exceeds 8388")` for N above
  the cap (not a silent clamp), and — a bonus finding beyond what was asked — `WDT(id != 0)` raises
  `ValueError("WDT(%d) doesn't exist")` too, since rp2 only ever implements id 0. Both now matched by
  the twin. Added an internal `asyncio`-task countdown (`_arm()`/`_countdown()`, cancel-and-reschedule
  on every `feed()`, mirroring `Timer`'s own established pattern) driving
  `would_have_triggered_count`/`would_have_triggered_log`/an optional `on_would_trigger` callback, no
  disable API. Timing tests poll at 5ms against a 150ms WDT period (a first attempt at 20ms/20ms
  raced and was flaky under load — fixed by widening the poll-to-period ratio, not by loosening the
  assertions). 29/29 `test_digital_twin_machine.py` tests passing.
- **C — SimulatedReboot, implemented as designed.** `SimulatedReboot(Exception)` base,
  `SimulatedReset`/`SimulatedBootloaderEntry` subclasses; `reset()`/`bootloader()` still increment
  their module counters, then raise. Covered by dedicated tests (counter increments, correct
  subclass, catchable via the base class).
- **D — WLAN scripted outcomes, implemented as designed.** `WLAN.script_connect_outcomes()` FIFO,
  consumed one per *completed* `_run_connect()`; a cancelled attempt (via `disconnect()` or a
  superseding `connect()`) naturally never consumes an entry, since cancellation interrupts the
  coroutine before the consuming line ever runs — no extra bookkeeping needed. Failure outcomes
  revert `_ifconfig` to the unconfigured tuple, not just leave `_connected` false. 8 new tests added
  (15/15 total in `test_digital_twin_network_neopixel.py`).
- **F — root-caused and fixed, wider than originally scoped (per the owner's own choice mid-round —
  see the "F fix scope" question above).** The real bug was never in `system_service.py`: every one
  of 14 test files (not just the 2 originally flagged) carries its own copy-pasted `_tmp_cfg_dir()`
  helper whose deterministic, never-cleaned-up directory numbering silently reuses an earlier
  `scripts/test.sh` run's *already-persisted* config files, misreporting a genuine value-changing
  write as `"Unchanged"` instead of `"Valid"`. Confirmed by direct reproduction (clean run: 29/29;
  dirty rerun: 23/29, identical failures every time) before touching any code. Fix: each of the 14
  files' own `_sweep_stale_tmp_dirs(prefix)`, called once at import time, removes any pre-existing
  directories matching that file's own prefix before `_tmp_cfg_dir()` hands out new ones — no
  `scripts/test.sh` change, so item E's chroot recipe isn't triggered by this. Regression tests added
  directly against the sweep helper in `test_sensortask_wozi.py` (removes a matching stale dir and
  its contents; leaves a non-matching entry alone; tolerates a missing `tests/_tmp` entirely).
  Verified clean-then-dirty-rerun idempotence for all 14 files individually, plus the full suite.
- **G — `digital_twin/launch.py`, implemented, with one design correction from the plan.** `argparse`
  *is* importable on the pinned Unix-port build (confirmed directly), but reading the vendored
  micropython-lib implementation showed it doesn't support `action="append"` (blocking the
  plan's own repeatable `--fault`/`--wifi-outcome` flags), has no `choices=`, and surfaces parse
  errors via `sys.exit(2)` rather than a catchable exception — so per the plan's own explicit
  fallback clause, `parse_args()` is a small hand-rolled flag loop instead, not an argparse wrapper.
  `--seed` also turned out simpler than planned: MicroPython's `random` module has no instantiable
  `Random` class (confirmed directly — only CPython has one), but every chip fake's own
  `random_source=None` default already falls back to the same shared module-level `random`, so
  `main()` just calls `random.seed(config.seed)` once — no `random.Random(seed)` object needed.
  (`machine.configure_random_source()` was still added, mirroring `configure_fram_state_path()`'s
  own module-level-hook shape, as a real seam for a future caller that wants a distinct
  random-source object — tested directly — just not exercised by `launch.py` itself.) One robustness
  fix beyond the original design: `_sensor_loop()` wraps each of the three sensors' own read in its
  own `try`/`except OSError` — an early version let one `--fault`-injected sensor's exception crash
  the whole loop task silently, taking the other two sensors' readings down with it; now isolated,
  matching `system_service.py`'s own per-setter try/except convention. Verified with both the unit
  test suite (22/22, including 2 short-duration/fixed-seed `main()` smoke tests) and a real manual
  CLI run (`micropython digital_twin/launch.py --seed 42 --duration 3 --no-wdt-feed --wifi-outcome
  success --fault scd30:writeto:1`) showing the fault firing exactly once, WLAN transitioning
  CONNECTING → GOT_IP, and all three sensors continuing to report afterward.

Full-suite regression run (`scripts/test.sh`, no `--coverage`) after all of the above, from a fully
clean `tests/_tmp/` (confirming F's fix holds, not just individually per-file but across the whole
suite in one real run): **2,059/2,059 tests passing across all 42 files, zero failures.**

**Item E and the coverage border — both done.**

**Item E (pyproject.toml/ruff/mypy scope extension + chroot pre-push verification) — done, with a
real design correction from the plan.** Adding `digital_twin` to `[tool.mypy]`'s `files` list alone
(step 1) collided outright: `mypy` fails with `Duplicate module named "machine"` the instant
`digital_twin/machine.py` is scanned alongside `tests/machine.py`'s own bare `machine` module -
confirmed directly, a straight collision, not the softer resolution-priority hijack
`tests/network.py`'s own exclude guards against. Step 2's empirical check found the real, deeper
issue: mypy resolves each bare `machine`/`network`/`neopixel` module name to exactly one file per
run, so `digital_twin/`'s own hardware fakes and the real `typings/` board stubs can never both be
checked correctly in one invocation - `digital_twin/launch.py` and every
`tests/test_digital_twin_*.py` exercise the twin's own richer API (`WDT.would_have_triggered_count`,
`WLAN.script_connect_outcomes()`, `Pin.reset_registry()`, ...) that the real board stub has no
reason to declare, so checking them under the main pass's `mypy_path` (unchanged: `typings` + `src`,
no `digital_twin`) only ever produces attr-defined noise, never a real finding. Concretely
confirmed, not assumed: `mypy src tests` - the exact command `.github/workflows/ci.yml`'s
`lint-and-typecheck` job already ran - was silently broken (43 errors) *before this session's own
fix*, never caught because no PR had been opened against this branch yet to actually trigger CI.
**Fix**: `digital_twin/machine.py`/`network.py`/`neopixel.py`/`launch.py` and every
`tests/test_digital_twin_*.py` are excluded from the main `[tool.mypy]` pass (see its own exclude
comment for the full account); a new, separate `digital_twin/typecheck.ini` config
(`mypy_path = digital_twin:typings`) gives the whole subsystem its own always-clean pass instead,
run unconditionally by `scripts/typecheck.sh` regardless of its own args - so CI's existing
`scripts/typecheck.sh src tests` step gates on `digital_twin/` too without `ci.yml` needing to name
it explicitly. Fixing this surfaced real, small bugs in `digital_twin/machine.py` (`Pin._initialized`
typing, `I2C.readfrom_mem`'s `no-any-return`, `RTC.datetime`'s Optional-vs-`Tuple` mismatch - the
stub's own convention won, matching `typings/machine.pyi`) and `_scd30_chip.py` (`self._timer`'s
type), all fixed directly since `digital_twin/` is freely-editable, fully-reviewed code, not WIP.
`scripts/lint.sh` and `.github/workflows/ci.yml`'s `Ruff`/`Mypy` steps now cover `digital_twin/`
explicitly (ruff has no equivalent per-run resolution conflict, so it's just named directly
alongside `src`/`tests`). **Chroot verification**: ran the full clean-Ubuntu-24.04-debootstrap
recipe from CLAUDE.md's "Pre-push verification" end to end (`uv sync` under bare Python 3.12,
`scripts/lint.sh`, `scripts/typecheck.sh`, `scripts/test.sh`) - all three matched the ordinary
session sandbox's own results exactly (30 known `improved-quality/` lint findings, 50 known mypy
findings + a clean `digital_twin/` pass, **2,059/2,059 tests passing**), confirming nothing here
depends on anything the sandbox happened to have pre-installed.

**Coverage border - done.** `scripts/test.sh --coverage`'s tracer
(`tests/_coverage_runner.py`) was hardcoded to a `src/`-only prefix, so `digital_twin/` was
completely invisible to the existing coverage tooling even though it's now a real, gated,
freely-editable scope. Generalized the tracer to `("src/", "digital_twin/")` (confirmed directly:
MicroPython's `str.startswith()` accepts a tuple, same as CPython) and had `scripts/test.sh`
render a second, separate report from the same shared trace run
(`htmlcov_digital_twin/`/`coverage_digital_twin.xml`/`coverage_summary_digital_twin.md`, wired into
`ci.yml` the same way as the existing `src/` report) rather than merging the two into one - the two
scopes have different maturity/gating expectations (CLAUDE.md's "Code quality tooling"). First real
`digital_twin/` coverage number: **94%** (992 statements, 63 missed). Used the per-line missing
report (`coverage.Coverage.report(morfs=..., show_missing=True)`) to separate genuine gaps from
tracer artifacts before writing anything: several `while True:` loop-header lines
(`_wdt_feeder`/`_wifi_watcher`/`_sensor_loop` in `launch.py`, `Timer._run`/`WDT._countdown` in
`machine.py`) consistently showed as "missed" even though their bodies were demonstrably exercised
by already-passing tests - a MicroPython/coverage.py line-attribution quirk for a bare `while True:`
immediately followed by another statement, not a real gap, left alone. Real gaps closed with new
tests: `FaultInjector.clear()` (never called anywhere); `Pin.value()`'s setter form, `toggle()`, and
a same-value `simulate_edge()` no-op; an unwired SPI bus id (`id != 0` - no device, zero-filled
`readinto()`); FRAM `readinto()` with nothing recognized pending; SCD30's
`STOP_CONTINUOUS_MEASUREMENT`/`SOFT_RESET`/`READ_FIRMWARE_VERSION` commands and its
unrecognized-command readback fallback; `NeoPixel.__getitem__` readback; `WLAN.deinit()`/
`status("rssi"|"stations")`/`config()`; and `network.country()`/`hostname()`'s setter form.
**One real robustness bug found and fixed along the way, not just a coverage gap**: writing a
`--fault wlan:...` coverage test for `launch.py`'s `main()` found that `WLAN.active()`/`connect()`
at startup and `WLAN.status()` in cleanup and in `_wifi_watcher()`'s own loop were all unguarded -
any WLAN fault crashed `main()` outright before it ever reached the WDT-feed/sensor-read loops,
confirmed by direct reproduction against the interpreter before touching any code. Fixed by
isolating each the same way `_sensor_loop()` already isolates each sensor's own read (per-call
`try`/`except OSError`, print and continue) - re-verified directly afterward that the same fault no
longer crashes `main()`. Added a longer-duration (4.5s) `main()` smoke test with
`no_wdt_feed=False` to also reach a real `watchdog.feed()` call and SCD30's own 2-second
timer-driven "ready" reading, neither reachable within the two existing shorter-duration tests -
this also caught a real timing bug in the session's own edit to the combined sgp40+bmp3xx fault
test (both one-shot faults fire on `_sensor_loop()`'s very first iteration, so a duration that
never reached a second iteration left `summary["readings"]` at 0, failing the test - caught by a
full `scripts/test.sh` run, fixed by extending the duration past `_sensor_loop()`'s own 2.0s poll
interval). Deliberately left uncovered, not chased: `_bmp3xx_chip.py`'s two Newton-solver
divide-by-zero guards (unreachable with the fixed, verified-round-tripping calibration set across
the twin's whole configured range - manufacturing a pathological target value to hit them would
test the guard, not the twin); `launch.py`'s run-forever branch (`--duration` omitted - genuinely
would hang a test, matching every other real-Ctrl-C-only code path in this codebase) and its
`if __name__ == "__main__":` glue (never reached under `import launch`, same as every
`tests/test_*.py`'s own such block). **Final `digital_twin/` coverage after all of the above: 98%**
(1,001 statements, 24 missed - the artifacts and deliberate gaps above account for essentially all
of what remains). Full-suite regression, `scripts/test.sh --coverage`, from a fully clean
`tests/_tmp/`: **2,075/2,075 tests passing across all 43 files** (`src/` coverage unchanged at 94%,
confirming no regression there), **zero failures**.

Both of the above were also confirmed clean through the full clean-Ubuntu-24.04-chroot recipe
before either was pushed (see item E's own writeup above - the chroot run predates the coverage
border's own commits, but both landed together and are covered by the same sandbox-vs-chroot
lint/typecheck parity check; the coverage border's own test-suite correctness was verified directly
in-session, twice, against the real interpreter rather than re-running the heavier chroot recipe a
second time for changes that don't touch the dev-tooling/build-environment setup CLAUDE.md's
pre-push gate is actually scoped to).

**Step 3 is now complete against the full, resumed "questions → refresh action list → TDD → maximize
coverage" workflow** - every item from round 1, round 2's A-G, and this round's E/coverage border is
done and tested. One further documentation gap was found and closed in the same close-out pass: the
main `README.md` linked to `digital_twin/README.md` but never showed how to actually start the twin
itself - fixed with a new "Digital twin (hardware simulator)" section giving the exact, directly-
verified `digital_twin/launch.py` standalone-CLI command (seed/duration/no-wdt-feed/fault/
wifi-outcome/fram-state-path flags), plus a pointer to `digital_twin/README.md`'s separate
`MICROPYPATH`-based "swap the twin into a real `src/sensortask_wozi.py` run" section so the two
aren't conflated. No further open items remain from this step's own scope.

**Merge-back correction (post-session)**: this step's session originally fast-forwarded
`claude/step2-webserver-api-service` rather than the trunk, following what turned out to be an
ambiguous reading of this doc's own "Branch / session structure" diagram at the time (since fixed,
see that section above). The Step 4 kickoff session caught this before branching Step 4 off the
stale trunk, fast-forwarded `claude/framework-wiring-rest-api-hx99v7` to Step 3's tip (clean, no
divergent commits — trunk was a strict ancestor), and confirmed CI green on the result. Step 3's
work is now on the actual trunk; `claude/step2-webserver-api-service` and
`claude/step3-digital-twin-simulator` are stale/superseded, left in place only as historical
record.

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

**Done** (this session): all of the above landed.

- **`html_stub/`** (new top-level folder, 7 flat files mirroring `html_raw/{general,wozi}`'s
  combined file set — `index.html`, `style.css`, `functions.js`, `favicon.ico`,
  `nettimeconfig.html`, `sensorconfig.html`, `systemledconfig.html`) — every file "Hello world"-
  shaped placeholder content, not the real site.
- **`scripts/build_frozen_html.sh`** — gzips a temp copy of `html_stub/`'s files, then runs
  `PYTHONPATH=ext python -m freezefs <tmp> <out> --on-import mount --target /html --overwrite
  always` (no `--compress`, per the known finding above; `ext/freezefs` has no `__init__.py` — an
  implicit namespace package, confirmed directly, so `PYTHONPATH=ext` is what makes `python -m
  freezefs` resolve it). Output defaults to `frozen_modules/frozen_html.py`. Source directory(ies)
  default to `html_stub` but are overridable via the `HTML_SRC_DIRS` env var (a space-separated
  list merged into one flat build tree before gzipping, mirroring `build-wozi.sh`'s own
  `general`+board-variant merge) — this is what lets the real website build reuse this script
  unmodified once real content replaces the stub, rather than needing a hardcoded-path edit first.
- **Real finding, not anticipated going in**: the output directory can *not* be `.frozen/` (the
  name this doc originally assumed, matching `scripts/test.sh`'s existing `MICROPYPATH="src:tests:
  .frozen"`). `.frozen/` is a hardcoded sentinel in MicroPython's own import machinery
  (`py/builtinimport.c`'s `MP_FROZEN_PATH_PREFIX ".frozen/"`) — any sys.path entry combining to a
  path starting with that literal string is routed straight to the compiled-in frozen-module table
  and the real filesystem is never consulted at all. A real `frozen_html.py` placed on disk under
  `.frozen/` is therefore silently unimportable (`ImportError: no module named 'frozen_html'` even
  though the file genuinely exists) — confirmed both empirically (reproduced, then fixed) and
  against the pinned v1.28.0 C source directly. Fixed by using a new, ordinary, non-reserved
  directory instead — `frozen_modules/` (gitignored) — added as its own `MICROPYPATH` segment
  alongside (not replacing) the real `.frozen` sentinel, which `scripts/test.sh` still needs
  unchanged for `import asyncio` etc. Recorded here as the "known findings" a future session
  touching this area should carry in, since this doc's own original text got it wrong.
- **`src/asy_webserver_service.py`** (Step 2's own module, freely editable — extended, not
  replaced): new `static_mount`/`static_index` constructor params. When `static_mount` is given,
  registers one generic `@app.get("/")` + `@app.get("/<path:filename>")` pair (Microdot's `path`
  URL segment type, confirmed to compile to `/(.+)`) — zero per-file routes, unlike the legacy
  reference file's hand-written one-route-per-file list, and generator-friendly the same way the
  registration-list API already is. **Registered last**, after every real API route — `find_route()`
  returns the first registered pattern that matches (confirmed directly against `ext/microdot.py`),
  and the wildcard's own regex also matches every fixed path (e.g. `/measurements`), so registration
  order is what keeps an exact-match API route from being shadowed by the wildcard. Serves via
  `send_file(mount + "/" + filename, compressed=True, file_extension=".gz")` (no `ext/microdot.py`
  edits); a missing file or a `".."` in the requested path both degrade to a clean 404 through the
  same shaped error handler Step 2 already registered.
- **`src/sensortask_wozi.py`**: module-level `import frozen_html` (unconditional — the project's
  standing "imports happen once, at module load, never inside a function" convention, confirmed via
  owner direction this session), mounting `/html` as a side effect of the import itself, matching
  freezefs's own on-import design and the legacy reference file's identical top-of-file shape.
  `build_system()`'s existing `WebserverService(...)` call (`WIRING_CONTRACT.md`'s construction-order
  item 14) gains `static_mount="/html"`.
- **Tests**: `tests/test_asy_webserver_service.py`'s new Section G (9 tests) exercises the generic
  route-wiring mechanism against a synthetic, hand-built `VfsFrozen` fixture
  (`ext/freezefs/ffsmount.py`'s own runtime mount driver, constructed directly — bypassing
  freezefs's archive-generation step entirely), independent of the real stub content: root/index
  serving, content-type inference, missing-file 404, directory-traversal rejection, a flat-mount
  nested-path miss, and the registration-order regression test (a real API route must never be
  shadowed by the wildcard). `tests/test_frozen_html_integration.py` (new file, 7 tests) is the
  separate real-pipeline proof this step's own criteria asked for: imports the *actual* built
  `frozen_html` module and drives real requests through a real `WebserverService`, decompressing the
  real gzip bytes (via `deflate.DeflateIO`) to confirm the placeholder content round-trips
  correctly, including the binary `favicon.ico` case (falls back to `application/octet-stream`,
  proving the pipeline isn't text-only). `ruff`/`mypy` both clean; full existing suite (`scripts/
  test.sh`, plain and `--coverage`) re-verified green, `src/asy_webserver_service.py` still at 99%
  line coverage.
- **`WIRING_CONTRACT.md`** updated in place (construction-order item 14's own note, plus a new
  "Step 4 landed" status bullet) — not left to drift, per that doc's own standing-maintenance
  instruction.

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

**Refined plan — resolved via project-owner Q&A this session** (supersedes/extends the above where
the two differ; kept as its own subsection per Steps 1-2's own precedent, so the original scoping
stays legible as the starting point). Own research done before the Q&A round: `tests/
test_sensortask_wozi.py` (784 lines, already landed by Step 1/2's sessions) already exercises
`build_system()`'s full real object graph through `app.dispatch_request()` for all six REST
endpoints against `tests/machine.py` fakes — dispatch-level, no real socket, no digital twin; that
coverage is not duplicated here. `tests/test_asy_webserver_service.py`'s Section F.8 already proves
a real `asyncio.start_server()`-backed connection works cleanly under the Unix port (loopback,
ephemeral port); its own F.9 is Step 2's actual soak methodology (`gc.collect()` → baseline → 120
cycles → `gc.collect()` → `assert after >= baseline - 4096`, `run_timed(..., timeout_s=60.0)`) —
reused here per decision 9 below. Confirmed by reading `src/asy_webserver_service.py` directly:
`WebserverService.__init__`'s real default is `host="0.0.0.0", port=80`, and `build_system()`
passes neither through — a non-root Unix-port run binding port 80 fails with `EACCES`, a genuine gap
this step has to close, not a hypothetical. Confirmed by reading `src/system_service.py` directly:
`start_and_check_tasks()`'s own loop already calls `self.watchdog.feed()` every iteration, so
`WDT.would_have_triggered_count` staying `0` under normal conditions is a real, already-wired
assertion, not something this step needs to build a feeder for. Confirmed by reading
`tests/test_digital_twin_launch.py` directly: the per-file `sys.path.insert(0, "digital_twin")`
trick (same one `tests/test_setter_microdot_integration.py` already uses for `ext/`) already runs
*with* `machine`/`network` resolving to the twin's own fakes, inside a process where `tests/
machine.py` is also nominally reachable via `scripts/test.sh`'s default `MICROPYPATH` — the
insert-at-position-0 ordering is deterministic (not the fragile "depends on ordering" case
`digital_twin/README.md`'s "never together" warning is actually about, which is specifically the
*production/twin* `MICROPYPATH="src:digital_twin:frozen_modules:.frozen"` invocation never also
carrying a `tests` segment). This means a middle integration tier can be an ordinary `tests/
test_*.py` file, discovered and run by `scripts/test.sh`'s existing default loop, with zero new
`MICROPYPATH`/entry-point plumbing — only the genuinely unbounded/interactive end-to-end tier needs
a dedicated separate invocation.

Owner decisions (this session's 10 clarifying questions, answered directly):

1. Confirmed the proposed split: a dedicated `scripts/`-housed entry point for the twin-separated
   `MICROPYPATH`, distinct from `scripts/test.sh` — the digital twin and `tests/` stay fully
   separated/independent, even though some fakes are deliberately duplicated (not shared) between
   them and must be watched to stay in sync (already `digital_twin/README.md`'s own stated policy
   for `network.py`/`neopixel.py`).
2. **Real HTTP, real sockets, real server** — every REST endpoint must be reachable over Microdot's
   actual transport, the same as the real system, not `app.dispatch_request()` bypass (which
   `tests/test_sensortask_wozi.py` already covers without a twin). No frozen HTTP client library
   exists anywhere in this repo's dependency set (checked directly) — a minimal hand-rolled HTTP/1.1
   client over `asyncio.open_connection()` is required, matching this project's established
   hand-roll-when-a-library-isn't-reliably-available convention (`digital_twin/launch.py`'s own
   `argparse` fallback is the precedent). Simplified by `_mark_connection_close()` already forcing
   `Connection: close` on every response (confirmed directly, `asy_webserver_service.py`) — the
   client never needs to support keep-alive.
3. **Settable server address by CLI, default `localhost:8080`**, reachable by a real browser on the
   Unix machine running the test — not the production `0.0.0.0:80` default. `build_system()` gains
   optional `web_host`/`web_port` keywords (mirroring its existing `cfg_path`/`debug` override
   pattern), defaulting to today's `0.0.0.0`/`80` for production parity, forwarded straight into
   `WebserverService(host=, port=)`.
4. Soak-cycle count can be shorter than Step 2's 120 — real sensor-poll cadence must **not** gate
   how long the REST-facing soak takes: the system is async, so the HTTP-facing soak loop hammers
   real request/response round trips back-to-back (bounded by real network/event-loop latency, not
   by the twin's own real-time sensor `Timer` cadence, which keeps running concurrently and
   unaffected in the background at real intervals). A rational, smaller cycle count than 120 is
   fine given each cycle is a real TCP round trip, not a fake-reader/writer call.
5. Three test tiers, explicitly: **unit** (existing `tests/test_digital_twin_*.py`, unchanged),
   **integration** (new — see decision 10), **end-to-end** (the full soak/manual-run entry point).
   Not a production system — no new CI job required for this step; keep the whole thing rational in
   scope, matching `BACKLOG.md`'s existing "no CI firmware-build stage yet" being tracked
   separately.
6. FRAM persistence for the end-to-end/manual entry point defaults to a **persistent** file inside
   `digital_twin/` (not an ephemeral per-run scratch path) — written only on explicit shutdown
   (`machine.flush_fram()`, already the twin's own explicit-write-only design, confirmed directly
   against `digital_twin/machine.py`/`_fram_chip.py`), in-memory only during the run itself. The new
   *automated* middle-integration-tier tests still use an ephemeral per-test path (matching every
   other test file's own `_tmp_cfg_dir()`-style isolation convention) — the persistent-by-default
   behavior is specific to the manual/end-to-end entry point, not the automated test tiers.
7. **Both**: an automated, unit-tested assertion (`watchdog.would_have_triggered_count == 0` after a
   bounded, zero-fault run) *and* the ability to watch escalation actually happen on a manual run —
   the end-to-end entry point keeps `--fault`/`--wifi-outcome` CLI passthrough (mirroring
   `digital_twin/launch.py`'s own flags) for deliberate manual exploration, not gating the automated
   pass/fail run.
8. No further constraints — keep it simple and lean, whatever shape actually works.
9. **Reuse Step 2's exact soak methodology** (`gc.collect()` → baseline → N cycles → `gc.collect()`
   → `assert after >= baseline - 4096`) for the end-to-end tier's memory-flat check.
10. **Build the middle integration tier too** (not just unit + end-to-end) — real gap-finding value
    for the existing unit-test suite. Lands as `tests/test_digital_twin_sensortask_integration.py`,
    using the precedented `sys.path.insert(0, "digital_twin")` trick, discovered by `scripts/
    test.sh`'s ordinary default loop (see "own research" above for why this doesn't collide with
    `tests/machine.py`) — builds `sensortask_wozi` for real against the twin's buses and drives real
    HTTP round trips against a fixed, non-privileged test port, without needing the full end-to-end
    entry point's own `MICROPYPATH`/CLI plumbing at all.

**Resulting concrete file list**:
- `src/sensortask_wozi.py` — `build_system()` gains `web_host`/`web_port` (decision 3).
- `tests/test_sensortask_wozi.py` — a new unit test for the override (`tests/machine.py`-backed, no
  twin involved).
- `tests/test_digital_twin_sensortask_integration.py` — new, the integration tier (decision 10),
  part of `scripts/test.sh`'s default run.
- `digital_twin/run_wozi_integration.py` — new, the end-to-end CLI orchestrator (decisions 2/3/6/7):
  hand-rolled arg parsing (`--host`, `--port`, `--fram-state-path`, `--fault`, `--wifi-outcome`,
  `--seed`, `--duration`, `--soak-cycles`, mirroring `digital_twin/launch.py`'s own conventions),
  a minimal hand-rolled HTTP/1.1 client, `--duration` omitted means run forever (manual/
  browser-reachable mode), `--duration` given means a bounded automated soak ending in the
  watchdog/memory assertions above.
- `tests/test_digital_twin_run_wozi_integration.py` — new, pure-logic unit tests for the
  orchestrator's own parsing/HTTP-client helpers, mirroring `tests/test_digital_twin_launch.py`'s
  shape.
- `scripts/run_unix_port_integration.sh` — new, the dedicated entry point (decision 1): builds the
  toolchain + `frozen_modules/frozen_html.py` the same way `scripts/test.sh` does, sets
  `MICROPYPATH="src:digital_twin:frozen_modules:.frozen"`, runs the orchestrator above, forwarding
  any CLI args through (defaults to a bounded automated soak run when none are given). Not part of
  `scripts/test.sh`'s own default loop.

**Status update (this session): all of the above landed.** `scripts/lint.sh`/`scripts/typecheck.sh`
both clean for every new/changed file (`src/sensortask_wozi.py`, `src/asy_webserver_service.py`,
`digital_twin/_http_client.py`, `digital_twin/run_wozi_integration.py`,
`tests/test_digital_twin_sensortask_integration.py`,
`tests/test_digital_twin_run_wozi_integration.py`, plus the existing `tests/test_sensortask_wozi.py`/
`tests/test_asy_webserver_service.py` extended with new regression coverage) — `improved-quality/`'s
own pre-existing, tracked findings are the only remaining `scripts/typecheck.sh`/`scripts/lint.sh`
non-zero exit, unchanged by this session. Full `scripts/test.sh` (plain and `--coverage`) re-verified
green, including the two new test files. `digital_twin/typecheck.ini` gained `src` on its own
`mypy_path` (alongside the matching `pyproject.toml` exclude-list addition for
`digital_twin/run_wozi_integration.py`) — the one file needing both the twin's own `machine`/
`network` API and a real `src/` import (`sensortask_wozi`) in the same module, a case neither
existing mypy pass was built for; see `digital_twin/typecheck.ini`'s and `pyproject.toml`'s own
updated comments for the full reasoning.

**A real, previously-undetected production bug was found and fixed along the way**, exactly the
kind of thing owner decision 10 anticipated: `src/asy_webserver_service.py`'s `_get_settings_flat()`
(backing `/networking`/`/system`/`/notification`'s GET handlers) never flattened
`config_manager.make_dict()`'s real `{type_name: {field: value}}` shape — the actual return shape
of `AsyConnTime`/`AsyNtpClient`/`NotificationCoordinator`'s own `get_dict_cfg()` — so in production
`/networking` and `/notification` always returned `{}` and `/system` silently dropped its
`ntp`-sourced `GMTOffset`/`DSTOffset` fields, keeping only `DebugLevel` (sourced from `SystemService`'s
own already-flat `get_dict_cfg()` override). `tests/test_asy_webserver_service.py`'s own uniform
`_FakeModule` fake happened to return an already-flat shape for every module, masking this
completely — only visible once `tests/test_digital_twin_sensortask_integration.py` drove a GET
against the *real* driver objects. Fixed via a new `_flatten_cfg_values()` helper in
`src/asy_webserver_service.py`; regression coverage added in both
`tests/test_asy_webserver_service.py` (a `_NestedCfgModule` fake reproducing the real shape) and
`tests/test_digital_twin_sensortask_integration.py` (asserting the real fields round-trip over real
HTTP against the real drivers).

**Two real MicroPython-Unix-port-specific findings, both now documented in the affected files' own
comments, not just here:**
- `globals()` does not preserve test-function definition order on this interpreter (confirmed
  directly — a file's own `test_*` functions ran in a different order than written). Every test
  file in this session's new work was written to never assume "the last test in the file" is "the
  last test to run" — each test that starts a real background task keeps an explicit reference to
  it and cancels it again in its own `finally`, never relying on file position for cleanup ordering.
- Calling `asyncio.run()` from inside a coroutine that is already running inside another
  `asyncio.run()` call segfaults the real interpreter outright, rather than raising a clean error
  the way CPython's own reentrancy guard would — found the hard way (a real interpreter crash, not
  a Python-level exception) while writing this session's own tests; fixed by `await`ing directly
  instead once already inside an async context.

### Baseline-verification session (post-Step-5, this session)

Owner-directed follow-up: actually build and run the real assembled system against the digital
twin end-to-end for the first time via `scripts/run_unix_port_integration.sh` itself (not just
through the automated test tiers), walk every REST endpoint through a real browser, set/verify log
level persistence across a real reboot, and repeat with bus fault injection — with an explicit
owner constraint that `src/` must never be edited *only* to make the twin run, though genuinely
general-scope bugs (real production bugs, not twin accommodations) are fair game. This actually
running the full system for real (rather than the bounded, single-task-starter tests the automated
tiers use) surfaced five more real, previously-undetected bugs:

1. **`scripts/run_unix_port_integration.sh`'s own `MICROPYPATH` was missing `ext`** — the very
   first real standalone run failed at `from microdot import Microdot` immediately.
   `scripts/test.sh`'s own `MICROPYPATH` has the identical gap, invisible there only because every
   `tests/test_*.py` file that needs `microdot` does its own `sys.path.insert(0, "ext")` — this
   real entry point had no such per-file workaround. Fixed in the script itself (and
   `digital_twin/README.md`'s matching documentation) — `"src:digital_twin:ext:frozen_modules:.frozen"`.
2. **`digital_twin/_fram_chip.py`'s `save_state()` needed one large contiguous allocation** for the
   whole FRAM image's hex string (16385 bytes for the real 0x2000-byte FRAM) - reproduced as a
   deterministic `MemoryError` after a few seconds of the real task supervisor running (real
   asyncio task/timer/HTTP churn fragments the heap enough), even with ~1.5MB of *total*
   `gc.mem_free()` still free. Fixed by streaming the write in small chunks instead
   (`_SAVE_CHUNK_SIZE`) — never needs more than one small chunk contiguous at a time.
3. **`digital_twin/machine.py`'s `I2C.log`/`SPI.log` were unbounded lists** — an ad-hoc
   introspection aid nothing actually reads, but a real, continuously-running system fires enough
   bus transactions that the list's own internal growth eventually needed a large-enough
   contiguous reallocation to fail with a real `MemoryError` too (this was the dominant contributor
   to the observed heap fragmentation — fixing it alone took a 20-cycle soak's memory-flat failure
   from a ~32KB drop down to single-digit KB). Bounded to a `deque(maxlen=200)` instead, same
   convention `print_log.py`'s own `PrintLogHistory` already uses.
4. **`digital_twin/_bmp3xx_chip.py` had no `handle_writeto()`** — `asy_i2c_driver.py`'s
   `I2CDevice.setup()`/`_probe_for_device()` always writes zero bytes to every I2C device at
   construction as a bus-presence probe, regardless of that device's real protocol family; this
   chip fake only had `handle_writeto_mem()` (its real register-addressed protocol), so every real
   boot's BMP3XX reader task hit `AttributeError`, repeatedly failed and restarted, and reliably
   pushed the task-failure counter over `system_service.py`'s own auto-reboot threshold within
   ~10-15 seconds of every real run. Fixed by adding a minimal `handle_writeto()` accepting the
   empty-probe shape (nothing else in this codebase's own BMP3xx driver ever sends a plain,
   non-mem `writeto()`).
5. **`src/asy_scd30_driver.py`'s `SCD30_Reader` never had a `get_cfg_schema()` method** — unlike
   every other reader (`SensorReaderConfig` subclasses inherit it), SCD30 is a plain `SensorReader`
   (params live on the sensor itself, no local `cfgmgr`) and never defined one locally either, even
   though `asy_webserver_service.py`'s `_put_sensors()` route calls `module.get_cfg_schema()`
   uniformly for every registered sensor — a real production bug (crashes identically on real
   hardware), not twin-specific: every real `PUT /sensors` touching SCD30 crashed with a 500.
   Never caught before because `tests/test_asy_webserver_service.py`'s own `_put_sensors` tests use
   a fake module that already has `get_cfg_schema()` defined - same "fake happens to paper over the
   real shape" pattern as the `_flatten_cfg_values()` bug above. Fixed by adding the method,
   returning the same schema `get_dict_cfg()` already uses.
6. **`src/asy_wifi_service.py`'s `dns_server` (a separate `captive_dns.DNSServer` instance) never
   had its own `pr.setup()` called** — every one of its `err_s()`/`wrn_s()` calls degraded forever
   to "PrintLog: Uninitialized, call setup first!" instead of actually logging, real hardware
   falling back to hotspot/AP mode has the identical gap. Fixed by calling
   `await self.dns_server.pr.setup()` alongside `wlan_connect()`'s own existing `self.pr.setup()`.

Also tuned (not a bug fix): `digital_twin/run_wozi_integration.py`'s `_soak()` warm-up was 2 cycles
(Step 2's own F.9 convention, copied verbatim) — far too few for *this* soak, where every settings
GET re-reads and re-parses its real config file from disk. A 100-cycle diagnostic showed
`gc.mem_free()` drop ~52KB over the first 30 cycles then settle into a noisy ±15KB band — a real,
bounded, converging warm-up transient, not a leak. Bumped to 40 cycles, which helps substantially
(a real run's memory-flat failure margin went from ~32KB down to single-digit KB) but doesn't
reliably clear `_MEM_FLAT_TOLERANCE_BYTES`'s tight 4096-byte budget every time — see `_soak()`'s own
comment. **Open question for the project owner, deliberately not resolved unilaterally**: is 4096
bytes tight enough for this *real* object graph's natural noise, given the value was copied
verbatim from Step 2's synthetic fake-based test?

**Also flagged, not fixed (a scope/fidelity decision, not an obvious bug)**: SCD30's own PUT
settings (`MeasInt`, `TempOffs`, etc.) don't survive a twin process restart, unlike every other
settings group. On real hardware this is fine — the physical SCD30 chip has its own onboard NVM
that survives an MCU-only reboot — but the twin's `Scd30Chip` fake has no persistence mechanism the
way `_fram_chip.py`'s `FramChip` does (its own `state_path`/`save_state()`). Building that would be
a real feature addition (mirroring `FramChip`'s own pattern plus tests), not a bug fix — left for
the project owner to decide whether twin fidelity needs to go that far.

After every fix: full `scripts/lint.sh`/`scripts/typecheck.sh` clean (only `improved-quality/`'s
pre-existing, tracked debt remains), full `scripts/test.sh` green (2128 tests), and a real, fresh
end-to-end run — build via `scripts/run_unix_port_integration.sh`, walk every GET/PUT endpoint
through a real browser (Playwright against the pre-installed Chromium), set `DebugLevel` to `all`
via the real API, restart the process (the twin's own `machine.reset()` only raises
`SimulatedReset` rather than actually restarting - config/FRAM persist to disk regardless, so a
real Ctrl-C/SIGINT stop-and-relaunch is the correct way to exercise "reboot" against this twin) and
confirm the persisted level produces a full verbose startup log, then repeat the whole walkthrough
with `--fault` flags active on every bus (SCD30/SGP40/BMP3XX/FRAM) - confirmed proper recovery
after each fault's bounded `times` count is exhausted. NTP sync against a real server
(`pool.ntp.org`) could not be verified end-to-end in this sandbox specifically - confirmed directly
that this session's outbound network policy allows DNS (UDP/53) but blocks NTP (UDP/123) to four
different public servers; the DNS-resolution and timeout/error-handling paths were still verified
to degrade gracefully (`NtpSynced: false`, no exception) rather than crash.

**Step 5 re-audit session (owner-directed follow-up, after Step 6 scope was separated out and the
large final audit was confirmed to live on the trunk branch instead)**: re-walked this whole step
for anything still open outside Step 6/the trunk-branch audit's scope. Found and fixed one real doc
bug (`digital_twin/README.md`'s new SCD30-persistence section wrongly claimed
`digital_twin/launch.py` defaults to a persistent state file the same way
`run_wozi_integration.py` does - `LaunchConfig`'s own default is `None`/in-memory-only for both
FRAM and SCD30, unchanged from before this step; only `run_wozi_integration.py` defaults to a
persistent path, per decision 6's own scoping). Full `scripts/test.sh`, `scripts/lint.sh`,
`scripts/typecheck.sh` re-verified clean (only `improved-quality/`'s pre-existing tracked debt).

Also closed the remaining open item from the paragraph above: **the NTP gap is structurally deeper
than "this sandbox's network policy blocks UDP/123."** A real, standalone reproduction - a real
local UDP NTP responder on `127.0.0.1:123`, and a fully WiFi-connected, correctly-configured live
digital-twin run with `NTP_Host` pointed at it (bypassing this sandbox's own network policy
entirely by never leaving loopback) - still failed every sync attempt, zero packets ever reaching
the responder. Root cause, isolated down to a bare `socket.socket().connect(("127.0.0.1", 123))`
call: the MicroPython Unix port's "standard" build's `connect()`/`bind()`/`sendto()` reject a plain
`(host, port)` tuple with `TypeError: object with buffer protocol required` - a known Unix-port-only
quirk (`micropython/micropython#6924`) `tests/test_asy_udp_socket.py` already discovered and works
around in its own test helpers, but the real production call sites
(`asy_ntp_client.py`/`asy_dns_client.py`/`captive_dns.py`) never pre-resolve via
`socket.getaddrinfo()` the way those test helpers do - correctly so, since a plain tuple is exactly
what real rp2 hardware's socket implementation requires (`typings/socket.pyi`'s `_Address`
contract). `AsyUDPSocket._connect()`'s own broad `except (OSError, MemoryError, TypeError)` swallows
this as an ordinary "peer unreachable" failure, so **NTP sync and DNS resolution cannot succeed
under the Unix port at all, unconditionally, regardless of network reachability** - not a `src/` bug
(fixing it there would mean the twin dictating a production code shape that's wrong for real
hardware, exactly what CLAUDE.md's "don't edit `src/` only to make the twin run" owner constraint
rules out). Recorded in full in `BACKLOG.md`'s open question #5, which already tracked the general
"UDP verified only against the Unix port, not real rp2/lwIP" gap - this session sharpens that from
an untested-on-real-silicon caveat into a confirmed, structural, always-fails-here fact, and leaves
its resolution exactly where BACKLOG.md's open question #5 already put it: real rp2 hardware.

That same reproduction (a live, fully-booted, AP/hotspot-fallback-mode end-to-end run - no SSID
configured, so `sensortask_wozi.main()`'s own real object graph never left hotspot mode) surfaced a
second, independent, real finding: `captive_dns.py`'s `DNSServer.run()` loop has no backoff of its
own on a persistently-failing `recvfrom()` - measured at ~5 warning-level log lines/second,
continuously, for as long as the DNS server task runs. Recorded in full, including why this is
exactly a first concrete instance of Step 6's own "cascading recovery storms" category rather than
something to hand-patch mid-re-audit, in `BACKLOG.md`'s Step 6 scope entry (open question #6) right
where that category is defined.

**Follow-up audit (same session, after pushing the six fixes above)**: rather than wait for the
same bug *patterns* to reproduce as real failures again, a dedicated pass searched the codebase for
other latent instances of each one before they cause a real failure. Found and fixed four more:
`digital_twin/neopixel.py`'s `NeoPixel.writes` and `digital_twin/network.py`'s `WLAN`
`connect_calls`/`config_calls` had the identical unbounded-accumulator shape as the already-fixed
`I2C.log`/`SPI.log` (bounded to `deque(maxlen=...)` the same way); `digital_twin/machine.py`'s
`WDT.would_have_triggered_log` too; `digital_twin/_fram_chip.py`'s `_load_state()` was the exact
read-side mirror of the `save_state()` fragmentation bug (a single-shot `bytearray.fromhex()` over
the whole FRAM image), rewritten to stream-decode in chunks the same way. Also closed the test gap
that let the `SCD30_Reader.get_cfg_schema()` bug through in the first place: neither
`tests/test_sensortask_wozi.py` nor `tests/test_digital_twin_sensortask_integration.py` had ever
exercised the real `PUT /sensors` route against SCD30 (the former only ever `PUT` SGP40; the latter
never `PUT /sensors` at all) — both now do. Full suite: 2138 passing (up from 2128 after the first
six fixes), `src/` coverage 94% → 95%, `digital_twin/` steady at 96% with several files now at
100%. The two open questions in `BACKLOG.md` (the soak's memory-flat tolerance, and whether SCD30
needs twin-side chip-state persistence) remain genuinely unresolved — not chased further here,
deliberately left for the project owner rather than guessed at.

**SCD30 twin persistence + memory-decline root-cause session (follow-up, owner-directed)**: the
project owner directed two things — build the SCD30 twin-side persistence feature flagged above (if
the twin's own decline could be shown to genuinely stabilize, plus noise, the soak's tolerance could
be sized to it) and dig into the memory-decline question properly rather than leave it open.

`digital_twin/_scd30_chip.py`'s `Scd30Chip` gained a `state_path`/`save_state()`/`_load_state()` set
mirroring `FramChip`'s own pattern (plain `json.dump()`/`json.load()`, not chunked — five scalars,
not an 8KB buffer, no realistic fragmentation risk), persisting exactly the five settings
`src/asy_scd30_driver.py`'s own setters document as NVM-persisted on real hardware (measurement
interval, ambient pressure, altitude, temperature offset, ASC enable) — never the live CO2/temp/
humidity readings, matching what a real power cycle actually does to the sensor. Wired through
`digital_twin/machine.py` (`configure_scd30_state_path()`/`flush_scd30()`/`_current_scd30_chip`,
identical shape to the existing FRAM globals) and both entry points
(`digital_twin/run_wozi_integration.py`'s `--scd30-state-path`, defaulting to
`digital_twin/scd30_state.json` next to the FRAM state file; `digital_twin/launch.py`'s own flag,
defaulting to `None`/in-memory like its own `--fram-state-path`). Full test coverage added
(round-trip, no-autosave-before-explicit-save, persisted-file-shape, live-readings-never-persisted,
missing-file, malformed-JSON, machine.py wiring, CLI parsing for both entry points).

The memory-decline investigation itself is the long story now captured in `BACKLOG.md`'s open
question #6 (not duplicated here) — the short version: the earlier "will stabilize, just a slow
warm-up transient" read turned out to be wrong once measured over hundreds of cycles instead of 100;
it's a real, continuous, HTTP-independent decline. Real, attributed contributors were found (SCD30's
own read-and-store cycle, SGP40+BMP3xx's own read-and-store cycles), but a genuine ~245 bytes/sec
residual survives disabling every real `machine.Timer` starter in the system — including a
`digital_twin/machine.py` `WDT.feed()` rewrite that looked like a clean fix (avoiding its own
cancel-and-recreate-task-per-call pattern) and passed every existing test, but was proven by a
rigorous same-script A/B test to not actually be the cause, and was reverted rather than kept as a
misleading fix. `_MEM_FLAT_TOLERANCE_BYTES` was deliberately left untouched — the project owner's
own condition for loosening it ("no leak, will stabilize, not continuously drop") was directly
contradicted by the fresh data, so tightening the net around a still-real, still-open problem instead
of loosening the gate around it was the only defensible move here. The project owner decided this
becomes its own dedicated Step 6, run in a separate session immediately after this branch merges —
see `BACKLOG.md`'s open question #6 for the full carry-forward brief.

**Two real bugs found via the project owner's own manual run on real hardware (a real Linux machine,
not this session's own sandbox), same session**: (1) `src/asy_webserver_service.py`'s
`_get_measurements()`/`_get_sensors()` both re-wrapped a result that the driver-level
`get_dict_data()`/`get_dict_cfg()` had *already* self-wrapped with the sensor's own name
(`config_manager.make_dict()`/`base_classes._get_dict_cfg()`'s own `{name: {...}}` shape), producing
`{"SCD30": {"SCD30": {...}}}` for every real sensor on both `/measurements` and `/sensors` — a real,
general-scope production bug, not twin-specific, present since before this session and never caught
by any existing test because `tests/test_asy_webserver_service.py`'s own `_FakeModule` fixture
happened to return an already-flat shape (the identical class of test-fixture-doesn't-match-reality
gap `_flatten_cfg_values()`'s own fix already hit once before in this same file), and because both
`tests/test_sensortask_wozi.py`'s and `tests/test_digital_twin_sensortask_integration.py`'s own
real-driver/real-HTTP tests only ever checked top-level response keys, never the values. Fixed via
`.update()` instead of indexed assignment in both methods; the fake fixture (`_NestedCfgModule`,
already existing for the `_flatten_cfg_values()` precedent) extended to also cover
`get_dict_data()`, every affected test updated to the correct nested shape, two new dedicated
regression tests added, and both real-driver test files' own GET assertions strengthened to check
the values (not just top-level keys) so this class of bug can't slip through unnoticed again. (2)
`digital_twin/run_wozi_integration.py`'s `_soak()` let a single failed HTTP request (a real
`OSError: [Errno 104] ECONNRESET`, hit directly running the real default 20-cycle soak against the
real assembled system) crash the entire diagnostic run, instead of tolerating it the way the real
server it's driving already tolerates a rejected/reset connection
(`WebserverService._serve()`'s own `max_connections=3` reject-when-full path closes with zero
response ever written, by design) — `_soak()` now catches `OSError` per-request in both its warmup
and main cycle loops and records a failure instead of propagating, with a new regression test
(`test_soak_records_a_connection_reset_as_a_failure_instead_of_crashing`) driving it against a real
socket server that resets every connection immediately. Investigating this surfaced a third, more
serious, still-unresolved finding (a real MicroPython Unix-port interpreter segfault under heavy
concurrent connection load) — see `BACKLOG.md`'s open question #7, folded into the same dedicated
Step 6 session as the memory-decline investigation above.

## Out of scope for all five steps

- Real website content (stub only, see Step 4).
- The future per-variant build-script generator itself (only its constraints are honored, per
  "Generator-readiness constraint" above).
- The other three deployed variants (arzi/neu×3) — this prototype is `wozi` only.
- Real-hardware build genericization and physical-hardware verification — comes after all five
  steps merge back and the large audit closes, not a branch of its own inside this scheme.
- Editing `improved-quality/sensortask-wozi.py`, `ext/microdot.py`, or `tests/machine.py`.
