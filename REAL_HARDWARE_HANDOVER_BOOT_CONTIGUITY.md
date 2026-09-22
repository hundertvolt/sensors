# Real-hardware handover — the boot placement reset, measured as placement (2026-09-21)

The board-side counterpart of the host guard built this session:
`tests_scripts/test_digital_twin_boot_contiguity.py` plus `tests/_boot_contiguity_probe.py`
(`HEAP_FRAGMENTATION_MEASUREMENTS.md` §7L; the plan section it was built from is closed and deleted). The host tier now
measures `gc.collect()`'s boot-confined placement reset **directly** — where each list's survivors
land — instead of inferring it from a contiguity fraction. The board has never taken that reading.

**This file is written to be executed top to bottom by a session that has the owner's real-hardware
go-ahead in its own conversation** (CLAUDE.md's gate — a go-ahead given to another session does not
carry over). It asks for no flash write and no reflash; see "Safety" for why.

---

## 1. What is already settled, host-side

Measured on all six real devices, three repeats each, at `-X heapsize=16M` and `gc.threshold(-1)`.
Every metric is a byte offset of the blocks a boot list newly allocated, relative to the top of what
was already allocated when that list began ("the seam"): the **reach** is the highest such block,
the **depth** is how far *below* the seam the median one sits. Deeper is better — it means the
survivors went into low holes instead of stacking above the churn.

| position | metric | collects live | collects suppressed | separation |
|---|---|---|---|---|
| setup batch | median **depth below** seam, worst of 6 | **452,832** | 218,528 | 2.1x |
| both lists | reach above seam | **16,352** (every device) | 141,632 | 8.7x |
| both lists | median depth below seam, worst of 6 | **356,576** | 108,352 | 3.3x |
| both lists | new blocks > 128 KiB above seam | **0** on every device | 98–726 | — |

**These are the settrace-free interpreter's figures** (the split of 2026-09-21, MEASUREMENTS §7L.7).
On the old settrace build the *batch's own reach* discriminated 7.5x; without the 4-5x allocation
inflation the batch barely moves the frontier at all — 8,160 B in **both** arms on four of six
devices — so that metric is gone and the depth/cumulative ones above replaced it. A board run
comparing against the older numbers would be comparing against an artefact of the test binary.

Three facts that matter for the board run:

- **The metrics are heap-size independent**, re-verified on the settrace-free binary: wozi measures
  a batch median of **−481,376 B at both `-X heapsize=8M` and `16M`**, a cumulative reach of
  **16,352 B** at both, and 0 blocks above the band at both — byte-identical, both arms. By contrast
  `largest_free_run` as a fraction of free moves with the heap size for the same code. That is why
  no fill calibration is needed and why the host bounds are absolute offsets from the seam.
- **Retention is arm-independent**, to within 0.05% (`used_bytes` after the batch: 643,360 live
  against 643,584 suppressed on wozi). §7A.1's "placement, not consumption" finding, reproduced.
- **The settle position does not discriminate and must not be asserted on.** Four seconds after the
  starter loop, dev's *suppressed* arm reported a **larger** `largest_free_run` than its live arm
  (10.19–10.47 MB / 64–66% against 9.37–9.47 MB / 59–60%). The run-phase decay §7F.9 measured swamps
  the boot gain and can invert it. Read at the loop's **end**.

## 2. What the board cannot produce yet, and the one change that fixes it

`tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py` dumps maps at
`after_build_system`, `after_starter_loop_end` and `after_starter_list`. **It has no seam map** —
`baseline` is a `_report_checked()` probe reading, not a `mem_info(1)` dump — so
`tests_hardware/heap_map.py`'s `delta()` has no `before` for the setup batch, and the board cannot
compute any of §1's figures. Every board reading to date is an absolute contiguity number at one
position, which is a different (and weaker) statement.

**The fix, and the finding that makes it cheap: both arms run from one image, with no reflash.** The
emitted collects resolve `gc` as a module global in the generated `sensortask_dev`, and the starter
loop's resolve it as a module global in `system_service` — so a device script can rebind both to a
stand-in and suppress every collect at runtime. This is exactly what §7F.9 did host-side and what
`tests/_boot_contiguity_probe.py` does now; it works identically on the board. **No BEFORE image is
needed for the control arm**, which removes the reflash that §7D's arm comparison required.

