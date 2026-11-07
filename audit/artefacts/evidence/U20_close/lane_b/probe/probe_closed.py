import test_asy_base_classes as t
r = t._chip_store_reader("probeclosed", t._VAL_SI + t._VAL_BOOL)
async def push(v):
    return True
r._push_callbacks["SelfCal"] = push
r.cfgmgr.close_writes()
print(t.run(t._put_flushed(r, {"SampleInterval": 42, "SelfCal": True, "Ghost": 1})), r.chip_writes, r.snapshot_reads)
