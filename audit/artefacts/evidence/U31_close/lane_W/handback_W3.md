U31 lane W block W3 FINAL
Branch audit/u31-w, head ab959c1 (from a31c4da). Worktree S/wt-u31w. Nothing pushed, nothing uncommitted. rebuild.sh rc 0 at a31c4da and at 86d00c9.
Commits:
- 86d00c9: src/asy_webserver_service.py. `_TimeoutStreamProxy` takes `timeout_ms: int`. `__init__` converts once with `round(serving.per_call_timeout_s * 1000)` and `round(serving.outer_cap_s * 1000)`. All 4 `wait_for` sites (the proxy's two, `_close_writer`, the outer one in `_serve`) are now `asyncio.wait_for_ms`, so none is left for lane C's guard. Tests: `_VirtualClock` gains `sleep_ms` and `wait_for_ms` and records the bounds; `_DrivenClock.wait_for_ms`; `_ASYNCIO_NAMES` swaps `wait_for` for `wait_for_ms`; the proxy sites take 50/1000 and the `_ms` attributes 2000/4000; new test_every_bound_is_asked_in_whole_milliseconds.
- ab959c1: tests/test_digital_twin_sensortask_integration.py. `_WIFI_STEP_MS = src_int(..."_STA_CONNECT_POLL_MS")`. `_radio_rung_bound_s` sums in ms and returns seconds. `_SteppedWifiAsyncio` now caps `sleep_ms` too, and `sleep()` converts as core.sleep does. `src_float` import dropped.
Steps:
- Step 17 (.118, .119, .126, .127): ms parts applied. Everything else was already in place: head parser, flags, hold/release, namedtuples, drop window, both close failures persisted.
- Step 38: ms parts applied; the builder objects, `sock=` and the `src_int` defaults were already in place.
- Step 59: check only. The twin WDT-0 hold (`would_have_triggered_count == 0`) passes on all 6 devices at both stages.
Seen failing:
- Before the src change, the new test failed at test_asy_webserver_service.py:2616 with `AssertionError: []` (10 tests red in all).
- Before its fix, the twin file failed at import on wozi: `KeyError: _STA_CONNECT_POLL_S is not a const()`. Bites: none (no guards).
Checks, all rc 0 at -1 and at 32768, zero MemoryError / "memory allocation failed" in every log:
- MicroPython files: webserver_service 220/220, webserver_connections 24/24, twin integration ×6 devices, wifi_service 268, udp_socket 70, captive_dns 64, neopixel_wifi 8, dns_client 46, ntp_client 188, ntp_wifi_dns 13, setter_microdot 34, website_build 7, twin wifi_modes 1.
- pytest: 34 readers 2572 passed (request_timeout_ceiling and buildgen_generate among them); `--collect-only tests_hardware` 196/226 collected.
- mypy main, src/tests/device_scripts, twin and host passes clean; ruff clean on the 8 scopes.
- Red, waiting on the lead (R-24): 17 scans 868 passed, 1 failed, test_tunables_register::test_the_tags_and_the_part_n_rows_agree. Its lines are exactly W1's 9 and W2's 3 (e.g. "src/asy_udp_socket.py:30: udp.retry_backoff_ms is tagged but has no SPECIFICATION.md Part N row"); none of them are mine. test_twin_record not run (expected red).
Final grep: one hit, tests/test_digital_twin_network_neopixel.py:56 (lane F's file; it is converted on audit/u31-f, 0 hits there). hotspot_role_reversal :439/:573: confirmed gone.
Relay lines I would have written:
- "W3 86d00c9 ab959c1 (webserver bounds via wait_for_ms; twin integration poll read + sleep_ms step)".
- W→D, these still say `asyncio.wait_for()`: SPEC:6196-6198 (F.2), SPEC:7509 ("applied via `asyncio.wait_for()`"), tests_hardware/README.md:1400.
Part N: no tag renamed. web.per_call_timeout_s / web.outer_cap_s keep seconds (R-20).
Times, before (base) → after, -1 / 32768 s:
- Grown files: webserver_service 4.51/7.14 → 4.41/7.30 (+2.2 %); connections 1.21/1.27 → 1.22/1.25.
- Twin integration: arzi 117.68/118.27 → 117.66/118.21; dev 22.79/23.22 → 23.06/23.41; others within ±1 %.
- Not changed by me: wifi_modes 25.77/25.71 → 27.69/27.78 (+8 %), under 10 %.
Effect per mode: STA and AP keep 5000 ms per call and 15000 ms per request, and no longer box a float per stream call. Silent, Off, USB: no change. The twin step is twin-only.
Silent-failure scan, lane W's 12 files, all classes, the modes above plus a task restart: no new finding. A 0 ms bound is impossible by construction: codegen.py:741-742 passes only the src constants.
Decisions (agent, 2026-10-21):
- (1) `round()` as the packet says. It equals `int()` for every shipped and test value; the smallest test value is 0.01 s = 10 ms.
- (2) The test clocks keep virtual seconds and convert ms at their `wait_for_ms` boundary. `wait_for` is dropped from both stand-ins, so a stray seconds wait fails loudly.
- (3) network_neopixel.py:56 left to lane F.
- (4) A test comment now reads "the per-write timeout wrapper" in place of `asyncio.wait_for()`.
Runs: the batch first gated every file; I killed my own pid 17724 before any test had started and relaunched it as pid 20787. All logged in RUNS.md and all exited.
nothing of mine is running
