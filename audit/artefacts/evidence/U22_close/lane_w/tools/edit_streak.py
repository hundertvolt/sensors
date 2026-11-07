# Applies the idle-silent-iteration streak rule to src and rewrites the raising-attempt test onto the real cadence.
import sys
wt = sys.argv[1]
p = wt + "/src/asy_wifi_service.py"
s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:90]
    s = s.replace(old, new)
rep("""                if self._reconn_wifi:
                    await self._handle_reconnect_trigger()
                if self._conn_phase == _PHASE_HOTSPOT:
                    await self._run_hotspot_mode()
                elif self._conn_phase == _PHASE_SILENT:
                    await self._run_silent_mode()
                else:
                    await self._run_sta_mode()
                # Consecutive-failure streak over real WLAN-hardware exceptions (separate from
                # _connection_failures' AP-reachability fallback): gives up on the whole task,
                # matching a Reader's _read_loop() returning False.
                if not await self._error_check((None,), condition=self._hw_op_failed):
                    await self.pr.err_s(
                        "Giving up after repeated WLAN hardware failures, restarting task.", errno=_ERR_WLAN_GIVE_UP,
                    )
                    return
""", """                if self._reconn_wifi:
                    await self._handle_reconnect_trigger()
                evidence = True  # an idle silent iteration made no radio call: it neither counts nor heals the streak
                if self._conn_phase == _PHASE_HOTSPOT:
                    await self._run_hotspot_mode()
                elif self._conn_phase == _PHASE_SILENT:
                    evidence = await self._run_silent_mode()
                else:
                    await self._run_sta_mode()
                # Consecutive-failure streak over real WLAN-hardware exceptions (separate from
                # _connection_failures' AP-reachability fallback): gives up on the whole task,
                # matching a Reader's _read_loop() returning False.
                if (evidence or self._hw_op_failed) and not await self._error_check((None,), condition=self._hw_op_failed):
                    await self.pr.err_s(
                        "Giving up after repeated WLAN hardware failures, restarting task.", errno=_ERR_WLAN_GIVE_UP,
                    )
                    return
""")
rep("""    async def _run_silent_mode(self) -> None:
        # One connect attempt per hotspot_time_min, uncapped, the watcher marking it due on the window's own timer; never a
        # scan: WLAN's scan() holds the VM up to 10 s (extmod/network_cyw43.c:236-246, v1.29.0), past the watchdog.
        if not self._hotspot_timer_running:
            await self._arm_hotspot_timer()  # a failed arm is persisted and retried next iteration
        if not self._silent_attempt_due:
            return
        self._silent_attempt_due = False""", """    async def _run_silent_mode(self) -> bool:  # True: an attempt ran, so the hardware streak has evidence to judge
        # One connect attempt per hotspot_time_min, uncapped, the watcher marking it due on the window's own timer; never a
        # scan: WLAN's scan() holds the VM up to 10 s (extmod/network_cyw43.c:236-246, v1.29.0), past the watchdog.
        if not self._hotspot_timer_running:
            await self._arm_hotspot_timer()  # a failed arm is persisted and retried next iteration
        if not self._silent_attempt_due:
            return False
        self._silent_attempt_due = False""")
rep("""        if self._conn_phase == _PHASE_STA_ESTABLISHED:  # a link ends the period: a later loss takes the 60 s retry
            self._hotspot_timer.deinit()
            self._hotspot_timer_running = False

    async def _run_sta_mode(self) -> None:""", """        if self._conn_phase == _PHASE_STA_ESTABLISHED:  # a link ends the period: a later loss takes the 60 s retry
            self._hotspot_timer.deinit()
            self._hotspot_timer_running = False
        return True

    async def _run_sta_mode(self) -> None:""")
open(p, "w").write(s)

