F2r hand-back, saved by the lead from the message it sent (2026-10-26). Commit c56b366b on audit/u35-f2r.

F2r hand-back. Commit c56b366b on audit/u35-f2r (base 656fc82). Not pushed, nothing uncommitted. 13 files: src fram_manager, notification_service, ntp_client, uart_link_driver; html/style.css; 7 tests/ files; tests_scripts/test_website_tokens.py. No change to asy_uart_driver.py (item 5's fix sits in the link driver), so no overlap with F1r.

Landed (each test failed first on the old code):
1. erase_ready() now also checks `self.fram.initialized` (asy_fram_manager.py:800). Red: `[True]` at test :3499. Premise check: no in-tree path opens the window. The driver's logger is RAM-only (fram_manager:649), so its err_s never suspends, and every path reaches lost.set() without yielding. Only the public FRAM_SPI.set_values() (sleep(0) at :351) opens it, and the test drives that. Effect: every FRAM device, STA/AP; nothing observable today.
2. In notification _check_one(), utc_now() and the age check moved outside the producer's try. Red at test :1605 (SOURCE blamed). Effect: notification devices, once the clock is set. A refused allocation there no longer writes NOTIFY E SOURCE plus a PARTIAL cycle. It now ends the monitor task (supervisor restart, one SYSTEM entry), as utc_now() at :329 already did. **Lead: this changes which entry that event logs; I landed it as the brief and the row prescribe.** Exact-age test (frozen clock) added, red on a planted `>=`.
3. The NTP resync cadence is now TickSeconds `_cadence`; while out of sync it is held at its last synced value, as the tick count was. Red: 3610, not 3600 (:3351). Two existing tests encoded tick counting (360 ticks with no time passing; loop started a tick late), so they now step the clock and start the loop first. Both pass on the old src too (proved with the base asy_ntp_client). Effect: every device, STA; a dropped tick no longer delays the resync.
5. The hazard run's raw frames now go out through writefrom() from a buffer with CRC room. Red: 25 copies (1 crossing + 24 sweep values; the finding said 26). TX bytes are identical to the base code in both modes (83 frames, same digests; f2r/wire/). Effect: dev only, STA/AP. dev's buses use CRCPass, so dev copied nothing before either.
6. Light --color-neutral #6b7280 -> #666c7a: 4.53:1 on neutral-bg (was 4.16), 5.26:1 on surface; dark unchanged at 5.16. The pair is now in _PAIRS, red first at 4.16. Website readers pass. vitest not run: tests_js has no reference to the token.
7. The six catalog codes each get a test (5 base, using a RAM store with no file; UART_WRONG_KIND as an ACK at a listener). Each failed on its own planted code. OF-103's equality test was already there: tests/test_asy_neopixel_driver.py:1140-1145.

Handed back, item 4 (OF-246), unchanged. C.7 already decides it:
- SPECIFICATION.md:3161-3162: "each layer that meets the fault keeps its own entry (owner, 2026-10-02)".
- :3539-3540: a failed cycle persists the streak entry beside the driver's read code.
- :3630: "alternating codes and reboots are outside the rule".
- The facts: SGP40 E READ (sgp40:476) + E STREAK (base:589), 1000 ms period (:625), max_module_error 5. A 4-in-5 pattern gives 8 entries per 5 s, one per 625 ms, against 627 ms per chunk write (:6653).

Red check, waits on the lead (allow-list): tests_scripts/test_counter_steps.py:28. The `_EXEMPT` row NTPClient._ntp_sec_count is orphaned; test_every_exempt_and_pending_entry_is_still_an_unguarded_step fails, delete the row.

Findings:
- Silent-failure scan, class 5, new: asy_ntp_client.py:385 `_unsynced_wait_s += _NTP_CHECK_INTERV` still counts delivered ticks. The unsynced retry is 10 s late per dropped tick. Out of my item's scope.
- Otherwise the scan found nothing new.
- T's tests/test_digital_twin_uart_link.py:193 passes a frame with no CRC room. It is right only because dev has no CRC; T could size it like the ack beside it.
- For D3: SPECIFICATION.md:3059-3060 "which do not call them yet" is stale already (system_service:378, :466 call them), not caused by my change.

Checks:
- 42 importer files (per-device ×6) at -1 and 32768: 104 runs, all pass, zero memory markers.
- ruff clean; mypy main, twin, host and conftest passes clean. S/shared/typings is absent and the offline cache had no stubs, so I installed the pinned stubs from the index into S/u35/laneR/f2r/typings (kept for reuse).
- 42 tests_scripts readers: 2987 pass, 1 red (above).
- mpy-cross output differs for all 4 src files, as expected for behaviour changes.

After-times (-1/32768): ntp 23.67/24.17, uart_comm 61.5/62.3, system_service 24.2/25.6 (U32 table 24.9/26.4), fram_manager 0.62/1.46, notification 0.14/0.17. uart_link_driver is 3.76/5.43 against the U32 table's 2.35/2.43, but that table is stale: CF1b measured this file at 3.53/4.91. At -1 it ran 3.74 with my tests before the fix. **Lead: please do a paired check at 32768 for uart_link_driver.**

Deviations: no twin CI runs (CHECKLIST 2). Logs: S/u35/laneR/f2r/. RUNS.md lines are all closed.
nothing of mine is running
