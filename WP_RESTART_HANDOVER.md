# WP restart handover — pre-implementation state

**Temporary file.** Its only purpose is to carry the pre-implementation state of session
`f21f1990-6b52-5b40-b4b2-b9f45eaf712a` (2026-09-15/16) into a fresh session. Delete it once that
session has absorbed it — like `UART_C_PORT_CHANGELOG.md`, it is not permanent project
documentation.

## Provenance — how this was produced

Parts 1-3 come **from the session transcript**, not from memory or summary. The session was
compacted, so the originals were recovered from
`~/.claude/projects/-home-user-sensors/f21f1990-....jsonl`:

- **Part 1** — the project owner's initiating prompt, verbatim.
- **Part 2** — the project owner's own decision messages, extracted in order. Verbatim **except**
  for two passages describing the execution model that was used to carry the work out. That model
  was abandoned, and the owner directed it be removed so it does not seed a fresh session; the
  affected messages are marked where they appear. Nothing bearing on a design decision was
  altered.
- **Part 3** — the working checklist (`session_findings_todo.md`). The live file had been edited
  further *after* implementation began, so the pre-implementation state was rebuilt by replaying
  the original `Write` plus only the 11 `Edit`s made before that point. All 11 replayed cleanly
  with zero conflicts, and the result contains no implementation-era content.

  **All diagnostic content was then removed from it, at the owner's direction.** Gone are every
  root-cause analysis, ruled-out hypothesis, "gap found" inventory, and every past-tense claim
  about what the current code already does or does not do. What remains is the owner's decisions
  and the resulting action items. Where an action item previously rested on such a claim (for
  example "no change needed here — already correct"), it has been rewritten as something to check
  rather than something to trust.

  The reason: these findings were produced in a session whose later state proved unreliable, so
  they carry a real risk of being wrong, and a wrong finding presented as settled is worse than no
  finding at all. **Treat every statement in Part 3 about current code behavior as unverified.**

- **Later additions.** WP6, WP7 and Topics 9-11 in Part 3, and all of Part 5, were written after
  the checklist existed. They record design decisions and background the owner gave during the
  implementation attempt — the owner's own explanations, not findings from this session's analysis.
  Part 5 is the standing requirement to move that background into the permanent docs once the work
  is implemented and verified.

Implementation began immediately after Part 2's final message. **None of what it produced is
included here** — all of it was rolled back (see Part 4).

---

# Part 1 — The initiating prompt (verbatim)

