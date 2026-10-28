UM4 hand-back, written by the lane (Wed Oct 28 00:36:57 UTC 2026)

**Commits** on audit/u35-um1 in S/wt-u35um1 (base c570ba76), oldest first. Not pushed. The tree is clean except the linked node_modules.
- b41a51b5: item 1. `digital_twin/_driven_clock.py` and the runner's test-only `--test-uart-driven-clock`. `_twin_launch()` in tests_scripts/test_digital_twin_generated_boot.py passes the flag for every device wiring a uart_link pair, and `_run_twin` fails a launch whose output has no `UART_CLOCK` line. Also the clock's unit file, the runner test and Part N rows `l2.driven_clock_run_limit_s` and `l2.twin_uart_clock_recheck_ms`.
- 6290b8e6: item 1. Every exchange in tests/test_digital_twin_uart_link.py runs on one `DrivenTime`.
- 59bcf233: item 3. audit/trace/UART_PART_J.md :20 and :116 now read the owner's 2026-10-27 catch.
- d6b2914b: item 1. scripts/_digital_twin_scenarios.py's `Context.boot()` passes the flag for a uart_link device, with its unit test.
- e83504cb: review.md re-rendered.
- d42cad40: item 4, the merge of 111129f4 (a merge commit).
- 369a7c39: fix of an item-1 red found by the merged head's tier. `_driven_clock.py` was missing from `_KNOWN_TICKS_USERS`.
- 5f1cccb6: fixes of item-1 reds found by the same tier, plus two flaky clock tests (see "Fixes after the merge").

## Item 1: the clocks, the loops, the bites
**The mechanism.** On the Unix port, while a non-fd pollable waits, every scheduler step costs about 1 ms. That makes the link's 1000 ms ACK timeout a measure of host load.
- The driven clock lends `asy_crc_checks`, `asy_uart_driver`, `asy_uart_comm` and `asy_uart_link_driver` one virtual `ticks_ms()` and their sleeps.
- Virtual time catches up with the host only while none of their tasks is runnable, in wake order. So CRC turns and host stalls spend no deadline.
- A modelled flash hold (`_flash_stall`) moves it at once.
- The clock is released at the run's end. Reset scenarios exit without the release line, which is harmless.

**CRC16 dev-link test** (tests_scripts/test_digital_twin_generated_boot.py::test_the_uart_link_device_boots_and_exercises_its_link_with_crc16_on_both_ends)
- Clock: the driven clock, through `_twin_launch()`. Every assertion is unchanged.
- Load: K busy loops pinned to the twin's CPU, at 32768. Red signature: Transfers (0, 0), Failures (0, 1).
- Unfixed (flag removed):
  - K=3: 0/75 red. It did not reproduce today.
  - K=8: 20/20 red before the merge, and 3/10 red on the final merged head.
- Fixed, on the final head 5f1cccb6: **K=3 0/75 red, K=8 0/40 red.** Each count is one launch. The first launch on this head was killed by the 23:11 container restart and is not counted.
- Earlier clock versions, superseded and not counted toward the final: the settle version, K=3 0/75; the wait_for version, K=3 0/75 and K=8 0/19 (the 18:11 restart cut it); the pre-merge final, K=3 0/75 and K=8 0/40.
- Bites on the final head, idle host:
  - First ACK delayed 1100 ms on the module clock (past the timeout): 5/5 red.
  - Delayed 900 ms (under it): 0/5 red. So the timeout decides, not slowness.
  - Host stall past the timeout before the first ACK: 0/3 red fixed, 3/3 red unfixed.
- Guard bite: a runner printing no `UART_CLOCK` line fails the test with the guard message.
- Formal pair (base c570ba76 → head): the file 61.3 → 61.6 s; test_stripped_image_boots 8.6 → 8.8 s.

