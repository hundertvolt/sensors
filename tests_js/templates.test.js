import { afterEach, describe, expect, it } from "vitest";
import { userEvent } from "vitest/browser";
import { ERR_COUNT_CAP, isUnavailable } from "../js/api-contract.js";
import { buildErrcountGroup, buildFieldGroupCard, buildNavDrawer, buildSectionShell, resetControl, updateErrcountGroup, updateFieldGroupValues } from "../js/templates.js";
import { formatFieldValue } from "../js/field-format.js";
import NTP_CLIENT_SOURCE from "../src/asy_ntp_client.py?raw";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";
import { mustQuery } from "./_dom_helpers.js";

/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */
/** @typedef {import("../js/definitions.js").FieldGroup} FieldGroup */
/** @typedef {import("../js/definitions.js").ErrcountGroup} ErrcountGroup */
/** @typedef {import("../js/templates.js").CardDisplay} CardDisplay */
/** @typedef {{counter: number, history?: {num: number, type: "N"|"E"|"W"}[]}} ErrcountEntry */

/** @type {CardDisplay} */
const AVAILABLE = { deviceNowS: null, isUnavailable: () => false };

/** @type {HTMLElement[]} */
const mounted = [];

afterEach(() => {
    for (const el of mounted.splice(0)) {
        el.remove();
    }
});

/**
 * Attaches `el` to the document until the test ends.
 * @template {HTMLElement} T
 * @param {T} el
 * @returns {T}
 */
function mount(el) {
    document.body.appendChild(el);
    mounted.push(el);
    return el;
}

/**
 * A GET body holding `value` where `field` reads it: under its path, else under its key.
 * @param {FieldDef} field
 * @param {unknown} value
 * @returns {Record<string, unknown>}
 */
function valuesFor(field, value) {
    /** @type {unknown} */
    let nested = value;
    for (const step of [...(field.path ?? [field.key])].reverse()) {
        nested = { [step]: nested };
    }
    return /** @type {Record<string, unknown>} */ (nested);
}

/**
 * A one-field group card, a submit group when `editable`, mounted; returns the field's wrapper.
 * @param {FieldDef} field
 * @param {unknown} value
 * @param {{editable?: boolean, display?: CardDisplay}} [options]
 * @returns {HTMLElement}
 */
function fieldCard(field, value, options = {}) {
    /** @type {FieldGroup} */
    const group = { key: "fixture", label: "Fixture", submit: options.editable === true, fields: [field] };
    const card = mount(buildFieldGroupCard(group, valuesFor(field, value), 0, options.display ?? AVAILABLE));
    return mustQuery(card, "[data-field-wrapper-key]");
}

// An editable number/string field has two ".field-description"-classed <p>s (the "Current
// value: …" caption, then the hint text) - the hint is always the last one.
/**
 * @param {HTMLElement} el
 * @returns {string | null}
 */
function hintText(el) {
    const nodes = el.querySelectorAll(".field-description");
    const last = nodes[nodes.length - 1];
    if (last === undefined) {
        throw new Error("Expected at least one .field-description");
    }
    return last.textContent;
}

/** @type {FieldDef} */
const EPOCH_FIELD = { key: "TS", label: "Timestamp", kind: "readonly", format: "epoch" };
/** @type {FieldDef} */
const BACKUP_TS_FIELD = {
    key: "SGP40_BackupTS",
    label: "SGP40 Last Backup",
    kind: "readonly",
    format: "epoch",
    path: ["SGP40", "BackupTS"],
    specialValues: [
        { value: null, meaning: "None since boot" },
        { value: 0, meaning: "No timestamp" },
    ],
};
/** @type {FieldDef} */
const RESET_REASON_FIELD = {
    key: "ResetReason",
    label: "Last Reset Reason",
    kind: "readonly",
    codes: { 1: "power-on", 3: "reboot command" },
};
/** @type {FieldDef} */
const CAL_LIGHT_FIELD = {
    key: "CalLight",
    label: "Calibration Light",
    kind: "readonly",
    codes: { 0: "not applicable now", 1: "suitable", 2: "too dark", 3: "too bright" },
    codeTones: { 0: "neutral", 1: "good", 2: "warn", 3: "warn" },
};
const DEVICE_NOW_S = 1_800_000_000;

describe("formatFieldValue", () => {
    it("shows an em dash for undefined/null", () => {
        expect(formatFieldValue({ key: "x", label: "X", kind: "readonly" }, undefined)).toBe("—");
        expect(formatFieldValue({ key: "x", label: "X", kind: "readonly" }, null)).toBe("—");
    });

    it("masks a masked field regardless of the underlying value", () => {
        expect(formatFieldValue({ key: "PW", label: "Password", kind: "string", mask: true }, "hunter2")).toBe("••••••••");
    });

    it("resolves an enum value to its label", () => {
        const field = {
            key: "OperationMode",
            label: "Mode",
            kind: /** @type {const} */ ("enum"),
            options: [{ value: 5, label: "Red + Green + Blue" }],
        };
        expect(formatFieldValue(field, 5)).toBe("Red + Green + Blue");
        expect(formatFieldValue(field, 99)).toBe("99"); // no matching option - falls back to the raw value
    });

    it("formats a gmtimestruct field from its real structured shape, not a pre-formatted string", () => {
        // Real shape: the generated module's _gmtimestruct_to_dict() (buildgen/codegen.py).
        const field = { key: "UTCTime", label: "UTC Time", kind: /** @type {const} */ ("readonly"), format: /** @type {const} */ ("gmtimestruct") };
        const value = { Year: 2025, Month: 8, MDay: 2, Hour: 8, Minute: 4, Second: 3, Weekday: 6 };
        expect(formatFieldValue(field, value)).toBe("2025-08-02 08:04:03");
    });

    it("reads a time struct missing one of its members as an invalid time value, never 'undefined'", () => {
        const field = { key: "UTCTime", label: "UTC Time", kind: /** @type {const} */ ("readonly"), format: /** @type {const} */ ("gmtimestruct") };
        expect(formatFieldValue(field, { Year: 2025, Month: 8, MDay: 2, Minute: 4, Second: 3 })).toBe("invalid time value");
        expect(formatFieldValue(field, { Year: 2025, Month: 8, MDay: 2, Hour: "8", Minute: 4, Second: 3 })).toBe("invalid time value");
        expect(formatFieldValue(field, "2025-08-02 08:04:03")).toBe("invalid time value");
    });

    it.each([
        [0, "0 s ago"],
        [119, "119 s ago"],
        [120, "2 min ago"],
        [7199, "119 min ago"],
        [7200, "2 h ago"],
        [172799, "47 h ago"],
        [172800, "2 d ago"],
    ])("shows a timestamp %i s before the device's clock as %s", (age, text) => {
        expect(formatFieldValue(EPOCH_FIELD, DEVICE_NOW_S - age, { deviceNowS: DEVICE_NOW_S })).toBe(text);
    });

    it("says the age is unknown while the device's clock is not known", () => {
        expect(formatFieldValue(EPOCH_FIELD, DEVICE_NOW_S, { deviceNowS: null })).toBe("age unknown");
        expect(formatFieldValue(EPOCH_FIELD, DEVICE_NOW_S)).toBe("age unknown");
    });

    it("reads a timestamp more than 5 s ahead of the device's clock as a clock mismatch, and up to 5 s as now", () => {
        expect(formatFieldValue(EPOCH_FIELD, DEVICE_NOW_S + 6, { deviceNowS: DEVICE_NOW_S })).toBe("clock mismatch");
        expect(formatFieldValue(EPOCH_FIELD, DEVICE_NOW_S + 5, { deviceNowS: DEVICE_NOW_S })).toBe("0 s ago");
    });

    it("shows a timestamp's special values as their text, never as a date or an age", () => {
        const context = { deviceNowS: DEVICE_NOW_S };
        expect(formatFieldValue(BACKUP_TS_FIELD, null, context)).toBe("None since boot");
        expect(formatFieldValue(BACKUP_TS_FIELD, 0, context)).toBe("No timestamp");
        expect(formatFieldValue(BACKUP_TS_FIELD, DEVICE_NOW_S - 30, context)).toBe("30 s ago");
    });

    it("leaves a timestamp without specials at the em dash when it is null", () => {
        expect(formatFieldValue(EPOCH_FIELD, null, { deviceNowS: DEVICE_NOW_S })).toBe("—");
    });

    // The `decimals` hint (SPECIFICATION.md Part H): no driver in src/ rounds any output, so this
    // is the one place a declared precision becomes a real property rather than an aspiration.
    it("honours a decimals hint on a number", () => {
        expect(formatFieldValue({ key: "H", label: "Hue", kind: "readonly", decimals: 1 }, 217.43859649122808)).toBe("217.4");
        expect(formatFieldValue({ key: "CCT", label: "CCT", kind: "readonly", decimals: 0 }, 4183.72)).toBe("4184");
        expect(formatFieldValue({ key: "R", label: "Red", kind: "readonly", decimals: 4 }, 0.02814159)).toBe("0.0281");
    });

    it("pads to the declared precision rather than only truncating", () => {
        expect(formatFieldValue({ key: "Lux", label: "Lux", kind: "readonly", decimals: 2 }, 12)).toBe("12.00");
    });

    it("leaves a null at the em dash even with a decimals hint", () => {
        // CCT is legitimately null in a dark room, and toFixed() on null would be a TypeError.
        expect(formatFieldValue({ key: "CCT", label: "CCT", kind: "readonly", decimals: 0 }, null)).toBe("—");
    });

    it("passes a non-number through untouched, never into toFixed()", () => {
        expect(formatFieldValue({ key: "Mode", label: "Mode", kind: "readonly", decimals: 2 }, "STA")).toBe("STA");
        expect(formatFieldValue({ key: "On", label: "On", kind: "readonly", decimals: 2 }, true)).toBe("true");
        expect(formatFieldValue({ key: "N", label: "N", kind: "readonly", decimals: 2 }, Number.NaN)).toBe("NaN");
        expect(formatFieldValue({ key: "I", label: "I", kind: "readonly", decimals: 2 }, Number.POSITIVE_INFINITY)).toBe("Infinity");
    });

    it("leaves a field with no decimals hint and no site default exactly as it was", () => {
        expect(formatFieldValue({ key: "Temp", label: "Temp", kind: "readonly" }, 23.100000000000001)).toBe("23.1");
        expect(formatFieldValue({ key: "CO2", label: "CO2", kind: "readonly" }, 612)).toBe("612");
    });

    it("rounds a fractional value with no decimals hint to the site default, an integer unchanged, a field's own decimals winning", () => {
        const context = { deviceNowS: null, defaultDecimals: 2 };
        expect(formatFieldValue({ key: "Temp", label: "Temp", kind: "readonly" }, 23.456, context)).toBe("23.46");
        expect(formatFieldValue({ key: "CO2", label: "CO2", kind: "readonly" }, 612, context)).toBe("612");
        expect(formatFieldValue({ key: "Hum", label: "Humidity", kind: "readonly", decimals: 1 }, 41.27, context)).toBe("41.3");
    });

    it("joins a list's items, and names an empty list as none", () => {
        const field = { key: "ConfigFaults", label: "Config Faults", kind: /** @type {const} */ ("readonly") };
        expect(formatFieldValue(field, ["WIFI", "NTP"])).toBe("WIFI, NTP");
        expect(formatFieldValue(field, [])).toBe("none");
    });

    it("lets an enum label win over a decimals hint", () => {
        const field = {
            key: "Resolution",
            label: "ADC Resolution",
            kind: /** @type {const} */ ("enum"),
            decimals: 2,
            options: [{ value: 16, label: "16 bit (flicker-rejecting)" }],
        };
        expect(formatFieldValue(field, 16)).toBe("16 bit (flicker-rejecting)");
    });
});

