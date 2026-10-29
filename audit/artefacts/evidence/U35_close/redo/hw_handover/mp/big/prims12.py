"""prims12.py: real flash writes (owner, 2026-10-29: "Try that flash write test once") beside the UART ring, FRAM and Wi-Fi:
one scratch file written like a config save, three rounds, then removed. A DMA-paced back-to-back UART0 stream keeps sending
while interrupts are off; a 5 kHz hard Timer times every interrupts-off window; the host echoes UDP every 10 ms."""
import gc, json, os, time, select, socket, network, asyncio, machine, rp2, asy_uart_driver
from array import array
from machine import Pin, SPI, UART, Timer, mem32
PROBE = "/u35_flashprobe.json"
UART0_DR, UART0_DMACR, DREQ_UART0_TX = 0x40034000, 0x40034048, 20
wdt = machine.WDT(timeout=8000)
mb0, mb1 = machine.mem_backup(0), machine.mem_backup(1)
for i in range(4): mb0[i] = 0
for i in range(3): mb1[i] = 0
def say(*a): print("SUM prims12", *a)
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
gp = array("i", (0, 0, 0))  # last tick us, longest gap us, gaps over 2 ms
win = array("i", range(24))
def tick(_):  # hard IRQ: no allocation; a gap is a stretch with interrupts held off (or the ISR itself delayed)
    n = time.ticks_us(); d = time.ticks_diff(n, gp[0]); gp[0] = n
    if d > gp[1]: gp[1] = d
    if d > 2000:
        if gp[2] < 24: win[gp[2]] = d
        gp[2] += 1
def gaps_reset():
    gp[1] = 0; gp[2] = 0
def gaps():
    return gp[1], [win[i] for i in range(min(gp[2], 24))], gp[2]
async def feeder():
    t0 = time.ticks_ms()
    while True:
        wdt.feed(); mb0[0] = time.ticks_diff(time.ticks_ms(), t0) // 100; mb0[1] = st.get("uart_good", 0); mb0[2] = st.get("udp_rx", 0)
        mb0[3] = gp[1]; mb1[1] = st.get("lag_max", 0)
        await asyncio.sleep_ms(100)
async def lag():
    while True:
        t0 = time.ticks_ms(); await asyncio.sleep_ms(10); d = time.ticks_diff(time.ticks_ms(), t0) - 10
        st["lag_max"] = max(st.get("lag_max", 0), d); bump("lag_over20", d > 20)
async def fram():
    b = bytearray(1024)
    while True:
        try:
            cs(0); spi.write(b"\x03\x00\x00\x00"); spi.readinto(b); cs(1)
            bump("fram_reads"); bump("fram_bad", b != ref)
        except OSError:
            cs(1); bump("fram_oserror")
        await asyncio.sleep_ms(5)
async def reader(u):  # holds the session lock for good, as UARTComm does
    await u.session_lock.acquire()
    acc = bytearray(); last = -1
    while True:
        chunk = await u.read(128, 200)
        if chunk is None: continue
        acc += chunk
        while len(acc) >= 64:
            if acc[0] != 0xA5:
                acc = acc[1:]; bump("uart_skipped"); continue
            seq = acc[1] | acc[2] << 8
            if all(acc[k] == (seq + k) & 0xFF for k in range(3, 64)):
                bump("uart_good"); bump("uart_seq_gap", last >= 0 and seq != 0 and seq != last + 1); last = seq; acc = acc[64:]
            else:
                bump("uart_bad"); acc = acc[1:]
async def echo(s):
    p = select.poll(); p.register(s, select.POLLIN)
    while True:
        if p.poll(0):
            try:
                data, addr = s.recvfrom(64); bump("udp_rx"); s.sendto(data, addr)
            except OSError as e:
                bump("udp_err%d" % e.args[0])
            continue
        await asyncio.sleep_ms(2)
def flash_write(i):  # the shape of a config save: one json.dump() straight into the file, no temporary file
    d = {"Name": "u35probe", "round": i, "vals": [1.5 * i, 2.5, 3.5], "pad": "p" * 640}
    t = time.ticks_us()
    with open(PROBE, "w") as f: json.dump(d, f)
    return time.ticks_diff(time.ticks_us(), t)
async def main():
    sizes = [(n, os.stat("/" + n)[6]) for n in os.listdir("/") if n.endswith(".cfg")]
    say("config_file_sizes", sorted(s for _, s in sizes), "probe_exists_before", PROBE[1:] in os.listdir("/"))
    c = creds(); wlan = network.WLAN(network.STA_IF); wlan.active(True); wlan.connect(c[0], c[1])
    for _ in range(150):
        if wlan.isconnected(): break
        wdt.feed(); await asyncio.sleep_ms(100)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 5006)); s.setblocking(False)
    UART(0, 115200, tx=Pin(0), rx=Pin(1), txbuf=512)
    u = asy_uart_driver.UART(1, 8, 9, baudrate=115200, rxbuf=512, txbuf=512, rx_ring=512)
    say("ring", u._rx_dma is not None or u.setup_rx_ring())
    stream = bytearray(256 * 64)
    for q in range(256):
        o = q * 64; stream[o] = 0xA5; stream[o + 1] = q; stream[o + 2] = 0
        for k in range(3, 64): stream[o + k] = (q + k) & 0xFF
    mem32[UART0_DMACR] = mem32[UART0_DMACR] | 0x02  # TXDMAE: UART0 TX paced by DMA, independent of the CPU
    tx = rp2.DMA()
    ctrl = tx.pack_ctrl(size=0, inc_read=True, inc_write=False, treq_sel=DREQ_UART0_TX)
    gp[0] = time.ticks_us(); tim = Timer(mode=Timer.PERIODIC, freq=5000, callback=tick, hard=True)
    for f in (feeder(), lag(), fram(), reader(u), echo(s)): asyncio.create_task(f)
    print("READY IP=%s" % wlan.ifconfig()[0])
    await asyncio.sleep(4)
    try:
        for i, name in enumerate(("baseline", "write1", "write2", "write3")):
            mb1[0] = i + 1; st.clear(); o0 = u.rx_overruns; gaps_reset()
            tx.config(read=stream, write=UART0_DR, count=len(stream), ctrl=ctrl, trigger=True)
            await asyncio.sleep_ms(300)
            print("MARK %s %d" % (name, time.ticks_ms()))
            dt = flash_write(i) if i else 0
            while tx.active(): await asyncio.sleep_ms(20)
            await asyncio.sleep_ms(300)
            g = gaps(); st["uart_overruns"] = u.rx_overruns - o0
            say(name, "write_us", dt, "irqoff_max_us", g[0], "irqoff_over2ms", g[2], "windows_us", g[1], sorted(st.items()))
            await asyncio.sleep(3)
    finally:
        tx.close(); mem32[UART0_DMACR] = mem32[UART0_DMACR] & ~0x02; gaps_reset()
        t = time.ticks_us()
        try: os.remove(PROBE)
        except OSError as e: say("remove_failed", e)
        dt = time.ticks_diff(time.ticks_us(), t); await asyncio.sleep_ms(50); tim.deinit(); g = gaps()
        say("remove_us", dt, "irqoff_max_us", g[0], "windows_us", g[1], "probe_exists_after", PROBE[1:] in os.listdir("/"))
    gc.collect(); say("mem_free", gc.mem_free())
asyncio.run(main())
print("DONE")
