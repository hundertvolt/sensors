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
| `voc_algorithm.py` | `[ ]` | Already verified "constant-for-constant" against Sensirion's archived C reference (`embedded-sgp`). Re-verify the reference is still the right one / hasn't been superseded; confirm MicroPython currency. No logging (exempt). |
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
now, defer its formal pass to Cluster 10 per the "harmonize late" decision.

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
  upgrade to persisted logging under the "add/complete logging" rule, same errno-space as
  `AsyFramManager`'s existing `errno=60-88` range (Cluster 10 pass-2 assigns exact numbers, picking
  up where that range currently ends). All 8 calls are already inside `async def` methods (no
  `ConfigManager`-style sync-`__init__` constraint here) — nothing blocking this beyond the pass-2
  numbering itself.
- `asy_fram_manager.py`: already read most of it via earlier greps this session — `AsyFramManager`
  constructs `self.pr = PrintLogHistory(history_length, debug)` (in-memory, correctly avoiding a
  recursive FRAM-into-FRAM dependency for its own log) and already has ~35 `err_s`/`wrn_s`/`evt`/
  `one`/`all` calls with real `errno=60-88`/`wrnno=60-80` numbering — just needs `name="FRAM"`
  added to that one constructor call, nothing else.
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
strings → English (confirmed count: `asy_sgp40_driver.py` ×13, `asy_bmp3xx_driver.py`/
`asy_scd30_driver.py` ×1 each).

