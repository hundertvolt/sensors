import { afterEach, describe, expect, it } from "vitest";
import { installMockFetch } from "../js/mock-server.js";

/** @type {import("../js/definitions.js").SiteDefinitions} */
const DEFS = {
    schemaVersion: "1.0.0",
    device: { id: "test", displayName: "test" },
    landingSection: "measurements",
    defaultPollIntervalMs: 3000,
    sections: [
        {
            key: "sensors",
            label: "Sensors",
            rest: { get: "/sensors", put: "/sensors" },
            pollGroup: "settings",
            groups: [
                {
                    key: "SCD30",
                    label: "SCD30",
                    submit: true,
                    fields: [
                        { key: "MeasInt", label: "Measurement Interval", kind: "number", min: 2, max: 1800 },
                        { key: "ContMeas", label: "Continuous Measurement", kind: "toggle" },
                    ],
                },
            ],
        },
        {
            key: "networking",
            label: "Networking",
            rest: { get: "/networking", put: "/networking" },
            pollGroup: "settings",
            groups: [{ key: "identity", label: "Identity", submit: true, fields: [{ key: "Hostname", label: "Hostname", kind: "string", minLength: 1, maxLength: 63 }] }],
        },
        {
            key: "status",
            label: "Status",
            rest: { get: "/status", put: "/status" },
            pollGroup: "live",
            groups: [
                {
                    key: "resetErrors",
                    label: "Reset Errors",
                    submit: true,
                    fields: [{ key: "ResetErrors", label: "Confirm", kind: "toggle" }],
                },
            ],
        },
        {
            key: "measurements",
            label: "Measurements",
            rest: { get: "/measurements" },
            pollGroup: "live",
            groups: [{ key: "SCD30", label: "SCD30", fields: [{ key: "CO2", label: "CO2", kind: "readonly" }] }],
        },
    ],
};

const DATA = {
    measurements: { SCD30: { CO2: 600, TS: 1000, Model: "SCD30" } },
    sensorsConfig: { SCD30: { MeasInt: 5, ContMeas: true } },
    networkingConfig: { Hostname: "wozi" },
    systemConfig: {},
    notificationConfig: {},
    status: {
        networking: {},
        system: {},
        sensors: {},
        notification: {},
        errcount: { SCD30: { counter: 2, history: [{ num: 1, type: /** @type {const} */ ("E") }] } },
    },
};