describe("field markup, through a one-field buildFieldGroupCard()", () => {
    it("renders a non-editable field as a plain value span, never an input", () => {
        const el = fieldCard({ key: "CO2", label: "CO2", unit: "ppm", kind: "readonly" }, 612);
        expect(el.querySelector("input")).toBeNull();
        expect(mustQuery(el, '[data-field-key="CO2"]').textContent).toBe("612");
    });

    it("renders a nested readonly field's own value, not [object Object]", () => {
        // The card resolves the path, so what reaches the field's markup is already the leaf.
        const el = fieldCard({ key: "R", label: "Red", kind: "readonly", path: ["RGB", "R"], decimals: 4 }, 0.02814159);
        expect(mustQuery(el, '[data-field-key="R"]').textContent).toBe("0.0281");
    });

    it("shows a min/max range hint for an editable number field", () => {
        const el = fieldCard({ key: "MeasInterval", label: "Measurement Interval", unit: "s", kind: "number", min: 2, max: 1800 }, 5, { editable: true });
        expect(hintText(el)).toContain("Valid values: 2 to 1800 s");
    });

    it("shows a length hint for an editable string field", () => {
        const el = fieldCard({ key: "Hostname", label: "Hostname", kind: "string", minLength: 1, maxLength: 63 }, "fixture-host", { editable: true });
        expect(hintText(el)).toContain("Length: 1 to 63 characters");
    });

    it("adds the UTF-8 byte bound to the length hint of a byte-bounded string", () => {
        const el = fieldCard({ key: "SSID", label: "Wi-Fi SSID", kind: "string", minLength: 0, maxLength: 32, byteLength: true }, "", { editable: true });
        expect(hintText(el)).toContain("Length: 0 to 32 characters, at most 32 bytes (UTF-8)");
    });

    it("names a host label's character set in its hint", () => {
        const el = fieldCard({ key: "Hostname", label: "Hostname", kind: "string", minLength: 1, maxLength: 32, shape: "hostLabel" }, "fixture-host", { editable: true });
        expect(hintText(el)).toContain("letters, digits and '-' only");
    });

    it("adds neither cue to a string with no byte bound and no shape", () => {
        const el = fieldCard({ key: "NTPHost", label: "NTP Server", kind: "string", minLength: 3, maxLength: 64 }, "pool.ntp.org", { editable: true });
        expect(hintText(el)).toBe("Length: 3 to 64 characters");
    });

    it("states a number field's resolution with its unit in the hint, and none without one", () => {
        /** @type {FieldDef} */
        const field = { key: "TempOffset", label: "Temperature Offset", unit: "°C", kind: "number", min: 0, max: 655.35, float: true };
        expect(hintText(fieldCard({ ...field, resolution: 0.01 }, 1.5, { editable: true }))).toContain("Resolution: 0.01 °C");
        expect(hintText(fieldCard(field, 1.5, { editable: true }))).not.toContain("Resolution");
    });

    it("lists a string field's special values in its hint, the value quoted", () => {
        /** @type {FieldDef} */
        const field = { key: "PW", label: "Wi-Fi Password", kind: "string", mask: true, minLength: 8, maxLength: 63, specialValues: [{ value: "", meaning: "Open network" }] };
        expect(hintText(fieldCard(field, "••••••••", { editable: true }))).toBe('Length: 8 to 63 characters · "" = Open network');
    });

    it("names the form a host name or an IPv4 list takes, from the server's own shape rules", () => {
        // The server's _ntp_host_ok() and _dns_fallback_ok() (src/asy_ntp_client.py); the list's bound is read from there.
        const listMax = /^_DNS_FALLBACK_MAX = const\((?<max>\d+)\)/mu.exec(NTP_CLIENT_SOURCE)?.groups?.max;
        expect(listMax).toBeDefined();
        /** @type {FieldDef} */
        const host = { key: "NTPHost", label: "NTP Server Address", kind: "string", minLength: 3, maxLength: 253, shape: "hostName" };
        expect(hintText(fieldCard(host, "pool.ntp.org", { editable: true }))).toBe("Length: 3 to 253 characters · a host name (letters, digits, '-' and '.') or an IPv4 address");
        /** @type {FieldDef} */
        const list = { key: "DNSFallback", label: "Fallback DNS Servers", kind: "string", minLength: 0, maxLength: 47, shape: "ipv4List" };
        expect(hintText(fieldCard(list, "1.1.1.1", { editable: true }))).toBe(`Length: 0 to 47 characters · up to ${listMax} IPv4 addresses, comma-separated, no spaces`);
    });

    it("adds no form hint to a country code, whose description states its form", () => {
        /** @type {FieldDef} */
        const field = { key: "Country", label: "Country", kind: "string", minLength: 2, maxLength: 2, shape: "countryCode", description: "Two uppercase letters (ISO 3166-1 alpha-2), e.g. DE." };
        expect(hintText(fieldCard(field, "DE", { editable: true }))).toBe("Length: 2 to 2 characters · Two uppercase letters (ISO 3166-1 alpha-2), e.g. DE.");
    });

    it("shows each special value's meaning in the description", () => {
        /** @type {FieldDef} */
        const field = {
            key: "AmbPres",
            label: "Ambient Pressure",
            unit: "hPa",
            kind: "number",
            min: 700,
            max: 1400,
            specialValues: [{ value: 0, meaning: "Compensation off / use Altitude" }],
        };
        expect(hintText(fieldCard(field, 1013, { editable: true }))).toContain("0 = Compensation off / use Altitude");
    });

    it("includes field.description in the hint text, alongside a range hint", () => {
        /** @type {FieldDef} */
        const field = { key: "MeasInterval", label: "Measurement Interval", kind: "number", min: 2, max: 1800, description: "How often the sensor takes a new reading." };
        const el = fieldCard(field, 5, { editable: true });
        expect(hintText(el)).toContain("Valid values: 2 to 1800");
        expect(hintText(el)).toContain("How often the sensor takes a new reading.");
    });

    it("renders an editable toggle that flips its own On/Off state with no network call", () => {
        const el = fieldCard({ key: "SelfCal", label: "Self-Cal", kind: "toggle" }, true, { editable: true });
        const button = mustQuery(el, '[data-field-key="SelfCal"]');
        expect(button.getAttribute("aria-pressed")).toBe("true");
        expect(button.textContent).toBe("On");

        button.click();

        expect(button.getAttribute("aria-pressed")).toBe("false");
        expect(button.textContent).toBe("Off");
        expect(button.dataset.value).toBe("false");
    });

    it("renders an always-executed toggle with no reported state as unset, then cycles On, Off, On", () => {
        const el = fieldCard({ key: "ContMeas", label: "Continuous Measurement", kind: "toggle", alwaysExecuted: true }, undefined, { editable: true });
        const button = mustQuery(el, '[data-field-key="ContMeas"]');
        expect(button.dataset.value).toBe("unset");
        expect(button.getAttribute("aria-pressed")).toBe("mixed");
        expect(button.textContent).toBe("—");
        /** @type {(string | null | undefined)[][]} */
        const seen = [];
        for (let i = 0; i < 3; i += 1) {
            button.click();
            seen.push([button.dataset.value, button.getAttribute("aria-pressed"), button.textContent]);
        }
        expect(seen).toEqual([
            ["true", "true", "On"],
            ["false", "false", "Off"],
            ["true", "true", "On"],
        ]);
    });

    it("renders a dispatch toggle with no reported state as Off, not unset", () => {
        const el = fieldCard({ key: "Calibrate", label: "Calibrate Gain Ratio", kind: "toggle", dispatch: true }, undefined, { editable: true });
        const button = mustQuery(el, '[data-field-key="Calibrate"]');
        expect(button.dataset.value).toBe("false");
        expect(button.textContent).toBe("Off");
    });

    it("renders an editable enum as a select with the current value pre-selected", () => {
        /** @type {FieldDef} */
        const field = {
            key: "SensingRange",
            label: "Sensing Range",
            kind: "enum",
            options: [
                { value: 0, label: "375 lux" },
                { value: 1, label: "10,000 lux" },
            ],
        };
        const select = /** @type {HTMLSelectElement} */ (mustQuery(fieldCard(field, 1, { editable: true }), '[data-field-key="SensingRange"]'));
        expect(select.value).toBe("1");
    });

    it("renders an editable enum with no matching current value as unselected, not silently defaulting to the first option (regression)", () => {
        // SystemCmd is write-only and never returned by GET /system (Part A.8), so currentValue
        // is always undefined. Without a blank placeholder a <select> auto-selects its first
        // option, so Apply alone PUT a reboot - confirmed live in Chromium before the fix.
        /** @type {FieldDef} */
        const field = {
            key: "SystemCmd",
            label: "Command",
            kind: "enum",
            options: [
                { value: "reboot", label: "Reboot" },
                { value: "bootloader", label: "Reboot into bootloader" },
                { value: "mempause", label: "Pause backups for 5 minutes" },
                { value: "resetconfig", label: "Reset to defaults" },
                { value: "erasefram", label: "Erase FRAM" },
            ],
        };
        const select = /** @type {HTMLSelectElement} */ (mustQuery(fieldCard(field, undefined, { editable: true }), '[data-field-key="SystemCmd"]'));
        expect(select.value).toBe("");
        for (const option of Array.from(select.options)) {
            if (option.value !== "") {
                expect(option.selected).toBe(false);
            }
        }
    });

    it("renders an editable composite field with one input per sub-field", () => {
        /** @type {FieldDef} */
        const field = {
            key: "LightCmdLED",
            label: "LED Flash",
            kind: "composite",
            subFields: [
                { key: "R", label: "Red", kind: "number" },
                { key: "G", label: "Green", kind: "number" },
            ],
        };
        const grid = mustQuery(fieldCard(field, undefined, { editable: true }), '[data-field-key="LightCmdLED"]');
        expect(grid.querySelectorAll("input")).toHaveLength(2);
        expect(mustQuery(grid, '[data-sub-field-key="R"]')).not.toBeNull();
    });

    it("renders an editable composite field with no subFields as an empty, non-crashing grid", () => {
        const grid = mustQuery(fieldCard({ key: "LightCmdLED", label: "LED Flash", kind: "composite" }, undefined, { editable: true }), '[data-field-key="LightCmdLED"]');
        expect(grid.querySelectorAll("input")).toHaveLength(0);
    });

    it("renders an editable number field pre-filled via a current-value caption, not the input's value", () => {
        const el = fieldCard({ key: "MeasInterval", label: "Measurement Interval", unit: "s", kind: "number", min: 2, max: 1800 }, 5, { editable: true });
        const input = /** @type {HTMLInputElement} */ (mustQuery(el, '[data-field-key="MeasInterval"]'));
        expect(input.value).toBe(""); // sparse-PUT convention: starts empty, not pre-filled with the current value
        expect(mustQuery(el, '[data-current-value-for="MeasInterval"]').textContent).toContain("5");
    });

    it("gives a masked input type=password and autocomplete=new-password, starting empty", () => {
        const el = fieldCard({ key: "PW", label: "Wi-Fi Password", kind: "string", mask: true, minLength: 8, maxLength: 63 }, "••••••••", { editable: true });
        const input = /** @type {HTMLInputElement} */ (mustQuery(el, '[data-field-key="PW"]'));
        expect(input.type).toBe("password");
        expect(input.getAttribute("autocomplete")).toBe("new-password");
        expect(input.value).toBe("");
    });

    // Distinct from data-field-key, which must keep pointing at the control itself for
    // collectGroupBody()/paint(): this tags the whole per-field wrapper, so a PUT result can
    // color that field's own box - Part H.3's per-field granularity beside the accent stripe.
    it("tags the field's own wrapper with a distinct data-field-wrapper-key, separate from the control's data-field-key", () => {
        const wrapper = fieldCard({ key: "CO2", label: "CO2", kind: "readonly" }, 612);
        expect(wrapper.dataset.fieldWrapperKey).toBe("CO2");
        // The wrapper is a different element from the control itself.
        expect(wrapper).not.toBe(mustQuery(wrapper, '[data-field-key="CO2"]'));
    });

    it("tags a composite field's own wrapper with data-field-wrapper-key too, distinct from the grid's data-field-key", () => {
        const wrapper = fieldCard({ key: "LightCmdLED", label: "LED Flash", kind: "composite", subFields: [{ key: "R", label: "Red", kind: "number" }] }, undefined, { editable: true });
        expect(wrapper.dataset.fieldWrapperKey).toBe("LightCmdLED");
        expect(wrapper).not.toBe(mustQuery(wrapper, '[data-field-key="LightCmdLED"]'));
    });
});

