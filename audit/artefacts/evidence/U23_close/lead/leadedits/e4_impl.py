# Edit 4, step 2: one exported isRecord in js/definitions.js replaces definitions' isObject, render's isRecord and the mock's isPlainObject.
import re
import sys
root = sys.argv[1]
BODY = "    return typeof value === \"object\" && value !== null && !Array.isArray(value);\n}\n"


def rd(name):
    return open(f"{root}/js/{name}").read()


def wr(name, s):
    open(f"{root}/js/{name}", "w").write(s)


def drop_local(s, name, doc_returns):
    block = f"/**\n * @param {{unknown}} value\n * @returns {doc_returns}\n */\nfunction {name}(value) {{\n{BODY}\n"
    assert s.count(block) == 1, name
    return s.replace(block, "")


# definitions.js: drop the private isObject, add the exported isRecord first in the public group (a getter, D.15).
s = rd("definitions.js")
s = drop_local(s, "isObject", "{value is Record<string, unknown>} true for a plain object: not null, not an array.")
assert "isObject" in s
s = re.sub(r"\bisObject\(", "isRecord(", s)
assert "isObject" not in s
anchor = s.index("export async function loadDefinitions(")
doc = s.rindex("\n/**\n", 0, anchor) + 1
shared = (
    "/**\n"
    " * The one plain-object check of every js/ module: any object but null and an array, an `Object.create(null)`\n"
    " * object and a class instance included.\n"
    " * @param {unknown} value\n"
    " * @returns {value is Record<string, unknown>}\n"
    " */\n"
    f"export function isRecord(value) {{\n{BODY}\n"
)
s = s[:doc] + shared + s[doc:]
wr("definitions.js", s)

# render.js: drop its local copy, import the shared one.
s = rd("render.js")
s = drop_local(s, "isRecord", "{value is Record<string, unknown>} true for a plain object: not null, not an array.")
old = 'import { resolveFieldValue } from "./definitions.js";'
assert s.count(old) == 1
s = s.replace(old, 'import { isRecord, resolveFieldValue } from "./definitions.js";')
wr("render.js", s)

# mock-server.js: the same, under its old name isPlainObject.
s = rd("mock-server.js")
s = drop_local(s, "isPlainObject", "{value is Record<string, unknown>}")
s = re.sub(r"\bisPlainObject\(", "isRecord(", s)
assert "isPlainObject" not in s
old = 'import { neverUnchanged } from "./definitions.js";'
assert s.count(old) == 1
s = s.replace(old, 'import { isRecord, neverUnchanged } from "./definitions.js";')
wr("mock-server.js", s)
print("ok")
