from collections import namedtuple
N = namedtuple("N", ("A", "B", "TS"))
n = N(1, 2, 3)
print(hasattr(n, "_asdict"), hasattr(N, "_fields"), hasattr(n, "_replace"))
try:
    print(n._asdict())
except Exception as e:
    print("err", e)