describe("installMockFetch", () => {
    /** @type {(() => void) | undefined} */
    let uninstall;

    afterEach(() => {
        uninstall?.();
    });

    it("answers GET /sensors from the fixture", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/sensors");
        const body = await response.json();
        expect(body.SCD30.MeasInt).toBe(5);
    });

    it("passes non-REST paths through to the real fetch", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        // A relative static-asset path (no leading "/") never matches a REST path, so this hits
        // the real fetch and 404s against the test server - proving the mock did not intercept it.
        const response = await fetch("definitions/does-not-exist.json");
        expect(response.status).toBe(404);
    });

    it("validates PUT /sensors against field min/max and reports Valid/Invalid/Unchanged", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/sensors", {
            method: "PUT",
            body: JSON.stringify({ SCD30: { MeasInt: 3000, ContMeas: true } }),
        });
        const body = await response.json();
        expect(body.result.SCD30.MeasInt).toBe("Invalid"); // 3000 > max 1800
        expect(body.result.SCD30.ContMeas).toBe("Unchanged"); // fixture already has ContMeas: true
    });

    it("marks an in-range changed value as Valid and persists it for the next GET", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const put = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { MeasInt: 10 } }) });
        expect((await put.json()).result.SCD30.MeasInt).toBe("Valid");

        const get = await fetch("/sensors");
        expect((await get.json()).SCD30.MeasInt).toBe(10);
    });

    it("resets error counters and refills history with no-error placeholders (real reset() never shrinks it)", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        await fetch("/status", { method: "PUT", body: JSON.stringify({ ResetErrors: true }) });

        const get = await fetch("/status");
        const body = await get.json();
        expect(body.errcount.SCD30.counter).toBe(0);
        expect(body.errcount.SCD30.history).toEqual([{ num: 0, type: "N" }]);
    });

    it("leaves error counters untouched when ResetErrors is absent", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        await fetch("/status", { method: "PUT", body: JSON.stringify({}) });

        const get = await fetch("/status");
        expect((await get.json()).errcount.SCD30.counter).toBe(2);
    });

    it("validates PUT /networking against the networking group's own field defs", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/networking", { method: "PUT", body: JSON.stringify({ Hostname: "" }) });
        expect((await response.json()).result.Hostname).toBe("Invalid"); // below minLength: 1

        const ok = await fetch("/networking", { method: "PUT", body: JSON.stringify({ Hostname: "new-name" }) });
        expect((await ok.json()).result.Hostname).toBe("Valid");
        expect((await (await fetch("/networking")).json()).Hostname).toBe("new-name");
    });

    it("validates PUT /system's SystemCmd against the fixed real command set", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const ok = await fetch("/system", { method: "PUT", body: JSON.stringify({ SystemCmd: "reboot" }) });
        expect((await ok.json()).result.SystemCmd).toBe("Valid");

        const bad = await fetch("/system", { method: "PUT", body: JSON.stringify({ SystemCmd: "not-a-real-command" }) });
        expect((await bad.json()).result.SystemCmd).toBe("Invalid");
    });

    it("increments a TS-suffixed leaf by exactly 1 on jitter, jitters a plain number, and leaves a non-number leaf untouched", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/measurements");
        const body = await response.json();

        expect(body.SCD30.TS).toBe(1001); // timestamp-looking key: always +1, never randomized
        expect(body.SCD30.Model).toBe("SCD30"); // non-number leaf: untouched
        expect(body.SCD30.CO2).toBeGreaterThan(590);
        expect(body.SCD30.CO2).toBeLessThan(610);
    });

    it("silently ignores a PUT /sensors group key that isn't a real sensor, applying the real ones normally", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/sensors", {
            method: "PUT",
            body: JSON.stringify({ BOGUS: { SomeField: 1 }, SCD30: { MeasInt: 10 } }),
        });
        const body = await response.json();

        expect(body.result.BOGUS).toBeUndefined();
        expect(body.result.SCD30.MeasInt).toBe("Valid");
    });

    it("rejects an unsupported HTTP method with a 405", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/sensors", { method: "DELETE" });
        expect(response.status).toBe(405);
    });

    it("injects exactly one network failure via controls.nextFailure, then serves normally again", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("network") };
        uninstall = installMockFetch(DEFS, DATA, controls);

        await expect(fetch("/sensors")).rejects.toThrow(/failed to fetch/i);
        expect(controls.nextFailure).toBeUndefined(); // one-shot - consumed after firing

        const response = await fetch("/sensors");
        expect(response.ok).toBe(true);
    });

    it("injects exactly one HTTP error status via controls.nextFailure, then serves normally again", async () => {
        const controls = { nextFailure: /** @type {"network" | number | undefined} */ (500) };
        uninstall = installMockFetch(DEFS, DATA, controls);

        const response = await fetch("/sensors");
        expect(response.ok).toBe(false);
        expect(response.status).toBe(500);

        const second = await fetch("/sensors");
        expect(second.ok).toBe(true);
    });

    it("injects a malformed-body failure: HTTP 200 with res:ERR/code:1, matching the real backend's own make_response(1) exactly", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("malformed-body") };
        uninstall = installMockFetch(DEFS, DATA, controls);

        const response = await fetch("/sensors", { method: "PUT", body: "not valid json {" });
        expect(response.ok).toBe(true); // HTTP-level success, per SPECIFICATION.md Part A.8
        const body = await response.json();
        expect(body).toEqual({ res: "ERR", code: 1, descr: "Invalid JSON request", result: {} });
        expect(controls.nextFailure).toBeUndefined();
    });

    it("injects a torn-json failure: HTTP 200 with an unparseable body, simulating a corrupted transmission", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("torn-json") };
        uninstall = installMockFetch(DEFS, DATA, controls);

        const response = await fetch("/sensors");
        expect(response.ok).toBe(true);
        await expect(response.json()).rejects.toThrow();
    });

    it("injects an empty-body failure: HTTP 200 with a zero-length body", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("empty-body") };
        uninstall = installMockFetch(DEFS, DATA, controls);

        const response = await fetch("/sensors");
        expect(response.ok).toBe(true);
        expect(await response.text()).toBe("");
    });

    it("injects a partial-result failure: one submitted field silently missing from a successful PUT's result", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("partial-result") };
        uninstall = installMockFetch(DEFS, DATA, controls);

        const response = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { MeasInt: 10, ContMeas: false } }) });
        const body = await response.json();
        expect(body.res).toBe("OK"); // the real backend's own gap: overall envelope still reports OK
        expect(Object.keys(body.result.SCD30)).toHaveLength(1); // one of the two submitted fields is missing
        expect(controls.nextFailure).toBeUndefined();
    });
});
