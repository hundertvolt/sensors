CE3 hand-back (U35 lane C). Commit d255632 on audit/u35-ce, on top of 8f504a4. Not pushed. Nothing is uncommitted.
Counts: 35 rows, all settled. 30 got a test, 5 turned out unreachable (removal routed, no test), 0 left open.
Tests added (in each module's own tests/test_<module>.py). Every one went red on a plant of each of its lines first: 64 plants, one at a time, in a /dev/shm copy that is now removed.
- uart_driver, 16 rows, 5 tests:
  - overrun over every read form (:247-248, 561-562, 641, 669-670)
  - lap during a copy, through the `_LapOnCopy` DMA double (:256-257, 317-318, 521, 567-568, 623-624, 646, 680-681)
  - mid-line timeout (:665-666)
  - closed channel (:212-213, 298-299)
  - no ring (:342)
  - :225-226 is covered by three of these.
  - How the plants showed: discarded/overrun counts changed, a phantom byte appeared in the next read, a raw ValueError escaped, or a hang. :641 only shows through its console line, so the test asserts there is none.
- bmp3xx:705: the bus goes down between reset()'s two sessions.
- config_manager: :510 failed history clear; :559-560 field with no default (the test also asserts no file is written); :626-628 compare raising MemoryError, worded clear of the markers.
- fram_manager :168-170 and :424-425: set_values_sync() raising, UNEXPECTED logged, clear/write return False.
- isl29125: :325-328 and :829-832 arm/re-arm failure; :1519 refused reset.
- scd30: :319 and :761, a stop command on a down bus.
- sgp40:462: serialisation failure.
- uart_comm:562: a raising uart_listen() is logged and the loop backs off.
- uart_link:226-228: a cancel mid-way through the double initiation.
- The report_if_fatal() lines (fram 169/424, isl 326/830, uart_comm 562) are bitten by injecting a C-stack overflow.
- No product file, wire byte, protocol constant or flash/NVM write changed. No effect in any operating mode or on any device.
Rows whose bite needs a note:
- isl29125:1519: a down bus does reach the line, but planting it changes nothing, because :1521-1522 then raises the same error. The bite comes from a double where the bus refuses the write while it is up: the plant then shows a CONFIG read.
- scd30:319: the test goes through `_set_mgr_cfg()`, because through `_set_dict_cfg()` the key still came back Failed with the line planted.
Re-classed unreachable, removal routed to U36 (proofs are in e51.md and its JSON):
- asy_uart_driver.py:564-565, 620-621, 672-673 (`if not want:`): ready() reports POLLIN only for a non-zero `_rx_level()` (:716), and that level falls only when a read in the locked session consumes bytes. A re-init reports -1 and a deinit() makes ready() False. Proposed fix: drop the branches (a 0-byte copy is harmless).
- asy_scd30_driver.py:735: the write and the readinto share one session holding bus_lock (asy_i2c_driver.py:453). The only product path that clears the bus is init() under recover() (:386-392), and it takes the same lock.
- asy_system_service.py:441: `_supervisor_task` is set once (:792), before parked can be set (:538). Nothing cancels `_shutdown_task` (:387 is its only assignment).
Checks:
- All 9 edited files pass at GC -1, at 32768 and under settrace, with 0 memory markers and no .incomplete note.
- The settrace JSON shows all 30 tested rows executed; only the 5 unreachable rows stay uncovered. system_service:441 rests on the read alone; its file was not run in CE3.
- ruff is clean on all 9 files. The main mypy pass (cold cache, typings symlink, removed afterwards) is clean after 4 fixes: one ignore that was no longer needed, and three mocks whose signatures differ now carrying `[method-assign, assignment]`.
- Doc/convention checks (CE2's 38-file set): 1870 passed.
Timing: no file is more than 10% slower.
- The bmp3xx base row (12.48 s) was beaten by host load. Paired old/new runs: 14.02/13.74 s against 13.73/13.79 s.
- uart_link (3.6 s against the base's 1.72 s) was not paired. The base row predates CE2's added tests, and CE2's paired run showed no growth.
Runs: 15 run.sh runs, 30 RUNS.md lines, every one exited 0. The reds inside them were my own new tests while I was getting them right: a DMA registry reset closing earlier rings, a line read made outside the session, the fram/scd30 expectations, and 5 mypy findings. All are explained and fixed. There were also two short debug scripts (unshare, nice, under a minute each).
Left:
- The silent-failure scan (CHECKLIST 16) of my 9 files was not run (valve).
- tests/test_asy_uart_driver.py:2319: the name of test_the_allocating_read_yields_rather_than_spinning_on_an_empty_ring states the unreachable empty-ring premise. It still passes as a multi-round read test; rename it once U36 settles :564-565.
For D3: nothing new beyond CE2's lines. The E.5.1 register is unchanged by CE3.
nothing of mine is running
