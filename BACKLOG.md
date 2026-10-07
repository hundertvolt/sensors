# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

**Everything that needs the dev bench is gathered in "Real-hardware work still owed" below**, so a
go-ahead session can work it in one pass; `tests_hardware/README.md` stays the reference for how.

**The numbered list below has gaps, and its numbers are never reused or renumbered.** Code comments
and `SPECIFICATION.md` cite items by number, so a resolved item whose number is cited stays as a
short closed stub saying what the answer was (items 1, 5, 6, 9, 12 today); one whose number nothing
cites is deleted outright, its permanent content migrated per the policy above. A gap therefore means
"resolved and removed", never "lost".

## Refactor targets not yet done

- **Mypy shall be configured to disallow `Any` types** (owner-specified). Mostly addressed, but
  not by the flag it was originally written about: all three passes now run full `--strict`
  (`disallow_any_generics` included), so no *implicit* `Any` from a bare `dict`/`list`/`tuple`
  survives anywhere in scope. **Deferred to a dedicated future session (project owner, 2026-09-11)
  - not to be picked up as part of unrelated work.** **None of this is a pipeline finding** -
  `disallow_any_explicit` is *off* in all three configs, so lint/typecheck/CI are green; the counts
  below are what would appear if it were switched on. Re-measured 2026-09-11: **224 in the main
  `src`+`tests` pass** and **115 in the host pass** (up from the 17 recorded before
  `tests_hardware/` joined that scope);
  `digital_twin/` was not re-measured, previously 45. Plus `disallow_any_unimported` (54, main
  pass only). Explicit `Any` appears 107 times in `src/` and 213 in `tests/`. A large share of the
  test-side uses are monkeypatch/wrapper classes duck-typing a real MicroPython object; the `src/`
  side is largely legitimate (`asy_print_log.py`'s variadic logging methods, `asy_config_manager.py`'s
  generic value-checking helpers, opaque `ticks_ms()`-typed values). Turning `disallow_any_explicit`
  on still needs a typing strategy for the test wrappers (e.g. `Protocol` classes + `__getattr__`
  delegation) and a decision on the genuinely-variadic/opaque `src/` cases - not just a flag flip.
- **FRAM's `verify_present()`/`set_write_protected()` stay in `src/` (owner, 2026-09-26: 'So they
  remain as they are.'; decided earlier more than once).**
  They have zero callers in `src/` today and that is fine: "zero callers now, maybe callers
  tomorrow" is the whole point, and both are bus-hazard-tested across all four tiers and confirmed
  correct under real fault injection (CLAUDE.md's bus-hazard hard rule). The project owner has
  decided this more than once; it is not an open design question, and no future session should
  re-propose removing them or ask again who is supposed to call them.
- **The full test-suite scan for tier/layering-completeness and wrongly-trusted-hazard tests
  (owner, 2026-09-15; important to apply, no ordering — owner, 2026-09-29: 'It has no priority in
  terms of order now, it's only highly important to be applied.') has now run once, beyond
  bus-hazard's own corner** — UART, WiFi/network/NTP/DNS, FRAM/memory/reboot/watchdog, and
  webserver/notification/config-push were all swept, real call chains traced end-to-end rather than
  grep-counted. Full account, including what was fixed, what's a confirmed structural exception, and
  what's named-but-not-fixed (needing either a dedicated real-hardware session or a project-owner
  design decision): `tests_hardware/README.md`'s "Tenth pass". No second instance of the
  SGP40-shaped bug (a real hardware trigger silently substituted with a software-only one) turned
  up, but several real tier-parity gaps did, most now closed. Settled: the mock tier's ~20-scenario UART fault-injection catalog is a structural
  exception until injection hardware exists (2026-09-22, SPECIFICATION.md E.6.6 row
  `uart-fault-catalog`); the
  shipped-driver F.5.8 test exists (2026-09-25); the exerciser SET and the NOTIFY FRAM-recovery test
  are scratched, each needing a `src/` change for the test alone (owner, 2026-09-25). Re-running
  this sweep against other domains (it did not touch e.g. sensortask/asy_system_service integration
  beyond what FRAM/memory covered) is future work, not assumed done everywhere.

## Open questions (need owner input or further investigation)

- **ISL29125's chip configuration divergence under concurrent API load (found by `679c2b0`'s
  isolation work (agent, 2026-09-15); the owner rated that work's two defects 'HIGH IMPORTANCE and
  must-fix' (owner, 2026-09-15, `679c2b0`, paraphrase)) — fixed,
  unit-tested and confirmed on silicon; only the `Overrange` half below still owes a run.** Root cause, traced through
  the real code: `ISL29125_I2C.configure()` mutated the in-memory shadow fields
  `encode_shadow()`/`matches_shadow()` read (`self._mode`, `self._range_fs`, `self._resolution`,
  ...) *before* it ever acquired the per-sensor device-session lock that SPECIFICATION.md Part C.8
  documents as what serializes "a multi-transaction sequence against another coroutine starting its
  own sequence on the same sensor" — only the actual wire write was ever inside that lock. Under
  real concurrent load (`_read_loop()`'s own background reads/`_switch_range()` calls, or a second
  concurrent request) that lock does get contended, so a `configure()` call could be suspended
  *after* mutating the shadow but *before* its write reached the chip, letting a concurrent `GET`'s
  `get_config_snapshot()` + `matches_shadow()` observe the shadow already showing the new value
  against a chip that still held the old one — a false "diverged from the shadow" `ISL_DIVERGED`
  (`W31`) report with nothing actually wrong on the wire, which is why three quiet trials never
  reproduced it but 2 concurrent `GET` workers did (twice, per the original isolation). The existing
  mock test that looked like it should cover this
  (`test_concurrent_read_and_write_never_interleave_on_the_wire`) only ever proved wire-level
  atomicity, never this shadow-vs-chip timing race. **Fixed** by widening the device-session lock in
  `configure()` to span the whole validate-mutate-write(-rollback-on-failure) sequence, matching
  Part C.8's own documented intent (`_write_shadow()` renamed `_write_shadow_locked()`: no longer
  self-locking, the caller now holds the lock for the whole critical section). Regression test:
  `tests/test_asy_isl29125_driver.py::test_configure_never_exposes_the_shadow_ahead_of_a_write_still_in_flight`
  holds the exact lock `configure()` needs (standing in for real contention) and confirms the
  shadow cannot change while `configure()` is blocked waiting for it. **Confirmed on silicon**: the
  first fully clean bench tier after the fix (`HEAP_FRAGMENTATION_MEASUREMENTS.md` archive §7H.6),
  and every bench tier of 2026-09-24/25 since, ran the concurrent load that used to produce it.
  **Still open, R9's other half**: the `Overrange` field below has never run on silicon
  (`device_scripts/isl29125_mechanism_envelope.py` reads it instead of the retired saturation
  warning); it rides S3b ("Real-hardware work still owed").
- **The sibling `W12` ("saturated on the high range") finding from the same isolation work is
  resolved differently, by design rather than by fixing a bug (project owner, 2026-09-15):**
  saturation status was never a fault, so it no longer lives in the error/warning log at all. It's
  now a live, mode-aware `Overrange` measurement field on `ISL29125` (`src/asy_isl29125_driver.py`):
  true whenever nothing left could mitigate the saturation — the configured range itself under
  Fixed range (nothing will ever switch it), or Automatic Range already parked on its highest
  setting with nowhere further to go. This structurally can't fail an error-log-empty bench
  assertion again, and closes a real pre-existing gap the old warning never covered: a saturated
  *fixed low-range* reading used to go unreported entirely (the old condition only ever checked
  `sample_range == _RANGE_HIGH_LUX`). Covered by three new/updated tests in
  `tests/test_asy_isl29125_driver.py`; `tests_hardware/device_scripts/isl29125_mechanism_envelope.py`
  updated to check the field directly instead of the retired saturation warning (also pending
  real-hardware re-run). The field reaches the website from its `@web` tag, and
  `mockdata/samples.json`'s ISL29125 sample carries it.

1. `legacy/firmware/modules/_boot.py`'s `import sensortask.py` (literal `.py`) - **mechanism
   answered; the file is never changed regardless.** Kept only because CLAUDE.md's own hard rule and
   `tests_hardware/flash/test_reboot_persistence.py` cite this number. Traced through the pinned
   source at 1.28 and re-verified at 1.29.0 (`tools/mpy-tool.py`'s frozen-name generation,
   `py/frozenmod.c`'s exact-match lookup, `py/builtinimport.c`'s `stat_module()`/
   `process_import_at_level()`): a plain `import sensortask` is unambiguously the correct form, and
   the dotted one *should* raise, because it needs "sensortask" to resolve as a package. Why it
   nonetheless works on the legacy units' 1.24.1 firmware was never verified against that version's
   own import machinery; a test would run on one of the owner's legacy units as the owner's
   operation, never on the dev bench (owner, 2026-09-26). Nothing to do on the refactor side either:
   `buildgen.codegen.generate_boot_entry_source()` already emits the correct
   `from sensortask_wozi import main`.
