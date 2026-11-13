"""Digital-twin construction, wiring and boot checks for the device named by TEST_DEVICE - one job per generated
device, dispatched by scripts/test.sh (SPECIFICATION.md E.2.1)."""

import os
import sys

sys.path.insert(0, "digital_twin")  # see tests/test_digital_twin_sgp40.py's own comment for why
sys.path.insert(0, "digital_twin/unixport")  # the UDP shim's directory (digital_twin/README.md "_unix_port_udp_addr_shim.py")

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()  # before any poll object is registered (digital_twin/README.md "Known gaps")
patch_asy_udp_socket_for_unix_port()  # before any UDPSocket is constructed (digital_twin/README.md "_unix_port_udp_addr_shim.py")

PER_DEVICE = True
device = os.getenv("TEST_DEVICE")
if not device:
    raise RuntimeError("run through scripts/test.sh, or set TEST_DEVICE to one of devices/*.toml")

import machine  # noqa: E402 - imported after the prewarm and the UDP shim
import microtest  # noqa: E402 - imported after the prewarm and the UDP shim
import network  # noqa: E402 - imported after the prewarm and the UDP shim
from _digital_twin_construction_scenarios import register_for_device  # noqa: E402 - imported after the prewarm and the UDP shim

globals().update(register_for_device(device))
microtest.after_each(machine.reset_test_state)
microtest.after_each(network.reset_test_state)

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
