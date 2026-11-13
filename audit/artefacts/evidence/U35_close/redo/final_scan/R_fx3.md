# R_fx3: standing rules, docs, CI and stale references

Worktree `S/wt-fx3`, branch `final-fx3`, one commit `79e5d752` on 590cffcf (message: `S/u35r/final_scan/fx3_commit.txt`).
Not pushed. 16 files, +172/-310.

## Per item

1. **Done.** Restraint rulings into the standing rules.
   - SPECIFICATION.md 0.2: new paragraph "Restraint in practice" after "P4 in practice" (+21). It quotes, with dates:
     10-28 (hypothetical no-go; verify suspicious ones; the hardcoded-timed-check quote; unit tests good quality
     without deep dives; verification machinery temporary, marked paraphrase because the owner's sentence names the
     audit), 10-23 (modules as libraries; planted faults only for complex measurement tests), 11-07 yardstick, 11-09
     (smart design; micro/intermediate/macro; ask before removing), 11-11 (root causes; no runaway chains, no drift
     into fixing tests; negative tests), 11-13 ("prefer to keep existing, working tests ..."), and a pointer to the
     11-10 precedence in CLAUDE.md.
   - CLAUDE.md working agreements: one "Restraint" bullet pointing to it (+3).
   - work-routines "Rules that keep coming back": one bullet, "no gate" (+2). Put at the list's end, away from the
     `gc.collect()` line the other lane may change.
   - SPEC I.4(a): "can raise" became "meets an expectable, concrete (non-hypothetical) `MemoryError`" (2/2).
   - Source note: "Hypothetical findings which are suspicious to be real need to be verified" is not in
     owner_rulings_after_LN118.md; it comes from the 10-28 owner-quote list in `S/u35r/scan/REPORT.md:43`.
   - The precedence quote keeps the owner's spelling "sopersede", as the repo already keeps "Micropyhton" verbatim
     (UART_C_PORT_CHANGELOG.md B98).
2. **Done.** CLAUDE.md workflow: the "never asked ... decided on the owner's behalf" clause replaced by "a decision the
   principles leave genuinely open goes to the owner (the 2026-11-07 rule above)" (+2/-3). "No owner stop-points" and
   the rest kept.
3. **Done.** CLAUDE.md decision records: the 11-10 rule quoted, with the proposal-until-adopted clause (+3); the
   drift clause at :350-352 now yields to a later owner decision (+2/-1).
4. **Done.** CLAUDE.md :224-231 (+13/-8) and SPEC C.8's standing rule (+15/-8) rewritten to the owner's four points;
   the settings-save case names the existing bench load test (`bench/test_bus_concurrency_under_api_load.py`'s
   config-write arms, C.8 tier 4).
   **Read-only check, no hole found:**
   - I2C: scd30, sgp40, isl29125, bmp3xx each have an `I2C_HAZARD_CATALOG` adapter; mock generated and twin generic
     passes iterate every device's TOML; flash tier has same-device, cross-device, sweep and general-call tests for
     all four; bench load test covers every bus.
   - SPI/FRAM: mock (CS overlap, two users, erase), twin (FRAM faults, erase races), flash (same-device, CS hijack,
     reset race, erase race), bench (erase under API load). `SPI_HAZARD_CATALOG` is empty because no device has two
     SPI occupants.
   - Software-only: bus/FRAM/config/command/status locks, settings file, sockets and memory all have twin scenarios
     (concurrent config writes, reboot+bootloader at once, connection-ceiling set, memory gates, loop lag).
   - Borderline, not holes: (a) wozi's BMP3XX+SGP40 on one i2c1 has no physical twin on the dev bench, where the
     BMP3XX sits alone on i2c0. Mock and twin cover it, which is the standing wozi rule. (b) The NeoPixel `_led_lock`
     crossover is pinned at mock (`test_asy_neopixel_driver.py`); the twin only exercises its two users (NTP signal,
     notification alert) and has no dedicated crossover. (c) The `dev`-only UART link has crossover at all four
     levels.
