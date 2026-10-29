"""prims9.py: the UART link's receive line held low or glitched, as a peer power-cycle or a loose cable does: GPIO9's input
forced low through IO_BANK0 INOVER (the pad is never driven) while UART0 sends frames; per phase the driver's intact and
broken frames, overrun count and UARTRSR, the loop lag, and the time to the first intact frame after the line returns."""
import time, asyncio, machine, asy_uart_driver
from machine import Pin, UART, Timer, mem32
CTRL9 = 0x40014004 + 8 * 9
RSR1 = 0x40038004
wdt = machine.WDT(timeout=8000)
mb0, mb1 = machine.mem_backup(0), machine.mem_backup(1)
for i in range(4): mb0[i] = 0
for i in range(3): mb1[i] = 0
def say(*a): print("SUM prims9", *a)
st = {}
def bump(k, n=1): st[k] = st.get(k, 0) + n
BASE = 0; LOWV = 0; tog = 0
def g_short(_):  # one pulse of a few microseconds, about one bit time at 115200
    mem32[CTRL9] = LOWV; mem32[CTRL9] = BASE
def g_long(_):  # a 2 kHz square wave on the input: 250 us low, 250 us high
    global tog
    tog ^= 1; mem32[CTRL9] = LOWV if tog else BASE
async def feeder():
    t0 = time.ticks_ms()
    while True:
        wdt.feed(); mb0[0] = time.ticks_diff(time.ticks_ms(), t0); mb0[1] = st.get("good", 0); mb1[1] = st.get("lag_max", 0)
        await asyncio.sleep_ms(100)
async def lag():
    while True:
        t0 = time.ticks_ms(); await asyncio.sleep_ms(10); d = time.ticks_diff(time.ticks_ms(), t0) - 10
        st["lag_max"] = max(st.get("lag_max", 0), d); bump("lag_over20", d > 20)
async def writer(tx):
    seq = 0; f = bytearray(64)
    while True:
        f[0] = 0xA5; f[1] = seq & 0xFF; f[2] = seq >> 8 & 0xFF
        for k in range(3, 64): f[k] = (seq + k) & 0xFF
        tx.write(f); seq = (seq + 1) & 0xFFFF; bump("sent")
        await asyncio.sleep_ms(8)
async def reader(u):  # holds the session lock for good, as UARTComm does
    await u.session_lock.acquire()
    acc = bytearray()
    while True:
        chunk = await u.read(128, 200)
        if chunk is None: bump("read_none"); continue
        bump("zero_bytes", chunk.count(b"\x00")); acc += chunk
        while len(acc) >= 64:
            if acc[0] != 0xA5:
                acc = acc[1:]; bump("skipped"); continue
            seq = acc[1] | acc[2] << 8
            if all(acc[k] == (seq + k) & 0xFF for k in range(3, 64)):
                bump("good"); acc = acc[64:]
                if "rel" in st and "first_good_ms" not in st: st["first_good_ms"] = time.ticks_diff(time.ticks_ms(), st["rel"])
            else:
                bump("bad"); acc = acc[1:]
async def main():
    global BASE, LOWV
    tx = UART(0, 115200, tx=Pin(0), rx=Pin(1), txbuf=512)
    u = asy_uart_driver.UART(1, 8, 9, baudrate=115200, rxbuf=512, txbuf=512, rx_ring=512)
    say("ring", u._rx_dma is not None or u.setup_rx_ring(), "ctrl9", hex(mem32[CTRL9]))
    BASE = mem32[CTRL9] & ~(3 << 16); LOWV = BASE | 2 << 16
    for f in (feeder(), lag(), writer(tx), reader(u)): asyncio.create_task(f)
    await asyncio.sleep(1)
    for i, (name, kind, ms) in enumerate((("baseline", None, 0), ("low_1ms", "hold", 1), ("low_100ms", "hold", 100),
                                          ("low_10s", "hold", 10000), ("glitch_1bit_1khz", g_short, 1000),
                                          ("glitch_250us_2khz", g_long, 4000))):
        mb1[0] = i + 1; st.clear(); o0 = u.rx_overruns
        await asyncio.sleep(1)
        pre = dict(st); st.clear()
        rsr = -1
        if kind == "hold":
            mem32[CTRL9] = LOWV
            if ms < 10: time.sleep_us(ms * 1000)
            else: await asyncio.sleep_ms(ms)
            rsr = mem32[RSR1] & 0xF; mem32[CTRL9] = BASE
        elif kind is not None:
            t = Timer(mode=Timer.PERIODIC, freq=ms, callback=kind, hard=True)
            await asyncio.sleep_ms(2000)
            t.deinit(); rsr = mem32[RSR1] & 0xF; mem32[CTRL9] = BASE
        st["rel"] = time.ticks_ms()
        await asyncio.sleep(2)
        st.pop("rel"); st["overruns"] = u.rx_overruns - o0; st["rsr_at_release"] = rsr
        say(name, "pre", sorted(pre.items()), "fault_and_after", sorted(st.items()))
    mem32[CTRL9] = BASE
asyncio.run(main())
print("DONE")
