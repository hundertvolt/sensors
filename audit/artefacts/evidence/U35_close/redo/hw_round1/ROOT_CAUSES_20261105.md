# Round 1 root causes, control image: for the main session (bench session, 2026-11-05)

Asked by the main session, 12:55 UTC. Evidence is from `logs/4g.log`, `logs/5g.log` and `logs/4a.log` (git-ignored on the Pi),
`build/archive/run_bench_hardware_suite/20261105T110340Z/`, the Pi's `journalctl`, and my own runs on the board at 12:29-13:02 UTC.
Addresses are masked. Status words: **confirmed** (reproduced or read directly), **inferred** (fits the evidence, not tested).
Paths are from the bench branch's tree, head `1d2f900a`. The fixes are proposals; I changed no code.

## 1. picotool retry: confirmed exit, inferred timing

- **Where:** `tests_hardware/flash/test_system_commands.py:275-277`. Same single try in `tests_hardware/bench/test_system_commands_over_rest.py:76-78`, called at `:218`.
- **Symptom (4g, 10:35 UTC):** `harness.HardwareTestFailureError: picotool reboot found no BOOTSEL device (exit 249):` / `No accessible RP-series devices in BOOTSEL mode were found.` The kernel shows the BOOTSEL device up at 10:35:23 (`idProduct=0003`, `Product: RP2 Boot`). `sudo picotool info` found it at 10:47 and `picotool reboot` worked at 10:48.
- **Effect:** the board stayed in BOOTSEL for 13 minutes. The next 22 tests had no board, and the `finally` at `:281` could not remove `hwtest-scratch/`, which stopped the next two sessions at the standard-state check.
- **Fix:** retry while `_retryable_picotool_exit()` (`tests_hardware/harness.py:278`, exit 249 at `:97`) holds, as `reflash()` does at `:594-608`.

## 2. Kick timing: confirmed

- **Where:** `tests_hardware/bench/test_bus_concurrency_under_api_load.py:448`, called right after the PUT is accepted. `test_system_commands_over_rest.py:161-165` (the erase, and `:190` the raced commands) has no kick before the command's own reset. The workaround is `tests_hardware/bench_control.py:209-216`.
- **Symptom (5g, `test_fram_erase_under_api_load`), `journalctl`:**

```
11:12:25 kick; USB disconnect (reset_and_wait)
11:12:35 AP-STA-CONNECTED <mac>
11:12:40 iw station del <mac>         the kick after erasefram was accepted
11:12:43 AP-STA-CONNECTED <mac>       the board, still shutting down, rejoins: the stale entry is back
11:13:02 USB disconnect               the erase's own reset, about 22 s after the kick
11:13:43 iw station del <mac>         the 60 s wait ran out; recovery kick
11:13:45 AP-STA-CONNECTED <mac>       joined 2 s after the kick: the entry was what blocked it
11:13:51 USB disconnect               see item 3
11:15:45 AP-STA-DISCONNECTED <mac>    the AP drops the entry by itself
11:17:33 USB disconnect               next test's reset
11:17:43 AP-STA-CONNECTED <mac>
```

- **Then, by design:** the failed streak logs `WIFI W38` (`_WRN_WLAN_CONNECT_FAILED`) and `W79` (`_WRN_WLAN_TO_HOTSPOT`), saved in `errcount-erase-over-rest.json`. `dev` then holds its hotspot for `hotspot_time_min = 8` (`devices/dev.toml:10`). No firmware defect here.
- **Cascade:** 84 tests failed in setup, 61 as `the log check cannot read the loggers before the test - GET /status on <addr>: URLError(OSError(113, 'No route to host'))` and 23 as the same `URLError`. Each took about 3 s, so they all fell inside the hotspot window, from about 11:14 to 11:17.
- **Fix:** kick after the slow command's reset, for instance when USB drops (`board.is_device_present()`), not before it. A command whose shutdown lasts tens of seconds outlives a kick sent at the reply. Separately, the log check's setup could wait or reset once rather than fail every test at once.
- **My own runs hit this too:** after a plain `mpremote reset` with no kick, the board was off the network at 13:03, and two of my probes in item 8 returned nothing. That fits the same stale entry; I did not check it further.

## 3. Serial conflict in `recover_by_reset`: inferred

- **Where:** `tests_hardware/harness.py:520` (`observe_during` tails the port for the whole action), `:572-589` (`recover_by_reset`), `:514-517` (`kick_then_reset`), `:895` (`hard_reset`, `mpremote reset`). Reached from `tests_hardware/bench/test_bus_concurrency_under_api_load.py:449-452`.
- **Symptom:** `harness.HardwareTestFailureError: mpremote reset failed (exit 1):`, failing in `mpremote/transport_serial.py:190`, `read_until(1, b"raw REPL; CTRL-B to exit\r\n>", ...)`.
- **Reasoning:** `tail_log()` has the same serial port open and reads it, so it can take the prompt `mpremote` waits for. USB still dropped at 11:13:51, which fits a Ctrl-C that did arrive (`RR_INTERRUPTED`, 21). I did not run a test of this.
- **Fix:** stop the tail around the recovery reset, then restart it. A failed reset there also lost the test's real error, so the raise should keep the timeout as its cause.

## 4. The two tests that reach a real board: confirmed

- **Where:** `tests_scripts/test_tests_hardware_run_record.py:66` (`test_result_note_and_session_notes_land_in_the_record`) and `:83` (`test_a_session_note_is_printed_when_no_record_is_written`). Both load `-p conftest`, so the session autouse fixtures `fram_evidence_saved` (`tests_hardware/conftest.py:322`) and `standard_state` (`:463`) run. `_board_if_present` (`:311`) acts on any attached board.
- **Step:** 4a, `scripts/test.sh`, `tests_scripts` tier.
- **Symptom:** the 12:12 UTC run. `build/archive/pytest/20261105T120455Z` and `T120620Z` each hold `errcount-session-{start,end}.json` and `fram-raw-session-{start,end}.txt`; the guard reports `8 new path(s)`. In the same window, 12:04:55-12:07:25: 12 USB disconnects, 10 `iw dev wlan0 station del`. With `MPREMOTE_DEVICE=/dev/no-pico-serial-device-detected` the 12:43 run reports `0 new path(s)`.
- **Fix:** run both with `--twin`, or set that variable in `_pytest()`'s environment. Until then 4a needs the variable on this bench, and Node 24 first on PATH.

## 5. Soft-reset channel comparison: confirmed

- **Where:** `tests_hardware/flash/test_uart_crossover.py:243`; `tests_hardware/device_scripts/uart_dma_ring_interrupts_off.py:134`, `:346`, `:76`, `:80`.
- **Symptom:** `the DMA channels the ring held were not free after the soft reset: [1, 2, 0] -> [0, 1, 2]`.
- **Cause:** the same three channels. Before, `_Sender` claims first, then the ring, and the fact lists `[rx, reload, sender]`. After, the script claims its two first and then the sender. So it can only match by chance.
- **Fix:** compare as sets. The test then goes on to `:244` and its `hard_reset()` at `:245`, which it skipped here.

## 6. `build()` feed: confirmed

- **Where:** `tests_hardware/device_scripts/uart_dma_ring_interrupts_off.py:136-145` (`_Sender.build`), reached through `_soft_reset()` at `:336`.
- **Symptom:** `test_a_soft_reset_during_traffic_leaves_no_running_ring[crc16]`, `OSError: [Errno 5] Input/output error` in `mpremote`, with output ending at `FACT gc_threshold=-1`.
- **Cause:** measured `CRC16.add` on a 53 B frame: 20,728 us on average. A 2 s stream is 419 frames, so about 8.7 s unfed against the 8 s watchdog. Reproduced alone: USB gone after 9.6 s, 12:30 UTC.
- **Fix:** pass `wdt` and feed in the loop, as `finished()` does.

## 7. `_serving_status`: inferred

