# diag: the boot probe, plus FAKE lines naming every heap block owned by the fakes' logs at each map
import sys
import uctypes
import machine
_AT = sys.argv.pop(5)
_REG = []
_ci, _wi = machine._CallLog.__init__, machine._WireLog.__init__
def _cinit(self, *a):
    _ci(self, *a)
    _REG.append(self)
def _winit(self, *a):
    _wi(self, *a)
    _REG.append(self)
machine._CallLog.__init__ = _cinit
machine._WireLog.__init__ = _winit
_L = {"items": uctypes.UINT64 | 24}
_S = {"data": uctypes.UINT64 | 24}
def _walk(obj, out, depth=0):
    t = type(obj)
    if t is list:
        out.append(id(obj)); out.append(uctypes.struct(id(obj), _L).items)
        for e in obj:
            _walk(e, out, depth + 1)
    elif t is tuple:
        if len(obj):
            out.append(id(obj))
        for e in obj:
            _walk(e, out, depth + 1)
    elif t is str:
        pass
    elif t is bytes:
        if len(obj) > 0:
            out.append(id(obj)); out.append(uctypes.struct(id(obj), _S).data)
    elif t is bytearray:
        out.append(id(obj)); out.append(uctypes.addressof(obj))
    elif t is dict:
        out.append(id(obj))
        for k, v in obj.items():
            _walk(k, out, depth + 1); _walk(v, out, depth + 1)
    elif t in (int, bool, float) or obj is None:
        pass
    else:
        out.append(("OTHER", repr(t)))
def _attr_hook(label):
    if label != _AT:
        return
    out = []
    for log in _REG:
        out.append(id(log))
        _walk(log._chunks if hasattr(log, "_chunks") else log._items, out)
    print("FAKEREG", label, len(_REG))
    for a in out:
        if isinstance(a, tuple):
            print("FAKEOTHER", label, a[1])
        else:
            print("FAKE", label, "%x" % a)
src = open("tests/_boot_contiguity_probe.py").read()
src = src.replace('    print(f"=== ENDMAP {label} ===")\n', '    print(f"=== ENDMAP {label} ===")\n    _attr_hook(label)\n', 1)
exec(src)
