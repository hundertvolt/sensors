# Fold F1 (M_SRC_CORE, M_GEN, M_SCR, M_TOOL)

SF-xx | M-ID (part N) | file | unit kept | test/SPEC/bench carriers needed

SF-B1 | M.SRC_CORE.091 (1) | src/asy_fram_manager.py (+ print_log.py store call, same commit) | U16 | L1 aligned one-chunk shift (A.U16.03, TEST_UNIT); L0 seeds distinct and non-zero per CRC width (TSC); SPEC C.7 pitfall and A.4 text (SPEC); SGP40 backup chunk `owner=` (SRC_SENS)
SF-B3 | M.SRC_CORE.044 (1), .015 (1); M.GEN.008 (1), M.GEN.014 (1) | src/config_manager.py, src/system_service.py, buildgen/codegen.py, buildgen/definitions.py | U11 (flag) / U20 (getter, key, row) | L1 failed flush sets, good flush clears (TEST_UNIT); L0 definitions parity (TSC); mock row (WEB); SPEC C.5.2/C.7.3 sentence
SF-M1-07 | M.SRC_CORE.043 (2) (+ .015 (1), M.GEN.008/.014 (1)) | src/config_manager.py | U11 | L1 failed setup write lists the store in ConfigUnpersisted (TEST_UNIT)
SF-M1-04 | M.SRC_CORE.043 (1) | src/config_manager.py | U11 | L1 directory path listed in ConfigFaults (TEST_UNIT)
SF-B4 | M.SRC_CORE.012 (1) (closed by SF-A11's removal of the arm) | src/system_service.py | U11 | L1 mempause answers Valid and the unpause arrives (TEST_UNIT)
SF-A11 | M.SRC_CORE.012 (1), .008 (1), .010 (1), .011 (7) | src/system_service.py | U11 | L1 deadline unpause by driven ticks, refused after reset/acceptance (TEST_UNIT); twin case "unpause timer cannot arm" retired (TWIN); fram_pause_unpause_and_gating.py real-Timer step (HW_DEV); SPEC C.9/F.1 sentence
SF-B5 | M.SRC_CORE.013 (1), .008 (1) | src/system_service.py | U11 | L1 dead uptime timer: one persisted 17, signature resolves (TEST_UNIT); twin alarm-pool case (TWIN)
SF-M1-06 | M.SRC_CORE.013 (1) | src/system_service.py | U11 | L1 dead timer + 7-day gap keeps uptime/HTTPDropped exact (TEST_UNIT)
SF-A10 | M.SRC_CORE.006 (1); M.GEN.008 (2), M.GEN.014 (2) | src/system_service.py, buildgen/codegen.py, buildgen/definitions.py | U11 (.006) / U20 (key, row) | mem32 fakes in tests/machine.py and twin machine.py (TEST_HELP, TWIN); L1 bits stored (TEST_UNIT); SPEC A.8/F.5.4 sentence on raw bits and HAD_POR; bench reset-kind rows (HW_BENCH); mock row (WEB)
SF-A14 | M.GEN.001 (1), M.SRC_CORE.006 (2), M.GEN.034 (1) | buildgen/codegen.py, src/system_service.py | U20 (.006 entry is U11; part (2) staged U20) | L0 boot-entry AST pin (TSC); SPEC A.8 code 21; bench Ctrl-C → ResetReason 21 (HW_BENCH); js code label via catalog (WEB, mock sample)
SF-B12 | M.SRC_CORE.091 (2), .092 (1), .063 (1), .065 (1); M.GEN.034 (1) | src/asy_fram_manager.py, src/print_log.py | U16 (.091/.092/.065), U11 (.063) | L1 allocator refusal → one FRAM entry at setup; L1 store RAM-only entries (TEST_UNIT); SGP40's own refusal (SRC_SENS)
SF-M1-03 | M.SRC_CORE.065 (1) | src/print_log.py | U16 | L1 unreadable store shows one entry under its own name (TEST_UNIT)
SF-M1-01 | M.SRC_CORE.017 (1), .043 (3), .065 (2), .005 (1); M.GEN.034 (1) | src/system_service.py, src/config_manager.py, src/print_log.py | U11 (.065 part (2) staged U11 inside the U16 entry) | L1 absent file + restored FRAM + code 2 → one W; blank FRAM / code 7 / code 9 → none (TEST_UNIT); twin Run 1 stays clean (M.SCR.049, TWIN); SPEC A.8/C.7.3 sentence
SF-M3-06 | M.SRC_CORE.027 (1) | src/base_classes.py | U16 | L1 injected MemoryError prints its own text once (TEST_UNIT, wording clear of the gate markers); SGP40 half (SRC_SENS)
SF-M4-01 (a) | M.SRC_CORE.016 (1) | src/system_service.py | U11 stage, moves to start_tasks() in U20 | L1 unretrieved task → one level-gated line (TEST_UNIT); check every memory-gated tier runs at DebugLevel >= 1 (TSC/SCR); bench non-reading host (HW_BENCH)
SF-B8 (base half) | M.SRC_CORE.038 (1) | src/base_classes.py | U19 | L1 raising/None source → exactly {name: {"error": "unavailable"}} (TEST_UNIT); page half already in M.WEB (F3)
SF-B14 (firmware half) | M.SRC_CORE.063 (2) | src/print_log.py | U11 | none in firmware; `_MAX_CNT` mirror pinned by test_js_api_mirrors (TSC); page half M.WEB.001/.016 (F3)
SF-M4-06 | M.SCR.040 (1) | scripts/test.sh | U27 | test_test_sh.py: marker in a timed-out attempt fails a retried-pass file (TSC)
SF-M4-07 | M.SCR.067 (1) | scripts/build_firmware.py | U27 | test_build_firmware.py pins unlink → tmp+replace → record order (TSC)

## Rows in scope not folded

- SF-B18 (generator writes not atomic): already covered, no fold. `buildgen/generate.py` and `definitions.py` write via
  `.tmp` + `os.replace()` (M.GEN.019, M.GEN.018); `scripts/_generate_sensortask_modules.py` writes every file through tmp
  + `os.replace()` (M.SCR.068). `build_firmware.py`'s stage writes (`:56, :98-99, :149`) sit in the per-build work dir
  that M.SCR.065 wipes at the start of every build, so they are safe by construction. The one real gap, the `.uf2` copy
  at `:162`, is SF-M4-07 (folded).
- M_TOOL: no row in sf_rows.md has a site in M_TOOL's files (toolchain/, ci.yml, pyproject.toml). The U36 chroot-recipe
  rows land in CLAUDE.md/`tests_hardware/README.md` (A.U1.05 → M.DOCS.047/M.HW_BENCH.112), so they are not mine.

## Deviations and decisions to review

- SF-M1-01: folded by-mode M4-04's detector (one SYSTEM warning when the config file is absent while FRAM history
  survives and the reset was not a config reset), not the row's first form (every store's absent-file print becoming a
  persisted warning). The first form would log on every fresh filesystem, including the twin's Run 1, and break
  M.SCR.049's clean boot, which has no tolerance list (OR140.a (13)). I also excluded code 9 next to code 7, because an
  incomplete config reset has already deleted files. The detector needs two flags (`absent_at_boot`, `restored`) and a
  new SYSTEM warning code.