A real-hardware session (branch `claude/real-hardware-memory-validation-p3vkxr`, PR #84 in this repo — do NOT merge, read, or depend on that branch/PR; it is being discarded once its two real findings are independently resolved here) found a real, unforeseen defect while testing against the real dev board. This branch, `claude/automated-build-chain-nuzumw`, is the project's reference branch — you are starting from its current head, and this is where the investigation and any eventual fix belong.

**The finding, verbatim from that session's own isolation work** (their BACKLOG.md commit, not present on this branch yet):

---
A config-persisting `PUT /sensors` resets its own HTTP connection when it lands under concurrent API load. HIGH IMPORTANCE, must be fixed — completely unforeseen (project owner, 2026-09-15); it is not to be tolerated in a test, and the failing test must not be weakened to accommodate it. Found by the two bench-tier config-write tests the bus-hazard work added (`tests_hardware/bench/test_bus_concurrency_under_api_load.py`'s `test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` and `test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load`), running against the real dev board on the shipped `threshold` build. **Isolated to the flash write itself**, three conditions, 2 GET workers × 8 iterations + 4 PUTs each, repeated:

| condition | connection resets |
|---|---|
| GET load only | 0 |
| GET load + PUTs returning "Unchanged" (accepted, nothing written) | 0 |
| GET load + PUTs that really persist to the flash filesystem | 1–2 per run, **every one on the writing connection** |

The host sees `ConnectionResetError: [Errno 104]`. Reproduced on most runs (5 resets across 3 change-mode rounds in the isolation probe, plus 4 of 4 pytest runs before it). Three facts narrow it: a bystander GET is **never** reset, only the connection whose own request is being serviced; the config always persists correctly afterwards (no data loss, no corruption); and the DUT's own `WEBSERVER` error log stays completely empty, so nothing on the device notices. A quiet (unloaded) persisting PUT never reproduces it.

**Why this is a design question, not a test question**: an RP2040 flash erase/program is inherently uninterruptible — XIP is disabled and interrupts are off for the duration, so the CYW43 link is unserviced and lwIP's timers do not run, which is exactly CLAUDE.md's F.3 "long-blocking operations must not stall timing-sensitive work" meeting an operation that cannot yield. The fix therefore has to be a design-level one in the REST/persistence layer (send the response before performing the persist, defer the write to a point where no connection is mid-response, or similar), decided by the project owner — not a tolerance added to the assertion. Note this interacts with an already-settled safety property: CLAUDE.md's WiFi-power-cycle recovery rule depends on "every real flash write is reachable only through the REST PUT path", so any redesign that moves the write off that path must re-establish that argument.
---

**Your task, in order:**

1. Add this finding to *this branch's own* `BACKLOG.md` (under "Open questions" or a new HIGH IMPORTANCE entry near the top, following this file's existing style) — it currently only exists on the discarded branch. Cite the source as PR #84 / commit `679c2b0`'s isolation work, not as your own new discovery.
2. Read `src/asy_webserver_service.py` (the REST/PUT handling, connection lifecycle, `_serve()`), `src/config_manager.py` (`write_config()` and how a persisting write reaches flash), and the vendored `ext/microdot.py` (read-only — never edit it, see CLAUDE.md's vendoring rule) closely enough to trace the exact code path a persisting PUT takes from request to flash write to response.
3. Check current MicroPython/rp2-port documentation and source directly (CLAUDE.md's standing "always verify against current docs, don't rely on training memory" rule) for the actual mechanism: does a flash erase/program really disable interrupts for its whole duration on this port, and does that really explain a *TCP RST* specifically (as opposed to just a stall)? Confirm or correct the hypothesis in the finding above — don't just assume it's right because it reads plausibly.
4. Also read CLAUDE.md's F.3 "long-blocking operations" rule and its WiFi-power-cycle-recovery rule (the "every real flash write is reachable only through the REST PUT path" invariant) — any fix approach you propose must be checked against both.
5. Once you have a real root-cause understanding (not just a restated hypothesis) and a short list of concrete fix approaches with their tradeoffs against the existing architecture and that invariant — **stop. Do not implement a fix. Do not write code changes beyond the BACKLOG.md entry in step 1. Do not open a PR beyond whatever this session's own tooling does automatically for the doc commit.** The project owner wants to discuss the approach with you before any implementation begins. End your turn with a clear write-up: root cause (or your best-evidenced current understanding of it if not fully certain), the candidate fixes, and their tradeoffs.

You do not have real-hardware access or a go-ahead to use it in this session (CLAUDE.md's standing gate) — this is a source/docs investigation, not a bench reproduction.

---

# Part 2 — Owner decisions, in order

The 17 messages between the initiating prompt and the start of implementation. These carry the
design decisions; Part 3 is the structured result of them.

## Decision message 2

> Actually, I understand the mechanism, but I don't understand why the already existing connection gets stalled by this. It should rather be like "as long as the connection which has already been established and waits for a response cannot be reset by more incoming connections, rather don't accept more incoming sessions". That would mitigate all of the other issues. Prioritize existing connections against new ones.

## Decision message 3

> Which options are actually available, how was that solved in other projects (actively search for it), and what would be your suggestion?

## Decision message 4

> I understand the options, but before I decide I need to know how our current system currently handles it wrt. reported errors:
>
> * For sure, the inflight value checks will reject any wrong values and report a failure in the immediate response, but that is not at stake at all, because it all happens before the actual flash.
> * The actual filesystem / flash writes - what failures can they produce and how are they reported currently? That's what probably could get lost.
> * Power losses right before or right at the moment of writing are dangerous anyway, that's already the case and accepted in the current scope.
>
> Check and report.

## Decision message 5

> That surfaces a lot of misunderstandings and complexity:
>
> * "What's not durable about this reporting: CFGMGR_<name> is not one of the seven FRAM-backed loggers": It was not meant to be like that. The ONLY module which NEVER has own FRAM logging is the FRAM module itself - for the reason that if FRAM is in error, it does not make sense to persist that in this very FRAM. Every other module shall have FRAM logging optional. 
> * Look into the facts stored for the TOML system setup files: There must be notes that some system services automatically get FRAM wired in implicitly if an FRAM module is installed / mentioned in the TOML file. WiFi and NTP should actually be included here. 
> * CFGMGR_* should automatically inherit the FRAM logger from the module if it has one wired. And all of that should be wired into the API and website status messages.
>
> Not 100% sure, but I think some of that is already the case and you didn't stumble upon it, so check thoroughly.
>
> Let's tackle this first before we go on. Give me a short report on what you found.

## Decision message 6

> Give me a short wrap-up of your findings, the current list is too detailed, what is the case, what are the consequences?

## Decision message 7

> My top-level assumptions, plans and questions:
>
> * WiFi, NTP and webserver are all mandatory modules of every build implicitly. They get FRAM logging wired up implicitly whenever FRAM is configured as present in the TOML, as the existing auto-FRAM-wired modules do. If no FRAM chip is wired up, they all get RAM logging by default. All of these modules get wired through the status API to the website (maybe already the case, only just RAM-logged?). The buildgen is adapted to adhere to this. 
> * Are there other modules affected by the same? FRAM-capable but never wired up?
> * ConfigManager gets optional FRAM-Logging right from the start if the module using this ConfigManager instance has FRAM. errno, wrnno reservation and consistency already done per default in the base classes, not mutable by the modules. If new errnos and wrnnos are to be introduced with this and this conflicts with other implicit conventions project-wide, the conflicting other errnos and wrnnos must be adapted allover and all of their usages (e.g. in the unit tests) must be aligned along. Take extra care that the ConfigManager and the Base Classes and their user modules don't run into an import loop!
>
>
> Are these plans complete and sound? 
> Before you start anything, research the code in detail and answer my questions.

## Decision message 8

> * "This isn't just a code change — it reshuffles the on-flash layout for every already-deployed device with real FRAM data," A pure non-issue. There are zero deployed devices so far, apart from the Dev board which is overwritten, deleted and rebooted allover anyway. Zero risk of data loss.
> * UART_Comm shall fully support FRAM, but not by default. Like some other drivers already do, from its API, it shall have the option of directly wiring it up to FRAM and it creates its own instance. Alternatively, it shall be able to inherit the FRAM instance of its upstream instanciator. I told the session writing it to do so, and to take example on the existing modules doing so. Check if it arrived like this.
> * "a FRAM chunk-allocation failure already degrades silently via a _diag() print, no errno recorded": Once a clean and verified firmware build is done, FRAM allocation is constant and therefore safe. Handling OK in that sense. But during the build itself / during the tests which run after a build, there is yet no verification if the allocated FRAM space is sufficient, that is completely silently lost. This feature must be added to the build / tests with high importance.
> * errno/wrnno range reservation ("base range 1-9, every driver starts at 10+") is only a documentation convention today: Okay as long as it is actually being obeyed
>
>
> Analyze again with this background and report back shortly what you found.

## Decision message 9

> * " it's currently documented in two places as a settled decision that UART_Comm never gets FRAM": This was never requested by me and is actually wrong. Needs to be fixed and fully implemented as discussed. Unit tests for full normal flow, full error handling / self-healing / resilience, biting coverage, regression are all to be added.
> * "but self.pr.err() is the bare synchronous print-only method, not err_s()." Needs to be updated and wired up through the API to the website with all unit tests (full normal flow, full error handling / self-healing / resilience, biting coverage, regression) to be added.
> * No need to do a full scale errno / wrnno audit here
>
>
> Generally, unit tests all go into all layers and tiers with the documented scheme (higher tiers include all lower tiers, digital twin and real hardware synchronity).
>
> Check, analyze and report back.

## Decision message 10

> FRAM init: Keep it sync and find a way how either the digital twin tests, or the real hardware tests (both of them must be able!) can reliably trigger on the out of memory message. As I said, it is stable once the build is done, no dynamic allocation ever. Therefore, validating the size is sufficient right after the build is enough. Actually, it does not even need its own errno / wrnno. It just needs a 100% sure and detectable check right after building that the space is sufficient.
> Would that work, thereby relieving all the complexity you schemed?

## Decision message 11

> Now go through your memory and through the transcript of this session again and note down all our found topics and the final decisions taken about them. Make a detailed to-do list out of it.

## Decision message 12

> Save that list in a temporary file, rather add details to be sure.

## Decision message 13

> 1. With all of the discussed items implemented, I could imagine a scheme which behaves identical on the API / website level, except for the immediate flash write feedback. But now, in case we encounter a flash write feedback, the new implementation would automatically generate a errno or wrnno entry inside the instantiating module's logging, be it RAM, be it FRAM. So we get around the original issue and still don't miss errors.
>
> 2. As already mentioned, we do not even add errno/wrnno for the out of FRAM memory. Within all of the many planned changes, try to keep the footprint minimal.  So nothing new to forward to the API. Handle via mpremote.
>
>
>
> Come back at me concerning the final implementation of (1). Would it work, and which options are still to be decided?

## Decision message 14

> 1. Accept as residual risk, not more risky than the current status.
> 2. Multiple PUTs to one sensor do not occur due to the API design, everything changed is submitted all at once. 
> 3. As simple as possible, probably just "write after connection is closed" is sufficient, as it's atomic per sensor / per module anyway due to API design
> 4. Everything stays as it is. Valid now means "validated". Persisted goes along with "no errno / no warnno recorded". API remains unchanged.
> 5. It gets the staged value if not written yet or the written value if already done.
> 6. Adapt to reflect the reality / these decisions.
> 7. This is ok. It would be found by the new tests. On the API and website, this chunking bust be hidden, the module must fold all of this into its status API consitently.
>
>
> Save these decisions and statuses in detail in our checklist. Make sure to reflect the latest decisions in every detail.

## Decision message 15

> Our PR's target branch was updated. Check, pull it in, analyze if something relevant for our scope was done.

## Decision message 16

> Add action items to our checklist what needs to be done for fulfilling the task. Then sort the list and find work packages. Save the list and tell me the names of the work packages.

## Decision message 17

> To each work package add:
> - a goal description, quality which must be reached to be sufficient.
> - More details by thoroughly checking if it is really complete, self-contained and harmonic
> - The requirement to check all touched files against our specifications
> - The requirement that complete functionality, resilience and biting coverage tests are to be added, regression tests if required.

## Decision message 18

*Edited: this message set out the execution model that was later abandoned. Its standing
requirements are kept; the delivery mechanism is removed.*

> Now implement the work packages.
> - Each work package needs an exhaustive, comprehensive account of the context before it starts.
> - Each is merged as soon as its work is done and CI is green.
> - Scan the results against the whole spec and consolidate the work
> - Allow no regressions, expect all units tests to stay working or to be adapted without losing strictness
> - Prefer added unit tests as scecified

---

# Part 3 — Final to-do & action list

Two things are combined here:

- The document the original five work packages were cut from, as it stood when implementation
  began, **reduced to the decisions and the action items** (see the provenance note above for what
  was taken out and why).
- **WP6, WP7 and Topics 9-11, added afterwards.** These cover design decisions the owner explained
  *after* that checklist was written, so they were never part of it. They are requirements on the
  same footing as everything else here.

---

# Session findings & to-do list — PUT /sensors connection reset + FRAM logging audit

Repo: `hundertvolt/sensors`, branch `claude/automated-build-chain-nuzumw` (the project's reference
branch). Session started from a real-hardware finding on discarded branch
`claude/real-hardware-memory-validation-p3vkxr` (PR #84, commit `679c2b0` — verified genuine, not
fabricated, by reading the actual PR/commit content on GitHub).

Already committed/pushed this session: BACKLOG.md entry (commit `3f7cc25` on the reference branch)
recording the original PUT/sensors finding verbatim, citing PR #84/commit `679c2b0` as source.
Nothing else has been implemented yet — everything below is analysis/decisions pending
implementation.

---

## WORK PACKAGES — sorted implementation units

Every decision below is final (see the topic sections further down). This section turns them into
concrete action items, grouped into packages by which files each one touches.

WP6 and WP7 were added later than WP1-WP5 and are not part of the original five; WP7 is largely
verification and documentation of an existing design rather than new implementation.

**Suggested order, and why** (the grouping is about file overlap, not about splitting the work up):
- **WP4 first.** Zero file overlap with anything, and no production code change at all — the
  cheapest way to get the FRAM capacity check in place before the packages that grow FRAM usage.
- **WP2 before WP5.** Both touch `config_manager.py`. Not a hard code dependency in either
  direction — WP5's deferred-write mechanism works against today's RAM-only `CFGMGR_<name>` logger
  and only gains FRAM durability once WP2 lands — but doing WP2 first means WP5's deferred-write
  errors are durable from the start instead of needing a second pass.
- **WP1 and WP3 both touch `buildgen/codegen.py`**, in different functions
  (`_emit_build_system`/device-wiring for WP1 vs. `_build_args_uart_link` for WP3), so either
  order works.

### WP1 — FRAM wiring: WiFi / NTP / Webserver (implicit-if-present)
**Depends on**: nothing. **Touches**: `buildgen/codegen.py`, `buildgen/validate.py`,
`SPECIFICATION.md`. **Corresponds to**: Topic 2 below.

**Goal**: WiFi, NTP, and the webserver's own error/warning history become durable across a reboot
automatically whenever a device's TOML wires a FRAM chip, with zero behavior change for devices
that don't — closing the gap where all three already have the class-level capability (same
mechanism every already-wired sensor uses) but the generator never gives them the chance.

**Sufficient when**: a FRAM-equipped device's generated `build_system()` constructs `conn`, `ntp`,
and `webserver` with real FRAM chunks; a non-FRAM device's generated build is behaviorally
unchanged (RAM-only, byte-identical construction order otherwise); `scripts/lint.sh`,
`scripts/typecheck.sh` (all three passes), and `scripts/test.sh` stay fully clean; no currently-
passing `buildgen`/digital-twin/unit test regresses.

**Completeness / self-containment / harmony check (do this last, not as a first-pass assumption)**:
- [ ] Confirm `conn`/`ntp`/`webserver`'s new `fram=` wiring is shaped identically to how
      `sysfunct`'s already works (same device-wiring resolution, no bespoke one-off logic invented
      for these three specifically).
- [ ] Confirm the reordered construction doesn't silently break anything else that assumed
      `conn`/`ntp` exist before `fram`'s old position (steps 2/3 vs. 6) — grep every generated
      construction line and every hand-written caller of `build_system()`'s intermediate state.
- [ ] Check how `DNSServer` receives its FRAM from `conn`, and that it still works once `conn`
      receives a *real* `AsyFramManager` rather than `None`.
- [ ] Run CLAUDE.md's mandatory bird's-eye-view scan across `buildgen/` and every module this
      touches once implemented — confirm no cross-file inconsistency was introduced, and if one
      is found, **flag and discuss it rather than silently fixing it**, per that same standing rule.

**Spec-conformance requirement**: check every touched file (`buildgen/codegen.py`,
`buildgen/validate.py`, generated device modules, `SPECIFICATION.md`) against `SPECIFICATION.md`
Part D's full "ready to land" checklist and Part G's shared-primitive catalog before considering
this WP done — in particular, confirm this doesn't invent a second implicit-FRAM-wiring pattern
when the existing `_fram_kw`/device-wiring mechanism already covers the shape needed.

**Testing requirement**: full functional coverage of the FRAM-present path; full resilience/edge-
case coverage of the FRAM-absent path *and* a misconfigured `fram_target` (pointing at a
nonexistent/wrong-typed instance); regression tests confirming every other currently-generated
device's build output is otherwise byte-for-byte unaffected — at both the mock and digital-twin
tiers.
- [ ] Reorder `build_system()`'s construction so `fram` (currently step 6) is built before `conn`
      (step 2) and `ntp` (step 3) — and `spi0` (step 5) ahead of them too, since `fram` needs it.
      Accepted as zero-risk (no deployed devices besides the routinely-wiped dev board).
- [ ] Extend the `[device.wiring] fram_target` mechanism (`codegen.py:390-394`, today only feeds
      `sysfunct`) to also emit `fram=` for `conn` and `ntp`.
- [ ] Add `fram=` wiring to the `webserver = WebserverService(...)` emission (`codegen.py:547`) —
      no reordering needed for this one, simplest of the three.
- [ ] Extend `buildgen/validate.py`'s `_DEVICE_WIRING_CONSUMERS` dict (`validate.py:71`, currently
      `{"fram_target": (..., "sysfunct")}`) to also list `conn`/`ntp`/`webserver` as valid
      consumers of the device-level `fram_target` key.
- [ ] Update `SPECIFICATION.md`'s documented construction order and "seven-chunk order" note to
      match the new real order once implemented.
- [ ] Tests (mock + digital twin): FRAM-present device → `conn`/`ntp`/`webserver` inherit it and
      their `self.pr` becomes `PrintLogHistoryStore`; no-FRAM-chip device → all three stay
      `PrintLogHistory` (RAM-only) — regression-proof the fallback path explicitly, not just the
      happy path. Check whether `DNSServer` (owned internally by `conn`) inherits transitively,
      and add a test asserting it.

### WP2 — FRAM wiring: ConfigManager inherits from its owning module
**Depends on**: nothing (see coordination note above re: WP5). **Touches**: `config_manager.py`,
`base_classes.py`. **Corresponds to**: Topic 3 below.

**Goal**: Every sensor's own config-write failure history durably follows whatever FRAM durability
its owning module already has — closing the specific bug where `SensorReaderConfig` already
receives `fram` in scope and already uses it for its own logger, but silently drops it before
constructing the `ConfigManager` it owns.

**Sufficient when**: a FRAM-wired sensor's `CFGMGR_<name>` errno/wrnno history survives a
simulated reboot exactly like its owning module's own history already does; a non-FRAM sensor
behaves exactly as today (RAM-only, no observable change at all); no import cycle exists (verified
by actually running `scripts/typecheck.sh`/`scripts/test.sh` against the real Unix-port
interpreter, not by inspection alone); `write_config()`'s own errno numbering, response shape, and
exception handling are provably unchanged — this WP only changes *where* the log lives, never
*what* gets logged or *when*.

**Completeness / self-containment / harmony check**:
- [ ] Confirm `ConfigManager` ends up matching the exact same "accept `fram`, call `make_logger`"
      shape as every other FRAM-capable class in `src/` — not a bespoke variant with its own
      slightly different parameter order/defaults.
- [ ] Run CLAUDE.md's mandatory bird's-eye-view scan across all of `src/` now that a
      previously-fixed class boundary (`ConfigManager.pr` always being a plain `PrintLogHistory`)
      has changed — confirm nothing elsewhere assumed that (an `isinstance` check, a direct
      attribute access that would break on `PrintLogHistoryStore`, etc.).
- [ ] Confirm the FRAM chunk-count increase this introduces (one new chunk per FRAM-wired sensor)
      is reflected in `SPECIFICATION.md`'s construction-order/chunk-order documentation, not left
      stale — and cross-check against WP4's capacity test once both exist.
- [ ] If the scan surfaces any cross-file inconsistency, **flag and discuss it, don't silently
      fix it** — same standing rule as WP1.

**Spec-conformance requirement**: check `config_manager.py` and `base_classes.py` specifically
against `SPECIFICATION.md` Part D's checklist and Part C.5.2 (setter dispatch / `ConfigManager`
architecture), since Part C.5.2 is the one place this module's documented architecture is being
extended and must stay accurate afterward.

