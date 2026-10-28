import sys
import machine
_REG = []
_ci, _wi = machine._CallLog.__init__, machine._WireLog.__init__
def _cinit(self, *a):
    _ci(self, *a); _REG.append(("C", a))
def _winit(self, *a):
    _wi(self, *a); _REG.append(("W", a))
machine._CallLog.__init__ = _cinit
machine._WireLog.__init__ = _winit
def _hook(label):
    print("REG", label, len(_REG), _REG[-3:], sorted(machine.Pin._value_logs))
src = open("tests/_boot_contiguity_probe.py").read()
src = src.replace('    print(f"=== ENDMAP {label} ===")\n', '    print(f"=== ENDMAP {label} ===")\n    _hook(label)\n', 1)
exec(src)