2. Config-schema migration is a real data-loss risk on the *current deployed* codebase —
   `ConfigManager` overwrites the entire config file with hardcoded defaults the moment one key is
   missing, so a firmware update adding a config key could silently wipe WiFi credentials/tuned
   values. No legacy config migration: legacy units get fresh setup at reflash (owner, 2026-09-26);
   from the release on, a renamed key or file needs a migration, pinned by a golden stored-config
   fixture (owner, 2026-09-26).
3. MicroPython version target vs. upstream drift — the owner's legacy units run 1.24.1 (owner,
   2026-09-26); the refactor pins 1.29.0. A legacy unit moves to the refactor only by the owner's
   reflash with fresh setup, following the reflash runbook; no config migration code is written
   (owner, 2026-09-26). The refactor is where the version target moves forward. The full 1.28→1.29
   audit is in SPECIFICATION.md Part F.5 (two real findings, several free wins, the rest ruled out);
   the toolchain builds `RPI_PICO_W` firmware at 1.29.0 from scratch with no patches. Earlier
   1.27→1.28 rp2-port changes were RP2350-specific, not RP2040-breaking. Re-run F.1's standing
   re-check whenever the pin moves again.
4. Does `asy_config_manager.py`'s `write_config()` need long-block-lock-style coordination? **No**
   (owner, 2026-08-11, `acc4993`): the deferred flush (owner, 2026-09-16, `9ac59cf`) stages a write
   and flushes it later, so a write no longer holds a live request (SPECIFICATION.md F.2); and a
   write never happens on its own (only ever triggered by a real user interaction via the REST
   layer), which also matters separately for not wearing out the flash with unnecessary writes. No
   coordination mechanism needed. **Note**: `get_long_block_lock()` itself was already removed
   entirely before this was decided (see CLAUDE.md's "Long-blocking operations" hard rule) — this
   decision doesn't resurrect it.
5. ~~Real-hardware verification gap for `asy_udp_socket.py`/`asy_captive_dns.py`~~ - **closed
   (2026-09-08, real bench hardware).** Kept as a stub because `tests_hardware/README.md`,
   `bench_control.py` and two bench test files cite this number. All three UDP-layer claims are
   confirmed on real rp2/lwIP: garbage-response robustness and truncation; connected-socket
   source-address filtering (**holds** - real OS/lwIP enforcement, a forged reply never corrupts the
   DUT's RTC); and POLLERR/POLLHUP delivery (**never observed** - `UDPSocket.ready()`'s handling
   is correct but effectively dead code on this platform). Technique, results, and the bench-harness
   gap the pass also closed (`start_udp_source_capture()`, a real `tcpdump` capture, replacing a
   DNAT redirect that does not deliver locally at `route_localnet=0`): `tests_hardware/README.md`'s
   "Fourth pass" and "Known assumptions and open findings".
6. ~~Should `asy_wifi_service.py` gain an independent WiFi reachability check?~~ — **closed
   (2026-09-08): investigated, no `src/` change.** The CYW43 firmware/lwIP stack can silently mask a
   real link disruption from `wlan.isconnected()` entirely; decided, with full upstream research
   citations, real bench-hardware recovery-timing data, and regression coverage, in
   `SPECIFICATION.md` Part F.2 - that Part is now this item's complete, permanent, self-contained
   home. Kept here as a closed stub, at its original number, only because several `tests/`/
   `tests_hardware/` code comments still cite it as "BACKLOG.md open question 6" - don't renumber
   this item while those references exist.
8. **Two bench-rig capabilities would each move one test candidate from `[MANUAL]` to `[AUTO]`
   (owner, 2026-09-22, `d0bfbca`: no hardware will be bought for this): both candidates stay
   `[MANUAL]`.** Not "planned for later" any more, which is how
   this read from 2026-09-11 until the question was put again. One qualifier, from the same
   sitting's answer about the UART fault catalog (SPECIFICATION.md E.6.6 row `uart-fault-catalog`):
   fault-injection hardware may arrive one day for that work, and if it does, the GPIO half below
   is worth re-opening then — as a new entry, not by treating this one as still pending. A programmable GPIO fault-injection
   harness (upgrades the "genuinely wedged I2C bus → watchdog backstop" test) and a dedicated
   second WiFi test client (upgrades the real end-to-end hotspot session; today's host has one
   adapter, already hosting the AP). Both stay `[MANUAL]` until the rig exists — and no
   software-only stand-in claims the same coverage (agent, 2026-09-22). Migrated
   from the deleted `HARDWARE_TEST_PLAN.md`; surrounding architecture in SPECIFICATION.md Part E.6.
9. **WiFi-reconnect flakiness across the bench suite - root-caused and fixed at the root.** Kept
   as a stub because three `tests_hardware/` files cite this number. What looked like several
   unrelated symptoms was: a missing `BENCH_AP_PASSWORD` cascading into ~25 unrelated-looking
   failures (now defaulted from `bench.ap_password()`, which reads the real PSK live - no env var
   needed); a real association race in `join_dut_hotspot()` (now re-verifies live visibility before
   every retry instead of a blind sleep); a factually wrong `_configure_hotspot_ap()` comment plus a
   missing re-entry guard (both fixed, with mock-tier regression coverage); and one sibling test
   lacking the recovery fallback every other one had. The hard-reset recovery mechanism itself
   (`kick_all_stations()` + `hard_reset()`) was independently verified rock-solid (28/28 trials,
   ~9.1s each, zero variance) and was never a source of flakiness.
12. **Does `machine.soft_reset()` reset the RP2040 hardware counter `time.ticks_ms()` derives
    from? - ANSWERED on real hardware (2026-09-11): no, and the question was aimed at the wrong
    mechanism.** The counter is free-running hardware time and survives the soft reset `mpremote`
    performs on raw-REPL entry (two reads 3s apart: 25769 then 29136 ms). **The real hazard is the
    watchdog.** An `mpremote exec` stops `main.py`, so nothing feeds the WDT and the board takes a
    genuine *hard* reset ~8s later, which does zero the counter (measured: 1368364 then 5323 ms,
    12s apart). Acted on 2026-09-18 - `test_ticks_ms_real_2pow30_rollover` would have passed
    **vacuously within about two hours**, because the reboot alone satisfies `now < before`; a drop
    now only counts as a wrap when the previous read was already within two hours of 2**30
    (`_WRAP_FLOOR_MS`), so the ambiguity fails honestly instead. Kept as a stub because
    `tests_hardware/flash/test_bus_electrical_timing.py` cites this number. **Do not re-investigate
    the soft-reset semantics**; what remains is designing a measurement method that leaves the board
    running, which is G6 under "Real-hardware work still owed", not this item.
24. **`PUT /status {"ResetErrors": true}` costs a large, slowly-growing fraction of the product's
    own request ceiling. Now measured on real hardware; one question left.**
    `asy_webserver_service.py`'s `_put_status()` resets every registered error source, concurrently
    since the owner chose it (owner, 2026-09-26; every figure below was measured while it still reset
    them one after another), and each FRAM-backed one pays a real FRAM write; WP1/WP2/WP3 grew that set to 21 on `dev`. Two
    real ceilings bound it, both confirmed directly: the server aborts any request at
    `outer_cap_s = 15.0` (`asy_webserver_service.py:275`, via `asyncio.wait_for()` at `:667`), and
    the real web UI gives up at `DEFAULT_TIMEOUT_MS = 15000` (`js/poll-manager.js:8`). A device whose
    sweep crosses 15s is broken for its own operators, not merely slow in CI.

    **Real hardware, `dev` bench board, 2026-09-17, 21 FRAM-backed chunks** — the numbers that
    supersede every twin estimate below:

    | condition | wall clock | % of the 15s ceiling |
    | --- | --- | --- |
    | idle, real accumulated history | **6.32s** | 42% |
    | idle, repeated on already-empty logs | 6.40-6.62s | 43-44% |
    | via `reset_all_error_logs()` | 6.89-6.98s | 46% |
    | **3 concurrent `GET /status` workers** | **11.58s** | **77%** |

    Correctness confirmed alongside: HTTP 200, all 21 counters (`UART_init`/`UART_resp` included)
    read back 0 with every history ring cleared.

    **Three things this settles, two of which contradict what this item previously said.**
    **(1) The twin is not a floor.** Real idle (6.32s) is *faster* than the twin's own `dev` figure
    (8.151s) — the Unix-port interpreter plus the fake chip's Python-level work cost more than real
    SPI wire time saves. The "real hardware pays real clocking on top of it" claim here was wrong,
    and so was the ~10-12s extrapolation drawn from the boot-latency branch's delta calibration
    (`358c08f`); a staggered boot `setup()` genuinely does not predict a back-to-back write burst.
    **(2) The cost is fixed PER CHUNK (~305ms), not per history entry** — clearing 21 chunks holding
    real history costs the same as clearing 21 empty ones, consistent with the ~170ms-per-FRAM-logger
    `setup()` figure being paid roughly twice (a read+write pair). So the "~0.6s marginal per source"
    figure previously derived from the 4-source `dev`/`wozi` twin delta overstated it; that delta
    was never purely 4 chunks. **(3) The event loop is not blocked**: concurrent `GET /status` stayed
    0.56-0.76s throughout a `PUT` lasting 8.1s, so the 8388ms watchdog cap is not threatened — the
    time is yielded, not held.

    **The reader-count curve, real hardware 2026-09-25** (image `2026-09-25T05:21:43Z`, same 21
    chunks, three sweeps per point, readers re-requesting `/status` with zero think time — queue R2):

    | concurrent `GET /status` readers | wall clock (3 sweeps) | % of the 15s ceiling |
    | --- | --- | --- |
    | 0 | 2.31 / 2.43 / 2.43s | 16% |
    | 1 | 5.53 / 5.61 / 5.76s | 37% |
    | 2 | 8.80 / 10.57 / 11.03s | 59-74% |
    | 3 | 13.16 / 13.24 / 14.69s | 88-98% |
    | 4 | no result: refused 20x at the connection ceiling, then no answer within 30s | over |

    **What is still open — and it is the load case, not the idle one.** Idle is now far below the
    2026-09-17 figures, but the curve **does not flatten**: it climbs ~3.5s per reader, so three
    readers already reach 88-98% of the ceiling and four exceed it. The "~6 more chunks under load"
    headroom derived from the single 3-reader point no longer holds — under load there is none.
    At four readers the board is saturated outright (F18; the owner's decision on such clients is in
    SPECIFICATION.md H.7: ceiling starvation of the `PUT`, WEBSERVER `W49`/`W50` reclaims
    (`HTTP_CALL_TIMEOUT`/`HTTP_REQUEST_CAP`), UART link `E81`/`E22` (`UART_NO_ACK`/`TIMEOUT`) and
    resyncs). Nothing asserts elapsed time anywhere: both client timeouts
    are backstops placed against the cap (the CI suite derives `_RESET_ERRORS_TIMEOUT_S` from a
    mirrored `_SERVER_OUTER_CAP_S`; `tests_hardware/error_log_helpers.py` carries a measured 30.0s),
    and `tests_scripts/test_request_timeout_ceiling.py` enforces every copy against `outer_cap_s`
    itself — but a backstop is not a budget. **Where to fix**: an explicit elapsed-time budget, sized
    against the load case rather than the idle one, from the curve re-measured on silicon with the
    concurrent reset (its design fix, done); and if a future device's chunk count approaches ~27, a
    further design-level fix at the source (one shared chunk) rather than a larger client timeout,
    per CLAUDE.md's root-cause-don't-raise-the-limit rule.

    Twin figures kept only as the harness baseline they are (5 reps, idle host, loopback): `dev`
    8.151s (7.901-8.259) / `wozi` 5.592s (5.534-5.746) at the shipped `gc.threshold(32768)`, and
    7.396s / 5.207s at `gc.threshold(-1)`. Useful for spotting a twin-side regression; not a
    predictor of real-hardware cost in either direction.

29. **The spurious `WLAN_AUTH_FAILED` (`W36`, "WLAN wrong password") on a correct password -
    answered from source (2026-09-24).** Kept as a stub because `SPECIFICATION.md` C.7.1 and
    `tests/test_asy_wifi_service.py` cite this number. cyw43-driver reports BADAUTH, which
    MicroPython surfaces as `STAT_WRONG_PASSWORD`, for any failed AUTH event and any failed 4-way
    handshake other than three timeout codes (`lib/cyw43-driver/src/cyw43_ctrl.c`), so an AP
    vanishing mid-association reads as a wrong password; `_poll_sta_connect_status()` records it
    faithfully. Both sightings sat inside `WLAN_NO_AP`/`WLAN_CONNECT_FAILED` (`W37`/`W38`) runs. The
    log text now says what the status means, and the bench outage check accepts `WLAN_AUTH_FAILED`
    as benign beside `WLAN_NO_AP`.

32. **The bench tier's `ResetErrors` timeout was raised 10.0s → 30.0s with no elapsed-time budget
    to replace what that bound was incidentally enforcing.** Recorded 2026-09-17: a loosening with
    no compensating check.
    The old `10.0` was genuinely miscalibrated — it sat *below* the product's own
    `outer_cap_s = 15.0`, so a legitimate sweep (measured 6.32s idle, **11.58s under three
    concurrent readers** on the dev bench) failed as a client timeout before the server could abort,
    and the test could never observe the server's real behaviour at all. Raising it was correct.
    **But the twin got a compensating `_RESET_ERRORS_BUDGET_S` (12.0s, asserted per sweep by
    `_put_reset_errors_timed()`) and the bench tier did not.** `reset_all_error_logs()` passes the
    timeout and asserts nothing about elapsed time, so a sweep that degraded to, say, 25s on real
    hardware would now pass silently where the old bound would at least have gone red — for the
    wrong reason, but red.
    **Why no bench budget was set instead of recording this.** Sizing one needs the reader-count
    curve R2 measured on 2026-09-25 (0/1/2/3/4 readers, below). Two points did not
    say whether it flattens: the twin's 12.0s is already below the 11.58s-at-3-readers measurement
    plus any margin, so copying it across would flake the bench suite, and anything above ~15s
    cannot fire before the server's own abort. Both halves of the owner's standing requirement for
    this budget — "reliably won't fail the pipeline accidentally with a false positive" **and**
    "will reliably fail if something really went wrong" — are unsatisfiable until that curve exists.
    **The curve is taken (item 24's 2026-09-25 table), and it says no budget can meet both halves
    at the current design**: three readers already land at 13.2-14.7s against a 15s server abort, so
    any budget that never false-positives sits at or above the point where the server gives up
    first (R4 on 2026-09-25 measured 12.1-14.6s at three readers again, the worst 0.4s from the
    abort). The owner chose the concurrent reset (owner, 2026-09-26), and it has landed; the bench
    budget is set once the curve is re-measured on silicon with it. Then add the bench analogue of the twin's own budget check to
    `tests_hardware/error_log_helpers.py`.

44. **Board anomalies from the connection-limit sittings — recorded, not chased; each needs
    silicon** (HEAP_FRAGMENTATION_MEASUREMENTS.md archive §7R.5; row F17). A fourth, 2026-09-24: the
    USB serial dropped mid-upload of `uart_idle_poll_rate.py`; later resets overwrote
    `reset_cause()`, an isolated re-run passed, and two later full bench tiers did not reproduce it.
    - One silent reset in 1 of 9 instrumented peak-load boots, cause lost. Watchdog starvation is the
      first candidate to rule out: the supervisor loop is the only feed site (`asy_system_service.py`'s
      `feed_watchdog()`), and a board CPU-bound at ~2.2 requests/s can miss the 8,388 ms cap.
    - Hotspot fallback after a reset, three times. `devices/dev.toml`'s `conn_fail_to_hotspot = 5` is
      the mechanism that would take it there. **One instance is now measured (2026-09-25, F17)**: a watchdog reset with no `kick_all_stations()` before it gave `reset_cause()` =
      `WDT_RESET` and WIFI `WLAN_CONNECT_FAILED` (`W38`) ×5 (`STAT_CONNECT_FAIL`) — the
      stale-AP-station mechanism, cleared by a kick. Whether the earlier three were the same is not
      recoverable.
    - ~~A likely watchdog reset at `mpremote` attach~~ — **not an open anomaly: that mechanism is
      already measured** (item 12, 2026-09-11 — an `mpremote exec` stops `main.py`, nothing feeds the
      WDT, and the board takes a hard reset ~8 s later; the occurrence was ~9 s after attach). It is
      `tests_hardware/README.md`'s "> 45 s between a reset and the next attach" trap, not a finding.

## Real-hardware work still owed

Folded in from the retired `REAL_HARDWARE_TEST_QUEUE.md` and `HARDWARE_TEST_HANDOVER.md` after the
2026-09-24/25 sitting; row IDs (T4, S4, ...) are kept because commits and the whole-project audit
plan (on its own branch) cite them. **Nothing here authorizes anything**: CLAUDE.md's go-ahead gate
applies, and `tests_hardware/README.md` is the reference for how any of it runs (flags, wear
gates, traps).

- **How a sitting runs.** D1 and D2 are the owner's standing answers (owner, 2026-09-22, `00f3eac`,
  paraphrase — the commit records no owner words): D1, spend flash/NVM writes, but only after a
  clean default run, so a gated failure is the gated test's own; D2, the NeoPixel-aimed-at-ISL29125
  light rig is in place. D3 — always a `dev` build of the tree under test, never `wozi` — is
  CLAUDE.md's WoZi hard rule; confirming it at each sitting, and the order below, are the run sheet
  (agent, 2026-09-22): read and save `errcount` before anything writes (CLAUDE.md), build and flash,
  confirm `/system`'s `build.BuildDate`, flash tier, bench tier, then the gated run
  (`scripts/run_bench_hardware_suite.sh --allow-persistence-writes -s`), reading each verdict's
  deselected count, not only "clean". **Board state at the fold**: `dev` image
  built 2026-09-25T12:54:13Z (tree `851e816`), `max_connections = 6`, `DebugLevel` 5; its last
  runs were two clean default bench tiers and one clean gated run (2026-09-25).
- **Not yet confirmed on silicon.** (1) SGP40 `SGP_WRITTEN_NO_TS` (`W35`) spends one slot per run
  of untimestamped backups (`83c9920`'s episode rule on the board's image, the central newest-entry
  rule in `asy_print_log.py` since): no run since has kept NTP away past `SGPWaitTimeNTP`, so none logged
  one. Zero-wear check: block UDP 123 longer than that, expect one `W35` with `ErrCount` rising per
  backup. (2) The flash tier's watchdog-starvation test ending with `hard_reset()` (`79eb41b`,
  test-only, no reflash needed): no full flash-tier run since. Before it, the flash tier always left
  the board parked at the REPL with no watchdog, because the test attached within ~1 s of boot.
