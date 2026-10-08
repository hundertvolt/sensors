# The humidity helpers' water pair (owner, 2026-10-07: 'Adapt the humidity to the verified range')

The repo's earlier research (planning survey item 33, harvest ALGO.S03/PAR.N085) identified the legacy formula as the
Magnus form over water, 7.6/240.7 being the published supercooled-water pair (ice 9.5/265.5), and recorded −30..40 degC as
its domain (SPECIFICATION.md G.2, "each formula keeps its legacy form"). No stored source has the legacy 237.4. Checked
today: the published base-10 pair is 7.5/237.3 with 6.1078 hPa (Tetens 1930, coefficients per Murray 1967), as ECMWF's
`thermofeel` (`thermofeel.py`, citing Murray 1967) and `pythermalcomfort` (`jos3_functions/thermoregulation.py`,
0.61078 kPa * 10**(7.5 x / (x + 237.3))) implement it. Change: 237.4 -> 237.3, everything else legacy. A first pass moved to
the WMO-No. 8 form (-45..60 degC, `humidity_fail_first.log`); it was replaced by the legacy form with the published pair,
which the stored decisions require (`humidity_murray_fail_first.log`: 5 tests fail on the WMO code before the change).
Both passes showed the saturated round trip landing a rounding step above 100 %: `rel_humidity()` keeps a 0.001 % margin.