describe("field ids and labels", () => {
    /** @type {FieldGroup} */
    const SETTINGS_GROUP = {
        key: "SCD30",
        label: "SCD30",
        submit: true,
        fields: [
            { key: "MeasInterval", label: "Measurement Interval", unit: "s", kind: "number", min: 2, max: 1800 },
            { key: "SelfCal", label: "Self-Cal", kind: "toggle" },
            { key: "Mode", label: "Mode", kind: "enum", options: [{ value: 1, label: "One" }] },
            { key: "LightCmdLED", label: "LED Flash", kind: "composite", subFields: [{ key: "R", label: "Red", kind: "number" }] },
            { key: "FirmwareVersion", label: "Firmware", kind: "readonly" },
        ],
    };

    it("ids each control by its group and field index, never by its key, and binds its label to that id", () => {
        const card = mount(buildFieldGroupCard(SETTINGS_GROUP, { MeasInterval: 5, SelfCal: true, Mode: 1, FirmwareVersion: "1.0" }, 3, AVAILABLE));
        for (const [index, key] of [
            [0, "MeasInterval"],
            [1, "SelfCal"],
            [2, "Mode"],
        ]) {
            const wrapper = mustQuery(card, `[data-field-wrapper-key="${key}"]`);
            const control = mustQuery(wrapper, `[data-field-key="${key}"]`);
            expect(control.id).toBe(`field-3-${index}`);
            expect(/** @type {HTMLLabelElement} */ (mustQuery(wrapper, "label.field-label")).htmlFor).toBe(`field-3-${index}`);
        }
        expect(card.querySelector('[id^="field-MeasInterval"]')).toBeNull();
    });

    it("names a readonly value and a composite grid through a span label, with no label pointing at nothing", () => {
        const card = mount(buildFieldGroupCard(SETTINGS_GROUP, { FirmwareVersion: "1.0" }, 3, AVAILABLE));
        const readonly = mustQuery(card, '[data-field-wrapper-key="FirmwareVersion"]');
        expect(readonly.querySelector("label")).toBeNull();
        expect(mustQuery(readonly, "span.field-label").id).toBe("field-3-4-label");
        expect(mustQuery(readonly, '[data-field-key="FirmwareVersion"]').getAttribute("aria-labelledby")).toBe("field-3-4-label");

        const composite = mustQuery(card, '[data-field-wrapper-key="LightCmdLED"]');
        expect(mustQuery(composite, "span.field-label").id).toBe("field-3-3-label");
        const grid = mustQuery(composite, '[data-field-key="LightCmdLED"]');
        expect(grid.getAttribute("role")).toBe("group");
        expect(grid.getAttribute("aria-labelledby")).toBe("field-3-3-label");
        expect(composite.querySelector("label[for]")).toBeNull();

        for (const label of card.querySelectorAll("label[for]")) {
            expect(document.getElementById(/** @type {HTMLLabelElement} */ (label).htmlFor)).not.toBeNull();
        }
    });

    it("keeps the unit inside the label", () => {
        const card = mount(buildFieldGroupCard(SETTINGS_GROUP, {}, 0, AVAILABLE));
        expect(mustQuery(card, '[data-field-wrapper-key="MeasInterval"] label.field-label .field-unit').textContent).toBe(" [s]");
    });
});

