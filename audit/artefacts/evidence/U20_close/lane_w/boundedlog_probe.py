import sys
sys.path.insert(0, "digital_twin")
import machine
log = machine._BoundedLog(4)
for i in range(3):
    log.append(i)
assert list(log) == [0, 1, 2] and log == [0, 1, 2] and log[1:] == [1, 2], list(log)
for i in range(3, 10):
    log.append(i)
assert list(log) == [6, 7, 8, 9], list(log)
assert log == [6, 7, 8, 9] and log[0] == 6 and log[-1] == 9 and log[1:3] == [7, 8] and log.dropped == 6
assert log._items == [8, 9, 6, 7]  # storage untouched by a read: _ordered() returns a fresh list
print("BOUNDEDLOG ORDER OK")
