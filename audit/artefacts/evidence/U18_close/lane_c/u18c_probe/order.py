import asyncio
order = []
async def old():
    try:
        await asyncio.sleep(10)
    finally:
        order.append("old-finally")
async def new():
    order.append("new-start")
async def main():
    t = asyncio.create_task(old())
    await asyncio.sleep_ms(20)
    t.cancel()
    asyncio.create_task(new())
    await asyncio.sleep_ms(20)
    print(order)
asyncio.run(main())
