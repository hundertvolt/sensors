/**
 * Field-by-field PUT matrix through a real browser against a real twin, for every writable field of
 * every device's generated definitions (SPECIFICATION.md Part H.7).
 */
import { commands } from "vitest/browser";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { neverUnchanged } from "../js/definitions.js";
import { expectedDisplay } from "./_expected_display.js";
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
// @tunable l0.put_matrix_case_timeout_ms = 15000
const CASE_TIMEOUT_MS = 15000;

/**
 * The value the twin holds for `testCase`'s field right now, read straight from its GET (undefined when absent).
 * @param {PutFieldCase} testCase
 * @returns {Promise<unknown>}
 */
async function readCurrentValue({ sectionKey, groupKey, field, putPath }) {
    const real = await commands.getRealCurrentValues([putPath]);
    const body = /** @type {Record<string, unknown>} */ (real[putPath]);
    const scoped = sectionKey === "sensors" ? /** @type {Record<string, unknown> | undefined} */ (body[groupKey]) : body;
    return scoped?.[field.key];
}

/**
 * The value a never-"Unchanged" field is sent with: On for a toggle (a dispatch toggle acts only when On, an
 * always-executed one is sent whenever set), an enum's first option, a number's minimum.
 * @param {FieldDef} field
 * @returns {unknown}
 */
function actionValue(field) {
    if (field.kind === "toggle") {
        return true;
    }
    if (field.kind === "enum") {
        return field.options?.[0]?.value;
    }
    return field.min;
}

/**
 * The confirmation the page asks before sending `value` for a `confirm` field: an enum names the option, a toggle
 * its card's submit label (SPECIFICATION.md Part H.4).
 * @param {PutFieldCase} testCase
 * @param {unknown} value
 * @returns {string}
 */
function confirmationFor({ defs, sectionKey, groupKey, field }, value) {
    if (field.kind === "enum") {
        return `${(field.options ?? []).find((option) => option.value === value)?.label ?? String(value)}?`;
    }
    const group = defs.sections.find((section) => section.key === sectionKey)?.groups.find((candidate) => candidate.key === groupKey);
    return `${(group && "submitLabel" in group ? group.submitLabel : undefined) ?? field.label}?`;
}

/**
 * The status section's group holding `fieldKey`, or its errcount group when `fieldKey` is null.
 * @param {SiteDefinitions} defs
 * @param {string | null} fieldKey
 * @returns {string}
 */
function statusGroupKey(defs, fieldKey) {
    const status = defs.sections.find((section) => section.key === "status");
    const group = status?.groups.find((candidate) => (fieldKey === null ? "kind" in candidate && candidate.kind === "errcount" : "fields" in candidate && candidate.fields.some((field) => field.key === fieldKey && field.kind === "readonly")));
    if (group === undefined) {
        throw new Error(`the status section has no group for ${fieldKey ?? "the error counts"}`);
    }
    return group.key;
}

/**
 * Sets every backup interval to "Backups off" through the page. The twin has no NTP, so each SGP40 backup warns (once a
 * minute by default): the one counter that climbs by itself, which a reset's all-zero read would otherwise race.
 * @param {SiteDefinitions} defs
 */
async function turnBackupsOff(defs) {
    const sensors = defs.sections.find((section) => section.key === "sensors");
    const cards = (sensors?.groups ?? []).flatMap((group) => ("fields" in group ? group.fields : []).filter((field) => field.key === "BackupPeriod").map((field) => ({ groupKey: group.key, field })));
    for (const { groupKey, field } of cards) {
        const off = field.specialValues?.find((special) => special.meaning === "Backups off");
        expect(off, `${groupKey}'s BackupPeriod declares no "Backups off" value`).toBeDefined();
        const value = off?.value;
        // eslint-disable-next-line no-await-in-loop -- one card after another, as a visitor applies them
        const applied = await commands.applyField({ sectionKey: "sensors", groupKey, fieldKey: field.key, field, value, expectRenderedValue: value, readCaption: false });
        expect(["valid", "unchanged"]).toContain(applied.applyStatus);
    }
}

