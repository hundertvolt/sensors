import sys
exec(open(sys.argv[0].rsplit("/",1)[0] + "/attr_probe.py").read().split("src = open")[0].replace("_AT = sys.argv.pop(5)", "_AT = 'x'"))
def _attr_hook(label):
    if label not in ("batch_00", "after_batch"):
        return
    for log in _REG:
        n = log._n if hasattr(log, "_n") else len(log._items)
        if n:
            print("LOG", label, type(log).__name__, n, log.maxlen, repr(log[0])[:60])
            if n > 100:
                h = {}
                for e in log:
                    k = (e[0], len(e[1]) if len(e) > 1 and isinstance(e[1], bytes) else None)
                    h[k] = h.get(k, 0) + 1
                print("HIST", sorted(h.items(), key=lambda kv: -kv[1])[:12])
src = open("tests/_boot_contiguity_probe.py").read()
src = src.replace('    print(f"=== ENDMAP {label} ===")\n', '    print(f"=== ENDMAP {label} ===")\n    _attr_hook(label)\n', 1)
exec(src)
