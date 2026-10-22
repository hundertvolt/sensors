U28 lane P hand-back. Commit cc9682a on branch `audit/u28-p` (built on cf00454), in worktree S/wt-u28p. It touches 64 files, exactly files_P.txt, with nothing outside the set. Setup ran as the brief says: lock_check rc 0, rebuild rc 0, no command refused.

**Steps**
- Applied: 16, 29, 30, 32, 33, 36, 37/38, 39, 40, 87, 91, 93, 104, 105, 108, plus OF-151 and OF-159. The whole suppression table is done: 68 RUF100 noqa removed, E731 fixed in code, 68 E402 lines given ` - imported after the prewarm and the UDP shim`, 69 code lists sorted, the 7 src/ reasons written, the B904 comment added at `_http_client.py:127`.
- Already landed: 92 (`src/asy_wifi_service.py:283` already carries its trigger line).
- Verify rows: nothing written.

**Deviations**
- `asy_uart_comm._pair()`: the reason comment sits inside the `try`, directly above `:636`, and `:638`/`:639` carry trailing reasons. R1's form check only accepts the line directly above, so the M text's single line above the `try` would not pass.
- The device script's `:204` reason names the ring copy, which is what the wrapper actually times. The M text says the UART.
- I reworded 11 reasons from `# deliberate monkeypatch` to `# mocked by reassignment` while sorting their code lists. This makes their allow-list rows stale; I added nothing to the allow-list.
- The twin case cancels the SGP40's setup and measurement on each shared bus that carries one. A per-occupant version can't land inside a bus session: twin transfers are synchronous, and the BMP3XX read has no yield.

**Seen failing first**
- RUF100 / form / N802: `S/u28/laneP/api_reds.txt`.
- OF-159: at <API> the new test failed reading "listen read failed or was cancelled" (`red_of159_uart_comm.txt`).
- OF-151: the tightened sweep failed at <API> on the real driver. `reset()`'s RuntimeError had been swallowed on every run because the register fake does not clear CONFIG1-3. Now seeded.
  - Bite (`read_status` raises before the bus): the old sweep passes, the new one fails with "planted: raises before the bus".
- Twin case: passed at once, so I bit it in a scratch copy (`I2CDevice` keeps the bus on cancel). It fails with "dev i2c1: the SGP40 cancelled 1 turns in: the bus lock outlived the cancelled session".

**Checks**
- ruff over the four scopes: clean.
- Three mypy passes cold (main with no args and with args, twin, host): rc 0.
- 12 doc checks, suppression form, ruff exemptions live: green apart from the reds below.
- tests_scripts tier, 4 groups: red only on the lines below. `test_live_twin_ceiling_parser` failed only because my run lacked the pinned Node on PATH; with it, it passes 11/11, and the 5 other Node-using files are green.

**Red, waiting on others**
- `test_decision_vocabulary.py::test_the_allowlist_only_shrinks`: stale rows `_decision_vocab_allowlist.txt:200, 201, 228, 229, 283-288, 319`. Lead.
- `test_twin_record.py::test_every_entrys_hashes_are_the_current_files`: already red at <API> because R1 (5adc25c) changed a runner file; my runner, script and src/API changes add to it. Needs one `scripts/record_twin_instrument_runs.py` re-run after the merge. Lead or R.
- `test_no_variant_literals.py`: `tests_scripts/test_ruff_exemptions_live.py:66` ("dev") and `:145` (wozi). R.

**Scan findings**
- Class 4, "a sweep that swallows an early raise": `tests/test_asy_isl29125_driver.py:4063`, covered here, including the swallowed reset error. The class is clear project-wide (BMP3xx/SCD30 closed at U27; the SGP40 sweep swallows nothing).
- Class 3/7, "a CRC drop read as a silence": `src/asy_uart_comm.py:558` covered. **New, needs parking:** the same conflation at `:690-691` ("no answer to GET"), `:734-735` ("train stalled at chunk") and `:994-995` ("no ACK for frame").
- "A cancelled session that holds its bus": inherently safe (`Lockable.__aexit__` releases on every exit), now pinned at the twin tier too.
- "A suppression whose reason no longer holds": none.
- Both GC stages: zero `MemoryError` / "memory allocation failed" (a case-sensitive grep; the case-insensitive hits are test names).

**Owed**
- To X, in relay.md under "## P": the UART_C_PORT_CHANGELOG row (Python-internal), the SPEC D.6 group reasons, the C.8 twin-case line, the edited device scripts and the after-times.
- To R: the variant literals above.
- To the lead: the allow-list rows, the twin re-record and parking the new finding. No `@tunable` added; `_CANCEL_TURNS = 40` is untagged, as the mock tier's `_CANCEL_OFFSETS`.

**After-times**: none beyond 10 %. The twin bus-hazard file took 152.09/158.06 s against a base of 151.55/157.05.

**Runs** (all exited rc 0 unless stated)
- uart_comm, isl29125, ntp, math_helpers and the twin bus-hazard file, each at -1 and 32768.
- The 12 asy_uart_comm users at both stages: base_classes, uart_driver, uart_link_driver, readiness_gates, ticks_rollover, uart_comm_cancel_sweep, uart_comm_hazard, twin machine_uart, twin uart_comm_hazard, twin uart_field_sweep, twin uart_link, and twin sensortask_integration[dev].
- Bite runs exited rc 1, as intended.
- Tier groups exited rc 1 / 1 / 1 / 0, explained above; Node reruns rc 0.

Nothing of mine is still running, and the typings link is removed. Logs are in S/u28/laneP/.
