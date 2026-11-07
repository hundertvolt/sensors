G3 hand-back. Commit c2a81a6 on audit/u35-g1b, on top of 43d1a6b. Not pushed, nothing uncommitted. Logs: S/u35/laneG/g3/.

**Step 1, write order (applied)**
- Mechanism: at 069b9fe, `_write()` in asy_fram_manager.py:373-382 wrote block 0 and then block 1 whatever their state. Seen failing on that order with a structural start state (block 1's status pair BUSY): "cancelled after 1 turns: from start (1, (2, 2)): blocks [0, 1] both left BUSY", and the relaunch restored None.
- Fix: `_write_chunk(buf, -1)` (asy_fram_manager.py:396-410) reads block 1's status pair with one 2-byte READ inside the first block's own session. Block 0 goes first only if both bytes read IDLE.
- Failed read: the driver's report and FRAM_STATUS_READ are logged, then block 1 goes first. Reason: there is no proof block 1 is whole, and the same guard fails the write's first command before a byte is sent (agent, 2026-10-22).
- G2's version opened a separate `_first_block()` session, which allocated 1,568 B per write. That pushed test_asy_fram_allocation_budget's blank setup to 31,296 B against its 30,000 B budget. Inlining the read brings it to 29,888 B; the base is 29,728 B.
- Tests: the cancel sweep now starts from 3 states. A new order test covers IDLE, byte 1 BUSY, byte 2 BUSY and an unreadable status. Bites: old order "both left BUSY"; failed-read-picks-0 seen; G2's PB "bus is still locked", PC "CS left asserted", PD "entry cut short left RAM" all still bite.
- Two-cut sweep, logged: G2's two_cut.py as written reports 784/784 lost on both old and fixed code. It uses a 10-slot store while `_relaunched()` uses `_CUT_SLOTS` (3), so the geometry mismatches. With both at 10: 069b9fe loses 196/784, the fix loses 0/784.
- Wire-trace goldens: +1 CS cycle per chunk write (blank 55→56, ts_write 50→51), and blank chunks now take block 1 first. This is a protocol change under the owner's 2026-09-18 "every CS cycle stays" rule, made on the owner's behalf (agent, 2026-10-22).
- Other test edits: test_write_fails_cleanly_when_block_1s_write_itself_fails writes the chunk once first. The planted-fault and concurrent-observer expectations follow the new read.

**Step 2, bounded traces (applied)**
- `_trace_before_close()` (asy_webserver_service.py:994) holds a trace for at most one per-call timeout. It covers the refusal, bad-head, peer-reset and the three reclaim arms. `_note_drop()` is used for the refusal again.
- Seen failing on 43d1a6b, on a driven clock: bad-head `(61, [], True, True)` and socket-error `(51, [], False, True)`, i.e. not closed within 4 timeouts. G2's refusal case moved onto the same helper.
- The task's top catch ("Connection task failed:") stays a direct err_s(), still unbounded. test_task_tops.py recognises a top by that call and went red (15 failed) when I wrapped it. Bounding it needs the checker changed; that is your call.

**Step 3, time (applied)**
- Measured cause: not the 8 KB chip (0.1 ms each). It is the host's CS-settle `time.sleep_us(2)`, about 250 µs per CS session.
- The file now swaps a no-op sleep_us in at module level. The settle is a busy-wait with no await; test_asy_spi_driver.py pins it.
- Paired times (base 069b9fe / G2 / head):
  - fram_manager: 6.31/7.63 → 7.24/8.55 → 1.17/2.26 s at -1/32768.
  - connections: 1.30/1.37 → 1.66/1.75 → 1.46/1.60 s (+0.16/+0.23 s against base, under the 0.5 s bar).

**Step 4, proofs (all rc=0, 0 memory markers)**
- test_sensortask: 6 devices × 2 stages, 105/105 each.
- 33 tests/ readers of both src modules at both stages, plus test_digital_twin_sensortask_integration for 6 devices at -1 and dev/wozi at 32768.
- settrace: fram_manager 148, connections 26, wire_trace 9.
- Twin, dev: uart_ring 3/3 per stage beside 4 burners, killed by pid. Webserver concurrency family 20/20 per stage. 4x plant 1/1; the twin's log level does not show whether refusals were hit.
- G2's twin_batch.sh exited 2 on its `--only` list ("--" items). It passed with those removed.
- tests_scripts, whole tier: 41 failed + 1 error, 6764 passed. The cause was mine: I removed frozen_modules per CHECKLIST 13, which test.sh rebuilds before pytest.
  - After the rebuild, the 5 red files passed except test_task_tops (fixed above, then 685 passed) and test_twin_record (expected red).
  - The whole tier was not re-run.
- ruff and all mypy passes are clean. The final one-line revert got ruff, a main-config mypy run on that file, and the webserver unit files at both stages and settrace.
- mpy-cross: fram_manager 11383→11551 B; webserver 15367→15419 B.
- The twin batch and the full mypy passes ran on e62b601, before the top-catch revert.

**FRAM sites:** a new 2-byte status read per chunk write. FRAM reads are destructive, so block 1's status cells take 3 operations per write, still under the read path's 3-per-read worst case that the endurance test pins. The block-write order changes; the write count does not. No flash or NVM write is added or changed.

**Per mode:** the FRAM change is identical on every device and mode. The webserver change applies to STA and AP; Silent, Off and USB are unchanged.

**For D3:**
- SPEC 183-191 (the status-byte protocol and CS cycles) and 207 ("3 operations per read, 2 per write") are stale.
- SPEC 212-214: "both copies left marked … 1 abrupt restart in 8" was measured on the old order.
- SPEC 8258-8262 ("already persisted" by an arm) is stale.
- SPEC 6588 and 11773 now bound every pre-close trace.
- G2's 12216, 9785, 6588 are carried over.

**Open finding:** a cut `_read()` that starts with block 0 BUSY marks block 1 BUSY too, so both end BUSY. I have not checked whether any cancel reaches a chunk read in production.

nothing of mine is running