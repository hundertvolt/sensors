K1 is done: commit `af38779` on `audit/u35-k1` (worktree `S/wt-u35k1`, from `bc0d77b`, not pushed). All 30 blocks in the 24 files are now at the cap, with no meaning change and no code change. Nothing is left over the cap.

**Blocks by kind (30)**
- **Rewrapped, words unchanged (8):** api_response:61, captive_dns:5, crc_checks:8, fram_driver:8, fram_driver:275, udp_socket:143, wifi_service:712, ntp_client:370 (this one gains a line: 2 to 3).
- **Tightened (6):**
  - api_reference:1: "every route `asy_webserver_service.ROUTES` registers" became "every `asy_webserver_service.ROUTES` route".
  - twin_wiring:90: "covering" became "with", "straight" dropped, "rather than" became "not", the slash list became "a, b and c", "no more than one" became "at most one".
  - print_log:354: "all the same" became "still".
  - uart_link_driver:42: "The hazard mode" became "Hazard mode", "through" became "via". The owner quote is verbatim.
  - udp_socket:123: "inside" became "in".
  - setup_toolchain:873: "its own major version and at least its picotool_VERSION_REQUIRED" became "its own major and at least picotool_VERSION_REQUIRED".
- **Split, one paragraph break each unless noted (16):**
  - twin_wiring:1: how the plan is derived | pointer to the twin-side docs.
  - version:1: the version source and bump rule | who consumes it.
  - base_classes:1, two breaks: the primitives | the sensor-driver base | the never-raises contract. This divides the module's one content list into its two families; it is the closest of these to a cut thought, so please give it a look.
  - bmp3xx:5: driver and layers | datasheets.
  - config_manager:1: storage and schema | never-raises.
  - fram_driver:5: the driver | naming origin and datasheet check.
  - fram_manager:1: chunk format | allocator, layout and contract.
  - isl29125:5: driver and layers | datasheet.
  - notification_service:1: the two classes | origin and LED coupling.
  - print_log:1: contents | history/console behaviour and never-raises.
  - scd30:5: driver, layers and published values | source datasheet. It also drops "see " before "SPECIFICATION.md Part C".
  - sgp40:5: driver, layers and shape | datasheet.
  - system_service:1: contents | never-raises and where the reset reason is stored.
  - system_service:5: the live debug-level push | the system-command reset being intended.
  - webserver_service:1: the service and its endpoints | the Microdot rule and doc pointers.
  - math_helpers:1: the functions | the None contract.
- **Moved:** none. **CAPMOVE lines:** none.

**`src/` line shifts (base to head, everything after the block moves).** The `-O3` output is byte-identical in all 14:
- base_classes 4-839 → 10-845; system_service 8-790 → 14-796 (its comment 5-7 is now 8-13)
- fram_driver 8-502 → 12-506; print_log 5-478 → 9-482
- config_manager 4-718 → 7-721; webserver_service 3-1109 → 6-1112; math_helpers 5-228 → 8-231
- bmp3xx 9-723 → 11-725; isl29125 9-1571 → 11-1573; scd30 9-921 → 11-923; sgp40 9-825 → 11-827; fram_manager 5-809 → 7-811; notification_service 5-382 → 7-384
- ntp_client 372-570 → 373-571

The other 6 `src/` files keep their line count, and their plain mpy-cross output is byte-identical (`S/u35/laneK/k1/mpy_compare.txt`).

**Checks** (logs in `S/u35/laneK/k1/`):
- `show.py 120`: `TOTAL 0`, exit 0.
- `verify.py`: `CODE-CHANGED FILES: 0`, exit 0, saved as `S/u35/laneK/k1/verify.txt`. Only 3 docstrings changed words: api_reference, base_classes, scd30.
- `measure.py`: exit 0, none of my files listed, GENERATED 0.
- ruff: exit 0. No `.sh` files in my set, so no shellcheck.
- The 12 commit checks and 17 scans (21 files, one process): exit 1, 968 passed, 6 failed. All 6 are reds the integration head already had, waiting on D2 (LEAD NOTES 70, plan line 1882):
  - tunables_register: no Part N row for `config.flush_slice_bytes`;
  - level_containment: 4 twin scenarios with no counterpart or E.6.6 row;
  - task_inventory ×4: no C.9 row for `_two_initiations()`.
  uart_link_driver's line count is unchanged, so none of these come from a line I moved.
- Regenerating the device modules changes only the build date and inputs stamp.
- No docstring with a runtime reader changed: setup_toolchain's edit is the comment at line 873, not the module docstring argparse reads, so no `--help` run was needed. That edit is comment-only, so the installer run CLAUDE.md asks for after toolchain changes does not apply.
- K runs no unit or twin files, so I have no timings.

**For the lead:** BACKLOG.md:1187 cites `src/asy_system_service.py:59, :101` for the DebugLevel store. That was already wrong at `bc0d77b`: those lines are `_MAX_STORAGE_PAUSE` and `BOOT_TIMERS`. At `af38779` the right lines are 78 (`_NAME`) and 121 (`_VAL_DEBUG_LEVEL`). PROJECT_AUDIT_PLAN.md's line citations into the shifted files go further out of date, but they were already against older lines.

**Decisions (agent, 2026-10-22):** where a split was needed, I kept each docstring's original closing style (lone or inline `"""`). I split isl29125 like the other three driver headers because tightening alone could not reach the cap.

Runs: rebuild 0, generator 0, measure 0, checks 1 (the 6 reds above). Raw copies deleted; nothing uncommitted; nothing of mine is running.