- **Where:** `tests_hardware/bench/test_system_commands_over_rest.py:102-108`, read at `:221-222`.
- **Symptom:** `the winner's code 3 not read: 21 ({'reboot': 'Valid', 'bootloader': 'Failed'})`.
- **Cause:** it accepts any 200, including from the boot that has not yet reset. USB shows no reset between the rejoin at 11:23:49 and the cleanup's at 11:24:00, so it read the old boot, and 21 is what the previous reset left. The reboot's own reset did not get to happen.
- **Fix:** take `BootSignature` before the command and wait for it to change.

## 8. The `MemoryError`: reproduced; cause measured on the board (update 13:55 UTC below)

- **Exact lines (console, `DebugLevel` 5):**

```
WEBSERVER Microdot caught: memory allocation failed, allocating 242 bytes
WEBSERVER Unhandled exception in route handler: memory allocation failed, allocating 242 bytes
```

- **Logged as:** `WEBSERVER` `E23` (`_ERR_UNEXPECTED`), FRAM-backed, through `src/asy_webserver_service.py:729-734`.
- **Caught, not a crash:** the client gets `{"code": 500, "res": "ERR", "descr": "Internal server error", "result": {}}`, after 1.6-4.1 s in the 5g test. No reboot: `BootSignature` held across a run.
- **Test and step:** 5g, `tests_hardware/bench/test_uart_link_under_api_load.py::test_a_hazard_run_under_the_readers_load_reports_every_verdict` (`check_hazard_run_under_load`, `:258-279`): `89 API issue(s) during the hazard run: worker 2 iter 0: GET /status answered 500 in 4.1s; ...`, with the `WEBSERVER` counter at 122 and `E23` in its history, saved in `errcount-test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing-1.json`.
- **Image:** `gc_control.uf2`, commit `dca91249`, `BuildDate` `2026-11-05T09:19:30Z`, with `gc.threshold(32768)` removed from `buildgen/codegen.py:835`, so the reactive default of -1. `overrides ['modlwip_eagain']`. Not run on an image with the threshold.
- **It does not need the hazard run.** I wrongly suggested that earlier. Three readers of `GET /status` every 50 ms are enough:

| Load | From | Reads answered 500 | `WEBSERVER` counter added | `MemFree` min / median / max (from the 200s) |
|---|---|---|---|---|
| 3 readers, 60 s | boot, uptime about 10 s | 14 of 46 | 14 | 2,416 / 15,328 / 42,848 |
| 3 readers, 60 s | boot, uptime about 12 s | 8 of 46 | 8 | 2,096 / 19,232 / 36,384 |
| 3 readers, 60 s | settled, uptime 72 s | 10 of 48 | 10 | 1,552 / 16,832 / 35,312 |
| 1 reader, 60 s | settled, uptime 567 s | 0 of 42 | 0 | 80 / 33,664 / 53,696 |
| 2 readers, 60 s | settled, uptime 634 s | 1 of 46 | 1 | 784 / 23,568 / 52,640 |
| 3 readers on `/measurements`, 60 s | settled, uptime 703 s | 0 of 313 | 0 | not read |
| 3 readers + `UartHazards`, 150 s | uptime about 20 s | 38 of 109, plus 3 timeouts and 5 resets | 75, `W48` and `W60` among them | not read |

- **Failed sizes:** 242, 250, 251, 252, 253, 254, 255, 256, 257 bytes.
- **Reproduce:** `DUT_IP=<addr> .venv/bin/python repro_status_load.py base 3 60 /status`; add the hazard run with `hazard` in place of `base`. Needs `pyserial` from the venv, and the console must be free. Writes no flash, only `WEBSERVER` log entries to FRAM.
- **Lead (inferred):** those sizes sit just under `_DEFAULT_CHUNK_BYTES = 256` (`src/asy_webserver_service.py:149`), so the failing allocation looks like `_PieceWriter`'s piece join (`:200-219`) during `_build_status_pieces`. The comment at `:150-151` sized that value to the holes a fragmented heap has at -1. A failure at 256 B would mean those holes are now smaller, or the heap is really full.
- **So it depends on overlapping `/status` requests.** One response is 7,369 B and takes 1.4 s; `/measurements` is 572 B and takes 0.24 s. `_build_status_pieces` (`:641-671`) builds the whole response before any of it is sent, with awaits between sections, and `_pieces_response` (`:971`) holds every piece until the socket has taken it. So each open `/status` holds up to about 7.4 KB in 256 B blocks while others build theirs, and each build also reads config files (212 `Reading config data` lines over 42 requests). This fits the rates above; I did not measure the heap at the moment of failure.
- **Measured with a heap map at the failure (13:20-13:50 UTC, no flash write).** `heap_probe/heap_probe.py` runs the frozen firmware on the control image under `mpremote run`, wraps `_PieceWriter.flush`, and prints `micropython.mem_info(1)` from the `except MemoryError`, before anything is unwound. Allocation failed after its own collection, so those maps show live data. Maps: `heap_probe/heap_maps_20261105.txt`. 3 readers, 60 s, one run each:

| Run (`mpremote run`, control image) | Reads | Failed flushes | Baseline after `gc.collect()`, idle: free / runs / largest | Free at failure | Largest free run at failure |
|---|---|---|---|---|---|
| `gc.threshold` -1 | 21 answered 200, 10 answered 500, 1 timeout | 11 | 57,632 B / 384 / 153 blocks | 13,952-23,392 B | 12-15 blocks (at most 240 B) |
| `gc.threshold(32768)` (set by the script, where `main.py` sets it) | 37 answered 200, 8 answered 500 | 8 | 58,224 B / 142 / 122 blocks | 12,640-16,208 B | 15 blocks in the 3 maps taken |
| 32768, pieces of 128 B | 36 answered 200, 1 answered 500 | 1 | 57,936 B / 121 / 144 blocks | 12,784 B | 7 blocks (112 B) |
| 32768, pieces of 256 B, overlapping requests share one built response (2 s) | 117 answered 200, none 500 | 0 | 58,000 B / 127 / 87 blocks | no failure | no failure |

