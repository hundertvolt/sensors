R3 lane D2 hand-back, written by the agent (Wed Nov  4 17:10:02 UTC 2026)

Read-only on `S/wt-u35int` at `17688315` (its status unchanged: only the untracked build outputs it had). Records in
`S/u35r/r3/d2/`; `d2/ftmp/` (PDF text dumps, two walk scripts, their JSON) is deleted. Runs, all through
`S/u35/lead/run.sh`, static, seconds each: `r3d2_pdftext`, `r3d2_pdftext2`, `r3d2_pdftext3` (pdftotext into `ftmp`),
`r3d2_rungs`, `r3d2_rungs_show`, `r3d2_rungs_scripts`, `r3d2_names`, `r3d2_names2`. No test runner, build, port or
hardware. Datasheets from `/home/user/datasheets/` after the lead's 16:30 correction (the eight PDFs I had dumped from
the stale folder are byte-identical there; the RP2040, W25Q16JV, CYW43439, BMP390, Pico W and two SGP40 notes were
added).

## Per row
1. OR41 with U35-09: **met**, `d2/or41_matrix.md`. 55 actor x resource lines over SPEC's lock table plus heap, loop,
   alarm pool, TCP slots and the UART ring; each names its test per level or a reason. U35-09's row: both
   recombinations at L2 (`:1404`, `:1410`), L1 and L3 by reason, L4 for the first (the bench NTP-block test), none for
   the write variant (E.6.6's recorded reason). A real interaction with no test anywhere: none.
2. OR49: **met**, `d2/or49_load.md`. 13 cells (UDP split from TCP), each a test or a reason; A1 cited as "A1 (lane M)"
   for the soft-IRQ queue and, conditionally, the DNS flood.
3. U35-52: **met, one gap (G1)**, `d2/u35_52_rungs.md`. 120 rows: 16 dropped with the rung R1 removed (8 setup-failure
   bus rungs, 3 Timer-arm rungs, 4 lost-FRAM rungs, 1 ISL INT re-arm); 104 stay, 84 with every named test present and
   20 re-pointed to today's tests (19 found, 1 missing at L2).
4. Bus-hazard rule: **met**, `d2/bus_hazard.md`. 7 bus-facing changes (B3 8 MHz; B4 clock-out, no-bus contract,
   BMP3XX STATUS poll, ISL shadow compare, SGP40 restore; B6 `_rx_stop()`) x 3 kinds x 4 tiers = 84 cells, each a
   named test or a reason. Missing: none.
5. Wear table: **met**, `d2/wear.md`. 32 marked tests, every one in README's budget table with the same store and
   count, and every table row a marked test; 25 prerequisite scratch builds plus the pinned helpers. Wrong markers: none.
6. P1: **met as a sheet, with three blockers**, `d2/round1_sheet.md`: 16 items in order with expected outcome and wear,
   the exclusions, and 7 stale BACKLOG entries listed (not edited). Blockers: G2, G3, G4; and the scratch
   `long_fram.py` needs its baud (`:12`, 1 MHz) and duration (`:9`, 1,200 s) edited for the overnight 8 MHz run.
7. P4: **met at the desk**, `d2/p4_frozen_image.md`: production mode imports the frozen `sensortask_dev` and
   `frozen_html` with no mount; preconditions: the final image flashed, no shadowing `.py` on the board's filesystem
   (`sys.path` is `['', '.frozen', '/lib']` after mpremote's soft reset). Beside it, gap G2.
8. P7: **met**, `d2/p7_chip_facts.md`: SGP40 (serial words with CRCs, self-test, waits, general call) and SCD30
   (data-ready gap, not-ready polls, stored settings, waits, bus clock and stretch) against the final drivers and dev's
   TOML: every fact holds; the SCD30's missed-edge fallback has its L2 gap (G1).
9. P8: **met**, `d2/p8_datasheets.md`: 19 facts, 15 hold, 2 in part (BMP3XX POR defaults; UARTRSR's wording), 2 on no
   datasheet here (the SGP40 restore is the algorithm's; the CYW43439 documents no country readback). The lead's
   citation check: 46 `datasheets/<path>` citations at `17688315` (46 matches, 3 placeholders set aside, the brace
   list expanded to 4) against the submodule's pinned `786c947c`: 0 missing; 39 bare PDF-name citations checked too.

## Gaps (to the lead; nothing added to any tree)
- **G1** (U35-52, A8, OR113.a (2)): the SCD30's 500 ms fallback trigger after a missed RDY edge has no L2 test since
  `b4341646` removed W73's twin test; evidence: the rung row "U15: SCD30 data-ready interrupt edge missed R2", a
  `git grep` of the twin tier finding no stuck-RDY or fallback case. Proposed: the fallback half of the removed twin
  test without W73 (edge muted, pin held high, one read within `_trigger_half_ticks` ticks, no entry).
- **G2** (P4 / round 1): `flash/test_memory_stress.py::test_loop_lag_under_combined_load_stays_under_the_uart_reply_budget`
  skips on silicon with no gate marker and is not in `PERMANENT_SKIPS`; `_hardware_verdict.py:_judge_skip()` reads it
  "unexpected skip", so the flash runner's verdict fails whatever else passes. Proposed: its node ID in
  `PERMANENT_SKIPS` with its reason, or a twin-only marker the verdict treats as expected (one line).
- **G3** (P1, PLAN round 1's crc16 rerun): `uart_comm_hazards.py` reports neither end's `rx_overruns` or
  `discarded_bytes` nor a log at a failing exchange, so "both ends' logs and the ring counters at every failing
  exchange" has no instrument. Proposed: add both drivers' counters and each link logger's newest entries to the
  facts of every failing exchange (test-side only).
- **G4** (P1): owed rows with no instrument in the tree: the first unfed watchdog stretch and dev's ring peak
  (REPORT 7 item 11), the idle poll rate, the `ResetErrors` budget timing, the general call per chip, the two resets
  with SDA held, and REPORT 7 item 8's channel-13 country scan. Proposed: a throwaway script per row in the bench's
  `mp/` practice before the round, or the row marked "not run" on the sheet (lead).

## Findings (not gaps; doc text for R4 or the owner's sizing)
- E.6.6 `ntp-unreachable-under-load` (`SPECIFICATION.md:5831`): "the outage under load is a gap until written" is
  stale for the first recombination; the bench test has reset under the NTP block with load since `0c0ad52c`.
- "x1, no IIR" after a BMP3XX POR (`SPECIFICATION.md:364`, `tests/test_digital_twin_hot_replug.py:235`): the
  datasheet resets pressure oversampling to x4 (BMP388 DS001 Table 24, p. 30); the twin models 0x02 correctly.
- `src/asy_uart_driver.py:76-78`: Table 427 is the right table, but its wording ties BE/PE/FE to "the character at the
  top of the FIFO" and marks all four bits write-to-clear; "the byte the DMA read last" is the bench's reading.
- `src/asy_scd30_driver.py:171` cites `Datasheets/scd30/...` with a capital D.
- The flash tier's `test_no_frame_is_lost_while_interrupts_are_off` fails up front at dev's 512 B responder ring
  (4,608 B needed for the 400 ms window): the BACKLOG entry's open sizing, an expected red in round 1.

## Round 1
Sheet: `S/u35r/r3/d2/round1_sheet.md`. Wear sum: 6 flash cycles (8 with G6's own round); flash filesystem up to 126
owned writes plus up to about 210 prerequisite scratch writes; SCD30 NVM up to 14 (13 owned with both flags, 1 start
command); manual steps extra (flash up to 65 plus `resetconfig`'s, NVM up to 24), each stated before its confirm.

## Method of the two deleted walks
- Rungs: every `file.py::name` in conformance.md's rung rows (L1, L2, bounded/once/race-free) looked up at `HEAD` as a
  `def` of the name or a `@_register`/`@scenario` of it, in files of that basename outside `audit/`, `arduino/`,
  `legacy/`.
- Names: every backticked test, scenario or file name in the nine records, the same lookup; 369 checked, 351 present,
  18 absent by design (the 11 old names U35-52 reports, a placeholder, the scratch script, `long_fram.py` twice, which
  lives outside the tree, and four untracked generated build files present on disk).

## Notes on my own conduct
- One `python3 -c` that read `build/generated_src/sensortask_dev_expected.json` ran outside `run.sh` early on (a
  read-only JSON print, seconds); every later run went through the wrapper.
- A `sed` of `devices/dev.toml`'s first lines put the device's hotspot password value into my terminal output once;
  it is in no record, and later reads of the TOML filtered such keys.
- The harness saved one long tool output under `/root/.claude/`; I did not open it and re-ran the command with
  `':!audit'` instead.
- Decisions taken: the bus-hazard kinds for the UART change follow SPEC J's UART shape (same-instance concurrency,
  both ends transmitting, field sweep) (agent, 2026-11-04); the R6 rows' L2 cell is the twin CI's Run 3/Run 4
  (agent, 2026-11-04).

## Follow-up (lead's ACTION_LIST item 12, G4; written Wed Nov  4 17:22:05 UTC 2026)

Written outside the repository in `S/u35r/hw_handover/mp/` in the existing scripts' shape: a docstring of three
lines or fewer, `SUM` lines, `DONE=1`, and a sed-set constant (HANDOVER's `MODE` pattern) as the explicit confirm.
No worktree changed. The only run was `r3d2_fu_syntax`, a host compile of the nine files: 9 compiled, no
`__pycache__` written. No credential, Wi-Fi password or hotspot value is in any of them; `dns_idle_poll.py` reads the
stored Wi-Fi config at run time without printing it, as `net_timing.py` does. Every board script feeds the boot's
watchdog, which the final image keeps armed through `mpremote`'s soft reset. None spends flash or NVM wear. The scripts
that boot or reset the product, and the host `ResetErrors` script, refuse until confirmed: they write production FRAM
chunks or wipe them.

| file | lines | row answered |
|---|---|---|
| `boot_stretch_final.py` | 54 | 12a: the first unfed watchdog stretch, each setup unit's stretch, the gap to the supervisor (CONFIRM) |
| `ring_peak_final.py` | 51 | 12b: dev's receive-ring peak per link, read-only from the DMA count (CONFIRM) |
| `dns_idle_poll.py` + `host_dns_query_timing.py` | 73 + 46 | 12c: the idle listener's loop share, and the first-query latency after a silence and in a burst (the bench half) |
| `host_reset_errors_timing.py` | 62 | 12d: the `ResetErrors` sweep timed against 0-4 readers, 3 each (asks for "wipe") |
| `general_call_per_chip.py` | 57 | 12e: the general call per chip on dev's bus 1 (volatile CONFIG1 marker, put back) |
| `held_sda_reset.py` | 71 | 12f: the two resets with SDA held, `MODE` `machine_reset` or `watchdog` (CONFIRM) |
| `country_scan.py` | 30 | 13: REPORT 7 item 8, channels heard under "DE" and "XX" (setup: an AP on channel 13, the owner's) |
| `long_fram.py` (edited) | 85 | 11: `baudrate=8_000_000`, `DUR_S = 36000`, the docstring's "1 MHz" made "8 MHz"; nothing else changed |

- Already answered by an existing instrument, so nothing was written: the bus-0 half of the general call
  (`flash/test_bus_concurrency.py::test_bmp3xx_alone_survives_a_general_call`, item 4) and the per-bus ACK/NAK (the
  bench's `i2c_timing.py`, READING:78).
- Left unscripted, as small as the row needs: the damaged-config boot of "The two unfed boot stretches" (one repair
  write, gated) and the SCL/SDA line levels (a scope, the owner's hands). Both are stated on the sheet.
- **Blocker for the lead (11):** `long_fram.py` never feeds a watchdog. It ran on the bare image, where nothing arms
  one. On the final image the boot's `WDT(timeout=8000)` survives `mpremote`'s soft reset
  (`tests_hardware/README.md:248`), so the overnight run would end in a watchdog reset within 8.4 s. It needs one
  `machine.WDT(timeout=8000)` and a feed beside its existing `time.sleep_ms(1)` every 64 passes. I kept to "nothing
  else changed" and did not add it.
- The sheet `S/u35r/r3/d2/round1_sheet.md` now names a script or an existing instrument, the expected outcome and the
  wear for each row. Items 9 and 4 note that G3 and G2 are admitted to lane M. The wear sum is unchanged, since the
  scripts add none.

nothing of mine is running
