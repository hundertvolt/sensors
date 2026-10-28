# Lane R working notes (agent's own, not a deliverable)
R1 = 25b71a4. Landed in R1 beyond the bare API (ARG002 forbids unused params in src/): step 25 in full (capped
piece readline, 93 logged via caller's log), OF-39 (write deadline in _write_all), OF-38 cause (rx_ring_refusal set
in setup_rx_ring), _count_discarded() helper (used by readline only so far), rx_ring public (A-4).
Seen failing first (R1): u17/r_seen_failing_R1.txt (shape failures), plus mutations: deadline off -> the deadline
test fails (hangs to run bound); cap off -> over-cap test fails; trim off -> 3 readline tests fail.
Overlay for runs before merge: u17r_ov (stub PieceBuffer + catalog with E93) - drop once the base is merged.
Red until G1 on my tree: test_error_catalog::test_every_code_constant_equals_its_catalog_entry_and_owner and
::test_no_code_constant_holds_a_non_catalog_value (src/asy_uart_driver.py:48 _ERR_UART_TRANSFER_CAP = 93).
Phase 2 TODO: step 7 codec bound (+59 tests), 17 done (_SEQ_HALF), 18 cancel comment, 19 _count_discarded at every
_read_delimited None, 20 cancel wraps, 21/22 counted branches, 55 cap cancel tests, 56 discard cases + exact-size
codec, 74(d) done, OF-33 idle-rate test on the shared clock, member order last, silent-failure scan.
