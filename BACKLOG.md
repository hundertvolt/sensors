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
  this in next time `pyproject.toml` is touched for another reason anyway (same framing as the
  already-tracked `improved-quality/microdot.py` exclude-entry cleanup below).
- **Bare `except:` is forbidden in refactored code** (`except Exception:` or narrower required).
  Ruff's E722 is already enabled, so existing bare excepts in `improved-quality/` show as tracked
  findings rather than being silenced — eliminating them is still real refactor work.
- **No CI firmware-build stage yet.** `build-*.sh`'s hardcoded `/home/nico/rpi_pico/...` path is
  fixed (each script now captures its own `$(pwd)` before any `cd`, matching how the script has
  always assumed it's invoked - from inside `py-include/`, real dir or symlink, regardless of
  machine - and passes that as `FROZEN_MANIFEST`; verified with a real end-to-end
  `build-wozi.sh` run producing a successful `firmware.elf` link against the pinned v1.28.0
  toolchain). Still open: wiring an actual firmware-build stage into CI itself.
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
- **Every deliberate system reset (reboot, bootloader entry, or a deliberate watchdog-starve
  give-up) must pause FRAM operations first and give it a brief wait before the reset actually
  happens** — a real risk (mid-write/mid-read power loss, MB85RS64V reads are destructively
  read internally per `SPECIFICATION.md` Part A.4) that a reset triggered while a FRAM transaction is
  in flight could corrupt data, same class of concern as the dual-copy/status-byte design
  `asy_fram_manager.py` already guards against for power loss but not specifically for a
  self-triggered reset racing an in-progress transaction. Owner-flagged as important for the final
  wiring-up of this refactor's task/reset plumbing, likely needing rework across several files, not
  just one. **Current state, confirmed by reading `system_service.py` directly**: `_reboot()`
  (backing both `reboot_system()`/`reboot_bootloader()`) already calls `self.storage_pause(True)`
  before arming the `_RESET_DELAY`-second (4s) delayed reset timer, and already does so before the
  `_force_watchdog_starve` fallback too (armed when the reset timer itself can't be allocated) - so
  the one existing deliberate-reset path already pauses-then-waits. Confirmed via grep that
  `machine.reset()`/`machine.bootloader()`/`WDT()` have no other call site anywhere in `src/` or
  `improved-quality/` today. **Both open sub-items closed**: (1) margin is sufficient - the FRAM
  bus runs at 1MHz (`asy_spi_driver.py`'s default `baudrate`) over a `max_size=0x2000` (8KB) chip,
  and no single chunk approaches that whole size (individual chunks are tens of bytes), so even a
  two-block write plus CRC-verify readback completes in low single-digit milliseconds - three
  orders of magnitude under both the deliberate 4s `_RESET_DELAY` and the worst-case ~8s
  watchdog-starve wait; a genuinely wedged bus is the separate, already-accepted "hardware
  watchdog is the backstop" case (CLAUDE.md). (2) the invariant is now actively enforced, not just
  true by chance: `tests/test_reset_call_site_invariant.py` scans every `src/*.py` file and fails
  if `machine.reset()`/`machine.bootloader()` appear anywhere but `system_service.py`, or `WDT()`
  anywhere but `sensortask_wozi.py`.
- **No standardized timeout/cancellation mechanism yet for blocking calls that genuinely can be
  timeout-wrapped** (FRAM SPI transactions, `src/asy_udp_socket.py`'s own `select.poll`-driven
  `ready()`/`write_and_recvfrom()` — anything that isn't a raw blocking `machine.I2C` call
  mid-transaction, which can't be interrupted regardless; see CLAUDE.md's "wedged I2C bus" hard
  rule for why that case is different and already decided, and why `socket.getaddrinfo()` turned
  out to belong in the *can't* bucket instead and is gone from this codebase entirely now). Each
  remaining call currently uses its own bespoke approach rather than one consistent mechanism
  applied everywhere.
- **Bus concurrency (`asyncio.Lock` + `async with`) coverage audit — closed, no gaps found.** Every
  `*_DeviceSession(Lockable)` driver in `src/` (SCD30/BMP3xx/SGP40/I2CDevice, plus FRAM's
  structurally identical `_op_lock`) was audited for re-entrant acquisition, exception-safety on
  release, starvation, and cross-lock ordering: no method re-acquires an already-held lock,
  `Lockable.__aexit__` always releases (try/except around `.release()`, never suppresses the
  original exception), every extended hold is a bounded, protocol-justified delay, and every call
  site acquires the per-sensor session lock before the shared bus lock, never the reverse. No code
  changes needed.
- **Common driver error classes across sensors — future direction, not designed or implemented
  yet.** Each driver currently defines and reports its own `errno`/`wrnno` values independently
  (see `SPECIFICATION.md` Part C.7); the one exception is `errno=10` ("initial setup failed"), which
  all three drivers already use for the same situation by independent convergence rather than by
  any enforced scheme. Project owner's stated direction: keep per-driver definition/reporting (not
  a single shared enum), but predefine a small set of common error *classes* so the same number
  means the same or an equivalent condition across different drivers, beyond just the one
  already-consistent case. No scheme (numbering ranges, category list, how a driver opts in)
  designed yet.
- **The task-supervisor error-budget counter** is behaviorally correct and intentional as designed,
  but flagged by the owner as implementable more efficiently — worth a cleaner implementation in
  the refactor without changing observed behavior. (Neopixel warning-flash sequencing was the other
  half of this item - resolved by the `src/asy_neopixel_driver.py`/`src/asy_notification_service.py`
  promotion, see `SPECIFICATION.md` Part A.4.)
- **Bus-layer status has no dedicated REST endpoint or field yet.** `asy_i2c_driver.py`/
  `asy_spi_driver.py` deliberately have no logger of their own today (see `SPECIFICATION.md` Part
  C.7.1's table) — the natural REST shape once each bus instance gets its own logger name
  (`"I2C0"`/`"I2C1"`/`"SPI0"`) would be one endpoint with one field per bus instance, mirroring
  `/status`'s existing `errcount` aggregation (`SPECIFICATION.md` Part A.8). Not designed or
  implemented yet.
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
   MicroPython Unix port's socket implementation, not real rp2/lwIP — no rp2 hardware was available
   to test against. If a deployed unit ever shows UDP behavior diverging from what's
   tested/documented in the driver, this is the first place to look. **Explicitly deferred by the
   project owner**: on-device verification is real future work, not something to chase in the
   current session.
   **Sharper root cause confirmed (Step 5 re-audit session)**: this isn't just an abstract
   "untested on real silicon" gap — it's now confirmed structural. A real, standalone reproduction
   (a fresh `AsyUDPSocket("127.0.0.1", 123)` client against a real local UDP responder, and the raw
   `socket.socket().connect()` call underneath it) showed the MicroPython Unix port's "standard"
   build's `connect()`/`bind()`/`sendto()` reject a plain `(host: str, port: int)` tuple outright
   with `TypeError: object with buffer protocol required` — a known, long-standing Unix-port-only
   quirk (`micropython/micropython#6924`) that `tests/test_asy_udp_socket.py` already found and
   works around in its own test helpers (`make_addr()`/`resolve_addr()`, which pre-resolve via
   `socket.getaddrinfo()` before ever constructing an `AsyUDPSocket`). The real production call
   sites — `asy_ntp_client.py`'s `_fetch_ntp_reply()`, `asy_dns_client.py`'s `resolve_ipv4()`,
   `captive_dns.py`'s own `AsyUDPSocket(("0.0.0.0", 53), ...)` — never do this pre-resolution; they
   pass a plain tuple straight through, exactly matching `typings/socket.pyi`'s real-rp2-hardware
   `_Address` contract (`tuple[str, int] | ...`), which is correct and required for real hardware.
   Net effect: `_connect()`'s own broad `except (OSError, MemoryError, TypeError)` silently swallows
   this `TypeError` as an ordinary "peer unreachable" failure, so **under the Unix port specifically,
   every real NTP sync and every real DNS resolution attempt fails 100% of the time, unconditionally,
   regardless of network reachability** — confirmed directly by pointing a fully-connected,
   correctly-configured digital-twin run's `NTP_Host` at a real, working local UDP NTP responder on
   `127.0.0.1:123` (bypassing this sandbox's own separate outbound-network restriction entirely) and
   observing the sync attempt still fail with `NTP Invalid NTP time received!` every cycle, with zero
   packets ever reaching the responder. **Not a bug and not something to fix in `src/`**: this is
   exactly the class of thing CLAUDE.md's own "don't edit `src/` only to make the twin run" owner
   constraint rules out — the production code is already correct for the real target. It does mean
   the earlier "NTP round-trip couldn't be verified end-to-end because this sandbox's network policy
   blocks UDP/123" framing understated the gap: even a sandbox with full, unrestricted internet
   access could not have verified this code
   path under the Unix port either. Real rp2 hardware remains the only way to verify NTP/DNS's actual
   UDP transport — same conclusion this entry already reached, now reached from a direct
   reproduction instead of an absence of one.

## Deferred / explicitly out-of-scope work

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
- **`pyproject.toml`'s mypy `exclude` list still has a dead regex entry for
  `improved-quality/microdot.py`** (removed — see `SPECIFICATION.md` Part A.5), matching
  nothing today, harmless but worth deleting (along with its now-dangling "see its own module
  docstring" comment) next time `pyproject.toml` is touched for another reason — not urgent enough
  to be the sole reason to trigger CLAUDE.md's "Pre-push verification" chroot recipe on its own.
- **HTML/frontend redesign — confirmed genuine near-future target, not this pass.** Owner-confirmed
  out of scope here: the frontend work involves changes far larger than a field-name fix (a real
  redesign, not a patch), and the refactored side's own website is still deliberately just a
  placeholder stub (`SPECIFICATION.md` Part A.9) with no real content to wire up yet anyway. The
  concretely-stale symptom that prompted this entry — the legacy frontend still sending the
  pre-migration `setSGP`/`setBMP` field names/formats (see Part C.5.3's wire-format note) — is real
  but is pre-refactor debt on the currently-deployed frontend, not something the redesign needs to
  inherit; it'll be superseded outright once the real frontend for the refactored REST API is built,
  not fixed in place first.
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
- **`improved-quality/sensortask-wozi.py` has the same task/session-narrative-comment problem the
  rest of `src/` was already swept for** — pervasive dated migration-narrative comments, a
  TODO/stale-comment combo, one leftover `DRIVER_SPEC.md section 7` reference, and no module-level
  docstring (every `src/` file has one). Left untouched deliberately: out of scope under CLAUDE.md's
  hard rule on editing `improved-quality/` source without a scoped, owner-authorized exception, and
  explicitly deferred by the owner to its own future session rather than bundled into this one.
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
  done - `improved-quality/sensortask-wozi.py` still calls `conn.network_available` by its current
  name, and renaming would break that WIP file without the scoped exception CLAUDE.md's hard rule
  requires for editing it. Instead, a prominent comment now sits directly above the first
  self-checking getter, explicitly cross-referencing `network_available()` and naming the
  convention a new getter must pick deliberately.
- **`config_manager.py`'s three defensive `TypeError`/`AttributeError` catches** (non-string
  filename, non-iterable `keys`, non-dict `data` passed to `write_config()`) — **re-investigated now
  that the Microdot REST layer exists**: they're still not load-bearing. `asy_webserver_service.py`'s
  own `_body_as_dict()` and `_put_sensors()`'s per-sensor `isinstance(fields, dict)` check already
  guarantee only dict-shaped data ever reaches `write_config()`, and `get_dict()`'s `keys` always
  comes from a schema (`schema_names()`), never request data - so these three catches remain pure
  defense-in-depth, not because the REST wiring is missing but because the REST layer's own
  validation already fully absorbs the risk before it gets this far. Already covered by direct unit
  tests (`tests/test_config_manager.py`) independent of caller discipline - no further action.
- **Whole-system integration test scope — closed.** `tests/test_sensortask_wozi.py` and
  `tests/test_digital_twin_sensortask_integration.py` exercise the real `build_system()` object
  graph end-to-end (construction order, FRAM chunk order, the `setup()`-batch order, every REST
  endpoint reachable over real HTTP against real twin-backed drivers, task-supervisor restart
  against the real full task list, the WiFi hotspot/DNS/status-LED chain through a real STA→hotspot
  transition, and SGP40 VOC-backup reboot survival through the real `sgp_reader`/`fram`
  construction order and a real simulated reboot) — see `SPECIFICATION.md` Parts A.7/A.8.
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
- **Firmware build script should strip `if TYPE_CHECKING:` blocks from its temp frozen-copy, not
  the real `src`/`ext` files.** `mpy-cross` does not dead-code-eliminate `if TYPE_CHECKING:` the way
  it does an `if micropython.const(0):` branch — confirmed empirically (compiled real `src/*.py` +
  `ext/microdot.py` with this repo's own `mpy-cross`): the guarded imports/Protocol classes/type
  aliases fully survive into the `.mpy` bytecode (their qstrs included) since `TYPE_CHECKING` is a
  plain runtime-checked global, not a compile-time constant. Stripping these blocks (via an `ast`
  transform: parse → drop `if TYPE_CHECKING:`/its defining `try/except ImportError` header → re-parse
  the unparsed output as a validity check → hand that to `mpy-cross`) saved ~3.6KB across the 22
  files promoted to `src/` at the time of this measurement (108,339 → 104,748 bytes total; `src/`
  has since grown past 22 files, so a re-run today would save more, not less) — all still compiled
  clean. Safe specifically
  because nothing on this platform ever does runtime annotation introspection (no `typing` module,
  no `get_type_hints()` on-device) — the guarded names are only ever reached via string-literal
  forward-ref annotations that MicroPython never evaluates anyway, so deleting the block changes
  nothing observable. Directly grows the Pico W littlefs partition, which is whatever flash remains
  after the firmware image (see `SPECIFICATION.md` Part F.1). This prototype has not been committed
  to the repo — reimplement as a proper `scripts/`-housed step when the build script itself
  gets built, matching only a bare `TYPE_CHECKING`/`mod.TYPE_CHECKING` test (leave any compound
  condition untouched rather than guess) and sanity-`ast.parse()`-checking its own output before
  compiling.
