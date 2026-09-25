# Heap fragmentation — how to measure it

How to get a heap-layout or serving-memory figure worth believing, on the digital twin and on the
board: what the allocator does, which instruments and metrics work, the traps that have silently
produced wrong numbers, how to calibrate the twin, and how to rebuild the instruments. **It holds
method, not results.** Current-state facts and rules live where they are enforced — `SPECIFICATION.md`
Part I (I.2's settled decisions, I.3's bounded assembly, I.4(e)/(f)/(f.1)/(g)), H.7 and B.14.2 —
and the silicon-side rules for serving under load are `tests_hardware/README.md`'s "Measuring heap
and serving under load". This file is the reasoning those rules come from.

**The measurement record is archived, not deleted.** The investigation's full evidence (PR #105
onwards, to 2026-09-24: every table, ensemble, silicon sitting and quarantined figure) is this file
as of commit `12640c2`: `git show 12640c2:HEAP_FRAGMENTATION_MEASUREMENTS.md`. A citation written
**"archive §7R"** names a section of that version; **"§M3"** names a section of this one. Read the
archive's §9 before reusing any old number — it lists the figures a defective instrument produced.

Provenance markers, where a claim below carries one: **[SRC]** read from the code or the pinned
MicroPython v1.29.0 source; **[TWIN]** measured on a frozen Unix port; **[HW]** the `dev` bench board.

---

## M1. What a heap measurement is measuring

**The allocator** [SRC, `py/gc.c` at v1.29.0]:
- **Lowest-fit over one fixed heap area.** `gc_alloc()` takes the first free run that fits, scanning
  up from a hint; no size classes, no best-fit, no split heap on either port.
- **The hint advances only on a one-block allocation**, retreats on every free below it, and every
  collection resets it to zero. So a collection changes *where the next allocations land*.
- **A collection happens only when an allocation cannot be satisfied** at `gc.threshold(-1)`, the
  real default; `gc.threshold(n)` adds one after every n bytes allocated.
- **Nothing ever moves.** Mark-and-sweep, no compaction; `del` frees nothing until the next sweep.

**The placement law** [TWIN, confirmed per object with no counterexample]: a long-lived object is
placed inside the heap's large free run if and only if, at the instant it is allocated, no lower free
run can hold it — and it stays there, splitting that run. Only multi-block objects are at risk (a
one-block request always finds a hole). Transient churn pushes the heap towards that condition but is
self-limiting, because a transient that cannot be placed triggers the collection that restores the
holes; irreversible consumption by permanent objects is what moves the boundary. The heap therefore
runs on a knife edge: whether a given birth lands low or high is a coincidence of timing, and a few
kilobytes of badly placed survivors can cost tens of kilobytes of contiguity while free memory barely
moves. Full account: archive §0A.

**Four consequences for method, and every trap in §M3 is one of them ignored:**
1. **Consumption and layout are different quantities.** Always report both — bytes used or free,
   *and* where the survivors are or how large the largest run is. Either alone misleads.
2. **The outcome is a coincidence count.** A single run cannot tell a remedy from phase luck;
   ensemble it (§M3.10), and expect variants to fail to compose.
3. **Position decides.** The same image reads completely differently depending on what the heap held
   before the measurement (§M3.9). Compare only like positions, or use a delta that cancels them.
4. **The GC threshold changes placement**, not retention: the same bytes survive at either setting,
   but a threshold's frequent collections keep resetting the hint. Every figure must name the
   threshold it was taken at (§M3.8).

---

## M2. Instruments and metrics

### M2.1 The block map — the instrument of choice

`micropython.mem_info(1)` prints the GC's own per-block allocation map, headed by `max free sz`: the
longest free run, **in blocks** [SRC]. It **allocates nothing**, so it cannot perturb what it
measures; it is **exact**, not a search; and it **carries position**. Verified equal to the
bisecting probe to the byte on the twin.

- **Block size**: 16 B on the RP2040 and on the 32-bit twin, 32 B on the 64-bit Unix port. A
  hard-coded ×32 once doubled every 32-bit figure — derive it from the binary.
