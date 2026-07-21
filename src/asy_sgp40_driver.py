"""Sensirion SGP40 VOC sensor driver: SGP40_I2C (chip protocol - init/self-test/reset, raw-signal
measurement with humidity/temperature compensation) and SGP40_Reader (the async framework-facing
wrapper - trigger timer, read loop, error counting, config schema, FRAM backup/restore of
voc_algorithm.py's VOCAlgorithm state), following the same SensorReader/SensorReaderConfig shape as
asy_scd30_driver.py/asy_bmp3xx_driver.py.

Verified against Sensirion's SGP40 datasheet (datasheets/sgp40/, version 1.2 - Feb 2022): I2C
address 0x59, command bytes/timings (Table 8), CRC-8 (poly 0x31, init 0xFF - see crc_checks.py),
temperature/humidity-to-ticks conversion (Table 10), and the general-call soft-reset sequence
(Table 17). See BACKLOG.md for the full review write-up.

Shared contract: every method returns a well-defined value (None/False, or an all-None namedtuple),
never raises - except SGP40_I2C's raw bus-transaction calls (a NAK/timeout OSError from
`I2CDevice` is allowed to propagate, per src/README.md section 2's I2C carve-out); every call into
SGP40_I2C from SGP40_Reader already wraps a full read/write sequence in its own try/except.
"""

import asyncio
import math
import time
from collections import namedtuple
from struct import unpack_from

from machine import Timer
from micropython import const

from asy_i2c_driver import I2CDevice
from base_classes import Lockable, SensorReaderConfig
from config_manager import make_dict
from crc_checks import CRC8, CRC32
from voc_algorithm import VOCAlgorithm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

    from asy_fram_manager import AsyFramChunkTimestampedBuffer, AsyFramManager
    from asy_i2c_driver import I2C

# roughly the time how often the data written to the FRAM is verified.
# less a data safety feature here but rather a check if communication and integrity is generally okay
_FRAM_VERIFY_MINS = const(60)
_MAX_NTP_WAITTIME = const(600)  # 600s = 10min

_VAL_BP = const((("BackupPeriod", "int", 1, 0, 1440, None),))
_VAL_BMAX = const((("BackupMaxAge", "int", 7200, 0, 10080, None),))
_VAL_WT = const((("WaitTimeNTP", "int", 30, 0, 600, None),))

_NAME = const("SGP40")
# VOC/Raw/TS also doubles as the full result of a read (see _read_sgp/_store_sgp) - no separate
# results type needed, unlike asy_scd30_driver.py's SCDResults, which carries derived fields SGP40
# doesn't have.
SGP40 = namedtuple("SGP40", ("VOC", "Raw", "TS"))


