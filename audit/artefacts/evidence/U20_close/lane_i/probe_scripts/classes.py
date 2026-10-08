import sys
sys.path.insert(0, "ext")
from _sensortask_scenarios import build, register_for_device
for d in ("dev", "wozi"):
    register_for_device(d); m = build(d)
    objs = {n: getattr(m, n) for n in dir(m) if not n.startswith("_") and hasattr(getattr(m, n), "get_loggers") and not isinstance(getattr(m, n), type)}
    classes = []
    for n, o in sorted(objs.items()):
        if type(o) not in classes:
            classes.append(type(o))
    print(d, sorted(objs), [c.__name__ for c in classes])
    for a in classes:
        for b in classes:
            if a is not b and issubclass(a, b):
                print("SUB", a.__name__, b.__name__)
    print("setup owners", [c.__name__ for c in classes if "setup" in c.__dict__], "init owners", [c.__name__ for c in classes if "__init__" in c.__dict__])
