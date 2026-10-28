# The boot-clear wrap test after U13's SCL lead-in (U14, lane T)

What failed: `tests/test_asy_i2c_driver.py` `test_the_boot_clear_ends_at_the_bus_timeout_on_the_fake_clock`, 111/112
at both GC stages (`before_*.log`, run in lane T's worktree once U13's lane I commit `0dd79bb` was merged, 2026-10-07
14:10). The failing line (1413) asserted the old SCL pulse log for a held SCL (`[0, 1]`: one ineffective pulse).

Why: the test was right for the boot clear it was written against. U13 (`0dd79bb`) made the boot clear wait for SCL
before reading SDA, as the runtime clear does, so a held SCL now ends at the bus timeout as `SCL_HELD` with no pulse.
No product fault: the expectation moved, the 2**30 crossing the test proves did not.

Fix: commit `64838c8` (U14 lane T): a held SCL expects no pulse and `SCL_HELD` alone; a clock let go inside the
timeout costs the 20 lead-in reads, then one per pulse's release and the STOP's.

What proves it: `after_*.log`, lane T's runs of the updated file at 14:11 (one minute before the commit), 112/112
under both names the run gave them (`plain`, `thr`).