- **Corrected 2026-11-06: the "largest" column above and the room figures here came from a `heapmap.py` that dropped the `(N lines all free)` lines, so they understate idle.** Rebuilt from the map addresses, matching `mem_info`'s `max free sz`: largest idle run 489 blocks at -1 (not 153) and 2,338 at 32768 (not 122). The 128 B and share rows' 144 and 87 are wrong the same way, and those maps were not kept. At-failure figures stand.
- **Answer to the question asked at 13:45: placement, driven by load, on both GC settings.** The allocation fails with 12-23 KB free because no run of 16 blocks (16 B each) is left: `max free sz` 15 and 0 blocks in usable runs, at both settings. At idle the threshold helps (corrected): runs 385 to 142, largest run 489 to 2,338 blocks, room in runs of 16 blocks or more 2,664 blocks (42.6 KB) to 3,207 (51.3 KB). That gain does not survive to the failure.
- **Mechanism (measured sizes, the sum is my arithmetic).** A `/status` piece of 256 B takes 17 blocks of data plus the 1-block `bytes` object. 7,369 B is about 30 pieces, so about 8.6 KB per held response. Objects of 16-63 blocks grow from 858 blocks at baseline to about 2,040 at failure (-1), and 2,270 (32768): 2.2 to 2.6 responses. The "15 KB of usable runs" this line first compared them with was the `heapmap.py` undercount (corrected above); real idle room is 42.6-51.3 KB, so that arithmetic does not explain the rates: 1 reader 0 of 42, 2 readers 1 of 46, 3 readers 8-14 of about 46.
- **Six readers, the configured ceiling (13:50-13:55 UTC, 32768, 60 s, one run each):** plain: 22 answered 200, 24 answered 500, 5 timeouts, 25 connection resets. With the share hook: 98 answered 200, 3 answered 500, 39 connection resets, largest free run 15 blocks at its failure. So the 2 s share does not hold at the ceiling. I did not look into the connection resets or into what filled the runs in the 3 failures; the hook rebuilds every 2 s while a slow send can still hold the previous list, which may be part of it.
- **Reachable in ordinary use:** `/status` is by far the largest body: 7,375 B, against 614 B (`/sensors`), 576 B (`/measurements`), 220 B or less (`/networking`, `/system`, `/notification`). `test_openhab_case_two_pollers_and_an_open_website_are_all_served` (`tests_hardware/bench/test_network_resilience.py:835`) has one client polling `/status`, and the website fetches it too (`js/shell.js:96`, `js/render.js:630`). That test has not run on this image; it was in 5g's cascade.
- **The intervention supports it:** sharing one built response among overlapping requests is the only change between the 8-of-45 run and the 0-of-117 run. The share is a test hook with a 2 s window, not a proposed fix: it serves data up to 2 s old.
- **Corrections to my lead above:** builds do not overlap. The probe's in-flight counter around `_build_status_pieces` peaked at 1 in all four runs. What overlaps is the send: `_pieces_response` keeps the pieces alive until the slow send ends (1.4 s). The sizes just under 256 B are `flush()`'s join (`:242`), now caught there.
- **Smaller pieces only move the limit:** 128 B still failed once in 37, with the largest run down to 7 blocks. They also add overhead per byte. The comment at `:150-151` ("sized to the holes a fragmented heap still has") does not hold here: the holes left at failure are smaller than the piece.
- **The budget in Part N is too high for `dev` on this silicon:** `web.serving_demand_budget_b` is 72,232 B, an estimate from "about 105,000 B free after boot", with "measurement owed". Measured: 57,632-58,224 B free after `gc.collect()` at idle, uptime 45 s, in four boots. `dev`'s demand of 68,790 B is more than that free heap, and much more than the usable runs. Not checked on another device: only `dev` is benched.
- **Options as I see them, for the unit to judge:** keep one response's pieces alive per route, whether by sharing the same list among requests that arrive during a send or by a lock around build and send. Or stream, one piece alive per connection, which loses the exact `Content-Length` and the 500 status for a late failure. Only the share was tried, and only as the test hook. I have not tested other routes under a mixed load.
- **Limits of these four runs:** one run each. The firmware ran under `mpremote run` rather than `main.py`, so the script's compile and the wrappers are on the heap (the idle free matches across all four). A failure's map printing adds delay, so read the rate as a rate under the probe, close to the earlier plain runs.
- **Also seen under this load:** `UARTLINK` `Failures` rose by 2-4 per minute, though `test_the_link_stays_healthy_while_the_api_is_hammered` passes, and it hammers something other than `/status`.
- **Why the suite did not see it first:** 5g's `test_serving_heap_at_default_gc.py` tests never ran; they were in the cascade.

## 9. `test_two_concurrent_cancellers_both_return` on the Pi: not root-caused

- **Where:** `tests/test_asy_uart_driver.py:970`: `assert second_result is True`. Full output: `test_asy_uart_driver_20261105T124309Z.log` here.
- **History:** passed in the 12:12 UTC 4a run, failed in the 12:43 UTC run, at 16 parallel files. 164 of the file's 165 tests passed.
- **Not done:** I have no repeat rate, because my repeat runs used a wrong module path. A third 4a is running now and will add one sample.

- **4a's third run (12:50-13:18 UTC):** this test passed (165 of 165), so it is intermittent on the Pi: 1 failure in 3 full runs here. The same run failed `test_only_the_api_writes_the_scd30[wozi]` with `AssertionError: (4, 3, 2)` at `tests/_sensortask_scenarios.py:3078`, which passed in the 2 runs before. Output: `test_sensortask_wozi_20261105T131850Z.log`. `test_sensortask[dev]` exceeded its 240 s and passed on attempt 2 in 2 of the 3 runs (83 of 101, then 95 of 101, when stopped).
- **Lead on `(4, 3, 2)` (inferred from reading, not tried):** `idle_ticks` is read after 10 ticks (`tests/_sensortask_scenarios.py:1417`, `4 * interval + 2`, interval 2 s). The 4 means the counter went back to 0 at about the sixth tick, which `_frc_reset()` or `_frc_step()` does (`src/asy_scd30_driver.py:384, 398`). The helper does not wait for the reader's init before it ticks, so a late soft reset on a slow host would do this. I did not inject a delay to test it.

## 10. Other 4g and 5g failures

| Test | Result | Status |
|---|---|---|
| `test_the_link_keeps_transferring…[crc16]` | 9 transfers (floor 20), worst round trip about 1,700 ms (limit 500 ms). `none`: 93 and 167 ms. Zero failures, echoes intact | Confirmed: CRC16's Python cost against limits measured without CRC. Needs per-mode limits or a faster CRC |
| `test_get_and_set…[crc16]` | `largest_block` grows by exactly 768 B, 4 of 4; `none` equal | Not explained; growth is not a retained allocation |
| `test_no_frame_is_lost…[none]` | `after_intact` 0 of 4 | 1 in 24 runs. Not explained, firmware not excluded |
| `test_reboot_falls_back…` teardown | `/status` timed out after a passing test | Not verified |
| `test_fram_erase_blanks…` and 6 others in `test_system_commands.py`, `test_bus_concurrency.py` | The script's output ends before `erasefram`, with no `failure` fact. `refusals`, which skips `_seed()`, passes | Inferred: `_seed()`'s 60 unfed FRAM writes outlast the watchdog. Not tested |
| 5g's NTP tests, first 200 after the RTC set, SGP40 `W33`/`W35`, `E85`, `UART_resp` `W56`/`E80`, `wifi_radio_reinit_recovery.py` | See `logs/5g.log` | Not read yet; they need a run without the cascade |
| 4g's other 9: `test_chip_conformance.py` (4), `test_memory_stress.py` (3), held SDA, general call | Listed in my 10:50 UTC report | Measurements, not read further |

## 11. 4a's later stages on this Pi, first run (`b6a7bc1e`, 13:22 UTC onward, old head)

Run by hand after `scripts/test.sh`, each stage even if an earlier one fails, with Node 24.22.2 and `MPREMOTE_DEVICE` masked. My board probes (HTTP and serial only) ran during part of the GC stage; I did not separate their effect.

- **`GC_THRESHOLD=32768 scripts/test.sh`: exit 1, 2,044 s.** `gc32768_summary_20261105T135658Z.txt`. No `MemoryError` line named. 5 files failed: 4 exceeded `PER_FILE_TIMEOUT_S` (240 s) on all 3 attempts, and 1 scenario failed.
  - `tests/test_sensortask.py[dev]`: 38, 33, 35 of 101 when stopped (at -1 it reaches 83-101).
  - `tests/test_sensortask.py[wozi]`: 83, 64, 82 of 101.
  - `tests/test_digital_twin_bus_hazard_concurrency.py`: 22, 20, 22 of 25.
  - `tests/test_digital_twin_uart_link.py`: 4 of 22 on all 3, each at `test_a_hazard_run_put_through_the_api_while_readers_hammer_it_reports_every_verdict`.
  - `scenarios[dev]`: `loop_lag_under_combined_load`: "the SGP40 fault storm never reached its 5-read streak under the load (40.1s)".
  - **Inferred, not measured per file:** collecting every 32 KB on the Unix port's 16 MB heap is much slower on this Pi, so these look like the slow-host class rather than firmware. Stopped by a time limit, they say nothing about the tests they never reached.
- **`npm test`: exit 1, 942 s.** `npm_live_backend_failure_20261105.txt`. 1,622 passed, 1 failed, 1 passed on retry: `tests_js/live-backend.test.js > live digital-twin backend: arzi > the real website ... round-trips a real PUT`, "still applying DebugLevel when its test's 45000ms were up". The twin's output also says "UDP port 123 is held by another NTP responder". Cause not looked into.
- **Twin CI (`scripts/run_digital_twin_ci.sh`, finished 16:24 UTC, before the final code landed):** exit 0 on all six: `arzi` 1,275 s, `dev` 1,570 s, `grkizi` 1,274 s, `klkizi` 1,241 s, `schlafzi` 1,279 s, `wozi` 1,295 s. These still count as `b6a7bc1e`'s, not the final head's.

