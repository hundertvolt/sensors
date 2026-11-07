import test_digital_twin_uart_link as t
import machine
t.build_linked_system()
dev = t.sensortask_dev
f = dev.fram
print("MGR init", f.initialized, type(f).__name__)
for k in dir(f):
    if not k.startswith("__"):
        v = getattr(f, k)
        if isinstance(v, (int, bool, str)): print("  ", k, v)
chip = machine._current_fram_chip
print("CHIP", chip.size, bytes(chip.rdid_response))
