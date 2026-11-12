# blocks_t4.md: the sections written after the 656fc82 snapshot (recovered 2026-10-26)
[The snapshot copy, S/u35/briefs/blocks_t4.md, holds "Both blocks", T4a items 1-6 and T4b items 1-2. Line numbers refer
to the lost heads.]

## T4a amendment (lead, 2026-10-23)
7. The twin's FRAM image save (B2b2_final.md item 2): `save_state()` (digital_twin/_fram_chip.py:274-286) writes the
   [rest of the sentence lost; from the summary: the twin FRAM image save limited to the chip's used span, 66.1 MB ->
   274 KB per dev run, host wear (CLAUDE.md's host-wear rule); T4a landed it in 95e3b95.]

## T4a amendment 2 (lead, 2026-10-23): B2c's values and its two leftovers
[Header lines lost; from the summary: B2c's values applied: `_SOAK_CYCLES = 80`, `_MEM_TREND_TOLERANCE_SD_MULTIPLIER =
4.0`, `_MEM_SAMPLE_INTERVAL_MS = 100`, gc.collect() kept; the old setting (20 cycles at 3.0) caught 0 of 12 planted leak
boots; with the new values a planted leak turns Run 11 red on dev at both stages and the tree stays green. The owner
accepted the cost (owner, 2026-10-23: "Question 1: This is okay, go ahead.").]
8. Run 5b (`scripts/_digital_twin_ci_suite.py:1338-1359`): B2c found its "nothing" branch never taken, 0 of 80 lost,
   because Run 5 now stops by the stop file after NTP and two read cycles, so no chunk write is ever cut; the comment
   still names the cut-mid-write case. A check that meets its case only by timing luck is not kept as such: either
   Run 5b cuts a chunk write deterministically through the twin's own tear or power-loss model, seen failing on a
   planted non-atomic restore, or, where `tests/test_digital_twin_fram_crash_points.py` already proves every cut
   point, Run 5b's comment and message state what it proves and cite that file. Take the conservative option, logged.
   [T4a landed: Run 5b requires Run 5's exact log entries and count.]
9. M.PROC.024 (2), not run by B2c: with Run 11 at 80 cycles, the twin suite on the 2**30-period Unix build, the wrap
   landing inside Run 11's window, one device per GC stage, in B2b2's form (`S/u35/laneB/b2/ticks30_batch.py`).

## T4b amendment (lead, 2026-10-23)
3. CR's review row: `tests/test_digital_twin_run_generic_integration.py:818` asserts only that a `CFGMGR_WIFI` line was
   printed (a log assertion on presence only): number and type of exactly one entry per event, its goal kept, the bite
   shown. Any other row CR2 hands back for a T4 file comes the same way.
4. CE2's routed row: `tests/test_digital_twin_run_generic_integration.py:507` runs `runner._test_kbd_traceback(...)`
   through `tests/_untraced.py`'s `untraced()` (on audit/u35-ce, merged into the integration head before T4b starts): a
   KeyboardInterrupt delivered inside a trace call at `digital_twin/run_generic_integration.py:702` ends coverage
   tracing for the rest of the file, so every `--coverage` run exits 3 with that file's note until this lands. Seen
   first: the file's `.incomplete` note under `--coverage`; after: none, the file's tests and assertions unchanged.

## T4a2 (lead, 2026-10-23): the Run 13 red first, then T4a's rest and T4b's two small items
Continue `audit/u35-t4` at `c3d1ce6` (T4a's 95e3b95 with the integration head 0f9f07d merged in). Start state
`S/u35/handbacks/T4a_final.md` [lost].
1. Root-cause the dev twin CI red (`S/u35/laneT/t4/runs/L2_twin_dev.log:380-381`): Run 13's erasefram cell at -1
   printed WATCHDOG_WOULD_TRIGGER count=1 after BOOT_DONE, never reached its machine reset within 16 s, was killed, and
   the next boot read ResetReason 1, not 8. [Root-caused: recovered/handbacks/T4a2_final.md.]
2. T4b items 3 and 4 (small, they unblock the coverage run's exit 3).
3. Then T4a's items 3 (folds), 6 (the escalation timeout scenario and the `_UART_LOAD_REQUEST_S` plant proof) and 9
   (M.PROC.024 (2)), in that order, as far as the valve allows.

## T4b2 (lead, 2026-10-23): T4's rest after T4a2
1. T4b amendment item 3, by T4a2's plan (the run ends past the WIFI store's setup; exactly one entry of its code; a
   planted doubled entry turns it red; the per-layer rule, OR140.a (7): only that layer's entries count).
2. T4a item 3 (folds (1)-(3)), then T4a item 6.
3. T4b item 1 (the README texts).
4. T4a item 9 (M.PROC.024 (2)) if budget remains; otherwise its plan and cost.
5. T4b item 2's checks, the twin CI for dev and arzi at both stages last, zero memory markers.
[Done: item 1 (recovered/handbacks/T4b2_final.md). Rest moved to T4b3.]

## T4b3 (lead, 2026-10-23; never launched)
1. T4a item 3's folds. Fold (1), `client_gone_mid_response_is_counted`: the decision (agent, 2026-10-23, the lead's, on
   T4b2's facts): the host's send buffer grows to 4 MiB, so no frozen-site body is mid-write at the reset and the case
   meets its condition only by luck; it gets a twin knob, scoped to that scenario and off by default, that pins each
   accepted socket's `SO_SNDBUF` to its floor (rp2's lwIP send buffer is small and fixed), so a body above it is
   mid-write at the reset every time. The knob's own test proves the pin; the scenario then never skips here, and a
   planted miscount turns it red. The twin's default buffers stay as they are: whether every twin run should pin them
   is a fidelity question for the records, not this block. Folds (2) and (3) as T3g_final.md's facts give them.
2. T4a item 6 (the escalation timeout scenario and the `_UART_LOAD_REQUEST_S` plant proof).
3. T4b item 1 (the README texts), including the `boot phase:` line naming the latest in-process boot's device.
4. T4a item 9 (M.PROC.024 (2)) by T4b2's plan: B2b2's 2**30-period build, the wrap at Run 11's start offset; only the
   suite runs Run 11 needs if the suite can select them, otherwise the whole suite, one device per GC stage.
T4b item 2's twin CI for dev and arzi moves to the close (W10 runs the twin CI for every device at both stages on the
merged head; agent, 2026-10-23, to run it once rather than twice). The suite's readers and the 12 checks stay T4's.