class SGP40_Reader(SensorReaderConfig):
    def __init__(
        self,
        i2c: "I2C",
        asy_comp_callback: "Callable[[], Coroutine[Any, Any, list[int | float | None]]]",
        fram_storage: "AsyFramManager | None" = None,
        fram_ntp_callback: "Callable[[], Coroutine[Any, Any, bool]] | None" = None,
        max_i2c_err: int = 5,
        cfg_path: str = "",
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(
            SGP40(None, None, None),
            max_i2c_err,
            _NAME,
            _VAL_BP + _VAL_BMAX + _VAL_WT,
            cfg_path=cfg_path,
            fram=fram_storage,
            history_length=history_length,
            debug=debug,
        )
        self.sgp = SGP40_I2C(i2c)
        self.trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_timer = Timer()
        self.backup_counter = 0
        # real values are always set by _init_sgp() before read_loop() ever reads these
        self.voc_init = 0
        self.voc_write = 0
        self.comp_callback = asy_comp_callback  # expects [Temperature, Humidity]
        if fram_storage is None or fram_ntp_callback is None:
            self.ts_storage = None
        else:
            self.ts_storage = fram_storage.get_timestamped_chunk(
                VOCAlgorithm.get_params_memsize(), fram_ntp_callback, crc=CRC32()
            )  # timestamped backup storage (FRAM)
        self.last_backup: int | None = None
        self.restored_from: int | None = None
        self.reset = False

    def start_asy_read(self) -> asyncio.Task[bool]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_loop())

    def start_timer(self) -> None:  # voc algorithm needs 1s period fixed
        self.trigger_timer.init(
            period=1000,
            mode=Timer.PERIODIC,
            callback=lambda b: self.trigger_event.set(),
        )

    def stop_timer(self) -> None:
        self.trigger_timer.deinit()

    def get_task_starters(self) -> list["Callable[[], asyncio.Task[Any]]"]:
        return [self.start_asy_read]

    def get_timer_starters(self) -> list["Callable[[], None]"]:
        return [self.start_timer]

    async def get_mem_status(self) -> tuple[int | None, int | None]:
        return self.last_backup, self.restored_from

    async def get_data(self) -> SGP40:
        data = await self._get_meas_data()
        return SGP40(*data)

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(_NAME, _VAL_BP + _VAL_BMAX + _VAL_WT)

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log(_NAME)

    async def reset_voc(self, flag: bool) -> None:
        if flag:
            self.reset = True

    async def _init_sgp(self) -> bool:
        await self.pr.setup()  # required for all logged warnings and errors
        self._err_cnt_internal = 0
        self.backup_counter = 0
        self.voc_init = 0
        self.voc_write = 0
        try:
            await self.sgp.setup()
        except Exception as e:
            await self.pr.err_s(_NAME, "Error in initial setup:", e, errno=10)
            return False  # error

        if self.ts_storage is None:
            self.pr.one(_NAME, "initialized without storage")
            return True  # no storage configured

        cfg_values = await self.cfgmgr.get_int_values(_VAL_BP + _VAL_WT)
        if cfg_values is None or len(cfg_values) != 2:
            await self.pr.err_s(_NAME, "Error reading config data!", errno=11)
            return False  # error

        if cfg_values[0] > 0:  # backup verification period setting
            await self.ts_storage.set_verify(
                int(math.ceil((10 * _FRAM_VERIFY_MINS) / cfg_values[0]) * 0.1)  # SGPBackupPeriod
            )

        if cfg_values[1] >= 1:  # more than 1s waittime for ntp
            if cfg_values[1] > _MAX_NTP_WAITTIME:  # limit if more than 10min
                cfg_values[1] = _MAX_NTP_WAITTIME
            self.voc_init = cfg_values[1]  # SGPWaitTimeNTP
            self.voc_write = cfg_values[1]  # SGPWaitTimeNTP
        self.pr.one(_NAME, "initialized with storage")
        return True

    async def _check_storage(
        self,
    ) -> "tuple[AsyFramChunkTimestampedBuffer | None, bool, bool, tuple[int, int, int] | None]":
        if self.ts_storage is None:
            self.voc_init = 0
            self.voc_write = 0
            return None, False, False, None  # no storage configured at all

        cfg_values = await self.cfgmgr.get_int_values(_VAL_BP + _VAL_BMAX + _VAL_WT)
        if cfg_values is None or len(cfg_values) != 3:
            await self.pr.err_s(_NAME, "Error reading config data!", errno=12)
            return None, False, False, None

        serialize = False
        deserialize = False

        # restore part
        if self.voc_init > 0:  # not yet initialized
            self.pr.evt(_NAME, "VOC Backup laden Trigger")
            self.voc_init -= 1  # countdown init timer
            deserialize = True

        # backup part
        self.backup_counter += 1
        if cfg_values[0] > 0 and self.backup_counter >= (60 * cfg_values[0]):
            self.backup_counter = 0
            serialize = True
        self.pr.all(_NAME, "Backup counter:", self.backup_counter, "Trigger:", 60 * cfg_values[0])

        if self.backup_counter >= 100000:
            self.backup_counter = 0
            # counts seconds, resets at 86400 = 1 day, give it some more space

        buf = self.ts_storage.get_buffer() if serialize or deserialize else None

        # explicit unpack-then-repack (not tuple(cfg_values)) so mypy sees a real 3-tuple, matching
        # the declared return type, without a runtime-unsafe typing.cast (see module docstring)
        backup_period, backup_maxage, wait_ntp = cfg_values
        return buf, serialize, deserialize, (backup_period, backup_maxage, wait_ntp)

    async def _run_restore(
        self,
        buf: "AsyFramChunkTimestampedBuffer | None",
        deserialize: bool,
        cfg_values: tuple[int, int, int] | None,
    ) -> bool:
        if not deserialize or self.ts_storage is None or buf is None or cfg_values is None:
            return False  # no buffer / no trigger

        res, ts, age = await self.ts_storage.read_into(buf)
        if not res:  # not valid / no backup
            await self.pr.wrn_s(_NAME, "Kein Backup gefunden!", wrnno=10)
            self.voc_init = 0
            return False

        if ts is None:
            await self.pr.wrn_s(_NAME, "Backup ohne Zeitstempel geladen", wrnno=11)
            self.voc_init = 0
            ts = -1  # means valid data, no timestamp
        else:  # backup has valid timestamp
            if age is None:
                if self.voc_init > 0:
                    self.pr.evt(_NAME, "Backup mit Zeitstempel gefunden, NTP Wartezeit:", self.voc_init)
                    return False
            else:
                self.pr.one(_NAME, "Backup mit Zeitstempel geladen")
                self.voc_init = 0
                if cfg_values[1] > 0 and age > (60 * cfg_values[1]):  # SGPBackupMaxAge
                    await self.pr.wrn_s(_NAME, "Backup ist zu alt", wrnno=12)
                    return False

        self.restored_from = ts
        return True

    async def _run_backup(
        self,
        buf: "AsyFramChunkTimestampedBuffer | None",
        serialize: bool,
        cfg_values: tuple[int, int, int] | None,
    ) -> None:
        if not serialize or self.ts_storage is None or buf is None or cfg_values is None:
            return  # no buffer / no trigger

        self.pr.evt(_NAME, "Backup Trigger.")
        if cfg_values[0] > 0:  # SGPBackupPeriod -  backup verification period setting
            current_verify = await self.ts_storage.get_verify()
            desired_verify = int(math.ceil((10 * _FRAM_VERIFY_MINS) / cfg_values[0]) * 0.1)  # SGPBackupPeriod
            if current_verify != desired_verify:
                await self.ts_storage.set_verify(desired_verify)

        if self.voc_write > 0:
            self.voc_write -= 1
        require_ntp = self.voc_write > 0

        self.pr.evt(_NAME, "Schreibe Backup.")
        ntp_synced, ts, res = await self.ts_storage.write_into(buf, require_ntp=require_ntp)

        if require_ntp and not ntp_synced:  # no write due to no timesync yet
            # set backup counter to retry serialization in self._read_sgp()
            self.backup_counter = 60 * cfg_values[0]  # SGPBackupPeriod
            self.pr.all(_NAME, "Backup NTP Wartezeit:", self.voc_write)
            return  # no write error

        if not res:  # no data was written for other reason
            await self.pr.err_s(_NAME, "Schreibfehler beim Backup!", errno=13)
            return  # don't continue due to error

        if require_ntp:  # (ntp_synced and require_ntp) and res must have been True here
            self.voc_write = cfg_values[2]  # SGPWaitTimeNTP
            self.last_backup = ts
            self.pr.evt(_NAME, "Backup mit Zeitstempel geschrieben.")
            return

        if ntp_synced:  # require_ntp was false from here on, but res was True
            self.voc_write = cfg_values[2]  # SGPWaitTimeNTP
            self.pr.evt(_NAME, "Backup wieder mit Zeitstempel geschrieben.")
        else:
            await self.pr.wrn_s(_NAME, "Backup ohne Zeitstempel geschrieben.", wrnno=13)
        self.last_backup = ts
        return

    async def _read_sgp(
        self, buf: "AsyFramChunkTimestampedBuffer | None", serialize: bool, deserialize: bool
    ) -> tuple[SGP40, bool, bool]:
        if self.reset:
            self.pr.evt(_NAME, "Reset Trigger")
            self.backup_counter = 0
            serialize = False
            deserialize = False
            self.last_backup = None
            self.restored_from = None
            if self.ts_storage is not None:
                if not await self.ts_storage.clear():
                    await self.pr.err_s(_NAME, "Fehler beim FRAM löschen!", errno=14)

        try:  # caller-supplied callback (sensortask-*.py's own compensation source, not itself
            # promoted/audited) - could legitimately misbehave, same treatment as every other
            # caller-supplied callback in this codebase (e.g. asy_fram_manager.py's ntp_sync_callback)
            comp_data = await self.comp_callback()  # [Temperature, Humidity]
        except Exception as e:
            await self.pr.err_s(_NAME, "Kompensationsdaten-Callback fehlgeschlagen:", e, errno=18)
            comp_data = [None, None]
        if len(comp_data) != 2 or comp_data[0] is None or comp_data[1] is None:
            await self.pr.wrn_s(_NAME, "hat keine Kompensationsdaten!", wrnno=14)
            if deserialize:
                self.pr.evt(_NAME, "Initialisierung wird wiederholt...")
                self.voc_init = 1  # retry init if triggered and no compensation data is available
                self.backup_counter = 0  # no backup if restore is pending
            return SGP40(None, None, None), False, False

        try:
            timestamp = time.mktime(time.gmtime())
            (
                voc_index,
                raw,
                serialized,
                deserialized,
            ) = await self.sgp.measure_index_and_raw(
                temperature=float(comp_data[0]),
                relative_humidity=float(comp_data[1]),
                reset=self.reset,
                buf=None if buf is None else buf.get_data_buf(),
                serialize=serialize,
                deserialize=deserialize,
            )
            self.reset = False
            self.pr.all(_NAME, "gelesen")

            if deserialize:
                if deserialized:
                    self.pr.one(_NAME, "Restore erfolgreich angewandt")
                else:
                    await self.pr.err_s(_NAME, "Fehler beim Deserialisieren!", errno=15)

            if serialize:
                if serialized:
                    self.pr.evt(_NAME, "Backupdaten erfolgreich erstellt")
                else:
                    await self.pr.err_s(_NAME, "Fehler beim Serialisieren!", errno=16)

        except Exception as e:
            voc_index = raw = timestamp = None
            serialized = False
            await self.pr.err_s(_NAME, "Lesefehler:", e, errno=17)
        return SGP40(voc_index, raw, timestamp), True, serialized

    async def _store_sgp(self, data: SGP40) -> None:
        if data.VOC is None or data.Raw is None or data.TS is None:
            return  # don't run on invalid data
        await self._set_meas_data(data)
        self.pr.all(_NAME, "Daten gespeichert")

    async def read_loop(self) -> bool:
        if not await self._init_sgp():  # init sensor at startup
            return False  # break and restart if init fails
        while True:
            await self.trigger_event.wait()  # wait for read trigger event
            self.pr.evt(_NAME, "sensor trigger")
            buf, serialize, deserialize, cfg_values = await self._check_storage()
            deserialize = await self._run_restore(buf, deserialize, cfg_values)  # check for available backup data
            data, compensated, serialize = await self._read_sgp(buf, serialize, deserialize)  # read data
            if not await self._error_check(data, _NAME, condition=compensated):  # check and count errors
                return False  # break and restart if too many errors
            await self._store_sgp(data)  # store data in result buffer
            await self._run_backup(buf, serialize, cfg_values)  # store backup if data was issued