- **M1 + S3b, the ISL29125 light programs** — needs the owner at the bench, ~30 min. M1 first
  (`scripts/run_manual_hardware_tests.sh --only isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry`,
  interactive: repeatability on an unchanged scene, continuity across the range switch, and writing
  down the rig geometry S3b depends on; the reference light meter is an optional data point, never
  pass/fail), then `scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep` (~10 min). R9's
  `Overrange` half rides S3b (open question "ISL29125's chip configuration divergence" above).
- **R13 + N3, UART `wrnno` 54 (`UART_DRAIN_BOUND`) against a real babbling peer** — needs hardware
  the bench does not have (owner, 2026-09-25): the live firmware owns both UARTs, so nothing on the
  board can play the peer. Confirm `GET /status` shows `W54` for `UART_init`/`UART_resp` after the
  drain hits its bound, and that a boot drain against the same peer persists nothing
  (SPECIFICATION.md C.7.1). N3 also owes a check that `UART_C_PORT_CHANGELOG.md` records the
  reclassification (receiver-side only, no emitted bytes change). Low urgency: the mock tier covers
  the logic.
- **T4 — the FRAM per-block hold stays** (owner, 2026-09-26: 'Probably better to keep';
  SPECIFICATION.md F.5.8). Measured 2026-09-25: a 1-byte write holds the loop 2.8-3.4 ms without
  yielding (~0.6-0.7 ms per CS command). The command-envelope timing script below is its only copy,
  until it becomes a committed device script or is deleted. Run it
  with `scripts/mpremote_connect.sh exec "import machine; machine.WDT(timeout=8000)"` then
  `scripts/mpremote_connect.sh run <file>`; it writes at the top of the address space and never
  calls `get_chunk()`, so production's error logs are safe:

  ```python
  """Times the real SPI wire cost of one command envelope and one whole block operation."""

  import asyncio
  import time

  import asy_spi_driver
  from asy_fram_manager import FRAMManager


  async def _main() -> None:
      spi0 = asy_spi_driver.SPI(0, 2, 3, 4)
      fram = FRAMManager(spi0, 5, max_size=0x40000, debug=None)
      if not await fram.setup():
          print("RESULT: FAIL fram.setup() failed - real chip not responding on spi0/cs5")
          return
      chip = fram.fram
      addr = 0x3FF00  # top of the address space, clear of every production chunk
      one = bytearray(1)
      eight = bytearray(8)

      # (a) the synchronous, non-yielding stretches, bus already held.
      async with chip:
          t0 = time.ticks_us()
          w_status = chip.set_values_sync(one, addr)
          t1 = time.ticks_us()
          r_status = chip.get_values_sync(eight, addr)
          t2 = time.ticks_us()
      write_us = time.ticks_diff(t1, t0)
      read_us = time.ticks_diff(t2, t1)
      if not await chip.report_set_values(w_status):
          print("RESULT: FAIL the 1-byte write reported a failure status")
          return
      if not await chip.report_get_values(r_status):
          print("RESULT: FAIL the 8-byte read reported a failure status")
          return

      # (b) the bus-lock hold: entry to exit, yields inside it included.
      t3 = time.ticks_us()
      async with chip:
          for _ in range(4):  # a block operation's own command count
              chip.set_values_sync(one, addr)
              await asyncio.sleep(0)
              chip.get_values_sync(eight, addr)
              await asyncio.sleep(0)
      hold_us = time.ticks_diff(time.ticks_us(), t3)

      print(f"HOLD write_5cs={write_us}us read_1cs={read_us}us block_operation={hold_us}us")
      print(f"RESULT: PASS longest non-yielding stretch {max(write_us, read_us)}us, bus held {hold_us}us")


  asyncio.run(_main())
  ```
