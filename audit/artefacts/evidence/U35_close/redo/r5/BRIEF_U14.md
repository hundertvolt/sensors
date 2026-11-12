# Read-only precompilation: the agents' decisions as at most 20 big-picture owner questions (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md`'s rules (binding; labels `u14_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. The integration tree is
`S/wt-u35int` (read-only for you).

## The owner's direction (2026-11-06 06:53 UTC, verbatim)
"Option B, but with precompilation. Single decision is by far to fine grained, that's micro management. Group such
decisions into topics and realms, get a big picture which is the result of all contained decisions, and put that high
level big picture into the questions. Do you get that covered with 20 final top level, well human understandable
questions?"

## The material
Every line outside `audit/` carrying a decision taken on the owner's behalf: `git grep -n "(agent, 20" -- ':!audit'
':!arduino' ':!legacy' ':!python'` (466 lines today; SPECIFICATION.md alone 266), and the 20 "owner-reviewed" ones
for reference. Read each in its context (the paragraph or code around it), not the line alone. What the owner has
already ruled is decided and never asked again: `S/u35r/recovered/owner_rulings_after_LN118.md` and every "(owner,
date)" in the tree.

## Your work
1. **Sort each line** into one of two kinds:
   - **choice:** an agent picked between real alternatives with behaviour, product, test or process consequence;
   - **record:** no real alternative existed: a datasheet or source fact, the direct consequence of an owner ruling,
     or wording only. Name the citation that should replace its tag (the datasheet table, the source line, or the
     owner ruling it follows).
2. **Group the choices into realms** (for example memory, recovery and the watchdog, logging and error codes, UART,
   each sensor, storage, the web and REST layer, the twin, tests and tiers, the build chain, docs and process; use
   what the material shows, not this list). Per realm write the **big picture**: what the system does, or how the
   project works, as the result of all its choices together, in plain words a non-developer owner understands.
3. **One question per realm, at most 20 in all** (merge realms to stay within 20). Each question, in prose: the big
   picture; the few choices inside it that carry the most weight (one line each); where a different ruling would
   change something real, the realistic alternative and its consequence; a recommendation (accept as is, or the
   change). No question asks about a single line. A realm whose choices all carry little weight is folded into one
   last question: "accept the rest as they stand".

## Output (write only these two files)
- `S/u35r/r5/U14_QUESTIONS.md`, at most 200 lines: the realm map (realm, number of choice lines, number of record
  lines), then the questions in the order you would ask them, each self-contained.
- `S/u35r/r5/U14_TAGS.tsv`: one row per tagged line: `file:line`, kind (choice/record), realm, and for a record its
  replacing citation.

## Limits
Read-only otherwise: no runs but greps and `git` reads; never edit the tree. Never read `arduino/`; never open
`/root/.claude/`. Budget about 1 % of the week; at 80 % of it stop and report what is done.

## Hand-back
Return the path of `U14_QUESTIONS.md` and three lines: the counts (choice, record), the number of questions, and
anything that would not fit the 20. Last line: "nothing of mine is running".
