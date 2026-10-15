
######## SubagentHandback 2026-10-13T20:10:56.754Z
U24 lane U4 hand-back. Commit 77f9c2d on audit/u24-u4 (S/wt-u24u4, base 31d5bfc), all 15 files. All 15 pass at -1, 32768 and settrace (batch a3 after the D.15 reorder, plus reruns of the files edited later), with zero MemoryError or "memory allocation failed". Notes and logs are in S/u24/laneU4/ (record.txt, runs/, bite/, batch.*.txt, checks.c2.*).

**Steps**
- Applied:
  - W1 migration in all 15 files: harness run/cancel/cancel_all, the shared doubles, 13 src_const reads, private names, the new fault call shape, reset_id, and Any removed.
  - Steps 47, 99 (.039), 155, 157, 158, 159, 161, 162, 196, 197, 235, 240, 23, 27, 254, OF-43 and OF-103.
  - U24 parts only of 176, 177, 178, 179, 223–226 and 293.
  - Retired-citation and registration-shape comments (A-36): fram_integration owner tag; the scd30, scd30+sgp40 and sgp40 comments.
- Already landed: step 24 (fram_manager:1194), step 239 (spi:112-121), step 163 (i2c:100-137 and :1153).
- Verify only, all in end form: 160 (fram_manager:3018-3177), 180 (no _now() tests left; utc_now is at asy_base_classes.py:749), 8 (asy_neopixel_driver.py:47-67), 119 (asy_spi_driver.py:34-69).
- Nothing at U24 for register row :257. DrivenTime only swaps a module's `time`, but wait_for_ms sleeps on core.sleep_ms (extmod/asyncio/funcs.py:56) and the loop reads its own imported ticks (core.py:4). The recording stand-in stays, now typed without Any.

**Deviations**
- W1 and the primary steps are one commit, because they edit the same lines.
- The 256 KB part is a file-local subclass in fram_driver: no shared home is in my file set.
- The C.14.2 citations stay as they are (that change is U36's).
- Typed bindings use the idiom U1–U3 use: `_X: int = src_const(...)  # type: ignore[assignment]`.

**Seen failing first** (base reds, now green)
- fram_manager:721: old fault shape on a 4-byte read; the test now reads 41 bytes and asserts pending()==1 (:766).
- wire_trace: 9 of 9 at :116, golden firstbit 0; now _INIT_EVENT ".../8/1" (:28).
- spi: :287 (LSB), :1087 and :842 (old shape); now FakeSPI.MSB (:277), the new golden (:1089) and the new shape (:832).
- i2c: :153 (scan now [0x10, 0x50]), :517 (new busy-scan test at :516), :1179 (0x60 attached, :1184), and old shapes at :527, :564, :1277.
- notification_service: 9 parked-task failures fixed by the harness.

**Bites** (a regression planted in a scratch copy: the old test passes, the new one fails)
- fram_driver: the 256 KB test fails on the 8 KB builder; a swallowed bus-lock fault fails :1805.
- spi: a write that never forwards fails :778; a read that never fills fails :793.
- i2c: a probe that never reaches the bus fails the log assert (:419); an empty scan fails :196; a fake where every probe ACKs fails :939.
- neopixel:
  - no-op toggle fails :1179;
  - _MAX_SIGNAL_S planted at 59.0 fails :1202;
  - with the clamp removed, the wrap-absence lines fail on their own (:1091, :1108, :1122).
- Tautology test removed from allocation_budget: no failing run was needed.
- Budgets re-measured per binary (5 runs each, all identical): standard 26,496 / 20,128 B, settrace 263,232 / 238,208 B. Budgets kept.

**Red checks** (none fails on a U4 file)
- My change leaves stale allow-list rows, which the lead deletes:
  - decision-vocabulary allow-list: tests_scripts/_decision_vocab_allowlist.txt:266, :399, :402, :404;
  - citations allow-list: tests_scripts/_citation_allowlist.txt:99-101.
- Other lanes' rows: import_placement pending list (F and T), tunables (X), test_microtest :246/:253/:257 and test_const_mirrors (other lanes; zero U4 entries).

**Scan findings**
- New, fixed: class 4, swallow hiding an early raise. spi:439 swallowed __aenter__'s own "not set up" RuntimeError (bite: :440 fails).
- New, fixed: class 4, check that matches nothing. The infinite-colour test (neopixel:1036) could not tell a clamp from a refusal (bite: :1022 fails).
- New, fixed: fake fidelity. The i2c _PinSpy reconfigured pins passed with omitted arguments; it now forwards _OMITTED.
- Inherently safe: i2c:808 and spi:860.
- Checked with no finding: hook that raises, stale generated tree, port held by another suite, aborted or incomplete file.

**Facts owed**
- Lead:
  - Any baseline: delete pyproject.toml:459-462, 464, 470, 480-484 (11 U4 modules; trial config clean).
  - ANN401: delete pyproject.toml:299-300.
  - _NOT_YET_CLEANED: delete test_no_variant_literals.py:73-75.
  - Unfolded clone groups (they need a shared home in F's or H's files): the 256 KB part (_sensortask_scenarios:103, fram_manager, fram_driver, system_service) and _UTCValid (7 copies).
- X: no @tunable added or changed. Y: none.

**After-times over 10 %**
- fram_driver at 32768: median CPU 0.272 → 0.309 s (+14 %); wall 0.33 → 0.36 s.
- A local plain-asyncio.run variant measures 0.280 s, and the 256 KB part is within noise. So the growth is the shared harness's per-run() cost over 199 calls, which is H's file. Skipping the empty reap recovers almost nothing.
- spi: +17 % CPU at -1 (≈9 ms). All other files are within 10 %.

**Runs**: batches a1, st1, a3 and checks c1, c2 (all exits logged); one bite loop stopped by TaskStop (HEAD's unbounded run() hung on the plant) and redone; the A/B timing loops were entered in RUNS.md late. Nothing of mine is running.
