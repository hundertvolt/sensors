# R5 next steps (lead, 2026-11-07 17:58 UTC; resumed 2026-11-09 17:16 after the weekly limit)
- int `audit/u35-int` b412d1b3 (specfund merged). Snapshot 48 carries it and every record to FINDINGS 12.107.
- bfix resumed 11-09 (due 21:30) in S/wt-bfix (branch audit/bfix from 18e9d59c; brief r5/BRIEF_BFIX.md): if the container is lost,
  rerun it from the brief. CRC yield change waits for the chip read (owner declined it for now).
- stretch running (read-only, r5/BRIEF_STRETCH.md): the 104-122 ms /status stretch and the 41 ms VOC step.
- bchain running (r5/BRIEF_BCHAIN.md, due 23:00): GC-threshold host-tier rerun skipped; matrix dedup by hardware_family (owner 10-23).
- After bfix merges: the owner's five (12.107) + STRETCH's two (12.108) + complete1 (7) BMP3XX poll, split by file into a
  webserver/logging unit and a driver-side unit; the five lock sites (12.111 (4)) decided on bfix's numbers; then the P9
  doc unit (LEVELS_2 rows, COMPLETE_2's twin time and WLAN rows, COMPLETE_1 (2)(3)(5)).
- Bench list: CRC per-byte figure; SCD30 routine stretch; stall.wlan_switch; req/s re-measure after fixes; post-B UART cadence.
- Owed to the owner: the hotspot password's doc copies (SPEC 3 lines, audit plan 1, ~20 audit files): remove?
- Completeness passes running (r5/BRIEF_COMPLETE.md, resumed, due 11-09 20:30; next snapshot adds ftmp_complete1 ftmp_complete2 to SNAP_EXCLUDE); prevention in common_r1.md (12.109). Owed: the free-heap wrap-up (web.chunk_bytes margin 1.0-2.2x).
- Bench off until the owner restarts it; the fix image and the CRC chip read wait for it.
