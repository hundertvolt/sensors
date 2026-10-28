import asyncio, sys
ns = {"__name__": "x"}
exec(open("tests/test_asy_system_service.py").read(), ns)
svc = ns["make_service"]()
calls = [0]
def starter():
    calls[0] += 1
    async def _c():
        raise RuntimeError("probe death")
    return asyncio.create_task(_c())
real_log = svc._log_dead_task
seen = []
async def logged(task, n):
    print("log_dead_task", id(task), "again" if id(task) in seen else "first", "armed", svc._reset_armed)
    seen.append(id(task))
    await real_log(task, n)
svc._log_dead_task = logged
async def scenario():
    sup = asyncio.create_task(svc.start_and_check_tasks([starter]))
    for _ in range(400):
        await asyncio.sleep(0)
    print("armed", svc._reset_armed, "starts", calls[0], "log", (await svc.get_error_counter())["SYSTEM"], "count", svc.pr._err_count)
    sup.cancel()
with ns["_FastAsyncSleep"]():
    asyncio.run(scenario())
print("survived")
