/**
 * PUT-behaviour matrix over every real writable field of every device's generated definitions
 * (deduplicated by derivation), against js/mock-server.js's fetch interception - six categories per field
 * (owner, 2026-08-24) (valid, special, omitted, resubmit-unchanged, out-of-range, wrong-type), matching SPECIFICATION.md Part A.8.
 */
import { describe, expect, it } from "vitest";
import samples from "../mockdata/samples.json";
import { neverUnchanged } from "../js/definitions.js";
import { composeMockData, installMockFetch } from "../js/mock-server.js";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";
import { collectPutFieldCases, dedupePutFieldCases, shardPutFieldCases, validStringValue } from "./_put_field_cases.js";

/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("../js/definitions.js").MockDeviceData} MockDeviceData */
/** @typedef {import("../js/definitions.js").MockSamples} MockSamples */
/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */
/** @typedef {import("./_put_field_cases.js").PutFieldCase & {data: MockDeviceData}} PutFieldCase */

/**
 * @param {string} device
 * @returns {{defs: SiteDefinitions, data: MockDeviceData}}
 */
function deviceUnderTest(device) {
    const defs = /** @type {SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device));
    return { defs, data: composeMockData(defs, /** @type {MockSamples} */ (samples)) };
}

/**
 * @param {string} device
 * @param {SiteDefinitions} defs
 * @param {MockDeviceData} data
 * @returns {PutFieldCase[]}
 */
function collectMockPutFieldCases(device, defs, data) {
    // A masked field's GET answers the mask, never the stored value the readback categories expect.
    return collectPutFieldCases(device, defs, data)
        .filter((c) => c.field.mask !== true)
        .map((c) => ({ ...c, data }));
}

const CASES = dedupePutFieldCases(DEVICE_IDS.flatMap((device) => {
    const { defs, data } = deviceUnderTest(device);
    return collectMockPutFieldCases(device, defs, data);
}));

/**
 * Sends one raw PUT body as exact JSON text, so a test controls a number's literal int/float
 * shape - which JSON.stringify() cannot, JS having no such distinction. Returns that field's
 * result and a fresh GET, inside the one installMockFetch() lifetime state persists for.
 * @param {PutFieldCase} testCase
 * @param {string | undefined} literal raw JSON literal text for the field's value, or undefined to
 * omit the field from the body entirely (the "untouched" sparse-PUT case)
 * @returns {Promise<{status: string | undefined, getBody: Record<string, unknown>}>}
 */
async function putAndGet({ defs, data, sectionKey, groupKey, field, putPath }, literal) {
    const uninstall = installMockFetch(defs, data);
    try {
        const inner = literal === undefined ? "" : `"${field.key}":${literal}`;
        const rawBody = sectionKey === "sensors" ? `{"${groupKey}":{${inner}}}` : `{${inner}}`;
        const putResponse = await fetch(putPath, { method: "PUT", headers: { "Content-Type": "application/json" }, body: rawBody });
        const putEnvelope = /** @type {{result?: Record<string, unknown>}} */ (await putResponse.json());
        const rawResult = sectionKey === "sensors" ? /** @type {Record<string, unknown> | undefined} */ (putEnvelope.result?.[groupKey]) : putEnvelope.result;
        const status = /** @type {string | undefined} */ (rawResult?.[field.key]);

        const getResponse = await fetch(putPath);
        const getBody = /** @type {Record<string, unknown>} */ (await getResponse.json());
        return { status, getBody };
    } finally {
        uninstall();
    }
}

/**
 * @param {Record<string, unknown>} getBody
 * @param {PutFieldCase} testCase
 * @returns {unknown}
 */
function currentValueIn(getBody, testCase) {
    const scoped = testCase.sectionKey === "sensors" ? /** @type {Record<string, unknown>} */ (getBody[testCase.groupKey]) : getBody;
    return scoped?.[testCase.field.key];
}

/** JSON.stringify()'s own rendering of a plain JS value - correct for string/enum/toggle values,
 * which JS's type system already renders unambiguously (unlike a whole-number "number" value,
 * which needs a test to state its int/float literal shape explicitly - see numberLiteral()).
 * @param {unknown} value
 * @returns {string}
 */
function literalOf(value) {
    return JSON.stringify(value);
}

/**
 * @param {number} value
 * @param {boolean} asFloat force a decimal point even for a whole number - no longer required for
 * the real backend to accept a `field.float`-marked field's value (it now coerces a bare-integer
 * literal, SPECIFICATION.md Part A.8), kept only so tests can still control literal shape
 * explicitly where the test's own intent is to exercise a specific shape either way.
 * @returns {string}
 */
