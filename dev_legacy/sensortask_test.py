import asyncio
import asy_i2c_driver
import asy_spi_driver
from system_service import SystemService
from asy_fram_manager import AsyFramManager
from asy_scd30_driver import SCD30_Reader
from asy_bmp3xx_driver import BMP3xx_Reader
from asy_sgp40_driver import SGP40_Reader
from print_log import PrintLog
from machine import WDT
from micropython import const

_MAX_I2C_ERR = const(5)

async def sgp_comp_callback() -> List[int | float | None]:
    data = await scd_reader.get_data()
    if data is None:
        return [None, None]
    return [data.Temp, data.Hum]

async def foo():
    return True

watchdog = None #WDT(timeout = 8000)

dbg_level = PrintLog.level_err()

i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)
i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000)
spi0 = asy_spi_driver.SPI(0, 2, 3, 4)

fram = AsyFramManager(spi0, 5, max_size=0x40000, debug=PrintLog.level_info())
sysfunct = SystemService(foo, watchdog=watchdog, fram=fram, debug=dbg_level)

scd_reader = SCD30_Reader(i2c1, 11, trigger_sec=3, max_i2c_err=_MAX_I2C_ERR, fram=fram, debug=dbg_level)
bmp_reader = BMP3xx_Reader(i2c0, max_i2c_err=_MAX_I2C_ERR, fram=fram, debug=dbg_level)
sgp_reader = SGP40_Reader(
    i2c1,
    sgp_comp_callback,
    fram_storage=fram,
    fram_ntp_callback=foo,
    max_i2c_err=_MAX_I2C_ERR,
    debug=PrintLog.level_info(),
)



# Main Function
async def main():

    await fram.setup()


    await sysfunct.start_timers(sysfunct.get_timer_starters() +
                                scd_reader.get_timer_starters() +
                                bmp_reader.get_timer_starters() +
                                sgp_reader.get_timer_starters())



    evtloop = asyncio.get_event_loop()
    evtloop.create_task(sysfunct.start_and_check_tasks(sysfunct.get_task_starters() +
                                                       scd_reader.get_task_starters() +
                                                       bmp_reader.get_task_starters() +
                                                       sgp_reader.get_task_starters()))
    
    


    while True:
        #print(await scd_reader.get_dict_data())
        #print(await scd_reader.get_dict_cfg())        
        #print(await bmp_reader.get_dict_data())
        #print(await bmp_reader.get_dict_cfg())
        #print(await sgp_reader.get_dict_data())
        #print(await sgp_reader.get_dict_cfg())
        
        print(await sysfunct.get_error_counter())
        print(await fram.get_error_counter())
        print(await scd_reader.get_error_counter())
        print(await bmp_reader.get_error_counter())
        print(await sgp_reader.get_error_counter())
        
        
        #await sysfunct.reset_error_counter()
        #await fram.reset_error_counter()
        #await scd_reader.reset_error_counter()
        #await bmp_reader.reset_error_counter()
        #await sgp_reader.reset_error_counter()
        
        await asyncio.sleep(3)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()