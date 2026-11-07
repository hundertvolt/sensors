# Wall time from request_signal(0.1) to the ramp's final black write, and from on() to the overlay write.
import time, asyncio
exec(open("tests/test_asy_neopixel_driver.py").read().split("def test_")[0])

async def ramp_once():
    d = make_driver(); tasks = await _start_all_tasks(d); px = _pixel(d); n0 = len(px.writes)
    t0 = time.ticks_us(); await d.request_signal(50, 60, 70, 0.1)
    while not d.led_overl_start.state if hasattr(d.led_overl_start, "state") else False:
        await asyncio.sleep_ms(1)
    while d.start_signal_event.is_set():
        await asyncio.sleep_ms(0)
    r = time.ticks_diff(time.ticks_us(), t0) // 1000
    d.on(); t1 = time.ticks_us(); n1 = len(px.writes)
    while len(px.writes) == n1:
        await asyncio.sleep_ms(0)
    o = time.ticks_diff(time.ticks_us(), t1) // 1000
    await _cancel_all(tasks); return r, o

async def main():
    rs, os_ = [], []
    for _ in range(int(__import__("sys").argv[-1]) if False else 60):
        r, o = await ramp_once(); rs.append(r); os_.append(o)
    rs.sort(); os_.sort()
    print("ramp_ms median", rs[len(rs)//2], "max", rs[-1], "| overlay_ms median", os_[len(os_)//2], "max", os_[-1])
asyncio.run(main())
