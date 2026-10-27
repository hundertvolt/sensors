# U35 lane C briefs (blocks_c.md), the parts the lead's context holds (recovered 2026-10-26)
[Lost: "All blocks" lines 1-9 and 21-29, the CR, CF1, CF2, CR2 and CE2 sections (their scope is re-derived from
audit/actions/U35.md: CR = A.U35.03 and A.U35.37; CF1 = A.U35.04, A.U35.35, A.U35.05's rest; CM = A.U35.08 and A.U35.09's
row; CE = A.U35.41 and OR16.a (3)). Line numbers refer to the lost heads.]

## All blocks (lines 10-20, as printed)
  `audit/sweeps/` derives every row; you read what it flags. Each row names its evidence (the script's finding, your
  reading, a plant); a row resting on the script alone says so ("scanner: no red flag"), never a verdict by assumption.
- A defect any row records takes the OR12.a path, never a note alone. In a test file (U35's): fixed here, the test's
  goal kept, the fix seen failing first on a plant in a scratch copy. In a product or tooling file: a finding with
  file:line, its failure scenario and the proposed fix, routed to the next unit in `audit/order/work_order.json` (from
  U35 on) whose files list holds the file, else U37; a U36 row carries its route only.
  [Superseded 2026-10-26 by the owner's "Firmware really complete, don't push fixes to future units": a product fix
  lands in U35.]
- Not yours while their blocks run: T4's files (`scripts/_digital_twin_ci_suite.py`, `scripts/_twin_process.py`,
  `scripts/run_digital_twin_ci.sh`, `tests/test_digital_twin_*.py`, `digital_twin/README.md`,
  `digital_twin/_fram_chip.py`) and N5's (`tests/test_digital_twin_machine.py`, `tests/_boot_contiguity_probe.py`,
  `tests/_twin_devices.py`); never `src/`, `SPECIFICATION.md` or another block's `audit/b3/` file.

## CM: audit/b3/matrices.md (A.U35.08, A.U35.09's row)
1. The assembly matrix: dimensions and values from `devices/*.toml` and `buildgen/validate.py`; the pairs computed by
   `audit/sweeps/pairs.py`; each pair shipped (the device carrying it) or a gap; a gap is closed by a `zz_test_*`
   fixture generated at test time and booted at L2 (never committed as a device), or, where a lower level proves it,
   there. More gap boots than about six: the set handed back with its cost.
2. The interaction matrix: actor × resource as the action lists them, existing cells mapped first (the bus-hazard
   files, the UART hazard file, the webserver concurrency scenarios, the OR119.a states, the bus-rung hazards); each
   cell its test (level), "independent" with its written reason, or `queue_c.md` for a silicon-only cell. A gap gets a
   forced-interleaving test (a gate or barrier fake, never a sleep count) at the lowest level; more than fit: the list.
3. A.U35.09's row: recombination × level, each cell its test or its reason (the two L2 scenarios are at
   `scripts/_digital_twin_scenarios.py:1304`, `:1310`).

## CE: audit/b3/e51.md (A.U35.41, OR16.a (3))
1. A.U35.41's verdict table checked against the tree, row by row: the carried-by change landed (site gone, or kept
   with its stated reason or the test that exercises it) or not (its finding routed).
2. Gate 2's coverage report (`S/u35/gate2/coverage.log` and the archive it names, taken at 7851668; each line
   re-located at 33d9ad8): every uncovered `src/` line classed as a register entry, covered elsewhere (the test that
   reaches it), unreachable (removal routed, or kept as an overridable or runtime-failure guard with its double or its
   reason), or a gap (a test here when the file is a test file's to cover, else routed).
3. For D3: E.5.1's register as it must read (only what stays, one line each with its reason) and the two sites of D3's
   item 5, in the hand-back. Not yours: SPECIFICATION.md.
[Gate 2's coverage log is lost with S/u35/gate2; the evidence snapshot holds lead/gate2.out only. The redo re-runs
the coverage tier on its base.]

## Amendment (lead, 2026-10-23): CM and CE start on 024390d (N5 merged); N5's device picks go to CM
CM and CE take base `024390d` instead of 33d9ad8. CM item 4: N5's hand-back (`S/u35/handbacks/N5_final.md`, item 2's
"Differs" list and `tests_scripts/test_fram_less_boot.py:92`, `:98`) names one-device picks whose picked device wires
the exercised part differently from other devices (FRAM size and address width, a chip alone on its bus or sharing it,
pins). Each is an assembly-matrix cell. Under the owner's decision (LEAD NOTES 130) and OR43.a (3) ... (superseded by
CM amendment 2). CM starts after T4a hands back, so `tests/test_digital_twin_*.py` are CM's then for this item only.

