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
