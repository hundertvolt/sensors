# U25 lane plan refresh: v0 (`lane_plan_draft.md`, sites at `e14d76f`) → v1 (`lane_plan_v1.md`, sites at `8e7dedc`)

Agent, 2026-10-14, file-only (git, grep and text scripts; no test, lint, build or MicroPython run). Tree: `8e7dedc`
(U24's squash `aa3530f`, then `b63d9b0` and `8e7dedc`), read through `git show`/`git grep` in `S/wt-u24w1`, never its
working files. Rules: `S/CHECKLIST.md`, `S/u21/CONCURRENCY.md` (rule 13: effort is the measure), `u25/lead_rulings_v0.md`
(binding). Every new default is conservative and reversible, decided on the owner's behalf for review (agent,
2026-10-14). `git diff --stat e14d76f 8e7dedc -- audit ':!audit/artefacts'` touches only `REGISTER.md`,
`sweeps/open_findings.md` and two scan records: the work order, the actions and the M entries are v0's.

Tools (`u25/tools/`, v0's reused; v1 outputs in `tools/v1/`): `relocate.py` (u24's, re-pointed: base `e14d76f`, target
`8e7dedc`; now also parses `:a, :b` lists), `v0_ctx.py` (the file of each bare `:N` cite of v0, given by hand),
`delta.py`/`delta_steps.py`/`delta_classes.py` (what U24 did to each packet site), `lanes_v1.py` (the cut, the sets,
the v1 placement), `refresh_packets.py` + `extract_v1.py` (the packets), `make_v1.py` + `v1/plan_edits.json` (the plan:
40 sites renumbered, 37 asserted edits).

## 1. Sites re-located on `8e7dedc`

### 1.1 v0's own sites (`lane_plan_draft.md`, `gaps.md`)

