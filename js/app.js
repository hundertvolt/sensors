/**
 * Prototype entry point (WEBSITE_PLAN.md §10 session 2). Reads `?device=` to pick which
 * definitions.json + mock fixture to load - a **prototype-only** convenience: real firmware
 * bakes exactly one device's definitions.json into the frozen build and never branches on a
 * query param (SPECIFICATION.md Part A.9), it just always fetches the one file it was shipped
 * with. This switch exists purely so both devices can be clicked through from one static
 * checkout without two separate local copies.
 */

import { loadDefinitions } from "./definitions.js";
import { installMockFetch } from "./mock-server.js";
import { initNav } from "./nav.js";
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

    const mockDataResponse = await fetch(`../mockdata/${device}.json`);
    const mockData = await mockDataResponse.json();
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
            return;
        }
        stopCurrentSection();
        setCurrentNav(sectionKey);
        stopCurrentSection = renderSection(defs, section, mainEl);
    }

    selectSection(defs.landingSection);
}
