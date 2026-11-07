exec(open("tests/test_asy_webserver_connections.py").read().split('if __name__ == "__main__":')[0])
clock = _DrivenClock()
service = _make_service(per_call_timeout_s=1.0, outer_cap_s=2.0)
stand_in = _AsyncioStandIn(wait_for=clock.wait_for, sleep=clock.sleep)
async def one():
    await service.setup()
    w = _Writer()
    await service._serve(_Reader([(0, _GET_STATUS)]), w)
    return len(w.written)
try:
    n = run(_driven(clock, one()))
finally:
    stand_in.uninstall()
print("PROBE one GET /status took virtual", clock.now, "s =", round(clock.now / _STEP_S), "rounds; bytes", n)
