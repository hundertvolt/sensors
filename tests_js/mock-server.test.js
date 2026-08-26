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
                        { key: "ForceCalRef", label: "Forced Calibration Reference", kind: "number", min: 400, max: 2000 },
                    ],
                },
                {
                    key: "SGP40",
                    label: "SGP40",
                    submit: true,
                    fields: [{ key: "SGPResetVOC", label: "Reset VOC Index", kind: "toggle" }],
                },
            ],
        },
        {
            key: "networking",
            label: "Networking",
            rest: { get: "/networking", put: "/networking" },
            pollGroup: "settings",
            groups: [
                {
                    key: "identity",
                    label: "Identity",
                    submit: true,
                    fields: [
                        { key: "Hostname", label: "Hostname", kind: "string", minLength: 1, maxLength: 63 },
                        { key: "PW", label: "Wi-Fi Password", kind: "string", minLength: 8, maxLength: 63, mask: true },
                    ],
                },
            ],
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
        {
            key: "system",
            label: "System",
            rest: { get: "/system", put: "/system" },
            pollGroup: "settings",
            groups: [
                {
                    key: "command",
                    label: "System Command",
                    submit: true,
                    fields: [
                        {
                            key: "SystemCmd",
                            label: "Command",
                            kind: "enum",
                            options: [
                                { value: "reboot", label: "Reboot" },
                                { value: "bootloader", label: "Reboot into bootloader" },
                                { value: "mempause", label: "Pause backups for 5 minutes" },
                            ],
                        },
                    ],
                },
            ],
        },
        {
            key: "notification",
            label: "Notification",
            rest: { get: "/notification", put: "/notification" },
            pollGroup: "settings",
            groups: [
                { key: "pause", label: "Pause Notifications", submit: true, fields: [{ key: "PauseTime", label: "Pause Time", kind: "number", min: 0, max: 3600 }] },
                {
                    key: "flash",
                    label: "Manual Flash Command",
                    submit: true,
                    fields: [
                        {
                            key: "lightCmdLED",
                            label: "LED Flash",
                            kind: "composite",
                            subFields: [
                                { key: "r", label: "Red", kind: "number", min: 0, max: 255 },
                                { key: "g", label: "Green", kind: "number", min: 0, max: 255 },
                                { key: "b", label: "Blue", kind: "number", min: 0, max: 255 },
                                { key: "t", label: "Time (s)", kind: "number", min: 0.5, max: 60.0 },
                            ],
                        },
                    ],
                },
            ],
        },
    ],
};

