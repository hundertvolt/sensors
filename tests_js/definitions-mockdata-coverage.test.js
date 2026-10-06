/**
 * Every readonly field a device's generated definitions name must resolve against that device's
 * composed mock data, through the site's own resolver.
 */
import { describe, expect, it } from "vitest";
import samples from "../mockdata/samples.json";
import { resolveFieldValue } from "../js/definitions.js";
import { composeMockData } from "../js/mock-server.js";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";

/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */

// Mirrors js/render.js's own groupValuesFrom(), duplicated deliberately: that function is not
// exported, and exporting it purely for a test would widen the module's surface for nothing.
// If the two ever disagree this test goes red, which is the failure mode worth having.
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
                // Only readonly fields: a command-only trigger is never echoed in a GET.
                if (field.kind !== "readonly") {
                    continue;
                }
                const resolved = resolveFieldValue(field, values);
                if (resolved === undefined) {
                    missing.push(`${section.key}/${group.key}/${field.key}`);
                    continue;
                }
                // A `path` naming a GROUP rather than a leaf resolves to the sub-object, which
                // renders as "[object Object]" - a value, so the check above cannot see it.
                // gmtimestruct is the one format whose value legitimately is a struct.
                if (field.format !== "gmtimestruct" && typeof resolved === "object" && resolved !== null) {
                    missing.push(`${section.key}/${group.key}/${field.key} (an object, not a leaf)`);
                }
            }
        }
    }
    return missing;
}

describe("definitions and mockdata agree", () => {
    // A blank row is not a defect the renderer reports, so an unresolvable readonly field fails here.
    it.each(DEVICE_IDS)("every readonly field %s's definitions name resolves in its composed mock data", (device) => {
        const defs = /** @type {import("../js/definitions.js").SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device));
        const data = composeMockData(defs, /** @type {import("../js/definitions.js").MockSamples} */ (samples));
        expect(unrenderableReadonlyFields(defs, data)).toEqual([]);
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
