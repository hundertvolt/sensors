# U18 close evidence

Each folder holds a lane's working logs and probes (paths inside name the scratch worktrees they ran in; files over
100 KB gzipped; scratch copies of product source used as overlays were left out).

| folder | what it shows | cited by |
|---|---|---|
| `lane_w/` | the Wi-Fi service: W1 and the rest seen failing (`seen_failing_rest.txt`), the dead-flash-task test, the runs before and after at both GC stages and settrace (OF-71) | SF-U18-15..-19, -22 |
| `lane_n/` | the NTP client: N1 on a contract overlay, the rest seen failing on the base, the request constant, the twin CI suite's Run 7/8/9 runs (`lo`-only namespace) | SF-U18-12..-14, -20, -24 |
| `lane_c/` | captive DNS: the ten tests seen failing, the drain guard under injected waits, the flood and heap-failure tests seen failing | SF-U18-07..-10 |
| `lane_r/` | the resolver: the refusal and truncation tests seen failing, the mutants for R1's teardown and no-fallback behaviours | SF-U18-11 |
| `lane_u/` | `UDPSocket`: the seven console arms, the two poll rates and the failed send seen failing, the port redirect | SF-U18-05, -06 |
| `lane_k/` | the console line and the log store: OF-61's run tests seen failing, the logging layer's console lines, the heap-locked arity test, the 43 FRAM-logger files at both stages | SF-U18-01, -03, -04 |
| `lane_i/` | the integration tier: the public-resolver probe, the silent-server lock-hold tests, the LED through the flash task | SF-U18-21 |
| `lane_g/` | the build chain: grammar, special, status and settings tests seen failing; the per-device scenarios before and after (OF-71) | the catalog and generator rows |
| `lane_j/` | the website mirror: the mock tests seen failing, the simulated API-base definitions run, the put-matrix fix | OF-84..-86 |
| `lane_t/` | the shim move: the importers' ImportErrors, the five scans with a planted subdirectory file, the coverage render before and after | SF-U18-23 |
| `lane_d/` | the docs lane's notes and cite re-reads at the pin | the SPEC/BACKLOG rows |
| `lead_intrun/` | the lead's early merged-tree runs (provisional: one merge landed mid-run; its one failure is the twin test N fixed) and the full `tests_scripts` run at `032e3e5` | the integration notes |
| `gate_final/` | the close gate | the commit's local-gate paragraph |
| `gate_final/tests_scripts_overrun/` | the -1 stage's tests_scripts overrun root-caused: c11ca0a and 6bd84cf timed side by side (junit), one commit's cold typecheck then and now | OF-89 |
| `gate_final/gc_default_rerun.log.gz`, `vmstat_rerun_gc-1.log` | the -1 stage on 6bd84cf run alone: tests_scripts passed in 1075 s; the NTP resync-age test failed on the host's uptime | SF-U18-25 |
| `gate_final/final_675356e/` | the final head (the NTP test's read on its stepped clock): lint, both typecheck scopes, the -1 stage, the coverage leg (`run_lint.sh`, `run_final.sh`) | the commit's local-gate paragraph |
| `lead_intrun/uptime_sweep/` | the uptime class: the old NTP file failing at 10^8 s and passing at 30 s, the fixed one at both uptimes and both GC stages, then every `tests/test_*.py` at both uptimes (`timens_run.py` sets `CLOCK_MONOTONIC` in a time namespace) | SF-U18-25 |
| `gate_fix/` | the U18 fix's gate on fb9b92d (the fix's tree): lint, both typecheck scopes, both GC stages, the six twins, npm, the coverage leg run alone; `vmstat.log` the run queue behind the three files that passed on their second attempt at the 32768 stage | the fix commit's local-gate paragraph |
| `gate_fix/retried_alone/` | those three files alone at the 32768 stage: 83 s, 88 s and 115 s against the 240 s limit | the fix commit's local-gate paragraph |
| `fix_uart/` | the UART cancel sweeps: the failure rate on settrace at ambient load and with contention, the planted slow-host runs (`plant_*`), the failing transaction's trace, the sweep cost by budget; after the fix the contention and plant runs, both files at both stages and on settrace, the step ceiling's old form tripping and new form holding, the planted runaways (`proof/`) | SF-U18-28 |
| `fix_voc/` | the VOC suite: per-test profile, before and after at both GC stages and on settrace, the first-hit and overflow probes behind the restored counters | SF-U18-27, OF-90 |
