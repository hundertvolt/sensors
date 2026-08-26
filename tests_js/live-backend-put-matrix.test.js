/**
 * Field-by-field PUT matrix, driven end to end: a real MicroPython Unix-port digital twin, a real
 * Chromium browser filling and submitting the real rendered controls (never a raw fetch), and
 * assertions against what the page actually renders afterward - not just the HTTP response.
 * tests_js/live-backend.test.js already proves this whole chain works for one field
 * (System/DebugLevel); this file generalizes it to every real writable field in wozi.json (the
 * only device the digital twin ever boots as), reusing the same field enumeration
 * (tests_js/_put_field_cases.js) that drives tests_js/mock-server-put-matrix.test.js's own
 * mock-backend matrix, so both matrices cover the same field set by construction.
 *
 * Boots the twin and opens one page ONCE for the whole file (tests_js/_live_matrix_command.js),
 * then drives every field's cases against that one shared session - a fresh subprocess+browser
 * page per field (mirroring live-backend.test.js's own per-test isolation) would multiply this
 * file's real-process-boot cost across every field for no real benefit, since every case here
 * already re-navigates to its own section (a real nav-drawer click) before acting, which already
 * forces a fresh GET + fresh render each time. Because state is shared, this file also (unlike the
 * mock matrix's fresh-fixture-per-test) tracks each field's own current value as tests apply real
 * changes to it, not a frozen mockdata/*.json baseline that never risks going stale relative to the
 * order tests actually run in.
 *
 * Real UI action boundaries (see tests_js/_live_matrix_command.js's own header comment for the
 * mechanical reasons): this matrix does not attempt "reject an invalid enum option", "reject the
 * wrong JSON type", or "field omitted from the request body" - none of those has a real user
 * gesture behind it (a <select> only ever offers its own declared options; every text input's
 * typed value is already exactly what a real PUT body carries). Those three categories, plus every
 * field unique to the "dev" device (SHTC3/MPRLS/ISL29125 - the live twin only ever boots as wozi),
 * stay covered only by tests_js/mock-server-put-matrix.test.js's mock-backend matrix - this file
 * does not attempt to reproduce them and does not claim to.
 */
import { commands } from "vitest/browser";
import { afterAll, describe, expect, it } from "vitest";
import wozi from "../html/definitions/wozi.json";
import { formatFieldValue } from "../js/field-format.js";
import { collectPutFieldCases } from "./_put_field_cases.js";

/** @typedef {import("./_put_field_cases.js").PutFieldCase} PutFieldCase */
/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */

const REAL_PATHS = /** @type {const} */ (["/sensors", "/networking", "/system", "/notification"]);

