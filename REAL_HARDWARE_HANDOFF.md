# REAL_HARDWARE_HANDOFF.md

**STATUS: WAITING FOR GO-AHEAD.** If you are a Claude Code session reading this file: reading it is
fine at any time, but do not run anything against real hardware because of it - no `mpremote`
command, no `nmcli`/`iw`/`iptables` call, no `picotool`, no `scripts/run_flash_hardware_suite.sh`/
`run_bench_hardware_suite.sh`/`run_manual_hardware_tests.sh` invocation, not even a "just to see if
it works" dry run - until the project owner has explicitly told **you, in this conversation**, to
start the real-hardware integration described here. A go-ahead given to a different session, or to
an earlier session that already ended, does not carry over - if there is any doubt whether you have
it, ask first rather than assume.

Temporary handoff doc, same lifecycle as `HARDWARE_TEST_PLAN.md`/`tmp_hardware_test_candidates.md`
(see `README.md`'s "Further reading"): **delete this file once the real-hardware integration it
describes is complete and verified**, migrating anything still permanently true into
`tests_hardware/README.md`/`SPECIFICATION.md`/`BACKLOG.md` first - don't just delete it once things
run, fold forward first, per this repo's standing "resolved items move into a permanent doc, not
silently dropped" convention (CLAUDE.md's "Working agreements").

## Why this file exists

`tests_hardware/` (65 automated `pytest` tests across a flash tier and a bench tier, plus a
structurally separate 12-test manual runner) was designed and implemented on branch
`claude/unit-tests-future-ideation` (GitHub PR #52, based on `claude/digital-twin-oserror-7y00lb`)
by a cloud session with **no board or bench rig attached at all**. Every test is
collectible/lint-clean/type-correct, cross-checked against real driver source and datasheets where
possible, and re-audited twice for wrong claims (see `tests_hardware/README.md`'s own "mistakes
found and corrected" sections) - but **literally none of it has ever executed against real
hardware**. That gap is exactly what this handoff is for: a session running locally, on the actual
bench machine, with `mpremote`/the bench WiFi bridge/real boards already reachable the way no cloud
session ever can be.

**Your job, once given the go-ahead**: actually run this tier, find out what real hardware
disagrees with, fix what should be fixed, flag what needs the project owner's judgment, and report
back - not just "did it pass" but what you found, the same standard of honesty the two review
passes on PR #52 already set (grep-only claims turned out wrong twice; read real source in full
before asserting anything about it, exactly like `tests_hardware/README.md`'s own corrections had
to do).

## Before you start (once given the go-ahead)

1. Confirm you're on the branch this content has actually landed on (`claude/digital-twin-oserror-
   7y00lb`, once PR #52 merges into it - check with the project owner if unsure which branch/commit
   to be on) and that it includes the tier: `ls tests_hardware` should show `flash/`, `bench/`,
   `manual/`, `harness.py`, `bench_control.py`, `http_client.py`, `conftest.py`, `README.md`.
2. **Read `tests_hardware/README.md` in full.** It is the durable technical reference this file
   deliberately does not duplicate: prerequisites (`env --tier flash`/`--tier bench`), environment
   variables (`MPREMOTE_DEVICE`, `BENCH_AP_PASSWORD`), the exact run commands, and - critically - a
   checklist of every mechanism flagged as unverified during implementation, plus the two "mistakes
   found and corrected" write-ups (the SCD30 RDY-pin finding and the second re-audit's findings).
   Everything in this handoff assumes you've read that file; it isn't repeated here except where
   the stakes are high enough to restate.
3. Skim `HARDWARE_TEST_PLAN.md` §11 (the hotspot role-reversal scenario) - the single most complex
   and highest-risk piece of this tier, both technically and in terms of what a mistake could cost
   (see the safety facts below).

## The critical safety facts (read these even if you skip everything else)

- **`picotool` in the sandbox that wrote this tier had no USB support** (confirmed directly: its
  own `--help`/`version` output said so). Before anything that calls `picotool load` - the
  automated `test_real_uf2_reflash_and_boot_smoke_test` and the manual
  `first_ever_uf2_flash_of_a_blank_board` - confirm your local `picotool` actually has USB support,
  or rebuild/reinstall one that does.
- **A real UF2 reflash is gated behind `--allow-flash-cycle` and is a genuine flash cycle** - this
  project's own hard constraint is at most one flash to provision a board, ever, plus this one
  deliberate re-provisioning path (`HARDWARE_TEST_PLAN.md` §6.1). Don't pass that flag, or run the
  manual first-flash test, as part of a routine pass - only when you've deliberately decided a
  re-provisioning flash is warranted.
- **A failed stage-6 real-credential PUT in the hotspot role-reversal scenario can permanently
  strand the DUT** until a physical power-cycle. Confirmed directly against
  `src/asy_wifi_service.py`: by that stage the DUT has necessarily already been in hotspot mode
  since stage 0, so a failed real STA reconnect lands in `_PHASE_DEACTIVATED`, a terminal state
  only a real power-cycle clears (a deliberate safety feature - `SPECIFICATION.md` Part A.4, not a
  bug). `test_hotspot_role_reversal.py`'s own `joined_hotspot` fixture already recovers from this
  automatically via `hard_reset()` - if you see that fire, recognize it for what it is (a
  designed-for recovery path, not a new failure) rather than being alarmed by it.
- **`BENCH_AP_PASSWORD` must be set** (env var) for the real-credential-handoff test in the
  role-reversal scenario to actually run rather than skip cleanly -
  `toolchain/setup_toolchain.py`'s `ensure_bench_bridge()` never re-prints the bench AP's password
  on an idempotent re-run, so you need it from whenever the bridge was first created, or reset the
  bridge to generate a fresh one if that's acceptable.
- **Long-duration soaks (`--run-long-soak`, up to ~12.4 days for the real `ticks_ms()` rollover
  test) and the flash-cycle test (`--allow-flash-cycle`) are opt-in and skipped by default** - don't
  add these flags to what should be a routine run without deciding deliberately, this session, that
  you want them running.
- **`bench/test_network_resilience.py`'s NTP/DNS garbage-response tests use a real `nat` table
  PREROUTING DNAT rule** (`bench_control.py`'s `redirect_udp_port_to_local()`) to hijack UDP 123/53
  traffic to a local rogue responder - flagged there as unverified against a real NetworkManager-
  managed bridge (same caveat as `own_ip_on()`/`gateway_ip()`). If a test using it is ever killed
  mid-run, check for a stray `iptables -t nat -L PREROUTING` rule tagged
  `sensors-bench-fault-injection` and remove it by hand (`clear_udp_port_redirect()`'s own args) -
  a leftover rule would otherwise silently break real NTP/DNS for every subsequent run.
- **Every fault-injecting test resets the real `/status` error/warning history before and after
  itself** (`PUT /status {"ResetErrors": true}`, via `error_log_helpers.py`) - if any such test is
  ever killed mid-run, the board's live error history may be left showing that test's own
  deliberately-provoked fault. Not a correctness risk (a stale entry doesn't affect the running
  system), but worth a manual `PUT /status {"ResetErrors": true}` before treating the error history
  as a clean baseline for anything else.
- **A real, not-yet-root-caused WiFi reconnection flakiness was found on the bench unit before this
  tier existed** (intermittent hotspot fallback after a hard reset, ~2/5 boots in an earlier
  session) - fold chasing it down into this tier's real-hardware work rather than treating it as a
  separate task. Full details and the tests to use for it: `tests_hardware/README.md`'s "First real
  run" list.
- **`bench/test_sensor_config_push_over_real_hardware.py` mutates the board's real, persisted
  BMP3xx config** (PressOvers/TempOvers/FiltCoeff) and restores the original values in a `finally`
  block. If that test is ever killed (Ctrl-C, a crash, a `--timeout` kill) between the PUT and the
  restore, the board is left with non-default oversampling/filter settings - check `GET /sensors`'
  BMP3XX fields against this repo's own defaults (PressOvers=1, TempOvers=1, FiltCoeff=0,
  `asy_bmp3xx_driver.py`'s `_VAL_POV`/`_VAL_TOV`/`_VAL_FC`) if this test is ever interrupted, and
  restore by hand via `PUT /sensors` if so.

## Suggested run order

**This section describes the original, never-yet-started order.** Real-hardware execution is now
under way - **read `REAL_HARDWARE_RUN_LOG.md`'s "Next session should start here" list for the
current, up-to-date next step** rather than restarting from item 1 below. Kept here for the general
shape (fast/no-network first, longest/highest-risk scenario watched closely, opt-in soaks/flash-
cycle last), which still holds even though the specific starting point has moved on:

1. `scripts/run_flash_hardware_suite.sh -v` - fast, no bench/WiFi needed, confirms basic
   `mpremote`/board access works before anything more elaborate. Fix or report anything that fails
   here before moving on - a flash-tier failure likely points at something more fundamental
   (provisioning, `mpremote` connectivity, the board itself) than a bench-tier failure would.
2. `scripts/run_bench_hardware_suite.sh -v` - needs `env --tier bench` already set up (see
   `tests_hardware/README.md`'s Prerequisites). This also re-runs the flash tier (bench ⊇ flash).
3. `scripts/run_bench_hardware_suite.sh -v -k hotspot_role_reversal` on its own once, watching it
   closely the first time - it's the longest, most involved scenario, and the one carrying the
   real power-cycle risk noted above. Confirm `BENCH_AP_PASSWORD` is set first (see above) or the
   real-credential test will skip rather than exercising stage 6 at all.
4. `scripts/run_manual_hardware_tests.sh --list`, then work through the manual tests
   (`--only <name>` or a full unattended-by-design-impossible run) at your own pace - these need a
   human physically present regardless of anything else.
5. Long-soak tests and the flash-cycle test last, and only once you've decided deliberately, this
   session, to run them.

## What to do with what you find

- **A test fails because the test itself is wrong** (a bad assumption about real hardware timing,
  a wrong constant, a mistaken read of driver behavior - exactly the shape of mistake the two
  review passes on PR #52 already found and fixed twice): fix the test, following this repo's own
  testing conventions (`tests_hardware/README.md`, `HARDWARE_TEST_PLAN.md`), and read the *real*
  source in full before asserting anything new about it - a narrow grep is exactly what caused the
  first mistake.
- **A test fails because it found a real bug in `src/`**: flag it, don't fix `src/` blind without
  fully understanding it first - the same standing practice as everywhere else in this codebase
  (CLAUDE.md's hard rules, e.g. the `modules/_boot.py` import-mechanism rule).
- **A test's own design assumption turns out wrong in a way that needs a judgment call** (not just
  a constant tweak - e.g. one of the items already flagged "needs verification on first real run"
  in `tests_hardware/README.md` resolves in a way that changes the test's own design): flag it to
  the project owner rather than guessing, the same as any other architecturally significant
  decision (CLAUDE.md's "Working agreements").
- **Once a real-hardware pass is genuinely representative** (not necessarily 100% of all 65+12
  tests on the first try - long-soaks and the flash-cycle test are opt-in for a reason, and a
  first pass finding real things to fix is expected, not a failure of this plan): tell the project
  owner, then migrate anything from `HARDWARE_TEST_PLAN.md`/`tmp_hardware_test_candidates.md` that's
  still permanently true into `SPECIFICATION.md`/`BACKLOG.md`, delete both those files plus this
  one, and update `README.md`'s "Further reading" section accordingly - the same close-out sequence
  every other temporary planning doc in this repo has already followed.
