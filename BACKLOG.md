# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

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
  side is largely legitimate (`print_log.py`'s variadic logging methods, `config_manager.py`'s
  generic value-checking helpers, opaque `ticks_ms()`-typed values). Turning `disallow_any_explicit`
  on still needs a typing strategy for the test wrappers (e.g. `Protocol` classes + `__getattr__`
  delegation) and a decision on the genuinely-variadic/opaque `src/` cases - not just a flag flip.
- **FRAM's `verify_present()`/`set_write_protected()` stay in `src/` — SETTLED, do not re-raise.**
  They have zero callers in `src/` today and that is fine: "zero callers now, maybe callers
  tomorrow" is the whole point, and both are bus-hazard-tested across all four tiers and confirmed
  correct under real fault injection (CLAUDE.md's bus-hazard hard rule). The project owner has
  decided this more than once; it is not an open design question, and no future session should
  re-propose removing them or ask again who is supposed to call them.
- **No standardized timeout/cancellation mechanism yet for blocking calls that genuinely can be
  timeout-wrapped. PRIORITIZED (project owner, 2026-09-11): to be done soon** — ahead of the other
  items in this section, not whenever it next comes up. The calls in question: FRAM SPI
  transactions and `src/asy_udp_socket.py`'s own `select.poll`-driven
  `ready()`/`write_and_recvfrom()` — anything that isn't a raw blocking `machine.I2C` call
  mid-transaction, which can't be interrupted regardless; see CLAUDE.md's "wedged I2C bus" hard
  rule for why that case is different and already decided, and why `socket.getaddrinfo()` turned
  out to belong in the *can't* bucket instead and is gone from this codebase entirely now). Each
  remaining call currently uses its own bespoke approach rather than one consistent mechanism
  applied everywhere.
- **The task-supervisor error-budget counter** is behaviorally correct and intentional as designed,
  but flagged by the owner as implementable more efficiently — worth a cleaner implementation in
  the refactor without changing observed behavior. (Neopixel warning-flash sequencing was the other
  half of this item - resolved by the `src/asy_neopixel_driver.py`/`src/asy_notification_service.py`
  promotion, see `SPECIFICATION.md` Part A.4.)
- **Rough sequencing, not a committed plan**: (1) dev/build environment setup (genericized
  `build-*.sh`/toolchain paths) — everything else touching CI/firmware depends on this; (2) the
  structural patterns above (per-sensor config, generalized error-counter bookkeeping) are largely
  done; (3) bus/sensor error-recovery robustness items above, which build on that structure — the
  standardized timeout/cancellation mechanism is the next one of these to pick up. mypy/ruff/stubs/
  Unix-port-tests were pulled forward out of this order already, once `math_helpers.py` cleared the
  `src/` bar, and that's now standing practice for every new file, not a one-off.

## Open questions (need owner input or further investigation)

1. `modules/_boot.py`'s `import sensortask.py` (literal `.py`) — works reliably on real hardware
   (pinned to MicroPython 1.26), but MicroPython's documented freeze/import behavior says it should
   raise `ImportError`. **The mechanism itself is now confirmed, not a mystery**: traced
   directly through the pinned source (`tools/mpy-tool.py`'s frozen-name generation,
   `py/frozenmod.c`'s exact-match lookup, `py/builtinimport.c`'s `stat_module()`/
   `process_import_at_level()`) - a plain `import sensortask` (no `.py`) is unambiguously correct:
   `stat_module()` auto-appends `.py` before matching against the frozen table, while a
   dotted `import sensortask.py` requires "sensortask" to resolve as a *package* (have `__path__`),
   which a flat frozen file never does, so it should raise. **Re-verified at v1.29.0**: `mpy-tool.py`
   did change (`short_name` is now `".".join(name.split(".")[:-1])` rather than a literal `.py`
   strip, plus a new non-ASCII module-name rejection), but the frozen name it produces for a flat
   `foo.py` is identical, and `py/frozenmod.c` is untouched - the analysis stands unchanged.
   the refactor's own generated boot entry (`buildgen.codegen.generate_boot_entry_source()`, since
   Session 6 - `boot_entry/wozi_boot.py` at the time this was written) already does
   `from sensortask_wozi import main` - the correct form - so there's nothing to fix on the
   refactor side. **`modules/_boot.py` itself stays untouched**: it targets the currently-deployed
   1.26 firmware, a different version whose own import machinery hasn't been separately verified
   here - CLAUDE.md's hard rule (don't touch without real 1.26 hardware testing first) still
   applies, and extrapolating from the 1.28/1.29 trace above would be exactly the "changing it
   blind" risk that rule exists to prevent.
2. Config-schema migration is a real data-loss risk on the *current deployed* codebase —
   `ConfigManager` overwrites the entire config file with hardcoded defaults the moment one key is
   missing, so a firmware update adding a config key could silently wipe WiFi credentials/tuned
   values. **Decided: not patched on the current codebase** — accepted (reconfigure via web UI
   after a key-adding update). The refactor's per-sensor config model avoids this failure mode
   structurally, not by patching the current global-JSON codebase.
3. MicroPython version target vs. upstream drift — deployed units run 1.26; the refactor now pins
   **1.29.0**, the newest stable. **Decided**: deployed code stays pinned to 1.26 until a deliberate
   reflash campaign; the refactor is where the version target moves forward. The full 1.28→1.29
   audit is in SPECIFICATION.md Part F.5 (two real findings, several free wins, the rest ruled out);
   the toolchain builds `RPI_PICO_W` firmware at 1.29.0 from scratch with no patches. Earlier
   1.27→1.28 rp2-port changes were RP2350-specific, not RP2040-breaking. Re-run F.1's standing
   re-check whenever the pin moves again.
