CRr2b5 hand-back, saved by the lead from the message it sent (2026-10-27). Commit c12d1bd6 on audit/u35-crr2b (on 575f8c22).

U35 lane CRr2b5 hand-back. Items 1 and 2 are done in one commit, along with finds 1 and 2 of item 3. I stopped at that seam at about 78 tool calls. Find 3, item 4 and one re-derivation are not done.

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad. Logs are in S/u35/laneC/crr2b5/.

**Commit**
- c12d1bd6 on audit/u35-crr2b, on top of 575f8c22. Not pushed; the tree is clean.
- One commit holds the mechanism, every set, the README text, finds 1 and 2, the widened hazard set and the new review verdict.

**The restart at 05:15**
- No run of mine was cut. i1_green and plants_i1 both have done lines at 05:09, and every later run began after the restart and finished. So no CUT line was needed.
- One labelling note: my run.sh wraps S/u35/lead/run.sh in `setsid timeout -k 15` and passes the label `../laneC/crr2b5/<label>`. The logs land in my folder, but RUNS.md shows these runs as "U35 lead ../laneC/crr2b5/<label>".

**Item 1: CRr2b4's diff reviewed and kept, with two fixes**
- The mechanism is correct as CRr2b4 wrote it:
  - The segment rule: `bounds = [before, *pre_clear, after]`, with only the first segment read as a continuing history (`cleared=i > 0`).
  - Duplicates are dropped, so each entry is named once.
  - The read is kept only after the PUT answers Valid.
  - `_saved_status()` sends one GET, shared with save_errcount.
  - One behaviour change: a /status without errcount now fails the clear before its PUT. That refuses to erase what cannot be read, so I kept it.
