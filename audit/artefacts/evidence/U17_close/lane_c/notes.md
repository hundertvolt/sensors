# lane C running notes (scratch, for the final report)
C1 = f22b399.
- whole-tree reds owed to others at C1: test_error_catalog (G1 rows 91-93), test_tunables_register (D rows
  uart.flash_hold_max_ms, uart.chunk_bytes, uart.max_transfer_bytes), test_lint_ceilings (max-returns 11 -> 10:
  _accept_set held the 11; measured max now 10: asy_fram_manager.py:191, asy_uart_driver.py:451,
  tests_scripts/test_driver_shape.py:43, test_ticks_wrap_scan.py:224) -> G's pyproject.
- mypy (scratch copy with typed PieceBuffer stub): my files clean; 43 errors in callers: harness(5), link driver(5),
  test_asy_uart_link_driver(4), readiness_gates(1), ticks_rollover(2), hazard(17), device scripts (6+4+2+6).
- _FLASH_HOLD_MAX_MS trace: S_max ~1.6 KB (NTP file: NTPHost 253 control chars x 6 = 1518 B json escapes,
  mp_str_print_json py/objstr.c:142-164) -> 7 data pages; lfs2 v2.11 (0x0002000b) cache 1024, inline_max 512
  (lfs2.c:4350), prog 256, block 4096 (_boot.py progsize=256); data: lfs2_file_relocate erase 1 + 7 programs;
  metadata commit worst: splittingcompact (lfs2.c:2126-2232) split -> 2 erases, <= 9 pages each (half block 2048 +
  40 B tail/gstate/crc); relocation of the tail pair (block_cycles 100, lfs2.c:1941-1948, vfs_lfsx.c:101) moves it,
  the predecessor (superblock pair {0,1}) commit compacts/expands: 2 erases, <= 9 pages each. E=1+2+2=5,
  P=7+18+18=43 -> 5x400+43x3 = 2129 ms (assumption: root metadata at most two pairs).
- body commit c9d6d82; harness switch 3rd commit; R merged c8da12a.
- seen failing (b2_before.txt): 15 incl GET chunks, entry order x3, W57, ring floor x2, discard x2, streak, hold-off aged, declined backoff, tx stall, ring cause.
- guards: aliased band, unaged hold-off, dead-link doubling, backoff at ceiling, contract tests (empty into/stream, exp_size miss, empty set, zero stream, max stream, borrowed buffer), caller-supplied dest, hammer, train at cap.
- COBS wrong length: seen failing cobs_seen_failing.txt, fixed by borrowing _discarded_seen.