// The four action fields' probes, run in this order: mempause holds storage for five minutes, and a ResetErrors after
// it answers Failed (the FRAM logs cannot be cleared then). Reboot, bootloader, resetconfig and erasefram end the
// twin process: covered by the unit tier's shutdown scenarios (reboot on silicon too), not driven here.
/** @type {Record<string, (testCase: PutFieldCase) => Promise<void>>} */
const ACTION_PROBES = {
    async ResetErrors(testCase) {
        const { device, defs, sectionKey, groupKey, field } = testCase;
        // A backup round that read its interval before this PUT ends long before the reset, two served requests later.
        await turnBackupsOff(defs);
        const archived = await commands.archiveErrcount(`${device}-before-reset`);
        expect(archived).toContain(`build/archive/live_twin/`);
        const applied = await commands.applyField({ sectionKey, groupKey, fieldKey: field.key, field, value: true, expectRenderedValue: null, confirmMessage: confirmationFor(testCase, true), readCaption: false });
        expect(applied.applyStatus).toBe("valid");
        const { errcountRows } = await commands.remountAndReadField({ sectionKey: "status", groupKey: statusGroupKey(defs, null), fieldKey: "", kind: "errcount" });
        expect(errcountRows.length).toBeGreaterThan(0);
        expect(errcountRows.filter((row) => !row.endsWith(": 0"))).toEqual([]);
    },
    async LightCmdLED({ sectionKey, groupKey, field }) {
        const args = { sectionKey, groupKey, fieldKey: field.key, field, expectRenderedValue: null, readCaption: false };
        // Lit for ten seconds, so the second send - a navigation and two page requests later - lands while it runs.
        const lit = await commands.applyField({ ...args, value: { R: 10, G: 20, B: 30, T: 10 } });
        const busy = await commands.applyField({ ...args, value: { R: 10, G: 20, B: 30, T: 10 } });
        const outOfRange = await commands.applyField({ ...args, value: { R: 256, G: 20, B: 30, T: 10 } });
        expect([lit.applyStatus, busy.applyStatus, outOfRange.applyStatus]).toEqual(["valid", "failed", "invalid"]);
    },
    async PauseTime({ defs, sectionKey, groupKey, field }) {
        const args = { sectionKey, groupKey, fieldKey: field.key, field, expectRenderedValue: null, readCaption: false };
        const first = await commands.applyField({ ...args, value: 5 });
        const second = await commands.applyField({ ...args, value: 5 });
        const shown = await commands.remountAndReadField({ sectionKey: "status", groupKey: statusGroupKey(defs, field.key), fieldKey: field.key, kind: "readonly" });
        const tooLong = await commands.applyField({ ...args, value: 3601 });
        expect([first.applyStatus, second.applyStatus, tooLong.applyStatus]).toEqual(["valid", "valid", "invalid"]);
        const remaining = Number.parseInt(shown.valueText ?? "", 10);
        expect(remaining >= 1 && remaining <= 5, `Remaining Pause Time read ${String(shown.valueText)}`).toBe(true);
    },
    async SystemCmd(testCase) {
        const { sectionKey, groupKey, field } = testCase;
        const applied = await commands.applyField({ sectionKey, groupKey, fieldKey: field.key, field, value: "mempause", expectRenderedValue: null, confirmMessage: confirmationFor(testCase, "mempause"), readCaption: false });
        expect(applied.applyStatus).toBe("valid");
    },
};

/**
 * The action fields the live tier drives itself, each with its own probe below; a field another device lacks is
 * simply not collected for it.
 * @param {string} device
 * @returns {PutFieldCase[]}
 */
function actionCasesOf(device) {
    const defs = /** @type {SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device));
    const order = Object.keys(ACTION_PROBES);
    return defs.sections.flatMap((section) => section.groups.flatMap((group) => ("fields" in group && group.submit ? group.fields : [])
        .filter((field) => order.includes(field.key))
        .map((field) => ({ device, defs, sectionKey: section.key, groupKey: group.key, field, putPath: /** @type {string} */ (section.rest.put), currentValue: undefined }))))
        .sort((a, b) => order.indexOf(a.field.key) - order.indexOf(b.field.key));
}

