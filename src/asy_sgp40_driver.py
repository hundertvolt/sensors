# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
# SPDX-License-Identifier: MIT
# From adafruit_sgp40, restructured for asyncio + MicroPython - see THIRD_PARTY_LICENSES.md.

"""Sensirion SGP40 VOC sensor driver: SGP40_I2C (chip protocol) and SGP40_Reader (async wrapper - trigger timer, read loop, error counting, config schema, FRAM backup/restore of voc_algorithm.py's VOCAlgorithm state).
Same shape as asy_scd30_driver.py/asy_bmp3xx_driver.py (see SPECIFICATION.md Part C).
Verified against Sensirion's SGP40 datasheet (datasheets/sgp40/, v1.2 - Feb 2022).
"""

import asyncio
import math
from collections import namedtuple
from struct import unpack_from

from machine import Timer
from micropython import const

from asy_base_classes import DeviceSession, SensorReaderConfig, utc_now
from asy_config_manager import checked_float, make_dict, name_cfg
from asy_crc_checks import CRC8, CRC32
from asy_i2c_driver import I2CDevice
from asy_print_log import DEFAULT_LOG, LogConfig
from voc_algorithm import VOCAlgorithm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import NamedTuple

    from asy_base_classes import NtpSyncFct, TaskStarter, TimerStarter, ValueRef
    from asy_config_manager import FieldSchema
    from asy_fram_manager import FRAMChunkTimestampedBuffer, FRAMManager
    from asy_i2c_driver import I2C
    from asy_print_log import ErrorLog

    # The VOC backup's two parts: the FRAM store its chunk comes from and the NTP-sync check that
    # timestamps it (the generated module passes ntp.ntp_issynced).
    class SgpBackup(NamedTuple):
        store: FRAMManager
        ntp_synced: NtpSyncFct

else:
    SgpBackup = namedtuple("SgpBackup", ("store", "ntp_synced"))

# Codes from the global catalog (buildgen/error_catalog.json; SPECIFICATION.md Part C.7.1).
_ERR_INIT = const(10)
_ERR_READ = const(11)
_ERR_CHIP_SET = const(13)
_ERR_SOURCE = const(15)
_ERR_CFG_READ = const(26)
_ERR_SGP_ALGO_STATE = const(58)
_ERR_SGP_BACKUP_CLEAR = const(59)
_ERR_SGP_BACKUP_WRITE = const(110)
_WRN_SGP_RESTORED_NO_TS = const(33)
_WRN_SGP_BACKUP_AGE = const(34)
_WRN_SGP_WRITTEN_NO_TS = const(35)
_WRN_SGP_NO_BACKUP = const(65)

_SGP40_ADDR = const(0x59)  # datasheet 4.2: the address is fixed
_CMD_HEATER_OFF = b"\x36\x15"  # datasheet Table 14: hotplate off, measurement stopped, idle mode
_HEATER_OFF_MAX_MS = const(1)  # datasheet Table 8 maximum
# roughly the time how often the data written to the FRAM is verified.
# less a data safety feature here but rather a check if communication and integrity is generally okay
# @tunable sgp40.fram_verify_mins = 60
_FRAM_VERIFY_MINS = const(60)
_MAX_NTP_WAITTIME = const(600)  # 600s = 10min
# @tunable sgp40.backup_counter_max = 100000
_BACKUP_COUNTER_MAX = const(100000)  # see _check_storage()'s own note on the 86400s = 1 day margin
_SELF_TEST_PASS = const(0xD4)  # datasheet Table 13, high byte only (the low byte is "ignore")
# Waits between a command and its result, and after the general-call reset.
# @tunable sgp40.measure_wait_ms = 100
_MEASURE_WAIT_MS = const(100)  # >3x the datasheet's 30 ms maximum (Table 8)
# @tunable sgp40.serial_read_wait_ms = 3
_SERIAL_READ_WAIT_MS = const(3)
# @tunable sgp40.self_test_wait_ms = 500
_SELF_TEST_WAIT_MS = const(500)
# @tunable sgp40.general_call_reset_wait_s = 1
_GENERAL_CALL_RESET_WAIT_S = const(1)
_NO_TIMESTAMP = const(0)  # Backup/restore without a timestamp: the FRAM chunk's uninitialised-timestamp value (asy_fram_manager.py)
_VOC_SETTLED_SAMPLES = const(86400)  # 24 h learning time at the fixed 1 s period (Info Note VOC Index)
# Three times the longest configurable producer interval (BMP3XX SampleInterval 3600 s): a slow
# producer is never cut off (agent, 2026-10-06).
# @tunable sgp40.comp_max_age_s = 10800
_COMP_MAX_AGE_S = const(10800)
# Datasheet Table 10's range of the compensation ticks. The two checks below take any finite value a single-precision
# float holds exactly (+-2**24, Part F.1); the clamp does the rest.
_T_TICKS_MIN_C = const(-45.0)
_T_TICKS_MAX_C = const(130.0)
_RH_TICKS_MAX = const(100.0)
_COMP_T_FIELD: "FieldSchema" = ("Temp", "float", None, -16777216.0, 16777216.0, None)
_COMP_RH_FIELD: "FieldSchema" = ("Hum", "float", None, -16777216.0, 16777216.0, None)

