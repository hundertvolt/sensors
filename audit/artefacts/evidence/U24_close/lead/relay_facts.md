# U24 relayed facts (for X's and Y's "Relayed facts" sections; one line each, source hand-back named)
- X, from F1 (d7e455a): E.4 (the fault convention, the ports cited, the Not-modelled lines); C.12 (an ENODEV probe; scan()
  never raises, [] when busy); F.7 row 12 / J.7 (both UART fakes answer every ioctl but POLL, GET_FILENO included, with
  -EINVAL); K.2 (Pin: a None pull and an omitted pull are the same, no pull, on every configuring call).
- Y, from F1: none.
- X/Y, from S1 (f5c6db2): none (no taker yet); no @tunable.
- X, from H1 (2006fed): E.2 as published in the hand-back (microtest, _async_harness, _src_const, strict JSON,
  require_fresh, stamps, shared doubles, _protocols); E.3: a direct run can refuse a stale tree (callers in wave 2).
- Y, from H1: CLAUDE.md "Known segfault cause": a nested asyncio.run() segfaults with no parked task at all (the inner
  run leaves cur_task None, extmod/asyncio/core.py:200; the outer coroutine's next await crashes); reproducer
  S/u24/laneH/nested/no_parked.py. The bullet stays true otherwise (a raw asyncio.run() still crashes).
- X, from the U23 fix (2ad4747): SPEC H.7: each live check takes its test's timeout and ends its own waits one twin stop
  (15 s) before it (Vitest never cancels a command); each refuses to start while 127.0.0.1:19481 answers; an overrun
  names its step. Budgets inside the test: smoke 30/45 s, tabs 185/200 s, restart 165/180 s (the two tagged budgets'
  Part N rows already count the stop; literals unchanged). New untagged `SMOKE_TIMEOUT_MS = 45000`: X rules its tag.
- U24 open findings (lead): the trigger of arzi/schlafzi's 200 s tab-check overrun in CI run 38422274046 is not
  reproduced (9 local runs, 1/2/4 CPUs, headless shell and full Chromium 141; CI used chromium-headless-shell rev 1243,
  Chrome 153); evidence S/u23/cifix/{ci,runs,checks}/; the overrun now names its step if it recurs.
- X, from T final (5c4d72a): C.8: the host tier selects devices only through tests_scripts/_devices.py (DEVICE_NAMES,
  device_toml(), devices_with(driver)); fixtures are named "fixture"; no tests_scripts test file names a variant.
  E.2.2: test_buildgen_pico_gpio.py is the pin-table home. E.2.3: pytest suites are module-level (no class Test*),
  checked by test_code_conventions. No @tunable added; OF-113's `_VALID_CASES = 30` untagged like `_CASES` (X rules).
- X, from S final (0e59e52): E.1: the three runners (test.sh: 53; run_digital_twin_ci.sh: 53, 18080;
  run_unix_port_integration.sh --device <name>: 53) take the per-port lock right after validation; refusal message;
  release on exit (EXIT trap); descendants pass through the owner chain; a per-namespace XDG_RUNTIME_DIR (lead ruling).
  E.5/E.5.3: four reports (the generated one without XML; host data in results_dir), any render failure -> exit 3,
  host coverage report-only, --xml-file optional. No @tunable added. A-37: 964.6 s traced tier, single run stands.
- Y, from S final: CLAUDE.md "Two suites ..." gains the per-port lock (and the per-namespace runtime dir); README's
  manual-runner example passes --device <name>; BACKLOG's chroot list names the coverage==7.16.2 pin and the
  host-coverage step.
- X, from J final (c6b9ea1): H.7: the live tier needs the built toolchain; all four commands throw; every twin holds the
  53 lock, the restart check across both boots. E.1: the JS lock = S's directory/files/message/owner chain, re-entrant
  with a count, released after the twin exits and at process exit. H.8/H.4/K.8 as in J1. Part N :10356/:10357 Sites ->
  tests_js/_twin_process.js (20000, 15000) + scripts/cross_browser_smoke.mjs.
- Y, from J final: README website tooling: the live tier needs the toolchain and fails, never skips. BACKLOG chroot
  list: unit-tests, -gc-threshold and -coverage set up .nvmrc's Node.
- X, from F final (3050b0f): E.4 (the surface rule and its check, the machine contract, the twin pending list, port
  citations, the fault-queue convention, the corrected lightweight sentence); C.12; F.5.1 (I2C static per id); F.7 row
  12 / J.7 (GET_FILENO -> EINVAL, POLL through poll_mask); F.9 (bounded-poll wording); K.2.
- Y, from F final: CLAUDE.md "Known hang cause": a real poll over a fake is now counted and the after-each check fails it.
- X, from the U23 summary fix (7defbce): SPEC E.10: test.sh's summary names each failed test of the deciding attempt with its first failure line (microtest's own FAIL form), at most 5 then '+N more'.
- (X, from the U23 drain fix 73f675c) SPECIFICATION.md Part N rows l0.live_twin_tab_wait_ms (:10366) and l0.live_concurrent_tabs_timeout_ms (:10367): the per-tab reload slot includes its drain (the drain gets at most the slot less one l0.live_twin_section_wait_ms); a drain still open fails naming the other tabs' in-flight requests. Part H.7.1's drain rule is what the reload waits for.
- X, from U3 final b69328f: SPEC J.3: the tests' wire-constant copies are pinned line by line to the protocol's own; J.7: the link exerciser runs both CRC modes at L1, plus a CRC16 corrupted-frame case; E.4: the UART fake applies rp2's TX/RX pin rule (CTS/RTS not modelled); heap readings in tests are taken between harness runs. No @tunable.
- Y, from U3 final b69328f: UART_C_PORT_CHANGELOG.md Class B (Python-internal, no C impact) row: the link exerciser's banner payload b"dev-uart-crossover" -> b"uart-crossover" (src/asy_uart_link_driver.py:35), dev only (the only device wiring uart_link); the wire format and payload_size unchanged.
- X, from U2 final b76ddb7: Part N: new @tunable l1.webserver_leak_rate_max_b = 8 (tests/test_asy_webserver_service.py:2697; healthy 0.0, planted 16.0 B/cycle at gc -1); E.7/E.8 state the soak as a two-window leak rate; withdraw l1.webserver_leak_scenario_timeout_s (SPEC :10380); web.max_content_length (:10173) and web.chunk_bytes (:10180): drop the test site (the test reads the source); fake-server poll_ms/poll_tries (:10473/:10482): add tests/test_ntp_fram_system_integration.py and tests/test_ntp_wifi_dns_integration.py as sites; F/K note: rp2 ignores the RTC weekday, so asy_ntp_client.py:329's weekday is harmless. Radio shape corpus: each judge declares _JUDGED_SHAPES, tests_scripts/test_radio_shape_corpus.py checks they cover every corpus key (E.4).
- Y, from U2 final b76ddb7: none.
- X, from M final cc8d32f: SPEC E.2 (or F.1 :5348): tests/_strict_json.py scans the body's UTF-8 bytes in linear time (a str's len()/index are O(n) in MicroPython, py/objstrunicode.c:116-117,164-186); offsets count characters; invalid UTF-8 is refused (UnicodeError is a ValueError). The l1.webserver_leak_rate_max_b tag is now at test_asy_webserver_service.py:2701. No @tunable.
- X, from B final d1c9d9c: L.4/L.5/E.3: the generator removes every file it did not write from build/generated_src/ (top level, definitions/, api/) before writing the stamps, `.tmp` files stay; `.inputs_stamp.json` is {"inputs", "outputs"}, outputs listing both stamps; require_fresh() refuses an orphan, a missing output or an empty list; new error line `error: cannot remove <file>: <strerror>`, exit 1. Two concurrent generator runs share `.tmp` names and fail visibly (exit 1). No @tunable.
- X, from K final e262d67: Part N: new row l1.async_harness_reap_limit_ms = 5000 (Sites tests/_async_harness.py:29; basis: post-cancel cleanup is ms-scale); runner.kill_after_s: the per-file timeout's first signal is SIGINT, new site _cleanup's 2x stop bound. E.3.1: INT -> microtest's ABORT line with the hung test's traceback -> --kill-after hard stop (137, its own line); the EXIT trap stops every background job by pid and waits before releasing the port lock; the summary names ABORT lines. E.2: the harness's guarantees (every reap ends, naming what it could not end; no finished task kept; per-call cost +2.0 us at -1 / +3.1 us at 32768, +0 B).
- X, from D final adf4f4f: C.8: the generated scheme drives every writer on every shared bus (a bus with no writer reports SKIP); a shared SPI bus without an adapter fails loud; the mock tier covers the FRAM erase hazards. Part N: new row l0.fram_less_boot_timeout_s = 60 (tests_scripts/test_fram_less_boot.py:16). E.4/E.8: the website tests identify inlined definitions by byte equality with build/generated_src/definitions/<d>.json.
- X, from the W2 lead fix: E.2 (harness guarantees): the reap and cancel() pass over a finished task whose data the loop cleared after another task awaited it (awaiting it again raises None and crashes the port, extmod/modasyncio.c task_iternext); F (asyncio facts, next to "awaited at most once"): in 1.29.0's C asyncio a second await of such a task segfaults rather than raising.
- X, from the W2 lead commit d994e5b (W3 = d994e5b): E.2 (harness): the reap first gives the loop one round, as the board's loop never stops (a task the run left queued and due takes its step: a deferred config flush completes there), then cancels each unfinished task on its own; release_finished() drops the finished tasks a running call still tracks (a heap reading inside a run measures only the system; used by the supervisor-death drift test, bound unchanged at 2048 B); the shared helpers gain UTCValid (tests/_fake_time.py, the boot's first NTP clock set for a block) and FakeMB85RS2MTA (tests/_fram_chip_fake.py, the 256 KB part's size and RDID; tests/_generated_module.py's array-sharing variant subclasses it). E.3.1: a file killed at the hard stop past its timeout (137, it ignored the interrupt) is retried like a 124 timeout.
- Y, from the W2 lead commit d994e5b: CLAUDE.md "Standing backstop: hanging tests": the per-file timeout's first signal is SIGINT (microtest names the hung test with an ABORT line and traceback); --kill-after stays the hard stop; 124 and 137-past-the-timeout are both retried. A new "don't re-diagnose" fact for the "Known segfault cause" family: awaiting a finished task a second time, after another task awaited it and the loop's queued handler entry cleared its data, segfaults the Unix port (1.29.0 C asyncio, extmod/modasyncio.c task_iternext: nlr_raise(None)); the harness passes over such tasks; a test file dying with "Segmentation fault" in a reap is this, not a memory bug. BACKLOG chroot entry: the dev group's coverage pin is "coverage==7.16.2".
