# SPDX-FileCopyrightText: 2018 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_mprls`
====================================================

CircuitPython library to support Honeywell MPRLS digital pressure sensors

* Author(s): ladyada

Implementation Notes
--------------------

**Hardware:**

* Adafruit `Adafruit MPRLS Ported Pressure Sensor Breakout
  <https://www.adafruit.com/product/3965>`_ (Product ID: 3965)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

# imports

import asyncio
import time
from asy_i2c_driver import I2CDevice, I2C
from machine import Pin
from micropython import const
from machine import Timer
from async_manager import DataManager, LockedValue, TimeCounterManager


_MPRLS_DEFAULT_ADDR = const(0x18)


class MPRLS_Reader:
    def __init__(self, i2c, asy_cfg_callback, reset_pin=None, eoc_pin=None, trigger_sec=1, max_i2c_err=5, debug=False):
        self.mprls = MPRLS(i2c, reset_pin=reset_pin, eoc_pin=eoc_pin)
        self.meas_data = DataManager(2)
        self.base_trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_timer = Timer()
        self.trigger_period = LockedValue(int(trigger_sec))
        self.trigger_counter = 0
        self.error_counter = TimeCounterManager()  # use inherently limited counter here as overall error counter
        self.max_i2c_err = max_i2c_err
        self.cfg_callback = asy_cfg_callback  # expects (valid, [MPRLSSampleInterval, PressureOffset, FilterCoefficient])
        self.debug = debug

    def start_asy_read(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_mprls())

    def start_asy_trigger(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._base_trigger())

    def start_timer(self):
        self.trigger_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda b: self.base_trigger_event.set())

    def stop_timer(self):
        self.trigger_timer.deinit()

    async def set_trigger_secs(self, value):
        await self.trigger_period.setValue(int(value))

    async def get_error_counter(self):
        return await self.error_counter.get_counter()

    async def get_data(self, startIdx=0, length=-1):
        return await self.meas_data.get_data(startIdx=startIdx, length=length)

    async def _base_trigger(self):
        self.trigger_counter = 0
        while True:
            await self.base_trigger_event.wait()
            self.trigger_counter += 1
            if self.trigger_counter >= await self.trigger_period.getValue():
                self.trigger_event.set()
                if self.debug: print("MPRLS sensor trigger, period:", self.trigger_counter)
                self.trigger_counter = 0

    async def read_mprls(self):
        err_cnt = 0
        try:
            await self.mprls.setup()
        except:
            err_cnt = 1
        (valid, [SInt, POffs, FiltCoeff]) = await self.cfg_callback()
        del POffs, FiltCoeff
        if valid:
            await self.trigger_period.setValue(SInt)
            if self.debug: print("Setting MPRLS sensor config at startup.")
        else:  # valid
            err_cnt = 1
        del valid, SInt

        if err_cnt != 0:
            await self.error_counter.increment()
            if self.debug: print("Error reading MPRLS config data / setting sensor at startup!")
            return False
        while True:
            await self.trigger_event.wait()
            err = False
            try:
                Timestamp = time.mktime(time.gmtime())
                Pressure = await self.mprls.get_pressure()
                if self.debug: print("MPRLS gelesen")
            except:
                err = True
                Timestamp = None
                Pressure = None
                if self.debug: print("MPRLS Lesefehler!")

            if err:
                await self.error_counter.increment()
                err_cnt += 1
                if self.debug: print("MPRLS Fehlerzähler erhöht auf", err_cnt)
                if err_cnt > self.max_i2c_err:
                    if self.debug: print("MPRLS Maximale Fehleranzahl erreicht!")
                    return False    # Abbruch der Schleife führt zu System-Reset
            else:
                if err_cnt > 0:
                    err_cnt -= 1
                    if self.debug: print("MPRLS Fehlerzähler zurück auf", err_cnt)

                (valid, [SInt, POffs, FiltCoeff]) = await self.cfg_callback()
                del SInt
                if not valid:
                    POffs = 0.0
                    FiltCoeff = 0.0
                    await self.error_counter.increment()
                    if self.debug: print("Error reading MPRLS config data!")

                pc = Pressure - POffs
                if FiltCoeff > 0.0:  # optional first-order lowpass filter
                    if FiltCoeff > 1.0: FiltCoeff = 1.0
                    [pc_old] = await self.meas_data.get_data(startIdx=0, length=1)
                    if pc_old is not None:
                        pc = pc_old + (FiltCoeff * (pc - pc_old))

                await self.meas_data.set_data([pc, Timestamp])
                if self.debug: print("MPRLS Daten gespeichert")
                del POffs


