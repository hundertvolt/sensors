import annot_probe as m
print("x before:", getattr(m, "x", None), "z before:", getattr(m, "z", None))
try:
    m.x
except AttributeError as e:
    print("AttributeError", e)
import asyncio
asyncio.run(m.build())
print("x after:", m.x, type(m.z).__name__)