**Testing requirement**: functional (FRAM present → durable, proven across a simulated reboot, not
just "the constructor accepted the parameter"); resilience/biting coverage (FRAM chunk allocation
itself fails at construction time → falls back to RAM-only exactly like every other
`PrintLogHistoryStore` consumer already does, and sensor construction does not crash or partially
complete); regression (every existing `tests/test_config_manager.py` write-failure test still
passes unmodified or is extended, never weakened, to accommodate this change).
- [ ] Add `fram: "AsyFramManager | None" = None` to `ConfigManager.__init__`, with
      `if TYPE_CHECKING: from asy_fram_manager import AsyFramManager` guarding the type-only
      import — mirror `base_classes.py:25`'s exact pattern. **Never** a real runtime import (would
      create `config_manager → asy_fram_manager → base_classes → config_manager`, a genuine
      circular import, since `asy_fram_manager.py:14` already really imports from
      `base_classes.py`).
- [ ] Change `config_manager.py`'s logger construction from direct `PrintLogHistory(...)` to
      `make_logger(fram, history_length, debug, name="CFGMGR_" + name)` (real import of
      `make_logger` from `print_log.py` — check for an import cycle before relying on it).
- [ ] Make `SensorReaderConfig.__init__` (around `base_classes.py:281-285`) forward its own
      in-scope `fram` into the `ConfigManager(...)` call it makes.
- [ ] Decide whether any new errno/wrnno is needed; the intent is that none is.
- [ ] Tests: (a) a `SensorReaderConfig`-based module built with `fram=<manager>` → its
      `.cfgmgr.pr` is FRAM-backed and a real write-failure errno persists across a simulated
      reboot/restore; (b) built with `fram=None` → stays RAM-only (regression); (c) confirm
      `/status`'s `CFGMGR_<name>` entry reflects the persisted history correctly in the FRAM-backed
      case with no API-layer code change required.

### WP3 — FRAM support: UART_Comm (was wrongly, deliberately excluded)
**Depends on**: nothing. **Touches**: `asy_uart_link_driver.py`, `buildgen/codegen.py`
(`_build_args_uart_link`, a different section than WP1), `devices/dev.toml`. **Corresponds to**:
Topic 5 below.

**Goal**: UART_Comm's own error/warning history becomes optionally FRAM-backed via the API, exactly
as originally intended — both "wire it directly, own chunk" and "inherit the upstream
instantiator's logger" — replacing the currently-documented, incorrect "never" exclusion with a
real, working, fully tested path.

**Sufficient when**: a `dev`-built UART link instance can be wired via TOML to either get its own
FRAM chunk or reach through to an upstream logger, and its errno/wrnno history is durable/shared
accordingly; `wozi` (zero UART instances) is shown to be unaffected — demonstrated, not assumed; all
four bus-hazard test tiers pass, including real hardware once a real-hardware go-ahead exists for
that session.

**Completeness / self-containment / harmony check**:
- [ ] Confirm this fix does **not** quietly change UART_Comm/`UartLinkExerciser`'s "never blocks
      the asyncio loop, not even in a wait state" invariant — `CLAUDE.md`'s sharpest, most
      easy-to-violate-by-accident rule in the whole codebase. FRAM chunk I/O goes through already-
      awaited calls, but this is a new code path through a module singled out by its own hard rule
      and deserves explicit, dedicated re-verification, not an assumption that "it's just a logger
      call, so it's fine."
- [ ] Confirm the new `# @wiring fram_target ...` tag follows the exact grammar every other
      driver's tag already uses (`SPECIFICATION.md` Part C.14.2), not an invented variant.
- [ ] Run CLAUDE.md's mandatory bird's-eye-view scan, with particular attention to this module's
      own hard rule (above) — flag and discuss rather than silently fix anything that doesn't sit
      cleanly with it.
- [ ] Confirm this stays classified correctly in `UART_C_PORT_CHANGELOG.md` per `CLAUDE.md`'s
      standing rule for *any* change to this protocol module, however small: this is Python-
      internal (no wire-format/C-port impact), and that classification needs its own log entry,
      not just an assumption.

**Spec-conformance requirement**: check `asy_uart_comm.py`/`asy_uart_link_driver.py` against
`SPECIFICATION.md` Part J (the UART protocol spec) and Part D's checklist; confirm the "never
blocks" invariant section (Part F.5.8/F.5.9) is explicitly re-read and re-checked against this
specific change, not just generally kept in mind.

