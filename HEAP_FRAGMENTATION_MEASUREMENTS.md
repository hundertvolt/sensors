# Heap fragmentation — confirmed measurements and findings

Temporary file, same convention as `HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md`, whose Part 2 it
continues: delete once its contents are migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`.
The handover states the defect and the ideas on the table; this file is the measured evidence base
built on branch `claude/heap-fragmentation-remediation` (PR #105, base = PR #103's branch).

**Only measurements that survived verification are recorded here.** Figures that were produced by a
defective instrument, or that a later and stronger measurement overturned, are not mixed in — they
are quarantined in §9, named, with the reason, so nobody re-uses them. §1 records the instrument
defects themselves, because each one is a trap a future session will otherwise re-enter.

**Start at §0.** It is the ledger of every hypothesis this investigation tested — whose it was, what
tested it, and whether it is confirmed, suggestive, refuted, withdrawn or still untested. The rest
of the document is the evidence those verdicts rest on. §6A.12's scorecard is the same thing
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
| O2 | Other modules allocate in the same region when instantiating, without pain | **confirmed literally, but an artifact of nesting** | every module's `setup()` is 936-971 KB — but that is its logger's FRAM round trip; own work is 5-18 KB (§4.1, §4.2) |
| O3 | Something inside the FRAM path is plainly inefficient — masses of short-lived allocations | **confirmed and quantified** | 74 chip-select sessions to persist 12 bytes; 40 of the 50 write sessions carry four flag bytes (§3.1) |
| O4 | A shared per-instance buffer would beat short-lived per-call allocations | **refuted as a lever** | hoisting all 80 throwaways saves 3,488 B of 843,040 (0.41%) and fragmentation is no better, mostly worse (§6.2) |
| O5 | It IS findable — fragmentation was always either heavy or absent, never partial | **confirmed, and reproduced from one knob** | allocation size 5 -> 9 GC blocks flips in_big 21 -> 0 at constant volume and yields (§6A.2) |
| O6 | Replace the awaited CS settle with `time.sleep_us(2)` | **implemented; churn win real, contiguity not** | 56% of each session's allocation and a real hazard removed, but neutral-to-worse on layout (§8) — and it caused a regression (§8.1) |
| O7 | Arbitrate the bus with `threading.Lock` + `ThreadSafeFlag` | **refuted** | wrong primitive: only one task may wait on a `ThreadSafeFlag`, and `machine.SPI` is already blocking (§7.3) |
| O8 | The pattern: moderate per-call churn x very many calls x asyncio-friendly frequent yields x emergent across files x running in parallel with long-lived allocation | **confirmed in structure; one element inverted** | plain `bytearray(64)` churn at that position reproduces the defect and exceeds it, so it is not FRAM/SPI/chunk-specific (§6A.1). The yield element measures protective, not harmful (§6A.4) |
| O9 | The sawtooth: churn repeatedly allocates the whole free memory, gc collects often because fill is high, the level sawtooths across the whole heap, and survivors thrown at random points stay where they land, ending evenly distributed | **confirmed** | fill driven to **64 bytes free**, amplitude 272,576 of ~278,000 (§6A.6); survivors smeared across all ten heap deciles at span 96-99% when broken vs the bottom 1-2 deciles at 18-40% when clean (§6A.7) |
| O10 | There is no churn budget: it is a lottery, pure chance plus nonlinearity — a conjunction of parallelism, volume and interleaving, each with a threshold, and the knee is where all conditions are met at once | **confirmed for the conjunction and the absence of a budget; component verdicts differ** | volume x survivor population interact multiplicatively (§6A.11); parallelism suggestive (§6A.10); interleaving inverted (§6A.4). "No budget" now has a mechanism: the churn knee is a property of the *pair*, not of the churn (§6A.11) |
| O11 | The survivor population is itself one of the conditions | **confirmed, decisively** | churn alone 0%, survivors alone -18%, both together **-88%** of the largest free block (§6A.11) |

### 0.2 This session's hypotheses

| # | hypothesis | standing | evidence |
|---|---|---|---|
| C1 | Interleaving of churn with long-lived allocation is the whole story | **withdrawn — too glib** | true as far as it goes, but §4 shows the FRAM path is also 36x every other peripheral in transaction count, and §6A shows size class dominates (§9) |
| C2 | Collections during the batch strand the survivors (collection-stranding) | **refuted by my own test** | base is broken at 560k, 4M *and* 16M, where the entire 8.4 MB of churn fits with room to spare (§6.5) |
| C3 | The churn's sweep *extent* is the variable | **refuted** | no dose-response: 4 loggers (498 sessions) keep 100% in 5/5 runs while 1 logger (126 sessions) keeps 51-62% (§9) |
| C4 | A large heap will clear the defect | **prediction failed, recorded as such** | broken at 16 MB, kept 49%, in_big 41 (§6.5) |
| C5 | Churn volume does not control the outcome | **confounded; restated** | every rung changed size mix and object count along with volume; held fixed, volume *is* monotonic 0 -> 3 -> 21 (§6.1, §6A.1) |
| C6 | The `bare` control shows a bare SPI transaction is harmless | **withdrawn** | `_after_fram()` injects the whole burst as one early block, so it measured the churn-first configuration, not the interleaved one (§9) |
| C7 | Churn and survivors compete for the *same* dust holes, because they are the same size class | **confirmed, quantitatively** | survivors are mean 52 B ~ 2 blocks; a 2-block request fits 82% of the 1,058 seam holes, a 9-block request 21%; measured mid-churn occupancy 82% vs 16% — 82% measured against 82% predicted (§6A.3) |
| C8 | The size threshold is mediated by collection frequency — a large request fails on contiguity and forces an early, shallow collection | **confirmed** | large-unit churn collects at a median 220,864 B still free vs 1,440 B for small-unit churn (§6A.6) |
| C9 | Cutting the 74 chip-select sessions to ~6 will clear the contiguity floor | **withdrawn** | ~12x against a required 40-100x; 70,000 B per logger measures in_big 14 / span 97%, inside the saturated regime (§6A.8) |
| C10 | Loop yields are protective for layout | **confirmed, and confound-checked** | first measured at constant total bytes, which entangled it with small-object count; re-run at fixed small-object count it holds — in_big 21 -> 4 -> 2 as yields rise (§6A.4) |
| C11 | Pre-allocating each module's permanent objects at construction is the remedy the evidence favours | **refuted** | the mechanism is real — the same objects placed pre-seam give in_big 0 and 100% kept where in-window they give 380 and 12% — but it holds only below the churn threshold. At the real 843,232 B dose pre-seam objects are unprotected (kept ~50%), and the real system's 76 survivors are already an order of magnitude below the survivor axis's own onset, so that axis is not the binding constraint (§6A.13) |

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

### 1.2 Six instrument defects, each of which silently produced wrong numbers

Recorded because every one of these is re-enterable, and each was caught only by an explicit audit.

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

Mechanism [SRC]: MicroPython's GC is mark-and-sweep, **non-compacting**, first-fit from a scan hint
that `gc_collect_end()` resets to 0. With no churn, a few dozen small allocations are satisfied out
of the ~950 small dust holes low in the heap and the allocator never reaches the big run. With ~1,000
chip-select sessions sweeping the allocator across the heap, an object born at any moment lands
wherever the sweep has reached.

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

### 3.1 Transaction amplification — the headline finding

[TWIN, counted with audited counters; [SRC] for the structure] One `PrintLogHistoryStore.setup()`
persists a **12-byte** record (2-byte header + 10-byte history deque) and costs **74 SPI chip-select
sessions**.

The arithmetic closes exactly, and was confirmed by independent counting:

```
setup()            = _read() on a blank chip (24 CS) + _write() (50 CS)         = 74
write_into(12 B)   = 2 redundant blocks x 5 byte-level ops x 5 CS per op        = 50
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

