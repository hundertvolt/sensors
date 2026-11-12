U35 lane C, block CR3 (device-script facts, the hardware tests' logs, the :861 ruling): hand-back

**Commit:** 9cb382c on audit/u35-cr, on top of 146df65. Not pushed. Nothing is uncommitted, and /dev/shm/cr3 has been removed.

**Counts:** 8,514 rows, 284 flagged. Verdicts: biting 8,356, justified 133, fixed 24 (CR 4, CR2 14, CR3 6), weak 1 (T4's :818, unchanged), open 0. Routed product findings: 0, because CR2's :861 route is withdrawn by the ruling.

**Item 1: all 42 rows are terminal.**
- 5 conformance probes are biting. The host assertion is in flash/test_chip_conformance.py :145/:150/:155/:161/:166: each test checks DONE=1 (:41) and finds no divergence over conformance.parse()/compare(). compare() itself is bitten by tests_scripts/test_twin_board.py:241.
- 3 are biting false flags: the facts are read through f-string keys (uart_crossover_recovery, unretrieved_task_exception_handler, wifi_country_code_reaction).
- 28 are justified: each fact is either evidence or implied by a fact that is asserted. Each reason is stated where the script is run (a trailing comment on the run line) or cites a statement already there (harness.py:669-670, the scripts' docstrings).
- 6 are fixed with 7 new host assertions:
  - test_bus_concurrency :125 and :130: sibling reads > 0 around the reset and the heater-off. Without them, the zero-failure checks pass when nothing was read.
  - :153: at least one read inside the reset rung's window.
  - :290: the baseline read succeeded.
  - test_reset_reasons :152 and :184: no_reset_after_ms is absent, as test_system_commands.py:230 already checks.
  - test_uart_crossover :234: _setup_ok(facts, "rxdmae_setup"), the same check as for mismatch_setup.
- **Bites:** on synthetic script output, the vacuous case passes the old test and fails the new one; the healthy case passes both (S/u35/laneC/cr3/bites.out). On the twin, the three tests it can run pass with the new assertions (twin_bus: 3 passed). The RXDMAE window only runs on silicon, and test_reset_reasons needs the bench, so those two have the synthetic bite only.
- Two other guards I drafted were reverted after reading src, so their rows are justified instead: the verify script's initialized fact (a failed setup already logs a RAM-only E entry, src/asy_print_log.py:404-407 and :427-428, so the exact-history check fails anyway); the erase race's seeded_system fact (the seed runs unconditionally in that state, and a raise prints "failure", which the test already asserts is absent).

**Item 2: classed, not landed** (agent, 2026-10-23, the conservative choice).
- All 99 tests are classed by reading their names, markers and first comments: 53 normal, 40 provoked, 6 unsettled. The list is in review.md's "Normal-situation scan" section.
- **Proposed shape for the bench (46 tests):** a function-scoped autouse fixture does a GET of errcount before and after each test and fails on any module's new E or W entry; a `provokes_log` marker carrying its reason exempts a test.
- **Why it is not landed:** the 19 hotspot tests run off the bridge, so their check can only happen at the module's bounds; the 6 unsettled tests need one bench errcount run to class; the flash tier (53 tests) has no REST, and its scripts own the chip. Its check would need a shared `logs` fact added to about 40 device scripts, plus a twin re-record.

**Item 3:** the rows at :363 and :371 are now "justified (owner decision)", with no product route. The scenario comment quotes the owner's words, with the decision marked as paraphrase.

**Checks:** ruff clean on the 15 changed files. Host mypy with a cold cache: clean, 308 files. Collect-only on the 12 changed hardware files: 99 of 111 collected. 32 tests_scripts readers plus the doc checks: 1,432 passed, 2 failed (the comment cap on my scenario comment, rewrapped, then cap, decision-vocabulary and citations passed (656); test_twin_record hash check red, expected, 15 host test files' recorded hashes no longer match, needs the lead's re-record). No MicroPython runs: the tests/ edit is comment-only. Silent-failure scan: no finding.

**Runs (in RUNS.md):** twin_bus rc=0 (29.8 s), readers rc=1 (the two reds above, both explained), collect rc=0.
**Left for the next block:** landing item 2's bench fixture and marker, and the flash tier's per-script logs fact; an open product question, unread: whether the boot after a commanded config reset logs W CONFIG_LOST (flash test_system_commands :117), a possible A.U35.37 (a).
**For D3:** none. **For T4:** :818 unchanged.
nothing of mine is running

[CR3's brief (blocks_c.md, lead, 2026-10-23), as printed in the lead's review: "Continue audit/u35-cr in S/wt-u35cr at 146df65; start state S/u35/handbacks/CR2_final.md, S/u35/laneC/cr/ds_keys.txt and review.md's open rows. 1. The 42 device-script rows from ds_keys.txt, each classed as CR2's item 2 states (a fact a host test asserts by key: biting, named; a fact no host test reads: the host test that runs the script asserts it by key, or the print is a stated diagnostic, justified in place); the five conformance probes: the host assertion over tests_hardware/conformance.py's parse found, or added. Host-side changes bitten on the host (synthetic output, as CR2 bit new_entries()) and through TwinBoard where it runs the script. 2. The 99 hardware tests naming no log (A.U35.37 (c)): prefer one shared check over 99 edits ... a GET only, no clear, no write. Bitten on the host with synthetic counters. If the classing or the shape cannot be settled conservatively, hand back the classed list and the proposed shape instead of landing it. 3. The lead's ruling on tests/_sensortask_scenarios.py:861 (LEAD NOTES 138): not (a). The first boot after a reflash is the owner's own case, "handled gracefully (CRC mismatch → treated as empty and re-initialised, no crash, no error flood — OR35)" (owner, 2026-09-26, OR47.a (2)), which bounds the entries; the test's bound is that decision. The row becomes "justified (owner decision)", no product route; the scenario's comment at :364-365 quotes the owner's words instead of the bare tag."]
