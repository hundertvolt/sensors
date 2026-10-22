Y2 hand-back (lane Y, block 2). Branch audit/u35-y in S/wt-u35y, head 726ab46 (based on 6a59b8e). Nothing is uncommitted and nothing is pushed.

**Commits**
- b7d419a: steps 28, 29, 73, 74, 6's mock half, 76 and 77.
- 0d2ab4c: R-15 for _bus_hazard_catalog and test_bus_hazard_generated, which includes Y1's bhg_typed.diff. Both baseline lines, both _RESIDUAL rows and the catalog's ANN401 entry are gone; the ANN401 comment now names only the scenarios module (no meaning change).
- 726ab46: R-15 for test_bus_hazard_multi_device, with its baseline line and _RESIDUAL row (it had no ANN401 entry).

**Steps: all applied, with two deviations**
- 28: the catalog adapters have `default_address(i2c)`, read from each driver's own I2CDevice, and `releases_bus_mid_read`, set True only for sgp40.
  - Deviation (agent, 2026-10-21): `exercise_raises` and `releases_bus_mid_read` moved to `I2CHazardAdapter.declare()`. Otherwise the constructor needs 10 arguments, and ruff's PLR0913 ceiling is 8. No exemption was added.
- 29: added `sibling_inside_window()`. The switch floor now applies only to a bus with no flagged occupant.
- 73: both `switches >= 2` checks are replaced by the window check.
- 74 and 6: the 0x00-filtered assert and its comment are deleted, and so is the lone-BMP mock test. The section header names the device script as its guard.
- 76: the bus-fault test runs under `wait_for(..., _ISOLATION_BOUND_S)` (tag `l1.bus_fault_isolation_bound_s = 5`) and asserts `bus_lock` is free afterwards. The reserved-address test loops every adapter's `default_address`.
- 77: both SPI tests use a real FRAM_SPI from `make_fram_manager()`; the overrun test runs under the same bound.
  - Deviation (agent, 2026-10-21): the FRAM sits on CS 1 and the other device on CS 6, because that is how the shared builder places them. The step text had them the other way round; I swapped them rather than copying the builder.
- Typing (agent, 2026-10-21): each per-driver function takes `object` and narrows it with an `isinstance` assert. No cast and no ignore.

**Seen failing on planted defects** (copies in S/u35/laneY/bite*, none committed):
- SGP40 holding the bus across its conversion:
  - both interleave tests fail with "no sibling transaction landed inside an SGP40 conversion window";
  - the generated dev and wozi i2c1 all-occupants tests fail the same way;
  - the base file's old switch floor still passed on this plant.
- I2C bus lock leaked on an error: the bus-fault test fails at the 5 s bound with its message.
- sgp40 default address 0x78: the reserved-address test names sgp40.
- FRAM_SPI entering on another holder's lock: "the FRAM's block session ran while another device held its CS asserted".
- FRAM_SPI leaking its bus lock: the overrun test fails at the bound.

**Red checks, both expected**
- test_decision_vocabulary::test_the_allowlist_only_shrinks: the row at tests_scripts/_decision_vocab_allowlist.txt:293 ("And BMP3xx's own address must never appear…") is now orphaned. The lead deletes it.
- test_tunables_register: red only on "tests/test_bus_hazard_multi_device.py:71: l1.bus_fault_isolation_bound_s is tagged but has no … Part N row" (R-17, D's 5f97080).

**Other checks**
- Every other check of the 12 passed, plus ruff_exemptions_live (814 passed); ruff is clean.
- scripts/typecheck.sh after each module commit: rc=0, 10/10.
- Readers (ci_workflow, config_paths_resolve, lint_type_scopes, no_variant_literals, preview_server, script_metadata_pins, suppression_form, tool_pins, typecheck_sh): 136 passed.
- No relay lines written. Zero MemoryError and zero "memory allocation failed" in every log.

**Baseline now:**
- main pass: 7 modules (_boot_contiguity_probe, _sensortask_scenarios, _uart_link_contract, asy_system_service, machine, test_asy_uart_comm, test_asy_uart_driver);
- twin pass: machine;
- host pass: scripts._hardware_verdict.

**Disk-full window (17:05-17:15):**
- Repeated after it: every bite, the paired times, typecheck and the commit checks.
- The early 32768 runs had failed with rc=2 (mktemp hit ENOSPC); those are replaced by the repeat.
- `git status` was clean and `git show` reads b7d419a whole; the commit message was checked complete.
- One `git fsck` reported a missing blob that none of my commits or index entries use, and a second fsck was clean.

**Times (base/head, s):**

| file | -1 | 32768 |
|---|---|---|
| test_bus_hazard_generated | 63.58/63.35 | 63.60/63.64 |
| test_bus_hazard_multi_device | 3.25/3.08 | 3.86/3.58 |

All passed (39/39; 22/22, down from 23 because of the deleted mock test). Nothing grew.

**Silent-failure scan** of my three files: none found; these are test-only changes. Effect per mode: none in STA, AP, Silent, Off or USB, on any device.

**Open for the lead: D.15 module-level order.** Both modules were already out of order at base: the checker, run on them as src paths, reports `i2c_const` before `_bmp_data6` and `_gather` before `_across_offsets`. My edits keep the classes in order. A whole-module reorder of the two files was not done; it needs its own commit, owner to be decided (agent, 2026-10-21).

**State for Y3:** OF-32 is first, then the two UART files' Any. The worktree's .venv and typings/ copies stay until the lane ends.

Runs: batch1 (rc=0; its 32768 legs were refused for disk space) and batch2 (rc=0). Both are logged in RUNS.md. Nothing of mine is running.
