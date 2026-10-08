# SCD30 onto the shared base (U15, lane B)

What failed: `tests/test_asy_scd30_driver.py` on the old driver, `u15b_before.txt`: 42/124, 82 failing.

Why: the old driver had no range gate, no not-ready warning, no FRC readiness, no config store and no recovery rung.

Fix: commit `343ab5f` (codes published first in `ae10506`).

What proves it: `u15b_final_-1.txt` and `u15b_final_32768.txt`, 124/124; `u15b_runall.log` and `runs/`, lane B's files
at both GC stages with zero memory-error lines (the notification, setter, NTP/FRAM-system, twin SCD30, six
sensortask files and the twin sensortask integration file); `u15b_runall.sh` is the runner.
