# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

## Refactor targets not yet done

- **Bare `except:` is forbidden in refactored code** (`except Exception:` or narrower required).
  Ruff's E722 is already enabled, so existing bare excepts in `improved-quality/` show as tracked
  findings rather than being silenced — eliminating them is still real refactor work.
- **No CI firmware-build stage yet.** Blocked on genericizing `build-*.sh`'s hardcoded
  `/home/nico/rpi_pico/...` path and the `py-include` symlink (see "Deferred" below) — needs to
  land before/alongside this.
- **Mypy shall be configured to disallow `Any` types** (owner-specified, not yet implemented). The
  closest existing option is `disallow_any_explicit`; `pyproject.toml` deliberately stops short of
  it and the other `--strict`-only checks today. Blast-radius check done: `Any` appears ~29 times
  across `src/`/`tests/`, almost entirely in test-file monkeypatch/wrapper classes duck-typing a
  real MicroPython object rather than reimplementing its interface — turning this on will need a
  real typing strategy for those wrappers (e.g. `Protocol` classes matching just the overridden
  methods, plus `__getattr__` delegation) worked out first, not just a flag flip.
- **Per-driver REST config setters are a known gap, deliberately not closed sensor-by-sensor.**
  `get_dict_cfg()` gives every `*_Reader` a generic, schema-driven way to *read back* its config;
  there's no equivalent generic *write* path — each REST handler still calls `set_*` methods one
  field at a time by hand, and several config values accepted by a REST handler (SGP40's
  `BackupPeriod`/`BackupMaxAge`/`WaitTimeNTP`) have no setter on the driver at all, so the write is
  a silent no-op against real hardware. Deferred on purpose until all three sensors (SCD30/SGP40/
  BMP3xx) were promoted to `src/` — **that's now done** — so a single consolidated generic-setter
  mechanism can be designed once across all of them (applies to `config_manager.py`'s own
  `ConfigManager` too: typed getters exist, no matching typed setters, only untyped
  `write_config(dict, schema)`).
- **FRAM bus-recovery is only partially wired up.** `asy_fram_driver.py`'s own `src/` promotion
  added device-identification/write-protect verification, but there's still no periodic/triggered
  re-probe policy (`verify_present()`/`get_write_protected()`/`set_write_protected()` have zero
  callers anywhere) and no task supervisor for FRAM specifically. Whoever wires this up must wrap
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
- **Bus concurrency (`asyncio.Lock` + `async with`) needs a coverage audit** — no gaps, no
  deadlock/starvation. The `*_DeviceSession(Lockable)` pattern (an outer per-sensor lock around a
  whole write-then-read transaction, `asyncio.sleep(0)` yield between phases) is the pattern to
  verify/extend, not start from scratch. (The one concrete gap this audit had already turned up —
  SCD30's low-level getter/setter forwards not logging via `self.pr.err_s()`, unlike BMP3xx's — is
  now fixed; see DRIVER_SPEC.md section 7 for the settled forward-logging convention every driver
  now follows. The broader "no gaps, no deadlock/starvation" audit itself is still open.)
- **Common driver error classes across sensors — future direction, not designed or implemented
  yet.** Each driver currently defines and reports its own `errno`/`wrnno` values independently
  (see DRIVER_SPEC.md section 7); the one exception is `errno=10` ("initial setup failed"), which
  all three drivers already use for the same situation by independent convergence rather than by
  any enforced scheme. Project owner's stated direction: keep per-driver definition/reporting (not
  a single shared enum), but predefine a small set of common error *classes* so the same number
  means the same or an equivalent condition across different drivers, beyond just the one
  already-consistent case. No scheme (numbering ranges, category list, how a driver opts in)
  designed yet — out of scope until config setters (above) are done.
- **Neopixel warning-flash sequencing and the task-supervisor error-budget counter** are both
  behaviorally correct and intentional as designed, but flagged by the owner as implementable more
  efficiently — worth a cleaner implementation in the refactor without changing observed behavior.
- **`improved-quality/microdot.py` is a confirmed *unintentional* fork of vendored Microdot**
  (owner-confirmed). Action when refactor work resumes: revert it to match upstream exactly, no
  behavioral additions ever. Not touched now (`improved-quality/` source stays out of routine
  editing) — distinct from `python/CommonDrivers/microdot.py`, which still matches upstream.
- **Rough sequencing, not a committed plan**: (1) dev/build environment setup (genericized
  `build-*.sh`/toolchain paths) — everything else touching CI/firmware depends on this; (2) the
  structural patterns above (per-sensor config, generalized error-counter bookkeeping) are largely
  done; (3) bus/sensor error-recovery robustness items above, which build on that structure; (4)
  remaining tooling/CI (the firmware-build stage) — mypy/ruff/stubs/Unix-port-tests were pulled
  forward out of this order already, once `math_helpers.py` cleared the `src/` bar, and that's now
  standing practice for every new file, not a one-off.

## Open questions (need owner input or further investigation)

