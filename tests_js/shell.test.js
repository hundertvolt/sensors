// Tests js/shell.js: section switching, the stop handle, the device clock and the build watch's reload rule.
import { afterEach, describe, expect, it, vi } from "vitest";
import { historyOf, startShell, visibilityOf } from "../js/shell.js";
import shellSource from "../js/shell.js?raw";
import { readIntConst } from "./_source_constants.js";

const WATCH_INTERVAL_MS = readIntConst(shellSource, "DEVICE_WATCH_INTERVAL_MS");

/** @type {import("../js/definitions.js").SiteDefinitions} */
const DEFS = {
    schemaVersion: "1.0.0",
    device: { id: "fixture-device", displayName: "Fixture Device" },
    landingSection: "measurements",
    defaultPollIntervalMs: 3000,
    sections: [
        { key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: "settings", groups: [] },
        { key: "status", label: "Status", rest: { get: "/status" }, pollGroup: "settings", groups: [] },
    ],
};

/**
 * One readonly timestamp, read as an age against the device's clock.
 * @type {import("../js/definitions.js").SiteDefinitions}
 */
const CLOCK_DEFS = {
    ...DEFS,
    sections: [
        {
            key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: "settings",
            groups: [{ key: "SENS", label: "Sensor", fields: [{ key: "TS", label: "Updated", kind: "readonly", format: "epoch" }] }],
        },
    ],
};

/**
 * One writable number, for an Apply the shell counts as pending.
 * @type {import("../js/definitions.js").SiteDefinitions}
 */
const APPLY_DEFS = {
    ...DEFS,
    landingSection: "settings",
    sections: [
        {
            key: "settings", label: "Settings", rest: { get: "/settings", put: "/settings" }, pollGroup: "settings",
            groups: [{ key: "main", label: "Main", submit: true, fields: [{ key: "Interval", label: "Interval", kind: "number", min: 1, max: 100 }] }],
        },
    ],
};

/**
 * @param {unknown} body
 * @param {number} [status]
 */
function json(body, status = 200) {
    return new Response(JSON.stringify(body), { status });
}

/**
 * Answers /status with `status()`, /system with the build `builds()` names (or `system()` itself), /measurements empty
 * and every path in `routes` its own way; 404 otherwise.
 * @param {{
 *   status?: () => unknown, builds?: () => unknown, system?: () => Promise<Response>,
 *   routes?: Record<string, (init: RequestInit | undefined) => Promise<Response>>,
 * }} [options]
 */
function installFetchStub({ status = () => ({ system: { UnixTime: 1_700_000_000 } }), builds = () => ({ version: "1.0.0" }), system, routes = {} } = {}) {
    const stub = vi.fn((/** @type {RequestInfo | URL} */ input, /** @type {RequestInit | undefined} */ init) => {
        const path = String(input);
        const route = routes[path];
        if (route !== undefined) {
            return route(init);
        }
        if (path === "/status") {
            return Promise.resolve(json(status()));
        }
        if (path === "/system") {
            return system ? system() : Promise.resolve(json({ build: builds() }));
        }
        if (path === "/measurements") {
            return Promise.resolve(json({}));
        }
        return Promise.resolve(json({ res: "ERR", code: 404, descr: "Not found", result: {} }, 404));
    });
    window.fetch = stub;
    return {
        /** @param {string} path */
        count: (path) => stub.mock.calls.filter(([input]) => String(input) === path).length,
        total: () => stub.mock.calls.length,
    };
}

/** A response the test releases by hand. */
function heldResponse() {
    /** @type {(response: Response) => void} */
    let release = () => { /* replaced below, before the promise is handed out */ };
    /** @type {Promise<Response>} */
    const promise = new Promise((resolve) => {
        release = resolve;
    });
    return { promise, release };
}

/**
 * GETs held on the wire until the test answers them, each rejecting once its signal aborts as a real fetch does;
 * `events` logs every send and answer in order.
 */