## CR3: see recovered/handbacks/CR3_final.md (its brief is quoted there).

## CE3 (lead, 2026-10-23): e51.md's 35 owed tests, after CE2
Continue `audit/u35-ce` in `S/wt-u35ce` at `8f504a4`; start state `S/u35/handbacks/CE2_final.md` and e51.md's action
column. The 35 rows (bmp3xx, config_manager, fram_manager, isl29125, scd30, sgp40, system_service, uart_comm,
uart_driver's 19, uart_link), each its test in its module's `tests/test_<module>.py`, seen failing first on a plant of
the lines it covers, its row naming the test; a row that turns out unreachable on reading is re-classed with its proof
and its removal routed. The UART files' tests change no wire byte and no protocol constant.

## CF1b (lead, 2026-10-23): faults.md's 206 unrun plants, cheaper
Continue `audit/u35-cf` in `S/wt-u35cf` at `328c80d`; start state `S/u35/handbacks/CF1_final.md` (its "What is left"
gives the driver's resume, stop and table commands). CF1 ran 11 of 217 plants; the cost was the widening of a survivor
to every importing file (30-35 min for base_classes or print_log, and the one widened K flip was equivalent).
The change of method (agent, 2026-10-23): the widening is dropped. A plant green on its module's own test files is
read first: equivalent (no observable change, its reason) or a gap in the module's direct tests, which every module
must have (A.U35.07); a gap gets its direct test in `tests/test_<module>.py`, the plant re-run red. A test elsewhere
that also catches it is not looked for. State it in faults.md's method line.
1. The 206 plants in that order: the named bites and the boot-entry five, the K rows from K.12 on, then the seeded picks.
2. A.U21.13's unpatched modlwip control run, last: one private Unix-port build in `/dev/shm` (never the shared
   toolchain's binaries or directories), the `tests/lwip_host` files run on it, the result recorded, the build removed.
   If the build needs more than one compile or touches anything shared, hand back its cost instead.
[Scope change sent to CF1b on 2026-10-23 (owner's Question 2): plants only for complex measurement checks (memory,
leaks, accumulation, timing bounds, soak, log gates, multi-layer), the named bites, the boot-entry plants, the K rows,
the modlwip control and the JS/twin/mock named items; the seeded plain-logic picks dropped.]

## CM amendment 2 (lead, 2026-10-23): base 0f9f07d; the owner's ruling on single-device picks
CM's base is `0f9f07d` (N5 and CE2 merged). Item 4 changes by the owner's decision (owner, 2026-10-23: "Single device
tests with different wiring should actually be avoided, so these tests should go for all devices."; said on N5's list of
one-device picks whose device wires the part differently): each pick in N5's "Differs" list and
`tests/test_fram_less_boot.py:92`, `:98` runs on every generated device that wires the part it exercises, its
assertions kept, not on one device and not only on one per wiring; the "covered elsewhere" route of the first
amendment is withdrawn. N5's "Match" picks stay as they are (the matrix deduplication the owner accepted, LEAD NOTES
130). The tests_scripts `DEVICE_NAMES[0]` sites are classed by script: where what a site checks differs per device, it
goes to every device; where it is identical, it stays. State each file's time before and after; a growth goes in the
hand-back with what makes it cheap where you found it (a build or boot shared across a file's cases, say), never a
dropped device.

## CR4 (lead, 2026-10-23): the hardware tests' log check, landed; CE3's silent-failure scan
Continue `audit/u35-cr` after merging the integration head (a merge, no rebase). Start state CR3_final.md and
review.md's "Normal-situation scan" section.
1. The bench tier's check, landed (agent, 2026-10-23, the lead's choice of CR3's proposed shape): a function-scoped
   autouse fixture reads every module's error counters by GET before and after each bench test and fails on a new E or
   W entry in any module, naming the module, the code and the test; a `provokes_log` marker carrying its reason exempts
   a test, and is put on each of CR3's 40 provoked tests (the reason read from the test, not invented). GET only: no
   clear, no reset, no write of any kind, FRAM included. The 6 unsettled tests get the check, not the marker: they are
   classed at the first bench run, and the README says so. The 19 hotspot tests, which run off the bridge, are checked
   at their module's bounds. Registered in `tests_hardware/conftest.py` with the repo's marker conventions. Bitten on
   the host with synthetic counters, and every bench file still collects (`--collect-only`).
2. The flash tier's per-script `logs` fact: if one helper can emit it for every script and one host check can read it,
   land it within the budget, bitten on synthetic output and through `TwinBoard`; otherwise hand back the plan with its
   cost. Do not re-record `twin_record.json` (the lead does it once at the close).
3. CHECKLIST 16's silent-failure scan over CE3's 9 test files: each finding fixed in the test, seen failing first on a
   plant, or "no finding" per file.

## CF1c (lead, 2026-10-23): CF1b's open rows (never launched)
1. The two exact-bound survivors left after F2 takes `src/asy_notification_service.py:230`: `src/asy_isl29125_driver.py:569`
   and `src/asy_neopixel_driver.py:184`. Each gets the driven or frozen-clock test faults.md proposes, red on the plant.
2. The three plants caught only by the file timeout (K.04 flip, asy_system_service.4, asy_uart_driver.5): a test whose
   wait has no bound is a defect under the standing no-hang rule. Give
   `test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset` and
   `test_a_caught_allocation_failure_in_a_poll_or_teardown_prints_its_own_text` a run bound, every assertion kept; the
   three re-plants then fail by assertion inside the bound, not by the timeout.
3. `named.pair_scan` (A.U3.11): re-target the plant at `tests_scripts/test_fault_or_warning_never_both.py` (M.TSC.111).
4. `named.fram_two_entries` (A.U3.04, dropped by the owner, FOLD_BRIEF F11 (7), quote its "OR140.a items" words): test a
   count the per-layer rule still requires, or row "not applicable: dropped by the owner" with the quote.
5. A.U21.13's unpatched modlwip control, last: first `make -n` with `BUILD=` and the overrides directory in `/dev/shm`
   shows no write outside `/dev/shm`; only then one compile, the `tests/lwip_host` files run on it, the result recorded,
   the build removed; otherwise hand back what it showed.
6. `src/asy_system_service.py:441` (F1: reachable by a cancel of the shutdown task, against CE3's "unreachable"): its
   direct test, which settles which reading holds; e51.md's row says so.
7. `tests/test_asy_uart_driver.py:2319`: rename to what it proves (a multi-round read), assertions unchanged.

## CM2 (lead, 2026-10-23; stopped by the usage limit, lost)
1. The red: `tests_scripts/test_twin_wiring_contract.py::test_every_key_a_consumer_reads_off_a_plan_is_declared`: give
   each comprehension its own scope, as Python 3 does; a planted undeclared key read still fails it.
2. The integration file's cost (165.4 → 302.9 s summed at -1): the driver-specific scenarios of one device job share one
   boot where their states allow it, every assertion and device kept.
3. Item 4's rest (bus_hazard's `_FRAM_DEVICE` tests, :714, :1069; fram :881; clock_jump :163, :194; ntp :376, :477; the
   scd30 and sgp40 helpers; hot_replug; launch), each on every device wiring its part, with the three per-device
   defects fixed in the tests (`machine.reset_peripherals()` per iteration; the bus_hazard port band reused per word,
   not widened; the bus built inside the run as the `_SHARED` cases do).
4. The bites, in a `/dev/shm` copy with the generated tree re-run after the plant; the SCD30 irq-11 plant again.
5. CHECKLIST 16 over the diff.

## CM3 (lead, 2026-10-23; never launched): the assembly matrix's gaps, booted (OR41.a asks all-pairs; "about six" was
the lead's valve): config-value dimensions added (SGP40 `BackupPeriod` 0, `WaitTimeNTP`, the notification window,
`DebugLevel`, every schema field switching a code path); pairs recomputed; each fixture valid under validate.py; a pair a
unit or L1 test proves needs no boot; the rest as `zz_test_*` fixtures in `tmp_path`, booted at L2 with the cheapest
proving boot (BOOT_DONE, zero markers, no unexpected E/W, the one or two GETs the pair's parts answer), both GC stages;
the risky "shared bus + shared FRAM + REST writes" case with a REST write in flight; the file's cost and critical-path
effect measured; bitten by a broken pair.
## CM4 (never launched): CM items 2 and 3 (the interaction matrix and the recombination row), as written above.
