
# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya
#
# SPDX-License-Identifier: MIT
"""
`isl29125`
================================================================================

MicroPython Driver for the Intersil ISL29125 Color Sensor


"""
import asyncio
import time
from micropython import const
from asy_i2c_driver import I2CDevice, I2C
from machine import Pin
from machine import Timer
from async_manager import DataManager, LockedValue, TimeCounterManager


# Device registers
_REG_WHOAMI = const(0x00)
_CONFIG1 = const(0x01)
_CONFIG2 = const(0x02)
_CONFIG3 = const(0x03)
_FLAG_REGISTER = const(0x08)

# Operation Modes
POWERDOWN = const(0b000)
GREEN_ONLY = const(0b001)
RED_ONLY = const(0b010)
BLUE_ONLY = const(0b11)
STANDBY = const(0b100)  # No ADC Conversion
RED_GREEN_BLUE = const(0b101)
GREEN_RED = const(0b110)
GREEN_BLUE = const(0b111)

# Sensing Range
LUX_375 = const(0b0)
LUX_10K = const(0b1)

# ADC Resolution
RES_16BITS = const(0b0)
RES_12BITS = const(0b1)

# IR compensation
IR_OFF = const(0b0)
IR_ON = const(0b1)

# Interrupt
NO_INTERRUPT = const(0b00)
GREEN_INTERRUPT = const(0b01)
RED_INTERRUPT = const(0b10)
BLUE_INTERRUPT = const(0b11)

# Persistent Control
IC1 = const(0b00)
IC2 = const(0b01)
IC4 = const(0b10)
IC8 = const(0b11)


