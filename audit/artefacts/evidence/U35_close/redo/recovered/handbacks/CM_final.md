CM hand-back (branch audit/u35-cm, worktree S/wt-u35cm, base 0f9f07d). Not pushed. Nothing uncommitted.
Commit: d24e225 "U35 lane CM: one-device picks of a differently wired part run on every device wiring it" (7 test files plus audit/sweeps/pairs.py, audit/sweeps/device_picks.py, audit/b3/matrices.md).
[Diff stat: audit/b3/matrices.md +256; audit/sweeps/device_picks.py +73; audit/sweeps/pairs.py +71; tests/_twin_devices.py 14; tests/test_digital_twin_network_neopixel.py 105; tests/test_digital_twin_sensortask_integration.py 17; tests/test_neopixel_wifi_integration.py 21; tests_scripts/test_digital_twin_scenarios.py 27; tests_scripts/test_fram_less_boot.py 13; tests_scripts/test_twin_wiring_contract.py +11.]

Item 4 (owner's ruling), partly done:
- New `devices_with()` in tests/_twin_devices.py. Its contract test failed first on 0f9f07d (AttributeError: no devices_with).
- Now runs on every device that wires the part, assertions kept:
  - integration `_driver_specific()`: all its callers, including :552, which was not on N5's list (agent, 2026-10-23)
  - network_neopixel :630
  - neopixel_wifi `_a_device_with_a_neopixel` (not on N5's list)
  - tests_scripts/test_fram_less_boot.py :92/:98, parametrized
  - scenarios `_lag_run` and its 4 tests: device_picks.py measured that they differ per device (dev's smallest hard consumer is 925 ms, the others 6000; dev's link roles)
- All of these are green on all 6 devices at gc -1 and 32768, with zero memory markers.
- tests_scripts `DEVICE_NAMES[0]`: 68 functions classed by script. 5 changed (`_lag_run`), 63 stay: the device is only a vehicle for a mechanism. Two of those 63 were computed identical on all 6 (definitions :419/:440, scenarios :230).
- Times in s (gc -1 / 32768, before → after):
  - integration, summed over the 6 jobs: 165.4/168.5 → 302.9/307.3. arzi is unchanged at 61; every other job grew about 27 s, because it now boots per scenario. It would be cheaper with one boot shared across a job's driver-specific scenarios.
  - network_neopixel: 14.71/14.85 → 16.26/16.49 (+11 %), growth from the 6 devices.
  - neopixel_wifi: 2.77/2.98 → 3.82/4.30
  - fram_less_boot: 0.91 → 2.02
  - scenarios and wiring_contract: unchanged.
- No bite yet for the committed widenings: a src/ plant makes build/generated_src stale, so every boot refuses. A bite needs the plant copy regenerated.
- One plant did run: the SCD30 irq-11 plant. The new scd30 file failed on dev and the old one passed (55/55); that file was then reverted, see below.

Item 4 still open: bus_hazard (`_FRAM_DEVICE` with 10 tests, :714, :1069), fram :881, clock_jump :163/:194, ntp :376/:477, scd30 helper, sgp40 helper, hot_replug, launch. I rewrote them as device loops, ran them, and reverted them. Three per-device defects, recorded in matrices.md:
- (1) Each device iteration inherits the previous board. `configure_fram_state_path` raises (bus_hazard's two reboot tests, clock_jump :194). The fix is `machine.reset_peripherals()` per iteration.
- (2) The bus_hazard port band (19400-19419): 24 scd30 boots plus 6 erase boots overrun it and cascade. Ports must be reused per word, otherwise the band is the lead's call (I never raise a bound).
- (3) Neighbour chips' timers leave a task parked on shared buses: dev's ISL29125 and SCD30, wozi's BMP3xx (the scd30 helper's 4 tests, bus_hazard :714). The bus should be built inside the run, as the `_SHARED` cases do.
- The fifth fault was my own script swallowing the `__main__` block, not a test defect.

Item 1, partly done: pairs.py finds 211 pairs, 66 shipped, 145 gaps; each row is in matrices.md. A greedy all-pairs cover needs 12 zz_test_ fixtures, each an L2 boot (about 20-60 s per device job). That is over "about six", so the set comes back to you with its cost. Each row's validity under validate.py is unchecked. The behaviour-switching config values are not yet a dimension.
Items 2 and 3 not started: no interaction-matrix rows, no recombination row.

Red, not mine: tests_scripts/test_twin_wiring_contract.py::test_every_key_a_consumer_reads_off_a_plan_is_declared is red on 0f9f07d itself. Its scanner gives both comprehensions' `a` one scope, so it reads tests/test_digital_twin_machine.py:121 (N5's `_board_plan`, the spi comprehension) as I2CAttachment['max_size']. It is a scanner false positive and waits on the lead or a later block. My new contract test passes.

Checks: ruff clean; mypy main (no args and src tests), twin and host passes clean, with a temporary typings symlink, removed; the 12 before-commit checks plus no_variant_literals, level_containment and device_tomls: 884 passed; comment cap, scenarios, vocabulary and citations re-run after the last edit: 762 passed. Silent-failure scan: I only self-checked the diff for vacuous loops and skips (every device list asserts non-empty); I did not re-read the scan document.
Runs: batches before, before2, sf, after and the bite_* runs, all with start and exit lines in RUNS.md. The /dev/shm copies are removed.
For D3: the integration file's docstring now says driver-specific scenarios run on every device wiring them, citing SPECIFICATION.md E.2.1, so E.2.1 needs the same sentence.
nothing of mine is running
