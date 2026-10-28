D2e hand-back (lane D, U35). One commit, `bbf808d`, on `audit/u35-d2` (on 5b05a53), in S/wt-u35d2. It touches only SPECIFICATION.md, CLAUDE.md, BACKLOG.md and tests_hardware/README.md. Not pushed, nothing uncommitted.

**Carry items**
1. **Landed.** Every site was found again by its quoted text.
   - A.4: the sibling-and-rename sentence is gone; the bullet now reads as it did at f3fff0e.
   - C.7.3: replaced by the single-write paragraph, with the owner's 06:32 decision quoted along with its question. It states: `_write_file()` under the lock; no yield; O_TRUNC makes no commit at open (lfs2.c:3146-3149); the commit happens at close (`:3434-3496`); a failed write commits nothing (`:3250-3253`).
   - Z's power-cut fact is included: a cut during the first boot's write leaves an empty file (`:3125-3128`). The next boot treats it as damaged, rewrites the defaults and adds a ConfigFaults entry. I checked this against setup().
   - F.3 `stall.flash_program`: the first two cells are back to f3fff0e's wording, with the helper named. The other cells already matched f3fff0e (checked cell by cell).
   - J.6: back to f3fff0e's "littlefs runs without yielding" sentence.
   - Part N: the `config.flush_slice_bytes` row is withdrawn, and `uart.flash_hold_max_ms`'s basis cell is back to f3fff0e's (agent, 2026-10-07).
2. **Landed.** The F.3 consumers cell keeps the agent's 2026-10-21 classification and adds the owner closing the stall. The consequences are worded exactly as LEAD NOTES 86 lists them: no reset, no loss, a late answer, a late read, one LED stutter, a DNS retry, and on dev's bench link one failed and resynced transaction. The quote and its question come from LEAD NOTES 86.
3. **Landed.** D.3 has a new "Least wear" item with the owner's words (LEAD NOTES 87 / CHECKLIST 24).
   - It names both guards, and states the write-site guard's limit (LEAD NOTES 103): an aliased `open`, a command passed through a local, and ext/ are not covered.
   - C.8's write-safety constraints now point to D.3.
4. **Landed in CLAUDE.md.**
   - The least-wear rule names test_firmware_write_sites.py and its limit.
   - The UART bullet adds the link-exerciser exception: the LEAD NOTES 95 quote in full, with its question, and test_uart_link_bench_only.py as the guard (keyed on `[device] bench = true`, as J built it).
   - Lines wrap at about 100 characters. Every quote was checked word for word against lane_plan.md and CHECKLIST 24.
5. **Landed.**
   - A.8: a hazard run's faults land in both FRAM logs (`UART_init`, `UART_resp`), and one run fills UART_resp's 10-entry log, overwriting older entries (the default history length is 10, asy_print_log.py:434). The website shows this before the run is confirmed (buildgen/definitions.py:103).
   - The tests_hardware/README.md hazard-run item now says to read and save both logs first.
6. **Step 142, partly done.** I checked tests_hardware for U35's new instruments: the commits 76b2d7f, e9fd1c7 and 7a7d01a, and the queue_c list. Two rows are added:
   - The torn-write bench run (bench/test_end_to_end_timing.py, `--allow-persistence-write`, 2 flash writes per README's budget table, owner quote as the test carries it, no twin, per twin_record.json).
   - The lone BMP3xx under general calls (flash/test_bus_concurrency.py:268 plus the sweep's broadcast assertion at :239, zero wear, runs under `--twin`).
   - Loop lag on the bench and the UART hazard run already had rows.
   - **Left for U37 (queue_c's owner):** the silicon arm of the memory gates, the two-image GC proof, the read-stagger trigger timestamps, the speed-probe bands, and the interaction, recombination and rung cells. None has a single tests_hardware instrument, and I wrote nothing that is not true in the tree. The silicon arm would also need a planted image that costs a flash cycle, which is the owner's question under the least-wear rule.
7. **Nothing stale from J.** J's SCD30 counts match the C.8 and A.4 text. No document names the removed gate test file. CLAUDE.md already says `UARTLinkDriver`.

**Checks (all rc 0, zero memory markers; all logged in RUNS.md)**
- 25 doc and reader files, including both new guards: 1069 passed.
- The 8 pre-commit checks, after `git add`: 143 passed.
- The 17 repo-wide scans on bbf808d: 880 passed, rc 0.
- test_tunables_register is green after the Part N edit. Its earlier red is from Z's and J's records (`config.flush_slice_bytes`); I did not re-run it on the base.
- I wrote the start line for the first long run late, at its exit, and marked it so.
- Logs and edit scripts are in S/u35/laneD/d2e/.

**For the lead:** no allow-list line is orphaned (vocabulary and citations stay green with their only-shrinks checks).

**Modes:** documentation only, so nothing changes in any mode (STA, AP, Silent, Off, USB) or on any device. No wear question arises.

nothing of mine is running