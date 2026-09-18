# Heap fragmentation — confirmed measurements and findings

Temporary file, same convention as `HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md`, whose Part 2 it
continues: delete once its contents are migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`.
The handover states the defect and the ideas on the table; this file is the measured evidence base
built on branch `claude/heap-fragmentation-remediation` (PR #105, base = PR #103's branch).

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
- **[HW]** = real `dev` bench board. **This branch had no real-hardware go-ahead** — every [HW]
  figure below is cited from the handover, not re-measured here.
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
| O12 | The FRAM path's churn is an architectural inefficiency of the driver/protocol *construction*: a critical-path run should generate orders of magnitude fewer short-lived allocations, with every integrity feature of the storage kept | **confirmed by a wire-identical prototype** | same 74 CS cycles, same bytes on the bus, asserted event by event; board-equivalent `setup()` 118,144 -> 3,072 B (38x) with everything below the lock synchronous, ~1,300 (~90x) with one lock acquisition per chunk operation (§3B) |
| O13 | `gc.collect()`, confined to the boot lists - start, between each module, end, and the same for the async setup list - keeps the boot's permanent survivors packed at the bottom of the heap by giving each of them a fitting hole low down, and stays forbidden everywhere else. Clarified by the owner, 2026-09-18: survivors are never moved, and packing the *later* ones low is what was meant by "compacted" | **the mechanism is confirmed exactly as stated; the size of the effect falls short of the floor on its own; and it is null at the threshold the firmware ships** | each collect resets the allocator's free-scan index, so the next module's survivors take the lowest fitting hole instead of a hole above the churn's high-water mark - deciles 20/5/4/2/1/5/5/13/4/5 at span 92% become 29/7/0/0/1/0/0/0/32/0 at median gap 224 B (§7A.4), and the number of collects gives a clean dose-response (§7A.2). On the board's own metric at the board's own fill it is worth 3.2-6.9x, reaching 45% of free after `build_system()` and 58% after the task list, against a tripwire of 55-74% that is itself ~5x above the firmware's own worst reachable allocation (§7A.8, §7A.9): the strongest single remedy measured, and still short. At the shipped `gc.threshold(32768)` (§1.5) it changes nothing (§7A.6) |
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

**The single large run is the only source of a large contiguous allocation, so the 80,000 B floor is
a statement about it alone.**

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
median, i.e. nothing. On the evidence it **is** the (e)-stage fix I.4(f) names rather than defense in
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

**Reported, not changed (CLAUDE.md's flag-don't-fix rule).** The 4,096 B cap does not bound what is
allocated, only what is answered: `Request.max_body_length` stays at microdot's 16 KB default, so a
12 KB `PUT` to any route is read into one contiguous buffer before the 413. `ext/microdot.py` is
vendored and never edited; the one-line fix belongs next to the existing
`Request.max_content_length` assignment in `asy_webserver_service.py`. Not this branch's to make -
it is a webserver change, not a heap-layout one - but it is the single allocation that decides how
much contiguity this firmware actually needs.

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
`_handle_status_bytes()` coroutines (18 per blank `setup()`), ~2,300 B of `crc_checks`' `async`
per-byte CRC, and ~5,000 B of the chunk layer's own coroutines and buffers.

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

### 7C.2 The perturbation ensemble on the real path — A removes the lottery, not the fragmentation

§7A.8's protocol, re-run with A in place: `build-nosettrace` rebuilt against the restructured
`src/` through `manifest_heap.py` (so the frozen bytecode is the shipped code, not a live-source
import whose own code objects would sit on the measured heap), `gc.threshold(-1)`, the same
calibrated heaps, `largest contiguous / free` after the batch, `hp.mapdump()`'s own `gc.collect()`
before each reading. The 508k arm is the 10 `k` perturbations §7A.8 published plus its 5 `q` runs;
the 560k arm is the 6 `k` perturbations `base` has, so the comparison is like for like.

| configuration | | largest contiguous | largest / free | clears 55% |
|---|---|---|---|---|
| after `build_system()`, 508k | `base`, 15 | 30,752 - 60,800 | **11.9 - 23.4%** (med 14.3) | 0 / 15 |
| after `build_system()`, 508k | **A, 15** | **31,328 - 31,328** | **12.4 - 12.5%** (med 12.4) | 0 / 15 |
| the whole boot sequence, 560k | `base`, 6 | 23,648 - 24,832 | **8.1 - 8.5%** (med 8.4) | 0 / 6 |
| the whole boot sequence, 560k | **A, 6** | **21,088 - 21,376** | **7.3 - 7.4%** (med 7.4) | 0 / 6 |

**The finding is the second column, not the fourth.** A's largest contiguous block is **31,328 B in
all fifteen runs** where `base` swings by a factor of two. The perturbations are demonstrably still
landing: `A`'s seam-time largest moves with `k` (219,808 → 218,016 B) and its retained bytes rise
monotonically with it, exactly as the injected survivors demand — yet the post-batch outcome does
not move at all. §2.3 said placement is the variable; what made it a *lottery* was the ~1 MB of
same-size-class churn the batch ran through. Remove 9/10ths of that churn and the outcome is decided
by the permanent object graph alone. This is the sharpest confirmation of §0A's model in this file:
the model predicts that with the churn gone the result should become deterministic, and it did,
without being asked to.

**It is deterministic at a worse number than `base`'s median.** 12.4% against 14.3% after
`build_system()`, and 7.4% against 8.4% after the whole sequence. §7B.1 predicted no layout gain
from A alone and that is what happened, but the small loss has a mechanism worth naming, because it
is the cost side of A.1.3's buffer hoisting:

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

So A trades ~7 KB of permanent retention for 9/10ths of the churn, and on this metric that trade is
very slightly negative. **That is the honest I.4(e)/(f) record this row exists for** (HEAP_REMEDIATION_PLAN.md
A.5): A is an allocation-count fix worth 9.0x per logger `setup()`, it removes the variance that made
the defect a lottery, and it does not move the tripwire. The tripwire needs B, or B plus C.

*Instrument note, in §1.2's spirit.* Adding a `len(chunk.__dict__)` call to the attribution script to
count those 17 attributes inflated the hoisted-buffer figure measured immediately after it from 3,200
to 3,520 B — the `__dict__` access allocates 320 B of its own, the same artifact `mapdump_live` has.
The 3,200 B above is from the run without it.

---

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
| the handover's §2.7.1 twin table | not reproducible at its stated configuration; see §1.4 |
| the handover's §2.4 "JSON-derived strings in `_cache`" hypothesis | refuted: exactly **one** str/bytes survivor in the whole batch (§2.2) |
| the handover's §2.5 "**6** CS sessions per byte-level write" | `get_write_protected()` issues no bus traffic. It is **5**, and only 5 closes the arithmetic (§3.1) |
| the handover's §2.10.1 proposed enforcement metric | at 400k it reads 100% on a heap fragmented to 0.10 contiguity, and its own probe perturbs the result favourably (+67% at 400k, +16% at 560k) because the binary search's collections reset the allocation scan hint |

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
| `build-nosettrace` | `make -j8 BUILD=build-nosettrace VARIANT=standard VARIANT_DIR=<toolchain>/build_overrides/unix_kbd_intr_variant "CFLAGS_EXTRA=-DMICROPY_PY_SYS_SETTRACE=0 -Wno-array-bounds" FROZEN_MANIFEST=<scratchpad>/manifest_heap.py` in `ports/unix` — the heapprobe recipe with the flag off, into its own build dir; builds clean with no warnings |

Two runtime neutralisations are applied in every harness, and are twin artifacts with no counterpart
on the device: `_fram_chip.FramChip.__init__` shrunk from a 262 KB backing bytearray to 8 KB (the
address space is left unchanged so chunk decoding is identical), and `machine.I2C.log`/`SPI.log`
replaced with a sink. **Note that `digital_twin/machine.py`'s `SPI.write` does `data = bytes(buf)`
and constructs its log tuple as a call argument**, so a sink stops the retention but not the
allocation — hence rung r0's -68,992 B is an artifact, not a real saving.

---

## 11. Open decisions — owner's call, put and not yet answered

0. **Build the twin/test interpreter without `MICROPY_PY_SYS_SETTRACE`** (§1.2 item 7) — a second
   binary for `scripts/test.sh`, `--coverage` keeping its own. Every allocation figure the twin
   produces today, the memory-safety suite's included, carries a per-call and per-resume cost the
   firmware does not have. Touches `toolchain/setup_toolchain.py` and `scripts/`, so it is behind
   the two-target clean-chroot gate; the recipe that produced `build-nosettrace` is in §10.
1. **Ship the CRC yield-granularity fix (§3.4) on its own merits?** `src/crc_checks.py` is under no
   editing restriction. Justified on latency alone now — 448 B per CRC on the real VM, not 16,800
   (§3A.6); measured **not** to improve fragmentation (worst 26,528 vs base 26,784), so it is an
   efficiency fix, not the remedy.
2. **Are `asy_fram_driver.py`/`asy_fram_manager.py` — and `asy_spi_driver.py` — open for a scoped
   exception, for §3B's restructure?** This item's earlier form proposed cutting *transactions* (one
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
3. **The ordering guarantee.** Deferring only the per-logger `PrintLogHistoryStore.setup()` to one
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

4. **The boot-confined `gc.collect()` exception (§7A) — take it, and on what grounds?** Put by the
   owner on 2026-09-18 and measured the same day. It works, and at native `gc` defaults it is the
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

**One constraint already settled and not to be re-proposed.** The 80,000 B floor is not to be
lowered. The second, `gc.collect()`/`gc.threshold()` as the remedy — forbidden by
`SPECIFICATION.md` I.4(e)/(f)/(g) and previously rejected by the owner outright (removes the
symptom, breaks with any GC behaviour change, and loads the processor and I/O system) — was
**reopened by the owner on 2026-09-18** as the boot-confined exception above, and is item 4, not a
closed door. The general prohibition for business logic and the run phase stands unchanged.

---

## 12. Not started, carried forward from the handover

- Commit Tier 1 into the repo properly: the retained frozen-port build variant, the runtime
  neutralisations, the calibrated heap size, and the census tooling. Touches
  `toolchain/setup_toolchain.py` and adds a `scripts/` entry, so it triggers the two-target
  clean-chroot pre-push gate (Ubuntu noble/GCC 13 **and** Debian trixie/GCC 14).
- The `buildgen` seam + contiguity guard, written test-first and verified to fail when the invariant
  is deliberately broken. It must assert **absolute contiguity against free** at the seam and after,
  not a ratio between two probes, and must hold its own perturbation constant (§9, last row).
- ~~Fix the stale lint-selection sentence in CLAUDE.md's "Code quality tooling"~~ — **done in this
  session.** It claimed the selection was `E`/`F`/`W`/`I`/`UP`/`B` while `pyproject.toml:104` sets
  `select = ["ALL"]`, which CLAUDE.md itself referenced correctly in four other places.
- Amend the handover's §2.7.1 twin table with §1.4's calibration finding, rather than leaving two
  contradictory tables in the repo.
- Optional: rebuild the frozen port from the post-`f6a182d` tree and run the exact same-binary A/B
  (an `oldsleep` inverse-patch mode is already implemented) so the committed code is measured rather
  than approximated by the runtime `newsettle` patch.
