G scan, written by the lane (Wed Oct 28 07:46:01 UTC 2026)

Part G of SCAN-REST: how the audit ran, unit by unit, and in the U35 redo, its lane chains set against the real
investigations. Read-only. Range `25caf528..497b3eda`, read in `S/wt-u35int`, `arduino/` excluded. Nothing under
`/root/.claude/` or any agent transcript was opened. The redo's sources were the headlines and first sections of the 94
files in `S/u35r/handbacks_redo/`, `S/u35r/REDO.md`, `S/u35r/closing_ledger.md`, and `S/u35/lane_plan.md`'s LEAD
NOTES 105-118 and 149-367 (read by grep and line range).

How things are counted:
- **Commits** are non-merge commits. The range has 981 of them, plus 84 merges.
- **Touched** means added + removed lines, from `git log --numstat -M`, with the net change in brackets.
- **Firmware** = `src/` + `devices/` + `ext/`. **Tests** = `tests/`, `digital_twin/`, `tests_scripts/`, `tests_hardware/`,
  `tests_js/` and `mockdata/`. **Docs** = the root `*.md` files except the plan, plus the two tier READMEs.
  **Audit** = `audit/` + `PROJECT_AUDIT_PLAN.md`.
- **src NCNB** counts the non-blank lines of `src/*.py` that are not comments, the owner's measure (LEAD NOTES 363). It
  reproduces the owner's figures: 9654 at `25caf528`, 12303 at `497b3eda`.
- The scripts and their output are in `S/u35r/scan/G_work/` (`units.py`, `units_out.md`, `log.txt`).

## 1. Totals over the range

| measure | at 25caf528 | at 497b3eda | change |
|---|---|---|---|
| src NCNB lines | 9,654 | 12,303 | +2,649 (+27 %) |
| buildgen NCNB lines | 2,784 | 4,817 | +2,033 (+73 %) |
| test-tree lines (all five test dirs) | 100,112 | 216,691 | +116,579 (+116 %) |
| SPECIFICATION.md lines | 6,785 | 13,360 | +6,575 (+97 %) |
| audit/ (added lines, net) | — | ~1.55 M | 13,602 evidence files with 925 k lines at head |

Lines touched in the 981 commits:

| firmware | buildgen | website | tests | tooling | docs | audit |
|---|---|---|---|---|---|---|
| 24,965 (+3,883) | 10,055 (+2,783) | 6,692 (+298) | 257,400 (+115,446) | 23,517 (+10,577) | 26,648 (+8,114) | 1,764,153 (+1,545,271) |

- About 80 % of every touched line is audit apparatus. Without the legacy move and the datasheet submodule move, the
  share is 84 %.
- Tests to product code (firmware + buildgen + website) runs about 6 : 1.
- Ten units hold 2,398 of the 2,649 new src NCNB lines (91 %): U13 +459, U15 +395, U30 +346, U19 +215, U17 +191,
  U35-pre +174, U11 +172, U16 +156, U20 +150, U18 +140.

## 2. The course by phase