- Two or more consecutive all-free lines print as `(N lines all free)`: reconstruct by **absolute
  address**, never by counting printed lines.
- On the board `mem_info` writes to the platform print, not `sys.stdout`, so the device cannot parse
  its own map: capture it and parse host-side with `tests_hardware/heap_map.py`.
- **A truncated capture reads as a heap with an enormous free run at the end** — the direction that
  turns a regression into a pass. `tests_scripts/test_heap_map_parser.py` pins the parser for that.
- **`HeapDelta`** (blocks free in a `before` map and allocated in an `after` map) is independent of
  what the heap held before, and a **lower bound**: a block occupied in both maps is never attributed,
  even if its first occupant was freed and a new survivor took its place.

### M2.2 The bisecting `bytearray` probe — kept only as a cross-check

`_largest_block()` binary-searches the largest allocatable `bytearray`. Its traps:
- **It can pin its own buffer.** In some call contexts the just-freed probe survives the collect;
  every larger attempt then fails and the search returns exactly the first size that succeeded, always
  `_PROBE_MAX >> k` (e.g. 49,152 of 196,608). **The tell is exact**: `gc.mem_alloc()` after a collect
  is higher by precisely the returned figure. The device scripts print it as `retained=` and
  `_report_checked()` re-reads while it is non-zero. A round `_PROBE_MAX >> k` value is suspect on
  sight. Mechanism: archive §7F.8.
- It only ever **understates**, and it allocates — its collections reset the scan hint, biasing a
  layout favourably — so it runs after the last map dump, never before one.
- Collect **before** measuring (else reclaimable garbage reads as fragmentation), and read
  `gc.mem_free()` **before** the probe (its leftovers can report the impossible `largest > free`).
- A free-run profiler that holds its claims in a list must pre-size the list, or growing it lands in
  the region just claimed and raises on its own probe.
- **Host-side, cross-check it against the map.** They measure the same run by different means, so a
  disagreement means one of them is wrong.

### M2.3 Pricing an allocation

- **`mem_alloc()` deltas undercount silently when a collection fires inside the window.** Check the
  identity `free_before - free_after == alloc_after - alloc_before`, and size the heap so no collection
  is possible (the twin used `-X heapsize=64M` for churn work). This one defect once understated a
  figure 3.9x.
- **One operation, priced**: `gc.collect(); a = gc.mem_alloc()`, the operation, `gc.mem_alloc() - a`,
  repeated (3-8 reps) with any state reset *outside* the window; a non-zero spread means the window
  is not clean.
- **Twin absolute bytes need the flag-free binary** (§M3.7), and even there they are the twin's, not
  the board's (§M4.1).

### M2.4 Which metrics work

| metric | verdict | why |
| --- | --- | --- |
| `new_above(N)` from a `HeapDelta` across the boot | **works** | what the boot itself placed in the top N bytes; independent of suite position; a lower bound |
| `free_above_top_survivor` | **works** | absolute: free space above the highest live block. Separated the arms 14-34x on the twin. Position-dependent by nature |
| largest free run (`max free sz`) | works, with a used/free figure beside it | contiguity alone cannot say whether it is layout or consumption |
| survivors' reach / median depth relative to the seam's top survivor | **works on the twin** | heap-size independent (byte-identical at 8M and 16M), so it needs no calibration; the depth is a median, so no single allocation moves it |
| `in_big`: survivors landing inside the seam's largest free run | works for layout experiments | counts the mechanism directly |
| `placeable(n)`: free runs that fit n bytes, at true peak | works for serving | answers "can the next piece be placed" |
| fraction of the seam's largest run kept (`kept%`) | **does not** | non-monotonic in every dose series — it is the lottery itself |
| count of free runs above a size | **does not** | reads backwards: a fragmented heap has *more* medium holes |
| allocation span (`alloc_span_pct`) | diagnostic only | a couple of objects at the extremes saturate it |
| largest/free compared across heap sizes | **does not** | fill-dependent; moved 18 points on a 2x heap change with the code unchanged |
| contiguity sampled after a burst, with an allocating probe | **does not** | misses the peak and perturbs the layout |
| the twin's placement ratios, applied to the board | **does not** | the board did not reproduce them at its own fill (archive §7M.4); host bounds stay host bounds |

