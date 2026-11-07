# U8C: a stalled UART responder passed silently

**Finding (class 4, test harness, every mode that runs a listener).** `tests/_uart_comm_harness.py`'s
`with_listener()` and the copy in `tests/test_asy_uart_link_driver.py` waited `LISTENER_DRAIN_S` for the responder's
listener, then cancelled it and dropped the `TimeoutError`. A responder that never finished its rounds therefore
passed the exchange: evidence of a wedged responder was lost.

**Fix (U8C lead).** Both now go through `awaited_with_listener()`: a listener that does not finish within
`LISTENER_DRAIN_S` is cancelled and the exchange fails with "the responder's listener did not finish its N round(s)".
A test whose scenario stalls the responder on purpose says so with `listener_may_stall=True`.

## Files

| file | what it shows |
|---|---|
| `harness_fix.diff` | the harness and link-driver change |
| `new_tests_against_old_harness.log` | the U8C test file against the pre-fix harness: the planted `test_a_responder_that_never_finishes_its_rounds_fails_the_exchange` fails with "a stalled responder was cancelled silently" (the old harness swallowed the stall); the other five fail only on the new keyword the old harness lacks |
| `strict_harness_before_stall_declarations.log` | the fixed harness before the opt-out existed: 145/149, the four tests whose scenario stalls the responder on purpose (negative expected size refused, out-of-range command id refused, a write failing at each point, a write that never reaches the peer); each now declares the stall |

After the declarations: `test_asy_uart_comm` 149/149, `test_asy_uart_link_driver` 20/20, `test_uart_comm_hazard`
98/98. No test relied on the swallow except these four, all of which stall the responder by design.
