# B7 falsification brief (lead, 2026-11-03)

Your job: try to REFUTE the claims below about commit `21086438` (three commits on base `d6bc7617`: 6c00e98e, 15b2175b,
21086438; pre-audit `25caf528`). You get the claims, not the reasoning behind them. A claim stands only if you could not
break it; say how hard you tried. Also look for a lost feature or a reintroduced real defect in these files against
the pre-audit code: `src/asy_neopixel_driver.py`, `src/asy_notification_service.py`, and the notification's sites in
`buildgen/codegen.py`, `buildgen/definitions.py`, `buildgen/error_catalog.json`, `mockdata/samples.json`. The deployed
behaviour is in `legacy/firmware/python/IndividualDrivers/neopixel_signal.py` and `modules/sensortask-wozi.py`.
The WS2812 datasheet is in `datasheets/`; say where you took any other chip fact from.

- Read-only worktree `S/wt-b7f` (detached at `21086438`); S =
  `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-b7f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `b7f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file; it counts as a run). Its binding
  rules apply. No whole gate: single test files only (one tests_scripts file counts as one), at most ten runs in all.
  The host is yours from the start; runs go one after another, never two at once.
  Never open anything under `/root/.claude/`. Never read `arduino/` (`':!arduino'` in every git grep and git log).
  `tests_hardware` only with `--collect-only` or `--twin`.
- The legacy tree (`python/`, `modules/`, `legacy/`) is reference-only: read it, never run or change it.

## Claims
1. The overlay task writes the pixel only when the overlay changes: no periodic rewrite, no `wait_for_ms()` and no
   `_OVERLAY_REFRESH_MS` remain in `src/`, the tests, `SPECIFICATION.md` (Part N included) or buildgen's tunables. A
   cancel at any instant of its wait ends the task.
2. `_clamp_byte()` maps NaN and +/-inf to 0 and clamps to 0..255. The ramp floors its duration at 0.1 s (a NaN
   included) and plays +inf as one step. There is no 60 s cap, and every product caller already bounds the duration
   (REST 0.5-60 s, `FlashDur` 0.5-10 s) and the colours.
3. `request_signal()` waits while a signal is queued or running and its 120 s deadline is ahead, then stores its
   values, sets the slot and answers True: it never drops. The last request wins. A request is lost only behind a
   ramp longer than 120 s, which no product caller can ask for.
4. W67 is gone from every site (source, catalog, tests, docs, the website's mirrors), and the W band [67, 68] is intact.
   `_trigger_signal()` logs E14 on a raise, as at `25caf528`.
5. After a ramp, black is written and the slot cleared inside the overlay lock, then the overlay is restored. A
   supervisor restart mid-ramp writes black, replays the one flash in the slot, then restores the overlay. No product
   path leaves the pixel lit outside a signal or the overlay.
6. An external command is refused while a signal is queued or running; the REST callback is unchanged.
7. `/status`'s notification block answers `PauseTime` alone, and the Pause control's `statusPath` still reads it (dev
   and wozi). No `Triggered`, `State`, `TS` or NotifyState remains in product code, buildgen, the website, mock data,
   the catalog or the docs. Nothing else read the removed sample (it was in no `/measurements` list), and the empty
   `NOTIFY` namedtuple passed to `SensorReaderConfig` has no reader that breaks on it.
8. With the sample-age bound gone, no producer's sample can trigger a flash from an old value: every producer re-stamps
   its sample every cycle.
9. No producer field the service reads holds a non-number; a NaN never triggers a flash; E15 stays for a producer that
   raises.
10. Every cycle that cannot read the service's own config persists one CFG_READ entry (one ring slot) and prints one
   console line.
11. `NeopixelDriver.setup()` answers None, and nothing reads it.
12. The constructor takes `neopixel_freq` and `led_overl_bri` again, with the module constants as defaults; no TOML key
    reaches them and codegen passes neither.
13. The three event lines "External LED command received.", "Internal LED command received." and "Internal LED command
    started." are back where `25caf528` had them.
14. No product check got weaker: every test change is the mechanical consequence of an item above. Look hardest at the
    three host checks changed in 15b2175b (the status-group test, the module-double surface test, the
    measurement-module guard), the twin Wi-Fi modes test's "(a)" check, the two integration tests that now expect one
    start frame, and every removed test (the overlay refresh, the drop warning, the State scenario, the stale-sample
    twin test, `raise_on_write`).
15. `SPECIFICATION.md` and `BACKLOG.md` describe the current behaviour of every item, and no doc still describes a
    removed mechanism.
16. Numbers: `src/` bytecode is 194,689 B at 15b2175b (-822 B against `d6bc7617`'s 195,511 B), and no module grew;
    21086438 adds only the three lines: the LED driver 2,392 B to 2,523 B, `src/` 194,820 B. Dev's
    `imageFreeBytes` is 58,956 B at 15b2175b (57,868 B at `d6bc7617`).

## Hand-back
Write `S/u35r/r1/B7/FALSIFY.md`, first line "B7 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