**tests/test_digital_twin_uart_link.py**
- Clock: each exchange runs on one `DrivenTime` over the link's three modules and its wire (`_driven()`). The clock continues from the previous run's instant, and `_wire_on` starts past the wire's `_next_free_us`.
- Boot, setups and log reads stay on the poll-round clock; none of them exchanges.
- Changes needed: the collection pause uses `clock.advance()`, and the max-train stall fires at ticker round 750.
- Pair at -1: 73.1 → 30.4 s. At 32768: 97.7 → 63.1 s. CPU about equal.
- Under 4 pinned burners: 152.6 → 134.6 s at -1, and 317.5 → 341.8 s at 32768. That load is CPU-bound, see "For the lead".
- Bites: every ACK past the timeout on the module clock fails every exchanging test. A host stall past the timeout before the first ACK: 22/22 pass.
- 22/22 at both stages. Lane N11d's measurements of this file were taken on its own worktree.

**Scenario harness** (scripts/_digital_twin_scenarios.py)
- Clock: the flag, for a uart_link device.
- Its unit test is red on the old harness.
- Ring scenario bites: unfixed host stall red, fixed green, fixed virtual delay red.
- Final head: the dev tier PASS at -1 (11m27s) and at 32768 (11m39s). The flag reached 61 of 61 twins at each stage.

**The clock's own file** (tests/test_digital_twin_driven_clock.py)
- 10 tests. 75 runs at each stage on the final head, all clean.
- All 11 planted clock faults are caught. Three plants were re-pointed at the sets, and one is the lost-cancel form below.
- Smoke boots (dev, novel_combo), before the merge:
  - 80/80 shutdowns clean.
  - A host stall: E81 unfixed, clean fixed.
  - A virtual delay passes the smoke on either clock. Its timeout lands after the smoke's /status read, so it is not a bite of the smoke.

**Other formal pairs (base → head):**
- test_digital_twin_scenarios 9.0 → 8.2 s.
- test_twin_runner_test_flags 0.98 → 1.07 s.
- test_digital_twin_run_generic_integration 1.79 → 1.74 s and 1.98 → 1.86 s.
- test_ticks_rollover 3.9 → 4.0 s.

