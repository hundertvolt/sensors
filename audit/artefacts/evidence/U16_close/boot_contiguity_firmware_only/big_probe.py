import sys, uctypes
exec(open(sys.argv[0].rsplit("/",1)[0] + "/attr_probe.py").read().split("src = open")[0].replace("_AT = sys.argv.pop(5)", "_AT = 'x'"))
_LA = {"alloc": uctypes.UINT64 | 8, "items": uctypes.UINT64 | 24}
def _attr_hook(label):
    if label != "after_batch":
        return
    for log in _REG:
        st = log._items if hasattr(log, "_items") else None
        if isinstance(st, list) and len(st) > 100:
            s = uctypes.struct(id(st), _LA)
            print("BIG", label, len(st), s.alloc, "%x" % s.items)
src = open("tests/_boot_contiguity_probe.py").read()
src = src.replace('    print(f"=== ENDMAP {label} ===")\n', '    print(f"=== ENDMAP {label} ===")\n    _attr_hook(label)\n', 1)
exec(src)
