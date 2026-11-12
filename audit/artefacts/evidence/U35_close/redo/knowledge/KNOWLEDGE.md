# The knowledge list (PLAN.md section 0; started in R0, 2026-11-02)

One line per item the finishing plan removes: what it was, why it went, the commit holding its code. Decision 7
decides which lines also go into the docs (R4). Facts that need no removal to be worth keeping stay in their sources.

## R0

- The twin record's committed copy (`tests_hardware/twin_record.json`, 122 entries) and its staleness test
  (`tests_scripts/test_twin_record.py`): went because the committed copy and its hash-pinning test were audit
  machinery, and the only red in CI; the runner stays and R3 records once on the final tree. Code: `497b3eda`.
  Its 35 exception reasons are kept in `twin_record_exceptions.md`.
