# Planted plain-subtraction tick code (U14, lane T)

What the plants are: scratch copies of five tick sites with `ticks_diff()`/`ticks_add()` replaced by plain
subtraction or addition, each diff against the tree the crossing tests were written on (`f351490` for the I2C,
ISL29125 and UART files, `d4067a0` for the system service). They were run in scratch only, never committed.

What failed (lane T's reports; the run logs were not kept): every new crossing test failed on the plants of commit
`21b0126` (I2C SCL waits, ISL29125 settle, UART hold-off). On the system-service plants the two tests of `df7603a`
read `([200, 100], [0, 1, 2, 3])` for the trigger stagger and `(False, False, False, False)` for the storage-pause
deadline instead of the values the same run gives far from the wrap.

Why it matters: a crossing test that passes on the plant would prove nothing about the wrap; these show the tests
bite. No product defect was found: every shipped site already used `ticks_diff()`/`ticks_add()`.

What proves it: the landed tests pass on the real sources at both GC stages (`test_ticks_rollover.py` 22/22,
`test_asy_system_service.py` 123/123, `test_asy_i2c_driver.py` 111/111 at `21b0126`, `test_asy_isl29125_driver.py`
214/214, `test_asy_uart_comm.py` 152/152, lane T's counts).
