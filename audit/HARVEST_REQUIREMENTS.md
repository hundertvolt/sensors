# Harvest requirements — pass 1 over the harvest results

Audit working file (temporary, deleted with `audit/`, OR11.a). Method: `audit/CONSOLIDATION.md`
section 7. Detail per candidate: `audit/hreq/G1.md`-`G10.md` (brief: `audit/sweeps/hreq_prompt.md`);
cross-group merge: `audit/hreq/MERGE.md`; execution routing: `audit/hreq/ROUTING.md`. Baseline: HEAD
`06eff58` (tree identical to `main` `798e5a7` outside `audit/`, the plan and `datasheets/`).

## 1. Accounting

- **Harvest**: 6,500 items, every one placed (`audit/sweeps/hreq_check.py`: 6,500/6,500, 0 unknown).
  5,547 feed candidate requirements; 953 carry no norm: drift-only 313, descriptive 239, defect
  candidate 171, stale 108, open item 82, suppression inventory 40. The last five feed the scans of
  passes 3+ (section 8 of `CONSOLIDATION.md`).
- **Candidates**: 965 (G1 HW 109, G2 TEST 74, G3 SENS/ALGO/BUS/LED 109, G4 PLAT/MEM/PERF 87, G5
  CORE/STOR/XCUT/SEC 96, G6 UART/NET/REST 88, G7 TWIN/WEB 86, G8 GEN/TOOL/SCR/CI 134, G9 DOC/PAR/LIC
  101, G10 code conventions 81).

| Provenance | holds | partly | drifted | wrong | stale | unverifiable | not checked | total |
|---|---|---|---|---|---|---|---|---|
| O (owner's words) | 82 | 79 | 40 | 9 | 0 | 4 | 0 | 214 |
| O-confirmed | 68 | 35 | 18 | 0 | 1 | 0 | 4 | 126 |
| F (external fact) | 76 | 32 | 5 | 8 | 0 | 3 | 0 | 124 |
| A (session agent) | 210 | 156 | 33 | 2 | 0 | 8 | 12 | 421 |
| C (code convention) | 29 | 47 | 4 | 0 | 0 | 0 | 0 | 80 |
| **total** | **465** | **349** | **100** | **19** | **1** | **15** | **16** | **965** |

By pillar: P5 205, P4 203, P2 142, P8 79, P6 67, P3 61, P9 57, P7 55, process 44, P1 28, P10 24.
By relation to OR1-OR58: refines 350, restates 323, extends 166, new 78, conflicts or tension 48.

## 2. What the numbers say

1. **The owner's own rules drift most.** 49 of 214 owner-worded rules are drifted or wrong at HEAD
   and 79 hold only partly: rules are written once and then not applied everywhere (D.15 class order,
   the dynamic-import ban, "no warning for expected startup conditions", the derived device set, the
   `max-args` ratchet, generated code at the `src/` lint bar). Agent-worded rules hold more often
   (210 of 421), because they were mostly written next to the code that honours them.
2. **Wrong facts are doc claims the primary source contradicts** (19): `asyncio.run()`'s mechanism,
   `ENODEV` from zero-length I2C writes, timestamps to 2106 not 2037, `const()` importability, no FPU,
   `bool` not an `int` subclass, `reset_cause()` reads `WDT_RESET` for every reset, a filesystem file
   shadows a frozen module, the GPIO table, SCD30 FRC readback, SCD30 NVM reachable over REST. The
   rules around them mostly stand; their stated reasons do not.
3. **Owner decisions can be lost.** The 2026-09-13 D.15 ruling was dropped by merge `e5d2c43`; an
   agent sentence ("FRAM layout must stay identical across firmware versions") contradicted the owner
   for two months (OR56 (3)).
4. **421 rules have no owner behind them.** Most are sound local engineering; 46 conflict with an
   owner row, change behaviour against legacy, or restrict what an owner row allows
   (`ROUTING.md` task 2).
5. **Execution load**: 513 routed lines — code 298, doc 108, test 50, rule-write 19, hardware 10
   (`ROUTING.md`); 398 candidates move or add a rule to a permanent home, 68 have none today.

## 3. Big-picture additions

### 3.1 Two further pillars

| # | Pillar | Samples |
|---|---|---|
| P11 | Grounded: every behaviour-bearing claim traces to a primary source at the pinned version — datasheet page, MicroPython or upstream source line, or a measurement naming image and date — and is corrected in place when the source disagrees | CLAUDE.md standing practices, OR2, OR4, OR55, 124 F candidates, the 19 wrong facts |
| P12 | Contracts at boundaries: every interface the project cannot change in one commit has one normative text, a named owner of change and a conformance check | UART wire (Part J, C peer), REST routes and keys (OR58, OR52.a (2)), stored config keys, FRAM layout within a build (OR56 (3)), device TOML schema, `@web` tags, vendored Microdot and the stubs (`G5.093`, `G6.071`, `G4.053`) |

### 3.2 Harmonizations 24-33 (continuing `CONSOLIDATION.md` section 3)

24. **Rank of a rule**: owner words > owner-confirmed > external fact > agent text > code convention;
    a later owner row beats an earlier one. A fact beats any text about it: a claim the primary source
    contradicts is corrected in place whoever wrote it; an owner rule with a wrong stated reason keeps
    its rule and gets its reason corrected (OR13.a).
25. **Agent rules** are adopted as project rules where they hold and fit OR1-OR58; they yield where an
    owner row says otherwise; a behaviour divergence from legacy that an agent decided alone goes to
    the owner (OR48.a (2)), unless it is an adaptation with no functional loss.
26. **Legacy parity is with intent** (OR57): a legacy bug that defeats legacy's own intent is a legacy
    defect, never a behaviour to keep.
27. **Lost owner decisions are restored**, not re-asked: D.15's 2026-09-13 ruling (class member
    order, comments move with their code) returns to SPECIFICATION.md and the reorder runs under OR24.
