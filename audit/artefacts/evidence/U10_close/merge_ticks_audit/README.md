# The merged U10 tree's ticks-audit failure

The first full run on the merged lanes (5ba961e, both GC stages) failed one test,
`tests/test_ticks_rollover.py::test_every_known_ticks_user_is_actually_covered_by_this_audit`:
"asy_udp_socket.py no longer measures elapsed time - update _KNOWN_TICKS_USERS".

Root cause: the UDP socket's `ready()` now bounds its poll with `asyncio.wait_for_ms` (lane B,
c7a9727), so the module has no `ticks_ms()` left; the audit's user list is lane A's file, and no lane
ran the other's test. The test did its job. Fix: the module leaves the list (63029cf); 7/7 after.
`gate_failure_gc-1.log` is the failing output (identical at gc.threshold 32768).
