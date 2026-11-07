# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_sgp40`
================================================================================

CircuitPython library for the Adafruit SGP40 Air Quality Sensor / VOC Index Sensor Breakouts

"""
import asyncio
import time
import math
from struct import unpack_from
from asy_i2c_driver import I2CDevice, I2C
from machine import Timer
from async_manager import DataManager, TimeCounterManager
from micropython import const

# roughly the time how often the data written to the FRAM is verified.
# less a data safety feature here but rather a check if communication and integrity is generally okay
_FRAM_VERIFY_MINS = const(60)

class SGP40_Reader:
    def __init__(self, i2c, asy_comp_callback, asy_cfg_callback, ts_storage=None, max_i2c_err=5, debug=False):
        self.sgp = SGP40(i2c)
        self.meas_data = DataManager(3)
        self.trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_timer = Timer()
        self.error_counter = TimeCounterManager()  # use inherently limited counter here as overall error counter
        self.max_i2c_err = max_i2c_err
        self.comp_callback = asy_comp_callback  # expects [Temperature, Humidity]
        self.cfg_callback = asy_cfg_callback    # expects [backup period(mins), max restore age(mins), backup wait time for ntp synced(secs)]
        self.ts_storage = ts_storage  # timestamped backup storage (FRAM)
        self.last_backup = None
        self.restored_from = None
        self.reset = False
        self.debug = debug

    def start_asy_read(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_sgp())

    def start_timer(self):  # voc algorithm needs 1s period fixed
        self.trigger_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda b: self.trigger_event.set())

    def stop_timer(self):
        self.trigger_timer.deinit()

    async def get_error_counter(self):
        return await self.error_counter.get_counter()
    
    async def get_mem_error_counters(self):
        if self.ts_storage is None:
            return 0, 0, -1
        return await self.ts_storage.get_error_counters()
    
    async def get_mem_status(self):
        return self.last_backup, self.restored_from
    
    async def get_data(self, startIdx=0, length=-1):
        return await self.meas_data.get_data(startIdx=startIdx, length=length)

    async def reset_voc(self, flag):
        if flag:
            self.reset = True

    async def read_sgp(self):
        err_cnt = 0
        backup_counter = 0
        voc_init = 1
        voc_write = 1
        serialize = False
        deserialize = None
        try:
            await self.sgp.setup()
        except:
            err_cnt = 1

        (valid, [backup_period, backup_maxage, wait_ntp]) = await self.cfg_callback()
        if valid:
            if (self.ts_storage is not None) and (backup_period > 0): # backup verification period setting
                await self.ts_storage.set_verify(int(math.ceil((10 * _FRAM_VERIFY_MINS) / backup_period) * 0.1))
            if 1 <= wait_ntp <= 600:  # wait ntp between 1sec and 10mins
                voc_init = wait_ntp
                voc_write = wait_ntp
        else:
            err_cnt = 1
        del wait_ntp

        if err_cnt != 0:
            await self.error_counter.increment()
            if self.debug: print("Error reading SGP40 config data / setting sensor at startup!")
            return False
        while True:
            await self.trigger_event.wait()
            reset = False
            (valid, [backup_period, backup_maxage, wait_ntp]) = await self.cfg_callback()
            del wait_ntp
            backup_counter += 1
            if valid:
                if voc_init > 0:
                    if self.ts_storage is None:
                        voc_init = 0
                    else:
                        if self.debug: print("SGP40 VOC Backup laden Trigger")
                        voc_init -= 1
                        ts, age, deserialize = await self.ts_storage.read()  # any value returns as None if not valid
                        if deserialize is None:
                            if self.debug: print("SGP40 Kein Backup gefunden!")
                            voc_init = 0
                        else:  # backup found
                            if ts is None:
                                if self.debug: print("SGP40 Backup ohne Zeitstempel geladen")
                                voc_init = 0
                                ts = -1   # means valid data, no timestamp
                            else: # backup has valid timestamp
                                if age is None:
                                    if voc_init > 0:
                                        if self.debug: print("SGP40 Backup mit Zeitstempel gefunden, NTP Wartezeit:", voc_init)
                                        deserialize = None
                                else:
                                    if self.debug: print("SGP40 Backup mit Zeitstempel geladen")
                                    voc_init = 0
                                    if (backup_maxage > 0) and (age > (60 * backup_maxage)):
                                        if self.debug: print("SGP40 Backup ist zu alt")
                                        deserialize = None
                        if deserialize is not None:
                            self.restored_from = ts
                        del ts, age

                if (self.ts_storage is not None) and (backup_period > 0) and (backup_counter >= (60 * backup_period)):
                    backup_counter = 0
                    serialize = True
            else:  # valid
                if self.debug: print("Error reading SGP40 config data!")
                await self.error_counter.increment()
                serialize = False
                deserialize = None

            if backup_counter >= 100000: # # counts seconds, resets at 86400 = 1 day, give it some more space
                backup_counter = 0
            
            if self.reset:
                if self.debug: print("SGP40 Reset Trigger")
                backup_counter = 0
                reset = True
                serialize = False
                deserialize = None
                self.last_backup = None
                self.restored_from = None
                if self.ts_storage is not None:
                    if not await self.ts_storage.clear():
                        await self.error_counter.increment()
                        if self.debug: print("SGP40 Fehler beim FRAM löschen!")
                self.reset = False
            
            [Temp, Hum] = await self.comp_callback()
            if (Temp is None) or (Hum is None):
                if self.debug: print("SGP40 hat keine Kompensationsdaten!")
            else:
                err = False
                try:
                    Timestamp = time.mktime(time.gmtime())
                    (VOC_Index, 
                    raw, 
                    bytearr, 
                    deserialized) = await self.sgp.measure_index_and_raw(temperature=Temp,
                                                                         relative_humidity=Hum,
                                                                         serialize = serialize,
                                                                         deserialize = deserialize,
                                                                         reset = reset)
                    if self.debug: print("SGP40 gelesen")
                except:
                    err = True
                    Timestamp = None
                    VOC_Index = None
                    raw = None
                    bytearr = None
                    deserialized = False
                    if self.debug: print("SGP40 Lesefehler!")
                if err:
                    err_cnt += 1
                    await self.error_counter.increment()
                    if self.debug: print("SGP40 Fehlerzähler erhöht auf", err_cnt)
                    if err_cnt > self.max_i2c_err:
                        if self.debug: print("SGP40 Maximale Fehleranzahl erreicht!")
                        return False    # Abbruch der Schleife führt zu System-Reset
                else:
                    if err_cnt > 0:
                        err_cnt -= 1
                        if self.debug: print("SGP40 Fehlerzähler zurück auf", err_cnt)
                    await self.meas_data.set_data([VOC_Index, raw, Timestamp])
                    if self.debug: print("SGP40 Daten gespeichert")
                
                reset = False
                deserialize = None
                
                if valid and serialize:
                    if self.debug: print("SGP40 Backup Trigger.")
                    if self.ts_storage is None:
                        voc_write = 0
                        serialize = False
                    else:
                        if backup_period > 0: # backup verification period setting
                            current_verify = await self.ts_storage.get_verify()
                            desired_verify = int(math.ceil((10 * _FRAM_VERIFY_MINS) / backup_period) * 0.1)
                            if current_verify != desired_verify:
                                await self.ts_storage.set_verify(desired_verify)
                            del current_verify, desired_verify
                        if voc_write > 0:
                            voc_write -= 1
                        if bytearr is None:
                            await self.error_counter.increment()
                            serialize = False
                            if self.debug: print("SGP40 Fehler beim Serialisieren!")
                        else:
                            if self.debug: print("SGP40 Schreibe Backup.")
                            require_ntp = (voc_write > 0)
                            ntp_synced, ts, res = await self.ts_storage.write(bytearr, require_ntp=require_ntp)
                            if require_ntp:
                                if ntp_synced:
                                    voc_write = 0
                                    self.last_backup = ts
                                    serialize = False
                                    if self.debug: print("SGP40 Backup mit Zeitstempel geschrieben.")
                                else:
                                    res = True
                                    if self.debug: print("SGP40 Backup NTP Wartezeit:", voc_write)
                            else:  # require_ntp
                                self.last_backup = ts
                                serialize = False
                                if self.debug: print("SGP40 Backup ohne Zeitstempel geschrieben.")
                            if not res:
                                await self.error_counter.increment()
                                serialize = False
                                if self.debug: print("SGP40 Schreibfehler beim Backup!")
                            del require_ntp, ntp_synced, ts, res


class SGP40:
    """
    Class to use the SGP40 Air Quality Sensor Breakout

    :param int address: The I2C address of the device. Defaults to :const:`0x59`


    **Quickstart: Importing and using the SGP40 temperature sensor**

        Here is one way of importing the `SGP40` class so you can use it with the name ``sgp``.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import adafruit_sgp40
            # If you have a temperature sensor, like the bme280, import that here as well
            # import adafruit_bme280

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()  # uses board.SCL and board.SDA
            sgp = adafruit_sgp40.SGP40(i2c)
            # And if you have a temp/humidity sensor, define the sensor here as well
            # bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

        Now you have access to the raw gas value using the :attr:`raw` attribute.
        And with a temperature and humidity value, you can access the class function
        :meth:`measure_raw` for a humidity compensated raw reading

        .. code-block:: python

            raw_gas_value = sgp.raw
            # Lets quickly grab the humidity and temperature
            # temperature = bme280.temperature
            # humidity = bme280.relative_humidity
            # compensated_raw_gas = sgp.measure_raw(temperature=temperature,
            # relative_humidity=humidity)
            # temperature = temperature, relative_humidity = humidity)



    .. note::
        The operational range of temperatures for the SGP40 is -10 to 50 degrees Celsius
        and the operational range of relative humidity for the SGP40 is 0 to 90 %
        (assuming that humidity is non-condensing).

        Humidity compensation is further optimized for a subset of the temperature
        and relative humidity readings. See Figure 3 of the Sensirion datasheet for
        the SGP40. At 25 degrees Celsius, the optimal range for relative humidity is 8% to 90%.
        At 50% relative humidity, the optimal range for temperature is -7 to 42 degrees Celsius.

        Prolonged exposures outside of these ranges may reduce sensor performance, and
        the sensor must not be exposed towards condensing conditions at any time.

        For more information see:
        https://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/9_Gas_Sensors/Datasheets/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf
        and
        https://learn.adafruit.com/adafruit-sgp40

    """

    def __init__(self, i2c: I2C, address: int = 0x59) -> None:
        self.i2c_device = I2CDevice(i2c, address)
        self._command_buffer = bytearray(2)
        self._measure_command = b"\x26\x0F\x80\x00\xA2\x66\x66\x93"
        self._voc_algorithm = None

    async def setup(self) -> None:
        await self.i2c_device.setup()
        await self.initialize()

    async def initialize(self) -> None:
        """Reset the sensor to it's initial unconfigured state and configure it with sensible
        defaults so it can be used"""
        # check serial number
        self._command_buffer[0] = 0x36
        self._command_buffer[1] = 0x82
        serialnumber = await self._read_word_from_command(3)

        if serialnumber[0] != 0x0000:
            raise RuntimeError("Serial number does not match")

        # Check feature set
        self._command_buffer[0] = 0x20
        self._command_buffer[1] = 0x2F
        featureset = await self._read_word_from_command()
        if featureset[0] & 0xFF00 != 0x3200:
            raise RuntimeError(f"Feature set does not match: {featureset[0]:#x}")

        # Self Test
        self._command_buffer[0] = 0x28
        self._command_buffer[1] = 0x0E
        self_test = await self._read_word_from_command(delay_ms=500)
        if self_test[0] != 0xD400:
            raise RuntimeError("Self test failed")
        self._reset()

    async def _reset(self) -> None:
        # This is a general call Reset. Several sensors may see this and it doesn't appear to
        # ACK before resetting
        self._command_buffer[0] = 0x00
        self._command_buffer[1] = 0x06
        try:
            await self._read_word_from_command(delay_ms=50)
        except (OSError, RuntimeError):
            # Got expected OSError from reset
            # or RuntimeError on some Blinka setups
            pass
        await asyncio.sleep(1)

    @staticmethod
    def _celsius_to_ticks(temperature: float) -> List[int]:
        """
        Converts Temperature in Celsius to 'ticks' which are an input parameter
        the sgp40 can use

        Temperature to Ticks : From SGP40 Datasheet Table 10
        temp (C)    | Hex Code (Check Sum/CRC Hex Code)
            25      | 0x6666   (CRC 0x93)
            -45     | 0x0000   (CRC 0x81)
            130     | 0xFFFF   (CRC 0xAC)

        """
        temp_ticks = int(((temperature + 45) * 65535) / 175) & 0xFFFF
        least_sig_temp_ticks = temp_ticks & 0xFF
        most_sig_temp_ticks = (temp_ticks >> 8) & 0xFF

        return [most_sig_temp_ticks, least_sig_temp_ticks]

    @staticmethod
    def _relative_humidity_to_ticks(humidity: float) -> List[int]:
        """
        Converts Relative Humidity in % to 'ticks' which are  an input parameter
        the sgp40 can use

        Relative Humidity to Ticks : From SGP40 Datasheet Table 10
        Humidity (%) | Hex Code (Check Sum/CRC Hex Code)
            50       | 0x8000   (CRC 0xA2)
            0        | 0x0000   (CRC 0x81)
            100      | 0xFFFF   (CRC 0xAC)

        """
        humidity_ticks = int((humidity * 65535) / 100 + 0.5) & 0xFFFF
        least_sig_rhumidity_ticks = humidity_ticks & 0xFF
        most_sig_rhumidity_ticks = (humidity_ticks >> 8) & 0xFF

        return [most_sig_rhumidity_ticks, least_sig_rhumidity_ticks]

    async def get_raw(self) -> int:
        """The raw gas value"""
        # recycle a single buffer
        self._command_buffer = self._measure_command
        read_value = await self._read_word_from_command(delay_ms=500)
        self._command_buffer = bytearray(2)
        return read_value[0]

    async def measure_raw(self, temperature: float = 25, relative_humidity: float = 50):
        """
        A humidity and temperature compensated raw gas value which helps
        address fluctuations in readings due to changing humidity.


        :param float temperature: The temperature in degrees Celsius, defaults
                                     to :const:`25`
        :param float relative_humidity: The relative humidity in percentage, defaults
                                     to :const:`50`

        The raw gas value adjusted for the current temperature (c) and humidity (%)
        """
        # recycle a single buffer
        _compensated_read_cmd = [0x26, 0x0F]
        humidity_ticks = self._relative_humidity_to_ticks(relative_humidity)
        humidity_ticks.append(self._generate_crc(humidity_ticks))
        temp_ticks = self._celsius_to_ticks(temperature)
        temp_ticks.append(self._generate_crc(temp_ticks))
        _cmd = _compensated_read_cmd + humidity_ticks + temp_ticks
        self._measure_command = bytearray(_cmd)
        return await self.get_raw()

    async def measure_index_and_raw(self,
                                    temperature: float=25,
                                    relative_humidity: float=50,
                                    serialize=False,
                                    deserialize=None,
                                    reset=False):
        """Measure VOC index after humidity compensation
        :param float temperature: The temperature in degrees Celsius, defaults to :const:`25`
        :param float relative_humidity: The relative humidity in percentage, defaults to :const:`50`
        :note  VOC index can indicate the quality of the air directly.
        The larger the value, the worse the air quality.
        :note 0-100, no need to ventilate, purify
        :note 100-200, no need to ventilate, purify
        :note 200-400, ventilate, purify
        :note 400-500, ventilate, purify intensely
        :return int The VOC index measured, ranged from 0 to 500
        """
        # import/setup algorithm only on use of index
        # pylint: disable=import-outside-toplevel
        from asy_sgp40_driver.voc_algorithm import VOCAlgorithm

        if self._voc_algorithm is None:
            self._voc_algorithm = VOCAlgorithm()
            self._voc_algorithm.vocalgorithm_init()

        if reset:
            self._voc_algorithm.vocalgorithm_reset()

        raw = await self.measure_raw(temperature, relative_humidity)
        if raw < 0:
            return -1, raw, None, False
        
        (voc_index,
        bytearr,
        deserialized) = self._voc_algorithm.vocalgorithm_proc_ser_des(raw,
                                                                      serialize=serialize,
                                                                      deserialize=deserialize)
        return voc_index, raw, bytearr, deserialized     

    async def _read_word_from_command(
        self,
        delay_ms: int = 10,
        readlen: Optional[int] = 1,
    ) -> Optional[List[int]]:
        """_read_word_from_command - send a given command code and read the result back

        Args:
            delay_ms (int, optional): The delay between write and read, in milliseconds.
                Defaults to 10ms
            readlen (int, optional): The number of bytes to read. Defaults to 1.
        """
        # TODO: Take 2-byte command as int (0x280E, 0x0006) and packinto command buffer

        async with self.i2c_device as i2c:
            await i2c.write(self._command_buffer)

        await asyncio.sleep(round(delay_ms * 0.001, 3))

        if readlen is None:
            return None
        readdata_buffer = []

        # The number of bytes to read back, based on the number of words to read
        replylen = readlen * 3
        # recycle buffer for read/write w/length
        replybuffer = bytearray(replylen)

        async with self.i2c_device as i2c:
            await i2c.readinto(replybuffer, end=replylen)

        for i in range(0, replylen, 3):
            if not self._check_crc8(replybuffer[i : i + 2], replybuffer[i + 2]):
                raise RuntimeError("CRC check failed while reading data")
            readdata_buffer.append(unpack_from(">H", replybuffer[i : i + 2])[0])

        return readdata_buffer

    def _check_crc8(self, crc_buffer: ReadableBuffer, crc_value: int) -> bool:
        """
        Checks that the 8 bit CRC Checksum value from the sensor matches the
        received data
        """
        return crc_value == self._generate_crc(crc_buffer)

    @staticmethod
    def _generate_crc(crc_buffer: ReadableBuffer) -> int:
        """
        Generates an 8 bit CRC Checksum from the input buffer.

        This checksum algorithm is outlined in Table 7 of the SGP40 datasheet.

        Checksums are only generated for 2-byte data packets. Command codes already
        contain 3 bits of CRC and therefore do not need an added checksum.
        """
        crc = 0xFF
        for byte in crc_buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (
                        crc << 1
                    ) ^ 0x31  # 0x31 is the Seed for SGP40's CRC polynomial
                else:
                    crc = crc << 1
        return crc & 0xFF  # Returns only bottom 8 bits

