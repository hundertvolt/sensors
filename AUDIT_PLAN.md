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

**Quality measure**: `PrintLog.__init__`/subclasses take `name: str`; `get_log()` returns the
identical dict shape as today sourced from `self.name`; every existing `tests/test_print_log.py`
test passes (extended, not dropped, for the new required parameter); no other file touched yet.

**Status**: `[ ]` not started.

## Cluster 2 — `config_manager.py`

**Goal**: implement its own `"CFGMGR_" + name` identity, add real `err_s`/`wrn_s` logging (own
`errno`/`wrnno` list — new, doesn't exist today), and the caller-side cross-reference logging
convention (the *owner* logs its own line whenever it accesses the config manager).

**Status**: `[ ]` not started. Depends on Cluster 1.

## Cluster 3 — `base_classes.py`

**Goal**: `SensorReader.__init__` gains `name`/`logger` reach-through; drop `_error_check`'s
redundant `name` parameter (verify true redundancy first); thread the config-push/pull methods
(`_set_mgr_cfg`, `_set_dict_cfg`, `_recover_failed_push`) so their `err_s`/`wrn_s` calls correctly
use the owning instance's name automatically (they already call `self.pr.*`, so this should fall
out of Cluster 1's change for free — verify, don't assume).

**Status**: `[ ]` not started. Depends on Clusters 1-2.

## Cluster 4 — `asy_i2c_driver.py`, `asy_spi_driver.py`

**Goal**: **no logging added** (reverted — see above). Verify every real caller of `I2CDevice`/
`SPIDevice` across every current sensor driver and `FRAM_SPI` genuinely wraps and logs each call
site per `src/README.md` section 2's carve-out instructions. Fix the caller if a gap is found.

**Status**: `[ ]` not started. Depends on Cluster 3. Can't fully close until Cluster 7 (the real
callers) is also in view.

## Cluster 5 — `asy_dns_client.py`, `captive_dns.py`

**Goal**: `captive_dns.py`'s `DNSServer` gets its own name/logger (proposed `"DNSSRV"`) — already
verified single-construction-safe. `asy_dns_client.py` gets no logger (reverted) — same
upstream-coverage verification as Cluster 4, against `asy_ntp_client.py` (Cluster 8).

**Status**: `[ ]` not started. Depends on Cluster 0 (asy_udp_socket), Cluster 3.

## Cluster 6 — `asy_fram_driver.py`, `asy_fram_manager.py`, `asy_uart_driver.py`

**Goal**: thread the shared `"FRAM"` name through the existing `logger=` sharing mechanism (already
precedented, just needs identity). Re-verify the FRAM determinism rule against every current
chunk-owning caller (see Cluster 7/9 — cross-cluster). `asy_uart_driver.py`: read for style ideas
now, defer its formal pass to Cluster 10 per the "harmonize late" decision.

**Status**: `[ ]` not started. Depends on Clusters 1, 3-4.

## Cluster 7 — `asy_bmp3xx_driver.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py`

**Goal**: strip manual `_NAME` arguments (name now automatic); close out Cluster 4's bus-layer
upstream-coverage verification from the caller side; re-verify FRAM determinism for
`SGP40_Reader`'s VOC-backup chunk and any `PrintLogHistoryStore` instance; German-language log
strings → English (confirmed count: `asy_sgp40_driver.py` ×13, `asy_bmp3xx_driver.py`/
`asy_scd30_driver.py` ×1 each).

**Status**: `[ ]` not started. Depends on Clusters 0-4, 6.

## Cluster 8 — `asy_wifi_service.py`, `asy_ntp_client.py`

**Goal**: strip manual `_NAME` arguments; close out Cluster 5's `asy_udp_socket.py`/
`asy_dns_client.py` upstream-coverage verification from the caller side; German-language log
strings → English (confirmed count: `asy_wifi_service.py` ×4).

**Status**: `[ ]` not started. Depends on Clusters 0, 2-3, 5.

## Cluster 9 — `asy_neopixel_driver.py`, `asy_notification_service.py`, `system_service.py`

**Goal**: strip manual `_NAME` arguments; re-verify FRAM determinism for every `fram=`-constructed
instance here (`NeopixelDriver`, `NotificationCoordinator`, `SystemService`); confirm no German
strings remain (none found in `asy_neopixel_driver.py` this session; `system_service.py` had 3 —
recheck).

**Status**: `[ ]` not started. Depends on Clusters 1-3, 6.

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

None outstanding right now — every top-level decision surfaced during pre-audit planning is
resolved and captured above. New ones get logged here, batched 5-10 at a time, framed as
what's-to-decide/scope/consequences, as clusters actually turn them up.
