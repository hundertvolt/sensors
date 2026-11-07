async def f(a, b=1, *, tries):
    return tries
import asyncio
try:
    asyncio.run(f(1))
except TypeError as e:
    print("TypeError", e)
print(asyncio.run(f(1, tries=3)))
try:
    raise MemoryError("injected for x")
except (MemoryError, OSError, TypeError) as e:
    if isinstance(e, MemoryError):
        print("UDPSocket", e)
