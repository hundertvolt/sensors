# D2S: runtime checks that only guard what typing enforces (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back).
Worktree and branch: in your launch message (the integration head, after the raising merge). Logs in `S/u35/laneB/d2s/`.

## The rule and the owner's words
SPECIFICATION.md D.2: "Don't defend against out-of-contract input at runtime if static typing already enforces it
(mypy) — dead weight for a scenario that can't occur", and "don't add runtime type checks 'just in case' (D.2)".
The owner, 2026-10-27, on asy_base_classes.py's `_checked_write_results`: "if the check you remove really solely
covers typing breakages and nothing else it can go (option b)", and asked whether the rule was kept elsewhere.
That check broke it (it came in by 2026-09-24, after the rule); lane BR4 removes it. Your task is the rest of src/.

The owner's test, 2026-10-27: "A strong hint for an unnecessary check is that it is proven to be fully covered by
typing adherence alone, and that it is unreachable with today's code". So both conditions together mark a removal;
neither alone does (a hardware-fault guard is unreachable in tests yet real; a reachable check is not dead weight).

## The lead's notes from the raising merge (binding)
- BR4 removed `_checked_write_results` (S/u35r/handbacks_redo/BR4.md item 7); its reading of SCD30's three
  `type: ignore`s (none on the results' path) was re-read by the lead and holds. Treat that site as done.
- The walk's header names the last commit that changed src/, so any commit changing src/ leaves raising.md stale
  until a later re-render (the lead re-rendered int, 96ed596f). Item 0b fixes that before your first src commit.

## Items, in order
0b. raising_walk.py's header: name something the same commit can carry (the src/ tree's content hash from the
   working tree, say), so a commit changing src/ and its re-render are current together. Bite: a src edit without
   the re-render fails `--check`; with it, passes.
0. Start from the records: every raising-walk verdict whose unreachable proof rests on typing (D.2, "every override
   returns", "mypy types it", and the like) in `audit/b3/raising_verdicts/*.json`, and every guard line that
   `audit/sweeps/e51_hits.json` shows uncovered. A guard on both lists is the first candidate; then item 1 finds the
   rest.
1. Inventory every runtime type or shape check in src/: `isinstance()`, `type(...) is/==`, `hasattr()`, `callable()`,
   `len()` checks on typed tuples, `except (TypeError, AttributeError, KeyError)` around typed values, and any
   assert-like raise on a value's type. The generated modules (build/generated_src) and buildgen/codegen.py's
   emitted code count too. One row per site with file:line.
2. Class each site, with its proof:
   - keep: the value comes from outside the type system: a request body or query, JSON parsed from flash or FRAM,
     wire bytes (UART, DNS, NTP, HTTP), a sensor reading, `Any`, a `cast`, a `type: ignore` on its path, or a
     documented duck-typed API (say which);
   - remove: the value's type is fixed by mypy strict on every path into the site (trace each caller and
     construction; no Any, cast or ignore), so the check only fires on a typing breakage, AND it is unreachable with
     today's product code (uncovered by the suite, or a walk verdict proves it unreachable; a test that reaches it
     only by injecting the type breakage does not count as reaching it);
   - unsure: anything else, handed back with the path that makes it unsure.
3. Remove the proven "remove" sites, one commit per module, each with the tests, raising-walk verdicts, e51 rows and
   review rows that named them updated or removed, the importers of that module at both stages (PER_DEVICE files
   on all six devices), zero memory markers. A removal never changes behaviour for type-correct code; if a test
   only exercised the type breakage, it goes with the check, named in the hand-back.
4. Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
Commits; the inventory with every site's class and proof; the removed tests by name; the unsure sites in prose for
the owner, each with a recommendation; last line "nothing of mine is running".
