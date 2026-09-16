# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently lives in CLAUDE.md (AI-session
operating constraints/architecture reference) or README.md (human-facing orientation) instead,
migrated there rather than duplicated here. See README.md for orientation, CLAUDE.md for operating
constraints.

## Refactor targets not yet done

- **A config-persisting `PUT /sensors` resets its own HTTP connection when it lands under
  concurrent API load. HIGH IMPORTANCE, must be fixed — completely unforeseen (project owner,
  2026-09-15); it is not to be tolerated in a test, and the failing test must not be weakened to
  accommodate it.** Found by the two bench-tier config-write tests the bus-hazard work added
  (`tests_hardware/bench/test_bus_concurrency_under_api_load.py`'s
  `test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` and
  `test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load`), running
  against the real dev board on the shipped `threshold` build. **Isolated to the flash write
  itself**, three conditions, 2 GET workers × 8 iterations + 4 PUTs each, repeated:

  | condition | connection resets |
  |---|---|
  | GET load only | 0 |
  | GET load + PUTs returning `"Unchanged"` (accepted, nothing written) | 0 |
  | GET load + PUTs that really persist to the flash filesystem | 1–2 per run, **every one on the writing connection** |

  The host sees `ConnectionResetError: [Errno 104]`. Reproduced on most runs (5 resets across 3
  `change`-mode rounds in the isolation probe, plus 4 of 4 pytest runs before it). Three facts
  narrow it: a bystander GET is **never** reset, only the connection whose own request is being
  serviced; the config always persists correctly afterwards (no data loss, no corruption); and the
  DUT's own `WEBSERVER` error log stays completely empty, so nothing on the device notices. A quiet
  (unloaded) persisting PUT never reproduces it.
  **Why this is a design question, not a test question**: an RP2040 flash erase/program is
  inherently uninterruptible — XIP is disabled and interrupts are off for the duration, so the
  CYW43 link is unserviced and lwIP's timers do not run, which is exactly CLAUDE.md's F.3
  "long-blocking operations must not stall timing-sensitive work" meeting an operation that cannot
  yield. The fix therefore has to be a design-level one in the REST/persistence layer (send the
  response before performing the persist, defer the write to a point where no connection is
  mid-response, or similar), decided by the project owner — not a tolerance added to the assertion.
  Note this interacts with an already-settled safety property: CLAUDE.md's WiFi-power-cycle recovery
  rule depends on "every real flash write is reachable only through the REST PUT path", so any
  redesign that moves the write off that path must re-establish that argument.
  **Source**: found and isolated by the real-hardware session on branch
  `claude/real-hardware-memory-validation-p3vkxr` (PR #84), recorded in its commit `679c2b0`; that
  branch/PR is being discarded once this and its sibling ISL29125 finding are independently
  resolved on this branch, so this entry — not the PR — is now the record of it. A follow-up
  investigation on this branch (source/docs only, no real-hardware access) confirmed the mechanism
  against the pinned MicroPython v1.29.0 source directly: `ports/rp2/rp2_flash.c`'s
  `begin_critical_flash_section()`/`end_critical_flash_section()` wrap *each* `flash_range_erase()`
  and `flash_range_program()` call individually in `save_and_disable_interrupts()` (plus a
  multicore lockout, unused here since this project is single-core), and that same global
  interrupt disable also gates the CYW43 GPIO "host wake" IRQ, its PendSV-dispatched `cyw43_poll()`,
  and the hardware-alarm-driven soft timer that runs lwIP's own `sys_check_timeouts()`
  (`ports/rp2/mpnetworkport.c`) — so the blackout isn't specific to the one coroutine handling the
  PUT, it is a total, port-wide freeze of every connection's TCP housekeeping and of the WiFi
  radio's own servicing for the operation's duration. A multi-sensor PUT does one such blackout
  window per changed sensor (each `write_config()` call is a separate synchronous, unyielding
  `open()`/`json.dump()`/close file write with no `await` inside it), not one longer window, since
  `_put_sensors` awaits each sensor's `_set_dict_cfg()` in turn. What source alone could **not**
  confirm: the precise packet-level trigger for the RST specifically (vs. a plain stall). One
  candidate mechanism was found and then ruled out on timing grounds — `extmod/modlwip.c`'s socket
  close path arms a `tcp_poll()` callback that aborts (RSTs) a connection whose close doesn't
  complete cleanly, but only after `MICROPY_PY_LWIP_TCP_CLOSE_TIMEOUT_MS` (10000ms) — far longer
  than any plausible single flash-op blackout, so this is very unlikely to be it. The remaining
  candidates (an immediate `tcp_abort()` fallback when `tcp_close()` itself returns non-OK, e.g.
  `ERR_MEM`; or lwIP's own RFC-793 response to a segment that arrives for that PCB during the
  blackout and looks stale/out-of-window once processing resumes) are plausible but need a real
  packet capture against the dev board to confirm — a future real-hardware session's job, not
  something resolvable from source alone.
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

- **`isl29125_lighting_scenarios.py`'s `W13` dead-interrupt warning fired in 2 of 4 runs before the
  entry-park fix and in 0 of 3 after it — plausibly explained, not proven.** The warning needs five
  *consecutive* range decisions taken by the periodic safety net with no threshold interrupt behind
  them. The pre-fix runs had three scenarios entering on an inherited wrong range, each of which
  forced an unplanned corrective down-switch — a decision no threshold crossing ever announced,
  because the light had not actually crossed one, so exactly the kind that feeds that counter. That
  would explain both the firing and its disappearance, but three clean runs is thin evidence for an
  intermittent, and the mechanism was never confirmed against the driver's own decision path.
  Worth one dedicated look: if it is right, nothing is wrong; if W13 returns on a green-entry run,
  it is a real signal about the INT path that the passing
  `test_isl29125_real_irq_edge_beats_the_periodic_fallback` does not cover, since that one proves a
  single edge arrives, not that edges keep carrying decisions under sustained range activity.

- **NEXT UP once the ISL29125 test work is finished (project owner, 2026-09-16): sweep the
  digital-twin suite for fixed-budget `asyncio.sleep(N)`-then-assert waits, the shape that makes a
  test measure the HOST's speed instead of the code under test.** One instance was found by accident
  and is fixed (`test_digital_twin_bus_hazard_concurrency.py`'s
  `_run_real_task_graph_and_assert_healthy()` now polls for first samples via `_await_first_samples()`,
  bounded, with the per-sensor assertions unchanged so a genuinely dead sensor still fails - proved
  by mutating `_store_sgp()` to store nothing, which still fails with the same message). **25 more
  fixed-budget sleeps remain** across `test_digital_twin_bus_hazard_concurrency.py`,
  `test_digital_twin_real_website_integration.py`, `test_digital_twin_network_neopixel.py`,
  `test_digital_twin_sensortask_integration.py` and `test_digital_twin_webserver_concurrency.py`;
  none has been checked, and the one that was checked was wrong.

  **Read this before chasing an SGP40 bug: there isn't one.** The failure surfaced as `SGP40 never
  produced real data under concurrent bus load`, reproduced 2 of 2 under 4-way CPU load on the bench
  Pi4 and 0 of 4 unloaded, which reads like an SGP40-specific degradation. It is not. Time-to-first
  sample on dev's real twin task graph, measured directly:

  | sensor | unloaded | 4-way CPU load |
  |---|---|---|
  | BMP3xx | 4986 ms | ~13.3 s |
  | ISL29125 | 5906 ms | ~14.4 s |
  | SCD30 | 6429 ms | ~14.8 s |
  | SGP40 | 6746 ms | ~15.9 s |

  Every sensor slows by roughly the same absolute amount (~+8.5 s, a uniform ~2.4x), and under load
  **all four** blow the old 9 s budget. SGP40 was named only because it is the first of the three
  assertions in that block (line 165) and, separately, is consistently last to report by a few
  hundred ms. So the signature is pure host-CPU starvation of the twin's simulated timing, not bus
  contention and not a driver fault - the same conclusion the sibling test at line 398 would have
  reached with the same misleading message. A future session should not read "SGP40" in that
  assertion as evidence about SGP40.

  Two things the sweep should decide, not just mechanically convert: whether a bounded poll is right
  everywhere (a test whose POINT is that something happens within a deadline must keep its deadline),
  and whether the outer `run_timed()` timeouts still make sense once inner waits can stretch - the
  two here went 20s -> 40s so the safety net cannot fire before the bounded wait finishes.

- **A full `scripts/test.sh` run's own `tests/_tmp` directory grows unboundedly across the whole
  run, and once it accumulates enough entries this causes real, multi-minute-scale test slowdowns —
  found while verifying WP1/WP2.** **The "confirmed unrelated to WP1/WP2" half of that
  conclusion is wrong, and the correction matters more than the original finding** (measured on the
  bench Pi4, 2026-09-16, `tests/_tmp` wiped immediately before every run, same interpreter, same
  `-X heapsize=32M`): `tests/test_sensortask.py` takes **15s at `9cf8a9c^` and 498s at `9cf8a9c`**
  itself - the WP1+WP2 commit - a **33x slowdown from that one change**, reproduced at 501s on a
  second idle run of the merged tree. All 321 tests pass in both cases; only wall clock moved. That
  alone puts the file at more than double `scripts/test.sh`'s own 240s per-file timeout with a
  pristine temp directory, so it fails the suite with or without the accumulation described below.
  `tests/test_digital_twin_webserver_concurrency.py` is in the same position at 273s.
  The mechanism is visible in the diff: every `ConfigManager` now builds its logger through
  `make_logger(fram, ...)` and awaits `self.pr.setup()`, so a graph that constructs many
  ConfigManagers pays a real FRAM-backed logger setup per manager instead of a bare
  `PrintLogHistory()`. On real hardware `build_system()` runs once per boot, so this is a boot-time
  and FRAM-chunk-budget question (SPECIFICATION.md Part A.7's chunk layout) rather than a
  steady-state one - but it is a WP1/WP2 question, not a temp-directory one, and the entry below
  should not send the next session looking in the wrong place.
  The temp-directory growth is real too, and still worth fixing on its own: Every `tests/test_*.py` file that
  needs its own per-test config-file isolation creates fresh subdirectories under the one shared
  `tests/_tmp` (e.g. `_tmp_cfg_dir()`/`dtcc_<n>`/`dtrw_<n>`-style helpers, one per file, each
  sweeping only *its own* prefix at its own start via `_sweep_stale_tmp_dirs(prefix)`) — nothing
  sweeps any other file's leftovers, so the directory's total entry count only ever grows across a
  single `scripts/test.sh` invocation's full 66-file sequence. **Confirmed directly, isolated from
  any WP1/WP2 code change**: pre-populating `tests/_tmp` with 900 generic, unrelated directories
  (simulating "60 other files already ran") and then running `tests/test_sensortask.py` alone — a
  file whose own code was not touched by this experiment — took **7m2s instead of its normal <2
  minutes**, with `user` time barely changing (33s vs the normal ~10s) - almost the entire extra
  time is blocked on filesystem I/O (`os.mkdir()`/`os.listdir()`/`os.rmdir()` calls scaling badly
  with directory entry count on this container's filesystem), not test logic. This is exactly what
  was intermittently timing out `tests/test_sensortask.py` and
  `tests/test_digital_twin_webserver_concurrency.py` — the suite's two heaviest, most
  temp-dir-hungry files — inside full `scripts/test.sh` runs during this session, even after
  raising `-X heapsize` and the per-file timeout for unrelated, real reasons (see this file's other
  WP1/WP2 entries): both passed **every single test correctly**, every time, whether standalone or
  mid-suite; only the *wall-clock budget* was ever at risk, and only once the shared directory had
  grown enough. **Not fixed here — needs a design decision, not a quick patch**: candidates include
  a single global sweep of the whole `tests/_tmp` tree once at the very start of `scripts/test.sh`
  (before any test file runs, rather than each file sweeping only its own prefix), giving each test
  *file* (not just each test function) a directory that's fully removed (not swept-by-prefix) when
  that file's own run starts, or moving to a scheme that doesn't accumulate at all. Whichever is
  chosen must not weaken the isolation these directories exist for. Real CI (GitHub Actions) starts
  each job from a fresh checkout with no directory to have accumulated *before* that job's own
  `scripts/test.sh` invocation, but every one of that invocation's own 66 files still shares the
  same `tests/_tmp` across that one run, so the same growth-across-one-run mechanism applies there
  too, not just in a long-lived local sandbox - this is worth confirming against a real CI run
  before assuming it never bites there.
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
  standing real-hardware gate, not given in this session.
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

16. **Seven `src/` modules number `errno`/`wrnno` inside the range `base_classes.py` reserves.**
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

17. `asy_uart_comm.py`'s `wrnno` 11 ("drain bound reached - the peer never stopped sending") can
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
- **Wiring WiFi/NTP/webserver into the device's FRAM chip (WP1, CLAUDE.md's implicit-FRAM-wiring
  rule) measurably increases one-time boot latency, via lock contention on the FRAM chip's single
  shared `asyncio.Lock` (`FRAM_SPI`, `src/asy_fram_driver.py`), not via any per-op slowness.** Every
  FRAM-backed module's own task calls `self.pr.setup()` (a real chunk read, and a write on first
  boot) the first time it runs; `system_service.py`'s `start_and_check_tasks()` starts every task
  within one ~1-second stagger window, so once `conn`/`ntp`/`webserver`/`conn`'s own `DNSServer`
  joined the existing FRAM-wired set (`sysfunct`/`scd30`/`sgp40`/`bmp3xx`/`neopixel`/`notification`),
  all of them now contend for that one lock in the same busy window. Measured directly against the
  real generated code for all 6 devices under the digital twin: boot-to-first-`200` now lands between
  ~4.5s and ~6.3s (`dev` slowest — the device with the most FRAM-wired instances), versus ~1.9-2.2s
  before WP1. **Not open work**: the finding is the resolution — this is a one-time, self-resolving
  boot cost (steady-state serving is unaffected), matching CLAUDE.md's own already-accepted position
  that boot latency isn't a thing to optimise for its own sake, so
  `tests_scripts/test_digital_twin_generated_boot.py`'s own `_TWIN_DURATION_S` was raised (6 → 15) to
  sit comfortably above the new observed range rather than inside it — see that constant's own
  comment for the full measurement. **Re-measured after WP2 landed** (every `SensorReaderConfig`-
  based module's own `ConfigManager` now also draws its own separate chunk): boot-to-first-`200`
  moved to ~6.1s (wozi) / ~7.7s (dev), a modest further increase over WP1-alone's ~5.1s/~6.3s, not
  the much larger jump the lock-contention theory alone would predict — because every one of WP2's
  new chunks (`conn`/`ntp`/`sysfunct`/`sgp40`/`bmp3xx`/`notification`'s own `cfgmgr`) has its
  `setup()` called as part of that same module's own `.setup()`, which rides the pre-task-start
  setup batch (`sysfunct → fram → conn → ntp → sgp40 → bmp3xx → notification`, SPECIFICATION.md's
  own step 16) rather than the contended task-starter stagger window - only `webserver`'s own lazy
  `self.pr.setup()` is exposed to that contention, and WP2 adds no new chunk to `webserver` itself
  (it still has no `cfgmgr`). Both numbers stay comfortably inside the 15s test budget. Still worth
  watching if a real-hardware run ever shows this mattering there, but the design itself needs no
  changes on this evidence.
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
- **`asy_i2c_driver.py`'s `get_bits`/`set_bits`/`get_register_struct` still call the allocating
  `readfrom_mem()` rather than zero-copy `readfrom_mem_into()`** — this was flagged as worth doing
  before `asy_isl29125_driver.py` was migrated, and that migration has now happened without it.
  **Still not done, deliberately, and worth a decision rather than silent carry-over**: the ISL's
  own hot path is one `get_register_struct(_REGISTER_DATA, "6s")` per read cycle — a 6-byte
  allocation at the configured sample interval, nowhere near the fixed-size-buffer bar
  SPECIFICATION.md Part I reserves the zero-copy treatment for. The cost of doing it is a changed
  signature on three shared methods every existing driver calls. Left as the same low-priority item
  it was, no longer blocked on anything.
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
