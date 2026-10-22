# U19 close evidence

Each folder holds a lane's working logs and probes (paths inside name the scratch worktrees they ran in; files over
100 KB gzipped). Scratch copies of product source - overlays, planted mutants and the tests run against an older
module - were left out: by name, and by content (any file sharing 90% or more of its lines with one tracked file);
the lane reports describe each plant, and its log here shows the failure.

| folder | what it shows | cited by |
|---|---|---|
| `lane_ws/` | the webserver: the new tests seen failing on the old module (`logs/ws1_seen_failing_on_old_src.log`, `seen_failing_r*`), the route-level file at both GC stages and on settrace before and after (OF-71), the test-order probe behind OF-34 | SF-U19-01, -03..-06, -10, -17 |
| `lane_wc/` | the new connection-level file: 24 planted defects, each failing its test (`u19wc_plants/P*.log`); the EAGAIN and ceiling probes; `wc_hammer/` the file 10 times on each of the standard and settrace binaries beside six nice-19 CPU hogs (per-run logs, `summary.txt`), and 10 + 10 unsaturated before it (`summary_unsat.txt`) | SF-U19-01, -02, -04 |
| `lane_c/` | the config manager, envelope and result-word swap: each file before, after the constants and after the swap at both GC stages, the producer test's bite, mypy at each step | SF-U19-11, -12 |
| `lane_b/` | the base classes: `HourlyWindowCounter`'s tests and planted window defects, the unavailable marker seen failing (`marker86_seen_failing.txt`), the L0 checks before and after, coverage before and after | SF-U19-07, -08, -09 |
| `lane_s/` | the three drivers: each marker test seen failing, before and after at both GC stages and on settrace, the SCD30 store mutation, the integration files the change reaches | SF-U19-07 |
| `lane_g/` | the build chain: the generator and definitions tests seen failing, the L0 runs on the lane, the API base and the integration tree, the Any baseline before and after | the catalog and generator rows |
| `lane_r/` | the REST reference, the Microdot digest pin and the result-word scan: each seen failing, runtimes before and after; `apibase/` lint and both typecheck scopes on the API base; `apirun0/` the base's first run | SF-U19-12, -13, -14 |
| `lane_j/` | the website mock: the mock tests seen failing, the simulated definitions run, lint, typecheck and tests | the mock rows |
| `lane_i/` | the integration tier: the per-device scenarios before and after at both GC stages and on settrace (`m_*`) | SF-U19-15 |
| `lane_d/` | the SPEC lane's tag lists before and after and its spec-test runs | the SPEC rows |
| `lane_e/` | the docs lane's removed BACKLOG lines | the BACKLOG rows |
| `lane_own/` | the owner answers' end-to-end Wi-Fi test: the four planted defects each failing it (`p1..p4`), the file at both GC stages and on settrace | OR150 |
| `lead_int/` | the lead's merged-tree runs: the MicroPython tier at both stages on the integration tree (`int*_d`, `int*_t`), the twins and npm (`tn1`), the L0 run after the site rebuild (`l0_b120`), the split asserts (`split_runs`), the serving-demand budget on every device (`budget_runs/`; `seq/` holds dev's valid run, 81/81 at a demand of 68,172 B, and a planted 68,000 B budget failing exactly the demand test; the top-level `dev.log` and `plant_dev.log` are a harness error: the dev file twice at once in one worktree, sharing `tests/_tmp`, with the plant unread since the script's own directory comes first on the path) | SF-U19-16 |
| `gate/` | the close gate on `2391e63` (lint, both typecheck scopes, both GC stages, the six twins, npm; `vmstat.log`), then the coverage leg run alone on `7efb5f2`, the final tree (a SPEC re-wrap later): `coverage.log`, `vmstat_cov.log`; `gate_times.txt` the timeline | the commit's local-gate paragraph |
