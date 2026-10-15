# The concurrency scenario's real write was refused (SF-U11-06)

`tests/_webserver_concurrency_scenarios.py` `_real_config_write()` PUT `{"SCD30": {"Interval": n}}`; SCD30's field is
`MeasInterval`, so every write answered "Invalid" under a 200 and the two scenarios asserting "GET polling survives a
real write" passed without any write. Step 1 made the helper return the field's answer and the scenarios assert
`(200, "Valid")`, keeping the wrong name: on the base tree (d5cdead) both scenarios failed with every answer `None`
(`concurrency_real_write_fail_first.log`). Step 2 named `MeasInterval`: 20/20 on the base tree
(`concurrency_real_write_base_fixed.log`), zero memory markers. No other test sends that name against a real SCD30.
