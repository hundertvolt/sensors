"""REPORT 7 item 8: the country code read from the air. For each code in CODES the radio is brought up afresh under it
and scans SCANS times; per code, the channels any access point was heard on (no SSID printed). Needs an access point on
channel 13 in range; joins nothing, writes nothing; the boot's own country returns with the closing hard reset."""

import time

import machine
import network

CODES = ("DE", "XX")
SCANS = 3
wdt = machine.WDT(timeout=8000)

for code in CODES:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    wlan.deinit()  # rp2's WLAN deinit is real (SPECIFICATION.md F.5.1): the next active(True) brings CYW43 up afresh
    network.country(code)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep_ms(500)
    heard: dict = {}
    for _ in range(SCANS):
        wdt.feed()
        for ap in wlan.scan():
            heard[ap[2]] = heard.get(ap[2], 0) + 1
        wdt.feed()
    print("SUM country code=%s read_back=%s channels=%s ch13=%d" % (code, network.country(), sorted(heard.items()), heard.get(13, 0)))
print("DONE=1")
machine.reset()  # ends the session in a hard reset, restoring the product and its stored country
