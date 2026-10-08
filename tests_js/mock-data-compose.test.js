// composeMockData() gives every device mock data covering its whole generated definitions: each field
// a value of its kind, no key the definitions do not name, an entry per errcount row, catalog codes only.
import { describe, expect, it } from "vitest";
import samples from "../mockdata/samples.json";
import { resolveFieldValue } from "../js/definitions.js";
import { composeMockData } from "../js/mock-server.js";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";

/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */
/** @typedef {import("../js/definitions.js").FieldGroup} FieldGroup */
/** @typedef {import("../js/definitions.js").ErrcountGroup} ErrcountGroup */
/** @typedef {import("../js/definitions.js").MockDeviceData} MockDeviceData */

const SAMPLES = /** @type {import("../js/definitions.js").MockSamples} */ (samples);

/**
 * @param {string} device
 * @returns {SiteDefinitions}
 */
function definitionsOf(device) {
    const defs = GENERATED_DEFINITIONS.get(device);
    if (defs === undefined) {
        throw new Error(`no generated definitions for ${device}`);
    }
    return defs;
}

/**
 * A field group's GET values, as js/render.js's groupValuesFrom() reads them out of each section's body.
 * @param {string} sectionKey
 * @param {FieldGroup} group
 * @param {MockDeviceData} data
 * @returns {Record<string, unknown>}
 */
function groupValues(sectionKey, group, data) {
    if (sectionKey === "measurements") {
        return data.measurements[group.key] ?? {};
    }
    if (sectionKey === "sensors") {
        return data.sensorsConfig[group.key] ?? {};
    }
    if (sectionKey === "status") {
        if (group.key === "sensors") {
            return Object.fromEntries(Object.entries(data.status.sensors).flatMap(([name, body]) => Object.entries(body).map(([leaf, value]) => [`${name}_${leaf}`, value])));
        }
        return /** @type {Record<string, unknown>} */ (data.status[/** @type {"networking" | "system" | "notification"} */ (group.key)] ?? {});
    }
    return /** @type {Record<string, unknown>} */ (data[/** @type {"networkingConfig" | "systemConfig" | "notificationConfig"} */ (`${sectionKey}Config`)]);
}

/**
 * What is wrong with one field's composed value, or null: a command carries none, an always-executed
 * setting may have none (GET cannot always report it), everything else a value of its kind.
 * @param {FieldDef} field
 * @param {Record<string, unknown>} values
 * @returns {string | null}
 */
function valueProblem(field, values) {
    if (field.dispatch === true) {
        return Object.hasOwn(values, field.key) ? "a command, yet GET carries it" : null;
    }
    const value = resolveFieldValue(field, values);
    if (value === undefined) {
        return field.alwaysExecuted === true ? null : "no value";
    }
    if (field.kind === "number") {
        return typeof value === "number" ? null : "not a number";
    }
    if (field.kind === "toggle") {
        return typeof value === "boolean" ? null : "not a boolean";
    }
    if (field.kind === "string") {
        return typeof value === "string" ? null : "not a string";
    }
    if (field.kind === "enum") {
        return (field.options ?? []).some((option) => option.value === value) ? null : "not one of its options";
    }
    if (field.format === "gmtimestruct") {
        return typeof value === "object" && value !== null ? null : "not a time struct";
    }
    return null; // readonly: present is all a value of any shape needs
}

/**
 * @param {SiteDefinitions} defs
 * @param {MockDeviceData} data
 * @returns {string[]} "section/group/key: problem" for every field whose composed value is wrong
 */
function fieldProblems(defs, data) {
    return defs.sections.flatMap((section) => section.groups.flatMap((group) => {
        if (!("fields" in group)) {
            return [];
        }
        const values = groupValues(section.key, group, data);
        return group.fields.flatMap((field) => {
            const problem = valueProblem(field, values);
            return problem === null ? [] : [`${section.key}/${group.key}/${field.key}: ${problem}`];
        });
    }));
}

/**
 * @param {SiteDefinitions} defs
 * @param {string} sectionKey
 * @param {string} [groupKey]
 * @returns {Set<string>} every top-level key the section's (or one group's) fields read
 */
function namedKeys(defs, sectionKey, groupKey) {
    const section = defs.sections.find((s) => s.key === sectionKey);
    const groups = (section?.groups ?? []).filter((g) => "fields" in g && (groupKey === undefined || g.key === groupKey));
    return new Set(groups.flatMap((g) => /** @type {FieldGroup} */ (g).fields.map((f) => f.path?.[0] ?? f.key)));
}

/**
 * @param {SiteDefinitions} defs
 * @returns {ErrcountGroup[]}
 */
