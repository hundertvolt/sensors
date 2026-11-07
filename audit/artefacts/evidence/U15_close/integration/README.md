# The lead's cross-lane step (U15, commits 0944abc and 6106a4b)

`tests_scripts_1.log`: the merged lanes' tree, 7 failed (stale pins: the `ContMeas` schema test, two `MeanAtmTemp`
anchors, the Run 5c exemption set, the largest PUT body on dev and wozi; and the cadence script's device literal).
`tests_scripts_2.log`: after the pins, 3085 passed, the one red left the cadence script
(`no_variant_literals_cadence.log`), fixed by `6106a4b`; `cadence_backup.py` is the script's first form. The
`mp_*` logs are the seven MicroPython files at both GC stages (`run_mp.sh`), all passing with zero memory-error
lines. `typecheck.log`: all three mypy passes clean. `vocab_before.txt`/`vocab_regen.txt`: the decision-vocabulary
allow-list before and as the check regenerated it (nine lines gone, none added); the committed list drops those nine
and the `test_buildgen_schema_ast.py` ContMeas sentence the same commit rewrote, ten in all.
