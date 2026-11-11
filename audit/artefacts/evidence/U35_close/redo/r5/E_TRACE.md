et hand-back, written by the agent (Wed Nov 11 11:30:04 UTC 2026)
Read-only: git, grep and reading only (int wt 015dda9f; bench branch 49b3980b; the pinned v1.29.0 at S/tc-c/micropython); nothing run or edited. src/ is the same for the image (c75d3ebd) and int. The 11-11 per-node logs are not committed (archive 20261111T092718Z on the Pi), so E5 is mapped by code where the HANDBACK names no node.
## E2 test_no_send_stall_with_the_override: the page waits for lwIP arena memory, which the zero-window clients hold
- Resource: the MEM_SIZE arena (versions.toml:59, 12,000 B). Every tcp_write() copies into it (modlwip.c:802 COPY). One non-reader queues up to TCP_SND_BUF (:65, 6,400 B,
  ~7.2 KB of arena with pbuf overhead), so two fill it, as SPEC B.14.2.1 already says (SPECIFICATION.md:2479-2482). Not the limit: MEMP_NUM_TCP_SEG 48 (:66), above the arena's ~13 segments; PBUF_POOL, inbound only.
- The EAGAIN path: the page connection's tcp_write gets ERR_MEM, and the override returns EAGAIN. stream.py drain (:77-87) re-queues for POLLOUT, set while tcp_sndbuf()>0
  (modlwip.c:1639), so the writer spins on a ready poll: cooperative, one memoryview slice per round (stream.py:85). The spin met its bound on the final image
  (/status max 1.28 s, other routes <0.82 s, stopped 0 s): the override's own aim, no VM freeze, held.
- Nothing on the device frees the arena near 10 s. The dead clients' write times out at 5 s (asy_webserver_service.py:156, :391) and the server closes them. tcp_close() sends
  no RST, the window being restored (tcp.c:352-353; modlwip.c:909); it adds FIN to the unsent queue (tcp_out.c:1009-1019), so each pcb keeps its queue in FIN_WAIT_1 until
  modlwip's close poll aborts it 10 s after the close (modlwip.c:64, :1689, :1586-1590; tcp.c:1423-1425): ~15 s after the stall began. The page's own write is reclaimed at
  5 s too, but its FIN needs an arena pbuf (tcp_out.c:1023), so its close goes TF_CLOSEPEND (tcp.c:448-452) and the client hears nothing. The 10.01 s is the test client's
  own timeout (test:143, 2 x 5 s); the host closing its non-readers (RST on unread data) is what frees the arena.
- Earlier runs: passed 11-06 08:49 (page 2.10 s, 5 at zero window, /status max 2.95 s). Control 11-11: page 1.61 s, /status 10.01 s. Final: page None. Nothing in this path
  changed: the EAGAIN block and [lwip] are byte-identical from b7533307 to c75d3ebd; the images differ only by gc.threshold, i.e. timing. The page starts 4 s into the stall
  (test:136-143) and finishes ~1 s after the dead clients' 5 s reclaim, but only if its pcb holds some arena then: after the reclaim the dead writers stop competing and its
  own ACKed segments come back to it; without that foothold it waits for the ~15 s abort. So 1.6-2.1 s and >10 s are one race's two outcomes. The control's /status edge is not named in the HANDBACK, so not traced.
- Class: a stated limit (B.14.2.1) met by a test bound with no source. The 3 s bound (test:32) asks the stack to serve a new connection while it is full, which the design does
  not provide; the earlier passes were the race won. The test's remedy, a short POLLOUT back-off (owner 2026-09-30, SPEC:2737), cannot help: it lowers the spin's CPU cost,
  which met its bound, and creates no arena space.
