# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries (original
# adafruit_sgp40, CircuitPython) - restructured/rewritten for asyncio + MicroPython, see
# THIRD_PARTY_LICENSES.md.
# SPDX-License-Identifier: MIT

"""Sensirion SGP40 VOC sensor driver: SGP40_I2C (chip protocol) and SGP40_Reader (async wrapper - trigger timer, read loop, error counting, config schema, FRAM backup/restore of voc_algorithm.py's VOCAlgorithm state).
Same shape as asy_scd30_driver.py/asy_bmp3xx_driver.py (see SPECIFICATION.md Part C).
Verified against Sensirion's SGP40 datasheet (datasheets/sgp40/, v1.2 - Feb 2022).
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
from config_manager import make_dict, name_cfg
from crc_checks import CRC8, CRC32
from voc_algorithm import VOCAlgorithm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, Protocol

    from asy_fram_manager import AsyFramChunkTimestampedBuffer, AsyFramManager
    from asy_i2c_driver import I2C
    from print_log import ErrorLog

    class _ValueSource(Protocol):
        # Structural stand-in for temperature_source/humidity_source's producer
        # (BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §2.9) - any *_Reader (or a `_Default*`
        # fallback provider, see below) exposing the same get_data() -> NamedTuple contract every
        # driver already has (SPECIFICATION.md C.4.2). Only get_data() is used here - same shape as
        # asy_notification_service.py's own _ValueSource.
        async def get_data(self) -> "Any": ...

# roughly the time how often the data written to the FRAM is verified.
# less a data safety feature here but rather a check if communication and integrity is generally okay
_FRAM_VERIFY_MINS = const(60)
_MAX_NTP_WAITTIME = const(600)  # 600s = 10min
_BACKUP_COUNTER_MAX = const(100000)  # see _check_storage()'s own note on the 86400s = 1 day margin
_SELF_TEST_PASS = const(0xD4)  # datasheet Table 13, high byte only (the low byte is "ignore")

_VAL_BP = const((("BackupPeriod", "int", 1, 0, 1440, None),))
_VAL_BMAX = const((("BackupMaxAge", "int", 7200, 0, 10080, None),))
_VAL_WT = const((("WaitTimeNTP", "int", 30, 0, 600, None),))
_N_STORAGE_CFG = const(3)  # value count of the _VAL_BP + _VAL_BMAX + _VAL_WT batch read below
_N_SETUP_CFG = const(2)  # value count of the _VAL_BP + _VAL_WT batch read below
# Command-only trigger, not a persisted config value - reuses the schema's "special-alone" field
# convention (def=None + a non-tuple special, see SPECIFICATION.md C.5). Deliberately excluded
# from get_dict_cfg()'s own schema argument below - this key is never in ConfigManager's _cache.
_VAL_RESET = const((("SGPResetVOC", "bool", None, None, None, True),))

# @web-group section=sensors submitGroup=self label="SGP40 — VOC Index" submit=true
# @web BackupPeriod section=sensors submitGroup=self label="VOC Index Backup Interval" unit="min" special:0="Backups off"
# @web BackupMaxAge section=sensors submitGroup=self label="VOC Index Backup Max Age" unit="min" special:0="Use all found backups"
# @web WaitTimeNTP section=sensors submitGroup=self label="VOC Index NTP Wait Time" unit="s" special:0="Never wait for NTP sync"
# @web SGPResetVOC section=sensors submitGroup=self label="Reset VOC Index" description="Only 'On' has effect. Resets the VOC algorithm and deletes the current backup." dispatch=true

_NAME = const("SGP40")
# VOC/Raw/TS also doubles as the full result of a read (see _read_sgp/_store_sgp) - no separate
# results type needed, unlike asy_scd30_driver.py's SCDResults, which carries derived fields SGP40
# doesn't have.
# Kept as a literal tuple inline (not `_FIELDS` below) because mypy's namedtuple plugin can only
# infer field names from a literal at the call site, not through a variable indirection.
SGP40 = namedtuple("SGP40", ("VOC", "Raw", "TS"))
_FIELDS = const(("VOC", "Raw", "TS"))  # kept in sync with SGP40's own fields above

# @web-group section=measurements submitGroup=self label="SGP40 — VOC Index"
# @web VOC section=measurements submitGroup=self kind=readonly label="VOC Index"
# @web Raw section=measurements submitGroup=self kind=readonly label="VOC Raw" unit="ticks"
# @web TS section=measurements submitGroup=self kind=readonly label="Timestamp" unit="s"

# This driver's live cross-instance dependencies (SPECIFICATION.md Part C.14): the optional FRAM
# backup target, resolved by buildgen/ (Session 3 of BUILD_CHAIN_PLAN.md) to an already-constructed
# instance, passed directly (fram_target maps to this driver's own fram_storage= kwarg, named
# differently for historical reasons - see buildgen/buildspec.py), never a getter/callback.
# The temperature/humidity compensation source used to be one whole-object comp_source field here
# (required=True, fixed to SCD30_Reader) - BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md §2.9
# generalized it into two independent per-value fields below (_VALUE_WIRING), each freely wireable
# from *any* instance exposing a matching attribute name, not fixed to one producer class.
# datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf Table 3: fSCL max 400 kHz
# ("standard-mode" 100 kHz / "fast-mode" 400 kHz). A generator-checked build requirement
# rather than a comment each device TOML author has to remember - a bus this driver shares
# with an SCD30 is held to that sensor's own stricter 100 kHz tag on top of this one.
# @requires bus.frequency<=400000
# @wiring fram_target AsyFramManager fram_storage optional kwarg

# Per-value measurement wiring (§2.9) - each field resolves independently, the same generic
# {source, field} shape asy_notification_service.py's warn_* fields already use, matched by
# attribute name alone (no fixed producer class). Both required: an SGP40 with no compensation
# data at all needs an explicit default opt-in, per §2's wiring-defaults mechanism - see
# _DefaultTemperatureSource/_DefaultHumiditySource below.
# @value-wiring temperature_source temperature_source temperature_field required
# @value-wiring humidity_source humidity_source humidity_field required

_ConstValue = namedtuple("_ConstValue", ("value",))


class _DefaultTemperatureSource:
    """§2's wiring-defaults mechanism, opted into via [instance.wiring].temperature_source =
    {default = true, temperature = 25} - a constant compensation fallback when no live temperature
    source is wired. 25 degC matches SGP40_I2C.measure_raw()'s own datasheet-documented default
    (Table 9). Every `_Default*` provider's get_data() returns an object exposing exactly one
    attribute named "value" (a fixed, hardcoded contract - see BUILDGEN_WIRING_DEFAULTS_AND_TEST_MATRIX.md
    §10.1 item 1), so buildgen always resolves a defaulted per-value field as (provider, "value")."""

    def __init__(self, temperature: float = 25) -> None:
        self._data = _ConstValue(float(temperature))

    async def get_data(self) -> "_ConstValue":
        return self._data


class _DefaultHumiditySource:
    """Same mechanism as _DefaultTemperatureSource, for relative humidity - 50%RH matches
    SGP40_I2C.measure_raw()'s own datasheet-documented default (Table 9)."""

    def __init__(self, relative_humidity: float = 50) -> None:
        self._data = _ConstValue(float(relative_humidity))

    async def get_data(self) -> "_ConstValue":
        return self._data


