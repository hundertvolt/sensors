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
    ],
};

const DATA = {
    measurements: { SCD30: { CO2: 600, TS: 1000 } },
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
});
