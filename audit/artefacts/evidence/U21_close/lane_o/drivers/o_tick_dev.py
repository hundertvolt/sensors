# lane O: dev's tick-offset TEST image, once, through scripts/build_firmware.py's own staging and
# setup_toolchain.build_firmware(tick_offset_test=True), on the private toolchain.
import functools, importlib.util, sys
from pathlib import Path
wt, tc, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve(), Path(sys.argv[3])
spec = importlib.util.spec_from_file_location("build_firmware", wt / "scripts" / "build_firmware.py")
bf = importlib.util.module_from_spec(spec); sys.modules["build_firmware"] = bf; spec.loader.exec_module(bf)
st = bf.st; mo = st.micropython_overrides
board = st.load_versions(wt / "toolchain" / "versions.toml")["toolchain"]["board"]
real_apply = mo.apply_tick_offset_override
def apply_with_board(micropython_dir, overrides_dir, **kwargs):
    # T's call on this base predates the board keyword (setup_toolchain.py:514; T's 5b6dc1b passes board=board).
    return real_apply(micropython_dir, overrides_dir, board=kwargs.get("board", board))
mo.apply_tick_offset_override = apply_with_board
st.build_firmware = functools.partial(st.build_firmware, tick_offset_test=True)
sys.argv = ["build_firmware.py", "dev", "--toolchain-dir", str(tc), "--jobs", "2", "--output", str(out)]
rc = bf.main()
print("build_firmware.py dev (tick-offset test image) rc", rc, flush=True)
tick_dir = tc / "micropython" / "ports" / "rp2" / f"build-{board}-tickoffset"
print("tick_offset_in_build:", mo.tick_offset_in_build(tick_dir))
mo.verify_tick_offset_in_build(tick_dir, expected=True); print("readback expected=True: PASS")
try:
    mo.verify_tick_offset_in_build(tick_dir, expected=False); print("RELEASE REFUSAL MISSING"); rc = 1
except mo.OverrideError as e:
    print("release readback over the test image refused:", e)
sys.exit(rc)