function wireRecorder() {
    /** @type {{signal: AbortSignal | null | undefined, answer: () => void}[]} */
    const wire = [];
    /** @type {string[]} */
    const events = [];
    /**
     * @param {string} path
     * @param {RequestInit | undefined} init
     * @returns {Promise<Response>}
     */
    const hold = (path, init) => new Promise((resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
        events.push(`sent ${path}`);
        const answer = () => {
            events.push(`answered ${path}`);
            resolve(json({}));
        };
        wire.push({ signal: init?.signal, answer });
    });
    return { wire, events, hold };
}

function buildElements() {
    const appShellEl = document.createElement("div");
    const mainEl = document.createElement("main");
    const drawerEl = document.createElement("nav");
    const hamburgerEl = document.createElement("button");
    const backdropEl = document.createElement("div");
    const elements = { appShellEl, mainEl, drawerEl, hamburgerEl, backdropEl };
    document.body.append(...Object.values(elements));
    return elements;
}

/** @param {boolean} [startHidden] */
function fakeVisibility(startHidden = false) {
    let hidden = startHidden;
    /** @type {Set<() => void>} */
    const listeners = new Set();
    return {
        /** @type {import("../js/poll-manager.js").Visibility} */
        source: {
            isHidden: () => hidden,
            onChange: (callback) => {
                listeners.add(callback);
                return () => {
                    listeners.delete(callback);
                };
            },
        },
        /** @param {boolean} value */
        setHidden(value) {
            hidden = value;
            for (const callback of [...listeners]) {
                callback();
            }
        },
        get listenerCount() {
            return listeners.size;
        },
    };
}

/**
 * A section history the test drives: `pop(key)` is the browser's Back or Forward landing on that entry.
 * @param {string | null} [initial]
 */
function fakeHistory(initial = null) {
    let current = initial;
    /** @type {string[]} */
    const pushed = [];
    /** @type {Set<(key: string | null) => void>} */
    const listeners = new Set();
    return {
        source: {
            current: () => current,
            /** @param {string} key */
            push: (key) => {
                pushed.push(key);
                current = key;
            },
            /** @param {(key: string | null) => void} callback */
            onPop: (callback) => {
                listeners.add(callback);
                return () => {
                    listeners.delete(callback);
                };
            },
        },
        pushed,
        /** @param {string | null} key */
        pop(key) {
            current = key;
            for (const callback of [...listeners]) {
                callback(key);
            }
        },
        get listenerCount() {
            return listeners.size;
        },
    };
}

/**
 * The listeners still registered on `target`: every (type, listener) added and not removed since the spies began.
 * @param {EventTarget} target
 * @returns {() => number}
 */
function listenerCounter(target) {
    const added = vi.spyOn(target, "addEventListener");
    const removed = vi.spyOn(target, "removeEventListener");
    return () => added.mock.calls.filter(([type, listener]) => !removed.mock.calls.some(([t, l]) => t === type && l === listener)).length;
}

/** @param {HTMLElement} mainEl */
function headingOf(mainEl) {
    return mainEl.querySelector(".section-heading")?.textContent;
}

