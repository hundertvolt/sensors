import sys, textwrap, collections
ids = [l.split()[0] for l in open(sys.argv[1])]
fam = collections.OrderedDict()
for i in ids: fam.setdefault(i.split(".")[0], []).append(i)
names = {"toml": "the TOML file", "instance": "an `[[instance]]`", "device": "`[device]`", "bus": "a `[bus.*]` table",
 "gpio": "pin legality", "names": "names and keys", "wiring": "wiring", "source": "a driver's source", "src": "a `src/` fact the build reads",
 "driver": "the driver registry", "requires": "`@requires`", "limits": "`@limits`", "tag": "every tag family", "web": "`@web`/`@web-group` and the definitions",
 "schema": "schema constants", "api": "the API reference", "toolchain": "the toolchain tables", "twin": "the twin wiring plan", "cli": "the CLI"}
order = ["toml","device","bus","instance","gpio","names","wiring","source","src","driver","requires","limits","tag","schema","web","api","toolchain","twin","cli"]
assert set(order) == set(fam), set(fam) ^ set(order)
out = []
for f in order:
    out.append(f"{names[f]}: " + ", ".join(f"`{i}`" for i in fam[f]))
body = "; ".join(out) + "."
print("\n".join("  " + l for l in textwrap.wrap("The rule ids, by what each guards — " + body, 98, break_long_words=False, break_on_hyphens=False)))
