DR8 decision review, written by the part (2026-10-28 11:50 UTC)

# DR8: agent-tagged lines outside `audit/` and SPECIFICATION.md Part N, at `11b66cd8`

Input: the 237 lines of `inputs/SPEC_11b66cd8.md` before line 11919 that carry "(agent", and the 220 lines that
`git grep -n '(agent' 11b66cd8 -- ':!arduino' ':!audit' ':!SPECIFICATION.md'` returns. Read-only; nothing ran.
Tracking was matched by words against `inputs/REGISTER_11b66cd8.md` lines 100-812 and `inputs/DR1_review_decisions.tsv`.

## 1. Counts

457 tagged lines: **48 facts**, **409 decisions**.

| verdict | n | meaning here |
|---|---|---|
| SAME | 246 | I would decide the same today |
| TRACKED | 81 | a register row or review item holds it; full verdict left to that part (my lean noted) |
| OWN | 61 | the owner's words cover it |
| DIFF | 10 | I would decide differently now |
| OBS | 7 | answers a question only a removed mechanism raises |
| FORM | 3 | right decision, larger form than needed |
| SUP | 1 | superseded by a later owner answer |
| CHECK | 0 | none needs a run to settle (the suspicious ones are already tracked, e.g. the lost-FRAM chain under REG:795) |

Per topic (decisions only):

| topic | n | DIFF | OBS | FORM | OWN | SUP | TRACKED | SAME |
|---|---|---|---|---|---|---|---|---|
| twin | 78 | 0 | 1 | 0 | 3 | 0 | 4 | 70 |
| tests-hardware | 40 | 0 | 1 | 0 | 2 | 0 | 10 | 27 |
| tests-unit | 37 | 0 | 0 | 0 | 2 | 0 | 6 | 29 |
| ci-tooling | 37 | 2 | 0 | 0 | 1 | 0 | 9 | 25 |
| uart | 31 | 2 | 0 | 0 | 2 | 0 | 9 | 18 |
| website | 17 | 0 | 0 | 0 | 6 | 0 | 2 | 9 |
| buildgen-toml | 16 | 0 | 0 | 1 | 4 | 0 | 5 | 6 |
| wifi | 14 | 0 | 0 | 0 | 9 | 0 | 2 | 3 |
| webserver-rest | 14 | 0 | 0 | 0 | 3 | 0 | 1 | 10 |
| driver-sgp40 | 14 | 1 | 1 | 0 | 3 | 0 | 3 | 6 |
| supervisor-reset-watchdog | 11 | 1 | 0 | 0 | 1 | 0 | 6 | 3 |
| driver-isl29125 | 11 | 2 | 0 | 0 | 0 | 0 | 0 | 9 |
| storage-fram | 10 | 0 | 0 | 0 | 4 | 0 | 3 | 3 |
| timing-waits | 9 | 0 | 0 | 1 | 1 | 0 | 4 | 3 |
| ntp-dns | 8 | 0 | 0 | 0 | 4 | 1 | 3 | 0 |
| driver-scd30 | 8 | 0 | 0 | 0 | 3 | 0 | 1 | 4 |
| core-logging | 8 | 0 | 1 | 1 | 3 | 0 | 0 | 3 |
| led-notification | 7 | 2 | 2 | 0 | 0 | 0 | 3 | 0 |
| process | 6 | 0 | 0 | 0 | 1 | 0 | 1 | 4 |
| memory-gc | 6 | 0 | 1 | 0 | 1 | 0 | 3 | 1 |
| config | 6 | 0 | 0 | 0 | 0 | 0 | 1 | 5 |
| bus-i2c-spi | 6 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| security | 5 | 0 | 0 | 0 | 4 | 0 | 1 | 0 |
| release | 2 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| licensing | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |
| generated-code | 2 | 0 | 0 | 0 | 1 | 0 | 0 | 1 |
| driver-bmp3xx | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| docs-records | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |

Facts (no verdict): SPEC:340, 627, 669, 1174, 1347, 1383, 2474, 2987, 3148, 3152, 4034, 4059, 4816, 5096, 5427, 5566,
5579, 6415, 6510, 6840, 6841, 7454, 8442, 9244, 9356, 9540, 9690, 10094, 11658, 11893; BACKLOG.md:51, :1068;
CLAUDE.md:123, :525 (the "(agent, YYYY-MM-DD)" template inside the owner's record rule), :605 (the agent's measured
question; the decision is the owner's); HEAP_FRAGMENTATION_MEASUREMENTS.md:369; PROJECT_AUDIT_PLAN.md:413, :435 (label
results); UART_C_PORT_CHANGELOG.md:218; buildgen/buildspec.py:3; digital_twin/README.md:548, :557;
scripts/setup_cross_browser_toolchain.sh:33; tests_hardware/README.md:103, :116; tests_scripts/test_decision_vocabulary.py:103,
test_micropython_overrides.py:1287, test_tunables_register.py:367 (fixture strings).

Checks made on the whole set:
- **"owner-reviewed" tags.** 17 tagged lines claim "owner-reviewed, 2026-10-01/02". Each maps to an answered review item
  (ok, or "Fine, and ..."): static-no-cache, c-stack-reboot, timestamps-before-ntp, website-accessibility,
  apply-failure-marks-fields, website-display-details, scd30-calibration-readiness, reflash-runbook-erase,
  licence-notices, ntp-sync-last, dns-fallback-setting, ntp-synced-goes-stale, heap-floors-kept, bench-sudo-checked.
  No misattribution found.
- **"(owner, 2026-10-05)" on agent text** (SPEC:3029, :6844, :7407) traces to OR141: "do all as you suggested".
- **The catalog's "Retired numbers are never reused"** (SPEC:3653) carries no tag, so it is outside this set; SCAN2 s8
  check 5 already records it as agent text with no owner words.

## 2. DIFF rows

**SPEC:1898 — the apt mirror check's per-job required rate** (agent, 2026-10-28). Topic ci-tooling; L8, misfit.
- As taken: before each apt install, CI probes the runner's Ubuntu mirrors and drops those under a rate derived from the
  bytes left and the fetching step's bound.
- New answer: no mirror machinery. A slow azure mirror is a proven external issue: leave it, and re-run the job.
- Basis: the owner, 2026-10-27 (about 16:48, on CI): "Don't care about proven external issues so far." Also the owner,
  2026-10-22/23: "Don't worry too much about the CI on Git for the moment. There are known large outages ... It's not
  Git and it's not the code." The text calls it external itself (actions/runner-images#14823). It landed after those words:
  `39fc5cf8` (2026-10-27 23:40 UTC) and `235e4f7f` (2026-10-28 00:47 UTC).
- Change: CI only, no device code. Goes: `.github/actions/apt-cache-restore`, `.github/actions/apt-cache-save`,
  `scripts/ci_apt_cache.py`, `tests_scripts/test_ci_apt_cache.py`, B.10.1's paragraph and the `ci.apt_*` Part N rows.

**SPEC:1923 — "Integrity stays with Ubuntu's signature"** (agent, 2026-10-27). Topic ci-tooling; L8, misfit.
- As taken: the archive cache's copy-in checks each archive against the SHA-256 of the fresh index.
- New answer and basis: as SPEC:1898. It is part of the same mechanism, and it goes with it.

**SPEC:422 — the notification's `State` codes** (agent, 2026-10-06). Topic led-notification; L2/L6, misfit.
- As taken: `/status` notification `State` reports why a cycle evaluated nothing, or only part.
- New answer: no `State` key. `Triggered` and `TS` (pre-audit) and E15 stay.
- Basis: S2-G4X-2. Pre-audit there is no state at all (grep). The generated `/status` key is the only reader. No owner
  decision names these codes: state-code-values covers the SGP40 and ISL29125 fields only. NT-2 is H.
- Change: about 25 src lines, the key in 6 generated modules, the catalog's NotifyState table and the definitions rows.