- Fix 1: the two-clear test now has WIFI W WLAN_TO_HOTSPOT in the first pre-clear read only, and it asserts that entry.
- Fix 2: the plant's expected list for "later segments read as continuing" is now only `a_clear_through_the_helper_then_the_same_history`.
- I added one fix of my own. mypy host found 3 errors at test_bench_log_check.py:228 and :245: CRr2b4's two lambdas used `None` returns as values. They are now `_clear_twice()` and a `save_text` function.
- Plants: all 9 caught (plant 0 is 575f8c22's fixture and helpers, plus 8 more), in `plants_i1.log` and again after the fixes in `plants_i2.log`. The log-check file: 43 passed (`i1_green.log`, `i2_logcheck.log`).

**Item 2: the sets.** Every new set below was "unmarked" before; line numbers are on src at 575f8c22.
- The CEIL pair is WEBSERVER W HTTP_REFUSED (asy_webserver_service.py:925) plus W HTTP_PEER_RESET (:953).
- Why the bus arms get CEIL: there are 3 readers plus 1 or 2 writer threads against a ceiling of 6 (devices/dev.toml:14), and the module's own retrying fetch (:512) treats a refusal at the ceiling as expected.

| Test | Set |
|---|---|
| bus_concurrency plain, ISL write, BMP write, SCD30 write | CEIL |
| bus_concurrency light degradation | CEIL + W HTTP_CALL_TIMEOUT (:348/:942) + W HTTP_REQUEST_CAP (:942) |
| bus_concurrency NTP outage | CEIL + NTP E NTP_NO_REPLY (asy_ntp_client.py:277) |
| bus_concurrency WiFi flapping | CEIL + CALL_TIMEOUT + REQUEST_CAP + W HTTP_SOCKET_ERROR (:945) + WIFI W WLAN_NO_AP (asy_wifi_service.py:623) + W WLAN_AUTH_FAILED (:620) + the NTP mid-flight group (below) |
| end_to_end hard resets | FRAM W FRAM_BLOCK_INVALID (asy_fram_manager.py:224-253) + E FRAM_STATUS_BYTE (:137) |
| memory_stress plain hammer | CEIL |
| network_resilience NTP retry | NTP E NTP_NO_REPLY (:277) |
| network_resilience NTP garbage | NTP W NTP_UNSYNC_REPLY (:324) |
| network_resilience DNS garbage | NTP E NTP_DNS (:424) |
| network_resilience spoof | NTP E NTP_NO_REPLY |
| network_resilience garbage NTPHost | NTP E NTP_DNS_NXDOMAIN (:422) |
| network_resilience garbage SSID | WLAN_NO_AP + WLAN_AUTH_FAILED + W WLAN_TO_HOTSPOT (:700) + W WLAN_SILENT (:697) |
| network_resilience nonsense values | CFGMGR_BMP3XX E BAD_ARG (asy_config_manager.py:640) + WIFI E BAD_ARG (asy_wifi_service.py:300, asserted at test :1013) |
| network_resilience slowloris | W HTTP_REQUEST_CAP (:942) |
| network_resilience abrupt disconnect | W HTTP_PEER_RESET (:953) + W HTTP_SOCKET_ERROR (:945) |
| test_wifi_networking unreachable NTP (find 1) | NTP E NTP_NO_REPLY |

- The NTP mid-flight group is E NTP_DNS_NOT_SENT (:420), E NTP_DNS (:424), E NTP_NOT_SENT (:270) and E NTP_NO_REPLY (:277).
- The garbage SSID set has no NTP entries: the SSID-change reconnect takes wifi_mode_lock (asy_wifi_service.py:559/:759), the same lock an NTP attempt runs under.

The five sets CRr2b4 did not reach:
- **test_an_incomplete_command:** unchanged, SYSTEM W CONFIG_LOST only.
  - The script boots the FRAM-wired build over an empty scratch config (script :63-:70). Its setup logs CONFIG_LOST at asy_system_service.py:753-756.
  - The config managers only set absent_at_boot (asy_config_manager.py:541); they log nothing.
  - The planted EIO (script :38-:51) fires inside erase_chip (:477), which runs after storage.quiesce() (:461). So no entry logged during the erase can persist.
  - CRr2b3's reason ("its FRAM write is the cut one") was wrong, but the set holds. Caveat: I inferred quiesce's pause from the paused-write path (asy_fram_manager.py:370) and did not read quiesce in full.
- **Stack exhaustion:** unchanged, TASK_RAISED (:328) + STACK_EXHAUSTED (:587) + CONFIG_LOST (:756). The script boots the FRAM-wired build over a scratch config (script :67-:77), and the reader it rebinds dies of RuntimeError into the supervisor (:555/:581-:587).
- **Escalation:** unchanged, but this is a find for you.
  - system_service_restarts_a_real_dead_task.py:54 builds SystemService with `LogConfig(None, ...)` (asy_print_log.py:446, fram=None). Its TASK_RAISED and TASK_BUDGET_REBOOT entries are RAM-only and die with the reset.
  - :589 is the only site that logs TASK_BUDGET_REBOOT.
  - So test_reset_reasons.py's `any(... TASK_BUDGET_REBOOT ...)` on production's SYSTEM history after the reboot can pass only on an older entry, and fails on a board whose log was cleared.
  - This is test code and the fix is your call. I took the conservative option and changed nothing.
- **UART hazard run:** widened by one entry, UART_resp W UART_CMD_DECLINED.
  - Path: asy_uart_comm.py:804, through `_accept_set` :302-:304. The legal first chunks are ACKed, then the exerciser's `_set_callback` (asy_uart_link_driver.py:117) declines them, because their id 0x07 (:47, :206) is not `_CMD_ECHO` 0x02.
  - The twin already pins this (tests/test_digital_twin_uart_link.py:977). Without the entry, the bench test would fail on its own provocation.
  - Not narrowed: SIZE_MISMATCH looks unreachable on the responder here (:271/:280 are on the GET-answer path; :311/:765/:784/:794 need an expected size the exerciser never asks for). I did not finish showing that for every site, so it stays.
- **serving_heap per-source:** not re-derived. I did not read allocation_need_per_source.py; the set is unchanged.

**The README:** "The bench log check" no longer says a clear hides what came before it. It now describes the per-segment reading.

**Item 3: two of the three finds done**
- Find 1: the marker is in (table above).
- Find 2: src does print the console line. asy_ntp_client.py:281 prints "Invalid NTP time received!" inside `_handle_ntp_sync_failure()` on every failed sync, so the old alternative passed whichever path ran.
  - I took the "one payload with its true code" option. The test now asserts `assert_module_error_log_contains(NTP, W NTP_UNSYNC_REPLY)`; its marker is that entry.
  - The `_GARBAGE_PAYLOAD` comment was also false ("mode 7", but the parser never reads the mode). It now says leap indicator 3.
  - This adds no bench time.
- Find 3 (memory_stress extended, through the twin): not done.

**Item 4:** not started (the calibration bleed and the scanner's decorator text).

**Checks**
- lint_direct rc=0 (`lint_i2.log`, `lint_i2b.log`).
- mypy: main rc=0, bench-conftest rc=0, host rc=0 after the fix (`mypy_host_i2b.log`; `mypy_host_i2.log` was the red pass).
- Readers: 1555 passed, 2 failed (`readers_i2.log`). Both failures are test_twin_record: the instruments with no entry (red at base) and the hash re-record.
- collect-only: 201/232 (`collect_i2.log`). Every marker entry resolves to a live catalog row.

**review_rows.py:** 8512 rows: CRr2 63, fixed 61, justified 128, biting 8260. `--check` rc=0 (`review_rows_check_i2b.log`). The one new row, test_a_marked_tests_entry_before_its_clear_inside_the_set_passes, is "biting", with the plants as its evidence.

**Files whose twin record changes:** tests_hardware/bench/conftest.py, tests_hardware/error_log_helpers.py, tests_hardware/README.md, and the bench files test_bus_concurrency_under_api_load, test_end_to_end_timing, test_memory_stress_bench, test_network_resilience, test_uart_link_under_api_load and test_wifi_networking.

**Deletions:** my plant tree S/u35/laneC/crr2b5/plant_i1 (twice) and the worktree's typings link (twice), each as its own literal-path rm. I did not touch S/u35/laneC/crr2b4/plant_i1.

**Left for the next block:** find 3, item 4, the serving_heap per-source re-derivation, the hazard set's narrowing, and your ruling on the escalation assertion.

nothing of mine is running
