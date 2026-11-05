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

## 8. The `MemoryError`: reproduced; root cause not found

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
| 3 readers + `UartHazards`, 150 s | uptime about 20 s | 38 of 109, plus 3 timeouts and 5 resets | 75, `W48` and `W60` among them | not read |

- **Failed sizes:** 242, 250, 251, 252, 253, 254, 255, 256, 257 bytes.
- **Reproduce:** `DUT_IP=<addr> .venv/bin/python repro_status_load.py base 3 60 /status`; add the hazard run with `hazard` in place of `base`. Needs `pyserial` from the venv, and the console must be free. Writes no flash, only `WEBSERVER` log entries to FRAM.
- **Lead (inferred):** those sizes sit just under `_DEFAULT_CHUNK_BYTES = 256` (`src/asy_webserver_service.py:149`), so the failing allocation looks like `_PieceWriter`'s piece join (`:200-219`) during `_build_status_pieces`. The comment at `:150-151` sized that value to the holes a fragmented heap has at -1. A failure at 256 B would mean those holes are now smaller, or the heap is really full.
- **Not known:** one reader's rate, `/measurements` under the same load (both probes returned nothing, item 2), whether the threshold image shows it, and what holds the heap. `MemFree` is read mid-load, so it does not show the state at the failure.
- **Also seen under this load:** `UARTLINK` `Failures` rose by 2-4 per minute, though `test_the_link_stays_healthy_while_the_api_is_hammered` passes, and it hammers something other than `/status`.
- **Why the suite did not see it first:** 5g's `test_serving_heap_at_default_gc.py` tests never ran; they were in the cascade.

## 9. `test_two_concurrent_cancellers_both_return` on the Pi: not root-caused

- **Where:** `tests/test_asy_uart_driver.py:970`: `assert second_result is True`. Full output: `test_asy_uart_driver_20261105T124309Z.log` here.
- **History:** passed in the 12:12 UTC 4a run, failed in the 12:43 UTC run, at 16 parallel files. 164 of the file's 165 tests passed.
- **Not done:** I have no repeat rate, because my repeat runs used a wrong module path. A third 4a is running now and will add one sample.

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
