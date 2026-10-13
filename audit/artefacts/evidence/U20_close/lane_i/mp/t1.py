class B:
    def __init__(self, x):
        self.x = x
class C(B):
    pass
class D(B):
    def __init__(self, x):
        super().__init__(x)
        self.d = 1
rec = []
for cls in (B, C, D):
    print(cls.__name__, "__init__" in cls.__dict__)
real_c = C.__init__
def w(self, *a, **k):
    real_c(self, *a, **k)
    rec.append(("C", self.x))
C.__init__ = w
c = C(5); b = B(6)
print(rec)
del C.__init__
rec.clear(); C(7); print(rec, C.__init__ is B.__init__)
real_b = B.__init__
def wb(self, *a, **k):
    real_b(self, *a, **k); rec.append(("B", self.x))
B.__init__ = wb
D(9); print(rec)
B.__init__ = real_b
import asyncio
class S:
    async def m(self, a):
        return a + 1
real_m = S.m
async def wm(self, a):
    rec.append("m"); return await real_m(self, a)
S.m = wm
print(asyncio.run(S().m(1)), rec)
S.m = real_m
