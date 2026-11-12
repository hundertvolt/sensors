# SCAN2: the second pass, hidden, overlaid and higher-order overkill (lead, 2026-10-28)

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Read-only: you change nothing
in the repo, the worktrees or the first scan's files. Your part (G1-G4) and its scope are in your launch message.

## The owner, verbatim (2026-10-28)
- The request: "Now with all that background and a sharpened vision, go through the changes since the audit start
  again and check if you found all such runaways, cascades, overkill places; there might be more hidden or overlaid /
  higher dimensional occurrences you did not see yet. And if you would remove those you already know, there might be
  side effects which make more overkill visible. Nevertheless, real features, real findings inside the minimal code,
  rare but real cases all keep effective."
- The background: "a verified finding or a taken decision stand for their own and are worth keeping at least
  documented. When cleaning the firmware and the buildgen, some of them may become obsolete, e.g. when removing
  cascades and issues these cascades themselves introduced and are overkill or runaway. They have no more direct
  meaning to the project anymore, but still are worth to know about in general. Others, which stay in scope, stay
  valid and effective as they are, but ideally are resolvable with way more minimal code. Rare but real conditions
  which drop out through the cleanup no longer matter. Rare but real conditions staying in scope still shall be
  addressed - no regressions, but more efficiency."
- Earlier the same day: "Firmware state at the beginning was already quite solid. ... My expectation is that no real,
  verified gap is re-introduced. But the way it flows into the firmware and buildgen is *really* minimal change.";
  "building upon hypothetical findings is a clear no-go"; "Hypothetical findings which are suspicious to be real need
  to be verified"; "hardcoded delay checks like this are a very bad, very awkward pattern".
- Settled, never to be questioned again: every "ok" on the review page stands as the owner's decision ("The OK in the
  review stay valid."); the Wi-Fi behaviour as built is the owner's ("We thoroughly discussed the WiFi issues and I
  decided everything already."); the FRAM per-owner CRC seed stays ("The FRAM idea of yours is good, keep it!"). For
  these you may only note a smaller form of the same behaviour, marked "form only".

## What the first scan already has (read before you start, by section, not whole)
- `S/u35r/scan_pub/REPORT.md` sections 2-5 (classes, real gaps, the code in doubt, smaller forms) and 8.
- The row files `S/u35r/scan_pub/A.md` (core, storage), `B.md` (network, UART), `C.md` (drivers, LED), `D.md`
  (buildgen, generated code). Rows have IDs like `A-B13`; grep `^### ` for the index.
