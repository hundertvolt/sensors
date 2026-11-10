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
