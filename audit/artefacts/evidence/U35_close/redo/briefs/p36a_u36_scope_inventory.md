# P36a: U36's scope inventory, read-only preparation (lead, 2026-10-27)
The owner allowed preparing the next units while U35 finishes ("preparing the next units is fine"). U36 is the B4 docs
pass (audit/REGISTER.md :62). Its own session starts only on the owner's go after U35 and the hardware session. This
block is preparation only: read, collect, draft. Nothing is decided, changed, committed or asked.

Read first: the repository's CLAUDE.md ("Step-session workflow", "Documentation contains current state...", the
3-line comment cap), then audit/REGISTER.md's header and the U-rows' table, and `S/u35r/d3r_rec2_items.md` (what U35's
own docs block, D3r, already carries).

Source tree: read the integration head through `S/wt-u35int` (read-only: never write, check out, merge or run anything
there; the lead merges into it while you read). Prefer `git -C S/wt-u35int show HEAD:<path>` and `git -C S/wt-u35int
grep -n <pattern> HEAD -- . ':!arduino'`.

## Items
1. Every item staged to U36 anywhere under audit/: REGISTER.md rows naming U36, audit/sweeps/open_findings.md rows
   whose unit is U36, action and plan entries (A.U36.*, M.* steps with a U36 part, the order/ and refined/ files),
   and lines elsewhere in audit/ that stage work "to U36" or "U36's". One row each:
   - its id;
   - its source path:line;
   - the doc or file it touches;
   - what it asks, in one line;
   - its state on the head: done, partly done or open, with the line that shows it.
2. Cross-check against `S/u35r/d3r_rec2_items.md`. For each pair, say whether the D3r item and the U36 item overlap,
   and how, so the same text is not written twice. Never move an item between units: that is the owner's and the
   lead's call.
3. Group the open items by document: SPECIFICATION Parts, README, BACKLOG, digital_twin/README, tests_hardware/README,
   DEVICE_REFERENCE, CLAUDE.md, and others. Count each group, and name any group whose items conflict with each other
   or with the head.
4. Draft up to 10 clarifying questions that the inventory shows U36's session would have to raise, per CLAUDE.md's
   step (2): each with its facts, its options and their consequences, and a recommendation, in prose. They are a
   draft for the lead. They are never sent to the owner from this block.

## Output
- `S/u36prep/inventory.tsv` (item 1's rows), `S/u36prep/scope_draft.md` (items 2-4, a short goal and done-criteria
  section per CLAUDE.md's step (1)), each in your own words. Never copy source or doc text beyond a short quoted
  phrase that locates a line.
- No repo edits, no commits, no test or build runs. Never read arduino/, never open anything under /root/.claude/, no
  model identifiers anywhere. Shell: read-only commands only; file writes with the Write or Edit tool, under S/u36prep/.
- Count your tool calls. At 80, write what you have, mark the rest open, and hand back.
- Hand-back:
  - the row counts by source and by state;
  - the groups and their counts;
  - the overlaps with D3r;
  - the draft questions' titles;
  - anything on the head that contradicts an audit record (a finding for the lead, not a fix);
  - last line "nothing of mine is running".
