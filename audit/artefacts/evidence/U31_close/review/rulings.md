# U31 review rulings, RA and RB (lead; decided on the owner's behalf, conservative and reversible)
Confirmed by the lead: RB-1 (build-standard: `await asyncio.sleep_ms(2.0)` raises "TypeError: can't convert float to int").
- RA-1 blocking, fix (FX1): pre-write the reset record at the escalation decision (allocation-free `write_reset_record`), build the entry coroutine inside the bounded wait's `try`, log the MemoryError arm through `console()`; a test that fails the coroutine's own allocation. Check that a system command passing the gate after the decision still writes its own record last.
- RA-2 fix (FX1): the supervisor-fault handler sets `_reset_decided` first: a reset follows, so ResetErrors is refused as for every reboot decision (owner, 2026-10-13: "1 b, 2 b").
- RA-3 fix (FX1): the timed-out escalation's console line carries `message`.
- RA-4 fix: code wording (FX1) "Reboot entry not written:"; Part N row "in RAM at most" (lead).
- RA-5 fix (FX1): `quiet=True` with WiFi's one-line reason (same behaviour; D.10 one form).
- RA-6 accepted, no change (agent, 2026-10-21): `_frame_ms` stays a per-instance attribute: it is the tests' documented seam (Part N `led.refresh_hz`: "tests set the attribute after construction"); a module const would remove it.
- RA-7 doc only (agent, 2026-10-21): `ServingLimits` keeps seconds and converts once at construction (the lane plan's ruling, settled by its action text); D.4 names that exception (D1). isl29125's int() is a dwell comparison, not a wait (pre-existing, out of scope).
- RA-8 fix: `×` → `*` in the two WiFi comments (FX1); Part N "(0.5 s)" → "(500 ms)" (lead).
- RA-9 fix (FX1) (agent, 2026-10-21): the supervisor's own fault gets a SYSTEM code of its own: code 42's catalog text names "a supervised task", and the supervisor is not one; a distinct code keeps the evidence of which entry preceded a watchdog reset. The bench helper that asserts no new TASK_RAISED covers the new code too. SPEC lines naming it (C.9 Supervisor row, F.1): D1 or the lead.
- RB-1 blocking, fix (FX2): every one-yield sleep_ms stand-in runs the real path's own check first (`time.ticks_add(time.ticks_ms(), max(0, ms))`), so a float raises TypeError as on rp2; a shared-helpers test pins it. Any src site that then fails is a real defect, fixed at its source.
- RB-2 fix (FX2): the boot scenario's recorder also sees waits under `wait_for_ms()` (asyncio.core.sleep_ms and runner tasks the batch spawns), and asserts the drained links are exactly the device's uart_link instances (none on five devices).
- RB-3 fix (FX2): cite A.7.
- RB-4 fix (FX1): feeds == 1 and the sibling's later re-read.
- RB-5 fix (FX2): run_timed(drive(), _RUN_BOUND_S).
- RB-6 fix (FX2): pin the settle's order against the stations query on the WLAN fake.
- RB-7 accepted, no change (agent, 2026-10-21): the literals are pinned by the tunables register (Part N Sites `2900`/`100` against each tag's literal, test_tunables_register rule 4), so a mis-scaled value fails there.

# RC and RD rulings (lead, 2026-10-21; decided on the owner's behalf, conservative and reversible)
Each checked against its source by the lead: RC-1 (code order), RC-2 (conftest.py:67), RC-3 (README budget table), RC-4 (codegen.py:25, base_classes:585), RC-6 (cyw43-driver v1.1.1 cyw43_ctrl.c:353-355, :666-669), RC-9, RD-1 (old text at aba11d5 kept the webserver in its own clause; webserver.py:331-346), RD-2 (expected_rows() has ten rows), RD-3 (config_manager.py:399-401, 584-586: one non-yielding `with open()` per flush; J.6 and N `uart.flash_hold_max_ms` 2129 ms), RD-4 (bite list), RD-5, RD-13 (test body: no API load), RD-16 (C.3 holds the bus recovery and the boot clear).
- RC-1 blocking, fix (FX4): mark at the load's stop, wait for the next LOOP_LAG line (the window straddling the stop) and bound it as a load window. The settle check reads the line after it: its window began at the straddler's close, after the stop, so the sleep `_LOOP_LAG_SETTLE_S` goes, with its tag (agent, 2026-10-21: structural, stricter, about 10 s less per run). A stub-twin case whose straddling window is over the bound must fail.
- RC-2 blocking, fix (FX6): `config_HWTEST_stretch.bin`, README updated.
- RC-3 blocking, fix (FX6): the budget row lists `test_flash_write_loop_gap_is_recorded`: 1 scratch write.
- RC-4 fix (FX4): read `_MAX_MODULE_ERROR` from buildgen/codegen.py (the value the generated module passes); Part N `module.max_error` Dependants (lead).
- RC-5 fix (FX4): derive the settled bound from `con.led_frame` (1000 // `_NEOPIXEL_FREQ_HZ`, 50 ms): a settled loop drops no LED frame; the `@tunable` literal goes; Part N row (lead).
- RC-6 fix (FX4): cite cyw43_ctrl.c:353-355 and :666-669, and call the instant IDLE a simplification (no product path reads status between `active(False)` and `deinit()`).
- RC-7, RC-8, RC-11 fix (FX4).
- RC-9 fix (FX6): "Four".
- RC-10 fix (FX5): the `stall.flash_program` Guard cell says record only.
- RD-1 blocking, fix (FX5): the webserver's waits in their own clause again; they raise TimeoutError, which `_serve()` turns into a reclaimed connection and its warning; three waits map no sentinel.
- RD-2 blocking, fix (FX5): extend `expected_rows()` to every row whose value a src constant gives (con.dns_query, con.http_call, stall.uart_call, stall.sync_wait, hold.wifi_lock, stall.flash_program), one bite each; the feed sentence says "a `feed` row whose value opens with a figure".
- RD-3 blocking, fix (FX5): `stall.flash_program` is the whole flush, 2129 ms (`uart.flash_hold_max_ms`), one erase 400 ms with interrupts off inside it; the consumers it crosses are marked with their outcome from source (con.uart_reply: read the reply wait in asy_uart_comm.py to see whether a reply that landed in the ring during the hold is read before the deadline check). The accepted degradation is tagged (agent, 2026-10-21). New open finding to U35 (the next holder of src/asy_config_manager.py): a flush written in chunks with a yield between them would bound the loop stretch near one erase (decided not now: it changes J.6's ring derivation).
- RD-4 fix (FX5): one bite per class.
- RD-5 fix (FX5): bites for the stale waiver and the asyncio-blind guard; the rule reads "no float literal or float constant and no true division" (test docstring and D.4); D.4 names the stand-ins' runtime refusal (FX2) if it reads true.
- RD-6, RD-8, RD-17 (SPEC part), RD-18 fix (FX5). RD-17's runner --help part (FX4).
- RD-7 fix (FX5): quote the owner, else "paraphrase" and a pointer; the technical consequence is not tagged with the owner's date.
- RD-9 fix (FX5): the margins are in the Part N rows each row cites.
- RD-10 fix (FX5): the function name `_scenario_boot_feeds_the_watchdog` at :821, as F.3 names every scenario.
- RD-11, RD-12, RD-14, RD-15: Part N (lead). RD-12's twin figures: FX4 re-measures after RC-1, dated; the lead writes them into F.3 `lag.loop` and Part N.
- RD-13 fix (FX5): BACKLOG states the instrument as the test runs it, no concurrent API load. New open finding to U33 (the next holder of the bench memory-stress tier): the bench instrument runs without the HTTP load the twin scenario applies.
- RD-16 fix (FX5): C.3.
- FX2's owed items (FX6): `full_heap_wait` runs `check_sleep_ms(timeout)` first; `_StaggerClock` and `_LateTicks` refuse a float delta as rp2's ticks_add does (a consistency defect, fixed).

# RE rulings (lead, 2026-10-21; RE read a311feb..7d89c52, the fixes after the earlier ranges; nothing blocking)
Checked by the lead: RE-5 (machine_timer.c:141-148: init() cancels the alarm, then parses), RE-2 (figures_after.txt and figures_after2.txt recomputed: load 21.3-74.0, straddler 4.2-36.5, boot 237.0-245.5, settled 3.6-31.4 quiet / two 60.8 and 71.5 loaded), RE-7 (five waits listed).
- RE-1 fix (lead): the comment cites Part N `l1.lwip_host_spin_window_rounds`, which holds the owner's question and answer; the squash message quotes them.
- RE-2 fix (lead): both batches, each range rounded outward to whole ms, named in the cell.
- RE-3 fix (lead): the SPEC cell tagged (agent, 2026-10-21); the comment says "99 % of wakes within one LED frame".
- RE-4 fix (lead, agent, 2026-10-21): every wake after the load within one DNS query (`con.dns_query`, codegen's `_DNS_TIMEOUT_MS`, 500 ms), the smallest consumer that is not cosmetic, under every hard bound; a stall of up to 6 s at rest no longer passes on the five devices without a UART link; the host stalls seen (61-72 ms) stay far below it. The stub case moves to that cap.
- RE-5 fix (lead): both fakes cancel the running schedule before they refuse (the unit fake clears its callback at init()'s entry, the twin deinits first); the contract check adds an armed PERIODIC timer refused at re-init, its callback gone; seen failing on both fakes first.
- RE-6, RE-7 ("Five waits"), RE-8 ("its float refusal", the range named) fix (lead).