class SGP40_Reader(SensorReaderConfig):
    def __init__(
        self,
        i2c: "I2C",
        temperature_source: "_ValueSource",
        temperature_field: str,
        humidity_source: "_ValueSource",
        humidity_field: str,
        max_module_error: int = 5,
        name_ext: str = "",
        cfg_path: str = "",
        fram_storage: "AsyFramManager | None" = None,
        fram_ntp_callback: "Callable[[], Coroutine[Any, Any, bool]] | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(
            SGP40(None, None, None),
            max_module_error,
            _NAME,
            _VAL_BP + _VAL_BMAX + _VAL_WT + _VAL_RESET,
            name_ext=name_ext,
            cfg_path=cfg_path,
            fram=fram_storage,
            history_length=history_length,
            debug=debug,
        )
        self.sgp = SGP40_I2C(i2c)
        # SGPResetVOC is command-only (see _VAL_RESET above) - registered the same way as every
        # other module's real live-push field (project decision - constant at runtime, no per-call
        # plumbing needed), just never persisted.
        self._push_callbacks[name_cfg(_VAL_RESET)] = self._push_reset_voc
        self.trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_timer = Timer()
        self.backup_counter = 0
        # real values are always set by _init_sgp() before read_loop() ever reads these
        self.voc_init = 0
        self.voc_write = 0
        # Direct reference to each producer's own concurrency-safe value holder (its get_data(),
        # already _datalock-guarded - SPECIFICATION.md Part C.14/G.2), not a wrapping getter
        # function - _read_sgp() reads temperature_field/humidity_field off each directly every
        # cycle, resolved independently (§2.9's per-value generalization) - the two may be the same
        # producer instance (the common case, both off one SCD30) or two different ones.
        self.temperature_source = temperature_source
        self.temperature_field = temperature_field
        self.humidity_source = humidity_source
        self.humidity_field = humidity_field
        if fram_storage is None or fram_ntp_callback is None:
            self.ts_storage = None
        else:
            try:  # broad on purpose, matching print_log.py's own FRAM-allocation guard - this
                # matters more here since __init__ runs before any task supervisor exists to
                # catch an escaped exception.
                self.ts_storage = fram_storage.get_timestamped_chunk(
                    VOCAlgorithm.get_params_memsize(), fram_ntp_callback, crc=CRC32(),
                )  # timestamped backup storage (FRAM)
            except Exception:
                self.ts_storage = None
            if self.ts_storage is None:
                self.pr.err("FRAM backup storage allocation failed!")
        self.last_backup: int | None = None
        self.restored_from: int | None = None
        self.reset = False
        # Two independent sub-parts of a pending reset, tracked separately since they can complete
        # on different cycles (see reset_voc()/_read_sgp()). Both start "done".
        self._reset_fram_cleared = True
        self._reset_algo_applied = True

    async def _check_storage(
        self,
    ) -> "tuple[AsyFramChunkTimestampedBuffer | None, bool, bool, tuple[int, int, int] | None]":
        if self.ts_storage is None:
            self.voc_init = 0
            self.voc_write = 0
            return None, False, False, None  # no storage configured at all

        cfg_values = await self.cfgmgr.get_int_values(_VAL_BP + _VAL_BMAX + _VAL_WT)
        if cfg_values is None or len(cfg_values) != _N_STORAGE_CFG:
            await self.pr.err_s("Error reading config data!", errno=13)
            return None, False, False, None

        serialize = False
        deserialize = False

        # restore part
        if self.voc_init > 0:  # not yet initialized
            self.pr.evt("VOC backup load trigger")
            self.voc_init -= 1  # countdown init timer
            deserialize = True

        # backup part
        self.backup_counter += 1
        if cfg_values[0] > 0 and self.backup_counter >= (60 * cfg_values[0]):
            self.backup_counter = 0
            serialize = True
        self.pr.all("Backup counter:", self.backup_counter, "Trigger:", 60 * cfg_values[0])

        if self.backup_counter >= _BACKUP_COUNTER_MAX:
            self.backup_counter = 0
            # counts seconds, resets at 86400 = 1 day, give it some more space

        buf = self.ts_storage.get_buffer() if serialize or deserialize else None

        # explicit unpack-then-repack (not tuple(cfg_values)) so mypy sees a real 3-tuple, matching
        # the declared return type, without a runtime-unsafe typing.cast (see module docstring)
        backup_period, backup_maxage, wait_ntp = cfg_values
        return buf, serialize, deserialize, (backup_period, backup_maxage, wait_ntp)

    async def _read_sgp(
        self, buf: "AsyFramChunkTimestampedBuffer | None", *, serialize: bool, deserialize: bool,
    ) -> tuple[SGP40, bool, bool]:
        # Snapshotted once at entry so a concurrent reset_voc(flag=True) (e.g. a REST handler) only
        # ever affects the *next* cycle, never this one.
        reset_now = self.reset
        if reset_now:
            self.pr.evt("Reset trigger")
            self.backup_counter = 0
            serialize = False
            deserialize = False
            self.last_backup = None
            self.restored_from = None
            if self.ts_storage is None:
                self._reset_fram_cleared = True  # nothing to clear - vacuously satisfied
            elif not self._reset_fram_cleared:
                self._reset_fram_cleared = await self.ts_storage.clear()
                if not self._reset_fram_cleared:
                    await self.pr.err_s("Error clearing FRAM!", errno=15)

        # Direct read of each producer's own get_data() (SPECIFICATION.md Part C.14), resolved
        # independently by attribute name (§2.9's per-value generalization - the same getattr()
        # resolution asy_notification_service.py's own _check_one() already uses for warn_*) - no
        # wrapping callback. get_data() never raises, but the named field can individually still be
        # None (the producer hasn't completed its first real measurement yet, or its own error
        # streak gave up) - a normal, expected input, not an exception (CLAUDE.md: no E/W log for
        # expected startup jitter). Split the same way _check_one() already does: only get_data()
        # itself raising - a genuine violation of its own never-raises contract - is a real fault
        # worth logging; a getattr()-returned None is read via its own default, never routed through
        # float() (which would raise TypeError on None and get misreported as a read failure) and
        # never logged here on its own - a persistent producer failure is caught and logged by that
        # producer's own driver already, not re-detected from this side.
        temp_val: int | float | None
        hum_val: int | float | None
        try:
            temp_data = await self.temperature_source.get_data()
            hum_data = await self.humidity_source.get_data()
        except Exception as e:
            await self.pr.err_s("Compensation data read failed:", e, errno=18)
            temp_val, hum_val = None, None
        else:
            temp_val = getattr(temp_data, self.temperature_field, None)
            hum_val = getattr(hum_data, self.humidity_field, None)

        if temp_val is None or hum_val is None:
            if deserialize:
                self.pr.evt("Retrying initialization...")
                self.voc_init = 1  # retry init if triggered and no compensation data is available
                self.backup_counter = 0  # no backup if restore is pending
            return SGP40(None, None, None), False, False
        temperature_c = float(temp_val)
        humidity_rh = float(hum_val)

        try:
            timestamp = time.mktime(time.gmtime())
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
            ) = await self.sgp.measure_index_and_raw(
                temperature=temperature_c,
                relative_humidity=humidity_rh,
                reset=reset_for_measure,
                buf=None if buf is None else buf.get_data_buf(),
                serialize=serialize,
                deserialize=deserialize,
            )
            if reset_now and self._reset_algo_applied and self._reset_fram_cleared:
                self.reset = False
            self.pr.all("read")

            if deserialize:
                if deserialized:
                    self.pr.one("Restore applied successfully")
                else:
                    await self.pr.err_s("Error deserializing!", errno=16)

            if serialize:
                if serialized:
                    self.pr.evt("Backup data created successfully")
                else:
                    await self.pr.err_s("Error serializing!", errno=17)

        except Exception as e:
            # I2C failed, but a pending reset_for_measure already completed above regardless.
            if reset_now and self._reset_algo_applied and self._reset_fram_cleared:
                self.reset = False
            voc_index = raw = timestamp = None
            serialized = False
            await self.pr.err_s("Read failed:", e, errno=11)
        return SGP40(voc_index, raw, timestamp), True, serialized

    async def _init_sgp(self) -> bool:
        await self.pr.setup()  # required for all logged warnings and errors
        self._err_cnt_internal = 0
        self.backup_counter = 0
        self.voc_init = 0
        self.voc_write = 0
        try:
            await self.sgp.setup()
        except Exception as e:
            await self.pr.err_s("Error in initial setup:", e, errno=10)
            return False  # error

        if self.ts_storage is None:
            self.pr.one("initialized without storage")
            return True  # no storage configured

        cfg_values = await self.cfgmgr.get_int_values(_VAL_BP + _VAL_WT)
        if cfg_values is None or len(cfg_values) != _N_SETUP_CFG:
            await self.pr.err_s("Error reading config data!", errno=12)
            return False  # error

        if cfg_values[0] > 0:  # backup verification period setting
            await self.ts_storage.set_verify(
                int(math.ceil((10 * _FRAM_VERIFY_MINS) / cfg_values[0]) * 0.1),  # SGPBackupPeriod
            )

        if cfg_values[1] >= 1:  # more than 1s waittime for ntp
            cfg_values[1] = min(cfg_values[1], _MAX_NTP_WAITTIME)  # limit if more than 10min
            self.voc_init = cfg_values[1]  # SGPWaitTimeNTP
            self.voc_write = cfg_values[1]  # SGPWaitTimeNTP
        self.pr.one("initialized with storage")
        return True

    async def _run_restore(
        self,
        buf: "AsyFramChunkTimestampedBuffer | None",
        *,
        deserialize: bool,
        cfg_values: tuple[int, int, int] | None,
    ) -> bool:
        if not deserialize or self.ts_storage is None or buf is None or cfg_values is None:
            return False  # no buffer / no trigger

        res, ts, age = await self.ts_storage.read_into(buf)
        if not res:  # not valid / no backup
            await self.pr.wrn_s("No backup found!", wrnno=10)
            self.voc_init = 0
            return False

        if ts is None:
            await self.pr.wrn_s("Backup loaded without timestamp", wrnno=11)
            self.voc_init = 0
            ts = -1  # means valid data, no timestamp
        elif age is None:
            if self.voc_init > 0:
                self.pr.evt("Backup with timestamp found, NTP wait time:", self.voc_init)
                return False
        else:
            self.pr.one("Backup with timestamp loaded")
            self.voc_init = 0
            if cfg_values[1] > 0 and age > (60 * cfg_values[1]):  # SGPBackupMaxAge
                await self.pr.wrn_s("Backup is too old", wrnno=12)
                return False

        self.restored_from = ts
        return True

    async def _run_backup(
        self,
        buf: "AsyFramChunkTimestampedBuffer | None",
        *,
        serialize: bool,
        cfg_values: tuple[int, int, int] | None,
    ) -> None:
        if not serialize or self.ts_storage is None or buf is None or cfg_values is None:
            return  # no buffer / no trigger

        self.pr.evt("Backup trigger.")
        if cfg_values[0] > 0:  # SGPBackupPeriod -  backup verification period setting
            current_verify = await self.ts_storage.get_verify()
            desired_verify = int(math.ceil((10 * _FRAM_VERIFY_MINS) / cfg_values[0]) * 0.1)  # SGPBackupPeriod
            if current_verify != desired_verify:
                await self.ts_storage.set_verify(desired_verify)

        if self.voc_write > 0:
            self.voc_write -= 1
        require_ntp = self.voc_write > 0

        self.pr.evt("Writing backup.")
        ntp_synced, ts, res = await self.ts_storage.write_into(buf, require_ntp=require_ntp)

        if require_ntp and not ntp_synced:  # no write due to no timesync yet
            # set backup counter to retry serialization in self._read_sgp()
            self.backup_counter = 60 * cfg_values[0]  # SGPBackupPeriod
            self.pr.all("Backup NTP wait time:", self.voc_write)
            return  # no write error

        if not res:  # no data was written for other reason
            await self.pr.err_s("Write error during backup!", errno=14)
            return  # don't continue due to error

        if require_ntp:  # (ntp_synced and require_ntp) and res must have been True here
            self.voc_write = cfg_values[2]  # SGPWaitTimeNTP
            self.last_backup = ts
            self.pr.evt("Backup written with timestamp.")
            return

        if ntp_synced:  # require_ntp was false from here on, but res was True
            self.voc_write = cfg_values[2]  # SGPWaitTimeNTP
            self.pr.evt("Backup written with timestamp again.")
        else:
            await self.pr.wrn_s("Backup written without timestamp.", wrnno=13)
        self.last_backup = ts
        return

    async def _store_sgp(self, data: SGP40) -> None:
        if data.VOC is None or data.Raw is None or data.TS is None:
            return  # don't run on invalid data
        await self._set_meas_data(data)
        self.pr.all("data stored")

    async def _push_reset_voc(self, value: int | float | str | bool | None) -> bool:
        # Narrows _push_callbacks' wide value type to reset_voc's real bool parameter. Deliberately
        # does NOT forward reset_voc()'s own return value: it uses False for "no-op" (see its own
        # docstring), not "push failed" (SPECIFICATION.md C.5.2) - always reports success once typed.
        if not isinstance(value, bool):
            return False
        await self.reset_voc(flag=value)
        return True

    def start_asy_read(self) -> asyncio.Task[bool]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_loop())

    def start_timer(self) -> None:  # voc algorithm needs 1s period fixed
        try:
            self.trigger_timer.init(
                period=1000,
                mode=Timer.PERIODIC,
                callback=lambda _b: self.trigger_event.set(),
            )
        except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - degrades gracefully
            # instead of crashing the caller (this sensor just never gets triggered this cycle).
            self.pr.err("Could not start timer:", e)

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_read]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_timer]

    def stop_timer(self) -> None:
        self.trigger_timer.deinit()

    async def get_mem_status(self) -> tuple[int | None, int | None]:
        return self.last_backup, self.restored_from

    async def get_data(self) -> SGP40:
        # Narrows to this Reader's concrete SGP40 - see SPECIFICATION.md C.4.2's get_data() convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        # Deliberately excludes _VAL_RESET (SGPResetVOC) - see that const's own comment: it's never
        # in cfgmgr's _cache (special-alone, not persisted), and ConfigManager.get_dict() is
        # all-or-nothing per requested key, so including it here would break this whole read.
        return await self._get_dict_cfg(self.name, _VAL_BP + _VAL_BMAX + _VAL_WT)

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def reset_voc(self, *, flag: bool) -> bool:
        # Uniform setter return contract (project-wide decision): True = applied, False = no-op.
        # flag=False deliberately does nothing (see test_reset_voc_false_is_a_no_op's own contract
        # note) - only flag=True actually triggers a reset.
        if flag:
            self.reset = True
            # A fresh request always restarts both sub-parts' tracking, even if a previous reset was
            # already midway through completing - this specific request must be fully honored too,
            # not silently considered already-satisfied by an earlier, unrelated reset's bookkeeping.
            self._reset_fram_cleared = False
            self._reset_algo_applied = False
            return True
        return False

    async def read_loop(self) -> bool:
        if not await self._init_sgp():  # init sensor at startup
            return False  # break and restart if init fails
        while True:
            await self.trigger_event.wait()  # wait for read trigger event
            self.pr.evt("sensor trigger")
            buf, serialize, deserialize, cfg_values = await self._check_storage()
            deserialize = await self._run_restore(buf, deserialize=deserialize, cfg_values=cfg_values)  # check for available backup data
            data, compensated, serialize = await self._read_sgp(buf, serialize=serialize, deserialize=deserialize)  # read data
            if not await self._error_check(data, condition=compensated):  # check and count errors
                return False  # break and restart if too many errors
            await self._store_sgp(data)  # store data in result buffer
            await self._run_backup(buf, serialize=serialize, cfg_values=cfg_values)  # store backup if data was issued


