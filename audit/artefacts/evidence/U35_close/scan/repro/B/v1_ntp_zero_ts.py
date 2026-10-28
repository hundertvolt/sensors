# V1: the pre-audit NTP reply parser fed one 48-byte reply: LI 0, VN 4, mode 4, stratum 2, transmit timestamp 0.
import asyncio
import asy_ntp_client as m
from machine import RTC

class _Pr:
    def all(self, *a): print("pr.all", *a)
    def one(self, *a): print("pr.one", *a)

class _Self:
    pr = _Pr()
    async def _episode_log(self, code, *args, warn=False):
        print("logged", code, args)

msg = bytearray(48)
msg[0] = (0 << 6) | (4 << 3) | 4  # LI 0, VN 4, mode 4 (server)
msg[1] = 2  # stratum 2: not Kiss-o'-Death
async def main():
    tm = await m.AsyNtpClient._parse_ntp_reply(_Self(), bytes(msg), 0)
    print("returned", tm)
    print("RTC now", RTC().datetime())
asyncio.run(main())
