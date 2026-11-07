U31 lane C block C2 FINAL
Branch audit/u31-c in S/wt-u31c, head 489c87a, nothing uncommitted, nothing pushed. Commits: ac6efb4 "one standing check that every src/ sleep takes whole milliseconds" (new tests_scripts/test_src_sleep_forms.py); 489c87a "buildgen bounds each I2C timeout by the device's smallest hard consumer" (buildgen/validate.py +34, test_buildgen_validate.py +61/-2, test_buildgen_error_contract.py +1).
Steps:
- Step 17's sleep-form check and step 25's time.sleep case: applied. AST scan of src/*.py through every alias. asyncio.sleep takes only an int literal or a const(<int>) name; no asyncio.wait_for; a sleep_ms/wait_for_ms delay has no float literal, no float module name and no `/`; time.sleep* only at the 4 named (file, function, argument) waits, and a waiver that matches nothing fails.
- Step 3 (A.U31.08 under R-3): applied, as its own rule `bus.i2c-timeout-consumer`. The check: 2 x timeout (default `_DEFAULT_TIMEOUT_US`) <= min(each link's `_DEFAULT_TIMEOUT_MS - (2*poll_wait + poll_idle + _GC_PAUSE_WORST_MS)`, `_WDT_TIMEOUT_MS - _TASK_CHECK_TIME*1000`). It runs last in build_model. Source: ports/rp2/machine_i2c.c:125,:147 v1.29.0 (one timeout per transfer). The step's earlier stages had already landed.
- Steps 48 and 53, U31 rows: applied (bound tests; one contract row). Every earlier-stage row was already in place (one hit each).
- Left for C3: steps 14 (R-17) and 27, plus asy_system_service.py (OF-26, OF-29's half, OF-222). Nothing half-done.
Seen failing first:
- Guard on the base src (only asy_base_classes.py differs, and it has no sleeps): "AssertionError: 25 src/ sleep site(s) break the form" (1 failed/19 passed). It stays red until wave 1 merges: count 25 (bmp3xx 3, captive DNS 1, i2c probe 2, neopixel 3, notification 2, scd30 4, udp 1, webserver wait_for 4, wifi 5).
- Rule, at the base validate.py: 4 x "DID NOT RAISE BuildError". These are the dev-shaped pair with poll_idle_ms 900 (75 ms of slack), the link and watchdog edges at 37500/37501, and the unstated timeout. Contract: "rows for rule ids no buildgen/ site raises any more" plus its row.
Bites (scratch copies, deleted): the plan's two (`asyncio.sleep(0.05)`, `time.sleep_ms(1)`) are committed tmp_path rows that the guard refuses. Five more in scratch copies, each failed: a stale waiver; an alias map blind to asyncio; a plain int name accepted; from-imports ignored; `/` accepted.
Deviation, two existing uart-floor tests: they built at poll_idle_ms 975, which leaves zero slack. They now run on a device with no I2C bus and keep their exact edges.
Decisions (agent, 2026-10-21):
- `_clear_bus_awaiting` (the runtime clear's 5 us half periods) counts as a named wait beside the boot clear. This matches the plan's 25.
- A float module name in an ms delay is refused like a float literal.
- The minimum is taken over all consumers. The watchdog consumer always applies.
Modes: build-time only. All six devices build unchanged (dev's bound 462500 us, the others 3000000 us) and generated output is unchanged, so no effect in STA, AP, Silent, Off or USB. A future TOML whose I2C timeout eats a link's reply slack is now refused.
Runs (all exit 0 unless noted, zero MemoryError and zero "memory allocation failed"):
- test_buildgen_validate 413 passed, 6.17 s (base 8.78). test_buildgen_error_contract 184 passed, 8.92 s (base 11.44). test_src_sleep_forms: 1 failed by design, 19 passed, 1.42 s.
- ruff clean; host mypy pass clean (303 files). 12 convention checks + lint_type_scopes: 796 passed (twice).
- Readers of validate.py: 21 pure-parse files, 1760 passed/6 skipped, 78 s; 3 light twin readers, 73 passed; test_digital_twin_generated_boot, 22 passed, 56 s.
- The first twin-reader try failed 10 tests with "node v22.22.2 on PATH, .nvmrc pins 24" (environment only). It passed with the pinned Node 24.21.0 first on PATH.
- RUNS.md has lines for the two runs over a minute. Logs in S/u31/laneC/c2_*.
Silent-failure scan (validate.py change, the guard): none found. module_int_const fails loudly (src.const-missing). The slack cannot go negative because the floor check runs first.
Facts owed:
- D: L.3 table and F.3 stall.i2c_transfer gain bus.i2c-timeout-consumer (formula, bounds, fix text); D.4's "checked by tests_scripts/test_src_sleep_forms.py".
- Lead (R-24): Part N rule row i2c.timeout_consumer_us. loop.sync_wait_max_us is "Checked by" the guard; its exceptions are the SPI CS settle and both bus clears.
- S/W: a rename of _clear_bus, _clear_bus_awaiting, session_begin/end or their argument constants trips the stale-waiver test.
nothing of mine is running
