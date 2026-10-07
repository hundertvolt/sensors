"""Digital-twin fake `rp2` module: the DMA channel surface of ports/rp2/rp2_dma.c (v1.29.0) a UART receive ring uses.
A paced channel takes the bytes digital_twin/machine.py's UART receives as their wire time elapses, never per event-loop
turn; independent of tests/rp2.py (held to the same checks, tests/_uart_link_contract.py)."""

import machine
import uctypes

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from array import array
    from typing import ClassVar

    _Buffer = bytearray | memoryview | array[int]

_EBUSY = 16  # MP_EBUSY (py/mperrno.h); the errno module carries no EBUSY name (py/moderrno.c)
_NUM_CHANNELS = 12  # RP2040 datasheet 2.5: twelve channels; DMA() claims the lowest free one (rp2_dma.c:357-366)
_CLOSED = 0xFF
_CHANNEL_BASE = 0x50000000  # DMA channel n's registers at + 0x40 * n (datasheet 2.5.7)
_AL1_TRANS_COUNT_TRIG = 0x1C
_TREQ_PERMANENT = 0x3F  # unpaced
# rp2_dma.c's DEFAULT_DMA_CONFIG: quiet, unpaced, both addresses incrementing, word transfers, enabled.
_DEFAULT_CTRL = (1 << 21) | (_TREQ_PERMANENT << 15) | (1 << 5) | (1 << 4) | (2 << 2) | 1
# (name, lsb, width, read-only): the RP2040 CTRL_TRIG fields pack_ctrl() takes (rp2_dma.c:271-293, hardware/regs/dma.h).
_FIELDS = (
    ("enable", 0, 1, False),
    ("high_pri", 1, 1, False),
    ("size", 2, 2, False),
    ("inc_read", 4, 1, False),
    ("inc_write", 5, 1, False),
    ("ring_size", 6, 4, False),
    ("ring_sel", 10, 1, False),
    ("chain_to", 11, 4, False),
    ("treq_sel", 15, 6, False),
    ("irq_quiet", 21, 1, False),
    ("bswap", 22, 1, False),
    ("sniff_en", 23, 1, False),
    ("busy", 24, 1, True),
    ("write_err", 29, 1, False),
    ("read_err", 30, 1, False),
    ("ahb_err", 31, 1, True),
)


def _field(ctrl: int, name: str) -> int:
    for field, lsb, width, _read_only in _FIELDS:
        if field == name:
            return (ctrl >> lsb) & ((1 << width) - 1)
    raise KeyError(name)


