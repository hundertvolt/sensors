# timens_run.py <uptime_s> <cmd...>: run cmd with CLOCK_MONOTONIC (and boottime) reading about <uptime_s> at its start.
import ctypes
import os
import subprocess
import sys

CLONE_NEWTIME = 0x80
target = int(sys.argv[1])
now = int(float(open("/proc/uptime").read().split()[0]))
offset = target - now
libc = ctypes.CDLL(None, use_errno=True)
if libc.unshare(CLONE_NEWTIME) != 0:
    sys.exit(f"unshare(CLONE_NEWTIME) failed: errno {ctypes.get_errno()}")
with open("/proc/self/timens_offsets", "w") as f:  # settable until the first process enters the namespace
    f.write(f"monotonic {offset} 0\nboottime {offset} 0\n")
sys.exit(subprocess.call(sys.argv[2:]))  # the child is that first process
