# R5 unit bfix: the FRAM hold fixed at its source, the UART independent of FRAM timing (lead, 2026-11-07)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `bfix_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then `S/u35r/r5/DESIGN_FU.md` (the
design: item 4's (ii), (i) and docs; item 5's trims), `S/u35r/findings/FINDINGS.md` 12.96-12.101, and the owner's
entries from 2026-11-07 16:45:25 on in `S/u35r/recovered/owner_rulings_after_LN118.md`. The candidate for (i):
`git -C S/wt-uartq diff` (uncommitted, on 2f6d1453; int 18e9d59c differs from it only outside `src/` and `tests/`).

## Owner rulings behind this unit (verbatim)
- 16:45:25: "... only option B stays - what would any setting of FRAM or UART ever have cross dependencies? ..."
- 16:47:31: "Especially keep in mind: all gaps closed, (really) agreed on features implemented, and from there on minimal,
  efficient and lean changes."
- 17:31:00: "Probably applying this this already answers the open questions about the checksum from, and respecting,
  multiple points of view. These findings are fundamental. They must flow into and be applied to the general specs, as
  well as the consequences about the ruling. This, as well as all necessary scans and checks, can start immediately and
  run through."

## Your work (worktree `S/wt-bfix`, branch `audit/bfix` from int `18e9d59c`; create it; commit locally, never push)
1. (ii) in `src/asy_fram_manager.py`, by removal, as DESIGN_FU item 4 says: the CRC once per write, outside every FRAM
   lock; a read releases the lock before its check; a compare reads the other block and compares with `==`, the CRC only
   on a mismatch; `check_length`, the slice machinery and their state go. The compare's buffer: reuse one that exists if
   it fits, else one transient per compare (boot reads and the verify cadence only), never per log entry. Stored chunks
   stay readable (T3).
2. (i): apply the candidate (`git -C S/wt-uartq diff | git apply`), then its trims: the writer's coroutine and task
   allocation never makes a logging call raise (a `MemoryError` there leaves the entry in RAM; the next call writes
   it); `_err` stays a coroutine that no longer awaits FRAM, so its call sites stay as they are. The UART only.
3. The CRC's per-byte yield: leave `src/asy_crc_checks.py` as it is until the lead messages you the chip's figure
   (bench, tonight). The rule then (owner 17:31, every level): the yield's purpose stays (no CRC stalls other tasks past
   `con.routine_stall`); its per-byte granularity goes. If 264 x the measured per-byte stretch is under that bound, the
   yield goes (2 lines); otherwise one yield per 64 bytes. The lead sends figure and form; tests for either then.
4. Tests first, seen red on `18e9d59c` where they pin a change (DESIGN_FU's T1-T3 and its UART tests): rounds held per
   block operation at most 2 and equal for an 8-byte and a 264-byte chunk; an `err_s()` started during a 264-byte write
   plus verify completes within a fixed round count; a golden chunk image from today's code reads back valid and a new
   write is byte-identical; a declined SET and a fault each resync on time while the store's chunk write is held shut;
   an `err_q()` whose task creation raises `MemoryError` returns and the next entry writes. The mock and twin
   bus-hazard tiers get T2's shape. Rounds, never wall-clock checks.
5. Docs, current state: F.3's `hold.fram_block` row with its real consumers (every FRAM-backed logger, the SGP40
   backup, the supervisor through SYSTEM) and the new hold; the driver's "a second SPI device" comment says who waits;
   C.7.1 (the two logging forms; the UART uses the `_q` form); Part G's logging row; Part J's recovery (the receiver
   resyncs without waiting on its log write; an entry logged just before a reset may not reach FRAM). The rulings'
   consequences: the CRC paragraph that quotes "pure wall clock time" (Part I) and `hold.fram_block`'s 2026-09-26 "keep"
   each name the fact they rested on that did not hold (both run under a lock every FRAM user waits on; both measured
   idle on the smallest case) and the rule now in force (owner, 2026-11-07). `UART_C_PORT_CHANGELOG.md`: one Class B entry.
6. Unit specfund edits SPECIFICATION.md Parts 0, D and K and CLAUDE.md at the same time: touch none of those.

## Never
No hardware. Never read `arduino/`; never edit `ext/`; never open `/root/.claude/`. No `gc.collect()`, no new delay, no
per-frame or per-entry allocation in the steady state. Read `devices/*.toml` and generated modules filtered (common_r1).
Never print, copy or write any Wi-Fi credential or the hotspot fallback password.

## Checks
Each touched test file at both GC stages while fixing; `lint_direct.sh`; the three mypy passes; then the gate as
common_r1 says, under `S/u35/lead/heavy.lock` holding the line `bfix` (wait while it exists; `rm` it, literal path,
its own command, after). Report the frozen size and `imageFreeBytes` against 18e9d59c.

## Limits
Write only the files above and their tests. One commit, plus one small one for item 3 if its figure arrives after the
gate (then that commit's touched tests at both GC stages). Budget about 2 % of the week. Hand back by 23:00 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_BFIX.md`, at most 30 lines, as common_r1 says; plus the module sizes, `imageFreeBytes`, and the
lines added and removed in `src/`.
