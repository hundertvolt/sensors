# A-C merge HW_BENCH (HEAD fa6b6a5)

Scope: CLUSTERS.md "## HW_BENCH" — `tests_hardware/` except `flash/` and `device_scripts/` (HW_DEV's): the README,
`conftest.py`, `harness.py`, the host helpers (`bench_control.py`, `error_log_helpers.py`, `http_client.py`,
`heap_map.py`, `rogue_udp_responder.py`, `soak_tiers.py`, `website_identity.py`, `isl29125_conformance.py`,
`ntp_probe.py`), `bench/`, `manual/`, and every new file actions create there (`bench/conftest.py`, `bench/_load.py`,
`bench/test_reset_reasons.py`, `bench/test_system_commands.py`, `bench/test_modlwip_send_stall.py`,
`bench/test_uart_link_crc16.py`, `bench/test_wifi_radio_reinit.py`, `bench/test_boot_order_and_triggers.py`,
`bench/test_ticks_ms_rollover.py`, `bench/test_scd30_frc_readiness_baseline.py`, `bench_facts.py`, `conformance.py`,
`evidence.py`, `kick_then_reset.py`, `plausibility_bounds.py`, `scd30_prerequisite.py`, `spoof_udp.py`,
`twin_board.py`, `twin_record.json`, `heap_bounds.py`). Constituents per file: the index's `by_file` actions plus every
action whose Site, Change or Blast slot names the file (grep of the 1,545 action blocks of `audit/actions/*.md` by path
and basename; 176 blocks beyond the index, each read at the hit). `git diff 8e36b1e fa6b6a5 -- tests_hardware` is empty
(the audit commits since the index touched only `audit/`), so every line cited holds at HEAD `fa6b6a5`.

**Hardware rule, every change below.** Nothing here runs: a `test`/`hardware` change is written and checked board-free
(L0, `--collect-only`, twin run first); it executes only in the phase-C round named in its "Round" line, under the
owner's go-ahead given in that round's own conversation (CLAUDE.md go-ahead rule; A.C.01 (1)). Only the bench board
named by data (`[device].bench`, today `dev`) is ever flashed, with a dev-native image from its own TOML; `wozi` is
never flashed (A.C.01 (5)).

**Conventions every merged change below applies** (each change names the ones it uses; mechanics are not repeated).

- **B0 Lines, units, rounds.** Line numbers are HEAD `fa6b6a5`. Units run in number order (U0 B0; U1-U8 B1; U9-U34 B2;
  U35-U37 B3-B5), then the phase-C rounds R0-R7 (A.C.02-A.C.09). A merged change lands in the latest unit of its
  constituents unless stages are listed. "Round" names the A.C round whose suite run first executes the change on
  silicon (A.C.01's frame applies to every round; inventory row H-number of `audit/actions/C.md` in brackets). Every
  action citing a pinned upstream source line is re-checked against the refreshed pin before execution (OR129.a (5),
  AC_NOTES 34 second).
- **B1 U10 rename sweep** (mechanical, lands with each renaming action in U10, found by its grep): `system_service` →
  `asy_system_service`, `config_manager` → `asy_config_manager`, `crc_checks` → `asy_crc_checks`, `api_response` →
  `asy_api_response`, `captive_dns` → `asy_captive_dns` (A.U10.37); `AsyFramManager` → `FRAMManager`, `AsyConnTime` →
  `WifiService`, `UART_Comm` → `UARTComm`, `UartLinkExerciser` → `UARTLinkDriver` (A.U10.38); REST/config keys
  (A.U10.40: `NtpSynced` → `NTPSynced`, `NtpLastSyncAge` → `NTPLastSyncAge`, `NTP_Host` → `NTPHost`, `MeasInt` →
  `MeasInterval`, `buildDate` → `BuildDate`, …); unit suffixes (A.U10.43); starter names (A.U10.44). Text below uses the
  HEAD spellings where it quotes HEAD and the renamed ones in end states; the rename is never a separate change here.
- **B2 Host annotations** (A.U20.33, U20, mechanical): every host file of this cluster drops `from __future__ import
  annotations`; `TYPE_CHECKING`-only names (`Board`, `BenchBridge`, `Iterator`, `Callable`, `HttpResponse`, …) and
  forward references (`RogueUdpResponder`, `harness.py`'s own classes) are quoted, nothing else. New files written by
  U26 are born in that form.
- **B3 Docstrings to comments** (A.U10.34, U10): function, method and class docstrings in this cluster (91 in 11 files
  at HEAD) become `#` comment blocks directly under the `def`/`class` line, ≤ 3 prose lines; module docstrings stay
  (`manual/runner.py`'s feeds argparse). Every new or rewritten function below carries its explanation in that form.
- **B4 `@tunable` tags** (A.U8C/A.U8C2, grammar A.U8.02): every tagged literal becomes the module constant its row
  writes, Part N row basis "estimated (agent, <commit>) — measurement owed … L3/L4" (N.1); a literal a later
  constituent deletes or replaces by a read (`BENCH`, `ast`, TOML) loses its tag and its row is withdrawn, named per
  change; a renamed ID (A.U26.35's soak durations) is written once in its new spelling.
- **B5 Permanent text.** Comments, docstrings, README text and commit messages cite no audit ID (G9/R12, AC_NOTES 4);
  actor tags read "(owner|agent, YYYY-MM-DD)" (AC_NOTES 6); each block ≤ 3 prose lines under A.U27.28's counting
  (13 `tests_hardware/` files over the cap at HEAD are rewrapped by A.U27.28 in U27; every block a change below rewrites
  is written to the bar in the same edit). README text states current facts, rules and reasons, not history (G9/R11).
- **B6 Imports** (A.U0.07, owner unit U26 for `tests_hardware/`): the function-level imports
  (`bench/test_hotspot_role_reversal.py:248, 296, 335`, `harness.py:44, 252, 268`, `manual/runner.py:72-76`) move to
  module level, and `isl29125_conformance.py:35`'s by-path `exec()` goes with that file (M.HW_BENCH.071); their
  `_PENDING` entries leave `tests_scripts/test_import_placement.py` in the same commit and, the scope reaching zero,
  `tests_hardware/`'s `PLC0415` entry leaves `pyproject.toml` (TSC carries the two non-cluster files).
- **B7 Ordering last** (A.U36.038, U36): each Python file here is re-sorted to D.15 by the script-driven pure move after
  every other change on it; test functions of `test_*.py` files keep their order.
- **B8 No implicit sync, no explicit `Any`** (A.U26.75, A.U26.76, U26): every `uv run` inside `tests_hardware/` is `uv
  run --no-sync`; no hand-written `Any` remains (`JSONValue`/`JSONObject` from `http_client.py`, `ErrcountEntry` from
  `error_log_helpers.py`, `Protocol`s, `object`).
- **B9 Wear and evidence** (CLAUDE.md wear and FRAM rules): an owned flash-filesystem or SCD30-NVM write carries
  `persistence_write` (a further SCD30 write also `scd30_extra_write`); a shared prerequisite write stays unmarked and is
  pinned by name in `tests_scripts/test_persistence_write_marker_completeness.py` (`_KNOWN_PERSISTING_HELPERS`,
  `_PREREQUISITE_DEVICE_SCRIPTS`, `_JUSTIFIED_UNMARKED`); a reflash is `flash_cycle`; FRAM is outside every gate. The
  two collection-time gates deselect (invisible to a skip count, so the verdict reports the deselected count, A.U7.14);
  the other gates skip in-test. Every path that can clear or overwrite FRAM evidence (a `ResetErrors` PUT, `erasefram`,
  a reflash, an isolated-driver script on production's first chunk) saves it first through A.U26.22's one primitive.

## tests_hardware/conftest.py

### M.HW_BENCH.001 One option table: data-named board, image record, kebab gates
- **From**: A.U26.01 (4) (`--bench-device`), A.U26.03 (`--image-record`), A.U26.05 (3) (`--twin`), A.U26.14 (4)
  (`--allow-toolchain-reverify`), A.U26.35 (1) (`--soak-duration`), A.U26.74 (1)-(3) (flag renames, help texts),
  A.U26.79 (1) (`--repair-standard-state`), A.U26.11 (help), A.U26.09 (help), A.C.06 (1)/A.U26.85 (`--lwip-control-image`),
  agent decision D1 (`--dut-ip`, M.HW_BENCH.006); A.SDEP.03 (pytest deprecations: blast-only, the refresh adapts this
  file only if a used API is deprecated).
- **Site**: `tests_hardware/conftest.py:1-4` (docstring), `:16-19` (imports), `:25-102` `pytest_addoption()`.
- **Change**: `from soak_tiers import SOAK_TIER_SECONDS` → `from soak_durations import SOAK_DURATION_SECONDS`
  (M.HW_BENCH.040). `pytest_addoption()` registers, in this order, with help texts stating exactly what each spends:
  `--device PATH` (unchanged); `--bench-device NAME` ("the board on the bench; default $BENCH_DEVICE, else the one
  devices/*.toml with [device].bench = true"); `--image-record PATH` (default `build/firmware-<bench device>.json`,
  resolved at fixture time); `--dut-ip ADDR` ("the DUT's last known address on the bench network; lets the session save
  /status before anything resets the board"); `--lwip-control-image PATH` ("the unpatched control image a phase-C round
  built in a throwaway worktree; required by the unpatched lwIP test, never defaulted"); `--twin` ("run flash-tier
  tests and device scripts against the Unix-port twin instead of a board"); `--soak-duration {short,mid,long}` (choices
  from `SOAK_DURATION_SECONDS`, help naming each duration in seconds and `scripts/run_bench_soak_tests.sh`);
  `--allow-flash-cycle` ("one or more reflashes owned by the test (flash wear)"); `--allow-multi-day-rollover` ("the
  ~12.4-day ticks_ms() rollover observation (bench/test_ticks_ms_rollover.py); no write"); `--allow-neopixel-sweep`
  ("~10 minutes of light programs on the NeoPixel-to-ISL29125 rig recorded by the manual tier; no write of its own, its
  config pushes need --allow-persistence-write"); `--allow-persistence-write` ("the owned flash-filesystem and SCD30 NVM
  writes listed in tests_hardware/README.md's budget table; shared prerequisite writes run without it");
  `--allow-scd30-extra-write` ("on top of --allow-persistence-write: the further SCD30 NVM writes the budget table lists
  under scd30_extra_write"); `--allow-toolchain-reverify` ("a full toolchain re-verification: network fetches and ~8
  min of builds; no board write"); `--repair-standard-state` ("repair a board found outside the standard state; each
  repair is a listed prerequisite write"). `--bench-device` and `$BENCH_DEVICE` naming no `devices/NAME.toml` raise
  `pytest.UsageError` in `pytest_configure()`. Docstring `:1-4` (≤ 3 lines): "Shared pytest options, markers and
  fixtures for tests_hardware/: every fixture skips when its hardware is absent, so the tier collects with nothing
  attached under every option (tests_hardware/README.md)." The old spellings `--allow-persistence-writes`,
  `--allow-multi-day-rollover-wait`, `--soak-tier` are gone (no alias).
- **Resolved**: A.U26.09's help ("two further SCD30 NVM writes (the concurrent offset write and its restore)") counts
  only A.U26.08 (3); A.U26.32, A.U26.72 and A.C.15 (1) also carry `scd30_extra_write` — settled by A.U26.74 (3)'s form
  for `--allow-persistence-write` (the help points to the one budget table, M.HW_BENCH.130) and A.U26.09's own "one
  budget table". `--dut-ip`: agent decision D1 (A.U26.22 (4)'s "save_errcount … before its first reset" needs an
  address the fixture learns only after a reset). `--lwip-control-image`: A.C.06 (1), C A-C note 1.
- **Unit**: U26.
- **Depends**: M.HW_BENCH.040 (soak module rename), M.HW_BENCH.010 (`bench_device()`), A.U7.14 (marker→option map).
- **Blast carried by**: A.U7.14's verdict marker→option map (`soak_duration` → `--soak-duration`, `toolchain_reverify`
  → `--allow-toolchain-reverify`, the two renamed flags) → A.U7.14 (SCR); A.U26.31's collect matrix gains
  `--dut-ip <addr>` and `--lwip-control-image <tmp path>` as valued options → GAP-B1 (TSC); `pyproject.toml`
  `addopts = ["--strict-markers"]` → A.U26.74 (1) (TSC); `tests_scripts/test_tests_hardware_persistence_write_gating.py`
  flag strings, `test_require_clean_hardware_run_sh.py` → A.U26.74/A.U7.14 (TSC); flag users in `flash/conftest.py`,
  `flash/test_bus_concurrency.py`, `flash/test_bus_electrical_timing.py` → A.U26.74 (HW_DEV); README.md/SPEC/CLAUDE.md
  flag names → A.U26.74 with U36 (DOCS, SPEC); this README's running and gating sections → M.HW_BENCH.126/.130;
  `scripts/run_bench_soak_tests.sh --duration` → A.U26.35 (SCR); `bench/conftest.py`'s `--image-record` reader →
  M.HW_BENCH.060.
- **Kind**: code

### M.HW_BENCH.002 Markers registered strictly, each naming what it spends
- **From**: A.U26.74 (2)-(3), A.U26.35 (1), A.U26.36, A.U26.14 (4), A.U26.39 (4), A.U4.08 (marker text, REST half),
  A.U26.09 (budget), A.U35.51 (marker audit: blast-only, its `conformance.md` reads these).
- **Site**: `tests_hardware/conftest.py:105-113` `pytest_configure()`.
- **Change**: markers, each `config.addinivalue_line("markers", …)`: `soak_duration` ("passive observation over one
  named duration; skipped unless --soak-duration"); `multi_day_rollover` ("the ~12.4-day ticks_ms() rollover observed
  over REST; skipped unless --allow-multi-day-rollover"); `flash_cycle` ("reflashes the board (flash wear); skipped unless
  --allow-flash-cycle"); `persistence_write` ("the test itself spends a limited-endurance write — the RP2040 flash
  filesystem, or SCD30 NVM: a PUT /sensors to the SCD30 spends one write per changed field, one per AmbPres or
  ForceCalRef sent and one per ContMeas=false, none for an unchanged TempOffs/MeasInt/Altitude/SelfCal — deselected
  unless --allow-persistence-write; a shared prerequisite write stays unmarked, tests_hardware/README.md");
  `scd30_extra_write` ("further SCD30 NVM writes beyond what persistence_write admits; always carried with it;
  deselected unless both flags"); `neopixel_sweep` ("needs the NeoPixel-to-ISL29125 rig; skipped unless
  --allow-neopixel-sweep"); `toolchain_reverify` ("full toolchain re-verification; skipped unless
  --allow-toolchain-reverify"); `destructive_last` ("informational: runs after every other test of its module"),
  `role_reversal` and `over_provisioned_image` (informational, kept: `bench/test_heap_under_connection_ceiling.py:159`
  uses the latter). `long_soak` is gone (renamed). The `persistence_write` text keeps the REST half A.U4.08 writes, with
  the B1 key spelling (`MeasInterval` after A.U10.40). `pytest_configure()` also performs M.HW_BENCH.001's
  `--bench-device` check.
- **Resolved**: A.U4.08 (U4) writes the REST half into the HEAD text at `:109`; A.U26.74 (U26) rewrites the whole line
  for the renamed flag — one text, the U26 form carrying A.U4.08's sentence (A.U4.08's own Blast names the flag-name text
  U26's). The "SECOND … beyond the routine per-session one" wording of `scd30_extra_write` is stale after OR90.a/OR92.a
  (the prerequisite normally spends zero, A.U26.07) — rewritten as above.
- **Unit**: stage 1 U4 (A.U4.08's REST sentence into `:109`); stage 2 U26 (the whole marker set).
- **Depends**: A.U4.04 (SCD30 onto the chip store).
- **Blast carried by**: `tests_scripts/test_persistence_write_marker_completeness.py:374` drops the inert `timeout` and
  maps every `--allow-*` to its marker → A.U26.74 (4) (TSC); markers on tests → each test's change here and HW_DEV's;
  CLAUDE.md wear rule marker names (`soak_duration`, `--allow-persistence-write`) → A.U26.74 (5) with U36 (DOCS).
- **Kind**: code

### M.HW_BENCH.003 The collection hook tags deselections and runs destructive tests last
- **From**: A.U7.13 (3), A.U26.39 (4), A.U26.74 (flag names), A.U26.31 (structural premise: only these two options
  are read at collection).
- **Site**: `tests_hardware/conftest.py:116-133` `pytest_collection_modifyitems()`.
- **Change**: reads `--allow-persistence-write`/`--allow-scd30-extra-write` (the only options read at collection);
  each deselected item gets `("deselected_by", "--allow-persistence-write")` or `("deselected_by",
  "--allow-scd30-extra-write")` appended to `item.user_properties` before `config.hook.pytest_deselected(...)`; then,
  within each module, items carrying `destructive_last` move after the module's other items, order otherwise stable.
  Its comment block (≤ 3 lines) says the wear gates deselect rather than skip, so a run reports the deselected count
  (A.U7.14).
- **Resolved**: —
- **Unit**: U26 (A.U7.13's (3) lands in U7 on the HEAD flag names; U26 renames them in the same lines).
- **Depends**: A.U7.08 (run-record plugin), M.HW_BENCH.002.
- **Blast carried by**: `tests_scripts/test_tests_hardware_run_record.py` (deselections carry their flag) → A.U7.13
  (TSC); L0 collect-only "destructive_last items last" → A.U26.39 (TSC); A.U26.31's structural test → A.U26.31 (TSC).
- **Kind**: code

### M.HW_BENCH.004 Notes reach the run record: `result_note`, `record_session_note()`
- **From**: A.U7.13 (2).
- **Site**: `tests_hardware/conftest.py` after `pytest_collection_modifyitems()`.
- **Change**: as A.U7.13 (2): fixture `result_note(request) -> Callable[[str], None]` with keyword `recovery: bool =
  False` appending `("result_note" | "recovery", text)` to `request.node.user_properties`; helper
  `record_session_note(config, text, *, recovery=False, source)` looks up the `_pytest_run_record` plugin and calls its
  `add_session_note(...)`, printing the note when the plugin is absent.
- **Resolved**: —
- **Unit**: U7 (every U26 user lands after it).
- **Depends**: A.U7.08.
- **Blast carried by**: every converted RESULT NOTE print → A.U7.15 (HW_BENCH sites: M.HW_BENCH changes of each bench
  module); session-note users M.HW_BENCH.005/.006/.007, `flash/conftest.py` → A.U26.07 (HW_DEV).
- **Kind**: code

### M.HW_BENCH.005 Board, bridge and bench-device fixtures: twin-aware, leftovers cleared
- **From**: A.U26.01 (4), A.U26.05 (3), A.U26.21 (3), A.U26.31 (DONE-AT-HEAD half: the skip-not-error fixtures stay).
- **Site**: `tests_hardware/conftest.py:136-158` (`board`, `bench`); new `bench_device_name`.
- **Change**: `bench_device_name(request) -> str` (session): `--bench-device`, else `$BENCH_DEVICE`, else
  `harness.bench_device()`. `board(request)`: under `--twin` yields `twin_board.TwinBoard(...)` (a missing Unix-port
  binary → `pytest.skip("MicroPython Unix port not built at <path> - run scripts/test.sh once")`); otherwise as HEAD
  (`Board(device=...)`, unreachable → skip). `bench(board, request)`: under `--twin` skips ("the twin has no bench
  bridge"); unconfigured → skip as HEAD; configured → `removed = bridge.clear_leftovers()` once, each removal reported
  through `record_session_note(…, source="bench.clear_leftovers")`, then yield.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.010 (`bench_device()`), M.HW_BENCH.091 (`TwinBoard`), M.HW_BENCH.022 (`clear_leftovers()`),
  M.HW_BENCH.004.
- **Blast carried by**: `tests_scripts/test_bench_device.py` → A.U26.01 (TSC); `tests_scripts/test_twin_board.py`
  → A.U26.05 (TSC); `tests_scripts/test_bench_control_restore.py` → A.U26.21 (TSC); README Environment variables
  (`BENCH_DEVICE`) → M.HW_BENCH.126.
- **Kind**: code

### M.HW_BENCH.006 A session starts with evidence, then checks the standard board state
- **From**: A.U26.22 (4), A.U26.79 (1), A.U26.12 (1) (the read-only DebugLevel reader), A.U26.27 (1) (the bench
  DebugLevel check), A.U26.13 (3) (recovery-event report), A.C.01 (3)/(6) (round frame), agent decision D1 (`--dut-ip`).
- **Site**: `tests_hardware/conftest.py` new session fixtures after `bench`.
- **Change**: three autouse session fixtures, in dependency order. (1) `fram_evidence_saved(request)`: with a board
  present and not `--twin` — first, when `--dut-ip` is given and `GET /status` answers there within 5 s, the verbatim
  body is saved through `error_log_helpers.save_errcount(<addr>, "session-start")` (the only read of a pre-session
  `ResetReason`: it lives in RAM after boot and a raw-REPL entry ends it); otherwise a session note "pre-session
  /status not saved: no reachable --dut-ip" (`record_session_note(…, source="fram_evidence_saved")`); then
  `harness.save_fram_raw(board, "session-start")` (raw dump, read-only), then `board.hard_reset()` (the dump entered
  the raw REPL). (2) `standard_state(request, fram_evidence_saved)` (A.U26.79, bench-aware): at start checks — over
  REST when a bench is configured (it requests `dut_ip`; the image check is `bench/conftest.py`'s `board_image`,
  M.HW_BENCH.060, the flash tier alone has no REST image proof), else through read-only execs — `DebugLevel` 5 (no
  bench: A.U26.12's reader `board.exec("import json\ntry:\n  print('LEVEL=' + str(json.load(open('config_SYSTEM.cfg')).get('DebugLevel')))\nexcept OSError:\n  print('LEVEL=absent')")`
  then `board.hard_reset()`; bench: `GET /system`, strict parse), FRAM write-protect clear (a read-only status-register
  read, HW_DEV's device script), no `config_HWTEST_*` file (read-only `os.listdir()` exec, then `hard_reset()`), and the
  SCD30 snapshot (`MeasInterval`, `AmbPres`, `TempOffs`, `Altitude`, `SelfCal` from `GET /sensors`; flash-only runs
  read it through the interval-read script of A.U26.07 and record what that script yields). `_STANDARD_DEBUG_LEVEL = 5`
  with its bound checked against `asy_system_service`'s `_VAL_DEBUG_LEVEL` maximum by `ast`. A deviation fails the
  session start with "board not in the standard state: <what>, expected <value> — rerun with --repair-standard-state";
  with that flag it is repaired (`PUT /system {"DebugLevel": 5}` with a bench, else
  `system_debug_level_set_standard.py`; write-protect cleared; scratch removed), each repair a session note and a pinned
  prerequisite write (B9). At end: the same checks, the SCD30 values compared with the start snapshot (a difference
  fails the teardown naming the field), and the final `errcount` saved (`save_errcount(dut_ip, "session-end")` with a
  bench). (3) `report_recovery_events(board, request)`: at teardown every entry of `board.recovery_events` (A.U26.13 (3))
  goes through `record_session_note(…, recovery=True, source="mpremote")`.
- **Resolved**: three DebugLevel checks (A.U26.12's flash fixture `debug_level_standard`, A.U26.27's bench
  `debug_level_checked`, A.U26.79's `standard_state`) merge into `standard_state`, which A.U26.79 (1) already defines as
  the one check "over REST when the bench is configured (else over a read-only exec as A.U26.12)"; the two separate
  fixtures are not written (their tests need nothing: `standard_state` is autouse and fails with the cause before the
  first test, G1/R19). A.U26.22 (4) places `save_errcount` "in the `dut_ip` fixture before its first reset", which
  `dut_ip` cannot do (it learns the address through an exec followed by a reset), and its autouse raw dump would end the
  in-RAM `ResetReason` G1/R11 asks to save; D1 orders REST first when an address is known and records the gap
  otherwise (shown in the OR2.c review).
- **Unit**: U26.
- **Depends**: M.HW_BENCH.001, M.HW_BENCH.004, M.HW_BENCH.007 (`dut_ip`), M.HW_BENCH.011 (`save_fram_raw`,
  `recovery_events`), M.HW_BENCH.050 (`save_errcount`), A.U11.05 (`ResetReason`), A.U26.07 (interval script, HW_DEV),
  A.U26.79's two device scripts (HW_DEV).
- **Blast carried by**: `fram_raw_dump.py`, `system_debug_level_set_standard.py`, the write-protect read script →
  A.U26.22/A.U26.79 (HW_DEV); `_PREREQUISITE_DEVICE_SCRIPTS`/`_KNOWN_PERSISTING_HELPERS` gain the repairs with reason
  "restores the standard board state" → A.U26.79 with A.U26.06 (TSC); L0 decision table with a fake board/fetch, and
  `tests_scripts/test_evidence_snapshot.py` (REST save before any raw-REPL call when `--dut-ip` answers) →
  A.U26.79/A.U26.22 (TSC; the `--dut-ip` order case is GAP-B2); the deleted `system_debug_level_raise_…`/`restore_…`
  scripts → A.U26.12 (HW_DEV); README "How a round runs" start/end state → M.HW_BENCH.123; `BACKLOG.md:359-361`
  board-state line → A.U26.79 (3) with U36 (DOCS).
- **Kind**: code, hardware (Round: every round's start and end, A.C.01 (3)/(6)/(8) [H02, H05])

### M.HW_BENCH.007 `dut_ip` reports its recoveries; the stale-credential path scans with the AP down
- **From**: A.U26.29 (2), A.U26.21 (2), A.U26.38, A.U26.41 (3), A.U26.45, A.U26.49 (2), A.U26.22 (4) (REST save
  when no `--dut-ip` was given), A.U8C.57, A.U8C2.25, A.U0.18 (blast-only: no owner tag sits in this file at HEAD).
- **Site**: `tests_hardware/conftest.py:161-200` (`_DUT_HOSTNAME_CANDIDATES`, `_DUT_HOTSPOT_PASSWORD`,
  `_recover_stale_dut_credentials`), `:203-270` (`dut_ip`).
- **Change**: (1) Constants (B4): `_HOTSPOT_SCAN_TIMEOUT_S = 30.0` (`l4.hotspot_role_reversal_hotspot_scan_timeout_s`),
  `_HOTSPOT_SCAN_POLL_S = 2.0` (`…_scan_poll_s`), `_JOIN_HOTSPOT_TIMEOUT_S = 45.0` (`…_join_hotspot_timeout_s`),
  `_PROVISION_PUT_TIMEOUT_S = 10.0` (`l4.conftest_provision_put_timeout_s`), `_DUT_IP_EXEC_TIMEOUT_S = 15.0`,
  `_HTTP_READY_PROBE_TIMEOUT_S = 5.0`, `_HTTP_READY_POLL_S = 2.0`, `_IP_AND_HTTP_TIMEOUT_S = 60.0`
  (`l4.conftest_ip_and_http_timeout_s`, the three uses `:257, :262, :269`), and `_DUT_SERVING_AFTER_STA_S = 30.0`
  tagged `l4.dut_serving_after_sta_s` (the `:248` bound). (2) `_DUT_HOSTNAME_CANDIDATES` and `_DUT_HOTSPOT_PASSWORD` go:
  the candidates are computed at call time as `(<bench TOML [device].hostname>, <_VAL_HOST default read from
  src/asy_wifi_service.py by ast>)` (one helper in `harness.py`, M.HW_BENCH.013), the password is
  `harness.hotspot_password()`; the comment `:161-163` becomes one line "The hotspot SSID is the Hostname value: the
  bench TOML's, or the schema default on a board whose config predates it." (3) `_recover_stale_dut_credentials(bench,
  note)`: `bench.ap_down()` first; then inside one `try` whose `finally` is `bench.leave_dut_hotspot_and_restore_bridge()`:
  the scan wait (`_HOTSPOT_SCAN_*`), `join_dut_hotspot(found[0], hotspot_password(), timeout_s=_JOIN_HOTSPOT_TIMEOUT_S)`,
  the PUT and its result check (unchanged). (4) `dut_ip(board, bench, request)`: the first fallback (one more kick +
  reset) goes through `harness.recover_by_reset(board, bench, ready=…, first_wait_s=_IP_AND_HTTP_TIMEOUT_S,
  retry_wait_s=_IP_AND_HTTP_TIMEOUT_S, skipped="the first STA connect after the session's reset",
  note=<record_session_note bound to source="dut_ip">, description="DUT STA connect")`; the second (stale credentials)
  records `record_session_note(…, recovery=True, source="dut_ip")` naming its write ("stale-credential recovery: one
  PUT /networking (flash write, pinned prerequisite)"), then kick + reset and the last wait. The HTTP-ready wait
  description `:250` → "DUT serves real HTTP at <ip> within <_DUT_SERVING_AFTER_STA_S> s of STA connect (the generated
  main() starts the webserver task before the first NTP sync)". The `:211-212`/`:233-234`/`:253`/`:255` comments state
  the raw-REPL fact once (A.U26.60's form: an exec stops `main.py`; `hard_reset()` restarts it). (5) When
  `fram_evidence_saved` had no reachable `--dut-ip`, `dut_ip` calls `save_errcount(ip, "session-start")` right after
  its first successful HTTP-ready wait, before returning (M.HW_BENCH.006).
- **Resolved**: the `:248` literal carries two tags — A.U8C.57's `l4.conftest_http_ready_timeout_s` and A.U26.41 (3)'s
  `l4.dut_serving_after_sta_s` (the same wait, re-sized to the new boot order); A.U26.41 (3) is the later and specific
  one, so `l4.conftest_http_ready_timeout_s` is withdrawn (its Part N row is not written). A.U26.21 (2) and A.U26.38
  both move the join into the `try`: one restructured function, A.U26.38's AP-down-first order.
- **Unit**: U26 (A.U8C/A.U8C2 tags are U8, written here with the U26 edit since every tagged line moves).
- **Depends**: M.HW_BENCH.012 (`recover_by_reset`), M.HW_BENCH.013 (`hotspot_password()`, hostname candidates),
  M.HW_BENCH.023 (`is_ssid_visible()` AP check), M.HW_BENCH.004, M.HW_BENCH.006, A.U20.06 (boot order), A.U8.01-03.
- **Blast carried by**: `tests_scripts/test_tests_hardware_conftest_constants.py` (pins `_DUT_HOTSPOT_PASSWORD`) →
  A.U26.49 (TSC); `pyproject.toml` S105 entry for `tests_hardware/conftest.py` goes → A.U26.49 (TSC; A.U28.29's
  credential block, U28, no longer lists it); Part N rows → A.U8C.57/A.U8C2.25/A.U26.41 (SPEC); L0
  `recover_by_reset()` cases → A.U26.29 (TSC); the shared IDs in `bench/test_hotspot_role_reversal.py` →
  M.HW_BENCH.071; `bench/test_end_to_end_timing.py:44-46` (same `l4.dut_serving_after_sta_s`) → M.HW_BENCH.067.
- **Kind**: code, test (Round: R1 default bench tier and every bench round [H73])

## tests_hardware/harness.py

### M.HW_BENCH.010 Board facts come from data: one helper each
- **From**: A.U26.01 (3)(5), A.U27.37, A.U26.49 (2), A.U26.45 (hostname candidates), A.U26.23 (2), A.U26.80, A.U0.07
  (`harness.py:44`, B6), A.U26.02 (blast: `harness.py:39-41` names no `buildDate` today — holds).
- **Site**: `tests_hardware/harness.py:26-46` (path inserts, `REPO_ROOT`, `configured_max_connections()`), new
  helpers beside it.
- **Change**: `REPO_ROOT` is defined first; `sys.path.insert(0, str(REPO_ROOT))` sits beside the toolchain insert
  (`:26-28`); module-top imports `tomllib`, `buildgen.validate`, `buildgen.generate`. Helpers, each with a ≤ 3-line `#`
  block: `bench_device() -> str` (A.U26.01 (3): the one `devices/*.toml`, `zz_test_*` excluded, whose `[device].bench`
  is true; none or several → `HardwareNotAvailableError` naming the files); `configured_max_connections(device: str |
  None = None) -> int` (`None` → `bench_device()`); `hotspot_password(device: str | None = None) -> str` (the TOML's
  `[device].hotspot_password`); `dut_hostname_candidates() -> tuple[str, str]` (bench TOML `[device].hostname`, then
  `_VAL_HOST`'s default read from `src/asy_wifi_service.py` by `ast`); `fram_backed_logger_names(device: str | None =
  None) -> list[str]` (`expected_facts()`'s `"fram_backed_loggers"` through `buildgen.generate.generate_device(...)`, no
  file); `get_routes(method: str = "GET", *, json_only: bool = True, streams: bool | None = None) -> list[str]` (from
  the one REST reference U19 generates, its machine-readable form; `json_only` keeps JSON-bodied routes, `streams`
  filters by the table's streaming property).
- **Resolved**: A.U27.37 (U27) replaces the call body by `buildgen.validate.device_max_connections_by_name()`; A.U26.01
  (U26) changes the default; B6 moves the late import in U26 — staged: U26 module-top import of `device_max_connections`
  with the path form, U27 swaps to the by-name helper (A.U27.37 keeps "A.U26.01's bench-device default").
  `get_routes()` before U19's reference exists is moot: U19 < U26, so A.U26.80's `ast` fallback is not written.
- **Unit**: stage 1 U26 (all helpers, the default, the module-top import); stage 2 U27 (`configured_max_connections()`
  body → `device_max_connections_by_name(device or bench_device())`).
- **Depends**: A.U20.34/A.U20.35 (`[device].bench` key, GEN), A.U20.07/A.U20.11 (`expected_facts()` keys, GEN),
  A.U19.20 (REST reference), A.U27.37.
- **Blast carried by**: callers of `configured_max_connections()` in `bench/` (unchanged calls) → M.HW_BENCH changes of
  each module; `website_identity.py` `device` keyword → M.HW_BENCH.037; L0 `tests_scripts/test_bench_device.py` →
  A.U26.01 (TSC); `test_bench_harness_helpers.py:138-143` holds → A.U27.37 (TSC); the hotspot-password triple check
  (TOML = `_VAL_HOTSPOT_PW` default) → A.U26.49 (TSC); `get_routes()` L0 (`/notification` included) → A.U26.80 (TSC);
  `devices/dev.toml` `bench = true` → A.U26.01 (GEN, M.GEN); BACKLOG chroot entry "pytest pythonpath" → A.U27.37
  (DOCS).
- **Kind**: code

### M.HW_BENCH.011 `_mpremote()`: a retry never re-runs a started script; every recovery is recorded
- **From**: A.U26.13 (2)(3), A.U26.37, A.U26.79 (2), A.U26.75, A.U26.65 (USB rebind, transient retry, node rebind
  comments), A.U8C.112 (tags), agent decision D2 (the two settle sleeps deferred to U26 by A.U8C.112 under G7/R23).
- **Site**: `tests_hardware/harness.py:183-207` `_usb_reset_device()`, `:296-304` constants, `:345-406`
  `Board.__init__`/`_rebind_device_if_moved()`/`_mpremote()`.
- **Change**: (1) `Board.recovery_events: list[str]` (new attribute). (2) `_mpremote(*args, timeout_s=None,
  allow_recovery=True, retry_if_started=True)`: `cmd = ["uv", "run", "--no-sync", "mpremote", "connect", self.device,
  *args]`; a transient failure whose stdout already holds output returns at once when `retry_if_started` is false; each
  retry, node rebind and USB rebind appends one line to `recovery_events` (attempt, marker matched, elapsed); on
  `subprocess.TimeoutExpired` it first interrupts the board — `serial.Serial(self.device).write(b"\x03\x03")` then the
  `reset` call — records the event, then raises `HardwareTestFailureError` as today. (3) `_usb_reset_device(device) ->
  tuple[bool, str]`: each `sudo tee` result checked; a non-zero exit returns `(False, "<unbind|bind> refused:
  <stderr>")` at once; after the unbind it polls (≤ `_USB_UNBIND_SETTLE_MAX_S = 2.0`, `l4.harness_usb_unbind_settle_max_s`)
  until `/sys/bus/usb/devices/<usb_id>/driver` is gone, after the bind (≤ `_USB_BIND_SETTLE_MAX_S = 3.0`,
  `l4.harness_usb_bind_settle_max_s`) until the tty node exists again; success `(True, "unbind+bind of <usb_id>")`.
  `_mpremote()` appends the detail; a refused rebind raises `HardwareNotAvailableError("USB rebind recovery refused by
  sudo — see tests_hardware/README.md prerequisites")`. (4) Constants (B4): `_USB_REBIND_CMD_TIMEOUT_S = 10.0`,
  `_MPREMOTE_DEFAULT_TIMEOUT_S = 60.0`, `_USB_GRACE_S = 10.0` (`:368, :399, :404, :486`), `_USB_GRACE_POLL_S = 0.5`
  (`:389, :499`), `_MPREMOTE_SHORT_TIMEOUT_S = 10.0` (`:413, :480`), the `l4.harness_max_device_rebinds` tag on
  `_MAX_DEVICE_REBINDS`. (5) Each workaround's comment (≤ 3 lines) names defect, bound and removal trigger (A.U26.65):
  the USB rebind ("the bench's USB CDC can stop entering raw REPL until the port is rebound (tests_hardware/README.md
  traps); one rebind per call; remove when a full round records no rebind event"), the transient retry and its grace,
  the node rebind after re-enumeration.
- **Resolved**: D2 — A.U8C.112 left `:202` (2.0) and `:204` (3.0) untagged pending U26's keep-or-poll decision under
  G7/R23, and no U26 action takes it; a fixed settle sleep is what G7/R23 removes, so both become bounded polls on the
  state they wait for (shown in the OR2.c review). A.U26.79 (2)'s interrupt and A.U26.13's event list share
  `recovery_events`.
- **Unit**: U26 (the U8 tags land with it).
- **Depends**: A.U7.13 (session notes), M.HW_BENCH.006 (the report fixture), A.U21.26 (sudo rules).
- **Blast carried by**: L0 `tests_scripts/test_harness_mpremote_retry.py` (retry/no-retry/soft-reset/refused unbind/
  timeout-interrupt cases) → A.U26.13/A.U26.37/A.U26.79 (TSC); the settle-poll cases join it → GAP-B3 (TSC); the
  no-`uv run`-without-`--no-sync` check → A.U26.75 (TSC); the passwordless-sudo list (`tee`) → A.U21.26 (TOOL);
  README traps and Workarounds table rows → M.HW_BENCH.127/.128; Part N rows → A.U8C.112 (SPEC).
- **Kind**: code

### M.HW_BENCH.012 Isolated runs render board facts, run once, and return what they saw
- **From**: A.U26.13 (1), A.U26.44 (2), A.U26.43 (1), A.U26.22 (3) (`save_fram_raw`), A.U26.68 (`parse_facts`),
  A.U26.78 (1) (render-time `# @include`), A.U26.60 (`run_isolated()` docstring), A.U31.05 (blast: `run_isolated()` arms
  the watchdog before `mpremote run`, holds), A.U8.08 (blast: the `WDT(timeout=8000)` literal is the
  `wdt.timeout_ms` mirror).
- **Site**: `tests_hardware/harness.py:440-459` (`run_isolated()`, `run_isolated_expect_reset()`), new functions.
- **Change**: `render_device_script(path, **extras) -> Path`: a script holding the line `BENCH: "BenchFacts" = {}  #
  rendered by tests_hardware/harness.py` gets its right side replaced by `repr(bench_facts.build(bench_device()) |
  extras)`, every `# @include _shared/<name>.py` line replaced by that file's text, and is written to
  `build/device_scripts/<name>` (one small file, overwritten per run); a script with neither is run unchanged.
  `run_isolated(script_path, *, soft_reset_after=True, timeout_s=None, allow_recovery=True, **extras) -> str`: renders,
  then `_mpremote("exec", <arm>, "run", <rendered>, allow_recovery=…, retry_if_started=False)`; then, when requested, a
  separate `_mpremote("soft-reset")` whose failure raises "script completed (output below) but the trailing soft-reset
  failed" with the first call's output — never a re-run. `<arm>` is `"import machine; machine.WDT(timeout=8000)"`, the
  8000 carrying the `wdt.timeout_ms` mirror tag (A.U8.08). `run_isolated_expect_reset(script_path, *, timeout_s=None,
  **extras) -> str` renders and returns the captured stdout (possibly partial). `parse_facts(output) -> dict[str,
  object]`: every `FACT <key>=<json>` line parsed; a missing `DONE` line raises `HardwareTestFailureError` quoting the
  output. `save_fram_raw(board, reason) -> Path`: runs `device_scripts/fram_raw_dump.py` (rendered with the bench build's
  allocation size) and saves its stdout through `evidence.save_text(f"fram-raw-<n>-{reason}.txt", …)`. Docstrings →
  `#` blocks (B3) stating once: raw-REPL entry stops `main.py`; the soft reset that follows keeps the armed watchdog, the
  GC threshold, `ticks_ms()` and pin muxing and never re-runs `main.py` (`ports/rp2/main.c:246-247`, v1.29.0).
- **Resolved**: A.U26.13 (two calls) and A.U26.44 (render first) edit the same method: render, then the two calls.
- **Unit**: U26.
- **Depends**: M.HW_BENCH.011, M.HW_BENCH.041 (`bench_facts.build()`), M.HW_BENCH.055 (`evidence`), A.U26.78's
  `_shared/` files and `fram_raw_dump.py` (HW_DEV).
- **Blast carried by**: ≈ 60 `run_isolated()` callers (unchanged calls; `**extras` users: SEAM/NONCE A.U26.43, CRC_MODE
  A.S0930.05, COMMAND A.S0930.39, bounds A.U26.33/.58) → HW_DEV and the bench modules here; `device_scripts/bench_facts.pyi`
  and the one `BENCH` line per script → A.U26.44 (HW_DEV); the guard `tests_scripts/test_device_script_bench_facts.py`,
  `parse_facts()` L0, the `print("RESULT:` ban → A.U26.44/A.U26.68 (TSC); `TwinBoard` renders the same way →
  M.HW_BENCH.091; `tests_scripts/test_bench_harness_helpers.py` stubs (two calls) → A.U26.13 (TSC).
- **Kind**: code

### M.HW_BENCH.013 Reset, presence and exec state the raw-REPL facts; `soft_reset()` goes
- **From**: A.U26.60, A.U14.01 (blast: the `hard_reset()` docstring), A.U26.83 (`Board.soft_reset()`), A.U8C.112
  (`:423`, `:470`, `:491` tags), A.U26.65 (Board docstring's `machine.bootloader()` claim).
- **Site**: `tests_hardware/harness.py:340-343` (class docstring), `:408-438`, `:461-501`.
- **Change**: `soft_reset()` (`:461-464`) is deleted (no caller, A.U26.83; its `:462` tag use goes). `hard_reset()`'s
  comment: "`mpremote reset`: a raw-REPL exec of `machine.reset()` (tools/mpremote/mpremote/main.py:407-411, v1.29.0), a
  real MCU reset that re-runs the frozen main.py; it writes no reset record, so /status reports it as a watchdog reset
  without a record." `is_reachable()`'s comment keeps "raw-REPL entry stops main.py; never poll a live system"; `exec()`
  states the same in one line. The class comment (B3): "Drives the board through `uv run --no-sync mpremote`: the one
  isolated-driver mechanism, the reset, the bootloader entry the reflash helper uses, and passive log tailing."
  Constants: `_PRESENCE_PROBE_TIMEOUT_S = 0.2`, `_MPREMOTE_RESET_TIMEOUT_S = 15.0` (`:470`),
  `_LOG_TAIL_READ_TIMEOUT_S = 0.5`.
- **Resolved**: A.U14.01's suggested docstring ("a watchdog-forced reboot") and A.U26.60's ("a real MCU reset … reads
  as a watchdog reset without a record") say the same; A.U26.60's text is used (it also names the `/status` reading).
- **Unit**: U26.
- **Depends**: A.U11.05 (`ResetReason`).
- **Blast carried by**: `flash/test_reboot_persistence.py:1-3` "DTR" → A.U26.60 (HW_DEV); `soft_reset` grep clean in
  `tests_scripts/` → A.U26.83 (verified, none).
- **Kind**: code

### M.HW_BENCH.014 One `reflash()` helper: exit-249 retry only, passive end
- **From**: A.S0930.06 (2), A.U26.14 (1)-(3), A.U26.85 (1) (its user), A.C.06 (1)-(3).
- **Site**: `tests_hardware/harness.py` new function after `Board`.
- **Change**: `reflash(board, uf2_path: Path) -> None`: `board.enter_bootloader()`; then `sudo picotool load -x -v
  <uf2_path>` retried only while its exit code is 249 (BOOTSEL device not yet enumerated, `_retryable_picotool_exit(code)
  -> bool`), at most 5 attempts, each retry appended to `board.recovery_events`; any other non-zero exit raises at once
  with its output (the comment: every other exit may already have written flash); then `wait_until(board.is_device_present,
  …)` and `wait_for_boot(board, …)` (M.HW_BENCH.016) over `tail_log()` — passive, no `is_reachable()` after the reset.
  It writes nothing else and builds nothing: callers pass an image they built (the round's standard `.uf2`, a CRC16
  image, the control image).
- **Resolved**: A.U26.14 reworks the retry inside `flash/test_toolchain_flash_boot.py`; A.S0930.06 (2) moves the same
  steps into this helper — one helper (A.U26.14 Depends says so), the smoke test calls it (HW_DEV).
- **Unit**: U26 (SUPP_owner_0930 lands with U26, A.S0930.06's "A-C merges").
- **Depends**: M.HW_BENCH.011, M.HW_BENCH.016.
- **Blast carried by**: `flash/test_toolchain_flash_boot.py` → A.U26.14 (HW_DEV); `bench/test_uart_link_crc16.py` →
  M.HW_BENCH.094; `bench/test_modlwip_send_stall.py` → M.HW_BENCH.075; `_retryable_picotool_exit` L0 → A.U26.14 (TSC);
  `picotool` under sudo `secure_path` → A.U21.27 (TOOL).
- **Kind**: code, hardware (Round: R4 [H38, H39, H70])

### M.HW_BENCH.015 Recovery by reset is one reported helper; serving waits are tunable
- **From**: A.U26.29 (1), A.U8C.112 (`:224`, `:257-259`, `:264`, `:272`), A.U8C2.47, A.U8.05 (the script-server wait's
  IDs), A.U0.07 (`harness.py:252, 268`, B6).
- **Site**: `tests_hardware/harness.py:221-286` (`wait_until`, `restore_board_to_serving`, `wait_for_script_server`).
- **Change**: `kick_then_reset(board, bench)` (the two calls); `recover_by_reset(board, bench, ready, *, first_wait_s,
  retry_wait_s, skipped, note, description)` as A.U26.29 (1): wait; on timeout `note("recovery pass: kick +
  hard_reset() after <description>; skipped: <skipped>", recovery=True)`, kick, reset, wait again (a second timeout
  raises). `restore_board_to_serving()` calls `kick_then_reset()`; `import http_client` moves to module top (B6).
  Constants: `_WAIT_UNTIL_POLL_S = 1.0`, `_SERVING_PROBE_TIMEOUT_S = 10.0`, `_SERVING_RESTORE_TIMEOUT_S = 90.0`,
  `_SERVING_RESTORE_POLL_S = 3.0`, `_SCRIPT_SERVER_TIMEOUT_S = 120.0`, `_SCRIPT_SERVER_HANDOVER_S = 20.0`,
  `_SCRIPT_SERVER_PROBE_TIMEOUT_S = 3.0`, `_SCRIPT_SERVER_HANDOVER_POLL_S = 0.5`, `_SCRIPT_SERVER_POLL_S = 1.0`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.004 (`result_note`/`record_session_note` as `note`).
- **Blast carried by**: the eleven fallback sites → M.HW_BENCH.007 (`dut_ip`), .067 (`test_end_to_end_timing.py`),
  .076-.080 (`test_network_resilience.py`), .095 (`test_wifi_networking.py`); the no-bare-`hard_reset()` check over
  `bench/` and the `recover_by_reset()` cases → A.U26.29 (TSC); the CLI → M.HW_BENCH.042.
- **Kind**: code

### M.HW_BENCH.016 One boot-line, crash-line and fault-window observer
- **From**: A.U26.26, A.U26.47 (2), A.U35.05 (the hardware gates read `MEMORY_ERROR_MARKERS`), A.C.18, A.U7.22/A.U7.23
  (blast: readers of the marker set).
- **Site**: `tests_hardware/harness.py:34-37` and a new section after it.
- **Change**: `MEMORY_ERROR_MARKERS` unchanged (its comment ≤ 3 lines, citing SPEC I.4(e)). New:
  `BOOT_COMPLETION_MARKERS = ("config is ready", "FRAM SPI FRAM Driver Setup complete")` with the comment "One-time
  setup() lines, printed at DebugLevel >= 3 (the standard state holds 5); tests_scripts pins each against src/.";
  `boot_lines(lines)`, `crash_lines(lines)` (`Traceback` or any marker), `wait_for_boot(board, timeout_s) -> list[str]`
  (passive `tail_log()` until a boot line or the timeout; `TimeoutError` naming the DebugLevel need);
  `observe_during(board, action) -> tuple[T, list[str]]` (a tail thread from before `action` until it returns plus 5 s,
  `_OBSERVE_TAIL_AFTER_S = 5.0` tagged `l4.observe_during_tail_after_s`).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: A.U11.19 (the missing-file branch no longer prints the old `:478` line; `config is ready` stays).
- **Blast carried by**: the boot oracles (`test_network_resilience.py:311, 342`, `test_wifi_networking.py:97`,
  `manual_bus_electrical.py:46`, `flash/test_reboot_persistence.py:66`, `flash/test_memory_stress.py:97`,
  `bench/test_memory_stress_bench.py:93, 169`) → M.HW_BENCH.076/.095/.101/.074 here and A.U26.26 (HW_DEV); the
  pinned-strings L0 (`RTC set to:` included) and `observe_during()` L0 → A.U26.26/A.U26.27/A.U26.47 (TSC);
  `tests_scripts/test_memory_error_gate_agreement.py` gains `heap_map` → A.U26.47 (TSC); the planted-red arm on
  silicon → A.C.18 (round R1 end, [H43]).
- **Kind**: code

### M.HW_BENCH.017 The ceiling instrument: tagged values, typed probe
- **From**: A.U8.05, A.U8C.112 (`:165`), A.U26.76 (`harness.py:22, 161`), A.U26.65 (held pad line), A.U14.03 (blast:
  the `:49-51` comment stays), A.U36.532 (blast: the `H.7.1` citers `:51, :80, :141` keep their number).
- **Site**: `tests_hardware/harness.py:49-172`.
- **Change**: stacked tags above `discover_max_connections()` `:56`: `l4.ceiling_probe_limit = 40`,
  `l4.ceiling_settle_s = 1.0`, `l4.ceiling_dwell_s = 0.3` (the defaults stay keyword defaults: `tests_scripts/
  test_request_timeout_ceiling.py:117-131` reads them by AST); above `_open_probe()` `:113`
  `l4.ceiling_probe_connect_timeout_s = 2.0`; above `_wait_for_slots_to_drain()` `:138` `l4.ceiling_drain_timeout_s =
  10.0`, `l4.ceiling_drain_release_s = 1.0`, `l4.ceiling_drain_hold_s = 0.3`; `_HOLD_CHECK_TIMEOUT_S = 0.05`
  (`:165`). `_assert_probe_held(admitted_socks: list[socket.socket], started: float)` (no `Any`; the `TYPE_CHECKING`
  `Any` import goes). The `HELD_PAD_LINE` comment names its bound and removal trigger in ≤ 3 lines (A.U26.65): it resets
  the per-call read timeout each walk step; removed if the walk stops needing to outlast `per_call_timeout_s`.
- **Resolved**: A.U8.05 creates the six ceiling IDs; A.U8C.112 repeats them ("already created … nothing further") and
  adds `:165` — one tag set.
- **Unit**: U26 (tags of U8 land with the U26 edit of the same lines).
- **Depends**: A.U8.01-A.U8.04.
- **Blast carried by**: Part N rows and relations → A.U8.05 (SPEC); callers in `bench/` → M.HW_BENCH.069/.087.
- **Kind**: code

### M.HW_BENCH.018 The board resolver delegates to the installer's
- **From**: A.U21.28 (blast: "U26 makes `resolve_board_device()` delegate to `resolve_board_serial()`, keeping
  `_NO_BOARD_DEVICE`").
- **Site**: `tests_hardware/harness.py:28-30` (import), `:296-337` (`_BOARD_BY_ID_GLOB`, `resolve_board_device()`).
- **Change**: `from setup_toolchain import resolve_board_serial` (the `detect_pico_serial_devices` import goes);
  `_BOARD_BY_ID_GLOB` goes (moved to `toolchain/setup_toolchain.py` as `BOARD_BY_ID_GLOB`);
  `resolve_board_device(by_id_dir, sys_tty_dir, dev_dir) -> str`: `candidates = resolve_board_serial(by_id_dir,
  sys_tty_dir, dev_dir)`; several → `HardwareNotAvailableError` as today; none → `_NO_BOARD_DEVICE`; one → its path (a
  by-id link already, so `_stable_name_for()` goes unless still used — it is not).
- **Resolved**: —
- **Unit**: U26 (after U21's resolver).
- **Depends**: A.U21.28.
- **Blast carried by**: `tests_scripts/test_resolve_board_device.py` keeps its seven cases → A.U21.28 (TSC/TOOL);
  `scripts/mpremote_connect.sh` → A.U27.13 (SCR); README serial-device note → M.HW_BENCH.126.
- **Kind**: code

## tests_hardware/bench_control.py

### M.HW_BENCH.020 Every injection is undone and proven absent by state
- **From**: A.U26.21 (1), A.U8C.56 (`:249, :255` timeouts), A.U36.544 (5) item 5 (`:118` BACKLOG citer).
- **Site**: `tests_hardware/bench_control.py:102-124` (`block_udp_ports`, `unblock_udp_ports`,
  `redirect_udp_port_to_local`, `clear_udp_port_redirect`), `:184-188` (`clear_network_degradation`), `:248-257`
  (`_run_iptables`, `_run_tc`).
- **Change**: `allow_missing` is deleted from both runners and every call. `unblock_udp_ports()` and
  `clear_udp_port_redirect()` run `iptables -D`; on a non-zero exit they list the chain (`sudo iptables -S FORWARD`,
  `sudo iptables -t nat -S PREROUTING`): the listing failing → `HardwareTestFailureError` naming sudo/the tool; a line
  still holding `--comment sensors-bench-fault-injection` and the same port → `HardwareTestFailureError("restore left
  a FORWARD DROP/PREROUTING DNAT in place: <line>")`; otherwise absent. `clear_network_degradation()`: on a failed
  `qdisc del`, `sudo tc qdisc show dev <iface>` must succeed and show no `netem`, else raise. The project comment tag
  becomes one module constant `FAULT_COMMENT = "sensors-bench-fault-injection"` (every default argument uses it). The
  `:118` docstring's "(BACKLOG.md open question #5)" → "(SPECIFICATION.md F.1, UDP on rp2/lwIP)" and its last sentence
  names the README section "What the network-fault injections reach" for the local-delivery gap. `_CMD_TIMEOUT_S =
  10.0` (B4, `:90, :249, :255, :271`).
- **Resolved**: A.U36.544 (U36) edits the `:118` docstring A.U26.21 (U26) leaves in place: staged by text only, the U36
  pointer change on the U26 end state.
- **Unit**: stage 1 U26 (restore logic, constants); stage 2 U36 (the `:118` pointer).
- **Depends**: A.U36.544 (F.1's UDP paragraph).
- **Blast carried by**: the 17 injection sites in `test_network_resilience.py` and the netem arms in
  `test_bus_concurrency_under_api_load.py` (unchanged calls) → M.HW_BENCH.076-.080, .064; L0
  `tests_scripts/test_bench_control_restore.py` and `test_bench_harness_helpers.py` (`allow_missing` stubs rewritten)
  → A.U26.21 (TSC); README injection section → M.HW_BENCH.129.
- **Kind**: code

### M.HW_BENCH.021 Workaround comments name defect, bound and removal; owner tag restored
- **From**: A.U26.65 (`:58-62`, `:72-80`, `:85-100`, `:126-151`), A.U0.18 (`:190`), A.U8C.56 (`:24, :43, :138, :198,
  :201`), A.U8C2.24 (`:132, :145`), A.U26.49 (3) (`:146`), A.U21.20 (blast: the `:146` line is U26's).
- **Site**: `tests_hardware/bench_control.py:24-100`, `:126-151`, `:190-215`.
- **Change**: each workaround comment ≤ 3 lines with defect, bound and removal trigger: `ap_ssid()` `--escape no`
  ("nmcli -g escapes ':' as '\:'; applies to every SSID/PSK read; remove if nmcli -g stops escaping"), `ap_down()`
  idempotence ("nmcli down errors on an inactive connection; one call per stage; remove if nmcli makes down
  idempotent"), `kick_client()`/`kick_all_stations()` ("a stale AP-side station entry survives the DUT's reset and
  blocks its reassociation (tests_hardware/README.md traps); once before each reset; remove when a round records no
  stale-entry reconnect failure"), the tcpdump capture ("DNAT to 127.0.0.1 does not deliver to a local socket on this
  bench (route_localnet 0); one capture per test; remove if the redirect delivers locally"). `:190` "the bench Pi4 has
  a single WiFi radio" → "… (owner, 2026-09-01)". The `:146` example line uses documentation addresses ("e.g.
  `14:35:23.753510 IP 192.0.2.57.55718 > 198.51.100.123.123: NTPv3, ...`", RFC 5737). Constants (B4): `_NMCLI_TIMEOUT_S
  = 30.0`, `_NMCLI_SHORT_TIMEOUT_S = 15.0`, `_UDP_CAPTURE_TIMEOUT_S = 55.0`, `_JOIN_HOTSPOT_TIMEOUT_S = 30.0`,
  `_TCPDUMP_TIMEOUT_S = 60` (the string `"60"` → `str(_TCPDUMP_TIMEOUT_S)`), `_CAPTURE_WAIT_FLOOR_S = 5.0`; the
  `l4.bench_control_udp_capture_timeout_s` row names `l4.bench_control_tcpdump_timeout_s` as its upper bound.
- **Resolved**: —
- **Unit**: U26 (A.U0.18's U0 tag is written into the U26 rewrite of the same comment; the U8 tags land with it).
- **Depends**: A.U8.01-A.U8.03.
- **Blast carried by**: README Workarounds table rows → M.HW_BENCH.128; Part N rows → A.U8C.56/A.U8C2.24 (SPEC);
  `tests_scripts/test_setup_toolchain_env.py` MAC → A.U21.20 (TSC).
- **Kind**: code, doc

### M.HW_BENCH.022 A run starts by clearing and reporting a killed run's leftovers
- **From**: A.U26.21 (3)(4).
- **Site**: `tests_hardware/bench_control.py` new method `BenchBridge.clear_leftovers()`.
- **Change**: `clear_leftovers() -> list[str]`: every iptables rule (FORWARD, nat PREROUTING) whose `-S` line holds
  `FAULT_COMMENT` is deleted by its `-D` form; a `netem` root qdisc on `wifi_iface()` is deleted; the
  `ROLE_REVERSAL_CLIENT_CONN` profile, if present, is deleted; the AP is brought up if down; returns one line per
  removal. It touches network state only, never a log or an archive (OR38.a (2)), and never `BENCH_BRIDGE_CONN`/
  `BENCH_ETH_CONN` (the host's own access path, CLAUDE.md dead-man's-switch rule).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.020.
- **Blast carried by**: the `bench` fixture's call and notes → M.HW_BENCH.005; L0 `clear_leftovers()` and the
  access-path guard (no `tests_hardware/` module passes `BENCH_BRIDGE_CONN`/`BENCH_ETH_CONN` to `_nmcli`) → A.U26.21
  (TSC).
- **Kind**: code

### M.HW_BENCH.023 The single radio never scans while it hosts the AP
- **From**: A.U26.38.
- **Site**: `tests_hardware/bench_control.py:193-199` `is_ssid_visible()`.
- **Change**: before scanning, `nmcli -t -f NAME connection show --active` must not list `self.ap_conn`, else
  `HardwareTestFailureError("is_ssid_visible() called while the bench AP is up - the single radio cannot scan")`;
  the comment keeps "requires ap_down() first" as the rule the check enforces.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: —
- **Blast carried by**: callers `conftest.py:176` → M.HW_BENCH.007; `test_hotspot_role_reversal.py:38, 80, 185, 361`
  → M.HW_BENCH.071/.072; `test_network_resilience.py:553` → M.HW_BENCH.078 (each already follows an `ap_down()`, grep
  at execution); the stubbed-`_nmcli` L0 → A.U26.38 (TSC); README bench facts single-radio row → M.HW_BENCH.120.
- **Kind**: code

### M.HW_BENCH.024 Spoof support: hold the real reply back
- **From**: A.U26.56 (1).
- **Site**: `tests_hardware/bench_control.py` new method after `unblock_udp_ports()`.
- **Change**: `block_udp_ports_from(ports, comment=FAULT_COMMENT)` adds a FORWARD DROP for UDP datagrams whose source
  port is in `ports` toward the DUT (`--sport`), and `unblock_udp_ports_from()` removes it with
  M.HW_BENCH.020's verified-absent form; `clear_leftovers()` covers its rules by the shared comment.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.020.
- **Blast carried by**: the connected-socket spoof test → M.HW_BENCH.079.
- **Kind**: code

### M.HW_BENCH.025 Remove the confirmed leftovers
- **From**: A.U26.83 (`is_valid_mac`, `_MAC_RE`, `wait_for_link_local_teardown`), A.U8C.56 (deferred `:277`: withdrawn,
  the function goes), A.U8C2.24 (deferred `:281` `l4.bench_control_link_local_settle_s`: withdrawn, the function goes).
- **Site**: `tests_hardware/bench_control.py:260-264`, `:277-281`; `import time` (`:10`, used only there).
- **Change**: the three definitions and the now-unused `time` import are deleted (`re` stays: `read_captured_udp_source_port`).
- **Resolved**: A.U26.83 settles G7/R23's "removed (OR46.a), or it polls" as removed; the two deferred tags have no site.
- **Unit**: U26.
- **Depends**: —
- **Blast carried by**: callers none (repo grep, A.U26.83).
- **Kind**: code

## tests_hardware/http_client.py

### M.HW_BENCH.030 The hardware client keeps the twin client's shape, typed and pinned
- **From**: A.U26.70, A.U26.76 (`:12, 21, 24, 28`), A.U8C.113, A.U25.31 (co-land: the twin's `CeilingRefusedError` and
  parameter order); blast-only, hold: A.U24.34/.35/.38/.40/.60, A.U25.42/.51/.63, A.U8C.25, A.U19.17, A.U0.31,
  A.SDEP.15/.17 (each names the twin client `digital_twin/_http_client.py` or a twin-tier test, not this file's code);
  A.U36.544 (3) (`:48` "queue F10/F11").
- **Site**: `tests_hardware/http_client.py:1-60`.
- **Change**: `JSONValue` (recursive alias `None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]`)
  and `JSONObject = dict[str, JSONValue]`; `HttpResponse(status_code, headers, body, drained: bool = False)`, `json() ->
  JSONObject` raising `ValueError("json() on a drained response")` when drained and refusing a non-object;
  `class CeilingRefusedError(ConnectionError)`; `fetch(host, port, method, path, json_body: JSONObject | None = None,
  timeout_s: float = _FETCH_TIMEOUT_S, read_body: bool = True) -> HttpResponse` translating a `CEILING_CLOSE` raised
  before any response byte into `CeilingRefusedError` (cause kept) and, with `read_body=False`, draining the body
  unkept; `_FETCH_TIMEOUT_S = 10.0` (`l4.http_client_fetch_timeout_s`). `is_ceiling_close(exc)` stays as
  `isinstance(exc, CeilingRefusedError)` or the URLError-wrapped form for its existing callers; the `CEILING_CLOSE`
  comment keeps its fact ("the client sees FIN or RST depending on kernel TCP state, both measured on the bench") and
  drops "queue F10/F11". The module docstring
  (≤ 3 lines) names `digital_twin/_http_client.py` and `tests_scripts/test_http_client_shape_parity.py`, and both rely
  on the server answering `Connection: close`.
- **Resolved**: parameter order agreed with A.U25.31 (`host, port, method, path, json_body, timeout_s, read_body`; the
  twin's `async` the one difference) — A.U26.70 (2).
- **Unit**: U26 (after A.U25.31 lands in U25).
- **Depends**: A.U25.31.
- **Blast carried by**: the parity test and `tests_scripts/test_http_client_ceiling_close.py` cases → A.U26.70 (TSC);
  the twin client's docstring naming this file → M.TWIN (A.U25.31, TWIN); callers of `is_ceiling_close` →
  M.HW_BENCH.064/.076/.087.
- **Kind**: code

## tests_hardware/heap_map.py

### M.HW_BENCH.035 The allocation marker is the shared one
- **From**: A.U26.47 (1); blast-only, hold: A.U36.023 (the parser anchor joins F's pin-move re-check list),
  A.U25.61/A.U8C.01/.71/.72/.73/.86/A.U8C2.30 (device-script output formats it parses, unchanged), A.U7.23 (the gate
  list), A.U24.13 (`tests_scripts` user, unchanged).
- **Site**: `tests_hardware/heap_map.py:192`.
- **Change**: `_ALLOCATION_FAILED = re.compile("|".join(map(re.escape, harness.MEMORY_ERROR_MARKERS)))` with
  `from harness import MEMORY_ERROR_MARKERS` at module top.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.016.
- **Blast carried by**: `tests_scripts/test_memory_error_gate_agreement.py` gains `heap_map` in `_HARDWARE_TIER_FILES`
  → A.U7.23/A.U26.47 (TSC); `tests_scripts/test_heap_map_parser.py` unchanged; SPEC F pin-move list → A.U36.023 (SPEC).
- **Kind**: code

## tests_hardware/rogue_udp_responder.py

### M.HW_BENCH.036 The rogue responder binds port 0 and counts what it answered
- **From**: A.U26.73, A.U26.55 (2), A.U8C.118, A.U28.27 (blast: its per-file `S104` reason).
- **Site**: `tests_hardware/rogue_udp_responder.py:11-46`.
- **Change**: `RogueUdpResponder(garbage_payload: bytes, local_port: int = 0)`; `port` property
  (`self._sock.getsockname()[1]`); `answered_from: dict[str, int]` incremented per source address after each successful
  `sendto`; `_RECV_TIMEOUT_S = 0.5`, `_JOIN_TIMEOUT_S = 5.0` (B4); the `S104` bind-all-interfaces reason comment ≤ 1 line
  ("binds the bench host's responder on the bench LAN").
- **Resolved**: A.U26.73's argument swap (payload first, port defaulted) and A.U26.55's counter edit one class.
- **Unit**: U26.
- **Depends**: —
- **Blast carried by**: the two garbage tests construct it first and redirect to `responder.port` → M.HW_BENCH.078;
  `pyproject.toml` per-file `S104` entry → A.U28.27 (TSC).
- **Kind**: code

## tests_hardware/website_identity.py

### M.HW_BENCH.037 The website check names its device and reads every errcount group
- **From**: A.U26.01 (5), A.U6.01 (blast: definitions after the construction order), A.U6.25 (blast: union of every
  errcount group), A.U36.512 (`:57` "every other variant"), A.U36.544 (3) (`:2` "queue row G9"), A.U26.45 (the variant
  sweep counts this file's `"dev"` default among A.U26.01's sites), B6 (`noqa: E402` lines `:15-16`).
- **Site**: `tests_hardware/website_identity.py:1-60`.
- **Change**: `assert_page_is_this_devices_build(res, link, *, device: str)` (required keyword); `_errcount_keys(device)`
  returns the union of every `kind == "errcount"` group's module keys (A.U6.25), built through
  `buildgen.definitions.definitions_for_toml()` (A.U6.01's construction-order path) instead of a bare `build_model()` +
  `generate_definitions()`; the `sys.path` insert stays before the buildgen imports, so the two `# noqa: E402` stay only
  if ruff still flags them (RUF100 decides; CLAUDE.md's E402 rule); `:57` comment → "dev is a superset of every other
  device today, so …" (≤ 3 lines); the docstring drops "(queue row G9)".
- **Resolved**: —
- **Unit**: U36 for the `:57` word (A.U36.512); U26 for the rest (A.U6.01/A.U6.25 land in U6, their blast here is
  carried in the U26 edit, the call shape existing from U6 on — stage 1 U6: switch to `definitions_for_toml()` and the
  union so the file keeps working when U6 lands; stage 2 U26: the required `device` keyword; stage 3 U36: the word).
- **Depends**: A.U6.01, A.U6.25, M.HW_BENCH.010.
- **Blast carried by**: callers `bench/test_rest_endpoints_over_sta.py:36`, `bench/test_hotspot_role_reversal.py:289`
  pass `device=bench_device_name` → M.HW_BENCH.084/.071.
- **Kind**: code

## tests_hardware/isl29125_conformance.py → tests_hardware/conformance.py

### M.HW_BENCH.038 One conformance gate for every bus chip, run through the twin board
- **From**: A.U26.66 (1), A.U26.45 (`:34`), A.U10.30 (`:35` exec), A.U27.12 (`:39-42, 59-61`), A.U27.15 (`:64`),
  A.U8.15 (`l0.isl29125_conformance_heapsize = 8M`: withdrawn), A.U8C.114, A.U28.28 (`noqa: S603`), A.U0.07 (`:35`, B6);
  blast-only, hold: A.U25.25 (the removed `configure_i2c_wiring()`), A.U25.44 (launch-site guard), A.U25.62 (no class
  named here), A.U8C.77/A.U8C2.33 (the probe script, HW_DEV).
- **Site**: `tests_hardware/isl29125_conformance.py:1-86` (`git mv` → `tests_hardware/conformance.py`).
- **Change**: module docstring (≤ 3 lines): "Host side of the chip conformance probes: runs a probe on the twin through
  TwinBoard at both GC stages and diffs it against the same probe on silicon, physical keys compared only in an
  independent form." `_TWIN_ENTRY`, `unix_port_binary()`, the temp file, the `exec` launch and its `noqa: S603` go.
  `run_probe_on_twin(probe: Path, gc_threshold: int) -> dict[str, str]`: `TwinBoard(...).run_isolated(probe,
  gc_threshold=gc_threshold, timeout_s=_TWIN_PROBE_TIMEOUT_S)` then `parse()` (unchanged, KEY=VALUE lines); a missing
  binary → `pytest.skip("MicroPython Unix port not built at <path> - run scripts/test.sh once")`; `DONE` required as
  today. `compare(real, twin, physical_keys, independent_checks) -> list[str]`: protocol keys compared verbatim, each
  physical key through its probe-declared independent form (a range, a CRC validity, a monotonic relation);
  `PHYSICAL_KEYS` moves into each probe's host table (the ISL29125 set is the HEAD set). `_TWIN_PROBE_TIMEOUT_S =
  180.0` tagged `l3.conformance_twin_probe_timeout_s` (A.U8C.114's row, its ID following the module rename). No heapsize
  of its own: TwinBoard's binary and heap are `scripts/test.sh`'s (`l1.unix_heapsize`), so A.U8.15's 8M tag is withdrawn.
- **Resolved**: A.U26.66 replaces the whole launch that A.U10.30 (exec named in F.1), A.U27.12 (binary path) and
  A.U27.15 (`MICROPYPATH`) each edit: the launch now lives in `twin_board.py` (M.HW_BENCH.091), where A.U27.12's
  `_unix_port.sh` lookup and A.U27.15's `twin` path land; the F.1 exception moves with it (GAP-B4). ID rename: agent
  decision (B4's renamed-ID rule, as A.U26.35 does for the soak IDs).
- **Unit**: U26 (the file is renamed and rewritten once; the U8C tag lands on the new constant).
- **Depends**: M.HW_BENCH.091 (`TwinBoard`), M.HW_BENCH.041 (rendered `BENCH`), A.U26.05.
- **Blast carried by**: `flash/test_sensor_accuracy.py:80-89` moves to `flash/test_chip_conformance.py`, the four new
  probes and their `PHYSICAL_KEYS` tables → A.U26.66 (HW_DEV); SPEC F.1 named-exception list and the import-graph /
  import-placement checks (`exec` of a device script now in `digital_twin/run_device_script.py`) → GAP-B4 (SPEC, TWIN,
  TSC); A.U25.44's launch-site guard reads `twin_board.py`'s `MICROPYPATH` → GAP-B5 (TWIN, TSC); `pyproject.toml`
  per-file `S603` reason → A.U28.28 (TSC); README "Chip conformance probes" → M.HW_BENCH.118.
- **Kind**: code, hardware (Round: R1 flash tier [H25, H26])

## tests_hardware/ntp_probe.py

### M.HW_BENCH.039 No change beyond the sweep conventions
- **From**: A.U20.33 (B2: the future import goes; no `TYPE_CHECKING` name) — the only action naming the file.
- **Site**: `tests_hardware/ntp_probe.py:1-23`.
- **Change**: B2 only; B5 holds (the docstring is 3 lines; `_NTP_EPOCH_DELTA`'s source comment names
  `src/asy_ntp_client.py`'s constant, a cited copy — A.U26.49 (4)'s drift fence reads it: the comment becomes `#
  source: src/asy_ntp_client.py _NTP_EPOCH_DELTA` so the fence accepts it).
- **Resolved**: —
- **Unit**: U20 (B2), U26 (the `# source:` form, with A.U26.49's fence).
- **Depends**: A.U26.49 (4).
- **Blast carried by**: —
- **Kind**: code

## tests_hardware/soak_tiers.py → tests_hardware/soak_durations.py

### M.HW_BENCH.040 Soak runs are named durations
- **From**: A.U26.35 (1), A.U8C.119 (IDs renamed per A.U26.35 (3)).
- **Site**: `tests_hardware/soak_tiers.py:1-7` (`git mv` → `soak_durations.py`).
- **Change**: `SOAK_DURATION_SECONDS = {"short": 60.0, "mid": 600.0, "long": 6 * 3600.0}` with three stacked tags
  `# @tunable l4.soak_duration_short_s = 60.0`, `# @tunable l4.soak_duration_mid_s = 600.0`, `# @tunable
  l4.soak_duration_long_h = 6`; docstring (≤ 3 lines): "Named soak durations for --soak-duration and every
  soak_duration test; its own module because a subdirectory's conftest.py shadows a bare `from conftest import ...`."
- **Resolved**: A.U8C.119's IDs `l4.soak_tiers_*` are written once as `l4.soak_duration_*` (A.U26.35 (3)).
- **Unit**: U26.
- **Depends**: —
- **Blast carried by**: importers `conftest.py` → M.HW_BENCH.001; `flash/test_memory_stress.py`,
  `flash/test_bus_electrical_timing.py` → A.U26.35 (HW_DEV); `bench/test_memory_stress_bench.py` → M.HW_BENCH.074;
  Part N rows → A.U8C.119 with the renamed IDs (SPEC); README soak text → M.HW_BENCH.126.
- **Kind**: code

## New host helpers

### M.HW_BENCH.041 `bench_facts.py`: the bench board's facts as one rendered dict
- **From**: A.U26.44 (1), A.S0930.05 (the `crc` fact, A.S0930.01's key), A.U26.49 (1) (bounds as extras), A.U26.48 (3)
  (`WORST_CASE_ALLOCATION` as an extra), A.U26.22 (3) (allocation size for `fram_raw_dump.py`), A.U26.23 (3)
  (`fram_wired`/`fram_backed_loggers` for the capacity script), A.U26.58 (queue depth, an extra of its host test).
- **Site**: new `tests_hardware/bench_facts.py`.
- **Change**: `build(device: str) -> dict[str, object]` (host CPython) from `buildgen.validate.build_model()` of
  `devices/<device>.toml`: `device_module` (`sensortask_<device>`), `bus` (each `[bus.*]` table's full parameter set —
  I2C id/scl/sda/frequency/timeout, the key absent when the TOML sets none; SPI id/sck/mosi/miso; UART id/tx/rx/baudrate/
  rxbuf/txbuf/poll_wait_ms/poll_idle_ms and `crc`, `"none"` when absent), `instances` (per instance driver, bus,
  address, `irq_pin`/`cs_pin`/`pin`), `addresses`, `fram_max_size`, `fram_wired`, `fram_backed_loggers`, and the driver
  constants a script copies (e.g. ISL29125 `_MODE_RGB`) read from `src/` by A.U20.28's `ast` reader (one reader, reused).
  Per-run values (bounds, `SEAM`, `NONCE`, `CRC_MODE`, `COMMAND`, the FRAM dump size) are `extras` of
  `render_device_script()`, never facts. Header ≤ 3 lines; no literal pin or address anywhere in the file.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: A.U20.28 (address reader), A.U20.07/A.U20.11 (`expected_facts()` keys), A.S0930.01 (`crc` key).
- **Blast carried by**: `device_scripts/bench_facts.pyi` and every script's `BENCH` reads → A.U26.44 (HW_DEV); the guard
  `tests_scripts/test_device_script_bench_facts.py` (builds for every derived device) → A.U26.44 (TSC); the twin plan
  agreeing with it → A.U20.28's contract test (GEN/TSC).
- **Kind**: code

### M.HW_BENCH.042 `kick_then_reset.py`: the ad-hoc reset never skips the kick
- **From**: A.U26.29 (4), A.U33.07 (blast: the BACKLOG item it answers is deleted, citing this CLI).
- **Site**: new `tests_hardware/kick_then_reset.py`.
- **Change**: a CLI run as `.venv/bin/python tests_hardware/kick_then_reset.py [--device D]`: resolves the board
  (`Board(device=...)`) and the bridge (`BenchBridge()`; unconfigured → exit 2 naming `env --tier bench`) and calls
  `harness.kick_then_reset(board, bench)`; header ≤ 3 lines naming the trap it answers (README traps section).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.015.
- **Blast carried by**: README traps section names it → M.HW_BENCH.127; BACKLOG `:721-728` → A.U33.07 (DOCS).
- **Kind**: code

### M.HW_BENCH.043 `plausibility_bounds.py`: one bound per quantity, each with its source
- **From**: A.U26.49 (1).
- **Site**: new `tests_hardware/plausibility_bounds.py`.
- **Change**: `BOUNDS: dict[str, tuple[float, float, str]]` — CO2 `(200, 10000, "owner floor 2026-09-03; SCD30
  datasheet Table 1: 400-10000 ppm")`, humidity, temperatures, pressure, VOC index `(0, 500, "SGP40 datasheet: index
  1-500; 0 while the algorithm's initial blackout runs, src/voc_algorithm.py _VOCALGORITHM_INITIAL_BLACKOUT")`, raw,
  lux `(0.0057, 10000, "ISL29125 datasheet FN8424 p.1")`, each source naming its page (read from the PDF at
  execution); host tests import it, device scripts receive it as a render extra.
- **Resolved**: the bench REST check's 400 ppm floor (`bench/test_rest_endpoints_over_sta.py:18`) becomes the shared
  200 (the owner's floor, `dc3ee33`) — A.U26.49 (1). A.U26.49 (1) writes the VOC index as `(1, 500, SGP40 datasheet)`;
  the shipped algorithm reports 0 for its first 45 samples (`src/voc_algorithm.py:15, 761`), and a bench session's
  first tests run within that window after `dut_ip`'s reset, so the shared floor is 0 (as
  `bench/test_bus_concurrency_under_api_load.py:21` already has) — agent decision D4, a bound that would fail a healthy
  board is not a plausibility bound.
- **Unit**: U26.
- **Depends**: —
- **Blast carried by**: `bench/test_rest_endpoints_over_sta.py`, `bench/test_bus_concurrency_under_api_load.py` →
  M.HW_BENCH.084/.064; the five device scripts' CO2 floor and `isl29125_plausibility_read.py:14`,
  `bmp3xx_plausibility_read.py` bounds → A.U26.49 (HW_DEV); the drift fence over `tests_hardware/` → A.U26.49 (4) (TSC).
- **Kind**: code

### M.HW_BENCH.044 `scd30_prerequisite.py`: start the measurement at most once per session
- **From**: A.U26.07 (4).
- **Site**: new `tests_hardware/scd30_prerequisite.py`.
- **Change**: as A.U26.07 (4): module-level `_Session` (`start_sent: bool`, never reset) and
  `ensure_scd30_measuring(board, state) -> str` — interval read (timeout 30 s; FAIL or no `INTERVAL=` → raise, zero
  sends), data-ready wait (`timeout_s = 3 * interval + 60`), `MEASURING` → "already measuring (no write)";
  `NOT_MEASURING` → refuse when `start_sent`, else set it, send once (any failure raises, never retried), confirm;
  "started (one NVM write)". The three scripts run through `board.run_isolated()` (rendered `BENCH`). The interval-read
  timeout `30.0` and the `+ 60` margin are tagged (`l3.scd30_prerequisite_interval_read_timeout_s`,
  `l3.scd30_prerequisite_wait_margin_s`, B4).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.012; the three device scripts (A.U26.07, HW_DEV).
- **Blast carried by**: `flash/conftest.py`'s `scd30_measuring` fixture → A.U26.07 (HW_DEV); L0
  `tests_scripts/test_scd30_prerequisite.py` (each failure mode, exactly one send) → A.U26.07 (TSC, OR92.a); the
  prerequisite script pinned in `_PREREQUISITE_DEVICE_SCRIPTS` → A.U26.06 (TSC).
- **Kind**: code, hardware (Round: R1 first flash run [H31])

### M.HW_BENCH.045 `spoof_udp.py`: a hand-built datagram from a documentation address
- **From**: A.U26.56 (2).
- **Site**: new `tests_hardware/spoof_udp.py`.
- **Change**: `build_datagram(src, dst, sport, dport, payload) -> bytes` (IPv4 header checksum, UDP checksum over the
  pseudo-header) and a CLI `sudo .venv/bin/python tests_hardware/spoof_udp.py --src 203.0.113.5 --dst <addr> --dport 53
  --payload-hex …` sending it through `socket.SOCK_RAW`/`IPPROTO_RAW`; refuses a `--src` outside RFC 5737's three
  documentation ranges (exit 2), so it can never forge a real host's address.
- **Resolved**: the documentation-range refusal is agent decision D3 (A.U26.56 names the address; the refusal keeps the
  tool to that use, shown in the OR2.c review).
- **Unit**: U26.
- **Depends**: —
- **Blast carried by**: the off-subnet test → M.HW_BENCH.072; the sudo rule for this one command → A.U21.26 (TOOL);
  L0 checksum test → A.U26.56 (TSC).
- **Kind**: code, hardware (Round: R1 [H61])

### M.HW_BENCH.046 `heap_bounds.py`: the worst-case allocation defined once
- **From**: A.U26.48 (3).
- **Site**: new `tests_hardware/heap_bounds.py`.
- **Change**: `WORST_CASE_ALLOCATION = 16_384` with its actor comment "(agent, 2026-09-19; the retired 80,000 B floor
  was the owner's, 2026-09-19)"; `flash/test_memory_stress.py:24` imports it, the device script receives it through the
  rendering.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.012.
- **Blast carried by**: `flash/test_memory_stress.py`, `heap_headroom_after_full_system_build.py` → A.U26.48 (HW_DEV).
- **Kind**: code

## tests_hardware/evidence.py (new)

### M.HW_BENCH.055 One evidence directory per run
- **From**: A.U26.22 (1), A.U7.20 (the hardware wrapper's archive directory).
- **Site**: new `tests_hardware/evidence.py`.
- **Change**: `evidence_dir() -> Path` = `$EVIDENCE_DIR` when set (the hardware wrapper's `build/archive/hardware/<ts>/`),
  else `build/archive/pytest/<UTC>/` created once per process through `scripts/_archive_evidence.py`'s API;
  `save_json(name, obj) -> Path`, `save_text(name, text) -> Path` (one small file each, never overwriting: a name already
  present gains `-<n>`).
- **Resolved**: A.U26.22 names `$EVIDENCE_DIR` as "set by the hardware wrapper"; A.U7.20 makes the wrapper write into
  `build/archive/hardware/<ts>/` but exports nothing — GAP-B6 (SCR) carries the export.
- **Unit**: U26.
- **Depends**: A.U7.20.
- **Blast carried by**: `$EVIDENCE_DIR` export in `scripts/_require_clean_hardware_run.sh` → GAP-B6 (SCR);
  `tests_scripts/test_evidence_snapshot.py` (`$EVIDENCE_DIR` honoured) → A.U26.22 (TSC); users M.HW_BENCH.012/.050.
- **Kind**: code

## tests_hardware/error_log_helpers.py

### M.HW_BENCH.050 Save, then clear: the one evidence primitive before any `ResetErrors`
- **From**: A.U26.22 (2), A.U36.544 (4) (`:3` "A.7" → "A.8, H.6"), A.U8.05 (`:14` `l4.reset_errors_timeout_s`),
  A.U8C.100 (`:14` repeat; `:23`), A.U19.14
  (blast gap: its removal of BACKLOG item 24 leaves `:13`'s "Measurements: BACKLOG item 24" dangling), A.U35.40 (2)
  (its two calls go through the save), A.S0930.29 (2)/(4)/(5) and A.S0930.28 (callers saving before `erasefram`),
  A.C.10 / A.U33.09 (the phase-C bench budget: a later delta).
- **Site**: `tests_hardware/error_log_helpers.py:1-19`.
- **Change**: module docstring (≤ 3 lines): "Shared /status errcount helpers: save the logs, then clear them; confirm a
  provoked fault left its catalog entry. Shape: GET /status -> {"errcount": {"<Logger>": {"counter": int, "history":
  [...]}}} (SPECIFICATION.md A.8, H.6)." `save_errcount(dut_ip, reason) -> Path`: `GET /status`, strict (200, a JSON object),
  saves the verbatim body (`errcount`, `ResetReason` and every other field) through `evidence.save_json(f"errcount-
  {reason}.json", …)`. `reset_all_error_logs(dut_ip, reason)` (the `reason` required) calls `save_errcount()` first,
  then the PUT. The `:11-13` comment: "Above the server's 15.0 s outer_cap_s, never below: a legitimate concurrent reset
  stays under the cap and WiFi latency is absorbed here. Timings: SPECIFICATION.md C.7." `_RESET_ERRORS_TIMEOUT_S = 30.0`
  tagged `l4.reset_errors_timeout_s`; `_ERRCOUNT_TIMEOUT_S = 10.0` (`l4.error_log_helpers_errcount_timeout_s`).
  `code` is re-exported from `tests/_error_codes.py` (`sys.path.append(str(REPO_ROOT / "tests"))` at module top, then
  `from _error_codes import code`; appended, so no `tests/` fake shadows a module the host tier imports) — the one
  lookup every bench module uses.
- **Resolved**: the `:13` pointer: A.U19.14 deletes item 24 in U19 and moves its figures to item 32 and SPEC C.7
  (A.U11.31's Docs); the comment points to SPEC C.7, the permanent home, not to item 32, which closes in phase C
  (A.C.10) — no second rewrite. The budget constant A.C.10 adds after R1 is a phase-C delta on this file, not written
  now (its figures do not exist).
- **Unit**: stage 1 U19 (the `:11-13` comment); stage 2 U26 (save-then-clear, `reason`, tags, the `code` re-export).
  The U2 import of `code` (A.U2.03) lands in U2 as `from _error_codes import code` with the same append, and stays.
- **Depends**: M.HW_BENCH.055, M.TEST_HELP.045 (`tests/_error_codes.py`), A.U11.31 (concurrent reset).
- **Blast carried by**: ≈ 30 `reset_all_error_logs(` callers gain a reason (`request.node.name` or a literal) → each
  bench module's change here (M.HW_BENCH.064/.067/.071/.074/.076/.086/.093); `tests_scripts/test_evidence_snapshot.py`
  (GET and file written before the PUT, call order recorded) → A.U26.22 (TSC); the phase-C budget constant, its Part N
  row and BACKLOG item 32's closure → A.C.10 after R1 (delta) [H46]; DEVICE_REFERENCE "read and save first" → A.U19.14
  (DOCS).
- **Kind**: code

### M.HW_BENCH.051 Log oracles fail closed and are typed
- **From**: A.U26.67, A.U26.76 (`:7, 22, 25, 77`), A.U2.08/A.U3.06 (`:30-32` docstring), B3.
- **Site**: `tests_hardware/error_log_helpers.py:22-41`, `:68-87`.
- **Change**: `class ErrcountEntry(TypedDict)` (`counter: int`, `history: list[JSONObject]`); `get_errcount(dut_ip) ->
  dict[str, ErrcountEntry]` asserts `errcount` is an object; `errcount_entry(counts, name) -> ErrcountEntry` (public:
  the two test sites below use it too; A.U26.67 names it `_entry`) raises
  `AssertionError(f"{name!r} is not in /status errcount ({sorted(counts)}): a renamed or unwired logger, or a changed
  /status shape")` and requires `counter` (int) and `history` (list); every helper uses it.
  `assert_no_task_ended()`'s comment (≤ 3 lines): "The supervisor's record since the test's opening ResetErrors: a task
  that ended (TASK_RAISED, TASK_CANCELLED, TASK_RETURNED) or a budget reboot lands in SYSTEM, which FRAM keeps across a
  hard_reset(); a routine fault is handled in place (SPECIFICATION.md C.7.2)." `assert_module_error_log_contains(dut_ip,
  module_name, num, kind)` keeps its signature (callers pass `code(kind, NAME)`). `assert_no_module_logged_a_new_error()`
  compares the key sets too: a logger present before and absent after, or the reverse, fails naming it.
- **Resolved**: A.U2.08 (U2) and A.U3.06 (U3) both name the `:30-32` docstring's errno text; the catalog names above
  are the end state of both (A.U3.06 adds TASK_RETURNED); written once in U26 with A.U26.67's rewrite (between U3 and
  U26 the HEAD text stays — a docstring, no behaviour).
- **Unit**: U26.
- **Depends**: M.HW_BENCH.030 (`JSONObject`), A.U2.01/A.U3.06 (catalog names).
- **Blast carried by**: `tests_scripts/test_bench_no_task_ended_completeness.py:59-78` (`(None, True)` case now fails)
  and `tests_scripts/test_bench_harness_helpers.py:82-91` (absent-before case → shape-change message) → A.U26.67 (TSC);
  the two test sites that bypass the helpers → M.HW_BENCH.093 (`test_uart_link_under_api_load.py:104-107, 193-196`),
  M.HW_BENCH.074 (`test_memory_stress_bench.py:120-126`).
- **Kind**: code

### M.HW_BENCH.052 Remove the uncalled non-empty check; keep the clean check for its caller
- **From**: A.U26.83 (`assert_module_error_log_nonempty` removed; its removal of `assert_module_error_log_clean`
  dropped — settled by A.U35.40 (3)), A.U35.40 (3) (docstring), A.U26.76.
- **Site**: `tests_hardware/error_log_helpers.py:43-65`.
- **Change**: `assert_module_error_log_nonempty()` deleted. `assert_module_error_log_clean(dut_ip, module_name,
  allowed_warnings: tuple[int, ...] = (), allowed_errors: tuple[int, ...] = ())` stays (through `_entry()`); its comment
  (B3): "Nothing in the log's history beyond the named entries; for a test whose documented outcome includes those codes
  (a deliberately provoked torn write)."
- **Resolved**: A.U26.83 (U26) vs A.U35.40 (U35) — A.U35.40's Depends settles it: the helper stays; no U26 removal and
  U35 re-add churn.
- **Unit**: stage 1 U26 (the deletion of `…_nonempty`, `_entry()` use, typing); stage 2 U35 (the comment, with its
  caller).
- **Depends**: M.HW_BENCH.051.
- **Blast carried by**: the caller `bench/test_end_to_end_timing.py` → M.HW_BENCH.068 (U35).
- **Kind**: code

## tests_hardware/twin_board.py (new)

### M.HW_BENCH.091 `TwinBoard`: `Board`'s API over the Unix-port twin
- **From**: A.U26.05 (2), A.U26.44 (2) (renders the same way), A.U26.66 (1) (both GC stages for the probes), A.U27.12
  (binary lookup, via M.HW_BENCH.038's merge), A.U27.15 (`twin` MICROPYPATH, via the same), A.U35.05 (3) (the hardware
  gates' twin arm runs through it), A.U25.44 (launch-site guard: GAP-B5).
- **Site**: new `tests_hardware/twin_board.py`.
- **Change**: `class TwinBoard` with `Board`'s public names and signatures (`run_isolated`, `run_isolated_expect_reset`,
  `exec`, `hard_reset`, `tail_log`, `is_reachable`, `is_device_present`, `recovery_events`): `run_isolated(path, *,
  timeout_s=None, gc_threshold: int = -1, **extras)` renders through `harness.render_device_script()` and runs
  `<build-standard micropython> -X heapsize=16M digital_twin/run_device_script.py <plan.json> <rendered> --gc-threshold
  <n>` under `timeout` of `timeout_s`, with `MICROPYPATH` and `TZ=UTC` as `scripts/test.sh` sets them for the twin, the
  plan from `buildgen.twin_wiring.compute_twin_wiring()` for `bench_device()` written once per process to
  `build/twin_board/plan.json`; `hard_reset()`/`is_reachable()`/`is_device_present()` return True with no effect;
  `tail_log()` returns the last run's output lines; `recovery_events` stays empty (no retry). A missing binary raises
  `FileNotFoundError` naming the build hint (the `board` fixture turns it into a skip, M.HW_BENCH.005). Stage 2 (U27):
  the binary path comes from `scripts/_unix_port.sh unix_port_bin standard` (existence through its `check` form) and
  `MICROPYPATH` from `scripts/micropypath.toml`'s `twin` entry.
- **Resolved**: A.U27.12/A.U27.15 retarget the conformance launch, which now lives here (M.HW_BENCH.038).
- **Unit**: stage 1 U26; stage 2 U27.
- **Depends**: A.U26.05 (1) (`digital_twin/run_device_script.py`, TWIN), A.U20.28 (`compute_twin_wiring()`),
  M.HW_BENCH.012, A.U27.12, A.U27.15.
- **Blast carried by**: L0 `tests_scripts/test_twin_board.py` (shape parity with `Board`, a one-line script's output)
  → A.U26.05 (TSC); `digital_twin/README.md` "Running device scripts in the twin" → A.U26.05 (TWIN); the F.1 `exec`
  exception and A.U25.44's guard → GAP-B4, GAP-B5.
- **Kind**: code

## tests_hardware/twin_record.json (new)

### M.HW_BENCH.092 The twin-first record of every instrument
- **From**: A.U26.05 (4)(5), A.U35.49, A.U35.21 (its script's entry), A.C.12/A.C.14 (A-C note 3: their scripts join),
  A.U26.87, A.S0930.05/.28/.39 (their scripts).
- **Site**: new `tests_hardware/twin_record.json` (written by `scripts/record_twin_instrument_runs.py`, never by hand).
- **Change**: one entry per `device_scripts/*.py`, `flash/test_*.py`, `bench/test_*.py`: `{"sha256", "runner_sha256"
  (run_device_script.py + twin_board.py), "api_sha256" (the `src/` modules the script imports, by `ast`), "result":
  "pass" | "exception", "reason", "date"}`; bench modules are `exception` "needs the bench bridge (network, WLAN
  role-reversal)" unless their functions run against `TwinBoard`; silicon-only checks keep their named reason
  (`scheduler_saturation_drop.py` "needs the rp2 scheduler", A.U26.58; the UART precondition "silicon-only", A.U26.59;
  `reset_code_boot_phase_hang.py` "watchdog reset needs silicon", A.C.12). Written first in U26 (the runner's landing),
  re-recorded at both GC stages after B2's last and B3's last hardware-facing change (A.U35.49), and after every phase-C
  delta that touches an instrument.
- **Resolved**: —
- **Unit**: stage 1 U26; stage 2 U35 (the full re-record); a re-record follows every later instrument change (the L0
  check enforces it).
- **Depends**: M.HW_BENCH.091; A.U26.05 (4) (the recorder, SCR).
- **Blast carried by**: `tests_scripts/test_twin_record.py` (entry per file, hashes current, reasons non-empty) →
  A.U26.05 (TSC); `scripts/record_twin_instrument_runs.py` → A.U26.05 (SCR); fidelity-table rows from the review →
  A.U35.49 (TWIN); README habit 5 → M.HW_BENCH.121.
- **Kind**: test

## tests_hardware/bench/conftest.py (new)

### M.HW_BENCH.060 The bench tier proves the board runs this round's image first
- **From**: A.U26.03, A.S0930.06 (1) (the record's `deviceToml`/`uartCrc` keys the check reads), A.U26.85 (the
  record's `overrides`), A.C.09 (`--image-record` at a throwaway worktree's record), A.U26.27 (1) (its bench DebugLevel
  fixture: merged into M.HW_BENCH.006, not written here), A.U35.05 (`tests_hardware/bench/` index row: blast-only, the
  soak observers it names are M.HW_BENCH.016's).
- **Site**: new `tests_hardware/bench/conftest.py`.
- **Change**: module docstring (≤ 3 lines). Autouse session fixture `board_image(dut_ip, bench_device_name, request) ->
  dict[str, object]`: loads the record at `--image-record` (default `build/firmware-<bench device>.json`; missing →
  `pytest.exit("no image record at <path>: build the bench image with scripts/build_firmware.py before a bench run",
  returncode=1)`); asserts `record["device"] == bench_device_name`; `GET /system` strict (200, object, `build` present)
  and `build.BuildDate == record["BuildDate"]` (the key as A.U10.40 spells it; the record follows); 
  `micropython_overrides.check_lwip_ensemble(record["lwip"], record["maxConnections"]) == []`;
  `record["maxConnections"] == configured_max_connections()`; any mismatch → `pytest.exit(<both values>, "the board is
  not running the image this round built — reflash it, or rebuild from this tree", returncode=1)`. A `record["dirty"]`
  image (a throwaway-worktree build: the control, CRC16 or no-threshold image) is reported through
  `record_session_note(…, source="board_image")` "local-only image: revert after this round"; `overrides` and `uartCrc`
  are written into the same note so the run record names which image ran. A test that reflashes mid-session (CRC16,
  control image) re-runs the same comparison against the record of the image it flashed (a module-level
  `check_image(dut_ip, record)` the fixture also calls).
- **Resolved**: A.U26.27's separate `debug_level_checked` is not written (M.HW_BENCH.006 Resolved); `check_image()` as a
  callable is what A.S0930.06 (3)'s "A.U26.03's image check passes" after its restore reflash needs.
- **Unit**: U26.
- **Depends**: A.U26.02/A.S0930.06 (1)/A.U26.85 (the record and its keys, SCR), M.HW_BENCH.001, M.HW_BENCH.004,
  M.HW_BENCH.010, A.U10.40.
- **Blast carried by**: L0 `tests_scripts/test_board_image_fixture.py` (equal/different date, device, ensemble finding,
  missing record) → A.U26.03 (TSC); README "Verify the image" → M.HW_BENCH.126; "How a round runs" → M.HW_BENCH.123.
- **Kind**: code, hardware (Round: every bench round's first step [H04])

## tests_hardware/bench/_load.py (new)

### M.HW_BENCH.061 One shared reader worker for the bench load arms
- **From**: A.U26.78 (2), A.U26.54 (1) (answered counts), A.U26.50 (the worker guard's rules), A.U26.82/A.U26.87/
  A.S0930.29 (5)/A.S0930.40 (4) (users).
- **Site**: new `tests_hardware/bench/_load.py`.
- **Change**: `sensors_reader(dut_ip, iterations, record: Callable[[str], None], answered: list[int] | Counter, *,
  timeout_s, check=_schema_sanity_findings) -> None`: one module-level worker that GETs `/sensors` `iterations` times
  through `http_client.fetch`, inside `try/except (OSError, http_client.HTTP_ERROR)` recording each failure, counts every
  answered (2xx, parsed) response, and runs the schema check on each body; `start_readers(n, …) ->
  list[threading.Thread]` and `join_all(threads, timeout_s)` (joined in the caller's `finally`). `_schema_sanity_findings()`
  moves here from `test_bus_concurrency_under_api_load.py` with its ranges read from the drivers' `_VAL_*` tuples by
  `ast` (A.U26.49 (1)) and the plausibility bounds of M.HW_BENCH.043.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.030, M.HW_BENCH.043.
- **Blast carried by**: the six nested `get_sensors_worker` copies and A.U26.32's arm → M.HW_BENCH.064/.065; the UART
  load tests → M.HW_BENCH.093; the clone check (excludes nothing here) → A.U26.78 (3) (TSC); the worker guard reads it
  → A.U26.50 (TSC).
- **Kind**: code

## tests_hardware/bench/dns_probe.py

### M.HW_BENCH.062 The DNS probe can ask for any QTYPE
- **From**: A.U18.01 (blast assigned to U26's site: `build_query()` gains `qtype`; no U26 action carries it), A.U18.02
  (blast-only: no query changes shape), A.U8C.44, B1 (`src/captive_dns.py` → `src/asy_captive_dns.py` in the docstrings).
- **Site**: `tests_hardware/bench/dns_probe.py:14-24`, `:27`, `:43-46`.
- **Change**: `build_query(hostname, qtype: int = 1) -> tuple[bytes, bytes]` packs `qtype` (QCLASS IN);
  `query(server_ip, hostname, timeout_s: float = _QUERY_TIMEOUT_S, raw_query=None)` with `_QUERY_TIMEOUT_S = 5.0`
  (`l4.dns_probe_query_timeout_s`); `extract_answer_ip()`'s comment: "the captive DNS answers an A/ANY query with
  exactly one A record and every other type with an empty NOERROR reply (SPECIFICATION.md C.7.5)"; a new
  `answer_count(response) -> int` (ANCOUNT, `None`-safe on a short packet) for the AAAA assertion.
- **Resolved**: —
- **Unit**: U26 (after A.U18.01, U18).
- **Depends**: A.U18.01 (C.7.5).
- **Blast carried by**: the AAAA query in the role-reversal module → M.HW_BENCH.072.
- **Kind**: code

## tests_hardware/bench/test_boot_order_and_triggers.py (new)

### M.HW_BENCH.063 The boot order and the trigger spacing, observed on silicon
- **From**: A.U26.41 (1)(2), A.U7.24/A.U26.51 (module constants), A.U26.22 (the boot log saved as evidence).
- **Site**: new `tests_hardware/bench/test_boot_order_and_triggers.py`.
- **Change**: as A.U26.41 (1)-(2): `test_webserver_answers_before_the_first_ntp_sync_completes(board, bench, dut_ip,
  result_note)` — `kick_then_reset()`, then a `tail_log()` thread stamping each line with `time.monotonic()` and a
  `GET /status` poller every `_STATUS_POLL_S = 0.5` s (`l4.boot_order_status_poll_s`) for `_BOOT_WINDOW_S = 90.0`
  (`l4.boot_order_window_s`); asserts every boot line (`harness.boot_lines()`) precedes the first 200, and the first 200
  precedes the first `RTC set to:` line or arrives while `NTP sync starting.` is the latest NTP line; saves the stamped
  log through `evidence.save_text("boot-log.txt", …)` (the round's boot log) and records the STA-connect-to-first-200
  time as `l4.dut_serving_after_sta_s`'s measured figure (`result_note`). `@pytest.mark.soak_duration
  test_bus_triggers_keep_their_minimum_spacing(board, dut_ip, request, result_note)` — the duration from
  `--soak-duration`, DebugLevel 5, each `sensor trigger` event line stamped per module, modules grouped by the bench
  TOML's bus sharers, the minimum gap between two modules' triggers on one bus ≥ the design stagger read from
  `expected_facts()` (never copied), SCD30's data-ready reads excluded; the distribution reported. Both restore serving
  in `finally` (`restore_board_to_serving()`). `COVERS_TWIN_SCENARIOS` as A.U7.24 requires (the L2 boot-order run).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: A.U20.06, A.U20.07 (order and `expected_facts()`), M.HW_BENCH.015, M.HW_BENCH.016, M.HW_BENCH.055.
- **Blast carried by**: `tests_scripts/test_bench_restores_serving.py` (no device script: n/a) → A.U26.41; the L2 half
  → A.U20.07 (TWIN); Part N `l4.dut_serving_after_sta_s` row → A.U26.41 (SPEC); twin record entry → M.HW_BENCH.092.
- **Kind**: test, hardware (Round: every round's boot log, R1 [H06]; the trigger run R5 long [H19])

## tests_hardware/bench/test_bus_concurrency_under_api_load.py

### M.HW_BENCH.064 One reader worker, counted floors, tagged bounds, derived checks
- **From**: A.U26.78 (2), A.U26.54 (1), A.U26.49 (1) (`:19-30`, `:58-78`), A.U26.76 (`:9, 42, 58`), A.U26.22 (2)
  (`reset_all_error_logs` reasons), A.U26.65 (`:25-55` ceiling-close wrapper comment; `:45` "(F15)" dropped, A.U36.544
  (3)), A.U26.70 (`is_ceiling_close`
  user), A.U26.50 (the local `fetch` wrapper is a fetching call), A.U26.51/A.U7.24 (`COVERS_TWIN_SCENARIOS =
  ["bus_hazard_concurrency"]`), A.U26.29 (`:364-379` fallback), A.U7.15 (`:379`), A.U0.18 (`:1` owner tag), A.U36.544
  (4)/(5) (`:73` C.8 pointer, `:124` item 6), A.U8C.45, A.U8C2.16; blast-only, hold: A.U13.R02 (5) ("runs unchanged
  and must pass"), A.U12.18, A.U15.12/.13/.25/.R01/.R02/.S01, A.U30.07, A.U35.09 (matrix row), A.U35.50 (four-tier
  check: a missing cell it finds is a U35 delta).
- **Site**: `tests_hardware/bench/test_bus_concurrency_under_api_load.py:1-160` and every worker (`:91, 172, 252, 321,
  413, 503`), `:364-385`.
- **Change**: header (≤ 3 lines): "Bench-tier automated tests (the owner's suggested angle, 2026-09-03): heavy API load
  through the full HTTP stack against every bus at once — the bench counterpart of flash/test_bus_concurrency.py
  (SPECIFICATION.md C.8)." The six nested `get_sensors_worker` copies become `_load.sensors_reader(...)` threads with
  their answered counters; each test asserts `sum(answered) >= _MIN_ANSWERED[<test>]`, a per-test tunable
  `l4.bus_concurrency_under_api_load_<arm>_min_answered` (Part N, "estimated (agent, <commit>) — measured in phase
  C", margin stated), and the post-fault `/status` wait (recovery). `CO2_MIN_PPM…VOC_MAX` and `_schema_sanity_findings()`
  leave the file (→ `_load.py`, `plausibility_bounds.py`). The local `fetch` keeps its name and positional signature
  (the wear guard reads PUT bodies by it) with `json_body: JSONObject | None`; its comment names defect, bound and
  removal (A.U26.65: "a ceiling refusal under concurrent load is the stack's reject-when-full, not a fault; ≤
  `_CEILING_RETRY_ATTEMPTS` per call; remove if the arms ever run below the ceiling"); `attempt ==
  _CEILING_RETRY_ATTEMPTS - 1`. Every `reset_all_error_logs(dut_ip)` → `reset_all_error_logs(dut_ip,
  request.node.name)`. The flap arm's fallback (`:364-379`) → `recover_by_reset(…, skipped="error-log-empty checks for
  SCD30, BMP3XX, SGP40, ISL29125, FRAM", note=result_note, description="WiFi flapping under bus load")`. The `:73`
  comment states the reason in place ("SGP40's own data field: a torn read of it is what this watches for"), `:124`
  → "(SPECIFICATION.md F.2)". Constants per A.U8C.45/A.U8C2.16 (`_GET_ITERATIONS_PER_WORKER`, `_PUT_RESET_COUNT`,
  `_FETCH_TIMEOUT_S` 15.0, `_CEILING_RETRY_BACKOFF_S` 0.25, `_CEILING_RETRY_ATTEMPTS` 3, `_JOIN_TIMEOUT_S` 120.0,
  `_PROBE_TIMEOUT_S` 10.0, `_RECOVERY_TIMEOUT_S` 30.0, `_RECOVERY_POLL_S` 2.0, `_DEGRADED_FETCH_TIMEOUT_S` 20.0,
  `_DEGRADED_JOIN_TIMEOUT_S` 180.0, `_NTP_RESYNC_TIMEOUT_S` 20.0, `_NTP_RESYNC_POLL_S` 1.0, `_FLAP_STEP_S` 3.0 and
  `_FLAP_CYCLES` 3 (the shared `l4.network_resilience_flap_*` IDs), `_FLAP_RECOVERY_*`, `_REBOOT_READY_*` (the latter
  two now `recover_by_reset`'s waits), `_ISL29125_WRITE_CYCLES` 4), the join messages interpolating their constant.
  `COVERS_TWIN_SCENARIOS = ["bus_hazard_concurrency"]`.
- **Resolved**: A.U8C.45's tags on the six worker bodies' literals move with the bodies into `_load.py`'s call
  arguments (the constants stay here and are passed). A.U36.544 (U36) edits two comments the U26 rewrite keeps:
  stage 2.
- **Unit**: stage 1 U26; stage 2 U36 (`:73`, `:124` pointers).
- **Depends**: M.HW_BENCH.061, M.HW_BENCH.043, M.HW_BENCH.050, M.HW_BENCH.015, M.HW_BENCH.004, A.U8.01-03.
- **Blast carried by**: Part N rows → A.U8C.45/A.U8C2.16/A.U26.54 (SPEC); `pyproject.toml:336-337` S112 comment "counted,
  and floored" → A.U26.54 (TSC); the persistence-write guard reads the `fetch` PUT bodies (unchanged) → A.U26.06 (TSC).
- **Kind**: test, hardware (Round: R1 default; gated arms R3 [H16, H32, H71, H73])

### M.HW_BENCH.065 The bench hazard arms: SCD30 write, re-trigger proof, erase and reboot under load
- **From**: A.U26.32, A.U4.07 (`:474-476` comment), A.U26.71 (`:270-285`), A.U26.23 (sibling set derived),
  A.S0930.29 (5), A.S0930.40 (4), A.U26.09 (budget rows), A.U26.47 (markers over the window).
- **Site**: `tests_hardware/bench/test_bus_concurrency_under_api_load.py:229-305` (NTP arm), `:474-476`, new tests at
  the end.
- **Change**: (1) NTP arm (`:229-305`): loses `@pytest.mark.persistence_write`; its unchanged-value `NTP_Host` PUT
  asserts `"Unchanged"` (the proof nothing is written) and no longer claims a re-trigger; the NTP attempt that meets the
  block is the client's own retry timer inside a block sized to contain it (period read from `src/asy_ntp_client.py` by
  `ast`), asserted by an NTP failure entry or `NTPSynced` false during the block; comment `:275-276` rewritten; joins
  `_JUSTIFIED_UNMARKED` with its reason. (2) `:474-476` → gone: the SCD30 arm below replaces it. (3) New
  `@pytest.mark.persistence_write @pytest.mark.scd30_extra_write
  test_scd30_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load(board, dut_ip, request, result_note)`
  as A.U26.32: reads `TempOffs`; the writer PUTs two alternating values original ± 0.5 K within `_VAL_TO`'s range (read
  by `ast`), `_SCD30_WRITE_CYCLES = 2` (`l4.bus_concurrency_under_api_load_scd30_write_cycles`), each PUT asserting
  `"Valid"`; restore in `finally` asserting `"Valid"`/`"Unchanged"`; readers through `_load.sensors_reader`; afterwards
  every bus-sharing sibling's log empty (the logger set of `harness.fram_backed_logger_names()` restricted to the SCD30's
  bus sharers from `bench_facts`); banner (≤ 3 lines): "PUT /sensors reaches SCD30's NVM through its chip store: two
  owned writes and the restore, gated (tests_hardware/README.md budget table)." (4) `test_fram_erase_under_api_load`
  (A.S0930.29 (5)): `save_errcount(dut_ip, …)` and `save_fram_raw(board, …)` first; `erasefram` while the hammer runs →
  `"Valid"`; reboot with `ResetReason` 8 (never 2); serving afterwards; every FRAM-backed log empty (derived set). (5)
  `test_reboot_under_api_load` (A.S0930.40 (4)): `save_errcount()` first; `reboot` under the hammer → `"Valid"`,
  `ResetReason` 3, serving, every FRAM-backed history ⊇ the saved one. (4) and (5) unmarked (FRAM only / no write), each
  over `observe_during()` with `crash_lines()` empty and the API floor asserted.
- **Resolved**: A.U4.07 (U4) rewrites the false comment; A.U26.32 (U26) replaces it with the test it calls for — the
  U4 text lives from U4 to U26.
- **Unit**: stage 1 U4 (`:474-476` comment); stage 2 U26 (the rest; SUPP_owner_0930's tests land with U26).
- **Depends**: M.HW_BENCH.061, M.HW_BENCH.010, M.HW_BENCH.012, M.HW_BENCH.016, M.HW_BENCH.050, A.U4.04, A.U4.02
  ("Unchanged"), A.U6.17 (derived field classes), A.S0930.09-.17/.31 (the commands), A.U11.05 (codes).
- **Blast carried by**: `_JUSTIFIED_UNMARKED` and the derived dispatch classes → A.U26.71 (TSC); the erase/reboot tests
  unflagged by the guard → A.S0930.19/A.U26.06 (TSC); budget rows → M.HW_BENCH.130; the L2 SCD30 write arm →
  A.U15.R01 (TWIN); four-tier rule rows → A.U35.50.
- **Kind**: test, hardware (Round: (3) R3 gated [H32]; (1), (4), (5) R1 default [H13, H14, H73])

## tests_hardware/bench/test_end_to_end_timing.py

### M.HW_BENCH.067 A commanded reboot over REST is attributed and bounded, waited for passively
- **From**: A.U26.28 (1), A.S0930.40 (1) (header `:19-21`, the reply-to-loss bound), A.U26.41 (3) (`:44-46` wait
  comment), A.U26.29 (2) (`:48-53` fallback), A.U8C.46 (`:40, :41, :46, :49, :53`).
- **Site**: `tests_hardware/bench/test_end_to_end_timing.py:19-53`.
- **Change**: header comment (≤ 3 lines): "A commanded reboot over REST runs the controlled shutdown and resets through
  the armed timer, never the watchdog, on real timing." The test (`board, bench, dut_ip, result_note`): the PUT asserts
  `"Valid"`; `kick_all_stations()`; the time from the reply to `not board.is_device_present()` is asserted ≤
  `_TASK_CHECK_TIME + _RESET_DELAY` plus `_REBOOT_LOSS_MARGIN_S` (`l4.end_to_end_timing_reboot_loss_margin_s`) and ≥
  `_RESET_DELAY` (constants read from `src/asy_system_service.py` by `ast`), the margin itself asserted below `8000 −
  (_RESET_DELAY + _TASK_CHECK_TIME) * 1000` ms with the generated `WDT(timeout=…)` read from the generated module (so
  the upper bound excludes a watchdog reset, which records the same code); then passively `is_device_present()` again
  and `GET /status` 200 through `recover_by_reset(…, skipped="the passive post-reboot wait", description="REST reboot")`
  (no `is_reachable()`, which would stop the fresh `main.py`); asserts `status["system"]["ResetReason"] == 3` (never 2)
  and SYSTEM's log holds no task-end entry (`assert_no_task_ended`); records the measured reply-to-loss time and its
  S2-S4 share (`result_note`). The `:26-28`/`:42-44` comments collapse into one ≤ 3-line note (passive waits only; the
  webserver serves within `l4.dut_serving_after_sta_s` of STA connect, the generated `main()` starting it before the
  first NTP sync). Constants: `_REBOOT_PHASE_TIMEOUT_S = 30.0`, `_DOWN_POLL_S = 0.5`, `_READY_PROBE_TIMEOUT_S = 5.0`,
  `_SERVING_POLL_S = 2.0` (B4); the `:41` `is_reachable` wait and its `_POLL_S` use go.
- **Resolved**: A.U26.28 (1) and A.S0930.40 (1) both rewrite this test: A.U26.28's passive wait and code assertion,
  A.S0930.40's timing bound and header — combined; A.U26.41 (3)'s "webserver within ~N s" wording rides in the one note.
- **Unit**: U26.
- **Depends**: A.U11.05 (`ResetReason`), A.S0930.31/.33 (reboot through the sequence), M.HW_BENCH.015, M.HW_BENCH.051,
  M.HW_BENCH.004, A.U20.06.
- **Blast carried by**: README "Reset codes proven on the bench" row 3 → M.HW_BENCH.119; Part N margin row →
  GAP-B7 (SPEC: `l4.end_to_end_timing_reboot_loss_margin_s` has no tagging action — A.S0930.40 names "a named
  margin").
- **Kind**: test, hardware (Round: R1 [H10, H14])

### M.HW_BENCH.068 The burst, cold-boot and backup-reset tests claim only what they assert
- **From**: A.U26.52 (2) (`:85-88`), A.U26.01 (blast: `:66` unchanged call), A.U31.04 (`:91-94, :105, :109`), A.U35.40
  (1)(2), A.U0.28 (`:121` owner tag), A.U26.29 (2)(3) (`:146-165`, `:189-203`), A.U26.22 (2) (`:129, :206` reasons),
  A.U36.544 (5) item 9 (`:149`), A.U8C.46 (`:72, :81, :88, :105, :106, :115, :130, :136, :143, :153, :154, :162, :163,
  :173, :177, :178, :183, :191, :192, :200, :201, :204, :211`), A.U8C2.17 (`:142`), A.U7.24/A.U26.51
  (`COVERS_TWIN_SCENARIOS = ["webserver_concurrency", "sensortask_integration", "poll_prewarm"]`), A.U26.76/B8 (no `Any`
  here: holds).
- **Site**: `tests_hardware/bench/test_end_to_end_timing.py:56-215`.
- **Change**: (1) Burst: the final check is `http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_PROBE_TIMEOUT_S)
  .status_code == 200` alone; its comment says a crash surfacing after the burst is what it catches. (2) Cold boot:
  banner `:92-93` "… + sensor-init latency, reported." / "Reported with a sanity ceiling, never asserted against a tight
  bound: boot latency is not a metric (CLAUDE.md), only the watchdog feed margins are (SPECIFICATION.md Part F.3).";
  `:105` → "sanity ceiling only - see the banner above"; `:109` → "reported, never asserted (boot latency is evidence, not
  a target)" — the print becomes `result_note`. (3) Backup resets (`persistence_write` stays: the test owns the
  `BackupPeriod` PUT): banner `:121` "(owner's explicit request)" → "(owner, 2026-09-04)"; `reset_all_error_logs(dut_ip,
  request.node.name)` at both ends; the recovery after each of `_RESET_CYCLES` resets goes through `recover_by_reset(…,
  skipped="the passive reconnect after this reset", description=f"reset {n} during a natural backup")`, each recovery a
  recovery note; the `:149` pointer → "(tests_hardware/README.md 'Known assumptions and open findings')"; `:168-169`
  → `assert_module_error_log_empty(dut_ip, "SGP40")` and `assert_module_error_log_clean(dut_ip, "FRAM",
  allowed_warnings=(code("W", <dual-copy recovery>), code("W", <both copies lost>)), allowed_errors=(code("E", <status-byte
  write failure>),))` with the comment "Three hard resets landing inside real SPI writes are meant to tear some: exactly
  the status-byte failure and the two dual-copy recovery warnings are allowed, anything else fails, and a fresh backup
  must still complete below (owner, 2026-09-13)."; the restore's reachability fallback (`:184-203`) → one
  `recover_by_reset(…, first_wait_s=_RESTORE_RECOVERY_TIMEOUT_S, …)`. Constants per A.U8C.46/A.U8C2.17 (B4).
- **Resolved**: A.U26.29 lists `:48-53, 189-200` as fallbacks and `:146-156` as a reported retry loop; with
  `recover_by_reset()` the loop's retry and the restore's fallback both become its calls (one mechanism, each use a
  recovery note). The catalog names of the three FRAM codes are A.U2.01's (the HEAD numbers 31/71/72 are not written).
- **Unit**: stage 1 U26 ((1), (2), the recovery helper, reasons, tags); stage 2 U35 (A.U35.40's assertion and comment);
  stage 3 U36 (`:149` pointer).
- **Depends**: M.HW_BENCH.015, M.HW_BENCH.050/.052, A.U2.01/A.U2.03 (catalog), A.U31.04's SPEC F.3 table (U31).
- **Blast carried by**: README "Known assumptions and open findings" (the hotspot-fallback bullet of A.U36.544 and the
  torn-write bullet of A.U35.40) → M.HW_BENCH.131; Part N rows → A.U8C.46/A.U8C2.17 (SPEC); twin record → M.HW_BENCH.092.
- **Kind**: test, hardware (Round: R1 default; the backup-reset test R3 gated [H68])

## tests_hardware/bench/test_heap_under_connection_ceiling.py

### M.HW_BENCH.069 The ceiling heap test names its threshold and its instrument values
- **From**: A.U8.05 (`:25-40` IDs), A.U8C.47, A.U8C2.18, A.U26.48 (1), A.U26.68 (facts and `DONE`), A.U26.01 (blast:
  `:115, :164` unchanged calls), A.U26.10 (blast: `:114`'s script keeps `cfg_path=""`, a listed prerequisite),
  A.U7.24/A.U26.51 (`COVERS_TWIN_SCENARIOS`), A.U30.20 (blast: `_MIN_FRACTION_AT_CEILING` is a fraction of time at the
  ceiling, not of free heap — holds), A.U8C.73 (the device script's tags, HW_DEV), A.U36.532 (`H.7.1` citers keep their
  number).
- **Site**: `tests_hardware/bench/test_heap_under_connection_ceiling.py:1-172`.
- **Change**: `PER_CONNECTION_ALLOCATION = 2048` carries the `web.max_content_length` mirror tag; stacked or single
  tags on `_HOLD_S` (`l4.ceiling_hold_s`), `_DRIP_INTERVAL_S`, `_RECYCLE_S`, `_MIN_FRACTION_AT_CEILING`,
  `_ADMISSION_WAIT_S` (A.U8.05's IDs); new `_HOLDER_SOCKET_TIMEOUT_S = 5.0`, `_WORKER_JOIN_S = 10.0`,
  `_SCRIPT_TIMEOUT_S = 240.0`, `_HAMMER_JOIN_S = 30.0`, `_REFUSED_BACKOFF_S = 0.1`, `_STAGGER_MARGIN_S = 2.0`,
  `_SAMPLE_STEP_S = 0.25` (B4). The test reads `facts = harness.parse_facts(output)` (requires `DONE`), requires the
  `gc_threshold` fact, prints it beside every heap figure (`result_note`, not `print`), and every assertion message
  names it ("at GC_THRESHOLD=<n>: …"). The two `print("[HW] …")` reports become `result_note` calls; the wall test
  keeps `over_provisioned_image` and its `pytest.fail` text. `COVERS_TWIN_SCENARIOS = ["webserver_concurrency",
  "sensortask_integration", "poll_prewarm"]`.
- **Resolved**: A.U8C.47 repeats A.U8.05's six IDs ("already created … nothing further") — one tag each.
- **Unit**: U26 (U8 tags with it).
- **Depends**: M.HW_BENCH.012 (`parse_facts`), M.HW_BENCH.017, M.HW_BENCH.004, A.U8.01-05.
- **Blast carried by**: `heap_under_connection_ceiling.py`'s `FACT` lines → A.U26.68 (HW_DEV); Part N rows → A.U8.05/
  A.U8C.47/A.U8C2.18 (SPEC); README "Measuring heap" → M.HW_BENCH.132.
- **Kind**: test, hardware (Round: R1 [H40, H44]; the wall test on an over-provisioned image only when a round's plan
  names it)

## tests_hardware/bench/test_hotspot_role_reversal.py

### M.HW_BENCH.071 The role-reversal fixture restores on every path and records what it proved
- **From**: A.U26.39 (1)-(3)(5), A.U26.49 (2) (`:43` literal, RF342 comment), A.U26.65 (`:27-41` join re-verify
  retry comment), A.U7.15 (`:97, :102`: superseded by A.U26.39 (2), dropped), A.U26.22 (2) (reasons), A.U26.01 (5)
  (`:289` `device=`), A.U0.07 (`:248, :296, :335` imports, B6), A.U26.76/B8, A.U8C.48 (`:27, :33, :38, :68, :80, :86,
  :95, :109, :115, :121`), A.U7.24/A.U26.51 (`COVERS_TWIN_SCENARIOS = ["real_website_integration",
  "sensortask_integration"]`), A.U28.29 (blast: the S105 entry for this file goes with the literal).
- **Site**: `tests_hardware/bench/test_hotspot_role_reversal.py:1-125`, `:132-160`.
- **Change**: docstring (≤ 3 lines) drops "Definition order matters - see stage 6 below" (order is enforced,
  M.HW_BENCH.073). `_HOTSPOT_PASSWORD` and its stale comment go; every join uses `harness.hotspot_password()`.
  `_join_dut_hotspot_with_reverify_retry(bench, ssid, password, *, attempts=_JOIN_ATTEMPTS)` keeps its loop; its
  comment (≤ 3 lines) names defect, bound and removal ("nmcli's own rescan can miss a hotspot is_ssid_visible() just
  saw; ≤ _JOIN_ATTEMPTS joins; remove when a round records no re-verify retry"), each retry used reported through the
  `note` callable it now takes. `joined_hotspot(board, bench, dut_ip, hotspot_ssid, request)`: stage 0 reads and keeps
  the SSID; stages 0-2 run inside a `try`: on any exception after the stage-0 PUT it tries (bounded) to reach the DUT
  over its hotspot and PUT the saved SSID back, then restores the bridge; if that fails it raises naming the stranded
  state and the serial-side repair (README recipe) — never a silent exit. It records the scanned SSID list, the password
  it joined with and the association time (a module-level `_JoinRecord` the tests read). Stage 7: a rejected or
  unreachable restore raises (`HardwareTestFailureError`), reported by pytest as a teardown error beside any test
  failure. Stage 8: after leaving the hotspot, `recover_by_reset(board, bench, ready=…, skipped="the passive STA
  reconnect after the flip back", note=<record_session_note bound to "joined_hotspot">, description="role flip back")`,
  then `GET /networking` over the bridge must report the STA mode (the phase left `_PHASE_DEACTIVATED`) — the loud raise
  follows if not. Content: `test_dut_enters_hotspot_mode_after_ssid_cleared` asserts `GET /networking` over the hotspot
  reports the hotspot mode; `test_hotspot_ssid_matches_configured_hostname` asserts the recorded scan contained
  `hotspot_ssid`; `test_hotspot_password_matches_known_fixed_value` → `test_the_dut_accepts_the_toml_hotspot_password`
  asserting the recorded join password equals `harness.hotspot_password()` (the source-equality check is L0, A.U26.49);
  `test_bench_radio_associates_within_bounded_window` asserts the recorded association time ≤ `_JOIN_HOTSPOT_TIMEOUT_S`.
  `test_real_static_website_content_serves_over_the_hotspot_link` passes `device=bench_device_name`. Constants per
  A.U8C.48 (B4); `import socket` at module top.
- **Resolved**: A.U7.15 (U7) would route the two stage-7 notes through `record_session_note`; A.U26.39 (2) (U26,
  G1/R28 "a rejected restore fails loudly") turns them into a raise — A.U7.15's two sites are dropped (no hardware run
  falls between U7 and U26). The `request` parameter A.U7.15 adds stays (stage 8's note uses it).
- **Unit**: U26.
- **Depends**: M.HW_BENCH.010, M.HW_BENCH.015, M.HW_BENCH.004, M.HW_BENCH.037, M.HW_BENCH.023, A.U18.28 (an active AP
  reports `STAT_GOT_IP`: blast-only, the real AP already does).
- **Blast carried by**: `_KNOWN_PERSISTING_HELPERS` keeps `joined_hotspot` (its "stage-0 PUT … stage-7 restore"
  comment holds) → A.U26.39 (TSC); `tests_scripts/test_tests_hardware_conftest_constants.py` (the password pin) →
  A.U26.49 (TSC); README role-reversal section and the serial-side repair recipe → M.HW_BENCH.124.
- **Kind**: test, hardware (Round: R1 for stages 0-5, R3 for stage 6 [H62, H73])

### M.HW_BENCH.072 Captive DNS, REST and client faults over the hotspot: every check proves its effect
- **From**: A.U26.04, A.U26.15 (1) (`:275-281` WarnCO2), A.U26.40 (`:244` rename), A.U26.55 (3) (`:334-351`), A.U26.56
  (2)(3) (`:230-240`), A.U26.63 (DHCP scope), A.U18.01 (blast: the AAAA query, "U26 site"), A.U19.20 (blast: `:269`'s
  hand-copied route set, uncovered by A.U26.80), A.U26.71 (blast: the WarnCO2 PUT stays marked), B1 (`src/captive_dns.py`
  → `src/asy_captive_dns.py` in comments `:202, :211, :221, :227`), A.U36.544 (4) (`:322` "Part A.5" pointer), A.U36.544
  (3) (the stage banners' "(item 4)", "(items 5-7)", "(items 8-13)", "(items 14-16)", "(items 17-19)" at `:151, :160,
  :191, :264, :330` dropped; the stage names stay), A.U8C.48
  (`:185, :251, :254, :258, :270, :287, :300, :324, :339, :348, :361, :363`), A.U8C2.19, A.U0.35 (blast: `:3`'s
  docstring is the network module's).
- **Site**: `tests_hardware/bench/test_hotspot_role_reversal.py:164-370`.
- **Change**: (1) DHCP lease test: `own = bench.own_ip_on().split(".")`, `gw = joined_hotspot.split(".")`; asserts
  `own[:3] == gw[:3]` and `16 <= int(own[3]) <= 23`, the message naming both addresses; comment "The AP's DHCP server is
  MicroPython's `shared/netutils/dhcpserver.c` (v1.29.0): it leases the server's own first three octets and a last
  octet `16 + n`, `n < 8` (`dhcpserver.h:31-32`, `dhcpserver.c:238`)."; the `:179-180` comment → "MicroPython's C DHCP
  server (`shared/netutils/dhcpserver.c`), compiled into the firmware - no project code". (2) New
  `test_an_aaaa_query_gets_an_empty_answer(joined_hotspot)`: `dns_probe.query(…, raw_query=build_query("www.example.com",
  qtype=28)[0])` answers with ANCOUNT 0 (`dns_probe.answer_count()`). (3) `:244` →
  `test_dns_flood_leaves_captive_dns_serving_and_it_recovers` (body unchanged, constants B4). (4) Off-subnet spoof: the
  skip marker goes; `test_spoofed_off_subnet_source_address_is_ignored(bench, joined_hotspot)` sends a well-formed DNS
  query from `203.0.113.5` through `sudo .venv/bin/python tests_hardware/spoof_udp.py …`, captures with tcpdump on the
  radio for `_SPOOF_CAPTURE_S = 5.0` (`l4.hotspot_role_reversal_spoof_capture_s`) any packet from the DUT to
  `203.0.113.5` and asserts none, then asserts a legitimate query from the bench radio is still answered. If the phase-C
  attempt shows unreasonable effort or no case beyond L1-L3 (OR77.a), the skip returns with the recorded reason and the
  "(owner, 2026-09-26)" OR71.a (6) tag, as a delta (M.HW_BENCH.131's README line follows the result). (5) `:269`'s
  literal path list → `harness.get_routes(json_only=False) + ["/"]` (every registered GET route; `/notification`
  included). (6) WarnCO2 PUT (`persistence_write` stays): reads the current value (`GET /notification`), PUTs one that
  differs (1700, or 1750 if it already holds 1700), asserts `"Valid"`, restores the read value in `finally` asserting
  `"Valid"`/`"Unchanged"`. (7) Malformed request: a `TimeoutError` on the read fails ("the server neither answered nor
  closed a malformed request within 10 s"); accepted outcomes an HTTP 400-class status line or a close, each named. (8)
  `test_concurrent_multi_client_burst_is_out_of_scope_here` is deleted (its fact becomes the E.6 row "multi-client load
  in hotspot mode: one bench radio", A.U7.25). (9) `reset_all_error_logs(joined_hotspot, request.node.name)` at each
  call. Comments name `src/asy_captive_dns.py`; `:322`'s "Part A.5" → the section that states the toggle's cost, or the
  pointer goes (A.U36.544 (4), executor's read).
- **Resolved**: (2) and (5) are blast items their actions left on this file with no U26 carrier (A.U18.01 says "U26
  site"; A.U26.80 lists four route sites, not `:269`) — carried here. A.U36.544 (U36) edits one comment of the U26 end
  state: stage 2.
- **Unit**: stage 1 U26; stage 2 U36 (`:322` pointer).
- **Depends**: M.HW_BENCH.062, M.HW_BENCH.045, M.HW_BENCH.024 (capture helpers), M.HW_BENCH.010 (`get_routes`),
  M.HW_BENCH.050, A.U18.01 (C.7.5, QTYPE rule), A.U19.20 (route table), A.U7.25 (E.6 list), A.U21.26 (sudo rule).
- **Blast carried by**: the permanent-skip entry of A.U7.14's verdict and OR71.a (6)'s skip go when (4) works → A.U7.14
  (SCR; A.U26.56 (3) "A-C edits A.U7.14"); E.6 rows → A.U7.25/A.U26.39 (SPEC); README DHCP and injection sections →
  M.HW_BENCH.129; `pyproject.toml` S105/S106 for this file → A.U26.49/A.U28.29 (TSC).
- **Kind**: test, hardware (Round: R1 [H61, H73])

### M.HW_BENCH.073 Stage 6 runs last by marker; the flip back is a test of its own
- **From**: A.U26.39 (4)(5), A.U26.71 (`:380-392`), A.U0.35 (`:425-426` owner tag), A.U18.38 (blast: `:143-147` holds),
  A.U26.06 (the module-level `pytestmark` is read), A.U8C.48.
- **Site**: `tests_hardware/bench/test_hotspot_role_reversal.py:373-428`.
- **Change**: `test_invalid_credentials_rejected_without_triggering_reconnect` loses `persistence_write` (every field
  rejected) and asserts `result["PW"] == "Invalid"`, then no reconnect; it joins `_JUSTIFIED_UNMARKED` ("PW below
  `_VAL_PW`'s bound: rejected, nothing persists"). It and `test_real_credentials_put_succeeds_and_confirms_accepted_values`
  (`persistence_write` kept) carry `@pytest.mark.destructive_last`. `test_role_flip_back_and_reachability_are_asserted_in_fixture_teardown`
  and `test_post_condition_sta_connected_state_inferred_from_reachability` merge into one `destructive_last` test placed
  after the two stage-6 tests: it performs the flip back itself (restore SSID over the hotspot, leave the hotspot,
  `recover_by_reset`) and asserts STA reachability and `GET /networking`'s STA mode, so the fixture's teardown finds the
  work done; its comment: "No STA-phase field is added to /networking (owner, 2026-09-26: 'It seems to be unreachable by
  definition.'): a reachable board on the bridge network is STA-connected by definition." The banners `:373-377`,
  `:410-414` state the enforced order (the marker), not definition order.
- **Resolved**: A.U0.35's `:425-426` tag lands in the merged test's comment (the two tests it sat in merge in U26).
- **Unit**: U26 (A.U0.35's U0 tag on `:425-426` lands in U0 and moves with the merge).
- **Depends**: M.HW_BENCH.002/.003 (`destructive_last`), M.HW_BENCH.071, A.U4.02, A.U6.17.
- **Blast carried by**: `_JUSTIFIED_UNMARKED` → A.U26.71 (TSC); the collect-only "destructive items last" L0 →
  A.U26.39 (TSC); `test_tests_hardware_persistence_write_gating.py` deselection set shrinks by one → A.U26.71 (TSC).
- **Kind**: test, hardware (Round: R3, the destructive stage last of the round's gated bench rows [H62])

## tests_hardware/bench/test_memory_stress_bench.py

### M.HW_BENCH.074 The hammer and the soaks claim liveness, floor the readers, derive their sets
- **From**: A.U26.35 (1)(2), A.U26.54 (2), A.U26.23 (2), A.U26.26 (`:93, :169` copies), A.U26.67 (`:123`), A.U26.52 (4)
  and A.U26.80 (`:28`, `:145`), A.U36.512 (`:21` "variant": moot, the comment goes), A.U26.22 (2), A.U8C.49, A.U8C2.20,
  A.U19.20 (blast: the same two route sets), A.U7.24/A.U26.51 (`COVERS_TWIN_SCENARIOS`), A.U33.09 (blast: BACKLOG's S4
  row names the renamed test, DOCS), A.U35.05 (3) (the bench soak gate's twin arm), B1 (`SGPResetVOC` → `ResetVOC`).
- **Site**: `tests_hardware/bench/test_memory_stress_bench.py:1-174`.
- **Change**: imports `soak_durations.SOAK_DURATION_SECONDS`, `harness.{bench_device, boot_lines, crash_lines,
  fram_backed_logger_names, get_routes}`, `error_log_helpers.{assert_no_task_ended, errcount_entry, get_errcount,
  reset_all_error_logs}`. `_FRAM_BACKED_MODULES` and its stale comment go: the module set is
  `fram_backed_logger_names(bench_device())`. `_HAMMER_PATHS = tuple(get_routes())` (every registered JSON GET route,
  `/system` and `/notification` included); the soak reader's `paths` likewise. `_run_max_speed_hammer_load()` returns
  readers' answered count and the writer's accepted count separately. `_assert_no_crash_or_reboot(lines)` →
  `assert not crash_lines(lines)` and `assert not boot_lines(lines)` (its two comments go: the helper holds the reason
  once). Hammer: asserts readers' answered ≥ `_MIN_ANSWERED = 100` (`l4.memory_stress_bench_min_answered`) and
  `/status` serving afterwards (recovery); the writer's accepted count is reported (`result_note`), not asserted (writer
  starvation is accepted degradation, owner 2026-09-28). Extended hammer (`@pytest.mark.soak_duration`, skip text
  naming `scripts/run_bench_soak_tests.sh --duration mid`): the FRAM-backed set from the derived names through
  `errcount_entry()`; its docstring → a ≤ 3-line `#` block (B3) keeping "captures the FRAM-backed errcount in the
  assertion message before any clear (CLAUDE.md)". `test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic`
  → `@pytest.mark.soak_duration test_http_soak_stays_live`: no crash line, no boot line, `assert_no_task_ended()`, and
  failed requests ≤ `_SOAK_REQUEST_FAILURE_RATE` × requests sent (`l4.soak_request_failure_rate`, basis "estimated
  (agent, <commit>) — measured in phase C over the 6 h run"), counted host-side. Every `reset_all_error_logs(dut_ip)` →
  `(dut_ip, request.node.name)`. Constants: `_HAMMER_DURATION_S` (tag), `_FETCH_TIMEOUT_S = 5.0`, `_JOIN_TIMEOUT_S =
  10.0`, `_VOC_RESET_INTERVAL_S = 3.0`, `_SOAK_REQUEST_STEP_S = 0.2` (B4). Comment `:156` "(that's item 17's job)" →
  "(the hammer above is the flood)". `COVERS_TWIN_SCENARIOS = ["webserver_concurrency", "sensortask_integration",
  "poll_prewarm"]`.
- **Resolved**: `:107/:127`'s 100 carries A.U8C2.20's `l4.memory_stress_bench_min_successes` and A.U26.54's per-test
  floor form `l4.<test>_min_answered` — one constant, A.U26.54's ID and its readers-only meaning (F18 reading, OR83).
  `:174`'s 5 carries A.U8C2.20's `l4.memory_stress_bench_soak_error_max` and A.U26.35 (2)'s rate — A.U26.35 settles
  it (G1/R22 "re-derived per duration"); `_SOAK_ERROR_MAX` is withdrawn. `:156`'s "item 17" is an undefined label
  (A.U0.08 (d) "list IDs"; G9/R12) — rewritten here (B5).
- **Unit**: U26.
- **Depends**: M.HW_BENCH.040, M.HW_BENCH.010, M.HW_BENCH.016, M.HW_BENCH.050/.051, M.HW_BENCH.004, A.U19.20.
- **Blast carried by**: `scripts/run_bench_soak_tests.sh --duration`, the runners' `-m "not soak_duration"` → A.U26.35
  (SCR); Part N rows → A.U8C.49/A.U8C2.20/A.U26.35/A.U26.54 (SPEC); BACKLOG S4 row → A.U33.09/A.U36 (DOCS); README soak
  section → M.HW_BENCH.126.
- **Kind**: test, hardware (Round: hammer R1 [H83: `MemFree` floor polled during it]; soaks R5 [H64])

## tests_hardware/bench/test_modlwip_send_stall.py (new)

### M.HW_BENCH.075 The lwIP stall proof: reproduce on the control image, then show the override holds
- **From**: A.U26.85, A.C.06 (1) (C A-C note 1: the test takes the control image the round built through
  `--lwip-control-image`; no build in the test, no build flag), A.U21.14 (the proof's content and the bounds), A.U35.05
  (blast: a timing bound is check-style, proven red by a plant), AC_NOTES 21/24 (patched branch proven reached; a
  failed bound goes to the owner as an override change).
- **Site**: new `tests_hardware/bench/test_modlwip_send_stall.py`.
- **Change**: (1) `@pytest.mark.flash_cycle test_send_stall_on_the_unpatched_image(board, bench, dut_ip, request,
  result_note)`: reads `--lwip-control-image`; a missing option, a missing file, or an image record whose `overrides` is
  not `[]` fails (never skips) naming the cause; saves FRAM evidence (`save_errcount`, `save_fram_raw`); records the
  release image's record at start (`board_image`'s); `harness.reflash(board, <control .uf2>)`; `check_image(dut_ip,
  <control record>)`; runs exactly (2)'s hammer and bound checks and records each verdict, the fresh `GET /` time,
  whether the board stopped answering ≥ 5 s, and `ResetReason`/`SysUptime` after (a watchdog reset reads 2 with a boot
  line); in `finally` reflashes the release image recorded at start and waits for serving and `check_image()` — both
  flash cycles owned by this test. The verdicts are recorded; the test passes when the steps ran (the round plan expects
  the stall bound to fail there — a control run passing every bound means the hammer never reached the `ERR_MEM` loop,
  which the round reports, A.C.06). (2) `test_no_send_stall_with_the_override(board, dut_ip, result_note)` (default-on,
  no wear): `configured_max_connections() - 1` raw sockets each sending `GET /js/app.js` and never reading
  (`SO_RCVBUF` minimal), `_STALL_SETTLE_S = 2.0` (`l4.lwip_stall_settle_s`), then a timed `GET /` on a fresh
  connection; plus, per JSON route (`get_routes()`) and page asset (from the served `index.html`), a dead client and a
  slow client (`_SLOW_CLIENT_BPS = 256`, `l4.lwip_slow_client_bytes_per_s`); while they hold, a `GET /status` loop
  asserts each response ≤ `l4.lwip_spin_concurrent_request_max_s`; asserts no reboot (`BootSignature`, `SysUptime`),
  `assert_no_task_ended()`, zero allocation markers over `observe_during()`, and the patched branch reached — the page
  load completes within the bound while ≥ 2 connections sit at zero window (their host receive queues); after the
  clients close, `harness._wait_for_slots_to_drain()` frees every slot and a full page load succeeds. Each `ERR_MEM`
  source is driven to its edge and recorded (arena: few connections, large route; segment pool: many connections each
  queuing small writes; per-pcb queue: one connection, many small writes to a non-reading peer). A failed bound is
  reported for the owner as an override change (a short POLLOUT back-off), never a larger bound.
- **Resolved**: A.U26.85 (1) "the test itself builds the control image" → "takes the control image the round built"
  (A.C.06 (1), settled in C). The image record's `overrides` key is A.U26.85's Site on `scripts/build_firmware.py`
  (SCR).
- **Unit**: U26 (A.U21.14's override and host hammer land in U21).
- **Depends**: M.HW_BENCH.001 (`--lwip-control-image`), M.HW_BENCH.014, M.HW_BENCH.060 (`check_image`),
  M.HW_BENCH.016, M.HW_BENCH.017, M.HW_BENCH.050, A.U21.10/A.U21.13/A.U21.14, A.U26.02 + A.U26.85's `overrides` key (SCR).
- **Blast carried by**: Part N rows `l4.lwip_spin_concurrent_request_max_s` (A.U21.14) and the two new ones → GAP-B7
  (SPEC: no tagging action names them); BACKLOG's lwIP owed row names this module → A.U21.14 (DOCS); README flash-cycle
  list → M.HW_BENCH.130; the round builds the control image in a throwaway worktree → A.C.06 (C).
- **Kind**: test, hardware (Round: (2) R1 provisional, then R4 after (1) on the control image [H39, H40])

## tests_hardware/bench/test_network_resilience.py

### M.HW_BENCH.076 Header, outage and flap tests: one recovery helper, catalog codes
- **From**: A.U0.18 (`:1` owner tag), A.U0.35 (`:3`), A.U26.63 (`:1-3` docstring), A.U29.01 (blast: `:3` is SPEC
  A.11 row 10's source), A.U36.544 (5) (the docstring's "question #5", `:117` item 29), A.U7.15 (`:61, :68, :99, :106`),
  A.U26.29 (the `:63-68`, `:101-106` fallbacks join the helper: its no-bare-`hard_reset()` check would flag them),
  A.U2.03/A.U2.14/A.U18.36 (`:115-123` "wrnno=4/5"), A.U26.67 (`errcount_entry`), A.U26.22 (2) (reasons), A.U26.51/
  A.U7.24 (`COVERS_TWIN_SCENARIOS`), A.U8C.50 (`:44, :57, :58, :67, :70, :80, :82, :95, :96, :105, :108, :128`),
  A.U8C2.21 (`:78`), A.U18.R01 (blast: "unchanged"), A.U26.76/B8.
- **Site**: `tests_hardware/bench/test_network_resilience.py:1-131`.
- **Change**: docstring (≤ 3 lines): "Bench-tier tests for real WiFi outage and flap (owner's audit question,
  2026-09-01), NTP/DNS servers answering garbage (SPECIFICATION.md F.1, UDP on rp2/lwIP), the admission ceiling on
  silicon, malformed requests and slowloris. DHCP is not fault-injected: a documented known limitation (owner,
  2026-09-26; tests_hardware/README.md)." Outage and flap tests take `request, result_note`; the graceful-recovery
  timing stays a plain `result_note`; the fallback becomes `recover_by_reset(board, bench, ready=lambda:
  _sta_reconnected(dut_ip), first_wait_s=_OUTAGE_RECONNECT_TIMEOUT_S, retry_wait_s=_RECONNECT_TIMEOUT_S,
  skipped="_assert_wifi_log_has_only_benign_outage_warnings", note=result_note, description="a real WiFi outage")`,
  the benign-warning check running only when the helper reports no recovery (it returns whether it reset).
  `_assert_wifi_log_has_only_benign_outage_warnings()` reads the WIFI entry through `errcount_entry()` and tolerates
  `code("W", <AP not found>)` and `code("W", <authentication or handshake failed>)` (A.U2.14/A.U18.36's names); its
  comment: "an outage logs AP-not-found from a retry poll mid-outage and the handshake failure cyw43 reports when the AP
  drops mid-handshake (SPECIFICATION.md C.7.1, the WIFI row); the password never changes here." `reset_all_error_logs(…,
  request.node.name)`. Constants per A.U8C.50/A.U8C2.21 (B4). `COVERS_TWIN_SCENARIOS = ["webserver_concurrency",
  "sensortask_integration", "poll_prewarm"]` at module top.
- **Resolved**: A.U0.18 and A.U0.35 both edit the docstring; A.U26.63 and A.U36.544 rewrite the rest — one ≤ 3-line text
  carrying both owner tags (A.U0.18's merged-docstring note). A.U36.544 item 29's "`W4`" is the HEAD number A.U2.14
  renames; the pointer names the C.7.1 row, not a number.
- **Unit**: U26 (the U0 tags, U2 codes and U7 notes land in their units on HEAD lines and are rewritten in U26's
  edit; the U36 pointers are written here already, their targets existing by then — stage 2 U36 only if A.U36.544's
  F.1/C.7.1 text lands later than this file's U26 edit, which it does: stage 2 U36 swaps the two pointers in).
- **Depends**: M.HW_BENCH.015, M.HW_BENCH.050/.051, M.HW_BENCH.004, A.U2.01.
- **Blast carried by**: SPEC F.1 "UDP on rp2/lwIP" paragraph → A.U36.544 (SPEC); SPEC A.11 row 10 → A.U29.01 (SPEC);
  Part N rows → A.U8C.50/A.U8C2.21 (SPEC).
- **Kind**: test, hardware (Round: R1 [H73])

### M.HW_BENCH.077 Network-degradation tests watch the whole fault window and make NTP act inside it
- **From**: A.U26.47 (2), A.U26.55 (1), A.U26.22 (2), A.U8C.50 (`:149, :150, :156, :163-165, :180, :182, :198, :199,
  :205, :210-212, :228, :229, :235, :240-242`), A.U8C2.21 (`:179`).
- **Site**: `tests_hardware/bench/test_network_resilience.py:133-246`.
- **Change**: each of the four netem tests wraps inject → recover → clear in `harness.observe_during(board, …)` and
  asserts `crash_lines()` empty over the whole window (the 5 s post-fault tails `:156, :205, :235` go), then
  `assert_no_task_ended()` and `assert_module_error_log_empty(dut_ip, "WEBSERVER")`. Inside each impairment window the
  test waits for an NTP attempt the client makes on its own (its retry/resync period read from `src/asy_ntp_client.py` by
  `ast`, the window sized to contain one) and asserts its outcome from `/status` and the NTP log; a test where no
  attempt can fall inside the window is renamed to what it proves (REST reachability under the impairment) with that
  reason in its comment. Constants per A.U8C.50/A.U8C2.21; `_CRASH_CHECK_TAIL_S` (`l4.network_resilience_crash_check_tail_s`)
  is withdrawn (its three tails go).
- **Resolved**: A.U26.47 replaces the fixed 5 s tails A.U8C.50 tagged — the tag is withdrawn (B4).
- **Unit**: U26.
- **Depends**: M.HW_BENCH.016, M.HW_BENCH.020, M.HW_BENCH.051.
- **Blast carried by**: `observe_during()` L0 → A.U26.47 (TSC).
- **Kind**: test, hardware (Round: R1 [H73])

### M.HW_BENCH.078 NTP retry and garbage-server tests prove the fault reached the DUT
- **From**: A.U26.71 (`:249-285`), A.U26.73, A.U26.55 (2), A.U26.40 (`:283-289` comment), A.U18.16 (`:294` payload
  cut to 48 B), A.U2.03/A.U2.15 (`:314` "errno 14 or 15", `:353-355`), A.U18.10 (blast: `:351-355` holds), A.U26.29
  (`:318-322`, `:346-350`), A.U36.544 (5) (`:287`), A.U8C.50 (`:254, :259, :265, :273, :281, :304, :319, :323, :335,
  :346, :350`; deferred `:275` resolved), A.U10.40 (`NTP_Host` → `NTPHost`, `NtpSynced` → `NTPSynced`).
- **Site**: `tests_hardware/bench/test_network_resilience.py:249-358`.
- **Change**: (1) NTP retry test: loses `@pytest.mark.persistence_write`; its PUT of the current `NTPHost` asserts
  `"Unchanged"` (nothing written) and its comments stop claiming a re-trigger (an unchanged-value PUT fires no post
  function, `src/asy_api_response.py`); the block of UDP 123 lasts `_ntp_retry_period_s() + _NTP_BLOCK_MARGIN_S`
  (`l4.network_resilience_ntp_block_margin_s`, the period read by `ast`; the deferred `:275` 8.0 s is replaced by it),
  inside which the client's own timer makes the attempt, asserted by an NTP failure entry or `NTPSynced` false during
  the block; then the retry timer resyncs with no reset; joins `_JUSTIFIED_UNMARKED` with its reason. (2) Garbage
  tests: `_ROGUE_LOCAL_PORT_*` go; `with RogueUdpResponder(_GARBAGE_PAYLOAD) as responder:` then
  `redirect_udp_port_to_local(123|53, responder.port)` / `clear_udp_port_redirect(…, responder.port)`;
  `_GARBAGE_PAYLOAD` is 48 bytes (still not a valid NTP header, comment says why 48: the NTP packet size the client
  receives into); each asserts `responder.answered_from.get(dut_ip, 0) >= 1` before judging the DUT ("the injection
  never reached the DUT" otherwise); the codes compared through `code("E", …)` (the NTP no-reply and invalid-reply
  names, A.U2.15); the fallbacks through `recover_by_reset(…, skipped="the passive reconnect after the forced resync",
  …)`. The section comment `:286-289` → "NTP/DNS servers answering garbage rather than being unreachable (SPECIFICATION.md
  F.1, UDP on rp2/lwIP); delivery and its limits: tests_hardware/README.md 'What the network-fault injections reach'."
- **Resolved**: the `:275` sleep A.U8C.50 deferred to U26 under G7/R23: A.U26.71's "a block sized to contain it" decides
  it — a derived wait plus a tagged margin, not a fixed sleep.
- **Unit**: stage 1 U26; stage 2 U36 (the F.1 pointer text, as M.HW_BENCH.076).
- **Depends**: M.HW_BENCH.036, M.HW_BENCH.020, M.HW_BENCH.015, M.HW_BENCH.050, A.U4.02, A.U6.17, A.U18.16.
- **Blast carried by**: `_JUSTIFIED_UNMARKED` and the derived classes → A.U26.71 (TSC); README injection section →
  M.HW_BENCH.129.
- **Kind**: test, hardware (Round: R1 [H73])

### M.HW_BENCH.079 The connected-socket spoof lands while the DUT still waits
- **From**: A.U26.56 (1), A.U6.21 (blast: `:376`, `:403` read `UtcTime` that is `None` before a sync — "U26 site"),
  A.U26.29 (3) (`:380-390` retries reported), (2) (`:405-413`), A.U36.544 (5) (`:362`, `:382`), A.U18.19 (blast: the test
  stays the L4 proof of the source filter, unchanged in purpose), A.U8C.50 (`:374, :391, :400, :401, :410, :414`),
  A.U8C2.21 (`:386`), A.U26.22 (2).
- **Site**: `tests_hardware/bench/test_network_resilience.py:361-416`.
- **Change**: before the reset that provokes the sync, `bench.block_udp_ports_from([123])` holds the real reply back
  (verified-absent teardown); the spoof is sent at once after the capture reports the DUT's port; the test records the
  delay between the captured request and the spoof (`result_note`) and asserts it is below `_NTP_CONN_TIMEOUT` (read
  by `ast`); after the check the block is removed and a normal sync must follow (`NTPSynced` true). `UtcTime` reads
  `None`-safe: `:376` asserts `UtcTime is not None` with a message before reading `Year`; `:403` `utc =
  status["system"]["UtcTime"]; year_after = None if utc is None else utc["Year"]` (`None` = not synced, still ≠ 2050).
  Each capture retry used is a `result_note(…, recovery=True)`; the final reset recovery goes through
  `recover_by_reset()`. Comments: `:362` → "(SPECIFICATION.md F.1, UDP on rp2/lwIP)", `:382` → "(tests_hardware/README.md
  'Known assumptions and open findings')".
- **Resolved**: A.U6.21 hands `:376/:403` to "U26 site" with no U26 action carrying it — carried here.
- **Unit**: stage 1 U26; stage 2 U36 (the two pointers).
- **Depends**: M.HW_BENCH.024, M.HW_BENCH.015, A.U6.21, A.U10.40 (`Year`).
- **Blast carried by**: —
- **Kind**: test, hardware (Round: R1 [H61])

### M.HW_BENCH.080 Config-fault tests repair leftovers and restore on every path
- **From**: A.U26.15 (2)(3), A.U26.29 (2) (`:482-487`, `:560-568`), A.U26.45 (`:504`), A.U26.49 (2) (`:505`),
  A.U26.83 (`:535-543`), A.U0.18 (`:418-419`), A.U2.03/A.U2.15 (`:449-495`), A.U18.14 (blast: `_ntp_error_log_contains`
  needs no change), A.U10.40, A.U8C.50 (`:431, :441, :453, :454, :459, :465, :476, :483, :487, :510, :520, :530, :554,
  :555, :563, :568, :569, :571, :581, :584, :591, :597, :606`), A.U8C2.21 (`:561`, derived `:566`).
- **Site**: `tests_hardware/bench/test_network_resilience.py:418-608`.
- **Change**: section comment `:418-419` gains "(owner's suggestion, 2026-09-02)". Garbage `NTPHost`: a board already
  on `_GARBAGE_NTP_HOST` is repaired (restore target: `_VAL_NH`'s default read from `src/asy_ntp_client.py` by `ast`)
  with a `result_note` "repaired a leftover garbage NTPHost from an aborted run", through the shared
  `_repair_leftover(host, route, body)` (pinned in `_KNOWN_PERSISTING_HELPERS`); the post-restore fallback goes through
  `recover_by_reset(…, skipped="NTP resync after the restore PUT without a reset", …)`; the NTP codes by catalog name.
  Garbage SSID: `_GARBAGE_SSID = "bench-test-net-does-not-exist"` (its length checked in the test against `_VAL_SSID`'s
  bound read by `ast`); `_HOTSPOT_PASSWORD` and its stale comment go (`harness.hotspot_password()`); the PUT and every
  step after it sit inside the `try`/`finally` whose restore branch runs on every path; a leftover garbage SSID is
  repaired to `bench.ap_ssid()` with a note; the unreachable bridge-restore branch (`:535-543`, `http_client_is_ok()`
  and its use) goes — only the hotspot restore path stays, its comment stating why the bridge path cannot occur; the
  join retries go through `recover_by_reset(…, skipped="the first join attempt", …)`. Constants per A.U8C.50/A.U8C2.21.
- **Resolved**: —
- **Unit**: U26 (A.U0.18's U0 tag written into the same comment).
- **Depends**: M.HW_BENCH.010, M.HW_BENCH.015, M.HW_BENCH.050, A.U26.06 (helper pin).
- **Blast carried by**: `_KNOWN_PERSISTING_HELPERS` gains `_repair_leftover` → A.U26.15 (TSC); `pyproject.toml`
  S105/S106 for this file → A.U26.49/A.U28.29 (TSC); L0 default reads → A.U26.15 (TSC).
- **Kind**: test, hardware (Round: R3 gated (both persist) [H73])

### M.HW_BENCH.081 Ceiling, request and body-cap tests: traced drops expected, sets derived
- **From**: A.U19.08 (blast: refusals and early resets are now traced in WEBSERVER — "`tests_hardware` benign-code lists
  gain 60/48", M.SRC_NET.127), A.U2.19 (`:639, :969-972, :992`), A.U2.03/A.U2.07 (`:929-935`), A.U19.23 (blast: those
  counts unchanged by U19), A.U26.06 (`:716-727` raw PUT: `_JUSTIFIED_RAW_REQUESTS`), A.U26.20 (`:904-940`), A.U26.49
  (`:768` read), A.C.13 (the cap read by `ast`), A.U10.41 (`:812`), A.U7.15 (`:901`), A.U36.544 (3) (`:877` "queue F10"
  dropped, the measured "~25%" fact kept with its date), A.U26.52 (1) (`:1028-1070`),
  A.U26.80 / A.U19.20 (`:1034`), A.U26.70 (`is_ceiling_close` users), A.U26.01 (blast: `:617, :1007, :1031, :1081`
  unchanged calls), A.U26.22 (2), A.U8C.50 (`:633-:1101` sites, `web.max_content_length` at `:768`), A.U8C2.21 (`:651,
  :852`, derived `:672, :674`).
- **Site**: `tests_hardware/bench/test_network_resilience.py:611-1103`.
- **Change**: (1) Where a test drives the ceiling or resets connections — `:693` (over-ceiling), `:899` (mixed sizes
  at the ceiling), `:1017` (the discovery walk), and any of `:1065`/`:1102` whose run records a refusal — the WEBSERVER
  check becomes `assert_module_error_log_clean(dut_ip, "WEBSERVER", allowed_warnings=(code("W", "HTTP_REFUSED"),
  code("W", "HTTP_PEER_RESET")))`, plus `/status` `HTTPDropped` ≥ the client-side count of refusals (A.U19.10's
  field); the `:689-692` comment → "Reject-when-full closes without a response and traces one HTTP_REFUSED entry per
  refusal (SPECIFICATION.md H.7)". Elsewhere (`:712, :744, :758, :796, :808, :837`) WEBSERVER stays empty. (2) The
  slowloris test asserts `code("W", "HTTP_REQUEST_CAP")` (outer cap) at `:972`; `:639`'s "wrnno=2" comment and `:992`'s
  note name the per-call code `HTTP_CALL_TIMEOUT`. (3) Raw malformed PUT stays unmarked; `_JUSTIFIED_RAW_REQUESTS` holds
  it ("body is not JSON; microdot rejects it before any route handler"). (4) `_BODY_CAP` is read from
  `src/asy_webserver_service.py`'s `_DEFAULT_MAX_CONTENT_LENGTH` by `ast` (no literal, so A.U8C.50's `web.max_content_length`
  mirror tag at `:768` is withdrawn); `_OLD_CONTENT_CAP` stays a cited constant ("the cap before SPECIFICATION.md I.6;
  the 2048..4096 band is the discriminator"); `_SCHEMA_MAX_BODY` and the field `:812` fills are computed from the `_VAL_*`
  tuples read by `ast` (the largest string field after A.U10.41's RFC 1035 bound on `NTPHost`), never a literal. (5)
  `:901` → `result_note(f"{len(answered)} answered, {len(refused)} refused …")`. (6) `:904-940`: a second PUT
  `{"Hostname": "ä" * 32}` (64 UTF-8 bytes, over `_VAL_HOST`'s byte bound read by `ast`) asserts `"Invalid"`, the WIFI
  log's rejection entry (`code("E", …)` per C.7.4), no reconnect (`Mode` unchanged, no "WLAN connection" line over a 5 s
  tail) and `/status` 200; the SSID case the same with `_VAL_SSID`; `:929-935`'s CFGMGR code by catalog name (BAD_ARG);
  `_JUSTIFIED_UNMARKED`'s reason gains "the Hostname/SSID values exceed their byte bounds and are rejected". (7)
  Full-ceiling test: before the burst one uncontended GET per path records a reference body (a 200 parsing to an object);
  each burst body must parse with the reference's key set, and a streamed route's body be `Content-Length`-complete; the
  path set is `harness.get_routes(streams=None)` filtered to JSON (the streamed ones named by the table's property).
  Constants per A.U8C.50/A.U8C2.21; the join messages interpolate their constants.
- **Resolved**: A.U19.08 makes refusals and resets log WEBSERVER entries, which the HEAD tests assert never happen —
  the "benign list" its blast hands to `tests_hardware` exists nowhere at HEAD, so the empty-log assertions on the
  refusal paths become the clean check with exactly those two codes (carried here; U19's own blast). A.C.13 reads the
  cap by `ast` "not the `:768` copy" while A.U26.49 keeps mirror-tagged copies; reading removes the copy (G1/R41's first
  choice), so both tests here share the read value.
- **Unit**: U26 (after U19's product change; the HEAD assertions are wrong from U19 to U26, a window with no hardware
  run).
- **Depends**: M.HW_BENCH.052 (clean check), M.HW_BENCH.050 (`code`), M.HW_BENCH.010 (`get_routes`), M.HW_BENCH.030,
  A.U19.08/A.U19.10 (codes, `HTTPDropped`), A.U2.19, A.U10.41, A.U2.01.
- **Blast carried by**: `_JUSTIFIED_RAW_REQUESTS`/`_JUSTIFIED_UNMARKED` → A.U26.06/A.U26.20 (TSC); the deleted
  `wifi_country_hostname_edge_values.py` → A.U26.20 (HW_DEV); `tests_scripts/test_persistence_write_marker_completeness.py:29`
  reason naming the new largest field → A.U10.41 (TSC).
- **Kind**: test, hardware (Round: R1 [H40, H73])

### M.HW_BENCH.082 New bench rows: cap binding, the owner's OpenHAB mix, console starvation
- **From**: A.C.13, A.U26.64, A.U19.23 (its hardware row: no instrument in any action; A.C.05 (1) and C inventory H42
  describe it) — agent decision D5.
- **Site**: `tests_hardware/bench/test_network_resilience.py` after `:787` and after `:1070`.
- **Change**: (1) `test_an_oversized_body_is_refused_before_it_is_read(dut_ip)` as A.C.13: raw socket `PUT /sensors`
  with `Content-Length: <cap + 1>` and no body byte → a complete `413` within `l4.cap_binding_answer_s` while nothing
  more is sent; control arm `Content-Length: <cap>` gets no response in that window and the socket closes before
  `web.per_call_timeout_s`; `MemFree` before/after differs by less than the cap (recorded); unmarked, its
  `_JUSTIFIED_UNMARKED` reason "refused unread: nothing persists"; its host logic runs against the twin first. (2)
  `test_openhab_case_two_pollers_and_an_open_website_are_all_served(dut_ip, board, result_note)` as A.U26.64: 120 s, two
  pollers (`/measurements`, `/status`, each per `l4.openhab_poll_interval_s`) and one website client (the served
  `index.html`'s assets, then the routes `js/poll-manager.js` or the generated definitions poll); every response
  complete, no ceiling refusal, no reboot, no task end, no allocation marker over `observe_during()`, `/status` serving
  at once after; per-route latency recorded. (3) `@pytest.mark.persistence_write
  test_console_output_with_a_non_reading_usb_host_never_starves_the_watchdog(board, dut_ip, request, result_note)`: PUT
  `DebugLevel` 0 (`"Valid"`), a host thread opens `board.device` with DTR asserted and never reads, the adversarial-client
  load of A.U19.23's L1 test replayed over HTTP for `_CONSOLE_LOAD_S = 60.0` (`l4.console_starvation_load_s`): six
  slowloris connections, refused heads, truncated bodies, resets, ceiling refusals; asserts no reboot (`ResetReason`,
  `SysUptime` unchanged) and `/status` serving; `finally` restores `DebugLevel` 5 (asserting `"Valid"`) — two owned
  flash writes.
- **Resolved**: D5 — A.U19.23 states a phase-C hardware row and A.C.05 (1) runs it, but no action writes its
  instrument; a gated test makes the row repeatable instead of a hand step (shown in the OR2.c review).
- **Unit**: U26.
- **Depends**: M.HW_BENCH.016, M.HW_BENCH.010, A.U19.07 (stream guard), A.U8.02 (relation `l4.cap_binding_answer_s` <
  `web.per_call_timeout_s`), A.U26.05 (twin run), A.U11.08 (`MemFree`).
- **Blast carried by**: Part N rows `l4.cap_binding_answer_s` → A.C.13 (SPEC), `l4.openhab_poll_interval_s` →
  A.U26.64 (SPEC), `l4.console_starvation_load_s` → GAP-B7 (SPEC); SPEC I.6 binding sentence after R1 → A.C.10;
  budget table row (2 writes) → M.HW_BENCH.130; `_JUSTIFIED_UNMARKED` → A.C.13 (TSC).
- **Kind**: test, hardware (Round: (1), (2) R1 [H41, H73]; (3) R3 [H42])

## tests_hardware/bench/test_reset_reasons.py (new)

### M.HW_BENCH.083 Every reset code proven on the bench through `/status`
- **From**: A.U26.28 (2) (codes 2, 4, 5, 6), A.C.12 (codes 0, 9, 10 + p, 20; replaces A.U26.28's boot-failure
  exception row), A.S0930.40 (2) (the bootloader test's reply-to-loss bound), A.U31.07/OR130.a (the escalation feeds
  once before stopping: a code 2 there is a failure), A.U26.22, A.U26.29, A.U7.24/A.U26.51.
- **Site**: new `tests_hardware/bench/test_reset_reasons.py`.
- **Change**: every test saves FRAM evidence first (`save_errcount`, `save_fram_raw`), reads `GET /status`'s
  `ResetReason` after the production boot serves (passive waits only), and restores serving in `finally`
  (`restore_board_to_serving()`): `test_a_harness_hard_reset_reads_as_watchdog_without_a_record` (code 2);
  `test_a_bootloader_reboot_is_attributed` — `PUT /system {"SystemCmd": "bootloader"}` → `"Valid"`, the reply-to-loss
  time bounded as M.HW_BENCH.067 (its margin under the same watchdog limit), `sudo picotool reboot` (no load, no flash
  write), serving, code 4; `test_the_supervisor_escalation_reboot_is_attributed` —
  `system_service_restarts_a_real_dead_task.py` in its budget mode through `run_isolated_expect_reset()`, code 5 and the
  SYSTEM log's escalation entry (a 2 fails: OR130.a's one feed before the reboot); `test_the_starved_watchdog_fallback_is_attributed`
  — `reboot_fallback_starves_the_watchdog.py`, code 6; `test_an_invalid_record_reads_as_unknown` — code 0;
  `test_an_incomplete_command_is_attributed` — code 9, and the raw dump after the boot shows every chunk blank or holding
  its saved content; `test_a_hang_in_boot_phase_p_is_attributed` parametrised over phases 1-5, the generated
  `main(watchdog=machine.WDT(timeout=8000), cfg_path=<scratch>)` with one callee of that phase rebound to
  `time.sleep_ms(10000)` from outside — code 10 + p; `test_a_c_stack_exhaustion_is_attributed` — code 20. The four
  A.C.12 scripts are HW_DEV's; none writes flash (FRAM only). A code an attempt cannot reach returns to the E.6
  exception list with the attempt's recorded result (OR77.a), as a phase-C delta.
- **Resolved**: A.U26.28's "boot-failure (10 + phase) … a structural exception" is replaced by A.C.12's attempt (C A-C
  note 2); code 1 stays the manual power-cycle step (M.HW_BENCH.102).
- **Unit**: U26 (C's instruments co-land with U26, C.md heading).
- **Depends**: A.U11.05/A.U11.06/A.U11.07 (record, phases, codes), A.U30.19 (code 20), A.S0930.13-.17/.31 (commands,
  code 9), A.U20.02/A.U25.69 (`main()` keywords), M.HW_BENCH.012, M.HW_BENCH.015, M.HW_BENCH.050.
- **Blast carried by**: the device scripts (escalation mode, the four A.C.12 scripts) → A.U26.28/A.C.12 (HW_DEV);
  A.U26.06 (2)'s persisting-call set counts a generated `main(` without a scratch `cfg_path` → A.C.12/A.U26.06 (TSC);
  `tests_scripts/test_bench_restores_serving.py` covers the module → A.U26.28 (TSC); README reset-code table →
  M.HW_BENCH.119; E.6 row removal → A.C.12 (SPEC); twin records (three agree with A.U25.55's L2 codes, the boot-phase one
  "watchdog reset needs silicon") → M.HW_BENCH.092.
- **Kind**: test, hardware (Round: R1 [H10, H12, H15])

## tests_hardware/bench/test_rest_endpoints_over_sta.py

### M.HW_BENCH.084 Every declared sensor is checked against its sourced bounds
- **From**: A.U26.53, A.U26.49 (1) (`:15-30`, the 400 floor), A.U26.01 (5) (`:36`), A.U8C.51, A.U36.544 (3) (`:35`
  "queue row G9"), A.U26.29 (the two deliberate resets `:105-106`, `:140-141` become `kick_then_reset()`), A.U7.24/
  A.U26.51 (`COVERS_TWIN_SCENARIOS = ["real_website_integration", "sensortask_integration"]`).
- **Site**: `tests_hardware/bench/test_rest_endpoints_over_sta.py:1-160`.
- **Change**: the bound constants `:18-24` go; the expected sensor set is the bench TOML's sensor instances
  (`bench_facts.build(bench_device())`), each checked by a per-driver checker table keyed by driver name against
  `plausibility_bounds.BOUNDS` (a declared driver without a checker fails "no plausibility checker for driver X");
  ISL29125's checker: `Lux` within FN8424 p.1's span, `RangeAct` ∈ the driver's two ranges (read from `src/` by `ast`),
  `CCT` within G3/R34's limit, the normalised colour fields within 0-1, each check naming its page. The website test
  passes `device=bench_device_name`; its comment "(queue row G9)" goes. The mempause and GainRatio tests reset through
  `kick_then_reset(board, bench)` (the deliberate reset under test, not a recovery). Constants per A.U8C.51 (B4).
- **Resolved**: —
- **Unit**: U26 (the U36 label drop written in the same U26 rewrite of `:35`).
- **Depends**: M.HW_BENCH.041, M.HW_BENCH.043, M.HW_BENCH.037, M.HW_BENCH.015, A.U15 (G3/R34's CCT limit).
- **Blast carried by**: the L2 twin equivalent unchanged → A.U26.53 (TWIN).
- **Kind**: test, hardware (Round: R1 [H73])

## tests_hardware/bench/test_scd30_frc_readiness_baseline.py (new)

### M.HW_BENCH.085 The FRC readiness defaults measured on the bench
- **From**: A.U26.84, A.U26.79 (the SCD30 snapshot's interval).
- **Site**: new `tests_hardware/bench/test_scd30_frc_readiness_baseline.py`.
- **Change**: `@pytest.mark.soak_duration test_scd30_frc_readiness_baseline(dut_ip, request, result_note)` as
  A.U26.84: at the configured interval (the session snapshot), polls `/measurements` once per interval for the soak
  duration, computes CO₂ spread and change rate over sliding windows (20 s τ63 multiples up to 10 min), writes the
  distributions through `evidence.save_json()` and a `result_note`; asserts only that a measurement arrived every
  interval. No write. Header (≤ 3 lines) names the room condition the round plan states (stable, unoccupied).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: A.U15's readiness parameters (REF/R06), M.HW_BENCH.040, M.HW_BENCH.006, M.HW_BENCH.055.
- **Blast carried by**: Part N rows `sens.scd30_frc_*` set from the figures → A.C.10 after R5 (delta); DEVICE_REFERENCE
  cites the measurement → U15 (DOCS).
- **Kind**: test, hardware (Round: R5 long [H34])

## tests_hardware/bench/test_sensor_config_push_over_real_hardware.py

### M.HW_BENCH.086 Config pushes repair leftovers; the SCD30 Altitude question is measured, gated
- **From**: A.U26.15 (4) (`:36-110` leftover repair), A.U26.72 (new test), A.U4.07 (`:22-23` comment), A.U26.09 (budget,
  result words), A.U9.09 (`:116-118`, `:140`), A.U22.03 (withdrawn by OR126.a (4): its `:131` rewording dropped), A.U2.03/
  A.U2.07 (`:69, :109` comments), A.U10.40 (`SGPResetVOC` → `ResetVOC`, `MeasInt`), A.U26.76 (`:8, :40, :80`),
  A.U26.22 (2), A.U8C.52, A.U8C2.22, A.U7.24/A.U26.51.
- **Site**: `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:1-191`.
- **Change**: (1) `:22-23` (U4): "PUT /sensors reaches SCD30's NVM through its chip store (`_set_mgr_cfg()`,
  compare-before-write); a bench counterpart spends real NVM wear, so it is added behind persistence_write or its wear
  reason is listed." (U26) → replaced by the SCD30 test below and the one-line pointer to it. (2) BMP3XX and ISL29125
  push tests: a leftover test value is repaired to the schema default read from the driver's `_VAL_*` by `ast` through
  `_repair_leftover()`, with a `result_note`, instead of refusing to run; `original: dict[str, JSONValue]`. (3) New
  `@pytest.mark.persistence_write @pytest.mark.scd30_extra_write
  test_scd30_altitude_takes_effect_while_ambient_pressure_is_zero(dut_ip, request, result_note)` as A.U26.72: reads
  `AmbPres`/`Altitude`; PUTs `AmbPres: 0` (`"Valid"`, always-executed), waits three intervals, records CO2; PUTs
  `Altitude` +1000 m within `_VAL_ALT` (`"Valid"`), records CO2 over five intervals with timestamps; restores `Altitude`
  then `AmbPres` in `finally` with result words; the shift and the interval it appears at go to a `result_note` and
  `evidence.save_json()`; asserts only that every PUT and restore was accepted (four owned NVM writes). (4) PauseTime test:
  comments `:116-118` "PauseTime counts down measured time over real HTTP", the `:140` message "PauseTime never reached
  0"; `_OVERRIDE_POLL_TRIES = 10`, `_OVERRIDE_POLL_S = 1.0` (B4; the `:131` comment stays as HEAD has it — A.U22.03 is
  withdrawn). (5) The CFGMGR codes in comments `:69, :109` by catalog name. (6) `reset_all_error_logs(…, request.node.name)`.
  `COVERS_TWIN_SCENARIOS` per A.U7.24.
- **Resolved**: A.U4.07 (U4) rewrites the comment that A.U26.72 (U26) makes moot: staged. A.U22.03's rewording is
  dropped (withdrawn, OR126.a (4)).
- **Unit**: stage 1 U4 (`:22-23`); stage 2 U26.
- **Depends**: A.U4.04 (chip store), M.HW_BENCH.080 (`_repair_leftover`), M.HW_BENCH.050, M.HW_BENCH.055, A.U9.09.
- **Blast carried by**: `_KNOWN_PERSISTING_HELPERS` (`_repair_leftover`) → A.U26.15 (TSC); budget table rows →
  M.HW_BENCH.130; SPEC M (SCD30) and the Altitude help text after the measurement → A.U26.72 via A.C.10 (delta).
- **Kind**: test, hardware (Round: (2)-(5) R3 gated where marked, R1 otherwise; (3) R3 [H33])

## tests_hardware/bench/test_serving_heap_at_default_gc.py

### M.HW_BENCH.087 The serving sweep names its threshold and derives its routes
- **From**: A.U26.48 (1), A.U26.68, A.U26.80 / A.U19.20 (`:27`), A.U26.70 (`:66` `is_ceiling_close`), A.U26.10 (blast:
  `:106, :120` unchanged; the serving script keeps `cfg_path=""` as a listed prerequisite), A.U26.01 (blast: `:123`),
  A.U8C.53, A.U7.24/A.U26.51.
- **Site**: `tests_hardware/bench/test_serving_heap_at_default_gc.py:1-150`.
- **Change**: `_PATHS = (*get_routes(), "/", "/js/app.js")` with the comment "every registered JSON GET route, plus
  the page and the largest static file it fetches next (a static mount, not a REST route)"; the refusal check uses
  `isinstance(e, http_client.CeilingRefusedError)` (or the kept `is_ceiling_close`); both tests parse `FACT` lines and
  `DONE` through `harness.parse_facts()`, require the `gc_threshold` fact and name it in every assertion message and
  report; `_MAX_ROUTE_NEED = 480` stays tagged (`l4.serving_heap_at_default_gc_max_route_need`, re-derived on a named
  image in phase C, G4/R47); constants per A.U8C.53 (B4).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.010, M.HW_BENCH.012, M.HW_BENCH.030.
- **Blast carried by**: the device scripts' `FACT` output → A.U26.68 (HW_DEV); the `_MAX_ROUTE_NEED` re-derivation →
  A.C.10 after R1 (delta) [H44].
- **Kind**: test, hardware (Round: R1 [H44])

## tests_hardware/bench/test_system_commands.py (new)

### M.HW_BENCH.088 The system commands over REST: reset with save and restore, erase with evidence first
- **From**: A.S0930.29 (1)-(4), (6), (8), A.S0930.40 (3), A.S0930.19 (the reset test carries `persistence_write`),
  A.U26.15 (leftover-repair pattern), A.U26.22, A.U26.23 (derived logger set), A.U26.29, A.U26.49 (TOML hostname/password),
  A.U26.47, OR118.a (2)-(3), OR124.a.
- **Site**: new `tests_hardware/bench/test_system_commands.py`.
- **Change**: as A.S0930.29: (1) `@pytest.mark.persistence_write test_config_reset_over_rest_brings_back_the_defaults` —
  a board holding no `config_*.cfg` (an aborted earlier run) is restored from the newest saved set first (note);
  `save_errcount()`; `config_files_dump.py` output saved verbatim (`evidence.save_text`); `PUT /system {"SystemCmd":
  "resetconfig"}` → `"Valid"`; passive wait; the bench joins the unit's hotspot (`join_dut_hotspot(<TOML hostname>,
  hotspot_password())`, AP down first); `ResetReason` 7, `Hostname` = the TOML's, `SSID` "", `DebugLevel` 0; `finally`:
  leave the hotspot and restore the bridge, `config_files_restore.py` writes the saved files back verbatim (one write
  per file, owned), `recover_by_reset()`/`kick_then_reset()`, then serving on the bench WLAN with the saved SSID and
  hostname, verified by GET. (2) `test_fram_erase_over_rest_blanks_every_error_log` — `save_errcount()` and
  `save_fram_raw()` first; `"erasefram"` → `"Valid"`; `ResetReason` 8; every FRAM-backed module's counter 0 and history
  empty (`fram_backed_logger_names()`). Not wear-gated. (3) `test_near_miss_action_words_do_nothing_over_rest` — the
  near-miss list → `"Invalid"` each; `SysUptime` keeps rising; config GETs unchanged. (4)
  `test_erase_reboot_and_mempause_at_once` — evidence first; three threads; exactly one reset; `ResetReason` 8 when
  `erasefram` answered `"Valid"`, 3 when `reboot` did; the other shutdown-side answer `"Failed"`. (5)
  `test_reboot_and_bootloader_at_once` (A.S0930.40 (3)) — one `"Valid"`, the other `"Failed"`; `ResetReason` 3 or 4
  matching the winner (after `picotool reboot` when bootloader won). (6) The reply-to-serving time of (2) recorded; a
  `ResetReason` 2 in (2) is a watchdog reset, a failure. Every test reads its output through `observe_during()`'s
  markers. The hotspot join of (1) runs inside the round's armed bench-network switch (A.C.01 (2)); a board left on its
  hotspot is recovered over USB (`config_files_restore.py`, then `machine.reset()`), never left.
- **Resolved**: —
- **Unit**: U26 (SUPP_owner_0930's tests land with U26).
- **Depends**: A.S0930.09-.17/.31-.33 (product), M.HW_BENCH.010, M.HW_BENCH.012, M.HW_BENCH.015, M.HW_BENCH.016,
  M.HW_BENCH.050, M.HW_BENCH.055, M.HW_BENCH.023.
- **Blast carried by**: `config_files_dump.py`, `config_files_restore.py` → A.S0930.29 (HW_DEV); the wear guard sees (1)
  marked and (2)-(5) unflagged → A.S0930.19/A.U26.06 (TSC); README "System commands" and reset-code rows 3/4/7/8 →
  M.HW_BENCH.119; the manual power cuts → M.HW_BENCH.102.
- **Kind**: test, hardware (Round: (2)-(5) R1 [H13, H14]; (1) R3 gated [H13])

## tests_hardware/bench/test_ticks_ms_rollover.py (new)

### M.HW_BENCH.089 The rollover is observed over REST on a running board
- **From**: A.U26.36, A.U26.29 (the start reset), A.U26.74 (flag).
- **Site**: new `tests_hardware/bench/test_ticks_ms_rollover.py`.
- **Change**: as A.U26.36: `@pytest.mark.multi_day_rollover test_ticks_ms_rollover_is_survived(board, bench, dut_ip,
  request, result_note)` with its in-test skip on `--allow-multi-day-rollover`; one `kick_then_reset()` so the counter
  and `SysUptime` start near 0, recording `BootSignature`; hourly passive `GET /status` and `/measurements` until
  `SysUptime` exceeds `2**30 / 1000 + 3600` s, each asserting no reboot (`BootSignature` unchanged, `SysUptime` strictly
  increasing), `NTPLastSyncAge` ≤ the sync interval + 60 s, every sensor's `TS` advancing, and `assert_no_task_ended()`; a
  failed poll is retried within the hour and noted. Nothing touches the raw REPL. `_POLL_INTERVAL_S = 3600.0`
  (`l4.ticks_rollover_poll_interval_s`).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.015, M.HW_BENCH.051, A.U10.40 (key names).
- **Blast carried by**: the flash-tier test removed → A.U26.36 (HW_DEV); A.U7.14's marker map → A.U7.14 (SCR); README
  recipe → M.HW_BENCH.126; BACKLOG G6 row → A.U26.36 with U36 (DOCS).
- **Kind**: test, hardware (Round: R6 [H63])

## tests_hardware/bench/test_uart_link_under_api_load.py

### M.HW_BENCH.093 The link under API load: counters read at the window's end, hazards and the multi-chunk SET added
- **From**: A.U7.16 (`:39-43`, `:47-57`: skip → fail, "the bench device's TOML"), A.U26.54 (3) (`:143-155`), A.U26.67
  (`:104-107`, `:193-196`), A.U26.76 (`:10, :37`), A.U26.82 (the bench hazard test), A.U26.87 (the L4 multi-chunk SET),
  A.S0930.05 (the hazard script in both CRC modes), A.S0930.06 (3) (the three checks factored into module-level helpers),
  A.U26.45 (blast: A.U7.16's sites), A.U26.22 (2), A.U26.78 (readers), A.U8C.54, A.U7.24/A.U26.51
  (`COVERS_TWIN_SCENARIOS = ["uart_link"]`), A.U36.539 (blast: README).
- **Site**: `tests_hardware/bench/test_uart_link_under_api_load.py:1-197`.
- **Change**: (1) `_UART_MODULES` is derived from the bench TOML's `uart_link` instances (`bench_facts`) and their
  errcount keys (the generated definitions), not a literal pair. `_link_counters()`/`_require_uart_modules()` call
  `pytest.fail(...)` with "check the bench device's TOML still declares its uart_link instances and this build used it";
  `sensors: dict[str, JSONValue]`. (2) The three existing tests become module-level check functions
  (`check_link_healthy_under_load(dut_ip, …)`, `check_transfers_under_load(…)`, `check_overload_does_not_corrupt(…)`)
  that the test functions call, so `test_uart_link_crc16.py` reuses them. (3) Transfers: the counters are read once
  right after the last worker joins and `moved > 0` is asserted on that read; the 30 s post-load poll goes. (4) The
  module checks read entries through `errcount_entry()` (fail closed). (5) New `test_uart_comm_hazards_hold_under_api_load(board,
  bench, dut_ip, crc_mode)` parametrised `crc_mode ∈ {"none", "crc16"}` (scripts run from RAM, no reflash):
  `uart_comm_hazards.py`'s H1/H2 part through `run_isolated(…, CRC_MODE=crc_mode)` while `_load.sensors_reader` threads
  load the API; the same verdicts as the flash test from `parse_facts()`, plus the API floor
  (`l4.uart_link_under_api_load_hazards_min_answered`); restores serving in `finally`. (6) New
  `test_a_multi_chunk_set_echoes_intact_under_serving_load(board, bench, dut_ip)` (A.U26.87 (2)):
  `uart_link_echo_under_serving_load.py` boots the generated device module's `main()` and calls the initiator's
  `uart_set(_CMD_ECHO, <multi-chunk>)` then `uart_get(_CMD_ECHO)` N times while the host drives `sensors_reader` load;
  judges intact == total, the exerciser's `Failures` unchanged, the API floor; restores serving. (7)
  `reset_all_error_logs(…, request.node.name)`; constants per A.U8C.54 (B4; the 30 s post-load wait's IDs
  `l4.uart_link_under_api_load_wait_*` keep only the remaining uses).
- **Resolved**: A.U26.54 (3) removes the `:143-150` post-load poll that A.U8C.54 tagged at `:147-148` — those two tag
  uses go (the constants stay for `:99-100, :188-189`).
- **Unit**: U26 (A.U7.16's U7 skip→fail lands in U7 on HEAD text and is re-worded here).
- **Depends**: M.HW_BENCH.041, M.HW_BENCH.061, M.HW_BENCH.051, M.HW_BENCH.012, M.HW_BENCH.015, A.U26.82/A.U26.87
  device scripts (HW_DEV), A.S0930.01/.02 (CRC key and wiring), A.U17.25 (tier map).
- **Blast carried by**: `uart_comm_hazards.py`, `uart_link_echo_under_serving_load.py` → A.U26.82/A.U26.87 (HW_DEV);
  `tests_scripts/test_bench_restores_serving.py` covers the new tests → A.U26.87 (TSC); SPEC J.7 tier map → A.U36.539/
  A.U17.25 (SPEC); `UART_C_PORT_CHANGELOG.md` — none (tests only, A.U26.82/A.U26.87).
- **Kind**: test, hardware (Round: R1 [H37])

## tests_hardware/bench/test_uart_link_crc16.py (new)

### M.HW_BENCH.094 The bench link suite in the CRC16 mode, behind `flash_cycle`
- **From**: A.S0930.06 (3), A.U26.22 (evidence before a reflash), A.U26.03/A.U26.79 (end state).
- **Site**: new `tests_hardware/bench/test_uart_link_crc16.py`.
- **Change**: as A.S0930.06 (3): one `@pytest.mark.flash_cycle test_the_link_suite_runs_on_a_crc16_image(board, bench,
  dut_ip, bench_device_name, tmp_path, request)`: `save_errcount()` and `save_fram_raw()` first; the bench TOML copied
  into `tmp_path` with `crc = "crc16"` on both link instances; `scripts/build_firmware.py <device> --device-toml <tmp>
  --output <tmp>/firmware-<device>-crc16.uf2` (its record beside it; the round's `.uf2` and record untouched);
  `harness.reflash(board, <crc16 .uf2>)` and `check_image(dut_ip, <crc16 record>)` (record's `uartCrc` crc16); the three
  `test_uart_link_under_api_load` check functions; `finally`: `reflash(board, <the round's standard .uf2>)` unchanged (no
  rebuild), serving, `check_image()` against the round's record, `UARTLINK.Failures` 0 over two polls.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: A.S0930.01/.02 (CRC key), A.S0930.06 (1) (`--device-toml`, record keys, SCR), M.HW_BENCH.014,
  M.HW_BENCH.060, M.HW_BENCH.093, M.HW_BENCH.050.
- **Blast carried by**: `tests_scripts/test_build_firmware.py` `--device-toml` cases → A.S0930.06 (TSC); README
  flash-cycle list "two reflashes: the CRC16 image and back" → M.HW_BENCH.130.
- **Kind**: test, hardware (Round: R4 [H38])

## tests_hardware/bench/test_wifi_networking.py

### M.HW_BENCH.095 STA, NTP and DNS tests prove what they claim and report their recoveries
- **From**: A.U26.27 (2) (`:54-59`), A.U26.26 (`:97`), A.U26.29 (2) (`:100-107`), A.U7.15 (`:42`), A.U2.03/A.U2.15
  (`:108-110` errno 21), A.U3.06 (blast: `:111`'s console text kept verbatim), A.U18.36 (blast: no wrong-password
  assertion in this file), A.U36.544 (3)/(5) (`:32` "queue F13", `:80` item 6), A.U26.22 (2), A.U8C.55, A.U8C2.23,
  A.U7.24/A.U26.51 (`COVERS_TWIN_SCENARIOS = ["network_neopixel"]`, the network half).
- **Site**: `tests_hardware/bench/test_wifi_networking.py:1-120`.
- **Change**: section banner `:17` "Item 7 - real STA connect…" → "Real STA connect/disconnect…" (an undefined label,
  B5); the `:30-32` comment keeps the measurement ("measured 2026-09-19: 1 miss in 3 full suite runs, 12/12 clean in
  isolation") and drops "queue F13"; the second-cold-boot note → `result_note(…, recovery=True)` naming what the reset
  skipped (the first association). `test_real_ntp_sync_succeeds_over_genuine_udp(board, dut_ip)`: reads `/status`
  before the window, tails 60 s, passes only if an `RTC set to:` line arrived in the window or `NTPSynced` is true with
  `NTPLastSyncAge` ≤ 60 + the read's own duration afterwards; the failure-word scan stays second. NTP-unreachable test:
  the boot check `:97` → `harness.boot_lines(lines)` non-empty; the fallback → `recover_by_reset(…, skipped="the
  passive reconnect after the forced resync", …)`; `:110` → `assert_module_error_log_contains(dut_ip, "NTP", code("E",
  <no reply>), "E")`; `:80` comment's "BACKLOG open question 6" → "(SPECIFICATION.md F.2)"; `reset_all_error_logs(…,
  request.node.name)`. Constants per A.U8C.55/A.U8C2.23 (B4).
- **Resolved**: —
- **Unit**: stage 1 U26; stage 2 U36 (`:80` pointer, if F.2's text lands after this edit).
- **Depends**: M.HW_BENCH.016, M.HW_BENCH.015, M.HW_BENCH.050, A.U10.40 (keys), A.U2.15.
- **Blast carried by**: pinned-strings L0 gains `RTC set to:` → A.U26.27 (TSC).
- **Kind**: test, hardware (Round: R1 [H73])

## tests_hardware/bench/test_wifi_radio_reinit.py (new)

### M.HW_BENCH.096 The WiFi radio re-init rung on silicon
- **From**: A.U26.34 (3), A.U18.R01 (its rung's L3/L4 step, re-homed by A.U26.19), A.U26.17 (the serving guard covers it).
- **Site**: new `tests_hardware/bench/test_wifi_radio_reinit.py`.
- **Change**: `test_the_radio_reinit_rung_restores_the_link(board, bench, dut_ip, result_note)`: runs
  `wifi_radio_reinit_recovery.py` (reads the production `config_WIFI.cfg` read-only, constructs the WiFi service over the
  scratch config path primed in RAM, connects, calls `_recover_device()`, prints the elapsed time as a fact) and asserts
  the link came back (`isconnected()` and an IP) within the connect budget; records the time; `finally`
  `restore_board_to_serving()`. No config write. `COVERS_TWIN_SCENARIOS` per A.U7.24.
- **Resolved**: A.U26.34 (3) places it in a new bench module ("it needs the bench AP up"); A.U18.R01's planned step in
  the retired repro script moves here (A.U26.19's blast, "A-C amends A.U18.R01's blast").
- **Unit**: U26.
- **Depends**: A.U18.R01 (the rung, SRC_NET), M.HW_BENCH.012, M.HW_BENCH.015.
- **Blast carried by**: `wifi_radio_reinit_recovery.py` → A.U26.34 (HW_DEV); the twin run of the script →
  M.HW_BENCH.092; README rung table → M.HW_BENCH.122.
- **Kind**: test, hardware (Round: R1 [H16])

