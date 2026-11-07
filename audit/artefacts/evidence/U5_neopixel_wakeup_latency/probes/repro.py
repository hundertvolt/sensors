# A synchronous stall longer than the test's settle wait makes the IO-woken overlay task lose the race.
import time, asyncio
exec(open("tests/test_asy_neopixel_driver.py").read().split("def test_")[0])

def trial(stall_ms):
    driver = make_driver(led_overl_bri=42)
    async def scenario():
        tasks = await _start_all_tasks(driver)
        driver.on()
        asyncio.create_task(_block(stall_ms))
        await asyncio.sleep(0.05)
        await _cancel_all(tasks)
    async def _block(ms):
        time.sleep_ms(ms)
    run(scenario())
    w = _pixel(driver).writes
    return w[-1][0] if w else None

for ms in (0, 20, 40, 60, 80, 120):
    print(ms, trial(ms))