- `S/u35r/picture/PICTURE.md` sections 2 (the lines L1-L8), 4 (misfits M1-M13) and 8 (the cleanup's rules).
- The census (lead, mechanical, src/ only): `S/u35r/scan2/funcs.tsv` (every new, changed or removed function with
  its size and shape deltas: try, raise, isinstance, if, while, time calls, waits, tasks/timers, report_if_fatal,
  log calls; new boolean flags, new except types, new raise messages, new numbers >= 100) and
  `S/u35r/scan2/families.tsv` (the same, grouped by shape across files). Tool: `S/u35r/scan2/tools/census.py`.
  "new"/"removed" include renames and moves, so check a pair before calling something new.
- Extracted trees: `S/u35r/scan2/base/` (25caf528, the audit's start) and `S/u35r/scan2/head/` (497b3eda, the
  integration head), each with `src buildgen js html devices`. Git: `/home/user/sensors` (use `git show <rev>:<path>`,
  `git log -S`, `git diff -M30% 25caf528 497b3eda -- <path>`); the worktree `S/wt-u35int` is at 497b3eda.
- Owner record: `PROJECT_AUDIT_PLAN.md` (the OR table), `S/u35r/recovered/owner_rulings_after_LN118.md`,
  `audit/review/decisions.json` and `answers.json` (status "ok" = the owner's decision). Origins: the action files
  `audit/actions/U*.md` ("Why"), `audit/sweeps/open_findings.md` (OF rows), the commit messages.

## What to look for (the sharpened lens)
1. **Hidden:** a change the first scan has no row for, or a row classed too kindly: an R that is an agent applying a
   general principle to a case found by reading, a K whose code is far beyond the knowledge, an "as landed" that is
   much larger than the behaviour needs.
2. **Overlaid:** one condition handled by two or more mechanisms, at different layers or in different modules (for
   example a retry in a driver plus the bus layer plus the recovery ladder; a catch in a helper plus its caller plus
   the supervisor). The owner's line: one simple mechanism at the layer that owns the fault, then the existing ladder
   (task end, supervisor restart, reboot, watchdog). A second mechanism for the same condition is overkill.
3. **Families:** one shape copied across modules: state flags, per-episode log flags, deadlines and age checks,
   retries, counters and caps, typed or typing-only guards, bool returns threaded through callers, extra log lines,
   try-wraps, `report_if_fatal()` sites, `raise` contracts. Use `families.tsv`. The verdict is per family: one
   mechanism in a shared base, or none.
4. **Higher order:** a mechanism that handles a condition another addition created (order 2, 3, ...), including
   fix-of-a-fix chains; an interface widened for one addition and threaded through every caller; a platform helper
   whose users are mostly in doubt; product code that exists for the tests (P4); a generality nobody uses
   (parameters, TOML keys, tunables with one value).
5. **Removal simulation:** assume the known in-doubt items are taken out (the pre-audit form restored where the
   change was hypothetical, excessive or a cascade). Name what else then loses its reason, and what then becomes
   visible as overkill that was hidden behind them.
6. **Keep effective:** for anything you would take out, name the real feature, owner decision, verified finding or
   rare-but-real condition that touches the same code, and the minimal form that keeps it effective with no
   regression. "Real" means an owner decision, an observed failure, or a confirmed reproduction or source proof.

## One row per finding
ID `S2-<G>-<n>`. Fields, one line each:
- **where:** file:line range at 497b3eda (or function), plus related sites.
- **what:** the behaviour as the device (or the build) sees it.
- **first scan:** the row ID(s) it extends, or NEW.
- **lens:** hidden / overlay / family / order-N / P4 / platform / generality / removal-effect.
- **condition:** what it handles, and whether that is observed, verified (by what), owner-decided, hypothetical, or
  created by another addition (name it).
- **class:** R, K, H, X, C (as in the first scan), with C carrying its order and root; plus OV when another
  mechanism already covers the condition (name it).
- **removal effect:** what goes with it (callers, constants, flags, catalog codes, FRAM chunk bytes, status/REST
  fields, JS fields, buildgen support, TOML keys; tests and twin parts as counts only).
- **keep:** what must stay effective, and its minimal form with an estimated size; or "nothing".
- **lines:** code lines involved at 497b3eda, approximate.

Mechanical changes (renames, moves, typing, comments) get no rows; say per file that you checked.

## Verification
- No runs: no Unix-port runs, no twin, no tests, no builds of the firmware. Static checks are fine: git, grep, the
  pinned MicroPython source `/root/pico-toolchain/micropython` (v1.29.0), `datasheets/`, `legacy/` (read-only), and
  read-only host Python on the extracted trees (`python3 -I`). G3 may run buildgen's generator on copies (below).
- A hypothetical that looks suspiciously real: do not decide it. List it under "needs verification" with the one
  minimal check that would settle it (what to run against the pre-audit code, and what the outcome means). The lead
  runs those serially.
- Never build on a hypothesis: a claim of "only X uses Y" or "Y exists because of X" is backed by grep or by the
  introducing commit (`git log -S`), cited.

## Rules
- Never read `arduino/` (`':!arduino'` on git grep/log). `ext/` is vendored and out of scope. `legacy/` is reference
  only. Never open anything under `/root/.claude/`, nor any agent transcript.
- No source copied into your file beyond identifiers and one-line anchors. Never write a credential's value; the
  hotspot fallback password is named only as "the hotspot default".
- Efficiency: read diffs and line ranges, not whole files; grep the audit records by anchor. Don't re-derive what a
  first-scan row already establishes; cite it. Target size of your file: about 30-60 KB.
- Records: say "the owner" (no pronoun). Quote the owner verbatim with the source.

## Hand-back
- Write `S/u35r/scan2/<G>.md`, first line "<G> second pass, written by the part (<date -u>)". It holds:
  - the rows, by family or chain rather than by file;
  - the overlay map: condition -> every mechanism handling it (file:line);
  - the families table: shape -> sites -> verdict;
  - the chains: root -> order 2 -> order 3, with what removing the root takes along;
  - first-scan rows to reclassify, each with the reason;
  - the keep list: what stays effective, in its minimal form, with size;
  - needs verification: each with its one minimal check;
  - totals: rows and lines per class, and lines that would go versus stay.
- Final message: the path, one line of counts, the three largest new finds in one line each. Last line: "nothing of
  mine is running".
