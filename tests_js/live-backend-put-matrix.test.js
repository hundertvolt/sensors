/**
 * Field-by-field PUT matrix, driven end to end: a real MicroPython Unix-port digital twin, a real
 * Chromium browser filling and submitting the real rendered controls, and assertions against what
 * the page actually renders afterward. Generalizes tests_js/live-backend.test.js's single-field
 * proof to every real writable field in wozi.json. See WEBSITE_PLAN.md §7 ("a real end-to-end
 * field-by-field PUT matrix") for the shared-session architecture and the real-UI-action boundaries
 * this file deliberately doesn't cross (those stay covered only by the mock-backend matrix).
 */
import { commands } from "vitest/browser";
import { afterAll, describe, expect, it } from "vitest";
import wozi from "../html/definitions/wozi.json";
import { formatFieldValue } from "../js/field-format.js";
import { collectPutFieldCases } from "./_put_field_cases.js";

/** @typedef {import("./_put_field_cases.js").PutFieldCase} PutFieldCase */
/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */

const REAL_PATHS = /** @type {const} */ (["/sensors", "/networking", "/system", "/notification"]);

// Three real, documented backend quirks where a field's GET readback never reflects a value that
// was just applied - see WEBSITE_PLAN.md §7 for the full account (driver sources, the digital-twin
// fake, and the confirmed js/mock-server.js divergence this exposed).
/** @type {Record<string, unknown>} */
const ALWAYS_REMOUNTS_AS = { ForceCalRef: 400, ContMeas: false, SGPResetVOC: false };

// Generous per-case ceiling: one real nav-drawer click, one real fill/select/toggle, one real
// Apply click, a data-apply-status poll, and (for most cases) a second real remount+read - all
// against a local twin, but under real browser/event-loop scheduling.
const CASE_TIMEOUT_MS = 15000;

const boot = await commands.startLiveMatrix();

/** @type {PutFieldCase[]} */
let CASES = [];
if (!boot.skipped) {
    const real = await commands.getRealCurrentValues([...REAL_PATHS]);
    const data = /** @type {import("../js/definitions.js").MockDeviceData} */ ({
        sensorsConfig: real["/sensors"],
        networkingConfig: real["/networking"],
        systemConfig: real["/system"],
        notificationConfig: real["/notification"],
    });
    CASES = collectPutFieldCases("wozi", /** @type {SiteDefinitions} */ (wozi), data);
}

afterAll(async () => {
    await commands.stopLiveMatrix();
});

if (boot.skipped) {
    it.skip(`live-backend PUT matrix (skipped: ${boot.reason})`, () => {});
} else {
    describe.each(CASES)("live PUT $sectionKey/$groupKey/$field.key ($field.kind)", (testCase) => {
        const { sectionKey, groupKey, field } = testCase;
        let currentValue = testCase.currentValue;

        /**
         * Fills+applies `value` through the real UI, then confirms it rendered correctly both
         * same-view and after a full remount (WEBSITE_PLAN.md §12: only number/string captions
         * self-refresh in place, so a remount is the only proof for toggle/enum).
         * @param {unknown} value
         * @param {"Valid" | "ValidOrUnchanged"} expectedStatus "ValidOrUnchanged" tolerates either
         * outcome for a resubmit case - the real backend's "Unchanged" detection doesn't reliably
         * fire (WEBSITE_PLAN.md §7), matching tests_js/live-backend.test.js's own established
         * tolerance for this scenario.
         */
        async function applyAndExpectRendered(value, expectedStatus) {
            // Same-view caption AND remount both reflect a real GET round-trip (js/render.js's
            // onApplied() -> fetchOnce()) - so both need ALWAYS_REMOUNTS_AS's override for the three
            // quirky fields (WEBSITE_PLAN.md §7). A toggle/enum's same-view state is local to the
            // click instead (no in-place poll touches it), so raw `value` is still correct there.
            const expectedRemountValue = field.key in ALWAYS_REMOUNTS_AS ? ALWAYS_REMOUNTS_AS[field.key] : value;

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

        // An empty-string current value has no real "resubmit" gesture - typing nothing is
        // indistinguishable from untouched under the sparse-PUT convention (WEBSITE_PLAN.md §4).
        const resubmittable = currentValue !== undefined && !(field.kind === "string" && currentValue === "");
        if (resubmittable) {
            it(
                "resubmitting the field's own current value renders correctly (Valid or Unchanged)",
                async () => {
                    await applyAndExpectRendered(currentValue, "ValidOrUnchanged");
                },
                CASE_TIMEOUT_MS,
            );
        }

        if (field.kind === "number") {
            const min = /** @type {number} */ (field.min);
            const max = /** @type {number} */ (field.max);
            const mid = min + (max - min) / 2;
            // wholeRange (cosmetic probe-value shape) and isFloat (the real accept/reject-fractional
            // decision) are deliberately separate flags - WarnHum's range is whole-numbered but the
            // field is float-typed, so conflating them wrongly rejects its valid fractional literal.
            const wholeRange = Number.isInteger(min) && Number.isInteger(max);
            const isFloat = field.float === true;
            const step = wholeRange ? 1 : 0.5;
            const specialMagnitudes = new Set((field.specialValues ?? []).map((s) => s.value));

            // Rounded to 2 decimal places: SCD30's TempOffs has a real 0.01° hardware truncation
            // (SPECIFICATION.md, near the ForceCalRef/AmbPres notes) that an unrounded mid value
            // would silently fail against; harmless for every other field.
            const validValues = [min, mid, max]
                .map((v) => (wholeRange ? Math.round(v) : Math.round(v * 100) / 100))
                .filter((v) => v !== testCase.currentValue);

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
                await applyAndExpectRendered(value, "Valid");
            });

            for (const special of field.specialValues ?? []) {
                it(
                    `accepts the declared special value ${special.value} ("${special.meaning}"), rendered correctly`,
                    async () => {
                        await applyAndExpectRendered(special.value, special.value === testCase.currentValue ? "ValidOrUnchanged" : "Valid");
                    },
                    CASE_TIMEOUT_MS,
                );
            }
        }

        if (field.kind === "string") {
            const minLength = field.minLength ?? 0;
            const maxLength = /** @type {number} */ (field.maxLength);
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

            it.each(validLengths.map((len) => "x".repeat(len)).filter((v) => v !== testCase.currentValue))(
                "accepts a %s-char string (a valid value distributed across the length range), rendered correctly",
                async (value) => {
                    await applyAndExpectRendered(value, "Valid");
                },
            );
        }

        if (field.kind === "toggle") {
            const opposite = !testCase.currentValue;
            it(
                "flipping to the opposite state renders Valid with the new state actually shown",
                async () => {
                    await applyAndExpectRendered(opposite, "Valid");
                },
                CASE_TIMEOUT_MS,
            );
        }

        if (field.kind === "enum") {
            const options = (field.options ?? []).filter((o) => o.value !== testCase.currentValue);
            it.each(options.map((o) => o.value))("selecting option %s renders Valid with that option actually shown selected", async (value) => {
                await applyAndExpectRendered(value, "Valid");
            });
        }
    });
}