# 0 in the special slot: an in-range value with a meaning (SPECIFICATION.md C.5).
_VAL_BACKUP_PERIOD = const((("BackupPeriod", "int", 1, 0, 1440, 0),))
_VAL_BACKUP_MAX_AGE = const((("BackupMaxAge", "int", 7200, 0, 10080, 0),))
_VAL_WAIT_TIME_NTP = const((("WaitTimeNTP", "int", 30, 0, 600, 0),))
# Command-only trigger, not a persisted config value - reuses the schema's "special-alone" field
# convention (def=None + a non-tuple special, see SPECIFICATION.md C.5). Deliberately excluded
# from get_dict_cfg()'s own schema argument below - this key is never in ConfigManager's _cache.
_VAL_RESET_VOC = const((("ResetVOC", "bool", None, None, None, True),))
_N_STORAGE_CFG = const(3)  # value count of the _VAL_BACKUP_PERIOD + _VAL_BACKUP_MAX_AGE + _VAL_WAIT_TIME_NTP batch read below
_N_SETUP_CFG = const(2)  # value count of the _VAL_BACKUP_PERIOD + _VAL_WAIT_TIME_NTP batch read below

# @web-group section=sensors submitGroup=self label="SGP40 — VOC Index" submit=true
# @web BackupPeriod section=sensors submitGroup=self label="VOC Index Backup Interval" unit="min" special:0="Backups off"
# @web BackupMaxAge section=sensors submitGroup=self label="VOC Index Backup Max Age" unit="min" special:0="Use all found backups"
# @web WaitTimeNTP section=sensors submitGroup=self label="VOC Index NTP Wait Time" unit="s" special:0="Never wait for NTP sync"
# @web ResetVOC section=sensors submitGroup=self label="Reset VOC Index" description="Only 'On' has effect. Resets the VOC algorithm and deletes the current backup." dispatch=true

_NAME = const("SGP40")
# VOC/Raw/VOCState/TS doubles as a read's full result, so no separate results type is needed - unlike
# SCDResults, which carries derived fields this driver has none of. Kept as a literal tuple, not
# `_FIELDS`: mypy's namedtuple plugin infers field names only from a literal at the call site.
SGP40 = namedtuple("SGP40", ("VOC", "Raw", "VOCState", "TS"))
_FIELDS = const(("VOC", "Raw", "VOCState", "TS"))  # kept in sync with SGP40's own fields above

# @web-group section=measurements submitGroup=self label="SGP40 — VOC Index"
# @web VOC section=measurements submitGroup=self kind=readonly label="VOC Index"
# @web Raw section=measurements submitGroup=self kind=readonly label="VOC Raw" unit="ticks"
# @web VOCState section=measurements submitGroup=self kind=readonly label="VOC Algorithm" codes=VOCState description="0 blackout (first 46 samples, index 0), 1 learning (fresh start, first 24 h), 2 learned (past the 24 h learning time), 3 restored from backup (first 24 h after the restore)."
# @web TS section=measurements submitGroup=self kind=readonly label="Timestamp" format=epoch
# @web BackupTS section=status submitGroup=maintenance kind=readonly format=epoch label="SGP40 Last Backup" special:null="None since boot" special:0="No timestamp"
# @web RestoreTS section=status submitGroup=maintenance kind=readonly format=epoch label="SGP40 Restore Timestamp" special:null="None since boot" special:0="No timestamp"

# Live cross-instance dependencies (SPECIFICATION.md Parts C.14 and L.4): the optional FRAM store (its
# logger's and, through backup=, the VOC backup's), and two per-value compensation references (Part
# L.6.3), each wireable from any instance exposing a matching field.

# datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf Table 3: fSCL max 400 kHz. A
# generator-checked build requirement, not a comment a TOML author must remember - a bus shared
# with an SCD30 is additionally held to that sensor's stricter 100 kHz tag.
# @requires bus.frequency<=400000
# @wiring fram_target FRAMManager log optional kwarg

# Per-value measurement wiring (Part L.6.3): each field resolves independently in the same
# {source, field} shape the warn_* fields use, matched by attribute name alone. Both are required,
# so an SGP40 with no compensation data at all opts in explicitly through a `_Default*`.
# @value-wiring temperature_source temperature required
# @value-wiring humidity_source humidity required

_ConstValue = namedtuple("_ConstValue", ("value",))


