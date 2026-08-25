"""Manual, deliberately-aggressive concurrency stress tool for the (now root-caused and fixed, see `unix_port_poll_prewarm.py`) MicroPython Unix-port segfault under heavy concurrent connection load.
Full account, usage, and exit/crash behavior in `digital_twin/README.md`'s "Known gaps" section."""

# Same MICROPYPATH as run_wozi_integration.py; flags: --clients/--requests/--rounds/--host/--port.
# A genuine segfault kills the interpreter outright (check exit status / dmesg, no Python traceback);
# a MemoryError at higher concurrency is a distinct, catchable outcome this tool also reports.

import asyncio
import gc
import sys

import _http_client
import machine
from unix_port_poll_prewarm import prewarm_poll_set

import sensortask_wozi

_CONFIG_DIR = "digital_twin/config/"
_ENDPOINTS = ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status", "/")


async def _wait_until_built(timeout_s: float = 10.0) -> None:
    async def poll() -> None:
        while sensortask_wozi.webserver is None:
            await asyncio.sleep_ms(20)

    await asyncio.wait_for(poll(), timeout_s)


async def _wait_until_serving(host: str, port: int, timeout_s: float = 10.0) -> None:
    async def poll() -> None:
        while True:
            try:
                await _http_client.fetch(host, port, "GET", "/")
                return
            except OSError:
                await asyncio.sleep_ms(50)

    await asyncio.wait_for(poll(), timeout_s)


async def _hammer_client(host: str, port: int, n_requests: int, client_id: int, results: list) -> None:
    for i in range(n_requests):
        path = _ENDPOINTS[i % len(_ENDPOINTS)]
        try:
            resp = await _http_client.fetch(host, port, "GET", path)
            results.append(("ok", client_id, i, resp.status_code))
        except OSError as e:
            results.append(("err", client_id, i, str(e)))
        except MemoryError as e:  # see module docstring - a real but distinct outcome from the segfault
            results.append(("memory", client_id, i, str(e)))


def _parse_args(argv: "list[str]") -> "dict[str, object]":
    opts: dict[str, object] = {"clients": 8, "requests": 15, "rounds": 1, "host": "127.0.0.1", "port": 8099}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--clients":
            opts["clients"] = int(argv[i + 1])
        elif arg == "--requests":
            opts["requests"] = int(argv[i + 1])
        elif arg == "--rounds":
            opts["rounds"] = int(argv[i + 1])
        elif arg == "--host":
            opts["host"] = argv[i + 1]
        elif arg == "--port":
            opts["port"] = int(argv[i + 1])
        else:
            raise ValueError(f"unknown argument: {arg!r}")
        i += 2
    return opts


async def main(n_clients: int, n_requests: int, n_rounds: int, host: str, port: int) -> None:
    # Must run before anything else in the process registers a poll object - see
    # unix_port_poll_prewarm.py's own module docstring and digital_twin/README.md's "Known gaps"
    # section.
    prewarm_poll_set(port=port + 1000)
    machine.configure_fram_state_path(None)
    machine.configure_scd30_state_path(None)
    main_task = asyncio.get_event_loop().create_task(
        sensortask_wozi.main(cfg_path=_CONFIG_DIR, web_host=host, web_port=port)
    )
    try:
        await _wait_until_built()
        await _wait_until_serving(host, port)
        gc.collect()
        for round_n in range(n_rounds):
            print(f"round {round_n}: firing {n_clients} concurrent clients x {n_requests} requests each")
            results: list = []
            await asyncio.gather(*[_hammer_client(host, port, n_requests, c, results) for c in range(n_clients)])
            ok = sum(1 for r in results if r[0] == "ok")
            err = sum(1 for r in results if r[0] == "err")
            mem = sum(1 for r in results if r[0] == "memory")
            print(f"round {round_n}: completed without crashing - {ok} ok, {err} err, {mem} memory, out of {len(results)}")
    finally:
        main_task.cancel()
        try:
            await main_task
        except (asyncio.CancelledError, Exception):
            pass


if __name__ == "__main__":
    _opts = _parse_args(sys.argv[1:])
    asyncio.run(main(_opts["clients"], _opts["requests"], _opts["rounds"], _opts["host"], _opts["port"]))  # type: ignore[arg-type]
