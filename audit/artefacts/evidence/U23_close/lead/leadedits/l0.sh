#!/bin/bash
# l0.sh: the whole tests_scripts tier on wt-u23L in S/u23/api2/l0.sh's form, output in leadedits/l0.log.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $S/wt-u23L || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
PYTHONPATH=scripts unshare -n $S/u22/api5/ns.sh env TZ=UTC nice -n 19 /home/user/sensors/.venv/bin/python -m pytest tests_scripts -q -p no:cacheprovider > $S/u23/leadedits/l0.log 2>&1
echo "rc=$?" >> $S/u23/leadedits/l0.log
