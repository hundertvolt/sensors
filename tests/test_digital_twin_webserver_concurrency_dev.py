"""Real-socket concurrent-connection coverage for WebserverService on dev - one of six
wrappers over the shared tests/_webserver_concurrency_scenarios.py library (Part E.2.1)."""

from _webserver_concurrency_scenarios import register_for_device

globals().update(register_for_device("dev"))

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
