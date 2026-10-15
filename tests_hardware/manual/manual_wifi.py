"""Manual tests, an execution mode of L4 (manual/runner.py): a real phone/laptop joining the DUT's fallback hotspot,
loading its website end to end, and the captive-portal observation - the hotspot answers DNS with its own address
and redirects an unknown HTTP path to `/` (SPECIFICATION.md A.5, src/asy_captive_dns.py); what an OS makes of it is open."""

import evidence
from harness import hotspot_password
from runner import confirm, confirm_pass, observe, print_instruction, register, state_expected_outcome


@register(
    "real_sta_fail_hotspot_fallback_second_client",
    "Join the DUT's fallback hotspot with a real phone/laptop within a stated window and confirm a real DHCP lease is obtained - stronger evidence than the automated tier's own-process check.",
    "[USB+WiFi][MANUAL]",
)
def test_real_sta_fail_hotspot_fallback_second_client() -> None:
    print_instruction('This test needs the DUT already in (or about to enter) hotspot fallback mode - e.g. after PUT /networking {"SSID": ""}.')
    state_expected_outcome("a hotspot named after the DUT's configured Hostname appears in your phone/laptop's WiFi list within ~30s.")
    confirm("Trigger hotspot fallback now (or wait for it to happen organically), then press Enter once you're watching for the AP to appear")
    print_instruction(f"On your phone/laptop, scan for WiFi networks and join the DUT's hotspot (password: {hotspot_password()}) within 60 seconds.")
    confirm("Press Enter once you've joined (check your device's WiFi settings for its address)")
    confirm_pass("Did your phone/laptop receive a real DHCP-leased IP address on the DUT's hotspot? [y/N]")


@register(
    "real_end_to_end_hotspot_session_real_client",
    "Join the DUT's hotspot with a real client, then load the device's webserver in a real browser - the full real path from a genuine client's perspective.",
    "[USB+WiFi][MANUAL]",
)
def test_real_end_to_end_hotspot_session_real_client() -> None:
    print_instruction(f"Join the DUT's hotspot (SSID = its configured Hostname, password {hotspot_password()}) with a phone/laptop, within 60 seconds.")
    confirm("Press Enter once joined")
    print_instruction("Open a browser on that device and navigate to http://<gateway IP, usually 192.168.4.1>/")
    state_expected_outcome("the device's real website loads (title, styling, live measurements) within a few seconds - the page bench/test_hotspot_role_reversal.py proves programmatically, now seen by a real browser.")
    confirm("Press Enter once you've loaded the page")
    confirm_pass()


@register(
    "real_phone_captive_portal_auto_detection",
    "Observe whether a real phone/laptop's OS-level 'sign in to network' captive-portal popup fires against the hotspot's DNS answer and its redirect of unknown paths to / - open until tried; the observation is recorded as text.",
    "[USB+WiFi][MANUAL]",
)
def test_real_phone_captive_portal_auto_detection() -> None:
    print_instruction("Join the DUT's hotspot with a real phone (iOS/Android) or laptop - watch closely for any 'Sign in to network' / captive portal popup during or immediately after joining.")
    state_expected_outcome("open: a popup (the OS's connectivity probe reached the DUT's webserver and was redirected to /) or none. Either is data, recorded below.")
    confirm("Press Enter once you've joined and waited ~15 seconds to see whether a popup appears")
    text = observe("Describe what you observed (device and OS, popup or none, what it showed):")
    if text:
        evidence.save_text("captive-portal.txt", text + "\n")
