# B4 + B5 merge notes (lead, 2026-11-03)

Trial at int a6047339 with B4 963d0de1 and B5 21e12c76 (`git merge-tree`, `trial_merge_b4b5.out`): each merges into
int cleanly alone; together the one conflict is SPECIFICATION.md's teardown-returns-`bool` sentence (C.13 list).
B4 drops `I2C.deinit()`/`SPI.deinit()` from the list (they answer nothing); B5 rewords the `UDPSocket.disconnect()`
clause. Combined: "`UDPSocket.disconnect()` (the captive DNS checks it and persists a failure, `SOCKET_TEARDOWN`;
the resolver and the NTP fetch call it unchecked), `UART.deinit()` (C.13); one on a class". Re-run the trial after
both units' fix rounds; the catalog, codegen and definitions auto-merged here.
