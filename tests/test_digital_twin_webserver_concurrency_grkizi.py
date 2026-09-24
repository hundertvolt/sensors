"""Real-socket concurrent-connection coverage for WebserverService on grkizi - one of six
wrappers over the shared tests/_webserver_concurrency_scenarios.py library (Part E.2.1)."""

import sys

sys.path.insert(0, "digital_twin")

from unix_port_poll_prewarm import prewarm_poll_set

# First, before the library boots a device and bursts real connections at it: pollfds growth is a
# Unix-port segfault otherwise (digital_twin/README.md's "Known gaps").
prewarm_poll_set()

from _webserver_concurrency_scenarios import register_for_device  # noqa: E402 - must follow the prewarm

globals().update(register_for_device("grkizi"))

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
