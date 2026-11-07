# U25 v1: the lead's rulings on the refresh agent's six points (agent, 2026-10-14)

1. A-3 ACCEPTED: MN removes a twin pending-list entry (`tests/test_digital_twin_machine.py:84-89`,
   `tests_scripts/test_fake_surface_conformance.py:27`) only in the commit whose change makes that entry's check pass,
   since the exact-equality check forces it; it only removes, never adds, and reports each line. A narrow reading of
   CHECKLIST 4: every other list stays the lead's.
2. A-35 ACCEPTED, refined: an out-of-set finding's target is the next unit whose work-order file list
   (`audit/order/work_order.json`) holds its file; none such: the lead names it at U25's close in the open findings.
3. A-36 ACCEPTED: SH stays one lane (a split adds a lane's fixed cost for no parallel gain, CONCURRENCY rule 13).
4. A-28 ACCEPTED: the moved offline NTP writer imports the product's `config_filename()` (one source, as the UDP shim's
   import of `asy_udp_socket`).
5. A-29 ACCEPTED: `tests_scripts/test_isl29125_copies.py` covers only the copies `test_const_mirrors.py` does not.
6. `<W3>` ACCEPTED as D's base (`<W2>` plus the lead step).
7. Launch hold (lead, for the base table's accuracy): no heavy process of a lane (rebuild, test, lint, typecheck, npm,
   pytest) until `S/u25/base_times.tsv` exists; reading, worktree setup and writing tests first are allowed meanwhile.
8. (agent, 2026-10-14) `tests_scripts/test_device_tomls.py` (in no lane's set) joins P's set: P's wrapper and `_DEVICES`
   removal turns its `:156-178` glob/regex red, so the change that breaks it carries the edit; it keeps covering every
   device's test family (through the per-device dispatch), never less.
9. (agent, 2026-10-14) `inject_hang(times<1)` silently accepted (`digital_twin/_fault_injection.py:35`, C's scan): C fixes
   it in its final (its own file), seen failing first, refused like `inject_fault`'s `times<1`.
10. (agent, 2026-10-14) `tests/_digital_twin_construction_scenarios.py` (P's, P done) joins G's set for wave 2: its new
   `boot_sequence_matches_the_generated_expectation` scenario boots dev's real main() with the UART drivers' own
   real select.poll() (MN's after-each check: "a real select.poll() queried a UART fake 1 times"); G wires the bounded
   pollers between build_system and the setups as the runner does, reusing the runner's helpers, never a clone.
