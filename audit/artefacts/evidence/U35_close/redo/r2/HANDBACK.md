R2 hand-back, written by the agent (Wed Nov  4 13:38:56 UTC 2026)

Worktree `S/wt-r2`, branch `audit/r2` from 8a32d826, ten commits, never pushed. Brief: `S/u35r/r2/BRIEF_B.md`.

## Commits (oldest first)

| commit | subject (after `U35: `) |
|---|---|
| f6593d6a | a loop end resets the chip at once, so rp2's REPL never starts |
| 95064ed3 | build chain carries: the UART buffer citations, HardConsumer's unread fields, every settings page checked |
| 95e4fbde | three convention gates and the checks' self-bite tests go |
| b315f98b | twin and fake knobs that only their own tests read go |
| d0eb67f3 | the shared twin tells its own background by its event, and the launcher stop file goes |
| 06371ab1 | the seven sleep-then-assert tests wait for their condition |
| 32a24907 | each L2 scenario runs once per device and GC stage; the twin CI matrix has 12 jobs |
| fb447c7e | Part N registers firmware, build and suite-level values; a single test's own waits are plain literals |
| 7ebdea6a | gate fix: the boot entry's first import names reset, and seven untagged test constants cite their own origin |
| 433d53b2 | the twin CI job's timeout row records the exclusive-port-53 scenario each leg now runs |

