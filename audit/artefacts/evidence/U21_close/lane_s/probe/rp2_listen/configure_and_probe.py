# Scratch (lane S, never committed): configure the rp2 firmware build in u21tc-s exactly as the installer
# does (its own overrides, CMake only, no compile of the firmware), then compile probe.c with that build's
# flags and print each probe array's size from arm-none-eabi-nm.
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "toolchain")
import micropython_overrides as mo  # noqa: E402
import setup_toolchain as st  # noqa: E402

toolchain = Path(sys.argv[1])
probe_dir = Path(sys.argv[2])
mp = toolchain / "micropython"
board = st.load_versions(st.VERSIONS_PATH)["toolchain"]["board"]
board_vars = mo.apply_lwip_connection_counts_override(mp, toolchain / "build_overrides", board, st.load_lwip_macros())
mod_vars = mo.apply_modlwip_eagain_override(mp, toolchain / "build_overrides")
build = mp / "ports" / "rp2" / "build-listenprobe"
cmd = ["cmake", "-S", ".", "-B", str(build), "-DPICO_BUILD_DOCS=0", f"-DMICROPY_BOARD={board}", f"-DMICROPY_BOARD_DIR={board_vars['BOARD_DIR']}", f"-DUSER_C_MODULES={mod_vars['USER_C_MODULES']}"]
subprocess.run(cmd, cwd=mp / "ports" / "rp2", check=True, capture_output=True, text=True, env=st.build_env())
flags = (build / "CMakeFiles" / "firmware.dir" / "flags.make").read_text()
args = []
for key in ("C_DEFINES", "C_INCLUDES", "C_FLAGS"):
    args += shlex.split(re.search(rf"^{key} = (.*)$", flags, re.MULTILINE).group(1))
obj = probe_dir / "probe.o"
subprocess.run(["arm-none-eabi-gcc", *args, "-c", str(probe_dir / "probe.c"), "-o", str(obj)], check=True, env=st.build_env())
out = subprocess.run(["arm-none-eabi-nm", "-S", str(obj)], check=True, capture_output=True, text=True).stdout
for line in sorted(out.splitlines()):
    parts = line.split()
    if len(parts) == 4 and parts[3].startswith("probe_"):
        print(f"{parts[3]} = {int(parts[1], 16)}")
print("flags from", build / "CMakeFiles" / "firmware.dir" / "flags.make")