28. **One event, one persisted entry** (OR56 (1)) makes OR35.b's newest-entry rule sufficient; no
    per-module exception.
29. **Tests take expected values from an independent source** (OR19.a (2)); D.12's "sanity bound"
    applies only where no reference value can be derived.
30. **Unreachable defensive branches** follow OR46.a: removed, except a guard of an overridable
    extension point or of a documented runtime failure (OR26.a), each listed with its reason.
31. **Hand-kept tables** stay only where the owner decided so (`buildspec.py`, the `status`/`errcount`
    catalog), each with an agreement test; everything else is derived (OR43.a (3)).
32. **Twin fakes stay independent of unit-tier fakes** (`G7.001`, owner-confirmed `b8791e6`); where the
    two tiers expose the same test API they share one convention and a contract test.
33. **The new API is the only reference** (OR58): no legacy path or spelling is kept; keys follow one
    scheme before the release, then OR52.a (2) freezes them.

### 3.3 Decided in this pass (reviewable, logged as decisions on the owner's behalf, OR2.c)

| Topic | Decision | Basis |
|---|---|---|
| Annotation quoting (`G5.002`, `G10.025`) | harmonise every file to D.6 | OR24.a (1) is later than D.6's "not mass-edited" |
| Dynamic-import ban (`G5.006`) | whole repo, as F.1's owner wording says; a site that must load a file by path is a named exception in F.1 | owner words "anywhere in this codebase" |
| First-boot missing config file, command-only schema (`G5.029`) | print only, never persisted; a corrupt file stays persisted | owner principle `8a45060` (2026-09-12) |
| CLAUDE.md flash-write rule (`G5.034`, `G9.031`) | reworded to "an accepted PUT that changed a value, or at most one repair per boot" | fact; the WiFi-backstop argument is unchanged |
| CRC empty payload (`G5.080`) | callers never pass a zero-length payload; `crc_checks.py` untouched | the "not to be modified" ruling |
| Stale as fresh (`G3.044`, `G3.058`, `G3.060`) | binds every driver; SCD30's not-ready reuse is the one named exception with its owner reason | M.1.1 req 16, `110f3db` |
| float32 effects (`G3.011`) | proven on L3; numeric ranges checked against datasheet bounds by review; no extra Unix-port build | OR39 speed, OR45.a |
| Timezone fields (`G7.080`) | stay on the System page; OR43.a's "NTP" means server and transport | display settings, not transport |
| Twin fidelity table (`G7.008`) | one row per measured hardware fact (OR17.a (1) inventory), grouped by class; fake gaps appear where such a fact exists | OR17.a (2) |
| `WaitTimeNTP = 0` (`G9.067`) | restores at once, as legacy and the owner's UI label say | OR48 functional loss, OR57 |
| SGP40 chip-identity check (`G3.039`) | adopted; the SGP40 3-word serial read is completed | adaptation, no functional loss |
| Hotspot 302 for unmatched paths (`G6.059`) | adopted | part of the captive portal (PR #53), additive |
| Apply failure marks fields Failed (`G7.074`) | adopted | visible failure, no functional loss (OR48.a (1)) |
| Zero-think-time readers, F18 (`G4.087`, `G6.087`) | in contract as load (OR49.a (1)); writer starvation at the connection ceiling is a defect, fixed by admission fairness; bench-only UART degradation is accepted if it recovers | OR49.a pass criteria |
| Combined twin faults (`G7.030`) | in OR41.a's matrix, asserting escalation (reboot), not per-driver recovery | OR18.a |
| GCC 14 CI leg (`G8.070`) | not added; the owner's manual two-chroot run covers it | owner decision 2026-09-18 |
| Test-side `gc.collect()` before a timed window (`G1.063`) | allowed; never inside it | OR55.a |
| MemoryError wording (`G4.062`, `G9.046`) | CLAUDE.md and F.2 reworded to OR26.a | OR26.a |

### 3.4 Sources not reachable

- Stull (2011) and McCamy (1992) papers behind the dew-point and CCT formulas (`G3.008`): the code's
  validity bounds stay as they are until a copy is available.
- `lib/lwip` and `lib/pico-sdk` submodules at `v1.29.0` (G4 marked lwIP-internal facts unverifiable;
  G1 fetched pico-sdk itself); cyw43-driver and micropython-lib are now fetched in the scratchpad.

## 4. Questions for the owner

Section 4 of the report in chat; answers are recorded as OR rows in PROJECT_AUDIT_PLAN.md 3.2.
