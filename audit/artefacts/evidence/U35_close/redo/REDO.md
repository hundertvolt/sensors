# U35 redo plan after the container reset (lead, 2026-10-26)

Base: `656fc82` (= gate 2's 7851668 outside audit/; LEAD NOTES 118, 149, 151). Sources: the five verification tables
and hand-backs (`S/u35r/verify/V1-V5*.md`), the recovered notes (`S/u35r/recovered/`), the snapshot's briefs and
hand-backs (`S/u35/briefs`, `S/u35/handbacks`). Owner rules in force: `S/u35r/recovered/owner_rulings_after_LN118.md`;
2026-10-26: recover and redo, be really sure; firmware really complete, nothing pushed to future units; prepare the next
units in parallel where sensible; stop after U35 for the hardware round. Every item below names its source.

## Firmware (lane F): all of it lands in U35
F1r (src/asy_webserver_service.py, asy_base_classes.py, asy_sgp40_driver.py, comments in scd30/uart_driver; their tests)
- OF-142 the flat GET's unavailable marker read by its whole shape (F1_final.md; V5).
- SensorReader `logger=` restored with its test, owner's library rule (F1_final; V1 step 12, V2 step 72; V5 N2); the
  stale "(C.7)" reach-through comment at tests_scripts/test_lint_ceilings.py:52 (V1, NO RECORD); C.14.1's
  "always agree" sentence at SPEC:4433-4434 to D3 (V1, NO RECORD).
- sgp40 `_exchange()` dead reply bound removed with its proof (F1_final; V5 N3).
- The 7 narrowing comments (F1_final; V5 N4); webserver:949 "persisted" -> "traced" (LEAD NOTES 116; V5 N5, NO PLAN).
- The hotspot-exit guard test (F1_final: cannot occur; the test pins it).
- The first-boot scan, re-done and recorded (F1_final item 4; CONFIG_LOST kept, LEAD NOTES 147).
- The library-rule classification of e51's direct-test-only and unreachable lines: after CEr's e51 table (the lost
  verdicts are re-derived), each line classed feature/guard/dead as F1 did (F1_final item 3: uart's three `if not
  want:` kept as the never-block guard, scd30:735 kept, isl lines kept as features, webserver :425/:903 kept,
  system:441 reachable by a cancel with its direct test).
F2r (fram_manager, fram_driver, notification_service, ntp_client, uart_link_driver, uart_driver:779, html/style.css)
- OF-250 erase_ready()/get_write_protected() in the chip-loss window; OF-232 the age check outside the producer's try,
  plus the exact-age test at :230 (CF1b); OF-247 the NTP resync cadence from elapsed time; OF-242 the UART frame copies;
  OF-139 the light-theme contrast >= 4.5:1; OF-245 the six catalog codes' tests. OF-103's equality test is already in
  the tree (V5: tests/test_asy_neopixel_driver.py:1139-1145): its row closed in REC2, not redone.
F3r (src/asy_print_log.py): a caught MemoryError prints its text through console() at every level (LEAD NOTES 146),
  test first; then the whole tier at both stages and the dev and wozi twin CI, every marker root-caused (V4 step 139's
  premise depends on it; V5 N1).
F4 (owner, 2026-10-26, LEAD NOTES 155-157): F4a OF-122's guard in the modlwip copy; F4b OF-107's boot-entry record;
  F4c OF-122's silicon check prepared (after F4a). F3r also takes F2r's NTP unsynced-wait finding.

## Twin and suite (lane T)
T4r1 (scripts/_digital_twin_ci_suite.py, digital_twin/_fram_chip.py, digital_twin/README.md, the twin test files)
- Run 11's calibration values 80 / 4.0 / 100 ms, gc.collect() kept, each with its source; bitten by a planted leak at both
  stages (owner Q1 "This is okay, go ahead."; V4 step 157). The sampler decision (R-22, step 165) recorded.
- TimeStale checks (null in Run 1, false after Run 8's first sync) (V3 118, V4).
- The twin FRAM save limited to the used span (host wear; V4 150). writes_at presized at construction with its
  heap-locked test (T4a2_final; V3 109; V4 150).
- Run 5b deterministic or stating what it proves (T4a amendment 2 item 8).
- README steps 167, 169, 170, 171 (V4) and the `boot phase:` text; the "no REST route" comments at the runner (:412)
  and suite (:210) corrected (MemFree is published, buildgen/codegen.py:293) (V4, NO RECORD).
T4r2 (after T4r1): the smoke boot's exact one-entry check and the runner's latest-boot phase line (T4b2_final); folds
  (1)-(3) with the scenario-scoped SO_SNDBUF knob (T4b3; V3 125); the escalation timeout scenario and the
  `_UART_LOAD_REQUEST_S` plant proof (T4a item 6); the conformance.md OR130 L2 cell's missing "Run 3" (V4);
  tests/test_digital_twin_uart_link.py:193's frame given CRC room like the ack beside it (F2r).
T4r3: M.PROC.024: the 2**30-period ticks build rebuilt privately, (1) the other L1 tick files under it, (2) the twin
  suite with the wrap inside Run 11's window, one device per stage (V3 108); F.1's sentence restated after (V3 112).

## Coverage and e51 (lane E)
CE2r: the coverage tracer death: runner probe, `.incomplete` note, test.sh exit 3, E.10's text; tests/_untraced.py and
  the C-stack test files through it, the twin integration file's :507 included (lead_notes_119_148 facts; V3 111).
CEr (after CE2r and the F lane's src changes): one coverage run on the merged head; e51_sweep.py rewritten; e51.md and
  its verdicts; every uncovered src line classed; the owed direct tests (CE3_final's 30 as a checklist, the rest
  re-derived) each red on a plant first; the E.5.1 register text for D3.

## Campaign records (lane C)
CRr: redflags.py and review_rows.py rewritten; review.md (every test, its verdict); the test fixes the scan finds (CR2's
  14 re-found; CR3's 6 known); the 42 device-script facts and 7 host assertions (CR3_final); the bench
  no_unprovoked_log_entry fixture and provokes_log marker (CR4_final); the bmp3xx unbounded run() fix (CR4); then the
  flash tier's per-script `logs` fact (CR4's plan; V3 102 NO RECORD after CR4).
CFr: plant.py rewritten; faults.md; plants only for complex measurement checks (owner Q2), the named bites, the boot
  entry's five, the K rows; CF1b's 12 fixes as a checklist; CF1c's items (two exact-bound tests, the unbounded waits, the
  pair_scan retarget, fram_two_entries re-read, the modlwip control under `make -n`, the uart test rename); K.10's
  planting rule restated with the owner's scope to D3 (V3 128, NO RECORD).
CMr: N5's hardware predicate first (blocks_n4_n5_d3.md), then the all-device picks (CM_final + CM2's list; V3 99, 123,
  124), the scanner's comprehension scope, a shared boot per device job, the bites; CM3 (all pairs, config-value
  dimensions, zz_test_ fixtures booted cheaply); CM4 (interaction matrix, recombination row).

## Measurements (lane B)
B2r: timing.md's B0, post-refresh and post-B3 columns (the B0 and post-refresh values from the evidence of U0/U21; the
  post-B3 column from today's baseline runs on 656fc82, S/u35/lead/base_testsh_*.log) and the heavy-file order (steps
  107, 120, 161); the walks re-run and raising.md's 414 rows classed (V3 104); step 136's reasons reviewed and
  reasons.json rebuilt (V4 136); conformance.md's open rows (V1 step 7, V4 138); intent.md's open rows (V4 137); the
  l0-l2 Basis values measured (V3 105, V4 147); load.md (V4 160); the FRAM both-copies-marked loss rate on the new write
  order (SPEC:229; V5 N25-N28); the queue_c twin-first column (V4 141); A.U35.15's NTP loopback confirmation runs,
  OR141.a (5)'s UDP idle-poll measurement, levels.md's multi-chunk SET ladder (V3 102, NO RECORD); the OF-150/OF-71 local
  times; the coverage shard measurement.

## Lane N (tests and tools, small)
N4r (tests_js/live-backend-put-matrix.test.js, scripts/test.sh, tests_scripts/test_test_sh.py): the probe holds NTP
  still; the tier order made structural or stated; the tests_scripts tier's host writes (blocks_n4_n5_d3.md).
N6 (NO RECORD finds): step 86's `run(conn.setup())` (tests/test_neopixel_wifi_integration.py:48); step 88's false C.7
  quotes (test_notification_scd30_integration.py:6, test_notification_scd30_sgp40_integration.py:243); the stale
  wall-clock comment (test_notification_neopixel_integration.py:99-100); step 92's builders (reset_id and
  run(reader.setup()), test_ntp_fram_system_integration.py:483-551); OF-244's two `_ruff()` copies; OF-13's tags
  (A.U8C.21, `_RUN_BOUND_S`).

## Docs and records (lanes D, R) and the close
D3r: every stale line the blocks hand back, plus V4's steps 158, 162, 163 and the E.9 history bullet (SPEC:5913), E.2.1's
  device sentence, E.5.1's register, the sampler outcome, F3's lines, C.14.1; F1r's and F2r's D3 facts
  (handbacks_redo/F1r.md, F2r.md); the F4 blocks' docs if they hand any back; F3r's stale lines (handbacks_redo/F3r.md:
  SPEC 617-618, 3446-3448, 3668-3670, 563-569, 7487-7493, 9068-9070, 9077-9078 at bc3bed11, re-located on the head). BACKLOG's chroot list: F4a's toolchain/
  change (lead).
REC2: open_findings.md corrected (the 13 U24 rows, OF-254/255/260, OF-13, OF-198, OF-103), new rows for N1-N5 and the
  NO ROW items, the lost blocks' findings, REGISTER rows, scan record, the evidence README.
W10: merge, the twin record re-recorded with the rebuilt reasons.json, the full gate at both stages with every device's
  twin, push, CI via hooks, the owner report; then stop.

## Owner questions (asked at the recovery's consolidation point)
OF-122, OF-107, OF-246; OF-16, OF-127, OF-186; REGISTER:796 (a)-(e); V1's accidental private artifact.
Added 2026-10-26: the soft-reset record (decided (b), lane F4d); its boot-phase extension (question 9, decided (b), lane F4e); report_unretrieved() silent at level 0 with a
MemoryError (F3r, after OF-246). Lead items from F3r: the synced NTP cadence's one-tick lateness (F2r's change, fix in
U35 after F2r hands back); the four now-redundant console() bypasses (kept, conservative; named in the report).

## Additions after Q35's completion inventory (lead, 2026-10-27; LEAD NOTES 256; S/u35r/handbacks_redo/Q35.md)
- Records lanes own their defects: every block on raising.md (BR), conformance.md (CO), intent.md (IN), matrices.md
  (CM3/CM4), load.md (LD) fixes a defect it finds in-lane, src/ included, with its test seen failing first, each in its
  own commit. Anything not small and local comes back to the lead as a prose question for the owner. B2r keeps only
  the measurements.
- Not in the plan before, now in it:
  - A.U35.51's wear-gate and host-churn table, conformance.md :148-150 (about 1 block; a marker fix if one is wrong);
  - levels.md: the walk re-run on the head and its 137 cells checked against review.md, plus the two entry-point
    rows (1-2 blocks), beside the multi-chunk SET ladder;
  - A.U35.57's BACKLOG chroot paragraph for U35's scripts/ changes (D3r);
  - faults.md's open named.fram_alloc row: re-planted after N11's 26af8dad, verdict recorded (with N11c or REC2);
  - queue_c.md's missing silicon items (V4 141, CR4's six unsettled bench tests), mapped to C.md H rows (REC2's
    records lane);
  - e51.md's three stale "comment owed" rows refreshed (REC2).
- intent.md's six "no test" codes (src/asy_base_classes.py:82-86, src/asy_uart_comm.py:137): P36a found them named
  by tests on the head (tests/test_asy_base_classes.py:2961, :3025, :3417-3429; tests/test_asy_uart_comm.py:3429). The
  IN block checks each one bites and closes the rows and OF-245 together.
- Records walked on old trees (intent.md and levels.md at e1ad71f, raising.md at b1bf1f3): each block re-runs its walk
  on its base first, committed alone.