**Assert `new_above` and `free_above_top_survivor` together**: they fail for different reasons, and
the difference is the diagnosis — the absolute one failing while the delta passes says the heap was
colonised *before* the boot ran.

### M2.5 Thresholds are derived, never fitted

1. Enumerate every externally drivable allocation path (request body, static file chunk, response
   pieces, DNS and UART buffers, FRAM chunk) and take its **largest single contiguous allocation**
   from the source. That is the **worst reachable allocation** — 16,384 B through Microdot's unbound
   `max_body_length` when derived (archive §7A.9), 2,048 B since `SPECIFICATION.md` I.6 bound both
   limits.
2. Set every layout check as a stated multiple of it, and write the multiple down.
3. **Never raise a threshold to fit a board reading.** The retired 80,000 B floor was ~69 % of one
   healthy measurement and so encoded whatever that board happened to do.
4. A derived threshold's first silicon run can fail; **that is a finding, not automatically a
   regression** — it says something the derivation assumed is untrue.

`tests_hardware/flash/test_memory_stress.py` carries the current set (≤ 100,000 B used, nothing
newly placed in and ≥ 16,384 B free above the top survivor, a ≥ 32,768 B run), deliberately not
lowered to the new 2,048 B worst case. A gate between measured rungs (`_MAX_ROUTE_NEED`, §M6) sits
*between* two rungs, because a rung's effective size wanders within it.

---

## M3. Traps that silently produced wrong numbers

Each was caught only by an explicit audit, and each is re-enterable. Occurrences: archive §1.2, §9.

1. **Collection inside a pricing window** — §M2.3's identity, every time.
2. **Mocking by rebinding a module attribute misses `from x import name` consumers**, who bound the
   original at import. Rebind across `sys.modules` and assert the count rebound.
3. **An underscore-named `micropython.const()` scalar is inlined at compile time and is not a module
   attribute** — reading one raises `AttributeError`, which a broad `except` hides. Inline the
   literal in probes (a `const()` holding a dict *is* present).
4. **A substitution that changes control flow is not an isolation.** Every stub or no-op arm needs an
   audit that the bus work is byte-identical (chip-select, transfer and sleep counts) and the outcome
   unchanged, before its number means anything.
5. **Allocating instrumentation perturbs the layout.** Gate counters on an audit flag and never take
   a headline from an audit run; run any allocating probe after the last map dump; add no
   `gc.collect()` during the phase being measured.
6. **Scenarios sharing one heap are not independent.** One process per scenario.
7. **`MICROPY_PY_SYS_SETTRACE` allocates a frame and a code object on every call and generator
   resume**, callback or not [SRC, `py/profile.c`]. It inflated every twin byte figure 4-5x and
   non-uniformly (a yield cost 896 B with it, 0 B without), and it can make the wrong mechanism look
   right. Price bytes on the flag-free binary (`build-standard`); `--coverage`'s `build-settrace`
   carries the flag. **Any constant calibrated on one binary** (a per-yield cost, a probe's retained
   bytes, a heap size) must be re-derived on the other.
8. **The GC threshold is inherited, not reset.** rp2 runs `gc_init()` once, before the soft-reset
   loop, and `main.py` only in the friendly REPL; `mpremote`'s first act on attach is a Ctrl-C, and
   `main.py` sets `gc.threshold(32768)` only after importing the device module. So a device script's
   threshold is `-1` or 32768 depending on attach timing, and back-to-back scripts inherit the
   previous one's. **Every heap-measuring device script sets its own threshold at module level and
   prints `GC_THRESHOLD=` on every result line; a result that does not name its threshold is void.**
   `tests_scripts/test_device_script_gc_threshold.py` enforces it. Twin harnesses that import
   `sensortask_<dev>` directly never run the boot entry and so sit at `-1` unless they set it.