## 12. Final image `b7533307`, first results (16:25-16:43 UTC)

**The `/status` silicon check is improved but not clean.** `repro_status_load.py base 3 60 /status` on the plain final image, run 3 times at about 70 s each, no flash write:

| Run | 200 | 500 | Failed allocation | Lowest `MemFree` sampled | Failure after start |
|---|---|---|---|---|---|
| 1 | 51 | 1 | 250 B | 9,296 B | about 36 s |
| 2 | 51 | 1 | 250 B | 7,200 B | about 13 s |
| 3 | 51 | 1 | 250 B | 4,544 B | about 25 s |

- 3 of 156 reads failed. Before the fix, on the control image under `mpremote run`, it was 10 of 32 at threshold -1 and 8 of 45 at 32768. The two setups aren't identical, so the comparison is indicative.
- The console shows `WEBSERVER Microdot caught: memory allocation failed, allocating 250 bytes` and `Unhandled exception in route handler: ...`, so the project's memory gates would count these. Full console, masked: `status_silicon_check_console_20261105.txt`.
- 250 B is below `web.chunk_bytes` (256 B), which points at `_PieceWriter.flush`'s join, as before. Inferred from the size; I took no traceback on this image.
- No reset: uptime continued, `LastTaskEnd` stayed null. `WEBSERVER`'s FRAM counter went 230 to 233. Nothing was cleared.

**UART link failures under the same load (not new).** `UART_init`'s `Failures` was 0 after about 580 s idle, then 4, 8 and 11 at the end of each run. The console has `no ACK for frame N` (16) and `train stalled at chunk N` (4), each followed by a resync. The control-image probes show the same resync lines (3 and 9), so the `/status` fix didn't cause them. Cause not looked into; loop lag under HTTP load is the first thing to check.

**Step 3 reads rc=1 in the hand-back, but the image is good.** It flashed and verified at 16:29:41, then `/system` and `/status` got no answer within 180 s each. AP log: the stale entry dropped at 16:31:03 and the board rejoined at 16:38:58, its hotspot time being 8 minutes. `/system` read by hand afterwards: `board_BuildDate=2026-11-05T16:25:34Z`, matching the record. I did not reflash.

`round1.sh`'s `flash()` has no kick, unlike the harness's new `kick_after_reset()`. 3g got through at 09:24 with the same `flash()`, so this depends on the AP's entry at that moment. `get system 180` is shorter than the worst case of about 9.5 minutes. **For the main session:** `flash()` is used again by 15's fallback, and 180 s will fail again in that case. The runner is yours, so I have not changed it.

## 13. Step 4b on the final image (`logs/4b.log`, archive `build/archive/run_flash_hardware_suite/20261105T165007Z`)

**Run at 16:50, 1,410 s: 72 passed, 14 failed, 4 skipped, 17 deselected.** All 14 also failed on the control image, and none is new. The cascade is gone: 4g's first run had 39 failures. `test_no_frame_is_lost…` (both modes), `test_get_and_set…` (all three) and `test_comm_hazards…` (both) pass. No `MemoryError` line appears in the log.

| Test | Measured | Reading | Status |
|---|---|---|---|
| `test_a_held_sda_line…` | `stuck_errno` None | `_stuck_errno` uses `writeto(address, b"")`. On rp2 a zero-length write goes through soft I2C (`ports/rp2/machine_i2c.c:127-142`), whose start doesn't check SDA, so a held-low line can read as an ACK. A test assumption. Proposed: a 1-byte transfer, which takes the hardware path | Path read in the pinned source; not tried on the board |
| `test_bmp3xx_alone…` | `pwr_ctrl` 0 to 3 | `before` is read before the reader's first forced read. The same run's conformance shows `B05_pwr_ctrl_after_conversion` 03 on the chip, so the enable bits stay after any conversion; the general call need not be involved. Proposed: take `before` after one read | Inferred |
| `test_fram_erase_blanks…`, `test_an_erase…[mempause]` | erase `ok` in 16,529 and 16,370 ms; `reset` code 8 reached; then `no_reset_after_ms=16000` | `_RESET_WAIT_MS` (2 x watchdog, 16 s) runs from the command's answer, so it ends about when the erase does, before the reset's one-shot fires. The script then ends the run itself. Script timing, not firmware. Proposed: start the wait at the `reset` fact | Inferred from the facts' order and figures |
| `test_fram_erase_racing…` | `erase` None | Likely the same wait: with loads the erase ends later than 16 s. `[loads]` in `test_system_commands.py` passed in the same run, so it's a close race | Inferred; I read only the assertion |
| `test_scd30_matches…` | `C03_read_before_a_command` chip `dddddd`, twin `000000` | Twin differs from the chip | Measured at both GC settings; datasheets not checked |
| `test_sgp40_matches…` | `A02_serial_stable` chip `yes`, twin `no` | Same | Same |
| `test_bmp3xx_matches…` | `B03` 13/00, `B05` 03/00, `B07` 10/70, `C02` 0000/0200 (chip/twin) | Same | Same |
| `test_fram_matches…` | `C02_wel_after_write` chip 1, twin 0 | Same | Same |
| `test_real_gc_heap_headroom…` | 128,576 B used (bound 100,000); free 59,568 B; largest 44,896 B (min 32,768) | Over by 28,576 B, about equal at -1 and 32768. Bound or graph: yours to judge. The free figure is below Part N's 68,790 B demand and 72,232 B budget, as in item 8 | Measured |
| `test_routine_no_yield…` | `voc_max_us` 41,345 (bound 21,000); `gc_max_us` 17,680 | VOC stretch about twice the GC term | Measured |
| `test_c_stack_peak…` | 4,020 B of 7,936 B (half is 3,968 B), chain `fram.get_values_sync` | 52 B over | Measured |
| `test_the_link_keeps…[crc16]` | 9 transfers (floor 20) | Item 10: CRC16's Python cost against limits measured without CRC | As item 10 |
| `test_reboot_falls_back…` teardown | `/status` timed out after a passing test | Not read | Open |

**The first 4b attempt at 16:44 ran no test.** All 90 skipped: the `board` fixture's one `is_reachable()` call failed, and being session-scoped, that skips the whole tier (`tests_hardware/conftest.py:207`). The board reset at 16:44:30, then went to its hotspot through the stale entry. It came about a minute after the third load run. Three later probes took 0.4 s each, and the rerun at 16:50 got through. Not explained; 1 sample. The gate correctly read the skips as failures. Proposed: retry the probe once.

**The image record reads dirty.** I edited this file in `audit/` while the image built. No file outside `audit/` differs between `b7533307` and the head, so the firmware is `b7533307`'s.