- **Give ad-hoc bench scripts one helper that kicks the AP's stations and then resets.** Every
  hotspot fallback of the 2026-09-25 sitting was a reset without `kick_all_stations()` *immediately*
  before it; kicking 50 s early does not help, since the board re-associates in between.
- **The two unfed boot stretches, measured** — a `dev` boot log with a `ticks_ms()` stamp at every
  watchdog feed, taken in a hardware session (zero wear): the stretch from `WDT()` to the first setup
  feed, and from the last setup feed to the supervisor's first, each expected well inside the 8,000 ms
  timeout. It replaces the estimates in Part N `boot.unfed_stretch_1_ms`/`boot.unfed_stretch_2_ms`
  (SPECIFICATION.md) and checks the L1 boot-stretch scenario's sleep sum.
- **What SCL and SDA do on silicon during an I2C bus recovery** — on `dev`, with a slave holding
  SDA low mid-byte: the line levels through `I2C.recover()`'s clear and its re-construction
  (pico-sdk's `i2c_init()` resets the whole block, SPECIFICATION.md F.5.1), and through the
  constructor's boot clear. Expected: the held slave releases SDA within the nine pulses, the STOP
  is on the wire, and no sibling sees a stray START while the controller is rebuilt. Zero wear; it
  confirms the twin's bus-recovery case (`tests/test_digital_twin_bus_hazard_concurrency.py`). Needs
  a device script that holds SDA, which the flash tier does not have.
- **Still owed elsewhere in this file**: R2's `ResetErrors` curve feeds item 24's design fix and
  item 32's bench budget; S4, the real 6 h soak ("Real-hardware re-test of the segfault fix" below);
  G6, a rollover method that leaves the board running (item 12, adapt now, measure later by
  decision); H1, the owner's two-chroot run (the chroot entry below); F17, item 44's anomalies.
  Excluded on purpose: G10, the UART protocol against its C implementation (post-audit only), and
  the two unbought bench-rig capabilities (item 8).

## Deferred / explicitly out-of-scope work

- **A transient SPI RX overrun is not retried (owner, 2026-09-24).** MicroPython 1.29's
  `OSError(EIO)` on 32+ byte rp2 SPI reads (SPECIFICATION.md Part F.5.2) is absorbed by the FRAM
  layer's dual copy: `_read_chunk()` logs errno 23 (`UNEXPECTED`) and `_read()` falls back to block 1
  and repairs block 0, so a retry inside the chunk loop would buy little.
- **`FiltCoeff` keeps its two meanings, namespaced per sensor** (owner, 2026-09-26). BMP3xx's IIR
  register index and the ISL29125's EMA coefficient share the name, namespaced per sensor on
  `/sensors`.
- **`arduino/` and the C reconciliation are post-audit only** (owner, 2026-09-25: 'the C port stays
  out of scope, anything there is post-audit only'). That covers the UART protocol's C
  implementation (its reconciliation against `UART_C_PORT_CHANGELOG.md` included) and the
  BME688/BSEC material with its licensing. Nothing here tracks work on it.
- **CLAUDE.md's two-target clean-chroot verification is an owner-run periodic check, not a blocking
  per-push gate - settled (owner decision, 2026-09-18).** The recipe, both targets and the separate
  installer verification all stand exactly as CLAUDE.md documents them; what changed is who runs
  them and when. The owner runs them manually every now and then, on the bench Pi4 (trixie/GCC 14.2)
  or their own box, rather than a session blocking a push on a chroot it usually cannot build.
  The legs were last satisfied 2026-09-12. Changed since:
  `scripts/test.sh` (+520 lines - parallelism autodetection, the backgrounded `tests_scripts/` job
  and its timeout, the heap-size and port-base moves), `scripts/typecheck.sh`, `scripts/lint.sh`,
  `scripts/build_firmware.py`, `scripts/_require_clean_hardware_run.sh`,
  `scripts/run_digital_twin_ci.sh`, `scripts/run_unix_port_integration.sh`,
  `scripts/_digital_twin_ci_suite.py` (test orchestration only - no build step, so the chroot legs
  neither exercise nor are threatened by it; 2026-09-22 widened its `MemoryError` log check to match
  `memory allocation failed` too - same class of change, still no build step),
  **`toolchain/setup_toolchain.py` (2026-09-21: `build_unix_port()` now builds TWO variants -
  `build-standard` without `MICROPY_PY_SYS_SETTRACE` as the test rig, `build-settrace` with it for
  `--coverage` only - so a from-scratch chroot run builds the Unix port twice and takes
  correspondingly longer; `scripts/test.sh` picks the binary by mode, then asks it which variant it
  actually is (`hasattr(sys, "settrace")`) and rebuilds on a mismatch, because a REUSED chroot's
  `build-standard` predates the split and still carries the flag while remaining executable - the
  single most likely way a reused chroot breaks here, now detected rather than silently measured)**,
  `pyproject.toml` (+159), and on the web side
  `package.json`/`vitest.config.js`/`eslint.config.js` (2026-09-19's PUT-matrix split - npm scripts
  and a build-time define, which `env --tier generic` installs through but does not compile),
  and - the class the lint/typecheck recipe never exercises at all - the two `toolchain/` files:
  `setup_toolchain.py` as described above, plus the new `micropython_overrides.py` (PR #90's
  `MICROPY_ASYNC_KBD_INTR=0` Unix-port build override, SPECIFICATION.md Part B.14.1). That pair is
  what a compiler-version-sensitive break would actually show up in, so it is the part worth the
  owner's next manual run; a `scripts/test.sh` change is host tooling and low-risk.
  **2026-09-22 adds a second override to that same class, and it changes the rp2 firmware build
  rather than the Unix port**: `micropython_overrides.py`'s `lwip_connection_counts` (Part B.14.2)
  generates an out-of-tree board directory and passes `BOARD_DIR=` to `make`, and
  `setup_toolchain.py`'s `build_firmware()` now applies it unconditionally and then verifies the
  resulting macros by preprocessing the real translation unit with the flags CMake recorded. Two
  consequences for a chroot run: the firmware build gains a post-build `-E` step with the C compiler
  CMake recorded (seconds, but it needs the ARM toolchain present, which the installer leg already provides), and
  `toolchain/versions.toml` gained an `[lwip]` table that `build_firmware()` reads on every build -
  a malformed one fails the build loudly rather than silently building unpinned. The installer
  verification leg (`uv run toolchain/setup_toolchain.py`) is the one that exercises this, not the
  lint/typecheck recipe. **Same day, extended**: the override now also validates the `[lwip]` table
  as an *ensemble* before building (lwIP's options are not independent — `lib/lwip/src/core/init.c`
  makes sixteen of their relationships compile-time `#error`s, and `opt.h` derives four more values
  from them), and the generated header carries a sentinel the post-build check demands, so a shim
  that was never *found* fails even when the asked-for values match MicroPython's own defaults.
  Both are pure host-side Python with no new dependency; the chroot relevance is unchanged.
  2026-09-22 added two more to `scripts/test.sh`, both pure shell with no build impact: the
  `MemoryError` gate matches `memory allocation failed` as well as the class name, and argument/`GC_THRESHOLD` validation moved ahead of the two live-tree sweeps so
  a rejected invocation mutates nothing (it previously wiped `tests/_tmp` while the concurrent
  MicroPython tier held scratch dirs under it). A third, text-only change the same day: the
  out-of-range rejection's message now names the rp2040's own 32-bit machine word instead of
  "a machine word" — the bound is the firmware's, since this 64-bit host accepts values up to its
  own word and only raises `OverflowError` near 2^63 (measured against the pinned interpreter).
  Also 2026-09-22, `pyproject.toml`: the `tests/_coverage_runner.py = ["S102"]` per-file-ignore is
  gone, the suppression now sitting inline at the one `exec()` it covers the way
  `tests/_threshold_runner.py`'s already did — lint config only, no build impact.
  And one more `scripts/test.sh` change the same day, shell only with no build step: the two
  `_render_coverage.py` calls are `||`-guarded and the verdict block maps a renderer-only failure
  onto exit 3, so a coverage-tooling failure stays distinguishable from a failed test.
  A further `scripts/` change on 2026-09-22, also shell only:
  `scripts/setup_cross_browser_toolchain.sh`'s two `apt-get update` calls go through an
  `apt_update()` helper that tolerates their own failure, the same treatment
  `toolchain/setup_toolchain.py`'s `ensure_apt_packages()` already gives them — under `set -e` a
  single unrelated third-party source (a PPA that 403s or whose key expired) aborted the whole
  installer before it could install a package the main archive serves. Every `apt-get install`
  stays fatal. The chroot recipe never runs this script, so it changes nothing the legs cover.
  **The connection-limit work (2026-09-23/24) adds, by what covers it:**
  - **Installer leg** (`uv run toolchain/setup_toolchain.py`), the only leg a change here can move:
    `versions.toml`'s `[lwip]` sized for `max_connections = 6` (PCB 9, SEG 48, `MEM_SIZE` 12000 —
    limit + 3, limit × 8, limit × 2,000); the lwIP readback now runs the C compiler CMake recorded
    (not `arm-none-eabi-gcc` from `PATH`) under a 120 s timeout, and must still read back the set it
    asked for; `setup_toolchain.py` reports an `OverrideError` like a `SetupError`.
  - **Host-side Python, no build input changed**: `micropython_overrides.py`'s
    `check_lwip_ensemble()` restates all sixteen `init.c` checks, adds `MEMP_NUM_TCP_PCB >=
    max_connections + SPARE_TCP_PCBS` (3) and refuses `max_connections` below 1;
    `validate_lwip_macros()` is public, buildgen calls it first, and it refuses `TCP_MSS` 0; an
    unexpanded option name reads back as absent; `scripts/build_firmware.py` passes `toolchain_dir=`,
    so every device build applies the override.
  - **Lint config only**: `pyproject.toml`'s `max-args` 24 (`backlog=`, `chunk_bytes=`) and the
    `S603` per-file ignore for `toolchain/micropython_overrides.py`.
  - **Test orchestration, no build step**: `_digital_twin_ci_suite.py`'s Run 11b (full-ceiling
    burst per SPECIFICATION.md Part E.9; 1 s settle before every burst; ceiling read through
    buildgen's `webserver_init_default()` inside its failure guard; a request counts as served only
    with a 200 and a parsed JSON object); `scripts/test.sh` re-emits each red outcome as a GitHub
    annotation from one `GITHUB_ACTIONS` block (pytest tier first, per-file ones capped at 8 plus
    "and N more"), so a local or chroot run prints nothing extra.
  **2026-09-24, comments only**: `pyproject.toml`, `toolchain/versions.toml`, `scripts/typecheck.sh`,
  `ci.yml` and the composite action had their comments cut to the 3-line cap; no setting, pin or
  step changed, so nothing here moves either leg.
  **2026-09-24, `scripts/` behaviour**: `html_stub/` is retired, so `build_frozen_html.sh` now
  requires `HTML_SRC_DIRS` and `scripts/test.sh` builds the real wozi site as `frozen_html`
  (`build_website.sh`, pure Python, no Node); `test.sh`'s variant probe also imports `asyncio`.
  Both run in a chroot's `scripts/test.sh` leg with nothing new to install.
  **2026-09-24, `toolchain/setup_toolchain.py`**: `env`'s `uv sync` is retried three times with a
  10 s / 20 s pause (`run_retried()`, mirroring `ci.yml`'s `unit-tests`), after a clean-sandbox install
  failed on one HTTP 502 from `actionlint-py`'s release download. Same command, same dependencies;
  the installer leg only gains the retry.
  **Partial evidence, not a leg**: a session sandbox (GCC 13.3, not a `--variant=minbase` chroot)
  ran `env --tier generic` and then `uv run toolchain/setup_toolchain.py` from an empty toolchain
  directory on 2026-09-24 — all eight verification checks passed and the lwIP readback was clean.
  **2026-10-06, comments only, no build impact**: decision tags in the comments of `pyproject.toml`,
  `.github/workflows/ci.yml`, `.github/zizmor.yml`, `scripts/lint.sh` and `scripts/test.sh`; no
  setting, pin or step changed, so nothing here moves either leg.
  **2026-10-06, dependency refresh**: `pyproject.toml`/`uv.lock` tool versions (mypy 2.4.0, ruff
  0.16.10, actionlint-py 1.7.12.25); `package.json`/`package-lock.json`/`.nvmrc` (Node 22 → 24, every
  npm devDependency at its newest, `@types/node` on the Node major, the eslint-comments plugin
  added); `ci.yml` action pins (setup-node v7, paths-filter v4.0.3) and the cross-browser cache key.
  The MicroPython ref did not move, so the installer leg is not owed by this entry; both legs owe the
  new Node major and the refreshed Python tools.
  **2026-10-06, Lint config only**: `pyproject.toml` `max-args` 24 → 8, `max-statements` 80 → 78
  and `max-returns` 12 → 11 (each ceiling at its measured maximum, pinned by the new
  `tests_scripts/test_lint_ceilings.py`), PLR0913 per-file ignores for `src/asy_uart_driver.py`,
  `src/asy_isl29125_driver.py`, `tests/machine.py`, `digital_twin/machine.py`; `eslint.config.js`
  `max-classes-per-file` 2 → 1, pinned by `tests_js/lint-ceilings.test.js` through a new
  Node-context Commands API module, `tests_js/_lint_command.js` (registered in `vitest.config.js`,
  `tests_js/vitest-commands.d.ts`, `tsconfig.json`/`tsconfig.node.json`) — no build impact and no
  new dependency; the lint leg and the web tier run them with what is already installed.
  **2026-10-06, website definitions from one source**: `scripts/build_website.sh` always generates
  the device's definitions from `devices/<device>.toml`; the new `scripts/build_device_websites.sh`
  builds every device's site; `scripts/_generate_sensortask_modules.py` also writes every device's
  definitions and an `index.json` manifest into `build/generated_src/definitions/`; `package.json`
  gains `build:definitions` and `prepreview`, and `build:site` builds every device's site;
  `ci.yml`'s web filter gains `src/`, `buildgen/` and `devices/`, and the cross-browser job builds
  through `npm run build:site`. Shell and host Python with no new dependency; a chroot's
  `scripts/test.sh` leg runs the generator as before, and `env --tier generic` installs nothing new.
  **2026-10-06, the runner summary block and the level ladder**: `scripts/test.sh`, `lint.sh` and
  `typecheck.sh` end with the SPECIFICATION.md E.10 block (new `scripts/_summary_block.sh` and
  `scripts/_summary_block.py`); `test.sh` reports a retried pass as `RETRIED-PASS`, validates
  `PER_FILE_TIMEOUT_S`/`TESTS_SCRIPTS_TIMEOUT_S` up front, exits 2 on a usage or setting error,
  runs its pytest tier with the run-record plugin `scripts/_pytest_run_record.py` and archives its
  evidence through `scripts/_archive_evidence.py` under `build/archive/`; the hardware runners run
  the lower levels first (`scripts/_run_lower_levels.sh`) and judge through
  `scripts/_hardware_verdict.py`. Bash and stdlib host Python with no new dependency: the chroot's
  `scripts/test.sh` leg exercises the block and the archive, and nothing new is installed.
  **2026-10-07, renames, lint config and comment-only conversions, no build impact**:
  `pyproject.toml`'s per-file ignores and mypy override list follow the `asy_` module renames
  (`src/asy_api_response.py`, `src/asy_print_log.py`, `asy_system_service`, …); `N801` leaves the
  global ignore list for per-file entries on the C.2 compound and Sensirion-port files
  (`asy_bmp3xx_driver.py`, `asy_fram_driver.py`, `asy_isl29125_driver.py`, `asy_scd30_driver.py`,
  `asy_sgp40_driver.py`, `voc_algorithm.py`); `FBT001` joins `src/asy_isl29125_driver.py`'s entry
  (its `_push_*` family, as in its siblings'); `max-statements` 78 → 77 (the measured maximum once the
  generated pause callback returns its setter's answer); `asy_base_classes` leaves the explicit-`Any`
  baseline. `scripts/lint.sh`'s `gc.collect()` guard names `src/asy_system_service.py`;
  `scripts/_digital_twin_ci_suite.py` sends the renamed REST keys (`MeasInterval`, `NTPHost`); the
  function and class docstrings of `scripts/` and `toolchain/` became `#` comments, every file
  otherwise AST-identical (`OverrideError` gains a `pass`). Lint config, shell and host Python
  only, no new dependency and no build input changed, so nothing here moves either leg.
  **2026-10-07, lint config only, no build impact**: `pyproject.toml`'s `T20` (print) leaves the
  global ignore list for per-file entries on `tests/`, `digital_twin/`, `tests_scripts/`,
  `tests_hardware/`, `buildgen/`, `scripts/` and `toolchain/`, and `src/asy_print_log.py`'s entry
  becomes `T20` alone (its `ANN401` goes with the `**kwargs`); `asy_api_response`,
  `asy_config_manager`, `asy_print_log` and `asy_system_service` leave the explicit-`Any` baseline.
  `scripts/_digital_twin_ci_suite.py`: one comment. `tests_scripts/` gains two AST checks
  (`test_device_script_config_schemas.py`, `test_stored_config_golden.py`): stdlib host Python, no
  new dependency, so nothing here moves either leg.
  **2026-10-07, mypy config only, no build impact**: `pyproject.toml`'s main-pass `exclude` gains
  `digital_twin/rp2.py`, which collides with the new `tests/rp2.py` fake as `digital_twin/machine.py`
  does with `tests/machine.py`. No new dependency and no build input changed, so nothing here moves
  either leg.
  Kept here as the running list of what the owner's next manual run has to cover.
- **Session 7's `pyproject.toml` `max-args` ratchet (21 → 22, for `WebserverService.__init__`'s new
  `build_info=` parameter) only got the noble leg of CLAUDE.md's two-target clean-chroot
  verification** — the narrower, earlier instance of the entry above. The trixie leg — required by the same rule whenever `pyproject.toml`
  changes, specifically to catch a GCC>=14-only issue the noble/GCC-13 leg can't see (the precedent:
  the mbedtls `-Warray-bounds` false positive, SPECIFICATION.md Part B.7.1) — couldn't be run from
  that session's own sandbox: `debootstrap --variant=minbase trixie` needs `deb.debian.org`, which
  the sandbox's egress policy rejected outright (confirmed directly, not a transient failure), with
  no alternate Debian mirror to fall back to. The change itself is a pure ruff/pylint lint-rule
  threshold with no compiler-version sensitivity, so the residual risk was judged low, not zero
  (agent, 2026-09-12) — a from-scratch trixie leg (or a run on the bench Pi4, which already runs
  trixie/GCC 14.2) should still confirm it whenever one is next convenient. The change itself is the
  `build_info=` parameter SPECIFICATION.md Part L.7 describes.
