# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

**Anything in here that needs the dev bench is also listed in `REAL_HARDWARE_TEST_QUEUE.md`**, which
is the single running queue a go-ahead session works through in one pass. Items stay tracked here as
usual; that file exists so the real-hardware subset does not have to be reassembled from this file,
`tests_hardware/README.md` and the handover docs every time.

**The numbered list below has gaps, and its numbers are never reused or renumbered.** Code comments
and `SPECIFICATION.md` cite items by number, so a resolved item whose number is cited stays as a
short closed stub saying what the answer was (items 1, 5, 6, 9, 12, 15, 20, 23, 31, 33 today); one whose number nothing
cites is deleted outright, its permanent content migrated per the policy above. A gap therefore means
"resolved and removed", never "lost".

## Refactor targets not yet done

- **A config-persisting `PUT /sensors` reset its own HTTP connection under concurrent API load -
  fixed (WP5, 2026-09-16), pending real-hardware re-confirmation.** Root cause: an RP2040 flash
  write disables interrupts port-wide for its whole duration (`ports/rp2/rp2_flash.c`'s
  `begin_critical_flash_section()`), freezing the CYW43 link and lwIP's own timers along with it -
  and the old `ConfigManager.write_config()` performed that write synchronously, inline, inside the
  very PUT request whose connection then got reset. Fixed at the design level exactly as this entry
  originally called for: `write_config()` now validates and stages synchronously, then hands the
  actual `open()`/`json.dump()` write to an independent `asyncio.create_task()`, fully decoupled
  from the request/response (see `config_manager.py`'s own comments and SPECIFICATION.md Part F.2
  for the full mechanism, including the accepted residual risk window and its interaction with the
  WiFi-power-cycle backstop). Mock-tier (`tests/test_config_manager.py`) and digital-twin-tier
  coverage all pass; **still open**: re-running the two real-hardware bench tests that originally
  found this
  (`tests_hardware/bench/test_bus_concurrency_under_api_load.py`'s
  `test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` and
  `test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load`) against the
  real dev board, once a real-hardware go-ahead exists for a session - this entry stays until that
  confirmation lands.
  **Half of that confirmation has since landed, and it split the two arms — read item 30 with this
  entry, not separately** (noted 2026-09-18 by the pre-merge sweep; the two were written a day apart
  and never cross-referenced). The bench session of 2026-09-17, on firmware carrying this WP5 fix,
  found the **BMP3XX arm passing** and the **ISL29125 arm still failing** (four-arm isolation: PUT
  alone 0/10, PUT + 1 reader 0/6, PUT + 2 readers **6/18**, plain GET + 2 readers 0/6). So the
  deferral fixed what it was built to fix - the *shared* synchronous flash write is no longer the
  discriminator, which is precisely what the two arms having opposite outcomes on the same flash path
  proves - but a second, ISL29125-specific mechanism remains, and that residual is item 30, where the
  next step (the `RangeAuto=false` bisection) already lives. **What is genuinely still owed here is
  therefore only the BMP3XX arm's re-confirmation being treated as durable** rather than one bench
  run; the ISL29125 arm is not "pending re-confirmation", it is a known open defect with its own item.

  Note the bench re-run that produced these numbers needs `--allow-persistence-writes`: the write path
  is now gated behind `@pytest.mark.persistence_write`, so a default bench run deselects both arms and
  re-confirms neither.
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
- **The full test-suite scan for tier/layering-completeness and wrongly-trusted-hazard tests
  (project owner, 2026-09-15) has now run once, beyond bus-hazard's own corner** — UART,
  WiFi/network/NTP/DNS, FRAM/memory/reboot/watchdog, and webserver/notification/config-push were all
  swept, real call chains traced end-to-end rather than grep-counted. Full account, including what
  was fixed, what's a confirmed structural exception, and what's named-but-not-fixed (needing either
  a dedicated real-hardware session or a project-owner design decision): `tests_hardware/README.md`'s
  "Tenth pass". No second instance of the SGP40-shaped bug (a real hardware trigger silently
  substituted with a software-only one) turned up, but several real tier-parity gaps did, most now
  closed. **Named follow-ons still open, tracked in that section, not repeated here**: a real-hardware
  test for UART's F.5.8 "never blocks" invariant against the actual shipped driver (not a hand-rolled
  clamp); wiring a periodic SET into the bench UART exerciser's live load; deciding whether the mock
  tier's ~20-scenario UART fault-injection catalog is a genuine real-hardware structural exception or
  needs a raw-second-UART injection technique; a project-owner design review before any
  `rotate_ap_password()` bench test (real AP credential rotation on the shared bench rig); a
  real-hardware test for `_reboot()`'s alarm-pool-exhaustion fallback; and a hard-reset-recovery bench
  test for NOTIFY's own FRAM chunk (needs an observable-write signal analogous to SGP40's `BackupTS`
  first). Re-running this sweep against other domains (it did not touch e.g. sensortask/system_service
  integration beyond what FRAM/memory covered) is future work, not assumed done everywhere.

## Open questions (need owner input or further investigation)

