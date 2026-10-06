/**
 * Field-by-field PUT matrix through a real browser against a real twin, for every writable field of
 * every device's generated definitions (SPECIFICATION.md Part H.7).
 */
import { commands } from "vitest/browser";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { neverUnchanged } from "../js/definitions.js";
import { formatFieldValue } from "../js/field-format.js";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";
import { collectPutFieldCases, dedupePutFieldCases, shardPutFieldCases, validStringValue } from "./_put_field_cases.js";

/** @typedef {import("./_put_field_cases.js").PutFieldCase} PutFieldCase */
/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */

// Cases come from the definitions alone; each case reads its current value from the live twin.
const NO_DATA = /** @type {import("../js/definitions.js").MockDeviceData} */ ({
    measurements: {}, sensorsConfig: {}, networkingConfig: {}, systemConfig: {}, notificationConfig: {},
    status: { networking: {}, system: {}, sensors: {}, notification: {}, errcount: {} },
});

// Generous per-case ceiling: one real nav-drawer click, one real fill/select/toggle, one real
// Apply click, a data-apply-status poll, and (for most cases) a second real remount+read - all
// against a local twin, but under real browser/event-loop scheduling.
const CASE_TIMEOUT_MS = 15000;

/**
 * True if this group carries a `dispatch: true` field, which collectGroupBody() always
 * resubmits - keeping every Apply a real round trip, so a resubmit-unchanged probe still gets an
 * answer. Without one the field is sparse-omitted, so this picks which command a case uses.
 * @param {SiteDefinitions} defs
 * @param {string} sectionKey
 * @param {string} groupKey
 * @returns {boolean}
 */
function groupHasDispatchField(defs, sectionKey, groupKey) {
    const section = defs.sections.find((s) => s.key === sectionKey);
    const group = section?.groups.find((g) => "fields" in g && g.key === groupKey);
    return group !== undefined && "fields" in group && group.fields.some((f) => f.dispatch === true);
}

/**
 * The value the real UI starts from for `testCase`: its live GET value, else the field's own
 * defaultValue (resolveFieldValue()'s fallback, Part H.5).
 * @param {PutFieldCase} testCase
 * @returns {Promise<unknown>}
 */
async function readCurrentValue({ sectionKey, groupKey, field, putPath }) {
    const real = await commands.getRealCurrentValues([putPath]);
    const body = /** @type {Record<string, unknown>} */ (real[putPath] ?? {});
    const scoped = sectionKey === "sensors" ? /** @type {Record<string, unknown> | undefined} */ (body[groupKey]) : body;
    const value = scoped?.[field.key];
    return value === undefined ? field.defaultValue : value;
}

/**
 * The value a never-"Unchanged" field is sent with: a toggle in the state its card does not
 * already show (so the Apply carries it), an enum's first option, a number's minimum.
 * @param {FieldDef} field
 * @returns {unknown}
 */
function actionValue(field) {
    if (field.kind === "toggle") {
        return field.dispatch === true ? true : !field.defaultValue;
    }
    if (field.kind === "enum") {
        return field.options?.[0]?.value;
    }
    return field.min;
}

const config = await commands.getLiveMatrixConfig();
// Sharded in CI only, via $PUT_MATRIX_SHARD relayed by getLiveMatrixConfig(): this one file is
// most of the web tier's wall clock, so parallel shards keep it clear of its own budget. Unset
// locally, so `npm test` and `npm run test:put-matrix` still run every case.
const CASES = config.skipped
    ? []
    : shardPutFieldCases(dedupePutFieldCases(DEVICE_IDS.flatMap((device) => collectPutFieldCases(device, /** @type {SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device)), NO_DATA))), config.shard);
// The never-"Unchanged" class of the sensors and notification sections (a system command would
// restart the twin; the composite LED command keeps its own tests): two identical sends, both Valid.
const NEVER_UNCHANGED_CASES = config.skipped
    ? []
    : shardPutFieldCases(dedupePutFieldCases(DEVICE_IDS.flatMap((device) => {
        const defs = /** @type {SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device));
        return defs.sections
            .filter((section) => section.key === "sensors" || section.key === "notification")
            .flatMap((section) => section.groups.flatMap((group) => ("fields" in group ? group.fields : [])
                .filter((field) => neverUnchanged(field) && field.kind !== "composite")
                .map((field) => ({ device, defs, sectionKey: section.key, groupKey: group.key, field, putPath: /** @type {string} */ (section.rest.put), currentValue: undefined }))));
    })), config.shard);
