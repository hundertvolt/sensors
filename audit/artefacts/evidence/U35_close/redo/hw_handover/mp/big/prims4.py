"""prims4.py: the firmware's concurrent DMA/IRQ users at once, quiet and then under a host UDP flood: the UART driver's
512-byte ring on UART1 fed from UART0, 1 KB FRAM reads over SPI DMA, a UDP echo over CYW43, a 10 ms loop-lag probe."""
import gc, json, os, time, select, socket, network, asyncio, machine, asy_uart_driver
from machine import Pin, SPI, UART
wdt = machine.WDT(timeout=8000)
def say(*a): print("SUM prims4", *a)
def creds():
    for name in os.listdir("/"):
        if name.startswith("config_") and name.endswith(".cfg"):
            try:
                with open("/" + name) as f: d = json.load(f)
            except (OSError, ValueError): continue
            if isinstance(d, dict) and d.get("SSID") and "PW" in d: return d["SSID"], d["PW"]
    return None
cs = Pin(5, Pin.OUT, value=1)
spi = SPI(0, baudrate=1000000, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
def rd(n, addr=0):
    b = bytearray(n); cs(0); spi.write(bytes((0x03, addr >> 16 & 0xFF, addr >> 8 & 0xFF, addr & 0xFF))); spi.readinto(b); cs(1); return b
ref = bytearray()
for a in range(0, 1024, 16): ref += rd(16, a)
spi.init(baudrate=8000000)
st = {}
def bump(k, n=1): st[k] = st.get(k, 0) + n
async def feeder():
    while True: wdt.feed(); await asyncio.sleep_ms(500)
async def lag():
    while True:
        t0 = time.ticks_ms(); await asyncio.sleep_ms(10); d = time.ticks_diff(time.ticks_ms(), t0) - 10
        st["lag_max"] = max(st.get("lag_max", 0), d); bump("lag_n"); bump("lag_over20", d > 20); bump("lag_over44", d > 44)
async def fram():
    b = bytearray(1024)
    while True:
        try:
            cs(0); spi.write(b"\x03\x00\x00\x00"); spi.readinto(b); cs(1)
            bump("fram_reads"); bump("fram_bad", b != ref)
        except OSError:
            cs(1); bump("fram_oserror")
        await asyncio.sleep_ms(5)
async def writer(tx):
    seq = 0; f = bytearray(64)
    while True:
        f[0] = 0xA5; f[1] = seq & 0xFF; f[2] = seq >> 8 & 0xFF
        for k in range(3, 64): f[k] = (seq + k) & 0xFF
        tx.write(f); seq = (seq + 1) & 0xFFFF; bump("uart_sent")
        await asyncio.sleep_ms(8)
async def reader(u):
    acc = bytearray(); last = -1
    while True:
        chunk = await u.read(128, 200)
        if chunk is None: bump("uart_read_none"); continue
        acc += chunk
        while len(acc) >= 64:
            if acc[0] != 0xA5:
                acc = acc[1:]; bump("uart_skipped"); continue
            seq = acc[1] | acc[2] << 8
            if all(acc[k] == (seq + k) & 0xFF for k in range(3, 64)):
                bump("uart_good"); bump("uart_seq_gap", last >= 0 and seq != (last + 1) & 0xFFFF); last = seq; acc = acc[64:]
            else:
                bump("uart_bad"); acc = acc[1:]
async def echo(s):
    p = select.poll(); p.register(s, select.POLLIN)
    while True:
        if p.poll(0):
            try:
                data, addr = s.recvfrom(512); bump("udp_rx")
                try: s.sendto(data, addr); bump("udp_tx")
                except OSError as e: bump("udp_tx_err%d" % e.args[0])
            except OSError as e:
                bump("udp_rx_err%d" % e.args[0])
            continue
        await asyncio.sleep_ms(2)
async def main():
    c = creds(); wlan = network.WLAN(network.STA_IF); wlan.active(True)
    if c: wlan.connect(c[0], c[1])
    for _ in range(150):
        if wlan.isconnected(): break
        wdt.feed(); await asyncio.sleep_ms(100)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 5005)); s.setblocking(False)
    tx = UART(0, 115200, tx=Pin(0), rx=Pin(1), txbuf=512)
    u = asy_uart_driver.UART(1, 8, 9, baudrate=115200, rxbuf=512, txbuf=512, rx_ring=512)
    say("ring", u._rx_dma is not None or u.setup_rx_ring(), "connected", wlan.isconnected())
    for f in (feeder(), lag(), fram(), writer(tx), reader(u), echo(s)): asyncio.create_task(f)
    for phase in ("quiet", "flood"):
        st.clear(); o0 = u.rx_overruns; gc.collect(); m0 = gc.mem_free()
        if phase == "flood": print("FLOOD_START IP=%s" % wlan.ifconfig()[0])
        await asyncio.sleep(45)
        st["uart_overruns"] = u.rx_overruns - o0; st["mem_free_end"] = gc.mem_free(); st["mem_free_start"] = m0
        say(phase, sorted(st.items()))
    # the UDP pcb pool with the hotspot's AP interface up beside the station (its DHCP server takes one more)
    s.close(); ap = network.WLAN(network.AP_IF); ap.config(ssid="bench-probe", key="probe-1234567"); ap.active(True)
    await asyncio.sleep_ms(1500); socks = []
    try:
        while len(socks) < 12: socks.append(socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
        stop = "none"
    except OSError as e: stop = repr(e)
    say("udp_pcbs_with_ap_and_sta opened", len(socks), "stopped_by", stop)
    for x in socks: x.close()
    ap.active(False)
asyncio.run(main())
print("DONE")
