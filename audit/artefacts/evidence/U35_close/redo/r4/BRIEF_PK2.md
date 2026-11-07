# Fix unit 2: the gaps proof run 3 still found in the new-module procedure (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `pk2_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/p10_lead/sgp40/COMPARE.md`
(proof run 3's comparison against the real module; section 3 is your work list) and, where a sentence's place is
unclear, the run's procedure log, section 3 of `S/p10/sgp40/HANDBACK.md`. `S/u35r/r4/HANDBACK_PK.md` says where the
first fix unit put its sentences; do not move or reword those.

## Your work (worktree `S/wt-pk2`, branch `audit/pk2`, at `84a76ae8`; commit locally, never push)
1. **Part K, four sentences** (COMPARE.md section 3, each at the item it names): a parameter a `@wiring` or
   `@value-wiring` tag fills is an `[instance.wiring]` field, never a buildspec row (K.3 item 1); what the
   fault-planting copy must hold (K.10); a host test about the devices carrying the driver takes them from
   `devices_with(<driver>)` (K.6); a datasheet's maximum SCL frequency is a bus prerequisite, `@requires
   bus.frequency<=<Hz>` (K.4). Fit each to the text around it; check every name it cites exists in this tree.
2. **K.0, one sentence:** a record point that departs from a standing owner rule (for example C.4.2's staleness rule:
   a failed read publishes nothing, the last good sample stands) is put to the owner before code, never followed
   silently. Run 3's record said a failed read nulls the values, and the build followed it.
3. **`tests/test_digital_twin_hot_replug.py:199`:** `_supervised()` finds a reader's value sources by `getattr` on the
   names `_temperature`/`_humidity`, a silent no-op for any other name. Make it find every value reference the
   reader holds whatever it is called (the type `@value-wiring` hands a reader; check it in `src/` and `buildgen/`),
   so the naming contract goes away rather than being documented. Same behaviour for today's readers.

## Not yours
Everything else in COMPARE.md (strip artefacts, the run's own design choices, the "record vs real" points, which are
settled), and any other file under `src/`, `tests/`, `digital_twin/`, `buildgen/` or `tests_hardware/`.

## Rules for the text
- The smallest form: one sentence per gap; no new section, list or table. Net growth of Part K plus the skill at most
  10 lines.
- Text outside `audit/` cites no audit IDs, run numbers or unit names: state the rule itself.
- A sentence that records a choice carries "(agent, 2026-11-06)"; a fact gets its source citation instead.
- SPECIFICATION.md keeps its wrap width; comment-block and line rules as CLAUDE.md states them.

## Checks
`S/u35/lead/lint_direct.sh`; the three mypy passes; `tests/test_digital_twin_hot_replug.py` at both GC stages (the
single-file command in `S/p10/sgp40/RUN_BRIEF.md`'s Environment section) for each device that runs it; every
tests_scripts file that reads SPECIFICATION.md or the skill (grep for them). Then, once `S/u35/lead/heavy.lock` is
absent, take it as common_r1 says, run the tests_scripts tier whole, and release it.

## Limits
Write only SPECIFICATION.md, `.claude/skills/integrate-module/SKILL.md` and `tests/test_digital_twin_hot_replug.py`.
One commit. Budget about 0.5 % of the week; hand back by 05:30 UTC.

## Hand-back
`S/u35r/r4/HANDBACK_PK2.md`, at most 20 lines, and return its path: per item where it went (file:line), lines in and
out, the checks. Last line: "nothing of mine is running".
