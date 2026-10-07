# I2C register access: the new tests fail first on the base driver

`new_tests_on_base_driver.txt`: lane I's new `tests/test_asy_i2c_driver.py` (a WIP form between 3fbac86 and 2965220),
run against the base `src/asy_i2c_driver.py` (identical at 081b60e and 81fa894): 67/107 pass, 40 fail. Among them the
silent-failure cases SF-A01/SF-A02 (SF-U13-01, -02): `test_a_nacked_data_byte_in_a_register_write_raises_eio_and_stores_nothing`,
`test_a_nacked_register_byte_raises_eio_instead_of_a_stale_read`, `test_a_short_ack_count_raises_eio_and_a_no_stop_write_then_sends_the_stop`;
the rest pin the new API (bus clear, `recover()`, bool answers, `get_register_bytes()`), absent from the base.
Why: the base wrote registers through `writeto_mem()`, which discards the short ACK count, and read them through
`readfrom_mem_into()`, which returns silently on a NACKed register byte (`extmod/machine_i2c.c`, v1.29.0; REGISTER rows
SF-A01/SF-A02). Fix: 2965220 (one `writeto()` with the count tested; a no-stop address write, then `readfrom_into()`).
Proof: `after_fix_lane_sweep.txt` (the file at both GC stages in the lane's own tree); the U13 gate runs it on the merge.