**Existing errno/wrnno inventory** (grepped this session, feeds Cluster 10's pass-1): BMP3xx
`errno=10-21` (grouped: 10=init, 11-14=config read/write, 15-20=oversampling/filter forwards,
21=trigger-interval); SCD30 `errno=10-24` (10=init, 11=read, 12=stop-continuous-measurement,
13-24=per-field get/set forwards in pairs); SGP40 `errno=10-18` + `wrnno=10-14` (10=init,
11-12=config, 13-18=backup read/write/serialize, `wrnno`=backup-missing/stale conditions). All
three already follow the shared `errno=10`="init failed" convention — nothing to fix there, just
confirm it still holds once Cluster 6's FRAM errno range is finalized (no accidental overlap,
though they're different `name`s/logger instances so numeric overlap across drivers is fine by
design — only *within* one driver's own numbering does it matter).

**Status**: `[ ]` not started. Depends on Clusters 0-4, 6. A full line-by-line read of these three
(large — 20-30KB each) is deferred to actual cluster execution; this entry captures what's already
known from this session's greps, not a substitute for that read.

## Cluster 8 — `asy_wifi_service.py`, `asy_ntp_client.py`

**Goal**: strip manual `_NAME` arguments; close out Cluster 5's `asy_udp_socket.py`/
`asy_dns_client.py` upstream-coverage verification from the caller side; German-language log
strings → English (confirmed count: `asy_wifi_service.py` ×4).

**Already read `asy_wifi_service.py`'s constructor in full this session** — confirmed `DNSServer`
is constructed exactly once inside `asy_conn_time.__init__` (line 106), itself only ever
instantiated once at module level (see the FRAM determinism verification already done). Existing
errno/wrnno inventory: `asy_wifi_service.py` `errno=11-18` (11=mode-switch, 12=hotspot-activate,
13=STA-connect-attempt, 14=STA-poll, 15-16=STA-disconnect/deactivate, 18=disconnect-timeout) +
`wrnno=1-7` (1-3=missing-config per connection phase, 4-7=WLAN status conditions); `asy_ntp_client.py`
`errno=11-20` (11=missing-config, 12-13=DNS/address resolution, 14-15=NTP response validation,
16-17=retry-timer/max-retries, 19=time-calc, 18/20=missing-config-interval-fallback/give-up) +
`wrnno=1-3` (callback failures: `network_available()`, `get_dns_server()`).

**Status**: `[ ]` not started. Depends on Clusters 0, 2-3, 5. A full line-by-line read of both files
is deferred to actual cluster execution.

## Cluster 9 — `asy_neopixel_driver.py`, `asy_notification_service.py`, `system_service.py`

**Goal**: strip manual `_NAME` arguments; re-verify FRAM determinism for every `fram=`-constructed
instance here (`NeopixelDriver`, `NotificationCoordinator`, `SystemService`); confirm no German
strings remain (none found in `asy_neopixel_driver.py` this session; `system_service.py` had 3 —
recheck).

**Already read `system_service.py`'s `start_and_check_tasks()`/`start_timers()` in full this
session** (used to verify the FRAM determinism rule — see above): task restarts only re-invoke an
already-captured starter callable, never re-run `__init__`, confirmed safe. Existing errno/wrnno
inventory: `system_service.py` `errno=1-4` (1=NTP-sync-callback, 2=boot-signature-timestamp,
3=task-starter-failed, 4=task-error-budget-exceeded-rebooting) + `wrnno`=task-restart-per-index
(`wrnno=n+1`, dynamic per task, not a fixed small set — worth a note in Cluster 10's taxonomy since
it's a different shape than every other module's fixed wrnno list); `asy_notification_service.py`
`errno=1-4` (1=value-callback-failed, 2=threshold-config-read-failed, 3=local-time-callback-failed,
4=request_signal_cb-failed) + `wrnno=1-5`.

**Relevant precedent for Cluster 2's open decision**: `asy_notification_service.py`'s `register()`/
`finalize()` are sync (can't call async `self.pr.wrn_s()` directly, same shape as
`config_manager.py`'s sync `__init__` problem) — already solved here via a buffer drained by
`monitor_loop()` each cycle (see that file's own module docstring). `ConfigManager` has no natural
periodic loop to drain into, so this precedent doesn't transfer mechanically, but it's the
concrete existing example option 2 of Cluster 2's decision refers to.

**Status**: `[ ]` not started. Depends on Clusters 1-3, 6. `asy_neopixel_driver.py`/
`asy_notification_service.py` full reads deferred to actual cluster execution (structure already
known from this session's greps: both consistently pass `_NAME` at every call site already).

## Cluster 10 — Global pass

**Goal**: style-guideline consolidation (replaces `src/README.md` + `DRIVER_SPEC.md`, folds in both
plus everything settled in this document); error-code convention pass 2 (assign real numbers using
the pass-1 inventory, extend `DRIVER_SPEC.md` section 7 with the running list); full
`WIRING_CONTRACT.md` study of `sensortask-wozi.py`; whole-system integration test scoping (mirrors
the real multi-module wiring shape, not just today's pairwise chains); re-confirm every
cross-cluster item closes cleanly (bus-layer/UDP/DNS-client verification, FRAM determinism,
`asy_uart_driver.py`'s deferred harmonization).

**Status**: `[ ]` not started. Depends on everything.

---

## Open decisions log

One found while fleshing out Clusters 2-9's detail:

**1. `config_manager.py`'s `__init__`-time errors, under the new "add real err_s/wrn_s logging"
goal** (Cluster 2). *What's to decide*: most of `ConfigManager`'s genuinely important error
conditions (empty schema defaults, an invalid default value, a first-time-write failure) happen
inside the synchronous `__init__`, which can never call the async `err_s`/`wrn_s` — so they can't
become persisted/counted history without either accepting that gap or a real redesign. *Scope*: one
file (`config_manager.py`), but option 3 below would touch every `ConfigManager` construction site
project-wide. *Options and consequences*:
  1. Leave `__init__`-time failures as non-persisted (console-only), only upgrade the
     already-`async def` methods (`get_dict`, `write_config`, etc.). Zero blast radius, but the
     single most consequential failure class (an invalid config file at boot) stays uncounted.
  2. Buffer `__init__`-time failures, drain them at the first real async call — `asy_notification_
     service.py`'s `register()`/`finalize()` already solves the identical "sync method, needs async
     logging" shape this way (drained by its own periodic `monitor_loop()`). `ConfigManager` has no
     equivalent natural drain point, so it'd have to piggyback on whichever async method its owner
     calls first — workable, but real added state/complexity to a currently-simple class.
  3. Move the loading/validation logic into an async `setup()` (matching `PrintLogHistoryStore`'s
     own pattern), making `__init__`-time failures genuinely awaitable. Real project-wide blast
     radius — every construction site needs an added `await cfgmgr.setup()`, and `self.valid` is no
     longer reliably known immediately after construction the way it is today.

New decisions get logged here, batched 5-10 at a time, framed as what's-to-decide/scope/
consequences, as clusters actually turn them up.
