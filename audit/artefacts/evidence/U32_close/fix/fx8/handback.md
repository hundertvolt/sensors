FX8 hand-back (agent, 2026-10-21). Commit adf5002 on audit/u32-fx8 (S/wt-u32fx8, from c6b8a07, rebuild rc 0). Only tests/test_asy_neopixel_driver.py changed. Nothing pushed, nothing uncommitted.

**Cause: the lead's hypothesis holds, measured.** The scheduler runs tasks in order of their scheduled tick. The scenario's wake is due at s2+200 ms (s2 is about 22.6 ms). The ramp's 10 frame wakes end it at about 103 ms, so the slack is about 118 ms. Once the frame wakes run that late in total, the scenario resumes before the overlay task, and `cancel_all` cuts off the restore. That is the gate's :282 failure.
- **Injected lateness:** 12 ms per frame passes (4.4 ms slack left). 13 ms per frame fails on that same final assertion, at -1 and at 32768 alike. So the GC stage plays no part.
- **Beside the four twins (13:10, load under 1):** 40/40 pass. Slack at least 117.6 ms; total lateness median 3.4/3.7 ms (-1/32768), max 5.3 ms.
- **Beside the gate's coverage leg (14:14, load about 1.9):** 40/40 pass. One 32768 run had a single wake 32.0 ms late and slack down to 86.3 ms.
- **After phase B2's done (14:31):** the host was not idle. Other sessions kept the load at 3.3-4.2. All 40 target runs passed (slack at least 110 ms). But the real-clock `test_request_signal_restores_overlay_on_state_after_ramp` (its slack is only about 47 ms) failed twice at c6b8a07:402, once at each stage.

**Converted to `_DrivenClock`, every assertion kept, each seen failing on a planted driver in S/u32/laneFX8/bite/** (passes on the real driver at both stages):
- The target. "No restore after a ramp" fails :297 (final write). "Overlay ignores the lock" fails :296. Its deferral is now checked at every yield the ramp holds the lock.
- Restore-on-after-ramp: no-restore bite fails :419.
- on, off, toggle off→on, toggle on→off: "writes the previous state" bite fails :198, :214, :229, :246.
- Repeated on: "two writes per wake" bite fails :264.
- Overlay brightness clamp: "no clamp" bite fails :1155.
- led_signal idle, colour pass-through, request/led out-of-range: "peak step dropped" bite fails :538, :610, :1120, :1140.
- Fractional t: "t truncated" bite fails :628.

These 12 had the same hazard (agent, 2026-10-21): the driver's real-time work had to land inside a real sleep, with 47-300 ms of slack.

**Left on the real clock:** ramps_up_then_down, restores_off, two_concurrent, back_to_back, below_floor, low_freq, large_t, external_and_internal, overlay_calls_during_active_ramp, in_memory_variant, infinite_rgb, infinite/nan duration. Each assertion holds however late the wakes come:
- a ramp's first frame is written as soon as the event wakes the task, before any real wait;
- "ends black" is also true on the cancel path, since the ramp's `finally` writes black;
- `request_signal`'s wait has no real bound short of 120 s.

One wrong comment fixed: the 1 Hz ramp takes 2 s, so the 1.5 s wait ends mid-ramp.

**Same shape in other files (facts, not edited):**
- test_notification_neopixel_integration.py:125 (1.3 s wait for a 1.0 s cycle) and :146 (2.5 s for 2.0 s)
- test_notification_scd30_integration.py:135, test_notification_sgp40_integration.py:146, test_notification_scd30_sgp40_integration.py:238 (1.3 s for 1.0 s); test_notification_scd30_sgp40_integration.py:199 (2.6 s, asserting both colours' peak frames)
- test_asy_notification_service.py:1024 (1.3 s for a 1.0 s settle) and :1220 (1.1 s for 1 s of measured time)
- test_ticks_rollover.py:223/229 (a 50 ms sleep, then a 200×5 ms loop for a 10 ms poll)

**Runs (all rc 0 unless noted, zero MemoryError and zero "memory allocation failed" everywhere):**
- File before: 9.70 s at -1, 9.58 s at 32768. After: 7.25 s and 7.29 s, 54/54 each.
- ruff clean. Main mypy pass: no-args 262 files rc 0; `src tests tests_hardware/device_scripts` 228 files rc 0.
- No tests_scripts file names this file. The 17 scans plus the content readers (microtest, exception_handler_contract, port_bands, threshold_runner, test_sh) in one process: 1181 passed. The one warning is the uninitialised datasheets submodule.
- Probes: smoke, load, inject, cov, idle all finished. The two idle-run rc 1 results are the restore-on failures above.
- The 13:34 restart killed only wait_then_idle.sh (pid 3158), before its probe began. Its exit line and the relaunch (pid 2804) are in RUNS.md.

**Effect per mode (STA, AP, Silent, Off, USB):** none. This is a test-only change.

Nothing of mine is running.