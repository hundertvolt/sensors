# Lane checklist (binding for every agent from U24 wave 2 on; replaces common.md, CONCURRENCY.md and exec_prompt.md
# as reading; your brief adds only its own scope). Owner, 2026-10-13: "reduce effort by improving efficiency and
# working style ... Still, don't cut back on accuracy."
S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Read the rulings your brief cites, not the whole list.

## Never
1. Push, `git stash`, edit `ext/` or `legacy/`, read `arduino/` (every git grep ends `-- ':!arduino'`; ruff only on the
   eight scopes), touch real hardware (`tests_hardware/` only `pytest --collect-only`), write into `/root/pico-toolchain`.
2. Run `npm install`/`ci`/`test`, `uv sync`/`lock`, `apt-get`, `sudo`, `playwright install`, toolchain builds, the whole
   `scripts/test.sh`, twin CI runs or the whole `tests_scripts/` tier (unless your brief says so).
3. Edit a file outside your set (stop and report it), or edit while a run of yours reads the tree.
4. Weaken a check, raise a bound, or add to an allow-list (they only shrink; only the lead edits them: report the line).
5. Put an audit ID (OF-, OR, A.U, M., SF-, unit/wave/lane names, WIP hashes) in any committed file except under `audit/`.
6. Change the UART wire format; put a device literal outside `devices/` (fixtures: `fixture-device`).

## Always
7. Tests first: each behaviour change has a test seen failing on the code before it (name the failing line); a test
   that passes at once is a guard and gets a planted bite in a scratch copy (nothing planted is committed). A pure
   migration's check is the file green at both GC stages.
   A bitten `tests/` module loads only when the test file runs from the bite's own directory (MicroPython puts the
   script's directory first on its path): copy the test file beside it, and check the failure names the bitten behaviour.
8. Sources, not memory: `datasheets/` for chips; `/root/pico-toolchain/micropython` (v1.29.0); `ext/microdot.py`.
9. Root-cause every failure; never retry it away. A failure you cannot explain goes in the hand-back with its output.
10. Zero `MemoryError` / "memory allocation failed" in any output, at gc -1, 32768 and settrace; injected ones are worded
    clear of both.
11. Comment blocks at most 3 prose lines (JS, CSS, config too); decisions carry "(owner|agent, YYYY-MM-DD)", owner words
    quoted or marked "paraphrase". D.15 member order is your last edit to each file.

## Runs
12. Every MicroPython, vitest and twin- or runner-starting pytest file in its own `unshare -n S/u24/ns_xdg.sh nice -n 19 ...`,
    one file per process, one run at a time in your worktree, one heavy run of yours at a time. A wall-time-bound file
    (live JS, twin concurrency/integration/uart-link/webserver files, anything asserting elapsed time) starts only while
    at most 4 heavy processes run on the host (`ps`). Command forms: your brief or `S/u24/briefs/common.md` "Runs".
13. RUNS.md (`S/u21/RUNS.md`, append only, each line ends with a newline): one line at start and one at exit for every
    run over a minute or in the background. Kill by pid only. At hand-back nothing of yours runs. A run standing in for a
    CI job (a job's own command, `--part`, `--gc-threshold`) starts from a tree without gitignored build output, as CI's
    checkout does: remove `build/generated_html` and `frozen_modules` first, or a leftover build hides what the job builds.
14. Timing: wrap your normal check runs in bash `time` (`/usr/bin/time` is not on the host) and report the after-times of files you grew; compare
    with the lead's base table (`S/u24/base_times.tsv`, your brief names it). No separate before-runs. A file more than
    10 % slower at either stage is made efficient, never given a bound.

## Before each commit (after `git add` of your files by name)
15. ruff on your files; the mypy passes they need (cold cache, temporary `typings` symlink to `S/shared/typings`, removed
    after); for `js/`/`tests_js/`: `npm run lint`, `npm run typecheck`, `tests_js/lint-ceilings.test.js`; the 12 doc and
    convention checks listed in common.md "Before every commit". Commit with `git -c commit.gpgsign=false commit`,
    subject `U24 lane <L>: <summary>`, ending with the two trailers (Co-Authored-By / Claude-Session) as in common.md.
16. Silent-failure scan of your files (`audit/sweeps/silent_failure_scan.md`, all classes, the modes your brief names).

## Working economy (owner, 2026-10-20: "81% of re-reading really is much, try to improve here as you suggested. But don't cut back on quality or depth ever.")
Every turn re-reads your whole conversation, so a turn costs more the longer you run. Nothing here drops a check, a run,
a read your step needs or a piece of evidence; it removes repeats and output nobody reads.
17. Batch: independent reads, greps and checks go out together as parallel tool calls in one turn, not one per turn.
18. Run output goes to a log file. Read its exit code and a summary: counts, `grep -n` for FAIL/Error/Traceback/the two
    memory markers, `tail -n 20`. Anything not green: read every part of the log it points to, then root-cause it.
19. Read by site: locate with `grep -n`, read the range you need (`sed -n a,bp`); never re-read what you hold unless it
    changed. Read a whole file once, when the step needs all of it. Diffs: `git diff --stat`, then the hunks you need.
20. Wait in one call: one blocking call per up to 9.5 minutes (`timeout 570 tail --pid=<pid> -f /dev/null; tail -n 5 <log>`),
    never short polls, sleeps or Monitor ticks.
21. Lifetime: at the end of a block your brief names, commit and hand back even if you could go on. Past about 80 tool
    calls, finish the step in hand, commit and hand back the same way; a fresh agent continues. A block hand-back adds a
    state note: each step left with its state, open threads with `file:line`, and "nothing uncommitted".
22. Disk (lead, 2026-10-21, after the disk filled at 17:05): before every wall-time-bound or twin run, `df -h /` must
    show at least 3 GB available; below that, start nothing and tell the lead. Keep raw data (coverage files, copies of
    trees, archives) only until summarised, then delete your own with literal paths. A red or a failed write while the
    disk was full is not evidence: re-run it once the space is back, and say so.

## Hand-back = your record (subagents cannot write report files here): at most 30 lines
Commit hash; steps by verdict (applied / partly / already landed with line / nothing at U24 with why); deviations;
seen-failing-first, one line each; red checks with their exact line and who they wait on; scan findings (class, mode,
file:line, new or covered); facts owed to X, Y and the lead, one line each or "none"; after-times beyond 10 %; runs
started and their exits. Logs, if any, in `S/u24/lane<L>/`; only logs that prove a claim or show a failure.
