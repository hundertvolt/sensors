# Lane A's runs (U15)

`runtests.sh` runs each named file at gc.threshold -1 and 32768 in its own network namespace and counts memory-error
lines. `run1.txt` (16:33) and `run2.txt`/`run3.txt` are lane A's tree; `run4.txt` (17:05) and `run5.txt` (17:13) the
merged lane tree (A with B, C and D's code). In `run4.txt` the twin ladder case
`test_a_sustained_fault_on_one_twin_chip_climbs_to_the_bus_clear_and_recovers_once_cleared` fails at both stages
(18/19) and the twin sensortask file fails on lane B's `:377` tuple (14/15, fixed at the merge); `run5.txt` has the
twin hazard file 19/19, the multi-device tier 18/18 and the generated tier 36/36 at both stages, all zero memory-error
lines. `scan_notes.md` is the lane's silent-failure scan.

Root cause of `run4.txt`'s ladder failure (lane A's account, 2026-10-07, on the lead's question): a defect in the then
uncommitted test, no driver at fault. `_ladder_run` injected the faults before the task graph started, so the SGP40's
setup read failed and `_init_failed()` ran the controller rung at once: the "one bus rung" wait passed through the setup
path, the streak loop exited at 0, and the run ended before BMP3XX's first cycle (`Pres` None, the failing assert). The
committed test (7893eb1) waits for both readers' first samples before injecting, asserts the SGP40 streak is nonzero
after the rungs, and checks the sibling's ErrCount 0 and exactly one heater-off W14. The earlier pre-merge "seen failing"
runs of ladder cases (a) and (b) ran the defective form, so they are not fail-first evidence for the committed tests;
the lead's planted-defect runs (`../integration/ladder_plants/`) are.