class DMA:
    # One claimed channel. A paced channel whose read address is a UART data register moves that UART's
    # received bytes into its write buffer, wrapping on a write-address ring, as the UART fake hands them
    # over; a channel chained to writes its count register and re-triggers it, as on silicon (datasheet 2.5.2).
    _registry: "ClassVar[dict[int, DMA]]" = machine._DMA_CHANNELS

    def __init__(self) -> None:
        free = [n for n in range(_NUM_CHANNELS) if n not in DMA._registry]
        if not free:
            raise OSError(_EBUSY)
        self.channel = free[0]
        DMA._registry[self.channel] = self
        self._read: int | _Buffer = 0
        self._write: int | _Buffer = 0
        self._reload = 0  # TRANS_COUNT as written: copied into the live count at each trigger (datasheet 2.5.7)
        self._count = 0
        self._ctrl = 0
        self._busy = False
        self._offset = 0  # bytes written since the write address was set, before the ring wrap

    def __del__(self) -> None:
        # rp2.DMA's finaliser is close() (rp2_dma.c:673): a soft reset aborts and frees every channel. A
        # soft reset of the twin is a process exit, so this is modelled for fidelity, called by tests only.
        self.close()

    def _accept(self, address: int, dreq: int) -> bool:
        # Called by the UART fake: does this channel drain the data register at `address`, paced by `dreq`?
        return self._busy and self._read == address and _field(self._ctrl, "treq_sel") == dreq

    def _check_open(self) -> None:
        if self.channel == _CLOSED:
            raise ValueError("channel closed")

    def _check_ring(self) -> None:
        # Silicon wraps the address bits, so a window not aligned to its size writes outside it (datasheet
        # 2.5.1.3); the fake refuses such a ring instead, as a driver bug a test should see at once.
        ring_size = _field(self._ctrl, "ring_size")
        if not ring_size or not _field(self._ctrl, "ring_sel") or isinstance(self._write, int):
            return
        size = 1 << ring_size
        if uctypes.addressof(self._write) % size or len(self._write) < size:
            raise ValueError("DMA write ring not naturally aligned to its size")

    def _complete_one(self) -> None:
        self._count -= 1
        if self._count == 0:
            self._busy = False
            chain_to = _field(self._ctrl, "chain_to")
            if chain_to != self.channel and chain_to in DMA._registry:
                DMA._registry[chain_to]._trigger()

    def _push(self, byte: int) -> None:
        # One paced byte-wide transfer into the write buffer, wrapping on a write ring.
        if _field(self._ctrl, "size") != 0:
            raise NotImplementedError("only byte transfers from a UART are modelled")
        if isinstance(self._write, int):
            raise NotImplementedError("a paced write to a register address is not modelled")
        index = self._offset
        ring_size = _field(self._ctrl, "ring_size")
        if ring_size and _field(self._ctrl, "ring_sel"):
            index &= (1 << ring_size) - 1
        self._write[index] = byte
        if _field(self._ctrl, "inc_write"):
            self._offset += 1
        self._complete_one()

    def _run_unpaced(self) -> None:
        # An unpaced channel completes at once. Modelled only as a reload channel: word reads from a
        # buffer into another channel's AL1_TRANS_COUNT_TRIG, the one write such a ring needs.
        index = 0
        source = self._read
        if isinstance(source, int):
            raise NotImplementedError("an unpaced read from a register address is not modelled")
        while self._busy:
            value = source[index]
            target = self._write - _AL1_TRANS_COUNT_TRIG - _CHANNEL_BASE if isinstance(self._write, int) else -1
            chained = DMA._registry.get(target // 0x40) if target >= 0 and target % 0x40 == 0 else None
            if chained is None:
                raise NotImplementedError("an unpaced transfer other than a count reload is not modelled")
            chained._reload = value
            chained._trigger()
            if _field(self._ctrl, "inc_read"):
                index += 1
            self._complete_one()

    def _source(self) -> "machine.UART | None":
        # The UART fake whose data register this channel reads, or None.
        return machine.UART._for_data_register(self._read) if isinstance(self._read, int) else None

    def _trigger(self) -> None:
        # The live count reloads; the write address carries on from where the last run left it.
        self._count = self._reload
        self._busy = self._count > 0 and _field(self._ctrl, "enable") == 1
        if self._busy and _field(self._ctrl, "treq_sel") == _TREQ_PERMANENT:
            self._run_unpaced()

    def active(self, value: object = None) -> bool:
        self._check_open()
        if value is not None:
            if value:
                self._trigger()
            else:
                self._busy = False
        return self._busy

    def advance(self, data: "bytes | bytearray") -> None:
        # Twin-only test knob: moves `data` into the write buffer as paced transfers would, for a test that
        # needs a given fill or a count near zero without driving the UART.
        self._check_open()
        for byte in data:
            if not self._busy:
                break
            self._push(byte)

    def close(self) -> None:
        if self.channel == _CLOSED:
            return
        self._busy = False
        self._ctrl = 0
        DMA._registry.pop(self.channel, None)
        self.channel = _CLOSED

    def config(self, *, read: "int | _Buffer | None" = None, write: "int | _Buffer | None" = None, count: "int | None" = None, ctrl: "int | None" = None, trigger: bool = False) -> None:
        self._check_open()
        if read is not None:
            self._read = read
        if write is not None:
            self._write = write
            self._offset = 0
        if count is not None:
            self._reload = count
        if ctrl is not None:
            self._ctrl = ctrl
        self._check_ring()
        if trigger:
            self._trigger()

    @property
    def count(self) -> int:
        self._check_open()
        source = self._source()
        if source is not None:
            source._update()
        return self._count

    @count.setter
    def count(self, value: int) -> None:
        self._check_open()
        self._reload = value

    @property
    def ctrl(self) -> int:
        self._check_open()
        return self._ctrl | (0x01000000 if self._busy else 0)

    def pack_ctrl(self, **fields: int) -> int:
        value = fields.pop("default", _DEFAULT_CTRL | ((self.channel & 0xF) << 11))
        for name, lsb, width, read_only in _FIELDS:
            if name not in fields:
                continue
            given = int(fields.pop(name))
            if read_only:
                continue
            mask = (1 << width) - 1
            if given & mask != given:
                raise ValueError("bad field value")
            value = (value & ~(mask << lsb)) | (given << lsb)
        if fields:
            raise TypeError
        return value

    @property
    def read(self) -> int:
        self._check_open()
        return self._read if isinstance(self._read, int) else uctypes.addressof(self._read)

    @classmethod
    def reset_registry(cls) -> None:
        # Twin-only test knob: a soft reset - every channel's finaliser runs (rp2_dma.c:637-673), all twelve are free.
        for channel in list(cls._registry.values()):
            channel.close()

    @staticmethod
    def unpack_ctrl(value: int) -> "dict[str, int]":
        return {name: (value >> lsb) & ((1 << width) - 1) for name, lsb, width, _read_only in _FIELDS}

    @property
    def write(self) -> int:
        # RP2040-E12: WRITE_ADDR reads wrong during ring transfers, so the fake answers the configured
        # start, never the live address - a driver deriving progress from it fails a test.
        self._check_open()
        return self._write if isinstance(self._write, int) else uctypes.addressof(self._write)