9. **Position decides the answer** [HW]. `Board.run_isolated()` interrupts the running firmware and
   never resets, so a device script builds inside whatever heap `main.py` has been living in: freshly
   flashed and deep in a suite, the same image read the same free bytes and a 70 % smaller largest
   run. A standalone reading is a controlled cost comparison, not a layout reading. Name the position
   on every line: `after_build_system`, `after_starter_loop_end` (the starter list's own site), and
   `after_starter_list` (settled 4 s after the loop's end — the run phase, where most of a boot-time
   placement gain has already decayed).
10. **Ensemble every layout comparison.** Two perturbation families: a retained `bytearray` of *k*
    blocks allocated at the seam (a global offset), and *q* extra transient allocations per bus
    session (a phase shift spread through the batch); ~15 runs per variant. A variant is robust only
    if it holds across both.
11. **The twin's fakes allocate where the board's C objects do not.** The fake FRAM's 262,144 B
    image (shrink it to 8 KB for layout work, address space unchanged; keep it for serving work),
    `machine.SPI.write`'s `bytes(buf)` and log tuple (a sink stops the retention, not the
    allocation), the `Timer`/`WDT` fakes (neutralise them), `network.WLAN`'s call-log deque (an
    804 B allocation the board never makes), and the watchdog fake (feed it per rung, not per probe).
    Attribute a failure to a fake before calling it a finding.
12. **The twin hides write-phase failures unless told not to.** A `MemoryError` after the headers
    are out lands in `_serve()`'s `except` and goes only to `err_s`, silent at the default debug
    level: print every `err_s`, and check every body against its `Content-Length`. A static page
    that fits one read (the retired `html_stub/`) cannot exercise the read loop — freeze the real site.
13. **Device-script habits** (the rest are `tests_hardware/README.md`'s four): build every line the
    script will print *before* shaping the heap; under `mpremote run`, `sys.argv` reads `[]` and
    cannot be assigned, so select an arm with an `exec`'d global; a wrapper around a route handler
    must pass through every keyword Microdot passes (`_get_static` takes `filename`); an `await`-less
    `get_value()` is a coroutine object, always truthy — read `.value`.
14. **Read the FRAM `errcount` before anything clears it**, and remember that a device script
    building its own `AsyFramManager` writes production's first chunk (CLAUDE.md's FRAM-log rule).
15. **Re-derive a tool's printed summary from its raw output** when a label looks wrong.

---

## M4. Twin calibration

### M4.1 What transfers

**Counts** (sessions, objects, calls, yields) transfer to the board directly. **Ratios** between arms
measured on the same binary transfer. **Absolute bytes do not**: blocks are 32 B on the 64-bit port
against the board's 16 B, and the 64-bit twin doubles dicts, lists and frames while leaving strings
alone — so it also **ranks allocation walls wrongly**. Quantitative serving work uses the 32-bit twin
(§M5.2), which has the board's own object sizes and reproduced its failing call sites exactly.

### M4.2 Heap size by fill fraction, never by copying a number

1. On a large heap, measure the bare system's `used` after `build_system()` (and after the starter
   list, if the run goes that far).
2. Choose the heap so that fill matches the board's (~44 % after `build_system()` [HW]).
3. **Subtract the instrument's own retained bytes** — a probe's imports, arrays and wiring plan
   (~52,700 B for the layout probe on the settrace binary) sit before the seam and shift fill.
4. Re-derive after any change of binary, manifest or object graph.

**Undersizing inverts the diagnosis**: at 59 % fill the construction phase looked like the whole
problem and the setup batch looked harmless. Last derived: ~455k bare on the flag-free binary, 508k
under the probe to `build_system()`, 560k to the starter list (archive §1.4).

**Serving is calibrated against the board's own failure curve instead**: run the same rounds load
(N = 4/5/7, 12 rounds) at a series of heaps and bracket the heap whose failure counts match the
board's (the 32-bit twin bracketed at 560k-600k, archive §7Q.9). Take each image's lwIP cost
(2,324 B per connection it is sized for) off the heap, and **throughput-match** the twin with a CPU
quota, because an unthrottled twin is optimistic near the wall (`SPECIFICATION.md` E.8).

