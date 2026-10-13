import asyncio, sys
print(sorted(k for k in sys.modules if "asyncio" in k))
core = sys.modules["asyncio.core"]
print(core.create_task, core._io_queue.map)
print(hasattr(asyncio, "core"))
