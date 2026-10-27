"""The listener close on silicon (SPECIFICATION.md B.14.4): closing a listening socket, and one whose listen() ran out
of heap, leaves lwIP's two TCP pcb pools byte for byte as they were, and the stack answers after. The pools' addresses
come from the flashed image's own firmware.elf; the device script reads memory, writes none and touches no flash."""

import errno
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import micropython_overrides
import pytest
import setup_toolchain
from harness import DEVICE_SCRIPTS_DIR, MEMORY_ERROR_MARKERS, REPO_ROOT, bench_device, configured_max_connections, elf_symbols, parse_facts

if TYPE_CHECKING:
    from collections.abc import Callable

    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ()

_SCRIPT = DEVICE_SCRIPTS_DIR / "listener_close_leaves_the_pcb_pools.py"
# The script's pool names -> lwIP's memp pool (lib/lwip/src/include/lwip/priv/memp_std.h) and the image record's count.
_POOLS = {"listen": ("TCP_PCB_LISTEN", "MEMP_NUM_TCP_PCB_LISTEN"), "conn": ("TCP_PCB", "MEMP_NUM_TCP_PCB")}
_DESC_BYTES = 12  # struct memp_desc without desc and stats (lib/lwip/src/include/lwip/priv/memp_priv.h:108-130)
_MEM_ALIGNMENT = 4  # source: extmod/lwip-include/lwipopts_common.h:42 (v1.29.0); LWIP_MEM_ALIGN_BUFFER adds it less one


def _image(request: pytest.FixtureRequest) -> "tuple[Path, dict[str, int]]":
    # The rp2 build directory whose firmware.elf is the flashed image's: its uf2 equals the one beside the image record
    # (--image-record, else the bench device's own), and the build compiled the patched modlwip copy.
    toolchain = Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain"))
    board_name = setup_toolchain.load_versions(setup_toolchain.VERSIONS_PATH)["toolchain"]["board"]
    build_dir = toolchain / "micropython" / "ports" / "rp2" / f"build-{board_name}"
    option = request.config.getoption("--image-record")
    record_path = Path(option) if option else REPO_ROOT / "build" / f"firmware-{bench_device()}.json"
    rebuild = f"build and flash the bench image (uv run scripts/build_firmware.py {bench_device()}) with this toolchain"
    for path in (record_path, record_path.with_suffix(".uf2"), build_dir / "firmware.uf2", build_dir / "firmware.elf"):
        assert path.is_file(), f"{path} is missing: {rebuild}"
    assert (build_dir / "firmware.uf2").read_bytes() == record_path.with_suffix(".uf2").read_bytes(), f"{build_dir} holds another build than {record_path.with_suffix('.uf2')}: {rebuild}"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert isinstance(record, dict) and isinstance(record.get("lwip"), dict) and isinstance(record.get("overrides"), list), f"{record_path} holds no image record: {rebuild}"
    assert micropython_overrides.MODLWIP_OVERRIDE_DIR_NAME in record["overrides"], f"the image record names no modlwip override: {record['overrides']}"
    copy = toolchain / "build_overrides" / micropython_overrides.MODLWIP_OVERRIDE_DIR_NAME / micropython_overrides.MODLWIP_COPY_NAME
    micropython_overrides.verify_modlwip_eagain_in_build(build_dir, toolchain / "micropython", copy)
    return build_dir / "firmware.elf", {name: record["lwip"][count] for name, (_pool, count) in _POOLS.items()}


