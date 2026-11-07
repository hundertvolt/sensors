/**
 * The page shell both entries share: the nav, section switching, the device watch and one stop handle.
 * Takes every document-derived input from its entry (SPECIFICATION.md Part H.2, H.3).
 */

import { initNav } from "./nav.js";
import { pollManager, startPolling } from "./poll-manager.js";
import { renderSection } from "./render.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("./poll-manager.js").Visibility} Visibility */
/** @typedef {{nowS: () => number | null, observe: (statusBody: unknown) => void}} DeviceClock */
/** @typedef {{current: () => string | null, push: (key: string) => void, onPop: (cb: (key: string | null) => void) => () => void}} SectionHistory */

/** Device watch cadence: the clock and the build compare. */
// @tunable web.device_watch_interval_ms = 60000
const DEVICE_WATCH_INTERVAL_MS = 60000;

/**
 * The open section as the URL's `#<key>`, one entry per selection from the menu, so Back and Forward walk the sections.
 * @param {Window} win
 * @returns {SectionHistory}
 */
export function historyOf(win) {
    const current = () => (win.location.hash.length > 1 ? win.location.hash.slice(1) : null);
    return {
        current,
        push: (key) => win.history.pushState({ section: key }, "", `#${key}`),
        onPop: (cb) => {
            const listener = () => cb(current());
            win.addEventListener("popstate", listener);
            return () => win.removeEventListener("popstate", listener);
        },
    };
}

/**
 * Starts the nav, the section the history names (else the landing one) and the device watch: the device's clock
 * offset, and a reload once the device reports another build, deferred while an Apply is pending.
 * @param {{
 *   defs: SiteDefinitions,
 *   elements: {appShellEl: HTMLElement, mainEl: HTMLElement, drawerEl: HTMLElement, hamburgerEl: HTMLElement, backdropEl: HTMLElement},
 *   keyTarget: EventTarget,
 *   visibility: Visibility,
 *   history: SectionHistory,
 *   reload: () => void,
 * }} options
 * @returns {() => void} stop: ends the section, the watch and every listener the shell added.
 */
export function startShell({ defs, elements, keyTarget, visibility, history, reload }) {
    const { mainEl, ...navElements } = elements;
    const watchAbort = new AbortController();
    let stopped = false;
    /** @type {string | null} */
    let currentKey = null;
    let stopSection = () => { /* no section rendered yet - replaced on the first select */ };
    /** @type {number | null} */
    let offsetS = null;
    /** @type {string | null} */
    let firstBuild = null;
    let reloadPending = false;
    let pendingApplies = 0;

    /** @type {DeviceClock} */
    const deviceClock = {
        nowS: () => (offsetS === null ? null : Math.floor(Date.now() / 1000 + offsetS)),
        observe: (statusBody) => {
            const unixTime = /** @type {{system?: {UnixTime?: unknown}} | null} */ (statusBody)?.system?.UnixTime;
            if (typeof unixTime === "number") {
                offsetS = unixTime - Date.now() / 1000;
            }
        },
    };
    const applyTracker = {
        begin: () => {
            pendingApplies += 1;
        },
        end: () => {
            pendingApplies -= 1;
            reloadIfDue();
        },
    };
    const ignoreWatchFailure = () => { /* silent: the section's own GET owns the banner */ };
    const watchNow = () => {
        watchOnce().catch(ignoreWatchFailure);
    };
    /** @param {string | null} key */
    const knownOrLanding = (key) => defs.sections.find((entry) => entry.key === key)?.key ?? defs.landingSection;

    const nav = initNav({ defs, ...navElements, keyTarget, onSelect: (key) => selectSection(key, { push: true }) });
    const removePop = history.onPop((key) => selectSection(knownOrLanding(key)));
    const stopWatch = startPolling(watchOnce, DEVICE_WATCH_INTERVAL_MS, { visibility, onError: ignoreWatchFailure });

    async function watchOnce() {
        const { signal } = watchAbort;
        const status = await pollManager.request("/status", undefined, undefined, signal);
        if (status.ok) {
            deviceClock.observe(status.body);
        }
        const system = await pollManager.request("/system", undefined, undefined, signal);
        const build = system.ok ? /** @type {{build?: unknown} | null} */ (system.body)?.build : undefined;
        if (stopped || typeof build !== "object" || build === null) {
            return;
        }
        const seen = JSON.stringify(build);
        firstBuild ??= seen;
        if (seen !== firstBuild) {
            reloadPending = true;
            reloadIfDue();
        }
    }

    /**
     * @param {string} key
     * @param {{push?: boolean}} [options]
     */
    function selectSection(key, { push = false } = {}) {
        const section = defs.sections.find((entry) => entry.key === key);
        if (section === undefined) {
            return; // unreachable - narrows the type for tsc: keys come from defs.sections
        }
        if (push && key !== currentKey) {
            history.push(key);
        }
        currentKey = key;
        stopSection();
        nav.setCurrent(key);
        stopSection = renderSection(defs, section, mainEl, { visibility, deviceClock, onRecovered: watchNow, applyTracker });
    }

    function reloadIfDue() {
        if (reloadPending && pendingApplies === 0 && !stopped) {
            stop(); // frees the device's sockets for the reload's own requests
            reload();
        }
    }

    function stop() {
        if (stopped) {
            return;
        }
        stopped = true;
        stopSection();
        stopWatch();
        watchAbort.abort();
        nav.dispose();
        removePop();
    }

    selectSection(knownOrLanding(history.current()));
    return stop;
}

/**
 * The document's visibility as the poll loops read it.
 * @param {Document} doc
 * @returns {Visibility}
 */
export function visibilityOf(doc) {
    return {
        isHidden: () => doc.visibilityState === "hidden",
        onChange: (cb) => {
            doc.addEventListener("visibilitychange", cb);
            return () => doc.removeEventListener("visibilitychange", cb);
        },
    };
}
