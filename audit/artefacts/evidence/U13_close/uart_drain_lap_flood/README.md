# UART boot drain: a flood that laps the receive ring ended the drain as "quiet"

Seen: lane U's run of its own files on its WIP tree (`lane_U_run1.txt`, before d5c769e): at gc.threshold 32768 three
drain checks of `tests/test_asy_uart_comm.py` failed (151 tests then; the drain ended without its W54 and its errno
history, e.g. `['E81']`); the reactive stage passed. The `test_sensortask_dev.py` lines in the same file are an
`ImportError: no module named 'frozen_html'` of that ad hoc run's path, not a product or test failure.
Cause: with the DMA ring a peer flood laps the ring, and the read reports a receive overrun; `_drain()` took that
failed read as a quiet window and stopped early, before its bound, so no drain warning was logged.
Fix: d5c769e (B57): `_drain()` counts a read that failed on an overrun as traffic (`rx_overruns` before and after),
draining to its bound and logging `wrnno` 54; new test `test_a_flood_that_laps_the_ring_drains_to_its_bound_not_as_quiet`.
Proof: `test_asy_uart_comm.py` 152/152 at both stages in lane U's final runs and in the U13 gate (89/89 files, both stages).
