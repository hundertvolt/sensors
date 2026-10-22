/**
 * Prototype entry point: picks a device from the build's definitions manifest (`?device=` overrides it), installs the
 * mock backend and starts the shared shell. Never staged (SPECIFICATION.md Part H.2).
 */

import { loadDefinitions } from "./definitions.js";
import { composeMockData, installMockFetch } from "./mock-server.js";
import { pollManager } from "./poll-manager.js";
import { showBanner } from "./render.js";
import { buildDateOf, historyOf, startShell, visibilityOf } from "./shell.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */

const DEFINITIONS_DIR = "../build/generated_src/definitions";

/**
 * The manifest's sorted device ids, or an error when it is no non-empty string array.
 * @returns {Promise<string[]>}
 */
async function fetchDeviceList() {
    const manifest = /** @type {{devices?: unknown} | null} */ (await requestJson(`${DEFINITIONS_DIR}/index.json`));
    const devices = manifest?.devices;
    if (!Array.isArray(devices) || devices.length === 0 || !devices.every((id) => typeof id === "string")) {
        throw new Error("index.json does not list any device");
    }
    return /** @type {string[]} */ (devices);
}

/**
 * One JSON file through the request queue, throwing for a non-ok status.
 * @param {string} path
 * @returns {Promise<unknown>}
 */
async function requestJson(path) {
    const response = await pollManager.request(path);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    return response.body;
}

/**
 * @param {{
 *   appShellEl: HTMLElement, mainEl: HTMLElement, drawerEl: HTMLElement,
 *   hamburgerEl: HTMLElement, backdropEl: HTMLElement, errorBannerEl: HTMLElement,
 *   deviceNameEl: HTMLElement,
 * }} elements
 * @returns {Promise<() => void>} stop: ends the shell and uninstalls the mock backend.
 */
export async function startApp(elements) {
    const { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl, errorBannerEl, deviceNameEl } = elements;
    const nothingStarted = () => { /* nothing was started */ };
    /** @type {string[]} */
    let devices;
    try {
        devices = await fetchDeviceList();
    } catch (error) {
        showBanner(errorBannerEl, `Could not load the device list: ${String(error)}`);
        return nothingStarted;
    }
    // The manifest is sorted, so its first device is the default; an unknown ?device= falls back to it.
    const requestedDevice = new URLSearchParams(window.location.search).get("device");
    const device = requestedDevice !== null && devices.includes(requestedDevice) ? requestedDevice : /** @type {string} */ (devices[0]);

    /** @type {SiteDefinitions} */
    let defs;
    try {
        defs = await loadDefinitions(`${DEFINITIONS_DIR}/${device}.json`);
    } catch (error) {
        showBanner(errorBannerEl, `Could not load definitions for "${device}": ${String(error)}`);
        return nothingStarted;
    }

    deviceNameEl.textContent = defs.device.displayName;

    /** @type {import("./definitions.js").MockDeviceData} */
    let mockData;
    try {
        const samples = /** @type {import("./definitions.js").MockSamples} */ (await requestJson("../mockdata/samples.json"));
        mockData = composeMockData(defs, samples);
    } catch (error) {
        showBanner(errorBannerEl, `Could not load mock fixture data for "${device}": ${String(error)}`);
        return nothingStarted;
    }
    const uninstall = installMockFetch(defs, mockData);
    // The URL's hash carries the section; its ?device= query stays the device's.
    const stopShell = startShell({
        defs,
        elements: { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl },
        keyTarget: document,
        visibility: visibilityOf(document),
        history: historyOf(window),
        reload: () => window.location.reload(),
        pageBuildDate: buildDateOf(document),
    });
    return () => {
        stopShell();
        uninstall();
    };
}