### M4.3 When calibration is impossible, measure something heap-size independent

`scripts/test.sh` runs every file at a fixed `-X heapsize=16M` and a test cannot change its own heap.
Shrinking it would also make the suppressed arm's churn force collections and stop being suppressed.
So the committed twin guard (`tests_scripts/test_digital_twin_boot_contiguity.py`) asserts
**placement relative to each list's own seam** — reach above it and median depth below it — which
is byte-identical at 8M and 16M, and it runs a suppressed control arm that must *violate* every bound,
or the guard is not a guard. Its bounds are twin bounds; none is ever copied to the board.

### M4.4 A faithful frozen twin

- Freeze `src/`, `ext/`, `build/generated_src/`, `frozen_modules/` **and `digital_twin/`** — on the
  board `machine` is firmware, so freezing the fakes is the faithful analogue. Import then costs a
  fraction of the source-loaded port's.
- Include the **variant's** manifest (`variants/standard/manifest.py`, or the kbd-intr override
  variant's), not `$(PORT_DIR)/variants/manifest.py` — the latter omits `extmod/asyncio`.
- **A module on `MICROPYPATH` still wins over a frozen one**, so `MICROPYPATH=<dir>:.frozen` shadows
  one module for an A/B without a rebuild. Shadow the control arm too (an unmodified copy), so the
  shadow's compile cost is common to every arm.

---

## M5. Building the instruments

### M5.1 Committed

| instrument | what it measures |
| --- | --- |
| `tests_hardware/heap_map.py` (+ `tests_scripts/test_heap_map_parser.py`) | parses `mem_info(1)` captures; `HeapDelta`, `new_above()`, `free_above_top_survivor`, largest run |
| `tests/_boot_contiguity_probe.py` + `tests_scripts/test_digital_twin_boot_contiguity.py` | the twin placement guard: a `gc` stand-in dumps the seam map at the first emitted collect and forwards to the real collect only on the live arm — one instrument, both arms, no second image |
| `tests/test_asy_fram_allocation_budget.py` | the FRAM path's allocation budget, one per binary |
| `tests/test_asy_fram_wire_trace.py` | the FRAM path's chip-select/transfer trace, held byte-identical across any restructure |
| `device_scripts/heap_headroom_after_full_system_build.py` | flash-tier layout after `build_system()`: before/after maps, probe with `retained=`, a control reading at the unchanged threshold |
| `device_scripts/heap_layout_after_full_boot_sequence.py` | the boot sequence at each named position; the `_ProbeGc` seam map; arms selectable at runtime (§M3.13); counts starters to find the loop's real end |
| `device_scripts/allocation_need_per_source.py` | the need sieve (§M6.1) |
| `device_scripts/serving_at_default_gc.py`, `heap_under_connection_ceiling.py` | serving at `-1`; heap with the connection ceiling held open |
| `bench/test_serving_heap_at_default_gc.py`, `bench/test_heap_under_connection_ceiling.py`, `flash/test_memory_stress.py` | the host sides, with `sweep_levels()`, tallies and the derived assertions |
| `tests_scripts/test_device_script_gc_threshold.py`, `test_device_script_config_flush.py` | §M3.8's and the config-flush habit's static enforcement |

### M5.2 Interpreter builds

- **`build-standard` / `build-settrace`** — `toolchain/setup_toolchain.py` builds both; plain
  `scripts/test.sh` uses the flag-free one.
- **`build-nosettrace`** (a frozen flag-free twin), in `ports/unix`:
  `make -j8 BUILD=build-nosettrace VARIANT=standard VARIANT_DIR=<toolchain>/build_overrides/unix_kbd_intr_variant "CFLAGS_EXTRA=-DMICROPY_PY_SYS_SETTRACE=0 -Wno-array-bounds" FROZEN_MANIFEST=<manifest>`.
