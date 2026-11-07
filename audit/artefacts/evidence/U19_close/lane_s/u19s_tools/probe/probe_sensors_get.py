# Probe: what GET /sensors answers per sensor on a freshly built mock-tier device (no snapshot queued).
import json
import sys

import _sensortask_scenarios as s

device = sys.argv[1] if len(sys.argv) > 1 else "wozi"
s.register_for_device(device)
module = s.build(device, web_host="127.0.0.1", web_port=0)
res = s._dispatch(module, "GET", "/sensors")
parsed = json.loads(s.drain_json_response_body(res.body))
for name in sorted(parsed):
    print(name, parsed[name])
