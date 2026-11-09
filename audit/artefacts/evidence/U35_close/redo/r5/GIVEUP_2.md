giveup2 hand-back, written by the agent (Mon Nov  9 22:18:09 UTC 2026)
Pass 2 of BRIEF_GIVEUP.md (drivers, system, logging, generation), read only, tree `S/wt-u35int` 8f04f2f1 (generated modules
21:41:57, fresh). C = confirmed (code, git, datasheet read), I = inferred. Ledger `S/u35r/r5/GIVEUP_2_ledger.tsv` (one header
line, then one row per hit: loc, construct, verdict, origin, source). Not redone: CPRIM polls, SIMPLER_1-4, units B and fsync.

## Enumeration (N = the brief's name list, C = `Timer\(|settimeout|poll\(|\bwhile\b|sleep|for .* in range\(`, both `-i`)
- src: `git grep -n -i -E "N|C" 8f04f2f1 -- src/<the 18 modules not in pass 1>` = 753.
- devices: same over `devices/` = 43 (0 lines hidden by the filter). Generated: `grep` over `build/generated_src/sensortask_*.py`
  = 134 (6 Wi-Fi lines read by identifier match only: `max_module_error`).
- buildgen: same over `validate.py defaults.py` = 136 (8 read by identifier only: an AP-mode time range, a key length rule),
  plus `git grep -n -A1 "@tunable" -- buildgen/codegen.py buildgen/definitions.py` = 16 (limits.py, buildspec.py: pass 3).
- Part N: N.3 rows with a `src/` or `buildgen/` home (95) + 9 Wi-Fi rows read by name only + N.4's 4 rule rows = 108.
- Total 1,190 hits = 1,190 ledger rows = KEEP 314 + NOTBOUND 665 + IN_B 58 + IN_FSYNC 25 + REMOVE 27 + DERIVE 25 + ASK 7 +
  ROUTED 69 (Part N and generated rows of pass-1 constants: web, uart, ntp, wifi, udp, captive dns; judged at their source).

## REMOVE, ranked by gain against risk (4 sites)
1. ISL29125 settle wait capped at 2 rounds (`asy_isl29125_driver.py:128-129,651-655,794-803`; REF 75d222e2 09-14, session;
   source none, C). `time_to_settle_ms()` is a software deadline the device's own CONFIG1 writes push out: an inside wait. Goes:
   `_SETTLE_WAIT_MAX_ROUNDS`, its Part N row, the discard branch, `_unsettled_cycle` (:288,:624,:655,:712). Stays: the DS-derived
   settle deadline; no read before the chip settled. No gap: the bounded form published nothing past the cap either; now the
   cycle reads once the writes stop. dev only; one test file pins the cap (`tests/test_asy_isl29125_driver.py`), M.1.4 states it.
