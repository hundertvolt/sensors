# MQTT PoC bench results, 2026-10-08 on `f2e30c4a`

The second image of the day, flashed to put the current code on the board (owner, 2026-10-08: "No soak test
required yet, but for the rest of your suggestions you have my go ahead.", the suggestions including "a fresh
flash of the current code"; the flash commands allowed for the session, owner, 2026-10-08: "Allowed for this
session."). The earlier image's results are in `../2026-10-08_51a5bd2d/`.

## Setup

| | |
|---|---|
| Commit | `f2e30c4a`: the `51a5bd2d` image's src plus the U18/U19 merges and the MQTTHost host-name check (`ea81cc0e`) |
| Image | `dev`, `BuildDate` 2026-10-08T16:56:05Z (`system_after_flash.json`) |
| Image replaced | `dev`, `BuildDate` 2026-10-08T09:47:36Z, `51a5bd2d` (`system_before_flash.json`) |
| Before the flash | `tests/` for the MQTT client, codec, DNS, NTP, web server and the dev graph: 589 tests at each GC stage, all passed, no memory marker; lint and the host typecheck clean |

## Preparation

- `fram_before_flash.json`: the old image's logs held WEBSERVER (2) and ISL29125 (1), left by attempt 6's
  serving sweep and heap tests on that image.
- Flash: `machine.bootloader()` over mpremote, then `sudo picotool load -x -v build/firmware-dev.uf2`, loaded
  and verified on the first attempt.
- **First boot joined the bench AP by itself**, serving about 15 s after the load (the first flash of the day
  fell back to hotspot and needed a kick and a hard reset).
- `fram_after_flash.json`: the logs carried across the flash. MQTT still holds the old image's attempt 7
  entries (`E 115` DNS, `E 119`/`E 120` from the stall sweep, `W 77`, the short-session warning's old number,
  82 since U19); new on this boot only WIFI `W 38` and CFGMGR_NTP `W 10` (`STORED_DEFAULT`, U18's new NTP
  keys). `MQTTState` `disabled`, NTP synced, all 24 FRAM modules present.

## The flash step (`flash_step/`): 1 of 3 passed, the same two as on `51a5bd2d`

`scripts/run_bench_hardware_suite.sh --skip-lower-levels --scope mqtt` with the four write groups.

- `test_real_gc_heap_headroom_survives_a_full_system_build`: **114,768 B against the 100,000 B tripwire**.
  The board's split: `baseline` 63,984 B (`51a5bd2d`: 62,720), `after_build_system` 114,560 B (113,072), so
  the graph is 50,576 B (50,352). U18/U19 add about 1.5 KB, nearly all at import; the largest free block is
  59,376 B (61,232), still above the 32,768 B contiguity floor.
- `test_every_fram_wired_module_gets_a_real_chunk_after_a_full_system_build`: the same stale expectation of a
  FRAM-backed `CFGMGR_SCD30`, which stays RAM-only (owner, 2026-09-29: 'no extra FRAM chunk').
- `test_env_tier_flash_recurring_run_is_idempotent`: passed.

The bench step then ran on its own, as on the first image.

## The bench step (`bench_step/`): 68 of 74 passed, every MQTT test among them

The scope's 24 bench entries on their own (`--skip-lower-levels`, the four write groups), 2026-10-08
18:00–18:56 UTC, 3,352 s: **68 passed, 5 failed, 1 skipped** (the permanent raw-socket spoofing skip).
`pytest.log`, `run_record.json` (every result note) and `console.log.gz` are the runner's own output.

**All 28 MQTT tests passed**, the 8 new ones included. The result notes beside the `51a5bd2d` image's
(attempt 4, and attempt 7 for the 8 new tests):

| Test | `51a5bd2d` | `f2e30c4a` |
|---|---|---|
| First connect after the poll | 1.3 s | 1.6 s |
| Largest measurement payload (384 B slot) | 245 B | 244 B |
| Broker killed for 5 s: reconnected after the restart | 4.2 s | 4.2 s |
| Broker stalled: detected / reconnected after the resume | 21.0 / 8.7 s | 19.3 / 9.4 s |
| Silent path loss: detected / reconnected | 21.5 / 13.8 s | 22.2 / 11.9 s |
| Reset path: connection ended / reconnected | 6.7 / 11.4 s | 9.3 / 11.7 s |
| Duplicate client id: retakes in 20 s / reconnected after it left | 0 / 39.8 s | 0 / 40.0 s |
| Inbound flood: messages taken; `GET /status` max / median | 3001 of 3001; 1.93 / 1.84 s | 3001 of 3001; 1.91 / 1.82 s |
| 500 QoS 1 messages acknowledged | 7.1 s | 7.1 s |
| `raspberrypi.local` broker: connected | 1.6 s | 1.7 s |
| Password broker: connected; back on the anonymous broker | 1.6 / 1.7 s | 1.6 / 1.5 s |
| Wrong password: refused attempts in 40 s; connected after the correction | 5; 1.7 s | 5; 1.5 s |
| `.invalid` name: `MQTT_DNS` first logged; reconnected after the restore | 4.1 / 1.5 s | 1.7 / 1.7 s |
| `.local` name: `MQTT_DNS` first logged; reconnected after the restore | 4.1 / 1.6 s | 4.2 / 1.6 s |
| Stall 1 / 5 / 9 / 13 s after the connect: detected (design 24 / 20 / 16 / 12 s) | 24.38 / 20.13 / 16.28 / 12.19 s | 24.13 / 20.30 / 16.23 / 12.28 s |
| Reconnected after each sweep stall | 61.5–63.5 s | 61.5–63.3 s |
| Reboot: connected after the reset, will published on the takeover | 15.8 s | 13.0 s |
| AP outage (recovery pass: a hard reset, 0 failed attempts logged) | 15.4 s | 15.3 s |
| **Fault run at MicroPython's default GC: lowest free heap over 42 samples** | **2,192 B** | **528 B** |

- **The one real change is the default-GC fault run's lowest free heap, 1,664 B lower.** That is about the
  ~1.5 KB U18/U19 add at import (the flash step above). The run passed with no memory marker, so the margin
  shrank and nothing failed.
- **The `.invalid` name logged `MQTT_DNS` at 1.7 s, against 4.1 s on `51a5bd2d`.** The `.local` name stayed at
  4.2 s. That fits U18's resolver asking its caller's servers, but this run did not show the cause.
- **Wrong password: the codes listed differ, but the behaviour does not.** The note prints the whole MQTT
  history, and this test does not clear it first. Here the earlier fault tests' `W 82`, `E 116`, `E 119` and
  `E 120` were still in it; in attempt 7 only the password test had run before it. In both runs the counter
  grew by 5, and each refusal was `E 117` (the test asserts it).
- Every other figure moved by no more than the run-to-run spread.

**The 5 failures, none from the MQTT changes:**

- `test_ntp_connected_socket_rejects_a_reply_from_an_unexpected_source`: `UTCTime` null, NTP not yet synced
  when the test started. The same precondition gap as on `51a5bd2d`.
- `test_connections_at_and_above_the_real_socket_limit_degrade_cleanly`,
  `test_the_board_holds_exactly_the_connection_ceiling_this_tree_configures`,
  `test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status` and
  `test_malformed_http_request_over_real_wireless_degrades_cleanly`:
  - Each found the WEBSERVER log not empty, holding `W 60` (`HTTP_REFUSED`, refused at the connection ceiling),
    `W 48` (`HTTP_PEER_RESET`) or `W 61` (`HTTP_BAD_HEAD`, the malformed request).
  - All four passed on `51a5bd2d`. The connection ceiling and the refusals themselves held: each test failed
    only at its closing log check.
  - U19 (`f5c82557`, "every dropped connection counted") now logs a warning for each refused, reset or
    bad-head connection through `_note_drop()`, while these four bench tests still assert that such a drop
    leaves WEBSERVER's log empty.
  - So the test and the code disagree, inside the audit's own U19. Outside this branch's MQTT scope (owner,
    2026-10-08: "ignore anything else so far which does not come from your changes"), so it was recorded,
    not changed.
