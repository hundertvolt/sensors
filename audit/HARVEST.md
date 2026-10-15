# Audit harvest — what the project already records

Every limitation, accepted risk, settled decision, assumption, workaround, unenforced invariant, mirror
obligation, suppression, open question and piece of drift that the project's own comments, docstrings,
docs, commit messages and GitHub discussions state — recorded, not verified, triaged or solved (owner,
`PROJECT_AUDIT_PLAN.md` 3.1; validation step V10). Snapshot: commit `2a88cc8`, moved to `4dc80ef` (`main` after PR #58) by the plan's V11; line anchors resolve at `4dc80ef`.
Per-area catalogs: `audit/harvest/<AREA>.md`; item IDs `<AREA>.Nnnn` are stable once committed.

## How to read an item

`**AREA.Nnnn** KIND · anchor — "verbatim quote" — what it declares · plan cross-reference · [agent]`

- **Kinds**: TODO (deferred work), LIMIT (known limitation, gap, fidelity gap of a fake/twin), RISK
  (accepted risk), SETTLED (owner decision / deliberate — check it is still accurate, never reopen), ASSUME
  (assumption, unverified claim, single dated measurement), WORKAROUND (external defect worked around),
  INVAR (contract kept by convention only, or the named enforcer), MIRROR (duplicate/mirror obligation),
  SUPPRESS (lint/type/test suppressions and gates), PLATFORM (version- or silicon-specific fact), OPENQ
  (open question), DRIFT (doc/comment vs code or doc, stale fact, dangling reference), NOTE(<label>) (an
  agent's own finer label such as LIC, PAR, MEM or REVERT, kept as given).
- **Plan cross-reference**: `covered-by: <ID>` — a plan topic/seed already covers it; `related: <ID>` —
  partial overlap; none — new to the plan. Agents set these; the audit re-checks them.
- **Anchor tags**: a script compared every quote with the snapshot at its anchor. Untagged: the quote is
  there (or the anchor is not a file line: a SPECIFICATION Part, a commit, a PR). `⟨re-anchored⟩`: the
  quote was found elsewhere in the same file and the anchor now points there. `⟨quote not matched⟩`: a
  paraphrased or composite quote — check before relying on it. The bench PSK is redacted (`HW.T11`).
- **Baseline tags** (V11): `⟨4dc80ef: …⟩` on an item whose source left the tree between `2a88cc8` and
  `4dc80ef` says what became of it — a retired queue/handover row's fate (with the commit), where its
  content lives now, or that the quoted text was reworded. `[D1]` marks the 24 delta items recorded at
  the move. Catalogs are edited in place since V11; `harvest_merge.py`'s render would rebuild them from
  `raw/` without the tags and the delta, so it is not re-run.

## Size and anchor check

6507 items from 17 agents; 31 exact duplicates (same kind and anchor) folded;
6476 catalogued. Anchor check: ok 5847, not-a-file 450, quote-not-found 100, no-quote 47, moved 29, out-of-bounds 3.

**At `4dc80ef` (V11)**: 6,500 items (24 delta items added, `[D1]`); `audit/sweeps/harvest_check.py`
reads ok 5,759, not a file 468, quote not found 119, no quote 49, out of bounds 13, file gone 92 (the
queue and handover, folded into BACKLOG by `03f8bcf`); 124 items carry a `⟨4dc80ef: …⟩` fate tag.
The counts in the table are current.

| Area | Items | SETTLED | INVAR | MIRROR | LIMIT | RISK | ASSUME | PLATFORM | WORKAROUND | SUPPRESS | TODO | OPENQ | DRIFT | NOTE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [XCUT](harvest/XCUT.md) | 96 | 9 | 34 | 3 | 5 | 13 | 12 | 1 |  | 8 | 3 |  | 2 | 6 |
| [CORE](harvest/CORE.md) | 269 | 48 | 61 | 3 | 36 | 30 | 33 | 2 | 2 | 30 | 11 | 4 | 5 | 4 |
| [ALGO](harvest/ALGO.md) | 81 | 11 | 17 | 10 | 15 | 5 | 8 | 3 |  | 8 | 1 |  | 2 | 1 |
| [BUS](harvest/BUS.md) | 141 | 15 | 43 | 2 | 26 | 4 | 16 | 14 |  | 11 | 3 | 1 | 1 | 5 |
| [SENS](harvest/SENS.md) | 412 | 58 | 54 | 17 | 72 | 15 | 57 | 71 | 2 | 32 | 5 | 2 | 8 | 19 |
| [STOR](harvest/STOR.md) | 210 | 44 | 35 | 8 | 30 | 19 | 23 | 19 |  | 7 | 5 | 2 | 8 | 10 |
| [UART](harvest/UART.md) | 282 | 72 | 74 | 28 | 26 | 10 | 26 | 8 | 1 | 9 | 13 | 1 | 4 | 10 |
| [NET](harvest/NET.md) | 258 | 43 | 31 | 7 | 50 | 18 | 31 | 15 | 2 | 39 | 6 | 3 | 6 | 7 |
| [REST](harvest/REST.md) | 186 | 20 | 31 | 13 | 30 | 16 | 36 | 7 | 5 | 13 | 2 | 4 | 4 | 5 |
| [LED](harvest/LED.md) | 64 | 8 | 18 | 8 | 13 |  | 6 | 3 |  | 6 | 1 |  | 1 |  |
| [GEN](harvest/GEN.md) | 280 | 26 | 63 | 51 | 54 | 7 | 45 | 10 |  | 5 | 4 |  | 11 | 4 |
| [TOOL](harvest/TOOL.md) | 172 | 19 | 28 | 7 | 24 | 12 | 20 | 18 | 16 | 5 | 11 |  | 4 | 8 |
| [SCR](harvest/SCR.md) | 220 | 24 | 41 | 12 | 48 | 8 | 25 | 7 | 9 | 24 | 9 |  | 10 | 3 |
| [CI](harvest/CI.md) | 222 | 40 | 21 | 4 | 23 | 8 | 19 | 8 | 17 | 36 | 14 |  | 16 | 16 |
| [WEB](harvest/WEB.md) | 286 | 15 | 25 | 73 | 89 | 4 | 35 | 8 |  | 3 | 8 | 1 | 20 | 5 |
| [TEST](harvest/TEST.md) | 767 | 24 | 125 | 96 | 195 | 9 | 105 | 7 | 32 | 121 | 4 |  | 30 | 19 |
| [TWIN](harvest/TWIN.md) | 380 | 25 | 50 | 21 | 150 | 4 | 75 | 3 | 20 | 11 | 3 | 1 | 4 | 13 |
| [HW](harvest/HW.md) | 863 | 64 | 114 | 62 | 118 | 67 | 190 | 27 | 10 | 65 | 28 | 12 | 73 | 33 |
| [SEC](harvest/SEC.md) | 46 | 2 | 4 | 1 | 6 | 22 | 1 |  |  | 5 |  |  | 2 | 3 |
| [MEM](harvest/MEM.md) | 175 | 23 | 32 | 2 | 20 | 9 | 39 | 1 |  | 18 | 4 | 8 | 1 | 18 |
| [PERF](harvest/PERF.md) | 55 | 4 | 4 |  | 2 | 4 | 32 |  |  |  |  | 8 |  | 1 |
| [PLAT](harvest/PLAT.md) | 400 | 4 | 5 |  | 2 | 2 | 7 | 361 | 8 | 3 |  |  | 5 | 3 |
| [PAR](harvest/PAR.md) | 259 | 32 | 95 | 12 | 44 | 13 | 22 | 11 | 1 | 1 | 2 | 1 | 14 | 11 |
| [DOC](harvest/DOC.md) | 314 | 22 | 19 | 5 | 13 | 1 | 9 | 1 |  |  | 5 | 1 | 226 | 12 |
| [LIC](harvest/LIC.md) | 57 | 2 |  | 9 | 3 | 2 | 11 |  |  | 2 | 3 | 1 | 14 | 10 |
| [UNSORTED](harvest/UNSORTED.md) | 5 |  |  |  |  |  |  |  |  |  |  |  |  | 5 |

## Partitions (read-only agents, one each)

- **H01** (415 items): src/, first half (14 files)
- **H02** (484 items): src/, second half, plus ext/ (22 files)
- **H03** (415 items): tests/ part A: helpers, fakes, first test files (28)
- **H04** (332 items): tests/ part B (10 large files)
- **H05** (315 items): tests/ part C (35)
- **H06** (462 items): digital_twin/ and every tests/test_digital_twin_* (50)
- **H07** (547 items): tests_hardware/ code (97)
- **H08** (275 items): tests_hardware/README.md, the queue, the handover, dev_legacy/, mockdata/ (37)
- **H09** (520 items): scripts/, toolchain/, buildgen/, .github/, devices/, root Python config (57)
- **H10** (352 items): tests_scripts/ (65)
- **H11** (281 items): js/, html/, tests_js/, web config (37)
- **H12** (452 items): SPECIFICATION.md lines 1-3421 (Parts A-E)
- **H13** (503 items): SPECIFICATION.md lines 3422-6785 (Parts F-M)
- **H14** (279 items): CLAUDE.md, README.md, DEVICE_REFERENCE.md, update_and_install.txt
- **H15** (259 items): BACKLOG.md, HEAP_FRAGMENTATION_MEASUREMENTS.md (+ archive at 12640c2), UART_C_PORT_CHANGELOG.md, licences
- **H16** (191 items): legacy tree: python/, modules/, html_raw/, build-*.sh (parity oracle only)
- **H17** (425 items): all commit messages to 2a88cc8, GitHub issues and pull requests (read-only)

Partial reads, as reported:

- H02: `src/voc_algorithm.py` comments all read, code read at 1-330 and 700-797, the rest grepped; `ext/microdot.py` read in full only on the code paths this project uses.
- H15: the `12640c2` heap-measurement archive (5,553 lines) keyword-scanned end to end, ~1,300 lines read in full.
- H16: legacy `voc_algorithm.py` lines 430-911 (uncommented) scanned only; `python/CommonDrivers/microdot.py` provenance only.
- Every other partition: every file read in full (comments via the extractor, docs in full text); nothing reported unreadable.

## Untracked deferred work from git history and GitHub (H17, verbatim)

Deferred items found in commit messages or PR/issue discussions that no later commit, doc or BACKLOG
entry picks up. Their catalog entries carry the same text in the owning area.

48 items (commit-derived and GitHub-derived; includes partial-untracked statuses such as "reason UNTRACKED (low)").

- SETTLED | commit b64857d | "arzi/neu pressure compensation (accepted limitation) ... the hotspot password (accepted for now)" | Owner accepted arzi/neu's missing pressure compensation as a limitation and the hardcoded hotspot password "for now"; the pressure-compensation acceptance is not restated in SPECIFICATION (grep "compensat" finds only SGP40/SCD30 compensation) (low). | area: PAR | status: hotspot pw tracked: CLAUDE.md "one known real credential"; pressure-compensation acceptance UNTRACKED (low) | related: PAR.T*
- REVERT | commit b0a9235 (reverts 4e2d953) | "Revert \"Explicitly catch ZeroDivisionError in math_helpers.py; document exhaustiveness check\"" | Explicit ZeroDivisionError catch and the src/README.md "verify caught exception set against MicroPython source" checklist expansion were reverted without a stated reason. | area: ALGO | status: src/math_helpers.py has no ZeroDivisionError (grep); reason for revert UNTRACKED (low) | -
- SETTLED | commit b1059bd | "Records the declined lookup-table CRC optimization (small buffer sizes in practice, not worth the RAM cost)" | Owner/session declined table-driven CRC. | area: ALGO | status: not restated in SPECIFICATION (grep finds no CRC lookup-table note) — UNTRACKED (low) | -
- TODO | commit a5fe9fd | "future SPIDevice consumers need the same \"does every call site actually catch what this can raise\" check" | SPI raises ValueError/RuntimeError/NotImplementedError on setup/programmer-error paths; each new consumer's call sites must be audited. | area: BUS | status: no dedicated tracker found (ISL29125 is I2C; FRAM is the only SPI consumer) (low) — UNTRACKED | related: BUS.T*
- PLATFORM | commit b087dc7 | "A value omitted before a comma/brace (e.g. {\"Count\": , \"Offset\": 1.5}) doesn't raise on this MicroPython version - it desyncs the parser into a mangled dict" | MicroPython json.load leniency relied on to degrade via per-key default fallback; json.dumps(nan) writes a token json.loads cannot read back. Version-specific (checked at 1.28). | area: PLAT | status: covered by a test per commit; not found restated in SPECIFICATION (grep "omitted"/"desync" in config_manager.py/SPEC) — UNTRACKED as a platform fact to re-check on version bumps (low) | related: PLAT.T*
- SETTLED | commit 96031eb | "get_size() also has zero callers today (kept as legitimate API surface ...); get_values()/set_values() don't reject a zero-length buffer" | Zero-caller FRAM API and zero-length buffer acceptance deliberately left. | area: STOR | status: not restated in BACKLOG (which only settles verify_present/set_write_protected) — UNTRACKED (low) | related: STOR.T*
- PLATFORM | commit d92da47 | "cancelling a task before its first scheduler step can raise CancelledError to the awaiter no matter what try/except exists inside the coroutine" | asyncio property relied on as irrelevant because the real caller never awaits the DNS task. | area: PLAT | status: not restated in SPECIFICATION (low) — UNTRACKED | -
- SETTLED / RISK | commit 110f3db | "a genuine not-ready cycle now reuses the last good reading with a fresh timestamp and does NOT count as an error (matching legacy)" | SCD30 can report a previous cycle's values under a new timestamp by owner choice (legacy parity over "safer-looking" change). | area: SENS | status: not found restated in SPECIFICATION (grep) — UNTRACKED (low) | related: SENS.T*, PAR.T*
- PAR / DRIFT | commit 2bda920 | "python/IndividualDrivers/asy_bmp3xx_driver.py (deployed production driver): same tuple correction ... modules/sensortask-wozi.py ... html_raw/wozi/sensorconfig.html" | The IIR fix edited the reference-only legacy tree, so `python/`/`modules/`/`html_raw/` no longer match the firmware actually deployed (which still uses 0,2,4,...,128); deployed units' stored BMPFiltCoeff values (2,4,8,...) are outside the refactor's accepted set {0,1,3,7,...}, and the migration consequence is stated nowhere (SPECIFICATION has no IIR/FiltCoeff migration note). | area: PAR | status: UNTRACKED | related: PAR.T*
- SETTLED | commit 500851c | "recorded the general \"leave the catch, skip an untestable test, note why\" convention in BACKLOG.md, confirmed directly by the project owner" | Owner convention for untestable defensive catches; no longer in BACKLOG (grep) and not visible in SPECIFICATION Part D/E. | area: TEST | status: UNTRACKED (low) | related: TEST.T*
- WORKAROUND | commit cc911be | "a confirmed Unix-port-vs-rp2 time.gmtime() tuple-length difference the test suite works around" | Unix-port gmtime shape differs from rp2 (8-tuple); tests paper over it. | area: TEST | status: not found restated in SPECIFICATION Part F (grep); removal trigger none stated — UNTRACKED (low) | related: PLAT.T*
- SETTLED | commit 5ddbcd3 | "An earlier wifi_mode_lock_timeout_ms/bounded-acquire mechanism added to asy_wifi_service.py during this work was reverted per direction" | Bounded wifi_mode_lock acquire rejected (keep timing centralized). | area: NET | status: owner decision; not restated in docs (low) — UNTRACKED | related: NET.T*
- OPENQ | commit 8784c66 | "a theoretical (verified unreachable in practice, matches legacy behavior) task-restart edge case in asy_wifi_service.py's permanent-WLAN-deactivation feature" | Flagged for owner input; class-naming half is done (AsyConnTime/AsyNtpClient). | area: NET | status: no closure found by grep (low) — UNTRACKED | related: NET.T*
- DRIFT | commit b6cb852 | "build-*.sh: removed the hardcoded /home/nico/rpi_pico/... path; each script now derives its own FROZEN_MANIFEST path" | A second edit to the reference-only legacy tree (build-*.sh) after 2bda920; the build scripts differ from what produced the deployed images. | area: PAR | status: UNTRACKED as a "legacy tree ≠ deployed" fact (low; build scripts don't change runtime behaviour) | related: PAR.T*
- ASSUME / DRIFT | commit 6a91514 → 7079757 | "Widen the errcount wait to 90s and the DNS wait to 90s (from 30s)" | Run 7 budgets were widened on a disproven timing hypothesis (real cause: CAP_NET_BIND_SERVICE) and remain at 90 s (scripts/_digital_twin_ci_suite.py:958,968). | area: SCR | status: UNTRACKED (low; budgets never narrowed back) | related: SCR.T*
- LIMIT | commit b373034 | "The real backend's \"Unchanged\" PUT result essentially never fires in practice, matching an already-established tolerance in tests_js/live-backend.test.js" | Live tests tolerate a result code the backend defines but practically never emits (write_config compare semantics). | area: WEB | status: tolerance lives in tests_js; not found stated in SPECIFICATION (low) — UNTRACKED | related: WEB.T*, REST.T*
- OPENQ | commit f7ceab8 | "the residual bug unix_port_poll_prewarm.py works around looks like a narrower, still-unfiled edge case rather than a duplicate" | Upstream MicroPython modselect edge case was never reported upstream; the workaround has no removal trigger. | area: TWIN | status: UNTRACKED (no issue filed / no follow-up recorded) | related: TWIN.T07
- DRIFT / PAR | commit e05f015 | "it runs the deployed fleet's actual MicroPython 1.24.1 and holds code changes made directly on-device that were never copied to any host machine" | Contradicts CLAUDE.md/BACKLOG #3/SPECIFICATION.md:3426 ("deployed units run MicroPython 1.26"); also shows at least one unit carried on-device code not in the repo, weakening "legacy tree = deployed behaviour". dev_legacy/README.md:671 now only says the bench unit ran 1.24.1. | area: PAR | status: UNTRACKED (fleet version and on-device divergence never reconciled) | related: PAR.S10, PAR.T*
- SETTLED | commit 1096b31 / a10c578 | "the router's own reservation re-keying is the project owner's own follow-up, not something to track here" | Out-of-repo bench follow-up deliberately untracked. | area: HW | status: UNTRACKED by owner decision (low) | -
- OPENQ | commit e246825 | "one separate, flagged-not-chased finding (a device-side AttributeError traceback whose line numbers don't match the current src/ checkout, suggesting stale firmware rather than a current bug)" | Unexplained device-side AttributeError. | area: HW | status: no closure found; later explained generally by d967013 (build_firmware's ast.unparse drops comments so line numbers never match) — cause of the AttributeError itself UNTRACKED (low) | -
- DRIFT | commit e624018 / d082272 | "Document why DEV_UNIQUE_GROUPS currently matches zero dev sensor groups ... Dev is expected to gain its own unique sensor(s) later" | tests_js/mock-server-put-matrix.test.js:21 still names {SHTC3, MPRLS, ISL29125} and mockdata/dev.json:5-6,13-14,65-75 still carries SHTC3/MPRLS data/errcount entries, although html/definitions/dev.json has neither (rewritten in d082272; ISL29125 later added). Owner later decided "leave the mockdata orphans" (commit 12a616a, q5) but only in the retired ISL29125 planning doc; the test comment "matches none of dev's real groups today" is now stale since ISL29125 is a real dev group. | area: WEB | status: UNTRACKED (low; owner decision not in live docs) | related: HW.T07, PAR.S14
- TODO | commit 349ba1e | "Remaining findings (a systemic code-comment-length/narrative-block violation across ~68 new files, dangling references to deleted HARDWARE_TEST_PLAN.md/DEV_HARDWARE_BASELINE_PLAN.md section numbers ..., and one licensing-doc judgment call) are reported separately" | Comment-length done later (CLAUDE.md: every scope measures zero); the "licensing-doc judgment call" is not identified in any later commit. | area: LIC | status: comment part done; licensing judgment call UNTRACKED (low) | related: LIC.T*
- SUPPRESS / DRIFT | commit 454f6a2 | "Per-file exemptions live centrally in [tool.ruff.lint.per-file-ignores], never as inline noqa comments." | Stated rule (still at pyproject.toml:214-215) vs reality: 2 inline `# noqa: B905` in src/ (asy_wifi_service.py:709, asy_webserver_service.py:778) and 74 inline `# noqa` across tests/digital_twin/scripts/buildgen/toolchain/tests_scripts/tests_hardware; BACKLOG 2026-09-22 also moved S102 from per-file to inline deliberately. | area: CI | status: UNTRACKED as a doc/practice contradiction (low) | related: CI.T* (plan line 2376 "E402 noqa split")
- LIC / TODO | commit 90e8c17 | "ext/freezefs/archive.py synced to upstream main (no release tags exist)" | Vendored freezefs pinned to an untagged upstream commit; no tag-level provenance. | area: LIC | status: not found as an explicit plan topic (plan treats ext/freezefs as reliance-only) — UNTRACKED (low) | related: LIC.T*, WEB
- OWNER-DECISION LOST | commit 9f4c084 -> 41762dc -> 080cde3 -> merge e5d2c43 | 41762dc: "The reorder itself is a decided task now ... moves ... into 'Refactor targets not yet done' at high priority, naming all eleven non-compliant classes" and amends D.15's comment clause ("comments move with the code they annotate") | The HIGH-PRIORITY BACKLOG item "Sort every class in src/ to D.15" and the D.15 amendment were added on main, then silently dropped when merge e5d2c43 took this branch's side on all 36 conflicts; neither text exists at 2a88cc8 (SPEC D.15 at :2717 still says "no change to any ... comment"). An AST check at 2a88cc8 finds 9 classes still non-compliant (SCD30_Reader, UART_Comm, UART, _ModuleLike, AsyConnTime, ConfigManager, Framing_Base, Framing_COBS, SystemService). | area: XCUT/DOC | UNTRACKED | related: XCUT.T*
- DIVERGENCE | commit 9f4c084 | "the GET entry points validate their arguments before the readiness gate while the SET ones gate first" | Flagged, not changed; still true (uart_get_into checks buf before gating; uart_set_into gates first). | area: UART | UNTRACKED (low) | related: UART.T*
- OWNER-PRINCIPLE | commit 8a45060 | "Project owner's direction: this is a general principle - no error/warning should ever be logged for expected startup jitter on any boot, on any module - to be addressed, and audited for elsewhere in the codebase, in a dedicated follow-up session" | 7727ad1 fixed SGP40 and audited only the narrower "None vs exception" class; the general no-startup-jitter-logging principle is not written as a standing rule in CLAUDE.md/SPEC (SPEC:2526-2532 records only the SGP40 fix), and the owner's grace-period idea was never decided or recorded. | area: XCUT/SENS | UNTRACKED (principle) | related: SENS.T*
- FLAKY | commit 2e7e4eb | "a real but unrelated CI-timing flake (tests/test_asy_ntp_client.py::test_integration_recovers_on_retry_after_one_dropped_request, a TimeoutError on a real 5-second UDP round-trip wait) ... confirmed transient, not a regression, not touched" | Flaky real-UDP test left as is. | area: TEST/NET | UNTRACKED (low; no BACKLOG/SPEC mention; test still at tests/test_asy_ntp_client.py:2205) | related: NET.T*, TEST.T*
- FLAG | commit 4303242 / 38a1753 / 7e0d507 | "seven classes elsewhere in src/ do not satisfy D.15" -> "eleven of 74" | See the "OWNER-DECISION LOST" D.15 item above (41762dc owner ruling later dropped in merge e5d2c43). | area: XCUT | UNTRACKED (same item as 41762dc) | -
- SCOPE-MARKER LOST | commit 179a10c | "BACKLOG 17's five cross-file consistency findings, 25's reserved-range errno/wrnno audit, 26's unreachable UART wrnno 11, and the src/-wide D.15 reorder - each now carry the same marker ... 'Independent session - out of the ISL29125'" | Three of four later done (58abf8f, b0f755c); the D.15 reorder has no BACKLOG entry at 2a88cc8 (marker grep finds nothing). | area: XCUT | UNTRACKED (D.15 reorder; same as 41762dc item) | -
- DOC-DRIFT | commit dfb85ff | "SPECIFICATION.md's F.2 WiFi-power-cycle-backstop invariant now states the accepted residual risk window precisely ... instead of the old, now-inexact 'structurally cannot have a write in flight' claim" | SPEC F.2 (SPECIFICATION.md:3641-3649) was corrected, but CLAUDE.md:199-201 Hard rule still says "a device whose API is unreachable structurally cannot have a write in flight" — the claim SPEC calls "no longer exactly true". | area: DOC/STOR | UNTRACKED | related: NET.T*, DOC.T*
- REPORTED-NOT-CHANGED | commit 04ef56a | "I2CDevice inherits Lockable's __aenter__/__aexit__ unchanged, so an I2C session burst has no scheduling point either ... recorded for a decision rather than fixed here" | I2C session bursts hold the event loop (no yield between sessions), unlike SPI after 04ef56a. Recorded only in HEAP_FRAGMENTATION_MEASUREMENTS.md, whose 2026-09-24 condensation (17b4354) dropped it; it survives only in the git archive (12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md:5227). BACKLOG.md:613-624 records the related SPI-sync/I2C-async API asymmetry as deliberate, but not the missing between-session yield for an I2C burst. | area: BUS/PERF | UNTRACKED (low; partly covered by BACKLOG.md:613) | related: BUS.T*, PERF.T*
- OBSERVATION | commit 7ccbe8d | "The real main() runs start_timers() and an NTP sync between the two lists, so the firmware has a third boot stretch with no collect in it - B's design covers the two lists deliberately and widening it would widen the I.4 exception, so it is recorded as an observation, not changed" | Uncovered boot stretch for the placement reset. | area: MEM | UNTRACKED (low; SPEC I.4(f.1) at :5073 names only the two lists, not this gap) | related: MEM.T*
- LOST-THEN-RECOVERED | commit 323a1a7 | "Five more items main had and this branch did not, each re-verified here before recording (BACKLOG 37-41)" | Recovery after merge e5d2c43 — lists five items but NOT the D.15 reorder task, confirming that one stayed lost. | area: DOC/XCUT | status: 37-41 later closed (58abf8f etc.); D.15 reorder UNTRACKED (see 41762dc item) | -
- DEAD-HELPER | commit ae51e4b | "Its new assert_module_error_log_clean() is defined and called from nowhere - flagged so a future session uses it or drops it rather than assuming it is load-bearing" | Unused test helper. | area: HW/TEST | UNTRACKED (low; still defined at tests_hardware/error_log_helpers.py:49 with zero callers at 2a88cc8) | related: TEST.T*
- PROCESS-LESSON | commit c2050da (also 4f39c0b) | "Lint was red from 55e5f6f9: the gate checks before those commits read lint.sh through tail, which hid ruff's output and exit status" | Second recurrence of reading lint.sh's tail instead of its exit code. | area: TOOL/process | UNTRACKED (low; lesson in commit messages only, not in CLAUDE.md/README) | -
- ONLY-IN-TEMP-DOC | commit 21560a4 | "SGP40 W13 fills its ring while NTP is absent" ("one 'backup written without timestamp' slot per backup (1 min), 9 slots after one hotspot episode ... Suggested: apply C.7.1's per-episode repeat rule ... a candidate for BACKLOG 50's list") | Same warning-flood class as item 35, unfixed; BACKLOG 50 was already closed (b5450aa) when this was found, and the finding lives only in the throwaway HARDWARE_TEST_HANDOVER.md:163. | area: SENS/STOR | UNTRACKED (medium; temp doc only) | related: SENS.T*, STOR.T*
  → `4dc80ef`: fixed, W13 spends one slot per outage (`83c9920`; SPECIFICATION.md:1939)
- ONLY-IN-TEMP-DOC | commit 21560a4 | "an attach within ~1 s of boot parks the board with no watchdog" ("it never recovers on its own ... Suggested: add to ... tests_hardware/README.md") | Bench trap. | area: HW | UNTRACKED (low; HARDWARE_TEST_HANDOVER.md:176 only, not in tests_hardware/README.md) | -
  → `4dc80ef`: tracked, `tests_hardware/README.md:390-393`; the flash tier now ends with `hard_reset()` (`79eb41b`)
- ONLY-IN-TEMP-DOC | commit 21560a4 / HARDWARE_TEST_HANDOVER.md:172 | "FRAM E31 + W73 at the first boot after flashing: mpremote exec machine.bootloader() most likely landed mid-write ... entering BOOTSEL this way can cost one FRAM log entry" | Bootloader entry can tear a FRAM write. | area: STOR/HW | UNTRACKED (low; temp doc only) | -
  → `4dc80ef`: tracked, `tests_hardware/README.md:401`
- KNOWN-GAP | https://github.com/hundertvolt/sensors/pull/41 | "validates each DNS label's length (≤63 octets ...) but not the *total* encoded QNAME length (≤255 octets" | `_build_query()` builds a spec-invalid query for a >255-octet name; degrades to a timeout/`None`. Still true at 2a88cc8 (src/asy_dns_client.py:40-51); reachable because NTP_Host keeps its 1024 bound | area: NET | UNTRACKED | related: BACKLOG NTP_Host SETTLED entry (BACKLOG.md:489-506), commit-side NTP_Host items
- DEAD-CODE | https://github.com/hundertvolt/sensors/pull/30 | "`BMP3XX_I2C.get_altitude()` has zero callers anywhere in `src/` — dead code, left for a future cluster's decision" | Still no src caller at 2a88cc8 (src/asy_bmp3xx_driver.py:570); not in BACKLOG/SPEC | area: SENS | UNTRACKED | -
- DEAD-CODE | https://github.com/hundertvolt/sensors/pull/50 | "`wlan_isconnected()` still has zero production callers. Whether to remove it or keep it as intentional public API surface is a code decision ... left as-is" | Was cited as BACKLOG ~line 379 in Sept 8; no BACKLOG/SPEC mention at 2a88cc8, method still at src/asy_wifi_service.py:775 — pruned without decision | area: NET | UNTRACKED | -
- DOC-DRIFT | https://github.com/hundertvolt/sensors/pull/53 | "an end-to-end HTTP redirect check once hotspot mode is genuinely reached" | PR #53 added captive-portal `redirect("/")` (src/asy_webserver_service.py:658-660) but tests_hardware/manual/manual_wifi.py:40 still says no HTTP redirect exists | area: TEST-HW | UNTRACKED | -
- OUT-OF-SCOPE | https://github.com/hundertvolt/sensors/pull/53 | "DHCP Option 114 (RFC 8910) was researched and deliberately left out of scope (requires patching" | Captive-portal DHCP option deliberately not done; no doc records the decision | area: NET | UNTRACKED | -
- INVAR | https://github.com/hundertvolt/sensors/pull/40#issuecomment-5344576386 | "the three top-level `await self.cfgmgr.get_*_values()` calls in `monitor_loop()` execute as one uninterrupted synchronous unit" | No-lock justification rests on `_get_values()` never suspending on the success path; only the error path awaits `pr.err_s`. Still holds at 2a88cc8 (src/asy_notification_service.py:343-345, src/config_manager.py:240-293); recorded only in the PR comment | area: CORE | UNTRACKED | -
- CRASH-UNEXPLAINED | https://github.com/hundertvolt/sensors/pull/58#issuecomment-5659653795 | "died with **exit code -11 (SIGSEGV)** on the reboot launch ... No fix for this specific crash exists yet in any PR" | grkizi Run 5c reboot segfault, re-run as a flake; no doc records a root cause for this signature | area: TWIN | UNTRACKED (possibly the SIGINT/VM-corruption class closed in 8466f2b, not verified) | related: 8466f2b, CLAUDE.md nested-asyncio.run segfault rule
- LEAK-IN-TOOL | https://github.com/hundertvolt/sensors/pull/95#issuecomment-5692708409 | "`tests/machine.py`'s `Timer.all_timers` is a process-lifetime registry that file never clears ... An unverified one-line fix sits in `1bfd631` on the backup branch" | Registry still unbounded at 2a88cc8 (tests/machine.py:611,630); only per-driver tests clear it; masked by the per-device test_sensortask split, not fixed | area: TEST | UNTRACKED | related: CLAUDE.md heapsize history (E.3.1)
- FUTURE | https://github.com/hundertvolt/sensors/pull/104 | "going further would need `tests_scripts/` itself parallelized (e.g. `pytest-xdist`), flagged as a further opportunity, not attempted" | tests_scripts single-process tier is the suite's wall-clock floor | area: TEST | UNTRACKED | -

## Each agent's own top 10 (verbatim; anchors are the agent's)

### H01 — src/, first half (14 files)

1. RISK src/asy_ntp_client.py:157/217/250 vs src/base_classes.py:198/207 — NTP (and NOTIFY) wrnno 1-2 share a logger with base_classes' reserved wrnno 1-2, contradicting SPECIFICATION.md:1907-1908 "No clash is live" (not in plan).
2. DRIFT src/asy_ntp_client.py:9-10 — "numbering starts at 11, clear of base reservation" vs wrnno 1-3 in code.
3. INVAR src/api_response.py:31-34 — errno 99 "must not collide" is convention only; FRAM_SPI also uses errno 99.
4. RISK src/asy_sgp40_driver.py:586-593 — I2C general-call reset broadcast to every device on a shared bus, OSError swallowed.
5. LIMIT src/asy_ntp_client.py:450-453 — errno 18 persisted every 10 s tick while config read fails (no repeat rule); also errno 19 (:407-411) per call.
6. MIRROR src/asy_isl29125_driver.py:162-165/880-896 — ISL `_FIELDS` is unused; the wire keys are hand-written, so the field-agreement test protects nothing there.
7. LIMIT src/asy_fram_manager.py:73-78 — failed check-buffer allocation degrades to rewriting block 1 on every read.
8. PLATFORM src/asy_fram_manager.py:549/613 (also ntp, notification) — unsourced "rp2 mktime() OverflowError past ~2037" fact, not in Part F.
9. DRIFT src/asy_fram_driver.py:151-153 ("PLAN A.1.2"), src/asy_isl29125_driver.py:305/500 ("step 9", "spec R5"), src/api_response.py:69 ("see CLAUDE.md"), src/asy_fram_manager.py:3 — dangling doc pointers not in DOC.S05.
10. ASSUME src/asy_isl29125_driver.py:87-88 — cycle/settle timing built on typical tINT and an inferred 12-bit value; plus :100-104 tolerances from one bench measurement.

### H02 — src/, second half, plus ext/ (22 files)

1. RISK `src/asy_wifi_service.py:320-323` — a failed `LedWifiOn` config read at task start sets `_PHASE_DEACTIVATED` (WLAN off until restart); not in the plan, and combines with `CORE.S02`.
2. RISK `src/base_classes.py:219-229` — every failed read cycle persists errno 1, then errno 2 plus a task restart that resets the streak, so a dead sensor writes to the FRAM ring continuously (`PERF.T10`).
3. RISK `ext/microdot.py:804-806` — upstream says "The filename is assumed to be trusted"; the project passes the client `<path:filename>` with only a `..` substring guard (`asy_webserver_service.py:650-655`).
4. WORKAROUND `src/asy_webserver_service.py:271-278` — header coalescing depends on Microdot's exact write pattern (`ext/microdot.py:672-681`); if that pattern changes, the proxy buffers the head forever.
5. DRIFT `src/asy_webserver_service.py:123, 387, 698` ("decision 3/6/7" are absent from A.8) and `:689` ("(F.6)" points at the SIGINT/heap Part).
6. SUPPRESS `src/asy_uart_comm.py:1078-1080` — after a fully received and ACKed SET, a right-size MemoryError drops the payload the peer believes was delivered (`UART.T08`).
7. RISK `src/config_manager.py:241-243, 271-273` — an invalid config persists errno 5/7 on every read with no `repeat=`.
8. ASSUME `src/asy_uart_driver.py:30-33` — the 1 s cancel-ack bound assumes every poll round, including `poll_idle_ms`, is well under 1 s.
9. RISK `src/crc_checks.py:18-24` — a misconfigured CRC silently degrades to pass-through, which disables integrity checking.
10. INVAR `src/voc_algorithm.py:52, 56-57` — the params field order and the `32q`/256 B size form the persisted SGP40 FRAM layout, and nothing ties them together (`ALGO.T05`).

### H03 — tests/ part A: helpers, fakes, first test files (28)

1. DRIFT `tests/_webserver_concurrency_scenarios.py:249-254` — `_real_config_write()` PUTs `SCD30.Interval` (field is `MeasInt`; SCD30 has no ConfigManager) while only the status is read, so the two "concurrent real config write" scenarios likely exercise no write.
2. LIMIT `tests/_sensortask_scenarios.py:65-72` — dev's 256 KB FRAM fake keeps the 8 KB memory and 2-byte address decode while the driver sends 24-bit addresses; dev mock-tier FRAM addresses may alias.
3. DRIFT `tests/test_asy_isl29125_driver.py:2835` (and `test_asy_neopixel_driver.py:541`) — "bool is an int subclass in MicroPython" contradicts SPECIFICATION.md:3478-3480 and the BMP3xx test.
4. OPENQ `tests/_webserver_concurrency_scenarios.py:133-138` — unexplained connection-accounting sensitivity to a readiness probe was worked around with a fixed sleep, not root-caused.
5. INVAR `tests/test_asy_fram_manager.py:88-90` — FRAM chunk layout is a cross-firmware-version contract resting only on construction call order.
6. RISK `tests/test_asy_bmp3xx_driver.py:1827-1829` — timer-arming failures are print-only, never counted or persisted.
7. LIMIT `tests/machine.py:95-111` — call logs silently drop the oldest half past 4096 entries; whole-log readers (bus-hazard address sweep) may see truncated history.
8. DRIFT `tests/_sensortask_scenarios.py:552 vs :643` + LIMIT `:237-243` — setup-order scenario name contradicts its assertion; starter-membership checks omit isl29125/uart_link.
9. PLATFORM `tests/network.py:73-76` — a >32-byte SSID reaching `connect()` overflows cyw43's `last_ssid_joined` on silicon; only the fake catches it.
10. DRIFT `tests/test_asy_fram_allocation_budget.py:3-5` — says the test interpreter is a settrace build (stale since the 2026-09-21 two-binary split); budgets are single-date absolute byte figures.

### H04 — tests/ part B (10 large files)

1. DRIFT `tests/test_asy_udp_socket.py:1050-1052`: the test "mirrors" an NTP call shape with disconnect() in `finally`, but `src/asy_ntp_client.py:175-191` has no `finally`. The mirror hides the NET.S13 PCB-leak-on-cancel gap.
2. LIMIT `tests/test_asy_webserver_service.py:1108-1135`: the torn-read "characterization" only calls a fake and never touches the service. It cites a SPEC A.8 note that says nothing about torn reads, and test_asy_scd30_driver.py:1140-1146 says SCD30's torn read is fixed.
3. DRIFT `tests/test_asy_udp_socket.py:399-401` vs plan NET.S19: BACKLOG Q5 and this comment say lwIP source filtering was confirmed on hardware (2026-09-08). The plan seed still calls it unverified.
4. LIMIT `tests/test_asy_sgp40_driver.py:2379-2405`: the address sweep swallows every exception and only checks `touched <= {...}`. A run where every call raises before touching the bus still passes, the same pattern as TEST.S02 but in another file.
5. SUPPRESS `tests/test_asy_webserver_service.py:1468-1492, 2625-2643, …`: about 50 lines set the process-global `gc.threshold()` inside test bodies. This overrides the file-level (e)/(f) stage choice that CLAUDE.md's memory rule depends on (TEST.T03).
6. LIMIT `tests/test_asy_uart_comm.py:748-756`: the "survives the ticks rollover" test cannot cross rp2's 2**30 boundary, because the Unix-port tick period is 2**62 (XCUT.T25, UART.S07).
7. LIMIT `tests/test_asy_scd30_driver.py:1113-1118`: the webserver suite's over-complete fake module masked a real `PUT /sensors` 500. That same fake still backs the REST tests (`test_asy_webserver_service.py:53-55`).
8. MIRROR `tests/test_asy_webserver_service.py:2510-2511`: the streaming writer re-implements MicroPython's `json.dumps()` text byte for byte. It must be re-checked whenever the pinned version moves.
9. PLATFORM `tests/test_asy_ntp_client.py:1418-1424`: `gmtime()` returns a 9-tuple on the Unix port but an 8-tuple on rp2. Every cettime() test therefore runs through a shim, and the DST formula itself is not independently verified (`:1414-1416`).
10. LIMIT `tests/test_asy_uart_link_driver.py:358-360`: the claim that the FRAM path never blocks the asyncio loop is tested against a trivial coroutine fake chunk and asserts only `ticks > 2`. A real FRAM write's synchronous SPI time is not modelled.

### H05 — tests/ part C (35)

1. DRIFT `tests/test_fram_integration.py:3-5`: "Real RP2040 SPI write()/readinto() cannot raise" contradicts F.5.2's 1.29 `OSError(EIO)` on 32+ byte SPI reads, so the FRAM chain is never tested against an SPI-level fault on stale grounds.
2. DRIFT/LIMIT `tests/test_setter_microdot_integration.py:4-6, 688-710`: the "real Microdot end to end" SCD30 section never calls `SCD30_Reader._set_dict_cfg()` (now schema-driven in `src/asy_scd30_driver.py:257-289`); it tests a local re-implementation whose field defaults differ from src.
3. RISK `tests/test_setter_microdot_integration.py:660-669`: since WP5's deferred flush, a PUT whose flash write fails still answers 200/"Valid"; the failure is visible only as a later errno.
4. RISK `tests/test_config_manager.py:2259-2261`: a mid-`json.dump()` failure leaves an unparseable config file on flash, and resubmitting the same value is "Unchanged" and writes nothing.
5. SETTLED `tests/test_uart_comm_hazard.py:854-856`: a test pins a known blind spot (mismatched peer reports errno 22, not 32), "accepted rather than fixed"; alongside `:741-743` (undetected payload corruption under the deployed CRC_Pass).
6. LIMIT/PLATFORM `tests/test_ticks_rollover.py:1, 21-23, 98-110`: the rig's tick period is 2**62, not rp2's 2**30, and the no-raw-subtraction guard is a per-line heuristic over `src/` only.
7. RISK/PLATFORM `tests/test_config_manager.py:347-357`: int→float blanket accept is exact only up to the mantissa (24 bits on RP2040), and the unit tier cannot reproduce the single-precision threshold.
8. RISK `tests/test_system_service.py:428-429`: a persistently raising NTP callback persists an `err_s` entry on every uptime tick, i.e. 120 per boot.
9. RISK `tests/test_strict_json.py:86-88`: MicroPython `json.dumps()` emits inf/NaN without raising, so a route that lets one through silently ships a body no browser accepts.
10. LIMIT `tests/test_captive_dns.py:327-333, 800-806`: on the Unix port a real server socket never yields a string `addr[0]`, so the captive-DNS reply path over a real socket is untested at this tier.

### H06 — digital_twin/ and every tests/test_digital_twin_* (50)

1. LIMIT digital_twin/machine.py:899-913: the twin RTC never advances and is not coupled to `time.time()`/`gmtime()` (the host clock). NTP-set clock jumps and RTC-driven time are unmodelled. Related: TWIN.T09, NET.T11.
2. LIMIT digital_twin/machine.py:852-854: the twin WDT only records and never resets the process, so reboot-after-watchdog behaviour is never exercised. Related: README:692-708 late-feed workaround.
3. DRIFT digital_twin/machine.py:828-830: the self-rearm comment says the old task returns on its own, but with a PERIODIC re-init the old loop keeps running, so the timer may double-fire. The regression test covers ONE_SHOT only (tests/test_digital_twin_machine.py:475-484).
4. LIMIT digital_twin/machine.py:916-940: `SimulatedRebootError` subclasses `Exception`, so a broad `except Exception` in src/ swallows a simulated `reset()`.
5. ASSUME digital_twin/machine.py:500-502: "no test comes close" to the `ticks_us` period. UART-link wire time rests on signed `ticks_diff` from a fixed epoch, and long dev twin runs (manual or CI) may exceed half the period.
6. ASSUME/LIMIT digital_twin/_sgp40_chip.py:72-75 and _scd30_chip.py:177-196: the fakes silently accept unrecognised commands and never check argument CRCs, so a wrong command code from a driver passes at the twin tier.
7. DRIFT digital_twin/README.md:667-669: README says the suite has no elapsed-time budget for ResetErrors, but `scripts/_digital_twin_ci_suite.py:116, 273-281` asserts `_RESET_ERRORS_BUDGET_S`.
8. RISK tests/test_digital_twin_bus_hazard_concurrency.py:177-178 and :233-235: wozi's i2c1 grouping and its FRAM fault recovery are verified only by this twin run. Twin I2C transactions take zero time (see the LIMIT at :112-127).
9. DRIFT tests/test_digital_twin_sensortask_integration.py:178-179, 184-186, 415-417: these point to a "Construction across every real device" section that no longer exists in the file.
10. LIMIT digital_twin/README.md:354-358 and run_generic_integration.py:194-196: single-chip persistence globals, and `--fault`/`--hang` reach only the first instance of a multi-instance driver. Multi-instance devices are only partly covered.

### H07 — tests_hardware/ code (97)

1. FRAM evidence fabrication/overwrite by device scripts: `device_scripts/fram_error_log_reset_race_seed_and_race.py:14-15, 28-31` + `fram_error_log_reset_race_verify.py:31-32` leave errno 5/6/7 entries in production's chunk 0 (the exact CLAUDE.md incident shape); ~12 further scripts overwrite chunk 0 or raw address 0 (`fram_same_device_rw_concurrency.py:13`, `fram_manager_roundtrip.py`, `sgp40_fram_backup_restore.py`, ...) — covered-by HW.T17, but the concrete list is new.
2. Gate mechanics: only `persistence_write`/`scd30_extra_write` deselect (`conftest.py:116-133`); `long_soak`, `flash_cycle`, `multi_day_rollover`, `neopixel_sweep` are in-test skips, plus an unconditional `@pytest.mark.skip` (`bench/test_hotspot_role_reversal.py:232-241`) and firmware-absence skips (`bench/test_uart_link_under_api_load.py:39-57`, `flash/test_uart_crossover.py:19-34`) — HW.T13/SCR.T05.
3. `neopixel_sweep` help says "Spends no write of any kind" (`conftest.py:65`) while `isl29125_mechanism_envelope.py:100-196` makes ~9 flash writes — HW.S05.
4. Unrestored persisted state: garbage-SSID PUT with pre-restore asserts outside try/finally (`bench/test_network_resilience.py:520-533`); WarnCO2=1700 never restored (`test_hotspot_role_reversal.py:274-281`); SCD30 NVM `set_ambient_pressure(1013)` / `set_temperature_offset(4.0)` never restored (`scd30_same_device_rw_concurrency.py:67`, `bus_concurrency_scd30_write_vs_siblings.py:75`) — HW.T03.
5. Vacuous or weakened oracles: `is_device_present() or http…` short-circuit (`bench/test_end_to_end_timing.py:85-88`); DNS/NTP "real UDP" tests assert only absence of failure words (`bench/test_wifi_networking.py:54-70`); manual `confirm()`-only tests can never FAIL (`manual/runner.py:27-28, 94-98`); scheduler test passes with nothing dropped (`scheduler_saturation_drop.py:43, 54`) — HW.T05.
6. Contradictory in-file claims about whether an "Unchanged" PUT fires `post_asy_fct` (`bench/test_network_resilience.py:270-272` vs `434-436, 514-516`) — XCUT.T11.
7. Known transient over-admission by one above `max_connections` under load (`bench/test_network_resilience.py:646-648`) and ceiling rejections leaving no log trace (`:690-693`) — REST.T06/REST.T08.
8. Committed credential copies for the consistency topic: `conftest.py:165`, `test_network_resilience.py:505`, `test_hotspot_role_reversal.py:43`, `manual/manual_wifi.py:19,30`, `wifi_reconnect_after_failed_attempts_repro.py:9-10,109`, with two different stated sources of truth — HW.T11/HW.S08/HW.S24.
9. Host hazards: `conftest.py:187` calls `join_dut_hotspot()` (which does `ap_down()`) outside the try/finally that restores the AP, and scans while the AP is still up against `is_ssid_visible()`'s stated precondition (`bench_control.py:195-196`); iptables/netem left on a killed run — HW.T12.
10. Tree-vs-image and measurement provenance: every ceiling/body-cap oracle reads the TREE (`harness.py:39-41`, `test_network_resilience.py:617, 768-770, 800-807`), and thresholds rest on single dated measurements (`heap_headroom_after_full_system_build.py:36-39`, `uart_idle_poll_rate.py:20`, `uart_read_never_blocks_the_loop.py:15-19`) — HW.T19/HW.T16.

### H08 — tests_hardware/README.md, the queue, the handover, dev_legacy/, mockdata/ (37)

1. RISK tests_hardware/README.md:429-438 (+ queue :330-332, handover :172-175) — every isolated-driver device script overwrites production FRAM chunks, and one fabricates a plausible SYSTEM entry; the board's error logs are not a clean record (HW.T17).
2. RISK tests_hardware/README.md:529-538 (+ queue :339-341 "It has happened") — role-reversal stage 6 can reach the terminal `_PHASE_DEACTIVATED`; stage 0 clears the persisted SSID; routine bench runs include it (HW.S25, HW.S10).
3. OPENQ REAL_HARDWARE_TEST_QUEUE.md:262 / HARDWARE_TEST_HANDOVER.md:159-162 — F18: connection admission has no fairness (a `ResetErrors` writer refused 20×, no answer in 30 s) and the UART link degrades under 4 zero-think-time readers; owner decision.
   → `4dc80ef`: F18 open as an owner decision, BACKLOG.md:380-387
4. RISK REAL_HARDWARE_TEST_QUEUE.md:297 — W5: a ~1,026 B over-cap response piece (`NTP_Host` bound) "fits by argument, never by measurement" at the limit of 6.
   → `4dc80ef`: W5 measured 2026-09-25, SPECIFICATION.md:4946-4949 (`6e40e27`)
5. TODO REAL_HARDWARE_TEST_QUEUE.md:276 — G8: CLAUDE.md's (e) stage (zero allocation failures at `gc.threshold(-1)` under real load) has never been asserted on silicon; every flash/bench run is an (f)-stage run.
   → `4dc80ef`: G8 retired, covered by `test_serving_sweep_at_the_reactive_default` (`2f48f86`)
6. RISK HARDWARE_TEST_HANDOVER.md:176-178 — an `mpremote` attach within ~1 s of boot parks the board at the REPL with no watchdog armed and it never recovers; not yet in README/traps.
   → `4dc80ef`: in `tests_hardware/README.md:390-393`; the flash tier ends with `hard_reset()` (`79eb41b`)
7. DRIFT tests_hardware/README.md:635-641 — presents the independent WiFi reachability check as an undecided owner question; CLAUDE.md and BACKLOG item 6 say it is settled.
8. DRIFT tests_hardware/README.md:510-513 — ticks_ms/soft-reset question still "open" and the rollover test "deliberately uses `board.exec()`", while BACKLOG item 12 answered it and queue G6 says the exec-poll design cannot measure.
9. ASSUME tests_hardware/README.md:574-595 — the whole bench tier implicitly requires live `DebugLevel` ≥3 (5 for NTP); at 0 every `dut_ip`-dependent test cascades.
10. DRIFT dev_legacy/README.md:537-543 with RISK tests_hardware/README.md:845-857 — docs instruct `ResetErrors` before (and after) runs with no read-first step, against CLAUDE.md's FRAM-forensics-first rule (HW.S06).

### H09 — scripts/, toolchain/, buildgen/, .github/, devices/, root Python config (57)

1. scripts/_digital_twin_ci_suite.py:127-133 — the soak's mem sampler runs `gc.collect()` in the DUT every 25 ms, so Run 11 measures a heap collected far more often than either GC stage it claims to test (MEM; related TEST.T03, new).
2. scripts/run_digital_twin_ci.sh:10-11 + _digital_twin_ci_suite.py:6 — both claim the shell script "owns clean" and is "deliberately redundant"; no shell-level clean exists (new DRIFT).
3. toolchain/setup_toolchain.py:33-36/335/379 — `-Wno-array-bounds` applied to every translation unit of firmware and both Unix ports, not just mbedtls, while every other warning fails the build.
4. scripts/test.sh:363-364 + :378-380 — a MemoryError printed in a timed-out attempt is discarded if a retry passes; intermittent hangs pass if any of 3 attempts completes.
5. .github/workflows/ci.yml:59-64/88-93 — web tests are success-gated on web lint, contrary to CLAUDE.md's sequencing-not-gating rule for the Python lanes.
6. buildgen/codegen.py:301/303/604-616 — `type: ignore`/`noqa` emitted into shipped generated modules that no lint/type pass reports (with GEN.S17).
7. scripts/cross_browser_smoke.mjs:476-501 — missing WebKit/Firefox/Edge is a warning only; the run passes as long as Chromium ran.
8. devices/dev.toml:96-98 — TOML declaration order fixes the FRAM chunk layout; the "byte-identity constraint" it cites is undefined (XCUT.T09).
9. pyproject.toml:18-24 / 168-169 / 214-215 — "PINNED like every tool" (pytest/mpremote unpinned), "three known credential sites" (eight exempted files plus six TOMLs), "never scattered # noqa" (several exist).
10. toolchain/micropython_overrides.py:37-57/105-127/166 — the anchor set (unix_kbd_intr line; lwipopts_common defaults; rp2 CMake include order; lwipopts include; board cmake line; board-dir shape) that must be re-verified on every pin move; unix_kbd_intr has no post-build proof (TOOL.S07).

### H10 — tests_scripts/ (65)

1. LIMIT tests_scripts/test_comment_block_cap.py:59 — any tag substring exempts a whole over-cap comment block; the gate is weaker than CLAUDE.md's "prose introducing tags is not exempt"; JS/CSS/config remain review-only.
2. LIMIT tests_scripts/test_persistence_write_marker_completeness.py:99-121 — wear guard sees only literal-method/literal-body `fetch()` PUTs; device_scripts/, mpremote writes and non-fetch HTTP are outside it; helper callers' markers unverified (:307).
3. DRIFT tests_scripts/test_persistence_write_marker_completeness.py:194-196 — "Exactly one exists today" vs two `_JUSTIFIED_UNREADABLE_BODIES` entries.
4. LIMIT tests_scripts/test_request_body_cap_headroom.py:79-107 — body-cap headroom computed from @web-tagged fields only, compact JSON, chars not bytes; ASSUME 24-char number bound (:23-26).
5. ASSUME tests_scripts/test_digital_twin_boot_contiguity.py:46-80 — I.4(f.1) guard bounds are single-campaign twin measurements with thin (~1.4x) margins; no MemoryError scan of probe output (:127-140, TEST.T18).
6. LIMIT tests_scripts/test_gc_collect_sites.py:15-59 + test_lint_sh.py:86-98 — gc.collect guard covers src/ (name `gc` only) and buildgen presence; lint.sh allowance is file-granular; tests/ and digital_twin/ unchecked.
7. RISK tests_scripts/test_tests_hardware_conftest_constants.py:72-81 / test_buildgen_generate.py:405-411 / test_buildgen_validate.py:92-94 — shared hotspot password pinned in 3+ places; out-of-bounds TOML values silently fall back to src defaults at boot.
8. ASSUME tests_scripts/test_http_client_ceiling_close.py:31-36 vs test_ceiling_probe.py:106-107 — ECONNREFUSED is a real failure for one oracle and the PCB-exhausted wall for the other.
9. LIMIT tests_scripts/conftest.py:55-60 (+ boot_contiguity :101-109, coverage_runner :20-28, overrides :44-49/:346-350) — toolchain-dependent tests SKIP when unprovisioned, while test_live_twin_ceiling_parser.py:20-25 hard-FAILS without node.
10. DRIFT tests_scripts/test_device_tomls.py:3 — "until Session 3's generator/validator exists": a second hand-written set of collision checks (own `_BASE_DOC`) duplicates buildgen.validate.

### H11 — js/, html/, tests_js/, web config (37)

1. tests_js/_put_field_cases.js:11-14 (MIRROR) — six hand-kept "special field" lists (H.4, H.6, definitions `dispatch` flags, mock SENSOR_QUIRK_FIELDS, mock-matrix GET_READBACK_QUIRK_FIELDS, live ALWAYS_REMOUNTS_AS) disagree on ContMeas/ISLCalibrate/ForceCalRef/PauseTime; H.4 says derive from tags.
2. tests_js/live-backend-put-matrix.test.js:80-83 (LIMIT) — test tolerates "the real backend's Unchanged detection doesn't reliably fire", citing an H.7 statement that doesn't exist.
3. js/render.js:235-244 + html/definitions/wozi.json:290-293 (MIRROR/LIMIT) — every /status submit shows Valid, including ResetErrors="No" (dispatch always sent) which the server treats as a no-op.
4. js/render.js:219-223 (LIMIT, SEC) — reboot/bootloader/ResetErrors PUTs carry no auth or CSRF token.
5. tests_js/_live_matrix_command.js:9-12 (ASSUME) — live matrix computes expected captions with the formatter under test (oracle = SUT).
6. html/definitions/wozi.json + dev.json provenance (DRIFT) — "hand-written" vs "generated, never hand-maintained" vs "generated and committed"; dev.json is formatted like generator output (covered-by WEB.S13).
7. js/mock-server.js:251-254, js/render.js:132-135, tests_js/render.test.js:1016-1018, tests_js/mock-server.test.js:545-546 — client and tests still model the dropped-result server gap that H.6 (SPECIFICATION.md:4525-4527) says is fixed (covered-by WEB.S12).
8. tests_js/_live_twin_command.js:218-235 + tests_js/live-backend.test.js:46-48 (LIMIT) — the "connection ceiling" browser test runs half the ceiling by design, so it never reaches the ceiling.
9. html/definitions/wozi.json:72-75 (LIMIT) — ContMeas has no `dispatch` flag and no GET readback, so after a reload the UI shows On even after measurement was stopped.
10. tests_js/mock-server.test.js:325-327 vs src/asy_scd30_driver.py:506 (MIRROR) — mock and live matrix assume ForceCalRef always reads 400; the driver comment says only "after a power cycle".

### H12 — SPECIFICATION.md lines 1-3421 (Parts A-E)

1. DRIFT SPECIFICATION.md:2501-2507: C.14.2 says `asy_notification_service.py` imports `NeopixelDriver` and wirable drivers import `AsyFramManager` at module level. Neither is true: there is no NeopixelDriver import, and the AsyFramManager imports are TYPE_CHECKING-only. New.
2. DRIFT SPECIFICATION.md:1521-1523 vs 2443-2449: C.2 still describes `_WIRING` as a 2-element Python tuple. C.14.2 says it has been a 5-field `# @wiring` comment since 2026-09-10. New.
3. OPENQ SPECIFICATION.md:535-537: the `CFGMGR_SYSTEM` setup-order fix costs +0.90 s of real boot latency, which is unexplained (queue R6). New.
4. RISK SPECIFICATION.md:1835-1844: a `ResetErrors` that answers OK after a write the chip did not store is accepted (owner, 2026-09-17), on the basis that the chip is "trusted". The evidence wipe also interacts with REST.S04.
5. ASSUME SPECIFICATION.md:228-230: says a reset has an "ample" FRAM margin (low single-digit ms), while C.7 measures ~305 ms per chunk and 21 chunks. Related to XCUT.T03.
6. DRIFT SPECIFICATION.md:1827-1830 vs A.7:487-497: the two sections disagree on where each FRAM logger's `pr.setup()` runs (inside its task vs the pre-task batch). This matters for CORE.S03 and the ResetErrors boot window.
7. INVAR SPECIFICATION.md:159-161: "never import `async_manager`". In the flat frozen namespace such an import resolves silently, and no guard exists. New.
8. PLATFORM SPECIFICATION.md:2010-2014: pinned cyw43 copies an SSID over 32 bytes past a 36-byte buffer unchecked. The byte bounds live only in `asy_wifi_service`; the web UI checks characters.
9. DRIFT SPECIFICATION.md:976-980: says the real firmware-build test is parametrized over wozi/dev. The code uses all six `DEVICE_NAMES`. New.
10. RISK SPECIFICATION.md:1313-1320: when the lwIP `MEM_SIZE` arena is exhausted, `modlwip` `tcp_write` retries can block the whole VM for up to 10 s, and no asyncio timeout can interrupt it. Covered by PLAT.T04.

### H13 — SPECIFICATION.md lines 3422-6785 (Parts F-M)

1. DRIFT F.1:3439-3444 vs L.4:6286-6288: the owner's "no `__import__`/`importlib` anywhere" rule is broken at 9+ sites (`digital_twin/run_generic_integration.py:356`, four `tests/` scenario helpers, `buildgen/validate.py:6,194-197`), and L.4 documents one of them. Frozen-set soundness (L.2:6079-6082) rests on this rule.
2. DRIFT I.6:5184-5195 and 5236-5255: the body-cap exposure maths (4 × 2048) and the whole W5 reset analysis still assume `max_connections = 4`. It is 6 now (related REST.S11).
3. DRIFT J.7:5555-5556: says `digital_twin/machine.py` "has no `UART` at all today". Four lines later the doc says both models exist, and `UARTLink` is at `digital_twin/machine.py:481-488`.
4. DRIFT G.2:4234-4236 vs L.3:6223: G.2 still prescribes a `_WIRING: "WiringSchema"` Python tuple, but `src/` only has `# @wiring` comment tags.
5. INVAR F.5.7:3869-3875: `asy_uart_driver.UART.init()` must construct `machine.UART(...)`, not re-`init()`, or rp2's heap gets corrupted. Only a comment and a hardware injector guard this.
6. INVAR/DRIFT F.5.8:3905-3926 and F.5.9:4037-4042: the claims "every read clamped", "all seven paths guarded" and "the only deadline-less wait is `uart_listen`" are contested by BUS.S05 and BUS.S06 (readline paths, `_write_all`).
7. RISK F.2:3624-3644: the accepted deferred-flush power-loss window, and the related DRIFT with CLAUDE.md, which still says "structurally cannot have a write in flight". The "single scheduler tick" size is unmeasured. M.1.5:6746-6749 depends on the same REST-only write premise (SENS.S24).
8. LIMIT I.3:4922-4933: `NTP_Host`'s settled 1,024-character bound produces a ~1,026 B piece. That is outside the 256 B bound, only argued, never measured, and would not fit at `max_connections` 7.
9. INVAR J.6:5516-5524: "must be constructed with a single-digit `poll_wait_ms`" has no enforcement (buildgen checks only the floors). J.5/J.6's Class A constants and the C-side re-verification obligation (5335-5336) have no reachable executor.
10. DRIFT F.5.6:3832 ("21 `const()` files", 25 now), F.1:3512-3515 (the const-attribute claim conflicts with upstream docs) and F.5.3:3778-3780 ("hardware" sqrt on a Cortex-M0+). These are PLATFORM facts that need re-checking against source at 1.29.0.

### H14 — CLAUDE.md, README.md, DEVICE_REFERENCE.md, update_and_install.txt

1. **ASSUME CLAUDE.md:199-201**: "every real flash write is reachable only through the REST PUT path". This premise backs a SETTLED backstop rule and the ruff ASYNC230 ignore, but boot-time `ConfigManager.setup()` rewrites and deferred post-response flushes are exceptions (related CORE.S02/CORE.T12/CORE.S17).
2. **DRIFT README.md:611-613**: the README says an int sent for a float field is rejected as "Invalid". The code accepts it (`src/config_manager.py:130-134`). A user-facing contract is misdocumented, possibly also in the Part A.8 mirror to js.
3. **DRIFT README.md:465-467 vs 579-582/614-619**: twin FRAM/SCD30 state defaults to in-memory, yet the walkthrough promises it persists across restarts to `digital_twin/*_state.json`.
4. **INVAR CLAUDE.md:111-116**: `ext/microdot.py` is "byte-identical to v2.6.2" on the strength of one dated check. No gate re-verifies it, and the whole REST layer relies on that vendoring premise.
5. **INVAR CLAUDE.md:119-126**: the UART C-port changelog obligation is convention only, with no completeness check. With DOC.S14, the file has no deletion trigger.
6. **LIMIT CLAUDE.md:329-335 / ASSUME :331-333**: the zero-MemoryError bar is enforced by four gates only. It depends on `src/` logging `str(e)`, a convention nothing enforces (TEST.T18).
7. **INVAR CLAUDE.md:237-245 (+ DRIFT :240-245)**: the four-tier bus-hazard rule is mechanical only at the mock tier (`tests/test_bus_hazard_generated.py`, which the rule's own list omits). The twin, flash and bench tiers are review-only.
8. **DRIFT CLAUDE.md:511-513 and README.md:115-117**: "no lint/type config yet ... future decision" contradicts the owner's "legacy tree reference-only, forever" rule (CLAUDE.md:170-177).
9. **INVAR CLAUDE.md:367-379 + LIMIT :387-394**: FRAM-forensics-before-ResetErrors is convention only, with no automatic errcount snapshot or board-run history (HW.T02/HW.T17). Evidence loss is irreversible.
10. **SETTLED CLAUDE.md:693-695 / WORKAROUND :681-695**: the "don't re-diagnose" shutdown-flake rule presumes the `unix_kbd_intr` override is applied. Only its source anchor is checked, and the CI cache key omits `micropython_overrides.py` (TOOL.S07, CI.S01).

### H15 — BACKLOG.md, HEAP_FRAGMENTATION_MEASUREMENTS.md (+ archive at 12640c2), UART_C_PORT_CHANGELOG.md, licences

1. [012] The standardized timeout/cancellation mechanism, which the owner PRIORITISED. No plan topic covers it.
2. [046]/[047]/[048] Item 30, the ISL29125 connection reset. Root cause open, the DUT logs nothing, and the test retry masks it.
3. [039]/[049] Items 24 and 32. The ResetErrors sweep reaches 88-98 % of the 15 s cap at 3 readers, and the bench tier has no elapsed-time budget.
4. [032] The premise of item 4 ("a write never happens on its own") conflicts with CORE.S02 and CORE.T12 (boot-time rewrites).
5. [053] The premise of the SETTLED SPI-EIO decision conflicts with CORE.S16 (a transient read overwrites the ring).
6. [023] The ISL29125 divergence entry is stale against queue R9.
7. [106]/[111]/[112]/[119] The lwIP and firmware build overrides have never gone through either chroot leg. The owed list also omits some changed scripts.
8. [179] The writer defect behind the malformed concatenated config file was never found. It is dropped from the current docs.
9. [170]/[176]/[177]/[185] Archive open questions not carried forward: Gap 2 at real positions, run-phase months, the third boot stretch without a collect, and the refused-client retry cost.
10. [212]/[200] The A7 CRC flag day is recorded but not triggered (dev runs CRC_Pass). The changelog's deletion trigger is unreachable.

### H16 — legacy tree: python/, modules/, html_raw/, build-*.sh (parity oracle only)

1. RISK `modules/sensortask-wozi.py:316-321` — trailing commas make SCD30 readbacks 1-tuples, so legacy wrote MeasInt/AmbPres/Altitude/ForceCalRef/SelfCal to NVM on every non-empty PUT value; changes the premise of `PAR.S02`/`SENS.T07` (same in arzi/neu `:277-281`).
2. RISK `python/IndividualDrivers/asy_sgp40_driver/__init__.py:339,341-352` — the legacy general-call reset never ran (un-awaited, and aimed at 0x59 not 0x00); the refactor's bus-wide broadcast (SPECIFICATION.md:2055) is new field behaviour, not parity.
3. DRIFT `python/IndividualDrivers/asy_bmp3xx_driver.py:56-59` (+ `modules/sensortask-wozi.py:373`, `html_raw/wozi/sensorconfig.html:142`, `build-*.sh:1-3,40`) — the legacy tree at HEAD was edited after the initial commit (2bda920, b6cb852), so it is not what fielded wozi runs; feeds `PAR.T15`.
4. RISK `python/CommonDrivers/async_manager.py:115-129` (+ `:126-127,178-179`) — legacy wipes all of `config.json` to defaults on any missing key or bad JSON, and writes non-atomically.
5. RISK `python/CommonDrivers/async_connect.py:347-362` (+ `:183-192`) — legacy origin of permanent WLAN deactivation (second failure streak, or an invalid config read at task start).
6. MIRROR `python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:91-164` — legacy VOC state is "31q"/248 B vs src "32q"; not interchangeable across reflash or rollback (`PAR.S09`, `PAR.T14`).
7. RISK `modules/_boot.py:4-12` — legacy formats littlefs on any mount exception; the key fact for a 1.29 → 1.26 rollback (`PAR.T14`, `PAR.S10`).
8. RISK `modules/sensortask-wozi.py:570-573,585-608` — `all_running` never recovers: failed `fram.setup()` or a persistently failing sensor reboot-loops the unit (`PAR.S12`, `PAR.S04`).
9. INVAR `python/CommonDrivers/api_helpers.py:160-183` + `:33,42-45` — legacy error codes 0-10 and `""` = "Unchanged" semantics vs `src/api_response.py`'s 0-5/100 (`PAR.T11`, `NET.S17`).
10. LIMIT `python/IndividualDrivers/asy_fram_manager.py:279-329` (+ `:219-223`) — legacy reads rewrite status bytes and treat BUSY/mismatched copies as invalid; decides what a rollback does with the refactor's FRAM layout (`PAR.T14`).

### H17 — all commit messages to 2a88cc8, GitHub issues and pull requests (read-only)

1. commit 41762dc / merge e5d2c43 — Owner-decided D.15 docstring-reorder task lost in a merge; SPEC D.15 (SPECIFICATION.md:2725) still says "no change", 9 classes non-compliant — UNTRACKED
2. commit dfb85ff — CLAUDE.md:199-201 ("structurally cannot have a write in flight") contradicts SPEC F.2:3632-3640 residual-risk window — UNTRACKED
3. commit 21560a4 — SGP40 W13 ring flood without NTP, attach-within-1s parks board, FRAM E31/W73 after bootloader: only in temporary HARDWARE_TEST_HANDOVER.md — UNTRACKED
   → `4dc80ef`: all three now fixed or tracked (see the ONLY-IN-TEMP-DOC entries above)
4. commit 8a45060 — Owner principle "no error/warning for expected startup jitter" never promoted to a rule — UNTRACKED
5. commit 2bda920 — Legacy tree edited (BMP3XX tuple fix) despite reference-only rule; FiltCoeff migration parity — UNTRACKED
6. commit e05f015 — Deployed fleet runs MicroPython 1.24.1 with on-device edits never copied back (docs say 1.26) — UNTRACKED
7. https://github.com/hundertvolt/sensors/pull/41 — DNS QNAME total ≤255 not checked; reachable via NTP_Host 1024 bound — UNTRACKED
8. https://github.com/hundertvolt/sensors/pull/95#issuecomment-5692708409 — tests/machine.py Timer.all_timers unbounded registry (fragmentation MemoryError), masked not fixed — UNTRACKED
9. https://github.com/hundertvolt/sensors/pull/53 — manual_wifi.py:40 says no HTTP redirect though captive redirect exists; DHCP Option 114 decision unrecorded — UNTRACKED
10. commit 04ef56a — I2CDevice session burst has no scheduling point (asymmetry with UART yield) reported, not changed — UNTRACKED
