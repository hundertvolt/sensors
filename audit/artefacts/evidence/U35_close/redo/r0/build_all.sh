#!/bin/bash
# build_all.sh: the six device images at the current tree, one after another; prints the .uf2 bytes per device.
set -u
for d in arzi dev grkizi klkizi schlafzi wozi; do
  python scripts/build_firmware.py "$d" --jobs 3 > "build_$d.out" 2>&1; rc=$?
  echo "$d rc=$rc uf2=$(stat -c %s "build/firmware-$d.uf2" 2>/dev/null)"
done
