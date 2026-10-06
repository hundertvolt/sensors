# The inline-table skip in test_buildgen_validate.py

`test_device_wiring_value_must_be_a_string_reference[value3]` (a dict wiring value) skips with "an inline table
can't be produced by this fixture writer": the case is listed but never checked, at every stage since it was written.
Probe `zz_probe_inline_test.py` (copied into `tests_scripts/`, run with pytest at 1a721b9, then removed) writes the
TOML text directly: `led_target = { target = "neopixel" }` and `led_target = {}` are both refused with "must be a
string instance reference" (2 passed). The product behaviour is right; the gap is the test's. U7 replaces the skip
with the real check.
