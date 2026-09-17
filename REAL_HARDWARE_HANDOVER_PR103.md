# Real-hardware test requests — `claude/digital-twin-wifi-fram-persistence-fix` (PR #103)

Temporary file, same convention as `REAL_HARDWARE_HANDOVER.md`/`WP_RESTART_HANDOVER.md` before it:
delete once its findings have been either confirmed-and-migrated into `SPECIFICATION.md`/
`CLAUDE.md`/`BACKLOG.md`, or confirmed not to apply. Written by a session with **no real-hardware
access this conversation**, for a session that has (or will get) the project owner's go-ahead to
run against real hardware — see CLAUDE.md's standing gate ("A session needs the project owner's
go-ahead, given directly in that session's own conversation, before running anything against real
hardware"). Nothing in this file authorizes skipping that gate.

## Context: why these measurements are being asked for

The code these requests are about now lives on the **base branch**
(`claude/automated-build-chain-nuzumw`), which this branch carries in full — its two commits were
cherry-picked there (`cd459bf`, `90aece7`), so this branch's own remaining diff is just this file.
Read the code on whichever branch you are checked out on; it is identical either way.

What that code does: it fixes two `digital-twin-e2e` staleness bugs surfaced by WP1's FRAM wiring,
then a real (not flaky) CI timeout on `dev`'s `PUT /status {"ResetErrors": true}`. WP1/WP2/WP3 grew
`dev`'s FRAM-backed error-log subset to 10+ entries (every `CFGMGR_<name>` logger, WIFI/NTP/
WEBSERVER/SYSTEM, SGP40/BMP3XX/SCD30, plus `dev`'s own two `uart_link` instances
`UART_init`/`UART_resp` that no other device carries — `devices/dev.toml`'s two
`driver = "uart_link"` blocks, each with its own `fram_target = "fram"`), and `_put_status()` resets
every one of them sequentially, each paying a real FRAM write. Fixed by giving that one call its own
client timeout in the CI suite (`scripts/_digital_twin_ci_suite.py`'s `_RESET_ERRORS_TIMEOUT_S`,
derived from the server's own 15s per-request cap), not by changing any runtime behavior.
Separately, this branch merged in the base branch's test-economy work
(`TEST_PARALLELISM`, heap size, per-device test splitting) — that part is host/CI-sandbox-only and
has **no real-hardware implication at all**; don't spend bench time on it (see "What NOT to do").

Everything below is about the FRAM-wiring side, all measured only against the digital twin's fake
FRAM chip (`digital_twin/_fram_chip.py`, zero real wire time) or reasoned about from code — none of
it has a real number yet.

## What to measure — in priority order

**Run these before any `tests_hardware/flash/` or `tests_hardware/bench/` isolated-driver run on the
same board.** All three requests below treat FRAM-backed error logs as evidence, and CLAUDE.md's
2026-09-11 caveat applies directly: an isolated-driver device script builds its own
`AsyFramManager` over the same chip, and the allocator is deterministic, so its first chunk *is*
production's first chunk — such a run overwrites the real logs, and one leaving a well-formed chunk
behind fabricates a plausible-looking entry that reads as genuine. If a flash/bench-tier suite has
already run against this board since its last normal boot, say so in the findings rather than
reporting the logs as real evidence; `tests_hardware/README.md` has the full mechanism.

### 1. Real wall-clock time for `PUT /status {"ResetErrors": true}` on `dev`

**This is the highest-value measurement on the list, and the bar is not a test timeout — it is the
product's own 15s ceiling.** The server aborts any request at `outer_cap_s = 15.0`
(`src/asy_webserver_service.py`), and the real web UI gives up at the same 15s
(`js/poll-manager.js`'s `DEFAULT_TIMEOUT_MS`). So a device whose reset sweep approaches 15s is
broken for its own operators, not merely slow in CI. The call already resets 10+ FRAM-backed sources
sequentially on `dev` and grows with every WP, and **no number for it has ever been taken on real
hardware** — the suite's client timeout is a backstop, not a budget, and nothing asserts elapsed
time (BACKLOG.md item 24). Measure, on `dev`'s own real entry point/config (not `wozi`'s hardcoded
pins on the `dev` board — CLAUDE.md's WoZi/dev policy, that combination "tests nothing at all"):

- End-to-end HTTP round-trip time for a real `PUT /status {"ResetErrors": true}` once the board has
  been running long enough to have accumulated at least one real entry in several of the FRAM-backed
  logs (a boot-time `CFGMGR_*` write is enough — doesn't need an actual fault injected).
- Confirm the response is `200` and every FRAM-backed counter (`GET /status`'s `errcount`, the full
  chunk layout in CLAUDE.md/SPECIFICATION.md Part A.7 — SGP40/BMP3XX/SCD30/SYSTEM/NEOPIXEL/NOTIFY/
  WIFI/DNSSRV/NTP/WEBSERVER, every `CFGMGR_<name>`, `UART_init`/`UART_resp`) actually reads back 0
  afterward — not just that the HTTP call itself returned in time.
- **Before this call**, per CLAUDE.md's standing rule: read `GET /status`'s FRAM-backed error logs
  first and record what's there — this call is destructive/irreversible for that evidence.
- Report the number against the 15s ceiling, not just as a duration: comfortably under (say < 5s)
  closes BACKLOG item 24; anything past roughly half of it makes the sequential-reset design a real
  item to fix at the source — batched or concurrent reset, or one shared chunk — rather than
  something to absorb with a larger timeout anywhere. Also worth having: the same number on one
  non-`dev` device, since `dev`'s two `uart_link` instances make it the worst case and a second
  point says how much of the cost is per-source.

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
