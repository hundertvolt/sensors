B3 hand-back (U33 lane B, block B3, the lane's final block). Branch `audit/u33-b`, worktree `S/wt-u33b`. **Lane B final head is 629069e**, with nothing uncommitted and nothing pushed. I used about 30 tool calls.

**Commits**
- **e8a12af, step 4: applied.** The E722 bullet now carries A.U33.06's text: "Bare `except:` (E722) stays enabled (owner, 2026-07-13, `c0dfd20`, paraphrase: flag bare excepts rather than silence them): every one it flagged has been fixed, none remains in any lint scope, and the rule keeps it that way." The citation row `CLAUDE.md	improved-quality/pycheck.sh` is removed in the same commit.
  - Facts checked first: a grep for bare `except:` over the eight scopes finds nothing; `pyproject.toml` has no E722; `c0dfd20`'s own message says bare excepts stay flagged.
  - The commit message names the meaning change: the stale "tracked to-do" framing becomes the current state, the retired pycheck.sh comparison goes, and the tag gains its commit plus "paraphrase". The rule, its actor and its date are unchanged.
- **629069e, the two wozi sentences: applied** (found by their text).
  - UART bullet: "wozi is never flashed" becomes "no session ever flashes or bench-tests `wozi`". Its reason and the (agent, 2026-09-11) tag are kept.
  - WoZi bullet: "never physically flashed or bench-tested" becomes "never bench-tested", still tagged (owner, 2026-09-03, `a19691c`). After the test-suite sentence I added: "No session ever flashes `wozi`; like every legacy unit, it moves to the refactored firmware only by the owner's own reflash (owner, 2026-09-26, paraphrase)."
  - The commit message names the meaning change: narrowed to sessions, following the owner's most recent decision.
- `git diff c6b8a07..HEAD -- CLAUDE.md` shows exactly 3 hunks. All 4 allowlist rows named for lane B are now gone: citation `Session 2` and `pycheck.sh`, and vocab :7 and :12. Vocab :45 is untouched. No audit IDs appear in any commit message.

**Seen failing first:** with the E722 text edited and the row still present, `test_citations.py::test_the_allowlist_only_shrinks` failed, naming `CLAUDE.md	improved-quality/pycheck.sh` (1 failed, 14 passed). After the row was removed, the 4 readers passed (43 passed, exit 0). Log: `S/u33/laneB/b3_seen1.log`.

**Checks on 629069e**
- The 17 repo-wide scans from U32's common brief, in one process: 874 passed, exit 0, 77.9 s.
- After the wozi edit: citations, decision_vocabulary, legacy_paths and no_variant_literals, 43 passed, exit 0.
- No log contains `MemoryError` or "memory allocation failed".
- The only warning is the known one: the datasheets submodule is not initialised.
- As the brief said, I did not run the whole `tests_scripts` tier; the lead runs it on the integration head.

**Paired times** (base `S/wt-u33plan` at c6b8a07, then head, one run, two alternating rounds, in seconds; every run exit 0 with the same pass counts on both sides):

| Reader | Base | Head |
|---|---|---|
| citations | 11.89 / 11.06 | 11.24 / 11.10 |
| decision_vocabulary | 10.07 / 9.16 | 8.74 / 9.32 |
| legacy_paths | 1.90 / 1.98 | 1.94 / 2.05 (+0.05 s) |
| no_variant_literals | 8.95 / 8.80 | 8.51 / 8.51 |
| comment_block_cap | 5.49 / 4.91 | 4.99 / 4.82 |

No reader is over the time rule's bounds. Logs are `S/u33/laneB/b3_scans17.log`, `b3_pairs.tsv` and `b3_pair_*.log`.

**Decisions (agent, 2026-10-21)**
- At the UART site I wrote "flashes or bench-tests", R-6's optional parenthetical. The sentence's reason ("untestable there") needs the testing half once the owner may reflash the unit.
- The new 2026-09-26 sentence goes after the test-suite sentence. That way the 2026-09-03 tag stays where it was, on both statements it covers.
- Each edited span is rewrapped only within its own lines; no neighbouring line changed. This leaves the UART bullet with three shorter lines (72, 75, 66 characters).

**Other**
- Effect by mode (STA/AP/Silent/Off/USB): none. These are documents only, and no mode's behaviour is described differently.
- Silent-failure scan: nothing to scan, since nothing executable changed.
- Relay line written under `## B` in `S/u33/relay.md`.
- Runs: I logged b3_checks.sh's start and its exit 0 in `S/u21/RUNS.md`. The lead can merge 629069e into `audit/u33-int`.
- No real hardware was touched, and nothing of mine is running.