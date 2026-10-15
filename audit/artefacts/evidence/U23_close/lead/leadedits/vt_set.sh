#!/bin/bash
# vt_set.sh <prefix>: the brief's vitest files on wt-u23L, one at a time, each in its own netns, nice 19.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/leadedits; p=${1:?prefix}
cd $S/wt-u23L || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
: > $O/${p}_summary.txt
for f in templates accessibility render generated-definitions-render site-functions definitions mock-server mock-server-put-matrix mock-data-compose definitions-mockdata-coverage api-reference-agreement main app lint-ceilings; do
  t0=$(date +%s)
  unshare -n $S/u22/api5/ns.sh nice -n 19 npx vitest run tests_js/$f.test.js > $O/${p}_$f.log 2>&1
  echo "$f rc=$? wall=$(( $(date +%s) - t0 ))s $(grep -E '^ +Tests ' $O/${p}_$f.log | tr -s ' ')" >> $O/${p}_summary.txt
done
echo done >> $O/${p}_summary.txt
