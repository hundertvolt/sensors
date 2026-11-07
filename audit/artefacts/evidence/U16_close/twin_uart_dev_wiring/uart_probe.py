import test_digital_twin_uart_link as t
t.build_linked_system()
dev = t.sensortask_dev
i, r = dev.uart_link_init._comm, dev.uart_link_resp._comm
for comm in (i, r):
    print("PRE", comm.name, t.run(comm.get_error_counter())[comm.name], list(comm.pr.history) if hasattr(comm.pr, "history") else None)
ans = t.run(t.exchange(i.uart_get(0x01)))
print("ans", ans)
for comm in (i, r):
    print("POST", comm.name, t.run(comm.get_error_counter())[comm.name], list(comm.pr.history) if hasattr(comm.pr, "history") else None)
print("fram pr", t.run(dev.fram.get_error_counter()))
