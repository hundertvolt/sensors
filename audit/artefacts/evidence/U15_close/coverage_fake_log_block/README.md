# U15 gate coverage leg: a fake call log's one-block growth

- Verdict coverage run on 723b7c8 alone: 89/90 files; `test_asy_scd30_driver.py`
  `test_every_two_decimal_temperature_offset_is_sent_as_typed` raised `MemoryError: memory allocation failed, allocating
  32768 bytes` in `tests/machine.py` `_CallLog.append` (the list doubling from 2048 to 4096 entries). Plain build at
  -1 and 32768: 90/90.
- Reproduced alone (single file, build-settrace, 23 s): `before_coverage_test_asy_scd30_driver.log`.
- Fix: both fakes' call and wire logs kept in fixed-size chunks (256 entries / 512 bytes); the twin's 200-entry call log
  unchanged. After: the same single-file coverage run 124/124; the users of the logs (scd30, machine_uart_link, i2c
  driver, write counters, bus hazard multi-device) pass at -1 and 32768.
- Guard: `tests/_uart_link_contract.py` `_assert_fixed_occupancy` asserts the chunked storage for every log past one
  block; against the previous fakes it fails on both tiers ("wire_log: stored in one block of 4096").
