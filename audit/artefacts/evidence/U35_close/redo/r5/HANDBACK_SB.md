SB hand-back, written by the agent (Wed Nov 11 13:47 UTC 2026). Commit f9853e33 on audit/sb (from ca780dbd), 8 files, not pushed.
1. versions.toml TCP_SND_BUF 6400 -> 1600 (+ its @tunable tag; header comment: "TCP_SND_BUF as the bench measures it"). The value sits in versions.toml only: a later value is that line, its tag line and the Part N row, plus B.14.2.1's "shipped" sentence.
- Sanity check against the pinned init.c:303-322 and opt.h:1383-1409, MSS 800: SND_BUF 1600 >= 2*MSS 1600 (equal: lwIP's floor); QUEUELEN (6400+799)/800 = 8, between 2 and 0xFFFF, <= SEG 48, >= 2*(1600/800) = 4;
  SNDLOWAT min(max(800,1601),1599) = 1599 < 1600 and < 0xFFFF-3200; SNDQUEUELOWAT max(4,5) = 5 < 8. The per-connection checks: 6 x 2 = 12 <= SEG 48; PCB 9 >= 6+3; MEM_SIZE 12000/6 = 2000 >= the floor.
  SNDLOWAT/SNDQUEUELOWAT are used only in api_msg.c (netconn, compiled out: LWIP_NETCONN 0). Every value from 1600 to 6400 passes the same set.
- Anchors: unchanged (they are the upstream text, not our values). test_setup_toolchain_env's test_the_current_names... applied both lwIP overrides with 1600 against S/tc-c's checkout: green.
- Tests pinning 6400: none pins versions.toml's value. The 6400s in test_micropython_overrides.py are MicroPython's pinned block (_pinned()) and a synthetic set, so they stay; the 1600 row of the derivation test already existed. The value change has no test to see red.
- Host build: build-lwip takes [lwip] (setup_toolchain.build_unix_lwip_port -> apply_unix_lwip_host_override(load_lwip_macros())). build-standard/build-settrace and the twin do not.
  The record's versions.toml sha now differs, so scripts/_unix_port.sh ensure runs `setup` once for S/tc-c (all three Unix binaries, with the firmware verification), plus the dev image. The lead rebuilds; I built nothing.
- FINDING (b), predicted, not reproduced (no build-lwip at 1600 exists): tests/lwip_host/test_modlwip_eagain.py assumes 6400. At 1600: test_the_segment_pool_edge gets EAGAIN at 3 x QUEUELEN 8 = 24, asserts 48 (certain);
  _load (test_a_write_to_a_peer..., test_capacity_returns..., test_repeated_rounds...): one stalled loopback pair holds about 8.9 KB (6400 received + 1600 queued), so loader 1's MSS write succeeds and fails "was not EAGAIN" (high);
  test_a_reading_peer_receives_every_byte_intact: the first EAGAIN comes at sndbuf 0, POLLOUT clear, failing its "arena" edge assertion (medium-high). The queue-limit edge and spin round hold (8 x 16 B).
  I left it unchanged: test-first needs build-lwip at 1600 to see the red, and the loopback arena edge mixes tcp_write's EAGAIN with the loopback copy's ENOMEM, so a fix needs runs. B.14.4's "What the host build shows" (32 segments, 10,400 B) is 6400's and gets re-measured with it.
2. Docs (filtered views). B.14.2.1: the SEG bullet (QUEUELEN derived, 8 at 1600). The MEM_SIZE bullet loses "6,400 B / two clients fill it". A new paragraph gives the owner's 13:38:57 words and the arithmetic: 1.125 x SND_BUF per stalled client, 1.8 KB for a live one, floor(10200/(1.125 x v)): 1600: 5, 2400: 3, 3200: 2, 6400: 1 (lead's reading checked; 4000: 2, 4800: 1).
  It also covers the silicon 7.6-20.2 s at 6400, zero send buffer before the arena within the tolerance, and the override staying. "The shipped 1,600 B is measured on silicon, 2026-11-11", cost "estimated +0.1-0.8 s ... is measured: owed" <- THE LEAD FILLS "owed". The stated-limit sentence and the 20 s bound are gone.
  B.14.4: "[lwip] keeps its values (owner, 2026-09-30; F.9), `TCP_SND_BUF` apart (B.14.2.1)". F.9 states no 6,400 and no [lwip] value: unchanged. Part N row lwip.tcp_snd_buf 1600 (basis, margin, triggers).
  BACKLOG build-environment list: one entry. digital_twin/run_generic_integration.py comment and README row: rp2's send buffer named by its versions.toml source, no number.
3. test_modlwip_send_stall.py: identical to 9b1e651d~1 except the kept "A failed bound goes to the owner, never a quietly larger bound." _PAGE_MAX_S is gone; the page bound is _REQUEST_MAX_S and the client timeout _STOPPED_ANSWERING_S * 2.
  FINDING (c), predicted: at 1600, 5 stalled clients plus a page queue about 10.8 KB < 12 KB, so the hammer may never reach ERR_MEM. Then test_send_stall_on_the_unpatched_image (control image built with [lwip]) would pass all bounds and fail with _REMOVAL_SIGNAL, and _MIN_ZERO_WINDOW would no longer prove the patched branch. That is for the bench to read.
