# U33 (DOC): what every lane block reads besides its own brief (lead, 2026-10-21)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Base `c6b8a07` (U32's final
integration head; LEAD NOTES 1). `<CITE>` is lane S's first commit (the SPECIFICATION.md item-32 repoint), relayed under
`## S` in `S/u33/relay.md`.

## Reading
- `S/CHECKLIST.md`: binding, your only general reading (items 17-21 are the working economy). This file overrides its
  unit specifics: subject `U33 lane <L>: <summary>`, logs in `S/u33/lane<L>/`, branch `audit/u33-<l>`, worktree
  `S/wt-u33<l>` from `c6b8a07` (a later block of your lane continues on the same branch and worktree).
- The plan `S/u33/lane_plan.md`: P1's step-table rows for your steps (the evidence is your start: a "landed" part is not
  redone), P2.1, your lane in P2.2, P2.3, the rulings your steps name (P2.4), P2.5, your block in P2.8, and the LEAD
  NOTES.
- Your steps' merged texts and carried actions: `S/u33/pk/U33.md` (only your steps by P1's number, and the carried
  action texts they name, at the end of the packet). Nothing else from the packet.
- A later block: the previous block's hand-back (`S/u33/handbacks/<L><n>_final.md`) and the tree are your start.

## Sites
- The packet quotes lines from older trees; P1 located every site at `c6b8a07`. Still locate each site by its quoted
  text before editing, never by a line number alone. A site you cannot find, or a part already landed: stop that part and
  report it with the text you searched for.

## Rules
- Documents only: no code file changes (the two allowlists are data files of lane B). No audit ID in any text outside
  `audit/` (test_citations.py:58-59 refuses them; avoid `Session N` and `Step N`, :54). Decision tags
  "(owner|agent, YYYY-MM-DD)"; an owner decision quotes the owner's words and the question, a paraphrase is marked
  "paraphrase"; compaction, migration and rewording never change actor, qualifier ("for now", "until ..."), scope or
  foreclosure, and the commit says "no meaning change" or names the change (CLAUDE.md, Working agreements, decision
  records). Every new sentence with decision vocabulary carries its actor or source (test_decision_vocabulary.py:22-32).
- Documentation holds current state, targets and rules, not the history that got there (CLAUDE.md, Working agreements).
- An open owner question in BACKLOG.md (6 and 7 today) stays as entered; nothing is decided against it.
- Allowlists only shrink, each row in the same commit as the text it covers (R-13), seen failing first: delete the text,
  see the stale-entry test name the row, then remove the row.
- Never real hardware; `tests_hardware/` only with `--collect-only`. The UART wire format is untouched.
- An unforeseen decision: the more conservative, more easily reversible option grounded in sources, logged in your
  hand-back as "(agent, 2026-10-21)". Never ask. A consistency defect in your files is fixed, not flagged.
- Time: your readers' base and after times back to back in one run, alternating `S/wt-u33plan` and your head (LEAD
  NOTES 3); over 10 % and over 0.5 s, or over 10 s: make it efficient, never by cutting strictness.
- Before your lane's final: the 17 repo-wide scans of U32's common brief (`S/u32/briefs/common_u32.md`, "Before your
  lane's final") once on your head in one process, plus every `tests_scripts` file that reads a file you changed (grep
  its name), then the whole tier once via `S/u29/tier.sh <wt> <outdir> <label>` (LEAD NOTES 4). Zero `MemoryError` and
  zero "memory allocation failed" in any output.
- For each change, name its effect per operating mode (STA, AP, Silent, Off, USB): for a document, which mode's
  description it changes, if any.
- Runs: CHECKLIST's Runs; one blocking wait per run, never a poll loop of tool calls.

## Hand-back = your record (at most 30 lines unless your block says more; subagents cannot write report files)
Commit hashes; steps by verdict (applied, landed, deviated with why); seen-failing lines; red checks with their exact
line; relay lines written; before/after times; decisions "(agent, 2026-10-21)"; for a non-final block, the state the
next block starts from; runs with their exits and "nothing of mine is running".
