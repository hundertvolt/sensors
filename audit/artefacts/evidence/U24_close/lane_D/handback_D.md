
######## SubagentHandback 2026-10-13T22:02:39.656Z
U24 lane D final: adf4f4f on audit/u24-d (base 31d5bfc). 26 files, all in files_D.txt; tests/_boot_recorder.py and test_digital_twin_unix_port_gc_unwedge.py needed no change. No WIP (ruling 2).
1. Steps applied: all W1 steps (13 .034, 99 .026/.029/.231, 139, 133, 218, 249, 250, 78 parts .01/.08/.60, 323, 327, 330, 340, 345); 125 .027+.231 (A.U24.27/.28); .035/.038 (A.U24.43); A.U24.50 (1)(2); A.U24.06; .041 (A.U24.32 (1)(2)); .040 (A.U24.17) plus OF-111; row 63; .036; 41 M.TEST_UNIT.238 (A.S0930.23 (a)-(c) plus the storage reader); 331/338/339/343 (A.U24.30/.38); OF-112; A.U24.56 S24; .67 (3); the lead's :49 comment fact.
2. Already landed: .037 (2) at `_generated_module.py` boot_generated(); .047 (U20); the "no config_*.cfg after a reset" half of the storage item, at `_sensortask_scenarios.py` resetconfig (listdir assert). Nothing at U24: 126 .031 (U25).
3. Deviations:
   - `_DEVICES` tuples kept (A-5; test_device_tomls reads them). D.15 reorder of the sectioned libraries left to U36 (packet :250 (6)); new members placed by section.
   - Both website tests now identify the inlined definitions by byte equality with build/generated_src/definitions/<d>.json, not strict_loads. Reason: a strict_loads parse costs about 4.2 s, and the byte equality is stricter.
   - fram_fake_class and the 256 KB fake moved from `_sensortask_scenarios.py` to `_generated_module.py`, and the probe no longer seeds. Reason: the grown library import broke boot_contiguity's control arm for dev (859 KB below the seam). Now 32 passed, 5 skipped, as base.
   - The erase sweep steps 10 turns at a time.
4. Seen failing first:
   - Per-writer test: isl_stray_read fails it; base's config_write passes.
   - Exact-touched sweeps: scd30_raises_first fails them on 6 buses; base passed them vacuously.
   - sup_never_started: "task(s) [17] not running".
   - collector_drops_webserver: count shows WEBSERVER 0.
   - Also failing first: build_date_swapped, led_never_signals (empty frames), and scenario_unregistered (90 vs 89).
   - A device without sgp40 reports SKIP.
   - twin_steps_ignored: bmp3xx and scd30 fail; base passes.
   - FRAM-less test: missing file on base; fram_kept bite fails 2.
   - FRAM layout: layout_top_down fails at `_sensortask_scenarios.py:572`.
   - The 4 new hazard tests in test_bus_hazard_multi_device passed at once (guards). Each is bitten:
     - The two erase tests (a) and (c): erase_half_units, pass1_block0_only and addr_always_24bit.
     - (a) alone: quiesce_no_wait.
     - Cancel test: lock_kept_on_cancel and measure_buffer_kept.
     - Storage reader: config_write_yields.
5. Red checks:
   - tests/test_digital_twin_sensortask_integration.py:845 heap drift [748800..1185952]. Waits on H/lead: `_async_harness.py` `created` keeps every dead restarted task (about 47 KB each); a pruning probe is green.
   - test_digital_twin_webserver_concurrency_<d>.py: intermittent SIGSEGV at 32768 (schlafzi 2 of 3 whole-file runs; 4 of 35 runs of the first four scenarios with the harness, 0 of 16 without its reap). Waits on H/lead.
     - Trace: `_reap` awaits a task (stream_awrite) that ended during the reap after its runner had awaited it (state False, data None). Awaiting it again raises None (SPEC F "awaited at most once"; dmesg: segfault at 6).
     - Fix: skip `task.done()` before each await in `_reap` (:74-76); with that fix, 18 of 18 runs pass.
   - test_tunables_register: tests_scripts/test_fram_less_boot.py:16 `l0.fram_less_boot_timeout_s` has no Part N row (X).
   - Stale allow-list rows for the lead to delete:
     - test_decision_vocabulary: `_decision_vocab_allowlist.txt:202`.
     - test_microtest `_JSON_LOADS_ALLOWED`: :21, :25, :27.
     - test_no_variant_literals `_NOT_YET_CLEANED`: :52, :84.
   - My files are clean in test_microtest and test_const_mirrors (W1 had D 19 and 21).
6. Scan:
   - class 4: the storage reader swallowed any OSError; now only ENOENT counts as "no file" (new, fixed).
   - class 4: exercise swallow (covered by .028).
   - class 2/6: harness retention, and class 4/6: harness double await (both new, H; item 5).
   - OF-111 refusal mode: covered by `_every_write_refused`.
7. Facts owed:
   - U1: `tests/_bus_hazard_catalog.BMP_EXPECTED_TEMPERATURE` = 28.460795242070162 (BMP388 §9.1-9.2).
   - X: C.8 — the generated scheme drives every writer on every shared bus (a bus with no writer reports SKIP); a shared SPI bus fails loud without an adapter; the mock tier now covers the FRAM erase. New tag `@tunable l0.fram_less_boot_timeout_s = 60`.
   - Lead, explicit-Any lines (base → now): `_sensortask_scenarios` 77→77, catalog 21, probe 3, test_bus_hazard_generated 5→8, test_bus_hazard_multi_device 7→5, construction 7→5, webserver 16→13. ANN401: `_sensortask_scenarios` 61→62 (`_strict`); no row retired. mypy main pass: only F's 37 errors; twin and host passes clean.
8. Times beyond 10 %:
   - test_bus_hazard_multi_device 1.48/1.84 → 3.8/5.6 s (settrace 5.2): 4 new hazard tests; the 256 KB erase alone is about 1 s of product cost.
   - test_website_build_integration 0.17/0.27 → 0.20/0.31 s: require_fresh() plus the per-device 404 paths.
   - Twin files under 0.1 s differ only by the wrapper's start-up (the unchanged gc_unwedge also went 0.027→0.04 s).
   - Wrappers at -1/32768/settrace: wozi 44/62/85, dev 61/87-92/118, the other four 40/55-58/78. The base runs failed early, so they are not comparable; versus U23's full pass, wozi -1 is 46.9 → 44.1.
   - test_bus_hazard_generated 63/64/65 s against base 84/84.
9. Runs, all logged in RUNS.md; nothing of mine runs.
   - Batches: f1 26 runs, all rc 0. f2 58 runs: :845 rc 1 ×2, schlafzi 32768 rc 139. f3 42 runs: :845 ×2, U2's neopixel_wifi rc 1 ×2 (W1 red, unchanged), schlafzi 32768 rc 139.
   - Zero MemoryError in every run.
   - Repeats and variants for the segfault, the bites, and the pytest files boot_contiguity, fram_less_boot and device_tomls.
   - Logs in S/u24/laneD/logs.
