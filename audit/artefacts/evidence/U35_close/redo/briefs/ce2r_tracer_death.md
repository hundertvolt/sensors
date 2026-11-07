# CE2r: the coverage tracer's silent death, detected and avoided (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneE/ce2r/`.
This redoes block CE2 of U35, whose commit (8f504a4) was lost in the container reset; only the lead's summary of it
survives: `S/u35r/recovered/lead_notes_119_148.md` (the CE2 bullet) and `S/u35r/verify/V3.md` row 111. Treat that summary
as a lead, not as fact: re-derive every claim from the pinned source and from runs before you build on it.

## The finding (from the summary; prove it first)
Under build-settrace, an exception raised while the trace callback runs (the C-stack tests reach their recursion limit
inside it) leaves `mp_prof_is_executing` set (py/profile.c around :168-173, py/vm.c around :161-185 at v1.29.0; read them
in your toolchain copy's micropython checkout), so no later line of that test file is traced: the coverage of every test
after it is silently missing and nothing says so. CPython documents the same unset-on-error rule for its tracer.

## What to build
1. Prove it: a minimal test file under `tests/` scratch (not committed) run with tests/_coverage_runner.py on
   build-settrace, showing lines after the raise untraced; then find, by measurement and not by grep, every committed
   tests/ file whose coverage run loses its tracer (the summary says 6, one of them
   tests/test_digital_twin_sensortask_integration.py around :507). List each with the test and line where it dies.
2. Detection in tests/_coverage_runner.py: after the file's tests, run a one-line probe compiled under a traced `src/`
   name; if its line is not recorded, the tracer died: write `<out>.json.incomplete` naming the last traced file and
   line (keep that as the trace callback's cheapest possible bookkeeping) and still dump the lines (every path, as now).
3. scripts/test.sh lists every `.incomplete` note in its summary and exits 3 (E.5.3's code 3, today "only a coverage
   report failed to render"), never 1: the tests passed; only the coverage measure is short. Its E.10 summary line
   says which. CI already tolerates 3 (E.5.3's table): check ci.yml's handling, do not change ci.yml.
4. Avoidance: `tests/_untraced.py`, `untraced(call)`: a plain call unless the coverage runner set the module's `tracer`
   (build-standard has no `sys.settrace`, so nothing else may touch it), else `sys.settrace(None)`, the call, and the
   tracer restored in `finally`. Each file from step 1 runs only its deliberately exhausting call through it, so the
   rest of the file is traced again; every assertion kept, and each file still passes at both GC stages under
   build-standard. Lines run inside `untraced()` are not counted: say so in E.5.1's tracer-classes text.
5. Tests for each new behaviour, each seen red first (a plant in a scratch copy where the test itself cannot be red
   first): the probe flags a planted raising trace callback and names its last line; no note on a healthy file; the
   restore in `finally` on a raise; `untraced()` a plain call with no tracer; test.sh's listing and exit 3
   (tests_scripts/test_test_sh.py's own style, no full coverage run needed). Then each step-1 file under the coverage
   runner with no note.
6. SPECIFICATION.md E.5.1 (the tracer-death class, what `untraced()` excludes), E.5.3 (code 3's second meaning), E.10
   (the summary line); the register "per A.U35.41's table" is CEr's, not yours.

## Proof and checks
Coverage-runner runs use your own toolchain copy: `cp -a S/tc-int S/tc-ce2r` and `PICO_TOOLCHAIN_DIR=S/tc-ce2r`; never
run its setup; never the shared `/root/pico-toolchain` for anything that could rebuild it (redo_common.md's toolchain
hazard). The test files at both GC stages with build-standard directly, zero memory markers. No full `--coverage` run:
that is CEr's, on the merged head. ruff, the mypy passes (stubs at `S/shared/typings`), the comment cap,
test_citations, test_decision_vocabulary, test_test_sh.py and every tests_scripts reader of a changed file. Other lanes
run: nice 19, and keep CPU use modest. Delete S/tc-ce2r when you are done and say so.

## Not yours
src/, toolchain/, ci.yml, digital_twin/, audit/ records, every allow-list (hand back the row you need). Commit subject
`U35 lane CE2r: <summary>`, the two trailers; do not push. Hand-back: commits, the source lines that prove the
mechanism, the files that lose their tracer (test and line), each red and green with log paths, the docs lines, anything
that surprised you; last line "nothing of mine is running".
