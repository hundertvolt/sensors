# R5 next steps (lead, 2026-11-07 17:58 UTC; resumed 2026-11-09 17:16 after the weekly limit)
- int `audit/u35-int` f1a734f5 (bfix, bchain merged). Snapshot 52 28371bca (next PARENT, CI running) carries FINDINGS to 12.122.
  SNAP_EXCLUDE adds every ftmp_ dir by name (lead, crceng, weblog, cprim, complete1/2, ...) and crceng_probe.
- crceng (unit C) running in S/wt-crceng from a202591d (r5/BRIEF_CRCENG.md, due 01:00): native CRC engine first - it
  also closes the SGP40 chunk's ~272-round _op_lock hold that quiesce() waits on (12.117, near-critical).
- weblog (unit A) running in S/wt-weblog from f1a734f5 (r5/BRIEF_WEBLOG.md, due 03:00).
- simpler1-4 in and triaged (12.124-12.126): unit B (+ firmware items), unit T (tests, after weblog), unit C (build chain, CI), P9 docs; logprep (read-only, 21:30) preps the logging question; owner queue one at a time, twin fakes first.
- After bfix merges, units by file (two writing at most): (A, after bchain) webserver/logging: owner's (1)(2), STRETCH errcount
  fragment, the lock sites (12.111 (4)); (C) CRC engine and byte loops: one viper CRC for 8/16/32 (yields go), _rx_copy,
  FRAM compare, _bytes_to_int, UART write gate and poll floor, COBS/_rx_line_len removal check (12.115); (B) drivers:
  SCD30 bus release, BMP3XX computed wait, boot stagger, lean removals (12.107 (5)), neopixel signal wait, VOC, and a
  D.8 re-read of every 11-03 "back to pre-audit" rollback. Then the P9 doc unit (LEVELS_2 rows, twin time/WLAN rows,
  COMPLETE_1 (2)(3)(5), D.8 platform-first and poll-count rule, the ask-before-removing-a-feature rule (owner 11-09 18:30), the audit goal "minimal and optimal at the same time through smart design" (owner 11-09 19:11) in Part 0 or D.8, CLAUDE.md's version-bump practice over pure loops).
- Bench (up 11-09 until ~20:55): CRC forms and SCD30 frames done (12.113-12.114). Owed: stall.wlan_switch; req/s
  re-measure after fixes; post-B UART cadence; frozen viper on the next image. Done: complete1/2, cprim (12.110-12.115).
- 20:32: crceng merged (int 2fbad553, checks green; FINDINGS 12.128); snapshot 53 held for the owner's word on the
  >4-byte CRC width (unused-features question). Bench relays 20:00 (probe) and 20:32 (thanks, nothing more tonight;
  bench a383d840). Owner queue: Q1 twin fakes (open since 19:4x), then logging (option c: lean synchronous FRAM,
  figures 12.128), unused features (incl. the CRC width), timers, LED log, codes 44/45, setup's throwaway images.
  -> 12.134: weblog merged (int 8f04f2f1); units B (06:00) and fsync (07:00) writing; then T, C, P9.
- 21:46: int 8f04f2f1 (crceng + weblog); units B (06:00) and fsync (07:00) writing; snapshot 54 next; then T, C, P9.
- 22:01: owner 21:57 (give-ups are a pattern): rule in common_r1, B/fsync told; giveup passes 1-3 read-only, due 01:30 -> 12.135; P9 gets the Part D line.
- 22:3x: snapshot 54 red (test race, 12.136) -> fix 6aec784f -> snapshot 55 b4d87294 pushed (next PARENT), CI pending; giveup2 back, 1 and 3 running.
- 22:4x: giveup 1-3 back (12.137, 12.138; B addendum sent); owner 22:27 widened: consent passes 1-4 read-only, due 03:30; rule 'nothing new without a source' in common_r1; snapshot 55 CI pending.
- 22:53: snapshot 55 b4d87294 green (run 42711567341, 28/28) = next PARENT; consent 1-4 running (03:30); B 06:00, fsync 07:00.
- 23:3x: consent 1-4 back (12.139-12.143); ASKs settled by evidence; credit check running (03:30); B told 44/45 leave no row; fsync told get_log(name) goes.
- 01:0x: container restart; B (69c06662) and fsync (1547690d) resumed; owner question open on pre-audit credits (12.144).
- 01:2x: fsync handed back (12.145); follow-up asked (boot collects go); B gating under heavy.lock; then merge B, fsync (transform on B's files, drop 6aec784f's writer lines), snapshot, bench relay.
- 02:4x: ub merged (int ddf77ce8 = 39e18d2a's tree, gate applies); waiting for fsync's follow-up commit, then merge fsync (transform on ub's files, drop the writer waits, UART Class B entry), gate, snapshot 56, bench relay.
- 03:1x: fsync e1958815 back; mfs merge unit running (S/wt-mfs, due 07:30); then int fast-forward, snapshot 56 (parent b4d87294), bench relay; then G (+ T in parallel).
- 04:28: snapshot 56 512bb0dc pushed (CI pending) = int a293d6f9; next: unit G (bounds + firmware simplify) and unit T in parallel; one bench image after G.
- 04:30: units G (firmware bounds + simplify, S/wt-g) and C (build chain + website, S/wt-c) writing from a293d6f9, due 13:00; T after both; P9 last; one bench image after G (owner's reflash OK needed).
- 05:25: snapshot 57 e8d48fab green (28/28) = next PARENT; G and C writing (13:00).
- 05:27: owner meter 26 % since the weekly reset (lead's share estimate 35-40 %: shares overstate ~1/3); remaining G..D ~12-15 % on the meter, ~40 % total, inside the plan's 50-60 %.
- 05:4x: bench relay 05:45 pushed (bench head 24278836): zero-flash checks now; the reflash after G.
- 06:02: owner: bench is up on the 05:45 relay.
- 06:1x: bench 06:03: FRAM 26 ms per entry (5x over) -> G item 13 (command path), G due 15:00; I2C checks pass; image relay after G.
- 06:2x: bench reachability root-caused (12.153); relay 06:16 pushed (bench 967e2577); the branch is the channel.
06:3x: owner 06:26:36 ruling recorded (pre-audit credits resolved by rule: later clear decision wins; session-only goes; leftovers to owner). Read-only unit cr2 running (BRIEF_CREDIT2.md, 117 rows, due 09:30); add ftmp_cr2 and ftmp_lead to SNAP_EXCLUDE at snapshot 58. Status-pair question next.
07:1x: cr2 back (12.155): 117 resolved, LEFT 0; text -> P9, R0 growths -> T/P9. Status-pair question with the owner (gain asked, answered 07:0x).
07:3x: C merged (12.156), int 26d7f317, lint clean; combined gate after G's hand-back (G holds the lock). Owner: status pair (asked 07:1x). Queued: buildgen.definitions CLI.
08:4x: owner chose (a) for the status pair (no G item 14; P9 rewords SPEC A.4's reason). Next queued: buildgen.definitions CLI.
08:5x: G merged (12.157), int 81e2ebcd; lint + mypy clean; combined gate running (lock 'lead', tc-c). Units T (BRIEF_T.md, due 15:00) and P9 (BRIEF_P9.md, due 14:00) started, read/edit only until the lock frees. Add ftmp_t ftmp_p9 ftmp_cr2 ftmp_lead to SNAP_EXCLUDE. After the gate: coverage check over 24 changed tests/ files, snapshot 58 (parent e8d48fab), image relay with the owner's OK.
- 09:4x: gate_mg green, cov58 green (26 jobs), heavy.lock released; snapshot 58 being built (parent e8d48fab).
- 09:49: snapshot 58 910a0a62 pushed (parent e8d48fab; next PARENT once green). CI on hundertvolt/sensors#107 pending. Image relay drafted next; reflash needs the owner's OK.
- 10:0x: snapshot 58 CI: gc-threshold job red in apt install (150 s step limit vs a slow mirror, no test ran; 12.159). Re-run once after the run completes; apt-limit fix unit after P9, into snapshot 59.
- 10:1x: PR comment posted (issuecomment-6764443177). BRIEF_APT.md written (apt wall-clock limit goes; mirror check re-based on the job's timeout-minutes); starts after T and P9 are merged; add ftmp_apt to SNAP_EXCLUDE. Re-run failed job when run 42793916276 completes.
- 10:5x: P9 merged (int 6953c09f, 12.160); gc-threshold job re-run queued; unit APT started from 6953c09f (beside T). Next: T hand-back (15:00), merge T + APT, gate, snapshot 59; image relay once snapshot 58 is green.
- 11:0x: snapshot 58 CI green (run 42793916276 attempt 2; next PARENT 910a0a62). Image relay 10:58 pushed (bench 881562cf = code dab692d6 + relay); the bench asks the owner for the reflash OK.
- 11:10: bench flashed snapshot 58 (owner OK at the bench); first boot as expected; items 1-6 running.
- 11:2x: bench item 1: FRAM entry 12.7 / backup 13.0 ms (targets 5/8 missed; 12.162). Relay 11:16 pushed (item 6 = product switch). Owner asked: keep / lean / fallback.
- 11:3x: owner asked whether async FRAM helps; answered no (12.163). APT sent back two points (credit, Playwright limit); FRAM (a)/(b)/(c) open.
- 11:25: owner chose FRAM (a). Unit FS (settle removal + F.3 silicon rows) after T merges; rides the last-round image; bench told in the next relay.
- 11:5x: T merged (int a5c1dc93, lint clean); FS launched (FRAM settle + F.3 rows + T's doc list); APT in its full run. Then: APT + FS merge, combined gate, coverage check, snapshot 59.
- 12:0x: bench items 2-6 recorded (12.165); relay 12:03 pushed (bench 720df65d); FS got item 7 (doc facts). Waiting: APT, FS, bench item 3 re-run.
- 12:1x: APT round 2 (Playwright option D, the split/retry judged, the 15-min figure); FS running; then merge both, gate, coverage, snapshot 59.
- 12:2x: bench item 3 under load recorded (12.167); heap side-finding (largest block 22.7 KB after load, stays after collect) -> relay 12:23 (bench 795a0b19) asks the plateau/creep measurement.
- 12:2x: APT merged (int 146eb2e0, lint clean). Waiting: FS; bench heap measurement. Then: merge FS, combined gate (tc-c), coverage check, snapshot 59 (parent 910a0a62; SNAP_EXCLUDE + ftmp_apt ftmp_t ftmp_fs).
- 12:4x: bench heap (12.169): no leak; largest block 23->20->18 KB after 6-reader loads, 55 KB after 2 readers; min 11.4 KB during load vs UART cap 12.2 KB (dev's real transfers tiny). To the free-heap wrap-up + last-round image.
- 13:4x: FS merged (int 5621a24d); T's reap round limit fixed + FS doc findings (int 651af010; 12.170). Gate gate59 running (heavy.lock lead). Then: coverage check, snapshot 59 (parent 910a0a62; SNAP_EXCLUDE + ftmp_apt ftmp_t ftmp_fs), CI, last-round image relay.
- 13:43: owner asked whether 40 % is within expectation; answered: over the 05:27 forecast (~40 % at the finish), remaining ~7-10 points -> ~47-50 %, inside the plan's 50-60 % only if the close stays narrow.
- 14:5x: container restart 13:5x (CS resumed, gate restarted). gate59: all green but scenarios[dev] a_full_ceiling_of_concurrent_request_bodies (-1): six PUT /system writes timed out at 15 s (25.9 s; passes ~6 s in every gate since 11-09; 6/6 alone). Reproducing under the four-device parallel load with logs kept (repro_load2). CS back (12.171); scope put to the owner (A/B/C, recommended B). heavy.lock: lead.
- 14:57: owner chose (A): finish as planned (D.15 sweep by hand included). Next: briefs W1a (lists/baselines/twin items) + W2 (docs/release) in parallel; W1b (D.15) after W1a; O5 asked next.
- 15:1x: units W1a (tests/tooling) and W2 (docs/release) running; O5 (release number) asked. gate59 -1 red (12.172): rerun_e running under heavy.lock (lead) with dev twin logs kept.
- 15:5x: rerun_e green (12.172 closed unreproduced). gate59 green otherwise. cov59 running (lock lead); then snapshot 59.
- 16:0x: snapshot 59 a771238b pushed (12.173), CI pending; next PARENT once green. W1a, W2 running; O5 open.
- 16:2x: W2 merged (int 3bee346e); unit PIN (dev-tool pin moves, A.SDEP.25) started beside W1a; P05 waits for O5. Then W1b (D.15) after W1a + PIN merge; shared venv re-synced to the new pins after PIN.
- 16:0x: snapshot 59 a771238b CI green (run 42845410992, 28/28) = next PARENT. W1a, PIN running; P05 waits for O5.
- 16:4x: PIN merged (int 64b719c2, 12.175); disk 5.8 GB. Waiting: W1a; O5. After W1a: venv sync + Node 26 in run.sh, merge, W1b (D.15) brief.
- 16:4x: O5 = 2.0 (owner 16:40:55); P05 done, int 5b8c3446 (12.176). Next owner question: O3. Waiting: W1a.
- 16:5x: O3 closed by owner 16:47:07 (12.177, int 77a4e1e8). No owner question left. Waiting: W1a.
- 17:5x: W1a merged (20629434) + follow-ups 886f8af0 (12.178); tools on new pins + Node 26; gate60 running (lock lead); W1b out. Next: (c) root-cause read; after gate60: snapshot 60.
- 18:4x: gate60 green (12.179); cov60 running (lock lead); (c) measurement prepared in wt-uload (uload.sh). W1b running. Then snapshot 60.
- 18:5x: SGP40 serial read DONE by evidence (bench 10-28; comment fix owed in src/asy_sgp40_driver.py after cov60). RP (read-only probe re-read, BRIEF_RP.md) out. Writing: W1b. SNAP_EXCLUDE += ftmp_uload ftmp_rp.
- 19:0x: package list fixed (owner asked 19:03:24 why the count stays): 1 W1b; 2 small fixes + snapshot 60 (cov60, (c), SGP40 comment, SPEC/BACKLOG staleness); 3 probe re-check (RP done 19:0x); 4 re-verification + image; 5 last bench round; 6 W3; 7 final verification + D. New finds fold into a row; a row is ticked only when done.
- 19:1x: cov60 green; snapshot 60 37216f41 pushed (CI pending). Lock free for W1b; then uload measurement (lead).
- 19:3x: W1b merged (int f0d59a75, 12.182) after docs batch cf5724ae. uload before-runs (lock lead). Then: fix (c), tc-c re-record, P01 re-verification.
- 19:3x: snapshot 60 CI green (run 42881699131); next PARENT 37216f41.
- 19:5x: (c) fixed (bfa240fa, 12.183); tc-c re-recorded; gate61 running (lock lead). Next: snapshot 61 (PARENT 37216f41) = P01 with CI; meanwhile draft the last-round relay (read-only).
- 19:5x: LR (read-only last-round relay draft, BRIEF_LR.md) out. SNAP_EXCLUDE += ftmp_lr.
- 20:2x: last-round relay prepared (12.184); owner asked (go, wear in or out). gate61 at the twin stage.
- 20:3x: gate61 cut by the 30 min limit after e/f green; gate61b (twin + npm) running. Waiting: owner's (a)/(b) for the last round.
- 20:4x: bench day 5 end (fc4e5708). Relay builds on fc4e5708. Waiting: owner's confirmation of (a) with wear last; gate61b.