const config = await commands.getLiveMatrixConfig();
// Sharded in CI only, via $PUT_MATRIX_SHARD relayed by getLiveMatrixConfig(): this one file is
// most of the web tier's wall clock, so parallel shards keep it clear of its own budget. Unset
// locally, so `npm test` and `npm run test:put-matrix` still run every case.
const CASES = shardPutFieldCases(dedupePutFieldCases(DEVICE_IDS.flatMap((device) => collectPutFieldCases(device, /** @type {SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device)), NO_DATA))), config.shard);
// The never-"Unchanged" class of the sensors section (the action fields of the other sections have their own
// probes above): two identical sends, both Valid.
const NEVER_UNCHANGED_CASES = shardPutFieldCases(dedupePutFieldCases(DEVICE_IDS.flatMap((device) => {
    const defs = /** @type {SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device));
    return defs.sections
        .filter((section) => section.key === "sensors")
        .flatMap((section) => section.groups.flatMap((group) => ("fields" in group ? group.fields : [])
            .filter((field) => neverUnchanged(field) && field.kind !== "composite")
            .map((field) => ({ device, defs, sectionKey: section.key, groupKey: group.key, field, putPath: /** @type {string} */ (section.rest.put), currentValue: undefined }))));
})), config.shard);
const ACTION_CASES = shardPutFieldCases(DEVICE_IDS.flatMap(actionCasesOf), config.shard);
const devicesWithCases = [...new Set([...CASES, ...NEVER_UNCHANGED_CASES, ...ACTION_CASES].map((testCase) => testCase.device))];

