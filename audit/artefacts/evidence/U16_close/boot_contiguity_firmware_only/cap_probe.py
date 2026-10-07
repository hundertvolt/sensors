# diag: the boot probe with the SPI fake's call log capped at 64 entries, like the fakes' Pin value logs
import sys
import machine
_si = machine.SPI.__init__
def _init(self, *a, **k):
    _si(self, *a, **k)
    self.log = machine._CallLog(64)
machine.SPI.__init__ = _init
exec(open("tests/_boot_contiguity_probe.py").read())
