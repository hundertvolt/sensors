# diag: run the boot probe with the fakes' call/wire logs storing nothing (MODE env-like argv[5])
import sys
import machine
mode = sys.argv.pop(5) if len(sys.argv) > 5 else "nolog"
if mode == "nolog":
    def _noop(self, entry):
        self._n = min(self._n + 1, self.maxlen)
    machine._CallLog.append = _noop
    machine._WireLog.append = _noop
exec(open("tests/_boot_contiguity_probe.py").read())