class ISL29125_Reader:
    def __init__(self, i2c, asy_cfg_callback, irq_callback=None, irq_pin=None, trigger_sec=1, max_i2c_err=5, debug=False):
        self.isl = ISL29125(i2c)
        self.meas_data = DataManager(4)
        self.base_trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_event = asyncio.ThreadSafeFlag()
        self.irq_triggered = asyncio.ThreadSafeFlag()
        self.trigger_timer = Timer()
        self.trigger_period = LockedValue(int(trigger_sec))
        self.trigger_counter = 0
        self.error_counter = TimeCounterManager()  # use inherently limited counter here as overall error counter
        self.max_i2c_err = max_i2c_err
        self.cfg_callback = asy_cfg_callback
        # expects (valid, [ISLSampleInterval, ISLOperationMode, ISLSensingRange, ISLAdcResolution, ISLIrCompensation,
        #                  ISLInterruptAssignment, ISLInterruptHighThres, ISLInterruptLowThres, ISLInterruptAutoClear, ISLPersistentControl])
        self.debug = debug

        self.irq_auto_clear = -1
        self.irq_pin = None
        self.irq_callback = irq_callback
        self.irq_waiting = False
        if irq_pin is not None:
            self.irq_pin = Pin(irq_pin, mode=Pin.IN)
            self.irq_pin.irq(trigger=self.irq_pin.IRQ_FALLING, handler=lambda b: self.irq_triggered.set())

        # defaults:
        # ISLSampleInterval = 1s
        # ISLOperationMode: 0b101 = 5 = RGB
        # ISLSensingRange: 0b1 = 1 = LUX_10K
        # ISLAdcResolution: 0b0 = 0 = 16bit
        # ISLIrCompensation = 63 = on / max (-1 = off)
        # ISLInterruptAssignment = 0 = NO_INT
        # ISLInterruptHighThres = 65535 = max
        # ISLInterruptLowThres = 0 = min
        # ISLPersistentControl = 0 = IC1

    def start_asy_read(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_isl29125())

    def start_asy_trigger(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._base_trigger())

    def start_irq_handler(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._interrupt_handler())

    def start_timer(self):
        self.trigger_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda b: self.base_trigger_event.set())

    def stop_timer(self):
        self.trigger_timer.deinit()

    async def set_irq_auto_clear(self, value):
        self.irq_auto_clear = value

    async def get_irq_auto_clear(self):
        return self.irq_auto_clear

    async def set_trigger_secs(self, value):
        await self.trigger_period.setValue(int(value))

    async def get_trigger_secs(self):
        return await self.trigger_period.getValue()

    async def get_error_counter(self):
        return await self.error_counter.get_counter()

    async def get_data(self, startIdx=0, length=-1):
        return await self.meas_data.get_data(startIdx=startIdx, length=length)

    async def _base_trigger(self):
        self.trigger_counter = 0
        while True:
            await self.base_trigger_event.wait()
            if (self.irq_pin.value() == 0) and not self.irq_waiting:  # Interrupt pin is currently set but not triggered
                await self.isl.clear_register_flag()  # clear interrupt flag
                if self.debug: print("ISL29125 sensor interrupt init-cleared.")
            self.trigger_counter += 1
            if self.trigger_counter >= await self.trigger_period.getValue():
                self.trigger_event.set()
                if self.debug: print("ISL29125 sensor trigger, period:", self.trigger_counter)
                self.trigger_counter = 0

    async def _interrupt_handler(self):
        while True:
            await self.irq_triggered.wait()
            if self.debug: print("ISL29125 sensor interrupt triggered.")
            if self.irq_callback is not None:
                rgb = await self.isl.get_colors()
                self.irq_callback(rgb)
                if self.irq_auto_clear > 0:
                    self.irq_waiting = True
                    await asyncio.sleep_ms(self.irq_auto_clear)
                if self.irq_auto_clear >= 0:
                    await self.isl.clear_register_flag()  # clear interrupt flag
                    self.irq_waiting = False
                    if self.debug: print("ISL29125 sensor interrupt cleared.")

    async def read_isl29125(self):
        err_cnt = 0
        try:
            await self.isl.setup()
        except:
            err_cnt = 1
        (valid, [SInt, OpMode, SensRange, AdcRes, IrComp,
                 IntAss, IntHiThres, IntLoThres, AutoClr, PersCtl]) = await self.cfg_callback()
        if valid:
            try:
                self.irq_auto_clear = AutoClr
                await self.trigger_period.setValue(SInt)
                await self.isl.set_operation_mode(OpMode)
                await self.isl.set_sensing_range(SensRange)
                await self.isl.set_adc_resolution(AdcRes)
                
                if IrComp < 0:
                    await self.isl.set_ir_compensation(0)
                    await self.isl.set_ir_compensation_value(0)
                else:
                    await self.isl.set_ir_compensation(1)
                    await self.isl.set_ir_compensation_value(IrComp)
                
                await self.isl.set_interrupt_assignment(IntAss)
                await self.isl.set_high_threshold(IntHiThres)
                await self.isl.set_low_threshold(IntLoThres)
                await self.isl.set_persistent_control(PersCtl)
            except:
                err_cnt = 1
            if self.debug: print("Setting ISL29125 sensor config at startup.")
        else:  # valid
            err_cnt = 1
        del valid, SInt, OpMode, SensRange, AdcRes, IrComp, IntAss, IntHiThres, IntLoThres, PersCtl

        if err_cnt != 0:
            await self.error_counter.increment()
            if self.debug: print("Error reading ISL29125 config data / setting sensor at startup!")
            return False
        while True:
            await self.trigger_event.wait()
            try:
                Timestamp = time.mktime(time.gmtime())
                red, green, blue = await self.isl.get_colors()
                if self.debug: print("ISL29125 gelesen")
            except:
                Timestamp = None
                red = None
                green = None
                blue = None
                if self.debug: print("ISL29125 Lesefehler!")
            # no err flag here; red, green, blue can also return as None from the driver!
            if (Timestamp is None) or (red is None) or (green is None) or (blue is None):
                await self.error_counter.increment()
                err_cnt += 1
                if self.debug: print("ISL29125 Fehlerzähler erhöht auf", err_cnt)
                if err_cnt > self.max_i2c_err:
                    if self.debug: print("ISL29125 Maximale Fehleranzahl erreicht!")
                    return False    # Abbruch der Schleife führt zu System-Reset
            else:
                if err_cnt > 0:
                    err_cnt -= 1
                    if self.debug: print("ISL29125 Fehlerzähler zurück auf", err_cnt)

                await self.meas_data.set_data([red, green, blue, Timestamp])
                if self.debug: print("ISL29125 Daten gespeichert")

    async def get_interrupt_triggered(self):
        return await self.isl.get_interrupt_triggered()

    async def clear_register_flag(self):
        return await self.isl.clear_register_flag()

    async def set_operation_mode(self, OpMode):
        await self.isl.set_operation_mode(OpMode)

    async def get_operation_mode(self):
        return await self.isl.get_operation_mode()

    async def set_sensing_range(self, SensRange):
        await self.isl.set_sensing_range(SensRange)

    async def get_sensing_range(self):
        return await self.isl.get_sensing_range()

    async def set_adc_resolution(self, AdcRes):
        await self.isl.set_adc_resolution(AdcRes)

    async def get_adc_resolution(self):
        return await self.isl.get_adc_resolution()

    async def set_ir_compensation(self, IrComp):
        if IrComp < 0:
            await self.isl.set_ir_compensation(0)
            await self.isl.set_ir_compensation_value(0)
        else:
            await self.isl.set_ir_compensation(1)
            await self.isl.set_ir_compensation_value(IrComp)
        
    async def get_ir_compensation(self):
        IrComp = await self.isl.get_ir_compensation()
        if IrComp == 0:
            return -1
        return await self.isl.get_ir_compensation_value()
        
    async def set_interrupt_assignment(self, IntAss):
        await self.isl.set_interrupt_assignment(IntAss)

    async def get_interrupt_assignment(self):
        return await self.isl.get_interrupt_assignment()

    async def set_high_threshold(self, IntHiThres):
        await self.isl.set_high_threshold(IntHiThres)

    async def get_high_threshold(self):
        return await self.isl.get_high_threshold()

    async def set_low_threshold(self, IntLoThres):
        await self.isl.set_low_threshold(IntLoThres)

    async def get_low_threshold(self):
        return await self.isl.get_low_threshold()

    async def set_persistent_control(self, PersCtl):
        await self.isl.set_persistent_control(PersCtl)

    async def get_persistent_control(self):
        return await self.isl.get_persistent_control()


