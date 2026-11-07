import asyncio
import sys
sys.path.insert(0, "digital_twin")
import asy_dns_client
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port
from _udp_port_redirect import redirect_udp_port
from asy_udp_socket import UDPSocket
patch_asy_udp_socket_for_unix_port()


def test_redirect_maps_only_the_real_port_and_restores():
    original = asy_dns_client.UDPSocket
    with redirect_udp_port(asy_dns_client, 53, 23999) as redirect:
        cls = asy_dns_client.UDPSocket
        assert cls is not original
        a = cls(("127.0.0.1", 53), mode="client")
        b = cls(("127.0.0.1", 54))
        assert isinstance(a, UDPSocket)
        assert a._addr == ("127.0.0.1", 23999), a._addr
        assert b._addr == ("127.0.0.1", 54)
        try:
            cls(b"\x00" * 16)
            raise AssertionError("no TypeError")
        except TypeError:
            pass
        assert redirect.constructed == 3
    assert asy_dns_client.UDPSocket is original


def test_redirect_restores_on_exception():
    original = asy_dns_client.UDPSocket
    try:
        with redirect_udp_port(asy_dns_client, 53, 23998):
            raise ValueError("x")
    except ValueError:
        pass
    assert asy_dns_client.UDPSocket is original


def test_redirected_round_trip():
    async def go():
        server = UDPSocket(("127.0.0.1", 23997), mode="server")
        await server._connect()
        with redirect_udp_port(asy_dns_client, 53, 23997):
            cli = asy_dns_client.UDPSocket(("127.0.0.1", 53))
        n = await cli.write(b"ping")
        data, addr = await server.recvfrom(64, timeout_ms=500)
        await cli.disconnect(); await server.disconnect()
        return n, data, addr
    n, data, addr = asyncio.run(go())
    assert n == 4 and data == b"ping", (n, data)
    assert isinstance(addr, tuple) and addr[0] == "127.0.0.1", addr

if __name__ == "__main__":
    import microtest
    microtest.run(globals())
