# R5 owner-prep logprep: the facts for the owner's logging question (lead, 2026-11-09; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding, its "Standing direction" above all; label `logprep_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Tree `S/wt-u35int` at f1a734f5,
read only. Then `S/u35r/r5/SIMPLER_2.md` item 2, `S/u35r/r5/HANDBACK_BFIX.md`, `S/u35r/r5/CPRIM.md` sections 1-2
(the chip CRC figures: viper hoisted 0.95 ms per 264 B, binascii 0.09 ms), FINDINGS 12.125-12.126. Units writing now:
crceng (`asy_crc_checks`, `asy_fram_manager`, the UART modules) and weblog (`asy_webserver_service`, `asy_print_log`
reset, five lock sites); read their files at f1a734f5 only, never their worktrees.

## The question the owner will get
Errors are logged two ways: `err_s()/wrn_s()` await the FRAM write, `err_q()/wrn_q()` record and print at once and
one writer task per store writes behind. Which single form is the simplest that never makes a caller wait on FRAM and
loses no entry before a hang or reset? Size three options, facts only:
- (a) Today's two forms after weblog: what couplings remain (which callers can still wait on FRAM through a log
  while holding something others need), and the per-site audit that keeps them in check.
- (b) `_q` as the one form, plus a drain of each store's writer before the storage pause and reset. The `src/` sites
  and test sites that change; the coroutine frames saved; which `src/` sites log and then, before that task's next
  await, run a step that can block the loop or reset (getaddrinfo, a bus recovery, `machine.reset()`, a long
  synchronous loop): there the entry is lost on a hang where today it lands. A drain at those known sites: how many.
- (c) FRAM access made synchronous: with the native CRC engine, the worst-case silicon time of each FRAM operation
  in the run phase (the largest chunk write and read, at the driver's 8 MHz; the boot load apart), what else uses
  that SPI bus on any device (TOMLs, filtered), what the per-command yields and the two FRAM locks protect then,
  and whether a log entry could then be written at once inside the logging call (no writer task, no wait, the entry
  in FRAM before the call returns). Weigh that blocking time against the loop's other synchronous steps
  (STRETCH.md's figures) and the UART's hardware FIFO at the dev link's baud. Name every owner ruling it touches
  (the 2026-09-18 whole-bus hold, the per-command yield's record, CLAUDE.md's FRAM-log diagnostic rule) with its
  record.
Per option: lines and sites that change (src, tests), what goes, which gap opens or closes, the silicon cost, C or I.

## Never
Never edit any tree. No gate or whole-tier run; single-file probes through `S/u35/lead/run.sh` at most. No hardware.
Never read `arduino/` (`':!arduino'` in every git grep and log); never open `/root/.claude/`. Credential filter on
every view or grep of repo text; never print, copy or write any Wi-Fi credential or the hotspot password. Scratch only
under `S/u35r/r5/ftmp_logprep/`.

## Hand-back
Write only `S/u35r/r5/LOGPREP.md` (at most 40 lines; first line "logprep hand-back, written by the agent (<date
-u>)"). Budget about 1 % of the week. Hand back by 21:30 UTC: its path, one line per option, and last "nothing of
mine is running".
