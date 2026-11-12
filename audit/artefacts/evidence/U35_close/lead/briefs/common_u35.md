# U35: what every lane block reads besides its own brief (lead, 2026-10-21)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Base `f3fff0e` (LEAD NOTES 1);
base worktree for paired times `S/wt-u35base` (rebuilt; never edit it).

## Reading
- `S/CHECKLIST.md`: binding; it is your only general reading (items 17-21 are the working economy). This file
  overrides its unit specifics:
  - subject `U35 lane <L>: <summary>`; logs in `S/u35/lane<L>/`;
  - branch `audit/u35-<l>`, worktree `S/wt-u35<l>`, created from `f3fff0e` and set up with `S/u23/rebuild.sh`;
  - a later block continues on the same branch and worktree.
- The plan `S/u35/lane_plan.md`, only these parts:
  - from P1, the step-table rows for your steps (search by step number): their evidence is your start, and a "landed"
    part is not redone;
  - from P2: P2.1, your lane in P2.2, P2.3, the rulings your steps name (P2.4), P2.5 and your block in P2.8;
  - the LEAD NOTES (they amend P2).
- Your steps' texts: `python3 -I S/u35/tools/steps.py --standing <your step numbers>` gives the packet's standing
  sections (the silent-failure classes, the operating modes, the procedure) plus your steps. Nothing else from the
  860 KB packet.
- A later block: the previous block's hand-back (`S/u35/handbacks/<L><n>_final.md`) and the tree are your start.
- The relay `S/u35/relay.md`: read your `## <L>` part before each step; write a line only where your brief says.

## Sites
P1 and P2 located sites at `1dd6dd5`; at `f3fff0e` only tests/test_asy_neopixel_driver.py and tests_js/shell.test.js
moved. Locate each site by its quoted text before editing, never by a line number alone. If you cannot find a site, or
a part has already landed: stop that part and report it.

## Rules
- Files: only your lane's (P2.2 and LEAD NOTES 2a; `S/u35/lead/lanes.py` holds the lists). Another lane's file is never
  edited; a defect found there goes in your hand-back with its line.
- No audit ID in any text outside `audit/`: test_citations.py refuses them, and avoid `Session N` and `Step N` too.
  Decisions:
  - tags read "(owner|agent, YYYY-MM-DD)";
  - an owner decision quotes the owner's words and the question; a paraphrase is marked "paraphrase";
  - rewording never changes actor, qualifier, scope or foreclosure, and the commit says "no meaning change" or names
    the change;
  - every new sentence with decision vocabulary carries its actor or source.
- Comment blocks are at most 3 prose lines. `src/` edits follow LEAD NOTES 7 (the mpy-cross byte compare).
- `ext/` and `legacy/` are never edited, and `arduino/` is never read: every git grep carries `':!arduino'`, every git
  log `-- . ':!arduino'`. Never real hardware: `tests_hardware/` only with `--collect-only` or the twin. The UART wire
  format is untouched.
- Memory: zero `MemoryError` and zero "memory allocation failed" in any output, at -1 and at 32768. Never a
  `gc.collect()`, a threshold or a `-X heapsize` change as a fix. A deliberate injection is worded clear of both markers.
- Time: LEAD NOTES 4.
- Allowlists only shrink, and only the lead edits them: a row your change orphans goes in your hand-back.
- Least wear (CHECKLIST 24): a change that adds, multiplies or reshapes a write to the flash filesystem or the
  SCD30's NVM, product or test, is stopped and handed back as an owner question.
- `tests_scripts/test_twin_record.py` goes red on any `src/`, device-script or runner change: expected. Never edit
  `tests_hardware/twin_record.json` (LEAD NOTES 8 has H2's one exception).
- Retries (owner, 2026-10-20): only a test that runs into its timeout is retried, twice. A "Passed only on retry" is a
  finding you root-cause.
- Every new test is seen failing first. A guard that passes at once is bitten in a scratch copy; nothing planted is
  ever committed.
- Decisions during execution:
  - take the more conservative, more easily reversible option grounded in sources, and log it as "(agent, 2026-10-21)";
  - never ask;
  - fix a consistency defect in your own files rather than flag it.
- For each change, name its effect per operating mode (STA, AP, Silent, Off, USB) and per device where it differs.
- Before your lane's final: run the 17 repo-wide scans of `S/u32/briefs/common_u32.md` ("Before your lane's final")
  once on your head, in one process. Also run every `tests_scripts` file that reads a file you changed: P2.2 lists your
  readers; grep the names to be sure. Not the whole tier (LEAD NOTES 5).
- Runs:
  - CHECKLIST's Runs (12-14); port-binding runs in `unshare -n S/u24/ns_xdg.sh`;
  - the host is shared (LEAD NOTES 6): count heavy processes before every wall-time-bound run;
  - one blocking wait per run, never a poll loop of tool calls.
- Safety:
  - kill only your own processes, by pid, checked first; never a pgrep pattern;
  - no `git stash`; `rm` only with literal paths or `"${var:?}"`; never write onto a device path;
  - never `grep -r` over the scratchpad; every timestamp from `date -u`.

## Hand-back = your record
At most 35 lines unless your block says more; subagents cannot write report files. It holds:
- commit hashes; steps by verdict (applied, landed, deviated with why);
- seen-failing cases and bites, one line each;
- red checks with their exact line; relay lines written;
- before/after times; decisions "(agent, 2026-10-21)";
- for a non-final block, the state the next block starts from;
- runs with their exits, and "nothing of mine is running".

## Datasheets (lead, 2026-10-21)
The PDFs under `/home/user/sensors/datasheets/` are AES-encrypted with an empty password; the venv and the system
python cannot decrypt them. `S/u35/lead/pdfvenv/bin/python -I` has pypdf and pycryptodome: `PdfReader(path)`,
`.decrypt("")`, then each page's `extract_text()`. Write extractions under your lane's log folder, never into the tree.
`S/u35/lead/ds/bst-bmp388-ds001.txt` is the BMP388's.

## Same-device runs (lead, 2026-10-22)
Never run two processes of the same test file for the same device at once, plants and bites included: each wipes its
`tests/_tmp/<file>_<device>` scratch when it starts (tests/_tmp_scratch.py:52), so the other fails with ENOENT (T3d).
