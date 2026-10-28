# Scratch (lane S, never committed): the one-time sensitivity build. The installer's own host-build
# path with the modlwip EAGAIN insertion disabled in-process, into build-lwip-control under its own
# overrides root, so neither build-lwip nor its generated files are touched.
import sys
from pathlib import Path

sys.path.insert(0, "toolchain")
import micropython_overrides as mo  # noqa: E402
import setup_toolchain as st  # noqa: E402

toolchain = Path(sys.argv[1])
micropython_dir = toolchain / "micropython"
mo._MODLWIP_EAGAIN_BLOCK = ""  # the pinned retry loop, unpatched
make_vars = mo.apply_unix_lwip_host_override(micropython_dir, toolchain / "build_overrides_control", st.load_lwip_macros())
make_vars["BUILD"] = "build-lwip-control"
binary = st._build_unix_variant(micropython_dir, 2, make_vars=make_vars, build_dir_name="build-lwip-control", label="sensitivity control, insertion disabled")
copy = toolchain / "build_overrides_control" / mo.UNIX_LWIP_HOST_DIR_NAME / "src" / "extmod" / "modlwip.c"
assert "hand the wait back to the caller" not in copy.read_text(), "the control copy still carries the EAGAIN block"
dep = (binary.parent / "extmod" / "modlwip.P").read_text()
assert str(copy) in dep, "the control build did not compile its own unpatched copy"
print("control built:", binary)
