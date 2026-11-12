# The whole-project audit: final report (draft; W3a 2026-11-10 at 51c9c75f; lead update 2026-11-12 at 67e47fa6)

Pre-audit tree `25caf528` (2026-09-25). Final tree `67e47fa6` unless the bench's last steps change code
(10g PASS 2026-11-12; `<BENCH: k, wear>`; P01: `<gate66 on 67e47fa6>`, CI run 43167146357 on snapshot 65 `4d4d8a60`),
merged into `main` as release 2.0 with the owner's agreement (release number: owner, 2026-11-10, "It's 2.0").
The audit's records (`audit/`, `PROJECT_AUDIT_PLAN.md`) are deleted at D. Every record stays reachable from three
branches that are never deleted (owner, 2026-11-10 21:55:27): `claude/u35-audit-archive` at `<D: sha>`, the last
commit holding them; `claude/u35-bench-campaign`, the bench's evidence; `claude/u35-int-backup`, the integration history.

## 1. What the audit changed against 25caf528 (current fact, by area)
Volume at 67e47fa6, outside `audit/` and `arduino/`: 1,327 commits (1,197 without merges), 929 files
(+204,547 / -163,742 lines). `src/` keeps 28 modules (seven now carry the `asy_` prefix), 13,214 -> 14,738 lines;
`buildgen/` 3,681 -> 5,755; `tests/` 62,532 -> 101,776 lines; files: `tests_scripts/` 65 -> 213, `tests_hardware/`
98 -> 178, `scripts/` 20 -> 52, `fakes/` new (6). Images at 7c142edd (of 1,228,800 B before the filesystem): dev 1,157,508 B (94.2 %, 71,292 B free); arzi,
grkizi, klkizi and schlafzi 1,096,580-1,096,604 B (89.2 %, about 132,200 B free); wozi 1,106,864 B (90.1 %).
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
  queue, no callbacks on a closing listener) in every image, with `TCP_SND_BUF` 1,600 B: five clients that stop
  reading cannot fill the 12,000 B send pool (6,400 B let two block every route); `DNSFallback` a user setting.
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
item: done in code (87c14760, SPECIFICATION.md N.2); its two record lines state it since `7f47edbe` (2026-11-12).
- TO PLACE: W3b (f3c4fe9f, 67e47fa6) placed the firmware facts: the `WaitTimeNTP` 0 wording (DEVICE_REFERENCE.md;
  no warning is logged, as code and legacy show) and the stage-only wipe's root (build_device_websites.sh). The
  test, twin and tooling lines (H.4 mock, Edge keyring, UART soak root, twin fidelity row, feed-gap hold,
  flash-stall model, `_unix_port.sh check`, two unfilled rows) stay in the archived record: firmware facts only.
- BENCH, on the final image (11-11, bench notes 14:30-20:35): the serving heap at the ceiling, the lwIP send stall
  (page 0.508-0.63 s) and the two ResetErrors refusals pass in the bench tier; the SGP40 now matches the twin (step
  d's A). Still owed: the VOC stretch `<BENCH>`, and the owed-hardware rows with the FRAM and crossover pulls (j,
  a later window).
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
  step k (2026-11-12): `<BENCH: noble and trixie results>`.