**SPEC:4352 — the uptime tick's 1 s sleep fallback** (agent, 2026-10-06). Topic supervisor-reset-watchdog; L2, misfit.
- As taken: when the tick timer cannot be armed, the uptime tick falls back to 1 s sleeps, persists TIMER once per task
  run and re-arms on every pass.
- New answer: the pre-audit catch-and-print at the arm, and nothing more.
- Basis:
  - The trigger is refuted: A.md V6 counts at most 12 Timers against a pool of 16 (S2-G1-7, A-S20 H).
  - The owner, 2026-10-21, Q2 (REG:783): "a - if the shortage came each boot, this would be a malformed firmware, which
    would already be seen in the tests - nothing which would happen by itself as a surprise."
- Change: part of S2-G1-7's ~70 lines: `_tick_failed`, the fallback loop, `start_uptime_timer()`'s wake, and the E17
  use here.

**SPEC:5585 — "A re-check that only narrows an `Optional` for the type checker stays, with a comment saying so"**
(agent, 2026-09-30). Topic uart (14 of the 20 sites); L2, misfit.
- As taken: a standing rule in E.5.1 that keeps run-time branches which no run can reach.
- New answer: a narrowing is written for the type checker only (a cast or a non-Optional attribute after construction).
  No run-time branch.
- Basis:
  - The owner, 2026-10-27: "catching errors which can only happen for the reason of unfulfilled typing are overkill".
  - The owner, 2026-10-27: "A strong hint for an unnecessary check is that it is proven to be fully covered by typing
    adherence alone, and that it is unreachable with today's code".
  - S2-G4-22: 20 such branches, each called unreachable by its own comment.
- Change: E.5.1's sentence; about 40 src lines (UART comm 8, UART driver 5, link 1, FRAM manager 4, SCD30 1,
  webserver 1).

**UART_C_PORT_CHANGELOG.md:213 — B89: six never-true checks kept, each with a comment** (agent). Topic uart; L2, misfit.
- New answer and basis: as SPEC:5585. The review item kept-branches covers two other branches (UDP POLLERR, the Wi-Fi LED
  narrowing), not these six.
- Change: the six branches. Class B in the changelog, no wire effect.

**SPEC:11606 — "A chip-setup failure at init runs the controller rung"** (agent, 2026-10-07). Topic driver-isl29125
(base reader); L3, misfit.
- New answer: a setup failure enters the normal ladder, mild rung first. The task end, the supervisor's restart and the
  reboot (whose construction clears every bus) carry it on.
- Basis: OR113 (owner, 2026-09-30): "try to recover mildly, but escalating up to a full bus reset is absolutely allowed
  if the mild measures don't work out". `_init_failed()` enters at the strongest rung first, and does so at every restart
  on a shared bus (S2-G1-4).
- Change: the 7-line `_init_failed()` and its 6 calls (~14 lines). Keep `_init_done()`'s `self._rungs = 0`.

**SPEC:11638 — ISL29125 divergence detection on every read cycle** (agent, 2026-10-06). Topic driver-isl29125; L2, misfit.
- As taken: a 3-byte shadow-vs-chip snapshot every cycle, logging W31 ISL_DIVERGED and re-applying.
- New answer: no per-cycle comparison.
- Basis:
  - C.md ISL-10 (H, FN8424): CONFIG changes without our write only through a reset or a brownout, and BOUTF already
    handles that.
  - The pre-audit failed-write path reconciles a partial write.
  - The divergence the bench once saw was a race, fixed at its root by moving the shadow mutation inside the session
    lock (BACKLOG.md:51ff).
- Change: ~9 lines, one bus read per cycle on a shared bus, W31, and REG:443's W/E pair allowance.

**src/asy_neopixel_driver.py:37 — the overlay rewritten at least every 300 s** (agent, 2026-10-06). Topic
led-notification; L2, misfit (M2).
- New answer: the pre-audit `await ...wait()`, with no periodic rewrite.
- Basis: REPORT s3: "It was hypothetical, and it created a real defect of its own: the lost shutdown cancel" (confirmed
  by the lead). C.md NP-5 is H. The owner, 2026-10-28: "hardcoded delay checks like this are a very bad, very awkward
  pattern".
- Change: −5 lines (REPORT s3); the `led.overlay_refresh_ms` tunable goes. SPEC:410 (below) goes with it.

**src/voc_algorithm.py:219 — 35 constants pre-converted once through `_f16()`** (agent, 2026-10-20). Topic
driver-sgp40; L5/L2, misfit.
- New answer: upstream's per-sample conversion, as the literal port has it.
- Basis:
  - The owner, OR109 (2026-09-29): "'temporary', that's the difference. ... If the VOC algorithms allocates and the
    allocation goes after it's done and gc can clean the mess up, everything is settled."
  - OR109.a (1): "No rework of the fix16 helpers".
  - C.md VOC-5 is H.
  - The literal-port rule is the owner's (OR141; SPEC:3029, SPEC:6844).
- Change: 35 instance attributes and about 40 call sites back to upstream's form.

## 3. OBS rows

| id | root it depends on (scan row) | topic |
|---|---|---|
| SPEC:373 | the SGP40 10,800 s compensation age check (S2-G1-18; SGP-2 H, DELAY): "no timestamp yet counts as current" is one of its clauses | driver-sgp40 |
| SPEC:420 | the notification's 10,800 s sample age check (S2-G1-18; NT-3 H) | led-notification |
| SPEC:7664 | the same age rule, "two sites do not yet make a shared helper" (S2-G1-18, S2-G4-10) | core-logging |
| SPEC:410 | the NeoPixel 300 s rewrite (C.md NP-5 H, cascade 17; REPORT s3): "a refresh never cuts into a ramp" exists only for the refresh | led-notification |
| SPEC:7680 | the memory-gate console lines (S2-G4-6, A-P11 C, P4): `console()`'s arity argument serves those lines only | memory-gc |
| SPEC:5878 | E.6.6 `timer-pool-under-graph`: its failed-arm paths rest on the refuted trigger (S2-G1-7) | tests-hardware |
| scripts/_digital_twin_scenarios.py:1663 | the escalation's 1200 ms entry bound (S2-G1-6; SCAN2 s7 item 4: goes) | twin |

## 4. FORM rows

| id | smaller form | scan row | topic |
|---|---|---|---|
| SPEC:3761 | a repeat during an in-flight `ResetErrors` needs no rule once resets run one at a time | A-P7 (X, implausible); REPORT s5 "overlapping error resets ... one at a time"; OR35.a "layered limits are overkill" | core-logging |
| SPEC:6763 | keep F.3's table as text; no test recomputing its code-derived rows | E.md tests_scripts "Excessive" (U31 added the timing budget); F.md "Docs became checked data" | timing-waits |
| buildgen/validate.py:1039 | refuse dev's UART values once, at construction as pre-audit, or at build, not both | S2-G4X-5; G3 Family A (UART bounds); SCAN2 pattern 4 | buildgen-toml |

## 5. OWN rows

