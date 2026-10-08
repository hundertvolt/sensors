import asyncio, socket
print(bytearray(b"\x00\x01") != b"\x00\x01", bytearray(b"\x00\xff") in (b"\x00\x01", b"\x00\xff"), [0, 1] != b"\x00\x01")
print((28).to_bytes(2, "big"))
class A:
    async def f(self, x):
        await asyncio.sleep(0)
        return x + 1
class B(A):
    async def f(self, x):
        try:
            return await super().f(x)
        finally:
            print("finally ran")
print(asyncio.run(B().f(1)))
a = socket.getaddrinfo("127.0.0.1", 23456)[0][-1]
s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s1.bind(a)
s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s2.bind(a)
    print("bound!?")
except OSError as e:
    print("OSError", e)
s1.setblocking(False)
try:
    s1.recv(512)
except OSError as e:
    print("recv empty:", e)
