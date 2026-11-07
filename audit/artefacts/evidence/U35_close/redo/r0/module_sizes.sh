#!/bin/bash
# module_sizes.sh REPO REV OUTTSV: each src/*.py at REV, its line count and its bytecode compiled with bare source names.
set -eu
R="$1"; REV="$2"; OUT="$3"; X=/root/pico-toolchain/micropython/mpy-cross/build/mpy-cross
T=$(mktemp -d -p "$(dirname "$OUT")"); : > "$OUT"
git -C "$R" ls-tree --name-only "$REV" src/ | grep '\.py$' | while read -r f; do
  b=$(basename "$f"); git -C "$R" show "$REV:$f" > "$T/$b"
  (cd "$T" && "$X" -s "$b" -o "${b%.py}.mpy" "$b")
  printf '%s\t%s\t%s\n' "$b" "$(wc -l < "$T/$b")" "$(stat -c %s "$T/${b%.py}.mpy")" >> "$OUT"
done
rm -r "${T:?}"
