import gc, sys
class P:
    def __init__(self, level): self.level = level
    def early(self, _l, ctx):
        try:
            try:
                if self.level >= 1:
                    print("X", ctx["message"])
            finally:
                ctx["exception"] = None
        except Exception:
            pass
    def empty(self): pass
def nothing(): pass
for label, call in (("method_level0", lambda p, c: p.early(None, c)), ("method_level1", lambda p, c: p.early(None, c))):
    pass
for lvl in (0, 1):
    p = P(lvl)
    for i in range(3):
        c = {"message": "m", "exception": None}
        gc.collect(); b = gc.mem_alloc(); p.early(None, c); a = gc.mem_alloc()
        print("RESULT method level", lvl, i, a - b)
for i in range(3):
    gc.collect(); b = gc.mem_alloc(); nothing(); a = gc.mem_alloc(); print("RESULT direct_empty_call", i, a - b)
p = P(0)
for i in range(3):
    gc.collect(); b = gc.mem_alloc(); p.empty(); a = gc.mem_alloc(); print("RESULT method_empty", i, a - b)
