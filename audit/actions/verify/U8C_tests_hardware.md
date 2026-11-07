# A-L verify U8C_tests_hardware — U8C + U8C2, files under `tests_hardware/` (HEAD 741dfb5, finished at 3d0ba2e — no code change since a4766a9 outside `audit/`, U8/U8C/U8C2 unchanged)

Counts: 111 actions checked (A.U8C.44-A.U8C.119, A.U8C2.16-A.U8C2.49, the `tests_hardware/` part of A.U8C2.51) · OK 66 ·
FIX 45 (A.U8C.45, .48, .50, .54, .55, .57, .59-.63, .65-.68, .70-.74, .76, .82, .84, .87-.89, .91, .94-.99, .115;
A.U8C2.16, .21, .24, .35-.37, .40, .43, .46, .48, .49 — most through the four systematic items V.15, V.16, V.18, V.12)
· REJECT 0 · ADD 2 (V.07 one site, V.17 new action A.U8C.121; V.16 adds 15 sites to ten actions); 1,190 verdict rows
checked in context (997 U8C + 193 U8C2), 34 need a correction (verdict 6, ID 25, reason 3); findings
V.U8C_tests_hardware.01-18 (15 FIX, 3 ADD); ledger complete for `tests_hardware/`. Search: C.0.1 re-run identical (2,265;
997 here); G1-G15 re-run identical here (235 keys, 239 appearances: 193 rows + 42 dropped).

Per-file counts (rows U8C+U8C2 · non-OK items): every file OK except `bench/test_bus_concurrency_under_api_load.py`
77+5 · 3 (V.01, V.02, V.18), `bench/test_hotspot_role_reversal.py` 47+3 and `conftest.py` 12+3 · 1 (V.03),
`bench/test_network_resilience.py` 195+10 · 6 (V.03-V.06, V.08, V.18), `bench/test_uart_link_under_api_load.py` 21+0 · 2
(V.07, V.18), `bench/test_wifi_networking.py` 13+1 · 1 (V.08), `bench_control.py` 10+4 · 1 (V.09),
`device_scripts/bus_concurrency_same_device_scd30.py` 7+5 · 3 (V.10, V.11, V.16), `scd30_same_device_rw_concurrency.py`
7+1 · 3 (V.11, V.15, V.16), `scd30_plausibility_read.py` 5+3 · 1 (V.10), `uart_idle_poll_rate.py` 11+3 · 3 (V.10, V.12,
V.13), `isl29125_mechanism_envelope.py` 18+12 · 2 (V.12, V.15), `sgp40_fram_backup_restore.py` 4+0 · 1 (V.12),
`uart_link_under_concurrent_system_load.py` 18+5 · 1 (V.12), the two WiFi repros 15+4, 4+2 · 3 (V.14, V.15, V.18),
`heap_layout_after_full_boot_sequence.py` 9+2 · 2 (V.14, V.15), the device scripts named in V.15/V.16 (callers slot,
feed cadence), `flash/test_toolchain_flash_boot.py` 8+1, `manual/manual_bus_electrical.py` 2+2,
`manual/manual_persistence.py` 0+5, `device_scripts/isl29125_real_irq_edge.py` 8+9 · 1 each (V.18). Disagreement with
the `tests/` half: none on its readings; V.18 (message text restating a tagged value) is raised here only and applies
there too.

Scope: every hit-table row, action and ledger/register-fix/open-point item of `audit/actions/U8C.md` and
`audit/actions/U8C2.md` whose file is under `tests_hardware/` (93 files, 1,190 rows: 997 U8C + 193 U8C2; actions
A.U8C.44-A.U8C.119, A.U8C2.16-A.U8C2.49, the `tests_hardware/` entries of A.U8C2.51). `git diff --stat a4766a9 HEAD --
. ':!audit'` is empty, so both files' line numbers apply. Reading of the rule: as `verify/U8C_tests.md` (C.0.2 order,
U8C's readings, U8C2's readings E and Y). Scripts:
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/al/verifyU8C_hw/` (`c01.py` C.0.1,
`fam.py` G1-G15, `cmpfam.py` comparison, `parse.py`/`dossier.py` per-file row + action extraction), written from the
rule texts, not from the authors' or the `tests/` verifier's scripts.

## Completeness (check 1)

- **C.0.1** (own `c01.py`, both trees): 2,265 hits, identical key for key (kind, file, literal line, literal) to U8C's
  table; kinds const 290, const-c 253, call 599, kw 915, param 60, assert 131, deadline 17. `tests_hardware/` share:
  997 (kw 445, call 262, const 173, const-c 86, param 20, deadline 8, assert 3); every line cited is the literal's own.
- **G1-G15** (own `fam.py`, U8C2's rules as written, callee index over `tests/`, `tests_hardware/`, `src/`,
  `digital_twin/`): all-tree family totals equal U8C2's except G15 23 vs 25 (the two `"0"` strings in
  `tests/test_config_manager.py`, already V.U8C_tests.01). `tests_hardware/` share: 235 (file, line, literal) keys, 239
  family appearances (G1 3, G2 60, G3 1, G4 8, G5 7, G6 35, G6s 21, G7 11, G9 42, G10 31, G11 4, G12 1, G14 13, G15 2),
  identical family for family to U8C2's table + its "dropped" list (193 table rows + 42 dropped keys); no zero-valued G15
  string in `tests_hardware/`; no U8C2 row repeats a U8C key; G14 gives the same 13 with or without G4's assert-name
  exclusion. Every line is the literal's own.

## Per-file results

Per file: rows (U8C + U8C2) opened in context · actions checked · non-OK items. A file with no finding line is OK in
every verdict, ID, mirror and action slot.

- `bench/dns_probe.py` 2+3 · A.U8C.44 · OK.
- `bench/test_bus_concurrency_under_api_load.py` 77+5 · A.U8C.45, A.U8C2.16 · 2 FIX:
  - V.U8C_tests_hardware.01 | U8C row `:297` kw 20.0 and A.U8C.45 | FIX | `:297` is `wait_until(_synced, timeout_s=20.0,
    poll_interval_s=1.0, description="NTP resynced …")` — the NTP-resync deadline. The call row of the same literal says
    `ntp_resync_timeout_s`, the kw row says `degraded_fetch_timeout_s` (a per-request HTTP timeout it is not); A.U8C.45
    then lists `:297` under both IDs and its Change rewrites the one literal into both `_DEGRADED_FETCH_TIMEOUT_S` and
    `_NTP_RESYNC_TIMEOUT_S` | row `:297` kw 20.0 → `tuned | \`l4.bus_concurrency_under_api_load_ntp_resync_timeout_s\` —
    deadline for NTP to resync after the transient outage`; A.U8C.45 Site `degraded_fetch_timeout_s` → ":175, :186, :255,
    :266, :324, :335 (20.0)"; Change: "each literal at :175, :186, :255, :266, :324, :335 becomes `_DEGRADED_FETCH_TIMEOUT_S`".
  - V.U8C_tests_hardware.02 | A.U8C2.16 Change | FIX | the retry count 3 at `:46` (`for attempt in range(3)`) has a
    derived partner at `:50` (`if attempt == 2 or not http_client.is_ceiling_close(exc): raise` — "last attempt"), an
    `==` literal outside every family (U8C2 blind spot). Tagging `:46` alone leaves a hidden second copy: raised, the
    loop still gives up at the third attempt; lowered to 2, the last failure falls through to `AssertionError("unreachable")`
    instead of re-raising
    | append to the Change: "the literal at :50 (`attempt == 2`) becomes `attempt == _CEILING_RETRY_ATTEMPTS - 1`
    (derived, untagged)"; Site add "derived, untagged: :50 (2)".
