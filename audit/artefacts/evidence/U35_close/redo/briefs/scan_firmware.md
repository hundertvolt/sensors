# SCAN-FW: firmware and buildgen against the pre-audit state (lead, 2026-10-28)
This brief replaces `inv_firmware_additions.md`. Owner, verbatim (2026-10-28):
- "Just to clarify. Firmware state at the beginning was already quite solid. We gained substantial knowledge ever
  since. The mistake was how that went into the project. My expectation is that no real, verified gap is
  re-introduced. But the way it flows into the firmware and buildgen is *really* minimal change."
- "Our findings and gained knowledge are extremely valuable. Speculative and hypothetical effects maybe, maybe not.
  Resulting cascades are a red flag at least."
- "Hypothetical findings which are suspicious to be real need to be verified"

**Target.** Per module: the pre-audit code, plus each real, verified gap and each owner-decided change, each in its
really minimal form. This scan establishes that list and the facts behind it. You change nothing in the repo.

## Range and scope
- From the audit's start `25caf528` (2026-09-25) to the integration head `497b3eda`. Read the worktree
  `S/wt-u35int` and its git history; never write to it.
- Your file group is in your launch message. Firmware means `src/` and the generated device modules
  (`build/generated_src/`, produced by buildgen from `devices/*.toml`). Buildgen is in scope too.
- Legacy reference: `legacy/firmware/python/`, read-only; the field units run it.
- Never read `arduino/` (use `':!arduino'` on git grep/log). `ext/` is vendored and out of scope. Never open anything
  under `/root/.claude/` or any agent transcript.

## What counts
- A behavioural change: a task, a timer, a retry, a timeout or timed wait, a periodic action, a guard or validation
  branch, a fallback, a state, a config field, a log entry type, an error path, a buffer or caching scheme, a lock,
  a widened or narrowed accept rule, a removed behaviour.
- Not counted: rewording, comments, renames, typing, restyling, and code moved between files with its behaviour
  unchanged. Per file, one line saying you checked for these.
- Read diffs, not whole files. Use `git log --format='%h %ad %s' --date=short 25caf528..497b3eda -- <file>`, then
  `git show <h> -- <file>`, or `git diff 25caf528 497b3eda -- <file>`. Diff a renamed file against its old name.

## One row per change
- **where:** file:line range at 497b3eda.
- **what:** one line, the behaviour as the device sees it.
- **commits:** short hashes.
- **origin:** the finding or decision behind it. Sources: `audit/sweeps/open_findings.md` OF rows,
  `audit/consolidation/M_*.md` items, SPECIFICATION.md Part N's "Basis" for a tunable, the commit subject, and any
  `(owner, date)` / `(agent, date)` tag in the code.
- **evidence:**
  - O: an owner decision. Quote it verbatim with its source (`S/u35r/recovered/owner_rulings_after_LN118.md`,
    SPECIFICATION.md, CLAUDE.md).
  - F: an observed failure of the pre-audit code (bench, field, or a test that failed on it; say where).
  - H: hypothetical, found by reading or by a scan.
- **legacy:** yes / no / partly, with legacy path:line.
- **form:** design or patch (a local fix around a symptom), and one line why.
- **depends on:** the other addition it exists to protect, support or work around, or none.
- **device cost:** code lines; tasks, timers, timed waits and allocations at run time; any per-wake or per-request
  cost.
- **class:**
  - R, a real improvement: evidence O or F.
  - K, a valuable finding with questionable code: the knowledge stays, the code is in doubt.
  - H, hypothetical.
  - X, excessive growth: right intent, more code than needed.
  - C, cascade: it exists because of another addition. Name the root.
- **for H, the triage:**
  - *suspicious*: a concrete mechanism in our code, and either a trigger that occurs in normal operation on these
    devices or a rare trigger with a severe consequence (a hang, a watchdog reset, data loss, a wrong measurement);
  - *implausible*: say why.
