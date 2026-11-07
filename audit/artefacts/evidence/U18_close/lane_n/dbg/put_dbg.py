import test_asy_ntp_client as t
c = t.make_client()
print(t._put(c, {"NTPHost": "pool.ntp.org"}))
print(t._put(c, {"NTPHost": "192.168.1.1"}))
print(t._put(c, {"NTPHost": "pool.ntp.org"}))
