# R3 lane M: the bench's probes on the twin (P6) (agent, 2026-11-04)

Run `r3m_probes` (rc 0, 35 s): a throwaway script ran the eight probes of the bench campaign's day 1 (the five chip
conformance probes, `timer_alarm_pool_exhaustion`, `scheduler_saturation_drop`, `wifi_country_code_reaction`) through
`TwinBoard` at gc.threshold -1 and 32768 on `17688315`, (results `m/data/twin_probes.json`) and diffed each against the silicon output in the campaign's
`HANDBACK.md` (`S/bench_read/.../hw_handover/HANDBACK.md:786-975`, 2026-10-28, bare v1.29.0 image on `dev`). The five
conformance probes go through `tests_hardware/flash/test_chip_conformance.py`'s own tables and `conformance.compare()`
(a physical key compared only in its independent form); the three FACT probes key by key. Both stages agree everywhere.
The probe scripts are today's; the silicon ran the campaign's copies of the same scripts.

## Agreeing

- ISL29125: every key (0 divergences).
- The alarm pool: 16 constructed, `OSError(ENOMEM)` (errno 12) on the 17th, as on silicon.
- BMP3XX `A01_chip_id` 0x50 on silicon against the twin's 0x60: inside its independent form (both ids accepted), and
  already the row "the BMP3XX chip id" (`digital_twin/README.md:237`).

## Disagreements, each with its proposed fidelity-table row (A10)

Rows in the table's own columns (class | fact on silicon | twin | evidence | proven at | status). Items 1-5 propose a
new row (1-4 open, 5 accepted); 6 and 7 are covered by an existing row, named.

1. BMP3XX `B07_status_after_data_read`: silicon 0x10, twin 0x70.
   `| Chips | reading a DATA register clears STATUS's drdy_press/drdy_temp (DS001 4.3.3, Table 27: "It gets reset, when one pressure DATA register is read out") | drdy bits stay set after the data read (0x70) | bench probe B07 0x10 (2026-10-28) against the twin's 0x70 | L3 | open: a twin correction (the driver's STATUS poll then always reads ready in the twin) |`
2. BMP3XX `B03_pwr_ctrl_during_forced` and `B05_pwr_ctrl_after_conversion`: silicon 0x13 then 0x03, twin 0x00 both.
   `| Chips | PWR_CTRL keeps press_en and temp_en through a forced conversion and returns to sleep mode alone (0x13 during, 0x03 after) | reads 0x00 during and after | bench probe B03/B05 | L3 | open: the enable bits are a twin correction; "during" is the accepted no-conversion-time row (:239) |`
3. BMP3XX `C02_osr_config_after_softreset`: silicon OSR/CONFIG 0x00 0x00 after 0xB6, twin 0x02 0x00.
   `| Chips | after a 0xB6 soft reset the bench's part (chip id 0x50) reads OSR 0x00, not the register map's 0x02 (DS001 and DS003 4.3, "0x1C OSR 0x02") | 0x02, the register map's value | bench probe C02 against both datasheets | L3 | open: silicon and datasheet disagree; to settle on the bench before either side changes |`
   The existing row "0xB6 resets OSR and CONFIG ... the reset as on silicon" (`:239`) is then stale for OSR.
4. SGP40 `A02_serial_stable`: silicon yes, twin no.
   `| Chips | the SGP40's serial number is hard-coded at production: the same three words on every read (datasheet 3.4) | fresh random words on every read (digital_twin/_sgp40_chip.py:91-94) | bench probe A02 yes against the twin's no | L3 | open: a twin correction (one serial per chip instance) |`
5. SCD30 `C03_read_before_a_command`: silicon 0xDD 0xDD 0xDD, twin 0x00 0x00 0x00. Proposed row:
   `| Chips | a read with no command pending returns 0xDD bytes | zero bytes | bench probe C03 | L3 | accepted: no driver path reads without a command (agent, 2026-11-04) |`
6. FRAM `B01_status` 0x02 against 0x00 and `C02_wel_after_write` 1 against 0: both the existing row "the MB85RS2MTA
   (`dev`) keeps WEL set after a WRITE or WRSR ... the MB85RS64V clears it | WEL cleared at every ..." (B01 reads the
   WEL an earlier write left set). No new row.
7. `scheduler_saturation_drop` (twin: nothing fires, 12 dropped, not self-healed; silicon: 11 dropped, every timer
   ~500 heal fires) and `wifi_country_code_reaction` (twin: `AttributeError: 'WLAN' object has no attribute 'scan'`):
   the existing Runtime row on soft callbacks (a synchronous script gives the twin's Timers no turn) and the twin
   record's reason (no `scan()`). No new row.

Totals: 8 probes at 2 stages each: 2 agree fully (ISL29125, the alarm pool); 5 proposed rows (1-4 open, a twin
correction or a bench settlement each; 5 accepted); 2 disagreements covered by existing rows (6, 7).
