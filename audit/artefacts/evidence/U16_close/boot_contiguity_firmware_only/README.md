# The boot-contiguity check measured the FRAM fake's SPI log; now the firmware, with dev as its control

The first U16 close gate (37a88e6) failed `test_suppressing_the_emitted_collects_breaks_both_bounds[dev]`: with every
emitted collect suppressed, dev's batch median sat ~322 KB below the seam, past the 300 KB bound. `arms.py <tree>` prints
both arms per device with the check's own metrics; bisection across the U16 chain (`arms.log` and the lead's notes)
pinned it to the merge that brought U15's chunked fake logs (dev suppressed -8,608 before, 321,984 after).
`attr_probe.py`/`attr2.py` and the `attr_*.txt.gz` outputs attribute every new block of the batch to the fakes' logs or the
firmware: 92-96% were the FRAM fake's SPI log (an `("init", ...)` entry per transaction, the fake not overriding
`init()`). `big_probe.py`/`big_*.txt.gz`: before the merge that log was one doubling list whose 16 KB array sat ~150 KB above
the seam in the suppressed arm, pulling the median shallow - the control "worked" through the fake. `nolog_probe.py`,
`cap_probe.py`, `logs_probe.py`: firmware-only, wozi's control never separates (its batch makes ~2 KB of survivors).
Fix (a0bba37): the probe keeps the fakes' logs out of the mapped heap; control and ratio on dev; two new guards.
`meas.py`, `lf.py`: the firmware-only figures written into SPECIFICATION.md I.4(f.1) and the test file.
