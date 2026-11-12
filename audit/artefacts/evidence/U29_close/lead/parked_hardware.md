# U29 parked hardware items (for hardware session 1; nothing ran on hardware in U29)

Every item needs the owner's go-ahead given in that session's own conversation. Before any clearing, read the
FRAM-backed error logs (`GET /status` `errcount`).

1. **The hotspot join's cause** (`l4.hotspot_role_reversal_join_attempts` stays 5; owner, 2026-10-20: "No need to change
   anything about the Hotspot retires (only find the cause, as already planned)").
   - Run `tests_hardware/bench/test_hotspot_role_reversal.py`. Its stage 6 can deactivate the WLAN permanently: follow
     `tests_hardware/README.md` before running it.
   - Record each re-verify retry note and the attempt every join needed.
   - Find the cause of a join needing a retry: nmcli's own rescan timing against `is_ssid_visible()`, and the AP's beacon
     in a capture. The firmware configures only an inactive AP (`4d06553`) and never repeats the mode switch (U18
     `f1f800e`), so the 2026-09-08 reconfiguration theory is ruled out.
2. **The other bench event retries** keep their counts (picotool load 5, association 2, heap-probe rereads 3): record the
   attempts each needed, as evidence for their recorded reasons.
3. **The silicon half of the WiFi radio rung** (OF-160).
   - `tests_hardware/device_scripts/wifi_radio_reinit_recovery.py` with `tests_hardware/bench/test_wifi_radio_reinit.py`
     calls `_recover_device()` itself.
   - The failed-hardware-call trigger (two failed joins) has its L2 case since U29.
