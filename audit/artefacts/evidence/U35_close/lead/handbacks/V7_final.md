V7 hand-back (lane V, last block). Branch audit/u35-v7 in S/wt-u35v7. One commit, ed649bd, on 3f2183c. Nothing pushed. Nothing uncommitted. No typings link left. Nothing of mine is running. About 71 tool calls, the restart included.

**Parts by verdict**
- **Pin fake fidelity: applied, in both fakes.** tests/machine.py and digital_twin/machine.py now follow machine_pin.c:464-476. irq() on an external pin raises ValueError("expecting a regular GPIO Pin"), even with no arguments. A bare irq() returns the registration unchanged. An explicit None, or any other argument, still replaces handler, trigger and hard. I also fixed the twin's copy, since it had the same two gaps (D.10).
  - Seen failing: test_fakes.py:415 (external pin), test_fakes.py:429 (bare call), test_digital_twin_machine.py:307.
  - Bites: b1 makes a None handler return early: red at :429. b2 checks the handler sentinel only: red at :434. b4 makes irq(None) keep the handler: red at :431. b3, the twin with no bare-call return: red at :313.
  - Every file that reaches Pin.irq is green at both stages: test_fakes, test_digital_twin_machine, test_digital_twin_scd30, test_asy_isl29125_driver, test_asy_scd30_driver, test_digital_twin_isl29125, test_digital_twin_isl29125_autorange.
- **Ring saturation per logger: applied**, all six devices. Every FRAM-backed logger is seeded one below _MAX_CNT. More distinct codes than the ring holds count up to the top and stop there. The ring keeps the newest codes in order, and a rebuild on the chip image restores both. Bites: b7 (the count wraps to 0 at its top) gives WIFI ErrCount 10. b8 (the restore truncates the count to one byte, asy_print_log.py:410) gives NOTIFY 255.
- **ISL29125 stored ticks (:431, :567): applied**, dev only. The window and the candidate hold are armed a minute before a wrap, and each ends on its own deadline. Eight five-day stalls follow, crossing four wraps; each is over at the first cycle after its stall. Bites: b5 (raw subtraction in _expire_calibration) and b6 (the same in _measured_ratio) are both red.
- **UART stored tick (asy_uart_comm.py:381): applied**, dev, both instances. A hold-off armed before a wrap holds for one window. After idles of 3, 7, 20 and 33 days the gate opens at once. Bite b9 (drop `remaining > window`) leaves the gate shut at 7, 20 and 33 days.
- **Not written: NTP resync count.** asy_ntp_client.py:374 counts 10 s ticks, so forty days needs 345,600 refresh passes in-process. With stalls instead, the test would pin V6's class-5 discrepancy, which D.1 says to flag first.
- **Not written (out of calls, CHECKLIST 21): the storm's periodic paths (bus NAK, NTP no reply, webserver drops), recovery and ladder rungs.** They can be written in-process. The next block can put them beside fault_storm_keeps_every_module_within_its_persisted_log_rate.

**Times** (test_sensortask, 3f2183c → head, alternating, the runner beside each copy; seconds at -1 / 32768)

| Device | -1 | 32768 |
|---|---|---|
| arzi | 32.53→33.86 | 36.81→40.07 |
| dev | 51.13→53.93 | 61.51→64.58 |
| grkizi | 31.82→33.97 | 36.94→39.44 |
| klkizi | 32.37→33.95 | 37.43→39.81 |
| schlafzi | 32.37→33.97 | 37.03→39.04 |
| wozi | 36.21→38.27 | 41.45→44.03 |

- Every file grew 4.1 to 8.9 %, all under 10 %. The growth is the three new scenarios (99 → 102 per device).
- Zero MemoryError and zero "memory allocation failed" in every log.

**Checks**
- ruff is clean. All three mypy passes are rc=0 (cold cache).
- D.15 shows only the known `@_register` line.
- test_digital_twin_generated_boot: 22 passed.
- The 12 checks, the 17 scans and the readers ran in one pytest process: 1689 passed, 17 red. No red line names a file of mine:
  - test_tunables_register: asy_config_manager.py:71, plus new rows from asy_uart_link_driver.py:51-55 and the uart-link hazard tests.
  - test_task_inventory ×4: asy_uart_link_driver.py:218 `_two_initiations()` creates a task outside every task starter.
  - test_lock_order ×9: asy_uart_link_driver.py:164 and :228, where `bus` resolves to no lock-table row.
  - test_microtest json_loads: lane P's, the known one.
  - test_twin_record ×2: expected.
  - All of these come from the merged head (lane U's UART link driver). They wait on U, D and the lead.

**Findings for the lead**
- Base red on dev at 3f2183c: _sensortask_scenarios.py:3125 (`webserver_status_get_reflects_the_real_object_graph`, base line ~3026). /status "sensors" carries an extra `UART_init` key. It fails on 3f2183c's own files at both stages and is identical on head. I did not root-cause it: some other lane's src change adds the key.
- Tool gap: tests_scripts/test_code_conventions.py:238-240 `_import_time_names` does not count a method's default as an import-time need. Because of that, I named the twin's sentinel `_absent_handler` so it sorts first.

**Decisions (agent, 2026-10-22)**
- Both fakes take the irq fix, because they share the same rp2 contract.
- The handler default is a sentinel function, and the code adds no new type: ignore.
- The ISL and UART scenarios do nothing on devices without the chip or link (dev only).
- The restart cut checks.sh during its pytest step. I wrote its done line and re-ran that step once, as c2.

**Effect per mode:** tests and twin fake only. STA, AP, Silent, Off and USB are unchanged on every device.

**Runs** (all with RUNS.md lines): s1-s3 and the b1-b4 seen/bite runs; irqchain (the 4 ENOENT reds were a snapshot that lacked buildgen/error_catalog.json; the irqchain2 re-run is all rc=0); the diag probes; bites b5-b9 (red as planned); chain.sh (24 runs; only dev is rc=1, the base red); checks c1 (terminated by the restart) and c2 (rc=1, the reds above); genboot rc=0. The plant, snapshot and run copies are deleted.

Logs are in S/u35/laneV/v7/:
- s*/b*_fakes/b3_twinmachine: the fake cases;
- irq_*/irq2_*: the Pin.irq files;
- bite_*: the scenario bites;
- pb_*/ph_*: the paired times;
- c1_*/c2_checks.log: the checks;
- genboot.log: the twin boot run.