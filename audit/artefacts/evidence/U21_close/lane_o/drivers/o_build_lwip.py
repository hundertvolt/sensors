# lane O: rebuild only the host lwIP flavour on the private toolchain, through the installer's own path.
import sys
from pathlib import Path
wt, tc = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(wt / "toolchain"))
import setup_toolchain as st
binary = st.build_unix_lwip_port(tc / "micropython", tc, 2)
print("build_unix_lwip_port PASS (build, diagnostics, kbd readback, host readback):", binary)
