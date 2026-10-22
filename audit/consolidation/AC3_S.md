# A-C3 Part S: Site trace and repo-wide Blast-pointer sweep (HEAD f18cb83)

Brief: `audit/sweeps/ac23_prompt.md` A-C3 Part S, AC_NOTES 47 and 49. Read-only on every `M_*.md`; each finding names
the M-ID to amend and the exact amendment text, for the lead to apply after A-C2. Inputs: the 52 action files
(`audit/actions/*.md` minus AC_NOTES and the register-fix files: 1,545 actions), the 16 merges (1,865 merged changes),
`GAPS_G1-G4.md`, `site_index.json` (the old extractor's output), CLUSTERS.md. Code facts are read at HEAD.

Tools (all under `audit/sweeps/`, re-runnable): `ac3_site_trace.py` (corrected extractor and the pair trace, writes
`ac3_site_trace.json`), `ac3_triage_compact.py`/`ac3_triage_dump.py`/`ac3_snip.py` (views for reading by hand),
`ac3_fanout.py` and `ac3_rename_fanout.py` (per-file carriers of a fan-out action), `ac3_blast_sweep.py` (writes
`ac3_blast_sweep.json`).

## 1. Summary

| | count |
|---|---|
| actions read / actions with at least one Site file | 1,545 / 1,537 (8 have none: A.C.18, A.SDEP.02, A.SDEP.25, A.S0930.32, A.U14.29, A.U24.35 (withdrawn), A.U37.13, A.U37.16 — procedures, all carried by PROC or their cluster) |
| (action, file) pairs, corrected extractor / old index | 4,351 / 2,850 (1,508 pairs new; 4 old pairs dropped, all A.U14.17's: the old parser read its Change (a)/Blast (a) lines as Site; those four files are blast items, swept in §5) |
| carried: From names the action and Site names the file | 3,577 exact; 51 by the file's section heading (Site gives line numbers only); 6 by a `<placeholder>` path; 3 by section |
| not carried as found | 714 pairs of 148 actions — every one read by hand below (557 "merged elsewhere", 84 named only in a cluster's preamble convention, 73 directory/file nesting) |
| result | 18 findings with amendments (§3): 12 carrier gaps, 2 conflicts between a merged change and its action, 1 structural (rename sweeps and conventions form no step), 3 trace corrections; 9 From completions (§4); the rest disposed with a reason (§6) |
| Blast pointers swept repo-wide | 3,957 items (831 M-ID, 2,821 A-ID, 305 with no ID): 1 missing M-ID, 1 stale pointer, 4 label corrections, 0 uncarried (§5) |
| owner questions | none: every finding is settled by an action's own text, a merged change's own statement, CLAUDE.md or AC_NOTES |

## 2. Method

**Extractor** (`ac3_site_trace.py`, replacing `ac_index.py`'s `PATH_RE` for this check). Per Site slot, after joining
continuation lines and rejoining a backticked path broken at a line wrap (`tests/test_digital_twin_sensortask_ integration.py`):
- any token whose first segment is a repository top-level entry, a planned one (`legacy/`) or `audit/`, backticked or
  not — so `host_typecheck.ini`, `vitest.config.js`, `.gitignore`, `.nvmrc`, `mockdata/`, `dev_legacy/`, `legacy/`,
  `audit/…`, `tsconfig*.json` are caught; a leading dot is kept;
- a bare file name continuing a list resolves against the last path's directory, then the root, then a unique basename
  outside the legacy tree; a relative path (`device_scripts/x.py`, `bench/x.py`) against the nearest ancestor that has
  its first segment; brace and glob forms expand against the tree (`devices/*.toml`, `test_sensortask_{…}.py`);
- `SPEC <Part>`, a bare `BACKLOG` and `README "…"` in prose map to the root document; upstream paths (`extmod/`,
  `ports/`, `py/`, `lib/`, `shared/`) are not repository files and are skipped;
- the A.U10.37 renames are one site (old and new `src/` and `tests/test_` names).
- "Site and change" slots (A.U24.38, A.U24.39, A.U24.56) are read as Site; the four U26 actions whose Site says "the
  sites above/named last" (A.U26.45, .65, .69, .76) take the files their Why slot names, listed in the script.

**Trace.** The same extractor reads every merged change's Site, with its `## <path>` heading as the starting directory.
A pair is carried when one change's From names the action (ranges such as `A.U10.01-.05`, `A.U26.09/.32` expanded) and
its Site names the file. A From mention marked dropped/withdrawn with its reason counts as the disposition (67 pairs;
each was read). The pairs left over were read against the action's full text, the carriers' bodies and every
ledger row; §6 records each one's disposition.

**Fan-out actions.** Where an action's Site is a whole tree or a mechanical query (renames, docstrings, member order,
future imports, role names), the per-file carriers were checked with `ac3_fanout.py`/`ac3_rename_fanout.py` against
the HEAD files the query matches. This is where most of the gaps were.

## 3. Findings with amendments

Unit numbers follow each action's own unit. New M-IDs continue each file's highest number at this HEAD (GEN .063,
SRC_CORE .131, SRC_SENS .092, TEST_UNIT .339, TWIN .164, PROC .045, DOCS .108, TSC .227, HW_BENCH .135, HW_DEV .157,
TEST_HELP .067); the lead may renumber. Every new change also gets a ledger row in its file.

### S-01 (gap) The freezefs re-vendor itself has no carrier — A.SDEP.07
`ext/freezefs/{LICENSE,__main__.py,archive.py,ffsextract.py,ffsmount.py}`: M.PROC.003 (6) / the family-(d) step names
only the downstream carriers (M.SCR.072, the hash test, the THIRD_PARTY entry); M_SRC_NET drops the action pointing at
"TOOL", TOOL has no row; no change's Site names the files (`ext/freezefs/*` was a glob the old index missed).
**Amend M_GEN.md**, new section after `## ext/typings/microdot/*.pyi (new)`:
```
## ext/freezefs/* (vendored)

### M.GEN.064 Re-vendor freezefs at upstream main, unmodified
- **From**: A.SDEP.07 (the re-vendor; A-C3 Part S: no change carried the files); A.U34.08 (read: the commit record and hashes).
- **Site**: `ext/freezefs/LICENSE`, `__main__.py`, `archive.py`, `ffsextract.py`, `ffsmount.py` (whole files).
- **Change**: if upstream `main` (or its newest tag, should upstream start tagging) differs from the vendored state byte
  for byte, the five files are replaced by that commit's files, unmodified, and the commit SHA and each sha256 are
  recorded in the refresh record; otherwise unchanged. No other edit, ever.
- **Resolved**: —
- **Unit**: U0 (dependency refresh, family (d), with M.GEN.051).
- **Depends**: A.SDEP.01, A.SDEP.02.
- **Blast carried by**: `scripts/build_frozen_html.sh` → M.SCR.072; `tests_scripts/test_vendored_freezefs.py` hashes →
  M.TSC.153; THIRD_PARTY entry → M.DOCS.003; SPEC `:63` → M.SPEC.005; the silicon check of a format change → M.DOCS.064.
- **Kind**: code
```
Ledger row: `| A.SDEP.07 | M.GEN.064 |`.

### S-02 (gap) D1.22's reclassification is carried nowhere — A.U0.38
`audit/dprov/D1.md` (D1.22: "agent-as-settled" → "owner-quoted (OR87.a (b))") is in A.U0.38's Site; no merge carries an
audit-file edit of it. **Amend M.PROC.003** Change, step (8), append: "A.U0.38's audit-file part runs here with the U0
doc actions: `audit/dprov/D1.md` D1.22's class 'agent-as-settled' → 'owner-quoted (OR87.a (b))' (audit file)." Site
gains "`audit/dprov/D1.md` (D1.22)". From gains "A.U0.38 (the D1.22 audit-file edit)". PROC ledger: `| A.U0.38 | M.PROC.003 (D1.22 only) |`.

### S-03 (gap) Quoted annotations left in three files — A.U10.31
A.U10.31 counts quoted annotations naming no `TYPE_CHECKING` symbol in 21 files; three have no carrier
(`asy_notification_service.py` 3, `asy_uart_link_driver.py` 3, `print_log.py` 1; HEAD `asy_uart_link_driver.py:87`
`"tuple[bool, bytes | None]"`, `:96` `"tuple[bool, int | None]"`, `:101` `"bytearray | None"`). A.U10.47's check fails
on them at execution, so the step must exist.
- **M.SRC_SENS.030** From gains "A.U10.31 (the file's 3 quoted annotations)"; Change appends: "Every annotation in the
  file that names no `TYPE_CHECKING` symbol is bare (A.U10.31; 3 at HEAD); one a forward reference would break stays
  quoted (D.6)." Ledger SRC_SENS A.U10.31 adds M.SRC_SENS.030.
- **M.SRC_NET.211** From gains "A.U10.31 (`:87`, `:96`, `:101`)"; Change appends: "`_get_callback() -> tuple[bool,
  bytes | None]`, `_set_callback() -> tuple[bool, int | None]`, `_message_callback(..., payload: bytearray | None)`:
  unquoted (A.U10.31)." Ledger SRC_NET A.U10.31 adds M.SRC_NET.211.
- **M.SRC_CORE.060** From gains "A.U10.31 (the file's one quoted annotation)"; Change appends: "Every annotation in the
  file that names no `TYPE_CHECKING` symbol is bare (A.U10.31; 1 at HEAD); a forward reference stays quoted (D.6)."
  Unit of that stage: U10. Ledger SRC_CORE A.U10.31 adds M.SRC_CORE.060.

### S-04 (gap) D.15 member order has no step in eight files — A.U10.33
A.U10.33 lists 44 out-of-order classes. SRC_NET has a D.15 change per file; SRC_CORE has none for
`config_manager.py:215 ConfigManager`, `print_log.py:68 PrintLog`, `:133 PrintLogHistory`, `:226 PrintLogHistoryStore`,
`asy_fram_driver.py:97 FRAM_SPI`; SRC_SENS states the reorder once as a preamble convention (`M_SRC_SENS.md:14`) and
has changes only for `asy_i2c_driver.py`, `voc_algorithm.py` and `asy_isl29125_driver.py`, so `asy_bmp3xx_driver.py`
(`:125 BMP3xx_Reader`, `:403 BMP3XX_I2C`), `asy_neopixel_driver.py:43 NeopixelDriver`,
`asy_notification_service.py:135 NotificationCoordinator`, `asy_scd30_driver.py` (`:118`, `:444`),
`asy_sgp40_driver.py` (`:129`, `:542`) and `asy_spi_driver.py:33 SPI` have no step (A-C2 builds steps from changes,
not from conventions). **New M.SRC_CORE.132** (under `## src/config_manager.py`, Site also naming the other two) and
**new M.SRC_SENS.093** (after M.SRC_SENS.088), each:
```
### M.SRC_<X>.nnn D.15 member order in the remaining classes
- **From**: A.U10.33 (A-C3 Part S: the classes below had no carrier).
- **Site**: <the file:line class list above for the cluster>.
- **Change**: A.U10.33's script-driven pure move per class, after every other U10 edit to the same file; AST
  comparison (same (name, body) set, comment multiset unchanged); later stages insert at the D.15 position (A.U10.47).
- **Resolved**: —   - **Unit**: U10 (last U10 change per file).   - **Depends**: the file's other U10 changes.
- **Blast carried by**: lint/typecheck baselines → A.U10.33 (TOOL).   - **Kind**: code
```
Ledger rows: SRC_CORE `A.U10.33` adds M.SRC_CORE.132; SRC_SENS `A.U10.33` adds M.SRC_SENS.093.

### S-05 (gap) Docstrings-to-comments has no carrier in five scopes — A.U10.34
A.U10.34 converts every function/class docstring in every Python scope (AST at HEAD: buildgen 21, scripts 8,
toolchain 47, tests_scripts 72, tests 26, digital_twin 4, tests_hardware 102). Carried: `toolchain/` (M.TOOL.035/.043/
.066/.067), `scripts/_digital_twin_ci_suite.py` (M.SCR.046), `tests_scripts/test_comment_block_cap.py` (M.TSC.065),
`tests_hardware/manual/runner.py` (M.HW_BENCH.100), the two `src/` sites. Uncarried, with their HEAD lines:
- GEN — `buildgen/definitions.py` (:122, :486); `model.py` (:129); `pico_gpio.py` (:80); `schema_ast.py` (:43);
  `tag_comments.py` (:28, :183, :211, :225, :234); `twin_wiring.py` (:34); `validate.py` (:137, :160, :177, :182, :190,
  :207, :231, :255); `version.py` (:11); `web_tag.py` (:38).
- SCR — `scripts/_strip_type_checking.py` (:10, :21, :67).
- TSC — `_script_loader.py` (:11); `conftest.py` (:22, :37); `test_bench_harness_helpers.py` (:98);
  `test_build_firmware.py` (:20); `test_buildgen_definitions.py` (:38); `test_buildgen_validate.py` (:1023, :1102);
  `test_ceiling_probe.py` (:21); `test_device_tomls.py` (:247, :271); `test_digital_twin_boot_contiguity.py` (:86, :114,
  :151); `test_digital_twin_ci_suite_ceiling.py` (:86); `test_digital_twin_ci_suite_errcount.py` (:17, :265, :340);
  `test_digital_twin_generated_boot.py` (:109, :116, :136); `test_gc_collect_sites.py` (:25); `test_heap_map_parser.py`
  (:206); `test_js_coverage_report_dir.py` (:19); `test_lint_sh.py` (:16, :36); `test_measurement_field_tuple_agreement.py`
  (:33); `test_micropython_overrides.py` (:135, :171, :274, :453, :804); `test_persistence_write_marker_completeness.py`
  (:56, :65, :77, :99, :109, :116, :124, :136, :147, :210, :356); `test_request_body_cap_headroom.py` (:44, :81);
  `test_request_timeout_ceiling.py` (:19, :48); `test_require_clean_hardware_run_sh.py` (:24, :36, :53);
  `test_resolve_board_device.py` (:18); `test_setup_cross_browser_toolchain_sh.py` (:14); `test_setup_toolchain_env.py`
  (:27, :43, :268, :380); `test_test_sh.py` (:91, :105, :159, :201, :275, :287, :390, :478, :564, :634, :684, :716,
  :764); `test_tests_hardware_conftest_constants.py` (:16, :41) — all under `tests_scripts/`.
- TEST_HELP — `tests/_boot_contiguity_probe.py:53`; `_bus_hazard_catalog.py` (:350, :368, :410, :455, :502, :523);
  `_shared_rest_roundtrip.py` (:18, :26, :35); `_strict_json.py:119`; `_tmp_scratch.py` (:36, :57, :69);
  (`_webserver_concurrency_scenarios.py`'s six go with the file, A.U25.46.)
- TEST_UNIT — `tests/test_asy_uart_link_driver.py:143`; `test_bus_hazard_generated.py:47`; `test_system_service.py`
  (:959, :977).
- TWIN — `digital_twin/_http_client.py:48`; `unix_port_gc_unwedge.py:7`; `unix_port_poll_prewarm.py` (:30, :48);
  `tests/test_digital_twin_bus_hazard_concurrency.py:90`.
- HW_BENCH / HW_DEV — carried only by the preamble conventions B3 (`M_HW_BENCH.md:41-43`, `M_HW_DEV.md:44-45`).

**Amendment**: one new change per cluster, landing in U10, each with this body (Site = that cluster's list above):
new **M.GEN.065**, **M.SCR.075**, **M.TSC.228**, **M.TEST_HELP.068**, **M.TEST_UNIT.340**, **M.TWIN.165**, and
**M.HW_BENCH.136** / **M.HW_DEV.158** whose Site is "every function, method and class docstring under
`tests_hardware/` (AST query; 102 at HEAD in 28 files: HW_DEV the device scripts and `flash/`, HW_BENCH the rest)" and
whose Resolved says "the B3 convention is this change".
```
- **From**: A.U10.34 (A-C3 Part S: no carrier in this cluster).
- **Change**: each function, method and class docstring becomes a `#` comment block directly under the `def`/`class`
  line, same text, ≤ 3 prose lines (overflow to the owning doc per CLAUDE.md's comment rule); module docstrings stay
  (the five argparse readers included). A file a later change rewrites carries the form forward.
- **Resolved**: —   - **Unit**: U10.   - **Depends**: —
- **Blast carried by**: `tests_scripts/test_comment_block_cap.py` stays green → M.TSC.065.   - **Kind**: code
```

### S-06 (gap) Future-import removal in 28 bench files rests on a convention — A.U20.33
Fan-out at HEAD: every `from __future__ import annotations` in `scripts/`, `toolchain/`, `tests_scripts/` has a carrier;
in `tests_hardware/` 28 of 40 files have only the HW_BENCH B2 convention (`M_HW_BENCH.md:37-40`): `bench_control.py`,
`soak_tiers.py`, `harness.py`, `isl29125_conformance.py`, `heap_map.py`, `error_log_helpers.py`, `manual/`
(`manual_sensor_accuracy.py`, `manual_wifi.py`, `runner.py`, `manual_persistence.py`, `manual_bus_electrical.py`,
`manual_toolchain.py`), `http_client.py`, `website_identity.py`, `conftest.py`, `rogue_udp_responder.py`, `bench/`
(`test_rest_endpoints_over_sta.py`, `test_hotspot_role_reversal.py`, `test_wifi_networking.py`, `test_end_to_end_timing.py`,
`test_uart_link_under_api_load.py`, `test_network_resilience.py`, `test_bus_concurrency_under_api_load.py`,
`test_heap_under_connection_ceiling.py`, `dns_probe.py`, `test_sensor_config_push_over_real_hardware.py`,
`test_memory_stress_bench.py`, `test_serving_heap_at_default_gc.py`). **New M.HW_BENCH.137** "B2 host annotations
across the cluster": From A.U20.33; Site the 28 files; Change = convention B2's text; Unit U20; Resolved "the B2
convention is this change"; Blast "`host_typecheck.ini` pass stays green → M.TOOL.079".

### S-07 (gap) Public `make_*` builders in 22 test files — A.U24.76
A.U24.76: "the 87 file-local `def make_*` builders in 34 `tests/test_*.py` files (15 already `_make_*`)" take the
private form, and its L0 check (`tests_scripts/test_microtest.py`) fails on any public one. TEST_UNIT's convention says
each file's change names it; these files' changes do not (public `def make_` count at HEAD): `test_asy_bmp3xx_driver.py`
(4), `test_asy_neopixel_driver.py` (1), `test_asy_sgp40_driver.py` (5), `test_asy_spi_driver.py` (2),
`test_asy_uart_comm.py` (1), `test_asy_uart_driver.py` (1), `test_base_classes.py` (1), `test_captive_dns.py` (3),
`test_fram_integration.py` (1), `test_machine_uart_link.py` (1), `test_notification_fram_integration.py` (3),
`test_notification_neopixel_integration.py` (1), `test_notification_scd30_integration.py` (3),
`test_notification_scd30_sgp40_integration.py` (3), `test_notification_sgp40_integration.py` (2), `test_print_log.py`
(1), `test_setter_microdot_integration.py` (4), `test_system_service.py` (3), `test_voc_algorithm.py` (2) — TEST_UNIT;
`test_digital_twin_isl29125.py` (1), `test_digital_twin_isl29125_autorange.py` (1), `test_digital_twin_machine_uart.py`
(1) — TWIN. **New M.TEST_UNIT.341** and **new M.TWIN.166** "File-local builders take the private form": From A.U24.76;
Site the files above; Change "every module-level `def make_<x>` → `_make_<x>` with its uses in the file (a builder
another change replaces by a shared helper is skipped there)"; Unit U24; Depends A.U24.49; Blast "the L0 check →
A.U24.76 (TSC)".

### S-08 (gap) The missing-key-directory test is not rewritten — A.U24.38
`tests/test_tmp_scratch.py:116-123` `test_construction_and_teardown_tolerate_a_missing_key_directory_entirely` asserts
only "no exception". **Amend M.TEST_UNIT.338**: From gains "A.U24.38 (`:116-123`)"; Site gains "`:116-123`"; Change
appends: "`test_construction_and_teardown_tolerate_a_missing_key_directory_entirely` runs under `_RecordingOs`: the
recorded calls touch only the key path (never the shared root), and the key directory does not exist afterwards."
Ledger TEST_UNIT `A.U24.38` adds M.TEST_UNIT.338.

### S-09 (gap) The network fake keeps five explicit `Any` — A.U25.63
`digital_twin/network.py` (`:18` import, `:63` `_stations`, `:65` `config_calls`, `:66` `connect_calls`, `:136`
`status()` return) is in A.U25.63's site list ("`network.py` (5)"); M.TWIN.040 rewrites the whole file but neither
names A.U25.63 nor types these. **Amend M.TWIN.040**: From gains "A.U25.63 (the file's five `Any`)"; Change appends
(agent proposal under A.U25.63's and G8/R61's "no hand-written `Any`"; A.U25.63 names the file's count, not the types):
"no explicit `Any`: `_stations: list[tuple[bytes]]` (rp2's one-element MAC tuples), `config_calls:
deque[dict[str, object]]`, `connect_calls: deque[tuple[str | None, str | None]]`, `status() -> int | list[tuple[bytes]]`;
the `typing.Any` import goes." Ledger TWIN `A.U25.63` adds M.TWIN.040.

### S-10 (conflict) The UART load script still counts a churn `MemoryError` — A.U26.47 (3)
A.U26.47 (3): in `uart_link_under_concurrent_system_load.py` "a `MemoryError` is recorded as a failure … and the run
ends FAIL; `alloc_failures` leaves the PASS line". M.HW_DEV.051 (2) keeps "`except MemoryError` keeps `held = []` and
`load.alloc_failures += 1`", and no host assertion fails on it; M_HW_DEV's ledger maps A.U26.47 to M.HW_DEV.095 (a
different file). Settled by A.U26.47 and CLAUDE.md's memory rule (a caught-and-degraded allocation failure is a
defect, not a passing result). **Amend M.HW_DEV.051**: From gains "A.U26.47 (3)"; Change (2) → "`_memory_churn_loop`'s
`except MemoryError` keeps `held = []`, records one bounded failure ('churn allocation of 512 B failed while <= 25
blocks were held') and loses `gc.collect()`; the facts carry `alloc_failures`, and the host load test (M.HW_DEV.045)
asserts it is 0, so the run fails on any churn allocation failure." **Amend M.HW_DEV.045** Change (3) append: "the load
test asserts `alloc_failures == 0` (A.U26.47 (3))"; From gains "A.U26.47 (3)". Ledger HW_DEV: `| A.U26.47 | merged
into M.HW_DEV.045, M.HW_DEV.051; M.HW_DEV.095 (soak markers) |`.

### S-11 (conflict) The emitted maintenance keys spell names `MAINTENANCE_NAMES` should give — A.U6.20 (2)
M.GEN.035 says `MAINTENANCE_NAMES = {"sgp40": "SGP40", "uart_link": "UARTLINK"}` is "read by `definitions.py` and
`codegen.py`" (A.U6.20 (2): `codegen.py:629, :634` read it); M.GEN.009, the change that rewrites those lines, emits the
literals `"SGP40"`/`"UARTLINK"` and does not name A.U6.20. Settled by A.U6.20 (2). **Amend M.GEN.009**: From gains
"A.U6.20 (2) (`:629`, `:634` read `MAINTENANCE_NAMES`)"; in Change replace "maintenance one entry per SGP40 keyed by
its `resolved_name` (`"SGP40"`, `"SGP40_<ext>"`) plus `("UARTLINK", <initiator var>.get_link_status)`" by "maintenance
one entry per SGP40 keyed by its `resolved_name` (`MAINTENANCE_NAMES["sgp40"]`, `MAINTENANCE_NAMES["sgp40"] + "_<ext>"`)
plus `(MAINTENANCE_NAMES["uart_link"], <initiator var>.get_link_status)`; `codegen.py` spells neither name";
Depends gains M.GEN.035.

### S-12 (gap) The Vitest timeout tag has no carrier — A.U8.15
A.U8.15 tags `vitest.config.js:31` `testTimeout: 20000` as `l0.vitest_test_timeout_ms = 20000`; WEB's ledger has no
A.U8.15 row, M.WEB.074 (the file's change) does not write it. **Amend M.WEB.074**: From gains "A.U8.15 (`:31` tag)";
Change appends: "`// @tunable l0.vitest_test_timeout_ms = 20000` on its own line directly above `testTimeout: 20000`
(A.U8.02's grammar); the backstop comment above it stays within the 3-line cap." Ledger WEB: `| A.U8.15 | M.WEB.074 |`.

### S-13 (gap) The new skill file has no carrier — A.U36.543 (9)
New `.claude/skills/integrate-module/SKILL.md` (A.U36.543 (9)); M.DOCS.060 only adds the README map entry. **New
M.DOCS.109** under a new section `## .claude/skills/integrate-module/SKILL.md (new)`: From "A.U36.543 (9)"; Site the
new file; Change "front matter `name: integrate-module`, `description: Add a module, service or sensor driver to this
repo by walking SPECIFICATION.md Part K in order.`; body ≤ 10 lines as A.U36.543 (9) writes it (read Part 0 and Part K
in order, then apply Part D); no audit ID"; Unit U36; Depends the Part K rewrite (M.SPEC changes of A.U36.543);
Blast "README map entry → M.DOCS.060". Ledger DOCS adds the row.

### S-14 (gap) The twin-suite deadline helper's L0 case — A.S0930.34 (4)
"An L0 case gives [`_commanded_reset_deadline_s()`] a temporary copy of `src/system_service.py` with
`_RESET_DELAY`/`_TASK_CHECK_TIME` changed and asserts the deadline follows both": TSC carries (2) and (3) only.
**Amend M.TSC.165**: From gains "A.S0930.34 (4) (deadline-helper case)"; Change appends: "`_commanded_reset_deadline_s()`
over a `tmp_path` copy of `src/asy_system_service.py` with `_RESET_DELAY` and `_TASK_CHECK_TIME` changed equals their sum
plus the named margin, following both." Unit: with M.SCR.054 (S0930, after U25). Ledger TSC `A.S0930.34` adds M.TSC.165.

### S-15 (structural) Script-driven sweeps and conventions form no step
A-C2 builds steps from merged changes. Several U10/U36 actions are one script over the whole tree; their per-file
carriers cover part of the files and cluster preamble conventions claim the rest (TEST_UNIT "U10 rename sweep, per
file", HW_BENCH/HW_DEV B1-B4, SRC_SENS "Names", TWIN's renames). Files that use an old name at HEAD and are named by no
change carrying the action (`ac3_rename_fanout.py`; generic names make A.U10.44's list noisy):
- A.U10.40 (REST/config keys), 16 files: `tests/test_api_response.py`, `tests/test_base_classes.py`,
  `tests/test_digital_twin_sensortask_integration.py`, `tests/test_tmp_scratch.py`,
  `tests_hardware/bench/test_bus_concurrency_under_api_load.py`, `tests_hardware/bench/test_memory_stress_bench.py`,
  `tests_hardware/device_scripts/isl29125_mechanism_envelope.py`, `tests_hardware/device_scripts/isl29125_real_irq_edge.py`,
  `tests_hardware/manual/manual_persistence.py`, `tests_js/_put_field_cases.js`, `tests_js/mock-server-put-matrix.test.js`,
  `tests_scripts/test_buildgen_definitions.py`, `test_buildgen_generate.py`, `test_buildgen_schema_ast.py`,
  `test_buildgen_web_tag.py`, `test_persistence_write_marker_completeness.py` (the two `html/definitions/*.json` go at U6).
- A.U10.37 (module renames), 14 files importing an old module: `BACKLOG.md`, `tests/test_asy_sgp40_driver.py`,
  `tests/test_digital_twin_bus_hazard_concurrency.py`, `tests/test_digital_twin_isl29125_autorange.py`,
  `tests/test_digital_twin_sensortask_integration.py`, and nine device scripts (`fram_cs_hijack_fault_injection_and_recovery.py`,
  `fram_reset_race_during_write_seed_and_race.py`, `fram_reset_race_during_write_verify_recovery.py`,
  `fram_same_device_rw_concurrency.py`, `heap_layout_after_full_boot_sequence.py`, `isl29125_lighting_scenarios.py`,
  `isl29125_mechanism_envelope.py`, `system_debug_level_raise_for_boot_log_check.py`, `system_debug_level_restore_after_boot_log_check.py`).
- A.U10.38 (class renames), 33 files (several carried in substance under A.U20.41/A.U36.x, which still leaves no
  A.U10.38 step in U10): `BACKLOG.md`, `HEAP_FRAGMENTATION_MEASUREMENTS.md`, `buildgen/{buildspec,definitions,model,validate}.py`,
  `digital_twin/{machine,run_generic_integration}.py`, `scripts/run_digital_twin_ci.sh`, `scripts/run_unix_port_integration.sh`,
  `src/base_classes.py`, `src/config_manager.py`, `tests/_digital_twin_construction_scenarios.py`,
  `tests/test_asy_fram_driver.py`, `tests/test_asy_sgp40_driver.py`, `tests/test_digital_twin_{bus_hazard_concurrency,sensortask_integration,uart_link}.py`,
  `tests_hardware/bench/{dns_probe,test_network_resilience,test_rest_endpoints_over_sta,test_uart_link_under_api_load}.py`,
  `tests_hardware/device_scripts/{bmp3xx_plausibility_read,sgp40_fram_backup_restore,wifi_service_reconnect_repro}.py`,
  `tests_hardware/flash/test_fram_storage.py`, `tests_scripts/buildgen_fixtures/novel_combo.toml`,
  `tests_scripts/test_buildgen_{definitions,generate,graph,tag_comments,validate}.py`, `tests_scripts/test_digital_twin_ci_suite_errcount.py`.
- A.U10.18 (lock names): `src/asy_sgp40_driver.py:169` comment "`_datalock`-guarded get_data()" (→ `_data_lock`).
- A.U10.35 (92 private attributes) and A.U10.44 (starter/loop names): same shape; their own method (mypy
  `attr-defined`, grep) finds the readers at execution.
- A.U36.038 (2) (the Python D.15 reorder of every host scope, U36): carriers only M.GEN.010/.011, M.SCR.063,
  M.TEST_HELP.034; nothing for `digital_twin/`, `toolchain/`, the `tests/` and `tests_scripts/` files, `tests_hardware/`.
**Amendment: M_PROC.md** gains, under "File edits carried elsewhere", two merged changes:
```
### M.PROC.046 U10 rename and key sweeps run once over the whole tree
- **From**: A.U10.18, A.U10.35, A.U10.37, A.U10.38, A.U10.40, A.U10.43, A.U10.44 (the whole-tree halves; A-C3 Part S).
- **Site**: every tracked file outside `legacy/`, `ext/`, `arduino/`, `audit/` and the UART changelog that a renamed
  name or key reaches (each action's own query); the per-file merged changes carry their files' context edits.
- **Change**: per action, in U10 after its per-file changes: the action's script/rename map is applied once over the
  scope, then its completion check runs — `grep -rn` of every old name/key empty (A.U10.37/.38/.40/.43/.44), the
  three mypy passes clean with no `attr-defined` (A.U10.35/.18). The files A-C3 Part S lists (S-15) are named in the
  step's record as covered by this sweep.
- **Resolved**: the cluster conventions (TEST_UNIT "U10 rename sweep", HW_BENCH/HW_DEV B1, SRC_SENS "Names") describe
  this step; they are its per-cluster wording, not separate steps.
- **Unit**: U10 (each sweep after its action's per-file changes, before U11).   - **Depends**: the U10 per-file changes.
- **Blast carried by**: each action's own Blast (unchanged).   - **Kind**: code, test, doc
```
and **M.PROC.047 "U36 host-scope reorder runs once over every Python scope"** (From A.U36.038 (2); Site every Python
file of the eight scopes; Change A.U36.038 (2)'s script-driven move, AST-verified per file, after M.TSC.044/.064's
widened check lands; Unit U36; Resolved "GEN/SCR/TEST_HELP/WEB carry their files' context; this step covers the
rest"). A-C2: S-04 to S-07 and S-15 replace convention-only coverage with steps; the remaining preamble conventions
(HW_BENCH B4, HW_DEV B4 `@tunable` tags; B5 permanent text) are already carried per file by named changes.

### S-16 (trace) The datasheet move's change names neither the action nor the files — A.U28.35
M.PROC.018 (2) performs `git rm` of the PDFs and `git submodule add … datasheets` "in one commit (A.U28.35 …)", but its
From has no A.U28.35 and its Site names the owner's GitHub repository only. **Amend M.PROC.018**: From gains "A.U28.35
(the move)"; Site gains "`datasheets/` (the tracked PDFs, moved out); `.gitmodules` (new)". Ledger PROC: `| A.U28.35 | M.PROC.018 |`.

### S-17 (trace) The B3 working files are opened by a change that names one action — A.U35.03/.04/.08/.22/.23/.28/.41/.50
M.PROC.022 opens every `audit/b3/` file (`review.md`, `faults.md`, `matrices.md`, `timing.md`, `load.md`, `e51.md`,
`conformance.md`, `levels.md`), From names only A.U35.01. **Amend M.PROC.022** From → "A.U35.01; the rows of A.U35.03
(`review.md`), A.U35.04 (`faults.md`), A.U35.08 (`matrices.md`), A.U35.22 (`levels.md`, with M.PROC.023), A.U35.23
(`timing.md`), A.U35.28 (`load.md`), A.U35.41 (`e51.md`), A.U35.50 (`conformance.md`)". PROC ledger gains those eight
rows → M.PROC.022.

### S-18 (trace) A.S0930.22's FRAM-manager file is placed elsewhere without saying so
A.S0930.22's Site lists `tests/test_asy_fram_manager.py`; its case (3) (a FRAM write in flight) lands in
`tests/test_system_service.py` through M.TEST_UNIT.306, whose Resolved names only `test_config_manager.py`. **Amend
M.TEST_UNIT.306** Resolved, append: "It also lists `tests/test_asy_fram_manager.py`: case (3) runs here through the
command sequence with the gated fake chip, so that file gains nothing."

## 4. From completions (the change carries the action's edit; its From does not name it)

Each: add the A-ID to the change's From, and the change to the action's ledger row in that file.

| M-ID | add to From | what the body already carries |
|---|---|---|
| M.DOCS.064 | A.C.10 (phase-C removal of delivered rows) | Unit "then phase C"; DOCS ledger already maps A.C.10 here |
| M.SRC_SENS.054 | A.U0.35 (B03, `:162-163`: superseded by A.U15.04's comment, which fixes the dangling CLAUDE.md pointer) | the `_init_scd()` comment rewrite |
| M.SRC_SENS.033 | A.U10.21 (`setup() -> bool`), A.U11.31 (`reset_error_counter()` returns the reset's bool) | both in its Change/Resolved |
| M.SRC_SENS.061 | A.U10.31 (`get_data() -> _ConstValue` unquoted) | stated in Change |
| M.HW_BENCH.050 | A.U2.03 (the U2 `from _error_codes import code` import) | stated in Unit |
| M.TEST_HELP.001 | A.U21.13 (microtest runs where no fake exists, `tests/lwip_host/`) | agent decision D1 |
| M.WEB.054 | A.U23.36 (the masked-field cases) | in Change |
| M.WEB.031 | A.U23.04 (the entry passes the document-derived visibility through the shared shell) | M.WEB.030 carries it for `main.js`; `app.js` takes the same shell |
| M.PROC.023 | A.U35.22 (its `levels.md` rows) | the file M.PROC.023 maps |

## 5. Blast-pointer sweep, repo-wide (AC_NOTES 49)

Every "Blast carried by" slot of the 16 merges, split at top-level `;`: 3,957 items. An M-ID must exist; an A-ID must
be in some merged change's From (any cluster); where an item names a target cluster, that cluster's file (outside its
ledger) must hold the A-ID, else it was read by hand; items with no ID were checked for a Site carrier of every path
they name.
- **M-IDs (831)**: one missing. **M.DOCS.085** Blast "J.7's L2 cells name the two twin files (M.TWIN.153/.154 → SPEC)"
  → "(M.TWIN.154/.156 → SPEC)": M.TWIN.153 does not exist; the two files are M.TWIN.154 (comm hazard) and M.TWIN.156
  (field sweep).
- **A-IDs (2,821 items)**: none uncarried. 10 IDs the parser built from shorthand (`A.U11.S01, A.U11.21`,
  `A.U16.R03/U25`, …) were read: none is a real pointer. 107 items name a cluster that does not hold the A-ID; each was
  read: 101 are carried by the real owner (Part N rows by M.SPEC.156/.157, release-note lines by M.DOCS.059, BACKLOG
  chroot entries by M.DOCS.066, `.gitignore` by M.PROC.019, phase-C items by M.PROC.036, `watchdog=` by A.U20.02's
  twin changes, the L2 webserver cases by M.SCR.018 (l), as G1-G4 found). Six items need a pointer correction (one stale pointer in two changes, four labels):
  - **M.HW_DEV.060** and **M.HW_DEV.063** Blast "seam-count L0 … → A.U26.43 (TSC)" → "seam count → M.TEST_UNIT.041 (an
    L1 recording fake, gap pass G3 B6)": no TSC change carries A.U26.43.
  - **M.SPEC.153** Blast "twin test comments → A.U36.020 (TEST_UNIT)" → "(TWIN, M.TWIN.122/.126)".
  - **M.SRC_NET.165** "`tests_scripts/test_suppression_form.py` → A.U28.30 (SCR)", **M.SRC_NET.172** and **M.SRC_NET.204**
    "A.U10.47's check (SCR)": label → TSC (the check is a `tests_scripts/` file).
- **No-ID items (305)**: 11 name a path no Site appeared to carry; all 11 resolve (a bare test-file name — M_TSC/M_WEB
  carry each; `GAPS_G2.md` hand-offs). The rest were read by G1-G4.

## 6. Disposition ledger (every pair not carried as found)

Classes: READ (source, input or oracle read, not edited); REF (the file is named in text or a quotation); RUN (a round
or step runs it); NOEDIT (the action states the site stays); DIR (a directory named as a grep scope; its files traced
one by one); GLOB (a glob over-matches the action's real sites); ART (extractor artefact); OTHER (another named change
carries it); OBSOLETE (the site leaves first); GENERIC (a change whose Site is the action's whole set, e.g. "every
device script printing RESULT:"); RECHECK (re-read only, M.PROC.008 runs the re-check; an edit only if the fact moved,
as a delta).

| action | file(s) | disposition |
|---|---|---|
| A.C.06 | `tests_hardware/bench/test_uart_link_crc16.py` | RUN; created by M.HW_BENCH.094 (A.S0930.06) |
| A.C.08 | `tests_hardware/bench` | RUN |
| A.C.10 | `devices/*.toml` (6) | M.PROC.036 Blast carries the round deltas ("TOML origin comments") (OR106.a) |
| A.C.10 | `BACKLOG.md` | §4 (M.DOCS.064) |
| A.SDEP.07 | `ext/freezefs/*` (5) | S-01 |
| A.SDEP.08 | `audit/`, `ext/`, `datasheets/` | REF (grep exclusions) |
| A.SDEP.08 | `CLAUDE.md`, `pyproject.toml:237-238` | RECHECK |
| A.SDEP.15 | `src/asy_ntp_client.py`, `asy_scd30_driver.py`, `asy_sgp40_driver.py`, `system_service.py` | READ (W10 symptom sites; only the bmp3xx/isl29125 comments are edited) |
| A.SDEP.19 | `toolchain/setup_toolchain.py` | READ (W33: the retry stays; its reason text is elsewhere) |
| A.SDEP.23 | `audit/actions/` | carried by M.PROC.013 (audit files) |
| A.S0930.04 | `tests/_field_sweep.py` | ART (`…_field_sweep.py` = `tests/test_digital_twin_uart_field_sweep.py`, M.TWIN.156) |
| A.S0930.22 | `tests/test_asy_fram_manager.py` | S-18 |
| A.S0930.26, A.U20.07, A.U31.03 | `tests/test_sensortask_<device>.py` | NOEDIT (the wrappers register every scenario through `register_for_device()`, `tests/test_sensortask_wozi.py:4-6`; one file at U24, M.TEST_UNIT.337) |
| A.S0930.29 | `config_files_dump.py`, `config_files_restore.py` | ART (device scripts: M.HW_DEV.100/.101) |
| A.S0930.34 | `tests_scripts/test_digital_twin_ci_suite_*.py` | S-14 |
| A.S0930.35 | `CLAUDE.md` | REF |
| A.U0.02 | `audit/REGISTER.md`, `audit/pass2/*` (23), `audit/harvest`, `audit/refined` | carried: M.PROC.003 (1) runs it "as written"; M.DOCS.042 names `audit/` |
| A.U0.35 | `src/asy_scd30_driver.py` | §4 |
| A.U0.38 | `audit/dprov/D1.md` | S-02 |
| A.U1.04/.05/.06 | `tests_hardware/README.md` | carried under the file's heading (M.HW_BENCH.111/.112/.113) |
| A.U1.07 | `dev_legacy/README.md` | READ |
| A.U1.11 | `modules/_boot.py`, `modules/sensortask.py` | REF |
| A.U10.07 | `buildgen/codegen.py` | READ ("read-only here") |
| A.U10.18 | `src/asy_fram_manager.py` | NOEDIT (no renamed lock name in the file, grep); `asy_sgp40_driver.py:169` → S-15 |
| A.U10.21 | `src/asy_notification_service.py` | §4 |
| A.U10.26 | `src/asy_webserver_service.py` | READ ("already conform") |
| A.U10.29/.39/.44, A.U2.04, A.U16.04, A.U19.16, A.U24.01, A.U28.30, A.U30.19, A.U36.542, A.U8.13 | `src` | DIR |
| A.U10.31 | notification, uart_link_driver, print_log | S-03; `asy_sgp40_driver.py` §4 |
| A.U10.31 | `asy_dns_client.py`, `asy_fram_driver.py`, `asy_udp_socket.py`, `crc_checks.py`, `framing_codecs.py`, `voc_algorithm.py` | GLOB ("every `src/*.py`"; the action's count lists none there) |
| A.U10.33 | eight files | S-04 |
| A.U10.34 | `buildgen`, `scripts`, `tests_scripts`, `tests`, `digital_twin`, `tests_hardware` | S-05 |
| A.U10.35 | `audit/refined/S09.md` | READ; `src` DIR; the sweep → S-15 |
| A.U10.37/.38/.40/.43/.44 | per S-15 | S-15; `src/voc_algorithm.py` (A.U10.38, .43) NOEDIT (Sensirion names kept, per-file N801, L01); `src/asy_i2c_driver.py` (A.U10.38) NOEDIT (wrappers keep their names); `asy_wifi_service.py` `wifi_refresh_sec` (A.U10.43) OTHER (parameter removed, A.U18.40/V.U18.D) |
| A.U11.31 | `src/asy_notification_service.py` | §4 |
| A.U11.S01 | `src/asy_webserver_service.py`, `buildgen/codegen.py` | dropped by the lead ruling AC_NOTES 38 GAP-14 (never-true checks not written) |
| A.U14.12, A.U20.41, A.U30.11, A.U14.36 | `src/system_service.py`, `src/crc_checks.py`, `src/asy_udp_socket.py` | REF |
| A.U14.28 | `tests/test_digital_twin_sensortask_integration.py` | disposed in M.TWIN.144 ("`:128-129` comment is moot") |
| A.U17.28 | `src/asy_uart_comm.py` | NOEDIT (`clear()` unchanged) |
| A.U18.44 | `src/asy_dns_client.py`, `asy_udp_socket.py` | NOEDIT ("no `Any`, grep") |
| A.U19.23 | `src/asy_webserver_service.py` | READ ("the client-triggerable log calls it drives, unchanged") |
| A.U2.03 | `tests_hardware/error_log_helpers.py` | §4 |
| A.U2.23 | `CLAUDE.md:391` | OTHER (per A.U2.08, M.DOCS.090) |
| A.U20.17, A.U20.32, A.U37.10 | `buildgen`, `buildgen/*.py` (17), `devices/*.toml` | DIR/GLOB (grep scopes; the named sites are traced) |
| A.U20.33 | `tests_hardware` (28) | S-06; `buildgen` DIR (no future import there) |
| A.U20.36 | `buildgen/codegen.py`, `definitions.py` | READ |
| A.U21.13 | `tests/microtest.py` | §4 |
| A.U23.01 | `mockdata/samples.json` | REF |
| A.U23.04 | `js/app.js` | §4 |
| A.U23.25, A.U24.66, A.U25.23, A.U27.27, A.U36.511 | `js`, `tests_scripts`, `scripts`, `devices` | DIR |
| A.U23.36 | `tests_js/render.test.js` | §4 |
| A.U23.41 | `js/*.js` (8) | READ (L0 guard scope; "the end state passes it") |
| A.U23.48 | `html_raw/*`, `legacy` | READ (oracle pages; M.PROC.045) |
| A.U24.17 | `tests/_uart_link_contract.py` | REF (the pattern cited) |
| A.U24.38 | twin test files | OTHER (A.U25.51's); `tests/test_tmp_scratch.py` S-08 |
| A.U24.45 | `src/asy_wifi_service.py` | disposed in M.SRC_NET.078 (the `led_pin` tests are void) |
| A.U24.49, A.U10.35 | `audit/refined/S09.md` | READ |
| A.U24.56 | `js/templates.js` | OTHER ("the `js/templates.js:293` copy is U23's"); `tests/sensortask_<device>.py`, `run_wozi_integration.py`, `run_dev_integration.py`, `modules/sensortask-wozi.py` REF (retired names quoted); `audit/actions/U1.md` READ; SPEC REF |
| A.U24.57 | `src/asy_isl29125_driver.py` | READ ("read only") |
| A.U24.67 | `tests/test_config_manager.py` (`:268`, `:340`) | OTHER (A.U19.02 + A.U36.513 in its TEST_UNIT change) |
| A.U24.67 | `tests/test_asy_webserver_service.py:742` | OTHER (rewritten by the file's legacy-pointer change) |
| A.U24.67 | `tests/test_notification_*_integration.py` | OTHER (A.U36.513, M.TEST_UNIT.276/.278/.280/.281) |
| A.U24.67 | `tests/test_digital_twin_*` | OTHER ("U25's") |
| A.U24.69 | `tests/test_digital_twin_sensortask_integration.py`, `scripts/_digital_twin_ci_suite.py`, `js`, `tests_js` | REF (the port takers named; the lock is in the runners, M.SCR.012/.013/.039/.061, M.WEB.061/.062/.078) |
| A.U24.73 | `tests/_webserver_concurrency_scenarios.py` | OBSOLETE (retired by A.U25.46, M.TEST_HELP.031) |
| A.U24.76 | 22 test files | S-07 |
| A.U25.34 | `scripts/run_digital_twin_ci.sh` | NOEDIT (`:43-47` unchanged) |
| A.U25.46 | `scripts/run_digital_twin_ci.sh`, `scripts/test.sh` | OTHER (wired in U27: M.SCR.061, M.SCR.041 Resolved) |
| A.U25.59 | `digital_twin/_fram_chip.py` | GLOB (an SPI chip; the I2C replug knob does not apply) |
| A.U25.62 | `digital_twin/*.py` | GENERIC (every reference; TWIN's listed changes) |
| A.U25.63 | `digital_twin/network.py` | S-09 |
| A.U26.16 | `tests_scripts/test_bench_harness_helpers.py` | OTHER (its own file, M.TSC.026 Resolved) |
| A.U26.19 | `BACKLOG.md` | GENERIC (M.DOCS.066's per-unit chroot list) |
| A.U26.22 | `fram_same_device_rw_concurrency.py` | GENERIC (M.HW_DEV.007's per-script regions) |
| A.U26.47 | `uart_link_under_concurrent_system_load.py` | S-10 |
| A.U26.66 | `{scd30,sgp40,bmp3xx,fram}_conformance_probe.py` | ART (device scripts: M.HW_DEV.130-.132/.144) |
| A.U26.68, A.U8.08 | device scripts (glob) | GENERIC (M.HW_DEV.002 / M.HW_DEV.004) |
| A.U26.86 | `reboot_fallback_starves_the_watchdog.py` | REF |
| A.U27.07, A.U37.03 | `ext`, `legacy`, `UART_C_PORT_CHANGELOG.md` | REF (scope exclusions) |
| A.U27.30 | `js`, `tests_js` | GLOB ("none in `js/`/`tests_js/`") |
| A.U27.33 | four runner scripts | GLOB (the 14-script survey found nothing to change in them) |
| A.U27.36 | `scripts/main.py` | ART (the boot entry's staged name on the board) |
| A.U28.35 | `datasheets/*` | S-16 |
| A.U30.18 | `audit/stack_depth.py` | audit-scratch analysis, not a tree file; its results land through M.TSC.007/.020/.076, M.SPEC.092 |
| A.U32.01 | `legacy/README.md`, `tests_hardware/README.md` | REF (home choice reasoning; the runbook lands in README.md, M.DOCS) |
| A.U32.04, A.U32.05 | `python/…`, `modules/…`, `improved-quality/…` (git show), `src/asy_webserver_service.py` | READ |
| A.U34.02, A.U34.07, A.U36.010, A.U36.035, A.U36.540 | THIRD_PARTY, CLAUDE.md, `src/config_manager.py`, BACKLOG | REF |
| A.U35.02, A.U35.05 | runner scripts, `tests_hardware/bench` | RUN |
| A.U35.03, .04, .37, .49, .51 | every test / module / instrument | B3 sweeps: findings pass A-C as deltas (OR106.a); their working files S-17 |
| A.U35.07, .08, .09, .11, .19, .20, .30, .35, .48 | inputs and product lines named as code under test | READ (the clusters' ledgers drop them with that reason) |
| A.U35.22, .23, .28, .41, .50 | `audit/b3/*.md` | S-17; `ci.yml` run records, `setup_toolchain.py` wall clock (A.U35.23) READ |
| A.U36.004 | `tests/test_digital_twin_sensortask_integration.py:98-100` | OBSOLETE (in `_start_webserver()`, which leaves with the HTTP tests, M.TWIN.144/A.U25.46) |
| A.U36.038 | per S-15 | S-15; `order.py` ART (scratchpad) |
| A.U36.501 | `js/**/*.js`, `html/**/*.html` | REF (config globs) |
| A.U36.515, A.U36.549, A.U8.23 | `definitions.json`, `tests_scripts/*.md`, `build/generated_src` | ART |
| A.U36.522 | SPECIFICATION.md | REF (B.13 quoted) |
| A.U36.537 | `src/asy_sgp40_driver.py` | REF (named in the SPEC M.3 heading) |
| A.U36.543 | `.claude/skills/integrate-module/SKILL.md` | S-13 |
| A.U37.04, A.U37.05 | `tests_hardware/README.md`, BACKLOG, UCL; `audit/actions/C.md`, `audit/b3/queue_c.md` | READ (close checks; the owed list's sources) |
| A.U37.15 | `legacy`; `pyproject.toml` | REF; NOEDIT ("only if an exclusion is there": grep finds none) |
| A.U6.20 | `buildgen/codegen.py` | S-11 |
| A.U6.26 | `src/asy_dns_client.py` / `asy_wifi_service.py` | "in the file U18 chooses": M.SRC_NET.043 carries the chosen one; the other is not edited |
| A.U7.19 | `tests_hardware/manual/__main__.py` | READ |
| A.U7.20 | `vitest.config.js` | OTHER (archive through `package.json` `pretest:coverage`, M.WEB.071; `reportsDirectory` stays) |
| A.U8.14 | `scripts/test.sh` | REF (inside the quoted `ci.yml:469` line) |
| A.U8.15 | `vitest.config.js` | S-12 |

## 7. Limits

- Fan-out per file was checked for A.U10.18, .31, .33, .34, .37, .38, .40, .43, .44, A.U20.33, A.U24.76; other
  whole-tree actions were traced at the level their Site names (a directory or a query). A.U10.35's 92 attributes and
  A.U10.44's generic names were not resolved per file; S-15 makes their sweep a step instead.
- The rename lists come from git-grep over the working tree at HEAD; generic names (`_run`, `read_loop`) over-match,
  so A.U10.44's per-file list is not given as evidence.
- The 305 no-ID Blast items were path-checked here and read by G1-G4; they were not all re-read.