- **`buildgen/buildspec.py`'s per-driver schema is hand-maintained — making it AST-derivable is a
  separate, unstarted unit of work.** Everything else `buildgen/` needs from a driver is derived
  from `src/` automatically (the class itself via `driver_registry.py`'s naming convention,
  `_WIRING`, `_VALUE_WIRING`, `_LIMITS`, `_Default*`); `buildspec.py`'s "which TOML fields does this
  driver require/allow, does it sit on a bus, does it have a selectable address" dicts are the one
  exception, because Session 2's shipped TOML field names (`pin`, `cs_pin`, ...) and `src/`'s
  constructor parameter names (`neopixel_pin`, `spi_cs`, ...) are two independently-evolved naming
  spaces with no rule connecting them. So adding a 7th driver means editing one table by hand, and
  forgetting to is a real (if now clearly-reported) failure. **The small half is already done**: a
  driver that resolves via `driver_registry` but has no `buildspec.py` entry raises a dedicated
  error naming that as the cause, instead of reporting every one of its real fields as
  "unrecognized" (SPECIFICATION.md Part L.6's "Known limitation" section). The large half —
  deriving the schema from each driver's own constructor signature, or from a new declarative tuple
  beside `_WIRING` — needs real design, not a mechanical continuation, and hasn't been started.
  **Owner decision, 2026-09-18: it stays hand-maintained, and this is no longer an open question.**
  The drivers are an integral part of this repo, not third-party definitions arriving from outside,
  so one table edit per new driver is an acceptable cost — and the small half above already turns
  forgetting it into a named error rather than a confusing one. Kept to record that the alternative
  was considered and declined (owner, 2026-09-18).
  **Same answer for `buildgen/definitions.py`'s cross-cutting `status`/`errcount` sections** (owner,
  2026-09-24): they stay a hand-maintained catalog beside the `@web`-derived per-driver sections.
