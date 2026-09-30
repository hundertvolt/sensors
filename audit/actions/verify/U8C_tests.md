# A-L verify U8C_tests — U8C + U8C2, files under `tests/` (HEAD 854675a)

Scope: every hit-table row, action and ledger/register-fix item of `audit/actions/U8C.md` and
`audit/actions/U8C2.md` whose file is under `tests/` (70 files, 1,921 rows: 1,268 U8C + 653 U8C2; actions
A.U8C.01-A.U8C.43, A.U8C2.01-A.U8C2.15, A.U8C2.50, the `tests/` entries of A.U8C2.51). Code at `854675a` equals
`a4766a9` outside `audit/` (`git diff --stat a4766a9 HEAD -- . ':!audit'` empty), so both files' line numbers apply.
Scripts: `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/al/verifyU8C_tests/`
(`mysearch.py` C.0.1, `myfam.py` G1-G15, `cmp1.py`/`cmp2.py` comparisons, `actcheck.py`/`chgcheck.py` action
cross-checks), written from the rule texts, not from the authors' scripts.

## Completeness (check 1)

- **C.0.1** (own `mysearch.py`): 2,265 hits, identical key for key to U8C's table (const 290, const-c 253, call 599,
  kw 915, param 60, assert 131, deadline 17), every line the literal's own. Note: C.0.1 kind 1 has no "nonzero"
  clause, and U8C correctly keeps the eight `const … = 0` hits (`tests/machine.py:19, :213, :605`,
  `tests/network.py:11, :14`, `tests/test_asy_uart_comm.py:36`, `tests/test_uart_comm_hazard.py:40`, one in
  `tests_hardware/`).
- **G1-G15** (own `myfam.py`, U8C2's rules as written, same callee index): 995 (family, site) keys on 984 sites;
  U8C2's table + dropped list give 997 on 986. The only difference is two G15 keys U8C2 has and the stated rule
  excludes (V.U8C_tests.01). Every other key matches, family for family; no site in both U8C's and U8C2's tables;
  no duplicate row; every line is the literal's own.
- **Arithmetic 997 − 140 = 857 vs 846**: the table's family column sums to 857 appearances (G4 220, G10 120,
  G12 94, G6 70, G9 69, G2 55, G1 43, G3 41, G7 27, G6s 26, G15 25, G8 20, G13 19, G14 13, G5 7, G7b 4, G11 4);
  the 11 are the sites listed under two families, each counted once:
  `tests/_webserver_concurrency_scenarios.py:185, :199` (G6s/G9), `tests/test_asy_isl29125_driver.py:642` (G4/G6),
  `:1828` (G4/G6s), `tests/test_digital_twin_isl29125_autorange.py:363, :364, :400` (G4/G6),
  `tests_hardware/device_scripts/heap_under_connection_ceiling.py:32`, `serving_at_default_gc.py:71` (G6s/G9),
  `uart_link_under_concurrent_system_load.py:173` (G6/G9), `tests_hardware/flash/test_memory_stress.py:54` (G4/G6).
  The ledger's "new sites" column agrees (G6 75−5−5 = 65, G6s 26−1 = 25, G9 69−5 = 64). Reconciled; with
  V.U8C_tests.01 applied the true figures are 995 − 140 = 855 appearances, 844 sites.
- **Actions ↔ table** (`actcheck.py`, `chgcheck.py`): every tuned/mirror row of a `tests/` file is in its action's
  Site with the same ID and line, and every Site line is in the Change; the 13 deferred-U25 rows are named in their
  actions' Site as "deferred U25"; 323 new constants, no name clash with the file or between U8C and U8C2.

## Per-file results
