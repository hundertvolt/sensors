# Lane I's whole-suite sweep: 23 files red in the lane worktree, all an absent built artefact

`sweep1.txt` (lane I's per-file sweep of its own worktree, `sweep.sh`) lists 23 failing files beside the
webserver read-timeout-then-cap check (root-caused at U11, SF-U11-07). Every one of the 23 builds a full device
graph and stopped at `ImportError: no module named 'frozen_html'`: lane worktrees had no `frozen_modules/`, which
`scripts/test.sh` builds before its MicroPython tier. Reproduced on the same worktree (`repro_*.log`). The same
files pass in every gate on the merged trees (gate logs of U13: 90/90 files at both stages). Lane briefs since
U14 say to report such a file for the lead to run instead of reading it as a result.
