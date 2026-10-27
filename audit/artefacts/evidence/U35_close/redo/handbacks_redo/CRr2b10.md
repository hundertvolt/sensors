CRr2b10 hand-back, saved by the lead from the message it sent (2026-10-27). Commits 950c3a83, fc6f42a6 on audit/u35-crr2b (on d8dfde93).

U35 lane CRr2b10 hand-back. Items 1 and 2 are done, one commit each on audit/u35-crr2b (worktree S/wt-u35crr2b, on d8dfde93). Item 3 is not started: I stopped at a seam at about 85 tool calls. Nothing is pushed and nothing is uncommitted; the typings link is removed.

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad. Logs are in S/u35/laneC/crr2b10/. Every run went through its run.sh (a copy of CRr2b9's with this lane's name): 23 runs, 46 RUNS.md lines naming "U35 lane CRr2b10", each run with a done line. Nothing was refused. I used no stash and no nohup, and did not touch S/u35/laneC/crr2b4/plant_i1.

**Commits**
- 950c3a83: the outage and flap bench tests name NTP's mid-flight entries and wait out its sync and retries.
- fc6f42a6: the console bench test drains the connection ceiling before its restore.

## Item 1: outage and flap tests (950c3a83)

**What changed** (tests_hardware/bench/test_network_resilience.py):
- **Both sets.** Before: WIFI W WLAN_NO_AP and W WLAN_AUTH_FAILED. After: those two plus NTP E NTP_DNS_NOT_SENT (src/asy_ntp_client.py:420), E NTP_DNS (:424), E NTP_NOT_SENT (:270) and E NTP_NO_REPLY (:277). Each marker's reason now names the NTP attempt.
- **`_assert_recovered()`** calls a new `_wait_for_ntp_quiet()` after `recover_by_reset`, on both paths. It polls one GET /status at a time for NTP's counter, NTPSynced and NTPLastSyncAge (codegen.py:283 emits both keys).
  - It requires Synced. The bound reuses `_NTP_RESYNC_AFTER_RESET_TIMEOUT_S` (120 s); past it, a TimeoutError names the last view.
  - If NTP's counter is above 0, it waits for an age newer than the last failure it counted, or until the chain bound passes since serving, whichever comes first.
- **The chain bound** is `_NTP_SYNC_RETRIES` × (`_NTP_RETRY_INTERV` + one attempt), plus a margin. Values are read from src and buildgen (`_ntp_attempt_s`, `_ntp_retry_chain_s`).
  - One attempt is 14 s: (1 + `_DNS_FALLBACK_MAX`) × `_DNS_TRIES` × 2 × `_DNS_TIMEOUT_MS`, plus 2 × `_NTP_FETCH_TIMEOUT_MS` (asy_dns_client.py resolve_ipv4 :159-176; asy_ntp_client.py :264-278).
  - The chain is `_handle_ntp_sync_failure()` (:280-302). A retry that finds no network ends silently (:428-430).
  - The bound is 3 × 29 + 10 = 97 s.
- **New Part N rows:**
  - `l4.network_resilience_ntp_retry_chain_margin_s` = 10.0
  - `l4.network_resilience_sync_age_slack_s` = 2.0: the 1 s age tick (asy_base_classes.py:387) plus whole-second truncation (:352).

**Bites** (bites_ntp.py, bites_ntp.log, 24/24 ok). Each case runs HEAD's test, a variant with the new set and HEAD's timing, and the new test, on a fake board in virtual time, each followed by an idle next window. Every window is judged by `assert_no_unprovoked_entry`.
- A group entry with a silently ended chain: HEAD's own window FAILS on E NTP_NO_REPLY; the new test's window passes.
- A retry failing after the old end: HEAD's next window FAILS on E NTP_DNS, and so does the new-set/old-timing variant's. The new test's own window holds the entry and its next window passes; it ended at a fresh sync 27 s after serving.
- Reset path, boot sync failing once after serving: HEAD's next window FAILS; the new test passes both windows.
- Reset path where NTP never syncs: the new test fails, bounded, at 120 s.
- The flap analogue of the retry case behaves the same.
- Healthy runs: identical, the new test adding one poll.

