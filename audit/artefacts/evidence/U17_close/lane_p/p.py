import gc
b = bytearray(b"abcdefgh")
try:
    b[5:] = b""
    print("shrink ok", b, len(b))
except Exception as e:
    print("shrink err", type(e), e)
try:
    del b[3:]
    print("del ok", b)
except Exception as e:
    print("del err", type(e), e)
d = bytearray(6)
mv = memoryview(d)
mv[1:3] = memoryview(b"xyz")[0:2]
print(d)
d[3:5] = memoryview(bytearray(b"QR"))
print(d)
print(memoryview(memoryview(d))[0:2])
l = [bytearray(2) for _ in range(4)]
gc.collect(); a0 = gc.mem_alloc()
del l[2:]
print("del list", len(l), gc.mem_alloc() - a0)
gc.collect(); a0 = gc.mem_alloc()
x = bytearray(b"abcdefgh")
gc.collect(); a1 = gc.mem_alloc()
x[3:] = b""
print("shrink alloc", gc.mem_alloc() - a1, len(x))
