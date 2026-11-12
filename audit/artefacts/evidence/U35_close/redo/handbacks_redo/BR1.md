BR1 hand-back, saved by the lead from the message it sent (2026-10-27). Commits 651d3e79, 5023bcf7, 32a62f28 on audit/u35-braise (on 36bee227).

BR1 hand-back (U35 lane BR1), worktree S/wt-u35braise, branch audit/u35-braise. Not pushed. Nothing uncommitted (node_modules was already untracked).

Commits:
- 651d3e79 (item 1, already sent to you): verdicts are now one file per module, `audit/b3/raising_verdicts/<module>.json`.
  - Raises are keyed by function, call groups by "function::callee". A call verdict splits that function's calls out of the module-wide group.
  - The walk refuses a stale key and writes nothing in that case. New flag: `--check`.
  - Every hand "unreachable" is rendered into a generated block in e51.md's header. e51_sweep.py's render keeps the header, so its --check stays green.
  - No-change proof: the 36bee227 tool and the new one, both run on 36bee227, give identical raising.md and stdout (both diffs empty).
- 5023bcf7: math_helpers.py.
- 32a62f28: asy_print_log.py.
- Each commit was checked: walk `--check`, `e51_sweep.py --check`, `review_rows.py --check`, and test_citations/test_decision_vocabulary/test_comment_block_cap (666 passed). The raising.md diff touches only that module's rows.

Rows by verdict, before (651d3e79, module-wide groups) and after (per-function groups):
- math_helpers.py: open 9, unreachable 1 → handled 6, unreachable 5 (11 groups).
- asy_print_log.py: open 25, transitive 22, unreachable 1 → handled 50, unreachable 39 (89 groups).
- asy_base_classes.py: not started (tool-call budget). 120 per-function call groups are left; the one raise row is already "handled". Before: open 42, transitive 33, inherently safe 2, unreachable 1.
  - `S/u35/laneB/br1/groups.py <tree> <module>` prints the exact keys a verdict file needs.

Defects: none in either module. No src change, so no rebuild and no MicroPython runs were needed.

e51.md rows added: 44 in the generated "Unreachable raises" block (5 math_helpers, 39 print_log). Each row carries its proof and the narrow except around it, if any.

Points for you and the owner:
1. The e51 block sits in e51.md's header, above a new "## Uncovered lines" heading, because e51_sweep.py (not in my file set) re-renders everything after the header. If you would rather e51_sweep.py render it, that is a change to that tool.
2. Two classes every row shares are stated once, in each verdict file's "conventions" key, and raising.md does not render that key:
   - a C-stack overflow (I.4(d.1));
   - a small fixed allocation (F.2 → I.4(a)), whose catching except is named there: `_log_dead_task()` at asy_system_service.py:326, and the generated boot entry's `except BaseException` at sensortask_<device>_main.py:38, emitted by buildgen/codegen.py:867.
   Making the walk render it would conflict with BR2/BR3, so it is your call.
3. A wording question on asy_print_log.py's "Never raises" header: it holds only modulo allocation. On an exhausted heap every logging call can raise MemoryError at entry (the *args tuple or the generator; G.2's task-top caveat). get_log()'s two lists grow with the configured history_length and reach the webserver's `except Exception` at asy_webserver_service.py:1005, which writes that module's entry as unavailable, the right layer. I recommend no code change; the header could name this, which is a doc decision.
4. Stale on the head, for the base_classes lane:
   - the handled `_checked_write_results` raise proof cites callers :507/:689 (excepts :508/:690); its call sites are now :514 and :696;
   - the walk's three debug print keys (507, 689, 795) are stale too. I left them so item 1's diff stayed empty.

Runs: all through `S/u35/laneB/br1/run.sh`, with RUNS.md lines: item1_diff, item1_selftest, item1_checks, mh_walk, mh_checks, pl_checks. All rc=0. Scratch copies deleted; logs are in `S/u35/laneB/br1/`.

nothing of mine is running
