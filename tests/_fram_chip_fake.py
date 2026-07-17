"""Stateful fake for the MB85RS64V FRAM chip itself, sitting on top of tests/machine.py's fake
`machine.SPI` (which only models the raw, dumb bus - no opcode/CS-session semantics at all, by
design per tests/README.md's mocking-boundary). A fourth instance of that same boundary: this
interprets the byte streams asy_fram_driver.py's FRAM_SPI actually sends (RDID/RDSR/WRSR/WREN/
WRDI/READ/WRITE) the way a real chip would, so FRAM_SPI's own logic (device-ID check, write-enable
-latch handling, write-protect readback, address decoding) runs for real against it.

Transaction tracking is deliberately narrow, not a general SPI-FRAM emulator: it only recognizes
the exact call shapes FRAM_SPI itself produces (a WRITE's address header and data payload arrive
as two separate write() calls with the bus lock held throughout, matching real CS staying
asserted across both; every other opcode is a single write(), optionally followed by one
readinto()). WEL semantics match the datasheet exactly (DS501-00015-4v0-E, "STATUS REGISTER" ->
WEL): WREN sets it; it's reset after WRDI recognition, at the CS rising edge after WRSR
recognition, and at the CS rising edge after WRITE recognition (confirmed directly against the
real datasheet PDF, not inferred from a similar part).

Fault-injection knobs (`drop_wren`/`drop_next_wrdi`/`drop_wrsr`/`disturb_write_autoclear`/
`disturb_wrsr_autoclear`/`rdid_response`) simulate a bus disturbance eating one specific
transaction's real effect while every other byte still moves normally - not "unplug the whole
bus" (tests/machine.py's own
test_disconnected_wire_is_undetectable_reads_whatever_is_on_the_bus_not_an_exception already
covers that undetectable case at the raw-SPI layer). `disturb_write_autoclear`/
`disturb_wrsr_autoclear` suppress the datasheet's own auto-clear specifically so
FRAM_SPI's explicit WRDI-verification/retry path (defense-in-depth against that exact
auto-clear mechanism itself glitching) stays exercised by a real simulated fault instead of
being permanently unreachable now that the normal case already clears WEL before WRDI even runs.
"""

from machine import SPI as FakeSPI

_OPCODE_WREN = 0x06
_OPCODE_WRDI = 0x04
_OPCODE_RDSR = 0x05
_OPCODE_WRSR = 0x01
_OPCODE_READ = 0x03
_OPCODE_WRITE = 0x02
_OPCODE_RDID = 0x9F


class FakeMB85RS64V(FakeSPI):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.memory = bytearray(0x2000)
        self.status = 0x00  # WEL clear, no write protection
        self.rdid_response = bytes([0x04, 0x7F, 0x03, 0x02])  # correct MB85RS64V ID by default
        self.drop_wren = False  # simulate WREN's opcode transfer getting corrupted on the wire
        self.drop_next_wrdi = 0  # simulate N consecutive WRDI transfers getting corrupted
        self.drop_wrsr = False  # simulate WRSR's status-byte transfer getting corrupted
        self.disturb_write_autoclear = False  # simulate the chip's own WRITE-completion WEL auto-clear not firing
        self.disturb_wrsr_autoclear = False  # simulate the chip's own WRSR-completion WEL auto-clear not firing
        self._pending_op: int | None = None
        self._pending_addr: int | None = None

    @property
    def wel(self) -> bool:
        return bool(self.status & 0x02)

    def _decode_addr(self, data: bytes) -> int:
        return (data[1] << 8) | data[2]  # 2-byte address form, matches this driver's <=0xFFFF path

    def write(self, buf: object) -> None:
        data = bytes(buf)  # type: ignore[call-overload]
        if self._pending_op == _OPCODE_WRITE and self._pending_addr is not None:
            # data phase of a previously-opened WRITE (opcode+address arrived in the prior call)
            if self.wel:
                end = self._pending_addr + len(data)
                self.memory[self._pending_addr : end] = data
            if not self.disturb_write_autoclear:
                self.status &= ~0x02  # WEL auto-clears at the CS rising edge after WRITE recognition
            self._pending_op = None
            self._pending_addr = None
            return
        opcode = data[0]
        if opcode == _OPCODE_WREN:
            if not self.drop_wren:
                self.status |= 0x02
        elif opcode == _OPCODE_WRDI:
            if self.drop_next_wrdi > 0:
                self.drop_next_wrdi -= 1
            else:
                self.status &= ~0x02
        elif opcode == _OPCODE_WRSR:
            # Requires WEL set first, exactly like WRITE (datasheet: WEL "indicates if FRAM
            # array and status register are writable"); WRSR can't write bit 1 (WEL) itself, so
            # the current WEL bit is preserved through this assignment regardless.
            if self.wel and not self.drop_wrsr:
                self.status = (data[1] & ~0x02) | (self.status & 0x02)
            if not self.disturb_wrsr_autoclear:
                self.status &= ~0x02  # WEL auto-clears at the CS rising edge after WRSR recognition
        elif opcode == _OPCODE_WRITE:
            self._pending_op = _OPCODE_WRITE
            self._pending_addr = self._decode_addr(data)
        elif opcode == _OPCODE_READ:
            self._pending_op = _OPCODE_READ
            self._pending_addr = self._decode_addr(data)
        elif opcode == _OPCODE_RDSR:
            self._pending_op = _OPCODE_RDSR
        elif opcode == _OPCODE_RDID:
            self._pending_op = _OPCODE_RDID

    def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        if self._pending_op == _OPCODE_READ and self._pending_addr is not None:
            n = len(buf)
            buf[:] = self.memory[self._pending_addr : self._pending_addr + n]
        elif self._pending_op == _OPCODE_RDSR:
            buf[:] = bytes([self.status])
        elif self._pending_op == _OPCODE_RDID:
            buf[:] = self.rdid_response[: len(buf)]
        else:
            buf[:] = bytes(len(buf))
        self._pending_op = None
        self._pending_addr = None
