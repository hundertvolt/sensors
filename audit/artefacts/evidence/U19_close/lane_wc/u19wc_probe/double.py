exec(open("tests/test_asy_webserver_connections.py").read().split('if __name__ == "__main__":')[0])
clock = _DrivenClock()
service = _make_service(per_call_timeout_s=1.0, outer_cap_s=5.0, debug=2)
stand_in = _AsyncioStandIn(wait_for=clock.wait_for, sleep=clock.sleep)
console = _Console()
async def one():
    await service.setup()
    w = _Writer()
    await service._serve(_Reader([], eof=False), w)   # a client that connects and sends nothing
    return w.written[:12], await _log(service)
try:
    r = run(_driven(clock, one()))
finally:
    console.restore()
    stand_in.uninstall()
print("PROBE", r, [l[:2] for l in console.lines])
