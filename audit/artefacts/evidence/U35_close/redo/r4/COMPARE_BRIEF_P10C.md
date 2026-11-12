# Read-only comparison: proof run 3's SGP40 module against the real one (lead, 2026-11-05)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Read
`S/u35r/r1/common_r1.md`'s rules (binding; labels `cmp3_`).

## What this is
A build agent rebuilt the SGP40 module in `S/p10/sgp40/tree` (its own git; baseline `b163296`, head `48f3573`)
from the datasheet, the owner record `S/p10/sgp40/BRIEF.md` and the repository's procedure (SPECIFICATION.md Part K,
K.0, `.claude/skills/integrate-module/SKILL.md`), without seeing the real module. Its report: `S/p10/sgp40/HANDBACK.md`
and its section 3, the procedure log (20 entries). The key, `S/p10_lead/sgp40/KEY.md`, lists what the real module is; the real module
itself is in `S/p10_lead/sgp40/full/` (the unstripped export of `84a76ae8`; read-only for you).
This is the third run. Runs 1 and 2 led to a Part K and skill fix unit (`S/u35r/r4/HANDBACK_PK.md`: K1, K3-K6, N1-N3),
which this tree carries. Run 3's value is what it says about those fixes.

## What to answer
1. **Per check:** matched, differs (how; and which is better where that is plain from the datasheet or the brief),
   or missing, with file:line on both sides. Checks: (1) driver shape (Part C layers); (2) config schema and live push;
   (3) readings and VOCState; (4) `@web`, `@web-group`, `@wiring`, `@value-wiring`, `@requires` tags; (5) use of
   `src/voc_algorithm.py` as is, state pack/unpack included; (6) compensation (skip if unavailable, clamp, round,
   non-finite fails); (7) waits and `@tunable` rows; (8) FRAM backup, restore with the NTP wait, the reset retry;
   (9) error catalog rows; (10) build-chain rows; (11) twin chip model; (12) tests per tier, bus-hazard coverage
   included; (13) docs (Part M section, Part N rows); (14) wiring on all six devices; (15) image size: the run's dev
   `imageFreeBytes` against the stripped baseline 79,068 and the real 60,172.
2. **Per procedure-log entry:** its class: (K) Part K or the skill is missing, unclear or wrong, with the one sentence
   that fixes it and where it goes; (S) a strip artefact; (B) the run brief caused it; (C) a finding about the
   codebase itself (check it in `full/`: real or not). A divergence in a row KEY lists under "Taken by the strip" or
   "Strip-adjusted" is (S). Keep (K) sentences to the smallest set that covers every (K) entry.
3. **The earlier fixes:** for each (K) entry, say whether one of the fix unit's sentences was meant to cover it, and
   if so why it did not (not reached, unclear, too narrow). Then the smallest set of further sentences for the rest.
4. **The baseline reds:** the 9 `tests_scripts` tests KEY lists as red at the start: each one's state at the run's
   end, and whether the run's change matches what the real module does for it.
5. **The strip:** traces of the stripped module the run reports, or this comparison finds, that steered its
   choices, each with its line in the stripped tree.

## Limits
Read-only: write only `S/p10_lead/sgp40/COMPARE.md`. No runs but greps and `git` reads; never edit either tree.
Never read `arduino/`; never open `/root/.claude/`. Budget about 0.7 % of the week.

## Hand-back
`S/p10_lead/sgp40/COMPARE.md`, at most 70 lines, and return its path. Last line: "nothing of mine is running".