class _DefaultTemperatureSource:
    # Part L.6.2's wiring-defaults mechanism, opted into via [instance.wiring].temperature_source =
    # {default = true, temperature = 25}: a constant compensation fallback when no live temperature
    # source is wired.

    # 25 degC is not an arbitrary pick: it matches SGP40_I2C.measure_raw()'s own datasheet-documented
    # default (Table 9), so a defaulted source and an unwired one compensate identically.
    def __init__(self, temperature: float = 25) -> None:
        self._data = _ConstValue(float(temperature))

    # Every `_Default*` provider returns an object exposing exactly one attribute named "value" (a
    # fixed contract), so buildgen resolves a defaulted per-value field as (provider, "value").
    async def get_data(self) -> _ConstValue:
        return self._data


class _DefaultHumiditySource:
    # The same mechanism for relative humidity; 50 %RH matches measure_raw()'s datasheet default
    # (Table 9).

    def __init__(self, relative_humidity: float = 50) -> None:
        self._data = _ConstValue(float(relative_humidity))

    async def get_data(self) -> _ConstValue:
        return self._data


def _current_value(data: object, field: str, now: int | None) -> object:
    # A producer sample older than _COMP_MAX_AGE_S counts as unavailable; one without a TS (before the
    # first sync, or a constant default source) counts as current.
    ts = getattr(data, "TS", None)
    if now is not None and isinstance(ts, int) and now - ts > _COMP_MAX_AGE_S:
        return None
    return getattr(data, field, None)


def _verify_every(backup_period_min: int) -> int:
    # About one verify per hour of backups, at least every backup once a backup is longer than an hour apart
    # (owner, 2026-09-29).
    return max(1, int(math.ceil((10 * _FRAM_VERIFY_MINS) / backup_period_min) * 0.1))


