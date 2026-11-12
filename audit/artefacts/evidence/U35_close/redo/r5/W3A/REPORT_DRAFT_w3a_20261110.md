# The whole-project audit: final report (draft, W3a, 2026-11-10; tree 51c9c75f; lead's edits at eb8a214e)

Pre-audit tree `25caf528` (2026-09-25). Final tree `<BENCH: head after the last round and P01's green pass>`,
merged into `main` as release 2.0 with the owner's agreement (release number: owner, 2026-11-10, "It's 2.0").
The audit's records (`audit/`, `PROJECT_AUDIT_PLAN.md`) are deleted at D. Every record stays reachable from three
branches that are never deleted (owner, 2026-11-10 21:55:27): `claude/u35-audit-archive` at `<D: sha>`, the last
commit holding them; `claude/u35-bench-campaign`, the bench's evidence; `claude/u35-int-backup`, the integration history.

## 1. What the audit changed against 25caf528 (current fact, by area)
Volume, outside `audit/` and `arduino/`: 1,306 commits, 928 files (+205,158 / -164,148 lines). `src/` keeps 28
modules (seven now carry the `asy_` prefix), 13,214 -> 14,744 lines; `buildgen/` 3,681 -> 5,755; `tests/`
62,532 -> 101,601 lines; files: `tests_scripts/` 65 -> 213, `tests_hardware/` 98 -> 178, `scripts/` 20 -> 52,
`fakes/` new (5). Image and free-flash figures per device: `<BENCH: P01's firmware builds>`.
- **Errors and logs.** One global error catalog; one entry per fault per level (an error at its level, a warning
  at the level that degrades); every module's history under `GET /status` `errcount`, FRAM-backed for the FRAM
  wired modules; one history slot per repeat (the newest-entry rule).
- **Storage.** Every FRAM chunk operation and every log entry is synchronous inside its call (an entry about
  12.7 ms on silicon), no lock is held across an entry, the FRAM bus runs at 8 MHz, each chunk's CRC is seeded by
  its owner, one native CRC engine serves every check. A config file is written only when a value changes, or
  once per boot to repair a damaged one, through a deferred flush.
- **Time and scheduling.** Uptime and the NTP check are deadline sleeps on a fixed grid, with no tick timers;
  the boot stagger sleeps to its deadlines; NTP retries every 60 s while unsynced; `SysUptime` counts measured time.
- **Reset and supervision.** Every reset carries a recorded `ResetReason` (a C-stack exhaustion, a console
  interrupt, a loop that ended after boot each have their own code); every system command runs one controlled
  shutdown; `ResetErrors` is refused while a reset is decided or storage is paused; the supervisor names the task
  that ended last (`LastTaskEnd`); the boot lists run with no `gc.collect()`, under the shipped `gc.threshold(32768)`.
- **Drivers.** The four sensors share one base and recovery ladder: SCD30 frees its bus across each command wait,
  BMP3XX waits one datasheet conversion time and reads one burst, the SGP40's VOC port is bit-identical to
  Sensirion's C reference, ISL29125 gains `RangeAuto`. The LED holds one lock: an internal request queues in
  arrival order, an external command is refused while a signal runs.
- **Network and REST.** Six endpoints from one generated reference; a head guard before Microdot; refusals at the
  connection ceiling counted; `/status` streamed one response at a time; a patched lwIP copy (EAGAIN on a full send
  queue, no callbacks on a closing listener) in every image; `DNSFallback` a user setting.
- **UART link.** Bounded piece receives on a DMA ring, never blocking the loop; its own `PUT /uart` route on `dev`;
  every protocol change in `UART_C_PORT_CHANGELOG.md` for the C side's reconciliation (post-audit).
- **Build chain.** `buildgen` generates each device's task module, boot entry, page definitions and website from
  `devices/*.toml`, with one validator whose every rule names its fix; release `2.0` (`buildgen/version.py`); the
  release's stored-config and API-reference fixtures are committed and compared.