**Twin:** neither body runs there. The `bench` fixture skips under --twin (tests_hardware/conftest.py:232-233), so item 1 rests on the bites.

**Added bench time:** one GET /status when NTP logged nothing in the window. Up to 97 s after serving when it did (10-27 s in the bites when a sync follows). No write is added.

**Finding for the lead (not added, since it is an allow-list row):** E NTP_RETRIES (asy_ntp_client.py:300-301) is reachable in both windows.
- On the CYW43 false-positive path, `network_available_locked()` is `status == STAT_GOT_IP` (asy_wifi_service.py:985-986), so all three retries run and fail.
- The fourth failure lands about 3 × 29 s after the first, inside the 150 s first wait.
- CRr2b4 excluded it on an 18 s window, which these tests do not have. Bite case 8 shows the own window failing on it, under HEAD and under the new set.
- The same reasoning may apply to the bus flapping test, which is not mine.

## Item 2: the console test (fc6f42a6)

**What changed:**
- After `port.close()`, the test calls `_wait_for_slots_to_drain(dut_ip, 80, _MAX_CONNECTIONS, timeout_s=_CONSOLE_DRAIN_TIMEOUT_S)` when no adversary is still alive.
- The DebugLevel 5 restore moved into a `finally`, so a failed drain still restores it.
- New Part N row: `l4.console_starvation_drain_timeout_s` = 30.0.
- I re-checked `_serve` on this tree: every traced or served entry is written before the finally's `decrement()` (asy_webserver_service.py:914-971). Only the refused branch frees its slot first (:922-925).
- The set is unchanged: the probes can trace only HTTP_PEER_RESET and HTTP_REFUSED, both already in it.

**Bites** (bites_console.py, bites_console.log, 8/8 ok). The real drain runs against fake probe sockets.
- A warning written 3 s after the close: HEAD's next window FAILS, and the new test's own window holds it.
- The refused branch (slot freed, trace 0.2 s later): the same.
- A slot that never frees: the new test fails bounded at 30 s with the drain's message.

**Twin** (twin_drain.py, twin_drain.log, both GC stages, rc 0). The body needs `serial.Serial(board.device)`, and the twin's device is "dev" (twin_board.py:55), so I ran the test's adversary kinds against the dev twin's real webserver instead.
- **HEAD's end:** the first request after the join was REFUSED (CeilingRefusedError) at both stages. That request is the restore PUT in the real test, so HEAD's restore raced the ceiling. fc6f42a6 fixes it.
- **The new end:** the drain took 2.9 s at -1 and 1.7 s at 32768, the next request got 200, and every window passed with its next window gaining nothing.
- **Rings:** only WEBSERVER [FRAM] has entries, all of them codes in the test's set. 0 memory markers.
- **One entry I cannot fully explain:** at 32768 the RAM-only FRAM logger held E FRAM_STATUS_BYTE and W FRAM_BLOCK_INVALID, outside every judged window. They most likely come from the boot over the FRAM state my first, crashed run left in the same state dir. That crash was the CeilingRefusedError above, in my script.

**Added bench time:** about 2-3 s, at most 30 s.

## Deviations
- I first put the drain after the restore, against CRr2b9's design. The twin's refusal showed why that is wrong, and the commit follows the design.
- To keep `hw_no_log` with its "fixed" verdict, I reworded the drain comment. The scanner's HW_LOG regex (redflags.py:55) matched "logs"/"logged" and falsely credited the test with a log read.
- One check's output was too large and the harness saved it under /root/.claude/. I did not open it.

## Checks
- lint_direct rc 0, mypy host rc 0, collect-only 201/232.
- Readers: 1279 passed, 2 failed, both test_twin_record (the instruments with no twin record, red at base, and the hash re-record).
- Comment cap, tunables register, citations, decision vocabulary and the bench log check: 727 passed.

## review_rows.py
8512 rows: CRr2 63, fixed 67, justified 128, biting 8254. The counts are unchanged; review.md was re-rendered for shifted lines.

## Twin record changes
tests_hardware/bench/test_network_resilience.py.

## Left
- Item 3: the overlap fix in its two sibling scripts and the HTTP bench counterpart of the ISL test (crr2b2 item 3). Untouched.
- The NTP_RETRIES row above, for the lead.

nothing of mine is running