function numberLiteral(value, asFloat) {
    if (asFloat && Number.isInteger(value)) {
        return `${value}.0`;
    }
    return String(value);
}

describe.each(CASES)("PUT $device $sectionKey/$groupKey/$field.key ($field.kind)", (testCase) => {
    const { field, currentValue } = testCase;
    const isFloat = field.kind === "number" && field.float === true;

    it("omitted from the body: not in the result, and the stored value is left untouched", async () => {
        const { status, getBody } = await putAndGet(testCase, undefined);
        expect(status).toBeUndefined();
        expect(currentValueIn(getBody, testCase)).toBe(currentValue);
    });

    if (currentValue !== undefined) {
        it("resubmitting the field's own current value: Unchanged, and the stored value is unaffected", async () => {
            const literal = field.kind === "number" ? numberLiteral(/** @type {number} */ (currentValue), isFloat) : literalOf(currentValue);
            const { status, getBody } = await putAndGet(testCase, literal);
            expect(status).toBe("Unchanged");
            expect(currentValueIn(getBody, testCase)).toBe(currentValue);
        });
    }

    it("a value of the wrong JSON type: Invalid, and the stored value is unaffected", async () => {
        // A JSON string is the wrong type for every field kind covered by this matrix (number,
        // string fields already validate real string values elsewhere in this same describe block,
        // enum, toggle) - "not-a-real-value" is guaranteed wrong for all of them.
        const wrongTypeLiteral = field.kind === "string" ? "12345" : '"not-a-real-value"';
        const { status, getBody } = await putAndGet(testCase, wrongTypeLiteral);
        expect(status).toBe("Invalid");
        expect(currentValueIn(getBody, testCase)).toBe(currentValue);
    });

    if (field.kind === "number") {
        const { min, max } = /** @type {{min: number, max: number}} */ (field);
        const mid = min + (max - min) / 2;

        it.each(
            [min, mid, max]
                .map((v) => (Number.isInteger(min) && Number.isInteger(max) && !isFloat ? Math.round(v) : v))
                .filter((v) => v !== currentValue),
        )("accepts %s (a valid value distributed across the range): Valid, and it gets persisted", async (value) => {
            const { status, getBody } = await putAndGet(testCase, numberLiteral(value, isFloat));
            expect(status).toBe("Valid");
            expect(currentValueIn(getBody, testCase)).toBe(value);
        });

        const step = Number.isInteger(min) && Number.isInteger(max) ? 1 : 0.5;
        const specialMagnitudes = new Set((field.specialValues ?? []).map((s) => s.value));
        /**
         * Steps further away from the range until a value avoids every declared special value - a
         * plain min-1/max+1 can otherwise coincide with one (e.g. FiltCoeff's min 0 and special -1).
         * @param {number} start
         * @param {1 | -1} direction
         * @returns {number}
         */
        function firstRejectable(start, direction) {
            let value = start;
            while (specialMagnitudes.has(value)) {
                value += direction * step;
            }
            return value;
        }
        it.each([firstRejectable(min - step, -1), firstRejectable(max + step, 1)])(
            "rejects %s (out of [min, max], and not a declared special value): Invalid, not persisted",
            async (value) => {
                const { status, getBody } = await putAndGet(testCase, numberLiteral(value, isFloat));
                expect(status).toBe("Invalid");
                expect(currentValueIn(getBody, testCase)).toBe(currentValue);
            },
        );

        for (const special of (field.specialValues ?? []).filter((s) => s.value !== currentValue)) {
            it(`accepts the declared special value ${special.value} ("${special.meaning}"): Valid, and it gets persisted`, async () => {
                const { status, getBody } = await putAndGet(testCase, numberLiteral(/** @type {number} */ (special.value), isFloat));
                expect(status).toBe("Valid");
                expect(currentValueIn(getBody, testCase)).toBe(special.value);
            });
        }
        for (const special of (field.specialValues ?? []).filter((s) => s.value === currentValue)) {
            it(`resubmitting the declared special value ${special.value} ("${special.meaning}"), which happens to already be the current value: Unchanged`, async () => {
                const { status, getBody } = await putAndGet(testCase, numberLiteral(/** @type {number} */ (special.value), isFloat));
                expect(status).toBe("Unchanged");
                expect(currentValueIn(getBody, testCase)).toBe(special.value);
            });
        }

        if (isFloat) {
            it("accepts a bare-integer literal for this float-typed field: Valid, coerced (the server's per-kind validation, SPECIFICATION.md Part A.8 - int -> float is a blanket accept)", async () => {
                // A whole number in [min, max], distinct from the current value - which would
                // legitimately resubmit as Unchanged - and from any declared special, which is
                // simply outside this test's intent. The three rounded candidates always find one.
                const wrongShapeBase = [Math.round(mid), Math.round(min), Math.round(max)].find(
                    (v) => v >= min && v <= max && v !== currentValue && !specialMagnitudes.has(v),
                );
                const { status, getBody } = await putAndGet(testCase, numberLiteral(/** @type {number} */ (wrongShapeBase), false));
                expect(status).toBe("Valid");
                expect(currentValueIn(getBody, testCase)).toBe(wrongShapeBase);
            });
        } else {
            it("rejects a decimal-point (fractional) literal for this int-typed field: Invalid, not truncated (the server's per-kind validation, SPECIFICATION.md Part A.8)", async () => {
                // Math.round() guarantees a genuine whole number to start from, regardless of
                // whether (max - min) happens to be odd (which would otherwise leave `mid` itself
                // already fractional).
                const wrongShapeBase = Math.round(mid);
                const literal = `${wrongShapeBase}.5`;
                const { status, getBody } = await putAndGet(testCase, literal);
                expect(status).toBe("Invalid");
                expect(currentValueIn(getBody, testCase)).toBe(currentValue);
            });
        }
    }

    if (field.kind === "string") {
        const minLength = field.minLength ?? 0;
        const { maxLength } = /** @type {{maxLength: number}} */ (field);
        const validLengths = [...new Set([Math.max(minLength, 1), Math.min(minLength + 3, maxLength), maxLength])];

        // Lengths, not strings - see live-backend-put-matrix.test.js's own note. This copy never
        // wedged a run only because it has no failure-screenshot path; the oversized test name is
        // identical, so it is fixed alongside rather than left as the next one to bite.
        it.each(validLengths.filter((len) => validStringValue(field, len) !== currentValue))(
            "accepts a %s-char string (a valid value distributed across the length range): Valid, and it gets persisted",
            async (len) => {
                const value = validStringValue(field, len);
                const { status, getBody } = await putAndGet(testCase, literalOf(value));
                expect(status).toBe("Valid");
                expect(currentValueIn(getBody, testCase)).toBe(value);
            },
        );

        // A too-short probe that is a declared special (MQTTHost's "" at minLength 1) is accepted by design, as the
        // number branch steps past its specials; mock-server.test.js pins a string special before its bounds.
        const tooShort = "x".repeat(Math.max(minLength - 1, 0));
        if (minLength > 0 && !(field.specialValues ?? []).some((special) => special.value === tooShort)) {
            it("rejects a too-short string: Invalid, not persisted", async () => {
                const { status, getBody } = await putAndGet(testCase, literalOf(tooShort));
                expect(status).toBe("Invalid");
                expect(currentValueIn(getBody, testCase)).toBe(currentValue);
            });
        }
        it("rejects a too-long string: Invalid, not persisted", async () => {
            const { status, getBody } = await putAndGet(testCase, literalOf("x".repeat(maxLength + 1)));
            expect(status).toBe("Invalid");
            expect(currentValueIn(getBody, testCase)).toBe(currentValue);
        });
    }

    if (field.kind === "enum") {
        const options = field.options ?? [];
        const firstOptionValue = options[0]?.value;
        it.each(options.map((o) => o.value).filter((v) => v !== currentValue))(
            "accepts option %s (a valid value distributed across the option set): Valid, and it gets persisted",
            async (value) => {
                const { status, getBody } = await putAndGet(testCase, literalOf(value));
                expect(status).toBe("Valid");
                expect(currentValueIn(getBody, testCase)).toBe(value);
            },
        );

        it("rejects a value that isn't one of the declared options: Invalid, not persisted", async () => {
            const bogus = typeof firstOptionValue === "number" ? -999999 : "not-a-real-option";
            const { status, getBody } = await putAndGet(testCase, literalOf(bogus));
            expect(status).toBe("Invalid");
            expect(currentValueIn(getBody, testCase)).toBe(currentValue);
        });

        if (typeof firstOptionValue === "number") {
            it("rejects a fractional value for this numeric enum field: Invalid, not persisted (mock-server.js's coerceAndValidate() enum branch, SPECIFICATION.md Part A.8 - every declared numeric enum is itself a plain int field server-side)", async () => {
                // Every currently-declared numeric enum's own real options are whole numbers
                // (BMP3XX's oversampling/filter settings) - a fractional value can never coincide
                // with one, so this is unconditionally a genuine rejection, not an accidental match.
                const fractional = firstOptionValue + 0.5;
                const { status, getBody } = await putAndGet(testCase, literalOf(fractional));
                expect(status).toBe("Invalid");
                expect(currentValueIn(getBody, testCase)).toBe(currentValue);
            });
        }
    }

    if (field.kind === "toggle") {
        it.each([true, false].filter((v) => v !== currentValue))("accepts %s: Valid, and it gets persisted", async (value) => {
            const { status, getBody } = await putAndGet(testCase, literalOf(value));
            expect(status).toBe("Valid");
            expect(currentValueIn(getBody, testCase)).toBe(value);
        });
    }
});