4. Reset race: harness.restore_board_to_serving() (the shared teardown restore; conftest's _board_state and session-end save_fram_raw paths pass through it too) now waits wait_until(board.is_device_present, _SERVING_RESTORE_TIMEOUT_S) after the HTTP wait.
  One line plus a 1-line comment; no new mechanism. Test: tests_scripts/test_bench_harness_helpers.py::test_restore_board_to_serving_..._and_usb (presence False then True), seen red (calls lacked the probes), then green.
Cost per changed operation: TCP_SND_BUF 0 B RAM (a counter; MEM_SIZE and SEG unchanged), page load +0.1-0.8 s estimated (to be measured). Restore: one serial open/close after serving (0.2 s probe), normally immediate, bound 90 s (the restore's own). No src/ change, so module sizes are unchanged; firmware not built.
Checks: rebuild.sh ok; lint_direct rc 0; mypy x3 clean; 19 tests_scripts files 2600 passed, 6 skipped (all test_build_firmware.py:719, the opt-in real ARM compile); --collect-only bench send_stall + reset_reasons: 20 collected. No gate run (the lead's).
Decision (agent, 2026-11-11): the host lwIP test is not adapted blind (item 1 finding); the bench test's other precondition messages are kept as they were.
## Resume, written by the agent (Wed Nov 11 14:22 UTC 2026): lwIP host test at 1,600. Commit a55ac841 (on f9853e33).
1. Red on wt-sb: 5/9 (sb_lw_red), the same as the lead's lwip1600a. Each failure was a 6,400 assumption, fixed where it sat. No new helper, harness or layer: +47/-36 lines ignoring the intact loop's re-indent.
- _load (T1, capacity, repeated rounds): one pair's stall is TCP_WND + TCP_SND_BUF = 8,000 B of payload, under the 12,000 B arena, so loader 1's write succeeded.
  _ARENA_LOADERS = ceil(MEM_SIZE / (TCP_WND + TCP_SND_BUF)) = 2 at 1,600, and 1 at 6,400 (the old design). Probe: loader 0 wrote 8,000 B and stopped with POLLOUT clear; loader 1 wrote 800 B, then ENOMEM; loaders 2-3 got the patched EAGAIN.
  A loader's ENOMEM is counted as its piece queued: tcp_write() took it, the loopback copy failed (path a). Path b needs unsent data in an open window, and MSS writes never leave any (F.7 row 23 says the same).
  _drain_all now checks each peer's own debt exactly, so a wrong reading fails loudly.
- Segment pool: 3 writers x QUEUELEN 8 = 24 < 48. _SEGMENT_WRITERS = SEG // QUEUELEN + 1 = 7 at 1,600 (2 at 6,400), from both ends of 4 pairs; ceil(48/7) = 7 < 8.
- Intact data: "96 of 256 B" is upstream's partial write, MIN(tcp_sndbuf, len), with POLLOUT clear: the send buffer is the writer's first edge. Fix: accept 0 < written <= len. Halfway, the loaders fill the arena, the writer's next MSS write must be the patched EAGAIN, the loaders close, and the rest follows, every byte checked in order. SNDLOWAT 1599 plays no part (netconn only).
- Green: 3 rounds x both GC stages, 9/9 each (sb_lw_g2, about 27 s per run). Not under coverage: lwip_host files never run on build-settrace.
- 3,200 and 6,400 NOT run, a rebuild is needed: the only 6,400 build-lwip (tc-int/tc-gate/tc-mcov, 2026-10-26) lacks asyncio, which tests/microtest.py imports (ImportError, sb_lw_6400); 3,200 was never built. Derived counts there: loaders 2 / 1, writers 4 / 2.
2. B.14.4, re-measured on build-lwip at 1,600 (two runs, probe in ftmp_sb):
- Writes: every one within 58 us, EAGAIN ones within 23 us; the text now says "0.06 ms" (was 0.16 ms at 6,400).
- Edges: queue limit 8 segments; segment pool 48 with 7 writers.
- Capacity: 8,000 B = TCP_WND + TCP_SND_BUF, the same after close; stable over 20 rounds.
- "Without the insertion" is kept as the 6,400 B result (no unpatched host build exists at 1,600).
- F.7 row 23: "10,400 B (13 MSS)" now reads "TCP_WND + TCP_SND_BUF (8,000 B, 10 MSS)". Its "never accepts ENOMEM" now says the loaders' ENOMEM counts as queued and is never accepted at an edge under test.
3. Control proof at 1,600 (answer only): NOT reachable.
- The arena holds only send queues on the board (inbound uses PBUF_POOL), at most 1.125 x 1,600 = 1,800 B per pcb. Hammer peak: 5 non-readers + the page = 6 x 1,800 = 10,800 B < 12,000 B.
- The segment pool cannot run out from admitted connections alone (6 x QUEUELEN 8 = 48 = the pool). A queue-limit ERR_MEM would need 8 pbufs within 1,600 B, i.e. writes averaging < 200 B; the server's write sizes were not checked.
- The _hold phases hold at most dead + slow + /status at once, about 5.4 KB, and each host close sends an RST.
- So the control image meets no ERR_MEM, passes every bound, and test_send_stall_on_the_unpatched_image fails with _REMOVAL_SIGNAL.
- What it would take: >= 12,000 B queued at once. Either TCP_SND_BUF > 10,200 / (5 x 1.125) = 1,813 B with this 5-client hammer, or, at 1,600, device-closed pcbs keeping their queues in FIN_WAIT_1 (from the 5 s per-call timeout to the 10 s close abort) plus newly admitted ones: 9 pcbs x 1,800 = 16,200 B.
Outside these files (one line): test_modlwip_send_stall.py's _MIN_ZERO_WINDOW message ("the patched branch was never proven reached") no longer fits at 1,600, where zero window is the send-buffer edge.
Checks: lint_direct rc 0; mypy x3 clean; test_code_conventions, test_ticks_wrap_scan, test_comment_block_cap, test_tunables_register and the lwip_host readers (overrides, setup_toolchain_env, test_sh): 1361 passed. Nothing rebuilt or set up.
nothing of mine is running
