/**
 * Every readonly field a device's generated definitions name must resolve against that device's
 * composed mock data, through the site's own resolver.
 */
import { describe, expect, it } from "vitest";
import samples from "../mockdata/samples.json";
import { resolveFieldValue } from "../js/definitions.js";
import { composeMockData, installMockFetch } from "../js/mock-server.js";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";

/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */

// Mirrors js/render.js's own groupValuesFrom(), duplicated deliberately: that function is not
// exported, and exporting it purely for a test would widen the module's surface for nothing.
// If the two ever disagree this test goes red, which is the failure mode worth having.
/**
 * @param {{key: string}} section
 * @param {{key: string, fields?: FieldDef[]}} group
 * @param {Record<string, unknown>} data
 * @param {Record<string, unknown>} statusBody
 * @returns {Record<string, unknown>}
 */
function groupValuesFrom(section, group, data, statusBody) {
    const source = section.key === "measurements" || section.key === "sensors" || section.key === "status"
        ? /** @type {Record<string, unknown>} */ (data[group.key] ?? {})
        : data;
    const statusFields = (group.fields ?? []).filter((field) => field.statusPath !== undefined);
    if (statusFields.length === 0) {
        return source;
    }
    const values = { ...source };
    for (const field of statusFields) {
        values[field.key] = resolveFieldValue({ ...field, path: field.statusPath ?? [] }, statusBody);
    }
    return values;
}

/**
 * A list whose every item is a string, number, boolean or null: String() renders it as text, never as an object.
 * @param {unknown} value
 * @returns {boolean}
 */
function isScalarList(value) {
    return Array.isArray(value) && value.every((item) => item === null || ["string", "number", "boolean"].includes(typeof item));
}

/**
 * A field js/field-format.js renders from a JSON object through its own shape check (its RECORD_FORMATTERS).
 * @param {FieldDef} field
 * @returns {boolean}
 */
function isObjectFormat(field) {
    return field.format === "gmtimestruct" || field.format === "lasttaskend";
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
            const values = groupValuesFrom(section, group, sectionData, /** @type {Record<string, unknown>} */ (data.status ?? {}));
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
                // The two object formats (gmtimestruct, lasttaskend) and a list of scalars (ConfigFaults) are leaves.
                if (!isObjectFormat(field) && typeof resolved === "object" && resolved !== null && !isScalarList(resolved)) {
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

    // G.3's mirror of _put_status(): every dispatch key the status section lists answers {key: true} "Valid" and any
    // other value "Invalid", as the device answers ResetErrors and each registered command outside its "Failed" windows.
    it.each(DEVICE_IDS)("answers every status command %s's definitions list as the device does", async (device) => {
        const defs = /** @type {import("../js/definitions.js").SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device));
        const status = defs.sections.find((section) => section.key === "status");
        const put = status?.rest.put ?? "";
        const keys = (status?.groups ?? []).flatMap((group) => ("fields" in group ? group.fields : [])).filter((field) => field.dispatch === true).map((field) => field.key);
        expect(keys).toContain("ResetErrors");
        const uninstall = installMockFetch(defs, composeMockData(defs, /** @type {import("../js/definitions.js").MockSamples} */ (samples)));
        /** @type {(body: Record<string, unknown>) => Promise<unknown>} */
        const answer = async (body) => (await (await fetch(put, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })).json()).result;
        try {
            const answers = await Promise.all(keys.flatMap((key) => [true, false, 1].map((value) => answer({ [key]: value }))));
            expect(answers).toEqual(keys.flatMap((key) => [{ [key]: "Valid" }, { [key]: "Invalid" }, { [key]: "Invalid" }]));
            expect(await answer({ Unlisted: true })).toEqual({ Unlisted: "Invalid" });
        } finally {
            uninstall();
        }
    });

    it("gives the mock's stale-time flag the value its NTP sync implies once the clock is set", () => {
        // The generated module publishes TimeStale as NTPSynced inverted while UnixTime is set.
        const { networking, system } = samples.status;
        expect(typeof system.UnixTime).toBe("number");
        expect(system.TimeStale).toBe(!networking.NTPSynced);
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

    it("reads a maintenance field by its path and reports one whose instance is absent", () => {
        const fields = [
            { key: "SGP40_BackupTS", label: "Backup", kind: /** @type {const} */ ("readonly"), path: ["SGP40", "BackupTS"] },
            { key: "SGP40_2_BackupTS", label: "Backup 2", kind: /** @type {const} */ ("readonly"), path: ["SGP40_2", "BackupTS"] },
        ];
        const defs = { sections: [{ key: "status", groups: [{ key: "sensors", fields }] }] };
        expect(unrenderableReadonlyFields(defs, { status: { sensors: { SGP40: { BackupTS: 1 }, SGP40_2: { BackupTS: 2 } } } })).toEqual([]);
        expect(unrenderableReadonlyFields(defs, { status: { sensors: { SGP40: { BackupTS: 1 } } } })).toEqual(["status/sensors/SGP40_2_BackupTS"]);
    });

    it("takes a list of names as a leaf and still reports a list that holds a sub-object", () => {
        const defs = {
            sections: [{ key: "status", groups: [{ key: "system", fields: [{ key: "ConfigFaults", label: "Config Faults", kind: "readonly" }] }] }],
        };
        expect(unrenderableReadonlyFields(defs, { status: { system: { ConfigFaults: [] } } })).toEqual([]);
        expect(unrenderableReadonlyFields(defs, { status: { system: { ConfigFaults: ["SCD30", "WIFI"] } } })).toEqual([]);
        expect(unrenderableReadonlyFields(defs, { status: { system: { ConfigFaults: [{ Module: "SCD30" }] } } })).toEqual(["status/system/ConfigFaults (an object, not a leaf)"]);
    });

    it("takes a task-end record as a leaf, as it takes a time struct", () => {
        const defs = {
            sections: [{ key: "status", groups: [{ key: "system", fields: [{ key: "LastTaskEnd", label: "Task Last Ended", kind: "readonly", format: "lasttaskend" }] }] }],
        };
        expect(unrenderableReadonlyFields(defs, { status: { system: { LastTaskEnd: null } } })).toEqual([]);
        expect(unrenderableReadonlyFields(defs, { status: { system: { LastTaskEnd: { Task: "SCD30.start_asy_read", Uptime: 3600 } } } })).toEqual([]);
    });
});
