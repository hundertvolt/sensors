# R5 unit FS: FRAM's per-command settle pauses go; FRAM rows state the silicon; the docs T's removals made false (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it; the filter rule above all; label `fs_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. FINDINGS
(`S/u35r/findings/FINDINGS.md`) 12.128, 12.162, 12.163. Both PDFs in `datasheets/fram/` (tCSU, tCSH, tD: read the
page, cite it). The bench's figures: `git show origin/claude/u35-bench-campaign:audit/artefacts/evidence/U35_close/
redo/hw_round1/HANDBACK.md`, the FRAMCHUNK and FRAMCMD3 lines only (grep them; never read the file whole).
Code: int `S/wt-u35int` at a5c1dc93 (P9 and T merged). Unit APT may still be finishing in `S/wt-apt` (CI files and
SPEC B.4/B.10.1/Part N apt rows: not yours).

## Owner (verbatim)
- 2026-11-10 11:25:20 (FRAM timing, three options put): "option a" - the measured figures stand, no new mechanism;
  the datasheet-backed removal of the 2 us CS settle pauses rides the image flashed anyway for the last round.
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"

## Your work (worktree `S/wt-fs`, branch `audit/fs` from the int head above; create it; commit locally, never push)
1. `src/asy_fram_driver.py`: the six `sleep_us(CS_SETTLE_US)` in `_send_and_read`/`_send_and_write`/`_send_command`
   and the import go. `src/asy_spi_driver.py`'s two (per operation, `_begin`/`session_end`): judge by the same
   datasheets and the source rule (FRAM is every device's only SPI device): keep or remove, and say which and why.
   No other code line changes; the CS cycle and its bytes stay as they are.
2. Tests and checks that pin a removed sleep follow it (T removed `test_src_sleep_forms.py` and
   `test_timing_budget.py`; grep the rest: `tests/test_asy_fram_manager.py`, `tests/_bus_hazard_catalog.py`, `digital_twin/
   machine.py` if it models one) - only what pins it; a behaviour test stays.
3. SPECIFICATION.md (filtered views only): :272's "blocking 2 us settle"; F.3 `stall.fram_entry` (the 5,000 / 8,000 us
   "acceptance" goes; the snapshot 58 silicon figures in: medians of 30, entry write 12.7 ms, backup write 13.0, entry
   read 10.9, backup read 13.2, maxima as the bench logged them), `stall.fram_command` (~250 us per command, the
   breakdown's figures), `stall.reset_errors` (19 entries at the measured entry time, arithmetic shown),
   `rate.persisted_log` (its "~3.5 ms" basis was a projection: recompute the wear at the measured entry time). Each
   says the settle removal is re-measured on the last round's image. Grep SPEC, `tests_hardware/` and `audit/`-free
   docs for any other 5 / 8 ms acceptance and state the fact there too.
4. The maxima (backup write 21.05 ms, backup read 21.44 ms) sit at `con.routine_stall` (21 ms). The breakdown's own
   maxima (begin 6.1 ms, set_values 6.6 ms against medians of 0.2 / 0.8 ms) point to a collection in the timed
   window. Establish from the code whether the chunk path allocates (then the product's stretch carries the pause)
   or only the probe's loop does; state the F.3 bound check from that, and report plainly if a FRAM stretch can
   exceed `con.routine_stall` on its own.

5. The docs unit T's removals made false: `S/u35r/r5/HANDBACK_T.md`'s "For P9" list (SPEC, CLAUDE.md, README lines:
   fakes/, launch.py gone, the PrintLog report, run() unbounded and the reap in rounds, Run 3's bound gone, the checks
   gone, feed sites one rule, nine lint scopes). State each new fact once; a removed check's pointer goes with it.
   The three tests_scripts failures T left (test_citations, test_level_containment, test_tunables_register) go
   green by fixing the doc lines they read, never by weakening the check. P9's working agreement binds: current
   fact, each rule once, no history.
6. `_record_reads` in the isl29125 test (dead since T): goes.

## Never
Never change a stored FRAM byte, a CS cycle's bytes, a wire byte or a /status byte. Never edit `ext/`; never read
`arduino/` (`':!arduino'` in every git grep and git log); never open `/root/.claude/`; no hardware. No new bound or
mechanism. Credential filter as common_r1 says. Scratch only under `S/u35r/r5/ftmp_fs/`.

## Checks and hand-back
Touched test files at both GC stages; `lint_direct.sh`; three mypy passes; then the gate as common_r1 says
(PICO_TOOLCHAIN_DIR=S/tc-c) under `S/u35/lead/heavy.lock` holding `fs` (wait while it exists; `rm` it, literal path,
its own command). dev `imageFreeBytes` against the int head. One commit; budget about 2 % of the week. Hand back:
`S/u35r/r5/HANDBACK_FS.md` (at most 40 lines: per item what changed, the datasheet pages, item 4's finding, item 5's lines per file), your
commit, one line per headline result, and last "nothing of mine is running".
