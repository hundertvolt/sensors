# U7 close: what failed on the way, and why

## First gate (2421a80): 22 tests_scripts failures at both GC stages

`first_gate_gc_default_failures.txt`, `first_gate_gc_32768_failures.txt` (the run's own listing and summary block).

- 20 errors in `test_hardware_runners.py` and 1 failure in `test_summary_block.py`: `git commit` in a scratch
  repository exited 128. Root cause: this host's global git config signs every commit through a signer that needs the
  network (`commit.gpgsign=true`, `gpg.ssh.program`), and the gate runs inside `unshare -n`; reproduced with one
  `unshare -n git commit` in an empty repository ("failed to write commit object"). The lanes ran the same tests
  outside a namespace, where signing worked. The tests were not hermetic: a developer's own git config decided them.
  Fixed: both helpers run git with `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`; rerun inside
  `unshare -n`: 766 passed.
- 1 failure in `test_import_placement.py`: the follow-up that replaced the inline-table skip imported `tomllib` inside
  two test functions. Fixed: imported at module top, which also retired two older pending entries for the same import.

No firmware defect; both are test-apparatus faults the gate's own environment exposed.

## Second gate (1ad00b2), GC 32768: one neopixel test

`rerun_gc32768_neopixel_failure.txt`. `test_overlay_write_deferred_while_ramp_holds_the_overlay_lock` failed at
`assert driver.led_overl_lock.locked() is True`, 0.02 s of real sleep into a 0.1 s ramp: any wake-up later than
~80 ms finds the ramp already finished. The run shared the host with `npm test`'s live twins and three agents'
single-file test runs. This is SF-U5-05's signature (`U5_neopixel_wakeup_latency/`): a fixed real-time wait with
tens of ms of slack, failing under load, a different test each time; U5 measured the VM delaying every sleeping
process's wake-up at once by 36-220 ms. No product change in U7 touches the driver or its tests. The stage was rerun
on a quieter host (below); the fix is driven time (U35), which U9 starts for this file.

## The final gate (1ad00b2), on a quiet host

Both `scripts/test.sh` stages: 88/88 MicroPython files, 3867 tests; `tests_scripts` 2743 passed, 6 skipped (the opt-in
ARM firmware compile, which CI's `firmware-build-verify` runs); zero memory markers, no retried file. The twin suite on
all six devices (from the first gate, unchanged code under test since): 236-302 checks each, every one passed, Run 11
on one boot. `npm test`: 1082 passed, 5 skipped, each named with its reason in the run's own summary block (the four
enum options already shown on `dev`, the SSID resubmit on `arzi`). Lint and the three typecheck passes clean.
