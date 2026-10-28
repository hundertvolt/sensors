CO5 hand-back, written by the lane (2026-10-27 15:05 UTC; final checks appended at the end)

Lane CO5, branch audit/u35-conf2, worktree S/wt-u35conf2, started on 158058ed. Nothing is pushed. Logs are in
S/u35/laneB/co5/ (run wrapper run.sh; both-stage runner files.sh/both.sh; one-test runner one.sh).

## Commits
1. 05f1a8d3 item 0: level containment for held_i2c_line and setup_resets; the sgp40 suppression form.
2. cf8b130f item 2: the twin FRAM chip's stick_next_wrdi and corrupt_next_write knobs, and U16's two L2 cells.
3. 6d9d3c34 item 3: U18's hotspot-timer L2 cell (an existing twin test, cited and bitten). Audit text only.
4. e35fb0f6 item 4: U18's UDP socket L2 cells (R1, R2), and the OverflowError proof the lead asked for.
5. 1fd9db0f item 5: review.md re-rendered; review_rows.py --check green.
Item 1 is a measurement: no commit (no src change, as briefed); its record is below and in the logs.

## Item 0: the merge check's containment reader
- setup_resets: the dev bench can run it without wear or risk, so it gets the counterpart.
  - New device script tests_hardware/device_scripts/setup_resets_each_chip_once.py runs each I2C chip's driver setup()
    on silicon. A recorder stands in for the wrapper's machine.I2C and records every transfer.
  - New flash test test_bus_concurrency.py::test_every_chip_setup_resets_it_once_after_a_read_identified_it checks:
    one soft reset per chip, after the read that identified it, then a valid read. The resets are the datasheets'
    (SCD30 0xD304, BMP3xx 0xB6 to 0x7E, ISL29125 0x46 to 0x00, SGP40 the general call 0x06).
  - Every write is a volatile command or register: no NVM, no flash. setup() already runs ungated in other L3 scripts.
  - The module now names setup_resets. E.6.6 flash-only-bus-checks lists the L4 gap; README's rung table has the row.
  - Run with --twin at both stages: pass. Bitten under --twin on three plants in a scratch copy, each red:
    - BMP3XX setup without its reset: "0 reset write(s) 7eb6 to 0x77";
    - ISL29125 reset before its ID check: "reset before any read identified it (reads at [3, 5], reset at 1)";
    - SCD30 reset twice: "2 reset write(s) d304".
