# A-L verify U8C_tests_hardware — U8C + U8C2, files under `tests_hardware/` (HEAD 741dfb5; no code change since a4766a9 outside `audit/`)

Counts: (filled in at the end)

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
    `==` literal outside every family (U8C2 blind spot). Tagging `:46` alone leaves a hidden second copy: a changed
    `_CEILING_RETRY_ATTEMPTS` would retry past the last attempt without raising, and end in `AssertionError("unreachable")`
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
  notify.loop_tick_s": see V.U8C_tests_hardware.DEP).
- `bench/test_serving_heap_at_default_gc.py` 11+1 · A.U8C.53 · OK (`:29` shares `l4.network_resilience_slot_release_wait_s`
  by C.0.2's "same purpose across files … shares one ID"; `:30` Dependant: V.U8C_tests_hardware.DEP).
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
