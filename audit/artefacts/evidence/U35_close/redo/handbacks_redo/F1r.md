F1r hand-back, saved by the lead from the message it sent (2026-10-26T18:39). Commit 18b9ff6 on audit/u35-f1r.

F1r hand-back. Commit 18b9ff6 on audit/u35-f1r (base 656fc82). Not pushed, nothing uncommitted. Logs are in S/u35/laneR/f1r/.

Items by verdict:
- Item 1, the hotspot-exit window: it cannot occur. I added a guard test and changed no product code. The test is test_an_ntp_attempt_at_the_hotspot_window_end_never_finds_the_ap_a_network, at the end of tests/test_asy_wifi_service.py. A probe takes wifi_mode_lock at every yield through the window end, the real mode switch and an STA attempt that links. It passes on the tree. With `await asyncio.sleep(0)` planted after `_leave_hotspot_mode()`'s phase assignment in a scratch copy, it fails with "the network check passed with the AP still selected" (wifi_bite_m1.log).
  - The lost F1's proof was wrong in one premise: `_uptime_loop` runs as its own task, not in the connect loop. The verdict still holds. The uptime loop's locked section only awaits `_set_meas_data()`, and no holder of `_data_lock` keeps it across an await. An NTP attempt in the hotspot phase returns without an await. So the lock is always free at the assignment, and the acquire and `active(False)` follow with no yield between them. The commit body has the full proof.
- Item 2, the flat GET's unavailable marker: landed. `_get_settings_flat()` now needs the marker's whole shape (one key, error == UNAVAILABLE), the same test as js/api-contract.js's isUnavailable(). The new test failed first on the old line, at its assert (test_asy_webserver_service.py:4320). No marker byte or REST field changes meaning. No module has a field named error today, so no device or mode changes.
- Item 3, the part that needs no e51 table:
  - SensorReader's `logger=` is restored, in the same form as UARTComm's. Its test failed first with "unexpected keyword argument 'logger'". It defaults to None, so no device changes.
  - The sgp40 `_exchange()` reply bound is proven dead and removed; the proof is in the commit. The function is private; `_read_word` passes 1 word and `_read_words` is only called with 3; the buffer is 9 bytes and never rebound; no test named the bound.
  - All seven narrowing comments are in, located on this base at: uart_driver :182, :289, :356, :368, :809; scd30 :279; webserver :212. They use asy_uart_comm.py's wording ("Unreachable: … - kept to narrow the Optional for the type checker"). mpy-cross output for uart_driver and scd30 is identical to the base.
  - The rest of item 3 waits for the e51 table: webserver:903's test, the isl29125 rows, the three uart `if not want:` branches, scd30:735 and system:441.
- The two added items are done:
  - webserver :949 now says "traced" where it said "persisted"; this is comment only.
  - test_lint_ceilings.py:52-53 now states the fact without citing C.7: `logger=` shares an already-built sibling's logger, no device wires it, and tests do. Its message at :192 now names `_LOGGER_ALLOWED` instead of "the classes C.7 names" and keeps the "only the classes" fragment its test matches.
- Item 4, first boot: nothing in src/ or buildgen/codegen.py is keyed on being the first boot. Each one-time behaviour is triggered by evidence:
  - no config file (ENOENT): the defaults are written once and absent_at_boot is set (config_manager:539-543);
  - W69 CONFIG_LOST needs three things: the file absent, FRAM history restored, and a reset record that is not a config reset (system_service:740). So the boot after a commanded config reset meets the same no-file evidence and writes the defaults, and the reset record suppresses W69 (your (a) decision, LEAD NOTES 147, still matches this code);
  - an FRAM chunk that is blank or fails its CRC or seed check is re-initialised (fram_manager:236);
  - a blank or invalid SGP40 backup starts the VOC algorithm fresh (sgp40:564);
  - the reset reason comes from reset_cause() and mem_backup (system_service:151-160); it is only reported, and it only gates W69;
  - Wi-Fi goes DEACTIVATED only when its LED config is unreadable (wifi:316); the used-hotspot flag resets at each task start and on a credentials change.

Checks:
- The 44 test files that import the changed modules ran at -1 and 32768, every device for the two PER_DEVICE files: 108 runs, all rc 0, zero memory markers (imp.log).
- ruff is clean. The mypy passes are clean from a cold cache: main 265 files, twin 52, host 308, plus the network.py and conftest checks.
- 49 tests_scripts readers and convention checks: 3310 passed, 1 failed. The 4 runner-starting files ran in their own processes: 242 passed.
- The one red, waiting on your W10 twin-record re-record: test_twin_record.py:71, "changed since their twin run was recorded", api_sha256 for 31 device scripts. This is expected after a src/ change.

Deviations:
- The 12-check list (S/u24/briefs/common.md) is not in this container. I ran the convention checks by name instead: citations, code_conventions (member order), comment_block_cap, decision_vocabulary, gc_collect_sites, tunables_register, third_party_attribution, driver_shape.
- S/shared/typings does not exist, so I used a temporary copy of wt-u35t4r/typings and removed it afterwards. scripts/typecheck.sh refuses the shared venv (`require_project_venv`), so I ran its five mypy passes directly.

Silent-failure scan, all classes, STA/AP/Silent/Off/USB: nothing new. The marker fix closes a class 4/7 mismatch between the Python and JS readers. The window is proven closed (class 5).

Times: test_asy_wifi_service, paired and alternating, two rounds: base 24.37/24.62 s, head 24.39/24.65 s, so no growth. test_asy_webserver_service is 4.1/6.4 s against the U32 table's 4.42/8.01; base_classes is 0.4/0.4 s.

Facts for D3:
- SPECIFICATION.md:4433-4434 (C.14.1) says self.pr.name and self.name "always agree"; that is no longer true with `logger=`, where `pr` is the sibling's.
- SPECIFICATION.md:805 says `UARTComm` takes `logger=` "as every other module"; only SensorReader, UARTComm and UARTLinkDriver take it.
- The E.5.1 register (:5435-5458) can list the seven new narrowing comments. It has no sgp40:697 row on this base, so nothing needs dropping.

Runs (RUNS.md lines, all closed): the wifi guard and bite, the webserver and base_classes red-first runs, the importer run (18:03-18:28), the wifi paired timing, and the readers. All ended as reported above. The other processes on the host are T4r's and F2r's.
nothing of mine is running
