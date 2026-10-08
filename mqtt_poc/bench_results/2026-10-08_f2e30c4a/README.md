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
