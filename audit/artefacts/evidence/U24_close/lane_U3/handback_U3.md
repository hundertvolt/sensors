
######## SubagentHandback 2026-10-13T20:13:46.489Z
U24 lane U3 hand-back. Branch audit/u24-u3, not pushed. Commits: 53186ac (W1, the migration) and b69328f (final: the banner, the setup asserts, the value checks). Logs are in S/u24/laneU3/: runs/, bite/, checks_*/, mypy_*.log, seen_failing_banner.log.

**Steps**
- Applied:
  - Step 99: TEST_HELP.023, TEST_UNIT.168, .169 (C), .178 (with A.S0930.03: both CRC modes), .267, and TWIN.158's U24 part (harness, banner, comment).
  - Also: 12 (bounds kept, no new tunable), 18, 39, 229, 231, 232, 216, 198, 333, 334, 285, 288, 291, 292, 247, 254, 6/201, 203, 43/44, 242/243, 40/49/202, 245.
- Already landed, verified: 199 (test_asy_uart_comm.py:464); 31 (range sweeps gone, `_SRC` kept for :732); 217 (no `.cfg_schema` reads left); 200 (legacy/dev_drivers paths at :3025, :3029, :3129); 45 (config_manager:2941-3035); 244 (system_service:1270, :1321); 246 (:1936, :2546); 57 (src/asy_system_service.py:306-309, :606-611).
- Partly: A.U24.73. test_asy_uart_comm.py (26 lines) and test_asy_uart_driver.py (21 lines) keep `Any` in their `**kwargs` builders, for the reason pyproject.toml:275 already gives (no Unpack).

**Deviations**
- rp2.py's `_FIELDS` is renamed `_CTRL_FIELDS`: it only shares a name with a src const, so there is nothing to read with src_const.
- The J.3 wire copies stay the protocol's own copy, each line pinned with `# pins` (A.U24.01 (3)).
- Pair's unused `**comm_kwargs` is dropped (no caller; PLR0913 blocks spelling them out).
- test_the_erase_unit_mirror_matches_the_source is removed, since the value is now read from source.
- `_pump` stays local (5 settle yields, not tick()'s 2).
- The CRC-mode registration reuses `register_both_crc_modes` instead of a copy (A-15).
- Helpers in the test files are not re-sorted by D.15.

**Seen failing first, and bites**
- Pin rule, on the old fake: test_asy_uart_driver.py:248 (new) and :237. Pin rule now in the fake; :178 fixed to UART1 on 8/9, so :245 is green.
- Banner: test_asy_uart_link_driver.py:258 failed on `b'dev-uart-crossover'`.
- The 24 uncaught resets and the uart_driver :245/:259/:310 reds were red in the base sweep.
- Bites, each a planted product change in a scratch copy:
  - build_pair accepted a failed setup before the fix and fails after, in both pair builders.
  - In-memory logger check; RegionBuffer has no lock (:325); error count saturates (:287); per-level printing.
  - Link FRAM write-through (:449); unknown key, file read back (:2982); corrupted frame costs one failure (:358).
  - Heap windows: uart_comm grew 8000/10080/7936 B per window; twin leak tests retained 41984 and 100096 B.

**Red checks**
- Lead rows: test_decision_vocabulary — `_decision_vocab_allowlist.txt:395` and `:412` retire, besides J's and T's rows.
- Others' rows only:
  - test_import_placement: F's and T's 21 rows.
  - test_tunables_register: X's two rows.
  - test_microtest and test_const_mirrors: other lanes' files; mine scan clean (0 asyncio.run, 0 public builders, 0 mirrors; 11 reads, 25 cited).
- mypy main: 36 errors in 10 files, all F's consumer errors; mine are cleared. Twin and host passes clean. ruff clean on all eight scopes.

**Scan findings (both new, both in H's tests/_async_harness.py)**
- Class 6, aborted file: `_reap` (:79-80) blocks forever when a task awaits the one a BaseException escaped from (Task.cancel forwards to it, extmod/asyncio/task.py:164-176). test_asy_system_service ran to its 300 s timeout. Worked around: `_sequence_done` now polls.
- Class 2: `created` (:31-37) holds every task until the run ends: 46,720 B over 200 tasks, against 0 with plain asyncio.run. My three heap tests now read the heap between runs.
- Covered or fixed: build_pair ignoring a failed setup (A.U24.31); the UART fake taking any pin (ruling 5); a create_task patch set outside a run, overridden by the harness.

**Facts owed**
- To X:
  - J.3: the wire copies are pinned.
  - J.7: the exerciser runs both CRC modes at L1, plus the CRC16 corrupted-frame case.
  - E.4: the UART fake applies rp2's TX/RX pin rule; CTS/RTS are not modelled.
  - Heap readings are taken between runs. No @tunable added.
- To Y: UART_C_PORT_CHANGELOG Class B row — banner `dev-uart-crossover` → `uart-crossover` (src/asy_uart_link_driver.py:35), dev only, no C impact.
- To the lead:
  - Any-baseline lines retire: pyproject.toml:446, 452, 453, 456, 463, 467, 471, 474, 488 and digital_twin/typecheck.ini:68-69 (trial run: no new errors).
  - ANN401: pyproject.toml:278 retires.
  - The banner reaches dev's firmware: the module is frozen, and dev is the only device wiring uart_link.
  - The two harness findings above.
  - "No per-test reset" comments made false by the reset hook, in other lanes' files: test_ticks_rollover.py:412 and i2c:50 (U4), _bus_hazard_catalog.py:49 (D), bmp3xx:158, isl29125:125, scd30:53, sgp40:146 (U1).

**After-times beyond 10 %** (-1 / 32768 / settrace)
- test_asy_uart_link_driver: 2.42 / 2.63 / 2.67 s against 1.72 / 1.81 s. The cause is 10 new cases, 9 of them CRC16 runs. The old 8 checks take 0.93 s against about 1.4 s before. I did not shorten it further.
- Below 10 %: system_service 24.7 / 29.2 / 31.3 s against 23.7 / 27.4 s.
- Framing under settrace takes 121 s; a copy of the base file took 166 s.
- No MemoryError in any run.

**Runs**
- Exit 0: 2 rebuilds; batches at -1 and 32768 (16 files); the final batch, 14 files at all three stages, all green; 2 check sweeps; mypy ×6; the bites, each ending in its expected FAIL.
- One unlogged 300 s run: the system_service hang, rc 124. It is logged late in RUNS.md.
- Nothing of mine is running.
