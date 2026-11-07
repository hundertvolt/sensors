# Mutation check: with the reader buffering until EOF, the streaming test's command must time out.
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import setup_toolchain as st

def buffered(stream, lines, secrets):
    data = stream.read()
    lines.append(data)
    print(st._redact(data, secrets), end="", flush=True)

st._stream_output = buffered
flag = Path(sys.argv[2])
started = time.monotonic()
try:
    st.run(["sh", "-c", 'echo first; while [ ! -e "$1" ]; do sleep 0.05; done; echo second', "sh", str(flag)], timeout_s=2)
except st.SetupError as e:
    print("MUTANT CAUGHT:", e, f"after {time.monotonic() - started:.1f}s")
else:
    print("MUTANT SURVIVED")
