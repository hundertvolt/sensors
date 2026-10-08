# lane O: one keep-going build of the host lwIP flavour on the private toolchain, to list every diagnostic at once.
import shutil, subprocess, sys
from pathlib import Path
wt, tc = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(wt / "toolchain"))
import setup_toolchain as st
import micropython_overrides as mo
mp = tc / "micropython"
make_vars = mo.apply_unix_lwip_host_override(mp, tc / "build_overrides", st.load_lwip_macros())
unix = mp / "ports" / "unix"
shutil.rmtree(unix / make_vars["BUILD"], ignore_errors=True)
cmd = ["make", "-k", "-j2", *(f"{k}={v}" for k, v in make_vars.items())]
print("$", " ".join(cmd), flush=True)
r = subprocess.run(cmd, cwd=unix, env=st.build_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
print(r.stdout)
print("make rc", r.returncode)
sys.exit(r.returncode)
