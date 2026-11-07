# Duration of a full gc.collect() in the neopixel test process after its tests have run, and the heap it walks.
import gc, time
exec(open("tests/test_asy_neopixel_driver.py").read().replace('if __name__ == "__main__":', "if False:"))
for name, fn in list(globals().items()):
    if name.startswith("test_") and callable(fn):
        try: fn()
        except Exception: pass
alloc = gc.mem_alloc(); free = gc.mem_free()
t0 = time.ticks_us(); gc.collect(); d = time.ticks_diff(time.ticks_us(), t0)
print("alloc_kb", alloc // 1024, "free_kb", free // 1024, "collect_ms", d / 1000, "alloc_after_kb", gc.mem_alloc() // 1024)
