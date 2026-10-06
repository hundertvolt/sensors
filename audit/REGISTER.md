# Audit register

Temporary, like `PROJECT_AUDIT_PLAN.md`: removed with `audit/` at phase D. Plan 4.5 defines its fields, plan 4.7 the
lease and resumption procedure.

## Header

| field | value |
|---|---|
| lease | session `01BWfjT6GSD7bxCP57j86vB8` (https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8), since 2026-10-06 |
| released | — |
| audit branch | `claude/whole-project-audit-plan` (PR https://github.com/hundertvolt/sensors/pull/107) |
| go-ahead | OR145 (plan 3.2), 2026-10-06: implementation up to the first required real-hardware step |
| planning baseline | `4dc80ef` |
| audit baseline | `798e5a7` (`origin/main` at the go-ahead; already an ancestor of the audit branch, so anchors resolve at the branch head and only BACKLOG.md lines from :350 on move by +1) |
| current phase | B0 (unit U0) |
| work order | `audit/order/WORK_ORDER.md` (1909 changes, 6571 steps, 0 violations) |

## Unit table

| unit | scope | state | commit |
|---|---|---|---|
| U0 | B0 ENV: baseline, apparatus, prevention rules, B0 doc pass | not started | — |
| U0R | dependency refresh after the baseline | not started | — |
| U1 | legacy move to `legacy/` | not started | — |
| U2 | error-number catalog | not started | — |
| U3 | central log-repeat rule, one entry per event | not started | — |
| U4 | compare-before-write primitive, SCD30 onto it | not started | — |
| U5 | config objects and `max-args` | not started | — |
| U6 | one-source website definitions | not started | — |
| U7 | tier ladder and runner summary block | not started | — |
| U8 | `@tunable` scheme | not started | — |
| U8C | `@tunable` classification of tests | not started | — |
| U8C2 | search gaps of the test-tier classification | not started | — |
| U9 | LED pilot | not started | — |
| U10 | XCUT: system-wide contracts | not started | — |
| U11 | CORE | not started | — |
| U12 | ALGO | not started | — |
| U13 | BUS | not started | — |
| U14 | PLAT | not started | — |
| U15 | SENS | not started | — |
| U16 | STOR | not started | — |
| U17 | UART protocol | not started | — |
| U18 | NET | not started | — |
| U19 | REST | not started | — |
| U20 | GEN | not started | — |
| U21 | TOOL | not started | — |
| U22 | LED re-check | not started | — |
| U23 | WEB | not started | — |
| U24 | TEST | not started | — |
| U25 | TWIN | not started | — |
| U26 | HW levels L3/L4 | not started | — |
| U27 | SCR | not started | — |
| U28 | CI | not started | — |
| U29 | SEC | not started | — |
| U30 | MEM | not started | — |
| U31 | PERF | not started | — |
| U32 | PAR | not started | — |
| U33 | DOC | not started | — |
| U34 | LIC | not started | — |
| U35 | B3 test campaign | not started | — |
| U36 | B4 docs pass | not started | — |
| U37 | B5 close of execution | not started | — |
| C | hardware rounds (own go-ahead per session) | not started | — |
| D | close: plan and audit/ removed, one merge into main | not started | — |

## Non-interference (A.U0.04)

Applied from the first executing agent on:

- One worktree per executing agent (`git worktree add`); auditors and verifiers never write in the lead's checkout.
  Implementation agents work on disjoint files only.
- Every port-binding command (`scripts/test.sh`, `npm test`, twin runs, coverage) runs under
  `flock /tmp/sensors-audit-ports.lock` until U0 proves network-namespace isolation (M.PROC.003 (5a)); firmware builds
  under `flock /tmp/sensors-audit-toolchain.lock`. Isolation proven 2026-10-06 (U0 record (5a)): from then on each
  port-binding command runs in its own network namespace (`unshare -n`, `lo` up) instead of taking the ports lock, and
  parallel twin runs each get their own worktree, since the twin keeps its state in the tree.
- Every firmware build cleans the shared `mpy-cross/build`, so builds and `setup_toolchain.py test` run under the toolchain
  lock; `test` also rebuilds the shared `build-standard` Unix port, so it runs only while no suite or twin is running (learned 2026-10-06:
  the baseline harness, started before the lock existed, built unlocked over a gate's build and broke both; both re-ran
  alone and passed). A private toolchain copy (with its own `setcap`) only when the shared
  one is locked longer than the agent can wait, never by default.
- Before a rerun, the twin's FRAM log is read; `digital_twin/fram_state.json`, `digital_twin/scd30_state.json`,
  `digital_twin_ci_logs/`, `htmlcov*/`, `coverage*.xml` and failed-run output move to `audit/archive/<UTC timestamp>/`
  (the last 3 kept). Only pure scratch is deleted; evidence is moved, never deleted.
- Fault planting and repeat runs are budgeted first, run on tmpfs, at most about 20 repeats, as confirmation only. A
  timing failure under contention stays unconfirmed until reproduced alone. A retry is never a fix (OR37.a (2)).
- Worktrees and scratch branches go when their unit closes.
- Every unit closes only after the silent-failure scan (`audit/sweeps/silent_failure_scan.md`, OR147) has run over its
  changes and swept each class it found project-wide, in every operating mode the changes take part in (boot, reset
  countdown, flash and FRAM writes, network, calibration, recovery, reconfiguration, load; OR148); the result is in the
  unit's record.

## Unreachable sources (OR4.a)

| source | reason | needed for |
|---|---|---|
| `deb.debian.org`, `security.debian.org` (HTTP and HTTPS) | egress policy: 403 at the proxy, 2026-10-06 | the trixie leg of CLAUDE.md's chroot recipe (M.PROC.009, families (a) and (e)); owed in BACKLOG's chroot list |

## Owner-review list (OR2.c)

Decisions taken on the owner's behalf during execution, for the B5 review.

| unit | decision | reasoning |
|---|---|---|
| U9 | SF-B2: the notification coordinator recognises the default (no-LED) sink instead of the sink changing its `False` return | keeps the sink's documented contract unchanged; the more reversible of the two options |
| U18 | SF-M2-01: an empty SSID returns to hotspot mode directly instead of counting as a failure streak | keeps the unit reachable; the owner rule's "second STA failure streak" presupposes real STA attempts; reversible |
| U18, U22 | SF-M2-02: LED alerts gated on "clock set" rather than "synced" | the clock stays accurate long after a missed sync; the LED is the unit's only output |
| post-audit | SF-B16: no wire change for declined-vs-lost on the UART; recorded for C reconciliation | the wire format is frozen (owner, 2026-09-25) |

## Parked deltas (OR2.c, OR106.a)

Findings during execution that need a change outside the work order; each passes A-C as a delta before it is applied.

| unit | finding | state |
|---|---|---|
| U15 | SCD30 temperature offset truncated (`src/asy_scd30_driver.py` `int(offset * 100)`): one tick = 0.01 °C (Interface Description §1.4.7), so 4,585 of 65,536 float32 inputs write one tick low and read back 0.01 K under the PUT value. Upstream Adafruit `3eb3b52` uses `round()`. Legacy deployed driver also truncates, so this is a D.1 flag (behaviour vs field behaviour). Found by the refresh, family (g). | parked; A-C delta before U15 |
| U18 | NTP accepts 44-47-byte replies (`src/asy_ntp_client.py`, no length check; `tests/test_asy_ntp_client.py` pins `_truncated(44)` as accepted). The NTP header is a fixed 48 bytes; upstream micropython-lib `9ec1830` rejects shorter replies. Receiver-side tightening. Found by the refresh, family (g). | parked; A-C delta before U18 |
| U18 | NTP accepts a zero transmit timestamp: raw 0 maps through the era step to 2036-02-07, inside the 2025-2100 plausibility window, so a malformed reply with stratum ≠ 0 sets the RTC to 2036. Upstream micropython-lib `5139530` rejects it. Receiver-side tightening. Found by the refresh, family (g). | parked; A-C delta before U18 |
| U36 | CLAUDE.md's chroot recipe runs `scripts/test.sh` without Node, while `tests_scripts/test_live_twin_ceiling_parser.py` asserts `node` on `PATH` (a hard prerequisite, A.U24.52): in a bare noble chroot the recipe as written fails 10 tests (found in U0's family (a) chroot leg, 2026-10-06; the same at the baseline, which carries the test). The recipe needs `env --tier generic` (or a pinned Node) before `test.sh`; it lands with the recipe's move and form (A.U1.05, U36). | parked |
| U36 | The U0 citation, vocabulary and import-placement checks read `git ls-files`, so the recipe's `cp -r` of a git worktree (whose `.git` is a file pointing outside the chroot) fails them; the recipe needs a real clone or `git init` over the copy. Found by U0's tooling lane, 2026-10-06. | parked |
| U13 | Owner requirement OR146 (2026-10-06): every receive overrun reaches the sender as a failed transaction, reliably with interrupts off. Ring lap already covered; UARTRSR OE (hardware FIFO overrun) added as M.SRC_NET.221 (6) with L1/twin/bench tests; changelog Class A. | folded (A-C: no conflict with J.7, F.5.8/F.5.9 or the raise contract; the overrun reports through the existing sentinel/resync path) |
| U16 | SF-B1 (first silent-failure pass, verified by lead against `asy_fram_manager.py:645-680`, `print_log.py:224-280`): FRAM chunk identity is address + CRC only; equal-size logger chunks (30 B each) shift by exactly one chunk when a firmware change adds or removes an owner ahead of them, so a module loads a neighbour's history with a valid CRC and `/status` mislabels it. M_SPEC C.7 pitfall text and A.U16.03 (3-byte rotation) assume such a chunk reads invalid. Minimal fix (OR149): seed each chunk's existing CRC (`crc_checks.py` `add`/`check` already take `init`) with a per-owner value; CRC linearity makes a foreign equal-length chunk fail deterministically (residual = Δinit·x^(8n) mod g, non-zero for Δ ≠ 0 since g has a constant term), so the existing blank path handles it with no new bytes. A test pins the seeds distinct across every chunk-owner name in the project; A.U16.03 gains an aligned-shift case; covers every chunk type. Mode: after a firmware change. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U9, U22 | SF-B2 (verified by lead, `asy_notification_service.py:223-228`): `_trigger_signal()` ignores `request_signal()`'s bool, so a dropped LED flash still reports `Triggered` and is never counted. Fix: test the bool, warn and count. `_DefaultSignalSink` returns `False` by design: conservative choice is the coordinator knowing it holds the default sink (no semantic change to the sink); on the owner-review list. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U11, U20 | SF-B3 (agent, littlefs cited `lfs2.c:3146-3149, 3250-3253`): a PUT answered "Valid" whose deferred flush fails runs from RAM and reverts at reboot; persisted as errno 14 but `ConfigFaults` lists boot faults only. Fix: per-store `unpersisted` flag reported beside `ConfigFaults`, cleared by the next good flush; no retry (C.7.3). U11 first checks whether the persisted errno 14 in `errcount` already makes it visible enough (then no change). Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U11 | SF-B4 (verified by lead, `system_service.py:354-374`, generated `_system_cmd_callback`): `mempause` answers "Valid" when the auto-unpause timer failed and the pause was aborted; M.SRC_CORE.012 still ends `return True`. Fix: abort branch returns `False` (API "Failed") and persists `_ERR_TIMER`. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U11 | SF-B5 (agent): a failed uptime tick-timer arm leaves `BootSignature` null for the whole boot, console only, never retried. Fix: use the arm bool, persist once, re-arm from `status_counter()` on a bounded sleep (NTP pattern, M.SRC_NET.054). Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U18 | SF-B6 (agent): a failed hotspot `status("stations")` query returns `[]` and starts the hotspot shutdown timer. Fix: `None` = unknown, timer state unchanged, one warning per failure run. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U18 | SF-B7 (agent): WLAN observation failures read as "disconnected" and reset `WifiUptime`. Fix: an unknown state distinct from disconnected; counted. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U19, U23 | SF-B8 (agent): a config GET after a chip-read failure returns `null` fields indistinguishable from "not set" (SCD30, BMP3XX, ISL29125). Fix: the existing `unavailable` marker for read failures; page shows it. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U15 | SF-B9 (agent; datasheet point closed by lead: `por_detected`, EVENT 0x10 bit 0, clear-on-read, BMP384 ds003 4.3.7, BMP388 ds001, BMP390 ds002): BMP3XX settings silently revert after a sensor self-reset; the driver never reads EVENT. Fix: read `por_detected` each cycle (or shadow-compare), re-apply settings, count (ISL29125 precedent M.SRC_SENS.082). Mode: peripheral self-reset. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U15 | SF-B10 (agent): SCD30 "not ready" read re-stores cached values with a fresh timestamp. The restamp is the owner's named exception (owner, 2026-07-22, `110f3db`; by-mode M3, C95), so this is a SPEC D.1 flag-first item, not a change: U15 records it as a fine-tuning question on the owner-review list, and only the stuck-RDY visibility (SF-A04's counter) is applied. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U15 | SF-B11 (agent): ISL29125 calibration outcome (timed out / converged) is console-only. Fix: result readable on the API and a timed-out run logged. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U16, U11 | SF-B12 (agent): FRAM allocator full or history allocation failed leaves the module RAM-only, console or silent. Fix: persisted in a module that has storage (SYSTEM) or reported in `/status`; counted. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U25 | SF-B13 (agent): a malformed or truncated twin FRAM state file silently becomes a blank chip, and the save is not atomic. Fix: say so on load; write-temp-then-rename. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U11, U23 | SF-B14 (agent): `ErrCount` saturates at 65535 silently; with the newest-entry rule repeats stop showing. Fix (minimal): none in firmware if the page renders the cap value as "65535+"; keep K.28's bound. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U18, U28 | SF-B15 (agent): UDP datagram truncation (`asy_udp_socket.py:168-180`) documented, not detected. Fix: receive into buffer+1 and treat a full buffer as truncated, counted. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| post-audit (C reconciliation) | SF-B16 (agent): the UART initiator cannot tell a declined command from a lost frame; a distinction needs a wire change, which the owner's wire freeze excludes (owner, 2026-09-25). Recorded for the C-reconciliation list; on the owner-review list. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U22 | SF-B17 (agent): the notification goes silently inactive while its producer sensor or NTP is down. Fix: an explicit inactive state with its reason on `/measurements`. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U20, U21 | SF-B18 (agent, low): generator writes are not atomic; a killed run leaves partial outputs. Fix: write-temp-then-rename. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_B_own_code.md`. | parked, to A-C |
| U13 | SF-A01 (verified by lead: SDK `i2c.c:229-231` returns the short byte count on a data NACK; `extmod/machine_i2c.c:640-648` `writeto_mem()` discards it; `writeto()` returns it): an I2C data-byte NACK is accepted as a full write, so an SCD30 NVM PUT or a BMP3XX/ISL29125 config write answers "Valid" while the chip did not take it. Minimal fix: at the one choke point use `writeto()` with a preassembled buffer and test count == len, else `OSError(EIO)`. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U13 | SF-A02 (verified by lead: `extmod/machine_i2c.c:556-560` read_mem returns 0 on a register-byte NACK, `:625` raises only on < 0; rp2 has no WRITE1 path): `readfrom_mem_into()` returns silently with the buffer untouched, so stale scratch bytes decode as a fresh reading (BMP3XX on dev/wozi, ISL29125 on dev). Minimal fix: an ordering change, `writeto(reg, stop=False)` with the count tested, then `readfrom_into()`. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U13 | SF-A03 (agent): the I2C abort reason is folded into one `EIO` below us (`i2c.c:180-186`, rp2 `machine_i2c.c:150-155`). No code; one SPEC sentence that the cause is not readable. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U15 | SF-A04 = SF-B10 (SCD30 stale store with fresh timestamp): minimal fix tests the `new_data` bool M.SRC_SENS.057 already returns in the store; one counter for a stuck-high RDY only because nothing else tells a late edge from a line that never clears. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U15 | SF-A05 = SF-B9 plus `ERR_REG.fatal_err`: one EVENT read per cycle (clear-on-read), the existing re-apply path on `por_detected`; read ERR_REG in the same burst if contiguous. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U13 | SF-A06 (agent): M.SRC_NET.221 (6) reads UARTRSR for OE only; FE and BE in the same sticky register are ignored and left to the CRC (dev). Minimal fix: widen the tested mask to OE|FE|BE; the frame fails the same way. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U13, U31 | SF-A07 (agent, not confirmed): a TX frame longer than the 32-byte FIFO can stall on the wire for up to one W25Q16JV sector erase (max 400 ms) while flash is written. No code unless the timing-budget row shows the peer's deadline crossed; add the row. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U18 | SF-A08 (agent: `modlwip.c:299, 456-461`, 4 queued datagrams per UDP socket, the rest dropped untraceably): captive DNS loses queries in hotspot mode under bursts. Minimal fix: drain the queue per wake before sleeping; SPEC sentence on the bound. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U18 | SF-A09 (agent: `dhcpserver.h:32`, `dhcpserver.c:234-236`): the AP DHCP pool has 8 leases of 24 h; when exhausted, new clients are ignored. No code; SPEC sentence (hotspot use is one configuring client). Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U11 | SF-A10 (agent: `modmachine.c:74-89`): `reset_cause()` merges commanded reset with watchdog starvation and RUN pin with brown-out; the hardware keeps them (watchdog REASON TIMER/FORCE, CHIP_RESET HAD_POR/HAD_RUN). Minimal fix: two `machine.mem32` reads in `begin_boot()` stored with the decoded cause. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U11 | SF-A11 (agent: `mpirq.c:105`, soft-Timer fire dropped when the scheduler queue is full): the storage auto-unpause is one soft one-shot; a dropped fire leaves FRAM paused until reboot. Minimal fix: store the unpause deadline (`ticks_add`) and test it on a tick that already runs, removing the one-shot. Pairs with SF-B4. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U18, U30 | SF-A12 (agent, class 4): the UDP socket wrapper swallows `MemoryError` and returns None without `str(e)`, invisible to the four memory gates. Minimal fix: log `str(e)` (or let it propagate per the memory rule). Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U20 | SF-A14 (agent: `asyncio/core.py:154, 194`): a REPL Ctrl-C ends the whole event loop; a pending config flush is lost and the reset reads as a watchdog reset (bench only). Minimal fix: one `write_reset_record()` in the boot entry's exit path. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| Phase C (hardware) | SF-A open points, not decidable from source: what CYW43 firmware drops during a 400 ms interrupts-off flash stall; whether DMA reads update UARTRSR like CPU reads (matters to M.SRC_NET.221 (6)); whether `mem_backup` survives a RUN-pin reset; SCD30 after a partly written register pointer and after an NVM write cut by power loss; whether a MISO pull-up on the FRAM breakout defeats the write-enable check. Each becomes a bench check in the hardware phase. Full entry: `audit/sweeps/scan_runs/20261006_first_pass_A_platform.md`. | parked, to A-C |
| U18, U20 | SF-M2-01 (verified by lead, `asy_wifi_service.py:441-443, 476-489`): with an empty SSID (factory state or reset to defaults), `_attempt_sta_connect()` sets the failure counter to the hotspot limit without any STA attempt; after the hotspot has run once, that registers as the second failure streak and deactivates WLAN until a power cycle, e.g. after a Hostname or Country PUT answered "Valid" from the hotspot page. The owner-confirmed rule (SPEC A.4: deactivation after a second STA failure streak) assumes real STA attempts. Minimal fix: the empty-SSID branch returns to hotspot mode directly instead of faking a streak; also closes an unconfigured unit going dark after one unattended hotspot window (inventory C69). On the owner-review list. The router-down variant is the owner rule itself and stays. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M2_network_rest.md`. | parked, to A-C |
| U18, U22 | SF-M2-02 (agent): side effect of planned M.SRC_NET.057 (NTP staleness reachable): `cettime()` answers only while `Synced`, so 3x the NTP interval (36 h default) after the last sync every LED alert stops though the clock is still good, and the LED looks like "air is fine". Minimal fix: gate `cettime()` on the one-way "clock set" state (`utc_now() is not None`). Fine-tuning of an owner-reviewed change; on the owner-review list. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M2_network_rest.md`. | parked, to A-C |
| U18 | SF-M2-03 (agent): the fallback to hotspot, the permanent deactivation, and a connect stuck in CONNECTING or waiting for an IP leave nothing in FRAM. Minimal fix: three persisted warnings on the existing code paths (newest-entry rule). Full entry: `audit/sweeps/scan_runs/20261006_bymode_M2_network_rest.md`. | parked, to A-C |
| U18, U22 | SF-M2-04 (agent): a phone joined to the hotspot holds the unit off the home LAN indefinitely and the LED looks like normal STA. Legacy behaviour, not changed. Minimal fix: a distinct LED pattern through the planned shared flash task; whether to bound the hotspot hold is an owner question (BACKLOG owner-question list). Full entry: `audit/sweeps/scan_runs/20261006_bymode_M2_network_rest.md`. | parked, to A-C |
| U19 | SF-M2-05 (agent, low): Microdot mutes ECONNRESET/EPIPE in `Response.write()`, so `HTTPDropped` misses a client gone mid-response. Minimal fix: `_TimeoutStreamProxy.awrite()` sets the existing `peer_gone` flag on `OSError`, as reads do. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M2_network_rest.md`. | parked, to A-C |
| U23 | SF-M2-06 (agent, low): settings sections load once; a toggle or dropdown equal to the stale value is left out of the PUT while the device holds another value. Minimal fix: refresh the section before reading the form on Apply. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M2_network_rest.md`. | parked, to A-C |
| U16 | SF-M1-02 (work-order defect, verified by lead in M.SRC_SENS.063's merged text): the "otherwise" branch tests `age < 0 or age > …` when `age` can still be `None` (an undated backup, or the NTP wait ended unsynced, `_voc_init` at 0); `None < 0` raises `TypeError` in MicroPython, so the SGP40 task dies and restarts until the supervisor reboots, on every device for as long as NTP is unreachable. HEAD does not have this. Fix in the M text before U16: guard the bound with `age is not None and (...)`, plus a test with an undated backup after the wait expires. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M1_lifecycle_storage.md`. | parked, to A-C |
| U11 | SF-M1-01 (agent): the stock frozen `_boot.py` reformats the filesystem silently when littlefs fails to mount; the unit returns with factory config (WiFi to hotspot) and nothing records why. Minimal fix: M.SRC_CORE.043's absent-file console line becomes a persisted warning in the store's own logger. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M1_lifecycle_storage.md`. | parked, to A-C |
| U16 | SF-M1-03 (agent, extends SF-B12): a logger whose FRAM store reads unreadable at setup runs RAM-only for the boot with a console line only. Minimal fix: SF-B12's report covers this branch. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M1_lifecycle_storage.md`. | parked, to A-C |
| U11 | SF-M1-07 (agent, extends SF-B3): a failed create write in `ConfigManager.setup()` leaves `ConfigFaults` empty. Minimal fix: SF-B3's `unpersisted` flag set on that path too. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M1_lifecycle_storage.md`. | parked, to A-C |
| U11 | SF-M1-04 (agent, low): a config path that is a directory makes the store invalid but is not listed in `ConfigFaults` (manual action only). Minimal fix: `faulted = True` in that branch. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M1_lifecycle_storage.md`. | parked, to A-C |
| U11 | SF-M1-06 (agent, extends SF-B5): with the uptime tick timer dead, uptime may go unread past the 2^29 ms `ticks_diff()` limit, corrupting uptime and `HTTPDropped`. Minimal fix: SF-B5's re-arm loop reads uptime on each pass. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M1_lifecycle_storage.md`. | parked, to A-C |
| Phase C (hardware) | SF-M1-05 (agent, not confirmable from source): the RP2040 bootrom probably overwrites the reset record for the bootloader command, so reset reason 4 would never show. Bench check plus one SPEC F.5.4 sentence. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M1_lifecycle_storage.md`. | parked, to A-C |
| U22, U15 | SF-M3-01 (agent): after the SCD30 stops measuring with its task alive (ContMeas off, RDY stuck low), notifications and SGP40 compensation keep using its last sample as current; likewise SGP40's last VOC while it skips. Keep-last-good means never `None`; all six devices. Minimal fix: a consumer treats a sample whose `TS` is older than a fixed limit as unavailable (the owner rule "skip if unavailable" then applies). Full entry: `audit/sweeps/scan_runs/20261006_bymode_M3_peripherals.md`. | parked, to A-C |
| U16, U30 | SF-M3-06 (agent, same class as SF-A12): `LockableBuffer`/`RegionBuffer` (`base_classes.py:60-72`) swallow `MemoryError` without its text, invisible to the four memory gates; SGP40 then reports a heap failure as "No backup found". Minimal fix: log `str(e)` once; SGP40 tests for the `None` buffer. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M3_peripherals.md`. | parked, to A-C |
| U15 | SF-M3-02 (agent): an out-of-datasheet-range reading is logged as a plain read failure (errno 11) and escalates toward reboot like a bus fault (BMP3XX at HEAD, SCD30 gate added by the work order). Minimal fix: a distinct catalog code; whether the escalation should differ is on the owner-review list. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M3_peripherals.md`. | parked, to A-C |
| Phase C (hardware), U15 | SF-M3-03 (agent, unconfirmed): the SCD30 soft reset at every boot, task restart and recovery rung is equivalent to power-up per the Interface Description; a power loss aborts ASC's first 7-day search; whether a soft reset does is not stated. SPEC sentence now; bench check; whether the boot reset is needed goes to the owner-review list. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M3_peripherals.md`. | parked, to A-C |
| U15 | SF-M3-04 (agent, dev): ISL29125 compares its shadow config with the chip only after a failed write or on a GET; a corrupted CONFIG byte goes undetected on a headless unit. Minimal fix: run the existing snapshot comparison every read cycle. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M3_peripherals.md`. | parked, to A-C |
| U15 | SF-M3-05 (agent): every SGP40 task restart restores the FRAM backup over the live algorithm state; with BackupPeriod/BackupMaxAge 0 it can be days old. Minimal fix: skip the restore when the algorithm has already been fed since boot; check against the legacy driver first (CLAUDE.md field-behaviour rule). Full entry: `audit/sweeps/scan_runs/20261006_bymode_M3_peripherals.md`. | parked, to A-C |
| U17 | SF-M3-07 (agent, dev): `ResetErrors` zeroes the UART `_valid_frames`, so the "link unintelligible" diagnostic (E32) can fire on a link that worked for days. Minimal fix: leave that counter out of the reset. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M3_peripherals.md`. | parked, to A-C |
| U26 | SF-M3-08 (agent): RP2040-E15, the bench Pi 4's VL805 USB host can hang the RP2040 USB device controller; nothing in the repo names it. Minimal fix: a README prerequisite naming the VL805 firmware version and a version check in the bench preflight. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M3_peripherals.md`. | parked, to A-C |
| U15, U22 | SF-M3-09 (agent): SGP40 and WS2812 self-resets have no detector; a cold SGP40 restart can spike the VOC index into warn_voc, a blanked pixel leaves the WiFi overlay wrong until the next flash. Minimal fix: one SPEC sentence for the SGP40; refresh the overlay once per notification cycle. Full entry: `audit/sweeps/scan_runs/20261006_bymode_M3_peripherals.md`. | parked, to A-C |

## Findings

| ID | title | area | severity | status |
|---|---|---|---|---|
| X01 | `tests/test_uart_comm_hazard.py` `_hammer_faulted` (`:1077`): the per-failure retention bound (< 16 B) failed once in family (b)'s gate at `-1` (704 B over 30 failures = 23.5 B) on a 4-core host carrying two gates, twelve twins and the baseline; the test and everything it imports are byte-identical to the baseline; 10/10 repeats under the same load pass, and the gate's `-1` row re-run alone passes (87/87). Not reproduced alone; the bound's load sensitivity goes to U30's restructure of this measurement (`M.TEST_UNIT`, `_hammer_faulted.hammer`) | tests | low | open |
