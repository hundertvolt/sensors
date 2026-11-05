# B8 falsification brief (lead, 2026-11-04)

Your job: try to REFUTE the claims below about commit `3d0e36bb` (two commits on base `d5c90b71`: 6f24e171 and
3d0e36bb; pre-audit `25caf528`; U6, the owner's website-definitions foundation, is `1b59a05d`, U10 `41b47f1d`). You get
the claims, not the reasoning behind them. A claim stands only if you could not break it; say how hard you tried. Also
look for a lost feature or a reintroduced real defect in the changed files against the pre-audit code
(`git diff --stat d5c90b71 3d0e36bb -- ':!arduino'`: buildgen, devices, js, html, the stager scripts, the boot entry).
The deployed behaviour is in `modules/sensortask-wozi.py` and `legacy/`. Chip and port facts: the pinned MicroPython
and pico-sdk under `/root/pico-toolchain` (say file:line); say where you took any other fact from.

- Read-only worktree `S/wt-b8f` (detached at `3d0e36bb`, `node_modules` linked); S =
  `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-b8f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `b8f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file; it counts as a run). Its binding
  rules apply. No whole gate: single test files only (one tests_scripts or tests_js file counts as one), at most ten
  runs in all. The host is yours from the start; runs go one after another, never two at once.
  Never open anything under `/root/.claude/`. Never read `arduino/` (`':!arduino'` in every git grep and git log).
  `tests_hardware` only with `--collect-only` or `--twin`. Keep any source copy or extract out of `S/u35r/` except
  under `S/u35r/r1/B8/f/ftmp/` (never published), and delete that folder before you hand back.
- The legacy tree (`python/`, `modules/`, `legacy/`) is reference-only: read it, never run or change it.

## Claims
1. Every build check removed in this change is one whose violation neither refuses a boot nor loops it: for each, the
   firmware either keeps a default, clamps, or fails at run time with a logged error. Look hardest at the UART baud
   range (0, negative, above 7,812,500), the rxbuf/txbuf floor (below 32), the hostname label, `name_ext` absent on a
   repeatable driver, two instances on one UART, and a `{source, field}` naming no field.
2. `instance.irq-pull-up-type` must stay: `irq_pull_up = "false"` (a string) builds into a generated module that
   raises at every boot.
3. The restored `names.logger-collision` refuses what it refused at `25caf528` (instance against instance) and
   nothing more; no two loggers can share a name on any device the build accepts.
4. The I2C timeout is one 1..200,000 us check; `smallest_hard_consumer()` keeps every reader it had; no remaining
   reader references a removed rule, constant or helper anywhere (source, tests, docs, buildgen's tunables).
5. Removing the boot entry's `report_if_fatal(ended)` loses nothing: no later boot, route or log reads what it
   recorded. The loop end prints nothing at any DebugLevel; `record_loop_end()` still runs on every loop end, and the
   start line is unchanged.
6. Removing `generate._compiled()` lets no generator bug ship: every image build and every test tier still compiles
   each generated module.
7. `SetupFct` is `Callable[[], Awaitable[None]]`; no setup in any device's setup lists answers anything but None.
8. The page build-date stamp is gone from every site (js, the stager, `build_website.sh`, `build_firmware.py`, tests,
   docs); `js/shell.js`, `js/main.js`, `js/app.js` and `tests_js/shell.test.js` are byte-identical to `656fc82f^`; the
   first-build reload still works.
9. A GET answering JSON that is no object paints the pre-audit banner again; the Apply stripes for Invalid and Failed
   are solid, differing from `25caf528` by one comment line.
10. The browser validator (`js/definitions.js`) checks exactly what U6 (`1b59a05d`, renamed by U10) checked, with
    today's format and shape sets, and nothing added after U10; every device's generated definitions validate in the
    browser and in the Python mirror; the corpus and mirror pins follow the same scope.
11. No product check got weaker: every test change is the mechanical consequence of a removal or restoration above.
    Look hardest at the tests removed though no row named them (the generator-bug test, the stager's two stamp tests,
    the settings-group guard), `test_fatal_report_sites.py` no longer scanning the boot entries, and
    `test_host_cli_exit_idiom.py`'s changed input.
12. `SPECIFICATION.md`, `README.md` and `BACKLOG.md` describe the current behaviour of every item; no doc still
    describes a removed check or the stamp.
13. Numbers: `src/` bytecode 194,887 B to 194,883 B (-4 B), no module grew; net lines against `d5c90b71`: buildgen
    +39 -306, js +44 -235, scripts +8 -31, tests_scripts +65 -664; dev `imageFreeBytes` 60,492 B (58,708 B at d5c90b71).

## Hand-back
Write `S/u35r/r1/B8/FALSIFY.md`, first line "B8 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
