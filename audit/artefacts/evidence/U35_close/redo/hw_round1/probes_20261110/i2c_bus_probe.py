"""Bench probe (bench, 2026-11-10, lead relay 05:45 item 3), e8d48fab's drivers mounted: (a) on i2c1 the ISL29125 finishes
transactions inside the SCD30's 50 ms waits (every machine.I2C call timed); (b) on i2c0 the BMP3XX at x32/x32 gives a
valid sample after one computed wait, no STATUS poll. Reads only on the SCD30 (no NVM command); BMP3XX registers are RAM."""
import array
import asyncio
import time

import machine

from asy_bmp3xx_driver import BMP3XX_I2C
from asy_i2c_driver import I2C, I2CDevice
from asy_scd30_driver import SCD30_I2C

wdt = machine.WDT(timeout=8000)
CAP = 3000
t0s = array.array("i", [0] * CAP)
t1s = array.array("i", [0] * CAP)
adr = bytearray(CAP)
ops = bytearray(CAP)  # 1 writeto, 2 readfrom_into, 3 other
n_rec = [0]
T_BASE = time.ticks_us()


class Recorder:  # stands in for the wrapper's machine.I2C and times every call on the wire
    def __init__(self, bus):
        self._bus = bus

    def _rec(self, op, a, t0):
        i = n_rec[0]
        if i < CAP:
            t0s[i] = time.ticks_diff(t0, T_BASE)
            t1s[i] = time.ticks_diff(time.ticks_us(), T_BASE)
            adr[i] = a
            ops[i] = op
            n_rec[0] = i + 1

    def writeto(self, a, buf, stop=True):
        t0 = time.ticks_us()
        try:
            return self._bus.writeto(a, buf, stop)
        finally:
            self._rec(1, a, t0)

    def readfrom_into(self, a, buf, stop=True):
        t0 = time.ticks_us()
        try:
            return self._bus.readfrom_into(a, buf, stop)
        finally:
            self._rec(2, a, t0)

    def __getattr__(self, name):
        return getattr(self._bus, name)


def quant(v):
    v = sorted(v)
    n = len(v)
    return (v[0], v[n // 2], v[-1]) if n else (None, None, None)


async def scd30_with_neighbour(seconds):
    i2c1 = I2C(1, 15, 14, 50000, 200000)
    i2c1._i2c = Recorder(i2c1._i2c)
    scd = SCD30_I2C(i2c1)
    async with scd._i2c_scd30 as s, s.i2c_device as dev:
        await dev.setup()  # the zero-byte probe only: SCD30_I2C.setup() would also soft-reset the chip
    isl = I2CDevice(i2c1, 0x44)
    async with isl as dev:
        await dev.setup()
    n_rec[0] = 0
    stop = [False]
    isl_ok = [0, 0]
    meas = [0, 0, 0]  # calls, new data, faults
    sample = [None]

    async def neighbour():
        while not stop[0]:
            async with isl as dev:
                v = await dev.get_register_bytes(0x00, 1)  # device ID register (FN8424 p9)
            isl_ok[0] += 1
            if v is not None and v[0] == 0x7D:
                isl_ok[1] += 1
            await asyncio.sleep_ms(3)

    async def scd30_loop():
        end = time.ticks_add(time.ticks_ms(), seconds * 1000)
        while time.ticks_diff(end, time.ticks_ms()) > 0:
            wdt.feed()
            meas[0] += 1
            try:
                if await scd.read_measurement():
                    meas[1] += 1
                    sample[0] = (await scd.get_CO2(), await scd.get_temperature(), await scd.get_relative_humidity())
            except Exception as e:  # reported, not hidden
                meas[2] += 1
                print("I2CBUS scd30_fault", repr(e))
            await asyncio.sleep_ms(250)
        stop[0] = True

    t = asyncio.create_task(neighbour())
    await scd30_loop()
    await t
    n = n_rec[0]
    print("I2CBUS a records", n, "cap", CAP, "scd30_calls", meas[0], "new_data", meas[1], "faults", meas[2], "isl_reads", isl_ok[0], "isl_id_ok", isl_ok[1])
    print("I2CBUS a sample co2_t_rh", sample[0])
    scd_idx = [i for i in range(n) if adr[i] == 0x61]
    waits = []
    inside = []
    for k in range(len(scd_idx) - 1):
        i, j = scd_idx[k], scd_idx[k + 1]
        gap = t0s[j] - t1s[i]
        if ops[i] == 1 and gap >= 40000:  # a command written, the next SCD30 transfer after its wait
            waits.append(gap)
            inside.append(sum(1 for m in range(i + 1, j) if adr[m] == 0x44 and t0s[m] >= t1s[i] and t1s[m] <= t0s[j]))
    print("I2CBUS a scd30_waits", len(waits), "gap_us min/med/max", quant(waits))
    print("I2CBUS a isl29125_calls_inside_each_wait min/med/max", quant(inside), "waits_with_none", sum(1 for c in inside if c == 0))
    xfer = [t1s[i] - t0s[i] for i in scd_idx]
    print("I2CBUS a scd30_call_us min/med/max", quant(xfer))
    print("I2CBUS a isl_call_us min/med/max", quant([t1s[i] - t0s[i] for i in range(n) if adr[i] == 0x44]))


async def bmp3xx_x32(reads):
    i2c0 = I2C(0, 13, 12, 50000, None)
    i2c0._i2c = Recorder(i2c0._i2c)
    bmp = BMP3XX_I2C(i2c0, 0x77)
    await bmp.setup()
    await bmp.set_pressure_oversampling(32)
    await bmp.set_temperature_oversampling(32)
    print("I2CBUS b osr", await bmp.get_pressure_oversampling(), await bmp.get_temperature_oversampling())
    durs = []
    calls = []
    vals = []
    faults = 0
    for _ in range(reads):
        wdt.feed()
        n_rec[0] = 0
        t0 = time.ticks_us()
        try:
            p, t = await bmp._read()
            vals.append((p, t))
        except Exception as e:
            faults += 1
            print("I2CBUS b fault", repr(e))
        durs.append(time.ticks_diff(time.ticks_us(), t0))
        n = n_rec[0]
        calls.append("".join("w" if ops[i] == 1 else "r" for i in range(n)))
        if n >= 2:
            gaps = [t0s[i + 1] - t1s[i] for i in range(n - 1)]
            calls[-1] += ":" + str(max(gaps))
    print("I2CBUS b reads", reads, "faults", faults, "read_us min/med/max", quant(durs))
    print("I2CBUS b machine_calls_per_read:longest_gap_us", sorted(set(calls)))
    if vals:
        print("I2CBUS b first_sample_pa_degC", vals[0], "last", vals[-1])


async def main():
    print("I2CBUS freq", machine.freq())
    await scd30_with_neighbour(12)
    await bmp3xx_x32(10)


asyncio.run(main())
print("I2CBUS done")