- `bench/test_end_to_end_timing.py` 52+2 · A.U8C.46, A.U8C2.17 · OK.
- `bench/test_heap_under_connection_ceiling.py` 10+6 · A.U8C.47, A.U8C2.18 · OK (`:25` mirror is A.U8.05's own; `:27-40`
  are A.U8.05's IDs; Blast's `tests_scripts/test_request_timeout_ceiling.py:125-133` reads only `_DRIP_INTERVAL_S`/`_RECYCLE_S`).
- `bench/test_hotspot_role_reversal.py` 47+3 and `conftest.py` 12+3 · A.U8C.48, A.U8C2.19, A.U8C.57, A.U8C2.25 · 1 FIX:
  - V.U8C_tests_hardware.03 | U8C rows `test_hotspot_role_reversal.py:33, :38 (×4), :80 (×4)`, `conftest.py:183 (×2), :184 (×2),
    :187`, `test_network_resilience.py:563`; A.U8C.48, A.U8C.50, A.U8C.57 | FIX | the three shared IDs take the stem
    `conftest`, but U8C's own cross-file reading gives a shared ID "the stem of the file that holds the original". The
    original is `test_hotspot_role_reversal.py`: `timeout_s=45.0` there since `33719a4` (2026-09-01), the
    `is_ssid_visible` scan wait since `a45878a` (2026-09-02); `conftest.py` gained both in `c9e11fd` (2026-09-04), whose
    message says it "reuses test_hotspot_role_reversal.py's own proven stage-6 mechanism" (`git log -S`) | rename in
    every row, Site, Change tag and Blast: `l4.conftest_hotspot_scan_timeout_s` →
    `l4.hotspot_role_reversal_hotspot_scan_timeout_s`, `l4.conftest_hotspot_scan_poll_s` →
    `l4.hotspot_role_reversal_hotspot_scan_poll_s`, `l4.conftest_join_hotspot_timeout_s` →
    `l4.hotspot_role_reversal_join_hotspot_timeout_s`; row reasons "the same … as conftest.py:18x (shared ID)" in
    `test_hotspot_role_reversal.py` become "(shared ID; original here, copied into conftest.py:183-187)"; A.U8C.57
    Depends keeps A.U8C.48 (the original's action creates the rows).
- `bench/test_memory_stress_bench.py` 6+5 · A.U8C.49, A.U8C2.20 · OK.
- `bench/test_network_resilience.py` 195+10 · A.U8C.50, A.U8C2.21 · 3 FIX (plus V.03's `:563`):
  - V.U8C_tests_hardware.04 | A.U8C.50 Blast | FIX | "tests this file only" is wrong: `tests_scripts/test_request_timeout_ceiling.py:295-313`
    (`test_the_bench_ceiling_test_keeps_its_held_set_inside_the_per_call_timeout`) walks
    `test_connections_at_and_above_the_real_socket_limit_degrade_cleanly` for `extra.settimeout(<numeric ast.Constant>)`
    and asserts `read_timeouts and read_timeouts[-1] + 1.0 < per_call_timeout_s`. A.U8C.50 turns `:656` (10.0) into
    `_RAW_SOCKET_TIMEOUT_S` and `:662` (1.0) into `_ADMITTED_SILENCE_S`, so `read_timeouts` is empty and the test fails;
    its hardcoded `+ 1.0` is the `:673` retry sleep, which becomes `_SLOT_RELEASE_WAIT_S` | Blast tests: "existing that
    change: `tests_scripts/test_request_timeout_ceiling.py:295-313` — resolve a `Name` argument of `extra.settimeout`
    through `_module_constant()` (`:48`) and read the retry sleep as `_module_constant(…, "_SLOT_RELEASE_WAIT_S")`
    instead of the literal `1.0` (assertion message likewise); without it the test fails once `:656`/`:662`/`:673` are
    names". A.U8C2.21's Blast sentence "leaves all three intact" gains "(A.U8C.50's constants do not — see there)".
  - V.U8C_tests_hardware.05 | A.U8C2.21 Change | FIX | two tagged retry counts keep a derived hard-coded partner:
    `:561` `range(3)` ↔ `:566` `if attempt == 2: raise`; `:651` `range(3)` ↔ `:672` `if attempt < 2:` (U8C2's own row
    `:672` says "last attempt index (attempts − 1)") and the message at `:674` ("… was not rejected after 3 attempts")
    | append to the Change: "derived, untagged: :566 `attempt == 2` → `attempt == _JOIN_ATTEMPTS - 1`; :672 `attempt < 2`
    → `attempt < _OVER_CEILING_ATTEMPTS - 1`; :674 message '… after 3 attempts' → '… after {_OVER_CEILING_ATTEMPTS}
    attempts'"; Site add "derived, untagged: :566 (2), :672 (2), :674 (message)".
  - V.U8C_tests_hardware.06 | U8C row `:275` (call 8.0) and A.U8C.50 | FIX | `time.sleep(8.0)  # longer than the real 5s
    fetch timeout, so this attempt genuinely fails` holds UDP 123 blocked until the triggered NTP attempt has failed — a
    fixed wait for a state, and the state is observable without touching the property (the same test's `:283` notes the
    failed attempt "did legitimately log something"; `_ntp_error_log_contains()` at `:491` already polls exactly that log
    over HTTP, which the block does not affect). C.0.2 "Deferred" / U8C's reading: a fixed readiness sleep in an `l4.`
    file is deferred U26, and no G7/R23 exception (a probe would disturb the property) applies | row → `deferred U26 |
    if kept: \`l4.network_resilience_ntp_fail_wait_s\` — fixed wait for the blocked NTP attempt to fail (a poll of the NTP
    error log could replace it); Dependant of ntp.fetch_timeout_ms`; A.U8C.50: drop `_NTP_FAIL_WAIT_S` and `:275` from
    Site/Change, add ":275 (8.0) deferred U26" to Site; U8C "Deferred sites" 14 → 15 U26, Status tuned 1505 → 1504,
    deferred U26 14 → 15, new IDs 576 → 575, provisional IDs 20 → 21.
- `bench/test_rest_endpoints_over_sta.py` 20+1 · A.U8C.51 · OK.
- `bench/test_sensor_config_push_over_real_hardware.py` 25+1 · A.U8C.52, A.U8C2.22 · OK (`:132` "Dependant of
  notify.loop_tick_s": see V.U8C_tests_hardware.17).
- `bench/test_serving_heap_at_default_gc.py` 11+1 · A.U8C.53 · OK (`:29` shares `l4.network_resilience_slot_release_wait_s`
  by C.0.2's "same purpose across files … shares one ID"; `:30` Dependant: V.U8C_tests_hardware.17).
- `bench/test_uart_link_under_api_load.py` 21+0 · A.U8C.54 · 1 ADD:
  - V.U8C_tests_hardware.07 | A.U8C.54 | ADD | `:177` `threads = [threading.Thread(target=burst_worker) for _ in range(6)]`
    — the size of the "deliberate overload" burst of `test_an_api_overload_does_not_corrupt_the_link_or_the_reverse`, a
    load volume on real hardware (U8C2's reading "load volume … at L2-L4 … tuned", like `:24`/`:25` here). No family
    reaches it: G10 reads `for` statements only and a comprehension's `range()` is outside every rule (the one such site
    in `tests_hardware/`: `grep -rnE "for [a-z_]+ in range\([0-9]+\)\]" tests_hardware`). U8C2's "Known blind spots"
    does not name it | A.U8C.54 Site add `l4.uart_link_under_api_load_burst_workers` :177 (6); Change add
    "`_BURST_WORKERS = 6` (new, module level) tagged `# @tunable l4.uart_link_under_api_load_burst_workers = 6`; the literal
    at :177 becomes `_BURST_WORKERS`"; U8C2 "Known blind spots" add "a `range(N)` inside a comprehension (one site,
    classified in U8C's A.U8C.54)".
- `bench/test_wifi_networking.py` 13+1 · A.U8C.55, A.U8C2.23 · 1 FIX:
  - V.U8C_tests_hardware.08 | U8C rows `test_wifi_networking.py:88`, `test_network_resilience.py:304, :335`; A.U8C.50,
    A.U8C.55 | FIX | the shared 90 s log window takes the stem `network_resilience`, but the original is
    `test_wifi_networking.py:88` (`33719a4`, 2026-09-01 11:26; `test_network_resilience.py` copied the line and its comment
    in `aa008e9`, 13:25 the same day, whose header names "test_wifi_networking.py's own
    test_real_ntp_handles_a_genuinely_unreachable_server_…") | rename `l4.network_resilience_rogue_tail_s` →
    `l4.wifi_networking_ntp_fault_tail_s` in the three rows, both Sites, both Change tags; row `:88` reason "(shared ID;
    original here, copied into test_network_resilience.py:304, :335)"; A.U8C.50 Depends add A.U8C.55; A.U8C.55 Depends
    drop A.U8C.50.
- `bench_control.py` 10+4 · A.U8C.56, A.U8C2.24 · 1 FIX:
  - V.U8C_tests_hardware.09 | A.U8C2.24 Blast | FIX | "`wait_for_link_local_teardown()` by the bench bridge helpers (grep)"
    — it has no caller: `grep -rn wait_for_link_local_teardown tests_hardware tests_scripts scripts toolchain` finds only
    the definition (`bench_control.py:277`), as RF309/G7/R23 state ("has no caller (grep: definition only)") | Blast
    callers: "`start_udp_source_capture()`/`read_captured_udp_source_port()` used by
    `tests_hardware/bench/test_network_resilience.py:388-391`; `wait_for_link_local_teardown()` has no caller (definition
    only; U26 removes it or makes it a poll, G7/R23)". The two deferrals (`:277`, `:281`) are right: G7/R23's State names
    this exact sleep for U26.
- `device_scripts/allocation_need_per_source.py` 16+2 · — · OK.
- `device_scripts/bmp3xx_plausibility_read.py` 2+1, `bmp3xx_same_device_rw_concurrency.py` 11+0,
  `bus_concurrency_cross_device_scd30_sgp40.py` 4+1, `bus_concurrency_isl29125_write_vs_siblings.py` 10+2,
  `bus_concurrency_scd30_write_vs_siblings.py` 7+1 (`:70` deferral right: a readiness sleep a `completed`-counter poll
  replaces), `bus_deinit_is_a_noop_on_real_hardware.py` 1+0, `bus_topology_autodetect_and_hazard_sweep.py` 18+7 ·
  A.U8C.58-61, A.U8C.63, A.U8C.64, A.U8C2.26-28 · OK apart from the callers slot (V.U8C_tests_hardware.15).
- `device_scripts/bus_concurrency_same_device_scd30.py` 7+5 and `scd30_same_device_rw_concurrency.py` 7+1 · A.U8C.62,
  A.U8C.84, A.U8C2.37 · 2 FIX (`:64` deferral right):
  - V.U8C_tests_hardware.10 | U8C2 row `bus_concurrency_same_device_scd30.py:36` and A.U8C.62 (same defect at
    `scd30_plausibility_read.py:28`/A.U8C.82/A.U8C2.36 and `uart_idle_poll_rate.py:66`/A.U8C.94/A.U8C2.40) | FIX | the
    U8C2 rows say the divisor is "already covered: U8C's `:39` row makes this divisor use the constant; no new work", and
    U8C2's register fix says the sibling rows "already name their divisors" — but naming is not changing: A.U8C.62's
    Change rewrites only `:39`, A.U8C.82's only `:30, :41`, A.U8C.94's only `:68`. `int(_SETTLE_S / 0.5)` (`:36`),
    `int(_SETTLE_S / 0.5)` (`scd30_plausibility_read.py:28`) and `SAMPLE_MS // 250` (`uart_idle_poll_rate.py:66`) keep
    their literal, so a changed step would silently desynchronise the loop count from the step (U8C2 treated the
    identical `scd30_same_device_rw_concurrency.py:32` as a new site, A.U8C2.37 — the three siblings must match it) |
    A.U8C.62 Site `…_settle_step_s` → ":36, :39 (0.5)", Change "each literal at :36, :39 becomes `_SETTLE_STEP_S`";
    A.U8C.82 Site `l3.scd30_plausibility_read_step_s` → ":28, :30, :41 (0.5)", Change "each literal at :28, :30, :41
    becomes `_STEP_S`"; A.U8C.94 Site `l3.uart_idle_poll_rate_sample_step_ms` → ":66, :68 (250)", Change "each literal at
    :66, :68 becomes `_SAMPLE_STEP_MS`"; the three U8C2 rows' reason "already covered … no new work" → "divisor of the
    loop count; replaced by the step constant in A.U8C.62 / A.U8C.82 / A.U8C.94"; A.U8C2.36 and A.U8C2.40 drop their
    "already covered … no new work" clause for `:28`/`:66` and the Site entries move to the U8C actions.
  - V.U8C_tests_hardware.11 | U8C rows `bus_concurrency_same_device_scd30.py:21, :39`, `scd30_same_device_rw_concurrency.py:20,
    :35`, U8C2 rows `:36`, `:32`; A.U8C.62, A.U8C.84, A.U8C2.37 | FIX | the shared settle IDs take the stem
    `bus_concurrency_same_device_scd30`, but the original is `scd30_same_device_rw_concurrency.py` (`_SETTLE_S = 12.0` and
    the `/ 0.5` loop since `8905d2b`, 2026-09-14); `bus_concurrency_same_device_scd30.py` gained the copy in `2abebb0`
    (2026-09-19) and says so ("scd30_same_device_rw_concurrency.py carries the same constant", `:20`) — U8C's own reading
    gives the shared ID the original's stem | rename in all rows, Sites and Change tags:
    `l3.bus_concurrency_same_device_scd30_settle_s` → `l3.scd30_same_device_rw_concurrency_settle_s`,
    `l3.bus_concurrency_same_device_scd30_settle_step_s` → `l3.scd30_same_device_rw_concurrency_settle_step_s`; A.U8C.62
    Depends add A.U8C.84, A.U8C.84 Depends drop A.U8C.62.
- `device_scripts/fram_busy_status_lockout.py` 1+0, `fram_cs_hijack_fault_injection_and_recovery.py` 5+0,
  `fram_error_log_reset_during_boot_window.py` 2+0, `fram_error_log_reset_race_seed_and_race.py` 4+0,
  `fram_error_log_reset_race_verify.py` 5+0, `fram_error_log_roundtrip.py` 2+0, `fram_manager_roundtrip.py` 1+0,
  `fram_pause_unpause_and_gating.py` 5+5, `fram_reset_race_during_write_seed_and_race.py` 2+0,
  `fram_reset_race_during_write_verify_recovery.py` 1+0, `fram_same_device_rw_concurrency.py` 6+0,
  `fram_write_protect_roundtrip.py` 1+0 · A.U8C.65-70, A.U8C2.29 · OK apart from V.15 (`HISTORY_LENGTH = 10` "contract"
  in the seed/verify pair is right — both scripts must address the same chunk; `:31` `min(remaining, 1.0)`: V.16).
- `device_scripts/heap_headroom_after_full_system_build.py` 6+1, `heap_layout_after_full_boot_sequence.py` 9+2,
  `heap_under_connection_ceiling.py` 3+1, `serving_at_default_gc.py` 8+2 · A.U8C.71-73, A.U8C.86, A.U8C2.30 · OK apart
  from V.15 and V.14 (A.U8C.72's Depends) (`tests_scripts/test_digital_twin_boot_contiguity.py:259-300` reads the three mirrored bounds with
  `^NAME = (-?\d+)$`: tag lines above the assignment leave it intact; `heap_headroom` is the original of the shared probe
  IDs, `6cf82a1` 2026-09-11 against `7aba427` 2026-09-18).
- `device_scripts/isl29125_cross_device_concurrency.py` 6+2, `isl29125_lighting_scenarios.py` 15+13,
  `isl29125_plausibility_read.py` 6+4, `isl29125_real_irq_edge.py` 8+9, `isl29125_same_device_rw_concurrency.py` 12+1,
  `isl29125_mock_conformance_probe.py` 4+24 · A.U8C.74, A.U8C.75, A.U8C.77-80, A.U8C2.31, A.U8C2.33-35 · OK (every
  deferral checked: the conformance probe's `settle()` is a real `sleep_ms`, `:53-59`, and each deferred settle precedes a
  read a status/`TS` poll could gate; the `:178`/`:182` hold windows and `real_irq_edge.py:34` are observation windows;
  `:335` mirror of `isl29125.periodic_only_warn_at` is right, `_PERIODIC_ONLY_WARN_AT = const(5)` at
  `src/asy_isl29125_driver.py:109`), apart from V.15.
- `device_scripts/isl29125_mechanism_envelope.py` 18+12 · A.U8C.76, A.U8C2.32 · 1 FIX (V.U8C_tests_hardware.12, `:24`).
- `device_scripts/reboot_fallback_starves_the_watchdog.py` 3+1, `reboot_persist_read.py` 2+0, `reboot_persist_write.py`
  2+0, `watchdog_starvation_reset.py` 1+0 · A.U8C.81, A.U8C.97 · OK apart from V.15 (`l3.starvation_wdt_ms` is A.U8.08's row).
- `device_scripts/scd30_plausibility_read.py` 5+3 · A.U8C.82, A.U8C2.36 · FIX in V.10 (`:28`).
- `device_scripts/scd30_real_irq_edge.py` 4+2, `scheduler_saturation_drop.py` 3+0, `sgp40_general_call_reset_hazard.py`
  5+2, `sgp40_voc_algorithm_quality.py` 5+1, `system_debug_level_raise_for_boot_log_check.py` 3+0,
  `system_debug_level_restore_after_boot_log_check.py` 2+0, `system_service_restarts_a_real_dead_task.py` 2+2,
  `timer_alarm_pool_exhaustion.py` 1+2 · A.U8C.83, A.U8C.85, A.U8C.88-90, A.U8C2.38 · OK (`N_TIMERS`/`N_QUALITY_SAMPLES`
  are outside C.0.1 by its `_?N_[A-Z]` exclusion; the dead-task 4 × 0.9 s window is an observation window bounded above by
  the reboot threshold, rightly tuned).
- `device_scripts/sgp40_fram_backup_restore.py` 4+0 · A.U8C.87 · 1 FIX (V.12, `:15`, `:16`).
- `device_scripts/uart_crossover_exchange.py` 9+0, `uart_crossover_recovery.py` 9+1, `uart_driver_read_never_blocks_the_loop.py`
  11+3, `uart_read_never_blocks_the_loop.py` 7+3 · A.U8C.91-93, A.U8C.96, A.U8C2.39, A.U8C2.42 · OK apart from V.15
  (`PAYLOAD_SIZE`/`TIMEOUT_MS`/`BAUDRATE` "contract" matches A.U8.06's exclusion; the `dev.uart_*` mirrors are named
  constants; `:106` deferral right).
- `device_scripts/uart_idle_poll_rate.py` 11+3 · A.U8C.94, A.U8C2.40 · FIX in V.10 (`:66`), V.12 (`:78`) and 1 FIX:
  - V.U8C_tests_hardware.13 | A.U8C2.40 Change | FIX | `:100` holds the factor twice (`idle > _EXPECTED_IDLE_ROUNDS * 2
    or idle < _EXPECTED_IDLE_ROUNDS // 2`); the row's own reason is "the ×2 / ÷2 band", but the Change says "the literal at
    :100 becomes `_EXPECTED_ROUNDS_FACTOR`" (one key per C.0.1/U8C2 keying, two literals) | "both literals at :100 become
    `_EXPECTED_ROUNDS_FACTOR`" (as V.U8C_tests.05 did for two keyword literals on one line).
- `device_scripts/uart_link_under_concurrent_system_load.py` 18+5 · A.U8C.95, A.U8C2.41 · FIX in V.12 (`:191`); the
  mirror-by-reading of `:24-26` (U8C open point 3) is right: the values build the same pair as `devices/dev.toml`.
- `device_scripts/wifi_reconnect_after_failed_attempts_repro.py` 15+4 and `wifi_service_reconnect_repro.py` 4+2 · A.U8C.98,
  A.U8C.99, A.U8C2.43 · 1 FIX:
  - V.U8C_tests_hardware.14 | A.U8C.98, A.U8C.99, A.U8C2.43 Depends | FIX | both scripts are orphans (no runner:
    `grep` finds no `run_isolated`/`DEVICE_SCRIPTS` reference) and G1/R09's State gives U26 their verdict: "orphan
    verdicts: `wifi_service_reconnect_repro.py` and `wifi_reconnect_after_failed_attempts_repro.py` are retire
    candidates" (`audit/pass2/G1.md:83`). Tagging them before that verdict can create Part N rows and sites for files U26
    deletes | Depends of all three add "U26 (G1/R09 orphan verdict — if the script is retired this action lapses and its
    rows and mirror sites are not created)"; A.U8C.99 also gains U26 (it has none today). The same holds for
    `heap_layout_after_full_boot_sequence.py` (A.U8C.72), which `PROJECT_AUDIT_PLAN.md:3244` proposes to retire under
    HW.S16/MEM: add "U26/U30 (orphan verdict, plan B.3)" to A.U8C.72's Depends.
- `error_log_helpers.py` 2+0 · A.U8C.100 · OK (`:14` is A.U8.05's `l4.reset_errors_timeout_s`; the tag line leaves
  `tests_scripts/test_request_timeout_ceiling.py:86-97`, which reads `_RESET_ERRORS_TIMEOUT_S`, intact).
- `flash/conftest.py` 1+0, `flash/test_bus_concurrency.py` 19+0, `flash/test_bus_electrical_timing.py` 5+3,
  `flash/test_fram_storage.py` 14+0, `flash/test_memory_stress.py` 2+1, `flash/test_reboot_persistence.py` 9+0,
  `flash/test_sensor_accuracy.py` 7+0, `flash/test_task_supervisor.py` 1+0, `flash/test_uart_crossover.py` 6+0,
  `flash/test_watchdog_starvation.py` 29+0 · A.U8C.101-108, A.U8C.110, A.U8C.111, A.U8C2.44, A.U8C2.45 · OK apart from
  V.17 (Dependants) — every host `run_isolated(timeout_s=…)` checked against its script's own internal bound; `:51`
  `_WDT_RESET = 3` is `machine.WDT_RESET` (identifier); U8C2's register fix to search-gap 7 (`:119`, `:122`) is right.
- `flash/test_toolchain_flash_boot.py` 8+1 and `manual/manual_toolchain.py` 2+0 · A.U8C.109, A.U8C.117, A.U8C2.46 · OK
  apart from V.18 (`test_toolchain_flash_boot.py` is the original of the shared IDs: `33719a4` against `f843c3d`).
- `harness.py` 34+3 · A.U8C.112, A.U8C2.47 · OK (both deferrals, `:202`/`:204`, are readiness sleeps an
  `is_device_present()` poll replaces; the six `l4.ceiling_*` defaults are A.U8.05's; `harness.py:444, :458`
  `WDT(timeout=8000)` sit inside `mpremote exec` strings, so no C.0.1/G-family hit — A.U8.08 owns them).
- `heap_map.py` 1+2, `ntp_probe.py` 1+0, `manual/runner.py` 1+1 · — · OK.
- `http_client.py` 1+0, `isl29125_conformance.py` 1+0, `rogue_udp_responder.py` 2+0, `soak_tiers.py` 4+0,
  `manual/manual_sensor_accuracy.py` 5+0 · A.U8C.113, A.U8C.114, A.U8C.116, A.U8C.118, A.U8C.119 · OK (the three stacked
  tags above `soak_tiers.py:7` each find their literal as a whole token on that line — `6` in `6 * 3600.0`, not inside
  `60.0`/`600.0` — so A.U8.02's check (2) holds).
- `manual/manual_bus_electrical.py` 2+2, `manual/manual_persistence.py` 0+5 · A.U8C.115, A.U8C2.48, A.U8C2.49 · FIX in V.18.

## Cross-file findings

- V.U8C_tests_hardware.12 | U8C rows `device_scripts/isl29125_mechanism_envelope.py:24`,
  `device_scripts/sgp40_fram_backup_restore.py:15, :16`, `device_scripts/uart_idle_poll_rate.py:78`,
  `device_scripts/uart_link_under_concurrent_system_load.py:191`; A.U8C.76, A.U8C.87, A.U8C.94, A.U8C.95 | FIX | five
  fixed waits for a state the script can observe without disturbing the property, classified tuned, while U8C/U8C2
  defer the same kind (C.0.2 "Deferred"; G7/R23 Req "waits for readiness by polling for the exact expected state …; a fixed
  sleep is used only where a probe would disturb the property"): `SETTLE_S = 4.5` (`:24`) is waited out in `_hold()`
  (`:79-82`) before every level — the same settle-before-reading as the deferred `:209`, and `_fresh_sample()` (`:44-53`)
  already polls for a new `TS`; `BACKUP_WAIT_S = 75.0`/`RESTORE_WAIT_S = 10.0` run the reader for a fixed time
  (`_run_until_cancelled()`, `:38-49`) and only then read `get_mem_status()` (`:84`, `:119`), an in-memory read a poll can
  make every feed step; `uart_idle_poll_rate.py:78` and `uart_link_under_concurrent_system_load.py:191` sleep after
  `cancel()` for the tasks to unwind — `listener.done()` is already polled at `:71-75`, and awaiting the cancelled tasks is
  the direct form. (`network_resilience.py:275` is the sixth, V.06.) The observation windows U8C/U8C2 kept tuned —
  `isl29125_mock_conformance_probe.py:178, :182`, `isl29125_real_irq_edge.py:34`, `network_resilience.py:400`, the
  slot-release and admit waits, `heap_layout_…:28`, the dead-task window — stay tuned | the five rows → `deferred U26 |
  if kept: <same ID> — fixed wait for <state>; a poll of <observable> could replace it`; A.U8C.76, A.U8C.87, A.U8C.94,
  A.U8C.95: move each site from the tag list to "deferred U26: :<line>" and drop its constant/tag from the Change (the
  constants at `:24`, `:15`, `:16` stay untagged); Depends add U26 to A.U8C.87 and A.U8C.95; U8C Status and "Deferred
  sites": deferred U26 14 → 20 with V.06, tuned 1505 → 1499, new tuned IDs 576 → 570, provisional IDs 20 → 26; the rows
  `flash/test_sensor_accuracy.py:61`, `flash/test_fram_storage.py:44` keep their Dependant text against the provisional IDs.
- V.U8C_tests_hardware.15 | the callers slot of A.U8C.61, .65, .66, .68, .71, .72, .73, .76, .84, .89, .91, .96, .97, .99
  and A.U8C2.37 | FIX | "callers run on the board by …" lists files that only mention the script's name — a sibling
  device script's comment or docstring (`bus_concurrency_scd30_write_vs_siblings.py:1`,
  `fram_error_log_reset_race_verify.py:2`, `fram_error_log_reset_race_seed_and_race.py:62`,
  `heap_layout_after_full_boot_sequence.py:14, :17`, `bus_concurrency_cross_device_scd30_sgp40.py:25`,
  `bus_concurrency_same_device_scd30.py:20, :31`, `sgp40_general_call_reset_hazard.py:51`,
  `uart_driver_read_never_blocks_the_loop.py:25`, `reboot_fallback_starves_the_watchdog.py:12`), a comment in another
  tier (`tests/test_digital_twin_bus_hazard_concurrency.py:235`, `tests/test_asy_uart_link_driver.py:202`,
  `bench/test_bus_concurrency_under_api_load.py:21`), or a `tests_scripts/` static reader; A.U8C.73 even lists
  `tests_scripts/test_bench_restores_serving.py`/`test_request_timeout_ceiling.py`, which name the *bench* file
  `test_heap_under_connection_ceiling.py` (a substring match), and omits the real runner | each slot names only the
  real runner (the file passing the script to `run_isolated`/`run_isolated_expect_reset`, grep
  `[\"/]<name>.py\"` in `tests_hardware/`): A.U8C.61, .65, .96 → `tests_hardware/flash/test_bus_concurrency.py`
  (`test_uart_crossover.py` for .96), A.U8C.66, .68 → `flash/test_fram_storage.py:60` /
  `flash/test_bus_concurrency.py:131`, A.U8C.71 → `flash/test_memory_stress.py:35`, A.U8C.72 → "no runner (orphan)",
  A.U8C.73 → `bench/test_heap_under_connection_ceiling.py:121`, A.U8C.76, .89 → `flash/test_sensor_accuracy.py`,
  A.U8C.84, A.U8C2.37 → `flash/conftest.py:32`, A.U8C.91 → `flash/test_uart_crossover.py`, A.U8C.97 →
  `flash/test_watchdog_starvation.py:23`, A.U8C.99 → "no runner (orphan, run by hand)"; the static readers move to the
  tests slot as "unaffected" (`test_device_script_gc_threshold.py`, `test_heap_map_parser.py:198-209`,
  `test_device_script_config_flush.py`, `test_digital_twin_boot_contiguity.py:259-300` — the last reads
  `_STARTER_LOOP_TIMEOUT_MS`/`_STARTER_LOOP_GRACE_MS`/`_TIMERS_TIMEOUT_S` by `^NAME = (-?\d+)$`, which the tag lines
  above leave intact); sibling scripts that share an ID stay in the "shared IDs also sited in" clause only.
- V.U8C_tests_hardware.16 | U8C/U8C2 search rules and A.U8C.59-63, .67, .70, .74, .84, .88 | ADD | the WDT feed cadence of
  the device scripts is a real-clock budget (N iterations × the loop's real per-iteration time must stay under
  `wdt.timeout_ms`, or the board resets mid-run) that no rule reaches: `if i % N == 0: wdt.feed()` is an `==` compare of
  a `%` operand (G6 reads `+ - * / //` only) and `step = min(remaining, 1.0)` has no timing name in its other argument
  (G11). Sites (`grep -rnE "% [0-9]+ == 0" tests_hardware`): `bmp3xx_same_device_rw_concurrency.py:43` (5),
  `bus_concurrency_cross_device_scd30_sgp40.py:44` (10), `bus_concurrency_isl29125_write_vs_siblings.py:52, :68` (10),
  `bus_concurrency_same_device_scd30.py:63` (10), `:78` (5), `bus_concurrency_scd30_write_vs_siblings.py:50, :64` (10),
  `fram_same_device_rw_concurrency.py:49` (5), `isl29125_cross_device_concurrency.py:73, :87` (10),
  `scd30_same_device_rw_concurrency.py:59` (10), `sgp40_general_call_reset_hazard.py:84, :99` (10); and
  `fram_pause_unpause_and_gating.py:31` (1.0, `sleep_fed()`'s feed step) | tuned, Dependant of `wdt.timeout_ms`: per
  file one constant per distinct value, `_WDT_FEED_EVERY = N` tagged `# @tunable l3.<stem>_wdt_feed_every = N`
  (`bus_concurrency_same_device_scd30.py`: `_READER_WDT_FEED_EVERY = 10`, `_SNAPSHOT_WDT_FEED_EVERY = 5`;
  `fram_pause_unpause_and_gating.py`: `_FEED_STEP_S = 1.0`, `l3.fram_pause_unpause_and_gating_feed_step_s`), each
  `i % N` → `i % _WDT_FEED_EVERY`; added to the listed file actions; `wdt.timeout_ms`'s Dependants list them (V.17);
  U8C2 "Known blind spots" add "a `%` operand compared with `==` (WDT feed cadence) and a `min()`/`max()` clamp whose
  other argument carries no timing name".
- V.U8C_tests_hardware.17 | U8C (the `tests_hardware/` part) | ADD | the counterpart of V.U8C_tests.09: 20 tuned
  `tests_hardware/` rows state "Dependant of …" (or "must stay below/under …"), and only three reach Part N through
  A.U8C2.51 (`network_resilience.py:957`, `l3.system_service_restarts_a_real_dead_task_wait_rounds`,
  `l4.bench_control_udp_capture_timeout_s`) | new action:

  ### A.U8C.121 List the tuned `tests_hardware/` sites under their source rows' Dependants
  - **Why**: G4/R54 (as A.U8C.01); U8 N.1 "Dependants" (A.U8.01); the U8C hit-table rows below each state the relation
  - **Site**: SPECIFICATION.md Part N (created by A.U8.01), the rows below
  - **Change**: add to Dependants — `dns_server.recv_backoff_max_s` (A.U8.11): `l4.hotspot_role_reversal_dns_recovery_timeout_s`
    (`tests_hardware/bench/test_hotspot_role_reversal.py:258`, the post-flood query deadline); `wifi.sta_retry_after_loss_s`
    (A.U8.10): `l4.network_resilience_flap_step_s` (`bench/test_network_resilience.py:80, :82`,
    `bench/test_bus_concurrency_under_api_load.py:348, :350`, short against the 60 s retry); `ntp.fetch_timeout_ms` (A.U8.09):
    `l4.network_resilience_ntp_fail_wait_s` (`:275`, longer than the 5 s fetch; deferred U26 by V.06 — listed if kept);
    `web.per_call_timeout_s` (A.U8.04): `l4.network_resilience_admitted_silence_s` (`:662`, plus the 1 s retry sleep, under
    the per-call timeout — pinned by `tests_scripts/test_request_timeout_ceiling.py:295-313`); `web.outer_cap_s` (A.U8.04):
    `l4.network_resilience_slowloris_socket_timeout_s` (`:950`, above the cap); `notify.loop_tick_s` (A.U8.12):
    `l4.sensor_config_push_over_real_hardware_override_poll_s` and `_override_poll_tries`
    (`bench/test_sensor_config_push_over_real_hardware.py:131, :132`, ten ~1 s ticks over a 3 s countdown);
    `wdt.timeout_ms` (A.U8.08): `l3.sgp40_fram_backup_restore_wdt_feed_interval_s` (`device_scripts/sgp40_fram_backup_restore.py:17`,
    `sgp40_voc_algorithm_quality.py:19`) and the feed cadences of V.16; `l3.starvation_wdt_ms` (A.U8.08):
    `l3.reboot_fallback_starves_the_watchdog_feed_attempt_ms` (`:49`), `l3.watchdog_starvation_reset_elapsed_max_s`
    (`flash/test_watchdog_starvation.py:29`), `l3.watchdog_starvation_fallback_elapsed_max_s` (`:68`);
    `system.task_check_s`, `system.task_fail_increment`, `system.task_fail_max` (A.U8.08, A.U8.12):
    `l3.system_service_restarts_a_real_dead_task_watch_step_s` (`:38`); `l3.serving_at_default_gc_quiet_to_leave`
    (A.U8C.86): `l4.serving_heap_at_default_gc_level_gap_s` (`bench/test_serving_heap_at_default_gc.py:30`, must stay
    below 10 × 1 s); `l3.bus_electrical_timing_rollover_poll_interval_s` (A.U8C2.44): `l3.bus_electrical_timing_wrap_headroom_h`
    (`flash/test_bus_electrical_timing.py:107`, wider than one poll); `l3.scd30_same_device_rw_concurrency_run_bound_s`
    and the settle window (A.U8C.84): `l3.conftest_scd30_rw_script_timeout_s` (`flash/conftest.py:32`);
    `l3.sgp40_fram_backup_restore_backup_wait_s` (A.U8C.87): `l3.fram_storage_backup_script_timeout_s`
    (`flash/test_fram_storage.py:44`); `l3.scd30_plausibility_read_settle_s` (A.U8C.82):
    `l3.sensor_accuracy_scd30_script_timeout_s` (`flash/test_sensor_accuracy.py:24`);
    `l3.sgp40_voc_algorithm_quality_blackout_wait_s` (A.U8C.89): `l3.sensor_accuracy_sgp40_script_timeout_s` (`:40`);
    `l3.isl29125_mechanism_envelope_settle_s` and `_max_wait_s` (A.U8C.76): `l3.sensor_accuracy_envelope_script_timeout_s`
    (`:61`). Each entry states the relation in words; no audit ID in the text.
  - **Blast**: callers — · generated — · js — · tests `tests_scripts/test_tunables_register.py` (A.U8.02) does not check
    Dependants — unaffected · twin — · docs SPEC Part N only · toml — · uart —
  - **Depends**: A.U8.01, A.U8.04, A.U8.08-A.U8.12, A.U8C.45, A.U8C.48, A.U8C.50, A.U8C.52, A.U8C.53, A.U8C.76, A.U8C.81,
    A.U8C.82, A.U8C.84, A.U8C.86, A.U8C.87, A.U8C.89, A.U8C.90, A.U8C.101, A.U8C.103, A.U8C.104, A.U8C.107, A.U8C.111,
    A.U8C2.22, A.U8C2.44
  - **Kind**: doc
- V.U8C_tests_hardware.18 | A.U8C.45, .50, .54, .98, .99, .115, A.U8C2.35, .46, .48, .49 | FIX | a message or operator
  instruction on the tagged literal's own statement (or next to it) restates the value in text, so a changed constant
  leaves it wrong — for the manual scripts the operator acts on the text: `manual_bus_electrical.py:17, :22` ("You have 20
  seconds" beside `countdown(20)`), `:26, :29` ("30s" beside `tail_log(30.0)`), `:43, :49`; `manual_persistence.py:21,
  :41` ("20 seconds"), `:23` ("Wait 10 seconds"); `flash/test_toolchain_flash_boot.py:90` ("after 5 attempts");
  `bench/test_bus_concurrency_under_api_load.py:120, :451, :542` ("within 120s"), `:202, :289, :359` ("within 180s");
  `bench/test_network_resilience.py:874` ("within 60s"); `bench/test_uart_link_under_api_load.py:93, :140` ("within 120s"),
  `:182` ("within 60s"); `device_scripts/wifi_service_reconnect_repro.py:106, :137` ("180s", "600s");
  `wifi_reconnect_after_failed_attempts_repro.py:113` ("10s"); `isl29125_real_irq_edge.py:61` ("within 1.5s" = 30 × 50 ms)
  | each action's Change gains "the message at :<line> interpolates the constant (f-string, `{_NAME}` or `{_NAME / 1000:.0f}`
  for a ms constant shown in s)". This extends the `tests/` half, which did not raise message text; the same pattern
  exists there (e.g. hang-bound messages), so the lead should apply it to both halves or to neither.

## Deferrals, ledger, register fixes, open points (the `tests_hardware/` parts)

- **Deferrals** (U8C 14 + U8C2 14 = 28 in `tests_hardware/`; the 13 U25 ones are all in `tests/`, verified there): each
  opened; all 28 are fixed waits for a state a poll can observe (a counter, `TS`, device presence, a status bit) or,
  for `bench_control.py:277, :281`, the exact sleep G7/R23's State hands to U26 (RF309) — all right. Six more belong with
  them (V.06, V.12); none of the 28 is an observation window.
- **Mirrors in device scripts.** Read as the `tests/` half did: a mirror is the literal itself carrying the product ID's
  tag (inline or on a named constant), checked host-side by A.U8.02's register test — never an import. Every
  `tests_hardware/` mirror row is such a literal (A.U8.08's 31 `wdt.timeout_ms` sites, the `dev.uart_*` named constants,
  `isl29125.periodic_only_warn_at` at `isl29125_lighting_scenarios.py:335`, the `wifi.*` mirrors of the orphan repro,
  `web.max_content_length` at two bench sites); none imports `src/`.
- **Ledger rows** G4/R54, G1/R15, G8/R31, G7/R23 (both files): the `tests_hardware/` share is complete — every hit has
  a row; every hang bound (`run_isolated`, `join`, `wait_until`, `wait_for`, subprocess, socket) is tuned; G1/R15's
  instrument values (`harness.py:165`, `test_heap_under_connection_ceiling.py:49, :62, :78, :100, :101`,
  `harness.py:278, :284`) are all in actions. The G7/R23 row's "27 fixed sleeps deferred" becomes 33 with V.06/V.12.
- **Register fixes**: U8C's A.U8.05 item (`harness.py:165`, `…ceiling.py:49`) — right; U8C2's items on search-gap 7
  (`:119`, `:122`), A.U8.13 (`isl29125_lighting_scenarios.py:335`), A.U8.05 (`:62, :78, :100, :101`, `harness.py:278,
  :284`) — right; U8C2's A.U8C.84 item (`:32`) — right, but its sentence "Its sibling rows at `bus_concurrency_same_device_scd30.py:39`
  and `scd30_plausibility_read.py:30` already name their divisors" must go: they name them, no action replaces them (V.10).
- **Open points**: U8C's netem-profile reading, the `serving_at_default_gc.py:34` output cap and the
  `uart_link_under_concurrent_system_load.py:24-26` mirror-by-reading, U8C2's stimulus-length reading
  (`bus_topology_…:125, :132`, `wifi_reconnect_…:91`) and `network_resilience.py:957` derived — applied consistently in
  every `tests_hardware/` row; none was self-resolvable from an owner row.
- **Status arithmetic** after this file's FIX/ADD items (on top of the `tests/` half's): U8C tuned −6 (V.06, V.12),
  deferred U26 +6, new tuned IDs −6 +1 (V.07) +11 (V.16: nine `_wdt_feed_every` files, one file with two, one
  `_feed_step_s`) — the renames (V.03, V.08, V.11) change no count.

## Checked OK

A.U8C.44, .46, .47, .49, .51-.53, .56, .58, .64, .69, .75, .77-.81, .83, .85, .86, .90, .92, .93, .100-.114, .116-.119;
A.U8C2.17-.20, .22, .23, .25-.34, .38, .39, .41, .42, .44, .45, .47, the `tests_hardware/` entries of A.U8C2.51
