# Scratch mutation sweep: each mutant of src/asy_system_service.py must fail the test that pins the mutated rule.
import subprocess
import sys
from pathlib import Path

S = Path("/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad")
WT = S / "wt-u20s"
SRC = (WT / "src/asy_system_service.py").read_text()
MUT = S / "u20s_work/mut"
MP = f"{MUT}:build/generated_src:src:tests:frozen_modules:.frozen"
BIN = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
MUTANTS = [
    ("gate re-check after the preflight", "            if self._reset_armed:  # re-checked: the preflight can yield, and an escalation may have armed meanwhile\n                refusal = \"a reset is already armed\"\n", "", ["test_an_escalation_armed_during_the_erase_preflight_refuses_the_command"]),
    ("escalation re-check after its log write", "                if self._feed_owned:\n                    continue\n", "", ["test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset"]),
    ("feed_watchdog latched on ownership", " and not self._force_watchdog_starve and not self._feed_owned:\n            self._watchdog.feed()", " and not self._force_watchdog_starve:\n            self._watchdog.feed()", ["test_after_the_takeover_no_other_site_feeds", "test_a_command_before_the_supervisor_runs_waits_for_its_first_pass"]),
    ("scan breaks once owned", "                    if self._feed_owned:\n                        break  # a command passed the gate during this pass: the shutdown sequence stops every task\n", "", ["test_tasks_dying_while_a_command_runs_never_escalate"]),
    ("S2 waits on the owner lock", "                if store.owner_lock is None:\n", "                if True:\n", ["test_a_config_put_mid_write_when_a_command_starts_is_flushed_before_the_arm"]),
    ("unpause refused once owned", "if not (self._reset_armed or self._feed_owned) and", "if not self._reset_armed and", ["test_a_deadline_crossed_after_an_accepted_command_leaves_storage_paused"]),
    ("pause refused during a shutdown", "        if self._shutdown:\n            return False\n        if self._storage_pause", "        if self._storage_pause", ["test_the_same_command_again_answers_true_and_any_other_answers_false", "test_two_commands_at_once_start_one_sequence_and_one_reset"]),
    ("stores closed at acceptance", "            for store in self._config_stores:\n                store.close_writes()\n            self.pr.evt(\"System command", "            self.pr.evt(\"System command", ["test_reboot_takes_over_closes_quiesces_stops_then_resets_with_code_3", "test_every_command_over_rest_reaches_its_arm_without_an_owner_lock_deadlock"]),
    ("the own feed right before the arm", "            if fed:\n                self._own_feed()  # a system command's last feed, right before the arm\n", "", ["test_a_healthy_sequence_feeds_once_per_step_and_last_right_before_the_arm"]),
    ("S5 incomplete -> code 9", "            code = purpose if ok else _RR_COMMAND_INCOMPLETE\n", "            code = purpose\n", ["test_a_file_that_cannot_be_deleted_ends_the_reset_in_code_9"]),
    ("S1 proves the supervisor stopped", "        if task is None or not task.done():\n            return  # not proven stopped", "        if False:\n            return  # not proven stopped", ["test_a_hang_in_any_step_is_never_fed"]),
    ("same purpose answers True", "                return self._shutdown == purpose\n", "                return False\n", ["test_the_same_command_again_answers_true_and_any_other_answers_false"]),
    ("run_setups feeds after each", "            await setup()\n            self.feed_watchdog()\n", "            await setup()\n", ["test_run_setups_awaits_in_order_feeds_after_each_and_collects_after_each_feed"]),
    ("config faults filled", "        self._config_faults = [store.module_name for store in self._config_stores if store.faulted]\n", "", ["test_get_config_faults_names_each_faulted_store_once_in_list_order"]),
    ("tasks stopped in S4", "            if t is not None and not t.done():\n                t.cancel()\n", "            pass\n", ["test_reboot_takes_over_closes_quiesces_stops_then_resets_with_code_3", "test_a_task_cancelled_inside_a_bus_session_frees_the_bus"]),
]
results = []
for name, old, new, tests in MUTANTS:
    assert SRC.count(old) == 1, (name, SRC.count(old))
    (MUT / "asy_system_service.py").write_text(SRC.replace(old, new))
    for test in tests:
        cmd = f"ip link set lo up; TZ=UTC MICROPYPATH='{MP}' nice -n 19 timeout 120 {BIN} -X heapsize=16M {S}/u20s_work/trace_all.py test_asy_system_service {test}"
        out = subprocess.run(["unshare", "-n", "bash", "-c", cmd], cwd=WT, capture_output=True, text=True).stdout
        caught = ("FAIL " + test) in out or ("OK " + test) not in out
        results.append((name, test, "CAUGHT" if caught else "MISSED"))
        print(results[-1], flush=True)
(MUT / "asy_system_service.py").unlink()
sys.exit(0 if all(r[2] == "CAUGHT" for r in results) else 1)