// The live PUT matrix runs as parallel CI shards (see .github/workflows/ci.yml's web-put-matrix and
// live-backend-put-matrix.test.js). A shard split that drops or doubles a case would silently shrink
// that matrix, so the partition itself is proven here rather than trusted.
describe("shardPutFieldCases", () => {
    const [firstDevice] = DEVICE_IDS;
    const device = /** @type {string} */ (firstDevice);
    const { defs, data } = deviceUnderTest(device);
    const cases = collectPutFieldCases(device, defs, data);

    it("returns every case when no shard is requested", () => {
        expect(shardPutFieldCases(cases, undefined)).toEqual(cases);
        expect(shardPutFieldCases(cases, "")).toEqual(cases);
    });

    it.each([1, 2, 3, 7])("partitions the full case list exactly once across %i shards", (count) => {
        const shards = Array.from({ length: count }, (_unused, i) => shardPutFieldCases(cases, `${i + 1}/${count}`));
        expect(shards.flat()).toHaveLength(cases.length);
        expect(new Set(shards.flat())).toEqual(new Set(cases));
        expect(Math.max(...shards.map((s) => s.length)) - Math.min(...shards.map((s) => s.length))).toBeLessThanOrEqual(1);
    });

    it.each(["0/3", "4/3", "3", "a/b", "1/0"])("rejects the malformed shard spec %s", (spec) => {
        expect(() => shardPutFieldCases(cases, spec)).toThrow(/shard spec/);
    });
});

