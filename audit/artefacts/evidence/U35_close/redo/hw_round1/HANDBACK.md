# Round 1 bench hand-back

Rebuilt by `round1.py` after every step, last 2026-11-05 07:56 UTC. Each verdict is its step's newest run; after step 4a a passing pytest step reads NOT CLEAN (lower levels skipped).

| step | name | verdict | ResetReason after | started (UTC) | took | host load at end | FC/FS/NVM/pre |
|---|---|---|---|---|---|---|---|
| 1 | evidence | rc=1 |  | 2026-11-05 07:52:48 | 0h00 | 0.28 | 0/0/0/0 |
| 2 | host_env | not run |  |  |  |  | 0/0/0/0 |
| 4a | lower_levels | not run |  |  |  |  | 0/0/0/0 |
| 3g | gc_control_image | not run |  |  |  |  | 1/0/0/0 |
| 4g | flash_tier_gc_control | not run |  |  |  |  | 0/0/1/136 |
| 5g | bench_tier_gc_control | not run |  |  |  |  | 0/0/0/66 |
| 3 | final_image | not run |  |  |  |  | 1/0/0/0 |
| 4b | flash_tier | not run |  |  |  |  | 0/0/0/136 |
| 5 | bench_tier | not run |  |  |  |  | 0/0/0/66 |
| 9 | crc16_hazards | not run |  |  |  |  | 0/0/0/0 |
| 10a | soak_short | not run |  |  |  |  | 0/0/0/8 |
| 10m | soak_mid | not run |  |  |  |  | 0/0/0/8 |
| 11 | fram_8mhz | not run |  |  |  |  | 0/0/0/0 |
| 12a | boot_stretch | not run |  |  |  |  | 0/0/0/0 |
| 12b | ring_peak | not run |  |  |  |  | 0/0/0/0 |
| 12c | dns_idle_poll | not run |  |  |  |  | 0/0/0/0 |
| 12d | reset_errors_budget | not run |  |  |  |  | 0/0/0/0 |
| 12e | general_call_per_chip | not run |  |  |  |  | 0/0/0/0 |
| 12f | held_sda_resets | not run |  |  |  |  | 0/0/0/0 |
| 16b | bmp3xx_probe | not run |  |  |  |  | 0/0/0/0 |
| 13 | country_scan | not run |  |  |  |  | 0/0/0/0 |
| 10c | soak_long_clock_stretch | not run |  |  |  |  | 0/0/0/0 |
| 10d | soak_long_core_headroom | not run |  |  |  |  | 0/0/0/0 |
| 10e | soak_long_bus_triggers | not run |  |  |  |  | 0/0/0/0 |
| 10f | soak_long_hammer | not run |  |  |  |  | 0/0/0/0 |
| 10g | soak_long_http_S4 | not run |  |  |  |  | 0/0/0/0 |
| 10h | soak_long_frc_baseline | not run |  |  |  |  | 0/0/0/0 |
| 7f | gated_flash | not run |  |  |  |  | 0/72/6/0 |
| 7b | gated_bench | not run |  |  |  |  | 0/50/7/0 |
| 8f | flash_cycles_flash | not run |  |  |  |  | 1/0/0/0 |
| 8b | flash_cycles_bench | not run |  |  |  |  | 4/0/0/0 |
| 10b | hotspot_case_b | not run |  |  |  |  | 0/4/0/2 |
| 15 | rollover | not run |  |  |  |  | 2/0/0/0 |

Wear started (the sheet's maxima per started step): FC 0 of 9, FS owned 0 of 126, NVM 0 of 14, prerequisite writes 0 of 422.

## Long runs summed (October's aggregate)

```

```

## Logs

### 1 evidence

<!-- step 1 -->
```
== step 1 start 2026-11-05 07:52:48 1793865168 load 0.18 0.07 0.09
SUM status not read: no JSON answer
Resolved 22 packages in 3ms
Audited 20 packages in 0.67ms
warning: `--no-sync` is a no-op for Python scripts with inline metadata, which always run in isolation
Traceback (most recent call last):
  File "<stdin>", line 8, in <module>
ImportError: no module named 'asy_spi_driver'
rc=1
== step 1 end rc=1 2026-11-05 07:53:08 20s load 0.28 0.10 0.10
== read-across: GET /status after step 1
SUM status not read: no JSON answer
```
<!-- end step -->
