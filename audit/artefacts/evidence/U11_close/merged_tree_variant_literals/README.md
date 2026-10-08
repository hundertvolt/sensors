# The merged U11 tree failed the variant-literal check (SF-U11-07)

The full gate on 1e61c84 (both GC stages) passed every MicroPython file (89/90 files; 4045 tests) and failed two
`tests_scripts/test_no_variant_literals.py` checks: lane D's new `tests_scripts/test_stored_config_golden.py` named devices
by literal (`wozi`, `dev.toml`), and two test files cleaned by the lanes still sat on the pending list
(`gate_1e61c84_excerpt.log`). Root cause: the lanes' pre-commit list did not include that check. Fix: the two tests
iterate `DEVICE_NAMES` and select the SGP40 case by the TOML's driver; the two pending entries are removed; the check
joins every later lane brief's pre-commit list.