class MPRLS:
    """
    Driver base for the MPRLS pressure sensor

    :param ~busio.I2C i2c_bus: The I2C bus the MPRLS is connected to
    :param int addr: The I2C device address. Defaults to :const:`0x18`
    :param ~microcontroller.Pin reset_pin: Optional ``digitalio.pin`` for hardware resetting
    :param ~microcontroller.Pin eoc_pin: Optional ``digitalio pin``
                                         for getting End Of Conversion signal
    :param float psi_min: The minimum pressure in PSI, defaults to :const:`0`
    :param float psi_max: The maximum pressure in PSI, defaults to :const:`25`

    """

    def __init__(self, i2c_bus, *, addr=_MPRLS_DEFAULT_ADDR, reset_pin=None, eoc_pin=None, psi_min=0.0, psi_max=25.0):
        # Init I2C
        self._i2c_device = I2CDevice(i2c_bus, addr)
        self._buffer = bytearray(4)

        if psi_min >= psi_max:
            raise ValueError("Min PSI must be < max!")
        self._psimax = psi_max
        self._psimin = psi_min

        if reset_pin is not None:  # Optional hardware reset pin
            self._reset_pin = Pin(reset_pin, mode=Pin.OUT)
        else:
            self._reset_pin = None

        if eoc_pin is not None:  # Optional end-of-conversion pin
            self._eoc_pin = Pin(eoc_pin, mode=Pin.IN)
        else:
            self._eoc_pin = None

    async def setup(self):
        await self.reset()
        await self._i2c_device.setup()

    async def reset(self):
        if self._reset_pin is not None:
            self._reset_pin.value(1)
            await asyncio.sleep(0.01)
            self._reset_pin.value(0)
            await asyncio.sleep(0.01)
            self._reset_pin.value(1)
            await asyncio.sleep(0.005)  # Start up timing

    async def get_pressure(self):
        """The measured pressure, in hPa"""
        return await self._read_data()

    async def _read_data(self):
        """Read the status & 24-bit data reading"""
        self._buffer[0] = 0xAA
        self._buffer[1] = 0
        self._buffer[2] = 0
        async with self._i2c_device as i2c:
            # send command
            await i2c.write(self._buffer, end=3)
            # ready busy flag/status
            while True:
                # check End of Convert pin first, if we can
                if self._eoc_pin is not None:
                    if self._eoc_pin.value() == 1:
                        break
                else: # or you can read the status byte
                    await i2c.readinto(self._buffer, end=1)
                    if not self._buffer[0] & 0x20:
                        break
                await asyncio.sleep(0.005) # 5ms conversion time
            # no longer busy!
            await i2c.readinto(self._buffer, end=4)

        # check other status bits
        if self._buffer[0] & 0x01:
            raise RuntimeError("Internal math saturation")
        if self._buffer[0] & 0x04:
            raise RuntimeError("Integrity failure")

        # All is good, calculate the PSI and convert to hPA
        raw_psi = (self._buffer[1] << 16) | (self._buffer[2] << 8) | self._buffer[3]
        # use the 10-90 calibration curve
        psi = (raw_psi - 0x19999A) * (self._psimax - self._psimin)
        psi /= 0xE66666 - 0x19999A
        psi += self._psimin
        # convert PSI to hPA
        return psi * 68.947572932
