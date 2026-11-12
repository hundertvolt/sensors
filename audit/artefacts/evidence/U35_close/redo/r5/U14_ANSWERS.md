# U14 owner answers and what each changes (lead, 2026-11-06); applied by one unit after the last question

- Q1 (08:06): A; SPECIFICATION.md 0.2's "proven good" sentence is replaced by the owner's definition (owner,
  2026-11-06): a behaviour, pattern, feature or fix the product profits from and actually requires; anything the owner
  required or requested, or that was developed into a good shape, leans to "keep", but this is no hard gate: a fix
  whose only reason was removed overkill is obsolete and goes, its knowledge preserved.
- Q2 (owner, 2026-11-06 08:47:35 UTC): "Keep as is, Option A." The 16 failure-handling choices stand, code 9 included.
  Asked first: what code 9 buys, what "ResetErrors refused after a supervisor fault" means (the loop's own crash,
  until the watchdog reset, at most about 8 s), how a successful command overwrites the pre-written 9, which files a
  config reset deletes. Owner's premise: a plain reboot writes nothing into the flash filesystem (checked below).
- Q3 (owner, 2026-11-06 09:08:46 UTC), direction, rest of Q3 still open: "all hazard code goes into that module. If the
  module is not imported, as in all non-dev builds, there is not a single trace of anything about it, no hook, no
  website, no endpoint, no lines. If it is selected, in brings in everything it needs, the only switch for that being
  its inclusion in the toml file." Apply: remove add_status_command() / _status_commands / the :796 lookup from
  src/asy_webserver_service.py; the link module brings its own route, registered by dev-only generated lines on the
  app codegen.py:593 creates (e.g. PUT /uart), its form a dev-only website section posting there; if the shared page
  code cannot post a new section unchanged, back to the owner first. test_uart_link_bench_only.py fails on any trace
  (hook, key, route, form, generated line) in a non-dev build. Bench hazard test and doc lines follow the new path.
- Q3 rest (owner, 2026-11-06 09:14:02 UTC): "The rest of the Q3 topics stay as they are (A)" - the bounded run under
  /status load, the two flash-tier hazards, the 50 ms idle poll, both CRC modes, piece-by-piece train answers, and
  ResetErrors not re-arming the no-valid-frame diagnostic stand.
- Q4 (owner, 2026-11-06 10:20:31 UTC): "I would like all of the tests, except #9 for the reason it's almost no added
  value at a very high cost." Gaps 1-8 get board tests (unit gtest); #9 (NTP failure modes) an accepted limitation in
  E.6.6 with the owner's reason (the client's lines are the twin's; the board's own UDP methods, lwIP and RTC run on
  every real boot's sync and in the unreachable-server test). Asked first: what "all" means (09:19:58), #9's code
  identity (10:11:34). The three test rules (driven-clock months, soak = liveness, deadline polls) not objected to.
- Q5 (owner, 2026-11-06 10:50:12 UTC): "Question 5: Option C" (asked first, 10:48:06, whether C costs only a few
  lines more). All five fake-chip differences corrected in `digital_twin/`: SGP40 serial fixed, BMP3xx drdy cleared
  by a data read, PWR_CTRL 0x13 during / 0x03 after a forced conversion, SCD30 no-command read DD DD DD
  (`_scd30_chip.py:266`), BMP3xx `_OSR_RESET` 0x00 (the bench part, chip id 0x50; DS001/DS003's 0x02 kept in the
  row). Each README row becomes "fixed:" with a small `D` self-test, per the table's convention. The two runtime
  differences (soft-timer callbacks never queued, watchdog as a task) stay accepted. Apply unit; no `src/` change.
- Q6 (owner, 2026-11-06 11:03:01 UTC): "fine like this", after the owner's own direction (10:59:41): measure all that
  are useful, each marked "firmware-change potential" or "attention". Part N rows get "bound" or "attention" (one word,
  Margin column). Bound (9): boot unfed stretches 1-2 (step 12a), supervisor scan (new zero-wear device script), I2C
  timeout ceiling 200 ms (10c), con.routine_stall 21 ms (loop_stretch_timing.py), head limits 32 lines / 2,048 B
  (new bench capture of real client heads), UART poll 2 ms / idle 50 ms (12b); before the wear steps' cleared: line.
  Attention (19): rungs 2/3/4, emergency buffer 100 B, 8 test budgets, 7 CI values: set from existing bench logs and
  CI history (one read-only unit). Choices (4): LED wait 120 s, web backoff 60 s, device watch 60 s, clock mismatch
  5 s: relabelled "choice", no measurement owed. Two non-number records (the rule row, the scenario duplicate).

## Also for the apply unit (the diagnosis's decisions, owner, 2026-11-06)
- W65 (11:12:17): stays for every invalid SGP40 backup read, an erase and a first boot included, once per boot/task
  start (as the code does). SPECIFICATION.md :444-445 and :3664 state this exception with the ruling. No src/ change.
