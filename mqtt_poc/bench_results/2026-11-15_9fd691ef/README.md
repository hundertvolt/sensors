# MQTT PoC bench run, 2026-11-15, image `9fd691ef`

The record of the run's hand-backs (the audit's bench session, branch `claude/u35-bench-campaign`: relay 42's block
in `dc302103`, relay 43's in `e9675404`, relay 44's in `2213c92c`). The logs, the archive and the capture stay on the
bench host (`logs/day9_20261115/`, `build/archive/run_bench_hardware_suite_scope_mqtt/20261115T083024Z/`).

## Setup

- The owner, 2026-11-15, in the code session: "You shall do no wear related tests, while flashing a new image
  containing the MQTT code of course is allowed"; asked "How should login be covered on the bench?": "Both login
  tests (Recommended)". In the bench session: "Yes, flash and run", then "Go for all"; for the capture, "Yes, capture
  and run".
- Code: `claude/whole-project-audit-plan-followup` at `9fd691ef` (the final base `a6f28126` plus the client and the
  exerciser), carried to the bench branch as `d98e62d6`.
- Host: the bench Pi4, Debian trixie. Image: 1,178,948 B (95.9 %), `"dirty": false`, BuildDate 2026-11-15T08:22:34Z.
  This sandbox's build of the same commit is 1,177,644 B: the ARM compiler is the distribution's unpinned
  `gcc-arm-none-eabi`, GCC 13.2.1 on Ubuntu 24.04 and Debian trixie's GCC 14 on the Pi.
- Writes: one flash cycle; `config_MQTT.cfg`'s defaults once at the first boot (the file was absent); the two login
  tests' 5 owned writes (2 + 3, each undone); the unmarked prerequisites (the MQTT module's enabling and disabling
  PUTs, the hotspot module's SSID clear and restore, the flash step's scratch builds). No SCD30 write.

## First boot

`MQTTState` "disabled", `MQTTLINK` 0/0/0. `MQTT` and `CFGMGR_MQTT` take chunks after `NOTIFY`'s, so `WEBSERVER`
moved and read blank; `CFGMGR_MQTT` logged W22 once (the absent file, read before its defaults were written). After a
REST reboot, no new FRAM entry beyond the boot-time NTP miss (E71).

## Flash step (3 tests)

- FRAM chunk layout: PASS, 1,200 of 262,144 B allocated (the final base: 1,140).
- `env --tier flash` rerun: deselected by its own gate (`--allow-toolchain-reverify`).
- Full-build heap headroom: FAILED as expected, "at gc.threshold [-1, 32768]: the build and its setups keep 45488 B,
  over 41000 B". The build kept 45,488 B (the final base: 36,368 B), its largest free block after it 58,048 B
  (minimum 32,768 B; the final base: 72,128 B). Baseline alloc 70,672 / free 117,408 / largest 116,846; after the
  build 116,160 / 71,984 / 58,048; control 115,968 / 72,224 / 58,048; at the production threshold
  116,032 / 72,192 / 58,048. The map and the boot placement figures were not read: the test asserts the bound first.

## Bench step: 68 of the scope's 79 tests

59 passed, 2 failed, 6 errors. Out of the run by the owner's wear rule: the `.local` broker, both unresolvable names,
the status settings, the persistent session, the changed client id, the hotspot module's two PUTs and two
failed-credential stages, the unresolvable `NTPHost`.

**The MQTT module: 22 of 22 passed.**

| Test | Figure |
|---|---|
| connect and `online` | connected 0.7 s after the first link poll |
| the exerciser's echo probes | 3 probes 9.99 s apart; `MQTTLINK` Transfers 0 -> 3, Failures 0 |
| broker killed (5 s outage) | reconnected 2.5 s after its restart |
| broker stalled | detected in 18.8 s, reconnected 7.9 s after the resume |
| silent path loss | detected in 14.9 s ("no pingresp"), reconnected 13.4 s after the restore |
| reset path | ended in 9.6 s, reconnected 11.3 s after the restore |
| stall at 1/5/9/13 s after a probe | detected in 19.18/15.20/11.21/17.13 s (predicted 19/15/11/17) |
| duplicate client id | 0 retakes in 20 s against 1 by the duplicate; reconnected 39.9 s after it left |
| inbound flood | 3,001 of 3,001 taken; `GET /status` under it max 1.43 s, median 1.37 s |
| inbound QoS 1 burst | 500 acknowledged in 5.1 s |
| password broker | connected in 0.8 s, the password shown masked |
| wrong password | 5 refused attempts in 40 s; codes 116/117/119/120; connected 0.7 s after the correction |
| AP outage (30 s) | a recovery pass: no passive reconnect within 240 s, then the harness's kick and one hard reset; connected 256.7 s after the AP returned, 0 failed attempts logged (the bench's documented CYW43 case, as on both 2026-10-08 runs) |
| reboot | connected 12.2 s after the reset; the broker published the will on the takeover |
| the faults at MicroPython's default gc | every step passed; free heap 7,472-67,936 B over 42 samples |

**The other reds** (each rerun once):
- `test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status`, failed every time (13 within-cap
  refusals against `HTTPDropped` 8, then 10 against 5, then 11 against 10 under the capture). Root cause, from the pinned
  source and confirmed on the wire (relays 43 and 44): a connection that completes its handshake while modlwip's accept
  queue is full (the listen backlog, `max_connections + 1`, 6 on `dev`) gets `ERR_BUF` from `_lwip_tcp_accept()`, and
  lwIP aborts it; the server never sees it. In the capture the board reset 10 connections after receiving their
  request bytes, 31-175 ms after the handshake, the window's 10 W60 entries, and 15 more 1.4-5.6 ms after the
  handshake acknowledging only the SYN, 5 of them within-cap PUTs: the uncounted refusals. The test's bound assumes
  every refusal reaches the server. The owner, asked what should change: "Leave it to the base".
- `test_real_concurrent_client_burst_does_not_crash_the_webserver`, failed once and passed on its rerun: its final
  `GET /status` came the instant its clients finished, before `_serve()` released their slots. Fixed on the PR branch
  in `2b8b65ae` (the owner: "Add the wait here (Recommended)").
- Setup and teardown errors: SGP40 W33/W35 on five tests (the final base's known teardown codes); ISL29125 W31
  (`ISL_DIVERGED`, also among the final base's teardown codes); MQTT E3 `CFG_GET_RAISED` once in the default-gc heap
  window, the starved config read that test provokes for every config module, declared for MQTT in `2b8b65ae`.

At the end the board served the image with the client disabled; `LastTaskEnd` null.
