# Scratch runner: puts the contract-emulation overlay ahead of tests/ (the script dir is not tests/).
import gc
import sys

if len(sys.argv) > 2:
    gc.threshold(int(sys.argv[2]))
sys.path.insert(0, "/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18n/ovl")
import microtest

mod = __import__(sys.argv[1])
microtest.run(mod.__dict__)
