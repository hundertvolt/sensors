import { afterEach, describe, expect, it, vi } from "vitest";
import radioShapes from "../tests/_radio_shape_cases.json";
import { validateDefinitions } from "../js/definitions.js";
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
                        { key: "MeasInterval", label: "Measurement Interval", kind: "number", min: 2, max: 1800 },
                        {
                            key: "AmbPres", label: "Ambient Pressure", kind: "number", min: 700, max: 1400, alwaysExecuted: true,
                            specialValues: [{ value: 0, meaning: "Compensation off / use Altitude" }],
                        },
                        { key: "ContMeas", label: "Continuous Measurement", kind: "toggle", alwaysExecuted: true },
                        { key: "ForceCalRef", label: "Forced Calibration Reference", kind: "number", min: 400, max: 2000, alwaysExecuted: true },
                    ],
                },
                {
                    key: "SGP40",
                    label: "SGP40",
                    submit: true,
                    fields: [{ key: "ResetVOC", label: "Reset VOC Index", kind: "toggle", dispatch: true }],
                },
                {
                    key: "ISL29125",
                    label: "ISL29125",
                    submit: true,
                    fields: [
                        { key: "IRCompAdjust", label: "IR Compensation Adjust", kind: "number", min: 0, max: 63 },
                        { key: "Calibrate", label: "Calibrate Gain Ratio", kind: "toggle", dispatch: true },
                    ],
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
                        { key: "SSID", label: "Wi-Fi SSID", kind: "string", minLength: 0, maxLength: 32, byteLength: true },
                        { key: "Country", label: "Country", kind: "string", minLength: 2, maxLength: 2, byteLength: true, shape: "countryCode" },
                        { key: "Hostname", label: "Hostname", kind: "string", minLength: 1, maxLength: 63, byteLength: true, shape: "hostLabel" },
                        {
                            key: "PW", label: "Wi-Fi Password", kind: "string", minLength: 8, maxLength: 63, mask: true, byteLength: true,
                            specialValues: [{ value: "", meaning: "Open network" }],
                        },
                        { key: "HotspotPW", label: "Hotspot Password", kind: "string", minLength: 8, maxLength: 63, mask: true, byteLength: true },
                    ],
                },
                {
                    key: "ntp",
                    label: "NTP Time Sync",
                    submit: true,
                    fields: [{ key: "NTPHost", label: "NTP Server Address", kind: "string", minLength: 3, maxLength: 253, shape: "hostName" }],
                },
                {
                    key: "dns",
                    label: "DNS Fallback",
                    submit: true,
                    fields: [{ key: "DNSFallback", label: "DNS Fallback Servers", kind: "string", minLength: 0, maxLength: 47, shape: "ipv4List" }],
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
                    fields: [{ key: "ResetErrors", label: "Confirm", kind: "toggle", dispatch: true }],
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
                            dispatch: true,
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
                { key: "pause", label: "Pause Notifications", submit: true, fields: [{ key: "PauseTime", label: "Pause Time", kind: "number", min: 0, max: 3600, dispatch: true }] },
                {
                    key: "flash",
                    label: "Manual Flash Command",
                    submit: true,
                    fields: [
                        {
                            key: "LightCmdLED",
                            label: "LED Flash",
                            kind: "composite",
                            dispatch: true,
                            subFields: [
                                { key: "R", label: "Red", kind: "number", min: 0, max: 255 },
                                { key: "G", label: "Green", kind: "number", min: 0, max: 255 },
                                { key: "B", label: "Blue", kind: "number", min: 0, max: 255 },
                                { key: "T", label: "Time (s)", kind: "number", min: 0.5, max: 60.0 },
                            ],
                        },
                    ],
                },
            ],
        },
    ],
};