- held_i2c_line gets an E.6.6 row, held-i2c-line-silicon: the bench cannot hold SCL.
  - No bench chip holds SCL past its bounded clock stretch (SCD30 Interface Description 1.1). No other pin is wired
    to an SCL (dev.toml; README's wiring). The clear's own Pin(..., OPEN_DRAIN, value=1) takes back any hold the RP2040
    makes itself (ports/rp2/machine_pin.c:287-288). No fault-injection rig will be bought (owner, bus-fault-injection).
  - Its held-SDA clears already run at L3 (test_a_held_sda_line_is_cleared_and_every_device_answers), in a module that
    does not name the family. Its once-only report is the reader's _init_done(), which that isolated-driver script
    does not construct, so a script holding SDA under the full graph's boot is a gap until written. The twin cannot
    run held-SDA scripts (twin_record: bit-banged pins hold no SDA in the twin), so that script would be silicon-first.
- test_digital_twin_sgp40.py:314: the type-ignore code list is now comma-space separated.
- Whole tests_scripts tier on this commit (tier0.log): 7001 passed, 6 skipped. The three reds were the known ones:
  member_order (D2S's) and test_twin_record's two. My new device script now also appears in
  test_every_instrument_has_an_entry's list; twin_record.json is not mine to edit.

## Item 1: the FRAM fault's log pair, measured
Method:
- A scratch script (m_overrun.py) boots each device's generated graph on the twin, on one driven clock.
- It counts every FRAM chunk read and every code the FRAM manager's ring keeps.
- Per device, two boots. Boot A is fault-free: it fills the twin chip (15 driven minutes), then saves it. Boot B uses
  that chip with CO4's RX-overrun plant held sticky from before the setups: every SPI read of 32+ bytes raises EIO,
  and the chip stays present. Boot B then runs one driven hour.
- All six devices, logs mA_/mB_<device>.log.
Results, the same on every device:
- Reads per boot: one per FRAM-backed logger, then one SGP40 VOC backup read. The logger reads are 13 bytes each
  (16 on wozi, 14 on arzi, grkizi, klkizi and schlafzi, 20 on dev). The backup read is 268 bytes, at the first SGP40
  cycle (2.4-2.7 driven s). Logger chunks are 2+10+1 bytes, under rp2's 32-byte DMA threshold, so they never overrun.
- The one 268-byte read faults on both blocks. It logs E23 UNEXPECTED ("General read error in _read_chunk: EIO") and
  W63 FRAM_BLOCK_INVALID ("Read fault in block 0, reading block 1"). Then block 1 logs E23 again and W63 ("Read fault
  in block 1"). The read returns None. That is 4 ring slots, count 4: two per faulting block, four per chunk read.
- SGP40 logs one W65 SGP_NO_BACKUP. It sets _voc_init = 0, so no further restore read happens in that boot.
- Per hour after the boot: 0 further 32+ byte reads and 0 further FRAM entries (the marks at 10 min and 60 min).
  - Backups keep being written every minute: W35, written without timestamp, offline NTP.
  - Verified writes read back through the 8-byte check buffer (check_length=8), which is under the threshold.
- Does anything end the repeats? Nothing ends the fault. The repeats stop only because the product makes no further
  32+ byte read in that boot. CO4's "a fault that persists ends at the chip-loss probe" is not what happens:
  - _read() returns None for a fault before _blank_verdict() ("return None if fault or fault1 else ...", the read
    path in asy_fram_manager.py), so verify_present() never runs;
  - measured: no FRAM_CHIP_LOST, the lost flag never set, writes continue.
- Evictions: the FRAM manager's ring is RAM-only (log_ram) and starts every boot empty (count 0 after the setups,
  measured). The four entries take 4 of 10 slots and evict nothing. They would go only after six later distinct
  FRAM-manager entries in that boot; there were none in the hour. No other module's ring is touched (SGP40's W65 is
  its own). A fault that starts after the boot's restore read adds no entry at all until the next boot.
- Control (boot A, fault-free): the same read pattern and zero FRAM entries.
The designs, as GET /status's FRAM entry would read after such a boot (replayed on the measured sequence,
m_designs.py, designs2.log):
- (a) Keep the pair, as today: ErrCount 4, ErrNum/ErrType ... E23 W63 E23 W63 (6 empty slots).
- (b) Fold a repeated pair (a code equal to either of the two newest raises only the count): ErrCount 4, ... E23 W63.
  This changes the newest-entry rule (C.7.1) for every logger, not only FRAM's.
- (c) Log the fall-through once per fault run: ErrCount 3, ... E23 W63 E23. This drops the block-1 warning, the one
  that says no copy was left.
- SGP40's entry is the same in all three: W65.
A related shape the lead may weigh with it: a verified write whose readback fails its CRC also logs two entries,
E49 FRAM_DATA_CRC then E50 FRAM_VERIFY. L1 pins this (test_a_verify_pass_whose_block_read_fails_the_crc_logs_fram_data_crc),
and item 2's twin test pins it again.

## Item 2: U16's two cells (datasheet first: MB85RS64V DS501-00015 p.6, p.7, p.9; MB85RS2MTA DS501-00032 p.6)
- Twin knobs in digital_twin/_fram_chip.py, default off, modelled on drop_next_wren:
  - stick_next_wrdi: each WRDI while > 0 leaves WEL set. This is the WEL a lost WRDI leaves on the MB85RS2MTA, which
    keeps WEL after a WRITE (continual programming). The twin models the 64V's WEL clear at WRITE, so the knob sets
    WEL; a fidelity row now says so.
  - corrupt_next_write: each payload WRITE while > 0 stores bit 0 of its first byte flipped (a bit error on SI,
    written as received).
