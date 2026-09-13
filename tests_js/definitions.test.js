import { afterEach, describe, expect, it, vi } from "vitest";
// These tests run in a real browser (Playwright + Chromium), so the shipped definitions are
// imported as modules - node:fs is not reachable here. Same import shape the PUT matrix uses.
import woziDefs from "../html/definitions/wozi.json";
import devDefs from "../html/definitions/dev.json";
import { loadDefinitions, resolveFieldValue, SUPPORTED_SCHEMA_MAJOR, validateDefinitions } from "../js/definitions.js";

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

    it("rejects a section missing key or label", () => {
        const missingKey = { ...MINIMAL_VALID, sections: [{ label: "X", rest: { get: "/x" }, pollGroup: "live", groups: [] }] };
        expect(validateDefinitions(missingKey).some((p) => p.includes("sections[0].key"))).toBe(true);

        const missingLabel = { ...MINIMAL_VALID, sections: [{ key: "x", rest: { get: "/x" }, pollGroup: "live", groups: [] }] };
        expect(validateDefinitions(missingLabel).some((p) => p.includes("sections[0].label"))).toBe(true);
    });

    it("rejects a section missing rest.get", () => {
        const broken = {
            ...MINIMAL_VALID,
            sections: [{ key: "x", label: "X", rest: {}, pollGroup: "live", groups: [] }],
        };
        expect(validateDefinitions(broken).some((p) => p.includes("rest.get"))).toBe(true);
    });

    it("rejects a section with a missing or unrecognized pollGroup", () => {
        // js/render.js's renderSection() only ever checks `=== "live"`, so a missing/typo'd
        // pollGroup silently falls back to a single one-shot fetch instead of failing loudly here -
        // exactly the "shape mismatch surfaces a visible error" contract this module's own header
        // comment promises for every other field.
        const missing = { ...MINIMAL_VALID, sections: [{ key: "x", label: "X", rest: { get: "/x" }, groups: [] }] };
        expect(validateDefinitions(missing).some((p) => p.includes("pollGroup"))).toBe(true);

        const typo = { ...MINIMAL_VALID, sections: [{ key: "x", label: "X", rest: { get: "/x" }, pollGroup: "Live", groups: [] }] };
        expect(validateDefinitions(typo).some((p) => p.includes("pollGroup"))).toBe(true);
    });

    it("accepts every real pollGroup value", () => {
        for (const pollGroup of ["live", "settings", "none"]) {
            const defs = { ...MINIMAL_VALID, landingSection: "x", sections: [{ key: "x", label: "X", rest: { get: "/x" }, pollGroup, groups: [] }] };
            expect(validateDefinitions(defs)).toEqual([]);
        }
    });

    it("rejects a non-positive or non-numeric section pollIntervalMs when present", () => {
        // js/render.js passes this straight to setTimeout() (startPolling()) - 0/negative/NaN would
        // otherwise reach it silently and fire an unthrottled tight polling loop.
        for (const pollIntervalMs of [0, -1000, "3000", null]) {
            const defs = { ...MINIMAL_VALID, sections: [{ key: "x", label: "X", rest: { get: "/x" }, pollGroup: "live", pollIntervalMs, groups: [] }] };
            expect(validateDefinitions(defs).some((p) => p.includes("pollIntervalMs"))).toBe(true);
        }
    });

    it("rejects a missing or non-positive defaultPollIntervalMs", () => {
        for (const defaultPollIntervalMs of [undefined, 0, -1, "3000"]) {
            expect(validateDefinitions({ ...MINIMAL_VALID, defaultPollIntervalMs }).some((p) => p.includes("defaultPollIntervalMs"))).toBe(true);
        }
    });

    it("rejects a missing device.id", () => {
        const broken = { ...MINIMAL_VALID, device: {} };
        expect(validateDefinitions(broken).some((p) => p.includes("device.id"))).toBe(true);
    });

    it("rejects a missing landingSection", () => {
        const broken = { ...MINIMAL_VALID, landingSection: undefined };
        expect(validateDefinitions(broken).some((p) => p.includes("landingSection"))).toBe(true);
    });

    it("rejects a missing/empty sections array", () => {
        expect(validateDefinitions({ ...MINIMAL_VALID, sections: undefined }).some((p) => p.includes("sections"))).toBe(true);
        expect(validateDefinitions({ ...MINIMAL_VALID, sections: [] }).some((p) => p.includes("sections"))).toBe(true);
    });

    it("rejects a section that isn't an object", () => {
        const broken = { ...MINIMAL_VALID, sections: ["not-an-object"] };
        expect(validateDefinitions(broken).some((p) => p.includes("sections[0] is not an object"))).toBe(true);
    });

    it("rejects a section missing groups (not an array) and a group missing key/label", () => {
        const missingGroups = { ...MINIMAL_VALID, sections: [{ key: "x", label: "X", rest: { get: "/x" }, pollGroup: "live" }] };
        expect(validateDefinitions(missingGroups).some((p) => p.includes("groups must be an array"))).toBe(true);

        const missingGroupLabel = {
            ...MINIMAL_VALID,
            sections: [{ key: "x", label: "X", rest: { get: "/x" }, pollGroup: "live", groups: [{ key: "g" }] }],
        };
        expect(validateDefinitions(missingGroupLabel).some((p) => p.includes("missing key/label"))).toBe(true);
    });

    it("rejects an errcount group whose modules isn't an array", () => {
        const broken = {
            ...MINIMAL_VALID,
            sections: [
                {
                    key: "status",
                    label: "Status",
                    rest: { get: "/status" },
                    pollGroup: "live",
                    groups: [{ key: "errcount", label: "Errors", kind: "errcount" }],
                },
            ],
        };
        expect(validateDefinitions(broken).some((p) => p.includes("modules must be an array"))).toBe(true);
    });

    it("rejects a non-errcount group whose fields isn't an array", () => {
        const broken = {
            ...MINIMAL_VALID,
            sections: [{ key: "x", label: "X", rest: { get: "/x" }, pollGroup: "live", groups: [{ key: "g", label: "G" }] }],
        };
        expect(validateDefinitions(broken).some((p) => p.includes("fields must be an array"))).toBe(true);
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

    /**
     * @param {Record<string, unknown>} field
     * @returns {Record<string, unknown>}
     */
    function withField(field) {
        return {
            ...MINIMAL_VALID,
            sections: [{ ...MINIMAL_VALID.sections[0], groups: [{ key: "G", label: "G", fields: [field] }] }],
        };
    }

    it("accepts a readonly field carrying a nested path and a decimals hint", () => {
        expect(validateDefinitions(withField({ key: "R", label: "Red", kind: "readonly", path: ["RGB", "R"], decimals: 4 }))).toEqual([]);
    });

    it("rejects a malformed path", () => {
        for (const path of ["RGB.R", [], [""], ["RGB", 3], {}]) {
            const problems = validateDefinitions(withField({ key: "R", label: "Red", kind: "readonly", path }));
            expect(problems.some((p) => p.includes(".path")), JSON.stringify(path)).toBe(true);
        }
    });

    it("rejects a path on a writable field, where a PUT body is always flat", () => {
        const problems = validateDefinitions(withField({ key: "R", label: "Red", kind: "number", path: ["RGB", "R"] }));
        expect(problems.some((p) => p.includes(".path is only valid on a readonly field"))).toBe(true);
    });

    it("rejects a malformed decimals hint", () => {
        for (const decimals of [-1, 1.5, "2", null]) {
            const problems = validateDefinitions(withField({ key: "Lux", label: "Lux", kind: "readonly", decimals }));
            expect(problems.some((p) => p.includes(".decimals")), JSON.stringify(decimals)).toBe(true);
        }
    });

    // Nothing anywhere ran this validator against the shipped dev definitions before: the PUT
    // matrix imports that file raw, and this suite only ever loaded wozi's. A malformed dev
    // definitions file therefore shipped and failed in a browser instead of here.
    it.each([
        ["wozi", woziDefs],
        ["dev", devDefs],
    ])("accepts the shipped %s definitions file", (_device, shipped) => {
        expect(validateDefinitions(shipped)).toEqual([]);
    });
});

