import { afterEach, describe, expect, it, vi } from "vitest";
// Every device's generated definitions come from tests_js/_generated_definitions.js (a real browser run: no node:fs).
import { GENERATED_DEFINITIONS, staleAgainst } from "./_generated_definitions.js";
import { readIntConst } from "./_source_constants.js";
import definitionsSource from "../js/definitions.js?raw";
import pollManagerSource from "../js/poll-manager.js?raw";
import { isRecord, loadDefinitions, resolveFieldValue, validateDefinitions } from "../js/definitions.js";
import { pollManager } from "../js/poll-manager.js";

const SUPPORTED_SCHEMA_MAJOR = readIntConst(definitionsSource, "SUPPORTED_SCHEMA_MAJOR");
const DEFAULT_TIMEOUT_MS = readIntConst(pollManagerSource, "DEFAULT_TIMEOUT_MS");
// setTimeout's own ceiling: a larger delay fires at once.
const TIMEOUT_CEILING_MS = 2 ** 31 - 1;

const MINIMAL_VALID = {
    schemaVersion: "1.0.0",
    device: { id: "fixture-device", displayName: "Fixture Device" },
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
        // renderSection() only ever checks `=== "live"`, so a missing or misspelled pollGroup
        // falls back to one silent one-shot fetch instead of failing loudly - against the
        // "shape mismatch surfaces a visible error" contract this module promises elsewhere.
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

    it("holds both poll intervals to setTimeout's ceiling", () => {
        const sectionWith = (/** @type {number} */ pollIntervalMs) => ({ ...MINIMAL_VALID, sections: [{ ...MINIMAL_VALID.sections[0], pollIntervalMs }] });
        expect(validateDefinitions({ ...MINIMAL_VALID, defaultPollIntervalMs: TIMEOUT_CEILING_MS })).toEqual([]);
        expect(validateDefinitions(sectionWith(TIMEOUT_CEILING_MS))).toEqual([]);
        expect(validateDefinitions({ ...MINIMAL_VALID, defaultPollIntervalMs: TIMEOUT_CEILING_MS + 1 })).toEqual([
            "defaultPollIntervalMs must be a positive number of at most 2147483647 ms",
        ]);
        expect(validateDefinitions(sectionWith(TIMEOUT_CEILING_MS + 1))).toEqual(["sections[0].pollIntervalMs must be a positive number of at most 2147483647 ms"]);
    });

    it("takes the site's default decimals as an integer from 0 to 100 only", () => {
        for (const defaultDecimals of [0, 2, 100]) {
            expect(validateDefinitions({ ...MINIMAL_VALID, defaultDecimals })).toEqual([]);
        }
        for (const defaultDecimals of [-1, 1.5, 101, "2", null]) {
            expect(validateDefinitions({ ...MINIMAL_VALID, defaultDecimals }), JSON.stringify(defaultDecimals)).toEqual([
                "defaultDecimals must be an integer from 0 to 100 when present",
            ]);
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

    it("asks for confirmation on an enum or a toggle only, and only with a boolean", () => {
        const options = [{ value: "reboot", label: "Reboot" }];
        expect(validateDefinitions(withField({ key: "C", label: "Command", kind: "enum", options, confirm: true }))).toEqual([]);
        expect(validateDefinitions(withField({ key: "R", label: "Reset", kind: "toggle", confirm: false }))).toEqual([]);
        for (const field of [
            { key: "C", label: "Command", kind: "enum", options, confirm: "yes" },
            { key: "N", label: "Number", kind: "number", confirm: true },
            { key: "S", label: "Text", kind: "string", confirm: true },
            { key: "R", label: "Reading", kind: "readonly", confirm: true },
        ]) {
            expect(validateDefinitions(withField(field)), JSON.stringify(field)).toEqual([
                "sections[0].groups[0].fields[0].confirm must be a boolean on an enum or toggle field when present",
            ]);
        }
    });

    it("rejects a malformed decimals hint", () => {
        // 101 is the real ceiling, not a round number: Number#toFixed throws a RangeError above
        // 100, so a definitions file declaring more would pass validation and then break the card
        // it is on - which is exactly what this validator exists to prevent.
        for (const decimals of [-1, 1.5, "2", null, 101]) {
            const problems = validateDefinitions(withField({ key: "Lux", label: "Lux", kind: "readonly", decimals }));
            expect(problems.some((p) => p.includes(".decimals")), JSON.stringify(decimals)).toBe(true);
        }
    });

    it.each([...GENERATED_DEFINITIONS])("accepts the generated %s definitions", (_device, generated) => {
        expect(validateDefinitions(generated)).toEqual([]);
    });
});

describe("isRecord", () => {
    it("accepts every object but null and an array, an Object.create(null) one and a class instance included", () => {
        for (const value of [{}, { a: 1 }, Object.create(null), new Date(0), new Map()]) {
            expect(isRecord(value)).toBe(true);
        }
    });

    it("refuses null, an array, a function and a primitive", () => {
        for (const value of [null, undefined, [], [{ a: 1 }], () => ({}), 0, Number.NaN, "{}", true, Symbol("s")]) {
            expect(isRecord(value)).toBe(false);
        }
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

    it("yields undefined for a value the GET did not report, whatever the field's kind", () => {
        // An always-executed toggle the GET cannot report (SCD30's ContMeas) stays unset, never a stand-in.
        expect(resolveFieldValue({ key: "ContMeas", label: "Continuous Measurement", kind: "toggle", alwaysExecuted: true }, {})).toBeUndefined();
    });

    it("passes a null through as a real value", () => {
        // CCT is legitimately null in a dark room; the renderer shows an em dash for it.
        expect(resolveFieldValue({ key: "CCT", label: "CCT", kind: "readonly" }, { CCT: null })).toBeNull();
    });
});

describe("loadDefinitions", () => {
    const originalFetch = window.fetch;

    afterEach(() => {
        window.fetch = originalFetch;
    });

    it("returns the parsed definitions on a valid fetch", async () => {
        window.fetch = vi.fn(() => Promise.resolve(new Response(JSON.stringify(MINIMAL_VALID), { status: 200 })));
        const defs = await loadDefinitions("definitions/fixture-device.json");
        expect(defs.device.id).toBe("fixture-device");
    });

    it("throws on a non-ok HTTP response", async () => {
        // The device answers a missing file with its JSON envelope (asy_api_response.make_response()).
        const envelope = { res: "ERR", code: 404, descr: "Not found", result: {} };
        window.fetch = vi.fn(() => Promise.resolve(new Response(JSON.stringify(envelope), { status: 404 })));
        await expect(loadDefinitions("definitions/missing.json")).rejects.toThrow("Failed to fetch definitions/missing.json: HTTP 404");
    });

    it("throws with the validation problems on a malformed document", async () => {
        window.fetch = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ not: "valid" }), { status: 200 })));
        await expect(loadDefinitions("definitions/broken.json")).rejects.toThrow("failed definitions validation");
    });

    it("throws a clear message (not a raw SyntaxError) when the response isn't valid JSON (a transmission error)", async () => {
        window.fetch = vi.fn(() => Promise.resolve(new Response("{not valid json", { status: 200 })));
        await expect(loadDefinitions("definitions/torn.json")).rejects.toThrow(/not valid json/i);
    });

    it("waits for the request already in flight before it fetches (one request at a time)", async () => {
        let inFlight = 0;
        let maxInFlight = 0;
        /** @type {(() => void)[]} */
        const releases = [];
        window.fetch = vi.fn((url) => {
            inFlight += 1;
            maxInFlight = Math.max(maxInFlight, inFlight);
            return new Promise((resolve) => {
                releases.push(() => {
                    inFlight -= 1;
                    resolve(new Response(String(url).endsWith(".json") ? JSON.stringify(MINIMAL_VALID) : "{}", { status: 200 }));
                });
            });
        });
        const pending = pollManager.request("/status");
        const loading = loadDefinitions("definitions/fixture-device.json");
        await vi.waitFor(() => expect(releases).toHaveLength(1), { interval: 1 });
        expect(window.fetch).toHaveBeenCalledTimes(1);
        releases[0]?.();
        await pending;
        await vi.waitFor(() => expect(releases).toHaveLength(2), { interval: 1 });
        releases[1]?.();
        expect((await loading).device.id).toBe("fixture-device");
        expect(maxInFlight).toBe(1);
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
        await vi.advanceTimersByTimeAsync(DEFAULT_TIMEOUT_MS);
        await assertion;
    });
});

