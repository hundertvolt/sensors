"""The one table of test port bands (SPECIFICATION.md E.1): each binding owner's own range, disjoint and below the OS
ephemeral range (32768-60999), since the files run concurrently and a MicroPython listener cannot read its port back;
an allocator that fails at its band's end; and a per-device band split evenly over the generated devices."""

import errno

from _twin_devices import generated_devices

# owner: (first, last, protocol). An owner is the module binding the ports; a fixed row is one bound by its own
# constant (the twin scan, the CI suite, the JS twins, the smoke), listed so no other row can take it.
BANDS = {
    "unix_port_poll_prewarm": (17400, 17463, "tcp"),
    "_sensortask_scenarios": (17500, 17509, "tcp"),
    "_digital_twin_ci_suite": (18080, 18080, "tcp"),
    "test_digital_twin_http_client": (18090, 18119, "tcp"),
    "test_asy_webserver_connections": (18600, 18699, "tcp"),
    "test_digital_twin_run_generic_integration": (19090, 19099, "tcp"),
    "dtsi": (19100, 19199, "tcp"),
    "test_digital_twin_wifi_modes": (19200, 19209, "tcp"),
    "test_digital_twin_bus_hazard_concurrency": (19400, 19419, "tcp"),
    "cross_browser_smoke": (19420, 19421, "tcp"),
    "_live_twin_command": (19481, 19481, "tcp"),
    "_live_matrix_command": (19482, 19482, "tcp"),
    "_digital_twin_construction_scenarios": (19500, 19599, "tcp"),
    "_digital_twin_scenarios": (20000, 20999, "tcp"),
    "asy_udp_socket": (21000, 21999, "udp"),
    "test_asy_captive_dns": (22000, 22999, "udp"),
    "test_asy_ntp_client": (23000, 23999, "udp"),
    "test_asy_dns_client": (24000, 24999, "udp"),
    "test_ntp_wifi_dns_integration": (25000, 25999, "udp"),
    "test_ntp_fram_system_integration": (26000, 26999, "udp"),
    "asy_wifi_service": (27000, 27999, "udp"),
    "test_shared_helpers": (28001, 28001, "udp"),
    "test_digital_twin_ntp": (29000, 29599, "udp"),
    "test_digital_twin_clock_jump": (29600, 29999, "udp"),
}
# The owners whose band is split over the generated devices: their per-device files run concurrently.
PER_DEVICE_OWNERS = ("dtsi", "_digital_twin_construction_scenarios", "_digital_twin_scenarios")


class PortAllocator:
    # Successive ports of one owner's band, or of one device's block of it; past its end is a failure, never a neighbour's port.
    def __init__(self, owner: str, device: "str | None" = None) -> None:
        self.owner = owner
        self.first, self.last = band_for_device(owner, device) if device is not None else BANDS[owner][:2]
        self._next = self.first

    def next(self) -> int:
        if self._next > self.last:
            raise AssertionError(f"{self.owner} ran past its port band {self.first}-{self.last}")
        port = self._next
        self._next += 1
        return port

    def taken(self, port: int) -> OSError:
        # What a user raises for an EADDRINUSE on one of this band's ports, naming the band.
        return OSError(errno.EADDRINUSE, f"port {port} (band {self.owner}) is taken")


def band_for_device(owner: str, device: str) -> "tuple[int, int]":
    # The device's block: its index in the generated devices times an even share of the band, so a new device shrinks each block.
    if owner not in PER_DEVICE_OWNERS:
        raise AssertionError(f"{owner} has no per-device band - use PortAllocator({owner!r})")
    devices = generated_devices()
    if device not in devices:
        raise AssertionError(f"{device!r} is not a generated device {devices!r}")
    first, last, _protocol = BANDS[owner]
    size = (last - first + 1) // len(devices)
    if size < 1:
        raise AssertionError(f"{owner}'s band {first}-{last} cannot give each of {len(devices)} devices a port")
    start = first + devices.index(device) * size
    return start, start + size - 1
