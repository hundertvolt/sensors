G4 second pass, round 2, written by the part (Wed Oct 28 10:12:13 UTC 2026)

# G4b: the crosswalk of G1-G4, the closure extended by G1-G3's roots, and the regression flags

Same brief, same rules: read only; no run beyond the closure tool (`python3 -I`). S = the scratchpad. Inputs:
`S/u35r/scan2/G1.md` (S2-G1-1..23), `G2.md` (S2-G2-1..14), `G3.md` (S2-G3-1..17), my `G4.md` (S2-G4-1..22) and
`G4_closure.tsv`. Output: this file and `S/u35r/scan2/G4b_closure.tsv` (254 rows over 30 roots, same five columns;
inputs `S/u35r/scan2/G4work/roots_round2.tsv`, tool `G4work/closure.py`).

## 0. Corrections to G4.md made in this round (all in place in G4.md, each marked there)

- **S2-G4-10 (sample-age checks).** My first draft named SCD30 `ContMeas` Off as a live path the checks cover, and
  classed the row K. Wrong: a not-ready SCD30 cycle re-stores its cached values with a fresh TS
  (`asy_scd30_driver.py:479, 531-535`, the owner's named exception in review "stale-as-fresh-every-driver"), so the TS
  never ages and the checks never see it. G1's S2-G1-18 had it right. Back to H; the needs-verification item is
  withdrawn.
- **S2-G4-9 (LED deadline).** I had read the review item's title, "why" and the owner's note, but not its decision
  text: "An internal notification request instead waits for the running signal up to a deadline and then queues, as
  legacy queued it, but bounded." (`decisions.json`, `led-request-internal-queue`, status "ask" with the owner's
  "Fine, and this for a reason ..."). The text now quotes it; the class conflict with G1 is listed in section 2.
- **S2-G4-20 (`class_has_read_triggers()`).** It serves G5 (R), whose D.md row names it (`driver_registry.py:88`);
  only `trigger_spread()` goes with G5b. G3's S2-G3-11 had it right; D.md's cascade 6 had put it under G5b.

# 1. Crosswalk: one line per mechanism

Columns: the mechanism; the rows of each part (G1, G2, G3, G4); the first-scan rows; each part's class. "≠" marks a
line where two parts class the same mechanism differently (listed again in section 2, not arbitrated).

