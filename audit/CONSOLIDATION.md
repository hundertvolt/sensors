# Consolidation — pass 1 (owner requirements OR1-OR51 only)

Audit working file (temporary, deleted with `audit/`, OR11.a). Pass 1 reads only the recorded owner
requirements (PROJECT_AUDIT_PLAN.md 3.2) against each other, the plan's sections 1-4 and CLAUDE.md.
Later passes cross them with the harvest and the seeds. Nothing here starts audit work.

## 1. The big picture

**Goal** (OR1, OR5, OR44): turn a complete, working prototype into a true release: consolidated,
harmonized, "one material", with no leftovers.

**Concept** (OR44 statement): a device that runs indefinitely without user interaction once
configured, handles every issue inside, has layered fallbacks while barely reachable, has premium
code, is tested from main cases to rare corner cases, and runs lean on low-end hardware.

**Pillars** (OR44.a P1-P6, plus four candidates found in pass 1, marked new):

| # | Pillar | Carried by (samples) |
|---|---|---|
| P1 | Unattended indefinitely | OR31, OR35, OR42, OR47, CLAUDE.md WDT/backstop rules |
| P2 | Handles everything inside | OR18, OR26, OR22.a (3), OR31.a |
| P3 | Layered fallbacks | OR18.a (hardware faults escalate), OR22.a, OR31.a |
| P4 | Premium code, one material | OR24, OR28, OR36, OR46, OR51 |
| P5 | Tested main to corner cases | OR16, OR19, OR21, OR25, OR41, OR45, OR49 |
| P6 | Efficient on low-end hardware | OR39, OR40, OR46.a (3), CLAUDE.md memory rule |
| P7 (new) | Evidence survives and stays readable | OR35, L-DIAG, CLAUDE.md FRAM-forensics rule, OR38.a (2) |
| P8 (new) | One source of truth, generated not copied | OR10.a, OR43.a (3), OR45.a (1), OR51.a (4), buildgen |
| P9 (new) | Operating and testing never wear or damage | OR37, OR42, OR49.a (2), CLAUDE.md wear rule |
| P10 (new) | Extensible without edits elsewhere | OR10, OR43.a (no device count), OR44.a checklist |

## 2. Phases

| Phase | Content | Driven by |
|---|---|---|
| A. Consolidation (now) | Pass 1: requirements. Pass 2+: requirements × harvest × seeds × code. Source-access list. Owner questions, owner format. Exit: every foreseeable question answered | OR2.a/b, OR3, OR4.a, OR5, OR51.a (3) |
| B0. Baseline | Toolchain, every tier once, counts/timings/coverage recorded | plan 4.6, OR39.a (4) |
| B1. Foundations | Changes other work builds on, done first to avoid churn: legacy move to `legacy/`, errno/wrnno catalog, central log-repeat rule, compare-before-write primitive (SCD30), config objects and `max-args`, one-source website definitions, one tier ladder, `@tunable` scheme | OR32, OR28, OR35, OR42.c, OR46.b, OR43.a, OR45.a, OR30 |
| B2. File-by-file pass | Every file, four levels (micro, imports, seams, macro), all lenses, the OR51 gate, legacy-loss scan, dead code, staleness incl. non-code files | OR46.a, OR51, OR48.a, OR50, OR18, OR26, OR36 |
| B3. Test campaign | Every test reviewed (biting), fault planting, intent and interaction matrices, generated code and build chain, load limits, races, hygiene | OR16, OR19, OR21, OR22, OR23, OR25, OR37, OR38, OR41, OR49 |
| B4. Docs | History trace, drift, content rules, principles Part + one checklist, README, OR51 persistence, module procedure proven on ISL29125/BMP3xx baselines | OR13, OR14, OR15, OR27, OR44.a (3), OR10.b, OR51.a (4) |
| B5. Close of execution | Cleanup, re-verification passes until one pass is all green, hardware queue and knowledge base, twin fidelity, final report (load-test entries) | OR11, OR9.a, OR8.a, OR29, OR17, OR49.a (3) |
| C. Hardware rounds | Owner go-ahead per session. FRAM logs read first, two-image GC proof, bench boot log and trigger timestamps, twin correction, bench Pi package check | OR5.a, OR17, OR28.a, OR40.a (3), OR47.a, OR50.a (3) |
| D. Close | Plan and `audit/` deleted after the last hardware round; merge to `main` | OR11.a |

Sync points throughout B (OR6.a): commit, push, both GC stages locally, CI green (event hooks
only), register and PR status note, continue.

