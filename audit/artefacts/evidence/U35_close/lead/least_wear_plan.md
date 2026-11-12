# Least wear in the production code: enforcement plan (lead, 2026-10-22; nothing coded yet)

The rule (owner, 2026-10-22: "The least wear rule is even more important for the production code than for the tests,
as it will run potentially for years. This is something to be added to our pillars, a completely central important
rule."), documented in CLAUDE.md (`6dabd9b`), the audit's pillar table, CHECKLIST 24 and common_u35.md.

## E1. The config write back to the single write (owner, 2026-10-22: "your suggested next steps are fine (go back to the single write)")
- src/asy_config_manager.py: both write sites back to the pre-U35 `with open(self._config_file, "w")` write. Out:
  the slices, `_write_text()`, `_finish_write()`, `_TMP_SUFFIX`, the sibling cleanup in `delete_file()`, the
  `config.flush_slice_bytes` constant and tag.
- tests/test_asy_config_manager.py: the write tests back to the single write's shape; tests/_littlefs_fake.py kept
  only for what still uses it (the commit-at-close model), its rename and sibling parts out.
- Docs: SPECIFICATION.md A.4, C.7.3, F.3 `stall.flash_program`, J.6 and Part N (`config.flush_slice_bytes` out,
  `uart.flash_hold_max_ms`'s basis as before) back to the single write. The stall finding closes as an accepted
  degradation with its consequences. The finish-path item routed to U36 is withdrawn.
- Checks: the file's tests at both GC stages, mpy-cross, the readers, the twin record re-recorded after.

## E2. A structural guard: every production write site pinned
- New tests_scripts check: an AST scan of `src/`, buildgen's templates and the generated modules for every call that
  writes a limited-endurance store: `open()` in a write, append or create mode; `os.remove`, `os.rename`, `os.mkdir`,
  `os.rmdir`; a filesystem format or mount; an `rp2.Flash` block write or erase; and the SCD30 driver's commands that
  store a value in its NVM (the set read from the Interface Description, not from memory).
- Each site is pinned by name with its trigger (boot defaults, boot repair, a changing PUT, a command) and why it is
  needed. A new or moved site fails, naming file:line, until the owner decides it. The list grows only on the owner's
  word, as the gc.collect() sites already work.
- Seen failing first: a planted extra `open()` for write and a planted `os.rename()` in a scratch copy, both named.

## E3. Behavioural pins: the flash operations per logical write
- Unit tier, with an open/os call recorder (the pattern CLAUDE.md describes for TmpScratch): a changing config PUT is
  one open for write and one close of the config file itself, nothing else; an unchanged PUT, zero; a boot with a
  valid file, zero; Reset to defaults, one remove per file. SCD30: a PUT changing n NVM-backed fields, n writes;
  unchanged, zero. Existing compare-before-write tests count where they already pin one of these.

## E4. A read-only sweep of every production write path (a fresh agent)
- Every write to flash or NVM in `src/` and the generated modules, per trigger (boot, PUT, command, restart, any
  periodic path), per device and mode, checked against the rule; the SCD30's NVM semantics from its datasheet (which
  commands persist, the continuous-measurement start among them).
- Output: one table. Anything that could write less becomes an owner question; nothing is changed by the sweep.
- Also: every U35 decision taken on the owner's behalf, re-read against CHECKLIST 24.

## E5. Documentation
- SPECIFICATION.md Part D's review checklist gains the least-wear item; C.8's write-safety constraints point to it;
  the pillars' "Design principles" Part (the doc work) carries it. CLAUDE.md names the guard once it exists.

## Order
E4 (read-only) beside E1; then E2 and E3 on the reverted code; E5 with them; then the twin re-record and the W6 gate.
Each block a fresh agent, files disjoint from D2d's (SPECIFICATION.md, BACKLOG.md, tests_hardware/README.md).

## Open for the owner
1. Keep lane P's one separable change: the boot write now holds the config lock, so a Reset to defaults waits for
   it (no extra write)?
2. The guard's scope: product code and generated modules only, or the hardware tests' device scripts too (already
   behind the persistence_write markers)?
3. Timing: inside U35 before the W6 gate (recommended: the gate then tests the final code), or a unit of its own
   after U35?

## Owner answers (owner, 2026-10-22)
- 1: "1. is good." The boot write keeps the config lock.
- 3: "3. Inside U35, so it already gets into the first wave of real hardware runs"
- 2: "yes, it's about pattern enforcement only, and it's valid for both firmware and the test scripts, but with the
  gate variable applied in the tests, it is already well set up. So the rule applies for all and is already well
  implemented in the tests, no need to change." E2 covers the firmware (`src/`, buildgen's templates, the generated
  modules); the tests stay as they are.
- "Still wait for my go ahead."
