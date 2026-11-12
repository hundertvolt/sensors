# U34 planning, block P2: the cut, waves, rulings, risks and blocks (lead, 2026-10-21)

You are the second of two read-only planning blocks for unit U34 of a whole-project audit (vendored code, third-party
attribution, the type-check and lint configuration, the explicit-`Any` baselines). You run no tests, builds or network
commands and change no worktree. Small `python3 -I` helper scripts go only under `S/u34/plan_scratch/`; nothing is
written anywhere else. Your final message is your record (subagents here cannot write report files): at most about 200
lines.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: `S/wt-u33plan` (detached at
`c6b8a07`, U32's final tree). Never read `arduino/` (`':!arduino'` in every git grep, `-- . ':!arduino'` on every git
log). `legacy/` is reference-only and never edited. `ext/` changes only by re-vendoring an unmodified upstream tag (owner,
2026-10-01; `S/u34/pk/U34.md:376`).

## Inputs
- Block P1's record `S/u34/handbacks/P1_final.md`: the step table, open findings, the packet-vs-code drifts and its
  "For P2 to rule" list (a) to (f). It is your start: do not re-locate what it located; open a site only to settle an
  edge.
- `S/u34/upstream_captive.md`: the one upstream fetch P1 asked for, done by the lead (year 2019, holder p-doyle, no
  NOTICE). Steps 10-12 are no longer "needs upstream".
- The packet `S/u34/pk/U34.md` (read only the steps P1 marks to write, part landed or conflicts, and the carried
  action texts they name), and `audit/order/work_order.json` (unit U34; and, for routing, the later units' file lists).
- U33 (documents) lands before U34: `S/u33/lane_plan.md`, P1 rows 3, 4, 22, 29 and 30, P2's R-2, R-3 and R-18. U35's
  file list holds many test files and `src/asy_system_service.py`.
- The format: `S/u33/lane_plan.md` "## P2" and its LEAD NOTES, and `S/u32/lane_plan.md` "## P2" (a unit with code).

## What earlier units taught about the cut (check each edge before settling yours)
- For every file a lane changes, list every `tests_scripts/` file that reads it (grep its name) as that lane's readers.
  A source-wide check that a lane's change trips is that lane's to run.
- Type-check changes: the three mypy passes (`pyproject.toml` main pass, `digital_twin/typecheck.ini`,
  `host_typecheck.ini`) see different module universes. A change to one pass's config is checked by that pass on the
  whole scope, and by `tests_scripts/test_mypy_any_baseline.py` and the lint/type scope checks.
- A `src/` header change is comments only, but every `src/` change (even a comment) moves `tests_hardware/twin_record.json`
  hashes: the lead re-records it at the close. A real bytecode change in `src/` (for example removing
  `UDPSocket.write_and_recvfrom()`) needs its tests at both GC stages and the twin.
- Routing rule: a finding or a part outside the unit's files goes to the next unit in `work_order.json` whose files list
  holds its file; with none, U35 for a test file and U37 for any other.
- Block size: blocks over the 80-call valve were the ones owning a large file run per device at both stages, or a
  document span plus checks. Size each block by its run load and its document span, not only its line count.
- Documents: one owner per document; THIRD_PARTY_LICENSES.md is read by `tests_scripts/test_decision_vocabulary.py`
  (`_LICENCE_FILE`) with no allow-list row, so every new sentence with decision vocabulary carries its actor or source.

## Produce
2. THE CUT: lanes by file family, one owner per file, at most four agents at once. Per lane: files, steps (by P1's
   number), open findings, size, checks at -1 and 32768 (with base times where `S/u32/base_times.tsv` has them, else
   "base to measure"), its `tests_scripts` readers, seen-failing-first items, dependencies.
3. WAVES AND ORDER, each dependency with its reason; the first commit any other lane needs, named like U31's <CORE>.
4. RULINGS DRAFT under the owner's review-list rule: each ruling names what settles it (a source, a recorded resolution,
   an owner decision quoted from the tree, a standing project rule) or is marked process. Only an item that nothing
   settles AND that has real impact goes on the owner's list, in plain words with its options and their effects per
   device and bus. Expect that list to be empty or very short. Rule on every one of P1's (a) to (f) and every P1
   "conflicts" row. For (a), state how many modules each pass's baseline holds, which lie in U34's 28 files, which the
   routing rule sends elsewhere, and what the step's own text ("the baseline ends empty") requires of this unit.
5. RISKS by operating mode (STA, AP, Silent, Off, USB); the UART wire format; the memory gates at both GC stages (zero
   MemoryError and zero "memory allocation failed", never fixed by `gc.collect()`, a threshold or `-X heapsize`); the
   frozen image (which steps change bytecode); timing (which files grow; growth over 10 % and 0.5 s, or over 10 s, is
   made efficient, never by cutting strictness).
8. BLOCKS: each lane cut into fresh-agent blocks of about 60-80 tool calls at file-group seams (no file split across two
   blocks of one lane); the last block of each lane runs the lane's complete checks.
Also: the base-time shard list, one row per file the unit grows (`path@-1`, `path@32768`, or a bare `tests_scripts`
path), split into three shards of similar total time.

Be exact: every claim about the code cites path:line at `c6b8a07`.

## Working economy (binding)
About 60-80 tool calls; at 80 you stop at a clean seam and hand back what is done, saying what is left. Batch reads;
never re-read a file you have already read in this block.
