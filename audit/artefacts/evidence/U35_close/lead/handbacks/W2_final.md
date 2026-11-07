W2 hand-back (lane W, block 2). Commit `0d33534` on `audit/u35-w`, on top of W1's `1b638f1`, in S/wt-u35w. Nothing is uncommitted, nothing of mine is running, and the typings symlink is removed. I used about 63 tool calls.

**Findings by verdict**
- OF-197, applied. The encoding guard's scopes are now host_typecheck.ini's `files`: buildgen/ and the tests_hardware/ host code join, and device_scripts/ stays out. A test holds the scopes equal to the ini. An `encoding=` that is not a string literal (None, a name, a subscript) is now flagged. Both new trees were already clean, so it lands green.
  - Still not matched, as the OF row says (none today): tempfile text mode, TextIOWrapper, os.fdopen, codecs.open, gzip/bz2/lzma "t" mode, argparse.FileType, an aliased open. subprocess `text=` stays out by R-13.
- OF-199: test_tool_help.py reordered (applied). test_port_lock.py was already in D.15 order at f3fff0e (helpers :57-209 sorted, tests from :217), so it was already landed.
- OF-206, applied. In _repo_scan.py the docstring walk now enters statements only, through a new `statement_nodes()` that keeps ast.walk's order. The tree is freed before one lazy token pass, and `prose_blocks()` is cached by (path, text), so checks in the same run share each file's read.
  - Every block is unchanged: 28649 blocks over 722 tracked files, plus 8 edge samples, compared equal against the base module (w2_equiv.log).
- OF-207, applied. `_ruff()` takes the venv's ruff first and PATH's only when the venv has none. It refuses a version pyproject.toml does not pin, the same form as test_ruff_exemptions_live.py.
- OF-212 (the schema half), applied. A ConfigManager whose file name is computed at run time is now named in the failure. It passes only once listed in `_UNREAD` with its reason; the list is empty because there are none today. A stale listing fails.
  - New in the same class: a file name with no schema owner was exempt silently. SCD30 has a schema but is not in `_OWNERS`. Such a name is now named too; only config_HWTEST_* is exempt by name.
- test_definitions_js_mirrors.py: no change. OF-231 landed on the JS side in W1, and the file is already in D.15 order.

**Seen failing first, and bites** (nothing planted was committed): 7 new cases failed on the old code (w2_first.log):
- scopes vs ini;
- three bite rows (`encoding=None`, `encoding=mode`, `encoding=options[...]`);
- the computed schema name;
- the unowned schema name;
- the stray ruff (it returned stray/ruff, not venv/ruff).

The non-ASCII guard passed at once. Bitten in a scratch copy by dropping `isascii()`: it failed.

**Times** (paired, alternating against f3fff0e at nice 19, load about 1.3-1.7)
- test_citations: 10.17-10.74 s → 8.14-8.48 s (3 pairs).
- test_host_text_encoding: 1.65-1.75 s → 1.35-1.38 s. It was 2.1-2.3 s, 33 % slower, before I made it efficient.
- test_decision_vocabulary: 7.49-7.72 s → 5.98-6.16 s.
- test_lint_ceilings flat (8.7-9.1 s); test_device_script_config_schemas 0.63-0.74 s → 0.67-0.76 s.

**Checks**
- ruff on tests_scripts/ is clean, and the host mypy pass is clean (306 files).
- Run 1: 33 files, one per process (the changed files, all 28 _repo_scan readers, the commit checks); 32 green.
- Run 2, after the last edit: 17 files; 16 green.
- One red, not mine: test_no_variant_literals fails on `'arzi'` at tests_js/live-backend-put-matrix.test.js:34-35 (EXPECTED_SKIPS keys, from W1's `1b638f1`). That file is W3's.

**Decisions (agent, 2026-10-21)**
- The encoding scopes are tied to host_typecheck.ini by a test.
- SCD30 is not added to `_OWNERS`: its schema is read through `get_cfg_schema()` (src/asy_scd30_driver.py:584), and I did not check that against the extracted constant. Its file is named instead.
- `_ruff()` also checks the pin, to match its sibling.
- `prose_blocks()` is cached per (path, text).
- The encoding guard skips an ASCII file that names no open, read_text or write_text.

**Scan** (all classes): the unowned schema name is new and fixed here. The unmatched encoding forms are covered by the OF-197 row. A .py that fails to parse falls back to the hash reader; that is covered because ruff parses every file in the lint gate. The cache cannot go stale (pure in path and text). This is host tooling only, so device behaviour is unchanged in STA, AP, Silent, Off and USB on every device.

**Facts owed:** X none. Y none. Lead:
- No allow-list rows orphaned.
- The new `_UNREAD` dict starts empty.
- Two copies of `_ruff()` now exist (test_lint_ceilings.py, test_ruff_exemptions_live.py; the second is in no lane): a shared-helper candidate.

**Runs** (RUNS.md lines written): citations timing rc 0; runall 1 rc 0 (one reader red); grown-files timing rc 0; runall 2 rc 0 (same red, its line logged at exit); encoding timing rc 0.

**W3's start state:** audit/u35-w at `0d33534`; node_modules still links to S/wt-u8's. Open thread: the 'arzi' literals at tests_js/live-backend-put-matrix.test.js:34-35 (W3's file).

**Logs:** S/u35/laneW/ — w2_first.log, w2_equiv.log, w2_time_citations.log, w2_time_grown.log, w2_time_encoding.log, w2_runall.log, w2_runall2.log, w2_r_*.log, w2_mypy_host.log, w2_prof_base.log.