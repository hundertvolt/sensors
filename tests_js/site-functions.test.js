// Every function the device's earlier pages offered keeps its counterpart on the generated site, per device: the
// readings and settings of each sensor the device's TOML declares, network and time, system settings and commands,
// the notification LED, and per-field result colours after an Apply against the mock.
import { afterEach, describe, expect, it, vi } from "vitest";
import samples from "../mockdata/samples.json";
import { composeMockData, installMockFetch } from "../js/mock-server.js";
import { renderSection } from "../js/render.js";
import { DEVICE_IDS, GENERATED_DEFINITIONS } from "./_generated_definitions.js";

/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("../js/definitions.js").Section} Section */
/** @typedef {import("../js/definitions.js").FieldGroup} FieldGroup */
/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */

const SAMPLES = /** @type {import("../js/definitions.js").MockSamples} */ (samples);
const TOML_FILES = /** @type {Record<string, string>} */ (import.meta.glob("../devices/*.toml", { query: "?raw", eager: true, import: "default" }));
// The commands the earlier pages' system page offered.
const LEGACY_COMMANDS = ["reboot", "bootloader", "mempause"];
// @tunable l0.section_render_wait_ms = 5000
const SECTION_RENDER_WAIT_MS = 5000;
// @tunable l0.render_wait_timeout_ms = 2000
const APPLY_WAIT_MS = 2000;
// @tunable l0.render_poll_ms = 10
const WAIT_POLL_MS = 10;

/**
 * @param {() => boolean} check
 * @param {number} timeoutMs
 */
async function waitFor(check, timeoutMs) {
    const start = Date.now();
    while (!check()) {
        if (Date.now() - start > timeoutMs) {
            throw new Error(`condition not met within ${timeoutMs}ms`);
        }
        // eslint-disable-next-line no-await-in-loop -- each poll waits for the previous one
        await new Promise((resolve) => {
            setTimeout(resolve, WAIT_POLL_MS);
        });
    }
}

/**
 * Every `[[instance]]` of a device TOML as its driver and name extension, read from the raw text.
 * @param {string} toml
 * @returns {{driver: string, nameExt: string}[]}
 */
