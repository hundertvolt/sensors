# U35 closing ledger (lead, 2026-10-28 05:30)
Owner, 2026-10-28: "I don't actually want to cut back or trade anything, I just want to make sure that you set up the
process such that it can finished and is not designed self-sustaining / will never end".

The work left in U35 is this list, finite. When it is empty, U35 closes (W10) and stops for the hardware round.

## Items (state; done when)
1. LD+CM3, load records and the assembly matrix: running; its brief's items 1-5 committed green, merged, checked.
2. CRr2c, flash-tier log check through the twin: running; the same.
3. IN2, the reverse map and the lwip_host review rows: running; the same.
4. CRr2d, the bench tier's provokes_log sets through the dev twin: queued; the same.
5. CMr1n, both drift arms separate in every layout measured, the cycling arm committed if it does: queued; the same.
6. RF1, redflags' by-name credit raises flags but no longer credits; the 9 rows and the timer-deinit row read: queued
   after IN2; the same.
7. CM4, the interaction matrix and the recombination row: queued after LD+CM3; the same.
8. The NeoPixel overlay's lost cancel: the owner's answer, then the lead applies the chosen form; merged, checked.
9. The serial close: mc_cov, B2r on a quiet host, twin CI on int and the twin_record re-record, D3r, REC2, W10 (the
   close commit, push, CI green, the owner report), then STOP.

## How the list may change (binding from 2026-10-28 05:30)
- **Admission.** A new item joins only if it is one of these:
  - (a) a defect in the firmware: src/, the generated modules, or the build that makes them;
  - (b) a defect that makes one of this list's own deliverables wrong (a check that cannot fail or silently passes, a
    record stating something false or unverified, a red test) and that the lane which found it cannot close itself.
  Each addition is named to the owner in the next report, with its reason.
- **Everything else is routed, not dropped.** Improvements, extensions, stronger forms of an already-correct check,
  coverage beyond an item's done-criteria and observations go to the findings list below with their evidence. The owner
  report and BACKLOG carry that list to the next unit's own scope.
- **Closure per item.** A lane fixes the defects of its own work before it hands back, its own reds and a check of its
  own that does not separate included. If a done-criterion turns out unreachable, it hands back the measured limit
  once. The lead then decides in that review: the limit is accepted and recorded, or it becomes one owner question.
  An item gets at most one follow-up lane, and a follow-up spawns none on the same item. CMr1n is the drift item's
  follow-up.
- **No self-made noise.** A timing-bound run starts only while at most 4 heavy processes run (heavy.sh). A red seen
  under contention is re-run once at low load before it is investigated, and then it is root-caused as always.
- **Visible convergence.** Every report to the owner gives this list's count: open, closed, and added with a reason.

## Findings routed to the next unit (with evidence)
(none yet)
