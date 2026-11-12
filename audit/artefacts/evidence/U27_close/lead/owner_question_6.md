# U27 close: BACKLOG.md owner question 6 (draft)

Where: `BACKLOG.md`, section "## Owner questions", appended after question 5 (the file's last lines at `7f34f35`, `:1152-1160`),
one blank line before it, in the list's own format (bold question, entry date and actor, body, options with their
consequences, effects per device and bus, the default). The entry carries no audit ID (CHECKLIST 5) and no decision
vocabulary word; its only path is `tests_scripts/test_comment_block_cap.py`, present at `7f34f35`. The numbers were measured on
2026-10-15 on the final tree 7f34f35 by the lead (lane U's tree had 675/399 and 116/106). The lead also asks it in the unit-end report; the OF and review rows cite
"BACKLOG.md owner question 6".

Text to append (exactly, between the fences):

```
6. **Count a long comment line as several?** (entered 2026-10-15, agent) CLAUDE.md caps every comment block at 3 prose
   lines, and the check that measures it (`tests_scripts/test_comment_block_cap.py`) counts each comment line once, so a
   paragraph packed onto one long line passes the cap. (a) keep it so: nothing changes, and a long one-line comment stays
   within the cap. (b) count a line as its length over 110 characters, rounded up: 761 comment blocks in 437 files go over
   (measured 2026-10-15) and are rewrapped or shortened before the switch is turned on. (c) the same at 120 characters: 126
   blocks in 116 files. Either way no device's firmware, wiring or bus changes: the check reads source text only, and the
   switch is one constant in that file. Until answered: (a), the current behaviour.
```