| phase | dates | commits | product lines | what it is |
|---|---|---|---|---|
| main bench work merged in | 09-25 | 16 | 8 fw | pre-audit hardware queue (W/R/G/F rows); not audit work |
| Phase A: planning and consolidation | 09-25 .. 10-05 | 611 | 0 | owner rows OR1-OR144, harvest, provenance, passes 2-4, A-L action lists, A-C merge, review package, fold; OR145, the go-ahead, opens B0 |
| B0/B1: U0-U8C2 | 10-06 .. 10-07 | 64 | src +46 NCNB (main's merge adds +4 before it) | baseline, dependency refresh, legacy move, the eight foundations |
| B2: U9-U34 | 10-07 .. 10-21 | 56 | src +2,402 NCNB | file-by-file pass, one unit commit each plus its fixes |
| B3: U35, first round | 10-21 .. 10-22 | 1 (squashed) | src +174 NCNB | 96 hand-backs, LEAD NOTES 1-118, pushed as `656fc82f` at the owner's request |
| pause and container reset | 10-23 .. 10-26 | 0 | — | usage limit on 10-23, container lost on 10-26 (LEAD NOTES 149) |
| B3: U35 redo | 10-26 18:38 .. 10-28 05:01 | 233 (+67 merges) | src +40 lines net, +23 NCNB | 94 hand-backs, LEAD NOTES 149-367, paused by the owner at 06:13 |

Phase A in detail (audit lines only, no product line):

| sub-phase | commits | audit touched (net) |
|---|---|---|
| A0 plan + owner rows | 170 | 15,174 (+9,772) |
| A1 harvest, provenance, consolidation | 34 | 67,270 (+49,228) |
| A2 allover pass 2 | 23 | 9,659 (+8,133) |
| A3 refined harvest | 30 | 4,328 (+2,890) |
| A4 / A5 passes 3 and 4 | 41 | 4,110 (+2,902) |
| A6 A-L action lists | 176 | 62,302 (+50,172) |
| A7 A-C merge, gap pass, work order | 104 | 651,079 (+514,287) |
| A8 / A9 A-C review, fold | 33 | 17,456 (+7,096) |

- A7 holds `audit/order/work_order.json` (129,166 lines; 1,909 changes, 6,571 steps) and the site index.
- A6 ran as author → verifier → corrections for each of the 38 units: "A-L U0 verification (36 FIX, 18 ADD)",
  "U8C/U8C2 verification ... 1,921 verdicts".

## 3. Units: what each delivered, and its size

Notes on the columns:
- src Δ is the src NCNB change.
- "Actions" counts the unit's planned `A.U<n>.<k>` rows in `audit/actions/U<n>.md`.
- "Evid." counts the lines in the unit's `audit/artefacts/evidence/U<n>_close/` at head.
- Lines are touched (net).
- A tag "OR<n>" marks an owner-required change from plan 3.2. Everything else is consolidation, hardening or harness.

| unit | commits | actions | delivered | src Δ | firmware | buildgen | website | tests | tooling | docs | audit | evid. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| U0/U0R | 51 | 60 | baseline record, provenance labels in comments, Microdot v2.7.0 re-vendor, tool/npm/Actions refresh, silent-failure scan rules OR147-150 | 0 | 504 (+388) | 8 | 8 | 2,405 (+2,119) | 1,235 | 1,812 (+242) | 15,203 | ENV |
| U1 | 1 | 27 | legacy tree into `legacy/` (OR32) | 0 | 18 | 2 | 6 | 130 | 34 | 629 | 38 | — |
| U2 | 1 | 26 | one global error catalog (OR28) | +76 | 655 (+77) | 158 | 0 | 764 | 0 | 177 | 52 | — |
| U3 | 2 | 15 | one central log-repeat rule (OR35) | -6 | 510 (-22) | 0 | 0 | 2,642 (+1,554) | 102 | 303 | 68 | — |
| U4 | 1 | 8 | compare-before-write, SCD30 parity restored (OR42) | +51 | 453 (+63) | 7 | 0 | 950 | 0 | 148 | 43 | — |
| U5 | 1 | 18 | config objects, max-args 8 (OR46) | -115 | 882 (-116) | 403 | 0 | 3,640 (+112) | 62 | 465 | 56 | — |
| U6 | 1 | 30 | one-source website definitions (OR43) | +13 | 72 | 262 (+160) | 2,047 (-1,341) | 2,954 (+1,758) | 401 | 303 | 4,714 | 682 |
| U7 | 1 | 26 | level ladder, runner summary block (OR45, OR15) | 0 | 0 | 0 | 0 | 4,048 (+3,232) | 1,898 (+1,278) | 596 | 252 | 171 |
| U8 | 2 | 24 | `@tunable` scheme (OR30) | +27 | 215 (+131) | 17 | 1 | 1,071 | 552 | 626 (+426) | 356 | 310 |
| U8C | 2 | 121 | `@tunable` classification of the test tiers (2,265 hits) | 0 | 0 | 0 | 0 | 3,251 (+1,203) | 0 | 565 (+495) | 854 | 793 |
| U8C2 | 1 | 51 | the classification's search gaps (846 more sites) | 0 | 0 | 0 | 0 | 423 | 2 | 148 | 95 | — |
| U9 | 1 | 11 | LED pilot | +19 | 175 | 9 | 16 | 944 (+762) | 8 | 58 | 97 | 44 |
| U10 | 2 | 47 | one name scheme, member order (OR24, OR96), shared primitives, whole-tree checks | +7 | 10,261 (+9) | 403 | 40 | 14,779 (+3,619) | 421 | 1,438 | 412 | 320 |
| U11 | 2 | 39 | core: config store, one reset path, measured uptime, supervisor task | +172 | 1,500 (+230) | 34 | 2 | 7,454 (+4,208) | 25 | 550 | 14,898 | 14,824 |
| U12 | 1 | 18 | algorithms: CRC words, codecs, VOC port pinned to Sensirion | +54 | 234 (+74) | 0 | 0 | 1,188 (+842) | 0 | 88 | 283 | 227 |
| U13 | 1 | 19 | bus layers: I2C register access, bus clear and recovery ladder (OR113), UART DMA receive ring (OR141/146) | +459 | 1,067 (+561) | 37 | 0 | 6,413 (+4,173) | 5 | 515 | 8,538 | 11,189 |
| U14 | 2 | 38 | platform facts, the 2**30 tick wrap proven | +17 | 63 | 0 | 0 | 1,643 (+1,321) | 0 | 518 (+274) | 2,538 | 3,790 |
| U15 | 2 | 44 | four drivers on the shared base and recovery ladder, SCD30 FRC readiness (OR98/99) | +395 | 1,549 (+485) | 43 | 0 | 4,532 (+3,272) | 29 | 576 (+324) | 12,247 | 13,302 |
| U16 | 2 | 23 | FRAM: tri-state read, chip watch, lost chip found | +156 | 688 (+184) | 13 | 0 | 3,894 (+2,138) | 15 | 397 | 8,457 | 14,069 |
| U17 | 1 | 33 | UART protocol: bounded pieces under a cap (OR143), flash-hold ring floor | +191 | 623 (+251) | 62 | 0 | 3,790 (+2,272) | 4 | 649 (+205) | 16,307 | 17,960 |
| U18 | 2 | 47 | network: Wi-Fi snapshot, captive DNS by query type, NTP DNS fallback (OR56) | +140 | 1,108 (+182) | 158 | 41 | 7,172 (+3,250) | 80 | 651 (+305) | 93,160 | 96,336 |
| U19 | 2 | 24 | REST: head guard, dropped connections counted, unavailable marker, generated API reference | +215 | 881 (+263) | 189 (+153) | 81 | 3,565 (+2,819) | 239 | 643 | 75,286 | 76,154 |
| U20 | 1 | 42 | buildgen: generated boot entries, controlled shutdown per system command (OR116-122), one validator | +150 | 415 (+231) | 3,804 (+1,688) | 2 | 10,948 (+6,118) | 86 | 1,197 (+545) | 42,991 | 47,034 |
| U21 | 1 | 31 | toolchain: bounded installer steps, lock, modlwip EAGAIN override (OR112), host lwIP build | 0 | 0 | 0 | 0 | 3,762 (+3,092) | 3,014 (+1,232) | 1,041 (+561) | 10,822 | 12,178 |
| U22 | 1 | 4 | LED re-check; Wi-Fi silent mode and fresh-boot settings (OR151/152); the NeoPixel 300 s rewrite (OF-75) | +44 | 267 (+67) | 20 | 0 | 2,409 (+1,987) | 8 | 393 | 35,851 | 33,705 |
| U23 | 9 | 49 | website and web tier from the definitions; 7 of its 9 commits fix or probe live-check cleanup | +19 | 74 | 203 | 4,323 (+1,495) | 9,056 (+6,600) | 680 | 599 | 81,834 | 82,936 |
| U24 | 3 | 82 | test rig: one harness that ends every task, port-true fakes | 0 | 2 | 0 | 55 | 32,158 (+5,622) | 675 | 597 | 21,823 | 23,920 |
| U25 | 7 | 74 | digital twin: port-true fakes, runner on the wiring plan, shared boot; 6 fixes (4 for port 53 and the bind capability, the tracer, a drift check) | 0 | 0 | 34 | 0 | 20,896 (+7,148) | 4,563 (+2,469) | 1,747 | 34,032 | 36,891 |
| U26 | 1 | 87 | hardware levels L3/L4: device scripts, session, guards (desk only) | 0 | 3 | 2,037 (+51) | 0 | 33,872 (+14,058) | 375 | 1,752 (+592) | 35,762 | 39,585 |
| U27 | 2 | 39 | script tooling: shared runner libraries, build chain | -14 | 49 | 186 | 4 | 11,121 (+3,867) | 3,661 (+1,231) | 967 | 28,225 | 30,430 |
| U28 | 5 | 43 | CI: one retried sync, derived matrices, datasheets submodule (OR80), job budgets | +2 | 32 | 8 | 0 | 4,718 (+1,744) | 1,777 | 677 | 39,056 | 43,823 |
| U29 | 1 | 4 | threat model, history secret scan | 0 | 2 | 0 | 0 | 718 | 120 | 147 | 8,241 | 9,492 |
| U30 | 3 | 21 | memory ladder: C-stack overflow flag and reboot, allocation-failure text at the gates, ResetErrors refused in mempause | +346 | 975 (+409) | 7 | 0 | 7,164 (+4,684) | 952 (+606) | 916 (+576) | 147,195 | 154,624 |
| U31 | 1 | 19 | timing budget: whole-ms waits, one F.3 table, loop-lag bound | +15 | 338 (+24) | 50 | 0 | 2,535 (+1,623) | 164 | 366 | 80,248 | 84,382 |
| U32 | 1 | 6 | legacy parity: named tasks, `LastTaskEnd` | +34 | 289 (+49) | 18 | 30 | 1,730 (+972) | 0 | 299 | 43,439 | 46,565 |
| U33 | 1 | 9 | docs: one owed-hardware list (no code) | 0 | 0 | 0 | 0 | 4 | 0 | 602 | 3,033 | 6,190 |
| U34 | 1 | 12 | licences: headers against their entries, an unused UDP method out | -19 | 45 (-23) | 0 | 0 | 762 | 39 | 246 | 8,431 | 11,012 |
| U35-pre | 1 | 57 | driven-clock and cancel sweeps; TimeStale (owner); blank FRAM read vs lost chip; CRC width; UART hazard mode (owner) | +174 | 544 (+242) | 1,838 (+40) | 34 | 21,810 (+7,072) | 770 | 818 (+272) | 9,384 | 8,254 |
| U35-redo | 233 | (57) | see section 4 | +23 | 464 (+40) | 45 | 2 | 15,685 (+9,683) | 1,521 | 1,093 (+521) | 45,868 | — |

What the table shows:
- **B1 is the lean part, and it is what the owner asked for.** U2-U8 are owner rows, together +46 src NCNB. U5 is -115
  and U6 is -1,341 website lines.
- **B2's firmware growth sits in hardening, not features.** The recovery ladder runs U13 → U15. The memory ladder (U30)
  adds C-stack and allocation-failure paths. U11, U16 and U17 add reset, chip-watch and bounded-piece paths. The large
  features the owner required are the UART DMA ring, the system commands, the SCD30 FRC readiness and silent Wi-Fi.
- **Audit evidence grows from U18 on.** Most units from U18 to U32 commit 24-155 k evidence lines each. B2 alone
  commits about 0.91 M of them.
- **Test volume runs ahead of the code it tests from U23 on.** U23-U27 change 0-74 src lines each, yet touch 107 k test
  lines.
- **The flake-chasing commit trains start in B2.**
  - U23: 7 fixes or probes, all on live-check cleanup.
  - U25: 6 fixes, on port 53, the bind capability and the tracer.
  - Both topics come back in U35's N15/TH1 and CE2r.
- **Topics run across units and come back.**

| topic | first in | comes back in |
|---|---|---|
| the 2**30 tick wrap | U14 ("proven") | U35-redo T4r3/b/c (666 more runs) |
| tagging tuned test literals | U8C/U8C2 (172 actions) | U35-redo N8 → N11e |
| twin port and host binding | U25 | N15/TH1 |
| coverage tracer | U15 and U25 fixes | CE2r, CEr1, CEr2 |
| caught MemoryError paths | U17 ("not caught") and U30 | F3r, UM1-UM2 |
| the NeoPixel rewrite | the OF-75 scan finding (U17), the rewrite in U22 | LC1 and the owner's stop |

## 4. The U35 redo

Scale:
- 94 hand-backs, follow-up lanes included.
- 233 non-merge commits and 67 merges in 34.5 hours.
- 219 lead notes (LN149-367).
- It came after a first round of 96 hand-backs (2026-10-21/22) that was squashed into `656fc82f`.

Net change across the redo:

| src | tests | audit | docs | tooling + buildgen |
|---|---|---|---|---|
| +214/-174, net **+40** | +12,100/-2,303 | +22,030/-990 | +696/-175 | +1,255/-213 |

- The firmware changes are small, as the owner expected: 15 lanes, each between -35 and +31 net src lines. Around them
  run about 9.7 k net test lines and 21 k audit lines.
- 20 commits only re-render, re-locate or re-dump records after a merge, because those records are keyed on line
  numbers. 9 of the lead's 14 commits are such re-renders.
- About 30 hand-backs stopped at the ~80-call seam, so the next lane in the chain resumed the same item.
- Lanes stopped by a refused command: F4c, F4c2, CRr1b, CRr2b4, CMr1b. Q35's write was refused but did not stop it.
- The run lost time to three container restarts and a harness restart: LN149, LN214, LN240, LN302.
- Owner interventions in the window:
  - LN153: no multiple-choice questions for complex topics.
  - LN163: "way too fast" (work launched before an answer).
  - LN165: "papered over the event loop fallback".
  - LN260/261 and LN278-280: budget and seam.
  - LN320: CI red "for several days".
  - LN357: "not designed self-sustaining / will never end".
  - LN358/362: the NeoPixel 5-minute check.
  - LN360: pause.
  - LN363/364: complexity and expectations.
  - LN365: no go-ahead.

### 4.1 Runaway chains (one topic over many lanes, or one investigation feeding the next)

| # | chain | lanes | commits | lines touched | what happened | delivered |
|---|---|---|---|---|---|---|
| R1 | **Bench-tier log check**: CRr2b → b2 → b3 → b4 → b5 → b6 → b7 → b8 → b9 → b10 → b11 → b12; CRr2c and CRr2d queued | 12 | 23 (+3 lead) | tests 1,758, audit 1,271, docs 93 | A new bench fixture (`no_unprovoked_log_entry`, `provokes_log`) fails a test that leaves an unmarked E/W entry. Each lane then found more bench tests whose log windows bleed: NTP mid-flight, Calibrate, ResetVOC, console, flapping, write-vs-siblings. Each fix was a wait or a widened set, and each set was then proven by bite runs. It was checked only by reading, collection and the twin; the silicon runs are owed (no hardware go-ahead in U35). | L4 test-harness text, unverified on hardware; no firmware finding |
| R2 | **Per-wiring twin tests and their cost**: CMr1 → b → c → d → e → f → g → h → i → j → k → l → m, plus WR1, N5r; CMr1n queued | 15 | 34 | tests 3,562, audit 307 | Tests now run on every device that wires a part, which multiplied the twin runs. To win the time back, the following lanes added a per-wiring dedup key (`wiring_read`, later widened by WR1), converted files to the driven clock one by one, added a Unix-port idle-poll skip (a fidelity workaround for OF-243), chased drift transients, added `DrivenTime.cancel()` and rebuilt the twin watchdog as one task. CMr1h's own attempt was measured slower and reverted. | harness and tests only; no firmware change; one D.10 duplication flagged (`_driven_modules` copies) |
| R3 | **Tagging and measuring test waits**: N8 → N10 → N11 → N11b → N11c → N11d → N11e (lineage U8C/U8C2) | 7 | 22 | tests 1,342, docs (Part N) 170 | Every tuned literal and real-time wait in the tests became a named constant with an `@tunable` tag and a measured Part N row, timed slowest-of at both GC stages under load. Each lane handed back at the seam with candidates left. | tags and Part N rows; the useful by-products were one shorter stall drain and the hazard checks at the shipped poll rates |
| R4 | **Twin-scenario harness growth**: T4r2 → T4r2b → T4r2c → T4r2d | 4 | 5 | tests 349, tooling 198 | To assert edge behaviours, the harness grew: an exact smoke-boot log check, `UnmetPremiseError`, a new runner flag `--test-defer-faults` with a 13th TestFlags field, and send buffers pinned at the host floor through SO_SNDBUF. | scenarios for a refused config write, deferred faults and a client gone mid-response; no firmware change |
| R5 | **Records walks that keep their own maintenance**: BR1 → BR1b → BR2 → BR3 → BR4 (raising.md); CO1 → CO5 (conformance.md); CEr1 → CEr2 (e51.md); CFr → CFr2 (faults.md); IN+LV (intent.md, levels.md); CRr1/b/c, CRr2a/a2 (review.md, 8,467 rows) | 20 | 58 (+9 lead re-renders) | audit about 35,000 (+3,459 lead); tests about 3,100 | Each walk classes every row of one record (raising call groups, recovery-rung cells, uncovered lines, planted faults, test rows). Each found a few defects and grew tests to close cells. All are keyed on line numbers, so every merge needed a re-render. | a few small firmware fixes (section 4.2) and some biting tests; the records themselves are temporary (owner, LN362) |
| R6 | **NTP cadence cascade**: F2r item 3 → F3r (the unsynced wait) → F5 (the synced resync) | 3 | 3 (+2 exemption drops) | F5 alone src +10/-3, tests 54; F2r and F3r's NTP parts are a few lines inside larger lanes | F2r moved the resync from tick counting to elapsed time. F5 then found that this made the resync one tick late in every cycle after the first, with the lateness building up (red: 7210, not 7200). | a fix of a fix; the net behaviour (a dropped tick no longer delays the resync) is a small real gain |
| R7 | **Event-loop exit record (OF-107)**: F4b → F4b follow-up → F4d (soft reset keeps the record) → F4e (boot-phase variant) | 4 | 5 | src 27, buildgen 39, tests 727, docs 115 | A fallback for a non-Exception BaseException leaving `asyncio.run()`. No in-tree code raises one (LN156). It was merged before the owner answered (LN163), then re-asked, and approved as option (b) (LN166). Each follow-up reordered `begin_boot()`'s decision chain again. | ResetReason 22 and two order changes; hypothetical trigger |
| R8 | **Listener-close silicon check (OF-122)**: F4a (+ third patch) → F4c (stopped) → F4c2 (stopped) → F4c3 → N10's `elf_symbols` fixes | 5 | 6 | tests 516, tooling 103, docs 176 | The fix itself is real (section 4.2). The chain is the silicon proof: pool-slot writes refused twice by the safety check, narrowed to a read-only pcb-pool comparison, plus ELF symbol tooling. | a prepared L4 check that has not run |
| R9 | **UART PieceBuffer MemoryError**: UM1 (provenance) → UM2 (catches, owner option C) → UM3 (CRC16 red, needs the owner) → UM4 (the twin UART link on the driven clock) | 4 | 14 | src 113 (net +31), tests 1,078, audit 2,079 | Started from a provenance question: "not caught" was never put side by side with OR26.a. The failure needs a ≤256 B piece allocation failing on dev, the only image with `uart_link`. The owner chose to catch it; the lane chain then grew driven-clock harness for the twin link. | three catches restored (hypothetical trigger); a CRC16 root cause for the owner; harness |
| R10 | **NeoPixel overlay** (across units): OF-75 (U17 scan, a hypothetical brownout) → U22's 300 s periodic rewrite (`01032838`) → LC1 finds its `wait_for` loses a shutdown cancel → the alarm-task fix held → the lead re-verifies against MicroPython's C source (LN358) → owner: "patches a rather hypothetical issue", "debug the Micropython sources ... out of our scope" (LN362) | 1 lane + lead | 0 merged | — | A hypothetical finding produced a hardcoded wait, and that wait produced a real but rare defect plus a structural proposal. This is the cascade the owner names in LN363. | the proposal is open; ledger item 8 |
| R11 | **CI apt mirror**: CI1 → CI1b → the lead's `dcfeacd3` (its own test's throttled servers) | 2 + lead | 4 (+1 lead) | tooling 911, tests 576, docs 153 | The problem was real (section 4.2), but the fix grew to three composite actions, a mirror-rate probe derived from the bytes left, and 16 + more tests of the probe itself (tests testing the tool). | CI green on the apt step |

