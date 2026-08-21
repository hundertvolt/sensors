import { afterEach, describe, expect, it, vi } from "vitest";
import { loadDefinitions, SUPPORTED_SCHEMA_MAJOR, validateDefinitions } from "../js/definitions.js";

const MINIMAL_VALID = {
    schemaVersion: "1.0.0",
    device: { id: "wozi", displayName: "wozi" },
    landingSection: "measurements",
    defaultPollIntervalMs: 3000,
    sections: [
        {
            key: "measurements",
            label: "Measurements",
            rest: { get: "/measurements" },
            pollGroup: "live",
            groups: [{ key: "SCD30", label: "SCD30", fields: [{ key: "CO2", label: "CO2", kind: "readonly" }] }],
        },
    ],
};

describe("validateDefinitions", () => {
    it("accepts a minimal well-formed document", () => {
        expect(validateDefinitions(MINIMAL_VALID)).toEqual([]);
    });

    it("rejects a non-object", () => {
        expect(validateDefinitions(null).length).toBeGreaterThan(0);
        expect(validateDefinitions("nope").length).toBeGreaterThan(0);
    });

    it("rejects a missing/unsupported schemaVersion", () => {
        const problems = validateDefinitions({ ...MINIMAL_VALID, schemaVersion: undefined });
        expect(problems.some((p) => p.includes("schemaVersion"))).toBe(true);

        const wrongMajor = validateDefinitions({ ...MINIMAL_VALID, schemaVersion: `${SUPPORTED_SCHEMA_MAJOR + 1}.0.0` });
        expect(wrongMajor.some((p) => p.includes("not supported"))).toBe(true);
    });

    it("rejects a landingSection that matches no real section", () => {
        const problems = validateDefinitions({ ...MINIMAL_VALID, landingSection: "nonexistent" });
        expect(problems.some((p) => p.includes("landingSection"))).toBe(true);
    });

    it("rejects a section missing rest.get", () => {
        const broken = {
            ...MINIMAL_VALID,
            sections: [{ key: "x", label: "X", rest: {}, pollGroup: "live", groups: [] }],
        };
        expect(validateDefinitions(broken).some((p) => p.includes("rest.get"))).toBe(true);
    });

    it("accepts an errcount group without requiring fields", () => {
        const withErrcount = {
            ...MINIMAL_VALID,
            sections: [
                {
                    key: "status",
                    label: "Status",
                    rest: { get: "/status" },
                    pollGroup: "live",
                    groups: [{ key: "errcount", label: "Errors", kind: "errcount", modules: [{ key: "SCD30", label: "SCD30" }] }],
                },
            ],
            landingSection: "status",
        };
        expect(validateDefinitions(withErrcount)).toEqual([]);
    });
});

describe("loadDefinitions", () => {
    const originalFetch = window.fetch;

    afterEach(() => {
        window.fetch = originalFetch;
    });

    it("returns the parsed definitions on a valid fetch", async () => {
        window.fetch = vi.fn(async () => new Response(JSON.stringify(MINIMAL_VALID), { status: 200 }));
        const defs = await loadDefinitions("definitions/wozi.json");
        expect(defs.device.id).toBe("wozi");
    });

    it("throws on a non-ok HTTP response", async () => {
        window.fetch = vi.fn(async () => new Response("not found", { status: 404 }));
        await expect(loadDefinitions("definitions/missing.json")).rejects.toThrow("404");
    });

    it("throws with the validation problems on a malformed document", async () => {
        window.fetch = vi.fn(async () => new Response(JSON.stringify({ not: "valid" }), { status: 200 }));
        await expect(loadDefinitions("definitions/broken.json")).rejects.toThrow("failed definitions validation");
    });
});
