# V2: does a json.dump() that fails part-way leave a truncated file (the pre-audit flush and setup write form)?
# The failure is a RuntimeError from a nesting too deep for the C stack, raised after the leading keys are out.
import json
p = "v2_cfg.json"
with open(p, "w") as f:
    json.dump({"A": 1, "B": 2.5}, f)
print("before:", open(p).read())
deep = []
for _ in range(20000):
    deep = [deep]
try:
    with open(p, "w") as f:
        json.dump({"A": 1, "B": 2.5, "Z": deep}, f)
except Exception as e:
    print("raised:", type(e).__name__, e)
t = open(p).read()
print("after: length", len(t), "starts", repr(t[:40]))
try:
    json.loads(t)
    print("parses")
except ValueError as e:
    print("does not parse:", e)