### 4.2 Real investigations, each with what it delivered

| investigation | lanes | real or hypothetical | delivered |
|---|---|---|---|
| lwIP callbacks set on a listening pcb at close (OF-122) | F4a | **real upstream defect**: reproduced on the host lwIP build (tcp.c:2070 assert, exit 134); reached by the controlled shutdown and the supervisor restart (LN154) | **verified fix** on host: three patches in the toolchain's modlwip copy, with retire rule and host test; the silicon check is prepared but has not run |
| lost shutdown cancel in `wait_for` | LC1 (lead LN358) | **real but rare**: reproduced with the real asyncio on the pinned Unix port (5/5 old form, 20/20 new form); the effect is a shutdown hang, then a watchdog reset with the command not carried out | **verified fix** for `UDPSocket.ready()` (+10/-9 src, tests red first); the NeoPixel half is held for the owner |
| I2C recovery rung run twice for one episode | CO1 | real under two readers failing on one bus (forced interleaving: two clears, three recoveries) | **verified fix**, 5 src lines changed, with its test |
| typing-only runtime checks | D2S | real excess code | **simplification**: src +36/-71 (net -35) over 8 modules, plus BR4's -11 |
| the flat GET's unavailable marker read by its whole shape | F1r | latent (no field is named `error` today) | small fix and test (src net -1), matching `js/api-contract.js` |
| light-theme neutral contrast 4.16:1 | F2r item 6 | **real** (website) | fix to 4.53:1, with its pair in the token test |
| coverage tracer dies silently after a raise inside the trace callback | CE2r | **real tooling defect**: coverage silently incomplete (py/profile.c mechanism) | detection with exit 3, untraced C-stack calls; tool fix |
| Run 11's leak check too weak | T4r1 | **real**: the old values missed a planted leak 6 of 6 times | calibrated values (80 / 4.0 / 100 ms), bitten at both stages; test fix |
| twins of concurrent test processes receive each other's DNS packets | N15 → TH1 | **real**: reproduced 6 of 6 | one loopback address per process, and launchers drop a caller's `TEST_TWIN_HOST`; harness fix |
| CI apt download step timing out for days | CI1 | **real** (LN320-322) | mirror check and package cache; CI fix (see R11 for its size) |
| put-matrix ResetErrors probe flake | N4r | real (the twins boot in AP, so NTP never syncs) | test fix |
| tests leave files in the checkout and live-tier configs | N12, N14 | real | hygiene fixes with a standing guard |
| "a raise leaves lasting state" in system service and FRAM | BR2, BR3 | **hypothetical** (a MemoryError at a coroutine or copy) | four small fixes, src net +15, with tests |
| erase in the chip-loss window; notification age check under MemoryError; dev hazard-frame copies | F2r items 1, 2, 5; F2r_readiness | **hypothetical** ("nothing observable today") | small fixes; the readiness follow-up added a new `is_ready()` API only to satisfy the readiness-gate scan |
| caught MemoryError printed below the debug level | F3r | owner rule (LN146), not a finding | `PrintLog._line()`, src net +10 |
| hotspot-exit window | F1r item 1 | cannot occur | guard test only |
| 147 KB per-boot heap step | HP1 → HP2 | **not a firmware defect** (upstream's stale `child_last` plus the test's own boot chain) | **knowledge**, nothing changed |
| system_service:453 cancel path | CFr2 | the draft test was wrong; no defect | **knowledge** |
| 2**30 tick wrap over every L1 file and the twin suite | T4r3 → b → c | confirmation of U14's proof | **knowledge**: 654 L1 runs and 12 twin runs, all green, no change |
| Unix-port 1 ms poll on zero-timeout rounds | CMr1e (lead LN252) | real fidelity gap, already recorded as OF-243 | **knowledge**, plus a per-file skip helper as interim relief |
| CRC16 red | UM3 | root cause established | **nothing yet**, an owner decision |
| completion inventories | Q35, P36a | — | read-only lists (57 actions; 849 U36 rows; U36's action files found stale) |

Net verified firmware fixes from the redo:
- The modlwip listener guard (toolchain C patch).
- The UDP cancel fix.
- The I2C double-rung fix.
- The D2S simplification.
- The contrast fix.
- The NTP cadence fix, once R6's own regression is netted out.

Everything else in src/ is either hypothetical-trigger hardening (BR2/BR3, F2r items 1/2/5, R7, R9) or an owner rule
applied (F3r).

## 5. Runaway areas and chains (list)

1. **Phase A apparatus**: 611 commits and 831 k audit lines, with no product line. A7 alone is 651 k lines, mostly the
   129 k-line work order and the site index. Every unit's plan was written, verified and corrected before execution.
2. **Per-unit evidence logs**: 925 k lines in 13,602 files under `audit/artefacts/evidence/`. U30 155 k, U18 96 k,
   U31 84 k, U23 83 k, U19 76 k.
3. **R1, the bench-tier log check**: 12 lanes on one fixture's consequences, none of them verifiable on silicon in U35.
4. **R2, per-wiring twin tests**: 15 lanes of harness feeding harness (dedup keys, driven-clock conversions, idle-poll
   skip, `DrivenTime.cancel`, the twin watchdog), with CMr1n still queued.
5. **R3, test-wait tagging**: 7 lanes in U35 after 172 actions in U8C/U8C2, measuring the test suite's own timeouts.
6. **R5, the records walks** (raising, conformance, e51, faults, intent, levels, review): 20 lanes and about 35 k audit
   lines, plus 20 re-render commits that exist only because the records are keyed on line numbers.
7. **R4, twin-scenario harness growth**: a new runner flag, a premise exception and socket pinning, all to reach edge
   assertions.
8. **Fix-of-a-fix and fallback cascades**: R6 (NTP cadence), R7 (OF-107's three reorders, merged before the owner
   answered), R9 (PieceBuffer catches → twin link harness).
9. **R10, the NeoPixel cascade**: a hypothetical finding (OF-75), then a hardcoded 300 s rewrite (U22), then a real
   lost-cancel defect (LC1), then an investigation into MicroPython's C sources. This is the case the owner names in
   LN362/363.
10. **R8 and R11**: real problems whose proof or tooling outgrew the fix. They are a silicon-check preparation stalled
    twice by refusals, and a CI mirror probe with tests of the probe itself.
11. **Cross-unit returns**: the 2**30 wrap (U14 → T4r3), twin port binding (U25 → N15/TH1), the coverage tracer
    (U15/U25 → CE2r/CEr1/CEr2) and MemoryError paths (U17/U30 → F3r/UM).
