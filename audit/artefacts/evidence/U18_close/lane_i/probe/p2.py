import asyncio, os
import asy_ntp_client as ntpmod
from asy_ntp_client import NTPClient, NtpTiming
from asy_wifi_service import WifiConfig, WifiService
import network
d = "tests/_tmp/probe_p2/"
try:
    os.mkdir("tests/_tmp")
except OSError:
    pass
try:
    os.mkdir(d)
except OSError:
    pass
conn = WifiService(WifiConfig("SensorNode", "12345678", 5, 5), cfg_path=d)
asyncio.run(conn.setup())
conn._wlan._connected = True
conn._wlan._status = network.STAT_GOT_IP
conn._wlan._ifconfig = ("10.0.0.5", "255.255.255.0", "10.0.0.1", "192.0.2.53")
with open(d + "config_NTP.cfg", "w") as f:
    f.write('{"NTPHost": "2", "NTPOffset": 0, "NTPInterval": 12, "GMTOffset": 0, "DSTOffset": 0}')
ntp = NTPClient(conn.get_wifi_mode_lock(), conn.network_available_locked, conn.get_dns_server_ip, NtpTiming(500, 1, 2000, 10, 600), cfg_path=d)
asyncio.run(ntp.setup())
calls = []
real = ntpmod.resolve_ipv4
async def rec(host, servers=(), **kw):
    calls.append((host, servers))
    return await real(host, servers, **kw)
ntpmod.resolve_ipv4 = rec
print(asyncio.run(ntp._get_ntp_config()))
async def sc():
    conn._dhcp_dns = "192.0.2.53"
    t = asyncio.create_task(ntp._sync_loop())
    ntp._ntp_sync_trigger_event.set()
    await asyncio.sleep(0); await asyncio.sleep(0)
    print("locked", conn.wifi_mode_lock.locked())
    await asyncio.sleep(3)
    t.cancel()
asyncio.run(sc())
print(calls)
print(asyncio.run(ntp.get_error_counter()))
