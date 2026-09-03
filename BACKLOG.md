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
- **FRAM bus-recovery is only partially wired up.** `asy_fram_driver.py`'s own `src/` promotion
  added device-identification/write-protect verification, but there's still no periodic/triggered
  re-probe policy — `verify_present()` and `set_write_protected()` have zero callers anywhere;
  `get_write_protected()` has exactly one, `_write()`'s own write-protection gate, which isn't a
  re-probe of anything — and no task supervisor for FRAM specifically. Whoever wires this up must wrap
  the calls in the same `try/except Exception` discipline this file's other methods already use —
  `asy_fram_driver.py` doesn't catch its own inherited `RuntimeError` path on these three itself.
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
   `tests_hardware/` (flash/bench automated `pytest` tests, from `HARDWARE_TEST_PLAN.md`'s
   mock/twin/flash/bench/manual backend design) closes this gap in code. **Real-hardware execution
   is now in progress** on the bench Pi4 — see `REAL_HARDWARE_RUN_LOG.md` (repo root, temporary) for
   current status and `tests_hardware/README.md` for how to run it.

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
6. **Should `asy_wifi_service.py` gain an independent WiFi reachability check?** Confirmed on real
   hardware (`tests_hardware/README.md`'s "Known assumptions and open findings"): the CYW43
   firmware/lwIP stack can silently mask a real link disruption from `wlan.isconnected()`/
   `wlan.status()` entirely — a real `arping` probe got zero responses from the DUT while
   `iw station dump` showed it continuously "associated: yes" for hundreds of seconds spanning a
   whole AP outage. This is a well-documented, long-standing upstream MicroPython characteristic
   (`micropython/micropython#9455`/`#9505`/`#18797`, open since v1.19.1/2022), not project-specific.
   `_wlan_isconnected_or_false()` is a bare pass-through to `wlan.isconnected()` with no independent
   check, so `_on_sta_disconnected()`'s retry logic structurally cannot fire if the firmware never
   reports the disconnect. **Not decided**: whether to add one (e.g. a periodic ping/HTTP
   self-check) beyond trusting `isconnected()` alone. Mitigated at the test-harness level only for
   now (`bench/test_network_resilience.py`'s outage/flap tests recover via a real `hard_reset()` if
   the graceful wait times out, but still re-raise so the real limitation stays visible as a test
   failure).
7. **Real-hardware verification of the captive-portal hotspot redirect, and of
   `scripts/build_firmware.py`'s frozen autostart chain against the dev bench — both still
   genuinely untested, not confirmed bugs (2026-09-03 cleanup).** An earlier investigation flashed
   `scripts/build_firmware.py wozi` (wozi's own hardcoded pins and full feature set, including
   `frozen_html`/`static_mount`) onto the dev bench's differently-wired hardware and treated the
   resulting oddities as open bugs: a 404 instead of the expected 302 on `GET /generate_204`, and a
   real `errno=11` I2C read failure on the shared i2c1 bus. Neither was a valid test of anything —
   wozi's own build has no business running on the dev bench at all, since its pin assignments and
   feature set target different hardware, and no `--device dev`/per-variant equivalent exists yet
   (see "per-variant `sensortask-*.py` generator" below — the real gap this stood in for). Both
   findings are dropped as noise from that mismatch, not tracked as bugs to chase; don't re-run
   `scripts/build_firmware.py wozi` against the dev bench expecting a meaningful result until that
   generator exists.

   What's still a genuine, unaffected gap: **the captive-portal redirect has never been verified on
   real hardware under a valid configuration.** The one dev-native path that does run cleanly
   (`dev_legacy/README.md`'s mounted-entry-script recipe) never wires up `frozen_html`/`static_mount`
   at all, so it doesn't exercise this code path either — the gap isn't "confirmed broken on
   hardware," it's "never actually run on hardware, full stop." `src/`'s own logic is already proven
   correct end-to-end against the real MicroPython Unix-port interpreter
   (`tests/test_digital_twin_sensortask_integration.py::test_wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server_and_status_led`,
   11/11 passing, including a real `_PHASE_HOTSPOT` transition and a real `302`/`Location: /`), so
   this isn't a `src/` question — it's specifically about real rp2/lwIP sockets and real Microdot
   request handling, which no amount of Unix-port testing substitutes for. Closing it needs
   extending the dev bench's own entry script (embedded in `dev_legacy/README.md`) with
   `frozen_html`/`static_mount` so hotspot-mode redirect can be validated on the dev bench — per
   CLAUDE.md's hard rule, a passing dev-bench result is treated as valid for wozi too, so this is a
   real, complete next step on hardware that's actually available today, not a placeholder pending a
   wozi board that will never exist.

## Deferred / explicitly out-of-scope work

- **`env --tier flash`/`--tier bench` real-hardware verification — not yet done.**
  `toolchain/setup_toolchain.py env` (SPECIFICATION.md Part B.12) folds Generic/Flash/Bench dev-
  environment setup into one tiered command. `generic` was verified fully end-to-end in a cloud
  sandbox (real `uv sync`/`npm ci`/toolchain build); the USB/network *detection* logic was also
  exercised for real where safe (empty-`/sys` USB scan, a real `iproute2` apt-install-and-parse).
  Not yet exercised for real: `flash` against an actual RP2040 board, and `bench` actually creating
  the NetworkManager bridge/AP (deliberately not installed/enabled in the shared cloud sandbox this
  was built in, to avoid disrupting that container's own networking). Next step: run both tiers for
  real on the bench Rpi4, the same dedicated-session pattern used for the earlier `build_firmware.py`
  autolaunch verification (see this branch's own commit history).
- **Real-hardware re-test of the segfault fix and the memory-leak soak test (owner's standing
  future plan, not yet actionable)** — the project owner has real future plans to run tests directly
  on the actual rp2040 target hardware. Once that's possible, repeat both Unix-port soak tests
  there:
  - The **segfault stress test** (`digital_twin/segfault_stress_repro.py`'s repeated-concurrent-
    client-burst scenario) — not because the root cause is in doubt (a dangling-pointer bug in
    `extmod/modselect.c`, confirmed compiled out of real rp2 firmware via
    `MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` and fixed on the Unix port by
    `digital_twin/unix_port_poll_prewarm.py` — see `digital_twin/README.md`'s "What's here" for the
    fix and BACKLOG.md's own git history for the investigation), but as standing on-target
    validation practice for the wider stress scenario itself.
  - The **memory-leak soak test** (a long-running `gc.mem_free()` recovery-peak trend measurement
    against the real assembled system under HTTP soak traffic) — not because the "no confirmed leak
    on the Unix port" conclusion is in doubt (four independent, properly-powered replication
    experiments found no reproducible decline, on either idle or HTTP-soak traffic), but because the
    Unix port's allocator/heap behavior isn't guaranteed identical to rp2040's real one, so an
    independent on-target confirmation is worthwhile.
  Neither soak-test script currently has a real-hardware-runnable form (both assume the Unix-port
  `digital_twin` harness); porting/adapting them for actual on-device execution is part of this
  future work, not already done.
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
- **Per-variant `sensortask-*.py` generator — not yet built.** SPECIFICATION.md Part A.3 already
  names this as a real planned direction (one setup-definition file → every variant's
  `sensortask-*.py`/website pair), shaped for by A.8's registration-API/A.9's `HTML_SRC_DIRS`
  mechanisms; `src/sensortask_wozi.py` today only covers the "wozi" variant, hand-written with its
  own fixed sensor set (SCD30 + BMP3xx + SGP40, all FRAM-backed) assumed present unconditionally.
  Two concrete requirements for whenever this generator is actually built, so they aren't lost
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
  unconditionally. **This is also the real blocker for using `scripts/build_firmware.py` on the dev
  bench at all**: with only the `wozi` variant hardcoded, an earlier session tried to work around
  the gap by scratch-patching `src/sensortask_wozi.py`'s pin numbers and flashing that through
  `scripts/build_firmware.py`'s own autostart chain — a mixed, neither-wozi-nor-dev configuration
  that produced noise mistaken for real bugs (open questions list, item 7, before this cleanup).
  Until this generator exists, don't flash `scripts/build_firmware.py wozi` (or a hand-patched copy
  of it) onto the dev bench expecting a meaningful result — `dev_legacy/README.md`'s own
  mounted-entry-script recipe is the only currently-valid way to run the real, wired-together system
  on that hardware.
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
- **Network fault injection against the real dev bench unit (nftables/`tc netem` on the host
  Rpi4's bridge) — not yet built.** `dev_legacy/README.md`'s "WiFi/NTP/DNS integration testing"
  section documents the bridge (`br0` = `eth0` + a hosted `wlan0` AP) the physical RP2040 bench
  unit connects through for real WiFi/NTP/DNS testing; the natural next step is scripting
  packet-loss/latency/DNS-blackhole fault injection on that same bridge (`tc netem` for loss/delay,
  `nftables` for selective drops, e.g. NTP-only or DNS-only outages) to exercise
  `asy_wifi_service.py`/`asy_ntp_client.py`/`asy_dns_client.py`'s own retry/give-up/hotspot-fallback
  paths against real, not simulated, network failure — the digital twin's own fault injection
  (`--fault`/`--hang` in `digital_twin/launch.py`/`run_wozi_integration.py`) only ever faults the
  I2C/SPI/FRAM bus layer, never the network layer. No script or recipe exists for this yet.
