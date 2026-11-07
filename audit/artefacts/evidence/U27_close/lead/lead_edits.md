# U27 close: the lead's edits outside audit/ (draft)

## SPECIFICATION.md F.7 row 17 (`SPECIFICATION.md:6554` at `7f34f35`)

The row's "Workaround site" cell (the table's fifth column: `| # | Difference | Unix port | rp2 | Workaround site | rp2 proven
by | Removal trigger |`) names only the unit fake; the digital twin gained a test-only knob at U27 (lane S, OF-157).

Old line (exactly, one occurrence at `7f34f35`):

```
| 17 | soft-callback queue | depth 4 (`py/mpconfig.h:1232-1234`) | depth 8 (`ports/rp2/mpconfigport.h:131`); every soft Timer and Pin IRQ callback is queued there and dropped when it is full (`shared/runtime/mpirq.c:103-106`, `py/scheduler.c:162-180`; F.1) | the unit fake's `Timer.drop()` stands in for a drop | L3/L4 | none |
```

New line:

```
| 17 | soft-callback queue | depth 4 (`py/mpconfig.h:1232-1234`) | depth 8 (`ports/rp2/mpconfigport.h:131`); every soft Timer and Pin IRQ callback is queued there and dropped when it is full (`shared/runtime/mpirq.c:103-106`, `py/scheduler.c:162-180`; F.1) | the unit fake's `Timer.drop()` and the digital twin's test-only `Timer.drop_next_soft_callbacks` (`digital_twin/machine.py`, off by default, cleared by `reset_test_state()`) stand in for a drop | L3/L4 | none |
```

Checked at `7f34f35`:
- The knob's name and file: `class Timer` in `digital_twin/machine.py` holds `drop_next_soft_callbacks = 0` (`:1363`), listed in
  `TEST_API` (`:1360`), consumed for soft callbacks only (`:1413-1415`), cleared by `reset_test_state()` (`:1748`); the unit
  fake's `Timer.drop()` is `tests/machine.py:1288`.
- The citation check (`tests_scripts/test_citations.py`): the one new path token, `digital_twin/machine.py`, exists; the
  upstream paths are unchanged and skipped by root (`py`, `ports`, `shared`); the new text adds no "Part"/"SPEC" section,
  BACKLOG item, plan label or audit ID.
- The decision-vocabulary check (`tests_scripts/test_decision_vocabulary.py:22-24`): no word of its vocabulary in the new text.
- The comment-cap check: `.md` is review-enforced, not counted (`tests_scripts/test_comment_block_cap.py:57`, "documentation:
  prose throughout, no header block"); the table row is one line, as every F.7 row is.
- `digital_twin/README.md:233` already states the twin's side (fidelity row); the two now agree.
