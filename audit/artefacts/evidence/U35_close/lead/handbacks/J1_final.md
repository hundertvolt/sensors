U35 lane J: hand-back. Commit `20b84f9` on audit/u35-j (one commit on cd8f077; not pushed). Tests only, no product file touched. Worktree clean, nothing uncommitted.

**Items**
- **1. Done:** `tests_scripts/test_firmware_write_sites.py`. The table pins **9 sites**:
  - `ConfigManager._write_file` open w, and `ConfigManager.delete_file` os.remove;
  - seven SCD30 `_send_command` sites: 0x5403 temp offset, 0x4600 interval, 0x0010 ambient pressure, 0x5102 altitude, 0x5204 forced recal, 0x5306 self-cal, 0x0104 stop.
  - The generated modules of all six devices hold no site today.
- **2. Done:** `tests_scripts/test_uart_link_bench_only.py`. The allow-set is the board with `[device] bench = true` rather than the literal "dev", because `test_no_variant_literals.py` refuses a quoted device name and its allowlist only shrinks (agent, 2026-10-22). Floors: the check fails if no TOML declares uart_link, and it requires the bench board's own firmware to import and freeze the driver.
- **3. Done, with one gap from the brief's wording.** Counts pinned:
  - a PUT changing n of the four compared keys (TempOffset, MeasInterval, Altitude, SelfCal) sends exactly n storing frames, n = 0..4;
  - setup() sends none;
  - the whole boot start sequence (reader setup, both tasks with the chip init and its soft reset, the trigger timer, a recovery's soft reset) sends **0**. Its frames, pinned in order: D100, D304, 5403 read, 4600 read, D304.
  - **Gap:** "a PUT changing none sends none" fails for three keys. AmbPres (0x0010) and ForceCalRef (0x5204) send one frame per PUT even when the value is unchanged; that is already pinned at `test_ambpres_and_forcecalref_always_write`. ContMeas false sends one 0x0104 every time. I added no "none" pin for these three and did not touch the driver.
- **4. Done:** `tests/test_asy_system_service_gate.py`, with the rig import kept.
  - **Problem found:** `scripts/test.sh` runs files in parallel, and importing `test_asy_system_service` re-runs its module-level `TmpScratch("sysservice")`. That constructor deletes `tests/_tmp/sysservice`, which the other file may be using at that moment.
  - **What I did:** the gate file swaps in a `TmpScratch` subclass before the import, so its copy uses the key `sysservice_gate`. A third test pins that the swap took effect (agent, 2026-10-22).
  - **Cleaner fix, not in my files:** move `_Rig` into a `tests/` helper module.
  - No `tests_scripts` list needs the new file; every check finds test files by glob.

**Seen failing first and bites** (all planted in a scratch copy, nothing committed)
- Write sites: planted open "w", os.rename and an SCD30 altitude send each fail naming file:line. A removed os.remove fails as vanished. An `open(...,'w')` planted in codegen fails in every generated entry. Planted `open(p)` and `open(p,"rb")` stay green.
- UART link: a non-bench copy of dev.toml fails both tests.
- SCD30: making Altitude always-written fails the n-count test. A 0x0010 send planted in `setup()` fails the boot test.
- Gate: M's lock-free gate hunk fails the first test, `[False, True, True, False]`. The second test passes under that hunk; M's log shows it is bitten by the lock-removed-claim-kept variant instead. Removing the scratch swap fails the third test.

**Checks**
- SCD30 file: 133/133 at -1 and at 32768 (base 131/131). Gate file: 3/3 at both stages. Zero memory markers in every log.
- Write sites 20 passed; UART link 7 passed. Ruff clean. mypy clean in all three runs: main pass (266 files), main pass on `src tests tests_hardware/device_scripts` (232), host pass (308).
- The 17 scans, the 12 commit checks and the readers in one run: 1121 passed, 2 failed.
  - `test_suppression_form`: mine (the noqa lines lacked reasons), fixed.
  - `test_tunables_register`: the expected red, SPECIFICATION.md:11804 `config.flush_slice_bytes`.
  - After my last three edits (noqa reasons, the module alias, the D.15 reorder), re-ran the subset that reads them: 750 passed.
- `test_microtest` 24 passed, after aliasing the rig module (a module-level `test_*` name must be a function). `test_threshold_runner` 12 passed; the `test_test_sh` subset that globs `tests/` 10 passed.

**Times** (alternating base/head pairs, `nice -n 19`)
- The first two pairs showed head +2-3 s. Cause: the n-PUT test waited out the driver's real 50 ms command sleeps (2.0 s). Running it under FastAsyncSleep brings it to 5 ms; the boot test takes 45 ms.
- Final pair, base/head: -1 22.72/22.92 s, 32768 30.19/30.03 s, so no growth. Gate file 0.25-0.41 s.

**Silent-failure scan:** one new finding, class 3 (detection left to chance), mode "a check that matches nothing". The static scan cannot see an aliased `open` or a command passed through a local variable, and it does not cover `ext/` (microdot's only open, ext/microdot.py:828, is 'rb'). No other findings.

**Mode effects:** none in any mode or on any device, since only tests changed.

**Runs**
- The cut run's end line is appended to RUNS.md (rc=137, container restart) and the run was redone from the start.
- Re-runs pair.sh rc 0, pair2 rc 0, final_runs.sh rc 0 (its two rc=1 lines are the intended bites).
- Logs are in S/u35/laneJ/. Scratch copies deleted.

nothing of mine is running