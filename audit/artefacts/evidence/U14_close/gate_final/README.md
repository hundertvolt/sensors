# U14 final local gate, tree f664ffd (identical to the U14 commit outside audit/)
- `coverage_f664ffd.log.gz`: scripts/test.sh --coverage alone (622 s), its own vmstat `vmstat_coverage.log.gz`; nothing else
  ran beside it.
- gate_v8 with NOCOV=1 after it: lint, typecheck (both scopes, cold cache), test.sh at -1 and 32768, twins dev and wozi
  (`gate_times.txt`, `vmstat.log.gz`). The chained command hit the harness's 30-minute background limit, which stopped
  the arzi, klkizi, schlafzi and grkizi twins and npm (`cut_off_time_limit/`); their rerun was stopped by a container
  restart (`cut_off_restart/`); the third run passed (`tw_*.log.gz`, `npm_test.log.gz`, `vmstat_rerun.log.gz`).
  Neither cut-off log holds a failure: each ends mid-run on passing lines.
