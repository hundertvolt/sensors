# Heap fragmentation — confirmed measurements and findings

The measured evidence base for the heap-fragmentation defect, built on branch
`claude/heap-fragmentation-remediation` (PR #105, base = PR #103's branch). It continues the Part 2
of `HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md`, deleted on 2026-09-22 once this file superseded it
and its one unpersisted finding — the external prior art — moved into `SPECIFICATION.md` Part I.1.

**This file is the citation target, not a throwaway.** The rules and current-state facts it
established are in `SPECIFICATION.md` Part I, CLAUDE.md and BACKLOG.md, as the migration convention
requires; what stays here is the evidence *behind* them, cited by section from ~30 places across the
repo — 8 in `SPECIFICATION.md` (Parts B, C, E, F and I), 8 in `REAL_HARDWARE_TEST_QUEUE.md`, and two
`src/` comments in `asy_fram_driver.py` that cite it directly. It goes when those citations do — not
while the spec points at it for detail it deliberately does not carry. References below to
`HEAP_REMEDIATION_PLAN.md`, and to "the handover's §2.x", are provenance only: both files were
deleted on 2026-09-22, the plan's open real-hardware rows carried into
`REAL_HARDWARE_TEST_QUEUE.md` §1F. A bare `§` anywhere else in this file means this file.

**Only measurements that survived verification are recorded here.** Figures that were produced by a
defective instrument, or that a later and stronger measurement overturned, are not mixed in — they
are quarantined in §9, named, with the reason, so nobody re-uses them. §1 records the instrument
defects themselves, because each one is a trap a future session will otherwise re-enter.

**Start at §0A** for the mechanism — what is happening and why it produces the observed effects,
with every observation it accounts for; §0A.6 is the whole thing in one paragraph, and §0A.3 is the
load-bearing part. §0B is the test record, and §0B.7 is what is still open. **§1.2 item 7 (2026-09-18) is a
correction to every absolute byte figure in the file: the twin's build flag inflates allocation 4-5x; the
board-faithful re-pricing of the FRAM path is §3A, and §3B prices the restructuring that keeps the wire protocol byte-identical (38-90x).** **§1.5
(2026-09-18) bounds the whole corpus differently again: every figure here is at `gc.threshold(-1)`,
while the firmware's own boot entry sets `gc.threshold(32768)`, where the twin shows no layout
defect at any churn dose — §7A measures the owner's boot-confined `gc.collect()` scheme against
both.** **§0** is the ledger of every hypothesis this investigation tested — whose it was, what
tested it, and whether it is confirmed, suggestive, refuted, withdrawn or still untested. The rest
of the document is the evidence those verdicts rest on. §6A.13's scorecard is the same thing
narrowed to the factors that control the defect.

Note also §2.1's calibration: the twin heap is sized by **fill fraction**, not by copying a number
from the handover.

Provenance, same markers the handover uses:
- **[TWIN]** = measured host-side in the digital twin, on a frozen MicroPython 1.29.0 Unix port,
  by this branch's sessions. Independently reproducible; the harnesses are named in §10.
- **[SRC]** = read directly from the code in this repo, verified.
- **[HW]** = real `dev` bench board. Figures before §7D are cited from the handover, not
  re-measured — the branch had no go-ahead when they were written. **§7D is this branch's own
  real-hardware measurement** (go-ahead given 2026-09-18) and supersedes the twin where they
  disagree; §7D.4 names each correction.
- **[EXT]** = external source, URL given.

**Unit warning, applies to every [TWIN] byte figure.** A GC block is **32 bytes** on the 64-bit Unix
port and **16 bytes** on the RP2040. Counts (chip-select sessions, objects, transactions) transfer
to the board directly; byte totals are roughly 2x the board's and **ratios transfer, absolutes do
not**. Twin heap sized to `-X heapsize=560k` for layout work (calibrated in §2.1) and `64M` for
churn work (so no collection can intervene — see §1.2).

---

## 0. Hypothesis ledger — whose theory, what tested it, where it stands

The sections below are evidence; this is the map of the reasoning that produced them, kept so no
falsified theory gets re-proposed and so every conclusion carries its strength and its author.
**[O]** = the project owner's hypothesis, **[C]** = this session's. Standing is one of *confirmed*,
*suggestive*, *refuted*, *withdrawn* (mine, on my own later evidence) or *untested*.

### 0.1 The owner's hypotheses

| # | hypothesis | standing | evidence |
|---|---|---|---|
| O1 | Without the FRAM, fragmentation is negligible | **confirmed** | big run survives byte-for-byte, 132,416 -> 132,416, in_big 0 every repeat (§2.3) |
| O2 | Other modules allocate in the same region when instantiating, without pain | **confirmed literally, but an artifact of nesting** | every module's `setup()` is 936-971 KB — but that is its logger's FRAM round trip; own work is 5-18 KB (§4.1, §4.2). All ten setups also contribute permanent objects to the seam's free space, 4-10 eligible each (§0B.6) |
| O3 | Something inside the FRAM path is plainly inefficient — masses of short-lived allocations | **confirmed and quantified; re-priced on the settrace-free build** | 74 chip-select sessions to persist 12 bytes; 40 of the 50 write sessions carry four flag bytes (§3.1). On the real VM: 137,120 B per logger `setup()`, 73% of it the twelve single-status-byte writes, ~1 KB of asyncio bookkeeping per session; the yields cost 0 B (§3A) |
| O4 | A shared per-instance buffer would beat short-lived per-call allocations | **refuted as a lever** | hoisting all 80 throwaways saves 3,488 B of 843,040 (0.41%) and fragmentation is no better, mostly worse (§6.2) |
| O5 | It IS findable — fragmentation was always either heavy or absent, never partial | **confirmed, and reproduced from one knob** | allocation size 5 -> 9 GC blocks flips in_big 21 -> 0 at constant volume and yields (§6A.2) |
| O6 | Replace the awaited CS settle with `time.sleep_us(2)` | **implemented; the hazard fix is the case for it, the churn win was settrace** | "56% of each session's allocation" was the settrace cost of two `sleep()`s; on the real VM they were ~32 B each (§3A.6). The bus hazard (§5.1) is real and removed; neutral-to-worse on layout (§8); caused a regression (§8.1) |
| O7 | Arbitrate the bus with `threading.Lock` + `ThreadSafeFlag` | **refuted** | wrong primitive: only one task may wait on a `ThreadSafeFlag`, and `machine.SPI` is already blocking (§7.3) |
| O8 | The pattern: moderate per-call churn x very many calls x asyncio-friendly frequent yields x emergent across files x running in parallel with long-lived allocation | **confirmed in structure; two elements null** | plain `bytearray(64)` churn at that position reproduces the defect and exceeds it, so it is not FRAM/SPI/chunk-specific (§6A.1). The yield element is **null on the real VM: a yield allocates 0 B** (§1.2 item 7, §3A.5) — §6A.4's "protective" result measured the settrace build's 28-block sleep object, not a yield. "In parallel" is refuted outright for the boot batch: 0 of 1,562 yields had another `src/` task runnable, and `build_system()` creates no task at all — the interleaving is one task alternating churn with its own survivors (§0B.6). The "emergent across files" element is exactly right: §3A.5's critical path is eight async layers in four files |
| O9 | The sawtooth: churn repeatedly allocates the whole free memory, gc collects often because fill is high, the level sawtooths across the whole heap, and survivors thrown at random points stay where they land, ending evenly distributed | **confirmed** | fill driven to **64 bytes free**, amplitude 272,576 of ~278,000 (§6A.6); survivors smeared across all ten heap deciles at span 96-99% when broken vs the bottom 1-2 deciles at 18-40% when clean (§6A.7) |
| O10 | There is no churn budget: it is a lottery, pure chance plus nonlinearity — a conjunction of parallelism, volume and interleaving, each with a threshold, and the knee is where all conditions are met at once | **confirmed for the conjunction and the absence of a budget; component verdicts differ** | volume x survivor population interact multiplicatively (§6A.11); interleaving null — a yield allocates nothing on the real VM (§1.2 item 7); **parallelism is absent from the boot batch entirely** (§0B.6), so it cannot be one of the met conditions there. "No budget" now has a mechanism: the churn knee is a property of the *pair*, not of the churn (§6A.11). The chance is not between runs — the outcome is deterministic per configuration (§6.3, §6.4) — it is a fixed order's sensitivity to any shift in it |
| O12 | The FRAM path's churn is an architectural inefficiency of the driver/protocol *construction*: a critical-path run should generate orders of magnitude fewer short-lived allocations, with every integrity feature of the storage kept | **confirmed by a wire-identical prototype** | same 74 CS cycles, same bytes on the bus, asserted event by event, and unchanged by everything since (the golden traces in `tests/test_asy_fram_wire_trace.py`). **As BUILT and shipped, at the lock scope the owner chose: 122,880 -> 13,696 B (9.0x)** for a blank logger `setup()` and 80,384 -> 9,152 (8.8x) for a valid one (§7C, §11 item 6). §3B's prototype ladder (3,072 B / 38x, ~1,300 / ~90x) assumed per-block locking throughout and never priced the rung the plan first picked |
| O13 | `gc.collect()`, confined to the boot lists - start, between each module, end, and the same for the async setup list - keeps the boot's permanent survivors packed at the bottom of the heap by giving each of them a fitting hole low down, and stays forbidden everywhere else. Clarified by the owner, 2026-09-18: survivors are never moved, and packing the *later* ones low is what was meant by "compacted" | **confirmed exactly as stated, and both halves of the original caveat are now superseded** — the floor it "fell short of" was retired by the owner 2026-09-19 (§7G), and "null at the shipped threshold" was a twin reading at a fixed threshold: on silicon the threshold is what carries the gain into the run phase (§7H.3) | each collect resets the allocator's free-scan index, so the next module's survivors take the lowest fitting hole instead of a hole above the churn's high-water mark - deciles 20/5/4/2/1/5/5/13/4/5 at span 92% become 29/7/0/0/1/0/0/0/32/0 at median gap 224 B (§7A.4), and the number of collects gives a clean dose-response (§7A.2). On the board's own metric at the board's own fill it is worth 3.2-6.9x, reaching 45% of free after `build_system()` and 58% after the task list, against a tripwire of 55-74% that is itself ~5x above the firmware's own worst reachable allocation (§7A.8, §7A.9): the strongest single remedy measured, and still short. At the shipped `gc.threshold(32768)` (§1.5) it changes nothing (§7A.6) |
| O11 | The survivor population is itself one of the conditions | **confirmed, decisively** | churn alone 0%, survivors alone -18%, both together **-88%** of the largest free block (§6A.11) |

### 0.2 This session's hypotheses

| # | hypothesis | standing | evidence |
|---|---|---|---|
| C1 | Interleaving of churn with long-lived allocation is the whole story | **withdrawn — too glib** | true as far as it goes, but §4 shows the FRAM path is also 36x every other peripheral in transaction count, and §6A shows size class dominates (§9) |
| C2 | Collections during the batch strand the survivors (collection-stranding) | **refuted by my own test** | base is broken at 560k, 4M *and* 16M, where the entire 8.4 MB of churn fits with room to spare (§6.5) |
| C3 | The churn's sweep *extent* is the variable | **refuted** | no dose-response: 4 loggers (498 sessions) keep 100% in 5/5 runs while 1 logger (126 sessions) keeps 51-62% (§9) |
| C4 | A large heap will clear the defect | **prediction failed, recorded as such** | broken at 16 MB, kept 49%, in_big 41 (§6.5) |
| C5 | Churn volume does not control the outcome | **confounded; restated**, and §0B.4 now shows uniform small churn strands nothing at a natural survivor population even at 2.3x base's volume | every rung changed size mix and object count along with volume; held fixed, volume *is* monotonic 0 -> 3 -> 21 (§6.1, §6A.1) |
| C6 | The `bare` control shows a bare SPI transaction is harmless | **withdrawn** | `_after_fram()` injects the whole burst as one early block, so it measured the churn-first configuration, not the interleaved one (§9) |
| C7 | Churn and survivors compete for the *same* dust holes, because they are the same size class | **confirmed per object, 162/162** (§0B.1); refined — only survivors needing >= 2 contiguous blocks are eligible, which is 25 of the 76 (§0B.2) | survivors are mean 52 B ~ 2 blocks; a 2-block request fits 82% of the 1,058 seam holes, a 9-block request 21%; measured mid-churn occupancy 82% vs 16% — 82% measured against 82% predicted (§6A.3) |
| C8 | The size threshold is mediated by collection frequency — a large request fails on contiguity and forces an early, shallow collection | **confirmed on the settrace build; the mechanism is allocator-level and build-independent, the byte figures are not** | large-unit churn collects at a median 220,864 B still free vs 1,440 B for small-unit churn (§6A.6) |
| C9 | Cutting the 74 chip-select sessions to ~6 will clear the contiguity floor | **withdrawn as stated; the achievable side reopened by §3B** | ~12x against a required 40-100x; 70,000 B per logger measures in_big 14 / span 97%, inside the saturated regime (§6A.8). §3B now reaches 38-90x *without* cutting a session; the required side was computed in settrace bytes and is not re-derived (§3A.6), so whether that clears the floor is untested |
| C12 | The status-byte pair, the two copies and the per-write WREN/WRDI envelope are redundant bookkeeping | **withdrawn — owner's account, 2026-09-18** | each element is grounded (§3B.1): the status bytes are a lock against a copy caught mid-operation, the pair written separately so a torn pair is detectable; the copies restore the last valid value; the CRC catches bus errors; each CS cycle is what commits a command at the chip. The wire protocol is the integrity feature; the cost is the Python that carries it |
| C10 | Loop yields are protective for layout | **withdrawn — a settrace artifact** | it held, confound-checked, on the settrace build (§6A.4), where each yield allocated a 28-block object that competed for no survivor's hole and forced early collections. On the real VM a yield allocates 0 B (§1.2 item 7), so it can be neither protective nor harmful to layout |
| C13 | Every figure in this file is the `gc.threshold(-1)` picture, and the firmware ships `gc.threshold(32768)`, where the twin shows no layout defect at any churn dose | **confirmed [SRC] + [TWIN]; the qualitative half was the handover's, and the [HW] question it raised is resolved** | the threshold is set in the generated boot entry, which neither the harnesses nor the hardware test's own device script execute (§1.5); at 32,768 B `base` keeps 87% against 18%, survivors span 12% of the heap against 92%, and every churn dose from zero to base's own clears the floor (§7A.5). The handover's §2.12 already recorded that a threshold set before `build_system()` makes the twin look healthy and called it masking; what is new is the quantification and the [SRC] trace. The [HW] 20,592 B is a deliberate pre-threshold reading, so board and twin agree and the corpus's baseline is the one the hardware test asserts on (§1.5) |
| C11 | Pre-allocating each module's permanent objects at construction is the remedy the evidence favours | **refuted** | the mechanism is real — the same objects placed pre-seam give in_big 0 and 100% kept where in-window they give 380 and 12% — but it holds only below the churn threshold. At the real 843,232 B dose pre-seam objects are unprotected (kept ~50%), and the real system's 76 survivors are already an order of magnitude below the survivor axis's own onset, so that axis is not the binding constraint (§6A.12) |

## 0A. The model

What is happening and why it produces what was observed. Every claim is **[SRC]** verified against
the pinned MicroPython v1.29.0 source, **[TWIN]** measured, or marked as **inference**. §0B is the
test record behind it; §0A.7 is what remains open.

Revision note: §0A.1-§0A.2 are unchanged and confirmed. **§0A.3 has been rewritten** — the earlier
statement, that transient churn holds the holes a survivor needs, is not what the evidence supports.
Transient churn turns out to be *self-limiting*. The active agent is irreversible consumption by
**permanent** objects, with transients modulating collection timing.

### 0A.1 What the allocator actually does [SRC]

Read from `py/gc.c` at tag `v1.29.0`:

- **Allocation is lowest-fit over the whole heap.** `gc_alloc()` scans the allocation table from
  `area->gc_last_free_atb_index` upward and takes the **first** run of `n_blocks` free blocks it
  finds (`:938-948`). No size-class free lists, no best-fit.
- **The scan hint is a lower bound, not a cursor.** It advances only when the request was for
  exactly one block (`if (n_free == 1)`, `:987-991`), whose own comment says this is "to reduce
  fragmentation ... which guarantees that there are no free blocks before this one". A multi-block
  allocation leaves it where it was.
- **The hint retreats on every free below it** (`:1110-1111`, and `gc_realloc` at `:1241`), and a
  collection resets it to zero for every area (`gc_collect_end()`, `:611-613`).
- **A collection happens only when an allocation cannot be satisfied.** `gc_alloc()` falls through
  to `gc_collect()` only after a full scan finds nothing (`:960-973`), then retries. Under
  `gc.threshold(-1)` — MicroPython's real default — nothing else triggers one.
- **The collector never moves an object.** Mark-and-sweep, no compaction.
- **`del` does not free a block.** It drops a reference; the block stays marked-used until the next
  sweep. So dropped transients accumulate monotonically between collections.
- **Both ports run a single fixed heap area with no growth** (`MICROPY_GC_SPLIT_HEAP` and `..._AUTO`
  default to 0; the Unix port does not override them; rp2 ties the former to PSRAM, absent on a
  Pico W). Every split-heap branch is compiled out on both, including the second hint-advance site
  at `:952-956`.

Three consequences carry everything below. **Every allocation is served from the lowest free run
that fits it**, so a request reaches high memory only when nothing lower can hold it. **Placement is
final.** And **an allocation that cannot be satisfied triggers a collection and then succeeds** —
which is what makes transient pressure self-limiting.

### 0A.2 The heap the setup batch inherits [TWIN]

| | value |
|---|---|
| small free holes ("dust") at the seam | **1,058**, totalling 6,798 blocks (217,536 B) |
| one large free run | ~56,000-121,000 B depending on campaign, high in the heap |
| holes that fit a 2-block request | **870 (82%)**, holding 97% of the dust blocks |
| holes that fit a 5 / 9 / 28-block request | 464 (43%) / **226 (21%)** / **12 (1%)** |

**The dust is mostly *import* residue, not construction residue** (§0B.3): import alone leaves 520
holes and 2,162 blocks — 71% of the seam's hole count — and construction adds only 216 more. Both
are fixed workloads, which is why the dust is heap-size independent.

**The single large run is the only source of a large contiguous allocation**, so any contiguity
criterion is a statement about it alone. (It was the 80,000 B floor when this model was written;
that floor was **retired by the owner on 2026-09-19** and replaced by survivor volume, survivor
placement and a contiguity check derived from the worst reachable allocation — §7G. The model's
claim is unaffected: whatever the criterion, this run is what it measures.)

### 0A.3 The mechanism

Two populations allocate during the setup batch:

- **transients** — the FRAM logger path's churn: 843,232 B per logger setup, a *mix* of size
  classes (2-block one-byte `bytearray`s, 5-7 block coroutine frames, 28-block `sleep(0)` objects);
- **survivors** — each module's own permanent objects: 72-76 in total, ~4,000 B.

**Only some survivors are eligible to be harmed** (§0B.2). The population is **51 one-block objects
plus 25 multi-block ones**, and every stranded object ever observed is multi-block (2-6 blocks). A
1-block request can be met by *any* free single block and one essentially always exists, so
**two-thirds of the survivors are structurally immune**. The eligible population is ~25; base strands
8-9 of them.

The placement law, confirmed per object **261 times with no counterexample** (§0B.1, §0B.4):

> An eligible survivor is placed **inside the large free run** if and only if, at the instant it is
> allocated, **no free run below that one is large enough to hold it**. Being live, it is never
> moved again, so it stays there and splits the run.

Each stranded object splits the large run once more. **8-9 objects, well under 1 KB in total, take
it from 121,504 B to 91,008 B in one run; 13-21 of them take it from ~132 KB to ~43 KB.** The batch
barely changes the *number* of holes (736 -> 733): it is not creating dust, it is splitting the one
run that matters.

#### What produces the "no fitting hole" condition

This is where the model changed. There are two ways holes get consumed, and they behave oppositely:

**Transient consumption is self-limiting.** Dropped transients accumulate until a collection, so
they do progressively occupy holes — fill has been measured running down to **64 bytes free**
(§6A.6). But a transient that finds no fitting hole *triggers the collection itself* and then
succeeds, restoring every hole. So a transient of the same size class as a survivor cannot starve
that survivor: it hits the wall first, and the collection resets the field. This is inference from
`:960-973`, and it is what the measurements show — **uniform small-object churn stranded nothing in
~190 probes at doses from 0 to 1,875 KB per logger, 2.3x base's own** (§0B.4). Fitting-hole counts
dipped to 1, 2, 3 and never to 0.

**Permanent consumption has no brake.** A permanent object takes its hole irreversibly; no
collection returns it. Once the permanent population has taken the fitting holes, every later
same-size allocation must go high. This is the axis with the strong threshold: nothing at all up to
525 retained objects, then 0 -> 7 -> 119 between 795 and 1,148 (§6A.11) — and 795 objects is 91% of
the 870 holes that fit their size class.

So the two axes are **not symmetric**, and their measured interaction follows: permanent objects
alone cost 18% of the large run, a 176x-below-knee churn dose alone costs 0%, and **together they
cost 88%** (§6A.11). Permanent consumption sets how close the heap sits to the boundary; transients
determine the timing of the collections that reset it.

#### Why the outcome is a lottery

Placement depends on the hole state at one instant, and that state oscillates with the collection
cycle. Measured at the real survivor birth positions across 7 perturbations, the fitting-hole count
is reproducible to within a few percent and swings between ~400 and **exactly 1**: three or four of
ten real births occur with **one** fitting hole left — the one the survivor then takes (§0B.4). The
system runs on a knife edge, so the damage is a *coincidence count*, not a function of the inputs.
That is why nothing composes (§6.6), why two perturbation families can disagree in direction
(§6A.10), and why every figure here is ensembled.

### 0A.4 Why each observation follows

| observation | what the model says |
|---|---|
| Largest block collapses 5.6x while free falls only 16% [HW] | 8-21 permanent objects totalling under 2 KB sit *inside* the one run that matters. Consumption and layout are different quantities (§2.1) |
| Survivors span 88-98% of the heap across 53-63 distinct runs | each is placed in the lowest hole that fits it at its own birth instant, and those instants sit at different points of the collection cycle (§2.2, §6A.7) |
| Suppressing logger FRAM I/O leaves the big run byte-for-byte intact, with the *same* survivors | identical 76-object population and type histogram; only placement differs (§2.3, §0B.2) |
| One logger setup is as damaging as twenty | the batch is already at the boundary from the first logger onward; being at the boundary is binary (§2.4) |
| Running the same churn *after* the batch gives exactly 100% kept, in_big 0 | no eligible survivor is allocated afterwards, so there is nothing to place badly. The only exact zero ever measured (§2.5) |
| Only 8-21 of 76 survivors are ever stranded | 51 are 1-block and structurally immune; the eligible set is ~25 (§0B.2) |
| Allocation size is a hard threshold between 5 and 9 blocks | eligibility is a hole-fit question: 82% of holes admit 2 blocks, 21% admit 9 (§6A.2, §6A.3) |
| A larger probe survivor is stranded *earlier* in a run | fewer holes fit it — 833 fit 1 block, 667 fit 2, 267 fit 8, 72 fit 16 (§0B.1) |
| Small churn drives free to **64 bytes**; large churn collects at **220,864 B** still free | a small request keeps finding *some* hole, so nothing fails and nothing collects until the heap is genuinely full; a large request fails on contiguity long before that (§6A.6) |
| Loop yields are **protective** at fixed small-object count | `sleep(0)` is 896 B = 28 blocks, fitting 12 of 1,058 holes. It cannot take a survivor's hole, and it fails-and-collects early like any large request (§6A.4) |
| Uniform churn at 2.3x base's volume strands nothing | transient pressure is self-limiting: the churn triggers the collection that restores the holes (§0B.4) |
| Permanent population and churn interact multiplicatively (0%, -18%, -88%) | only permanent consumption is irreversible; transients modulate the timing (§6A.11) |
| No fixed churn budget exists | the boundary is set by the permanent population; §6A.8's figures are not a property of volume alone (§6A.11, §0B.4) |
| Heap size is irrelevant — broken at 560k, 4M and 16M alike | the dust is import-plus-construction residue, both fixed workloads, so the hole population is heap-independent. A bigger heap adds a bigger large run, not more dust (§6.5, §0B.3) |
| Cutting 63% of churn (r2) is slightly *worse*; cutting 99.4% (r4) is clean | r2 removed the 224 B frames and 896 B sleeps — the **large**, hole-safe, collection-forcing part — and left the rest. r4 removed effectively all of it (§6.1) |
| `synccrc` cut churn 11.9x and measured *worse* than base | it removed the per-byte `sleep(0)`, i.e. 28-block protective allocations, while leaving small churn (§7) |
| Pre-seam permanent objects are protected at 4,800 B churn and unprotected at 843,232 B | placed while the dust is free they are never displaced, but they consume dust irreversibly, so the un-hoisted survivors are displaced as before (§6A.12) |
| Nothing composes; perturbation families can disagree in direction | the damage is a coincidence count against an oscillating state (§6.6, §6A.10) |
| Added parallelism worsens the tail but barely the median | more concurrent activity means more instants near the boundary, so more births can coincide — a tail effect (§6A.10) |

### 0A.5 The four results that only this model explains

1. **Reducing churn made things worse** (r2, `synccrc`): those variants preferentially removed
   *large* allocations, which are hole-safe and collection-forcing. Churn is not one quantity.
2. **Yields are protective**: a yield is a 28-block allocation.
3. **No churn budget**: the boundary is set by irreversible permanent consumption.
4. **Hoisting permanent objects earlier does not help at the real dose**: it protects the hoisted
   ones and consumes the dust the rest need.

A model accounting only for "small churn is bad" predicts the opposite in all four.

### 0A.6 The model in one paragraph

The heap the setup batch inherits has one large free run and ~1,058 small holes left over mostly
from import. Allocation is lowest-fit and never moves anything, so an object goes high only when
nothing lower fits it. Two-thirds of each module's permanent objects need a single block and can
always be placed low; the other ~25 need two or more contiguous blocks and are eligible to be
harmed. Whether an eligible object is placed inside the large run is decided entirely by whether a
fitting hole exists below it at that instant — confirmed per object 261 times without exception.
Transient churn pushes the heap towards that condition but cannot complete it, because a transient
that fails triggers the collection that restores the holes; irreversible consumption by permanent
objects is what actually moves the boundary. The heap therefore runs on a knife edge on which three
or four of ten real births find exactly one usable hole, and the damage is the count of births that
fall on the wrong side. Each one that does splits the only large run there is, which is why under
2 KB of permanent data can cost 60 KB of contiguity while total free memory barely moves.

### 0A.7 The audit that generated the confirmation work

**This table is the audit that generated §0B's work, kept for provenance.** Its items resolved as:
1, 3, 5 and 7 closed; 6 and 8 dissolved; 2 advanced and still open; and two of the model's own
statements changed rather than being confirmed, which is why §0A.3 was rewritten. **§0A.7's own
wording predates that rewrite** — where it says transients "hold" the holes, read §0A.3's
self-limiting account instead. For what is open *now*, see §0B.7.

Each load-bearing claim of §0A.3, classified as **[V]** verified against source, **[M]** directly
measured, **[I]** inferred from a correlation, or **[U]** untested. Ranked by how much the model
leans on it.

**Closed since the first draft of this section.** Both ports run a **single fixed heap area with no
growth**: `MICROPY_GC_SPLIT_HEAP` and `..._AUTO` default to 0 (`py/mpconfig.h:774-780`), the Unix
port does not override them, and rp2 ties the former to `MICROPY_HW_ENABLE_PSRAM`
(`ports/rp2/mpconfigport.h:100-101`), which a Pico W does not have. So every `#if
MICROPY_GC_SPLIT_HEAP` branch is compiled out on both — including the **second** hint-advance site
at `py/gc.c:952-956`. The `n_free == 1` advance at `:987` is the only one that exists on either
port, and the heap cannot acquire a new area mid-run. The model's foundation transfers structurally;
only its numbers are port-specific.

| # | claim | status | what is missing, and what would close it |
|---|---|---|---|
| 1 | **A survivor is placed in the large run *because* no hole below it could fit at that instant** | **[I]** — the central claim, and correlational only | Evidence is an association (82% hole occupancy alongside high in_big) plus the exact complementarity `in_big + surv_in_dust = total`. The causal step has never been observed for a single object. Closing it: allocate a marked 2-block probe at controlled instants during the churn, capture the hole state immediately before, and record where the probe actually landed. The model predicts *lands in the large run **iff** no fitting hole exists below it*, with no exceptions — a per-object prediction, falsifiable by one counterexample |
| 2 | **On the churn axis the binding quantity is the live transient peak** | **[U]** | 870 holes fit a 2-block request, and the survivor-axis onset (795-1,148 objects) sits at 91-132% of that — a clean numerical fit. But the churn-axis onset is 8,000-20,000 B per logger, only 83-208 objects, **an order of magnitude below 870**. The model's account is that transients are allocated and freed repeatedly so their *live* population is what holds holes; that peak has never been measured. Until it is, 870 is a candidate law for one axis, not a derived threshold for both |
| 3 | **The stranded objects are other modules' permanent objects, displaced** | **[I]**, and partly contradicted by my own data | §2.2 reports the in_big size signature as a cluster of **64 B objects plus one 160 B and one 192 B, nearly all "other head"** — which reads like retained coroutine/generator residue, not module state. §6A.11's isolated consolidated pass retains **16-17 objects of its own**. So some of the stranded set may be the churn's *own* retained objects — **self-stranding rather than displacement**, a materially different story for part of the damage. Never resolved. Closing it: identify the in_big objects by owner, or compare the in_big population between a churn variant that retains nothing and one that does |
| 4 | **The survivors' own size class is what makes them vulnerable** | **[U]** — and this is a sharp, untested prediction | Only the *transients'* size was ever varied (5 -> 9 blocks). The model says eligibility is symmetric: a survivor needing 9 blocks should find only 21% of holes available and so be **more** readily stranded, even by large transients. Varying survivor size is a clean discriminator between "size class of the pair" and "size class of the churn", and it has not been run |
| 5 | **The dust is the construction phase's residue** | **[I]** | This is what the heap-size-irrelevance result rests on (§6.5): a bigger heap adds a bigger large run, not more dust. But the hole distribution has never been compared **after import** against **after construction**, so the dust's origin is assumed. Cheap to close with two map dumps |
| 6 | **Hole *count* is the binding quantity, not hole *capacity*** | **[I]** | The two coincide in every configuration measured. They can be separated by holding total dust blocks fixed while changing the hole-size distribution |
| 7 | **The damage is a coincidence count** | **[I]** | This is the model's explanation for the lottery, the heavy tail and the non-additivity, and it is qualitative. It has never been counted: the number of survivor births falling inside a held-hole window has not been recorded and checked against in_big. Doing so would make the model **predictive** rather than only explanatory |
| 8 | **The 82%-predicted / 82%-measured agreement** | **[M]**, with a known sampling weakness | The strongest single piece of evidence, but occupancy was sampled at **one** matched point mid-churn — and §6A.11 later showed a single sample cannot characterise this quantity (21% at n=3,000 against 22% at n=8,783, on opposite sides of the outcome). The agreement should be re-established as a time-average, or at several matched points, before being leaned on further |
| 9 | **Added parallelism worsens the tail** | **[I]**, suggestive | n=6 rather than 16; this campaign's base ran unusually clean (in_big 2-6 against 7-16 elsewhere); and the churn task retains its own objects, moving the survivor population 69 -> 82, so it is not a pure isolation (§6A.10) |
| 10 | **The mechanism holds on the real board** | **[U]** | Everything but the symptom is [TWIN]. A GC block is **16 B** there against 32 B here, so the 52 B survivor is ~4 blocks rather than 2, and every hole-fit fraction and threshold shifts. The structure should carry (§0A.1 is port-independent now); **none of the quantitative thresholds have been re-derived for 16 B blocks**, and no real-hardware run has been made against this model |

**Order these would settle the model fastest:** 1 (the causal step), 3 (what is actually stranded),
2 (the churn-axis quantity), 4 (survivor size symmetry). Items 5-8 tighten it; 9 and 10 are scope
rather than mechanism.

## 0B. Confirming the model — what the tests closed, and what they changed

The §0A.7 audit named ten open items. This section reports the runs made against them. Three
results **changed** the model rather than confirming it — the two below, plus the self-limiting
finding in §0B.4 that caused §0A.3 to be rewritten.

### 0B.1 The central claim, tested per object — 162 of 162, no counterexamples

Gap 1 asked for the causal step itself: *is a survivor placed in the large free run **because** no
hole below it could fit at that instant?* Made falsifiable by allocating a **probe survivor** at
controlled birth points — a runtime-built tuple, which is a **single** allocation whose address
`id()` reports (a `bytearray` is two allocations, object plus buffer, and a 1-block request also
advances the GC hint, so neither is usable). The probe's true block extent is read from the final
map, never assumed.

**Design correction made mid-experiment.** The first version dumped the map *before* allocating, and
produced one counterexample at 16 blocks: 2 fitting holes existed, yet the probe landed in the large
run. Measured cause — **the dump itself allocates 320 B (10 blocks), every time, consistently** —
so the snapshot was stale by more than the slack it was measuring. Re-designed to allocate **first**
and dump **after**, reconstructing the pre-state by marking the probe's own blocks free again, which
leaves nothing allocated between the probe and its own snapshot. The counterexample disappeared.

| probe size | probes | counterexamples | fitting holes below, at the first probe |
|---|---|---|---|
| 1 block | 23 | **0** | 833 |
| 2 blocks (the survivors' own class) | 23 | **0** | 667 |
| 8 blocks | 23 | **0** | 267 |
| 16 blocks | 23 | **0** | 72 |
| **at real survivor positions**, real churn, 7 perturbations | **70** | **0** | 403 |
| **total** | **162** | **0** | |

The transition lands exactly where the model says. In the synthetic runs the count of fitting holes
below the large run falls monotonically — 833, 743, 694, ... 51, 33, **0** — every probe lands low
while it is non-zero, **every probe lands in the large run once it reaches zero**, and at the probe
after a collection the count jumps back to 1,142 and placement returns to the dust.

This also settles **gap 7**: the "coincidence count" is no longer a qualitative story. Each probe is
a birth, and the model predicts its individual fate correctly **162 times out of 162**.

### 0B.2 Changed: only multi-block survivors can ever be stranded

Gap 3 asked what the stranded objects actually are, since §2.2's size signature looked like
coroutine residue. Answered by typing them from the block map's own legend:

| run | inside the large run | in the dust |
|---|---|---|
| base, k=0 | **8** — all "other head"; sizes 2,2,2,2,2,3,5,6 blocks | 68 |
| base, k=3 | **9** — all "other head"; sizes 2x5, 3, 4, 5, 6 | 67 |
| `noio` | **0** | 76 — other head 55, float 11, dict 7, tuple 2, list 1 |
| synthetic churn | **0** | 76 — **histogram identical to `noio`** |

Two things follow, and the second is new.

**The stranded set is the batch's own permanent population, not churn residue.** The total is the
same 75-77 objects with and without churn, and the type histograms match exactly; only the placement
differs. The §2.2 worry is resolved — and note the synthetic churn retains *nothing*, so any
stranding under it is necessarily of batch survivors.

**The vulnerable population is far smaller than 76.** The dust population is **51 one-block objects
plus 25 multi-block ones**, and every stranded object in every run is multi-block (2-6 blocks). A
1-block request can be met by *any* free single block, and one essentially always exists — so
**two-thirds of the survivors are structurally immune**. The eligible population is ~25, of which
8-9 strand in base: about a third of what can be hit. §0A.3's "a survivor born while the holes are
held" should be read as **"a survivor needing two or more contiguous blocks"**.

### 0B.3 Changed: the dust is mostly import residue, not construction residue

Gap 5. §0A.4 explained heap-size irrelevance by saying the dust is the construction phase's residue.
Measured across three stages of one base run:

| stage | holes | blocks | fit 2 blocks | largest run |
|---|---|---|---|---|
| after **import**, before any construction | **520** | 2,162 | 354 | 289,984 |
| at the **seam**, after construction | 736 | 4,658 | 670 | 121,504 |
| **after** the setup batch | 733 | 5,297 | 673 | **91,008** |

**Import alone leaves 71% of the seam's hole count and 46% of its blocks.** Construction adds only
216 holes. The conclusion in §6.5 survives — import and construction are both fixed workloads, so
the dust is still heap-size independent — but the attribution was wrong and is corrected here.

Worth noting in the same table: the batch barely changes the hole *count* (736 -> 733) while taking
the largest run from 121,504 to 91,008. It is not creating dust; it is splitting the one run.

### 0B.4 Gap 2 advanced, not closed — and it now points somewhere specific

The churn-axis question was: what quantity binds, given that the onset is at 83-208 objects while
870 holes fit a 2-block request. Probed directly by running the per-object experiment across churn
doses at a natural-scale survivor population (10 per logger, 90 total against the real 76):

| synthetic churn per logger | probes | minimum fitting holes reached | stranded |
|---|---|---|---|
| 0 / 960 B / 4,800 B / 19,200 B | 23 each | 1 | **0** |
| 96,000 B / 288,000 B | 23 each | 1 | **0** |
| 823,000 B (base's own dose) | 23 | 1 | **0** |
| 1,875,000 B (2.3x base) | 23 | 1 | **0** |

**Uniform small-object churn does not strand anything at a natural survivor population, even at
2.3x base's volume.** Yet base does strand 8-9. So base's churn differs from uniform small churn in
a way that matters, and the candidates are concrete: its **size mix** (it contains 2-block
`bytearray`s, 5-6 block frames and 28-block sleep objects, not one uniform class) and its own
retained objects. §6A.8's "churn budget" figures were measured with the equal-total-bytes injector
and should not be read as a property of churn volume alone.

At the real survivor birth positions the same instrumentation shows why the system is so
knife-edged: across 7 perturbations the fitting-hole count at the ten probe points is reproducible
to within a few percent — 403, **1**, ~220, **1**, ~40, ~360, **1**, ~30, ~330, **1** — so three or
four of ten real births occur with **exactly one** fitting hole left, the one the survivor then
takes. One more competing demand at those instants and it strands.

**Not closed:** 70 probes at real positions produced no stranding, while base strands 8-9 of 76. The
probes are placed once per module `setup()`; the survivors that do strand are born at instants that
sampling does not reach. The positive branch of the law is therefore confirmed 20+ times
synthetically and **zero times at a real survivor position**.

### 0B.5 Two gaps dissolved rather than answered

- **Gap 6, hole count versus hole capacity.** The per-object law is neither: it is *does any single
  fitting hole exist below the large run*. Aggregate count and aggregate capacity are both emergent
  summaries of that, so no separate aggregate law is needed and the question does not arise.
- **Gap 8, the single-sample occupancy weakness.** Superseded. The 82%/82% agreement was one
  mid-churn sample; the per-probe fitting-hole counts are a direct per-birth measurement of the
  quantity that actually governs placement, taken 162 times.

### 0B.6 Changed: the startup phase has no parallelism at all

Prompted by the owner's restatement of the model as three patterns present in the original code:
distributed long-lived survivors, high churn in the FRAM graph, and **both interleaving in the
startup phase**. The first two hold (below, and §3/§4). The third does not hold in the sense of
task-level parallelism — it is refuted at the source, and the interleaving that does exist is of a
different kind.

**[SRC] The setup batch is a straight sequential await chain.** `buildgen/codegen.py:465-466`
emits one `await <instance>.setup()` per module with `sysfunct.feed_watchdog()` between them — no
`create_task`, no `gather`. Tasks start only *after* `build_system()` returns (`_emit_main`:
`start_timers`, `ntp_force_sync`, `start_and_check_tasks`). All 25 `create_task` sites in `src/`
sit in a `start_*` method that `_collect_task_starters()` invokes there; the two that do not —
`config_manager.py:385`'s deferred flash flush and `asy_wifi_service.py:367`'s DNS server — are on
the REST and connect paths, and `ConfigManager.setup()` itself only awaits its logger and reads the
file (`config_manager.py:444-456`).

**[TWIN] Measured at every yield of the real batch**, by reading `asyncio.core._task_queue.peek()`
at each one (validated against a two-task control: `None` when the running task is alone, the other
task's coro when one exists). The twin's two hardware fakes are neutralised here — see below.

| module `setup()` | yields | yields with another `src/` task runnable | CS sessions | I2C sessions |
|---|---|---|---|---|
| `AsyFramManager` | 4 | **0** | 2 | 0 |
| `SystemService` | 172 | **0** | 74 | 0 |
| `AsyConnTime` | 172 | **0** | 74 | 0 |
| `AsyNtpClient` | 172 | **0** | 74 | 0 |
| `SGP40_Reader` | 172 | **0** | 74 | 0 |
| `BMP3xx_Reader` | 172 | **0** | 74 | 0 |
| `ISL29125_Reader` | 172 | **0** | 74 | 0 |
| `NotificationCoordinator` | 172 | **0** | 74 | 0 |
| `UartLinkExerciser` x2 | 354 | **0** | 148 | 0 |
| **total** | **1,562** | **0** | **668** | **0** |

Tasks in the scheduler queue when `build_system()` returns: **0**. So nothing the construction or
setup phase does creates a task, and **every `await asyncio.sleep(0)` in the batch is a round trip
to the scheduler and straight back into the same task.** The I2C column is 0 because
`SensorReaderConfig.setup()` is only `await self.cfgmgr.setup()` (`base_classes.py:419-420`) — a
sensor's own chip init happens later, in its read-loop task. **The setup batch's entire I/O is the
FRAM's.**

**The twin's own two tasks are fakes of hardware.** Left live, `peek()` was non-`None` at 1,554 of
1,579 yields — every one of them `digital_twin/machine.py`'s `Timer._run` (:811) or
`WDT._countdown` (:890), which model an rp2040 hardware timer and the hardware watchdog as asyncio
tasks. Neither is a task on the board. They were also mostly parked on a future deadline rather
than runnable: across the whole batch the twin delivered **5** timer callbacks and **0** watchdog
expiries (11 arms, 10 countdown tasks each cancelled by the next feed). So foreign execution during
the batch is 5 events against 1,579 yields even in the twin, and zero on hardware. **Carry this as
a caveat:** these two fakes were live in every other twin run in this file, and they are the only
parallelism any of them had — which is the concrete form of gap 9's confound.

**What the interleaving actually is.** Not two tasks racing, but one task alternating, inside each
module's own `setup()`: its logger's FRAM round trip (74 chip-select sessions, ~843 KB) and its own
permanent allocations, module after module. Attributing survivors to the phase that creates them —
blocks free at the seam that are occupied by the end of that phase, grouped into contiguous runs:

| module `setup()` | objects born in seam-free blocks | of those, >= 2 blocks (eligible) | bytes |
|---|---|---|---|
| `AsyFramManager` | 12 | 9 | 1,216 |
| `SystemService` | 14 | 5 | 1,088 |
| `AsyConnTime` | 14 | 6 | 832 |
| `AsyNtpClient` | 13 | 6 | 1,120 |
| `SGP40_Reader` | 13 | 8 | 1,184 |
| `BMP3xx_Reader` | 15 | 4 | 896 |
| `ISL29125_Reader` | 20 | 10 | 1,408 |
| `NotificationCoordinator` | 16 | 7 | 1,344 |
| `UartLinkExerciser` | 14 | 7 | 1,184 |
| `UartLinkExerciser` | 8 | 4 | 736 |
| **total** | **139** | **66** | **11,008** |

**All ten setups contribute, and all ten contribute eligible objects** — 4 to 10 each. The survivor
population is genuinely distributed across modules rather than concentrated in one, which is the
part of the owner's first pattern that needed measuring. Two caveats. This is an instrumented run
(a collect and a map dump at every phase boundary), so it measures *births*, not base's placement:
the cumulative 139 exceeds the ~76 alive at the end because some die in a later phase. And `in_big`
was **0** in this run — which is §0A.3's self-limiting mechanism seen from the other side: with
every hole restored at each boundary, lowest-fit always finds one below. It is recorded as model
confirmation, not as a remedy (SPECIFICATION.md I.4(e)-(g) forbids that one).

**Why the model is unaffected, and what it strengthens.** The placement law is instantaneous — *is
there a fitting hole below, at this instant* — so it needs an order, not a race. Sequential
execution supplies one. And it accounts for something already in the record that a genuine lottery
would not predict: the outcome is **reproducible**, not variable — §6.3's in_big 22 and 24 and
§6.4's 17-22 are all noted as deterministic across all six perturbations. The chance in this system
is not chance between runs; it is the extreme sensitivity of a fixed order to any shift in it, which
is why a 2-block change of one object's size moves the result and why nothing composes.

### 0B.7 Still open

- **Gap 2's positive branch at real positions** (§0B.4) — the one remaining mechanism gap.
- **What in base's churn does the stranding**, given uniform churn does not (§0B.4). Its size mix was
  the named suspect — and §1.2 item 7 now weighs against it too: on the settrace-free build the
  transient population is entirely different (no frame/code object per call, no 28-block object per
  yield, 4.75x fewer bytes) and the defect is **stronger** (in_big 30 vs 11, kept 18% vs 59%). **The
  dose series is now run on that build** (§7A.5): the transition sits between a 90x and a 172x cut,
  so base's dose is far above it and §3B's 38-90x does not reach it. What in base's churn does the
  stranding at a *given* dose is still open; the injector matched base's own kept% at base's dose,
  so the size mix is not needed to reproduce the outcome there.
- **Gap 9, parallelism** — the question is now narrower than "not re-run": §0B.6 shows the real
  startup phase has *none*, so §6A.10's added-parallelism arm describes a regime the boot batch
  never enters. What is still untested is whether parallelism matters *after* boot, once the task
  graph is live (§12).
- ~~Which configuration the [HW] symptom belongs to~~ — **answered from [SRC] the same day**
  (§1.5): the hardware test's device script runs `build_system()` itself, asserts before any
  threshold is set, and only then reports a second, unasserted line with
  `gc.threshold(32768)` applied. The board's 20,592 B is a deliberate no-threshold reading, the twin
  reproduces it, and the corpus's baseline is the one the hardware test asserts on. What remains
  untested on hardware is whether the *boot-collect scheme* moves the board the way it moves the
  twin, which needs a go-ahead and a device-script run, not a new question.
- **Gap 10, hardware** — unchanged, and no go-ahead. A GC block is 16 B there against 32 B here, so
  the "1-block objects are immune" boundary in §0B.2 falls at a different byte size on the board and
  the eligible population may be a different fraction of the whole.

## 1. The instrument

### 1.1 What it is checked against

No number in this file comes from an unvalidated instrument. The checks, all [TWIN]:

| check | result |
|---|---|
| block-map parser against synthetic fixtures, including the `(N lines all free)` abbreviation | 12/12 pass |
| map reconstruction vs the GC's own `free` and `max free sz` | exact match on every dump |
| GC's `max free sz` vs the largest bytearray actually allocatable (binary search) | agrees within 17 B |
| per-variant semantics ("removes exactly 2x668 sleeps, nothing else") | 19/19 assertions |
| determinism of the construction/setup seam | identical 10/10 runs |
| within-config repeatability | identical 3/3 runs; `noio` exact 5/5 |
| cross-harness agreement on the boot batch's chip-select count | 668 + 222 = 890 (§4.3) |

`micropython.mem_info()`'s header carries `max free sz` in blocks — the GC's own largest-free-run
figure. `mem_info(1)` prints the block map but **abbreviates two or more consecutive all-free lines
as `(N lines all free)`**, so any reconstruction must work by absolute address, not by counting
printed lines.

### 1.2 Eight instrument defects, each of which silently produced wrong numbers

Recorded because every one of these is re-enterable, and each was caught only by an explicit audit.
**Item 7 is the largest and was found last (2026-09-18); it inflates every absolute byte figure
measured before it, and is therefore stated first.**

7. **The Unix port is built with `MICROPY_PY_SYS_SETTRACE=1`, and that flag is not inert: it
   allocates a frame object *and* a code object on every bytecode entry — every call and every
   generator resume — whether or not a trace callback is installed.** [SRC] `py/vm.c:272`
   `FRAME_ENTER()` calls `py/profile.c:190` `mp_prof_frame_enter()`, which does
   `mp_obj_new_frame()` unconditionally; only the callback dispatch *after* it is gated. The rp2
   firmware never carries the flag (CLAUDE.md), so this is a twin-only cost. Found by building the
   same frozen manifest without it (`build-nosettrace`, recipe in §10) and re-pricing every node of
   the FRAM path on both binaries — the price list is byte-identical whether modules are frozen or
   source-loaded, so the difference is the flag alone.

   | node [TWIN, 32 B blocks] | settrace (every run before this item) | settrace-free | ratio |
   |---|---|---|---|
   | `await asyncio.sleep(0)` / `sleep_ms(n)` | 1,152 / 1,024-1,152 | **0** | — |
   | `await asyncio.sleep(float > 0)` | 1,312 | 32 | 41x |
   | `await` an immediate-return coroutine | 224 | 64 | 3.5x |
   | `asyncio.Lock` acquire + release | 672 | 288 | 2.3x |
   | one chip-select session, empty | 4,032 | 1,024 | 3.9x |
   | `CRC8._crc()` over 13 bytes (13 yields) | 15,424 | 160 | 96x |
   | `FRAM_SPI._write()` (5 sessions) | 33,536 | 8,192 | 4.1x |
   | `_handle_status_bytes(check_idle=True)` (12 sessions) | 91,552 | 21,728 | 4.2x |
   | one logger `setup()`, blank chunk (74 sessions) | **651,680** | **137,120** | **4.75x** |
   | one logger `setup()`, valid chunk (47 sessions) | 453,728 | 89,536 | 5.1x |

   It was found through its signature: with the flag, **every level of await chain adds 128 B to
   every yield that passes through it** (plus 224 B per call) — measured 352 B/level on a plain
   `yield from` chain with no asyncio at all, 736 B/level with four yields per leaf, exactly
   `224 + k*128`; without the flag the per-yield term is **0** and the per-call term 96 B. So a
   `sleep(0)` at the FRAM path's mean depth of 10.7 cost ~2.5 KB in the twin and costs nothing on
   the board, and a thin async wrapper layer appeared to cost ~10 KB per logger setup (§3A).

   **What survives this item unchanged:** every *count* (sessions, transfers, calls, yields,
   survivors), every *retained*-bytes figure, the call graph, the ratios between variants measured
   on the same binary, and — tested directly — **the defect itself**, which reproduces on the
   settrace-free build and is *stronger* there, with the transient population that produced it in
   the twin (frame/code objects on every call, a 28-block object per yield) entirely absent:

   | build | heapsize | survivors | in_big | kept% | largest free after |
   |---|---|---|---|---|---|
   | settrace, frozen (every earlier run) | 560k | 76 | 11 | 59 | 72,224 |
   | settrace-free, same manifest | 560k | 64 | **30** | **18** | 50,752 |
   | settrace-free | 480k | 65 | 28 | 16 | 33,440 |
   | settrace-free | 400k | 65 | 34 | 38 | 46,176 |

   The settrace-free twin is 44% full at **~455k** (113,888 B after import, 200,096 B after
   `build_system()`), against ~529k for the settrace build — §1.4's calibration is for the old
   binary. **What does not survive:** any conclusion that rested on a yield or a call *allocating*.
   Those are corrected where they stand — the ledger's O6, O8, O10 and C10, §3.2-3.4, §5, §6.1's
   r2 explanation — and §3A gives the board-faithful anatomy. Everything else in this file that
   quotes a [TWIN] byte figure from before this item should be read as "on the settrace build",
   inflated 4-5x in total and non-uniformly per node; the per-node table above is the conversion.

1. **`mem_alloc()` deltas silently undercount when a collection fires mid-window.** The weak check
   ("`free` fell and `alloc` rose") passes even when a collection has truncated the window. The
   strong check is the identity `(free_before - free_after) == (alloc_after - alloc_before)`, plus a
   heap large enough that no collection is possible. This one defect understated per-logger churn by
   **3.9x** (215,872 B reported vs 843,232 B actual).
2. **Rebinding a module attribute cannot mock a function consumers imported by name.** Every
   consumer does `from print_log import make_logger`, which binds into its own namespace at import,
   so patching `print_log.make_logger` has no effect. A "RAM-only logging" variant built that way
   measured the unmodified FRAM path. The fix is to rebind across `sys.modules` and **assert the
   count** (`rebound=8`).
3. **`micropython.const()` with an underscore-prefixed name is compile-time-inlined and is NOT a
   module attribute at runtime.** Verified directly. Five probes read
   `asy_fram_manager._STATUS_IDLE` / `asy_fram_driver._SPI_OPCODE_RDSR`, raised `AttributeError`
   inside a broad `except`, and silently diverted the setup path. Probes must inline the literals.
   (A `const()` holding a dict, e.g. `_KNOWN_PRODUCT_IDS`, *is* present — the inlining is
   scalar-only.)
4. **A no-op substitution that changes control flow is not an isolation.** No-oping the SPI transfer
   aborts the FRAM protocol (`initialized` 10 -> 1, `cs` 668 -> 1). Every substitution needs an
   audit asserting byte-identical bus work (`cs`/`xfer`/`sleep` counters) and an unchanged outcome
   (`initialized`) before its number means anything. This caught six invalid probes (s4, s6, s7,
   first t1/t2, nobus).
5. **Instrumentation that allocates perturbs what it measures.** Branch counters installed ungated
   shifted the seam by 41 KB and made one whole heap-size table incomparable. Counters must be gated
   on an `_AUDIT` flag; audit runs never produce a headline figure. Likewise a `largest_block()`
   probe must run *after* the last map dump, never before, and repeated `gc.collect()` during
   construction changes the outcome it is measuring (25,216 vs 4,896).
6. **Scenarios sharing one heap are not independent.** Sleep-cost scenarios E-G started from a
   destroyed 6.8 KB seam because A-D ran first in the same process. One process per scenario.
8. **The synthetic injector's yield-cost constant is settrace-specific.** `probe.py synth` holds the
   byte budget constant by subtracting `_YCOST = 896` per yield - the settrace build's cost of one
   `asyncio.sleep(0)`. On the settrace-free binary a yield allocates **0 B** (item 7), so every
   synth dose run there is understated by `yields x 896`: 154,112 B per logger at the default 172
   yields, which silently turns a 22,190 B dose into a refusal and base's own 843,232 B into
   689,120 B. Now an env knob (`YCOST=0` for `build-nosettrace`); §7A.5's dose series is the first
   run with it correct, and no earlier synth figure in this file was measured on that binary.

### 1.3 The metric that works, and the one that does not

**Does not work: "fraction of the seam's largest free run kept".** Non-monotonic in every dose
series (`limit_2` 54%, `limit_5` 100%, `bare_20` 63%, `bare_668` 100%). It is a placement lottery.

**Works: `in_big`** — the number of survivors (blocks free at the construction/setup seam, allocated
after it) that land *inside* the seam's largest free run. Reported alongside the absolute
largest-free-block figure.

**Single-configuration measurements cannot distinguish a remedy from phase luck.** Every headline
figure below is ensembled over two independent perturbation families:
(a) a retained bytearray of *k* GC blocks allocated at the seam — a global offset shift;
(b) *q* transient allocations per chip-select session — a phase shift distributed through the batch.
16 runs per variant. A variant is reported as robust only if it holds across both families.

### 1.4 Twin calibration

[TWIN] `-X heapsize=400k` leaves the twin **59% full** after `build_system()`; the board is **44%**
full [HW]. Fill fraction dominates contiguity, and at 400k the diagnosis *inverts* — construction
looks like the entire problem and the setup batch looks free, which is an undersizing artifact.
Sized by fill fraction instead, `560k` gives 42% full and the closest match to the board's own
largest/free ratio. **This supersedes the handover's §2.7.1 table, which cannot be reproduced at its
stated configuration.**

At 560k, the twin reproduces the board's shape:

| | largest block | largest/free |
|---|---|---|
| after import | 366,432 | 0.88 |
| after the construction phase | 178,496 | 0.54 |
| after the setup batch (as shipped) | 43,904-51,776 | 0.13 |

**For the settrace-free build (§1.2 item 7) the same fill-fraction rule gives ~455k**: 113,888 B
after import, 200,096 B after `build_system()`, against 145,120 / 232,640 for the settrace build.

**Those are `fill.py`'s *bare* figures, and `probe.py` is not bare** (2026-09-18). The probe retains
~52,700 B of its own - its imports, the wiring-plan dict, the probe arrays, and the twin
`Timer`/`WDT` fakes that `fill.py` neutralises and it does not - constant across arms and allocated
before the seam, so it shifts fill without changing what any variant does relative to another. At
455k the probe's process is therefore **55%** full, not 44%. Sizing so the *bare* system sits at the
board's 44% under the probe gives **508k** for a run ending at `build_system()` and **560k** for one
that also runs the task-starter list. §7A.8 is measured at those two, and at them the twin
reproduces the board's own largest-over-free ratio (17.5-18.2% against the board's 18.9%).

Frozen-port import cost, for reference — this is what makes a run take ~4 s instead of minutes:

| | heap cost of `import sensortask_dev` |
|---|---|
| stock port, source on `MICROPYPATH` | 541,248 B |
| frozen `src` + `ext` + `build/generated_src` | 163,648 B |
| **+ `digital_twin/` frozen too** | **136,896 B** |

Freezing `digital_twin/` is the faithful analogue, not an extra: on real hardware `machine` is in the
firmware. **Correction to the handover's §2.9.3:** the freeze manifest must include the *variant's*
manifest (`variants/standard/manifest.py`), not `$(PORT_DIR)/variants/manifest.py` — the latter omits
`extmod/asyncio`, so `import sensortask_dev` dies with `ImportError: no module named 'asyncio'`.

### 1.5 Every figure in this file is at `gc.threshold(-1)`; the firmware ships `gc.threshold(32768)`

[SRC] `buildgen/codegen.py`'s `generate_boot_entry_source()` emits `gc.threshold(32768)` into the
generated boot entry, and `scripts/build_firmware.py:112` writes that entry onto the board as
`main.py` - so a flashed unit runs the whole batch with a 32,768 B allocation threshold. The
harnesses here import `sensortask_<dev>` directly and never execute that entry, so every figure in
this file (and in the handover) was measured at `gc.threshold(-1)`, MicroPython's own default, where
a collection happens only when an allocation cannot be satisfied (§0A.1). For the legacy deployed
tree `-1` is exactly faithful: it sets no threshold and calls no `gc.collect()` anywhere [SRC].

That is the correct baseline - CLAUDE.md and `SPECIFICATION.md` I.4(e) require the native-default
case to hold on its own - but it bounds what the corpus claims: **it is the (e)-stage picture, not
the shipped one.**

[TWIN, settrace-free] `base`, one perturbation per cell:

| heap | fill after the batch | kept% at `threshold(-1)` | kept% at `threshold(32768)` |
|---|---|---|---|
| 300k | 83% | 100 (the seam's big run is already only 17,280 B) | 45 |
| 340k | 74% | 19 | 71 |
| 380k | 66% | 13 | 80 |
| **455k** (§1.4's calibration for this binary) | **55%** | **18** | **87** |
| 560k | 45% | 19 | 91 |
| 700k | 36% | 19 | 94 |

Ensembled over §1.3's 15 perturbations at 455k, `base` keeps **13 / 18 / 23%** (worst/median/best)
with the threshold off and **87 / 87 / 89%** with it on, and clears the 55% floor 0 of 15 times
against 15 of 15. Retention is identical either way (253,312 B used against 253,760); only placement
moves - survivors span 92% of the heap at `-1` and **12%** at 32,768 (§6A.7's metric). The mechanism
is §0A.1's: every collection resets the allocator's free-scan index to zero, so the next survivor
takes the lowest fitting hole instead of one above the churn's high-water mark, and at 32,768 B the
batch's own churn triggers one every few hundred allocations.

**The discrepancy this opens.** The [HW] symptom (§2.1) is largest 115,536 -> 20,592 B, i.e.
**18% kept** - which is what the twin produces with the threshold **off**, not on.

**Resolved from [SRC], 2026-09-18, and the answer is the first candidate.** The [HW] figures come
from `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py`, an isolated-driver
script that runs `build_system()` itself and never executes the generated `main.py`. It measures and
asserts **before** any threshold is set, deliberately: "a headroom figure that only holds with a
proactive threshold isn't headroom (CLAUDE.md's memory-safety ladder)". It then sets
`gc.threshold(32768)` and reports a second time, for information only - that second line is what a
production-configured board would show, and no floor is asserted against it. So the board's 20,592 B
is the `threshold(-1)` reading by design, which is exactly what the twin reproduces, and there is no
contradiction between the two. **The corpus's baseline is the same one the hardware test asserts
on**, which is the stronger statement than the one this section originally made.

The handover said the qualitative half of this first, and it belongs to it: its §2.12's "setting the
threshold *before* `build_system()` makes the twin heap look healthy - that is the threshold masking
a design defect, which is exactly the condition I.4(e) exists to detect". The device script embodies
the same rule in code. What is added here is the
quantification (the per-dose sweep in §7A.5, the fill sweep above), the [SRC] trace of where the
threshold is set and which path skips it, and the fact that the *board* figure is a no-threshold
figure rather than a production one.

---

## 2. The defect's shape

### 2.1 It is a layout defect, not a consumption defect

[HW, cited from the handover] Largest contiguous block collapsed **5.6x** (115,536 -> 20,592 B)
across WP1+WP2 while free memory fell only 16% (130,224 -> 108,736 B). Only the 80,000 B contiguity
floor fails; the 100,000 B free floor still passes. Fully deterministic — byte-identical across three
bench runs with materially different FRAM states.

### 2.2 The survivors are small, numerous, scattered, and mostly not the FRAM's

[TWIN] Map diff across the construction/setup seam, stable across repeats:

| | value |
|---|---|
| new survivors after the setup batch | 72-76 objects |
| total bytes | 3,968-4,000 B |
| mean size | 52-55 B |
| max size | 256 B |
| type mix | 55-58 generic heads, 7 dicts, 3-11 floats, 2 tuples, 1 list, **1 str/bytes** |
| spatial span | 88-98% of the heap, median gap 2,592 B between consecutive survivors |
| distinct free runs landed in | 53-63 |

**This refutes the handover's §2.4 hypothesis** that the unnamed splitters are "JSON-derived string
values inside `_cache`". There is exactly **one** str/bytes survivor in the whole batch. The bulk are
generic heads — instances, bound methods, or asyncio residue.

The `in_big` survivors have a consistent size signature across `base`, `w6` and `w10`: a cluster of
**64-byte** objects plus one **160-byte** and one **192-byte**, nearly all "other head" — the shape
of retained coroutine/generator objects.

### 2.3 Placement is the variable, not identity

[TWIN] Same build, same batch, only the logger FRAM setup I/O suppressed:

| | new survivors | mean size | landed in the big run | big run |
|---|---|---|---|---|
| as shipped | 72-76 | 55 B | **13-21** | 132,320 -> 42,880 |
| logger FRAM I/O suppressed | 65-76 | 55 B | **0** | 132,416 -> **132,416** |

Nearly the same objects, same count, same mean size, same type mix — and the big run survives
**byte for byte**, every repeat. The earliest 31 survivors are at **byte-identical addresses** with
and without FRAM. A couple of kilobytes of data, in a dozen-odd objects, destroys ~90 KB of
contiguous space.

Mechanism: **see §0A for the verified account** — this paragraph's original wording described the
allocator as a *sweep* whose position at an object's birth decided its placement, which reading
`py/gc.c` does not support. Allocation is **lowest-fit**: the hint advances only on single-block
requests and retreats on every free below it, so each allocation takes the lowest run that fits it.
The correct statement of this result is therefore: with no churn, the batch's few dozen small
permanent allocations are all satisfied out of the ~1,058 dust holes low in the heap and never reach
the big run; with the churn running, transients of the same size class are *holding* those holes at
the moment a survivor is born, and lowest-fit then has nowhere below the big run to put it.

### 2.4 The minimum sufficient dose is one

[TWIN] `limit_1` — a single FRAM-backed logger `setup()` inside the batch — is **as bad as the full
batch** (in_big 10-20, kept 28-74%). There is no partial regime: one logger's churn is already 2.6x
the free heap, enough to displace every subsequent long-lived allocation. This is why the effect is
binary in the field and never observed as a gradual degradation.

### 2.5 Position decides everything

[TWIN] Three variants doing **byte-identical work** — `cs=76`, `xfer=124`, `sleep=176`,
`initialized=2` on every counter — differing only in *when* that one logger setup runs:

| position of the one setup | kept% (q=0/1/2/3) | in_big |
|---|---|---|
| before the batch | 72/25/27/22 | 11/27/27/27 |
| **inside the batch (as shipped)** | 74/30/30/28 | 10/20/20/20 |
| **after the whole batch** | **100/100/100/100** | **0/0/0/0** |
| none at all (control) | 100/100/100/100 | 0/0/0/0 |

Run in true isolation after everything, that same setup leaves just **8 survivors, 448 B**, and keeps
the big run byte-for-byte intact. This is the only mechanism-level zero found anywhere in the
investigation.

At full dose the position fix is real but no longer perfect, and the mechanism says why: the deferred
pass runs 20 logger setups back to back, each displacing the *next* ones' own survivors (~60 B, one
small object per logger). Residual in_big 0-4.

---

## 3. The FRAM logging path, priced exactly

**Every byte figure in §3.1-3.4 is on the settrace build (§1.2 item 7) — inflated ~4x overall and
up to 96x on the CRC. The counts are exact and stand. §3A re-prices the same path node by node on
the settrace-free build and is the anatomy to use.**

### 3.1 Transaction amplification — the headline finding

[TWIN, counted with audited counters; [SRC] for the structure] One `PrintLogHistoryStore.setup()`
persists a **12-byte** record (2-byte header + 10-byte history deque) and costs **74 SPI chip-select
sessions**.

The arithmetic closes exactly, and was confirmed by independent counting:

```
setup()            = _read() on a blank chip (24 CS) + _write() (50 CS)         = 74
write_into(12 B)   = 2 copies x 5 byte-level ops x 5 CS per op                  = 50
  5 byte-level ops = 4 status flag bytes + 1 data write
  5 CS per op      = WREN, RDSR (verify WEL), WRITE, WRDI, RDSR (verify clear)
read_into (valid)  = 2 blocks x 23 CS + 1                                       = 47
```

Per-call counts for one fresh logger `setup()` [TWIN, audited, `initialized=True`]:

| call | count |
|---|---|
| `SPIDevice.__aenter__` (chip-select sessions) | **74** |
| `set_values` (byte-level FRAM writes) | 14 — of which `_set_check_sb` = **12** |
| `get_values` (data reads) | 4 |
| `_send_opcode` / `_read_status` | 28 / 28 |
| `_enable_write` / `_disable_write` | 14 / 14 |

**40 of the 50 write transactions carry four single bookkeeping flag bytes. Only 10 carry the
payload.** Each flag byte pays the identical WREN/verify/WRDI/verify envelope a real data write pays,
twice over for block redundancy — and the two flags per block are at *physically adjacent* addresses
(`st_addr + 0` and `st_addr + 1`), so they are two separate 5-session envelopes for what one 2-byte
write would cover.

Wire traffic to store 12 payload bytes: **114 bytes written, 20 read**.

**Correction to the handover's §2.5**, reported rather than silently fixed: it states the `_write()`
envelope is **6** CS sessions per byte-level write, counting `get_write_protected()` as a bus
operation. It is not — `get_write_protected()` reads a cached `_wp` or a GPIO pin and issues no SPI
traffic ([SRC] `asy_fram_driver.py:165-173`; measured `notinit=0`, so the error branch is never
taken). The envelope is **5**, and 14 x 5 + 4 = 74 closes exactly, which 6 does not.

### 3.2 The per-session atom

[TWIN] One full chip-select session, priced line by line (`asy_spi_driver.py`):

| construct | bytes | share |
|---|---|---|
| **2 x `await asyncio.sleep(0.001)`** — `__aenter__` and `__aexit__` | **3,071** | **56%** |
| the `async with` protocol itself (`__aenter__`/`__aexit__` coroutine pair) | 768 | 14% |
| `spi.configure(**5 kwargs)`, of which `machine.SPI.init`'s native kwargs map = 512 | 768 | 14% |
| `Lockable` acquire/release | ~512 | 9% |
| `cs_pin.value()` x2 (bound-method objects) | ~288 | 5% |
| bare `await` baseline, for reference | 224 | — |
| **total** | **5,501** | |

Independent cross-check: the handover's delegated [TWIN] measurement of a bare SPI CS session gave
**~5,519 B** — two instruments, 0.3% apart.

Measured as one gc-bracketed window instead of by line summation, a bare `async with self._spidev`
session costs **8,064 B** pre-commit and **4,768 B** with `f6a182d`. The ~2.5 KB difference from the
line-by-line figure is the measuring wrapper's own frames; both scopes are stated so neither is
misread.

Aggregate per-session figures, for sizing arguments:
- 843,232 B / 74 sessions = **~11,400 B per session** including the chunk and CRC layers.
- (11,727,552 - 452,320) / 890 sessions = **~12,668 B per session** across the whole boot.

### 3.3 Standalone pricing of the whole path

[TWIN] Nothing in the process but the SPI bus, `AsyFramManager`, and one 12-byte chunk. Every window
verified collection-free by the §1.2 identity.

| phase | frozen base | with `f6a182d` | CS | wire bytes |
|---|---|---|---|---|
| `asy_spi_driver.SPI` ctor | 15,904 | 15,904 | 0 | — |
| `AsyFramManager` ctor | 3,360 | 3,360 | 0 | — |
| `AsyFramManager.setup()` | 20,832 | 13,696 | 2 | 2 w / 5 r |
| `PrintLogHistoryStore` ctor (allocates the chunk) | 3,552 | 3,552 | 0 | — |
| `chunk.get_buffer()` | 1,408 | 1,408 | 0 | — |
| `chunk.read_into()` on a blank chip | 275,616 | 149,536 | 24 | 52 w / 12 r |
| **`chunk.write_into()`** | **585,728** | **336,480** | **50** | 114 w / 20 r |
| `chunk.read_into()` with valid data | 587,488 | 341,440 | 47 | 100 w / 46 r |
| `PrintLogHistoryStore.setup()` (read path) | 620,800 | 350,688 | 47 | 100 w / 46 r |
| FRAM lock acquire/release, nothing inside | 2,016 | 2,016 | 0 | — |
| bare chip-select session | 8,064 | 4,768 | 1 | 0 |
| `get_values(1 B)` | 12,000 | 8,448 | 1 | 4 w / 1 r |
| `set_values(1 B or 13 B)` — same cost either way | 50,656 | 30,336 | 5 | 9 / 21 w |
| `crc.add_into(12 B payload)` | 16,800 | 16,800 | 0 | — |

**28,040 bytes of heap churn per payload byte** (336,480 / 12) with the committed settle; 48,811
pre-commit.

`AsyFramManager` itself is the cheapest thing in the system: ctor + setup = 17 KB, less than the
`i2c1` constructor alone. **The cost is not in the manager or the driver's per-call efficiency.**

### 3.4 `crc_checks.py` yields after every single byte

[SRC] `src/crc_checks.py:36-50`:

```python
async def _crc(self, buf, crc) -> int:
    for c in buf:
        crc ^= c << self.crc_shift
        for _ in range(8): ...      # 8 shifts of work
        await asyncio.sleep(0)      # a full scheduler round-trip, per byte
```

The comment's intent (a large buffer must not stall other tasks) is the documented upstream idiom
[EXT], but applied at **1-byte granularity** on the 13-byte buffers this code actually uses.
[TWIN] `crc.add_into(12 B)` = **16,800 B**, ~1,400 B per payload byte — confirmed twice by
independent harnesses. This file is under no editing restriction.

---

## 3A. The FRAM path, file by file — call graph and cost anatomy on the settrace-free twin

Asked for as: the exact files, classes, instantiation and call graph from the top-level logger down
to the SPI bus driver, and where in that construction the high-churn / high-temporary / high-yield
pattern sits, and whether it runs along survivor creation. [SRC] for the structure, [TWIN,
settrace-free, 32 B blocks] for every byte, [SRC]-verified counts from an instrumented run for every
edge. Standalone: one `AsyFramManager`, one `PrintLogHistoryStore`, nothing else loaded.

### 3A.1 Files, classes, instantiation

| layer | file | class (base) | instances | what it owns |
|---|---|---|---|---|
| logger | `print_log.py` | `PrintLogHistoryStore(PrintLogHistory(PrintLog))` | one per module **and** one per `ConfigManager` (WP2) — 20 store-backed on `dev` | `history` deque(10), `err_count`; its `fram` chunk from `fram.get_chunk(12, crc=CRC8())` in `__init__` |
| chunk | `asy_fram_manager.py` | `AsyFramChunk(_AsyBaseFramChunk)` | one per logger | `block_addr` = the two copies, `crc`, `_op_lock` (`asyncio.Lock`), `_check_length=8` |
| buffer | `asy_fram_manager.py` / `base_classes.py` | `AsyFramChunkBuffer(LockableBuffer(Lockable))` | **one per read/write call**, from `get_buffer()` | a 13-byte `bytearray` + its own `asyncio.Lock` (never used on this path) |
| integrity | `crc_checks.py` | `CRC8(CRC_Base)` | one per chunk | `inc_crc`/`inc_count` for the incremental read check |
| manager | `asy_fram_manager.py` | `AsyFramManager` | one per device | `fram` (the chip), `allocated_size`, the chunk allocator |
| chip | `asy_fram_driver.py` | `FRAM_SPI(Lockable)` | one | `_spidev`, pre-allocated `_id_buf`/`_status_buf`/`_addr_buf` |
| bus device | `asy_spi_driver.py` | `SPIDevice(Lockable)` | one per chip | CS pin; **shares** the bus's `asyncio.Lock` |
| bus | `asy_spi_driver.py` | `SPI` | one per bus | `machine.SPI`, `async_lock` |

`framing_codecs.py` is not on this path (UART only). Every `Lockable` is an `asyncio.Lock` wrapper;
`async with` on any of them is two coroutine calls plus a Python-implemented `acquire()` generator.

### 3A.2 The call graph, with exact counts

`setup()` on a blank chunk (what the twin does every run, and the board on its first boot ever):
`_read()` fails on both blocks, then `_write()`. 74 sessions.

```
PrintLogHistoryStore.setup                                          1
+- PrintLogHistoryStore._read                                       1   get_buffer() -> AsyFramChunkBuffer
|  +- AsyFramChunk.read_into -> _AsyBaseFramChunk._read             1   async with _op_lock
|     +- _read_into (block 0), _read_into (block 1)                 2
|        +- _read_chunk                                             2   async with fram (drv lock)
|           +- _handle_status_bytes(BUSY, check_idle=True)          2
|              +- _set_check_sb  x2 (status byte 1, status byte 2)  4
|                 +- FRAM_SPI.get_values(1 B)  -> _read_address     4   1 session each
|                 +- FRAM_SPI.set_values(1 B)  -> _write            4   5 sessions each
|           (uninitialised -> return; no payload read, no IDLE reset)
+- PrintLogHistoryStore._write                                      1   get_buffer() again
   +- AsyFramChunk.write_into -> _AsyBaseFramChunk._write           1   async with _op_lock
      +- _write_chunk (block 0), _write_chunk (block 1)             2   async with fram
         +- _handle_status_bytes(BUSY, check_idle=False)            2   -> 2 x set_values(1 B)
         +- CRC8.add_into(13 B buf, 12)  -> _crc: 12 yields         2
         +- FRAM_SPI.set_values(13 B)     -> _write                 2   5 sessions
         +- _handle_status_bytes(IDLE, check_idle=False)            2   -> 2 x set_values(1 B)

FRAM_SPI._write(addr, data)   [every set_values]                   14   = 5 sessions
   get_write_protected                                             14
   _enable_write  = _send_opcode(WREN) + _wel_is_set(_read_status) 14   2 sessions
   session: write(addr buf 4 B) + write(data)                      14   1 session
   _disable_write = _send_opcode(WRDI) + _wel_is_set(_read_status) 14   2 sessions
SPIDevice.__aenter__ / __aexit__                                    74   each: Lockable -> Lock.acquire/release
   SPI.configure(5 kw) -> machine.SPI.init                          74
   SPIDevice.write -> SPI.write -> machine.SPI.write                88
   SPIDevice.readinto -> SPI.readinto -> machine.SPI.readinto       32
   asyncio.sleep(0) in __aexit__                                    74   + 24 in CRC8._crc = 98 yields
```

`setup()` on a valid chunk (the board on every boot after the first): `_read_into(block 0)` (23
sessions: 12 status BUSY-with-check, 1 payload read, 10 status IDLE) then `_compare_with(block 1)`
(24: the same with the 8-byte `_check_length` buffer taking two reads). **47 sessions, 8 byte-level
writes, 7 reads; still 44 of 47 sessions are status-byte traffic.** The twin overstates the board's
steady state by 74 vs 47.

### 3A.3 Prices per node

Each node in its own collection-free window, current `src/`, 8 reps, all identical, no collection.
Both binaries; the settrace-free column is the one that transfers to the board (in 32 B units).

| node | sessions | settrace | **settrace-free** | kept |
|---|---|---|---|---|
| `TWIN machine.Pin.value()` | | 256 | 0 | 0 |
| `TWIN machine.SPI.init(5 kw)` | | 448 | 64 | 0 |
| `TWIN machine.SPI.write(n)` / `readinto(n)` | | 864 / 1,024 | 96 / 128 | 0 |
| `await` immediate-return coroutine | | 224 | 64 | 0 |
| `await asyncio.sleep(0)` | | 1,152 | **0** | 0 |
| `asyncio.Lock` acquire + release | | 672 | 288 | 0 |
| `SPI.configure(5 kw)` (incl. twin `init`) | | 704 | 64 | 0 |
| **`SPIDevice` session, empty** | 1 | 4,032 | **1,024** | 0 |
| `SPIDevice.write(1 B)` inside a session | | 1,120 | 192 | 0 |
| `SPIDevice.readinto(1 B)` inside a session | | 1,312 | 256 | 0 |
| `FRAM_SPI._send_opcode` | 1 | 5,472 | 1,408 | 0 |
| `FRAM_SPI._read_status` | 1 | 6,720 | 1,696 | 0 |
| `FRAM_SPI._enable_write` / `_disable_write` | 2 | 12,960 | 3,296 / 3,328 | 0 |
| `FRAM_SPI._read_address(n)` (n = 1, 8, 13: identical) | 1 | 6,912 | 1,504 | 0 |
| **`FRAM_SPI._write(n)` (n = 1 or 13: identical)** | 5 | 33,536 | **8,192** | 0 |
| `get_values(1 B)` under the drv lock | 1 | 7,488 | 1,664 | 0 |
| `set_values(n)` under the drv lock | 5 | 35,136 | 8,352 | 0 |
| `CRC8.add_into(13 B, 12)` (12 yields) | 0 | 16,384 | **448** | 0 |
| `CRC8.check_inc()+run_inc(13 B)` | 0 | 19,520 | 480 | 0 |
| `_set_check_sb(check_idle=False)` | 5 | 36,288 | 8,736 | 0 |
| `_set_check_sb(check_idle=True)` | 6 | 43,936 | 10,432 | 0 |
| `_handle_status_bytes(check_idle=False)` | 10 | 74,336 | 17,664 | 0 |
| `_handle_status_bytes(check_idle=True)` | 12 | 89,888 | 21,056 | 0 |
| `_write_chunk` | 25 | 203,040 | 44,768 | 0 |
| `_read_chunk`, valid, 13 B buf / 8 B buf | 23 / 24 | 194,496 / 204,064 | 41,856 / 44,000 | 32 |
| `_read_chunk`, blank | 12 | 91,744 | 21,920 | 0 |
| `chunk._read`, valid / blank | 47 / 24 | 422,176 / 192,544 | 88,672 / 45,408 | 0 |
| `chunk._write` | 50 | 417,408 | 90,336 | 0 |
| `PrintLogHistoryStore._read`, valid / blank | 47 / 24 | 443,616 / 200,544 | 89,440 / 46,048 | 0 |
| `PrintLogHistoryStore._write` | 50 | 438,208 | 90,976 | 0 |
| **`PrintLogHistoryStore.setup()`, blank** | **74** | 651,680 | **137,120** | 0 |
| `PrintLogHistoryStore.setup()`, valid | 47 | 453,728 | 89,536 | 0 |
| `PrintLogHistoryStore(...)` constructor (`get_chunk`) | 0 | 3,200 | 1,280 | (permanent) |

The "under the drv lock" rows have the harness's own `async with drv` (1,664 / 672) subtracted.
In situ inside the real batch, three more await levels down, the same `setup()` measures
**137,184 B** — the depth tax is gone with the flag (it was 50,240 B there on the settrace build,
exactly 4 levels x 98 yields x 128).

### 3A.4 The anatomy — where the bytes are

**One chip-select session, 1,024 B:** `asyncio.Lock` acquire + release 288 (28%); the five
coroutine frames `SPIDevice.__aenter__`, `Lockable.__aenter__`, `Lock.acquire` (a generator),
`SPIDevice.__aexit__`, `Lockable.__aexit__` ~480; the two `super()` objects and their bound methods
~190; `SPI.configure` -> twin `machine.SPI.init` 64 (0 on the board, a C call); `Pin.value` 0;
**`asyncio.sleep(0)` 0**. A transfer inside it: 192 (write) / 256 (readinto) — a coroutine frame
around a C call, plus the twin's 96/128.

**One byte-level write, 8,352 B for 5 sessions:** WREN session + RDSR session + WRITE session (two
transfers) + WRDI session + RDSR session = 5 x 1,024 + 6 x 192 + 2 x 256 = 6,784; the twelve
coroutine frames of `set_values`/`_write`/`_enable_write`/`_disable_write`/2x`_send_opcode`/
2x`_wel_is_set`/2x`_read_status`/`get_write_protected`/`_setup_addr_buffer` and two
`bytearray([opcode])` make up the rest. **Identical for 1 and 13 bytes of payload.**

**One logger `setup()`, 137,120 B, by leaf work:**

| | sessions | B | share |
|---|---|---|---|
| 12 single-status-byte writes (`set_values(1 B)`) | 60 | 100,224 | **73%** |
| 2 payload writes (`set_values(13 B)`) | 10 | 16,704 | 12% |
| 4 status-byte reads (`get_values(1 B)`) | 4 | 6,656 | 5% |
| 2 CRC8 computations over 12 B (24 yields) | 0 | 896 | 0.7% |
| the seven manager/logger layers above them (frames, kwargs, two `get_buffer()`, `_op_lock`, log calls) | 0 | ~12,640 | 9% |
| of the total, twin-only (`Pin.value`, `SPI.init`, `SPI.write`, `SPI.readinto` — C on the board) | | 17,280 | 12.6% |

**Board-equivalent: ~119,840 B in this build's 32 B units.** On the RP2040 a GC block is 16 B and a
pointer 4 B, so the same objects take roughly half the bytes — order **60-70 KB per logger
`setup()`, ten of them per boot on `dev`**, in a 190 KB heap. Not measured on hardware (no
go-ahead); the count of objects transfers exactly, the bytes are an estimate.

### 3A.5 The critical path, and what the three "highs" actually are

**The path.** `_AsyBaseFramChunk._handle_status_bytes -> _set_check_sb -> FRAM_SPI.set_values ->
FRAM_SPI._write -> {_enable_write, _disable_write} -> {_send_opcode, _read_status} ->
SPIDevice.__aenter__/__aexit__` — 60 of the 74 sessions and 73% of the bytes go through it, and it
is 8 async layers deep at the session. It exists because the chunk protocol writes **two status
bytes, one at a time, before and after every block operation**, and the chip driver wraps **every**
write, however short, in its own WREN / RDSR-verify / WRITE / WRDI / RDSR-verify envelope. 12 bytes
of payload -> 14 byte-level writes -> 70 sessions; 2 of the 74 carry payload. **None of that is
redundant** — §3B.1 records what each element is for (an earlier wording here said otherwise; C12).
The 74 CS cycles are the integrity feature; what §3B shows is that the *Python* carrying them can
cost 38-90x less with the wire trace unchanged.

**"High churn"** is this: ~1 KB of asyncio bookkeeping per session x 74 sessions, plus ~200 B per
transfer. The buffers the code hoists (`_addr_buf`, `_status_buf`) are already hoisted; the
per-call `bytearray([opcode])` and `bytearray(1)` are ~64 B each. O4 (§6.2) stands: buffers are
not it. **"High temporary allocation"** is coroutine frames and `asyncio.Lock` objects — the *shape*
of the layering, not any buffer. **"High loop yield"** is real as a count (98 per setup: one per
session in `SPIDevice.__aexit__`, one per byte in `CRC8._crc`) and **costs 0 B on the real VM**; on
the board a yield is a scheduler round-trip that finds an empty queue (§0B.6) and returns — time,
not heap. The 896-1,152 B per yield, the 128 B/level depth tax and the "yields are protective"
result were all the settrace flag (§1.2 item 7).

**Along survivor creation?** No — strictly *between*. Every node's `kept` is 0 (±32 B); the whole
round trip retains 64-352 B per logger (the `initialized` flag and the restored history), 1,152 B
over all ten on `dev`. The survivors are born in the module's own code before and after the round
trip — the same sequential alternation §0B.6 established, with the settrace-free in-situ numbers:

| per module `setup()` | allocated | retained |
|---|---|---|
| module-own code before its logger's round trip | 512-800 | (live frames) |
| the logger's round trip | **137,184** | 64-352 |
| module-own code after it | 1,344-3,584 | net ~256 |
| **all ten:** logger round trips / module-own code | **1,234,656** / 36,672 | 1,152 / 3,584 |

So the FRAM path is 97% of the setup batch's allocation and 24% of its retention; the module code
is 3% of the allocation and 76% of the retention. They alternate ten times in one task.

### 3A.6 Corrections this makes to earlier sections

- §3.2's "per-session atom" and §3.3's standalone pricing are settrace figures: the atom is 1,024 B
  not 4,032; the setup 137,120 not 651,680. The session and transfer counts stand.
- §3.4: the CRC's byte-wise yield costs **448 B per 12-byte CRC** on the real VM, not 16,800. The
  yield-granularity fix is a latency fix only (12 scheduler round-trips per CRC, 24 per setup).
- O6/§8: the awaited-settle replacement removed 2 x ~32 B per session on the real VM, not 56% of
  the session — its **bus-hazard** justification (§5.1) is the whole case for it now.
- C9/§6A.8's "~12x against a required 40-100x" was computed in settrace bytes; the *ratio* is
  build-independent only if both terms scale alike, which §1.2 item 7's table shows they do not.
  Not re-derived here.

## 3B. Restructuring the FRAM path with the wire protocol held byte-identical

The owner's principle (2026-09-18): the high churn is an architectural issue — a critical-path run
should generate orders of magnitude fewer short-lived allocations, as a principle of how drivers and
protocols are built — and the storage's integrity features are not to change. This section prices
what that principle reaches with the protocol untouched. [SRC] for the structure; [TWIN,
settrace-free, board-equivalent] for the bytes; the prototype is `proto.py` (§10). Nothing here is
committed; the files are under C.3.1 (§11 item 2).

### 3B.1 What the protocol's elements are for (owner, 2026-09-18)

Recorded because §3A.5 and §11 item 2 had called parts of this redundant (C12); they are not, and no
lever below touches any of them.

- **The status bytes are a lock.** A copy is marked busy before it is written or read and idle after,
  so a copy caught mid-operation is refused rather than trusted — FRAM readout is destructive
  internally and restores afterwards, so an interrupted *read* is as unsafe as an interrupted write
  (`SPECIFICATION.md` A.4). The two bytes of the pair are written **separately, on purpose**: a
  power loss between them leaves the pair inconsistent, which `_handle_status_bytes(check_idle=True)`
  detects (`err + 2*gap`). One 2-byte write would erase that signal.
- **The two copies** exist so the last valid value can be restored when one is corrupted
  (`_read()`'s block-1 fallback and its rewrite of the bad copy).
- **The (optional) CRC** detects bus transfer errors.
- **Every CS cycle is required**: the chip acts on WREN, WRDI and a WRITE's data at the CS rising
  edge; the WREN / RDSR-verify before and WRDI / RDSR-verify after each write is the write-enable
  latch protocol (`asy_fram_driver.py`, datasheet). A byte-level write is five CS cycles because
  the chip needs five.

So a blank-chunk `setup()` is 74 CS cycles and a valid one 47 *by design*. What §3A priced as
expensive is not one of those cycles but the Python that carries each: three nested `async with`
locks, eight coroutine layers, and a coroutine object around every blocking C transfer.

### 3B.2 The invariant, and how it is checked

`proto.py` records every CS edge and every transfer (opcode, address and data bytes for writes; the
bytes read back for reads; every `machine.SPI.init`) by wrapping the twin's `machine.SPI`/`Pin`,
runs the current `src/` path and each prototype from the same chunk state, and asserts the traces
equal. Both the blank (74 CS, 342 events) and the valid (47 CS, 219 events) `setup()` traces are
**identical for every variant** below. The prototypes reimplement `_AsyBaseFramChunk`'s
status/copy/CRC/`check_length` protocol and `FRAM_SPI`'s envelope in full, not a simplified one.

Pricing: settrace-free build, each variant in its own collection-free window, 6 reps, all identical.
For the board-equivalent pass the twin's `machine.SPI.init/write/readinto` and
`FramChip.write/readinto` are replaced by allocation-free equivalents — they are C on the board — and
a raw replay of the whole 342-event trace then costs **128 B**, i.e. the fakes are out of the
figures. 32 B units; halve for the RP2040.

### 3B.3 The result

| variant | shape | blank `setup()` (74 CS) | valid `setup()` (47 CS) | one byte-level write (5 CS) |
|---|---|---|---|---|
| current `src/` | coroutine per CS cycle, per transfer, per helper; bus lock per CS cycle | 118,144 | 77,376 | 7,840 |
| **P1** | chip envelope and transfers synchronous; bus lock once per block operation; status-byte helpers still coroutines; `sleep(0)` after every byte-level command | 7,296 (**16x**) | 4,800 (16x) | **128** |
| **P2** | as P1, status-byte protocol synchronous too; one coroutine per block operation, yielding after each status-byte pair and after the payload command | **3,072 (38x)** | **1,984 (39x)** | 128 |
| P1 with one yield per block operation instead of per command | yield policy only | 7,296 (=) | 4,800 (=) | |

With the twin's fakes left in (the units §3A.3 used) the same rows read 137,216 / 22,784 / 18,560 —
the fakes are a fixed ~17 KB per setup, which is why §3A.4's board estimate stands.

**What P2's 3,072 B is:** four block operations (two blank reads, two writes) x 576 for `async with`
on an `asyncio.Lock` (two coroutine objects plus the Python `acquire()` generator; §5) = 2,304, plus
~200 B of frames per block operation. One P2 block write (25 CS) is **672 B = one lock acquisition
+ one frame**; the synchronous 5-CS envelope itself is 0 (the 128 in the table is the harness's own
coroutine). **The floor is now set entirely by lock acquisitions.** One acquisition per chunk
operation instead of per block operation — the scope the chunk's `_op_lock` already has — puts the
blank setup near **1,300 B (~90x)**; below that only the operation's own coroutine remains.

**Yields cost nothing.** P1 with 74 yields and with 6 price identically, as §5 predicts
(`asyncio.sleep(0)` allocates 0 B on the real VM). Yield granularity is therefore a **latency**
knob with no byte cost, as long as the yields sit in the one coroutine that owns the operation
rather than in coroutines of their own — a coroutine *call* is 64 B, a yield is 0.

### 3B.4 The levers, ranked by what they buy

From §3A.3's prices and the prototype:

1. **Synchronous below the lock.** Nothing under the bus lock awaits anything except the lock
   itself and the deliberate yield; the CS assert, the settle (already `time.sleep_us`), the
   transfers (blocking C calls on rp2) and the CS deassert are all synchronous work already, wrapped
   in coroutines. Per blank setup: `SPIDevice.__aenter__/__aexit__` per CS cycle 74 x 1,024 =
   75,776 (64%); `SPIDevice.write`/`readinto` as coroutines around a C call 88 x 192 + 32 x 256 =
   25,088 (21%); the coroutine frames of `FRAM_SPI`'s
   `set_values/_write/get_write_protected/_enable_write/_disable_write/_send_opcode/_read_status/
   _wel_is_set` per byte-level write 14 x ~1,400 = 19,712 (17%). One change removes all three: a
   synchronous session (`configure` + CS + settle + transfers + CS + settle) and synchronous
   `read_block`/`write_block` envelopes in the chip driver, called under a lock the *caller* holds
   once per block operation. This is P1's 16x; §7's `syncdeep` was its first rung.
2. **Status-byte protocol as plain functions.** `_handle_status_bytes`/`_set_check_sb` are
   coroutines only because their callees were. Synchronous, they cost nothing and the
   block-operation coroutine yields between them. P1 -> P2: 7,296 -> 3,072.
3. **Lock hierarchy.** Today three locks nest per block operation: the chunk's `_op_lock` (per chunk
   operation), `FRAM_SPI.asy_lock` (per block operation; `get_values`/`set_values` require it held)
   and the bus lock (per CS cycle). After lever 1 the bus lock is taken per block operation, and the
   driver lock is redundant with it once the driver's atomic unit is the block operation; one
   acquisition per *chunk* operation is the floor. Each `async with` on a lock is 576 B, so this
   decides ~3,000 vs ~1,300 B per setup. **Owner's call**: the per-CS-cycle release of the bus lock
   exists so another device on the same bus can interleave between cycles. Every device TOML has the
   FRAM alone on `spi0` (`devices/*.toml`, `[bus.spi0]`), but it is the abstraction that changes.
4. **Per-call small objects** (32-96 B each, <5% of the bytes, but the size class the model cares
   about — §0A.3): `bytearray([opcode])` in `_send_opcode`/`_read_status` (-> `bytes` constants),
   `bytearray(1)`/`bytearray([val])` in `_set_check_sb` (-> one per chunk), `temp` and its two
   memoryviews in `_compare_with` (-> per chunk), the `cb` closure and its cells in
   `_read_into`/`_compare_with` (-> state on the chunk), `AsyFramChunkBuffer` **with its own
   `asyncio.Lock`** on every `get_buffer()` call (-> one per store; its size is fixed for the store's
   life), memoryview slices per CRC call.
5. **CRC** (§11 item 1): synchronous, 448 -> ~100 B per CRC; otherwise a latency lever only.

What does not change: the on-chip layout, every byte on the bus, the order and count of CS cycles,
the status-byte semantics and every error path's meaning. The driver's failure paths today `await
self.pr.wrn_s/err_s(...)` (async because the logger persists); in the synchronous form they return
the errno up the stack and the coroutine that owns the operation logs it — the same numbers, the
same messages, logged once instead of at the leaf.

### 3B.5 What it needs, and what it does not claim

- **A scoped exception** for `asy_fram_driver.py`, `asy_fram_manager.py` and `asy_spi_driver.py`
  (CLAUDE.md; `SPECIFICATION.md` C.3.1) — §11 item 2. `SPIDevice` gains a synchronous session
  form (the async `__aenter__/__aexit__` stays for any other caller); `FRAM_SPI` gains synchronous
  `read_block`/`write_block` under a caller-held lock; `AsyFramChunk`'s public API is unchanged.
- **Bus-hazard coverage across the four tiers** (CLAUDE.md's standing rule; the change is
  bus-facing). The property the twin tier can assert is the yield policy itself — the maximum
  number of CS cycles between two yields; the flash tier is where its hold time gets measured.
- **F.3's hold-time principle.** The longest synchronous stretch is the yield policy's choice: P2's
  is one status check (6 CS: a 1-byte read and a 5-cycle write) — at 1 MHz and with the RP2040's
  per-cycle overhead, of the order of a millisecond (an estimate; no hardware go-ahead). A finer
  policy (after every 5-CS command) costs nothing in bytes.
- **It is an efficiency fix.** By the model's own account the contiguity defect is controlled by the
  size class and the churn-survivor conjunction, not by churn volume (§6A.8, §0B.4); C9 stays
  withdrawn as stated. What a 38-90x cut does to the defect is read from the §0B.4 dose series on
  the settrace-free build, which is still to be run (§0B.7). Not measured here.

## 4. Per-module census — what is different about the FRAM path

Every module constructed and set up in its own collection-free window, one process per
configuration, 64 MB heap, every window reporting the §1.2 identity as clean. SPI chip-select
sessions and raw `machine.I2C` operations counted per window.

### 4.1 Every module alone, RAM loggers (`fram=None`)

[TWIN]

| module | ctor | setup() | deferred chip init | I2C ops |
|---|---|---|---|---|
| i2c0 / i2c1 / spi0 | 10,784 / 20,096 / 14,368 | — | — | 0 |
| uart0 / uart1 | 4,096 / 4,128 | — | — | 0 |
| watchdog | 3,232 | — | — | 0 |
| conn | 13,600 | 6,368 | — | 0 |
| ntp | 7,296 | 6,816 | — | 0 |
| sysfunct | 7,328 | 6,336 | — | 0 |
| sgp40 | 8,480 | 5,760 | — | 0 |
| bmp3xx | 11,904 | 18,432 | **56,256** | 12 |
| isl29125 | 17,792 | 16,704 | **67,360** | 9 |
| scd30 | 5,472 | — | **47,936** | 4 |
| neopixel | 6,400 | — | 640 | 0 |
| notification (+ register/finalize) | 1,632 + 13,088 | 12,448 | — | 0 |
| uart_link init / resp | 6,528 / 6,624 | 8,320 / 6,368 | — | 0 |
| webserver | 29,696 | — | — | 0 |
| **whole system** | | | **452,320 B** | **25** |

### 4.2 The same modules, FRAM loggers (as shipped)

[TWIN]

| module setup() | RAM logger | FRAM, frozen base | FRAM, with `f6a182d` | SPI-CS |
|---|---|---|---|---|
| sysfunct | 6,336 | 942,720 | 493,408 | **74** |
| conn | 6,368 | 943,648 | 491,488 | **74** |
| ntp | 6,816 | 944,096 | 491,936 | **74** |
| sgp40 | 5,760 | 943,040 | 490,880 | **74** |
| bmp3xx | 18,432 | 954,816 | 503,552 | **74** |
| isl29125 | 16,704 | 954,112 | 502,848 | **74** |
| notification | 12,448 | 971,872 | 500,640 | **74** |
| uart_link init / resp | 8,320 / 6,368 | 950,048 / 955,136 | 491,488 / 491,488 | **74** each |
| scd30 / bmp3xx / isl29125 chip init | 47,936 / 56,256 / 67,360 | 963,328 / 1,038,304 / 1,055,520 | 531,008 / 538,304 / 555,520 | **74** each |
| `AsyFramManager.setup()` itself | — | 22,272 | 13,216 | **2** |
| **whole-boot total** | **452,320** | **11,727,552** | **6,338,688** | **890** |

Every module lands on **exactly 74**. The FRAM path is perfectly uniform across modules, not
concentrated in any one of them. FRAM logging multiplies total boot churn by **25.9x** as frozen,
**14.0x** with `f6a182d`.

### 4.3 The conclusion, and the cross-check that supports it

**Per-transaction cost is the same order on both buses.** FRAM SPI:
(11,727,552 - 452,320) / 890 = **~12,668 B per session**. I2C: the three chip inits spend ~171,552 B
over 25 operations = **~6,900 B per operation**.

**Transaction count is what differs, by a factor of 36.** Bringing up a real BMP390 — chip-ID check,
21 bytes of calibration coefficients, soft reset with `cmd_rdy` polling, full config — takes **12**
I2C operations. Persisting one module's 12-byte error history to FRAM takes **74** SPI sessions. Six
times the bus traffic of initialising an actual sensor chip, to store 12 bytes. Across the boot: **25
I2C operations for every sensor on the board, against 888 FRAM sessions for 12 x 12 = 144 bytes of
log history.**

Cross-harness consistency check, two independently written harnesses: the setup batch proper is
9 module setups x 74 + 2 (`fram.setup()`) = **668** CS sessions, which is exactly the `cs=668` counter
every batch-level probe reported. The three deferred sensor chip inits each pay a full logger setup
via `await self.pr.setup()`, adding 3 x 74 = 222. **668 + 222 = 890**, the solo census total.

So: not the instance size, not the layer nesting, not `asyncio` as such, and **not the FRAM
module** — one protocol shape that turns a 12-byte record into 74 bus transactions, 80% of them
bookkeeping.

---

## 5. `asyncio.sleep` allocation semantics

**Superseded on the numbers by §1.2 item 7.** Every figure in the table below is the settrace
build's. On the settrace-free build (and therefore the board), measured the same way:

| form | settrace | **settrace-free** |
|---|---|---|
| `await asyncio.sleep(0)`, `sleep_ms(0)`, `sleep_ms(1)`, `sleep_ms(50)` | 1,024-1,152 | **0 B** |
| `await asyncio.sleep(0.001)`, `sleep(0.02)` | 1,312 | 32 B (one float) |
| `await` an immediate-return coroutine | 224 | 64 B |
| `asyncio.Lock` acquire + release | 672 | 288 B |
| `async with lock: pass` | 1,216 | 576 B |

A yield allocates nothing on the real VM. The rows below that describe *retention* (obsolete once
complete, collectable) remain true trivially; the two rows about the damaging combination were
measured with settrace's 28-block sleep objects standing in for "transient churn" and describe that
object, not a yield.

[TWIN, settrace] Measured with one process per scenario (see §1.2 defect 6), windows verified collection-free.

| property | result |
|---|---|
| allocation is independent of the awaited duration | **confirmed** — 1,440 B for 0.001 / 0.005 / 0.020 s identically; 1,280 B for `sleep_ms(1)` and `sleep_ms(50)` identically |
| cost tracks the *form*, not the duration | the zero-delay form is ~128 B cheaper than its non-zero counterpart; the float form ~160 B more than the ms form |
| the allocation is obsolete once the coroutine completes | **confirmed** — retained 0.0 B per await after collection |
| it is then collectable | **confirmed** — gross 1,280-1,440 B, retained 0.0 B |
| at low frequency it does not hurt | **confirmed, but the mechanism is not rate** — the operative variable is whether a collection *intervenes*: interleaved with no collection = 2% kept, collected every 10 sleeps = 90%, every sleep = 94%, at identical sleep and object counts |
| the damaging combination is heavy transient churn interleaved with long-lived allocation | **confirmed** — sleeps alone 73%, long-lived alone 96%, phased 68%, **interleaved 2%**. **Not asyncio-specific**: identical interleaving with plain `bytearray` churn and no asyncio at all gives 9% |

### 5.1 The awaited settle was also a bus hazard

[SRC] `asyncio.sleep(t > 0)` **yields to the scheduler between CS assert and CS deassert**, so other
coroutines ran and allocated inside an open chip-select window while the bus lock was held. Against
the datasheets in `datasheets/` — MB85RS2MTA tCSU/tCSH 10 ns and tD 40 ns, MB85RS64V tD 60 ns — a
1 ms delay is **100,000x over-specified**. rp2's `mp_hal_delay_us` busy-waits on `time_us_64()`, so
`sleep_us(1)` only guarantees an elapsed time in (0, 1] us while `sleep_us(2)` guarantees >= 1 us,
still over 16x the longest requirement. This is what `f6a182d` fixes (§8).

---

## 6. Ruled out — negative results that constrain any future fix

Every entry [TWIN], audit-clean (byte-identical bus work, unchanged `initialized`), ensembled over
both perturbation families.

### 6.1 Churn volume alone does not control the outcome

**Corrected by §6A — read that first.** Every variant in this subsection reduced churn by changing
which code ran, so each also changed the allocation **size mix** and object **count**. The
factorial holds those fixed and finds churn volume *is* monotonically causal (at Y=0: 5,000 B ->
in_big 0; 160,000 B -> 3; 843,232 B -> 21). What this subsection actually establishes is narrower
and still useful: **cutting total bytes, by itself, predicts nothing**, because a change that cuts
bytes while shifting the mix toward small objects makes it worse. The ladder, each rung removing
one layer's allocations:

| rung | churn per logger setup | worst largest-free | in_big |
|---|---|---|---|
| base | 843,232 | 26,784 | 7-16 |
| r0 — twin bus+chip emulation removed (artifact, not real) | 774,240 | 24,288 | 6-18 |
| r1 — SPI transfer bodies bypassed | 743,392 | 31,040 | 5-17 |
| **r2 — the whole `async with` gone** | **214,496 (-63%)** | **23,168 — worse than base** | 13-15 |
| r3 — driver command envelope gone | 76,576 (-91%) | 58,208 | 9 |
| **r4 — chunk layer gone** | **4,896 (-99.4%)** | **105,856** | **0** |
| noio — no logger FRAM I/O at all | — | 118,336 | 0 |

Cutting 629 KB of churn per logger (r2) makes it measurably *worse*. Cutting 91% (r3) only halves the
damage. It stops only at r4, whose distinguishing feature is structure, not volume — and r4 is
equivalent to removing the churn from the batch entirely.

**Sharpest single demonstration:** `synccrc` cut churn **11.9x** to 70,720 B per logger — the lowest
of any variant doing real I/O — and measured **worse than base** (in_big 18, worst 15,168), while
`syncdeep` at 113,536 B has in_big 4. And `fix` beats `r2` decisively (in_big 3 vs 15) at nearly
identical churn, so **shape matters, not volume**.

### 6.2 Not the per-call buffer allocations

The "allocate as briefly as possible" vs "one shared buffer per instance" question, tested properly:

| variant | churn per logger | worst | median |
|---|---|---|---|
| base | 843,040 | 42,560 | 51,136 |
| t1 — driver opcode buffers hoisted (56 throwaway list+bytearray pairs per setup) | 841,248 | 39,040 | 50,176 |
| t2 — chunk status-byte buffers hoisted (24 throwaways) | 841,472 | 27,040 | 34,592 |
| t1+t2 | 839,552 (**-0.41%**) | 30,240 | 39,200 |
| all five hoists (t1+t2+s1+s2+s3) | — | **22,528 — the worst figure measured** | 34,304 |
| construction-time hoisting of every first-use allocation | — | 10,912 | — |

3,488 B saved out of 843,040 — which matches 80 throwaway pairs x ~44 B exactly. **Buffer lifetime is
0.41% of this problem**, and hoisting every per-call allocation gives the worst result of any
variant. s1/s2/s3 (hoisting `_compare_with`'s per-call `bytearray` + two memoryviews, `_read_into`'s
per-call closure, `get_buffer()`'s per-call buffer) are individually null: 22-26 KB worst, churn
unchanged.

### 6.3 Not any single component of the write path

Six overlays on the `chunkw` reproducer (a 50-CS-per-write strong reproducer, worst 15,264 — worse
than the whole real batch), then combinations, then an additive build-up from the clean baseline.
**Only w2 is clean** (in_big 0, 100% in all six perturbations). Broken: the status-byte protocol
(w1), the CRC (w3), the chunk's logging (w4), the WREN/WRDI pairs (w5), **the chip-select context
management (w6, in_big 22 deterministic)**, the transfers (w8), and every combination (w56, w9, w10 —
in_big 24 deterministic).

### 6.4 Not the await chain

Five bare awaits added to a clean configuration left it clean (w13); one left it broken (w12).
`x1` — adding *only* `await self.get_write_protected()`, with zero extra bus traffic (`cs=2`,
`xfer=4`, `sleep=524`, byte-identical) — flipped in_big from 0 to 17-22 deterministically in all six
perturbations, and that method provably does nothing but allocate a bound method and a coroutine
frame (`notinit=0`, `errs=0`, `wrns=0`: the error branch is never taken). `x2`+`x3` together measured
*better* than either alone. The bisection is non-monotonic and non-additive throughout.

### 6.5 Not heap size, and not collections during the batch

| heap | base | noio |
|---|---|---|
| 560k | broken (kept 39%) | clean, in_big 0 |
| 4M | broken (kept 20%) | clean, in_big 0 |
| 16M | broken (kept 49%, in_big 41) | clean, in_big 0 |

At 16 MB the entire 8.4 MB of batch churn fits with room to spare and the defect is undiminished.
**A prediction of mine failed here and is recorded as such**: I predicted a large heap would clear
it. It did not, and that kills the collection-stranding model (see §9).

### 6.6 Nothing composes

Every combination measured **worse than its better component**:

| combination | result | vs its components |
|---|---|---|
| CS-settle fix + deferral | 17,536 | vs 37,152 / 42,112 |
| synchronous path + deferral | 26,880 | vs 62,240 / 42,112 |
| synchronous path + CRC granularity | 15,168 | vs 62,240 / 26,528 |
| all five buffer hoists | 22,528 | vs 27,040-39,040 individually |
| construction-time hoisting | 10,912 | — |

**Consequence for any future work: a fix here must be measured, and can be silently undone by an
unrelated later change.** The system's response to a local change is not predictable from the
change's size or direction.

### 6.7 Removing the sleeps does not fix it

| variant | worst | median |
|---|---|---|
| base | 42,560 | 51,136 |
| `nosleep` (sleeps removed entirely) | 24,032 | 44,832 |
| `usleep` (`sleep_us(2)`) | 24,416 | 39,008 |
| `sleep_ms(0)` | 36,064 | 55,392 |

All three are neutral-to-worse than base on contiguity. (This baseline pair, 42,560 / 51,136, comes
from a 6-perturbation set; the 16-run both-family ensemble gives base 26,784 / 42,208. Compare
variants only within the same set.)

---

## 6A. The factorial: what actually controls it

Everything in §6 varied churn by changing *which code ran*, which changed allocation **size mix**,
object **count** and **position** at the same time. A synthetic injector separates those axes. It
replaces `PrintLogHistoryStore.setup` — the first line of every module's own `setup()`, so it sits
at exactly the real position, distributed one-per-module across the batch — with a controllable
number of transient allocations of controllable size, plus a controllable number of
`await asyncio.sleep(0)` loop yields.

Calibration, [TWIN], every window identity-verified (§1.2). `bytearray(n)` costs
`ceil(n/32)*32 + 32` — predicted and measured agree exactly at every size:

| construct | measured | predicted |
|---|---|---|
| `bytearray(32)` | 64 B (2 blk) | 64 |
| `bytearray(64)` | 96 B (3 blk) | 96 |
| `bytearray(128)` | 160 B (5 blk) | 160 |
| `bytearray(256)` | 288 B (9 blk) | 288 |
| `bytearray(512)` | 544 B (17 blk) | 544 |
| `bytearray(1024)` | 1,056 B (33 blk) | 1,056 |
| `await` an immediate-return coroutine | **224 B**, and **not** a scheduler round-trip | — |
| `await asyncio.sleep(0)` | **896 B** (28 blk) | — |

The 224 B figure independently reproduces §3.2's bare-await line item, and the 896 B figure
independently reproduces the handover's own [TWIN] value — two cross-checks on this port. Because a yield itself costs 896 B,
the filler count is reduced to compensate, so total churn stays fixed while the yield count varies.
At C = 843,232 B / Y = 172 the injector reproduces base's churn, its total loop-yield count
(9 x 172 + 2 = `sleep=1552`, identical to base) and its position, with `cs=2` — no real FRAM I/O.

### 6A.1 Synthetic small-object churn reproduces the defect

| cell | churn/logger | yields/logger | in_big (p=0/3/13) | kept% |
|---|---|---|---|---|
| A | 843,232 | 172 | 9 / 9 / 9 | 45 / 42 / 49 |
| B | 843,232 | **0** | **21 / 21 / 15** | 29 / 30 / 31 |
| C | 160,000 | 172 | **0 / 0 / 0** | 101 / 100 / 100 |
| D | 160,000 | 0 | 3 / 3 / 3 | 48 / 48 / 47 |
| E | 5,000 | 0 | 0 / 0 / 0 | 101 / 100 / 100 |
| base (real FRAM I/O) | 843,232 | 172 | 2 / 2 / 4 | 64 / 70 / 63 |
| noio | ~0 | ~0 | 0 / 0 / 0 | 100 |

Plain `bytearray(64)` churn at that position **reproduces the defect and exceeds it** — worse than
the real FRAM path. So the defect is **not FRAM-specific, not SPI-specific and not chunk-layer
specific**; the FRAM logger path is one instance of a general pattern.

### 6A.2 Allocation size is the threshold variable

Total churn 843,232 B and Y = 0 held constant; only the unit size varies, so object count varies
inversely:

| unit | cost/object | objects | in_big (p0/p3) | kept% |
|---|---|---|---|---|
| 32 B | 64 B (2 blk) | 13,175 | 21 / 21 | 30% |
| 64 B | 96 B (3 blk) | 8,783 | 21 / 19 | 30% |
| 128 B | 160 B (5 blk) | 5,270 | 21 / 17 | 30% |
| **256 B** | **288 B (9 blk)** | **2,927** | **0 / 0** | **101%** |
| 512 B | 544 B (17 blk) | 1,550 | 0 / 0 | 101% |
| 1024 B | 1056 B (33 blk) | 798 | 0 / 0 | 101% |

A sharp, reproducible knee between 5 and 9 GC blocks. **This is the binary "either heavy or none"
character observed in the field, produced by one knob.**

### 6A.3 Why: the churn and the survivors compete for the same holes

Seam free-hole histogram, [TWIN]: 1,058 small free holes totalling 6,798 blocks. What fits where:

| request | fits | holding, of the dust blocks |
|---|---|---|
| 2 blk (64 B) | **870 of 1,058 holes (82%)** | 97% |
| 5 blk (160 B) | 464 (43%) | 79% |
| 9 blk (288 B) | 226 (21%) | 56% |
| 28 blk (896 B, one `sleep(0)`) | 12 (1%) | 12% |

**The batch's own long-lived survivors are mean 52 B — about 2 blocks.** They compete for exactly
the 82% of holes that 2-3 block churn can occupy. Matched mid-churn non-collecting map dumps
confirm the occupancy directly:

| churn unit | dust-hole blocks live at a matched sample | live inside the big run |
|---|---|---|
| 32 B (2 blk) | **82%** | 0% |
| 256 B (9 blk) | **16%** | 0% |

82% measured against 82% predicted by the histogram. So: small-object churn fills the dust region,
first-fit then walks each newly-born long-lived object past it into the single large free run, and
the churn's later collection strands it there. Churn of >= 9 blocks cannot fit those holes, leaves
them free for the survivors, and the big run survives byte-for-byte.

### 6A.4 Loop yields are protective, not harmful

At constant total churn, in every perturbation: A (Y=172) in_big 9 vs B (Y=0) in_big **21**; C
(Y=172) in_big 0 vs D (Y=0) in_big 3. A yield allocates an 896 B / 28-block object that fits 1% of
the dust holes, so **every byte spent on a yield is a byte not spent filling a hole a survivor
needs.** Writing a hot path to be extra friendly to cooperative multitasking is not the aggravating
factor here; it is mildly protective at equal churn.

**This is a statement about layout only, and it must not be read as licence to remove yields.** They
carry an entirely separate, load-bearing obligation — keeping the event loop turning — and removing
them broke a real test. See §8.1.

**Re-tested without its confound, and it holds.** The table above holds *total churn* constant, so
raising the yield count lowers the small-object count (each yield costs 896 B) — the yield axis was
entangled with the one variable §6A.2 shows to be decisive. Re-run holding the **small-object count
fixed** and adding yields on top, so yields add bytes without displacing any small object:

| yields per logger | in_big at 3,000 small objects (p0/p3) | in_big at 8,783 small objects (p0/p3) |
|---|---|---|
| 0 | **21 / 21** | **15 / 13** |
| 50 | 8 / 8 | 8 / 8 |
| 200 | **4 / 4** | 6 / 6 |
| 800 | 13 / 8 | 7 / 7 |
| 3,000 | **2 / 0** | **2 / 2** |

Monotone-ish downward at both dose levels and in both perturbation families, so the protective
effect is real and not the confound. The mechanism is the same one §6A.3 measures: a yield is a
28-block allocation that fits 1% of the dust holes, so it cannot take a hole a ~2-block survivor
needs. `kept%` is noisier than `in_big` here (at 50 yields it reads worse than at 0 while in_big
reads better) — the placement lottery, §6A.10.

### 6A.5 Small-object count, total bytes held constant

Balance of the byte budget in 1024 B units, which cannot fit a dust hole:

| small (64 B) objects per logger | big units | in_big (p0/p3) | kept% |
|---|---|---|---|
| 0 / 100 / 300 / 600 / 900 / 1,500 / 3,000 | 798 → 525 | **0 / 0** throughout | 100-101% |
| 8,783 (pure small) | 0 | 11 / 15 | 42% |

Up to at least 3,000 small transients per logger setup is harmless when the byte-budget balance is
large-object churn. The mechanism behind that — left open in an earlier revision of this section —
**is now established by the sawtooth trace in §6A.7**: a large allocation fails on contiguity long
before the heap is actually full, so it forces an early, shallow collection and the fill sweep never
reaches the dust holes.

### 6A.6 The fill sawtooth, measured

`gc.mem_free()` sampled through the churn (sampling only — `mem_free()` does not collect). An upward
jump is a collection, so the trace gives the collection count, the amplitude, and how deep the fill
sweep penetrates before it is reset. Free at the seam is ~278,000 B.

| variant | free range | amplitude | collections | median pre-collection free | outcome |
|---|---|---|---|---|---|
| 32 B units (small) | **64** .. 272,640 | 272,576 | >= 29 | **1,440 B** (min **64 B**) | broken |
| 1024 B units (large) | 174,752 .. 273,920 | 99,168 | >= 89 | **220,864 B** | clean |
| 3,000 small + 525 large | 864 .. 274,016 | 273,152 | >= 68 | **191,488 B** | clean |

Small-object churn drives the heap to **64 bytes free** — it consumes literally every hole,
including every dust hole a survivor would want, and the level sawtooths across the entire free
space. Large-object churn **cannot**: a 33-block contiguous request fails on fragmentation while
~220 KB is still free in pieces too small for it, so it collects early and shallow and never claims
the dust. Amplitude alone is not the discriminator — the mixed variant's amplitude is as wild as the
small one's and it is clean. **The discriminating quantity is how deep the sweep penetrates the
small-hole population before a collection resets it**, and allocation size is the gate on that.

### 6A.7 Where the survivors end up: the spread metric

`in_big` counts only the survivors landing in the single largest seam free run. The decile
histogram of survivor addresses over the whole heap shows that is the tip of the real effect:

| variant | span of heap | in_big | survivor deciles (low -> high) |
|---|---|---|---|
| 3,000 small + large balance | **18%** | 0 | `62 16 0 0 0 0 0 0 0 0` |
| 256 B units, full volume | **40%** | 0 | `43 22 4 6 1 0 0 0 0 0` |
| noio | 67% | 0 | `26 7 1 7 7 5 23 0 0 0` |
| base (real FRAM I/O) | 96-98% | 2-9 | `27 15 9 12 3 0 1 2 6 1` |
| 32 B units, full volume | **99%** | 21 | `26 4 0 2 1 2 7 7 5 21` |

Clean variants pile the survivors into the bottom one or two deciles. Broken ones **smear them
across all ten**, with a distinct pile in the top decile where the large free run lives. Note `noio`
spans 67% with in_big 0: spread by itself is not the defect — what matters is whether the survivor
front reaches the **top** deciles, where the one usable contiguous run is.

### 6A.8 The churn budget: a step function, and it is out of reach

All-small (64 B) units, Y = 0, one campaign so the figures are mutually comparable:

| churn per logger setup | span% | in_big | top decile |
|---|---|---|---|
| 0 (`noio`) | 67% | 0 | 0 |
| 1,000 | 70% | 0 | 0 |
| 3,000 | 74% | 0 | 0 |
| 8,000 | 86% | **0** | 0 |
| **20,000** | **99%** | **13** | **13** |
| 35,000 | 95% | 6 | 6 |
| 120,000 | 97% | 18 | 18 |
| 843,232 | 97% | 13 | 13 |
| base (real) | 98% | 9 | 9 |

Below the knee the survivor front advances **gradually** (67 -> 70 -> 74 -> 86% span) without ever
reaching the big run. Above it the outcome **saturates** and shows no further dependence on volume
across a 42x range. **The knee sits between 8,000 and 20,000 B of small-object churn per logger
setup** — against base's 843,232 B, a required reduction of **40-100x**.

This is the step function behind the field observation that fragmentation was always either heavy or
absent, never partial. **§6A.11 amends where the knee comes from**: these figures are all at the
natural ~76-survivor population, and the knee moves with that population rather than being a
property of the churn. It also **retires churn reduction as a remedy**: the 74 -> ~6 chip-select
transaction reduction that §3.1's arithmetic points to is a ~12x cut, landing near 70,000 B per
logger — measured at in_big 14, span 97%, firmly inside the saturated regime. A prediction made in
an earlier session that this fix would clear the defect is **withdrawn**; the measurement says it
will not.

### 6A.9 The closing model

A long-lived object born **while** transient churn is sweeping the free space gets placed wherever
first-fit can satisfy it at that instant. The chain, every link measured:

1. Small transients (2-3 GC blocks, the same size class as the 52 B mean survivor) fit **82% of the
   1,058 dust holes** the construction phase leaves (§6A.3).
2. Enough of them therefore drive the fill sweep to the heap floor — **64 B free** — consuming every
   hole a survivor could otherwise use (§6A.6).
3. The sweep sawtooths across the whole free space, and the batch's other modules create their own
   long-lived objects at effectively random points in that cycle (the many loop yields make the
   interleaving fine-grained), so each lands at whatever height is free at that instant (§6A.7).
4. Being live, they are never moved — the GC is non-compacting — so they stay, smeared across all
   ten deciles including the top, where the only usable contiguous run is.
5. The transients are then collected, leaving those survivors stranded in what had been the big run.

The controlling quantities, in order: **transient size class relative to the survivors'** (a
threshold — >= 9 blocks is clean at any volume tested), **whether the sweep penetrates to the dust
holes** (gated by that size, and by volume up to a knee at ~8-20 KB per logger), and **whether
long-lived allocation is happening in that window at all** (position — §2.5's dose-1 result is the
only configuration reaching exact zero). Total bytes matter only through the second.

This subsumes §2.3-§2.5 and supersedes the framing in §6.1.

**Cross-campaign caveat.** The probe's own code changed between campaigns (the trace sampler, the
mixed-shape branch), which shifts the seam and therefore the placement lottery — measured directly:
the same configuration read in_big 3 in one campaign and 8 in another. Compare figures only within
the campaign that produced them; each table above is internally consistent and was reproduced across
both perturbation families.

### 6A.10 Parallelism, and why the whole thing is a lottery

**The outcome is chance plus a threshold, at every level measured.** The same configuration gives
in_big 2-20 across perturbations; two perturbation families disagree in *direction* on the same
variant; no two beneficial changes compose (§6.6). This is the most robust qualitative finding in
the investigation, and it is why every headline figure here is ensembled and why a single
configuration can never establish a remedy.

**Genuine parallelism — churn concurrent with survivor births, not merely adjacent to them.** Every
other experiment in §6A injects churn *inline*, inside a logger setup, so churn and survivor
allocation alternate at module granularity. `parplus` instead keeps the real batch completely intact
(`cs=668`, `xfer=1084`, `initialized=10` — the real FRAM logger I/O untouched, so the batch keeps
its real duration and its real await points) and adds a **concurrent churn task** on top, running
for the batch's whole duration. Ensembled over 6 perturbations, with ~5M concurrent small objects:

| | base | base + concurrent churn |
|---|---|---|
| in_big per run | 4, 6, 2, 4, 2, 2 | 0, **20**, 6, 6, 2, 3 |
| in_big worst | 6 | **20** |
| largest free block, median | 40,544 | **33,120** |
| largest free block, worst | 25,248 | 25,120 |

Added parallelism **widens the distribution and worsens the tail** (worst in_big 6 -> 20, median
largest block down 18%) while barely moving the worst case of the largest-block metric. That is the
shape of "more parallelism buys more tickets in a worse lottery".

**Stated as suggestive, not established**, for three reasons: n=6 per variant rather than the usual
16; this campaign's base runs unusually clean (in_big 2-6, against 7-16 in the larger ensembles), so
the contrast may be inflated; and the churn task retains its own objects, moving the survivor
population 69 -> 82, so it is not a pure isolation. Closing it needs the full ensemble and a design
that holds the churner's own retained objects constant.

**One factor in the conjunction remains entirely untested: the survivor population itself.** It has
been a fixed ~76 objects / ~4 KB in every run here, never varied. "More permanent reservations made
during the churn window" is a plausible fourth condition and is directly testable by injecting extra
*retained* allocations during the batch, which no experiment here does.

### 6A.11 The survivor population — the factor that explains why there is no budget

The knob: extra **retained** 64 B bytearrays per logger setup, interleaved with the churn at the
same position and in the same size class as the batch's own ~52 B survivors. Accounting audited —
`survn=25` gives `retained=225` (9 injections x 25), and the map shows 526 survivors against a
baseline 76, i.e. 225 x **2**: each retained `bytearray(64)` is two heap objects, its header and its
data buffer.

**Survivors alone** (no churn at all) do almost nothing:

| extra srv/logger | survivors | in_big | largest free |
|---|---|---|---|
| 0 | 76 | 0 | 58,336 |
| 25 | 526 | 0 | 58,304 |
| 40 | 797 | 1 | 53,536 |
| 60 | 1,156 | 1 | 49,440 |
| 90 | 1,695 | 7 | 43,424 |
| 100 | 1,877 | 5 | 47,552 |

25x the survivor population costs 18% of the largest free block — that is consumption, not a layout
collapse.

**Churn alone** at 50 small objects per logger (4,800 B — **176x below** base's 843,232 and well
under §6A.8's 8,000-20,000 B knee) is likewise harmless: in_big 0, largest free 58,304.

**Together, the same two harmless doses are catastrophic:**

| churn 4,800 B + extra srv/logger | survivors | in_big | span% | largest free |
|---|---|---|---|---|
| 0 | 76 | 0 | 78% | 58,304 |
| 10 | 257 | 0 | 84% | 58,304 |
| 25 | 525 | **0** | 85% | **58,304** |
| 40 | 795 | 7 | 91% | 47,520 |
| **60** | 1,148 | **119** | 95% | **26,144** |
| 75 | 1,426 | 164 | 97% | 13,312 |
| 90 | 1,692 | 260 | 99% | 7,328 |
| 100 | 1,866 | **390** | 98% | **6,784** |

Identical in both perturbation families at every point. Decomposed against the 58,336 B clean
baseline: churn alone **0%**, survivors alone **-18%**, both **-88%**. Neither marginal effect
predicts the joint one — a textbook interaction, and the effect at 4,800 B of churn is *worse* than
base's own 843,232 B at the natural survivor count (6,784 vs 18,400).

**This is why no churn budget exists.** The 8,000-20,000 B knee in §6A.8 is not a property of the
churn; it is a property of the **pair**. Measured at the natural ~76-survivor population it sits
there; raise the population and 4,800 B suffices. Onset in the survivor axis is equally sharp —
nothing at all up to 525 survivors, then 0 -> 7 -> 119 between 795 and 1,148. Both axes have a
threshold, and the defect needs both crossed at once, which is exactly the conjunction model in
§6A.13.

**Limit of this experiment, and the next step it names.** The knob only *adds* survivors, so the
**sub-76 regime is untested** — and that is precisely where remedy lever (b) operates (pre-allocate
each module's permanent objects at construction, so fewer are born inside the churn window). The
2D shape makes that lever look right for the first time on evidence rather than analogy, but
confirming it needs a variant that *hoists* the batch's own survivors out of the window, which is a
real code change, not a knob. Cells at 400 extra survivors per logger, and at 3,000 churn objects
with 100, are absent because they `MemoryError` — 3,600 retained bytearrays is ~230 KB on a 278 KB
free heap. Out of range by construction, not a defect, and not read as data.

### 6A.12 Survivor hoisting: the mechanism confirmed, the remedy killed

Lever (b) — allocate each module's permanent objects at construction so fewer are born inside the
churn window — was the one remedy the 2D map appeared to favour. Tested directly.

The knob only *adds* survivors, so a true hoist (moving existing ones earlier) is not expressible.
What is expressible, and is the mechanism question, is an exact A/B: **the same retained objects, the
same count, the same size class, allocated either during the window or before the seam.** The
pre-seam arm hooks `AsyFramManager.__init__`, which `build_system()` calls in its construction
phase. Containers are sized exactly and allocated in the same phase as their contents (see the
instrument note below).

**At 4,800 B of churn per logger, pre-seam placement is total protection:**

| churn 4,800 B/logger | survivors | in_big | seam_max | after_max | kept% |
|---|---|---|---|---|---|
| control | 76 | 0 | 56,576 | 57,248 | 101% |
| 225 **in-window** | 522 | 0 | 56,576 | 57,248 | 101% |
| 540 **in-window** | 1,149 | **129** | 56,576 | 29,152 | 51% |
| 900 **in-window** | 1,866 | **380** | 56,576 | 7,104 | 12% |
| 225 **pre-seam** | 76 | 0 | 32,576 | 33,248 | 102% |
| 540 **pre-seam** | 76 | 1 | 6,240 | 5,088 | 81% |
| 900 **pre-seam** | 74 | **0** | 6,240 | 6,240 | **100%** |

Identical objects, identical churn: in-window they take in_big to 380 and destroy 88% of the big
run; pre-seam they take in_big to 0 and the batch destroys **nothing**. **The mechanism is
confirmed** — a permanent object that already exists when the churn starts is not displaced by it.

**At the real churn dose, pre-seam placement protects nothing:**

| real base churn (843,232 B/logger) | survivors | in_big | seam_max | after_max | kept% |
|---|---|---|---|---|---|
| plain base | 76 | 0 / 2 | 57,440 | 57,440 / 39,072 | 100 / 68 |
| +225 **pre-seam** | 74 / 76 | 4 / 4 | 33,440 | 16,416 | **49 / 50** |
| +900 **pre-seam** | 76 | 4 / 3 | 6,240 | 3,136 | **50 / 49** |

The batch destroys about half of whatever seam it is given, regardless of when the permanent objects
were allocated. Pre-seam objects are protected at 4,800 B and unprotected at 843,232 B, which places
the protection strictly inside the low-churn regime.

**Why lever (b) cannot work, argued from the measured map.** The survivor axis has its own
threshold: nothing at all up to 525 survivors, onset between 795 and 1,148 (§6A.11). **The real
system sits at 76** — already an order of magnitude *below* its own threshold, and still broken,
because the churn axis is far *above* its threshold (843,232 B against 8,000-20,000 B). Hoisting can
only reduce an already-sub-threshold quantity, and reducing a quantity that is not the binding
constraint cannot change a saturated outcome. The two tables above are that argument's direct
evidence: the survivor axis stops mattering exactly where the churn axis saturates.

**What this leaves.** Of the three levers in §6A.9, (b) is dead and (c) — raising the transients'
size class above ~9 GC blocks — is a restatement of reducing small-object churn, which §6A.8 prices
at a required 40-100x against an achievable ~12x. **§3B has since moved the achievable side to
38-90x** (wire-identical prototype, board-equivalent); the required side is settrace arithmetic not
re-derived (§3A.6), so (c) is reopened, not resolved. **Lever (a), position, was the only candidate the
evidence supported before that**, and §2.5's dose-1 result remains the only exact zero ever measured:
byte-identical work, moved after the batch, gives 100% kept and in_big 0.

**Instrument note, a defect worth recording.** The first two attempts at this experiment were both
invalidated by their own container. Growing the retention list with `append()` reallocates its
backing array repeatedly, and each reallocation is a large transient; replacing that with a
pre-sized `[None] * 4096` was worse still — a 32 KB list allocated at import lands **inside** the
big free run and splits it, dropping the control's own seam from 56,800 to 6,368 and making every
arm incomparable. Fixed by sizing each container exactly and allocating it in the same phase as the
objects it holds, so the control allocates no container at all. The control's seam returning to
~56,500 is the check that this is clean.

### 6A.13 Scorecard against the conjunction model

The model that matches the evidence: the defect needs several conditions met at once, each with a
threshold, and above them the outcome is a heavy-tailed lottery rather than a gradient.

| candidate factor | verdict |
|---|---|
| **allocation size class** of the transients relative to the survivors | **decisive, hard threshold** (§6A.2/§6A.3) — 5 vs 9 GC blocks flips it binary at constant everything else, with 82% vs 16% dust-hole occupancy measured and predicted from the hole histogram. The sharpest single knob found |
| **churn volume** | **threshold, then saturation** (§6A.8) — gradual front advance to 8,000 B per logger, saturated from 20,000 B, then flat across a 42x range. **But the threshold is not a property of the churn**: §6A.11 shows it moves with the survivor population, and at a raised population 4,800 B is enough |
| **position** relative to long-lived allocation | **decisive** (§2.5) — the only exact zero found anywhere |
| **parallelism** (churn concurrent with survivor births) | **suggestive**: worse tail and lower median (§6A.10), not established |
| **interleaving / yield count** | **measured in the opposite direction** — protective at fixed small-object count (§6A.4), with a mechanism that explains why. Note this is a layout statement only; §8.1 is what removing yields costs |
| **survivor population size** | **confirmed, threshold, and it interacts multiplicatively with churn volume** (§6A.11) — alone -18%, with a 176x-below-knee churn dose -88%. But the real system sits at 76, an order of magnitude **below** the axis's own onset (795-1,148), so it is not the binding constraint and reducing it cannot help (§6A.12) |

## 7. Remedy candidates, measured

[TWIN] Worst case and median largest-free-block, 16 runs across both perturbation families, full
dose. Ranked.

| variant | churn per logger | worst | median | in_big |
|---|---|---|---|---|
| `noio` — no logger FRAM I/O in the batch at all | — | **118,336** | 118,336 | 0, all 16 |
| `r4` — chunk layer removed | 4,896 | 105,856 | 107,360 | 0 |
| **`syncdeep`** — synchronous SPI critical section behind the unchanged async API, `configure()` re-applied only on change | **113,536 (7.4x)** | **62,240 (2.3x)** | — | **4, deterministic all 16** |
| `last_20` — every logger's FRAM setup deferred to one pass after the batch | 843,232 | 42,112 | 78,464 | 0-4 |
| `last_14` | 843,232 | 39,296 | 70,688 | 2-6 |
| **`fix`** — the three-change CS-pattern bundle | **194,432 (4.3x)** | **37,152** | 37,216 | **3, deterministic** |
| base (as shipped) | 843,232 | 26,784 | 42,208 | 7-16 |
| `first_20` — consolidated pass **first** | 843,232 | 14,048 | 63,744 | 0-29, unstable |
| `synccrc` — synchronous path + per-256-byte CRC yield | 70,720 (11.9x) | 15,168 | — | 18 |

Full-dose `kept%` detail for the ordering variants:

| variant | kept% across the six perturbations | in_big |
|---|---|---|
| base | 41/85/43/35/45/36 | 16/8/12/11/7/12 |
| first_20 | 100/33/72/52/39/17 | 0/15/11/22/16/29 |
| last_14 | 89/50/53/71/70/85 | 4/4/4/2/6/2 |
| **last_20** | 100/100/53/100/71/80 | **0/0/2/0/4/2** |
| noio | 100/100/100/100/100/100 | 0/0/0/0/0/0 |

### 7.1 Against the 80,000 B floor

> **The floor this subsection scores against was retired by the owner on 2026-09-19 (§7G)** — it was
> a tripwire at 69% of one healthy board reading, not a demand any allocation makes, and it asked
> for a third of physical memory contiguously free. The pass/fail verdicts below are therefore
> against a criterion that no longer applies; the *relative* comparisons between arms still stand.

Absolute twin bytes do not transfer (§ unit warning), but the ratio does. The board needs
largest >= 80,000 of ~146,000 free ~= **55% of the seam's big run** [HW].

- base: median ~36% — **fails**
- `last_20`: median ~66% — clears it; **worst ~36% — still fails**

**Ordering alone is a real, mechanistically-justified improvement but does not guarantee the floor.**

### 7.2 Zero survivors was not achieved

Stated plainly: **no variant with real FRAM I/O at full dose reached zero.** ~20 variants x 16 runs
each — buffer hoisting five ways, construction-time hoisting of every first-use allocation, sleep
removal three ways, CRC granularity, the synchronous path at two depths, sync+CRC, deferral at two
positions x three doses, and five combinations. The only zero is the dose-1 ordering result (§2.5).

### 7.3 `ThreadSafeFlag` is the wrong primitive

[EXT] It exists to wake a task from an **ISR or another thread**, and **only one task may wait on
it** — so it cannot arbitrate a bus shared by several drivers. And `machine.SPI` is already
synchronous/blocking, so there is nothing to await. The documented upstream idiom is to yield only
to bound blocking time on *large* transfers. That reframes the instinct correctly: the right shape
is a **synchronous critical section with no thread at all** — which is what `syncdeep` is.

Sources: [Maximising MicroPython speed](https://docs.micropython.org/en/latest/reference/speed_python.html)
· [MicroPython constrained-environment notes](https://mpython.readthedocs.io/en/v2.2.1/reference/constrained.html)
· [micropython-async THREADING.md](https://github.com/peterhinch/micropython-async/blob/master/v3/docs/THREADING.md)
· [asyncio docs](https://github.com/micropython/micropython/blob/master/docs/library/asyncio.rst)
· [await SPI reads and writes (discussion #13054)](https://github.com/orgs/micropython/discussions/13054)

---

## 7A. The boot-confined `gc.collect()` exception, measured (owner's proposal, 2026-09-18)

The proposal in the owner's terms: the setup phase runs exactly once and lays foundations that may
never change again, so heap hygiene there is crucial; `gc.collect()` is called by the system
service's own boot list (at the start of the list, between each instantiated module, and at the
end), and the same scheme is applied to the async setup list; it stays forbidden for all business
logic and for the whole run phase, so it is called a handful of times, concentrated in boot, and
then never again.

### 7A.1 What was run

[TWIN, settrace-free, 455k, `gc.threshold(-1)` unless a row says otherwise] The generated batch is
`await X.setup()` followed by `sysfunct.feed_watchdog()`, ten times over
(`build/generated_src/sensortask_dev.py:228-247`), so `feed_watchdog()` **is** the system-service
call that sits between two modules and after the last one - wrapping it puts a collect at exactly
the proposed sites with a single wrapper. The wrapper is installed after the seam dump, so the seam
is byte-identical to `base`'s, and the start-of-list collect is already in every arm because
`hp.mapdump("seam")` collects. `gcboot` collects after every module; `gcboot2` / `gcboot5` /
`gcboot10` after every second / fifth / tenth, which is the cadence dose series.
`basex` / `gcbootx` extend the run to the async setup list: `start_and_check_tasks()`'s own starter
loop, replicated to the point where its `while True` supervisor would begin (22 tasks), without and
with a collect after each starter.

15 perturbations per variant (§1.3's two families). **Retention is unchanged across every arm** -
253,312 B used after the batch for `base` against 253,472 for `gcboot`, 207,104 B free against
206,944 - so nothing below is a consumption effect, and nothing below is the wrapper either
(`gcboot2` carries the identical wrapper and measures half the benefit).

### 7A.2 The boot list: a clean dose-response

| collects during the batch | worst | median | best | clears the 55% floor |
|---|---|---|---|---|
| 0 - `base` | 13% | 18% | 23% | **0 / 15** |
| 1, after the last module | 12% | 14% | 26% | 0 / 15 |
| 2, every fifth | 16% | 24% | 56% | 1 / 15 |
| 5, every second | 34% | 34% | 76% | 2 / 15 |
| **10, after every module** | **59%** | **60%** | **87%** | **15 / 15** |

Absolutely: worst-case largest free block 23,584 -> **104,640 B**, median 32,576 -> 104,800. **One
collect at the end achieves nothing**, which is the point - this is not about freeing garbage (every
map dump collects first anyway), it is about *when* placement is reset relative to each survivor's
birth. It is also the first variant in this file to clear that bar on **every** run rather than on
the median (§7.1, §7.2). `kept%` is a retention ratio against the seam, though, not the board's own
quantity - **§7A.8 re-does this on largest-over-free at the board's own fill, which is the figure
that answers whether the floor is met**, and the verdict there is weaker than this table looks.

### 7A.3 The async setup list

Boot list plus task-starter list, 6 perturbations per arm, same binary and heap:

| | kept, worst | kept, median | largest free block, median |
|---|---|---|---|
| `basex` | 5% | 6% | 11,296 |
| **`gcbootx`** | **40%** | **41%** | **72,032** |
| `basex`, `threshold(32768)` | 81% | 81% | 165,376 |
| `gcbootx`, `threshold(32768)` | 80% | 81% | 165,648 |

Starting the 22 tasks is itself a heavy survivor event - it takes `base` from 18% to 6% kept and
adds ~220 survivors, so the async list matters as much as the setup list. The scheme recovers a 6.4x
larger block there too, but **40% does not clear the 55% floor**: at native defaults, boot collects
alone do not make the whole boot sequence safe.

### 7A.4 It is not compaction, and the difference matters

MicroPython's collector never moves an object (§0A.1). Nothing is compacted; every survivor already
placed stays exactly where it is. What the collects change is where the *next* allocations go -
`gc_collect_end()` resets the free-scan index to zero, so each module's permanent objects take the
lowest fitting holes instead of being pushed above the churn's high-water mark. Measured as survivor
placement (§6A.7's decile histogram, k=0):

| | span | median gap | deciles, low -> high |
|---|---|---|---|
| `base` | 92% | 1,504 B | 20 5 4 2 1 5 5 13 4 5 |
| `gcboot` | 85% | 224 B | 29 7 0 0 1 0 0 0 32 0 |
| `base`, `threshold(32768)` | 12% | 320 B | 0 0 0 0 2 53 7 0 0 0 |

Two tight clusters instead of a smear. That also explains why `in_big` *rises* (26 -> 32) while the
outcome improves: the survivors sit packed at the bottom of the seam's big run rather than strewn
through it, so `in_big` counts all of them and the run above them stays whole. **`in_big` is not a
valid metric for a collecting arm** - the largest-free-block figure is, and the independent
`probe_largest` allocation agrees with it to within 24 B in every run above.

### 7A.5 What it is worth against the alternatives

Same binary, heap and 15 perturbations:

| variant | worst | median | clears the floor |
|---|---|---|---|
| `r4` - chunk layer removed (172x less churn; removes integrity features, not a candidate) | 88% | 89% | 15 / 15 |
| **`gcboot`** | **59%** | **60%** | **15 / 15** |
| `base` | 13% | 18% | 0 / 15 |
| `syncdeep` - §7's runner-up on the settrace build | 8% | 8% | 0 / 15 |

Two corrections fall out of that column. `syncdeep` measured **2.3x better than base** on the
settrace build (§7) and measures **worse than base** here, deterministically across all 15 runs:
§7's ranking is a settrace ranking and does not transfer. And the churn axis itself, re-run on this
build with the injector's yield cost corrected (§1.2 item 8) - §0B.7's named next test, now run:

| synthetic churn per logger | at `threshold(-1)` | at `threshold(32768)` |
|---|---|---|
| 843,232 B - base's own dose | 16% - 0 of 10 | 85% - 10 of 10 |
| 113,536 B - 7.4x cut (`syncdeep`'s) | 17% - 0 of 10 | 89% - 10 of 10 |
| **22,190 B - 38x cut (§3B's P2)** | **14% - 0 of 10** | 92% - 10 of 10 |
| **9,369 B - 90x cut (§3B's floor)** | **45% - 0 of 10** | 92% - 10 of 10 |
| 4,896 B - 172x cut (`r4`'s) | 68% - 10 of 10 | 94% - 10 of 10 |
| 0 | 93% - 10 of 10 | 97% - 10 of 10 |

(worst-case kept%, and how many of 10 perturbations clear the 55% floor.)

**§3B's restructure does not clear the floor at native defaults** - not at 38x, not at its own 90x
floor; the transition sits between 90x and 172x. That is C9's withdrawal confirmed by direct
measurement instead of arithmetic, and it answers §11 item 2's open question: §3B is an efficiency
fix, exactly as it claimed, and not the remedy. **At the shipped threshold the churn axis does not
bind at all** - every dose from zero to base's own clears the floor at 85-97%.

### 7A.6 Where this leaves the rule it asks to bend

`SPECIFICATION.md` I.4(e) requires the native-default case to be clean on its own, and I.4(f) makes a
`gc.threshold()` value or a `gc.collect()` call defense in depth **once (e) already holds** - "never
the fix itself, and never reached for to make a failing (e)-stage test pass". The measured effect of
this scheme is precisely and only on the (e)-stage configuration: 0 of 15 -> 15 of 15 against the
floor at `threshold(-1)`, and at the shipped `threshold(32768)` 87% -> 86% worst and 87% -> 92%
median, i.e. nothing. **That "nothing" is about B's effect measured AT a fixed threshold, and is
not the last word on the threshold itself**: §7H.3 [HW] found the shipped threshold is what carries
B's boot gain into the run phase (80% held against 12% at the reactive default), so the two are not
independent the way this paragraph's framing implies. On the evidence it **is** the (e)-stage fix I.4(f) names rather than defense in
depth on top of one, so adopting it is an amendment to I.4, not an application of it. That is a
decision (§11 item 4), not a measurement.

What would make it genuine defense in depth: a design-level fix that clears the floor at native
defaults by itself, with the boot collects added on top. The dose table above prices that at a ~172x
churn cut, against §3B's 38-90x.

### 7A.8 The decisive question: does it hold with no threshold at all?

The owner's criterion (2026-09-18): a `gc.threshold()` is a means of moving an already stable system
further from the edge and never the mechanism to rely on, so the system must work without one, and
the question is whether the boot-confined collects get it there. §7A.2's `kept%` cannot answer that
- it is a retention ratio against the seam, not the board's own quantity. The board's is **largest
contiguous over free**, and the floor is an absolute 80,000 B - a regression tripwire, not a
consumer's demand, as the paragraph below establishes.

**What the 80,000 B floor actually is, checked at source (2026-09-18).** It is not a demand from any
allocation the firmware makes. `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py`
sets `_MIN_FREE = 100_000` and `_MIN_LARGEST_BLOCK = 80_000` with the comment "Floors, not expected
values. Measured on the real dev board at MicroPython 1.29.0 (2026-09-11): free=130720,
largest_block=116032 after a full `build_system()`. These sit ~23%/~31% below that, so an ordinary
allocation-pattern change won't trip them but a real regression will." The 80,000 is therefore a
**regression tripwire at 69% of a healthy board measurement**, and the probe's shape is justified as
"the same shape a real `json.dumps()`/read buffer needs", not as an 80 KB consumer. Nothing in the firmware
allocates anywhere near it - **§7A.9 prices every reachable path: 4,096 B as configured, 16,384 B
worst case, everything else at or under 1,024 B.** The handover's §2.12 gloss - "encodes a real product property (an 80 KB
contiguous allocation must remain obtainable after boot)" - is an interpretation of that tripwire,
not something traced to a consumer, and this file had repeated it as a requirement. **What the floor
is good for is unchanged**: it is the one assertion that catches a layout regression on real
silicon, the healthy board it was calibrated against sat at largest/free = 88.8%, and today's board
sits at 18.9%. Read the rows below as distance to that tripwire, not as a prediction that a specific
allocation fails.

**Two calibrations had to be fixed first.**

- *The floor as a ratio is a range, not 55%.* §7.1's "55%" is 80,000 against ~146,000 B free. §2.1's
  own [HW] measurement has free at **108,736 B** after the batch, where the same 80,000 B is
  **74%** - which is the handover's own scaling rule (its §2.7: "the floor demands largest >= 73.6%
  of free"). Both are cited below; nothing here clears the conservative form.
- *The probe carries ~52,700 B of its own retained objects* (its imports, the wiring-plan dict, the
  probe arrays, and the twin `Timer`/`WDT` fakes `fill.py` neutralises and it does not), constant
  across arms and allocated before the seam. §1.4's "44% full at ~455k" is `fill.py`'s **bare**
  system (200,096 B retained), so at 455k the probe's own process is **55%** full, materially denser
  than the board. Sizing so the *bare* system sits at the board's 44%: **508k** after
  `build_system()`, **560k** once the task list has run too. Every figure below is at those sizes,
  with the bare fill reported so it can be checked.

[TWIN, settrace-free, `gc.threshold(-1)`, real FRAM path, 15 perturbations for the setup list and 6
for the full sequence]

| configuration | bare fill | | largest contiguous | largest / free | clears 55% |
|---|---|---|---|---|---|
| after `build_system()`, 508k | 43.7% | `base` | 30,752 - 36,992 | **11.9 - 14.2%** | 0 / 10 |
| after `build_system()`, 508k | 43.8% | **10 collects** | 115,008 - 116,560 | **44.6 - 45.0%** | 0 / 10 |
| the whole boot sequence, 560k | 42.9% | `base` | 23,648 - 24,656 | **8.1 - 8.4%** | 0 / 6 |
| the whole boot sequence, 560k | 43.0% | **32 collects** | 169,120 - 169,296 | **57.7 - 57.8%** | 6 / 6 |

(worst and median; the two collecting rows are the owner's scheme applied to the setup list alone
and to both lists.)

**The answer, stated plainly: against the tripwire, not settled and closer to "no" than to "yes";
against what the firmware actually allocates, the question does not arise** (§7A.9 - the worst
reachable allocation is 16,384 B and even the broken board covers it). The scheme is worth a factor
of 3.2 to 6.9 on the board's own metric, and it lands *on* the tripwire rather than clearly above
it - over the optimistic 55% form for the full sequence, under it after `build_system()`
alone, and under the conservative 74% form in both. `base` is nowhere near either, at 8-14%.

Two further readings of the same table. The twin at this calibration **reproduces the board's cited
ratio**: 18.9% on the board (20,592 of 108,736) against 17.5-18.2% measured here at 560k, which is
independent support for §1.5's conclusion that the [HW] symptom is the `threshold(-1)` shape. And
the task-starter list is not a footnote - it costs `base` more than the entire setup batch does
(14.2% -> 8.4%), so any scheme that stops at `build_system()` is treating the smaller half.

**What the combination looks like, with the caveat that matters.** Synthetic churn at the real setup
positions, same heap and calibration, 10 perturbations:

| synthetic churn per logger | no collects | 10 collects |
|---|---|---|
| 843,232 B - base's own dose | 15.4% | 70.0% - 10 of 10 |
| 22,190 B - §3B's 38x cut | 9.6% | 87.5% - 10 of 10 |
| 9,369 B - §3B's 90x floor | 51.1% | 87.5% - 10 of 10 |

Neither lever alone reaches the floor at its own dose; together they are far above it. **But the
injector overstates the collecting arm**: at base's own dose it gives 70.0% where the real FRAM path
gives 45.0%, a 25-point gap that does not exist in the non-collecting arm (15.4% against 14.2%). So
read the combination as *directionally* strong and not as 87%. The real number needs §3B built,
which needs §11 item 2's scoped exception; that is the measurement that would actually settle the
owner's question, and it is not available from the twin as the code stands.

### 7A.9 What the firmware's largest real contiguous allocation is [SRC]

The owner's point, 2026-09-18: nothing in the firmware comes near a third of physical memory,
contiguous or scattered, so an 80 KB requirement would be madness. Checked against the code, and it
is right. Every allocation path that can be driven from outside:

| path | largest single contiguous allocation | where |
|---|---|---|
| HTTP request body, as the project configures it | **4,096 B** | `asy_webserver_service.py:311` sets `Request.max_content_length = 4096` |
| HTTP request body, worst case actually reachable | **16,384 B** | `ext/microdot.py:425` buffers the body whenever `content_length <= Request.max_body_length`, whose 16 KB default the project never overrides; the 4 KB check runs later, in `dispatch_request` (`:1443`), so an oversized body is fully allocated and *then* answered 413 |
| static file / website asset | **1,024 B** per chunk | `ext/microdot.py:567` `send_file_buffer_size`; `style.css` is 11,257 B on disk and never held whole |
| REST GET response | streamed | `_stream_dict_response()` exists precisely so a growing dict is never one `json.dumps()` (CLAUDE.md) |
| DNS receive buffer | 512 B | `asy_dns_client.py:21` `_DNS_RECV_BUF` |
| UART frame | 53 B | `asy_uart_comm.py`, fixed by the two-implementation contract |
| FRAM chunk buffer | tens of bytes | `asy_fram_manager.py`, per chunk |

So the tripwire sits about **5x above anything the firmware can be asked to allocate**, and 20x above
the intended ceiling. Two consequences, and they point in opposite directions.

**It weakens "the defect breaks something".** At the board's own broken end (largest 20,592 B) the
worst reachable allocation still fits, with 1.26x margin, and the intended 4 KB one fits five times
over. No `MemoryError` occurred in any twin run in this file, at any variant or dose. What failed on
real hardware is an assertion calibrated to a healthy measurement, not a consumer.

**It does not make the floor pointless.** 1.26x is thin: the same degradation that took the board
from 115,536 to 20,592 B, applied once more, puts the reachable 16 KB body read at risk, and the
tripwire is what catches that a layout regression happened at all. Keep it; read a number below it
as "the heap's layout has regressed this far", not as "an allocation is failing".

> **Superseded by the owner, 2026-09-19. The 80,000 B floor is retired, not kept.** In the owner's
> own words: *"I don't know, I did not introduce it and can be removed as it does not reflect
> reality. my expectation is that there are as few survivors in the long heap and that sufficient
> contiguous gaps fit with some rather sure margin for real use, but not one third of the whole RAM
> contiguously free. Replace by more expressive tests."* So the paragraph above was arguing to keep
> a number nobody had ever asked for. What replaced it is §7G.

**Reported, not changed (CLAUDE.md's flag-don't-fix rule).** The 4,096 B cap does not bound what is
allocated, only what is answered: `Request.max_body_length` stays at microdot's 16 KB default, so a
12 KB `PUT` to any route is read into one contiguous buffer before the 413. `ext/microdot.py` is
vendored and never edited; the one-line fix belongs next to the existing
`Request.max_content_length` assignment in `asy_webserver_service.py`. Not this branch's to make -
it is a webserver change, not a heap-layout one - but it is the single allocation that decides how
much contiguity this firmware actually needs.

> **FIXED 2026-09-19 under a temporary scope extension, and this section had two errors.**
> Both caps are now 2,048 B and bound to one another, so the band is closed:
> `SPECIFICATION.md` Part I.6.
>
> **Error 1 — the table's "largest single contiguous allocation" is per-allocation, and never asked
> how many can be live at once.** `readexactly(content_length)` allocates a fresh `bytes` per
> request and `max_connections` was 4, so the real simultaneous worst case was **4 x 16,384 =
> 65,536 B** in four separate contiguous runs, against ~105,000 B free. It became 4 x 2,048 =
> 8,192 B.
>
> **Updated 2026-09-24**: `max_connections` is now **6** (SPECIFICATION.md Part H.7, evidence §7R),
> so the simultaneous worst case is
> **6 x 2,048 = 12,288 B** — still in separate contiguous runs of 2,048 B each, so the *largest
> single* allocation the firmware can be asked for is unchanged. The figure scales with the
> connection ceiling by construction, which is why raising that ceiling is a contiguity question
> and not only a socket one.
>
> **Error 2 — "the tripwire sits about 5x above anything the firmware can be asked to allocate" is
> now 16x**, because the worst reachable allocation fell to 2,048 B. §7G's thresholds are
> deliberately **not** lowered to match: they are a regression tripwire with margin, not a bare
> restatement of the requirement, and re-deriving them at 2,048 would only cost sensitivity. That
> is a choice, recorded here so it is not mistaken for the arithmetic still holding.

### 7A.7 What is not claimed

- **No hardware.** Every figure is [TWIN], and §1.5's unresolved [HW]/threshold discrepancy applies
  here too - it is the question that decides whether any of this is needed on a real unit.
- **The run phase is untouched** and unmeasured. The scheme forbids collects there, and nothing here
  tests what the heap does over months of uptime.
- **Cost, as far as it can be stated.** Ten full mark-sweeps in the boot list and 22 in the task
  list, each measured at 300-490 us over the twin's 455 KB heap on an x86-64 host. That figure does
  not transfer to the RP2040. What transfers is the shape - one mark-sweep per module, each already
  adjacent to a `sysfunct.feed_watchdog()` call - and that boot latency is explicitly not a metric to
  optimise (CLAUDE.md) while starving the watchdog is.
- **Not measured with §3B's restructure in place**, which is the configuration the project is
  heading for. §7A.5's dose table is the nearest proxy: at 38-90x less churn the native-default case
  is still below the floor, so the two levers are not redundant with each other there.

## 7B. The two remedies side by side (owner's question, 2026-09-18)

Asked for as: the gain to expect from each method, its effort and risk, the gain from both combined,
whether this is a flaw of the FRAM infrastructure or of the garbage collector, and what best practice
suggests. "A" is §3B's restructure, "B" is §7A's boot-confined collects. Every layout figure below is
at native `gc` defaults on the board's own metric (largest contiguous over free) at board-matched
fill (§7A.8); A's figures are the synthetic injector at the real positions, which tracks the
non-collecting arm to within a point and is therefore trustworthy for A alone.

### 7B.1 Gain

> **Amended by §7D.4 [HW].** This section predicted A would buy no layout gain. On real hardware it
> buys 40.2% of one. The prediction was made from [TWIN] figures taken in the cold configuration
> §7D.2 shows the defect does not appear in; B's own numbers here are still [TWIN] and unmeasured
> on silicon (§7D.8).

| | A: FRAM restructure | B: boot collects |
|---|---|---|
| layout, after `build_system()` | **P2 (38x): none** - 9.6% against base's 15.4%, worst-case kept 14% against 16%. **One lock per chunk operation (~90x): partial** - 51%, 0 of 10 clear 55% | 14.2% -> **45.0%** (3.2x), 0 of 10 clear 55% |
| layout, after the task list too | not measured | 8.4% -> **57.8%** (6.9x), 6 of 6 clear 55%, 0 of 6 clear 74% |
| against the 80,000 B tripwire at the device script's own point (after `build_system()`, 109-131 KB free on the board) | 90x: ~55-67 KB, **fails** | 45% ~ 49-59 KB, **fails** |
| gain that is certain regardless of layout | logger `setup()` 118,144 -> 3,072 B (38x) / ~1,300 (~90x) board-equivalent; ~10 MB of churn off the twin's boot; **every run-phase error persist** (`print_log.py`'s `_store_err()` -> `_write()`, 50 CS cycles) from ~80 KB to ~1.3 KB | none outside layout |
| at the shipped `threshold(32768)` | efficiency only | nothing (87% -> 86%) |

Why A's two forms differ so sharply: §6A.8's knee is 8,000-20,000 B of small-object churn per logger.
P2 lands at 22 KB, just above it, inside the saturated regime, so it buys nothing on layout; the 90x
form lands at 9.4 KB, inside the knee, and is partial. Only ~5 KB per logger (`r4`'s 172x) clears the
floor alone.

### 7B.2 Effort and risk

**A** is the expensive one: three files under C.3.1 (§11 item 2), a synchronous session form in
`SPIDevice`, synchronous `read_block`/`write_block` under a caller-held lock, the lock-hierarchy and
yield-policy decisions, bus-hazard coverage across all four tiers, and a hold-time measurement on
hardware (~1 ms synchronous stretches, estimated; F.3). It touches the storage integrity path, and
`f6a182d` already produced one regression on the same driver (§8.1). The mitigation exists:
`proto.py`'s event-for-event bus trace equality (342 / 219 events, §3B.2) is the invariant and
becomes the test. Its payoff does not depend on the layout outcome.

**B** is one line at each of two sites (the generated setup loop in `buildgen/codegen.py`, the
starter loop in `system_service.py`) plus a test that the count equals the list lengths and that none
occurs after the supervisor starts. Its risks are not in the code:

1. It amends I.4 and sets a precedent. It needs the same grep guard `method-assign` has
   (`scripts/lint.sh`), so that `gc.collect(` can exist in exactly those two sites.
2. It rests on `gc_collect_end()` resetting the free-scan index (`py/gc.c:612` at `v1.29.0`), which
   has no documented contract - though the pinned tag's own documentation recommends precisely this
   practice [SRC]: a demanded GC "is advantageous ... firstly to preempt fragmentation and secondly
   for performance", and "`gc.collect()` issued after the import will ameliorate the problem"
   (`docs/reference/constrained.rst:413-437`).
3. It dampens the tripwire. The device script runs `build_system()`, which would carry the
   collects, so a future churn regression shows ~3x weaker than it does today.
4. It does nothing for the run phase, which is months of uptime and where the identical FRAM path
   runs on every logged error.

Boot cost is 32 mark-sweeps, each next to a `feed_watchdog()`; the docs put a collection at "several
milliseconds ... about 1ms on the Pyboard", and boot latency is not a metric here (CLAUDE.md).

### 7B.3 Combined

They act on different links of §6A.9's chain, which is why they compose: B resets placement
*between* modules, A shrinks the sweep *within* a module so the survivors born mid-setup stop being
pushed above the churn's high-water mark. The proxy gives 87.5% for both 38x+collects and
90x+collects (§7A.8), but overstates the collecting arm by 25 points (70.0% against a real 45.0% at
base's dose), so the corrected expectation is **60-80% after `build_system()`**: 55% likely cleared,
74% uncertain, and on the board 66-104 KB, straddling the tripwire. It has to be built to be known.
One decision-simplifying reading: with B in place, 38x and 90x measure the same, so §3B.4's lever 3
(the lock hierarchy, the riskiest abstraction change) becomes an efficiency choice rather than a
layout one.

### 7B.4 Whose flaw

The FRAM infrastructure has a confirmed architectural inefficiency (O12): the Python around each CS
cycle costs ~40x the cycle's payload - a flaw by the owner's own principle (§3B), independent of any
GC.

The GC has no defect. It has three deliberate properties [SRC, `py/gc.c`]: it is a conservative
mark-sweep that scans the C stack and registers for anything pointer-shaped, so it *cannot* move
objects (compaction is impossible by construction, not omitted); one pool, lowest-fit, no size
classes, so small transients and small permanents share the same holes (C7); and no collection until
exhaustion at default, so the sawtooth reaches 64 B free (§6A.6). The consequence is a property, not
a bug: **a permanent object's address is decided by whatever churn is running at its birth.** The
documentation says to design around it with exactly two tools - collect at initialisation, threshold
at run - and the project already uses the second.

The actual defect is the boot design: it interleaves each module's permanent allocations with ~1 MB
of same-size-class churn on that allocator with no placement discipline. Neither party alone. What is
missing is a boot-phase contract, which is what §12's seam + contiguity guard would enforce.

### 7B.5 Recommendation

1. Grant §11 item 2 and build A on its own merits: it is the design-level fix I.4(g) prescribes, the
   only lever that reaches the run phase, and its benefit is certain. Start at P2 and leave the lock
   hierarchy alone; escalate to the 90x form only if the measurement asks for it.
2. Take §11 item 4 as boot-phase placement discipline, written narrowly into I.4: emitted only by
   the two boot lists, never a fix for an allocation that fails, confined by a lint guard. The
   grounding is the pinned documentation's own recommendation plus the measured mechanism (§7A.4).
3. Sequence them: A first, measured alone on the twin at calibrated fill and on the board against the
   unlowered 80,000 B; then B on top, measured again. That keeps the (e)/(f) record honest: if A
   alone passes the tripwire, B is pure defense in depth and needs no amendment; if not, the
   amendment states what it is.
4. Keep `threshold(32768)`. Do not lower the floor. Do not take B alone: it fails the tripwire at the
   device script's measurement point and would set the precedent without the design fix.
5. Add §12's per-module contiguity guard, which restores the sensitivity B takes from the tripwire.

---

## 7C. A, built and measured — what the real code costs (2026-09-18)

> **This section measures the build as it stood BEFORE the owner's lock-scope decision.** It takes
> the bus lock once per byte-level command, which is what made it land at 6.7x where §3B projected
> 38x; the owner then chose once per block operation (2026-09-18, §11 item 6) and the rebuild costs
> **13,696 B / 9.0x** per blank `setup()`. §7C.1's ladder is where that difference is priced. Read
> the per-node costs below as valid and the headline multiple as superseded; the wire traces are
> byte-identical at both scopes. **A + B together is §7E (twin) and §7F/§7H (silicon).**

§3B priced prototypes. This is the first measurement of the **real** restructured `src/`, built per
HEAP_REMEDIATION_PLAN.md A.1.1-A.1.3: `SPIDevice` gains a synchronous session with a blocking
`sleep_us(2)` settle, `FRAM_SPI`'s internals become plain functions over it with the bus lock taken
once per byte-level command and one `sleep(0)` after it, and the chunk layer's per-call scratch
buffers, callback closures and per-iteration slices are hoisted or removed.

Method: §3A.3's census, settrace-free binary, twin fakes first as they are and then made
allocation-free (the board-equivalent pass, §3B's own protocol), median of five, each `setup()` in
its own collection-free window. `max_size=0x40000`, so the address buffer is the 4-byte form.

| arm | blank `setup()` (74 CS) | valid `setup()` (47 CS) |
|---|---|---|
| base branch, twin fakes as-is | 141,952 | 92,640 |
| **base branch, board-equivalent** | **122,880** | **80,384** |
| A, bus lock per command, twin fakes as-is | 33,728 | 23,744 |
| A, bus lock per command, board-equivalent | 18,240 (6.7x) | 13,536 (5.9x) |
| A, bus lock per block operation, twin fakes as-is | 29,184 | 19,360 |
| **A, bus lock per block operation, board-equivalent** | **13,696 (9.0x)** | **9,152 (8.8x)** |
| §3B's P2 prototype, for reference | 3,072 (38x) | 1,984 (39x) |

The last row is the shipped shape: the owner chose per-block-operation locking (§11 item 6, closed
2026-09-18). Both A rows are the same code apart from where the bus lock is taken.

The wire protocol is byte-identical throughout — `tests/test_asy_fram_wire_trace.py` asserts every
CS cycle and every transfer's bytes against goldens captured from the pre-restructure code.

### 7C.1 Where the remaining cost is, and why it is not 38x

Per-node, board-equivalent, in the shipped per-block-operation shape:

| node | cost |
|---|---|
| bus lock acquire + release (bare `Lock`) | 288 |
| the whole synchronous 5-CS write envelope, lock already held | **32** |
| `async with FRAM_SPI` (driver lock + bus, once per block operation) | 1,152 |
| `crc.add_into()` over one chunk | 576 |
| `_write_chunk` (one block) | 3,200 |
| `_read_into` (one block) | 3,616 |
| `_compare_with` (one block) | 4,032 |

The bus work itself is now **32 B per five CS cycles** — the goal of the restructure, reached.
Everything left is await machinery. In the shipped shape a blank `setup()` is four block
operations, so the locks cost 4 x 1,152 = 4,608 B rather than the 18 x ~380 B the per-command scope
paid, and that difference — 4,544 B measured, 18,240 to 13,696 — is the whole of what the decision
bought.

The residue, roughly: ~4,600 B of block-operation locks, ~1,700 B of `_set_check_sb()`/
`_handle_status_bytes()` coroutines (18 per blank `setup()`), and the rest in the chunk layer's own
coroutines and buffers. **Two terms of an earlier version of this list were wrong and are corrected
in §7C.3**: the CRC term was given as ~2,300 B (it is ~320 B — a blank `setup()` makes exactly
**two** `_crc` calls, not fourteen) and ~5,000 B was attributed to what plan item A.7 could recover
(it recovers 288 B per operation and nothing at `setup()`).

**Why this is not §3B's 38x, and why that number was never reachable.** Two of those four residue
terms are not part of this restructure at all. `crc_checks.CRC_Base._crc` is a coroutine with an
`await` per byte; §3B's prototypes used a plain synchronous `crc8()` and so paid none of it — that
is §11 item 1 / plan item A.8, undecided. `AsyFramChunkBuffer` allocates a fresh `asyncio.Lock` on
every `get_buffer()`; the prototypes had no such buffer object — that is plan item A.7, a
consumer-side change outside these three files. And the prototypes carried **no error reporting at
all**: the real code's `wrnno`/`errno` surface is what keeps `_set_check_sb()` and
`_handle_status_bytes()` coroutines, since each of their branches logs a different message with a
different number and a persisted log entry is an await. Making them synchronous would recover
~1,700 B but only by moving those messages off their decision sites, which C.7.1's auditability
does not obviously permit; it is recorded as available, not taken.

So 38x was a prototype figure for a prototype's obligations. **9.0x is the figure for code that
keeps every guard, every number and every message**, and the part of the gap that belongs to this
work — the lock scope — is closed.

**The decision that produced the last row** was put as §11 item 6 and answered by the owner on
2026-09-18: take the bus lock once per block operation. HEAP_REMEDIATION_PLAN.md A.1.4 had chosen
per-command and priced that at "~1,800 B"; the measured cost was 4,544 B, and the ~1,800 B in
§3B.3 is the gap between per-block-operation and per-*chunk*-operation locking (lever 3), one rung
further down. Both §3B prototypes already locked per block operation, which is why neither ever
measured the per-command rung.

`FRAM_SPI.__aenter__` now takes the driver lock and the bus together, for one block operation; the
byte-level entry points gain synchronous forms (`get_values_sync()`/`set_values_sync()`) whose
status is reported by `report_get_values()`/`report_set_values()`, so the guards' numbers and
messages live in one place whichever path decided them. The chunk layer calls the synchronous forms
and yields after each status-byte pair, after the payload command, and per `check_length` slice —
§3B's P2 yield points. A second SPI device now waits for a block operation (~25 CS, ~600 us) rather
than a command (~5 CS, ~100 us); nothing else about the path changed, and the golden wire traces are
byte-identical across both scopes.

Yields still cost nothing (§5), so the loop is not starved for a block operation's duration: the
scheduling points simply moved from the driver's byte-level entry points into the block operation
that owns them, which is where §3B's P2 had them. `tests/test_asy_fram_manager.py` pins that a
concurrent task still observes a block marked BUSY and then IDLE again during one `write()`.

**Closed**: §11 item 6, answered 2026-09-18.

### 7C.2 The perturbation ensemble on the real path — no layout gain, and one instrument family invalidated

> **Superseded in its headline by §7D.4 [HW], 2026-09-18.** This section's central conclusion — that
> A buys no layout gain — is **false on real silicon**, where A improves the in-suite largest
> obtainable block by 40.2% (20,592 → 28,864 B). The reason is §7D.2: `Board.run_isolated()` never
> resets, so this ensemble's cold, single-purpose process is the configuration in which the defect
> does not exist. The twin was measuring the arm of the comparison with nothing to find. Everything
> below is still valid as a [TWIN] measurement of construction cost and of A's variance removal
> (which §7D.4 confirms on silicon); read its layout conclusions as superseded.

§7A.8's protocol, re-run with A in place: `build-nosettrace` rebuilt against the restructured
`src/` through `manifest_heap.py` (so the frozen bytecode is the shipped code, not a live-source
import whose own code objects would sit on the measured heap), `gc.threshold(-1)`, the same
calibrated heaps, `largest contiguous / free` after the batch, `hp.mapdump()`'s own `gc.collect()`
before each reading. The 508k arm is the 10 `k` perturbations §7A.8 published plus its 5 `q` runs;
the 560k arm is the 6 `k` perturbations `base` has, so the comparison is like for like.

**Only the `k` family is comparable across the two arms — `q` is not, and this had to be found
before the numbers could be read at all.** The two families (§1.3) perturb by different mechanisms:
`k` retains one `bytearray(32 * k)` **at the seam**, which is code-path independent and valid in
both arms; `q` injects `q` transient `bytearray(32)`s **inside `SPIDevice.__aenter__`**. On the base
branch `FRAM_SPI` enters that async session once per CS cycle (six `async with self._spidev` sites,
74 entries per blank logger `setup()`), so `q` fires 74 times per logger. Under A the driver takes
`self._spidev.asy_lock` directly and drives the chip through the synchronous session, so
`SPIDevice.__aenter__` **never runs on the FRAM path at all** and `q` fires **zero** times. `q`
therefore does not perturb A, and "`q` changes nothing under A" is a statement about the
instrument's hook, not about the heap. The `q` rows are reported and excluded from every comparison.

| configuration | | largest contiguous | largest / free | clears 55% |
|---|---|---|---|---|
| after `build_system()`, 508k | `base`, 10 `k` | 30,752 - 38,048 | **11.9 - 14.6%** (med 14.2) | 0 / 10 |
| after `build_system()`, 508k | **A, 10 `k`** | **31,328 - 31,328** | **12.4 - 12.5%** (med 12.4) | 0 / 10 |
| the whole boot sequence, 560k | `base`, 6 `k` | 23,648 - 24,832 | **8.1 - 8.5%** (med 8.4) | 0 / 6 |
| the whole boot sequence, 560k | **A, same 6 `k`** | **21,088 - 21,376** | **7.3 - 7.4%** (med 7.4) | 0 / 6 |
| *(reference, not comparable)* | `base`, 5 `q` | 32,800 - 60,800 | 12.8 - 23.4% | 0 / 5 |
| *(reference, not comparable)* | A, 5 `q` | 31,328 - 31,328 | 12.4% | 0 / 5 |

**A does not move the ratio, and it is slightly worse.** 12.4% against `base`'s 14.2% median after
`build_system()`, 7.4% against 8.4% after the whole sequence. §7B.1 predicted no layout gain from A
alone; that is what happened, and the small loss is real rather than noise — every one of the six
matched 560k pairs has A below `base`.

**A is less sensitive to a seam survivor, but "the lottery is gone" is too strong.** On the ten
comparable `k` runs at 508k, `base` spreads 30,752-38,048 B (1.24x) while A returns **31,328 B in
all ten**, and the perturbation is demonstrably landing (A's seam-time largest moves 219,808 →
218,016 B across `k`, its retained bytes rise monotonically). But at 560k with the task list
included, A is **not** flat: 19,264 B at `k13`, then 21,952 / 22,528 / 23,200 as `k` grows to 55,
i.e. 6.7-8.1%. So the honest statement is narrower than the one this section first carried: at
508k after `build_system()` the seam perturbation stopped moving the outcome; after the whole boot
sequence it still does. **What produced `base`'s dramatic 30,752-60,800 B swing was the `q` family**
(43,488-60,800 B on four of its five runs, against 30,752-38,048 for `k`) — a family that cannot be
compared across these arms at all. That swing is itself interesting, and consistent with §6A.4's
finding that small-object churn is protective rather than harmful, but it is not evidence about A.

**Gap, stated rather than papered over**: `base` has only the 6 `k` runs at 560k, so whether it too
drifts with larger seam survivors there is unmeasured. Closing it needs the pre-restructure frozen
binary rebuilt, which this session overwrote in place.

The cost side of A.1.3's buffer hoisting, which is where the small loss comes from:

| dump | `base` retained | A retained | delta |
|---|---|---|---|
| `import` (before any construction) | 166,624 | 167,648 | **+1,024** |
| `seam` (after construction) | 253,408 | 260,640 | **+7,232** |
| `after` (post setup batch) | 254,304 | 261,536 | **+7,232** |

All of it is construction-time: the setup batch itself retains **+896 B in both arms, identically**,
which is its own independent check that the restructure changed the batch's churn and not its
product. Of the 7,232 B, **3,200 B is measured directly** — the 20 chunks' hoisted `bytearray(1)` +
`bytearray(check_length=8)` + `memoryview`, priced by nulling the three references and collecting,
160 B per chunk — and 1,024 B is import residue from the new methods. The remaining ~3,000 B is
construction-phase and **not attributed**. One hypothesis was measured and **ruled out**: a chunk's
instance dict growing past a rehash step. The step is real (334 B per instance at ≤ 17 attributes,
430 B at ≥ 18) but `AsyFramChunk` carries exactly **17**, one below it, so it would have shown as
+1,920 B and did not.

**The measurement that actually matches the goal.** The goal is fewer long-lived survivors
scattered through the heap, not a largest/free ratio and certainly not the 80,000 B tripwire
(§7A.8, §7A.9 — a regression detector at 69% of one healthy board reading, ~5x above anything the
firmware can be asked to allocate). §6A.7's spread instrument, on the same matched runs:

| | `base` | A |
|---|---|---|
| survivors the batch leaves, whole boot sequence | 285 - 290 | **257 - 263** |
| of those, landing in the seam's big free run | 225 - 226 | **190 - 194** |
| distinct free runs they occupy | 52 - 55 | **44 - 50** |
| heap span | 97 - 98% | 99% |
| the setup batch alone, 508k | 65 | 64 - 65 |

~10% fewer survivors across the whole boot, consistent in all six matched pairs, and all of the
reduction is in the task-starter phase — the setup batch's own 65 is unchanged. The scatter is
**not** meaningfully reduced: still 44-50 distinct free runs at 99% span. And the instrument counts
only survivors born *in the batch*, so A's +7,232 B of construction-time retention is invisible to
it; on total permanent objects the two arms are close to a wash.

**Why that is the expected result, not a disappointment.** §6A.12 gives the two axes separate
thresholds. The survivor axis has onset between 795 and 1,148; the system sits at 288, an order of
magnitude below, so removing 30 survivors cannot change a saturated outcome. The binding axis is
churn, and A moved it 9.0x. §7A.8's synthetic sweep brackets the churn threshold between **9,369
B/logger (51.1%)** and **22,190 B/logger (9.6%)**, and that injector is calibrated in the
non-collecting arm (it predicted 15.4% where `base` measured 14.2%). A's real dose is **13,696
B/logger** and it measured **12.4%** — inside the bracket, on the high side, exactly where the
injector says that dose lands. Instrument and real code agree.

**So A stopped just short of a threshold whose position is now bracketed.** An earlier version of
this section then claimed A.7 and A.8 would together recover ~7,300 B and put the dose near 6,400
B/logger, below the 9,369 B point that measured 51.1%. **That is retracted** — §7C.3 measured both
items and neither recovers what was attributed to it. The residue is real, but it is not in those
two places, so there is no measured path from 13,696 B to the far side of the bracket.

**That is the honest I.4(e)/(f) record this row exists for** (HEAP_REMEDIATION_PLAN.md A.5): on the
twin, A is an allocation-count fix worth 9.0x that reduces batch survivors ~10% on an axis that is
not binding, does not reduce their scatter, and leaves the churn axis short of its own threshold.
**§7D overturns the layout half of that on silicon** — +40.2% — so the sentence that survives is the
narrower one: this ensemble could not see a layout gain because it measured a cold heap. Survivor
*scatter* is still what measure B addresses directly — §7A.4's deciles go from 20/5/4/2/1/5/5/13/4/5
at a 1,504 B median gap to 29/7/0/0/1/0/0/0/32/0 at 224 B — and §7B.5 sequences it exactly here.

*Instrument note, in §1.2's spirit.* Adding a `len(chunk.__dict__)` call to the attribution script to
count those 17 attributes inflated the hoisted-buffer figure measured immediately after it from 3,200
to 3,520 B — the `__dict__` access allocates 320 B of its own, the same artifact `mapdump_live` has.
The 3,200 B above is from the run without it.

### 7C.3 A.7 and A.8 measured, on the owner's instruction (2026-09-18)

Both were filed as "propose, don't do". The owner asked for A.7 to be measured before deciding, and
asked of A.8 whether the assumption behind it was wrong or only the means. Settrace-free binary,
live `src/`, steady state past first-instance module-init artifacts.

**A.8 — `crc_checks.CRC_Base._crc`'s `await asyncio.sleep(0)` after every byte.** The owner's reason
for it was that a CRC run in one go could stall other asyncio tasks.

| input | synchronous | per-byte yield | factor | alloc sync | alloc async |
|---|---|---|---|---|---|
| CRC8, 12 B — a `PrintLogHistoryStore` chunk | 7.5 us | 41.8 us | 5.8x | 0 B | 160 B |
| CRC8, 48 B — `asy_uart_comm`'s default payload | 29.7 us | 172.5 us | 5.8x | 0 B | 160 B |
| CRC8, 255 B — that payload's maximum | 154.6 us | 903.5 us | 5.8x | 0 B | 160 B |
| CRC32, 256 B — the SGP40 FRAM backup | 156.9 us | 910.9 us | 5.8x | 0 B | 160 B |

(x86 Unix port; the RP2040 factor is **unmeasured** — queued as a device script beside
`REAL_HARDWARE_TEST_QUEUE.md` §1A's A6.)

Three things follow. **The assumption is sound where the buffers are large**: the largest CRC input
in the system is 256 B (`VOCAlgorithm.get_params_memsize()`, CRC32, the SGP40 backup) and 255 B on
the UART, and a synchronous run over those is 2,048 inner iterations of interpreted bit-banging.
Even a conservative RP2040 factor puts that in the milliseconds, which is the same order as the
4.4 ms per-frame UART stall Part F.5.8 treats as a defect. **The means is too fine**: the yield
count scales with the buffer, so bounding each stretch at one byte costs **5.8x the total wall
time** — the loop is occupied almost six times longer to keep each stretch short. Yielding every
`N` bytes bounds the stretch just as well at a fraction of that (at N=16 the overhead is ~1.4x, not
5.8x). **And it recovers no memory**: the allocation is a flat **160 B per `_crc` call regardless of
length**, because `await asyncio.sleep(0)` allocates nothing on this build (§5) — so the per-byte
yields are free in bytes and expensive in time, the exact opposite of how this file had them priced.
A blank logger `setup()` makes **two** `_crc` calls, 12 B each, for ~320 B in total. Only making
`_crc` synchronous recovers that, and for the 256 B case the owner's original concern forbids it.
The shape the evidence points at is therefore size-dependent, not granularity-only: a synchronous
path for small buffers and a coarse-yield async path above some length.

**A.7 — `AsyFramChunkBuffer` per store instead of per `get_buffer()` call.** Prototyped by caching
one instance per chunk and re-running the real paths:

| | valid `setup()` | 10x `_write()` | 10x `_read()` |
|---|---|---|---|
| per call (today) | 96 B | 178,240 B | 191,680 B |
| per store (A.7) | 96 B | 175,360 B | 188,800 B |
| **saving** | **0 B** | **2,880 B (288 B/op)** | **2,880 B (288 B/op)** |

And the cost side, steady state: **299 B of permanent retention per buffer** (110 B of it the
`asyncio.Lock`; the first instance reads 384-1,120 B, a one-time module-init artifact that a warm-up
removes). Across the 21 FRAM-backed stores that is **~6,300 B of new permanent survivors**.

**So A.7 trades 288 B of transient churn per operation for 299 B of permanent retention per store,
roughly 1:1 by the byte** — and it saves nothing at `setup()`, which is the phase the defect lives
in. That is the same trade A.1.3's buffer hoisting already made (+7,232 B permanent, §7C.2), which
measured slightly net-negative on placement and did not reduce scatter. Permanent survivors are the
quantity the goal names. **Recommendation: do not take A.7.** The 288 B/operation is a run-phase
saving worth under 10% of a block operation's ~3,200 B, and it is not worth 21 more survivors.

---

## 7D. Measure A on real silicon — the first [HW] figures this branch produced (2026-09-18)

**Provenance: [HW] throughout.** Real `dev` bench board, real-hardware go-ahead given directly by
the project owner in the running session. This is the section §7A.7 named as missing ("No hardware.
Every figure is [TWIN] ... it is the question that decides whether any of this is needed on a real
unit") and §1.5 bounded the whole corpus against. It answers it.

### 7D.1 How the two arms were built, and why not from the merge base

`REAL_HARDWARE_TEST_QUEUE.md` A0 asked for the "before" image to come from
`claude/automated-build-chain-nuzumw`. It was built differently, deliberately, and the difference
matters for what the numbers mean.

Measure A's source changes are confined to `asy_fram_driver.py`, `asy_fram_manager.py` and
`asy_spi_driver.py`, and those three files were touched **only** by A's four implementation commits
(`7132088`, `c621cfb`, `9415902`, `8951387`) since `335479d^` = `ec13efc`. The new synchronous API
(`session_begin`/`write_sync`/`set_values_sync`/...) has zero references anywhere outside them.
So the "before" arm is **this branch's tip with exactly those three files checked out at
`ec13efc`** — isolating A, where the branch-tip form would have dragged in every unrelated merge
difference as well.

Independent evidence the two images really differ: 2,234,880 B vs 2,237,440 B (+2,560 B), and the
device script's own `baseline` heap line differs (139,008 vs 138,496 B free) before anything is
built.

### 7D.2 The defect is position-dependent, and a cold build cannot see it

The same firmware, on the same board, in the same sitting, read two completely different numbers
depending on **when in a suite** the measurement was taken:

| context | free (B) | alloc (B) | largest_block (B) |
|---|---|---|---|
| standalone `run_isolated()`, freshly flashed | 105,008 | 87,968 | **95,104** |
| inside the full flash suite | 105,216 | 87,760 | **28,864** |

`free` and `alloc` agree to within 0.2 %. **Only contiguity collapsed — by 70 %.** This is the
cleanest possible confirmation that the defect is pure layout, not consumption, and it fixes a
methodological trap: `Board.run_isolated()` (`tests_hardware/harness.py:266`) interrupts the
**already-running** firmware into the raw REPL and never resets first, so the device script builds
its graph inside whatever heap `main.py` has been living in. Freshly flashed that is seconds of
uptime; deep in a suite it is many minutes across many tests.

**Consequence: a standalone heap reading measures the wrong thing.** It is a valid controlled
comparison of two builds' construction cost, but it cannot see the defect — which is exactly why
both arms passed the 80,000 B floor standalone and both failed it in-suite.

### 7D.3 The matched in-suite pair — what A actually bought

Both arms flashed back to back, same board, same sitting, same
`scripts/run_flash_hardware_suite.sh` with no gates:

| arm | free (B) | alloc (B) | largest_block (B) |
|---|---|---|---|
| BEFORE | 108,736 | 84,240 | **20,592** |
| AFTER | 105,216 | 87,760 | **28,864** |

**The BEFORE arm reproduces the handover's 2026-09-17 reading of 20,592 B to the byte** — the same
figure §7A.9 reasons about as "the board's own broken end". That is the strongest available
evidence that the rig is in the state the defect was first found in and that the two arms are the
right comparison.

**Measure A improves the in-suite largest obtainable block by 8,272 B, +40.2 %.** The bench suite,
run separately over 38 minutes, returned 28,864 B again — byte-identical, so the figure is
deterministic given suite position, not a draw.

### 7D.4 What this confirms and what it corrects

**Confirms.** §7C.2's finding that A removes the variance holds on silicon and is if anything
stronger: the AFTER arm returned an identical 95,104 B in 4 of 5 standalone runs (range 400 B)
where BEFORE swung 1,040 B and never repeated a value.

**Corrects, and this is the substantive one.** §7B.1 and §7C.2 concluded A buys no layout gain.
On real hardware it buys 40 % of one. The twin could not see this: §7C.2's ensemble measured a
cold, single-purpose process, which §7D.2 now shows is the configuration in which the defect does
not exist. The twin was measuring the arm of the comparison that has nothing to find.

**Corrects, smaller.** §7C.2 priced A's retention at +7,232 B. On silicon the construction-seam
delta is **+3,664 B allocated / -3,632 B free** — half that. The mechanism still matches (the 20
hoisted per-chunk buffers dominate); the magnitude does not transfer, consistent with the file's
own standing unit warning that ratios transfer and absolutes do not.

**Does not change.** A does not clear the tripwire, and was never expected to (§7B.1). Read against
§7A.9's framing — the floor is a regression tripwire ~5x above anything the firmware can be asked
to allocate — the honest statement is that A moves the board's broken end from 1.26x margin over
the worst reachable 16,384 B allocation to **1.76x**. That is a real improvement in the quantity
§7A.9 says the floor is actually proxying for, and it is still not headroom.

### 7D.5 A fixed a heap-growth failure, and broke two fault injectors

Running the full flash suite on **both** arms gives direct attribution, which no single-arm run can:

| test | BEFORE | AFTER | attribution |
|---|---|---|---|
| `test_real_gc_heap_headroom_survives_a_full_system_build` | FAIL 20,592 | FAIL 28,864 | improved 40 %, not fixed |
| `test_the_link_keeps_transferring_while_every_other_subsystem_is_busy` | **FAIL** | **PASS** | ~~A fixed this~~ — **overturned, see §7H.5**: the test is marginal around its own threshold and both passes and fails on the same image |
| `test_fram_cs_pin_hijack_fault_injection_and_recovery` | PASS | **FAIL** | **A broke this** |
| `test_fram_hard_reset_race_during_write_and_recovery` | PASS | **FAIL** | **A broke this** |

Totals: BEFORE `2 failed, 34 passed, 3 skipped, 12 deselected` (844.84 s); AFTER `3 failed,
33 passed, 3 skipped, 12 deselected` (864.67 s). The bench tier on the AFTER arm: `3 failed,
90 passed, 4 skipped, 27 deselected` (2,288.40 s), the same three.

**The fix is a real one and belongs in A's ledger.** The UART crossover test fails on BEFORE with
`heap grew 3584 bytes over the last two thirds of the run under parallel load` and passes on AFTER.
That is a run-phase allocation-growth check — the phase §7A.7 lists as untouched and unmeasured —
and A closes it.

**The two breakages are broken tests, not a broken driver.** Both are GPIO-level fault injectors
whose technique depends on an await point that A removed.
`fram_cs_hijack_fault_injection_and_recovery.py`'s `cs_yanker()` does `await asyncio.sleep(0)` and
then deasserts CS, relying on being scheduled *inside* the victim's command envelope; its own
docstring says so ("whether the yanker actually ran before the victim's own `__aenter__` sleep
elapsed"). That awaited settle is precisely what `f6a182d`/A replaced with a blocking
`time.sleep_us(2)`. With no scheduling point left in the envelope the injector cannot inject, the
write completes intact, and the test reports "the hijacked write was not reliably blocked". The
reset-race test fails the same way.

So the driver is not less safe — a shorter non-yielding CS window is harder to corrupt. What was
lost is the **injection technique**. Both tests need one that does not depend on an await point (a
hardware timer IRQ, or injection from the second core). Until then they fail honestly rather than
mis-measuring, which is the better failure mode, but they cover nothing.

### 7D.6 Hold time on real wire — the number the twin structurally cannot produce

`digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time. Measured on the
real chip (queue row A6, AFTER arm):

```
HOLD write_5cs=2849us  read_1cs=772us  block_operation=21269us
```

Both are **~28-35x the working estimates** the queue and §7B carried (~100 us per command, ~600 us
per block operation).

- **Longest synchronous, non-yielding stretch: 2,849 us.** This is the F.3 number, and it is large
  enough to matter — CLAUDE.md treats the UART's measured 4.4 ms frame as a forbidden loop block,
  and this is the same order of magnitude. A 1-byte `set_values_sync()` is ~6 CS envelopes
  (`_is_write_protected` 1, `_enable_write` 2, `_send_and_write` 1, `_disable_write` 2), all now
  inside one non-yielding stretch.
- **Bus-lock hold for a block operation: 21,269 us (21.3 ms).** This is the A5 number — what a
  second SPI device would wait. No `devices/*.toml` wires one, so it stays structurally untestable
  on this rig; 21.3 ms is the closest real evidence, against the ~600 us previously assumed.

**Where the time goes, and why it corrects a stated premise.** SPI runs at 1 MHz
(`asy_spi_driver.py:57`), so six short transactions is ~300 us of actual wire time — roughly
2,550 us of the 2,849 us is MicroPython interpreter and `machine.SPI` call overhead. The 2 us CS
settle contributes ~12 us in total and is irrelevant to the result. Queue rows A6 and R7 both name
"SPI wire time under lock contention" as the dominant real term the twin omits; on this silicon the
dominant term is **interpreter overhead per transaction**, not wire time.

### 7D.7 Boot cost, for the record

`build_system()` on the AFTER arm, 5 runs: 912, 910, 957, 926, 919 ms — **median 919 ms**, spread
47 ms. Comfortably clear of the 8,388 ms watchdog cap, which is the only thing this figure is for
(boot latency is explicitly not an optimisation target, CLAUDE.md WP6).

### 7D.8 What is still not answered

- **Measure B is unmeasured on hardware.** It was built later the same day (`7ccbe8d`) and measured
  in the twin (§7E), so the A+B column of §7B.3 and §7A's whole dose-response remain [TWIN] — but the
  reason is now bench time rather than unbuilt code. The runnable form is
  `REAL_HARDWARE_HANDOVER_MEASURE_B.md` (queue §1B; **deleted 2026-09-19** once §7H migrated its
  results), which also carried the instrument §7E.3's
  fault made necessary: a device script that reaches the starter list, not just `build_system()`.
- **The `gc.threshold(32768)` question §1.5 raises is still open at the decisive point.** The
  device script reads `after_build_system` at MicroPython's reactive default and then sets 32768;
  in every run on both arms the two lines were identical, so the threshold moved nothing *at that
  instant*. That is not the same as measuring the firmware's own boot path under its own threshold
  from the start, which remains untested on hardware.
- **The run phase over months of uptime** is still untouched, exactly as §7A.7 says — though §7D.5's
  UART result is the first real-hardware evidence that A helps there.
  **Sharpened 2026-09-19 (§7F.9):** it is not only months that are untouched. On the twin the run
  phase takes back most of measure B's placement gain within about **two seconds** of the first
  tasks running, on every heap size tried, leaving A + B roughly 2x A-only rather than 5-7x. That
  makes "which position the 80,000 B floor is about" a real question rather than a pedantic one —
  §11 item 7.

## 7E. A + B on the real path — the measurement the owner's question turns on (2026-09-18)

Measure B built per HEAP_REMEDIATION_PLAN.md B.1-B.3: `buildgen/codegen.py` emits `gc.collect()`
once before the setup batch and once after each module's `feed_watchdog()` (11 for `dev`), and
`SystemService.start_and_check_tasks()` collects once before its starter loop and once after each
starter (23 for `dev`). Nowhere else. §7A.8's protocol, settrace-free frozen binary rebuilt against
this `src/` and these generated modules, `gc.threshold(-1)`, calibrated heaps, `k` perturbations
only (the `q` family is not comparable across arms — §7C.2).

| arm | after `build_system()`, 508k | the whole boot sequence, 560k |
|---|---|---|
| `base` — neither | 11.9 - 14.6% (med 14.2) | 8.1 - 8.5% (med 8.4) |
| A alone | 12.4 - 12.5% (med 12.4) | 7.3 - 7.4% (med 7.4) |
| B alone, simulated (§7A.8's `gcboot`) | 44.6 - 45.1% (med 45.0) | 57.7 - 57.9% (med 57.8) |
| **A + B, shipped** | **86.2 - 86.3%** (med 86.3) | **87.5 - 90.2%** (med 88.7) |
| clears the 55% form | **10 / 10** | **6 / 6** |
| clears the conservative 74% form | **10 / 10** | **6 / 6** |

Largest contiguous block, median: **217,680 B** after `build_system()` and **255,824 B** after the
whole sequence, against `base`'s 36,992 B and 24,656 B. **Cross-checked independently**: `hp`'s own
`probe_largest` actually allocates a `bytearray` of that size, and reports 260,248 B where the block
map said 260,256 B — an 8-byte agreement, so this is a real obtainable allocation and not a map
artifact.

**Read the 560k column as "at the end of the starter loop", not "after boot" — §7F.9.** `basex`
stops where the list stops, and the run phase that follows it carries no collect and gives most of
this gain back within about two seconds on every heap size tried. That is a statement about the
position the number names, not a retraction: at the position it does name, it is confirmed by an
independent instrument driving the real `start_and_check_tasks()`.

**§7A.8's synthetic proxy predicted 87.5% for the combination and warned it was probably
optimistic.** On the real path it is 86.3% / 88.7%. The proxy was right, and the warning was
unnecessary — the one place in this file where a prediction landed on the nose.

**The two levers compound rather than add.** A alone is worth nothing on this metric (it is even
marginally negative); B alone is worth 45-58%; together they are 86-89%. The mechanism is §0A's:
each collect resets the allocator's free-scan index, and what the *next* module then finds depends
on how much churn ran in between. A removes 9/10ths of that churn, so each reset is followed by a
clean lowest-fit placement instead of one competing with ~1 MB of same-size-class traffic. Neither
lever can produce that alone, which is why §7B.3 sequenced them together and why B alone was never
the recommendation.

### 7E.1 Survivor placement — the mechanism, confirmed on the real path

§6A.7's decile histogram, 560k, the same six perturbations:

| arm | span | median gap | survivors | deciles, low → high |
|---|---|---|---|---|
| `base` | 98% | 160 B | 288 | 26 3 0 8 21 67 13 65 39 46 |
| A alone | 99% | 192 B | 261 | 27 4 0 0 33 58 49 18 26 46 |
| **A + B** | **53 - 55%** | 256 B | 246 - 258 | **60 44 12 14 50 66 0 0 0 0** |

**Zero survivors in the top four deciles, against `base` putting 150 of 288 there.** The span more
than halves. That is exactly §7A.4's predicted shape — survivors packed low, the top of the heap
left whole — now measured on the real code rather than on an injector.

Two caveats, both in §7A.4's own terms. `in_big` falls (226 → ~15) and `distinct` rises (53 →
~157): **neither is a valid metric for a collecting arm**, because the survivors now sit low among
the seam's many small free runs rather than strewn through its one big one. The largest-contiguous
figure and the independent allocation probe are the metrics that mean something here.

### 7E.2 At the shipped `gc.threshold(32768)`, for the (f)-stage record

| arm | after `build_system()`, 508k | the whole boot sequence, 560k |
|---|---|---|
| **A + B** | **95.9 - 96.2%** (med 95.9) | **94.8 - 96.2%** (med 95.5) |
| B alone, simulated | 91.4 - 91.5% (med 91.4) | — |

§7A.6 said the collects change nothing measurable at the shipped threshold, and that still reads
correctly as a statement about *B alone* — the threshold already does most of B's work. What is new
is that A + B is 4-5 points above B alone here too, and that both configurations clear every form of
the floor with wide margin. **The honest framing for I.4 is unchanged**: this scheme earns its place
at the (e) stage, where it is worth 6x, and the threshold remains additive margin on top rather than
the thing that makes the system safe.

### 7E.2a Two things this measurement does not cover, stated rather than implied

**The gap between the two lists.** The real generated `main()` runs `sysfunct.start_timers()` and
`await ntp.ntp_force_sync()` *between* `build_system()` and `start_and_check_tasks()` — so the
firmware has a third stretch of boot, carrying a real NTP round trip, with no collect in it.
B's design (B.1) covers the two lists and deliberately nothing else, and widening it would widen
I.4(f.1)'s exception, which is not this measure's call to make. Recorded as an observation: if a
later measurement finds survivors born in that gap, the question reopens as its own decision.

**`probe.py`'s `basex` skips both of those calls**, so the 560k arm measures
`build_system()` + the starter loop and not the real boot in full. That deviation is identical in
every arm compared here (`base`, A, B, A+B), so the comparison holds; what it means is that 88.7%
is the figure for those two lists, not a prediction of what a board reads after a complete boot.
§7D.2 is the standing warning on that distinction from the hardware side.

### 7E.3 One instrument correction this measurement needed first

The first 560k run returned **10.1%**, wildly inconsistent with 86.3% at 508k. The cause was the
instrument, not the code: `probe.py`'s `basex` mode **replicates** `start_and_check_tasks()`'s
starter loop inline (to stop before its `while True` supervisor) rather than calling the method, so
it never reached B's second collect site at all — that arm measured A plus the batch collects only.
A `BSTART=1` switch now makes the replicated loop collect where the shipped method does, without
also installing the batch collects `GCBOOT=1` adds (which would double the real ones). The 10.1%
row is worth keeping as the measurement of *B's first site alone*, and it is the sharpest evidence
that **the task-starter list is where most of B's value is**: batch collects alone take the full
sequence from 8.4% to 10.1%; adding the starter-list collects takes it to 88.7%. §7A.8 already
observed that the task list costs `base` more than the entire setup batch does; this is the same
fact from the remedy's side.

---

## 7F. A + B on real silicon — the run §7E was waiting for (2026-09-18, PARTIAL)

**Provenance: [HW] throughout.** Real `dev` bench board, go-ahead given directly by the project
owner in the running session. Run against `REAL_HARDWARE_HANDOVER_MEASURE_B.md`'s protocol (that
file has since been deleted, its results migrated here).
**This run is incomplete** — §7F.6 lists exactly what is still owed and why; nothing below depends
on the missing pieces.

Arms built per that handover's §4.1 isolation: the AFTER arm is the branch tip; the BEFORE arm is
the tip with `src/system_service.py` and `buildgen/codegen.py` at `da9bcf1` (= `7ccbe8d^`) and the
device module **regenerated**, so it is A-only. Verified before flashing: freshly generated
`sensortask_dev` carries **11** `gc.collect()` on the AFTER arm and **0** on the BEFORE arm;
`src/system_service.py` carries **2** and **0**. The two `.uf2` files differ in 523,556 bytes.

### 7F.1 The headline: the tripwire passes in-suite for the first time

| arm | in-suite `test_real_gc_heap_headroom_survives_a_full_system_build` |
|---|---|
| BEFORE (A only) | `free=105,088 alloc=87,888 largest_block=28,736` → **FAIL** (floor 80,000 B) |
| AFTER (A + B) | **PASS** — full flash suite `36 passed, 3 skipped, 12 deselected`, zero failures |

The tripwire has failed in-suite on **every image ever measured**: 20,592 B on base (§7D.3),
28,864 B and 28,736 B on A-only across two independent sittings. On A + B it passes.

**P1 confirmed.** Its stated falsifier — an AFTER in-suite reading under ~40,000 B, which would
have made §7E twin-only — did not occur. The BEFORE arm's 28,736 B also reproduces §7D.3's
A-only 28,864 B to within 128 B across a reflash and a different sitting, which is what makes the
pair trustworthy.

**The exact AFTER figure is not in hand** — only the bound `largest_block >= 80,000` and
`free >= 100,000` that passing implies. See §7F.6.

### 7F.2 The whole boot sequence, on a fresh heap

`heap_layout_after_full_boot_sequence.py`, the instrument this run existed to introduce (the
previous one stops at `build_system()` and so reaches only the first of B's two collect sites).
All readings below are at the **standalone/fresh-heap position**, at `gc.threshold(-1)`:

> **One row here does not mean what its label says, established later in §7F.9 point 3.**
> `after_starter_list` was taken 4,000 ms from the supervisor task's *creation*, and the starter
> loop itself takes ~1 s, so it reads ~3 s into the **run phase** — past the decay, not at the
> starter list at all. The instrument has since been fixed to report `after_starter_loop_end` at the
> loop's own observed end; read this table's last row as a run-phase figure.

| reading (free / largest_block / pct) | BEFORE (A only) | AFTER (A + B) |
|---|---|---|
| `baseline` | 137,632 / 135,392 / 98% | 137,632 / 127,808 / 92% |
| `after_build_system` | 104,192 / 93,728 / **89%** | 104,128 / 90,720 / **87%** |
| `after_start_timers` | 101,760 / 93,728 / 92% | 101,696 / 90,720 / 89% |
| `after_starter_list` | 93,632 / 66,144 / **70%** | 94,272 / 57,424 / **60%** |
| ~~`after_starter_list_production_threshold`~~ | ~~93,632 / 49,152 / 52%~~ | ~~94,272 / 49,152 / 52%~~ **withdrawn, §7F.8** |
| `BOOT build_system_ms` | 943 - 951 | **1,402** |
| `BOOT start_timers_ms` | 789 - 790 | 789 |
| `LISTS` | starters=22 timers=8 | starters=22 timers=8 |

`starters=22 timers=8` matches §7E's [SRC] count, so the starter loop really does run 23 collects
on the AFTER arm.

**Two rows of this table do not mean what they say, and both were found out after it was written.**

**The threshold row is withdrawn — §7F.8.** It read exactly 49,152 B on both arms where the line
above differs by 8,720 B. That is the ninth instrument artefact on this branch: the probe pinned its
own buffer and returned the first size that succeeded, always `_PROBE_MAX >> k`, and 49,152 is
`192 KB / 4`. Not a layout figure, not the threshold — the threshold hypothesis was tested and
refuted separately (the probe returns the same value at `threshold(-1)` and `threshold(32768)` at
200k/300k/560k, differing in both directions where it differs at all). Both device scripts now
detect the pin and reread.

**The `after_starter_list` row is a run-phase reading — §7F.9.** The script settles 4,000 ms after
the starter list, and the twin puts most of measure B's decay inside the first two seconds of the
run phase. So neither the 70% nor the 60% says anything about what the starter-list collects did;
the reading that does is `after_starter_loop_end`, which the script did not take at the time and
now does.

### 7F.3 P3 confirmed — the instrument sees the starter list

On the **BEFORE** arm `after_starter_list` (70%) is materially worse than `after_build_system`
(89%). That is the control: with nothing resetting placement, the starter list scatters survivors.
Had it not held, P1 and P2 would have meant nothing. Twin base moves 14.2% → 8.4% over the same
span; the board moves 89% → 70%, same direction, much gentler.

### 7F.4 P2 is NOT confirmed at this position — and the position is the reason

> **Superseded by §7H.2 [HW], 2026-09-19: P2 is CONFIRMED.** The aged-heap AFTER reading this
> section says the run could not take was taken the next sitting — `after_starter_loop_end`
> 5,024 B / 5% on A-only against **75,104 B / 80%** on A + B, beating the twin's own upper bound.
> §7F.9 adds the host-side half on the real method. Everything below is still the right reading of
> a *fresh* heap; only its "untested" verdict is closed.

On the fresh heap, A + B is **slightly worse** than A alone at every point (87% vs 89% after
`build_system()`, 60% vs 70% after the starter list). Read naively that is P2 falsified.

It is not, and §7D.2 is why. **A fresh heap is the configuration in which the defect does not
exist** — both arms are already at 87-89%, near the 98% baseline, with nothing to recover. B's
collects cannot improve a layout that is not broken, and they cost. The configuration where the
defect does exist is the in-suite one, and there the same two images give 28,736 B → PASS.

**So P2 is untested, not refuted.** Testing it needs an aged-heap AFTER reading, which §7F.5's
second defect prevented this session from taking. Anyone reading the §7F.2 table in isolation will
conclude B is harmful; it is the single most misreadable number in this file.

**Amended 2026-09-19, and the position was only half the reason.** §7F.9 measured the same two arms
host-side against the real `start_and_check_tasks()` and found that the row this section argues
about is taken **4 seconds into the run phase**, by which point the twin has already lost most of
B's gain on every heap size tried — so the 87/89 and 60/70 pairs are run-phase readings on both
arms, and a fresh heap is not the only thing standing between them and P2. Read at the starter
loop's own end, where B's second site actually acts, the twin gives A + B **20 / 50 / 59%** against
A-only's **6 / 5 / 11%**. P2 is still owed on silicon, but it now has an instrument that can see it
(`after_starter_loop_end`) and a quantitative prediction to be read against.

### 7F.5 Two defects in the handover's own method, found by following it

**1. §4.1's build verification points at a stale file and cannot fail correctly.** It says to run
`grep -c "gc.collect()" build/generated_src/sensortask_dev.py`, expecting 11 on the AFTER arm.
That path holds an artifact dated **before measure B landed**: `scripts/build_firmware.py` calls
`generate_device()` into a `tempfile.TemporaryDirectory()` [SRC] and never writes
`build/generated_src/` at all — that directory is written by `scripts/_generate_sensortask_modules.py`.
Following §4.1 literally **reports 0 on a correct AFTER build**, which looks exactly like the
"stale generated module" failure the check exists to catch. Its companion check is inert too: the
two `.uf2` files are **byte-identical in size** (2,238,464 each), so "compare the two sizes" cannot
discriminate. Working replacements, used here: call `generate_device()` and count on its
`module_source` (AFTER 11 / BEFORE 0), `grep -c` on `src/system_service.py` (AFTER 2 / BEFORE 0),
and `md5sum`/`cmp` on the images (523,556 bytes differ).

**2. §4.3's saturation check cannot work as written.** It says to re-run the layout script "about
five minutes later" and treat agreement as evidence the ageing has saturated. But the script
strands `main.py` and leaves `WDT(timeout=8000)` armed, so **the board resets ~8 s after it ends**
— the second run always measures a fresh heap. Observed directly: run 1, taken genuinely aged right
after the suite, gave `after_starter_list` **10,128 B / 10%**; run 2 a minute later gave
**66,144 B / 70%** with a fresh `baseline` of 137,632 B. The disagreement is the reset, not
position-confounding, and reading it as the latter would be a false finding about the method. A
real check has to leave `main.py` running between readings.

That aged reading is worth keeping on its own: **10,128 B / 10% on the BEFORE arm after the whole
boot sequence** is the worst layout figure this project has measured on silicon, and it is the
position P2 needs on the AFTER arm.

### 7F.6 What is still owed

- **The exact AFTER in-suite `largest_block`.** `heap_headroom_after_full_system_build.py` prints
  its `HEAP` lines unconditionally, but `test_memory_stress.py` only surfaces the captured output
  in its **failure** message, so a passing run discards it. **`pytest -s` does not help** —
  confirmed by re-running the suite with it; `Board.run_isolated()` captures device stdout into a
  Python string rather than letting it reach the terminal. Getting the number needs a one-line
  change to that test to print the captured output on pass. P1 stands without it.
  **Done host-side 2026-09-18 (PR #105 session), not yet run:** the test now prints every `HEAP `
  line whatever the verdict. `-s` was powerless before because the test never emitted the string at
  all; now that it does, `scripts/run_flash_hardware_suite.sh -s` surfaces the figures on a passing
  run, so the next in-suite run yields the number without having to make the test fail to see it.
- **A rerun of `heap_layout_after_full_boot_sequence.py` on both arms with the 2026-09-19
  instrument.** Not a new experiment — the same run again, now that the script takes the
  `after_starter_loop_end` reading P2 turns on (§7F.9), detects the probe pin that made the
  threshold row unreadable (§7F.8), and takes a control reading before switching the threshold.
  Two invocations. Everything §7F.2 records stays valid except the withdrawn row.
- **An aged-heap AFTER reading**, which is what P2 actually turns on (§7F.4), and which needs
  §7F.5's second defect addressed first.
  **Amended (PR #105 session): it does not.** §7F.5's own run 1 — 10,128 B / 10% on the BEFORE arm,
  taken right after the suite — is a valid aged reading obtained *with* the defect present. The
  defect breaks the saturation **check**, not the reading, so the AFTER arm's aged figure costs one
  invocation at the end of the next suite run. The check itself is replaced rather than repaired:
  one reading after the flash suite and one after the bench suite, each following its own run, which
  age the heap by different amounts and need nothing to survive in between — the same argument §7D.3
  already made for the tripwire's 28,864 B appearing in both.
- **The AFTER arm's threshold-first reading.** The BEFORE arm's was taken: with
  `gc.threshold(32768)` set *before* the run, `after_starter_list` is **75,536 B / 79%** against
  the reactive default's 66,144 B / 70% — so on the A-only image the firmware's own threshold gives
  a *better* layout than the reactive default, which is the direction §1.5 and §7D.8 flag as the
  open question. One invocation on the AFTER arm closes it.
- **P5**, the `errcount` re-read. Pre-flight was NTP 11 (`E1`x6, `E2`, `E20`, `E1`, `E1`) and
  SYSTEM 1 (`W4`), everything else 0.
- ~~**The unexplained 49,152 B.**~~ **Closed 2026-09-19 — §7F.8.** It was the probe pinning its own
  buffer, not the threshold and not the layout. The row is withdrawn and both scripts now detect it.
- The F1 SSID script (handover §6.2) was **deliberately not run** (B-D3), it being the script that
  stranded the bench on 2026-09-18.

### 7F.7 P4 confirmed, and F2 confirmed fixed on silicon

**P4.** `build_system_ms` rises 943 → **1,402 ms**, so B's 11 batch collects cost ~455 ms, about
41 ms each on the RP2040's real heap. Far under the ~2,000 ms falsifier and under the 8,388 ms
watchdog cap; no `WDT_RESET` was observed across the run's reboots. The twin's 300-490 us per
collect [TWIN] does not transfer, as §7A.7 said it would not — the real figure is ~85x that, which
is the first RP2040 collect cost this project has measured.

**F2 (queue finding).** Both rewritten FRAM fault injectors —
`test_fram_cs_pin_hijack_fault_injection_and_recovery` and
`test_fram_hard_reset_race_during_write_and_recovery` — **pass on both arms**. They failed on the A
arm on 2026-09-18, and this is the first real-chip confirmation that the hijacked payload is
actually *refused*: the twin's fake chip ignores CS, so host-side validation could only ever show
that the injection fires. Neither reported the "nothing was injected, so nothing was tested" guard.

### 7F.8 The 49,152 B coincidence, explained: the probe can pin its own buffer [TWIN]

§7F.2 flagged `after_starter_list_production_threshold` reading **exactly 49,152 B on both arms**
where the line above differed by 8,720 B, and recorded that the obvious hypothesis — the threshold
clamping the probe — had been tested and refuted. The real mechanism was found on 2026-09-19, and it
is neither the threshold nor the layout.

**`_largest_block()` can keep its own probe buffer alive through a stale root.** The search
allocates `bytearray(mid)`, `del`s it and collects; in some call contexts the just-freed buffer
survives that collect. Every later, larger attempt then fails for want of the space the pinned
buffer is holding, `high` walks down to the pinned size, and the search returns **exactly the first
size that succeeded** — which, for a binary search over `[0, _PROBE_MAX]`, is always
`_PROBE_MAX >> k`: 98,304, **49,152**, 24,576, 12,288. The reading is an artefact of the
instrument, and it is always an *understatement*.

Reproduced deterministically on the settrace-free Unix port at 200k, 300k, 500k and 1M heaps, with
a fragmented heap and repeated `_report()` calls. The **pin** occurs at all four; it **corrupts the
answer** at 200k and 300k, where the true largest run is below `_PROBE_MAX` and the search therefore
has somewhere lower to converge to. At 500k and 1M the answer is already `_PROBE_MAX` and only
`retained` shows it happened — which is the case a reader would never notice without that field:

| run | free | largest_block | mem_alloc vs the clean runs |
|---|---|---|---|
| r1 | 237,280 | 121,472 | — |
| **r2** | 237,280 | **98,304** = `_PROBE_MAX / 2` | **+98,304** |
| r3 - r5 | 237,280 | 121,632 | — |

**The tell is `alloc`, and it is exact**: in the pinned run `gc.mem_alloc()` is higher by precisely
`largest_block`. Byte-identical across repeated processes, and the same shape at 200k
(12,288 = `_PROBE_MAX / 16`, alloc +12,288).

**Why both arms produced the same number.** Whether the pin happens depends on the call sequence,
not on the heap: the script, the frame nesting and the number of probe iterations are identical on
the two images. Both arms' true `after_starter_list` value sits between 49,152 and 98,304, so on
both the first successful probe is the second midpoint, 49,152 — and both pin there. That accounts
for every feature of the row at once: the identical value, its roundness, its being *worse* than the
line above, and `free` being unchanged (`gc.mem_free()` is read before the probe runs).

**Consequences.**
- **The `after_starter_list_production_threshold` row of §7F.2 is withdrawn**, on both arms. It is
  not a layout figure. Nothing else in §7F depends on it.
- The contradiction it created is gone with it. §7F.6's threshold-first BEFORE reading
  (**75,536 B / 79%** against the reactive default's 66,144 / 70%) said the firmware's own threshold
  gives the *better* layout; the withdrawn row said the opposite. Only the first is a measurement.
- **No other figure in this file is affected.** The artefact's signature is a value of the form
  `_PROBE_MAX >> k`, and no other reading has one: 135,392 / 127,808 / 93,728 / 90,720 / 66,144 /
  57,424 / 28,864 / 28,736 / 20,592 / 10,128 are all off-node.
- **One older figure elsewhere in the repo has the signature.** `SPECIFICATION.md` I.3's "smallest
  largest-allocatable-contiguous-block under real hammer load was 49152 bytes" is exactly
  `192 KB / 4`. Its instrument arrived with a merge from `main` and is not in this tree, so this
  cannot be settled here; flagged in place and queued as R16. The claim it supports is unharmed —
  the artefact only understates, so that headroom is 48x or better.
- **It could have produced a false tripwire FAIL.** `heap_headroom_after_full_system_build.py`
  asserts a floor of 80,000 B on the same probe; a pin at 49,152 fails it on an image that is fine.
  That has not happened — every in-suite failure recorded here is off-node — but it was reachable.

**Both device scripts now detect and recover from it** (2026-09-19). `_report()` records
`gc.mem_alloc()` before the search and again after a collect, prints the difference as
`retained=`, and `_report_checked()` re-runs the reading while `retained` is non-zero. On the twin
one rerun has always been enough, and the retried value lands on its clean neighbours (121,440
against 121,248/121,440; 20,192 against 20,000/20,192). Both scripts also take a **control reading
at the unchanged threshold** before setting `gc.threshold(32768)`, so a difference in the threshold
line can no longer be confused with a difference between two probe runs — the confound that made
this row unreadable in the first place.

### 7F.9 Where measure B's gain is, and how fast the run phase takes it back [TWIN]

§7F.4 read the fresh-heap table as "P2 untested, because a fresh heap has no defect to fix". That
was half right. Run host-side on 2026-09-19 against the real `build_system()` and the real
`SystemService.start_and_check_tasks()` — no replica of the starter loop, unlike §7E's `basex` — with
the A arm made by rebinding the two modules' own `gc` to a no-op `collect()` (34 suppressed calls,
= 11 + 23, matching the [SRC] counts exactly):

| heap | arm | `after_build_system` | **starter loop end** | +2 s | +4 s | +10 s | +20 s |
|---|---|---|---|---|---|---|---|
| 1,000k | A | 11% | 6% | 5% | 6% | 3% | 5% |
| 1,000k | **A + B** | **45%** | **20%** | 17% | 7% | 9% | 13% |
| 1,300k | A | 10% | 5% | 3% | 5% | 5% | 4% |
| 1,300k | **A + B** | **68%** | **50%** | 14% | 21% | 9% | 14% |
| 1,600k | A | 40% | 11% | 9% | 9% | 6% | 8% |
| 1,600k | **A + B** | **78%** | **59%** | 19% | 11% | 11% | 8% |

(Largest contiguous over free. Settrace binary, so the heap sizes are ~4-5x the board's own fill
scale and are **not** comparable to §7E's calibrated 508k/560k — §1.2 item 7. The A-vs-A+B
comparison at a fixed heap is unaffected. `_PROBE_MAX` raised to 768 KB so nothing is censored.
The rebinding is exactly equivalent to the BEFORE image for these two modules: `gc.collect` is the
**only** `gc` attribute either of them uses — 11 uses in the generated module and 2 in
`system_service.py`, checked by grep — so nothing else changes behaviour.)

**Three things follow, and they resolve rather than weaken P2.**

1. **The starter-list collects do their job.** At the moment the loop ends, A + B holds 20 / 50 / 59%
   against A-only's 6 / 5 / 11% — a 3-5x gap, at every heap size. §7E's claim that the second site
   *preserves* what the batch built is confirmed on the real method.
2. **The run phase undoes most of it within about two seconds.** The supervisor and the 22 now-running
   tasks churn with no collect — by design, I.4(f.1) confines the exception to the two lists — and
   both arms fall toward a floor. A + B stays roughly 2x A-only there, but the 68% is gone.
3. **So §7F.2's `after_starter_list` row is a run-phase reading, not a starter-list one.** The device
   script slept 4,000 ms from the supervisor task's *creation*, and the loop itself takes ~1 s
   (`1.0 / len(starters)` per starter, whatever the count), so the board read about **3 s into the
   run phase** — squarely past the decay. The board's AFTER arm (60%) and BEFORE arm (70%) are both
   measurements of the run phase, and P2 was never addressed by either.

**This also settles the §7E disagreement.** `probe.py basex` stops at the end of the starter loop and
reported 88.7%; the device script settles 4 s and reported 60%. Both are right about different
positions, and neither instrument was wrong — the two numbers were being compared as if they named
the same moment. §7E.2a already warned that `basex` "measures `build_system()` + the starter loop and
not the real boot in full"; this is the other half of that warning.

**The instrument is fixed** (2026-09-19): `heap_layout_after_full_boot_sequence.py` now wraps
`SystemService._start_task` to count starters as they land, waits for the loop's own end rather than
a guessed constant, and reports **`after_starter_loop_end`** there — the reading measure B's second
site is actually about — before going on to the settled `after_starter_list` reading, which keeps
its old label. That reading now settles 4 s from the loop's **end** rather than 4 s from the
supervisor's creation, so it sits ~1 s later than §7F.2's — which the table above says is inside the
noise, every column from +2 s on being in the same band. `BOOT` now prints `starter_loop_ms` and
`settle_ms` separately, so the position is on the line rather than inferred.

**What this does not change.** B's value on silicon is measured and stands: the in-suite tripwire
passes on the AFTER arm and fails on the BEFORE arm (§7F.1), and that reading is taken after
`build_system()`, where the batch collects are worth 4-7x on the twin and enough to clear the
80,000 B floor on the board. A boot-time placement gain that decays in the run phase is exactly what
a boot-confined placement reset can be expected to buy; it is not a defect in B, and it is not an
argument for widening the exception into the run phase.

---

## 7G. The 80,000 B floor, retired and replaced (owner, 2026-09-19)

**The decision, in the owner's words:** *"I don't know, I did not introduce it and can be removed as
it does not reflect reality. my expectation is that there are as few survivors in the long heap and
that sufficient contiguous gaps fit with some rather sure margin for real use, but not one third of
the whole RAM contiguously free. Replace by more expressive tests."*

That retires the number this whole branch has been reporting against, and it replaces one arbitrary
threshold with three checks that each say what they mean. §7A.9 had already shown the floor was
5x above anything the firmware can be asked to allocate; what it got wrong was the conclusion
("keep it"), not the arithmetic.

### 7G.1 A better instrument, and it costs nothing [SRC]

`micropython.mem_info(1)` prints the GC's own per-block allocation map, and the `gc_dump_info()`
header above it prints **`max free sz`: the longest run of free blocks, in blocks** [SRC, `py/gc.c`
`gc_info()`]. Three properties matter here:

- **It allocates nothing**, so it cannot perturb the layout it measures — unlike the binary-search
  probe, which allocates up to 192 KB per reading.
- **It is exact**, not a search result, and therefore immune to §7F.8's pinning artefact outright.
- **It carries position**, which no single number can: the map shows *where* the survivors are.

Verified equal to the probe to the byte: a fragmented 300k heap gives `max free sz: 3842` blocks x
32 B = **122,944 B**, and the binary-search probe on the same heap returns **122,944**. On the real
boot sequence at 1M the two agree at **167,456 B**, delta 0.

Both device scripts now print the map; `tests_hardware/heap_map.py` parses it host-side (the device
cannot — `mem_info` writes to the platform print, not `sys.stdout`), and
`tests_scripts/test_heap_map_parser.py` pins the parser, because its dangerous failure mode is
silent: a truncated capture reads as a heap with an enormous free run at the end, which is the
direction that turns a regression into a pass.

### 7G.2 The three checks, and what each clause of the owner's sentence became

| the owner's words | the check | the threshold, and where it comes from |
|---|---|---|
| "as few survivors" | `used <= 100,000 B` after the full build | ~14% over the 87,760-87,968 B [HW] the dev object graph itself costs |
| "as few survivors **in the long heap**" | `free_above_top_survivor >= 16,384 B` | one whole worst reachable allocation still fits **above the highest long-lived object** (§7A.9) |
| "sufficient contiguous gaps fit with some rather sure margin for real use" | `largest_free_run >= 32,768 B` | **2x** that worst case |
| "but not one third of the whole RAM" | — | 32,768 B is **12%** of the RP2040's 264 KB SRAM; the retired floor was 30% |

Every threshold is derived from §7A.9's measured 16,384 B worst reachable allocation — microdot's
own `max_body_length` default, which the project never overrides — and **none may be raised to fit a
board reading**. That is the discipline the old floor lacked: it was set at ~69% of one healthy
measurement, so it encoded whatever that board happened to do.

The probe stays, and the host side **cross-checks it against the map**. They measure the same run by
different means, so a disagreement means one of them is wrong — and §7F.8's artefact has exactly
that signature.

### 7G.3 `free_above_top_survivor` is the discriminating metric [TWIN]

Measured on the real boot sequence, 1,300k, the two arms of §7F.9:

| position | A only | A + B |
|---|---|---|
| `after_build_system` | **6,240** | **213,472** |
| `after_starter_loop_end` | **5,184** | **71,552** |
| 4 s into the run phase | **1,568** | **35,680** |

A 14-34x separation, in the direction the mechanism predicts: with no placement reset the survivors
reach the very top of the heap, and with one they do not. This is what "as few survivors in the long
heap" looks like when it is measured rather than inferred, and it separates the arms far more
sharply than the contiguity number the old floor watched.

**One metric was tried and rejected**: the *count* of free runs above a size. On the A-only arm it is
consistently **higher** (14/16/23 gaps >= 4 KB against A + B's 9/11/18), because a fragmented heap has
more medium holes. A gap count reads backwards as a health metric and is reported only as a
diagnostic.

`alloc_span_pct` was also weak here (99% against 83-97%) — a couple of objects at the extremes
saturate it — so it stays a diagnostic too.

### 7G.4 What is owed on silicon

**There is no host-side gate on any of this, and building one is not free.** `mem_info(1)` works
identically on the Unix port, so the same three checks could run in the twin's CI — but only at a
*calibrated* heap size: at `scripts/test.sh`'s 16 MB everything passes trivially, and absolute bytes
do not transfer anyway (§1.4). A calibrated-heap layout gate means a `scripts/` change and a
heapsize decision, which is the owner's call and bigger than this change. Recorded as an option, not
built.

**`free_above_top_survivor` has never been measured on real hardware**, on any image. Its threshold
is derived from the requirement rather than fitted to a reading, which is the only honest way to set
it before the first run — but it does mean the first bench run is where it is found out. **A failure
there is a finding, not automatically a regression**: it would say that long-lived objects do reach
the top of the real heap, which is worth knowing either way. Queue row B7.

### 7G.5 "Zero survivors in the long heap" — asked for, measured, and it holds [TWIN]

The owner's ask, 2026-09-19: *"one thing I would like as a test would be 'zero survivors in the long
heap with A and B applied and without gc.threshold set'. But only if this is reliable and won't
produce false positives erratically. If it's brittle, we could also change it to 'no more than X
survivors'."*

Answered by measurement rather than by picking a number. **Zero is reliable — at the
requirement-sized region, and only when measured as a delta.** Both qualifications came out of the
data, not out of caution.

**Why a delta.** Asked absolutely — "no allocated block in the top N" — the answer depends on what
was on the heap *before* the boot ran, which is §7D.2's position problem in a new place: in-suite,
`main.py`'s own leftovers sit wherever they sit, and the boot would be blamed for them. Comparing
the block map before `build_system()` against the map after it counts only what **the boot placed**.
Whatever was already up there appears in both maps and cancels. The measurement is then the same
whatever the suite has done to the board beforehand — which no other figure in this file can claim.

**And it is a lower bound, deliberately.** A block that is occupied in *both* maps is not
attributed, even when the first occupant was freed in between and the boot's own survivor took its
place — which is a real case on the board, where `build_system()` rebinds the module globals and
drops `main.py`'s graph as it builds its own. So the delta can undercount exactly where the
absolute check is strict, and the absolute check can blame the boot for something it did not place.
That is why both are asserted: **the pair brackets the truth, and the two failing differently is
itself the diagnosis.**

**The sweep.** Real `build_system()`, `gc.threshold(-1)`, `fresh` = first build in the process,
`aged` = a full boot plus 4 s of run phase first, then `build_system()` again — which is exactly
what a device script does on the board, since it rebinds the same module's globals and drops the
previous graph. Perturbations retain 0/7/61 extra objects before the build, shifting every later
placement.

| fill | arm | `new_in_top16K` | `new_in_top32K` | `new_in_top64K` | highest new block |
|---|---|---|---|---|---|
| 1,150k aged (58%) | A only | 11 | 306 | 337 | 98% |
| 1,150k aged (58%) | **A + B** | **0** | **0** | 256 | 95% |
| 1,250k aged (53%) | A only | 4 | 9 | 9 | 99% |
| 1,250k aged (53%) | **A + B** | **0** | **0** | **0** | 87% |
| 1,300k aged (51%) | A only | 5 | 5 | 9 | 99% |
| 1,300k aged (51%) | **A + B** | **0** | **0** | **0** | 84% |
| 1,300k fresh | A only | 0 | 0 | 0 | 92-94% |
| 1,300k fresh | **A + B** | **0** | **0** | **0** | **61-62%** |
| 1,600k aged (41%) | **A + B** | **0** | **0** | **0** | 68% |

**`new_in_top16K = 0` and `new_in_top32K = 0` held in every A + B run — 17 of 17**, across four
heap sizes spanning 41-58% fill, fresh and aged, at three perturbations. A-only breaks the 16 KB
boundary as soon as the heap is aged, and reaches 92-99% of the heap in every configuration.

**Where it becomes brittle, measured rather than guessed.** At 1,150k — a *tighter* fill than the
board's ~46% — A + B places 256 blocks in the top 64 KB. So 64 KB is the edge and a fraction-based
boundary is worse: "no survivor above 90% of the heap" fails there too. That is precisely the
"false positives erratically" the owner asked to avoid, and it is why the shipped boundary is
**16,384 B — one worst reachable allocation (§7A.9)** — and not the biggest number that happened to
pass.

**The transfer caveat, stated because absolute bytes do not transfer (§1.4).** 16 KB is 1.2-1.4% of
these twin heaps and **8.5%** of the board's ~192 KB, so the board is being asked for proportionally
more. What the twin verifies at comparable fill is that the top **13-16%** stays clear (highest new
block at 84-87%), which is ~25-31 KB board-equivalent — so 16,384 B keeps roughly 2x margin at the
board's own fill. It is **not** verified for 32,768 B on the board, which is why that is reported
and not asserted. `highest_new_pct` is printed on every run so the real margin becomes visible the
first time this runs on silicon, and the boundary can be raised against a reading rather than a
hope.

**What shipped.** `tests_hardware/flash/test_memory_stress.py` now asserts **both** forms, because
they fail for different reasons and the difference is the diagnosis:
1. `delta(baseline, after_build_system).new_above(16_384) == 0` — attributable to the boot,
   independent of suite position.
2. `free_above_top_survivor >= 16_384` — absolute, and position-dependent by nature.

A failure of 2 while 1 passes says the heap was already colonised before the boot ran, and the
message says so. Four more parser tests pin the delta, including that a block already allocated in
the `before` map is never counted however high it sits.

---

## 7H. The 2026-09-19 sitting — P2 settled, the new checks' first silicon run (COMPLETE)

**Provenance: [HW] throughout.** Real `dev` bench board, owner's go-ahead in the running session.
This sitting closed every item §7F.6 left owed, ran §7G's replacement checks for the first time,
and overturned one claim §7D.5 made.

Arms built by §7F.1's isolation: BEFORE = tip with `src/system_service.py` and `buildgen/codegen.py`
at `da9bcf1`, **regenerated** (verified 0 generated + 0 `system_service` collects); AFTER = tip
(verified 11 + 2). `md5sum`s differ. §7F.5's note about the stale `build/generated_src/` was heeded —
the count was taken off a fresh `generate_device()` call, not that path.

### 7H.1 B1's owed figure, and it is larger than the bound implied

`test_memory_stress.py` prints every `HEAP ` line on a passing run since 2026-09-18, so
`run_flash_hardware_suite.sh -s` surfaced it with no extra invocation:

| arm | in-suite `after_build_system` | verdict |
|---|---|---|
| BEFORE (A only) | `free=104,368 alloc=88,464 largest_block=27,968 retained=0` | FAIL (old 80,000 floor) |
| AFTER (A + B) | `free=104,272 alloc=88,560 largest_block=91,008 retained=0` | PASS |

**91,008 B against 27,968 B — 3.25x.** §7F could only say ">= 80,000"; the real figure clears the
retired floor by 1.14x and §7G's replacement `largest_free_run >= 32,768` by 2.78x. `retained=0` on
every line of both arms, so §7F.8's pinning artefact touched none of this.

### 7H.2 P2 CONFIRMED — the reading it always turned on

B6, both arms, taken immediately after that arm's suite without resetting. The position is
genuinely aged, confirmed by `after_build_system` matching the in-suite value (26,736 / 89,792)
rather than the ~93,000 a fresh heap returns.

| reading (free / largest / pct) | BEFORE (A only) | AFTER (A + B) |
|---|---|---|
| `after_build_system` | 103,168 / 26,736 / **25%** | 103,104 / 89,792 / **87%** |
| `after_start_timers` | 100,608 / 27,024 / 26% | 100,544 / 89,792 / 89% |
| **`after_starter_loop_end`** | 93,056 / **5,024 / 5%** | 93,024 / **75,104 / 80%** |
| `after_starter_list` (4 s settle) | 92,160 / 5,664 / 6% | 92,128 / 11,952 / 12% |
| `BOOT build_system_ms` | 679 | 1,404 |
| `BOOT starter_loop_ms` | 2,409 | 2,964 |

§7F.9's prediction was A + B **20-59%** of free at the loop end against A-only's **5-11%**.
Measured: A-only **5%**, inside its band; A + B **80%**, above the twin's own upper bound. The
falsifier — AFTER no better than BEFORE at the same position — is not close. **P2 is confirmed, and
the separation on silicon is wider than the twin's.**

**F6's run-phase decay is confirmed on silicon as well**: A + B gives back 80% -> 12% across the 4 s
settle; A-only moves 5% -> 6%, having nothing to lose. So both halves of §7F.9's finding hold —
the gain is real and large where the boot lists end, and most of it is returned in the run phase.

### 7H.3 B4 — the threshold does not merely add to B, it is what makes B's gain survive

AFTER arm, `gc.threshold(32768)` set *before* the run, against the reactive-default run above:

| reading | AFTER, reactive default | AFTER, threshold-first |
|---|---|---|
| `after_build_system` | 89,792 / 87% | 94,304 / 91% |
| `after_starter_loop_end` | 75,104 / 80% | 79,680 / 85% |
| `after_starter_list` (4 s settle) | **11,952 / 12%** | **74,896 / 80%** |
| `BOOT build_system_ms` | 1,404 | 1,033 |
| `BOOT starter_loop_ms` | 2,964 | 1,720 |

Same image, same board, one invocation apart: **with the firmware's own threshold set from the
start, the run-phase decay does not occur** — 80% is held where the reactive default falls to 12%.
It is also faster, by 371 ms of `build_system()` and 1,244 ms of starter loop.

This is the same direction the BEFORE arm showed on 2026-09-18 (threshold-first 75,536 / 79%
against reactive 66,144 / 70%), now much larger because there is more gain to preserve. It bears
directly on §1.5 and §7D.8: **the threshold is what carries B's placement gain into the run phase.**

> **The inference this sentence originally drew from that — "so the threshold is not defence in
> depth" — overreached, and is withdrawn (2026-09-21).** It conflates two different claims. Whether
> the system is *stable* without the threshold is settled and the answer is yes: the whole
> MicroPython suite passes at `gc.threshold(-1)` — 85/85 files, zero `MemoryError`s, caught-and-
> logged included — and so does the twin CI's own eleven-run sequence. Whether the boot *placement
> gain* survives the run phase without it is the different question this section measures, and the
> answer to that is no. So the owner's framing stands unchanged: the threshold is defence in depth
> pushing an already-stable system further from the edge, not the thing that makes it stable. What
> this measurement adds is only that it also preserves a layout benefit B creates — which is a
> reason to keep it, never a reason the design may lean on it.
>
> **Qualified 2026-09-23 (§7Q):** "stable without the threshold" held for the two tiers cited, not
> for the board under concurrent HTTP load, which served at most 4 requests at `-1`. Root-caused
> and fixed in the twin in §7Q; silicon confirmation is queue rows W4/W5.

**Stated as one reading per condition, not a repeated measurement.** Two arms x one invocation, and
the settle-point figure is the one that moves most. Worth repeating before anything is concluded
from it, which is why it is reported and not asserted anywhere.

### 7H.4 §7G's replacement checks, first silicon run — and the top of the heap is empty

The full flash suite re-run on the AFTER arm with §7G's instrument: **36 passed, 3 skipped,
12 deselected, zero failures.**

```
MAP after_build_system: used=89040 free=103792 largest_free_run=90688
    free_above_top_survivor=90688 gaps>=4K=1 gaps>=16K=1
    deciles=[1163, 1177, 1177, 1079, 806, 163, 0, 0, 0, 0]
```

| §7G.2 check | threshold | measured | margin |
|---|---|---|---|
| `used <= 100,000` | 100,000 | **89,040** | 1.12x |
| `largest_free_run >= 32,768` | 32,768 | **90,688** | 2.77x |
| `free_above_top_survivor >= 16,384` | 16,384 | **90,688** | **5.53x** |
| probe vs map cross-check | delta <= 64 B | 90,688 vs 90,688 | **delta 0** |

§7G.4 said `free_above_top_survivor` "has never been measured on real hardware, on any image" and
that a failure would be a finding either way. It passes, with 5.5x margin. **The decile histogram
is the stronger statement: the top four deciles hold zero allocated blocks**, and the fifth holds
163. That is the owner's "as few survivors in the long heap" satisfied outright on the shipped
image, not approached.

The probe and the map agreeing **exactly** also retires any doubt that §7F.8's artefact is at work
in these readings.

### 7H.5 A claim §7D.5 made is overturned

§7D.5 recorded `test_the_link_keeps_transferring_while_every_other_subsystem_is_busy` as
**"A fixed this"**, on one observation per arm. Four further runs say otherwise:

| run | image | result |
|---|---|---|
| S1 2026-09-18 | base (A reverted) | FAIL — heap grew 3,584 B |
| S1 2026-09-18 | A | PASS |
| S1 2026-09-19 | A only | **FAIL** — heap grew 4,192 B |
| S1 2026-09-19 | A + B | **FAIL** — heap grew 4,752 B |
| S2 2026-09-19 | A + B | **PASS** |
| S1 2026-09-19 (B7 re-run) | A + B | **PASS** |

The same image both passes and fails it, and the A-only arm now fails where A passed before. **The
test is marginal around its own threshold, not a stable signal**, so the 2026-09-18 attribution was
drawn from a single observation that did not reproduce. §7D.5's row is corrected in place. Nothing
else in §7D depends on it; A's layout result (§7D.3) is a different measurement entirely.

### 7H.6 Everything else this sitting closed

- **S2, the bench tier: `93 passed, 4 skipped, 27 deselected` — zero failures**, the first fully
  clean bench run on any image. Closes T.2's bench tier on A + B, C1's tier-4 bus-hazard run for the
  I2C shared scratch buffer, and R9's ISL29125 shadow-divergence check.
- **R11 / C1 (I2C shared scratch buffer)**: tier 3 and tier 4 both green across two full suites.
  `test_isl29125_same_device_read_write_concurrency` and
  `test_i2c_and_spi_deinit_are_silent_noops_and_each_bus_id_is_a_singleton` pass.
- **R14** (`test_watchdog_starvation_triggers_a_real_hardware_reset`, the new banner assertion that
  could turn a green test red): **PASS** on silicon, first run.
- **R8's calibrate half** (`test_isl29125_calibrate_command_push_over_real_rest`): **PASS**. The
  reboot half stays D1-blocked.
- **F2**: both FRAM injectors pass again on both arms, and neither reported the
  "nothing was injected" guard.
- **P5, `errcount` after the sitting**: FRAM 2 -> 0, SGP40 3 -> 10 (`W10` x4, `W13` x5, `W11`),
  WIFI 5 -> 9 (`W6` x9). **No errno 90/91/92/93/99/100, no wrnno 81/82/84** — the FRAM byte-level
  guards stayed clean across two full suites and a bench tier. FRAM's own pre-flight entries going
  to 0 is the documented chunk-overwrite hazard, observed again.

### 7H.7 Three observations that are not results

- **The pre-flight `errcount` carried `FRAM: E31, W73`.** `W73` is a real FRAM-manager warning
  ("Invalid data in block 1, overwriting with block 0 data"), but **`errno=31` is
  `asy_isl29125_driver.py`'s "Status read failed"** — a foreign code under FRAM's own logger. That
  is CLAUDE.md's chunk-contamination hazard, from an earlier isolated-driver script, not a FRAM
  fault. Recorded because the rule says to read these before they are overwritten, and they were
  overwritten by this sitting's own scripts.
- **A malformed file exists on the board's flash**:
  `config_HWTEST_ISL29125.cfgconfig_ISL29125.cfg` — two config filenames concatenated. Some test
  path builds a filename by concatenation without a separator. Harmless where it sits (nothing
  reads it), but it is a real defect in whatever wrote it. Not chased; queued.
- **R12 (per-device hostname) cannot be checked on this board as it stands.** `GET /networking`
  reports `SensorNode` while `devices/dev.toml` says `SensorStationDev` — which is R12's own
  documented "the persisted value wins on a board that already has a config file" case, not a
  failure. Confirming it needs a board with no `config_WIFI.cfg`, i.e. a deliberate config wipe,
  which is a flash write and outside D1.

---

## 7I. The post-merge full bench run (2026-09-19, owner's instruction — COMPLETE)

One full bench-tier run at default flags, no arguments, no wear flags, no soak — the mandate of
`REAL_HARDWARE_HANDOVER_POST_MERGE_BENCH_RUN.md` (since deleted, its results being these), run
after the branch merged 22 commits of base
plus the `arduino/` import and the ISL29125 promotion. The verdict line in full:

```
1 failed, 97 passed, 4 skipped, 27 deselected in 2439.57s (0:40:39)
```

The handover asked for the deselected count to be read rather than the word "clean": **27, exactly
the reference figure** from the two preceding sittings, and **97 passed / 4 skipped** matches the
reference too. The four skips are the two NeoPixel-rig light programs, the `--allow-flash-cycle`
reflash smoke test, and the spoofed-off-subnet-source row. **The one failure is W5 — and not on any
assertion about the body cap** (§7I.2).

**The image.** `src/` changed by exactly one line since the previously flashed build, and it is a
comment (`max_content_length`'s own `1.8x` → `1.56x` margin note), so the frozen bytecode is
identical and no reflash was spent. Confirmed functionally before starting rather than assumed:
2047 → 200, 2048 → 200, 2049 → 413, 4096 → 413 over the real network, which is W1 and W2's own
subject matter.

### 7I.1 The pre- and post-run `errcount`, read before anything wrote

CLAUDE.md's standing rule. Before the suite:

| module | counter | non-empty history |
|---|---|---|
| `WIFI` | 5 | `W6` |
| `SGP40` | 6 | `W13` x5, `W11` |
| every other module (21 total, `WEBSERVER` included) | 0 | — |

After the suite, once its own `reset_all_error_logs()` calls had cleared the table and the run had
refilled it:

| module | counter | non-empty history |
|---|---|---|
| `NTP` | 11 | `E1` x5, `E2`, `E20`, `E1` x3 |
| `SYSTEM` | 1 | `W4` |
| every other module | 0 | — |

**`WEBSERVER` is empty both times**, which is the assertion every queue §1D row makes and the one that
matters: a 413 is raised inside vendored Microdot before any of our own code runs, so anything
there would be a finding about this project. `NTP`'s entries are attributable —
`test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` is the second-to-last test
in the run. Nothing unexplained appeared, so queue §2A F9's contamination hazard is not in play here.

### 7I.2 W5's rewrite is confirmed on silicon — the red is one line further down

Every one of the four assertions the row was rewritten around **holds**, in the suite run and in
three dedicated repeats afterwards:

| run | answered | refused at ceiling | **wrong status** | non-ceiling exceptions |
|---|---|---|---|---|
| bench suite | (reached the health check, so all four passed) | — | **0** | **0** |
| repeat 1 | 20 / 24 | 4 | **0** | **0** |
| repeat 2 | 20 / 24 | 4 | **0** | **0** |
| repeat 3 | 20 / 24 | 4 | **0** | **0** |

Twenty answers against a floor of four, both verdicts present every time, and **not one request
answered with the wrong status** across all of them. That is the property the body cap actually
owns, and it is now `[HW]`.

What fails is the line *after* those four:

```
assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=15.0).status_code == 200, \
    "webserver unresponsive after concurrent mixed-body load"
```

which raised `ConnectionResetError` out of `http.client._read_status`. **The server is not
unresponsive.** Polled immediately after the load rather than asked once, it answered **200 after
75 ms** in two of the three repeats and first-try in the third:

| repeat | attempts after the load |
|---|---|
| 1 | `0.000s ConnectionResetError`, `0.075s 200` |
| 2 | `0.000s ConnectionResetError`, `0.073s 200` |
| 3 | `0.000s 200` |

This is §7H-era F10's slot-release lag at the *other* end of the test. A slot is released in
`_serve()`'s `finally`, which runs after `_close_writer()` awaits the close; 24 workers have just
finished, so their slots are still draining. W5 took a `time.sleep(1.0)` settle **before** its
workers — added for exactly this reason — and none **after** them, while
`tests_hardware/http_client.py`'s `fetch()` is single-shot with no retry by construction.

**FIXED 2026-09-19, owner's decision** ("a defect in the test setup, not a failure ... the test must
still fail if the server genuinely is unreachable, but under fair circumstances, not within an
almost-zero-delay recovery phase where it doesn't even have a chance"). The health check now uses
the **same `wait_until()` the neighbouring `test_connections_at_and_above_the_real_socket_limit_degrade_cleanly`
already uses 170 lines up in the same file** — 15 s bound, 1 s poll — whose own comment names this
very phenomenon ("closing 5 sockets near-simultaneously can transiently reset a brand-new connection
right after"). All four cap assertions are untouched.

**It is not a weakening, and that was verified rather than argued.** `wait_until()` treats a raising
check as not-yet-ready but still raises `TimeoutError` with the last exception embedded once the
bound expires. Exercised host-side against two genuinely dead targets, using the exact call shape
the test now makes:

| target | outcome | elapsed |
|---|---|---|
| a bench-LAN address that answers nothing | `TimeoutError ... (last error: URLError(OSError(113, 'No route to host')))` | 19.4 s |
| a reachable host with nothing on port 80 | `TimeoutError ... (last error: URLError(ConnectionRefusedError(111, 'Connection refused')))` | 15.0 s |

Both fail, inside the bound, naming the real cause. Three consecutive green runs of the fixed row
on the board followed, with the same zero-wrong-status result and a wider refusal spread than
before — 16/8, 19/5 and 20/4 answered/refused — which is the anti-vacuity floor of 4 doing its job
rather than the row becoming easier to pass.

**The suite's own verdict line is clean for the first time since the queue §1D rows were added:**

```
98 passed, 4 skipped, 27 deselected in 2328.23s (0:38:48)
OK: real-hardware suite run clean - no unexpected skips, no failures.
```

Same 4 skipped / 27 deselected as every reference run, one more passed, nothing else moved.

### 7I.3 §7G's replacement checks, re-measured after the merge — every margin held or improved

The mandated invocation takes no arguments, so pytest captures device stdout and the `HEAP`/`MAP`/
`DELTA` lines the handover asks to be written down never surface on a passing test. They were
recovered by re-running that one test alone with `-s` (about five seconds of board time):

```
HEAP baseline:                            free=137312 alloc=55520 largest_block=136400 retained=0
HEAP after_build_system:                  free=102656 alloc=90176 largest_block=93696  retained=0
HEAP after_build_system_control:          free=102656 alloc=90176 largest_block=93696  retained=0
HEAP after_build_system_production_threshold: free=102656 alloc=90176 largest_block=93696 retained=0
MAP  after_build_system: used=90192 free=102640 largest_free_run=93696
     free_above_top_survivor=93696 gaps>=4K=1 gaps>=16K=1
     deciles=[1206, 1205, 1200, 1135, 870, 21, 0, 0, 0, 0]
DELTA boot placement: new_blocks=2169 highest_new_pct=51 new_in_top16K=0 new_in_top32K=0
```

**`retained=0` on every `HEAP ` line**, so queue §2A F5's caveat does not apply and every figure here is
usable. Against §7H.4's reading on the pre-merge image:

| §7G.2 check | threshold | §7H.4 | **§7I** | margin now |
|---|---|---|---|---|
| `used <= 100,000` | 100,000 | 89,040 | **90,192** | 1.11x |
| `largest_free_run >= 32,768` | 32,768 | 90,688 | **93,696** | **2.86x** |
| `free_above_top_survivor >= 16,384` | 16,384 | 90,688 | **93,696** | **5.72x** |
| probe vs map cross-check | delta <= 64 B | delta 0 | 93,696 vs 93,696 → **delta 0** | — |
| `new_above(16_384) == 0` (§7G.1) | 0 | 0 | **0** | — |

`used` moved +1,152 B and the contiguous run **+3,008 B the right way**, so both replacement checks
are further from their thresholds than before the merge, not nearer. The decile histogram is the
stronger statement again and it improved: **the top four deciles still hold zero allocated blocks,
and the fifth dropped from 163 to 21**. No threshold was re-fitted and none needed to be — the
handover's §3 forbids it and nothing came close.

### 7I.4 R15 closed — per-module error logs persist across a real production reboot

The flash tier already covered the *mechanism* through an isolated-driver script's own
`AsyFramManager`; what had never been shown on silicon was the **production object graph's**
per-module wiring surviving a real reset. Read `errcount`, `PUT /system {"SystemCmd": "reboot"}`,
read it again:

| module | before | after | |
|---|---|---|---|
| `NTP` | counter 11, `E1 E1 E1 E1 E1 E2 E20 E1 E1 E1` | counter 11, **identical** | **SAME** |
| `SYSTEM` | counter 1, `W4` | counter 1, `W4` | **SAME** |
| `WIFI` | counter 2, `W6` | counter 7, `W6 W6` | appended, not lost |
| `SGP40` | counter 0, — | counter 5, `W13` … | appended during the same boot |

`NTP`'s full ten-entry history came back byte-identical, which is the row's own criterion. `WIFI`
and `SGP40` are not counter-examples: both logged *new* warnings during the very boot being
measured (the reboot's own STA attempts, and SGP40's routine boot warning — it carried six `W13`s
in the pre-suite table too), with the pre-reboot entries still present underneath. `FRAM`'s own row
was 0 on both sides, so the "in-memory by design" exception the row calls out was not exercised.

### 7I.5 One thing that cost time, and is nobody's defect

The hand-issued `PUT /system {"SystemCmd": "reboot"}` above left the DUT **in hotspot mode**: the
command returned `Valid`, the board reset and came up entirely healthy — all tasks running, every
sensor reading, uptime advancing — but STA never re-associated, and the serial log repeated
`WIFI Hotspot mode is active / Connected stations: []` with `NTP Network not available` for about
four minutes. A `board.hard_reset()` recovered it to its own address in ~40 s.

It is the known **stale-AP-station-table** behaviour, not a new one.
`tests_hardware/conftest.py`'s `dut_ip` fixture calls `bench.kick_all_stations()` before every
`hard_reset()`, and `test_real_reboot_sequencing_via_rest_completes_cleanly` calls it immediately
after this same REST reboot, its own comment naming "the same stale-AP-station-table finding as
every other real reboot in this tier". **That test passed in this run.** The trap belongs only to a
session issuing the reboot by hand, and is recorded as queue §2A F12 and in §6's standing traps.

---

## 7J. The 2026-09-19 evening sitting — eight more suite runs, five defects closed (COMPLETE)

The owner's instruction: fix anything the current run turned up, push, then **three consecutive full
bench runs at default flags**, then **one run with all persistence tests including the extra SCD30
write**, still no soak. Every failure below was fixed and pushed *before* the next pass started,
per the owner's follow-up instruction. **Not one of them was a defect in `src/`.**

### 7J.1 The scoreboard

| run | flags | verdict |
|---|---|---|
| verification (post-W5-fix) | default | **98 passed**, 4 skipped, 27 deselected — 38:48 |
| triple A, run 1 | default | **98 passed**, 4 skipped, 27 deselected |
| triple A, run 2 | default | 1 failed, 97 passed — **F7** |
| triple A, run 3 | default | **98 passed**, 4 skipped, 27 deselected |
| triple B, run 1 | default | **98 passed**, 4 skipped, 27 deselected — 40:09 |
| triple B, run 2 | default | **98 passed**, 4 skipped, 27 deselected — 37:58 |
| triple B, run 3 | default | **98 passed**, 4 skipped, 27 deselected — 40:09 |
| persistence, run 1 | `--allow-persistence-writes --allow-scd30-extra-write` | 3 failed, 117 passed, 4 skipped, **5 deselected** — 48:27, **F14** |
| persistence, run 2 | same | **120 passed**, 4 skipped, 5 deselected — 48:58 |

Triple A was restarted as triple B because F7's fix changed what was under test — three consecutive
clean runs have to be three runs of the same thing. **No `RESULT NOTE` appeared in any of triple
B**, so the STA-connect retry added in F13 was never actually consumed; nothing was being absorbed.

**The wear-gate run is the one that earned its keep**: deselected fell 27 → 5, i.e. it executed
**22 tests no previous sitting had ever run**, and three of them failed on their first exposure.
Flags deliberately *not* passed: `--allow-flash-cycle` (a deliberate re-flash, not a persistence
test) and `--allow-neopixel-sweep` (needs a physical light rig this bench does not have — those two
fail rather than skip without it, which is why they are the 4 skipped throughout).

### 7J.2 F11 — W5's health check (owner-decided, fixed)

Covered in §7I.2. The owner's ruling: *"a defect in the test setup, not a failure ... the test must
still fail if the server genuinely is unreachable, but under fair circumstances, not within an
almost-zero-delay recovery phase where it doesn't even have a chance."* Fixed with the same bounded
`wait_until()` the neighbouring connection-ceiling row already uses, verified to still fail against
a silent address and a dead port.

### 7J.3 F13 — a single association asserted as if it were deterministic

`test_real_sta_connect_reaches_established_after_a_hard_reset` failed in triple A run 1, taking
`test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` with it as a pure cascade
(`No route to host` — the DUT was simply off the LAN). The firmware behaved correctly: two failed
associations (`WLAN status: -1`, the CYW43 reporting failure), then the designed hotspot fallback.

**Measured before changing anything**: one `kick_all_stations()` + `hard_reset()` recovered it with
zero connect failures, then **12 further cold boots established 12/12, zero connect failures**. It
had passed in the two preceding full runs, making it 1 miss in 3. Status `-1` is an AP/RF-side
event, so nothing in `src/` is implicated. Fixed with at most **one** second cold boot, assertions
unchanged and run on the last attempt, both messages naming the attempt count, and a `RESULT NOTE`
printed whenever the retry is consumed so a rising rate stays visible. A systematic break still
fails both attempts — this row is the primary regression coverage for the stale AP-side
station-table scenario and was deliberately not blunted.

### 7J.4 F7 — the UART heap figure was measuring churn phase, not retention

Failed in triple A run 2 (`heap grew 3744 bytes`), inside the 3,584–4,752 B spread already on
record against a 2,048 B bound. F7 had been root-caused host-side as a sampling defect; this run
supplied the arithmetic that settles it:

`_CHURN_BLOCK = 512` and `_memory_churn_loop`'s held list oscillates between 13 and 25 blocks — a
**6,144 B swing, three times the bound** — and both endpoints were single `gc.mem_alloc()` reads
taken while that loop still ran, the end one inside the `finally` *before* `load.stop = True`.

Both ends now take the **live floor** (`_heap_floor()`: minimum of 8 collected samples at 8 ms,
spanning more than two churn cycles), sampled identically and under the same running load —
quiescing first would bias the difference negative instead of making the two comparable.

| | before | after |
|---|---|---|
| observed values | 3,584 / 3,744 / 4,192 / 4,752 B | **-272 / +16 / +224 / +336 / +752 / +848 B** |
| vs the 2,048 B bound | ~2x over | **2.4x under** |

The negative reading is the signature of a real floor rather than a phase artefact. **The bound is
unchanged at 2,048 B** — no threshold was re-fitted — and still catches what it exists for: 53 B
retained per transaction across this run's ~117 transfers is ~6 KB, far above it.

### 7J.5 F14 — three first-ever-executed tests, and F15 — the guard that caught my own fix

The wear-gate run's three failures:

- **`test_same_device_concurrent_sessions_never_corrupt_each_other`**: `CO2=119.73297` on iterations
  0-4, *the same value every time* — a stale data register, not corruption.
  `bus_concurrency_same_device_scd30.py` calls `scd.setup()` (a soft reset) then reads immediately,
  while the SCD30's measurement interval is NVM-persisted and so resumes at once, raising data-ready
  over the first unsettled conversion. **Its sibling `scd30_same_device_rw_concurrency.py` was
  already fixed for exactly this and its comment names the identical signature** ("a stuck
  CO2=141.99 on every iteration"); this script never got the same treatment. Mirrored it: a 12 s
  drain that *calls* `read_measurement()` rather than sleeping, because data-ready clears only on
  read.
- **`test_isl29125_config_write_...` and `test_bmp3xx_config_write_...`**: `ConnectionResetError` —
  F10/F11's slot-release lag a third time. These open **3** connections, *below* `max_connections =
  4`, and the file's own header already tried to buy safety with margin ("must stay under
  max_connections=4 with real margin ... or a brief overlap ... hits a genuine (but here undesired)
  reject-when-full"). Margin does not help: the slot is released in `_serve()`'s `finally` after
  `_close_writer()` awaits, so back-to-back worker requests outrun it. The BMP3XX row's second
  error — `PressOvers=1 rejected: ... "Unchanged"` — is a **cascade**: the lost write desynchronised
  the worker's alternation, so the next value already matched. Both now retry a ceiling close **and
  only** a ceiling close.

**F15 is what that fix then ran into, and it is the more interesting finding.** The retry wrapper's
first form, `_fetch(dut_ip, "PUT", "/sensors", {...})`, made `isl29125_write_worker` and
`bmp3xx_write_worker` **invisible** to `tests_scripts/test_persistence_write_marker_completeness.py`,
whose AST detector matches a call named exactly `fetch` with **at least 5 positional args**, method
at `args[2]` and body at `args[4]`. CI reported them as `gone: ['bmp3xx_write_worker',
'isl29125_write_worker']`.

**The guard worked exactly as designed** — it pins the set in *both* directions, so a helper leaving
is as loud as one joining — and the tempting fix, deleting the two names from
`_KNOWN_PERSISTING_HELPERS`, would have turned CI green while leaving two real flash writes
permanently unwatched. Fixed by **restoring visibility instead of excusing it**: the wrapper is now
named `fetch` with `http_client.fetch`'s exact positional signature, the detector sees straight
through it, and `_KNOWN_PERSISTING_HELPERS` is **unchanged**. The `is_ceiling_close()` predicate was
also **promoted out of `test_network_resilience.py` into `http_client.py`** per CLAUDE.md Part G's
shared-primitive rule rather than duplicated.

**F15's residual is closed, host-side, 2026-09-19** — see §7K.1. The guard now fails on any
`fetch()` call that passes its method as a variable, re-derives the one allowlisted wrapper's
premise from `http_client.fetch`'s own signature, and pins `fetch()` as this tier's sole HTTP
chokepoint. Closing it surfaced two live defects in the guard itself.

### 7J.6 State the bench was left in — SUPERSEDED by §7P (2026-09-22)

**Read §7P instead for the board's current state.** The hand-back described below was undone on
2026-09-22: the board was reflashed from this branch's tip and `DebugLevel` put back to 5. What
stays useful here is the *recipe* — this is still how to hand the board back as an ordinary quiet
device, and §7P points at it for exactly that.

On the owner's instruction at the end of this sitting, the board was taken **out of test
configuration** and set up as an ordinary device on the local network.

**What was done**, in order: built `scripts/build_firmware.py dev` fresh from this tip (`buildDate
2026-09-19T21:18:50Z`), flashed it with `picotool load -x -v`, then cleaned the filesystem. The
flash does **not** wipe the littlefs config — every file survived it, which is worth knowing in its
own right — so the cleanup was explicit:

| file | action |
|---|---|
| `config_HWTEST_DEBUGLEVEL_BACKUP.cfg`, `config_HWTEST_ISL29125.cfg`, `config_HWTEST_REBOOT.cfg` | **deleted** — test residue |
| `config_HWTEST_ISL29125.cfgconfig_ISL29125.cfg` | **deleted** — this is queue §2A **F8**'s malformed two-names-concatenated file, whose residual was "fold it into the next run that already spends a flash write". This was that run. |
| `config_BMP3XX.cfg`, `config_ISL29125.cfg`, `config_SGP40.cfg`, `config_NOTIFY.cfg` | **deleted** — regenerated at driver defaults on boot, i.e. a fresh device |
| `config_NTP.cfg` | **kept** — it carries real locale (`GMTOffset`/`DSTOffset` 3600, `pool.ntp.org`), which a reset to defaults would have silently wiped |
| `config_WIFI.cfg` | **rewritten**, same SSID/PW/Country, `Hostname` corrected from the stale `SensorNode` to `devices/dev.toml`'s own `SensorStationDev` |
| `config_SYSTEM.cfg` | **rewritten** to `{"DebugLevel": 0}` |

**Verified after a `kick_all_stations()` + `hard_reset()`**: associated to the bench AP (RSSI -23),
DHCP from the real router (192.168.85.57, gateway/DNS 192.168.85.1), NTP synced, website serving
HTTP 200 at 9,292 bytes, all four sensors reading plausible values, and **resolvable by name on the
LAN as `SensorStationDev.fritz.box`** — a normal device, reachable by hostname. The boot's own
`errcount` (four `CFGMGR_* W3`, one per deleted file; `WIFI W6`; plus the FRAM-persisted `NTP`/
`SYSTEM` history and F9's familiar foreign `FRAM E31`) was **read and recorded before** a single
`ResetErrors`, per CLAUDE.md; the table is now clean.

**This incidentally answers R12**, which was BLOCKED on D1 for exactly this reason: with the stale
persisted `Hostname` gone, the per-device value takes effect and the unit is reachable under it.
R12's own note is what predicted this ("the persisted value wins on a board that already has a
config, so a stale `SensorNode` there is correct behaviour, not a failure").

**This deliberately breaks the bench tier.** Several `tests_hardware/` tests read the serial log and
a `DebugLevel` of 0 silences what they parse — confirmed immediately here, where a post-reset
`tail_log()` returned nothing at all. Before resuming any bench-tier work:
`PUT /system {"DebugLevel": 5}`, confirm it took, and re-check the board is on the bench SSID.

### 7J.7 One thing left undiagnosed at the time — since root-caused (§7K.2)

**F16**: CI run `35468454090` reported `tests/test_uart_comm_hazard.py` at 95/96, `only 149/150
hammered transactions completed`. Nothing in this sitting touches the mock tier, and the three
preceding CI runs on this branch were green. Re-run locally **5 times on the same Unix-port binary:
96/96 every time**, which is why it was recorded as CI-only and explicitly **not** written off as a
flake on that evidence. **That caution was right and the framing was wrong**: it reproduces readily
once the host is loaded the way `scripts/test.sh` itself loads it, and the lead recorded here — that
`limit=300` might be a tight event-loop-step budget — is not what `limit` means. Both are settled in
§7K.2.

---

## 7K. The two host-side leftovers, closed without bench time (2026-09-19)

§7J left exactly two rows open that needed no hardware. Both are now closed, and in each case the
recorded lead turned out to be wrong — which is the part worth keeping.

### 7K.1 F15 — the guard had no concept of a call it could not recognise, and two live holes besides

The residual as recorded: `tests_scripts/test_persistence_write_marker_completeness.py` has
`_JUSTIFIED_UNREADABLE_BODIES` for a PUT *body* it cannot read, but nothing for a *call* it cannot
recognise, so the next wrapper not shaped like `fetch` reopens F14's hole silently.

Three checks close it, each verified by injecting the regression it exists for rather than by
agreeing with today's tree:

| check | what it catches | proven by |
|---|---|---|
| `test_no_fetch_wrapper_hides_its_method_from_the_detector` | any `fetch()` call passing its method as a variable — F14's draft exactly | renaming the real wrapper to `_fetch`: **fails** |
| `test_every_forwarding_wrapper_still_mirrors_fetchs_own_signature` | the one allowlisted wrapper drifting off `http_client.fetch`'s positional signature | swapping its `method`/`path` parameters: **fails** |
| `test_fetch_is_the_only_route_from_this_tier_to_an_http_request` | a module driving `urllib`/`http.client` itself, bypassing the detector entirely | — (`http_client.py` is the only importer today, confirmed) |

`_JUSTIFIED_FORWARDED_METHODS` carries exactly one entry, the ceiling-close retry wrapper F14 added,
and the second check re-derives that entry's premise instead of trusting it — the same discipline
`test_every_justified_exemption_still_rests_on_every_field_being_rejected` already applies to the
other allowlist. Raw `socket` is deliberately out of scope: this tier uses it for DNS probes and the
connection-ceiling rows, never to speak HTTP, and an allowlist of four files would be noise.

**Two live defects surfaced while building this, neither of them the residual.** The detector's
keyword fallback looked for `body=` — but `http_client.fetch`'s parameter has always been
`json_body`, so that escape hatch could never fire in its entire life. And
`_persisting_put_functions()` read `args[4]` positionally only. Together, a keyword-passed literal
PUT body was invisible to **both** detectors: not flagged as a writer, not flagged as unreadable.
Fixed by deriving fetch's real method index, body index and body keyword from its own `def`
(`_fetch_shape()`), so a reordered or renamed parameter now fails loudly instead of silently
shifting what every detector reads. `test_a_put_body_passed_by_keyword_is_still_seen` pins it.

Nothing in `tests_hardware/` changed: `_KNOWN_PERSISTING_HELPERS` and both justification tables are
untouched, and the tier's 16 guard tests pass.

### 7K.2 F16 — not CI-only, and neither recorded lead was the mechanism

**It reproduces locally, 3 runs out of 3**, by running the whole file under 24 CPU hogs on 4 cores:
`FAIL test_sustained_hammering_never_degrades_or_grows_the_heap_nocrc`, `95/96 passed`, the same
`only 149/150` every time. That is not an exotic condition — `scripts/test.sh` creates it
deliberately, at 4x the runner's core count (16 concurrent interpreters on a 4-core host) plus the
backgrounded `tests_scripts/` tier. The "CI-only" reading came from five *unloaded* local runs.

**Both recorded leads were checked and neither holds.**

- `run(hammer(), limit=300)` is not an event-loop step budget. `run()` is
  `asyncio.run(asyncio.wait_for(coro, limit))`, so `limit` is a **timeout in seconds** — and an
  expiry raises `TimeoutError`, it never returns `149`. All 150 iterations ran; one returned `False`.
- The listener budget is not binding either. Instrumented with an unbounded counting listener, 150
  transactions consume **exactly 150** of the 450 rounds available, 1 per transaction in both CRC
  modes — three times the headroom, not a starved tail.

**The mechanism.** The loopback link delivers in memory within one event-loop turn, so no part of the
configured `timeout` is ever spent on transmission: the only thing it can measure is whether this
*host* rescheduled the reading task in time. `ready()` enforces it against `time.ticks_ms()`, so one
long scheduling gap fails one read, one transaction, and the run. Sized against J.6's own floor
(`2 × poll_wait_ms + poll_idle_ms + ` worst-case GC pause):

| arm | budget | floor | margin |
|---|---|---|---|
| real `dev` link | 1000 ms | 2·2 + 50 + 21 = 75 ms | 13.3x |
| `test_uart_comm_hazard.py`, CRC16 | 240 ms | 2·1 + 1 + 21 = 24 ms | 10x |
| same file, no CRC | 30 ms | 24 ms | **1.25x** |

The no-CRC arm is the outlier and it is the one that fails; the CRC arm was already raised 8x, by
`timeout_for()`, for this same symptom. Measured scheduling gaps, via a 1 ms-tick observer inside the
run: **3 ms idle, 23-26 ms at 8x CPU oversubscription**, and past 30 ms in a loaded full-file run.

**One candidate ruled out rather than assumed**: that the floor's 21 ms GC term — measured on the
*target* — understates a 16 MB Unix-port heap. Measured directly: worst `gc.collect()` pause on that
heap with a mid-file object graph is **2 ms**. The host's collector is fast; this is OS scheduling,
not GC.

**The fix** builds the two tests that assert a *clean* run completes in full (`_hammer_clean`,
`_measure_retention`) at `_TIMEOUT_MS * 8` — the margin the CRC arm already had. A clean run never
consumes the timeout, so this costs no wall clock, and the short budget stays where it genuinely
earns its keep: the fault-injecting tests, whose recovery cycles it makes cheap. Nothing in `src/`
changed, and no assertion was loosened — `ok == 150` and `completed == 120` are still exact.

**Before and after, same load, same binary, same file:**

| | 24 CPU hogs on 4 cores, full file |
|---|---|
| before | `FAIL ..._nocrc` / `95/96 passed` — **3 of 3 runs** |
| after | `96/96 passed` — **5 of 5 runs** |

Unloaded it was 96/96 on both sides, which is why five quiet local runs said nothing.

**The accepted trade-off, stated rather than buried**: neither test would now catch a *latency*
regression below 240 ms. They assert completion and heap retention, not duration, and the CRC arm has
carried exactly this trade-off since `timeout_for()` was written. An observer task measuring the gap
instead was considered and rejected: it would allocate inside the very window
`_measure_retention` goes to such lengths to keep clean.

---

## 7L. Measure B, measured as placement — plan section C built and its bounds derived (2026-09-21)

Plan section C asked for a twin guard asserting **absolute largest-contiguous against free** at the
seam, after `build_system()` and after the starter list, at "the calibrated heap", with thresholds
set from B.6's figures. Built instead as a **placement** guard, because the contiguity framing turned
out not to survive its own premise. What shipped: `tests/_boot_contiguity_probe.py` (the boot driver)
and `tests_scripts/test_digital_twin_boot_contiguity.py` (27 tests, six devices; 22 when 7L.3's
bounds were first derived, and the bounds themselves are 7L.7's).

### 7L.1 Why the plan's own metric was replaced

Two blockers, both measured rather than argued.

- **`scripts/test.sh` hardcodes `-X heapsize=16M` and a test cannot change its own process's heap**,
  so "the calibrated heap" (§1.4's 455k) is unreachable from `tests/`. Shrinking the heap instead is
  worse than useless: the setup batch's own churn peaks near 1 MB on this binary (`alloc` 517,280 ->
  977,152 across one `sysfunct.setup()`), so at a calibrated fill the suppressed arm would force
  reactive collections and stop being a suppressed arm at all. The defect is self-limiting, which is
  exactly §0A.1's third consequence.
- **The plan's metric is heap-size dependent and the replacement is not.** Same code, same arm:

| metric | at `heapsize=8M` | at `heapsize=16M` |
|---|---|---|
| `largest_free_run` / free after the batch, collects live | 93% | 96% |
| `largest_free_run` / free after the batch, suppressed | 64% | 82% |
| **reach above the seam, collects live** | **1,046,688** | **1,046,688** |
| **reach above the seam, suppressed** | **3,336,064** | **3,336,064** |

The reach is **byte-identical** across a 2x heap change; the fraction moves by 18 points. So the
guard asserts reach and needs no calibration, and `test.sh`'s fixed heap size stops being a problem.

### 7L.2 The instrument

`tests_hardware/heap_map.py` — the board tier's own parser — already had what was needed:
`HeapDelta` is "blocks free in `before` and allocated in `after`", position-independent by
construction. The probe supplies the `before` map the board tier never had: a `gc` stand-in
installed on the generated module and
on `system_service` dumps `micropython.mem_info(1)` at its first call — the seam — and then forwards
to the real collect **only on the live arm**. One instrument, both arms, no second image.

`mem_info(1)` allocates nothing, so unlike the bisecting `bytearray` probe it cannot perturb what it
measures and cannot hit §7F.8's own pinning artefact. The metrics are byte offsets relative to the
seam's top survivor: reach (max), median, and the count above a 512 KiB band.

### 7L.3 The bounds as first derived, on the settrace binary — SUPERSEDED by 7L.7

> **These figures are the settrace build's.** §11 item 0 was taken on 2026-09-21 and the plain
> suite moved to a settrace-free interpreter, on which the headline metric here **stops
> discriminating altogether**. The shipped bounds are §7L.7's; everything below is kept because it
> is what the metric choice was originally argued from, and because the contrast is the clearest
> statement of how much the flag distorted these numbers.

Six devices, three repeats. **The batch figures are byte-identical across repeats**; the cumulative
ones vary ~4% with task scheduling.

| position | metric | worst live | best suppressed | bound | margin / headroom |
|---|---|---|---|---|---|
| batch | reach | 278,688 | 2,103,008 | 640 KiB | 2.35x / 3.21x |
| batch | median | 45,056 | 1,174,880 | 192 KiB | 4.36x / 5.98x |
| batch | blocks > 512 KiB up | 0 | 1,110 | 256 | — / 4.3x |
| both lists | reach | 633,344 | 3,530,208 | 1,280 KiB | 2.07x / 2.69x |
| both lists | median | −55,744 | 1,213,632 | 192 KiB | — / 6.17x |

Per-device batch reach, live against suppressed: wozi 278,688 / 2,567,008 (9.2x), dev 239,456 /
3,255,808 (13.6x), arzi 274,592 / 2,103,008 (7.7x), klkizi, grkizi and schlafzi 275,136 / 2,103,072
(7.6x). Every bound is the worst live reading times a margin, and every one sits at least 2.6x below
the best suppressed reading — derived, not fitted, and twin-only (§7G's rule).

### 7L.4 Two claims turned from prose into assertions

- **Retention is arm-independent.** `used_bytes` after the batch: wozi 643,360 live against 643,584
  suppressed, dev 745,344 / 745,728, arzi 577,568 / 577,984 — a 0.05% worst case. §7A.1's finding,
  reproduced on the real `build_system()` rather than a wrapper, and now asserted at 1%: if the arms
  ever diverge on how much *survives*, the collects have started compensating for a leak and
  I.4(f.1)'s justification has changed.
- **A real boot fires exactly the collects the static guards count.** `batch_collects` equals the
  generated module's own `await X.setup()` count + 1 and `starter_collects` equals the observed
  starter count + 1, on all six devices — dev's **11 + 23** matching §7F.9's measured 34 exactly.
  Derived from each list's length, never from the emitted line count: see 7L.5.

### 7L.5 Verified against four injected regressions, and one of them exposed an instrument defect

Each was injected into the real source, regenerated, run, then reverted.

| injected | result |
|---|---|
| per-module collect removed from `codegen.py` | **12 failed** — both positions, all six devices |
| leading batch collect removed from `codegen.py` | **passed 22/22 at first** — see below |
| per-starter collect removed from `system_service.py` | **12 failed** — cumulative + count; batch correctly still passed |
| leading starter collect removed from `system_service.py` | **6 failed** — the count test |

**The second one is the finding.** The effect measurement anchors its seam at the *first* collect, so
deleting the leading collect moved the anchor with it and the shifted baseline hid the change. The
existing static guard (`test_buildgen_generate.py`) did catch it, so the suite was never blind — but
the new test was, and a test that re-anchors silently is the kind of instrument §1.2 catalogues.
Closed by deriving the expected count from each list's own length rather than from the emitted line
count, which makes the anchor's existence a separate assertion. Re-verified: 6 failures.

### 7L.6 What this does not do

- **No board figure** — true when this was written, and **superseded by §7M**, which took the
  board's reading on 2026-09-22 and found the ratios here do *not* transfer at the board's own fill.
  Every number in §7L is twin units; read §7M before quoting any of it about hardware.
- **The settle position is measured and deliberately not asserted on.** Four seconds after the
  starter loop, dev's *suppressed* arm reported a **larger** `largest_free_run` than its live arm
  (10.19–10.47 MB / 64–66% against 9.37–9.47 MB / 59–60%). §7F.9's decay does not merely erase the
  gain, it can invert the ranking — so any guard reading that position would be measuring noise.
- **Section C's file name and tier differ from the plan's.** It is
  `tests_scripts/test_digital_twin_boot_contiguity.py`, not `tests/test_digital_twin_boot_contiguity.py`:
  `mem_info(1)` goes to the platform print rather than `sys.stdout`, so an in-process MicroPython
  test structurally cannot read its own map, and `heap_map.py` is host CPython. Plan C is annotated
  with this.

### 7L.7 Re-derived on the settrace-free interpreter, and the metric had to change (2026-09-21)

§11 item 0 was answered — two Unix-port binaries, the plain suite on the flag-free one — and the
guard was re-measured on it before anything was believed. **The control arm caught the problem by
itself**: on the new binary the two `test_suppressing_the_emitted_collects_breaks_both_bounds`
cases were the only failures, reporting a suppressed-arm batch reach of **77,664 B against a
655,360 B bound**. A guard whose broken configuration also passes is not a guard, and it said so.

**Why the old metric died.** Without the 4-5x allocation inflation the setup batch no longer pushes
the allocation frontier at all: its reach above the seam is **8,160 B in BOTH arms** on arzi,
klkizi, grkizi and schlafzi — byte-identical, zero discrimination — and 8,160 against 12,192 on
wozi. The batch's churn was never the signal; the settrace frame/code objects were most of what
made it look like one.

**What survives, measured across all six devices, three repeats each.** The batch figures are again
byte-identical across repeats; the cumulative ones vary a few percent with task scheduling.

| position | metric | worst live | best suppressed | bound | margin / headroom |
|---|---|---|---|---|---|
| batch | median **depth below** seam | 452,832 | 218,528 | 300 KiB | 1.47x / 1.41x |
| both lists | reach above seam | 16,352 (every device) | 141,632 | 64 KiB | 4.0x / 2.16x |
| both lists | median depth below seam | 356,576 | 108,352 | 256 KiB | 1.36x / 2.42x |
| both lists | blocks > 128 KiB up | **0** everywhere | 98 | 32 | — / 3.06x |

Two things follow. **The discrimination moved to the starter list**, which is §7E.3's finding
arriving from the other direction: the batch alone barely moves the frontier once its churn is real
rather than inflated, while the starter list's 22 tasks still do — 16,352 B live against 141,632 B
suppressed. And **depth below the seam is the better metric anyway**: it is a median, so no single
large allocation can move it, and it measures placement directly rather than through the frontier.

**Re-verified by injection on the new binary**, not assumed: removing the per-module collect from
`codegen.py` fails **13** of the then-22 tests (batch placement on all six devices, the whole sequence on
dev, and the count check on all six). Reverted afterwards.

**One side effect worth recording.** The flag-free interpreter is also faster where it matters:
`test_sensortask_wozi.py` 24.60s → 9.26s (2.7x), `test_system_service.py` unchanged within noise,
`test_asy_wifi_service.py` 114.29s → 114.25s — the wait-bound file does not move, which is exactly
what a per-call allocation cost predicts.

---

## 7M. The board's own placement reading — E1-E4 and T7, and the twin's ratios do NOT transfer (2026-09-22)

§7L built the host guard and derived its bounds; the board had never taken the reading. It has now,
on `dev`, from this branch's own image (`buildDate 2026-09-22T16:11:57Z`), both arms off that one
image with no reflash. **The headline is that the twin's two transferable ratios do not reproduce
on silicon**, which is the outcome the (now deleted) boot-contiguity handover's §3 (B9) named in
advance as "a finding either way" and told this session to record before touching anything.

### 7M.1 The instrument

`tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py` gained the 23-line `_ProbeGc`
port from `tests/_boot_contiguity_probe.py`, so it now dumps a **seam map** at the generated module's
first emitted collect (`batch_00`) — the `before` that `heap_map.delta()` previously had no candidate
for — and can suppress every emitted collect at runtime.

**The arm is selected by a plain global, not argv**, and that was determined empirically rather than
assumed: under `mpremote run`, `sys.argv` reads back `[]` and **assigning** it raises
`AttributeError: 'module' object has no attribute 'argv'`, while `exec "_ARM_OVERRIDE='suppressed'"`
in the same raw-REPL session does reach the run's globals. (Appending to `sys.argv` in place also
works, but leaves the arm at index 0, with no script-name slot — an off-by-one waiting to happen.)

`_report_checked()`'s existing probe readings were left in place, as the handover asked, so the run
stays comparable with §7H.4.

### 7M.2 What the board measures

Board units throughout — 16 B blocks, 12,052 blocks, **192,832 B of heap total**, with the seam at
**~98,720 B**, i.e. the heap is already 51% allocated when the setup batch begins. Metric
definitions are `tests_scripts/test_digital_twin_boot_contiguity.py`'s own, reused verbatim.

**Three repeats per arm, and the ranges are tight — this is signal, not noise.**

| position | metric | live (median, range) | suppressed (median, range) | twin says | board says |
|---|---|---|---|---|---|
| batch | median **depth below** seam | 10,736 (10,736–11,232) | 15,600 (15,408–16,288) | 2.07x live | **0.69x — inverted** |
| batch | reach above seam | 2,576 (2,560–2,896) | 3,952 (3,520–4,000) | no discrimination | **1.53x, correct direction** |
| both lists | median depth below seam | **+976** (624–1,344) | **−1,840** (−1,984..−1,824) | 3.3x live | **sign discriminates** |
| both lists | reach above seam | 20,960 (20,784–21,120) | 19,072 (18,688–19,808) | 8.66x live | **0.91x — no separation** |
| both lists | new blocks > 64 KiB up | 0 | 0 | 0 against 98–726 | **0 in both — structurally mute** |
| both lists | `used_bytes` (retention) | 101,936 | 101,888 | arm-independent to 0.05% | **0.05% — matches exactly** |

Two of those rows need stating in words rather than as a ratio. **The whole sequence's median
straddles the seam**: live sits 976 B *below* it, suppressed 1,840 B *above* it. A ratio across zero
is meaningless, so the honest figure is the **difference, 2,816 B, with the live arm lower** — which
is B10's qualitative claim, and it holds. And the **>128 KiB band the twin uses cannot exist here**:
128 KiB above a seam at 98,720 B is past the top of a 192,832 B heap, so the 0-in-both-arms reading
is an artefact of heap size, not evidence. The table uses 64 KiB instead, and it is 0 in both arms too.

### 7M.3 The pre-batch probe was ruled out as the cause, not assumed innocent

The device script runs `_report_checked("baseline")` before `build_system()`, and on this heap that
probe allocates **132,672 B of a 135,008 B free pool** and frees it — a near-total defragmentation
immediately before the thing being measured, which the twin probe has no equivalent of. That is a
credible explanation for a washed-out effect, so it was tested rather than argued about: a
scratchpad-only variant with that one call removed, two repeats per arm.

| metric | live | suppressed | direction against the committed variant |
|---|---|---|---|
| batch depth below seam | 960 | 2,400 | **no claim — see below** |
| batch reach above seam | 4,888 | 7,192 | still 1.47x, correct direction |
| both lists depth below seam | −1,576 | −5,320 | live still 3,744 B lower |
| both lists reach above seam | 22,032 | 22,928 | still 1.04x, no separation |

Three of the four magnitudes move while their direction does not, so the probe is not what is
suppressing the effect, and the variant was not committed.

**The batch-depth row is the exception and an earlier draft of this section overstated it.** At n=2
the two arms' per-run values are −2,336/+4,256 (live) against −432/+5,232 (suppressed): a spread of
~6.6 KB with the ranges overlapping almost entirely, so the medians' 0.40x is noise and **no
direction is claimed for it here**. The inversion is a finding of the *committed* variant, where the
arms are tight and disjoint (live 10,736–11,232, suppressed 15,408–16,288), not of this one. The
other three no-probe metrics are tight and do support their rows — §7M.5 has every run.

### 7M.4 What this does and does not mean

**What transfers:** the batch's own reach (1.5x, the metric §7L.7 had written off as mute on the
twin), the sign of the whole sequence's median, and the arm-independence of retention.
**What does not:** the batch's median depth (0.69x, inverted) and the cumulative reach (0.91x) —
the twin's two headline numbers, 2.07x and 8.66x.

**The most likely reason is fill, and it is stated as interpretation, not as measurement.** The
twin's own absolute figures — a 452,832 B median depth and a 141,632 B suppressed reach — are each
larger than this board's **entire 192,832 B heap**. With ~94 KB of free space above a seam that
already sits at 51%, there is not the room for "survivors go into low holes instead of stacking above
the churn" to open up the separation a 16 MB heap shows; every board reach observed is 2–23 KB.

**This is not a reason to change anything, and specifically not a reason to touch measure B.**
Retention is arm-independent on the board exactly as on the twin, no new floor is asserted (§7G's
rule), and measure B's *silicon* confirmation was never this metric — §7F's P1–P5 and the tripwire's
5.5x margin stand untouched. What is now recorded is narrower and true: **the placement metric's
ratios are a twin-scale statement, and the board does not reproduce them at its own fill.** The host
guard's bounds remain host bounds; none of them was ever to be copied to the board, and none was.

**T7 closes with the same runs.** `after_starter_loop_end` was read on both arms — the starter list's
own site, which no silicon run had ever measured — and the probe reports `retained=0` there in both,
confirming the reading is a figure rather than a floor.

### 7M.5 Every run, in board units — the handover's own evidence requirement

Board heap geometry, derived by the parser and never converted by hand:
**`block_bytes=16`, `heap_blocks=12052`, `total_bytes=192832`.**

Depths are positive **below** the seam. Both band counts the handover named are included; both are
**0 in every run of every arm**, and structurally so — 128 KiB above a seam at ~98,700 B already
exceeds the 192,832 B heap, and 512 KiB exceeds it by more than 2.5x. Neither band can discriminate
anything on this hardware, which is a property of the board, not a result.

| run | seam B | batch new | batch reach | batch median depth | batch >128K | batch >512K | boot new | boot reach | boot median depth | boot >128K | boot >512K |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 live | 98720 | 53 | 2336 | 11136 | 0 | 0 | 612 | 21056 | 1008 | 0 | 0 |
| E2 suppressed | 98544 | 53 | 3536 | 14368 | 0 | 0 | 629 | 19824 | -2144 | 0 | 0 |
| live rep1 | 98736 | 54 | 2560 | 11232 | 0 | 0 | 616 | 20784 | 1344 | 0 | 0 |
| live rep2 | 98560 | 53 | 2896 | 10736 | 0 | 0 | 604 | 20960 | 624 | 0 | 0 |
| live rep3 | 98560 | 53 | 2576 | 10736 | 0 | 0 | 617 | 21120 | 976 | 0 | 0 |
| supp rep1 | 98720 | 59 | 3520 | 16288 | 0 | 0 | 619 | 19808 | -1984 | 0 | 0 |
| supp rep2 | 98656 | 53 | 4000 | 15600 | 0 | 0 | 630 | 18688 | -1840 | 0 | 0 |
| supp rep3 | 98560 | 54 | 3952 | 15408 | 0 | 0 | 620 | 19072 | -1824 | 0 | 0 |
| live no-probe1 | 96160 | 56 | 4944 | -2336 | 0 | 0 | 610 | 22048 | -1568 | 0 | 0 |
| live no-probe2 | 96192 | 56 | 4832 | 4256 | 0 | 0 | 614 | 22016 | -1584 | 0 | 0 |
| supp no-probe1 | 95648 | 88 | 7408 | -432 | 0 | 0 | 625 | 22944 | -5264 | 0 | 0 |
| supp no-probe2 | 95728 | 54 | 6976 | 5232 | 0 | 0 | 625 | 22912 | -5376 | 0 | 0 |

The two canonical runs' own captured summary output, verbatim:

```
ARM collects                                     | ARM suppressed
HEAP baseline:              free=135008 lb=132672 | HEAP baseline:              free=135040 lb=132608
HEAP after_build_system:    free=100528 lb=91760  | HEAP after_build_system:    free=100592 lb=90160
LISTS starters=22 timers=8 batch_collects=11      | LISTS starters=22 timers=8 batch_collects=11
HEAP after_start_timers:    free=98000  lb=91760  | HEAP after_start_timers:    free=98176  lb=93776
HEAP after_starter_loop_end:free=90944  lb=73040  | HEAP after_starter_loop_end:free=90992  lb=74448
HEAP after_starter_list:    free=89712  lb=63984  | HEAP after_starter_list:    free=89856  lb=65136
HEAP ..._control:           free=89712  lb=49152  | HEAP ..._control:           free=89856  lb=65248
   retained=49152  <- the 7F.8 pinning artefact   |    retained=0
HEAP ..._control_retry1:    free=40496  lb=14928  | (no reread needed)
HEAP ..._production_thresh: free=40560  lb=14928  | HEAP ..._production_thresh: free=89856  lb=65248
COUNTS batch_collects=11 starter_collects=23      | COUNTS batch_collects=11 starter_collects=23
BOOT build_system_ms=1238 timers=790 loop=1790    | BOOT build_system_ms=1123 timers=790 loop=1527
RESULT: PASS 89712 B free, 63984 B largest        | RESULT: PASS 89856 B free, 65136 B largest
```

`retained=0` at `after_starter_loop_end` in both arms is T7's own check. The live arm's
`_control` position hit the pinning artefact at exactly 49,152 B with `retained=49152` and the
script's own reread cleared it — the same event §7G/R16 describe, reproduced here on silicon.

**What is NOT recorded here, and why.** The raw `micropython.mem_info(1)` block maps behind these
figures are 8,370 lines across the twelve runs. They are the parser's *input*, fully reduced by the
table above, and this repo gitignores run logs (`digital_twin_ci_logs/`), so they were not committed
and did not survive the session. Regenerate them with, per arm:
`mpremote connect <dev> exec "import machine; machine.WDT(timeout=8000)" [exec "_ARM_OVERRIDE='suppressed'"] run tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py soft-reset`,
then `tests_hardware/heap_map.py`'s `parse_labelled()`/`delta()` host-side against `batch_00`,
`after_build_system` and `after_starter_loop_end`.


---

## 7N. The 2026-09-22 sitting's own record — the suite runs, and three rows that closed with them

**Image**: `scripts/build_firmware.py dev` from this branch's tip, `buildDate 2026-09-22T16:11:57Z`,
flashed with `picotool load -x -v` (verified OK). One deliberate flash cycle, which is run-sheet
step 3. The board had been left as an ordinary production device at `DebugLevel = 0` (§7J.6); that
was restored to 5 over the serial REPL before any tier ran, since several tests parse a log that 0
silences.

**`errcount` before anything wrote**: all 21 modules clean — every counter 0, every history slot
`N`/0 — recorded verbatim per CLAUDE.md's rule. The board's history allows that reading to be
trusted: the bench host had booted 9 minutes earlier and the board enumerated at 16:51:56, so
nothing had run against it since the 2026-09-19 production setup whose closing `ResetErrors` left
the table clean.

| run | result | against |
|---|---|---|
| **S1** `run_flash_hardware_suite.sh` | **36 passed, 3 skipped, 12 deselected**, 890.53 s | the queue's own `36 passed, 3 skipped, 12 deselected` target — exact match |
| **S2** `run_bench_hardware_suite.sh` | **98 passed, 4 skipped, 27 deselected**, 2509.87 s (41:49) | the queue's `93 passed, 4 skipped, 27 deselected` — **5 more passing**, which is growth in the three bench files that changed since, not a discrepancy |

Both clean, zero failures, and `_require_clean_hardware_run.sh` reported no unexpected skips. The
deselected counts are the wear gates, and they mean this pair does **not** speak for the gated set.

**Three queue rows close on these two runs, with no further board time:**

- **G7** — the two memory gates (`flash/test_memory_stress.py`, `bench/test_memory_stress_bench.py`)
  were widened on 2026-09-22 to read `harness.MEMORY_ERROR_MARKERS` and had never executed since.
  They executed here and passed, so the widened gate does not false-positive on a healthy real board
  — which is what the unit and twin tiers could only argue by construction.
- **T6** — the run-phase memory check on silicon, the same two files, green on this image.
- **T3** — all **14** FRAM device scripts green. This needed no separate invocation: every one of
  them (13 `fram_*.py` plus `sgp40_fram_backup_restore.py`) is driven by a flash-tier test in
  `test_fram_storage.py` or `test_bus_concurrency.py`, and all of those passed in S1 and again in
  S2. The row had assumed a hand-run pass was owed; it was not.

**Contamination note for whoever reads the FRAM logs next.** This sitting ran isolated-driver device
scripts (§7M's ten boot runs) that build their own `AsyFramManager` over the same chip, so
production's first FRAM chunks have been overwritten. The clean table above is the *pre-sitting*
reading and is the one to trust.


---

## 7O. The wear-gated run (S3), and the two-bugs-cancelling defect it was the only way to find

S3 ran on 2026-09-22 after S1/S2 came back clean, which is exactly the ordering D1's standing yes
requires — so the one failure it produced is attributable to the gated set rather than to anything
the default runs would also have shown. That is the whole point of the ordering, and it paid for
itself on the first try.

**First run: `1 failed, 118 passed, 4 skipped, 6 deselected`, 2980.36 s (49:40).** The failure was
`flash/test_reboot_persistence.py::test_config_value_survives_a_genuine_hard_reset` —
`RESULT: FAIL Marker=0 after reboot, expected 424242`.

### 7O.1 The defect is in the test scripts, not in `src/`

`ConfigManager.write_config()` **stages** and hands the flash write to its own task
(`asyncio.create_task(self._flush_staged(...))`, Part F.2 — an inline write disabled interrupts
port-wide and reset the very HTTP connection whose PUT triggered it). `flush_pending()` is what
awaits it.

`reboot_persist_write.py` called `write_config()` and returned with **no further await**, so
`asyncio.run()` tore the loop down with the flush still queued and nothing ever reached flash. The
write reporting `PASS` is consistent: staging succeeded, committing never happened. Production is
unaffected — a real PUT-driven flow keeps the event loop running.

### 7O.2 The same bug in the DebugLevel pair, where two instances of it were cancelling out

A scan of every `device_scripts/` file that writes config found the same omission in
`system_debug_level_raise_for_boot_log_check.py` (both writes) and
`system_debug_level_restore_after_boot_log_check.py`. The board's own filesystem showed what that
had been doing, and it is worse than a failing test:

| file on the board, after the run | held | should have held |
|---|---|---|
| `config_HWTEST_REBOOT.cfg` | `{"Marker": 0}` | `{"Marker": 424242}` |
| `config_HWTEST_DEBUGLEVEL_BACKUP.cfg` | `{"PrevLevel": 0}` | `{"PrevLevel": 5}` |

Both files existed holding `setup()`'s **defaults** — the only write that ever landed. So
`test_boot_import_mechanism_actually_boots_the_real_system` **passed** while backing up the wrong
value and then "restoring" it, and `config_SYSTEM.cfg` kept `DebugLevel: 5` only because the
restore's own write did not flush either. **Two instances of the same bug cancelling.** Fix either
one alone and the bench board silently ends up at `DebugLevel = 0` — the state that makes several
bench tests parse an empty log and fail quietly, and the exact condition §7J.6 warns about.

`isl29125_mechanism_envelope.py` writes config too and is **not** affected: it awaits
`asyncio.sleep_ms(200)` between pushes, so its flushes are scheduled, and nothing it does has to
survive a reset.

### 7O.3 Fixed and verified against the filesystem, not against the test

All three scripts now `await flush_pending()`. The poisoned `PrevLevel: 0` backup was deleted from
the board first — with the restore fixed and that file left in place, the next run would have
faithfully written `DebugLevel = 0`. Re-run of both tests: **2 passed**, and the board's own files
then read `{"Marker": 424242}`, `{"PrevLevel": 5}` and `{"DebugLevel": 5}`.

**The lesson generalises**: a `device_scripts/` file that writes config and then returns has no
event loop left to commit it, so `flush_pending()` is mandatory there in a way it is not in
production code. Two of the three affected scripts were passing tests while doing the wrong thing.
`tests_scripts/test_device_script_config_flush.py` now pins it **per manager**, not per file: each
staged write is matched to a `flush_pending()` on the object that actually holds it, so flushing one
of a cancelling pair does not cover the other, and a `_set_dict_cfg()` write is tracked to its
`.cfgmgr` (the delegation is itself pinned against `src/base_classes.py`). One justified exemption,
whose justification the guard re-derives; verified red against seven injected regressions.

### 7O.4 S3's own status: NOT re-run green end to end, deliberately

**The full gated suite has been run exactly once** (the `1 failed, 118 passed` above). After the fix,
only `test_reboot_persistence.py` was re-run — `2 passed` — and the fix was confirmed by reading the
board's own files rather than by re-running anything else.

A second full gated pass was started and **the owner stopped it (2026-09-22)**: permission to spend
wear covers one run, not a standing licence, and re-running a ~50-minute wear-spending suite to
"confirm green" after a single fixed failure is exactly the loop the gate exists to prevent. That
aborted run reached 15% and did spend six gated tests before it was killed
(`test_bus_concurrency.py`'s five cross/same-device session tests plus
`test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads`); it never reached the
reboot-persistence pair. **So: the gated set's own result stands at one failure, found and fixed,
with the fix verified on the two tests that carried it — and anyone wanting a clean full gated run
has to decide to spend one.**

**"End to end" means 119 of 129 tests.** Ten never executed even with the flag, all by design, so a
green gated run would still not be the whole tier:

| | why |
|---|---|
| **6 deselected** — `test_scd30_real_clock_stretch_never_exceeds_the_configured_timeout`, `test_single_core_timing_headroom_holds_under_normal_full_task_load`, `test_real_hardware_survives_extended_max_speed_hammer_load_with_fram_diagnostics_preserved`, `test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic`, `test_ticks_ms_real_2pow30_rollover` | `long_soak`/`multi_day_rollover`, which both wrappers exclude **unconditionally** whatever flags are passed — queue row S4's territory, and G6's deferred ~12.4-day run |
| **4 skipped** — the two ISL29125 light programs, `test_real_uf2_reflash_and_boot_smoke_test`, `test_spoofed_off_subnet_source_address_is_ignored` | the first two want `--allow-neopixel-sweep` (S3b), the third is `flash_cycle` |

**What a fresh gated pass would actually buy** is not reassurance about the fix — the re-run plus the
on-disk values prove that more directly than a green suite would — but **R1, R4, R5 and R8's reboot
arm**, which this run made reachable and whose results nobody has yet read out. That is the reason to
spend one, if there is one.


---

## 7P. State the bench was left in — READ THIS BEFORE THE NEXT BENCH RUN

Supersedes §7J.6, which described the 2026-09-19 production hand-back. **That hand-back has been
undone**: the board is a test board again, not the quiet LAN device §7J.6 left behind.

| | value |
|---|---|
| firmware | this branch's tip, `buildDate 2026-09-22T16:11:57Z`, flashed with `picotool load -x -v` |
| `DebugLevel` | **5** — restored over the serial REPL before any tier ran, and deliberately left there |
| network | STA on `sensors-bench-fa9707`, DHCP `192.168.85.57`, RSSI -49, NTP synced, reachable as `SensorStationDev.fritz.box` |
| UART link | 713 transfers, 0 failures |

**Config files left on the board.** Two are this session's test residue and are safe to delete; the
rest are ordinary.

| file | note |
|---|---|
| `config_HWTEST_REBOOT.cfg` = `{"Marker": 424242}` | residue of the reboot-persistence test, and the evidence its fix works |
| `config_HWTEST_DEBUGLEVEL_BACKUP.cfg` = `{"PrevLevel": 5}` | residue of the boot-import test. **Check this before the next run of it** — it holding `0` is the §7O.2 defect, and a correctly-flushing restore would then drive `DebugLevel` to 0 |
| `config_NOTIFY.cfg` has `WarnCO2: 1700` | a bench test's own push, not the 1600 default |
| `config_WIFI.cfg`, `config_NTP.cfg` | unchanged, real locale and credentials intact |

**`errcount` at hand-back is test residue, not evidence of a fault**: `FRAM` counter=14 with
`E34/W71/E34/W71/E31/W72/E31/W71/E46/W72`, plus `SGP40 W10` and `WIFI W10`. Those FRAM entries are
the CS-hijack and reset-race fault injectors doing their job. The clean pre-sitting reading is in
§7N and is the one to compare against — and remember the isolated-driver boot scripts overwrote
production's first FRAM chunks either way.

**To hand the board back as an ordinary quiet device**, §7J.6's recipe still applies and has to be
re-applied: delete the two `config_HWTEST_*` files, reset `DebugLevel` to 0, and decide about
`WarnCO2`. Nothing about that was done here, because the bench is expected to keep working.

### 7P.1 Two operational details worth not rediscovering

- **After a `picotool` reflash the board can take far longer than a naive poll window to rejoin the
  AP.** It was unreachable over HTTP for more than 90 s of polling, the AP station table stayed
  empty, and serial was silent — which looks exactly like a failed flash. It was not: at
  `DebugLevel = 0` the serial log says nothing by design, and once `DebugLevel` was raised the next
  boot showed the association completing ~45 s in, then every task healthy. **Raise `DebugLevel`
  before concluding anything from a quiet board**, and prefer the passive `tail_log()` diagnosis
  §7J/CLAUDE.md already prescribe over `exec`, which re-causes the symptom.
- **`sys.argv` cannot be assigned on this port.** `import sys; sys.argv = [...]` raises
  `AttributeError: 'module' object has no attribute 'argv'`, although reading it returns `[]` and
  appending to it works. This matters because `mpremote run` passes no argv at all — the mechanism
  that does work is a plain global set by an `exec` earlier in the same raw-REPL session, which
  reaches the run's globals (`exec "_ARM_OVERRIDE='suppressed'" run script.py`). Verified directly
  on this board, 2026-09-22; `heap_layout_after_full_boot_sequence.py` uses it.


---

## 7Q. Serving at `gc.threshold(-1)` — the board's 4-request ceiling, reproduced, root-caused and fixed [TWIN] (2026-09-23)

**Read §7Q.9 first for anything quantitative.** §7Q.1-§7Q.8 were measured on the 64-bit twin, where
dicts, lists and frames are twice their RP2040 size and strings are not, so its ratios transfer and
its rankings of *which* allocation fails first do not; §7Q.9-§7Q.13 are the 32-bit twin, which has
the board's own object sizes and reproduces its three failing call sites exactly. "The fix" in
§7Q.5 is the first version; the final design is §7Q.11.

The 2026-09-23 bench sitting (§7R.3) found that at MicroPython's own reactive default the board
serves at most **4** concurrent requests without a `MemoryError`, every failure a ~870 B allocation
inside `/status`'s piece coalescing, the largest free run driven to ~800 B. This section is the
same-day twin investigation of it. Everything here is **[TWIN]**; §7R is what silicon then showed.

### 7Q.1 The instrument

- **Frozen Unix port**, §1.4's recipe: `src/`, `ext/`, `build/generated_src/`, `digital_twin/` and
  `frozen_modules/` frozen, the variant's own manifest included. `import sensortask_dev` then costs
  108,512 B instead of ~541,000. Path still wins over frozen on this port (verified), so one module
  can be shadowed from a directory to A/B it — **every arm below shadows the same file**, the control
  an unmodified copy, so the shadow's own compile cost is common to all.
- **Heap 720k**: `digital_twin/_fram_chip.py` allocates a 262,144 B image, so the working heap is the
  remainder. At 720k the control fails at every N from 2 up (the board is clean to 4), so this is
  **harsher than the board**; 780k fails only at N=7 (2 failures), 820k-900k are clean through N=7.
  The system sits on a cliff between 720k and 820k — which is itself the finding's shape (§0A.3's
  knife edge, at runtime).
- **Load**: the sitting's own shape, 12 rounds of N simultaneous requests across `/status`,
  `/sensors`, `/`, `/measurements`, `/networking`, `/system`, from a separate CPython process (Part
  E.9), bodies drained not materialised. Allocation failures counted from the twin's own log.

### 7Q.2 The reproduction

| | board, image A (§4) | twin, 720k |
| --- | --- | --- |
| failing allocation | ~870 B, `/status` coalescing | **863-881 B**, `asy_webserver_service.py:161` (`"," + batch`) |
| worst largest free run at N=7 | 800 B | 672-1,248 B |
| failures at N=7, 12 rounds | 28 lines (~14 failures) | 20-21 |
| same load at `gc.threshold(32768)` | clean | **0 at N=4/7/8**, worst largest run 9.7-45 KB |

### 7Q.3 What one `/status` costs

Priced on a booted, idle system, one collection-free window per call, 3 reps (zero spread):

| | churn |
| --- | --- |
| whole route | **105,472 B for a 6,709 B body** |
| 21 errcount entries | 2,752 B each: `get_error_counter()` 736, `_shape_errcount_entry()` 1,440, `json.dumps()` 320 |
| coalescing those 21 fragments | 15,104 B (`"".join` would be 7,008) |
| pieces emitted | `[234, 209, 64, 101, 880, 881, 863, 871, 872, 865, 869]` |

**The seven ~870 B pieces are the failing allocations**, and they are there because
`_MAX_STATUS_PIECE_BYTES` was 1024. `/measurements` is 10,560 B and `/sensors` 24,544 B; their
largest single `json.dumps()` is 177 and 217 B, their pieces 399 and 584 B.

### 7Q.4 The heap at the instant of failure

A map dumped from inside the `except MemoryError` of a wrapped `_get_status` (no collect needed:
MicroPython collected before raising). Holes counted by size:

| dump | free | runs | ≥128 | ≥256 | ≥300 | ≥512 | **≥870** | ≥2048 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| idle, before load | 179,520-190,336 | ~868 | 322-370 | 160-201 | 125-157 | 81-93 | 39-44 | 5-15 |
| **fail1-fail3** | **100,832-110,432** | ~825 | 291-312 | 112-138 | **74-95** | 26-38 | **0** | 0 |
| idle, after load | 164,768-167,360 | ~910 | 386-397 | 199-204 | 138-156 | 73-80 | 22-27 | 2-3 |

At the instant a ~870 B piece failed, the heap had ~105 KB free and could still have placed **~85
allocations of 300 B, ~125 of 256 B and ~300 of 128 B**. Free space is never the constraint;
the size of the request is.

Whether the heap *recovers* after the load cannot be settled here: with the committed runner the
post-collect largest run went 9.8-18.4 KB idle → 1.5-4.7 KB loaded → **1.5-2.4 KB after 30 s idle**
(no recovery); with the device-script harness the pre-load heap was already at 2.4-6.0 KB and came
back to 2.3-3.8 KB. The two harnesses boot differently. Queue row W1 asks the board.

### 7Q.5 The levers — all at 720k, `-1`, 12 rounds, failures per run

| arm | what it changes | N=7 | N=8 | failing sizes |
| --- | --- | --- | --- | --- |
| control (shadowed copy) | — | 21 | 20 | 863-881 |
| `join` | `+=` ladder → `"".join`, churn −9% | 22 | 21 | 863-881 |
| cap 512 / 256 / 128 | `_MAX_STATUS_PIECE_BYTES` only | 3-5 | 3-5 | **285-300** |
| cap 256 + `join` (+ in-place encode) | also halves a request's peak live set | 7-8 | 9 | 285-300 |
| response gate, 1 / 2 / 3 slots | serialises response *construction* | 8 / 10 / 8 | 12 / 11 / 8 | 285-300 |
| split only, cap still 1024 | errcount entries split, pieces pack closer to the cap | 14 | 13 | **1011-1017** |
| hypothesis arm (not shippable) | history truncated to 3, fragments ~117 B | **0** | **0** | — |
| **the fix, 3 repeats** | cap 256 **and** errcount entries split at history elements | **0, 0, 1** | **0, 0, 0** | 464 (once) |
| the fix, N=5, 3 repeats | | 0, 0, 0 | | |

Three results carry the conclusion:

1. **Allocation size is the variable; churn volume is not.** A 9% churn cut changed nothing; a hand-
   built errcount string that cut the intermediate dicts **raised** churn to 189,888 B and was
   dropped; the fix itself makes **14% more** churn (120,000 B) and removes the failures. This is
   §6A.2's boot-phase finding (size 5 → 9 blocks flips the outcome at constant volume), at runtime.
2. **The failing size follows the largest allocation exactly**: 870 B pieces → 870 B failures; cap
   them and the ~290 B errcount fragments fail instead; pack the split fragments towards 1024 and
   1011-1017 B fail. Only when *every* allocation on the path fits the holes does it stop.
3. **Serialising construction does not help** — even one `/status` under construction at a time
   fails at ~290 B. What consumes the heap's one large run is the whole concurrent request
   population (Request objects, streams, finished responses held while they are written), not the
   builder alone.

The one failure left in the fix's nine runs is **not in this repo's code**: 464 B at
`ext/microdot.py:383`, the `Request` object's own attribute table growing as `__init__` sets ~20
attributes (~232 B on the RP2040's 32-bit words). Vendored, so it is not ours to change; it fits
the holes the board keeps, and it appeared once in ~750 requests at a heap harsher than the board.

### 7Q.6 The model

The idle heap is **one large free run plus hundreds of small holes** — §0A.2's dust, left by import
and boot survivors. A request whose allocations fit the small holes can be served from them
indefinitely. A request that needs a mid-sized block (870 B) can only be served from the large
run. At `gc.threshold(-1)` nothing collects until an allocation fails, so the concurrent request
population — Request objects, streams, response pieces held while they are written — is allocated
progressively up through the whole heap between collections, and whatever of it is live when the
next collection happens stays exactly where it landed: **the collector never moves anything**
(§0A.1). Those request-lifetime objects split the large run, and the next 870 B request finds
~105 KB free and nowhere to put 870 contiguous bytes.

**Why the default GC cannot resolve it**: it does collect — every `MemoryError` above is raised
*after* a full collection that freed all the garbage. What it cannot do is move a live object, and
the obstruction is live objects. **Why `gc.threshold(32768)` hides it**: at 32 KB a collection runs
~3 times per single `/status` in the twin (105 KB of churn), each resetting the allocator's scan to the bottom (§0A.1), so the
request population is repeatedly re-placed low and the large run is never entered. That is a
layout benefit, not stability — CLAUDE.md's standing rule — and it is exactly what the (e) stage
exists to catch.

**On "it is not about survivors"**: the obstruction during load is transient, request-lifetime
objects — that part is right. But the reason the free space *outside* the large run cannot serve a
mid-sized request is the permanent dust from import and boot. Both are needed for the failure; the
fix works by making the transient demand fit the dust, so neither has to change.

### 7Q.7 What it corrects

- **§7H.3's "whether the system is *stable* without the threshold is settled and the answer is yes"**
  holds for the tiers it cites (the unit suite and the twin CI at their default heap sizes, neither
  of which runs real concurrent HTTP under heap pressure). It did not hold for the board under
  combined load until this fix; a note there points here.
- **`SPECIFICATION.md` I.3's "~48x headroom" for the 1024 B cap is withdrawn** — contradicted by
  the board's own ~800 B largest run under load. I.3 now carries the 256 B rule and its reason.
- The twin CI never saw any of this because it runs non-frozen at a 2 MB heap. Checked: the plain
  CI binary at 1250k does not boot, and at 1350k it is clean — its 541 KB of import residue does not
  model the board. A gate would need the frozen port, which the owner decided against (§12, BACKLOG 45).

### 7Q.8 What is not claimed

That the board is stable at 8 or 10: every figure in this section is the twin's, and silicon later
showed neither is (§7R). What is claimed is that the twin reproduces the board's own failure sites
(§7Q.9), which is what made the fix testable before a board was.

### 7Q.9 The 32-bit twin — the board's own object sizes

The 64-bit twin put the next wall at 10 connections in `ext/microdot.py`'s `Request` object (464 B),
but that is a dict: on the RP2040 it is ~232 B, while a 256-character piece is ~272 B on both. A
twin whose pointers are twice the board's ranks the walls wrongly. **Built 32-bit** — `make
BUILD=build-heapprobe32 CC="gcc -m32" CXX="g++ -m32" LD="gcc -m32" MICROPY_PY_FFI=0
FROZEN_MANIFEST=<src, ext, generated, digital_twin, frozen_modules>` with `gcc-multilib` (1.29.0's
Makefile ignores `MICROPY_FORCE_32BIT`; upstream CI cross-compiles instead): 4-byte pointers,
16-byte GC blocks, `import sensortask_dev` 55 KB instead of 108 KB.
**An ad-hoc instrument, never a committed tool or CI gate** (owner, 2026-09-23): nothing of it is
merged, and this section, §7Q.14 and §10 are its documentation — what it is for and how to rebuild it.

**It reproduces the sitting's failure sites exactly**, where the 64-bit twin saw only the first:
`/status` coalescing at ~870 B, `_dump_errcount_entry` at **296 B** (the board logged 296 twice), and
`_get_measurements → _stream_dict_response` at 560-614 B (the board logged 509). Calibrated against
the board's own curve (§4: clean at 4, ~7 failures at 5, ~14 at 7, 12 rounds), shipped code:

| heap | N=4 | N=5 | N=7 |
| --- | --- | --- | --- |
| 500k | — | 24 | 36 |
| 530k | 11 | 12 | 24 |
| **560k** | 6 | **7** | **13** |
| **600k** | **0** | 0 | 2 |

The board sits between 560k and 600k: 560k matches its N=5 and N=7 exactly and is harsher at N=4.
**Both are used below as the two bounds.** Each image's own lwIP cost is taken off the heap — 2,324 B
per connection the image is sized for, byte for byte the board's (the twin's 262,144 B fake FRAM
image lives in the same heap, which is why the absolute sizes are larger than 190,036 B).

### 7Q.10 What each source and route needs — measured, not inferred

`tests_hardware/device_scripts/allocation_need_per_source.py` shapes the heap so no free run exceeds
S, for rising S, and runs every data source and every whole GET route on it; the smallest S at which
a probe succeeds cleanly at every larger rung too is its need. Two instrument defects found and fixed
before any figure was used: the first sieve let lowest-fit put each blocker into low dust instead of
next to its hole, so payloads merged into runs of up to 32 KB (rungs came out 256, 160, 288, 4,576 ...);
the rebuild fills every free block bottom-up with 1-block chain nodes (1-block allocations advance
the scan hint, so they land in address order) and keeps one in every k+1. And a `range()` object in
the fill loop left garbage inside the pattern. It is exact from ~6 blocks up; below that a few
blocks of its own residue floor the reading, which is why sources read "≤ 192 B". Two more rules it
needs: every line printed on a shaped heap is built before the heap is shaped, and the watchdog is
fed per rung on the twin (its fake allocates) and per probe on the board.

| 32-bit twin, `dev` | as shipped | final |
| --- | --- | --- |
| `/status` | **1,024 B** | 320 B |
| `/sensors` | 768 B | 256 B |
| `/measurements` | 512 B | 256 B |
| flat settings routes | ≤ 192 B | ≤ 192 B |
| every individual source | ≤ 192 B | ≤ 192 B |

**The modules were never the problem; the assembly was.** Checked on all six device configurations
on the 64-bit twin: shipped `/status` needs 1,024 B on every one, the fixed routes ≤ 288 B.

### 7Q.11 The final design, and the three walls it met on the way

1. **Errcount entries split at history elements** (the first fix, §7Q.5): 64-bit twin clean at 5-8.
   At 10 it failed in microdot's `Request` (see §7Q.9 for why that ranking was wrong) and in our
   own ~250 B pieces.
2. **Values written, never dumped whole**: `_PieceWriter.add_value()` walks dicts, lists and tuples
   and dumps only keys and scalars, reproducing `json.dumps()` byte for byte — including its rule
   for non-string keys, which quotes the key's *JSON* text (`True` → `"true"`, not `"True"`; found by
   the unit test that pins it). It replaces the errcount splice, and removes the whole-value
   `json.dumps()` a sensor's data dict needed (276 B on `/measurements` at 14). All six routes
   byte-identical to the shipped firmware.
3. **The writer's own list.** A piece made of tiny fragments (`", "`, `": "`, single digits) needs
   a list array as large as the piece: 256-512 B failures at `self._group.append`. The group is now
   collapsed into one string every 16 fragments.

**Cap 256, not 128.** At 128 the list holding a response's pieces grows to 64 slots — a 256 B array,
twice the cap — and at 14 connections failures fell only from ~13 to 7-9, never to zero, for twice
the writes. **Churn**: the first fix made 14% more and still removed the failures; the final design
cuts `/status` 4.5x (70,208 → 15,648 B) and raises `/measurements` 1.5x and `/sensors` 1.1x — which
changes nothing about the outcome, as size, not volume, is what fails.

### 7Q.12 8, 10, and the ceiling — final code, 32-bit twin, 12 rounds per run

| image sized for | at 560k (the board's harsher side) | at 600k (its gentler side) |
| --- | --- | --- |
| 8 | **0, 0, 0** failures (96/96 served each) | |
| 10 | **0, 0, 0** (120/120 each) | |
| 12 | **0, 0** (144/144 each) | |
| 13 | 8, 10 | |
| 14 | 13, 13 | **0, 0** |
| 16 | | **0** |
| 18 | | **0** (216/216) |
| 20 | | 16 |
| 24 | | 33 |

**The owner's target — 10 ground stable at the reactive default — holds at both bounds**, with 8
configured. The real ceiling lies between **12 and 18**, depending on where the board sits between
the two calibrations; image G in the handover's §0 sweeps 4-18 on silicon, which spans exactly that.
Past the wall the failing allocations are the pieces (~250 B), microdot's `Request` table (~232 B)
and the pieces list: nothing large is left, the heap simply runs out of holes of that size.

**Superseded as a prediction.** These runs served the sub-1 KB stub page and could not see a
write-phase failure (§7Q.14); re-run with the real `dev` page the wall stays at 14. But on silicon
the first JSON failures came at 10 (§7R.3): an unthrottled twin serves 50-100× faster than the
board, its requests hardly overlap, and near the wall it is optimistic by two levels or more. The
throughput-matched twin of §7R.4 is the one whose predictions held.

### 7Q.13 The hardware instruments, run against the twin first

Both device scripts and the bench test's own functions ran against the 32-bit twin before any of it
went to a board: a fake `Board` whose `run_isolated()` runs the device script in the twin, driving
the test module's own `sweep_levels()`, tallies and assertions unchanged. The per-source test
passed in 9 s; the sweep passed in 155 s — 48/48, 72/72, 96/96 at N = 4/6/8, and 96 served + 24
refused cleanly at N = 10, zero allocation failures. **Three instrument defects were found this way
and not on silicon**: the first sieve's merged holes (§7Q.10), and in the sweep script an
`_open_conns.get_value()` read without `await` — the counter is async, the coroutine object is always
truthy, so the script saw load forever and never reached its idle-after phase (the first recovery
script's unexplained timeout was the same bug). The twin's own recovery reading from that run: idle
before the load, largest free run 3,296 B and room for 315 blocks of 256 B; idle after, 1,456-2,784 B
and ~235 — partial recovery. The board's answer is queue row W1.

### 7Q.14 The static page — what silicon found and the twin missed (2026-09-23 evening)

**The finding** (§7R.3): on both images the sweep failed on
`allocating 1025 bytes` in microdot's `send_file` body loop (`ext/microdot.py:746`), from N = 6 on
image G. Each `read(1024)` is a fresh 1,025 B bytes object; a failed one raises *after* the `200` and
headers are out, and with HTTP/1.0 and no `Content-Length` the client reads the cut-off gzip body as
complete. Per-level on G: stable at 4, first failure at 6 (all `/`), JSON failures only from 10.

**Why the twin missed it — two gaps, both closed.** (1) The twin mounts `html_stub`, whose index is
under 1 KB: one short read, never a 1,025 B one. These runs now freeze **the `dev` device's own
website** (`scripts/build_website.sh dev`: `index.html.gz` 9,292 B — byte for byte the page the
board served — and `js/app.js.gz` 16,292 B); `dev` carries every module, so its site is the largest
and the most biting. (2) A write-phase `MemoryError` lands in `_serve()`'s `except Exception` and
goes only to `err_s`, which prints nothing at the twin's debug level; the harness now prints every
`err_s`, and the driver checks every body against its `Content-Length` (or the page's known size
where none is sent).

**Reproduced, then fixed** — 32-bit twin, `dev`'s site, `-1`, 12 rounds, fresh boot per level; "cut"
= a `200` whose body is short; failures are the device's own allocation-failure lines:

| heap | N | tip (pre-fix) | fix |
| --- | --- | --- | --- |
| G's, 560k (552,524 B) | 4 | clean | clean |
| | 6 | 2 cut, 2 × 1,025 B | clean |
| | 8 | 10 cut, 10 × 1,025 B | clean |
| | 10 | 18 cut, 1,025 B + 804 B | clean |
| | 12 | 21 cut, 1,025 B + 804 B | 1 × 804 B, all complete |
| | 14 | — | 10 × 500 (249-257 B pieces) — the §7Q.12 wall |
| F's, 560k (571,116 B) | 4 | clean | clean |
| | 6 | 1 cut, 1 × 1,025 B | clean |
| | 8 | 2 cut, 2 × 1,025 B | clean |
| F's, with `/js/app.js` added to the load | 4 / 6 / 8 | — | clean |

The tip arm's first failure at N = 6 on the 1,025 B read is **exactly the board's**, on both heaps.
The 804 B failures are the twin's own: `network.WLAN` is a Python fake whose 200-slot call-log deque
is (200 + 1) × 4 B; on the board it is a C object. (A first pass with the smaller `wozi` site,
7,175 B, gave the same picture with F's first cut only at N = 8.)

**The fix** (SPEC I.3, "Static files"): `_serve_static()` opens the file, hands it to
`send_file(stream=...)`, sets microdot's own per-response `send_file_buffer_size` to 256 and adds
`Content-Length`. No vendored edit. Per-source need on F's heap, `dev`'s site: `route:/` **320 B** (tip 1,536 B),
every JSON route 192-320 B.

**The instruments, re-validated in the twin**: the need test now probes `route:/` through microdot's
own `Response.body_iter()` — passes on the fix, fails on the tip with `route:/` at 1,536 B. Its gate
moved from 384 to **480 B**: the same fixed `/status` measured 336 B in one run and 400 B in another,
because a rung's *effective* size (its measured largest run) wanders within a rung. 480 sits between
rung 24 (384-400 B) and rung 32 (512 B). The sweep test now labels a short body `-truncated` and a
missing length `-unframed`; on the fix every level is complete with zero failures, on the tip every
`/` is `-unframed`. Adding `/js/app.js` to the sweep's load (every page load fetches it next) exposed
one more instrument defect in the twin first: the device script's failure-dump wrapper dropped the
`filename` keyword microdot passes `_get_static`, turning every script request into a 500.

---

## 7R. Serving on silicon: lwIP, the static page, and the connection limit under peak load [HW] (2026-09-23/24)

The silicon record behind `SPECIFICATION.md` H.7's limit of 6, I.3's 256 B bound and B.14.2's
ensemble. Dev bench, RPI_PICO_W, MicroPython 1.29.0. **Every verdict is at `gc.threshold(-1)`**, set
by the device script itself (`mpremote` soft-resets on raw-REPL entry, but rp2's `main.c` runs
`gc_init()` once, outside the soft-reset loop, so the boot entry's 32768 would otherwise still be in force), and every result line carries `GC_THRESHOLD=`. **Stable** = zero
true failures (a short body, a 4xx/5xx, any transport error other than a ceiling refusal) **and** zero
device lines matching `MEMORY_ERROR_MARKERS`, caught-and-logged included. A reset before any response
at the connection ceiling is a **refusal** and expected, not a failure (owner's rule).

**Two load shapes**, and only the second is peak. **Rounds**: 12 rounds of N parallel GETs over
`/status /sensors / /measurements /status /networking /sensors /system /js/app.js` with 0.5 s
pauses. **Peak**: N clients back to back for 60 s over the same mix, thread 0 swapping one GET for
the hammer test's dispatch-only `PUT /sensors {"SGP40": {"SGPResetVOC": true}}` every 3 s, on the
full production task graph. Every static body is checked against a validated idle reference and its
`Content-Length`, every JSON body parsed. One fresh boot per data point. The instruments and how to
rebuild them: §10.

### 7R.1 The images

| image | `max_connections` | PCB / SEG / `MEM_SIZE` | GC heap (linker) | `mem_info` total | what |
| --- | --- | --- | --- | --- | --- |
| A | 7 | 10 / 56 / 14,000 | 190,036 B | — | pre-fix `src/`, the first sitting |
| B, G, G′ | 16 | 19 / 128 / 32,000 | 169,120 B | — | over-provisioned; G′ with both serving fixes |
| F, F′ | 8 | 11 / 64 / 16,000 | 187,712 B | 183,360 B | F′ = static fix |
| H | 10 | 13 / 80 / 20,000 | 183,064 B | 178,816 B | |
| E7 | 7 | 10 / 56 / 14,000 | 190,036 B | 185,664 B | |
| **E6, E6′** | **6** | **9 / 48 / 12,000** | **192,360 B** | **187,904 B** | E6′ = the committed tip |

Every lwIP macro was read back out of each firmware's own translation unit and matched, and every
linker heap equals 187,712 + (8 − L) × 2,324 B to the byte; `mem_info` reports 4,352 B less (the
GC's own tables), and it is the percentage base below. `.bss` A → B grew 20,916 B for 9 connections,
2,324 B each, from two ELFs built hours apart.

### 7R.2 lwIP never bound anything (image A/B, boot entry's `gc.threshold(32768)`)

- **Admission is exact**: A admitted 7 on five probes out of five. A refusal is a **clean FIN ~6 ms
  after connect** — not an RST, a silent drop or a stall.
- **No admission wall below 16**: B admitted 16 on five probes out of five, so the application's own
  cap stops the probe, not lwIP. `LWIP_STATS` was never needed.
- **The GC heap binds first**: B's failures, captured off the serial console, were caught
  `MemoryError`s of 296-862 B inside the pre-fix JSON assembly. **A raised ceiling converts a clean
  refusal into a served-but-broken response**: at the same load A refused above 7 with every admitted
  body complete, while B admitted and answered 500 from N = 7, its 9 extra connections having cost
  20,916 B of the heap that serves them.
- **`PBUF_POOL_SIZE` 16 is enough** (inbound over-commit, `N × TCP_WND` against 12,832 B of pool:
  3.5× on A, 8.0× on B): the pool never surfaced, because real inbound demand is one small capped
  request per connection (`cyw43_lwip.c:281` allocates every received packet from it).
- **Parked connections are cheap**: a full ceiling of 7 held mid-request (sustained by staggered
  recycling, `SPECIFICATION.md` H.7.1) left room for 15 placeable 2,048 B blocks at worst, against a demand of 7.
  That holder recycled after every ~2 s drip rather than at 10 s (fixed 2026-09-24, H.7.1); the
  count's at-ceiling fraction was asserted either way, so the reading stands as a peak one.
- **Independent ensemble audit**: all 18 relevant `#error` conditions in `lib/lwip/src/core/init.c`
  re-derived, with the switches deciding which are live ground-truthed out of the translation unit
  (`LWIP_DISABLE_TCP_SANITY_CHECKS` undefined, `MEMP_MEM_MALLOC = MEM_USE_POOLS = 0`,
  `MEM_ALIGNMENT = 4`, `LWIP_WND_SCALE = 0`, `TCP_MSL = 60000`, `LWIP_NETCONN = LWIP_SOCKET = 0`):
  zero failing conditions on every image. `LWIP_IPV6 = 1`, so `PBUF_IP_HLEN` is 40 and
  `PBUF_POOL_BUFSIZE` 876 B (the checker's two constants were corrected; no verdict changed).
- **Suite runs on image A**: flash tier 36 passed / 3 skipped / 12 deselected; bench tier 103 / 4 /
  27; bench with `--allow-persistence-writes` **124 passed / 4 skipped / 6 deselected**, the first
  clean gated run end to end (queue rows R8 closed, R5's second green run). A baseline for image A,
  not a validation of the tip.

### 7R.3 At the reactive default, before and after the two serving fixes

**Before (image A, rounds, per-boot)**: 4 was the highest clean level — N = 5 / 6 / 7 gave 14 / 18 /
28 allocation lines, each a ~870 B `/status` piece. §7Q is the root cause and the fix.

**After the JSON fix, before the static fix (images F and G)**: **every failure on F up to its
limit of 8 was the static page** — microdot's `send_file` reading 1,024 B per write, a fresh
1,025 B allocation each, cut off **behind a `200` with no `Content-Length`**, so the client saw a
corrupt page as complete. It was probabilistic: 5 failed 1 run in 3, 6 one in 2, 7 and 8 every run.
On G the static page failed from 6 and the JSON pieces only from 10. §7Q.14 is the fix.

**After both (F′, rounds)**: the need test matches the 32-bit twin to the byte — `route:/` and
`route:/status` 320 B, `/sensors` and `/measurements` 256 B, `/networking` 192 B, `/system` and
`/notification` 160 B, every data/config source ≤ 160 B, every errcount entry 96 B. The one-boot
sweep at 4 / 6 / 8 served every body complete with zero allocation lines, 10 gave 96 + 24 refused.
Per boot, 2 to 8 were stable in 12 boots. Idle largest free run before and after the load:
8,944-11,424 → 6,752-10,672 B, free 82,128 → 80,720 B — a partial recovery of contiguity, a full one
of free bytes.

**10 is not reachable on this heap.** G′ (16, 169,120 B) at 10 failed every per-boot run, 3 of 3,
~1 `/status` in 10 answering 500 in every round, each a 242-257 B `_PieceWriter` piece; its one-boot
sweep up to 18 emptied the pool outright — 68-138 B allocations failing in SCD30 and BMP3XX config
reads, FRAM history writes and the device script. H (10, 183,064 B) at 10: 3 × `/status` 500 per
run, in both arms. At 12 on G′ the failures spread to microdot's 232 B `Request` (400s), cut static
bodies (visible now, as `IncompleteRead`) and non-web tasks.

**Free heap under rounds load** (post-collect every ~5.3 s; sampled, so the minimum is an upper
bound on the true peak, and a later peak measurement showed it overstates by ~20 KB at 6):

| image, N | min free under load | min largest free run |
| --- | --- | --- |
| F′, 4 / 5 / 6 / 7 / 8 | 33.3 / 27.7 / 25.7 / 24.6 / 20.7 % | 2,192 / 1,760 / 1,728 / 1,200 / 992 B |
| H, 8 / 9 / 10 | 21.3 / 19.5 / **11.5 %** | 1,408 / 1,024 / **288 B** |

### 7R.4 Peak load, each image at its own limit — the decision data

**True failures, no instrumentation on the device** (`--peak --no-sampler`, one boot per row):

| limit (image) | boots | requests | refused | **true failures** |
| --- | --- | --- | --- | --- |
| **6 (E6 3, E6′ 2)** | **5** | **2,255** | **70.0-70.2 %** | **0** |
| 7 (E7) | 3 | 1,334 | 70.5 % | **0** |
| 8 (F′) | 3 | 1,319 | 70.7 % | **1** (252 B `/status` piece) |

With a sampler: F′ at 8 failed in 3 more of 4 instrumented boots (0.26-0.55 %); H at 9 failed 1.7 %
(`-1`) and 3.2 % (32768). Every failure at 8-10 on every image was the same allocation, one
242-257 B `/status` piece (`_get_status` → `_build_status_pieces` → `_write_errcount_entry` →
`add_value` → `add` → `flush`); no other route failed and every served body was complete.

**Free heap at peak** (`--peak --margin`: a `gc.collect()` every 100 ms, so the exact live set;
production-equivalent adds back the device script's own 2,720 B):

| limit (image) | free at peak | largest free block at the minimum | idle, 0 open |
| --- | --- | --- | --- |
| **6 (E6, 2 boots)** | **21.2-21.7 %** | **1,456-1,504 B** | 44.3-44.6 % |
| 7 (E7) | 14.3 % | 528 B | 41.6 % |
| 8 (F′, `-1` / 32768) | 11.6 / 12.7 % | 512 / 400 B | — |

**The mechanism**, each point measured:

- **The board is CPU-bound at ~2.2 requests/s at every limit from 6 to 9** — completed requests per
  60 s boot are 121-149 at 6, 123-136 at 7, 122-134 at 8. A higher limit serves nothing more; each
  request lives longer (~N / 2.2 s), so more responses are held at once.
- **Each open connection holds ~7.5-8 KB of live heap at peak** (idle-to-peak drop per open
  connection: 45.2 KB / 6 on E6, 53.4 KB / 7 on E7, 48.8 KB / 6 on H), on top of its 2,324 B of
  static lwIP capacity.
- **The wall is a hole too small for one ≤ 257 B piece**, and at the limit's extreme the pool
  empties outright. Zero-failure counts over ~1,350 requests only bound the rate at ~0.2 %, so they
  cannot separate 6, 7 and 8; the heap margin can. Only 6 keeps the conventional 20-30 % free at
  peak with several pieces' worth of contiguous space.
- **~70 % of requests are refused at every limit when as many clients as the limit run back to
  back**, because `_open_conns`
  counts a connection until `_close_writer()` has finished, while its client already holds the
  complete body and has opened the next one. With 8 clients on H the count reached 10. The device's
  own count of reject-when-full closes matches the host's refusals exactly once it is installed at
  webserver creation (before that, host exceeded device by 0-21: the counter started seconds late).
- **`gc.threshold(32768)` does not reduce failures**: ~1.7-2× the collections and more contiguous
  space at 6, but H at 8 gave 1 vs 0 and at 9 gave 6 vs 3 — single runs, not separable from chance.
- **An image built for 8 is not cleaner at 8 than one built for 10** (F′ 4 of 7 boots failing, H 0
  and 1), against the expectation that 4,544 B more heap and a tighter cap would help. Unexplained;
  one untested hypothesis is that refused clients retry at once and every refused accept still costs
  its stream objects and a task.
- **The instrumentation does not cause the wall**: the same 252 B piece fails at 8 with nothing on
  the device but the task graph. The samplers cost ~10-20 % of throughput, so instrumented figures
  are pessimistic; the device script's own code and globals cost 2,720 B (52,960 B for an
  import-only script against 55,680 B), 3,008 B once it gained the rejection counter.
- **The committed image is the measured one**: E6′ built from the tip reads back 9 / 48 / 12,000,
  192,360 B and 187,904 B, identical to E6, and was clean in both peak boots (0 in 890).

**The throughput-matched twin reproduces this.** The 32-bit twin with its serving throttled to the
board's rate (a CPU quota of 3.5 % of one core once it serves, `MAXCONN` patched into the generated
module so admission is real) and its heap calibrated on the peak-load failures (F′ ≈ 564,648 B; H
between 554,000 and 560,000 B) predicted F′ at 7 clean and at 8 ≈ 0.3 %, and silicon matched both;
host refusals equalled device rejections exactly (1,336 = 1,336). It refuses less than the board
below the limit, so its refusal percentages are not used. Unthrottled, the twin serves 50-100×
faster, its requests hardly overlap, and it is optimistic by two levels or more (§7Q.12).

### 7R.5 Anomalies — recorded, not chased

- **One silent reset** in the first E6 collecting boot: output stopped ~40 s into the load with
  33.5 KB free and no error line; watchdog or hard fault, cause lost. 1 in 9 peak-load collecting
  boots, none in any uninstrumented boot.
- **Hotspot fallback after a reset, three times** (after a likely watchdog reset between two tests,
  after flashing F′, after flashing H); `kick_all_stations()` + hard reset recovered it each time.
- **A likely watchdog reset at `mpremote` attach** ~30 s after a test's own teardown reset, ~9 s
  after attaching. Not confirmed.
- **An empty `200` with no `Content-Length`**, twice, from an idle `GET /` during the boot-time WLAN
  drop. **Explained 2026-09-24, off silicon**: `_serve_static()` does set the length, but microdot
  writes the status line and each header apart, and `http.client` reads EOF mid-headers as their end,
  giving exactly `200`, no `Content-Length`, 0 B — so this was a response cut inside its header block
  (checked against a local socket). Fixed by sending the block as one write (SPECIFICATION.md I.3).
- **Two host-side stalls at N = 4** before the static fix (a `URLError` and a 30 s timeout, nothing
  on the device); none in the 12 boots after it.
- **FRAM E31 + W73**, new between the two days' readings: a status byte found not IDLE at a write,
  then block 1 invalid and restored from block 0 — the signature of a block write cut off by a
  reset, most plausibly the silent reset above, recovered by the two-copy scheme.

### 7R.6 Levers past the limit, after the fix [TWIN] (2026-09-23)

The 32-bit twin, unthrottled, heap 528,000 B (calibrated on image G's first JSON failures at 10,
§7R.3), dev's site, `-1`, 12 rounds; failed requests per run at N=10 (120 requests). Unthrottled it
is optimistic (§7Q.12), so only the arms' order carries over, not their absolute levels:

| arm | N=10, failures per run | failing sizes / what else |
| --- | --- | --- |
| the committed fix (control) | 10, 9, 9 | 241-257 B pieces, 804 B; 7 at N=8 |
| response gate, 4 in flight | 1, 2, 2 | 8 of 192 at N=16 |
| response gate, 2 in flight | 2, 2, 3 | 13 of 192 at N=16 |
| `chunk_bytes` 128 | 4, 5 | 124-256 B |
| `chunk_bytes` 64 | 15, 12 | **worse**: 512 B, the pieces list itself |
| lazy JSON (pieces built at write time), 256 / 128 / 64 | 16-19 / 7-9 / 2-7 | **harmful**: truncated `200`s and `400`s, failures after the headers went out |

No lever clears the wall at 10. A gate cuts failures about 5x but never to zero; a smaller chunk
helps only to 128 and 64 moves the failure onto the pieces list; lazy generation turns a clean `500`
into a truncated body. None was adopted: the limit is set by the heap margin (§7R.4), not moved.

## 8. What is committed

**Reverted, 2026-09-18, at the owner's instruction.** Every change this investigation made to
established `src/` and test files was taken back to `claude/automated-build-chain-nuzumw`'s state
so the remediation starts clean: `f6a182d`/`04ef56a` (`src/asy_spi_driver.py`,
`tests/test_asy_spi_driver.py`) and the Tier-0 model pair from `99080ff`
(`tests/_heap_fragmentation_model.py`, `tests_scripts/test_heap_fragmentation_model.py`), plus the
handover paragraph that pointed at it. The findings below stand as measurements — the blocking
settle's datasheet grounding, the §5.1 hazard, and §8.1's lesson that the CS path must keep a
scheduling point per session — and are re-done inside `HEAP_REMEDIATION_PLAN.md` A.1.1 with fresh
tests (A.2). The three defects the Tier-0 pair found in the handover's own instrument sketch are kept here so
the revert does not lose them: its `free_run_profile()` **MemoryErrors on its own probe**
(`held.append(...)` may have to grow the list, and the only region it can grow into is the one
`bytearray(n)` just claimed - pre-size both lists and guard the claim); `gc.collect()` must run
**before** the measurement (measuring pre-collect reports reclaimable garbage as fragmentation);
and `gc.mem_free()` must be read **before** `largest_block()` (the binary search leaves its own
probe allocations behind, enough to report the impossible `largest > free`). Everything after this
paragraph describes the state *before* the revert.

**`f6a182d`** — `src/asy_spi_driver.py`: both `await asyncio.sleep(0.001)` calls in
`SPIDevice.__aenter__`/`__aexit__` replaced with `time.sleep_us(_CS_SETTLE_US)`,
`_CS_SETTLE_US = const(2)`. Plus `tests/test_asy_spi_driver.py` (50/50).

What it buys, measured (figures as amended by §8.1):
- 3,071 B of the 5,501 B per chip-select session; bare session 8,064 -> 4,768 B before the §8.1 fix.
- Whole-boot churn 11,740,992 -> 8,830,208 B (**1.33x**, after §8.1; it was 1.85x before that fix
  restored a scheduling point).
- Removal of a scheduler yield that occurred **while CS was asserted and the bus lock held** (§5.1).
- ~94 ms of pure sleeping per chunk operation — the likely bulk of the 6.4 s `ResetErrors` [HW].

### 8.1 A regression `f6a182d` caused, and the fix

`f6a182d` removed the chip-select path's **only two scheduling points**. The blocking settle is
correct — an `await` between CS assert and deassert hands the loop away with the bus locked — but
with both awaits gone, a burst of one-byte bus commands holds the event loop for its entire
duration. `AsyFramManager` issues 74 such sessions per logger setup, so a logger's FRAM round trip
became one uninterruptible block.

That broke a real test, deterministically, not as a flake:
`tests/test_digital_twin_sensortask_integration.py::test_wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server_and_status_led`
— `AssertionError: real hotspot activation never started the real DNSServer task`. It waits up to
25 s of real time for the WiFi state machine to reach hotspot fallback while the rest of the system
runs, and the starved loop never got it there. **Bisected to a single variable**: reverting only
`src/asy_spi_driver.py` to the base branch's version makes the file pass 13/13; with `f6a182d` it
fails 12/13 in every isolated run. Two CI runs on docs-only commits had already failed — first
`test_uart_comm_hazard`, then this file — which initially looked like runner contention and was not.

**The fix:** `__aexit__` ends with one `await asyncio.sleep(0)`, placed **after** CS is deasserted
and the bus lock released, so it is outside the window the blocking settle protects. That restores a
bounded scheduling point per session while keeping the hazard closed. Cost, measured: **2,785 B per
session** — more than the 896 B a bare `sleep(0)` costs, because the suspension also retains
`__aexit__`'s own frame — which is why the whole-boot figure moves from 1.85x to 1.33x. Per §6A that
extra churn is in the harmless size class for layout (28 blocks, fits 1% of dust holes).

`tests/test_asy_spi_driver.py`: `test_session_does_not_yield_to_other_tasks_while_cs_is_asserted`
asserted no scheduler pass *after* the session as well, which was never the real invariant — it now
asserts the window is closed (CS deasserted, lock released) and that the yield did happen. Added
`test_a_burst_of_sessions_lets_other_tasks_run`, which pins the property the regression violated: 20
back-to-back sessions must yield at least 20 times.

**Reported, not changed:** `I2CDevice` inherits `Lockable.__aenter__`/`__aexit__` unchanged, so an
I2C session burst has no scheduling point either — the same structural property, pre-existing rather
than a regression. `SPECIFICATION.md` F.5.8 explicitly declines to generalise the UART never-block
rule to `asy_i2c_driver.py`/`asy_spi_driver.py`, and no I2C path issues anything like 74 sessions in
a row (the sensor chip inits are 4-12 operations, §4.1), so this is recorded for a decision rather
than fixed here.

What it does **not** buy: contiguity. Measured neutral-to-worse in isolation (§6.7). The commit
message and PR #105 say so explicitly with the numbers, so it cannot be misread as the remediation.

Test-surface note: `test_aenter_releases_the_lock_if_cancelled_during_the_settle_sleep` cancelled a
task *while parked in the removed sleep*, so its premise no longer exists. Replaced with
`test_aenter_has_no_cancellation_point_after_cs_is_asserted` plus
`test_session_does_not_yield_to_other_tasks_while_cs_is_asserted`, which pins the bus-hazard
invariant directly. The `except BaseException` path stays covered by
`test_aenter_releases_the_lock_if_configure_raises`.

**Bus-hazard tiers:** the mock tier was added and the twin tier runs in the suite. The two
real-hardware tiers (`tests_hardware/flash/test_bus_concurrency.py`,
`tests_hardware/bench/test_bus_concurrency_under_api_load.py`) were **not** run — no go-ahead in that
conversation, and CS timing deserves one.

**One unrelated suite failure, attributed not adjusted:**
`tests/test_uart_comm_hazard.py::test_sustained_hammering_never_degrades_or_grows_the_heap_nocrc`
("only 149/150 hammered transactions completed"). That file imports only `_uart_comm_harness` — no
SPI, no FRAM — and passes **96/96 in three isolated runs on the same modified tree**. Its budget is a
scheduler-step count (`limit=300` for 150 transactions) that can miss by one under the suite's
concurrent file execution. CI's `unit-tests` passed.

---

## 9. Quarantined — figures produced by a defective instrument, or since overturned

**Do not reuse any number in this section.** Each is here so it is not resurrected from an old
transcript.

| retracted figure | reason |
|---|---|
| "one logger `setup()` churns **215,872 B**" (and "215 KB") | `mem_alloc()` window truncated by a mid-window collection (§1.2 defect 1). True value **843,232 B** |
| "`_read()` of the 13-byte chunk = **81,696 B**; `_write()` = **78,080 B**" | same truncation. True values §3.3 |
| "one chip-select session ~**1.7 KB** in-path" | derived from the truncated figures. True value **5,501 B** (§3.2) |
| "`sleep(0.001)` = **1,056 B**" | shared-heap harness (§1.2 defect 6). Superseded by §5's 1,440 B |
| ~~"`await asyncio.sleep(0)` = 896 B"~~ — **this retraction was itself wrong** | 896 B is correct: it reproduces exactly on a clean 64 MB heap with a verified window (§6A calibration) and independently matches the handover's own [TWIN] figure. It was quarantined by conflating it with the different forms `sleep(float>0)` = 1,440 B, `sleep_ms(n>0)` = 1,280 B and `sleep_ms(0)` = ~1,152 B. Each form has its own cost; none supersedes another |
| the `bare` control, and the Q10 answer "each SPI transaction alone does not fragment" that rested on it | `bare` injects its whole burst immediately after `fram.setup()` via `_after_fram()` — **one contiguous block early in the batch, not distributed one-per-module** the way the real logger setups are. Since position is decisive (§2.5) it measured the churn-first configuration, not the interleaved one. §6A.1 runs the equivalent at the correct position and it **does** reproduce the defect |
| the claim that churn volume does not control the outcome (§6.1 as first written) | confounded: every rung changed size mix and object count along with volume. See §6A.1/§6A.2 |
| "the FRAM logger retains **nothing** (-224 B)" | below that instrument's resolution. The map diff is ~10x more sensitive: **~60 B per logger**, 16-17 objects per consolidated pass |
| "**7** survivors attributable to the FRAM I/O" | artifact of subtracting two different variants. Measured directly by before/after map dump: **16-17** |
| every "RAM-only logging" result before the `sys.modules` rebinding fix | measured the unmodified FRAM path (§1.2 defect 2) |
| `nobus` (no-op transfers) as an isolation | aborts the protocol, `initialized` 10 -> 1 (§1.2 defect 4) |
| `chunkio_20` cited as "chunk reads are clean" | degenerate — on a fresh chip the status byte reads UNINIT, so every read short-circuits after 3 CS sessions. Only **64 CS for 20 reads**. Proved nothing |
| s4, s6, s7, and the first t1/t2 | read `const()` values off the module; silently diverted the setup path (§1.2 defect 3) |
| one heap-size table (the 41 KB-shifted seam) | branch counters installed ungated (§1.2 defect 5). Re-run gated; the conclusion held |
| the "kept%" metric as a headline | placement lottery, non-monotonic (§1.3) |
| **model: "a collection intervening between churn and survivor births is the mechanism"** | plausible and internally consistent, then **falsified** by §6.5 — base is broken at 16 MB where no collection is forced. Do not rebuild on it |
| **model: "churn sweep extent is the variable"** | falsified: 4 loggers (498 CS sessions) keep 100% in 5/5 runs while 1 logger (126 sessions) keeps 51-62% |
| **model: "interleaving alone is the whole story"** | too glib as first stated; §4 shows the FRAM path is also 36x every other peripheral in transaction count, which is a separate, real defect |
| my prediction that a large heap would clear the defect | **wrong**; recorded in §6.5 |
| **[HW]** `after_starter_list_production_threshold` = **49,152 B**, both arms (§7F.2) | the probe pinned its own buffer and returned the first size that succeeded, `_PROBE_MAX / 4`. Not a layout figure and not the threshold's doing — §7F.8. Both device scripts now report `retained=` and reread |
| **[HW]** §7F.2's `after_starter_list` row read as "what the starter-list collects left behind" | it is taken 4 s into the run phase, past the decay §7F.9 measures. The figures stand; the reading of them does not. Use `after_starter_loop_end` |
| the handover's §2.7.1 twin table | not reproducible at its stated configuration; see §1.4 |
| the handover's §2.4 "JSON-derived strings in `_cache`" hypothesis | refuted: exactly **one** str/bytes survivor in the whole batch (§2.2) |
| the handover's §2.5 "**6** CS sessions per byte-level write" | `get_write_protected()` issues no bus traffic. It is **5**, and only 5 closes the arithmetic (§3.1) |
| the handover's §2.10.1 proposed enforcement metric | at 400k it reads 100% on a heap fragmented to 0.10 contiguity, and its own probe perturbs the result favourably (+67% at 400k, +16% at 560k) because the binary search's collections reset the allocation scan hint |
| "a 3.5x contiguity cliff between 7 and 8 connections" (the first argument for a limit of 7) | sampled **after** the burst with an allocating probe, normalised against the after-boot value. At true peak with `mem_info(1)`, 5 repeats, the within-N spread of placeable 2,048 B blocks (6-12) exceeds the between-N step (0-4) for every adjacent pair from 4 to 16: that metric cannot rank adjacent limits at all |
| "p50 latency grows ~1.3 ms per added connection" | the sweep's burst was `2 x max_connections`, so the load grew with the setting. At a fixed offered load of 4, p50 is flat at 4.2-4.5 ms for limits 4 to 16 [TWIN] |
| "an 18-connection bar" and "~12 KB of free heap needed per connection" | measured with the twin's own `_http_client` inside the DUT's process; every failure was the client's ~5.5 KB body buffer. Draining instead, the same load passed 42/42 (SPECIFICATION.md E.9) |
| "47 connections caught / 63 fatal" as the twin's wall | the transport path in isolation, nothing else running; with every module loaded it lands ~3x lower. An upper bound, never a capacity |
| "7 → 8 costs 7,488 B" | added the ~5,170 B transient live set per connection to the 2,324 B permanent one. The transient is returned (70 served requests leave ~1.6 KB in total, flat, [TWIN]) and belongs to a placement question, not a budget |
| "twin: 10 stable, the ceiling 12-18" (§7Q.12) as a prediction for the board | an unthrottled twin, stub page. Silicon failed at 10 on G′ and H (§7R.3) |
| rounds-load free heap read as the peak (e.g. 25.7 % at 6 on F′) | pauses and 5 s snapshots miss the moment all N allocate; ~20 KB too optimistic at 6 against the collecting peak sampler (§7R.4) |
| the non-collecting peak sampler's heap figure | reads "just after a GC" late (every ~60 ms against ~250 KB/s of churn), biased low by up to 15-30 KB; rp2 has no exact end-of-GC signal. Its verdict and failure counts stand |
| "each admitted connection costs ~13-14 KB at peak plus 2,324 B static" | the 13-14 KB is the E6 → E7 drop in free heap at peak, which already contains the static 2,324 B and idle-to-idle noise; the live set per open connection is ~7.5-8 KB (§7R.4) |

---

## 10. Reproducing this

Nothing in this file's tooling is committed — the harnesses live in the session scratchpad and are
listed so a future session knows what to rebuild rather than rediscover. All need a frozen Unix port
built per §1.4 and run from the repo root with `MICROPYPATH=.frozen`.

| harness | what it does |
|---|---|
| `probe.py` | whole-batch heap-layout probe over the real `src/` object graph; `<cfg> <mode[:param]> <audit 0\|1> [k] [q]` |
|  `solo.py` | §4's per-module census; `<cfg> <nofram\|fram> [audit] [base\|newsettle]` |
| `framsolo.py` | §3.3's standalone FRAM-path pricing, per-phase, with CS and wire-byte counters |
| `hp.py` | heap stats, map dumps, and the independent largest-allocatable-bytearray probe |
| `parse.py` | block-map reconstruction by absolute address (§1.1) |
| `rungs.py` / `cost.py` | §6.1's layer ladder and its per-rung churn harness |
| `sleepbench.py` | §5's sleep-cost scenarios, one process each |
| `ens.sh` / `ens2.sh` | the two perturbation families (§1.3) |
| `audit_check.py` / `constchk.py` | per-variant semantic audits; the `const()` visibility check |
| `probe.py synth` mode | §6A's factorial injector. argv: `<cfg> synth <audit> <pert> <q> <churn_b> <yields> <blk\|coro> <unit> [peak\|trace] [small_n]`. With `small_n >= 0` the three knobs (small objects, yields, hole-proof 1024 B units) are set explicitly and interleaved evenly, which is how §6A.4's confound-free yield sweep is run; with `small_n` omitted the byte budget is held constant instead |
| `probe.py synthpar` / `parplus` modes | §6A.10's concurrent-churn task. `synthpar` no-ops the logger setups (and so starves its own task of scheduling slots - the batch's awaits are what create the parallelism); `parplus` keeps the real batch intact and adds the task on top, which is the one that isolates added parallelism |
| `spread.py` / `saw.py` | survivor decile histogram, heap span and distinct-run count; the fill-sawtooth trace analysis |
| `probe.py synth` arg 12 (`surv_n`) | §6A.11's retained-survivor knob: extra kept 64 B bytearrays per logger setup, interleaved with the churn. `svgrid.py` tabulates the churn x survivor grid |
| `probe.py` args 14-15 (`probe_every`, `s1\|s2\|s8\|s16`) | §0B.1's per-object placement probe. A runtime-built tuple (one allocation, `id()` is its address); allocate first, dump `post<k>` after, and `causal.py` reconstructs the pre-state by freeing the probe's own blocks — the pre-dump order was invalid because `mapdump_live` itself allocates 320 B |
| `probe.py probemod` mode | §0B.4's probe at the REAL survivor birth positions: wraps every module's `setup()` and probes after it returns, with the real FRAM churn untouched |
| `causal.py` / `whatstranded.py` / `holehist.py` | the per-object verdict table; typing of the stranded objects from the map legend; hole-size histogram at any named dump (`import`/`seam`/`after`) |
| `probe.py` arg 13 (`presurv`) | §6A.12's pre-seam partner, hooked on `AsyFramManager.__init__` so the objects land in the construction phase. Works with any mode including plain `base`, which is how the real-churn arm is run. Both retention containers are sized exactly and allocated in-phase — §6A.12's instrument note has the two container artifacts that invalidated earlier attempts |
| `fgrid.py` / `holes.py` / `peak.py` / `hist.py` | in_big + kept% per run; dust-hole occupancy; matched non-collecting peak dumps; the seam hole-size histogram |
| `unitcost.py` / `unit2.py` | per-allocation cost calibration (`bytearray(n)`, bare await, `sleep(0)`) |
| `conc.py` | §0B.6's concurrency instrument: `_task_queue.peek()` at every yield of the real batch, phase-tagged per module `setup()`, with CS/I2C counters. `<cfg> [nofake] [census\|maps]` — `nofake` neutralises the twin's `Timer`/`WDT` task fakes (the real-hardware equivalent), `census` reports net retained bytes per phase, `maps` dumps the map at the seam and after each phase |
| `qdbg.py` / `cattr.py` / `twinpar.py` | the two-task control validating `peek()`; per-module survivor attribution from `conc.py maps`; the count of twin `Timer`/`WDT` fake executions during the batch |
| `fgraph.py` | §3A's instrumented call graph: every method of the six FRAM-path modules wrapped, exact call counts, caller->callee edges, yields and src-level await depth per yield site; `<cfg> <setup\|read\|write> [raw]`. Its byte columns are wrapper-inflated and only the counts/edges are used |
| `fprice.py` | §3A.3's price list: every node in its own raw collection-free window, 8 reps, blank/valid state reset outside the window, `kept` column; `<cfg>` |
| `depth.py` / `depth2.py` / `depth4.py` | the yield-cost-vs-await-depth measurements that exposed §1.2 item 7 (asyncio; multi-yield leaves; plain `yield from` chains with no asyncio) |
| `cmp_settrace.sh` / `sleepcost2.py` | the same measurements on the settrace and settrace-free binaries side by side; the `asyncio.sleep`/`Lock` forms on both |
| `along.py` | per module `setup()`: allocated and retained in the module's own code before, during and after its logger's round trip; twin `Timer`/`WDT` fakes neutralised |
| `fill.py` | post-`build_system()` fill on a large heap, for §1.4's fill-fraction calibration of either binary |
| `probe.py` gc modes | §7A: `gcboot` / `gcboot2` / `gcboot5` / `gcboot10` wrap `SystemService.feed_watchdog()` — the call the generated batch already makes between two modules — and collect after every / every second / fifth / tenth module; `basex` / `gcbootx` additionally run `start_and_check_tasks()`'s own starter loop. `GCTHRESH=<n>` applies a `gc.threshold()` where the generated boot entry applies it, `YCOST=0` corrects the synth budget on the settrace-free binary (§1.2 item 8). `GCUS` reports each collect's own microseconds |
| `gcfloor.py` | §7A.8's board-comparable metric: largest contiguous over free after the batch, with the bare fill recomputed by subtracting the probe's own ~52,700 B of retained instrument, per arm |
| `gcens.sh` / `gcsum.py` / `gcsum2.py` / `gcx.py` / `gch.py` | §7A's ensembles: `gcens.sh <variant> <build> <heapsize> <tag>` emits the 15 perturbation runs; `gcsum2.py` tabulates worst/median/best kept% with retained and free bytes per arm, `gcx.py` the task-list arms, `gch.py` the heap-size x threshold sweep behind §1.5 |
| `proto.py` | §3B: records every CS edge and transfer on the twin's `machine.SPI`/`Pin` for the current path and for each wire-identical prototype (`SyncFramChip`, `ProtoChunk`, `Proto2Chunk`) and asserts the traces equal; prices each in a collection-free window, first with the twin's fakes as they are, then with `machine.SPI.init/write/readinto` and `FramChip.write/readinto` replaced by allocation-free equivalents (the board-equivalent pass — the raw replay of the whole trace then costs 128 B). No argv; uses `build/generated_src/sensortask_dev_wiring_plan.json` |
| `build-heapprobe32` | §7Q.9's 32-bit frozen twin: `make BUILD=build-heapprobe32 VARIANT_DIR=<toolchain>/build_overrides/unix_kbd_intr_variant CC="gcc -m32" CXX="g++ -m32" LD="gcc -m32" MICROPY_PY_FFI=0 CFLAGS_EXTRA=-Wno-array-bounds FROZEN_MANIFEST=<manifest freezing src, ext, generated, digital_twin, frozen_modules>` in `ports/unix`; needs `gcc-multilib`. The generated `dev` module was frozen with `max_connections=64` so admission never caps a sweep |
| `build-heapprobe32`, the details that bit | `gcc-multilib` must be installed (a C program printing `sizeof(void*)` under `gcc -m32` prints 4), and `file` on the binary must say `ELF 32-bit LSB pie, Intel 80386` — the first attempt used `MICROPY_FORCE_32BIT`, which 1.29's Makefile silently ignores, and built 64-bit. The manifest `include()`s `<toolchain>/build_overrides/unix_kbd_intr_variant/manifest.py` and `freeze()`s `src`, `ext`, a copy of `build/generated_src` (with `max_connections` patched), `digital_twin`, `frozen_modules` and a directory holding `scripts/build_website.sh dev <dir>/frozen_website_dev.py`. A pre-fix arm freezes `git archive <rev> src` into its own build dir. A module on `MICROPYPATH` still wins over a frozen one, so `MICROPYPATH=<dir>:.frozen` A/Bs one module without a rebuild — shadow the control too, so the shadow's compile cost is common to every arm. ~2 minutes |
| `maps.py` / `bodies.py`, `equiv.py` / `bigdumps.py` / `respcost.py`, `statparts.py` / `latency.py` | §7Q's analysis helpers: free, largest run and `placeable(n)` per dump (`mem_info`'s `max free sz` is in blocks — ×16 on the 32-bit twin, ×32 on 64-bit; a hard-coded ×32 once doubled every 32-bit figure); a sha256 of every route's whole body per arm, which proved the fix byte-identical on all six routes; a spy on `json.dumps` for each route's largest single dump; one request priced step by step as `gc.collect(); a = gc.mem_alloc(); …`, 3 reps, zero spread; 60 sequential `/status`, median and p90 |
| `validate_sweep_tool.py` | ran the (since removed) silicon sweep's own `run_level()` against the twin with a fake `BenchBridge` and its 45 s post-reset settle capped — the same idea as `validate_bench.py`. On the pre-fix firmware it reported UNSTABLE at 8 from its host-side body check alone, the device printing nothing |
| `sweep.py` / `drive.py` / `boot.py` | §7Q's serving sweep: boot the frozen twin at a heap and threshold (`TWIN_BIN`, `SHADOW` for a module arm), drive N simultaneous requests x R rounds from a separate CPython process — one real socket per request, a `threading.Barrier(N)` so the burst is simultaneous, bodies drained never kept, a 1 s settle between rounds because a slot outlives its response — and count allocation failures from the log. `boot.py` runs the frozen `run_generic_integration` plus a `mem_info` sampler (env `SAMPLE_MS`, `MAPS`; `COLLECT=1` adds a collected dump) |
| `classify.py` | groups a log's `MemoryError` tracebacks by size and the last three frames — how every wall in §7Q.11 was attributed |
| `boot_site.py`, `SITE=1` | §7Q.14: `boot.py` / `twin_wrap.py` with `frozen_html` aliased to `dev`'s own website (`scripts/build_website.sh dev`, frozen into the binary), and (`boot_site.py`) every `err_s` printed so write-phase failures reach the log; `drive.py` checks each body against its `Content-Length` |
| `twin_wrap.py` / `validate_bench.py` | (`twin_wrap.py` repeats `run_generic_integration`'s setup — `prewarm_poll_set()`, the UDP address shim, the FRAM/SCD30 state paths, the device's wiring plan — then `exec`s the script's source; run it on port 80 from a directory holding the device's `config_*.cfg`; `SITE=1` aliases `dev`'s site) runs a device script UNCHANGED in the twin (the setup `run_generic_integration` does first, then the script's own source); `validate_bench.py` imports the bench test module and runs its own test functions with a fake `Board` whose `run_isolated()` is `twin_wrap.py` (§7Q.13) |
| `build-nosettrace` | `make -j8 BUILD=build-nosettrace VARIANT=standard VARIANT_DIR=<toolchain>/build_overrides/unix_kbd_intr_variant "CFLAGS_EXTRA=-DMICROPY_PY_SYS_SETTRACE=0 -Wno-array-bounds" FROZEN_MANIFEST=<scratchpad>/manifest_heap.py` in `ports/unix` — the heapprobe recipe with the flag off, into its own build dir; builds clean with no warnings |
| `combined_load_sweep.py` + `serving_stability_under_combined_load.py` [HW] | §7R's silicon tool, removed from the tree once the limit was settled; last present at commit `4914a25` (`tests_hardware/` and `tests_hardware/device_scripts/`). Host: `DUT_IP=<ip> uv run python tests_hardware/combined_load_sweep.py <levels…> [--threshold T] [--peak [--margin \| --no-sampler]] [--margin] [--raw-dir d]`, one fresh boot per listed level through `Board.run_isolated()` (which arms an 8 s `WDT`), then `kick_all_stations()`, hard reset and a 45 s settle. It substitutes switches into a copy of the device script, validates the idle reference (a 200 whose non-empty body equals its `Content-Length`, retried: every device-script boot drops and rejoins WLAN at ~6 s), classifies each request as ok / refused (`http_client.is_ceiling_close()`) / true failure, and prints one verdict line per level plus the device's allocation lines, its `PEAK_*` lines and a host-vs-device refusal cross-check. Device: sets and prints `gc.threshold`, starts `sensortask_dev.main()`, wraps `_open_conns.increment` to count increments above the limit as soon as the webserver exists (peak mode), and after 20 s runs a 150 s window with one probe — `mem_info(1)` maps every 5 s (rounds), the same after `gc.collect()` (`--margin`), a 20 ms `gc.mem_free()` + `_open_conns.value` low-water sampler (`--peak`), the same collecting every 100 ms (`--peak --margin`, exact live set, verdict not evidence) or nothing (`--no-sampler`, the control) |
| `boot_peak.py` / `drive_peak.py` / `sweep_peak.py` | §7R.4's throughput-matched peak twin. `boot_peak.py`: dev's site aliased, every `err_s` printed, the silicon peak sampler's logic (never collects unless `COLLECT=1`; `PEAK_AT` per open-connection count) and a rejection counter wrapped on `_open_conns.increment` as soon as `sensortask_dev.webserver` exists. `drive_peak.py <port> <N> [dur]`: the silicon `--peak` load. `sweep_peak.py <heap> <thr> <Nlist> <tag>`: a fresh twin per level; env `QUOTA` (% of one core, cgroup v1 `cpu.cfs_quota_us` under `/sys/fs/cgroup/cpu/twintest`, applied only once the twin serves), `MAXCONN` (patched into the frozen generated `sensortask_dev.py` as `max_connections=int(os.getenv("MAXCONN") or "64")`), `SETTLE`, `DUR`; waits 12 s after the load so the last 10 s `PEAK_SUMMARY` holds every rejection, and counts host resets beyond the device's rejections as true failures. Calibrated: `QUOTA=3.5`, F′'s heap ≈ 564,648 B |

Two runtime neutralisations are applied in every harness, and are twin artifacts with no counterpart
on the device: `_fram_chip.FramChip.__init__` shrunk from a 262 KB backing bytearray to 8 KB (the
address space is left unchanged so chunk decoding is identical), and `machine.I2C.log`/`SPI.log`
replaced with a sink. **Note that `digital_twin/machine.py`'s `SPI.write` does `data = bytes(buf)`
and constructs its log tuple as a call argument**, so a sink stops the retention but not the
allocation — hence rung r0's -68,992 B is an artifact, not a real saving.

---

## 11. Decisions put to the owner — the answered ones keep their answer in place

Answered items stay here with the answer stated at their top rather than being deleted, so a
later reader sees what was decided and on what evidence. **Nothing is open here any more.**

0. **Build the twin/test interpreter without `MICROPY_PY_SYS_SETTRACE`** (§1.2 item 7).
   **ANSWERED, owner, 2026-09-21: build it.** Done: `toolchain/setup_toolchain.py` builds
   `build-standard` (flag-free, the rig) and `build-settrace` (`--coverage` only), and
   `scripts/test.sh` picks by mode. It is **not** a second test run — the suite runs once, against a
   different binary — and the allocation-heavy files got faster with it (§7L.7). The guard's own
   bounds had to be re-derived on it, which §7L.7 records. Original framing: a second
   binary for `scripts/test.sh`, `--coverage` keeping its own. Every allocation figure the twin
   produces today, the memory-safety suite's included, carries a per-call and per-resume cost the
   firmware does not have. Touches `toolchain/setup_toolchain.py` and `scripts/`, so it owes
   BACKLOG.md's running list for the owner's next manual two-target chroot run — an owner-run
   periodic check since 2026-09-18, not a gate that blocks the change. The recipe that produced
   `build-nosettrace` is in §10.
1. **Ship the CRC yield-granularity fix (§3.4) on its own merits?** **CLOSED, owner, 2026-09-18:
   "pure wall clock time is not such an issue, don't touch."** `src/crc_checks.py` is not to be
   modified. §7C.3 measured the allocation as a flat 160 B per `_crc` call regardless of buffer
   length, so there was never any memory in it; the 5.8x wall-time cost of per-byte yielding is
   accepted, and the owner's original reason for the yield (a 256 B CRC stalling other tasks) holds.
   Not deferred to BACKLOG — decided.
2. **Are `asy_fram_driver.py`/`asy_fram_manager.py` — and `asy_spi_driver.py` — open for a scoped
   exception, for §3B's restructure?** **ANSWERED, owner, 2026-09-18: yes.** The exception was
   granted for exactly those three files, measure A is built, measured on silicon (§7D) and
   shipped; "Measured, not committed" below is the pre-decision state, kept for its evidence. The
   one sub-decision it left open is item 6, also answered. What the build then measured, against
   the projections below: **9.0x**, not 38x, at the chosen lock scope (§7C/§11 item 6). This item's earlier form proposed cutting *transactions* (one
   2-byte status write instead of two, one WREN envelope per chunk operation): **withdrawn** — the
   owner's account (§3B.1) grounds every one of the 74 CS cycles, and the wire protocol is not to
   change. What remains is the Python shape, and it is enough: §3B's prototype, asserted
   event-for-event identical on the bus, takes a logger `setup()` from 118,144 to 3,072
   board-equivalent bytes (38x) with everything below the lock synchronous and the lock held per
   block operation, and to ~1,300 (~90x) with one acquisition per chunk operation. §7's `syncdeep`
   was the first rung of the same lever. Still an efficiency fix by the model's own account
   (§6A.8; C9), not the remedy — and that is now **measured, not inferred**: on the settrace-free
   build a 38x cut keeps 14% of the seam's big run and a 90x cut 45%, both below the 55% floor,
   with the transition between 90x and 172x (§7A.5). Decisions inside it: the lock hierarchy (§3B.4 lever 3)
   and the yield policy (§3B.5), both yours. Measured, not committed.
   **What the evidence now points at, and what needs your call.** Of the three levers §6A.9 listed,
   two are closed by measurement: (b) pre-allocating every module's permanent objects at construction
   is **refuted** — the mechanism is real but holds only below the churn threshold, and the real
   system's survivor count is already an order of magnitude below its own onset, so that axis is not
   the binding constraint (§6A.12); (c) raising the transients' size class is a restatement of
   cutting small-object churn, priced at a required 40-100x against an achievable ~12x (§6A.8) —
   the achievable side is now 38-90x (§3B), the required side still un-re-derived (§3A.6).
   **Lever (a) — position — was the only candidate the evidence supported before §3B**: defer the per-logger
   `PrintLogHistoryStore.setup()` to one pass after every module's `setup()`, which is item 3 below
   and the only configuration that ever measured an exact zero (§2.5). It is implementable in
   `print_log.py` plus one generated step in `buildgen/codegen.py`, both outside the restricted
   files, and its cost is the persistence window item 3 states.
3. **The ordering guarantee.** **ANSWERED, owner, 2026-09-21: leave as is — do not defer.** The
   persistence window is the deciding cost: between `fram.setup()` and a deferred pass, a module
   failing in its own `setup()` would hold that error in RAM rather than FRAM, and that is exactly
   the evidence CLAUDE.md's read-the-FRAM-logs rule depends on. The owner's race objection stands on
   record alongside it. Worth noting for anyone tempted to reopen it: the exact-zero below was
   measured *before* A + B shipped at 86-89%, so its marginal value on the current design was never
   established. Everything below is the pre-decision analysis, kept for its evidence.
   Deferring only the per-logger `PrintLogHistoryStore.setup()` to one
   pass after the batch is implementable in `print_log.py` plus one generated step in
   `buildgen/codegen.py` (the batch is a single `setup_order` list at `:453-469`), without touching
   the ten drivers — `await self.pr.setup()` is the first line of every module's own `setup()`.
   `AsyFramManager.setup()` stays early; it is harmless. **Cost:** between `fram.setup()` and the
   deferred pass, a module failing in its own `setup()` holds that error in RAM rather than FRAM, so
   it is lost if the device resets first — which is exactly the evidence CLAUDE.md's FRAM-log rule
   depends on. Owner objection on record: solving this by ordering risks race conditions. Counter-
   evidence, for weighing: the setup batch is straight-line cooperative code and
   `start_and_check_tasks()` runs after it, so there are no concurrent tasks to race with; the real
   cost is the persistence window, not a race.

4. **The boot-confined `gc.collect()` exception (§7A) — take it, and on what grounds?**
   **ANSWERED, owner, 2026-09-18: taken.** `SPECIFICATION.md` I.4 gained **(f.1)** on the placement
   grounds sub-point (i) names, mechanically confined by `scripts/lint.sh` and two structural tests,
   with the effect guard added 2026-09-21 (§7L). **Two of the reasons to hesitate below have since
   been closed the other way**: the floor the "still short of the floor" clause measures against was
   **retired** by the owner on 2026-09-19 (item 7, §7G), and sub-point (ii)'s "settle §1.5 first"
   was settled that same 2026-09-18 — the board figure *is* the reactive-default reading by the
   device script's own design, so there was something to fix. (ii)'s "buys nothing measurable at the
   shipped threshold" also reads differently after §7H.3 [HW]: the threshold is what carries B's
   gain into the run phase, so it is not idle there. Everything below is the pre-decision state,
   kept for its evidence. Put by the owner on 2026-09-18 and measured the same day. It works, and at native `gc` defaults it is the
   strongest remedy in this file, with a clean dose-response in the number of collects and **no**
   effect from a single collect at the end. **On the board's own metric at the board's own fill it
   is still short of the floor** (§7A.8): largest-over-free goes from 14.2% to 45.0% after
   `build_system()` and from 8.4% to 57.8% after the task list too, against a floor of 55% in its
   optimistic form and 74% in the form §2.1's own [HW] free figure implies. A 3.2-6.9x improvement
   that lands on the line, not over it. Three things belong in the decision.
   (i) It is **not compaction** — nothing moves; it resets where the *next* survivors are placed
   (§7A.4), so the grounding is placement, not hygiene. (ii) At the `gc.threshold(32768)` the
   firmware's own boot entry already sets, it buys nothing measurable (87% -> 86% worst case), and
   whether the board really runs that way is §1.5's unresolved question — settle that first, because
   it decides whether there is anything to fix. (iii) On the evidence the scheme is the (e)-stage fix
   I.4(f) explicitly forbids rather than defense in depth on top of one (§7A.6), so taking it means
   amending `SPECIFICATION.md` I.4, with the boot-only confinement and the audit that keeps it
   confined written into the rule. The alternative shape that needs no amendment: a design-level fix
   that clears the floor at native defaults on its own, with the collects added on top — priced at a
   ~172x churn cut against §3B's 38-90x (§7A.5). (iv) **Neither lever reaches the floor alone and
   together they are far above it** on the synthetic proxy (§7A.8), but that proxy overstates the
   collecting arm by 25 points against the real path, so the combination needs §3B built - item 2 -
   before it can be measured rather than estimated. If the decision is to be evidence-led, item 2's
   exception is the one that unblocks the measurement item 4 turns on.
   **§7B lays the two side by side** - gain, effort, risk, the combination, whose flaw it is, and a
   recommended order (A first, measured alone; B on top, measured again).

6. **How finely should the SPI bus lock be taken inside the FRAM path?** **Answered by the owner,
   2026-09-18: once per block operation.** Raised by the build rather than an earlier plan, because
   A measured 6.7x where §3B projected 38x and the whole difference was this one scope.
   HEAP_REMEDIATION_PLAN.md A.1.4 had taken the lock per byte-level command and priced that at
   ~1,800 B; the measured cost was **4,544 B** per blank `setup()`, and §3B.3's ~1,800 B is the gap
   between per-block-operation and per-*chunk*-operation locking (lever 3), one rung further down —
   both §3B prototypes already locked per block operation, so the per-command rung was never
   measured there. Rebuilt at the chosen scope, a blank logger `setup()` costs **13,696 B against
   the base branch's 122,880 (9.0x)** and a valid one 9,152 against 80,384 (8.8x), with the wire
   traces byte-identical across both scopes. The cost accepted: a second SPI device waits for a
   block operation (~25 CS, ~600 us) instead of a command (~5 CS, ~100 us); there is no second SPI
   device in any device TOML today. **Lever 3 (per chunk operation) is not taken** — it is worth
   only ~1,800 B more here and moves the lock hierarchy itself, and A.6 reopens it only if the
   combination with the boot collects falls short. §7C/§7C.1 carry the measurement and the residue.

7. ~~**Which position is the 80,000 B floor about?**~~ **Answered the same day, by retiring the
   floor — §7G.** The owner's answer was that the floor is not theirs and does not reflect reality,
   and that what matters is few survivors in the long heap plus contiguous gaps that fit real use
   with a sure margin. The position question dissolves with it: the replacement checks measure
   survivor *placement* directly, at whatever position the script runs, instead of inferring layout
   health from one contiguity number. The original text is kept below because §7F.9's measurement
   still stands on its own.
   **Original:** Put 2026-09-19, off the back of §7F.9, and not
   answerable from this file's own evidence. The tripwire measures right after `build_system()`;
   the floor exists because a real allocation — a JSON response, a read buffer — has to succeed
   **during the run phase**, which is a different moment. Measure B is worth 4-7x at the boot
   position and, on the twin, roughly 2x once the run phase has had a couple of seconds. Both are
   real; they are not the same claim, and only the first is what the tripwire's PASS on silicon
   (§7F.1) certifies. Three ways to read it, and the choice is yours: (i) the boot position is the
   right one, because the worst contiguous demand this firmware makes is at boot and a run-phase
   allocation failure is what the memory-safety ladder's later rungs exist for — then nothing
   changes; (ii) the run-phase position is the right one, and the tripwire should be *moved* there
   rather than the floor changed (the floor itself is not up for lowering — see below); (iii) both,
   as two separate tripwires with separately measured floors. **What is not on the table** is
   widening I.4(f.1)'s exception into the run phase to hold the layout up — that is precisely the
   (e)-stage fix the rule forbids, and §7A.6 already argued it. Plan section C's seam + contiguity
   guard is the design-level answer if the choice is (ii) or (iii), which is one more reason it is
   the next thing to decide.

**One constraint, and it is the opposite of what this section used to say.** The 80,000 B floor was
**retired by the owner on 2026-09-19** — it was never theirs, and it demanded a third of physical
memory contiguously free, which nothing in this firmware needs. It is replaced by three
requirement-derived checks, §7G. What is not to be re-proposed is *re-introducing a fitted floor*:
every threshold in the replacement is derived from §7A.9's measured worst reachable allocation, and
none of them may be raised to fit a board reading. The second, `gc.collect()`/`gc.threshold()` as the remedy — forbidden by
`SPECIFICATION.md` I.4(e)/(f)/(g) and previously rejected by the owner outright (removes the
symptom, breaks with any GC behaviour change, and loads the processor and I/O system) — was
**reopened by the owner on 2026-09-18** as the boot-confined exception above, and is item 4, not a
closed door. The general prohibition for business logic and the run phase stands unchanged.

---

## 12. Not started, carried forward from the deleted handover

- ~~Commit Tier 1 into the repo properly: the retained frozen-port build variant, the runtime
  neutralisations, the calibrated heap size, and the census tooling. Touches
  `toolchain/setup_toolchain.py` and adds a `scripts/` entry, so it owes BACKLOG.md's running list
  for the owner's next manual two-target chroot run (Ubuntu noble/GCC 13 **and** Debian
  trixie/GCC 14) — periodic since 2026-09-18, not a blocking gate.~~ **Decided 2026-09-23 (owner): not committed** — the frozen-port twins,
  64-bit and 32-bit alike, and their tooling stay ad-hoc instruments documented here (§7Q.9, §10),
  never a committed build variant or CI gate. BACKLOG.md item 45.
- ~~The `buildgen` seam + contiguity guard, written test-first and verified to fail when the
  invariant is deliberately broken.~~ **Built 2026-09-21 — §7L**, as
  `tests_scripts/test_digital_twin_boot_contiguity.py` plus `tests/_boot_contiguity_probe.py`, and
  verified against four injected regressions. Its stated metric was **replaced**: "absolute
  contiguity against free" is heap-size dependent, so the guard asserts the reach of each list's new
  blocks above its own seam, which measured byte-identical at 8M and 16M (§7L.1). The perturbation
  is held constant as this item required.
- ~~Fix the stale lint-selection sentence in CLAUDE.md's "Code quality tooling"~~ — **done in this
  session.** It claimed the selection was `E`/`F`/`W`/`I`/`UP`/`B` while `pyproject.toml:104` sets
  `select = ["ALL"]`, which CLAUDE.md itself referenced correctly in four other places.
- ~~Amend the handover's §2.7.1 twin table with §1.4's calibration finding, rather than leaving two
  contradictory tables in the repo.~~ **Moot since 2026-09-22**: that handover was deleted, so the
  second table is gone; §9 keeps it quarantined by name with §1.4 as the reason, which is what the
  amendment was for.
- Optional: rebuild the frozen port from the post-`f6a182d` tree and run the exact same-binary A/B
  (an `oldsleep` inverse-patch mode is already implemented) so the committed code is measured rather
  than approximated by the runtime `newsettle` patch.
