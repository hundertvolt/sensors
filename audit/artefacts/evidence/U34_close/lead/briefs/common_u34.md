# U34: what every lane block reads besides its own brief (lead, 2026-10-21)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Base `147ea3f` (U33's integration
head; LEAD NOTES 1). `<UDPHDR>` is lane N's first commit (src/asy_udp_socket.py's header alone), relayed as
`<UDPHDR> <hash>` under `## N` in `S/u34/relay.md`.

## Reading
- `S/CHECKLIST.md`: binding, your only general reading (items 17-21 are the working economy). This file overrides its
  unit specifics: subject `U34 lane <L>: <summary>`, logs in `S/u34/lane<L>/`, branch `audit/u34-<l>`, worktree
  `S/wt-u34<l>` created from `147ea3f` and set up with `S/u23/rebuild.sh` (a later block continues on the same ones).
- The plan `S/u34/lane_plan.md`: P1's step-table rows for your steps (the evidence is your start: a "landed" part is not
  redone), P2.1, your lane in P2.2, P2.3, the rulings your steps name (P2.4), P2.5, your block in P2.8, and the LEAD NOTES.
- Your steps' merged texts: `S/u34/pk/U34.md`'s standing sections (the silent-failure scan, the operating modes, the
  register deltas), then only your steps by P1's number and the carried action texts they name. Nothing else.
- A later block: the previous block's hand-back (`S/u34/handbacks/<L><n>_final.md`) and the tree are your start.
- The relay `S/u34/relay.md`: read your `## <L>` part before each step; write a line only where your brief says.

## Sites
- The packet quotes lines from older trees and P1 located sites at `c6b8a07`; `147ea3f` moves the BACKLOG.md,
  CLAUDE.md, SPECIFICATION.md and tests_hardware/README.md lines. Locate each site by its quoted text before editing,
  never by a line number alone. A site you cannot find, or a part already landed: stop that part and report it.

## Rules
- No audit ID in any text outside `audit/` (test_citations.py refuses them; avoid `Session N` and `Step N`). Decision
  tags "(owner|agent, YYYY-MM-DD)"; an owner decision quotes the owner's words and the question, a paraphrase is marked
  "paraphrase"; rewording never changes actor, qualifier, scope or foreclosure, and the commit says "no meaning change"
  or names the change. Every new sentence with decision vocabulary carries its actor or source; THIRD_PARTY_LICENSES.md
  is scanned with no allow-list row (R-20).
- Comment blocks at most 3 prose lines; a header block changed in a `src/` file keeps its line count, so the frozen
  bytecode's line tables do not move; prove it with an mpy-cross byte compare of base and head (LEAD NOTES 7).
- `ext/` and `legacy/` are never edited; `arduino/` is never read. Never real hardware; `tests_hardware/` only with
  `--collect-only`. The UART wire format is untouched.
- Memory: zero `MemoryError` and zero "memory allocation failed" in any output, at -1 and at 32768; never a
  `gc.collect()`, a threshold or a `-X heapsize` change as a fix.
- Time: every file you grow or change is timed base (`S/wt-u33plan`, at `147ea3f`) and head back to back in one run,
  alternating (LEAD NOTES 4). Over 10 % and over 0.5 s, or over 10 s: make it efficient, never by cutting strictness.
- Allowlists only shrink and only the lead edits them: a row your change orphans goes in your hand-back.
- `tests_scripts/test_twin_record.py` goes red on any `src/` change of yours: expected; never edit
  `tests_hardware/twin_record.json` (the lead re-records it).
- Retries (owner, 2026-10-20): only a test that runs into its timeout is retried, twice; a "Passed only on retry" is a
  finding you root-cause.
- Every new test is seen failing first; a guard that passes at once is bitten in a scratch copy, nothing planted
  committed. An unforeseen decision: the more conservative, more easily reversible option grounded in sources, logged as
  "(agent, 2026-10-21)". Never ask. A consistency defect in your files is fixed, not flagged.
- For each change, name its effect per operating mode (STA, AP, Silent, Off, USB).
- Before your lane's final: the 17 repo-wide scans of `S/u32/briefs/common_u32.md` ("Before your lane's final") once on
  your head in one process, plus every `tests_scripts` file that reads a file you changed (P2.2 lists your readers; grep
  the names to be sure). Not the whole tier (LEAD NOTES 5).
- Runs: CHECKLIST's Runs (12-14); port-binding runs in `unshare -n S/u24/ns_xdg.sh`; the host is shared (LEAD NOTES 6).
  One blocking wait per run, never a poll loop of tool calls.

## Hand-back = your record (at most 30 lines unless your block says more; subagents cannot write report files)
Commit hashes; steps by verdict (applied, landed, deviated with why); seen-failing and bites one line each; red checks
with their exact line; relay lines written; before/after times; decisions "(agent, 2026-10-21)"; for a non-final block,
the state the next block starts from; runs with their exits and "nothing of mine is running".
