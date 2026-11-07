# R4 OR10.b preparation: two stripped trees and two briefs (lead, 2026-11-05)

## Read first
Read these first:
- `S/u35r/r1/common_r1.md` (binding; your labels start with `p10_`).
- `S/u35r/r4/ROWS.md` section 4 (OR10 and OR10.b's proof) and rows 19 and 20.
- The owner rows OR10.a and OR10.b in `PROJECT_AUDIT_PLAN.md`.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

The owner's OR10.b: "the fresh agent really builds the module in an isolated throwaway worktree from only the
datasheet and the brief, through every test tier and the build; its driver, config, `@web` tags, twin model and tests
are compared with the real ones; every divergence caused by the procedure (not by legitimate design freedom) becomes a
fix in Part K or the skill ... nothing from the throwaway worktree is ever merged." The owner chose two runs on
2026-11-05: one on ISL29125, one on BMP3xx.

## What you make, for each baseline (ISL29125, BMP3xx)
1. **A stripped tree.**
   - **Location:** `S/p10/<chip>/tree`.
   - **Source:** the files of `S/wt-r4a` at its head `6e006a95`, which holds the final Part K and the skill. Make it
     a NEW git repository with one commit and no history (`git init`, one commit), so no earlier version can leak.
   - **What to remove: every trace of that module.**
     - the driver;
     - its tests at every tier (unit, twin, tests_hardware, tests_scripts);
     - its twin chip model;
     - its buildspec, definitions and registry rows;
     - its `devices/*.toml` entries;
     - generated hints;
     - website rows;
     - its SPEC Part M section and other SPEC passages that describe that driver's specifics;
     - its legacy driver under `legacy/`;
     - its lines in the docs.
   - **What to keep:**
     - shared code;
     - every other module;
     - Part K;
     - the skill;
     - `datasheets/` without that chip's folder (the brief gives the datasheet path instead).
   - **What it must still do:** the tree must build and pass the gate's fast parts without the module. Run lint, the
     three mypy passes, `scripts/test.sh`'s file list for one wiring device, and `scripts/build_firmware.py` for that
     device. Choose the device as a device whose TOML wires the chip today, with the chip's entry removed.
   - **A leak check:** a case-insensitive `git grep` for the chip's names, its driver class, its config keys and its
     register names. Every remaining hit is listed and justified (for example, a datasheet-neutral word).
2. **The brief.**
   - **Location:** `S/p10/<chip>/BRIEF.md`.
   - **Length:** at most one page.
   - **What it is:** the owner-discussion stage's output (K.0's record), written as the owner would have decided it:
     the features, the API (the config values, the readings and their units), and the website (what it shows and lets
     a user set).
   - **Where it comes from:** the real module's behaviour.
   - **What it must not contain:** code, register maps or file names of the real driver. It names the datasheet
     path `/home/user/datasheets/<folder>/` and the wiring device.
3. **The comparison key.**
   - **Location:** `S/p10/<chip>/KEY.md`.
   - **Contents:** the list of the real module's files and the facts a later comparison will check: the config
     schema, the `@web` tags, the twin model's behaviours, the test names per tier, and the image size delta.
   - **Visibility:** the build agent will never be shown this file.

## Rules
- Write only under `S/p10/`.
- Never commit to, or change, any existing worktree or branch.
- No hardware.
- At most ten runs, one at a time.
- Never open `/root/.claude/`.
- Never read `arduino/`.
- Delete every scratch file you no longer need. Use `rm` with literal paths only, each as its own call.
- Budget: about 0.8 % of the week.

## Report
At most 25 lines:
- per chip, the tree's commit, the files removed, the gate parts run and their results, and the leak check's
  remaining hits;
- the brief's word count;
- anything that could not be stripped cleanly.

The last line is "nothing of mine is running".