06371ab1 and 32a24907 were rebuilt with `git commit-tree` (same trees, same dates) before the gate, because their
first messages cited an audit ID and a lane's run; fb447c7e was amended once to drop a `node_modules` symlink `git add
-A` had staged (`.gitignore`'s `node_modules/` matches a directory, not a link). No final commit holds either.

## Item by item

1. **Removals.**
   - A1-A3 done (95e4fbde): `tests_scripts/test_hardware_clones.py`, `test_host_annotations.py`,
     `test_host_text_encoding.py`. A2 only after ruff 0.16.10 reported TC004 on a planted file evaluating a
     `TYPE_CHECKING` name at run time (`ftmp/tc004_plant.py`, deleted). Their readers were updated:
     `tests_hardware/README.md:560` (the clone rule is now held by review), `BACKLOG.md` 801/817/987, SPEC's old 11188.
   - The 48 self-bite functions (appendix S) in 23 files, with the helpers only they used and the F401s they left in
     `test_timing_budget.py` (95e4fbde). Each check's real case stays.
   - N-knob-1..5 done (b315f98b): `_bmp3xx_chip.py` `fatal_err` and EVENT, `_scd30_chip.py` `rdy_stuck_high`, the twin
     pixel's `power_dip()`/`displayed()`, `tests/_fram_chip_fake.py`'s `silent`, and their self-tests. `silent`
     re-read first: its one reader was the fake's own test in `test_asy_system_service.py` (that assert now `(4, 3)`).
     The twin pixel's `raise_on_write` is not N-knob material: it predates the audit (25caf528) and a product test
     reads it, so it stays with its test.
   - W1-W5 done (d0eb67f3): the shared twin's 89 s retirement, its 30 s budget and the deadline failure gave way to the
     idle event (the boot's own SGP40 W35 backup, `_own_backup`, a `newest` field); the launcher stop file, its DIAG
     fallback and refusal, the suite's "never acted on its stop file" check and the run-12 interrupt case went;
     `shutdown()` ends by SIGINT with a 15 s timeout. Two Part N rows went with it.
   - **O-lock-1..5 not done: to the lead.** Dropping the CPython and JS locks needs a new npm-side wrapper around
     `scripts/_port_lock.sh` (a new mechanism, which BRIEF_B's bounds send to the lead), and dropping
     `scripts/_port_lock.py` breaks the documented direct run of `scripts/_digital_twin_ci_suite.py`
     (`README.md:675`, `digital_twin/README.md:670`), which then takes no lock at all.
   - The rig override: records only, nothing in code (no such override is in the tree).
2. **The seven fixed sleeps** (06371ab1): each waits for its condition through `tests/_twin_readiness.wait_for_value()`
   or the file's own waiter, bounded at 1 s; where the holder can release before a 10 ms poll (the 5 ms hold, a short
   transfer) one scheduler turn plus the assert is the wait. `run_generic_integration`'s loop-lag probe keeps a 5 ms
   lead (`_PROBE_LEAD_MS`): with one turn the lag test read 14,435 µs against its 15,000 µs floor at 32768. Seven Part
   N rows went.
3. **CI.** C1 option (b) (32a24907): the exclusive-port-53 mode runs only the scenarios needing it (one today), the
   rest deselected by name; the twin job runs suite and that scenario in one leg; the matrix is device x GC stage.
   Jobs: 46 before (CI run 41512927022), 34 after (twin 24 -> 12); every device and both stages kept.
   Timeouts: every value kept. `unit-tests`/`unit-tests-gc-threshold` (175) rest on `runner.scenarios_timeout_s`
   (2555 s), whose need is the bench Pi4's in-suite scenario time, unmeasured: the three rows say "measure on the
   bench". `digital-twin-e2e` (20) re-derived for the merged leg (433d53b2): the exclusive scenario took 54.5 s and
   54.6 s at -1 and 32768 here, so 1.54x the warmer leg, that scenario and the 2-minute wait. Both retries stay; the
   hang backstop is untouched.
4. **Part N** (fb447c7e), the narrow reading: 192 rows stay (188 ID rows, 4 rule rows): firmware 107, build 23, L0 3,
   L1 3, L2 6, L3/L4 12, CI 21, runners 13. 1,077 rows went in this commit (5 of them rule rows: the UART floors,
   whose formulas J.6 states, and the two loop rules, which F.3's `stall.sync_wait`/`stall.uart_call` rows carry with
   their checking tests), 9 more earlier (the seven sleeps, W1). Tag lines: 1,386 before, 258 in 79 files after;
   every literal stays. The intro states the scope with the owner's words. Prose naming a removed row now states the
   value or the relation: about 70 SPEC lines, `BACKLOG.md`, both READMEs, three code comments and
   `tests_scripts/test_src_sleep_forms.py`'s docstring; `test_retry_counts.py`'s table dropped 13 untagged IDs.
   - Heap-floor row `l3.heap_headroom_after_full_system_build_max_used`: Basis the owner's decision of 2026-10-02
     (review `heap-floors-kept`), Margin "none: the bound is the requirement".
   - `mem.max_await_depth`: one host run (`r2_depth`, 5 s, `ftmp/depth.py`, deleted) of `_await_depth.py` over all six
     devices: 25 levels, 47 chains, the longest a `GET /status` through Microdot's dispatch and a config store's
     FRAM-backed log write to the FRAM driver's own log. Tag, literal and row now 25 (was 28, the removed lost-chip
     chain); F.1's sentence follows.
5. **The loop end** (f6593d6a): the generated boot entry imports `reset` and calls it right after `record_loop_end()`
   in the `BaseException` arm; the Ctrl-C arm and the no-autostart entry are unchanged.
   `tests/test_generated_boot_entry.py` seen red (4/5) then green (5/5, both stages); the twin loop-end test accepts
   the simulated reset and reads the FORCED bit, its two console-soft-reset-after-a-loop-end cases gone; catalog row 22, A.7, F.5.4 and `tests_hardware/README.md` follow,
   citing `ports/rp2/modmachine.c:74-79` and SPEC F.5.4. Missed at commit time and caught by the gate:
   `tests/test_reset_call_site_invariant.py` expected the entry's first statement to be `from machine import WDT`;
   7ebdea6a makes it `from machine import WDT, reset` and its docstring names that one reset outside `_reboot()`.
6. **Carries** (95064ed3): `_UART_BUFFER_MIN`/`_MAX` cite `ports/rp2/machine_uart.c:68-69, :372-375, :387-390`
   (v1.29.0); `SETTINGS_GROUPS` and `_owns_config_store()` stay, since readers exist (`codegen.py`, `generate.py`), and
   the settings test now checks every emitted page against the table; `HardConsumer` keeps `.ms` only. P-sleep: no
   change. Not in BRIEF_B and not done: LIST section 6's other "phase B" carries (the twin erase cut points in
   `flash/test_system_commands.py`, `--only` and the missing `ss` in `run_digital_twin_ci.sh` (the gate printed
   `ss: command not found` again), `manual_persistence.py`'s ResetBits read, the bench W65 expectations, the held-SDA
   twin exception, the per-file heap probe).

## Where the removed items' knowledge lives

- A1: the "no hardware clone" rule is `tests_hardware/README.md`'s table row, held by review. A2:
  `requires-python >= 3.11` and ruff TC004 under `select = ["ALL"]`. A3: `test_buildgen_locale.py` builds under a
  non-UTF-8 locale, and the chroot recipe sets `LANG=C.UTF-8`.
- Self-bites: each check's real case; a check that stops biting is a review matter (no permanent control arms in CI).
- N-knobs: the product's handling of those faults stays covered by the unit fakes; the twin models no test-only knob.
- W1-W5: the boot's own background is told by its event, not by its age; a twin that ignores SIGINT fails the
  shutdown check's 15 s.
- Part N's removed rows: each literal stays at its site, its relation stated where a firmware row needs it.

## Phase-A count correction

LIST 5.1 counted the register as 1,278 ID rows plus 9 rule rows, with Runners at 22. Runners holds 13; the 9 rule rows
were counted in it, so the register held 1,269 ID rows and 9 rule rows. In scope: 188 + 4 = 192, not 197 + 4; out:
1,081 + 5, as LIST said.

## Gate (labels `r2_gate_*`, `r2_gate2_*`, logs in `S/u35/lead/`)

| step | first pass | after the fix round |
|---|---|---|
| `scripts/test.sh` (gc -1) | FAIL, 698 s: `test_reset_call_site_invariant.py` 1 of 3; `test_tests_hardware_product_copies.py` (7 constants whose exempting tag went) | PASS, 695 s: files 137 passed, 0 failed, 80 skipped, 6 deselected; tests 5,824; tests_scripts 6,785 |
| `GC_THRESHOLD=32768 scripts/test.sh` | FAIL, 726 s: every test passed (5,824 and 6,785), but my fix edits landed mid-run and the checkout guard named the 8 paths | PASS, 725 s: files 137 passed, 0 failed, 80 skipped, 6 deselected; tests 5,824; tests_scripts 6,785 |
| twin suite dev -1 | PASS, 598 s (329 + 15 checks) | not rerun (the fix touched neither twin nor product) |
| twin harness dev -1 | PASS, 57 s (1 passed, 1 skipped, 65 deselected) | not rerun |
| twin suite dev 32768 | PASS, 616 s (329 + 15 checks) | not rerun |
| twin harness dev 32768 | PASS, 57 s (1 passed, 1 skipped, 65 deselected) | not rerun |
| npm lint, typecheck, test:unit | PASS, 207 s (1,272 tests, 26 files) | not rerun |

Before the gate: lint (`lint_direct.sh` after `rebuild.sh`) clean; the six mypy passes clean.

## Sizes

SPECIFICATION.md: 1,589,923 B / 13,230 lines at 8a32d826, 1,128,895 B / 12,143 lines at 433d53b2.

Lines against 8a32d826 (`git diff --numstat`, arduino excluded): 332 added, 3,745 removed.

| path | added | removed | net |
|---|---|---|---|
| `tests_scripts/` | 30 | 1,127 | -1,097 |
| `tests_hardware/` | 34 | 592 | -558 |
| `tests/` | 72 | 575 | -503 |
| `scripts/` | 47 | 133 | -86 |
| `digital_twin/` | 21 | 61 | -40 |
| `tests_js/` | 0 | 20 | -20 |
| `devices/` | 0 | 12 | -12 |
| `src/` (comment lines only) | 1 | 9 | -8 |
| `buildgen/` | 8 | 10 | -2 |
| `.github/` | 4 | 6 | -2 |
| `SPECIFICATION.md` | 102 | 1,189 | -1,087 |
| `BACKLOG.md` | 9 | 8 | +1 |
| `README.md` | 4 | 3 | +1 |

Nothing grew but two doc files by one line each (BACKLOG's chroot-list entry, README's twin-runner paragraph).

## Decisions (agent, 2026-11-04)

- O-lock-1..5 go to the lead (above).
- The await-depth tripwire follows the measurement down to 25 ("a stale value is corrected with the measurement behind
  it", N.1).
- The five removed rule rows' content stays where it already was (J.6, F.3); only the pointers went.
- Seven hardware-tier constants that share a number and a word with a product field carry a `# source:` comment
  naming their own origin, the product-copy check's existing exemption, rather than a new one.
