# Webserver read-timeout-then-cap check: first seen failing by U13 lane I

Seen: lane I's whole-suite sweep over `wt-u13i` (`sweep.sh`, `nice -n 19`, load average 4.8 on 4 cores, both GC stages;
file written 11:48): `tests/test_asy_webserver_service.py`
`test_a_read_timeout_then_a_capped_400_write_logs_the_request_cap_code` failed once at gc -1 (197/198), passed at 32768
and in four reruns, and both stages in the lane's next sweep (`lane_I_sweep_lines.txt`). Neither the file nor the module
differed from the base, so lane I reported it as load-sensitive timing to be root-caused.
Cause (U11, case 2 of `U11_close/scheduling_budget_root_cause/`): the test needs two wall-clock deadlines 100 ms apart to
fire in order; one host stall over 100 ms between them swaps the order, and the product then correctly logs the cap
(W50) without the read timeout (W49). Not a product defect.
Fix: U11's db1b8ac (a virtual `wait_for()` clock for this test), carried into U13 through the U11 base; the stall
sweep there passes 68/68 at both stages and planted defects still fail. The further exposed checks are OF-34 (U19).
