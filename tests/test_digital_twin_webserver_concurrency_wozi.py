"""Real-socket concurrent-connection regression coverage for WebserverService against wozi
specifically - one of six per-device files generated from the shared
tests/_webserver_concurrency_scenarios.py scenario library (see that module's own docstring for
the full scenario set, the rationale for the per-device split, and every pointer to
SPECIFICATION.md this used to carry directly)."""

from _webserver_concurrency_scenarios import register_for_device

globals().update(register_for_device("wozi"))

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
