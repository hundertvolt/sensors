# Real-hardware handover — measure B on silicon (the boot-confined placement reset)

Temporary file, same convention as every handover before it: **delete once its results are migrated**
into `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7F, `SPECIFICATION.md` and `REAL_HARDWARE_TEST_QUEUE.md`.
Written 2026-09-18 by the PR #105 session, which had **no** real-hardware go-ahead — every figure
below was [TWIN] or [SRC] when written.

> **RUN, PARTIALLY, 2026-09-18 by a session that did have the go-ahead. Results:
> `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7F.** The headline (P1) is settled: the tripwire **passes
> in-suite on A + B**, having failed on every image ever measured. P3 and P4 confirmed, P2 untested
> (§7F.4), P5 owed. **Two defects in this file's own protocol were found by following it — §4.1's
> build check and §4.3's saturation check are both broken; see the boxed notes in each, and §7F.5.**
> Do not re-run from scratch: §7F.6 lists what is still owed.
>
> **Amended 2026-09-19, host-side, with no hardware.** Two of that run's own readings did not mean
> what they said: the `..._production_threshold` row was a **probe artefact** and is withdrawn
> (§7F.8), and `after_starter_list` is a **run-phase** reading taken ~3 s past the position P2 is
> about (§7F.9). `heap_layout_after_full_boot_sequence.py` now reports `retained=` on every line and
> a new `after_starter_loop_end`, and both scripts take a control reading before switching the
> threshold. What is owed is **two invocations of one script**, one per arm, right after each arm's
> suite run — queue row B6.

**Nothing in this file authorizes anything.** CLAUDE.md's gate stands: the session that runs this
needs the project owner's go-ahead **in its own conversation**, and a go-ahead given to this session
or to the 2026-09-18 bench session does not carry over. `tests_hardware/README.md` stays the
technical reference for prerequisites, flags and safety facts.

Provenance: **[HW]** measured on the real `dev` board (2026-09-18 bench session), **[TWIN]** measured
host-side on the settrace-free frozen Unix port, **[SRC]** read from this repo's code.

---

## 0. Why this run exists

Measure A has been measured on silicon (§7D) — it buys **+40.2 %** of in-suite largest obtainable
block, 20,592 → 28,864 B [HW]. Measure B has not. It is built, tested, green in CI and green in the
twin, and the twin puts A + B at **6.1x the base layout after `build_system()` and 10.6x by the end of the task
starter list** on this metric — while A alone is worth nothing on it:

| arm | after `build_system()`, 508k | end of the starter list, 560k |
|---|---|---|
| base — neither measure | 14.2 % | 8.4 % |
| A alone | 12.4 % | 7.4 % |
| B alone | 45.0 % | 57.8 % |
| **A + B, as shipped** | **86.3 %** | **88.7 %** |

All [TWIN] (§7E). **Both columns name a moment during boot, not "after boot"** — the right-hand one
stops where the starter list stops. That distinction was implicit when this table was written and
turned out to matter: the run phase takes most of the gain back within ~2 s (§7F.9). The board's own
A-only in-suite reading is **28,864 / 105,216 = 27.4 %** [HW] —
already more than twice the twin's A-only 12.4 %, because the twin measured a cold process and the
board measured an aged one (§7D.2). **So the twin's ratios are not a numeric prediction for the
board.** They are a direction and a mechanism, and this run is what turns them into evidence or
refutes them — exactly as §7D.4 refuted the twin's "A buys no layout gain" in the other direction.

**The one sentence that makes this run worth a bench slot.** The tripwire
(`test_real_gc_heap_headroom_survives_a_full_system_build`, floor 80,000 B *as it then stood* — that
floor was retired by the owner on 2026-09-19, MEASUREMENTS §7G) has **failed in-suite on
every image ever measured** — 20,592 B before A, 28,864 B after A. If B transfers at anything like
the twin's magnitude, this is the image where **it passes in-suite for the first time**. If it stays
under ~40,000 B, §7E is twin-only and says nothing about silicon.

---

## 1. What is already answered, so it is not re-run

