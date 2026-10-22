V8 hand-back (lane V). Branch audit/u35-v8 in S/wt-u35v8, built on 2360470. One commit: 88593ce. Nothing pushed, nothing uncommitted, no typings link left, nothing of mine running. I used about 75 tool calls, so I stopped under CHECKLIST 21. Only tests/_sensortask_scenarios.py changed.

**Parts by verdict**
- **LEAD NOTES 49: applied.** The expected sensors set now adds `module.uart_link_init.name` ("UART_init" on dev) where `_has_uart_link`. It also checks that the hazard report's keys are exactly Runs, Pending and Last.
  - Seen red first: this is the known base red on dev at the set-equality line, named by LEAD NOTES 49 and V7.
  - Bite ph: the report without "Pending" is red at :3285.
- **Bus NAK storm, the ladder rungs and recovery: applied, on all six devices.** New scenario `a_bus_nak_storm_climbs_each_rung_once_per_bus_and_every_reader_recovers`, beside the fault storm. It starts each I2C reader's real loop through `start_asy_read()`, then NAKs every address. It asserts:
  - per reader: max_module_error+1 streak entries, one give-up and one participant rung;
  - per bus: exactly one clear and one controller rung across all its readers;
  - each logger's chunk writes stay at or below its entries;
  - after the NAKs clear, the ended loops are restarted: streak 0, rungs 0, the bus not recovered again, no streak or give-up entry.
  - SGP40 reads only on a fresh compensation sample, so in the storm it persists nothing and its loop stays alive. Its bus alone (arzi) sees no rung.
  - Bite p2 (`self._rungs |= _RUNG_DEVICE` dropped) is red at :2456.
  - Bite p3 (the streak never counts down) stayed green: the restart's init resets the streak. The comment now says "reads on with its streak at 0".
- **Webserver drop: applied, on all six devices.** New scenario `a_storm_of_refused_connections_spends_one_slot_and_a_request_serves_once_the_slots_free`. Six refusals go through `_serve()`. It asserts: every stream closed, ErrCount 6, HTTP_REFUSED in one slot, chunk writes at or below 6, HTTPDropped 6, and a GET /status that serves and persists nothing.
  - Bite pw (alternating codes) is red at :2492.
- **NTP no-reply: not written.** I ran out of calls. It needs a UDP no-reply seam in-process, and the resync count stays out (V6's flag-first finding).
- **Paired times: not run.** The next block should run test_sensortask per device at both stages against 2360470, alternating. `S/u35/laneV/v8/vbase` holds 2360470's scenarios file, test file and `_threshold_runner`. The scripts are `S/u35/laneV/v8/r.sh` and `run.sh`. Expected growth is small: each new scenario takes about 0.5-1.5 s of the 5-7 s scratch runs, but I have no measurement.

**Checks**
- Every new or changed scenario is green on all six devices at -1 and at 32768, run through the scratch selector `S/u35/laneV/v8/only/only_sensortask.py`. Zero MemoryError and zero "memory allocation failed".
- ruff is clean. All three mypy passes are rc=0 (cold cache).
- D.15 shows only the known `@_register` line.
- The 12 checks, the 17 scans and the readers ran in one pytest process (c1): 1727 passed, 19 red. No red line names a file of mine:
  - tunables_register: asy_config_manager.py:71;
  - task_inventory ×4: now also asy_neopixel_driver.py:144 and :202, plus UARTLinkDriver._two_initiations;
  - lock_order ×9;
  - microtest json_loads (lane P's);
  - twin_record ×2 (expected);
  - new since V7: level_containment, where the twin scenarios fault_storm, ntp_unreachable_load, reader_saturation and watchdog_fault have no L3/L4 counterpart or E.6.6 row (lane T, or the lead);
  - new since V7: fake_surface_conformance[SPI], "tests/machine.py SPI declares no TEST_API". It looks like the checker does not read 2360470's annotated `TEST_API: tuple[str, ...]` (lead, LEAD NOTES 21).

**Decisions (agent, 2026-10-22)**
- The SGP40 is treated as gated in the NAK storm (its own `_read_loop` condition), and is not forced to climb.
- The participant rung counts as its done warning, the driver's own CHIP_SET entry or a CALLBACK entry, exactly once.
- Each reader's reply feed moved into the helper `_feed_i2c_readers`, to stay under PLR0915.

**Effect per mode:** tests only. STA, AP, Silent, Off and USB are unchanged on every device.

**Runs** (each with RUNS.md lines): h1-h10 and g_* scratch runs; bites pw, p2, p3, ph; checks c1 (rc=1, the reds above). The plant copies are deleted. Logs are in S/u35/laneV/v8/: bite_*.log, g_*.log, c1_*.log.