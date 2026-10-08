# Root cause: three timing-sensitive test failures (gate pilot 4, U13 lane I, handler agent)

README.md is the full account: per-case causal chain, threshold, verdict, fix, planted defects, and the
exposure sweep. Fix commit on audit/u11-rc: db1b8ac (test-only).
Scripts: inject_stall.py / web_inject*.py inject time.sleep_ms(D) at one chosen point inside the
interpreter (a host deschedule seen from inside); exposure_sweep.py / web_exposure.py walk every point.
planted_*.diff: the defects each fixed test must still fail on. logs/: raw runs.
