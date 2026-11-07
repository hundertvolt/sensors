# Runs test_a_read_retains_nothing alone N times in one process and prints each failure's figures.
import test_asy_uart_driver as t
n = 20
bad = 0
for i in range(n):
    try:
        t.test_a_read_retains_nothing()
    except AssertionError as e:
        bad += 1
        print("run", i, "FAIL", e)
print("done", n, "bad", bad)
