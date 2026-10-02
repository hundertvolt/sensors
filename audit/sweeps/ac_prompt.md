# Phase A-C — brief for the merge agents (2026-10-01)

You are an A-C merge agent of the whole-project audit of the `sensors` repo at /home/user/sensors (branch
`claude/whole-project-audit-plan`). Audit execution is BLOCKED: you change nothing except your output file
`/home/user/sensors/audit/consolidation/M_<CLUSTER>.md`. Append as you go so partial work survives. No git writes, no
tests, builds, network or hardware; never read `arduino/`; `ext/` only to read Microdot semantics.

## Why

The owner (OR106 (2)): "scan the list for overlaps and conflicts (e.g. multiple changes at the same place) and
consolidate everything, so even if multiple changes would happen to one place, they are then smoothed into a single
change." OR106.a: all changes to one site merge into a single change; a conflict an owner row or the register settles
is settled, any other goes to the owner in the owner's format; the merged list becomes B1/B2's work order and the
execution go-ahead is given on it. OR111.a: the consolidated list, applied as a whole on top of HEAD, must be complete,
sound and adherent to every rule collected in this audit. Accuracy before speed (OR107.a): never sample; finish fewer
files completely rather than skim, and list the rest as NOT-DONE.

## Inputs

- Your CLUSTER's file list (in the prompt that launched you) and the site index
  `audit/consolidation/site_index.json`
  (`by_file`: every action ID whose Site cites the file). The index is a parser's output: also grep
  `audit/actions/*.md` for each of your paths (Site, Change and Blast slots) — an action the index missed is still
  yours, and a Blast entry that names your file without its own action is a gap you must report.
- The action files `audit/actions/*.md` (U0-U37, U8C, U8C2, C, SUPP_*). They already carry their verifiers'
  corrections (each ends with a "Verified …" line); read the cited action in full, including its Depends/Blast notes
  and any "co-lands with … A-C merges" note, and the file's Conflicts/Open-points sections.
- `audit/actions/AC_NOTES.md` (lead decisions, items 1-36+) — binding.
- The finished merges `audit/consolidation/M_*.md`: their "Gaps for other clusters" sections name gaps your cluster
  must carry (grep your cluster name), and their merged product end states are what your tests and docs must match
  (cite the M-ID).
- `PROJECT_AUDIT_PLAN.md` 3.2 owner rows OR1-OR130 (quote row + ".a" reading; the most recent owner decision wins;
  OR64: a missing owner trace never proves the owner did not decide); the register `audit/pass2/` (G1-G10, LEAD, REF).
- CLAUDE.md in full (hard rules, working agreements, tooling rules) and SPECIFICATION.md as the actions amend it.

## Method, per file of your cluster

1. Read the file at HEAD (whole file for code; the touched sections plus their context for large docs).
2. Collect every action touching it. Group them by site inside the file (function, class, constant, doc section).
3. Per site, write ONE merged change: the end state after all constituents, precise enough to implement without a
   question. Where constituents overlap, write the combined text once. Where they conflict:
   - an owner row, the register, AC_NOTES or a later verifier item settles it → settle it and cite the source;
   - otherwise → an owner question (owner format, below), and write the merged change with your recommended option
     marked "pending Qn".
   Where a constituent is obsolete because another removes its site, or is already superseded (withdrawn, DONE at
   HEAD), say so and drop it with the reason.
4. Staging: a merged change lands in ONE unit — normally the latest unit among its constituents. Split it into stages
   only when an earlier stage is a prerequisite of other work in an earlier unit (a B1 foundation used by B2 files);
   then list the stages, each with its unit and the site's state after it, and say which other change needs the stage.
5. Blast closure: for every blast item of every constituent (callers, generated code and templates, `js/` mirror, tests
   at every level, twin, docs, TOMLs, UART changelog, BACKLOG chroot list), name the merged change or action that
   carries it. Inside your cluster name your M-ID; outside, name the A-ID (the other cluster merges it). A blast item
   nobody carries is a GAP: add a merged change for it if the site is yours, else list it under "Gaps for other
   clusters".
6. Adherence read of the file's end state: the file as it will stand after all merged changes, read against every rule
   that applies to it — CLAUDE.md hard rules (e.g. `ext/` never edited; legacy tree never worked on; no real
   credentials; UART protocol changes logged Class A/B; `src/` method-assign never suppressed; memory discipline and
   the no-growth rule OR110.a; no test-only artifacts in product code OR36; the 3-line comment cap; docs hold current
   state not history; permanent text cites no temporary audit ID G9/R12; wear gates; hardware only with the owner's
   go-ahead), the owner rows, the register requirements whose Home is this file. A breach becomes a new or changed
   merged change, or an owner question if nothing settles it.

## Output format (`audit/consolidation/M_<CLUSTER>.md`)

```
# A-C merge <CLUSTER> (HEAD <sha>)

## <path>
### M.<CLUSTER>.nnn <imperative title, max 10 words>
- **From**: <constituent A-IDs; dropped ones with the reason>
- **Site**: `<path>:<lines>` <function / section>
- **Change**: <the merged end state; before → after where useful>
- **Resolved**: <each conflict and its settling source, or "—">
- **Unit**: <U-number (and stages if split)>
- **Depends**: <M-IDs / A-IDs this needs first>
- **Blast carried by**: <item → M-ID / A-ID, each>
- **Kind**: code | test | doc | rule | hardware

## Gaps for other clusters
## Adherence findings (per file: rule → result; breaches fixed by M-ID or raised as Qn)
## Owner questions (numbered; a top-level decision in max 10 words, then options each with its consequence)
## Agent decisions for the OR2.c review
## Ledger
| action ID | merged into M-ID / dropped (reason) |
```

Every action of your files gets a ledger row. FINAL REPLY (max 150 words): files done / NOT-DONE, actions merged,
merged changes written, conflicts settled vs raised, gaps for other clusters, adherence breaches found.
