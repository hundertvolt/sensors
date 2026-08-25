/**
 * Prototype entry point. The `?device=` switch below is prototype-only (real firmware ships
 * exactly one device's definitions.json, never branches on a query param) - see
 * WEBSITE_PLAN.md §10 session 2 for why, and SPECIFICATION.md Part A.9 for the real build.
 */

import { loadDefinitions } from "./definitions.js";
import { installMockFetch } from "./mock-server.js";
import { initNav } from "./nav.js";
import { fetchWithTimeout } from "./poll-manager.js";
import { renderSection } from "./render.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */

const DEFAULT_DEVICE = "wozi";
const KNOWN_DEVICES = ["wozi", "dev"];

/**
 * @param {{
 *   appShellEl: HTMLElement, mainEl: HTMLElement, drawerEl: HTMLElement,
 *   hamburgerEl: HTMLElement, backdropEl: HTMLElement, errorBannerEl: HTMLElement,
 *   deviceNameEl: HTMLElement,
 * }} elements
 */
export async function startApp(elements) {
    const { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl, errorBannerEl, deviceNameEl } = elements;
    const params = new URLSearchParams(window.location.search);
    const requestedDevice = params.get("device") ?? DEFAULT_DEVICE;
    const device = KNOWN_DEVICES.includes(requestedDevice) ? requestedDevice : DEFAULT_DEVICE;

    /** @type {SiteDefinitions} */
    let defs;
    try {
        defs = await loadDefinitions(`definitions/${device}.json`);
    } catch (error) {
        errorBannerEl.textContent = `Could not load definitions for "${device}": ${String(error)}`;
        errorBannerEl.classList.remove("hidden");
        return;
    }

    deviceNameEl.textContent = defs.device.displayName;

    /** @type {import("./definitions.js").MockDeviceData} */
    let mockData;
    try {
        const mockDataResponse = await fetchWithTimeout(`../mockdata/${device}.json`);
        if (!mockDataResponse.ok) {
            throw new Error(`HTTP ${mockDataResponse.status}`);
        }
        try {
            mockData = await mockDataResponse.json();
        } catch (error) {
            throw new Error("response was not valid JSON (likely a corrupted or truncated transmission)", { cause: error });
        }
    } catch (error) {
        errorBannerEl.textContent = `Could not load mock fixture data for "${device}": ${String(error)}`;
        errorBannerEl.classList.remove("hidden");
        return;
    }
    installMockFetch(defs, mockData);

    let stopCurrentSection = () => {};
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
