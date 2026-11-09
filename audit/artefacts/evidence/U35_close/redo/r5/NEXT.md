# R5 next steps (lead, 2026-11-07 17:58 UTC; resumed 2026-11-09 17:16 after the weekly limit)
- int `audit/u35-int` a202591d (bfix merged). Snapshot 51 790b8cad (next PARENT, CI running) carries it and FINDINGS to 12.117.
- crceng (unit C) running in S/wt-crceng from a202591d (r5/BRIEF_CRCENG.md, due 01:00): native CRC engine first - it
  also closes the SGP40 chunk's ~272-round _op_lock hold that quiesce() waits on (12.117, near-critical).
- bchain running (r5/BRIEF_BCHAIN.md, due 23:00): GC-threshold host-tier rerun skipped; matrix dedup by hardware_family (owner 10-23).
- After bfix merges, units by file (two writing at most): (A, after bchain) webserver/logging: owner's (1)(2), STRETCH errcount
  fragment, the lock sites (12.111 (4)); (C) CRC engine and byte loops: one viper CRC for 8/16/32 (yields go), _rx_copy,
  FRAM compare, _bytes_to_int, UART write gate and poll floor, COBS/_rx_line_len removal check (12.115); (B) drivers:
  SCD30 bus release, BMP3XX computed wait, boot stagger, lean removals (12.107 (5)), neopixel signal wait, VOC, and a
  D.8 re-read of every 11-03 "back to pre-audit" rollback. Then the P9 doc unit (LEVELS_2 rows, twin time/WLAN rows,
  COMPLETE_1 (2)(3)(5), D.8 platform-first and poll-count rule, the ask-before-removing-a-feature rule (owner 11-09 18:30), the audit goal "minimal and optimal at the same time through smart design" (owner 11-09 19:11) in Part 0 or D.8, CLAUDE.md's version-bump practice over pure loops).
- Bench (up 11-09 until ~20:55): CRC forms and SCD30 frames done (12.113-12.114). Owed: stall.wlan_switch; req/s
  re-measure after fixes; post-B UART cadence; frozen viper on the next image. Done: complete1/2, cprim (12.110-12.115).
