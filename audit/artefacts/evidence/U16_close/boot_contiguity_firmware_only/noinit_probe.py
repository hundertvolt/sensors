# diag: no-retention logs, and the SPI fake's init() allocating nothing
import sys
import machine
def _noop(self, entry):
    self.dropped += 1
machine._CallLog.append = _noop
machine._WireLog.append = _noop
def _init(self, baudrate=-1, *, polarity=-1, phase=-1, bits=-1, firstbit=-1):
    pass
machine.SPI.init = _init
exec(open("tests/_boot_contiguity_probe.py").read())