4. Does `config_manager.py`'s `write_config()` need long-block-lock-style coordination? **Decided
   by the project owner: no** — a write is fast enough not to matter, and it never happens on its
   own/automatically anyway (only ever triggered by a real user interaction via the REST layer),
   which also matters separately for not wearing out the flash with unnecessary writes. No
   coordination mechanism needed. **Note**: `get_long_block_lock()` itself was already removed
   entirely before this was decided (see CLAUDE.md's "Long-blocking operations" hard rule) — this
   decision doesn't resurrect it.
5. ~~Real-hardware verification gap for `asy_udp_socket.py`/`captive_dns.py`~~ — **closed
   (2026-09-08, real bench hardware).** All three UDP-layer claims (garbage-response robustness/
   truncation, connected-socket source-address filtering, POLLERR/POLLHUP delivery) are now
   confirmed on real rp2/lwIP, not just the Unix port (which is structurally unable to exercise this
   transport at all — `ports/unix/modsocket.c` rejects `AsyUDPSocket`'s plain `(host, port)` tuple
   with `TypeError`, worked around for CI purposes only via `digital_twin/_unix_port_udp_addr_shim.py`
   — see `digital_twin/README.md` for that shim's own account):
   - **Garbage-response robustness and truncation**: `tests_hardware/bench/test_network_resilience.py`'s
     `test_ntp_server_sends_garbage_instead_of_a_valid_response`/`test_dns_server_sends_garbage_
     instead_of_a_valid_response` and `test_hotspot_role_reversal.py`'s
     `test_malformed_truncated_packet_is_silently_dropped` — see `tests_hardware/README.md`'s "Fourth
     pass" section. One separately-flagged doc/comment mismatch there
     (`test_dns_flood_backoff_curve_recovers_once_flood_stops`'s own comment claimed the wrong code
     path) is now fixed in place (2026-09-08) — see that file's own note for the corrected account
     and the real, still-open coverage gap it surfaced (no fault in this codebase can currently
     force the actual backoff-growth branch from a bench test).
   - **Connected-socket source-address filtering — CONFIRMED HOLDS**:
     `test_ntp_connected_socket_rejects_a_reply_from_an_unexpected_source`
     (`test_network_resilience.py`) forges a crafted NTP reply from a genuinely different source and
     confirms the DUT's RTC is never corrupted by it — `AsyUDPSocket`'s `mode="client"`
     `sock.connect()` gets real OS/lwIP-level enforcement on this hardware. Also confirmed at the
     mock tier (`tests/test_asy_udp_socket.py::test_client_mode_filters_datagrams_from_unexpected_sources`,
     cross-referenced to this real-hardware result in its own comment) — no twin/flash-tier
     equivalent needed (twin wraps the same sockets the mock tier already exercises; flash tier has
     no bench bridge to build an equivalent against).
   - **POLLERR/POLLHUP delivery — never observed, effectively dead code on this platform.** Real
     rp2/lwIP does not appear to propagate ICMP errors onto a connected UDP socket's poll state —
     `AsyUDPSocket.ready()`'s own `POLLERR`/`POLLHUP` handling is correct, defensive code this
     platform's socket implementation likely never triggers in practice. See
     `tests_hardware/README.md`'s "Known assumptions and open findings" for the probe technique and
     full result.

   Along the way, this also found and closed a genuine gap in the *bench harness itself* (not
   `asy_udp_socket.py`): `bench_control.BenchBridge.redirect_udp_port_to_local()`'s DNAT redirect
   doesn't reliably deliver to a local listening socket on this bench (`route_localnet=0`) — fixed by
   adding `start_udp_source_capture()`/`read_captured_udp_source_port()` (a real wire-level `tcpdump`
   capture, no local delivery needed) as the way to observe a DUT's own outbound request going
   forward. Full account in `tests_hardware/README.md`.

   A related but separate gap this pass also closed, at every tier that meaningfully applies: no
   tier had fast coverage for the *combined concurrent GET+config-write* traffic shape the real
   bench hammer-load test (`tests_hardware/bench/test_memory_stress_bench.py`) exercises. Added
   `tests/test_asy_webserver_service.py`'s Section I.4 (unit tier) and
   `tests/test_digital_twin_webserver_concurrency.py::test_realistic_mixed_polling_and_a_concurrent_real_config_write`
   (twin tier, real assembled system, at `max_connections=4`). Not added to flash tier (no network
   there, see `test_memory_stress.py`'s own header comment) or as a second bench test (already
   covered).
6. ~~Should `asy_wifi_service.py` gain an independent WiFi reachability check?~~ — **closed
   (2026-09-08): investigated, no `src/` change.** The CYW43 firmware/lwIP stack can silently mask a
   real link disruption from `wlan.isconnected()` entirely; decided, with full upstream research
   citations, real bench-hardware recovery-timing data, and regression coverage, in
   `SPECIFICATION.md` Part F.2 - that Part is now this item's complete, permanent, self-contained
   home. Kept here as a closed stub, at its original number, only because several `tests/`/
   `tests_hardware/` code comments still cite it as "BACKLOG.md open question 6" - don't renumber
   this item while those references exist.
7. **Should `asy_webserver_service.py`'s `max_connections=4` be raised?** Confirmed on real
   hardware (dev-bench, hotspot mode): a realistic 8-way concurrent client burst against `/`
   (simulating several phones/tabs hitting the DUT at once) got 7/8 real `302` responses (some
   queued 0.5-1.5s behind Microdot's own accept loop) and 1/8 flatly connection-refused (`000` in
   ~37ms) — `_serve()`'s existing "silently close, no accept, no response ever written"
   reject-when-full behavior working exactly as designed (see `tests_hardware/README.md`'s Fourth
   pass section for the mechanism), just with real, measurable client-visible impact under a more
   realistic burst shape than the pre-existing exactly-at-the-limit tests use. Not fixed — raising
   the cap costs RAM per additional held-open connection buffer on an RP2040 with a fixed, already
   tight budget, a real tradeoff only the project owner should weigh in on; left exactly as-is
   pending that decision. **New real evidence for this same tradeoff (2026-09-04)**: this file's own
   "real, easily-reproducible `MemoryError` under sustained real concurrent HTTP load" entry -
   concrete confirmation that concurrent request handling can already push the heap into real,
   if transient, near-exhaustion troughs at the *current* `max_connections=4` - a data point against
   raising the cap without also addressing headroom, not just a RAM-per-buffer cost argument.
   **Owner's call, 2026-09-11: keep deferred** - stays as-is, revisit only if a real deployment
   symptom makes it pressing.
8. **Two bench-rig capabilities would each move one test candidate from `[MANUAL]` to `[AUTO]` —
   deferred, planned for later (project owner, 2026-09-11).** A programmable GPIO fault-injection
   harness (upgrades the "genuinely wedged I2C bus → watchdog backstop" test) and a dedicated
   second WiFi test client (upgrades the real end-to-end hotspot session; today's host has one
   adapter, already hosting the AP). Both stay `[MANUAL]` until the rig exists — don't re-propose
   building it, and don't substitute a software-only stand-in claiming the same coverage. Migrated
   from the deleted `HARDWARE_TEST_PLAN.md`; surrounding architecture in SPECIFICATION.md Part E.6.
9. **WiFi-reconnect flakiness across the bench suite - root-caused and fixed at the root (was
   tracked here as several separate-looking symptoms; all traced to a small number of real
   causes).** A missing `BENCH_AP_PASSWORD` env var used to cascade into ~25 unrelated-looking test
   failures (the hotspot role-reversal fixture's own flip-back step silently skipped without it,
   leaving the DUT's persisted SSID cleared and unable to rejoin STA even via its own `hard_reset()`
   fallback) - fixed by defaulting to `bench.ap_password()` (reads the real PSK live via
   `nmcli --show-secrets`), no env var required any more. A real association race in
   `join_dut_hotspot()` (`is_ssid_visible()` true one moment doesn't guarantee the following `nmcli`
   scan still sees it) could exhaust its retry budget - fixed with
   `_join_dut_hotspot_with_reverify_retry()` (`tests_hardware/bench/test_hotspot_role_reversal.py`),
   which reconfirms live visibility before every retry instead of a blind sleep. A stale,
   factually-wrong code comment in `_configure_hotspot_ap()` (claiming `STAT_GOT_IP` was STA-only)
   was corrected in place, and a real re-entry guard (`not self.wlan.active()`) was added so a
   genuine re-entry while the AP is already active doesn't blindly reapply essid/password - both
   confirmed on real hardware and covered by new mock-tier regression tests
   (`tests/test_asy_wifi_service.py`). A `hard_reset()`-during-natural-FRAM-backup test was missing
   the same recovery fallback every sibling test already has - added. The hard-reset-recovery
   mechanism itself (`kick_all_stations()` + `hard_reset()`) was independently verified rock-solid
   (28/28 trials, ~9.1s each, zero variance) - not itself a source of flakiness. A bare-`pytest`-
   invocation hang some full-file test runs hit (`tests/test_asy_wifi_service.py`) was confirmed
   transient contention, not a real bug - `scripts/test.sh`'s own per-file timeout+retry mechanism
   (which exists for exactly this) passes clean on the first retried attempt.
10. **A spontaneous, singular `/dev/ttyACM0` USB dropout during a purely passive test - closed, not
    reproducible.** Four systematic reproduction attempts (host-side USB autosuspend, live `dmesg`
    correlation windows, a targeted compounded-reset stress test, a full session-wide `dmesg`
    re-check) found no correlated cause on either the Pi4 or rp2 side. Not worth further
    investigation unless it recurs under normal operation; a `dmesg -T -w`-concurrent capture
    technique is ready to reuse for a real correlated timestamp if it ever does.
11. **CLAUDE.md's "Pre-push verification" recipe had no GCC>=14 host target — CLOSED
    (2026-09-11).** Owner's call: add it alongside noble, not instead of it. Both targets are now
    required by that section, which carries the trixie deltas and the `gcc --version` check.
12. **Does `machine.soft_reset()` reset the RP2040 hardware counter `time.ticks_ms()` derives
    from? - ANSWERED on real hardware (2026-09-11): no, but the question was aimed at the wrong
    mechanism.** Two `mpremote exec` reads 3s apart returned 25769 and 29136 ms (delta 3367): the
    soft reset mpremote performs on raw-REPL entry leaves the counter running, because it is
    free-running hardware time.
    **The real hazard is the watchdog, not the soft reset.** An `mpremote exec` stops `main.py`, so
    nothing feeds the WDT and the board takes a genuine *hard* reset ~8s later - which DOES reset
    the counter. Measured directly: two reads 12s apart returned 1368364 then 5323 ms, the second
    being time since the intervening WDT reset. So `test_ticks_ms_real_2pow30_rollover`'s multi-day
    `board.exec()` polling still corrupts its own measurement, just via the WDT hard reset rather
    than via soft-reset semantics - each poll costs ~8s of uptime and restarts the count. Any real
    multi-day run needs the poll to re-feed or disable the watchdog, or to observe passively
    (`tail_log()`) instead.
13. **Is "reads also blocked while the chip is write-protected" intended? — CLOSED
    (2026-09-11).** Yes: intended and accepted, an access gate rather than data loss. Full
    behaviour, the two properties distinguishing it from the pause gate, and the tier coverage
    (including the silicon-level check only the bench tier can make): SPECIFICATION.md Part A.4's
    FRAM entry.
14. **Adopt `machine.mem_backup()` for reset forensics? — CLOSED (2026-09-11).** No, not in
    normal code; it stays a diagnostic tool to reach for if a severe, hard-to-debug reset ever
    appears that the FRAM logs cannot explain. Capability and decision:
    SPECIFICATION.md Part F.5.4.
15. **Should a transient SPI RX overrun be retried, or left to the task supervisor?** MicroPython
    1.29 added an `OSError(EIO)` raise site to rp2's SPI transfer path for *reading* transfers of
    32+ bytes (SPECIFICATION.md Part F.5.2), reachable here via `asy_fram_driver.py`'s 260-byte
    SGP40 VOC-state read. **Much less pressing than it first looked.** This entry originally said
    the overrun propagates uncaught and kills the reader task; driving it through the real stack
    (see the live-path tests added to `tests/test_asy_fram_manager.py` and
    `tests/test_digital_twin_bus_hazard_concurrency.py`) showed otherwise: `_read_chunk()`'s
    blanket `except Exception` catches it, logs errno 47, and `_read()` then reads block 1, so a
    single transient overrun is **fully absorbed** - correct data returned, block 0 repaired. Only
    an overrun that hits both copies degrades the read to `None`, and even then nothing raises.
    So a retry inside the chunk loop would buy little on a read path the dual-copy layer already
    covers. Still deliberately **not** changed (CLAUDE.md: flag, don't silently fix). Note that the
    interrupted read *does* leave the chunk marked busy and unreadable until rewritten - that is
    intended behavior, not a second bug to weigh here: see SPECIFICATION.md Part A.4's FRAM entry.
16. **A `ResetErrors` PUT landing in the boot window used to clear some modules' error logs and
    silently fail on others — FIXED (2026-09-11).** `PrintLogHistory.reset()` now writes
    unconditionally and claims initialization only once that write succeeds. Mechanism, the
    deliberate asymmetry against `_store_err()`'s own guard, and the tier coverage:
    SPECIFICATION.md Part C.7.
17. **SGP40's compensation-read-from-SCD30 boot race logged a real E/W pair for expected startup
    jitter, not a genuine fault — FIXED (2026-09-12).** `_read_sgp()` now reads each compensation
    field via `getattr(..., None)` before ever calling `float()` on it, the same split
    `asy_notification_service.py`'s own `_check_one()` already used — a field that's legitimately
    still `None` (SCD30 hasn't measured yet) is silent, expected input again, never logged; only a
    genuine exception from the compensation source's own `get_data()` (a violation of its
    never-raises contract) still logs (`errno=18`). Chosen over a global post-boot grace-period
    mechanism in `system_service.py`: the narrower per-call-site fix already matches an established,
    correct precedent with no new cross-cutting timing window to add/tune, and a persistent producer
    failure is still caught and logged by that producer's own driver, not re-detected from this
    side. A full audit for the same class of bug (any cross-module producer/consumer read whose
    exception handling doesn't separate "no data yet" from "a real exception") found no other
    occurrence in `src/` — `asy_notification_service.py`'s own read was already correct, and no
    other cross-module `get_data()`/cross-module value read exists in `src/` today. Mechanism, the
    corrected `errno`/`wrnno` table entry, and regression coverage (mock:
    `tests/test_asy_sgp40_driver.py`; digital twin, against the real wozi wiring:
    `tests/test_digital_twin_sensortask_integration.py`): SPECIFICATION.md Part C.14.2 and C.7.1.
18. ~~SPECIFICATION.md Part A.4's "SGP40 silently degrading to uncompensated VOC when SCD30 is
    down" wording may be imprecise.~~ — **closed (2026-09-12).** Reworded to state the actual
    behavior directly: SGP40 skips the read entirely and returns `SGP40(None, None, None)`
    (confirmed by `tests/test_asy_sgp40_driver.py::test_read_sgp_without_compensation_data_returns_all_none`),
    it never substitutes a fallback/default compensation value. The underlying behavior itself was
    never in question, only the doc wording describing it.
19. ~~BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §2.5's "Worked designs" example is stale.~~ —
    **closed (2026-09-12), and the section itself since removed (2026-09-13).** That document was
    rewritten to state only the final, shipped per-value mechanism (§2.9's design, now the whole of
    what it calls "wiring defaults") — the superseded whole-object `comp_source` worked example this
    item was about no longer exists to go stale. Current implementation:
    SPECIFICATION.md Part C.14.2, BACKLOG.md item 17.
20. **`tests_hardware/bus_topology.py` is a second, hand-kept, unenforced copy of `devices/dev.toml`'s/
    `wozi.toml`'s own wiring facts, and — found while checking it — appears to be dead code today.**
    Found by BUILD_CHAIN_PLAN.md's Session 8 closing-consistency pass (the one real gap that scan
    surfaced against the "every device-specific fact lives in exactly one place" acceptance
    criterion; everywhere else checked was already clean or a previously-documented exception).
    `DEV_I2C_BUSES`/`WOZI_I2C_BUSES`/`DEV_SPI_CS`/`WOZI_SPI_CS` hand-duplicate real per-device I2C
    pins/frequencies, sensor addresses, and the SPI CS pin/FRAM capacity that already live in the
    two real device TOMLs — confirmed still byte-for-byte matching today, but nothing (no test, no
    tooling) cross-checks the two against each other, so a future TOML edit could silently drift
    without this file ever noticing. Worse: nothing in the repo imports `bus_topology.py` at all
    (confirmed by grep) — the real on-target sweep CLAUDE.md's standing bus-hazard rule cites it
    for (`tests_hardware/flash/test_bus_concurrency.py`'s
    `test_bus_topology_autodetect_address_and_reserved_range_sweep`) actually runs a *different*,
    self-contained file (`device_scripts/bus_topology_autodetect_and_hazard_sweep.py`, which carries
    its own third, independent `KNOWN_ADDRESSES` copy, tied to this file only by a plain comment).
    The module's own docstring used to cite "SPECIFICATION.md Part C.8" for an "update-this-file-too"
    rule that doesn't exist there (or anywhere in SPECIFICATION.md) — corrected in place to describe
    the real, current state instead of a fictional cross-reference (dangling-citation fix only; no
    behavioral change). **Not fixed further** — genuinely the project owner's call, not a mechanical
    cleanup: whether `bus_topology.py` should be deleted as dead code, whether
    `bus_topology_autodetect_and_hazard_sweep.py` should import its `KNOWN_ADDRESSES` from it instead
    of keeping a third copy, and whether CLAUDE.md's own bus-hazard rule should drop the citation or
    point at a real, live consumer, are all real design decisions this pass didn't make unilaterally.
21. **SPECIFICATION.md Part H.5.1's `dispatch: true` claim doesn't match the real `wozi.json`/`dev.json`
    for two of its five named fields.** Part H.5.1 says `dispatch: true` "marks a repeatable command
    field (H.6, minus `ContMeas`)" — i.e. every field in H.6's dispatch-only list
    (`SystemCmd`/`PauseTime`/`lightCmdLED`/`ResetErrors`/`SGPResetVOC`) except `ContMeas`. Confirmed
    directly against `html/definitions/wozi.json`: only `SystemCmd`/`ResetErrors`/`SGPResetVOC`
    actually carry `dispatch: true`; `PauseTime` and `lightCmdLED` (both instances) carry none.
    `buildgen/definitions.py` faithfully reproduces this real, golden behavior either way, so this is
    a pre-existing spec-vs-reality mismatch to resolve with the project owner (which side is actually
    correct — the doc's claim or the shipped JSON), not a generator bug. Found by
    BUILD_CHAIN_PLAN.md's Session 4 post-merge self-audit; had never been migrated to this file before
    now, so it stayed unresolved and easy to lose track of.

## Deferred / explicitly out-of-scope work
- **Session 7's `pyproject.toml` `max-args` ratchet (21 → 22, for `WebserverService.__init__`'s new
  `build_info=` parameter) only got the noble leg of CLAUDE.md's required two-target clean-chroot
  pre-push verification.** The trixie leg — required by the same rule whenever `pyproject.toml`
  changes, specifically to catch a GCC>=14-only issue the noble/GCC-13 leg can't see (the precedent:
  the mbedtls `-Warray-bounds` false positive, SPECIFICATION.md Part B.7.1) — couldn't be run from
  that session's own sandbox: `debootstrap --variant=minbase trixie` needs `deb.debian.org`, which
  the sandbox's egress policy rejected outright (confirmed directly, not a transient failure), with
  no alternate Debian mirror to fall back to. The change itself is a pure ruff/pylint lint-rule
  threshold with no compiler-version sensitivity, so the residual risk is judged low, not zero — a
  from-scratch trixie leg (or a run on the bench Pi4, which already runs trixie/GCC 14.2) should
  still confirm it whenever one is next convenient. Full account: BUILD_CHAIN_PLAN.md's "Session 7
  done" entry.
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
  "unrecognized" (BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md's "Known limitation" section). The large half —
  deriving the schema from each driver's own constructor signature, or from a new declarative tuple
  beside `_WIRING` — needs real design, not a mechanical continuation, and hasn't been started.
- **`[device].name`/`hostname`/`hotspot_password` are validated but never wired into any boot
  path.** Confirmed against the generator (`buildgen.generate.generate_device()`): neither
  `AsyConnTime.__init__` nor any generated `sensortask_<device>.py` has a constructor-time
  injection point for them. `Hostname`/`HotspotPW` are ConfigManager-
  persisted runtime values with one hardcoded shared default (`"SensorNode"`/`"12345678"` —
  `asy_wifi_service.py`'s `_VAL_HOST`/`_VAL_HOTSPOT_PW`), identical in every device's frozen build,
  so **every device today actually boots as `SensorNode`**, whatever its `devices/*.toml` says. The
  TOML values are schema-checked and otherwise inert. **Still not fixed as of Session 6** (build
  chain + CI matrix + digital-twin test generalization) — that session's own finish criterion was
  eliminating the hand-written `sensortask_wozi.py`/`sensortask_dev.py` entry points, not this gap.
  Fixing it needs either a `src/` constructor-time override mechanism (`asy_wifi_service.py`'s
  `AsyConnTime.__init__` would need real `hostname=`/`hotspot_password=` parameters — several
  existing tests assert the literal `"SensorNode"`/`"12345678"` defaults) or a build-artifact
  config-seeding step — not a `buildgen/`-only change. A tripwire test
  (`test_hostname_and_hotspot_password_are_not_yet_wired_into_generated_code`) and a code comment in
  `validate.py` hold the current state in place so the gap can't quietly change shape unnoticed.
- **The 1.29.0 pin is now field-proven on the dev bench (2026-09-11).** Real `dev` firmware built
  from `src/` and flashed; `sys.implementation` on target reports `(1, 29, 0)` / `_mpy=4870` /
  `RPI_PICO_W`. Flash tier (25 passed), bench tier (85 passed) and the mid soak tier (4 passed) all
  ran clean against it. Deployed units stay on 1.26 regardless (open question 3). Of the three items
  that wanted on-target confirmation beyond just running the existing suites, **two are now closed**:
  - **The new SPI `OSError(EIO)` raise site** (Part F.5.2, open question 15) - **confirmed as far as
    target allows.** Its live path, `asy_fram_driver.py`'s 260-byte SGP40 VOC-state read, passes on
    real hardware at 1.29, so the DMA path is genuinely exercised. Answering #15 properly still
    needs a real overrun *observed*, which no Python-level knob can induce; the consequence is
    covered instead - see the RX-overrun entry below.
  - **That `I2C.deinit()`/`SPI.deinit()` really are silent no-ops** (Part F.5.1) - **done
    (2026-09-11)**, pinned down exactly where this entry suggested, by
    `device_scripts/bus_deinit_is_a_noop_on_real_hardware.py` +
    `test_i2c_and_spi_deinit_are_silent_noops_and_each_bus_id_is_a_singleton`. On live silicon an
    `i2c.scan()` returns the identical device list after `deinit()` and a real FRAM read still
    succeeds after `machine.SPI.deinit()`; the same script also confirms the static per-bus
    singleton claim (`machine.I2C(id) is machine.I2C(id)`) that the two fakes deliberately diverge
    from. Previously only fake-vs-fake agreement.
  - **The SRAM-resident-code change - settled 2026-09-11, project owner's call: the question is
    RAM, not speed.** No timing run is wanted, and the linker-map figure is never to be quoted as a
    measured speedup. The headroom it leaves is now measured on real hardware and gated by
    `tests_hardware/flash/test_memory_stress.py`'s
    `test_real_gc_heap_headroom_survives_a_full_system_build`; figures and reasoning in Part F.5.3.
- **The SPI RX-overrun error path shall be tested** (project owner's explicit direction,
  2026-09-10). MicroPython 1.29's new `OSError(EIO)` raise site (SPECIFICATION.md Part F.5.2),
  across the tiers CLAUDE.md's standing bus-hazard rule asks for. **All four are now done**;
  what they found is open question 15 above.
  - **Mock tier, raise-site semantics - done.** `tests/test_asy_spi_driver.py`: a write never
    raises, a sub-32-byte read never takes the DMA path so cannot overrun, a 32+ byte read raises.
  - **Mock tier, live path - done.** `tests/test_asy_fram_manager.py`'s four live-path tests inject
    the fault at the `machine.SPI` boundary and let it travel the real
    `asy_spi_driver` → `asy_fram_driver.get_values()` → `_read_chunk()` chunk loop. This needed a
    real gap closed first: `tests/_fram_chip_fake.py` overrides `readinto()` and so shadowed the
    base fake's own fault check, leaving the bus-level knobs unreachable through the FRAM stack.
  - **Digital twin - done.** `digital_twin/machine.py`'s SPI gained the same size-gated
    `rx_overrun`/`rx_overrun_remaining` model (the chip-level `FaultInjector` is the wrong place:
    it cannot express the 32-byte threshold, so it would raise on a 1-byte status read that real
    hardware could not fail). Exercised against the real booted object graph in
    `tests/test_digital_twin_bus_hazard_concurrency.py`.
  - **Real hardware - done (2026-09-11), and deliberately not a fault-injection test.** An RX
    overrun is a DMA timing condition; nothing reachable from Python on the device can induce one,
    so there is no on-target equivalent of the knob the other three tiers use. Both halves of what
    a bench run *can* do are now covered: the 260-byte SGP40 VOC-state read (the only path in this
    codebase past the 32-byte DMA threshold) passes on target at 1.29 via
    `tests_hardware/flash/test_fram_storage.py`'s existing backup/restore test, proving the DMA
    path is exercised at all; and the **consequence** rather than the cause is now pinned down by
    `device_scripts/fram_busy_status_lockout.py` + `test_both_blocks_left_busy_lock_the_real_chunk_
    until_it_is_rewritten`, which writes `_STATUS_BUSY` into both blocks' status bytes through the
    real driver and confirms the chunk reads back `None` with a real error logged, then recovers on
    a rewrite - the intended destructive-readout protection of SPECIFICATION.md Part A.4's FRAM
    entry, now proven on the real chip rather than only modelled.

- **`tests_hardware/device_scripts/`'s two real-hardware bugs are fixed but NOT re-run on the
  bench.** Moving that directory into the MicroPython mypy pass (commit 08529d1) is what surfaced
  them; both are grounded in source, not inferred, but neither has been executed against real
  hardware since:
  - `fram_write_protect_roundtrip.py` called `set_write_protected(False)` positionally at four
    sites. `ca767ba` ("wave 2 - FBT/A002 signature changes") made that parameter keyword-only in
    `src/asy_fram_driver.py` and never updated this caller, so every run since has raised
    `TypeError` on the script's first call. Now `set_write_protected(value=...)`.
  - `wifi_service_reconnect_repro.py` called `task.exception()`. MicroPython's `Task` has no such
    method - `extmod/modasyncio.c`'s `task_attr` exposes only `coro`/`data`/`state`/`done`/
    `cancel`/`ph_key` - so the line raised `AttributeError` at exactly the moment it was trying to
    report why a task died. Now `task.data`, which `extmod/asyncio/core.py`'s
    `run_until_complete()` sets to the terminating exception. The 1.28 stub package did not
    declare `data` and the line needed a `# type: ignore[attr-defined]`; the 1.29.0 stubs do
    declare it, so the ignore is gone.
  A flash-tier run should confirm both, whenever one is next scheduled.
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
- **Additional checker candidates, measured and mostly declined.** Evaluated against the real tree
  rather than by reputation, when shellcheck/actionlint/zizmor were added:
  - **`zizmor`** (GitHub Actions security) - **adopted.** All 50 findings fixed, not suppressed:
    `excessive-permissions` (workflow-level `permissions: {}` + per-job `contents: read`),
    `artipacked` (`persist-credentials: false` on every checkout), and `unpinned-uses` (SHA-pinned
    `codecov/`+`dorny/`; `actions/*` stays tag-pinned by an explicit `.github/zizmor.yml` policy,
    since a compromise of GitHub's own org compromises the runner anyway and SHA-bumping four
    first-party actions has real cost with no Dependabot configured). One audit is **disabled with
    cause**: `self-repository` wants `uses: $/.github/...` (GitHub's July-2026 syntax), which
    actionlint 1.7.12 - the other hard gate over the same files - rejects outright as invalid.
    Revisit when actionlint learns it. Runs `--offline` so it behaves identically in CI, on a dev
    box, and in the clean-chroot pre-push recipe.
  - **`import-linter`** - **rejected, measured; structurally incompatible.** It validates that every
    `root_packages` entry is a real package and refuses flat modules ("'x' is a module, not a
    package"), and `src/` is deliberately a flat set of modules with no `__init__.py` - they are
    copied flat alongside `ext/` and frozen into firmware. Both workarounds were tried and both
    produce a **false green**: wrapping `src/` in a shadow package (or letting it resolve as an
    implicit namespace package) reports `Analyzed 27 files, 0 dependencies` and marks every
    contract KEPT, because each intra-`src/` import is a bare absolute `from base_classes import
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
    as of 2026-09-04 (one real attempt this session was aborted by an unrelated cascading DUT-
    unreachable failure elsewhere in the same run - see this file's own `BENCH_AP_PASSWORD` entry -
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
    a substitute for the full 6h window this item was always about.
- **Website definitions-file autogeneration — done (BUILD_CHAIN_PLAN.md Session 4).** The
  `@web`/`@web-group` comment-tag family and `buildgen/definitions.py`'s generator now exist,
  resolving every open question this entry used to track (anchoring a non-driver-schema value like
  `lightCmdLED`, `@web-group`'s relationship to `SettingsGroup(...)` wiring, the formal grammar's
  scope) — see BUILD_CHAIN_PLAN.md's own "Session 4 done" account for the resolutions and
  `tests_scripts/test_buildgen_web_tag.py`/`test_buildgen_definitions.py` for the test coverage.
  Generating `html/definitions/<device>.json` for real was Session 6's own job; that session
  closed two of its three parts — `arzi`/`klkizi`/`grkizi`/`schlafzi` (the four devices that never
  had a hand-written file) now get one generated on the fly by `scripts/build_website.sh`'s own
  fallback, and this is wired into CI's 6-device `firmware-build-verify` matrix. **Still open**:
  retiring `wozi`/`dev`'s own hand-written `html/definitions/{wozi,dev}.json` in favor of generated
  output — deliberately deferred, since `tests_js/live-backend-put-matrix.test.js`/
  `mock-server-put-matrix.test.js` read those two files directly as fixtures and switching them
  over needs a `tests_js/` fixture audit no session has done yet (BUILD_CHAIN_PLAN.md's "Session 6
  done" account). **The same wozi/dev-only scope shows up in the browser prototype too**: `js/
  app.js`'s `KNOWN_DEVICES = ["wozi", "dev"]` (its `?device=` switch, prototype-only per that file's
  own docstring — real firmware ships exactly one device's `definitions.json`, never branches on a
  query param) is a real, literal device-name list living outside `devices/*.toml`, but it isn't an
  independent gap: it exists because `mockdata/`/`html/definitions/` only carry fixtures for those
  two devices, the same limitation this entry already tracks. Extending it to all 6 needs generating
  `mockdata/<device>.json` fixtures for the other four first, not just a `KNOWN_DEVICES` edit — found
  by BUILD_CHAIN_PLAN.md's Session 8 closing pass, flagged here rather than fixed piecemeal.
- **`scripts/build_firmware.py dev` confirmed the real, correct way to build/flash for the dev
  bench — Resolved (2026-09-03).** Device-parametrized boot-entry
  selection was real then via `boot_entry/<device>_boot.py` (that directory is retired now, replaced
  by `buildgen.codegen.generate_boot_entry_source()` — Session 6, above), and the earlier "wozi's own pins forced onto
  dev hardware" mismatch that produced noise mistaken for real bugs (once tracked as the open
  questions list's own item 7) no longer has anything to stand in for. `dev_legacy/README.md`'s
  mounted-entry-script recipe remains a valid, lighter-weight path for driver-level bring-up/
  debugging (watchdog off, no flash write), but is no longer the *only* valid way to run the real,
  wired-together system on this hardware — `scripts/build_firmware.py dev` (watchdog armed, the
  real production-shaped path) is now the one to use for actual verification work. **Never
  `scripts/build_firmware.py wozi` against this bench** — `wozi` is never physically flashed, only
  `dev` is (CLAUDE.md's hard rule); that mismatch is exactly what produced the noise this item
  originally described.
- **Manual cross-browser/cross-device spot check not yet done — needs the project owner directly.**
  Automated coverage (Part H.7's cross-browser smoke script, Vitest's browser-mode suite) only ever
  exercises Chromium/WebKitGTK/Firefox/Edge on Linux CI runners — Part H.1's "stable and
  good-looking on major mobile/desktop browsers" goal still wants at least one real human pass on
  real Safari and a real mobile device, which no automation here can substitute for.
- **UART sensor integration — confirmed staying unwired, not just deferred.** `asy_uart_driver.py`
  is promoted to `src/` but deliberately not wired into any `sensortask-*.py`; `asy_uart_comm.py`
  (its one real consumer) is its own separate, still out-of-scope promotion. Not a legacy deployed
  feature, so wiring it in would be a scope addition beyond feature-parity, not a postponed fix -
  owner-confirmed this stays as-is.
- **Owner requirement for the final wiring stage — fulfilled, entry kept only until the large
  post-merge audit closes.** Every `sensortask-*.py` built as part of the real rewrite needs a full
  Unix-port equivalent, runnable on a local computer, with whatever hardware is physically
  unavailable there mocked at the lowest level of bus data exchange (i.e. the same mocking boundary
  SPECIFICATION.md Part E.4/`tests/machine.py` already establish for unit tests — fake
  `machine.I2C`/`machine.SPI`/etc. byte-level transactions, not higher-level driver stand-ins) so the
  whole wired-together sensortask can be exercised as close to the real target as possible without
  physical hardware. **Fulfilled**: `digital_twin/` is the lowest-level-mocking module this
  requirement calls for (see `SPECIFICATION.md` Part A.10), and `scripts/run_unix_port_integration.sh`
  runs the whole wired-together (buildgen-generated) `sensortask_wozi.py` against it end to end (see
  `digital_twin/README.md`'s "Swapping the twin in for a Unix-port run" section). This entry should
  come out once the whole effort's large post-merge audit closes, per this file's own stated
  resolved-item policy — not yet removed on its own, since that audit hasn't closed yet.
- **Config-duplication centralization** — same keys hand-kept in sync across `_DEFAULT_CONFIG`, the
  REST handler, and the HTML form. Owned by the refactor: each promoted `*_Reader`'s own `_VAL_*`
  schema tuple + `get_dict_cfg()`/`get_dict_data()` is the intended single source, not fully wired
  end-to-end yet (`sensortask-wozi.py` itself predates the per-sensor-config model — see "Refactor
  targets not yet done" above).
- **`dev` config quirks** (e.g. LED/Neopixel REST routes referencing an uninstantiated object) —
  bench rig only, not bugs to fix.
- **`js/nav.js`'s `initNav()` registers a `document`-level `keydown` listener with no matching
  removal** — harmless today (called exactly once per real page load), but a latent leak if it's
  ever called more than once without a full page reload (e.g. a future hot-reload path, or a test
  file that calls it repeatedly against the same `document`). Worth a `removeEventListener`/cleanup
  return value if that ever becomes a real scenario.
- **`selectSection()` is duplicated near-verbatim between `js/app.js` and `js/main.js`** (both
  entry points build their own local closure over `onSelect`/nav rebuild). Low priority: the two
  entry points are deliberately separate (prototype vs. production, Part H.2), and the duplication
  is small: extracting a shared helper is a minor simplification, not a correctness fix.
- **Dev/build environment setup**: toolchain installer is done (`toolchain/setup_toolchain.py`, see
  SPECIFICATION.md Part B/README.md's "Toolchain setup"). `build-*.sh`'s hardcoded path/`py-include`
  dependency is now fixed too (see "Refactor targets not yet done" above).
  `update_and_install.txt` re-verified against current upstream docs — structurally still accurate,
  but missing the pico-sdk 2.0.0+ picotool major.minor version-matching requirement (already applies
  today) and the full apt package list. An official one-shot alternative exists
  ([`raspberrypi/pico-setup`](https://github.com/raspberrypi/pico-setup)'s `pico_setup.sh`), worth
  considering as a base.
- **`asy_wifi_service.py`'s locking-contract inconsistency and 60s-retry priority-inversion cost** —
  see SPECIFICATION.md Part C.8 for the full account. Still not picked up: a rename to make
  `network_available()`'s already-held-lock contract visible in its own name (e.g.
  `network_available_locked()`) was considered but not done — nothing blocks it now that
  `improved-quality/sensortask-wozi.py` is deleted, but `buildgen/codegen.py` itself still generates
  a call to it by the current name, so this remains a real (if small) call-site update.
- **`asy_i2c_driver.py`'s `get_bits`/`set_bits`/`get_register_struct` still call the allocating
  `readfrom_mem()` rather than zero-copy `readfrom_mem_into()`** — no real caller needs the
  zero-copy path yet, but worth doing before `asy_isl29125_driver.py` (its one plausible future
  caller) is migrated.
- **`asy_scd30_driver.py`'s persistent NVM setters have no published write-cycle endurance figure**
  (checked every available Sensirion doc) — safe today only because every setter is REST-triggered,
  never called from a boot path or periodic loop. Don't add a periodic/high-frequency caller
  without reconsidering this.
- Network fault injection against the real dev bench unit is complete:
  `BenchBridge.inject_network_degradation()` (`tc netem` on `wifi_iface()` only) covers loss,
  latency+jitter, corruption, duplication, and reordering, exercised by
  `tests_hardware/bench/test_network_resilience.py`. CYW43-firmware-level faults (e.g.
  `wlan.connect()` itself raising) aren't network-path faults `tc`/`iptables` can express — those
  stay covered by the digital twin's own `--fault wlan:...` hook instead.
- **Still open**: the NTP-outage-x-bus-load fault recombination has no twin/mock-tier equivalent
  (no NTP-drop-and-retry scenario exists at either tier to extend) — a real opportunity if a future
  session has the budget, not chased yet. The other two recombinations that matter (FRAM write vs.
  a real hardware reset; repeated WiFi flapping x concurrent bus load) already have coverage across
  every tier where they're meaningful.
- ~~A real device-side traceback at boot - `AttributeError: 'NoneType' object has no attribute
  '__aexit__'` in `asy_sgp40_driver.py`'s `_store_sgp()` calling `base_classes.py`'s
  `_set_meas_data()` (`async with self._datalock:`)~~ - **closed (2026-09-08), confirmed
  impossible against the current code, no hardware time needed.** Re-checked `base_classes.py`
  directly: `self._datalock = asyncio.Lock()` (line 171) is set unconditionally and synchronously
  in `SensorReader.__init__()`, with no conditional/lazy-init path anywhere - there is no code path
  under which an already-constructed `SensorReader` (or its `SGP40_Reader` subclass) could ever
  have `self._datalock is None` when `_set_meas_data()` (line 212) runs. Line numbers still match
  this file's own already-documented finding exactly (`_store_sgp` at line 349,
  `_set_meas_data` at line 211, matching the "349"/"211" cited against `c177608`) - the mismatch
  against the original traceback's reported line numbers (224/159) stands confirmed, not just
  suspected: the DUT was provably running a stale, earlier-flashed firmware image at that moment,
  not the code this repo actually ships. Same "singular, not systematically reproducible, closed
  without further hardware time" disposition as the USB-dropout and WDT-reset items - not a real
  bug in the current codebase.
- **Real, fully root-caused and fixed `MemoryError` under sustained concurrent HTTP load (2026-09-04→08).**
  A real, reproducible `MemoryError` under sustained concurrent HTTP load (dozens of occurrences
  within minutes) traced to `GET /status`'s single `json.dumps()` over the whole aggregate response
  (~5.7KB, at a real 17-module registration scale) — already caught cleanly by the existing blanket
  exception handling (no crash, no leak; a `gc.mem_free()` trace confirmed a healthy sawtooth
  pattern, not monotonic decline). Fixed by streaming the response as size-bounded JSON fragments
  (`_coalesce_json_fragments()`/`_append_coalesced_object()`, `_MAX_STATUS_PIECE_BYTES=1024`) plus
  `gc.threshold(32768)` as defense in depth — both confirmed on real hardware (0 MemoryErrors over a
  10-minute hammer load that previously produced 237). Two platform facts found while building this
  (MicroPython's `async def ... yield` "async generator" is broken, not just absent — segfaults the
  interpreter; over-fragmenting the response regresses throughput independent of memory safety) live
  permanently in SPECIFICATION.md Part F.1; the full audit that generalized this fix to every other
  GET route, the GC-threshold real-hardware data, and the real-hardware confirmation all live in
  SPECIFICATION.md Part I; the standing handling discipline is CLAUDE.md's memory-safety-discipline
  hard rule. A related, separate bug found and fixed along the way: every command-only/special-alone
  config field write (e.g. SGP40's `SGPResetVOC`) logged a spurious `CFGMGR_*` errno=8 — fixed in
  `base_classes.py`'s `_set_dict_cfg()` (filters its pre-write snapshot fetch down to genuinely
  persisted keys), with regression coverage in `tests/test_base_classes.py`.
