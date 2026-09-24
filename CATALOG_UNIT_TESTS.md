# Catalog: build-independent unit, resilience and regression tests

**What this is.** Every test this branch's connection-scaling and serving work (2026-09-22/23) added
or sharpened that runs in the ordinary suites, with no board, no special build and no scratch
tooling: `scripts/test.sh` (MicroPython tier and `tests_scripts/` pytest tier), the twin CI, and the
web tier. For each: what it pins, the defect or decision it guards, and **how it was shown to fail on
broken code** — a test never seen failing is marked so. Its companion, `CATALOG_INSTRUMENTATION.md`,
holds everything that measures rather than tests.

**Temporary, this session's working catalog only.** Kept current while this work continues (a
test added, changed or retired on this topic gets its entry in the same commit), then processed
into the permanent docs and **deleted before the branch merges**.

**How they run.** The whole suite twice, both green with zero `MemoryError`/`memory allocation
failed` markers: `scripts/test.sh` (reactive default, `gc.threshold(-1)`) and
`GC_THRESHOLD=32768 scripts/test.sh`. One MicroPython file:
`TZ=UTC MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen" <toolchain>/micropython/ports/unix/build-standard/micropython -X heapsize=16M tests/<file>.py`.
**Proving a test bites** without touching `src/`: put a modified copy of one module in a scratch dir
and put that dir before `src` on `MICROPYPATH` — the copy wins, and the test must fail.

---

## 1. Response bodies: bounded writes, identical bytes, framed static files

All in `tests/test_asy_webserver_service.py`. The rule they pin is SPECIFICATION.md Part I.3: no
response body is ever written in a piece larger than `WebserverService(chunk_bytes=...)` (default
256), JSON or static, and a static file carries its `Content-Length`.

| test(s) | pins | guards | shown to bite |
| --- | --- | --- | --- |
| `test_g3_every_static_file_arrives_whole_with_its_length_in_writes_of_at_most_256_bytes` | A build-independent stub mount (64 tiny files 0-63 B; every edge 127-129, 255-257, 511-513, 767-769; 1,023-1,025, 9,292 and 65,553 B), read back **write by write** through the real `_serve()`: status 200, `Content-Length` = size, byte-exact body, every write ≤ 256 B, all but the last exactly 256, no logged error | The silicon defect of 2026-09-23: microdot's `send_file` read 1,024 B per write (a fresh 1,025 B allocation each), and a failed read cut the page off behind a `200` with no length | Fails on the pre-fix code; fails with only the read size reverted to 1,024; fails with only the `Content-Length` line removed |
| `test_g3_a_json_route_mixing_tiny_medium_and_huge_values_is_written_in_bounded_pieces` | A stub sensor with 300 tiny values, strings at 40-250 chars, a ~80-piece list and a 150-entry nested dict, through `/measurements`: JSON round-trips, exact `Content-Length`, every write ≤ 256, > 100 writes | Any value serialised whole again | Fails with the cap reverted to 1,024 |
| `test_g3_a_single_scalar_longer_than_the_cap_is_the_one_piece_allowed_past_it_and_stays_whole` | A 600-char string goes out as exactly one write of its own JSON; nothing else exceeds the cap | Documents the one limit: `_PieceWriter` never splits a fragment (no real source is near it, ≤ 192 B) | Fails with the cap at 1,024 (the scalar merges into a larger piece) |
| `test_g3_one_chunk_bytes_parameter_bounds_json_pieces_and_static_reads_alike` | At `chunk_bytes=100` both a static file and a JSON route are written in ≤ 100 B pieces; a 1,000 B file is exactly `[100]*10 + [0]` | The owner's rule that one parameter sets both bounds, so they cannot drift apart | Fails if the static read is hard-coded to 256, and fails if the JSON writer is |
| `test_g3_a_zero_chunk_bytes_is_clamped_so_a_static_read_still_ends` | `chunk_bytes=0` still serves a file | microdot's body loop ends only on a short read; `read(0)` never is one, so an unclamped 0 hangs the connection | Not reverted (the hang would show as the file's own timeout) |
| `test_h2_add_value_is_byte_identical_to_json_dumps` | `_PieceWriter.add_value()` reproduces MicroPython's own `json.dumps()` byte for byte over 22 hand shapes and 36 errcount shapes: order, `", "`/`": "`, escapes, floats, and non-string keys quoted as their JSON text (`True` → `"true"`) | The fix must not change a single byte on the wire | Caught the author's own non-string-key bug during development |
| `test_h2_add_value_bounds_every_piece_however_large_the_value`, `test_h2_errcount_entry_is_never_one_string` | Large nested values and errcount entries come out in capped pieces | The ~870 B `/status` pieces and 296 B errcount strings that failed on silicon at the gc default | Fail with the cap at 1,024 |
| `test_h2_piece_writer_bounds_every_piece_and_never_splits_a_fragment` | Exact piece lengths `[255, 256, 1, 300, 14]` | Batching semantics | Structural |
| `test_h2_piece_writer_never_holds_more_than_sixteen_pending_fragments` | The pending list is collapsed every 16 fragments; pieces stay full | Without it the writer's own list array grew as large as a piece (256-512 B failures on the 32-bit twin) | Structural (`len(writer._group) <= 16`) |
| `test_h2_piece_writer_flush_is_idempotent_and_an_empty_writer_adds_nothing` | Flush semantics | — | Structural |
| H.2/H.3/I.2/I.3 hammer tests (`test_h2_stream_many_error_sources_…`, `test_h3_hammer_concurrent_status_requests_stay_valid_with_*`, `test_i2_hammer_concurrent_{measurements,sensors}_…`, `test_i2b_hammer_concurrent_{networking,system,notification}_…`, `test_i3_hammer_every_memory_bounded_get_route_concurrently_with_*`) | Every piece of every streamed route ≤ `_HAMMER_PIECE_BUDGET`, now **256 with no margin** (was 1,200) | A route regressing to one `json.dumps()` of a whole value | 11 failed with the cap reverted to 1,024; 18 in the file fail with the default at 1,024 today |

