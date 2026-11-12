U31 lane S block S2 FINAL
Commits on audit/u31-s (S/wt-u31s), after 602bb5c: 17c60ed (i2c probe settle), 4ba0e09 (BMP3XX waits). Nothing pushed, nothing uncommitted. Generated tree rebuilt (rebuild.sh rc 0, at 602bb5c's tree plus these src edits).
Steps:
- Applied, step 17 M.SRC_SENS.007/.013: `_PROBE_SETTLE_MS = const(100)`, tag `i2c.probe_settle_ms = 100`, both settles `sleep_ms`.
- Applied, step 17 M.SRC_SENS.040/.048: `_STATUS_POLL_MS = const(2)` and `_RESET_SETTLE_MS = const(3)` (tags `_ms`); conversion wait `sleep_ms((wait_us + 999) // 1000)`.
- Applied, steps 31 and 32, U31 parts: the x32/x32 test sees `sleep_ms(129)`, polls ≤ `_MEAS_TIMEOUT_MS // _STATUS_POLL_MS + 1`, and the :2384 comment is fixed.
- Already landed: step 29's U31 part (`_fast_sleep.py` patches `sleep_ms`, :37-38) and step 30 (the sea-level/wait-time test is gone; the accepts tests assert the calibration, e.g. :318).
- Not done: step 29's U24 part `_EXPECTED_TEMPERATURE` → `BMP_EXPECTED_TEMPERATURE` (still local, tests/test_asy_bmp3xx_driver.py:94). Moving it would tie the file's own dataset to the catalog and import ISL29125/SCD30/SGP40 into the file (decision 2).
Seen failing, on a never-committed version with the seconds forms and the new names:
- test_asy_i2c_driver.py new probe test: `AssertionError: [('sleep', 0.1, 0), ('sleep', 0.1, 1)]`.
- bmp3xx: x32 `[('sleep', 0.128939)]`; timeout `('sleep', 0.004939)`; new `test_reset_settles_one_tick_past_the_start_up_time` `[('sleep', 0.002)]`.
Bites, in a scratch copy, now deleted: truncating `// 1000` → `[('sleep_ms', 128)]`; settle const(2) → `[('sleep_ms', 2)]`; i2c after-settle moved out of `finally` → NAK case `[('sleep_ms', 100, 1)]`. The copy's 29 other fails were all ENOENT: it lacked buildgen/error_catalog.json, which tests/_error_codes.py:12 reads.
Red checks (both the lead's):
- test_tunables_register::test_the_tags_and_the_part_n_rows_agree, my lines: "src/asy_bmp3xx_driver.py:79: bmp3xx.status_poll_ms is tagged but has no SPECIFICATION.md Part N row"; ":81: bmp3xx.reset_settle_ms …"; "src/asy_i2c_driver.py:22: i2c.probe_settle_ms …"; "SPECIFICATION.md:11453: bmp3xx.status_poll_s is a tuned row, but no file carries its @tunable tag"; same text at :11454 (bmp3xx.reset_settle_s) and :11455 (i2c.probe_settle_s). Rows owed: status_poll_ms 2, reset_settle_ms 3, probe_settle_ms 100.
- test_import_placement::test_the_pending_list_only_shrinks: S1's two `test_next_sleep_s_*` rows. mypy main pass (both forms): only tests/test_neopixel_wifi_integration.py:59 (waits on W).
Relay lines I would have written:
- Lead: the Part N rows above; SPEC M.4 :11235 "2 ms (`bmp3xx.reset_settle_s`)" → 3 ms `bmp3xx.reset_settle_ms`; :11236 `bmp3xx.status_poll_s` → `_ms`, and the wait is rounded up to whole ms.
- S3: in `PollRoundClock` (tests/_bus_hazard_catalog.py:650-652), `sleep_ms` now also receives the probe settles (+100 ms on the fake clock per settle). The twin hazard file's `_FastSleep` patches `sleep` only, so those settles and BMP3XX's waits now run in real time there.
Times -1/32768 (base): i2c 1.48/1.50 (1.63/1.51); bmp3xx 13.71/13.82 (13.69/13.77); 0 memory markers.
Other checks passed: ruff; the 12 convention checks; const_mirrors; every tests_scripts reader of the two src files (buildgen_* ×10, config_schemas, device_script_config_schemas, fault_or_warning_never_both, import_graph, lock_order, memory_catalog): 2641 passed.
Silent-failure scan (both src files, classes 1-7): nothing new. ticks_add/ticks_diff are wrap-safe (core.py:4, :53-58); the early wake is covered by the +1 tick at reset and by the STATUS poll after the conversion. Datasheet: the PDF can't be rendered here (no pdftoppm), so tstartup 2 ms was read from S/dstxt's text of the same PDFs (DS001 :340-348, DS002 :354-358, DS003 :291-295).
Modes (STA, AP, Silent, Off, USB, and boot): identical in each. A BMP3XX read takes 1 ms more (the conversion wait rounds up) and a reset 1 ms more (once in the boot setup() batch); the probe settle is unchanged. One to two fewer heap floats per settle, poll or conversion; no console change.
Decisions (agent, 2026-10-21): (1) the seen-failing runs used a version with only the names changed, so the tests import and fail on the behaviour, not on the missing name; (2) step 29's catalog move is left out (above).
Runs: pre -1 i2c rc 1 / bmp rc 1 (expected); post i2c and bmp at -1 and 32768 rc 0 ×4; bites rc 1 ×2 (expected); tests_scripts rc 1 (the two reds above); mypy ×2 rc 1 (the :59 line). A stray `find /` I started was killed by pid 23421. Logs: S/u31/laneS/s2_*.
State for S3: head 4ba0e09; S2 complete; S3's block is untouched; nothing half-done.
nothing of mine is running
