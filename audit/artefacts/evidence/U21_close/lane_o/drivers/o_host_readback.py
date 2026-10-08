# lane O: the host readback alone, against u21tc-o's current build-lwip.
import sys
from pathlib import Path
wt, tc = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(wt / "toolchain"))
import setup_toolchain as st
import micropython_overrides as mo
mp = tc / "micropython"; b = mp / "ports" / "unix" / "build-lwip"
try:
    mo.verify_unix_lwip_host_in_build(b, mp, b / "micropython", env=st.build_env()); print("host readback PASS")
except mo.OverrideError as e:
    print("host readback FAIL:", e); sys.exit(1)
