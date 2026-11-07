# Read-only sweep: tier parity and wrongly trusted hazards, task graph and system service (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md`'s rules (binding; labels `swp_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then, in the integration tree
`S/wt-u35int` (read-only for you): BACKLOG.md:29-44 (the sweep, and the one domain it never covered) and
`tests_hardware/README.md`'s section "Tier parity beyond the bus hazards" (how the first run worked and what it found).
The owner chose this sweep (2026-11-06 06:13 UTC: "B").

## The domain
How the generated `sensortask_<device>` task graph works with `src/system_service.py`: task start-up and the setup
lists, the task supervisor and restarts, timers and the sequencer, the watchdog feed, shutdown and reset steps, and
the error-count and reset-reason paths they write — beyond what the FRAM/memory pass already covered (that section
names it).

## The lens (the same as the first run)
1. **Tier parity:** for each behaviour of the domain that a test pins, which of the four tiers (mock `tests/`, twin,
   flash, bench) test it, and is a missing tier a real gap, a structural exception already recorded (SPECIFICATION.md
   E.6.6), or not applicable.
2. **Wrongly trusted hazards:** a test that passes because a real trigger was replaced by a software-only one, or
   because a fake does what the real part never does (or never does what it does), so the hazard is believed covered
   when it is not. Trace the real call chain end to end; never count greps.

## Output
Per finding: what, the evidence (file:line on both sides), its class (gap / recorded exception / wrongly trusted), and
the smallest fix (one test, one fake corrected, or one E.6.6 row), or "needs hardware" / "needs an owner decision". Then
one line: whether the BACKLOG item can come out.

## Limits
Read-only: write only `S/u35r/r5/SWEEP.md`. No runs but greps and `git` reads. Never read `arduino/`; never open
`/root/.claude/`. Budget about 0.5 % of the week.

## Hand-back
`S/u35r/r5/SWEEP.md`, at most 50 lines, and return its path. Last line: "nothing of mine is running".
