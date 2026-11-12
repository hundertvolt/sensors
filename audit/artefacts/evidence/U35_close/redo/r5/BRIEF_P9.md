# R5 unit P9: the documentation states current fact, each rule once, every credit honest (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all: SPECIFICATION.md, CLAUDE.md and `devices/` are
never viewed unfiltered; label `p9_`). S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/
scratchpad`. FINDINGS (`S/u35r/findings/FINDINGS.md`) 12.111, 12.124-12.126, 12.144, 12.154-12.157;
`S/u35r/r5/CREDIT.md` + `CREDIT_ledger.tsv` (audit-era credits), `CREDIT2.md` + `CREDIT2_ledger.tsv` (the 117
pre-audit-dated credits, each row's new plain form decided), `SIMPLER_1.md` (4), `SIMPLER_4.md` (8), (9), (13).
Code: int `S/wt-u35int` at 81e2ebcd. Unit T writes at the same time and owns `tests/`, `digital_twin/`,
`tests_hardware/`, `tests_scripts/`, `tests_js/`; you own SPECIFICATION.md, CLAUDE.md, README.md, BACKLOG.md,
UART_C_PORT_CHANGELOG.md, DEVICE_REFERENCE.md, THIRD_PARTY_LICENSES.md, `.claude/`, and comment-only credit edits in
`src/`, `buildgen/`, `devices/`, `js/`, `scripts/`. T names SPEC sentences its removals make false; the lead forwards
them to you.

## Owner (verbatim)
- 2026-11-10 06:26:36 (pre-audit credits): "... if there are decisions into a different direction which are clear and
  came in later, the more recent ones sopersede the older ones. So probably you can resolve these items with rule
  based like that." (CREDIT2_ledger is that resolution: apply it, do not re-judge it.)
- 2026-11-10 08:46:45 (FRAM status pair): "i would rather not rely on the "it's written every byte received" but
  rather on CS being deselected. Rather option A)."
- Working agreement (CLAUDE.md): documentation holds current state, targets and rules, not the path that got there.

## Your work (worktree `S/wt-p9`, branch `audit/p9` from 81e2ebcd; create it; commit locally, never push)
1. Credits: every "owner-reviewed, 2026-11-06" suffix left in your files goes ("(agent, date)" stays); every audit-era
   STRETCHED/UNBACKED row of CREDIT_ledger in your files takes its plain form; every CREDIT2_ledger row in your files
   takes its new plain form (DP E05 rows: "(owner, 2026-08-12, as recorded in DP E05)"); UART_C_PORT_CHANGELOG.md:133
   to the one global catalog (OR28). Code files: comment text only - no code line, no bytecode change.
2. SPEC A.4's FRAM protocol paragraph: each status byte is its own WRITE so every byte is committed by a CS deselect
   (owner, 2026-11-10); the 09-18 account's other elements stay; "one 2-byte write would erase that signal" goes.
3. cr2's R0 doc rules (CREDIT2_ledger rule R0, unit P9): the starter-role definition (SPEC ~:4960) and the four rules
   that exist only in the docs (CLAUDE.md English rule, CLAUDE.md "unrelated issue fixed or entered", SPEC one
   declared scope per config value, BACKLOG deferred settings-store goal). Judge each by common_r1's two source rules:
   keep with "(agent, date)" and its need in one clause, or remove; say which and why.
4. One rule, one home (SIMPLER_1 (4), SIMPLER_4 (8)): CLAUDE.md's UART and memory restatements become the rule plus a
   pointer; owner quotes move whole into J.1 / I.4 (actor, qualifier and scope unchanged). SIMPLER_4 (9): README's
   three stale build-chain lines; (13): BACKLOG :26-31; `.claude/skills/work-routines/SKILL.md` :29/:48 if still false.
5. Part N: the about ten legacy-sourced values labelled "estimated" take "legacy" with their source (12.141; `CONSENT_1.md`).
   The HTTP 5 s / 15 s and the DNS rows read as G left them (check, do not re-derive).
6. Premises stated as they stand (12.111): max_connections' "CPU-bound at ~2.2 req/s" premise names its basis (one
   /status build's CPU) and "re-measure owed on the bench"; C.7's "1 s UART cadence through near-continuous chunk
   writing" (09-17) becomes the current fact or "silicon figure owed"; check SPEC:323's twin figure, the twin fidelity
   row and `stall.wlan_switch` - fix only what is still false.
7. SPEC sentences T's hand-back names (the lead forwards them), and anything the G and C merges left contradictory.

## Never
Never change a rule's meaning, an owner quote's words, a number's value or a code line. Never re-judge a CREDIT2 row.
Never edit `ext/`; never read `arduino/` (`':!arduino'` in every git grep and git log); never open `/root/.claude/`; no
hardware. Credential filter as common_r1 says; the hotspot fallback literal is never printed, copied or written.
Scratch only under `S/u35r/r5/ftmp_p9/`. Until `S/u35/lead/heavy.lock` is gone: reading and editing only.

## Checks and hand-back
`tests_scripts/test_comment_block_cap.py` and every tests_scripts test that reads a file you touched (single-process
pytest through the shared venv); `lint_direct.sh`; then, under `S/u35/lead/heavy.lock` holding `p9` (T may hold it:
wait while it exists; `rm` it, literal path, its own command), `uv run pytest tests_scripts` once and, if any `src/`,
`buildgen/` or `devices/` comment moved, `S/u23/rebuild.sh` plus `PICO_TOOLCHAIN_DIR=S/tc-c scripts/test.sh`. Lines
removed and moved per item. One commit; budget about 3 % of the week. Hand back by 14:00 UTC: `S/u35r/r5/HANDBACK_P9.md`
(at most 40 lines: per item what changed, counts), your commit, one line per headline result, and last "nothing of
mine is running".
