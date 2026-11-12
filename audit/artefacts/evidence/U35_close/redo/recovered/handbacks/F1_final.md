F1 hand-back. Commit 9cc8c96 on audit/u35-f1 (base 0a0476a), not pushed. Nothing is uncommitted.

Item 1, the hotspot-exit window: it cannot occur. I added a guard test, no product change.
- Test: test_an_ntp_attempt_at_the_hotspot_window_end_never_finds_the_ap_a_network (end of tests/test_asy_wifi_service.py). A probe takes wifi_mode_lock at every yield, as `_sync_loop()` does. It runs through the window end, the mode switch and the STA attempt, and the network check never passes while the AP is selected. It passes on the tree. With an `await asyncio.sleep(0)` planted in a scratch copy between `_leave_hotspot_mode()`'s phase assignment and `_select_wifi_mode()`, it fails: "the network check passed with the AP still selected".
- Proof: when the lock is free, the STA_SEEKING assignment and `_switch_wlan_mode()`'s `active(False)` run with no yield between them (extmod/asyncio/lock.py acquire). Every other lock holder runs in the connect-loop task itself, `_recover_device()` included (via `_climb_ladder`). The NTP attempt in the hotspot phase holds the lock across no await.
- N4's cited lines 479-483 do not run when leaving the hotspot (`leaving_hotspot` skips them). Where arzi's E73 entries came from is still not established; that needs the live twin.

Item 2, the flat GET's unavailable marker: landed. `_get_settings_flat()` now requires the marker's whole shape (one key, error == UNAVAILABLE), matching js/api-contract.js:28. The new test failed on the old line. The marker bytes are unchanged; the only effect is on a settings GET where a module has a field named error (none today).

Item 3, dead code under the library rule:
- Restored: SensorReader's `logger=` parameter. It was removed in 8d44fd1 (U11), not in U35; P1 only recorded it. Its test failed on the old tree with "unexpected keyword argument 'logger'". The default is None, so no current caller changes.
- Removed as dead: the sgp40 `_exchange()` reply bound (proof in the commit).
- Kept as features, each with its direct test in tests/test_asy_isl29125_driver.py: isl 1402-1408 and 1422 (public `decode_config`/`decode_status` accept None), 1463 (`matches_shadow`), 1277 (`is_bus_fault_pattern`), 1448-1453 (`fraction_to_counts` clamps), 1496 (`persist_for_interval`).
- Also kept: isl 455 and 788 (they narrow a public decoder's None), and webserver:425 `close()`, which stays so the proxy matches the asyncio Stream interface.
- Kept, not removed: isl `_decode_rgb_burst` guards 1217-1223 (they keep the three decoders' shared None contract; test_decode_rgb_burst_rejects_short_and_none). isl:1504 is narrowing and already commented.
- webserver:903: kept as a feature (system_cmd is optional). New test test_a_system_command_on_a_service_built_without_its_callback_reads_invalid; I planted FAILED for INVALID and it failed.
- Kept, with each one's reason:
  - uart :564-565, :620-621, :672-673: the anti-spin yield behind the hard rule that the UART driver never blocks the asyncio loop. Removing it would create a hazard if the premise ever breaks. I did not rename the test at :2319.
  - scd30:735: honours `I2CDevice.readinto()`'s documented False.
  - system:441: reachable after all. A cancel of the shutdown task lands in the `except CancelledError: pass` at :437. Its direct test is still owed; I did not add it.
- The 7 narrowing comments are in. scd30 and uart_driver compile to identical mpy-cross output.

Item 4, first boot: no behaviour is keyed on being the first boot. Each one-time behaviour has its evidence:
- No config file: defaults written, `absent_at_boot`.
- FRAM chunk blank or CRC/seed mismatch: re-initialised. SGP40 backup blank or invalid: the algorithm starts fresh.
- The reset reason comes from reset_cause() and mem_backup. The Wi-Fi streak resets on every task start. DEACTIVATED means no readable Wi-Fi configuration.
- Handed back (logged-entry contract): after a commanded config reset, the next boot logs no W CONFIG_LOST. The suppression is keyed on the reset record (`_RR_CONFIG_RESET`/`_RR_COMMAND_INCOMPLETE`, asy_system_service.py:740), which is evidence. Options, same on every device: (a) Keep it. (b) Log it there too: one more W69 per commanded reset in SYSTEM's FRAM log, whose text ("reformatted or wiped") would misdescribe the reset.

Runs (8 RUNS.md lines, all closed): 28 importer files at gc -1 and 32768: all passed, zero memory markers (the first pass hit "generated_src stale" after my src edits; regenerated and re-ran those 6 green). Twin integration for wozi at both stages: rc 0 (4 passed, 14 skipped). ruff clean; both main mypy passes clean. The 12 checks plus 11 readers: 1084 passed, after I reworded one comment that test_decision_vocabulary flagged ("must never" -> "never passes"). mpy-cross output: base_classes, sgp40 and webserver change; scd30 and uart_driver are unchanged.

Deviations: Not every importer of asy_base_classes was run; the new parameter defaults to None. No twin CI device runs (the CHECKLIST forbids them). The wifi file takes 24.4/24.9 s against U24's old base (19.5/21.2 s, from before later tests were added). Not a paired run; the lead should check.

Silent-failure scan: nothing new.

For D3: E.5.1 register: drop asy_sgp40_driver.py:697. Add keep lines for: scd30:735, the three uart `if not want:` branches, isl 1217-1223, webserver:425 and :903. Correct system:441: it is reachable by a cancel, not unreachable.
nothing of mine is running

[F1's commit message, as printed in the lead's review: "U35 lane F1: the flat GET reads the unavailable marker by its whole shape; logger= restored; the hotspot-exit window proven closed". Body: _get_settings_flat() took a module's answer for the unavailable marker on the key test "error" in values, so a readable module with a field named error sent its whole answer for each missing field; it now needs the marker's whole shape, one key and error == UNAVAILABLE, as js/api-contract.js already reads it; test first, failed at its first assert on the old line; no REST field changes meaning. The hotspot-exit guard test (probe takes wifi_mode_lock at every yield). SensorReader's logger= restored with its test (removed in 8d44fd1) under the owner's library rule. asy_sgp40_driver._exchange()'s reply bound removed as dead (agent, 2026-10-23): _exchange() is private; its callers pass 1 (_read_word()) and 3 (_read_words(), whose one caller passes 3), and the reply buffer is 9 bytes, so no input reaches the raise. A direct test for a system command on a service built without its callback (Invalid). Narrowing comments at seven re-checks (scd30:280; uart_driver :183, :290, :357, :369, :810; webserver :212), comment only. Diff stat: src/asy_base_classes.py 8, asy_scd30_driver.py 2, asy_sgp40_driver.py 2 (-), asy_uart_driver.py 10, asy_webserver_service.py 4; tests/test_asy_base_classes.py +9, test_asy_webserver_service.py +22, test_asy_wifi_service.py +34.]
[Lead's decision on the CONFIG_LOST hand-back (LEAD NOTES 147): (a) keep it (agent, 2026-10-23): keyed on the reset record, which is evidence; no behaviour changes.]
