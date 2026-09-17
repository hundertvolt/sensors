# Real-hardware test requests — `claude/digital-twin-wifi-fram-persistence-fix` (PR #103)

Temporary file, same convention as `REAL_HARDWARE_HANDOVER.md`/`WP_RESTART_HANDOVER.md` before it:
delete once its findings have been either confirmed-and-migrated into `SPECIFICATION.md`/
`CLAUDE.md`/`BACKLOG.md`, or confirmed not to apply. Written by a session with **no real-hardware
access this conversation**, for a session that has (or will get) the project owner's go-ahead to
run against real hardware — see CLAUDE.md's standing gate ("A session needs the project owner's
go-ahead, given directly in that session's own conversation, before running anything against real
hardware"). Nothing in this file authorizes skipping that gate.

## Context: what this branch actually changed

This branch fixes two `digital-twin-e2e` staleness bugs surfaced by WP1's FRAM wiring, then a real
(not flaky) CI timeout on `dev`'s `PUT /status {"ResetErrors": true}`: WP1/WP2/WP3 grew `dev`'s
FRAM-backed error-log subset to 10+ entries (every `CFGMGR_<name>` logger, WIFI/NTP/WEBSERVER/
SYSTEM, SGP40/BMP3XX, plus `dev`'s own two `uart_link` instances `UART_init`/`UART_resp` that no
other device carries), and `_put_status()` resets every one of them sequentially, each paying a
real FRAM write. Fixed by raising that one call's timeout in the CI suite
(`scripts/_digital_twin_ci_suite.py`'s `_RESET_ERRORS_TIMEOUT_S = 20.0`), not by changing any
runtime behavior. Separately, this branch merged in the base branch's test-economy work
(`TEST_PARALLELISM`, heap size, per-device test splitting) — that part is host/CI-sandbox-only and
has **no real-hardware implication at all**; don't spend bench time on it (see "What NOT to do").

Everything below is about the FRAM-wiring side, all measured only against the digital twin's fake
FRAM chip (`digital_twin/_fram_chip.py`, zero real wire time) or reasoned about from code — none of
it has a real number yet.

## What to measure — in priority order

### 1. Real wall-clock time for `PUT /status {"ResetErrors": true}` on `dev`

The CI suite's 20.0s timeout was sized to survive **CI-runner contention**, not calibrated as an
expected real-hardware duration — on an uncontended real bench board this call should be much
faster, but there is no real number to confirm that. Measure, on `dev`'s own real entry point/config
(not `wozi`'s hardcoded pins on the `dev` board — CLAUDE.md's WoZi/dev policy, that combination
"tests nothing at all"):

- End-to-end HTTP round-trip time for a real `PUT /status {"ResetErrors": true}` once the board has
  been running long enough to have accumulated at least one real entry in several of the FRAM-backed
  logs (a boot-time `CFGMGR_*` write is enough — doesn't need an actual fault injected).
- Confirm the response is `200` and every FRAM-backed counter (`GET /status`'s `errcount`, the full
  chunk layout in CLAUDE.md/SPECIFICATION.md Part A.7 — SGP40/BMP3XX/SCD30/SYSTEM/NEOPIXEL/NOTIFY/
  WIFI/DNSSRV/NTP/WEBSERVER, every `CFGMGR_<name>`, `UART_init`/`UART_resp`) actually reads back 0
  afterward — not just that the HTTP call itself returned in time.
- **Before this call**, per CLAUDE.md's standing rule: read `GET /status`'s FRAM-backed error logs
  first and record what's there — this call is destructive/irreversible for that evidence.

### 2. WIFI's FRAM-backed error log across a real abrupt restart

This branch's merge brought in a base-branch change to `_run_8_wifi_persistence_and_configure_ntp`:
WIFI's own top-level error log is now understood to be FRAM-backed (WP1's implicit-FRAM-wiring
rule), so it should survive an abrupt restart **all-or-nothing** (either the full pre-restart count
or 0, never a partial remnant) — the same guarantee already established for SGP40 in the twin. This
has only ever been checked against the twin's fake chip. On `dev`:

- Trigger WIFI's scripted connect-failure path enough times to log a few real "W"-typed history
  entries (see `asy_wifi_service.py`'s `conn_fail_to_hotspot`/`wrn_s()`), confirm they appear via
  `GET /status`, then power-cycle (abrupt, not a commanded reboot) and confirm the count comes back
  either unchanged or exactly 0 — never a partial count.

### 3. `dev`'s two `uart_link` instances (`UART_init`/`UART_resp`) through the same reset path

New to the FRAM-backed subset under WP3, never exercised on real hardware through
`PUT /status ResetErrors` before. On `dev`'s real crossover-jumper UART pair:

- Confirm both instances' error counters are independently resettable via that same call and read
  back correctly afterward via `GET /status`.
- Confirm issuing `ResetErrors` while the UART link is mid-transfer doesn't stall or corrupt an
  in-flight exchange — CLAUDE.md's standing rule that `asy_uart_driver.py`/`asy_uart_comm.py` may
  never block the asyncio loop, even briefly, applies regardless of what else is happening
  concurrently on the webserver task.

## What NOT to do

- **Don't measure boot-to-first-`200` latency, or anything else from the test-economy merge
  (`TEST_PARALLELISM`, `-X heapsize`, per-device test splitting).** All of that is host/CI-sandbox
  timing only — the real rp2040 never runs more than one device's own object graph once per boot,
  and CLAUDE.md is explicit that boot latency itself is not a metric to optimize for its own sake.
  If `REAL_HARDWARE_HANDOVER.md` (a separate, older handover on a different branch) is still open
  when this lands, treat it as unrelated work, not something this file's requests fold into.
- Don't re-run `scripts/build_firmware.py wozi`'s hardcoded pins on the `dev` bench board — this
  "tests nothing at all" per CLAUDE.md and has produced false bugs before.
- Don't treat a `ResetErrors` call as safe to retry casually once real FRAM-backed evidence exists
  on the board — read `GET /status` first, every time, per CLAUDE.md's standing rule.
- Don't chase `asy_fram_manager.py`'s/`asy_fram_driver.py`'s internals in response to anything found
  here — vendored-adjacent, heavily-audited FRAM logic (SPECIFICATION.md Part C.3.1); any real
  change there needs its own scoped review, not a drive-by from this file's measurements.
