# U13 final local gate, tree 9c0ed3d (identical to the U13 commit outside audit/)
- `coverage_9c0ed3d.log.gz`: scripts/test.sh --coverage alone at normal priority (639 s, finished before the gate below started); one nice-19 integration
  agent ran beside it. Its vmstat record was overwritten by the gate below, which wrote into the same directory.
- gate_v8 with NOCOV=1 (17:44-18:08): lint, typecheck (both scopes, cold cache), test.sh at -1 and 32768, npm, the twin
  suite on six devices; `gate_times.txt`, `vmstat.log.gz`.
