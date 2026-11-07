# N12: the live tier's config files written beside their directory; a scanner blind spot; test.sh's tier order (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then N4r's hand-back `S/u35r/handbacks_redo/N4r.md` ("FINDINGS" and
"ITEM 2"). Base, worktree and branch named at launch; logs in `S/u35/laneN/n12/`. Test and tool code only: no src/
change (if you find the fix belongs in src/, hand it back with evidence), no wear.

## Items
1. The host-write leak (CLAUDE.md's host-wear rule: a test must not leave files on the host). tests_js/_twin_process.js
   `makeConfigDir()` returns `mkdtempSync(prefix)` with no trailing separator, the live tier passes it as the twin's
   `--config-dir`, and `config_filename()` (src/asy_config_manager.py near :238) concatenates `cfg_path + "config_" +
   name + ".cfg"`, so every live-tier twin writes its config files BESIDE its directory in /tmp, and
   `removeConfigDir()` removes only the (empty) directory. The lead counts about 810 such files in /tmp now.
   (a) Prove it first: a test that boots one twin through the live tier's own helpers and asserts that every file it
   wrote lies inside the config directory and that nothing is left after removeConfigDir(): red on today's code.
   (b) Fix the caller (the trailing separator where the directory is handed to the twin). Check every other caller of
   `--config-dir` (scripts/_twin_process.py, the Python harnesses, digital_twin's runner): which pass a trailing
   separator, which do not; fix each that does not, red first where it leaks.
   (c) Make the twin runner refuse a `--config-dir` without its trailing separator with a clear error (the contract
   `config_filename()` relies on), so a new caller fails loudly instead of leaking; its own test, red first. If the
   runner's owner text (digital_twin/README.md) documents the flag, state the rule there.
   Do not delete the stray files in /tmp: list their exact paths in a file in your log dir and hand it back; the lead
   removes them.
2. tests_scripts/_repo_scan.py `prose_blocks()` does not know JS regex literals: a literal with an odd number of `"`
   hides every later comment from the repo scans (N4r's find; test_decision_vocabulary caught it once by luck). Teach
   it regex literals in the JS it scans (the contexts where `/` starts a regex, not a division), with tests: a regex
   holding a quote no longer hides the comments after it (red on today's code), a division is not taken for a regex.
   Then run every repo scan that uses prose_blocks over the tree and report any comment it now sees for the first time
   and what the scans say about it (a new finding goes to the lead, never allow-listed).
3. N4r's item 2 (the tier order, its brief `S/u35r/briefs/n4r_probe_order_writes.md` item 2 and the original N4 brief
   it points to): scripts/test.sh runs `_build_sites` before the tests_scripts tier is backgrounded, with the
   tests_scripts/test_test_sh.py test that pins the order (red on today's order), scripts/test.sh's stale lines it names
   (near :415-434 and :499) updated, and the no-frozen failure count re-measured as N4r describes. The paired whole-
   test.sh timing needs a quiet host: write its exact commands into your hand-back; the lead runs them.

## Proof and checks
Lint with `S/u35/lead/lint_direct.sh` (shellcheck for test.sh); the mypy passes; `npm run lint`, `npm run typecheck`,
`npm run test:unit` and the changed live test in the namespace (node_modules linked after the lock check); the comment
cap, test_citations, test_decision_vocabulary, test_tunables_register, test_test_sh.py and every tests_scripts reader
of a changed file. Your base has a changed `toolchain/`: any scripts/test.sh run uses a private copy (`cp -a S/tc-int
S/tc-n12`, deleted after). Shell rules (binding): scripts as files you wrote, never `bash -c` holding rm, never nohup
chains, rm only as its own command with a literal path or "${var:?}", a timed-out run's children killed; a refused
command stops you. Commit subject `U35 lane N12: <summary>`, the two trailers; do not push. Past 80 tool calls hand
back at a seam. Hand-back: commits; each red and green with log paths; the stray-file list's path; item 2's new
sightings; item 3's commands; last line "nothing of mine is running".
