#!/usr/bin/env bash
# usage: run1.sh <tree> <stage:std|thr|cov> <test file rel> <log>
tree="$1"; stage="$2"; file="$3"; log="$4"
cd "$tree" || exit 99
mp=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
case "$stage" in
  std) cmd=("$mp" -X heapsize=16M "$file") ;;
  thr) cmd=("$mp" -X heapsize=16M tests/_threshold_runner.py "$file" 32768) ;;
  cov) cmd=(/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython -X heapsize=16M tests/_coverage_runner.py "$file" "$log.cov.json") ;;
esac
start=$(date +%s.%N)
unshare -n bash -c 'ip link set lo up; exec "$@"' _ env TZ=UTC MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen" nice -n 19 timeout 900 "${cmd[@]}" > "$log" 2>&1
ec=$?
end=$(date +%s.%N)
printf 'exit=%s wall=%.1fs\n' "$ec" "$(echo "$end - $start" | bc)" >> "$log"
tail -1 "$log"