- Tests in tests/test_digital_twin_fram.py, all red first against the base twin chip (red2.log):
  - test_stick_next_wrdi_leaves_wel_set_for_that_many_wrdis_and_no_more (red: "WEL after each WRDI: [False, False,
    False]");
  - test_corrupt_next_write_flips_bit_0_of_that_many_payload_writes_and_no_more (red: "stored (b'\xaa', b'\xaa\xbb',
    ...)");
  - test_a_latch_one_wrdi_leaves_set_clears_on_the_retry_and_a_stuck_one_warns_once_per_event_with_the_payload_landed
    (red: knob left at 1).
    - Bites: the WRDI retry removed: "one WRDI left set: ... (1, [('W', 27)])" (biteW1). The stuck warning logged
      twice: "(2, [('W', 27)])" (biteW2).
  - test_a_verified_write_the_chip_stored_wrong_fails_once_rewrites_nothing_and_the_next_write_heals (red: "answered
    True after 2 payload writes").
    - Bites: an immediate rewrite: "after 3 payload writes" (biteV1). The mismatch reported as success: "answered True"
      (biteV2).
- Walk cells: U16 "latch does not clear after WRDI" R1 and "write verification mismatch" R1, L2 named.

## Item 3: U18 "hotspot timer cannot be armed" R1, L2
- The twin test already exists and the record had missed it:
  test_digital_twin_wifi_modes.py::test_stations_rule_settings_change_and_silent_mode_in_one_boot.
  - It empties the alarm pool while the reopened hotspot's window arms and while the silent mode's period arms.
  - It checks one E TIMER each, the streak fed, the timer not running and no "timer started" line, then the arm once
    the pool frees.
- It was cited rather than duplicated, and bitten on two plants:
  - a refused arm marked running: "the timer reads running after a refused arm" (biteH1);
  - a refused arm never retried: "the settings change's failed streak never opened the hotspot's window" (biteH2).

## Item 4: U18 "a UDP socket cannot be set up, bound or connected", R1 and R2, L2
- New helper tests/_udp_step_fault.py, FailNextUdpSetup. It fails the next product socket at socket() (ENOMEM), or at
  connect()/bind() (the shim's refused sockaddr, which the host kernel rejects with EINVAL). It keeps every socket it
  made.
- test_digital_twin_ntp.py::test_a_product_socket_failing_its_setup_or_connect_is_torn_down_and_the_next_fetch_builds_one_that_syncs
  - Two boots: one failing at socket(), one at connect(). Each checks: the fault fired once, one E NTP_NOT_SENT and
    nothing sent, every socket closed, and the next attempt syncs with no new entry.
  - Bite: a failed setup raising instead of self-healing: red, "socket: the boot's attempt never failed within 20.0
    driven s" (biteU2).
- test_digital_twin_sensortask_integration.py::test_the_captive_dns_socket_whose_bind_fails_logs_once_then_rebuilds_binds_and_answers
  - On the first device wiring a neopixel. The listener's first bind is refused: one E INIT, that socket closed, and
    after its backoff the same UDPSocket rebuilds, binds and answers a 6-query burst.
  - Bite: the failed setup's teardown skipped: red, "the real DNSServer never bound its port 53 socket" (biteU1).
  - The NTP test passes that plant, because NTP builds a fresh UDPSocket per fetch and closes it itself. The lazy
    rebuild of one instance is the listener test's to pin.
- The lead's OverflowError question. Finding: UDPSocket.ready() catches no OverflowError, and no product timeout can
  reach one. Not a defect, and no src change.
  - Every timeout_ms reaching ready() is one of three:
    - -1: the captive DNS's recvfrom()/sendto(), which take the no-deadline branch with no wait_for;
    - 500 ms: _DNS_TIMEOUT_MS, through NtpTiming into resolve_ipv4() and its write()/recvfrom();
    - 5000 ms: _NTP_FETCH_TIMEOUT_MS, NTP's write()/recvfrom().
  - The two constants are buildgen module constants (buildgen/codegen.py:27-32). No device TOML or REST field sets
    them. The generated modules carry 500/5000 on all six devices.
  - rp2's ticks_add() raises only from 2^29 ms, about 6.2 days (extmod/modtime.c:191; TICKS_PERIOD is 2^30 on rp2's
    31-bit small ints).
  - The proof is recorded in the UDP rows' gap cell.
  - audit/u35-d2s edits the same module's excepts. This lane changed nothing in it, so there is nothing to merge there.

## Item 5: review.md
- review.md is re-rendered. Each of CO4's 13 tests and this lane's eight rows (six tests, one flash test, one device
  script) has its row, every one "biting".
- Two verdicts were added to review_verdicts.json:
  - the NTP test's setup_credit_only flag (a per-step case helper, like the file's two existing ones);
  - the device script's ds_facts.
