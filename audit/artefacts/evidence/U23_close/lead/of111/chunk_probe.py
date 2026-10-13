# Scratch probe: the log-chunk snapshot is not vacuous - it holds every store's chunk and a plain ResetErrors changes it.
import sys

import _sensortask_scenarios as sc
from _error_codes import code

sc.register_for_device(sys.argv[1])
module = sc.build(sys.argv[1])
for logger in sc._fram_stores(module):
    sc.run(logger.err_s("probe", errno=code("E", "INIT")))
before = sc._log_chunk_bytes(module)
res = sc._dispatch(module, "PUT", "/status", {"ResetErrors": True})
after = sc._log_chunk_bytes(module)
print("chunks", len(before), "bytes", sum(len(b) for b in before), "changed", sum(1 for a, b in zip(before, after) if a != b), res.body)
