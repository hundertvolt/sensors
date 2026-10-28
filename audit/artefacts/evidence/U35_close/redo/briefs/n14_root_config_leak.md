# N14: the unit tier writes config_SYSTEM.cfg into the checkout root; coverage dumps lost on a failed render (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then N12's hand-back `S/u35r/handbacks_redo/N12.md` (the same class of leak,
fixed for the live tier) and CEr1's hand-back `S/u35r/handbacks_redo/CEr1.md` ("Findings for you"). Base, worktree and
branch named at launch; logs in `S/u35/laneN/n14/`. Test and tool code only: no src/ change, no wear.

## The finds
1. CEr1 saw a test write `config_SYSTEM.cfg` (`{"DebugLevel": 0}`) into its worktree root at 03:17:08 during its
   coverage run. Eight lead worktrees hold the same file (dated from their first runs). The lead's read:
   tests/test_asy_system_service.py's `_make_service()` defaults to `cfg_path=""`, and about 119 calls rely on that
   default, so `SystemService.setup()` writes its config into the process's current directory, the checkout root.
   Every later run then reads that file back, so a run's result can depend on what an earlier run left behind. Two
   rules are broken: the host-write rule (CLAUDE.md: a test must not leave files on the host) and test isolation.
2. CEr1: offline in this container, `uv run scripts/_render_coverage.py` could not resolve its inline
   `coverage==7.16.2`, and scripts/test.sh's EXIT trap then deleted the raw dumps, so the run's coverage evidence was
   gone. Only CI has the network, so this is container-only, but an evidence-losing path is ours to close wherever it
   shows.

## Items
1. Prove item 1 first. In a scratch copy of the tree with no root config file, run test_asy_system_service.py and see
   the file appear. Re-locate every caller relying on the default. Check whether any other tests/ factory or direct
   construction passes no config path to a class whose setup() writes a file: grep, and run one sweep. A structural
   way: list the root's entries, git-ignored ones included, before and after each tests/test_*.py file in a scratch
   copy.
2. Fix: each test gets a fresh directory (the file's own `_tmp_cfg_dir()` or TmpScratch; read both). Keep `""` only
   where a test is about the default itself, and then point its cwd somewhere scratch. Run the file at both stages,
   with its time before and after.
3. A standing guard that a test cannot silently write into the checkout. scripts/test.sh snapshots the repository's
   untracked and ignored files (`git status --porcelain --ignored`, or what fits better: read how test.sh already
   handles its outputs) after its build steps and before the MicroPython tier. After the tier, it fails naming each new
   path outside the tier's own declared outputs. Test it in tests_scripts/test_test_sh.py, red first. Then check that
   the guard does not fire on a healthy run (one plain `scripts/test.sh` in a private toolchain copy, `cp -a S/tc-int
   S/tc-n14`, deleted after; inside the namespace; background with its own bound, about 12-15 min). Record the build
   change in BACKLOG.md's list for the owner's next chroot run.
4. Item 2: a failed render keeps its dumps and says where. Read the trap and the coverage path first; the dumps may
   only stay where a later run overwrites or removes them (a build/ or results directory), never as a new stray in
   /tmp. And the run's summary names the render failure as the coverage-short cause (exit 3). Its test, red first.
   Do not pin coverage differently or change the offline behaviour of `uv run`.
5. When everything is green, list the stale root config files in the lead's worktrees (`S/wt-*/config_*.cfg`, exact
   paths) in your log dir. The lead removes them; you delete only your own scratch copies.

## Checks
lint with `S/u35/lead/lint_direct.sh` (shellcheck covers test.sh); the mypy passes; test_test_sh.py and every
tests_scripts reader of a changed file; test_comment_block_cap, test_citations, test_decision_vocabulary. Shell rules
(binding): scripts as files you wrote, never `bash -c` holding rm, never nohup chains, never a `tail --pid` wait, rm only
as its own command with a literal path or "${var:?}", a timed-out run's children killed; a refused command stops you.
Commit subject `U35 lane N14: <summary>`, the two trailers; do not push. Past 80 tool calls hand back at a seam.
Hand-back: commits; each red and green with log paths; the callers fixed; the guard's healthy-run result; the stale
file list; last line "nothing of mine is running".
