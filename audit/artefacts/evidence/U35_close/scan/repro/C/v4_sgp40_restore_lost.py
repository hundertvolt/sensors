# V4: pre-audit SGP40 - a measurement that fails on the restore cycle; is the restore re-armed before the next backup?
import asyncio
import asy_sgp40_driver as m


class Pr:
    def evt(self, *a): pass
    def all(self, *a): pass
    def one(self, *a): pass
    async def err_s(self, *a, **k): print("  err_s:", a, k)
    async def wrn_s(self, *a, **k): print("  wrn_s:", a, k)


class Src:
    async def get_data(self):
        class D:
            Temp = 22.0
            Hum = 45.0
        return D()


class FailingChip:
    async def measure_index_and_raw(self, **k):
        raise OSError(5)  # one EIO on the cycle that applies the backup


class Buf:
    def get_data_buf(self): return bytearray(256)
    def get_buf(self): return bytearray(264)


class Store:
    def get_buffer(self): return Buf()


class Cfg:
    async def get_int_values(self, schema): return [1, 7200, 30]  # BackupPeriod 1 min, BackupMaxAge, WaitTimeNTP


class Reader:
    pass


r = Reader()
r.pr = Pr(); r.sgp = FailingChip(); r.ts_storage = Store(); r.cfgmgr = Cfg()
r.temperature_source = Src(); r.temperature_field = "Temp"; r.humidity_source = Src(); r.humidity_field = "Hum"
r.reset = False; r._reset_algo_applied = True; r._reset_fram_cleared = True
r.last_backup = None; r.restored_from = 1234
r.voc_init = 0  # what _run_restore() leaves after loading a dated backup (asy_sgp40_driver.py@25caf528 :386-388)
r.backup_counter = 5


async def main():
    data, compensated, serialized = await m.SGP40_Reader._read_sgp(r, Buf(), serialize=False, deserialize=True)
    print("restore cycle:", data, "compensated", compensated, "-> voc_init", r.voc_init, "backup_counter", r.backup_counter)
    restores = 0
    for second in range(1, 121):
        buf, ser, des, cfg = await m.SGP40_Reader._check_storage(r)
        restores += 1 if des else 0
        if ser:
            print("second", second, ": backup due (serialize=True), restore attempts since the failure:", restores)
            break


asyncio.run(main())