**Tests left on the real or poll-round clock, with reasons:**
- tests/test_digital_twin_uart_comm_hazard.py and test_digital_twin_uart_field_sweep.py: the poll-round clock (J.7's one door), which counts the modules' own sleeps, not the host. Each green 3/3 under K=8 at 32768.
- tests/test_digital_twin_machine_uart.py, its two driver reads: 50 ms real timeouts on purpose, since the wire model's real time is what is under test.
- test_digital_twin_sensortask_integration.py:
  - its heap-floor wait ends on "no initiator busy", which an expired exchange also satisfies;
  - its driven scenarios already lend every `asy_*` module to `DrivenTime`, so they need nothing new.
- test_digital_twin_loop_end.py judges reset reasons, on `DrivenTime` over every `asy_*` module (CMr1j). It needs nothing new.
- Already on `DrivenTime`: bus_hazard, held_i2c, hot_replug, setup_resets, timer_pool, clock_jump, ntp.
- Runner and launch tests: no exchange verdict.
- scripts/_digital_twin_ci_suite.py Run 1 `_check_quiet_boot`, Run 3 (CRC16 pass) and Run 4: twin CI, not runnable here (CHECKLIST 2). Adding the flag is one argument in its spawn, your call.
- tests_js live-backend-put-matrix (the ResetErrors all-zero rows on dev): a live suite (CHECKLIST 2). The flag would be one argument in `tests_js/_twin_process.js` spawnTwin.
- live-backend.test.js, cross_browser_smoke, twin_board and boot_contiguity read no UART state.

## Item 2: comments and doc text
Each changed test has a comment of at most 3 lines saying why it runs on the driven clock.

The doc text for D3r follows.

**SPECIFICATION.md J.7**, after the paragraph ending "...so the step ceiling twice that count holds on a slow host too (agent, 2026-10-08).":

> **On the twin a reply budget counts a driven clock, never the host's.** The pinned Unix port makes every scheduler step wait in `poll()` for `MICROPY_PY_SELECT_IOCTL_CALL_PERIOD_MS` (1 ms) while any pollable in asyncio's IO queue is not a file descriptor, a zero timeout included (`extmod/modselect.c`, v1.29.0, `MICROPY_PY_SELECT_POSIX_OPTIMISATIONS` 1); rp2 (0) polls once and returns. Measured on the pinned Unix port: 6.9 µs a step with nothing registered, 1160 µs while a ThreadSafeFlag waits (the NeoPixel overlay's on a booted twin), 4.7 µs once it is set. A CRC16 frame and its ACK take about 220 steps (the owner's per-byte yield, I.2), so on a booted twin that round trip took about 0.6 s on an idle host and passed the link's 1000 ms ACK timeout under host load — a twin artefact, rp2's step being microseconds. So no twin test judges a UART deadline on the host's clock (agent, 2026-10-27):
> - in-process, `tests/test_digital_twin_uart_link.py` runs every exchange on one `DrivenTime` (`tests/_fake_time.py`) over the link's three modules and its wire (`_driven()`), on from the last run's instant; its boot, setups and log reads stay on the poll-round clock, no exchange in them;
> - in a twin process, the runner's `--test-uart-driven-clock` (`digital_twin/_driven_clock.py`) lends `asy_crc_checks`, `asy_uart_driver`, `asy_uart_comm` and `asy_uart_link_driver` one clock whose virtual time reaches the host's only while none of their tasks is runnable, in wake order, so a CRC's turns and a host stall spend no deadline, while a modelled flash hold (`digital_twin/_flash_stall.py`) moves it at once, as rp2 programs flash with interrupts off. Every launch of a device wiring a `uart_link` pair passes it: `tests_scripts/test_digital_twin_generated_boot.py`'s `_twin_launch()` (the CRC16 boot, every smoke boot, the compiled images of `tests_scripts/test_stripped_image_boots.py`) and `scripts/_digital_twin_scenarios.py`'s `Context.boot()`.
> The silicon round trip under API load is the hardware round's to read (L4, owed).

In the same section, the sentence beginning "Every UART L1 and L2 file judges its reply budgets the same way, through one shared `PollRoundClock`" loses its last item, `tests/test_digital_twin_uart_link.py`, whose exchanges now run on the driven clock.

**digital_twin/README.md**, in "What's here", after `_flash_stall.py`:
> - `_driven_clock.py` — the driven clock the runner's `--test-uart-driven-clock` lends the UART link's modules: their `ticks_ms()` and sleeps on virtual time that reaches the host's only while none of their tasks is runnable, so a CRC's turns and a host stall spend no protocol deadline; a flash hold moves it at once. Released at the run's end.

**digital_twin/README.md**, a row for the "Runner flags" test-only table:
> | `--test-uart-driven-clock` | `UART_CLOCK driven modules=<n>`; at the end `UART_CLOCK released virtual_ms=<n>` | the UART link's modules (`asy_crc_checks`, `asy_uart_driver`, `asy_uart_comm`, `asy_uart_link_driver`) on one driven clock (`_driven_clock.py`) for the run: a scheduler round here costs about 1 ms while a ThreadSafeFlag waits, so a reply deadline on the host's clock would read the host's load (SPECIFICATION.md J.7) |

**digital_twin/README.md**, a sentence for the fidelity table (or "Harness pitfalls"):
> A booted twin's scheduler step costs about 1 ms while any non-fd pollable (a waiting ThreadSafeFlag) sits in asyncio's IO queue (`extmod/modselect.c`, v1.29.0, Unix's POSIX poll optimisations), against microseconds on rp2: wall time on the twin is no measure of the device's, and a test judging a UART deadline runs the link on a driven clock (SPECIFICATION.md J.7).

**A Part F fact:**
> MicroPython's `asyncio.wait_for()`/`wait_for_ms()` lose a cancel that lands after the timeout fired and before the runner task ended: the waiter then awaits its runner (`extmod/asyncio/funcs.py:49-51`), `Task.cancel()` forwards a cancel to the task being awaited (`extmod/modasyncio.c:208-211`), and the waiter raises `TimeoutError` instead of `CancelledError` (v1.29.0). Found as a booted twin's shutdown hanging 1 run in 10-74 while its driven clock's driver caught that `TimeoutError` and looped; the driver now times its wait with an alarm task and awaits only an event (`tests/test_digital_twin_driven_clock.py`'s cancel-window test, red on the `wait_for_ms()` form).

I added one SPEC row myself, because the tier requires it: E.6.6 now has a `twin-instrument` row for `test_digital_twin_driven_clock`. I did not edit the J.7 text or the README.

## Item 3
UART_PART_J.md :20 and :116 now cite the owner's 2026-10-27 catch: A17, and the two ALLOC tests. :116 "holds". :20 "text diverges": Part J's promotion paragraph (SPEC ~:9379, "the one MemoryError let through") is still for your D3r.

## Item 4: the merge (d42cad40)
**Changelog.** Both sides' entries are united in the file's order.
- This branch's B90 (readline catch) and B91 (the PieceBuffer answer), committed first, keep their numbers. The owner report cites them that way.
- **D2S's B90 (`_check_buffer()`) is now B92.** D2S's hand-back still says B90. No text in the tree cites either number.

**Verdict files** (raising_verdicts/asy_base_classes.json, e51_verdicts.json)
- Each entry comes from the side that changed it. Where both sides did, this branch's text with int's line shifts applied:
  - uart_comm :1125→:1118, :988→:981, :903→:896, :569-571→:562-564, :948→:941 (three entries);
  - isl29125 :985→:984, :260→:259.
- Each line was read on the tree.
- In each side's added text, no citation into a file the other side changed moved.

**e51_hits.json**
- Per file, from the side that changed it.
- asy_uart_comm.py and asy_uart_driver.py (both sides changed them) come from a fresh dump: all 129 jobs, every tests/test_*.py, PER_DEVICE on all six devices, under build-settrace.
  - It ran in two launches, 115 + 14, because the first hit the 30-minute background limit.
  - Zero memory markers and no tracer cut short. 128 jobs rc 0. The one red was test_ticks_rollover, fixed in 369a7c39, and no src line depends on that test.
  - Against each side's hits, no line is lost: 777 and 550 lines.

**Rendered files.** raising.md, e51.md, conformance.md, queue_c.md and review.md were re-rendered by their tools.
- conformance.md now has the restated U17 cells; int's stale ":278 pending owner" text is gone.
- Its stamp reads e83504cb, the HEAD while the walk ran.

**src/** merged cleanly. Both behaviours are kept: `_check_buffer()` checks writability only, next to the PieceBuffer catch and the `read_at()` sends; and the readiness poll's narrowed except sits next to readline's catch.

## Fixes after the merge (369a7c39, 5f1cccb6)
The merged head's whole tier found four reds that came from my item-1 files since b41a51b5. They had gone unseen because before the merge I ran focused readers, not the whole tier.
- **Ticks users.** `_driven_clock.py` was missing from `_KNOWN_TICKS_USERS`. That turned test_ticks_rollover 22/23 and all 18 of test_ticks_wrap_scan red. Now it is listed, and the scan judges the file: clean, and two plants (a subtraction, an ordering) are each found at their line.
- **Counter steps.** `_turns` and `_woken` were unguarded integer steps. They are now sets: the tasks mid-turn, and the wakes released whose task has not run. No count remains, and behaviour is unchanged. I added no exemption entry, since adding to an allow-list is out.
- **Trailer.** The clock test file now ends with the canonical microtest trailer.
- **Level containment.** The E.6.6 row mentioned above.
- **Two flaky clock tests.**
  - The sleep test compared virtual time with a host stamp taken after the origin.
  - The spinner test read the clock after awaiting a task outside the lent modules.
  - Each failed when a host ms ticked in between: 1 in 10 and 3 in 80 runs. Each old form is red and each new form green on a planted 2 ms host step.

## Checks on the final head 5f1cccb6
- **Importer files.** At 369a7c39: the 83 files whose imports reach a module either side changed, both stages, PER_DEVICE on all six: 236 jobs, all rc 0, zero markers. At 5f1cccb6: the 16 importers of the last change, both stages: 92 jobs, all clean.
- **Whole tests_scripts tier:** 7052 passed, 2 failed. Both are test_twin_record. They are expected on a src change and wait for your re-record; the record covers run_device_script.py and twin_board.py, neither of which this branch changed.
- **lint_direct** rc 0. **The six mypy passes** on a cold cache: rc 0.
- **Audit checks:** the walk, e51 (--check and --self-test) and review_rows --check are all green, with 8611 rows. No new test rows came from the fixes.

## For the lead
- **Overlap with int's new lanes, for planning the merge:**
  - N11e:
    - SPECIFICATION.md Part N: my rows `l2.twin_uart_clock_recheck_ms` (:12471) and `l2.driven_clock_run_limit_s` (:12531) sit near N11e's rows (int :12461-12508);
    - my E.6.6 row at :5784;
    - tests/test_ticks_rollover.py: my one `_KNOWN_TICKS_USERS` line (:56) against N11e's hunks at :75 and :251.
  - Through this branch's UM2/UM3 work, not mine:
    - tests/test_asy_uart_comm.py, test_asy_uart_driver.py and test_asy_uart_link_driver.py (N11e);
    - tests/test_asy_base_classes.py (N11d).
  - N15: none. This branch leaves the UDP shim, scripts/test.sh, test_asy_udp_socket.py and `_dns_burst` untouched.
  - CMr1k (also in int now): tests/test_digital_twin_run_generic_integration.py. Its import hunk at :59 sits next to mine at :63-70; its other hunks are elsewhere.
  - review.md: rendered on both sides, so re-render it.
- **Lost cancel in product code.** The same lost-cancel window is in product code at `src/asy_neopixel_driver.py:82`, the overlay loop: `wait_for_ms(self._overlay_start.wait(), ...)` with `except TimeoutError: pass` inside `while True`. A supervisor or shutdown cancel landing in that window is lost. Other wait_for sites exist (asy_fram_driver:493, asy_system_service:595, asy_udp_socket:130, asy_webserver_service:337/346/739/935/998) but are not in loops that swallow the TimeoutError the same way, as far as read. This is a product change outside my brief, for your routing.
- **uart_link's remaining 240 s risk is CPU.** The hazard-run test takes 37.5 of 67.6 s at 32768, and I did not change it.
- **CRC16 margin.** The test's 3 s real window needs one rise. At K=8, 15 of 40 runs rose by 1, not 2: throughput, not the timeout.
- **Stale citations elsewhere.** audit/sweeps/open_findings.md has citations that were stale before the merge (asy_uart_comm.py :558/:559/:562/:656/:691, test_asy_base_classes.py :900/:916/:1425, and others). The merge did not cause them, and I did not edit the file.
- **Carried e51 hits.** In seven files neither side changed, the carried hits differ from the fresh dump: bmp3xx +1, config_manager +6, crc_checks +1, i2c +5/-1 (:335), scd30 +3, sgp40 +1, webserver +1. I kept them as carried, per the rule.
- **Process note.** Before the summary, the first runner edit was made with a Python heredoc and the uart_link draft was copied in with cp. Every later edit used Edit or Write.
- **Cleanup.** The coverage dumps are deleted, and S/wt-u35um4base is removed. Logs are in S/u35/laneB/um4/ (runs.txt, crc/, scen/, merge/).

## Item 5: merge of d25d3cc2 (written 2026-10-28 01:51 UTC)
**The merge commit is 1ac8ecaf**, a merge commit onto 5f1cccb6; its second parent is d25d3cc2. Not pushed.

**Conflicts.** There was one: audit/b3/review.md, which both sides had rendered. I took int's version, then re-rendered it with review_rows.py on the merged tree: 8641 rows, each with its verdict.

**Auto-merged files.** Every other file merged with each side's hunks apart. I checked that each keeps both sides' intent:
- **SPECIFICATION.md.** Part N holds 1327 rows: int's 1325 plus my two, `l2.twin_uart_clock_recheck_ms` (:12569) and `l2.driven_clock_run_limit_s` (:12630). Each is in its own table at its place. No row from either side is missing, and none is doubled. My E.6.6 row sits beside int's text.
- **tests/test_ticks_rollover.py.** My `_KNOWN_TICKS_USERS` entry, and N11e's neopixel-frame tag.
- **tests/test_digital_twin_run_generic_integration.py.** My clock-lend test and its imports, and CMr1k's per-wiring launcher and boot runs.
- **The UART L1 files** (test_asy_uart_comm.py, test_asy_uart_driver.py, test_asy_uart_link_driver.py) **and test_asy_base_classes.py.** This branch's PieceBuffer, readline and `read_at()` tests sit beside N11e's stall drains, shipped hazard rates and tags, and N11d's bound tags.
- **tests/test_digital_twin_machine_uart.py.** UM3's settle() test, and WR1's comment.

Int changed no src/ file, so raising.md, e51.md and e51_hits.json stand. The rebuild is done.

**Where the driven clock meets N11e's rates and drains.** In no test.
- N11e's `drain_s` is used only by test_asy_uart_comm.py, through the harness. Its `_SHIPPED_RATES` is used only by test_asy_uart_link_driver.py's hazard checks. Neither file uses a driven clock.
- None of my driven-clock tests passes `drain_s` or a rate: the twin uart_link file, the clock's own file, the CRC16 boot and the scenario harness.
- So each merged test keeps its own side's form unchanged.
- The merge does reach my uart_link file in one place. Its exchanges run on `DrivenTime`, and N11d changed that class to "a driven sleep is its listed wake". Every method the file uses is still there: `_sleep_ms`, `_wait_ms`, `run_until`, `advance`, `now`. The file is green at both stages (below).

**Bites, re-checked on 1ac8ecaf at -1 and at 32768.**
- **N11e's two hazard bites.** These are plants in a copy of asy_uart_comm.py, put first on MICROPYPATH, running test_asy_uart_link_driver.py.
  - uid 0xFF accepted: the three hazard tests fail with "['uid', [True, True, True], True]". 48/51 at each stage.
  - The ACK for uid 0xFE withheld: the same three fail at "virtual t=22500 ms, 22440 ms after". 48/51 at each stage.
- **N11e's two stall-drain bites.** These are plants in a copy of the harness, placed beside copies of test_asy_uart_comm.py and the threshold runner.
  - A timed-out drain reported True: test_a_responder_that_never_finishes_its_rounds_fails_the_exchange fails. 204/205.
  - may_stall ignored: the declared stall and the four other declared stalls fail. 200/205.
- **My 11 planted clock faults.** Each is caught at both stages; b4 fails a second test at 32768.
- **The uart_link file's two plants.**
  - Every ACK past the timeout on the module clock: 10 of the first 15 tests fail before run_bites' 300 s per-file timeout ends the run, at each stage.
  - A host stall past the timeout before the first ACK: 22/22 pass.
- **A correction to the items 1-4 bite runs above.** Those clock and link bites were run at -1 only.
  - This time the first 32768 pass ran with tests/_threshold_runner.py from tests/. That runner's directory comes first on sys.path, so it imported the real modules, not the plants, and every plant read green.
  - I re-ran each 32768 bite with the runner copied beside the plant, as N11e does. The 32768 results above come from that re-run.
- **The CRC16 probe**, on an idle host at 32768:
  - virtual ACK delay under the timeout: 0/5 red;
  - virtual delay past it: 5/5 red;
  - host stall past it: 0/3 red with the clock, 3/3 red without;
  - no plant: 0/3 red.
  - The probe file was placed for these runs and removed after.

**Checks on 1ac8ecaf.**
- **The UART files, the harness importers, the twin UART files and the runner test, at -1 then 32768:** 14 files, 28 jobs, all rc 0, zero memory markers. The files are test_asy_crc_checks, test_asy_uart_comm, test_asy_uart_driver, test_asy_uart_link_driver, test_machine_uart_link, test_uart_comm_cancel_sweep, test_uart_comm_hazard, and the twin's driven_clock, machine_uart, run_generic_integration, uart_comm_hazard, uart_field_sweep and uart_link, plus test_ticks_rollover.
- **The dev scenario harness, with N15's shim in the tree:** PASS at -1 (11m26s) and at 32768 (11m40s). The flag reached 61 of 61 twins at each stage.
- **The whole tests_scripts tier:** 7101 passed, 2 failed. Both are test_twin_record, the same two that wait for your re-record.
- **lint_direct** rc 0. **The six mypy passes** on a cold cache: rc 0.
- **Audit checks:** the walk, e51 (--check and --self-test) and review_rows --check are all green, with 8641 rows.

The tree is clean except the linked node_modules.

nothing of mine is running