describe("clear button and warning", () => {
    /** @type {FieldDef} */
    const DNS_FALLBACK_PLAIN = { key: "DNSFallback", label: "Fallback DNS Servers", kind: "string", minLength: 0, maxLength: 47, shape: "ipv4List" };
    const DNS_FALLBACK = { ...DNS_FALLBACK_PLAIN, clearable: true };

    it("puts a Clear button after a clearable string input, pointing at the input's id", () => {
        const el = fieldCard(DNS_FALLBACK, "1.1.1.1", { editable: true });
        const input = mustQuery(el, '[data-field-key="DNSFallback"]');
        const clear = /** @type {HTMLButtonElement} */ (mustQuery(el, "[data-clear-for]"));
        expect(clear.dataset.clearFor).toBe(input.id);
        expect(clear.type).toBe("button");
        expect(clear.classList.contains("action-button")).toBe(true);
        expect(clear.classList.contains("clear-button")).toBe(true);
        expect(clear.textContent).toBe("Clear");
        expect(input.nextElementSibling).toBe(clear);
    });

    it("gives no Clear button to a string that is not clearable, nor to a clearable one shown read-only", () => {
        expect(fieldCard(DNS_FALLBACK_PLAIN, "1.1.1.1", { editable: true }).querySelector("[data-clear-for]")).toBeNull();
        expect(fieldCard(DNS_FALLBACK, "1.1.1.1").querySelector("[data-clear-for]")).toBeNull();
    });

    it("builds a hidden warning naming the sibling's label after the caption of a field ignored while that sibling is set", () => {
        /** @type {FieldGroup} */
        const group = {
            key: "SCD30",
            label: "SCD30",
            submit: true,
            fields: [
                { key: "AmbPres", label: "Ambient Pressure", unit: "hPa", kind: "number", min: 700, max: 1400 },
                { key: "Altitude", label: "Altitude above sea level", unit: "m", kind: "number", min: 0, max: 65535, ignoredWhenSet: "AmbPres" },
            ],
        };
        const card = mount(buildFieldGroupCard(group, { AmbPres: 1013, Altitude: 0 }, 0, AVAILABLE));
        const wrapper = mustQuery(card, '[data-field-wrapper-key="Altitude"]');
        const warning = mustQuery(wrapper, "p.field-warning");
        expect(warning.dataset.shown).toBe("false");
        expect(warning.textContent).toBe("Ignored: Ambient Pressure is set.");
        expect(warning.previousElementSibling).toBe(mustQuery(wrapper, '[data-current-value-for="Altitude"]'));
        expect(mustQuery(card, '[data-field-wrapper-key="AmbPres"]').querySelector(".field-warning")).toBeNull();
    });
});

describe.each(DEVICE_IDS)("%s's generated code fields", (device) => {
    const defs = GENERATED_DEFINITIONS.get(device);
    const codeFields = (defs?.sections ?? []).flatMap((section) => section.groups.flatMap((group) => ("fields" in group ? group.fields : []))).filter((field) => field.codes !== undefined);

    it("render each code with its catalog text: a button with the description on click, or the toned text", () => {
        expect(codeFields.map((field) => field.key)).toEqual(expect.arrayContaining(["ResetReason", "State"]));
        for (const field of codeFields) {
            const [code, text] = Object.entries(field.codes ?? {})[0] ?? ["", ""];
            const el = fieldCard(field, Number(code));
            const value = mustQuery(el, `[data-field-key="${field.key}"]`);
            if (field.codeTones === undefined) {
                expect(value.tagName, field.key).toBe("BUTTON");
                value.click();
                expect(mustQuery(el, ".code-description").textContent, field.key).toBe(`${code}: ${text}`);
            } else {
                expect(value.textContent, field.key).toBe(`${text} (${code})`);
                expect(value.dataset.codeTone, field.key).toBe(field.codeTones[code]);
            }
        }
    });
});

describe("codes and timestamps on read-only values", () => {
    it("shows a code as a button with its number, whose click shows and hides its description after it", () => {
        const el = fieldCard(RESET_REASON_FIELD, 3);
        const button = /** @type {HTMLButtonElement} */ (mustQuery(el, "button.field-value.code-value"));
        expect(button.dataset.fieldKey).toBe("ResetReason");
        expect(button.type).toBe("button");
        expect(button.textContent).toBe("3");
        expect(button.getAttribute("aria-expanded")).toBe("false");

        button.click();
        expect(button.getAttribute("aria-expanded")).toBe("true");
        const description = /** @type {HTMLElement} */ (button.nextElementSibling);
        expect(description.classList.contains("code-description")).toBe(true);
        expect(description.textContent).toBe("3: reboot command");

        button.click();
        expect(button.getAttribute("aria-expanded")).toBe("false");
        expect(el.querySelector(".code-description")).toBeNull();
    });

    it("says a code with no catalog entry has no description", () => {
        const el = fieldCard(RESET_REASON_FIELD, 99);
        mustQuery(el, "button.code-value").click();
        expect(mustQuery(el, ".code-description").textContent).toBe("No description for code 99");
    });

    it("names a code button by its label and its number together", () => {
        const el = fieldCard(RESET_REASON_FIELD, 3);
        const button = mustQuery(el, "button.code-value");
        const names = (button.getAttribute("aria-labelledby") ?? "").split(" ").map((id) => document.getElementById(id)?.textContent);
        expect(names).toEqual(["Last Reset Reason", "3"]);
    });

    it("opens a code's description from the keyboard", async () => {
        const el = fieldCard(RESET_REASON_FIELD, 1);
        const button = mustQuery(el, "button.code-value");
        button.focus();
        await userEvent.keyboard("{Enter}");
        expect(mustQuery(el, ".code-description").textContent).toBe("1: power-on");
    });

    it("shows a toned code as its text and muted number, coloured by its tone", () => {
        const el = fieldCard(CAL_LIGHT_FIELD, 2);
        const value = mustQuery(el, '[data-field-key="CalLight"]');
        expect(value.tagName).toBe("SPAN");
        expect(value.textContent).toBe("too dark (2)");
        expect(value.dataset.codeTone).toBe("warn");
        expect(mustQuery(value, ".code-number").textContent).toBe("(2)");
    });

    it("shows an unknown toned code as its number alone, with no tone", () => {
        const value = mustQuery(fieldCard(CAL_LIGHT_FIELD, 7), '[data-field-key="CalLight"]');
        expect(value.textContent).toBe("(7)");
        expect(value.dataset.codeTone).toBeUndefined();
    });

    it("titles an epoch value with its UTC instant and shows its age against the device clock", () => {
        const value = mustQuery(fieldCard(EPOCH_FIELD, DEVICE_NOW_S - 5, { display: { ...AVAILABLE, deviceNowS: DEVICE_NOW_S } }), '[data-field-key="TS"]');
        expect(value.textContent).toBe("5 s ago");
        expect(value.title).toBe(new Date((DEVICE_NOW_S - 5) * 1000).toISOString());
    });

    it("gives a special timestamp no instant, and a timestamp no date can hold no title", () => {
        const special = mustQuery(fieldCard(BACKUP_TS_FIELD, 0), '[data-field-key="SGP40_BackupTS"]');
        expect(special.textContent).toBe("No timestamp");
        expect(special.hasAttribute("title")).toBe(false);
        const huge = mustQuery(fieldCard(EPOCH_FIELD, 1e20), '[data-field-key="TS"]');
        expect(huge.hasAttribute("title")).toBe(false);
    });

    it("rounds a fractional value with no decimals hint to the definitions' default", () => {
        const display = { ...AVAILABLE, defaultDecimals: 2 };
        expect(mustQuery(fieldCard({ key: "Temp", label: "Temp", kind: "readonly" }, 23.456, { display }), '[data-field-key="Temp"]').textContent).toBe("23.46");
        expect(mustQuery(fieldCard({ key: "CO2", label: "CO2", kind: "readonly" }, 612, { display }), '[data-field-key="CO2"]').textContent).toBe("612");
    });
});