**Testing requirement**: full four-tier coverage (mock/twin/flash/bench) as already itemized below,
**plus** an explicit blocking-latency regression test proving FRAM logging introduces no new
blocking wait in the UART read/write loop, **plus** confirmation the required
`UART_C_PORT_CHANGELOG.md` entry exists and is correctly classified.
- [ ] Remove the incorrect "no fram=" decision + comment in `asy_uart_link_driver.py:58`.
- [ ] Remove the matching incorrect comment/behavior in `buildgen/codegen.py:220-225`.
- [ ] Wire `UartLinkExerciser.__init__` to accept `fram=`/`logger=` and forward one or the other
      into its own `UART_Comm(...)` construction (class-level support already exists in
      `asy_uart_comm.py` — no change needed there).
- [ ] Add a `# @wiring fram_target ...` tag to the UART link driver's own source (none exists
      today, unlike e.g. SGP40's) so a device TOML can request it per-instance.
- [ ] Wire it into `devices/dev.toml` (the only device with real UART instances).
- [ ] Full test coverage across all four tiers (standing bus-hazard rule, already applied to UART
      regardless of this fix, just never satisfied for the FRAM path): `tests/` (mock — normal
      flow, allocation-failure fallback, regression against the no-`fram=` default),
      `tests/test_digital_twin_*` (twin — errno history survives a simulated reboot),
      `tests_hardware/flash/` (raw driver, real hardware), `tests_hardware/bench/` (full HTTP
      stack, confirm the error log surfaces through `/status` end-to-end).

### WP4 — FRAM capacity verification (deterministic post-build check)
**Depends on**: nothing — pure test addition, **zero production code change**. **Touches**:
`digital_twin/` tests, `tests_hardware/flash/`. **Corresponds to**: Topic 6 below.

**Goal**: A FRAM-capacity overflow (shipped firmware asks for more FRAM than the chip has) becomes
a hard, automatic, pre-flash test failure instead of a silent boot-time console print nobody's
watching — for every current and future device, at zero runtime/API cost.

**Sufficient when**: every real device TOML has a passing capacity-check test on both the digital
twin and (once real-hardware access is available) real hardware; a deliberately-shrunk test
fixture's `max_size` reliably fails the new check (a genuine negative test, proving the check can
actually fail, not just a happy-path assertion that never exercises the failure branch); zero
change to any `src/` file, shown by diff.

**Completeness / self-containment / harmony check**:
- [ ] Confirm the twin-tier check runs for **every** device TOML in `devices/`, not just wozi/dev
      — a check covering only the two most-tested devices does not actually satisfy this WP's own
      goal.
- [ ] Confirm this doesn't duplicate or silently conflict with any existing
      `tests_scripts/test_buildgen_definitions.py`-style validation.
- [ ] Run the bird's-eye-view scan across the new test files themselves for consistency with how
      other digital-twin/`tests_hardware/flash` tests are structured in this codebase (fixture
      naming, assertion style, `mpremote` harness usage) — flag and discuss any inconsistency
      rather than silently picking a new pattern.