/**
 * One valid value for a never-"Unchanged" field: a number's minimum, a toggle's true, an enum's first option.
 * @param {FieldDef} field
 * @returns {unknown}
 */
function validActionValue(field) {
    if (field.kind === "toggle") {
        return true;
    }
    if (field.kind === "enum") {
        return field.options?.[0]?.value;
    }
    return field.min;
}

// The never-"Unchanged" class (neverUnchanged()): an action is re-run and an always-executed field
// re-applied on every send, so a repeated identical value answers Valid both times. The composite
// LED command keeps its own tests; /status's ResetErrors answers no per-field result here.
const NEVER_UNCHANGED_CASES = dedupePutFieldCases(DEVICE_IDS.flatMap((device) => {
    const { defs, data } = deviceUnderTest(device);
    return defs.sections
        .filter((section) => section.key !== "status" && section.rest.put !== undefined)
        .flatMap((section) => section.groups.flatMap((group) => ("fields" in group ? group.fields : [])
            .filter((field) => neverUnchanged(field) && field.kind !== "composite")
            .map((field) => ({ device, defs, data, sectionKey: section.key, groupKey: group.key, field, putPath: /** @type {string} */ (section.rest.put), currentValue: undefined }))));
}));

describe.each(NEVER_UNCHANGED_CASES)("PUT $device $sectionKey/$groupKey/$field.key (never Unchanged)", (testCase) => {
    it("two identical valid sends both answer Valid", async () => {
        const literal = JSON.stringify(validActionValue(testCase.field));
        const first = await putAndGet(testCase, literal);
        const second = await putAndGet(testCase, literal);
        expect([first.status, second.status]).toEqual(["Valid", "Valid"]);
    });
});

describe("dedupePutFieldCases", () => {
    const [firstDevice] = DEVICE_IDS;
    const device = /** @type {string} */ (firstDevice);
    const { defs, data } = deviceUnderTest(device);
    const [first] = collectPutFieldCases(device, defs, data);

    it("keeps a field differing in any attribute and drops an identical one from a later device", () => {
        const base = /** @type {import("./_put_field_cases.js").PutFieldCase} */ (first);
        const identical = { ...base, device: "later-device" };
        const changed = { ...base, device: "later-device", field: { ...base.field, label: `${base.field.label} (changed)` } };
        expect(dedupePutFieldCases([base, identical, changed])).toEqual([base, changed]);
    });

    it("treats an instance's key as its driver's, so a second instance of one driver is deduplicated too", () => {
        const base = /** @type {import("./_put_field_cases.js").PutFieldCase} */ (first);
        const instance = { ...base, groupKey: `${base.groupKey}_second` };
        expect(dedupePutFieldCases([base, instance])).toEqual([base]);
    });
});
