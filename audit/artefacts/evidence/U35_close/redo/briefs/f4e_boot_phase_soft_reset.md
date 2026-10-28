# F4e: a console soft reset after a boot-phase failure keeps 10 + phase (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Worktree `S/wt-u35f4e`, branch `audit/u35-f4e` at `1ad9cff7` (the
integration head: F4d's swap, merged as a304353e, is in it; generated inputs already rebuilt); logs in
`S/u35/laneR/f4e/`. Facts: F4d's brief `S/u35r/briefs/f4d_soft_reset_record.md`, F4d's hand-back
`S/u35r/handbacks_redo/F4d.md` (its scan's last bullet is this finding), LEAD NOTES 189-190 in `S/u35/lane_plan.md`.
Re-check each fact yourself.

## The owner's words (2026-10-26, verbatim)
The lead's question, "Which one: (a) or (b)?", (b) as first put: "Move the boot-phase check up as well ... in the same
function, the phase check moves to just after the record check. The order becomes: record, phase marker, power-on,
invalid record, otherwise 2. ... a real power-on still reads 1, because both regions are empty. After a normal run the
marker reads "boot done", which is outside the boot range, so the record still decides. ... RAM only, no wear, the same
on every device. ... a unit test seen red first, a twin case, and one more step in the prepared manual bench test."
The owner: "Option b, should be in line with the prior similar decision" (the prior decision is F4d's, question 4).

## The facts
- `begin_boot()` (src/asy_system_service.py:148-170 at 1ad9cff7) decides: valid region-0 record, PWRON (1), torn record
  (0), valid in-boot phase (10 + p, `BOOT_CONSTRUCTION <= p < BOOT_DONE`), else 2. An exception escaping main() during
  boot writes no record (`record_loop_end()` writes only after BOOT_DONE; Ctrl-C always writes 21), so the watchdog reset
  decodes 10 + p. A friendly-REPL Ctrl-D inside the 8 s window after a power-on boot sees cause PWRON and reads 1.
- Power-off and the RUN pin clear both regions (SPEC F.5.4; RP2040 datasheet §4.7.4 and §2.13.1, text at
  `S/ds/rp2040.txt` around :41001 and :12224-12240; the datasheets repo is at /home/user/datasheets, read access granted
  by the owner). So a valid in-boot phase marker under a power-on cause means a soft reset, as the record does.
- The twin harness already models the soft reset: tests/test_digital_twin_loop_end.py `_case(kind, phase, "soft")`.

## What to build
1. The move, nothing more: the order becomes record, in-boot phase, PWRON, torn, else 2. Same on every device, RAM only.
   The existing 2-line comment above the chain is rewritten to cover both (at most 3 lines, pointing to F.5.4).
   A consequence of the approved order, to pin with a unit test and state in your hand-back: a torn record with a valid
   in-boot phase now reads 10 + p under any cause (was 0, or 1 under power-on). Say whether any reachable path can
   produce that state (`_write_region` writes magic last; begin_boot clears magic first).
2. Sweep every consumer that could now read 10 + p where it read 1: a flow that, after a power-on, leaves a valid in-boot
   phase marker (a device script calling `begin_boot()` or building the system without reaching BOOT_DONE, a twin run
   killed during boot whose mem_backup state is kept) and is followed by a soft reset or another `begin_boot()` call
   with no hard reset between. Check `tests_hardware/` (bench/test_reset_reasons.py, every device script listed by
   `grep -rln "begin_boot\|BOOT_CONSTRUCTION\|mem_backup(1)" tests_hardware`, the harness's own flows between scripts:
   mpremote's raw-REPL soft reset, `hard_reset`), the twin (when `run_generic_integration.py` writes the mem_backup
   state file, and which relaunches keep it), `scripts/_digital_twin_ci_suite.py`'s runs, the website and tests_js text
   for codes 10-15. Verdict per site with the source line that decides it.
3. Docs: SPECIFICATION.md F.5.4 (the order, the phase marker under a power-on cause, the decision tag below), A.7/A.8
   and `buildgen/error_catalog.json` where they state what 10-15 mean (F4d's wording for 21 and 22 is the model:
   "the watchdog reset or a console soft reset followed"), tests_hardware/README.md's rows for these codes, the twin
   README's mem_backup row if it states the order. Decision tag: (owner, 2026-10-26: "Option b, should be in line with
   the prior similar decision"; the question, paraphrase: whether a valid in-boot phase marker should also be read
   before the power-on check, so a console soft reset after a failure during boot keeps 10 + phase).

## Proof, each seen red first, both GC stages where it runs on MicroPython, zero memory markers
- Unit (tests/test_asy_system_service.py): a valid in-boot phase under a power-on cause reads 10 + p, for every boot
  phase; a BOOT_DONE marker under a power-on cause with no record reads 1; regions cleared reads 1; the torn-plus-phase
  case above; F4d's tests (:3843-3870) and the existing order tests stay green (if one of them plants an in-boot phase
  and expects 1, say so and why the new reading is right before changing it).