class SGP40_Reader(SensorReaderConfig):
    def __init__(
        self,
        i2c: "I2C",
        temperature: "ValueRef",
        humidity: "ValueRef",
        backup: SgpBackup | None = None,
        # @tunable module.max_error = 5
        max_module_error: int = 5,
        name_ext: str = "",
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        super().__init__(
            SGP40(None, None, None, None),
            _NAME,
            _VAL_BACKUP_PERIOD + _VAL_BACKUP_MAX_AGE + _VAL_WAIT_TIME_NTP + _VAL_RESET_VOC,
            max_module_error=max_module_error,
            name_ext=name_ext,
            cfg_path=cfg_path,
            log=log,
        )
        self._sgp = SGP40_I2C(i2c)
        self._recovery_bus = i2c
        # ResetVOC is command-only (see _VAL_RESET_VOC above) - registered the same way as every
        # other module's real live-push field (agent, 2026-08-04: constant at runtime, no per-call
        # plumbing), just never persisted.
        self._push_callbacks[name_cfg(_VAL_RESET_VOC)] = self._push_reset_voc
        self._read_event = asyncio.ThreadSafeFlag()
        self._trigger_timer = Timer()
        self._backup_counter = 0
        # real values are always set by _init_sgp() before _read_loop() ever reads these
        self._voc_init = 0
        self._voc_write = 0
        self._restore_waiting = False  # a timestamped backup waits for NTP: no chunk read until the decision
        # VOCState: samples since the algorithm last started fresh or was restored, and whether it was
        # restored. The algorithm lives on SGP40_I2C, so a task restart (_init_sgp()) keeps both.
        self._voc_samples = 0
        self._voc_restored = False
        # References to each producer and the field to read off its get_data() result (Part C.14):
        # the two may be one instance or two.
        self._temperature: ValueRef = temperature
        self._humidity: ValueRef = humidity
        self._ntp_synced: NtpSyncFct | None = None
        if backup is None:
            self._ts_storage = None
        else:
            self._ntp_synced = backup.ntp_synced
            try:  # broad on purpose, matching asy_print_log.py's own FRAM-allocation guard - this
                # matters more here since __init__ runs before any task supervisor exists to
                # catch an escaped exception.
                self._ts_storage = backup.store.get_timestamped_chunk(
                    VOCAlgorithm.get_params_memsize(), backup.ntp_synced, crc=CRC32(),
                )  # timestamped backup storage (FRAM)
            except Exception:
                self._ts_storage = None
            if self._ts_storage is None:
                self.pr.err("FRAM backup storage allocation failed!")
        self._last_backup: int | None = None
        self._restored_from: int | None = None
        self._reset_pending = False
        # Two independent sub-parts of a pending reset, tracked separately since they can complete on different cycles
        # (see reset_voc()/_read_sgp()); both start done. Never drop a reset, never redo the whole thing, never give up
        # retrying (owner, 2026-07-22, `90ced2b`, 'verbatim in spirit').
        self._reset_fram_cleared = True
        self._reset_algo_applied = True

    async def _check_storage(
        self,
    ) -> "tuple[FRAMChunkTimestampedBuffer | None, bool, bool, tuple[int, int, int] | None]":
        if self._ts_storage is None:
            self._voc_init = 0
            self._voc_write = 0
            return None, False, False, None  # no storage configured at all

        cfg_values = await self.cfgmgr.get_int_values(_VAL_BACKUP_PERIOD + _VAL_BACKUP_MAX_AGE + _VAL_WAIT_TIME_NTP)
        if cfg_values is None or len(cfg_values) != _N_STORAGE_CFG:
            await self.pr.err_s("Error reading config data!", errno=_ERR_CFG_READ)
            return None, False, False, None

        serialize = False
        deserialize = False

        # restore part
        if self._voc_init > 0:  # not yet initialized
            self.pr.evt("VOC backup load trigger")
            self._voc_init -= 1  # countdown init timer
            deserialize = True

        # backup part
        self._backup_counter += 1
        if cfg_values[0] > 0 and self._backup_counter >= (60 * cfg_values[0]):
            self._backup_counter = 0
            serialize = True
        self.pr.all("Backup counter:", self._backup_counter, "Trigger:", 60 * cfg_values[0])

        if self._backup_counter >= _BACKUP_COUNTER_MAX:
            self._backup_counter = 0
            # counts seconds, resets at 86400 = 1 day, give it some more space

        buf = self._ts_storage.get_buffer() if serialize or deserialize else None

        # explicit unpack-then-repack (not tuple(cfg_values)) so mypy sees a real 3-tuple, matching
        # the declared return type, without a runtime-unsafe typing.cast (see module docstring)
        backup_period, backup_maxage, wait_ntp = cfg_values
        return buf, serialize, deserialize, (backup_period, backup_maxage, wait_ntp)

    async def _compensation(self, now: int | None) -> tuple[object, object]:
        # Direct read of each producer's get_data() (Part C.14), resolved by attribute name like
        # _check_one() does for warn_*. get_data() never raises, but the named field can be None -
        # the producer has not measured yet, or its error streak gave up - which is expected input.

        # Split the way _check_one() splits it: only get_data() itself raising, a real violation of
        # its never-raises contract, is worth logging. A None field, or a sample too old to compensate
        # with, takes the caller's skip and is never misreported as a read failure.
        try:
            temp_data = await self._temperature.source.get_data()
            hum_data = await self._humidity.source.get_data()
        except Exception as e:
            await self.pr.err_s("Compensation data read failed:", e, errno=_ERR_SOURCE)
            return None, None
        return _current_value(temp_data, self._temperature.field, now), _current_value(hum_data, self._humidity.field, now)

    async def _init_sgp(self) -> bool:
        if self._timer_error is not None:  # a failed read-trigger arm: the restarted task re-arms first
            self._timer_error = None
            self.start_timer()
        self._err_cnt_internal = 0
        self._backup_counter = 0
        self._voc_init = 0
        self._voc_write = 0
        try:
            await self._sgp.setup()
        except Exception as e:
            await self.pr.err_s("Error in initial setup:", e, errno=_ERR_INIT)
            await self._init_failed()
            return False  # error

        if self._ts_storage is None:
            await self._init_done()
            self.pr.one("initialized without storage")
            return True  # no storage configured

        cfg_values = await self.cfgmgr.get_int_values(_VAL_BACKUP_PERIOD + _VAL_WAIT_TIME_NTP)
        if cfg_values is None or len(cfg_values) != _N_SETUP_CFG:
            await self.pr.err_s("Error reading config data!", errno=_ERR_CFG_READ)
            return False  # error

        if cfg_values[0] > 0:  # backup verification period setting
            await self._ts_storage.set_verify(_verify_every(cfg_values[0]))

        wait = min(cfg_values[1], _MAX_NTP_WAITTIME)
        self._voc_init = max(1, wait)  # 0 = never wait: one restore attempt on the first cycle, as legacy
        self._voc_write = wait
        self._restore_waiting = False
        self.pr.one("initialized with storage")
        await self._init_done()
        return True

    async def _push_reset_voc(self, value: int | float | str | bool | None) -> bool:
        # Only a validated bool arrives here (the shared validation). Deliberately does NOT forward
        # reset_voc()'s own return value: it uses False for "no-op" (see its own docstring), not "push
        # failed" (SPECIFICATION.md C.5.2) - always reports success.
        await self.reset_voc(flag=value is True)
        return True

    async def _read_loop(self) -> None:
        if not await self._init_sgp():  # init sensor at startup
            return  # end and restart if init fails
        while True:
            await self._read_event.wait()  # wait for read trigger event
            if await self._timer_fault():
                return  # the trigger timer never armed: the restart re-arms it
            self.pr.evt("sensor trigger")
            buf, serialize, deserialize, cfg_values = await self._check_storage()
            deserialize = await self._run_restore(buf, deserialize=deserialize, cfg_values=cfg_values)  # check for available backup data
            data, compensated, serialize = await self._read_sgp(buf, serialize=serialize, deserialize=deserialize)  # read data
            # A failed read clears every measured value; TS alone is None until the first NTP sync, which is no failure.
            if not await self._error_check(data, condition=compensated and data[0] is None):
                return  # end and restart if too many errors
            await self._store_sgp(data)  # store data in result buffer
            await self._run_backup(buf, serialize=serialize, cfg_values=cfg_values)  # store backup if data was issued

    async def _read_sgp(
        self, buf: "FRAMChunkTimestampedBuffer | None", *, serialize: bool, deserialize: bool,
    ) -> tuple[SGP40, bool, bool]:
        # Snapshotted once at entry so a concurrent reset_voc(flag=True) (e.g. a REST handler) only
        # ever affects the *next* cycle, never this one.
        reset_now = self._reset_pending
        if reset_now:
            self.pr.evt("Reset trigger")
            self._backup_counter = 0
            serialize = False
            deserialize = False
            self._last_backup = None
            self._restored_from = None
            if self._ts_storage is None:
                self._reset_fram_cleared = True  # nothing to clear - vacuously satisfied
            elif not self._reset_fram_cleared:
                self._reset_fram_cleared = await self._ts_storage.clear()
                if not self._reset_fram_cleared:
                    await self.pr.err_s("Error clearing FRAM!", errno=_ERR_SGP_BACKUP_CLEAR)

        timestamp = utc_now()  # None until the NTP client has set the clock this boot
        temp_val, hum_val = await self._compensation(timestamp)
        if temp_val is None or hum_val is None:
            if deserialize:
                self.pr.evt("Retrying initialization...")
                self._voc_init = 1  # retry init if triggered and no compensation data is available
                self._backup_counter = 0  # no backup if restore is pending
            return SGP40(None, None, None, None), False, False

        voc_state: int | None
        try:
            # First, before the reset bookkeeping: a value that is not a finite number is a read
            # failure, and a pending algorithm reset stays pending.
            t = checked_float(temp_val, _COMP_T_FIELD)
            h = checked_float(hum_val, _COMP_RH_FIELD)
            if t is None or h is None:
                raise ValueError(f"compensation value not a finite number (t={temp_val!r}, rh={hum_val!r})")
            # Applies the software reset at most once per pending request; vocalgorithm_reset()
            # never raises, so this half is guaranteed applied regardless of I2C outcome below.
            reset_for_measure = reset_now and not self._reset_algo_applied
            if reset_for_measure:
                self._reset_algo_applied = True
            (
                voc_index,
                raw,
                serialized,
                deserialized,
            ) = await self._sgp.measure_index_and_raw(
                temperature=t,
                relative_humidity=h,
                reset=reset_for_measure,
                buf=None if buf is None else buf.get_data_buf(),
                serialize=serialize,
                deserialize=deserialize,
            )
            if voc_index is None or raw is None:  # the command's CRC could not be computed: no measurement
                raise RuntimeError("raw signal not measured")
            if reset_now and self._reset_algo_applied and self._reset_fram_cleared:
                self._reset_pending = False
            self.pr.all("read")

            if deserialize:
                if deserialized:
                    self.pr.one("Restore applied successfully")
                else:
                    await self.pr.err_s("Error deserializing!", errno=_ERR_SGP_ALGO_STATE)

            if serialize:
                if serialized:
                    self.pr.evt("Backup data created successfully")
                else:
                    await self.pr.err_s("Error serializing!", errno=_ERR_SGP_ALGO_STATE)

            voc_state = self._voc_state(voc_index, fresh=reset_for_measure, restored=deserialized)

        except Exception as e:
            # I2C failed, but a pending reset_for_measure already completed above regardless.
            if reset_now and self._reset_algo_applied and self._reset_fram_cleared:
                self._reset_pending = False
            voc_index = raw = voc_state = None
            serialized = False
            if deserialize:  # the backup was read but never applied: keep it for the next cycle
                self._voc_init = 1
                self._backup_counter = 0  # no backup may overwrite it meanwhile
            await self.pr.err_s("Read failed:", e, errno=_ERR_READ)
        return SGP40(voc_index, raw, voc_state, timestamp), True, serialized

    async def _recover_device(self) -> bool:
        # The participant rung: heater off to idle (datasheet Table 14), reaching the SGP40 alone. The VOC
        # algorithm state is untouched; the next measure command re-enters measurement (3.1).
        try:
            await self._sgp.turn_heater_off()
        except Exception as e:
            await self.pr.err_s("Heater-off failed:", e, errno=_ERR_CHIP_SET)
            return False
        return True

    async def _run_backup(
        self,
        buf: "FRAMChunkTimestampedBuffer | None",
        *,
        serialize: bool,
        cfg_values: tuple[int, int, int] | None,
    ) -> None:
        if not serialize or self._ts_storage is None or buf is None or cfg_values is None:
            return  # no buffer / no trigger

        self.pr.evt("Backup trigger.")
        if cfg_values[0] > 0:  # SGPBackupPeriod -  backup verification period setting
            current_verify = await self._ts_storage.get_verify()
            desired_verify = _verify_every(cfg_values[0])
            if current_verify != desired_verify:
                await self._ts_storage.set_verify(desired_verify)

        if self._voc_write > 0:
            self._voc_write -= 1
        require_ntp = self._voc_write > 0

        self.pr.evt("Writing backup.")
        ntp_synced, ts, res = await self._ts_storage.write_into(buf, require_ntp=require_ntp)

        if require_ntp and not ntp_synced:  # no write due to no timesync yet
            # set backup counter to retry serialization in self._read_sgp()
            self._backup_counter = 60 * cfg_values[0]  # SGPBackupPeriod
            self.pr.all("Backup NTP wait time:", self._voc_write)
            return  # no write error

        if not res:  # no data was written for other reason
            await self.pr.err_s("Write error during backup!", errno=_ERR_SGP_BACKUP_WRITE)
            return  # don't continue due to error

        if require_ntp:  # (ntp_synced and require_ntp) and res must have been True here
            self._voc_write = cfg_values[2]  # SGPWaitTimeNTP
            self._last_backup = ts
            self.pr.evt("Backup written with timestamp.")
            return

        if ntp_synced:  # require_ntp was false from here on, but res was True
            self._voc_write = cfg_values[2]  # SGPWaitTimeNTP
            self.pr.evt("Backup written with timestamp again.")
        else:  # every untimestamped backup warns; the newest-entry rule spends one slot per run
            await self.pr.wrn_s("Backup written without timestamp.", wrnno=_WRN_SGP_WRITTEN_NO_TS)
        self._last_backup = ts
        return

    async def _run_restore(
        self,
        buf: "FRAMChunkTimestampedBuffer | None",
        *,
        deserialize: bool,
        cfg_values: tuple[int, int, int] | None,
    ) -> bool:
        if not deserialize or self._ts_storage is None or buf is None or cfg_values is None:
            return False  # no buffer / no trigger

        ntp_synced = self._ntp_synced
        if self._restore_waiting and self._voc_init > 0 and ntp_synced is not None and not await ntp_synced():
            return False  # still waiting for NTP: the chunk was read when the wait began, not every second
        res, ts, age = await self._ts_storage.read_into(buf)
        if not res:  # not valid / no backup
            await self.pr.wrn_s("No backup found!", wrnno=_WRN_SGP_NO_BACKUP)
            self._voc_init = 0
            self._restore_waiting = False
            return False

        # One chain, as legacy: the age bound is tested only once an age is known.
        if ts is None:  # undated: restored at once, no age to test
            await self.pr.wrn_s("Backup loaded without timestamp", wrnno=_WRN_SGP_RESTORED_NO_TS)
            ts = _NO_TIMESTAMP
        elif age is None and self._voc_init > 0:
            self._restore_waiting = True
            self.pr.evt("Backup with timestamp found, NTP wait time:", self._voc_init)
            return False
        elif age is None:  # dated, but the NTP wait ended unsynced: restored without an age test
            await self.pr.wrn_s("Backup loaded with unknown age (no NTP sync)", wrnno=_WRN_SGP_RESTORED_NO_TS)
        elif cfg_values[1] > 0 and (age < 0 or age > 60 * cfg_values[1]):  # BackupMaxAge; 0 accepts any age
            self._voc_init = 0
            self._restore_waiting = False
            await self.pr.wrn_s("Backup age out of range (too old, or dated in the future)", wrnno=_WRN_SGP_BACKUP_AGE)
            return False
        else:
            self.pr.one("Backup with timestamp loaded")
        self._voc_init = 0
        self._restore_waiting = False
        self._restored_from = ts
        return True

    async def _store_sgp(self, data: SGP40) -> None:
        if data.VOC is None or data.Raw is None:
            return  # don't run on invalid data; the timestamp may be None before the first sync
        await self._set_meas_data(data)
        self.pr.all("data stored")

    def _voc_state(self, voc_index: int, *, fresh: bool, restored: bool) -> int:
        # VOCState of one sample: the algorithm starts over at a reset and at a restore; the count saturates at its cap.
        if fresh or restored:
            self._voc_samples = 0
            self._voc_restored = restored
        if self._voc_samples < _VOC_SETTLED_SAMPLES:
            self._voc_samples += 1
        if voc_index == 0:  # only the blackout publishes 0: past it the reference clamps the index to >= 0.5
            return 0
        if self._voc_samples >= _VOC_SETTLED_SAMPLES:
            return 2
        return 3 if self._voc_restored else 1

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_read]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []

    def get_trigger_starters(self) -> "list[TimerStarter]":
        return [self.start_timer]

    def start_asy_read(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._read_loop())

    def start_timer(self) -> None:  # voc algorithm needs 1s period fixed
        try:
            self._trigger_timer.init(
                period=1000,
                mode=Timer.PERIODIC,
                callback=lambda _b: self._read_event.set(),
            )
        except (MemoryError, OSError) as e:
            # Alarm pool exhausted (ENOMEM) or no memory: wake the waiting task, which logs it and ends; its restart re-arms.
            self._timer_failed(e, self._read_event)

    def stop_timer(self) -> None:
        self._trigger_timer.deinit()

    async def get_data(self) -> SGP40:
        # Narrows to this Reader's concrete SGP40 - see SPECIFICATION.md C.4.2's get_data() convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        # Deliberately excludes _VAL_RESET_VOC (ResetVOC) - see that const's own comment: it's never
        # in cfgmgr's _cache (special-alone, not persisted), and ConfigManager.get_dict() is
        # all-or-nothing per requested key, so including it here would break this whole read.
        return await self._get_dict_cfg(self.name, _VAL_BACKUP_PERIOD + _VAL_BACKUP_MAX_AGE + _VAL_WAIT_TIME_NTP)

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def get_mem_status(self) -> tuple[int | None, int | None]:
        return self._last_backup, self._restored_from

    async def reset_voc(self, *, flag: bool) -> bool:
        # Uniform setter return contract (owner, 2026-09-26): True = applied, False = no-op.
        # flag=False deliberately does nothing (see test_reset_voc_false_is_a_no_op's own contract
        # note) - only flag=True actually triggers a reset.
        if flag:
            self._reset_pending = True
            # A fresh request always restarts both sub-parts' tracking, even if a previous reset was
            # already midway through completing - this specific request must be fully honored too,
            # not silently considered already-satisfied by an earlier, unrelated reset's bookkeeping.
            self._reset_fram_cleared = False
            self._reset_algo_applied = False
            return True
        return False