**Spec-conformance requirement**: place the new tests in the correct tier directories per
`SPECIFICATION.md` Part E's testing-tier taxonomy; update `tests_hardware/README.md` with the
required entry for the new real-hardware check (every `tests_hardware/` addition needs its own
README entry per that file's own convention) — check this file's existing structure before adding
to it, don't assume a location.

**Testing requirement**: this WP *is* testing, so its own meta-coverage matters — both the positive
(fits) and negative (deliberately doesn't fit) cases must exist at the twin tier at minimum, since
the negative case is what actually proves the check works rather than merely never having failed.
- [ ] Review `asy_fram_manager.py`'s `get_chunk()`/`get_timestamped_chunk()` and
      `asy_fram_driver.py`'s `FRAM_SPI` bare `.err()`/`.wrn()` calls, and decide whether any
      change is needed here.
- [ ] Digital twin: test that runs the real `build_system()` (already exercised by
      `digital_twin/run_generic_integration.py` against `_fram_chip.py`'s fake SPI chip) for
      **every** real device TOML and asserts `fram.allocated_size <= fram.size` (equivalently: no
      FRAM-chunk-holding module ended up with a `None` chunk reference) right after construction.
- [ ] Real hardware: equivalent check in `tests_hardware/flash/`, reading
      `fram.allocated_size`/`.size` directly off the live device via the existing `mpremote`-based
      harness. **Decided: mpremote-only, no new `/status`/API field** — keeps this change's
      footprint minimal, per explicit direction.
- [ ] Run this check against every currently-defined real device TOML, not just wozi/dev.

### WP5 — PUT /sensors deferred-write fix (the original connection-reset bug)
**Depends on**: nothing code-wise (see coordination note above re: WP2 for full FRAM-durability
value). **Touches**: `asy_webserver_service.py`, `config_manager.py`, `SPECIFICATION.md` (F.2
invariant + related docs), confirm-only on `api_response.py`. **Corresponds to**: Topic 1 below.

**Goal**: Close the confirmed real-hardware connection-reset defect without weakening the failing
bench tests that found it, without losing any error visibility (a genuine write failure must still
be discoverable, durably where WP2 applies), and without changing the client-visible API contract
— by deferring the flash write until after the response and connection are safely clear of the
network freeze it causes.

**Sufficient when**: the two real bench tests that found this
(`test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load`,
`test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load`) pass on real
hardware with zero connection resets and unmodified, un-weakened assertions; no existing
`tests/test_asy_webserver_service.py`/`tests/test_config_manager.py`/`tests/test_base_classes.py`
test regresses; `GET /sensors`'s staged-vs-written correctness is independently and explicitly
tested, not merely implied by the PUT tests passing.

**Completeness / self-containment / harmony check**:
- [ ] Confirm this does **not** get silently applied to SCD30 — per `SPECIFICATION.md`, SCD30
      "dispatches through its own non-persisting setter (no `cfgmgr`, NVM-backed)," so it doesn't
      go through `ConfigManager.write_config()` at all. Explicitly verify and test that SCD30 is
      unaffected, rather than assuming the staging mechanism naturally skips it.
- [ ] Run CLAUDE.md's mandatory bird's-eye-view scan across `src/` given this changes a
      cross-cutting pattern (every `SensorReaderConfig`-based PUT path) — confirm whether the other
      PUT-backed endpoints (`/networking`, `/system`, `/notification`) also need this treatment or
      are deliberately, explicitly out of scope; **flag and discuss, don't silently decide either
      way**.
- [ ] Confirm the "at most one staged value per sensor at a time" assumption (which this whole
      design's simplicity rests on) genuinely holds for **every** existing `/sensors` PUT caller in
      the codebase — the web UI, `js/mock-server.js`, any device/bench script — not just the two
      bench tests that originally found the bug.

**Spec-conformance requirement**: check `asy_webserver_service.py`, `config_manager.py`, and
`api_response.py` against `SPECIFICATION.md` Part A.5 (Microdot/REST layer) and Part C.5.2 (setter
dispatch) explicitly; update the F.2 invariant and search the rest of `SPECIFICATION.md`/
`CLAUDE.md` for any other place still stating or implying that a config write is always synchronous
within the request — every one of those needs updating, not just the one already identified.

**Testing requirement**: functional (staged → written happy path; `GET` returns the correct value
at each stage); resilience/biting coverage (the deferred write genuinely fails with a real
`OSError`/`MemoryError` — confirm the errno lands in the right place per WP2's wiring for that
module; the accepted power-loss-before-attempt case behaves exactly as accepted, not worse in some
other way); regression (every currently-passing synchronous-path test for an ordinary, uncontended
single PUT); plus the real-hardware confirmation above, once a real-hardware go-ahead exists for
that session.
- [ ] `asy_webserver_service.py`'s `_put_sensors()`/`_serve()`: after the (unchanged,
      validation-only) response is built, defer the actual `write_config()` call(s) to run
      **after** `_close_writer()` completes for that connection — one fire-and-forget call per
      closed connection with a staged write, no task queue (API design guarantees at most one
      staged value per sensor at a time).
- [ ] `config_manager.py`: add a single per-`ConfigManager` staging slot (not a queue) holding the
      validated-but-not-yet-written data between "response sent" and "write executes."
- [ ] `config_manager.py`'s read path (`get_dict()`/`_get_values()`): consult the staging slot
      first, fall back to `_cache` — implements the decided `GET` read-your-write rule (staged
      value if not yet written, written value once it has). Clear the staging slot once the
      deferred write completes, success or failure.
- [ ] Review `write_config()`'s exception handling/`errno=14`/"`_cache` committed only after
      success" contract, and `api_response.py`/`WriteValidity`, and decide what each needs.
- [ ] Update `SPECIFICATION.md`'s F.2 invariant text (and a repo-wide grep for anywhere else the
      old "write is always synchronous within the request" assumption is stated) to reflect: a
      flash write is now reachable only through a REST PUT that has already been accepted **and
      whose connection has already closed**; note the accepted residual-risk window explicitly
      rather than implying zero risk unconditionally.
- [ ] Add a test asserting the `/status` errcount presentation stays uniform across every module as
      WP1/WP3 add more FRAM-wired modules (no module special-cases how its own entry vs. its
      `CFGMGR_<name>` entry is shown).
- [ ] Full test coverage: normal flow (staged → written, GET reflects the right value at each
      stage), error handling (deferred write fails → errno recorded in the right place per WP2's
      wiring for that module, `_cache` unchanged exactly as today), the accepted residual-risk case
      (simulated restart between response and deferred write — confirm it's silently lossy exactly
      as accepted, not silently *wrong* some other way), and regression against every existing
      `write_config()`/`_set_dict_cfg()` test for the ordinary uncontended-PUT case.
- [ ] Re-verify the finished implementation against `CLAUDE.md`'s F.3 rule and the updated
      WiFi-power-cycle-recovery invariant explicitly, once code is written.
### WP6 — Boot-time watchdog safety for the one-time setup batch
**Depends on**: nothing. **Touches**: `system_service.py`, `buildgen/codegen.py` (generated
`build_system()`), `tests/test_system_service.py`. **Corresponds to**: Topic 9 below.

**Goal**: the one-time `setup()` calls made during boot cannot starve the hardware watchdog, no
matter how many modules a device wires, and a device built without a watchdog behaves identically
through the same code path.

**Background the owner established (implement against this, it is the requirement):**
- A one-time multi-second delay at boot is **not** itself a problem. These devices run for months
  and are rarely rebooted, and a short period of API unavailability after a reboot is normal for
  any networked device. Do not optimise boot latency for its own sake.
- What *is* a problem is approaching the watchdog's timeout while those one-time `setup()` calls
  run. `WDT(timeout=8000)` is armed before them (~8388ms hard cap, `SPECIFICATION.md` Part F).
- The owner's chosen remedy: **feed the watchdog after every `setup()` call.** These calls happen
  once, at boot, outside any loop — so a feed placed there cannot degenerate into something that
  keeps feeding a hung system forever. That property is what makes it safe, and it must stay true.
- A device may legitimately have **no** watchdog. That case must be handled by the same code path,
  elegantly and generally — the owner's proposal was that `SystemService` take the watchdog as a
  constructor argument, defaulting to a no-op when absent, rather than sprinkling `if wdt is not
  None` at every call site.

**Sufficient when**: the setup batch feeds the watchdog after each call; a no-watchdog build runs
the identical path with a no-op and needs no special-casing; `scripts/lint.sh`,
`scripts/typecheck.sh` and `scripts/test.sh` stay clean.

**Completeness / self-containment / harmony check**:
- [ ] Confirm the feed cannot be reached from any repeating/looping context — its safety rests
      entirely on being one-time and boot-only.
- [ ] Confirm the no-watchdog default genuinely removes the branch rather than hiding it.
- [ ] Run CLAUDE.md's bird's-eye-view scan over `src/` afterwards; flag any cross-file
      inconsistency for discussion rather than silently fixing it.

**Spec-conformance requirement**: check every touched file against `SPECIFICATION.md` Part D's
checklist and Part G's shared-primitive catalog — in particular, do not invent a second
watchdog-access pattern if one already exists.

**Testing requirement**: functionality (feed happens per call, in order); resilience/edge cases
(no-watchdog build; empty setup list; a `setup()` that raises); biting coverage (a long batch
that would starve the watchdog without the feed); regression (existing boot/task-supervisor tests).

- [ ] Give `SystemService` an optional watchdog, defaulting to a no-op, and route every feed
      through it.
- [ ] Feed after each call in the one-time boot setup sequence.
- [ ] Have `buildgen` emit whatever call shape this settles on.
- [ ] Add the unit tests above — the owner asked explicitly for functionality, error handling /
      resilience, coverage and regression tests on this change.

### WP7 — Sensor read-timer architecture: preserve, verify, document
**Depends on**: nothing. **Touches**: `system_service.py` (read-only unless a defect is found),
`SPECIFICATION.md`. **Corresponds to**: Topic 10 below.

**Goal**: the existing sensor read-trigger timing design is understood, proven correct against the
real rp2 MicroPython build, left intact, and written down — so no future change erodes it by
accident.

**Background the owner established — this is the design intent, not an observation to re-derive:**
- Every sensor's read period is settable in **whole multiples of one second, one second being the
  shortest**.
- The read-trigger timers are therefore **staggered evenly across exactly one second in total** —
  not at a fixed per-timer gap. With N timers spread over that one second, they sit at the maximum
  achievable mutual distance for the shortest possible period.
- Because they are **system timers**, they do not drift relative to one another once armed. Their
  phase relationship is fixed for the whole runtime.
- Those two facts together are the point: **no two sensor reads ever coincide, for any combination
  of configured periods, for the entire runtime** — no harmonics, no beat frequencies, no races
  from period overlay.
- This is also why the timer starters are triggered by **another real timer** (precise, interrupt,
  callback driven) and **not** by an `asyncio.sleep()`, which offers only coarse timing.
- Consequence for any future work: the one-second *total* spread is load-bearing and must not be
  changed into a fixed per-task gap, nor rescaled. One-time boot `setup()` calls are a **separate
  list** with no such obligation (Topic 9 / WP6) and must not be folded back into this mechanism.

**Sufficient when**: the above is verified against the pinned rp2 MicroPython source (not from
memory, per CLAUDE.md's standing rule), any deviation between intent and code is reported rather
than silently "fixed", and the reasoning is recorded in `SPECIFICATION.md`.

**Testing requirement**: a regression test that pins the *total* one-second spread and fails if it
is turned into a fixed per-task interval or rescaled; a test that the setup-call list carries no
stagger obligation.

- [ ] Verify the no-relative-drift and one-second-spread claims against the pinned MicroPython
      rp2 source and the current rp2 port docs.
- [ ] Verify the running code actually implements the intent; **report any mismatch, do not
      silently change it** (CLAUDE.md's flag-don't-fix rule).
- [ ] Add the regression test above.
- [ ] Document the mechanism and its rationale in `SPECIFICATION.md` (see Part 5).



---

## TOPIC 1 — PUT /sensors resets its own HTTP connection under concurrent load — **DECIDED, fully scoped, no owner decisions remain**

### FINAL DESIGN — all owner decisions now made (this session, latest round)

The chosen shape is the *minimal* form of "respond first, persist after" (a lightweight version of
what was earlier framed as option A/C, not a general-purpose write-behind queue): no background
worker infrastructure, no pending-value queue, no coalescing logic — because two facts collapse all
of that complexity away:

- **The API design guarantees no concurrent/overlapping PUTs to the same sensor's fields** — a
  sensor's config is always submitted as one complete, all-at-once field set per PUT (owner's own
  point 2). There is never a "second PUT arrives before the first one's write has landed" case to
  reconcile, so there is nothing to queue or coalesce — at most one staged value can ever exist per
  sensor at a time.
- **Each sensor's write is already atomic per module by API design** (owner's own point 3) — so the
  simplest possible trigger is correct and sufficient: **perform the actual `write_config()` call
  right after that connection's HTTP response has been sent and the connection closed**, still
  within the same request-handling flow (no separate scheduled task, no queue-draining worker). No
  "idle moment" heuristic, no interval, no `_open_conns`-threshold logic — none of that is needed.

**Error reporting — decided direction:** a deferred write reports failures through
`write_config()`'s own existing exception path into `CFGMGR_<name>`, rather than through any new
mechanism. **No new logging machinery and no new errno are to be introduced for this.** Verify how
that path actually behaves when the call happens after connection-close rather than inline, and
implement whatever that requires. **Topic 3 (ConfigManager inherits FRAM from its owning module)
is the precondition** for these errors being durable rather than RAM-only.

**Residual risk, explicitly accepted (owner's point 1):** if the device loses power *before* the
deferred `write_config()` call ever runs at all (i.e. between "response sent" and "write actually
attempted"), nothing is ever logged anywhere — the staged change is lost with zero trace, RAM or
FRAM, since `write_config()` never got a chance to hit its own exception handler. **Owner's ruling:
accept this as residual risk — it is not any riskier than the current status quo** (today, a
power-loss exactly during the sub-millisecond window between "response formatting" and "the
synchronous `write_config()` call actually executing" carries the identical loss, just an
even-narrower window; the deferred design only widens that window slightly, it doesn't introduce a
new *kind* of risk). No further mitigation planned for this case.

**HTTP/API contract — explicitly unchanged (owner's point 4):** no new response states, no envelope
change, no new field. `"Valid"` keeps its existing meaning of **"validated"** only — it no longer
implies (and per this design, never strictly guaranteed it anyway) that the byte is already on
flash. **"Persisted" is now signaled implicitly by the absence of any errno/wrnno recorded against
that write** — i.e. success is inferred by silence in `CFGMGR_<name>`'s error log, not by a
different response value. `api_response.py`'s `WriteValidity` (`Literal["Invalid", "Unchanged",
"Valid", "Failed"]`) is **not** touched — no `"Pending"` state, no new literal.

**`GET /sensors` read-your-write semantics — decided (owner's point 5):** a GET returns the
**staged value if the deferred write hasn't landed yet, or the actually-written value once it
has**. Concretely: the read path must check for a not-yet-flushed staged value for that key first,
falling back to `_cache` (the already-committed value) once the deferred write completes and clears
the staged slot. This is a small, real code change to the read path (`get_dict`/`_get_values` in
`config_manager.py` today read `_cache` directly) — it needs to consult the staging slot too, not
just `_cache`.

**FRAM-chunk footprint growth — accepted, with one explicit new requirement (owner's point 7):**
once Topic 3 lands, every FRAM-wired sensor's `CFGMGR_<name>` draws its **own separate** FRAM chunk
(a fresh `get_chunk()` call, distinct from the owning module's own chunk) — so this design
roughly doubles FRAM chunk consumption per FRAM-wired sensor. **Accepted as fine** ("it would be
found by the new tests" — i.e. Topic 6's capacity check is exactly the backstop for this). **New,
explicit requirement**: on the API and website, this internal chunking (one module = two error
streams, its own + its ConfigManager's) **must be hidden — each module must fold both into its own
status presentation consistently**, not as a per-module bespoke display. Checked against what
already exists: `SPECIFICATION.md` H.6's `/status` `errcount` convention (`{key, label}` per
registered module **plus** each module's own `CFGMGR_<name>` entry, generic and uniform across
every module today) already *is* this consistent, uniform pattern — so the requirement is to
**preserve** that existing uniformity as WiFi/NTP/Webserver/UART_Comm are added to the FRAM-wiring
scheme (Topics 2/5), not invent a new display convention per module. Worth a dedicated test
asserting this uniformity holds (see to-do below) rather than trusting it by inspection alone.

**Documentation — to be adapted, not just re-worded (owner's point 6):** the F.2 invariant in
`SPECIFICATION.md` (*"every real `ConfigManager.write_config()` call is reachable only through the
REST PUT path, so a device whose API is unreachable structurally cannot have a flash write in
flight"*) must be rewritten to state the new reality precisely: a flash write is now reachable only
through a REST PUT that has **already been accepted and whose connection has already closed** —
still true that an unreachable API cannot have a *new* write triggered, but now also true that a
**staged-but-not-yet-executed** write can exist very briefly after the response was sent and before
the connection-close trigger fires. The WiFi-power-cycle-recovery argument still holds (a device
whose API is unreachable can't accept a *new* PUT to begin with), but the "zero flash-corruption
risk" framing should explicitly note the accepted residual-risk window from above rather than imply
zero risk unconditionally.

### TO-DO
- [ ] `asy_webserver_service.py`'s `_put_sensors()`/`_serve()`: after the response is built (still
      based on validation only, unchanged), defer the actual `write_config()` call(s) to run
      **after** `_close_writer()` completes for that connection (no separate task queue — one
      fire-and-forget call per closed connection that had a staged write is sufficient, since at
      most one staged value can exist per sensor at a time by API design).
- [ ] `config_manager.py`: add a per-`ConfigManager` staging slot (single pending dict, not a
      queue) holding the validated-but-not-yet-written data between "response sent" and "write
      executes." No locking/coalescing logic needed beyond what `config_lock` already provides.
- [ ] `config_manager.py`'s read path (`get_dict()`/`_get_values()`): consult the staging slot
      first, fall back to `_cache` — implements the decided `GET` read-your-write semantics.
      Clear the staging slot once the deferred write actually completes (success *or* failure —
      either way there's nothing left to "stage").
- [ ] Review `write_config()`'s exception handling, its `errno=14` call and its "`_cache` only
      committed after success" contract against the decided behavior, and change what needs it.
- [ ] Review `api_response.py`/`WriteValidity` and decide whether any new state is needed.
- [ ] Update `SPECIFICATION.md`'s F.2 invariant text per the "documentation" paragraph above; also
      update `SPECIFICATION.md`/`CLAUDE.md` wherever the old "write is always synchronous within
      the request" assumption is stated elsewhere (a repo-wide grep for the current invariant
      wording is needed before editing — not yet done this session).
- [ ] Add a test explicitly asserting the `/status` errcount presentation stays uniform across every
      module once WiFi/NTP/Webserver/UART_Comm join the FRAM-wiring scheme (Topics 2/5) — i.e. no
      module special-cases how its own entry vs. its `CFGMGR_<name>` entry is shown, confirming
      owner's point 7's "must fold this in consistently" requirement holds structurally, not just
      by inspection.
- [ ] Full test coverage for the new deferred-write behavior itself: normal flow (staged → written,
      GET reflects staged then written value at the right times), error handling (deferred write
      fails → errno recorded in the right place, RAM or FRAM depending on Topic 3's wiring for that
      module, `_cache` stays unchanged exactly as today), the accepted residual-risk case (a
      simulated "device restarts between response and deferred write" scenario — confirm it's
      silent/lossy exactly as accepted, not silently *wrong* in some other way), and regression
      against every existing `write_config()`/`_set_dict_cfg()` test (the deferred trigger must not
      change any currently-tested synchronous-path behavior for a single, uncontended PUT outside
      the specific concurrent-load scenario this whole fix targets).
- [ ] Re-verify the final implementation against `CLAUDE.md`'s F.3 rule and the (now-updated)
      WiFi-power-cycle-recovery invariant explicitly, once code is written — not just at the design
      stage.

---

## TOPIC 2 — FRAM logging: WiFi, NTP, Webserver made implicit-if-FRAM-present

### DECISION: Implement, per user's explicit plan. FRAM-chunk-reorder risk explicitly accepted as zero (no deployed devices).
### TO-DO
- [ ] `buildgen/codegen.py`: extend `_fram_kw()`/device-wiring pattern (currently only feeds
      `sysfunct`) to also cover `conn`, `ntp`, `webserver`.
- [ ] Reorder `build_system()`'s construction so `fram` is built before `conn`/`ntp` (move step 6
      ahead of steps 2-3, and step 5's SPI bus ahead too since `fram` needs it) — accepted as safe.
- [ ] `buildgen/validate.py`: extend `_DEVICE_WIRING_CONSUMERS` to include `conn`/`ntp`/`webserver`
      alongside `sysfunct`.
- [ ] Add `fram=` wiring to the `webserver = WebserverService(...)` emission (`codegen.py:547`) —
      no ordering change needed for this one.
- [ ] Update `SPECIFICATION.md`'s documented construction order and "seven-chunk order" note once
      the real order changes (currently: SystemService → SCD30 → SGP40 error log → SGP40 VOC
      backup → BMP3xx → Neopixel → NotificationCoordinator — this list grows/reorders).
- [ ] Unit + digital-twin + (where applicable) hardware tests for: FRAM-present → conn/ntp/webserver
      inherit it; no-FRAM-chip device → all three stay RAM-only (regression-proofing the fallback
      path, not just the happy path).

---

## TOPIC 3 — FRAM logging: `ConfigManager` inherits from its owning module

### DECISION: Implement, per user's explicit plan ("ConfigManager gets optional FRAM-Logging right from the start if the module using this ConfigManager instance has FRAM").
### TO-DO
- [ ] Add `fram: "AsyFramManager | None" = None` param to `ConfigManager.__init__`
      (`config_manager.py`), with `if TYPE_CHECKING: from asy_fram_manager import AsyFramManager`
      guarding the type-only import (mirror `base_classes.py:25`'s exact pattern).
- [ ] Change `config_manager.py`'s import line to pull in `make_logger` (real import, safe) instead
      of constructing `PrintLogHistory` directly; call `self.pr = make_logger(fram,
      history_length, debug, name="CFGMGR_" + name)`.
- [ ] Fix `SensorReaderConfig.__init__` (`base_classes.py:281-285`) to pass its own `fram` through
      into the `ConfigManager(...)` call.
- [ ] Decide whether any new errno/wrnno is needed; the intent is that none is.
- [ ] Unit tests: (a) a `SensorReaderConfig`-based module built with `fram=<manager>` → its
      `.cfgmgr.pr` is FRAM-backed (`PrintLogHistoryStore`), and a real write-failure errno actually
      persists across a simulated reboot/restore cycle; (b) built with `fram=None` → stays RAM-only,
      regression-proofing today's default behavior; (c) confirm `/status`'s `CFGMGR_<name>` entry
      reflects the persisted history correctly in the FRAM-backed case (no API-layer change should
      be needed — this is a check that the existing generic wiring picks it up automatically).

---

## TOPIC 4 — Other modules affected by the same "FRAM-capable but never wired" pattern?

### DECISION: no other modules to change beyond Topics 2, 3 and 5.

The set of gaps this session set out to close is those three; nothing further was added to
scope here.

## TOPIC 5 — UART_Comm: full optional FRAM support (was wrongly, deliberately blocked)

### DECISION: Implement fully — both direct-wire and inherit-from-upstream options, per original (mis-executed) instruction. Full 4-tier test coverage required.
### TO-DO
- [ ] Remove the incorrect "no fram=" decision + comment in `asy_uart_link_driver.py:58`.
- [ ] Remove the matching incorrect comment/behavior in `buildgen/codegen.py:220-225`
      (`_build_args_uart_link`).
- [ ] Wire `UartLinkExerciser.__init__` to accept `fram=`/`logger=` params and forward one or the
      other into its own `UART_Comm(...)` construction (class-level support already exists, no
      change needed in `asy_uart_comm.py` itself).
- [ ] Add a `# @wiring fram_target ...` tag to the UART link driver's own source so `buildgen` can
      resolve a per-instance `fram_target` from a device TOML, same mechanism as every other
      per-instance driver.
- [ ] Wire it into `devices/dev.toml` (the only device with real UART instances — `dev` carries two
      crossover-jumpered instances per `CLAUDE.md`'s UART hard rule; `wozi` carries none).
- [ ] **Full test coverage across all four tiers**, per the standing bus-hazard rule already in
      `CLAUDE.md` (this rule already applied to UART regardless of this specific fix — it was just
      never fully satisfied for the FRAM path):
  - [ ] `tests/` (mock) — normal flow (chunk allocated correctly, errno history persists through a
        simulated FRAM read/write), error handling (allocation failure falls back to RAM-only
        without crashing construction), self-healing/resilience, regression against the old
        RAM-only default behavior (must still work with no `fram=`/`logger=` passed).
  - [ ] `tests/test_digital_twin_*` (digital twin) — construct the real generated `dev` device
        module against the twin's fake FRAM chip and assert UART_Comm's own errno history survives
        a simulated reboot of the twin.
  - [ ] `tests_hardware/flash/` — real hardware, raw driver level.
  - [ ] `tests_hardware/bench/` — real hardware, full HTTP/API stack, confirming the UART_Comm
        error log surfaces correctly through `/status` end-to-end.

---

## TOPIC 6 — FRAM allocation-capacity verification

### FINAL DECISION (user's own proposal, adopted): no errno/wrnno, no async change at all
- **Premise the design rests on — re-verify it before building on it**: that
  `AsyFramManager.allocated_size` only ever grows during construction and never after, per the
  "FRAM chunk determinism rule (no deallocation exists by design)" (`SPECIFICATION.md:199`). If
  that holds, "does everything fit" is a single fact, fully determined once `build_system()`'s
  construction phase finishes and true for the rest of that build's life — and there is no
  "arbitrary point during live operation" case to catch.
- Therefore: **leave `get_chunk()`/`get_timestamped_chunk()` and `FRAM_SPI`'s bare `.err()`/`.wrn()`
  calls exactly as they are** — sync, unchanged, harmless as incidental live-debug console output.
  They are no longer the enforcement mechanism.
- **The actual enforcement mechanism**: a single, 100%-deterministic post-construction check —
  after `build_system()` finishes, assert every module holding a chunk actually got one (its
  `self.fram`/`self.ts_storage` attribute is not `None`), equivalently `fram.allocated_size <=
  fram.size`. Both tiers below must run the *real* construction code, not a re-derived
  approximation of it:
  - **Digital twin**: `digital_twin/run_generic_integration.py` already calls the real
    `build_system()` against `digital_twin/_fram_chip.py`'s fake SPI chip — a twin test just needs
    to call it and check `fram.allocated_size` afterward. No new fakes/mechanism needed.
  - **Real hardware**: same assertion, read directly off the live device's `fram` object
    attributes via the existing `mpremote`-based `tests_hardware/flash/` harness. **Decided this
    round: option (a), mpremote-only — no new `/status` field.** Owner's explicit reasoning: keep
    the footprint of all these changes minimal; this doesn't need forwarding to the API since it's
    a one-time, build-deterministic build-validity fact, not an operational status a live client
    needs to query.

### DECISION: Adopted.
### TO-DO
- [ ] Leave `asy_fram_manager.py`'s `get_chunk()`/`get_timestamped_chunk()` and `asy_fram_driver.py`
      (`FRAM_SPI`)'s bare `.err()`/`.wrn()` calls unchanged — no code change needed here at all
      beyond the test additions below.
- [ ] Digital twin: add a test that runs the real `build_system()` for **every** real device TOML
      (not just wozi/dev) and asserts `fram.allocated_size <= fram.size` (equivalently: no
      FRAM-chunk-holding module ended up with a `None` chunk reference) immediately after
      construction.
- [ ] Real hardware: add the equivalent check to `tests_hardware/flash/`, reading
      `fram.allocated_size`/`.size` directly off the live device via `mpremote` — **decided:
      mpremote-only, no `/status`/API field** (keeps this change's footprint minimal, per owner's
      explicit direction this round).
- [ ] Confirm/derive this check for every currently-defined real device TOML
      (`devices/*.toml`), not just the two most-tested ones.

---

## TOPIC 7 — errno/wrnno range audit

### DECISION: Not doing a full-scale audit. Closed, no action.
User explicitly declined a full audit across every module ("No need to do a full scale errno /
wrnno audit here"), accepting the reservation scheme as a documentation convention "as long as it
is actually being obeyed." No further verification requested or planned.

---

## TOPIC 8 — Standing/general decision: test coverage scheme for all of the above

### DECISION: applicable, not new scope.
All of Topics 2/3/5/6 (anything bus-facing — FRAM is the SPI device underneath nearly everything;
UART is directly bus-facing) fall under the **existing** four-tier bus-hazard scheme already
established as a standing rule in `CLAUDE.md` (originally written for I2C/SPI bus-hazard testing,
but the user's own framing here — "higher tiers include all lower tiers, digital twin and real
hardware synchronicity" — is exactly that same `bench ⊇ flash` convention, generically applicable):
1. Mock (`tests/test_*.py`, real MicroPython Unix-port interpreter, no hardware).
2. Digital twin (`tests/test_digital_twin_*.py`, real generated `build_system()` against
   `digital_twin/`'s fake peripherals).
3. `tests_hardware/flash/` — real hardware, raw driver level (needs project owner's real-hardware
   go-ahead for this session, not yet obtained).
4. `tests_hardware/bench/` — real hardware, full HTTP/API stack (same go-ahead requirement).

For each of Topics 2, 3, 5, 6: tests must cover **normal flow, full error handling/self-healing/
resilience, "biting" edge-case coverage, and regression** (explicit user requirement) — not just a
happy-path smoke test — at whichever of the four tiers actually apply to that specific change
(Topic 6's check, for instance, has no natural "mock" tier equivalent since it's inherently a
whole-build-system construction check; Topics 2/3's FRAM-forwarding fixes are testable at the mock
tier directly since `ConfigManager`/`SensorReaderConfig` construction doesn't require real/fake
hardware at all).

**No real-hardware work (tiers 3/4 above) may be executed in any session without the project
owner's go-ahead given directly in that session's own conversation** (standing `CLAUDE.md` rule,
unrelated to this session specifically) — this has NOT been granted in this session; all
`tests_hardware/`-tier work above is planning only until a session has that go-ahead.
## TOPIC 9 — Boot-time watchdog feeding and setup-call pacing

### DECISION: feed the watchdog after every one-time `setup()` call; carry the watchdog as an optional, no-op-defaulting dependency.

Owner's reasoning, recorded because it is the requirement rather than a preference:

- **A one-time delay at boot is acceptable.** The device runs for months and is barely ever
  rebooted in real use, and an API unreachable for a few seconds after a reboot is what almost
  every networked device does. Boot latency is explicitly *not* a thing to optimise for its own
  sake.
- **Watchdog starvation during that window is the real risk**, and it is what the fix targets.
- **Why feeding there is safe**: these `setup()` calls run once, at boot, outside any loop. A feed
  in that position can never accidentally keep feeding a hung system forever — the property that
  makes it acceptable. Any future refactor that moves this code into a loop breaks that argument
  and must be rejected.
- **No-watchdog builds must be handled generally, not special-cased.** The owner's own proposal:
  `SystemService` takes the watchdog instance as an argument; absent, feeding degrades to a no-op.

**Superseded along the way, recorded so it is not re-proposed:** an earlier idea was to pace the
`setup()` calls with `await asyncio.sleep()` between them, mirroring the task starters. That was
replaced by Topic 10's decision — the setup calls get their **own separate list** with no stagger
obligation at all. Do not reintroduce a delay between setup calls.

### TO-DO
See WP6 above for the full action list.

---

## TOPIC 10 — Sensor read-timer architecture (existing design, to be preserved and documented)

### DECISION: the existing timing scheme stands. Verify it, document it, and do not rescale it.

This is background the owner supplied directly. It is the design intent behind code that already
exists — treat it as the specification, and check the code against it rather than the reverse.

- Sensor read periods are settable in **whole multiples of one second, minimum one second**.
- The read-trigger timers are staggered **evenly across one second in total** — deliberately a
  total spread, not a fixed per-timer gap. For N timers this yields the maximum achievable mutual
  spacing at the shortest selectable period.
- They are **system timers**, so they **do not drift relative to each other** once armed; their
  phase relationship holds for the entire runtime.
- Therefore **no two sensor reads ever coincide**, for any combination of configured periods, for
  the whole runtime. That is the property the design exists to guarantee: no harmonics, no beats,
  no races from period overlay.
- The timer starters are themselves triggered by **another real timer** — precise, interrupt and
  callback driven — rather than by `asyncio.sleep()`, whose timing is only coarse. This is
  deliberate and is part of the same guarantee.

**Standing constraints this places on all future work:**
- The one-second **total** spread must not become a fixed per-task gap, and must not be rescaled.
- One-time boot `setup()` calls belong to a **separate list** (Topic 9) and must never be folded
  back into this mechanism.
- Verification is against the pinned MicroPython rp2 source and current port docs, per CLAUDE.md's
  standing "don't rely on training memory" rule.

### TO-DO
See WP7 above for the full action list.
## TOPIC 11 — Cross-cutting requirements carried from the decision rounds

These were stated by the owner across the decision messages but do not belong to a single work
package. They are requirements, not suggestions.

### `self.pr.err()` → `err_s()`, wired through to API and website
The bare synchronous print-only `err()` is to be upgraded to the recording `err_s()` form and wired
through to the API and the website, so the failure actually shows up rather than only printing.
Owner's words: "Needs to be updated and wired up through the API to the website with all unit tests
(full normal flow, full error handling / self-healing / resilience, biting coverage, regression) to
be added."

- [ ] Determine which call sites this applies to — the earlier list was produced by this session's
      own analysis and is **not** carried forward; re-establish it from the code.
- [ ] Wire the recorded errors through to the API/status and the website.
- [ ] Full test set per the owner's wording above.

### errno/wrnno conflicts are realigned project-wide, not worked around
If a change introduces errno/wrnno values that conflict with conventions already in use elsewhere,
**the conflicting existing values are adapted across the whole project**, and every usage — the unit
tests explicitly included — is aligned with them. Reservation lives in the base classes and is not
mutable by individual modules.

- [ ] Before adding any code, check for a conflict.
- [ ] If one exists, realign project-wide including all test usages, rather than picking a free
      number to dodge it.

### WiFi, NTP and the webserver are implicitly mandatory in every build
Owner's framing: all three are mandatory modules of every build. They take FRAM logging implicitly
whenever the TOML declares a FRAM chip, exactly as the already-wired modules do, and fall back to
RAM logging when no FRAM chip is present. `buildgen` is adapted to enforce this rather than each
device's TOML restating it.

- [ ] Treat this as a build-level invariant, not a per-device option.

### Superseded: "prioritize existing connections over new ones"
Recorded so it is not re-proposed. The owner's first instinct on the connection-reset defect was to
refuse new incoming connections while an established one is awaiting its response, prioritising
existing connections over new ones. This was **not** the design ultimately chosen — Topic 1's
respond-then-persist is, on the owner's own later reasoning that the write is atomic per module by
API design and so the simplest possible trigger suffices. Keep it as context for why the simpler
design was preferred, not as an open option.

---


---


---

## Overall status summary (one line per topic)

| # | Topic | Status |
|---|---|---|
| 1 | PUT /sensors connection reset — fix approach | **Decided — respond-then-persist; no owner decisions remain** |
| 2 | WiFi/NTP/Webserver implicit FRAM wiring | Decided — implement |
| 3 | ConfigManager inherits FRAM from owner | Decided — implement, no new errno; **also a precondition for Topic 1's error durability** |
| 4 | Other modules affected? | Closed — scope limited to Topics 2/3/5 |
| 5 | UART_Comm full FRAM support | Decided — implement |
| 6 | FRAM capacity verification | Decided — deterministic post-build check, no errno/async; real-hardware tier explicitly settled as **mpremote-only, no new `/status` field** (owner's point 2 this round: "keep footprint minimal... handle via mpremote") |
| 7 | errno/wrnno audit | Closed — not doing it |
| 8 | Test coverage scheme | Existing 4-tier standing rule applies to 2/3/5/6, and to Topic 1's new deferred-write behavior |
| 9 | Boot-time watchdog feeding | Decided — feed after every one-time `setup()`; watchdog optional, no-op default |
| 10 | Sensor read-timer architecture | Existing design stands — verify against real source, document, do not rescale |
| 11 | Cross-cutting requirements | `err_s()` upgrade + API/website wiring; project-wide errno realignment; mandatory-module invariant |

**Every open decision from earlier rounds is now resolved.** Nothing beyond the Topic-1 BACKLOG.md
commit (`3f7cc25`) has been implemented. Topics 9 and 10 were settled *after* this checklist was
first written and have no ordering dependency on the rest; Topic 10 is mostly verification and
documentation of an existing design. Recommended implementation order, given that Topic 1's error
durability depends on Topic 3: **Topic 3 (and, alongside it, Topic 2 since both touch the same FRAM-forwarding machinery)
before Topic 1**, so Topic 1's deferred-write errors land durably from day one rather than needing
a second pass once Topic 3 lands later. Topics 5 and 6 have no ordering dependency on the
others and can be done at any point.

---

# Part 4 — Resulting repository state

Written after the fact. Everything above is the *input*; this is where the repository actually
stands now.

## Outcome

WP1-WP4 were implemented; WP5, the original `PUT /sensors` fix, was never started. A fifth branch
consolidated the four. **All of it has been rolled back.** The reference branch
`claude/automated-build-chain-nuzumw` was reset to `25e0e19` (Merge PR #92) — the last commit
before any WP work — and verified byte-identical to its pre-WP state.

- PRs #93 and #94 had already been merged into the reference branch; the reset removed their
  commits, so they still *read* as merged although their content is gone.
- PRs #95, #96, #97 were commented and closed.
- Removed from the branch: 16 code files and 3 markdown files, 639 insertions.

Nothing is lost. Every branch tip is preserved on the remote:

| backup branch | tip |
| --- | --- |
| `backup/2026-09-16/trunk-before-reset` | `f55fa66` |
| `backup/2026-09-16/wp1` | `6012036` |
| `backup/2026-09-16/wp2` | `4c5b420` |
| `backup/2026-09-16/wp3` | `44a7a5b` |
| `backup/2026-09-16/wp4` | `be2ad92` |
| `backup/2026-09-16/wp-watchdog` | `8223df3` |
| `backup/2026-09-16/wp-integration` | `1bfd631` |

The six original WP branches still exist on the remote — this session's git transport allowed
branch creation and force-update but refused ref *deletion*, so deleting them is a manual step.

## Process note

The work packages and the decisions behind them are the owner's, and stand. What failed was the
way the work was carried out: it was never held against a clear whole picture, and oscillated around
its goals instead of converging on them. Carry the packages forward; do the work in one place, in
one order, with the full picture held throughout.

## Starting point for the fresh session

- Branch `claude/automated-build-chain-nuzumw` at `25e0e19`, clean, equals its pre-WP state.
- Part 3's five work packages are unstarted. WP5 (the original `PUT /sensors` connection-reset fix,
  the finding that began the session) was never begun and is the only item with a fully settled
  design already in hand — see Topic 1's "FINAL DESIGN" section.
- `BACKLOG.md`'s entry for the original finding was committed before implementation began and
  survives the rollback.

---

# Part 5 — Background knowledge to persist once implemented and verified

**Standing requirement from the project owner.** The explanations in this document are currently
held only here, in a temporary file that is meant to be deleted. Several of them are design intent
that existing code already depends on, and losing them is how a later session erodes a guarantee by
accident.

So: **once the new session has implemented and verified the work, the background knowledge below
moves into the permanent documentation** — `SPECIFICATION.md` for anything architectural and reused
elsewhere, `CLAUDE.md` for anything that is a standing rule or operating constraint for future
sessions. This is part of the work, not an optional follow-up, and it happens *after* verification
so that what gets written down is what was actually confirmed — not what was merely intended.

CLAUDE.md's own rule applies to how it is written: a short pointer in the code's header block, the
substance in the relevant `SPECIFICATION.md` Part. Do not paste these paragraphs into source
comments.

### What must be persisted, and roughly where

1. **Sensor read-timer architecture** → `SPECIFICATION.md`, alongside the existing Part F timer
   facts. The full chain of reasoning: one-second minimum period in whole-second multiples → even
   stagger across one second *total* (not a per-timer gap) → system timers hold their phase with no
   relative drift → therefore no two reads ever coincide for any period combination, for the whole
   runtime. Include *why* a real timer rather than `asyncio.sleep()` drives the starters. State the
   total-spread rule as load-bearing, so a future reader does not "simplify" it into a fixed
   interval.
2. **Boot-time `setup()` calls are a separate list** → same place, as the counterpart rule: they
   carry no stagger obligation, must not be folded into the read-timer mechanism, and must not have
   a delay inserted between them.
3. **Why feeding the watchdog in the setup batch is safe** → `SPECIFICATION.md` Part F near the WDT
   facts: it is one-time and boot-only, outside any loop, so it cannot keep feeding a hung system.
   Record the constraint that follows — moving that code into a loop invalidates the argument.
4. **Boot latency is explicitly not a metric to optimise** → `CLAUDE.md`, as an operating
   constraint. Rare reboots; brief post-reboot API unavailability is normal and accepted. This
   stops a future session from "fixing" a boot delay that nobody considers a defect.
5. **The no-watchdog build is a first-class case** → wherever the watchdog dependency ends up being
   documented: handled by an optional dependency defaulting to a no-op, not by conditionals at call
   sites.
6. **FRAM logging is optional for every module except the FRAM module itself** → `SPECIFICATION.md`
   with the FRAM/logging architecture, including the reason: logging a FRAM fault into that same
   FRAM is pointless. Also record which modules are implicitly wired when a TOML declares a FRAM
   chip, and that `ConfigManager` inherits its owner's FRAM.
7. **The deferred-write persistence contract** → `SPECIFICATION.md` Part A.5/F.2 as the topics
   settle: `"Valid"` means validated, persistence is signalled by the absence of an errno against
   that write, `GET` returns the staged value before the write lands and the written value after,
   and the API envelope is unchanged. Update every existing place that still states or implies a
   config write is synchronous within the request.
8. **The accepted residual risk** → alongside it: power loss between "response sent" and "write
   attempted" loses the change with no trace, accepted as no worse than the status quo.
9. **FRAM capacity is verified after the build, not at runtime** → with the FRAM documentation:
   allocation is deterministic and fixed once a build is done, so a post-construction check is
   sufficient; no errno, no runtime machinery, failures handled via `mpremote`.
10. **errno/wrnno ranges are reserved in the base classes and not mutable by modules** →
    `SPECIFICATION.md` where the numbering convention lives, noting it is a convention the code
    does not enforce.

### The rule this is meant to establish

Any future work that touches a guarantee recorded above must state which guarantee it touches and
show it still holds. That is only possible if the reasoning — not just the rule — is written down,
which is the whole point of persisting it rather than leaving it in a deleted scratch file.
