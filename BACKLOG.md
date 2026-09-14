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

- **Sort every class in `src/` to SPECIFICATION.md D.15's method ordering — HIGH PRIORITY**
  (owner's ruling, 2026-09-13, after an AST sweep measured the gap). **D.15's order as written
  stands**: privates first, then publics, each group role-ordered (starters, getters, setters,
  others). `asy_uart_comm.py`'s interleaved layout is **not** a precedent to codify — it was an
  accident, the rule simply was not applied when that module was built.
  D.15's "no change to any comment" clause was never meant to forbid moving a comment along with
  the method it documents; it has been amended to say what it meant (relocation yes, rewriting no),
  so a file organised into labelled functional sections can still be sorted.
  **Amended again 2026-09-14, and this one moves methods between groups**: "starter" is now
  defined as a role, not a prefix — what a `get_*_starters()` collection hands to the base class or
  to `system_service.py` at boot, plus that collection and the `stop_*` pairing with such a
  `start_*`. A `start_*` that is really an on-demand command is an Other. Re-sweeping `src/` under
  the amended definition reclassifies eight methods across five files, in both directions:
  `ISL29125_Reader.start_calibration`, `AsyConnTime._start_hotspot`, `SystemService._start_task` /
  `start_timers` / `start_and_check_tasks` and both `stop_continuous_measurement`s become Others,
  while `UART_Comm._listen_loop` becomes a starter (`get_task_starters` hands it over).
  `SystemService`'s three are the genuinely arguable ones — they are the supervisor's own boot
  entry points, so they *do* the handing over rather than being handed over; settle that when the
  reorder is actually done rather than now.
  **The "eleven of 74" enumeration below predates that amendment and needs re-measuring as part of
  the reorder** — the classes named are still non-compliant, but the list is neither a current
  count nor complete. As measured 2026-09-13: `UART_Comm` (privates and publics interleaved
  throughout, its starters/getters group last rather than first), `UART` (`resync_framing` among
  the privates), `Framing_Base`/`Framing_COBS` (`_checked` mid-public), `SCD30_Reader`
  (`_set_dict_cfg`, a base-class override), `AsyConnTime`, `ConfigManager`, `SystemService`, and
  the three `asy_webserver_service.py` protocol stubs
  `_ModuleLike`/`_StreamLike`/`_TimeoutStreamProxy`. Compliant: `asy_bmp3xx_driver.py`,
  `asy_sgp40_driver.py` and `asy_isl29125_driver.py` — the ISL driver is verified against the rule
  including the 2026-09-14 amendment, private group included, so it needs no further work. Its one
  real deviation (`_end_calibration` sitting between two publics) was fixed in the same pass that
  amended the rule; `start_calibration` needed no move, since Others sort last either way.
  **Deliberately not done in the session that raised it** (owner's direction): it is a large,
  review-hostile diff across five working modules and three protocol stubs, several of them
  hardware-validated, and it belongs in a session of its own. Each class is a pure AST-verified
  sort with no behaviour change, so it can be done incrementally, one module per commit.
  **Independent session - out of the ISL29125 branch's scope and not blocked on it** (owner,
  2026-09-14). Nothing here needs the colour sensor, the bench rig or PR #75 to land first; it is
  picked up on its own.

- **The UART protocol's C implementation is not in this repo yet.** It runs on the Arduino peer and
  is the protocol's second implementation (SPECIFICATION.md Part J). A future session imports it,
  then reconciles it against `UART_C_PORT_CHANGELOG.md` — the running log of protocol changes made
  during the Python module's `src/` promotion — re-verifying each entry's conformance assumption
  against the real C source. That log file is deleted once the reconciliation is done; this entry
  comes out with it. **It is prototypical, exactly like this repo's legacy Python, with no device in
  the field running it** (owner, 2026-09-11) — so the reconciliation has no deployed pair to keep
  working and no flag day to schedule; both sides are simply reflashed together. Real hardware
  running the C side exists and can be connected to the dev board, so the reconciliation session can
  test the two implementations against each other for real rather than only reading them side by
  side.
- **Auto-builder: decide whether `sensortask_dev` importing `asy_uart_comm` is selection enough, or
  whether a separate selectable `uart_crossover` unit is still wanted.** The original requirement was
  recorded (owner, 2026-09-11) as: `asy_uart_comm.py` is a *submodule*, not an include-selectable
  one, with no upstream module, so a dev build meant to exercise the crossover jumper had nothing
  that would cause it to be included at all — hence a selectable `uart_crossover` module constructing
  the two instances across the jumper.
  **That premise has since changed, and the change is worth stating plainly rather than leaving the
  original entry to mislead the integration session.** `src/sensortask_dev.py` now constructs both
  instances itself (SPECIFICATION.md Part A.7 step 13b), so it *is* the upstream module the entry
  asked for: an import-scanning builder that selects `sensortask_dev` pulls `asy_uart_comm` in behind
  it. Independently, today's `scripts/build_firmware.py` globs and freezes all of `src/*.py`, so a
  dev firmware built with it contains the module either way. **The flash and bench hardware tiers are therefore
  not blocked, and have now been run** (2026-09-11, dev bench, owner's go-ahead in-session):
  `tests_hardware/flash/test_uart_crossover.py` 2/2 and
  `tests_hardware/bench/test_uart_link_under_api_load.py` 2/2, against a dev firmware built from the
  branch and flashed for the purpose. Neither skip guard fired, which independently confirms
  `asy_uart_comm` does reach a dev build behind `sensortask_dev`; they remain only as a diagnostic if
  some future firmware genuinely lacks the module.
  What is left for the integration session is a design question this branch should not answer for it:
  whether the auto-builder's selection model wants the variant entry point to carry the link (as it
  does now), or a separate selectable `uart_crossover` unit so the link can be included or omitted
  independently of `sensortask_dev`. Still **no file, no code and no placeholder** added here for it.

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

17. **Five cross-file consistency findings from the ISL29125 promotion's bird's-eye `src/` scan
    (CLAUDE.md: reported, not fixed — 2026-09-12).** None is a bug; each is a place two files
    answer the same question differently, and each needs a decision rather than a drive-by edit.
    **A recommendation was added to each on 2026-09-13**; all five still need the owner's yes/no,
    and four of them would touch drivers this branch otherwise leaves alone.
    - **`FiltCoeff` means two different things.** In `asy_bmp3xx_driver.py` it is the BMP3xx's
      on-chip IIR register — a discrete `int` from `_IIR_SETTINGS` (0…127). In
      `asy_isl29125_driver.py` it is a software EMA coefficient — a `float` in -1.0…1.0 with -1.0
      meaning off. Same field name, same `/sensors` endpoint, different type and different
      meaning. No wire collision (the sensor group namespaces it), and both names are locally
      the natural one. Options: leave it, or give one of them a distinguishing name.
      **Recommendation: leave it.** Renaming the BMP3xx field is a config-schema migration on
      already-deployed units — open question 2's own data-loss risk, for a purely cosmetic gain;
      renaming the ISL one makes the newer driver the odd one out. Both fields carry their own
      `description` in `html/definitions/<device>.json`, which is where a user actually meets them.
    - **Four names for two trigger-event roles.** `asy_bmp3xx_driver.py`/`asy_sgp40_driver.py` use
      `trigger_event`; `asy_scd30_driver.py` uses `start_trigger_event` + `irq_trigger_event`;
      `asy_isl29125_driver.py` uses `base_trigger_event` + `read_event`, and its own comment says
      it matches SCD30's shape — which it does structurally, not by name.
      **Recommendation: if one is chosen, it should be the ISL29125 pair** — `base_trigger_event`
      for the 1 s divider input and `read_event` for "go and read now", which are the only two
      roles any of the four drivers has, and the only naming that says which is which. A pure
      rename with no behaviour attached, but it touches three drivers and their tests.
    - **`from asyncio import ThreadSafeFlag` appears in exactly one file** (`asy_scd30_driver.py`);
      every other file in `src/` writes `asyncio.ThreadSafeFlag`. Pre-existing, not ISL-introduced.
      **Recommendation: change the one file.** Four lines in `asy_scd30_driver.py`, no behavioural
      risk whatsoever, and the cheapest of the five to settle.
    - **`_N_*_CFG` constants group on two different axes.** BMP3xx and ISL29125 group by type
      (`_N_INT_CFG`/`_N_FLOAT_CFG`/`_N_BOOL_CFG`); SGP40 groups by purpose (`_N_SETUP_CFG`/
      `_N_STORAGE_CFG`).
      **Recommendation: close this as "both, and the rule is whichever axis separates them".** It
      resolved itself on 2026-09-13: narrowing `_store_isl()`'s config read to `FiltCoeff` alone
      gave the ISL29125 two float batches, and no type-based name can tell two float batches
      apart — hence `_N_STORE_CFG` beside `_N_FLOAT_CFG`, which is exactly SGP40's own reasoning.
      Type when type separates them, purpose when it does not.
    - **Return-annotation quoting is mixed project-wide**, and most files use both forms. Twenty
      files carry quoted subscripted return annotations, eleven carry unquoted ones. MicroPython
      never evaluates annotations, so both are safe; there is simply no stated convention.
      **Recommendation: state the rule, do not mass-edit.** The one that matches what the code
      already mostly does, and the only one with a reason behind it: quote an annotation that
      names a `TYPE_CHECKING`-only import, leave the rest bare. A sentence in SPECIFICATION.md
      Part D costs nothing; touching 31 files to enforce it buys nothing.

    **Independent session - out of the ISL29125 branch's scope and not blocked on it** (owner,
    2026-09-14). Nothing here needs the colour sensor, the bench rig or PR #75 to land first; it is
    picked up on its own.
    Separately, and already known: `SGPResetVOC` and now `ISLCalibrate` are the only two config
    fields in `src/` carrying a device prefix. The retired promotion plan contradicted itself here
    (its prose said the ISL field carries no prefix, its schema table named it `ISLResetCal`); the
    code kept the table's prefix but not its name, the field having been rebuilt as a calibration
    trigger rather than a resetter. Recorded because the prefix question itself is still open, not
    the resolved contradiction.

