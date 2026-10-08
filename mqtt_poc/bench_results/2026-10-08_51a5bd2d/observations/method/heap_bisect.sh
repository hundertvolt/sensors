#!/usr/bin/env bash
S=/tmp/claude-1000/-home-nico-programming-sensors/2568bff6-7ea5-43c2-b076-16b8d5d7bd3c/scratchpad
MP=$HOME/pico-toolchain/micropython/ports/unix/build-standard/micropython; PY=/home/nico/programming/sensors/.venv/bin/python
F=$S/wt_c11ca0a
cd /home/nico/programming/sensors
for c in 3fe0fb2b e5d2c439 653328b1 1dea035d e2f78f05 8cd3b172 7934fae1 43aced07 65a0df3b f44b9411 c3df14e1 1b59a05d 40a3508f 01e8e3eb 2f049a00 41b47f1d 8d44fd14 2949ed97 cbb65df2 1cff5a26 5689e2f4 2977c4e0 c11ca0a 51a5bd2d; do
  d=$S/bis/wt_$c; [ -d $d ] || git worktree add -q --detach $d $c
  ( cd $d && timeout 300 $PY scripts/_generate_sensortask_modules.py >/dev/null 2>&1 ) || { echo "$c gen-failed"; continue; }
  ln -sfn /home/nico/programming/sensors/frozen_modules $d/frozen_modules 2>/dev/null
  for fakes in $F $d; do
    w=$S/bis/run_$c; rm -rf $w; mkdir -p $w
    cat > $w/wrap.py <<PYEOF
import json, machine
with open("$d/build/generated_src/sensortask_dev_wiring_plan.json") as fh:
    machine.configure_wiring(json.load(fh))
del fh
exec(open("$S/wt_c11ca0a/tests_hardware/device_scripts/heap_headroom_after_full_system_build.py").read())
PYEOF
    ( cd $w && MICROPYPATH="$d/build/generated_src:$d/src:$fakes/digital_twin:$d/ext:$d/frozen_modules:.frozen" TZ=UTC timeout 300 $MP -X heapsize=16M wrap.py > out.txt 2>&1 )
    b=$(grep -oP "^HEAP baseline: .*alloc=\K[0-9]+" $w/out.txt); a=$(grep -oP "^HEAP after_build_system: .*alloc=\K[0-9]+" $w/out.txt)
    if [ -n "$a" ]; then echo "$c fakes=$( [ $fakes = $F ] && echo c11 || echo own ) baseline=$b after=$a graph=$((a-b)) $(git log -1 --format=%s $c | cut -c1-60)"; break; fi
  done
  [ -n "$a" ] || echo "$c run-failed"
done
echo BISECT-DONE