## 3. Harmonizations (resolved in pass 1)

1. **"Goes to the owner" during execution** (OR36.a, OR43.a, OR48.a, OR50.a) means parked and logged
   for review under OR2.c, never a stop — execution stays uninterrupted (OR2).
2. **Hardware queue**: every `REAL_HARDWARE_TEST_QUEUE.md` in OR8.a/OR17.a/OR29.a means BACKLOG's
   "Real-hardware work still owed" (fold `03f8bcf`); OR11.a's "close of the hardware session" means
   the last hardware round (OR17: several rounds).
3. **What may remain in BACKLOG at the end** (OR5.a vs OR27.a vs plan goal 4): owed hardware items,
   C-port items, and owner-deferred future goals with their reason. Nothing else.
4. **One ordered checklist** (OR10.a vs OR44.a vs OR51.a (4)): Part K is extended into the single
   ordered path for any addition (module = general case, sensor = extension); Part D's checklist and
   the OR51 gate are folded into it; Parts C and G stay reference specs its steps cite. The OR10.b
   baseline runs are OR44.a's end-to-end proof — one exercise, not two.
5. **Control arms** (OR21.a "no new ones") vs permanent structural checks (OR15.a help-vs-README,
   OR28.a catalog, OR30.a tunables, OR31.a feed site, OR40.a gc sites, OR45.a containment): the
   latter are ordinary tests of a property, not control arms — allowed.
6. **Fix path**: PQ3's "owner sign-off before observable changes" is superseded by OR12.a/OR2.c
   (proven by datasheet or spec → fixed with a regression test and logged; anything less → logged).
7. **Owner stop-points** (PQ8): none during execution (OR2); owner may look in at sync points.
8. **Branching** (PQ2): one audit branch, one PR, one merge into `main` (OR11.a); per-fix-unit
   branches dropped; autonomous commits and pushes (OR6.a); `audit/` confirmed as the apparatus.
9. **Parallel agents** (PQ9): the 2026-09-25 permission says "throughout the whole session … and
   later work", and OR1.a defines "this session" as the global audit — so it covers execution.
10. **Address parameters** (OR36.a): BMP3XX's `address` is hardware (SDO selects 0x76/0x77,
    `@limits`, set in `devices/*.toml`) and stays; ISL29125's is hard-wired 0x44
    (`asy_isl29125_driver.py:1064-1066`) and goes — its comment "exactly as BMP3XX_I2C's does" is
    wrong and goes with it.
11. **Concurrency on real hardware** (OR41.a four tiers vs OR49.a no wear): config-write concurrency
    on hardware uses unchanged and rejected writes; a persisting write stays behind
    `persistence_write`.
12. **Lazy setup** (OR47.a): FRAM chunk setup (`pr.setup()`) moves into the boot batch; a sensor's own
    re-init retry inside its task stays (P3). Where SCD30's reader shape differs from its peers, OR24
    decides.
13. **SEV1 escalation** (PQ1): no immediate escalation — no hardware runs during execution, and
    anything needing the board is parked (OR2.c).
14. **Severity scale** (PQ3) kept only for ordering the register.

## 4. Research results (pass 1)

- MicroPython: `v1.29.0` is still the latest release (`v1.30.0-preview` only) — pin unchanged.
- Microdot: `v2.7.0` (2026-09-18) exists; `ext/microdot.py` is byte-identical to `v2.6.2`. The core
  diff adds a `QUERY` method, a `Vary` header for sessions/CSRF (unused here) and f-strings — no
  fix this project needs. Decision: stay on `v2.6.2`.
- Reachability: `docs.micropython.org`, `microdot.readthedocs.io`, `sensirion.com`,
  `raspberrypi.com`, `datasheets.raspberrypi.com`, `adafruit.com` are blocked. Workaround: both
  projects' docs are read from their GitHub sources (`docs/`), which are reachable. Still missing:
  the Sensirion VOC Index application note (not in `Sensirion/gas-index-algorithm` either).
- `ConfigManager.setup()` replaces a renamed or unknown key by its default and rewrites the file
  (`config_manager.py:446-462`): any config-key or file-name change (OR24) resets that setting on a
  device updated in place.
- `digital_twin/unix_port_gc_unwedge.py` is `gc.collect()` used as a tool; its root cause is closed
  by the `unix_kbd_intr` override (Part B.14.1).

## 5. Open questions (owner format)

See the chat message of 2026-09-26; answers are recorded in PROJECT_AUDIT_PLAN.md 3.2.
