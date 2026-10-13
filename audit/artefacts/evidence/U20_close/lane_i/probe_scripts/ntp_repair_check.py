import asyncio, sys
sys.path.insert(0, "ext")
import asy_spi_driver
from _sensortask_scenarios import fram_fake_class
from _generated_module import boot_generated

async def main(offline, cfg):
    asy_spi_driver._SPI = fram_fake_class("wozi")
    module = __import__("sensortask_wozi")
    module, wdt = await boot_generated(module, "wozi", offline_ntp=offline, cfg_path=cfg)
    log = await module.ntp.cfgmgr.pr.get_log()
    print("RESULT", "offline" if offline else "plain", log, "unpersisted", module.ntp.cfgmgr.unpersisted, "faulted", module.ntp.cfgmgr.faulted)
    with open(cfg + "config_NTP.cfg") as f:
        print("FILE", f.read())

asyncio.run(main(sys.argv[1] == "1", sys.argv[2]))