- **for suspicious H, one minimal verification:**
  - A software mechanism: one small reproduction against the real code. Use the pinned Unix port
    `/root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M`, with
    `MICROPYPATH=<int>/build/generated_src:<int>/src:<int>/tests:.frozen`, or the twin. Run it a few times.
  - A platform behaviour: the pinned MicroPython source, `/root/pico-toolchain/micropython` (v1.29.0).
  - A hardware-only effect: the datasheet (`datasheets/`) and the legacy field behaviour. Anything only the board
    can settle goes on the hardware-round list.
  - No campaigns, no grids. If a check is not minimal, record the item as unverified and say what it would take.
  - Outcome: confirmed, refuted or unverified, with the evidence.
- **minimal change:** for R and confirmed items. Give the smallest change against the pre-audit code that closes the
  gap, described or as a short sketch in your hand-back, never applied, with its size. Give the one test that pins it:
  an existing test's name, or what such a test would assert.
- Already established by the lead: the NeoPixel overlay's 300 s rewrite, its origin (OF-75, U22, an agent's choice),
  and its lost-shutdown-cancel cascade (`S/u35/lane_plan.md`, LEAD NOTES 358). Record it as a row with that evidence;
  do not re-verify it.

## Runs and efficiency
- Every reproduction runs as `unshare -n S/u24/ns_xdg.sh nice -n 19 <command>`. Write a line to `S/u21/RUNS.md`
  (append-only) before it, `| RUNNING <time> <date> | U35 scan <G> <label> pid <pid> | <dir> | <command> | <time> |`,
  and a done line after it, `| done <HH:MM> rc=<rc> | U35 scan <G> <label> pid <pid> |`. Scripts and logs go in your
  scratch dir, `S/u35r/scan/work_<G>/`. One run at a time.
- Grep for anchors, then read line ranges. The audit records are large: grep them by file name or OF number.
- No speculation: a field you cannot establish says "not found" and what you searched. Do not re-derive a mechanism's
  correctness beyond what the verification needs.

## Hand-back
- Write `S/u35r/scan/<G>.md`, first line "<G> scan, written by the lane (<date -u>)". It holds:
  - the rows, by file;
  - per-file totals: rows and code lines per class;
  - the cascades: chains of additions that exist for each other;
  - the verifications, each with its outcome;
  - the hardware-round list;
  - the minimal-change list (R and confirmed items), each with its size and its pinning test.
- Final message: the path, and one line of counts per class with code lines. Last line: "nothing of mine is running".

## Addendum (lead, 2026-10-28): the project scheme and pillars
Owner, verbatim: "While,you scan, check for violations of our project scheme and pillars, much of the excessive
additions do violate them". So each row also gets:
- **scheme:** the pillar or project rule the change violates, with the line that states the rule. Also the one it
  claims to serve, if it names one. Write "none" when it violates nothing.
- **Where the scheme is written:**
  - the pillars P1-P12: the table in `audit/CONSOLIDATION.md` (around lines 19-36);
  - CLAUDE.md "Hard rules" and "Working agreements". Among them: hypothetical-MemoryError wrapping is not blanket
    policy (SPECIFICATION.md Part F.2); a wedged I2C bus is the watchdog's job, with no I2C-level timeout; long-blocking
    operations (Part F.3); the memory-safety ladder (Part I.4); the comment-block cap; "same top-level features";
  - SPECIFICATION.md Part C (the shared driver architecture, C.1-C.7), Part D (the review checklist, D.1 "flag, don't
    silently change", D.10 consistency), Part G (the shared-primitive catalog: reuse before writing a new one);
  - the owner's 2026-10-28 rules quoted at this brief's top: minimal change, nothing built on a hypothetical, no
    patches, cascades a red flag; owner, verbatim: "hardcoded delay checks like this are a very bad, very awkward
    pattern".
- Read those by anchor and line range, not whole. Add per-file totals of violations by rule, and list in the
  hand-back the rules violated most often.
