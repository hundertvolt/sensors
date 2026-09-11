# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

## Refactor targets not yet done

- **No CI firmware-build stage yet for the legacy `build-*.sh` scripts.** The *new*, `src/`-based
  toolchain (`scripts/build_firmware.py`, `SPECIFICATION.md` Part B.11) already has this
  (`.github/workflows/ci.yml`'s `firmware-build-verify` job builds a real `firmware.uf2` on every
  push/PR) - the legacy `python/`+`build-*.sh` pipeline is a separate, still-uncovered path.
- **Mypy shall be configured to disallow `Any` types** (owner-specified). Mostly addressed, but
  not by the flag it was originally written about: all three passes now run full `--strict`
  (`disallow_any_generics` included), so no *implicit* `Any` from a bare `dict`/`list`/`tuple`
  survives anywhere in scope. What is still open is `disallow_any_explicit` - 226 findings in the
  main pass, 45 in `digital_twin/`, 17 in the host pass - plus `disallow_any_unimported` (54, main
  pass only). Explicit `Any` appears 107 times in `src/` and 213 in `tests/`. A large share of the
  test-side uses are monkeypatch/wrapper classes duck-typing a real MicroPython object; the `src/`
  side is largely legitimate (`print_log.py`'s variadic logging methods, `config_manager.py`'s
  generic value-checking helpers, opaque `ticks_ms()`-typed values). Turning `disallow_any_explicit`
  on still needs a typing strategy for the test wrappers (e.g. `Protocol` classes + `__getattr__`
  delegation) and a decision on the genuinely-variadic/opaque `src/` cases - not just a flag flip.
