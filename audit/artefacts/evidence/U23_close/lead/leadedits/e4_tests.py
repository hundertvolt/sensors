# Edit 4, step 1 (tests first): isRecord's cases in tests_js/definitions.test.js, importing it from js/definitions.js.
import sys
p = sys.argv[1] + "/tests_js/definitions.test.js"
s = open(p).read()
old_imp = 'import { loadDefinitions, resolveFieldValue, validateDefinitions } from "../js/definitions.js";'
new_imp = 'import { isRecord, loadDefinitions, resolveFieldValue, validateDefinitions } from "../js/definitions.js";'
assert s.count(old_imp) == 1
s = s.replace(old_imp, new_imp)
anchor = 'describe("resolveFieldValue", () => {\n'
assert s.count(anchor) == 1
block = '''describe("isRecord", () => {
    it("accepts every object but null and an array, an Object.create(null) one and a class instance included", () => {
        for (const value of [{}, { a: 1 }, Object.create(null), new Date(0), new Map()]) {
            expect(isRecord(value)).toBe(true);
        }
    });

    it("refuses null, an array, a function and every primitive", () => {
        for (const value of [null, undefined, [], [{ a: 1 }], () => ({}), 0, Number.NaN, "{}", true, Symbol("s")]) {
            expect(isRecord(value)).toBe(false);
        }
    });
});

'''
s = s.replace(anchor, block + anchor)
open(p, "w").write(s)
print("ok")