describe.each(devicesWithCases)("live PUT matrix on %s", (device) => {
    beforeAll(async () => {
        await commands.startLiveMatrix(device);
    });
    afterAll(async () => {
        await commands.stopLiveMatrix();
    });

    describe.each(CASES.filter((testCase) => testCase.device === device))("live PUT $sectionKey/$groupKey/$field.key ($field.kind)", (testCase) => {
        const { sectionKey, groupKey, field, defs } = testCase;
        /** @param {unknown} value */
        const shown = (value) => expectedDisplay(field, value, defs.defaultDecimals);

        /**
         * Fills+applies `value` through the real UI expecting exactly `expectedStatus`, then confirms it rendered
         * both same-view and after a full remount (SPECIFICATION.md Part H.3: a poll never repaints an editable
         * toggle or select; the remount proves the value reads back from the device, not the page's own state).
         * @param {unknown} value
         * @param {"valid" | "unchanged"} expectedStatus
         */
        async function applyAndExpectRendered(value, expectedStatus) {
            const applied = await commands.applyField({ sectionKey, groupKey, fieldKey: field.key, field, value, expectRenderedValue: value, defaultDecimals: defs.defaultDecimals });
            expect(applied.applyStatus).toBe(expectedStatus);

            const remounted = await commands.remountAndReadField({ sectionKey, groupKey, fieldKey: field.key, kind: field.kind });
            if (field.kind === "number" || field.kind === "string") {
                expect(applied.captionText).toBe(`Current value: ${shown(value)}`);
                expect(remounted.placeholder).toBe(shown(value));
            } else if (field.kind === "toggle") {
                expect(applied.toggleValue).toBe(String(Boolean(value)));
                expect(remounted.toggleValue).toBe(String(Boolean(value)));
            } else if (field.kind === "enum") {
                expect(applied.selectValue).toBe(String(value));
                expect(remounted.selectValue).toBe(String(value));
            }
        }

        /**
         * Fills+applies `value` expecting real rejection, then confirms the render never moved off the field's
         * current value (a rejected value is never shown as if accepted), same-view and after a remount.
         * @param {unknown} value
         */
        async function applyAndExpectRejected(value) {
            const current = await readCurrentValue(testCase);
            const applied = await commands.applyField({ sectionKey, groupKey, fieldKey: field.key, field, value, expectRenderedValue: current, defaultDecimals: defs.defaultDecimals });
            expect(applied.applyStatus).toBe("invalid");

            const remounted = await commands.remountAndReadField({ sectionKey, groupKey, fieldKey: field.key, kind: field.kind });
            if (field.kind === "number" || field.kind === "string") {
                expect(applied.captionText).toBe(`Current value: ${shown(current)}`);
                expect(remounted.placeholder).toBe(shown(current));
            }
        }

        /**
         * Applies `value` expecting exactly "unchanged" when the twin already holds it, else "valid".
         * @param {unknown} value
         */
        async function applyExpectingItsWord(value) {
            const current = await readCurrentValue(testCase);
            await applyAndExpectRendered(value, value === current ? "unchanged" : "valid");
        }

        // An empty-string current value has no "resubmit" gesture: typing nothing is
        // indistinguishable from untouched under the sparse-PUT convention (Part H.4).

        // Nor does a masked field: it reads back as the mask, never the stored credential, so a resubmit would be a new
        // password the twin persists (the page never sends a mask: render.test.js). A case with no resubmit gesture
        // skips visibly once its current value is read.
        /** @param {unknown} current */
        const hasNoResubmitGesture = (current) => current === undefined || (field.kind === "string" && current === "");
        if (field.mask !== true) {
            // An unchanged toggle or enum is sparse-omitted, so it never round-trips; a number or string is sent
            // whenever typed, and a dispatch field always is.
            const willRoundTrip = field.kind === "number" || field.kind === "string" || field.dispatch === true;
            if (willRoundTrip) {
                it(
                    "resubmitting the field's own current value renders it, answered Unchanged",
                    async (ctx) => {
                        const current = await readCurrentValue(testCase);
                        ctx.skip(hasNoResubmitGesture(current), "no current value to resubmit");
                        await applyAndExpectRendered(current, "unchanged");
                    },
                    CASE_TIMEOUT_MS,
                );
            } else {
                it(
                    "resubmitting the field's own current value is sparse-omitted (nothing to submit, no round trip)",
                    async (ctx) => {
                        const current = await readCurrentValue(testCase);
                        ctx.skip(hasNoResubmitGesture(current), "no current value to resubmit");
                        const result = await commands.applyUnchangedFieldExpectNothingToSubmit({
                            sectionKey,
                            groupKey,
                            fieldKey: field.key,
                            kind: /** @type {"toggle" | "enum"} */ (field.kind),
                            value: current,
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

            // Rounded to 2 decimal places: SCD30's TempOffset is stored in 0.01° ticks, rounding to the
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
                        await applyExpectingItsWord(Math.round(mid) + 0.5);
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
                await applyExpectingItsWord(value);
            });

            for (const special of field.specialValues ?? []) {
                it(
                    `accepts the declared special value ${special.value} ("${special.meaning}"), rendered correctly`,
                    () => applyExpectingItsWord(special.value),
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
            // name, from which vitest derives a screenshot filename - and NTPHost's maxLength
            // 1024 made that ENAMETOOLONG, wedging a run until the job's own cap killed it.
            it.each(validLengths)(
                "accepts a %s-char string (a valid value distributed across the length range), rendered correctly",
                async (len) => {
                    await applyExpectingItsWord(validStringValue(field, len));
                },
                CASE_TIMEOUT_MS,
            );
        }

        if (field.kind === "toggle") {
            it(
                "flipping to the opposite state renders Valid with the new state actually shown",
                async () => {
                    await applyAndExpectRendered(!(await readCurrentValue(testCase)), "valid");
                },
                CASE_TIMEOUT_MS,
            );
        }

        if (field.kind === "enum") {
            // Selecting the option already shown is the resubmit case, whose own probe above knows
            // whether the card round-trips at all; here it would wait for an answer that never comes.
            it.for((field.options ?? []).map((o) => o.value))("selecting option %s renders Valid with that option actually shown selected", async (value, ctx) => {
                ctx.skip(value === (await readCurrentValue(testCase)), "the current option: the resubmit probe covers it");
                await applyAndExpectRendered(value, "valid");
            });
        }
    });

    describe.each(NEVER_UNCHANGED_CASES.filter((testCase) => testCase.device === device))("live PUT $sectionKey/$groupKey/$field.key (never Unchanged)", (testCase) => {
        const { sectionKey, groupKey, field, defs } = testCase;
        it(
            "two identical valid sends both answer Valid",
            async () => {
                const value = actionValue(field);
                const args = { sectionKey, groupKey, fieldKey: field.key, field, value, expectRenderedValue: value, defaultDecimals: defs.defaultDecimals, readCaption: false };
                const first = await commands.applyField(args);
                const second = await commands.applyField(args);
                expect([first.applyStatus, second.applyStatus]).toEqual(["valid", "valid"]);
            },
            CASE_TIMEOUT_MS,
        );
    });

    describe.each(ACTION_CASES.filter((testCase) => testCase.device === device))("live action $sectionKey/$groupKey/$field.key", (testCase) => {
        it(
            "answers each send with its exact word through the page, its confirmation accepted",
            () => /** @type {(testCase: PutFieldCase) => Promise<void>} */ (ACTION_PROBES[testCase.field.key])(testCase),
            CASE_TIMEOUT_MS,
        );
    });
});
