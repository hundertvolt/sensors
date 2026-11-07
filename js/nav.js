/**
 * Nav controller: drawer open/close state and section-select dispatch. Builds no DOM itself -
 * see SPECIFICATION.md Part H.3 for the full mechanics/visual split this file follows.
 */

import { buildNavDrawer } from "./templates.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */

/**
 * @param {{
 *   defs: SiteDefinitions,
 *   appShellEl: HTMLElement,
 *   drawerEl: HTMLElement,
 *   hamburgerEl: HTMLElement,
 *   backdropEl: HTMLElement,
 *   keyTarget: EventTarget,
 *   onSelect: (sectionKey: string) => void,
 * }} options
 * @returns {{setCurrent: (sectionKey: string) => void, dispose: () => void}}
 */
export function initNav({ defs, appShellEl, drawerEl, hamburgerEl, backdropEl, keyTarget, onSelect }) {
    buildNavDrawer(defs, drawerEl);

    /** @type {(() => void)[]} */
    const removals = [];
    /**
     * @param {EventTarget} target
     * @param {string} type
     * @param {(event: Event) => void} listener
     */
    const listen = (target, type, listener) => {
        target.addEventListener(type, listener);
        removals.push(() => target.removeEventListener(type, listener));
    };

    const closeDrawer = () => {
        if (drawerEl.matches(":focus-within")) {
            hamburgerEl.focus(); // before inert, which would drop the focus
        }
        appShellEl.dataset.navOpen = "false";
        hamburgerEl.setAttribute("aria-expanded", "false");
        hamburgerEl.setAttribute("aria-label", "Open navigation");
        drawerEl.inert = true;
    };
    const openDrawer = () => {
        appShellEl.dataset.navOpen = "true";
        hamburgerEl.setAttribute("aria-expanded", "true");
        hamburgerEl.setAttribute("aria-label", "Close navigation");
        drawerEl.inert = false;
        /** @type {HTMLElement | null} */ (drawerEl.querySelector("[data-section-key]"))?.focus();
    };
    closeDrawer();

    for (const link of /** @type {NodeListOf<HTMLElement>} */ (drawerEl.querySelectorAll("[data-section-key]"))) {
        const { sectionKey } = link.dataset;
        if (sectionKey === undefined) {
            continue; // unreachable - narrows the type for tsc: buildNavDrawer() sets it on every link
        }
        listen(link, "click", () => {
            closeDrawer();
            onSelect(sectionKey);
        });
    }

    listen(hamburgerEl, "click", () => {
        if (appShellEl.dataset.navOpen === "true") {
            closeDrawer();
        } else {
            openDrawer();
        }
    });
    listen(backdropEl, "click", closeDrawer);
    listen(keyTarget, "keydown", (event) => {
        if (/** @type {KeyboardEvent} */ (event).key === "Escape") {
            closeDrawer();
        }
    });

    return {
        setCurrent: (sectionKey) => {
            for (const link of /** @type {NodeListOf<HTMLElement>} */ (drawerEl.querySelectorAll("[data-section-key]"))) {
                if (link.dataset.sectionKey === sectionKey) {
                    link.setAttribute("aria-current", "page");
                } else {
                    link.removeAttribute("aria-current");
                }
            }
        },
        dispose: () => {
            for (const remove of removals.splice(0)) {
                remove();
            }
        },
    };
}
