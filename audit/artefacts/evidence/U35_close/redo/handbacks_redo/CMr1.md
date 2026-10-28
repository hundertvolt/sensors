CMr1 hand-back, saved by the lead from the message it sent (2026-10-27). Commits 7f1ba012, 8059785c, 1fe006ea, f5e74027 on audit/u35-cmr1 (on bb220714).

CMr1 hand-back. Branch audit/u35-cmr1, worktree S/wt-u35cmr1, base bb220714. Not pushed, nothing uncommitted. After the 01:28 restart nothing of mine was running, and the worktree and logs matched my records. Logs are in S/u35/laneC/cmr1/. I stopped at a seam at about 75 tool calls.

**Commits (each green on its own)**
- 7f1ba012: tests/_twin_devices.py gets `devices_with(*drivers)`, which raises when no device wires the drivers; `device_with` now returns its first entry. The plan-key scanner in tests_scripts/test_twin_wiring_contract.py now gives each comprehension its own scope, types what a comprehension returns, and follows names unpacked from it (`(x,) = [...]`). Three new tests.
- 8059785c: integration `_driver_specific()` now runs a scenario on every device whose plan wires its drivers.
  - :942 (DNS listener idle rate) moves to the new `_first_device_wiring("neopixel")`, with its reason in the comment.
  - `_hotspot_boot` now steps the streak at 10 ms and sets the twin join to 0.05 s for that boot only. Ten polls still outlast the join, and no hotspot assertion reads its length.
  - Docstring updated.
- 1fe006ea: network_neopixel :630 loops `devices_with("neopixel")`, with the body moved into `_restart_ends_dark(device)` in D.15 order. In neopixel_wifi, `_devices_with_a_neopixel()` asserts a non-empty list and the timer-list test loops over it.
- f5e74027: test_fram_less_boot's two tests and the scenarios file's `_lag_run` and its 4 tests are parametrized over DEVICE_NAMES.

**Seen failing first**
red_contract.log: 3 failed.
- `test_each_comprehension_reads_its_own_names`: the old scanner flagged `(3,'I2CAttachment','max_size')`, the false positive. The new one does not.
- `test_a_name_unpacked_...`: the old scanner returned none of the reads behind `(chip,)`. The new one catches `irq_pin` and the undeclared `clk`.
- devices_with: AttributeError.
All three are green in green_contract.log (41 passed).

**Sites and their class (measured from plans and TOMLs, measure.txt)**
What differs between devices:
- NeoPixel pin: 18 on dev, 15 elsewhere.
- FRAM: 256 KiB on dev, 8 KiB elsewhere.
- dev puts scd30, sgp40 and isl29125 on i2c1 (scd30 irq 11); wozi puts sgp40 and bmp3xx on i2c1; on the others scd30 and sgp40 are each alone.
- Only dev has UART.

Changed to every device wiring the part:
- integration :552, :924, :1019, :1043, :1077, :1107, :1160, :1217, :1281
- network_neopixel :630; neopixel_wifi's pick; fram_less_boot :92/:98
- `_lag_run` and its callers: dev's smallest hard consumer is 925 ms against 6000 ms elsewhere, and only dev has link roles.

Stay as they are:
- integration :788: only dev wires all three drivers, and the new helper gives exactly [dev].
- integration :942: it asserts only asy_udp_socket's poll_idle_ms rate. No TOML key reaches it, and the boot's conn_fail_to_hotspot is 5 on every device.

**Not done; for the next block**
- bus_hazard `_FRAM_DEVICE` (10 tests), :714, :1069; fram :882; clock_jump :163/:194; ntp :376/:477; scd30 :54; sgp40 :239; hot_replug :112/:200; launch :51.
- All three per-device defects (item 2) live in these files, so none was reproduced or fixed here.
- Found late and not classified: tests/test_digital_twin_wifi_modes.py, which boots the first device wiring neopixel and fram.
- Not reclassified: the other `DEVICE_NAMES[0]` sites in tests_scripts, including scenarios :229, :231, :344, :345, :356, :391, :464.
- No audit/b3/matrices.md rows were written.

**Times (s), base then head back to back**
- Integration, summed over 6 jobs: at -1, 166.7 → 181.6 (+8.9%); at 32768, 169.6 → 186.8 (+10.1%).
  - Per job: arzi 61 → 44. Each other job +6 to +8 s, about +30% (for example wozi 21.0 → 27.5, dev 22.9 → 30.0).
  - These per-job and 32768 figures are over CHECKLIST 14's 10%. They are for you or the owner to decide.
  - Measured: a boot per scenario costs only 0.2-1.0 s. CM's +27 s per job was 22 s of hotspot streak (9.5 s and 12.5 s). So sharing one boot would save at most about 3 s per job; the streak stepping is what cut the cost.
  - One more option, unasked and not implemented: grkizi, klkizi and schlafzi have identical plans, so they could be deduplicated by wiring.
- network_neopixel: 14.77/14.87 → 16.48/16.95 (+12% / +14%).
- neopixel_wifi: 3.22/3.08 → 4.13/4.52.
- fram_less_boot boots: about 0.16-0.23 s each per device.
- Every run passed with mem=0 at both stages: all 24 integration runs and all 8 NeoPixel runs.

**Bite**
A copy of head with wozi's `[instance.wiring.warn_co2]` removed and regenerated. The new integration file fails on wozi in 2 tests (window test at :1185, stopped-scd30 test at :1242). The base file passes there with 14 tests skipped (bite_new_wozi.log, bite_old_wozi.log). No bite yet for network_neopixel, neopixel_wifi, fram_less_boot or `_lag_run`.

**Checks, all green**
- lint_direct rc=0.
- mypy main, twin and host passes all clean from a cold cache; the typings link was removed afterwards.
- Readers and doc checks (readers.log): wiring_contract, fram_less_boot, scenarios, device_tomls, import_placement, port_bands, tunables_register, code_conventions, no_variant_literals, citations, decision_vocabulary. The only red was a 4-line docstring caught by the comment cap, fixed before commit; the comment-cap, citations and vocabulary checks were re-run afterwards: 664 passed.
- Silent-failure check: every device list either raises or asserts non-empty.

**D3 sentence**
SPECIFICATION.md lines 5159-5163 (E.2.1) still say the integration file "runs its driver-specific scenarios only on the device `tests/_twin_devices.py` picks for them". It should now say they run on every device whose plan wires their drivers, and that :942 (a mechanism no device setting reaches) runs on the first device wiring a NeoPixel.

Runs: every run has start and done lines in RUNS.md, all exited. The scratch tree copies (base, head, bite) are deleted.

nothing of mine is running
