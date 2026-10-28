# V3: the ISL29125 settle deadline against rp2's ticks period (2**30 ms, extmod/modtime.c:166-196, py/smallint.h:42)
import asyncio
import asy_isl29125_driver as m

PERIOD = 1 << 30


class RP2Time:
    # ticks_ms/ticks_diff/ticks_add exactly as extmod/modtime.c computes them on a 2**30 period
    def __init__(self):
        self.now = 5000

    def ticks_ms(self):
        return self.now & (PERIOD - 1)

    def ticks_diff(self, end, start):
        return ((end - start + PERIOD // 2) & (PERIOD - 1)) - PERIOD // 2

    def ticks_add(self, t, d):
        if not (-(PERIOD // 2) < d < PERIOD // 2):
            raise OverflowError("ticks interval overflow")
        return (t + d) & (PERIOD - 1)


class Bus:
    async_lock = asyncio.Lock()
    bus_lock = async_lock


fake = RP2Time()
m.time = fake
isl = m.ISL29125_I2C(Bus())
# one CONFIG1 write: the deadline two 16-bit cycles out, as configure() arms it
isl._settle_until_ms = fake.ticks_add(fake.ticks_ms(), 606)
t0 = fake.now
for label, dt in (("+1 s", 1000), ("+1 h", 3600000), ("+6.2 d - 1 min", (1 << 29) - 60000), ("+6.2 d + 1 min", (1 << 29) + 60000), ("+9 d", 9 * 86400000), ("+12.4 d + 1 min", (1 << 30) + 60000)):
    fake.now = t0 + dt
    print(label, "time_to_settle_ms() ->", isl.time_to_settle_ms())

slept = []


class FakeAsyncio:
    @staticmethod
    async def sleep_ms(ms):
        slept.append(ms)


class Pr:
    def all(self, *a):
        pass


class Reader:
    pass


r = Reader()
r.isl = getattr(r, "isl", isl)
r._isl = isl
r.pr = Pr()
m.asyncio = FakeAsyncio
fake.now = t0 + (1 << 29) + 60000
asyncio_real = __import__("asyncio")
asyncio_real.run(m.ISL29125_Reader._settle_wait(r))
print("_settle_wait() at +6.2 d + 1 min requested sleeps (ms):", slept)