- **`[device].name`/`hostname`/`hotspot_password` are wired into the boot path now - done (owner
  decision, 2026-09-18).** Every device really did boot as `SensorNode` whatever its TOML said; the
  three fields were validated and then reached nothing. `WifiService.__init__` takes `hostname=`/
  `hotspot_password=` and substitutes them as the **defaults** of the two ConfigManager-persisted
  fields (`_with_default()`), so a user rename through the web UI still wins on a later boot, and
  every existing test that asserts the literal `"SensorNode"`/`"12345678"` keeps passing untouched -
  `None` means "keep the shared default", which is what a bare construction asks for.
  `buildgen/codegen.py` passes `devices/*.toml`'s own values into the generated `WifiService(...)`
  call; the `test_hostname_and_hotspot_password_are_not_yet_wired_into_generated_code` tripwire is
  replaced by its inverse, and `validate.py`'s long gap comment by two lines of current fact.
  **One new failure mode, closed at both ends**: ConfigManager treats a default it cannot satisfy as
  an invalid config and then answers `None` to *every* read, so an out-of-bounds injected value
  would have cost a device its whole networking config. `validate.py` now refuses a hostname longer
  than `network.hostname()`'s 32-character cap at build time (in practice a cap on `[device].name`),
  and `_with_default()` drops an out-of-bounds value back to the built-in default rather than
  installing it - the build-time rung is the one that fails, the runtime one keeps the device
  bootable. Four tests: the injection works, an out-of-bounds injection falls back, the generated
  call carries the values, the over-long hostname fails the build.

