# src/ Audit — Master Action List

Working document for the full `src/` audit (see BACKLOG.md's "Planned: full `src/` audit" for the
original goals/lenses this expands on). **Temporary**: this file is deleted once the project owner
agrees the audit is finished — it is not meant to persist the way CLAUDE.md/README.md/DRIVER_SPEC.md
do. Anything here that turns out to be a permanent fact worth keeping migrates into those docs
before this file goes away, matching BACKLOG.md's own "resolved items get pruned, not left to rot"
rule.

This file is written to be self-contained: everything decided during the pre-audit planning
conversation is captured here directly, not referenced back to that conversation.

Companion file: `WIRING_CONTRACT.md` (also temporary) — the `improved-quality/sensortask-wozi.py`
instantiation-order/dependency study. Seeded now with what's already been found; the deep study
happens at Cluster 10.

**Kickoff-procedure status** (BACKLOG.md's "Required kickoff procedure," steps 1-9): steps 1-2 done
from the start; **step 3 ("read the actual project files — every current `src/` file... not just
the docs describing them") is now genuinely complete** — every file in `src/` plus
`improved-quality/sensortask-wozi.py` has been read in full this session, not just grepped.
Steps 4/7/8 (the action list itself, goals, quality measures) are what this document is; step 9
(reality-check against the actual code) has already surfaced and corrected real findings throughout
(see each cluster's own notes) rather than being a final rubber-stamp pass. Step 5 (a dedicated
second validation pass over the whole list) has happened incrementally through this session's many
rounds of revision, not as one separate, discrete pass — worth keeping in mind if a future session
wants that as an explicit, final check before step 10's close-out.

## Status legend

`[ ]` not started · `[~]` in progress · `[x]` done · `[?]` blocked on an owner decision (see
"Open decisions" at the bottom of that cluster's section)

---

## Definition of Done (whole audit)

The audit is finished when, for every file in `src/`:

1. It conforms to the eventual consolidated style guideline (the planned successor to
   `src/README.md`'s checklist + `DRIVER_SPEC.md` — see Cluster 10). Until that guideline exists,
   "done" means passing `src/README.md`'s full 15-section checklist plus every convention fixed in
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

- `PrintLog.__init__` gains a required `name: str`, auto-prepended inside `err`/`wrn`/`one`/`evt`/
  `all`/`err_s`/`wrn_s`. `get_log()` drops its `name` argument, reads `self.name` internally, keeps
  returning the exact same `{name: {...}}` dict shape every existing caller already depends on
  (hard compatibility constraint — e.g. `sensortask-wozi.py`'s `fram_err_log["FRAM"]["ErrCount"]`
  must keep working unchanged).
- `base_classes.py`'s `SensorReader.__init__` gains `name: str` (currently missing entirely — only
  `SensorReaderConfig` has it, and only for the config filename) and an optional
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
  Verified against `DRIVER_SPEC.md` section 3 ("layer 2... raises on any real failure — this is the
  layer that does *not* return sentinels") and section 7 ("a per-field get/set forward... always
  logs on failure"): every real bus fault already surfaces to and gets logged by exactly one
  upstream owner (the `*_Reader`). Adding bus-layer logging would duplicate the same event under a
  second tag with no new information. Cluster 4's real work is the inverse of what was originally
  planned: **verify** every current `I2CDevice`/`SPIDevice` call site is genuinely wrapped by an
  upstream `try/except` (per `src/README.md` section 2's own standing instruction for this exact
  carve-out — "verify, don't assume, that every upstream caller closes the gap"), and fix the
  *caller* if a gap is found — never add logging to the bus layer itself.
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

Pass 1 (whole-picture inventory, largely already done via this session's greps — extend as new
call sites appear): every current `errno`/`wrnno` value in every file, plus every new logging call
this audit adds (mainly `config_manager.py`'s new `CFGMGR_*` instances, plus whatever the
stricter "verify upstream" check turns up as genuine gaps elsewhere). Pass 2: assign real numbers
per module, consistent with the inventory, extending `DRIVER_SPEC.md` section 7's existing
per-driver-numbering convention and its one existing cross-module precedent (`errno=10` = init
failure). Output is a running list (lives in `DRIVER_SPEC.md` section 7, permanent, not deleted
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

**Cross-cutting confirmation, not a finding to act on**: every `Timer.init()` call site's `except OSError as e: self.pr.err(...)` (never `err_s`) is correct as-is, not a gap — confirmed via `system_service.py`'s own explicit comment on `_timer_sequencer()`: a `Timer`-callback-invoked context has no running event loop, so only the synchronous `pr.err()` is callable there at all, `err_s()` genuinely cannot be `await`ed. This pattern repeats identically across every `start_timer()`/`_reboot()`/`pause_permanent_storage()` in `asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py`, `asy_wifi_service.py` (×3), `asy_ntp_client.py` (×3), and `system_service.py` (×4) — don't "fix" any of these into persisted logging during their clusters. One separate, still-open, correctly-scoped check: whether `Timer.init()` can also raise a genuine `MemoryError` distinct from the `OSError(ENOMEM)` CLAUDE.md already documents — worth verifying against current MicroPython source once, not per-file (Cluster 10).

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
| 5 | `asy_dns_client.py`, `captive_dns.py` | asy_udp_socket |
| 6 | `asy_fram_driver.py` → `asy_fram_manager.py`; `asy_uart_driver.py` (harmonize late) | asy_spi_driver, base_classes, crc_checks, print_log |
| 7 | `asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py` | math_helpers, asy_i2c_driver, base_classes, config_manager, crc_checks, voc_algorithm, asy_fram_manager |
| 8 | `asy_wifi_service.py`, `asy_ntp_client.py` | base_classes, captive_dns, config_manager, asy_dns_client, asy_udp_socket |
| 9 | `asy_neopixel_driver.py`, `asy_notification_service.py`, `system_service.py` | base_classes, config_manager, print_log |
| 10 | Global pass | everything |

Cluster 10 covers: style-guideline consolidation (replacing `src/README.md` + `DRIVER_SPEC.md`),
error-code convention pass 2, `sensortask-wozi.py` mechanical fixes + the full `WIRING_CONTRACT.md`
study, whole-system integration test scoping, and re-checking every cross-cluster item flagged
along the way (bus-layer/UDP/DNS-client upstream-coverage verification, FRAM determinism on every
touched file).

---

## Cluster 0 — foundational, no internal dependencies

**Goal**: confirm these five files (already read in full this session) hold up against the current
conventions above and `src/README.md`'s full checklist; they were largely already mature/reviewed
before this audit started, so this is closer to re-verification than first review.

**Quality measure**: each file passes `src/README.md` sections 1-15 with findings either fixed or
explicitly flagged; `lint.sh`/`typecheck.sh`/`test.sh` stay green; no behavior change without an
explicit flag-and-ask per section 1.

| File | Status | Notes |
|---|---|---|
| `math_helpers.py` | `[ ]` | Already cited (Stull 2011, Magnus-Tetens/Sonntag 1990, ideal gas barometric formula) and range-checked; already has a full test suite (`tests/test_math_helpers.py`). Re-verify citations against current sources per `src/README.md` section 1 (standing requirement, not one-time), confirm no MicroPython-currency drift (section 9). No logging (exempt, pure computation) — no naming-scheme work here. |
| `crc_checks.py` | `[ ]` | Already cited (Sensirion CRC-8 poly 0x31/init 0xFF; CRC-16/CCITT-FALSE; CRC-32/MPEG-2), already the source of several `src/README.md` rules. Re-verify same as above. No logging (exempt). |
| `voc_algorithm.py` | `[ ]` | **Read in full this session.** Confirmed a direct, faithful port of Sensirion's fixed-point reference (variable/method names trace the C source 1:1, e.g. `_vocalgorithm__mean_variance_estimator___calculate_gamma`) — deliberately non-idiomatic by design, not a style problem to clean up. `pack_into`/`unpack_from` already catch broadly and return bool, matching the "never raises" contract. No findings beyond re-verifying the reference is still current (standing check). No logging (exempt, confirmed). |
| `api_response.py` | `[ ]` | Clean, function-based, no internal deps. One `err_s` call (line 102) currently has no name — **will be fixed automatically once Cluster 1 lands** (it already calls `reader.pr.err_s(...)`, which will carry the right name once `PrintLog` does). Can't be marked fully done until Cluster 1 closes. |
| `asy_udp_socket.py` | `[ ]` | Confirmed: every I/O method already returns its documented sentinel, never raises (`__init__` excepted, by design). No logging added (see reverted decision above). **Can't be marked fully done until Cluster 5 and Cluster 8 both close** — needs `asy_dns_client.py`/`captive_dns.py`/`asy_ntp_client.py` in view to verify the upstream-coverage claim, not just this file alone. |

**Open decisions for this cluster**: none — both partial-closure dependencies above are sequencing
facts, not decisions needing input.

**External references needed**: Stull (2011) wet-bulb paper, Sonntag (1990) Magnus-Tetens
coefficients, ideal-gas barometric formula (already cited, standard physics — re-verify constants
only), Sensirion's CRC-8 spec, CRC-16/CCITT-FALSE and CRC-32/MPEG-2 standard definitions,
Sensirion's `embedded-sgp` VOC algorithm reference (already available at the cited repo — re-check
it's still current/hasn't been re-published elsewhere), current MicroPython changelog since
whatever version each file's patterns predate (per `src/README.md` section 9).

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
  `get_log("Tasks")`). Making `name` a required constructor arg is fine (nothing outside this file
  constructs `PrintLog`/`PrintLogHistory`/`PrintLogHistoryStore` positionally in a way that would
  collide — checked `src/*.py` and `tests/*.py` directly), but `get_log()` itself must **not**
  drop its `name` parameter outright or all 8 call sites break immediately, which would blow this
  cluster's "no other file touched" boundary. Fix: keep `get_log(name: str | None = None)` as a
  **transitional backward-compatible override** — `None` (the new default for any caller not yet
  passing one) falls back to `self.name`; an explicit value still works exactly as today. Each of
  the 8 callers drops its now-redundant explicit argument as part of *its own* cluster (7, 8, 6, 9
  respectively), not as part of Cluster 1.
- Same reasoning applies to `name` on the constructors themselves: give `PrintLog.__init__` a
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

**Status**: `[ ]` not started (a full implementation was trialed and reverted this session — see
above — no code currently landed).

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
- **Real architectural fork found, needs a decision — see "Open decisions" below**: most of this
  file's genuinely important error conditions (empty defaults, an invalid default value, a
  first-time-write failure) happen inside `__init__`, which is synchronous — it cannot `await`, so
  it can never call the async `err_s`/`wrn_s`. Only the methods that are already `async def`
  (`_get_values`, `get_dict`, `get_int_values`/`get_float_values`/`get_str_values`/`get_bool_values`,
  `write_config`) can legitimately gain persisted logging without a bigger redesign.
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

**Open decision needed**: how to handle `__init__`-time failures under the "add real err_s/wrn_s
logging" goal, given `__init__` can't await:
1. **Leave them as-is** — `__init__`-time failures stay non-persisted `err`/`wrn` (console-visible,
   not counted/retrievable via `get_error_counter()`); only the already-async methods gain real
   persisted logging. Simple, zero blast radius, but the most consequential failures (a config file
   that's outright invalid at boot) are exactly the ones that stay uncounted.
2. **Defer via a buffer, drained at the first real async call** — `asy_notification_service.py`
   already has a working precedent for this exact "sync method needs to log something async" shape
   (`register()`/`finalize()` are sync, so real rejections are buffered and drained by
   `monitor_loop()` each cycle — see that file's own module docstring). `ConfigManager` could buffer
   `__init__`-time failures the same way, drained the first time any of its async methods runs. More
   consistent, but adds real state/complexity to a class that's currently simple and synchronous
   end-to-end, and — unlike `NotificationCoordinator`'s periodic `monitor_loop()` — `ConfigManager`
   has no natural periodic drain point of its own; it'd have to piggyback on whichever async method
   the owner happens to call first.
3. **Bigger redesign**: move the loading/validation logic out of `__init__` into an async `setup()`
   (matching `PrintLogHistoryStore`'s own pattern) so `__init__`-time failures become genuinely
   awaitable. Real blast radius — every `ConfigManager` construction site project-wide would need a
   `await cfgmgr.setup()` added, and `self.valid` would no longer be reliably known immediately after
   construction, unlike today. Touches far more than this one file.

**Status**: `[ ]` not started. Depends on Cluster 1. Blocked on the decision above.

## Cluster 3 — `base_classes.py`

**Goal**: `SensorReader.__init__` gains `name`/`logger` reach-through; drop `_error_check`'s
redundant `name` parameter (verify true redundancy first); thread the config-push/pull methods
(`_set_mgr_cfg`, `_set_dict_cfg`, `_recover_failed_push`) so their `err_s`/`wrn_s` calls correctly
use the owning instance's name automatically (they already call `self.pr.*`, so this should fall
out of Cluster 1's change for free — verify, don't assume); add the caller-side cross-reference
logging Cluster 2 needs (a line logged via `self.pr` whenever `_get_mgr_cfg`/`_set_mgr_cfg`
actually calls into `self.cfgmgr`, so it pairs with `ConfigManager`'s own line for a human/future-
rsyslog reader).

**Already read in full this session** — concrete plan:

- `SensorReader.__init__(self, init_data, max_i2c_err, fram=None, history_length=10, debug=None)`
  gains `name: str` (new, required — every real subclass already has its own `_NAME` to pass) and
  `logger: PrintLog | None = None` (mirrors `FRAM_SPI`'s existing `logger=` parameter shape). When
  `logger` is given, reuse it instead of constructing a fresh `PrintLogHistory`/`Store` — the
  reach-through mechanism for directly-bound sibling objects.
- `SensorReaderConfig.__init__` already takes `name: str` (currently only used for the config
  filename) — forward it to `super().__init__(..., name=name)` too, and pass it into
  `ConfigManager(cfg_path + "config_" + name + ".cfg", name, ...)` per Cluster 2's redesign
  (replacing the current `self.pr` argument).
- `_error_check(results, name, condition=True)` — the `name` parameter is used exactly once, to
  build `name + " Fehlerzähler erhöht auf"`/`name + " Maximale Fehleranzahl erreicht!"` (string
  concatenation, a different shape from every other file's `(self.name, "message")` positional
  convention — also needs fixing to match, not just simplifying). Every call site
  (`self._error_check(results, _NAME)`, one per driver's `read_loop()`) passes exactly its own
  `_NAME` — never a different name — so dropping the parameter and using `self.pr.err_s("Fehlerzähler
  erhöht auf", ...)` (name now automatic) is safe. Verify this holds for every current caller before
  dropping, per the plan's own standing rule, not just assumed from this read.
- Six `err_s`/`wrn_s` calls in `_get_dict_cfg`/`_set_dict_cfg`/`_recover_failed_push` (lines ~191,
  194, 200, 203, 280, 293, 317, 347, 360 as read this session) already call `self.pr.err_s(...)`/
  `self.pr.wrn_s(...)` with no name argument at all — these get the right name for free once
  Cluster 1 lands, no code change needed here beyond confirming it (these are exactly the methods
  Cluster 2's cross-reference logging needs a line added to, around the `self.cfgmgr`/`_get_mgr_cfg`/
  `_set_mgr_cfg` calls specifically).

**Status**: `[ ]` not started. Depends on Clusters 1-2.

## Cluster 4 — `asy_i2c_driver.py`, `asy_spi_driver.py`

**Goal**: **no logging added** (reverted — see above). Verify every real caller of `I2CDevice`/
`SPIDevice` across every current sensor driver and `FRAM_SPI` genuinely wraps and logs each call
site per `src/README.md` section 2's carve-out instructions. Fix the caller if a gap is found.

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

**Status**: `[ ]` not started. Depends on Cluster 3. Can't fully close until Cluster 7 (the real
callers) is also in view.

## Cluster 5 — `asy_dns_client.py`, `captive_dns.py`

**Goal**: `captive_dns.py`'s `DNSServer` gets its own name/logger (proposed `"DNSSRV"`) — already
verified single-construction-safe. `asy_dns_client.py` gets no logger (reverted) — same
upstream-coverage verification as Cluster 4, against `asy_ntp_client.py` (Cluster 8).

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

**Status**: `[ ]` not started. Depends on Cluster 0 (asy_udp_socket), Cluster 3.

## Cluster 6 — `asy_fram_driver.py`, `asy_fram_manager.py`, `asy_uart_driver.py`

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

**Status**: `[ ]` not started. Depends on Clusters 1, 3-4.

## Cluster 7 — `asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py`

**Goal**: strip manual `_NAME` arguments (name now automatic); close out Cluster 4's bus-layer
upstream-coverage verification from the caller side; re-verify FRAM determinism for
`SGP40_Reader`'s VOC-backup chunk and any `PrintLogHistoryStore` instance; German-language log
strings → English.

**All three files now read in full this session** (correcting the earlier grep-only estimates):

- **German-string count was significantly undercounted** — the original grep only searched a fixed
  word list and missed common phrases. Real counts: `asy_bmp3xx_driver.py` — "gelesen", "Daten
  gespeichert" (2, not 1). `asy_scd30_driver.py` — "gelesen", "Daten gespeichert" (2, not 1), plus
  one German *code comment* (line 300: "CO2 Sensor IRQ triggern falls es nicht läuft...") — worth
  a top-level question at Cluster 10 on whether English-standardization extends to comments or only
  logged strings, since the original decision ("switch to English... print strings") only said
  strings explicitly. `asy_sgp40_driver.py` — roughly 26 German phrases (backup/restore/reset
  messages throughout `_check_storage`/`_read_sgp`/`_run_restore`/`_run_backup`), not 13. Re-sweep
  properly (read the whole file, not a fixed grep word list) when each file's cluster actually
  executes — don't trust the old counts as a checklist.
- Every `Timer.init()` `except OSError` site in these three files (`start_timer()` ×3, one per
  driver) is correctly non-persisted — see the cross-cutting confirmation in "Standing
  conventions" above, don't "fix" these.
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

**Status**: `[ ]` not started. Depends on Clusters 0-4, 6. Full reads done — ready to execute.

## Cluster 8 — `asy_wifi_service.py`, `asy_ntp_client.py`

**Goal**: strip manual `_NAME` arguments; close out Cluster 5's `asy_udp_socket.py`/
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

**Status**: `[ ]` not started. Depends on Clusters 0, 2-3, 5. Full reads done — ready to execute.

## Cluster 9 — `asy_neopixel_driver.py`, `asy_notification_service.py`, `system_service.py`

**Goal**: strip manual `_NAME` arguments; re-verify FRAM determinism for every `fram=`-constructed
instance here (`NeopixelDriver`, `NotificationCoordinator`, `SystemService`); confirm no German
strings remain; add `system_service.py`'s missing `_NAME` constant (see "Logging & naming scheme"
above — it's one of the files with zero identifying calls today).

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

**Status**: `[ ]` not started. Depends on Clusters 1-3, 6. Full reads done for all three files —
ready to execute.

## Cluster 10 — Global pass

**Goal**: style-guideline consolidation (replaces `src/README.md` + `DRIVER_SPEC.md`, folds in both
plus everything settled in this document); error-code convention pass 2 (assign real numbers using
the pass-1 inventory, extend `DRIVER_SPEC.md` section 7 with the running list); full
`WIRING_CONTRACT.md` study of `sensortask-wozi.py`; whole-system integration test scoping (mirrors
the real multi-module wiring shape, not just today's pairwise chains); re-confirm every
cross-cluster item closes cleanly (bus-layer/UDP/DNS-client verification, FRAM determinism,
`asy_uart_driver.py`'s deferred harmonization, and whether `AsyFramManager.setup()`/
`I2CDevice.setup()` need a readiness gate of their own — see "Standing conventions"'s table, not
yet resolved either way).

**Status**: `[ ]` not started. Depends on everything.

---

## Open decisions log

No outstanding open decisions right now.

**Resolved**: `config_manager.py`'s `__init__`-time errors (Cluster 2) — option 3 chosen (move the
loading/validation logic into an async `setup()`), now backed by real, already-proven precedent
(`FRAM_SPI`/`SPIDevice` already use this exact sync-`__init__`/async-`setup()` split) rather than
being a speculative redesign — see "Standing conventions"'s readiness-gate scheme above for the
full, harmonized rule this now follows, including the correction that `ConfigManager` keeps its
existing sentinel-returning (never-raises) failure reporting unchanged — only *when* the work runs
moves, not *how* failure is reported.

New decisions get logged here, batched 5-10 at a time, framed as what's-to-decide/scope/
consequences, as clusters actually turn them up.