2. BMP3XX cmd_rdy poll before soft reset, 50 ms give-up (`asy_bmp3xx_driver.py:72-73,636`; REF 433e35ec 07-21, session; "owner-
   reviewed 2026-11-06" only, C). DS001 gives no bound (its own comment, C); legacy wrote 0xB6 unchecked (C); Bosch's
   `bmp3_soft_reset()` reads cmd_rdy once (I, the public BMP3 API, not in the datasheets repo). Simpler: one STATUS read, or
   none - the kept ERR_REG cmd_err check after the 2 ms settle already catches a rejected reset. Goes: the number, its row; with
   B item 3 the measurement poll goes too, so `_wait_status_bits()` loses its last caller. Fits B's BMP3XX change (same function).
3. Config store `delete_file()` retries `os.remove` once (`asy_config_manager.py:472`; AUD 8d44fd14 10-07, session; no legacy,
   no ruling, C). A littlefs remove on the device's own flash is synchronous and fails the same way twice (I). Goes: the loop.
   Stays: the console line and the reset record "command incomplete" (`asy_system_service.py:463`), so the failure is not silent.
4. `dns.tries` = 1 on every device (`buildgen/codegen.py:29-30`, generated `_DNS_TRIES`, Part N 12046; REF 5ddbcd39 07-28,
   session, C): a retry knob whose loop never repeats; the resolver already walks the server list (its own comment). Goes: the
   tunable, the generated constant and NtpTiming's field; the `tries` loop is pass 1's file - decide together with pass 1.

## ASK (1 site)
1. ISL29125 calibration candidate readable 10 min, then cleared (`_CAL_HOLD_MS`, :117-118,296,538-539,582; REF 75d222e2, C):
   user-visible expiry with no source. Simpler: the candidate stays until the next calibration starts or a reboot (no number).

## DERIVE, ranked (4 sites)
1. `dns.timeout_ms` 500 ms per server, all six devices (`buildgen/codegen.py:27-28`, generated; REF 5ddbcd39 07-28; Part N:
   "estimated (agent), measurement owed", C). A network peer, so a bound belongs; its number has no source. Name one: C.8's NTP
   hold under the Wi-Fi mode lock (up to four servers x (500 + 20) + 5,020 ms = 7.1 s, the row's consumer) or a measured bound.
   Legacy resolved by `getaddrinfo()` (no timeout possible, F.2). Pass 1 judges the resolver module.
2. SGP40 measure wait 100 ms (`:76-77,642`; REF 5ff8c0b9 07-21, C): DS Table 8 / 3.2 gives 30 ms max (C, read); legacy 500 ms.
   Derive as the heater-off wait does (`_HEATER_OFF_MAX_MS + 1`): 30 ms + one tick, or name the 3.3x margin. Bench check (chip).
3. SCD30 soft-reset wait 2,500 ms (`:78-79,862`; REF 7267509c 07-21, C): Interface Description 1.1 "boot-up time is < 2 s"
   (C, read); legacy 0.2 s. The code says "wait the full bound", then adds 0.5 s: 2,000 ms, or name the margin. Setup/recovery only.
4. ISL29125 calibration run 120 s (`_CAL_WINDOW_MS`; owner 2026-09-13 "a bounded, user-started run", C): the bound is ruled,
   "~100 attempts" is the agent's (09-14). Name the count's reason or derive it from the converge rule. dev only; lowest gain.

## In B / in fsync (not judged again)
- B: LED 120 s wait, its poll and ramp (12 + 8 rows); BMP3XX data-ready poll and 300 ms give-up; uptime tick, stagger one-shot,
  `arm_tick_timer()`, notification pause tick and refusal drain; SCD30's yields between bus sessions. fsync: `verify_present()`'s
  1,000 ms `wait_for_ms` lock give-up (an inside wait: goes with the function); per-command yields; the log writer, generation and
  reset in-flight bits.

## KEEP and clean
Legacy values (C, `legacy/`): reset 4 s, supervisor 2 s, budget 100/300, signature 120 s, pause cap 3,600 s, starts 1000/N ms,
max_error 5, WDT 8 s, NTP fetch 5 s, notification 600 s / 0.1 s / 3,600 s / 2 x flash, LED floor 0.1 s, SCD30 50 and 10 ms, 500
ms tick, stuck-pin 2 x trigger_s (3 s), SGP40 3 / 500 / 1,000 ms, WaitTimeNTP cap 600 s, BackupMaxAge, I2C probe settle 100 ms.
Owner-ruled: FRAM RDID x3 (10-28), mempause deadline (10-28), reset one-shot (07-18), ladder order (OR113, 09-30; 2/3/4 = one
rung per failed cycle below the legacy give-up), HTTPDropped 24 h window (10-01), SCD30 "not measuring" after two intervals
(11-04), WREN/WRDI one retry (OR113's first rung). DS or derived: bus-clear SCL bound (rp2 I2C timeout) and 9 pulses, I2C 200 ms
(SCD30 stretch 150 ms, C) and its cap (2 x 11 x 200 ms < 8 s), Bosch 2 ms settle, SGP40 heater 1 ms + 1, FRC 6 min / 5
intervals and window cap, ISL settle deadline, CS settle, J.8 transfer cap, max_connections 6 (lwIP less 3), AutoRangeDwell
(user setting). Everything else NOTBOUND: value domains, plausibility gates, counters, loops, log calls, comments.

## Findings
- "owner-reviewed, 2026-11-06" is no source: the LED's 120 s carried it (Part N 12083) and was overkill (owner 21:36:14). In my
  scope the tag also sits on the BMP3XX 50 ms (REMOVE 2); the ladder keeps its numbers on OR113's order, not on the tag.
- The pattern in this scope, generalised: an inside wait takes no number (LED, verify_present, ISL settle); an outside wait takes
  the source's number (DS maximum + one tick, legacy, owner) or none where a check after the fact already catches the failure
  (BMP3XX ERR_REG); a retry exists only as OR113's one transaction retry on a chip, never on a deterministic local store.
- Outside the enumeration, found by reading: SCD30 missed-measurement window (`_frc_idle_ticks > 3 * interval`, 1.5 intervals,
  AUD 5689e2f4): KEEP, derived midpoint between one and two of the chip's intervals; ISL `periodic_only_warn_at` 5 is a
  diagnostic threshold, not a bound (its Part N row NOTBOUND).
- Slip: one `pdftotext` read of the SGP40 datasheet (a reader, not git or grep); every other datasheet read by the Read tool.
  No tree edited, no gate, no test, no hardware; scratch only in `ftmp_giveup2/`; 0 filter-word lines in this file and the ledger.
