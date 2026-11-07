U3b hand-back (lane U). Commit **bfc6519** on 78fb201, branch audit/u35-u, S/wt-u35u. Nothing is uncommitted and nothing of mine is running. I stopped at the 70-call valve, so this block is partly done.

**Steps**
- **Open thread: applied.** There is no protocol defect, and J's accept/reject rules and timings are untouched.
  - Cause of the first 81: the peer ACKs the raw GET (uid 0) into the slot where the SET's ACK (uid 6) is due. `_validate_ack` refuses the stale uid as NO_ACK (asy_uart_comm.py:927, 1024-1025). The peer finds the SET where its own ACK is due and logs PEER_INITIATED on its own side.
  - Cause of the second 81: a test cause. The hook counted one fault twice, because `_fault` logs through `_err` (asy_uart_comm.py:520-523). The recovery succeeds on its first try (Crossed `[True, False, 1, True]`). Trace: S/u35/laneU/u3b/probe/nocrc.log.
  - Fix: the hook counts `_err` only, the pin is `[85, 81]` with its cause written beside it, and the peer's 88 is asserted.
  - New check for the other outcome: when the SET's first uid is also 0, the GET's ACK confirms it and the initiator gets 88. This is a guard, bitten by a raw GET of uid 1, which fails with "[81]" (bites/alias_uid.log).
  - The src comment now names both outcomes. Comment only, same line count, mpy-cross byte-identical.
- **Stop, don't cancel: applied.** The plain cancel holds on the head. At this site it also holds with the shim from before the cancel fix (preshim/cancel.log), so the stop was never needed here.
- **Route: partly applied.**
  - `WebserverService.add_status_command(key, command)`: a new route field would break positional `RouteSources` calls outside the lane (the U30 F1a precedent).
  - `_put_status` answers {key: true} with Valid or Failed. Any other value, or an unregistered key, answers Invalid.
  - Codegen, on dev only, emits `webserver.add_status_command("UartHazards", uart_link_init.request_hazard_run)` and the maintenance entry `("UART_init", uart_link_init.get_hazard_report)`.
  - definitions.py gains `UART_HAZARDS_KEY`, the confirm-toggle group `uartHazards` and two readonly fields, `UART_init_Runs` and `UART_init_Pending`.
  - Seen failing: the route test failed first with "no attribute 'add_status_command'". It now asserts Invalid, Valid, Failed, and Invalid on a service with no command, plus zero writes through config_manager, webserver and link_driver.
  - Two buildgen readers went red on dev and were updated: the asking list and the maintenance sources. I have not shown them failing on base.

**Effect.** Dev only: the five other devices generate no key, entry or group (checked in build/generated_src). On dev, STA and AP can start one bounded run. Silent and Off have no API, so the run can't be started there. USB is unaffected. Nothing persists, so no boot starts a run.

**Checks and runs**
- ruff: clean.
- mypy: 0 in the main pass (230 files) and 0 in host_typecheck (306).
- buildgen definitions and generate: 793 passed.
- link_driver at head: 43/43 at both stages, zero memory markers. Times 3.60 s (-1) and 4.70 s (32768), against U3a's final 3.42 and 4.73.
- mpy-cross: link_driver identical; webserver 15112 → 15273 B.
- Rebuild rc=0.

**Decisions (agent, 2026-10-21)**
- A registration method instead of a route field.
- The command is called unguarded: the one registered callable only sets a flag, and Microdot's per-request catch answers 500 otherwise.
- The report's key is the initiator's resolved name, as with SGP40, since buildgen/model.py is in no lane.

**U3b's remainder (next block's start)**
1. Show the two updated buildgen reader tests failing on base.
2. mockdata/samples.json: `status.sensors.UART_init {Runs, Pending, Last}`. The JS coverage test should go red until then.
3. tests_js templates and definitions-mockdata-coverage cases for the new group and fields, run under `unshare -n ns_xdg.sh` after a rebuild.
4. js/mock-server.js (in no lane) answers only ResetErrors, so the mock answers UartHazards with Invalid. This needs an owner.
5. link_driver paired against f6f54cc at both stages; every dev generated-module test file at both stages; the 12 doc and convention checks; test_twin_record (red expected).
6. A webserver-level test of `add_status_command` belongs in tests/test_asy_webserver_service.py (in no lane).
7. Hazard-run allocation, left unchanged: `_write_raw` uses `device.write()`, which copies each frame for its CRC (asy_uart_driver.py:787). That is 26 small copies per run; switching to `writefrom` with a CRC-sized frame would remove them.

**Not done in this block:** relay lines (none written), the silent-failure scan, the 17 scans. The tunables rows are unchanged since U3a; I added no new tags.

Logs: S/u35/laneU/u3b/. Disk 9.1 GB free; at most 2 heavy processes running.