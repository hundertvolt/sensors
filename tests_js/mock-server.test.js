// Tests js/mock-server.js's installMockFetch(): each route answered as the real server answers it - validation and
// result words, masking, dispatched commands, the clock-driven values, delays and the error-counter reset.
import { afterEach, describe, expect, it, vi } from "vitest";
import samples from "../mockdata/samples.json";
import radioShapes from "../tests/_radio_shape_cases.json";
import { validateDefinitions } from "../js/definitions.js";
import { composeMockData, installMockFetch } from "../js/mock-server.js";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";

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
                        { key: "TempOffset", label: "Temperature Offset", kind: "number", min: 0, max: 655.35, float: true, resolution: 0.01 },
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
                        { key: "ProxyPW", label: "Proxy Password", kind: "string", minLength: 0, maxLength: 63, mask: true },
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
                                { value: "resetconfig", label: "Reset to defaults" },
                                { value: "erasefram", label: "Erase FRAM" },
                            ],
                        },
                    ],
                },
                { key: "build", label: "Build", fields: [{ key: "FirmwareVersion", label: "Firmware Version", kind: "readonly", path: ["build", "FirmwareVersion"] }] },
            ],
        },
        {
            key: "notification",
            label: "Notification",
            rest: { get: "/notification", put: "/notification" },
            pollGroup: "settings",
            groups: [
                { key: "pause", label: "Pause Notifications", submit: true, fields: [{ key: "PauseTime", label: "Pause Time", kind: "number", min: 0, max: 3600, dispatch: true, statusPath: ["notification", "PauseTime"] }] },
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
                                { key: "T", label: "Time (s)", kind: "number", min: 0.5, max: 60.0, float: true },
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
        SCD30: { CO2: 600, TS: 1000, SensorUptime: 120, Model: "SCD30" },
        ISL29125: { Lux: 300, RGB: { R: 0.02, G: 0.03, B: 0.01 }, CCT: null, TS: 1000 },
    },
    sensorsConfig: { SCD30: { MeasInterval: 5, TempOffset: 12.35, AmbPres: 1013, ForceCalRef: 400 }, SGP40: {}, ISL29125: { IRCompAdjust: 40 } },
    networkingConfig: {
        Hostname: "fixture-host", PW: "hunter2hunter2", HotspotPW: "fixture-hotspot", ProxyPW: "fixture-proxy", NTPHost: "ntp.fixture-host",
        DNSFallback: "192.0.2.53",
    },
    systemConfig: { build: { FirmwareVersion: "fixture-version" } },
    notificationConfig: {},
    status: {
        networking: {},
        system: {},
        sensors: {},
        notification: {},
        errcount: { SCD30: { counter: 2, history: [{ num: 1, type: /** @type {const} */ ("E") }] } },
    },
};

// src/asy_webserver_service.py's _LED_BUSY_DESCR: the envelope's descr when a running signal refused LightCmdLED.
const LED_BUSY_DESCR = "LED busy - retry later";
// src/asy_base_classes.py's COUNTER_CAP: the value every server counter saturates at.
const COUNTER_CAP = 2 ** 30 - 1;

/** @typedef {import("../js/mock-server.js").MockFetchControls} MockFetchControls */
/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */

/**
 * DEFS with the field `key` replaced by `change(field)`, for a case that needs another definition of it.
 * @param {string} key
 * @param {(field: FieldDef) => FieldDef} change
 * @returns {import("../js/definitions.js").SiteDefinitions}
 */
function defsWith(key, change) {
    const groups = (/** @type {import("../js/definitions.js").Section} */ section) => section.groups.map((group) => (
        "fields" in group ? { ...group, fields: group.fields.map((field) => (field.key === key ? change(field) : field)) } : group
    ));
    return { ...DEFS, sections: DEFS.sections.map((section) => ({ ...section, groups: groups(section) })) };
}

// The page's PUT header (js/render.js): without it the server, and the mock with it, refuses the body as code 1.
const JSON_HEADERS = { "Content-Type": "application/json" };

/**
 * PUTs `body` as JSON text; resolves to the parsed envelope.
 * @param {string} path
 * @param {unknown} body
 */
function putJson(path, body) {
    return fetch(path, { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify(body) }).then((response) => response.json());
}

/**
 * GETs `path`; resolves to the parsed body.
 * @param {string} path
 */
