# Type-check-only shape of the BENCH dict harness.render_device_script() renders into a device script: every key
# tests_hardware/bench_facts.py's build() returns, plus the per-run extras a host test passes. total=False because the
# extras are per script; a key a script reads that build() never returns fails tests_scripts' bench-facts guard.

from typing import TypedDict

class BusFacts(TypedDict, total=False):
    id: int
    scl_pin: int
    sda_pin: int
    frequency: int
    timeout: int
    sck_pin: int
    mosi_pin: int
    miso_pin: int
    tx_pin: int
    rx_pin: int
    baudrate: int
    rxbuf: int
    txbuf: int
    rx_ring: int
    poll_wait_ms: int
    poll_idle_ms: int
    crc: str
    max_transfer_bytes: int

class InstanceFacts(TypedDict, total=False):
    driver: str
    name_ext: str
    bus: str
    address: int
    irq_pin: int
    cs_pin: int
    pin: int

class Isl29125Facts(TypedDict):
    mode_rgb: int

class BenchFacts(TypedDict, total=False):
    device_module: str
    bus: dict[str, BusFacts]
    instances: dict[str, InstanceFacts]
    addresses: dict[str, int]
    fram_max_size: int
    fram_wired: list[str]
    fram_backed_loggers: list[str]
    isl29125: Isl29125Facts
    system_schema: dict[str, tuple[str, object, object, object, object]]
    scd30_schema: dict[str, tuple[str, object, object, object, object]]
    float_fields: dict[str, tuple[float, float]]
    resync_bound_ms: int
    depth: int
    # Per-run extras, each passed by its host test from one named source.
    standard_debug_level: int
    bounds: dict[str, tuple[float, float, str]]
    worst_case_allocation: int
    CRC_MODE: str
    SEAM: int
    NONCE: int
    COMMAND: str
    STATE: str
    PHASE: str
    KIND: str
    BOOT_DONE: str
    ARM: str
    part: str
    mode: str
    files: list[str]
    pools: dict[str, dict[str, int]]
    backlog: int