function instancesOf(toml) {
    return toml.split(/^\[\[instance\]\]$/mu).slice(1).map((chunk) => {
        const table = chunk.split(/^\[/mu)[0] ?? "";
        return { driver: /^driver\s*=\s*"(?<value>[^"]+)"/mu.exec(table)?.groups?.value ?? "", nameExt: /^name_ext\s*=\s*"(?<value>[^"]*)"/mu.exec(table)?.groups?.value ?? "" };
    });
}

/**
 * @param {SiteDefinitions} defs
 * @param {string} key
 * @returns {Section}
 */
function sectionOf(defs, key) {
    const section = defs.sections.find((candidate) => candidate.key === key);
    if (section === undefined) {
        throw new Error(`no ${key} section`);
    }
    return section;
}

/**
 * @param {Section} section
 * @returns {FieldGroup[]}
 */
function fieldGroupsOf(section) {
    return /** @type {FieldGroup[]} */ (section.groups.filter((group) => "fields" in group));
}

/**
 * @param {Section} section
 * @param {string} fieldKey
 * @returns {FieldGroup | undefined} the writable group carrying the field
 */
function writableGroupWith(section, fieldKey) {
    return fieldGroupsOf(section).find((group) => group.submit === true && group.fields.some((field) => field.key === fieldKey));
}

/**
 * Changes one control of `field` the way a visitor would, so the card's next Apply sends it.
 * @param {HTMLElement} card
 * @param {FieldDef} field
 */
function changeControl(card, field) {
    const control = card.querySelector(`[data-field-key="${CSS.escape(field.key)}"]`);
    if (control instanceof HTMLSelectElement) {
        const other = [...control.options].find((option) => option.value !== "" && option.value !== control.value);
        control.value = other?.value ?? "";
    } else if (control instanceof HTMLInputElement) {
        control.value = field.kind === "number" ? "1" : "x1";
    } else if (control instanceof HTMLButtonElement) {
        control.click();
    } else if (control instanceof HTMLElement) {
        for (const input of control.querySelectorAll("input")) {
            input.value = "1";
        }
    }
}

describe.each(DEVICE_IDS)("%s's site", (device) => {
    const defs = /** @type {SiteDefinitions} */ (GENERATED_DEFINITIONS.get(device));
    const instances = instancesOf(TOML_FILES[`../devices/${device}.toml`] ?? "");
    // A sensor is an instance whose driver the mock samples carry readings for.
    const sensors = instances.filter((instance) => Object.hasOwn(SAMPLES.measurements, instance.driver.toUpperCase()));
    /** @type {(() => void) | undefined} */
    let stop;
    /** @type {(() => void) | undefined} */
    let uninstall;
    /** @type {HTMLElement | undefined} */
    let mainEl;

    afterEach(() => {
        stop?.();
        uninstall?.();
        mainEl?.remove();
    });

    it("shows one Measurements group and one writable Sensors group per sensor its TOML declares", () => {
        expect(sensors.length).toBeGreaterThan(0);
        for (const sectionKey of ["measurements", "sensors"]) {
            const groups = fieldGroupsOf(sectionOf(defs, sectionKey));
            expect(groups.map((group) => group.key.split("_")[0]).sort(), sectionKey).toEqual(sensors.map((sensor) => sensor.driver.toUpperCase()).sort());
            if (sectionKey === "sensors") {
                expect(groups.every((group) => group.submit === true)).toBe(true);
            }
        }
    });

    it("sets the Wi-Fi identity, the Wi-Fi LED and the NTP server", () => {
        const networking = sectionOf(defs, "networking");
        // Each field's submitted group and its own kind: a field a submitted group shows read-only is not settable.
        const placed = Object.fromEntries(["SSID", "PW", "LEDWifiOn", "NTPHost"].map((fieldKey) => {
            const group = writableGroupWith(networking, fieldKey);
            return [fieldKey, [group?.key, group?.fields.find((field) => field.key === fieldKey)?.kind]];
        }));
        expect(placed).toEqual({ SSID: ["identity", "string"], PW: ["identity", "string"], LEDWifiOn: ["wifiLed", "toggle"], NTPHost: ["ntp", "string"] });
    });

    it("sets the system settings and sends reboot, bootloader and backup-pause commands", () => {
        const system = sectionOf(defs, "system");
        expect(writableGroupWith(system, "DebugLevel")).toBeDefined();
        const command = writableGroupWith(system, "SystemCmd")?.fields.find((field) => field.key === "SystemCmd");
        expect(command?.options?.map((option) => option.value)).toEqual(expect.arrayContaining(LEGACY_COMMANDS));
    });

    it("flashes the LED, pauses and configures notifications where the device has them", () => {
        const notification = sectionOf(defs, "notification");
        const hasNotification = instances.some((instance) => instance.driver === "notification");
        for (const fieldKey of ["LightCmdLED", "PauseTime", "AutoOn"]) {
            expect(writableGroupWith(notification, fieldKey) !== undefined, fieldKey).toBe(hasNotification);
        }
    });

    it.each(defs.sections.filter((section) => fieldGroupsOf(section).some((group) => group.submit === true)).map((section) => /** @type {[string, Section]} */ ([section.key, section])))(
        "colours each field an Apply in the %s section sent with its own result",
        async (_key, section) => {
            vi.spyOn(window, "confirm").mockReturnValue(true);
            uninstall = installMockFetch(defs, composeMockData(defs, SAMPLES));
            const main = document.createElement("main");
            mainEl = main;
            document.body.appendChild(main);
            stop = renderSection(defs, section, main);
            await waitFor(() => main.querySelectorAll("[data-group-key]").length === section.groups.length, SECTION_RENDER_WAIT_MS);

            for (const group of fieldGroupsOf(section).filter((candidate) => candidate.submit === true)) {
                const field = group.fields.find((candidate) => candidate.kind !== "readonly");
                const card = main.querySelector(`[data-group-key="${CSS.escape(group.key)}"]`);
                if (field === undefined || !(card instanceof HTMLElement)) {
                    throw new Error(`${section.key}/${group.key}: no writable field or no card`);
                }
                changeControl(card, field);
                const button = /** @type {HTMLButtonElement} */ (card.querySelector(".apply-button"));
                button.click();
                // eslint-disable-next-line no-await-in-loop -- one Apply at a time, as a visitor clicks them
                await waitFor(() => !button.disabled, APPLY_WAIT_MS);
                const box = card.querySelector(`[data-field-wrapper-key="${CSS.escape(field.key)}"]`);
                expect(box instanceof HTMLElement ? box.dataset.applyStatus : undefined, `${section.key}/${group.key}/${field.key}`).toMatch(/^(?:valid|unchanged|invalid|failed)$/u);
                expect(card.dataset.applyStatus, `${section.key}/${group.key}`).toBeDefined();
            }
        },
    );
});