function getJson(path) {
    return fetch(path).then((response) => response.json());
}

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
        uninstall = undefined; // a later test that installs nothing must not re-run this one's restore
        vi.useRealTimers(); // also ends a vi.setSystemTime() Date mock
        vi.unstubAllGlobals(); // after the uninstall, which restores the fetch it found
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
        const invalid = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { MeasInterval: 3000 } }) });
        expect((await invalid.json()).result.SCD30.MeasInterval).toBe("Invalid"); // 3000 > max 1800

        const unchanged = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { MeasInterval: 5 } }) });
        expect((await unchanged.json()).result.SCD30.MeasInterval).toBe("Unchanged"); // fixture already has MeasInterval: 5
    });

    it("marks an in-range changed value as Valid and persists it for the next GET", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const put = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { MeasInterval: 10 } }) });
        // The whole envelope, as make_response(0, result=...) builds it: the catalog's text for code 0.
        expect(await put.json()).toEqual({ res: "OK", code: 0, descr: "Command executed", result: { SCD30: { MeasInterval: "Valid" } } });

        const get = await fetch("/sensors");
        expect((await get.json()).SCD30.MeasInterval).toBe(10);
    });

    it("compares a number with a resolution in its steps and stores the value rounded to one, as the device reads it back", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        // 12.345 and 12.346 round to the stored 12.35's step; 12.3449 rounds to 12.34, 12.36 is a step away.
        expect((await putJson("/sensors", { SCD30: { TempOffset: 12.345 } })).result.SCD30.TempOffset).toBe("Unchanged");
        expect((await putJson("/sensors", { SCD30: { TempOffset: 12.346 } })).result.SCD30.TempOffset).toBe("Unchanged");
        expect((await putJson("/sensors", { SCD30: { TempOffset: 12.3449 } })).result.SCD30.TempOffset).toBe("Valid");
        expect((await getJson("/sensors")).SCD30.TempOffset).toBe(12.34);
        expect((await putJson("/sensors", { SCD30: { TempOffset: 12.36 } })).result.SCD30.TempOffset).toBe("Valid");
        expect((await getJson("/sensors")).SCD30.TempOffset).toBe(12.36);
    });

    // The server's per-kind validation (SPECIFICATION.md Part A.8): a JSON int is a valid float, a number with a
    // fraction no valid int, and a bool never a number.
    it.each([["TempOffset", 50, "Valid", 50], ["TempOffset", true, "Invalid", 12.35], ["MeasInterval", 5.5, "Invalid", 5], ["MeasInterval", 6, "Valid", 6], ["MeasInterval", true, "Invalid", 5]])(
        "answers PUT /sensors' %s: %j with %s and reads back %j",
        async (key, value, word, stored) => {
            uninstall = installMockFetch(DEFS, DATA);
            expect((await putJson("/sensors", { SCD30: { [key]: value } })).result.SCD30[key]).toBe(word);
            expect((await getJson("/sensors")).SCD30[key]).toBe(stored);
        },
    );

    it("answers Invalid for a readonly key and stores nothing, as for any key no writable field lists", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        expect((await putJson("/system", { FirmwareVersion: "9.9.9" })).result).toEqual({ FirmwareVersion: "Invalid" });
        expect(await getJson("/system")).toEqual({ build: { FirmwareVersion: "fixture-version" } });
    });

    it("resets error counters and refills history with no-error placeholders (real reset() never shrinks it)", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const answer = await putJson("/status", { ResetErrors: true });
        expect(answer).toEqual({ res: "OK", code: 0, descr: "Command executed", result: { ResetErrors: "Valid" } });

        const body = await getJson("/status");
        expect(body.errcount.SCD30.counter).toBe(0);
        expect(body.errcount.SCD30.history).toEqual([{ num: 0, type: "N" }]);
    });

    it("leaves error counters untouched when ResetErrors is absent", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        expect((await putJson("/status", {})).result).toEqual({});

        expect((await getJson("/status")).errcount.SCD30.counter).toBe(2);
    });

    it.each([[false], [1], ["true"], [null]])("answers ResetErrors: %j with Invalid and resets nothing, as _put_status() does", async (value) => {
        uninstall = installMockFetch(DEFS, DATA);
        expect((await putJson("/status", { ResetErrors: value, Bogus: true })).result).toEqual({ ResetErrors: "Invalid", Bogus: "Invalid" });
        expect((await getJson("/status")).errcount.SCD30.counter).toBe(2);
    });

    it("validates PUT /networking against the networking group's own field defs", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/networking", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ Hostname: "" }) });
        expect((await response.json()).result.Hostname).toBe("Invalid"); // below minLength: 1

        const ok = await fetch("/networking", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ Hostname: "new-name" }) });
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
        const response = await fetch("/networking", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ [key]: value }) });
        expect((await response.json()).result[key]).toBe(expected);
    });

    it("accepts a string field's schema special before its length bounds, as the server does", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const open = await fetch("/networking", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PW: "" }) });
        expect((await open.json()).result.PW).toBe("Valid"); // "" = open network, though below minLength 8
        const short = await fetch("/networking", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PW: "short" }) });
        expect((await short.json()).result.PW).toBe("Invalid"); // not a special: the bound still holds
    });

    it("bounds a byte-bounded string in UTF-8 bytes, not characters", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const tooLong = await fetch("/networking", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SSID: "é".repeat(32) }) });
        expect((await tooLong.json()).result.SSID).toBe("Invalid"); // 32 characters, 64 bytes
        const fits = await fetch("/networking", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SSID: "é".repeat(16) }) });
        expect((await fits.json()).result.SSID).toBe("Valid"); // 16 characters, 32 bytes
    });

    it.each([["reboot"], ["bootloader"], ["mempause"], ["resetconfig"], ["erasefram"]])("validates PUT /system's SystemCmd against the fixed real command set: %j answers Valid", async (word) => {
        uninstall = installMockFetch(DEFS, DATA);
        const ok = await fetch("/system", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SystemCmd: word }) });
        expect((await ok.json()).result.SystemCmd).toBe("Valid");

        const bad = await fetch("/system", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SystemCmd: "not-a-real-command" }) });
        expect((await bad.json()).result.SystemCmd).toBe("Invalid");
    });

    // The definitions-to-mock half of the SystemCmd mirror: every command a generated device offers, the mock runs.
    it.each(DEVICE_IDS)("answers Valid for every SystemCmd option device %s's generated definitions offer", async (device) => {
        const defs = /** @type {import("../js/definitions.js").SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device));
        const fields = defs.sections.flatMap((section) => section.groups.flatMap((group) => ("fields" in group ? group.fields : [])));
        const words = (fields.find((field) => field.key === "SystemCmd")?.options ?? []).map((option) => option.value);
        expect(words.length).toBeGreaterThan(0);
        uninstall = installMockFetch(defs, composeMockData(defs, /** @type {import("../js/definitions.js").MockSamples} */ (samples)));
        const answers = await Promise.all(words.map(async (word) => {
            const response = await fetch("/system", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SystemCmd: word }) });
            return (await response.json()).result.SystemCmd;
        }));
        expect(answers).toEqual(words.map(() => "Valid"));
    });

    // One argument per case: it.each() spreads an array case into its arguments.
    it.each([["Reboot"], ["reboot "], [" reboot"], ["reb"], ["rebootx"], ["ResetConfig"], ["reset_config"], ["resetconfig "], ["EraseFRAM"], ["erase_fram"], [" erasefram"], [1], [null], [["reboot"]], [{}]])("answers the SystemCmd near miss %j with Invalid: only the whole word runs a command", async (value) => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/system", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SystemCmd: value }) });
        expect((await response.json()).result.SystemCmd).toBe("Invalid");
    });

    it("derives SystemCmd's words from its options, not a hand-kept list", async () => {
        const extra = { value: "selftest", label: "Self test" };
        uninstall = installMockFetch(defsWith("SystemCmd", (field) => ({ ...field, options: [...(field.options ?? []), extra] })), DATA);
        expect((await putJson("/system", { SystemCmd: "selftest" })).result.SystemCmd).toBe("Valid");
        expect((await putJson("/system", { SystemCmd: "reboot" })).result.SystemCmd).toBe("Valid");
    });

    it("answers Invalid for a key no group of the endpoint lists, a dispatch key sent to another endpoint included", async () => {
        // Mirrors _apply_settings_groups(): every submitted key gets a word, an unknown one "Invalid".
        uninstall = installMockFetch(DEFS, DATA);
        const networking = await (await fetch("/networking", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ NoSuchKey: 1, SystemCmd: "reboot" }) })).json();
        expect(networking.res).toBe("OK");
        expect(networking.result).toEqual({ NoSuchKey: "Invalid", SystemCmd: "Invalid" });

        const system = await (await fetch("/system", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SystemCmd: "reboot", Bogus: 1, PauseTime: 60 }) })).json();
        expect(system.result).toEqual({ SystemCmd: "Valid", Bogus: "Invalid", PauseTime: "Invalid" });

        const notification = await (await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ Bogus: 1 }) })).json();
        expect(notification.result).toEqual({ Bogus: "Invalid" });
    });

    it("never persists SystemCmd into systemConfig - it's a dispatched action, not a stored setting (matches real GET /system, which never includes it)", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        await fetch("/system", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SystemCmd: "reboot" }) });

        const get = await fetch("/system");
        expect("SystemCmd" in (await get.json())).toBe(false);

        // A repeat submission must still report Valid, not Unchanged - SystemCmd is dispatched
        // fresh every time, it never "changes" or "stays the same" against a stored value.
        const again = await fetch("/system", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SystemCmd: "reboot" }) });
        expect((await again.json()).result.SystemCmd).toBe("Valid");
    });

    it("validates PUT /notification's PauseTime range like the real backend's _dispatch_notification_pause() and dispatches it to the live status value, not a stored setting", async () => {
        // Mirrors _dispatch_notification_pause(): PauseTime is a runtime action, checked
        // 0-3600, never persisted or "Unchanged", read back from GET /status. It follows
        // checked_int(), so a fraction is rejected outright rather than truncated (Part A.8).
        uninstall = installMockFetch(DEFS, DATA);

        const tooLarge = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PauseTime: 3601 }) });
        expect((await tooLarge.json()).result.PauseTime).toBe("Invalid");
        const negative = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PauseTime: -1 }) });
        expect((await negative.json()).result.PauseTime).toBe("Invalid");
        const fractional = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PauseTime: 60.5 }) });
        expect((await fractional.json()).result.PauseTime).toBe("Invalid");
        const list = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PauseTime: [60] }) });
        expect((await list.json()).result.PauseTime).toBe("Invalid");
        const object = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PauseTime: { s: 60 } }) });
        expect((await object.json()).result.PauseTime).toBe("Invalid");

        const ok = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PauseTime: 60 }) });
        expect((await ok.json()).result.PauseTime).toBe("Valid");

        // Never leaks into GET /notification's flat settings...
        expect("PauseTime" in (await (await fetch("/notification")).json())).toBe(false);
        // ...but does show up as the live value under GET /status.
        expect((await (await fetch("/status")).json()).notification.PauseTime).toBe(60);

        // A repeat submission of the same value must still report Valid, not Unchanged.
        const again = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PauseTime: 60 }) });
        expect((await again.json()).result.PauseTime).toBe("Valid");
    });

    it("derives PauseTime's bounds from its field and writes it where its statusPath points", async () => {
        uninstall = installMockFetch(defsWith("PauseTime", (field) => ({ ...field, max: 7200 })), DATA);
        expect((await putJson("/notification", { PauseTime: 5000 })).result.PauseTime).toBe("Valid");
        expect((await getJson("/status")).notification.PauseTime).toBe(5000);
    });

    it("writes a dispatched number without a statusPath nowhere", async () => {
        const withoutStatusPath = (/** @type {FieldDef} */ field) => {
            const copy = { ...field };
            delete copy.statusPath;
            return copy;
        };
        uninstall = installMockFetch(defsWith("PauseTime", withoutStatusPath), DATA);
        expect((await putJson("/notification", { PauseTime: 60 })).result.PauseTime).toBe("Valid");
        expect((await getJson("/status")).notification).toEqual({});
    });

    it("derives LightCmdLED's members and bounds from its subFields", async () => {
        vi.setSystemTime(Date.now());
        /** @type {FieldDef[]} */
        const subFields = [
            { key: "R", label: "Red", kind: "number", min: 0, max: 255 },
            { key: "G", label: "Green", kind: "number", min: 0, max: 255 },
            { key: "T", label: "Time (s)", kind: "number", min: 0.5, max: 120.0, float: true },
        ];
        uninstall = installMockFetch(defsWith("LightCmdLED", (field) => ({ ...field, subFields })), DATA);
        expect((await putJson("/notification", { LightCmdLED: { R: 1, G: 2, T: 100 } })).result.LightCmdLED).toBe("Valid");
        advanceMockClockMs(100000);
        expect((await putJson("/notification", { LightCmdLED: { R: 1, G: 2, B: 3, T: 1 } })).result.LightCmdLED).toBe("Invalid");
    });

    it("dispatches PUT /notification's LightCmdLED like the real backend's _dispatch_notification_led()/_notification_led_callback(), never as a persisted setting", async () => {
        // Mirrors _dispatch_notification_led(): a malformed payload, a missing or extra member or a value outside
        // its schema answers "Invalid"; a well-formed command while a signal still runs answers "Failed".
        // Each started flash makes the next one wait out its t on the frozen mock clock.
        vi.setSystemTime(Date.now());
        uninstall = installMockFetch(DEFS, DATA);

        const notADict = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: "not-a-dict" }) });
        expect((await notADict.json()).result.LightCmdLED).toBe("Invalid");

        const missingSubfield = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30 } }) });
        expect((await missingSubfield.json()).result.LightCmdLED).toBe("Invalid");

        const extraMember = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30, T: 1, X: 0 } }) });
        expect((await extraMember.json()).result.LightCmdLED).toBe("Invalid");

        const nonNumeric = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: "abc", G: 20, B: 30, T: 1 } }) });
        expect((await nonNumeric.json()).result.LightCmdLED).toBe("Invalid");
        const boolT = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30, T: true } }) });
        expect((await boolT.json()).result.LightCmdLED).toBe("Invalid");

        // A fractional R/G/B is rejected, never truncated.
        const fractionalRgb = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 10.5, G: 20, B: 30, T: 1 } }) });
        expect((await fractionalRgb.json()).result.LightCmdLED).toBe("Invalid");

        // A fractional t is fine - it's float-typed, a blanket accept regardless of shape.
        const fractionalT = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30, T: 1.5 } }) });
        expect((await fractionalT.json()).result.LightCmdLED).toBe("Valid");
        advanceMockClockMs(1500);

        // Out-of-range members are rejected (legacy led_cmd()'s bounds).
        const outOfRange = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 9999, G: -50, B: 30, T: 999 } }) });
        expect((await outOfRange.json()).result.LightCmdLED).toBe("Invalid");
        const r256 = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 256, G: 0, B: 0, T: 1 } }) });
        expect((await r256.json()).result.LightCmdLED).toBe("Invalid");

        // Boundary values (0/255 for R/G/B, 0.5/60.0 for T) are still accepted - only genuinely
        // outside the range is rejected.
        const lowerBoundary = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 0, G: 255, B: 0, T: 0.5 } }) });
        expect((await lowerBoundary.json()).result.LightCmdLED).toBe("Valid");
        advanceMockClockMs(500);
        const upperBoundary = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 255, G: 0, B: 255, T: 60.0 } }) });
        expect((await upperBoundary.json()).result.LightCmdLED).toBe("Valid");
        advanceMockClockMs(60000);

        // Never persisted - doesn't leak into GET /notification's flat settings...
        expect("LightCmdLED" in (await (await fetch("/notification")).json())).toBe(false);

        // ...and a repeat identical submission still reports Valid, never Unchanged (dispatched
        // fresh every call, exactly like SystemCmd/PauseTime).
        const again = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30, T: 1 } }) });
        expect((await again.json()).result.LightCmdLED).toBe("Valid");
    });

    it("refuses PUT /notification's LightCmdLED with Failed while an accepted flash still runs, and accepts one again once its t has passed", async () => {
        // Mirrors NeopixelDriver.led_signal(): a REST command arriving while a signal is queued or
        // running is refused at once (owner, 2026-09-29), never queued behind it.
        vi.setSystemTime(Date.now());
        uninstall = installMockFetch(DEFS, DATA);
        const flash = JSON.stringify({ LightCmdLED: { R: 10, G: 20, B: 30, T: 2 } });

        const first = await (await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: flash })).json();
        expect(first.result.LightCmdLED).toBe("Valid");
        expect(first.descr).not.toBe(LED_BUSY_DESCR);
        const second = await (await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: flash })).json();
        expect([second.res, second.code, second.descr, second.result.LightCmdLED]).toEqual(["OK", 0, LED_BUSY_DESCR, "Failed"]);

        advanceMockClockMs(1999); // still inside the first flash
        const stillBusy = await (await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: flash })).json();
        expect([stillBusy.descr, stillBusy.result.LightCmdLED]).toEqual([LED_BUSY_DESCR, "Failed"]);

        advanceMockClockMs(1); // the first flash's t has passed; neither refusal extended it
        const afterward = await fetch("/notification", { method: "PUT", headers: JSON_HEADERS, body: flash });
        expect((await afterward.json()).result.LightCmdLED).toBe("Valid");
    });

    it("dispatches PUT /sensors' ForceCalRef: range-validated, never Unchanged, and GET reads back the last reference applied (400 on a fresh mock)", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        expect((await getJson("/sensors")).SCD30.ForceCalRef).toBe(400);

        const outOfRange = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { ForceCalRef: 399 } }) });
        expect((await outOfRange.json()).result.SCD30.ForceCalRef).toBe("Invalid");

        const applied = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { ForceCalRef: 900 } }) });
        expect((await applied.json()).result.SCD30.ForceCalRef).toBe("Valid");

        // The chip reports the most recently used reference within one power-up and 400 after power-up
        // (Interface Description 1.4.6).
        expect((await (await fetch("/sensors")).json()).SCD30.ForceCalRef).toBe(900);

        // Resubmitting the value just applied still reports Valid, never Unchanged - a direct
        // hardware write is re-run every request.
        const resubmit = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { ForceCalRef: 900 } }) });
        expect((await resubmit.json()).result.SCD30.ForceCalRef).toBe("Valid");
    });

    it("runs PUT /sensors' AmbPres whenever an apply carries it: never Unchanged, and GET reads back the value applied", async () => {
        // An always-executed field: the chip takes it whenever a PUT carries it, so even the stored value is re-sent.
        uninstall = installMockFetch(DEFS, DATA);
        for (const value of [1013, 1013, 950]) {
            // eslint-disable-next-line no-await-in-loop -- each PUT must follow the last one's store
            const res = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { AmbPres: value } }) });
            // eslint-disable-next-line no-await-in-loop -- same reasoning as above
            expect((await res.json()).result.SCD30.AmbPres).toBe("Valid");
        }
        expect((await (await fetch("/sensors")).json()).SCD30.AmbPres).toBe(950);
        const outOfRange = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { AmbPres: 600 } }) });
        expect((await outOfRange.json()).result.SCD30.AmbPres).toBe("Invalid");
    });

    it("dispatches PUT /sensors' ContMeas as a command: bool-only, never persisted or reported by GET", async () => {
        uninstall = installMockFetch(DEFS, DATA);

        const wrongType = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { ContMeas: "not-a-bool" } }) });
        expect((await wrongType.json()).result.SCD30.ContMeas).toBe("Invalid");

        // True (keep running) and False (stop) both report Valid in the mock - there's no real I2C
        // bus here to ever produce the real driver's "Failed" (a genuine stop-attempt bus fault).
        const stop = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { ContMeas: false } }) });
        expect((await stop.json()).result.SCD30.ContMeas).toBe("Valid");
        const resume = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: { ContMeas: true } }) });
        expect((await resume.json()).result.SCD30.ContMeas).toBe("Valid");

        // ContMeas has no schema entry on the real backend (the sensor can't report whether
        // continuous measurement is running) - never shows up in GET /sensors at all.
        expect("ContMeas" in (await (await fetch("/sensors")).json()).SCD30).toBe(false);
    });

    it("dispatches PUT /sensors' ResetVOC like the real backend's _push_reset_voc(): bool-only, always Valid, never persisted or reported by GET at all", async () => {
        uninstall = installMockFetch(DEFS, DATA);

        const wrongType = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SGP40: { ResetVOC: "not-a-bool" } }) });
        expect((await wrongType.json()).result.SGP40.ResetVOC).toBe("Invalid");

        // A command-only, repeatable trigger (SPECIFICATION.md C.5.2.1): every request re-fires it,
        // reported Valid every time, never Unchanged.
        const first = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SGP40: { ResetVOC: true } }) });
        expect((await first.json()).result.SGP40.ResetVOC).toBe("Valid");
        const again = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SGP40: { ResetVOC: true } }) });
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

        const applied = await fetch("/networking", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ PW: "a-real-new-password", HotspotPW: "a-new-hotspot-pw" }) });
        expect((await applied.json()).result).toEqual({ PW: "Valid", HotspotPW: "Valid" });

        // Still masked after a real, accepted write - GET never reflects the actual stored value.
        const after = await (await fetch("/networking")).json();
        expect([after.PW, after.HotspotPW]).toEqual(["********", "********"]);
    });

    it("masks every field the definitions mark mask: true, not a fixed list", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const body = await getJson("/networking");
        expect([body.PW, body.HotspotPW, body.ProxyPW, body.Hostname]).toEqual(["********", "********", "********", "fixture-host"]);
    });

    it("sets each measurement TS to the clock, jitters a plain number, and leaves a time key and a non-number leaf untouched", async () => {
        vi.setSystemTime(new Date("2026-10-13T06:00:00.900Z"));
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/measurements");
        const body = await response.json();

        expect(body.SCD30.TS).toBe(Math.floor(Date.now() / 1000)); // the clock's Unix seconds, never a jittered value
        expect(body.SCD30.SensorUptime).toBe(120); // a key ending Uptime never jitters
        expect(body.SCD30.Model).toBe("SCD30"); // non-number leaf: untouched
        expect(body.SCD30.CO2).toBeGreaterThan(590);
        expect(body.SCD30.CO2).toBeLessThan(610);
    });

    it("answers GET /status' UnixTime and WifiTS from the clock", async () => {
        vi.setSystemTime(new Date("2026-10-13T06:00:00.900Z"));
        uninstall = installMockFetch(DEFS, DATA);
        const body = await getJson("/status");
        const now = Math.floor(Date.now() / 1000);
        expect([body.system.UnixTime, body.networking.WifiTS]).toEqual([now, now]);
    });

    it.each([["system", "networking", "WifiTS"], ["networking", "system", "UnixTime"]])(
        "writes no clock value into a /status %s source sent as the unavailable marker; the %s source still gets its %s",
        async (degraded, healthy, clockKey) => {
            vi.setSystemTime(new Date("2026-10-13T06:00:00.900Z"));
            const status = { ...DATA.status, system: {}, networking: {}, [degraded]: { error: "unavailable" } };
            uninstall = installMockFetch(DEFS, { ...DATA, status });
            const body = await getJson("/status");
            expect(body[degraded]).toEqual({ error: "unavailable" });
            expect(body[healthy][clockKey]).toBe(Math.floor(Date.now() / 1000));
        },
    );

    it("steps SysUptime and WifiUptime by one per GET /status and saturates both at COUNTER_CAP", async () => {
        const status = { ...DATA.status, system: { SysUptime: COUNTER_CAP - 1 }, networking: { WifiUptime: COUNTER_CAP - 1 } };
        uninstall = installMockFetch(DEFS, { ...DATA, status });
        const first = await getJson("/status");
        const second = await getJson("/status");
        const uptimes = [first.system.SysUptime, first.networking.WifiUptime, second.system.SysUptime, second.networking.WifiUptime];
        expect(uptimes).toEqual([COUNTER_CAP, COUNTER_CAP, COUNTER_CAP, COUNTER_CAP]);
    });

    it("serves every other /status value as stored: LocalTime is the same over ten GETs", async () => {
        const localTime = { Year: 2026, Month: 10, MDay: 13, Hour: 8, Minute: 0, Second: 0, Weekday: 1 };
        const status = { ...DATA.status, system: { LocalTime: localTime, MemFree: 104960, BootSignature: 1754568003 } };
        uninstall = installMockFetch(DEFS, { ...DATA, status });
        const bodies = await Promise.all(Array.from({ length: 10 }, () => getJson("/status")));
        const served = bodies.map((body) => [body.system.LocalTime, body.system.MemFree, body.system.BootSignature]);
        expect(served).toEqual(Array.from({ length: 10 }, () => [localTime, 104960, 1754568003]));
    });

    it("answers at once with no timer when controls.delayMs is unset", async () => {
        vi.useFakeTimers();
        uninstall = installMockFetch(DEFS, DATA, {});
        const answers = Promise.all([fetch("/status"), fetch("/sensors")]);
        expect(vi.getTimerCount()).toBe(0);
        expect((await answers).map((response) => response.status)).toEqual([200, 200]);
    });

    it("delays every answer by controls.delayMs, a fixed time", async () => {
        vi.useFakeTimers();
        uninstall = installMockFetch(DEFS, DATA, { delayMs: 250 });
        let answered = false;
        const pending = fetch("/status").then((response) => {
            answered = true;
            return response;
        });
        await vi.advanceTimersByTimeAsync(249);
        expect(answered).toBe(false);
        await vi.advanceTimersByTimeAsync(1);
        expect(answered).toBe(true);
        expect((await pending).status).toBe(200);
    });

    it("jitters a nested measurement sub-object's leaves too, not just the top level", async () => {
        // The ISL29125's body is the first with a third level; without the recursion those leaves
        // sit static forever, which reads as a broken renderer. Math.random is pinned to its maximum
        // so the expectations are exact: below 1 the spread is 5% and the rounding keeps 4 decimals.
        vi.spyOn(Math, "random").mockReturnValue(1);
        vi.setSystemTime(new Date("2026-10-13T06:00:00.900Z"));
        uninstall = installMockFetch(DEFS, DATA);
        const body = await (await fetch("/measurements")).json();

        expect(body.ISL29125.TS).toBe(Math.floor(Date.now() / 1000)); // the timestamp: the clock, never jittered
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
        const accepted = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ ISL29125: { Calibrate: true } }) });
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
            const res = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ ISL29125: { Calibrate: true } }) });
            // eslint-disable-next-line no-await-in-loop -- same reasoning as above
            expect((await res.json()).result.ISL29125.Calibrate).toBe("Valid");
        }
    });

    it("never composes a sensor sample's command value, so GET /sensors never echoes a command as a setting", async () => {
        /** @type {import("../js/definitions.js").MockSamples} */
        const commandSamples = {
            measurements: { SCD30: { CO2: 600 } },
            sensorsConfig: { SCD30: { MeasInterval: 5 }, SGP40: { ResetVOC: true }, ISL29125: { IRCompAdjust: 40, Calibrate: true } },
            networkingConfig: {}, systemConfig: {}, notificationConfig: {},
            status: { networking: {}, system: {}, sensors: {}, notification: {} },
            errcount: {},
        };
        const data = composeMockData(DEFS, commandSamples);
        expect(data.sensorsConfig).toEqual({ SCD30: { MeasInterval: 5 }, SGP40: {}, ISL29125: { IRCompAdjust: 40 } });
        uninstall = installMockFetch(DEFS, data);
        expect(await getJson("/sensors")).toEqual({ SCD30: { MeasInterval: 5 }, SGP40: {}, ISL29125: { IRCompAdjust: 40 } });
    });

    it("answers Invalid for a PUT /sensors key that isn't a real sensor, applying the real ones normally", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch("/sensors", {
            method: "PUT",
            headers: JSON_HEADERS,
            body: JSON.stringify({ BOGUS: { SomeField: 1 }, SCD30: { MeasInterval: 10 } }),
        });
        const body = await response.json();

        expect(body.result.BOGUS).toBe("Invalid");
        expect(body.result.SCD30.MeasInterval).toBe("Valid");
    });

    it.each([[5], [null], [[1]], ["x"]])("answers a PUT /sensors entry %j that is not an object with Invalid in place of its field map", async (entry) => {
        uninstall = installMockFetch(DEFS, DATA);
        const body = await (await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ SCD30: entry }) })).json();
        expect(body.result).toEqual({ SCD30: "Invalid" });
    });

    it.each([["DELETE", "/sensors"], ["POST", "/status"], ["PUT", "/measurements"]])("rejects %s %s, a method its route does not take, with make_response(405) and HTTP 405", async (method, path) => {
        uninstall = installMockFetch(DEFS, DATA);
        const response = await fetch(path, { method });
        expect(response.status).toBe(405);
        // The status is its code, and the envelope the catalog's (make_response(405)).
        expect(await response.json()).toEqual({ res: "ERR", code: 405, descr: "Method not allowed", result: {} });
    });

    it("intercepts only the routes the definitions declare, passing every other path through", async () => {
        const passedThrough = vi.fn(() => Promise.resolve(new Response("passed through", { status: 299 })));
        vi.stubGlobal("fetch", passedThrough); // the fetch the mock passes through to; afterEach restores the real one
        const defs = { ...DEFS, sections: DEFS.sections.filter((section) => section.key !== "notification") };
        uninstall = installMockFetch(defs, DATA);
        expect(await (await fetch("/notification")).text()).toBe("passed through");
        expect((await fetch("/networking")).status).toBe(200);
        expect(passedThrough).toHaveBeenCalledTimes(1);
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
        // The status is its code, with the catalog's text (make_response(500)).
        expect(await response.json()).toEqual({ res: "ERR", code: 500, descr: "Internal server error", result: {} });

        const second = await fetch("/sensors");
        expect(second.ok).toBe(true);
    });

    it("answers an injected status the catalog does not list with make_response()'s Unknown error", async () => {
        const controls = { nextFailure: /** @type {"network" | number | undefined} */ (503) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const response = await fetch("/status");
        expect(response.status).toBe(503);
        expect(await response.json()).toEqual({ res: "ERR", code: 503, descr: "Unknown error", result: {} });
    });

    it("injects a malformed-body failure: HTTP 200 with res:ERR/code:1, matching the real backend's own make_response(1) exactly", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("malformed-body") };
        uninstall = installMockFetch(DEFS, DATA, controls);

        const response = await fetch("/sensors", { method: "PUT", headers: JSON_HEADERS, body: "not valid json {" });
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

    // Mirrors _body_as_dict(): a body request.json cannot parse, or one that parses to anything but an
    // object, answers make_response(1) with HTTP 200 on every PUT route.
    it.each([["/sensors", "nope"], ["/sensors", "[1,2]"], ["/networking", "\"text\""], ["/system", "null"], ["/status", "5"], ["/notification", "{"]])(
        "answers PUT %s with the body %s by make_response(1), HTTP 200",
        async (path, body) => {
            uninstall = installMockFetch(DEFS, DATA);
            const response = await fetch(path, { method: "PUT", headers: JSON_HEADERS, body });
            expect(response.status).toBe(200);
            expect(await response.json()).toEqual({ res: "ERR", code: 1, descr: "Invalid JSON request", result: {} });
        },
    );

    // Mirrors Microdot's Request.json: a body is parsed only under the exact type application/json before any
    // ";", so _body_as_dict() refuses every other request, whatever its body says.
    it.each([["no Content-Type", {}], ["text/plain", { "Content-Type": "text/plain;charset=UTF-8" }], ["a differently cased type", { "Content-Type": "Application/JSON" }]])(
        "answers a PUT with %s by make_response(1), HTTP 200, and applies nothing",
        async (_case, headers) => {
            uninstall = installMockFetch(DEFS, DATA);
            const response = await fetch("/networking", { method: "PUT", headers, body: JSON.stringify({ Hostname: "new-name" }) });
            expect(response.status).toBe(200);
            expect(await response.json()).toEqual({ res: "ERR", code: 1, descr: "Invalid JSON request", result: {} });
            expect((await getJson("/networking")).Hostname).toBe("fixture-host");
        },
    );

    it("accepts the JSON type with a parameter, as Microdot reads only the type before the first \";\" (guard)", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const headers = { "Content-Type": "application/json; charset=utf-8" };
        const response = await fetch("/networking", { method: "PUT", headers, body: JSON.stringify({ Hostname: "new-name" }) });
        expect((await response.json()).result).toEqual({ Hostname: "Valid" });
    });

    it("injects a group-failure on the next PUT: every attempted key answers Failed in an OK envelope, then once only", async () => {
        const controls = /** @type {MockFetchControls} */ ({ nextFailure: "group-failure" });
        uninstall = installMockFetch(DEFS, DATA, controls);
        await getJson("/sensors");
        expect(controls.nextFailure).toBe("group-failure"); // a GET leaves it for the next PUT

        const sensors = await putJson("/sensors", { SCD30: { MeasInterval: 10, AmbPres: 950 }, ISL29125: { IRCompAdjust: 41 } });
        expect(sensors).toEqual({ res: "OK", code: 0, descr: "Command executed", result: { SCD30: { MeasInterval: "Failed", AmbPres: "Failed" }, ISL29125: { IRCompAdjust: "Failed" } } });
        expect(controls.nextFailure).toBeUndefined();
        expect((await putJson("/networking", { Hostname: "next-host" })).result).toEqual({ Hostname: "Valid" });

        controls.nextFailure = "group-failure";
        expect((await putJson("/networking", { Hostname: "other-host", Bogus: 1 })).result).toEqual({ Hostname: "Failed", Bogus: "Failed" });
    });
});