- 413 body cut (11:16:57): test fix only (done in the test-fix unit). No drain in `_serve()`.
- Overflow record (11:30:32, A): `_log_dead_task()` writes `_RR_STACK_EXHAUSTED` (20) before its awaited entry when the
  ended task's exception is the C-stack overflow; a unit test with the logger blocked; Part F.1 one sentence; the
  stack device script gains an escape mode (overflow not recorded by a handler) expecting 20 on silicon.
- WLAN console lines (12:09:55, A widened): print on every change of connection state, once per change, never per
  pass: "WLAN connection established" plus its diagnostics on entering a connection, "No WLAN connection" (and any
  other state line the loop repeats) on leaving it; `_conn_phase` already tracks the state. A unit test asserts one
  line per change across several passes in each state. Console only, no FRAM entry changes.
- Q7 (owner, 2026-11-06 12:20:58 UTC): no owner choice seen ("technically qualified and required ... so I do not see
  any choices here"). Recorded as technical decisions (agent), kept as built; retag the Q7 records accordingly. Lead's
  lesson for Q8-Q11: bring only items whose outcome shows in operation, worded as what it means there.
- Q7 addendum (owner, 2026-11-06 12:31:01 UTC): "You actually should do a wrap-up of free heap at the end. 60k left
  from105k must have some solid explanation." Last-round item: a measured heap account on the final image, stage by
  stage (boot entry, imports per module, build_system(), each setup, task start, idle under main.py, peak under the
  connection ceiling), reconciled line by line with the September 105 KB reading (87.8-88.0 KB allocated after the
  build, no setups) and with yesterday's 128.4 KB; inferred parts replaced by readings. It settles Part N's
  web.serving_demand_budget_b and the owner's 100,000 B after-build bound (2026-10-02), which yesterday's figures
  exceed; any change to either goes back to the owner.
- Q8 (owner, 2026-11-06 12:45:47 UTC): "ISL sensor: keep as is." The ISL29125 config stays checked only after a failed
  write and on a REST config read (the question's "every read cycle" was wrong, FINDINGS 12.62); brownout is caught
  every cycle through STATUS. The rest of Q8 stands as recommended (accept as is; calibration constants stay Part N
  rows, open to change). Apply unit: correct Q8's sentence wherever the records repeat "compared every read cycle".
- Q9 (owner, 2026-11-06 12:57:09 UTC): "Option A, keep." mDNS, ping and IPv6 stay on as built. The rest of Q9 accepted
  ("all good"), except the stale-time flag's polarity, asked back: /status `system.TimeStale` (buildgen/codegen.py:298,
  definitions.py:655) is `networking.NTPSynced` (codegen.py:281, definitions.py:619, "NTP Synced") inverted, with null
  until the clock is set this boot. Lead's answer put to the owner: keep, invert it into a synced flag, or drop it and
  let NTPSynced carry it (UnixTime null already says the clock is unset).
  Owner 13:01:01, B: "Option B, that is fully sufficient." (also: "overkill / bloat added without my explicit
  understanding"). Apply unit: remove system.TimeStale (codegen.py:287,298; definitions.py:655-657; its two tests_js
  checks; SPECIFICATION.md :1085-1094 and :6359; mockdata/samples.json; digital_twin/README.md:723; the twin CI
  suite's Run 1/Run 8 checks (scripts/_digital_twin_ci_suite.py:1126-1127, :1483-1484), which move to NTPSynced; tests/
  _sensortask_scenarios.py:3511-3527; tests_scripts test_buildgen_definitions.py:386-388, test_buildgen_generate.py:348-
  364, test_digital_twin_ci_suite_errcount.py:922; the lead told the owner a smaller list at 12:5x, corrected) and give the "NTP Synced" row the drifted-times note; the October
  wish ("a flag in /status showing it might be stale") is served by NTPSynced (owner, 2026-11-06).
- Q9 follow-up (owner 13:06:07, "doubled internally?"): no; TimeStale is computed per /status request, no variable.
  Three clock states, each distinct (_utc_valid, NTP Synced, _clock_valid); the lead recommended keeping them.
- Q10 open (13:11:42 the owner asked what "the catch around each web request" means). Fact: it is not around each
  request; src/asy_api_response.py:65-72 catches a raising post-write hook (WiFi reconnect, NTP force sync; buildgen/
  validate.py:111,113): the PUT answers with the changed fields "Failed" and logs CALLBACK, instead of Microdot's bare
  500 after the values were saved. Its recorded reason (agent, 2026-08-03, "prior field experience with Microdot
  behaving unexpectedly", tests/test_asy_api_response.py:183) names no incident; apply unit replaces it with the real one.
- Q10 (owner, 2026-11-06 13:17:14 UTC): "Question 10: Keep all of it". Section switch lets the in-flight GET finish;
  2 default decimals; the post-write hook catch kept, its recorded reason replaced by the real one (apply unit); the
  rest technical, as built.
- Q11: recorded as accepted, not asked (46 code-convention and build-chain choices, none visible in operation); the
  owner is told and can object.
- Q11 (owner, 2026-11-06 13:27:49 UTC, after seeing it at 13:19:17): "Q11: All accepted." Go for the apply work (same
  message): "A, all now": the firmware unit and the records-and-twin unit in parallel, plus the read-only attention
  unit.