- **ISL29125's chip configuration divergence under concurrent API load (PR #84/commit `679c2b0`'s
  isolation work, HIGH IMPORTANCE, completely unforeseen — project owner, 2026-09-15) — fixed in
  code and unit-tested; real-hardware re-verification still pending.** Root cause, traced through
  the real code: `ISL29125_I2C.configure()` mutated the in-memory shadow fields
  `encode_shadow()`/`matches_shadow()` read (`self._mode`, `self._range_fs`, `self._resolution`,
  ...) *before* it ever acquired the per-sensor device-session lock that SPECIFICATION.md Part C.8
  documents as what serializes "a multi-transaction sequence against another coroutine starting its
  own sequence on the same sensor" — only the actual wire write was ever inside that lock. Under
  real concurrent load (`read_loop()`'s own background reads/`_switch_range()` calls, or a second
  concurrent request) that lock does get contended, so a `configure()` call could be suspended
  *after* mutating the shadow but *before* its write reached the chip, letting a concurrent `GET`'s
  `get_config_snapshot()` + `matches_shadow()` observe the shadow already showing the new value
  against a chip that still held the old one — a false "diverged from the shadow" `wrnno=11` report
  with nothing actually wrong on the wire, which is why three quiet trials never reproduced it but
  2 concurrent `GET` workers did (twice, per the original isolation). The existing mock test that
  looked like it should cover this
  (`test_concurrent_read_and_write_never_interleave_on_the_wire`) only ever proved wire-level
  atomicity, never this shadow-vs-chip timing race. **Fixed** by widening the device-session lock in
  `configure()` to span the whole validate-mutate-write(-rollback-on-failure) sequence, matching
  Part C.8's own documented intent (`_write_shadow()` renamed `_write_shadow_locked()`: no longer
  self-locking, the caller now holds the lock for the whole critical section). Regression test:
  `tests/test_asy_isl29125_driver.py::test_configure_never_exposes_the_shadow_ahead_of_a_write_still_in_flight`
  holds the exact lock `configure()` needs (standing in for real contention) and confirms the
  shadow cannot change while `configure()` is blocked waiting for it. **Still open**: this needs a
  real-hardware re-run (the original finding only ever manifested under real concurrent bench load)
  before it can be considered fully closed — needs the project owner's go-ahead per CLAUDE.md's
  standing real-hardware gate. Queued as `REAL_HARDWARE_TEST_QUEUE.md` R9, together with the
  `Overrange` half below (`device_scripts/isl29125_mechanism_envelope.py` was updated to read the
  field instead of the retired `W12` log entry and has not run on silicon since).
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
  updated to check the field directly instead of the retired `W12` log entry (also pending
  real-hardware re-run). `html/definitions/dev.json`/`mockdata/dev.json` updated with the new field.

