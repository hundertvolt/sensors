# F4c: the listener-close guard proven on silicon, prepared (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base: F4a's merged head (the lead names it at launch). Worktree and branch
named at launch; logs in `S/u35/laneR/f4c/`. Facts: `S/u35/lane_plan.md` LEAD NOTES 154-155 and 157, F4a's hand-back.

## The owner's words (2026-10-26, verbatim)
On the listener-close defect: "Let's handle them like the similar findings: fix in the patched version and monitor
upstream for real fixes, as soon as upstream is fixed drop the patch. Double check your proposed solution is complete
and works without affecting other places." Then: "And for sure test and verify it in both twin and real hardware"
(said of the next topic; the lead applies the same bar here, LEAD NOTES 157).

## What to prepare (never run on hardware: no hardware in this session)
The twin cannot carry this (it runs on the Unix port's own sockets, not modlwip); F4a's host lwIP test is the emulated
tier. On silicon, a flash-tier device script and its host test, proving on the patched image that closing a listener
leaves the connection-pcb pool untouched:
- Addresses from the image under test (arm-none-eabi-nm on its ELF: `memp_memory_TCP_PCB_LISTEN_base`,
  `memp_memory_TCP_PCB_base`, the pool's free-list head), passed to the script; never hard-coded.
- The script confirms the target slots are free (walks the free list with mem32), writes sentinels into a free slot at
  the stray stores' offsets (element 0 at 96/108 for a listener in listen element 7; recompute for element 6), opens and
  closes a listener, then the MemoryError case (bind, `micropython.heap_lock()`, `listen(4)` raises, unlock, close),
  and reads the sentinels back. Never writes a slot in use or the free-list link (offset 0).
- A bite of the checker: the same script plants the stray store itself at the computed address and shows the check
  reports it.
- Least wear: no flash write, no FRAM use (an isolated script's own FRAM manager overwrites production's logs,
  tests_hardware/README.md), no extra flash cycle (it runs on the image the round already flashes).
Run it `--collect-only` and through whatever twin or fake backend the flash-tier harness offers for its host side;
record it in tests_hardware/README.md where the flash tier's scripts are listed. Hand back the steps, the addresses'
derivation and its cross-check against U21's map (`audit/artefacts/evidence/U21_close/lane_s/probe/rp2_listen/`).
Checks, commit, hand-back and "Not yours" as in F4b's brief (`S/u35r/briefs/f4b_loop_end.md`); subject `U35 lane F4c:`.