describe("the generated-definitions loader's TOML stamp", () => {
    const TOML = 'name = "fixture-device"\n';
    // sha256 of TOML's UTF-8 bytes, as sha256sum prints it.
    const TOML_SHA256 = "7dd835ef5e55c7c98444b97605ce72fb468a0a1d9ac2d9734b1d256b50b8b1cf";

    it("passes a stamp naming exactly the TOMLs, each with its own hash", async () => {
        expect(await staleAgainst(new Map([["fixture-device", TOML]]), { tomls: { "fixture-device": TOML_SHA256 } })).toEqual([]);
    });

    it.each([
        ["a TOML changed since generation", { tomls: { "fixture-device": "0".repeat(64) } }, ["fixture-device: changed since the tree was generated"]],
        ["a TOML the stamp does not name", { tomls: {} }, ["fixture-device: no stamp"]],
        ["a stamped device with no TOML", { tomls: { "fixture-device": TOML_SHA256, "gone-device": TOML_SHA256 } }, ["gone-device: stamped, but no such TOML"]],
        ["no stamp at all", undefined, ["no TOML stamp"]],
    ])("reports %s", async (_case, stamp, problems) => {
        expect(await staleAgainst(new Map([["fixture-device", TOML]]), stamp)).toEqual(problems);
    });
});