Port `_ProbeGc` from `tests/_boot_contiguity_probe.py` (23 lines, no host-only construct in it) into
the device script, take the seam map from its first `collect()` call, and add an `--arm` argument.
Keep `_report_checked()`'s existing probe readings untouched so the run stays comparable with §7H.4.

## 3. The runs

Prerequisites: `tests_hardware/README.md`'s bench setup, the dev board reachable over
`mpremote`, and the owner's go-ahead in this session. Nothing here needs
`--allow-flash-cycle`, `--allow-persistence-writes` or any other wear gate.

**B7 — the seam map and the board's own reach, live arm.** Run the extended
`heap_layout_after_full_boot_sequence.py` on the `dev` board, capture the full output, and compute
`delta(seam, after_batch)` and `delta(seam, after_starter_loop_end)` host-side with
`tests_hardware/heap_map.py`. Record reach, median, and the count above the 512 KiB band **in board
units** (16 B blocks on rp2, against the twin's 32 B — the parser derives this, do not convert by
hand), and the count above the 128 KiB band.

**B8 — the same run with `--arm suppressed`.** One invocation, same image, immediately after B7 so
the heap is aged the same way. This is the board's first controlled A/B of the collects without a
reflash.

**B9 — the ratio, which is the transferable claim.** Compare B7 and B8. The host says **2.1x** on
the batch's median depth and **8.7x** on the whole sequence's reach. A board ratio in the same
direction and order of magnitude confirms the mechanism on silicon; a board ratio near 1.0 would
mean the mechanism does not hold at the board's own fill, which is a finding either way and would
need recording before anything else. **Expect the batch's own reach to say nothing** — it is
identical in both arms on four of six devices host-side, which is why B7 records depth too.

**B10 — hold the twin's qualitative claim up to the board.** The host's live arm puts the *median*
new block **far below** the seam top on every device — 452,832 B down in the worst case, against
218,528 B with the collects suppressed. Check whether the board's median is likewise deeper live
than suppressed. This is the strongest single statement the metric makes and the least unit-dependent.

## 4. What transfers to the board and what does not

- **Does not transfer: any absolute byte bound.** §1's numbers are twin units — 32 B blocks and
  x86-64 words against the board's 16 B blocks and 32-bit words. (The 4-5x `MICROPY_PY_SYS_SETTRACE`
  inflation is **no longer** part of it: since 2026-09-21 the plain suite runs on a flag-free binary,
  which is exactly why the bounds had to be re-derived.) The host test says so in its own constants'
  comment, and the board's tripwire stays the hardware test. **Do not copy 300 KiB, 256 KiB or
  64 KiB onto the board.**
- **Transfers: the ratio between arms, the sign of the median, and the zero count above the band.**
  These are unit-free or nearly so.
- **Untested either side: whether the board's reach survives the run phase.** §7F.9 says most of the
  gain is gone within ~2 s and this session reproduced the inversion in §1. Nothing here changes
  that, and B7–B10 deliberately do not read the settled position for a verdict.

## 5. Safety

- **Read `GET /status`'s `errcount` — the FRAM-backed subset — before any
  `PUT /status {"ResetErrors": true}`** (CLAUDE.md). These scripts print no error log of their own.
- **An isolated-driver device script overwrites production's first FRAM chunks** — the allocator is
  deterministic, so its first chunk is production's first chunk. Read the error logs first, and
  treat any FRAM-backed log read after this run as contaminated (`tests_hardware/README.md`).
- **No flash write.** `heap_layout_after_full_boot_sequence.py` passes `cfg_path=""` and every
  `ConfigManager` it constructs only writes on an accepted REST PUT, which this run never issues.
  If a `config_*.cfg` appears in the board's root after it, that is a finding to record, not
  expected behaviour.
- **Never run two suites that both bind real ports at once** (CLAUDE.md). The script serves nothing,
  but the flash/bench tiers do.
- **Do not fit any threshold to a board reading** (§7G, owner). B7–B10 produce figures and one
  ratio; they assert no new floor.

## 6. Done when

- B7 and B8 have run on `dev` from one image, with their full captured output recorded in
  `HEAP_FRAGMENTATION_MEASUREMENTS.md` as §7L's board columns.
- B9's ratio and B10's median sign are stated, with the raw numbers next to them.
- Any divergence from §1's direction is written down as a finding before any threshold anywhere is
  touched.
- `REAL_HARDWARE_TEST_QUEUE.md`'s §1E rows are updated, and this file is deleted once all four are
  closed — the same condition every other handover in this repo carries.
