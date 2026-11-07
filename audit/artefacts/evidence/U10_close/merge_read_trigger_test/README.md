# The merged U10 tree's read-trigger collector test failure

The first full run on the merged lanes (5ba961e, both GC stages) failed
`tests_scripts/test_buildgen_generate.py::test_a_device_whose_readers_declare_no_read_triggers_collects_none`
("asy_sgp40_driver.py": `def get_trigger_starters` found in the copy).

Root cause: lane A wrote the test when no driver in `src/` declared read triggers; its helper only
added methods. Lane C then gave the BMP3XX, ISL29125 and SGP40 readers their own
`get_trigger_starters()`, so the "declares none" copy still declared three. The test was right about
its intent and wrong about its input. Fix (0b9993d): the helper strips every driver's declaration
before adding the named ones; 99/99 after. `gate_failure_gc-1.log` is the failing output (identical
at gc.threshold 32768).
