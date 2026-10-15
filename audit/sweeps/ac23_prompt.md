# A-C2 (work order) and A-C3 (end-state check) briefs

The 16 cluster merges and the gap pass are done (`audit/consolidation/M_*.md`, `GAPS_G1-G4.md`). 1,865 merged changes
carry 1,545 actions. Read `audit/sweeps/ac_prompt.md` for the change format, `audit/actions/AC_NOTES.md` (all items, 46-50
newest), and `PROJECT_AUDIT_PLAN.md` 3.2 (OR1-OR135; the most recent owner decision wins). A rule that settles a question
means it is not an owner question; owner questions use the owner's format (a top-level decision in max 10 words, then
options and consequences). Accuracy before speed. Never read `arduino/`, never edit `ext/` or any repository file outside
`audit/`, never run anything against real hardware, no git commits (the lead commits).

## A-C2: the work order (one agent; it alone may edit the Unit and Depends slots of M files)

Output: `audit/order/WORK_ORDER.md` (human-readable) and `audit/order/work_order.json` (machine-readable).

1. **Steps.** A merged change can span several units. A step is (change, unit): the part of one change that lands in one
   unit, carrying that unit's actions from its From slot. An action's unit is its ID prefix (`A.U10.x` → U10, `U36a`/`U36b`
   → U36, `A.C.x` → phase C, `A.SDEP.x` → U0's dependency-refresh step plus U37's second check). Supplement actions
   (`A.S0930.x`, the `SUPP_*.md` files) take the unit their supplement text states. The unit sequence is B0, U0 … U37 with
   U8C and U8C2 after U8, then phase C.
2. **Edges.** Action-level dependencies come from `audit/consolidation/site_index.json` (`actions[].depends`). Each merged
   change's Depends slot adds M-ID and A-ID references. Resolve every edge to the step that holds the named action, not to
   every change that carries it. `audit/sweeps/ac_order.py` is a coarse first parser (change level only). Its giant cycle
   comes from resolving A-IDs to whole changes; refine it into a step-level parser rather than trusting that output.
3. **Checks.** Fix each finding, or record why it stands:
   - every edge runs from an earlier step, or a same-unit one;
   - no cycle within a unit; give each unit its in-unit order;
   - the 7 changes with no Unit slot, and the unknown reference `M.SRC_NET.000` in M.TEST_UNIT.286;
   - the change-level cycles M.TWIN.019↔.033 and M.DOCS.008↔.011, which must be settled at step level;
   - the fixed constraints: U0's dependency refresh follows the B0 baseline and precedes every B1 change (LEAD/R33); the
     privatised UART names from U10 onward (AC_NOTES 48).

   A fix edits only Unit or Depends slots and adds a ledger note in the same M file.
4. **Test schedule (LEAD/R34).** For each unit, give:
   - the scoped test files, derived from the Site and Blast files of its steps;
   - the full gate it closes on;
   - which later units are independent of it (no shared site file and no edge), so they can run on parallel worktrees;
   - which hardware rounds it needs.

   Group the hardware rounds into as few owner-approved sessions as the edges allow.
5. **Hand-back:** counts (steps, edges, violations fixed, cycles), the per-unit size, the parallel lanes, and anything
   needing the owner.

## A-C3: the end-state check (read-only on M files; findings go to `audit/consolidation/AC3_<part>.md`)

Each part checks the planned end state, meaning HEAD with every merged change applied. It reports each finding with the
M-ID to amend and the exact amendment text. The lead applies them after A-C2, so A-C3 agents do not edit M files.

- **Part S (Site trace, AC_NOTES 47).** Extract every Site file of every action with a pattern that also catches root files
  (`host_typecheck.ini`, `vitest.config.js`, `.gitignore`, `mockdata/`, `dev_legacy/`, `legacy/`, `audit/`). Also catch
  bare file names that continue a Site list, resolved against the list's directory. Each (action, file) pair must be carried
  by a merged change whose From names the action and whose Site names the file, or be disposed in a ledger with a reason.
  Then run the Blast-pointer sweep once repo-wide (G1-G4 did it per group; this is the cross-check).
- **Part R (requirements).** Each of the 547 register requirements (`audit/pass2/G1-G10.md`, `LEAD.md`, `REF.md`) needs a
  trace from its Req to the merged changes, or the phase-C steps, that deliver it. Its State, Home and unit must agree with
  where those changes land. An untraced or partly traced requirement is a finding.
- **Part O (owner rows and adherence).**
  - Every OR row OR1-OR135 and its .a reading is honoured by the merged end state; none is contradicted by a change.
  - Per repository file the plan touches: the end state obeys every CLAUDE.md rule and the register's rules. Check
    header blocks, the 3-line comment cap, current-state-only docs, no temporary audit IDs in permanent text (G9/R12),
    English logs and comments, the vendored and legacy rules, no new permanent CI control arm (OR21.a (2)), and no
    credentials.
  - Read the six `tests_js` files in full against M.WEB.052-.059 (AC_NOTES 40).
