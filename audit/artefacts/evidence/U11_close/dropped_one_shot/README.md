# An armed reset kept the watchdog fed (SF-U11-05)

`SystemService._reboot()` armed the reset one-shot and returned; the supervisor kept feeding the watchdog. A one-shot the
scheduler drops (soft-timer callback dropped when the scheduler queue is full, Part F) never wakes `_reset_when_due()`:
no reset, storage paused for good, and every later reboot refused as "already armed". Part N `system.reset_delay_s`
already stated "nothing feeds during the countdown".

Test first: `tests/test_asy_system_service.py::test_an_armed_reset_stops_every_feed_so_a_dropped_one_shot_still_resets`
failed on the merged U11 tree before the fix (`dropped_one_shot_fail_first.log`: `AssertionError: 2`, the supervisor's
feed after the arm). Fix: `_force_watchdog_starve` latches once the timer is armed; 108/108 after it.