describe("resolveFieldValue", () => {
    it("reads a flat key when no path is given", () => {
        expect(resolveFieldValue({ key: "Lux", label: "Lux", kind: "readonly" }, { Lux: 12.5 })).toBe(12.5);
    });

    it("walks a nested path instead of the flat key", () => {
        const values = { Lux: 12.5, RGB: { R: 0.25, G: 0.5, B: 0.75 } };
        expect(resolveFieldValue({ key: "R", label: "Red", kind: "readonly", path: ["RGB", "R"] }, values)).toBe(0.25);
        expect(resolveFieldValue({ key: "B", label: "Blue", kind: "readonly", path: ["RGB", "B"] }, values)).toBe(0.75);
    });

    it("distinguishes RGB.B from HSB.B, which is the whole reason the body is nested", () => {
        const values = { RGB: { B: 0.75 }, HSB: { B: 0.03 } };
        expect(resolveFieldValue({ key: "B", label: "Blue", kind: "readonly", path: ["RGB", "B"] }, values)).toBe(0.75);
        expect(resolveFieldValue({ key: "Bri", label: "Brightness", kind: "readonly", path: ["HSB", "B"] }, values)).toBe(0.03);
    });

    it("yields undefined for a path that does not resolve, never a half-walked sub-object", () => {
        /** @type {import("../js/definitions.js").FieldDef} */
        const field = { key: "R", label: "Red", kind: "readonly", path: ["RGB", "R"] };
        expect(resolveFieldValue(field, {})).toBeUndefined();
        expect(resolveFieldValue(field, { RGB: null })).toBeUndefined();
        expect(resolveFieldValue(field, { RGB: 42 })).toBeUndefined();
        expect(resolveFieldValue({ ...field, path: ["RGB"] }, { RGB: { R: 1 } })).toEqual({ R: 1 });
    });

    it("still falls back to defaultValue when a path resolves to nothing", () => {
        /** @type {import("../js/definitions.js").FieldDef} */
        const field = { key: "R", label: "Red", kind: "readonly", path: ["RGB", "R"], defaultValue: 0 };
        expect(resolveFieldValue(field, {})).toBe(0);
    });

    it("passes a null through as a real value rather than falling back", () => {
        // CCT is legitimately null in a dark room - the renderer shows an em dash for it, and a
        // defaultValue fallback here would silently invent a colour temperature instead.
        expect(resolveFieldValue({ key: "CCT", label: "CCT", kind: "readonly", defaultValue: 5000 }, { CCT: null })).toBeNull();
    });
});

