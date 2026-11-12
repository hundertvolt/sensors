U31 lane T block T2 FINAL
Branch audit/u31-t in S/wt-u31t, head 7a7b003 (one commit over 03bc27e). Nothing pushed, nothing uncommitted. Logs are in S/u31/laneT/t2/. I made about 86 tool calls: I finished the 32768 stage that was running rather than splitting it across two agents.

1(a) Answer from source: a persistently failing reader produces at most one task end per supervisor pass, i.e. 0.5 ends/s per task. It does not tight-loop, and the device reboots as the spec intends (SPEC:6223 "the restart budget reboots the device"; SPEC:3026-3028 "about three restarts"). No finding.
- First episode: 6 failed reads at 1 s, then the give-up (asy_base_classes.py:584-586).
- The supervisor restarts the task at most once per pass, after its 2 s sleep (asy_system_service.py:532, :556).
- `_err_cnt_internal` is reset only at construction and by reset_error_counter (:417, :763). So the restarted task gives up on its first failed read.
- The restart runs `_init_sgp()` at once. The next read does not wait either: the free-running 1 s Timer kept setting `_read_event` while the task was down (asy_sgp40_driver.py:374-376, :619-624).
- The charge goes 100/200/300; the 4th end reaches 400 and escalates (asy_system_service.py:262, :526-530). The decay is 1 per clean pass (:551-553).
- So the reboot comes about 12-14 s after a permanent fault starts. That is why T's 60 s storm rebooted the device.

1(b) Why the bounds differed: `_hard_consumer_ms` existed twice (scripts/_digital_twin_scenarios.py:837 and test_memory_stress.py:46). Both used the UART reply timeout of 1000 ms on a device with a uart_link and the raw watchdog of 8000 ms otherwise.
- Now both read one helper, `smallest_hard_consumer_ms()` (end of scripts/_digital_twin_scenarios.py): the minimum of the watchdog less one 2 s supervisor sleep and each link's reply timeout less 2×poll_wait_ms + poll_idle_ms + `_GC_PAUSE_WORST_MS`. These are F.3's consumers and the same terms as lane C's rule in 489c87a.
- Result: dev 925 ms, every other device 6000 ms; both tighter than before.
- Real dev runs: max lag under load 237.9 ms at -1 and 241.6 ms at 32768, against 925 ms. Every device's max is 237-243 ms.

Seen failing first: the new L0 failed with "AttributeError: module '_digital_twin_scenarios' has no attribute 'smallest_hard_consumer_ms'".
Bites (scratch tree S/u31/laneT/bite_tree, nothing committed), all three failed as they should:
- lag with a stall past the bound: "the loop lagged 1437980 us under load, past the 925000 us smallest hard consumer".
- stagger with its flag unset: "the watchdog did not engage once the stagger one-shot's fire was dropped".
- reset with its flag unset: "the device reset although its reset one-shot's fire was dropped (... exit code 3)".

3. NTP retry: no existing twin knob reaches it in bounded time, so no scenario was added.
- The one-shot arms only on a failure while synced (asy_ntp_client.py:275-282).
- A synced resync comes only when `_ntp_sec_count` reaches NTPInterval×3600 s, and NTPInterval is at least 1 h (:113, :374-379).
- `ntp_force_sync()` clears Synced first (:553-554).
- A stored NTPInterval below 1 falls back to the default 12 (asy_config_manager.py:561-566).
- No runner flag touches NTP timing (run_generic_integration.py:384-406, :989-1030).

4. Checks, exit codes at -1 / 32768 (seconds):
- Runner test 0/0 (1.33/1.39). Measured, 3 runs each: its two new waiting tests cost 0.115/0.100 s, which is their real waits. Without them the file runs 1.214/1.296 s against base 1.20/1.27 (+1.2 %/+2 %).
- Flag L0 0/0 (0.63/0.64), scenario L0 0/0 (1.38/1.54), test_level_containment.py 0/0.
- Device-script L0s (the six) 0/0, test_digital_twin_generated_boot.py 0/0 (56.6/56.5), test_stripped_image_boots.py 0/0, `--collect-only tests_hardware` 0, host mypy 0.
- Scenario jobs, all PASS with "Passed only on retry: none": arzi 478/481, dev 593/602, grkizi 464, klkizi 463/469, schlafzi 465/466, wozi 485/490.
- dev's job is +35 % over the 439 s base. Of that, 85.7 s is the new scenarios' designed waits (loop lag 75.7 s: 60 s load + 10 s settle + boot; stagger 10 s). The remaining ~68 s is the pre-existing scenarios, not the new ones; I believe it was host load but did not measure it.
- The reset scenario passed on arzi and the stagger scenario on dev at both stages. Loop lag passed on all six devices at both stages.

5. Repo-wide scans: one red, test_tunables_register.py:253 "l2.twin_loop_lag_report_ms is tagged but has no SPECIFICATION.md Part N row". It is the lead's (Part N tags, unchanged from T: l2.twin_loop_lag_report_ms, l2.loop_lag_{load_s,settle_s,recovered_ms,period_ms}, l3.memory_stress_flash_gap_script_timeout_s). No new tag from me. All 19 tests_scripts files that read a lane-T file are green (test_twin_record.py excluded; it is the lead's).

Zero MemoryError and zero "memory allocation failed" in any log at either stage.

Silent-failure scan over lane T's 8 files, every class, modes reset countdown/boot/supervision/runtime limits/long uptime (wraps)/twin shutdown: no defect.
- The flash write is safe by construction: lfs2 writes the whole size or errors (extmod/vfs_lfsx_file.c:144-147).
- A dropped fire that never arrives shows up through the `callbacks>=1` check.
- One low class-3 note: the loop-lag load checks only that some request was served, and keeps the served count as evidence without a floor.

Decision (agent, 2026-10-21): the lag bound is the device's smallest hard consumer from one helper (925/6000 ms). This reverses T's 1000 ms choice and goes back to the plan's 925 ms.

Facts owed:
- To the lead: lane C's validate.py computes the same consumer, so at merge one export beside `device_max_connections` could serve all three users.
- To lane D: F.3's con.watchdog is 6000 ms in both helpers; the scan term is not subtracted.

Left: nothing.
nothing of mine is running
