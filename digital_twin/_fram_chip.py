"""Digital-twin chip fake for the MB85RS64V FRAM chip (SPI, CS on GPIO 1 in src/sensortask_wozi.py's
real wozi wiring) - answers the exact opcode/CS-session shape src/asy_fram_driver.py's FRAM_SPI
sends (RDID/RDSR/WRSR/WREN/WRDI/READ/WRITE), independently reimplementing the same protocol
tests/_fram_chip_fake.py already establishes for unit tests against tests/machine.py (confirmed
directly against src/asy_fram_driver.py, not copied from that file - FINAL_WIRING_PLAN.md's Step 3
never imports tests/machine.py or its fixtures). Deliberately a smaller fault-injection surface than
that fixture's own fine-grained WEL-corruption knobs (drop_wren, disturb_write_autoclear, ...) -
those exist there to defense-in-depth-test FRAM_SPI's own retry logic, already covered by
tests/test_asy_fram_driver.py; this twin only needs the same generic op-keyed FaultInjector every
other chip fake in this package uses.

Persistence (owner decision, FINAL_WIRING_PLAN.md's Step 3 clarifying-question round): the twin
must read back exactly what was written, including across process restarts, but must not write to
disk on every single WRITE opcode (SSD-hosted, avoid unnecessary write cycles). Resolution: an
explicit save_state() call (never automatic) serializes the full memory image to `state_path` as
JSON (hex-encoded bytes, matching every other persisted-state file in this codebase's json
convention - see ConfigManager). Whatever entry point Step 5 writes to run the assembled prototype
is expected to call save_state() once, in a try/finally around asyncio.run(main()), on the way out.
"""

import json

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
# running the real assembled system against this twin for the first time (FINAL_WIRING_PLAN.md's
# Step 5 baseline-verification pass): json.dump({"memory_hex": bytes(self.memory).hex()}) needs one
# contiguous ~2*size-byte allocation (16385 bytes for the real 0x2000-byte FRAM) - reproduced as a
# deterministic MemoryError after a few seconds of the real task supervisor running (real asyncio
# tasks/timers/HTTP handling churn the heap enough to fragment it) even with ~1.5MB of *total*
# gc.mem_free() still available, and an extra gc.collect() right before the call doesn't help
# (MicroPython's GC coalesces freed blocks but never relocates live ones, so this fragmentation
# isn't reclaimable). Chunked writes only ever need one small chunk contiguous at a time.


class FramChip:
    def __init__(self, size: int = 0x2000, state_path: "str | None" = None) -> None:
        self.size = size
        self.state_path = state_path
        self.status = 0x00
        self.rdid_response = _DEFAULT_RDID
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
            with open(self.state_path) as f:
                saved = json.load(f)
        except OSError:
            return  # no persisted state yet - start from a blank chip, matches a factory-fresh part
        memory_hex = saved.get("memory_hex", "")
        loaded = bytearray.fromhex(memory_hex) if memory_hex else bytearray()
        n = min(len(loaded), self.size)
        self.memory[:n] = loaded[:n]

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
