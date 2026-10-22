T1 hand-back (lane T, block 1). Branch audit/u34-t in S/wt-u34t, from 147ea3f. Nothing uncommitted, nothing pushed.

**Commits**
- 1b3c13c "U34 lane T: the explicit-Any baselines keep only modules that still hold it". Touches pyproject.toml (baseline list), host_typecheck.ini and tests_scripts/test_mypy_any_baseline.py.
- 334acd0 "U34 lane T: the CPY001 reason names an attribution header, SPDX where a license is named". Touches pyproject.toml only.

**Steps**
- **R-2 (applied, partly against P1's grep):** I ran the six typecheck.sh mypy runs with every exemption dropped (cold cache, logs in S/u34/laneT/noex.*.log). Every finding is `explicit-any`. mypy counts `Callable[..., T]` and an Any base class as explicit Any, which grep did not find.
  - **5 entries removed:** allocation_need_per_source, uart_crossover_exchange, uart_crossover_recovery and uart_driver_read_never_blocks_the_loop from pyproject.toml; [mypy-http_client] from host_typecheck.ini.
  - **3 entries kept, because they still show findings:**
    - serving_at_default_gc (main pass)
    - conftest (host pass; it is tests_hardware/conftest.py)
    - scripts._hardware_verdict (host pass)
  - The bench-conftest and conftest single-file checks show 0 findings even with no exemptions.
- **R-3 (applied):** a `_RESIDUAL` set per pass, plus a parametrized subset guard and a tmp-config self-test.
  - The sets are the 16 modules still showing findings (11 main / 2 twin / 3 host), not R-3's 13. The 3 extra are the entries R-2 kept. Decision (agent, 2026-10-21).
  - Its private helpers now follow D.15 order (AST-identical). Two helper comments swapped so neither points forward (no meaning change).
- **R-4 (applied):** no change to mypy_path or to the :21-24 comment.
- **R-13 / step 23 (confirmed):** all six ANN401 entries still fire under `ruff --select ANN401` with per-file-ignores cleared, 111 hits in total: tests/machine.py 3, digital_twin/machine.py 1, test_asy_uart_comm 15, test_asy_uart_driver 16, _bus_hazard_catalog 13, _sensortask_scenarios 63. They stay.
- **Step 22 (applied):** the CPY001 comment now has the attribution-header wording; the line is 120 characters, within the file's 121 maximum.
- **Step 27 (partly):** the baseline block stays, with 11 modules.
- **Step 28 (partly):** 3 host sections remain.
- **Step 37 (confirmed, no edit):** both twin entries still hold explicit Any; digital_twin/typecheck.ini is unchanged.
- **Steps 25 and 26 (check-only):** the full scripts/typecheck.sh passed.

**Seen failing and bites**
- The guard failed at the old configs, naming exactly the 4 device scripts (pyproject) and http_client (host). Log: S/u34/laneT/seen_failing.log.
- Bite: an exemption planted in a scratch copy of pyproject.toml and of the twin ini was named by the guard. Log: S/u34/laneT/bite.log. Nothing planted was committed.

**Checks (all run after `git add`)**
- ruff clean, after I added a COM812 trailing comma.
- Host mypy pass clean.
- The 12 before-commit checks plus test_lint_type_scopes, test_config_paths_resolve and test_ruff_exemptions_live: 829 passed.
- The one warning is test_citations' "datasheets/ submodule not initialised". It comes from the environment, not from my change.
- No red checks. No MemoryError and no "memory allocation failed" in any output.

**Times (base / head, run alternately)**
- Six mypy runs, total: 36.9 and 36.2 s base, 34.1 and 28.8 s head.
- test_mypy_any_baseline.py: 0.37 / 0.27 / 0.25 s base, 0.35 / 0.27 / 0.28 s head.
- Full scripts/typecheck.sh after the removals: rc=0, 10 passed, 25.4 s.

**How I ran typecheck.sh (agent, 2026-10-21)**
- $W/.venv is a `cp -a` of wt-lint's venv, whose uv.lock is identical to 147ea3f's, with the shebangs rewritten inside the copy.
- $W/typings is a real copy of S/shared/typings, so the script's stub install never writes to the shared tree.
- Both are gitignored and left in place for T2's lint.sh and typecheck.sh. Remove them with literal paths at the lane's end. I removed .mypy_cache.

**Silent-failure scan (my 4 files, classes 1-7, modes STA/AP/Silent/Off/USB):** no runtime effect in any mode; type-check config and a host test only. One class-3 note, covered by R-3: a residual row left behind after its module is cleared would let that exemption come back unflagged. Remove the row together with the module; U37's "nothing sets false" form closes it.

**Allowlist rows orphaned:** none. **Relay lines:** none, since the brief asks for none.

**Runs:** two run6 batches and timing.sh, logged in RUNS.md, all exit 0. Nothing of mine is running.

**State for T2:** BACKLOG.md, the R-14 measurement, lint.sh, the rest of T's readers and the 17 scans are still open. The step 30 test is in its subset form.

**Remaining exemptions, by pass, with explicit-Any sites (the same at base and head) and the config lines that go with each.** When a module leaves, its `_RESIDUAL` row in tests_scripts/test_mypy_any_baseline.py:16-34 should go too.

*Main pass (pyproject.toml): block :417-433; its comment :418-419 goes with the last entry.*
- _boot_contiguity_probe (:421): tests/_boot_contiguity_probe.py:42,150
- _bus_hazard_catalog (:422; ANN401 :275, comment :272-274 shared with scenarios): tests/_bus_hazard_catalog.py:162,205,211,223,257,262,266,292,301,305,330,342,348,419,426,740
- _sensortask_scenarios (:423; ANN401 :276): tests/_sensortask_scenarios.py:97,108,111,192,204,211,223,231,244,258,292,302,320,324,332,336,347,357,476,515,546,551,658,663,671,727,780,788,789,833,886,990,1130,1163,1177,1195,1282,1285,1286,1466,1491,1498,1515,1523,1629,1726,1749,1768,1771,1852,1942,1948,1954,1959,1964,1992,2002,2007,2025,2096,2100,2104,2114,2123,2130,2135,2136,2163,2169,2194,2536,2570,2587,2592,2597,2704,2852
- _uart_link_contract (:424): tests/_uart_link_contract.py:21
- asy_system_service (:425): src/asy_system_service.py:229,230,297,480,744 (5 sites; P1's grep said 7)
- machine (:426; ANN401 in :263, comment :261-262 shared with the twin's machine): tests/machine.py:251,261,270,276,722,857,1483
- serving_at_default_gc (:427): tests_hardware/device_scripts/serving_at_default_gc.py:32 (`Callable[..., Awaitable[object]]`)
- test_asy_uart_comm (:428; ANN401 :270, comment :267-269 shared with driver): tests/test_asy_uart_comm.py:145,150,330,692,787,1713,1792,1845,1881,1966,2109,2173,2360,2778,2780,2905,2979,3002,3058,3089,3134,3135,3221,3225,3227
- test_asy_uart_driver (:429; ANN401 :271): tests/test_asy_uart_driver.py:84,147,389,685,699,704,1295,1706,1742,1830,1939,1997,2012,2380,2401,2405,2443,2542,2573,2792,2801,2883
- test_bus_hazard_generated (:430): tests/test_bus_hazard_generated.py:44,67,77,87,99,148,165
- test_bus_hazard_multi_device (:431): tests/test_bus_hazard_multi_device.py:326,398,522,527

*Twin pass (digital_twin/typecheck.ini): comment :35-36 and :32's "the baseline below exempts…" clause go with the last entry.*
- machine (:37-38; pyproject ANN401 entry in :264): digital_twin/machine.py:134,422,467
- test_digital_twin_bus_hazard_concurrency (:39-40): tests/test_digital_twin_bus_hazard_concurrency.py:210,293,335,346

*Host pass (host_typecheck.ini): comment :43-44 goes with the last entry.*
- conftest (:45-46): tests_hardware/conftest.py:149,185,518 (`Callable[..., None]` note callables)
- scripts._hardware_verdict (:48-49): scripts/_hardware_verdict.py:73 (Any base `Summary`, from the bare import at :22; R-4 routes that fix to U37)
- test_cross_browser_smoke_probe (:51-52): tests_scripts/test_cross_browser_smoke_probe.py:33,138,149,153,163,172,178