- `SPEC:194` (storage-fram): chunk write order: block 1 status read first, non-idle copy first. Source: "Solutions you proposed agreed." (owner, 2026-10-22; REG:805). Built as the owner said; no gap found.
- `SPEC:198` (storage-fram): failed status read: block 1 first. Source: "Solutions you proposed agreed." (REG:805). Built as the owner said; no gap found.
- `SPEC:443` (wifi): empty SSID straight to hotspot. Source: Wi-Fi settled (owner 2026-10-28); REG:107. Built as the owner said; no gap found.
- `SPEC:449` (wifi): station-on-hotspot LED pattern. Source: Wi-Fi settled; REG:109. Built as the owner said; no gap found.
- `SPEC:486` (wifi): failed status read keeps last state, one WIFI warning. Source: Wi-Fi settled. Built as the owner said; no gap found.
- `SPEC:493` (wifi): DHCP lease limit accepted. Source: Wi-Fi settled. Built as the owner said; no gap found.
- `SPEC:1258` (webserver-rest): trace-before-close bound; SCAN2 s7 item 7 makes it obsolete on the refusal arm. Source: "Solutions you proposed agreed." (REG:805). Built as accepted. Gap to note: SCAN2 s7 item 7 sends the refusal arm back to close-then-trace, which makes this bound obsolete on that arm under the owner's 2026-10-28 background note; it stays on the other arms.
- `SPEC:1281` (webserver-rest): Cache-Control no-cache. Source: static-no-cache (ok). Built as the owner said; no gap found.
- `SPEC:1372` (security): mDNS accepted. Source: "Option 1, sign off A.11 as is" (owner, 2026-10-20; REG:710). Built as the owner said; no gap found.
- `SPEC:1373` (security): ICMP/IPv6 accepted. Source: REG:710. Built as the owner said; no gap found.
- `SPEC:1375` (security): DHCP server accepted. Source: REG:710. Built as the owner said; no gap found.
- `SPEC:1389` (security): new route joins A.11 in the same change, test-checked (F.md: a genuine contract check). Source: REG:710. Built as the owner said; no gap found.
- `SPEC:3029` (driver-sgp40): voc_algorithm literal-port exception. Source: OR141 "do all as you suggested" (owner, 2026-10-05). Gap: src/voc_algorithm.py:219 (VOC-5, DIFF) is a second, unnamed deviation from the literal port.
- `SPEC:3694` (wifi): refused period arm counts as failure (form only: S2-G1-7). Source: Wi-Fi settled. Form only: the refused-arm trigger is refuted (S2-G1-7, A.md V6), so the smallest form is the pre-audit catch; Wi-Fi is settled, so nothing else.
- `SPEC:3738` (wifi): persisted Wi-Fi entries. Source: Wi-Fi settled. Built as the owner said; no gap found.
- `SPEC:3843` (ntp-dns): no origin check. Source: ntp-no-origin-check (ok). Built as the owner said; no gap found.
- `SPEC:4054` (wifi): WifiService getter contract. Source: Wi-Fi settled. Built as the owner said; no gap found.
- `SPEC:5273` (tests-unit): driven-clock uptime proof. Source: driven-time-and-rtc-steps (ok). Built as the owner said; no gap found.
- `SPEC:6472` (supervisor-reset-watchdog): stack budget half the limit. Source: c-stack-reboot (ok: "at most half of the 7,936-byte stack"). Form only: SCAN2 s3 puts the C-stack check in the logger's _line() with 4 explicit calls and a Microdot hook (~118 lines go).
- `SPEC:6628` (wifi): failed RSSI read shows as a wrong RSSI. Source: Wi-Fi settled. Built as the owner said; no gap found.
- `SPEC:6791` (timing-waits): flash-program stall as accepted degradation. Source: owner 2026-10-22 "your suggested next steps are fine (go back to the single write)" (REG:799). Built as the owner said; no gap found.
- `SPEC:6844` (driver-sgp40): literal-port rule. Source: OR141 (owner, 2026-10-05). Same gap as SPEC:3029.
- `SPEC:7407` (ntp-dns): UDP idle poll 100 ms. Source: OR141 "do all as you suggested" (answering idle-poll-rate). Built as the owner said; no gap found.
- `SPEC:7658` (core-logging): utc_now None until NTP. Source: timestamps-before-ntp (ok). Built as the owner said; no gap found.
- `SPEC:7946` (website): accessibility baseline; Back built. Source: website-accessibility ("Fine, and make the "back" function of the browser work"). Back history built (PICTURE s5).
- `SPEC:8106` (website): Apply failure marks fields. Source: apply-failure-marks-fields (ok). Built as the owner said; no gap found.
- `SPEC:8172` (website): ContMeas mixed state. Source: website-display-details ("Fine, and ..."). Built as the owner said; no gap found.
- `SPEC:8254` (website): decimals from datasheet repeatability. Source: website-display-details ("Fine, and maintain a reasonable number of digits ..."). Follows the owner's words (counts derived from the source modules, website only); the counts (0-1 decimals) sit under the owner's example of 2-3, which reads as a limit.
- `SPEC:8272` (website): code tables beside descriptions. Source: state-code-values (ok); website-display-details. Built as the owner said; no gap found.
- `SPEC:8822` (memory-gc): free heap recorded, never required. Source: heap-floors-kept (ok); the owner retired the old floors. Built as the owner said; no gap found.
- `SPEC:9290` (tests-unit): test loggers at error level for the gates. Source: REG:729 ("Option 1 is good", owner, 2026-10-20). Gap: the owner chose test-side logging, yet product console() lines for the same gates remain (SPEC:7680, OBS; SCAN2 pattern 2).
- `SPEC:11799` (driver-scd30): soft reset at every start. Source: owner 2026-10-21 Q4 "a - the scd30 has its own processor and it should be rebooted along each restart ...". Built as the owner said; no gap found.
- `SPEC:11855` (driver-scd30): FRC rate/window provisional. Source: scd30-calibration-readiness (ok). Built as the owner said; no gap found.
- `PROJECT_AUDIT_PLAN.md:447` (uart): CRC-16 swap. Source: OR88 "the current state - adhering to the standards, using the CRC functions module - is the correct one". Built as the owner said; no gap found.
- `PROJECT_AUDIT_PLAN.md:473` (core-logging): SysUptime from ticks (form: REPORT s5 TickSeconds). Source: OR101 "make sure the fix of (4) does not depend on a UTC timestamp (ant not on UTC at all)". Form only: REPORT s5 (TickSeconds 29 lines, ~12 for SysUptime alone) and S2-G4-13 (two NTP instances go).
- `PROJECT_AUDIT_PLAN.md:479` (core-logging): shared tick primitive's home. Source: OR104 "... whichever fits best". Built as the owner said; no gap found.
- `PROJECT_AUDIT_PLAN.md:574` (process): parked rows folded into the work order. Source: OR150 "Make sure the new steps are consistently integrated into all implementation activities". Built as the owner said; no gap found.
- `README.md:447` (release): an update keeps the filesystem. Source: reflash-runbook-erase (ok). Built as the owner said; no gap found.
- `THIRD_PARTY_LICENSES.md:113` (licensing): DFRobot MIT treated as governing, BSD-3 recorded. Source: licence-notices (ok). Built as the owner said; no gap found.
- `THIRD_PARTY_LICENSES.md:208` (licensing): publishing an image. Source: licence-notices (ok). Built as the owner said; no gap found.
- `UART_C_PORT_CHANGELOG.md:109` (uart): A7 CRC swap. Source: OR88. Built as the owner said; no gap found.
- `buildgen/codegen.py:449` (generated-code): first NTP sync last. Source: ntp-sync-last (ok). Built as the owner said; no gap found.
- `devices/grkizi.toml:16` (buildgen-toml): hardware_family label. Source: OR141 "keep keys in the device files" (SCAN2 s6). SCAN2 s6: stays in [device], checked and never emitted.
- `devices/klkizi.toml:16` (buildgen-toml): hardware_family label. Source: OR141 (SCAN2 s6). Built as the owner said; no gap found.
- `devices/schlafzi.toml:16` (buildgen-toml): hardware_family label. Source: OR141 (SCAN2 s6). Built as the owner said; no gap found.
- `digital_twin/README.md:926` (twin): Run 11 sample period. Source: owner 2026-10-23 Q1 "This is okay, go ahead." (Run 11's calibrated leak check). Built as the owner said; no gap found.
- `digital_twin/README.md:975` (twin): Run 11 calibration. Source: owner 2026-10-23 Q1. Built as the owner said; no gap found.
- `scripts/_digital_twin_ci_suite.py:209` (twin): Run 11 calibrated values. Source: owner 2026-10-23 Q1. Built as the owner said; no gap found.
- `src/asy_ntp_client.py:117` (ntp-dns): at most three fallback servers. Source: dns-fallback-setting (ok: "up to three IPv4 addresses"). Built as the owner said; no gap found.
- `src/asy_ntp_client.py:382` (ntp-dns): stale age. Source: ntp-synced-goes-stale (ok). Built as the owner said; no gap found.
- `src/asy_scd30_driver.py:121` (driver-scd30): provisional FRC settings. Source: scd30-calibration-readiness (ok). Built as the owner said; no gap found.
- `src/asy_webserver_service.py:541` (webserver-rest): no-cache. Source: static-no-cache (ok). Built as the owner said; no gap found.
- `src/asy_wifi_service.py:754` (wifi): failed hotspot-timer arm feeds the streak (form only). Source: Wi-Fi settled. Form only, as SPEC:3694; its comment cites the uptime tick, whose fallback is a DIFF (SPEC:4352).
- `src/voc_algorithm.py:59` (driver-sgp40): fix16 wraps to int32. Source: OR101 "My decision: Fix the bugs" (VOC-1 O-spec). Built as the owner said; no gap found.
- `tests/test_asy_fram_wire_trace.py:8` (storage-fram): owner seed; same line: blank block without busy marker (A-M2, the confirmed blank-chunk gap). Source: "The FRAM idea of yours is good, keep it!" (owner, 2026-10-28). Built as the owner said; no gap found.
- `tests/test_asy_fram_wire_trace.py:500` (storage-fram): block-1 status read. Source: "Solutions you proposed agreed." (REG:805). Built as the owner said; no gap found.
- `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:36` (tests-hardware): worst case twice over. Source: heap-floors-kept (ok). Built as the owner said; no gap found.
- `tests_hardware/heap_bounds.py:6` (tests-hardware): 16,384 B tripwire margin. Source: heap-floors-kept (ok). Built as the owner said; no gap found.
- `tests_scripts/test_device_tomls.py:61` (buildgen-toml): one hardware_family, one hardware. Source: OR141 (SCAN2 s6). Built as the owner said; no gap found.
- `tests_scripts/test_error_catalog.py:731` (website): one toned table. Source: website-display-details ("CalLight colours follow a fixed tone table"). Built as the owner said; no gap found.
- `toolchain/setup_toolchain.py:738` (ci-tooling): installer writes no sudoers. Source: bench-sudo-checked (ok). Built as the owner said; no gap found.

## 6. SUP, CHECK and TRACKED rows

**SUP.** `src/asy_ntp_client.py:392`: "the tick nearest the boundary is due" (agent, 2026-10-26).
- Superseded by the owner's answer of 2026-10-27 (Q10): "Option a, the 10s don't matter at all relative to the interval,
  and on top, the interval as such is arbitrary."
- That answer stands. The rounding belongs to the NTP cadence chain: REPORT s4 item 6, and S2-G4-13 (two `TickSeconds`
  exist for it). It goes with the chain.

**CHECK.** None. Every row in doubt either rests on verified evidence (scan rows, the pinned source, owner words) or is
already tracked with its open check (the lost-FRAM premise is hardware item HW1 behind REG:795's R-8; the mempause
dropped-one-shot frequency is HW5 behind REG:113).

**TRACKED** (the full verdict belongs to the part holding the row; "lean" is this part's reading, not a verdict):

- `SPEC:303` TRACKED REG:795 (LEAD NOTE 28, R-8 no probe bound) (storage-fram, L2): lean OBS: RDID probe is the lost-FRAM chain (S2-G1-20, A-M4 C).
- `SPEC:320` TRACKED REG:292 (supervisor-reset-watchdog, L3): armed reset stops feeds; a dropped one-shot ends in the watchdog.
- `SPEC:375` TRACKED REG:489 (driver-sgp40, L2): lean DIFF: SGP-12 H implausible.
- `SPEC:378` TRACKED REG:489 (driver-sgp40, L2): restart while boot restore waits still restores.
- `SPEC:405` TRACKED led-task-defined-state (led-notification, L2): lean DIFF: NP-4 H implausible (worst case one replayed flash).
- `SPEC:417` TRACKED REG:108 (SF-M2-02) (led-notification, L3): alerts gated on clock set.
- `SPEC:567` TRACKED REG:110 (SF-M4-01 (b)), REG:527 (webserver-rest, L3): print_exception rebind; SCAN2 keeps a 3-4 line rebind for the C-stack report.
- `SPEC:1042` TRACKED REG:795 (LEAD NOTE 11), REG:783 (ntp-dns, L7): stale-clock flag form; S2-G4-15 form only.
- `SPEC:1128` TRACKED REG:757 (E115 and its band) (supervisor-reset-watchdog, L3): lean OBS: A-S16 H.
- `SPEC:1148` TRACKED REG:802 (the overwrite warning) (uart, L7): website warns a hazard run fills UART_resp.
- `SPEC:1152` TRACKED REG:795 (LEAD NOTE 12); owner exception REG:801 (uart, L7): hazard mode as the agent's form.
- `SPEC:1180` TRACKED REG:546 (supervisor-reset-watchdog, L3): failed delete reads 9 at next boot; owner "Good, ..." on reset-reason-codes.
- `SPEC:1370` TRACKED REG:795 (hazard mode) (security, L7): hazard row added to A.11 on 2026-10-21/22, after the owner's sign-off (REG:710).
- `SPEC:1669` TRACKED REG:578 (ci-tooling, L1): mbedtls GCC14 workaround retirement rule.
- `SPEC:1940` TRACKED ci-budget-margin (ci-tooling, L4): timeout-minutes rule.
- `SPEC:1942` TRACKED ci-budget-margin (ci-tooling, L4): cold-run addition.
- `SPEC:2799` TRACKED REG:723 (tests-unit, L4): GC stack override form.
- `SPEC:2821` TRACKED REG:723 (tests-unit, L4): 1024 not 4096.
- `SPEC:2973` TRACKED REG:778 (R-2) (ci-tooling, L1): checkers declined.
- `SPEC:3051` TRACKED REG:440 (bus-i2c-spi, L5): DeviceSession typed I2CDevice.
- `SPEC:3235` TRACKED REG:362 (uart, L2): lean DIFF: closed-channel catch guards a state no product path creates (S2-G2-11).
- `SPEC:3800` TRACKED REG:514 (ntp-dns, L3): lean DIFF: resolver str or None, no logger (S2-G2-5).
- `SPEC:3900` TRACKED REG:111 (SF-M1-01), REG:284 (config, L2): lean DIFF: W69 has its own false positive (S2-G4-21, OF-184).
- `SPEC:3982` TRACKED REG:520 (wifi, L2): one yield per datagram (confirmed gap).
- `SPEC:3985` TRACKED REG:520 (wifi, L2): lean DIFF: heap failure split from bad input (S2-G2-10).
- `SPEC:4295` TRACKED REG:795 (uart, L7): hazard initiations task row.
- `SPEC:4319` TRACKED REG:113 (SF-A11) (storage-fram, L2): mempause deadline on the status pass (A-S21: mechanism confirmed in source).
- `SPEC:4834` TRACKED REG:757 (RA-7) (timing-waits, L5): ServingLimits converted once to ms.
- `SPEC:5006` TRACKED REG:261 (process, L5): topical heading removed before reorder.
- `SPEC:5253` TRACKED REG:585 (twin, L4): Wi-Fi modes in a file of their own.
- `SPEC:5874` TRACKED REG:199 (tests-hardware, L4): flash-only-bus-checks (its 2026-10-27 setup-reset half untracked, SAME).
- `SPEC:5881` TRACKED REG:795 (tests-hardware, L7): uart-hazards-under-api-load.
- `SPEC:6253` TRACKED dynamic-import-ban (buildgen-toml, L5): every import static at module top.
- `SPEC:6650` TRACKED one-timeout-mechanism (timing-waits, L5): timeout mapped to the sentinel.
- `SPEC:6779` TRACKED stall-bounds (timing-waits, L3): routine stall bound.
- `SPEC:6811` TRACKED REG:757 (timing-waits, L4): loop-lag window figures.
- `SPEC:7096` TRACKED REG:114 (SF-A10) (supervisor-reset-watchdog, L2): lean OBS: ResetBits goes (S2-G4X-1).
- `SPEC:7452` TRACKED REG:393 (tests-unit, L6): rig differences worked around outside src/.
- `SPEC:7490` TRACKED REG:736 (RC-4) (tests-unit, L4): long module path left to fail at import.
- `SPEC:7545` TRACKED REG:415 (docs-records, L1): F.9 workaround index.
- `SPEC:7773` TRACKED i2c-scratch-view (bus-i2c-spi, L6): lean OBS/DIFF: I2C-9 H (OR110 short-lived temporaries).
- `SPEC:8092` TRACKED REG:618 (website, L7): section switch keeps the in-flight GET (PICTURE M13 withdrawn).
- `SPEC:8373` TRACKED REG:620 (website, L4): matrix page reduced motion.
- `SPEC:8603` TRACKED REG:760 (ci-tooling, L8): installer takes either driver name.
- `SPEC:8939` TRACKED i2c-scratch-view (bus-i2c-spi, L6): I2C long-lived view.
- `SPEC:9041` TRACKED REG:795 (LEAD NOTE 57) (uart, L6): _hazard_facts bounded.
- `SPEC:9398` TRACKED REG:492 (memory-gc, L4): boot-contiguity control arm on dev.
- `SPEC:9927` TRACKED REG:541 (uart, L6): bench ring sized on the bench.
- `SPEC:10056` TRACKED REG:795 (uart, L7): hazard mode form.
- `SPEC:10100` TRACKED REG:377 (tests-unit, L4): lean FORM: a planted-stall guard per check and CRC arm (owner 2026-10-23 Q2).
- `SPEC:11808` TRACKED REG:437, REG:342 (driver-scd30, L1): derived values None outside domains; cold-dry corner (REPORT s4 item 9).
- `.github/workflows/ci.yml:328` TRACKED monthly-firefox (ci-tooling, L8): Firefox key rolls monthly.
- `BACKLOG.md:230` TRACKED REG:780 (M1 + S3b wear naming) (tests-hardware, L6): hardware row's wear statement.
- `BACKLOG.md:341` TRACKED REG:780 (Expected slots tagged) (tests-hardware, L4): hardware row expectation.
- `BACKLOG.md:390` TRACKED REG:780 (tests-hardware, L4): hardware row expectation.
- `BACKLOG.md:400` TRACKED REG:780 (tests-hardware, L4): hardware row expectation.
- `BACKLOG.md:420` TRACKED REG:780 (tests-hardware, L4): hardware row expectation.
- `BACKLOG.md:424` TRACKED REG:780 (tests-hardware, L4): hardware row expectation.
- `BACKLOG.md:560` TRACKED REG:780 (tests-hardware, L4): hardware row expectation.
- `BACKLOG.md:1038` TRACKED REG:713 (ci-tooling, L4): coverage job limit 35 to 95 min (lean OBS: M8 test growth).
- `buildgen/validate.py:90` TRACKED REG:346 (buildgen-toml, L2): boot clear bound from the largest timeout.
- `buildgen/validate.py:96` TRACKED REG:346 (buildgen-toml, L2): three quarters of the watchdog.
- `buildgen/validate.py:618` TRACKED REG:757 (C2) (buildgen-toml, L4): I2C timeout rule (lean FORM: G3 Family A).
- `buildgen/validate.py:1567` TRACKED REG:757 (loop-lag bound) (buildgen-toml, L4): smallest hard consumer.
- `devices/dev.toml:179` TRACKED REG:541 (uart, L5): receive cap = protocol default.
- `scripts/_digital_twin_scenarios.py:131` TRACKED REG:757 (T3) (twin, L4): loop-lag load window.
- `scripts/_digital_twin_scenarios.py:1292` TRACKED REG:757 (RE-4) (twin, L4): post-load lag bound.
- `src/asy_notification_service.py:69` TRACKED REG:117 (SF-M3-01) (led-notification, L2): 10,800 s age bound (lean DIFF: S2-G1-18, DELAY).
- `src/asy_ntp_client.py:546` TRACKED REG:108 (SF-M2-02) (ntp-dns, L3): local time gated on clock set.
- `src/asy_sgp40_driver.py:88` TRACKED REG:117 (SF-M3-01) (driver-sgp40, L2): 10,800 s age bound (lean DIFF).
- `src/asy_system_service.py:412` TRACKED REG:546 (supervisor-reset-watchdog, L3): command incomplete written at acceptance.
- `src/asy_system_service.py:487` TRACKED REG:546 (supervisor-reset-watchdog, L3): a shortfall reads 9.
- `src/asy_uart_link_driver.py:43` TRACKED REG:795; owner exception REG:801 (uart, L7): hazard mode form.
- `tests/_uart_comm_harness.py:125` TRACKED REG:377 (tests-unit, L4): poll-round clock.
- `tests/test_asy_fram_wire_trace.py:9` TRACKED REG:795 (R-8) (storage-fram, L2): RDID probe (lean OBS S2-G1-20).
- `tests/test_digital_twin_bus_hazard_concurrency.py:602` TRACKED REG:795 (LEAD NOTE 30, V3) (twin, L4): forced failed reconnect.
- `tests_hardware/README.md:1144` TRACKED REG:802 (tests-hardware, L8): save UART logs before a hazard run.
- `tests_scripts/test_code_conventions.py:23` TRACKED REG:271 (ci-tooling, L5): trigger starters take timer names.
- `tests_scripts/test_digital_twin_boot_contiguity.py:42` TRACKED REG:492 (memory-gc, L4): control arm separates on the largest batch.
- `tests_scripts/test_digital_twin_boot_contiguity.py:44` TRACKED REG:492 (memory-gc, L4): devices with the most instances.
- `toolchain/micropython_overrides.py:81` TRACKED REG:578 (ci-tooling, L1): = SPEC:1669.

## 7. Contradictions, and counterparts in other sets

**Agent decisions against the owner's words** (the owner's side stands in each):
1. SPEC:1898 and SPEC:1923, the apt mirror and cache machinery (agent, 2026-10-27/28), against the owner, 2026-10-27:
   "Don't care about proven external issues so far."
2. SPEC:5585 and UART_C_PORT_CHANGELOG.md:213 (narrowing branches kept; B89's six never-true checks), against the
   owner's typing rule of 2026-10-27, quoted in section 2.
   - Inside the set, UART_C_PORT_CHANGELOG.md:216 (B92, a typing-only refusal removed) applies the owner's rule.
   - B89 and B92 answer the same question in opposite ways; the new knowledge supports B92.
3. SPEC:11606 (setup failure, strongest rung first) against OR113, "try to recover mildly, but escalating ... if the mild
   measures don't work out".
4. src/voc_algorithm.py:219 (VOC-5) against OR109's "everything is settled" for the VOC temporaries. It also conflicts with
   the owner-covered literal-port rule (SPEC:3029, SPEC:6844, via OR141) and with SPEC:6843's "One deliberate
   deviation": VOC-5 is a second deviation, and no rule names it.
5. SPEC:4352, the uptime tick fallback, and the refused-arm family under tracked rows, against the owner's Q2
   (2026-10-21): "nothing which would happen by itself as a surprise".
6. src/asy_neopixel_driver.py:37 and SPEC:410, the 300 s rewrite, against the owner, 2026-10-28: "hardcoded delay checks
   like this are a very bad, very awkward pattern" (M2).
7. SPEC:7680, the product `console()` lines for the memory gates, against the owner's choice of test-side logging. The
   owner, 2026-10-20: "Option 1 is good" (REG:729; SPEC:9290, OWN). Also OR36: "zero artifacts specifically added for
   testing" (M6).
8. SPEC:3761, the rule for overlapping resets, against OR35.a: "Protection against alternating codes and layered limits
   are overkill on such limited device". That is a FORM.

**Facts for the lead** (owner statements that seem to pull apart; no question framed):
- **Wi-Fi's settled refused-arm handling against the Q2 answer.**
  - SPEC:3694 and src/asy_wifi_service.py:754: a refused hotspot-timer arm counts as a hardware failure. This is
    owner-settled (2026-10-28: "We thoroughly discussed the WiFi issues and I decided everything already.").
  - The owner's Q2 (2026-10-21) calls a timer shortage a malformed firmware that the tests would show.
  - Both are owner words. Wi-Fi takes a smaller form only. Its comment cites "the uptime tick's" handling, which goes
    under item 5 above.
- **The refusal trace's bound.**
  - SPEC:1258 rests on the owner's "Solutions you proposed agreed." (2026-10-22).
  - SCAN2 s7 item 7 returns the refusal arm to close-then-trace. That makes the accepted bound obsolete on that arm, under
    the owner's 2026-10-28 background note on decisions tied to a removed cascade.
- **The register's framing of that acceptance.** REG:805 calls the "Solutions you proposed agreed." acceptance "An agent
  decision accepted by the owner ... not an owner decision". SPEC:194, :198, :1258 and
  tests/test_asy_fram_wire_trace.py:500 rest on it. Under this review's rule the owner's words make them OWN; the two
  readings differ.
- **The hazard row in A.11.** SPEC:1370's hazard row, edited 2026-10-21/22, postdates the owner's A.11 sign-off
  (REG:710, 2026-10-20: "Option 1, sign off A.11 as is"). The sign-off does not cover it; REG:795 tracks it.
- **ISL29125's unconverged calibration (W75).** SPEC:11754 is SAME here: the timeout of a user-started run is an
  expected outcome, not a guarded fault. C.md ISL-9 rates it H.
- **PieceBuffer's read_at().**
  - SPEC:10163 and UART_C_PORT_CHANGELOG.md:215 (B91) are SAME here: `read_at()` removed the one observed F row, a 12 KB
    copy per GET in the dev echo path (REPORT s2).
  - REPORT s5 counts `read_at()` among the parts to drop "with nothing lost". SCAN2 s6 corrects only `trim()`.

**Counterparts (the same decision held in another set).**

The register:

| register row | lines here |
|---|---|
| REG:795 (U35's decisions, by LEAD NOTE) | SPEC:303, 1042, 1152, 1370, 4295, 5881, 9041, 10056; tests/test_asy_fram_wire_trace.py:9; tests/test_digital_twin_bus_hazard_concurrency.py:602; src/asy_uart_link_driver.py:43 |
| REG:757 (U31's decisions) | SPEC:1128, 4834, 6811; buildgen/validate.py:618, :1567; scripts/_digital_twin_scenarios.py:131, :1292 |
| REG:757's "escalation's entry wait 1200 ms" (S2-G1-6) | scripts/_digital_twin_scenarios.py:1663 (OBS) |
| REG:117 (SF-M3-01) | SPEC:373, 420, 7664 (OBS); src/asy_sgp40_driver.py:88; src/asy_notification_service.py:69 |
| REG:111 (SF-M1-01) | SPEC:3900 |
| REG:514 | SPEC:3800 |
| REG:520 | SPEC:3982, 3985 |
| REG:362 | SPEC:3235 |
| REG:113 | SPEC:4319 |
| REG:489 | SPEC:375, 378 |
| REG:108 | SPEC:417; src/asy_ntp_client.py:546 |
| REG:546 | SPEC:1180; src/asy_system_service.py:412, :487 |
| REG:114 | SPEC:7096 |
| REG:110 | SPEC:567 |
| REG:780 | the seven BACKLOG.md hardware-round rows |
| REG:107, REG:109 | SPEC:443, 449 (OWN by the Wi-Fi settlement) |

The review page:

| review item | lines here |
|---|---|
| led-task-defined-state | SPEC:405 |
| i2c-scratch-view | SPEC:7773, 8939 |
| kept-branches | the same principle as SPEC:5585 and UART_C_PORT_CHANGELOG.md:213 |
| monthly-firefox | .github/workflows/ci.yml:328 |
| ci-budget-margin | SPEC:1940, 1942 |
| stall-bounds | SPEC:6779 |
| one-timeout-mechanism | SPEC:6650 |
| dynamic-import-ban | SPEC:6253 |
| c-stack-reboot | SPEC:6472 (OWN); likely also the U30 C-stack rows in the register sets |

Likely decided again in the register sets: the refused-timer-arm rows of U15, U18 and U31 (A-B6, A-B14, A-S20 by their
words), against SPEC:4352 and SPEC:5878.

## 8. SAME rows

- `SPEC:169` (config): pre-audit: the in-memory cache rewrites an externally corrupted file at the next write (only writer).
- `SPEC:695` (supervisor-reset-watchdog): loop-end 22 keeps a valid record of the reset under way; labels 21/22 kept (SCAN2 s7 item 6).
- `SPEC:1553` (ci-tooling): shell conventions with a check.
- `SPEC:1747` (ci-tooling): jobs pinned to ubuntu-24.04 (verified break on 26.04, REG:760).
- `SPEC:2123` (tests-hardware): bridge MAC pinned (observed drift).
- `SPEC:2479` (webserver-rest): PBUF_POOL_SIZE default kept.
- `SPEC:2607` (webserver-rest): third lwIP patch: two stores reordered in an existing override (mechanism read in modlwip.c).
- `SPEC:2732` (webserver-rest): its retirement condition.
- `SPEC:3056` (config): constructor fixed tail.
- `SPEC:3201` (uart): one merged UART class.
- `SPEC:3224` (uart): UART_TRANSFER_CAP through the caller's log.
- `SPEC:3508` (webserver-rest): one hook per endpoint as legacy.
- `SPEC:3532` (config): flat namedtuples built all-None.
- `SPEC:3708` (core-logging): owned helper may own a logger (DNSSRV).
- `SPEC:3932` (config): cut defaults write read as damaged next boot (confirmed gap).
- `SPEC:3960` (wifi): Hostname/Country shapes at PUT.
- `SPEC:3973` (wifi): captive DNS drops malformed queries.
- `SPEC:3978` (wifi): lwIP's 4-datagram queue accepted.
- `SPEC:4079` (timing-waits): cancellation restores state in finally.
- `SPEC:4089` (tests-unit): per-path cancel sweeps (E.md lists _cancel_sweep.py in harness growth, no verdict).
- `SPEC:4276` (supervisor-reset-watchdog): hotspot DNS task outside the supervisor.
- `SPEC:4525` (core-logging): readiness gate only where a product reads it.
- `SPEC:4550` (buildgen-toml): singletons out of the naming scheme.
- `SPEC:4660` (buildgen-toml): _WIRING exception.
- `SPEC:4940` (docs-records): no function docstrings (extends pre-audit D.11).
- `SPEC:4977` (process): dunders first (lead reading of OR96).
- `SPEC:4983` (process): import-time exception named by the check.
- `SPEC:5088` (tests-unit): no unit file relies on :123/:53 being closed.
- `SPEC:5092` (tests-unit): audit instead of a guard.
- `SPEC:5204` (tests-unit): waits poll with a deadline.
- `SPEC:5206` (tests-unit): fixed delay only where nothing to read.
- `SPEC:5376` (tests-unit): heap value never raised as a fix.
- `SPEC:5507` (tests-unit): allocator as mocking surface.
- `SPEC:5539` (tests-unit): traced tier as one pytest step.
- `SPEC:5673` (tests-unit): one float per call event (tracer).
- `SPEC:5718` (tests-unit): sharing not forced.
- `SPEC:5830` (tests-unit): consolidation targets one shape.
- `SPEC:5857` (tests-hardware): ws2812-no-readback.
- `SPEC:5858` (tests-hardware): human-only.
- `SPEC:5859` (twin): twin-instrument.
- `SPEC:5860` (twin): twin-instrument.
- `SPEC:5861` (twin): twin-instrument.
- `SPEC:5862` (twin): twin-instrument.
- `SPEC:5863` (twin): twin-instrument.
- `SPEC:5864` (twin): twin-instrument (PC-tier handler).
- `SPEC:5865` (twin): twin-instrument (idle poll).
- `SPEC:5866` (twin): twin-instrument (driven clock).
- `SPEC:5867` (twin): twin-instrument (rp2 constants).
- `SPEC:5872` (tests-hardware): fram-write-protect-no-rest.
- `SPEC:5875` (tests-hardware): held-i2c-line-silicon.
- `SPEC:5876` (tests-hardware): system-commands-instrumented.
- `SPEC:5877` (tests-hardware): hot-replug-manual.
- `SPEC:5879` (tests-hardware): clock-step-on-silicon.
- `SPEC:5880` (tests-hardware): ntp-responder-modes.
- `SPEC:5882` (tests-hardware): uart-load-flush.
- `SPEC:5883` (tests-hardware): webserver-requests-bench.
- `SPEC:5884` (tests-hardware): fault-storm-persisted-writes.
- `SPEC:5885` (tests-hardware): ntp-unreachable-under-load.
- `SPEC:5886` (tests-hardware): reader-saturation-floor (OR72: degradation check only).
- `SPEC:5887` (tests-hardware): watchdog-fault-planted.
- `SPEC:6043` (uart): hazard checks in both CRC modes.
- `SPEC:6099` (twin): a shared-boot overrun fails as the boot's.
- `SPEC:6218` (ci-tooling): re-check practice.
- `SPEC:6755` (timing-waits): no resurrection of the long-block lock.
- `SPEC:6760` (timing-waits): a crossing row is fixed or states its degradation.
- `SPEC:6809` (twin): Run 3 FRAM write ceiling.
- `SPEC:6843` (driver-sgp40): 16383 instead of 32767 (VOC-2 R, OR105).
- `SPEC:7089` (tests-hardware): intended resets through the REST reboot path.
- `SPEC:7123` (ci-tooling): repair stubs, no type: ignore.
- `SPEC:7144` (ci-tooling): no-source-lines not adopted.
- `SPEC:7320` (bus-i2c-spi): F.5.8 not generalised to I2C/SPI.
- `SPEC:7354` (uart): write asks only what an empty ring takes.
- `SPEC:7359` (uart): idle poll rule (extension of the owner's never-block rule).
- `SPEC:7556` (webserver-rest): third lwIP patch row.
- `SPEC:7742` (bus-i2c-spi): non-allocating bus API forms.
- `SPEC:7758` (storage-fram): one FRAM buffer per operation (OR110).
- `SPEC:7807` (bus-i2c-spi): no I2C session primitive.
- `SPEC:7808` (uart): read-in-flight from the lock.
- `SPEC:7825` (uart): one codec per driver.
- `SPEC:7907` (config): config objects one shape.
- `SPEC:8029` (website): bootstrap not tsc-checked.
- `SPEC:8124` (website): mock float tolerance.
- `SPEC:8524` (webserver-rest): no keep-alive.
- `SPEC:8616` (ci-tooling): conda packages unpinned.
- `SPEC:8655` (ci-tooling): sandbox Chromium fallback.
- `SPEC:8778` (memory-gc): budgets from the measured figure.
- `SPEC:8932` (storage-fram): declined log-call move.
- `SPEC:9851` (uart): ResetErrors keeps the valid-frame count.
- `SPEC:10111` (tests-unit): bounds in poll rounds.
- `SPEC:10117` (tests-unit): CRC16 on the 240 ms arm.
- `SPEC:10119` (tests-unit): step ceiling twice the count.
- `SPEC:10163` (uart): PieceBuffer sent from pieces (fixes the observed 12 KB echo copy).
- `SPEC:10184` (uart): a declared size caps a responder.
- `SPEC:10207` (uart): plain class (delegated by the owner).
- `SPEC:10605` (buildgen-toml): flashing outside the build scheme.
- `SPEC:10656` (generated-code): generated module's function set.
- `SPEC:11057` (twin): last-wired chip persists only.
- `SPEC:11630` (driver-isl29125): SYNC/CONVEN unused.
- `SPEC:11677` (driver-isl29125): derived-window rule.
- `SPEC:11713` (driver-isl29125): INT parking (ISL-1 R); the dead-line detector's pause goes with ISL-2.
- `SPEC:11720` (driver-isl29125): calibration band/windows the agent's values.
- `SPEC:11754` (driver-isl29125): unconverged calibration warns W75 (C.md ISL-9 says H).
- `SPEC:11788` (driver-scd30): legacy wait kept.
- `SPEC:11790` (driver-scd30): legacy wait kept.
- `SPEC:11865` (driver-sgp40): legacy wait kept.
- `SPEC:11866` (driver-sgp40): legacy wait kept.
- `SPEC:11867` (driver-sgp40): heater-off datasheet max.
- `SPEC:11901` (driver-bmp3xx): Bosch reference reset settle.
- `.github/zizmor.yml:16` (ci-tooling): self-repository disabled (tool conflict).
- `BACKLOG.md:161` (tests-hardware): no software stand-in claims manual coverage.
- `BACKLOG.md:207` (tests-hardware): hardware-round run sheet (errcount first).
- `BACKLOG.md:1119` (ci-tooling): chroot copy must be a checkout; failed render input archived.
- `BACKLOG.md:1131` (ci-tooling): residual trixie risk judged low.
- `BACKLOG.md:1173` (uart): three UART findings left as they are.
- `BACKLOG.md:1265` (ci-tooling): Ubuntu 26.04 move is its own step.
- `CLAUDE.md:170` (uart): wozi carries no UART instances.
- `CLAUDE.md:288` (uart): idle-poll mirror rule.
- `CLAUDE.md:391` (tests-hardware): br0 MAC pinned (observed drift).
- `CLAUDE.md:655` (ci-tooling): zizmor self-repository disabled.
- `CLAUDE.md:668` (ci-tooling): new files join ruff/mypy at once.
- `CLAUDE.md:781` (ci-tooling): needs: for sequencing, if: !cancelled().
- `CLAUDE.md:894` (tests-unit): heap size never raised as a fix.
- `CLAUDE.md:931` (ci-tooling): ruff format unused.
- `CLAUDE.md:1255` (process): green only when CI ran on the head.
- `PROJECT_AUDIT_PLAN.md:463` (process): lead readings of OR96 (dunders first).
- `PROJECT_AUDIT_PLAN.md:467` (driver-scd30): lead readings of OR98 (running sums, temperature guard), inside the owner's criteria.
- `PROJECT_AUDIT_PLAN.md:481` (core-logging): one cap 2**30-1 (kept as is, SCAN2 platform table).
- `UART_C_PORT_CHANGELOG.md:197` (uart): B73 drain flag cleared first.
- `UART_C_PORT_CHANGELOG.md:215` (uart): B91 PieceBuffer sent from pieces.
- `UART_C_PORT_CHANGELOG.md:216` (uart): B92 type refusal removed (typing covers it).
- `buildgen/signals.py:21` (buildgen-toml): signals fixed by the generator.
- `buildgen/validate.py:1242` (buildgen-toml): warn_* keys only in the signal catalog.
- `buildgen/version.py:2` (release): version bumped by hand.
- `digital_twin/README.md:212` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:213` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:214` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:223` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:226` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:228` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:234` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:235` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:237` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:238` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:239` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:240` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:243` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:245` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:248` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:251` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:252` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:260` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:261` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:262` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:263` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:265` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:266` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:272` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:276` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:277` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:281` (twin): fidelity row accepted (OR20 keep the twin small).
- `digital_twin/README.md:354` (twin): --duration ends on PATH.
- `digital_twin/README.md:563` (twin): paged chip memory.
- `digital_twin/README.md:896` (twin): shared-boot deadline.
- `digital_twin/unixport/_unix_port_udp_addr_shim.py:39` (twin): one loopback address per process.
- `scripts/_digital_twin_ci_suite.py:135` (twin): Run 9 failure count.
- `scripts/_digital_twin_ci_suite.py:1252` (twin): Run 3 write ceiling.
- `scripts/_digital_twin_scenarios.py:166` (twin): storm writes counted per event.
- `scripts/_digital_twin_scenarios.py:1241` (twin): twin boots at error level (agent's extension of the owner's Option 1).
- `scripts/_digital_twin_scenarios.py:2178` (twin): -1 stage prints, asserts nothing.
- `scripts/_twin_process.py:56` (twin): no launch passes TEST_TWIN_HOST on.
- `scripts/lint.sh:4` (ci-tooling): ruff format unused.
- `scripts/setup_cross_browser_toolchain.sh:35` (ci-tooling): micromamba pinned.
- `scripts/setup_cross_browser_toolchain.sh:126` (ci-tooling): conda packages unpinned.
- `src/asy_api_response.py:63` (webserver-rest): one hook per endpoint.
- `src/asy_bmp3xx_driver.py:78` (driver-bmp3xx): cmd_rdy wait bounded at 50 ms.
- `src/asy_crc_checks.py:52` (storage-fram): CRC32 as two words (confirmed efficiency gap).
- `src/asy_isl29125_driver.py:103` (driver-isl29125): device constants not config.
- `src/asy_isl29125_driver.py:588` (driver-isl29125): parked INT (ISL-1 R).
- `src/asy_isl29125_driver.py:716` (driver-isl29125): parked INT (ISL-1 R).
- `src/asy_scd30_driver.py:185` (driver-scd30): stuck-pin fallback period (SCD-8 R).
- `src/asy_sgp40_driver.py:219` (driver-sgp40): ResetVOC as a live-push field.
- `src/asy_system_service.py:175` (supervisor-reset-watchdog): = SPEC:695.
- `src/asy_uart_link_driver.py:4` (uart): plain class.
- `src/asy_webserver_service.py:266` (webserver-rest): last registration wins, no dedup code.
- `src/math_helpers.py:201` (driver-isl29125): sRGB literals.
- `src/voc_algorithm.py:41` (driver-sgp40): 16383 (VOC-2 R).
- `tests/_digital_twin_construction_scenarios.py:210` (twin): DrivenWall clock.
- `tests/_sensortask_scenarios.py:2124` (tests-unit): six-hour stalls.
- `tests/_sensortask_scenarios.py:2739` (tests-unit): serving budget estimated, measurement owed.
- `tests/_uart_comm_hazard_common.py:39` (tests-unit): both CRC modes.
- `tests/test_asy_api_response.py:183` (tests-unit): hook catch beside Microdot's (field experience).
- `tests/test_asy_base_classes.py:3364` (tests-unit): push callbacks per instance.
- `tests/test_asy_crc_checks.py:671` (tests-unit): independent CRC oracles.
- `tests/test_asy_fram_wire_trace.py:5` (tests-unit): wire trace as the restructure contract.
- `tests/test_asy_fram_wire_trace.py:529` (tests-unit): 100-year floor.
- `tests/test_asy_uart_comm.py:152` (tests-unit): stall drain bound.
- `tests/test_asy_uart_comm.py:3477` (tests-unit): legacy rxbuf kept.
- `tests/test_asy_uart_link_driver.py:661` (tests-unit): hazard polls at shipped rates.
- `tests/test_asy_uart_link_driver.py:664` (tests-unit): measured virtual run time, no margin.
- `tests/test_digital_twin_clock_jump.py:86` (twin): driven clock.
- `tests/test_digital_twin_clock_jump.py:173` (twin): driven clock.
- `tests/test_digital_twin_hot_replug.py:189` (twin): driven clock.
- `tests/test_digital_twin_launch.py:67` (twin): driven clock.
- `tests/test_digital_twin_ntp.py:126` (twin): local responder (owner change on twin-tolerates-ntp-offline).
- `tests/test_digital_twin_run_generic_integration.py:993` (twin): one smoke boot per distinct wiring.
- `tests/test_digital_twin_run_generic_integration.py:1016` (twin): run ends after the WIFI store setup.
- `tests/test_digital_twin_sensortask_integration.py:94` (twin): waits count polls, no wall-clock bound.
- `tests/test_digital_twin_sensortask_integration.py:143` (twin): Theil-Sen leak slope (complex measurement).
- `tests/test_digital_twin_sensortask_integration.py:153` (twin): unserved port.
- `tests/test_digital_twin_sensortask_integration.py:735` (twin): linked station scenario.
- `tests/test_digital_twin_sensortask_integration.py:1011` (twin): one run per wiring.
- `tests/test_digital_twin_timer_pool.py:165` (twin): plain clock for UART wiring.
- `tests/test_digital_twin_timer_pool.py:315` (twin): reboot with an empty pool reads 6 (kept, A-S6).
- `tests/test_digital_twin_uart_link.py:120` (twin): planted-leak calibration (complex measurement).
- `tests/test_digital_twin_uart_link.py:151` (twin): driven-clock read period.
- `tests/test_digital_twin_uart_link.py:154` (twin): measured run time.
- `tests/test_digital_twin_uart_link.py:926` (twin): link on the driven clock.
- `tests/test_math_helpers.py:598` (tests-unit): external oracle.
- `tests/test_uart_comm_hazard.py:1396` (tests-unit): measured 4 ms bound.
- `tests_hardware/README.md:208` (tests-hardware): bridge MAC pinned.
- `tests_hardware/bench/test_uart_link_under_api_load.py:58` (tests-hardware): hazard run timeout.
- `tests_hardware/conftest.py:111` (tests-hardware): thread death fails its test (no lost evidence).
- `tests_hardware/flash/test_system_commands.py:41` (tests-hardware): erase feed gap bound.
- `tests_hardware/plausibility_bounds.py:25` (tests-hardware): VOC floor 0.
- `tests_js/_live_twin_command.js:339` (website): reload waits for drain.
- `tests_js/_live_twin_command.js:423` (website): Playwright routing hold.
- `tests_js/_live_twin_command.js:500` (website): drain and reload share a slot.
- `tests_js/live-backend-put-matrix.test.js:31` (website): responder host read from source.
- `tests_js/live-backend-put-matrix.test.js:41` (website): SSID not seeded.
- `tests_js/live-backend.test.js:9` (website): smoke timeout from measurement.
- `tests_js/live-backend.test.js:13` (website): concurrent tabs timeout.
- `tests_scripts/conftest.py:59` (ci-tooling): toolchain lock held shared.
- `tests_scripts/test_bench_no_task_ended_completeness.py:24` (tests-hardware): join mechanics exempt.
- `tests_scripts/test_buildgen_validate.py:2626` (buildgen-toml): ceiling value from the sweep.
- `tests_scripts/test_code_conventions.py:29` (ci-tooling): no-autostart print allowed.
- `tests_scripts/test_device_script_facts.py:154` (tests-hardware): starving-loop rule.
- `tests_scripts/test_device_script_rig_parking.py:34` (tests-hardware): parking-try forms.
- `tests_scripts/test_digital_twin_generated_boot.py:232` (twin): normal boot logs no entry.
- `tests_scripts/test_host_text_encoding.py:3` (ci-tooling): explicit encodings.
- `tests_scripts/test_isl29125_copies.py:16` (twin): CONFIG3 not compared.
- `tests_scripts/test_script_metadata_pins.py:3` (ci-tooling): PEP 723 pins.
- `tests_scripts/test_tunables_register.py:38` (ci-tooling): shift read as factor four.
- `toolchain/micropython_overrides.py:285` (webserver-rest): MEM_SIZE share relationship.
- `toolchain/micropython_overrides.py:468` (webserver-rest): third lwIP patch (= SPEC:2607).
- `toolchain/setup_toolchain.py:875` (ci-tooling): picotool tag choice.
- `vitest.config.js:26` (ci-tooling): sandbox Chromium fallback.
