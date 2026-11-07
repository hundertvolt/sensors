# R4 proof run 3 preparation: the SGP40 stripped tree, its brief and its key (lead, 2026-11-05)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `p10s_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r4/BRIEF_P10.md`
(the first two runs' preparation brief: what a stripped tree, a brief and a key are; everything there holds unless
this file says otherwise), and section 4 of `S/p10_lead/bmp3xx/COMPARE.md` (what run 2's strip left behind).

The owner chose a third run at 21:16 UTC. It proves the procedure as it now stands, after the fixes the first two
runs led to, so its value depends on the tree being clean: the build agent must find no trace of the module, and the
tree must be green before the build starts.

## Source and tools
- **Source:** `git -C S/wt-u35int archive 84a76ae8` (the integration head: the fixed Part K, skill and F.1). Never
  write to `S/wt-u35int` or any other worktree or branch.
- **Tools:** the earlier runs' `S/p10_lead/strip.py`, `leak.py`, `keygen.py` and `subs_*.py`. Copy what you need into
  `S/p10_lead/sgp40/` and extend the copy (an `sgp40` entry, source and revision as above); leave the originals as
  they are.

## What you make
1. **The tree** `S/p10/sgp40/tree`: a new git repository, one commit, no history, with every trace of the SGP40
   module removed (BRIEF_P10.md's list: driver, tests at every tier, twin chip model, buildspec, definitions and
   registry rows, every `devices/*.toml` entry and the wiring that names it, generated hints, website rows, Part M.3,
   Part N's rows, other SPEC passages on its specifics, its legacy driver, its lines in the docs).
   - **Keep `src/voc_algorithm.py`, its tests and reference vectors, and its THIRD_PARTY_LICENSES entry**: the owner
     record gives the algorithm as an existing library to use. Remove only sentences in them that describe the driver.
   - Other modules that consume the SGP40's values (the notification source, any `@value-wiring` consumer) keep their
     own code; only the SGP40 side of the wiring goes.
2. **The brief** `S/p10/sgp40/BRIEF.md` (one page, as BRIEF_P10.md item 2): the features, API and website as the
   owner decided them, from the real module's behaviour. It includes the decisions the real module records as the
   owner's (waits the owner set, the published algorithm state and its meaning, what is and is not mitigated), which
   devices carry one and what feeds its compensation, and names `src/voc_algorithm.py` as the library to use. No
   code, register maps, command codes or file names of the real driver.
3. **The key** `S/p10_lead/sgp40/KEY.md` (as BRIEF_P10.md item 3), plus two lists:
   - **Taken by the strip:** every shared row the module was the only user of (an error-catalog code, an allow-list or
     confusables entry, a ruff per-file ignore, a memory-catalog row, a FRAM chunk, a lock-order row), so a later
     comparison classes a divergence there as the strip's, not the procedure's.
   - **Strip-adjusted:** every count, total or byte figure you changed because it included the module, old and new.

## A clean strip (the difference from runs 1 and 2)
- **Residue read.** After the scripted strip, read SPECIFICATION.md 15 lines either side of every hunk the strip
  made, and every passage that states a count, total, per-device table or byte budget covering all drivers (run 2's
  residue was in I.2, G.2, I.6, C.9.1 and E.5.1). Fix orphans: a sentence whose subject is gone, a count that still
  includes the module, a table row or trigger list that does. A byte figure you cannot recompute is removed with its
  sentence's module-specific part and listed as strip-adjusted. Do the same for code comments the leak check finds.
- **A green baseline.** From the tree, holding the heavy slot as common_r1 says: `S/p10/gate_proof.sh dev
  S/p10_lead/sgp40/g0`, then `uv run pytest tests_scripts -q` whole (run 2 found two tests red here at its start).
  A red test is the strip's to fix, not the test's to weaken: either the strip left something inconsistent (fix it),
  or the test pins the module itself (it goes with the module, and is listed in the key). Target zero red; anything
  left red is listed with its reason.
- **Leak check:** BRIEF_P10.md's `git grep`, with the chip's names, its driver class, config keys, reading keys,
  algorithm-state names, wait constant names and command codes. "Sensirion" and CRC terms are shared with the SCD30:
  justify such hits rather than remove them.

## Rules
Write only under `S/p10/sgp40/` and `S/p10_lead/sgp40/` (the key and your tools there: the build agent is never shown
`S/p10_lead/`). No hardware. At most twelve runs, one at a time. Never open `/root/.claude/`; never read `arduino/`.
`rm` with literal paths only, each as its own call; delete scratch you no longer need. Budget about 0.8 % of the week;
hand back by 23:45 UTC.

## Report: `S/u35r/r4/HANDBACK_P10C.md` (at most 25 lines), return its path
The tree's commit; files removed and changed (counts per tier); the residue fixes; the baseline gate steps and their
results, and dev's `imageFreeBytes`; the leak check's remaining hits with their justification; the brief's word count;
anything that could not be stripped cleanly. Last line: "nothing of mine is running".
