All runs were foreground except the one background batch, and every one exited. Logs are in `scratchpad/u22p_runs/`.

**2026-10-08 (before the cut)**
- Baselines: 5 LED files at e/f/cov.
- Tests-first runs of the driver and notification files.
- `u22p_seen` scratch-tree runs: the old product plus the two constants alone.
- After-change runs; ruff; mypy main pass on both scopes.

**2026-10-12, P1 re-validation**
- Regenerated the device modules. 5 LED files at e/f/cov.
- 4 notification integration files at e/f. That run found the two `:240` reds, which were reported.
- Consumers at e: ticks_rollover, bus_hazard_generated, reset_call_site_invariant, the 6 `test_sensortask_*`.
- ruff; mypy, both scopes; the 12 pre-commit L0 files; driver e/f re-run. Commit `e262800`.

**2026-10-12, P2**
- Merged `audit/u22-api`; regenerated (twice).
- The two `:240` files at e/f/cov.
- `test_buildgen_definitions` (`-k`, then the whole file); `test_buildgen_generate`, `test_api_reference`,
  `test_error_catalog`.
- wozi at e three times: F4 seen failing twice, the first being my own PUT-assert bug; then after X3.
- Pixel integration file: r44 run, then `_PHASE_YIELDS` probes at 3, 2 and 1 (restored to 4).
- `u22p_seen2` (pre-W1 Wi-Fi service): the pixel integration file and wozi.
- `u22p_seen3` (HEAD driver, `_PHASE_YIELDS = 1`).
- ruff over the eight scopes; all four mypy passes. Two allocation-measurement runs of under 1 s.
- Affected L0 set, 20 files. Final 9 files at e/f/cov. Commit `7b548af`.
- Background batch, pid 11099: the 6 device files at e/f/cov on the final tree and on the before tree;
  bus_hazard_generated, ticks_rollover and reset_call_site_invariant at e/f.

Scratch trees `u22p_seen*` and `u22p_before` are removed at the end. A `ps` check showed no micropython, pytest or mypy
process left.
