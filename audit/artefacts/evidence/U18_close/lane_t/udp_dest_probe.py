# Scratch probe (not committed): which UDP destinations a twin boot with a configured SSID reaches.
import sys

sys.path.insert(0, "ext")
sys.path.insert(0, "digital_twin")
sys.path.insert(0, "digital_twin/unixport")
import asyncio
import json

from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from unix_port_poll_prewarm import prewarm_poll_set

prewarm_poll_set()
patch_asy_udp_socket_for_unix_port()
import asy_udp_socket
import machine

_patched_connect = asy_udp_socket.UDPSocket._connect


async def _probe(self):
    print("UDP_CONNECT", self._mode, self._addr)
    await _patched_connect(self)


asy_udp_socket.UDPSocket._connect = _probe
CFG = sys.argv[1]
WINDOW_S = float(sys.argv[2])


async def go():
    with open("build/generated_src/sensortask_wozi_wiring_plan.json") as f:
        machine.configure_wiring(json.load(f))
    module = __import__("sensortask_wozi")
    await module.build_system(cfg_path=CFG, web_host="127.0.0.1", web_port=19991)
    ok, _ = await module.conn.cfgmgr.write_config({"SSID": "TestNet"})
    print("SSID written", ok)
    await module.sysfunct.start_timers(module._collect_trigger_starters(), module._collect_timer_starters())
    tasks = [s() for s in module._collect_task_starters()]
    await asyncio.sleep(WINDOW_S)
    print("synced", await module.ntp.ntp_issynced())
    for t in tasks:
        t.cancel()
    sys.exit(0)


asyncio.run(go())
