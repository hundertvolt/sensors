#!/bin/bash
# Copies lane C's worktree (on the API base) into a scratch tree and overlays stand-ins for V's 48u device_wiring
# fill, V's fix on the missing-[device]-field raise, and P's compile() of the generated sources. Never touches the worktree.
set -euo pipefail
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
WT=$SP/wt-u20c
SIM=$SP/u20c/sim2b/run$(date +%s)
mkdir -p "$SIM"
tar -C "$WT" -cf - --exclude=./.git --exclude=./audit --exclude=./arduino --exclude=./legacy --exclude=./datasheets --exclude=./node_modules --exclude='*/__pycache__' . | tar -C "$SIM" -xf -
ln -sfn "$SP/wt-u8/typings" "$SIM/typings"
/home/user/sensors/.venv/bin/python - "$SIM" <<'PY'
import sys
from pathlib import Path
sim = Path(sys.argv[1])
v = sim / "buildgen" / "validate.py"
t = v.read_text()
old = "            _check_wiring_reference(model, wf, value, \"device.wiring\", toml_field)\n"
assert t.count(old) == 1
t = t.replace(old, old + "            model.device_wiring.setdefault(consumer_label, {})[toml_field] = wf  # SIM\n")
old2 = 'f"[device] is missing required field'
assert old2 in t
import re
t = re.sub(r'raise BuildError\(model\.device, f"\[device\] is missing required field ([^\n]*?)\)\n', lambda m: 'raise BuildError(model.device, f"[device] is missing required field ' + m.group(1) + ', fix="SIM add it")\n', t)
v.write_text(t)
g = sim / "buildgen" / "generate.py"
t = g.read_text()
old = "    module_source = generate_module_source(model, model.construction_order, build_date if build_date is not None else current_build_date(), src_dir)\n"
assert t.count(old) == 1
t = t.replace(old, old + "    try:\n        compile(module_source, f'sensortask_{model.device}.py', 'exec')\n    except SyntaxError as e:\n        from buildgen.errors import BuildInternalError\n        raise BuildInternalError(f'[{model.device}] {e}') from e\n")
g.write_text(t)
print(sim)
PY
