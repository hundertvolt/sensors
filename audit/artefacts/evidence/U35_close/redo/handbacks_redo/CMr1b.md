CMr1b hand-back, saved by the lead from the message it sent (2026-10-27). Nothing committed; uncommitted work in S/wt-u35cmr1b (audit/u35-cmr1b at 52f691dc); its three timing batches were still running when it handed back.

CMr1b hand-back. I stopped early: my last command was refused by the safety classifier. It was `timeout 100 tail --pid=29497 -f /dev/null; awk ... times.txt | column -t`, a wait on my own timing batch plus a read of my own log, and the reason given was "Irreversible Local Destruction". Following the rule, I ran nothing after it.

**Nothing is committed.** Worktree S/wt-u35cmr1b, branch audit/u35-cmr1b, base 52f691dc, not pushed. The uncommitted work, by item:
- **Item 3 (deduplication), done and checked, not committed.**
  - tests/_twin_devices.py gets `wiring_read(device, *drivers)`. The key is built at run time from each named driver's generated construction statement (which carries its TOML settings), plus the pins and every occupant of each I2C bus, SPI bus or UART pair the driver sits on.
  - `distinct_wirings(*drivers)` keeps the first device of each distinct key; with no drivers named, the key covers every instance the device wires. The private helpers come first (D.15).
  - Applied in: integration `_driver_specific()` and its docstring, network_neopixel (keyed on neopixel and fram), and neopixel_wifi's `_devices_with_a_neopixel()` (whole-device key).
  - tests_scripts/test_twin_wiring_contract.py pins the grouping: 9 parametrized edits, one per read or unread key, plus a test that identical devices share a run. Seen failing first: red_group.log, 10 failed with AttributeError (no distinct_wirings or wiring_read). They now pass.
  - Groups measured on the real tree:

    | Drivers | Runs on |
    |---|---|
    | scd30 | arzi, dev |
    | sgp40 | arzi, dev, wozi |
    | fram | arzi, dev, grkizi |
    | neopixel | arzi, dev |
    | sgp40 + fram | arzi, dev, grkizi, wozi |
    | sgp40 + scd30 | arzi, dev, wozi |
    | notification + scd30 | arzi, dev |
    | notification + scd30 + sgp40 | arzi, dev, wozi |
    | bmp3xx | dev, wozi |
    | isl29125 | dev |
    | uart_link | dev |

- **Items 1 and 2 in bus_hazard, edited but not yet seen green.**
  - `_FRAM_DEVICES = distinct_wirings("fram")`. The 10 FRAM tests run through the new `_on_each()`, which calls the file's per-test reset (`machine`/`network.reset_test_state()`) before each device. That is the fix for defect 1.
  - The SGP40 race (formerly :714) runs per SGP40 wiring, with its bus built inside the run. That is the fix for defect 3.
  - The SCD30 system-command test runs per SCD30 wiring. Each word's port is reused by every device, and no band is widened. That is the fix for defect 2.
- **Item 1 in the other twin files, edited but not yet run.** fram (formerly :882), clock_jump (:163, :194), ntp (:376, :477) and hot_replug (`_replug`, :200) each loop over `distinct_wirings(...)` with a reset per device.

**Checks:**
- Green: lint_direct rc=0; mypy main and host passes clean; readers 802 passed (wiring_contract, comment_cap, citations, decision_vocabulary, tunables_register, port_bands, code_conventions, import_placement, no_variant_literals).
- The twin mypy pass flagged one `_on_each` signature. I fixed it with a typed factory; the pass is now clean from a cold cache and ruff is clean on the file.

**Runs still going (all mine, all niced, reading only the scratch trees in S/u35/laneC/cmr1b/trees, logging to S/u35/laneC/cmr1b/times.txt and RUNS.md, each file capped at 500-600 s):**
- batch1.sh, pid 29497: the integration file on 6 devices at both stages, then network_neopixel and neopixel_wifi, each on three trees (basebb=bb220714, base52=52f691dc, head=item 3) back to back. Partial results:
  - arzi, -1: 60.9 s on bb220714, 44.1 s on 52f691dc.
  - dev, 32768: 23.6 / 31.4 / 32.3 s; head ran 14 of 18 tests, as base52 did.
  - The rest will be in times.txt.
- batch2.sh, pid 30786: starts after batch1. It runs the red variants red_d1/d2/d3 (in trees/bh/tests/test_zz_red_*.py: no per-device reset; every device with a fresh port per boot; the SGP40 bus built before the run), then the bus_hazard file at both stages. Note the bh tree holds the earlier lambda form of the SCD30 call, so the final file needs one more run.
- batch3.sh, pid 31712: starts after batch2. It runs fram, clock_jump, ntp and hot_replug at both stages, on base52 then w2.
- A background wait (`tail --pid=29497`) ends when batch1 ends.
- The scratch trees (about 1.1 GB) are still in use by these runs. Delete them after.

**Remaining for the next block:**
- Read red_d*/bh_*/w_* in times.txt and the logs, and root-cause any red.
- Re-run the final bus_hazard file at both stages.
- Commit item 3, then items 1 and 2.
- Still to widen or classify: the scd30 helper (:54, its 4 tests; defect 3 applies there too), the sgp40 helper (:239), launch (:51), wifi_modes `_scenario_plan()`, and the tests_scripts `DEVICE_NAMES[0]` sites.
- Possibly deduplicate fram_less_boot and `_lag_run` the same way.
- Item 4's four bites.
- Item 5: the matrices.md rows. The file holds only its header; nothing is written.
- Item 6 sentence for D3r (SPECIFICATION.md E.2.1, about lines 5159-5163, not re-located): "A driver-specific scenario runs once per distinct wiring of its drivers: devices are grouped at run time by what the scenario reads of their generated plan and module (each driver's construction statement, and the pins and every occupant of each bus it sits on), and each group runs on its first device; a scenario no device setting reaches runs once on the first device wiring its drivers."

My batches are still running (pids 29497, 30786, 31712, and the tail wait); they end by themselves.
