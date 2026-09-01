"""Manual tests, Part 2 category B (tmp_hardware_test_candidates.md items 4-5) plus
HARDWARE_TEST_PLAN.md §11.5 item 25 (a genuine phone/laptop's OS-level captive-portal
auto-detection against the DNS-only spoof - an open question §11.1's research surfaced, not
settled by reading the code alone: src/captive_dns.py has no HTTP-level redirect, only DNS
spoofing, so whether a real phone's "sign in to network" popup fires at all is genuinely unknown
until a human tries it)."""

from __future__ import annotations

from runner import confirm, confirm_pass, print_instruction, register, state_expected_outcome


@register(
    "real_sta_fail_hotspot_fallback_second_client",
    "Join the DUT's fallback hotspot with a real phone/laptop within a stated window and confirm a real DHCP lease is obtained - stronger evidence than the automated tier's own-process check.",
    "[USB+WiFi][MANUAL]",
)
def test_real_sta_fail_hotspot_fallback_second_client() -> None:
    print_instruction("This test needs the DUT already in (or about to enter) hotspot fallback mode - e.g. after PUT /networking {\"SSID\": \"\"}.")
    state_expected_outcome("a hotspot named after the DUT's configured Hostname appears in your phone/laptop's WiFi list within ~30s.")
    confirm("Trigger hotspot fallback now (or wait for it to happen organically), then press Enter once you're watching for the AP to appear")
    print_instruction("On your phone/laptop, scan for WiFi networks and join the DUT's hotspot (password: 12345678) within 60 seconds.")
    confirm("Press Enter once you've successfully joined and received a real IP address (check your device's WiFi settings)")
    confirm_pass("Did your phone/laptop receive a real DHCP-leased IP address on the DUT's hotspot?")


@register(
    "real_end_to_end_hotspot_session_real_client",
    "Join the DUT's hotspot with a real client, then load the device's webserver in a real browser - the full real path from a genuine client's perspective.",
    "[USB+WiFi][MANUAL]",
)
def test_real_end_to_end_hotspot_session_real_client() -> None:
    print_instruction("Join the DUT's hotspot (SSID = its configured Hostname, password 12345678) with a phone/laptop, within 60 seconds.")
    confirm("Press Enter once joined")
    print_instruction("Open a browser on that device and navigate to http://<gateway IP, usually 192.168.4.1>/")
    state_expected_outcome("the device's real website loads (title, styling, live measurements) within a few seconds - the same page the automated tier's test_hotspot_role_reversal.py::test_real_static_website_content_serves_over_the_hotspot_link proves programmatically, now observed by an actual human browser.")
    confirm("Press Enter once you've loaded the page")
    confirm_pass()


@register(
    "real_phone_captive_portal_auto_detection",
    "Observe whether a real phone/laptop's OS-level 'sign in to network' captive-portal auto-detection popup fires against src/captive_dns.py's DNS-only spoof (no HTTP-level redirect exists) - an open question this session's own research surfaced (HARDWARE_TEST_PLAN.md §11.1/§11.5 item 25), not settled by reading the code alone.",
    "[USB+WiFi][MANUAL]",
)
def test_real_phone_captive_portal_auto_detection() -> None:
    print_instruction("Join the DUT's hotspot with a real phone (iOS/Android) or laptop - watch closely for any 'Sign in to network' / captive portal popup during or immediately after joining.")
    state_expected_outcome("UNKNOWN - this is genuinely open. Either a popup appears (the OS's own captive-portal probe request, e.g. a GET to a known connectivity-check URL, happened to land on the DUT's real webserver root and got treated as a captive portal), or nothing appears (the DNS-only spoof isn't enough to trigger the OS's own detection heuristic). Record which one happened - this is exploratory, not a strict pass/fail.")
    confirm("Press Enter once you've joined and waited ~15 seconds to see whether a popup appears")
    print_instruction("Record what you observed (a popup appeared / no popup appeared / something else) for the project owner - this test always reports PASS since either outcome is valid data, not a failure.")
    confirm("Press Enter to finish")
