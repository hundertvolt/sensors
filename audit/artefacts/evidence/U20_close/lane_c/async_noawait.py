import asyncio
async def build():
    global x
    x = 1
async def main():
    await build()
    print("built", x)
asyncio.run(main())
