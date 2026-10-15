# lane O: the four post-build proofs re-run against the real artifacts of u21tc-o, plus one planted miss each.
import sys
from pathlib import Path
wt, tc = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(wt / "toolchain"))
import setup_toolchain as st
import micropython_overrides as mo
mp = tc / "micropython"; unix = mp / "ports" / "unix"; env = st.build_env()
ov = tc / "build_overrides"
kbd = {"VARIANT": "standard", "VARIANT_DIR": str(ov / mo.UNIX_KBD_INTR_DIR_NAME)}
for name, vars_ in (("build-standard", kbd), ("build-settrace", {**kbd, "CFLAGS_EXTRA": "-DMICROPY_PY_SYS_SETTRACE=1", "BUILD": "build-settrace"})):
    mo.verify_unix_kbd_intr_in_build(unix, vars_, name, env=env); print("kbd readback PASS", name)
host = {"VARIANT": "standard", "VARIANT_DIR": str(ov / mo.UNIX_LWIP_HOST_DIR_NAME), "BUILD": "build-lwip", "MICROPY_PY_LWIP": "1", "MICROPY_PY_LWIP_LOOPBACK": "1", "MICROPY_PY_SOCKET": "0"}
mo.verify_unix_kbd_intr_in_build(unix, host, "build-lwip", env=env); print("kbd readback PASS build-lwip")
mo.verify_unix_lwip_host_in_build(unix / "build-lwip", mp, unix / "build-lwip" / "micropython", env=env); print("host readback PASS build-lwip")
try:
    mo.verify_unix_kbd_intr_in_build(unix, {"VARIANT": "standard"}, "build-standard", env=env); print("planted: real standard variant PASSED?!")
except mo.OverrideError as e: print("planted (VARIANT_DIR not redirected) refused:", str(e)[:70])
try:
    mo.verify_unix_lwip_host_in_build(unix / "build-standard", mp, unix / "build-standard" / "micropython", env=env); print("planted host PASSED?!")
except mo.OverrideError as e: print("planted (build-standard as host build) refused:", str(e)[:70])
print("leftover .pp:", sorted(str(p) for p in unix.rglob("unix_mphal.pp")))
