#!/bin/bash
# mpy_sizes.sh REPO OUT: each src/*.py at the audit's start and at the head compiled by the pinned mpy-cross; bytes per module.
R="$1"; OUT="$2"; X=/root/pico-toolchain/micropython/mpy-cross/build/mpy-cross
mkdir -p "$OUT/old" "$OUT/new" "$OUT/gen"
for c in old:25caf528 new:497b3eda; do
  tag=${c%%:*}; rev=${c#*:}
  git -C "$R" ls-tree --name-only "$rev" src/ | grep '\.py$' | while read -r f; do
    git -C "$R" show "$rev:$f" > "$OUT/$tag/$(basename "$f")"
    "$X" -o "$OUT/$tag/$(basename "$f" .py).mpy" "$OUT/$tag/$(basename "$f")" 2> "$OUT/$tag/$(basename "$f" .py).err" || echo "compile failed: $tag $f"
  done
done
for f in "$R"/build/generated_src/*.py; do "$X" -o "$OUT/gen/$(basename "$f" .py).mpy" "$f" || echo "compile failed: gen $f"; done