5. **Done**, from evidence only (hand-back on `claude/u35-bench-campaign` @abd3a6cd, lead relays, the report draft).
   - **Out of BACKLOG** (−~130 lines):
     - watchdog-starvation closing reset: 4b on 840a2213, 2026-11-13, one other red, which passed on rerun (`1a656af7`);
     - M1 (`157613c4`) and S3b (7f 2026-11-12, `074df619`; the envelope test is not among the 5 named reds, and the
       lead read 7f as "no firmware red", `7d8697ca`);
     - hard resets during FRAM backups: 7b, `990325db`/`cbe6a9cb`; its three reds are elsewhere;
     - lone BMP3xx: 4b, 2026-11-13;
     - BOOTSEL round trip: PASS 2026-11-11, ResetReason 2, `e43299cb`;
     - every reset code: moved into the table;
     - UART ring with interrupts off: 4b, 2026-11-13;
     - env --tier bench after the pins: rc 0, 2026-11-11, `794dcc5e`;
     - S4: 10g PASS, `40e505c1`; SPEC already holds the fact;
     - G6: 15 PASS on the rerun, `4bc80014`; SPEC's rollover paragraph now records it (+2/-1).
   - **Trimmed:**
     - T4: passed 2026-11-13; only its `stall.fram_entry` figure is owed.
     - No-yield/loop-gap row: the no-yield half goes. VOC and CRC were already in F.3; `stall.gc` gains 16.2 ms.
       The flash-write half stays.
     - ResetErrors budget: 12d's curve recorded (2026-11-12, 0.62-0.91 s at 0-4 readers). The error_log_helpers
       check is still owed.
   - **Other BACKLOG edits:** the final-wiring entry is deleted after its 2026-08-08 credit moved into SPEC A.10's
     first sentence (+3). The audit-plan clause at :17-19 is dropped (example IDs now T4, F17). The bridge, F17, H1
     and every row without evidence stay.
   - **tests_hardware/README.md:** each reset code's "on silicon" cell carries its date, plus one line on what the
     column holds (+15/-14). Sources:
     - 0: invalid record PASS (11-11);
     - 1: power cut and RUN pin (11-13);
     - 2: bootloader, held SDA, graph fault (11-11);
     - 3: storage-paused reboot (11-11) and five warm reboots (11-13);
     - 5: escalation in call (11-11);
     - 7: config reset (11-12, 11-13);
     - 8: FRAM erase (11-11);
     - 22: loop end (11-11);
     - 6, 9, 11-15, 20, 21: the 2026-11-11 bench tier (`e43299cb`), whose reds are all named and none is theirs.
       20's [escape] has a teardown red on an external NTP no-reply, and its call passed.
6. **Done.** BACKLOG "Deferred" bullet: upstream findings reported later as one bundle, if at all, both owner quotes,
   pointing to SPEC F.1 (`child_last`, second await of an ended task) and F.9 (+5).
7. **Done.** UART_C_PORT_CHANGELOG.md B95/B96: "(lead, 2026-11-03)" became "(agent, 2026-11-03)" (2/2).
8. **Done.** bench-routines: "the lead" became "the code session" (3 places, 3/3). "Campaign plan" appears only inside
   the owner's verbatim quote, so it stays.
9. **Done.**
   - `runner.scenarios_timeout_s` went from 2555 to 1200 s (scripts/test.sh 2/2): 1.2x the Pi4's 1,003 s and 2.1x
     CI's 563 s.
   - The owner's three attempts are unchanged, so the largest retry budget is 60 min, equal to the pytest tier's.
     By B.10.1's rule, unit-tests is (9.7+60)x1.25 = 90 and gc-threshold is (10.1+60)x1.25 = 90 (both were 175).
     Coverage stays 95.
   - Updated: ci.yml (4/4), SPEC B.10.1, E.3.1, and Part N's three rows.
   - 1,150 s would bring gc-threshold to 85 but leave only a 1.15x margin on the Pi4. unit-tests cannot go below 90,
     because the pytest tier's 60-min budget decides it.