const DATA = {
    measurements: {
        SCD30: { CO2: 600, TS: 1000, Model: "SCD30" },
        ISL29125: { Lux: 300, RGB: { R: 0.02, G: 0.03, B: 0.01 }, CCT: null, TS: 1000 },
    },
    sensorsConfig: { SCD30: { MeasInterval: 5, AmbPres: 1013, ForceCalRef: 400 }, SGP40: {}, ISL29125: { IRCompAdjust: 40 } },
    networkingConfig: { Hostname: "fixture-host", PW: "hunter2hunter2", HotspotPW: "fixture-hotspot", NTPHost: "ntp.fixture-host", DNSFallback: "192.0.2.53" },
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

/**
 * Moves the frozen mock clock forward; vi.setSystemTime() mocks Date only, so timers stay real.
 * @param {number} ms
 */
function advanceMockClockMs(ms) {
    vi.setSystemTime(Date.now() + ms);
}

describe("installMockFetch", () => {
    /** @type {(() => void) | undefined} */
    let uninstall;

    afterEach(() => {
        uninstall?.();
        vi.useRealTimers(); // also ends a vi.setSystemTime() Date mock
    });

    it("runs on fixture definitions the site's own validator accepts", () => {
        expect(validateDefinitions(DEFS)).toEqual([]);
    });

    it("answers GET /sensors from the fixture", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/sensors");
        const body = await response.json();
        expect(body.SCD30.MeasInterval).toBe(5);
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
        const invalid = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { MeasInterval: 3000 } }) });
        expect((await invalid.json()).result.SCD30.MeasInterval).toBe("Invalid"); // 3000 > max 1800

        const unchanged = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { MeasInterval: 5 } }) });
        expect((await unchanged.json()).result.SCD30.MeasInterval).toBe("Unchanged"); // fixture already has MeasInterval: 5
    });

    it("marks an in-range changed value as Valid and persists it for the next GET", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const put = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { MeasInterval: 10 } }) });
        expect((await put.json()).result.SCD30.MeasInterval).toBe("Valid");

        const get = await fetch("/sensors");
        expect((await get.json()).SCD30.MeasInterval).toBe(10);
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

    // One shared corpus with src/ and buildgen/: three implementations of each string shape, one list.
    /** @type {Record<string, {accept: string[], reject: string[]}>} */
    const SHAPES = radioShapes;
    const NETWORKING_FIELDS = DEFS.sections.flatMap((section) => (section.key === "networking" ? section.groups : []))
        .flatMap((group) => ("fields" in group ? group.fields : []));
    /** @type {[string, string, string, string][]} */
    const SHAPE_CASES = Object.entries(SHAPES).flatMap(([shape, { accept, reject }]) => {
        const field = NETWORKING_FIELDS.find((f) => f.shape === shape);
        if (field === undefined) {
            return [];
        }
        return [
            ...accept.map((value) => /** @type {[string, string, string, string]} */ ([shape, field.key, value, "Valid"])),
            ...reject.map((value) => /** @type {[string, string, string, string]} */ ([shape, field.key, value, "Invalid"])),
        ];
    });

    it("finds a fixture field for every shape the shared corpus names", () => {
        expect(new Set(SHAPE_CASES.map(([shape]) => shape))).toEqual(new Set(Object.keys(SHAPES)));
    });

    it.each(SHAPE_CASES)("answers a %s field (%s) PUT of %j with %s, as the server's shape check does", async (_shape, key, value, expected) => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/networking", { method: "PUT", body: JSON.stringify({ [key]: value }) });
        expect((await response.json()).result[key]).toBe(expected);
    });

    it("accepts a string field's schema special before its length bounds, as the server does", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const open = await fetch("/networking", { method: "PUT", body: JSON.stringify({ PW: "" }) });
        expect((await open.json()).result.PW).toBe("Valid"); // "" = open network, though below minLength 8
        const short = await fetch("/networking", { method: "PUT", body: JSON.stringify({ PW: "short" }) });
        expect((await short.json()).result.PW).toBe("Invalid"); // not a special: the bound still holds
    });

    it("bounds a byte-bounded string in UTF-8 bytes, not characters", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const tooLong = await fetch("/networking", { method: "PUT", body: JSON.stringify({ SSID: "é".repeat(32) }) });
        expect((await tooLong.json()).result.SSID).toBe("Invalid"); // 32 characters, 64 bytes
        const fits = await fetch("/networking", { method: "PUT", body: JSON.stringify({ SSID: "é".repeat(16) }) });
        expect((await fits.json()).result.SSID).toBe("Valid"); // 16 characters, 32 bytes
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
        // Mirrors _dispatch_notification_pause(): PauseTime is a runtime action, checked
        // 0-3600, never persisted or "Unchanged", read back from GET /status. It follows
        // checked_int(), so a fraction is rejected outright rather than truncated (Part A.8).
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

    it("dispatches PUT /notification's LightCmdLED like the real backend's _dispatch_notification_led()/_notification_led_callback(), never as a persisted setting", async () => {
        // Mirrors the real behavior: "Invalid" only for a non-dict payload; a missing, non-numeric,
        // fractional or out-of-range subfield reports "Failed" (legacy's led_cmd() bounds, Part A.8).
        // Each started flash makes the next one wait out its t on the frozen mock clock.
        vi.setSystemTime(Date.now());
        uninstall = installMockFetch(DEFS, DATA);

        const notADict = await fetch("/notification", { method: "PUT", body: JSON.stringify({ LightCmdLED: "not-a-dict" }) });
        expect((await notADict.json()).result.LightCmdLED).toBe("Invalid");

        const missingSubfield = await fetch("/notification", { method: "PUT", body: JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30 } }) });
        expect((await missingSubfield.json()).result.LightCmdLED).toBe("Failed");

        const nonNumeric = await fetch("/notification", { method: "PUT", body: JSON.stringify({ LightCmdLED: { R: "abc", G: 20, B: 30, T: 1 } }) });
        expect((await nonNumeric.json()).result.LightCmdLED).toBe("Failed");

        // A fractional R/G/B is rejected outright, not truncated - the int<->float coercion policy
        // applied to LightCmdLED too (superseding the old raw int()/float() truncating casts).
        const fractionalRgb = await fetch("/notification", { method: "PUT", body: JSON.stringify({ LightCmdLED: { R: 10.5, G: 20, B: 30, T: 1 } }) });
        expect((await fractionalRgb.json()).result.LightCmdLED).toBe("Failed");

        // A fractional t is fine - it's float-typed, a blanket accept regardless of shape.
        const fractionalT = await fetch("/notification", { method: "PUT", body: JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30, T: 1.5 } }) });
        expect((await fractionalT.json()).result.LightCmdLED).toBe("Valid");
        advanceMockClockMs(1500);

        // Out-of-range R/G/B/T is now rejected, matching legacy's own led_cmd() bounds.
        const outOfRange = await fetch("/notification", { method: "PUT", body: JSON.stringify({ LightCmdLED: { R: 9999, G: -50, B: 30, T: 999 } }) });
        expect((await outOfRange.json()).result.LightCmdLED).toBe("Failed");

        // Boundary values (0/255 for R/G/B, 0.5/60.0 for T) are still accepted - only genuinely
        // outside the range is rejected.
        const lowerBoundary = await fetch("/notification", { method: "PUT", body: JSON.stringify({ LightCmdLED: { R: 0, G: 255, B: 0, T: 0.5 } }) });
        expect((await lowerBoundary.json()).result.LightCmdLED).toBe("Valid");
        advanceMockClockMs(500);
        const upperBoundary = await fetch("/notification", { method: "PUT", body: JSON.stringify({ LightCmdLED: { R: 255, G: 0, B: 255, T: 60.0 } }) });
        expect((await upperBoundary.json()).result.LightCmdLED).toBe("Valid");
        advanceMockClockMs(60000);

        // Never persisted - doesn't leak into GET /notification's flat settings...
        expect("LightCmdLED" in (await (await fetch("/notification")).json())).toBe(false);

        // ...and a repeat identical submission still reports Valid, never Unchanged (dispatched
        // fresh every call, exactly like SystemCmd/PauseTime).
        const again = await fetch("/notification", { method: "PUT", body: JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30, T: 1 } }) });
        expect((await again.json()).result.LightCmdLED).toBe("Valid");
    });

    it("refuses PUT /notification's LightCmdLED with Failed while an accepted flash still runs, and accepts one again once its t has passed", async () => {
        // Mirrors NeopixelDriver.led_signal(): a REST command arriving while a signal is queued or
        // running is refused at once (owner, 2026-09-29), never queued behind it.
        vi.setSystemTime(Date.now());
        uninstall = installMockFetch(DEFS, DATA);
        const flash = JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30, T: 2 } });

        const first = await fetch("/notification", { method: "PUT", body: flash });
        expect((await first.json()).result.LightCmdLED).toBe("Valid");
        const second = await fetch("/notification", { method: "PUT", body: flash });
        expect((await second.json()).result.LightCmdLED).toBe("Failed");

        advanceMockClockMs(1999); // still inside the first flash
        const stillBusy = await fetch("/notification", { method: "PUT", body: flash });
        expect((await stillBusy.json()).result.LightCmdLED).toBe("Failed");

        advanceMockClockMs(1); // the first flash's t has passed; neither refusal extended it
        const afterward = await fetch("/notification", { method: "PUT", body: flash });
        expect((await afterward.json()).result.LightCmdLED).toBe("Valid");
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

    it("runs PUT /sensors' AmbPres on every apply: never Unchanged, and GET reads back the value applied", async () => {
        // An always-executed field: the chip takes it on every PUT, so even the stored value is re-sent.
        uninstall = installMockFetch(DEFS, DATA);
        for (const value of [1013, 1013, 950]) {
            // eslint-disable-next-line no-await-in-loop -- each PUT must follow the last one's store
            const res = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { AmbPres: value } }) });
            // eslint-disable-next-line no-await-in-loop -- same reasoning as above
            expect((await res.json()).result.SCD30.AmbPres).toBe("Valid");
        }
        expect((await (await fetch("/sensors")).json()).SCD30.AmbPres).toBe(950);
        const outOfRange = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { AmbPres: 600 } }) });
        expect((await outOfRange.json()).result.SCD30.AmbPres).toBe("Invalid");
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

    it("dispatches PUT /sensors' ResetVOC like the real backend's _push_reset_voc(): bool-only, always Valid, never persisted or reported by GET at all", async () => {
        uninstall = installMockFetch(DEFS, DATA);

        const wrongType = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SGP40: { ResetVOC: "not-a-bool" } }) });
        expect((await wrongType.json()).result.SGP40.ResetVOC).toBe("Invalid");

        // A command-only, repeatable trigger (SPECIFICATION.md C.5.2.1): every request re-fires it,
        // reported Valid every time, never Unchanged.
        const first = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SGP40: { ResetVOC: true } }) });
        expect((await first.json()).result.SGP40.ResetVOC).toBe("Valid");
        const again = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SGP40: { ResetVOC: true } }) });
        expect((await again.json()).result.SGP40.ResetVOC).toBe("Valid");

        // ResetVOC is a special-alone schema field, deliberately excluded from get_dict_cfg() -
        // never in ConfigManager's cache, so never shows up in GET /sensors at all.
        expect("ResetVOC" in (await (await fetch("/sensors")).json()).SGP40).toBe(false);
    });

    it("masks PW (and HotspotPW) on every GET /networking, whatever was applied", async () => {
        uninstall = installMockFetch(DEFS, DATA);

        // Fixture-seeded values are never echoed in plaintext, even before any write.
        const before = await (await fetch("/networking")).json();
        expect([before.PW, before.HotspotPW]).toEqual(["********", "********"]);

        const applied = await fetch("/networking", { method: "PUT", body: JSON.stringify({ PW: "a-real-new-password", HotspotPW: "a-new-hotspot-pw" }) });
        expect((await applied.json()).result).toEqual({ PW: "Valid", HotspotPW: "Valid" });

        // Still masked after a real, accepted write - GET never reflects the actual stored value.
        const after = await (await fetch("/networking")).json();
        expect([after.PW, after.HotspotPW]).toEqual(["********", "********"]);
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

    it("jitters a nested measurement sub-object's leaves too, not just the top level", async () => {
        // The ISL29125's body is the first with a third level; without the recursion those leaves
        // sit static forever, which reads as a broken renderer. Math.random is pinned to its maximum
        // so the expectations are exact: below 1 the spread is 5% and the rounding keeps 4 decimals.
        const random = vi.spyOn(Math, "random").mockReturnValue(1);
        uninstall = installMockFetch(DEFS, DATA);
        const body = await (await fetch("/measurements")).json();
        random.mockRestore();

        expect(body.ISL29125.TS).toBe(1001); // top-level timestamp: still exactly +1
        expect(body.ISL29125.CCT).toBeNull(); // a null leaf is not a number - left alone
        expect(body.ISL29125.Lux).toBe(303); // at or above 1: unchanged, 300 + 1% of itself
        // The nested leaves, each moved by 5% of itself - which only happens at all if
        // jitterInPlace() recursed into the sub-object.
        expect(body.ISL29125.RGB.R).toBe(0.021);
        expect(body.ISL29125.RGB.G).toBe(0.0315);
        expect(body.ISL29125.RGB.B).toBe(0.0105);
    });

    it("never jitters a non-negative measurement leaf into a negative one", async () => {
        // A property of every leaf, not a check on one guard: a brightness of -0.01 is not plausible
        // and the real site renders it verbatim. Asserted over the whole body with Math.random at 0,
        // the most negative jitter there is, so a change to the spread rule fails here.
        const random = vi.spyOn(Math, "random").mockReturnValue(0);
        try {
            uninstall = installMockFetch(DEFS, DATA);
            const body = await (await fetch("/measurements")).json();

            /** @param {Record<string, unknown>} group @param {string} where */
            const assertNoNegativeLeaf = (group, where) => {
                for (const [key, value] of Object.entries(group)) {
                    if (value !== null && typeof value === "object") {
                        assertNoNegativeLeaf(/** @type {Record<string, unknown>} */ (value), `${where}.${key}`);
                    } else if (typeof value === "number") {
                        expect(value, `${where}.${key}`).toBeGreaterThanOrEqual(0);
                    }
                }
            };
            assertNoNegativeLeaf(body, "measurements");

            // And the values themselves, so this cannot pass by everything having gone to zero:
            // each normalised leaf moved by 5% of itself, and stayed a usable number.
            expect(body.ISL29125.RGB.R).toBe(0.019);
            expect(body.ISL29125.RGB.G).toBe(0.0285);
            expect(body.ISL29125.RGB.B).toBe(0.0095);
            expect(body.ISL29125.Lux).toBe(297); // at or above 1: 300 - 1% of itself
        } finally {
            random.mockRestore();
        }
    });

    it("omits the command-only Calibrate from GET readback, as it already does for ContMeas/ResetVOC", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const accepted = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ ISL29125: { Calibrate: true } }) });
        expect((await accepted.json()).result.ISL29125.Calibrate).toBe("Valid");

        const body = await (await fetch("/sensors")).json();
        expect("Calibrate" in body.ISL29125).toBe(false); // never echoed back as if persisted
        expect(body.ISL29125.IRCompAdjust).toBe(40); // its neighbours are unaffected
    });

    it("accepts Calibrate repeatedly - it is a trigger, not a one-shot", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        for (let attempt = 0; attempt < 3; attempt += 1) {
            // Sequential is the point: each PUT must be accepted after the previous one already
            // fired, which running them in parallel would not show.
            // eslint-disable-next-line no-await-in-loop -- see the comment above
            const res = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ ISL29125: { Calibrate: true } }) });
            // eslint-disable-next-line no-await-in-loop -- same reasoning as above
            expect((await res.json()).result.ISL29125.Calibrate).toBe("Valid");
        }
    });

    it("silently ignores a PUT /sensors group key that isn't a real sensor, applying the real ones normally", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/sensors", {
            method: "PUT",
            body: JSON.stringify({ BOGUS: { SomeField: 1 }, SCD30: { MeasInterval: 10 } }),
        });
        const body = await response.json();

        expect(body.result.BOGUS).toBeUndefined();
        expect(body.result.SCD30.MeasInterval).toBe("Valid");
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

        const response = await fetch("/sensors", { method: "PUT", body: JSON.stringify({ SCD30: { MeasInterval: 10, ContMeas: false } }) });
        const body = await response.json();
        expect(body.res).toBe("OK"); // the real backend's own gap: overall envelope still reports OK
        expect(Object.keys(body.result.SCD30)).toHaveLength(1); // one of the two submitted fields is missing
        expect(controls.nextFailure).toBeUndefined();
    });
});
