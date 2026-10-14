
######## SubagentHandback 2026-10-13T20:32:13.309Z
U24 lane U2 hand-back. Commit b76ddb7 on audit/u24-u2 (S/wt-u24u2). Not pushed. Nothing of mine is running.
Steps:
- Applied: all of W1 (151, 152, 28, 99 .104/.112/.210/.282/.295, 182-185, 204, 286, 209, 210, 207 R, 211-215 R, 219, 220, 254, 222, 227, 228), 32, 34+287 B, 42+181 B, 241 B, 230 R, 35, 37 B, OF-82, OF-86, 22/A.U24.56/A-36 C. For 205 (V), A.U24.59 has landed at test_asy_udp_socket.py:617; the wifi part of A.U24.61 had not landed (`_cfg_schema` comparison), so I applied it: one test_get_cfg_schema_is_the_schema_in_source.
- Already landed: 208 (the builder makes the three config objects; it is now typed through a TypedDict plus Unpack), 33 (test_asy_webserver_service.py:814), 38 (wifi :31, :3906, :3931).
Deviations:
- One combined commit, no separate W1 commit.
- g3's mixed-size body is compared byte for byte with `b'{"STUB":'+json.dumps(v)+b'}'` instead of strict_loads. Planted ",, " → fails :3021.
- D.15 is applied to the members of every class (23 classes, AST-checked pure reorder). Module-level helpers in the test files are left in their sections, as in 51 of 56 test files.
- Soak per_call_timeout 0.02→0.01 s: rate stays 0.0 healthy / 16.0 planted. A virtual-clock version was tried and dropped: its rate drifted about ±10 B/cycle.
Seen failing first:
- 34: :2365/:2382/:2397 failed with the warnings planted as unpersisted.
- 37: :3763 via :3910/:3921 failed with a scratch GET route added.
- 35: healthy 0.0 vs planted 16.0 B/cycle, which failed the assert.
- 32: udp :406, EAGAIN.
- 42/181: captive :343, ntp :330.
- 287: captive :670, :652.
- 241: wifi :806, :750.
- 230: 6 failures with `_put_sensors` planted undispatched.
- OF-82: :593 and :227 failed with the loop never woken.
- OF-86: both a judge copy missing a key and the base tree fail tests_scripts/test_radio_shape_corpus.py (:37, :21).
- _ntp_frames: :2602.
- wifi on the pre-F fakes: :4931, :4988, :5003, :3165, :3344, plus the hotspot integrations.
- The surface check went from 2 failed to 2 passed.
Red checks, all waiting on the lead unless noted:
- test_ntp_generated_wiring.py:44 (also :3, :45, :49, :53): must say `_make_ntp`. H's rule (test_microtest.py:189) forced the rename.
- _decision_vocab_allowlist.txt: drop :302, :304, :318, :319, :351.
- test_import_placement.py: drop :78-80 and :100-103.
- test_no_variant_literals.py: drop :51, :76, :77.
- test_tunables_register: waits on X (see facts).
- test_microtest and test_const_mirrors reds are in other lanes' files; none are mine.
Scan, class 4 swallows in the test rig, new, flagged rather than fixed (behaviour):
- test_asy_captive_dns.py:111 `_read_replies` and test_asy_dns_client.py:441 `answer_once` absorb every OSError. A wrong errno surfaces as a timeout. Fix: absorb only EAGAIN.
- test_asy_webserver_service.py:950 `_file_or_none`: narrow to ENOENT.
- test_asy_webserver_connections.py:868/:882 `_can_listen`/`_refused_or_eof`: any OSError reads as the expected answer. Narrow to EADDRINUSE / ECONNREFUSED|ECONNRESET|EPIPE.
- OF-111 refusal: covered at webserver :1223, :1243. Ports: covered by U25's allocator.
Facts owed to X:
- New `l1.webserver_leak_rate_max_b = 8`: tag at test_asy_webserver_service.py:2697. Basis: healthy 0.0, planted 16.0 B/cycle, gc -1. E.7/E.8 should state the two-window rate.
- Withdraw `l1.webserver_leak_scenario_timeout_s` (SPECIFICATION.md:10380).
- web.max_content_length (:10173) and web.chunk_bytes (:10180): drop the test site; it now reads the source.
- Fake-server poll_ms/poll_tries (:10473/:10482): add tests/test_ntp_fram_system_integration.py and tests/test_ntp_wifi_dns_integration.py as sites.
- rp2 ignores the RTC weekday, so asy_ntp_client.py:329 is harmless.
Facts owed to Y: none.
Facts owed to the lead:
- pyproject Any baseline :455, :458, :466, :475-477, :485-487 retire; checked clean with a scratch config.
- pyproject ANN401 :279, :285-287, :291, :301 retire.
- tests/_strict_json.py is quadratic: each str index/len walks UTF-8 (py/objstrunicode.c:164-186). 37 KB takes 2.9 s against 2 ms for json.loads; indexing bytes would make it linear (H).
- A parse cache that outlives its test slows every later collection, so mine is cleared after each test.
- _async_harness._drive keeps every task until the run ends (~9.4 KB/cycle in long runs).
- src_const returns object, which forces `# type: ignore[assignment]` on every typed read.
After-times (base → after):
- webserver: 15.95 → 12.88 (gc -1); 16.57 → 14.53 (gc 32768); settrace 37.8.
- readiness -1: 0.155 → 0.171 (+10%, about 16 ms of harness import, A/B).
- Every other file is within 3% (connections A/B +3%). Zero MemoryError at gc -1, gc 32768 and settrace.
Runs:
- batch.sh final (pid 13217, 14 files × 3 stages, all green) rc=0, logged in RUNS.md. The final webserver runs at all 3 stages: rc=0.
- Diagnostic A/B timings, including base copies of webserver, connections and readiness: all exited 0.
Logs: S/u24/laneU2/runs/
