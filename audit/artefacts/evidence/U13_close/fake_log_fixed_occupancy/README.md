# Retention check failed on a fake log that dropped its older half

Seen: U13 gate0 (fe24d3d, gate_v3), gc.threshold 32768: `tests/test_asy_uart_driver.py` `test_a_read_retains_nothing`
failed with `AssertionError: (1024, 0)` (`excerpt.txt`, full log `gate0_gc_32768.log.gz`). Lane U then saw three
retention checks fail by 832, 1,024 and 1,408 B with the fake log unmuted. The same log's one `tests_scripts` failure,
`test_tunables_register`, is lane D's Part N rows not yet merged (merged at 4c01972), expected at that point.
Cause: lane T's first bounded logs (4e96c23) dropped their older half when full, so `machine.mem32.log`'s live size swung
by up to 32 entries between two heap samples (+1,504 B as it grew 25 -> 41, -448 B as it shrank 59 -> 49); the checks
read that swing as retention. Not a driver defect.
Fix: 90d0d29 (lane T, on the lead's direction): every bounded fake log grows lazily to its cap, then overwrites its
oldest entry in place and counts it in `dropped`; 3b35c3a (lane U) removes the interim mute of 18d15fb and clears the
wire log in place. Pinned by `check_the_bounded_logs_keep_a_fixed_occupancy` (both fakes), seen failing on the halving form.
Proof: driver 143 and hazard 98 at both stages twice in a row unmuted (lane U); gate1 (4479fdc) 89/89 files at both stages.
