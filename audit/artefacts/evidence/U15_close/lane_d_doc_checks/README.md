# Lane D's L0 checks across its docs commit (U15)

`d2a_*` ran before the docs edits, `d2b_*` and `d2c_*` after, on lane D's tree with the other lanes merged; the
`d2_mypy_*`/`d2c_mypy_*` files are the main, scope and host mypy passes. The tunables register and lock-order checks
fail first and pass after (the new Part N rows, the `_threshold_lock` row); the reds left in `d2c_*` (decision
vocabulary, fault-or-warning pairs, import placement, setter contract, two mypy errors in
`tests/test_ntp_fram_system_integration.py`) belong to the other lanes' files and were fixed by the lead at the merge
(`../integration/`).