describe("a group whose source is unavailable", () => {
    /** @type {FieldGroup} */
    const GROUP = {
        key: "SCD30",
        label: "SCD30",
        submit: true,
        fields: [
            { key: "MeasInterval", label: "Measurement Interval", unit: "s", kind: "number", min: 2, max: 1800 },
            { key: "Name", label: "Name", kind: "string", maxLength: 8 },
            { key: "SelfCal", label: "Self-Cal", kind: "toggle" },
            { key: "Mode", label: "Mode", kind: "enum", options: [{ value: 1, label: "One" }] },
        ],
    };

    /**
     * The controller's rule for a group read from one source object: unavailable when it is the marker.
     * @param {unknown} source
     * @returns {CardDisplay}
     */
    function displayFor(source) {
        return { deviceNowS: null, isUnavailable: () => isUnavailable(source) };
    }

    it("says unavailable in every number/string caption and placeholder, keeping the toggle and select", () => {
        const source = { error: "unavailable" };
        const card = mount(buildFieldGroupCard(GROUP, source, 0, displayFor(source)));
        for (const key of ["MeasInterval", "Name"]) {
            expect(mustQuery(card, `[data-current-value-for="${key}"]`).textContent).toBe("Current value: unavailable");
            expect(/** @type {HTMLInputElement} */ (mustQuery(card, `[data-field-key="${key}"]`)).placeholder).toBe("unavailable");
        }
        expect(mustQuery(card, '[data-field-key="SelfCal"]').tagName).toBe("BUTTON");
        expect(mustQuery(card, '[data-field-key="Mode"]').tagName).toBe("SELECT");
    });

    it("says unavailable on a read-only value", () => {
        const value = mustQuery(fieldCard({ key: "CO2", label: "CO2", kind: "readonly" }, 612, { display: { deviceNowS: null, isUnavailable: () => true } }), '[data-field-key="CO2"]');
        expect(value.textContent).toBe("unavailable");
    });

    it("turns an available card's captions to unavailable in place when its source becomes the marker, and back", () => {
        const values = { MeasInterval: 5, Name: "abc", SelfCal: true, Mode: 1 };
        const card = mount(buildFieldGroupCard(GROUP, values, 0, displayFor(values)));
        const caption = mustQuery(card, '[data-current-value-for="MeasInterval"]');
        const marker = { error: "unavailable" };
        updateFieldGroupValues(card, GROUP, marker, displayFor(marker));
        expect(mustQuery(card, '[data-current-value-for="MeasInterval"]')).toBe(caption);
        expect(caption.textContent).toBe("Current value: unavailable");
        updateFieldGroupValues(card, GROUP, values, displayFor(values));
        expect(caption.textContent).toBe("Current value: 5");
        expect(/** @type {HTMLInputElement} */ (mustQuery(card, '[data-field-key="Name"]')).placeholder).toBe("abc");
    });

    it("reads a source carrying the marker beside field values as available", () => {
        const source = { error: "unavailable", MeasInterval: 5 };
        const card = mount(buildFieldGroupCard(GROUP, source, 0, displayFor(source)));
        expect(mustQuery(card, '[data-current-value-for="MeasInterval"]').textContent).toBe("Current value: 5");
    });
});

describe("buildFieldGroupCard", () => {
    it("adds an inert Apply button/result paragraph for a submit group - clicking it does nothing on its own", () => {
        /** @type {FieldGroup} */
        const group = { key: "SCD30", label: "SCD30", submit: true, fields: [{ key: "MeasInterval", label: "Measurement Interval", kind: "number", min: 2, max: 1800 }] };
        const card = buildFieldGroupCard(group, { MeasInterval: 5 }, 0, AVAILABLE);
        expect(card.dataset.groupKey).toBe("SCD30");
        const button = mustQuery(card, ".apply-button");
        expect(() => button.click()).not.toThrow();
        expect(card.dataset.applyStatus).toBeUndefined(); // no networked behavior wired by the template itself
    });

    it("omits the Apply button entirely for a read-only group", () => {
        /** @type {FieldGroup} */
        const group = { key: "SCD30", label: "SCD30", fields: [{ key: "CO2", label: "CO2", kind: "readonly" }] };
        expect(buildFieldGroupCard(group, { CO2: 600 }, 0, AVAILABLE).querySelector(".apply-button")).toBeNull();
    });
});

describe("updateFieldGroupValues", () => {
    /** @type {FieldGroup} */
    const LIVE_GROUP = {
        key: "SCD30",
        label: "SCD30",
        fields: [{ key: "CO2", label: "CO2", kind: "readonly" }, EPOCH_FIELD, RESET_REASON_FIELD, CAL_LIGHT_FIELD],
    };

    it("rewrites a read-only value in the same node, keeping its element", () => {
        const card = mount(buildFieldGroupCard(LIVE_GROUP, { CO2: 600, TS: DEVICE_NOW_S - 10, ResetReason: 1, CalLight: 1 }, 0, { ...AVAILABLE, deviceNowS: DEVICE_NOW_S }));
        const co2 = mustQuery(card, '[data-field-key="CO2"]');
        const ts = mustQuery(card, '[data-field-key="TS"]');
        updateFieldGroupValues(card, LIVE_GROUP, { CO2: 612, TS: DEVICE_NOW_S - 200, ResetReason: 1, CalLight: 2 }, { ...AVAILABLE, deviceNowS: DEVICE_NOW_S });
        expect(mustQuery(card, '[data-field-key="CO2"]')).toBe(co2);
        expect(co2.textContent).toBe("612");
        expect(ts.textContent).toBe("3 min ago");
        expect(ts.title).toBe(new Date((DEVICE_NOW_S - 200) * 1000).toISOString());
        const calLight = mustQuery(card, '[data-field-key="CalLight"]');
        expect(calLight.textContent).toBe("too dark (2)");
        expect(calLight.dataset.codeTone).toBe("warn");
    });

    it("keeps an open code description open and current when the code changes", () => {
        const card = mount(buildFieldGroupCard(LIVE_GROUP, { ResetReason: 1 }, 0, AVAILABLE));
        const button = mustQuery(card, "button.code-value");
        button.click();
        updateFieldGroupValues(card, LIVE_GROUP, { ResetReason: 3 }, AVAILABLE);
        expect(mustQuery(card, "button.code-value")).toBe(button);
        expect(button.textContent).toBe("3");
        expect(button.getAttribute("aria-expanded")).toBe("true");
        expect(mustQuery(card, ".code-description").textContent).toBe("3: reboot command");
    });

    it("leaves a toggle and a select the user set alone", () => {
        /** @type {FieldGroup} */
        const group = { key: "g", label: "G", submit: true, fields: [{ key: "SelfCal", label: "Self-Cal", kind: "toggle" }, { key: "Mode", label: "Mode", kind: "enum", options: [{ value: 1, label: "One" }, { value: 2, label: "Two" }] }] };
        const card = mount(buildFieldGroupCard(group, { SelfCal: false, Mode: 1 }, 0, AVAILABLE));
        mustQuery(card, '[data-field-key="SelfCal"]').click();
        const select = /** @type {HTMLSelectElement} */ (mustQuery(card, '[data-field-key="Mode"]'));
        select.value = "2";
        updateFieldGroupValues(card, group, { SelfCal: false, Mode: 1 }, AVAILABLE);
        expect(mustQuery(card, '[data-field-key="SelfCal"]').dataset.value).toBe("true");
        expect(select.value).toBe("2");
    });
});

