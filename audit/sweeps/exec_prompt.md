# Executing-agent brief (phase B)

You apply work-order steps of one unit to the `sensors` repo. The owner gave the execution go-ahead (OR145): the
rules, pillars and specifications are binding and applied as written, never changed to fit. Accuracy over speed.

## Read first
- `CLAUDE.md` in full (hard rules, comment cap, memory discipline, test rules).
- Your packet (path given in your task): every step of your lane set, in work-order order. Each step has the merged
  change (`M.*`, the end state) and the IDs of the actions it carries; the action texts follow at the end of the packet.

## How to apply a step
1. **Which part lands here.** "Lands here" names the carried actions. A merged change spanning several units names its
   stages in its Unit slot; apply only this unit's stage and leave later stages for their units. A later-unit stage you
   leave out must not leave this unit's tree inconsistent (no dangling reference, no failing test).
2. **Precedence.** The merged change's "A-C review fold" lines and its Resolved line win over its Change text; the
   merged Change text wins over a carried action's text. Owner rows quoted in either win over agent wording.
3. **Locating.** Line numbers are from older HEADs: find each site by its quoted text. If the site is already in the
   stated end state, record "already". If the quoted text cannot be found, search for where it moved; if it cannot be
   located with confidence, record "not found" with what you searched, and do not guess.
4. **Permanent text** (everything outside `audit/`): never cites an audit ID (`OR\d+`, `PQ\d+`, `A.U…`, `M.…`,
   `LEAD/R…`, `G\d/R\d+`, `HR\d+`, `RF\d+`, `H1.\d+`, list IDs like `V01`/`A2-03`, unit names `U\d+`). Decision tags read
   `(owner, YYYY-MM-DD)` or `(agent, YYYY-MM-DD)`; owner words are quoted exactly as the step gives them. Every comment
   block (header or inline) stays within 3 prose lines; Markdown keeps the file's existing wrap width and style.
5. **Code.** Match the surrounding idiom. Never edit `ext/` (unless your step is the vendoring refresh), never read
   `arduino/`, never touch `python/`, `modules/`, `build-*.sh` (reference only), never commit credentials, never run
   anything against real hardware (`mpremote`, `picotool`, `nmcli`, `tests_hardware` runners other than
   `--collect-only`).
6. **Checks you run.** After your edits: `ruff check <touched .py files>` (use `.venv/bin/ruff`), `shellcheck` on
   touched shell scripts (`.venv/bin/shellcheck`), and `uv run pytest -q <tests_scripts files>` for any
   `tests_scripts/` file you touched. Do NOT run `scripts/test.sh`, `npm test`, twin runs or other port-binding suites:
   the lead runs scoped and full gates after merging lanes.
7. **Out of scope.** Anything you notice that no step asks for: do not fix it. List it under "Findings" in your report
   (file:line, what, why it matters).
8. **Silent failures (owner, 2026-10-06).** While you write code and tests, watch for the classes in
   `audit/sweeps/silent_failure_scan.md` (an ignored status from the layer below, bounded storage that drops silently,
   detection left to chance, a swallowed failure, a window that loses time or data, a fault without self-healing, a fault
   one side detects and the other never learns of) in every file you touch. Where your step owns the site, close it
   (detect, count, fail visibly, recover) with a test that plants the fault; otherwise list it under "Findings" with its
   class and mode. Check every operating mode the code takes part in, not only plain operation: boot, the reset
   countdown, flash and FRAM writes, network loss and reconnect, calibration, recovery, reconfiguration, load (the mode
   list in that file).

## Finish
Commit everything in your worktree in one commit (or one per co-landing group if the packet marks groups), message
`<unit>: <short summary of the lane set>` (no audit IDs needed in the commit body beyond the unit name), ending with
exactly:

    Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8

Do not push. Report: branch name and commit SHA; a table with one row per step (`M-ID | applied / already / partly /
not found / deferred | note`); every deviation from a step's text with its reason; the Findings list.
