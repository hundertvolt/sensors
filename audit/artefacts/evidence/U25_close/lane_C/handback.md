WIP 9230f0d (branch audit/u25-c, S/wt-u25c, base 8e7dedc; rebuild.sh rc 0; node_modules copied, lock hash identical). Stopped at C1 as briefed.
Applied (C1): renames SGP40Chip/SCD30Chip/BMP3XXChip/ISL29125Chip/FRAMChip; timer_factory replaces auto_refresh and the runtime `from machine import Timer` (no factory: no Timer; built once, re-init'd); module-top `import random` (BMP/ISL/SCD30); SCD30Chip(random_source, co2, temp, hum, rdy_pin, nvm=SCD30Nvm(2, True), *, timer_factory, state_path); power_cycle() on all four I2C chips (ISL: was simulate_brownout); SGP40Chip.handle_general_call() (+`resets`, `_measuring`); knobs silent/drop_next_wren/rdid_once (FRAM), corrupt_next() (SGP40, SCD30; replaces corrupt_next_reply/corrupt_next_measurement), rdy_stuck_high (SCD30); FRAMChip(size, rdid_response, state_path=None), `_DEFAULT_RDID` gone, header rewritten; FaultInjector(raisable_ops=) with TEST_API, inject_fault(op, exc_type, *args, times=1, match=None) (times<1 ValueError, refused op ValueError "'<op>' cannot raise on this bus (rp2) - see digital_twin/README.md's fidelity table"), maybe_raise(op, key=None): fresh exc_type(*args), oldest entry whose match accepts the key (A-27); chips pass command word / register / opcode; FRAM raisable_ops=("readinto",), its write() no longer raises.
Deviations: counters plain `+= 1` and FRAM fills unchanged until M1's saturating_add/fill_buffer exist (switched after <API>); SCD30 `_measuring` stored but not yet gating (later step); BMP power-up values still 0 (step 20). D.15 reorder deferred to the final (last edit).
Seen failing first (old 8e7dedc chips + scratch name aliases, S/u25/laneC/old, logs old_*.log): sgp40 general call (AttributeError handle_general_call/_measuring), power_cycle, corrupt_next, keyed read fault (TypeError inject_fault); bmp3xx power_cycle, keyed register fault; isl29125 no-factory test :526 AssertionError, timer_factory TypeError, power_cycle; scd30 fresh exceptions :319, match 0x0300 :335, keyed write :350, oldest-match :362, times=0 :381, timer factory :306, power_cycle :394, rdy_stuck_high :408 AssertionError, corrupt_next :234/:559; fram RDID required :165, rdid_once :173, drop_next_wren :182, silent :197, refused write :209, keyed readinto :414.
New tree: sgp40 21/21, bmp3xx 24/24, isl29125 44/44 at -1 and 32768; scd30 44/47, fram 29/35 at both stages, 0 memory markers. ruff clean; twin mypy: my files clean.
Red, waiting on MN1 (MN): digital_twin/machine.py:26, 379-395, 535-538 (old names; must pass timer_factory, and a required bytes RDID: `_FRAM_RDID_BY_MAX_SIZE.get()` gives None for 8 KB); tests/test_digital_twin_machine.py:121, 342, 479, 490 (old inject_fault form). My booted cases: scd30 test_a_booted_reader_on_a_constant_co2_twin_..., test_the_real_reader_accepts_a_reading_at_the_largest_temperature_offset, test_two_identical_puts_write_the_chip_nvm_only_...; fram test_a_blank_chunk_..., test_a_chunk_on_the_twin_chip_..., test_a_persistent_chip_read_fault_..., test_a_persistent_overrun_..., test_every_chunk_operation_stays_silent_..., test_the_timestamped_chunk_read_... (all ImportError via machine.py). The fresh exceptions make check_inject_fault_fifo pass once MN's `_twin_injector` (:121) uses the new form: MN drops its pending entry (:85) on <API>.
Red, other lanes: R digital_twin/launch.py:193-202, run_generic_integration.py:144-154 (`_apply_fault` old form); P tests/_digital_twin_construction_scenarios.py:184; G1 (wave 2) test_digital_twin_bus_hazard_concurrency.py:296 (a fram `write` fault is now refused), :344, :878; test_digital_twin_isl29125_autorange.py:16, 62, 90, 559, 584; test_digital_twin_generic_wiring.py:117, 162 (default RDID).
Retired for the lead: tests_scripts/test_import_placement.py:48, 50, 51, 52, 53 (the five Bmp3xx/Isl29125/Scd30 rows); tests_scripts/_decision_vocab_allowlist.txt:142 (_isl29125_chip.py "That flag is the whole signal ..."). Both checks red until the lead removes them. Other 10 convention checks green.
Scan (WIP diff, by site and by mode: chip re-plug, silent/lost FRAM, general call, fault refusal): fixed here, the fake raised on rp2 SPI writes, which the port cannot produce; new, twin-only: inject_hang accepts times<1 silently (_fault_injection.py:35); the packet keeps inject_hang unchanged, so not fixed. Covered by later steps: silent load fallbacks (M.TWIN.011/.013 (1)), counters unbounded (A.U25.23).
Facts for D: A-21 closed as modelled: silent FRAM reads 0x00 (SO High-Z, MB85RS64V p10; the RP2040 pad reset pull-down PDE=1, datasheet Table 341; machine_spi.c:209-213 sets only the function, pico-sdk gpio.c:42-48 leaves the pulls). Old names in SPECIFICATION.md:4601, 9928 and digital_twin/README.md:65, 356, 401, 740.
After-times: no comparable numbers yet (scd30/fram have red booted cases; the rest run in 20-30 ms, all noise); I measure at the final.
Runs: one over a minute (the 12-check pytest, 84.7 s, rc 1 for the two lead rows), its RUNS.md lines written after it exited. Nothing of mine is running. /usr/bin/time is missing on the host, so I time with bash `time`.

---

FINAL b6f50ac (audit/u25-c, S/wt-u25c, on 05ec861 = 9230f0d WIP + merge of audit/u25-api1 e34ffd6; rebuild.sh rc 0). The 13 files are listed in S/u25/files_C.txt.
Steps by verdict:
- 18: the rename had already landed at 8e7dedc (_crc8.py:1). I added the _CRC_POLY citation.
- Applied in full: 19+113 (SGP40), 20+99 (BMP3XX), 32 (FaultInjector, FRAM, ISL29125, SCD30, plus point 9: inject_hang(times<1) now raises ValueError), 101, 112, 120, 85, and the citations. Counters now use saturating_add and FRAM fills use fill_buffer.
- 30/31/138 verify only, both hold: tests_js/mock-server.test.js:596 asserts 400 on a fresh mock and :606 asserts 900 after a 900 PUT; mockdata/samples.json:9 has ForceCalRef 400.
Deviations:
(1) The SGP40 VOCState case drives the real reader over the bus of device_with("sgp40"), as the SCD30 booted cases do; it does not go through build_system. The silent-FRAM case does use build_system (A-20).
(2) FRAM rollover copies at most two slices instead of byte by byte; the result is the same.
(3) An RDID read past 4 bytes holds the ID's last bit, per both FRAM datasheets p10 (MB85RS2MTA reads 0xFF).
(4) test_a_persistent_chip_read_fault… assumed failing status-byte reads, which rp2 cannot produce once only 32+ byte reads raise. I rewrote it, and the timestamped case, to the rp2 outcome: None, busy markers left, False until the next write.
(5) For A-29, I planted a drift in each of the 16 copies in tests/test_digital_twin_isl29125.py. test_const_mirrors caught 6 (_MODE_RGB, _INTSEL_GREEN, three _STATUS_*, _DEVICE_ID) and missed 10: seven _ADDR_*, _RNG_HIGH, _BITS_12, _STATUS_RGBCF_MASK. The new test_isl29125_copies.py covers those missed copies plus the chip fake's 14 copies and autorange's _CHIP_GAIN_RATIO and _SWITCH_UP_LUX; its 25 planted drifts all fail. _ADDR_CONFIG3 is not compared: the driver has no CONFIG3 register.
(6) Two SCD30 booted cases now run under FastAsyncSleep (1.58 s → 0.26 s), and the PUT case gets a scratch cfg_path (before, it wrote its config into the cwd).
(7) The ISL topical headings went with the D.15 reorder, which is the last edit of every file.
Seen failing first (C1's list is in the WIP report). Pre-step tree: S/u25/laneC/pre, logs pre_*.log.
- sgp40: heater-off, raw walk.
- bmp3xx: OSR 0x02/CONFIG 0x00 at power-up and after 0xB6, probe hang.
- isl29125: PRST count stop, probe hang.
- scd30: 13 cases (FRC volatile, FRC/interval ranges, wrong CRC, stop/start, unprovisioned chip, soft reset, measuring persisted, json/shape/type load lines, ranges); inject_hang :689 failed on the tree before the fix.
- fram: 14 cases (wrap both ways, one-write framing, 32-byte gate, DMA pin, RDID tail, RDID table, write counting, marker/size/truncated lines, atomic save).
- Guards that passed at once all fail on a scratch bite: the SGP40 CRC and VOCState cases, the BMP probe image and probe fault, FRAM dropped WREN, missing-file silence, write protect (driver bite), silent recovery (driver bite on lost.clear), blank double read, and on SCD30 the RDY-stuck case, clear(), and state_path None.
Runs: five files × (-1, 32768, settrace) all pass with 0 memory markers: sgp40 24, bmp3xx 26, isl29125 47, scd30 55, fram 48. ruff clean. Host mypy clean. Twin mypy: only the configure_wiring lines below.
Red checks and who they wait on:
- Twin mypy reports configure_wiring(TwinWiringPlan) as arg-type at test_digital_twin_scd30.py:55, test_digital_twin_fram.py:829 and test_digital_twin_sgp40.py:241. It comes from digital_twin/machine.py:318 taking "dict[str, Any]" against P's TypedDict, and the same error is in launch.py:385 and other files. Waits on MN/P or the lead.
- test_tunables_register: my three new tags have no Part N row yet. Waits on X.
- MN: tests/test_digital_twin_machine.py:237 reads scd30._min_co2, which is now scd30.co2.lo. :517 expects OSR 0x00 at power-up; it is now 0x02. :146 and :352 still use the old inject_fault form.
- The other-lane reds from the WIP report stand (G1's bus_hazard, isl29125_autorange and generic_wiring files).
Scan (by site and by mode: first boot, after a firmware change, power loss, twin SIGINT, re-plug, silent FRAM, general call, runtime limits). Everything found was fixed in this unit; no new open findings:
- class 4: the FRAM and SCD30 state loads fell back silently; now one line with a fixed reason word.
- class 5: non-atomic saves; now .tmp then rename (extmod/vfs_posix.c:340-349).
- class 1 (reverse): FRAM faults rp2 cannot produce; now refused.
- Counters could grow unbounded; now saturating, PRST bounded.
- inject_hang(times<1) was accepted silently; now refused.
Facts for D:
- New tags: l2.bmp3xx_probe_hang_s = 0.05 (tests/test_digital_twin_bmp3xx.py:15) and l2.isl29125_probe_hang_s = 0.05 (test_digital_twin_isl29125.py:34), basis "a bounded small hang"; l2.fram_booted_until_yields = 2000 (test_digital_twin_fram.py:61), a scheduler-yield bound for the supervisor passes.
- Fidelity rows, FRAM: framing by write() pairing; rollover; write faults refused; faults only on reads of 32+ bytes (machine_spi.c:312-315); silent reads 0x00 (A-21 closed as modelled: SO High-Z per MB85RS64V p10, RP2040 Table 341 pad pull-down PDE=1); the RDID tail bit.
- Fidelity rows, SCD30: provisioned measuring default; wrong-CRC, interval and FRC out-of-range are assumptions; volatile FRC (1.4.6); soft reset = power-up (1.4.10); pressure persistence is an assumption; RH is not shifted by the offset (A-19); altitude overwrite not modelled; the counter counts accepted commands only.
- Fidelity rows, others: SGP40 general call (Table 17), heater-off (Table 14), unknown command an assumption; BMP chip id 0x60 and reset values (DS001 register map, 4.3.22), calibration synthetic; ISL PRST bound and the CONFIG1 restart an assumption.
- API end state: C1's, plus SGP40Chip.raw and heater_offs; SCD30Chip.co2/temp/hum, bad_crc_commands and SCD30Nvm; FRAMChip.write_count, writes_at and writes_at_dropped; a TEST_API on every chip.
- Old names to update: SPECIFICATION.md:4601, 9928 and digital_twin/README.md:65, 356, 401, 740. The README sections "SCD30 persistence" (six keys) and "FRAM persistence" (the load line, the atomic save) need the new behaviour.
Facts for the lead:
- My changes retired tests_scripts/test_import_placement.py:64-65 and tests_scripts/_decision_vocab_allowlist.txt:138, 141 and 376.
- test_no_variant_literals' _fram_chip.py entry, which you already retired, went with the _DEFAULT_RDID removal.
After-times, -1/32768 against base:
- sgp40 0.08/0.12 (0.02/0.03): new driver-level cases, CPU cost.
- bmp3xx 0.07/0.09 (0.02/0.05) and isl29125 0.08/0.08 (0.03/0.03): the 50 ms probe hang in each.
- fram 0.70/1.35 (0.20/0.29): the build_system boot, about 370 ms of construction CPU. Fast sleeps gained nothing.
- scd30 0.26/1.29 (1.58/1.93): faster than base.
- Settrace: 0.13, 0.10, 0.12, 2.04, 2.52 s in the same order.
Runs over a minute: the two convention pytest runs, 84.7 s (rc 1, the WIP's two lead rows) and 102.5 s (rc 1, the three reds above), each with its RUNS.md lines. Nothing of mine is running.