- The twin and npm steps were not rerun after the fix round: the fix touched only a unit-tier test and comments in
  `tests_hardware/`, and the twin row edit is SPEC text, which the rerun `test.sh` stages check.

## Slips against common_r1.md

- One early phase-B test run went directly instead of through `run.sh`.
- The two commit messages above, reworded before the gate.
- Gate fix edits made while the 32768 stage ran (its checkout-guard failure); the stage was rerun.

## Fix round

R2 fix round, written by the agent (Wed Nov  4 15:41:24 UTC 2026). Brief: `S/u35r/r2/FIX_BRIEF.md`, answering `S/u35r/r2/FALSIFY.md`
(verdicts: `ACTION_LIST.md` item 4). Branch `audit/r2` on top of 433d53b2, seven commits, never pushed; labels `r2x_`.

| commit | subject (after `U35: `) |
|---|---|
| b930a5be | the idle check excuses the boot's W35 only when the SGP40 count moved by exactly one |
| d974aa9d | the captive DNS tests wait for the server's socket to be bound, not merely created |
| 14ed9e5e | the BMP3xx twin's EVENT register is back: por_detected after power-up and soft reset, clear-on-read |
| a87b8214 | after a loop end no REPL starts, so a console soft reset reports only the Ctrl-C arm's 21 |
| 41d2ba96 | the bench loop-end test reads the 22 at once, with no drop-off wait an immediate reset could slip past |
| 20b691bf | stale text after the loop-end reset and the bite tests' removal |
| 17688315 | the bench loop-end test parses its script's phase fact again, a lost one no failure |

