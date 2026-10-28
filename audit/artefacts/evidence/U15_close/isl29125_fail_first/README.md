# ISL29125 onto the shared base (U15, lane C, first commit)

What failed: `tests/test_asy_isl29125_driver.py` before `a5bdf44`, `u15c_before_saved.log`: 199/236, 37 failing; the
twin auto-range file at HEAD, `u15c_twin_head.log`: 15/19 (the dead-line re-arm, the unconverged calibration
warning, the `CalLight` bands, and the red scene, 11 cycles against a bound of 6).

Fix: commit `a5bdf44`: per-cycle shadow check, INT parking and re-arm, one threshold writer, `CalLight`, W75.

What proves it: `u15c_after.log`/`u15c_after_gc.log` 236/236 and `u15c_twin.log`/`u15c_twin_gc.log` 19/19, the two
GC stages, zero memory-error lines.