- **Tests and CI.** Four tiers (unit on the Unix port, digital twin, flash, bench); every UART hazard in both CRC
  modes; the memory gates at both GC stages read `memory allocation failed` too; D.15 member order checked over
  every Python scope; no mypy pass exempts a module from the explicit-`Any` rule; every tool pinned to its newest
  stable release (mypy 2.4.1, ruff 0.17.4, uv 0.13.7, Node 26). `npm audit`: 4 moderate, dev-only, in eslint's
  minimatch chain, no fixed release in range.
- **Docs.** SPECIFICATION.md Part 0 (every agreement binds at every level) and D.8 (a cost far beyond its need is a
  defect at its source); Part N registers firmware, build and suite-level values only; README's Release section
  is the release note against the legacy firmware.

## 2. Open findings at their terminal state (audit/sweeps/open_findings.md; W3A/N01.tsv)
73 rows open or partly closed at 51c9c75f: DONE 35, PLACED 13, TO PLACE 9, DROPPED 8, BENCH 7, OWNER 1. The five
rows whose state cell was never filled: DONE 3, TO PLACE 2. OF-16's record and DECREV 4's ninth place are one
item: done in code (87c14760, SPECIFICATION.md N.2), its two record lines corrected before the archive commit `<D>`.
- TO PLACE (one doc line each, W3b or D): the `WaitTimeNTP` 0 wording, the mock's stateless system commands
  (H.4), the stage-only wipe's root, a pre-check Edge keyring, the UART soak's stale-root note, one twin fidelity
  row (AP `isconnected()`, unlinked rssi), the escalation hold in the feed-gap check, the flash-stall model, the
  `_unix_port.sh check` gap; and two from the unfilled rows.
- BENCH: `<BENCH: each row's step result>` (VOC stretch, serving heap at the ceiling, lwIP send stall, the two
  ResetErrors refusals, the SGP40 raw walk, the owed-hardware rows; the FRAM pull and the crossover pull, step j).
- OWNER: `disallow_any_unimported` in the three mypy passes (one site left), a question the audit planned and
  never put.

## 3. Owner items O1-O6
- **O1** CI mirror check (its derived rate decides for no current install set): kept, no change, settled by
  evidence under the owner's 2026-11-09 20:43:39 direction (FINDINGS 12.171, 12.177).
- **O2** Functions with no product caller, kept under the owner's 2026-11-09 18:30:08 rule: `SPIDevice`
  `session_begin()`/`session_end()`/`*_sync`, the SCD30's six single getters, the UART's `readline()` and
  `readline_until_complete()` with `_rx_line_len`, the twin's `--seed` (12.171, 12.177); `FRAM_SPI.verify_present()`,
  removed on 11-09 without that ask against the owner's 2026-09-26 ruling, restored (eb8a214e).
- **O3** The SCD30 across a power cut: closed by the owner, 2026-11-10 16:47:07 ("The SCD30 stores everything,
  including the "Go" for continuous measurements ... Field proven many times."); no instrument (77a4e1e8).
- **O4** Agent decisions dated 2026-11-06 to 11-10 outside `audit/`, for the owner's review at this phase stop
  (rule 4.1.9): see section 4.
- **O5** The release number: the owner, 2026-11-10 16:40:55, "It's 2.0" (5b8c3446).
- **O6** The clean-chroot legs: option (a), reused chroots with their scratch in RAM, which the owner's 2026-11-07
  words ("better style yes, but no blocker") and the recipe meet; run at the final head in the last round's
  step k: `<BENCH: noble and trixie results>`.

## 4. The agent decisions for review (W3A/O4.tsv)
62 credits on 60 lines at eb8a214e (2026-11-06 28, 11-07 9, 11-09 15, 11-10 10), in eleven topics: rules of method
6, FRAM and logging synchronous 15, bounds and their sources 6, UART module layout 2, the reset sequence 1, test
tiers 5, the E.6.6 tier allow-list 10, bench and flash test design 14, website 1, Wi-Fi 1, `/status` streaming 1.
Accept a topic whole or overrule a line. The two lines W3a flagged at 51c9c75f are settled in the tree (eb8a214e):
`verify_present()` is back, and the error-log reset order's test comment credits the owner, as the code does.

## 5. Load-limit coverage (W3A/LOAD.md)
The cells, re-read at 51c9c75f, are committed with the close's records in `audit/b3/load.md` (`<W3b>`; before,
that file held a header only and the cells lived in two lane scratch files).
Every finite shared resource at each level: 13 resources x 4 levels, 52 cells; at 51c9c75f 43 still right,
8 corrected (renamed or removed tests, the FRAM write queue gone with synchronous writes, the alarm pool used by
the sensor triggers and the reset timer only), 1 owed: a captive-DNS flood on silicon (`<D: justified or a gap>`).
One entry per new load test (gap, load, limit, degradation, recovery):
1. Full soft-callback queue (L2): 64 callbacks lost back to back; rp2's depth-8 queue; every callback in the spell
   lost, nothing logged, no reset; every periodic timer fires again and every reader reads again.