18. **Is the ISL29125's `BOUTF` actually high at power-up? — CLOSED (2026-09-13).** Yes, and the
    status *read* clears it, which p12 denies. Full lifecycle and evidence: SPECIFICATION.md Part
    C.11.1.1. The fake models all four transitions now; `src/` needed no change. Original entry
    kept below for the reasoning that led to it.

    ~~Is the ISL29125's `BOUTF` actually high at power-up?~~ (raised 2026-09-12 by the first real
    mock-conformance run, SPECIFICATION.md Part C.11.1). Measured and settled: the `0x46` reset
    command leaves `0x08` reading `0x00`, so it does **not** raise the flag — the twin's `_reset()`
    was corrected and `simulate_brownout()` added for the supply event. What is **not** settled is
    p12's claim that the register's power-on default is `0x04`: the probe's own first run issued a
    reset before its first status read, consuming the evidence, and nothing since has power-cycled
    the part. To settle it: power-cycle the board while it runs firmware that does **not** call
    `ISL29125_I2C.setup()` at boot (the pre-ISL dev build, not this branch's), then make a status
    read the very first transaction — `device_scripts/isl29125_mock_conformance_probe.py`'s own
    `B01` key does this if nothing precedes it. Low stakes either way: `setup()` clears `BOUTF`
    unconditionally, so no production behaviour depends on the answer; it decides only whether the
    fake's `__init__` should keep starting at `_STATUS_POR`.

19. **The ISL29125 NeoPixel auto-range sweep — CLOSED (2026-09-13), the script is retired.** It
    could not pass as written, was re-run one last time to confirm exactly why, and its one piece
    of unique coverage has been moved somewhere it can actually be measured.

    The final run's findings were precisely the two predicted rig/test-design faults, and nothing
    else: sweeps 0 and 1 never touched the low range at all (no dark pre-roll, so the driver stayed
    on its configured 10000 lx default for the whole window), and the continuity check compared two
    samples straddling a transition where the *light itself* had moved 1.07 → 348.46 lux between
    them — it was measuring the LED's slew rate, not the driver's gain step. The third blocker, the
    gain-ratio convergence assertion, turned out to be a real driver defect rather than a test one
    and is fixed (the hourly relearn rate limit was also gating the FIRST measurement, so a fresh
    unit — and `ISLResetCal`, whose whole point is to relearn — could not calibrate for an hour).

    **What replaced it.** Cross-range continuity is now measured inside
    `isl29125_mechanism_envelope.py`, which was already the staircase the sweep should have been:
    one stationary light at a level inside the overlap band, read on each range in turn with
    `RangeAuto` off. Two settled holds have none of the ramp's confound. Measured on this rig:
    132.50 lx on the 375 range against 147.76 lx on the 10000 range, an 11.5% step, bounded at 25%
    (a relative bound on the correction being applied at all, not a calibration claim —
    SPECIFICATION.md Part C.11.4 owns the accuracy question). The same run now also reports the ratio the driver learned before
    the calibration trigger discards it, so every envelope run is one more data point for
    SPECIFICATION.md Part C.11.4.

20. **The ISL29125's range ratio is not a constant — MIGRATED OUT (2026-09-14), not open.** It
    varies ~28 at ambient to ~22 near full scale, measured across 18 independent estimates plus two
    independent confirmations. It is a property of the part, not a decision anyone can take: telling
    low-range compression from a high-range under-read needs a reference meter, and generalising from
    one specimen needs a second board. Neither exists, so carrying it here as something to resolve was
    misleading. **Everything — the tables, the mechanism reading, and what it means for a single
    `GainRatio` — is now SPECIFICATION.md Part C.11.4.** Do not re-raise it as actionable. If a second
    unit ever arrives, C.11.4's measurements are the baseline to compare against.

21. **The ISL29125 flash-tier firmware — CLOSED (2026-09-13).** The bench board was carrying a
    pre-ISL `dev` build, so every ISL device script failed under `harness.Board.run_isolated()`
    (which does not mount) with `ImportError: no module named 'asy_isl29125_driver'`, and the
    branch's own driver could only be exercised through `mpremote ... mount <dir>` with the
    branch-only modules cross-compiled to `.mpy`.

    The board now runs a `uv run scripts/build_firmware.py dev` build of the branch tip, flashed
    with `picotool load -x -v`, and **the whole flash tier runs clean against it: 38 passed,
    1 skipped, 0 failed (25:51)** — the skip being `--allow-flash-cycle`'s own gate. All nine
    config files survived the flash.

    Two things worth keeping from how it was done. `mpremote mount` remains the right way to try a
    driver change before committing to a flash cycle — cross-compile with `mpy-cross -march=armv6m`
    and mount the directory; the board's production watchdog stays armed across a raw-REPL
    interrupt, so chain `exec "import machine; machine.WDT(timeout=8000)"` before `mount` or the
    handshake plus a slow import trips the 8 s ceiling. And a mounted run's config writes land in
    the mounted host directory rather than on the board's own filesystem, which is what makes it a
    genuinely non-destructive stand-in.

    **One consequence still open**: `config_ISL29125.cfg` on the bench board predates this
    branch's `AutoRangePersist` default change and still reads `4`. A persisted value always wins
    over a schema default, so the production system on that board is still running the
    configuration in which the interrupt cannot lead (item 22, SPECIFICATION.md Part C.11.1.3).
    Deleting the file so the next boot regenerates it is a one-line fix, but it is a real write to
    the board's flash filesystem and has not been made.

22. **What the ISL29125 module has been proven to do on real hardware** (2026-09-12, extended
    2026-09-13) — recorded so a later session does not redo it. Everything below now runs from
    **frozen firmware** through the ordinary tier runner, not over a mount: the full flash tier is
    38 passed / 1 skipped / 0 failed (item 21). Three ISL-specific tests carry the weight, all
    structural or relative (no absolute-lux assertion anywhere):
    - `test_the_isl29125_mock_answers_the_bus_exactly_as_the_real_chip_does` — 36/36 protocol keys
      match between the real part and the twin fake (Part C.11.1 for what the first run found).
    - `test_isl29125_mechanisms_hold_across_the_whole_illumination_envelope` — ascending and
      descending steady levels, 1.1 → 8829 lx; both ranges; 2 switches across a full up-and-down;
      fixed-range pinning; 12-bit vs 16-bit agreeing to 0.6% on one static scene; cross-range
      continuity at 11.5% (item 19); the calibration trigger; `W14` firing at hard saturation.
    - `test_isl29125_survives_recombined_realistic_lighting_scenarios` — 10 scenarios, ~520
      samples, 1.1-8829 lx, 26 range switches, zero errors and zero coherence violations, and
      **no `W15`/`W17` with enough switches for either to have fired** — which is what actually
      proves the INT line is carrying the range decisions rather than the periodic fallback
      silently covering for a dead interrupt.

    **Corrected 2026-09-13**: the envelope test's own "no `W15`" was claimed as that proof and is
    not — the warning needs five periodic-only decisions in a row and that run makes two switches
    in total, so it could not have fired however dead the line was. Checked where it *could* fire,
    `W15` promptly did, and the cause was a real defect (`AutoRangePersist` outlasting
    `SampleInterv`, SPECIFICATION.md Part C.11.1.3). The scenario test now asserts a minimum switch
    count alongside the warning check, so the claim above is load-bearing rather than vacuous —
    the same habit item 23 records.
    Also confirmed directly: device ID `0x7D`, the real falling-edge INT fast path beating a 30 s
    periodic fallback by 0.61 s, `PRST` counting whole RGB cycles (1066 ms at PRST=4), the
    `CONFIG1`-write conversion restart, 12-bit data being right-aligned, and both concurrency
    scripts (same-device read/write, and cross-device interleaving against SCD30 + SGP40).

    **Extended again 2026-09-13**, after the driver's two-class restructure and on firmware rebuilt
    from the branch *including* the merged UART promotion — so these figures cover both running
    together, not the ISL alone:
    - **Flash tier: 8/8**, three consecutive runs, `-k isl29125 --allow-neopixel-sweep` (~12 min
      each; the sweep dominates). The eighth is the new
      `test_isl29125_gain_ratio_survives_a_simulated_reboot_through_the_real_fram_chunk` — before
      it, the ISL's own FRAM chunk had **no** real-hardware coverage at all, on any tier.
    - **Bench tier: 3/3**, four consecutive runs. Two of those three had never passed: they came
      from commit `ab81b79`, whose own subject is "written, never run", and both encoded an
      expectation the driver has never met. Fixed on the test side — `CalTS` is `None` (not `0`)
      until a ratio is genuinely learned and persisted, matching `SGP40_Reader`'s own
      `last_backup`/`restored_from`; and no ISL test may assert an empty error log while
      auto-range is on, because the gain learner warns legitimately on its own schedule.
      **The second of those two no longer holds**: the learner is gone, so an ISL log *should* be
      empty and the tests assert exactly that (`tests_hardware/README.md` carries the live rule).
    **Warning numbers above are as they were logged**, before the 2026-09-14 renumbering
    (SPECIFICATION.md Part C.7.1). To read them against today's driver: `W14` (saturated) is now
    `W12`, `W15` (dead-INT detector) is now `W13`, `W17` no longer exists at all, and today's `W11`
    (shadow divergence) was split out of the `W10` those runs shared with brownout recovery.

    **Superseded in part by the 2026-09-13 calibration redesign** (Part C.11.3). The gain ratio no
    longer lives in FRAM, so the round-trip evidence above and the "a learned ratio surviving a
    reboot is unproven" gap both describe a mechanism that no longer exists — the ratio is config
    now, and its persistence is the same config persistence every other field already has, covered
    by the bench reboot test rewritten alongside it. What is **not** yet proven on hardware is the
    new path: a calibration run measuring a real sandwich under the NeoPixel rig, and the operator
    copying the candidate across.
    **CLOSED 2026-09-14 — that run happened and passed.** Three sandwiches converged at ~24.0 with a
    1.8% spread across nine candidates, the applied ratio never moved under the driver, and copying
    the measured value across cut the cross-range continuity step from 11.4% to 0.4%. Full numbers
    in SPECIFICATION.md Part C.11.3. Everything the 2026-09-14 field removals and warning
    renumbering needed re-proving was re-run in the same bench session and passed; its temporary
    write-up has been deleted now that every finding sits in its permanent home (the re-measured
    fast path in C.11.1.3, the derived-cache rule in `tests_hardware/README.md`). The mock and twin tiers cover it end to end (including the
    measured-then-applied error shrink); the flash/bench tiers assert only that the trigger is
    accepted, the applied ratio does not move, and `GainMeas` is present.

23. **A hardware test that depends on an unstated rig condition is the recurring failure mode in
    this tier** (pattern, 2026-09-13 — worth reading before writing a new one). Six instances so
    far, all found by actually running the tests rather than by review:
    - `isl29125_real_irq_edge.py` assumed a scene near a range boundary. A latched-white NeoPixel
      (~2000 lx) is static and mid-band, crosses no threshold, and so produces no threshold
      interrupt — correct driver behaviour, failing test. **Fixed**: the script parks the pixel.
    - `isl29125_autorange_sweep.py` assumed the LED ramp crossed the switch point slowly enough to
      sample; it did not, and the script is retired (item 19).
    - the envelope script's `W15` check sat below the threshold at which the warning can fire, so
      it read as a proof and was one (item 22). A ceiling with no matching floor, again.
    - the first `isl29125_lighting_scenarios.py` oscillation scenario put both its levels inside
      the hysteresis band and passed with `switches=0` (item 22's own note).
    - `isl29125_plausibility_read.py` depended on ambient, so its result depended on **test
      ordering**: it passed while the pixel was latched white by the interrupted WiFi signalling,
      then failed once the fixed IRQ script (above) began parking the pixel dark before it
      (`Lux=1.07` against a 5.0 floor, sensor covered). The nastiest of them, because the test
      itself never changed. **Fixed**: it lights its own scene at a known level and parks the pixel
      dark again on the way out, so it neither depends on nor imposes bench state.
    - `isl29125_mechanism_envelope.py` imposed state of a different kind: it seeds `cfgmgr._cache`
      without calling `cfgmgr.setup()`, so the manager kept its default `config_ISL29125.cfg`
      filename and its six `_set_dict_cfg()` calls each wrote that seeded cache over the board's
      PRODUCTION config. Six silent flash writes per run, invisible in the test output, and it is
      what actually moved the bench board's persisted `AutoRangePersist` from 4 to 2. **Fixed**:
      the script points `cfgmgr.config_file` at a `config_HWTEST_*.cfg` scratch name.
    The three habits that catch this class: **a device script provides its own light** rather than
    trusting the bench state, **it restores or side-steps every piece of shared state it touches**
    - light, config files, FRAM chunks - so it cannot decide a later script's result or corrupt
    production's, and it **asserts a minimum engagement** (this must switch / both ranges
    must be used) alongside every ceiling, so a test cannot pass while the mechanism it targets
    never runs.

24. **The two live-backend browser tests fail locally on a stale/stub frozen website** (observed
    2026-09-13 on this branch; **not caused by it** — nothing in the ISL29125 work touches the web
    lane, and 575/576 `tests_js` tests pass). `npx vitest run` reports 2 failed files, 1 failed
    test:
    - `tests_js/live-backend.test.js` — the browser-driven PUT round-trip fails with
      `page.waitForSelector: Timeout 10000ms exceeded` waiting for `[data-section-key="system"]`.
      The captured HTML in the failure shows why: the twin served the **wozi placeholder stub**
      (`<title>wozi placeholder</title>`, `Hello, wozi! (placeholder stub)`), not the real site.
    - `tests_js/live-backend-put-matrix.test.js` — fails at *collection* with
      `startLiveMatrix failed: digital twin never started serving on 127.0.0.1:19412 within
      20000ms`, twin stderr empty. Whether this is the same root cause surfacing earlier or a
      separate boot/port problem was **not** established.

    **Confirmed root cause for the first one.** `frozen_modules/` is a gitignored build artifact
    and currently holds `frozen_html.py` at 8 KB — the stub, built by `scripts/build_frozen_html.sh`
    from `html_stub/` — alongside a separate 84 KB `frozen_website_wozi.py`. `sensortask_dev.py`'s
    top-level `import frozen_html` is what mounts `/html`, so the twin serves whatever that module
    contains; here, the placeholder. The tracked `html/index.html` *is* the real site, so this is
    purely about which artifact got built into `frozen_modules/`.

    **Also worth fixing, and arguably the real defect:** `tests_js/live-backend.test.js`'s own
    docstring promises it "skips itself with a clear message if the MicroPython toolchain/frozen
    website aren't built yet, rather than failing the suite" — but `_live_twin_command.js`'s guard
    only checks that the Unix-port binary exists. It does not check that the frozen module is the
    **real** website, so a stub build fails with a confusing selector timeout instead of skipping
    as designed. Widening that guard would have turned this into a one-line skip message.

    Left for the web lane's owner: not investigated further, and nothing was rebuilt, since a
    `scripts/build_website.sh` run changes a gitignored artifact that other work on this bench may
    be relying on.


25. **Seven `src/` modules number `errno`/`wrnno` inside the range `base_classes.py` reserves.**
   Part C.7 reserves `errno` 1-9 and `wrnno` 1-2 for `SensorReader`/`SensorReaderConfig`, and
   `api_response.py`'s `handle_set_cmd()` owns the fixed cross-module slot `errno=99`; the project
   owner's standing direction (2026-09-11) is that **every** module aligns to that reservation for
   conformity and clash avoidance, whether or not it subclasses `SensorReader`. Audited across
   `src/`: `config_manager.py` (`errno` 1-14, `wrnno` 1-6), `system_service.py` (`errno` 1-6, plus
   its dynamic `wrnno = n + 1`), `asy_webserver_service.py` (`errno` 1-6, `wrnno` 1-5),
   `captive_dns.py` (`errno` 1-3, `wrnno` 1-3), `asy_wifi_service.py` (`wrnno` 1-7),
   `asy_ntp_client.py` (`wrnno` 1-3), `asy_notification_service.py` (`wrnno` 1-5 - its `errno` was
   already renumbered to 10-13 for exactly this reason). Conformant today:
   `asy_sgp40_driver.py` (`errno` 10-18, `wrnno` 10-14), `asy_bmp3xx_driver.py`,
   `asy_scd30_driver.py`, `asy_fram_manager.py`/`asy_fram_driver.py`, and - checked 2026-09-13
   after the merge, since that driver and this audit were written concurrently and it appeared in
   neither list - `asy_isl29125_driver.py` (`errno` 10-38, `wrnno` 10-13 since the 2026-09-14
   renumbering), clear of both reserved
   ranges.
   **No live clash exists** - none of the seven currently shares a logger with a `SensorReader`
   instance, so the reserved codes never reach the same history stream. It becomes a real defect
   the moment one of them gains a `logger=` reach-through, which is exactly the pattern
   `AsyFramManager`/`FRAM_SPI` already use and which the UART promotion adopts. **Where to fix**:
   a renumbering pass is mechanical but not free - every changed code is a persisted value in
   deployed units' FRAM histories and appears in `SPECIFICATION.md` C.7.1's table, the errcount
   UI's raw `num`, and existing tests. Needs an owner decision on whether to renumber in place
   (invalidating persisted history semantics for those modules on the next deployment) or only on
   each module's next substantial touch. Flagged, deliberately not fixed drive-by - see CLAUDE.md's
   "flag, don't silently change" rule.
   **Independent session - out of the ISL29125 branch's scope and not blocked on it** (owner,
   2026-09-14). Nothing here needs the colour sensor, the bench rig or PR #75 to land first; it is
   picked up on its own.

