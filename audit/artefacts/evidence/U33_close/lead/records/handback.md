U33 close records are committed as `c26db17` "U33 int: the close records" on `audit/u33-int` in `S/wt-u33s`, on top of `0f88c8c`. Not pushed. Nothing is left uncommitted and nothing of mine is running.

The commit holds 4 files under `audit/`, nothing else:
- `audit/sweeps/scan_runs/20261021_U33_close.md` is new. It has the U32 record's sections. All 31 steps are listed by P1's number:
  - 11 applied, each with its commit.
  - 16 landed, with anchors at `0f88c8c`. Steps 12-14 are parked for hardware.
  - 3 check-only (17, 23, 26).
  - Step 30 is held by owner question 6.
  - It also holds R-1..R-24 and L-1..L-7, the scan class by class (documents only), the modes S2 named, and the block counts with the tier-once rule.
  - "## Gates" holds only the `<GATES>` line. "## CI" holds `<CI_U32>` and the sentence sending U33's own run to U34's record.
- `audit/REGISTER.md`: the U33 unit row is set to done, with the record and evidence paths. Six rows follow the last U32 row (`:777-782`): plan and waves, rulings, findings closed or moved, decisions on the owner's behalf, gates `<GATES>`, and CI on U32's squash `<CI_U32>`.
- `audit/sweeps/open_findings.md`:
  - OF-121 closed with no edit (R-19). It cites L.4's sentence "There is no separate `boot_entry/` directory: the boot entries are generated too.", at `SPECIFICATION.md:10506-10507`.
  - OF-226 re-pointed to U35 with the R-5 reason; the silicon run R1 H20 stays parked.
  - OF-230 closed at `629069e` (both CLAUDE.md sentences quoted). It says the sibling sites stay with U36.
  - New OF-234, closed in this commit: B1's 4.7. `audit/actions/C.md` H76 said `wrnno` 11; the code says 54 since `43aced0` (`src/asy_uart_comm.py:146`, `buildgen/error_catalog.json:168`, BACKLOG.md:234).
  - New OF-235, open, to U36: the wozi "never physically flashed" wording at OF-230's sibling sites. These are SPECIFICATION.md L.1 (`:10111-10112`) and `devices/wozi.toml:1`, plus two more sites I found: A.3 `:148-149` and B.11 `:1836`. U36's own carried texts keep the old wording (`audit/actions/U36b.md:437`, `:929`).
- `audit/actions/C.md`: H76 now reads `wrnno` 54 (`UART_DRAIN_BOUND`).

Checks: test_citations, test_decision_vocabulary and test_legacy_paths on the staged head passed (24 passed, exit 0, 22 s). The only warning is the known datasheets one (`test_citations.py:236`). There are no memory markers. Logs are in `S/u33/rec/`.

In `S/u33/close/`:
- `assemble.sh` was run once: 85 files staged in `S/u33/close/evidence`, 620K. It reported one missing file, `S/u33/handbacks/REC_final.md`, which is this hand-back once you save it. Nothing was copied into the tree.
- `evidence_README.md` has the `<GATE>` and `<EVCHECK>` placeholders.
- `squash_msg.txt` has a 93-character subject and no line over 100; no audit IDs in the body.
- `register_rows.py` is the helper I used for the REGISTER edit.

Decisions I took (agent, 2026-10-21):
- **Credential mask:** assemble.sh reads the hotspot default from `devices/*.toml` at run time, and the bench LAN's octet from U32's assemble.sh. Neither value is written anywhere, unlike U32's script, which had the literal. Neither value appeared in any U33 file (0 masked).
- **CI row:** I added a CI row to REGISTER as U32's close has one, though the brief didn't list it. Delete it if unwanted.
- **OF-235's target:** routed to U36, the next unit with a step at those sites, rather than U34, which holds SPECIFICATION.md but has no step there.
- **No row for `PROJECT_AUDIT_PLAN.md`:** B2 noted that `:2667` and `:3293` quote BACKLOG text U33 removed. The plan quotes BACKLOG by line at its own base throughout, and U37 holds the file.

Open for you:
- **Count slip in P1:** P1's step-table total says "landed 15", but its own list adds up to 16. The record uses 16 landed plus 3 check-only.
- **Re-run assemble.sh** after saving this hand-back, so `REC_final.md` and the `S/u33/rec/` logs get staged.