X1 hand-back (lane X). Branch audit/u35-x in S/wt-u35x. I made one commit, 931e591, on top of 2360470. Nothing is pushed or uncommitted, no typings link is left, and nothing of mine is running. About 63 tool calls.

**Item 2, the NTP stand-ins (LEAD NOTES 55, twin half): applied in 931e591.**
- :1083 (test_a_restored_backup_reports_its_timestamp_without_ntp) stands for a real sync and reaches a VOC backup. Its stand-in did not set `_clock_valid`, so the backup got the unset stamp 0. The check `written is not None` let 0 through, so the test passed while proving "No timestamp". The check is now `assert written` (:1092), and the stand-in sets `module.ntp._clock_valid = True` (:1085).
- Seen failing first on arzi at -1: "the backup was written without a timestamp (0) although the clock was set".
- The other three stand-ins keep only Synced and the RTC flag. Each now has a comment saying why: the midnight window (:1165), the stopped SCD30 (:1226) and the boot without NTP (:1298). A probe run on arzi logged every ntp_clock_valid() call. None of these three makes one. The backup test reads it as True, then False after its reboot.
- Effect per mode: tests only. STA, AP, Silent, Off and USB are unchanged on every device.
- Silent-failure scan: one class-4 finding at :1092 (the unset stamp 0 taken as a real value), new, fixed here.

**Item 1, test_lock_order's 9 reds: stopped, not committed (CHECKLIST 3).** The clean form needs a file outside my set. tests/test_digital_twin_uart_link.py (lane U's) calls `_sweep_fields(bus, …)` at :192 and plants `_write_raw(bus, frame)` at :180-182. Keeping an unused `bus` parameter in src fails ruff's unused-argument rule (ARG002).
- A ready patch for all three files is at S/u35/laneX/p1.patch. `git apply --check` passes on 931e591.
- What it does: `_read_raw` and `_write_raw` take the lock through `self._uart`. They use the protocol module's own `bus = self._uart; if bus is None: return None/False` form. That guard never fires, because `_run_hazards()` returns first. All four methods drop the `bus` parameter.
- Verified with the patch:
  - lock-order findings drop from 2 to none;
  - ruff is clean;
  - mypy is clean (cold cache) in the main pass, both forms, and the twin pass, on a patched copy;
  - every file passes at -1 and at 32768 with zero memory markers: link driver 46/46, webserver service 224/224, twin link 22/22.
- My first 32768 runs failed (link driver 4, twin link 1). They had loaded the unpatched module: the threshold runner's folder comes first on sys.path. The TypeErrors name the old signatures. With the patched module put first on MICROPYPATH, all three files are green.
- mpy-cross compare (v1.29.0, -march=armv6m): 3680 B before, 3693 B after. Ignoring line tables and qstr index shifts, exactly 5 of 26 code objects change: _cross_both_ends, _read_raw, _run_hazards, _sweep_fields and _write_raw. No byte on the wire changes.
- Effect per mode: dev only, in STA and AP (the hazard run is a dispatch-only REST request). Silent, Off and USB are unchanged; other devices have no link.
- The patch moves `_two_initiations()` from :218 to :221. test_task_inventory's red cites :218.
- Not run on the patch: the readers of asy_uart_link_driver (test_buildgen_driver_registry, test_buildgen_wiring, test_device_tomls, test_memory_catalog, test_lint_ceilings, test_digital_twin_scenarios). They need to run once it is applied.

**Checks on 931e591**
- ruff is clean. The twin mypy pass is rc=0 (cold cache, 52 files).
- One pytest run of the 12 checks, test_lock_order, test_task_inventory and the readers (test_device_tomls, test_gc_collect_sites): 903 passed, 14 failed. None names my file:
  - test_tunables_register: asy_config_manager.py:71 config.flush_slice_bytes has no Part N row, plus the UART-link tags (waits on D2);
  - test_lock_order ×9: asy_uart_link_driver.py:164 and :228 (waits on the patch);
  - test_task_inventory ×4: asy_uart_link_driver.py:218, `_two_initiations()` has no C.9 row (waits on D2).

**Times:** The integration file on arzi went from 60.09 s at base to 60.12 s at -1, and ran 60.60 s at 32768 (the lead's table gives 63.5 s). The other five devices took 20-23 s at both stages. All flat.

**Decisions (agent, 2026-10-22)**
- I stopped item 1 and handed over the patch, rather than edit the twin link file.
- The narrowing uses the protocol module's None-guard form, not an assert or a type: ignore.
- The backup test's check is `assert written`, since 0 is the unset stamp (RestoreTS shows "No timestamp").
- The three stand-ins are named with why rather than given the flag, as the brief asks, based on the probe.

**Runs (all have RUNS.md lines)**
- rebuild rc=0; base integration on arzi rc=0; the seen-failing run rc=1 (as planned); probe rc=0.
- integ chain, 12 runs, all rc=0.
- checks1 rc=1 (the reds above); mypy twin pass rc=0; mypy passes on the patched copy rc=0.
- p1chain: every -1 run rc=0. Its 32768 reds were the loading artefact explained above; p1chain2 re-ran that stage, rc=0 for all three files.

Logs are in S/u35/laneX/:
- integ_*.log and integ.sum: the integration runs;
- seen_integ_arzi_m1.log: the seen-failing run; probe_integ_arzi_m1.log: the probe;
- checks1.log: the checks;
- p1.patch, p1/, lockorder_overlay.txt, mpy/compare.txt, p1_*.log and p2_*.log: the patch, its sources and its runs.