function errcountGroups(defs) {
    return defs.sections.flatMap((s) => s.groups.filter((g) => "kind" in g && g.kind === "errcount").map((g) => /** @type {ErrcountGroup} */ (g)));
}

/**
 * @param {SiteDefinitions} defs
 * @param {MockDeviceData} data
 * @returns {string[]} every composed key no definitions field names
 */
function strayKeys(defs, data) {
    /** @type {string[]} */
    const stray = [];
    /**
     * @param {string} where
     * @param {Record<string, unknown>} body
     * @param {Set<string>} allowed
     */
    const check = (where, body, allowed) => {
        stray.push(...Object.keys(body).filter((key) => !allowed.has(key)).map((key) => `${where}.${key}`));
    };
    for (const [pool, sectionKey] of /** @type {const} */ ([["measurements", "measurements"], ["sensorsConfig", "sensors"]])) {
        for (const [groupKey, body] of Object.entries(data[pool])) {
            check(`${pool}.${groupKey}`, body, namedKeys(defs, sectionKey, groupKey));
        }
    }
    for (const sectionKey of /** @type {const} */ (["networking", "system", "notification"])) {
        check(`${sectionKey}Config`, data[`${sectionKey}Config`], namedKeys(defs, sectionKey));
        check(`status.${sectionKey}`, data.status[sectionKey], namedKeys(defs, "status", sectionKey));
    }
    const maintenance = namedKeys(defs, "status", "sensors");
    for (const [name, body] of Object.entries(data.status.sensors)) {
        stray.push(...Object.keys(body).filter((leaf) => !maintenance.has(`${name}_${leaf}`)).map((leaf) => `status.sensors.${name}.${leaf}`));
    }
    check("status.errcount", data.status.errcount, new Set(errcountGroups(defs).flatMap((g) => g.modules.map((m) => m.key))));
    return stray;
}

/**
 * @param {{E: Record<string, string>, W: Record<string, string>}[]} tables
 * @param {MockDeviceData} data
 * @returns {string[]} "<module>: <type><num>" for every history code no table describes
 */
function undescribedCodes(tables, data) {
    /** @param {{num: number, type: "N"|"E"|"W"}} item */
    const described = (item) => {
        const { type } = item;
        return type === "N" || tables.some((codes) => String(item.num) in codes[type]);
    };
    return Object.entries(data.status.errcount).flatMap(([key, entry]) => (entry.history ?? [])
        .filter((item) => !described(item))
        .map((item) => `${key}: ${item.type}${item.num}`));
}

describe.each(DEVICE_IDS)("%s's composed mock data", (device) => {
    const defs = definitionsOf(device);
    const data = composeMockData(defs, SAMPLES);

    it("gives every field of every group a value of its kind", () => {
        expect(fieldProblems(defs, data)).toEqual([]);
    });

    it("composes no key the definitions do not name", () => {
        expect(strayKeys(defs, data)).toEqual([]);
    });

    it("has an entry for every errcount row", () => {
        const missing = errcountGroups(defs).flatMap((g) => g.modules.map((m) => m.key)).filter((key) => !(key in data.status.errcount));
        expect(missing).toEqual([]);
    });

    it("holds only codes the definitions' code tables describe", () => {
        const tables = errcountGroups(defs).map((g) => g.codes ?? { E: {}, W: {} });
        expect(tables.length).toBeGreaterThan(0);
        expect(undescribedCodes(tables, data)).toEqual([]);
    });
});

describe("composeMockData", () => {
    it("throws for a group no sample matches", () => {
        const defs = definitionsOf(DEVICE_IDS[0] ?? "");
        const ghost = {
            ...defs,
            sections: [{ key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: /** @type {const} */ ("live"), groups: [{ key: "GHOST", label: "Ghost", fields: [] }] }],
        };
        expect(() => composeMockData(ghost, SAMPLES)).toThrow('mock samples: no sample for group "measurements/GHOST"');
    });

    it("reports a value of the wrong kind and a stray key, so the checks above cannot pass vacuously", () => {
        const defs = definitionsOf(DEVICE_IDS[0] ?? "");
        const data = composeMockData(defs, SAMPLES);
        const [groupKey, body] = Object.entries(data.measurements)[0] ?? ["", {}];
        const [fieldKey] = Object.keys(body);
        if (fieldKey === undefined) {
            throw new Error("the first measurement group composed no values");
        }
        body[fieldKey] = undefined;
        body.Stray = 1;
        expect(fieldProblems(defs, data)).toContain(`measurements/${groupKey}/${fieldKey}: no value`);
        expect(strayKeys(defs, data)).toContain(`measurements.${groupKey}.Stray`);
    });
});
