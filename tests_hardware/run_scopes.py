"""Named scopes for scripts/run_bench_hardware_suite.sh --scope NAME: the flash and bench tests one change
reaches, each with the reason, run on their own until the whole of both tiers runs, and the settings groups
their own writes need (--allow-persistence-writes-to). `run_scopes.py NAME flash|bench|writes` lists one."""

from __future__ import annotations

import sys
from typing import NamedTuple


class Scope(NamedTuple):
    flash: tuple[tuple[str, str], ...]  # (pytest node id, why the change reaches it)
    bench: tuple[tuple[str, str], ...]
    writes: tuple[str, ...]  # every group a persistence_write test of the scope names (persistence_groups.py)


_FLASH = "tests_hardware/flash/"
_BENCH = "tests_hardware/bench/"
_RESOLVER = "the resolver the client shares with NTP changed: its query build and answer parse"
_CEILING = "the build's connection ceiling moved 6 -> 5 for the client's own socket"

SCOPES: dict[str, Scope] = {
    # The MQTT client PoC (SPECIFICATION.md Part A.11) and what its branch changed beside it (owner, 2026-10-08:
    # "only test MQTT (and whatever is affected by your changes) on the bench. you shall not run the whole bench
    # at this time (will happen lateron when mqtt as such is running)").
    "mqtt": Scope(
        flash=(
            (f"{_FLASH}test_fram_storage.py::test_every_fram_wired_module_gets_a_real_chunk_after_a_full_system_build", "the FRAM layout gains the MQTT and CFGMGR_MQTT chunks"),
            (f"{_FLASH}test_memory_stress.py::test_real_gc_heap_headroom_survives_a_full_system_build", "the client's buffers are resident in the full system build"),
            (f"{_FLASH}test_toolchain_flash_boot.py::test_env_tier_flash_recurring_run_is_idempotent", "toolchain/versions.toml's apt_packages gains mosquitto"),
        ),
        bench=(
            (f"{_BENCH}test_mqtt_broker_faults.py", "the client itself, against a real broker"),
            (f"{_BENCH}test_wifi_networking.py::test_real_ntp_sync_succeeds_over_genuine_udp", _RESOLVER),
            (f"{_BENCH}test_wifi_networking.py::test_real_dns_resolution_succeeds_over_genuine_udp", _RESOLVER),
            (f"{_BENCH}test_network_resilience.py::test_dns_server_sends_garbage_instead_of_a_valid_response", _RESOLVER),
            (f"{_BENCH}test_network_resilience.py::test_connections_at_and_above_the_real_socket_limit_degrade_cleanly", _CEILING),
            (f"{_BENCH}test_network_resilience.py::test_the_board_holds_exactly_the_connection_ceiling_this_tree_configures", _CEILING),
            (f"{_BENCH}test_network_resilience.py::test_a_full_ceiling_of_concurrent_requests_is_each_served_a_complete_body", _CEILING),
            (f"{_BENCH}test_network_resilience.py::test_a_concurrent_page_load_is_byte_identical_to_an_uncontended_one", _CEILING),
            (f"{_BENCH}test_network_resilience.py::test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status", _CEILING),
            (f"{_BENCH}test_network_resilience.py::test_the_largest_body_any_schema_can_produce_still_fits_under_the_cap", "the MQTT settings make PUT /networking the largest body"),
            (f"{_BENCH}test_end_to_end_timing.py::test_real_concurrent_client_burst_does_not_crash_the_webserver", _CEILING),
            (f"{_BENCH}test_end_to_end_timing.py::test_cold_boot_to_first_http_response_latency_is_sane", "the boot's setup batch gains the client's setup()"),
            (f"{_BENCH}test_end_to_end_timing.py::test_real_reboot_sequencing_via_rest_completes_cleanly", "the reboot path now carries the client's config store"),
            (f"{_BENCH}test_heap_under_connection_ceiling.py", "the heap at a full ceiling, the client resident"),
            (f"{_BENCH}test_serving_heap_at_default_gc.py", "serving at the reactive gc default, the client resident"),
            (f"{_BENCH}test_memory_stress_bench.py::test_real_hardware_survives_max_speed_hammer_load_without_memoryerror_or_reboot", "the hammer load's heap, the client resident"),
            (f"{_BENCH}test_rest_endpoints_over_sta.py::test_real_static_website_content_serves_over_the_normal_bridge_network", "the device's website gains the MQTT settings group"),
        ),
        writes=("networking/mqtt",),
    ),
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in SCOPES or argv[1] not in ("flash", "bench", "writes"):
        print(f"usage: run_scopes.py {{{','.join(sorted(SCOPES))}}} {{flash,bench,writes}}", file=sys.stderr)
        return 2
    scope = SCOPES[argv[0]]
    if argv[1] == "writes":
        print("\n".join(scope.writes))
    else:
        print("\n".join(node for node, _reason in (scope.flash if argv[1] == "flash" else scope.bench)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