**Plan unless you change it:** the final 4a now, no board. `PER_FILE_TIMEOUT_S=900`, which `scripts/_run_lower_levels.sh` applies to both GC stages since they share the variable. Device mask off, to check your `--twin` fix under real conditions. A `STOP` at 20:45 UTC keeps it inside the window; the full stage list may not fit (about 4 hours at today's times), so the rest of the twins go to day 2. `run 5` stays on day 2, because its 66 prerequisite flash writes would be spent again if the `/status` result (item 12) leads to a new image.

## 14. Answers to the lead's 17:34 UTC asks (17:40-18:02 UTC, no flash write, nothing cleared)

**Record of the 4a setting:** the final 4a (started 17:17 UTC on `b7533307`) runs with `PER_FILE_TIMEOUT_S=900`, Node 24.22.2 and no device mask.

**Loop lag under `/status` load, measured once.** `heap_probe/lag_probe.py`: the frozen firmware under `mpremote run`, threshold 32768, one extra task timing `sleep_ms(10)`; 3 readers, 60 s. 4a was running (load about 8), which slows the readers, not the board.

| Window | Ticks | Lag over 200 ms | Over 925 ms | Largest lag |
|---|---|---|---|---|
| Idle, 60 s | 4,920 | 0 | 0 | 87 ms |
| Load, 70 s | 1,676 | 26 | 14 | 2,625 ms |
| After, 30 s | 2,460 | 0 | 0 | 85 ms |

- 925 ms is `con.uart_reply` on `dev`, so the loop alone can use up the link's reply budget under this load. That fits the `no ACK` failures. Inferred: this session logged only 2 UART errors in the load window, so most long stalls hit no transfer waiting for a reply.
- A lag is a whole turn of the task queue, so this doesn't separate one long stretch from many tasks. I didn't locate the stall. Your 5 config reads per `/status` is the first place to look.
- `test_loop_lag_under_combined_load…` runs in step 5 and may fail on this.

**`/status` failures, 6 more runs:**

| Boot path | Runs | 200 | 500 | Failed allocation |
|---|---|---|---|---|
| Through the 8-minute hotspot, 16:39 | 3 | 153 | 3 | 250 B |
| Through the hotspot, 17:54 (uptime 596 s on) | 3 | 150 | 2 | 256 B, 251 B |
| Joined directly, 17:40 (uptime 1,620 s on) | 3 | 156 | 0 | none |

Lead only: 5 of 308 against 0 of 156 is weak given so few failures, and the direct session is one boot at a later uptime. Lowest `MemFree` sampled through the hotspot at 17:54: 5,584-10,544 B. UART errors appear on both paths (7, 7, 4 direct; 10, 7, 10 hotspot).

**The 16:44:30 reset:**
- **Reset reason: lost.** The board was off the network until my probes at 16:48:53-16:49:25, and each replaced it. `/status` at 16:50:40 reads 21, from those probes.
- **SYSTEM log:** counter 0 at 16:43 and in `errcount-session-start.json` at 16:50:40, so no SYSTEM entry from around then. The `archive/.../20261105T164404Z` record has no recovery event, as the `Board` was dropped at the skip.
- **Likely the harness's own reset.** Inferred from timing: pytest ran 26.15 s from about 16:44:04. `_mpremote`'s 10 s limit, then `_interrupt_after_timeout`'s Ctrl-C and `mpremote reset` (15 s limit), lands at 16:44:30. So the question is why `exec` took over 10 s, when it normally takes 0.4 s.
- **Repeat, one try:** 3 load runs, 57 s idle, the same `exec`: 0.38 s, rc 0. The board reset 8 s later (the watchdog, as the product was stopped) and reads `ResetReason` 21. That session had no 500s, so it wasn't quite the same state.

**FRAM holds test data now.** `SYSTEM` reads counter 18 with `E125`/`E126`, the test band that 4b's erase scripts write. I did not trace which run left them. Treat those as test data in step 5's record. Nothing cleared.

## 15. Final 4a on `b7533307`'s tree (17:17-20:24 UTC, no board contact)

Settings: `PER_FILE_TIMEOUT_S=900`, accepted by the lead at 17:34 UTC as the hang backstop, with no test's own bound changed; Node 24.22.2; no device mask. Recorded commits `dad8d551` and `2fa16c9d`, which differ from `b7533307` only under `audit/`. `bd67db94` came later, so nothing here ran with its 512 B ring. The runner stops at the first failing stage, so I ran `npm test` and the twins by hand after the GC stage failed.

| Stage | Result | Seconds |
|---|---|---|
| `scripts/test.sh` (-1) | pass: 137 of 137 files, 5,844 tests, `tests_scripts` 6,890 | 3,502 with the GC stage |
| `GC_THRESHOLD=32768 scripts/test.sh` | **fail**: 136 of 137 files, 5,843 tests | same |
| `npm test` | pass | 900 |
| twin `dev` | pass | 1,509 |
| twin `wozi` | pass | 1,278 |
| twin `arzi` | **fail**: 571 checks passed, 3 failed | 1,288 |
| twin `grkizi` | pass: 574 checks | 1,272 |
| twin `klkizi` | pass: 574 checks | 1,235 |
| twin `schlafzi` | not started: could not end by 20:52 | - |

**GC stage's one failure.** `scenarios[dev]`, `failed_config_snapshot_is_sent_as_unavailable`: "SCD30: 1 GET(s) sent the marker and the verify took 0 of 2 faults (38.6s)". Alone at load 0.7 it passes 3 of 3 in 19.7 s. The failed run shared the Pi with parallel scenarios and my board probes, load about 8. That points to load, but where the second fault went was not traced, so it stays a failure.

**`arzi`'s three failures:**
- `[gc.threshold=-1]` Run 4: largest feed gap 6,795 ms, above 75 % of the 8,000 ms watchdog timeout.
- `[gc.threshold=32768]` Run 11: largest feed gap 6,290 ms, same check.
- `[gc.threshold=32768]` Run 11: 1 HTTP failure in 1,260 soak requests, "warmup: GET /sensors -> TimeoutError('timed out')".

In these two runs the other stage and the other devices read 2,002-2,077 ms, except `klkizi`'s Run 11 at -1 with 3,013 ms, which passes. `would_have_triggered_count` was 0, and neither log has a memory marker. The kernel log is empty for 19:20-19:45. Cause not known: nothing here separates a host stall from one specific to `arzi`. The same twin passed on `b6a7bc1e`.

**Kept in** `logs/final_4a_20261105/` (git-ignored): the stage output, the first 4a log and the two `arzi` run logs, since a rerun overwrites `digital_twin_ci_logs/`.

**Where the bench stopped (owner, 2026-11-05: "When that current run has finished, pause for today.").** The board still runs `b7533307`, idle; `/status` answered 200 at 20:26 UTC. `bd67db94`, `a4ed871a` and `db6442b5` are pulled, and no image with them is built or flashed. Nothing was cleared. Day 2, per `bd67db94`: the new image, step 3, 4b, the `/status` load check, then `run 5`. Then `schlafzi` and the `arzi` rerun.

## 16. Day 2: the 512 B ring's image, step 3, 4b and the `/status` load check (2026-11-06, 06:11-07:03 UTC)

The owner, 2026-11-06: "You can run for 15 hours now". Image `c8887b35`, which carries `bd67db94`; record `dirty: False`. The logs the lead asked for are in `logs_final_4a/` (`c8887b35`). The Pi and the board rebooted at 06:07, before this session started; I did not cause it.

**Step 3: pass.** Flashed and checked in 260 s, `board_BuildDate` matching the record. `a4ed871a`'s kick and 720 s wait held.

**The `/status` load check: no failure in 331 reads.** `repro_status_load.py base 3 60 /status`, no flash write, nothing cleared.

| Boot path | Runs | 200 | 500 | Lowest `MemFree` | `UARTLINK` `Failures` at the end |
|---|---|---|---|---|---|
| Direct join after 4b, uptime 97 s on | 3 | 165 | 0 | 22,320 B | 1, 1, 2 |
| Through the 8-minute hotspot, uptime 560 s on | 3 | 166 | 0 | 21,280 B | 3, 3, 3 |

Yesterday: 5 of 308 failed through the hotspot and 0 of 156 on a direct join, with `MemFree` as low as 4,544 B. The console logged no memory line in any of the six runs, and `WEBSERVER`'s counter stayed 0. Six runs are a small sample against a 1.6 % failure rate, so `run 5` is the larger check. The hotspot boot came from `machine.reset()` with no kick (reason 21); the board rejoined after 8 min 17 s.

**4b: 11 failed, 75 passed, 4 skipped, 17 deselected, 1 teardown error, no memory line (1,393 s).**

| Tests | Day 1 | Day 2 | Reading | Status |
|---|---|---|---|---|
| Held SDA, BMP3xx alone, FRAM erase (3 tests) | failed | pass | `db6442b5`'s test-side fixes work | Measured |
| 4 twin conformance | failed | failed, same divergences | Round 2 (lead, 2026-11-05) | Unchanged |
| `test_real_gc_heap_headroom…` | 128,576 B used, 59,568 B free | 113,216 B used, 74,928 B free | 15,360 B back, as the ring predicts. Free is now above Part N's 68,790 B demand and 72,232 B budget. Still over the test's 100,000 B bound | Measured |
| `test_routine_no_yield…`, `test_c_stack_peak…` | 41,345 us, 4,020 B | 41,356 us, 4,020 B | Unchanged | Measured |
| `test_the_link_keeps…[crc16]` | 9 transfers | 9 transfers | Item 10 | Unchanged |
| `test_reboot_falls_back…` teardown | error | error | See below | Cause read in the code |
| **New:** `test_get_and_set…[none]`, `[cobs]` | pass | largest block 111,568 to 112,336 and 108,624 to 109,504 | See below | Inferred |
| **New:** `test_no_frame_is_lost…[crc16]` | pass | 2 of 22 frames intact in the 3 ms window, 1 overrun, `uartrsr_oe` false | See below | Inferred |

- **`test_no_frame_is_lost…[crc16]`: the 512 B ring against a continuous sender at CRC16's cost; no sign of a lost frame on the real link.** The script's own comment puts CRC16 at about 21 ms per frame on silicon, and a 55 B frame takes 4.8 ms on the wire. So `_drain` empties about 2.6 B/ms while the stream adds 11.5 B/ms, and 512 B fills in about 57 ms, at the start of the 3 ms window (stream margin 50 ms). The window isn't the cause. `[none]` passes all windows on the same ring, and every frame after the resync arrives intact. Computed, not measured. It's the same case `bd67db94` ruled out of sizing (a continuous sender, not the stop-and-wait peer), which the 8,192 B ring hid. The test needs a slower stream or an unchecked read under CRC16; that's the lead's to choose.
- **`test_get_and_set…[none]`, `[cobs]`: the check reads for exact equality and the block grew.** The refused train allocated nothing that stayed: the block grew by 768 and 880 B. `largest_block()` is a search by allocation, so a collection inside it can free garbage next to the largest block, and that this now matters fits the new layout. Inferred; `[crc16]` passes. Either `after >= before`, or a collected baseline before both reads, would fit the test's "nothing allocated".
- **The teardown error is the test order.** `closing_reset` hard-resets and waits only for USB, then the session's teardown (`tests_hardware/conftest.py:494`) makes one strict `GET /status` while the board is still booting. The exception also skips what follows it: the SCD30 snapshot at the end, the board-state check and the session-end FRAM dump. So **4b's session-end checks have not run on either day**. Read in the code; fails the same way on both days.

**FRAM.** 4b's erase tests blanked the chip again, so yesterday's history is gone from it, as a test-owned erase. The `/status` read before the flash is in `logs/day2_20261106/status_before_new_image.json` (git-ignored). Nothing was cleared by hand.

**Next (agent, 2026-11-06):** `run 5` on this image, then twins `arzi`, `schlafzi`, `dev`.

## 17. `run 5` on the 512 B image: a cascade, its cause, and the rerun (2026-11-06, 07:03-)

**First run, 07:03-07:32, 1,740 s: 7 failed, 13 passed, 84 errored in setup, 6 in teardown.** No memory line. The archive is `build/archive/run_bench_hardware_suite/20261106T070339Z`.

**The cascade's cause, found in the harness.** `test_fram_erase_under_api_load` failed with `the board did not leave USB within 60.0s`, but the kernel log shows it did: USB disconnect at 07:11:38.040, `ttyACM0` back at 07:11:38.360. `kick_after_reset()` polls the node every 500 ms (`_USB_GRACE_POLL_S`) and the gap is about 320 ms, so it misses roughly 1 reset in 3. Five gaps read 300-340 ms. With no kick, the AP's stale entry lasted to 07:13:10, the board went to its hotspot, and the tests after it failed in setup until a later reset at 07:16:01. This is `a4ed871a`'s own check; item 2's cascade had a different start.

**Fix (agent, 2026-11-06, decided on the lead's behalf, since the rerun can't run without it; the lead can revert it):** `kick_after_reset()` polls at 62.5 ms, in `tests_hardware/harness.py`. `tests_scripts/test_bench_harness_helpers.py` gets a test with a real gap's timing, which fails at the 500 ms step. Those two test files pass, with ruff and mypy clean on both changed files. The full `tests_scripts` was not run. No image change; the image stays `c8887b35`.

**The rerun:** the 78 test functions that errored in setup, plus `test_fram_erase_under_api_load`, through `PYTEST_K`. Tests that already ran aren't repeated, as a cascade's tests never spent their writes. The selection is in `logs/day2_20261106/rerun_5_k.txt`.

**The rerun, 07:36-08:49 on `c8887b35`, 4,352 s: 46 passed cleanly, 29 failed, 9 passed with a teardown error, 1 skipped.** No memory line. The cascade did not recur. Archive `20261106T073632Z`. Triage sent to the lead at 09:20 UTC, with each cause marked as read in the code, inferred or not traced:

| Group | Tests | Reading | Status |
|---|---|---|---|
| Missing kick | 15 in `test_reset_reasons.py` | `run_isolated_expect_reset` has no kick, so the 90 s wait ran into the stale entry | Read in the code and the AP log; fixed by the lead, `1f844c03`; rerun below |
| Teardown log check | 7 of 9 errors | SGP40 `W65`, with `W35` or `NTP E71` on two of them; fits a boot after an erase with no backup chunk yet | Inferred |
| Possibly product | Loop lag 967,405 us (bound 925,000); OpenHAB case, 7 cut bodies; sweep at -1, 13 resets; mixed bodies, 2 resets; three packet-fault tests | Not diagnosed. `WEBSERVER` held 23 entries at session end | Open |
| Likely test-side or downstream | Unknown sensor key (lead's fix `2745af2f`), oversized body's `MemFree`, hotspot `W61`, spoofed capture, `test_ntp_recovers` and the three after it | Not traced | Open |

**A wasted flash (agent, 2026-11-06).** The 08:51 pull failed, as my 08:50 hand-back had diverged from `a0503ca5`, and my command didn't stop on it. So step 3 at 08:52 flashed `92bcc381`, the same firmware as `c8887b35`, and the flash tests at 08:58 ran the old tests; their archive `20261106T085830Z` isn't a result. Corrected by merge `d3f10239` and a third flash. Flash cycles today: 3, where 2 would have done. Later pulls stop on failure, and merge commits carry `[skip ci]` (lead, 2026-11-06).

**On the final image `d3f10239` (heater-off wait in, `dirty: False`, 09:05 UTC):**

- **Flash, the lead's list:** `no_frame_is_lost`, `multi_chunk_train`, `watchdog_starvation`, `held_sda_line_through`: 9 of 9 passed, no memory line, session-end checks ran.
- **`test_a_damaged_config_file_is_repaired…`: passed, `ConfigFaults ['SYSTEM']`, one owned write and its repair.** Run once at the lead's request, with no `cleared:` line in `WEAR.txt`; not to be repeated. Its session-end wait timed out after 90 s ("DUT serving ... before the session-end GET"), so the session-end checks did not run there. Not traced; a hard reset with no kick would fit it.
- **Bench, the lead's list (09:18-09:32, 4 failed, 4 passed, 3 teardown errors):**
  - Passed: `mempause_over_real_rest`, `reset_errors_after_an_accepted_reboot`, `c_stack…[reboot]` (reason 20, teardown error below), `real_ntp_handles_a_genuinely_unreachable_server` (signatures 3287644897 and 1931067590, teardown `W35`/`W33`).
  - `test_bus_triggers_keep_their_minimum_spacing`: `ISL29125` and `SGP40` on `i2c1` triggered 470 ms apart, against a planned 500 ms.
  - `test_a_c_stack_exhaustion_is_attributed[entry_held]`: `ResetReason` 11, not 20; watchdog bits 1.
  - `c_stack…[reboot]` teardown: `FRAM E46 FRAM_STATUS_BYTE`, `FRAM W63 FRAM_BLOCK_INVALID`, `NTP E71`. FRAM errors under the deliberate stack exhaustion; not traced.
  - `test_webserver_answers_before_the_first_ntp_sync_completes`: first 200 at 12.47 s, RTC set at 10.60 s; 12.42 and 10.22 s on the first run.
  - `test_real_ntp_sync_succeeds…`: no `RTC set to:` line in 62 s, `NTPSynced` true, age 68 s. So it synced before the watched window; second time.

Not repeated on `d3f10239`: the rest of `run 5`. The firmware differs from `c8887b35` only by `src/asy_sgp40_driver.py`'s 1 ms wait.

## 18. Day 2 on `d3f10239`: the rest of `run 5`, twins, runs 9 and 10, the lag and the baseline (2026-11-06, to 13:03 UTC)

Logs: `logs/day2_20261106/` (git-ignored). All read from those logs; causes marked inferred are not traced.

**`5d`, the rest of `run 5` (`5d_day2.log`): 4 failed, 14 passed, 11 errors.** Failed: `test_put_nonsense_field_values…`, `test_an_incomplete_command…`, `c_stack…[entry_held]`, `test_a_console_interrupt…`. The errors I read are teardowns on `SGP40 W65 SGP_NO_BACKUP`, an entry not in those tests' `provokes_log`; with the lead as test fixes.

**Twins on `c1f8076b`, Pi quiet:** `arzi` 574 OK, 0 FAIL, feed gap 2,241 ms. `schlafzi` 574, 0, 2,126 ms. `dev` 688, 0, 2,183 ms. All PASS.

**Run `9 10m`, 11:04-11:58, rc 1 in all three steps; no memory line in any summary.**
- `9`: `crc16_hazards` passed; teardown error, the session-end wait timed out at 90 s, "No route to host".
- `10a`, `10m`: the 3 bench tests errored at setup, `URLError timed out` at `bench/conftest.py:86` `check_image`. So the soak's bench half did not run. Inferred: flash runs first in that session, its no-kick resets send the board to its hotspot, and `check_image` fetches once.
- Flash half: `10a` 3 of 3 passed. `10m`: 2 passed; `test_single_core_timing_headroom…` failed, one reboot right at its window's start, about 30 s after its own `hard_reset`. Reason not recorded (the later read shows 21). Most of that 600 s window was in hotspot mode.

**Bench half alone, with `soak()` bypassed (`PYTEST_K` does not reach it):**
- Short, 12:01-12:06 (archive `20261106T120101Z`): 3 passed.
- Mid, 12:06-12:38 (`20261106T120602Z`): `test_http_soak_stays_live` 0 of 860 failed. `test_scd30_frc_readiness_baseline` 257 samples, 0 missed. `test_real_hardware_survives_extended…` failed with `UART_init` and `UART_resp` `E81 UART_NO_ACK`, counter 2 each, and no reboot or task end. Lead's reading (2026-11-06): the `/status` stall below crossing the 1,000 ms ACK wait, not a new defect. Not rerun until the stall's source is known.

**FRAM cleared by those tests.** The short run was the first today to reach their `reset_all_error_logs`. Saved first: `errcount_before_first_soak_clear_20261106T1201.json`. `SYSTEM` `E42` and `E25` in it come from `test_a_c_stack_exhaustion_is_attributed`, whose `provokes_log` names both. No unprovoked one in any snapshot of 11-05 or 11-06. Compare against each archive's own `errcount-session-start.json` from here on.

**Single-core soak, mid, alone, 12:50-13:03 (`20261106T125007Z`):** the test passed, no reboot. So the `10m` reboot is 1 of 2. Teardown error: the same 90 s session-end wait. Board on its hotspot afterwards.

**Loop lag, `lag_two.sh`, 3 readers for 60 s, `gc.threshold(32768)`, Pi quiet, no flash write (`lag_3readers_{status,measurements}.console`):**

| Window | `/status` (51 answered 200) | `/measurements` (307 answered 200) |
|---|---|---|
| Boot | max 77 ms | max 76 ms |
| Idle | max 78 ms | max 93 ms |
| Load | max 2,481 ms, 16 at 925 ms or more, 6 at 500-925 | max 318 ms, 0 at 500 or more |
| After | max 54 ms | max 85 ms |

- Under `/status`, a stall about every 3.5 s, about 2.4 s long. In it the console shows three `CFGMGR_NTP … Reading config data into list` lines 0.7-0.85 s apart and no other module's lines. The read that prints that line is a dict lookup (`asy_config_manager.py:363-366`), so the time goes elsewhere. Source not traced.
- Same window: `UART_init` and `UART_resp` `no ACK for frame 1`, two pairs (12:40:49/50, 12:41:26), with resyncs. None under `/measurements`.

**Post-boot free heap, 32768, idle, no readers, after `gc.collect()` (`baseline_idle_{1,2}.console`), STA up:**

| Sample | Free | Used | Max free block (`mem_info`) | Runs |
|---|---|---|---|---|
| 1 | 72,288 B | 115,616 B | 3,162 blocks, 50,592 B | 134 |
| 2 | 73,072 B | 114,832 B | 3,276 blocks, 52,416 B | 133 |

Under `mpremote run` with the probe's wrappers, so a little below a plain boot; how much was not measured. Section 8's `heapmap.py` undercount is fixed.

**Next:** run 11, then the lead's push.

## 19. Day 2 on `ec5d656e`'s harness: the soak selection, step 9 and run 11 (2026-11-06, 13:10-16:18 UTC)

Image still `d3f10239`, no reflash. Merge `df8e640c`.

**Soak selection, `--duration mid`, 13:26-14:09, archive `20261106T132607Z`, rc 1:**
- Passed: `real_clock_stretch`, `single_core_timing_headroom`, `sgp40_sample_cadence` (602 cycles, 0 lost, max gap 1,877 ms, 2 gaps over 1,500 ms), `http_soak_stays_live` (0 of 854 failed over 600 s). The bench half now runs after the flash half.
- One teardown error on `http_soak_stays_live`: `SGP40 W33 SGP_RESTORED_NO_TS`. Lead, 14:21: a harness race. The sgp40 script writes undated backups (`W35`) into production's chunk, the next boot restores one (`W33`) after the fixture's opening read. To be fixed in the harness; no tolerance added.
- `ResetReason` at the bench half's opening read was 2. The pin is owed after items 4 and 5.

**Step 9, `crc16` hazards, 14:10:59-14:13:19, archive `20261106T141100Z`:** passed, no session-end teardown error.

**Run 11, `FRAM_HOURS=2`, 14:13:59-16:16:45:** 13 slices, all `rc=0`, `scratch_restored=1`.

| Op | n | OSErrors | Bad | Worst |
|---|---|---|---|---|
| `rdid` | 3,429,131 | 0 | 0 | 7,387 us |
| `read256` | 3,429,131 | 0 | 0 | 7,728 us |
| `write1` | 3,429,131 | 0 | 0 | 11,029 us |

- With the stopped slice of 13:10-13:20 the runner's summary sums 14 runs, n=3,703,418 each, upper bound `bad_rate<8.1e-07`.
- Worst `rdid` is bimodal by slice: 1,298-1,335 us in 6 of 13 slices, 7,314-7,387 us in the other 7. Cause not traced.
- `/status` 000 at 16:16:52. `long_fram.py` arms `WDT(timeout=8000)` and feeds it only inside its loop. Inferred, not proven: the watchdog resets the board about 8 s after the last slice, unkicked, and the AP's stale entry sends it to the hotspot, which fits `WIFI W38,W79` and `SGP40 W35,W33` at 16:17. The boot's `ResetReason` was not read before the next reset.
- `fram()` now ends on `reset_and_kick.py` (harness `reset_board`, lead 14:21), straight after the last slice. Run by hand after this run: `/status` 200 after 11.7 s, Mode STA, `ResetReason` 21 (an interrupted running `main.py`, on the reading above).

**Item 4, the new board tests, zero wear:**
- Flash, 16:18-16:22 (`20261106T161838Z`): 6 passed (`held_sda_line_through` x2, `emptied_alarm_pool`, `fault_inside_the_running_graph` x2, `stepped_clock_under_the_running_graph`).
- Bench, 16:23-16:27 (`20261106T162301Z`): 3 passed; `counted_once_in_http_dropped` failed, `HTTPDropped 0 -> 4 after 3 refusal(s)`. Lead, 16:54: the serving probe's race, fixed in the test on the new tree.
- `config_flush_during_link_traffic` not run: no `cleared:` line in `WEAR.txt`.

**Item 5, the test-side fixes, bench only, 16:28-17:02 (`20261106T162825Z`), 22 passed, 2 failed, 4 errors:**

| Test | Result | Reading |
|---|---|---|
| `loop_lag_under_http_load` | Failed: 1,006,799 us against 925,000 us, at 16,583 ms after `main()` started, p99 64,000 us, 1,028 samples, 183 FRAM writes, 0 failures | A measurement until the stall is fixed. Teardown also `WEBSERVER W51 HTTP_SOCKET_ERROR` |
| `concurrent_mixed_body_sizes` | Failed: `HTTPDropped` 11, 24 refusals seen | Not traced |
| `dns_server_sends_garbage`, `connected_socket_rejects` | Passed, teardown error `SGP40 W35, W33` each | Not traced |
| `serving_sweep` | Passed, 0 allocation failures, `N=8` 72 answered, 24 refused; lowest load sample free 368 B, largest run 320 B. Next test's setup error: `UART_init`, `UART_resp` `E81` | `E81` matches the `/status` stall's window (section 18), not proven here |
| `fram_erase_over_rest` | Did not run: that setup error | Owed |
| `heap_at_peak` | Passed: 102 of 146 samples at the ceiling of 6; after boot free 40,784 B, largest run 28,992 B; at peak largest run 21,552 B, 10 slots | Script console: `EHOSTUNREACH` reclaim twice |

**`ResetReason` 2, pinned on `d3f10239`, 17:03-17:06 (`logs/day2_20261106/rr_pin.out`), no config writes:**

| Case | `ResetReason` | Watchdog REASON bits |
|---|---|---|
| a. Running board, harness hard reset | 21 | FORCE |
| b. One `exec "pass"`, then the hard reset | 21 | FORCE |
| c. One read-only script (`fram_raw_dump.py`), then the hard reset | 21 | FORCE |
| d. `begin_boot()` once, phase mark cleared, then the hard reset | 2 | FORCE |

`main.py`'s Ctrl-C writes record 21, and it survives a stop and a soft reset. `build_system()` calls `begin_boot()`, which consumes the record, and those scripts clear the phase mark, so the next `machine.reset()` finds neither and falls through to `_RR_WATCHDOG`. So 2 after such a script is a harness reset, not an expired watchdog. The boot at 13:58 itself was not read for its bits. Case d stands in for a `build_system()` script, as those write scratch config.

## 20. The new image and the `/status` stall's source (2026-11-06, 17:08- UTC)

**Reflash, owner's OK, 17:08:23-17:12:26:** built from `9c0699e4` (the lead's `ae1d292a` merged), `BuildDate` 2026-11-06T17:08:25Z, `match=1`, `/uart` answers 200. Flash cycles today: 4.

**`/status` timing, `heap_probe/status_timing.py`, 3 readers for 60 s, 32768, under `mpremote run`, no flash write (`logs/day2_20261106/status_timing_1.console`):** 51 answered 200, 0 memory failures.

| Span | Mean | Max |
|---|---|---|
| Whole build | 739 ms (min 703) | 786 ms |
| `errcount`, 22 sources | 640 ms, 29 ms each | 56 ms for one |
| `system` | 41 ms | 70 ms |
| `networking` | 14.5 ms | 37 ms |
| `notification`, `SGP40`, `UARTLINK`, `UART_init` | 1-2.5 ms each | 27 ms |
| `GET /status` less the build (the lock wait) | 3 ms | |
| Send, 32 pieces | 1,052 ms | 1,412 ms |

Timed `gc.collect()`: idle 19.3 ms x3, free 71,328 B; after load 21.0 ms x3, free 62,384 B. So collection is not the stall.

**Loop lag of 200 ms or more, same run: 27 events, 39.4 s of the 58.3 s between the first and last, against 37.7 s of builds.** They fall in three groups: 747-852 ms, 1,507-1,610 ms and 2,267-2,313 ms, one, two and three builds. 24 of the 27 match the builds ending inside them to within 16-134 ms; the other 3 only count a neighbouring build at the window's edge. A lag task sleeping 10 ms cannot run while they last, so the builds do not yield to it (inferred from that, not traced in the scheduler), and up to three readers' builds run back to back.

So the stall is the `/status` build's CPU time, mostly `errcount`, held without a yield and multiplied by concurrent readers. 2.3 s exceeds the 1,000 ms UART ACK wait and the 925 ms hard consumer, which fits `E81` and `loop_lag_under_http_load`. A fix is not this runner's to choose.

**Lead's reruns on the new image:**
- Flash, 17:17-17:20 (`20261106T171720Z`): 4 passed. `one_supervisor_pass`: 2,316 ms between feeds, reset 4,002 ms after the last feed. `fault_inside_the_running_graph`: `ResetReason` 2, REASON bits TIMER, both arms, so 2 also covers a real expiry; the bits tell the two apart.
- Bench, 17:20-17:36 (`20261106T172040Z`, on `b7c5dea8`, before the lead's `318ba804`, which arrived during it; Node v24.22.2): 8 passed, 2 failed, 2 errors.
  - Passed: `counted_once_in_http_dropped`, head guard (Chromium 13 lines, 632 B, against 32 lines, 2,048 B), harness hard reset (21, FORCE), `c_stack` x3 (20; FORCE, TIMER, TIMER), radio re-init (link back in 8,216 ms), `real_sta_connect` (call).
  - `answers_before_the_first_ntp_sync` failed on `SYSTEM E115`, the flash line's own injection still in the log at session start. Passed on rerun.
  - `hazard_run_under_the_readers_load` failed: 13 API issues, `GET /status` reset before any response byte, 3 readers; teardown `WEBSERVER W60 HTTP_REFUSED`. Fits refusals at the ceiling while builds stall (inferred).
  - `real_sta_connect` teardown: `FRAM E51 FRAM_COPIES_DIFFER`. The source's comment names a write torn between blocks; a hard reset can do that, and the next write heals it. Inferred.
- Bench rerun, 17:37-17:43 (`20261106T173735Z`, on `4d90a869`): 3 passed. `answers_before_first_ntp`; `concurrent_mixed_body_sizes` (28 answered, 20 refused, 10 of them over the cap, 0 wrong); `fram_erase_over_rest` (serving 32.9 s after the reply, `ResetReason` 8).

**Owed archive fact, `SGP40 W35,W33` after the DNS and NTP tests (`20261106T162825Z`):** yes, the board booted inside each. DNS: uptime 100 s to 93 s, `UTCTime` null at both reads. `connected_socket_rejects`: uptime 130 s to 70 s. A boot with no NTP writes and restores undated backups.

**`SGP40 W65` read at 17:12:** already in item 5's session-end read at 17:02 (counter 2), so before the reflash. That session's `erase_reboot_and_mempause` erased FRAM. The flash log between 17:08 and 17:12 shows no FRAM step.
