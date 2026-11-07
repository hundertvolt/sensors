// Each device's generated REST reference agrees with its definitions (the routes the page and the mock serve), with
// js/api-contract.js's result words and with the mock's code table, read from the mock's source (no test-only export).
// The reference's fields come from the definitions themselves, so no field is compared.
import { describe, expect, it } from "vitest";
import mockServerSource from "../js/mock-server.js?raw";
import { FAILED, INVALID, UNCHANGED, VALID } from "../js/api-contract.js";
import { API_REFERENCES, DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";
import { readObjectConst } from "./_source_constants.js";

/**
 * @template T
 * @param {Map<string, T>} map
 * @param {string} device
 * @returns {T}
 */
function entryOf(map, device) {
    const entry = map.get(device);
    if (entry === undefined) {
        throw new Error(`nothing generated for ${device}`);
    }
    return entry;
}

/**
 * "<METHOD> <path>" for every route the definitions' sections declare (rest.get, rest.put).
 * @param {import("../js/definitions.js").SiteDefinitions} defs
 * @returns {string[]}
 */
function declaredRoutes(defs) {
    return defs.sections.flatMap((section) => [`GET ${section.rest.get}`, ...(section.rest.put === undefined ? [] : [`PUT ${section.rest.put}`])]);
}

describe.each(DEVICE_IDS)("%s's REST reference", (device) => {
    const reference = entryOf(API_REFERENCES, device);
    const defs = entryOf(GENERATED_DEFINITIONS, device);

    it("lists exactly the routes the definitions' sections declare", () => {
        expect(reference.routes.map((route) => `${route.method} ${route.path}`).sort()).toEqual(declaredRoutes(defs).sort());
    });

    it("names js/api-contract.js's four result words", () => {
        expect([...reference.resultWords].sort()).toEqual([VALID, UNCHANGED, INVALID, FAILED].sort());
    });

    it("lists the code table the mock's envelopes are built from", () => {
        expect(reference.envelopeCodes).toEqual(readObjectConst(mockServerSource, "STANDARD_CODES"));
    });
});

describe("the agreement checks", () => {
    // Guards the checks themselves: a route, a word or a code the other side lacks is a difference they report.
    it("tell a missing route, word and code apart from agreement", () => {
        const [first] = DEVICE_IDS;
        const reference = entryOf(API_REFERENCES, first ?? "");
        const defs = entryOf(GENERATED_DEFINITIONS, first ?? "");
        expect(declaredRoutes({ ...defs, sections: defs.sections.slice(1) }).sort()).not.toEqual(reference.routes.map((route) => `${route.method} ${route.path}`).sort());
        expect([VALID, INVALID, FAILED].sort()).not.toEqual([...reference.resultWords].sort());
        expect(readObjectConst(mockServerSource.replace('405: "Method not allowed", ', ""), "STANDARD_CODES")).not.toEqual(reference.envelopeCodes);
    });
});