[TWIN] Measured with one process per scenario (see §1.2 defect 6), windows verified collection-free.

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
§6A.12.

**Limit of this experiment, and the next step it names.** The knob only *adds* survivors, so the
**sub-76 regime is untested** — and that is precisely where remedy lever (b) operates (pre-allocate
each module's permanent objects at construction, so fewer are born inside the churn window). The
2D shape makes that lever look right for the first time on evidence rather than analogy, but
confirming it needs a variant that *hoists* the batch's own survivors out of the window, which is a
real code change, not a knob. Cells at 400 extra survivors per logger, and at 3,000 churn objects
with 100, are absent because they `MemoryError` — 3,600 retained bytearrays is ~230 KB on a 278 KB
free heap. Out of range by construction, not a defect, and not read as data.

### 6A.13 Survivor hoisting: the mechanism confirmed, the remedy killed

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
at a required 40-100x against an achievable ~12x. **Lever (a), position, is the only candidate the
evidence still supports**, and §2.5's dose-1 result remains the only exact zero ever measured:
byte-identical work, moved after the batch, gives 100% kept and in_big 0.

**Instrument note, a defect worth recording.** The first two attempts at this experiment were both
invalidated by their own container. Growing the retention list with `append()` reallocates its
backing array repeatedly, and each reallocation is a large transient; replacing that with a
pre-sized `[None] * 4096` was worse still — a 32 KB list allocated at import lands **inside** the
big free run and splits it, dropping the control's own seam from 56,800 to 6,368 and making every
arm incomparable. Fixed by sizing each container exactly and allocating it in the same phase as the
objects it holds, so the control allocates no container at all. The control's seam returning to
~56,500 is the check that this is clean.

### 6A.12 Scorecard against the conjunction model

The model that matches the evidence: the defect needs several conditions met at once, each with a
threshold, and above them the outcome is a heavy-tailed lottery rather than a gradient.

| candidate factor | verdict |
|---|---|
| **allocation size class** of the transients relative to the survivors | **decisive, hard threshold** (§6A.2/§6A.3) — 5 vs 9 GC blocks flips it binary at constant everything else, with 82% vs 16% dust-hole occupancy measured and predicted from the hole histogram. The sharpest single knob found |
| **churn volume** | **threshold, then saturation** (§6A.8) — gradual front advance to 8,000 B per logger, saturated from 20,000 B, then flat across a 42x range. **But the threshold is not a property of the churn**: §6A.11 shows it moves with the survivor population, and at a raised population 4,800 B is enough |
| **position** relative to long-lived allocation | **decisive** (§2.5) — the only exact zero found anywhere |
| **parallelism** (churn concurrent with survivor births) | **suggestive**: worse tail and lower median (§6A.10), not established |
| **interleaving / yield count** | **measured in the opposite direction** — protective at fixed small-object count (§6A.4), with a mechanism that explains why. Note this is a layout statement only; §8.1 is what removing yields costs |
| **survivor population size** | **confirmed, threshold, and it interacts multiplicatively with churn volume** (§6A.11) — alone -18%, with a 176x-below-knee churn dose -88%. But the real system sits at 76, an order of magnitude **below** the axis's own onset (795-1,148), so it is not the binding constraint and reducing it cannot help (§6A.13) |

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

## 8. What is committed

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
| `probe.py synth` arg 12 (`surv_n`) | §6A.12's retained-survivor knob: extra kept 64 B bytearrays per logger setup, interleaved with the churn. `svgrid.py` tabulates the churn x survivor grid |
| `fgrid.py` / `holes.py` / `peak.py` / `hist.py` | in_big + kept% per run; dust-hole occupancy; matched non-collecting peak dumps; the seam hole-size histogram |
| `unitcost.py` / `unit2.py` | per-allocation cost calibration (`bytearray(n)`, bare await, `sleep(0)`) |

Two runtime neutralisations are applied in every harness, and are twin artifacts with no counterpart
on the device: `_fram_chip.FramChip.__init__` shrunk from a 262 KB backing bytearray to 8 KB (the
address space is left unchanged so chunk decoding is identical), and `machine.I2C.log`/`SPI.log`
replaced with a sink. **Note that `digital_twin/machine.py`'s `SPI.write` does `data = bytes(buf)`
and constructs its log tuple as a call argument**, so a sink stops the retention but not the
allocation — hence rung r0's -68,992 B is an artifact, not a real saving.

---

## 11. Open decisions — owner's call, put and not yet answered

1. **Ship the CRC yield-granularity fix (§3.4) on its own merits?** `src/crc_checks.py` is under no
   editing restriction. Justified on latency and churn alone; measured **not** to improve
   fragmentation (worst 26,528 vs base 26,784), so it is an efficiency fix, not the remedy.
2. **Are `asy_fram_driver.py`/`asy_fram_manager.py` open for a scoped exception?** The
   transaction-count reduction the §3.1 arithmetic points to — one 2-byte status write instead of two
   1-byte writes, one WREN envelope per chunk operation instead of per byte-level op — is a ~12x
   churn cut, and **§6A.8 now predicts it will not clear the contiguity defect** (70,000 B per logger
   is still inside the saturated regime; the budget is 8,000-20,000 B). It remains worth doing on its
   own merits — 74 bus transactions to persist 12 bytes, 80% of them bookkeeping, plus the ~94 ms of
   sleeping per chunk operation behind the 6.4 s `ResetErrors` — but as an efficiency fix, not the
   remedy. Same for `syncdeep` (§7). Both are inside files CLAUDE.md and `SPECIFICATION.md` C.3.1
   make vendored-adjacent. Measured, not committed.
   **What the evidence now points at, and what needs your call.** Of the three levers §6A.9 listed,
   two are closed by measurement: (b) pre-allocating every module's permanent objects at construction
   is **refuted** — the mechanism is real but holds only below the churn threshold, and the real
   system's survivor count is already an order of magnitude below its own onset, so that axis is not
   the binding constraint (§6A.13); (c) raising the transients' size class is a restatement of
   cutting small-object churn, priced at a required 40-100x against an achievable ~12x (§6A.8).
   **Lever (a) — position — is the only candidate the evidence still supports**: defer the per-logger
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

**Two constraints already settled and not to be re-proposed.** `gc.collect()`/`gc.threshold()` as
the remedy is forbidden by `SPECIFICATION.md` I.4(e)/(f)/(g) and independently rejected by the owner
(removes the symptom, breaks with any GC behaviour change, and loads the processor and I/O system).
The 80,000 B floor is not to be lowered.

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
