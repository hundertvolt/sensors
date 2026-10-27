#!/bin/bash
# rebuild.sh <worktree>: the lead's rebuild of a worktree's generated inputs - the device modules, the frozen website
# (frozen_modules/frozen_html.py, as scripts/test.sh builds it) and every device's site (build/generated_html/).
W=${1:?worktree}
cd "$W" || exit 2
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
export PATH=/root/pico-toolchain/node/node-v24.22.1-linux-x64/bin:$PATH
nice -n 19 "$S/wt-base/.venv/bin/python" scripts/_generate_sensortask_modules.py > /dev/null || { echo "generate failed"; exit 1; }
nice -n 19 scripts/build_website.sh wozi > /dev/null || { echo "build_website failed"; exit 1; }
nice -n 19 scripts/build_device_websites.sh > /dev/null || { echo "build_device_websites failed"; exit 1; }
echo "rebuilt $(git rev-parse --short HEAD) $(ls build/generated_html | tr '\n' ' ')"
