# R5 unit apa: the 19 "attention" values of the estimates table, from what is already measured (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `apa_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/U14_ANSWERS.md`'s Q6
entry, and SPECIFICATION.md Part N in the integration tree `S/wt-u35int` (head `964ee399`): the estimates table with its
Margin column.

## Owner ruling behind this unit
Q6 (2026-11-06 11:03:01 UTC): "fine like this", after the owner's direction (10:59:41): "If they are really useful, I
would agree measuring all of them. But with a clear distinction which of them are pointers to a real issue with
"firmware changing potential" and which of them rather have an "attention" meaning - if they trigger, this means "look
closer" and not "error"." Go for this unit: 13:27:49 UTC, "A, all now".

## Your work (read-only)
The Q6 entry's 19 attention rows: the I2C rungs 2, 3 and 4, the emergency buffer of 100 B, 8 test budgets and 7 CI
values. For each row: the number Part N states, what it estimates, and the value the existing evidence gives. Sources,
in this order: the bench's records on the bench branch (`git -C S/wt-u35int show origin/claude/u35-bench-campaign:<path>`
under `audit/artefacts/evidence/U35_close/redo/hw_round1/`: `HANDBACK.md`, `ROOT_CAUSES_20261105.md`, the logs it
names), then the committed CI timing evidence under `audit/artefacts/evidence/` (the gates' times files) and
`.github/workflows/ci.yml`'s own comments. For each, say whether the stated number holds, the value you would write
(with its source, file and line or run), and where no evidence exists, say "no evidence" and the one measurement that
would give it. Nothing is decided here: the lead folds the values in.

## Never
Never edit any tree. Never read `arduino/`; never open `/root/.claude/`. No hardware, no runs but greps and `git`
reads. Never print, copy or write any Wi-Fi credential or the hotspot fallback password.

## Limits
Write only `S/u35r/r5/ATTN.md` (and scratch under your own `ftmp/`). Budget about 0.4 % of the week. Hand back by
14:45 UTC.

## Hand-back
`S/u35r/r5/ATTN.md`, at most 30 lines: one line per row (Part N key, stated number, evidence value with its source,
holds / adjust / no evidence), and return its path. Last line: "nothing of mine is running".
