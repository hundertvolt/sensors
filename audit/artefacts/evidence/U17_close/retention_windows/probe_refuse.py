# Raw heap growth per window of n refusals, n in a fixed sequence, results preallocated.
import gc
import test_asy_uart_comm as t
pair = t._cap_pair("responder")
def counting_set(cmd_id):
    return True, None
pair.responder._set_callback = counting_set
seq = (1, 1, 1, 50, 50, 200, 200, 1, 400)
res = [0] * len(seq)
async def go():
    await pair.responder._accept_set(pair.driver_b, counting_set, 0x23, 0, 4)
    for k in range(len(seq)):
        gc.collect(); before = gc.mem_alloc()
        for _ in range(seq[k]):
            await pair.responder._accept_set(pair.driver_b, counting_set, 0x23, 0, 4)
        gc.collect(); res[k] = gc.mem_alloc() - before
t.run(go(), limit=600)
print(list(zip(seq, res)))
print(t.persisted(pair.responder))
