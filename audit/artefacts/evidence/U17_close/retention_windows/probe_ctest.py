import test_asy_uart_comm as t
bad = []
for k in range(6):
    try:
        t.test_repeated_maximum_size_and_over_cap_trains_keep_the_heap_flat()
        bad.append("ok")
    except AssertionError as e:
        bad.append(str(e))
print(bad)
