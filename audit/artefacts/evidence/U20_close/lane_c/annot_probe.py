import asyncio
x: UndefinedName
y: "Q"
class C: pass
z: C
async def build() -> None:
    global x, z
    x = 1
    z = C()
print("before", hasattr(__import__("annot_probe"), "x") if False else "skip")