- **`build-heapprobe32`** (the 32-bit twin, ~2 min):
  `make BUILD=build-heapprobe32 VARIANT_DIR=<toolchain>/build_overrides/unix_kbd_intr_variant CC="gcc -m32" CXX="g++ -m32" LD="gcc -m32" MICROPY_PY_FFI=0 CFLAGS_EXTRA=-Wno-array-bounds FROZEN_MANIFEST=<manifest>`.
  **Pitfalls**: `gcc-multilib` must be installed, and `file` on the result must say
  `ELF 32-bit LSB pie, Intel 80386` — 1.29's Makefile silently ignores `MICROPY_FORCE_32BIT` and
  builds 64-bit. The manifest `include()`s the override variant's `manifest.py` and `freeze()`s
  `src`, `ext`, a copy of `build/generated_src` with `dev`'s `max_connections` patched high (so
  admission never caps a sweep), `digital_twin`, `frozen_modules`, and the output of
  `scripts/build_website.sh dev <dir>`. A pre-fix arm freezes `git archive <rev> src` into its own
  build dir.

**Both frozen twins are ad-hoc instruments, never a committed build variant or CI gate** (owner,
2026-09-23). This section is their documentation.

### M5.3 Ad-hoc harness shapes

Scratchpad tools, rebuilt from these descriptions when needed (names from the archive's §10):

| shape | how it works |
| --- | --- |
| layout probe (`probe.py`) | imports the real device module, builds the graph, dumps maps at the seam and after the batch; modes wrap `SystemService.feed_watchdog()` (the call the generated batch already makes between modules) to add or suppress collects, `GCTHRESH=` applies a threshold where the boot entry does, and a synthetic injector adds churn/survivors at chosen size classes |
| per-object placement probe | a runtime-built tuple (one allocation; `id()` is its address), allocated first and dumped after; the pre-state is rebuilt by freeing the probe's own blocks, because the dump itself allocates |
| call-graph pricing (`fgraph.py` / `fprice.py`) | wrap every method of the path under test for exact counts and edges (the wrapper's own bytes are discarded), then price each node alone in a collection-free window |
| wire-identity prototype (`proto.py`) | record every CS edge and transfer on the fake `SPI`/`Pin`, assert a restructured path's trace equals the current one, then price both with the fakes' own allocations removed |
| serving sweep (`sweep.py` / `drive.py` / `boot.py`) | boot the frozen twin at a heap and threshold; a separate CPython process drives N simultaneous requests × R rounds (one socket each, `threading.Barrier(N)`, bodies drained never kept, 1 s settle since a slot outlives its response); failures counted from the twin's own log and grouped by size and last three frames (`classify.py`) |
| peak twin (`boot_peak.py` / `drive_peak.py` / `sweep_peak.py`) | the silicon `--peak` load against a fresh twin per level under a cgroup CPU quota (`QUOTA`), `MAXCONN` patched into the frozen generated module, a rejection counter on `_open_conns.increment`; host resets beyond the device's rejections are true failures |
| device scripts in the twin (`twin_wrap.py` / `validate_bench.py`) | run a device script **unchanged** after `run_generic_integration`'s setup, and a bench test module's own functions against a fake `Board` whose `run_isolated()` is `twin_wrap.py`. **Always do this before silicon**: it found three instrument defects the board would otherwise have |

### M5.4 The removed silicon sweep tool

`tests_hardware/combined_load_sweep.py` + `device_scripts/serving_stability_under_combined_load.py`,
last present at commit `4914a25`, removed once the connection limit was settled. Per level: one fresh
boot through `Board.run_isolated()`, `kick_all_stations()`, hard reset, 45 s settle; the device sets
and prints its threshold, starts `sensortask_dev.main()`, wraps `_open_conns.increment` and after
20 s runs a 150 s window with one probe — `mem_info(1)` maps every 5 s (rounds), the same after a
collect (`--margin`: exact live set, verdict not evidence), a 20 ms `mem_free()` +
`_open_conns.value` low-water sampler (`--peak`), or nothing (`--no-sampler`, the control). Output:
a verdict per level, the device's allocation lines, its `PEAK_*` lines and a host-vs-device refusal
cross-check.

---

## M6. Measuring serving memory

The silicon rules — stable vs refused, peak vs rounds, checking every body, separating verdict from
measurement, pricing the instrument, verifying the image, one fresh boot per data point, holding a
ceiling open — are `tests_hardware/README.md`'s. What this file adds:

### M6.1 The need sieve: the smallest free run a route needs

Shape the heap so that no free run exceeds S, for rising S, and run each data source and each whole
GET route on it; the smallest S at which a probe succeeds, and keeps succeeding at every larger rung,
is its need. **Shape it bottom-up**: fill every free block with one-block chain nodes (one-block
allocations advance the scan hint, so they land in address order) and keep one in every k + 1. A
first version let lowest-fit put blockers into low dust instead of next to their holes, and payloads
merged into runs of up to 32 KB. No `range()` object in the fill loop — it leaves garbage inside the
pattern. Exact from ~6 blocks up; below that the sieve's own residue floors the reading.

### M6.2 An image's heap, before its figures count

For `dev` at MicroPython 1.29.0 the linker heap is **187,712 + (8 − L) × 2,324 B** for
`max_connections = L` (archive §7R.1); `mem_info`'s total is ~2.3 % less (the GC's own tables, scaling
with the heap) and is the percentage base. Read every lwIP macro back out of the built firmware and
check the linker heap against the formula; a mismatch means the image is not the one being described.

### M6.3 State the scope with the result

A serving figure holds only within its scope; write it down every time: which admission check was in
front of Microdot (the application's own `max_connections`, or none), which ports and routes were in
the load, rounds or peak, what internal load coincided (NTP, WLAN reconnect, sensor reads, FRAM
writes — scheduled or forced), and whether a device script or production `main.py` ran the task
graph (the script's own code costs heap production does not pay).

---

## M7. Remedy directions already ruled out

Measured, not argued; don't re-spend time on them without a new mechanism. Evidence: archive §6,
§6A, §7.

- **Cutting churn volume alone** — the outcome does not track volume; removing the *large*,
  collection-forcing allocations made it worse, and the required cut was out of reach.
- **Hoisting or pre-allocating permanent objects** — protects the hoisted ones at low churn and
  consumes the holes the rest need at the real dose.
- **A bigger heap** — the hole population is import-and-construction residue, heap-independent.
- **Removing the sleeps / a blocking chip-select settle alone** — neutral to worse for layout. The
  settle *inside* the CS window must block (a bus hazard otherwise), but **the CS path must keep a
  scheduling point per session**, after deassert and lock release: without it a 74-session logger
  setup starved the event loop and broke a real twin test deterministically (archive §8.1).
- **`ThreadSafeFlag`** in place of the awaited settle — the wrong primitive.
- **Any single write-path component, the await chain, the per-call buffers** — none controls it.
- **Combinations** — nothing composes; the outcome is a coincidence count (§M1).
- **`gc.collect()` / `gc.threshold()` as the fix** — forbidden by `SPECIFICATION.md` I.4(e)-(g);
  the boot-confined collects of I.4(f.1) are placement discipline at the two lists where permanent
  objects are born, never run-phase margin.

What did ship: the FRAM path restructured with the wire protocol byte-identical and the lock held per
block operation (`SPECIFICATION.md` C.8), and the boot-confined collects
(I.4(f.1)); for serving, bounded assembly and chunked static reads (I.3), `max_connections = 6`
(H.7) and the lwIP ensemble (B.14.2).

---

## M8. Research gaps, closed as not pursued

**Closed by the owner, 2026-09-24** — re-open only if a new layout symptom appears. The four: what
in the old churn did the stranding at a given dose; whether parallelism matters after boot, once the task graph is live (the boot batch
has none); the per-object picture on the board's 16 B blocks, where the one-block immunity boundary
falls at a different byte size; and a same-binary A/B of the committed chip-select settle. The
remedy shipped and holds on silicon, so none gated anything.
