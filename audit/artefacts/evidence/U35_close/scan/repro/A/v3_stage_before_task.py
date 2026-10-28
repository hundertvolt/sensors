# V3: pre-audit write_config() stages before create_task(); a MemoryError there (D4.35).
import asyncio
import config_manager
from config_manager import ConfigManager

_VAL = (("X", "int", 1, 0, 9, None),)

async def main():
    cm = ConfigManager("v3_cfg.json", _VAL, "V3")
    await cm.setup()
    real = asyncio.create_task
    def refuse(coro):
        coro.close()
        raise MemoryError("simulated refusal")
    config_manager.asyncio.create_task = refuse
    try:
        res = await cm.write_config({"X": 5}, _VAL)
    finally:
        config_manager.asyncio.create_task = real
    print("write_config answered", res)
    print("served after the refusal", await cm.get_dict(["X"]))
    await cm.flush_pending()
    print("file holds", open("v3_cfg.json").read())

asyncio.run(main())