227 records: **161 unchanged, 45 moved, 11 changed, 0 gone**; 9 scratch (the U23 register drafts `:14, :35, :42, :43`,
landed in `audit/REGISTER.md` at U23's close), 1 external (pinned checkout). 106 bare `:N` cites took their file by
hand (`v0_ctx.py`: v0's bare `machine.py`/`network.py`/`neopixel.py` are the twin's). Distinct sites that moved or
changed (38; renumbered in `lane_plan_v1.md`, `gaps.md` left as v0):

| `e14d76f` site | `8e7dedc` | status | cited at (v0 line) |
|---|---|---|---|
| `audit/REGISTER.md:623` | `:675` | moved | gaps :100, plan :10, plan :19, plan :195 |
| `digital_twin/machine.py:1291-1384` | `:1295-1388` | moved | gaps :67, plan :29 |
| `digital_twin/machine.py:639-1093` | `:639-1097` | changed | plan :32 |
| `tests/_generated_module.py:24` | `:29` | moved | gaps :71, plan :34 |
| `tests/_generated_module.py:69-77` | `:108-117` | changed | gaps :71, plan :34 |
| `tests_js/mock-server.test.js:591-599` | `:594-602` | changed | gaps :13, gaps :36, plan :36 |
| `.github/workflows/ci.yml:606` | `:618` | moved | gaps :40, plan :41 |
| `.github/workflows/ci.yml:610` | `:622` | moved | plan :41 |
| `scripts/test.sh:513-529` | `:570-586` | moved | plan :42 |
| `digital_twin/machine.py:543-635` | `:543-635` | changed | plan :95 |
| `digital_twin/machine.py:1351` | `:1355` | moved | plan :99 |
| `digital_twin/machine.py:1122-1174` | `:1126-1178` | moved | plan :111 |
| `digital_twin/machine.py:1333-1348` | `:1337-1352` | moved | plan :112 |
| `digital_twin/machine.py:1201` | `:1205` | moved | plan :114 |
| `digital_twin/machine.py:1204` | `:1208` | moved | plan :114 |
| `scripts/run_digital_twin_ci.sh:35` | `:43` | moved | plan :140 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:423` | `:412` | moved | gaps :75, plan :142, plan :318 |
| `tests/test_digital_twin_sensortask_integration.py:1027` | `:1013` | moved | gaps :75, plan :142, plan :325 |
| `tests/test_digital_twin_sensortask_integration.py:558` | `:543` | moved | gaps :75, plan :142 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:470` | `:459` | moved | plan :149 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:526` | `:515` | moved | plan :149 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:555` | `:544` | moved | plan :149 |
| `tests/test_digital_twin_isl29125_autorange.py:434-441` | `:470-478` | changed | gaps :76, plan :152 |
| `pyproject.toml:252` | `:255` | moved | plan :155, plan :337 |
| `pyproject.toml:305` | `:292` | moved | plan :155, plan :337 |
| `pyproject.toml:320` | `:306` | moved | plan :155, plan :337 |
| `digital_twin/README.md:559` | `:560` | moved | plan :157 |
| `digital_twin/README.md:508` | `:509` | moved | plan :157 |
| `digital_twin/README.md:699-726` | `:700-727` | moved | plan :157 |
| `digital_twin/_fault_injection.py:16` | `:24` | moved | plan :162 |
| `tests_scripts/test_no_variant_literals.py:36-72` | `:36-69` | changed | plan :342 |
| `tests_js/live-backend-put-matrix.test.js:86-88` | `:104-106` | moved | plan :467 |
| `digital_twin/machine.py:1210-1222` | `:1214-1226` | moved | plan :565 |
| `README.md:518-519` | `:527-528` | moved | plan :677 |
| `.github/workflows/ci.yml:618` | `:630` | moved | gaps :39 |
| `tests/_bus_hazard_catalog.py:502-524` | `:560-580` | changed | gaps :58 |
| `tests/test_digital_twin_sensortask_integration.py:586` | `:571` | moved | gaps :73 |
| `tests/_sensortask_scenarios.py:822` | `:818` | moved | gaps :74 |

What each changed one means (all still owed, the cited fact holds unless named): `machine.py:639-1097` (U24's
`-EINVAL`/`poll_mask()`, A.U24.80); `mock-server.test.js:594-602` (JSON headers added; A.U25.12 (7) still pins 400
fresh and 900 after a 900 PUT, C verifies); `machine.py:543-635` (U24 landed `MSB`/`LSB`, the default and `init()`'s
refusal, `:544-545, 558, 587-588`; A.U25.16's constructor refusal is owed); the autorange scenes `:470-478` (migration);
`test_no_variant_literals.py:36-69` (U24 dropped rows; the lead re-reads its list); `_bus_hazard_catalog.py:560-580`
(the general-call scenario, A-26 holds); `_generated_module.py:108-117` (the writer now derives its file name, A-28).

### 1.2 The packet's sites (`pk/U25_steps.md`, 139 steps, the fold parts, 146 carried actions; each entry's own base)

3360 records against their bases: 97 unchanged, 1166 moved, 1113 changed, 314 gone; not re-located 439 unresolved, 231
external (as at v0, these measure U10-U24 since the audit's bases). **U24's own delta** (each site's line at `e14d76f`
mapped to `8e7dedc`; 2357 records have a line at `e14d76f`): **1162 unchanged, 1027 moved, 103 changed, 65 gone**,
138 distinct (step, change, line) entries gone or changed (`tools/v1/u24_gone_changed.txt`, old and new text), by cause
(`tools/v1/u24_gone_changed_classes.txt`): private builders renamed (D.15) 22, unit fakes following rp2 (Pin signature,
`inject_fault(op, exc_type, *args)`, `status(*params)`, NeoPixel store, SPI numbering) 22, the shared harness 16,
constants read from `src/` or cited 15, device-generic text 13, docs and comments 12, the twin UART poll comments
(A.U24.80) 9, FixedRandom 5, JSON headers in the mock tests 5, lint and typing rows 5, other U24-stage edits 14 (the
JS launch env moved into `tests_js/_twin_process.js`, strict bodies, the FRAM fake moved to
`_generated_module.fram_fake_class()`, M.WEB.063's header). **Every one is a U24 stage of its change: the U25 part
stays owed and is found by its quoted text.** Most moved files: `digital_twin/README.md` 122, the webserver concurrency
scenarios 74, `test_digital_twin_bus_hazard_concurrency.py` 66, `digital_twin/machine.py` 47 (149 unchanged),
`test_digital_twin_sensortask_integration.py` 45, SPECIFICATION.md 44, `tests/machine.py` 40. Each packet step and
action now ends with a "Sites at `8e7dedc`" block, ‡ on the 665 lines U24 touched.

**Steps already landed at U24: none whole.** In part: A.U25.49 (citations `tests/test_digital_twin_isl29125.py:12-27`,
`src_const` read `test_digital_twin_isl29125_autorange.py:37`, the generic pin `tests_scripts/test_const_mirrors.py`;
A-29). U24's own stages that v0 counted as U24's (A.U25.16's constants, default and `init()`; M.SCR.062's required
device; M.WEB.063's header; M.TEST_HELP.006/.012/.013/.015/.016/.048) are in place: the owning lanes verify them only.

## 2. Premises U24 changed, and the steps they touch

| premise (v0) | at `8e7dedc` | steps and lanes | v1 |
|---|---|---|---|
| `_TWIN_PENDING` in `tests/_machine_contract.py` | `tests/test_digital_twin_machine.py:84-89`, exact equality `:134-136`; a second, class-level list `tests_scripts/test_fake_surface_conformance.py:27` (7 classes without `TEST_API`) | MN: A.U25.02/.05 (pin checks), .07 (reset), M.TWIN.020-036 (`TEST_API`); C: A.U25.70 (`check_inject_fault_fifo`) | A-3 holds, sites corrected; MN shrinks both, the FIFO entry on its api1 resume |
| the unit fault queue (F1 9(a)) | fires the oldest matching entry; the twin's end state named only the head | C: A.U25.70, M.TWIN.002 | A-27 (oldest matching) |
| the twin injector (F1 9(b)) | re-raises one object for every queued time | C: A.U25.70 | as v0 (fresh `exc_type(*args)` per raise) |
| the twin UART (F1 9(c)) | counts no real-poll queries; the unit fake does (`tests/machine.py:752-761, 979-982`) | MN: A.U25.04 | A-32 |
| U24 F's TWIN.130 | static object per id and the buffer clamp left to U25 | MN: M.TWIN.130 (step 123) | as v0 |
| the shared harness, microtest hooks, helpers | all landed by v0's names; every twin file already migrated (lane D) | G's W1, every lane's tests | W1 shrinks to wave 1's API changes; no WIP stop for G (A-34) |
| JS twin launches in the two command modules | `spawnTwin()` in new `tests_js/_twin_process.js:113-147`, read by `tests_scripts/test_live_command_device_args.py` | SH: A.U24.53 (per-run config dir), A.U25.08/.09 (`--mem-backup-state-path ""`) | A-30 |
| the offline NTP writer (literal path) | `tests/_generated_module.py:108-117` derives the file name (`src_const` of the NTP store's `_NAME`, `config_filename()`) | R: A.U25.33, M.TWIN.053 | A-28 |
| A.U25.49's copies unpinned | cited, read or pinned by `test_const_mirrors.py` | C: A.U25.49 | A-29 |
| the per-file timeout (`b63d9b0`) | `scripts/test.sh` runs each interpreter under a shell that takes the timeout's SIGINT; `test_test_sh.py` counts deliveries | P: M.SCR.041 (the `PER_DEVICE` dispatch, U24's deferred expansion), M.TSC.135 | every per-device job goes through the same wrapper; the delivery-count case stays green |
| the put matrix probe (`8e7dedc`) | every SGP40 backup interval off before the `ResetErrors` probe (H.7); `ACTION_PROBES` comment now `:104-106` | SH: A-16's comment | the backups-off step stays after R's responder (A-30) |
| the port lock | `run_digital_twin_ci.sh:38-41` takes 53 and 18080 for every twin it starts | SH: A-9's harness call | the call runs inside the script's lock; no second take |
| U24's "nothing at U24" deferrals | M.SCR.041 (U24 step 5) → U25 step 32 P; M.TEST_HELP.031 (126) → 55 P; M.TSC.135 (306) → 75 P; M.TWIN.108 (326) → 100 P; M.TOOL.032 (52) → 32 lead (C5); M.TWIN.010/.011/.013 → C, .016 → MN, .047/.049/.057 → R, M.SCR.048 → SH; A.U24.34/.36/.37/.47/.53/.65/.70 as v0 section 0 | as listed | all already in v0's placement; v1 keeps it |

## 3. Open findings (`audit/sweeps/open_findings.md` at `8e7dedc`)

| finding | where | v1 |
|---|---|---|
| OF-149 (coverage leg, one unnamed test of `tests/test_digital_twin_sensortask_integration.py`) | G (its file) | A-33 |
| OF-155 `tests/_machine_contract.py:25`, `tests/test_fakes.py:99` | MN | the broad `except BaseException` lets the timeout's interrupt through, seen failing first with an interrupt |
| OF-155 `digital_twin/run_generic_integration.py:364` | R | same |
| OF-156 `tests_js/live-backend.test.js:9` `SMOKE_TIMEOUT_MS` | SH (tag, measured basis) and D (the Part N row, relayed) | `test_tunables_register.py` red until D |
| OF-148 | G (A-12) | as v0 |
| v0's OF-19, -42, -47, -67, -74, -87, -100, -104, -108, -112, -114, -116, -132, -133 | as v0 section 1, v1 lane names | unchanged |
| OF-151 (SCD30, ISL29125 sweeps), OF-153, OF-154, OF-155 `tests/test_generated_boot_entry.py:61`, `tests/test_digital_twin_unix_port_unretrieved_report.py:84` | no U25 set holds the files | stay open (rule 13), retargeted at U25's close (A-35) |
| OF-150, OF-152, OF-145/146 | U27, U30, U30 | untouched |

## 4. The cut (A-2)

Wave 1: **MN** (v0's M then N; WIP MN1 = M1 + N1; 20 steps, 37 changes, 22 files, ~2700 lines), **C** (12, 16, 13 files,
~1800), **R** (20, 30, 22 files, ~2000), **P** (24, 30, 37 files of which 12 removed, ~1300). Wave 2 on `<W1>`: **SH**
(S's steps, then H's, no WIP between; 16, 37, 28 files, ~3500), **G** (G1's then G2's; 9, 14, 13 files, ~3100). The lead
step (12, 13, 7 files). Wave 3: **D** (X, Y, W; 33, 35, 5 files, ~1000). The two added files are SH's (A-30). `comm -12`
over all 28 pairs: empty; `cat files_*.txt | sort | uniq -d` over the eight v1 sets: empty; 147 files. **SH sits at the
3500-line line** (A-36): the split would be v0's S and H as two lanes, H starting on S's final, which adds a lane's fixed
cost and no parallel gain, since H needs S1's `_twin_process.py` first; default kept. G (~3100, 13 files) and MN (~2700)
are under it. Changed-line figures are v0's estimates less the harness migration U24 did in G's files.

## 5. Rulings re-checked on `8e7dedc` (one line each: `briefs/rulings.md`)

- Changed: **A-1** (done: U24's API is in place by name; the one location difference is A-3's); **A-2** (the v1 cut,
  rule 13); **A-3** (sites corrected, MN shrinks both pending lists, the FIFO entry after C1); **A-8, A-9, A-12, A-14,
  A-15, A-16** (lane names; A-16's site `:104-106`, the backups-off step kept).
- Hold as written: A-4..A-7 (`TwinWiringPlan` `buildgen/twin_wiring.py:35-40`, `configure_i2c_wiring("dev")`
  `tests_hardware/isl29125_conformance.py:32`, `configure_wiring()`'s clear `digital_twin/machine.py:345-347`: unchanged
  since `e14d76f`), A-10, A-11, A-13, A-17..A-26 (A-26's scenario now `tests/_bus_hazard_catalog.py:560-580`).
- New (agent, 2026-10-14), each on the owner-review list: A-27 the fault-queue match order; A-28 the moved NTP writer
  keeps the derived name; A-29 A.U25.49's L0 only where U24's pin misses; A-30 SH's two added files; A-31 the lanes'
  WIP and merge form (one API merge); A-32 the twin UART's real-poll count; A-33 OF-149's handling; A-34 wave 2's
  in-DUT tests read from the base, no hand-over wait; A-35 the out-of-set findings; A-36 SH's size kept.

## 6. Outputs

`lane_plan_v1.md`; `files_MN.txt`, `files_SH.txt`, `files_G.txt`, `files_D.txt` (v0's sets stay; C, R, P, LEAD
unchanged); `pk/U25_steps_v1.md` and `pk/packet_lane{MN,C,R,P,SH,G,LEAD,D}.md` (v0's C, R, P, LEAD packets in `pk/v0/`);
`briefs/` (`rulings.md`, `brief_lane<L>.md` ×7, `brief_lead.md`, `launch_checklist.md`).
