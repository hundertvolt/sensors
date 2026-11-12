# U35 planning, block P2: the cut, waves, rulings, risks and blocks (lead, 2026-10-21)

You are the planning block that turns four location records into U35's lane plan. Read-only: no tests, builds or
network commands, no worktree changes. Helper scripts only under `S/u35/plan_scratch/p2/`. Your final message is your
record (subagents here cannot write report files): at most about 250 lines.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: `S/wt-u33plan` at `1dd6dd5`
(read `tests/test_asy_neopixel_driver.py` and `tests_js/shell.test.js` as `git show 970b63b:<path>`). Never read
`arduino/`; `legacy/` reference-only; `ext/` never edited.

## Inputs
- The four location records `S/u35/handbacks/P1{a,b,c,d}_final.md` (steps 1-45, 46-110, 111-144, 145-179): your start.
  Do not re-locate what they located; open a site only to settle an edge.
- The packet `S/u35/pk/U35.md` (only for steps you must settle) and `audit/order/work_order.json` (U35 and later units).
- Findings routed to U35 since the packet was cut: `audit/sweeps/open_findings.md` rows targeting U35 (among them
  OF-231, OF-226, OF-184's file, OF-70's driver-side string) plus two not yet in the tree, both to U35:
  (1) OF-233 (U32's records, at `970b63b`): real-clock waits a loaded host can overrun in five notification test files
  (`tests/test_notification_{neopixel,scd30,sgp40,scd30_sgp40}_integration.py`, `tests/test_asy_notification_service.py`;
  sites in `S/u32/review/handbacks/FX8_final.md`): the same work as A.U35.13's driven time on those files.
  (2) U34's explicit-`Any` residue: the modules `S/u34/handbacks/T1_final.md` lists, sent to U35 by U34's plan R-2
  (`S/u34/lane_plan.md`): each loses its explicit `Any` sites and, in the same commit, its baseline line, its ANN401
  entry where it has one, and its `_RESIDUAL` row in `tests_scripts/test_mypy_any_baseline.py`.
- The format: `S/u32/lane_plan.md` "## P2" (a code unit's cut) and `S/u34/lane_plan.md` "## P2" and LEAD NOTES.

## The lead's rulings already made (lead, 2026-10-21; apply them, do not re-open)
- L-1 Driven time: extend `tests/_fake_time.py`'s existing `DrivenTime` in place (opt-in asyncio shim, `advance`,
  `run_until`, `jump`, `wait_for`/`wait_for_ms` shims; the ticks-only default unchanged), modelled on the neopixel
  file's `_YieldOnlyAsyncio`/`_DrivenClock` and the webserver tests' shims; no second class of the same name. Its
  self-test goes in `tests/test_driven_time.py`. Settled by CLAUDE.md's reuse-first rule and SPECIFICATION.md G.2. It
  is the first commit every driven-time step needs (name it like U31's <CORE>).
- L-2 No NTP-synced requirement in a boot with no SSID (Run 1, the generated-boot smoke): those checks assert no E and
  no W entry; the synced half stays proven at Runs 5 and 8 (P1c row 118, P1d section 4).
- L-3 The wire log is bounded; the tree's wording stays (P1d section 4).
- L-4 M.SPEC.160 lands in U35 after E.2.3 exists (P1c row 128); the non-dict config test stays (P1a 4.11, P1b);
  stale packet names follow the tree (`neopixel_freq`, `UARTComm`, `FakeNtpServer(port, *, poll_ms, poll_tries)`).
- L-5 Hardware stays parked: every step or part needing the bench is listed for hardware session 1 with its round;
  U35 runs only `--collect-only` and the twin. After U35's push the lead stops for the owner's order of hardware
  session 1 and the U36/U37 document work (owner, 2026-10-20).

## Produce
2. THE CUT: lanes by file family, one owner per file, at most five agents at once. Per lane: files, steps (by number),
   findings, size, runs at -1 and 32768 with base times (`S/u32/base_times.tsv` where it has them, else "base to
   measure"), its `tests_scripts` readers, seen-failing-first items, dependencies. The UART module's comment-only steps
   and changelog rows keep the wire format untouched (owner, 2026-09-25: "the UART wire format is not touched").
3. WAVES AND ORDER, each dependency with its reason (from the records: step 32 before the driven-time steps; step 108
   before 112; step 151 before 125 (h) and 160; A.U35.01's `audit/b3/` before 137, 138, 141, 153; M.SRC_CORE.131 before
   85's new cases); the first commit each other lane needs.
4. RULINGS DRAFT under the owner's review-list rule: each names what settles it or is marked process; only an item
   nothing settles AND with real impact goes on the owner's list, in plain words with options and their effects per
   device and bus. Rule on every "conflicts" row and every "(agent, 2026-10-21)" proposal in the records, on OF-167/OF-60
   (the blank FRAM chunk against an undriven bus), on P1a's torn-write code mapping (row 3, section 4.2), on where the
   twin record re-record at both GC stages sits (P1c 134/136/140, P1d 172, OF-229), and on the B3 measurement steps
   (`audit/b3/`, timing and load) as one lane or the lead's.
5. RISKS by operating mode (STA, AP, Silent, Off, USB); the frozen image (which steps change `src/` bytecode); the
   memory gates at both stages; timing (driven time should make files faster; growth over 10 % and 0.5 s, or over 10 s,
   is made efficient, never by cutting strictness).
8. BLOCKS: each lane cut into fresh-agent blocks of about 60-80 tool calls at file-group seams (no file split across
   two blocks of one lane); the last block of each lane runs the lane's complete checks; the whole `tests_scripts`
   tier is the lead's, once, on the integration head.
Also the base-time shard list (the files the unit grows or changes, `path@-1`/`path@32768`), split into three shards.

Be exact: every claim about the code cites path:line at `1dd6dd5`.

## Working economy (binding)
About 60-80 tool calls; at 80 you stop at a clean seam and hand back what is done, saying what is left. Batch reads;
never re-read what you hold.
