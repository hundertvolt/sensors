#!/bin/bash
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $S/wt-u23api || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
PYTHONPATH=scripts unshare -n $S/u22/api5/ns.sh env TZ=UTC nice -n 19 /home/user/sensors/.venv/bin/python -m pytest tests_scripts -q -p no:cacheprovider > $S/u23/api3/l0.log 2>&1
echo "rc=$?" >> $S/u23/api3/l0.log
