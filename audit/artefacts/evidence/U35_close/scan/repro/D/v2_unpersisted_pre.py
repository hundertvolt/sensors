# V2: pre-audit ConfigManager, a config write that fails: is it logged (visible) or silent?
import asyncio
from config_manager import ConfigManager

SCHEMA = (("A", "int", 1, 0, 10, None),)


async def main():
    cm = ConfigManager("v2_cfg.json", SCHEMA, "T")
    await cm.setup()
    print("valid", cm.valid)
    cm.config_file = "no_such_dir/v2_cfg.json"  # make the flash write fail (ENOENT)
    ok, res = await cm.write_config({"A": 2}, SCHEMA)
    await cm.flush_pending()
    print("write", ok, res)
    print("log", await cm.pr.get_log())


asyncio.run(main())