1. `modules/_boot.py`'s `import sensortask.py` (literal `.py`) — works reliably on real hardware,
   but MicroPython's documented freeze/import behavior says it should raise `ModuleNotFoundError`.
   Mechanism genuinely unresolved. **Do not "fix" without testing on real hardware first.**
   Addressed during the refactor, not before.
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
4. SCD30 `ForceCalRef` field procedure isn't written down anywhere — a real maintenance routine
   exists (confirmed by owner) but the actual steps (reference concentration, exposure
   conditions/timing, frequency) still need capturing from the owner.
5. Does `config_manager.py`'s `write_config()` need long-block-lock-style coordination? Its
   `open()`+`json.dump()` has no yield point, the same shape `__init__`'s read path had before the
   cache-elimination redesign closed *that* concern. Whether a real RP2040 littlefs write of a
   small config file is fast enough not to matter is a hardware-timing question this dev
   environment can't verify — needs either a real-hardware measurement or an owner call on wiring
   it in proactively. **Note**: `get_long_block_lock()` itself has since been removed entirely (see
   CLAUDE.md's "Long-blocking operations" hard rule) — this question was never about that specific
   lock instance, and removing it neither resolves nor forecloses this question. Answering "yes"
   here would mean designing a fresh coordination mechanism at that time, not reusing or
   resurrecting anything already removed.
6. `get_ambient_pressure()`'s read-back (SCD30) reuses the same command word used to *set* it —
   matches every sibling getter's pattern and the legacy driver, but neither Sensirion's own
   `embedded-scd` reference driver nor their `python-i2c-scd30` driver treats that command as
   readable (their own worked examples/command classes only show a write path for it). Not proven
   broken — legacy behavior, uneventful field use — but never confirmed against an authoritative
   source either. **Resolved by owner: leave as-is**, no alternate documented read-back exists to
   switch to regardless; recorded so it isn't re-investigated from scratch.
7. Real-hardware verification gap for `asy_udp_socket.py`/`captive_dns.py`: every UDP-layer claim
   (POLLERR/POLLHUP delivery, truncation, connected-socket source filtering) is verified against the
   MicroPython Unix port's socket implementation, not real rp2/lwIP — no rp2 hardware was available
   to test against. If a deployed unit ever shows UDP behavior diverging from what's
   tested/documented in the driver, this is the first place to look. Considered closing via a
   standalone on-device verification script — judged too hypothetical to chase for now.
8. BMP390's own datasheet isn't in `datasheets/bmp3xx/` (only BMP384/BMP388 are) — its `0x60` chip
   ID and assumed-identical register map/IIR table couldn't be verified against a real BMP390
   datasheet. Needs the owner to add the datasheet to close this.
9. `asy_wifi_service.py` never configures `wlan.config(reconnects=...)`, so the RP2040 WLAN driver
   may retry an STA connection internally forever and never actually settle on
   `STAT_WRONG_PASSWORD`/`STAT_NO_AP_FOUND`/`STAT_CONNECT_FAIL` — meaning `_poll_sta_connect_status()`'s
   dedicated handling of those three codes could be effectively unreachable on real hardware, and
   `connection_failures` may really just be "didn't finish within the poll window," not a genuine
   driver-reported failure. Trading this away would mean calling `wlan.config(reconnects=0)`, which
   changes retry behavior in ways only the owner can weigh. Rediscovered during this file's original
   promotion review; needs an owner call, not a unilateral fix.
10. Whether a hot-unplugged/replugged I2C or SPI sensor fully recovers is only field-tested at the
    task-death-and-respawn level (the whole `*_Reader` task dies and gets restarted by the
    supervisor) — never confirmed as *complete* recovery of the underlying bus/device state itself.
    Owner-flagged as "may be incomplete," to revisit/harden during the refactor rather than assume
    solved.
11. `scripts/typecheck.sh`'s combined `mypy src tests` run resolves every `from machine import X`
    project-wide to `tests/machine.py`'s fake module, not the real `typings/machine.pyi` board
    stub — true for every `src/` file, not just ones that exercise it directly. Whether any
    already-promoted driver has been silently type-checking against the fake's (so far compatible)
    signatures instead of the real stub this whole time has never been specifically re-verified.

## Deferred / explicitly out-of-scope work

- **Rename `max_i2c_err`** (`base_classes.py`'s `SensorReaderConfig`/`SensorReader` constructor
  parameter, and every promoted driver/service's own constructor that forwards it) to something
  bus-agnostic — confirmed by the owner it's a generically-useful "consecutive-failure streak
  before giving up and restarting the task" threshold via `_error_check()`, not literally about
  I2C, and both `asy_wifi_service.py` and `asy_ntp_client.py` (neither has an I2C bus) already rely
  on it under that misleading name. Deliberately not renamed yet (owner's own framing: "we will
  rename it later in another context") — touches every promoted driver/service's constructor
  signature and every test file that constructs one, a wider blast radius than any one promotion
  pass.
- **HTML/frontend automation & consistency** — known hand-written/brittle, not a priority; revisit
  after the Python-side refactor.
- **UART sensor integration** — `asy_uart_driver.py` is promoted to `src/` but deliberately not
  wired into any `sensortask-*.py`; `asy_uart_comm.py` (its one real consumer) is its own separate,
  still out-of-scope promotion. Unused by any deployed config — wiring it in is after the refactor
  of already-deployed features, not before.
- **Config-duplication centralization** — same keys hand-kept in sync across `_DEFAULT_CONFIG`, the
  REST handler, and the HTML form. Owned by the refactor: each promoted `*_Reader`'s own `_VAL_*`
  schema tuple + `get_dict_cfg()`/`get_dict_data()` is the intended single source, not fully wired
  end-to-end yet (`sensortask-wozi.py` itself predates the per-sensor-config model — see "Refactor
  targets not yet done" above).
- **`dev` config quirks** (e.g. LED/Neopixel REST routes referencing an uninstantiated object) —
  bench rig only, not bugs to fix.
- **Dev/build environment setup**: toolchain installer is done (`toolchain/setup_toolchain.py`, see
  `toolchain/README.md`/README.md's "Toolchain setup"). **Still not done**: doesn't yet genericize
  `build-*.sh`'s hardcoded `/home/nico/rpi_pico/...` path or the `py-include` symlink — the next
  step, and now a real near-term prerequisite for the firmware-build CI stage.
  `update_and_install.txt` re-verified against current upstream docs — structurally still accurate,
  but missing the pico-sdk 2.0.0+ picotool major.minor version-matching requirement (already applies
  today) and the full apt package list. An official one-shot alternative exists
  ([`raspberrypi/pico-setup`](https://github.com/raspberrypi/pico-setup)'s `pico_setup.sh`), worth
  considering as a base.
- **No end-user reference for Neopixel LED colors/patterns exists** — confirmed intentional
  single-LED dual-duty design, but no legend anywhere. Worth adding, low priority.
- **FRAM SGP40 "0 = disabled" backup/staleness semantics need user-facing documentation** — the
  behavior itself is intentional (see CLAUDE.md), just undocumented for whoever configures a unit.
- **`asy_wifi_service.py`'s getters hide two opposite locking contracts under one shape**:
  `network_available()` requires the caller to already hold `wifi_mode_lock` (documented in-line),
  while `get_wlan_ifconfig()`/`get_dns_server_ip()`/`get_wlan_rssi()`/`wlan_isconnected()` assume the
  *caller does not* hold it (checking `.locked()` defensively instead). This exact mismatch already
  caused one real bug (a fixed `get_dns_server_ip()` always returning `None`) — the underlying
  inconsistency itself is unfixed, flagged as worth a naming/typing convention if a third such
  callback is ever added, not urgent enough to redesign now.
- **`config_manager.py`'s `make_dict()` has a `repr()`-parsing quirk with non-scalar fields**: it
  splits a namedtuple's `repr()` on `"("`/`","`, so a field whose own value contains one of those
  characters corrupts the result — a nested-tuple-valued field truncates every subsequent field out
  of the returned dict silently, and a list-valued field (comma inside `[...]`) produces a garbage
  key that collapses the whole dict to all-`None` via the outer `except Exception`. Dormant today —
  every current config namedtuple (`SGP40`/`BMP3XX`/`NTP`/`SCD30`/`WIFI`) is flat scalar fields only
  — but a real landmine for whoever adds a list/nested-tuple config field next; check this function
  first if a promoted driver's config read-back silently comes back wrong/empty after such a change.
- **`config_manager.py`'s three defensive `TypeError`/`AttributeError` catches** (non-string
  filename, non-iterable `keys`, non-dict `data` passed to `write_config()`) are currently dead
  weight — nothing in `src/`/`improved-quality/` calls these with malformed input today. Owner's
  stated rationale for keeping them anyway: once the Microdot REST layer feeds real (untrusted)
  request data into these paths, they stop being defensive-only and become load-bearing. Revisit
  once that wiring exists, not before.
- **`asy_i2c_driver.py`'s `get_bits`/`set_bits`/`get_register_struct` still call the allocating
  `readfrom_mem()` rather than zero-copy `readfrom_mem_into()`** — no real caller needs the
  zero-copy path yet, but worth doing before `asy_isl29125_driver.py` (its one plausible future
  caller) is migrated.
- **`captive_dns.py`'s root-domain query (a single zero-length label, `.`) can't be told apart from
  a failed parse** — both produce `domain == ""`, so `response()` returns `None` for both,
  contradicting the module's own docstring claim that every on-subnet query gets an answer. No real
  captive-portal probe ever queries the bare root, so this is a documented gap, not an active fix.
- **`asy_scd30_driver.py`'s persistent NVM setters have no published write-cycle endurance figure**
  (checked every available Sensirion doc) — safe today only because every setter is REST-triggered,
  never called from a boot path or periodic loop. Don't add a periodic/high-frequency caller
  without reconsidering this.
- **`asy_wifi_service.py`'s 60s STA-retry branch holds `wifi_mode_lock` for up to a minute**, and
  `asy_ntp_client.py`'s sync task waits on that same shared lock — NTP sync can be delayed up to a
  minute during active WLAN instability. A priority-inversion-shaped cost worth having in view, not
  a correctness bug; not acted on.
