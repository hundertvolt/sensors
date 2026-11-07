U30 lane G hand-back. Commit f221308 on audit/u30-g (worktree S/wt-u30g, from 5ba138c, not pushed). Logs and scratch: S/u30/laneG/ (batch1.log, batch2b.log, x01/, x01b/, of187/, gcsites_seen_failing_shim.log, mypy_all.log).
Steps: 19 applied. scripts/_check_gc_collect_sites.py now checks src/, tests/, digital_twin/, tests_hardware/ and the generated modules (each boot entry: one module-level gc.threshold(<int literal>)) for collect, threshold-set, disable and enable. It has 47 rows, each naming its category, and device scripts may set their own stage. R-31: an empty scope, no device, a device that fails to generate or a file that fails to parse exits 2; a row whose file is gone is stale. The modules are built once per lint run: a fresh stamped build/generated_src/ is read, a stale one never. 110 applied, with X01. 141 and 142: their U30 parts applied. Landed 22-28 and 131: rows re-derived (relay). OF-04 evidence: uart_idle_poll_rate.py:65 and :107, uart_link_under_concurrent_system_load.py:256-260, test_uart_crossover.py:152.
Findings: OF-01 is a fact (`listener_cancelled`) that the host test fails on. OF-03 counts `fram_absent` and the host asserts 0. OF-196 and OF-202 fixed; OF-205: the check takes about 1.06 s over 8x the source. R-28/OF-187: per-death slope between settled floors, under 32 B; the 2048 B check kept. R-29/OF-47: scenarios run without wall-clock bounds, every wait counted. R-27: OF-149 and OF-188 did not reproduce in 6 settrace runs; recorded.
X01 root cause: a heap reading inside a run counts blocks held only at that moment (measured: a burst's run keeps about 2.2 KB that the next run frees). The faulted hammer now reads 3 windows after a 10-failure warm-up and takes the least. Bites: base with a planted 688 B one-off fails (25.6 B/failure); new passes it; a planted 16 B/failure leak fails new (66 B). FRAM: the 40-cycle loop retains nothing per cycle (alloc 472,608 B at both 40 and 400 cycles). The old exhaustion came from the fake's capped SPI log; no root cause in src/asy_fram_manager.py.
Decisions (agent, 2026-10-20):
- R-29: a hang is the per-file timeout's, whose abort names the test.
- uart_link_under_concurrent_system_load.py `_main`'s collect removed: no reading follows it.
- test_lint_sh's one-tool-failing runs stub the checker; the clean run links every tree it reads.
- test_uart_comm_hazard.py was not D.15-ordered at base (81 functions, 13 headed sections). I add no function, so I did not reorder it; my other files are D.15-ordered.
Seen failing first:
- the new checker tests: 59 of 64 fail on an API shim of the old checker;
- test_lint_sh: 5 cases fail;
- the live checker: 37 sites, then 26 after my fixes;
- the slope check against a planted leak: 72 B/death.
Red, waiting on others:
- test_gc_collect_sites live case and test_lint_sh clean run: the checker exits 1 on 26 threshold calls in tests/test_asy_webserver_service.py (lane N step 105, W1).
- test_tunables_register (lead, Part N): SPECIFICATION.md:11020 Sites and five withdrawn rows :11391/:11392/:11395/:11398/:11399.
- test_import_placement pending lines :63, :64, :67-:70 (lead).
- test_twin_record (lead re-record).
Relay: 4 lines under ## G (extra rows, pending lines, Part N, live count).
Times (after vs base, -1/32768):
- test_fram_integration: 1.2-1.3 / 1.7-1.8 s (1.32 / 1.80 s)
- test_uart_comm_hazard: 103.9 / 115.9 s (105.8 / 112.4 s; +3.1 %)
- test_digital_twin_uart_link: 55.7 / 67.9 s (69.1 / 79.8 s)
- twin integration on arzi: 118.1-119.3 / 119.8-121.4 s (118.4 / 120.4 s); other devices 21.7-25.1 s
- test_gc_collect_sites: 1.58-1.72 s (1.56 s)
- test_lint_sh: 1.9-2.3 s (3.68 s)
Proof: every run exit 0 with 0 markers. FRAM 10 + 10; twin integration on arzi 10 + 10; the other five devices 1 + 1 each; settrace on all six; hazard and twin link at both stages.
Checks: ruff clean; mypy main (with and without args), twin, host and conftest passes clean; the other convention checks pass; collect-only tests_hardware 196/226.
Owed to X: SPECIFICATION.md:8323-8335 (I.4(f.1)'s checker paragraph) and CLAUDE.md:397-398 are now stale. BACKLOG needs a chroot-list line for the scripts/ change.
Scan: my files, all classes. No new defect: the ignored park-settle bool in uart_idle_poll_rate.py is caught by the host's idle-round band check. Effect per mode: test and tooling only, no firmware effect in STA, AP, Silent, Off or USB. The device scripts are bench-only and were not run (first run at H37).
Runs: all logged in RUNS.md. Two runs were cut, both logged: the jitter experiment hit its time limit, and I killed the A/B loop by pid. Nothing of mine is running.
