/**
 * Every readonly field a shipped definitions.json names must resolve against that device's own
 * mockdata.json, using the site's own resolvers rather than a second implementation of them.
 */
import { describe, expect, it } from "vitest";
import wozi from "../html/definitions/wozi.json";
import dev from "../html/definitions/dev.json";
import woziData from "../mockdata/wozi.json";
import devData from "../mockdata/dev.json";
import { resolveFieldValue } from "../js/definitions.js";

/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */

// Mirrors js/render.js's own groupValuesFrom(). Duplicated deliberately and kept to the same
// shape: that function is not exported, and exporting it purely for a test would widen the
// module's surface for no runtime benefit. If the two ever disagree, this test goes red - which
// is the failure mode worth having.
/**
 * @param {{key: string}} section
 * @param {{key: string}} group
 * @param {Record<string, unknown>} data
 * @returns {Record<string, unknown>}
 */
function groupValuesFrom(section, group, data) {
    if (section.key === "measurements" || section.key === "sensors") {
        return /** @type {Record<string, unknown>} */ (data[group.key] ?? {});
    }
    if (section.key === "status" && group.key === "sensors") {
        /** @type {Record<string, unknown>} */
        const flat = {};
        const bySensor = /** @type {Record<string, Record<string, unknown>>} */ (data.sensors ?? {});
        for (const [sensorKey, fields] of Object.entries(bySensor)) {
            for (const [fieldKey, value] of Object.entries(fields)) {
                flat[`${sensorKey}_${fieldKey}`] = value;
            }
        }
        return flat;
    }
    if (section.key === "status") {
        return /** @type {Record<string, unknown>} */ (data[group.key] ?? {});
    }
    return data;
}

// Which mockdata top-level object backs each definitions section, matching what js/mock-server.js
// serves for that section's own GET.
const SECTION_DATA_KEY = {
    measurements: "measurements",
    sensors: "sensorsConfig",
    networking: "networkingConfig",
    system: "systemConfig",
    notification: "notificationConfig",
    status: "status",
};

/**
 * @param {Record<string, unknown>} defs
 * @param {Record<string, unknown>} data
 * @returns {string[]} "section/group/key" for every readonly field that does not render
 */
function unrenderableReadonlyFields(defs, data) {
    /** @type {string[]} */
    const missing = [];
    const { sections } = /** @type {{sections: {key: string, groups: {key: string, fields: FieldDef[]}[]}[]}} */ (defs);
    for (const section of sections) {
        const dataKey = SECTION_DATA_KEY[/** @type {keyof typeof SECTION_DATA_KEY} */ (section.key)];
        if (dataKey === undefined) {
            continue;  // a section with no GET body behind it at all
        }
        const sectionData = /** @type {Record<string, unknown>} */ (data[dataKey] ?? {});
        for (const group of section.groups) {
            const values = groupValuesFrom(section, group, sectionData);
            for (const field of group.fields ?? []) {
                // Only readonly fields: a writable one legitimately falls back to defaultValue, and
                // a command-only trigger is never echoed in a GET at all.
                if (field.kind !== "readonly") {
                    continue;
                }
                const resolved = resolveFieldValue(field, values);
                if (resolved === undefined) {
                    missing.push(`${section.key}/${group.key}/${field.key}`);
                    continue;
                }
                // A `path` naming a GROUP rather than a leaf resolves to the sub-object itself,
                // which formatFieldValue() stringifies as "[object Object]". That is a rendered
                // value, so the undefined check above cannot see it. gmtimestruct is the one
                // format whose value legitimately is a struct.
                if (field.format !== "gmtimestruct" && typeof resolved === "object" && resolved !== null) {
                    missing.push(`${section.key}/${group.key}/${field.key} (an object, not a leaf)`);
                }
            }
        }
    }
    return missing;
}

describe("definitions and mockdata agree", () => {
    // The gap this exists to catch has now happened twice in one branch, in both directions: the
    // UART promotion added UARTLINK_Transfers/UARTLINK_Failures to dev's definitions with no
    // mockdata behind them, and the ISL29125's GainMeas reached the definitions and the mockdata
    // while the real device body never carried it. Nothing compared the two sources, so both
    // rendered as a permanently blank row that looked like a device that had not reported yet.
    it("every readonly field dev's definitions name resolves in dev's mockdata", () => {
        expect(unrenderableReadonlyFields(dev, devData)).toEqual([]);
    });

    it("every readonly field wozi's definitions name resolves in wozi's mockdata", () => {
        expect(unrenderableReadonlyFields(wozi, woziData)).toEqual([]);
    });

    // Guards the check itself: a resolver that silently returned a value for everything would make
    // the two assertions above vacuous, and they would keep passing forever.
    it("reports a field whose mockdata is genuinely absent", () => {
        const defs = {
            sections: [{ key: "measurements", groups: [{ key: "GHOST", fields: [{ key: "Nope", label: "Nope", kind: "readonly" }] }] }],
        };
        expect(unrenderableReadonlyFields(defs, { measurements: {} })).toEqual(["measurements/GHOST/Nope"]);
    });

    it("reports a nested path that stops on a group instead of a leaf", () => {
        // The nested measurement group the ISL29125 introduced makes this reachable for the first
        // time: `path: ["RGB"]` resolves, so the absence check above passes, and the card renders
        // "[object Object]" where a number belongs.
        const defs = {
            sections: [{ key: "measurements", groups: [{ key: "ISL29125", fields: [{ key: "R", label: "Red", kind: "readonly", path: ["RGB"] }] }] }],
        };
        const data = { measurements: { ISL29125: { RGB: { R: 0.5, G: 0.25, B: 0.125 } } } };
        expect(unrenderableReadonlyFields(defs, data)).toEqual(["measurements/ISL29125/R (an object, not a leaf)"]);
    });
});
