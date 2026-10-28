# Full scan: the audit against the pre-audit state

Written by the lead, 2026-10-28 08:03 UTC. Range: the audit's start `25caf528` (2026-09-25) to the integration head
`497b3eda`. Read-only: nothing in the repo changed, nothing was built. Seven scan parts, each checked by the lead
against git before it went in here (section 12 lists what was checked and the corrections made).

Detail files, next to this one:
- **Firmware parts:** A.md (core and storage), B.md (network and UART), C.md (drivers and LED) and D.md (buildgen and
  generated code), with one row per change, its evidence, class, triage, scheme check and minimal change.
- **Other parts:** E.md (tests, tooling, website), F.md (docs and repo), G.md (the audit's course).
- **The drift analysis:** DRIFT.md, how the audit drifted, what it caused and how it could have been prevented.
- **Measurements and reproductions:** L_flash.md (bytecode sizes); `repro/` holds the reproduction scripts and their
  logs. The pre-audit source they ran against was extracted with `git archive 25caf528` and is not copied here.

## Why this scan, in the owner's words (2026-10-28)

- "I completely don't understand what lead you to implementing a pattern like that arbitrary 5 minutes check. That's
  high complexity on a limited device, undesirable as such. At least as far as I understand, it patches a rather
  hypothetical issue instead of cleanly and minimally implementing something clean. And anyhow, hardcoded delay
  checks like this are a very bad, very awkward pattern. Multiple issues we have in our pillars to strictly avoid.
  Looking at the immense effort you put into certain activities, including trying to debug the Micropython
  sources,which could not be more out of our scope , I wonder if the whole audit drifted into a wrong direction."
- "The verification machinery never was the goal of "perfection". The firmware shall be the main target, the buildgen
  as well. The unit tests shall have good quality, but don't need deep dives. The audit verification machinery is
  just a temporary tool. So we will have to find a distinction where to put the effort."
- "One of my biggest concerns is that much complexity was added to the firmware. Patching things was never an option,
  clean and minimal code always was the target. And building upon hypothetical findings is a clear no-go, especially
  if it leads to cascading effects like the one we stumbled upon."
- "Just to clarify what my expectations for the audit were from the very beginning: - A deep analysis of the big
  picture - Consolidation over the whole project - Agreed on new features being added - Docs to be consolidated -
  Repo cleanup - firmware quality already was high. So I expected some details changed due to findings, but in the
  dimension of a few lines per module, very minimal and clever. Not missing anything, but being smart and lean.
  Surely not by patching multiple loops over another. - The audit exceeded my expected time budget by a factor of 4
  and token usage by a factor of 15 and is not even done yet"
- "We will have to sort out the results up to now: real improvements, excessive growth, real findings, hypothetical
  findings, runaway situations, real investigations. And for the firmware and buildgen, a real diff against
  pre-audit. The current firmware size would not even fit the device's flash, I assume."
- "Our findings and gained knowledge are extremely valuable. Speculative and hypothetical effects maybe, maybe not.
  Resulting cascades are a red flag at least. So a fine distinction, looking at the big picture (full diff to the
  start), is required now."
- "Hypothetical findings which are suspicious to be real need to be verified"
- "Just to clarify. Firmware state at the beginning was already quite solid. We gained substantial knowledge ever
  since. The mistake was how that went into the project. My expectation is that no real, verified gap is
  re-introduced. But the way it flows into the firmware and buildgen is *really* minimal change."
- "While,you scan, check for violations of our project scheme and pillars, much of the excessive additions do violate
  them"

## What went wrong (agent, 2026-10-28; the owner agreed: "I agree with wour conclusions about scope and effort.")

1. **The wrong objective.** Each unit aimed at perfection of its area. The objective was lean consolidation, a few
   lines per module.
2. **Every finding became code.** A finding by reading, never observed, went straight into the firmware as a guard,
   a fallback or a timed check. It should have gone in as knowledge, a test, or a question to the owner.
3. **Rigor rules applied without scope.** Rules written for the firmware (bite every test, cover every cell, measure
   every tunable) were applied to the test machinery and the audit records as well, so the effort multiplied.
4. **Self-generated work.** Records, walks, scans and gates produced findings about themselves. Each finding
   started a lane, and lanes started follow-up lanes.
5. **Cascades.** An addition built on a hypothesis created a real defect or a new need, which was fixed with more
   code. Examples: the NeoPixel rewrite, the UDP deadline, the NTP cadence and the I2C bool contract.
6. **No cost feedback.** Neither flash, nor CI time, nor the token budget was checked against the plan as the work
   grew.

## The short answer

- **Your assessment is right.** The pre-audit firmware was solid. No scan found a single observed failure of the
  pre-audit firmware on the bench or in the field. What the audit added is mostly owner-decided features plus a large
  layer of hardening built on hypothetical findings, and of cascades built on that hardening.
- **The firmware still fits, but the audit spent about 61 % of the free flash.** The dev image of 2026-10-26 uses
  about 1,158 KB of the 1,200 KB firmware region, leaving about 43 KB; the audit's own U0 baseline left 107 KB. The
  audit's own `src/` growth is about 47 KB of bytecode (+29 %). (Corrected 2026-10-28 from "about half", which was
  estimated from bytecode before the baseline's image sizes were found; `DRIFT.md` 2.8.)
- **Real gaps in the pre-audit code exist, and they are small.** The scans confirmed 17 of them, most closable in 1
  to 14 lines (section 3). Four of them can happen in normal operation.
- **In doubt is roughly 40 % of the changed firmware lines**: about 1,640 of about 3,900, classed hypothetical,
  excessive or cascade (section 2). "Built on a hypothetical" is the most-violated rule in every firmware group.
- **Many "owner decisions" are ticks on an agent-written review page.** That page holds 69 answered items, 45 of them
  "ok". Several rest on hypothetical premises, the C-stack reboot among them (section 6).
- **Outside the firmware, growth ran far ahead of the product.**
  - Tests and tooling went from 106 k to 233 k lines, about 20 lines per product line.
  - SPECIFICATION.md tripled in bytes; one register of mostly test values is 47 % of all doc growth.
  - audit/ is 14,052 files and 127 MB.

## 1. Flash

| | before the audit | now |
|---|---|---|
| `src/` bytecode (pinned mpy-cross, per module) | 164,566 B | 211,648 B (+47,082 B, +29 %) |
| dev image payload (UF2) | about 1,093 KB, 107 KB free (U0 baseline, 2,238,464 B UF2) | about 1,158 KB, about 43 KB free (2,371,072 B UF2, lane build of 2026-10-26) |

- **Largest growth:** system service +5.6 KB, base classes +5.3 KB, webserver +4.5 KB, UART driver +4.0 KB, SCD30
  +3.7 KB, print log +2.7 KB, config manager +2.4 KB, NTP +2.2 KB, SGP40 +2.1 KB, UART link +2.0 KB, FRAM manager
  +2.0 KB, I2C +2.0 KB.
- **Smaller than before:** NeoPixel, notification service and UDP socket.
- **Also frozen into every image:** the website's `js/` grew 94 % in lines; no before/after size was measured.
- **Not measured:**
  - (Was listed here: the image size before the audit. It was measured after all, by the audit's own baseline at U0,
    `audit/artefacts/ENV/baseline.md`, and no later unit compared against it.)
  - The generated device modules' pre-audit size. They are 6.8-7.8 KB per device now.

## 2. Firmware: what each change is

One row per behavioural change. The classes:
- **R (real):** an owner decision, or an observed failure.
- **H (hypothetical):** found by reading or a scan, never observed.
- **X (excessive):** right intent, too much code.
- **C (cascade):** exists because of another addition.
- **K (knowledge):** a real fact, but its code is beyond need.

Lines are added or changed lines, so the sums exceed the net growth (+2,649 non-comment lines).

| group | rows | R | K | H | X | C |
|---|---|---|---|---|---|---|
| A core and storage (10 files) | 140 | 60 / 607 | 8 / 91 | 45 / 369 | 3 / 77 | 32 / 177 |
| B network and UART (9 files) | 132 | 64 / 887 | 16 / 91 | 43 / 325 | 3 / 44 | 6 / 37 |
| C drivers and LED (9 files) | 108 | 42 / 589 | 0 | 42 / 332 | 2 / 81 | 22 / 201 |
| **src/ total** | **380** | **166 / ~2,080** | **24 / ~180** | **130 / ~1,030** | **8 / ~200** | **60 / ~415** |
| D generated device code | 44 | 35 / 45 lines | 2 / 10 | 6 / 5 | 0 | 1 / 1 |
| D buildgen (host only, +2,035 lines) | 32 | 13 / ~1,516 | 1 / ~25 | 15 / ~314 | 1 / ~70 | 2 / ~110 |

How to read the table:
- **Observed failures:** none in the device code. The only F rows are a measured 12 KB copy per GET in the audit's
  own UART echo path, and a buildgen performance measurement.
- **The R column is mostly your features:**
  - the UART DMA ring (~214 lines) and the dev hazard mode (~95);
  - the controlled shutdown and the system commands (~150);
  - SCD30 calibration readiness (~130) and compare-before-write (~60);
  - Wi-Fi silent mode, the reset-reason record, TimeStale, the timestamps held back until NTP;
  - the error catalog, config objects, the newest-entry log rule.
- **Not all R is equally firm.** Group C counts 13 rows (~104 lines) as R where an agent applied one of your general
  principles to a case it found by reading: the I2C recovery ladder, the counter caps, the task ends. Group B classed
  that pattern as H. Six of those 13 have triggers that are implausible on these devices.
- **The generated device code is lean:** +45 lines on wozi, and −61 removed.
- **Buildgen's growth is host code.** About 314 lines of it are build checks that no current device TOML can trip.

## 3. Real gaps in the pre-audit code (the minimal-change list)

Each one was reproduced against the pre-audit code on the pinned Unix port (3 runs each, identical), or confirmed
from the pinned MicroPython v1.29.0 source. All are already fixed at head; the size is the smallest fix against the
pre-audit code, which in most cases is smaller than what landed.

**Can happen in normal operation:**

| gap | what the device does | smallest fix |
|---|---|---|
| ISL29125 settle deadline | after 6.2 days without a config write, the light sensor's read task sleeps about 6.2 days (`ticks_diff` past 2**29 ms) | 3 lines |
| FRAM blank chunk | a never-written chunk read twice reads invalid and logs 4 FRAM entries (legacy has the same defect) | 2 lines |
| I2C register-byte NACK | a NACKed register byte leaves the read buffer untouched with no error: old bytes decode as a fresh reading (frequency board-only) | ~5 lines |
| I2C data-byte NACK | a write the chip did not take answers success (frequency board-only) | ~4 lines |

**Rare trigger, real consequence:**

| gap | what the device does | smallest fix |
|---|---|---|
| SGP40 restore cycle | a read error on the one restore cycle overwrites the stored VOC backup 55 s later with the unlearned state | 3 lines |
| NTP zero timestamp | a stratum-2 reply with a zero transmit timestamp sets the clock to 2036-02-07 (legacy too) | 3 lines |
| config write cut part-way | a `json.dump()` failing mid-write leaves an unparseable config file | 4 lines (serialise first) |
| log store after a failed read | the log store's setup overwrites the FRAM history after any failed read | ~12 lines |
| FRAM layout shift | after a reflash that drops one of two equal-size chunks, a module reads its neighbour's history as its own | ~14 lines |
| captive DNS flood | the DNS loop never yields while datagrams keep arriving (watchdog consequence not reproduced) | 1 line |
| captive DNS 4 KB per query | `recvfrom(4096)` allocates 4 KB per query in hotspot mode (consequence unverified) | 1 line |
| config staged before its task | a MemoryError creating the flush task leaves a config served but never stored | ~3 lines |
| emergency exception buffer | rp2 reserves none, so a heap-exhaustion error carries no message | 2 lines |
| loop-end reset label | a Ctrl-C or loop-end exit reads as a plain watchdog reset (label only) | small, in the boot entry |
| lwIP listener close | an upstream lwIP assert on closing a listener, reached by shutdown and supervisor restarts (host-reproduced; silicon check prepared, not run) | toolchain patch, as landed |

**Small but real:**

| gap | what the device does | smallest fix |
|---|---|---|
| CRC32 | it leaves rp2's small-int range on every bit step, so it allocates per bit (efficiency only) | ~22 lines, or leave it |
| light-theme contrast | 4.16:1 on the website | as landed |

**Refuted:**
- alarm-pool exhaustion in normal operation;
- the pause callback;
- the bus-spread order;
- unpersisted config being hidden (the pre-audit code already logged it);
- the webserver holding a second copy of the response.

**The NeoPixel 5-minute rewrite is the reverse case.** It was hypothetical, and it created a real defect of its own:
the lost shutdown cancel. The minimal change is to revert it to the pre-audit `await ...wait()`, which removes 5
lines.

## 4. Hypotheticals and cascades: the code in doubt

Largest first. All of it is code the device carries today.

1. **The C-stack escalation** (`report_if_fatal()` at about 120 call sites, a fatal flag, the supervisor's stack
   branch, a 1200 ms bounded wait on its log write).
   - The trigger, a C-stack overflow in normal operation, has never been measured; the board reading is owed.
   - You ticked it "ok" on the review page (section 6). Groups A and B disagreed on its class because of that.
2. **The I2C "bus not initialized" contract.** The recovery ladder's no-controller state made a "no bus" result
   reachable at run time. Four drivers then gained `raise OSError("I2C bus not initialized")`: 26 sites now, 1
   before, about 77 lines. Only a failed controller re-construction produces that state.
3. **The lost-FRAM-chip chain**, about 8 linked additions:
   - a `lost` event and silent chunk operations;
   - an RDID probe for blank reads;
   - the re-setup of a lost chip, erase-readiness checks and `is_ready()`.

   Its root (what the SPI line reads with the chip absent) is unverified. One finding in it is still open.
4. **Console lines that exist for the test tiers' memory gates**, a P4 break ("nothing in the product for tests"):
   - console output in RegionBuffer, the COBS codec, the timer arm, the FRAM read copy and the logger;
   - a caught MemoryError printed at every debug level.

   One open finding says such a line can hold the loop for 500 ms behind an unread USB host.
5. **Hardcoded delay checks**, your "very bad, very awkward pattern":
   - the NeoPixel 300 s rewrite;
   - the LED queue's 120 s deadline;
   - two 10,800 s sample-age checks (notification, SGP40);
   - the 1200 ms escalation wait;
   - the webserver's 3 retries 5 s apart;
   - the per-call bound on a connection's log trace (a patch around FRAM latency);
   - the NTP cadence rounding.
6. **Fix-of-a-fix chains:**
   - **NTP cadence:** three commits, about 14 lines, for a 10 s slack you called irrelevant on 2026-10-27.
   - **UDP deadline:** the audit moved `ready()` onto `wait_for_ms()`, which lost a cancel. The redo moved it back.
     Against the pre-audit code the net change is the deadline's precision only.
   - **Loop-exit reset record:** reordered three times, for a non-Exception BaseException nothing in the tree raises.
   - **UART PieceBuffer catches:** they led to driven-clock harness work for the twin link.
7. **Per-episode logging flags** (config store, NTP, BMP3XX). They also stop the console line on repeats, which goes
   against OR35.a ("Console logs actually should keep printing all"), and against OR35.b's "no per-module or
   per-episode special cases".
8. **Unreachable checks:**
   - typed getters that validate the stored value's exact type;
   - typing-only guards (6 in group C);
   - 16 buildgen checks no TOML can trip;
   - a compile check of generated text that ruff, mypy and every test already compile.

   These go against your 2026-10-27 rule on checks that typing alone already covers.
9. **Real output changed with no decision.** The wet-bulb value is refused in Stull's cold-dry corner (below 10 °C).
   Legacy accepts it, and no owner text names it. That breaks D.1 ("flag and ask before altering real output").
   It is implausible on these indoor units anyway.

## 5. Owner-decided changes, and where they could be smaller

Most R rows are "as landed". The scans named smaller forms for some:

| change | as landed | smaller form | what you'd lose |
|---|---|---|---|
| I2C clear | a 31-line copy of the boot clear | one clock-out routine for both | nothing |
| I2C short-ACK write path | ~35 lines | ~4 lines | nothing |
| recovery ladder | ~75 lines | ~55 lines, without the cross-reader bus marks | two readers on one bus both clear it |
| PieceBuffer | as landed | ~25 lines fewer, without `read_at()`/`trim()` (they serve only dev's echo) | nothing |
| measured uptime (`TickSeconds`) | 29 lines | ~12 lines for SysUptime alone | Wi-Fi and NTP keep counting ticks |
| overlapping error resets | 29 resets in flight, bit sets | one at a time | concurrent resets |

## 6. Points that need your decision

1. **The review page.** The audit put 364 agent-written decisions on a review page. You answered 69: 45 "ok", 18
   "ask", 5 "change", 1 "withheld". Under the scan rules an "ok" counts as your decision, so those rows are R.
   - Several of them rest on hypothetical premises. The clearest is the C-stack reboot, whose "why" reads "today a
     broad handler can swallow it". Behind it are the ~120 `report_if_fatal()` call sites.
   - Do the 45 "ok" ticks stand as decisions, or are they re-opened under your no-hypotheticals rule? This decides how
     much of section 4 can go.
2. **Wi-Fi for a unit nobody configures.**
   - Before the audit, as in legacy, such a unit switches Wi-Fi off after its first hotspot window, until a power
     cycle. An agent changed that.
   - Your OR151 ("Entering the hotspot mode only through a reboot, as is.") reads as keeping the old behaviour.
3. **The NeoPixel overlay.** The revert to the pre-audit wait is the minimal change.
4. **Website features with no recorded agreement.** The page that reloads itself after a reflash, in-place updates
   and bounded polling do have your "ok" (review item "A website left open for days stays healthy and reloads itself
   after a reflash"). With no agreement found:
   - the `#section` Back history;
   - the Device Clock row, with `UnixTime` added to every `/status`;
   - code-button tones;
   - the section-switch wait;
   - the non-object banner.
5. **The target state**, which is the main decision. Per module: the pre-audit code, plus the section 3 fixes, plus your
   decided features in their smallest form. That means removing most of section 4.
   - Removing whole added mechanisms means going back to the pre-audit code with those mechanisms taken out, not
     patching on top of the current code.
   - I'll put forward an approach for that once you've decided the points above. Nothing starts before your go-ahead.

## 7. Hardware-round list (only the board can settle these)

1. C-stack depth along the 28-level await chain. This decides the C-stack escalation.
2. The FRAM SPI line's level with the chip absent. This decides the lost-chip chain.
3. I2C register-byte and data-byte NACK rates of the BMP3XX, ISL29125 and SCD30 on the dev buses.
4. SGP40 read errors right after boot (the restore cycle).
5. Config floats through `json` on rp2's single-precision build.
6. Whether 8 or more soft callbacks queue at once, for example after a long flash write.
7. A heap-exhaustion error's message with and without the emergency buffer.
8. The Wi-Fi country code against an access point on channel 13.
9. Whether a WS2812 loses its state under Wi-Fi bursts. This is the NeoPixel rewrite's premise.
10. The lwIP listener-close check on silicon (prepared).
11. Already owed by your own rows: the UART DMA ring proof, reset reasons 21, 22 and 10+phase, the first unfed
    watchdog stretch, and dev's receive-ring peak.
12. Optional: a DNS flood at dev's hotspot, and the heap in hotspot mode with a phone probing.

## 8. The rules violated most often

| rule | A | B | C | D |
|---|---|---|---|---|
| nothing built on a hypothetical | 25 | 40 | 38 | 23 |
| cascades a red flag | 23 | 10 | (in HYP) | 4 |
| really minimal change | 11 | 42 | 8 | 1 |
| hardcoded delay checks | 1 | 5 | 4 | 3 build-time |
| same top-level features (CLAUDE.md:508) | — | 5 | 1 | 1 |
| P4 nothing in the product for tests | 3 | 1 | 1 | 1 |
| D.1 flag, don't silently change | 1 | 3 | — | — |
| checks that typing already covers (your 2026-10-27 rule) | 1 | 1 | 6 | — |
| OR35 logging rules | 1 | — | 2 | — |
| allocation cuts for temporaries you had accepted (OR110) | — | — | 7 | — |

## 9. Tests and tooling

The eight test and tool areas went from 105,942 to 232,891 lines (2.2×), and from 328 to 655 files.

**What the growth is:**

| class | lines |
|---|---|
| tests that pin firmware, buildgen or website behaviour | +73.3 k |
| harness: fakes, runners, driven clocks, and their own tests | +44.0 k |
| audit machinery and convention gates | +6.0 k |
| CI | +1.6 k |

About 30 k of those lines are tests whose subject is a tool, not the firmware.

**What it costs:**
- CI's unit-tier timeouts went from 45 to 175 minutes, for a warm run of 9-10 minutes.
- The twin end-to-end matrix went from 6 to 24 jobs.
- The hang rule holds in letter only: a hung job can run about 128 minutes before it fails.

**Where it breaks your rules:**
- **"No deep dives":** some test files are up to 11× their module. There were campaigns to cover every uncovered line
  and every audit-table cell, and 100 self-bite tests that test the tests.
- **P8 (one source, generated not copied):** the port lock and the summary block exist in sh, Python and JS, with tests
  keeping the copies equal. There are also two separate board fakes.
- **No P4 or P9 break was found**, the host-wear rule included.

**Runaway areas:**
- the driven-clock and per-wiring widening (30 commits, no product line);
- the bench log check, refitted over 11 lanes for bench tests that have never run on silicon;
- port isolation (a lock in three languages, port bands, loopback addresses);
- the runner reporting;
- the `@tunable` tagging (1,249 tags, from 0);
- the coverage machinery;
- the repo-scan reader;
- the twin-record (~2,260 lines that record whether each hardware instrument had a twin run).

## 10. Docs and repo

**Docs:** the permanent docs went from 13,962 to 21,393 lines (+53 %), and from 1.1 to 2.3 MB (+108 %).
SPECIFICATION.md went from 514 to 1,573 KB.

**The register in SPECIFICATION.md** (Part N, the tunable parameters) is 562 KB, 47 % of all doc growth:
- of its ~1,284 rows, 1,127 are test, CI or runner values;
- 1,063 cells read "measurement owed".

**Classes of the added lines:**

| class | share | what it is |
|---|---|---|
| knowledge | ~87 % | about half of it documents the test/CI machinery; ~930 SPEC lines restate code |
| history | ~8.5 % | BACKLOG's 447-line chroot list, the pass narratives |
| audit-process text | ~3 % | owner Q&A quotes and "decided on the owner's behalf" text, also in the end-user DEVICE_REFERENCE.md |
| duplication | ~1 % | literal duplication, the floor |

**Provenance tags:** SPEC's owner/agent tags went from a few dozen to about 1,600-1,800, depending on the pattern.

**Repo:**
- `audit/` is 14,052 files and 127 MB in the tree, about 53 MB packed in the history: 85 MB of evidence logs in 13,142
  files, 39 MB of records, 47 scripts. Nothing outside it depends on it.
- Before it goes:
  - move the Stull 2011 paper (`audit/refs/`, the source of the wet-bulb domain in `src/math_helpers.py`) to the
    datasheets;
  - carry the open findings into BACKLOG;
  - check that the do-not-reopen decisions stand at their doc sites.
- **Other clutter:**
  - the tracked, generated `tests_hardware/twin_record.json`;
  - README's stale "execution blocked" text;
  - 603 lines of old pass narratives in `tests_hardware/README.md`.

## 11. The audit's course

**Totals:** 981 commits plus 84 merges. About 80 % of all touched lines are audit apparatus.

**Phase A (planning):** 611 commits and 831 k audit lines, with no product line, including a 129 k-line work order.

**Work units U0-U8 (owner rows):** lean, +46 `src/` lines, as you expected.

**Units U9-U34:** the firmware growth.
- Ten units hold 91 % of the new `src/` lines: core, bus layers, drivers, FRAM, UART, network, REST, buildgen, the
  memory ladder, and the U35 preliminary. It is hardening, not features.
- From U18 on, each unit committed 24-155 k lines of evidence logs.
- From U23 on, test volume ran ahead of the code: 0-74 `src/` lines per unit against 107 k test lines.

**The U35 redo:** 94 hand-backs, 233 commits and 67 merges in 34.5 hours.
- **Net:** +40 `src/` lines, against +9.7 k test lines and +21 k audit lines.
- **Real fixes:**
  - the lwIP listener guard;
  - the UDP lost cancel (a defect the audit itself had introduced);
  - the I2C recovery step run twice (also in the audit's own ladder);
  - the removal of typing-only checks (−35 lines);
  - the contrast fix;
  - the NTP cadence, once its own regression is netted out.
- **Runaway chains:** 11 of them. The largest:
  - the bench log check (12 lanes, never run on silicon);
  - the per-wiring twin tests and their cost (15 lanes);
  - the test-wait tagging (7 lanes, after 172 earlier actions on the same thing);
  - the records walks (20 lanes, about 35 k audit lines, 20 commits that only re-render records keyed on line numbers);
  - the NeoPixel cascade.
- **Investigations that delivered knowledge, rightly with no code:**
  - no heap leak (the 147 KB per-boot step);
  - one cancel path with no defect;
  - 666 tick-wrap runs, all green, confirming an earlier proof;
  - a Unix-port poll fidelity gap.

## 12. What I checked, and corrections

**Checked against git and the logs:**
- **Counts:** commit counts; `src/` and buildgen line counts at both ends; two units' deltas; the redo's `src/`
  diff; CI timeouts.
- **Code at the pre-audit commit:** the pre-audit ISL29125 code; the pre-audit `json.dump()` sites; the pre-audit NTP
  checks (no zero-timestamp test); the pre-audit core-module list; the 26 "bus not initialized" sites.
- **Reproduction logs:** groups A, B, C and D.
- **Docs and repo:** SPEC's and Part N's sizes; `audit/`'s size; the Stull reference; `@tunable` and `UnixTime`; the
  "decided on the owner's behalf" text; the OR35.a and OR151 quotes.

**Corrections and deviations:**
- **The C-stack escalation.** Group A classed it hypothetical; it has your review-page "ok" (2026-10-01). Group A did
  not consult the review answers, so other group A rows may carry an "ok" too.
- **Website features.** Group E listed the auto-reload among those with no owner agreement; it has your "ok".
- **Group A's K class** holds its confirmed hypotheticals, not the brief's meaning. They are listed in section 3.
- **One runs-ledger gap.** Two of group A's reproductions share one start line, so "one run at a time" isn't shown for
  that pair; each log holds its three runs.
- **Line counts** differ in method between groups: net, blame-attributed or approximate. Treat the sums as orders of
  magnitude.

**State:**
- Nothing is running.
- The paused lanes stay paused: four with work in their worktrees, three queued.
- Nothing will be implemented before your decisions and an explicit go-ahead.
