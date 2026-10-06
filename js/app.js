/**
 * Prototype entry point: picks a device from the build's definitions manifest (`?device=` overrides
 * it) and installs the mock backend; real firmware ships one device's definitions.json and never
 * branches on a query param (SPECIFICATION.md Part H.2; the real build: Part A.9).
 */

import { loadDefinitions } from "./definitions.js";
import { composeMockData, installMockFetch } from "./mock-server.js";
import { initNav } from "./nav.js";
import { fetchWithTimeout } from "./poll-manager.js";
import { renderSection } from "./render.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */

const DEFINITIONS_DIR = "../build/generated_src/definitions";

/**
 * Fetches and parses one JSON file, throwing a worded error for a non-ok status or a torn body.
 * @param {string} path
 * @returns {Promise<unknown>}
 */
async function fetchJson(path) {
    const response = await fetchWithTimeout(path);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    try {
        return await response.json();
    } catch (error) {
        throw new Error("response was not valid JSON (likely a corrupted or truncated transmission)", { cause: error });
    }
}

/**
 * The manifest's sorted device ids, or an error when it is no non-empty string array.
 * @returns {Promise<string[]>}
 */
async function fetchDeviceList() {
    const manifest = /** @type {{devices?: unknown} | null} */ (await fetchJson(`${DEFINITIONS_DIR}/index.json`));
    const devices = manifest?.devices;
    if (!Array.isArray(devices) || devices.length === 0 || !devices.every((id) => typeof id === "string")) {
        throw new Error("index.json does not list any device");
    }
    return /** @type {string[]} */ (devices);
}

/**
 * @param {{
 *   appShellEl: HTMLElement, mainEl: HTMLElement, drawerEl: HTMLElement,
 *   hamburgerEl: HTMLElement, backdropEl: HTMLElement, errorBannerEl: HTMLElement,
 *   deviceNameEl: HTMLElement,
 * }} elements
 */
export async function startApp(elements) {
    const { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl, errorBannerEl, deviceNameEl } = elements;
    /** @type {string[]} */
    let devices;
    try {
        devices = await fetchDeviceList();
    } catch (error) {
        errorBannerEl.textContent = `Could not load the device list: ${String(error)}`;
        errorBannerEl.classList.remove("hidden");
        return;
    }
    // The manifest is sorted, so its first device is the default; an unknown ?device= falls back to it.
    const requestedDevice = new URLSearchParams(window.location.search).get("device");
    const device = requestedDevice !== null && devices.includes(requestedDevice) ? requestedDevice : /** @type {string} */ (devices[0]);

    /** @type {SiteDefinitions} */
    let defs;
    try {
        defs = await loadDefinitions(`${DEFINITIONS_DIR}/${device}.json`);
    } catch (error) {
        errorBannerEl.textContent = `Could not load definitions for "${device}": ${String(error)}`;
        errorBannerEl.classList.remove("hidden");
        return;
    }

    deviceNameEl.textContent = defs.device.displayName;

    /** @type {import("./definitions.js").MockDeviceData} */
    let mockData;
    try {
        const samples = /** @type {import("./definitions.js").MockSamples} */ (await fetchJson("../mockdata/samples.json"));
        mockData = composeMockData(defs, samples);
    } catch (error) {
        errorBannerEl.textContent = `Could not load mock fixture data for "${device}": ${String(error)}`;
        errorBannerEl.classList.remove("hidden");
        return;
    }
    installMockFetch(defs, mockData);

    let stopCurrentSection = () => { /* no section rendered yet - replaced on the first select */ };
    const setCurrentNav = initNav({
        defs,
        appShellEl,
        drawerEl,
        hamburgerEl,
        backdropEl,
        onSelect: (sectionKey) => selectSection(sectionKey),
    });

    /** @param {string} sectionKey */
    function selectSection(sectionKey) {
        const section = defs.sections.find((/** @type {SiteDefinitions["sections"][number]} */ entry) => entry.key === sectionKey);
        if (section === undefined) {
            // Defensive only: every real sectionKey traces back to defs.sections itself (a nav
            // click, or defs.landingSection, which validateDefinitions() already requires to
            // match a real section key), so this can't currently fire.
            return;
        }
        stopCurrentSection();
        setCurrentNav(sectionKey);
        stopCurrentSection = renderSection(defs, section, mainEl);
    }

    selectSection(defs.landingSection);
}
