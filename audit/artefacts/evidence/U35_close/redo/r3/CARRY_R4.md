# Carried to R4 from R3 (lead, 2026-11-04)

- `SPECIFICATION.md:5831` (E.6.6 `ntp-unreachable-under-load`): "the outage under load is a gap until written" is
  stale for the first recombination; the bench test has reset under the NTP block with load since `0c0ad52c` (D2).
- `src/asy_uart_driver.py:76-78`: RP2040 Table 427 ties BE/PE/FE to the character at the top of the FIFO and marks
  all four bits write-to-clear; "the byte the DMA read last" is the bench's reading, to be worded as such (D2).
- P8's two facts with no datasheet: the SGP40 restore is the algorithm's; the CYW43439 documents no country readback
  (D2, `d2/p8_datasheets.md`).
