# R5 next steps (lead, 2026-11-07 17:58 UTC; resumed 2026-11-09 17:16 after the weekly limit)
- int `audit/u35-int` b412d1b3 (specfund merged). Snapshot 50 e0e2266a (next PARENT) carries every record to FINDINGS 12.111.
- bfix resumed 11-09 (due 21:30) in S/wt-bfix (branch audit/bfix from 18e9d59c; brief r5/BRIEF_BFIX.md): if the container is lost,
  rerun it from the brief. Its item 3 (CRC yield) dropped 11-09: the engine is unit (C) below.
- bchain running (r5/BRIEF_BCHAIN.md, due 23:00): GC-threshold host-tier rerun skipped; matrix dedup by hardware_family (owner 10-23).
- After bfix merges, units by file (two writing at most): (A) webserver/logging: owner's (1)(2), STRETCH errcount
  fragment, the lock sites (12.111 (4)); (C) CRC engine and byte loops: one viper CRC for 8/16/32 (yields go), _rx_copy,
  FRAM compare, _bytes_to_int, UART write gate and poll floor, COBS/_rx_line_len removal check (12.115); (B) drivers:
  SCD30 bus release, BMP3XX computed wait, boot stagger, lean removals (12.107 (5)), neopixel signal wait, VOC, and a
  D.8 re-read of every 11-03 "back to pre-audit" rollback. Then the P9 doc unit (LEVELS_2 rows, twin time/WLAN rows,
  COMPLETE_1 (2)(3)(5), D.8 platform-first and poll-count rule, CLAUDE.md's version-bump practice over pure loops).
- Bench (up 11-09 until ~20:55): CRC forms and SCD30 frames done (12.113-12.114). Owed: stall.wlan_switch; req/s
  re-measure after fixes; post-B UART cadence; frozen viper on the next image. Done: complete1/2, cprim (12.110-12.115).
