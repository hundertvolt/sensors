U31 lane D block D3 FINAL
Branch audit/u31-d (S/wt-u31d), head 6da05c1 on 10808b9. Nothing uncommitted, nothing pushed. Commits: 6584c6b L.3 · aaee521 I.3 · d1a0844 BACKLOG · 6f0a271 tests_hardware/README · 6da05c1 digital_twin/README. These are doc changes only, so no operating mode (STA, AP, Silent, Off, USB) behaves differently and no timed file grew. Silent-failure scan: no code changed, so no class applies.
Steps:
- 12 (L.3), applied: the `timeout` row (SPEC:10242) states that twice the timeout must fit the smallest hard consumer, as rule `bus.i2c-timeout-consumer` (the fix names the largest legal value). Sources: buildgen/validate.py:609-637, asy_system_service.py:63, asy_uart_comm.py:95/:112, asy_i2c_driver.py:28. It cites Part N `i2c.timeout_consumer_us` (SPEC:12551).
- 19 (A.5), already landed: A.5 says "a per-call or outer-cap timeout" (SPEC:568) and names no mechanism; A.5 (SPEC:489-609) has no `wait_for`.
- 23 (I.3), applied: "a per-write `asyncio.wait_for()`" is now `wait_for_ms()` (SPEC:8530), per asy_webserver_service.py:331-336.
- BACKLOG.md, applied: the boot-feed log row (:303-312) also times each setup unit against `boot.setup_unit_stretch_ms`. It adds one boot with a damaged config file: one flash write, behind `--allow-persistence-write` (asy_config_manager.py:581; tests_hardware/conftest.py:92). This tree has no build-environment change and U30's two entries are there, so nothing was added.
- 62 (CLAUDE.md), already landed: searched "UartLinkExerciser" and found no hit; CLAUDE.md:171 already says `UARTLinkDriver`. The long-blocking bullet (:250-252) is unchanged. CLAUDE.md was not edited.
- 63, applied in part: the `loop_stretch_timing.py` paragraph (tests_hardware/README.md:797, from the script's lines 35-108 and test_memory_stress.py:89-96). The step's site heading "Real-hardware coverage: sensors, FRAM and the API end to end" does not exist; there is no device-script list.
- Owed fixes, applied: tests_hardware/README.md:1411 now names `wait_for_ms(..., self._outer_cap_ms)` (asy_webserver_service.py:583, :917). digital_twin/README.md:254-256 has lane F's rows: the access-point-down row extended, plus the EPERM and deactivation rows (digital_twin/network.py:144-175, :198-236; tests :270, :416, :550, :565).
- 67: its U31 part is lane T's flag, so it is left to D1.
Left to D1:
- digital_twin/README.md flag rows: `--test-loop-lag-ms N` and `--test-drop-timer-fire reset|sequencer`.
- tests_hardware/README.md: the `test_flash_write_loop_gap_is_recorded` / `flash_write_loop_gap.py` bullet; the line "F.3's timing table owes three silicon rows …"; a paragraph for the loop-lag script `loop_lag_under_combined_load.py`. That script is already on the tree but has no README paragraph yet; it is tied to `lag.loop`.
- BACKLOG.md rows: "run `loop_stretch_timing.py` and `flash_write_loop_gap.py`, figures into F.3", and the bench loop-lag row (F.3 `lag.loop`). Also the build-environment list entry, if lane T's change under `scripts/` (`_digital_twin_scenarios.py`) needs one.
- CLAUDE.md: the boot-latency bullet's ending "; each inter-feed boot stretch and its margin are rows of SPECIFICATION.md Part F.3's timing budget table". F.3's table is not on this tree yet.
- From D2's list: F.3 `stall.i2c_transfer` gaining `bus.i2c-timeout-consumer`, and L1's MemoryError at the bounded escalation wait.
- For the lead: the module docstring at tests/test_asy_uart_link_driver.py:1 still says `UartLinkExerciser`. That file is outside my set.
Checks, one process on 6da05c1: the 17 repo scans plus toml_schema_contract, twin_fake_catalog, lock_order, memory_catalog, threat_model_statement, device_script_bench_facts and src_sleep_forms. Result: 957 passed, rc 0, zero memory markers, no red checks. The one UserWarning is the uninitialised datasheets/ submodule. Log: S/u31/laneD/final_d3.log; RUNS.md has its start and exit lines.
Decisions (agent, 2026-10-21):
- L.5's rule-id list gains `bus.i2c-timeout-consumer` (SPEC:10591). This is a consistency drift outside the block's parts.
- The CLAUDE.md pointer and the A.U31.05/.06 BACKLOG rows wait for D1, because they point at F.3 rows that do not exist yet and half of them is lane T's.
- The stretch paragraph sits beside the C-stack budget paragraph, which covers the same test file.
- The access-point-down row also cites `a_joined_link_with_no_address_holds_status_two`.
D1 starts from 6da05c1 with the "Left to D1" items above.
nothing of mine is running