// Two real, documented hardware quirks where a field's real GET readback never reflects the value
// that was just successfully applied - confirmed directly against src/asy_scd30_driver.py and
// digital_twin/_scd30_chip.py's own fake register, not assumed, after this matrix's own first real
// run against them produced a "renders the old value" failure that looked at first like a stale
// caption/timing bug (it wasn't):
//   - ForceCalRef: src/asy_scd30_driver.py's get_forced_recalibration_reference() docstring says
//     "Volatile readback: always returns 400 ... regardless of the last FRC value applied" - the
//     real SCD30 chip's forced-recalibration register genuinely can't be read back once set. The
//     digital twin models this exactly: digital_twin/_scd30_chip.py's handle_readfrom_into()
//     hardcodes `word(400)` for this command, and its write handler is a documented no-op for the
//     same reason.
//   - ContMeas: src/asy_scd30_driver.py's own comment says "ContMeas has no _VAL_* schema entry -
//     the SCD30 can't report whether continuous measurement is running", and _read_sensor_dict()
//     (GET /sensors's own data source) never includes this key at all - so js/templates.js's
//     buildField() always renders a freshly-mounted ContMeas toggle from `Boolean(undefined)` =
//     false on every remount, regardless of what was last applied.
//   - SGPResetVOC: src/asy_sgp40_driver.py's own comment on _VAL_RESET says "Command-only trigger,
//     not a persisted config value ... this key is never in ConfigManager's _cache", and
//     get_dict_cfg() deliberately excludes it from what GET /sensors ever reports for the exact
//     same reason as ContMeas above.
// js/mock-server.js models none of these three quirks (confirmed directly - none of the three
// fields is referenced by name anywhere in that file, so all three go through its generic
// store-and-echo path) - a real, confirmed divergence between the mock backend's own model and the
// real backend's documented behavior, worth reporting to the project owner rather than silently
// changed here or in js/mock-server.js.
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
         * Fills+applies `value` through the real UI, then confirms it rendered correctly two ways:
         * same-view (the caption/control right after Apply) and, since only a number/string
         * field's caption self-refreshes in place (js/render.js's paint()), a full from-scratch
         * remount for every kind - the only real-UI-driven proof a toggle/enum field's persisted
         * value round-tripped at all.
         * @param {unknown} value
         * @param {"Valid" | "ValidOrUnchanged"} expectedStatus "ValidOrUnchanged" tolerates either
         * outcome for a resubmit-the-same-value case - confirmed directly that the real backend's
         * own "Unchanged" detection (config_manager.py's `new_cache[key] != value` comparison) does
         * not reliably fire even for a plain system/settings field like DebugLevel, which reported
         * "Valid" on an exact resubmit in this matrix's own first real run against it. This matches
         * tests_js/live-backend.test.js's own already-established tolerance for this exact
         * field/scenario (`expect(["valid", "unchanged"]).toContain(...)`) - a known, accepted
         * ambiguity this file follows rather than a new strictness it invents.
         */
        async function applyAndExpectRendered(value, expectedStatus) {
            // What GET should actually report afterward - the applied value for almost every
            // field, but ALWAYS_REMOUNTS_AS overrides it for the three fields whose real GET
            // readback never reflects a write at all (see that const's own comment). This matters
            // for a number/string field's caption too, not just the remount: js/render.js's
            // onApplied() -> fetchOnce() -> paint() refreshes that caption from a REAL fresh GET
            // response, not from what was typed - confirmed directly, this matrix's own first real
            // run against ForceCalRef expected the typed value there and got 400 both times, same
            // view and remount alike. A toggle/enum control's own same-view state is different: no
            // in-place poll ever touches it (paint()'s "existing card" branch only refreshes
            // number/string captions/readonly spans), so it stays genuinely local to the click -
            // real `value` is still correct for that specific check below.
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

        // A string field's own current value being "" is skipped here, not tested: js/render.js's
        // collectGroupBody() treats an empty input as untouched (the sparse-PUT convention every
        // other field relies on too), so there is no real typed gesture that resubmits an empty
        // string at all - typing nothing is indistinguishable, to the real UI, from not touching
        // the field. Confirmed directly: this matrix's own first real run against SSID (whose real
        // default is "") hit exactly this - the Apply click never even reached the network, so
        // data-apply-status was never set at all.
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
            // Two distinct questions, deliberately not conflated (an earlier version of this file
            // used one flag for both and got it wrong): whether this field's own *range* happens to
            // be whole numbers (purely cosmetic - it only decides how clean the generated probe
            // values look) versus whether the field itself is declared `float: true` (the real
            // schema fact that decides whether a fractional literal should be accepted or
            // rejected). WarnHum is the real field this distinction matters for: its range is
            // [0.0, 100.0] (whole numbers) but it IS float-typed, so a fractional literal for it
            // must be accepted, not rejected - confirmed directly against this matrix's own first
            // real run, which wrongly expected rejection before this fix.
            const wholeRange = Number.isInteger(min) && Number.isInteger(max);
            const isFloat = field.float === true;
            const step = wholeRange ? 1 : 0.5;
            const specialMagnitudes = new Set((field.specialValues ?? []).map((s) => s.value));

            // Rounded to 2 decimal places even for a genuine float field, not just whole-number
            // ranges: SCD30's own set_temperature_offset() (src/asy_scd30_driver.py) sends
            // `int(offset * 100)` to the real chip register - a 0.01 degree hardware resolution, not
            // a JS/JSON precision question. This matrix's own first real run against TempOffs chose
            // an unrounded mid value (327.675) that got silently truncated to 327.67 by that real
            // register, which looked like a rendering bug before this was traced to its actual
            // cause. No other driver has this same scale-then-truncate pattern (checked directly
            // across every sensor driver), but rounding here costs nothing for a field that doesn't.
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

            // minLength === 1's own "too short" probe is the empty string - not typeable as a
            // genuine "I rejected this on purpose" gesture either, same reasoning as the
            // resubmit-"" skip above (an empty input is indistinguishable from untouched). A
            // minLength of 2+ has a real non-empty too-short probe and stays covered.
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
