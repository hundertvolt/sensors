# D2e carry list (lead, 2026-10-22): everything the D2e docs block must land, with its source
1. Z's stale SPECIFICATION.md sentences (handbacks/Z1_final.md): A.4 :170-173; C.7.3 :3756-3768 (incl. :3766: a power
   cut in the first boot's defaults write leaves an empty file, littlefs creating it at open, lfs2.c:3125-3128; the next
   boot repairs it with defaults and records a ConfigFaults entry, as at f3fff0e); F.3 :6531 `stall.flash_program`;
   J.6 :9602-9612 (2129 ms is again the one-stretch bound); Part N :11721 and :11743 (the `config.flush_slice_bytes`
   row out, `uart.flash_hold_max_ms`'s basis restored). Line numbers at 447ae0b; re-locate on the D2e base.
2. The stall finding stated as an accepted degradation with its consequences (owner's single-write decision).
3. Part D: the least-wear checklist item; C.8: a pointer to it.
4. CLAUDE.md: name the guard (tests_scripts/test_firmware_write_sites.py: every flash and SCD30-NVM write site pinned,
   a change failing as the owner's decision) in the least-wear rule; the UART link exception sentence with the owner's
   words (LEAD NOTES 95), naming its guard tests_scripts/test_uart_link_bench_only.py (only the `bench = true` board
   declares uart_link). SPECIFICATION.md's Part D least-wear item (item 3) names both guards too.
5. O: A.8 (:1116-1122) gains that the provoked faults land in both UART FRAM logs and one run fills UART_resp's
   10-entry log, overwriting older history; tests_hardware/README.md's hazard-run item says to read both logs first.
6. Step 142 (D2d's leftover): BACKLOG.md's owed-hardware rows for U35's new instruments, each checked in
   tests_hardware/ first (handbacks/D2d_final.md lists them).
7. Whatever J's hand-back reports as stale.
