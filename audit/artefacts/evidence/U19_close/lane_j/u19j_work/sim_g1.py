"""Inserts G1's two status-networking rows (lane plan step 6) into generated definitions JSON, for a local check."""
import json, sys, pathlib
for p in pathlib.Path(sys.argv[1]).glob("*.json"):
    if p.stem in ("index", "inputs_stamp"):
        continue
    d = json.loads(p.read_text())
    for s in d["sections"]:
        if s["key"] != "status":
            continue
        for g in s["groups"]:
            if g.get("key") == "networking":
                g["fields"].append({"key": "HTTPDropped", "label": "Dropped Connections", "kind": "readonly", "description": "Web connections dropped in the last 24 hours, hourly resolution."})
                g["fields"].append({"key": "WifiTS", "label": "Wi-Fi Status Time", "kind": "readonly", "format": "epoch"})
    p.write_text(json.dumps(d))
    print("patched", p.name)
