# After a soft reset: every DMA channel's state, which channel a fresh claim gets, and whether a channel left running
# by the last program still consumes UART1's receive stream (writing into memory the new heap now owns).
import machine, time, rp2
B = 0x50000000
def st(ch):
    c = machine.mem32[B + 0x40 * ch + 0x0C]
    return (c >> 24) & 1, c & 1, (c >> 15) & 0x3F, machine.mem32[B + 0x40 * ch + 0x08]
live = [(ch,) + st(ch) for ch in range(12) if st(ch)[0] or st(ch)[1]]
print("SUM dma_soft channels_busy_or_enabled (ch, busy, en, treq, count):", live)
d = rp2.DMA(); print("SUM dma_soft fresh_claim_gets_channel", d.channel); d.close()
if live:
    u1 = machine.UART(1, 115200, tx=machine.Pin(8), rx=machine.Pin(9)); u0 = machine.UART(0, 115200, tx=machine.Pin(0), rx=machine.Pin(1))
    machine.mem32[0x40038048] |= 1  # UART1 DMACR.RXDMAE, as the driver sets it: the old channel's DREQ is live again
    before = [st(ch[0])[3] for ch in live]
    u0.write(bytes(range(64))); time.sleep_ms(20)
    after = [st(ch[0])[3] for ch in live]
    print("SUM dma_soft old_channel_counts_before", before, "after_64_bytes", after, "uart1_any", u1.any())
print("DONE")
