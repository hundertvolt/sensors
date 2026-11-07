N5r hand-back, saved by the lead from the message it sent (2026-10-26). Commit fe88bcbf on audit/u35-n5r.

N5r hand-back. Branch audit/u35-n5r, worktree S/wt-u35n5r, base df670c35. Commit fe88bcbf "U35 lane N5r: the machine fake's tests pick their board by its wiring, not by name". Only tests/test_digital_twin_machine.py changed (+45/-23). Not pushed. Nothing uncommitted is mine (node_modules was already there).

Item 1, applied. Every assertion is kept, and both boards resolve to the same devices as before: a probe printed "PICK wozi dev".
- New `_BOARD` and `_ISL29125_BOARD` give the hardware per bus: I2C as {address: driver}, SPI as (driver, max_size) or None. `_board()` returns the first generated device wiring exactly that, or raises an AssertionError naming the spec and every device searched.
- :626 `_wire(device="wozi")` is now `_wire(wiring=_BOARD)`, moved after `_value_error` (D.15 order).
- :376 and :389 `_wire("dev")` are now `_wire(_ISL29125_BOARD)`. The ISL irq pin comes from the plan instead of Pin(6). The two tests are renamed: test_an_isl29125_board_wires_it_on_i2c1_beside_scd30_and_sgp40 and test_an_isl29125_board_hands_the_chip_the_same_pin_object_the_driver_constructs.
- :1228 `_wire("dev")` is now `_wire(_ISL29125_BOARD)`, a board whose i2c1 carries no 0x77, so a replaced board would show.
- Two sites not on the old list, :1203 and :1586 (both opened `sensortask_wozi_wiring_plan.json`), now use `wiring_plan(_board(_BOARD))`.
- :397 test_wozi_wiring_carries_no_isl29125 is renamed test_a_board_without_the_isl29125_wires_none. The comments at :1, :108, :374 and :505 no longer name a device.
- tests/_boot_contiguity_probe.py: no name pick at this head. It takes its device from argv, and its consumer runs every device and picks its control device by instance count. Unchanged.
- The grep of tests/, tests_scripts/ and digital_twin/ found only labels, which stay: run_generic_integration :193/:194 `_reset_line("dev", …)` and :230 `_shutdown_line("wozi", …)` are line-format strings, and bus_hazard :400 is a comment.
- My form differs from the lost N5's `_board_plan(**buses)`, and I kept it on purpose:
  - it returns a device name, not a plan, so the FRAM test can modify a fresh copy of the plan;
  - I2C matching ignores the order of chips on a bus;
  - `_BOARD` also requires spi1 to be unwired, which the spi1 test assumes;
  - the board is looked up in each test, not at import, so a missing board fails only the tests that need it.

Bites (scratch copies, now deleted):
- Bite A changed the spec to 0x76: 38 of 113 tests fail with "no generated device wires … searched ['arzi', … 'wozi']".
- Bite B took the first device whatever it wires (arzi): 13 fail, including both ISL tests and every bmp3xx test.
- Logs: S/u35/laneR/n5r/bite{0,a,b}.log.

Item 3: stays green, and it sees every plan key my file reads (lines 117-119, 419, 1610), all declared. The scanner's shared-comprehension-scope defect is still there but nothing triggers it. It also has a blind spot: a variable unpacked from a list comprehension, `(x,) = [...]`, is not tracked. My first draft hid its `irq_pin` read that way, so I moved the read inside the comprehension.

Item 2, read only. Picks: `generated_devices()[0]`, `device_with(fram/sgp40/scd30/neopixel)` and `(notification, scd30)` give arzi; `device_with(bmp3xx/isl29125/uart_link)` gives dev.

Wiring that differs between devices:
- dev's FRAM is 256 KiB (RDID 04 7F 48 03); every other device has 8 KiB.
- dev's SCD30 is on i2c1 (irq 11), shared with SGP40 and ISL29125; on the others it is alone on i2c0 (irq 8).
- wozi's SGP40 shares i2c1 with its BMP3xx; dev's BMP3xx is alone on i2c0.
- dev's NeoPixel is on pin 18; the rest use pin 15.

| Verdict | Sites | Why |
|---|---|---|
| Differs | bus_hazard `_FRAM_DEVICE` (10 tests), :714, :1069; clock_jump :163, :194; fram :881; hot_replug :112 (scd30, sgp40, bmp3xx), :200; launch :51; network_neopixel :630; ntp :376, :477; scd30 :54; sgp40 :239; integration `_driver_specific` :552, :924, :1019, :1043, :1077, :1107, :1160, :1217, :1281 | the part each exercises is wired differently on at least one device (above) |
| Same | integration :788, isl29125_autorange :67, uart_link :81, hot_replug isl29125 | dev is the only device wiring that set |
| Same | integration :942 | asserts the DNS listener's idle rate only |
| Same | integration `_first_device_only` :748, :808, :878 | WiFi mechanism, no device setting touches it |
| Same | clock_jump :260, :299, :321, :339; ntp :345, :369, :439 | NTP and RTC have no device setting |
| Same | run_generic_integration :825, :901, :926 | asserts only the runner, WIFI config, NTP config, clock and flash stall |
| Same | loop_end :251, :259, :268 | identical entry code and reset record |
| Same within a size | fram_crash_points :221 | 8 KiB devices differ only in SPI pins and CS |
| Same | scripts/test.sh:181 | the unit tier only needs a site on its path; every device's site is built on a plain run |
| Same | tests_js/api-reference-agreement.test.js:53 | a self-test of the checks; `describe.each` covers every device |

Not classified: tests_scripts `DEVICE_NAMES[0]` (66 sites).

Checks:
- The changed file passes 113/113 at -1 and at 32768 with no memory-error lines (after2_m1.log, after2_32768.log).
- ruff clean; the mypy twin pass is clean from a cold cache (mypy_twin.log).
- The tests_scripts readers: 959 passed, 6 failed (readers2.log).
- One red is caused by my change: test_no_variant_literals::test_every_not_yet_cleaned_entry_still_carries_a_literal. Its row at tests_scripts/test_no_variant_literals.py:29 now refers to a clean file, and removing it is your edit.
- The other five reds are already red on a clean df670c35 (basereds.log). All come from the loop_end and generated-main merge, not from me:
  - code_conventions[no_print]: sensortask_*_main.py:42;
  - tunables_register: loop_end.py:64 and :66;
  - level_containment: loop_end;
  - microtest trailer;
  - microtest json_loads: loop_end :191.

Times: 1.163 / 1.180 s before, 1.192 / 1.248 s after (+2.5% / +5.8%). The base table has no row for this file, so I took one before-run.

Silent-failure scan (classes 1-7) over my diff: no finding. The only case is an empty spec, which would match any device; both specs are fixed and non-empty. The change touches tests only, so it has no effect in any operating mode, and it adds or changes no flash or NVM write.

No new stale documentation lines. SPECIFICATION.md E.2.1 still lacks the owner's 2026-10-23 device-pick ruling, which was already routed to D3.

Runs (all exited): before, after1, after2, bite0/a/b, readers1, readers2, basereds, mypy twin. Logs are in S/u35/laneR/n5r/. The temporary base worktree is removed and pruned.

nothing of mine is running
