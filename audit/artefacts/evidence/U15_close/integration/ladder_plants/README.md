# Twin ladder cases against planted defects (lead, U15 integration)
`plants.py` plants one defect into a scratch copy of the integration tree; `run.sh` runs both ladder cases of
`tests/test_digital_twin_bus_hazard_concurrency.py` per plant (nice 19, own netns). P1: SGP40 has no heater-off rung.
P2: every reader runs its own bus rung (no "bus already recovered" check). P3: the bus-clear rung is skipped.
- round1 (the lane's committed tests): none passes; P1 fails case (a); P2 passes both; P3 passes (a) and times out (b).
- round2 (cases count clears and rebuilds): P1 fails (a); P3 fails (a) with "0 clear(s), 1 rebuild(s)"; P2 still passes
  both: the SGP40 reaches both rungs before the 2 s BMP3XX reaches its bus rung, so no rung is shared on the twin.
  P2 fails `tests/test_asy_base_classes.py`'s `test_two_readers_failing_on_one_bus_clear_it_once_and_rebuild_it_once`
  (`round2/P2_unit_*.log`), where the sharing is pinned; case (b)'s comment now says so.
