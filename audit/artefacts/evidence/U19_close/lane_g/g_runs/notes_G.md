# lane G working notes (scratch)
G1 = 4fe693c on audit/u19-g (base fb0657d)
- seen failing first: g1_seen_failing_generate.txt (24 failed), g1_seen_failing_definitions.txt (6 failed)
- test_error_catalog after G1: 2 red until WS1 constants: equals_its_catalog (src/asy_webserver_service.py:96 _WRN_HTTP_PEER_CLOSED = 48, catalog gives None); live_site (W48/W60/W61/W62 no live site)
- test_ticks_wrap_scan: 17 red on base fb0657d (digital_twin/run_generic_integration.py reads ticks, not in _KNOWN_TICKS_USERS) - pre-existing, not lane G
- generated modules mypy (not gated, follow_imports=silent): 26 -> 30 errors per pair; +3 per module WS1-dependent (uptime_s kw, notification_led type, get_dropped_count), -1 explicit Any each
- timings before: generate 30.4s (137 passed), definitions 16.0s (208), error_catalog 26.5s (31)
- timings after G1: generate 34.2s (155), definitions 19.6s (214), error_catalog 23.2s
- build/generated_src regenerated in wt-u19g (lead's copy saved to g_runs/generated_src_lead_before)
- website inputs changed: definitions (2 networking rows, catalog code texts W48/W60-62 in errcount codes) -> lead rebuilds frozen website