- **A digital-twin soak's wall clock is set by GC timing, so it must never be bisected to a code
  change** (established 2026-09-11 after one was — see SPECIFICATION.md Part E.7 for the measurement
  and the inverted control). Not open work: the finding itself is the resolution, and
  `tests/test_digital_twin_run_generic_integration.py`'s budget now sits above the whole observed
  range rather than inside it. Left here because the trap is easy to fall into a second time: the
  numbers are stable to within 0.3s per build, which reads exactly like a real signal.
- **The UART fakes still do not *wait* the way a real read does, deliberately.** They serve what
  they hold and return, where the peripheral would wait out `timeout_char` for every byte the caller
  asked for that has not arrived (SPECIFICATION.md Part F.5.8). Making them actually wait would turn
  a real-time defect into a slow test; both instead count the stall they would have taken, as
  `UART.would_have_blocked_bytes`, held to identical semantics by `tests/_uart_link_contract.py`.
  **The regression gap this entry was opened for is now closed, but it was not closed by counting
  alone** — a sweep that removed each of the driver's seven read-path clamps in turn (2026-09-12)
  found three that no test caught: the two `readline` paths, which the fakes never counted at all,
  and `_read_delimited`'s one-byte gate, which was counted but asserted nowhere. `readline()` now
  counts the one byte its gate guards, and each of the seven paths has a test that fails when its
  clamp is removed, re-verified by the same sweep. What remains genuinely unmodelled is the
  *duration* — a fake cannot tell a caller how many milliseconds of event loop an over-ask would
  have cost, only how many bytes it was over by. Only the bench tier measures the milliseconds, and
  F.5.8's table is that measurement.
