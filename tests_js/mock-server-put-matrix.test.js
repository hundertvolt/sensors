/**
 * Exhaustive PUT-behavior matrix over every real writable field in both shipped devices'
 * definitions.json, run directly against js/mock-server.js's real fetch interception (no DOM).
 * Six categories per field (project owner's own request, verified against the real backend's
 * documented semantics - SPECIFICATION.md Part A.8/config_manager.py's coerce_numeric()/
 * type_or_range_error()):
 *   1. several valid values across the range -> "Valid"
 *   2. every declared special value -> "Valid"
 *   3. the field omitted from the PUT body (the sparse-PUT "untouched" case) -> not in the result,
 *      value not persisted
 *   4. the field's own current stored value resubmitted -> "Unchanged" (never reached for a
 *      dispatch-only action - SystemCmd/PauseTime/lightCmdLED/ResetErrors always report "Valid" on
 *      an identical resubmission; those are tested separately, not by this generic matrix)
 *   5. an out-of-range value (and, for a field with special values, one that matches neither the
 *      normal range nor any special value) -> "Invalid"
 *   6. a value of the wrong JSON type -> "Invalid" (any non-numeric text, for every field kind);
 *      for a "number"-kind field specifically, the real backend's own int<->float coercion policy
 *      is exercised too - a `field.float`-marked field accepts a bare-integer literal (a blanket
 *      accept, coerced), while a field not marked `field.float` still rejects a decimal-point
 *      (fractional) literal outright, never truncated
 *
 * Shared field kinds (SCD30/SGP40, networking, system, notification) are identical between wozi.json
 * and dev.json, so they're only exercised once (via wozi) to avoid pure duplication; dev.json's own
 * unique sensor groups (SHTC3/MPRLS/ISL29125) are exercised too, to prove the matrix generalizes
 * across enum-heavy and negative-special-value field shapes wozi's own sensors don't have.
 * Dispatch-only fields (SystemCmd/PauseTime/lightCmdLED/ResetErrors) and the composite lightCmdLED
 * shape have their own distinct Invalid/Failed/Valid semantics, already covered by dedicated tests
 * elsewhere (mock-server.test.js, render.test.js) - excluded from this generic matrix rather than
 * force-fit into categories that don't apply to them.
 */
import { describe, expect, it } from "vitest";
import wozi from "../html/definitions/wozi.json";
import dev from "../html/definitions/dev.json";
import woziData from "../mockdata/wozi.json";
import devData from "../mockdata/dev.json";
import { installMockFetch } from "../js/mock-server.js";
import { collectPutFieldCases } from "./_put_field_cases.js";

/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("../js/definitions.js").MockDeviceData} MockDeviceData */
/** @typedef {import("./_put_field_cases.js").PutFieldCase & {data: MockDeviceData}} PutFieldCase */

// Shared driver/module field sets - identical between devices, so only wozi's copy is exercised.
const DEV_UNIQUE_GROUPS = new Set(["SHTC3", "MPRLS", "ISL29125"]);

/**
 * @param {string} device
 * @param {SiteDefinitions} defs
 * @param {MockDeviceData} data
 * @returns {PutFieldCase[]}
 */
function collectMockPutFieldCases(device, defs, data) {
    return collectPutFieldCases(device, defs, data).map((c) => ({ ...c, data }));
}

const CASES = [
    ...collectMockPutFieldCases("wozi", /** @type {SiteDefinitions} */ (wozi), /** @type {MockDeviceData} */ (woziData)),
    ...collectMockPutFieldCases("dev", /** @type {SiteDefinitions} */ (dev), /** @type {MockDeviceData} */ (devData)).filter((c) => DEV_UNIQUE_GROUPS.has(c.groupKey)),
];

/**
 * Sends one raw PUT body (exact JSON text, so a test controls a number's literal int/float shape
 * precisely - something building a JS value and calling JSON.stringify() on it cannot do, since JS
 * itself has no int/float type distinction) against a fresh mock install, and returns that field's
 * own result plus a fresh GET of the same endpoint - all within one `installMockFetch()` lifetime,
 * since state only persists for the duration of one install.
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
        const min = /** @type {number} */ (field.min);
        const max = /** @type {number} */ (field.max);
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
            it("accepts a bare-integer literal for this float-typed field: Valid, coerced (config_manager.py's coerce_numeric(), SPECIFICATION.md Part A.8 - int -> float is a blanket accept)", async () => {
                // A whole number in [min, max], distinct from the field's own current value (else
                // this would legitimately resubmit-as-Unchanged instead) and from any declared
                // special (kept out of this test's own intent, even though a special would also
                // still just be Valid). Round(mid)/round(min)/round(max) between them always find
                // one for any real field's range.
                const wrongShapeBase = [Math.round(mid), Math.round(min), Math.round(max)].find(
                    (v) => v >= min && v <= max && v !== currentValue && !specialMagnitudes.has(v),
                );
                const { status, getBody } = await putAndGet(testCase, numberLiteral(/** @type {number} */ (wrongShapeBase), false));
                expect(status).toBe("Valid");
                expect(currentValueIn(getBody, testCase)).toBe(wrongShapeBase);
            });
        } else {
            it("rejects a decimal-point (fractional) literal for this int-typed field: Invalid, not truncated (config_manager.py's coerce_numeric() policy, SPECIFICATION.md Part A.8)", async () => {
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
        const maxLength = /** @type {number} */ (field.maxLength);
        const validLengths = [...new Set([Math.max(minLength, 1), Math.min(minLength + 3, maxLength), maxLength])];

        it.each(validLengths.map((len) => "x".repeat(len)).filter((v) => v !== currentValue))(
            "accepts a %s-char string (a valid value distributed across the length range): Valid, and it gets persisted",
            async (value) => {
                const { status, getBody } = await putAndGet(testCase, literalOf(value));
                expect(status).toBe("Valid");
                expect(currentValueIn(getBody, testCase)).toBe(value);
            },
        );

        if (minLength > 0) {
            it("rejects a too-short string: Invalid, not persisted", async () => {
                const { status, getBody } = await putAndGet(testCase, literalOf("x".repeat(minLength - 1)));
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
        it.each(options.map((o) => o.value).filter((v) => v !== currentValue))(
            "accepts option %s (a valid value distributed across the option set): Valid, and it gets persisted",
            async (value) => {
                const { status, getBody } = await putAndGet(testCase, literalOf(value));
                expect(status).toBe("Valid");
                expect(currentValueIn(getBody, testCase)).toBe(value);
            },
        );

        it("rejects a value that isn't one of the declared options: Invalid, not persisted", async () => {
            const bogus = typeof options[0]?.value === "number" ? -999999 : "not-a-real-option";
            const { status, getBody } = await putAndGet(testCase, literalOf(bogus));
            expect(status).toBe("Invalid");
            expect(currentValueIn(getBody, testCase)).toBe(currentValue);
        });

        if (typeof options[0]?.value === "number") {
            it("rejects a fractional value for this numeric enum field: Invalid, not persisted (mock-server.js's coerceAndValidate() enum branch, SPECIFICATION.md Part A.8 - every declared numeric enum is itself a plain int field server-side)", async () => {
                // Every currently-declared numeric enum's own real options are whole numbers
                // (BMP3XX's oversampling/filter settings) - a fractional value can never coincide
                // with one, so this is unconditionally a genuine rejection, not an accidental match.
                const fractional = /** @type {number} */ (options[0].value) + 0.5;
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
