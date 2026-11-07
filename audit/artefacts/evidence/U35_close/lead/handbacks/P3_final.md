U35 P3 hand-back. Lane P, branch audit/u35-p, worktree S/wt-u35p. Head **934539c** (on 83e8633). Nothing is uncommitted and nothing of mine is running. I used about 80 tool calls.

**Steps by verdict**
- **R-9: applied.** I changed src/asy_config_manager.py and tests/test_asy_config_manager.py. UART_C_PORT_CHANGELOG.md is untouched.
- **What the code does now:** one helper, `_write_text()` (:431-451), serves both write sites: `_flush_staged` (:404) and setup's write (:607-608).
  - It writes 256-character slices of the text that is already serialised, all on one handle.
  - It yields (`asyncio.sleep(0)`) before each slice and once more before the close. There is no flush() or sync.
  - The new constant `_FLUSH_SLICE_CHARS` (:71-72) carries the tag `config.flush_slice_chars = 256`.
- **The lock:** `_config_lock` (:323) is held across every yield, at :396 for the flush and at :607 for setup, which now takes the lock (new).
- **Readers of the config file:** only setup's own `json.load` (:538), at boot, without the lock. Nothing can write before it: write_config refuses until the store is valid, and setup reads before it writes.
  - GET paths (get_dict :453, `_get_values` :364) read RAM through `_current()`, take no lock and never open the file.
  - No other src/ module opens a config file. asy_webserver_service.py:524 opens only the site's .gz files.
- **A cancel at a yield:** the helper writes the rest of the document, closes the file, clears `unpersisted`, then re-raises. littlefs's own OSError is re-raised at once and never retried.

**littlefs's commit point (v1.29.0, lfs2 0x0002000b)**
- "w" opens with WRONLY|CREAT|TRUNC (vfs_lfsx_file.c:63). For an existing file, the truncate is in RAM only (lfs2.c:3146-3149). A new file is committed empty at open (:3125-3128).
- Close calls `lfs2_file_sync_` (:3252). That function is the one atomic metadata commit (:3473-3476), and it skips the commit for a file marked errored (:3251). flush() is the same sync (vfs_lfsx_file.c:170-172), so it would commit a prefix.
- A reader that opens the file mid-write gets the old document, whole. For a file created by this write, it gets an empty file.
- A power loss mid-write leaves the old document: the new blocks are not referenced, and a torn commit fails its CRC (lfs2.c:1208). For a file absent at boot it leaves an empty file, which the next boot repairs with defaults.

**Seen failing first** (on 83e8633's src):
- :3301 `(['write','close'], 860)`.
- boot write `(['open','write','close'], 860)`.
- :3399 "no loop round ran while the flush's file was open".
- :3429 "the flush ended before a slice boundary".
- :3444.
- :3440 `unpersisted` stayed True after a cancelled flush that had committed its document (seen failing before the second fix).

**Bites** (scratch copies, all deleted):
- A lock release around each yield fails :3407, `max_writers == 1`.
- A flush() after each slice fails four tests: the reader saw "torn".
- No fallback fails :3438 (JSON syntax error).
- No OSError exclusion fails :3451.
- `sleep_ms(5)` fails :2850.
- No unpersisted clear fails :3440.

**The twin:** no twin test. The twin runs on the Unix port's VfsPosix, which truncates at open (`O_CREAT | O_TRUNC`, vfs_posix_file.c:76) and writes straight through (:139). `_flash_stall` (digital_twin/_flash_stall.py:41-66) models only the stall time at close, not commit at close.

**Figures for J.6 (relayed under `## D`, with the TAG row)**
- Each slice holds at most 1 erase and 4 page programs: 412 ms at the maxima, and 400 ms for ASCII text.
- The close holds at most 4 erases and 40 pages: 1720 ms (typical 196 ms).
- The longest stretch falls from 2129 ms to 1720 ms. The common case falls from about 427 ms to 400 ms. Files of 512 B or less are unchanged.
- **Decision (agent, 2026-10-21):** `_FLASH_HOLD_MAX_MS` stays at 2129. It is not in P3's files, and it is still an upper bound. So B68's threshold does not move, and there is no changelog row.

**Allocation per flush** (Unix port, 64-bit, collection suspended for each window; the threshold does not change the volume):
- 1584-character document: 6656 B before, 9088 B after (+2432 B).
- 5280-character document: 13024 B before, 20512 B after (+7488 B).
- That is about 350 B per slice, for 7 and 21 slices. At most one slice is live at a time. There is no new whole-document copy. Zero MemoryError at both stages.

**Runs** (all mem=0; logs in S/u35/laneP/p3/logs and logs2):
- config_manager, paired base/head, seconds: -1 0.10/0.12 → 0.14/0.11; 32768 0.14/0.14 → 0.19/0.19.
- 20 importers at both stages: green.
- Twin integration, dev: 22.8 s / 23.5 s, 4 passed, 8 skipped.
- After the second fix, test_sensortask 91/91 on all six devices at both stages, -1/32768 in seconds: arzi 28.0/32.8, dev 46.2/54.7, grkizi 28.8/32.6, klkizi 28.7/32.6, schlafzi 27.9/32.4, wozi 31.4/36.3.
- The two batches have start and done lines in RUNS.md, both rc=0.

**Red checks**
- **test_bus_hazard_multi_device.py:1095 (lane V's file).** "8 of 33 looks found a text no write stored", at both stages. The test assumes the write has no suspension point (:1089-1090), and the posix files it uses do not commit at close. It needs a commit-at-close model, for example my `_LittlefsOpen`.
- **test_tunables_register.** It needs D's Part N row for `config.flush_slice_chars`.
- **test_twin_record** was not run; it is expected red.
- ruff and both main mypy passes are clean.

**Silent-failure scan, new findings in my file (class 5, USB mode, all devices)**
- A KeyboardInterrupt while a flush is parked at a yield leaves the handle to gc's finaliser (vfs_lfsx_file.c:95). The finaliser commits a prefix, and the next boot repairs the file with defaults and lists it in ConfigFaults.
- A MemoryError inside the fallback can also commit a prefix. The slice it allocates is a small, fixed size.
- If the fallback's close fails, its OSError replaces the cancel.

**Effect per device and mode**
- **Devices:** all six persist config, so the effect is the same on each; only the file size matters.
- **Modes:** STA, AP, Silent and Off take the same path, including boot's validation (repair) write and the absent-file defaults write.
- **USB:** the same, plus the residual above.

**Facts owed**
- **D:** relay lines 45-46 name stale text at SPECIFICATION.md:6420, :9482-9483 and :11574.
- **V:** the :1095 test.

**P4 starts from:** 934539c with a clean tree. Owed to P4: R-10, re-running the 20 importers at both stages after the second fix, the readers, the 17 scans and P's final mpy-cross compare. The current one is in S/u35/laneP/p3/mpy/compare.txt: code changes only in setup, `_flush_staged`, the class body and the new `_write_text`.