describe("loadDefinitions", () => {
    const originalFetch = window.fetch;

    afterEach(() => {
        window.fetch = originalFetch;
    });

    it("returns the parsed definitions on a valid fetch", async () => {
        window.fetch = vi.fn(() => Promise.resolve(new Response(JSON.stringify(MINIMAL_VALID), { status: 200 })));
        const defs = await loadDefinitions("definitions/wozi.json");
        expect(defs.device.id).toBe("wozi");
    });

    it("throws on a non-ok HTTP response", async () => {
        window.fetch = vi.fn(() => Promise.resolve(new Response("not found", { status: 404 })));
        await expect(loadDefinitions("definitions/missing.json")).rejects.toThrow("404");
    });

    it("throws with the validation problems on a malformed document", async () => {
        window.fetch = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ not: "valid" }), { status: 200 })));
        await expect(loadDefinitions("definitions/broken.json")).rejects.toThrow("failed definitions validation");
    });

    it("throws a clear message (not a raw SyntaxError) when the response isn't valid JSON (a transmission error)", async () => {
        window.fetch = vi.fn(() => Promise.resolve(new Response("{not valid json", { status: 200 })));
        await expect(loadDefinitions("definitions/torn.json")).rejects.toThrow(/not valid json/i);
    });

    it("never hangs forever on a connection that never responds", async () => {
        vi.useFakeTimers();
        window.fetch = vi.fn((_url, init) => {
            return new Promise((_resolve, reject) => {
                /** @type {AbortSignal | undefined} */ (/** @type {RequestInit} */ (init).signal)?.addEventListener("abort", () =>
                    reject(new DOMException("The operation was aborted", "AbortError")),
                );
            });
        });

        const pending = loadDefinitions("definitions/hangs.json");
        const assertion = expect(pending).rejects.toThrow(/timed out/i);
        await vi.advanceTimersByTimeAsync(15000); // fetchWithTimeout()'s own DEFAULT_TIMEOUT_MS
        await assertion;

        vi.useRealTimers();
    });
});
