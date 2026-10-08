import errno
class _HeadRefused(OSError):
    pass
e = _HeadRefused(32)
print(e.errno, e.args, isinstance(e, OSError), e.errno in [32, 54])
try:
    b"\xff\xfeabc".decode()
except UnicodeError as u:
    print("unicode", type(u))
print("12".isdigit(), "1a".isdigit(), "".isdigit())
print(b"abc".find(b"\n"))
import sys
print(sys.implementation)
