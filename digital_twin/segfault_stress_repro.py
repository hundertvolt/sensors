"""Manual, deliberately-aggressive concurrency stress tool for BACKLOG.md open question #7: a real
MicroPython Unix-port interpreter segfault under heavy concurrent connection load, first found
while investigating a real ECONNRESET report (see FINAL_WIRING_PLAN.md's Step 5 session notes).
8 concurrent clients x 15 requests each (well beyond WebserverService's own max_connections=3
ceiling) reproduced a real interpreter segfault twice in a row in that session, confirmed via
`dmesg` - not a catchable Python-level exception, since it crashes the whole process
unconditionally. `digital_twin/run_wozi_integration.py`'s own `_soak()` is deliberately
strictly-sequential (see its own comment) and can never generate this on its own; this is a
separate, manual tool for deliberately trying to.

**Step 6 session note**: repeated attempts against this exact configuration (and several escalated
variants - mixed real endpoints instead of just `/`, up to 20 clients x 30 requests, 5 sustained
rounds of 12 clients x 20 requests = 1200 requests total) did not reproduce the segfault in this
session's own sandbox, despite genuine, repeated effort - the same "could not reproduce here despite
trying" outcome FINAL_WIRING_PLAN.md's Step 5 session already recorded for the original ECONNRESET
report itself. This does not mean the segfault isn't real: it was confirmed directly via `dmesg` in
a prior session, twice in a row, which this session has no reason to doubt. Plausible explanations
for the non-reproduction, none confirmed: sandbox/build environment differences (a different glibc
malloc implementation could have different sensitivity to whatever heap-corruption pattern is
actually happening), process/thread scheduling timing differences, or the trigger condition being
narrower than "N clients x M requests" alone captures. Owner-directed scope for this category was
"repro + document only, no gdb/backtrace work" - consistent with that, this tool is kept as a
permanent, reusable artifact for whoever picks this up next (real rp2 hardware access, a different
sandbox, or deeper C-level tooling might all change the odds), not chased further at the C level
here.

Usage:
    MICROPYPATH="src:digital_twin:ext:frozen_modules:.frozen" <micropython-unix-port-binary> \\
        digital_twin/segfault_stress_repro.py [--clients N] [--requests N] [--rounds N] [--host H] [--port P]

Exit code / crash behavior: a genuine segfault kills the whole interpreter process outright (no
Python-level traceback, no exit code this script controls) - that IS the positive repro, observable
via the calling shell's own exit status ($? reflecting the fatal signal) or `dmesg`. A MemoryError
is a real but different, catchable outcome this tool has also observed at higher concurrency
(client and server share one process/heap in this diagnostic setup, unlike a real deployment where
they're separate machines) - reported distinctly, not confused with the segfault it's hunting for.
"""

import asyncio
import gc
import sys

import _http_client
import machine

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