### Per fix

- **F1** (a87b8214): F.5.4 now says a Ctrl-D at the REPL follows only the Ctrl-C arm and reports its 21, and that a
  loop end's 22, or the 10 + p of a loop that ended during boot, is read after the entry's forced reset; A.7 already
  said the same (unchanged). `tests/test_asy_system_service.py`: the first soft-reset test keeps only the 21 case. The
  boot-phase one is gone, because `test_a_loop_ended_during_boot_writes_nothing_so_the_next_boot_reads_its_phase`
  (same file) already reads 10 + p after a reset, and the twin's `test_a_loop_ended_during_boot_reads_10_plus_its_phase`
  reads it after the forced one. File 186/186 (`r2x_f1`).
- **F2** (b930a5be): `_own_backup()` takes the move and excuses an SGP40 move only when the count went up by exactly
  one, with a missing count before read as 0. The falsifier's planted case is now a test
  (`test_the_boots_backup_beside_an_unstated_repeat_of_the_newest_code_is_still_named`): scenario a states SGP40's
  E110, and b states nothing but repeats E110 in place while the boot's W35 lands (count 1 -> 3). Before the fix it
  failed with `[[], []]`, both releases clean (`r2x_f2red`, `r2x_f2red2`). After the fix b is named with
  `'SGP40': (1, 3, ...)`, and the file passes 108/108 (`r2x_f2green`).
- **F3** (d974aa9d): the four waits in `tests/test_asy_captive_dns.py` read `server._udps.connected`. Held-port plants,
  each removed with `git checkout` afterwards:
  - `r2x_dns_bind`: a socket bound to the server's port without SO_REUSEADDR. The wait returned False after 1,001 ms
    with `connected` False: `R2X (False, False, 1001)`, against the 1,000 ms bound.
  - `r2x_dns_bind2`: the same blocker in front of
    `test_run_reuses_same_dns_server_instance_across_multiple_hotspot_cycles`, which now fails (66/67).
- **F4** (14ed9e5e): `_REGISTER_EVENT`, `_EVENT_POR_DETECTED` and the power-up, soft-reset and clear-on-read model are
  restored exactly as at 8a32d826, with the EVENT self-test and the two power-cycle reads. Against 8a32d826 only the
  `fatal_err` knob and its test differ. The twin side of the conformance probe (`conformance.run_probe_on_twin`, a
  throwaway script, deleted) reads `C03_por_after_softreset` '1' and `C04_por_after_second_read` '0' at both GC stages
  (`r2x_bmp_twin`); the falsifier's head run read '0'. The probe's `build/twin_board/` and `build/device_scripts/`
  were removed. Twin file 25/25 (`r2x_bmp_unit`).
