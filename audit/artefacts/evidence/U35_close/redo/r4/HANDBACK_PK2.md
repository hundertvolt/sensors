PK2 hand-back, written by the agent (Fri Nov  6 03:34:53 UTC 2026)
Commit `49cf0c2c` on `audit/pk2` (wt-pk2, parent `84a76ae8`), not pushed. Part K net +10 (cap 10), skill untouched;
SPEC 15 in / 5 out, the test file 6 in / 6 out. SPEC lines at `49cf0c2c`; every name cited was found in this tree.
1. K.3 item 1 SPEC:10187-10189 (+3/-2), cites C.14.2/L.6.3 (buildgen/model.py:138-148 reads `[instance.wiring]` apart
   from the fields `buildspec` checks; tags src/asy_sgp40_driver.py:137,142-143).
 - K.10 SPEC:10408-10411 (+4/-1): src/tests/digital_twin/buildgen (tests/microtest.py:12, tests/_error_codes.py:12), and
   the generator rerun per plant for a generated-module test (tests/_generated_tree.py:14 hashes every src/*.py).
 - K.6 SPEC:10315-10316 (+2), a bullet ending the buildgen-level list: `devices_with()` (tests_scripts/_devices.py:42).
 - K.4 SPEC:10237-10240 (+3/-1), folded into the bus-prerequisite parenthesis (src/asy_scd30_driver.py:178,
   src/asy_sgp40_driver.py:136).
2. K.0 SPEC:10122-10124 (+3/-1), "(agent, 2026-11-06)"; C.4.2's staleness rule is SPEC:3330-3335.
3. tests/test_digital_twin_hot_replug.py:35, 200-201: the sources are those of every `ValueRef` (src/asy_base_classes.py:
   68-73; buildgen/codegen.py:76-78 emits it) in `reader.__dict__` (as tests/_sensortask_scenarios.py:946), deduplicated by
   identity. Red then green: with SGP40's refs renamed (planted in src, reverted) the old lookup failed ("arzi's sgp40
   never read before the unplug"), the new one passed 2/2; the new one planted to find nothing failed the same way. Each
   device wires both refs to its scd30: one source, as before (sources gathered before the cast: twin mypy clean).
Checks: rebuild rc=0; lint_direct rc=0; mypy main/host/twin clean; hot_replug 2/2 at -1 and at 32768, no MemoryError;
21 tests_scripts files reading SPEC/the skill or scanning tests/: 939 passed.
tests_scripts tier whole at `49cf0c2c` (heavy slot taken 03:25, released 03:34): 6887 passed, 9 skipped, 0 failed.
nothing of mine is running
