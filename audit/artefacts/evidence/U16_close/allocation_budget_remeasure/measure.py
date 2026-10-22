import test_asy_fram_allocation_budget as t
async def blank():
    _m, lg = await t._rig()
    return await t._priced(lg)
async def valid():
    _m, lg = await t._rig()
    await lg.setup()
    return await t._priced(lg)
import sys
for name, fn in (("blank", blank), ("valid", valid)):
    vals = []
    for _ in range(5):
        a, c = t.run(fn())
        assert a == c, (a, c)
        vals.append(a)
    print(name, "settrace" if hasattr(sys, "settrace") else "standard", sorted(vals), "median", sorted(vals)[2])
