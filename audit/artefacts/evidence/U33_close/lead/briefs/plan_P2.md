# U33 planning, block P2: the cut, waves, rulings, risks and blocks (lead, 2026-10-21)

You are the second of two read-only planning blocks for unit U33 (DOC) of a whole-project audit. You run no tests, builds or
network commands and change no worktree. Small `python3 -I` helper scripts go only under `S/u33/plan_scratch/`; nothing
is written anywhere else. Your final message is your record (subagents here cannot write report files): at most about
200 lines.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: `S/wt-u33plan` (detached at
`c6b8a07`, U32's final tree). Never read `arduino/` (`':!arduino'` in every git grep, `-- . ':!arduino'` on every git
log) or `ext/`; `legacy/` is reference-only and never edited.

## Inputs
- Block P1's record `S/u33/handbacks/P1_final.md`: the step table (verdict and evidence per step), the open findings
  and the packet-vs-code drifts. It is your start: do not re-locate what it located; open a site only to settle an edge.
- The packet `S/u33/pk/U33.md` (read only the steps P1 marks "to write", "part landed" or "conflicts"), and
  `audit/order/work_order.json` (unit U33).
- The format: `S/u32/lane_plan.md` section "## P2" and its LEAD NOTES (U32's cut, waves, rulings, risks and blocks),
  and `S/u32/briefs/blocks.md` (how U32's blocks were briefed).

## What U31 and U32 taught about the cut (check each edge before settling yours)
- A test outside every lane's list that pins the old behaviour, or a source-wide check that a lane's new code trips: in
  U31 a test file calling `asyncio.run()` directly failed the harness-only check no lane's reader list held. For every
  file a lane changes, list every `tests_scripts/` file that reads it (grep its name) as that lane's readers.
- The generated code: `buildgen/codegen.py` emits each device's `sensortask_<device>.py`; a changed emitter reaches all
  six devices' tests (`tests/test_sensortask*.py` per device, the twin integration files, the boot contiguity check),
  `tests_scripts/test_buildgen_generate.py` and the generated-definitions JS tests. Name who owns each.
- Shared objects built whole: a NamedTuple or config built positionally whose new field forces every construction site;
  a Protocol whose new member breaks test fakes; `buildgen/error_catalog.json` rows; `SPECIFICATION.md` Part N rows for
  any added or removed `# @tunable` tag (the lead's); `tests_hardware/twin_record.json` (stale on any `src/` or
  device-script change; the lead re-records it at the close); `UART_C_PORT_CHANGELOG.md` (Class B, Python-internal,
  rows only: the UART wire format is never changed).
- Block size: U31's blocks over the 80-call valve were the ones owning a large file run per device at both stages (the
  supervisor block 122 calls, the scenario blocks 98-111); U32's were the review fixes spanning docs and checks (FX4 84,
  FX6 85) and a reader with the whole diff (92). Size each block by its run load and its document span, not only its
  line count.
- Documents: U33 is mostly documents (BACKLOG.md, CLAUDE.md, SPECIFICATION.md, tests_hardware/README.md). One owner
  per document; a step editing two documents goes to the owner of the larger part, the other part as a relay line.
  Every document lane's readers include `tests_scripts/test_citations.py`, `test_decision_vocabulary.py`,
  `test_comment_block_cap.py` and any check that greps the document (find them by grep). The owner's decision-record
  rules (CLAUDE.md, Working agreements) bind every reworded decision: actor, date, quote, "paraphrase", no meaning
  change unless named.

## Produce
2. THE CUT: lanes by file family, one owner per file, at most five agents at once. Per lane: files, steps (by P1's
   number), open findings, size, checks at -1 and 32768 (with base times where `S/u32/base_times.tsv`
   has them, U32's base on `72b1281`; mark the
   rest "base to measure"), its `tests_scripts` readers, seen-failing-first items, dependencies.
3. WAVES AND ORDER, each dependency with its reason; the first commit any other lane needs, named like U31's <CORE>.
4. RULINGS DRAFT under the owner's review-list rule: each ruling names what settles it (a source, a recorded
   resolution, an owner decision quoted from the tree, a standing project rule) or is marked process. Only an item that
   nothing settles AND that has real impact goes on the owner's list, in plain words with its options and their effects
   per device and bus. Expect that list to be empty or very short. Every P1 "conflicts" row gets a ruling.
5. RISKS by operating mode (STA, AP, Silent, Off, USB); the UART wire format; the memory gates at both GC stages (zero
   MemoryError and zero "memory allocation failed", never fixed by `gc.collect()`, a threshold or `-X heapsize`); timing
   (which files grow; growth over 10 % and 0.5 s, or over 10 s, is made efficient, never by cutting strictness).
8. BLOCKS: each lane cut into fresh-agent blocks of about 60-80 tool calls at file-group seams (no file split across
   two blocks of one lane); the last block of each lane runs the lane's complete checks.
Also: the base-time shard list, one row per file the unit grows (`path@-1`, `path@32768`, or a bare `tests_scripts`
path), split into three shards of similar total time, plus the per-device rows.

Be exact: every claim about the code cites path:line at `c6b8a07`.

## Working economy (binding)
About 60-80 tool calls; at 80 you stop at a clean seam and hand back what is done, saying what is left. Batch reads;
never re-read a file you have already read in this block.
