"""Appends lane D's U23 cases to tests_scripts/definitions_shape_cases.json in its one-case-per-line form."""
import copy
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
cases = json.loads(path.read_text())
names = {c["name"] for c in cases}

BASE = {"schemaVersion": "1.0.0", "device": {"id": "fixture-device", "displayName": "Fixture Device"}, "landingSection": "measurements", "defaultPollIntervalMs": 3000,
        "sections": [{"key": "measurements", "label": "Measurements", "rest": {"get": "/measurements"}, "pollGroup": "live",
                      "groups": [{"key": "G", "label": "G", "fields": [{"key": "CO2", "label": "CO2", "kind": "readonly"}]}]}]}


def doc(**top):
    d = copy.deepcopy(BASE)
    d.update(top)
    return d


def section(**keys):
    s = copy.deepcopy(BASE["sections"][0])
    s.update(keys)
    return doc(sections=[s])


def groups(*gs, **section_keys):
    return section(groups=list(gs), **section_keys)


def fields(*fs, **group_keys):
    g = {"key": "G", "label": "G", "fields": list(fs)}
    g.update(group_keys)
    return groups(g)


def field(**keys):
    return fields(dict(keys))


MAX = 2**31 - 1
new = [
    ("defaultPollIntervalMs at setTimeout's ceiling", doc(defaultPollIntervalMs=MAX), True),
    ("defaultPollIntervalMs above setTimeout's ceiling", doc(defaultPollIntervalMs=MAX + 1), False),
    ("section pollIntervalMs at setTimeout's ceiling", section(pollIntervalMs=MAX), True),
    ("section pollIntervalMs above setTimeout's ceiling", section(pollIntervalMs=MAX + 1), False),
    ("defaultDecimals at 2", doc(defaultDecimals=2), True),
    ("defaultDecimals at the toFixed ceiling", doc(defaultDecimals=100), True),
    ("defaultDecimals 1.5", doc(defaultDecimals=1.5), False),
    ("defaultDecimals -1", doc(defaultDecimals=-1), False),
    ("defaultDecimals 101", doc(defaultDecimals=101), False),
    ("defaultDecimals a string", doc(defaultDecimals="2"), False),
    ("duplicate section keys", doc(landingSection="m", sections=[
        {"key": "m", "label": "M", "rest": {"get": "/m"}, "pollGroup": "live", "groups": []},
        {"key": "m", "label": "M2", "rest": {"get": "/m2"}, "pollGroup": "live", "groups": []}]), False),
    ("a group that is null", groups(None), False),
    ("a group that is a string", groups("G"), False),
    ("duplicate group keys", groups({"key": "G", "label": "G", "fields": []}, {"key": "G", "label": "G2", "fields": []}), False),
    ("errcount module missing its label", groups({"key": "errcount", "label": "Errors", "kind": "errcount", "modules": [{"key": "SCD30"}]}), False),
    ("errcount module that is not an object", groups({"key": "errcount", "label": "Errors", "kind": "errcount", "modules": ["SCD30"]}), False),
    ("a submit group under a section with rest.put", section(rest={"get": "/s", "put": "/s"}, groups=[{"key": "G", "label": "G", "submit": True, "fields": [{"key": "F", "label": "F", "kind": "number"}]}]), True),
    ("a submit group under a section without rest.put", groups({"key": "G", "label": "G", "submit": True, "fields": [{"key": "F", "label": "F", "kind": "number"}]}), False),
    ("a field that is null", fields(None), False),
    ("a field that is a number", fields(7), False),
    ("field key missing", field(label="F", kind="readonly"), False),
    ("field label missing", field(key="F", kind="readonly"), False),
    ("field kind missing", field(key="F", label="F"), False),
    ("field kind unknown", field(key="F", label="F", kind="slider"), False),
    ("duplicate field keys", fields({"key": "F", "label": "F", "kind": "readonly"}, {"key": "F", "label": "F2", "kind": "readonly"}), False),
    ("a composite field with sub-fields", field(key="C", label="C", kind="composite", subFields=[{"key": "R", "label": "R", "kind": "number"}, {"key": "T", "label": "T", "kind": "number", "float": True}]), True),
    ("composite subFields not an array", field(key="C", label="C", kind="composite", subFields={"R": 1}), False),
    ("composite subFields missing", field(key="C", label="C", kind="composite"), False),
    ("composite with a sub-field missing its kind", field(key="C", label="C", kind="composite", subFields=[{"key": "R", "label": "R"}]), False),
    ("specialValues not an array", field(key="F", label="F", kind="number", specialValues={"value": 0, "meaning": "Off"}), False),
    ("a special value without a meaning", field(key="F", label="F", kind="number", specialValues=[{"value": 0}]), False),
    ("a clearable string", field(key="F", label="F", kind="string", clearable=True), True),
    ("clearable not a boolean", field(key="F", label="F", kind="string", clearable="yes"), False),
    ("clearable on a number field", field(key="F", label="F", kind="number", clearable=True), False),
    ("a readonly field reading its value from another route", field(key="F", label="F", kind="readonly", statusPath=["notification", "F"]), True),
    ("a number field reading its value from another route", field(key="F", label="F", kind="number", statusPath=["notification", "F"]), True),
    ("statusPath empty", field(key="F", label="F", kind="number", statusPath=[]), False),
    ("statusPath with an empty step", field(key="F", label="F", kind="number", statusPath=["notification", ""]), False),
    ("statusPath not an array", field(key="F", label="F", kind="number", statusPath="notification.F"), False),
    ("statusPath on a toggle field", field(key="F", label="F", kind="toggle", statusPath=["notification", "F"]), False),
    ("a readonly field with codes and codeTones", field(key="F", label="F", kind="readonly", codes={"0": "off", "1": "on"}, codeTones={"0": "neutral", "1": "good"}), True),
    ("codeTones key outside codes", field(key="F", label="F", kind="readonly", codes={"0": "off"}, codeTones={"1": "good"}), False),
    ("codeTones without codes", field(key="F", label="F", kind="readonly", codeTones={"0": "good"}), False),
    ("codeTones with an unknown tone", field(key="F", label="F", kind="readonly", codes={"0": "off"}, codeTones={"0": "red"}), False),
    ("codeTones not an object", field(key="F", label="F", kind="readonly", codes={"0": "off"}, codeTones=["good"]), False),
    ("a number field ignored while its sibling is set", fields({"key": "A", "label": "A", "kind": "number"}, {"key": "B", "label": "B", "kind": "number", "ignoredWhenSet": "A"}), True),
    ("ignoredWhenSet naming no sibling", fields({"key": "A", "label": "A", "kind": "number"}, {"key": "B", "label": "B", "kind": "number", "ignoredWhenSet": "Nope"}), False),
    ("ignoredWhenSet naming the field itself", field(key="B", label="B", kind="number", ignoredWhenSet="B"), False),
    ("ignoredWhenSet not a string", fields({"key": "A", "label": "A", "kind": "number"}, {"key": "B", "label": "B", "kind": "number", "ignoredWhenSet": ["A"]}), False),
    ("a number field with a resolution", field(key="F", label="F", kind="number", float=True, resolution=0.01), True),
    ("resolution 0", field(key="F", label="F", kind="number", resolution=0), False),
    ("resolution -1", field(key="F", label="F", kind="number", resolution=-1), False),
    ("resolution a string", field(key="F", label="F", kind="number", resolution="0.01"), False),
    ("resolution on a string field", field(key="F", label="F", kind="string", resolution=0.01), False),
    ("an always-executed field", field(key="F", label="F", kind="toggle", alwaysExecuted=True), True),
    ("alwaysExecuted not a boolean", field(key="F", label="F", kind="toggle", alwaysExecuted="true"), False),
    ("an enum field asking for confirmation", field(key="F", label="F", kind="enum", options=[{"value": "reboot", "label": "Reboot"}], confirm=True), True),
    ("a toggle field asking for confirmation", field(key="F", label="F", kind="toggle", confirm=True), True),
    ("confirm not a boolean", field(key="F", label="F", kind="toggle", confirm="yes"), False),
    ("confirm on a number field", field(key="F", label="F", kind="number", confirm=True), False),
]
for name, definitions, valid in new:
    assert name not in names, name
    cases.append({"name": name, "definitions": definitions, "valid": valid})
lines = ["  " + json.dumps(c, ensure_ascii=False) for c in cases]
path.write_text("[\n" + ",\n".join(lines) + "\n]\n")
print(len(cases))
