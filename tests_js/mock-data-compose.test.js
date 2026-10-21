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
            return data.status.sensors; // read by each field's path, [<module name>, <leaf>]
        }
        return /** @type {Record<string, unknown>} */ (data.status[/** @type {"networking" | "system" | "notification"} */ (group.key)] ?? {});
    }
    return /** @type {Record<string, unknown>} */ (data[/** @type {"networkingConfig" | "systemConfig" | "notificationConfig"} */ (`${sectionKey}Config`)]);
}

/**
 * The generated module's `LastTaskEnd` once a task has ended (buildgen/codegen.py's _system_status()).
 * @param {unknown} value
 * @returns {boolean} an object of exactly a string `Task` and an integer `Uptime`
 */
function isTaskEndRecord(value) {
    if (typeof value !== "object" || value === null) {
        return false;
    }
    const { Task: task, Uptime: uptime, ...rest } = /** @type {Record<string, unknown>} */ (value);
    return typeof task === "string" && Number.isInteger(uptime) && Object.keys(rest).length === 0;
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
    if (field.format === "lasttaskend") {
        return value === null || isTaskEndRecord(value) ? null : "neither null nor a task-end record";
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
 * @param {string} sectionKey
 * @param {string} groupKey
 * @returns {Set<string>} every dotted path one group's fields read (`SGP40.BackupTS`), a field without a path by its key
 */
function namedPaths(defs, sectionKey, groupKey) {
    const section = defs.sections.find((s) => s.key === sectionKey);
    const group = section?.groups.find((g) => "fields" in g && g.key === groupKey);
    return new Set((group === undefined ? [] : /** @type {FieldGroup} */ (group).fields).map((f) => (f.path ?? [f.key]).join(".")));
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
    const maintenance = namedPaths(defs, "status", "sensors");
    for (const [name, body] of Object.entries(data.status.sensors)) {
        stray.push(...Object.keys(body).filter((leaf) => !maintenance.has(`${name}.${leaf}`)).map((leaf) => `status.sensors.${name}.${leaf}`));
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

    it("throws for an errcount module no sample matches, never composing a healthy zero for it", () => {
        const defs = definitionsOf(DEVICE_IDS[0] ?? "");
        const errcount = { key: "errcount", label: "Errors", kind: /** @type {const} */ ("errcount"), modules: [{ key: "GHOST", label: "Ghost" }] };
        const ghost = { ...defs, sections: [{ key: "status", label: "Status", rest: { get: "/status" }, pollGroup: /** @type {const} */ ("live"), groups: [errcount] }] };
        expect(() => composeMockData(ghost, SAMPLES)).toThrow('mock samples: no sample for module "status/errcount/GHOST"');
    });

    it("composes a maintenance field by its path: an instance's entry under its own name, from its driver's sample", () => {
        const defs = definitionsOf(DEVICE_IDS[0] ?? "");
        const field = { key: "SGP40_second_BackupTS", label: "Second Backup", kind: /** @type {const} */ ("readonly"), path: ["SGP40_second", "BackupTS"] };
        const status = { key: "status", label: "Status", rest: { get: "/status" }, pollGroup: /** @type {const} */ ("live"), groups: [{ key: "sensors", label: "Sensor Maintenance", fields: [field] }] };
        const data = composeMockData({ ...defs, sections: [status] }, SAMPLES);
        expect(data.status.sensors).toEqual({ "SGP40_second": { BackupTS: SAMPLES.status.sensors.SGP40?.BackupTS } });
    });

    it("reports a maintenance value composed under a path no field reads", () => {
        const defs = definitionsOf(DEVICE_IDS[0] ?? "");
        const data = composeMockData(defs, SAMPLES);
        const [name, body] = Object.entries(data.status.sensors)[0] ?? ["", {}];
        data.status.sensors[name] = { ...body, Stray: 1 };
        expect(strayKeys(defs, data)).toContain(`status.sensors.${name}.Stray`);
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

    it("takes a task-end field as null or a {Task, Uptime} record and reports any other value", () => {
        const field = { key: "LastTaskEnd", label: "Task Last Ended", kind: /** @type {const} */ ("readonly"), format: /** @type {const} */ ("lasttaskend") };
        expect(valueProblem(field, { LastTaskEnd: null })).toBeNull();
        expect(valueProblem(field, { LastTaskEnd: { Task: "SCD30.start_asy_read", Uptime: 3600 } })).toBeNull();
        const wrong = [
            0, "SCD30.start_asy_read", { Task: "SCD30.start_asy_read" }, { Task: 7, Uptime: 3600 }, { Task: "SCD30.start_asy_read", Uptime: 1.5 },
            { Task: "SCD30.start_asy_read", Uptime: 3600, Extra: 1 },
        ];
        expect(wrong.map((value) => valueProblem(field, { LastTaskEnd: value }))).toEqual(wrong.map(() => "neither null nor a task-end record"));
    });
});
