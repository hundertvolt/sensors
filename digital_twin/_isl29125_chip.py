"""Digital-twin chip fake for the Renesas/Intersil ISL29125 RGB colour sensor (I2C 0x44) — answers `asy_isl29125_driver.py`'s register-addressed protocol with G/R/B counts derived from a modelled illumination, through the real range gain, ADC resolution and clipping.
Models the destructive 0x08 status read, the active-low INT line, `BOUTF` high at power-up and a deliberately non-nominal per-instance range ratio; see `digital_twin/README.md`'s "What's here"."""

from _fault_injection import FaultInjector

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    from machine import Timer  # type-only: the runtime import of Timer stays inside _start_timer()

    class _RandomSource(Protocol):
        # Structural stand-in for the `random` module (the default) or a seeded random.Random -
        # machine.py's configure_random_source() seam. Only uniform() is ever called here.
        def uniform(self, a: float, b: float) -> float: ...

    class _IntPin(Protocol):
        # Structural stand-in for machine.py's Pin (and any test's own pin fake) - only the
        # twin-only simulate_edge() is ever called here. machine.py's Pin is a per-id registry
        # singleton, so the Pin(6) handed in here and the Pin(6) the driver constructs are the
        # SAME object - that identity is what lets simulate_edge() reach the driver's own handler,
        # and it is load-bearing, not incidental.
        def simulate_edge(self, new_value: int) -> None: ...

_DEVICE_ID = 0x7D  # datasheet FN8424 Rev 3.00 p9, Table 2
_CMD_RESET = 0x46  # write to 0x00 - "the device will reset all registers to their default states" (p9)

_REG_DEVICE_ID = 0x00
_REG_CONFIG1 = 0x01
_REG_CONFIG2 = 0x02
_REG_CONFIG3 = 0x03
_REG_THRESH_LOW_L = 0x04
_REG_STATUS = 0x08
_REG_DATA = 0x09

_CONFIG1_MODE_MASK = 0x07  # p10, Table 4
_CONFIG1_RNG = 0x08  # p10, Table 5: 0 = 375 lux, 1 = 10000 lux
_CONFIG1_BITS = 0x10  # p10, Table 6: 0 = 16-bit, 1 = 12-bit
_MODES_WITH_CONVERSION = (0x01, 0x02, 0x03, 0x05, 0x06, 0x07)  # p10, Table 4 (0 = power-down, 4 = standby)

# Reserved bits read back ZERO, they do not hold what was written (measured on real silicon
# 2026-09-12: writing 0xFF reads back 3f/bf/1f). p9's own "all RESERVED bits are Intersil used bits
# ONLY" permits either, so this is a measurement, not a datasheet deduction.
_CONFIG_MASKS = (0x3F, 0xBF, 0x1F)  # CONFIG1 B7:6, CONFIG2 B6, CONFIG3 B7:5

_CONFIG3_INTSEL_MASK = 0x03  # p11, Table 11: 00 none, 01 green, 10 red, 11 blue
_CONFIG3_PRST_MASK = 0x0C  # p11, Table 12: 1/2/4/8 integration cycles
_PRST_CYCLES = (1, 2, 4, 8)

_STATUS_RGBTHF = 0x01  # p12, Table 16
_STATUS_CONVENF = 0x02  # p12, Table 17 - set when a conversion completes, cleared by the status read
_STATUS_BOUTF = 0x04  # p12, Table 18 - HIGH at power-up by design
_STATUS_RGBCF_SHIFT = 4  # p12, Table 19
_STATUS_RGBCF_MASK = 0x30
_STATUS_POR = 0x04  # p12, Table 15's own documented default
_LAST_REGISTER = 0x0E  # 0x00-0x0E is the whole map; the pointer stops here rather than rolling over

_FS_LOW_LUX = 375.0  # p10, Table 5 - the low range is the gain reference the ratio is measured against
_FULL_SCALE_COUNTS = 65535.0  # p3, Electrical Specifications: "Full Scale ADC Code, ADC 16 bits"
_CYCLE_MS_16BIT = 303  # 3 x tINT, tINT = 101ms typ at 16 bits (p3)
_CYCLE_MS_12BIT = 19  # 3 x ~6.3ms: p6 makes tINT an n-bit counter on one oscillator, so 101 x 2**-4

_FAULT_INT_STUCK_HIGH = "isl29125:int_stuck_high"


