import test_asy_webserver_service as t

real_setup = t._CommandBench.setup
real_cmd = t._CommandBench._system_cmd


async def setup_without_owner_lock(self):
    await real_setup(self)
    self.reader.cfgmgr.owner_lock = None  # the mutation: the sequence no longer waits out the PUT


async def cmd_holding_the_put_lock(self, cmd):
    async with self.reader._set_lock:  # the mutation: the caller holds the owner lock while it dispatches
        return await real_cmd(self, cmd)


for label, attr, fn, test in (
    ("no owner lock", "setup", setup_without_owner_lock, t.test_a_config_put_mid_write_when_a_command_arrives_is_waited_out_then_flushed),
    ("lock held at dispatch", "_system_cmd", cmd_holding_the_put_lock, t.test_each_system_command_over_put_system_reaches_its_reset_arm_without_a_lock_held),
):
    saved = getattr(t._CommandBench, attr)
    setattr(t._CommandBench, attr, fn)
    try:
        test()
        print("MUTANT SURVIVED:", label)
    except AssertionError as e:
        print("MUTANT KILLED:", label, repr(e))
    finally:
        setattr(t._CommandBench, attr, saved)