describe("resetControl", () => {
    /** @type {FieldGroup} */
    const GROUP = {
        key: "g",
        label: "G",
        submit: true,
        fields: [
            { key: "MeasInterval", label: "Measurement Interval", kind: "number", min: 2, max: 1800 },
            { key: "LightCmdLED", label: "LED Flash", kind: "composite", subFields: [{ key: "R", label: "Red", kind: "number" }, { key: "G", label: "Green", kind: "number" }] },
            { key: "SystemCmd", label: "Command", kind: "enum", dispatch: true, options: [{ value: "reboot", label: "Reboot" }] },
            { key: "Mode", label: "Mode", kind: "enum", options: [{ value: 1, label: "One" }, { value: 2, label: "Two" }] },
            { key: "ResetErrors", label: "Confirm Reset", kind: "toggle", dispatch: true },
            { key: "ContMeas", label: "Continuous Measurement", kind: "toggle", alwaysExecuted: true },
        ],
    };

    /**
     * @param {HTMLElement} card
     * @param {string} key
     * @returns {[HTMLElement, FieldDef]}
     */
    function wrapperAndField(card, key) {
        const field = GROUP.fields.find((candidate) => candidate.key === key);
        if (field === undefined) {
            throw new Error(`no field ${key}`);
        }
        return [mustQuery(card, `[data-field-wrapper-key="${key}"]`), field];
    }

    it("clears a typed input and every composite sub-input", () => {
        const card = mount(buildFieldGroupCard(GROUP, {}, 0, AVAILABLE));
        const input = /** @type {HTMLInputElement} */ (mustQuery(card, '[data-field-key="MeasInterval"]'));
        input.value = "30";
        resetControl(...wrapperAndField(card, "MeasInterval"), undefined);
        expect(input.value).toBe("");
        const subInputs = /** @type {HTMLInputElement[]} */ ([...card.querySelectorAll("[data-sub-field-key]")]);
        for (const sub of subInputs) {
            sub.value = "9";
        }
        resetControl(...wrapperAndField(card, "LightCmdLED"), undefined);
        expect(subInputs.map((sub) => sub.value)).toEqual(["", ""]);
    });

    it("returns a command dropdown to its placeholder, and selects a reported option", () => {
        const card = mount(buildFieldGroupCard(GROUP, { Mode: 1 }, 0, AVAILABLE));
        const command = /** @type {HTMLSelectElement} */ (mustQuery(card, '[data-field-key="SystemCmd"]'));
        command.value = "reboot";
        resetControl(...wrapperAndField(card, "SystemCmd"), undefined);
        expect(command.value).toBe("");
        const mode = /** @type {HTMLSelectElement} */ (mustQuery(card, '[data-field-key="Mode"]'));
        resetControl(...wrapperAndField(card, "Mode"), 2);
        expect(mode.value).toBe("2");
    });

    it("gives a select with no matching option its placeholder", () => {
        const card = mount(buildFieldGroupCard(GROUP, { Mode: 1 }, 0, AVAILABLE));
        const mode = /** @type {HTMLSelectElement} */ (mustQuery(card, '[data-field-key="Mode"]'));
        resetControl(...wrapperAndField(card, "Mode"), 7);
        expect(mode.value).toBe("");
        expect(mode.selectedOptions[0]?.textContent).toBe("Select…");
    });

    it("sets a toggle with its label and aria-pressed, and an always-executed toggle back to unset", () => {
        const card = mount(buildFieldGroupCard(GROUP, {}, 0, AVAILABLE));
        const reset = mustQuery(card, '[data-field-key="ResetErrors"]');
        reset.click();
        resetControl(...wrapperAndField(card, "ResetErrors"), false);
        expect([reset.dataset.value, reset.getAttribute("aria-pressed"), reset.textContent]).toEqual(["false", "false", "Off"]);
        const contMeas = mustQuery(card, '[data-field-key="ContMeas"]');
        contMeas.click();
        resetControl(...wrapperAndField(card, "ContMeas"), undefined);
        expect([contMeas.dataset.value, contMeas.getAttribute("aria-pressed"), contMeas.textContent]).toEqual(["unset", "mixed", "—"]);
    });
});

