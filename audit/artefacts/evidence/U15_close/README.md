# U15 close evidence

Each folder holds the logs a scan finding or review row cites, copied from the lanes' and the lead's working notes
(none over 200 KB, so nothing is compressed). Paths inside the logs name the scratch worktrees they ran in.

| folder | what it shows | cited by |
|---|---|---|
| `bmp3xx_fail_first/` | the BMP3XX unit file on the previous driver (90/134, 44 failing) and on lane A's (134/134) | SF-U15-01 |
| `scd30_fail_first/` | the SCD30 unit file on the old driver (42/124, 82 failing) and lane B's final runs of its files at both GC stages | SF-U15-02 |
| `isl29125_fail_first/` | the ISL29125 unit file before (199/236, 37 failing) and after lane C's first commit, and the twin auto-range file at HEAD (15/19) and after (19/19) | SF-U15-04, SF-U15-05 |
| `isl29125_brownout_and_expiry/` | lane C's second commit: the three new unit tests and one twin case failing first, the twin file after, the brownout probe | SF-U15-10, SF-U15-11 |
| `sgp40_fail_first/` | the SGP40 unit file on the unchanged driver (95/144, 49 failing) and after, at both GC stages, before and after the docs commit | SF-U15-07, SF-U15-08 |
| `lane_a_runs/` | lane A's runs of the base, BMP3XX, hazard-tier and system files, on its tree and the merged lane tree; its scan notes | the hazard-tier and scan rows |
| `lane_d_doc_checks/` | lane D's L0 checks and mypy passes across its docs commit, with the other lanes' reds they showed | the lead's integration rows |
| `integration/` | the lead's cross-lane step: the tests_scripts runs before and after, the seven MicroPython files at both GC stages, the typecheck, the allow-list regeneration, the cadence script's first form | the integration rows, A-48 |
| `gate_final/` | the close gate on 279b9d1 (the U14 fix under U15's code): lint, both typecheck scopes, scripts/test.sh at -1 and 32768, npm, the six twins, then the coverage run alone; gzipped logs, the two scripts and their times | the commit's local-gate paragraph |
