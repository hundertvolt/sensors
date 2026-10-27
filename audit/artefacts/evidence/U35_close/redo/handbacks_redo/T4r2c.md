T4r2c hand-back, saved by the lead from the message it sent (2026-10-26). Commit aa146d83 on audit/u35-t4r2c (on b8b7207e).

T4r2c hand-back. Worktree S/wt-u35t4r2c, branch audit/u35-t4r2c. One commit, aa146d83, on b8b7207e. Nothing is pushed and nothing is uncommitted. I stopped at the 80-call limit at a seam: fold (2) is done; fold (1) and item 5 were not started.

**Fold (2), done (aa146d83)**
- **T4r2b's premise, re-checked on this base:** the shared reads it reported are real.
  - BMP3XX: the stored-config apply when the task starts reads 0x1C/0x1F. `_read()` reads 0x1C on every measurement (src/asy_bmp3xx_driver.py:504).
  - ISL29125: `_verify_config` (:930, called each cycle at :687) and `reset()` (:1520) read the CONFIG1 burst that the snapshot reads (:1264).
  - SCD30: `setup()` (:918) reads 0x5403.
- **Fix: a new twin runner flag, `--test-defer-faults`.** Every `--fault` is held back until a `FAULT_ARM` line arrives on stdin. The runner then queues them all and prints `FAULTS_ARMED`; a later `FAULT_ARM` queues nothing more.
  - New code: `_fault_arm()` and `_test_arm_faults()` in digital_twin/run_generic_integration.py.
  - Also changed: a 13th TestFlags field, the usage text, the README row, and the flag's row in the flag table (tests_scripts/test_twin_runner_test_flags.py `_FLAG_TABLE`). That table is a registry, not an allow-list (lane_plan step 152 has lanes add rows to it), but please review the row.
- **The scenario `failed_config_snapshot_is_sent_as_unavailable`** (scripts/_digital_twin_scenarios.py) boots once per driver the device has. Each boot:
  1. waits for `boot phase: BOOT_DONE`;
  2. checks that nothing was queued, then arms two faults;
  3. sends GET /sensors until both are spent.
  - It asserts: the marker for that module only, with every other map intact; markers + verify lines == 2 and markers >= 1; the CHIP_GET entry in the error count; the map back once the faults are spent.
  - Keys: BMP3XX `readfrom_mem:1F` and SCD30 `readfrom_into:5403`. Once the boot is done, nothing else reads these unless a write or recovery runs.
  - ISL29125's limit, recorded in the docstring: `_verify_config()` reads the same burst every cycle, so a fault is taken by either the GET or the verify, and both are counted.
- **Red first:**
  - Knob tests on the base runner, both stages, 44/46: "TestFlags() takes 12 positional arguments but 13 were given" and "no attribute '_test_arm_faults'" (logs/red_knob_*).
  - Per-driver plants (the driver's `return None` changed to `return {}`, in a scratch tree): dev, both stages, rc=1, each at its own driver: "BMP3XX: 0 GET(s) sent the marker and the verify took 0 of 2 faults", the same for ISL29125 and SCD30 (scen/plant_*).
- **Green:**
  - The knob file: 46/46 at both stages, 1.39 s / 1.44 s, against base 1.32 / 1.37-1.40 s (within 10 %).
  - Fold (2), run together with the existing `a_real_bus_fault_degrades...` scenario (which takes the not-deferred path): passed on dev and arzi at both stages (g3_*). Fold (2) takes 15.3-15.6 s on dev and 3.7-3.8 s on arzi.
  - On dev, every fault went to a GET in the runs whose logs I read (none went to the verify). The verify branch of the accounting was not seen taking a fault.
- **Checks:** lint_direct rc=0 (after fixing a PLR0915 on main() and a 5-line docstring). Twin and host mypy cold, 0 issues. 21 readers plus the cap, citations, vocabulary and tunables checks: 1383 passed. Zero memory markers in every run. Silent-failure scan: nothing new. No new tunable, no stale SPEC sentence, no write site added or changed.

**Left (valve), facts for the next block**
- **Fold (1):** there is no SO_SNDBUF knob. Accepted sockets come from `asyncio.start_server(self._serve, …)` at src/asy_webserver_service.py:978. A knob would have to wrap that inside a `_test_` function. Not checked: whether the Unix port defines `socket.SO_SNDBUF`, and Linux's minimum send buffer.
  - `HTTPDropped` comes from buildgen/codegen.py:284, src/asy_webserver_service.py:592 and :1045; `_WRN_HTTP_PEER_RESET` = 48 (:108).
  - A second new flag will need TestFlags field 14, as aa146d83 shows.
- **Item 5:** `_UART_LOAD_REQUEST_S` is now at scripts/_digital_twin_scenarios.py:156, used at :2045, :2052 and :2068.

**Runs:** red_knob rc=1; green_knob and green_knob2 rc=0; g2 and g3 rc=0; the six plant runs rc=1 as planted; checks2 rc=1 (two findings, fixed); checks3 rc=0.
- The seq_plant and seq3 wrappers (each over a minute) wrote no RUNS.md lines of their own; each run inside them did.
- Logs are in S/u35/laneT/t4r2c/ (runs.sum, logs/, scen/).
- The private toolchain S/tc-t4r2c and the plant tree were deleted.

nothing of mine is running
