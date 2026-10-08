#!/bin/bash
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u18n
ip link set lo up
export TZ=UTC
nice -n 19 /home/user/sensors/.venv/bin/python scripts/_generate_sensortask_modules.py || exit 90
nice -n 19 /home/user/sensors/.venv/bin/python scripts/_digital_twin_ci_suite.py --micropython-bin /root/pico-toolchain/micropython/ports/unix/build-standard/micropython --device wozi --logs-dir /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18n/twin_logs