class ISL29125:
    """Driver for the ISL29125 Sensor connected over I2C.
    :param I2C i2c_bus: The I2C bus the ISL29125 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x44`
    :raises RuntimeError: if the sensor is not found
    """

    def __init__(self, i2c_bus, address=0x44):
        self.i2c_device = I2CDevice(i2c_bus, address)

    async def setup(self):
        await self.i2c_device.setup()
        dev_id = await self._get_reg(_REG_WHOAMI, "B")
        if dev_id != 0x7D:
            raise RuntimeError("Failed to find the ISL29125")
        await self.reset()
        await self.clear_register_flag()
        await self._set_bits(1, _FLAG_REGISTER, 2, 0) # Setting the brownout to 0 according to datasheet recommendation

    async def reset(self):
        await self._set_reg(_REG_WHOAMI, "B", 0x46)   # writing 0x46 to dev id register resets device to default

    async def get_green(self):
        return await self._get_reg(0x09, "H")

    async def get_red(self):
        return await self._get_reg(0x0B, "H")

    async def get_blue(self):
        return await self._get_reg(0x0D, "H")

    async def get_colors(self):
        red = await self._get_reg(0x0B, "H")
        green = await self._get_reg(0x09, "H")
        blue = await self._get_reg(0x0D, "H")
        return red, green, blue

    async def get_operation_mode(self):
        """The device has various RGB operating modes. The device powers up on
        a disable mode. All operating modes are in continuous ADC
        conversion. The following bits are used to enable the operating mode
        +----------------------------------------+-------------------------+
        | Mode                                   | Value                   |
        +========================================+=========================+
        | :py:const:`isl29125.POWERDOWN`         | :py:const:`0b000`       |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.GREEN_ONLY`        | :py:const:`0b001`       |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.RED_ONLY`          | :py:const:`0b010`       |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.BLUE_ONLY`         | :py:const:`0b011`       |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.STANDBY`           | :py:const:`0b100`       |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.RED_GREEN_BLUE`    | :py:const:`0b101`       |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.GREEN_RED`         | :py:const:`0b110`       |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.GREEN_BLUE`        | :py:const:`0b111`       |
        +----------------------------------------+-------------------------+
        """
        values = ("POWERDOWN", "GREEN_ONLY", "RED_ONLY", "BLUE_ONLY", "STANDBY", "RED_GREEN_BLUE", "GREEN_RED", "GREEN_BLUE")
        opmode = await self._get_bits(3, _CONFIG1, 0)
        return values[opmode]

    async def set_operation_mode(self, value):
        operation_values = (POWERDOWN, GREEN_ONLY, RED_ONLY, BLUE_ONLY, STANDBY, RED_GREEN_BLUE, GREEN_RED, GREEN_BLUE)
        if value not in operation_values:
            raise ValueError("Value must be a valid operation mode setting")
        await self._set_bits(3, _CONFIG1, 0, value)

    async def get_sensing_range(self):
        """The Full Scale RGB Range has two different selectable ranges at bit 3.
         The range determines the ADC resolution (12 bits and 16 bits).
         Each range has a maximum allowable lux value. Higher range values offer
         better resolution and wider lux value
        +----------------------------------------+----------------------------------+
        | Mode                                   | Value                            |
        +========================================+==================================+
        | :py:const:`isl29125.LUX_375`           | :py:const:`0b0` 375 lux          |
        +----------------------------------------+----------------------------------+
        | :py:const:`isl29125.LUX_10K`           | :py:const:`0b1` 10000 lux        |
        +----------------------------------------+----------------------------------+
        """
        values = ("LUX_375", "LUX_10K")
        sensrange = await self._get_bits(1, _CONFIG1, 3)
        return values[sensrange]

    async def set_sensing_range(self, value):
        sensing_range_values = (LUX_375, LUX_10K)
        if value not in sensing_range_values:
            raise ValueError("Value must be a valid sensing range setting")
        await self._set_bits(1, _CONFIG1, 3, value)

    async def get_adc_resolution(self):
        """ADC's resolution and the number of clock cycles per conversion is
        determined by this bit. Changing the resolution of the ADC, changes the
        number of clock cycles of the ADC which in turn changes the integration time.
        Integration time is the period the ADC samples the photodiode current signal
        for a measurement
        +----------------------------------------+----------------------------------+
        | Mode                                   | Value                            |
        +========================================+==================================+
        | :py:const:`isl29125.RES_16BITS`        | :py:const:`0b0` 16 bits          |
        +----------------------------------------+----------------------------------+
        | :py:const:`isl29125.RES_12BITS`        | :py:const:`0b1` 12 bits          |
        +----------------------------------------+----------------------------------+
        """
        values = ("RES_16BITS", "RES_12BITS")
        adcres = await self._get_bits(1, _CONFIG1, 4)
        return values[adcres]
        
    async def set_adc_resolution(self, value):
        adc_resolution_values = (RES_16BITS, RES_12BITS)
        if value not in adc_resolution_values:
            raise ValueError("Value must be a valid adc resolution setting")
        await self._set_bits(1, _CONFIG1, 4, value)

    async def get_ir_compensation(self):
        """The device provides a programmable active IR compensation which allows fine-tuning
         of residual infrared components from the output which allows optimizing the measurement
          variation between differing IR-content light sources.
        +----------------------------------------+----------------------------------+
        | Mode                                   | Value                            |
        +========================================+==================================+
        | :py:const:`isl29125.IR_OFF`            | :py:const:`0b0`                  |
        +----------------------------------------+----------------------------------+
        | :py:const:`isl29125.IR_ON`             | :py:const:`0b1`                  |
        +----------------------------------------+----------------------------------+
        """
        values = ("IR_OFF", "IR_ON")
        ircomp = await self._get_bits(1, _CONFIG2, 7)
        return values[ircomp]

    async def set_ir_compensation(self, value):
        ir_compensation_values = (IR_OFF, IR_ON)
        if value not in ir_compensation_values:
            raise ValueError("Value must be a valid IR compensation setting")
        await self._set_bits(1, _CONFIG2, 7, value)

    async def get_ir_compensation_value(self):
        """The effective IR compensation is from 0 t0 63 and 106 to 169 in the CONF2 register.
        Consult datasheet for detailed IR filtering calibration
        Allowed values here are 6 bits equiv. 0 to 63.
        """
        ircompval = await self._get_bits(6, _CONFIG2, 0)
        return ircompval

    async def set_ir_compensation_value(self, value):
        if not (0 <= value <= 63):
            raise ValueError("Value must be a valid IR compensation setting")
        await self._set_bits(6, _CONFIG2, 0, value)

    async def get_interrupt_assignment(self):
        """The interrupt_assignment is the status bits for light intensity detection.
        The property:`interrupt_triggered` is set to logic HIGH when the light intensity
        crosses the interrupt thresholds window (register address 0x04 - 0x07)
        +----------------------------------------+----------------------------------+
        | Value                                  | Value                            |
        +========================================+==================================+
        | :py:const:`isl29125.NO_INTERRUPT`      | :py:const:`0b00`                 |
        +----------------------------------------+----------------------------------+
        | :py:const:`isl29125.GREEN_INTERRUPT`   | :py:const:`0b01`                 |
        +----------------------------------------+----------------------------------+
        | :py:const:`isl29125.RED_INTERRUPT`     | :py:const:`0b10`                 |
        +----------------------------------------+----------------------------------+
        | :py:const:`isl29125.BLUE_INTERRUPT`    | :py:const:`0b11`                 |
        +----------------------------------------+----------------------------------+
        """
        values = ("NO_INTERRUPT", "GREEN_INTERRUPT", "RED_INTERRUPT", "BLUE_INTERRUPT")
        intthres = await self._get_bits(2, _CONFIG3, 0)
        return values[intthres]

    async def set_interrupt_assignment(self, value):
        interrupt_values = (NO_INTERRUPT, GREEN_INTERRUPT, RED_INTERRUPT, BLUE_INTERRUPT)
        if value not in interrupt_values:
            raise ValueError("Value must be a valid interrupt assignment Value")
        await self._set_bits(2, _CONFIG3, 0, value)

    async def get_high_threshold(self):
        """
        The interrupt threshold level is a 16-bit number (Low Threshold-1 and Low Threshold-2).
        The lower interrupt threshold registers are used to set the lower trigger point for
        interrupt generation. If the ALS value crosses below or is equal to the lower
        threshold, an interrupt is asserted on the interrupt pin (LOW) and the interrupt
        status bit (HIGH).
        """
        high_thres = await self._get_reg(0x06, "H")
        return high_thres

    async def set_high_threshold(self, value):
        if not (0 <= value <= 65536):
            raise ValueError("Value must be a valid threshold setting")
        await self._set_reg(0x06, "H", value)

    async def get_low_threshold(self):
        """
        The interrupt threshold level is a 16-bit number (Low Threshold-1 and Low Threshold-2).
        The lower interrupt threshold registers are used to set the lower trigger point for
        interrupt generation. If the ALS value crosses below or is equal to the lower
        threshold, an interrupt is asserted on the interrupt pin (LOW) and the interrupt
        status bit (HIGH).
        """
        low_thres = await self._get_reg(0x04, "H")
        return low_thres

    async def set_low_threshold(self, value):
        if not (0 <= value <= 65536):
            raise ValueError("Value must be a valid threshold setting")
        await self._set_reg(0x04, "H", value)

    async def get_interrupt_triggered(self):
        """Is set to high when the interrupt threshold have been triggered (out of
        threshold window) and logic low when not yet triggered. Mapped to boolean.
        +----------------------------------------+----------------------------------+
        | Value                                  | Value                            |
        +========================================+==================================+
        | :py:const:`0b0`                        | Interrupt is cleared or          |
        |                                        | not triggered yet                |
        +----------------------------------------+----------------------------------+
        | :py:const:`0b1`                        | interrupt is triggered           |
        +----------------------------------------+----------------------------------+
        """
        triggered = await self._get_bits(1, _FLAG_REGISTER, 0)
        return triggered > 0

    async def get_persistent_control(self):
        """To minimize interrupt events due to 'transient' conditions, an
        interrupt persistence option is available. IN the event of transient
        condition an 'X-consecutive' number of interrupt must happen before
        the interrupt flag and pint (INT) pin gets driven low. The interrupt
        is active-low and remains asserted until clear_register_flag is called
        +----------------------------------------+-------------------------+
        | Mode                                   | Value                   |
        +========================================+=========================+
        | :py:const:`isl29125.IC1`               | :py:const:`0b00`        |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.IC2`               | :py:const:`0b01`        |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.IC4`               | :py:const:`0b10`        |
        +----------------------------------------+-------------------------+
        | :py:const:`isl29125.IC8`               | :py:const:`0b11`        |
        +----------------------------------------+-------------------------+
        """
        values = ("IC1", "IC2", "IC4", "IC8")
        int_pers_ctl = await self._get_bits(2, _CONFIG3, 2)
        return values[int_pers_ctl]

    async def set_persistent_control(self, value):
        persistent_control_values = (IC1, IC2, IC4, IC8)
        if value not in persistent_control_values:
            raise ValueError("Value must be a valid persistent control value")
        await self._set_bits(2, _CONFIG3, 2, value)

    async def clear_register_flag(self):
        """Clears the flag register performing a read action"""
        flag_reg = await self._get_reg(0x08, "B")
        return flag_reg

    async def _get_bits(self, num_bits, reg_addr, start_bit, reg_width=1, lsb_first=True):
        bits = None
        async with self.i2c_device as i2c:
            bits = await i2c.get_bits(num_bits, reg_addr, start_bit, reg_width, lsb_first)
        return bits

    async def _set_bits(self, num_bits, reg_addr, start_bit, value, reg_width=1, lsb_first=True):
        async with self.i2c_device as i2c:
             await i2c.set_bits(num_bits, reg_addr, start_bit, value, reg_width, lsb_first)

    async def _get_reg(self, reg_addr, reg_format):
        reg = None
        async with self.i2c_device as i2c:
            reg =  await i2c.get_register_struct(reg_addr, reg_format)
        return reg

    async def _set_reg(self, reg_addr, reg_format, value):
        async with self.i2c_device as i2c:
            reg =  await i2c.set_register_struct(reg_addr, reg_format, value)