class SGP40_DeviceSession(Lockable):  # lock for consecutive i2c communication and self._command_buffer
    def __init__(self, i2c_device: I2CDevice) -> None:
        super().__init__()
        self.i2c_device = i2c_device


class SGP40_I2C:
    def __init__(self, i2c: "I2C", address: int = 0x59) -> None:
        self.i2c_sgp40 = SGP40_DeviceSession(I2CDevice(i2c, address))
        self._default_command_buffer = bytearray(2)
        self._command_buffer = self._default_command_buffer
        # Sized for the only readlen actually used anywhere in this file (readlen=1, 3 bytes/word);
        # _read_word_from_command() falls back to a fresh allocation if a future caller ever asks
        # for more words than this holds.
        self._reply_buffer = bytearray(3)
        self.crc = CRC8()
        self._measure_command = bytearray(b"\x26\x0f\x80\x00\xa2\x66\x66\x93")
        self._voc_algorithm: VOCAlgorithm | None = None

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
        # recycle self._reply_buffer for read/write w/length; fall back to a fresh allocation only
        # if replylen doesn't match its pre-sized length (never happens today - see __init__).
        replybuffer = self._reply_buffer if replylen == len(self._reply_buffer) else bytearray(replylen)

        async with sgp40.i2c_device as i2c:  # bus session
            await i2c.write(self._command_buffer)
        await asyncio.sleep(round(delay_ms * 0.001, 3))
        async with sgp40.i2c_device as i2c:
            await i2c.readinto(replybuffer, end=replylen)

        for i in range(0, replylen, 3):
            if await self.crc.check_from(replybuffer, 3, start=i) is None:
                raise RuntimeError("CRC check failed while reading data")
            readdata_buffer.append(unpack_from(">H", replybuffer, i)[0])

        return readdata_buffer

    async def _reset(self) -> None:
        # True I2C general-call reset (datasheet Table 17): 0x06 to the reserved address 0x00,
        # broadcast to every device on the bus. A NAK (OSError) is expected, not a failure.
        async with self.i2c_sgp40 as sgp40, sgp40.i2c_device as i2c:
            try:
                i2c.i2c.writeto(0x00, b"\x06")
            except OSError:
                pass
        await asyncio.sleep(1)

    @staticmethod
    def _celsius_to_ticks(temperature: float, buf: bytearray | memoryview) -> None:
        # Temperature-to-ticks, datasheet Table 10: 25C->0x6666, -45C->0x0000, 130C->0xFFFF.
        # Rounds to nearest (matching _relative_humidity_to_ticks below) rather than truncating.
        temp_ticks = int(((temperature + 45) * 65535) / 175 + 0.5) & 0xFFFF
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
            self._command_buffer = self._default_command_buffer
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

    async def setup(self) -> None:
        async with self.i2c_sgp40 as sgp40, sgp40.i2c_device as i2c:
            await i2c.setup()
        await self.initialize()

    async def initialize(self) -> None:
        # Only the serial-number read and self-test (datasheet Table 8) gate success - the
        # feature-set check the legacy driver had isn't datasheet-documented.
        async with self.i2c_sgp40 as sgp40:  # device session
            self._command_buffer[0] = 0x36
            self._command_buffer[1] = 0x82
            serialnumber = await self._read_word_from_command(sgp40, delay_ms=3)
        if serialnumber is None:
            raise RuntimeError("No sensor response!")
        if serialnumber[0] != 0x0000:
            # word[0]==0 isn't documented by Sensirion (no structural breakdown of the 3-word ID
            # given) or replicated by any other reference driver checked - unverified, inherited
            # from Adafruit; kept since it's observed working on deployed hardware.
            raise RuntimeError("Serial number does not match")

        async with self.i2c_sgp40 as sgp40:  # device session
            self._command_buffer[0] = 0x28
            self._command_buffer[1] = 0x0E
            self_test = await self._read_word_from_command(sgp40, delay_ms=500)
        if self_test is None:
            raise RuntimeError("No sensor response!")
        # Datasheet Table 13: only the high byte is the pass/fail marker (0xD4/0x4B); the low
        # byte is documented as "ignore", not guaranteed zero.
        if (self_test[0] >> 8) != _SELF_TEST_PASS:
            raise RuntimeError("Self test failed")
        await self._reset()
