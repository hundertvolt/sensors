import sys
sys.path.insert(0, "digital_twin")
import asyncio
import machine
from machine import Pin
import asy_i2c_driver
from asy_isl29125_driver import ISL29125_Reader
from _tmp_scratch import TmpScratch

machine.configure_i2c_wiring("dev")
Pin.reset_registry()
i2c = asy_i2c_driver.I2C(1, 15, 14, frequency=50000)
chip = i2c._i2c.devices[0x44]
chip._lux_step = 0.0
reader = ISL29125_Reader(i2c, 6, cfg_path=TmpScratch("u15c_probe").dir("b"))

async def main():
    await reader.cfgmgr.setup()
    assert await reader._init_isl()
    for step in range(3):
        if step == 1:
            chip.simulate_brownout()
        chip.set_illumination(200.0)
        r = await reader._read_isl()
        await reader._store_isl(r)
        log = (await reader.get_error_counter())["ISL29125"]
        print("cycle", step, "lux", r[0], "ErrNum", log["ErrNum"], "ErrType", log["ErrType"], "ErrCount", log["ErrCount"])

asyncio.run(main())
