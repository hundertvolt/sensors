# R5 unit BG: the two firmware budgets the final image is over, accounted (lead, 2026-11-11; read-only)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `bg_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Tree: int `S/wt-u35int` at
015dda9f, read only (never write there, never run anything in it). The bench's figures: on
`origin/claude/u35-bench-campaign` (fetch it), `audit/artefacts/evidence/U35_close/redo/hw_round1/HANDBACK.md`, the
sections of 2026-11-11 (d, and the B/C rerun after it) and 2026-11-05; earlier readings in that file's git history and
under `audit/` (filtered). Units ET and TW run beside you (E2/E4/E5; twins): leave those to them.

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"
- On the heap (2026-11-06): "Larger imports and larger built system should not have a significant impact, as they are
  all directly running from flash as frozen modules. Only their actual RAM usage in-operation counts, and that should be
  significatly lower than the numbers you named."

## Your work
1. C stack. `tests_hardware/flash/test_memory_stress.py::test_c_stack_peak_is_within_half_the_limit` holds
   `device_scripts/c_stack_budget.py`'s peak to half of 7,936 B (SPECIFICATION.md near "held to half the limit": agent,
   2026-09-27; owner-reviewed, 2026-10-02). Final image: 4,380 B on chain fram.set_values (leaves i2c1.writeto 2,820,
   i2c0.get_register_bytes 2,620, i2c0.writeto 2,420). 2026-11-05: 4,020 B on fram.get_values_sync. Find: which caller
   reaches set_values at that depth (the await chain plus the sync calls under it), what the measuring wrapper itself
   adds, what in src/ grew it by 360 B since 11-05 (`git log` on int, ':!arduino'), what happens at the limit (the
   stack-check path, reset code 20), and how 11-05's overage was answered (find the record). Then the options: a product
   change that shortens the chain (lines, risk, an image change), or the bound re-derived with this accounting.
2. Heap. `device_scripts/heap_headroom_after_full_system_build.py` `_MAX_USED = 100_000` ("every reading of a fully built
   dev graph is 87,760-87,968 B", 2026-09-19). Final image 103,360 B (control 103,296), free after the build 84,784 B,
   largest block 34,448 B; 5h: after one collect free 82,240-82,288 B, largest block 18-49 KB. Account for the growth
   since 09-19 from git history and the records (which objects the build now keeps that it did not; what MEMDX and the
   11-05 readings found), and say whether any of it is a defect (a survivor that should not survive) or the new features'
   real cost. Then the options as in 1.

## Never
Never edit any tree or branch; never run a test, a probe or a build; git, grep and read-only text tools only. Never read
`arduino/` (`':!arduino'` in every git grep and git log); never view SPECIFICATION.md, CLAUDE.md, BACKLOG.md, README.md,
`devices/`, `audit/` or `src/asy_wifi_service.py` unfiltered. Never open `/root/.claude/`. No hardware, no mpremote.
Scratch only under `S/u35r/r5/ftmp_bg/`. Bound every recursive grep (a path list and `timeout 60`).

## Hand-back
`S/u35r/r5/BUDGETS.md` (at most 50 lines; first line "bg hand-back, written by the agent (<date -u>)"): per budget the
accounting with evidence, defect or real cost, the options with consequences (an image change or not), your
recommendation and confidence. Budget about 1 % of the week. Your last line: "nothing of mine is running".