- No change to the override's send path can bring the page under 3 s. The one product change that can is the [lwip] share: TCP_SND_BUF 6,400 -> 1,600 (2 x MSS, lwIP's
  floor). Each pcb then holds ~2.1 KB of arena at most, so 5 dead clients leave ~1.5 KB for a live one, and the dead ones stop spinning (their sndbuf hits 0 first). 1 line in
  versions.toml plus its comment, 0 RAM (MEM_SIZE unchanged), check_lwip_ensemble passes by my hand-check (QUEUELEN 8, SNDLOWAT 1599); rebuild, one flash cycle. Cost: a
  42 KB page needs ~27 RTTs instead of ~7 (about +0.1-0.8 s on Wi-Fi). It conflicts with "[lwip] keeps its values" (owner, 2026-09-30; SPEC:2606): the owner's decision.
  Alternative: a 4th modlwip patch aborting a zero-window pcb on close frees the arena at the 5 s reclaim; the worst case is then 5 s plus transfer, still not 3 s.
  B.14.2.1's "Not yet reproduced on silicon" (SPEC:2490) is now stale. Confidence: high on the resource, the release path and the 10 s client timeout; medium on the race as why 11-06 and the control passed.
## E4 test_a_multi_chunk_set_echoes_intact_under_serving_load: the test runs a second initiator on one UARTComm
- The device script drives link._comm with SET then GET back to back (sleep_ms(0) between rounds; uart_link_echo_under_serving_load.py:54-67), while the exerciser's own
  loop, still running inside device.main(), does uart_get(BANNER) on the same instance every 1 s (asy_uart_link_driver.py:144-150). A second initiation is refused, not
  awaited (asy_uart_comm.py:222, _gate :515-517, E85); the hazard run pins this contract as TwoInitiations [True, False].
- What fails from round 46: not the REST calls, the ring or the peer. The teardown carries only UART_init E85 (no TIMEOUT/NO_ACK/FRAME codes), so every failure is a refusal.
  The exerciser's ticks land inside script transactions (Failures 0 -> 28); one tick won (Transfers 17 -> 18), and during that one banner GET the script's uart_set was
  refused 12 rounds in a row ("stored False, answer None"; a refusal returns at once and the round loops).
- Earlier runs never passed: 11-05 (5g) and 11-06 failed in call with all echoes intact, Failures 0 -> 22/23, Transfers 15 -> 15, teardown E85 + W51. Since then the exerciser won one tick: timing, same rule.
- What the docs promise: J.2, one initiator per link, with a re-entry on one instance refused (J.9 sentinel); F.5.8/F.5.9, the UART never blocks the loop. Both held: no
  timeout was logged and the readers were not reported failing. The test also promises "the exerciser failing none", which J.2 rules out while the script shares its initiator.
- Class: test. Smallest fix, no image change: each round waits for the exerciser's tick (link._transfers + link._failures changes), then runs one SET+GET inside its 1 s sleep.
  An order, not a delay; ~3 lines in the script; the assertions stay as written. Product alternative, the owner's: a different task's initiation waits FIFO on the bus lock
  instead of being refused (cf. "never dropped", 2026-11-09). It changes TwoInitiations to [True, True], J.2/J.9 and the twin; not the smallest change. W51 on this test is in E5. Confidence: high.