describe("startShell", () => {
    const originalFetch = window.fetch;
    /** @type {ReturnType<typeof buildElements> | undefined} */
    let elements;
    /** @type {(() => void) | undefined} */
    let stop;

    afterEach(() => {
        stop?.();
        stop = undefined;
        vi.useRealTimers();
        window.fetch = originalFetch;
        for (const el of Object.values(elements ?? {})) {
            el.remove();
        }
    });

    /**
     * @param {{
     *   defs?: import("../js/definitions.js").SiteDefinitions, visibility?: ReturnType<typeof fakeVisibility>,
     *   history?: ReturnType<typeof fakeHistory>, reload?: () => void, keyTarget?: EventTarget,
     * }} [parts]
     */
    function start({ defs = DEFS, visibility = fakeVisibility(), history = fakeHistory(), reload = vi.fn(), keyTarget = new EventTarget() } = {}) {
        elements = buildElements();
        stop = startShell({ defs, elements, keyTarget, visibility: visibility.source, history: history.source, reload });
        return { elements, visibility, history, reload, keyTarget };
    }

    it("opens the landing section, and leaves no timer, listener or request behind once stopped", async () => {
        vi.useFakeTimers();
        const requests = installFetchStub();
        const keyTarget = new EventTarget();
        const keyListeners = listenerCounter(keyTarget);
        const { elements: shown, visibility, history } = start({ keyTarget });
        await vi.waitFor(() => expect(requests.count("/system")).toBe(1));
        expect(headingOf(shown.mainEl)).toBe("Measurements");
        expect(keyListeners()).toBe(1);

        stop?.();
        stop = undefined;
        const before = requests.total();
        await vi.advanceTimersByTimeAsync(3 * WATCH_INTERVAL_MS);

        expect(requests.total()).toBe(before);
        expect(vi.getTimerCount()).toBe(0);
        expect(keyListeners()).toBe(0);
        expect(visibility.listenerCount).toBe(0);
        expect(history.listenerCount).toBe(0);
    });

    it("leaves one set of listeners after start, stop and start again", () => {
        installFetchStub();
        const keyTarget = new EventTarget();
        const keyListeners = listenerCounter(keyTarget);
        const visibility = fakeVisibility();
        const history = fakeHistory();
        start({ keyTarget, visibility, history });
        const firstCounts = [keyListeners(), visibility.listenerCount, history.listenerCount];
        stop?.();

        start({ keyTarget, visibility, history });

        expect([keyListeners(), visibility.listenerCount, history.listenerCount]).toEqual(firstCounts);
        expect(firstCounts[0]).toBe(1);
    });

    it("reloads once when the second watch sees a different build, stopping first", async () => {
        vi.useFakeTimers();
        let version = "1.0.0";
        const requests = installFetchStub({ builds: () => ({ version }) });
        const { reload } = start();
        await vi.waitFor(() => expect(requests.count("/system")).toBe(1));
        version = "1.0.1";

        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
        const before = requests.total();
        await vi.advanceTimersByTimeAsync(3 * WATCH_INTERVAL_MS);

        expect(reload).toHaveBeenCalledTimes(1);
        expect(requests.total()).toBe(before);
        expect(vi.getTimerCount()).toBe(0);
    });

    it("never reloads while the build stays the same, or when /system carries no build object", async () => {
        vi.useFakeTimers();
        /** @type {unknown} */
        let build = { version: "1.0.0" };
        const requests = installFetchStub({ builds: () => build });
        const { reload } = start();
        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(requests.count("/system")).toBe(2));
        build = undefined;
        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(requests.count("/system")).toBe(3));

        expect(reload).not.toHaveBeenCalled();
    });

    it("pauses the watch while the page is hidden and watches once on becoming visible", async () => {
        vi.useFakeTimers();
        const requests = installFetchStub();
        const { visibility } = start();
        await vi.waitFor(() => expect(requests.count("/system")).toBe(1));

        visibility.setHidden(true);
        await vi.advanceTimersByTimeAsync(3 * WATCH_INTERVAL_MS);
        expect(requests.count("/system")).toBe(1);

        visibility.setHidden(false);
        await vi.waitFor(() => expect(requests.count("/system")).toBe(2));
    });

    it("neither reloads nor rejects unhandled when the watch's /system request fails", async () => {
        const unhandled = vi.fn();
        window.addEventListener("unhandledrejection", unhandled);
        vi.useFakeTimers();
        const requests = installFetchStub({ system: () => Promise.reject(new TypeError("Failed to fetch")) });
        const { reload } = start();
        await vi.waitFor(() => expect(requests.count("/system")).toBe(1));
        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(requests.count("/system")).toBe(2));

        vi.useRealTimers();
        await new Promise((resolve) => {
            setTimeout(resolve, 50);
        });
        window.removeEventListener("unhandledrejection", unhandled);
        expect(unhandled).not.toHaveBeenCalled();
        expect(reload).not.toHaveBeenCalled();
    });

    it("shows ages against the device's clock: unknown until /status carries UnixTime, then tracking it as time passes", async () => {
        vi.useFakeTimers();
        // The device's clock runs a day behind the browser's, so an age read off the browser's clock would say "1 d ago".
        const deviceNowS = () => Math.floor(Date.now() / 1000) - 86_400;
        const takenAtS = deviceNowS() - 100;
        /** @type {() => number | null} */
        let unixTime = () => null;
        const requests = installFetchStub({
            status: () => ({ system: { UnixTime: unixTime() } }),
            routes: { "/measurements": () => Promise.resolve(json({ SENS: { TS: takenAtS } })) },
        });
        const { elements: shown } = start({ defs: CLOCK_DEFS });
        const age = () => shown.mainEl.querySelector('.field-value[data-field-key="TS"]')?.textContent;
        const reopen = () => /** @type {HTMLElement} */ (shown.drawerEl.querySelector('[data-section-key="measurements"]')).click();
        await vi.waitFor(() => expect(age()).toBe("age unknown"));

        unixTime = deviceNowS;
        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(requests.count("/system")).toBe(2));
        reopen();
        await vi.waitFor(() => expect(age()).toBe("2 min ago"));

        await vi.advanceTimersByTimeAsync(2 * 3_600_000);
        reopen();
        await vi.waitFor(() => expect(age()).toBe("2 h ago"));
    });

    it("defers a reload for a changed build until the pending Apply has settled", async () => {
        vi.useFakeTimers();
        let version = "1.0.0";
        let statusCalls = 0;
        let putSeen = false;
        let postWriteGets = 0;
        const heldStatus = heldResponse();
        const heldRefresh = heldResponse();
        const requests = installFetchStub({
            builds: () => ({ version }),
            routes: {
                "/status": () => {
                    statusCalls += 1;
                    return statusCalls === 2 ? heldStatus.promise : Promise.resolve(json({ system: { UnixTime: 1_700_000_000 } }));
                },
                "/settings": (init) => {
                    if (init?.method === "PUT") {
                        putSeen = true;
                        return Promise.resolve(json({ res: "OK", code: 0, descr: "Command executed", result: { Interval: "Valid" } }));
                    }
                    if (putSeen) {
                        postWriteGets += 1;
                        return heldRefresh.promise;
                    }
                    return Promise.resolve(json({ Interval: 10 }));
                },
            },
        });
        const { elements: shown, reload } = start({ defs: APPLY_DEFS });
        await vi.waitFor(() => expect(requests.count("/system")).toBe(1));
        version = "2.0.0";
        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(statusCalls).toBe(2));

        // The second watch's /status is held while Apply is pressed: its /system then lands inside the Apply.
        const input = /** @type {HTMLInputElement} */ (shown.mainEl.querySelector('input[data-field-key="Interval"]'));
        input.value = "5";
        /** @type {HTMLButtonElement} */ (shown.mainEl.querySelector(".apply-button")).click();
        heldStatus.release(json({ system: { UnixTime: 1_700_000_000 } }));
        await vi.waitFor(() => expect(postWriteGets).toBe(1));

        expect(requests.count("/system")).toBe(2);
        expect(reload).not.toHaveBeenCalled();
        heldRefresh.release(json({ Interval: 5 }));
        await vi.waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    });

    it("watches once more as soon as a section's failing episode ends, not only at its own cadence", async () => {
        vi.useFakeTimers();
        vi.spyOn(console, "error").mockImplementation(() => { /* the section's own once-per-episode failure line */ });
        let failing = true;
        const requests = installFetchStub({
            routes: { "/measurements": () => Promise.resolve(failing ? json({ res: "ERR", code: 500, descr: "Internal server error", result: {} }, 500) : json({})) },
        });
        const startedAt = Date.now();
        start();
        await vi.waitFor(() => expect(requests.count("/system")).toBe(1));
        await vi.waitFor(() => expect(requests.count("/measurements")).toBe(1));
        failing = false;

        await vi.advanceTimersByTimeAsync(DEFS.defaultPollIntervalMs);
        await vi.waitFor(() => expect(requests.count("/system")).toBe(2));

        expect(Date.now() - startedAt).toBeLessThan(WATCH_INTERVAL_MS);
        vi.mocked(console.error).mockRestore();
    });

    it("pushes one history entry per menu selection of another section, none for the current one", () => {
        installFetchStub();
        const { elements: shown, history } = start();
        const statusLink = /** @type {HTMLElement} */ (shown.drawerEl.querySelector('[data-section-key="status"]'));

        statusLink.click();
        statusLink.click();

        expect(history.pushed).toEqual(["status"]);
        expect(headingOf(shown.mainEl)).toBe("Status");
        expect(statusLink.getAttribute("aria-current")).toBe("page");
    });

    it("selects the popped section without pushing: Back, then Forward, then back to the landing entry", () => {
        installFetchStub();
        const { elements: shown, history } = start();
        /** @type {HTMLElement} */ (shown.drawerEl.querySelector('[data-section-key="status"]')).click();

        history.pop(null);
        expect(headingOf(shown.mainEl)).toBe("Measurements");
        history.pop("status");
        expect(headingOf(shown.mainEl)).toBe("Status");
        history.pop("measurements");
        expect(headingOf(shown.mainEl)).toBe("Measurements");

        expect(history.pushed).toEqual(["status"]);
        const current = shown.drawerEl.querySelector('[aria-current="page"]');
        expect(current?.getAttribute("data-section-key")).toBe("measurements");
    });

    it("on a switch lets the left section's GET on the wire end before the next section's first GET, and a page stop right after a switch aborts it", async () => {
        const { wire, events, hold } = wireRecorder();
        let statusGets = 0;
        installFetchStub({
            routes: {
                "/measurements": (init) => hold("/measurements", init),
                // The watch's own /status answers at once; the status section's first GET stays on the wire.
                "/status": (init) => {
                    statusGets += 1;
                    return statusGets === 1 ? Promise.resolve(json({ system: { UnixTime: 1_700_000_000 } })) : hold("/status", init);
                },
            },
        });
        const { elements: shown } = start();
        /** @param {string} key */
        const select = (key) => /** @type {HTMLElement} */ (shown.drawerEl.querySelector(`[data-section-key="${key}"]`)).click();
        await vi.waitFor(() => expect(events).toEqual(["sent /measurements"]));

        select("status");
        await new Promise((resolve) => {
            setTimeout(resolve, 50);
        });
        expect(wire[0]?.signal?.aborted).toBe(false);
        expect(statusGets).toBe(1);
        wire[0]?.answer();
        await vi.waitFor(() => expect(events).toEqual(["sent /measurements", "answered /measurements", "sent /status"]));

        select("measurements");
        stop?.();
        stop = undefined;
        await vi.waitFor(() => expect(wire[1]?.signal?.aborted).toBe(true));
    });

    it("opens a deep-linked section, and the landing section for an unknown key, pushing nothing", () => {
        installFetchStub();
        const deepLink = start({ history: fakeHistory("status") });
        expect(headingOf(deepLink.elements.mainEl)).toBe("Status");
        stop?.();
        for (const el of Object.values(deepLink.elements)) {
            el.remove();
        }

        const unknown = start({ history: fakeHistory("no-such-section") });

        expect(headingOf(unknown.elements.mainEl)).toBe("Measurements");
        expect([deepLink.history.pushed, unknown.history.pushed]).toEqual([[], []]);
    });
});

describe("historyOf and visibilityOf", () => {
    const originalUrl = window.location.href;

    afterEach(() => {
        window.history.replaceState(null, "", originalUrl);
    });

    it("reads the section from the URL hash, pushes one entry per key and reports a Back as a pop", async () => {
        const history = historyOf(window);
        expect(history.current()).toBeNull();

        history.push("status");
        expect(window.location.hash).toBe("#status");
        expect(history.current()).toBe("status");

        /** @type {(string | null)[]} */
        const popped = [];
        const removePop = history.onPop((key) => popped.push(key));
        window.history.back();
        await vi.waitFor(() => expect(popped).toEqual([null]));
        removePop();
        window.history.forward();
        await vi.waitFor(() => expect(history.current()).toBe("status"));
        expect(popped).toEqual([null]);
    });

    it("reads the document's visibility and reports each change until released", () => {
        const visibility = visibilityOf(document);
        expect(visibility.isHidden()).toBe(document.visibilityState === "hidden");
        const changes = vi.fn();
        const release = visibility.onChange(changes);

        document.dispatchEvent(new Event("visibilitychange"));
        release();
        document.dispatchEvent(new Event("visibilitychange"));

        expect(changes).toHaveBeenCalledTimes(1);
    });
});
