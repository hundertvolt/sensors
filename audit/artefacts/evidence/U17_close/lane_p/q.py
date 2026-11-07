import gc
l = [bytearray(2) for _ in range(40)]
gc.collect(); a0 = gc.mem_alloc()
while len(l) > 2:
    l.pop()
print("pop", len(l), gc.mem_alloc() - a0)
v = memoryview(bytearray(4))
gc.collect(); a0 = gc.mem_alloc()
v[0:2] = b"ab"
print("mv assign", gc.mem_alloc() - a0)
d = bytearray(8); p = bytearray(b"wxyz")
gc.collect(); a0 = gc.mem_alloc()
d[2:4] = memoryview(p)[1:3]
print("d from mv slice", gc.mem_alloc() - a0, d)
