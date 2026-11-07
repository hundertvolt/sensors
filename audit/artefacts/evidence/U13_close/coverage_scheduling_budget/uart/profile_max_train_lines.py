# Call-count profile of the max-length train under build-settrace: counts 'call' events per function
# while the initiator is at chunks [A, B) (a slow window) and [C, D) (a quiet window of equal length).
# Run directly (not under _coverage_runner): micropython profile_max_train.py A B C D
import sys
import time
A, B, C, E = (int(x) for x in sys.argv[1:5])
TEST = "tests/test_digital_twin_uart_link.py"
ns = {"__name__": "not_main", "__file__": TEST}
exec(compile(open(TEST).read(), TEST, "exec"), ns)
import asy_uart_comm
chunk = [0]
counts = {"slow": {}, "quiet": {}}
times = {"slow": [None, None], "quiet": [None, None]}
def window():
    c = chunk[0]
    if A <= c < B:
        return "slow"
    if C <= c < E:
        return "quiet"
    return None
def ltrace(frame, event, arg):
    if event == "line":
        w = window()
        if w is not None:
            key = "L " + frame.f_code.co_filename + ":" + frame.f_code.co_name
            d = counts[w]
            d[key] = d.get(key, 0) + 1
    return ltrace
def gtrace(frame, event, arg):
    if event == "call":
        w = window()
        if w is not None:
            key = frame.f_code.co_filename + ":" + frame.f_code.co_name
            d = counts[w]
            d[key] = d.get(key, 0) + 1
        if frame.f_code.co_filename.startswith(("src/", "digital_twin/")):
            return ltrace
    return None
orig_wfa = asy_uart_comm.UARTComm._write_frame_with_ack
async def wfa(self, device, cmd, chunks, cur_chunk, data, size):
    w0 = window()
    chunk[0] = cur_chunk
    w = window()
    if w != w0:
        if w0 is not None:
            times[w0][1] = time.ticks_ms()
        if w is not None:
            times[w][0] = time.ticks_ms()
    return await orig_wfa(self, device, cmd, chunks, cur_chunk, data, size)
asy_uart_comm.UARTComm._write_frame_with_ack = wfa
sys.settrace(gtrace)
try:
    ns["test_a_maximum_length_train_completes_and_still_yields"]()
    print("PASS")
except AssertionError as e:
    print("FAIL", e)
sys.settrace(None)
for w in ("slow", "quiet"):
    t = times[w]
    tot = sum(counts[w].values())
    print("==", w, "window ms", None if None in t else time.ticks_diff(t[1], t[0]), "total calls", tot)
    for k, v in sorted(counts[w].items(), key=lambda kv: -kv[1])[:25]:
        print("   ", v, k)
