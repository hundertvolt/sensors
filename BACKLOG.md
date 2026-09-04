# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

## HIGH PRIORITY — ready for a local Pi4 (real-hardware) session to run

- **`asy_wifi_service.py`'s own reconnect-trigger logic (`_run_sta_mode()`/
  `_handle_sta_connection_result()`) has no independent reachability check** - `isconnected()`
  reporting a false positive here has no backstop the way `network_available()`'s NTP consumer
  does (that one's own independently-timeout-bounded UDP round trip degrades benignly regardless -
  proven, `tests/test_ntp_wifi_dns_integration.py`'s `test_full_chain_degrades_cleanly_when_wifi_
  reports_connected_but_the_ntp_server_never_answers`). Real-hardware finding
  (`test_network_resilience.py`'s own account): the CYW43 firmware's `associated: yes`/
  `isconnected()` bookkeeping can stay stuck true well past a 150s wait window after a real outage,
  with no observed upper bound - the existing tests accept a `hard_reset()` fallback as a real pass
  rather than proving the graceful path always wins within some bound. Project-owner's own working
  model (2026-09-04): while `isconnected()` reports true, the CYW43 module is itself attempting
  silent self-resolution, and this is correct/desired for a normally-stable link with short,
  self-resolving outages and for a permanently-disabled AP the DUT was never previously established
  against - matches `_on_sta_disconnected()`'s own code shape exactly for the "never established"
  path (`_register_sta_connection_failure()` -> hotspot fallback once `isconnected()` does flip
  false). The one case confirmed **not** to match this model: an **already-established** connection
  whose AP is gone **permanently** - `_on_sta_disconnected()`'s ESTABLISHED branch retries every 60s
  forever and never reaches `_register_sta_connection_failure()`/hotspot fallback at all, so even a
  correctly-flipping `isconnected()` doesn't converge to hotspot mode here, only to an unbounded
  retry loop - a real, distinct question from the "does isconnected() flip at all" one, not yet put
  to the project owner directly. No unit/twin/real-hardware test proves or disproves the "usually
  self-resolves quickly, bounded in practice" empirical claim - only the "if it doesn't self-resolve,
  a hard_reset() fallback is an accepted real pass" reaction to it. Real-hardware next step: log real
  wall-clock recovery times across several genuine `ap_down()`/`ap_up()` cycles (the existing
  `test_real_wifi_outage_and_recovery_while_in_normal_sta_mode`/`test_real_wifi_flaps_repeatedly_
  without_wedging_the_system` already print `RESULT NOTE` lines distinguishing graceful vs.
  hard-reset recovery - collect these across enough real runs to say whether "usually resolves
  within N seconds" is actually true, not assumed) before treating this as settled either way.

## Refactor targets not yet done

- **`boot_entry/` isn't in `pyproject.toml`'s lint/typecheck `files` scope yet.**
  `boot_entry/wozi_boot.py` is the real, deliberately-separate blocking-import firmware entry point
  for `src/sensortask_wozi.py` (see that module's own docstring and `SPECIFICATION.md` Part A.7).
  Manually confirmed clean today (`ruff check boot_entry/wozi_boot.py` and
  `mypy boot_entry/wozi_boot.py --config-file pyproject.toml` both pass under the existing config),
  but it's not part of `scripts/lint.sh`/`scripts/typecheck.sh`/CI's default scan until
  `pyproject.toml`'s `files`/scan scope is extended to include it - deliberately not done as part
  of this same pass, since any `pyproject.toml` change needs CLAUDE.md's "Pre-push verification"
  chroot recipe run first, and one three-line file didn't seem to warrant that on its own. Fold
  this in next time `pyproject.toml` is touched for another reason anyway.
- **Bare `except:` is forbidden in refactored code** (`except Exception:` or narrower required).
  Ruff's E722 is already enabled to catch any future regression - `src/`/`tests/`/`digital_twin/`
  are all currently clean of them (confirmed: `scripts/lint.sh` reports zero findings, after
  `improved-quality/`'s own tracked bare-except debt was deleted along with the rest of that
  directory).
- **No CI firmware-build stage yet for the legacy `build-*.sh` scripts.** `build-*.sh`'s hardcoded
  `/home/nico/rpi_pico/...` path is fixed (each script now captures its own `$(pwd)` before any
  `cd`, matching how the script has always assumed it's invoked - from inside `py-include/`, real
  dir or symlink, regardless of machine - and passes that as `FROZEN_MANIFEST`; verified with a
  real end-to-end `build-wozi.sh` run producing a successful `firmware.elf` link against the pinned
  v1.28.0 toolchain). Still open: wiring an actual firmware-build stage into CI for these legacy
  scripts specifically. The *new*, `src/`-based toolchain (`scripts/build_firmware.py`,
  `SPECIFICATION.md` Part B.11) already has this: `.github/workflows/ci.yml`'s `firmware-build-verify`
  job builds a real `firmware.uf2` end to end on every push/PR - not the same gap, since the two
  build paths (legacy `python/`+`build-*.sh` vs. `src/`+`scripts/build_firmware.py`) are entirely
  separate pipelines.
- **Mypy shall be configured to disallow `Any` types** (owner-specified, not yet implemented). The
  closest existing option is `disallow_any_explicit`; `pyproject.toml` deliberately stops short of
  it and the other `--strict`-only checks today. Blast-radius check (re-run, not stale): `Any`
  appears ~190 times across 47 files in `src/`/`tests/` today. A large share is still test-file
  monkeypatch/wrapper classes duck-typing a real MicroPython object rather than reimplementing its
  interface, but a real, growing share is now legitimate `src/`-side usage too (`print_log.py`'s
  variadic logging methods, `config_manager.py`'s generic value-checking helpers, opaque
  `ticks_ms()`-typed values) — turning this on will need both a typing strategy for the test
  wrappers (e.g. `Protocol` classes matching just the overridden methods, plus `__getattr__`
  delegation) and a decision on how to type the genuinely-variadic/opaque `src/` cases, not just a
  flag flip.
- **FRAM bus-hazard/recovery test coverage — DONE across all four hard-rule tiers (2026-09-04).**
  FRAM previously had zero presence in any of CLAUDE.md's four hard-rule bus-hazard test files
  (`tests/test_bus_hazard_multi_device.py`, `tests/test_digital_twin_bus_hazard_concurrency.py`,
  `tests_hardware/flash/test_bus_concurrency.py`, `tests_hardware/bench/test_bus_concurrency_under_api_load.py`)
  despite being a promoted, bus-facing device like every I2C driver already covered there - closed.
  Real-hardware fault injection turned out **not** to need the separate GPIO fault-injection harness
  open question 8 flags as "not currently provisioned": FRAM's own CS pin is a plain,
  software-toggled `machine.Pin` the RP2040 already fully owns (`asy_spi_driver.py`'s
  `SPIDevice.cs_pin`), so a self-contained on-device script
  (`tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py`) races it
  directly during the one real yield point inside `SPIDevice.__aenter__()`, no external hardware
  needed - project-owner-proposed technique, confirmed reliable 5/5 trials each for both a hijacked
  write (silently never reaches the chip) and a hijacked read (never returns the real data), both
  asserted as hard requirements, plus a full recovery proof after each. `verify_present()` itself
  was already correctness-tested in isolation before this pass; the real remaining gap closed here
  was tier coverage, not the method's own correctness.
  **REAL FINDING, fixed along the way**: writing the twin-tier fault-injection test surfaced that
  `digital_twin/machine.py`'s `_wire_spi_device()` always constructed a fixed-identity `FramChip`
  (wozi's own 8KB MB85RS64V) regardless of which variant was actually running - `dev`'s own FRAM (a
  different, larger real chip, 256KB MB85RS2MTA) had been silently failing its own device-ID check
  on every twin run since `dev`'s own FRAM was added, caught and swallowed by
  `AsyFramManager.setup()`'s broad `except Exception`, unnoticed until this pass's new assertion.
  Fixed (`_wire_spi_device()` now reads the existing `_i2c_wiring_profile` global, mirroring
  `_wire_i2c_devices()`'s own per-variant branch); full local suite reruns clean.
  **Still genuinely open, a separate and larger question**: there is still no periodic/triggered
  *production* re-probe policy — `verify_present()`/`set_write_protected()` have zero real callers
  in `src/` — this test pass proves the existing primitive works under a real fault, it doesn't add
  automatic recovery to production code. That remains an explicit, undecided design question (who
  calls `verify_present()`, on what trigger) for whenever it's actually wanted.
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
   raise `ImportError`. **The 1.28 mechanism itself is now confirmed, not a mystery**: traced
   directly through the pinned v1.28.0 source (`tools/mpy-tool.py`'s frozen-name generation,
   `py/frozenmod.c`'s exact-match lookup, `py/builtinimport.c`'s `stat_module()`/
   `process_import_at_level()`) - a plain `import sensortask` (no `.py`) is unambiguously correct
   under 1.28: `stat_module()` auto-appends `.py` before matching against the frozen table, while a
   dotted `import sensortask.py` requires "sensortask" to resolve as a *package* (have `__path__`),
   which a flat frozen file never does, so it should raise. `boot_entry/wozi_boot.py` (the
   refactor's own 1.28-targeted entry point) already does `from sensortask_wozi import main` - the
   correct form - so there's nothing to fix on the refactor side. **`modules/_boot.py` itself stays
   untouched**: it targets the currently-deployed 1.26 firmware, a different version whose own
   import machinery hasn't been separately verified here - CLAUDE.md's hard rule (don't touch
   without real 1.26 hardware testing first) still applies, and extrapolating from the 1.28 trace
   above would be exactly the "changing it blind" risk that rule exists to prevent.
2. Config-schema migration is a real data-loss risk on the *current deployed* codebase —
   `ConfigManager` overwrites the entire config file with hardcoded defaults the moment one key is
   missing, so a firmware update adding a config key could silently wipe WiFi credentials/tuned
   values. **Decided: not patched on the current codebase** — accepted (reconfigure via web UI
   after a key-adding update). The refactor's per-sensor config model avoids this failure mode
   structurally, not by patching the current global-JSON codebase.
3. MicroPython version target vs. upstream drift — deployed units run 1.26; upstream stable is
   1.28.0 as of the last check. **Decided**: deployed code stays pinned to 1.26 until a deliberate
   reflash campaign; the refactor is where the version target moves forward. 1.27→1.28 rp2-port
   changes checked so far look RP2350-specific, not RP2040-breaking, but not exhaustively checked
   against every module — re-check whenever the refactor picks a landing version.
4. Does `config_manager.py`'s `write_config()` need long-block-lock-style coordination? **Decided
   by the project owner: no** — a write is fast enough not to matter, and it never happens on its
   own/automatically anyway (only ever triggered by a real user interaction via the REST layer),
   which also matters separately for not wearing out the flash with unnecessary writes. No
   coordination mechanism needed. **Note**: `get_long_block_lock()` itself was already removed
   entirely before this was decided (see CLAUDE.md's "Long-blocking operations" hard rule) — this
   decision doesn't resurrect it.
5. Real-hardware verification gap for `asy_udp_socket.py`/`captive_dns.py`: every UDP-layer claim
   (POLLERR/POLLHUP delivery, truncation, connected-socket source filtering) is verified against the
   MicroPython Unix port's socket implementation, not real rp2/lwIP. **Decided: deferred by the
   project owner** as real future work, not chased directly — but no longer blocked on tooling: a
   real Pico W is reachable over USB serial (README.md's "Real hardware access (mpremote)"), and
   `tests_hardware/` (flash/bench automated `pytest` tests, from SPECIFICATION.md Part E.6's
   mock/twin/flash/bench/manual backend design) closes this gap in code. **Real-hardware execution
   is standing practice** on the bench Pi4, both tiers running clean end to end — see
   `tests_hardware/README.md` for current status and how to run it.

   The Unix port is *also* structurally unable to exercise this code path at all (a genuine,
   confirmed C-level difference between the Unix port's `ports/unix/modsocket.c` and rp2's real
   `extmod/modlwip.c` socket implementations — the Unix port's `connect()`/`bind()`/`sendto()`
   reject `AsyUDPSocket`'s own plain `(host, port)` tuple with `TypeError`, which real rp2/lwIP
   accepts directly). This is worked around entirely from twin-side code
   (`digital_twin/_unix_port_udp_addr_shim.py`, `src/` untouched) so CI can still exercise a real
   NTP/DNS request/reply cycle — see `digital_twin/README.md`'s own `_unix_port_udp_addr_shim.py`
   section for the full three-quirk account. That workaround closes the "can't even run this code
   path in CI" half of the gap; it does not replace real-hardware verification of the actual
   rp2/lwIP transport, which is what this entry is still tracking.
6. Should `asy_wifi_service.py` gain an independent WiFi reachability check? Confirmed on real
   hardware (`tests_hardware/README.md`'s "Known assumptions and open findings"): the CYW43
   firmware/lwIP stack can silently mask a real link disruption from `wlan.isconnected()`/
   `wlan.status()` entirely — a real `arping` probe got zero responses from the DUT while
   `iw station dump` showed it continuously "associated: yes" for hundreds of seconds spanning a
   whole AP outage. This is a well-documented, long-standing upstream MicroPython characteristic
   (`micropython/micropython#9455`/`#9505`/`#18797`, open since v1.19.1/2022), not project-specific.
   `_wlan_isconnected_or_false()` is a bare pass-through to `wlan.isconnected()` with no independent
   check, so `_on_sta_disconnected()`'s retry logic structurally cannot fire if the firmware never
   reports the disconnect. **Decided (2026-09-04): investigated, no `src/` change.** Traced every
   real consumer of connection state across all of `src/` (not just `asy_wifi_service.py` itself) —
   only two exist beyond its own retry loop: `AsyNtpClient`'s `network_available` callback (a false
   "connected" signal just lets a doomed sync attempt through, which fails cleanly via NTP's own
   already-robust independent timeout/backoff/give-up machinery — no crash, just a slightly
   over-counted failure streak) and `WifiUptime` (keeps climbing during a dead-but-reported-alive
   stretch — a real but purely cosmetic `/status` inaccuracy, consumed by nothing that acts on it).
   No hang, crash, or data corruption anywhere; the hardware watchdog is fed by task-supervisor
   health, not network reachability, so this can't cause a WDT-loop either. The one real, concrete
   consequence is slower field recovery (the device can stay silently unreachable longer than the
   normal retry cadence would otherwise achieve, until the CYW43's own internal state changes or a
   physical power-cycle happens) — not a correctness bug, and the "physical intervention as accepted
   backstop" pattern already used elsewhere in this codebase covers it. Given that, the project owner
   judged the complexity of a new probe mechanism not worth it for this level of benefit. Mitigated
   at the test-harness level only, staying as-is (`bench/test_network_resilience.py`'s outage/flap
   tests recover via a real `hard_reset()` if the graceful wait times out, but still re-raise so the
   real limitation stays visible as a test failure; `test_hotspot_role_reversal.py`'s own
   `joined_hotspot` fixture teardown has the same fallback for its own role-flip-back reachability
   wait). **Regression coverage added across every tier this scenario meaningfully applies to**
   (2026-09-04, per the project owner's own follow-up request - "prove the benign behavior of
   every isconnected() consumer under a false-positive, don't just assert it from reading the
   code"): mock tier
   (`tests/test_ntp_wifi_dns_integration.py::test_full_chain_degrades_cleanly_when_wifi_reports_connected_but_the_ntp_server_never_answers`
   - the real `network_available()` chain reports connected via a real `AsyConnTime`/fake-`WLAN`
   object graph while a real, bound-but-never-answering UDP server proves the "sent, then nothing
   back" shape end to end, not just the pre-existing isolated-mock version in
   `tests/test_asy_ntp_client.py::test_asy_ntp_time_gives_up_after_repeated_sync_failures_and_persists_errno_20`);
   bench tier (`tests_hardware/bench/test_wifi_networking.py::test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing`,
   already existing, now cross-referenced as this scenario's own real-hardware proof - the real STA
   link stays up and `isconnected()` genuinely True throughout, only NTP's own port is blocked).
   Deliberately not extended to two tiers: **flash** (no network capability at all - this scenario
   is inherently WiFi/link-shaped, so the tier genuinely doesn't apply, not an oversight) and
   **digital twin** (`digital_twin/network.py`'s `WLAN` fake models a scripted connect sequence,
   not an independently-overridable "looks connected but everything downstream is broken" state
   without twin-internal changes the project owner didn't ask for here - the mock-tier test above
   already proves the same property through the real object graph, which is what the twin would
   have added beyond the mock tier anyway).
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
   pending that decision.
8. **Two real-hardware bench-rig capabilities, flagged as "not currently provisioned" during the
   original `tests_hardware/` design discussion, each gating one test candidate from `[MANUAL]` to
   `[AUTO]`** (migrated from the now-deleted `HARDWARE_TEST_PLAN.md` — see SPECIFICATION.md Part
   E.6 for the surrounding architecture these would extend): a programmable GPIO fault-injection
   harness on the bench rig, which would upgrade the "genuinely wedged I2C bus → watchdog backstop"
   manual test to automated; and a dedicated second WiFi test client on the bench rig (today's bench
   host has only the one WiFi adapter, already hosting the AP), which would upgrade "real end-to-end
   hotspot session" from a manual test to automated. Neither is assumed worth building — flag to
   the project owner as an explicit choice, not a default plan, if either ever becomes relevant.

## Deferred / explicitly out-of-scope work
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
    — real, committed, but `@pytest.mark.long_soak` (skipped unless `--run-long-soak` is passed) and
    **not yet actually run** as of 2026-09-04. Deliberately does **not** use the Unix-port twin's own
    `gc.mem_free()` recovery-peak-trend methodology — confirmed impossible on real hardware without
    disturbing the very system being measured (`mpremote exec()` always interrupts the live system
    first, and a live `asyncio.run()` doesn't resume once interrupted — see the test's own module
    docstring). Instead watches real HTTP soak traffic passively for the two disqualifying symptoms
    observable without disturbing anything: a `MemoryError` traceback, or an unexpected mid-soak
    reboot — a real but coarser signal than an actual trend measurement. Not because the "no
    confirmed leak on the Unix port" conclusion is in doubt (four independent, properly-powered
    replication experiments found no reproducible decline, on either idle or HTTP-soak traffic), but
    because the Unix port's allocator/heap behavior isn't guaranteed identical to rp2040's real one.
    **Next step**: run `scripts/run_bench_hardware_suite.sh --run-long-soak --long-soak-seconds
    <N>` for real and record the result here.
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
  mechanisms. `src/sensortask_dev.py` (the now-deleted `DEV_HARDWARE_BASELINE_PLAN.md`, 2026-09-03) is the first
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
- **`dev.json`'s SHTC3/MPRLS/ISL29125 field entries remain an unconfirmed projection.** These sensors
  have no real driver under `src/` yet, so their `html/definitions/dev.json` entries follow the same
  pattern every promoted sensor's entry does, without a real driver to confirm the projection against.
  Resolves naturally once a future session promotes those drivers — Part C.11 point 9's
  driver-promotion checklist already requires a matching definitions-file update in that same
  session.
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
- **`asy_wifi_service.py`'s getters hide two opposite locking contracts under one shape** —
  `network_available()` requires the caller to already hold `wifi_mode_lock`, while
  `get_wlan_ifconfig()`/`get_dns_server_ip()`/`get_wlan_rssi()`/`wlan_isconnected()` assume the
  *caller does not* hold it (checking `.locked()` defensively instead). A rename to make this
  visible in the method name itself (e.g. `network_available_locked()`) was considered but not
  done - nothing blocks it now that `improved-quality/sensortask-wozi.py` (the WIP file that once
  called `conn.network_available` by its current name) is deleted, but `src/sensortask_wozi.py`
  itself still calls it the same way, so a rename remains a real (if small) call-site update, not
  yet picked up. Meanwhile, a prominent comment sits directly above the first
  self-checking getter, explicitly cross-referencing `network_available()` and naming the
  convention a new getter must pick deliberately.
- **`asy_i2c_driver.py`'s `get_bits`/`set_bits`/`get_register_struct` still call the allocating
  `readfrom_mem()` rather than zero-copy `readfrom_mem_into()`** — no real caller needs the
  zero-copy path yet, but worth doing before `asy_isl29125_driver.py` (its one plausible future
  caller) is migrated.
- **`asy_scd30_driver.py`'s persistent NVM setters have no published write-cycle endurance figure**
  (checked every available Sensirion doc) — safe today only because every setter is REST-triggered,
  never called from a boot path or periodic loop. Don't add a periodic/high-frequency caller
  without reconsidering this.
- **`asy_wifi_service.py`'s 60s STA-retry branch holds `wifi_mode_lock` for up to a minute**, and
  `asy_ntp_client.py`'s sync task waits on that same shared lock — NTP sync can be delayed up to a
  minute during active WLAN instability. A priority-inversion-shaped cost worth having in view, not
  a correctness bug; not acted on.
- **Network fault injection against the real dev bench unit — DONE (2026-09-04).**
  `BenchBridge.inject_network_degradation()` (`tc netem` on `wifi_iface()` only - confirmed
  directly, `eth0`/`br0`/this host's own SSH stay completely untouched) covers loss, latency+jitter,
  real bit-level corruption, duplication, and reordering - the genuine remaining gap this item
  originally identified, once `block_udp_ports()`/`redirect_udp_port_to_local()` turned out to
  already cover the binary block/garbage-response cases. Six new real-hardware tests in
  `test_network_resilience.py`, all verified passing for real on the bench Pi4: sustained
  severe loss+latency (30%/150ms±50ms), light realistic everyday WiFi congestion (2%/30ms±20ms,
  expected to cause *zero* visible impact - a genuinely different assertion shape than every
  other fault test in this tier), real packet corruption, duplicated/reordered delivery, and a
  transient (not sustained) outage that recovers via `asy_ntp_client.py`'s own retry timer with
  no `hard_reset()` anywhere in the test - the real-hardware form of
  `tests/test_asy_ntp_client.py::test_integration_recovers_on_retry_after_one_dropped_request`.
  Parameter ranges are grounded in researched real-world figures (congested-WiFi/poor-link
  reference figures from published `tc netem` testing guides), not arbitrary - see the new tests'
  own section-header comment for the citations. Deliberately not attempted: reproducing the ~150
  other mock-tier `asy_wifi_service.py`/`asy_ntp_client.py` tests that inject a raw firmware/API-level
  exception (e.g. `wlan.connect()` itself raising) - those aren't network-*path* faults `tc`/`iptables`
  can express at all, they're CYW43-firmware-level faults the digital twin's own `--fault wlan:...`
  hook already covers software-side; only genuinely wire-level fault shapes (loss, latency,
  corruption, duplication, reordering, block, garbage) were in scope for a *network* fault-injection
  pass, and that set is now believed complete.
- **Compound-fault coverage (bus contention x network degradation) — confirmed passing for real
  (2026-09-04).**
  `tests_hardware/bench/test_bus_concurrency_under_api_load.py::
  test_concurrent_get_sensors_under_real_multi_client_load_survives_light_network_degradation` (the
  cloud-session bird's-eye-review test flagged as "written and ready, never yet run") ran clean on
  the bench Pi4 against the real dev board: concurrent multi-client `GET /sensors` bus reads plus a
  concurrent SGP40 general-call reset, all under real, simultaneously-active `tc netem` "everyday
  congestion" (`loss_pct=2, delay_ms=30, jitter_ms=20`) - zero corruption findings, full recovery
  once the degradation cleared, all four modules' (`SCD30`/`BMP3XX`/`SGP40`/`FRAM`) error logs
  clean. Re-ran together with the file's other (pre-existing, clean-network) test - both pass,
  95.93s. **Session note, not a project fact**: the bench host's own shell session had been started
  before `ensure_dialout_group()` granted `nico` real `dialout` membership, so `groups`/direct
  `pyserial` opens against `/dev/ttyACM0` failed with `Permission denied` despite `/etc/group`
  already listing it correctly - worked around with `sg dialout -c "..."` per invocation rather than
  needing a fresh login; a brand-new session/shell wouldn't hit this at all.