p = wt + "/tests/test_asy_wifi_service.py"
s = open(p).read()
rep('''def test_a_raising_silent_attempt_feeds_the_hardware_streak_and_keeps_the_mode() -> None:
    # A silent attempt is an ordinary attempt: a raising connect() persists WLAN_STA_START and counts toward the
    # hardware streak; its device rung, its give-up and the task's restart all keep the silent mode.
    with _RaisingConnectWLAN():
        client = make_client_with_json(_VALID_JSON, max_module_error=2)
        run(client.pr.setup())
        client._hotspot_timeout_trigger_event = _ParkedFlag()  # type: ignore[assignment]  # see _ParkedFlag
        client._conn_phase = _PHASE_SILENT
        real = client._run_silent_mode

        async def every_iteration_due() -> None:
            client._silent_attempt_due = True  # a period fired before every iteration: each one attempts
            await real()

        client._run_silent_mode = every_iteration_due  # type: ignore[method-assign]

        async def give_up() -> bool:
            loop = asyncio.create_task(client._connect_loop())
            await asyncio.wait_for(loop, _CONNECT_BOUND_S)  # the give-up returns: the supervisor restarts it
            return loop.done()

        with _FastAsyncSleep():
            assert run(give_up()) is True
        kept = _used_slots(run(client.get_error_counter()))
        for name in (("E", "WLAN_STA_START"), ("W", "DEVICE_RECOVERY"), ("E", "GIVE_UP"), ("E", "WLAN_GIVE_UP")):
            assert code(*name) in kept, (name, kept)
        assert client._conn_phase == _PHASE_SILENT, "the give-up left the silent mode"
        client._run_silent_mode = real  # type: ignore[method-assign]  # the restart's periods are ordinary again

        async def restarted() -> None:''', '''def test_a_raising_silent_attempt_feeds_the_hardware_streak_and_keeps_the_mode() -> None:
    # A silent attempt is an ordinary attempt: a raising connect() persists WLAN_STA_START and counts toward the
    # hardware streak, which the idle iterations between periods leave as it is, so a radio that never comes up still
    # reaches its device rung and its give-up; both, and the task's restart, keep the silent mode.
    with _RaisingConnectWLAN():
        client = make_client_with_json(_VALID_JSON, max_module_error=2)
        run(client.pr.setup())
        client._hotspot_timeout_trigger_event = _ParkedFlag()  # type: ignore[assignment]  # see _ParkedFlag
        client._conn_phase = _PHASE_SILENT
        real = client._run_silent_mode
        iterations = [0]

        async def counted() -> bool:
            iterations[0] += 1
            return await real()

        client._run_silent_mode = counted  # type: ignore[method-assign]  # counts the real iterations

        async def idle_then_fire(loop: "asyncio.Task[None]") -> None:
            target = iterations[0] + 6  # six idle iterations, half a minute of refreshes, then the period's fire
            await _until(lambda: iterations[0] >= target or loop.done())
            client._hotspot_timer.trigger()

        async def give_up() -> "tuple[bool, list[int]]":
            loop = asyncio.create_task(client._connect_loop())
            streak = []
            for _ in range(4):  # the give-up needs max_module_error + 1 failed attempts, each one period apart
                await idle_then_fire(loop)
                await _until(lambda: not client._silent_attempt_due or loop.done())
                streak.append(client._err_cnt_internal)
            await _until(loop.done)
            done = loop.done()
            if not done:
                await _cancel(loop)
            return done, streak

        with _FastAsyncSleep():
            done, streak = run(give_up())
        kept = _used_slots(run(client.get_error_counter()))
        assert done is True, ("the streak never reached its give-up", streak, kept)
        for name in (("E", "WLAN_STA_START"), ("W", "DEVICE_RECOVERY"), ("E", "GIVE_UP"), ("E", "WLAN_GIVE_UP")):
            assert code(*name) in kept, (name, kept)
        assert client._conn_phase == _PHASE_SILENT, "the give-up left the silent mode"
        client._run_silent_mode = real  # type: ignore[method-assign]

        async def restarted() -> None:''')
open(p, "w").write(s)
print("edited")

s = open(p).read()
rep('''    # from which side, lands in the same mode as "initial connection attempt after a fresh boot"."), from each state.
    for source in (_PHASE_HOTSPOT, _PHASE_SILENT, _PHASE_STA_ESTABLISHED):''', '''    # from which side, lands in the same mode as "initial connection attempt after a fresh boot"."), from each state, the
    # window end's own streak (seeking with the hotspot already used) included.
    for source in (_PHASE_HOTSPOT, _PHASE_SILENT, _PHASE_STA_ESTABLISHED, _PHASE_STA_SEEKING):''')
rep('''        if source != _PHASE_STA_ESTABLISHED:
            run(client._arm_hotspot_timer())  # the hotspot's window, or the silent period''', '''        if source in (_PHASE_HOTSPOT, _PHASE_SILENT):
            run(client._arm_hotspot_timer())  # the hotspot's window, or the silent period''')
open(p, "w").write(s)
print("edited identity")