describe("buildErrcountGroup", () => {
    /** @type {ErrcountGroup} */
    const THREE_MODULE_GROUP = {
        key: "errcount",
        label: "Errors",
        kind: "errcount",
        modules: [
            { key: "SCD30", label: "SCD30" },
            { key: "SGP40", label: "SGP40" },
            { key: "BMP3XX", label: "BMP388" },
        ],
        codes: { E: { 2: "the sensor did not answer", 4: "a read failed" }, W: { 5: "a reading was out of range" } },
    };
    /** @type {Record<string, ErrcountEntry>} */
    const THREE_MODULE_ERRCOUNT = {
        SCD30: { counter: 0, history: [{ num: 0, type: "N" }] },
        SGP40: { counter: 3, history: [{ num: 0, type: "N" }, { num: 5, type: "W" }] },
        BMP3XX: { counter: 12, history: [{ num: 0, type: "N" }, { num: 2, type: "E" }, { num: 4, type: "E" }] },
    };

    /**
     * @param {HTMLElement} card
     * @param {"flagged" | "all"} action
     */
    function clickAction(card, action) {
        mustQuery(card, `[data-errcount-action="${action}"]`).click();
    }

    /**
     * @param {HTMLElement} card
     * @param {number} index
     * @returns {HTMLElement}
     */
    function rowAt(card, index) {
        return /** @type {HTMLElement} */ (card.querySelectorAll(".errcount-row-wrapper").item(index));
    }

    /**
     * @param {HTMLElement} card
     * @returns {string[]}
     */
    function visibleModules(card) {
        return [...card.querySelectorAll(".errcount-row-wrapper")].filter((el) => !el.classList.contains("hidden")).map((el) => mustQuery(el, ".errcount-row-name").textContent ?? "");
    }

    it("wraps the rollup and module list in a card with the group's heading, like every other field group", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        expect(wrapper.classList.contains("card")).toBe(true);
        expect(mustQuery(wrapper, "h3").textContent).toBe("Errors");
    });

    it("tags the card with data-group-key itself, like buildFieldGroupCard() (SPECIFICATION.md Part H.3: js/templates.js owns the hook)", () => {
        expect(buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT).dataset.groupKey).toBe("errcount");
    });

    it("starts fully collapsed to just the rollup - no module rows visible", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        const list = mustQuery(wrapper, ".errcount-module-list");
        expect(list.classList.contains("hidden")).toBe(true);
        expect(list.dataset.filter).toBe("collapsed");
        // Rows exist in the DOM (built once, filtered by toggling .hidden - see the "Show
        // flagged"/"Show all" tests below) but every one starts hidden until a filter is chosen.
        const wrappers = wrapper.querySelectorAll(".errcount-row-wrapper");
        expect(wrappers).toHaveLength(3);
        expect([...wrappers].every((el) => el.classList.contains("hidden"))).toBe(true);
    });

    it("rolls up how many modules have errors vs. warnings, by each module's worst history entry", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        expect(mustQuery(wrapper, '[data-rollup="errors"]').textContent).toBe("1 module with errors");
        expect(mustQuery(wrapper, '[data-rollup="warnings"]').textContent).toBe("1 module with warnings");
        expect(mustQuery(wrapper, '[data-rollup="nodata"]').classList.contains("hidden")).toBe(true);
    });

    it("colours a counted module with only warnings in its history as a warning, on the row's one severity", () => {
        const wrapper = mount(buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT));
        clickAction(wrapper, "all");
        const sgp40 = rowAt(wrapper, 1);
        expect(sgp40.dataset.worst).toBe("W");
        expect(mustQuery(sgp40, ".errcount-row").hasAttribute("data-has-errors")).toBe(false);
        expect(mustQuery(sgp40, ".errcount-row-count").textContent).toBe("3");
    });

    it('"Show flagged" reveals only modules whose worst entry is an error or warning', () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        clickAction(wrapper, "flagged");
        const list = mustQuery(wrapper, ".errcount-module-list");
        expect(list.classList.contains("hidden")).toBe(false);
        expect(list.dataset.filter).toBe("flagged");
        expect(visibleModules(wrapper)).toEqual(["SGP40", "BMP388"]);
    });

    it('"Show all" reveals every module regardless of worst status', () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        clickAction(wrapper, "all");
        expect(mustQuery(wrapper, ".errcount-module-list").dataset.filter).toBe("all");
        expect(visibleModules(wrapper)).toHaveLength(3);
    });

    it("shows a module's own counter and its full history immediately once revealed - no separate expand click", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        clickAction(wrapper, "flagged");
        const rowWrapper = mustQuery(wrapper, '.errcount-row-wrapper[data-worst="E"]');
        expect(mustQuery(rowWrapper, ".errcount-row-count").textContent).toBe("12");
        const list = mustQuery(rowWrapper, ".history-list");
        expect(list.classList.contains("hidden")).toBe(false);
        expect(list.querySelectorAll(".history-entry")).toHaveLength(3);
    });

    it("renders an absent module as no data, never a zero", () => {
        /** @type {ErrcountGroup} */
        const group = { key: "errcount", label: "Errors", kind: "errcount", modules: [{ key: "SGP40", label: "SGP40" }] };
        const wrapper = buildErrcountGroup(group, {});
        clickAction(wrapper, "all");
        const rowWrapper = mustQuery(wrapper, ".errcount-row-wrapper");
        expect(mustQuery(rowWrapper, ".errcount-row-count").textContent).toBe("no data");
        expect(rowWrapper.dataset.worst).toBe("none");
        expect(rowWrapper.querySelector(".history-entry, .history-empty")).toBeNull();
    });

    it("renders every row as no data, counted in the rollup, when the body carried no errcount", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, null);
        const counts = [...wrapper.querySelectorAll(".errcount-row-count")].map((el) => el.textContent);
        expect(counts).toEqual(["no data", "no data", "no data"]);
        const nodata = mustQuery(wrapper, '[data-rollup="nodata"]');
        expect(nodata.classList.contains("hidden")).toBe(false);
        expect(nodata.textContent).toBe("3 modules without data");
        expect(mustQuery(wrapper, '[data-rollup="errors"]').textContent).toBe("0 modules with errors");
    });

    it("renders an unavailable module as unavailable, revealed by Show flagged", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, { ...THREE_MODULE_ERRCOUNT, SCD30: { error: "unavailable" } });
        const scd30 = /** @type {HTMLElement} */ (wrapper.querySelector(".errcount-row-wrapper"));
        expect(mustQuery(scd30, ".errcount-row-count").textContent).toBe("unavailable");
        expect(scd30.dataset.worst).toBe("none");
        expect(mustQuery(wrapper, '[data-rollup="nodata"]').textContent).toBe("1 module without data");
        clickAction(wrapper, "flagged");
        expect(visibleModules(wrapper)).toEqual(["SCD30", "SGP40", "BMP388"]);
    });

    it("reads a counter at the firmware's cap as saturated, and one below it as exact", () => {
        /** @type {ErrcountGroup} */
        const group = { key: "errcount", label: "Errors", kind: "errcount", modules: [{ key: "SCD30", label: "SCD30" }, { key: "SGP40", label: "SGP40" }] };
        const wrapper = buildErrcountGroup(group, { SCD30: { counter: ERR_COUNT_CAP, history: [] }, SGP40: { counter: ERR_COUNT_CAP - 1, history: [] } });
        const counts = [...wrapper.querySelectorAll(".errcount-row-count")].map((el) => el.textContent);
        expect(counts).toEqual([`${ERR_COUNT_CAP}+`, String(ERR_COUNT_CAP - 1)]);
    });

    it("shows a placeholder message for a module with no history", () => {
        /** @type {ErrcountGroup} */
        const group = { key: "errcount", label: "Errors", kind: "errcount", modules: [{ key: "SGP40", label: "SGP40" }] };
        const wrapper = buildErrcountGroup(group, { SGP40: { counter: 0 } });
        clickAction(wrapper, "all");
        expect(mustQuery(wrapper, ".history-empty").textContent).toBe("No history recorded.");
    });

    it("renders each entry's raw errno, colored by type via data-err-type only - never the type itself as text", () => {
        // Real backend shape (src/asy_print_log.py's get_log()): no per-entry timestamp exists, and
        // "type" is never meant to be shown as text - only to color "num" (owner,
        // 2026-08-21, `9fd2a28`). html/style.css's .history-entry[data-err-type] rules pick the color.
        /** @type {ErrcountGroup} */
        const group = { key: "errcount", label: "Errors", kind: "errcount", modules: [{ key: "BMP3XX", label: "BMP388" }] };
        const errcount = {
            BMP3XX: {
                counter: 3,
                history: [
                    { num: 0, type: /** @type {const} */ ("N") },
                    { num: 3, type: /** @type {const} */ ("W") },
                    { num: 2, type: /** @type {const} */ ("E") },
                ],
            },
        };
        const wrapper = buildErrcountGroup(group, errcount);
        clickAction(wrapper, "flagged");
        const entries = wrapper.querySelectorAll(".history-entry");
        expect(entries).toHaveLength(3);
        expect(/** @type {HTMLElement} */ (entries[0]).dataset.errType).toBe("N");
        expect(mustQuery(/** @type {HTMLElement} */ (entries[0]), ".history-entry-num").textContent).toBe("0");
        expect(/** @type {HTMLElement} */ (entries[1]).dataset.errType).toBe("W");
        expect(mustQuery(/** @type {HTMLElement} */ (entries[1]), ".history-entry-num").textContent).toBe("3");
        expect(/** @type {HTMLElement} */ (entries[2]).dataset.errType).toBe("E");
        expect(mustQuery(/** @type {HTMLElement} */ (entries[2]), ".history-entry-num").textContent).toBe("2");
        // No individual history entry ever renders "N"/"E"/"W"/"error"/"warning" as visible text
        // (the rollup line above them is allowed to say "errors"/"warnings" - only per-entry text is constrained).
        const list = mustQuery(wrapper, ".history-list");
        expect(list.textContent).not.toMatch(/error|warning|\bN\b|\bE\b|\bW\b/i);
    });

    it("makes an error or warning number a button, leaving a no-error entry a plain span", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        const sgp40 = rowAt(wrapper, 1);
        const nums = [...sgp40.querySelectorAll(".history-entry-num")];
        expect(nums.map((el) => el.tagName)).toEqual(["SPAN", "BUTTON"]);
        expect(nums[1]?.getAttribute("type")).toBe("button");
        expect(nums[1]?.getAttribute("aria-expanded")).toBe("false");
    });

    it("shows a history code's catalog text below the row's history on click, hides it on a second click, and moves it on another pill", () => {
        const wrapper = mount(buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT));
        clickAction(wrapper, "all");
        const bmp = mustQuery(wrapper, '.errcount-row-wrapper[data-worst="E"]');
        const [first, second] = /** @type {HTMLButtonElement[]} */ ([...bmp.querySelectorAll("button.history-entry-num")]);
        if (first === undefined || second === undefined) {
            throw new Error("Expected two code buttons");
        }
        first.click();
        const description = mustQuery(bmp, ".code-description");
        expect(description.previousElementSibling).toBe(mustQuery(bmp, ".history-list"));
        expect(description.textContent).toBe("2: the sensor did not answer");
        expect(first.getAttribute("aria-expanded")).toBe("true");

        second.click();
        expect(bmp.querySelectorAll(".code-description")).toHaveLength(1);
        expect(mustQuery(bmp, ".code-description").textContent).toBe("4: a read failed");
        expect([first.getAttribute("aria-expanded"), second.getAttribute("aria-expanded")]).toEqual(["false", "true"]);

        second.click();
        expect(bmp.querySelector(".code-description")).toBeNull();
        expect(second.getAttribute("aria-expanded")).toBe("false");
    });

    it("opens a history code's description from the keyboard", async () => {
        const wrapper = mount(buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT));
        clickAction(wrapper, "all");
        const sgp40 = rowAt(wrapper, 1);
        mustQuery(sgp40, "button.history-entry-num").focus();
        await userEvent.keyboard("{Enter}");
        expect(mustQuery(sgp40, ".code-description").textContent).toBe("5: a reading was out of range");
    });

    it("says a history code with no catalog entry has no description", () => {
        const wrapper = mount(buildErrcountGroup(THREE_MODULE_GROUP, { SCD30: { counter: 1, history: [{ num: 77, type: "E" }] } }));
        clickAction(wrapper, "all");
        mustQuery(wrapper, "button.history-entry-num").click();
        expect(mustQuery(wrapper, ".code-description").textContent).toBe("No description for code 77");
    });
});