- SF-M1-03/SF-B12 (store half): the entry goes into the logger's own RAM ring under a new shared code `LOG_RAM_ONLY`,
  not into FRAM's RAM logger through the chunk's `pr` as the row says. This avoids a FRAM-band code defined in
  print_log.py and a `pr` member on the chunk Protocol. It also covers the unallocated-chunk case, where there is no
  chunk to reach FRAM's logger through. The manager-side allocator refusal still reports into FRAM's logger (new code
  `FRAM_FULL`).
- SF-A11 + SF-B4: the deadline form takes out the one-shot timer, the unpause waiter task and the flag. That removes
  B4's abort branch entirely, so the API's "Valid" stays true. It also changes M.SRC_CORE.008/.010/.011 (folded) and
  a wide set of tests and scripts (the carriers above).
- SF-A10: the raw bits are exposed as a new `/status` key `ResetBits` and are not decoded. The row says only "stored
  with the decoded cause", so the key and its definitions row are my choice.
- SF-A14: a new ResetReason code 21 (`RR_INTERRUPTED`, public). It is an agent extension of the owner-reviewed code
  table.
- SF-B3: the fold states U11's "check first" as the row asks, with the expected outcome (the flag lands). If U11 finds
  the persisted errno enough, five fold parts drop together.
- Unit differences, entry units kept: M.SRC_CORE.005 (1) lands in U11 (the entry's stages are U2/U3/U10/U30).
  M.SRC_CORE.065 (2) is staged in U11 inside a U16 entry. M.SRC_CORE.006 (2) is staged in U20 inside a U11 entry.
- Not extended: SystemService's own `get_dict_cfg()` (M.SRC_CORE.017) still sends `dict.fromkeys(names)` for an
  unreadable SYSTEM store. SF-B8 scopes the sensor GET only.
- New catalog rows (FRAM_FULL, LOG_RAM_ONLY, SYSTEM W CONFIG_LOST, ResetReason 21) are folded into M.GEN.034 (1).
