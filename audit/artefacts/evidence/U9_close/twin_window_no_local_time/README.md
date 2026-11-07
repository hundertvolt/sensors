# U9: the midnight-window twin test could not get a local time

**Failure.** U9's gate at both GC stages: `tests/test_digital_twin_sensortask_integration.py`
`test_the_notification_window_spanning_midnight_flashes_red` failed at `assert local is not None` after
`ntp.cettime()` (`gate_failure_gc-1.log`; the same at 32768).

**Cause.** `asy_ntp_client.cettime()` returns a `GMTimeStruct` only when `time.gmtime()` has rp2's 8 fields; the Unix
port's has 9 (`micropython -c "import time; print(len(time.gmtime()))"` prints 9), so on the twin it always returns
`None`. The unit-level tests already stand in rp2's shape (`tests/test_asy_ntp_client.py`'s cettime() section,
`tests/test_notification_neopixel_integration.py`'s `_Rp2Gmtime`); the new twin test did not.

**Fix.** The twin test swaps `asy_ntp_client.time` for the same 8-field stand-in and restores it: 14/14
(`after_the_shim.log`).

**Wider finding (open, OF-19).** The same mismatch means no twin run has a local time, so the generated notification
wiring never evaluates a window in any twin run or twin CI check.