| # | mechanism | G1 | G2 | G3 | G4 (row / root) | first scan | classes |
|---|---|---|---|---|---|---|---|
| 1 | I2C no-controller branch, unreachable on rp2 | S2-G1-1 | | | S2-G4-3 / G4R02 | I2C-3, REPORT 4.2 | G1 H; G4 H |
| 2 | I2C bool contract, 26 "bus not initialized" raises | S2-G1-2 | | | S2-G4-3 / G4R02 | I2C-8, BMP-11, SCD-11, SGP-19, ISL-14 | ≠ G1 C (order 2/3, root H); G4 H |
| 3 | SPI copy of the contract, FRAM E52 | S2-G1-3 | | S2-G3-7 (E52 row) | S2-G4-3, S2-G4-4 / G4R02 | SPI-1, SPI-2, A-D5 | ≠ G1 H (SPI-1), C (rest); G4 H (SPI-1, SPI-2); G3 follows |
| 4 | `is_ready()` | S2-G1-3 | | | S2-G4-5 / G4R03 | A-D10 | G1 C (bus family); G4 C (lost-chip family): same class, different chain |
| 5 | `_init_failed()`: setup failure rebuilds the controller | S2-G1-4 | | | platform table "keep" (not analysed) | inside A-B13 | ≠ G1 H, OV; G4 keep (now superseded by G1's analysis) |
| 6 | `report_if_fatal()` at every broad handler | S2-G1-5 | S2-G2-13 | | S2-G4-1 / G4R01 | A-S15, A-P13, A-B22, A-S30, A-M18, A-D11, A-A4, NT-8, BMP-15, SCD-13, SGP-23, ISL-19, CD-8, NTP-22, WF-20, WS-23, UC-21 | G1 R form; G2 R form; G4 R form. Counts: G1 82/85 + G2 35/38 log the exception (117/123); G4 118/123 (the difference is `asy_webserver_service.py:807`, which logs a non-MemoryError through `pr.err()`) |
| 7 | the fatal flag set where nothing reads it | | | S2-G3-5 | S2-G4-2 / G4R01 | D-B6 | G3 C; G4 C |
| 8 | the escalation's 1,200 ms bounded entry write | S2-G1-6 | | | S2-G4-1 "keep" / G4R01 order 3 | A-S14 | ≠ G1 C, DELAY, removal proposed; G4 keep as landed |
| 9 | refused timer arm, six shapes | S2-G1-7 | S2-G2-1 | | S2-G4-7 / G4F01 | A-B6, A-B14, A-S20, A-S26, NTP-20, BMP-14, SCD-9, SGP-20, ISL-16 | G1 H; G2 H; G4 H |
| 10 | `quiet=` on the tick helper | S2-G1-7 (goes) | S2-G2-2 | | S2-G4-8 (goes) / G4R07 | WF-8, OF-29 | ≠ G1 and G4: goes; G2 C, 0 go (stays while Wi-Fi's settled re-arm stays) |
| 11 | per-episode log flags over `_keep()` | S2-G1-8 | | | S2-G4-8 / G4R07 | A-C6, BMP-9, NT-7, A-M9 | G1 H; G4 H. G1 adds SCD30's `_frc_cfg_ok` guard (round-2 root) |
| 12 | console lines for the memory gates | S2-G1-9 | S2-G2-3, S2-G2-4 | | S2-G4-6 / G4R04 | A-P11, A-B18, A-F2, A-M10, UDP-2, UD-9, DNS-6, WS-9 | ≠ G1 C (P4); G2 H (P4) and OV; G4 C (P4) |
| 13 | `setup()`/`deinit()`/`set_level()` widened to bool | S2-G1-10 | | | (I2C/SPI bools inside S2-G4-3) | A-B16, A-P10, I2C-8 | G1 H (P4); round-2 root |
| 14 | `start_tasks()` keeps a handler a PC tier installed | S2-G1-11 | | | (platform table: `report_unretrieved` keep) | A-S25 | G1 H (P4); round-2 root, with A-S25 itself (section 3) |
| 15 | "a reset is under way" in six flags | S2-G1-12 | | | | A-S6, A-S7, A-S9..A-S11, A-S13, A-S21, A-S32 | G1 R form only |
| 16 | writes closed and stores flushed at several layers | S2-G1-13 | | | platform table keep | A-B9, A-C14, A-S6, A-S9, A-C16, A-C18 | G1 R form only; G4 keep |
| 17 | the deferred config flush | S2-G1-14 | | | S2-G4-16 / G4F03 | A-B10, A-C10, A-C11, A-C16 | ≠ G1 C (root A-B10 H); G4 R (A-B10, A-C10 carry the ok'd "failed-push-no-flash-write") |
| 18 | entries logged before `setup()` | S2-G1-15 | | | (auto order 1 of A-P2, A-P5) | A-P2, A-P5 | G1 H; round-2 root |
| 19 | boot-time guards for races the batch excludes | S2-G1-16 | | | | A-D6, A-C18 | G1 H; round-2 root |
| 20 | NeoPixel queue deadline and W67 | S2-G1-17 | | S2-G3-7 (W67) | S2-G4-9 / G4R05 | NP-2, NT-5 | ≠ G1 NP-2 R form, NT-5 C and OV; G4 NP-2's deadline H, NT-5 C |
| 21 | sample-age checks at two consumers | S2-G1-18 | | S2-G3-7 (NotifyState row 3) | S2-G4-10 / G4R05 | NT-3, SGP-2, SCD-6 | G1 H (with SCD-6); G4 H (after correction; SCD-6 not in it) |
| 22 | typing-only guards | S2-G1-19 | | | families table; S2-G4-22 (narrowings) / G4R08, G4F08 | NP-3, NT-4, BMP-13, SGP-18, ISL-17, A-C7, A-K2, A-K3, A-P10 | ≠ G1 H (incl. `asy_scd30_driver.py:279`); G4 X for the 20 "kept to narrow" branches |
| 23 | the lost-FRAM chain | S2-G1-20 | | S2-G3-7 (E54) | S2-G4-5 / G4R03 | A-D1, A-M4, A-M5, A-M6, A-M14, A-D9, A-D10 | G1 C chain, root H; G4 H root, C dependents |
| 24 | W69 and its reset-reason exclusion | S2-G1-21 | | S2-G3-7 (W69) | S2-G4-21 / G4F04 | A-S28, A-C4 | G1 C (roots A-S28 H, A-S8 R); G4 H root, C |
| 25 | the participant rung guarded twice | S2-G1-22 | | | | inside A-B13, BMP-4, SCD-7, SGP-7 | G1 H, OV; round-2 root |
| 26 | ISL29125's dead-INT re-arm | S2-G1-23 | | | | ISL-2 | G1 H (first scan R O-gen); round-2 root |
| 27 | resolver widened to `(address, cause)` and `pr=` | | S2-G2-5 | S2-G3-7 (W16) | (auto order 1 of DNS-3) | DNS-3, NTP-5, DNS-4, DNS-7, DNS-8 | G2 K, plumbing order 2; round-2 root |
| 28 | NTP-3 and DNS-1 covering each other | | S2-G2-6 | | platform table (`DNS_NAME_MAX`) | NTP-3, DNS-1 | G2 H, OV; round-2 root |
| 29 | the refusal path holds its socket for a trace | | S2-G2-7 | | overlay map "stalled HTTP connection": no change | WS-3, WS-6 | ≠ G2 C (order 2 of WS-3's placement), close-then-trace proposed; G4 none proposed |
| 30 | WS-2's refusals and WS-9's print rebind | | S2-G2-8 | | S2-G4-6 (WS-9's console branch) | WS-2, WS-9 | G2 H, OV; G4 counts only WS-9's MemoryError branch; round-2 root |
| 31 | `timed_out`, the W49/W50 split | | S2-G2-9 | | | WS-5 | G2 K; round-2 root |
| 32 | an allocation failure split from bad input | | S2-G2-10 | | | NTP-10, CD-7, WS-10, UC-4 | G2 K (UC-4 R); round-2 root |
| 33 | DMA-ring guards for states nothing creates | | S2-G2-11 | | | UD-8, inside UD-1 | G2 X; round-2 root |
| 34 | the status-command dispatch in every image | | S2-G2-12 | | | WS-26 | G2 R, hidden cost; not a root |
| 35 | Wi-Fi re-checks a build-validated default | | S2-G2-14 | | platform table (`host_label_ok`) | WF-1 | G2 R settled, OV buildgen; not a root |
| 36 | boot-clear budget beside the timeout ceiling | | | S2-G3-1 | S2-G4-20 (H17 side) | H18, H17 | G3 C + OV (budget), H (ceiling); round-2 root |
| 37 | the I2C loop-hold check and its helper | | | S2-G3-2 | S2-G4-20 / G4R08d | H17 | G3 H; G4 C (root H17); same mechanism |
| 38 | UART build checks no TOML value can trip | | | S2-G3-3 | (auto order 1 of H14, H15) | H14, H15 | G3 H; round-2 root |
| 39 | dev's UART values checked at build and construction | | | S2-G3-4 | (auto order 1 of UC-8) | UC-8, UC-12, H10, H14, H15 | G3 OV, form only for the ring floor |
| 40 | the loop-end clause | | | S2-G3-6 | S2-G4-14 / G4R06c | B5, B6, B7, A-S5 | ≠ G3 K (B5, B6), C (B7), simulation of the whole pre-audit `try/finally`; G4 H (the BaseException width), K (the label), keeps 21 and 22 |
| 41 | catalog rows for H/X/C mechanisms | | | S2-G3-7 | per-chain catalog rows in `G4_closure.tsv` | (each mechanism's) | G3 follows the mechanism |
| 42 | /status keys for H mechanisms | | | S2-G3-8 | G4F05 (ResetBits) | G14b, G17, G22 | G3 H; G4 H (ResetBits); round-2 root for G17, G22 |
| 43 | the errcount table twice per site | | | S2-G3-9 | S2-G4-19 (test texts in the site) | (D-H8) | G3 X form only; G4 X (host metadata) |
| 44 | the boot oracle in every image build | | | S2-G3-10 | | H6, H5 | G3 X; round-2 root |
| 45 | buildgen exports and TOML keys only tests read | | | S2-G3-11 | S2-G4-20 (corrected) | D4, G5b, H31 | G3 H; G4 C (G5b side); round-2 root |
| 46 | the module-file table restated | | | S2-G3-12 | | (none) | G3 X; round-2 root |
| 47 | the browser's definitions validator | | | S2-G3-13 | | (E.md) | G3 X + OV; round-2 root |
| 48 | the page build-date stamp (OF-144) | | | S2-G3-14 | | (E.md) | G3 H; round-2 root |
| 49 | the section-switch hand-over | | | S2-G3-15 | (PICTURE M13 only) | (E.md) | ≠ G3 C of WS-3 (R), behaviour kept; PICTURE M13 "nobody asked for" |
| 50 | the device watch's extra /status | | | S2-G3-16 | | | G3 OV, form only; round-2 root |
| 51 | `_urgency` in the construction sort | | | S2-G3-17 | | | G3 C; round-2 root |
| 52 | code tones on the website | | | (S2-G3-13 names their validator) | S2-G4-18 / G4M13 | (E.md) | G4 H |
| 53 | the unavailable marker, firmware and JS | | | | S2-G4-17 / G4F02 | A-B8, WS-18, BMP-12, ISL-15 | G4 K |
| 54 | two clock-valid flags | | | | S2-G4-15 / G4F06 | A-B5, NTP-16, NTP-18 | G4 R form only |
| 55 | NTP cadence chain (two `TickSeconds`) | | | | S2-G4-13 / G4R06a | NTP-12, NTP-13, NTP-15 | G4 H, C |
| 56 | the webserver's start retries | | | S2-G3-7 (W62) | S2-G4-11 / G4R05 | WS-11 | G4 H |
| 57 | the catalog's owners and bands | | | (S2-G3-7 cites the test) | S2-G4-19 / G4F07 | | G4 X (host) |
| 58 | agent tags on timed checks | | | (S2-G3-1 cites two) | S2-G4-12 / G4M10 | | no code |
| 59 | 20 "kept to narrow the Optional" branches | (S2-G1-19 has one) | | | S2-G4-22 / G4F08 | | G4 X |

# 2. Class conflicts between parts (listed, not arbitrated)

1. **The deferred flush** (line 17): G1 C (root A-B10 H, RF208); G4 R (A-B10 and A-C10 carry A.U11.28, the ref of
   the review item "A rejected setting costs no flash write", status "ok"). G1's smaller form: one `write_config()`
   after the push loop (~3 lines).
2. **The LED queue deadline** (line 20): G1 R, form only (the decision text names "up to a deadline"); G4 H (the
   owner's note gives the callers' bound as the reason). Both quote the same review item.
3. **The escalation's 1,200 ms bound** (line 8): G1 C and DELAY, removal proposed, because the reset record is written
   before the wait and the very next await takes every `owner_lock` unbounded anyway (`asy_system_service.py:305`);
   G4 kept it with the rest of the escalation.
4. **The memory-gate console lines** (line 12): G1 C (P4), G2 H (P4) for the logger-less layers and OV beside the
   logger, G4 C (P4).
5. **The bus-None contract below its root** (lines 2-3): G1 C (order 2/3 of an unreachable root) and C for SPI-2;
   G4 H for all of it. Same removal.
6. **`quiet=`** (line 10): G1 and G4 take it out; G2 keeps it while Wi-Fi's owner-settled re-arm passes it.
7. **The typing narrowings** (line 22): G1 H; G4 X.
8. **The loop-end clause** (line 40): G3 simulates the full pre-audit `try/finally` (13 emitted lines, the F811 lint
   exemption, 2 catalog rows, ~10 src lines go; B5 alone if the label is wanted); G4 keeps both labels 21 and 22 as
   the confirmed label gap (REPORT 3) and removes only the BaseException width and the pre-bind.
9. **The refusal path** (line 29): G2 proposes close-then-trace on the refusal path (C of WS-3's placement); G4 had
   proposed no change there.
10. **The section-switch hand-over** (line 49): G3 C of WS-3 (R), kept; PICTURE M13 lists it among look changes
    "nobody asked for".
11. **`_init_failed()`** (line 5): G1 H and OV; my platform table said keep without an analysis of its own.
12. **ISL-2** (line 26): G1 H; the first scan R (O-gen OR113). No other part rowed it.

# 3. The closure extended: round-2 roots and what else loses its reason

## 3.1 The round-2 roots

Every G1-G3 row classed H, C, X, OV or P4, and K whose code would go, that was not among G4's 143 roots, went in
as a root with its own seeds (`roots_round2.tsv`): S2-G1-4, -8 (the SCD30 guard), -10, -11, -15, -16, -19 (the two
sites G4 lacked), -22, -23; S2-G2-5, -6, -7, -8, -9, -10, -11; S2-G3-1, -3, -8, -9, -10, -11, -12, -13, -14, -15,
-16, -17; and A-S25, which S2-G1-11's keep depends on. Rows already among G4's roots (lines 1-3, 6-9, 11-12, 17,
20-21, 23-24, 36-37, 39-43, 45) were not repeated. G4's own corrections (section 0) changed no root.

## 3.2 New dependents and newly visible overkill (order 2 and 3)

Two rounds were run over the round-2 roots: order 2 (what each root's removal leaves without a reason), then order 3
(what those leave). The second round found two small items (S2-G4X-1's import name, S2-G4X-2's `_FIELDS`), and a
third pass over them found nothing further: a fixpoint. Only items no part had rowed get a row.

### S2-G4X-1 The reset-flag registers go with `ResetBits`, not only the getter
- where: `asy_system_service.py:20` (`mem32` in the import), `:101-104` (`_WATCHDOG_REASON`, `_CHIP_RESET`,
  `_REASON_BITS`, `_CHIP_RESET_BITS`), `:145, 151-152` (`_reset_bits` and its read), `:678-679` (`get_reset_bits()`);
  generated `_system_status()` `sensortask_wozi.py:109`, emitter `codegen.py:293`; `definitions.py:635-638`.
- what: the two RP2040 register addresses, their masks and the `mem32` read exist only to publish the raw flags.
- first scan: A-S4, G14b (H); G3's S2-G3-8 counts the key and "3 src getters"; G4's G4F05 counted the flag and masks.
- lens: order 2, removal-effect.
- condition: grep: each of the six names is used only at `:152` and in the getter; `mem32` has no other use in the
  file (the UART driver imports its own).
- class: C, order 2, root A-S4 (H).
- removal effect: ~9 src lines, 6 generated lines, 1 emitter line, the site row; tests 1 file/4 lines, tests_scripts
  1/3, and the twin's model of the two registers (digital_twin 1 file/4 lines).
- keep: the reset-reason decode (`reset_cause()`, the record, OR60), which reads none of them.
- lines: ~17.

### S2-G4X-2 Without the `State` key, the notification's state machinery has no reader
- where: `asy_notification_service.py:72-77` (5 `_STATE_*` constants), `:136-137` (`NOTIFY`'s `State` field and
  `_FIELDS`), `:201`, `:273`, `:280-294` (six assignments), `:328-329` (`_store_notif_data()`'s `state` parameter);
  generated `_notification_status()` (`sensortask_wozi.py:119`); catalog `NotifyState` (`error_catalog.json:229-235`);
  `definitions.py:699-707`.
- what: each cycle records why it evaluated nothing or only part; the one reader is the generated `/status` key.
- first scan: NT-2 (H), D-G22 (H); G3's S2-G3-8 rows the key and the table, G1's S2-G1-8 the state-4 branch only.
- lens: order 2 (key -> state codes -> the config-unreadable branch's sample store, C.md cascade 9).
- condition: pre-audit the loop had no state at all (`base/src/asy_notification_service.py`, grep: no `state`); no
  owner decision on the codes ("state-code-values" ok names the SGP40 and ISL29125 fields only).
- class: C, order 2, root D-G22 (H) with NT-2 (H).
- removal effect: ~20 src lines, the 5-row table, the key in 6 generated modules, the definitions rows; `_check_one()`
  answers a bool again once NT-3 and NT-4 go too (its None arm); tests 6 files/25 lines, tests_scripts 2/4, twin 1/2.
- keep: `Triggered` and `TS` (pre-audit), E15 for a producer that raises (`:229`, also SGP40's `:322`).
- lines: ~25.

### S2-G4X-3 The base reader's E14 constant has no user once the rung's second guard goes
- where: `asy_base_classes.py:93` (`_ERR_CALLBACK = const(14)`); its one use `:576`.
- what: the base defines E14 only for `_climb_ladder()`'s catch around `_recover_device()`.
- first scan: inside A-B13; G1's S2-G1-22 rows the catch, not the constant.
- lens: order 2.
- condition: grep: no other use in the file (other modules define their own `_ERR_CALLBACK`).
- class: C, order 2, root S2-G1-22 (H).
- removal effect: 1 line; E14 stays in the catalog (shared).
- keep: the hooks' own catches (BMP-4, SCD-7, SGP-7, R).
- lines: 1.

### S2-G4X-4 `DNS_NAME_MAX` has no user once DNS-1 and CD-2 go
- where: `asy_dns_client.py:42` (definition), `:60` (DNS-1); `asy_captive_dns.py:14, 174` (CD-2).
- what: the 255-octet name bound is shared by the resolver's refusal and the captive DNS server's drop rule.
- first scan: DNS-1, CD-2 (H); G2's S2-G2-6 rows DNS-1; CD-2 is rowed by no part.
- lens: order 2, removal-effect.
- condition: grep: these four lines are every use.
- class: C, order 2, roots DNS-1 (H) and CD-2 (H).
- removal effect: 1 definition, 1 imported name; `DNS_LABEL_MAX` stays (the pre-audit 63-octet check
  `asy_dns_client.py:62-63`, captive DNS `:169`, NTP-1's PUT check `asy_ntp_client.py:166`), `DNS_QTYPE_A` stays
  (`asy_captive_dns.py:206`, `asy_dns_client.py:78`).
- keep: CD-2's other drops are G2's to judge (no row exists); this row only says the constant follows them.
- lines: 2.

### S2-G4X-5 Buildgen reads four src constants only for a check that cannot trip
- where: `buildgen/validate.py:1173-1174` (`_TICKS_HORIZON_MS`, `_RESYNC_NUM`, `_RESYNC_DEN`, `_DRAIN_BOUND_MULT` read
  through `module_int_const()`), used only by `:1184-1202` (`bus.uart-poll-idle-range`'s upper bound and
  `instance.uart-timeout-max`).
- what: the build parses `asy_uart_comm.py` for four constants whose comparison has one fixed answer for every TOML.
- first scan: H14 (H); G3's S2-G3-3 rows the checks.
- lens: order 2.
- condition: grep at head: `_TICKS_HORIZON_MS` has no other buildgen reader; the four src constants stay in use by
  `UARTComm` itself.
- class: C, order 2, root S2-G3-3 (H).
- removal effect: the two read lines (the rest of `:1172`'s tuple stays for the poll and reply checks).
- keep: `module_int_const()` (codegen and twin wiring read it: `codegen.py:565, 595, 631`, `twin_wiring.py:134`).
- lines: 2.

### S2-G4X-6 Every removed code becomes a tombstone, not a deletion
- where: `buildgen/error_catalog.json` (`"retired": true` rows); `buildgen/definitions.py:302` drops retired texts
  from the site; `tests_scripts/test_error_catalog.py` (`test_a_retired_code_has_no_live_site`); the rule
  `SPECIFICATION.md:3653`.
- what: the catalog keeps every number it ever issued; the site loses the text.
- first scan: G3's S2-G3-7 names the rule and its 15 codes; what is new here is the per-root list.
- lens: order 2 of every code-owning root.
- condition: the rule has no owner text (G3); OR47.a: "no requirement for the fram to stay consistent through
  firmware re-flashes".
- class: C, order 2, roots as listed.
- removal effect, codes per root (G4 and round 2): E52 (G4R02), E54 (G4R03), W62 (WS-11), W67 (NT-5), W69 (A-S28), E73
  and E74 and W16 (S2-G2-5), W50 (S2-G2-9), W73 (SCD-6, with S2-G1-18), the NotifyState table (S2-G4X-2), plus G3's
  first-scan list (E28, E53, E91, E92, E115, W12 only if captive DNS also stops using it, W71, W75). W12 stays: captive
  DNS still persists it (`asy_captive_dns.py:145`).
- keep: the catalog; whether a removed number is retired or reused is the owner's call.
- lines: ~1 per code in the JSON (the flag), each text ×2 per site removed (G3's S2-G3-9).

### S2-G4X-7 The uninstalled handler would bring back an ungated print the owner turned off
- where: `asy_system_service.py:775-779` (`start_tasks()` installs `report_unretrieved()` unless a handler is set),
  `asy_print_log.py:124-137`.
- what: removing A-S25 (H) would leave asyncio's default handler, which prints "Task exception wasn't retrieved" and
  a traceback to stderr at every level for a detached task that ends raising (`extmod/asyncio/core.py:230-240,
  294-297`); the supervisor polls `done()` and does not await before that re-run.
- first scan: A-S25 (H), A-P12 (H); G1's S2-G1-11 rows only the "already set" guard.
- lens: removal-effect (a regression found by simulating a removal).
- condition: the owner ruled on this handler's output: "Q6, report_unretrieved silent at level 0: 'Option a'"
  (`owner_rulings_after_LN118.md:70`).
- class: R (keep): A-S25 and A-P12 carry an owner-chosen behaviour, whatever their first-scan class.
- removal effect: none proposed; S2-G1-11's guard (P4, 1 condition line) still goes.
- keep: the handler and its level gate, as landed (~13 lines).
- lines: ~15 involved; 1 goes (the guard).

### S2-G4X-8 The fold and the rebind removal together leave Microdot's catch unreported
- where: `asy_webserver_service.py:561-564` (the rebind), `:804-814` (`_print_exception()`).
- what: G4's S2-G4-1 folds the C-stack check into the logger; G2's S2-G2-8 removes the rebind. Microdot's own catch
  prints through `microdot.print_exception`, which then calls no logger, so a C-stack overflow caught there would set
  no flag.
- first scan: WS-9 (H); the interplay is NEW.
- lens: overlay of two removals.
- condition: owner "ok" on `c-stack-reboot` ("A C-stack overflow caught anywhere is recorded").
- class: R (keep), the smallest form: a rebind of 3-4 lines that sets the flag and prints (G2's own keep).
- removal effect: none beyond S2-G2-8.
- keep: that rebind.
- lines: ~4.

Checked in the two rounds and already rowed by another part, so no row here: `restored` dead once S2-G1-15 and A-S28
go (S2-G1-21); `GeneratedDevice.expected_facts` and `build_firmware.py:112`'s unused value (S2-G3-10);
`startShell()`'s `pageBuildDate` and the stager's `--build-date` (S2-G3-14); UART driver's `_NAME` (S2-G2-3, -11); the
proxy losing `timed_out` and `traced` (S2-G2-8, -9); `_bus_mark`'s setup-episode line (S2-G1-4); NTP's own
`_WRN_STORED_DEFAULT` (S2-G2-6); `_int_rearmed` (S2-G1-23). Checked and still in use: `module_int_const()`,
`DNS_LABEL_MAX`, `DNS_QTYPE_A`, `DNS_UDP_MAX` (CD-3's 512 B, a confirmed gap), W12 (captive DNS), E15 (producer
raise), `ConfigManager.unpersisted` (read by the shutdown flush, section 4), W32 (ISL29125's periodic-only warning is pre-audit:
`base/src/asy_isl29125_driver.py:109`).

# 4. Regression flags: dependents that are owner decisions, R rows, confirmed gaps or rare-but-real

| root | the dependent that must stay | why | minimal form |
|---|---|---|---|
| S2-G1-4 `_init_failed()` | `_init_done()`'s `self._rungs = 0`; I2C-5's boot-clear report | the ladder is O-gen R (A-B13, OR113); the boot clear is R (I2C-1) | 1 line + I2C-5's ~5 |
| S2-G1-10 bools | `UARTComm.setup()`'s bool, read by `UARTLinkDriver.setup()` (`asy_uart_link_driver.py:290-293`) to set `initialized` | a product reader on dev (UC/UL owner features) | that one bool; the rest return nothing |
| S2-G1-10 bools | each module's logger set up first in the batch | A-B16 R (OR47) | as landed |
| S2-G1-11 / A-S25 | the handler and its level gate | owner Q6 "Option a" (S2-G4X-7) | ~13 lines as landed; only the guard goes |
| S2-G1-15 pre-setup merge | the unreadable-store branch `asy_print_log.py:409-413` | A-P4 K, a confirmed gap (REPORT 3, "log store after a failed read", ~12 lines) sits beside the merge `:414-431` | keep `:409-413` and the plain write-back |
| S2-G1-16 boot-race guards | `delete_file()` under the config lock (A-C15) | the shutdown sequence (A-S9 R) | only the setup-time lock at `:593` goes; A-C9's serialise-first (confirmed) on the same line stays |
| S2-G1-22 | the hooks' own catches | BMP-4, SCD-7, SGP-7 R | as landed |
| S2-G1-23 | ISL-1's parking and ISL-3's threshold lock | R (owner) | as landed |
| S2-G1-8 `_frc_cfg_ok` | FRC readiness capture | SCD-1 R (review "scd30-calibration-readiness" ok) | the capture without its episode guard |
| S2-G2-5 resolver | DNS-2's caller-given servers, NTP-1/NTP-2's PUT refusal, `DNS_UDP_MAX` (CD-3), E72 (NTP-4, K) | R/O, and CD-3 is a confirmed gap ("captive DNS 4 KB per query") | `resolve_ipv4() -> str | None` (G2: ~3 changed lines stay) |
| S2-G2-6 | NTP-1's PUT check; W10 for Wi-Fi | O; Wi-Fi settled | as landed |
| S2-G2-7 refusal path | WS-3's traces, WS-4's `HTTPDropped`, WS-6's bound on the other arms | R, owner-agreed (2026-10-22), review note on HTTP drops | close-then-trace on the refusal arm (~2 lines moved) |
| S2-G2-8 | WS-1's bounds; the C-stack report on Microdot's catch | review "http-head-limits" ok; "c-stack-reboot" ok | WS-1 as landed + a 3-4 line rebind (S2-G4X-8) |
| S2-G2-9 | W49 (the per-call timeout) | WS-3/WS-6 | one code for both |
| S2-G2-10 | UC-4's catches | owner option (c), 2026-10-27 | as landed (6 lines) |
| S2-G2-11 | the DMA ring, `deinit()` stopping the channels | UD-1 R (OR141) | the ring and the re-init re-arm (~11 lines) |
| S2-G3-1 | one boot-clear timing check | the boot clear is R (OR113) | the exact budget sum (~12 lines) |
| S2-G3-3 | the ring and cap checks | D-H10 R (OR143.a (2)) | as landed |
| S2-G3-8 | ResetReason; `ConfigManager.unpersisted` | OR60 R; the flag is also read by the shutdown flush (`asy_system_service.py:311`), which reports an incomplete command (A-S9 R) | only the key and `get_config_unpersisted()` go |
| S2-G3-9 | the clickable codes | review "reset-reason-codes" ("Good, and make the numbers clickable ...") | one table per page |
| S2-G3-10 | the oracle | OR47.a (1) | in the test generator (~40 lines) |
| S2-G3-11 | `class_has_read_triggers()`; `bench` | G5 R; OR78.a | as landed |
| S2-G3-13 | the strict banner | pre-audit design | the pre-audit validator scope (~110 lines) |
| S2-G3-14 | the first-build compare | review "website-unattended" ok; build date genuine (owner, 2026-10-05) | as landed less the stamp |
| S2-G3-15 | the drop trace free of navigation noise | WS-3, WS-4 R | the behaviour; G3's smaller form −10 lines |
| S2-G3-16 | the device watch | review "website-unattended" ok, "website-display-details" | the watch, skipping a duplicate /status |
| G4F05 / S2-G4X-1 | the reset-reason decode | OR60 R | `reset_cause()` and the record, unchanged |
| S2-G4X-2 | `Triggered`, `TS`, E15 | pre-audit; E15 shared with SGP40 | as pre-audit |

Rare but real conditions that drop out in this round: none new. The ones that stay and are named above: CD-3's 512 B
receive, A-P4's unreadable store, the shutdown's report of an unpersisted store.

# 5. Needs verification (new in this round)

1. **S2-G4X-7's default print.** Check: on the Unix port, run a supervised task that raises with `report_unretrieved`
   not installed and DebugLevel 0; "Task exception wasn't retrieved" on stderr confirms that removing A-S25 brings
   back the print Q6 turned off; no print means the supervisor's own await always comes first and A-S25 has no
   effect at level 0.
2. Carried from G2 and G1, not repeated: the C-stack fold's stack margin (G2's S2-G2-13, G4's item 1 in G4.md).

# 6. Totals for this round

| | rows | lines involved (head) | would go | stay |
|---|---|---|---|---|
| new dependents (S2-G4X-1..6) | 6 | ~48 | ~48 (S2-G4X-6 adds a flag per code; its site texts are G3's count) | 0 |
| regression rows (S2-G4X-7, -8) | 2 | ~19 | 1 | ~18 |
| **total** | **8** | **~67** | **~49** | **~18** |

Crosswalk: 59 mechanism lines covering all 54 G1-G3 rows and G4's 22; 12 class conflicts listed. Closure: 30 new
roots, 254 rows in `G4b_closure.tsv`, two rounds to the fixpoint.
