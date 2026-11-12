# U30 rulings re-sorted under the owner's review-list rule (lead, 2026-10-20, during U29's gate)

Rule (owner, 2026-10-20, criticism of U29's 15-item list): an item reaches the owner only if no source, project-consistency
rule or owner decision settles it, and it has real impact; stated in plain words; a consistency defect is fixed, not flagged.
Every ruling stays logged in the REGISTER as decided on the owner's behalf (CLAUDE.md workflow). The planner's header ("all go
on the owner's review list") is replaced by this sort; its own closing line already read "None of these needs the owner."
Line numbers in R-* are from `fd4ac55` and are refreshed with the packet after U29's squash; the sort does not depend on them.

## Settled, with what settles each
- By a recorded resolution or catalog: R-2 (M.SRC_CORE.034: base_classes would close an import cycle), R-3 (M.SRC_CORE.016
  Resolved (b)), R-4 (codes reserved, REGISTER), R-5 (M.SRC_SENS.017), R-9 (B63-B78 taken: a fact), R-34 (the landed SPEC
  figures win over the packet's).
- By an owner decision: R-7 (OF-146 "2 b"), R-8 (OF-145 "1 b"), R-24 (OF-36's default stands; its question is already the
  owner's pending one from U11, not a new item).
- By the finding's own requirement: R-12 (OF-62: the text already prints), R-14..R-17, R-19 (OF-78/80 ask that "the
  resolver's outcome names the cause"; the two NTP-band codes are numbered by U2's catalog), R-20, R-21, R-31.
- By a standing rule: R-6 and R-10/R-11 (checks tighten, never loosen; A.U30.16's categories), R-13 (the memory-marker
  wording rule), R-18 (same features: output bit-identical), R-28 (efficiency without lost strictness), R-29.
- Process, staging or parking (no product effect): R-1, R-22, R-23, R-25, R-26, R-27, R-30, R-33, R-35, R-36, R-37.

## R-32: the planner's ruling stands; one question checked at L0 (agent, 2026-10-20)
- A first reading here (an uncaught task death would be silent at the unit tier's OFF level) was wrong and is withdrawn:
  `tests/microtest.py`'s `run()` installs `digital_twin/unix_port_unretrieved_report.py`'s always-printing handler first
  (`microtest.py:112`), every twin launcher does the same, `start_tasks()` keeps a handler already set, and
  `tests_scripts/test_exception_handler_contract.py` pins all three. Uncaught deaths reach every PC gate at any level.
- Still open, and measured at the lead's L0 before any lane runs: a caught `MemoryError` in a class with a logger goes
  through the level-gated `err()` (`asy_print_log.py`), so where the unit tier builds such a class at the default OFF,
  its line would not reach the unit gate. L0 lists the unit tests that build a logger-bearing class at OFF and can reach
  an allocation-failure path (the hammers, the system builds); for those the generated system builds' level is read from
  their device files. If any can, the gap is closed in U30 (conservative: the gate must see it, owner 2026-09-26 "machine-
  checked"), test first, in the owning lane; if none can, R-32 stands as written and the U35 row records why.
- Found so far (read-only, at `4ac9a7f`): the generated `build_system()` takes `debug: int | None = None` and builds every
  logger from it (`buildgen/codegen.py`'s `_BOOT_KEYWORDS`, the `LogConfig(..., debug)` lines), so a unit-tier system
  build starts its loggers at OFF unless a stored level is applied after boot. L0 reads which tests pass `debug` or a
  stored `DebugLevel`, and whether a caught allocation failure there reaches any gate another way.
- Also found: the stored `DebugLevel` defaults to 0 (`asy_system_service.py`'s `_VAL_DEBUG_LEVEL`), and no unit-tier
  scenario or system test sets one, so the unit tier's system builds and hammers run their loggers at OFF; the twin CI
  suite sets `DebugLevel=5` for its verbose pass (`scripts/_digital_twin_ci_suite.py`), so the twin gate sees the paths
  it exercises. The residual is therefore the unit gate's half for logger-gated catch lines. Fold (6) is staged at U30,
  and the conservative option keeps evidence visible: L0 names the files, then the owning lane (or the lead, for a file
  no lane holds) lands a level of at least ERR there, test first; it is not deferred to U35.

## For the owner
None so far. U30's own close list follows the same rule.

## R-32's residual: decided by the owner (owner, 2026-10-20)
Question (lead, 2026-10-20): in the unit tests a caught `MemoryError` logged through a logger prints nothing, because the
unit tests run at `DebugLevel` 0, so the unit memory gate cannot see it. Options: (1) turn logging on (error level or
above) in the unit tests that can actually run out of memory (the system builds and the load tests, listed at L0);
(2) turn it on for every unit test; (3) leave the unit tests at 0 and rely on the twin's level-5 pass. Answer: "Option 1
is good". U30 lands it: L0 lists the files, the owning lane (or the lead, for a file no lane holds) raises the level, test
first. This supersedes the agent's ruling above where they differ.

R-32's residual, L0 (lead, 2026-10-20): mapped (`S/u30/option1_l0_map.md`), assigned to W2 lane L and lane V (lane_plan.md's
last LEAD NOTE).
