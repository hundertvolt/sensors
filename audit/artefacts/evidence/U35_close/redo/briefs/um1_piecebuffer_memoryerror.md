# UM1: PieceBuffer's callers and a MemoryError (lead, 2026-10-27; research, no product change)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then point 2 of `S/u35r/handbacks_redo/BR1b.md`. Worktree and branch: in your launch message. Logs in `S/u35/laneB/um1/`.
CLAUDE.md's UART hard rules apply (two-implementation contract, UART_C_PORT_CHANGELOG classes). Never read `arduino/`.

## The question
SPECIFICATION.md G.2 says of `PieceBuffer` (src/asy_base_classes.py) "a MemoryError there is not caught". No caller
catches it either: asy_uart_comm.py :278, :313, :1111 and asy_uart_driver.py :660 (re-locate them on your head), and
any other caller you find (the webserver's included). Yet I.4(a) (owner, 2026-09-25) says a function with a true
alternative flow catches, and each of these has one (None, or `ListenResult(None, ...)`). Establish the facts that
let the owner decide. CHECKLIST 1c: change no product file; this goes to the owner.

## Items
1. Provenance: the G.2 sentence's origin (`git log -S`, its decision tag) and I.4(a)'s exact text. Is "not caught" a
   recorded decision, or a description of the code as it was?
2. Reachability: under the zero-MemoryError design, can a piece allocation fail at all (piece bound, the heap after
   boot, fragmentation over a run)? Numbers from SPECIFICATION.md I.6 and the existing measurements, not new runs.
3. Per caller, both ways, with lines:
   - today: where the MemoryError ends (which task top, the supervisor's restart, what is logged and persisted);
   - caught: what the alternative flow does next.
   For each, what the peer sees on the wire: bytes, ACK/NACK, timing, recovery. A difference the peer can see is
   Class A (CLAUDE.md); one it cannot is Class B.
4. If the twin or a unit test can inject the failure (a PieceBuffer whose allocation raises), write that injection
   as a test and record what it shows today, at both stages. Commit the test only if it passes on today's code and
   pins today's behaviour; a red-first test for a fix waits for the owner's answer.
5. Options with consequences (leave, catch at some callers, catch at all), and a recommendation.

## Hand-back (the file, per redo_common)
The facts per item with lines; the options and the recommendation in prose; any commit; last line
"nothing of mine is running".
