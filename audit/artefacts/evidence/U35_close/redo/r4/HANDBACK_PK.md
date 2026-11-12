PK hand-back, written by the agent (Thu Nov  5 20:19 UTC 2026)
Commit `aff1af5c` on `audit/pk` (wt-pk, parent `4e05f80e`), not pushed; docs only. Part K + skill net +19 (cap 40),
F.1 +4; SPEC lines are at `aff1af5c`; every name the sentences cite was found in this tree.
1. K1: K.3 item 1 SPEC:10193-10195 (+3/-1; `twin_wiring.py` `fixed_address()` :129-137); its "Adding a new chip
  fake" clause goes at K.5's end SPEC:10258 (+1/-1), the step it names.
- K4: K.2 SPEC:10154-10156 (+3/-2; N.1, CLAUDE.md's bird's-eye scan).
- K5: K.4 SPEC:10231-10234 (+4/-1): `codes=` cites H.5.1; unit/decimals tagged (agent, 2026-11-05), citing ISL29125's
  `R`/`CalLight` (every src `@web` tag checked: no dimensionless value has a unit, no bool/code field decimals).
- N1 (replaces K2): K.6 head SPEC:10262-10268 (+7/-1); each listed table exists (`_KNOWN_TICKS_USERS`
  tests/test_ticks_rollover.py:57, `_KNOWN_PERSISTING_HELPERS`, `_EXPECTED_LARGEST`, launch.py's op tables, the five
  `_HEALTH_FIELD` maps, pyproject:235-243, I.2, L.3, E.6.6, Part N).
- N2: K.6 twin paragraph SPEC:10288-10291 (+4/-1) and K.11 SPEC:10429-10430 (+2/-1).
- K3: K.9 SPEC:10361-10362 (+2/-1); also K.11 SPEC:10445 "C.7.1/C.8" -> "C.7.1/C.9.1" (+1/-1), the same
  dangling note mirrored from K.9.
- K6: K.10 SPEC:10396-10397 (+2), pointing at F.1. N3: SKILL.md:16 (+1/-1).
2. F.1 SPEC:6284-6289 (+6/-2), after the host-folded float sentence, checked in tc-int v1.29.0:
   mpy-cross/mpconfigport.h:57, 98-99; py/parse.c:662, 876-899 (880-883: only `id.id` folds, so `float("inf")`
   does not); tools/mpy-tool.py:796 (`%.16g` prints `inf`/`nan`).
3. CLAUDE.md: not written, already there. CLAUDE.md:534-536 counts a line as its stripped length over 120, rounded
   up, tagged (owner, 2026-10-21), as test_comment_block_cap.py:22-25, 82 does; in the tree since `656fc82f`, and in
   the comparison's own tree `59d91860` (CLAUDE.md:572), so that finding was mistaken. CLAUDE.md is untouched.
4. C.9 one Timer per starter: not written. Part F gives no basis (SPEC:6247-6259: the 16-alarm pool and the GC
   disarm, nothing per starter), and no product code depends on it: `start_timers()` (src/asy_system_service.py:
   725-744) just calls each starter. Every src starter arms one Timer (SCD30 :529-542 and ISL29125 :935-951 arm
   their IRQ inside it); the only dependant is a test count, `feeds["timers"] >= armed` (tests/
   _sensortask_scenarios.py:1524-1530, 2013). (c) for the owner: C.9's rule, or that count accepts IRQ-only starters.
Checks: rebuild rc=0; lint_direct rc=0; the 20 tests_scripts files that read SPEC/CLAUDE.md/the skill (citations,
comment cap, decision vocabulary, memory catalog, level containment, toml contract, tunables, ...) 911 passed.
tests_scripts tier whole at `aff1af5c` (heavy slot taken 20:10, released 20:19): 6887 passed, 9 skipped, 0 failed.
nothing of mine is running
