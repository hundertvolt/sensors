# src/ Audit — Master Action List

Working document for the full `src/` audit (see BACKLOG.md's "Planned: full `src/` audit" for the
original goals/lenses this expands on). **Temporary**: this file is deleted once the project owner
agrees the audit is finished — it is not meant to persist the way CLAUDE.md/README.md/
`SPECIFICATION.md` do. Anything here that turns out to be a permanent fact worth keeping migrates
into those docs before this file goes away, matching BACKLOG.md's own "resolved items get pruned,
not left to rot" rule. (`DRIVER_SPEC.md` is now a stub pointing into `SPECIFICATION.md` — see a
later doc-scatter-cleanup pass, folded in mid-audit-planning.)

This file is written to be self-contained: everything decided during the pre-audit planning
conversation is captured here directly, not referenced back to that conversation.

Companion file: `WIRING_CONTRACT.md` (also temporary) — the `improved-quality/sensortask-wozi.py`
instantiation-order/dependency study. Seeded now with what's already been found; the deep study
happens at Cluster 10.

## Validation pipeline (BACKLOG.md steps 4-10 — each tracked explicitly, none marked done by another item's side effects)

BACKLOG.md's kickoff procedure requires each of these as its own genuine pass. Earlier drafts of
this document treated steps 5/6/8 as satisfied incidentally by other work — that was wrong; nothing
below counts as done until it has actually been executed as its own dedicated activity, and each
item's own "done" note says what was actually checked, not just that related work happened nearby.

1. `[x]` **Steps 1-3** — goals/lenses read, full doc set read, every real `src/` file (plus
   `sensortask-wozi.py`) read in full, not grepped. Confirmed complete earlier this session.