describe("updateErrcountGroup", () => {
    /** @type {ErrcountGroup} */
    const GROUP = {
        key: "errcount",
        label: "Errors",
        kind: "errcount",
        modules: [
            { key: "SCD30", label: "SCD30" },
            { key: "SGP40", label: "SGP40" },
        ],
        codes: { E: { 2: "the sensor did not answer" }, W: {} },
    };
    /** @type {Record<string, ErrcountEntry>} */
    const HEALTHY = { SCD30: { counter: 0, history: [{ num: 0, type: "N" }] }, SGP40: { counter: 0, history: [{ num: 0, type: "N" }] } };
    /** @type {Record<string, ErrcountEntry>} */
    const FAILING = { SCD30: { counter: 4, history: [{ num: 0, type: "N" }, { num: 2, type: "E" }] }, SGP40: { counter: 0, history: [{ num: 0, type: "N" }] } };

    it("keeps the filter buttons, and the focus on them, while it updates the counts", () => {
        const card = mount(buildErrcountGroup(GROUP, HEALTHY));
        const showAll = mustQuery(card, '[data-errcount-action="all"]');
        showAll.focus();
        updateErrcountGroup(card, GROUP, FAILING);
        expect(mustQuery(card, '[data-errcount-action="all"]')).toBe(showAll);
        expect(document.activeElement).toBe(showAll);
        expect(mustQuery(card, '[data-rollup="errors"]').textContent).toBe("1 module with errors");
        const scd30 = /** @type {HTMLElement} */ (card.querySelector(".errcount-row-wrapper"));
        expect(scd30.dataset.worst).toBe("E");
        expect(mustQuery(scd30, ".errcount-row-count").textContent).toBe("4");
    });

    it("re-applies the chosen filter, so a module that turns flagged shows at once", () => {
        const card = mount(buildErrcountGroup(GROUP, HEALTHY));
        mustQuery(card, '[data-errcount-action="flagged"]').click();
        expect([...card.querySelectorAll(".errcount-row-wrapper.hidden")]).toHaveLength(2);
        updateErrcountGroup(card, GROUP, FAILING);
        const scd30 = /** @type {HTMLElement} */ (card.querySelector(".errcount-row-wrapper"));
        expect(scd30.classList.contains("hidden")).toBe(false);
        expect(mustQuery(card, ".errcount-module-list").classList.contains("hidden")).toBe(false);
    });

    it("keeps a row's history nodes and open description while the history is unchanged, and rebuilds and closes them when it changes", () => {
        const card = mount(buildErrcountGroup(GROUP, FAILING));
        const pill = mustQuery(card, "button.history-entry-num");
        pill.click();
        updateErrcountGroup(card, GROUP, { ...FAILING, SCD30: { counter: 5, history: [{ num: 0, type: "N" }, { num: 2, type: "E" }] } });
        expect(mustQuery(card, "button.history-entry-num")).toBe(pill);
        expect(mustQuery(card, ".code-description").textContent).toBe("2: the sensor did not answer");

        updateErrcountGroup(card, GROUP, { ...FAILING, SCD30: { counter: 6, history: [{ num: 2, type: "E" }, { num: 2, type: "E" }] } });
        expect(card.querySelector(".code-description")).toBeNull();
        expect(card.querySelectorAll("button.history-entry-num")).toHaveLength(2);
        expect(card.contains(pill)).toBe(false);
    });

    it("drops the saturation mark when a capped counter falls after a reset", () => {
        const card = mount(buildErrcountGroup(GROUP, { ...HEALTHY, SCD30: { counter: ERR_COUNT_CAP, history: [] } }));
        const count = mustQuery(card, ".errcount-row-count");
        expect(count.textContent).toBe(`${ERR_COUNT_CAP}+`);
        updateErrcountGroup(card, GROUP, { ...HEALTHY, SCD30: { counter: 2, history: [] } });
        expect(count.textContent).toBe("2");
    });

    it("turns every row to no data when a later body carries no errcount, and back", () => {
        const card = mount(buildErrcountGroup(GROUP, FAILING));
        updateErrcountGroup(card, GROUP, null);
        expect([...card.querySelectorAll(".errcount-row-count")].map((el) => el.textContent)).toEqual(["no data", "no data"]);
        expect(mustQuery(card, '[data-rollup="nodata"]').textContent).toBe("2 modules without data");
        updateErrcountGroup(card, GROUP, FAILING);
        expect(mustQuery(card, '[data-rollup="nodata"]').classList.contains("hidden")).toBe(true);
        expect(mustQuery(card, ".errcount-row-count").textContent).toBe("4");
    });
});

describe("buildSectionShell", () => {
    it("builds the heading/description and returns an empty grid plus a hidden error banner, clearing prior content", () => {
        const mainEl = mount(document.createElement("main"));
        mainEl.innerHTML = "<p>stale content from a previous section</p>";

        /** @type {import("../js/definitions.js").Section} */
        const section = {
            key: "measurements",
            label: "Measurements",
            description: "Live readings.",
            rest: { get: "/measurements" },
            pollGroup: "live",
            groups: [],
        };
        const { grid, errorBanner } = buildSectionShell(section, mainEl);

        expect(mustQuery(mainEl, ".section-heading").textContent).toBe("Measurements");
        expect(mustQuery(mainEl, ".section-description").textContent).toBe("Live readings.");
        expect(grid.className).toBe("group-grid");
        expect(grid.children).toHaveLength(0);
        expect(mainEl.textContent).not.toContain("stale content");
        expect(errorBanner.className).toBe("error-banner");
        expect(errorBanner.dataset.shown).toBe("false");
        expect(errorBanner.getAttribute("role")).toBe("alert");
    });
});

describe("buildNavDrawer", () => {
    it("builds one inert data-section-key link per section plus a device-name heading", () => {
        const drawerEl = mount(document.createElement("nav"));
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defs = {
            schemaVersion: "1.0.0",
            device: { id: "fixture-device", displayName: "Fixture Device" },
            landingSection: "measurements",
            defaultPollIntervalMs: 3000,
            sections: [
                { key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: "live", groups: [] },
                { key: "sensors", label: "Sensors", rest: { get: "/sensors" }, pollGroup: "settings", groups: [] },
            ],
        };

        buildNavDrawer(defs, drawerEl);

        expect(mustQuery(drawerEl, ".nav-drawer-heading").textContent).toBe("Fixture Device");
        const links = /** @type {NodeListOf<HTMLElement>} */ (drawerEl.querySelectorAll("[data-section-key]"));
        expect(links).toHaveLength(2);
        const [firstLink] = links;
        if (firstLink === undefined) {
            throw new Error("Expected a [data-section-key] link");
        }
        expect(firstLink.dataset.sectionKey).toBe("measurements");
        // No listener attached yet - clicking must not throw and must have no observable effect.
        expect(() => firstLink.click()).not.toThrow();
    });
});

describe("XSS safety (standing guideline: textContent only, never innerHTML)", () => {
    const HOSTILE = '<img src=x onerror="window.__xssFired = true">';

    /** @param {HTMLElement} container */
    function expectLiteral(container) {
        expect(container.querySelector("img")).toBeNull();
        expect(/** @type {any} */ (window).__xssFired).toBeUndefined();
        expect(container.textContent).toContain(HOSTILE);
    }

    it("renders a hostile field label/value as literal text, never as parsed markup", () => {
        expectLiteral(fieldCard({ key: "CO2", label: HOSTILE, kind: "readonly" }, HOSTILE));
    });

    it("renders a hostile field-group label as literal text", () => {
        const card = mount(buildFieldGroupCard({ key: "SCD30", label: HOSTILE, fields: [] }, {}, 0, AVAILABLE));
        expect(card.querySelector("img")).toBeNull();
        expect(/** @type {any} */ (window).__xssFired).toBeUndefined();
        expect(mustQuery(card, "h3").textContent).toBe(HOSTILE);
    });

    it("renders a hostile errcount module label as literal text", () => {
        /** @type {ErrcountGroup} */
        const group = { key: "errcount", label: "Errors", kind: "errcount", modules: [{ key: "SCD30", label: HOSTILE }] };
        expectLiteral(mount(buildErrcountGroup(group, { SCD30: { counter: 0 } })));
    });

    it("renders a hostile code description as literal text, on a value and on a history entry", () => {
        const el = fieldCard({ key: "ResetReason", label: "Reset", kind: "readonly", codes: { 1: HOSTILE } }, 1);
        mustQuery(el, "button.code-value").click();
        expectLiteral(el);
        /** @type {ErrcountGroup} */
        const group = { key: "errcount", label: "Errors", kind: "errcount", modules: [{ key: "SCD30", label: "SCD30" }], codes: { E: { 1: HOSTILE }, W: {} } };
        const card = mount(buildErrcountGroup(group, { SCD30: { counter: 1, history: [{ num: 1, type: "E" }] } }));
        mustQuery(card, "button.history-entry-num").click();
        expectLiteral(card);
    });

    it("renders a hostile device/section name in the nav drawer as literal text", () => {
        const container = mount(document.createElement("nav"));
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defs = {
            schemaVersion: "1.0.0",
            device: { id: "fixture-device", displayName: HOSTILE },
            landingSection: "measurements",
            defaultPollIntervalMs: 3000,
            sections: [{ key: "measurements", label: HOSTILE, rest: { get: "/measurements" }, pollGroup: "live", groups: [] }],
        };

        buildNavDrawer(defs, container);

        expectLiteral(container);
    });
});
