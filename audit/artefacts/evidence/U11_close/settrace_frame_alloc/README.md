# CI `unit-tests-coverage` red on 8d44fd1: build-settrace allocates a frame per Python call (SF-U11-11)

CI run 37638089345, job `unit-tests-coverage` (the only job running `build-settrace`): two files failed one test each,
`test_the_reports_outputs_allocate_nothing` in `tests/test_digital_twin_unix_port_unretrieved_report.py` (128) and
`tests/test_asy_system_service.py` ((0, 128)). Every other job, the standard-build suite at both GC stages included, passed.
- Reproduced locally (`before_fix_*_settrace.log`), and also with no tracer installed: the cost is the binary's, not the
  coverage recorder's. `alloc_probe*.py` on both builds: every Python call, an empty one included, allocates 128 B on
  build-settrace and 0 B on build-standard (`alloc_probe*_<build>.txt`). Source: v1.29.0 `py/vm.c:157-163` FRAME_ENTER
  calls `mp_prof_frame_enter()` unconditionally, which allocates a frame object (`py/profile.c:190-196`); SPECIFICATION.md
  Part E.5.2 already states the flag allocates per call. The firmware never carries the flag: no product defect.
- Fix (test-only): each test measures one empty two-argument Python call on the running binary and requires the report
  to cost exactly that (0 on every real build). `after_fix_*`: the fixed tests pass on both builds and both GC stages;
  a planted 4-element list in either report body fails them on both builds ((64, 0) standard, (192, 128) settrace).
- `after_fix_ss_*_seq` were run one at a time: an earlier attempt ran five copies of the system-service file at once in
  one worktree, and four config tests failed because every copy shares `tests/_tmp/sysservice` (the runner's fault,
  rerun sequentially, all pass).
- Process: the local gate gains the `--coverage` suite on build-settrace, the leg CI runs and the gate did not.
