import asyncio, time, os
from asy_neopixel_driver import NeopixelDriver
from asy_wifi_service import WifiConfig, WifiService
d = "tests/_tmp/probe_p3/"
for x in ("tests/_tmp", d):
    try: os.mkdir(x)
    except OSError: pass
t0 = time.ticks_ms()
pixel = NeopixelDriver(0)
conn = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), ext_led=pixel, cfg_path=d)
print("ctor", time.ticks_diff(time.ticks_ms(), t0)); t0 = time.ticks_ms()
asyncio.run(conn.setup())
print("setup", time.ticks_diff(time.ticks_ms(), t0)); t0 = time.ticks_ms()
async def sc():
    ov = pixel.start_asy_overlay()
    t1 = time.ticks_ms()
    for _ in range(300):
        await asyncio.sleep(0)
    print("300 yields", time.ticks_diff(time.ticks_ms(), t1))
    ov.cancel()
asyncio.run(sc())
print("sc", time.ticks_diff(time.ticks_ms(), t0))