10. **Done.**
    - Removed: action.yml's `bound-s`/`bound-from` (+1/-13), ci.yml's self-parse and inputs (+2/-7), and
      `RATE_MARGIN`, `Rule.bound_s/bound_from/margin`, `required()`, the three CLI options and the now-dead
      `_positive()` (+6/-33).
    - The probe and cache are unchanged. The floor is the required rate.
    - SPEC: B.10.1 item 4 rewritten; Part N's margin row deleted; the probe-cap, floor and firmware-timeout rows
      adjusted. The floor row gains "a package set nears what the floor moves inside its job's limit" as a trigger,
      so the 588 MB fact is not lost.
    - Tests: the three bound-rate tests were adapted to a raised floor (same drop/keep/budget behaviour, new log line);
      the no-bound test was renamed `test_the_floor_alone_sets_the_required_rate`; the CLI test dropped its two
      options; `test_every_mirror_check_sizes_its_rate_on_its_own_fetching_bound` was removed, because it tested
      nothing but the removed plumbing (-26).
11. **Done.**
    - tests_hardware/README.md:588 drops "Then commit the record" and the "returns on the final tree" clause (1/1).
    - digital_twin/README.md:647-649 now says the record is a local output that is not committed (3/3).
    - The two BACKLOG citations went with their rows (item 5). The runner is unchanged.
12. **Done.** `_repo_scan.py` drops `audit/` and `PROJECT_AUDIT_PLAN.md` and their clause (4/4).
    `test_import_graph.py` drops `audit/` (2/2).

## Checks

- **Lint:** `checks.sh` lint_direct (ruff, shellcheck, actionlint, zizmor `--offline`, method-assign guard, gc sites)
  passed, rc 0.
- **mypy:** main 287 files, host 309, twin 59, no issues.
- **Focused gates:** 17 tests_scripts files, 943 passed. They are decision_vocabulary, citations, ci_workflow,
  ci_apt_cache, tunables_register, comment_block_cap, import_graph, uart_changelog, retry_counts, repo_scan_* x3,
  import_placement, work_routines_helpers, tool_help, code_conventions and lint_ceilings.
- **Full suite:** the tests_scripts pytest run under `ports.flock` (`S/u35/lead/fx3_full_ts.log`): 6563 passed,
  6 skipped, 0 failed, in 448 s, rc 0. The one warning is the uninitialised `datasheets/` submodule, which is
  expected in a worktree.
- **Not run:** the MicroPython tier. No `src/`, `tests/` or `digital_twin/` code changed; scripts/test.sh changed one
  value, which `test_test_sh.py` covers in the full run.

## Noticed, not done

- CLAUDE.md :446-448 still says owner questions come "only at requirement recording and in a consolidation run, never
  during execution". That half-contradicts the 11-07 rule, and the brief kept it.
- CLAUDE.md :470-479 "every agreed-but-deferred item whose trigger is met is swept in and done" is a scope-growth
  clause next to 11-11's "no runaway chains".
- tests_hardware/README.md, System commands section: "reboot and bootloader ... (codes 3 and 4)". Code 4 is retired
  (owner, 2026-11-02), and the bootloader reads 2.
- tests_hardware/README.md "Open on silicon": "that the bootloader reboot loses the reset record" was answered on
  2026-11-11 (ResetReason 2).
- SPEC rows `stall.fram_command`, `stall.fram_entry`, `stall.reset_errors` and `rate.persisted_log` still say
  "re-measured on the next image, which drops the CS settle". The final image ran and recorded no such figure; T4
  keeps the one owed.
- BACKLOG rows kept because the run likely passed but its figure is in no home doc:
  - the supervisor scan budget;
  - the UART hazard-run elapsed;
  - the SGP40 lost-sample count;
  - the idle poll rate (12c's figures: first query after silence 73.7-115 ms and 13.7 ms, loop share 8.47 %; the row
    also holds a filtered line);
  - the general call per chip (12e: 0x61, 0x59 and 0x44 present, the call ACKed, ISL29125 CONFIG1 unchanged);
  - the SCD30 argument reaction;
  - the CONFIG1 restart;
  - the BMP3XX calibration block;
  - Altitude while AmbPres is 0.
- BACKLOG rows kept for other reasons:
  - the boot stretches: 12a's output was cut by a USB EIO (first feed 1,051 ms, largest gap 2,012 ms);
  - loop lag on the bench: its teardown W51 is red every run;
  - the tooling-consolidation round: it has filtered lines, and its runs carried test-side reds.
- UART_C_PORT_CHANGELOG.md B95 still says "the audit's unreachable narrowing branches".
- `tests_hardware/twin_record.json`, which the runner writes, is not in `.gitignore`.
