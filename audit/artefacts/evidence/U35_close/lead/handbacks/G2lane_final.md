G2 hand-back (lane G, its last block). Branch audit/u35-g2 in S/wt-u35g2, made from 3f2183c and rebuilt (rc=0). One commit: 7d7c594, which is the branch head. Nothing is pushed and nothing is uncommitted. No typings link is left. Nothing of mine is running. I made about 30 tool calls.

**Verdict: the guard is removed in both files.**
- `_run_on_clock` now runs every plan on the driven clock, dev's UART-wired plan included. The comment no longer names `EPOCH_US`. It now says the link reads its wire time off the twin's plain clock (`digital_twin/_flash_stall.py`'s `plain_us()`) (agent, 2026-10-22).
- With the guard gone, some real-time code only dev used became dead, so I removed it: hot replug's real-time poll in `_until` and its `_POLL_S`, and the `clock is None` fallback in `_driven` in both files. The scenario types narrowed to `DrivenTime`.
- The timer pool's reboot case keeps its real waits, as G1 decided. Every assertion is kept.

**dev passes on the driven clock at both stages.** All runs rc=0, with zero MemoryError and zero "memory allocation failed". Times in seconds, 3f2183c → head, at gc -1 / 32768:
- Timer pool, dev: 43.4 → 12.6 / 39.8 → 13.1 (4/4 passed).
- Hot replug: 37.3 → 8.1 / 37.7 → 8.6 (2/2 passed).
- The other five devices, timer pool on the head at -1, each 4/4: wozi 11.6, arzi 10.8, grkizi 10.8, klkizi 10.8, schlafzi 10.8. These match G1's head times.
- Settrace on the head: timer pool dev 14.2, hot replug 10.0. Zero memory markers.
- No file is slower.

**G1's plants still bite on dev: 19 runs, all bitten.** Each red is on virtual time and carries its own wait's message. The plants ran in a scratch copy, which is now deleted. Nothing planted is committed.
- Timer pool on dev:
  - PA, PB, PB2 (boot and start);
  - PC (failed arm never ends the task);
  - PD (no restart);
  - PE and PE2 (no read once the pool frees; PE2 is on dev's sgp40);
  - PH, PI, PJ, PK (uptime stands still; SYSTEM, NTP and WiFi never re-arm).
- Hot replug, on bmp3xx and isl29125 with the power-cycle case on:
  - PA, PB, PB2 (boot and start);
  - PD (no restart);
  - PE ("never read before the unplug"; the power-cycle case went red too, with "BMP3XX never read");
  - PF (the task never ends while unplugged);
  - PG (no read after the re-plug);
  - PW ("the re-plug of bmp3xx starved the watchdog").
- Under PD, the tick case also goes red, with "NTP's timers never re-armed". G1's wozi run of PD showed the same line, so it comes from the plant itself.

**Checks**
- Clean: ruff, mypy main pass and mypy twin pass (cold cache, typings link removed after), and member order.
- One pytest process ran the 17 scans, the 12 commit checks and the reader test_device_tomls: 1005 passed, 5 failed.
- The 5 reds are not from my change. The same 5 tests fail on clean S/wt-u35int at 3f2183c, which I ran read only (log c_int_reds.log), and none of their lines names my files. They are owed to the lead and D:
  - `tests_scripts/test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree` lists 14 lines. 13 are tags with no Part N row (`src/asy_config_manager.py:71`, `src/asy_uart_link_driver.py:51/53/55`, the uart_link and hazard tunables in the tests, and two `tests_hardware/bench` ones). The 14th is a row with no tag: `SPECIFICATION.md:11787` `l1.notification_neopixel_wait_until_timeout_ms`.
  - `tests_scripts/test_task_inventory.py`, 4 tests: `asy_uart_link_driver.py:218/219 UARTLinkDriver._two_initiations()` and `asy_neopixel_driver.py:144/202` create tasks that no row of C.9's task table names.

**Silent-failure scan:** no new finding. G1's class 3 finding (twin mode: dev's waits depended on host load) is now closed for dev. Only the reboot case keeps real waits, which is G1's covered decision. Class 4: none, because `_until` re-raises with the wait's message.

**Effect per mode:** tests only. STA, AP, Silent, Off and USB are unchanged on every device.

**Decisions (agent, 2026-10-22):**
- The UART-wired plan runs on the driven clock.
- I removed the dead real-time branches rather than leave them in.
- I took the pair base from a copy of the 3f2183c tree, then reused that copy for the plants and deleted it.

**Facts owed:**
- To D: `SPECIFICATION.md:12114` and `:12116` (`l2.timer_pool_wait_s`, `l2.hot_replug_wait_s`) now bound driven seconds on every device, dev included. Only the reboot case is still real.
- To the lead: the 5 reds above.

**Runs:** every run has its lines in S/u21/RUNS.md, all done: rebuild, pairs.sh (rc 0), bite.py (19 runs), st.sh (rc 0), check.sh (pytest rc 1, the 5 reds) and the int read-only check.

**Logs** are in S/u35/laneG/g2/: times.txt, pairs.out, pb_*/ph_*.log, bite.out, bite_*.log, st.out, c_ruff.log, c_mypy_main.log, c_mypy_twin.log, c_pytest.log, c_int_reds.log.