2. `[x]` **Steps 4+7+8 combined** ("detailed action list" + "goal per step" + "quality measure per
   step") — this document is the action list; every cluster now has a Goal; **every cluster (0-10)
   now has an explicit Quality measure line** (Clusters 0-1 already had one; 2-10 got theirs added
   in this pass, not assumed complete just because a Goal existed).
3. `[x]` **Step 5, first half — completeness/unambiguity/consistency check of the list itself** — a
   dedicated read checking the document is internally complete and unambiguous on its own terms, not
   whether it matches the code (that's item 4). See "Completeness/consistency check log" below.
4. `[x]` **Step 9 — full reality check, done in one consolidated pass** — every cluster's claims
   re-verified against the actual files in one sweep, not scattered across incidental finds. See
   "Reality-check log" below.
5. `[x]` **Step 5, second half — second, global-perspective convergence pass** — one more full
   top-to-bottom pass, done only after 3-4 were clear, making the whole document internally
   consistent and stable. See "Convergence pass log" below.
6. `[x]` **Backward-direction (bottom-to-top) contradiction check, understanding-only** — confirm
   the document's *stated facts* (not sequenced actions) hold regardless of which direction they're
   read in. Real action ordering (cluster execution order, dependency order) is expected to only
   make sense forwards — this check is specifically about non-order-dependent claims (a fact stated
   in Cluster 9 must not contradict a fact stated in Cluster 2, independent of reading order). See
   "Backward-read check log" below.
7. `[x]` **Step 6 — external reference material identified per step** — folded into item 2's
   per-cluster edits (each cluster now names its external references, or states none apply) rather
   than tracked as a separate pass.
8. `[x]` **Step 10 — owner discussion/feedback checkpoint.** Closed: with items 2-7 all clear, the
   session confirmed it has no outstanding open decisions and no `[?]`-blocked clusters — the
   project owner reviewed and confirmed this in session, and in the same discussion resolved the
   `Timer.init()`/`MemoryError` item (defensive `except (OSError, MemoryError)` widening across
   Clusters 7-9, regardless of the separate one-time MicroPython-source verification carried into
   Cluster 10 — see the Open decisions log). The plan is validated and ready; Cluster 0 execution
   starts as its own follow-up work.

## Status legend

`[ ]` not started · `[~]` in progress · `[x]` done · `[?]` blocked on an owner decision (see
"Open decisions" at the bottom of that cluster's section)

---

## Definition of Done (whole audit)

The audit is finished when, for every file in `src/`:

1. It conforms to the eventual consolidated style guideline (Cluster 10's harmonization pass over
   `SPECIFICATION.md`'s Parts C/D — see Cluster 10; a doc-scatter cleanup already moved
   `DRIVER_SPEC.md`'s and `src/README.md`'s content there verbatim/unaudited, so Cluster 10 now
   edits those Parts in place against real per-file findings rather than producing a new merged
   document). Until that harmonization pass runs, "done" means passing `SPECIFICATION.md` Part D's
   full 16-section checklist (`src/README.md`'s former content) plus every convention fixed in
   this document.
2. The project-wide dependency graph stays a clean DAG — no import cycles, verified, not assumed.
3. Cross-file API shapes (setter/getter contracts, config-schema conventions, the logging/naming
   scheme below, error-code conventions) are consistent enough that building the real, standalone
   `sensortask-wozi.py` successor (stage 1 of the two-stage wiring plan — see "Wiring, two-stage"
   below) is mechanical, not a redesign. Actually building it is out of this audit's scope; making
   it *easy* to build is not.
4. Every class has logging that's either complete or deliberately, explicitly exempted (see
   "Logging & naming scheme" below) — never silently absent.
5. `errno`/`wrnno` numbering is internally consistent per module and drawn from a shared,
   documented convention across modules where that's sensible (see "Error-code convention" below).
6. Every FRAM-chunk-owning object satisfies the determinism rule below.
7. `lint.sh`/`typecheck.sh`/`test.sh` all green; no test dropped (only extended/adapted); coverage
   recorded before/after and never silently regressed.

---

## Standing conventions (decided during pre-audit planning — apply throughout, don't re-litigate)

### Logging & naming scheme

- `PrintLog.__init__` gains `name: str = ""` (**not** a bare required parameter — see Cluster 1's
  own section for why: a required `name` would break every other file's existing positional
  `PrintLogHistory(...)`/`PrintLogHistoryStore(...)` construction the instant Cluster 1 lands),
  auto-prepended inside `err`/`wrn`/`one`/`evt`/`all`/`err_s`/`wrn_s`. `get_log()` keeps a
  **transitional backward-compatible** `name: str | None = None` override — it does **not** drop
  its argument outright, since 8 external callers still pass one explicitly today and dropping it
  would break all 8 immediately; `None` falls back to `self.name`, an explicit value still works as
  today. `get_log()` always returns the exact same `{name: {...}}` dict shape every existing caller
  already depends on (hard compatibility constraint — e.g. `sensortask-wozi.py`'s
  `fram_err_log["FRAM"]["ErrCount"]` must keep working unchanged). Each of the 8 callers drops its
  now-redundant explicit `get_log(...)` argument as part of *its own* cluster, not Cluster 1's.
- `base_classes.py`'s `SensorReader.__init__` gains `name: str = ""` (currently missing entirely —
  only `SensorReaderConfig` has it, and only for the config filename; defaults for the same
  blast-radius reason as `PrintLog` above — see Cluster 3) and an optional
  `logger: PrintLog | None = None` reach-through parameter, mirroring the pattern already
  precedented by `asy_fram_driver.py`'s `FRAM_SPI(..., logger: PrintLog)` receiving
  `asy_fram_manager.py`'s own `self.pr`. `None` → builds its own named `PrintLogHistory`/
  `PrintLogHistoryStore` as today; given → reuses the passed instance (for directly-bound sibling
  objects sharing one identity).
- `_error_check(results, name, condition=True)` (`base_classes.py`) — drop the now-redundant `name`
  parameter once every call site's `self.pr` carries its own name; strip the manual `_NAME`
  argument from every `self._error_check(results, _NAME)` call site. Confirm true redundancy (no
  call site needs a *different* name than its own `self.pr`) before dropping — expected to hold,
  verify while in that file.
- Strip the manual `_NAME`/`name` first argument from every `err_s`/`wrn_s`/`evt`/`one`/`all`/
  `get_log()` call site project-wide once the name lives on the instance (~150+ call sites across
  every file that already does this correctly today, plus the ones below that don't yet).
- **FRAM**: `asy_fram_manager.py` (`AsyFramManager`) and `asy_fram_driver.py` (`FRAM_SPI`) already
  share one `PrintLog` instance (`logger=` constructor injection, pre-existing pattern). One shared
  name is sufficient: `"FRAM"`. (`FRAM_SPI` itself has no `errno`/`wrnno` usage today — only two
  informational `evt`/`one` calls — so there's no numbering overlap to separate.)
- **Bus layer** (`asy_i2c_driver.py`/`asy_spi_driver.py`) — **reverted**, no logging added here.
  Verified against `SPECIFICATION.md` Part C.3 ("layer 2... raises on any real failure — this is the
  layer that does *not* return sentinels") and C.7 ("a per-field get/set forward... always
  logs on failure") — the current, authoritative location of this content (`DRIVER_SPEC.md` is now
  a stub pointing there, kept only so old links resolve): every real bus fault already surfaces to
  and gets logged by exactly one upstream owner (the `*_Reader`). Adding bus-layer logging would
  duplicate the same event under a second tag with no new information. Cluster 4's real work is the
  inverse of what was originally planned: **verify** every current `I2CDevice`/`SPIDevice` call site
  is genuinely wrapped by an upstream `try/except` (per `SPECIFICATION.md` D.2's own standing
  instruction for this exact carve-out — "verify, don't assume, that every upstream caller closes
  the gap"; `src/README.md` is likewise now a stub pointing there), and fix the *caller* if a gap is
  found — never add logging to the bus layer itself.
- **`asy_udp_socket.py`/`asy_dns_client.py`** — same reverted treatment as the bus layer, same
  reason (`asy_udp_socket.py`'s own module docstring: "every I/O method returns its documented
  None-shaped sentinel, never raises" — confirmed by reading the file; every failure already
  degrades to a caller-visible sentinel). No logging added. Verify every real caller
  (`asy_ntp_client.py`, `asy_dns_client.py` itself for `AsyUDPSocket`; `asy_ntp_client.py` for
  `resolve_ipv4()`) already fully logs on a `None`/failure result. This check spans two clusters
  (5 and 8) and can't be closed from either alone.
- **`captive_dns.py`'s `DNSServer`** — gets its own logger, own name (proposed `"DNSSRV"`, open to
  correction when the file is actually touched). Verified safe: `DNSServer` is constructed exactly
  once, inside `asy_conn_time.__init__` (`src/asy_wifi_service.py:106`), which is itself only ever
  instantiated once at module level in `sensortask-wozi.py` — satisfies the FRAM determinism rule
  below if a FRAM-backed logger is ever wanted here.
- **`config_manager.py`** — gets its own name per instance, derived from its owner
  (`"CFGMGR_" + name`, e.g. `"CFGMGR_SGP40"`), not one shared literal `"CFGMGR"` (which would make
  every config file's logs indistinguishable from each other). Currently reuses its owner's `self.pr`
  directly and never calls `err_s`/`wrn_s` at all (only `one`/`all`/`evt`) — this changes: gains its
  own real error/warning logging (own `errno`/`wrnno` list), and the *owner* additionally logs its
  own line whenever it accesses the config manager, so the two lines cross-reference for a human (or
  future rsyslog) reader.
- **Networking group, future API note (not acted on now)**: `captive_dns.py` (own logger, above)
  and, once built, the future Microdot connection-timeout wrapper (`asy_webserver_service.py` —
  BACKLOG's "Microdot hardening design," doesn't exist in `src/` yet) will both surface under a
  future single "Networking" REST endpoint, one JSON field per component. Carry into
  `WIRING_CONTRACT.md` when that endpoint design actually happens — out of this audit's scope.
- **Bus-instance API note (not acted on now)**: each I2C/SPI bus instance gets its own name (e.g.
  `"I2C0"`/`"I2C1"`/`"SPI0"`, matching `sensortask-wozi.py`'s `i2c0`/`i2c1`/`spi0`). Once the REST
  API is designed, these become one endpoint with one field per bus. Carry into
  `WIRING_CONTRACT.md` — out of this audit's scope.
- **Logging coverage, general rule**: add or complete logging wherever a class doesn't already have
  it, *unless* sensibly exempt. Confirmed exempt (pure computation/primitives, no meaningful error
  to report): `math_helpers.py`, `crc_checks.py`, `voc_algorithm.py`, and `base_classes.py`'s
  `Lockable`/`LockableBuffer`/`LockedCounter`/`LockedFlag`/`LockedValue`. **Important**: before
  adding logging to any currently-silent file, apply the same check that reverted the bus-layer/UDP/
  DNS-client plan first — does an upstream caller already fully cover every failure mode? Only add
  new logging where a real gap survives that check; don't treat silence as automatically a gap.
- **Syslog severity mapping** — explicitly deferred. Keep the current internal level scheme
  (`OFF/ERR/WARN/ONCE/EVENT/ALL` + the err/wrn history split) as-is; the future syslog-forwarding
  module does the internal→external severity mapping itself when it's built. Not this audit's work.

### FRAM chunk determinism rule

No deallocation exists for FRAM chunks, and this is intentional (bump allocator, by design — see
CLAUDE.md). Chunk byte-offset/placement doesn't matter. What must hold, verified per file, not
assumed: **every FRAM-chunk-owning object's construction (and therefore its one-time
`get_chunk()`/`get_timestamped_chunk()` call) must be deterministic across every system event,
especially reboot** — an unconditional, fixed-position statement in the wiring sequence, never
inside a branch, a loop with variable order, or anything a task restart could re-enter.

Already verified safe, this session: task-level restarts (`system_service.py`'s
`start_and_check_tasks()`) only re-invoke an already-captured `task_starters[n]` callable on the
*existing* object — never re-run `__init__`. Full reboot replays `sensortask-wozi.py`'s entire
module-level construction sequence from scratch, and every current FRAM-chunk-owning construction
(`fram`, `sgp_reader`, `bmp_reader`, `scd_reader`, `pixel`, `notify_service`) is already an
unconditional top-level statement — no branching found today.

**Standing check for every cluster touching a FRAM-backed class**: confirm this still holds for
that file, and for any *new* FRAM-backed logger this audit itself introduces (e.g. if a
`CFGMGR_*` or `"DNSSRV"` logger ends up FRAM-backed) — prove single, deterministic construction
*before* adding it, not after.

### Error-code convention (two-pass, per Cluster 10 — convention only, no registry)

Pass 1 (whole-picture inventory — largely already done via this session's full file reads; an
earlier draft said "greps" here, which is wrong and worth flagging explicitly: several early
grep-based estimates in this document, e.g. German-string counts, turned out to be significantly
undercounted and were corrected once the real files were read in full — the errno/wrnno inventory
per cluster above is drawn from those full reads, not the original greps): every current
`errno`/`wrnno` value in every file, plus every new logging call
this audit adds (mainly `config_manager.py`'s new `CFGMGR_*` instances, plus whatever the
stricter "verify upstream" check turns up as genuine gaps elsewhere). Pass 2: assign real numbers
per module, consistent with the inventory, extending `SPECIFICATION.md` Part C.7's existing
per-driver-numbering convention (`DRIVER_SPEC.md` is now a stub pointing there) and its one existing
cross-module precedent (`errno=10` = init
failure). Output is a running list (lives in `SPECIFICATION.md` Part C.7, permanent, not deleted
with this file) so a new module's numbering is easy to pick consistently — convention only, nothing
enforced/registry-like.

### Legacy code usage

Primary use: answering open questions when genuinely stuck. Secondary, low-expectation: watch for
lost ideas worth recovering. Not a mandatory full diff against every promoted file.

### `improved-quality/sensortask-wozi.py`

Mechanical API-consistency fixes are allowed during this audit (owner-authorized). No full
`src/README.md` promotion process on this file in this scope — it stays WIP reference. Already-
found gaps in it (3 `# TODO` None-handling gaps in `/net/config`, `/time/config`, `/led/config` GET
handlers; the old-style `from uasyncio import ThreadSafeFlag` import; `_MAX_I2C_ERR`'s
still-not-yet-renamed generic name) get fixed here as mechanical edits when their cluster comes up,
not deferred wholesale.

### Wiring, two-stage (context, not this audit's work)

Stage 1 (later session): a standalone, hand-written `sensortask-wozi.py` successor, incorporating
this audit's harmonized modules plus any recovered legacy ideas. Stage 2 (far future): a generator
script + definition file. This audit only has to make Stage 1 easy.

### Test policy

Never drop a test or a test idea. Extend/adapt mechanically wherever a constructor signature
changes (expected: `PrintLog`/`SensorReader`/`ConfigManager` all gain new required/optional
parameters as part of the logging work above — touches most of `tests/*.py`, not just `src/`).
Keep every existing integration-chain test (FRAM+notification, notification+neopixel,
notification+SCD30, NTP+FRAM+system, NTP+WiFi+DNS, setter+Microdot); apply the same spirit to
currently-uncovered chains; redo/extend a chain's tests whenever a new element joins it. Each
integration *level* must carry checks — especially error-handling ones — that genuinely can't be
exercised one level down or up.

### Checkpoint cadence

No fixed schedule. Surface a batch of 5-10 top-level decisions (framed as: what's to decide, what's
the scope, what are the consequences — not fine detail) whenever a cluster's findings are blocking
enough or numerous enough to warrant it. Judgment call per cluster, not a rule.

### `asy_uart_driver.py`

Orphan module (zero real callers anywhere in `src/`/`improved-quality/`). Read early for style-
guideline ideas (it's a real, already-promoted file), but its own formal harmonization pass happens
late, after the style guideline (Cluster 10) has converged — "pick up the spirit early, harmonize
late."

### Sync-`__init__`/async-`setup()` readiness-gate scheme

Project-wide rule for any class whose real construction work needs an `await` (I/O, or just calling
an inherited async logging method) but is currently attempted inside a synchronous `__init__`.
Already proven in `asy_fram_driver.py`'s `FRAM_SPI` and `asy_spi_driver.py`'s `SPIDevice` before this
audit — this makes it the standard everywhere, not just those two:

- `__init__` stays synchronous, stashes constructor args, sets a readiness gate to "not ready."
- An explicit `async def setup()` does the real deferred work, flips the gate to "ready" on success.
- **Gate name/polarity is standardized**: `self.initialized: bool = False` → `True`, replacing ad
  hoc names/polarities (`FRAM_SPI`/`SPIDevice`'s current `uninitialized` — inverted, gets renamed
  and flipped, naming-only change) — *except* where the underlying meaning is genuinely different
  from "has setup run," not just differently spelled: `ConfigManager.valid` stays `valid` on
  purpose (it means "setup ran *and* produced trustworthy data," a real distinction every current
  caller already relies on — see Cluster 2). Don't force an identical name onto a genuinely
  different meaning.
- A `Type | None`-typed attribute stays the *complementary* mechanism for one specific sub-resource
  that can independently fail *during* an otherwise-successful `setup()` (`PrintLogHistoryStore.fram`
  is the existing example) — answers "did this one piece work," not "has setup run at all." Not a
  competing choice against the bool gate; both can coexist on the same class.
- **Response to "called before setup() ran" is *not* a free stylistic choice** — it must match
  whatever raise/never-raise contract the class already declares in its own module docstring, not a
  blanket rule:
  - A class documented as "never raises" (every `SensorReader`/`SensorReaderConfig` subclass,
    `PrintLog` family, `ConfigManager`) returns its documented sentinel and logs, exactly like every
    other failure mode that class already handles — confirmed this holds for `FRAM_SPI` specifically
    (its own docstring: "self-healing to a safe state without raising, except `__init__`/`setup()`'s
    one-time setup errors" — its current sentinel-returning behavior for `get_write_protected()`/
    `get_values()`/etc. was already correct; an earlier version of this plan wrongly proposed
    changing it to raise, corrected here).
  - `SPIDevice.__aenter__`'s raise is a structural necessity of Python's `async with` protocol (no
    sentinel-return option exists for a failed `__aenter__`), not a stylistic precedent — doesn't
    extend to any other method on any other class.
- **Verify, don't assume, for every class this scheme touches**: check that file's own module
  docstring for an already-declared raise/never-raise contract before deciding the response shape —
  don't default to copying whichever example was read most recently (the mistake corrected above).

**Known occurrences, checked this session** — not yet exhaustive, recheck when each cluster is
actually executed:

| Class | Current shape | What changes |
|---|---|---|
| `FRAM_SPI` (Cluster 6) | `uninitialized`, sentinel-returning | Rename/flip flag only, no behavior change |
| `SPIDevice` (Cluster 4) | `uninitialized`, raises in `__aenter__` | Rename/flip flag; raise stays (protocol necessity) |
| `PrintLogHistoryStore` (Cluster 1) | `initialized` + `fram: Chunk \| None`, sentinel-returning | Already matches the target shape — no change |
| `ConfigManager` (Cluster 2) | `valid`, computed synchronously in `__init__`, sentinel-returning | Move the work into `async def setup()`; keep `valid`'s name and sentinel-returning behavior unchanged |
| `NotificationCoordinator` (Cluster 9) | `_finalized` exists but doesn't guard `get_dict_cfg()`/`monitor_loop()`/etc. against being called too early — real gap, not just a naming mismatch | Add the guard, sentinel-based (never-raises contract inherited from `SensorReaderConfig`), reusing/renaming `_finalized` |
| `AsyFramManager.setup()`, `I2CDevice.setup()` | No readiness flag at all | **Resolved, confirmed by reading both files in full — neither needs one.** `AsyFramManager.get_chunk()`/`get_timestamped_chunk()` are pure bookkeeping (offset arithmetic, no hardware access), so they're safe before `setup()` runs; real hardware access always goes through the shared `self.fram` (`FRAM_SPI`), which already has its own `uninitialized` guard — a second gate at the manager level would be redundant. `I2CDevice` has no unconfigured-hardware-state risk the way `SPIDevice`'s CS pin does: the underlying `I2C` bus is fully ready immediately from `I2C.__init__` itself, and `I2CDevice.setup()` only performs an *optional* identity probe with no state transition to guard against. |

**Cross-cutting confirmation, partly a real finding**: every `Timer.init()` call site's `except OSError as e: self.pr.err(...)` (never `err_s`) is correct as-is on the sync-vs-async question — confirmed via `system_service.py`'s own explicit comment on `_timer_sequencer()`: a `Timer`-callback-invoked context has no running event loop, so only the synchronous `pr.err()` is callable there at all, `err_s()` genuinely cannot be `await`ed. Don't touch that part. **But the `except` clause itself is a real, if minor, gap**: it catches only `OSError`, not `(OSError, MemoryError)`, and `Timer.init()`'s documented failure mode (`OSError(ENOMEM)` on RP2040 alarm-pool exhaustion) is exactly the allocation-adjacent case CLAUDE.md's own standing rule already covers ("anywhere an `OSError` is caught around a call that could also plausibly exhaust memory, catch `(OSError, MemoryError)` instead") — an earlier pass through this document called the bare `except OSError` "correct as-is, not a gap," which was wrong against that existing rule. **Resolved, owner-confirmed**: widen every one of these sites to `except (OSError, MemoryError) as e:` regardless of how hard the failure is to provoke in practice — cheap, defensive, no behavior change on the success path. This repeats identically across every `start_timer()`/`_reboot()`/`pause_permanent_storage()` in `asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py` (Cluster 7, ×1 each), `asy_wifi_service.py` (×3)/`asy_ntp_client.py` (×3) (Cluster 8), and `system_service.py` (×4) (Cluster 9) — each of those clusters now carries this as a real action item, not a no-op confirmation. Separately, still worth doing once (not per-file): verify against current MicroPython source whether `Timer.init()` can raise a genuine `MemoryError` distinct from `OSError(ENOMEM)` — informational, doesn't gate the defensive catch above either way (Cluster 10).

---

## Cluster roadmap

Ordered along the real import/call graph — verified via grep against actual `import`/`from`
statements, not assumed. Foundational → dependency clusters → global, per the agreed strategy.

| # | Files | Depends on |
|---|---|---|
| 0 | `math_helpers.py`, `crc_checks.py`, `voc_algorithm.py`, `api_response.py`, `asy_udp_socket.py` | nothing internal |
| 1 | `print_log.py` | crc_checks |
| 2 | `config_manager.py` | print_log |
| 3 | `base_classes.py` | config_manager, print_log |
| 4 | `asy_i2c_driver.py`, `asy_spi_driver.py` | base_classes |
| 5 | `asy_dns_client.py`, `captive_dns.py` | asy_udp_socket, print_log |
| 6 | `asy_fram_driver.py` → `asy_fram_manager.py`; `asy_uart_driver.py` (harmonize late) | asy_spi_driver, base_classes, crc_checks, print_log |
| 7 | `asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py` | math_helpers, asy_i2c_driver, base_classes, config_manager, crc_checks, voc_algorithm, asy_fram_manager |
| 8 | `asy_wifi_service.py`, `asy_ntp_client.py` | base_classes, captive_dns, config_manager, asy_dns_client, asy_udp_socket |
| 9 | `asy_neopixel_driver.py`, `asy_notification_service.py`, `system_service.py` | base_classes, config_manager, print_log, asy_fram_manager |
| 10 | Global pass | everything |

Cluster 10 covers: style-guideline harmonization (editing `SPECIFICATION.md`'s Parts C/D, which
already hold `DRIVER_SPEC.md`'s/`src/README.md`'s former content verbatim, against real per-file
findings — not producing a new document), error-code convention pass 2, `sensortask-wozi.py`
mechanical fixes + the full `WIRING_CONTRACT.md` study, whole-system integration test scoping, and
re-checking every cross-cluster item flagged
along the way (bus-layer/UDP/DNS-client upstream-coverage verification, FRAM determinism on every
touched file).

---

## Cluster 0 — foundational, no internal dependencies

**Goal**: confirm these five files (already read in full this session) hold up against the current
conventions above and `SPECIFICATION.md` Part D's full checklist (`src/README.md`'s former content
— that file is now a stub pointing there); they were largely already mature/reviewed before this
audit started, so this is closer to re-verification than first review.

**Quality measure**: each file passes `SPECIFICATION.md` Part D (D.0-D.16) with findings either
fixed or explicitly flagged — including `voc_algorithm.py`'s already-filed `_fix16_exp()` D.4
finding below, not just future findings; `lint.sh`/`typecheck.sh`/`test.sh` stay green; no behavior
change without an explicit flag-and-ask per D.1.

**Executed 2026-08-07**: `lint.sh`/`typecheck.sh` confirmed green for these five files (all
findings in both runs are pre-existing and confined to `improved-quality/sensortask-wozi.py`, out
of this cluster's scope); `test.sh` passed in full (exit 0, zero `FAIL` lines across every
`tests/test_*.py` file, including `test_fix16_exp_saturates_at_documented_bounds` confirming the
`_fix16_exp()` fix below is behavior-identical). Commits `c2b4239` (this cluster) on top of
`20a2417` (the BACKLOG.md citation-staleness fix found while verifying no open topics remained
before starting this cluster).

| File | Status | Notes |
|---|---|---|
| `math_helpers.py` | `[x]` | `wet_bulb_temperature()`'s Stull (2011) formula and its 5-99% RH / -20-50 degC validity range re-verified word-for-word against the paper — no changes needed. **Real citation fix found and applied**: `dew_point()`'s module comment attributed its water-branch constants (`17.625`/`243.04`) to Sonntag (1990); verified against real sources that these are actually Alduchov & Eskridge's (1996) refit of the Magnus formula (re-optimized to ~0.4% accuracy over -40-60 degC) — Sonntag's own published water-branch values are `17.62`/`243.12`. The ice-branch constants (`22.46`/`272.62`) do match Sonntag (1996's paper doesn't re-derive the ice branch). Comment corrected to attribute each branch to its real source; zero behavior/coefficient change. `altitude_baro()`'s ideal-gas constants (g/M/R) are exact SI/CODATA values, unchanged. No MicroPython-currency drift (D.9) — `math` module usage is all stable, long-standing API. |
| `crc_checks.py` | `[x]` | All three CRC definitions re-verified against real sources, not just re-asserted: Sensirion CRC-8 (poly `0x31`, init `0xFF`, no reflection, final XOR `0x00`) confirmed directly against `datasheets/scd30/Sensirion_CO2_Sensors_SCD30_Interface_Description.pdf`'s own checksum section, and the file's exact bit-banged algorithm reproduces the datasheet's own worked example (`CRC(0xBEEF) = 0x92`) exactly. CRC-16/CCITT-FALSE and CRC-32/MPEG-2 parameter sets (poly/init/refin/refout/xorout) confirmed against the standard CRC catalogue. No code changes needed. No MicroPython-currency drift (D.9) — already uses `asyncio`/`struct` (not `u`-prefixed), already benefits from 1.26's bytearray/memoryview slicing optimization per its own docstring. |
| `voc_algorithm.py` | `[x]` | **`_fix16_exp()`'s filed D.4 finding fixed**: the two 4-element constant lists (`exp_pos_values`/`exp_neg_values`) are now precomputed once in `__init__` as instance tuples (`self._exp_pos_values`/`self._exp_neg_values`), reusing the exact same `self._f16(...)` calls rather than duplicating that rounding logic at module level — avoids the previous per-call allocation with zero behavior change, confirmed by the full existing test suite (including the boundary-saturation test) passing unchanged. Still a direct, faithful port of Sensirion's fixed-point reference otherwise; no other findings. |
| `api_response.py` | `[~]` | Re-verified against Part D — clean, function-based, already the project's own exemplar for the `TYPE_CHECKING`-guard pattern (D.6) and envelope-shape consistency (D.10). No changes needed. One `err_s` call (line 102) still has no name — **still can't be marked fully done until Cluster 1 lands** (unchanged from before this pass; not force-closed). |
| `asy_udp_socket.py` | `[~]` | Re-verified against Part D — every I/O method still returns its documented sentinel, never raises (`__init__` excepted, by design); no MicroPython-currency drift (`select.poll`/`ipoll` usage, `micropython.const`, no `u`-prefixed imports). No changes needed. **Still can't be marked fully done until Cluster 5 and Cluster 8 both close** (unchanged from before this pass) — needs `asy_dns_client.py`/`captive_dns.py`/`asy_ntp_client.py` in view to verify the upstream-coverage claim. |

**Open decisions for this cluster**: none — both partial-closure dependencies above are sequencing
facts, not decisions needing input.

**External references needed**: Stull (2011) wet-bulb paper (re-verified, matches exactly — see
table above), Alduchov & Eskridge (1996)/Sonntag (1990) Magnus-Tetens coefficients (re-verified,
citation corrected — see table above), ideal-gas barometric formula (re-verified, exact SI/CODATA
constants, no change), Sensirion's CRC-8 spec (re-verified directly against the SCD30 datasheet
PDF), CRC-16/CCITT-FALSE and CRC-32/MPEG-2 standard definitions (re-verified against the standard
CRC catalogue), Sensirion's `embedded-sgp` VOC algorithm reference (still current, no re-derivation
needed for this cluster's one finding), current MicroPython changelog since whatever version each
file's patterns predate (checked per `SPECIFICATION.md` D.9, no drift found in any of the five
files).

---

## Cluster 1 — `print_log.py`

**Goal**: implement the name-baking change (see "Logging & naming scheme" above) — the foundational
change every later cluster depends on.

**Verified this session** (design trialed, then reverted — code not landed, kept here so execution
doesn't need to re-derive it):

- Blast radius is bigger than "print_log.py alone" once actually traced: `get_log()` has 8 external
  callers today (`asy_bmp3xx_driver.py`, `asy_fram_manager.py`, `asy_notification_service.py`,
  `asy_ntp_client.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py`, `asy_wifi_service.py`,
  `system_service.py`), each still passing an explicit name (`get_log(_NAME)`, `get_log("FRAM")`,
  `get_log("Tasks")`). Adding a `name` constructor parameter carries no *positional-collision* risk
  either way (nothing outside this file constructs `PrintLog`/`PrintLogHistory`/`PrintLogHistoryStore`
  positionally in a way a new trailing parameter would disturb — checked `src/*.py` and `tests/*.py`
  directly) — but that's a narrower question than whether it should be *required*, which the next
  bullet answers (no, for a different reason: blast radius on every other file's own constructor
  call, not signature collision). Separately, and regardless of that: `get_log()` itself must **not**
  drop its `name` parameter outright or all 8 call sites break immediately, which would blow this
  cluster's "no other file touched" boundary. Fix: keep `get_log(name: str | None = None)` as a
  **transitional backward-compatible override** — `None` (the new default for any caller not yet
  passing one) falls back to `self.name`; an explicit value still works exactly as today. Each of
  the 8 callers drops its now-redundant explicit argument as part of *its own* cluster (7, 8, 6, 9
  respectively), not as part of Cluster 1.
- On whether `name` itself should be required: give `PrintLog.__init__` a
  default (`name: str = ""`), not a bare required parameter — every other file in `src/` still
  constructs `PrintLogHistory(history_length, debug)`/`PrintLogHistoryStore(fram, history_length,
  debug)` positionally without a name until *their own* cluster adds one. Accept the known,
  temporary cosmetic cost: between Cluster 1 landing and each later cluster passing a real name,
  console output shows an empty-string prefix (`print("", "message", ...)`) — harmless, self-heals
  cluster by cluster, not worth engineering around.
- Concrete signature changes: `PrintLog.__init__(self, level: int | None = None, name: str = "")`,
  storing `self.name = name`; `err`/`wrn`/`one`/`evt`/`all`/`_diag`/`err_s`/`wrn_s` each change
  their `print(*args, **kwargs)` call to `print(self.name, *args, **kwargs)`;
  `PrintLogHistory.__init__`/`PrintLogHistoryStore.__init__` each gain and forward `name: str = ""`
  to `super().__init__(..., name=name)`.
- Checked `tests/test_print_log.py` in full: **no existing test asserts on raw `print()` output** —
  only on `err_count`/`history` contents/`get_log()`'s dict/FRAM byte layout — so prepending
  `self.name` to every print call is safe and breaks nothing. Only one existing test
  (`test_get_log_classifies_error_warning_and_clear_entries`) passes `get_log("Sensor")` explicitly
  — keeps passing unchanged under the backward-compatible design above.
- New tests to add (trialed, all passed except one — see below): name defaults to `""`; name is
  stored verbatim when given; `PrintLogHistory`/`PrintLogHistoryStore` forward `name` to the base
  class; `get_log()` with no argument uses `self.name`; `get_log()` with no argument and no name set
  falls back to `""`.
- **One test-authoring mistake found while trialing this** (not a `print_log.py` bug — diagnosed
  after reverting, worth recording so it isn't repeated): a trial test constructed
  `PrintLogHistory(history_length=2, name="SGP40")`, called `err_s("e", errno=1)` once, then
  asserted `get_log()` returns exactly `{"SGP40": {"ErrCount": 1, "ErrNum": [1], "ErrType":
  ["E"]}}`. That's wrong — the history deque starts pre-filled with `_NO_ERR` entries
  (`[0, 0]` for `history_length=2`), and one `err_s()` call only overwrites the oldest slot, leaving
  `[0, 1]` — so the correct expectation is `ErrNum: [0, 1]`, `ErrType: ["N", "E"]` (exactly the same
  "leftover initial slot" shape the already-existing `test_get_log_classifies_error_warning_and_
  clear_entries` correctly accounts for). Fix when writing this test for real: either assert the
  `[0, 1]`/`["N", "E"]` shape, or construct with `history_length=1` so no initial slot survives.

**Quality measure**: `PrintLog.__init__`/subclasses take `name: str = ""`; `get_log()` stays
backward-compatible via its `name: str | None = None` override, returning the identical dict shape
as today; every existing `tests/test_print_log.py` test passes unchanged; every new test above
passes (including the one that failed during the trial — must be root-caused, not just retried);
no other file touched in this cluster.

**Status**: `[x]` done. **Executed 2026-08-07**: implemented exactly the design trialed above, no
deviation — `PrintLog.__init__(self, level: int | None = None, name: str = "") -> None` stores
`self.name`; `err`/`wrn`/`one`/`evt`/`all`/`_diag`/`err_s`/`wrn_s` all now call
`print(self.name, *args, **kwargs)` (`_diag` has no `**kwargs`, matching its existing signature);
`PrintLogHistory.__init__`/`PrintLogHistoryStore.__init__` each gained `name: str = ""` and forward
it to `super().__init__(..., name=name)`; `get_log(self, name: str | None = None)` falls back to
`self.name` when `name` is `None`, otherwise uses the explicit value exactly as before. Verified no
other file's construction call needed updating — `base_classes.py`, `asy_fram_manager.py`,
`system_service.py`, `asy_neopixel_driver.py` all construct `PrintLogHistory`/`PrintLogHistoryStore`
positionally as `(history_length, debug)`/`(fram, history_length, debug)`, unaffected by a new
trailing default parameter (grepped `src/` directly to confirm, per the cluster's own "no other file
touched" boundary). Added 6 new tests to `tests/test_print_log.py`: `test_name_defaults_to_empty_
string`, `test_name_is_stored_verbatim_when_given`, `test_printloghistory_forwards_name_to_the_base_
class`, `test_printloghistorystore_forwards_name_to_the_base_class`, `test_get_log_with_no_argument_
and_no_name_set_falls_back_to_empty_string`, `test_get_log_with_no_argument_uses_self_name` (built
with `history_length=1` specifically to avoid the leftover-initial-slot test-authoring mistake
recorded above), and `test_get_log_explicit_name_still_overrides_self_name`. `lint.sh`/`typecheck.sh`
stayed at the pre-existing `improved-quality/`-only baseline (30/44 errors respectively, zero in
`src/`/`tests/`); `scripts/test.sh` full suite passed 54/54 in `test_print_log.py` (all pre-existing
tests unchanged, all new tests passing) with zero `FAIL` lines suite-wide.

## Cluster 2 — `config_manager.py`

**Goal**: implement its own `"CFGMGR_" + name` identity, add real `err_s`/`wrn_s` logging (own
`errno`/`wrnno` list — new, doesn't exist today), and the caller-side cross-reference logging
convention (the *owner* logs its own line whenever it accesses the config manager).

**Verified this session** (read the full file — 340 lines, ~29 existing `self.pr.*` call sites, all
currently tagged only with `self.config_file`, the JSON filename, never a `_NAME`-style constant):

- `ConfigManager.__init__(self, filename, cfg_vals, logger: "PrintLog")` currently receives its
  *owner's own* `self.pr` directly and reuses it verbatim — this is the one thing that actually
  changes shape: giving `ConfigManager` its own distinct `"CFGMGR_" + name` identity means it can no
  longer just reuse whatever `logger` object its owner passes in (that object is the owner's,
  carries the owner's own name once Cluster 1 lands — reusing it here would mislabel every
  config-related log line as coming from the owner, not from config management). `ConfigManager`
  needs to construct its **own** internal `PrintLogHistory` instance from a plain `name: str`
  parameter instead of receiving an external `logger`. Concretely: replace the `logger: PrintLog`
  parameter with `name: str`, add `self.pr = PrintLogHistory(name="CFGMGR_" + name)` (in-memory
  only — no FRAM-backing needed; config read/write failures don't need reboot-survival the way
  sensor error history does, and `ConfigManager` never receives a `fram=` argument today). The one
  current call site (`base_classes.py`'s `SensorReaderConfig.__init__`:
  `ConfigManager(cfg_path + "config_" + name + ".cfg", default_vals, self.pr)`) changes to pass
  `name` instead of `self.pr`.
- `ConfigManager` currently has **no `get_error_counter()`/`get_log()`-equivalent method at all** —
  add one (`async def get_error_counter(self) -> ...: return await self.pr.get_log()`), matching
  every other module's shape, so its own error history becomes REST-surfaceable someday the same
  way (ties to the still-open "FRAM-backed error/trace history exposed consistently" goal from
  BACKLOG.md's original audit list).
- **Real architectural fork, found and resolved this session** (was left as an open, blocked
  decision in an earlier draft of this section — that was stale; the resolution already lives in
  the Open Decisions Log and the "Standing conventions" readiness-gate table, just hadn't been
  folded back into this cluster's own text until now): most of this file's genuinely important
  error conditions (empty defaults, an invalid default value, a first-time-write failure) happen
  inside `__init__`, which is synchronous — it cannot `await`, so it can never call the async
  `err_s`/`wrn_s`. **Resolved as option 3**: move the loading/validation logic out of `__init__`
  into a real `async def setup()`, matching `FRAM_SPI`/`SPIDevice`'s already-proven sync-`__init__`/
  async-`setup()` split. `__init__` now only stashes constructor args and sets `self.valid = False`;
  `setup()` does the real load/validate/first-write work and can genuinely call `err_s`/`wrn_s` on
  every failure path, not just the subset that happened to already be inside an `async def` method.
  `self.valid`'s name and sentinel-returning (never-raises) behavior stay exactly as today — only
  *when* the work runs moves, not *how* failure is reported.
- `self.config_file` stays in each message's text as extra detail (which specific file, useful even
  though `self.name` now also identifies the module) — not worth stripping, harmless and mildly
  useful for debugging.
- Provisional severity split for the pass-1 errno/wrnno inventory (final numbers assigned in
  Cluster 10): genuine errors (`err`→`err_s`, in every already-async method) — "Config is not
  valid, cannot read!", "Config read error:", "Key X not found, skipping!", "Type/range error in X",
  "Key X not found in config file, ignoring!", "Error writing config data:". Warnings (`wrn`→`wrn_s`,
  same constraint) — none of the current `wrn` calls are in an async method today (they're all in
  `__init__`), so this list is empty until/unless the fork below is resolved in favor of deferred
  logging.

**Quality measure**: `ConfigManager` constructed with `name: str` (not `logger:`), builds its own
in-memory `PrintLogHistory(name="CFGMGR_" + name)`; `__init__` only stashes constructor args and
sets `self.valid = False`; a new `async def setup()` performs the real load/validate/first-write
work and sets `self.valid` on completion, exactly like `FRAM_SPI.setup()`/`SPIDevice.setup()`
already do; **every** genuine error path in that logic (not just the subset that happened to already
be `async def`) uses real `err_s`/`wrn_s` with its own errno/wrnno; `get_error_counter()` exists and
returns the same dict shape `get_log()` already returns elsewhere; the one current call site
(`base_classes.py`'s `SensorReaderConfig.__init__`) passes `name` instead of `self.pr` as part of
*this* cluster (not deferred to Cluster 3, to keep the build green the moment this cluster lands —
see Cluster 3); the owner-side cross-reference logging line (Cluster 3's job, verified here too)
actually appears paired with each `ConfigManager` log line in a real run; `lint.sh`/`typecheck.sh`/
`test.sh` green; every existing `config_manager` test passes unchanged or is mechanically extended
for the `name`-instead-of-`logger` signature change and the new `setup()` call; no test dropped.

**External references**: none — pure internal Python/MicroPython logic, no hardware/protocol
dependency. Standing MicroPython-currency check only (confirm `json`/file-I/O idioms used here
haven't been superseded between 1.26 and the refactor's target version — no discrepancy expected,
not previously flagged as one).

**Status**: `[x]` done.

**Executed 2026-08-07**: `ConfigManager.__init__(self, filename, cfg_vals, name: str)` replaces the
`logger: PrintLog` parameter with a plain `name: str`; it now only stashes constructor args
(`self.config_file`, `self.cfg_vals`, `self.valid = False`, `self._cache = {}`) plus builds its own
`self.pr = PrintLogHistory(name="CFGMGR_" + name)` (in-memory only, matching the design). A new
`async def setup()` does the real load/validate/first-write work that used to live in `__init__`,
following `FRAM_SPI`/`SpiDevice`'s established sync-`__init__`/async-`setup()` split. Every genuine
error path in `setup()` and the three already-async methods (`_get_values`, `get_dict`,
`write_config`) now uses real `err_s`/`wrn_s` with its own errno/wrnno — sequential in source order,
`errno=1..14`, `wrnno=1..6` (final numbers still subject to Cluster 10's own inventory pass, per the
plan's own "provisional" framing). A new `async def get_error_counter()` returns
`await self.pr.get_log()`, matching every other module's shape. The one current call site
(`base_classes.py`'s `SensorReaderConfig.__init__`) now passes `name` instead of `self.pr` to
`ConfigManager(...)`, done as part of this cluster per its own Quality measure — no other line in
`base_classes.py` was touched (`SensorReaderConfig.setup()` itself remains Cluster 3's own job, not
pulled forward). `SPECIFICATION.md`'s "Microdot / REST layer" background section (the `ConfigManager`
paragraph describing its constructor/loading shape) was updated to match — a stale-doc fix in the
same session per CLAUDE.md's own working agreement, not a scope expansion.

**Real ripple discovered and fixed this session** (an owner-approved scope call, made explicitly
after flagging it rather than guessing — see the session's own decision log): moving the real load
out of `__init__` into `async def setup()` meant every test across the repo that constructs a
`SensorReaderConfig`-family object (`SensorReaderConfig` itself, `BMP3xx_Reader`, `SGP40_Reader`,
`NotificationCoordinator`, `asy_ntp_client`, `asy_conn_time` — every concrete class with a real
config schema) and then reads/writes through its `cfgmgr` needed an explicit
`run(x.cfgmgr.setup())` (or, inside an already-running `async def` helper, `await x.cfgmgr.setup()`)
added right after construction — otherwise `cfgmgr.valid` simply stays `False` forever and every
config read silently returns `None`. Fixed mechanically, scope held constant (assertions/test intent
left unchanged, only the missing `setup()` call added), across: `tests/test_config_manager.py` (the
file's own `_make()` helper plus ~26 direct construction sites), `tests/test_base_classes.py` (~40
sites across `SensorReaderConfig` and five locally-defined subclasses, one test rewritten in place —
`test_sensorreaderconfig_shares_the_same_logger_instance_with_its_configmanager` asserted
`reader.cfgmgr.pr is reader.pr`, which is now permanently false by design, not just missing a
`setup()` call, since `ConfigManager` builds its own separate `PrintLogHistory` — inverted to `is
not` and renamed), `tests/test_api_response.py`, `tests/test_asy_bmp3xx_driver.py`,
`tests/test_asy_notification_service.py` (staged `register()`/`finalize()` construction — the fix
lands right after each of the 46 `.finalize()` calls, not at construction time, since `self.cfgmgr`
doesn't exist until `finalize()` runs), `tests/test_asy_sgp40_driver.py`, `tests/test_asy_ntp_client.py`,
`tests/test_asy_wifi_service.py`, `tests/test_notification_neopixel_integration.py`,
`tests/test_notification_scd30_integration.py`, `tests/test_ntp_fram_system_integration.py`,
`tests/test_ntp_wifi_dns_integration.py`, `tests/test_setter_microdot_integration.py`.
`tests/test_neopixel_wifi_integration.py` and `tests/test_notification_fram_integration.py` also
construct one of these classes but never exercise a `cfgmgr`-dependent read/write path, so needed no
change — confirmed by running each individually, not assumed. **A real bug surfaced and fixed during
this ripple fix, not just a missing call**: a first mechanical pass over `test_asy_sgp40_driver.py`
blanket-inserted `run(x.cfgmgr.setup())` after every construction, including ones inside nested
`async def scenario():` helpers already running under `run(scenario())` — nested `run()` (i.e.
nested `asyncio.run()`) inside an already-running event loop doesn't raise a catchable Python
exception on this MicroPython build, it **segfaults the interpreter**. Caught by the segfault itself
(17/98 tests had printed `PASS`, then the process died with no `FAIL` line and no traceback), fixed
by identifying every insertion's enclosing function (sync vs. `async def`) programmatically and
switching the 17 async-context ones to `await x.cfgmgr.setup()` instead. Worth remembering for any
future mechanical test edit that adds a `run(...)` call: always check whether the insertion point is
already inside a running coroutine first.

Verified: `lint.sh` (30 errors)/`typecheck.sh` (44 errors) both match the established
`improved-quality/`-only baseline exactly, zero new findings in `src/`/`tests/`; `test.sh` full
31-file suite green, 0 `FAIL` lines, including 6 new tests added to `tests/test_config_manager.py`
(`name`-forwarding, `get_error_counter()` shape, directory-path/corrupt-JSON errors actually
recorded via `err_s`/`wrn_s` — not just printed).

## Cluster 3 — `base_classes.py`

**Goal**: `SensorReader.__init__` gains `name`/`logger` reach-through; drop `_error_check`'s
redundant `name` parameter (verify true redundancy first); thread the config-push/pull methods
(`_set_mgr_cfg`, `_set_dict_cfg`, `_recover_failed_push`) so their `err_s`/`wrn_s` calls correctly
use the owning instance's name automatically (they already call `self.pr.*`, so this should fall
out of Cluster 1's change for free — verify, don't assume); add the caller-side cross-reference
logging Cluster 2 needs (a line logged via `self.pr` whenever `_get_mgr_cfg`/`_set_mgr_cfg`
actually calls into `self.cfgmgr`, so it pairs with `ConfigManager`'s own line for a human/future-
rsyslog reader); **give `SensorReaderConfig` its own `async def setup()`** (owner-resolved scope
addition — see Open Decisions Log) that awaits `self.cfgmgr.setup()`, extending the project-wide
readiness-gate scheme one level up instead of carving out a `ConfigManager`-only exception.

**Already read in full this session** — concrete plan:

- `SensorReader.__init__(self, init_data, max_i2c_err, fram=None, history_length=10, debug=None)`
  gains `name: str = ""` and `logger: PrintLog | None = None` (mirrors `FRAM_SPI`'s existing
  `logger=` parameter shape). **Correction from an earlier draft of this section, caught during the
  completeness/consistency pass**: `name` must default to `""`, not be a bare required parameter —
  the same blast-radius reasoning Cluster 1 already worked out for `PrintLog.__init__` applies here
  too, and more sharply: a required `name` would break `super().__init__()` in *every* subclass
  (every `*_Reader`) the instant this cluster lands, since threading the real `name=_NAME` value
  into each subclass's own call is explicitly *those* subclasses' own cluster's job (6/7/8/9), not
  this one's. `name: str = ""` keeps Cluster 3 self-contained exactly like Cluster 1 is, with the
  same accepted, temporary, self-healing cosmetic cost (an empty-string log prefix until each
  subclass's own cluster passes the real value). When `logger` is given, reuse it instead of
  constructing a fresh `PrintLogHistory`/`Store` — the reach-through mechanism for directly-bound
  sibling objects.
- `SensorReaderConfig.__init__` already takes `name: str` (currently only used for the config
  filename) — forward it to `super().__init__(..., name=name)` too. **Note**: the
  `ConfigManager(...)` call's third argument (`self.pr` → `name`) is *not* this cluster's own work —
  Cluster 2's Quality measure now specifies that minimal, mechanical swap happens as part of Cluster
  2 itself (to keep the build green the moment Cluster 2 lands, since it's the one real call site
  for a signature Cluster 2 is changing), not deferred here. Cluster 3's own job on this line is only
  the `super().__init__(..., name=name)` forward.
- **Resolved consequence of Cluster 2's async-`setup()` redesign** (owner decision: extend the
  pattern upward, not carve out an exception — see Open Decisions Log): `SensorReaderConfig` gains
  its own `async def setup(self) -> None: await self.cfgmgr.setup()`, following the exact same
  sync-`__init__`/async-`setup()` shape as `FRAM_SPI`/`SPIDevice`. `SensorReaderConfig.__init__`
  itself stays synchronous (it only constructs `self.cfgmgr = ConfigManager(...)`, cheap and
  non-blocking, matching `ConfigManager.__init__`'s own new stash-only shape) — the new `setup()` is
  the only place anything is `await`ed. **Scope, precisely**: this new `setup()` is needed on every
  concrete `SensorReaderConfig` subclass — confirmed today that's `BMP3xx_Reader`, `SGP40_Reader`,
  `NotificationCoordinator` (each has a real config schema) — but **not** on plain `SensorReader`
  subclasses with no `ConfigManager` at all (`SCD30_Reader`, `NeopixelDriver` — see
  `WIRING_CONTRACT.md`/CLAUDE.md for why each of those two is exempt). Each affected subclass's own
  cluster (7 for the two drivers, 9 for `NotificationCoordinator`) is responsible for making sure its
  own construction site in `sensortask-wozi.py` actually calls `await x.setup()` — that's new scope
  for those clusters, not just this one. The structural fallout for `sensortask-wozi.py` itself
  (today's module-level construction is fully synchronous, and can't stay that way once any
  construction step needs an `await`) doesn't need resolving in this audit — Stage 1's real rewrite
  is out of scope — but is recorded in `WIRING_CONTRACT.md` so Stage 1 isn't blindsided by it.
  `NotificationCoordinator` specifically needs one more hop worth flagging for Cluster 9: its
  existing `register()`/`finalize()` staged-construction is sync (forced by
  `sensortask-wozi.py`'s non-async caller) and calls a deferred `super().__init__()` — that part is
  unaffected, but `NotificationCoordinator` still needs its own `setup()` (inherited or overridden)
  actually invoked, after `finalize()`, wherever `sensortask-wozi.py` ends up calling it.
- `_error_check(results, name, condition=True)` — the `name` parameter is used exactly once, to
  build `name + " Fehlerzähler erhöht auf"`/`name + " Maximale Fehleranzahl erreicht!"` (string
  concatenation, a different shape from every other file's `(self.name, "message")` positional
  convention — also needs fixing to match, not just simplifying). Every call site
  (`self._error_check(results, _NAME)`, one per driver's `read_loop()`) passes exactly its own
  `_NAME` — never a different name — so dropping the parameter and using `self.pr.err_s("Fehlerzähler
  erhöht auf", ...)` (name now automatic) is safe. Verify this holds for every current caller before
  dropping, per the plan's own standing rule, not just assumed from this read.
- **Nine** `err_s`/`wrn_s` calls in `_get_dict_cfg`/`_set_dict_cfg`/`_recover_failed_push` (lines
  191, 194, 200, 203 in `_get_dict_cfg`; 280, 293, 317 in `_set_dict_cfg`; 347, 360 in
  `_recover_failed_push` — re-verified directly against the file during this session's reality-check
  pass; an earlier draft of this section said "Six," undercounting) already call
  `self.pr.err_s(...)`/`self.pr.wrn_s(...)` with no name argument at all — these get the right name
  for free once Cluster 1 lands, no code change needed here beyond confirming it (these are exactly
  the methods Cluster 2's cross-reference logging needs a line added to, around the
  `self.cfgmgr`/`_get_mgr_cfg`/`_set_mgr_cfg` calls specifically). Separately, `_error_check`'s own
  two calls (errno=1/2, lines 217/219) are already accounted for elsewhere in this section. Confirmed
  by the same read: `base_classes.py`'s full errno/wrnno range is exactly `errno=1-9`/`wrnno=1-2`
  (1-2=`_get_dict_cfg`'s `_error_check`, 3-4=`_get_dict_cfg`'s own two, 5-9=`_set_dict_cfg`'s three
  plus `_recover_failed_push`'s two, in source order) — matching the cross-reference already made in
  Cluster 8's inventory notes, now independently reconfirmed against the source rather than taken on
  faith from that earlier cross-reference.

**Quality measure**: `SensorReader.__init__` accepts `name: str = ""` (transitional default, not
required — see the correction above) and `logger: PrintLog | None = None`, reusing a passed logger
instead of constructing a fresh one; `SensorReaderConfig.__init__` forwards its existing `name` to
`super().__init__()` (the separate `ConfigManager` call-site swap is Cluster 2's own job, already
done by the time this cluster lands — see there); `SensorReaderConfig` gains a working
`async def setup()` that awaits `self.cfgmgr.setup()`; `_error_check`'s `name` parameter is removed
only after every current call site is individually confirmed to pass exactly its own `_NAME` (not
just assumed); the nine identified `err_s`/`wrn_s` calls in `_get_dict_cfg`/`_set_dict_cfg`/
`_recover_failed_push` are confirmed to carry the right name with zero code change; a
cross-reference logging line is added at each real `self.cfgmgr` access point in `_get_mgr_cfg`/
`_set_mgr_cfg`; `lint.sh`/`typecheck.sh`/`test.sh` green; every current subclass across `src/`
(every `*_Reader`) still constructs successfully once its own cluster updates its call site, and
every `SensorReaderConfig` subclass specifically (`BMP3xx_Reader`/`SGP40_Reader`/
`NotificationCoordinator`) is confirmed to need its own `await x.setup()` added at its
`sensortask-wozi.py` construction site once its own cluster lands; no test dropped.

**External references**: none beyond the standing MicroPython-currency check already covered by
CLAUDE.md's "Platform target" section (`asyncio.Lock`/`Event` usage in this file, already current
as of the last check — re-confirm only if `toolchain/versions.toml`'s pin has moved since).

**Status**: `[x]` done.

**Executed 2026-08-08**: `SensorReader.__init__` gained `name: str = ""` and
`logger: PrintLogHistory | None = None` (typed as `PrintLogHistory`, not the bare `PrintLog` this
section originally specified — see below); when `logger` is given it's reused as-is (`self.pr =
logger`, short-circuiting the `fram`/no-`fram` branch entirely, including when `fram` is also
given), otherwise a fresh `PrintLogHistory`/`PrintLogHistoryStore` is constructed with `name`
threaded through, exactly as before. `SensorReaderConfig.__init__` now forwards its own `name` to
`super().__init__(..., name=name)`. `SensorReaderConfig` gained the planned `async def setup(self)
-> None: await self.cfgmgr.setup()`. `_error_check()` dropped its redundant `name` parameter — every
current call site (`asy_wifi_service.py`, `asy_scd30_driver.py`, `asy_ntp_client.py`,
`asy_bmp3xx_driver.py`, `asy_sgp40_driver.py`) was individually confirmed to always pass exactly its
own `_NAME` before the parameter was removed, then each of those 5 call sites was updated to drop
the now-gone argument. Its two `err_s()` calls (`errno=1`/`2`) now read `self.pr.err_s("Fehlerzähler
erhöht auf", ...)`/`self.pr.err_s("Maximale Fehleranzahl erreicht!", ...)` — name automatic, matching
this section's own example. The nine `_get_dict_cfg`/`_set_dict_cfg`/`_recover_failed_push`
`err_s`/`wrn_s` calls were reconfirmed to already carry the right name for free via `self.pr`, no
code change needed. Cross-reference logging was added exactly where this section specified: a
`self.pr.evt(...)` line in both `SensorReaderConfig._get_mgr_cfg` (before `self.cfgmgr.get_dict(...)`)
and `_set_mgr_cfg` (before `self.cfgmgr.write_config(...)`), pairing with `ConfigManager`'s own
`pr.all`/`pr.evt` lines for a human/future-rsyslog reader.

**One real correction to this section's own plan, caught during implementation**: `logger` is typed
`PrintLogHistory | None`, not the `PrintLog | None` this section specified. `SensorReader`/
`SensorReaderConfig` call `self.pr.err_s()`/`wrn_s()`/`get_log()` throughout the file — methods that
exist only on `PrintLogHistory` (and its `PrintLogHistoryStore` subclass), not on the looser base
`PrintLog`. Typing `logger` as bare `PrintLog` would have made every one of those calls a real mypy
error the moment a caller ever passed a plain `PrintLog` (which no real caller does — every actual
reach-through use passes a `PrintLogHistory`/`PrintLogHistoryStore` instance) — `FRAM_SPI`'s own
`logger: PrintLog` parameter is safe with the looser type only because that class never calls the
history-only API (confirmed directly: `asy_fram_driver.py` calls only `pr.wrn()`, never
`err_s()`/`wrn_s()`/`get_log()`). Fixed by typing `logger: PrintLogHistory | None` here instead,
matching this file's own actual usage rather than copying FRAM_SPI's annotation verbatim.

**SPECIFICATION.md updated to match**: Part C.4.1's `read_loop()` skeleton and Part C.7's
`_error_check()` signature description both dropped the `name`/`_NAME` argument; Part C.7 also
gained a note on the new `name`/`logger` constructor parameters; Part C.5's "One JSON file per
sensor" paragraph now describes `SensorReaderConfig.setup()` explicitly instead of only describing
`ConfigManager`'s own split.

**Verification**: `scripts/lint.sh` (30 errors, unchanged baseline, all in `improved-quality/`),
`scripts/typecheck.sh` (44 errors, unchanged baseline, all in `improved-quality/sensortask-wozi.py`
— one transient 45th error surfaced mid-implementation from a mypy narrowing quirk on a new test's
`reader.cfgmgr.valid is False` → `run(reader.setup())` → `reader.cfgmgr.valid is True` sequence on
the same chained attribute expression, `tests/test_base_classes.py:763` "Statement is unreachable" —
fixed by reading each side into its own local variable instead of re-checking the same `reader.cfgmgr
.valid` expression twice across the intervening call, which resolved it back to the 44-error
baseline), `scripts/test.sh` (31/31 files, 0 FAIL; `test_base_classes.py` itself 106/106 passing, up
from its pre-Cluster-3 count via 8 new tests: logger/name reach-through (4), `SensorReaderConfig
.setup()` (1), `name` forwarding (1), and the two cross-reference-logging tests for `_get_mgr_cfg`/
`_set_mgr_cfg`, each verified via a recording `PrintLogHistory` subclass override rather than
capturing real stdout). No other test file needed changes — no other file called `_error_check()`
with a now-invalid signature beyond the 4 already listed (`test_asy_sgp40_driver.py`,
`test_notification_scd30_integration.py`, `test_asy_bmp3xx_driver.py`) plus `test_base_classes.py`
itself, and no `SensorReaderConfig`-subclass construction site in any test file needed a `name=`/
`logger=` addition since `SensorReader`/`SensorReaderConfig`'s existing callers all already used
keyword arguments for the parameters after which `name`/`logger` were appended — confirmed directly
against every `super().__init__()` call site in `src/` (`asy_bmp3xx_driver.py`, `asy_sgp40_driver.py`,
`asy_ntp_client.py`, `asy_wifi_service.py`, `asy_notification_service.py`, `asy_scd30_driver.py`)
before considering this cluster's ripple closed.

## Cluster 4 — `asy_i2c_driver.py`, `asy_spi_driver.py`

**Goal**: **no logging added** (reverted — see above). Verify every real caller of `I2CDevice`/
`SPIDevice` across every current sensor driver and `FRAM_SPI` genuinely wraps and logs each call
site per `SPECIFICATION.md` D.2's carve-out instructions. Fix the caller if a gap is found.

**Already read both files in full this session** — the exact surface to verify against every
caller: `I2CDevice`'s public methods are `get_bits`, `get_register_struct`, `set_bits`,
`set_register_struct`, `setup`, `readinto`, `write`, `write_then_readinto` (three real callers:
`asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py` — Cluster 7).
`SPIDevice`'s are `write`, `readinto`, `write_readinto`, `setup` (one real caller: `FRAM_SPI` —
Cluster 6). Confirmed directly: `SPIDevice.write`/`readinto` genuinely cannot raise on rp2 hardware
(no ACK/NAK concept once the bus is constructed); `write_readinto` only raises a caller-input
`ValueError` on a buffer-length mismatch, already caught inside `asy_spi_driver.py` itself and
turned into `None` — so SPI's fault surface is already fully closed *at this layer*, nothing to
verify upstream for SPI specifically. I2C is the real work: `I2CDevice`'s methods forward straight
to `machine.I2C`'s own calls, which raise real `OSError` on a hardware fault — every one of the
eight methods' use across all three sensor drivers needs its call site confirmed inside a
`try/except` at the Reader layer when Cluster 7 is reached.

**Quality measure**: every one of `I2CDevice`'s 8 public methods, at every real call site across
`asy_bmp3xx_driver.py`/`asy_scd30_driver.py`/`asy_sgp40_driver.py`, confirmed wrapped in a
try/except at the Reader layer with a real, logged failure path — any gap found gets fixed at the
*caller* (Cluster 7), never by adding logging to `asy_i2c_driver.py`/`asy_spi_driver.py`
themselves; SPI's already-fully-closed fault surface reconfirmed with no new work; `lint.sh`/
`typecheck.sh`/`test.sh` green; no behavior change to either file expected — a clean pass here means
zero diff to this cluster's own two files, only to callers if a gap surfaces.

**External references**: RP2040 I2C/SPI peripheral raise/no-raise behavior — already established
via CLAUDE.md's "Platform target" section and this session's direct reads of both files (confirmed:
I2C raises real `OSError` on a hardware NAK/timeout, SPI transfers cannot on rp2 except one caught
`ValueError`). No chip-specific datasheet applies to these two files themselves (they're
bus-generic, not device-specific).

**Status**: `[x]` done (verification pass; final re-confirmation still happens when Cluster 7 touches
the same 3 caller files, per the dependency note below — not expected to change this conclusion).

**Executed 2026-08-08**: Re-read `asy_i2c_driver.py`/`asy_spi_driver.py` in full (no drift from the
prior session's read) and traced, method by method, every real call site of `I2CDevice`'s 8 public
methods across all three sensor drivers:

- **`asy_bmp3xx_driver.py`**: every `I2CDevice` touch inside `BMP3XX_I2C` (`_get_osr_setting`,
  `_read`, `_read_register`, `_set_osr_setting`, `get_filter_coefficient`/`set_filter_coefficient`,
  `setup`, `reset`, `_wait_status_bits`) is only reachable through a `BMP3xx_Reader` method that
  wraps the call in `try/except Exception` with a logged `err_s(...)` path (`_read_bmp`, `_init_bmp`,
  `get_pressure_oversampling`/`set_pressure_oversampling`, `get_temperature_oversampling`/
  `set_temperature_oversampling`, `get_filter_coefficient`/`set_filter_coefficient`). No gap found.
- **`asy_scd30_driver.py`**: every `I2CDevice` touch inside `SCD30_I2C` (`_send_command`/
  `_send_dev_command`, `_read_register`/`_read_dev_register`, `setup`, `reset`,
  `stop_continuous_measurement`, `read_measurement`) is only reachable through an `SCD30_Reader`
  method wrapped the same way (`_read_scd`, `_init_scd`, the six config getters, the seven config
  setters, `stop_continuous_measurement`). No gap found.
- **`asy_sgp40_driver.py`**: every `I2CDevice` touch inside `SGP40_I2C` (`_read_word_from_command`,
  `get_raw`, `measure_raw`, `measure_index_and_raw`, `setup`, `initialize`) is only reachable through
  `SGP40_Reader._read_sgp`/`_init_sgp`, both wrapped in `try/except Exception` with a logged
  `err_s(...)` path. `_reset()`'s own general-call `writeto(0x00, b"\x06")` already has its own local
  `try/except OSError: pass` (a NAK there is an expected, not a failure, per the datasheet's general-
  call semantics) — correctly scoped narrower than the outer wrap, not a gap. No gap found.
- **SPI reconfirmed**: `FRAM_SPI`'s three `SPIDevice` call sites in `asy_fram_driver.py` need no
  wrapping — reconfirmed `SPI.write()`/`readinto()` return `None` unconditionally on rp2 and
  `write_readinto()` already catches its own `ValueError` internally, matching this cluster's
  original finding exactly. No new work.

**Result**: zero gaps found across all three I2C sensor drivers — every one of `I2CDevice`'s 8 public
methods is reachable only via a Reader-layer call already wrapped in `try/except` with a real, logged
failure path. **No diff to any file this cluster** (`asy_i2c_driver.py`, `asy_spi_driver.py`, or any
of the three caller files) — matches this section's own "a clean pass here means zero diff" quality
measure exactly.

**Incidental finding, not a gap, not fixed here**: `BMP3XX_I2C.get_altitude()` (asy_bmp3xx_driver.py,
computes altitude from `sea_level_pressure` — an Adafruit-reference-driver carryover) has zero callers
anywhere in `src/`; `BMP3xx_Reader`'s actual "SLPres" field is computed separately via
`math_helpers.altitude_baro()` in `_store_bmp()`, never through this method. Dead code, not an
error-handling gap, so out of this cluster's own scope — flagged here rather than silently deleted,
per the project's "flag, don't guess" agreement; worth a decision (delete vs. wire up) whenever
`asy_bmp3xx_driver.py` is next touched (Cluster 7).

## Cluster 5 — `asy_dns_client.py`, `captive_dns.py`

**Goal**: `captive_dns.py`'s `DNSServer` gets its own name/logger (proposed `"DNSSRV"`, owner-resolved
as an *independent* instance, not shared with `asy_conn_time` — see Open Decisions Log) — already
verified single-construction-safe. `asy_dns_client.py` gets no logger (reverted) — same
upstream-coverage verification as Cluster 4, against `asy_ntp_client.py` (Cluster 8). **Also in
scope, owner-resolved this session**: unify `captive_dns.py`/`asy_dns_client.py`'s IPv4-validation
stance on the `isdigit()`-check style, and close `resolve_ipv4()`'s missing construction guard (see
New findings below).

**Verified this session — real finding**: `captive_dns.py` doesn't use `PrintLog` at all today.
`DNSServer`/`DNSQuery` both use a completely different, ad hoc scheme: a plain `debug: bool = False`
constructor flag gating raw `print(...)` calls directly, not `self.pr`/`PrintLog`'s leveled system
every other class in `src/` uses. This is a bigger, real inconsistency to fix, not just "add a
name": `debug` needs to become `debug: int | None` (matching every other class's constructor
signature, forwarded as `PrintLog`'s level) and every raw `print(...)` call becomes a real
`self.pr.evt(...)`/`self.pr.err_s(...)`/`self.pr.wrn_s(...)` call through a real `PrintLogHistory`
instance named `"DNSSRV"`. `DNSQuery` is constructed fresh on every single incoming DNS request
(inside `DNSServer.run()`'s loop) — same "ephemeral, can't hold its own meaningful history" shape
already established for `AsyUDPSocket` — so it should receive/reuse `DNSServer`'s own `self.pr`
reference (passed in as a constructor parameter) rather than getting an independent instance of its
own.

**Quality measure**: `DNSServer`/`DNSQuery` fully converted from raw `print()` + `debug: bool` to
`PrintLogHistory` + `debug: int | None`, matching every other class's constructor-signature shape;
`DNSServer` named `"DNSSRV"`; `DNSQuery` receives/reuses `DNSServer`'s own `self.pr` reference
rather than constructing its own; every existing `print()` call site converted to the matching
`evt`/`err_s`/`wrn_s` call with a real errno/wrnno; `asy_dns_client.py`'s "no logging needed" claim
reconfirmed jointly with Cluster 8 (can't close from this cluster alone); **this cluster's New
findings below also close**: `resolve_ipv4()` wraps its `AsyUDPSocket` construction in the same
guard `_fetch_ntp_reply()` already uses; `_ipv4_to_int()` is rewritten to the `isdigit()`-check,
never-raises style (matching `_is_ipv4_literal()`), with every caller's now-dead `ValueError` catch
removed; `lint.sh`/`typecheck.sh`/
`test.sh` green; new/extended tests cover the converted logging paths (malformed query, off-subnet
drop, `_ipv4_to_int`'s new never-raises behavior in place of its old failure path); no test dropped.

**External references**: RFC 1035 sections 4.1.1/4.1.2/4.1.4 (DNS message format) — already
correctly cited in `captive_dns.py`'s own comments; re-verify the citation is still accurate as
part of this cluster's work, not a fresh lookup (no reason to expect drift — RFC 1035 is a fixed
standard). RFC 791 section 3.2 (dotted-quad parsing) — same, already cited, re-verify only.

**Status**: `[x]` done.

**Executed 2026-08-08**:

- **`captive_dns.py`**: `DNSServer` now constructs its own independent `PrintLogHistory`/
  `PrintLogHistoryStore` (named `"DNSSRV"` via a new `_NAME` const), taking `fram`/`history_length`/
  `debug: int | None` constructor parameters — same shape as `NeopixelDriver`/`SensorReader`.
  `debug: bool = False` and every raw `print(...)`/`if self.debug:` call site are gone; every
  message is now a real `self.pr.evt(...)` (routine/informational — waiting/incoming/replying/
  ignoring/empty-query/shutdown/disconnected) or a persisted `await self.pr.err_s(...)`/
  `await self.pr.wrn_s(...)` with a real errno/wrnno (invalid server_ip/netmask at startup =
  errno 1, an unexpected loop exception = errno 2, a disconnect-cleanup exception = errno 3;
  `sendto()` reporting a dropped reply = wrnno 1, invalid recvfrom data/address = wrnno 2).
  `DNSQuery` drops its own `debug: bool` entirely and now takes a required `pr: PrintLogHistory`
  constructor parameter, reusing `DNSServer`'s own `self.pr` reference passed in from `run()`
  (`DNSQuery(data, self.pr)`) rather than constructing an independent instance — matches
  `AsyUDPSocket`'s established "ephemeral object reuses its owner's logger" precedent.
- **`_ipv4_to_int()` rewritten to the `isdigit()`-check, never-raises style**, matching
  `asy_dns_client.py::_is_ipv4_literal()` exactly: returns `int | None` instead of raising
  `ValueError`. All three real call sites updated to `is None` checks instead of `try`/`except`:
  `run()`'s startup netmask/server_ip validation (now a single `if ... is None: err_s(...); return`
  instead of a wrapping `try`/`except`), `run()`'s on-subnet check for `addr[0]`, and
  `DNSQuery.response()`'s `ip` validation before building the reply packet. Closes the D.10
  cross-file inconsistency per the owner's resolved decision above.
- **Real regression caught and fixed during this cluster's own test run**: `run()`'s on-subnet
  check first dropped the old local `try`/`except Exception: on_subnet = False` around
  `_ipv4_to_int(addr[0])` entirely, relying only on the new `is None` check — correct for a
  malformed-but-`str` `addr[0]`, but `_ipv4_to_int()` still raises for a **non-`str`** value (it
  calls `ip.split(".")` directly, matching `_is_ipv4_literal()`'s own no-non-str-guard stance).
  A real MicroPython Unix-port test run proved this isn't hypothetical: a server-mode socket bound
  via a pre-resolved sockaddr (this test build's own documented quirk, not real rp2 hardware) hands
  `recvfrom()` back an opaque raw sockaddr whose `addr[0]` is a plain `int`, not a host string —
  confirmed directly (`'int' object has no attribute 'split'`). Without a local guard, that
  exception fell through to `run()`'s outer `except Exception` (the "genuinely unexpected failure"
  path), triggering its 3-second backoff; if cancellation landed during that
  `await asyncio.sleep(3)`, the `CancelledError` raised *inside* the `except Exception:` block's own
  body propagated straight out of `run()`, skipping the `disconnect()` cleanup entirely and leaking
  the bound socket — caught by `test_run_reuses_same_dns_server_instance_across_multiple_hotspot_cycles`
  failing (`server.udps.sock` stayed non-`None` after cancellation). Fixed by restoring a narrow,
  local `try/except Exception: addr_int = None` around just the `_ipv4_to_int(addr[0])` call —
  routine untrusted-network-input handling (same bucket as off-subnet), not something that should
  ever reach the 3s backoff. `_ipv4_to_int(netmask)`/`_ipv4_to_int(server_ip)` at the top of `run()`
  keep no such guard — those come from `wlan.ifconfig()`, a real framework guarantee to return
  `str`, unlike `addr[0]`'s empirically-proven-inconsistent shape.
- **`asy_dns_client.py`**: `resolve_ipv4()`'s `AsyUDPSocket((server, port), mode="client")`
  construction now wrapped in `try/except (ValueError, TypeError): continue` — the same guard
  `asy_ntp_client.py::_fetch_ntp_reply()` already uses — closing the gap the New findings above
  identified. No logger added to this file (reconfirmed "no logging needed", jointly with Cluster 8
  as planned — this file still has no `self.pr` of its own).
- **`asy_wifi_service.py`**: `asy_conn_time.__init__`'s `self.dns_server = DNSServer(debug=bool(debug))`
  changed to `DNSServer(fram=fram, history_length=history_length, debug=debug)`, threading its own
  already-available constructor parameters through to give `DNSServer` its independent identity
  instead of a shared, coerced-to-bool value.
- **RFC citations re-verified, unchanged**: RFC 1035 §§4.1.1/4.1.2/4.1.4 and RFC 791 §3.2 — both
  still accurately cited in `captive_dns.py`'s own comments, no drift.
- **Tests**: `tests/test_captive_dns.py` rewritten throughout for the new `DNSServer`/`DNSQuery`
  constructor shapes (a shared `make_pr()` test helper replaces every `debug=True/False` call site;
  logging behavior is asserted via `server.pr.err_count`/`.get_level()`/`.name`, matching
  `test_base_classes.py`'s own established convention — no stdout-capture-based assertions);
  `_ipv4_to_int`'s malformed-string tests now assert `is None` instead of catching `ValueError`; new
  tests added for `_ipv4_to_int`'s remaining non-`str` raise behavior, the `DNSQuery` logger-reuse
  contract, the new persisted err_s/wrn_s paths (invalid startup config, dropped `sendto()`, invalid
  recvfrom data, the unexpected-exception backoff path, disconnect-failure logging), and
  `resolve_ipv4()`'s new construction guard (`tests/test_asy_dns_client.py`, via a raising
  `AsyUDPSocket` substitute — the file's own `_ResolvingAsyUDPSocket` wrapper resolves addresses
  through `socket.getaddrinfo()` before ever reaching `AsyUDPSocket`'s real type check, so a
  real malformed port raises `OSError` at the wrong layer to exercise this specific guard). No test
  dropped. `lint.sh`/`typecheck.sh`/`test.sh` all green (`test_asy_dns_client.py` 31/31,
  `test_captive_dns.py` 50/50, `test_asy_wifi_service.py` 168/168,
  `test_ntp_wifi_dns_integration.py` 8/8 — the latter two unaffected by this cluster's changes,
  reconfirmed clean).

**New findings (bidirectional Part C/D cross-check, 2026-08-07)**:

- `asy_dns_client.py::resolve_ipv4()` constructs `AsyUDPSocket((server, port), mode="client")`
  with no `try`/`except`, even though `AsyUDPSocket.__init__` is the one method its own module
  docstring flags as able to raise (`ValueError`/`TypeError`), and the structurally identical
  construction in `asy_ntp_client.py::_fetch_ntp_reply()` already wraps it. `resolve_ipv4()`'s own
  docstring promises "never raises" — currently only true because every real caller's
  `get_dns_server` callback happens to return a well-typed value; nothing enforces that at
  runtime. Add the same guard `_fetch_ntp_reply()` already uses, closing the gap between the two
  files' otherwise-identical pattern.
- **Resolved (owner decision, 2026-08-07): standardize on `asy_dns_client.py`'s `isdigit()`-check
  stance.** `captive_dns.py::_ipv4_to_int()` and `asy_dns_client.py::_is_ipv4_literal()` took
  opposite design stances on the same problem (IPv4-string validation) — one raising `ValueError`
  on malformed input, the other deliberately avoiding exceptions for control flow. This cluster's
  execution rewrites `_ipv4_to_int()` to the `isdigit()`-check style, removing its `ValueError`
  raise; every current caller that catches that `ValueError` needs its catch removed/adjusted to
  match the new never-raises shape. Closes the D.10 cross-file inconsistency.
- **Resolved (owner decision, 2026-08-07): `DNSServer` gets its own independent `"DNSSRV"`-named
  `PrintLogHistory`**, not `asy_conn_time`'s shared `self.pr` — per the Goal above. The owner's
  stated rationale: at the `sensortask` wiring level, `DNSServer`'s history is expected to later
  fold into one combined "Networking" REST endpoint alongside `asy_conn_time`/`asy_dns_client`
  (already anticipated in `WIRING_CONTRACT.md`'s "Forward API-design notes"), so keeping it
  independent now is the better fit than merging into `asy_conn_time`'s stream. Recorded as an
  accepted C.7 pattern in `SPECIFICATION.md` (see C.7's new "owned helper" bullet) — no longer an
  open decision.

## Cluster 6 — `asy_fram_driver.py`, `asy_fram_manager.py` (`asy_uart_driver.py` listed for context only — harmonize-late, not touched here)

**Goal**: thread the shared `"FRAM"` name through the existing `logger=` sharing mechanism (already
precedented, just needs identity). Re-verify the FRAM determinism rule against every current
chunk-owning caller (see Cluster 7/9 — cross-cluster). `asy_uart_driver.py`: read for style ideas
now, defer its formal pass to Cluster 10 per the "harmonize late" decision. Apply the readiness-gate
naming scheme (see "Standing conventions" above) to `FRAM_SPI`'s `uninitialized` flag — rename/flip
polarity only, its sentinel-returning behavior is already correct and does not change.

**Verified this session** (read `asy_fram_driver.py` in full):

- No structural change needed for the name itself — `FRAM_SPI` already receives `AsyFramManager`'s
  own shared `self.pr` via its existing `logger: PrintLog` constructor parameter (confirmed:
  `self.pr = logger`). Once that shared instance gets `name="FRAM"` in `AsyFramManager.__init__`,
  every one of `FRAM_SPI`'s existing calls (`self.pr.wrn(...)` ×3, `self.pr.err(...)` ×5,
  `self.pr.evt(...)` ×1, `self.pr.one(...)` ×1) gets the right prefix automatically — zero code
  change in `asy_fram_driver.py` itself for the naming part.
- **Real finding, separate from naming**: none of `FRAM_SPI`'s 8 error/warning calls are persisted
  (`err_s`/`wrn_s`) — they're all non-counted `err`/`wrn`. Genuinely actionable hardware-fault
  signals live here (WEL latch didn't set/clear, write-protect readback mismatch, device not
  initialized, address range invalid, lock-timeout on `verify_present()`) — good candidates to
  upgrade to persisted logging under the "add/complete logging" rule, sharing `AsyFramManager`'s
  errno-space (Cluster 10 pass-2 assigns exact numbers, picking up where that range currently
  ends — see the corrected inventory below). All 8 calls are already inside `async def` methods
  (no `ConfigManager`-style sync-`__init__` constraint here) — nothing blocking this beyond the
  pass-2 numbering itself.
- **`asy_fram_manager.py` now read in full this session** (correcting the earlier grep-only
  estimate): `AsyFramManager` constructs `self.pr = PrintLogHistory(history_length, debug)`
  (in-memory, correctly avoiding a recursive FRAM-into-FRAM dependency for its own log), and every
  chunk class (`_AsyBaseFramChunk`, `AsyFramChunk`, `AsyFramTimestampedChunk`) shares that exact
  same `self.pr` instance too (passed down as `logger=` at construction) — the "shared logger"
  design already extends all the way down to individual chunk objects, not just
  `AsyFramManager`/`FRAM_SPI`. The real numbering spans roughly **`errno=10-88`**, not `60-88` as
  the earlier grep-based estimate had it: `_handle_status_bytes`/`_set_check_sb` compute their own
  errno dynamically from caller-supplied bases (10 in `_write_chunk`, 30 in `_read_chunk`, 50 in
  `_clear_chunk`, each spanning up to base+6), plus fixed values 17/18/19/26 (`_write_chunk`),
  37/38/39/46/47/48 (`_read_chunk`), 57/58 (`_clear_chunk`), 60-73/80 (`_AsyBaseFramChunk`'s
  `_write`/`_read`/`clear`), 81/84 (`AsyFramChunk`/buffer-size checks), 82/85/86/87/88
  (`AsyFramTimestampedChunk`'s timestamp handling), 83 (`AsyFramManager.setup()` itself). Numeric
  overlap with other drivers' own 10-24-style ranges is fine (different `name`s once Cluster 1
  lands) — this correction only matters for FRAM's own *internal* consistency check and for
  correctly seeding Cluster 10's pass-1 inventory.
- FRAM determinism (see standing rule): `AsyFramManager` and `SGP40_Reader`'s VOC-backup chunk are
  the two real chunk-owning call sites today (see `WIRING_CONTRACT.md`) — already verified safe
  this session (both unconditional, once-only, module-level constructions). Re-confirm holds once
  this cluster's own edits land — a naming-only change shouldn't affect construction order, but
  verify rather than assume.

**Quality measure**: `FRAM_SPI`'s `uninitialized` flag renamed to `initialized` and polarity
flipped, with the exact same sentinel-returning behavior at every call site (no raise introduced —
its own docstring's "never raises except `__init__`/`setup()`" contract stays intact, matching the
correction already recorded in "Standing conventions"); its 8 non-persisted `err`/`wrn` calls
upgraded to `err_s`/`wrn_s` sharing `AsyFramManager`'s errno space (Cluster 10 assigns the exact
numbers, continuing from the corrected `10-88` range); FRAM determinism re-confirmed for every
chunk-owning construction (`fram`, `sgp_reader`, `pixel`, `notify_service`) after the naming change
lands — a naming-only change shouldn't move construction order, but this gets verified, not
assumed; **this cluster's New findings below also close**: `_check_device_id()`/`_read_status()`/
`_setup_addr_buffer()` pre-allocate their scratch buffers once (in `__init__`) instead of
reallocating on every call, matching `SCD30_I2C`'s buffer-reuse pattern and restoring the C.3
scratch-buffer rule C.3.1 already cites this file for; `lint.sh`/`typecheck.sh`/`test.sh` green; no
test dropped. `asy_uart_driver.py` itself
stays untouched this cluster (harmonize-late decision), confirmed still orphaned (zero real
callers) before deferring it again.

**External references**: Fujitsu MB85RS64V datasheet (DS501-00015, in `datasheets/fram/`) —
already read and cross-checked against Adafruit's `Adafruit_FRAM_SPI` reference driver per the
file's own docstring; re-read only if this cluster's edits touch any register/timing-dependent
behavior, which isn't expected (logging/naming only, no protocol change).

**Status**: `[x]` done.

**Executed 2026-08-08**: Implemented exactly the plan above, plus this cluster's own New findings
item below:

- **`asy_fram_manager.py`**: added `_NAME = const("FRAM")` and threaded it through
  `AsyFramManager.__init__`'s `self.pr = PrintLogHistory(history_length, debug, name=_NAME)`
  (previously constructed with no `name=` at all). `get_error_counter()`'s
  `self.pr.get_log("FRAM")` simplified to `self.pr.get_log()` (name-baking convention, matching
  Cluster 1) — `get_log()`'s own `name=None` default already falls back to `self.name`, now
  `"FRAM"`, so the returned dict's key is unchanged (`"FRAM"`), confirmed via the existing
  `errs["FRAM"][...]` test assertions all staying green with no edits needed. `FRAM_SPI` needed no
  constructor change for the name itself — it already receives `AsyFramManager`'s shared `self.pr`
  via its existing `logger=` parameter, so every chunk class (`_AsyBaseFramChunk` and its two
  subclasses) and `FRAM_SPI` itself now share one `"FRAM"`-named logger automatically.
- **`asy_fram_driver.py`'s readiness-gate rename**: `FRAM_SPI.uninitialized` → `initialized`,
  polarity flipped (`True`→not-ready becomes `False`→not-ready), at all 4 write sites (`__init__`,
  `setup()`, `verify_present()`'s failure path) and 5 read sites (`get_write_protected()`,
  `get_values()`, `set_values()`, `set_write_protected()`, `verify_present()`) — naming/polarity
  only, the sentinel-returning behavior at every guard is unchanged, matching the readiness-gate
  table's own "no behavior change" note.
- **Scratch-buffer pre-allocation** (this cluster's own New findings item, below): `_check_device_id()`/
  `_read_status()`/`_setup_addr_buffer()` now use `self._id_buf`/`self._status_buf`/`self._addr_buf`,
  allocated once in `__init__` (the last one sized 3 vs 4 bytes from `max_size`, exactly as the old
  per-call logic did) instead of a fresh `bytearray` on every call — matching `SCD30_I2C`'s
  buffer-reuse pattern. Safe because every real call path reaches these three methods only while
  holding `FRAM_SPI`'s own `asy_lock` (via the caller's `async with fram:`, or `verify_present()`'s
  own explicit acquire) — confirmed by tracing every call site, not assumed.
- **Persisted logging upgrade**: of `FRAM_SPI`'s 15 total `err()`/`wrn()` call sites (8 distinct
  message categories, some repeated verbatim across methods — corrected count from this session's
  full read, the plan's own "8 calls" phrasing meant distinct categories, not call sites), the 12
  call sites forming those 8 categories that are genuinely actionable hardware-fault signals (WEL
  didn't set ×2/didn't clear ×1, write-protect readback mismatch, device-not-initialized ×5,
  invalid-address-range ×2, verify_present() lock-timeout) were upgraded to `err_s()`/`wrn_s()`,
  sharing `AsyFramManager`'s errno space and continuing sequentially from where its own range ends:
  `errno=89-97` (not-initialized ×5 across the 5 guarding methods, invalid-range ×2, readback
  mismatch, lock-timeout), `wrnno=81-83` (WRDI-stuck-after-retry, WEL-didn't-set-in-`_write()`,
  WEL-didn't-set-in-`set_write_protected()`). The remaining 3 call sites ("FRAM currently write
  protected" and "FRAM access not locked!" ×2) were deliberately left on plain, non-persisted
  `err()`/`wrn()` — routine/expected outcomes and a caller-contract violation respectively, not
  hardware faults, matching the plan's own "genuinely actionable" framing. `FRAM_SPI.__init__`'s
  `logger` parameter is now typed `PrintLogHistory` (was the narrower `PrintLog`), a real, required
  change since `err_s()`/`wrn_s()` only exist on that subclass — every real production caller
  (`AsyFramManager`) already passes a `PrintLogHistory` instance, so this is a type-hint correction
  matching existing behavior, not a functional change.
- **FRAM determinism re-confirmed**: re-checked `fram`/`sgp_reader`/`pixel`/`notify_service`
  construction order in `improved-quality/sensortask-wozi.py` after landing the above — all four
  remain unconditional, once-only, module-level constructions; the naming/logging changes here
  touch no construction-order-relevant code path.
- **Test suite**: `tests/test_asy_fram_driver.py` rewritten section-by-section — every
  `fram.uninitialized` assertion flipped to `fram.initialized` (with polarity inverted to match),
  `logger=PrintLog()` call sites switched to `logger=PrintLogHistory()` (required by the new type
  hint), and a stale comment claiming "`FRAM_SPI` never calls the subclass-only `err_s()`/`wrn_s()`
  methods" corrected (it now does). 13 new tests added, dedicated to the persisted-logging paths:
  one per new `errno`/`wrnno` (before-setup ×5 combined via the 5 guarding methods' shared message,
  invalid-range ×2, readback mismatch, WEL-related ×3, lock-timeout folded into the existing bounded-
  wait test instead of a new ~1s-duplicate test) plus one confirming the two deliberately-excluded
  message categories still produce zero persisted history. Final: 59/59 passing (up from 46).
  `tests/test_asy_fram_manager.py` needed one call-site fix (`manager.fram.uninitialized = True` →
  `manager.fram.initialized = False`, at the one place a test reaches into `FRAM_SPI` internals to
  simulate the chip going away mid-run) — traced the resulting errno sequence by hand to confirm the
  new `FRAM_SPI`-level errnos (89-97) interleaved into the same bounded 10-entry history don't evict
  the chunk-level errno the test asserts on; confirmed with a real run, not just the trace: 96/96
  passing, no assertion needed changing. `lint.sh`/`typecheck.sh`/`test.sh` all green across the
  whole suite (0 new findings; two `mypy` "Missing return statement" false positives on two new
  tests' `async with fram: return await ...` pattern fixed by matching the file's own established
  `ok = await ...; return ok` shape used everywhere else in this file); no test dropped.

**Incidental finding, not fixed here**: the "Standing conventions" readiness-gate table (above)
lists `SPIDevice` (`asy_spi_driver.py`)'s own `uninitialized`→`initialized` rename under Cluster 4,
alongside `FRAM_SPI`'s (assigned to this cluster). Cluster 4's own executed section, however,
redefined its goal as a narrower verification-only pass ("no logging added (reverted)") and does not
mention the `SPIDevice` rename at all — it was never actually done, and Cluster 4 is already marked
`[x]` done with no note deferring it. This is exactly the kind of cross-section discrepancy the
project's "flag, don't guess" agreement calls for surfacing rather than silently fixing — out of
this cluster's own scope (`asy_spi_driver.py` isn't one of Cluster 6's files), so left for the
project owner to decide: fold into Cluster 10's harmonization pass, or treat as a small standalone
fix whenever `asy_spi_driver.py` is next touched.

**New findings (bidirectional Part C/D cross-check, 2026-08-07)**:

- **Closed, Cluster 6**: `FRAM_SPI._check_device_id()`/`_read_status()`/`_setup_addr_buffer()` each
  allocate a fresh `bytearray` on every call instead of a buffer sized once in `__init__` and
  reused — a real, checkable divergence from C.3's scratch-buffer rule, notable because C.3.1 cites
  this exact file as its only real SPI-driver example of that rule. Buffers are small (1-4 bytes),
  so impact is low-medium, but `_setup_addr_buffer()` runs on every chunk read/write via
  `asy_fram_manager.py`, so it's not a rare path. Pre-allocated once now, matching `SCD30_I2C`'s
  buffer-reuse pattern — see Cluster 6's own executed section above.
- `asy_uart_driver.py` (tracked separately, harmonize-late — the two findings below are logged now
  so they aren't lost, but stay deferred to this file's actual Cluster-10 harmonization pass):
  1. **Undocumented/unverified bus fault surface.** `asy_i2c_driver.py`'s and `asy_spi_driver.py`'s
     module docstrings each state their bus's raise-vs-sentinel contract explicitly (I2C: a real
     `OSError` always propagates; SPI: `write()`/`readinto()` never raise on rp2). `asy_uart_driver.py`'s
     docstring states nothing about whether `machine.UART`'s methods can raise `OSError` on a real
     rp2 hardware fault (framing/overrun), and no call site (`read()`/`readinto()`/`readline()`/the
     raw `uart.write()` in `_write_all()`) is wrapped in `try`/`except`. This is exactly the kind of
     gap C.3.1 instructs a reviewer to check for by name (verify per-bus, don't assume I2C's/SPI's
     shape transfers) — needs a real verification against MicroPython's rp2-port UART source before
     this file's harmonization can close, plus either exception-wrapping or an explicit, verified
     "cannot raise" docstring contract to match its siblings.
  2. **Three real architectural choices with no Part C counterpart**, to reconcile or document once
     this file is actually harmonized: (a) a single `UART(Lockable)` class merges what C.1/C.8 treat
     as two separate layers (bus primitive + per-device session) into one, with one lock — plausible
     for a point-to-point bus with no multi-device sharing, but never reconciled against C.8's
     explicit two-lock model; (b) CRC framing lives directly inside this otherwise protocol-agnostic
     bus-wrapper layer, unlike `I2C`/`SPI`, which have zero CRC awareness and leave all framing to
     the layer-2 protocol class — blurs the layer-1/layer-2 boundary C.1 establishes for the other
     two buses; (c) `cancel_read_timeout()` is a real, sensible externally-triggerable cancel for
     another coroutine's in-flight indefinite `ready()` wait, with no documented counterpart in C.9's
     timer/task/IRQ contract. None of these are bugs, but Part C currently has nothing to say about
     any of them — decide during this file's harmonization whether they become documented precedent
     (extending C.1/C.8/C.9 for a third bus type) or get restructured to match I2C/SPI's shape.

## Cluster 7 — `asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py`

**Goal**: strip manual `_NAME` arguments (name now automatic); close out Cluster 4's bus-layer
upstream-coverage verification from the caller side; re-verify FRAM determinism for
`SGP40_Reader`'s VOC-backup chunk and any `PrintLogHistoryStore` instance; German-language log
strings → English. **New, owner-approved scope**: `BMP3xx_Reader` and `SGP40_Reader` (both real
`SensorReaderConfig` subclasses, per Cluster 3's resolved setup()-ripple decision) need their
`sensortask-wozi.py` construction sites updated to `await` the new `setup()` — check first whether
either driver already defines its own async setup/init method (e.g. for hardware init) that the
inherited `SensorReaderConfig.setup()` should be unified with rather than duplicated; don't assume a
brand-new, separate call is right without checking the real file.

**All three files now read in full this session** (correcting the earlier grep-only estimates):

- **German-string count was significantly undercounted** — the original grep only searched a fixed
  word list and missed common phrases. Real counts: `asy_bmp3xx_driver.py` — "gelesen", "Daten
  gespeichert" (2, not 1). `asy_scd30_driver.py` — "gelesen", "Daten gespeichert" (2, not 1), plus
  one German *code comment* (line 300: "CO2 Sensor IRQ triggern falls es nicht läuft..."). **Owner
  decision**: English-standardization scope extends to comments too, not just logged strings —
  translate this comment as part of Cluster 7's own SCD30 work below, not deferred to Cluster 10; if
  any other German code comment turns up elsewhere in `src/` during execution, the same call applies
  there too. `asy_sgp40_driver.py` — roughly 26 German phrases (backup/restore/reset
  messages throughout `_check_storage`/`_read_sgp`/`_run_restore`/`_run_backup`), not 13. Re-sweep
  properly (read the whole file, not a fixed grep word list) when each file's cluster actually
  executes — don't trust the old counts as a checklist.
- Every `Timer.init()` `except OSError` site in these three files (`start_timer()` ×3, one per
  driver) keeps its non-persisted `pr.err()` logging as-is — see the cross-cutting confirmation in
  "Standing conventions" above — but widen the clause to `except (OSError, MemoryError) as e:`, the
  resolved defensive-catch decision.
- Bus-layer surface confirmed exactly matches Cluster 4's inventory: all three protocol classes
  (`BMP3XX_I2C`, `SCD30_I2C`, `SGP40_I2C`) call `I2CDevice`'s methods only from inside their own
  `try`-wrapped `_read_*`/`_init_*`/get-set-forward methods at the Reader layer — no call site found
  outside that wrapping, closing Cluster 4's upstream-coverage check from this side (final
  confirmation still wants Cluster 4's own file in view too, per that cluster's own note).

**Existing errno/wrnno inventory, confirmed accurate by the full read** (feeds Cluster 10's
pass-1): BMP3xx `errno=10-21` (10=init, 11-14=config read/write, 15-20=oversampling/filter
forwards, 21=trigger-interval); SCD30 `errno=10-24` (10=init, 11=read, 12=stop-continuous-
measurement, 13-24=per-field get/set forwards in pairs); SGP40 `errno=10-18` + `wrnno=10-14`
(10=init, 11-12=config, 13-18=backup read/write/serialize, `wrnno`=backup-missing/stale
conditions). All three already follow the shared `errno=10`="init failed" convention — nothing to
fix there, just confirm it still holds once Cluster 6's FRAM errno range is finalized (no
accidental overlap, though they're different `name`s/logger instances so numeric overlap across
drivers is fine by design — only *within* one driver's own numbering does it matter).

**Quality measure**: manual `_NAME` arguments stripped from every `err_s`/`wrn_s`/`evt`/`one`/`all`/
`get_log()` call site in all three files; every German string *and* the one known German code
comment (BMP3xx: "gelesen", "Daten gespeichert"; SCD30: same two strings plus the line-300 comment —
comments confirmed in scope, owner decision; SGP40: ~26 phrases across
`_check_storage`/`_read_sgp`/`_run_restore`/`_run_backup`) replaced with an equivalent English
version, no meaning lost; each driver's one `start_timer()` `except OSError` widened to
`except (OSError, MemoryError) as e:` (resolved defensive-catch decision, see "Standing
conventions"); Cluster 4's bus-layer upstream-coverage
check closed from this side (every `I2CDevice` call confirmed wrapped and logged at this layer);
FRAM determinism re-confirmed for `SGP40_Reader`'s VOC-backup chunk; each driver's existing
errno/wrnno ranges (BMP3xx 10-21, SCD30 10-24, SGP40 10-18/10-14) re-confirmed internally consistent
after the string changes (numbering itself doesn't move, only string content does); **this cluster's
New findings below also close**: `SCD30_Reader.stop_timer()`/`stop_continuous_measurement()`
reordered to sit with the other Starters, matching BMP3xx/SGP40's D.15 placement;
`asy_sgp40_driver.py::_read_word_from_command()`/`get_raw()` reuse a pre-sized buffer instead of
reallocating on SGP40's 1 Hz cadence; `asy_sgp40_driver.py::_reset()` nests the shared bus lock
(`async with sgp40.i2c_device as i2c:`) like every other SGP40 transaction, closing the C.8
locking gap; `lint.sh`/
`typecheck.sh`/`test.sh` green; no test dropped.

**External references**: Bosch BMP388/BMP390 datasheet, Sensirion SCD30 datasheet, Sensirion SGP40
datasheet (all in `datasheets/`, per CLAUDE.md) — already the basis for these drivers; re-read only
if any oversampling/filter/compensation/backup-timing formula is touched, which this cluster's
scope (logging/naming/language only) doesn't call for.

**Status**: `[ ]` not started. Depends on Clusters 0-4, 6. Full reads done — ready to execute.

**New findings (bidirectional Part C/D cross-check, 2026-08-07)**:

- `asy_scd30_driver.py`: `SCD30_Reader.stop_timer()`/`stop_continuous_measurement()` are placed
  after every getter/setter (near the file's end) instead of with the other Starters, unlike
  `BMP3xx_Reader`/`SGP40_Reader`, which both correctly place `stop_timer()` immediately after
  `get_timer_starters()` per D.15. A real, checkable D.10/D.15 divergence between SCD30 and its two
  sibling drivers — pure reorder, no behavior risk, but worth fixing alongside this cluster's own
  D.15 pass (`stop_continuous_measurement()` itself belongs in Setters/Others regardless, per
  D.15's own clarified `stop_*` wording — see `SPECIFICATION.md` D.15).
- `asy_sgp40_driver.py::_read_word_from_command()`/`get_raw()` allocate a fresh `bytearray`/list on
  every call on SGP40's fixed 1 Hz cadence, instead of reusing pre-sized buffers the way
  `SCD30_I2C` does with its own single `self._buffer` — real, indefinite per-second GC churn (D.4).
  A second small pre-allocated buffer swapped by reference (instead of `get_raw()`'s
  `self._command_buffer = bytearray(2)` reallocation) would close this cheaply.
- `asy_sgp40_driver.py::_reset()` (the I2C general-call/reset broadcast) only acquires
  `SGP40_DeviceSession`'s own device-session lock — it reaches directly into
  `sgp40.i2c_device.i2c.writeto(0x00, b"\x06")` rather than going through
  `async with sgp40.i2c_device as i2c:`, so the shared *bus* lock (C.8's lock 1) is never held for
  this call, unlike every other SGP40 transaction in the file. Since a general call is explicitly
  meant to affect every device on the bus, a concurrent transaction from another sensor sharing the
  same physical I2C bus could genuinely interleave with it. Real C.8 locking gap, worth fixing as
  part of this cluster's own pass over the file (nest the bus lock the same way every other method
  here already does).

## Cluster 8 — `asy_wifi_service.py`, `asy_ntp_client.py`

**Goal**: strip manual `_NAME` arguments; widen this cluster's six `Timer.init()` `except OSError`
sites (`asy_wifi_service.py` ×3, `asy_ntp_client.py` ×3) to `except (OSError, MemoryError) as e:`,
the resolved defensive-catch decision (see "Standing conventions" above) — logging behavior
unchanged, only the caught exception types widen; close out Cluster 5's `asy_udp_socket.py`/
`asy_dns_client.py` upstream-coverage verification from the caller side; German-language log
strings → English.

**Both files now read in full this session** (correcting the earlier grep-only estimates):

- `asy_wifi_service.py`'s German-string count was significantly undercounted (the original grep
  only searched a fixed word list) — real count is roughly 30+ phrases throughout (connection
  state transitions, hotspot messages, LED diagnostics), not 4. Re-sweep properly when this
  cluster executes.
- **`asy_wifi_service.py` has a deliberate, already-documented two-tier logging design — don't
  flatten it into uniform `err_s()` calls.** Its own module docstring states this explicitly:
  "'Attempt' operations persist a real errno via `self.pr.err_s()` and set `self.hw_op_failed`...
  routine state observations degrade silently via `self.pr.err()` instead." Confirmed in the code:
  every `wlan.status()`/`ifconfig()`/LED on-off-toggle observation call is intentionally
  non-persisted (matches "observation-tier" per its own comments), while every real connection
  *attempt* (mode switch, hotspot activate, STA connect, disconnect) is already `err_s()` with a
  real errno. This is the same lean-vs-complete distinction the audit's own general logging rule
  already allows for ("in a sensible way") — apply it as intentional here, not as a gap.
- **Small, real finding**: `asy_wifi_service.py` line 521, `elif status == 2: # not defined by
  constant in class yet!` — a literal magic number with a comment flagging it as unfinished.
  Should become a proper named constant (e.g. `_STAT_OBTAINING_IP`), matching every other
  `network.STAT_*` branch around it.
- `asy_ntp_client.py` has **zero** German strings — already fully English, no work needed there for
  the language-standardization goal.
- FRAM determinism re-confirmed: `DNSServer` is constructed exactly once inside
  `asy_conn_time.__init__` (line 106), itself only ever instantiated once at module level — already
  verified safe earlier this session, holds under the full read too.

**Existing errno/wrnno inventory, confirmed accurate by the full read**: `asy_wifi_service.py`
`errno=11-18` (11=mode-switch, 12=hotspot-activate, 13=STA-connect-attempt, 14=STA-poll,
15-16=STA-disconnect/deactivate, 18=disconnect-timeout) + `wrnno=1-7` (1-3=missing-config per
connection phase, 4-7=WLAN status conditions); `asy_ntp_client.py` `errno=11-20` (11=missing-config,
12-13=DNS/address resolution, 14-15=NTP response validation, 16-17=retry-timer/max-retries,
19=time-calc, 18/20=missing-config-interval-fallback/give-up) + `wrnno=1-3` (callback failures:
`network_available()`, `get_dns_server()`). Both already state in their own docstrings that
`errno`/`wrnno` numbering starts at 11, leaving room below for `base_classes.py`'s own shared range
(confirmed by that file's own full read earlier this session: `errno=1-9`, `wrnno=1-2`, used by
every `SensorReader`/`SensorReaderConfig` subclass's inherited `_error_check`/`_get_dict_cfg`/
`_set_dict_cfg`/`_recover_failed_push` methods) — confirms this convention is already deliberate,
not accidental, worth carrying into Cluster 10's pass-2 taxonomy as a documented precedent.

**Quality measure**: manual `_NAME` arguments stripped from both files; the two-tier logging design
in `asy_wifi_service.py` (attempt-tier via `err_s`+`hw_op_failed` vs. observation-tier via silent
`err()`) verified still intact after the edit, not flattened — checked by rereading the file's own
module docstring against the post-edit code, not assumed; line 521's magic number replaced with a
named constant (`_STAT_OBTAINING_IP` or equivalent) matching the surrounding `network.STAT_*`
branches; ~30+ German phrases in `asy_wifi_service.py` converted to English (`asy_ntp_client.py`
needs none — already fully English, confirmed); all six `Timer.init()` `except OSError` sites
(three per file) widened to `except (OSError, MemoryError) as e:`; Cluster 5's `asy_udp_socket.py`/`asy_dns_client.py`
upstream-coverage check closed from this side; FRAM determinism re-confirmed for `DNSServer`'s
single construction inside `asy_conn_time.__init__`; existing errno/wrnno ranges
(`asy_wifi_service.py` 11-18/1-7, `asy_ntp_client.py` 11-20/1-3) re-confirmed internally consistent;
**this cluster's New findings below also close**: `_hotspot_client_absent()`/`reconnect_wifi()`'s
`Timer.ONE_SHOT` callback no longer does business logic directly — either switched to `PERIODIC`
with idempotent-safe logic, or the work moved into a `ThreadSafeFlag`-woken coroutine with a
periodic self-heal check (see finding for the fix shape) — this is the high-priority item, verify
it's actually closed, not just attempted; `asy_ntp_client.py`'s constructor reorders its
driver-specific knobs (`dns_timeout_ms`/`dns_tries`/`ntp_fetch_timeout_ms`) to precede
`max_i2c_err`, matching C.2 and `asy_wifi_service.py`'s own constructor; `asy_wifi_service.py`'s
`LEDControl(Protocol)` moves inside an `if TYPE_CHECKING:` guard, matching every other `Protocol` in
the codebase; `lint.sh`/`typecheck.sh`/`test.sh` green; no test dropped.

**External references**: none beyond the standing MicroPython network/socket/DNS-currency check
already covered by CLAUDE.md's "wedged I2C bus"/`socket.getaddrinfo()` findings (both files already
avoid the documented can't-be-timeout-wrapped traps) — re-verify no new relevant MicroPython
issue-tracker finding has landed since the last check, not a fresh investigation from scratch.

**Status**: `[ ]` not started. Depends on Clusters 0, 2-3, 5. Full reads done — ready to execute.

**New findings (bidirectional Part C/D cross-check, 2026-08-07)**:

- **High priority — real reliability gap, not just a style nit.**
  `asy_wifi_service.py::_hotspot_client_absent()` arms `hotspot_timer` as `Timer.ONE_SHOT` with
  `callback=lambda b: self.reconnect_wifi()`. `reconnect_wifi()` does real work — `Timer.deinit()`,
  attribute mutation, `asyncio.Task.cancel()` — directly inside what fires as the Timer callback,
  contradicting C.9's "never business logic inside a Timer callback" rule. This combines badly with
  two other facts already on record elsewhere in this project: (1) `SPECIFICATION.md` Part F's
  documented soft-callback-drop risk (a soft callback can be silently dropped if MicroPython's
  fixed-depth scheduler queue is full, with no exception anywhere in that chain), and (2) this is a
  `ONE_SHOT` timer, not `PERIODIC` — C.9 already flags `ONE_SHOT` as the risky choice for exactly
  this reason, since a periodic timer self-heals on its next tick but a dropped one-shot never fires
  again. Verified directly: `hotspot_timer_running` is only ever cleared by `reconnect_wifi()`
  itself or by the two other explicit call sites (`_hotspot_client_connected()`,
  `_handle_reconnect_trigger()`) — nothing periodically re-arms it. If this specific callback is
  ever silently dropped, `_hotspot_client_absent()`'s own `if not self.hotspot_timer_running:` guard
  never re-fires, and the device can be left stuck in hotspot mode indefinitely with no further
  reconnect attempt ever made — unlike `system_service.py`'s own `ONE_SHOT` sites, which have the
  hardware watchdog as a real backstop, this one has none (hotspot mode itself doesn't feed the
  watchdog the same way). Recommend either switching to `Timer.PERIODIC` with idempotent-safe
  callback logic, or keeping `ONE_SHOT` but moving the real work out of the callback into a
  `ThreadSafeFlag`-woken coroutine per C.9's standard shape, with a periodic self-heal check
  alongside it (mirroring SCD30's own IRQ self-heal task for the same class of problem). Flag this
  for attention within Cluster 8's own scope, not deferred to Cluster 10.
- `asy_ntp_client.py`'s constructor places its own driver-specific optional knobs
  (`dns_timeout_ms`, `dns_tries`, `ntp_fetch_timeout_ms`) *after* `max_i2c_err` instead of before
  it — C.2 states the order as driver-specific knobs (the same role `trigger_sec` plays), then
  `max_i2c_err`, then `cfg_path`. `asy_wifi_service.py`'s own constructor gets this right
  (`conn_fail_to_hotspot`/`led_pin`/`ext_led`/`wifi_refresh_sec`/`hotspot_time_min` all precede
  `max_i2c_err`), making this a real, checkable inconsistency between the two files this cluster
  covers together. Low/medium severity — reorder as part of this cluster's own pass.
- `asy_wifi_service.py`'s `LEDControl(Protocol)` is defined unconditionally at module level via a
  bare `try/except Exception: class Protocol: pass` fallback, instead of the `if TYPE_CHECKING:`
  guard D.6 mandates and every other `Protocol` in the codebase actually uses (`print_log.py`'s
  `_FramChunk`/`_FramManager`, `api_response.py`'s `_RequestLike`, both fully inside
  `TYPE_CHECKING`). Nothing in the codebase ever subclasses or instantiates `LEDControl` at
  runtime, so it's purely an annotation aid that should be guarded the same way its siblings are —
  real, avoidable D.6/D.10 divergence with a small but real frozen-build cost.

## Cluster 9 — `asy_neopixel_driver.py`, `asy_notification_service.py`, `system_service.py`

**Goal**: strip manual `_NAME` arguments; re-verify FRAM determinism for every `fram=`-constructed
instance here (`NeopixelDriver`, `NotificationCoordinator`, `SystemService`); confirm no German
strings remain; add `system_service.py`'s missing `_NAME` constant (see "Logging & naming scheme"
above — it's one of the files with zero identifying calls today); widen `system_service.py`'s four
`Timer.init()` `except OSError` sites to `except (OSError, MemoryError) as e:`, the resolved
defensive-catch decision (see "Standing conventions" above). **New, owner-approved scope**:
`NotificationCoordinator` (a real `SensorReaderConfig` subclass, per Cluster 3's resolved
setup()-ripple decision) needs its own `setup()` actually invoked somewhere after its existing sync
`register()`/`finalize()` staged construction — check how that interacts with the deferred
`super().__init__()` call inside `finalize()` before assuming the two mechanisms compose cleanly;
update its `sensortask-wozi.py` construction site to `await` it once the design is confirmed.

**All three files now read in full this session** (correcting the earlier grep-only estimates):

- `asy_neopixel_driver.py` — confirmed already fully compliant: consistent `_NAME`-first calls
  throughout, no German strings, no findings. Ready as-is once Cluster 1 lands.
- `asy_uart_driver.py` (read ahead of its own late harmonization pass, per the "pick up the spirit
  early" decision) — confirmed clean and consistent with every other bus-adjacent class (matches
  `asy_i2c_driver.py`/`asy_spi_driver.py`'s own "never raises except one-time setup" shape), no
  `self.pr`/logging at all (matches its own "harmonize late" scoping, nothing to add prematurely).
- `system_service.py`'s German-string count was undercounted (fixed word list missed one) — real
  count is 4: "Task wurde beendet - versuche Neustart...", "Alle Tasks laufen.", "Task Fehlerzähler
  reduziert auf", "Task Fehlerzähler über...Reboot ausgelöst!".
- **`_timer_sequencer()`'s own code comment is the source of the cross-cutting Timer/sync-context
  confirmation** already folded into "Standing conventions" above — worth noting here since this is
  the file that made it explicit: "sync Timer-callback context (no event loop), so only `pr.err()`
  is usable, not the async `err_s()`."

Task restarts only re-invoke an already-captured starter callable, never re-run `__init__` —
confirmed safe (used to verify the FRAM determinism rule earlier this session). Existing
errno/wrnno inventory, confirmed accurate by the full read: `system_service.py` `errno=1-4`
(1=NTP-sync-callback, 2=boot-signature-timestamp, 3=task-starter-failed,
4=task-error-budget-exceeded-rebooting) + `wrnno`=task-restart-per-index (`wrnno=n+1`, dynamic per
task, not a fixed small set — worth a note in Cluster 10's taxonomy since it's a different shape
than every other module's fixed wrnno list); `asy_notification_service.py` `errno=1-4`
(1=value-callback-failed, 2=threshold-config-read-failed, 3=local-time-callback-failed,
4=request_signal_cb-failed) + `wrnno=1-5`.

**Cluster 2's decision is now resolved** (option 3, backed by real precedent — `FRAM_SPI`/
`SPIDevice` already do exactly this). `asy_notification_service.py`'s `register()`/`finalize()`
buffering stays as-is — it doesn't transfer to `ConfigManager` and doesn't get replaced, since it
solves a different problem (both are forced synchronous by `sensortask-wozi.py`'s non-async
module-level caller, not by deferred construction — checked in detail, see the "Standing
conventions" readiness-gate scheme above).

**Real gap found and added to this cluster's scope while checking that**: nothing today guards
`get_dict_cfg()`/`monitor_loop()`/`get_error_counter()`/etc. against being called before
`finalize()` runs — `self.cfg_schema` doesn't exist as an attribute until `finalize()`'s deferred
`super().__init__()` call, so an early call crashes with a bare `AttributeError` deep inside
`_get_dict_cfg`, not a clean, documented error. `self._finalized` already exists and already gates
`register()`/`finalize()` themselves against double-calls — it just isn't used to gate every other
method yet. Add that guard, sentinel-based per `NotificationCoordinator`'s inherited never-raises
contract (not raising — corrected from an earlier version of this plan, see "Standing conventions").

**Quality measure**: `_NAME` args stripped from `asy_neopixel_driver.py` (a no-op confirmation —
already compliant) and `system_service.py` (a real `_NAME` constant added where none exists today);
`system_service.py`'s 4 German strings converted to English; `system_service.py`'s four
`Timer.init()` `except OSError` sites widened to `except (OSError, MemoryError) as e:`; FRAM
determinism re-confirmed for
`NeopixelDriver`/`NotificationCoordinator`/`SystemService`'s chunk-owning constructions; a real
sentinel-based guard added so `get_dict_cfg()`/`monitor_loop()`/`get_error_counter()`/etc. on
`NotificationCoordinator` fail cleanly (documented sentinel, not a bare `AttributeError`) if called
before `finalize()` runs, reusing/renaming `_finalized`; existing errno/wrnno inventories
(`system_service.py` 1-4/dynamic-per-task, `asy_notification_service.py` 1-4/1-5) re-confirmed
internally consistent; **this cluster's New findings below also close**: `monitor_loop()` either
gains a real `self._error_check()` call using the already-accepted `max_i2c_err`, or the class stops
accepting that constructor parameter — one or the other, not left silently inert (decide which
during this cluster's execution, per the finding); `system_service.py::stop_uptime_timer()`
reordered into the Starters bucket per D.15, matching `asy_wifi_service.py`/`asy_ntp_client.py`'s
own `stop_*` placement; `SystemService.__init__`'s hand-duplicated fram-vs-memory `self.pr`
selection branch extracted into one shared helper both it and `SensorReader.__init__` call;
`lint.sh`/`typecheck.sh`/`test.sh` green; no test dropped.

**External references**: none beyond what's already cited inside `asy_neopixel_driver.py` itself
(no separate hardware datasheet — the NeoPixel timing protocol is already correctly implemented and
out of this cluster's scope to touch, since this cluster is logging/naming/guard-clause work only).

**Status**: `[ ]` not started. Depends on Clusters 1-3, 6. Full reads done for all three files —
ready to execute.

**New findings (bidirectional Part C/D cross-check, 2026-08-07)** — distinct from the
already-tracked "guard against calling before `finalize()`" gap above, which is about a different
failure mode:

- `NotificationCoordinator.monitor_loop()` never calls `self._error_check()`, despite the class
  accepting and storing `max_i2c_err` and passing it into `SensorReaderConfig.__init__` via
  `finalize()`. The inherited consecutive-failure-streak machinery (`_err_cnt_internal`/
  `_error_check`, C.7) is entirely dead for this class today: a config-read failure just logs a
  warning (`wrn_s(..., wrnno=5)`) and falls back to a fixed 600s interval forever, with no
  failure-streak threshold and no path to ever signal failure to the task supervisor via this
  mechanism (a separate mechanism — the task itself raising — still applies, but that's not what
  `max_i2c_err`'s presence in the constructor implies to a caller). Either wire in a real
  `_error_check()` call in `monitor_loop()`'s own cycle, or stop accepting `max_i2c_err` in the
  constructor if it's genuinely not meaningful for this class's failure mode — decide which as part
  of this cluster's own pass, don't leave the parameter silently inert.
- `system_service.py::stop_uptime_timer()` is placed after the Getters group
  (`get_uptime`/`get_boot_signature`/`get_error_counter`) instead of grouped with the rest of the
  Starters bucket, per D.15. Both `asy_wifi_service.py::stop_counter_timer()` and
  `asy_ntp_client.py::stop_ntp_timer()`/`stop_counter_timer()` place their `stop_*` methods
  correctly — `system_service.py` is the outlier against its own siblings' established D.15
  ordering. Pure reorder, fold into this cluster's own D.15 pass.
- `SystemService.__init__` hand-duplicates `SensorReader.__init__`'s fram-vs-memory `self.pr`
  selection branch nearly verbatim (plus one extra `self.storage_pause = fram.set_pause` line in
  the fram branch), even though `SystemService` doesn't subclass `SensorReader`/
  `SensorReaderConfig` at all — so a future change to that selection logic has to be kept in sync
  by hand across two copies that have already started to diverge slightly. Worth extracting a
  small shared helper (e.g. in `print_log.py`) both call, as part of this cluster's own work on
  `system_service.py`.

## Cluster 10 — Global pass

**Goal**: style-guideline harmonization pass over `SPECIFICATION.md`'s Parts C (driver spec) and D
(`src/` checklist) — a doc-scatter cleanup already moved `DRIVER_SPEC.md`'s/`src/README.md`'s
content there verbatim and unaudited (plus everything settled in this document), so this cluster's
job is editing those Parts in place against real per-file audit findings, not producing a new
merged file; error-code convention pass 2 (assign real numbers using
the pass-1 inventory, extend `SPECIFICATION.md` Part C.7 with the running list); full
`WIRING_CONTRACT.md` study of `sensortask-wozi.py`; whole-system integration test scoping (mirrors
the real multi-module wiring shape, not just today's pairwise chains); re-confirm every
cross-cluster item closes cleanly (bus-layer/UDP/DNS-client verification, FRAM determinism,
`asy_uart_driver.py`'s deferred harmonization, and a one-time, informational check of whether
`Timer.init()` can also raise a genuine `MemoryError` distinct from the documented `OSError(ENOMEM)`
case — see "Standing conventions" above; the defensive `except (OSError, MemoryError)` widening
itself is already resolved and applied per-cluster in 7-9 regardless of this check's outcome, so
this is a documentation confirmation, not a gate; the `AsyFramManager.setup()`/`I2CDevice.setup()`
readiness-gate question itself is also already resolved — confirmed neither needs one, see the
readiness-gate table — so Cluster 10's job on that specific item is only to re-confirm the
resolution still holds after every other cluster's edits land, not to reopen it).

**Quality measure**: `SPECIFICATION.md`'s Parts C/D read as one harmonized style guideline,
incorporating every convention fixed in this audit (logging/naming, readiness-gate scheme, FRAM
determinism rule, error-code convention) with no cross-file inconsistency left unresolved; Part
C.7 carries the full errno/wrnno pass-2 numbering table, real numbers assigned per module from the
pass-1 inventory already gathered per-cluster above, with no unresolved overlap *within* any one
module's own range; `WIRING_CONTRACT.md`'s full study is complete — the Stage-1 wiring successor's
construction order, dependency graph, and every forward API note are concretely documented, not
just seeded; whole-system integration test scope is written down (which multi-module chains need
coverage beyond today's pairwise ones); every cross-cluster item listed in the Goal above is
individually reconfirmed closed, not just listed as expected to be; `lint.sh`/`typecheck.sh`/
`test.sh` green project-wide; `AUDIT_PLAN.md`/`WIRING_CONTRACT.md` are ready for deletion per their
own stated temporary-file policy, with every permanent fact already migrated into
CLAUDE.md/README.md/`SPECIFICATION.md` before deletion.

**External references**: current MicroPython/rp2-port documentation and dev-forum/issue-tracker
findings (standing per-session currency check, CLAUDE.md's own requirement); current
`pico-sdk`/`picotool` version alignment (CLAUDE.md's already-flagged, separately-tracked
`update_and_install.txt` item — cross-reference only, not this audit's own work to fix); Microdot
v2.6.2 docs (already vendored/verified — re-check only if any Cluster-10 wiring note touches
Microdot's own behavior, not expected).

**Status**: `[ ]` not started. Depends on everything.

**First real installment of this cluster's own harmonization goal, done early (2026-08-07)**: a
full bidirectional cross-check between `SPECIFICATION.md`'s Parts C/D and the entire current state
of `src/` (all 22 files, via four parallel per-group audits plus direct verification of every
highest-severity claim before acting on it). Where the code's own established pattern was sound
and Part C/D's text was incomplete, imprecise, or factually wrong about it, the guideline text
itself was corrected in place (not the code) — see `SPECIFICATION.md` Parts C.3/C.3.1/C.4.3/C.4.4/
C.5/C.5.2/C.7/C.9/D.15/F.4 for the specific fixes (log-method inventory gained `pr.err`/`pr.wrn`;
C.7's errno numbering now states `base_classes.py`'s own reserved `1`-`9`/`1`-`2` range and the
dynamic-`wrnno` variant; C.5's "three catches in `write_config()`" claim corrected to name which
method each catch actually lives in, plus two undocumented `ConfigManager` accessor groups added;
C.5.2's `isinstance`-vs-`type()` convention scoped correctly to `int` fields, fixing a wrong
worked-example citation; C.3's scratch-buffer rule scoped to raw-I/O protocol classes; C.3.1's
`FRAM_SPI` citation corrected to describe its real merged-class structure; C.4.3/C.4.4 gained two
real, previously-undocumented patterns (staged `register()`/`finalize()` construction, `callback=`
used for sanitization); C.9 gained the mode-scoped-task opt-out; D.15's `stop_*` wildcard scoped to
timer/task-lifecycle stops; F.4 broadened from an Adafruit-only rule into a real two-vendor policy
covering `voc_algorithm.py`'s opposite, keep-it-literal Sensirion-derived treatment). Where the
code itself genuinely deviated from or was missing something Part C/D correctly requires, the
finding was filed as a new action item in the relevant cluster's own section above (0, 5, 6, 7, 8,
9) rather than fixed silently here. Two genuinely open, owner-facing design questions came out of
this pass — `DNSServer`'s error-reporting ownership and the `captive_dns.py`/`asy_dns_client.py`
IPv4-validation stance split — both logged in the Open decisions log below and **both resolved by
the project owner later the same day** (own independent `"DNSSRV"` history; standardize on the
`isdigit()`-check style — see the log for the full rationale of each, already folded into Cluster
5's own Goal/Quality measure/New findings above). This doesn't close Cluster 10
itself — the pass-2 errno numbering, `WIRING_CONTRACT.md` study, and integration-test scoping below
are all still unstarted — but the harmonization half of this cluster's Goal has real, applied
content behind it now, not just a plan.

---

## Validation pipeline logs

### Completeness/consistency check log

Dedicated top-to-bottom read, checking the document against itself (not against the code — that's
the reality-check log below). Real findings, all fixed in place rather than left as notes:

1. **Direct contradiction, most significant finding**: Cluster 2's own section still read "Open
   decision needed... blocked", carrying three unresolved options, while the Open Decisions Log and
   Cluster 9 both already stated the decision was resolved (option 3). Cluster 2's text was stale —
   fixed to state the resolution directly, and its Quality measure rewritten to match the actual
   resolved design (real `async def setup()`, not just "upgrade the already-async methods").
   Discovering this also surfaced a genuine new architectural question (does the async-`setup()`
   requirement ripple into `SensorReaderConfig`/every driver?) — logged as a new open decision
   rather than silently resolved, per the standing "escalate top-level decisions" agreement.
2. **Required-vs-default inconsistency**: Cluster 3's plan (and the matching "Standing conventions"
   bullet) said `SensorReader.__init__`/`PrintLog.__init__` should gain a *required* `name: str`.
   That directly contradicted the blast-radius reasoning Cluster 1's own section had already worked
   out in detail (a required parameter breaks every existing call site the instant the cluster
   lands, unless every caller is updated in the same cluster — which the roadmap explicitly does
   *not* do, deferring that to each subclass's own cluster). Fixed both to `name: str = ""`,
   consistent with Cluster 1's already-resolved transitional-default pattern; also fixed the
   parallel `get_log()` bullet, which said it "drops its name argument" when Cluster 1's own section
   (correctly) keeps a backward-compatible override.
3. **Roadmap-table vs. per-cluster dependency mismatches** (three found): Cluster 5's own dependency
   line named Cluster 3, which isn't real (`captive_dns.py` doesn't touch `base_classes.py`) — fixed,
   replaced with the real dependency the roadmap table was also missing (Cluster 1, since `DNSServer`
   will newly import `PrintLogHistory`). Cluster 6's own dependency line omitted Cluster 0
   (`crc_checks`), present in the roadmap table — added. Cluster 9's roadmap-table row omitted
   `asy_fram_manager` (Cluster 6), even though every one of its three files takes `fram=` and its own
   Status line already correctly listed Cluster 6 — added to the table.
4. **Minor structural ambiguity**: Cluster 6's section header listed `asy_uart_driver.py` as if it
   were in scope for that cluster's actual work, when the body text (correctly) defers it to
   Cluster 10's harmonize-late pass. Fixed the header to say so explicitly.
5. **Stale process description**: the Error-code convention section said pass-1 was "largely already
   done via this session's greps" — no longer true; several grep-based estimates (German-string
   counts especially) were found significantly wrong and superseded by full file reads. Fixed to say
   so explicitly, so a future reader doesn't trust the original greps as a checklist.

Nothing else found needing a fix — the remaining cross-references (cluster roadmap table's file
lists, the readiness-gate table, the FRAM determinism callouts) were checked and are internally
consistent.

### Reality-check log

Done as one consolidated sweep (not scattered), re-verifying the document's most load-bearing
factual claims directly against the real files via targeted greps/reads, rather than trusting the
full-session reads' own recall unchecked (that trust was exactly what let the earlier grep-based
undercounts stand uncorrected for a while). One real error found and fixed; everything else checked
came back accurate:

- **Fixed**: Cluster 3 claimed "six `err_s`/`wrn_s` calls" while listing nine line numbers.
  Re-grepped `base_classes.py` directly — the real count is nine (four in `_get_dict_cfg`, three in
  `_set_dict_cfg`, two in `_recover_failed_push`), confirmed by reading the surrounding code to
  attribute each line to its method. Text fixed above, with the corrected `errno=1-9`/`wrnno=1-2`
  attribution spelled out per-line.
- **Confirmed accurate**: `get_log()`'s 8 external callers (Cluster 1) — grepped `src/`, got exactly
  the 8 files already named, no more, no fewer. `config_manager.py`'s 29 `self.pr.*` call sites
  (Cluster 2) — grepped, exact match. `system_service.py` has zero `_NAME` constant anywhere
  (Cluster 9) — grepped, confirmed. `asy_wifi_service.py` line 521's magic-number comment (Cluster
  8) — read directly, matches verbatim. `asy_fram_manager.py`'s dynamic errno mechanism (Cluster
  6) — initially looked wrong from a literal `errno=\d+` grep (which only catches literal integers,
  missing `errno=err`/`errno=err+1`-style variable-derived calls) until `_set_check_sb`/
  `_handle_status_bytes` were read directly and confirmed the claimed bases (10/30/50) are real,
  just not literal-grep-visible — a useful reminder that a quick grep can itself mislead the same
  way the earlier German-string greps did, and needs the same "read the real code" discipline
  applied to it, not blind trust either. `asy_notification_service.py`'s `_finalized` gap (Cluster
  9) — grepped, confirmed `_finalized` gates `register()`/`finalize()` but not `get_dict_cfg()`/
  `monitor_loop()`, exactly as claimed.
- **Not independently re-derived**: the German-string counts themselves (already corrected once this
  session from grep-based undercounts to full-read-based counts) were left as-is rather than
  re-counted via a fresh grep, since a quick grep is exactly the methodology that produced the
  original wrong numbers — re-trusting the already-performed full reads is more reliable here than a
  second, still-partial grep pass would be. Re-verify these for real at execution time (each
  cluster's own quality measure already says so).

### Convergence pass log

One more full top-to-bottom read, done only after the completeness and reality-check passes above
were both clear, specifically hunting for anything those two passes' narrower focus could still
have missed — internal contradictions between sections that individually looked fine, and knock-on
effects of this session's own fixes not yet propagated everywhere they touch. Two real findings,
both fixed:

1. **Self-contradiction inside Cluster 1's own text, predating this session's edits**: one bullet
   said "making `name` a required constructor arg is fine," and the very next bullet reversed that
   to "give it a default, not a bare required parameter" — without ever flagging the reversal, so a
   reader hits an apparent contradiction mid-section. The two bullets were actually answering
   different questions (positional-signature safety vs. required-ness), just phrased so they read as
   conflicting. Reworded the first bullet to state only its actual, narrower point and explicitly
   hand off the required-vs-default question to the second bullet, instead of appearing to answer it
   and then being contradicted.
2. **Knock-on effect of this pass's own Cluster 2 fix, not yet propagated to Cluster 3**: Cluster 2's
   Quality measure (fixed above) now specifies that the one `ConfigManager(...)` call site's
   `self.pr` → `name` swap happens as part of Cluster 2 itself, to keep the build green the moment
   Cluster 2 lands. Cluster 3's own text, written before that fix, still described making that same
   swap as part of Cluster 3's work — a fresh duplication/contradiction this session's own earlier
   edit introduced. Fixed Cluster 3's bullet to note the swap is already handled by Cluster 2, and
   scope Cluster 3's remaining work on that line down to only the `super().__init__(..., name=name)`
   forward, which is genuinely new work.

No further issues found on this pass — the document reads consistently top-to-bottom at this point,
including through every fix made during the completeness and reality-check passes above.

### Backward-read check log

Read the document's stated facts starting from the bottom (Open Decisions Log → Validation pipeline
logs → Cluster 10 → 9 → ... → 0 → Cluster roadmap → Standing conventions/readiness-gate table →
Definition of Done → Validation pipeline tracker) and cross-checked every fact that appears in more
than one place for agreement, independent of which direction it's read in. This check is explicitly
about non-order-dependent claims, not the clusters' own execution order (which is only ever meant to
read sensibly forwards, per the dependency graph, and isn't in scope here). Facts cross-checked:

- `base_classes.py`'s `errno=1-9`/`wrnno=1-2` range — stated in Cluster 3 and referenced from
  Cluster 8's inventory notes; both agree, and now both trace to the same freshly-reconfirmed source
  (this session's reality-check grep), not just to each other.
- `ConfigManager`'s readiness-gate resolution (async `setup()`, option 3) — stated in the Standing
  Conventions readiness-gate table (appears first, reading forward), Cluster 2's own section
  (middle), and the Open Decisions Log (appears last) all agree on the same resolution and the same
  "only *when*, not *how*" framing; the new ripple-effect open decision sits alongside it without
  reopening or contradicting the resolution itself, as its own text explicitly says.
- `NotificationCoordinator`'s `_finalized` gap and fix — stated identically in the readiness-gate
  table and in Cluster 9's own section; agree.
- `name: str = ""` (not required) for both `PrintLog.__init__` and `SensorReader.__init__` — stated
  in Standing Conventions (top), Cluster 1, and Cluster 3; all three agree after this session's fixes.
- The `Timer.init()`-`MemoryError` question and the `AsyFramManager`/`I2CDevice` readiness-gate
  question — both appear in Standing Conventions' "Cross-cutting confirmation" and again in Cluster
  10's Goal text; both places agree on which one is still open (`MemoryError`) and which is already
  resolved (the readiness gate).
- Cluster 5's real dependency (Cluster 1, not Cluster 3) — agrees between the roadmap table and
  Cluster 5's own Status line after this session's fix.

No new contradictions found on this pass — every direction-independent fact checked agrees with
itself wherever it's stated, including the ones this session's own completeness/convergence passes
already had to fix. This is expected rather than a coincidence: this check ran last, after those
fixes, specifically so it would validate the corrected state rather than rediscover the same issues.

### Post-cross-check convergence pass log (2026-08-07)

A fresh forward-then-backward read, run after the bidirectional Part C/D cross-check (Cluster 10's
first real installment, above) and after resolving its two open decisions — specifically checking
whether that batch of new material integrated cleanly into the rest of the document, not
re-litigating anything the four earlier passes above already cleared. Four real findings, all fixed
in place:

1. **Stale doc citations, three different counts for the same thing.** Cluster 0/4 and the
   "Standing conventions"/"Error-code convention" sections still cited `src/README.md section N` /
   `DRIVER_SPEC.md section N` directly — both files were converted into stubs pointing at
   `SPECIFICATION.md` Parts D/C during an earlier doc-scatter cleanup, so those citations pointed at
   unnumbered stub text. Worse, three different section counts for the same checklist were in play:
   Cluster 0's Quality measure said "sections 1-15," the Definition of Done said "full 16-section
   checklist," and the real `SPECIFICATION.md` Part D has D.0-D.16 (17 named sections, D.0 being a
   genuinely new addition not present in the original `src/README.md`). Confirmed by content-matching
   (not by assuming a numeric offset) that the old numbering maps 1:1 onto `D.N`/`C.N` — e.g. old
   "section 2's verify-upstream-caller instruction" is `D.2`'s own text verbatim, old "section 9" is
   `D.9` verbatim. Fixed every live citation across the document to point at `SPECIFICATION.md`
   Part C/D directly, by section letter+number, not at the stub files by old numbering.
2. **Quality-measure completeness gap, Clusters 5/6/7/8/9.** Each of these clusters' "New findings"
   block (added by the bidirectional cross-check) lists real, concrete action items, but none of them
   had been folded into that cluster's own Quality measure — the checklist that actually defines
   "done" for the cluster and the thing an executor would check against. Since Clusters 5-9's Quality
   measures are written as closed, exhaustive lists (unlike Cluster 0's, which has a blanket "findings
   either fixed or explicitly flagged" catch-all), a new finding filed only in prose risked being
   silently missed at execution time. Fixed by appending each cluster's own New-findings items to its
   Quality measure explicitly (the hotspot-timer fix, SGP40 bus-lock/buffer findings, FRAM buffer
   pre-allocation, SCD30 method reorder, NTP client constructor reorder, `LEDControl` `TYPE_CHECKING`
   guard, `NotificationCoordinator`'s `_error_check()` question, `system_service.py`'s reorder/DRY
   findings, and Cluster 5's `resolve_ipv4()`/`_ipv4_to_int()` items below).
3. **Stale narrative, Cluster 10's own "first installment" paragraph.** Still described `DNSServer`'s
   error-reporting ownership as "genuinely open" and didn't mention the IPv4-validation-stance
   decision at all — both were resolved by the project owner later the same session. Fixed to state
   both are resolved, with a pointer to the Open Decisions Log and to where each resolution is now
   folded into Cluster 5's own Goal/Quality measure.
4. **Minor Goal omission, Cluster 5.** The IPv4-validation-stance unification is now real,
   owner-resolved scope for this cluster's execution, but wasn't mentioned in the cluster's own Goal
   paragraph (only in "New findings"/Quality measure). Added a sentence naming it explicitly, matching
   how every other owner-resolved scope addition in this document is announced at the Goal level.

No other issues found on this pass — the Open Decisions Log, roadmap table, readiness-gate table,
and every other cross-referenced fact checked in the four earlier passes above still agree with
themselves after this batch of edits.

---

## Open decisions log

**Resolved — `captive_dns.py`'s `DNSServer` error-reporting ownership (owner decision: own
independent `"DNSSRV"`-named `PrintLogHistory`, not `asy_conn_time`'s shared `self.pr`)**: once
Cluster 5 gives `DNSServer` a real `PrintLogHistory` (already its own Goal, replacing today's bare
`print()`), it gets its own instance rather than sharing its owner's. Rationale: at the
`sensortask` wiring level, `DNSServer`'s history is expected to later fold into one combined
"Networking" REST endpoint alongside `asy_conn_time`/`asy_dns_client` (already anticipated in
`WIRING_CONTRACT.md`), so independence now is the better fit than merging streams early. Recorded
as an accepted C.7 pattern in `SPECIFICATION.md` ("owned helper" bullet).

**Resolved — `captive_dns.py`/`asy_dns_client.py` IPv4-validation stance (owner decision:
standardize on `asy_dns_client.py`'s `isdigit()`-check, no-exceptions style)**: `_ipv4_to_int()`
gets rewritten to match `_is_ipv4_literal()`'s never-raises shape as part of Cluster 5's execution;
its current callers' `ValueError` catches come out with it. Closes the D.10 cross-file
inconsistency flagged in Cluster 5's findings.

**Resolved — `ConfigManager`'s async-`setup()` ripple (owner decision: extend the pattern
upward)**: `SensorReaderConfig` gains its own `async def setup()` (same sync-`__init__`/
async-`setup()` split, one level up) that awaits `self.cfgmgr.setup()`, keeping the project-wide
readiness-gate scheme consistent rather than carving out a one-off exception for `ConfigManager`.
**Accepted consequence, scoped precisely** (see Cluster 3 for the concrete design, Clusters 7-9 for
where it lands, `WIRING_CONTRACT.md` for the wiring-level fallout): every concrete
`SensorReaderConfig` subclass's own construction site in `sensortask-wozi.py` needs an added, awaited
`await x.setup()` call — this affects `BMP3xx_Reader`/`SGP40_Reader`/`NotificationCoordinator`
(confirmed `SensorReaderConfig` subclasses, i.e. ones with a real config schema) but **not**
`SCD30_Reader`/`NeopixelDriver` (confirmed plain `SensorReader` subclasses with no `ConfigManager` at
all — see CLAUDE.md's own note on `NeopixelDriver`'s deliberate no-config-schema exception and
`WIRING_CONTRACT.md`'s note on `SCD30_Reader`'s on-sensor-only params). The bigger structural
consequence: `sensortask-wozi.py`'s current module-level construction sequence is entirely
synchronous top-to-bottom; it can no longer stay that way once any construction step needs an
`await`. This doesn't need resolving now — Stage 1's actual rewrite is out of this audit's scope —
but it must be recorded so Stage 1 isn't blindsided by it; carried into `WIRING_CONTRACT.md` below.

**Resolved**: `config_manager.py`'s `__init__`-time errors (Cluster 2) — option 3 chosen (move the
loading/validation logic into an async `setup()`), now backed by real, already-proven precedent
(`FRAM_SPI`/`SPIDevice` already use this exact sync-`__init__`/async-`setup()` split) rather than
being a speculative redesign — see "Standing conventions"'s readiness-gate scheme above for the
full, harmonized rule this now follows, including the correction that `ConfigManager` keeps its
existing sentinel-returning (never-raises) failure reporting unchanged — only *when* the work runs
moves, not *how* failure is reported.

**Resolved**: English-standardization scope (Cluster 7) — extends to code comments, not just logged
strings; see Cluster 7's own SCD30 entry.

**Resolved — `Timer.init()`'s `except OSError` sites widen to `except (OSError, MemoryError)`
(owner decision: catch defensively regardless, don't gate on proving the failure mode first)**:
every `start_timer()`/`_reboot()`/`pause_permanent_storage()` `Timer.init()` call site across
`asy_bmp3xx_driver.py`/`asy_scd30_driver.py`/`asy_sgp40_driver.py` (Cluster 7, ×1 each),
`asy_wifi_service.py`/`asy_ntp_client.py` (Cluster 8, ×3 each), and `system_service.py` (Cluster 9,
×4) widens its bare `except OSError as e:` to `except (OSError, MemoryError) as e:`; the sync-only
`pr.err()` logging inside stays unchanged (that part was already correct — no running event loop in
a `Timer`-callback context). **This corrects an earlier mistake in this document**: a prior pass
called the bare `except OSError` "correct as-is, not a gap" — wrong against CLAUDE.md's own
already-standing rule that any `OSError` catch around a call that could plausibly exhaust memory
should also catch `MemoryError`, which `Timer.init()`'s documented `OSError(ENOMEM)` alarm-pool-
exhaustion failure mode qualifies for. Whether `Timer.init()` can *also* raise a genuine
`MemoryError` distinct from that `OSError(ENOMEM)` case remains a separate, one-time, informational
verification against current MicroPython source (Cluster 10) — it doesn't gate this defensive catch
either way, cheap insurance either way.

New decisions get logged here, batched 5-10 at a time, framed as what's-to-decide/scope/
consequences, as clusters actually turn them up.
