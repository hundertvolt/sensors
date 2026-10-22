U35 P1 hand-back (lane P, branch audit/u35-p, worktree S/wt-u35p, base f3fff0e). This was the lane's first block, not its final one. Everything is committed and the tree is clean.

**Commits:** 253f85b (steps 20+21, B87), a42e276 (steps 23+85, B88), 1856280 (steps 24-27 plus the :712 comment), 0dd3148 (step 119). Head is 0dd3148.

**Applied**
- **20, 21:** removed `_crc()`'s `poly is None` return and both `pack_into` `ValueError` catches in `add()` and `add_into()`. These catches could never fire: pack_into raises only "buffer too small" (py/modstruct.c:238-253, v1.29.0), and every buffer is sized from the CRC width. Existing tests stayed green at both stages.
- **23, 85:** `CRCBase.__init__` now checks the polynomial against the width's mask first and sets all four width fields from that result. I also corrected the length() comment.
- **22:** B87 (steps 20+21) and B88 (step 23) are Class B rows, in landing order.
- **24-27 and :712:** six trailing comments, wording per R-18, including step 25's "kept: it guards the copy into a caller's buffer". Line count stays 1211.
- **119:** `test_residual_math_errors_return_none`, with a `_RaisingMath` stand-in. src/math_helpers.py is untouched.

**Check-only on the base (R-33), all landed:**
- 12: asy_base_classes.py:400-431.
- 13: SPECIFICATION.md:4301-4302. Wording there is "self.pr.name/self.name always agree"; same meaning as the packet.
- 14: asy_config_manager.py:71/75/342/360, KeyError only at :369/:443, no TypeError or AttributeError.
- 15: asy_fram_manager.py:454-497.
- 16: :507-620 (pack :614, unpack :553, signed-age comment :567).
- 17: no timestamp-pack row exists, so nothing to retire. W33/W35 are the SGP backup-without-timestamp warnings, not that row.
- 18: asy_fram_driver.py:45-114.
- 19: verify_present :477-502 uses wait_for_ms, with no id_error and no E98. The lost path is now `_report_chip_lost()` after release.
- 42: test_asy_fram_manager.py:970/989/1077/1769, negative age at :3003, the removed tests are absent.

**Seen failing and bites**
- 23/85: all five new or extended cases (three widths, above-mask, negative poly) failed on the old constructor. Each helper line was also bitten on its own in S/u35/laneP/bite23: add_into on an exact-size buffer (:420) and check_from (:421) both failed.
- 119: the guard passed at once. I bit it 10 times (5 excepts × narrowed to ValueError or to ArithmeticError) in S/u35/laneP/bite119. Every bite failed, naming the escaping error and the function.

**mpy-cross (default and -march=armv6m):**
- asy_crc_checks: bytes change, 1920 → 1879, lines 193 → 186.
- asy_uart_comm: byte-identical. Output is in S/u35/laneP/mpy/.

**Runs (all exit 0, zero MemoryError and zero "memory allocation failed")**
- Paired base/head, 3 rounds each:
  - test_asy_crc_checks: 0.04/0.04 → 0.04/0.04
  - test_math_helpers: 0.02/0.02 → 0.02/0.03
- Head at -1/32768:
  - fram_manager 5.72/6.35, print_log 0.41/0.48, framing_codecs 0.77/0.82
  - scd30 22.71/29.65, sgp40 9.12/11.01, uart_driver 6.39/10.56
  - uart_comm 62.66/63.66, uart_comm_hazard 104.92/109.78, twin uart_link 55.38/65.22
- 40 tests_scripts readers (P2.2's list plus grep extras): 1979 passed. The 6 skips are test_build_firmware.py:710's opt-in RUN_SLOW_FIRMWARE_BUILD, one per device.
- Before each commit: the 12 checks (797 passed), ruff, both main mypy passes clean. uart_changelog and suppression_form also green.

**Disk-full window (17:05-17:15)**
- My only run in the window was the twin uart_link rerun (pid 30289); its output was lost. I repeated it as pid 14366 (green) and redid the rebuild first (rebuild3).
- All four commits predate the window, and git status is clean.
- A separate earlier red (19650, 16:58) was a stale build/generated_src after my src edits. Rebuilt with S/u23/rebuild.sh and rerun.

**Red checks:** none of mine. The only warning was the datasheets submodule not being initialised (test_citations.py:236), which is environmental.

**Relay:** one line under ## D, giving E.5.1 the CRC removals (SPECIFICATION.md:5232, :5256).

**Facts owed to D, for D2's E.5.1 work:**
- E.5.1's uart paragraph says "six statements" but lists four. All six now carry comments; the two not listed are `_read_answer_header()`'s and `_recv_train()`'s rx-None halves.
- math_helpers' "domain-guarded blocks" are now reached by the stand-in test (step 119's E.5.1 row).

**Decisions (agent, 2026-10-21)**
- Trailing comments on the UART lines, to keep the line count and the bytecode.
- The :783 premise reads "sized or checked against _dest_size()". It covers both destinations: the PieceBuffer is sized from it, and a caller's buffer is checked at :279-281.
- "Unreachable in its rx half" for the two `err or rx is None` sites.
- B87's claim is limited to "the module's CRC classes". A direct CRCBase built with a mismatched format would now raise.
- `length() == 0` added to the negative-polynomial case too, since it is the same defect.

**Silent-failure scan (all classes, my files): nothing new.**
- Silently degrading an invalid polynomial to pass-through is inherently safe: every construction uses a default polynomial, and buildgen/buildspec.py:71 allows only "none" and "crc16".

**Effect per mode:** none in STA, AP, Silent, Off or USB, on any device. dev is the one UART device.

**Orphaned allowlist rows:** none.

**State for P2:** it starts from 0dd3148 with the tree rebuilt. P2's files (fram_manager, chip fake, system_service copy, twin fram) are untouched.

Nothing of mine is running.
