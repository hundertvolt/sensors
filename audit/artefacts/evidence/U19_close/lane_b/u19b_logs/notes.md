# lane B working notes (scratch)
- B1 WIP a40160a. Before figures (test_asy_base_classes.py, 172 tests): e 0.51 s, f 0.59 s, settrace(cov) 0.93 s.
  After B1 (173): e 0.45 s, f 0.67 s, settrace 0.97 s. Zero MemoryError/"memory allocation failed" (case-sensitive).
- Seen failing first (b1_seen_failing.txt): 3 inverted + lock test (4 FAIL). Window draft: ImportError on base (window_seen_failing.txt).
- Window draft tests: u19b_logs/window_tests.py (8 tests), planted defects each caught (plant_window.py); no-alloc test uses heap_lock
  (settrace frame alloc skipped while locked, py/profile.c:126-129), samples mem_alloc outside the lock; deviation to report.
- Cross reds from B1: ntp:388, wifi:748, readiness_gates:289 & :307 (marker for invalid store). Fault/warning stale row (G).
- Findings: (1) webserver _get_settings_flat() drops a settings group's fields when its module sends the marker (class 4/7) -
  SYSTEM already sends marker today; (2) SensorReaderConfig._get_mgr_cfg serves defaults when cfgmgr.writable is False
  (unreadable file at boot) while SystemService marks unavailable (class 4) - proposal: return None when not writable;
  (3) runtime pair W CFG_KEYS -> E CFG_GET_RAISED (merge raising after warning) hidden from scan by nested if, as at base.
- Re-entrancy: no _set_lock holder calls get_dict_cfg; GET callbacks: BMP3XX get_config_snapshot (session), SCD30 _config_snapshot
  (session), ISL29125 get_config_snapshot + _check_divergence (configure / _switch_range -> _threshold_lock -> session).
