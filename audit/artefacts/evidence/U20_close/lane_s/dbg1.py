# Scratch: state of the escalation-log interleaving when the sequence does not finish.
import asyncio

import machine
import test_asy_system_service as t

rig = t._Rig(tasks=0)
calls = [0]
rig.starters = [t._dead_starter(calls)]
release, reached = asyncio.Event(), asyncio.Event()
real_err_s = rig.svc.pr.err_s


async def gated_err_s(*args, errno=0):
    if errno == t.code("E", "TASK_BUDGET_REBOOT"):
        reached.set()
        await release.wait()
    await real_err_s(*args, errno=errno)


rig.svc.pr.err_s = gated_err_s


async def scenario():
    sup = await rig.start()
    await reached.wait()
    print("reached; armed", rig.svc._reset_armed, "calls", calls[0])
    print("answer", await rig.svc.erase_fram())
    release.set()
    for i in range(200000):
        await asyncio.sleep(0)
        if i % 500 == 0:
            sv = rig.svc
            print(i, "parked", sv._supervisor_parked.is_set(), "sup", sv._supervisor_task.done(), "seq", sv._shutdown_task.done(), "ev", rig.events[-3:], "units", sum(1 for a, n in rig.chip.writes if n == 256))
        if rig.svc._shutdown_task.done():
            break
    sv = rig.svc
    print("parked", sv._supervisor_parked.is_set(), "sup done", sv._supervisor_task.done(), "seq done", sv._shutdown_task.done())
    print("armed", sv._reset_armed, "events", rig.events[-6:], "tasks", sv._tasks, "chunks", len(rig.manager._chunks))


with t._FastAsyncSleep():
    t.run(scenario())
print("record", machine.mem_backup(0)[1], "reset_bits", t.asy_system_service._reset_bits)
