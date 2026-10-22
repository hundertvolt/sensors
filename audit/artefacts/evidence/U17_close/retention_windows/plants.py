# Plants one retained object per operation and runs the three retention tests; each must fail.
import sys
kind = sys.argv[1]
kept = []
if kind == "piece":
    import asy_base_classes
    orig = asy_base_classes.PieceBuffer.write_at
    def leaky(self, offset, src):
        kept.append(bytearray(1))
        return orig(self, offset, src)
    asy_base_classes.PieceBuffer.write_at = leaky
    import test_asy_base_classes as t
    fn = t.test_piecebuffer_retains_nothing_after_construction
else:
    import asy_uart_comm
    if kind == "refuse":
        orig = asy_uart_comm.UARTComm._accept_set
        async def leaky(self, *a):
            kept.append(bytearray(1))
            return await orig(self, *a)
        asy_uart_comm.UARTComm._accept_set = leaky
        import test_asy_uart_comm as t
        fn = t.test_a_declared_size_over_max_transfer_bytes_is_refused_before_any_allocation
    else:
        orig = asy_uart_comm.UARTComm.uart_set
        async def leaky(self, *a, **k):
            kept.append(bytearray(1))
            return await orig(self, *a, **k)
        asy_uart_comm.UARTComm.uart_set = leaky
        orig_get = asy_uart_comm.UARTComm.uart_get
        async def leaky_get(self, *a, **k):
            kept.append(bytearray(1))
            return await orig_get(self, *a, **k)
        asy_uart_comm.UARTComm.uart_get = leaky_get
        import test_asy_uart_comm as t
        fn = t.test_repeated_maximum_size_and_over_cap_trains_keep_the_heap_flat
try:
    fn()
    print(kind, "PLANT NOT CAUGHT")
except AssertionError as e:
    print(kind, "plant caught:", e)
