# R5 unit fsync: FRAM access lean and synchronous; one logging form that writes inside the call (lead, 2026-11-09)

## Read first
`S/u35r/r1/common_r1.md` (binding: its "Standing direction" and the filter rule; labels `fsync_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/LOGPREP.md`
(the three options, the envelope counts, the rulings touched), FINDINGS 12.127-12.129 and 12.132 (1),
`S/u35r/r5/HANDBACK_WEBLOG.md`, `HANDBACK_BFIX.md`, `HANDBACK_CRCENG.md`, the bench probe
`S/u35/lead/probes_20261109/fram_cmd.py`. Datasheet: `/home/user/datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf`
(WEL is not reset by WRITE: continual programming). Code: int `S/wt-u35int` at 8f04f2f1. Unit B writes at the same
time (drivers and services; it never changes a log call's form).

## The evidence (bench 2026-11-09 20:29, dev idle, per call, medians less the 20 us call floor)
`spi.init()` 126 us; a lean RDSR 44 us; configure + settle + RDSR 198 us; READ 13 B 62 us, 268 B 373 us; an
`async with Lock` plus one `sleep(0)` around a lean RDSR 770 us. A firmware command (~0.6 ms) is ~0.15 configure +
~0.05 transfer + ~0.4-0.7 lock and yield. A log entry is 51 commands (~30 ms of chip time); lean and synchronous,
~3-4 ms (I). FRAM is spi0's only device on all six devices.

## Owner (verbatim, all 2026-11-09)
- 20:43:39: "... So try to get along that way as far as you can, finding objectively optimized solutions. ..."
- 21:33:48: "1. Incremental checksum was introduced especially for the FRAM. If it's obsolete now, drop it."
- 19:11:51: "solutions which are minimal and optimal at the same time through smart design"

## Your work (worktree `S/wt-fsync`, branch `audit/fsync` from int 8f04f2f1; create it; commit locally, never push)
1. SPI: the bus configures only when its last configured device differs (FRAM alone: once); a second SPI device stays
   served. FRAM driver: plain synchronous command functions, no per-command lock or yield; the WEL/RDSR checks stay;
   fewer commands only where the stored bytes and the two-block crash ordering stay exactly as they are (say why).
2. FRAM manager: synchronous chunk operations; every lock, yield, in-flight wait, generation counter and reset window
   that exists only because operations interleaved across awaits goes (LOGPREP (c)'s list; check each). Kept: the
   two-block recovery, the stored format (golden image test green throughout), the storage pause (entries stay in
   RAM while paused), the boot load and the shutdown erase stepped with their watchdog feeds.
3. Logging: one form that records, prints and writes the FRAM entry inside the call, the entry in FRAM before the
   call returns; `err_s`/`wrn_s`/`err_q`/`wrn_q` become one pair (names that say what they do, fewest changed lines);
   the writer tasks, `_write_later`/`_write_behind`, drains and reset windows go; `flush_pending()` and ResetErrors
   keep their answers. Weblog's per-lock-site round tests and `tests/_held_log.py` become the structural property
   (a log call never suspends). Do the call-site conversion as one saved transform (a script under
   `S/u35r/r5/ftmp_fsync/`, its command in the hand-back) so the lead can re-apply it to unit B's files at the merge.
4. CRC: plain functions (synchronous FRAM needs them); `run_inc()`/`check_inc()` go (owner 21:33:48 (1)); if the
   asy_ naming rule then wants the module renamed, rename it mechanically. `verify_present()` goes (12.107 (5)).
5. Tests first (seen red where they pin a change): every touched behaviour; the four-tier bus-hazard rule keeps a FRAM
   case in every tier, now the structural guarantee (no await inside an FRAM operation or a log call); the twin's
   crash-point and cut-entry tests keep their purpose. Unix-port figures per entry and per SGP40 backup, and the
   command counts, for the bench's acceptance on the next image: an entry <= 5 ms, the SGP40 backup <= 8 ms on the
   chip (if a count makes either unreachable, say so before finishing).
6. Docs, current state, fewest lines: C.7.1, C.8, F.3's FRAM rows (`hold.fram_block`, `stall.fram_command`), I.2,
   J.5's reset gap (closed), the UART modules' log entries (a bounded synchronous write, not a wait: RX by DMA, TX by
   IRQ; one line in F.5.8). Each owner ruling LOGPREP lists as touched gets one record line: which fact changed,
   decided under the owner's 20:43:39 direction (lead, 2026-11-09). UART changelog: one Class B entry if any UART
   module line changes (no wire change).

## Never
Never change a stored FRAM byte, a CRC value, a wire byte or a `/status` byte. Never remove a feature beyond the
items above. Never edit `ext/`; never read `arduino/`; never open `/root/.claude/`; no hardware. No `gc.collect()`,
no new delay. Credential filter as common_r1 says (Wi-Fi code: print only identifier matches). Scratch only under
`S/u35r/r5/ftmp_fsync/`.

## Checks and hand-back
Touched test files at both GC stages while fixing; `lint_direct.sh`; three mypy passes; then the gate under
`S/u35/lead/heavy.lock` holding `fsync` (unit B may hold it: wait while it exists; `rm` it, literal path, own
command). Sizes and `imageFreeBytes` against 8f04f2f1. One commit; budget about 3 % of the week. Hand back by 07:00
UTC: `S/u35r/r5/HANDBACK_FSYNC.md` (at most 40 lines, as common_r1 says, need against cost per changed operation),
your commit, one line per headline result, and last "nothing of mine is running".
