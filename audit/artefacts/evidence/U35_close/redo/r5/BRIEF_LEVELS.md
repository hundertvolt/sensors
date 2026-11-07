# R5 unit levels: did other agreements miss the same way? Three read-only passes (lead, 2026-11-07)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `levels1_`, `levels2_`, `levels3_` by pass). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/findings/FINDINGS.md`
12.96-12.101 (the mechanism), `S/u35r/r5/DESIGN_FU.md` (its scope is done - the FRAM, CRC, logging and UART parts, the
SGP40 backup, and the sweep of FRAM writes and locks held across yields over `src/`: do not redo it), SPECIFICATION.md
Part 0 (the principles), PROJECT_AUDIT_PLAN.md:373 (OR51, the owner's design questions). Code: `S/wt-u35int` (18e9d59c).

## Owner rulings behind this unit (2026-11-07, verbatim)
- 17:21:06: "I wonder if the same happened to other agreements as well. The agreements apply on function, module,
  import, integration and upstream and downstream, and full system - the specs (not just that one statement, in
  general!) apply to micro, medium and macro level!"
- 17:31:00: "Yes, [...] This, as well as all necessary scans and checks, can start immediately and run through."

## What to look for (FINDINGS 12.100)
(a) An agreement checked one file at a time while the cost lives in a combination; (b) a ruling made on the isolated
case whose premise fails in combination, under load or system-wide, and that then shielded the code; (c) a measurement
of the harmless case (idle, smallest input, Unix port) standing for the worst case, or a budget naming the wrong waiters.
The lens at every level (function, module, import, integration upstream and downstream, full system): OR51's design
questions, answered by one number per operation - its physical need against its worst-case cost, and who waits meanwhile.

## The three passes (one agent each)
1. Rulings that keep or accept a cost: SPECIFICATION.md's owner-cited statements that keep, accept or leave something
   (`grep -n -i -E '\(owner, 20' SPECIFICATION.md | grep -i -E "accept|keep|kept|stays|don.t touch|tolerat|leave|as it
   is"`, about 79) and PROJECT_AUDIT_PLAN.md's OR rows of that kind. Per ruling: what it keeps, the facts it rested on
   (its text and the commit that recorded it), and whether each holds at every level today. Output: the rulings whose
   premise fails, ranked, each with the new facts; they go back to the owner.
2. Budgets and measurements: SPECIFICATION.md F.3's budget rows (`con.`, `feed.`, `stall.`, `hold.`, `lag.`; 37) and
   Part N's rows. Per row: the condition behind its value (idle or loaded, which case, silicon or Unix port), whether
   that is the worst case, and whether its named consumers or waiters are the real ones in the code. Output: the rows
   that fail, ranked, each with the right condition or consumers.
3. The code outside DESIGN_FU's parts: every `src/` module except `asy_crc_checks`, `asy_fram_manager`,
   `asy_fram_driver`, `asy_print_log`, `asy_uart_comm` and `asy_uart_driver` (`asy_sgp40_driver` except its backup),
   plus the generated `sensortask_wozi.py` under `build/generated_src/` if present. Per module its function in one
   line, then the lens at each level. Output: findings with a concrete leaner form that loses nothing, ranked.

## Rules for every pass
Read-only: never edit a tree. Every finding carries evidence (file:line, commit, measurement), C (confirmed) or I
(inferred), and its origin (original 2026-07-13 / pre-audit / audit 10-06 to 10-28 / post-restart). No hypothesis is
a finding. Prefer removal; propose no new mechanism where removal or a simpler form holds. Read `devices/*.toml` and
generated modules filtered (common_r1). Never read `arduino/`; never open `/root/.claude/`; no hardware; never print,
copy or write any Wi-Fi credential or the hotspot fallback password.

## Limits and hand-back
Write only `S/u35r/r5/LEVELS_<pass>.md` (at most 60 lines) and scratch under `S/u35r/r5/ftmp_levels<pass>/`. Budget
about 1 % of the week each. Hand back by 21:30 UTC: its path, one line per headline result, and last "nothing of mine
is running".
