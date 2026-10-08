import asyncio
import _sensortask_scenarios as sc
import asy_system_service, asy_scd30_driver
sc.register_for_device("wozi")
async def go():
    module, _w = await sc._boot("wozi", web_host="127.0.0.1", web_port=0)
    r = sc._scd30_readers(module)[0]
    bus = sc._scd30_bus(r)
    print("before log", [e for e in bus.log if e[1:2] == (0x61,)][:10])
    try:
        print("COVERED", await sc._scd30_cycles(module), r._scd._i2c_scd30.i2c_device.device_address, len(bus.log), sc._scd30_commands(r, 0x0300))
    except AssertionError as e:
        print("ASSERT", e)
    print("first", bus.log[0], type(bus.log[2][2]))
    print("queue", bus.read_queue_by_address.get(0x61))
    print("errlog", await r.get_error_counter())
asy_system_service.asyncio = sc._AsyncioWaits()
asy_scd30_driver.asyncio = sc._AsyncioWaits()
asyncio.run(go())
