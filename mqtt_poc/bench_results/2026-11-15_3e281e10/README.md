# MQTT PoC bench run, 2026-11-15, image `3e281e10` (the trimmed client)

The record of relay 45's hand-back (the audit's bench session, branch `claude/u35-bench-campaign`, block `cb5915a6`).
The logs and the archive stay on the bench host (`logs/day9_20261115/*r45*`,
`build/archive/run_bench_hardware_suite_scope_mqtt/`, the 11:29 and 12:17 runs). The run before it, on `9fd691ef`, is
`../2026-11-15_9fd691ef/README.md`; its setup, wear rules and owner answers hold here too.

## What changed since that run

- The client's payload slots went 384 -> 256 B and its transmit buffer 640 -> 512 B (`7dd8af6e`; the owner, asked how
  `dev` with the client should meet the heap bound: "Try a balanced approach, find a sweet spot, far away from critical
  values, then re derive").
- The burst test waits for the slot release before its last probe; MQTT's two config-read codes are declared in the
  default-gc heap test (`2b8b65ae`).
- The scope's flash step gained the boot's heap layout (`3e281e10`).

## Setup

The owner in the bench session: "Yes, flash and run". One flash cycle (two that day); image 1,178,948 B (95.9 %), the
same as the run before (two constants changed), `"dirty": false`, BuildDate 2026-11-15T11:23:36Z. The FRAM layout is
the run before's, so the first boot kept every log; `MQTTState` "disabled", `MQTTLINK` 0/0/0. Writes: the flash, the
two login tests' 5 owned writes, the unmarked prerequisites; the rerun owned none.

## Flash step (4 tests)

| Figure | the final base (no client) | `9fd691ef` | `3e281e10` |
|---|---|---|---|
| kept by the build and its setups | 36,368 B | 45,488 B | 44,320 B |
| largest free block after the build (minimum 32,768 B) | 72,128 B | 58,048 B | 59,216 B |
| baseline alloc / free / largest | 67,280 / 120,800 / 118,992 | 70,672 / 117,408 / 116,846 | 70,688 / 117,392 / 116,880 |
| after the build alloc / free / largest | 103,648 / 84,496 / 72,128 | 116,160 / 71,984 / 58,048 | 115,008 / 73,136 / 59,216 |
| at the production threshold | 103,472 / 72,128 | 116,032 / 72,192 / 58,048 | 114,800 / 73,424 / 59,216 |
| new blocks above the 32,768 B high band (bound 32) | 0 | not in the scope then | 0 |
| boot starter loop / `build_system` / `start_timers` | 1,403 / 1,026 / 518 ms | not in the scope then | 1,470 / 1,293 / 520 ms |
| FRAM allocated | 1,140 B | 1,200 B | 1,200 B |

- FRAM chunk layout: PASS. Boot heap layout: PASS. `env --tier flash` rerun: deselected by its own gate.
- Full-build heap headroom: FAILED against the 41,000 B bound then in force, the expected red. The trim saved
  1,168 B, and the largest free block grew by the same amount. The bound was re-derived from this reading afterwards:
  44,320 B plus the same ~14 %, 50,500 B (agent, 2026-11-15). The map and the placement deltas were not read; the test
  reads them after the bound.

## Bench step: 68 of the scope's 79 tests

60 passed, 7 red. The burst test now passes.

**The MQTT module: 22 of 22 passed** (the run before in brackets).

| Test | Figure |
|---|---|
| connect and `online` | 0.7 s (0.7) |
| the exerciser's echo probes | 3 probes 9.99-10.04 s apart, Transfers 0 -> 3, Failures 0 (9.99 s) |
| broker killed | reconnected 2.4 s after its restart (2.5) |
| broker stalled | detected in 18.7 s, reconnected 8.0 s after the resume (18.8 / 7.9) |
| silent path loss | detected in 18.5 s, reconnected 15.1 s after the restore (14.9 / 13.4) |
| reset path | ended in 9.7 s, reconnected 11.1 s after the restore (9.6 / 11.3) |
| stall at 1/5/9/13 s after a probe | detected in 19.13/15.06/11.12/17.14 s (predicted 19/15/11/17) |
| duplicate client id | 0 retakes in 20 s, reconnected 39.8 s after it left (39.9) |
| inbound flood | 3,001 of 3,001; `GET /status` under it max 1.43 s, median 1.38 s |
| inbound QoS 1 burst | 500 acknowledged in 5.4 s (5.1) |
| password broker | connected in 0.8 s, the password shown masked |
| wrong password | 5 refused attempts in 40 s, connected 0.8 s after the correction |
| AP outage (30 s) | the same recovery pass: connected 257.7 s after the AP returned (256.7) |
| reboot | connected 12.0 s after the reset; the will published on the takeover (12.2) |
| the faults at MicroPython's default gc | every step passed; free heap 3,760-69,152 B over 42 samples, 17 collects (at the reactive default a low sample is no margin) |

**The reds:**
- `test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status`, as expected and not rerun:
  `HTTPDropped` 7 against 9 within-cap refusals (10 more over the cap). The base's, root-caused in the run before.
- Teardown errors, the same on the rerun: SGP40 W33/W35 on five tests (the final base's teardown codes).
- `test_real_hardware_survives_max_speed_hammer_load_without_memoryerror_or_reboot` errored at its setup in both runs,
  as it did in the run before: ISL29125's W31 `ISL_DIVERGED` from the default-gc heap pair before it, which that test
  does not declare. So the hammer load with the client resident has not run yet.

At the end the board served the image with the client disabled; `ResetReason` 21, `LastTaskEnd` null.