- **A's layout gain, functional conformance, hold times, boot cost and error logs** — all [HW],
  2026-09-18, `REAL_HARDWARE_TEST_QUEUE.md` §1A rows A0–A9 and §7D. Do not repeat A0–A9.
- **The position-dependence trap** (§7D.2, queue finding F3): `Board.run_isolated()` interrupts the
  already-running firmware **without resetting**, so a device script builds inside `main.py`'s aged
  heap. Same firmware, same board, same sitting: standalone `largest_block=95,104`, in-suite
  `28,864`, with `free`/`alloc` identical to 0.2 %. **Only like suite positions are comparable.**
  This is the single most important methodological fact in this file.
- **A+B in the twin** — §7E, including the `basex` instrument fault (§7E.3) that this run's new
  script exists to avoid repeating.

---

## 2. The instrument, and why the existing one is not enough

`heap_headroom_after_full_system_build.py` calls `build_system()` and stops [SRC]. That reaches
**measure B's first site only** — the 11 `gc.collect()`s `buildgen` emits into the setup batch. It
never reaches the second site, the 23 in `SystemService.start_and_check_tasks()`'s starter loop.

The twin says both sites are load-bearing, and in different ways:

- The **batch** collects *create* the good layout: after `build_system()`, 14.2 % → 86.3 %.
- The **starter-list** collects *preserve* it: with the batch collects but not the starter ones, the
  whole-sequence figure falls back to **10.1 %** (§7E.3). The starter list destroys what the batch
  built unless it collects too.

So two readings are needed, and the existing script can only take the first.

**New script, added by this handover and validated host-side:**
`tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py`.

It runs `main()`'s own sequence — `build_system()`, `_collect_task_starters()`,
`start_timers(timer_starters)`, then `start_and_check_tasks(task_starters)` as a task, settling 4 s
so the starter loop (1.0 s in total, whatever the count) and a supervisor pass or two complete —
and reports `free`/`alloc`/`largest_block`/`pct` at four labelled points plus a `BOOT` timing line.
Identical probe bounds to the existing script, deliberately, so the two scripts' `largest_block`
figures are comparable.

