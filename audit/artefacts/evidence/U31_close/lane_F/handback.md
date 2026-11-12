U31 lane F block F FINAL
Branch audit/u31-f in S/wt-u31f, nothing pushed, tree clean. Commits: 776a6b6 (OF-217, OF-218, twin network.py and its test); dfde28a (merge of audit/u31-api 75e26ef, done on your message); f387fc1 (the :56 edge and wifi_modes' sleep_ms).
Steps:
- Check 54: landed. The tag and the 5 s comment are at network.py:25-27, and the singletons are in place. A.U31.15's twin half (`_CONNECT_DELAY_S`) is unchanged.
- Check 58: landed for U31. A.U31.13 holds: no reader of `neopixel_dt`/`_frame_ms` in the twin test, and it runs in real time. M.TWIN.132's A.U22.01 L2 case is not in the tree; it is Unit U35's, not U31's.
- OF-217 applied: `connect()` on an inactive STA raises `OSError(EPERM)`. The 16 connecting tests now activate first through `_active_sta()`.
- OF-218 applied: switching the AP down drops a held STA link. The :56 edge is applied.
Decisions (agent, 2026-10-21):
(1) A dropped link reads status 1 (cyw43 LINK_JOIN), not 0, and keeps its address, as cyw43_ctrl.c:402-413, 434-437, 613-617, cyw43_lwip.c:296-298 and lwIP netif.c:1056-1086 give. A joined link with no IP (status 2) drops too. No firmware auto-rejoin is modelled.
(2) A STA `active(False)` now drops its link, address and any pending connect (network_cyw43.c:146-149, cyw43_ctrl.c:579-582). This is a new scan fix, same class, in my file.
(3) EINVAL is now raised as `OSError(errno.EINVAL)`, the one-argument form silicon uses, matching EPERM.
(4) I kept the test name `a_downed_access_point_fails_the_station_until_switched_back`, because the twin README cites it.
(5) wifi_modes' `_ScaledAsyncio` gains `sleep_ms` (R-16). Without it the service's ms waits ran unscaled: 27.69 s against a 25.77 s base.
Seen failing on base: :428 "a held link survived"; :280 (status stayed 2); :561 `[OSError(22,'EINVAL'), None, None]` plus a parked task; :587 `(22,'EINVAL')`; :573 (a deactivated STA kept its link). Bite on the own-AP guard (a planted drop of every interface): "the home network's access point took the device's own one down", 41/42.
Red, not mine:
- test_tunables_register: `wifi.*_ms is tagged but has no SPECIFICATION.md Part N row` (from <NET>; your Part N edit, R-24).
- test_twin_record: `api_sha256` of 6 device scripts (merged src; you re-record).
- Still waiting on W: tests/test_digital_twin_sensortask_integration.py:98 and tests_hardware/bench/test_hotspot_role_reversal.py:439 and :573 still read `_STA_CONNECT_POLL_S`. The integration file fails at import on my merged head, so I ran it on 776a6b6 (base plus my change).
Owed:
- D (digital_twin/README.md fidelity rows): an EPERM row (`connect_on_an_inactive_station_raises_eperm`); the AP-down row extended (link drops to LINK_JOIN, address kept); a deactivation row (`deactivating_the_station_drops_its_link_its_address_and_a_pending_connect`).
- You: close OF-217/218 in audit/sweeps/open_findings.md.
Scan, my 3 files, all classes, two new findings for you to park:
- Class 1, AP mode: the twin AP's `isconnected()` is always False; silicon answers True when the AP is up with at least one station (network_cyw43.c:324-335). Unreached by src (asy_wifi_service.py:718 short-circuits in hotspot), so inherently safe. Fix: active and stations.
- Class 1/3, STA: `status("rssi")` answers -50 when unlinked; silicon gives an unset int with the -EPERM dropped (network_cyw43.c:363-369). src is guarded (asy_wifi_service.py:841-845), but the twin cannot show that guard regressing.
- The brief's other modes were checked with nothing found.
Effect per mode:
- STA: the product activates first (asy_wifi_service.py:812-814). In teardown, `active(False)` now clears the address 2 s before `deinit()`, as silicon's DHCP stop does.
- AP: the hotspot is untouched by the knob.
- Silent: wm is green.
- Off and USB: none.
Runs and times (every run 0 memory markers, rc 0):
- Twin tests at -1/32768, s (base): nn 16.28/16.28 (15.56/15.57, +4.6 %); wm 25.65/25.82 (25.77/25.71).
- Integration file, all 6 devices on 776a6b6: within ±0.5 % of base.
- Scenarios, arzi, run with its own port-53 lock (`--exclusive-port-53`): 390/392 s, 51 passed, 0 failed, 2 skipped, 0 retried.
- Scans plus the files reading mine, one process: 1282 passed, 2 failed (above). Pre-commit checks: 787 passed. ruff and mypy (twin and main) clean.
RUNS.md lines are written; I wrote no relay lines. Logs are in S/u31/laneF/. The temporary worktree wt-u31f-pre is removed. Nothing of mine is running.