- review_rows.py --check: "8571 rows: CRr2 83, fixed 46, justified 129, biting 8313", rc 0.

## Defects
None. Every rung examined held its property, and the OverflowError path is unreachable.

## Question for the owner (the lead decides whether it goes)
**One faulting FRAM block read logs two entries: the fault (E UNEXPECTED) and the fall-through (W FRAM_BLOCK_INVALID).**
- When both blocks fault, a chunk read logs four. Under a sustained 32+-byte read fault with the chip present,
  measured on all six devices over a driven hour:
  - the product makes exactly one such read per boot, the SGP40 VOC restore;
  - so the FRAM manager's RAM-only ring takes four slots once per boot, and nothing more per hour;
  - nothing ends the fault itself.
- The options: (a) keep the two facts per block; (b) fold a repeated pair into the count; (c) log the fall-through
  once per fault run.
- Recommendation: (a), keep it. The cost measured is 4 of 10 RAM-only slots once per boot, with no wear and no growth.
  - (b) changes the newest-entry rule for every logger.
  - (c) drops the warning that says no copy was left.
- The same two-entry shape exists, already pinned at L1, for a verify readback that fails its CRC.

## Checks (final head 1fd9db0f)
Formal pairs, every run through run.sh (namespace, nice 19, RUNS.md lines "U35 lane CO5"). Zero memory markers in
every one, the measurement logs included.

| file | -1 | 32768 |
|---|---|---|
| test_digital_twin_fram.py | 3.0 s | 3.6 s (CO4: 2.8 / 3.4, within 10 %) |
| test_digital_twin_fram_crash_points.py | 13.1 s | 18.5 s |
| test_digital_twin_machine.py | 1.3 s | 1.5 s |
| test_digital_twin_generic_wiring.py | 0.1 s | 0.1 s |
| test_digital_twin_ntp.py | 36.4 s | 42.0 s |
| test_digital_twin_sensortask_integration.py, six devices | 22.1-47.6 s | 22.8-48.6 s |
| test_digital_twin_sgp40.py | 0.4 s | 0.4 s |
| flash/test_bus_concurrency.py's new test, --twin | pass | pass |

- No base table survives for per-file times; S/u24/base_times.tsv is gone, as CO4 noted.
- lint_direct: rc 0.
- The six mypy passes, cold caches: rc 0 each (main 274 files, twin 57, host 311, bench conftest, network, conftest).
- Audit checks:
  - raising_walk --check: current;
  - e51_sweep --check: every site has its verdict;
  - review_rows.py --check: rc 0;
  - conformance walk re-run per item: no rung cell left open.
- Whole tests_scripts tier on the final head (tierF.log): 7002 passed, 6 skipped. The three reds:
  - member_order: src/asy_fram_manager.py _FRAMBaseChunk, D2S's;
  - test_twin_record's two, the known pre-re-record state. The new device script is one more name in its
    missing list.

## Deviations
- The first six-device measurement run was stopped by the harness's 30-minute background limit after three devices
  (RUNS.md notes it). The other three ran again with a longer bound. No result was lost.
- The bites ran in a scratch copy of the tree, deleted after. They ran before three comment-only edits and two renames
  in the new tests (the helper class FailNextUdpSetup, the case helper _a_socket_failing_at). The asserting lines
  that went red are unchanged.

## Runs
All exited.
- Probes and iterations: setres1-2, quick1, psock, fram1-2, ntp1, dns1, sgp40a.
- Measurement: m1_dev_on (stopped by me at its first mark: too slow without streamed output), m2_wozi_on, mpair
  (stopped by the harness), mpair2, designs1-2.
- Red-first and bites: red2, biteSR1-3, biteW1-2, biteV1-2, biteH1-2, biteU1-2, regen1.
- Checks: static0-2, staticF, staticF2, tier0, tierF, formal2, formal4, walk2-4, render5, audit5.
- Deleted after use: the plant copy, the private toolchain copy S/u35/laneB/co5/tc, mypy caches, datasheet text
  extractions and the measurement's tests/_tmp dirs.

nothing of mine is running
