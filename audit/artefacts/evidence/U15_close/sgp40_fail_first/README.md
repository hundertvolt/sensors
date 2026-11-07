# SGP40 onto the shared base (U15, lane D)

What failed: `tests/test_asy_sgp40_driver.py` on the unchanged driver, `failfirst.txt`: 95/144, 49 failing (among
them the restore cycle whose read fails, the raw signal that cannot be measured, the heater-off rung and the
third serial word's CRC).

Fix: commit `ac96bf0`.

What proves it: `sgp_gc_default.out`/`sgp_gc_32768.out`, 144/144 after the code commit, and `d2_sgp_m1.out`/
`d2_sgp_32768.out`, 144/144 after the docs commit; zero memory-error lines.
