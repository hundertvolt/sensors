# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

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
  **Tier-parity gap found and closed (2026-09-04, cross-tier distribution audit)**: the flash-tier
  CS-hijack script exercises both a write and a read race, but the twin-tier exception-injection
  test only ever covered `write` - `readinto`, FRAM's other real fault-injectable op (`_FAULT_DEVICE_OPS`),
  had no twin-tier sibling. Not a redundant gap either: `_read_address()` (`get_values()`'s/
  `verify_present()`'s own real read primitive) has no try/except of its own, confirmed the same
  shape as `_write()`'s already-documented one - genuinely distinct code from the write path,
  needing its own proof that `AsyFramManager`'s one-layer-up broad `except Exception` is what
  protects it. Added `test_wozi_fram_recovers_after_an_injected_spi_read_fault` (mirrors the write
  test: seed real content, inject a `readinto` fault, assert it propagates as a raised `OSError`,
  `verify_present()` recovers cleanly, then a fresh read returns the real pre-fault seeded bytes,
  not stale/corrupted ones). 4/4 tests in the file pass; ruff/mypy clean.
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
   pending that decision. **New real evidence for this same tradeoff (2026-09-04)**: this file's own
   "real, easily-reproducible `MemoryError` under sustained real concurrent HTTP load" entry -
   concrete confirmation that concurrent request handling can already push the heap into real,
   if transient, near-exhaustion troughs at the *current* `max_connections=4` - a data point against
   raising the cap without also addressing headroom, not just a RAM-per-buffer cost argument.
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
    identical to rp2040's real one. **Next step**: run `scripts/run_bench_soak_tests.sh --tier
    long` for real (its own dedicated invocation now - see this file's own soak-tier entry below)
    and record the result here.
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
- **`isconnected()` false-positive behavior — real wall-clock recovery data collected, proven
  graceful via new test coverage, no `src/` change (2026-09-04).** Follow-up to the
  previously-open "does the graceful path usually resolve quickly?" question (was itself
  originally opened by a cloud-session bird's-eye review, see this file's own git history).
  **Real-hardware timing data, 8 real trials total on the bench Pi4** (`test_network_resilience.py`'s
  own `RESULT NOTE` lines, now printing actual elapsed seconds, not just which path was taken):
  - `test_real_wifi_outage_and_recovery_while_in_normal_sta_mode` (one real 15s `ap_down()`/
    `ap_up()` cycle while already `_PHASE_STA_ESTABLISHED`): **5/5 real runs required the
    `hard_reset()` fallback**, every one landing tightly in the 154.0-160.2s range (i.e. the
    graceful path essentially always rides out the full 150s wait ceiling before falling back) -
    this falsifies the "usually self-resolves quickly" half of the working model for *this exact*
    outage shape. `isconnected()` genuinely never flips false within the window in practice, not
    just "sometimes."
  - `test_real_wifi_flaps_repeatedly_without_wedging_the_system` (3x cycles of a real 3s
    `ap_down()`/3s `ap_up()`): **3/3 real runs recovered gracefully**, tightly clustered at
    28.7-30.4s - the opposite outcome, and just as consistent.
  This is a genuine, non-obvious asymmetry - repeated brief flapping self-heals reliably, one
  longer sustained outage essentially never does within 150s - worth recording precisely as
  observed rather than theorized away. Plausible mechanism (not confirmed, flagged as such): the
  bridge/hostapd side's own multiple deauth/reassociate events during the flap sequence may drive
  the CYW43 firmware's internal state machine through a transition a single clean 15s gap doesn't
  trigger - but this project's own code has no visibility into the CYW43 firmware's internals to
  confirm that, and doesn't need to; the `hard_reset()` fallback already covers the "didn't
  self-resolve" case correctly regardless of *why*.

  **Doc/repo/forum research** (widening BACKLOG's existing `micropython/micropython#9455`/`#9505`/
  `#18797` citations): `micropython/micropython#9455` (Pico W network inaccessible after ~5-10min
  idle, `OSError: -2`, no upper bound reported, still open, no maintainer fix/root-cause statement -
  one comment notes external pings extend accessibility, consistent with "periodic servicing" being
  a mitigation, not a fix); `#9505` (stale IP/status after a real AP-side disconnect, still open);
  `micropython/discussions/17207` ("half connected unusable state" - `isconnected()==True`,
  `status()==STAT_GOT_IP`, `ifconfig` address invalid, requests fail `OSError -2`, no maintainer
  firmware-level explanation, community workaround is a full `deinit()`+reconnect, not detection);
  Alan Edwardes' practitioner write-up (no reliable detection method found either; settled on a
  bounded connect-timeout + treating a chip-level reset as the real recovery mechanism - the same
  shape this codebase already uses). **No source found across any of this treats independent
  reachability probing as a solved problem** - every thread converges on "can't fully trust
  `isconnected()`, no upstream fix exists, a reset is the real backstop," matching this project's
  own already-decided position. This project's own `wlan.config(pm=0xA11140)` (power-save disabled,
  already in `asy_wifi_service.py`) is the one documented partial mitigation from that research, and
  it's already applied.

  **Code re-verified directly (not just recalled) to confirm graceful behavior, per the project
  owner's own framing: "no crash, graceful degradation with self-healing as soon as detectable" -
  already the case, confirmed by re-reading every real code path, not assumed**: every
  WLAN-observing call in `asy_wifi_service.py` is individually try/except-wrapped, degrading to
  `None`/`False`, never raising; `hw_op_failed` (the one flag that can trigger a task restart) is
  only ever set by a genuine hardware exception, never by `isconnected()` merely reporting a stale
  value, so the false-positive quirk itself structurally cannot cause a restart loop; self-healing
  begins on the very next `wifi_refresh_sec` (5s) cycle once `isconnected()` does flip, with no
  extra latency layered on top by this project's own code. Both downstream consumers
  (`asy_ntp_client.py`'s `network_available()`, `sensortask_wozi.py`/`sensortask_dev.py`'s
  `/status` fields) degrade to already-tested cosmetic/self-clearing effects, never a crash - see
  "Should `asy_wifi_service.py` gain an independent WiFi reachability check?" above for the full
  per-consumer trace. `is_hotspot_active()` is unaffected by construction (a plain `_conn_phase`
  int-compare, never touches `wlan` at all).

  **New unit-test coverage added (mock tier, `tests/test_asy_wifi_service.py`)** to make this
  graceful-degradation claim a standing, machine-checked guarantee rather than a read-the-code
  conclusion, per the project owner's own explicit direction that this is of major importance:
  - `test_run_sta_mode_stays_benign_across_many_cycles_when_isconnected_is_permanently_stuck_true` -
    drives the real (not monkeypatched) `_run_sta_mode()` across 30 real cycles with `isconnected()`
    permanently stuck true, proving `_conn_phase` stays `ESTABLISHED`, `connection_failures` stays
    0, `hw_op_failed` stays `False`, and no reconnect is ever even attempted - the real bug's exact
    shape.
  - `test_run_sta_mode_attempts_a_real_reconnect_on_the_very_first_cycle_once_isconnected_finally_flips_false` -
    completes the picture: after 10 stuck-true cycles, flips `isconnected()` false and proves a real
    reconnect attempt (`wlan.connect()`) fires on the very first following cycle, not a later one.
  Both pass; full local suite (`scripts/test.sh`) reruns clean, ruff/mypy clean. **Deliberately not
  extended to the digital twin tier, re-considered and still correct**: `asy_wifi_service.py`'s own
  code has no way to distinguish "genuinely still connected" from "`isconnected()` incorrectly still
  reporting connected" - both execute the bit-for-bit identical code path, so a twin-tier repro of
  the *wifi module's own* steady state would just re-exercise the ordinary connected-steady-state
  already covered by `tests/test_digital_twin_sensortask_integration.py`'s own
  `test_watchdog_is_never_starved_while_every_real_task_runs_concurrently`. The one place a false
  positive produces genuinely divergent, testable behavior is where a dependent operation that's
  actually broken gets attempted anyway (NTP's real UDP round trip) - and that's the
  `network_available()` consumer already covered at mock tier (`test_full_chain_degrades_cleanly_
  when_wifi_reports_connected_but_the_ntp_server_never_answers`, the real object graph) and bench
  tier (`test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing`, real hardware),
  with digital twin already correctly excluded there too - unchanged from that existing decision.
  Flash tier: still N/A (no network stack element).

  **Standing design decision, restated for clarity per the project owner's own framing (2026-09-04):
  this is not a critical top-level issue, not even a style break.** Hotspot mode is already
  time-limited as a deliberate safety measure; a physical power cycle bringing a permanently
  unreachable device back to hotspot mode (via `hard_reset()`, or in the field a real power cycle)
  is an accepted, intended, **stable feature** of this project's own fault-recovery design, not a
  fallback to chase away - the same "hardware watchdog/physical intervention is the accepted
  backstop" principle CLAUDE.md already applies to a wedged I2C bus, applied here to a wedged WiFi
  link. **Confirmed inherently safe, not just assumed**: every real flash write in `src/` is
  reachable only through the REST PUT path (traced every real caller of `write_config()` -
  `base_classes.py`'s `_set_mgr_cfg()`/`_set_dict_cfg()`, invoked exclusively from
  `api_response.py`/`asy_webserver_service.py`'s PUT handling, no exceptions found), so a device
  whose API is genuinely unreachable structurally cannot have a flash write in flight - a power
  cycle during this state carries zero flash-corruption risk. Full reasoning, folded into the
  permanent architecture record alongside the existing I2C wedged-bus backstop: SPECIFICATION.md
  Part F.2; the standing rule itself: CLAUDE.md's "Hard rules". The real timing data above just
  replaces "usually resolves quickly" with a more precise, evidence-backed picture of when that
  backstop actually gets used in practice for one specific outage shape - it doesn't change the
  design decision itself. No `src/` change made or needed.
- **Three new recombination tests, project owner's own explicit follow-up request (2026-09-04),
  built and folded into every tier they're genuinely meaningful for:**
  - **FRAM write vs. a real hardware reset.** `tests_hardware/flash/test_bus_concurrency.py::
    test_fram_hard_reset_race_during_write_and_recovery` (flash tier) - a real `machine.reset()`
    raced against an in-flight FRAM write at the same deterministic yield-point technique the
    CS-hijack test uses, via a new `Board.run_isolated_expect_reset()` harness primitive; confirmed
    5/5 real trials. `tests/test_digital_twin_sensortask_integration.py::
    test_sgp40_voc_backup_unflushed_write_is_lost_but_the_system_recovers_cleanly_to_the_last_flushed_state`
    (twin tier) - a real write that lands in-memory but is never flushed before a simulated reboot,
    proving the system falls back cleanly to the last durably-persisted state.
    `tests_hardware/bench/test_end_to_end_timing.py::
    test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly` (bench tier) - three
    real `hard_reset()`s at uncontrolled points relative to SGP40's own real, natural backup
    cadence (BackupPeriod=1min), honestly documented as probabilistic (a host-triggered reset can't
    be synchronized to the real SPI transfer's own timing) rather than claiming byte-precision it
    can't deliver. Mock tier: not extended - no real reboot/timing concept exists there to race
    against.
  - **Repeated real WiFi flapping x concurrent bus load.**
    `tests/test_digital_twin_bus_hazard_concurrency.py::
    test_wozi_survives_concurrent_bus_load_and_a_real_established_wifi_disconnect` (twin tier) - a
    single real established-connection disconnect, not repeated flapping (a real finding: this
    tier can't fast-forward `_on_sta_disconnected()`'s own genuine 60s `asyncio.sleep()`, so
    repeating that isn't a reasonable CI-time proof here); extends the mock-tier-only wifi_mode_lock
    proof through the real, fully-wired task graph + real bus contention.
    `tests_hardware/bench/test_bus_concurrency_under_api_load.py::
    test_concurrent_get_sensors_under_real_multi_client_load_survives_repeated_real_wifi_flapping`
    (bench tier) - reuses `test_network_resilience.py`'s own proven-fast real 3x(3s/3s) flap
    technique concurrently with the file's own GET/PUT bus-load workers. Flash/mock: N/A (no real
    network primitive at either tier).
  - **NTP transient-outage retry x concurrent bus load.**
    `tests_hardware/bench/test_bus_concurrency_under_api_load.py::
    test_concurrent_get_sensors_under_real_multi_client_load_survives_an_ntp_transient_outage_and_retry`
    (bench tier) - `test_network_resilience.py`'s own `block_udp_ports([123])` transient-outage
    scenario running concurrently with the file's own bus-load workers. **Deliberately not
    extended to twin/mock tier in this pass** - no NTP-drop-and-retry scenario currently exists at
    either tier at all (unlike the wifi-flap case above, which had an existing mock-tier proof to
    extend); building one from scratch was judged lower priority than completing the full
    3x-rebuild/3x-full-suite verification this same request also asked for. Flagged, not silently
    skipped - a real, still-open opportunity if a future session has the time budget for it.
  All three device scripts/harness additions ran clean under real hardware where applicable (flash/
  bench); every mock/twin addition verified under the real MicroPython Unix-port interpreter;
  ruff/mypy clean throughout.
- **Two real findings from the first full-production 3x-rebuild/3x-full-suite verification pass
  (2026-09-04), both fixed.**
  - **`test_real_uf2_reflash_and_boot_smoke_test`'s own comment claimed "a plain bounded wait"
    between `board.enter_bootloader()` and the real `picotool load` call that was never actually
    implemented** - `picotool` was invoked with zero delay, racing the real USB BOOTSEL
    re-enumeration. Confirmed on real hardware: failed with picotool's own "No accessible RP-series
    devices in BOOTSEL mode were found" (exit 249), leaving the board stuck in BOOTSEL mode for
    every test after it in the same run (explaining a cascading, unrelated-looking
    `test_watchdog_starvation_triggers_a_real_hardware_reset` failure right after it - the board
    wasn't running normal firmware for that test's own `run_isolated()` to interrupt). Fixed with a
    bounded retry (5x, 2s apart) rather than one fixed guessed delay - real BOOTSEL enumeration
    timing varies by run. Re-verified clean: both tests pass, 26/26 real passes in the full flash
    suite.
  - **`pytest`'s own exit code can't distinguish "every expected test genuinely passed" from
    "hardware was unreachable and every fixture skipped cleanly"** - both exit 0.
    `scripts/run_flash_hardware_suite.sh`/`scripts/run_bench_hardware_suite.sh` now route through a
    new shared `scripts/_require_clean_hardware_run.sh`, which inspects the real pytest output and
    hard-fails on any unexpected skip (one currently-known, deliberate, permanent exception:
    `test_spoofed_off_subnet_source_address_is_ignored`, open question 8's own raw-socket-spoofing
    gap) or on zero real passes - not just a nonzero exit code. Caught for real during this same
    pass: a mass-skip (60/60) on a bench run that followed directly after the BOOTSEL-stuck board
    above, which the old bare-exit-code check had silently treated as a clean run.
  - **Fixed properly (2026-09-04, project owner's own explicit direction), not just documented as
    a footgun to remember to work around**: the single blanket `--run-long-soak`/`--long-soak-seconds`
    pair used to bundle three genuinely different things under one flag - a real, easy trap (its
    own help text already warned the rollover test's ~12.4-day wait ignores the duration value
    entirely, but nothing stopped it firing anyway). Replaced with: (1) `--soak-tier
    {short,mid,long}` (`tests_hardware/conftest.py`'s own `SOAK_TIER_SECONDS` = 60s/600s/6h) for the
    three real `@pytest.mark.long_soak` tests, always skipped unless passed; (2) a completely
    separate `@pytest.mark.multi_day_rollover` marker + `--allow-multi-day-rollover-wait` flag for
    `test_ticks_ms_real_2pow30_rollover` alone, structurally incapable of being bundled with a soak
    tier now; (3) a new dedicated `scripts/run_bench_soak_tests.sh --tier {short,mid,long}` wrapper
    - the only intended way to run soak tests at all, requiring the tier explicitly, never implicit
    or bundled into a general suite run; (4) `run_flash_hardware_suite.sh`/`run_bench_hardware_suite.sh`
    now always pass `-m "not long_soak and not multi_day_rollover"`, so neither category can run
    through those general wrappers even if a caller mistakenly passes one of the new flags to them.
- **Real finding, recovered: a missing `BENCH_AP_PASSWORD` cascades into ~25 real test failures,
  not just one clean skip (2026-09-04).** `test_hotspot_role_reversal.py`'s own
  `test_real_credentials_put_succeeds_and_confirms_accepted_values` (the one step that PUTs the
  real bench-bridge SSID/PW back to the DUT while it's still reachable, before stage 7's
  `leave_dut_hotspot_and_restore_bridge()`) skips cleanly when `BENCH_AP_PASSWORD` isn't set - by
  design, documented in its own skip message. What isn't obvious from reading that one test in
  isolation: without it, the DUT's persisted SSID stays `""` (cleared by stage 0's own
  `PUT /networking {"SSID": ""}`), so stage 7's flip-back can never succeed - not gracefully, and
  not even via its own documented `hard_reset()` fallback (a real reboot still reads the same
  cleared, persisted SSID and falls straight back into hotspot mode) - leaving the DUT
  unreachable over the bench bridge for every test that runs after it in the same session. Real
  observed cost this session: 33 passed, 25 failed, 1 error in one run, entirely attributable to
  this one missing env var. **Recovered directly via serial** (`mpremote run` against
  `config_manager.ConfigManager` writing `config_WIFI.cfg` directly, bypassing the network
  entirely, then a real `mpremote reset`) rather than waiting through more doomed network-based
  retries - confirmed reconnected (`Mode: STA, Connected: true`) within ~20s. **Standing rule for
  any future real bench session running `test_hotspot_role_reversal.py`: always set
  `BENCH_AP_PASSWORD` first** (`tests_hardware/README.md`'s own credential-handoff section already
  documents how to find/record it) - this is not optional/best-effort the way the test's own quiet
  skip message might suggest.
- **Real infrastructure bug, fixed: both memory-soak tests' own "unexpected reboot" detection was a
  near-guaranteed false positive.** `"CFGMGR_" in line` was meant as a one-time boot marker, but
  it's actually the module-tag prefix `PrintLogHistory` stamps on *every* log line from a given
  `ConfigManager`, including ordinary routine reads - confirmed directly against a real soak run's
  own log, where it fired dozens of times from SGP40's own periodic backup-period check
  (`"CFGMGR_SGP40 config_SGP40.cfg - Reading config data into list."`, once per read cycle), with
  no real reboot anywhere in that run. Fixed in both
  `tests_hardware/bench/test_memory_stress_bench.py` and `tests_hardware/flash/test_memory_stress.py`:
  now checks for `config_manager.py`'s own two genuinely one-time-per-`setup()` completion messages
  (`"...- config is ready."`) instead.
- **Open, flagged, not chased further given the time already spent on this pass**: the very first
  real `--soak-tier short` run (before the reboot-detection fix above) also showed one real device-
  side traceback at boot - `AttributeError: 'NoneType' object has no attribute '__aexit__'` in
  `asy_sgp40_driver.py`'s `_store_sgp()` calling `base_classes.py`'s `_set_meas_data()`
  (`async with self._datalock:`) - the task supervisor caught and restarted the task cleanly
  (`"Task ended - attempting restart, error counter increased to 100"`), and the system ran
  normally for the rest of that whole session afterward. **Real doubt this reflects the current
  code, not chased to a conclusion**: the reported line numbers (`_store_sgp` at line 224,
  `_set_meas_data` at line 159) don't match the current `src/` checkout at all (349 and 211
  respectively as of `c177608`, and `self._datalock = asyncio.Lock()` is set unconditionally,
  synchronously, in `SensorReader.__init__()` - there's no code path where it should ever be
  `None`) - strong circumstantial evidence the DUT was still running an earlier-flashed firmware
  image at that exact moment, not this session's own latest reflash. Worth a real, dedicated
  investigation (reproduce cleanly against a freshly-confirmed-current flash, or drop it if it
  never recurs) before treating it as either a real bug or a non-issue.
- **Real finding, fully investigated and root-caused (2026-09-04): a real, easily-reproducible
  `MemoryError` under sustained real concurrent HTTP load - not a leak, already gracefully handled
  by the existing architecture, but real evidence worth folding into open question 7's own
  `max_connections` decision.** Confirmed reproducible in well under 10 minutes of concentrated
  real load (5+ concurrent HTTP client threads hammering `/measurements`/`/sensors`/`/status`/
  `/networking` plus a periodic `PUT /sensors SGPResetVOC` every 3s) - dozens of real, distinct
  `MemoryError` tracebacks (4KB-5.7KB range) over a 6.5-minute window, first one within 45 seconds.
  **Root cause, pinpointed exactly**: `microdot.py:1492` (`dispatch_request`) ->
  `microdot.py:589` (`Response.__init__`) - vendored, hands-off third-party code (CLAUDE.md's own
  "don't restyle" rule) building a real per-request response buffer, occasionally landing in one of
  the heap's own natural low points under real concurrent load.
  **Confirmed NOT a leak** - a temporary, investigation-only `gc.mem_free()` trace (piggybacked on
  `system_service.py`'s existing 1Hz uptime tick, reverted immediately after - `git diff` confirmed
  clean, never committed) showed a classic sawtooth pattern (troughs as low as ~2.8KB, peaks over
  110KB) with **no monotonic downward drift** across the full 6.5-minute heavy-load window - the
  late-window peaks (113KB, 115KB) were as good as or better than the early ones. MicroPython's own
  threshold-based incremental GC, under genuine sustained concurrent allocation pressure, produces
  real troughs low enough that a single ~5KB response-buffer allocation can occasionally lose the
  race and fail - a genuine, reproducible headroom/GC-timing sensitivity under concurrent load, not
  a reference leak.
  **Already gracefully handled, confirmed directly, not assumed**: every occurrence was caught by
  this project's own existing blanket exception handling (`"WEBSERVER Unhandled exception in route
  handler:"`, matching SPECIFICATION.md Part A.5's already-documented Microdot exception-catch
  architecture) - the one affected request fails cleanly (shaped 500), logged, and the system keeps
  running normally; no crash, no reboot, no corruption, confirmed by the same MEMTRACE run showing
  healthy oscillation the whole time with zero real reboots.
  **Real, actionable input for open question 7 ("should `max_connections=4` be raised?")**: this is
  new, concrete evidence *against* raising it without also addressing headroom - more concurrent
  connections means more simultaneous response-buffer allocations landing in the same heap, which
  would only make these troughs deeper/more frequent. Not acted on here (that's the project owner's
  own call, same as the rest of open question 7) - recorded as real, first-hand data for that
  decision, not a recommendation.
  **Threshold tuning: real evidence gathered, decision explicitly NOT made yet (2026-09-04, same
  investigation, project owner's own call - do not treat as settled).** A proactive
  `gc.threshold(N)` (MicroPython's default on this hardware is `-1`, proactive collection disabled -
  confirmed directly, so the allocator only ever collected reactively, after an allocation had
  already failed) is the candidate fix, with no vendored-code change needed - `16384` was validated
  directly on real hardware to eliminate the reproduction entirely (the same concurrent-load run that
  produced dozens of real `MemoryError`s in 6.5 minutes, first at 45s, produced zero, free-memory
  floor rising from ~2.8KB to ~123.7KB). **Real root-cause corroboration found while re-checking this
  work**: `/status` (`asy_webserver_service.py`'s `_get_status()`, the only route that aggregates
  every module's settings/status/error-log into one `json.dumps()` call) measured at 5711 bytes on
  real hardware - matching the top of the documented "4KB-5.7KB" `MemoryError` traceback size range
  almost exactly, versus every other route under 350 bytes. Strong circumstantial confirmation `/status`
  specifically is the failure site, and that shrinking/streaming that one response (untried) is a real,
  separate mitigation worth considering alongside any threshold choice.
  **A same-day direct A/B against `65536` was also run** (both realistic 1-3req/s and aggressive-hammer
  load): both values produced zero `MemoryError`s/reboots, but `65536` showed a lower free-memory floor
  under hammer load (~61.3KB vs. `16384`'s ~123.7KB) - mechanically expected, since a bigger threshold
  waits for more new garbage before collecting again (fewer, later, deeper collections), not more
  headroom. **However, the apparent "~once/sec" collection frequency and any conclusion about CPU-time
  cost from this A/B are NOT reliable** - project owner caught this directly: the only instrumentation
  used was a `gc.mem_free()` trace piggybacked on `system_service.py`'s existing 1Hz `status_counter()`
  tick, which cannot distinguish "collections really run once/sec" from "they run more often, this just
  only sampled once/sec." **No threshold value is decided. Nothing has been committed.** Real
  MicroPython GC internals were confirmed directly against the pinned `micropython/py/gc.c` source: an
  automatic collect-and-retry-once already happens before a real `MemoryError` is ever raised, but the
  allocator needs one *contiguous* free run of blocks and the collector is non-compacting, so a heap can
  have plenty of total free bytes yet still fail one large single allocation if it's fragmented into
  scattered smaller gaps - this is why this specific allocation site was disproportionately vulnerable
  versus the many small allocations elsewhere in the system.
  **Real, verified-in-source alternative mitigation found (2026-09-05): Microdot supports streaming
  response bodies from a generator.** Confirmed directly against `ext/microdot.py`: `Response.write()`/
  `body_iter()` (lines 665-759) iterate any body object exposing `__next__` (sync generator) or
  `__anext__` (async generator) and `await stream.awrite()` each yielded chunk to the socket
  immediately, never assembling the full body into one buffer first - unlike the `dict`/`list` path
  (`Response.__init__`, line 588), which is the one `json.dumps()` call actually responsible for
  today's single ~5.7KB contiguous allocation. Streaming `/status` would need its own hand-written
  generator yielding valid JSON fragments (the `dict`/`list` auto-encode branch doesn't apply to
  generators) and an explicit `Content-Type` header (also not auto-set for a generator body) - real,
  fiddly application code, not a config flag. No `Content-Length` concern: this vendored Microdot
  speaks plain `HTTP/1.0` with no keep-alive handling anywhere (confirmed via grep), so every
  connection closes after one response and a client reading until connection-close is correct,
  standard behavior. Reduces the *demand side* of the problem (shrinks the largest single contiguous
  allocation any route ever needs, down from ~5.7KB to roughly one field's worth) rather than the
  *supply side* (`gc.threshold()`'s collection proactiveness) - complementary to a threshold choice,
  not a replacement for it, but worth testing on its own to see whether it resolves the reproduction
  even independent of any `gc.threshold()` change.
  **Agreed plan for the next session** (updated 2026-09-05): (1) build real sub-second-resolution
  instrumentation (a dedicated polling task, not piggybacked on the 1Hz uptime tick - MicroPython's GC
  has no refcounting, so any `gc.mem_free()` increase between two closely-spaced samples is
  unambiguous proof a real collection just fired) and re-measure the threshold candidates under both
  realistic and hammer load with real frequency/CPU-time numbers, storing the results for a joint
  decision rather than deciding unilaterally; (2) build JSON streaming for `/status` specifically (it's
  already assembled from several independent per-module sources in `_get_status()`, a natural fit for
  yielding one source at a time); (3) test whether streaming alone resolves the real-hardware
  reproduction, even with no `gc.threshold()` change at all; (4) decide the actual fix - some
  `gc.threshold()` value, the streaming change, or both - based on steps 1 and 3's real results
  together, not before; (5) once a build is decided and committed, run the real-hardware bench suite;
  (6) if that passes, run the full test suite three times. Steps 1 and 4-6 need real hardware and the
  project owner's own go-ahead in-session before starting; not started yet.

  **Step (3) done (2026-09-05, real bench hardware, project owner's go-ahead given in-session):
  streaming alone does NOT resolve the reproduction - a real MemoryError still occurs, `gc.threshold()`
  left untouched at its default -1.** Freshly built+flashed `dev` firmware (this session's own step-2
  commit) onto the bench Pi4's board, then ran the same methodology as the original 2026-09-04
  investigation (5 concurrent HTTP client threads hammering `/measurements`/`/sensors`/`/status`/
  `/networking` as fast as possible, plus a `PUT /sensors {"SGP40":{"SGPResetVOC":true}}` every 3s)
  for 10 minutes, passively `tail_log()`-ing the real serial output throughout. **237 real
  `MemoryError` tracebacks** over the 10-minute window, first within seconds - not eliminated, though
  the traceback location moved: every one now points at `asy_webserver_service.py`'s own
  `_build_status_pieces()` (line numbers in the on-device traceback are offset from `src/`'s own
  line numbers by `scripts/build_firmware.py`'s `if TYPE_CHECKING:`-stripping stage - resolved by
  re-running the same strip locally and confirming the offset, not a sign of stale firmware),
  allocating ~4912-4926 bytes each time - specifically at the line joining every registered module's
  `errcount` entry into one string (`pieces.append(',"errcount":{' + ','.join(errcount_parts) + '}}')`).
  **Root cause of why this specific piece is still ~5KB**: this step's own design assumption
  ("`sensors`/`errcount` bounded by this codebase's small, fixed module/sensor count") didn't account
  for how many modules are *actually* registered on real hardware - 17 (`NEOPIXEL`, `CFGMGR_NOTIFY`,
  `CFGMGR_SGP40`, `CFGMGR_WIFI`, `CFGMGR_SYSTEM`, `SYSTEM`, `BMP3XX`, `NTP`, `DNSSRV`, `FRAM`,
  `CFGMGR_BMP3XX`, `SGP40`, `CFGMGR_NTP`, `WIFI`, `NOTIFY`, `SCD30`, `WEBSERVER`), each with its own
  up-to-10-entry error history - so the single joined `errcount` piece ends up almost exactly as large
  as the *entire* old pre-streaming aggregate (~5.7KB), defeating the mitigation's whole point for
  that one piece. Every occurrence was caught cleanly by the existing `app.errorhandler(Exception)`
  catch-all (`"WEBSERVER Unhandled exception in route handler:"`, errno=4) - no crash from the
  MemoryError itself, request failed with a clean 500, system kept running.

  **Fixed and confirmed on real hardware (2026-09-05): `_coalesce_json_fragments()`
  + `_append_coalesced_object()` replace the plain `",".join()` for both `"sensors"` and `"errcount"`.**
  Splitting one piece per module (matching the real module count, ~17-22 total transmitted pieces)
  was considered and rejected: that would land close to the ~20-piece count already measured (this
  same investigation, step 2) to cause a real +53% throughput regression via `_serve()`'s per-write
  `asyncio.wait_for()` wrapping. Instead, fragments are batched by a fixed byte budget
  (`_MAX_STATUS_PIECE_BYTES = 1024`) rather than by module count: each transmitted piece stays well
  under any size ever observed to fail, *and* the piece count stays low regardless of how many
  modules are ever registered (batches, not one-per-module). `_append_coalesced_object()` additionally
  fuses the section's own `{`/`}` onto the first/last batch rather than adding them as their own
  pieces, so the common case (a section small enough to fit in one batch - true for every registration
  size this project runs today except the real `errcount` section specifically) stays at exactly the
  same one-piece-per-section shape as the original step-2 design; `test_asy_webserver_service.py`'s
  existing `len(chunks) == 5` assertion still holds unchanged for that reason. New coverage added:
  `test_h2_stream_many_error_sources_are_coalesced_into_size_bounded_batches_not_one_growing_blob`
  (20 synthetic modules with realistic-sized histories, asserts every piece stays under 1.2KB and the
  full document still parses correctly). Local verification only so far: full `scripts/test.sh` clean
  (0 FAIL), and `tests/test_digital_twin_run_wozi_integration.py`'s real-socket soak timing re-measured
  at ~45.3s (vs. the already-validated 5-piece baseline's 42.7s - a ~6% difference, not the ~53%
  regression over-fragmentation previously caused) - the real module-count-scale registration this
  soak drives via the real `sensortask_wozi.build_system()` graph, not just the synthetic unit test.
  **Real-hardware re-run confirms the fix (2026-09-05, same bench Pi4, project owner's go-ahead given
  in-session): 0 MemoryErrors, 0 tracebacks, 0 reboots over the same 10-minute hammer load that
  previously produced 237 real MemoryErrors.** Fresh `dev` build+flash from this fix's own commit,
  same stale-AP-station-table workaround as before (`kick_all_stations()` before the post-flash
  reconnect), same methodology (5 concurrent threads hammering `/measurements`/`/sensors`/`/status`/
  `/networking` plus `PUT /sensors SGPResetVOC` every 3s, 10 minutes, passive `tail_log()` throughout).
  `SysUptime` climbed monotonically through 799s with zero crash/reboot markers the whole time (an
  extra ~90s watched past the hammer's own end, specifically to also re-check the second finding
  below). `GET /status` continued parsing as one complete, valid JSON document throughout and
  afterward, confirmed against the real 17-module registration count on this hardware. Board restored
  to a clean, bench-network-connected, error-counters-reset state before finishing.
  **One new, separate, minor observation from this same run, not chased further**: `CFGMGR_SGP40`
  logged 84 errno=8 entries (`config_manager.py`'s `get_dict()`: "unknown key, or a non-iterable/
  malformed keys param") during the load - plausibly related to the concurrent `SGPResetVOC` PUTs
  racing a GET, but not investigated; flagging rather than silently letting it pass unremarked.
  **The second finding from the prior run (a real hardware watchdog reset, `machine.reset_cause() ==
  machine.WDT_RESET`, observed a few minutes after that run's own hammer load ended) did NOT recur in
  this run's ~90s post-hammer observation window** - consistent with (but not proof of) that reset
  being a one-off from the prior run's own conditions rather than a deterministic consequence of this
  hammer pattern; still not root-caused, still worth a dedicated look if it recurs.
  **Second, separate real finding from the same run, root cause not yet determined**: sometime after
  the 10-minute hammer load itself ended (system healthy throughout, uptime monotonically reached 740
  with zero reboot markers by the end of continuous log capture), a real hardware watchdog reset fired
  (`machine.reset_cause() == machine.WDT_RESET`, confirmed directly after the fact) - the board came
  back up in hotspot mode with `SysUptime` reset to ~110s. Not conflated with the MemoryError finding
  above (the webserver's own per-connection `MemoryError`s are already caught inside `_serve()` and
  never escape to crash the supervised task), but a real, un-investigated regression risk worth
  chasing: whether this specific un-throttled, max-speed 5-thread-plus-command flood (a harsher
  pattern than the original investigation's own client mix, not yet compared side by side) is
  sufficient on its own to occasionally starve the event loop past the documented 8388ms WDT-feed cap,
  or whether something else is responsible. Board was restored to a clean, bench-network-connected
  state (stale AP station table entry cleared, hard-reset, error counters reset) before finishing.

  **Step (2) done (2026-09-05), software-only, no real hardware touched.** `_get_status()`/
  `_build_status_pieces()` in `asy_webserver_service.py` now build a plain `list[str]` of small,
  already-`json.dumps()`-encoded fragments - one per top-level section (`networking`/`system`/
  `notification`/`sensors`/`errcount`) - instead of one dict handed to a single `json.dumps()` call.
  Handed to Microdot as `Response(iter(pieces), headers={...})` with an explicit `Content-Length`
  (computed once every fragment is known, not left to `Response.complete()`'s bytes-only default).
  Bounds the largest single allocation this route ever makes to one section's own payload (bounded by
  this codebase's small, fixed module/sensor count) instead of the whole ~5.7KB aggregate. Two real
  findings from building this, both now documented in SPECIFICATION.md Part F.1:
  - **MicroPython's `async def ... yield` "async generator" is broken, not just absent.** It parses,
    but produces a runtime object typed `'generator'` with `__next__` but no `__aiter__`/`__anext__`
    at all (confirmed against the pinned interpreter directly, and against its own docs - PEP 525 is
    listed with an empty "Complete" column). `ext/microdot.py`'s `body_iter()` falls back to driving
    such an object via plain synchronous `next()`, which **segfaults the interpreter** the moment
    execution resumes past a real `await` inside it. Ruled out entirely for this reason, not by
    preference - every source is instead awaited up front (still inside a real coroutine) into a
    plain list, which Microdot then drives as an ordinary `list_iterator` with no `await` anywhere
    inside it.
  - **Fragmenting the response too finely regresses throughput, independent of memory safety.**
    `WebserverService._serve()` wraps every single stream write in its own `asyncio.wait_for()`
    (`_TimeoutStreamProxy`, the existing per-call-timeout hardening). An earlier attempt yielding one
    piece per punctuation character (~20 pieces for a typical `/status` body) measured a real 42.7s to
    65.2s (+53%) wall-clock regression on `tests/test_digital_twin_run_wozi_integration.py`'s fixed
    soak workload, confirmed against an unmodified baseline via `git stash`. Coalescing to 5 pieces
    (one per top-level key, built with ordinary string concatenation bounded to that one section)
    restored baseline timing while keeping the same memory-safety property intact.
  Confirmed memory-safe as designed, not just in effect: a MicroPython `list`'s own backing array
  (`py/objlist.c`/`py/objlist.h`) is one small allocation sized by *element count*, not content size;
  each string's own data buffer (`py/objstr.h`) is a separate, independently-sized allocation. A short
  list of independently-sized JSON fragments therefore never needs one large contiguous block itself.
  Full local verification: `scripts/lint.sh`/`scripts/typecheck.sh` clean, `scripts/test.sh` (real
  MicroPython Unix-port interpreter plus `uv run pytest tests_scripts`) clean, 0 `FAIL` lines. No real
  hardware was touched for this step.
  **Not fixed, deliberately**: the actual allocation site is inside vendored `ext/microdot.py`
  (pinned `v2.6.2`, hands-off per CLAUDE.md's own rule) - not something to patch directly. No `src/`
  change was made; the temporary trace instrumentation was fully reverted (`git diff` clean) and the
  board reflashed back to the exact, unmodified production firmware before this investigation
  concluded.