- **Four UART-audit findings reviewed and left as they are** (agent, 2026-09-11):
  - **The peer-sized `_accept_set()` allocation is to be chunked and capped** (owner, 2026-10-05).
  - **`asy_uart_driver.UART.deinit()`/`init()` do not respect the session lock.** Calling either
    while a read is in flight would leave the in-flight code holding a reference to a deinit'd
    peripheral. No caller does: `UARTComm` never deinits, and the one place that does
    (`tests_hardware/device_scripts/uart_crossover_recovery.py`'s injector) does it between
    exchanges. A guard was not added because `init()` calls `deinit()` itself, so refusing while
    locked would change construction semantics for a hazard nothing currently reaches.
  - **`UARTComm.setup()` called a second time while its own listen loop is running would
    deadlock** on the bus lock the loop holds during its unbounded read. Nothing calls it twice -
    `asy_system_service.py` runs the setup batch before any task starts - so no guard was invented for
    a caller that does not exist. Re-checked against the supervisor itself (2026-09-12): its restart
    ladder re-calls a dead task's *starter*, never a module's `setup()`, so the unreachability is a
    property of the code rather than of today's call sites.
  - **One `FramingCOBS` instance shared between two drivers would corrupt both**, since its
    long-lived scratch is per-instance, not per-call. Every construction site makes its own; noted
    because the failure would be silent if one ever did not.
- **A device-script loose end from the 2026-09-25 sitting — owner's call.** Two stale scratch
  configs sit on the dev board's flash, `config_HWTEST_DEBUGLEVEL_BACKUP.cfg` and
  `config_HWTEST_REBOOT.cfg`, left by earlier device scripts; the DebugLevel backup could mislead a
  later restore. Should their scripts remove them on exit?

- **`mypy tests_hardware/device_scripts` run STANDALONE reports two `Timer()` findings that no
  gate ever sees.** Both `timer_alarm_pool_exhaustion.py` and `scheduler_saturation_drop.py`
  construct a bare `machine.Timer()`, which is valid runtime usage the third-party board stub does
  not model (it requires a positional `id`). This is the same stub gap CLAUDE.md's "Code quality
  tooling" section already records for `src/`'s four drivers plus `I2C.deinit()`, and it has the
  same resolution: every invocation the project actually runs - CI's `scripts/typecheck.sh src
  tests tests_hardware/device_scripts` and a bare local `scripts/typecheck.sh` - includes
  `tests/`, whose `tests/machine.py` fake models `Timer()` correctly and wins module resolution.
  Worth knowing before anyone runs mypy over that directory on its own and reads the result as a
  regression.
- **Additional checker candidates, measured and mostly declined** (agent, 2026-09-10; a dead-code
  tool is run once, owner 2026-09-26). Evaluated against the real tree rather than by reputation,
  when shellcheck/actionlint/zizmor were added:
  - **`zizmor`** (GitHub Actions security) - **adopted.** All 50 findings fixed, not suppressed:
    `excessive-permissions` (workflow-level `permissions: {}` + per-job `contents: read`),
    `artipacked` (`persist-credentials: false` on every checkout), and `unpinned-uses` (SHA-pinned
    `codecov/`+`dorny/`; `actions/*` stays tag-pinned by an explicit `.github/zizmor.yml` policy,
    since a compromise of GitHub's own org compromises the runner anyway and SHA-bumping four
    first-party actions has real cost with no Dependabot configured). One audit is **disabled with
    cause**: `self-repository` wants `uses: $/.github/...` (GitHub's July-2026 syntax), which
    actionlint 1.7.12 - the other hard gate over the same files - rejects outright as invalid.
    Revisit when actionlint learns it. Runs `--offline` so it behaves identically in CI, on a dev
    box, and in the clean-chroot recipe.
  - **`import-linter`** - **rejected, measured; structurally incompatible.** It validates that every
    `root_packages` entry is a real package and refuses flat modules ("'x' is a module, not a
    package"), and `src/` is deliberately a flat set of modules with no `__init__.py` - they are
    copied flat alongside `ext/` and frozen into firmware. Both workarounds were tried and both
    produce a **false green**: wrapping `src/` in a shadow package (or letting it resolve as an
    implicit namespace package) reports `Analyzed 27 files, 0 dependencies` and marks every
    contract KEPT, because each intra-`src/` import is a bare absolute `from asy_base_classes import
    ...` that resolves outside the package. Making it work would mean rewriting every import in
    `src/` to package-relative form - an operational change to frozen firmware code, not a tooling
    change. Note also that Part C's Layer 2/3 split lives *inside* one module per driver, so
    import-linter could never have seen it; only the coarser module-level direction was ever in
    reach.
  - **`vulture`** (dead code) - **rejected, measured.** All 8 of its >=80%-confidence findings are
    false positives: it cannot see through quoted annotations or `if TYPE_CHECKING:` blocks, so it
    reports `Self`/`NamedTuple`/`Iterable`/`Sequence` as unused imports and flags the no-op
    `cast()` shim's required `typ` parameter.
  - **`gitleaks`/`detect-secrets`** - **rejected, redundant.** `detect-secrets` found only the known
    test/twin WiFi passwords and *missed* the real documented credential in `asy_wifi_service.py`
    that ruff's `S106` catches. Ruff's `S105`/`S106` are live everywhere except the three known,
    individually-exempted sites, which covers this better.
  - **`codespell`** - **rejected, measured.** 1519 findings, overwhelmingly false positives on
    domain vocabulary (`FRAM` -> "FRAME", `Pres` -> "Press", `optionEl` -> "optional").
  - Also considered and dismissed as not applicable or redundant: `markdownlint` (fights
    hand-formatted prose), `yamllint` (actionlint covers the only two YAML files), `hadolint` (no
    Dockerfiles), `taplo` (two TOML files), `pip-audit`/`npm audit` (dev-only dependencies, nothing
    ships to the device), and the many flake8/pylint-era Python tools ruff's `ALL` already subsumes.
- **Real-hardware re-test of the segfault fix and the memory-leak soak test — real-hardware forms
  now exist and are wired into `tests_hardware/`, but the actual long-soak run is still opt-in and
  has not yet been executed.** Corrects a stale claim (this entry used to say neither soak-test
  script had a real-hardware-runnable form at all — no longer true):
  - The **segfault stress test** equivalent is
    `tests_hardware/bench/test_end_to_end_timing.py::test_real_concurrent_client_burst_does_not_crash_the_webserver`
    — confirmed passing on real hardware (2026-09-04). Not because the root cause was ever in doubt
    (a dangling-pointer bug in `extmod/modselect.c`, confirmed compiled out of real rp2 firmware via
    `MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` and fixed on the Unix port by
    `digital_twin/unix_port_poll_prewarm.py` — see `digital_twin/README.md`'s "What's here" for the
    fix), but as standing on-target validation of the wider stress scenario itself.
  - The **memory-leak soak test** equivalent is
    `tests_hardware/bench/test_memory_stress_bench.py::test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic`
    — real, committed, `@pytest.mark.long_soak`, and **still not yet actually completed cleanly**
    as of 2026-09-04 (the one real attempt that day was aborted by an unrelated cascading DUT-
    unreachable failure elsewhere in the same run - see open question 9's `BENCH_AP_PASSWORD` -
    before this test itself ever got a genuine clean pass/fail). Deliberately does **not** use the
    Unix-port twin's own `gc.mem_free()` recovery-peak-trend methodology — confirmed impossible on
    real hardware without disturbing the very system being measured (`mpremote exec()` always
    interrupts the live system first, and a live `asyncio.run()` doesn't resume once interrupted —
    see the test's own module docstring). Instead watches real HTTP soak traffic passively for the
    two disqualifying symptoms observable without disturbing anything: a `MemoryError` traceback,
    or an unexpected mid-soak reboot — a real but coarser signal than an actual trend measurement.
    Not because the "no confirmed leak on the Unix port" conclusion is in doubt (four independent,
    properly-powered replication experiments found no reproducible decline, on either idle or
    HTTP-soak traffic), but because the Unix port's allocator/heap behavior isn't guaranteed
    identical to rp2040's real one. **`--tier mid` (10 minutes) run for real (2026-09-08, bench
    Pi4, project owner's go-ahead given in-session): clean pass** - `test_real_hardware_memory_
    does_not_leak_under_real_http_soak_traffic` plus its two long_soak siblings
    (`test_single_core_timing_headroom_holds_under_normal_full_task_load`,
    `test_scd30_real_clock_stretch_never_exceeds_the_configured_timeout`) all PASSED, 3/3, zero
    `MemoryError`/reboot markers, zero unexpected skips. **Still open**: the real `--tier long`
    (6h) production-duration run itself - `mid` is a genuine real-hardware pass at 10 minutes, not
    a substitute for the full 6h window this item was always about
    (S4).
- **Manual cross-browser/cross-device spot check not yet done — needs the project owner directly.**
  Automated coverage (Part H.7's cross-browser smoke script, Vitest's browser-mode suite) only ever
  exercises Chromium/WebKitGTK/Firefox/Edge on Linux CI runners — Part H.1's "stable and
  good-looking on major mobile/desktop browsers" goal still wants at least one real human pass on
  real Safari and a real mobile device, which no automation here can substitute for.
- **UART sensor integration — still unwired as a *sensor*, though the link itself now exists.**
  `asy_uart_comm.py` is promoted (SPECIFICATION.md Part J) and the buildgen-generated
  `sensortask_dev.py` constructs two instances across the dev bench's crossover jumper, which is
  what makes the protocol's self-compatibility property physically testable. What stays
  deliberately absent is any *sensor* behind that link: no BME688/BSEC coprocessor, and no such
  wiring in any other variant. Not a legacy deployed feature, so adding one would be a scope
  addition beyond feature-parity rather than a postponed fix — this stays as-is (owner, 2026-08-20,
  `b6cb852`). The protocol module is standalone by design (owner, 2026-09-11, `32b136f`): its
  BME688/BSEC first use case is explicitly out of scope and was **not** part of the promotion.
- **Owner requirement for the final wiring stage (owner, 2026-08-08, `7f498c1`, paraphrase) —
  fulfilled; held here only until the owner's audit of the whole refactor closes.** Every
  `sensortask-*.py` built as part of the real rewrite needs a full Unix-port equivalent, runnable on
  a local computer, with whatever hardware is physically unavailable there mocked at the lowest
  level of bus data exchange (i.e. the same mocking boundary SPECIFICATION.md Part
  E.4/`tests/machine.py` already establish for unit tests — fake `machine.I2C`/`machine.SPI`/etc.
  byte-level transactions, not higher-level driver stand-ins) so the whole wired-together sensortask
  can be exercised as close to the real target as possible without physical hardware. **Fulfilled**:
  `digital_twin/` is the lowest-level-mocking module this requirement calls for (see
  `SPECIFICATION.md` Part A.10), and `scripts/run_unix_port_integration.sh` runs the whole
  wired-together (buildgen-generated) `sensortask_wozi.py` against it end to end (see
  `digital_twin/README.md`'s "Swapping the twin in for a Unix-port run" section). Comes out when
  that audit closes.
- **Config-duplication centralization** — same keys hand-kept in sync across `_DEFAULT_CONFIG`, the
  REST handler, and the HTML form. Owned by the refactor: each promoted `*_Reader`'s own `_VAL_*`
  schema tuple + `get_dict_cfg()`/`get_dict_data()` is the intended single source, not fully wired
  end-to-end yet (`sensortask-wozi.py` itself predates the per-sensor-config model — see "Refactor
  targets not yet done" above).
- **`js/nav.js`'s `initNav()` registers a `document`-level `keydown` listener with no matching
  removal** — harmless today (called exactly once per real page load), but a latent leak if it's
  ever called more than once without a full page reload (e.g. a future hot-reload path, or a test
  file that calls it repeatedly against the same `document`). Worth a `removeEventListener`/cleanup
  return value if that ever becomes a real scenario.
- **`selectSection()` is duplicated near-verbatim between `js/app.js` and `js/main.js`** (both
  entry points build their own local closure over `onSelect`/nav rebuild). Low priority: the two
  entry points are deliberately separate (prototype vs. production, Part H.2), and the duplication
  is small: extracting a shared helper is a minor simplification, not a correctness fix.
- **`asy_scd30_driver.py`'s persistent NVM setters have no published write-cycle endurance figure**
  (checked every available Sensirion doc) — safe today only because every setter is REST-triggered,
  never called from a boot path or periodic loop. Don't add a periodic/high-frequency caller
  without reconsidering this.
- Network fault injection against the real dev bench unit is complete
  (`BenchBridge.inject_network_degradation()`, `tc netem` on `wifi_iface()` only: loss,
  latency+jitter, corruption, duplication, reordering, exercised by
  `tests_hardware/bench/test_network_resilience.py`); CYW43-firmware-level faults such as
  `wlan.connect()` itself raising are not network-path faults `tc`/`iptables` can express and stay
  covered by the digital twin's own `--fault wlan:...` hook. **Still open**: the
  NTP-outage-x-bus-load fault recombination has no twin/mock-tier equivalent - the NTP outage alone
  now does (twin Run 9: permanently unreachable NTP for 90 s, `scripts/_digital_twin_ci_suite.py`), so
  adding bus load to that run is the obvious extension; not chased yet. The other two recombinations that matter (FRAM write vs. a real hardware reset;
  repeated WiFi flapping x concurrent bus load) already have coverage across every tier where they
  are meaningful.
- **Part I.2's hotspot catalog has never been re-walked with a *placement* lens.** I.2 scanned
  every `src/` file for *how much* each function allocates, which is the question that matters for
  exhaustion; the heap-fragmentation defect (Part I.4(f.1)) was about *where* long-lived objects land, and only its known instance (the FRAM logging path, plus
  the two boot lists) was addressed. A second walk would ask a different question of the same files:
  which of them still allocate something long-lived while bus or network churn is in flight?
  Measures A and B removed the one confirmed case, and `tests_scripts/test_digital_twin_boot_contiguity.py`
  would catch a new one *in the boot lists* — so this is a genuine open question about the run phase,
  not a known gap, and no measurement points at one. Worth a pass if a future session has the budget;
  SPECIFICATION.md Part I.1's prior-art note explains why the `__init__`/`setup()` split is the
  structural answer wherever such a case is found.
- **SystemService's settings store grows with device-wide settings** — the timezone offsets
  (`GMTOffset`/`DSTOffset`) now held by `NTPClient`'s config, future rsyslog settings;
  `config_SYSTEM.cfg` holds only `DebugLevel` today (`src/asy_system_service.py:59, :101`).
  Owner-deferred goal (owner-confirmed, 2026-08-11, `249f2ae`: 'per the owner's explicit intent,
  this is meant to grow into a general, module-independent system-settings store', paraphrase).
- **Adopt a genuine non-blocking alternative to every currently-unavoidable blocking call as soon as
  one reliably exists** (owner, 2026-07-24, `cc911be`: 'Don't treat the current state as
  permanently accepted risk'; confirmed by the owner, 2026-09-29). Today's list, each backstopped by
  the hardware watchdog (SPECIFICATION.md F.2): a `machine.I2C` transfer on a wedged bus; a single
  `machine.SPI` transfer (synchronous, `ports/rp2/machine_spi.c:303-335`, v1.29.0; the FRAM's
  waits around it wait only on other coroutines, SPECIFICATION.md F.2).
  `socket.getaddrinfo()` is not called from `src/` (`asy_dns_client.py` resolves over its own
  non-blocking UDP client). Re-checked at each MicroPython version re-check (CLAUDE.md 'Platform
  target').
- **Resize the rp2 littlefs reservation** — only once flash space is actually short (owner,
  2026-09-26); trigger: the firmware image-size report; mechanism SPECIFICATION.md B.14.3.

## Owner questions

Questions for the project owner, each dated, in the owner's format; nothing else in the repo parks a
question.