## 2. Connection admission at the configured ceiling

| file / tests | pins | guards | shown to bite |
| --- | --- | --- | --- |
| `tests/test_asy_webserver_service.py`: `test_backlog_defaults_to_one_above_max_connections`, `test_an_explicit_backlog_is_honoured_when_it_covers_the_ceiling`, `test_a_backlog_below_the_ceiling_is_clamped_up_never_left_short`, `test_the_server_passes_its_own_backlog_to_start_server` | `backlog` defaults to `max_connections + 1`, is clamped up, and really reaches `asyncio.start_server()` | `start_server()`'s own default of 5 silently capped the accept queue below any ceiling above 5 — lwIP dropped the extras where `src/` never saw them | Not shown reverted |
| `tests/_webserver_concurrency_scenarios.py` (run per device by `tests/test_digital_twin_webserver_concurrency_{wozi,dev,arzi,klkizi,grkizi,schlafzi}.py`) — every burst derived from `_ceiling(module)`, never a literal 4/8/12 | Healthy bursts at exactly the ceiling all `200`; 2 × ceiling rejected cleanly; `max(12, 3 × ceiling)` high burst; 1..ceiling sweeps | Tests pinned at 4 pass trivially after the ceiling is raised | By construction |
| same file: `test_the_accept_queue_is_never_shallower_than_the_admission_ceiling` | With `ceiling` sockets held, `_backlog >= ceiling` and the next one is refused by `_serve()`, not dropped in the queue | Same as the backlog tests, end to end | — |
| same file: `test_a_full_ceiling_of_concurrent_request_bodies_is_answered_correctly` | A ceiling of simultaneous config PUTs all `200`; then 900 B-body PUTs, each `200` or rejected, ≥ 1 served | Simultaneous contiguous demand is `max_connections × body` (Part I.6) | — |
| same file: `test_every_admitted_connection_is_actually_served_a_complete_correct_response` | 3 rounds at the full ceiling over the heavy routes: each `200`, a parsed non-empty dict, under 10 s, and the server still serving after | "Admission is not service" — a truncated `200` or a minute-late reply passes a plain `count(200)` | — |
| same file: `test_a_full_ceiling_of_real_page_loads_is_served_without_truncation` | An uncontended `/` is the reference length; concurrent page loads must all equal it | The truncated-page class of bug | Mount-independent after a fix (an early version depended on the stub site's `/style.css`) |
| same file: `_drained(module)` before every full-ceiling round | Each round starts from an asserted zero on `_open_conns`, not a blind sleep | A slot outlives its response | A control arm forcing the counter non-zero fails both scenarios. Fixes nothing observed; it removes a class of flake |
| same file: `read_body=False` at every status-only request site | The client drains rather than materialises bodies | An in-process client measures its own buffers (Part E.9) | Re-validated at 19/19 and 12/12 |
| `tests/test_digital_twin_bus_hazard_concurrency.py`: `test_{wozi,dev}_real_task_graph_survives_a_full_ceiling_api_burst_during_bus_load` | The real task graph with a full-ceiling REST burst mid-run: every sensor produces data, FRAM stays present, the watchdog never starves, ≥ 1 `200` and the rest refused | CLAUDE.md's four-tier bus-hazard rule at the raised ceiling | Tolerates refusals and a 16 MB heap applies no pressure; the strict bar is §3's Run 11b |
| `tests/test_digital_twin_real_website_integration.py`: `test_a_full_ceiling_of_concurrent_real_page_loads_all_serve_the_real_website` | `max(2, ceiling // 2)` tabs each load `/` and `/js/app.js`; bodies decompress and are identical across tabs | The real site under concurrency | — |
| `tests_js/live-backend.test.js`, "several real browser tabs load the real website at once against one live twin" | Real browser tabs against the live twin, scaled to the ceiling | The same, from a real browser | Body not re-verified for this catalog |

## 3. The twin CI gate at the full ceiling

| where | pins | guards | result |
| --- | --- | --- | --- |
| `scripts/_digital_twin_ci_suite.py`, Run 11b `_run_11b_full_ceiling_concurrency` | Twin as a subprocess, driver in CPython threads, one real socket per request; 3 rounds at the device's own `max_connections` (read from `devices/<d>.toml`) over the five heaviest routes — **all served**, still serving after, clean shutdown; inherits the suite's no-`MemoryError` log check at both thresholds | The owner's hardest requirement: every module running, full ceiling, no `MemoryError`, at either threshold | 6/6 every round at -1 and 32768 (limit 6). A 1 s settle now precedes round 0 too: at an exact-ceiling burst the readiness probe's own connection, still closing, refused one of six on every device in CI (`4914a25`). Not shown reverted; it replaced in-process numbers that were withdrawn |

## 4. Test infrastructure that had real bugs

| file / tests | pins | guards | shown to bite |
| --- | --- | --- | --- |
| `tests/test_digital_twin_poll_prewarm.py` (whole file): `test_a_port_another_process_already_holds_is_skipped_not_fatal`, `test_every_port_of_a_full_window_is_tried_before_giving_up`, `test_a_fully_occupied_window_fails_loudly_and_names_it`, `test_the_prewarm_itself_still_grows_the_poll_set_when_its_base_is_taken`, `test_the_band_stays_clear_of_the_canned_http_servers` | `prewarm_poll_set()` scans a 64-port window from 17400 instead of binding one fixed port; a full window fails loudly and names it | **The real CI flake**: up to 16 concurrent test files bound port 18099 at import and the loser died with `EADDRINUSE` before any test ran | 30 concurrent prewarms: 28/30 died on the old fixed port, 0/30 with the scan |
| `tests/test_digital_twin_http_client.py`: `test_an_empty_status_line_is_a_refusal_not_a_malformed_response`, `test_a_ceiling_refusal_is_catchable_as_a_plain_oserror` | An empty status line raises `CeilingRefusedError` (an `OSError`); a non-empty malformed one still raises `ValueError` | A refusal can arrive as a clean FIN with no bytes; eight `except OSError` sites let a `ValueError` escape once the burst grew to 21 | Reproduced on the unfixed tree; 18/18 green at the 32768 stage after |
| `tests_scripts/test_test_sh.py`: `test_a_failing_file_s_own_output_survives_into_one_annotation`, `test_a_missing_log_cannot_abort_the_summary_the_annotation_is_part_of`, `test_every_way_the_suite_goes_red_gets_an_annotation_and_only_under_actions` | `scripts/test.sh` emits one `::error` annotation per red outcome (a failed file with its last 40 log lines, an allocation-failure-only file, the pytest tier), only under `GITHUB_ACTIONS` | CI runner logs cannot be read from a cloud session; annotations can | This channel named the real flake on its first red run |
| `tests_scripts/test_heap_map_parser.py`: `test_allocation_need_is_the_first_rung_from_which_every_larger_one_is_clean`, `test_a_caught_and_logged_allocation_failure_counts_as_a_failure`, `test_a_probe_that_never_succeeds_reads_as_none` | `heap_map.parse_allocation_need()`: a need is the first rung from which every larger rung is clean; a caught-and-logged failure counts; never-succeeds reads `None` | The hardware need test's verdict | — |
| same file (hardware session): `test_placeable_counts_capacity_not_runs` | `placeable(size)` is `sum(run // size)` | A bench row had asserted `gaps_at_least(2048) >= ceiling`, which no healthy board satisfies | — |

## 5. Build configuration: lwIP options and per-device ceilings

All `tests_scripts/` (pytest tier).

| file / tests | pins | guards | shown to bite |
| --- | --- | --- | --- |
| `test_micropython_overrides.py`, `TestVerifyLwipConnectionCountsAnchor` / `TestApplyLwipConnectionCountsOverride` (`test_every_anchor_is_load_bearing` over 15 anchors, `test_never_writes_inside_the_micropython_tree`, `test_generated_lwipopts_includes_the_real_one_then_redefines_every_option`, `test_is_idempotent`, `test_rejects_a_partial_unknown_or_ill_typed_option_set`, `test_every_settable_macro_is_one_the_pinned_source_actually_defines`, …) | The `MICROPY_BOARD_DIR` shim includes the real `lwipopts.h` first, then redefines each option; never writes into the checkout; fails loudly when the pinned MicroPython drifts | lwIP options reaching the build at all, and surviving an upgrade | Each anchor proven load-bearing by removing it |
| same file, `TestLwipEnsemble` (`test_the_derived_values_match_lwips_own_formulas`, `test_the_shipped_table_is_coherent_at_every_devices_own_ceiling`, `test_one_value_moved_alone_is_refused_by_name`, `test_apply_refuses_an_incoherent_set_before_writing_anything`, `test_the_shared_pools_must_serve_every_admitted_connection_not_just_one`, `test_the_mem_size_floor_is_the_fielded_designs_own_share`, `test_the_generated_header_carries_a_sentinel_the_build_check_demands`; hardware session: `test_the_pbuf_header_allowance_matches_the_ipv6_enabled_port`) | `check_lwip_ensemble()` mirrors lwIP's nine `init.c` `#error` relationships, plus two lwIP does not check (segments for every admitted connection, a `MEM_SIZE` share per connection) | lwIP options are not independent; a set that compiles can still starve connections | Rejects single-value moves by name; caught two violations in the first shipped set (SEG 32 < 56; `MEM_SIZE` 8000 = 1,142 B per connection) |
| `test_buildgen_validate.py`: `test_max_connections_is_optional_and_falls_back_to_the_src_default`, `test_the_src_default_itself_fits_under_the_pinned_lwip_pcb_count`, `test_a_max_connections_at_the_pcb_ceiling_is_rejected`, `test_a_max_connections_below_one_is_rejected`, `test_a_backlog_under_max_connections_is_rejected`, `test_a_backlog_at_or_above_max_connections_is_accepted`, `test_a_non_int_connection_field_is_rejected`, `test_every_shipped_device_states_its_own_ceiling` | Per-device `max_connections`/`backlog` validated against `MEMP_NUM_TCP_PCB` with one slot of margin; the default read from `src/`'s own AST | A device configured past what lwIP can hold | Not shown reverted |

## 6. Lessons from approaches that did not hold (one line each)

- `$GITHUB_STEP_SUMMARY` instead of annotations: broke `test_test_sh.py` (`set -u`), and job
  summaries are not in the REST API anyway. Reverted.
- Tests that only count `200`s: pass on truncated bodies. Every serving test now checks the body.
- A 16 MB Unix-port heap absorbs any single allocation: a hammer test that does not assert the piece
  size passes with the fix fully reverted. Assert the bound itself.

## 7. Candidates from the silicon peak-load instrumentation (2026-09-23/24)

The silicon sittings' instruments and findings (`HEAP_FRAGMENTATION_MEASUREMENTS.md` §7R), sorted
against what the ordinary suites already pin. Everything that only measures went to `CATALOG_INSTRUMENTATION.md`. **Nothing
here is written yet**; "owner" marks a candidate that would first need a rule decided.

| finding / behaviour | test tier and shape | status |
| --- | --- | --- |
| A rejection at the ceiling writes nothing and leaves the counter unchanged | `test_asy_webserver_service.py`, the F1 rejection test | **exists** |
| A refusal (reset, abort, broken pipe, bad status line) is told apart from a real transport failure | `tests_scripts/test_http_client_ceiling_close.py`; twin: `test_digital_twin_http_client.py` | **exists** |
| No body piece exceeds `chunk_bytes` (256); this is the `/status` wall at 242-257 B | §1's H.2/G.3 tests | **exists** |
| A static file always carries its `Content-Length` | §1's G.3 test | **exists**. The silicon's empty `200` with no length during the boot WLAN drop (MEASUREMENTS §7R.5) is unexplained; understand it before writing a test |
| A torn heap-map capture raises instead of reporting a healthy heap | `tests_scripts/test_heap_map_parser.py` | **exists** |
| **A slot is held until the close completes**: `_serve()` decrements `_open_conns` only after `_close_writer()` returns, so a closing connection still counts (this is where the ~70 % refusals come from) | MicroPython tier: a writer whose `wait_closed()` blocks on an `Event`; the counter must stay 1 until it is released, then return to 0 | **proposed**. It pins today's semantics, so changing them (BACKLOG item 44, owner) becomes a deliberate act that also updates this test |
| **PCB headroom follows the measured pattern**: `[lwip] MEMP_NUM_TCP_PCB ≥ max(max_connections) + 3` (closing and TIME_WAIT connections hold PCBs) | `tests_scripts/`, next to `TestLwipEnsemble` | **owner**. `buildgen/validate.py` demands only one slot of margin, and `check_lwip_ensemble()` has no PCB-per-connection floor, so +3 is shipped but unenforced |
| **Every heap- or serving-measuring device script sets `gc.threshold` itself and prints `GC_THRESHOLD=`** (`mpremote` does not reset the interpreter; a result line without it is void) | `tests_scripts/`, structural over `tests_hardware/device_scripts/` | **proposed**. 6 scripts call `gc.threshold`; only `serving_at_default_gc.py` prints it |
| **A host instrument that holds connections stays inside the firmware's own timeouts**: `harness.discover_max_connections()`'s default `dwell_s` below `WebserverService`'s `per_call_timeout_s`, and `test_heap_under_connection_ceiling.py`'s `_RECYCLE_S` below `outer_cap_s` | `tests_scripts/`, reading the defaults from `src/`'s AST as `test_request_timeout_ceiling.py` does | **proposed**. Both instruments failed *silently* on silicon when they did not (SPECIFICATION.md H.7.1): the probe walked past the ceiling, the holder measured an idle heap |
| **A bench test that runs a device script restores the board to serving afterwards** | `tests_scripts/`, structural over `tests_hardware/bench/`: every `run_isolated()` caller also reaches a restore in a `finally` | **proposed**. `run_isolated()` leaves `main.py` stopped; the one test that did not restore failed every later network test of the run. The restore helper exists twice, identically, in `test_heap_under_connection_ceiling.py` and `test_serving_heap_at_default_gc.py` — reported, not merged |
| Every device script's heap-map envelope round-trips through `heap_map.parse_labelled()` | `tests_scripts/test_heap_map_parser.py::test_every_emitters_own_envelope_round_trips_through_the_parser` | **exists** — one script's `<<<MEM` envelope had discarded every dump |
| `placeable(size)` is capacity, not a count of gaps | §4's `test_placeable_counts_capacity_not_runs` | **exists** |
| The removed silicon sweep's classification, validated reference fetch and margin window | would be pure functions with a fake `fetch` | **instrumentation**: the tool is removed (MEASUREMENTS §10); only if it is rebuilt |
| Rejection counter = host refusals; script footprint; sampler cost; linker heap = 187,712 + (8 − L) × 2,324 B | need the board or a built ELF | **instrumentation** (`CATALOG_INSTRUMENTATION.md` §6-§7) |
