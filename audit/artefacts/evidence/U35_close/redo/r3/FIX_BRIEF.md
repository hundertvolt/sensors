# R3 fix round, lane M (lead, 2026-11-04, prepared 19:21 UTC; time of sending in the message)

The lead admitted these items (`ACTION_LIST.md` items 11, 12 and 14). Same worktree, branch and rules as
`BRIEF_M.md`; on top of `26705ef8`. Test first: each new or strengthened test is seen red on a planted break (say
which), then green; while fixing, only the changed file runs. Nothing else is added (ACTION_LIST item 3).

## Tests strengthened or restored
1. D1 G1: `tests/test_asy_isl29125_driver.py`'s `test_start_timer_degrades_when_the_alarm_pool_is_exhausted` takes its
   siblings' assertions (`test_asy_bmp3xx_driver.py:2116-2124`, `test_asy_scd30_driver.py:945-953`).
2. D1 G2: `tests/test_digital_twin_hot_replug.py`'s power-cycled BMP3XX test also checks the E slots (the error
   counter unchanged), and the twin chip's registers against the twin model's own reset values (no literal: the
   silicon value is round 1's row 16b).
3. D1 G4: the runner's five behaviour tests from `497b3eda:tests_scripts/test_twin_record.py` (`:23-48`, `:83-138`,
   without `test_every_exception_names_its_reason`), in their smallest form, reading no committed record.
4. D2 G1: the fallback half of the SCD30 twin test `b4341646` removed (edge muted, pin held high, one read within
   `_trigger_half_ticks`, no entry).
5. M G1: in `tests/test_asy_scd30_driver.py`, ContMeas False with the snapshot answered and the stop command NAKed
   answers `Failed` and logs one E CHIP_SET.
6. M G2: in `tests/test_asy_i2c_driver.py`, a runtime `clear()` whose SCL reads low lets a sibling task run before
   it returns `_REC_SCL_HELD` (red on your `r3.i2c.stretch_yield` plant).

## Removed, fixed or recorded
7. D1 G3: `tests/test_voc_algorithm.py`'s `test_the_lowered_uptime_limit_leaves_the_output_unchanged` goes (its
   mechanism, the 16383 limit, went in `1206e862`), with any doc line naming it.
8. D2 G2: the flash tier's loop-lag test into `PERMANENT_SKIPS` with its reason (silicon's run needs the bench
   network, so it is the bench tier's; RESEARCH 7). One entry; no check weakened.
9. D2 G3: `tests_hardware/device_scripts/uart_comm_hazards.py` adds both drivers' `rx_overruns` and
   `discarded_bytes` and each link logger's newest entries to a failing exchange's facts (test side only); run it
   once against the twin.
10. M G3: `listener_close_leaves_the_pcb_pools.py`'s twin half takes a port below the host's ephemeral range (no
    clash with a fixed port elsewhere in the tree); run it ten times back to back against the twin, all green.
11. A10: your fidelity rows 1-5 into `digital_twin/README.md`'s existing table (rows only; the twin corrections
    are the last round's).
12. `src/asy_scd30_driver.py:171`: the citation's `Datasheets/` becomes `datasheets/` (a comment; bytecode equal).

## Then
- Commits on `audit/r3` (a few, by subject), message rules as in common_r1.md.
- R3's gate, once, one step at a time with the host otherwise idle: lint, typecheck, `scripts/test.sh` at both GC
  stages, dev's twin suite and harness at both stages; npm only if `js/` or `tests_js/` changed. Record each step's
  wall clock and its peak RSS (a throwaway `resource.getrusage(RUSAGE_CHILDREN)` wrapper under `m/ftmp/`; there is
  no `/usr/bin/time`).
- Sizes: `S/u35r/r0/module_sizes.sh S/wt-r3 <head> S/u35r/r3/m/sizes_head.tsv`.
- Append "Fix round" to `HANDBACK_M.md`: per item the commit, the red seen, lines added and removed; the gate's lines.
  Final message: five lines and last "nothing of mine is running".