- **FRAM has no periodic/triggered *production* re-probe policy.** `verify_present()`/
  `set_write_protected()` (bus-hazard-tested across all four tiers, confirmed correct under real
  fault injection - see CLAUDE.md's bus-hazard hard rule) have zero real callers in `src/` - an
  explicit, undecided design question (who calls `verify_present()`, on what trigger) for whenever
  it's actually wanted.
- **No standardized timeout/cancellation mechanism yet for blocking calls that genuinely can be
  timeout-wrapped** (FRAM SPI transactions, `src/asy_udp_socket.py`'s own `select.poll`-driven
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
  done; (3) bus/sensor error-recovery robustness items above, which build on that structure; (4)
  remaining tooling/CI (the firmware-build stage) — mypy/ruff/stubs/Unix-port-tests were pulled
  forward out of this order already, once `math_helpers.py` cleared the `src/` bar, and that's now
  standing practice for every new file, not a one-off.

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
   `boot_entry/wozi_boot.py` (the refactor's own entry point) already does
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
8. **Two real-hardware bench-rig capabilities, flagged as "not currently provisioned" during the
   original `tests_hardware/` design discussion, each gating one test candidate from `[MANUAL]` to
   `[AUTO]`** (migrated from the now-deleted `HARDWARE_TEST_PLAN.md` — see SPECIFICATION.md Part
   E.6 for the surrounding architecture these would extend): a programmable GPIO fault-injection
   harness on the bench rig, which would upgrade the "genuinely wedged I2C bus → watchdog backstop"
   manual test to automated; and a dedicated second WiFi test client on the bench rig (today's bench
   host has only the one WiFi adapter, already hosting the AP), which would upgrade "real end-to-end
   hotspot session" from a manual test to automated. Neither is assumed worth building — flag to
   the project owner as an explicit choice, not a default plan, if either ever becomes relevant.
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
11. **CLAUDE.md's "Pre-push verification" clean-chroot recipe has no GCC>=14 host target.** The
    existing recipe only builds an Ubuntu 24.04 "noble" chroot (GCC 13.x), which is exactly why the
    real mbedtls `-Warray-bounds` false positive (`SPECIFICATION.md` Part B.7.1, fixed via
    `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND`) wasn't caught by it — that bug was only found by
    testing directly on a Debian trixie (GCC 14.2) bench host outside this recipe. Whether to add a
    second trixie/GCC>=14 chroot target to the standing recipe (and if so, alongside or replacing
    noble) is an open choice for the project owner, not decided or built here.
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
13. **Is "reads also blocked while the chip is write-protected" the intended, accepted behavior of
    `FRAM_SPI`'s busy-flag protocol?** `_AsyBaseFramChunk._read_chunk()`'s busy/idle status-byte
    protocol needs to WRITE a transient busy marker before it reads data, so a real write-protected
    chip makes `chunk.read()` return `None` too, not just `chunk.write()` — confirmed directly on
    real hardware (`tests_hardware/device_scripts/fram_write_protect_roundtrip.py`). Not decided
    here; a project-owner call. **Refreshed 2026-09-11**: the repaired script has now been re-run -
    `test_write_protection_actually_gates_a_real_write` passed in a full bench-tier run - so the
    recorded-but-unrefreshed caveat is resolved and the observation stands as current. The behaviour
    question itself (is reads-also-blocked intended?) is still an open owner call.

14. **Adopt `machine.mem_backup()` for reset forensics?** New in 1.29, on by default on rp2, and
    confirmed present in this project's own built firmware: 28 bytes of watchdog-scratch storage
    that survives a WDT reset and `machine.reset()`, lost only on power-off — SPECIFICATION.md
    Part F.5.4. That is exactly the reset class the 2026-09-08 `WDT_RESET` post-mortem couldn't
    diagnose, and unlike the FRAM logs it costs zero wear. Needs a project-owner call on what to
    record (last supervisor phase? last tick? failing task id?) and where the write belongs. Not
    started.
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
16. **A `ResetErrors` PUT that lands before the FRAM-backed loggers finish `setup()` is silently
    dropped, and the restore then puts the old history straight back.** Found while making the
    digital-twin suite's error-persistence checks sound (2026-09-11). The webserver starts answering
    well before every `PrintLogHistoryStore.setup()` has run, and `print_log.py`'s `reset()` returns
    early with a `_diag()` when `not self.initialized` - deliberately, so stale state is never
    written to FRAM before the restore has happened. The consequence is that a `PUT /status
    {"ResetErrors": true}` issued in that startup window clears only the RAM ring, is never
    persisted, and is then overwritten by `setup()`'s own `_read()` - a client gets a `200` and the
    history reappears seconds later. Narrow (a boot-window race only), and the guard it comes from
    is correct in itself, so nothing was changed - flagged, not fixed, per CLAUDE.md. Options if it
    ever matters: defer the webserver's start until the loggers are initialized, queue a pending
    reset to apply after `setup()`, or answer `503` for a reset issued before initialization.

## Deferred / explicitly out-of-scope work
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
  - **Still open: the 12,918 B SRAM-resident-code win** (Part F.5.3) is a linker-map measurement,
    not a measured runtime speedup - don't quote it as one until a bench timing run backs it up.
    The 2026-09-11 bench session deliberately did not time it.
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

- **The four legacy `build-*.sh` scripts carry 28 shellcheck findings, including no shebang at
  all.** `scripts/lint.sh` and CI run shellcheck over `scripts/` only, where all 14 modern scripts
  are already clean - so that lane was a free ratchet. `build-arzi.sh`/`build-dev.sh`/
  `build-neu.sh`/`build-wozi.sh` are the same pre-refactor generation as `python/`+`modules/` and
  stay out of scope by that same standing decision. What is actually in there: **SC2148 x4** - none
  of the four has a shebang line, so they work today only because whatever invokes them happens to
  be bash; **SC2164 x21** - `cd` without `|| exit`, so a failed `cd` silently continues in the
  wrong directory (in the build scripts that means writing output somewhere unintended); **SC2103
  x5** - `cd ..` back instead of a subshell. All mechanical, none urgent, all real. Fold in
  whenever the legacy build path is next touched.
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
  tests boot_entry tests_hardware/device_scripts` and a bare local `scripts/typecheck.sh` - includes
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
- **Website definitions-file autogeneration — not yet built.** `html/definitions/<device>.json`
  (Part H.5) is currently hand-written. A worked, already-checked-against-real-code *sketch* exists
  for deriving most of it at build time from `#`-prefixed comment tags placed above each driver's
  `ConfigSchema` tuple (most fields — `min`/`max`, toggle/string/enum/number `kind`, special/enum
  option values — are already inferable from the schema tuple itself with no tag at all; a tag only
  needs to supply what the tuple can't: `label` (required), `unit`, `description`, an occasional
  `kind` override for a non-`ConfigSchema` value like `asy_webserver_service.py`'s `_SYSTEM_CMDS`,
  and `special:<value>="<meaning>"` for a sentinel/enum-option's human-readable meaning). Grammar:
  `# @web <key>=<value> <key>="<quoted value>" ...` for a per-field tag; `@web-group` for a
  module-level tag (`label`, `endpoint`, optional `submitGroup`). Three worked examples against real
  `src/` code: a sentinel special value (`asy_scd30_driver.py`'s `AmbPres`), a toggle needing no
  `kind` tag at all (`SelfCal`), and an enumerated field (`asy_bmp3xx_driver.py`'s `PressOvers`, six
  `special:` entries becoming six labeled `options`). **Not a decision** — no parser has been built
  and no `src/` file carries these tags yet. Left open, case by case, for whoever builds the real
  parser: where the composite `lightCmdLED` shape (r/g/b/t) and other non-driver-schema webserver
  values anchor a tag at all; whether `@web-group`'s `endpoint`/`submitGroup` belong on the schema
  declaration or should instead read off `src/sensortask_wozi.py`'s own `SettingsGroup(...)`
  construction-site wiring (which already states the same grouping, risking silent drift if tagged
  twice); a full formal grammar (escaping a `"` inside a quoted value, etc.) was deliberately not
  attempted, since the sketch's job was proving the *shape* of the idea against real code, not being
  implementation-ready.
- **Per-variant `sensortask-*.py` generator — not yet built (the automated version specifically;
  one real, hand-written second variant now exists).** SPECIFICATION.md Part A.3 already names the
  automated generator as a real planned direction (one setup-definition file → every variant's
  `sensortask-*.py`/website pair), shaped for by A.8's registration-API/A.9's `HTML_SRC_DIRS`
  mechanisms. `src/sensortask_dev.py` (2026-09-03) is the first
  concrete step toward it — a real, hand-written, `src/`-quality dev-bench variant carrying the
  same three sensors as wozi (SCD30 + BMP3xx + SGP40), built and flashed for real via
  `scripts/build_firmware.py dev`/`boot_entry/dev_boot.py`, confirmed clean on real hardware
  (6.5-minute stability window, real sensor readings, real captive-portal redirect). It's an
  interim baseline, not the generator itself — deliberately not over-invested in permanence, meant
  to be replaced once the generator lands. Two concrete requirements for whenever the generator is
  actually built, so they aren't lost
  between now and then: (1) any hardware-presence-conditioned wiring `sensortask_wozi.py` currently
  hardcodes for its own fixed sensor set — which FRAM chunks get allocated (Part A.7's seven-chunk
  order is wozi-specific) and any sensor-specific bus parameter (e.g. SCD30's own I2C
  clock-stretch `timeout=200000`) — must be derived from the target variant's actual module set,
  not copied verbatim into a variant lacking that sensor; (2) **every generated variant needs its
  own real unit tests** (owner requirement - a generated `sensortask-*.py` is exactly as much "real
  code" as a hand-written one, same Part D bar applies; the build script that generates the
  `sensortask-*.py`/test pair is also the natural place to activate/select which of the generated
  tests actually run for a given variant, rather than a separate manual step), and those tests must
  themselves check which sensors/FRAM a given variant actually has before asserting anything
  sensor- or FRAM-specific — asserting e.g. `scd_reader.pr.fram is not None` unconditionally against
  a variant with no SCD30 (or no FRAM at all) would either hard-fail on a module that was never
  supposed to exist, or - the sharper risk - pass vacuously for the wrong reason if the assertion is
  generated loosely enough to skip rather than genuinely check. A variant-specific test also can't
  hardcode *which bus* a sensor sits on (SCD30 is wired to `i2c0` on wozi, but a different variant
  could wire it to `i2c1` or a third bus entirely) — it must look the bus up through the sensor's
  own object graph (e.g. `scd_reader.scd.i2c_scd30.i2c_device.i2c`), never assume a specific
  `i2cN` name. `tests/test_sensortask_wozi.py`'s own
  `test_scd30s_own_i2c_bus_uses_a_clock_stretch_timeout_wide_enough_for_it` is the worked example
  this generalizes from (both the bus lookup and the FRAM assertions), not a template to copy
  unconditionally. **Resolved (2026-09-03): `scripts/build_firmware.py dev` is now the real,
  correct, confirmed-working way to build/flash for the dev bench** — device-parametrized boot-entry
  selection (`boot_entry/<device>_boot.py`) is real, and the earlier "wozi's own pins forced onto
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
  runs the whole wired-together `src/sensortask_wozi.py` against it end to end (see
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
  `improved-quality/sensortask-wozi.py` is deleted, but `src/sensortask_wozi.py` itself still calls
  it by the current name, so this remains a real (if small) call-site update.
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
