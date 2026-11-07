T3g hand-back (lane T, audit/u35-t, S/wt-u35t). One commit, b6902cd, on b7d9f31. Only scripts/_digital_twin_scenarios.py changed. Nothing is uncommitted and nothing of mine is running. I used about 57 tool calls.

**Items by verdict**
- **(h)'s bound: applied, with a deviation.** I took the brief's second option. The bound now counts entries per event.
  - Each logger may write 2 x (1 setup write + the entries its events allow). SGP40 gets 2 per failed cycle (the failure and the streak entry at asy_base_classes.py:584) plus 1 per recovery rung reached. The rung thresholds (2, 3, 4) are read by ast. WEBSERVER gets 1 per burst connection not served (`_note_drop`). Every other logger gets its setup write only.
  - The bound is exact on all six devices: SGP40 28, WEBSERVER 6, every other logger 2. All the other checks stay.
  - Why not the storm's own window: the twin's storm persists about 3 entries a second (13 in about 4.3 s), so no 627 ms rate over its own window fits.
  - I renamed the scenario to `a_bounded_fault_storm_persists_only_what_its_events_allow`, because the old name named a rate it no longer reads. The suite's `_PERSISTED_LOG_CHUNK_WRITE_MS` is no longer read by the scenarios; the CI suite keeps it.
- **(g)(a) `survives_bus_and_api_load_while_ntp_is_unreachable`: applied.** Boot 1 (AP) PUTs an SSID and NTPHost 192.0.2.1 (read by ast from `_offline_ntp_config.py`), then waits for both config files. Boot 2 runs as a station on the same state.
  - Under sensor reads and readers on every GET route, NTP must log the code the route predicts (72 with no route, 71 with one, never the other) past boot 1's count.
  - SYSTEM must not move, every route must be served, the device must still serve, and there is no reset.
- **(g)(b) `..._with_concurrent_config_writes`: applied.** Same load with the ceiling minus 1 readers, plus a writer storing a new GMTOffset every second. Every write must be Valid, the writer must end, and the last value must be in config_NTP.cfg.
- **Folds (1)-(3): not started (budget).** Facts for them:
  - Fold (3) is blocked: no `ConfigUnpersisted` field exists. `git grep -i unpersist` over src/, SPECIFICATION.md and digital_twin/ finds nothing. `_ERR_CFG_FILE_WRITE` is 33 (src/asy_config_manager.py:62). setpriv is at /usr/bin/setpriv and has `--bounding-set`.
  - Fold (1): `_WRN_HTTP_PEER_RESET` is 48 (src/asy_webserver_service.py:104). It is a warning, not an error.
  - Fold (2): `_ERR_CHIP_GET` is 12 (bmp3xx:38, isl29125:39, scd30:84). The marker is `UNAVAILABLE` (src/asy_base_classes.py:72).

**Seen failing first (plants in their own scratch trees, arzi, at -1 and 32768 alike)**
- pW (the old form on a fast host's 8000 ms window): "24 writes over the 8000 ms run: {'SGP40': 28}". The new form passes on all 6 at both stages.
- pB (40 extra writes per entry): {'SGP40': (1068, 28), 'WEBSERVER': (164, 6)}.
- pN (the NOT_SENT entry swallowed): both (g) scenarios fail with "NTP logged no errno 72 ... 0, []".
- pF (a changed GMTOffset flushed once, later ones dropped): (g)(b) fails with "the last write's GMTOffset 4620 never reached the config file". The file held 3660, write 0.
- pH (the writer ignores its stop): "the writer never ended, so its answers are not all in".

**A red I root-caused:** in r1, (g)(b) failed on all 12 controls. My writer passed `len(written)` as its index, but written[0] is its own slot, so the expected last value was one step low (arzi's file held 4620; the test expected 4560). I fixed it, and r2 and r3 are green.

**Scan (my file, all classes):** one class 3/4 gap in my new code: a writer still running past the join read as a pass. I fixed it with the writer-end check, and pH bites it. Nothing else.

**Times (new scenarios, so there is no base):** (h) 10.0-11.0 s, unchanged. (g)(a) 29.3-31.2 s. (g)(b) 30.0-31.3 s. Readers unchanged in count: scenarios 60, matrix 18, errcount 134, soak 24, all rc=0.

**Checks:** ruff is clean, and the cold host mypy pass at b6902cd has 0 issues in 306 files. The 12 checks plus the scenarios reader and const_mirrors: 864 passed, 1 failed.
- The red, waiting on lane D: `test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree`. Part N has no rows for `l2.zero_think_reads_per_reader` (:146), `l2.zero_think_reader_floor` (:148), `l2.zero_think_writer_period_s` (:150) or `l2.ntp_unreachable_write_period_s` (:161).
- Relay: those four TAG lines are under `## D` (relay.md:78-81). All are estimated (agent, 2026-10-22).

**Decisions (agent, 2026-10-22)**
- A per-event bound, and the rename.
- WEBSERVER is allowed one entry per unserved connection, not per counted refusal, so a slow host's reclaim is allowed.
- The route check is a UDP connect, rewritten in the harness, which may not import tests/ or the suite.
- The writer retries a clean refusal within `_STILL_SERVING_S`.
- `_lag_load` takes an optional reader count.

**Effect per mode:** test-only. Boot 1 runs in AP and boot 2 in STA on every device. Silent, Off and USB have no change.

**Owed:**
- T4: digital_twin/README.md text for the renamed storm and the two (g) scenarios, beside T3f's five.
- The lead: T3f's 627 ms finding stands. The new bound counts per event and does not hide it.
- Allow-lists: no row orphaned.

**T4 starts** from b6902cd, clean. Left: folds (1)-(3) (fold (3) blocked as above), the README text, and the Part N rows (lane D).

**Runs** (all in RUNS.md):
- r1: 12 controls rc=1 (the index bug above); pW, pB, pN and pF rc=1 as planted.
- r2: 12 controls rc=0; pF rc=1.
- r3: 12 controls rc=0; pF and pH rc=1.
- Host mypy twice, rc=0. checks12 rc=1 (the red above). mem=0 in every run.

**Logs:** S/u35/laneT/t3g/ (runs.sum, logs/, the plant runs in ctl/, plants.py, edit1.py, r1.sh-r3.sh, commit1.txt). The control and plant trees are deleted.