26. `asy_uart_comm.py`'s `wrnno` 11 ("drain bound reached - the peer never stopped sending") can
    never reach the FRAM history through the path that produces it. SPECIFICATION.md Part C.7.1 allows one persisted
    warning per fault episode; `_resync()` logs `wrnno` 10 first and spends it, then calls
    `_drain()`, so 11 is always demoted to visible-only. Measured 2026-09-13: a resync whose drain
    genuinely hits its bound persists `['W10']` and nothing else. **Not a violation of the rule** -
    it is "at most once per episode", satisfied by never - but 11 is the strictly more informative
    of the two, and it is the one signal separating a babbling or misconfigured peer from ordinary
    line noise once the link has carried a valid frame at some point (before that, `errno` 32
    covers it). **Where to fix**: have `_drain()` set a flag and let `_resync()` choose which
    `wrnno` spends the episode's slot, so the more specific condition wins - about five lines, no
    change to the one-per-episode budget. Needs an owner decision because it changes which entry an
    operator sees in a field log, the same class as the `errno` 32 decision of 2026-09-12.
    `SPECIFICATION.md` C.7.1 now states the actual behaviour rather than the intended one.
    **Independent session - out of the ISL29125 branch's scope and not blocked on it** (owner,
    2026-09-14). Nothing here needs the colour sensor, the bench rig or PR #75 to land first; it is
    picked up on its own.