## E5 the failed nodes and the teardown codes
- 4b, 9 failed: test_chip_conformance scd30/bmp3xx/fram -> A; held SDA [machine_reset] and [watchdog], the bootloader command and supervisor_raise -> B (4);
  c_stack_budget set_values_sync -> C; test_real_gc_heap_headroom (103,360 B > 100,000 B) -> D, the heap budget (not one of the brief's classes; the lead settles it).
- 5, 6 failed: rest_endpoints measurements and bus_concurrency ntp_transient_outage -> C (_CCT_MIN KeyError); reset_reasons escalate (EIO at an mpremote exec during
  re-enumeration) -> B; send stall -> E2; UART echo -> E4; bus_concurrency never_corrupts (SGP40 counter 2) -> E5, below.
- never_corrupts: the test's own action. Its _sgp40_resets sends two ResetVOC PUTs (test:501-511), which delete the backup. As the first node after the session's boot, it
  falls inside the boot's restore window with the clock unsynced: the restore finds no backup (W65, asy_sgp40_driver.py:512) and an undated backup is written (W35, :496).
  d lists no codes for it; c showed W65/W35 in this window. It passed 11-05 and 11-06 (clock synced). Its own _assert_bus_logs_empty (test:85, :423-430) wants 0.
  Fix (test, ~3 lines, no image change): wait for NTP sync before the resets, or reuse fram_erase's owed-W65/W35 form (test:386-400). Confidence: medium.
- The 13 teardown/setup errors are named by code in the HANDBACK, not by node; no code is in the carrying test's provokes_log. By code:
  NTP E71 x6: each test's reboot; test_boot_order_and_triggers.py:53-54 declares the same pair for its boot. Why a boot's attempt gets no reply is unexplained: it also shows
  on plain boots (errcount after step 3: E71 x2; after 5h: x1).
  SGP40 W35/W33: an unsynced boot writes undated backups and the next boot restores one (the lead's 11-06 14:21 reading). W65: a boot after an erase or a ResetVOC. W34: a
  backup older than BackupMaxAge or future-dated, left by the flash tier's scripts in production's chunk (4b errcount: W65, W34). All consequences of the tests. UART_init E85: E4's own. WEBSERVER W51 x2 (one is E4's): unexplained; the errno was never captured (11-07: "W51 not traced"). It is some OSError outside Microdot's muted
  32/54/104/128 (ext/microdot.py:56-61); the console line "socket error): [Errno N]" settles it.
  ISL29125 W31: unexplained at node level; a known load code (test_bus_concurrency_under_api_load.py:61), also seen 11-06 (serving_heap teardown).
  ISL29125 E13 [exception] and E55 + E1 [base]: unexplained; new on the final image (the control passed this node); one sample each. reset_code_loop_end.py:29-41 raises at
  the first loop wait after BOOT_DONE, then machine.reset(). No I2C byte is in flight then: a register read is a no-stop write plus a read with no await between
  (asy_i2c_driver.py:120-132), though mpremote's Ctrl-C that starts the script can land between those two calls. Settles it: the console's E13 text (one of 12 sites) and which boot logged it.
nothing of mine is running
## E2 reopened by the 13:00 run (appended by the agent, Wed Nov 11 13:05 UTC 2026; bench 427a14cb, int ca780dbd; src unchanged since the run's head 9e821210)
1. Mechanisms
- The four 10.02 s edges are not a property of those routes. The dev GET order is /measurements, /sensors, /networking, /system, /status, /notification, /uart
  (build/generated_src/api/dev.json, which is what harness get_routes() reads), so the three fast edges are the first three and the four failures are the last four.
  Drain (30 s, test:40/157) and page-after (:162) then fail too: one onset in the 4th edge, persisting more than ~90 s until the restore's reset.
  10.02 s is the poller's own timeout (2 x 5 s), and 10.52 s is one unanswered poll plus the 0.5 s cadence: inside each failed edge, nothing answered.
- What the host's close (RST, unread data) does, neither case wedged:
  - A pcb the device has already closed (FIN_WAIT_1, or TF_CLOSEPEND left ESTABLISHED) is purged and freed at once by an in-window RST (tcp_in.c:802-828, :442-448;
    its err callback was cleared at close, modlwip.c:1686). Its arena and its pcb come back immediately.
  - A writer still spinning on EAGAIN: _lwip_tcp_error sets ERR_RST and clears the pcb (modlwip.c:498-508). POLL reports it writable (:1650-1653), the write raises
    ECONNRESET (:736-740), Microdot mutes 104 (ext/microdot.py:56-61), and the handler ends.
- Nothing in src/ or modlwip can hold a slot or a pcb ~15 s past the clients' close: every connection is bounded by the 15 s outer cap (asy_webserver_service.py:865)
  and its finally closes synchronously (stream.py:19-21; _close_writer :693-703); a closed pcb is aborted <=10 s after close (modlwip.c:1689) or at the RST; the accept
  loop skips a failed accept (stream.py:160-163). So 30 s with no drain cannot come from the socket layer's own code. Either the loop stopped serving, or packets stopped moving below it (radio, driver, netif).
- The loop stayed alive: there was no reboot, so the 8.4 s watchdog was fed. The UART logged only 9 + 6 entries in a test of ~2.5 min with a 1 s exerciser (~150 transfers),
  so there were a handful of >=1 s gaps (timeout 1000 ms, asy_uart_comm.py:108), not starvation.
- Leading hypothesis, not proven: the radio's TX path jammed. While the CYW43 is flow-controlled, the driver waits up to 1 s per frame in C, with the lwIP lock held
  (cyw43_ll.c:651-692; CYW43_THREAD_ENTER is MICROPY_PY_LWIP_ENTER, extmod/cyw43_config_common.h:52). Every outgoing SYN-ACK, ACK or probe then costs up to 1 s:
  the board goes deaf, the link still reads as connected (no WIFI code, the CLAUDE.md false-positive class), there are occasional 1 s loop gaps, and a reset recovers it.
  Its timeout prints "[CYW43] STALL(...): timeout" (cyw43_ll.c:691; CYW43_PRINTF is mp_printf, extmod/cyw43_config_common.h:45).
- Settling reads. Without a new run: grep the node's observe_during console capture for "STALL", and set the UART E22 stamps against the edge times. In a next run: ping/arping the board during the deaf phase; if no STALL line appears, read the RX pbuf pool (PBUF_POOL_SIZE 16) next.
- Wedged or slow: by code, nothing in src/ or modlwip wedges. Whether the radio state recovers by itself is unknown, since the restore reset it.
  Confidence: high that the four routes are an onset, not a route property, and that the host's close frees the socket layer; medium-low on the radio cause.
2. The spin: no
- Per writer per round: IOQueue._enqueue (a 3-element list, a dict store, poller.register; core.py:73-86), one ipoll over every registered stream plus _dequeue (:113-129),
  a task switch, a memoryview slice (stream.py:85). Then in C: tcp_write walks the unsent list and a first-fit mem_malloc fails, then tcp_output runs.
  My estimate, not measured: ~0.15-0.3 ms and 50-80 B per round, so a GC (<=21 ms, asy_uart_comm.py:92) every ~400-650 rounds at 32768.
  At most 6 writers (the ceiling) puts a pass at roughly 2 ms or less. d measured exactly this with 5 at zero window: /status max 1.28 s, stopped 0 s.
- So the spin cannot produce the >=1 s gaps the UART timeouts need, nor 90 s of deafness. One coupling: the override calls tcp_output() every round
  (modlwip.c:806, before the EAGAIN return). If a TX wait like the one above is live, a round with sendable data can pay up to 1 s: the spin would amplify a stall, not cause one.
3. Fixes (each one is an image change: the per-call timeout is a build-time tunable too)
- Back-off on EAGAIN, three possible places. (i) The override in C cannot sleep cooperatively. It could only hide POLLOUT after ERR_MEM until a tcp_sent callback (a 4th patch, ~12 C lines plus anchors).
    But a fresh page pcb with nothing in flight is never woken by its own pcb, so it waits its 5 s per call: worse. (ii) A patched extmod/asyncio/stream.py drain (`if ret is None: await sleep_ms(N)`): 2 lines, but it touches every Stream writer, and it is another override. (iii) In src: the proxy's awrite writes the socket itself and sleeps N ms after None (~6 lines, asy_webserver_service.py:377-394, 0 RAM).
  Any of them restores only the spin's CPU cost, which was already within its bound; none of today's failed bounds. Cost: N ms more per stalled round.
- Abort (RST) on reclaim: not reachable from Python (no SO_LINGER; modlwip's setsockopt takes only REUSEADDR, BROADCAST and multicast membership, modlwip.c:1477-1546).
  A 4th modlwip patch could tcp_abort() at close a pcb with unsent data and snd_wnd 0 (~4 C lines plus anchor and proof).
  It frees the arena at the 5 s reclaim instead of ~15 s (page ~5 s plus transfer); the peer gets an RST after the reclaim, so no delivered data is lost. It does not touch the deafness.
- TCP_SND_BUF 1,600: 1 line, 0 RAM. Dead clients can then neither fill the arena nor spin. It restores status <=3 s, silence <5 s and page well under 20 s beside dead clients,
  structurally. Cost: ~+0.1-0.8 s per page load. It needs the owner, because of the 2026-09-30 "[lwip] keeps its values" ruling.
- Per-call timeout (5 s): lowering it only moves the reclaim earlier; the arena still waits for the 10 s close abort. Alone it restores nothing.
- Smallest set. For the arena half (d's and the control's failures), TCP_SND_BUF 1,600 alone covers all five bounds; the abort patch alone covers only the page.
  For 13:00's deaf board, none of the four is shown to restore silence, drain or page-after, because its mechanism is not established.
  So no honest stated limit can be written for it yet. Option A's premise ("/status keeps answering, the board recovers on its own") failed on silicon at 13:00, so the ruling
    goes back to the owner with the settling read above. My earlier "stated limit" covered the page bound only.
nothing of mine is running