class SGP40_I2C:
    def __init__(self, i2c: "I2C") -> None:
        # One session for the exchange, self._command_buffer and self._measure_command.
        self._i2c_sgp40 = DeviceSession(I2CDevice(i2c, _SGP40_ADDR))
        self._default_command_buffer = bytearray(2)
        self._command_buffer = self._default_command_buffer
        self._reply_buffer = bytearray(9)  # Sized for the longest reply, the 3-word serial number (datasheet Table 8)
        self.crc = CRC8()
        self._measure_command = bytearray(b"\x26\x0f\x80\x00\xa2\x66\x66\x93")
        self._voc_algorithm: VOCAlgorithm | None = None

    @staticmethod
    def _celsius_to_ticks(temperature: float, buf: bytearray | memoryview) -> None:
        # Temperature-to-ticks, datasheet Table 10: 25C->0x6666, -45C->0x0000, 130C->0xFFFF. Rounds to nearest (matching
        # _relative_humidity_to_ticks below) rather than truncating (owner, 2026-07-22, paraphrase); clamped to Table 10's
        # range, never wrapped.
        t = min(_T_TICKS_MAX_C, max(_T_TICKS_MIN_C, temperature))
        ticks = int((t + 45) * 65535 / 175 + 0.5)
        buf[0] = ticks >> 8  # most significant byte
        buf[1] = ticks & 0xFF  # least significant byte

    async def _measure_in_session(self, sgp40: DeviceSession) -> int:
        # Caller holds self._i2c_sgp40. The finally restores the default command even when the read raises.
        self._command_buffer = self._measure_command  # recycle a single buffer
        try:
            return (await self._read_word_from_command(sgp40, _MEASURE_WAIT_MS))[0]
        finally:
            self._command_buffer = self._default_command_buffer

    async def _read_word_from_command(self, sgp40: DeviceSession, delay_ms: int, readlen: int = 1) -> list[int]:
        # Sends self._command_buffer, waits delay_ms, reads back readlen CRC-checked words into the reply buffer.
        replylen = readlen * 3
        if replylen > len(self._reply_buffer):
            raise ValueError("reply longer than the reply buffer")
        async with sgp40.i2c_device as i2c:  # bus session
            if not await i2c.write(self._command_buffer):
                raise OSError("I2C bus not initialized")
        await asyncio.sleep(round(delay_ms * 0.001, 3))
        async with sgp40.i2c_device as i2c:
            if not await i2c.readinto(self._reply_buffer, end=replylen):
                raise OSError("I2C bus not initialized")  # before the CRC check: a stale buffer would pass it

        readdata_buffer = []
        for i in range(0, replylen, 3):
            if await self.crc.check_from(self._reply_buffer, 3, start=i) is None:
                raise RuntimeError("CRC check failed while reading data")
            readdata_buffer.append(unpack_from(">H", self._reply_buffer, i)[0])
        return readdata_buffer

    @staticmethod
    def _relative_humidity_to_ticks(humidity: float, buf: bytearray | memoryview) -> None:
        # Relative-humidity-to-ticks, datasheet Table 10: 50%->0x8000, 0%->0x0000, 100%->0xFFFF; rounded to
        # nearest and clamped to Table 10's range, never wrapped.
        h = min(_RH_TICKS_MAX, max(0.0, humidity))
        ticks = int(h * 65535 / 100 + 0.5)
        buf[0] = ticks >> 8  # most significant byte
        buf[1] = ticks & 0xFF  # least significant byte

    async def _reset(self) -> None:
        # True I2C general-call reset (datasheet Table 17): 0x06 to the reserved address 0x00,
        # broadcast to every device on the bus. A NAK (OSError) is expected, not a failure.
        acked: int | None = 0
        async with self._i2c_sgp40 as sgp40, sgp40.i2c_device as i2c:
            try:
                acked = i2c.i2c.writeto(0x00, b"\x06")
            except OSError:
                pass
        if acked is None:
            raise OSError("I2C bus not initialized")
        await asyncio.sleep(_GENERAL_CALL_RESET_WAIT_S)

    async def get_raw(self) -> int:
        async with self._i2c_sgp40 as sgp40:  # device session
            return await self._measure_in_session(sgp40)

    async def initialize(self) -> None:
        # Identity per datasheet 3.3-3.4: three CRC-checked serial words with legacy's word-0 check, and the self-test's
        # 0xD4 high byte (Table 13). No feature-set check: the datasheet documents none (owner, 2026-07-21).
        async with self._i2c_sgp40 as sgp40:  # device session
            self._command_buffer[0] = 0x36
            self._command_buffer[1] = 0x82
            serialnumber = await self._read_word_from_command(sgp40, _SERIAL_READ_WAIT_MS, readlen=3)
        if serialnumber[0] != 0x0000:
            # Word 0 == 0 is undocumented (datasheet 3.4 gives no structure) but field-proven: legacy checks it on
            # every unit. The dev board's word 0 is still to be recorded on real hardware.
            raise RuntimeError("serial number does not match")

        async with self._i2c_sgp40 as sgp40:  # device session
            self._command_buffer[0] = 0x28
            self._command_buffer[1] = 0x0E
            self_test = await self._read_word_from_command(sgp40, _SELF_TEST_WAIT_MS)
        # Datasheet Table 13: only the high byte is the pass/fail marker (0xD4/0x4B); the low
        # byte is documented as "ignore", not guaranteed zero.
        if (self_test[0] >> 8) != _SELF_TEST_PASS:
            raise RuntimeError("self test failed")
        await self._reset()

    async def measure_index_and_raw(
        self,
        temperature: float = 25,
        relative_humidity: float = 50,
        *,
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
            raw, buf, serialize=serialize, deserialize=deserialize, offset=offset,
        )
        return voc_index, raw, serialized, deserialized

    async def measure_raw(self, temperature: float = 25, relative_humidity: float = 50) -> int | None:
        # Humidity/temperature-compensated raw gas value (datasheet Table 9, command 0x260F).
        async with self._i2c_sgp40 as sgp40:  # device session
            # Staged inside the session: an await before the hold would let another caller overwrite the shared command (owner, 2026-09-29: 'No races allowed').
            mv = memoryview(self._measure_command)
            mv[0] = 0x26
            mv[1] = 0x0F  # compensated read command
            self._relative_humidity_to_ticks(relative_humidity, mv[2:4])
            if await self.crc.add_into(self._measure_command, 2, start=2) is None:
                return None
            self._celsius_to_ticks(temperature, mv[5:7])
            if await self.crc.add_into(self._measure_command, 2, start=5) is None:
                return None
            return await self._measure_in_session(sgp40)

    async def setup(self) -> bool:
        async with self._i2c_sgp40 as sgp40, sgp40.i2c_device as i2c:
            await i2c.setup()
        await self.initialize()
        return True

    async def turn_heater_off(self) -> None:
        # Datasheet Table 14: hotplate off, measurement stopped, idle mode; the next measure command restarts it.
        async with self._i2c_sgp40 as sgp40, sgp40.i2c_device as i2c:
            if not await i2c.write(_CMD_HEATER_OFF):
                raise OSError("I2C bus not initialized")
        await asyncio.sleep_ms(_HEATER_OFF_MAX_MS + 1)  # one tick more than the datasheet bound: sleep_ms() may wake up to 1 ms early
