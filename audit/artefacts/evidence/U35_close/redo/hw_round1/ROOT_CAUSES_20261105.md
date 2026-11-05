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

- **Answer to the question asked at 13:45: placement, driven by load, on both GC settings.** The allocation fails with 12-23 KB free because no run of 16 blocks (16 B each) is left. The threshold does not help: it cuts the idle runs from 384 to 142, but leaves about the same room in runs that can hold a piece: 996 blocks (15.9 KB) at -1, 903 blocks (14.4 KB) at 32768.
- **Mechanism (measured sizes, the sum is my arithmetic).** A `/status` piece of 256 B takes 17 blocks of data plus the 1-block `bytes` object. 7,369 B is about 30 pieces, so about 8.6 KB per held response. Objects of 16-63 blocks grow from 858 blocks at baseline to about 2,040 at failure (-1), and 2,270 (32768): 2.2 to 2.6 responses. So 15 KB of usable runs holds fewer than 2 responses, which fits 1 reader 0 of 42, 2 readers 1 of 46, 3 readers 8-14 of about 46.
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
