"""Long NeoPixel run on the light rig (REPORT 7 item 9: does a WS2812 lose its state under Wi-Fi bursts): the pixel is
set once per 10-minute window and watched through the ISL29125 (RGB, 375 lux, 16-bit) while 5 s UDP bursts go to the
gateway every minute; counts deviating samples in and outside bursts and windows that end deviated. DUR_S per run."""

import json
import os
import socket
import time

import network
from machine import I2C, Pin
from neopixel import NeoPixel

DUR_S = 1200
COLOR = (0, 16, 0)
ISL = 0x44
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=50000, timeout=200000)
px = NeoPixel(Pin(18), 1)
rgb = bytearray(6)


def green() -> int:
    i2c.readfrom_mem_into(ISL, 0x09, rgb)
    return rgb[0] | rgb[1] << 8


def median5() -> int:
    v = []
    for _ in range(5):
        time.sleep_ms(120)
        v.append(green())
    v.sort()
    return v[2]


def show(c: tuple) -> None:
    px[0] = c
    px.write()


cfg = {}
for name in os.listdir("/"):
    if name.startswith("config_") and name.endswith(".cfg"):
        try:
            with open("/" + name) as f:
                d = json.load(f)
            if isinstance(d, dict):
                cfg.update({k: v for k, v in d.items() if k in ("SSID", "PW", "Country")})
        except (OSError, ValueError):
            pass
network.country(cfg.get("Country", "DE"))
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(cfg.get("SSID", ""), cfg.get("PW", ""))
t = time.ticks_ms()
while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), t) < 30000:
    time.sleep_ms(100)
gw = (wlan.ifconfig()[2], 9) if wlan.isconnected() else None
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
payload = bytes(1024)
i2c.writeto_mem(ISL, 0x01, b"\x05")  # CONFIG1: RGB, 375 lux, 16-bit (asy_isl29125_driver.py's constants)
s = {"windows": 0, "blind_windows": 0, "persistent_windows": 0, "samples_in_burst": 0, "dev_in_burst": 0,
     "samples_outside": 0, "dev_outside": 0, "pkts": 0, "send_errors": 0, "no_wifi": int(gw is None)}
end = time.ticks_add(time.ticks_ms(), DUR_S * 1000)
while time.ticks_diff(end, time.ticks_ms()) > 0:
    show((0, 0, 0))
    amb = median5()
    show(COLOR)
    base = median5()
    span = base - amb
    s["windows"] += 1
    if span < 50:
        s["blind_windows"] += 1
    w_end = time.ticks_add(time.ticks_ms(), 600000)
    next_burst = time.ticks_add(time.ticks_ms(), 60000)
    dev = False
    while time.ticks_diff(w_end, time.ticks_ms()) > 0 and time.ticks_diff(end, time.ticks_ms()) > 0:
        in_burst = gw is not None and time.ticks_diff(time.ticks_ms(), next_burst) >= 0
        if in_burst:
            b_end = time.ticks_add(time.ticks_ms(), 5000)
            while time.ticks_diff(b_end, time.ticks_ms()) > 0:
                for _ in range(20):
                    try:
                        sock.sendto(payload, gw)
                        s["pkts"] += 1
                    except OSError:
                        s["send_errors"] += 1
                dev = abs(green() - base) * 2 > max(span, 50)
                s["samples_in_burst"] += 1
                s["dev_in_burst"] += dev
            next_burst = time.ticks_add(time.ticks_ms(), 60000)
        else:
            time.sleep_ms(120)
            dev = abs(green() - base) * 2 > max(span, 50)
            s["samples_outside"] += 1
            s["dev_outside"] += dev
    s["persistent_windows"] += dev
show((0, 0, 0))
sock.close()
wlan.disconnect()
wlan.active(False)
print("SUM L neopixel " + " ".join("%s=%d" % (k, v) for k, v in s.items()))
print("DONE=1")