class SGP40_DeviceSession(Lockable):  # lock for consecutive i2c communication and self._command_buffer
    def __init__(self, i2c_device: I2CDevice) -> None:
        super().__init__()
        self.i2c_device = i2c_device


class SGP40_I2C:
    def __init__(self, i2c: "I2C", address: int = 0x59) -> None:
        self.i2c_sgp40 = SGP40_DeviceSession(I2CDevice(i2c, address))
        self._command_buffer = bytearray(2)
        self.crc = CRC8()
        self._measure_command = bytearray(b"\x26\x0f\x80\x00\xa2\x66\x66\x93")
        self._voc_algorithm: VOCAlgorithm | None = None

    async def setup(self) -> None:
        async with self.i2c_sgp40 as sgp40:  # device session
            async with sgp40.i2c_device as i2c:  # bus session
                await i2c.setup()
        await self.initialize()

    async def initialize(self) -> None:
        # Reset to an unconfigured state and bring up with sensible defaults. Only the serial-
        # number read and self-test (both real, datasheet-documented commands, Table 8) gate
        # success - the previous feature-set check (command 0x202F) isn't in the datasheet's
        # command table, isn't done by Sensirion's own or DFRobot's reference drivers, and has a
        # known real-hardware unreliability report upstream; dropped rather than kept as a
        # spurious extra failure mode on the restart-after-disturbance path (see BACKLOG.md).
        async with self.i2c_sgp40 as sgp40:  # device session
            self._command_buffer[0] = 0x36
            self._command_buffer[1] = 0x82
            serialnumber = await self._read_word_from_command(sgp40, delay_ms=3)
        if serialnumber is None:
            raise RuntimeError("No sensor response!")
        if serialnumber[0] != 0x0000:
            # word[0]==0 isn't documented by Sensirion (no structural breakdown of the 3-word ID
            # given) or replicated by any other reference driver checked - unverified, inherited
            # from Adafruit; kept since it's observed working on deployed hardware (see BACKLOG.md).
            raise RuntimeError("Serial number does not match")

        async with self.i2c_sgp40 as sgp40:  # device session
            self._command_buffer[0] = 0x28
            self._command_buffer[1] = 0x0E
            self_test = await self._read_word_from_command(sgp40, delay_ms=500)
        if self_test is None:
            raise RuntimeError("No sensor response!")
        # Datasheet Table 13: only the high byte is the pass/fail marker (0xD4 pass, 0x4B fail) -
        # the low byte is explicitly documented as "ignore", not guaranteed zero. Checking the full
        # word against 0xD400 (inherited from the deployed driver) would spuriously fail whenever
        # real hardware returns a non-zero low byte, which the datasheet allows.
        if (self_test[0] >> 8) != 0xD4:
            raise RuntimeError("Self test failed")
        await self._reset()

    async def _reset(self) -> None:
        # True I2C general-call reset (datasheet Table 17): a single data byte 0x06 sent to the
        # reserved general-call address 0x00, broadcasting a reset to every device on the bus that
        # supports it - not a command sent to the SGP40's own address. Not every device needs to
        # ACK a general call, so a NAK (OSError) here is expected, not a real failure.
        async with self.i2c_sgp40 as sgp40:  # shared-bus lock: a general call affects every device on it
            try:
                sgp40.i2c_device.i2c.writeto(0x00, b"\x06")
            except OSError:
                pass
        await asyncio.sleep(1)

    @staticmethod
    def _celsius_to_ticks(temperature: float, buf: bytearray | memoryview) -> None:
        # Temperature-to-ticks, datasheet Table 10: 25C->0x6666, -45C->0x0000, 130C->0xFFFF.
        temp_ticks = int(((temperature + 45) * 65535) / 175) & 0xFFFF
        buf[0] = (temp_ticks >> 8) & 0xFF  # most significant byte
        buf[1] = temp_ticks & 0xFF  # least significant byte

    @staticmethod
    def _relative_humidity_to_ticks(humidity: float, buf: bytearray | memoryview) -> None:
        # Relative-humidity-to-ticks, datasheet Table 10: 50%->0x8000, 0%->0x0000, 100%->0xFFFF.
        humidity_ticks = int((humidity * 65535) / 100 + 0.5) & 0xFFFF
        buf[0] = (humidity_ticks >> 8) & 0xFF  # most significant byte
        buf[1] = humidity_ticks & 0xFF  # least significant byte

    async def get_raw(self) -> int | None:
        # recycle a single buffer
        async with self.i2c_sgp40 as sgp40:  # device session
            self._command_buffer = self._measure_command
            # 100ms: >3x margin over the datasheet's 30ms typ/max measurement duration (Table 8)
            read_value = await self._read_word_from_command(sgp40, delay_ms=100)
            self._command_buffer = bytearray(2)
        if read_value is None:
            return None
        return read_value[0]

    async def measure_raw(self, temperature: float = 25, relative_humidity: float = 50) -> int | None:
        # Humidity/temperature-compensated raw gas value (datasheet Table 9, command 0x260F).
        mv = memoryview(self._measure_command)
        mv[0] = 0x26
        mv[1] = 0x0F  # compensated read command
        self._relative_humidity_to_ticks(relative_humidity, mv[2:4])
        if await self.crc.add_into(self._measure_command, 2, start=2) is None:
            return None
        self._celsius_to_ticks(temperature, mv[5:7])
        if await self.crc.add_into(self._measure_command, 2, start=5) is None:
            return None
        return await self.get_raw()

    async def measure_index_and_raw(
        self,
        temperature: float = 25,
        relative_humidity: float = 50,
        reset: bool = False,
        buf: bytearray | memoryview | None = None,
        serialize: bool = False,
        deserialize: bool = False,
        offset: int = 0,
    ) -> tuple[int | None, int | None, bool, bool]:
        # VOC index (1-500, Sensirion Gas Index Algorithm - see voc_algorithm.py) from the
        # humidity-compensated raw signal. 100 = average of the last 24h; <100 improving,
        # >100 deteriorating air quality (datasheet Figure 8).
        if self._voc_algorithm is None:
            self._voc_algorithm = VOCAlgorithm()
            self._voc_algorithm.vocalgorithm_init()

        if reset:
            self._voc_algorithm.vocalgorithm_reset()

        raw = await self.measure_raw(temperature, relative_humidity)
        if raw is None or raw < 0:
            return None, None, False, False

        (voc_index, serialized, deserialized) = self._voc_algorithm.vocalgorithm_proc_ser_des(
            raw, buf, serialize=serialize, deserialize=deserialize, offset=offset
        )
        return voc_index, raw, serialized, deserialized

    async def _read_word_from_command(
        self,
        sgp40: SGP40_DeviceSession,
        delay_ms: int = 10,
        readlen: int | None = 1,
    ) -> list[int] | None:
        # Sends self._command_buffer, waits delay_ms, reads back readlen CRC-checked words.
        if readlen is None:
            return None
        readdata_buffer = []

        # The number of bytes to read back, based on the number of words to read
        replylen = readlen * 3
        # recycle buffer for read/write w/length
        replybuffer = bytearray(replylen)

        async with sgp40.i2c_device as i2c:  # bus session
            await i2c.write(self._command_buffer)
        await asyncio.sleep(round(delay_ms * 0.001, 3))
        async with sgp40.i2c_device as i2c:
            await i2c.readinto(replybuffer, end=replylen)

        for i in range(0, replylen, 3):
            if not await self.crc.check_from(replybuffer, 3, start=i):
                raise RuntimeError("CRC check failed while reading data")
            readdata_buffer.append(unpack_from(">H", replybuffer, i)[0])

        return readdata_buffer