- **F5** (41d2ba96, 17688315): I read `run_isolated_expect_reset()` first. It returns once mpremote ends, and
  `_attributed()` reads `/status` only after polling until the board serves, as the stack-exhaustion case does. So the
  drop-off wait is gone, and an immediate reset cannot slip past it.
  - The 22 alone proves the loop ended after BOOT_DONE: the script's own boot cleared every earlier record, and
    `record_loop_end()` writes 22 only after BOOT_DONE and nothing during boot (A.7).
  - I first dropped the phase assertion and the script's fact. The gate's first pass then failed
    `test_device_script_facts.py::test_every_host_function_that_runs_a_script_parses_its_facts` (a host function that
    runs a script must parse its facts).
  - 17688315 brings the fact back and parses it with `allow_missing_done=True`. Only a wrong phase fails; a fact lost
    in rp2's CDC queue does not.
  - Checked with `--collect-only` only (16 collected). Its first run is owed to round 1's first bench run.
    `tests_hardware/README.md`'s row 22 still reads "not yet run".
- **F6** (20b691bf):
  - Reset texts: `_RR_LOOP_ENDED`'s comment (`src/asy_system_service.py:94`), and codes 11-15 in SPEC's table and
    `buildgen/error_catalog.json`, now read "the watchdog reset or the boot entry's reset followed". Code 21 keeps its
    console soft reset.
  - `test_device_script_watchdog.py`'s exempt-list comment says why the loop-end script is on it: the frozen entry's
    product feeds the watchdog until the entry resets.
  - Bite wording gone: `test_timing_budget.py:3`, `test_error_catalog.py:3`, the plant header at :760 and the baseline
    comment at :798. The `# --- bites ---` header in `test_fram_chunk_owner_sites.py` is removed.
  - The await-depth row cites fb447c7e, the change on this branch that set it (25 again at 433d53b2 per the
    falsifier's `r2f_await24`).

### Gate (logs `S/u35/lead/r2x_gate*`)

| step | result |
|---|---|
| lint (`rebuild.sh` + `lint_direct.sh`) | clean (`r2x_gate_lint`, `r2x_gate2_lint` after 17688315) |
| mypy, six passes | clean (276, 59, 311, 1, 1, 1 files) |
| `scripts/test.sh` (gc -1) | first FAIL, 696 s: only `test_device_script_facts.py` (F5's first form); after 17688315 PASS, 701 s: files 137 passed, 0 failed, 80 skipped, 6 deselected; tests 5,824; tests_scripts 6,786 |
| `GC_THRESHOLD=32768 scripts/test.sh` | first FAIL, 722 s, the same single test; after 17688315 PASS, 727 s, same counts |
| twin suite dev -1 / 32768 | PASS, 623 s / 627 s (329 + 15 checks each) |
| twin harness dev -1 / 32768 | PASS, 56 s / 57 s (1 passed, 1 skipped, 65 deselected) |
| npm | not run: no JS file changed |

The twin steps ran on 20b691bf. 17688315 changes only a bench test and a device script, which the twin does not run;
the two `test.sh` stages were rerun on it.

### Lines

This round against 433d53b2: 75 added, 59 removed. Net per directory: `tests_scripts/` +13 (F2's test), `digital_twin/`
+7 (EVENT), `tests/` -7, `tests_hardware/` +1, `scripts/` +1, SPEC +1, `src/` and `buildgen/` 0.

Against 8a32d826 (arduino excluded): 374 added, 3,771 removed. SPECIFICATION.md is 1,129,050 B / 12,144 lines.

| path | added | removed | net |
|---|---|---|---|
| `tests_scripts/` | 48 | 1,132 | -1,084 |
| `tests_hardware/` | 35 | 592 | -557 |
| `tests/` | 80 | 590 | -510 |
| `scripts/` | 48 | 133 | -85 |
| `digital_twin/` | 21 | 54 | -33 |
| `tests_js/` | 0 | 20 | -20 |
| `devices/` | 0 | 12 | -12 |
| `src/` | 2 | 10 | -8 |
| `buildgen/` | 13 | 15 | -2 |
| `.github/` | 4 | 6 | -2 |
| `SPECIFICATION.md` | 110 | 1,196 | -1,086 |
| `BACKLOG.md` | 9 | 8 | +1 |
| `README.md` | 4 | 3 | +1 |

`S/u35r/r2/ftmp` is deleted again.

nothing of mine is running
