P8: the hardware facts R1 relied on, against the datasheets (lane D2, agent, 2026-11-04)

Datasheets: `/home/user/datasheets/` (the private repository, read-only; the lead's correction of 16:30 UTC withdraws
ROWS.md's "no RP2040, W25Q16JV or CYW43439 datasheet" limit). Page = PDF page; for the RP2040 datasheet the PDF
page less one is its printed page, given here. Text dumps only in `d2/ftmp/` (deleted at the hand-back).

## The facts
| R1 fact (where it is used) | datasheet: document, section, table, page | verdict |
|---|---|---|
| FRAM at 8 MHz (B3, `asy_fram_driver.py:124`) | MB85RS2MTA DS501-00032-3v0-E: fCK max 40 MHz at VDD 2.7-3.6 V, 33 MHz at 1.8-2.7 V (AC Characteristics, p. 15; features, p. 1); MB85RS64V DS501-00015-4v0-E: fCK max 20 MHz (AC Characteristics, p. 14) | holds, both parts |
| SPI mode 0 (the driver's `init 8000000/0/0/8/1`) | both parts: SPI mode 0 and mode 3 (features, p. 1) | holds |
| "24 MHz (rp2's ceiling) / 3, exact" (B3's comment) | RP2040 datasheet 4.4.3.4 "Clock ratios" (p. 505): master SSPCLKOUT at most SSPCLK/2; clk_peri is 48 MHz in the pinned source (`ports/rp2/main.c:104-105`, v1.29.0, not a datasheet fact) | holds: 48/2 = 24, 48/6 = 8 exactly; the bench's 20 -> 12 and 40 -> 24 (READING:72) agree |
| a lost FRAM is not detected: SO floats with the chip absent (B3 row 1, owner 2026-10-28) | both parts: SO is High-Z while CS is high (pin descriptions, p. 2); no internal pull is stated | holds for the chip; the absent-chip level is board-level, so it rests on the owner's word, not a datasheet |
| the MB85RS2MTA keeps WEL set after WRITE/WRSR ("continual programming", `asy_fram_driver.py:229-231` comment) | MB85RS2MTA status register table (p. 6); MB85RS64V resets WEL at CS rise after WRITE/WRSR (p. 6) | holds; the two parts differ, as the comment says |
| the I2C clock-out: nine SCL pulses, then STOP (B4 item 2, `asy_i2c_driver.py:25`, `:35`) | RP2040 datasheet 4.3.13.1 "SDA Line Stuck at LOW Recovery" (p. 458): up to nine clocks, then STOP | holds; RP2040's register list exposes no SDA-stuck-recovery enable, so the driver bit-bangs the same sequence |
| BMP3XX STATUS: cmd_rdy bit 4, drdy_press bit 5, drdy_temp bit 6; a data read clears drdy (B4 item 6, `_STATUS_CMD_RDY` 0x10, `_STATUS_DATA_READY` 0x60) | BMP388 DS001: Table 27 "Register 0x03 STATUS" (p. 32) | holds |
| the BMP3XX conversion bound 300 ms (`_MEAS_TIMEOUT_MS`) | BMP388 DS001: Table 22 "measurement time" (p. 26): 78.09 ms max at x32/x2 | holds |
| softreset 0xB6 restores the defaults, no settle time given (`_RESET_SETTLE_MS` 2, Bosch's reference) | BMP388 DS001: Table 46 (p. 39) | holds (no time stated) |
| after a POR the BMP3XX runs "at its defaults (x1, no IIR)" (B4 item 5's basis; `SPECIFICATION.md:364`, `tests/test_digital_twin_hot_replug.py:235`) | BMP388 DS001: Table 24 memory map (p. 30): OSR reset 0x02 (osr_p x4, osr_t x1), CONFIG 0x00 (IIR off); Table 41 (p. 37) | **partly**: pressure resets to x4, not x1; IIR off holds. The twin is right (`digital_twin/_bmp3xx_chip.py:41`, `_OSR_RESET = 0x02`). B4's conclusion stands (readings stay valid); the two texts are R4's doc fix |
| ISL29125 CONFIG changes without a write only by reset or brownout, which BOUTF reports (B4 item 9) | FN8424 Rev 3.00: Power-On Reset (p. 6), device reset 0x46 to register 0x00 (p. 9), BOUTF Table 18 (p. 12) | holds |
| the SGP40 restore (B4 item 12: a task restart restores the VOC backup) | no chip fact: the VOC algorithm's state is Sensirion's algorithm, ported in `voc_algorithm.py`; Info Note VOC Index (p. 1) gives only the 24 h learning time | marked: no datasheet here |
| RP2040-E13: an abort with transfers in flight completes as a normal completion (B6 row 1, `_rx_stop()`) | RP2040 datasheet erratum RP2040-E13 (p. 629); 2.5.5.3 "Channel Abort" caution (p. 97) | holds for the premature completion and its IRQ; that the completion fires the chain is inferred (chain triggers follow a completion, 2.5.2.2 "Chaining", p. 94) and was probe-confirmed on silicon (READING:44-52) |
| CHAIN_TO = the channel itself disables chaining (`_rx_stop()`) | RP2040 datasheet 2.5.2.2 "Chaining" (p. 94); CH0_CTRL_TRIG bits 14:11 (p. 112) | holds |
| RP2040-E12: WRITE_ADDR/READ_ADDR read wrong during a wrapping transfer (`asy_uart_driver.py:328-329`, `_rx_level()` from TRANS_COUNT) | RP2040 erratum RP2040-E12 (p. 629) | holds |
| UARTRSR's FE and BE "belong to the byte the DMA read last (Table 427)"; OE stays until UARTECR (B6 row 2, `asy_uart_driver.py:76-78`) | RP2040 datasheet Table 427 UARTRSR (p. 430): BE/PE/FE "associated with the character at the top of the FIFO", all four bits WC, cleared by any UARTECR write; Table 426 UARTDR (p. 429) carries the same bits per character | **partly**: the table number is right; "the byte the DMA read last" and the FE/BE-versus-OE split are the bench's reading (8 of 134 frames, READING:53-55), not the table's wording, which marks all four bits write-to-clear |
| the flash window: W25Q16JV sector erase typ 45 ms, max 400 ms (`flash/test_uart_crossover.py:34`, F.3 stall rows) | Winbond W25Q16JV Rev F 9.6 AC Electrical Characteristics, tSE (printed p. 62); tPP typ 0.4, max 3 ms (same table) | holds |
| flash endurance (the wear rule) | W25Q16JV Rev F section 1 Features (p. 5): at least 100K program-erase cycles per sector | holds |
| the country code: the chip reports nothing back (B5 keep; `network.country()` keeps any two characters, RESEARCH 8) | CYW43439 datasheet v03_00: 802.11d listed (p. 7), "worldwide regulatory support" (p. 2); no host command reference | marked: the readback rests on the pinned MicroPython source and the bench; the datasheet documents no country interface |
| the SCD30's general call: only the SGP40's datasheet names it (RESEARCH:94) | SGP40 Table 17 (p. 14); the SCD30 Interface Description and ISL29125 FN8424 name none | holds |

## The datasheet citations in the tree (the lead's addition)
- Every `datasheets/<path>` cited at `17688315` (`git grep` with `':!arduino'` and `':!audit'`; 46 matches;
  the 3 placeholders `<chip>/<file>`, `<name>/` x2 set aside and the brace list `{scd30,sgp40,bmp3xx,isl29125}` expanded to 4,
  46 paths) was checked against `git -C /home/user/datasheets ls-tree -r --name-only 786c947c...`
  (24 files). Missing: 0.
- Bare PDF names cited without the `datasheets/` prefix (39 occurrences, 17 names) were checked too: all resolve
  except an external NOAA URL's file (`src/asy_bmp3xx_driver.py:599`) and the elided `..._Interface_Description.pdf`
  (`src/asy_scd30_driver.py:171`, `tests/_sensortask_scenarios.py:236`), which reads as the SCD30 Interface
  Description; `src/asy_scd30_driver.py:171` spells the folder `Datasheets/` (capital D) - a one-character text fix for
  R4, not a gap. The legacy tree's two misses (`pressureAltitude.pdf`, `HT_DS_SHTC3_D1.pdf`) are reference-only.

## Result
19 facts: 15 hold, 2 hold only in part (BMP3XX POR defaults; UARTRSR's wording), 2 rest on no datasheet here (the
SGP40 restore; the CYW43439 country readback). None changes a behaviour; the two partial ones are doc-text findings.