## 4. The agent decisions for review (W3A/O4.tsv)
62 credits on 60 lines at eb8a214e (2026-11-06 28, 11-07 9, 11-09 15, 11-10 10), in eleven topics: rules of method
6, FRAM and logging synchronous 15, bounds and their sources 6, UART module layout 2, the reset sequence 1, test
tiers 5, the E.6.6 tier allow-list 10, bench and flash test design 14, website 1, Wi-Fi 1, `/status` streaming 1.
The two lines W3a flagged at 51c9c75f are settled in the tree (eb8a214e): `verify_present()` is back, and the
error-log reset order's test comment credits the owner, as the code does. **Reviewed by the owner 2026-11-12
07:45-08:40: all eleven topics accepted whole, no line overruled.** Two follow-ups: the BMP3XX conversion wait's
owed bench check (SPEC's BMP3XX timing row) goes to the later bench window as a read-only measurement; the
README's "next bench run settles the `REDIRECT`" sentence is dropped, the final-image run having settled it.
OF-239 (`disallow_any_unimported`): not adopted, the lead's decision under the owner's 2026-11-11 rules (tooling
only, no firmware effect); told to the owner 2026-11-12.

## 5. Load-limit coverage (W3A/LOAD.md)
The cells, re-read at 51c9c75f, are committed in `audit/b3/load.md` (2026-11-12, `7f47edbe`; before, that file
held a header only and the cells lived in two lane scratch files).
Every finite shared resource at each level: 13 resources x 4 levels, 52 cells; at 51c9c75f 43 still right,
8 corrected (renamed or removed tests, the FRAM write queue gone with synchronous writes, the alarm pool used by
the sensor triggers and the reset timer only), 1 owed, justified 2026-11-12: a captive-DNS flood on silicon holds at most the pinned modlwip's 4-datagram UDP queue
(`extmod/modlwip.c:299`, `:456-460`), the rest freed on arrival; the answering logic is L1's and L2's.
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
Silicon, final image (11-11; 6,400 B image in step d, 1,600 B image from 14:14): flash tier 90 passed, 2 failed (the
C-stack and heap bounds the owner replaced that day; both nodes pass under the new bounds); bench tier 110 passed,
1 failed (invalid_record: the script's missing USB flush, test-side, passes after the fix) and 10 teardown log
checks (SGP40 W33-W35, NTP E71 from two silent pool servers, WEBSERVER W51 on a reclaim during a WLAN reconnect,
the bootloader node's FRAM E46+W63 harness cut, clean on rerun); 5h rc 0. Entries 3-5 pass in call; entry 5's
teardown keeps WEBSERVER W51. The GC control image's arm: 5g 108 passed, 3 failed, 11 errors (known items, 20:04).

## 6. Do-not-reopen decisions at their doc sites (W3A/DNR.md)
271 rows: 244 present and current, 6 superseded by a later ruling the docs carry, 5 moot (their subject left the
tree), 1 contradicted at 51c9c75f and restored at eb8a214e (V14, `verify_present()`), 11 not located by search, 4 not
read (repo-text filter). Of the 11, read 2026-11-12: the five firmware-side ones stand under other wording (A24
SPECIFICATION.md:8096, L11 :6223, L21 :1294/:6333, L27 HEAP_FRAGMENTATION_MEASUREMENTS.md M7, L70
`src/asy_uart_comm.py:1136` and J.3); the six test and twin rows (A51, E09, V54, V61, L24, L61) stay in the
archived record.

## 7. Build environment (BACKLOG.md's chroot entry)
Last satisfied: noble 2026-11-07 (bench Pi4, arm64 ports mirror; lint, typecheck, `env --tier generic`, test.sh
at 4 and 16 jobs with its scratch in RAM); trixie 2026-09-12 (GCC 14.2.0), its 2026-11-07 run not satisfied (8
twin harness failures read as microSD write stalls). Changed since: uv 0.13.7 and the dev-group pins; Node 26 and
its npm tree; a third Unix-port binary (`build-lwip`); the installer's lwIP readback, patched `modlwip.c` copy,
GC mark-stack and qstr variant header, bounded network steps, one apt install with apt's own retries; host needs
`flock`, `timeout` and a writable runtime dir; one device per hardware family in the per-device runs.
Since then also `TCP_SND_BUF` 1,600 in `toolchain/versions.toml` [lwip].
Final legs (step k, 2026-11-12, bench Pi4, arm64): noble in its 11-07 chroot: env generic, lint and typecheck rc 0;
test.sh's MicroPython tier green (5,261 tests); tests_scripts 6,544 passed, 20 red on one host cause (no native
emitter in v1.29.0's aarch64 Unix port, in five files that built their own paths). Fixed on the owner's B (13:01):
int 33c7d0d9, proven under an arm64 simulation (20 red before, 251 passed after); the real proof is the trixie leg,
moved to the later window (its chroot was gone; rebuilding it would have pushed the wear past 21:33). Recipe finding:
a reused chroot reinstalls the pinned uv when the pin moves (README, 33c7d0d9).

## 8. The last round (bench 2026-11-11 and 11-12, dev image at 67e47fa6's src/)
- **Two-image GC proof** (11-11, FC 4+5): with the shipped `gc.threshold(32768)` the largest free block after a
  collect in operation is 20,288-57,792 B; the control image without it holds 3,456-7,632 B (the reactive default's
  known placement). The control's reds were test-side or the two known teardown log checks; no firmware verdict.
- **Heap** (dev): build survivors 35,936-36,176 B against the owner's bound 41,000 B (2026-11-11); largest free block
  after the build 35,136 B against 32,768 B; in operation 81,984-82,400 B free after one collect against dev's
  serving demand 68,790 B at the connection ceiling (about 13.2 KB margin); 14,000-15,616 B minimum under 6 readers.
- **C stack** (dev): quiet setup peak 4,796 B, provoked end 6,060 B of 7,936 B (1,876 B left; the owner's reserve
  1,024 B, 2026-11-11), after the FRAM path went from 13 to 10 pass-through levels.
- **Send stall** (11-11): two clients that stop reading blocked every route at `TCP_SND_BUF` 6,400 B (page closed at
  5.3 s); at 1,600 B (lead, under the owner's 13:24:56 and 13:38:57 delegation) five fit the 12,000 B pool, the
  send-stall test passes (page 0.508-0.63 s, five at zero window), the page costs 36-99 ms more (median 0.648 s
  against 0.580 s, max 0.801 s against 0.702 s). One failure on the GC control under host load 5-7, the dev rerun passed. Open: one 90 s silence
  at 6,400 B, checked by the 6 h HTTP soak (10g, 2026-11-12 05:54-11:56, final image): PASS, 6 of 39,132 GETs
  failed (bound 0.1 %), no silence (one of 90 s would fail ~160), no reboot or task end, every FRAM error log 0
  after it, MemFree 76,192 B. The BACKLOG question closed (5d7759cb), its fact kept in SPEC B.14.2.
- **Boot NTP E71** (step d): two pool servers never replied (tcpdump: one request, reply in 46 ms when it came);
  external, not product. **12d** (11-12): 15 `ResetErrors` answered 200 in 0.62-0.91 s, every log 0.
- **Wear** (11-12, after the owner's clearance, 06:14): 7b counted (three test-side reds recorded: restore order, W22 after a config reset, W81 where the test names NO_AP); 8f PASS; 8b's three CRC-16 link checks passed, its restore reflash then hit the known stale AP station entry (no kick before that reflash) and the board rejoined on its own after its access-point window, test-side; 10b: 21 passed, the wrong-password test failed on its own probe (the board left its access point 35-37 s after the PUT, inside the test's 40 s bound, but the host's network manager reported the link about 15 s late), its later tests cascaded and the board was restored over USB (the owner's choice), test-side; 15 did not reach its check (the tick-offset image hit the same stale AP station entry after its reflash and did not serve within 120 s), test-side, its rollover evidence still missing (the owner chose a rerun in the later window, 14:34, with the reflash now clearing the stale entry) `<BENCH: 15 rerun>`; 7f (the flash tier with the persistence-write gate open, its gated tests run for the first time): 11 of 16 passed; the config-write ring test could never pass with the 512 B responder ring (it read a 4.6 KB stream only afterwards) and was removed, the float probe starved its own watchdog (fixed, rerun owed), config reset met a stray legacy config file on the bench board and the light-sensor scenario saw real light, all test-side or bench environment.
  Later window: j (M1, the FRAM and RUN-pin manual items), 16b's power-cycle half, 13 (an AP on channel 13).
- **Re-verification (P01)**: gate66 on 67e47fa6 green (unit at both GC stages, twins at both, web tier); CI on
  snapshot 65 26/27, the coverage job's one twin-test timing defect fixed (7c142edd, test only); CI on snapshot 66
  `503c9c83`: green (run 43175368651, 2026-11-12 07:52); snapshot 67 `e55eccf3`: green (run 43214589908, 12:29); `tests_hardware --collect-only` at 7c142edd: 216 of 249 collected (33 deselected by
  the opt-in gates), no collection error.

## 9. D
`PROJECT_AUDIT_PLAN.md` and `audit/` deleted after every finding with forward value sits in the docs or BACKLOG;
the last commit holding them `<D>` on `claude/u35-audit-archive`, beside `claude/u35-bench-campaign` and
`claude/u35-int-backup`, none deleted; one merge into `main` as release 2.0 with the owner's agreement.
