cs hand-back, written by the agent (Tue Nov 10 14:05:09 UTC 2026)
Read-only on S/wt-u35int at 651af010; nothing run, built or edited. Rows: S/u35r/r5/CLOSE_STATUS.tsv (154 items).
## Counts
DONE 71 · OPEN 77 (73 distinct; P02, P03, F9, B06 point to other rows) · OWNER 6. OPEN by kind: bench-last-round 36,
test 16, final-report 12, docs 11, build 2, **firmware 0** (no product-code item is open on 651af010).
New, outside the 11-05 INVENTORY: N01, audit/sweeps/open_findings.md's 73 open/partly closed rows (PLAN R0: "input to
R5's OR5.a"); only 4 of their IDs appear in R1/R2 action lists, so their terminal states are unrecorded.
## Records that conflict (said, not re-decided)
- U37.02/A.U0.08 "empty at U37" vs owner 11-03 (i) "permanent repo rules with their shrinking allow-lists": the later
  owner word holds for the citation (18) and vocabulary (343) lists; the rest of U37.02 stays open (U02).
- BACKLOG:379-383 "neither leg satisfied" vs FINDINGS 12.90/12.95 (noble green 11-07). BACKLOG:241-251 "4 the bootloader
  reboot" vs src/asy_system_service.py:86-98 (no code 4) and the bench test (2). BACKLOG B33/B37 and fidelity rows
  211/222 ("assumption", "needs that device script") vs READING_20261029.md:76-78 (answered 10-29).
- INVENTORY B62's owner credit (08-11) vs 12.160 (agent-only source; P9 removed it). definitions main(): C kept it "for
  the owner", the lead settled it by evidence (12.156), T removed it. A.C.09 cites codegen.py:704; the line is :830 now.
## Owner items (operational)
- O1 (H08) CI mirror check's derived rate decides nothing today (firmware 0.98 MB/s < 1 MB/s floor). Guards a future,
  larger install set from a slow mirror. Keep: no change. Drop: ~10 lines less, the owner-credited check (10-27) stays.
- O2 (H14) Kept with no product caller (rule 18:30:08): SPIDevice session_begin/session_end/*_sync, SCD30's six single
  getters, UART readline()/readline_until_complete() with _rx_line_len, the twin's --seed. Keep: nothing changes.
  Remove one: its code and tests go, and so does its possible later use.
- O3 (B29) SCD30 AmbPres across a power cut, PUT half: write the instrument (~30 lines, one SCD30 NVM write in the gated
  run; fidelity row 226 becomes measured) or record row 226 as a limitation (no wear, stays an assumption).
- O4 65 agent decisions dated 11-06..11-10 outside audit/ (28/12/16/9), after the 11-06 Q1-Q11 review: rule 4.1.9
  reviews them at the phase stop, by topic, in the final report. Accept: no change; a topic ruled otherwise: code follows.
- O5 Release number: "2.0" is an agent decision (2026-09-30) and the tag needs the owner's agreement; it fixes
  FIRMWARE/WEBSITE_VERSION, the tag and the golden fixtures' release point (P04, P05).
- O6 (B52) Chroot legs on the final tree. Option A (11-06) has the bench run both; the microSD words (11-07 14:39/14:46)
  stopped the fresh trixie rebuild (12.94). (a) Both legs in reused chroots with /tmp in RAM: few card writes, A met.
  (b) Noble only: trixie stays at 12.84's inferred reading. (c) Leave both to the owner's periodic check: A unmet.
## The last round: what the tree must hold before the image
- Before: U01's pin re-check (a new MicroPython pin reopens the image); W1 and W2 merged; one green re-verification
  pass (A.C.09's precondition); O3 and O6 answered.
- Present: the two-image proof's --image-record (tests_hardware/conftest.py:79), the record's dirty flag
  (scripts/build_firmware.py:298-305), round1.sh steps 3g/4g/5g and 3/4b/5 (bench branch); 12.169's heap-load probes
  (bench bc53cdfa); the settle re-measure (fram_chunk_timing_frozen.py, bench ac7fe7bd; begin_sync still at
  src/asy_spi_driver.py:179) with T4's flash test.
- Round 1 left (bench hw_round1/HANDBACK.md, 11-06 17:43): never run 12a-12f, 16b, 13, 10c-10h, 7f, 7b, 8f, 8b, 15;
  red or not clean on c8887b35-era images 4g, 5g, 10a, 10m, 4b, 5 (re-run on the final image); M1+S3b with the owner;
  REPORT 7 items 4, 8 and 11; crc16 with both ends' logs; OR79.a; OR50.a (3)(b). long_fram at 8 MHz is done.
- Their probes are present (round1.sh :40-47, S/u35r/hw_handover/mp) but date from 11-04, before fsync: re-read them
  against 651af010 before the image, boot_stretch_final.py first (e1958815 took the boot lists' collects).
- Missing: the AmbPres PUT-half instrument (O3) and an SGP40 serial-read script (none found).
- OR17.a twin corrections: B37 (SGP40 unknown command) needs no bench. F3 (VOC raw walk), B33, B35, B36 and B38
  follow the bench.
## Recommended units (by file ownership; final-report items last)
0. U01: the dependency re-check (read-only, 2 lines; CLAUDE.md:49-50 is the lead's edit).
1. W1, tests and tooling (tests/, tests_scripts/, scripts/, digital_twin/, fakes/, pyproject.toml, .ini): B01/U02 (7
   mypy baselines; _PENDING 68 and the PLC0415 scope entries; 3 of _NOT_YET_CLEANED's 4), H01-H05, H12, B37's twin and
   row, F3's stage root cause on the host, B27's twin half; P09's D.15 sweep (~150 files) last. Done when: those lists
   and baselines are gone with their stale-entry halves, member_order covers every scope but the unit tests, the gate is
   green at both stages, and each changed tests/ file has had a coverage-build run.
2. W2, docs and release (BACKLOG, README, SPEC L.7, version.py and its test, mockdata, tests_scripts golden): P08, the B40
   row, N05, N03, H27, then P05 (after O5), P06, and last P04 with S03 at the release point. Done when: the doc checks
   are green, the version test reads the release, both golden tests compare against committed fixtures, and the gate is green.
   Then P01's first pass, the image, and the last round (L01-L07 and the bench rows).
3. W3, after the bench, records and final report: U05 with X1 and B49; the F.3/Part N figures from L04/L05; L06's twin
   corrections; H34 (free heap: does any UART receive need one block above 11.4 KB?); N01, N02, U17, U04 (1), P07 with
   OR49.a (3), O4's list. Then P01 until one pass is green, then D (S05, S06, B60, H36, the merge, the tag). Done when:
   every TSV row is DONE or names its D step.
