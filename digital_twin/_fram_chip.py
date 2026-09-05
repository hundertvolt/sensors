"""Digital-twin chip fake for the MB85RS64V FRAM chip (SPI) — answers `asy_fram_driver.py`'s exact opcode/CS-session shape (RDID/RDSR/WRSR/WREN/WRDI/READ/WRITE); independently reimplemented, not shared with `tests/_fram_chip_fake.py`.
Persists only via explicit `save_state()`; see `digital_twin/README.md`'s "FRAM persistence" section.
`rdid_response` defaults to the real MB85RS64V's own device ID (wozi's chip) - `machine.py`'s
`_wire_spi_device()` overrides both `size` and this for the `dev` wiring profile, whose real chip
is a different, larger part (MB85RS2MTA) with its own distinct product ID. REAL FINDING, fixed
2026-09-04: before this parameter existed, `_wire_spi_device()` always constructed a fixed-identity
chip regardless of profile, so `dev`'s own FRAM_SPI.setup() silently failed
`_check_device_id()`'s product-ID check on every twin run - caught and swallowed by
`AsyFramManager.setup()`'s own broad `except Exception`, leaving FRAM silently uninitialized the
entire time with nothing ever checking `.initialized`/`.verify_present()` closely enough to notice."""

from _fault_injection import FaultInjector

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    pass

_OPCODE_WREN = 0x06
_OPCODE_WRDI = 0x04
_OPCODE_RDSR = 0x05
_OPCODE_WRSR = 0x01
_OPCODE_READ = 0x03
_OPCODE_WRITE = 0x02
_OPCODE_RDID = 0x9F

_WEL_BIT = 0x02
_DEFAULT_RDID = bytes([0x04, 0x7F, 0x03, 0x02])  # real MB85RS64V device ID (datasheets/fram/)

_SAVE_CHUNK_SIZE = 512  # bytes per chunk when streaming the memory image out to disk in save_state()
# below - avoids ever allocating one contiguous string for the whole buffer. Found by actually
# running the real assembled system against this twin for the first time during baseline
# verification: json.dump({"memory_hex": bytes(self.memory).hex()}) needs one
# contiguous ~2*size-byte allocation (16385 bytes for the real 0x2000-byte FRAM) - reproduced as a
# deterministic MemoryError after a few seconds of the real task supervisor running (real asyncio
# tasks/timers/HTTP handling churn the heap enough to fragment it) even with ~1.5MB of *total*
# gc.mem_free() still available, and an extra gc.collect() right before the call doesn't help
# (MicroPython's GC coalesces freed blocks but never relocates live ones, so this fragmentation
# isn't reclaimable). Chunked writes only ever need one small chunk contiguous at a time.

_LOAD_CHUNK_CHARS = 1024  # hex characters per chunk when streaming the memory image back in from
# disk in _load_state() below - the read-side mirror of _SAVE_CHUNK_SIZE above, same reasoning.


class FramChip:
    def __init__(self, size: int = 0x2000, state_path: "str | None" = None, rdid_response: "bytes | None" = None) -> None:
        self.size = size
        self.state_path = state_path
        self.status = 0x00
        self.rdid_response = _DEFAULT_RDID if rdid_response is None else rdid_response
        self.fault = FaultInjector()
        self.memory = bytearray(size)
        self._pending_op: int | None = None
        self._pending_addr: int | None = None
        self._load_state()

    @property
    def _wel(self) -> bool:
        return bool(self.status & _WEL_BIT)

    def _decode_addr(self, data: bytes) -> int:
        return (data[1] << 8) | data[2]

    def _load_state(self) -> None:
        if self.state_path is None:
            return
        try:
            f = open(self.state_path)
        except OSError:
            return  # no persisted state yet - start from a blank chip, matches a factory-fresh part
        try:
            # Hand-parsed, not json.load() - the read-side mirror of save_state()'s own fix
            # (_SAVE_CHUNK_SIZE's comment): json.load() would materialize the whole memory_hex
            # value as one contiguous string (16385 bytes for the real 0x2000-byte FRAM), the same
            # fragmentation risk class as the fixed save_state() bug, just on the read path -
            # lower-probability in practice (this only ever runs once, at construction, before any
            # live churn has fragmented the heap) but the same latent shape, found by this session's
            # own follow-up audit of the fixed bug's pattern rather than a reproduced failure.
            header = f.read(128)  # the '{"size": N, "memory_hex": "' prefix is always well under this
            marker = '"memory_hex": "'
            idx = header.find(marker)
            if idx == -1:
                return  # malformed/unrecognized file - leave self.memory at its blank default
            pending = header[idx + len(marker) :]
            pos = 0
            while pos < self.size:
                chunk = f.read(_LOAD_CHUNK_CHARS)
                piece = pending + chunk
                pending = ""
                if not piece:
                    break
                end = piece.find('"')
                done = end != -1
                if done:
                    piece = piece[:end]
                if len(piece) % 2:  # a hex byte pair straddled this chunk boundary - hold the
                    pending = piece[-1:]  # trailing nibble for the next round instead of mis-pairing
                    piece = piece[:-1]
                if piece:
                    n = min(len(piece) // 2, self.size - pos)
                    self.memory[pos : pos + n] = bytearray.fromhex(piece[: n * 2])
                    pos += n
                if done or not chunk:
                    break
        finally:
            f.close()

    def save_state(self) -> None:
        if self.state_path is None:
            return
        # Streamed by hand (not json.dump()) - see _SAVE_CHUNK_SIZE's own comment above for why a
        # single-shot bytes(self.memory).hex() is a real fragmentation risk. The written file is
        # still exactly the JSON object _load_state() expects (hex digits never need escaping).
        with open(self.state_path, "w") as f:
            f.write(f'{{"size": {self.size}, "memory_hex": "')
            for start in range(0, self.size, _SAVE_CHUNK_SIZE):
                f.write(self.memory[start : start + _SAVE_CHUNK_SIZE].hex())
            f.write('"}')

    def write(self, buf: bytes) -> None:
        self.fault.maybe_hang("write")
        self.fault.maybe_raise("write")
        data = bytes(buf)
        if self._pending_op == _OPCODE_WRITE and self._pending_addr is not None:
            # data phase of a previously-opened WRITE (opcode+address arrived in the prior call)
            if self._wel:
                end = self._pending_addr + len(data)
                self.memory[self._pending_addr : end] = data
            self.status &= ~_WEL_BIT  # WEL auto-clears at the CS rising edge after WRITE recognition
            self._pending_op = None
            self._pending_addr = None
            return
        opcode = data[0]
        if opcode == _OPCODE_WREN:
            self.status |= _WEL_BIT
        elif opcode == _OPCODE_WRDI:
            self.status &= ~_WEL_BIT
        elif opcode == _OPCODE_WRSR:
            if self._wel:
                self.status = (data[1] & ~_WEL_BIT) | (self.status & _WEL_BIT)
            self.status &= ~_WEL_BIT  # WEL auto-clears at the CS rising edge after WRSR recognition
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

    def readinto(self, buf: bytearray, write_value: int = 0x00) -> None:
        self.fault.maybe_hang("readinto")
        self.fault.maybe_raise("readinto")
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