1. `modules/_boot.py`'s `import sensortask.py` (literal `.py`) - **mechanism answered; the file is
   never changed regardless.** Kept only because CLAUDE.md's own hard rule and
   `tests_hardware/flash/test_reboot_persistence.py` cite this number. Traced through the pinned
   source at 1.28 and re-verified at 1.29.0 (`tools/mpy-tool.py`'s frozen-name generation,
   `py/frozenmod.c`'s exact-match lookup, `py/builtinimport.c`'s `stat_module()`/
   `process_import_at_level()`): a plain `import sensortask` is unambiguously the correct form, and
   the dotted one *should* raise, because it needs "sensortask" to resolve as a package. Why it
   nonetheless works on the deployed 1.26 firmware was never verified against that version's own
   import machinery and never will be - the legacy tree is reference-only forever, so no session
   tests it. Nothing to do on the refactor side either:
   `buildgen.codegen.generate_boot_entry_source()` already emits the correct
   `from sensortask_wozi import main`.
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
5. ~~Real-hardware verification gap for `asy_udp_socket.py`/`captive_dns.py`~~ - **closed
   (2026-09-08, real bench hardware).** Kept as a stub because `tests_hardware/README.md`,
   `bench_control.py` and two bench test files cite this number. All three UDP-layer claims are
   confirmed on real rp2/lwIP: garbage-response robustness and truncation; connected-socket
   source-address filtering (**holds** - real OS/lwIP enforcement, a forged reply never corrupts the
   DUT's RTC); and POLLERR/POLLHUP delivery (**never observed** - `AsyUDPSocket.ready()`'s handling
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
    running, which is `REAL_HARDWARE_TEST_QUEUE.md`'s C7, not this item.
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

20. **`tests_hardware/bus_topology.py` deleted as dead code - closed (owner decision, 2026-09-18).**
    It was a hand-kept, tool-uncross-checked third copy of `devices/dev.toml`'s/`wozi.toml`'s wiring
    facts, and nothing in the repo imported it: the real on-target sweep CLAUDE.md's bus-hazard rule
    cited it for runs `device_scripts/bus_topology_autodetect_and_hazard_sweep.py` instead, which
    live-detects the topology and carries its own address table.
    **What moved rather than went away**: its only enforced content was the assertion that no declared
    device address falls in an I2C-reserved range (0x00-0x07, 0x78-0x7F). That is now
    `tests_scripts/test_device_tomls.py`'s `test_no_declared_i2c_address_falls_in_a_reserved_range`
    (+ the fixed-address half against `buildgen.twin_wiring.FIXED_ADDRESSES`, + a guard that the sweep
    is not silently seeing no addresses at all) - run against the real device set in an enforced lint/
    test scope, rather than over two hardcoded tuples in a file nothing loaded.
    The on-target script keeps its own `KNOWN_ADDRESSES` deliberately - it is MicroPython on the board
    and cannot import host code; that is now stated in its own comment and in Part K.7's checklist
    instead of a cross-reference to a file that no longer exists. CLAUDE.md's bus-hazard rule, Part
    K.7 and the new-driver checklist all repointed.

22. **Seven `src/` modules number `errno`/`wrnno` inside the range `base_classes.py` reserves.**
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
   `asy_scd30_driver.py`, `asy_fram_manager.py`/`asy_fram_driver.py`.
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

23. **`asy_uart_comm.py`'s `wrnno` 11 now outranks 10 - fixed (owner decision, 2026-09-18).**
    Kept as a closed stub only because `SPECIFICATION.md` C.7.1 cites this number. 11 ("drain bound
    reached - the peer never stopped sending") could never reach the FRAM history through the path
    that produces it: `_resync()` persisted 10 first and spent the episode's one slot. `_drain()` now
    flags the condition instead of logging it, and `_resync()` logs after the drain, choosing the more
    specific code. The one-persisted-warning-per-episode budget is unchanged - the owner's own
    condition on this fix, and the reason 11 takes the slot rather than adding one.
    The same change closed the inverse leak nobody had looked for: `setup()`'s boot drain is
    deliberately not a fault and not counted, yet against a babbling peer it persisted 11 on **every
    boot**, because the bound logged itself rather than flagging its caller. It now persists nothing.
    Covered by three tests in `tests/test_asy_uart_comm.py` (the bound case takes the slot, the quiet
    case is unchanged, the boot drain persists nothing - the first proven non-vacuous by inverting the
    choice and watching it fail); `UART_C_PORT_CHANGELOG.md` B32; SPECIFICATION.md C.7.1 restated.

24. **`PUT /status {"ResetErrors": true}` costs a large, slowly-growing fraction of the product's
    own request ceiling. Now measured on real hardware; one question left.**
    `asy_webserver_service.py`'s `_put_status()` resets every registered error source sequentially
    and each FRAM-backed one pays a real FRAM write; WP1/WP2/WP3 grew that set to 21 on `dev`. Two
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

    **What is still open — and it is the load case, not the idle one.** At 11.58s under three
    concurrent readers, `dev` sits at 77% of its own ceiling, and per-chunk cost roughly doubles
    under that contention (~551ms). That leaves headroom of roughly **6 more chunks under load**, not
    the ~10 the twin numbers suggested. Nothing asserts elapsed time anywhere: both client timeouts
    are backstops placed against the cap (the CI suite derives `_RESET_ERRORS_TIMEOUT_S` from a
    mirrored `_SERVER_OUTER_CAP_S`; `tests_hardware/error_log_helpers.py` carries a measured 30.0s),
    and `tests_scripts/test_request_timeout_ceiling.py` enforces every copy against `outer_cap_s`
    itself — but a backstop is not a budget. **Where to fix**: an explicit elapsed-time budget, sized
    against the load case rather than the idle one; and if a future device's chunk count approaches
    ~27, a design-level fix at the source (batched or concurrent reset, one shared chunk) rather than
    a larger client timeout, per CLAUDE.md's root-cause-don't-raise-the-limit rule.

    Twin figures kept only as the harness baseline they are (5 reps, idle host, loopback): `dev`
    8.151s (7.901-8.259) / `wozi` 5.592s (5.534-5.746) at the shipped `gc.threshold(32768)`, and
    7.396s / 5.207s at `gc.threshold(-1)`. Useful for spotting a twin-side regression; not a
    predictor of real-hardware cost in either direction.

25. **Persistence coverage against a HEALTHY store, not just a faulted one.** The digital-twin
    suite only touches SCD30/BMP3XX persistence through Run 4's `_NO_PERSIST_WHEN_FRAM_FAULTED`
    sweep, which runs after Run 3 faulted `fram:write` dead — so it proves "nothing persisted
    through a chip that was unavailable", a far weaker property than the name it used to carry.
    SGP40 gets the real chip-healthy treatment in Run 5b/5c; nothing else does, so a genuine
    regression in another module's FRAM persistence passes CI today. **Where to fix**: extend Run 5c
    to sweep every FRAM-backed source rather than adding runs per module — much cheaper in CI
    wall-clock than a 5b/5c pair each.
    **Queued for this session's own test audit (owner, 2026-09-18) — not to be started before it.**
    **Scanned 2026-09-18, and the gap is much wider than this item's own first paragraph says.**
    It is not an SCD30/BMP3XX gap: `dev`'s generated module makes **12** FRAM-wired constructions,
    plus one implicit `CFGMGR_<name>` logger per `SensorReaderConfig`-based module (WP2's rule), and
    **exactly two of them have any chip-healthy reboot-persistence proof at all** — SGP40 via Run
    5b/5c (`_PERSISTED_ERROR_MODULES` is literally `("SGP40",)`) and WIFI via Run 8. Everything else
    — SCD30, BMP3XX, ISL29125, SYSTEM, NOTIFY, NTP, WEBSERVER, DNSSRV, every `CFGMGR_*`, and `dev`'s
    two `uart_link` instances — is covered only by the faulted-chip sweep, which cannot distinguish
    "persistence works and the chip was dead" from "persistence never worked". NEOPIXEL is the one
    real exemption (no persisted logging at all, Part C.7.1). The audit's own first task is
    therefore to decide the sweep's shape, since a per-module 5b/5c pair × ~12 is not affordable in
    CI wall-clock and a single generalized Run 5c sweep is.

28. **`TEST_PARALLELISM` now autodetects host capability — the residual is a calibration question,
    not an open design decision.** The 4x-core-count default failed a healthy twin test on the bench
    Pi4 through CPU starvation alone (reproduced with twelve synthetic busy-loops and no parallel
    test processes), while being entirely safe on a fast 4-core x86 host — core *count* cannot tell
    those apart. `scripts/test.sh` now times a fixed integer loop in the very interpreter the tests
    run under and picks the multiplier from that (4x at <=250ms, 2x at <=900ms, 1x beyond), honouring
    a cgroup CPU quota when one is set, with `TEST_PARALLELISM` still overriding everything.
    Measured: 131-141ms (8 samples) -> 16 jobs on this project's x86 sandbox, unchanged from before,
    and a simulated Pi4-class 704ms -> 8 jobs.
    **One correction, 2026-09-18**: an earlier revision of this item quoted "117ms -> 16 jobs
    (unchanged from before)" as if that were what the script did. It was not — those figures were
    measured in isolation, while the probe itself sat *after* the `tests_scripts/` background launch
    and therefore timed the host with pytest saturating every core. In situ it read **391ms and
    picked 8**, not 16, on the very sandbox it was calibrated against. Fixed by moving the whole
    resolution ahead of that launch (nothing in it depends on anything in between), and
    `tests_scripts/test_test_sh.py` now asserts that ordering — the unit tests around it all run the
    extracted function in isolation on an idle machine, so none of them could have caught it. The
    wall-clock cost on that host was small (4m30.9s autodetected vs 4m26.6s pinned at 16) only
    because the backgrounded pytest tier at 263s was the binding constraint at both settings; the
    real defects were the non-determinism and that the probe was not measuring what it claimed to.
    **What is left**: the thresholds are calibrated from one fast host
    plus a simulated slow one, not from the Pi4 itself — if a real bench run still starves that twin
    assertion at 2x, the next step is 1x for that class, or widening the assertion's own budget.
    Note `_wait_until()` counts poll *iterations*, not wall clock, so making it a true wall-clock
    timer would make this worse rather than better.

29. **A real WiFi outage logs `W4` ("WLAN wrong password") twice alongside the expected `W5`
    ("access point not found"), on a network whose password never changed.** Observed on the dev
    bench board during `test_real_wifi_outage_and_recovery_while_in_normal_sta_mode` (2026-09-17).
    `tests_hardware/bench/test_network_resilience.py`'s own
    `_assert_wifi_log_has_only_benign_ap_not_found_warning()` expects only `W5`. Either the CYW43
    driver reports a misleading status during an AP-down transition and
    `asy_wifi_service.py`'s `_poll_sta_connect_status()` faithfully records it (making the test's
    expectation wrong), or the status mapping there is off. Not chased — one look should tell which.
    **Read item 35 with this one** (added 2026-09-18): `_poll_sta_connect_status()` persists one
    warning per connect *attempt*, and an outage retries, so "W4 twice" may be two attempts rather
    than two verdicts about one. That does not by itself explain a wrong-password verdict on a
    correct password, but it does change what the bench run should be looking at.

30. **ISL29125 HTTP connection reset under concurrent API load — root-cause not yet established.**
    Owner's direction: chase, root-cause and resolve. Needs **both** a config-persisting PUT and >=2
    concurrent readers (four-arm isolation on the dev bench, 2026-09-17: PUT alone 0/10, PUT + 1
    reader 0/6, PUT + 2 readers **6/18**, plain GET + 2 readers 0/6), so it is a real residual, not a
    test artifact, and not the `max_connections=4` reject path (that one is a clean single-worker RST
    at 5 concurrent workers, by design). Failures land at 21-72ms against 0.5-2.2s for successful
    writes — two cleanly separated populations, and the connection dies before reaching the handler.
    **The DUT logs nothing**: `WEBSERVER`'s counter stays 0, so this is invisible to FRAM forensics.
    The suspected mechanism is the deferred flash write's own interrupt-disable window
    (SPECIFICATION.md Part F.2's accepted residual risk) — **suspected, not proven**; all that is
    established is that the persisting write is necessary. Note the write path is now gated behind
    `@pytest.mark.persistence_write`, so reproducing it needs `--allow-persistence-writes`.
    **Where to look first — corrected 2026-09-17 after comparing the two arms properly.** An earlier
    version of this item said the BMP3XX arm passing "points at load/timing rather than at this one
    driver". That reads the evidence backwards. The two tests are the *same* shape: 2 GET workers on
    `/sensors` plus one writer alternating between two valid values, same endpoint, same
    `ConfigManager.write_config()` flash path. Identical setup, opposite outcome, so the flash write
    the two share cannot be what distinguishes them — the difference is in what each driver's own
    push does on the bus. `BMP3XX._push_pressure_oversampling()` is a single `set_*` write.
    `ISL29125._push_resolution()` → `set_resolution()` is a **three-step reconfiguration**:
    `isl.configure(resolution=...)`, then `_reapply_persist()` (the derived persistence counter
    changes with the cycle length), then — because `RangeAuto` defaults to `True` and `dev` leaves it
    there — `_switch_range()` to re-arm threshold registers that are scaled to the old resolution.
    That is a far longer critical section against two concurrent readers, and it is the first thing
    to instrument. **Cheap bisection**: `RangeAuto` is a plain REST bool, so `PUT /sensors
    {"ISL29125": {"RangeAuto": false}}` drops the third leg without touching any code — if the reset
    rate falls, the re-arm is implicated; if it does not, it is the first two.

31. **The website's errcount catalog is keyed per logger INSTANCE now - fixed (owner decision,
    2026-09-18).** `buildgen/definitions.py`'s `_errcount_group()` took only a `set[str]` of have-keys
    and emitted one fixed row per driver kind, plus two hardcoded `UART_init`/`UART_resp` rows, while
    the API derives its keys from the live object graph (`SensorReaderConfig.get_error_sources()`
    returns `[self, self.cfgmgr]`; the generated `_collect_error_sources()` loops over every
    constructed module). It now takes the `DeviceModel` and emits one row per instance from
    `spec.resolved_name` - the same string the API publishes - with the label suffixed by `name_ext`
    (`_NAME_EXT_LABEL` keeps `init`/`resp` rendering as "Initiator"/"Responder", so no real device's
    UI text moved). `uart_link` became an ordinary catalog entry; the hardcoded pair is gone.
    **No real device changed**: the golden-file comparison against all six hand-written
    `html/definitions/*.json` still passes byte-for-byte, which is what "latent, not live" meant.
    Both synthetic fixtures are now correct, and `_KNOWN_CATALOG_DRIFT` in
    `tests_scripts/test_digital_twin_generated_boot.py` is deleted rather than updated - the parity
    check runs with no exemptions at all, against real booted devices (8 passed).
    **Left for a later audit, deliberately out of this fix's scope**: the cross-cutting `status`/
    `errcount` sections of `definitions.py` are still a hand-maintained catalog rather than
    `@web`-tag-derived the way every per-driver section already is. That is the same class of gap as
    the `buildspec.py` schema entry below (owner: keep hand-maintained, the drivers are an integral
    part of the repo) - worth one deliberate look at whether the two should be decided together,
    not a mechanical continuation of this change.

32. **The bench tier's `ResetErrors` timeout was raised 10.0s → 30.0s with no elapsed-time budget
    to replace what that bound was incidentally enforcing.** Recorded 2026-09-17 during a
    self-audit of this branch; it is the one change on it that loosens rather than tightens.
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
    curve `REAL_HARDWARE_TEST_QUEUE.md`'s R2 asks for (0/1/2/3/4/6 readers). Two points do not
    say whether it flattens: the twin's 12.0s is already below the 11.58s-at-3-readers measurement
    plus any margin, so copying it across would flake the bench suite, and anything above ~15s
    cannot fire before the server's own abort. Both halves of the owner's standing requirement for
    this budget — "reliably won't fail the pipeline accidentally with a false positive" **and**
    "will reliably fail if something really went wrong" — are unsatisfiable until that curve exists.
    **Close this by** taking the curve, then adding the bench analogue of the twin's own budget
    check to `tests_hardware/error_log_helpers.py`.

33. **Closed 2026-09-18 (owner decision): the two open pull requests that targeted this branch are
    dropped, not landed.** PR #102 (`claude/real-hardware-boot-latency-measurements`) and PR #84
    (`claude/real-hardware-memory-validation-p3vkxr`) were real-hardware *workers*, never merge
    candidates, so the `main` merge orphaning them is not a loss. Both are closed on GitHub; their
    branches stay on the remote, so the diffs remain readable if anything is wanted later.
    **Carried across before closing**: PR #102's real boot-latency figures and its disproven
    `webserver` lazy-setup hypothesis are now in SPECIFICATION.md Part A.7's boot-latency note, its
    unexplained **+0.90s** `CFGMGR_SYSTEM` cost is queue row R6. `REAL_HARDWARE_HANDOVER.md` itself was
    deleted once every step it asked for was answered and migrated, as its own first lines instruct.
    **Deliberately NOT carried, which is the one thing to know if this is ever revisited**: none of
    PR #84 exists on any other branch — `buildgen/gc_policy.py`, `scripts/build_firmware.py
    --gc-policy`, `--memory-pressure`, `tests_hardware/device_modules/memory_pressure.py`,
    `tests_scripts/test_hardware_harness_transients.py` and SPECIFICATION.md Part I.6 — so that
    build-and-instrument tooling, and the four validation-apparatus fixes that came with it, are
    unshipped by decision rather than by oversight. Its three bench passes stand as executed (queue
    §5).
    **The adoption record this item's number is cited for (queue row R8) stays valid**: `main`'s
    ISL29125 tests were assessed one by one and the worthwhile ones adopted here 2026-09-18 — the
    calibrate-command and gain-ratio-across-a-real-reboot bench tests (the second gaining the
    `@pytest.mark.persistence_write` `main` lacked, since it owns two persisting PUTs), the
    manual-tier lux/reference-meter test that also records the rig geometry, and — the highest
    operational value — `main`'s `neopixel_sweep` gate on the two long lighting tests with its
    contextual entry in `scripts/_require_clean_hardware_run.sh`. **Not** adopted: `main`'s five
    real-Microdot setter tests, near-redundant against this branch's own driver-tier coverage; the
    one thing none of them pinned — *which* rung rejects an out-of-band value — is now pinned by
    `test_an_out_of_band_knob_is_rejected_by_the_schema_rung_not_the_setter`. The bench tier moved
    from **71 to 73 tests and 12 to 13 deselected**; the flash tier's 51/9 is unchanged, since the
    two new gates skip rather than deselect. Every count re-measured by a real `--collect-only` run.
    Neither adopted bench test has ever run on silicon: queue row R8.
    Also settled here: of the six items `HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md` §1.0 calls
    lost, five are accounted for on this branch or on `main` (checked item by item, not taken at
    face value); only `REAL_HARDWARE_FINDINGS_PR103.md` is unaccounted for, and it never existed in
    any ref here — its substance appears to be what item 30 and queue row R1
    already carry. `claude/pr103-real-hardware-fram-validation` is not on the remote and has no PR.


35. **Two more persisted-warning paths can refill the bounded FRAM history, the same class
    `asy_uart_comm.py` already closed.** Found 2026-09-18 while satisfying the owner's condition on
    item 23 ("take care that such conditions in general do not flood the persisted warnings") -
    the UART module's own budget was checked and holds, so this is what the same lens found
    elsewhere. Reported, not fixed: which entry an operator sees in a field log is a behaviour
    decision, the same class as the `errno` 32 and item 23 decisions.
    - **`asy_wifi_service.py`'s `_poll_sta_connect_status()`** persists exactly one of `wrnno`
      4/5/6/7 per call and returns, which is correct *per attempt* - but a real outage retries, and
      every retry spends another slot. A ten-slot ring is gone in ten retries, evicting whatever
      preceded the outage. **This is very likely the mechanism behind item 29** (a real outage
      logging `W4` twice alongside `W5` on a network whose password never changed): two entries are
      two attempts, not necessarily two different verdicts about the same one. Worth reading the two
      items together before chasing either - and worth checking on the bench run rather than only by
      reading code, since the alternative explanation (the CYW43 genuinely reporting a misleading
      status mid-transition) is still open.
    - **`asy_fram_manager.py`'s `_read()`** persists `wrnno` 71/72/73 on every degraded read, so a
      permanently corrupted block 0 logs one warning per read forever. The dual-copy layer means the
      data is still correct, which is exactly why this can run unnoticed for a long time.
    **Shape of the fix, if taken**: `asy_uart_comm.py`'s `_episode_wrn()` is the worked precedent -
    one persisted warning per episode, the rest visible-only, with the episode's own boundaries
    defined by the module. It is not a mechanism to lift wholesale; each of these two needs its own
    answer to "what is an episode here", which is the part needing a decision.

36. **`web-unit-tests` has under 2x headroom against its own 20-minute `timeout-minutes`, and that
    margin has now been spent twice.** CI run `35372354351` (head `b0f755c`) was cancelled at
    19m33s with every other job green; the same suite on the same tree runs in **9m36s locally**
    (11 files, 778 tests, exit 0, measured 2026-09-18), and the previous CI run on an identical
    `js/`/`tests_js/`/`html/` tree took 9m23s. So this is wall-clock on GitHub's runner, not a test
    regression - the same failure the job's own comment already records once before (PR #50, run
    `33856690559`), whose fix then was splitting `web-coverage` out rather than widening the budget.
    Nothing is proposed here: the budget is the owner's to set, and the suite's real cost is a
    headless-browser tier plus a live digital-twin subprocess, neither of which shrinks by trying
    harder. Worth noting that a cancelled run also **skips** `web-coverage` and
    `web-cross-browser-smoke`, so one slow runner silently removes three signals, not one. Options
    if it recurs: raise `timeout-minutes` for that job, or split the live-backend PUT matrix into
    its own job the way coverage already is.

37. **Five cross-file consistency findings carried over from `main`, each re-verified on this branch
    (2026-09-18) and each still needing an owner yes/no.** They were raised on `main` by the
    ISL29125 promotion's bird's-eye `src/` scan (2026-09-12) with recommendations added 2026-09-13,
    and this branch had never picked them up. None is a bug; each is a place two files answer the
    same question differently.
    - **`FiltCoeff` means two different things** - BMP3xx's on-chip IIR register (discrete `int`
      from `_IIR_SETTINGS`) and the ISL29125's software EMA coefficient (`float`, -1.0 = off), same
      field name on the same `/sensors` endpoint. No wire collision (the sensor group namespaces
      it). **Recommendation: leave it** - renaming the BMP3xx field is a config-schema migration on
      deployed units for a cosmetic gain, and both carry their own `description` in
      `html/definitions/<device>.json`, which is where a user meets them.
    - **Four names for two trigger-event roles**: `trigger_event` (BMP3xx/SGP40),
      `start_trigger_event` + `irq_trigger_event` (SCD30), `base_trigger_event` + `read_event`
      (ISL29125). **Recommendation: the ISL29125 pair if any** - it is the only naming that says
      which role is which. A pure rename, but it touches three drivers and their tests.
    - **`from asyncio import ThreadSafeFlag` appears in exactly one file** (`asy_scd30_driver.py`);
      every other file writes `asyncio.ThreadSafeFlag`. **Recommendation: change the one file** -
      four lines, no behavioural risk, the cheapest of the five.
    - **`_N_*_CFG` constants group on two axes** - by type (BMP3xx, ISL29125) and by purpose
      (SGP40). **Closed as "both, and the rule is whichever axis separates them"**: the ISL29125
      ended up with two float batches, which no type-based name can tell apart, hence
      `_N_STORE_CFG` beside `_N_FLOAT_CFG` - SGP40's own reasoning. Both are present here.
    - **Return-annotation quoting is mixed project-wide**: 22 `src/` files carry quoted subscripted
      return annotations, 11 carry unquoted ones, 9 carry both. MicroPython never evaluates
      annotations, so both are safe and there is simply no stated convention. **Recommendation:
      state the rule, do not mass-edit** - quote an annotation naming a `TYPE_CHECKING`-only
      import, leave the rest bare, as a sentence in SPECIFICATION.md Part D.

38. **Seven `src/` modules number `errno`/`wrnno` inside the range `base_classes.py` reserves, and
    the owner's standing direction (2026-09-11) is that every module aligns to it** - carried over
    from `main`, re-verified here 2026-09-18. Part C.7 reserves `errno` 1-9 and `wrnno` 1-2;
    `api_response.py` owns the fixed cross-module slot 99. Non-conformant: `config_manager.py`,
    `system_service.py`, `asy_webserver_service.py`, `captive_dns.py` (all `errno` and `wrnno`),
    plus `asy_wifi_service.py`, `asy_ntp_client.py` and `asy_notification_service.py` on `wrnno`
    alone. **No live clash exists** - none of the seven currently shares a logger with a
    `SensorReader` instance. It becomes a real defect the moment one gains a `logger=`
    reach-through, which is exactly what `AsyFramManager`/`FRAM_SPI` do and what this branch's
    `asy_uart_comm.py` adopted (C.7.1 records it numbering from 10 for that reason). Renumbering is
    mechanical but not free: every changed code is a persisted value in deployed FRAM histories and
    appears in C.7.1, the errcount UI's raw `num`, and existing tests. Needs an owner decision.

39. **An interrupted `setup_toolchain.py env --tier flash` can leave the Unix-port binary without a
    frozen `asyncio`, and `scripts/test.sh` uses it anyway** - carried over from `main` (hit
    2026-09-13). `run_verification_sequence()` builds the interpreter twice (frozen-verification
    manifest, then a vanilla rebuild restoring the real test rig); interrupting between the two
    leaves every `tests/test_*.py` dying with `ImportError: no module named 'asyncio'`, which reads
    as a code failure and is not one. `scripts/test.sh` only checks `[ ! -x "$micropython_bin" ]`,
    so a broken binary is indistinguishable from a good one. Recovery: `rm` the binary and re-run.
    **Recommendation: make that guard a capability check** (`"$micropython_bin" -c "import asyncio"`
    beside the `-x` test, rebuilding when it fails). `main` deferred it because `scripts/` was
    inside a blocking two-chroot pre-push gate; that gate became an owner-run periodic check on
    2026-09-18, so the recommendation is actionable now and only needs the owner's go-ahead.

40. **`SPECIFICATION.md` carries seven subsections about one sensor, and no other sensor has any**
    - carried over from `main`, where the owner ruled (2026-09-14) to leave the document exactly as
    it stands and tidy this in a session of its own. Three patterns exist and only the third is the
    question: *generic rule, named instance* (C.4.3, C.7, D.15 - the dominant, legitimate one);
    *sections named after a module that IS the architecture* (A.7, A.8, C.5, C.6, C.7, Part J -
    Part J additionally being a two-implementation interface definition); and *dedicated
    single-chip technical sections*, which only the ISL29125 has (C.11.1 through C.11.5, including
    C.11.1.1-C.11.1.3). Recorded so that session does not re-derive the scan.

41. **Two device scripts still hand-list their `cfgmgr._cache` keys and will silently miss a new
    schema field** - carried over from `main`, verified here 2026-09-18.
    `bmp3xx_plausibility_read.py` and `sgp40_fram_backup_restore.py` prime the cache from a literal
    dict; the four ISL29125 scripts already derive it from the driver's own schema
    (`{field[0]: field[2] for field in reader.cfg_schema if field[2] is not None}`) and then
    override only what the script deliberately changes. A field added to either driver leaves the
    hand-listed script reading a default that no longer exists, which looks like a driver fault.
    The generic form is a two-line change in each, but it can only be validated on the bench - so
    it rides the next real-hardware session rather than being pushed blind
    (`REAL_HARDWARE_TEST_QUEUE.md`).

42. **The 3-line comment cap is enforced in `src/` and measured everywhere else.** The cap was
    tightened from "no hard numeric cap" to 3 lines per inline block by the project owner on
    2026-09-14 and re-confirmed 2026-09-18; `main` had recorded that only the ISL29125 branch's own
    files complied and estimated ~200 pre-existing blocks. The real repo-wide figure, measured
    2026-09-18 with buildgen's machine-read tag lines (`# @web`, `# @wiring`, `# @limits`,
    `# @requires`) excluded as data rather than commentary, is **1,445 over-length blocks**:

    | scope | blocks | files |
    | --- | --- | --- |
    | `tests/` | 842 | 87 |
    | `tests_hardware/` | 144 | 43 |
    | `tests_scripts/` | 125 | 30 |
    | `tests_js/` | 74 | 12 |
    | `scripts/` | 73 | 5 |
    | `js/` | 70 | 9 |
    | `buildgen/` | 62 | 15 |
    | `digital_twin/` | 46 | 14 |
    | `toolchain/` | 9 | 2 |

    `src/` was swept to **zero** in the same pass (121 blocks, of which ~27 turned out to be tag
    runs), because it is the shipped firmware and the one scope where the rule earns its keep;
    nothing was deleted, only tightened or moved to the Part that already owned the fact. The rest
    is deliberately left: rewriting ~1,400 comment blocks in one diff would bury any review, and
    each one still needs the judgement call about where its detail belongs. Best taken scope by
    scope, `tests/` last - it is 58% of the total on its own.

## Deferred / explicitly out-of-scope work

- **The `main` merge conflict: how it resolves was settled 2026-09-14/18; only WHEN is open.**
  Recorded here so no future session re-opens it as a design question. `main` and this branch built
  the ISL29125 driver twice, in parallel, on the same day - `main` via PR #75, this branch via its
  own buildgen-native port (PR #83, forked from `03192a5` before the promotion existed on any shared
  ref). Git therefore sees six files as `add/add`, and the content conflicts are both sides writing
  up the same driver in the same places (`SPECIFICATION.md`, `BACKLOG.md`, `DEVICE_REFERENCE.md`,
  `html/definitions/dev.json`, `js/definitions.js`, `mockdata/dev.json`, the bus-hazard tests, six
  `tests_hardware/` files). Nothing else on `main` conflicts: the `arduino/` libraries are a pure
  addition and the SCD30 settle fix auto-merges.
  **Resolution: take this branch's side.** It is the newer of the two and carries three fixes `main`
  never got (the configurable INT pull-up, the shadow-divergence race fix, saturation moved out of
  `wrnno=12` into the API's `Overrange` field), and its driver differs from `main`'s by +140/-60,
  most of that the same code reworded. The two modify/delete conflicts (`src/sensortask_dev.py`,
  `digital_twin/run_dev_integration.py`, which PR #75 edited to wire the ISL29125 in by hand) resolve
  as **keep deleted** - buildgen generates both now, and `devices/dev.toml` already carries the
  wiring.
  **The exceptions list is already merged, not still owed**: `main`'s worthwhile ISL29125 tests were
  assessed one by one and adopted here in `32afd7f` (item 33 has the full account, queue row R8 the
  never-run-on-silicon caveat), so the resolution no longer needs to reach into `main`'s side for
  anything. What remains is purely mechanical, and is the owner's to schedule.

- **CLAUDE.md's 3-line header-comment cap eroded across this branch — `src/` is fixed, and the 61
  test-side blocks are deferred to one concentrated documentation-style run** (owner decision,
  2026-09-18: the cap stands as written, and the rest gets fixed in a single dedicated pass, not
  piecemeal alongside unrelated work). Measured 2026-09-18 over every triple-quoted module/class/
  function header in the eight lint scopes: `main` carries **18 over-cap blocks out of 290 (6.2 %)**,
  this branch **63 out of 431 (14.6 %)**, and 58 of the 63 sit in files this branch touched — drift
  introduced here, not the repo's pre-existing state. By scope (main → branch): `tests/` 7 → 30,
  `tests_hardware/` 10 → 17, `tests_scripts/` 1 → 9, `toolchain/` 0 → 3, `scripts/` 0 → 2, `src/`
  0 → 2. **The `src/` half is already done** (2026-09-18), that being the fully-reviewed bar and
  clean on `main`: `asy_notification_service.py::_DefaultSignalSink` and
  `asy_sgp40_driver.py::_DefaultTemperatureSource` are back to 3 lines with the detail moved to
  adjacent inline comments, so `src/` is at 0 over-cap blocks again. The remaining 61 are all
  test-side; the worst are module headers that became mini-essays —
  `tests/_sensortask_scenarios.py` (17 lines),
  `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py` (17),
  `bus_concurrency_isl29125_write_vs_siblings.py` (16),
  `tests/test_digital_twin_sensortask_integration.py` (15),
  `tests/_digital_twin_construction_scenarios.py` (14),
  `toolchain/micropython_overrides.py::apply_unix_kbd_intr_override` (13). The run applies the
  rule's own escape hatch throughout — relocate the prose to `SPECIFICATION.md`/
  `digital_twin/README.md`/an adjacent inline comment, never drop it.
- **CLAUDE.md's two-target clean-chroot verification is an owner-run periodic check, not a blocking
  per-push gate - settled (owner decision, 2026-09-18).** The recipe, both targets and the separate
  installer verification all stand exactly as CLAUDE.md documents them; what changed is who runs
  them and when. The owner runs them manually every now and then, on the bench Pi4 (trixie/GCC 14.2)
  or their own box, rather than a session blocking a push on a chroot it usually cannot build.
  The legs were last satisfied 2026-09-12. Changed on this branch since, against `main`:
  `scripts/test.sh` (+520 lines - parallelism autodetection, the backgrounded `tests_scripts/` job
  and its timeout, the heap-size and port-base moves), `scripts/typecheck.sh`, `scripts/lint.sh`,
  `scripts/build_firmware.py`, `scripts/_require_clean_hardware_run.sh`,
  `scripts/run_digital_twin_ci.sh`, `scripts/run_unix_port_integration.sh`, `pyproject.toml` (+159),
  and - the class the lint/typecheck recipe never exercises at all - `toolchain/setup_toolchain.py`
  plus the new `toolchain/micropython_overrides.py` (PR #90's `MICROPY_ASYNC_KBD_INTR=0` Unix-port
  build override, SPECIFICATION.md Part B.14.1). That last pair is what a compiler-version-sensitive
  break would actually show up in, so it is the part worth the owner's next manual run; a
  `scripts/test.sh` change is host tooling and low-risk. Kept here as the running list of what is
  owed, not as a merge blocker.

- **Session 7's `pyproject.toml` `max-args` ratchet (21 → 22, for `WebserverService.__init__`'s new
  `build_info=` parameter) only got the noble leg of CLAUDE.md's required two-target clean-chroot
  pre-push verification** — the narrower, earlier instance of the entry above. The trixie leg — required by the same rule whenever `pyproject.toml`
  changes, specifically to catch a GCC>=14-only issue the noble/GCC-13 leg can't see (the precedent:
  the mbedtls `-Warray-bounds` false positive, SPECIFICATION.md Part B.7.1) — couldn't be run from
  that session's own sandbox: `debootstrap --variant=minbase trixie` needs `deb.debian.org`, which
  the sandbox's egress policy rejected outright (confirmed directly, not a transient failure), with
  no alternate Debian mirror to fall back to. The change itself is a pure ruff/pylint lint-rule
  threshold with no compiler-version sensitivity, so the residual risk is judged low, not zero — a
  from-scratch trixie leg (or a run on the bench Pi4, which already runs trixie/GCC 14.2) should
  still confirm it whenever one is next convenient. The change itself is the `build_info=` parameter
  SPECIFICATION.md Part L.7 describes.
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
  forgetting it into a named error rather than a confusing one. Kept only to record that the
  alternative was considered and declined; don't re-propose it. (Item 31's closing note flags that
  `definitions.py`'s cross-cutting `status`/`errcount` catalog is the same class of hand-maintained
  table, worth deciding alongside this one if it is ever revisited.)
