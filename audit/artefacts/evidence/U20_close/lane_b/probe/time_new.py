import time
import test_asy_webserver_service as t

for name in ("test_each_system_command_over_put_system_reaches_its_reset_arm_without_a_lock_held", "test_a_config_put_mid_write_when_a_command_arrives_is_waited_out_then_flushed", "test_system_put_systemcmd_runs_only_on_the_exact_action_word"):
    s = time.ticks_ms()
    getattr(t, name)()
    print(name, time.ticks_diff(time.ticks_ms(), s), "ms")