**What it deliberately omits:** `ntp.ntp_force_sync()`, which sits between the two lists in the real
`main()`. It needs a reachable NTP server, and a network-dependent wait in the middle would put the
measurement at the mercy of the bench LAN. It allocates in that gap either way — stated, not
measured. The real firmware therefore has a third boot stretch with no collect in it; that is a known
design choice (widening B would widen `SPECIFICATION.md` I.4's exception), not an oversight.

**No floor is asserted.** No reading for this position exists on silicon yet, so any threshold would
be invented rather than measured. The figure is the deliverable; `RESULT: PASS` means only that the
script completed.

**Validation done host-side, no hardware** [TWIN]: run against the twin's fakes at
`-X heapsize=16M` and `2M`, it completes and reports all four points, `starters=22 timers=8`
(so 23 starter-loop collects, matching §7E's count [SRC]); at `1M` it fails honestly with
`RESULT: FAIL build_system() raised ... MemoryError` rather than hanging. `ruff` clean;
`scripts/typecheck.sh` clean with it in scope (158 files, up from 157).

**Not wired into a pytest test, on purpose.** It starts the real task graph, so running it mid-suite
could disturb later tests. §3 gets its in-suite position a different way, with its own validity
check.

---

## 3. Decide before the run

| # | Decision | Recommendation |
|---|---|---|
| B-D1 | **One firmware image or two?** The matched pair needs two build+flash cycles. | **Two.** See §4 for how to build the BEFORE arm; §4.4 has the one-image fallback and says why it is weaker. |
| B-D2 | **`--allow-persistence-writes`?** | **Not needed for anything in this file.** FRAM is outside the wear gate, and no row here owns a flash-filesystem write. Leave it off unless the sitting is also picking up queue rows R1/R4/R5/R8. |
| B-D3 | **Run the F1 SSID script (§6.2)?** It is the script that stranded the bench on 2026-09-18. | **Optional, and skipping it is a legitimate choice.** If run: last in order, with §6.2's recovery recipe open. |
| B-D4 | **Which device?** | `dev`, built from this branch's own tip via `scripts/build_firmware.py dev`. CLAUDE.md's hard rule: a `wozi` build on the dev bench tests nothing at all and has produced false bugs before. |

**Before anything else:** read `GET /status`'s `errcount` and write it down. The FRAM-persisted
per-module logs are the one piece of diagnostic evidence a reboot does not erase, and `ResetErrors`
destroys them irreversibly (CLAUDE.md). Also note what has already been run against the board — an
isolated-driver script builds its own `AsyFramManager` over the same chip and can leave a
plausible-looking fabricated entry behind (`tests_hardware/README.md`).

---

## 4. The protocol

### 4.1 Build the two images

Measure B's source changes are confined to **two** files [SRC], both touched only by `7ccbe8d`:
`src/system_service.py` (the starter-loop collects) and `buildgen/codegen.py` (the emitted batch
collects). So the BEFORE arm is **this branch's tip with exactly those two files checked out at
`da9bcf1`** (= `7ccbe8d^`) — the same isolation technique §7D.1 used for A, which keeps unrelated
merge differences out of the comparison.

```bash
git checkout claude/heap-fragmentation-remediation   # AFTER arm = the tip = A + B

# --- BEFORE arm (A only) ---
git checkout da9bcf1 -- src/system_service.py buildgen/codegen.py
scripts/build_firmware.py dev          # regenerates sensortask_dev.py from the OLD codegen
# flash, run §4.2 and §4.3, record

# --- back to the AFTER arm ---
git checkout HEAD -- src/system_service.py buildgen/codegen.py
scripts/build_firmware.py dev
# flash, run §4.2 and §4.3, record
```

> **DEFECT, found 2026-09-18 by running it.** The `grep -c` commands below **do not work**.
> `build/generated_src/` is written by `scripts/_generate_sensortask_modules.py`, not by
> `scripts/build_firmware.py`, which generates into a `tempfile.TemporaryDirectory()`. The copy
> there predates measure B, so the check reports **0 on a correct AFTER build** — indistinguishable
> from the stale-module failure it exists to catch. The `.uf2` size comparison is inert too: both
> images are exactly 2,238,464 bytes. **Use instead:** call `generate_device()` directly and count
> `gc.collect()` in its `module_source` (AFTER 11 / BEFORE 0), `grep -c` on `src/system_service.py`
> (AFTER 2 / BEFORE 0), and `md5sum` on the two images (they differ in 523,556 bytes).

**`buildgen/codegen.py` is a build-time file — the BEFORE image is only correct if the module is
regenerated after reverting it.** `scripts/build_firmware.py` calls `generate_device()` on every
invocation [SRC], so a plain rebuild does it; a stale `build/generated_src/` copied in by hand would
give an image with B's batch collects frozen in and B's starter collects absent, which measures
nothing. Confirm before flashing:

```bash
grep -c "gc.collect()" build/generated_src/sensortask_dev.py   # AFTER: 11   BEFORE: 0
grep -c "gc.collect()" src/system_service.py                   # AFTER: 2    BEFORE: 0
```

Independent evidence the two images really differ, the same check §7D.1 used: compare the two
`.uf2` sizes and the device script's own `baseline` heap line.

### 4.2 Reading 1 — after `build_system()`, in-suite (the tripwire)

```bash
scripts/run_flash_hardware_suite.sh
```

Read the `HEAP after_build_system: free=… alloc=… largest_block=…` line and the `RESULT:` line from
`test_real_gc_heap_headroom_survives_a_full_system_build`. This is T.1's A+B column, and the suite
position is identical across arms by construction — which is what made §7D.3's pair trustworthy.

The whole suite is also the T.2/T.3 re-run and the §6.1 verification, so it is not a detour.

### 4.3 Reading 2 — after the whole boot sequence

**Immediately after the suite finishes, without resetting the board:**

```bash
scripts/mpremote_connect.sh exec "import machine; machine.WDT(timeout=8000)" \
    run tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py
```

The `WDT(timeout=8000)` re-arm is what `Board.run_isolated()` does first [SRC]; without it the
script's own runtime can starve the watchdog. Do **not** append `soft-reset` — a reset would discard
the aged heap this reading depends on.

> **DEFECT, found 2026-09-18 by running it.** The re-run check below **cannot work**. This script
> strands `main.py` and leaves `WDT(timeout=8000)` armed, so the board resets ~8 s after it ends and
> the second run always measures a **fresh** heap, never the aged one. Observed: run 1 (genuinely
> aged, right after the suite) `after_starter_list` = **10,128 B / 10%**; run 2 a minute later
> **66,144 B / 70%** with a fresh `baseline`. The disagreement is the reset. A real check must leave
> `main.py` running between readings.
>
> **Amended 2026-09-18 (PR #105 session): the defect breaks the *check*, not the *reading*.** Run 1
> above is a valid aged reading, taken exactly as §4.3 says, and it is the worst layout figure this
> project has measured on silicon. So an aged AFTER reading — the one thing P2 turns on — costs **one
> invocation at the end of the next suite run**, not a method redesign; nothing has to survive
> between readings to obtain it. What is lost is only the evidence that "right after the suite" is a
> sound stand-in for "in the suite". **Use this instead of the re-run**: take one reading after the
> flash suite and one after the bench suite, each immediately following its own run. Those age the
> heap by different amounts, so agreement is the saturation evidence the re-run was meant to give,
> and neither reading needs the board to survive the other. It is the same argument §7D.3 already
> made for the tripwire, which read 28,864 B from both suites.

**Validity check, replacing the broken re-run.** §7D.3 read a byte-identical 28,864 B from both the
flash and the bench suite, which suggests the ageing effect saturates. Confirm that rather than
assume it by taking **one reading after the flash suite and one after the bench suite**, each
immediately after its own run. If they agree, the position has saturated and "right after the suite"
is a sound stand-in for "in the suite". **If they disagree materially, say so and treat every number
in §5 as position-confounded** — that is a finding about the method, and more valuable than a number
taken on a false assumption.

**The script changed on 2026-09-19 and now prints three things it did not.** All are free; nothing
in the invocation changes.
- **`after_starter_loop_end`** — a reading taken where the starter loop actually ends, detected by
  counting starters rather than waiting a guessed interval. **This, not `after_starter_list`, is the
  line P2 is about**: the twin puts most of measure B's gain back within ~2 s of the run phase
  starting, while `after_starter_list` sits a few seconds past the loop, on the far side of that
  decay (MEASUREMENTS §7F.9). It keeps its name and a 4 s settle — now timed from the loop's end
  rather than the supervisor's creation, so ~1 s later than §5's rows, which that same decay makes
  immaterial. `BOOT`'s new `starter_loop_ms` / `settle_ms` split puts the position on the line.
- **`retained=` on every `HEAP` line**, and a `_retryN` line when it is non-zero. The probe can pin
  its own buffer and then report `_PROBE_MAX >> k` — which is where §5's withdrawn 49,152 B row came
  from (MEASUREMENTS §7F.8). A non-zero `retained` on a *retry* line is the only case worth
  reporting; the retry itself is automatic.
- **`after_starter_list_control`**, a second reading at the *unchanged* threshold, taken before
  `gc.threshold(32768)` is set. Without it a difference in the threshold line cannot be told from a
  difference between two probe runs, which is exactly how the 49,152 B row was misread.

### 4.4 Reading 3 — the threshold question (§7D.8's second open item)

Both scripts read at MicroPython's reactive default and set `gc.threshold(32768)` only afterwards
[SRC], so neither has ever measured the firmware's own boot path **under its own threshold from the
start** — which is what `main.py` does. One extra invocation settles it, because the threshold is a
VM-global that persists across commands within a single `mpremote` call:

```bash
scripts/mpremote_connect.sh exec "import machine; machine.WDT(timeout=8000)" \
    exec "import gc; gc.threshold(32768)" \
    run tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py
```

This matters beyond bookkeeping: the twin shows **no layout defect at all** at `threshold(32768)`
(85–97 % kept at every churn dose), while the board's cited symptom is the `threshold(-1)` shape on a
board whose own entry sets 32768. One of those two things is wrong, and this is the reading that says
which.

**One-image fallback (B-D1 = one).** The tip alone still yields three real results: §5's P3 internal
control, the after-`build_system()` vs after-starter-list comparison within one arm, and a comparison
against §7D.3's already-recorded 28,864 B. Treat the last as **weaker evidence, and say so in the
write-up** — the base branch has moved since that reading (the merge at `b7dd34e`), so the delta
would carry more than B. Queue decision D4's warning against reusing an old reading as a "before"
arm applies.

---

## 5. What to record, and the predictions to read it against

Fill both arms in. Every cell is a number off a `HEAP`/`BOOT`/`RESULT` line — nothing here needs
interpretation at the bench.

**Filled in 2026-09-18 [HW].** Full analysis in `HEAP_FRAGMENTATION_MEASUREMENTS.md` §7F.

| reading | BEFORE (A only) | AFTER (A + B) |
|---|---|---|
| `after_build_system` free / largest / pct, in-suite (§4.2) | 105,088 / **28,736** / 27% | **not captured** — see §7F.6 |
| tripwire `RESULT:` (floor 80,000 B, since retired — §7G) | **FAIL** | **PASS** (suite: 36 passed, 0 failed) |
| `after_build_system` free / largest / pct (§4.3 script, fresh heap) | 104,192 / 93,728 / 89% | 104,128 / 90,720 / 87% |
| `after_start_timers` free / largest / pct | 101,760 / 93,728 / 92% | 101,696 / 90,720 / 89% |
| `after_starter_loop_end` free / largest / pct | **owed** — the line P2 turns on, added 2026-09-19 | **owed** |
| `after_starter_list` free / largest / pct (~3 s into the run phase) | 93,632 / 66,144 / 70% | 94,272 / 57,424 / 60% |
| ~~`after_starter_list_production_threshold`~~ | ~~93,632 / 49,152 / 52%~~ | ~~94,272 / 49,152 / 52%~~ **withdrawn — probe artefact, §7F.8** |
| §4.3 re-run five minutes later — same or different? | **check is broken** — see the §4.3 note; genuinely-aged run gave 10,128 / 10% | not taken |
| §4.4 threshold-first `after_starter_list` | 94,928 / **75,536 / 79%** | **owed** |
| `BOOT build_system_ms / start_timers_ms` | 943-951 / 789-790 | **1,402** / 789 |
| `LISTS starters= timers=` | starters=22 timers=8 | starters=22 timers=8 |
| `GET /status` `errcount` before / after | NTP 11, SYSTEM 1 (W4), rest 0 | after-read **owed** (P5) |

**Verdicts: P1 confirmed. P3 confirmed. P4 confirmed. F2 confirmed fixed on silicon (both
injectors pass on both arms). P2 untested — the fresh-heap column above will read as "B is harmful"
if taken at face value, and it is not: both its arms are run-phase readings taken seconds past the
position P2 is about (§7F.9), and the reading that can test it did not exist when this run was made.
It does now. P5 owed.**

### The predictions, each with its falsifier

- **P1 — the tripwire passes in-suite on the AFTER arm.** Twin: 12.4 % → 86.3 % after
  `build_system()`. On the board that would take 28,864 B to well above the 80,000 B floor.
  **Falsified if** the AFTER in-suite reading stays under ~40,000 B: B's twin effect does not transfer
  to silicon, and §7E is a twin-only result. That is the same class of correction §7D.4 applied to A,
  in the opposite direction, and it must be written up as plainly.
- **P2 — restated 2026-09-19, because the line it named was the wrong one.** The claim is that the
  starter-list collects *preserve* what the batch collects built, and the reading that shows it is
  **`after_starter_loop_end`**, not `after_starter_list` (which sits seconds into the run phase — §7F.9).
  On the twin, at the loop's end, A + B holds **20 / 50 / 59 %** across three heap sizes against
  A-only's **6 / 5 / 11 %**; read at the old position both arms have already decayed to single
  digits. **The prediction:** on the AFTER arm `after_starter_loop_end` keeps most of
  `after_build_system`'s figure — on a fresh heap that is ~90,000 B staying above ~50,000 B, and at
  the aged position it is the ratio that matters, not the byte count. **Falsified if** the AFTER
  arm's loop-end reading is no better than the BEFORE arm's at the same position: the second site is
  not doing its job on real timing, and B is half a measure. A drop between the loop end and the 4 s
  settle is **not** a falsifier — that is the run phase, and the twin predicts it on both arms.
- **P3 — the internal control, and it needs no second image.** On the **BEFORE** arm,
  after-starter-list must be **worse** than after-`build_system()` (twin base: 14.2 % → 8.4 %) —
  the starter list scatters survivors when nothing resets placement. **If P3 does not hold, the
  instrument is not seeing the starter list at all** and P1/P2 mean nothing. Check this first.
- **P4 — boot cost rises by tens of milliseconds, not seconds.** A-only `build_system()` is a median
  **919 ms** [HW] (§7D.7) against the 8,388 ms watchdog cap; B adds 11 collects there and 23 in the
  starter loop. **Falsified if** `build_system_ms` exceeds ~2,000 ms — then a collect on this heap
  costs far more than assumed, which is a finding about the RP2040's collector, not about B. Boot
  latency itself is explicitly not an optimisation target (CLAUDE.md WP6); this is a watchdog-margin
  check and nothing more.
- **P5 — `errcount` stays clean**, as it did for A (§1A row A8: no errno 90/91/92/93/99/100, no wrnno
  81/82/84). B changes allocation placement, not the FRAM path.

---

## 6. Three fixes in this branch that have never run on silicon

All three are host-side code this session wrote after the 2026-09-18 bench run reported them. They
live in `tests_hardware/`, which `mpremote run` pushes **from the working tree** at run time rather
than freezing into the image [SRC] — so both arms exercise the fixed versions automatically, and a
failure is about the fix, not the firmware.

### 6.1 The two FRAM fault injectors (queue finding F2) — covered by §4.2's suite run

`test_fram_cs_pin_hijack_fault_injection_and_recovery` and
`test_fram_hard_reset_race_during_write_and_recovery` both **failed on the A arm** on 2026-09-18 and
passed before A: their technique raced an `await asyncio.sleep(0)` into the CS window, which A made
non-yielding. Both now inject **deterministically at the driver's own synchronous transfer seam**,
wrapping `write_sync`/`readinto_sync` so the CS deassertion — or the `machine.reset()` — lands
immediately before the payload reaches the chip.

**Expect both to PASS on both arms.** The CS-hijack script now also proves the injection landed, by
reading the CS pin back at injection time; if it reports *"CS was never observed asserted at the
payload transfer - nothing was injected, so nothing was tested"*, that is the script telling you it
covered nothing — **not** a driver fault, and the distinction is exactly what the old flag could not
make.

**What only silicon can confirm:** that the hijacked payload is actually *refused* by the chip. The
twin's fake chip ignores CS, so host-side validation can only show the injection fires with CS
asserted and that the driver is usable afterwards.

### 6.2 `wifi_service_reconnect_repro.py` (queue finding F1) — optional, B-D3

This is the script that **stranded the bench** on 2026-09-18: it overwrote the DUT's persisted SSID
via the real `_set_dict_cfg()` path, then died on the reset before restoring, and recovery took a
serial-REPL session. Both halves were wrong — `REAL_SSID` was hardcoded to `"sensors-bench-ap"`
while the bench's own is `sensors-bench-fa9707`, so the restore would have written a *second* wrong
SSID had it run at all.

It now reads the live value through `_get_dict_cfg()` first, **aborts rather than overwriting** if it
cannot read it back, and restores in a `finally` that re-reads instead of trusting a flag. The
snapshot carries the real password, so it is never logged.

**Before running it:** write the board's current SSID down by hand, and have this ready —

```bash
# Recovery if the board goes unreachable with a garbage SSID (this is what worked on 2026-09-18):
scripts/mpremote_connect.sh exec "..."   # write the real SSID back into config_WIFI.cfg
scripts/mpremote_connect.sh reset
```

Per R10 it likely needs `run_isolated_expect_reset()` — the board drops USB CDC mid-run and a plain
`run_isolated()` ends in `OSError: [Errno 5]`. Run it **last**, after every measurement above is
recorded, so a stranding costs no data.

### 6.3 The marker question F1 opened — **owner's call, not the bench's**

The SSID write is test-owned and would qualify for `@pytest.mark.persistence_write`, but this is a
`device_scripts/` diagnostic invoked directly rather than a pytest test, so no marker can gate it —
and `tests_scripts/test_persistence_write_marker_completeness.py` structurally cannot catch it
(it pins pytest tests, and explicitly excludes `device_scripts/` [SRC]). Whether that needs a
different mechanism is a design decision. Do not invent one at the bench.

---

## 7. Hazards specific to this run

- **§4.3's script starts the real task graph.** `mpremote run` interrupts `main.py` into the raw REPL
  and the entry's own `finally: asyncio.new_event_loop()` clears the task queue [SRC], so the
  script's tasks are the only ones executing — but its WiFi and webserver starters re-init
  peripherals the interrupted firmware had already claimed. The webserver binds **8080**, not 80, to
  stay clear. Same hazard class as the existing `build_system()` script, which has run repeatedly;
  a wedged board recovers with `mpremote reset`, and nothing here persists anything.
- **Do not append `soft-reset` to §4.3's or §4.4's command.** The aged heap *is* the measurement.
- **`fram_*.py` device scripts overwrite production's first FRAM chunks**, because the allocator is
  deterministic and an isolated script's first chunk is production's first chunk. Expect
  NTP/SYSTEM/UART counters to read 0 afterwards — that is the documented hazard, observed live on
  2026-09-18, not a new finding.
- **Don't chase `asy_fram_manager.py`/`asy_fram_driver.py` internals** from anything found here. A
  failure in the FRAM path is a finding *about* measure A's scoped exception and belongs back to the
  PR #105 session — never a drive-by fix at the bench (SPECIFICATION.md C.3.1).
- **Two build+flash cycles spend two real flash writes.** Accepted for A's pair on 2026-09-18 on the
  same reasoning; noted so it is a knowing choice, not an oversight.

---

## 8. Not in scope

- **Everything in `REAL_HARDWARE_TEST_QUEUE.md` §2 (R1–R13), §3 (C1–C7) and §4 (H1–H3).** Independent
  of measure B. H1 — the two-chroot check on the Pi4 — is worth the sitting if the host is free, and
  is now an **owner-run periodic check rather than a per-push gate** (owner decision, 2026-09-18);
  the branch's `scripts/lint.sh` change is what it would cover.
- **Plan sections C and D.** C is the seam + contiguity guard, the thing that restores the tripwire's
  sensitivity once B dampens it; neither has the owner's go-ahead, and C could change what a
  contiguity figure even means. Measure B is what this run is for.
- **The run phase over months of uptime** (§7A.7, §7D.8). Still untouched. §7D.5's UART result is the
  only real-hardware evidence either measure helps there.
- **Re-fitting the tripwire to a board reading.** The 80,000 B floor was **retired by the owner on
  2026-09-19** and replaced by three requirement-derived checks (MEASUREMENTS §7G), each derived
  from §7A.9's measured worst reachable allocation. Raising or lowering one of those to make a
  reading pass is the thing the old floor did wrong; it is not this run's to do.

---

## 9. When the run is done

1. Fill §5's table in, in this file, and leave the falsified/held verdict next to each prediction.
2. Migrate into `HEAP_FRAGMENTATION_MEASUREMENTS.md` as **§7F**, marked [HW], with the same
   "confirms / corrects" structure §7D.4 uses — including anything that contradicts §7E, which is the
   most valuable thing this run can produce.
3. Tick `HEAP_REMEDIATION_PLAN.md` T.1 (the A+B column) and T.5 (B's boot cost).
4. Update `REAL_HARDWARE_TEST_QUEUE.md` §1B's pointer row, and close F1/F2's "unverified on silicon"
   caveats with the result.
5. Delete this file once 2–4 are done.