- Twin: `test_a_console_soft_reset_after_a_loop_ended_during_boot_reads_10_plus_its_phase` beside F4d's soft cases
  (`_case("core", _BOOT_SETUP, "soft")`, power-on bits). Bite: F4d's order planted in a scratch copy turns it red with 1.
  F4d widened the file's port band to 20 per device (tests/_port_bands.py); say if one more case still fits.
- Real hardware, prepared, never run, no flash write and no flash cycle: one more step in
  `tests_hardware/manual/manual_persistence.py::test_console_soft_reset_keeps_the_reset_record` (or a sibling, your
  call, said why), on the same power-on boot. It needs a valid in-boot phase marker and no record, then a friendly-REPL
  Ctrl-D inside the watchdog window, and the boot that follows must read 10 + p with power-on ResetBits. Prefer the
  product's own functions over any raw store (for example an isolated script that calls `begin_boot()`, which clears
  the record and marks phase 1, then feeds the static WDT, the way reset_code_invalid_record.py's valid_record_wait
  does) and a new STATE of an existing script over a new script; no FRAM manager (tests_hardware/README.md's FRAM-log
  rule). Verify each step against the pinned source (raw-REPL soft reset skips main.py, main.c:246; friendly Ctrl-D
  re-runs it; the Ctrl-C that mpremote sends writes 21, which the script's `begin_boot()` clears). Run it
  `--collect-only` and `python tests_hardware/manual --list`. If a step cannot be done without wear, stop and hand
  back the options: that is the owner's question.
Checks: ruff, the mypy passes (stubs at `S/shared/typings`), the comment cap, test_citations, test_error_catalog,
test_generated_boot_entry, test_decision_vocabulary, tests/test_asy_system_service.py and every changed file at both
stages, the tests_scripts files that read the changed files. Your base has F4a's `toolchain/`: run test files with the
shared binary directly; no `scripts/test.sh`, no twin CI, nothing pointed at the shared toolchain that could rebuild it.
After src edits run `S/u23/rebuild.sh S/wt-u35f4e`. Three other lanes run: keep CPU use modest (nice 19).

## Not yours
toolchain/, src/asy_ntp_client.py (F5), the files lanes N67 and F4c2 change (tests_scripts/test_tunables_register.py,
test_lint_ceilings.py, test_ruff_exemptions_live.py, SPEC Part N, the flash tier's scripts), audit/ records, every
allow-list (hand back the row you need). Commit subject `U35 lane F4e: <summary>`, the two trailers; do not push.
Hand-back: files and commits, each proof's red and green with log paths, the sweep's sites and verdicts, the torn-plus-
phase reachability, the hardware step and what each part was verified against, anything that surprised you; last line
"nothing of mine is running".
