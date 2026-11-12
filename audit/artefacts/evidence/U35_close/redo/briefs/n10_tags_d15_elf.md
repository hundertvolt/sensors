# N10: the webserver file's remaining tuned literals, one D.15 reorder, nm's duplicate names (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneN/n10/`.
Sources: N8's hand-back `S/u35r/handbacks_redo/N8.md` ("Unlisted tuned literals", "D.15: partly", its tools in
`S/u35/laneN/n8/tools/`), F4c3's `S/u35r/handbacks_redo/F4c3.md` ("Latent, new"), SPECIFICATION.md N.1 (the classes:
a value waited out in real time is tuned; a value fed only to a fake or used to select a case, never waited out in
real time, is test input) and N.2 (the row form, per-file `(n tags)` counts), D.15 (the reorder rule, topical headings).
Test and tool text only: no `src/`, no generated file, no wear.

## Items
1. tests/test_asy_webserver_service.py: every literal N8 lists under "Unlisted tuned literals" (re-locate each by value
   and context), classed by N.1. Tuned (waited out in real time: per-call timeouts and caps a case can wait out, hang
   bounds, real sleeps and waits, soak cycle counts that set real run time): one module constant per value and role
   in the file's constant block, with its `# @tunable l1.asy_webserver_service_<role>` tag and a Part N row, Basis
   measured as N8 measured (an instrumented scratch copy, both stages, build-standard; slowest observed against the
   bound) or estimated with the measurement owed. Test input: no tag, its class named in your hand-back. Proof as
   N8's: the file's AST identical once each constant is substituted back; 225/225 (or its count) at both stages, zero
   markers; test_tunables_register green and red on a scratch copy with one new tag deleted.
2. A measure, not a fix: the other tests/*.py files' literals waited out in real time and carrying no tag (`timeout_s=`,
   `per_call_timeout_s=`, `outer_cap_s=`, `asyncio.sleep(`, `wait_for(`/`wait_for_ms(` arguments, `run_timed(...,
   timeout_s=)`, a module constant without its tag): a scratch scanner (AST, in your log dir, not committed), the
   count per file and the first sites, and its false-positive classes. The count decides whether more comes.
3. tests/test_ntp_fram_system_integration.py: D.15 for its helpers. First, in its own commit, remove the topical
   headings the role order splits ("Fixtures: ..." near :89-91, "Real UDP NTP round trip ..." near :142-145; D.15:
   a topical heading the role order splits is removed before the reorder, role headings stay); then the pure reorder,
   AST-verified (same statements, non-helpers keep their order, zero D.15 findings by
   tests_scripts/test_code_conventions.py's own logic; N8's tools). 12/12 at both stages after.
4. tests_hardware/harness.py `elf_symbols()`: a name nm lists more than once (two local symbols of one name) is dropped
   rather than silently keeping the last, so a caller asking for it fails on the missing name; its comment says so.
   A tests_scripts test with a canned nm listing (no toolchain run): a duplicated name absent, a unique one present;
   red first on today's code.
5. N9's two harness finds (`S/u35r/handbacks_redo/N9.md`, "For you to decide" and "Harness model mismatch"; the lead
   decided both under CHECKLIST 1d):
   (a) tests_hardware/flash/test_memory_stress.py's soak reads SYSTEM's live log first with no boot wait: without a
   bench the conftest's reset leaves the read landing mid-boot. Make the first read follow a hard reset, the board
   present again and `wait_for_boot()` (reuse the file's or harness's existing boot-timeout constant before adding a
   tagged one with its Part N row). Shown with a TwinBoard-free unit-level check of the call order if one fits the
   existing tests_scripts harness tests; else state why only silicon shows it.
   (b) The harness's retry model: real mpremote prints what it read before "could not enter raw repl"
   (tools/mpremote/mpremote/transport_serial.py, v1.29.0, read-only in `/root/pico-toolchain/micropython`), so
   `run_isolated()` (retry_if_started=False) never retries that transient although its script never started, while
   tests_scripts/test_harness_mpremote_retry.py scripts the case with an empty stdout that never occurs. Make the test
   script mpremote's real output, red first on today's harness, and make the harness tell "never reached the raw REPL"
   from "the script started" by that error's own shape, so a run_isolated() whose raw REPL was never entered is
   retried like exec()'s. A retry must never re-run a script that started: say how the check guarantees it.

## Proof and checks
Each changed MicroPython file at both stages with build-standard directly, zero memory markers, times against N8's
(4.02/6.44 s for the webserver file); ruff, the mypy passes (stubs at `S/shared/typings`), the comment cap,
test_citations, test_decision_vocabulary, test_tunables_register, test_code_conventions, every tests_scripts reader of
a changed file; tests_hardware `--collect-only` only. No scripts/test.sh, no twin CI against the shared toolchain.
Never run mpremote, picotool or a tests_hardware test other than `--collect-only`/`--twin`.

## Not yours
src/, toolchain/, digital_twin/, audit/ records, the NTP rows of Part N, every allow-list (hand back the row you need).
Commit subject `U35 lane N10: <summary>`, the two trailers; do not push. Hand-back: commits; per literal its class and
tag or reason; item 2's counts; the AST comparisons; each red and green with log paths; last line "nothing of mine is
running".
