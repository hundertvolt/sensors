import asyncio
print(asyncio, asyncio.__file__ if hasattr(asyncio, "__file__") else "no file")
orig = asyncio.sleep_ms
asyncio.sleep_ms = lambda ms: orig(ms)
print("assigned ok")
asyncio.sleep_ms = orig
import socket
try:
    socket.foo = 1
    print("socket assignable")
except Exception as e:
    print("socket:", type(e).__name__, e)