class Isl29125Chip:
    def __init__(
        self,
        random_source: "_RandomSource | None" = None,
        int_pin: "_IntPin | None" = None,
        min_lux: float = 5.0,
        max_lux: float = 9000.0,
        lux_step: float = 400.0,
        gain_ratio: float = 25.9,
        dark_counts: int = 1,
        *,
        auto_refresh: bool = True,
    ) -> None:
        if random_source is None:
            import random as _random_module

            random_source = _random_module
        self._random = random_source
        # min/max are datasheet-derived (p1's feature list: range 0 reaches 375 lux, range 1
        # reaches 10000) - lux_step is NOT: it is a physical-plausibility judgment call bounding
        # how far one reading can move from the last, the same framing _scd30_chip.py's own
        # *_step arguments carry.
        self._min_lux, self._max_lux, self._lux_step = min_lux, max_lux, lux_step
        # Deliberately NOT the nominal 10000/375 = 26.67: the driver's gain-ratio self-calibration
        # only has something real to learn if this unit's own high-range full scale differs from
        # nominal, which on real silicon it always does.
        self._gain_ratio = gain_ratio
        self._dark_counts = dark_counts  # DDark, p3: typ 1 / max 5 counts at range 0, 16 bits
        self._int_pin = int_pin
        if int_pin is not None:
            # The line idles HIGH: it is open-drain pull-down with an external pull-up (p6), and
            # machine.py's Pin comes up at 0. Without this the line starts electrically asserted,
            # so the first real crossing produces no falling EDGE at all and the driver's handler
            # never runs - a silent, whole-mechanism failure with nothing to point at.
            int_pin.simulate_edge(1)
        self.fault = FaultInjector()
        self._config = bytearray(3)  # CONFIG1-3, all 0x00 at power-on (p9-p11, Tables 3/8/10)
        self._threshold_low = 0x0000  # p12, Table 14's own documented defaults
        self._threshold_high = 0xFFFF
        self._status = _STATUS_POR  # BOUTF high - a fresh chip really is in the post-brownout state
        self._data = bytearray(6)
        self._prst_count = 0
        self._int_asserted = False
        self._int_stuck_high = False
        self._timer: Timer | None = None
        # Initial value: one uniform draw within [min,max] at construction - every value after
        # this one steps from the last instead (see _produce_new_reading() below).
        self._lux = self._random.uniform(self._min_lux, self._max_lux)
        self._tint = (1.0, 1.0, 1.0)  # (red, green, blue) weights; neutral until set_illumination says otherwise
        if auto_refresh:
            self._start_timer()

    # -- modelling ---------------------------------------------------------

    def _start_timer(self) -> None:
        from machine import Timer as _Timer

        if self._timer is None:  # reused, never replaced - init() cancels the previous schedule
            self._timer = _Timer()
        self._timer.init(period=self.cycle_ms(), mode=_Timer.PERIODIC, callback=lambda _t: self._produce_new_reading())

    def cycle_ms(self) -> int:
        return _CYCLE_MS_12BIT if self._config[0] & _CONFIG1_BITS else _CYCLE_MS_16BIT

    def resolution_bits(self) -> int:
        return 12 if self._config[0] & _CONFIG1_BITS else 16

    def effective_full_scale(self) -> float:
        # The low range is the reference; the high range's real full scale is the low one times
        # this unit's own ratio, which is what makes the nominal 10000 an approximation to learn.
        if self._config[0] & _CONFIG1_RNG:
            return _FS_LOW_LUX * self._gain_ratio
        return _FS_LOW_LUX

    def set_illumination(self, lux: float, *, tint: "tuple[float, float, float] | None" = None) -> None:
        # The test seam the twin-tier sweep drives. `tint` is a (red, green, blue) weight triple:
        # without it a scalar-lux fake can only ever produce neutral scenes, so the one case the
        # auto-range peak rule exists for - a single clipped channel with green mid-scale - would
        # be unreachable at this tier.
        self._lux = lux
        if tint is not None:
            self._tint = tint
        self._produce_new_reading(walk=False)

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _channel_counts(self) -> "tuple[int, int, int]":
        bits = self.resolution_bits()
        maximum = (1 << bits) - 1
        full_scale = self.effective_full_scale()
        # Clipping is MODELLED, not clamped away: a channel past full scale reads exactly the
        # resolution's own maximum (4095 at 12 bits, 65535 at 16), because the driver tests
        # saturation against that raw maximum and a fake that always saturated at 65535 would
        # make the 12-bit half of that test vacuous.
        dark = self._dark_counts * (maximum / _FULL_SCALE_COUNTS) if full_scale == _FS_LOW_LUX else 0.0
        out = []
        for weight in self._tint:
            raw = self._lux * weight / full_scale * maximum + dark
            out.append(int(max(0, min(maximum, int(raw + 0.5)))))
        return out[0], out[1], out[2]

    def _produce_new_reading(self, *, walk: bool = True) -> None:
        if (self._config[0] & _CONFIG1_MODE_MASK) not in _MODES_WITH_CONVERSION:
            return  # power-down/standby: no conversion, and the data registers keep what they held
        if walk:
            self._lux = self._clamp(self._lux + self._random.uniform(-self._lux_step, self._lux_step), self._min_lux, self._max_lux)
        red, green, blue = self._channel_counts()
        # Register order is GREEN, RED, BLUE (p9, Table 1) - Table 20's own row labels are wrong.
        self._data = bytearray(
            [green & 0xFF, (green >> 8) & 0xFF, red & 0xFF, (red >> 8) & 0xFF, blue & 0xFF, (blue >> 8) & 0xFF],
        )
        # Double buffered, so the write above is atomic from the bus's point of view (p13). RGBCF
        # reports which channel the next conversion is on; rotated so it is never a constant.
        next_channel = ((self._status >> _STATUS_RGBCF_SHIFT) % 3) + 1
        self._status = (self._status & ~_STATUS_RGBCF_MASK) | (next_channel << _STATUS_RGBCF_SHIFT)
        self._status |= _STATUS_CONVENF  # "conversion completed" (p12, Table 17)
        self._update_int(green, red, blue)

    def _update_int(self, green: int, red: int, blue: int) -> None:
        intsel = self._config[2] & _CONFIG3_INTSEL_MASK
        if intsel == 0:  # "No Interrupt" (p11, Table 11) - the fixed-range mode's own disarm
            self._prst_count = 0
            return
        selected = (green, red, blue)[intsel - 1]
        # "below OR EQUAL TO the lower threshold" / above the higher one (p12).
        outside = selected <= self._threshold_low or selected > self._threshold_high
        if not outside:
            self._prst_count = 0
            return
        self._prst_count += 1
        if self._prst_count < _PRST_CYCLES[(self._config[2] & _CONFIG3_PRST_MASK) >> 2]:
            return
        self._status |= _STATUS_RGBTHF
        if self._int_asserted or self._int_pin is None:
            return
        self._int_asserted = True
        if self._int_stuck_high:
            return  # the flag still sets and the data keeps moving - only the line never moves
        self._int_pin.simulate_edge(0)  # active-low, open-drain (p6)

    def _reset(self) -> None:
        self._config = bytearray(3)
        self._threshold_low = 0x0000
        self._threshold_high = 0xFFFF
        self._data = bytearray(6)
        self._prst_count = 0
        self._release_int()
        # Measured on real silicon (2026-09-12): the status register reads 0x00 straight after the
        # 0x46 reset command, with no intervening write - so the reset clears BOUTF too. Table 15's
        # 0x04 is the POWER-ON default (p12 says "during the initial power-up"), which __init__
        # still models; it is not a value the reset command restores.
        self._status = 0x00

    def simulate_brownout(self) -> None:
        # A SUPPLY event, which is NOT the 0x46 reset command: every register drops to its
        # power-on default AND BOUTF comes back up (p12). That flag is the whole signal the
        # driver's recovery path keys on, and _reset() deliberately no longer raises it.
        self._reset()
        self._status = _STATUS_POR

    def _release_int(self) -> None:
        if self._int_asserted and self._int_pin is not None:
            self._int_pin.simulate_edge(1)
        self._int_asserted = False

    def configure_fault(self, op: str, *, active: bool = True) -> None:
        # A persistent behavioural MODE, deliberately not a FaultInjector entry: that shared
        # primitive queues exceptions and hangs, and this is neither - the bus keeps working and
        # the conversions keep happening, only the INT line never moves. That silent failure is
        # exactly the one requirement 17's periodic range evaluation exists to survive, and
        # nothing else in this package can produce it.
        if op != _FAULT_INT_STUCK_HIGH:
            raise ValueError(f"unknown ISL29125 fault mode {op!r} - expected {_FAULT_INT_STUCK_HIGH!r}")
        self._int_stuck_high = active

    # -- bus transaction handlers -----------------------------------------

    def handle_writeto(self, _data: bytes) -> None:
        # I2CDevice.setup()'s zero-byte ACK probe - see _bmp3xx_chip.py's own handle_writeto()
        # comment for the AttributeError every boot hits without this.
        self.fault.maybe_raise("writeto")

    def handle_writeto_mem(self, reg_addr: int, data: bytes) -> None:
        self.fault.maybe_hang("writeto_mem")
        self.fault.maybe_raise("writeto_mem")
        if not data:
            return
        if reg_addr == _REG_DEVICE_ID:
            if data[0] == _CMD_RESET:
                self._reset()
            return
        if _REG_CONFIG1 <= reg_addr <= _REG_CONFIG3:
            # The address pointer auto-increments (p7), so one burst can carry 1-3 config bytes.
            touched_config1 = reg_addr == _REG_CONFIG1
            for offset, value in enumerate(data):
                index = reg_addr - _REG_CONFIG1 + offset
                if index < len(self._config):
                    self._config[index] = value & _CONFIG_MASKS[index]
            if touched_config1:
                if (self._config[0] & _CONFIG1_MODE_MASK) not in _MODES_WITH_CONVERSION:
                    # Power-down/standby stops the conversion engine: real silicon reads 0x00 here,
                    # so both conversion-progress fields go with it (BOUTF, if set, stays).
                    self._status &= ~(_STATUS_CONVENF | _STATUS_RGBCF_MASK)
                # "ADC start at I2C write 0x01" with SYNC = 0 (p10, Table 7): the conversion
                # restarts, so the data registers keep the PREVIOUS cycle's values - taken on the
                # old gain - until a new cycle completes. That stale window is exactly what the
                # driver's settle wait exists to discard, so it must be modelled, not smoothed away.
                self._prst_count = 0
                if self._timer is not None:
                    self._start_timer()  # re-arm at the (possibly new) resolution's cycle time
            return
        if _REG_THRESH_LOW_L <= reg_addr <= 0x07:
            values = bytearray([self._threshold_low & 0xFF, self._threshold_low >> 8, self._threshold_high & 0xFF, self._threshold_high >> 8])
            for offset, value in enumerate(data):
                index = reg_addr - _REG_THRESH_LOW_L + offset
                if index < len(values):
                    values[index] = value
            self._threshold_low = values[0] | (values[1] << 8)
            self._threshold_high = values[2] | (values[3] << 8)
            self._prst_count = 0
            return
        if reg_addr == _REG_STATUS:
            # Table 15 marks 0x08 "RO", but p12's own BOUTF text requires an I2C write to clear
            # it - the marking is a datasheet defect, not a prohibition.
            if not data[0] & _STATUS_BOUTF:
                self._status &= ~_STATUS_BOUTF
            return
        # any other register: real hardware silently accepts and ignores it too.

    def _register_image(self) -> bytes:
        # The whole 0x00-0x0E map as one flat block. Reads are served out of this rather than
        # per-register-block, because the address pointer really does walk straight across the
        # block boundaries - measured on real silicon (2026-09-12): a 16-byte read from 0x00
        # returns id, CONFIG1-3, both thresholds, status and all six data bytes in one go.
        return (
            bytes((_DEVICE_ID, self._config[0], self._config[1], self._config[2]))
            + bytes((self._threshold_low & 0xFF, self._threshold_low >> 8, self._threshold_high & 0xFF, self._threshold_high >> 8))
            + bytes((self._status,))
            + bytes(self._data)
        )

    def handle_readfrom_mem(self, reg_addr: int, nbytes: int) -> bytes:
        self.fault.maybe_hang("readfrom_mem")
        self.fault.maybe_raise("readfrom_mem")
        image = self._register_image()
        reply = image[reg_addr : reg_addr + nbytes] if reg_addr <= _LAST_REGISTER else b""
        # Past 0x0E the pointer stops and the part keeps clocking out zeros - it does NOT roll
        # over to 0x00, despite p6's burst-WRITE text saying the write counter does (measured:
        # an 8-byte read from 0x0D gives the two data bytes then six zeros).
        reply = (reply + bytes(nbytes))[:nbytes]
        if reg_addr <= _REG_STATUS < reg_addr + nbytes and reg_addr <= _LAST_REGISTER:
            # Destructive by design (p11/p12): transferring the status byte is what clears RGBTHF,
            # CONVENF and BOUTF and releases the INT pin, so nothing else in the driver may read
            # this register "just to check". BOUTF being read-to-clear CONTRADICTS p12, which says
            # it "should be reset to LOW by an I2C write command" - measured 2026-09-13 on a
            # genuinely just-powered board: 0x08 read 0x04, and a second read 0x00 with only that
            # read in between. The RGBCF field is the one that survives a read. Whether a burst that merely SPANS 0x08
            # also clears them could not be measured (the threshold re-armed faster than the probe
            # could re-check) - clearing is the reading p12's "the 8-bit transfer" wording supports,
            # and the driver only ever reads 0x08 on its own, so nothing depends on the choice.
            self._status &= ~(_STATUS_RGBTHF | _STATUS_CONVENF | _STATUS_BOUTF)
            self._prst_count = 0
            self._release_int()
        return reply