2. Captive-DNS flood (L2): 200 datagrams with no pause; lwIP's per-socket queue; the excess dropped, the first drop
   logged; a query after the flood answered.
3. Zero-think-time readers (L4): four `/status` readers beside a PUT; the serving throughput; each reader above its
   floor; a GET and a PUT within the per-call cap after, no task ended, no reset.
4. Refusals at the ceiling (L4): held heads past `max_connections`; each refusal counted once in `HTTPDropped`; the
   held heads answered before they close.
5. The UART link under API load with FRAM writes and a config flush (L4): every read answered, no link failure or
   entry, the config store silent, the value read back.
6. Concurrent `/status` builds (L1): four readers; one response held at a time; all four answered.
Silicon results of 3-5 and of every L3/L4 cell: `<BENCH: step d, both images>`.

## 6. Do-not-reopen decisions at their doc sites (W3A/DNR.md)
271 rows: 244 present and current, 6 superseded by a later ruling the docs carry, 5 moot (their subject left the
tree), 1 contradicted at 51c9c75f and restored at eb8a214e (V14, `verify_present()`), 11 not located by search (a
reading before D), 4 not read (repo-text filter).

## 7. Build environment (BACKLOG.md's chroot entry)
Last satisfied: noble 2026-11-07 (bench Pi4, arm64 ports mirror; lint, typecheck, `env --tier generic`, test.sh
at 4 and 16 jobs with its scratch in RAM); trixie 2026-09-12 (GCC 14.2.0), its 2026-11-07 run not satisfied (8
twin harness failures read as microSD write stalls). Changed since: uv 0.13.7 and the dev-group pins; Node 26 and
its npm tree; a third Unix-port binary (`build-lwip`); the installer's lwIP readback, patched `modlwip.c` copy,
GC mark-stack and qstr variant header, bounded network steps, one apt install with apt's own retries; host needs
`flock`, `timeout` and a writable runtime dir; one device per hardware family in the per-device runs.
Final legs: `<BENCH: step k>`.

## 8. The last round (filled after the bench)
- Two-image GC proof (the shipped threshold against a control image without it, default flash and bench tiers):
  `<BENCH>`.
- Heap: the post-load largest free block under 6/6/6/2 readers on both images, and whether any UART receive needs
  one block above 11.4 KB; the C-stack margin (about 2.3 KB on snapshot 58): `<BENCH>`.
- FRAM chunk timing with no CS settle (F.3 rows), the boot stretch, ring peak, DNS idle poll, ResetErrors budget,
  general call per chip, BMP3XX calibration bytes, the country scan, the long soaks, the FRAM and crossover pulls,
  the wear steps last: `<BENCH>`.
- Twin corrections from silicon: the SGP40 raw walk, the general call per chip, the SCD30's argument reaction,
  ISL29125 CONFIG1, the BMP3XX calibration block (the SGP40 unknown-command timeout already follows silicon):
  `<BENCH>`.
- Coverage of the final tree (unexecuted lines, deleted or loosened tests, owner-row trace): `<BENCH>`.
- Re-verification (lint, three mypy passes, test.sh at both stages, coverage, the twin on every device, npm,
  every firmware build, `tests_hardware --collect-only`): `<BENCH: pass n of at most 3, all green>`.

## 9. D
`PROJECT_AUDIT_PLAN.md` and `audit/` deleted after every finding with forward value sits in the docs or BACKLOG;
the last commit holding them `<D>` on `claude/u35-audit-archive`, beside `claude/u35-bench-campaign` and
`claude/u35-int-backup`, none deleted; one merge into `main` as release 2.0 with the owner's agreement.
