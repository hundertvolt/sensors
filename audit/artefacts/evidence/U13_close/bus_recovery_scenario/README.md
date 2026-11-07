# The bus-recovery hazard scenario catches an unlocked or split recovery

L1 (`tests/_bus_hazard_catalog.py` `scenario_bus_recovery_does_not_disturb_concurrent_siblings`, per generated I2C bus
with two or more occupants): lane I reports that its first version missed a mutant whose `clear()`/`recover()` run
without the bus lock (`laneI_no_lock_mutant_excerpt.txt`, the planted source); the scenario now starts after every
occupant's first read, holds SDA through all nine pulses (status 3) and fails dev/i2c1 and wozi/i2c1 against it.
L2 (`tests/test_digital_twin_bus_hazard_concurrency.py`, the twin recovery case): `laneT_twin_case_before_recover.txt`
shows it red on lane T's tree before lane I's `recover()` existed (fail first, both stages); lane T reports 14/14 on
lane I's source overlay and the case failing on a mutant that releases the bus lock between the clear and the
re-construction (`laneT_split_hold_mutant.diff`, overlay of 3fbac86's driver).
No run log of either mutant run is on disk; the reports are the record. Fix commits: 2965220 (lane I), 1fca2f8 (lane T).
