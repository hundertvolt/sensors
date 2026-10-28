import sys
src = open("wt-u19wc/tests/test_asy_webserver_connections.py").read()
s = src
s = s.replace('''    expected, durations, normal, log, open_conns = run(scenario())
''', '''    expected, durations, normal, log, open_conns = run(scenario())
    print("PROBE eagain durations", durations, "feeder worst", feeder.worst_ms, "attempts", [w.send_attempts for w in stuck])
''')
s = s.replace('''    assert rebound  # Microdot's print_exception() is the service's level-gated one
''', '''    print("PROBE load virtual", clock.now, "feeder worst", feeder.worst_ms)
    assert rebound  # Microdot's print_exception() is the service's level-gated one
''')
s = s.replace('''if __name__ == "__main__":
    import microtest

    microtest.run(globals())''', '''if __name__ == "__main__":
    for _name, _fn in list(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _t0 = time.ticks_ms()
            try:
                _fn()
            except Exception as _e:
                print("PROBE FAIL", _name, repr(_e))
            print("PROBE time", time.ticks_diff(time.ticks_ms(), _t0), "ms", _name)''')
open("u19wc_probe/probe_connections.py", "w").write(s)