const devicesWithCases = [...new Set([...CASES, ...NEVER_UNCHANGED_CASES].map((testCase) => testCase.device))];

if (config.skipped) {
    it.skip(`live-backend PUT matrix (skipped: ${config.reason})`, () => { /* never runs: a skipped placeholder needs no body */ });
}

describe.each(devicesWithCases)("live PUT matrix on %s", (device) => {
    beforeAll(async () => {
        await commands.startLiveMatrix(device);
    });
    afterAll(async () => {
        await commands.stopLiveMatrix();
    });

    describe.each(CASES.filter((testCase) => testCase.device === device))("live PUT $sectionKey/$groupKey/$field.key ($field.kind)", (testCase) => {
        const { sectionKey, groupKey, field } = testCase;
        /** @type {unknown} */
        let currentValue;
        beforeAll(async () => {
            currentValue = await readCurrentValue(testCase);
        });

        /**
         * Fills+applies `value` through the real UI, then confirms it rendered correctly both
         * same-view and after a full remount (SPECIFICATION.md Part H.3: only number/string
         * captions self-refresh in place, so a remount is the only proof for toggle/enum).
         * @param {unknown} value
         * @param {"Valid" | "ValidOrUnchanged"} expectedStatus "ValidOrUnchanged" tolerates either
         * outcome for a resubmit case - a stored field answers "Unchanged", while one carried out on
         * every send (SCD30's AmbPres and ForceCalRef, a dispatch field) answers "Valid"
         * (SPECIFICATION.md Part H.7).
         */
        async function applyAndExpectRendered(value, expectedStatus) {
            // Every field here reads back what was applied: the never-"Unchanged" ones, whose GET
            // may not (Part H.7), leave the generic cases for their own category below.
            const expectedRemountValue = value;

            const applied = await commands.applyField({ sectionKey, groupKey, fieldKey: field.key, field, value, expectRenderedValue: expectedRemountValue });
            if (expectedStatus === "ValidOrUnchanged") {
                expect(["valid", "unchanged"]).toContain(applied.applyStatus);
            } else {
                expect(applied.applyStatus).toBe("valid");
            }

            const remounted = await commands.remountAndReadField({ sectionKey, groupKey, fieldKey: field.key, kind: field.kind });
            if (field.kind === "number" || field.kind === "string") {
                const expectedCaption = `Current value: ${formatFieldValue(field, expectedRemountValue)}`;
                expect(applied.captionText).toBe(expectedCaption);
                expect(remounted.placeholder).toBe(formatFieldValue(field, expectedRemountValue));
            } else if (field.kind === "toggle") {
                expect(applied.toggleValue).toBe(String(Boolean(value)));
                expect(remounted.toggleValue).toBe(String(Boolean(expectedRemountValue)));
            } else if (field.kind === "enum") {
                expect(applied.selectValue).toBe(String(value));
                expect(remounted.selectValue).toBe(String(expectedRemountValue));
            }
            currentValue = expectedRemountValue;
        }

        /**
         * Fills+applies `value` expecting real rejection, then confirms the render never moved off
         * whatever `currentValue` genuinely is right now (proving a rejected value is never shown
         * as if it had been accepted) via the same same-view + remount pair as the accept path.
         * @param {unknown} value
         */
        async function applyAndExpectRejected(value) {
            const applied = await commands.applyField({ sectionKey, groupKey, fieldKey: field.key, field, value, expectRenderedValue: currentValue });
            expect(applied.applyStatus).toBe("invalid");

            const remounted = await commands.remountAndReadField({ sectionKey, groupKey, fieldKey: field.key, kind: field.kind });
            if (field.kind === "number" || field.kind === "string") {
                const expectedCaption = `Current value: ${formatFieldValue(field, currentValue)}`;
                expect(applied.captionText).toBe(expectedCaption);
                expect(remounted.placeholder).toBe(formatFieldValue(field, currentValue));
            }
        }

        // An empty-string current value has no "resubmit" gesture: typing nothing is
        // indistinguishable from untouched under the sparse-PUT convention (Part H.4).

        // Nor does a masked field: PW reads back as the fixed "********" overlay, never the
        // stored credential, so resubmitting it is not a no-op probe but a new password the
        // backend would persist - overwriting the twin's real Wi-Fi credential mid-run.
        // A case with no resubmit gesture (above) skips visibly once its current value is read.
        const hasNoResubmitGesture = () => currentValue === undefined || (field.kind === "string" && currentValue === "");
        if (field.mask !== true) {
            // A non-dispatch toggle or enum resubmitted unchanged is sparse-omitted, so no round
            // trip fires unless a dispatch sibling keeps the shared card's body non-empty.
            // number/string are unaffected: applyAndExpectRendered() always fills a real value.
            const willRoundTrip =
                field.kind === "number" ||
                field.kind === "string" ||
                field.dispatch === true ||
                groupHasDispatchField(testCase.defs, sectionKey, groupKey);
            if (willRoundTrip) {
                it(
                    "resubmitting the field's own current value renders correctly (Valid or Unchanged)",
                    async (ctx) => {
                        ctx.skip(hasNoResubmitGesture(), "no current value to resubmit");
                        await applyAndExpectRendered(currentValue, "ValidOrUnchanged");
                    },
                    CASE_TIMEOUT_MS,
                );
            } else {
                it(
                    "resubmitting the field's own current value is sparse-omitted (nothing to submit, no round trip)",
                    async (ctx) => {
                        ctx.skip(hasNoResubmitGesture(), "no current value to resubmit");
                        const result = await commands.applyUnchangedFieldExpectNothingToSubmit({
                            sectionKey,
                            groupKey,
                            fieldKey: field.key,
                            kind: /** @type {"toggle" | "enum"} */ (field.kind),
                            value: currentValue,
                        });
                        expect(result.resultText).toBe("Nothing to submit - no fields were changed.");
                        expect(result.applyStatus).toBeNull();
                    },
                    CASE_TIMEOUT_MS,
                );
            }
        }

        if (field.kind === "number") {
            const { min, max } = /** @type {{min: number, max: number}} */ (field);
            const mid = min + (max - min) / 2;
            // wholeRange (cosmetic probe-value shape) and isFloat (the real accept/reject-fractional
            // decision) are deliberately separate flags - WarnHum's range is whole-numbered but the
            // field is float-typed, so conflating them wrongly rejects its valid fractional literal.
            const wholeRange = Number.isInteger(min) && Number.isInteger(max);
            const isFloat = field.float === true;
            const step = wholeRange ? 1 : 0.5;
            const specialMagnitudes = new Set((field.specialValues ?? []).map((s) => s.value));

            // Rounded to 2 decimal places: SCD30's TempOffs is stored in 0.01° ticks, rounding to the
            // nearest 0.01 (SPECIFICATION.md, near the ForceCalRef/AmbPres notes), which an unrounded mid
            // value would silently fail against; harmless for every other field.
            const validValues = [...new Set([min, mid, max].map((v) => (wholeRange ? Math.round(v) : Math.round(v * 100) / 100)))];

            /**
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
            const rejectValues = [...new Set([firstRejectable(min - step, -1), firstRejectable(max + step, 1)])];

            it.each(rejectValues)("rejects %s (out of range): real render stays at the field's own current value", async (value) => {
                await applyAndExpectRejected(value);
            });

            if (isFloat) {
                it(
                    "accepts a fractional literal for this float-typed field, rendered correctly",
                    async () => {
                        await applyAndExpectRendered(Math.round(mid) + 0.5, "Valid");
                    },
                    CASE_TIMEOUT_MS,
                );
            } else {
                it(
                    "rejects a decimal-point (fractional) literal for this int-typed field, not silently truncated",
                    async () => {
                        await applyAndExpectRejected(`${Math.round(mid)}.5`);
                    },
                    CASE_TIMEOUT_MS,
                );
            }

            it.each(validValues)("accepts %s (a valid value distributed across the range), rendered correctly", async (value) => {
                await applyAndExpectRendered(value, value === currentValue ? "ValidOrUnchanged" : "Valid");
            });

            // Declared outside the loop so the per-case body never closes over the loop itself:
            // `currentValue` is reassigned by applyAndExpectRendered() and must stay late-bound.
            /** @param {import("../js/definitions.js").SpecialValue} special */
            const specialValueProbe = (special) => async () => {
                await applyAndExpectRendered(special.value, special.value === currentValue ? "ValidOrUnchanged" : "Valid");
            };
            for (const special of field.specialValues ?? []) {
                it(
                    `accepts the declared special value ${special.value} ("${special.meaning}"), rendered correctly`,
                    specialValueProbe(special),
                    CASE_TIMEOUT_MS,
                );
            }
        }

        if (field.kind === "string") {
            const minLength = field.minLength ?? 0;
            const { maxLength } = /** @type {{maxLength: number}} */ (field);
            const validLengths = [...new Set([Math.max(minLength, 1), Math.min(minLength + 3, maxLength), maxLength])];

            // minLength === 1's own "too short" probe is the empty string - same untouched-input
            // ambiguity as the resubmit-"" skip above, so only minLength 2+ has a real probe to test.
            if (minLength > 1) {
                it(
                    "rejects a too-short string: real render stays at the field's own current value",
                    async () => {
                        await applyAndExpectRejected("x".repeat(minLength - 1));
                    },
                    CASE_TIMEOUT_MS,
                );
            }
            it(
                "rejects a too-long string: real render stays at the field's own current value",
                async () => {
                    await applyAndExpectRejected("x".repeat(maxLength + 1));
                },
                CASE_TIMEOUT_MS,
            );

            // Parametrised over LENGTHS, not the generated strings: `%s` goes into the test
            // name, from which vitest derives a screenshot filename - and NTP_Host's maxLength
            // 1024 made that ENAMETOOLONG, wedging a run until the job's own cap killed it.
            it.each(validLengths)(
                "accepts a %s-char string (a valid value distributed across the length range), rendered correctly",
                async (len) => {
                    const value = validStringValue(field, len);
                    await applyAndExpectRendered(value, value === currentValue ? "ValidOrUnchanged" : "Valid");
                },
                CASE_TIMEOUT_MS,
            );
        }

        if (field.kind === "toggle") {
            it(
                "flipping to the opposite state renders Valid with the new state actually shown",
                async () => {
                    await applyAndExpectRendered(!currentValue, "Valid");
                },
                CASE_TIMEOUT_MS,
            );
        }

        if (field.kind === "enum") {
            // Selecting the option already shown is the resubmit case, whose own probe above knows
            // whether the card round-trips at all; here it would wait for an answer that never comes.
            it.for((field.options ?? []).map((o) => o.value))("selecting option %s renders Valid with that option actually shown selected", async (value, ctx) => {
                ctx.skip(value === currentValue, "the current option: the resubmit probe covers it");
                await applyAndExpectRendered(value, "Valid");
            });
        }
    });

    describe.each(NEVER_UNCHANGED_CASES.filter((testCase) => testCase.device === device))("live PUT $sectionKey/$groupKey/$field.key (never Unchanged)", (testCase) => {
        const { sectionKey, groupKey, field } = testCase;
        it(
            "two identical valid sends both answer Valid",
            async () => {
                const value = actionValue(field);
                const args = { sectionKey, groupKey, fieldKey: field.key, field, value, expectRenderedValue: value };
                const first = await commands.applyField(args);
                const second = await commands.applyField(args);
                expect([first.applyStatus, second.applyStatus]).toEqual(["valid", "valid"]);
            },
            CASE_TIMEOUT_MS,
        );
    });
});