const DATA = {
    measurements: { SCD30: { CO2: 600, TS: 1000, Model: "SCD30" } },
    sensorsConfig: { SCD30: { MeasInt: 5, ForceCalRef: 400 }, SGP40: {} },
    networkingConfig: { Hostname: "wozi", PW: "hunter2hunter2" },
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
        const invalid = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { MeasInt: 3000 } }) });
        expect((await invalid.json()).result.SCD30.MeasInt).toBe("Invalid"); // 3000 > max 1800

        const unchanged = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { MeasInt: 5 } }) });
        expect((await unchanged.json()).result.SCD30.MeasInt).toBe("Unchanged"); // fixture already has MeasInt: 5
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

    it("never persists SystemCmd into systemConfig - it's a dispatched action, not a stored setting (matches real GET /system, which never includes it)", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        await fetch("/system", { method: "PUT", body: JSON.stringify({ SystemCmd: "reboot" }) });

        const get = await fetch("/system");
        expect("SystemCmd" in (await get.json())).toBe(false);

        // A repeat submission must still report Valid, not Unchanged - SystemCmd is dispatched
        // fresh every time, it never "changes" or "stays the same" against a stored value.
        const again = await fetch("/system", { method: "PUT", body: JSON.stringify({ SystemCmd: "reboot" }) });
        expect((await again.json()).result.SystemCmd).toBe("Valid");
    });

    it("validates PUT /notification's PauseTime range like the real backend's _dispatch_notification_pause() and dispatches it to the live status value, not a stored setting", async () => {
        // Real backend behavior this mirrors (src/asy_webserver_service.py's
        // _dispatch_notification_pause()): PauseTime is a runtime action - range-checked 0-3600,
        // never persisted to config storage, never reported "Unchanged", and its current value is
        // read back from GET /status's notification.PauseTime, never GET /notification. Now reuses
        // config_manager.py's own coerce_numeric() policy (SPECIFICATION.md Part A.8) - a
        // fractional value is rejected outright, not truncated.
        uninstall = installMockFetch(DEFS, DATA);

        const tooLarge = await fetch("/notification", { method: "PUT", body: JSON.stringify({ PauseTime: 3601 }) });
        expect((await tooLarge.json()).result.PauseTime).toBe("Invalid");
        const negative = await fetch("/notification", { method: "PUT", body: JSON.stringify({ PauseTime: -1 }) });
        expect((await negative.json()).result.PauseTime).toBe("Invalid");
        const fractional = await fetch("/notification", { method: "PUT", body: JSON.stringify({ PauseTime: 60.5 }) });
        expect((await fractional.json()).result.PauseTime).toBe("Invalid");

        const ok = await fetch("/notification", { method: "PUT", body: JSON.stringify({ PauseTime: 60 }) });
        expect((await ok.json()).result.PauseTime).toBe("Valid");

        // Never leaks into GET /notification's flat settings...
        expect("PauseTime" in (await (await fetch("/notification")).json())).toBe(false);
        // ...but does show up as the live value under GET /status.
        expect((await (await fetch("/status")).json()).notification.PauseTime).toBe(60);

        // A repeat submission of the same value must still report Valid, not Unchanged.
        const again = await fetch("/notification", { method: "PUT", body: JSON.stringify({ PauseTime: 60 }) });
        expect((await again.json()).result.PauseTime).toBe("Valid");
    });

    it("dispatches PUT /notification's lightCmdLED like the real backend's _dispatch_notification_led()/_notification_led_callback(), never as a persisted setting", async () => {
        // Real behavior this mirrors: "Invalid" only for a non-dict payload; every subfield
        // missing, non-numeric, (for the int-typed r/g/b) fractional, or out-of-range is rejected
        // via config_manager.py's coerce_numeric()/type_or_range_error() (SPECIFICATION.md Part
        // A.8) and reported "Failed" (never "Invalid") - r/g/b/t's shared int/float coercion +
        // range policy is now the same one every schema-backed field gets, matching legacy's own
        // led_cmd() bounds (r/g/b 0-255, t 0.5-60.0) rather than the src/ backend's old
        // silent-clamp/floor behavior.
        uninstall = installMockFetch(DEFS, DATA);

        const notADict = await fetch("/notification", { method: "PUT", body: JSON.stringify({ lightCmdLED: "not-a-dict" }) });
        expect((await notADict.json()).result.lightCmdLED).toBe("Invalid");

        const missingSubfield = await fetch("/notification", { method: "PUT", body: JSON.stringify({ lightCmdLED: { r: 10, g: 20, b: 30 } }) });
        expect((await missingSubfield.json()).result.lightCmdLED).toBe("Failed");

        const nonNumeric = await fetch("/notification", { method: "PUT", body: JSON.stringify({ lightCmdLED: { r: "abc", g: 20, b: 30, t: 1 } }) });
        expect((await nonNumeric.json()).result.lightCmdLED).toBe("Failed");

        // A fractional r/g/b is rejected outright, not truncated - the int<->float coercion policy
        // applied to lightCmdLED too (superseding the old raw int()/float() truncating casts).
        const fractionalRgb = await fetch("/notification", { method: "PUT", body: JSON.stringify({ lightCmdLED: { r: 10.5, g: 20, b: 30, t: 1 } }) });
        expect((await fractionalRgb.json()).result.lightCmdLED).toBe("Failed");

        // A fractional t is fine - it's float-typed, a blanket accept regardless of shape.
        const fractionalT = await fetch("/notification", { method: "PUT", body: JSON.stringify({ lightCmdLED: { r: 10, g: 20, b: 30, t: 1.5 } }) });
        expect((await fractionalT.json()).result.lightCmdLED).toBe("Valid");

        // Out-of-range r/g/b/t is now rejected, matching legacy's own led_cmd() bounds.
        const outOfRange = await fetch("/notification", { method: "PUT", body: JSON.stringify({ lightCmdLED: { r: 9999, g: -50, b: 30, t: 999 } }) });
        expect((await outOfRange.json()).result.lightCmdLED).toBe("Failed");

        // Boundary values (0/255 for r/g/b, 0.5/60.0 for t) are still accepted - only genuinely
        // outside the range is rejected.
        const lowerBoundary = await fetch("/notification", { method: "PUT", body: JSON.stringify({ lightCmdLED: { r: 0, g: 255, b: 0, t: 0.5 } }) });
        expect((await lowerBoundary.json()).result.lightCmdLED).toBe("Valid");
        const upperBoundary = await fetch("/notification", { method: "PUT", body: JSON.stringify({ lightCmdLED: { r: 255, g: 0, b: 255, t: 60.0 } }) });
        expect((await upperBoundary.json()).result.lightCmdLED).toBe("Valid");

        // Never persisted - doesn't leak into GET /notification's flat settings...
        expect("lightCmdLED" in (await (await fetch("/notification")).json())).toBe(false);

        // ...and a repeat identical submission still reports Valid, never Unchanged (dispatched
        // fresh every call, exactly like SystemCmd/PauseTime).
        const again = await fetch("/notification", { method: "PUT", body: JSON.stringify({ lightCmdLED: { r: 10, g: 20, b: 30, t: 1 } }) });
        expect((await again.json()).result.lightCmdLED).toBe("Valid");
    });

    it("dispatches PUT /sensors' ForceCalRef like the real backend's set_forced_recalibration_reference(): range-validated but never Unchanged, and GET always reads back the fixed real-hardware constant 400 regardless of what was applied", async () => {
        uninstall = installMockFetch(DEFS, DATA);

        const outOfRange = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { ForceCalRef: 399 } }) });
        expect((await outOfRange.json()).result.SCD30.ForceCalRef).toBe("Invalid");

        const applied = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { ForceCalRef: 900 } }) });
        expect((await applied.json()).result.SCD30.ForceCalRef).toBe("Valid");

        // Real SCD30 register limitation (src/asy_scd30_driver.py's get_forced_recalibration_reference()
        // docstring): the calibration update is permanent, but this readback always reports 400, never
        // whatever was just applied.
        expect((await (await fetch("/sensors")).json()).SCD30.ForceCalRef).toBe(400);

        // Resubmitting the exact fixture-seeded value (400) still reports Valid, never Unchanged - a
        // direct hardware write is re-run every request, with no stored value to compare against.
        const resubmit = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { ForceCalRef: 400 } }) });
        expect((await resubmit.json()).result.SCD30.ForceCalRef).toBe("Valid");
    });

    it("dispatches PUT /sensors' ContMeas like the real backend's _set_dict_cfg() ContMeas branch: bool-only, always Valid, never persisted or reported by GET at all", async () => {
        uninstall = installMockFetch(DEFS, DATA);

        const wrongType = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { ContMeas: "not-a-bool" } }) });
        expect((await wrongType.json()).result.SCD30.ContMeas).toBe("Invalid");

        // True (keep running) and False (stop) both report Valid in the mock - there's no real I2C
        // bus here to ever produce the real driver's "Failed" (a genuine stop-attempt bus fault).
        const stop = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { ContMeas: false } }) });
        expect((await stop.json()).result.SCD30.ContMeas).toBe("Valid");
        const resume = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { ContMeas: true } }) });
        expect((await resume.json()).result.SCD30.ContMeas).toBe("Valid");

        // ContMeas has no schema entry on the real backend (the sensor can't report whether
        // continuous measurement is running) - never shows up in GET /sensors at all.
        expect("ContMeas" in (await (await fetch("/sensors")).json()).SCD30).toBe(false);
    });

    it("dispatches PUT /sensors' SGPResetVOC like the real backend's _push_reset_voc(): bool-only, always Valid, never persisted or reported by GET at all", async () => {
        uninstall = installMockFetch(DEFS, DATA);

        const wrongType = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SGP40: { SGPResetVOC: "not-a-bool" } }) });
        expect((await wrongType.json()).result.SGP40.SGPResetVOC).toBe("Invalid");

        // A command-only, repeatable trigger (SPECIFICATION.md C.5.2.1): every request re-fires it,
        // reported Valid every time, never Unchanged.
        const first = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SGP40: { SGPResetVOC: true } }) });
        expect((await first.json()).result.SGP40.SGPResetVOC).toBe("Valid");
        const again = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SGP40: { SGPResetVOC: true } }) });
        expect((await again.json()).result.SGP40.SGPResetVOC).toBe("Valid");

        // SGPResetVOC is a special-alone schema field, deliberately excluded from get_dict_cfg() -
        // never in ConfigManager's cache, so never shows up in GET /sensors at all.
        expect("SGPResetVOC" in (await (await fetch("/sensors")).json()).SGP40).toBe(false);
    });

    it("masks PW on every GET /networking like the real backend's _mask_pw(), regardless of what was actually applied", async () => {
        uninstall = installMockFetch(DEFS, DATA);

        // Fixture-seeded value is never echoed in plaintext, even before any write.
        expect((await (await fetch("/networking")).json()).PW).toBe("********");

        const applied = await fetch("/networking", { method: "PUT", body: JSON.stringify({ PW: "a-real-new-password" }) });
        expect((await applied.json()).result.PW).toBe("Valid");

        // Still masked after a real, accepted write - GET never reflects the actual stored value.
        expect((await (await fetch("/networking")).json()).PW).toBe("********");
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
