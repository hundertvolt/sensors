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

