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