- **`[device].name`/`hostname`/`hotspot_password` are wired into the boot path now - done (owner
  decision, 2026-09-18).** Every device really did boot as `SensorNode` whatever its TOML said; the
  three fields were validated and then reached nothing. `AsyConnTime.__init__` takes `hostname=`/
  `hotspot_password=` and substitutes them as the **defaults** of the two ConfigManager-persisted
  fields (`_with_default()`), so a user rename through the web UI still wins on a later boot, and
  every existing test that asserts the literal `"SensorNode"`/`"12345678"` keeps passing untouched -
  `None` means "keep the shared default", which is what a bare construction asks for.
  `buildgen/codegen.py` passes `devices/*.toml`'s own values into the generated `AsyConnTime(...)`
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
  A flash-tier run should confirm both, whenever one is next scheduled
  (`REAL_HARDWARE_TEST_QUEUE.md` R10).
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
    a substitute for the full 6h window this item was always about
    (`REAL_HARDWARE_TEST_QUEUE.md` S4).
- **Website definitions-file autogeneration — done (SPECIFICATION.md Part L.4).** The
  `@web`/`@web-group` comment-tag family and `buildgen/definitions.py`'s generator now exist,
  resolving every open question this entry used to track (anchoring a non-driver-schema value like
  `lightCmdLED`, `@web-group`'s relationship to `SettingsGroup(...)` wiring, the formal grammar's
  scope) — see SPECIFICATION.md Part L.4 for the resolutions and
  `tests_scripts/test_buildgen_web_tag.py`/`test_buildgen_definitions.py` for the test coverage.
  Generating `html/definitions/<device>.json` for real was Session 6's own job; that session
  closed two of its three parts — `arzi`/`klkizi`/`grkizi`/`schlafzi` (the four devices that never
  had a hand-written file) now get one generated on the fly by `scripts/build_website.sh`'s own
  fallback, and this is wired into CI's 6-device `firmware-build-verify` matrix. **Still open**:
  retiring `wozi`/`dev`'s own hand-written `html/definitions/{wozi,dev}.json` in favor of generated
  output — deliberately deferred, since `tests_js/live-backend-put-matrix.test.js`/
  `mock-server-put-matrix.test.js` read those two files directly as fixtures and switching them
  over needs a `tests_js/` fixture audit nobody has done yet. **The same wozi/dev-only scope shows up in the browser prototype too**: `js/
  app.js`'s `KNOWN_DEVICES = ["wozi", "dev"]` (its `?device=` switch, prototype-only per that file's
  own docstring — real firmware ships exactly one device's `definitions.json`, never branches on a
  query param) is a real, literal device-name list living outside `devices/*.toml`, but it isn't an
  independent gap: it exists because `mockdata/`/`html/definitions/` only carry fixtures for those
  two devices, the same limitation this entry already tracks. Extending it to all 6 needs generating
  `mockdata/<device>.json` fixtures for the other four first, not just a `KNOWN_DEVICES` edit — found
  by SPECIFICATION.md Part L.1, flagged here rather than fixed piecemeal.
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
  addition beyond feature-parity rather than a postponed fix — owner-confirmed this stays as-is.
  The protocol module is standalone by design: its BME688/BSEC first use case is explicitly out of
  scope and was **not** part of the promotion.
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
- **`asy_i2c_driver.py`'s `get_bits`/`set_bits`/`get_register_struct` now read through
  `readfrom_mem_into()` - done (owner decision, 2026-09-18).** Not the way this entry assumed,
  which is why it is worth a line: it predicted "a changed signature on three shared methods every
  existing driver calls", and no signature moved at all. The allocation was internal
  (`_readfrom_mem()` returned a fresh `bytes` per read), so the fix is one long-lived 32-byte
  scratch per `I2C` instance plus a `memoryview` slice - CLAUDE.md's "reuse, don't churn
  same-shaped objects" (Part I), applied where it costs nothing at the call sites.
  Safe to share across the devices on a bus because every one of these methods fills and decodes
  with no `await` in between, and no `Timer`/`Pin.irq` callback in this codebase touches I2C -
  both checked against the real code, not assumed. A read larger than the scratch (nothing today;
  BMP3XX's 21-byte calibration block is the largest) falls back to allocating rather than refusing.
  `machine.I2C.readfrom_mem_into()` was verified against the pinned 1.29.0 source rather than from
  memory: `extmod/machine_i2c.c` routes it through the same `read_mem()` as `readfrom_mem` with the
  same `OSError` semantics, and rp2's own hardware I2C type reuses that same locals dict.
  Both test fakes gained `readfrom_mem_into()` **delegating to their own `readfrom_mem`**, so fault
  injection (`--fault <chip>:readfrom_mem`), the bus log and every existing test keep working
  unchanged. Three new tests in `tests/test_asy_i2c_driver.py`: the entry points use the
  non-allocating form, a returned value is copied out rather than aliased to the shared buffer
  (the one real hazard this design creates), and an oversized read still works.

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
  NTP-outage-x-bus-load fault recombination has no twin/mock-tier equivalent (no NTP-drop-and-retry
  scenario exists at either tier to extend) - a real opportunity if a future session has the budget,
  not chased yet. The other two recombinations that matter (FRAM write vs. a real hardware reset;
  repeated WiFi flapping x concurrent bus load) already have coverage across every tier where they
  are meaningful.