def _pool_addresses(elf: Path) -> "dict[str, dict[str, int]]":
    # Each pool's descriptor, slot array (address and size) and free-list head, from the image's own symbol table
    # (lib/lwip/src/core/memp.c: LWIP_MEMPOOL_DECLARE, through lwip/priv/memp_std.h).
    symbols = elf_symbols(elf)
    pools: dict[str, dict[str, int]] = {}
    for name, (pool, _count) in _POOLS.items():
        wanted = (f"memp_{pool}", f"memp_memory_{pool}_base", f"memp_tab_{pool}")
        missing = [symbol for symbol in wanted if symbol not in symbols]
        assert not missing, f"{elf} carries no {missing}: lwIP's pool layout has changed (lib/lwip/src/core/memp.c)"
        desc, base, tab = (symbols[symbol] for symbol in wanted)
        assert desc[1] == _DESC_BYTES, f"memp_{pool} is {desc[1]} B, not the {_DESC_BYTES} B descriptor the script reads"
        pools[name] = {"desc": desc[0], "base": base[0], "bytes": base[1], "tab": tab[0]}
    return pools


def test_closing_a_listener_and_a_failed_listen_leave_the_pcb_pools_as_they_were(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]") -> None:
    twin = request.config.getoption("--twin")
    pools: dict[str, dict[str, int]] = {}
    counts: dict[str, int] = {}
    if not twin:
        elf, counts = _image(request)
        pools = _pool_addresses(elf)
    # The product's backlog when the TOML sets none, max_connections + 1 (src/asy_webserver_service.py:584).
    output = board.run_isolated(_SCRIPT, pools=pools, backlog=configured_max_connections() + 1)
    failed = [line for line in output.splitlines() if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    assert not failed, "the run printed an allocation failure:\n" + "\n".join(failed)
    facts = parse_facts(output)
    assert facts.get("listener_closed") is True, f"closing the listener did not return: {facts}"
    assert facts.get("port_held_errno") is None, f"a bind without SO_REUSEADDR was refused after both closes - a pcb still holds the port: {facts}"
    if twin:
        result_note("twin run: no lwIP pools to read, and the host stack's listen() allocates nothing to refuse - the pool half is silicon's")
        assert facts.get("round_trip") is True, f"the loopback round trip did not echo: {facts}"
        return
    assert facts.get("platform") == "rp2", f"the script ran on {facts.get('platform')}: {facts}"
    assert facts.get("listen_refused") is True, f"listen() with the heap locked did not refuse its accept queue, so the failed-listen close never ran: {facts}"
    expected = {name: [(pools[name]["bytes"] - (_MEM_ALIGNMENT - 1)) // counts[name], counts[name], pools[name]["base"], pools[name]["tab"]] for name in _POOLS}
    assert facts.get("pools") == expected and facts.get("pools_matched") is True, f"the board's pool descriptors are not the ELF's - another image is on the board: read {facts.get('pools')}, ELF {expected}"
    free, used, changed = facts.get("free"), facts.get("used"), facts.get("changed")
    assert isinstance(free, dict) and isinstance(used, dict) and isinstance(changed, dict) and set(free) == set(_POOLS), f"no free-list facts for every pool: {facts}"
    result_note(f"pools {expected}; free slots before/after/end {free}; the slots the sockets took {used}; changed words {changed}")
    for name, (before, after, end) in free.items():
        assert None not in (before, after, end), f"the {name} pool's free list is broken in one of the three pictures: {free[name]}"
        assert set(before) <= set(after) and set(before) <= set(end), f"the {name} pool lost free slots - a pcb leaked: before {before}, after {after}, end {end}"
        assert set(before) - {used.get(name)}, f"the {name} pool had no free slot to compare but the one the sockets took ({used.get(name)}), so its byte check would pass on nothing: before {before}"
    assert changed["total"] == 0, f"{changed['total']} words of free slots changed across the two closes: {changed['first']}"
    # rp2's lwIP has no loopback netif (lwip/opt.h:1792), so ip4_route() refuses 127.0.0.1: the stack's own answer,
    # EHOSTUNREACH 113 on the host as in MicroPython (py/mperrno.h:81).
    assert facts.get("round_trip") in (True, errno.EHOSTUNREACH), f"the stack did not answer the round trip with an echo or its route refusal: {facts.get('round_trip')}"
