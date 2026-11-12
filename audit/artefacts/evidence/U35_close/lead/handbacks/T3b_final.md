T3b hand-back (lane T, audit/u35-t, S/wt-u35t). Commits fd0292d and f4cba3c, on 12669ab. Nothing is uncommitted and nothing of mine is running. I used 67 tool calls and stopped at the valve.

**Steps by verdict**
- **Run 3's silent writes (LEAD NOTES 24/28): applied, fd0292d.** I planted a write storm on the real dev twin through a scratch overlay ahead on MICROPYPATH: 60 `_write()` calls through the driver in FRAMManager.setup()'s failure path. The data-phase count `silent_write_count` stayed 0, because the driver's WEL check stops each write first. The chip did see 240 WRENs at -1 and 242 at 32768.
  - Fix: the chip now counts `silent_wren_count` (listed in TEST_API).
  - The shutdown line carries `fram_silent_writes=` and `fram_silent_wrens=`. Both are required, so a line missing either fails naming it.
  - Run 3 now checks two counts against window / 627 ms x 2: landed plus silent data-phase writes, and attempts = ceil(WRENs / 2).
  - The L0 case is in the errcount file.
  - Code reading: a product-level storm puts nothing on the wire, because a chip silent from boot fails `fram.setup()` and `set_values_sync()` returns `_SV_NOT_INIT` first.
- **149: applied in part, f4cba3c.**
  - Applied: `_normal_boot_log_failures()` in the `/status` branch (no E or W entry, NTP included, no NTPSynced, per R-4), and the :505 comment (no meaning change).
  - All six devices log no E or W at a normal boot.
  - **Not done:** the boot order at the booted level (R-24). It needs the twin log's boot-phase markers located; T4 or T3c.
- **155: check-only.** It has landed: 8 CLI flags, the `@scenario` registry with 56 entries, and the drivers/needs_* flags. Nothing to do.
- **125 (f)-(i) and folds (1)-(3): not started** (budget).

**Seen failing first and bites**
- Chip test, test_digital_twin_fram.py: `AttributeError: 'FRAMChip' object has no attribute 'silent_wren_count'`.
- Parser cases, errcount file: missing field `DID NOT RAISE ValueError`, then `'ShutdownLine' object has no attribute 'fram_silent_writes'`.
- Run 3 stub cases [2-3-0] and [0-0-9] on the old suite: `AssertionError: []`.
- 149: `NameError: _normal_boot_log_failures`.
- Bite on the real twin, dev Run 3 with the plant:
  - -1: `FAIL: Run 3: the 120 FRAM write attempts its silent chip saw (WRENs / 2) stay within the persisted-log rate, 24 over the 7554 ms run`.
  - 32768: 121 attempts, also FAIL.
- T2b's stub plant: unchanged, it now fails "carries no fram_silent_writes= field". An adapted copy fails at 9 WRENs and passes at 8.
- 149 bite: a scratch copy counting N entries failed all 6 devices with "... logged N0 on a normal boot". The copy was deleted.

**Red, waits on the lead:** `tests_scripts/test_citations.py::test_the_allowlist_only_shrinks`. My comment fix orphans `tests_scripts/_citation_allowlist.txt:89` (`tests_scripts/test_digital_twin_generated_boot.py	Session 3`); delete that row. Everything else is green: ruff, the host, twin and main mypy passes, and the other 12 checks plus fake_surface_conformance and twin_fake_catalog.

**Times** (base S/wt-u35base / head, all rc=0, mem=0)
- dev `--only 3` (s): -1 7.72/7.70, 32768 7.77/7.94.
- generated_boot: 55.84/56.70 s.
- errcount: 0.90/1.27 s, from 94 to 134 cases (most are T1/T2's). Per case it is flat.
- twin_fram at 32768: 0.69/0.77 s, from 48 to 51 tests; per test +5 %.
- The other 15 readers are flat. The table is in S/u35/laneT/t3b_readers/results.tsv.

**Runs**
- t3b_twin.sh (pid 17077) rc=0, plus the plant reruns: plant2 rc=1 (the bites).
- t3b_readers.sh (pid 19345) rc=0, with the bite expected rc=1.
- Both are in RUNS.md, and the twin state dirs were deleted.

**Effect per mode:** twin and suite only, no src/ change. It applies to every device's Run 3 at both stages. The generated boot runs in AP mode (no SSID).

**Decisions (agent, 2026-10-21)**
- The attempt count rounds WRENs / 2 up.
- Both new fields are required.
- The plant sits below the init gate, because a storm above it puts nothing on the wire.

**Owed to T4/D2:** digital_twin/README.md has no text on `silent_wren_count` or on the two shutdown fields.

**Silent-failure scan, my files:** nothing new.

**T4 / T3c start state:** f4cba3c, clean. Open items:
- 149's booted boot order;
- 125 (f)-(i) and folds (1)-(3);
- T3a's folds (11), (13), (15), (16) and (18).

Scratch: S/u35/laneT/t3b_plant/ (overlay, launchers) and t3b_twin/.