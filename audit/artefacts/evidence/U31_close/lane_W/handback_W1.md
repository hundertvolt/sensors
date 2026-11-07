U31 lane W block W1 FINAL
Branch audit/u31-w at 9aadd93, worktree S/wt-u31w, built from aba11d5. It merges audit/u31-api twice: once for <CORE>, then at 75e26ef for <LED> and <NET>. Nothing pushed, nothing uncommitted.
Commits:
- 851a4cb = <NET>, src/asy_wifi_service.py only. The 9 wifi `_MS` constants (comments now read "20 × 500 ms = 10 s" and "10 × 500 ms = 5 s"), sleep_ms at the stations settle and both polls, and `_flash_led`/`_run_led_pattern(on_ms, off_ms)` with `_led_pattern: tuple[int, int]`. Relay line "<NET> 851a4cb" is written under ## W.
- d0a1abd: test_asy_wifi_service.py uses a local `_MsSleep(FastAsyncSleep)` that records only sleep_ms ints. Two new tests pin the stations settle and the connect poll's full bound in ms.
- 3ca4a43: OF-29's WiFi sibling. The `_connect_loop` re-arm passes `quiet=True`, with a new test.
- 7cfde26: test_neopixel_wifi_integration.py. Line 59 now sets `_frame_ms = 10`, and `_FlashSleeps` records sleep_ms in ms (both sleep forms still yield).
- 376d8a9: test_hotspot_role_reversal.py gets a `_connect_poll_s()` helper reading `_STA_CONNECT_POLL_MS`. Value unchanged at 5.0 s; collect-only gives 196/226.
- 9aadd93: D.15 order only (`_MsSleep` before `_src_pattern`).
Steps:
- Applied: step 17's 6 wifi changes (.077, .081, .085, .087, .089, .092), the ms parts of steps 39/40, and OF-29's WiFi sibling. REGISTER:109's client pattern ms form is closed by <NET>.
- Left for W3 (their sites are lane W's, outside W1): test_digital_twin_sensortask_integration.py:98 still reads `_STA_CONNECT_POLL_S`, and `_SteppedWifiAsyncio` caps `sleep` only.
- Lane F's: test_digital_twin_network_neopixel.py:56 still reads `_STA_CONNECT_POLL_S`, so it breaks until F converts it.
Seen failing first:
- 11 tests in the wifi file failed on a seconds-form stand-in (`sleep(_X_MS / 1000)`, never committed), at :954 (hotspot pattern), :1397 (stations settle), :4681 (connect poll), the disconnect, client and deactivated pattern tests, and the `_led_pattern` comparisons.
- OF-29: the new test failed at :444 with 7 "Could not arm" lines in one episode.
- Bite: test_neopixel_wifi_integration.py run against the base wifi service failed 3 pattern tests (:170, :198, :303). The bite copy is deleted.
Red checks:
- tests_scripts/test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree: "wifi.sta_disconnect_poll_ms is tagged but has no SPECIFICATION.md Part N row", plus the 8 other renamed wifi tags. These wait on the lead's Part N renames (R-24). It is the only red in the 17 repo-wide scans plus the readers of my files.
- test_twin_record.py was not run (expected red, per the common brief).
Times (-1 / 32768) against base:
- test_asy_wifi_service.py: 24.38 / 24.81 s (base 24.39 / 24.73).
- test_neopixel_wifi_integration.py: 2.75 / 3.07 s (base 2.71 / 2.82, +8.9 % at 32768, under 10 %).
- Zero MemoryError or "memory allocation failed" in every run. mypy main pass, src/tests/device_scripts pass and host pass are clean; ruff is clean.
Effect per mode:
- STA, AP, Silent and Off keep identical wait values. I checked that float32 int(t*1000) gives 2900/100/500/1500. No repeating wait allocates a float any more.
- Silent stays dark. USB and an exhausted alarm pool now print one helper line per episode instead of one every 5 s pass; persisted TIMER entries are unchanged.
Silent-failure scan (my files, all classes, these modes plus a task restart mid-episode): no new finding. quiet= only suppresses repeats, and `_tick_armed` survives a restart.
Decision (agent, 2026-10-21): `quiet=True` instead of a new local `reported` flag. The retry branch runs only after an arm that already refused and printed, so no new state is needed (minimal-first rule).
Process note: five foreground pytest runs of 62-120 s were not logged at start in RUNS.md. I recorded them late in one line; all exited.
Next block: W2 starts from 9aadd93 (asy_udp_socket.py, asy_captive_dns.py and their tests). Nothing is half-done.
Nothing of mine is running.