27. **`test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly` asserts an empty
    FRAM log after deliberately provoking torn writes** (found 2026-09-13 in the first full
    flash+bench run of the ISL29125 branch; reproduces identically on a targeted re-run). The test
    hard-resets the board three times *during* FRAM writes and then requires the FRAM error log to
    be empty; it holds `E31`, `W71`, `E31`, `W72`. `W71` ("invalid data in block 0, reading block
    1") is the dual-copy recovery doing exactly its job and is arguably a success signal. `W72`
    ("invalid data in block 1") means one chunk lost *both* copies, and `E31` is a status-byte
    failure on the write side.
    Deliberately not "fixed" by loosening the assertion: the flash-tier
    `test_error_log_history_is_all_or_nothing_across_a_reset_raced_chunk_write` passes, so the
    all-or-nothing property holds per chunk.
    **RESOLVED (2026-09-13) — the entries are acceptable degradation, and the test now expects
    them** (owner's ruling). An error or warning here is the direct, expected consequence of an
    interrupted read or write, so requiring an empty log asserted that deliberately-provoked damage
    leaves no trace — not a property the hardware has. `assert_module_error_log_clean()` gained an
    `allowed_errors` parameter for exactly this case, and the test now permits `E31`/`W71`/`W72`
    while still failing on anything else and still requiring a fresh backup to complete afterwards.
    It also **clears the FRAM log in its own `finally`**, because those entries are real persisted
    state that the next test would otherwise read as evidence — CLAUDE.md's "read the FRAM logs
    before clearing" rule assumes a board that has been running normally. On a failure the entries
    are already in the assertion message, so nothing diagnostic is lost by clearing.

28. **Definitions and mockdata were never compared, and had drifted in three places — CLOSED
    (2026-09-13).** Found because dev's definitions advertised `UARTLINK_Transfers`/`UARTLINK_Failures`
    with no mockdata behind them (the UART promotion's own gap). Fixing only that would have left
    the mechanism open, so `tests_js/definitions-mockdata-coverage.test.js` now walks every shipped
    variant and asserts that each `kind: "readonly"` field a definitions file names actually
    resolves against that variant's mockdata — using `resolveFieldValue()` and a mirror of
    `render.js`'s own `groupValuesFrom()`, so it tests the real resolution rather than a second
    implementation of it. It carries a negative control, since a resolver that returned a value for
    everything would make the whole check vacuous.
    It found two more on its first run. **`GainMeas`** was in dev's definitions and mockdata while
    `get_dict_data()` — this driver's hand-written REST override — never emitted it, so a real
    device would have served a body without it (fixed in the same session). And **dev's mockdata
    had no `BMP3XX` at all**, in either `measurements` or `sensorsConfig`, though dev's definitions
    declare the group and `sensortask_dev.py` really does construct a `BMP3xx_Reader` — a
    pre-existing gap, unrelated to any recent work, that rendered a permanently blank card on the
    mock site. Values mirror wozi's, the same part.
    The class of bug is the same in all three: a field named in one of the three sources
    (definitions, mockdata, the device's real body) and absent from another, which renders exactly
    like a device that has not reported yet rather than like a defect.

29. **An interrupted `setup_toolchain.py env --tier flash` can leave the unit-test interpreter
    broken, and `scripts/test.sh` will use it anyway** (hit 2026-09-13). The flash tier legitimately
    rebuilds the MicroPython Unix port as part of `test_env_tier_flash_recurring_run_is_idempotent`,
    and `run_verification_sequence()` builds it **twice**: first with the frozen-verification
    manifest, then a vanilla rebuild that restores "the real test rig" (its own comment). Interrupt
    the run between those two and the binary left on disk has no frozen `asyncio` at all — every
    `tests/test_*.py` that imports asyncio then dies with `ImportError: no module named 'asyncio'`,
    which reads like a code failure and is not one. The most likely trigger here was this session's
    own `pkill` of a hardware suite, so it is a fragility rather than a latent bug, but nothing
    detects it: `scripts/test.sh` only checks `[ ! -x "$micropython_bin" ]`, so a *broken* binary is
    indistinguishable from a good one and is silently used.
    **Out of scope for the ISL29125 promotion (owner, 2026-09-13)** — it is general test tooling
    with nothing sensor-specific about it, and the documented workaround (`rm` the binary and
    re-run `scripts/test.sh`) costs a rebuild rather than a wrong answer. It belongs to a session
    already paying for a toolchain build, which is where the two-chroot pre-push gate below is
    nearly free rather than the dominant cost.
    **Recommendation: make that guard a capability check rather than an existence check** — e.g.
    `"$micropython_bin" -c "import asyncio"` (or a small `-X heapsize` smoke import) alongside the
    `-x` test, rebuilding when it fails. Deliberately not implemented here: `scripts/` is inside
    CLAUDE.md's "Pre-push verification" scope, which requires a clean Ubuntu-noble *and* Debian-trixie
    chroot run before pushing, and this session cannot satisfy that gate. Recovery in the meantime is
    `rm` the binary and re-run `scripts/test.sh`, which rebuilds it.

30. **`SPECIFICATION.md` carries six subsections about one sensor, and no other sensor has any.**
    Raised 2026-09-14 while deciding where the calibration band-gate finding belongs; **the owner's
    ruling is to leave the specification exactly as it stands, Finding 2 included, and tidy this up
    in a session of its own.** Recorded here so that session does not have to re-derive the scan.

    **One free fix for that session, found 2026-09-14 in the branch's final review**: the six
    subsections are also out of order in the file - `C.11.3` physically precedes `C.11.2`. Pure
    document order, no content change, and it is left alone here only because the owner's ruling is
    to touch nothing in the specification until that session.

    Three distinct patterns exist in the document, and only the third is the question:

    - **Generic rule, named instance** — the dominant and legitimate one. C.4.3 cites SGP40 against
      SCD30 to illustrate `SensorReader` vs `SensorReaderConfig`; C.7 names the drivers sharing the
      `errno` block; D.15 uses `ISL29125_Reader.start_calibration()` as the worked example of the
      amended starter rule. All 29 `src/` modules are named somewhere this way. Nothing to move.
    - **Sections named after a module that *is* the architecture** — A.7/A.7.1 (the two
      `sensortask_*.py` construction orders), A.8 (`asy_webserver_service.py`), C.5
      (`config_manager.py`), C.6, C.7 (`print_log.py`/`base_classes.py`), and Part J
      (`asy_uart_comm.py`). There is no generic version of "what order does `sensortask_wozi` build
      things in". Part J is the strongest case and rests on a different justification again: the
      UART protocol is a two-implementation contract with the Arduino peer, so that Part is the
      interface definition both sides implement, which is why CLAUDE.md points at it by name.
    - **Dedicated single-chip technical sections — ISL29125 only.** C.11.1.1 (`BOUTF`'s lifecycle
      and where datasheet p12 is wrong), C.11.1.2 (the threshold persistence counter and the
      destructive status read), C.11.1.3 (PRST derived from `SampleInterv`), C.11.2 ("ISL29125
      reference layer"), C.11.3 (the calibration design, holding the band-gate finding), C.11.4
      (the measured range-ratio table). Checked the other sensors the same way, with chip-only
      identifier sets (`AmbPres`/`FRC`/`ASC`; `sraw` and the VOC-index terms; `_VAL_POV`/
      oversampling/IIR): **SCD30, SGP40 and BMP3XX have no dedicated section anywhere.**

    Two places *do* treat every driver alike, so the convention is not simply absent: A.4's
    "functional behaviors confirmed intentional" list has one bullet per chip (ISL's is the same
    shape and length as SCD30's and SGP40's), and C.7.1's registry has one row per module. Both are
    consistent; the C.11 block is the outlier.

    **The decision that gates the work**: is C.11's contract "generic rules only, chips cited as
    examples", or "generic rules plus the worked example that established each one"? The block was
    written under the second reading. Under the first, C.11.1.3 and C.11.3 should not simply move —
    each has a generic kernel worth keeping in place ("a chip-side persistence window must stay
    shorter than the software re-check interval, or software beats the interrupt to every decision";
    "calibration is user-triggered, user-applied, and writes nothing by itself"), with the ISL
    arithmetic and mechanics extracted out from under it. C.11.1.1/C.11.1.2 are pure single-chip
    datasheet fact with no generic content, C.11.4 is measured data about one specimen, and C.11.2
    is prior-art analysis that may belong with the attribution material instead.

    **Where ISL-specific content would go instead**, if it leaves: CLAUDE.md caps every module
    header block at 3 lines and `asy_isl29125_driver.py`'s is already exactly 3, so the header
    cannot hold it — that same rule's next tier, "a short comment right next to the code it
    explains", is the destination for a code fact, and `tests_hardware/README.md`'s NeoPixel rig
    section for anything that is really an operator procedure. A new per-module doc file was
    considered and is **not** recommended: the repo has no such convention, and a document beside
    the code without being the code is what drifts.

    **Independent session - out of the ISL29125 branch's scope and not blocked on it** (owner,
    2026-09-14). Nothing here needs the colour sensor, the bench rig or PR #75 to land first.

31. **`_store_isl()` derives the normalisation span from live config rather than from the sample**
    (found 2026-09-14 in the branch's final review; reported rather than fixed, because the choice
    below is the owner's). `ISLResults` already carries `sample_range` precisely so the gain
    correction uses the range the sample was taken on - its own comment says `_store_isl()` "must
    not read the reader's current range back" - but the *span* the RGB/HSB outputs are divided by
    (`_RANGE_HIGH_LUX` under auto-range, `_fixed_range` otherwise) is still read live, after an
    `await`. A `RangeAuto` PUT landing between the data read and that line normalises one sample
    against the wrong denominator - 26.67x too large and clamped to 1.0 turning auto off against a
    fixed 375, 26.67x too small turning it back on.
    **Neither persistent nor state-corrupting**: the EMA filter holds lux, not the normalised
    values, so only that one sample's RGB/HSB/CCT are wrong and the next cycle is correct. It needs
    a REST PUT to land inside one specific window of a 1s cycle.
    Two ways to close it, and choosing between them is why it is not already done:
    - **Carry the span with the sample**, the shape `sample_range` already establishes. Complete,
      but widens `ISLResults` from five elements to six, which touches `_error_check()`'s own
      None-count contract, the `TYPE_CHECKING` alias, and every test that builds one.
    - **Read the two fields at the top of `_store_isl()`**, before its first `await`. Three lines
      and no test churn - but airtight only while `_error_check()` has no yield point on its happy
      path, which nothing enforces. It would look complete without being complete.

32. **`js/mock-server.js`'s measurement jitter was sized for readings of order hundreds, and the
    ISL29125's normalised 0-1 leaves are three orders smaller** (same review; the sign half of this
    was already fixed on the branch, the magnitude half was not). `jitterInPlace()` uses a spread of
    `max(|value| * 0.01, 0.05)` and rounds to two decimals, both chosen when CO2 ~600 was the
    largest thing in the file. On an `RGB.R` of 0.0281 the absolute floor is +-178%, and two
    decimals quantise the result to 0.03 - or to 0.00, which the card then renders as `0.0000`
    against a `decimals: 4` hint. That is the "looks like a device that has not reported yet"
    failure mode open question 28 exists to prevent, in the group this branch added.
    **Mock-only**: no firmware and no real renderer is involved. The sign clamp added on this branch
    stops the *invalid* half (a negative channel); what remains is fidelity.
    **Proposed**: scale both with the value - `spread = |value| >= 1 ? max(|value| * 0.01, 0.05) :
    |value| * 0.05`, and round to 4 decimals below 1 rather than 2. Nothing of ordinary magnitude
    moves. Left for a ruling because it makes the existing sign clamp structurally unreachable: the
    test that covers it ("never jitters a non-negative measurement leaf into a negative one") would
    have to become a property assertion over the real mockdata rather than a check on that clamp,
    and two tests pin the current exact values deliberately, with comments explaining the very
    coarseness they work around.

33. **A config burst that fails PART-WAY still leaves the chip and the shadow disagreeing, and
    only a REST config GET notices** (found 2026-09-14 alongside the rollback fix in the same
    review, which closed the common case but not this one). `configure()` now restores every shadow
    field when `_write_shadow()` raises, so the usual failure - a NAK on the address phase, nothing
    written - leaves the shadow describing the chip correctly. A NAK partway through the 3-byte
    burst is rarer and different: CONFIG1 landed, CONFIG2/3 did not, the rollback puts the shadow
    back to all-old, and the chip is now a mixture. `normalise()` then scales by the old resolution
    while the part runs the new one - 16x out, with the reads themselves still succeeding.
    **It does self-heal, but only through one path**: `_read_sensor_dict()` runs `matches_shadow()`
    and re-applies with `force=True`, and `js/render.js` polls each section's own GET while that
    section is open - so a device with someone watching corrects within a poll interval. A headless
    device corrects on the next GET, whenever that is.
    **What would close it**, and why it is a design question rather than a drive-by fix: the chip is
    the authority after a torn write, so the honest recovery is to re-read it - but `decode_config()`
    recovers only five of the nine shadow fields (mode, SYNC, CONVEN and INTSEL are not among them),
    so it needs a full decoder; and an I2C read issued from inside the `except` of a failed I2C
    write is itself likely to fail. The alternative is a dirty flag the read path checks, which
    turns divergence detection into something reachable every cycle rather than only from a config
    GET - about eight lines, one extra transaction only after a failed write, and a new mechanism.

## Deferred / explicitly out-of-scope work
- **Two device scripts still hand-list their `cfgmgr._cache` keys, and will break as a "dead
  sensor" the day their driver gains a config key.** `bmp3xx_plausibility_read.py` (8 keys) and
  `sgp40_fram_backup_restore.py` (3 keys, and the literal appears **twice** in that file, for
  reader1 and reader2). Both were verified in sync on 2026-09-14, so this is latent risk, not a live
  bug — which is exactly why it is easy to forget. The failure mode is not a config error: the batch
  read in `_init_*()` comes back short of its `_N_*_CFG` length check, init logs its "Error reading
  config data!" errno and returns False, and the read chain never starts, so the script reports
  *"sensor not responding or not wired to i2c1"* / `samples=0`. That is precisely what happened to
  three of the four `isl29125_*.py` scripts when `GainRatio` joined the ISL schema (2026-09-14):
  hours look like a hardware fault before anyone suspects the cache. The fix is one line, already
  applied to all four ISL scripts and written up as a standing rule in `tests_hardware/README.md`'s
  priming note:
  `reader.cfgmgr._cache = {field[0]: field[2] for field in reader.cfg_schema if field[2] is not None}`
  plus explicit overrides. **Convert whichever script its driver's schema changes first** — doing it
  pre-emptively needs a real-hardware run to re-verify each, which is the only reason it is deferred
  rather than done. Not a general licence to leave new scripts hand-listed: anything new derives.
- **A digital-twin soak's wall clock is set by GC timing, so it must never be bisected to a code
  change** (established 2026-09-11 after one was — see SPECIFICATION.md Part E.7 for the measurement
  and the inverted control). Not open work: the finding itself is the resolution, and
  `tests/test_digital_twin_run_dev_integration.py`'s budget now sits above the whole observed range
  rather than inside it. Left here because the trap is easy to fall into a second time: the numbers
  are stable to within 0.3s per build, which reads exactly like a real signal.
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
- **Four UART-audit findings reviewed and deliberately left as they are** (audit pass over the
  promotion, 2026-09-11 - every other finding from that pass was fixed and tested):
  - **A responder's `set_callback` returning `None` ("don't care") lets the *peer* size a heap
    allocation.** `_accept_set()` allocates `(CHUNKS - 1) x payload_size` from the peer-declared
    `CHUNKS`, i.e. up to ~64 kB at `payload_size = 255`. It is caught (`MemoryError`/`OverflowError`
    → logged, resync, no partial delivery) and so sits correctly on CLAUDE.md's
    catch→degrade→restart→watchdog ladder, but a callback that *declares* its expected size caps it
    instead of trusting the peer - worth preferring in any new responder.
  - **`asy_uart_driver.UART.deinit()`/`init()` do not respect the session lock.** Calling either
    while a read is in flight would leave the in-flight code holding a reference to a deinit'd
    peripheral. No caller does: `UART_Comm` never deinits, and the one place that does
    (`tests_hardware/device_scripts/uart_crossover_recovery.py`'s injector) does it between
    exchanges. A guard was not added because `init()` calls `deinit()` itself, so refusing while
    locked would change construction semantics for a hazard nothing currently reaches.
  - **`UART_Comm.setup()` called a second time while its own listen loop is running would
    deadlock** on the bus lock the loop holds during its unbounded read. Nothing calls it twice -
    `system_service.py` runs the setup batch before any task starts - so no guard was invented for
    a caller that does not exist. Re-checked against the supervisor itself (2026-09-12): its restart
    ladder re-calls a dead task's *starter*, never a module's `setup()`, so the unreachability is a
    property of the code rather than of today's call sites.
  - **One `Framing_COBS` instance shared between two drivers would corrupt both**, since its
    long-lived scratch is per-instance, not per-call. Every construction site makes its own; noted
    because the failure would be silent if one ever did not.
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
- **UART sensor integration — still unwired as a *sensor*, though the link itself now exists.**
  `asy_uart_comm.py` is promoted (SPECIFICATION.md Part J) and `src/sensortask_dev.py` constructs two
  instances across the dev bench's crossover jumper, which is what makes the protocol's
  self-compatibility property physically testable. What stays deliberately absent is any *sensor*
  behind that link: no BME688/BSEC coprocessor, and no such wiring in any other variant. Not a legacy
  deployed feature, so adding one would be a scope addition beyond feature-parity rather than a
  postponed fix — owner-confirmed this stays as-is. The protocol module is standalone by design: its
  BME688/BSEC first use case is explicitly out of scope and was **not** part of the promotion.
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
  `readfrom_mem()` rather than zero-copy `readfrom_mem_into()`** — this was written as "worth doing
  before `asy_isl29125_driver.py` is migrated", and that migration has now happened without it.
  **Still not done, deliberately, and worth a decision rather than silent carry-over**: the ISL's
  own hot path is one `get_register_struct(_REGISTER_DATA, "6s")` per read cycle — a 6-byte
  allocation at the configured sample interval, nowhere near the fixed-size-buffer bar Part I
  reserves the zero-copy treatment for. The cost of doing it is a changed signature on three shared
  methods every existing driver calls. Left as the same low-priority item it was, no longer blocked
  on anything.
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
