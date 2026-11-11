CSA hand-back, written by the agent (Wed Nov 11 13:56 UTC 2026)
Commit 4a598c74 on audit/csa (from ca780dbd; local only, not pushed). 10 files, +79/-76; src -16 lines.
## 1. The chain map (plain calls; F = folded, K = kept)
- Log entry (err_s/wrn_s on a FRAM-backed logger; also every ConfigManager read/write error: _get_values, write_config, the flush are async and reach FRAM only through it): err_s K entry -> _store F (pure: _record + _write + diag) -> PrintLogHistoryStore._write K (except MemoryError records) -> FRAMChunk.write_into F (hop: get_buf None check, then _write) -> _FRAMBaseChunk._write K (pause, size, CRC, _begin, two blocks, verify) -> _write_chunk K (except records; addr<0 pair read) -> _handle_status_bytes K (pair agreement check; also the twin's hook in run_generic_integration.py) -> _set_check_sb K (per-byte read/UNINIT/IDLE checks and write, each with its entry) -> FRAM_SPI.set_values K (public API, logs outcome bits) -> FRAM_SPI._write K (protection check, outcome bits) -> _enable_write/_disable_write K (one retry each) -> _read_status F (pure: RDSR + byte) -> _send_and_read K (the CS envelope, finally), then C. 13 -> 10.
- Store read (setup; reset writes as above): Store._read K (except records) -> FRAMChunk.read_into F (hop) -> _FRAMBaseChunk._read K -> _read_into F (pure: _read_chunk + fault flag) / _compare_with K (own buffer allocation, prints) -> _read_chunk K (except records, CRC) -> _handle_status_bytes -> _set_check_sb -> get_values K (public) -> _read_address F (pure) -> _send_and_read; or -> set_values -> ... as above. Deepest 12 -> 10.
## 2. Folded (the deepest first) and how
- _read_status: _send_and_read now answers its read buffer; its 6 sites index it in place (`..._send_and_read(_CMD_RDSR, self._status_buf)[0]`). _read_address went into get_values the same way.
- FRAMChunk.write_into/read_into: class aliases of the base's _write/_read, which now take the RegionBuffer and refuse an unallocated one first (no log, before the pause check, as the hop did); the timestamped pair passes its buffer (its own bbuf checks were dead after the tbuf check / are now _read's). Instance patches of write_into (tests/_sensortask_scenarios.py) still bind.
- _store into err_s/wrn_s; _read_into into _read (2 sites).
- Two lint consequences, decided (agent, 2026-11-11): `src/` carries no noqa (D.6), so pyproject.toml gets a one-line per-file SLF001 exemption for src/asy_fram_manager.py (the alias, its only site; live, ruff-exemptions test green); _read's exits would be 11 > PLR0911's 10, so its last branch answers `return match` (a bool, same values, same entries) instead of two returns.
- Kept with reason: every K above. _set_check_sb could merge into _handle_status_bytes as a counter loop over the pair (one more level, about -5 lines) but it carries checks, so per the brief it stays: the lead's call.
## 3. Proof
- Test first: a new test pins err_s/wrn_s's failed-write diagnostic (no test held it): green on the base, red on a planted removal of the diag in _store, green after the fold. Every other moved behaviour already had a test (unallocated buffer: test_asy_fram_manager 1773/2121/2279/2283; read faults; wire-trace goldens for RDSR/READ order).
- -1 and 32768, 0 failures, no allocation-failure line: test_asy_print_log 85, test_asy_fram_manager 135, test_asy_fram_driver 77, test_asy_fram_wire_trace 10, allocation_budget 2, test_digital_twin_fram 57, fram_crash_points 3, test_fram_integration 11, notification_fram 2, ntp_fram_system 12, bus_hazard_multi_device 23, digital_twin_bus_hazard_concurrency 26, test_asy_sgp40_driver 156, test_sensortask dev 86 and wozi 86. Coverage build: the three changed test files green.
- ruff (lint_direct rc 0), mypy main/host/twin 0 issues; tests_scripts whole tier 6564 passed (then the config/doc readers again on the final text: 816 passed); harness twin path `--twin -k c_stack` 1 passed; fram_raw_dump.py on the twin: facts as before (status_register 0, rdid 047f4803).
## 4. The twin (Unix port numbers, not the board's; -1 and 32768 identical)
- Before: quiet peak 9,680 B (setup, fram._send_and_read); provoked_end 11,808 B; provoked_logged 1.
- After: quiet peak 8,320 B (setup, _send_command = _send_and_read, now one depth); provoked_end 10,448 B. Both -1,360 B = 3 levels of ~453 B (twin).
- Board expectation (I): 3 x ~264 B, provoked end about 6,080 B (77 %) from 6,876; quiet peak about 4,690-4,950 B (write or read path), still over the half-limit 3,968 B the host test asserts.
## 5. Sizes
- Bytecode (mpy-cross v1.29.0, bare names): asy_fram_driver 3,604 -> 3,552, asy_fram_manager 9,123 -> 9,011, asy_print_log 4,357 -> 4,335: -186 B; lines 340->335, 651->641, 365->364. No module grows.
- Not built: scripts/build_firmware.py rebuilds inside the toolchain tree, and S/tc-c is read/run only; imageFreeBytes is the lead's reflash build.
## 6. Docs
- SPECIFICATION.md F.1 longest chain (now: 12 awaits to _get_values, 10 plain calls err_s -> _send_and_read, ~264 B each); F.5.2's line naming _read_address now names get_values; tests_hardware/README.md C-stack counts (3 below set_values, 10 nested); test comments and fram_raw_dump.py's RDSR read.
## Findings (not pursued)
- (c) S/u35r/r0/module_sizes.sh aborts at src/asy_uart_driver.py ("SyntaxError: invalid arch": native code needs -march); sizes above taken with mpy-cross per file instead.
- (c) SPEC Part N mem.max_await_depth's basis still names the old verify-pass / FRAM-manager-log chain (not a folded-function line; left).
nothing of mine is running
