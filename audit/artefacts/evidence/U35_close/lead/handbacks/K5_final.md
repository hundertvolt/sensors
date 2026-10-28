K5 is committed as 1fb687f on audit/u35-k5, worktree S/wt-u35k5, nothing uncommitted. Not pushed. It brings every over-cap block in my 27 files to the cap. Eleven blocks need no meaning change; one fixture header had a stale fact, which I corrected and named in the commit body.

**What I found.** I measured each block of the 27 files by the brief's rule (stripped length / 120, rounded up; JSDoc `@` lines with their continuations, tag lines and directives left out), with my own measurer at S/u35/laneK/k5/tools/blocks.py.
- 49 of the 61 long lines sit in blocks that already weigh 3 or less, or are `@`/directive lines. They are unchanged, including both .github action headers, the three ci.yml lines and the eslint directive at _live_twin_command.js:555.
- The lead's js120.txt has extra 4s in my files (eslint.config.js:2, mock-server.js:2/80/…, shell.test.js:71 and others). They are miscounts: its measure_js.py counts the closing `*/` line and the `@param` continuation lines. By hand those blocks are 3.
- 12 blocks were over the cap:
  - js/mock-server.js:768
  - pyproject.toml:181, 188, 197, 209, 218
  - tests_js/_live_twin_command.js:148 and 526
  - tests_js/_twin_process.js:168
  - tests_js/live-backend.test.js:7
  - tests_js/mock-server-put-matrix.test.js:2
  - tests_scripts/buildgen_fixtures/malformed_missing_device_table.toml:1

**What I did with them.**
- **Rewrapped (4):** pyproject.toml:181 and :188, _live_twin_command.js:148, mock-server-put-matrix.test.js:2.
- **Tightened (6):**
  - mock-server.js:770: "(a pending command" → "(pending command"
  - pyproject.toml:199: "imports on …'s pending list"
  - pyproject.toml:209: "rp2 has no itertools"
  - _live_twin_command.js:526: "every tab not loaded"
  - _twin_process.js:168: "an uninternable string" (the name of the check it runs)
  - live-backend.test.js:7: "boot, real HTTP, real browser navigation"
- **Split (2):**
  - pyproject.toml:218, at a bare `#`. Topic 1 is the owner-decided PT018/EM exemptions for both host suites; topic 2 is S603, which applies to tests_scripts/ only. This adds 2 lines to pyproject.toml. No live citation outside audit/ points past line 218, and PROJECT_AUDIT_PLAN.md's cites are already stale.
  - The fixture TOML. Topic 1 is what the fixture is; topic 2 is who reads it. This is the one meaning change: the header said only test_build_website_sh.py uses the fixture and copies it into devices/. In fact that test copies it into a sandbox copy's devices/, and test_build_device_websites_sh.py:66 also plants it in the live devices/ as zz_test_device_websites_skip.toml, then removes it (agent, 2026-10-22). The first sentence, which is allow-listed in _decision_vocab_allowlist.txt:354, is unchanged.
- **Moved:** none. No CAPMOVE line written. Nothing left over the cap.

verify.txt: S/u35/laneK/k5/verify.txt.

**Checks** (logs in S/u35/laneK/k5/):
- My measurer on my 27 files: 0 over cap. verify.py: rc 0, `CODE-CHANGED FILES: 0`. measure.py: rc 0, none of my files appear.
- tomllib parses of pyproject.toml and the fixture match the base's.
- `npm run lint` 0, `npm run typecheck` 0, `npx vitest run tests_js/lint-ceilings.test.js` 0 (4/4), each under `unshare -n ns_xdg.sh`. I copied node_modules in after the lockfile hash matched and removed it afterwards.
- `ruff check` on the eight scopes: 0.
- actionlint and zizmor did not apply: no workflow or action file changed.
- The 12 commit checks: rc 1, 800 passed and 1 red. The red is test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree (src/asy_config_manager.py:71 and other tags have no Part N row; SPECIFICATION.md:11787 has a row with no tag). The error lines are identical to K4's.
- The 17 repo-wide scans: rc 1, 872 passed and 6 red. The reds are that same tunables test, test_level_containment (fault_storm, ntp_unreachable_load, reader_saturation, watchdog_fault have no counterpart) and four test_task_inventory tests (asy_uart_link_driver.py:221/222, asy_neopixel_driver.py:144/202 are not in C.9's table). K2's and K4's scans17.txt show the same 6. None of them reads my files; they wait on the lead.
- 16 tests_scripts readers of my files (including test_build_website_sh, test_build_device_websites_sh, test_ruff_exemptions_live and test_typecheck_sh, with no real MicroPython): rc 0, 258 passed.
- I ran no MicroPython, twin or unit files. The silent-failure scan had nothing to scan, since no code changed.
- Zero MemoryError or "memory allocation failed" in any log.

**Runs.** RUNS.md has lines for the scans (rc 1) and readers (rc 0) runs. The 12-check run's lines were written after the fact; I had missed them at start. The container restart cut off no run of mine.

Facts owed: none to X or Y. Lead: the tunables, level-containment and task-inventory reds on bc0d77b, and measure_js.py's overcount.

nothing of mine is running