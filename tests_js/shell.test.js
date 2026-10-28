// Tests js/shell.js: section switching, the stop handle, the device clock and the build watch's reload rule, which both
// entries feed with the page's own build stamp.
import { afterEach, describe, expect, it, vi } from "vitest";
import { startApp as startPrototypeApp } from "../js/app.js";
import { startApp as startProductionApp } from "../js/main.js";
import { buildDateOf, historyOf, startShell, visibilityOf } from "../js/shell.js";
import shellSource from "../js/shell.js?raw";
import CODEGEN_SOURCE from "../buildgen/codegen.py?raw";
import STAGER_SOURCE from "../scripts/_stage_website.py?raw";
import { buildElements as buildPageElements } from "./_dom_helpers.js";
import { readIntConst } from "./_source_constants.js";

// The entries run the real shell; only the reload a test hands it is a spy, so a reload is seen and never done.
vi.mock("../js/shell.js", async (importOriginal) => {
    const real = /** @type {typeof import("../js/shell.js")} */ (await importOriginal());
    return { ...real, startShell: vi.fn(real.startShell) };
});

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
 * and every path in `routes` its own way; 404 otherwise. `read(path)` counts the /status and /system answers whose body
 * the shell has read: a watch's next one is scheduled only once its /system answer is read.
 * @param {{
 *   status?: () => unknown, builds?: () => unknown, system?: () => Promise<Response>,
 *   routes?: Record<string, (init: RequestInit | undefined) => Promise<Response>>,
 * }} [options]
 */
function installFetchStub({ status = () => ({ system: { UnixTime: 1_700_000_000 } }), builds = () => ({ version: "1.0.0" }), system, routes = {} } = {}) {
    /** @type {Map<string, number>} */
    const reads = new Map();
    /**
     * @param {string} path
     * @param {Response} response
     */
    const counted = (path, response) => {
        const text = response.text.bind(response);
        response.text = () => {
            const reading = text();
            reading.then(() => reads.set(path, (reads.get(path) ?? 0) + 1), () => { /* a body never read is no answer */ });
            return reading;
        };
        return response;
    };
    const stub = vi.fn((/** @type {RequestInfo | URL} */ input, /** @type {RequestInit | undefined} */ init) => {
        const path = String(input);
        const route = routes[path];
        if (route !== undefined) {
            return route(init);
        }
        if (path === "/status") {
            return Promise.resolve(counted(path, json(status())));
        }
        if (path === "/system") {
            return system ? system() : Promise.resolve(counted(path, json({ build: builds() })));
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
        /** @param {string} path */
        read: (path) => reads.get(path) ?? 0,
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
        window.fetch = originalFetch;
        for (const el of Object.values(elements ?? {})) {
            el.remove();
        }
    });

    /**
     * @param {{
     *   defs?: import("../js/definitions.js").SiteDefinitions, visibility?: ReturnType<typeof fakeVisibility>,
     *   history?: ReturnType<typeof fakeHistory>, reload?: () => void, keyTarget?: EventTarget, pageBuildDate?: string | null,
     * }} [parts]
     */
    function start({ defs = DEFS, visibility = fakeVisibility(), history = fakeHistory(), reload = vi.fn(), keyTarget = new EventTarget(), pageBuildDate = null } = {}) {
        elements = buildElements();
        stop = startShell({ defs, elements, keyTarget, visibility: visibility.source, history: history.source, reload, pageBuildDate });
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
        await vi.waitFor(() => expect(requests.read("/system")).toBe(1));
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
        await vi.waitFor(() => expect(requests.read("/system")).toBe(1));
        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(requests.count("/system")).toBe(2));
        await vi.waitFor(() => expect(requests.read("/system")).toBe(2));
        build = undefined;
        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(requests.count("/system")).toBe(3));
        await vi.waitFor(() => expect(requests.read("/system")).toBe(3));

        expect(reload).not.toHaveBeenCalled();
    });

    it("reloads once the first build the watch reads differs from the page's own: a reflash before the first watch", async () => {
        vi.useFakeTimers();
        let rebooting = true;
        const requests = installFetchStub({
            system: () => Promise.resolve(rebooting ? json({ res: "ERR", code: 503, descr: "Rebooting", result: {} }, 503) : json({ build: { BuildDate: "2026-02-02T00:00:00Z" } })),
        });
        const { reload } = start({ pageBuildDate: "2026-01-01T00:00:00Z" });
        await vi.waitFor(() => expect(requests.count("/system")).toBe(1));
        rebooting = false;

        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
        expect(requests.count("/system")).toBe(2);
    });

    it.each([
        ["the page's build date matches the device's", "2026-01-01T00:00:00Z", { BuildDate: "2026-01-01T00:00:00Z" }],
        ["the page carries none", null, { BuildDate: "2026-02-02T00:00:00Z" }],
        ["the device sends none", "2026-01-01T00:00:00Z", { FirmwareVersion: "1.0.0" }],
    ])("never reloads for the page's build when %s", async (_case, pageBuildDate, build) => {
        vi.useFakeTimers();
        const requests = installFetchStub({ builds: () => build });
        const { reload } = start({ pageBuildDate });
        await vi.waitFor(() => expect(requests.read("/system")).toBe(1));
        await vi.advanceTimersByTimeAsync(WATCH_INTERVAL_MS);
        await vi.waitFor(() => expect(requests.read("/system")).toBe(2));

        expect(reload).not.toHaveBeenCalled();
    });

    it("pauses the watch while the page is hidden and watches once on becoming visible", async () => {
        vi.useFakeTimers();
        const requests = installFetchStub();
        const { visibility } = start();
        await vi.waitFor(() => expect(requests.count("/system")).toBe(1));
        await vi.waitFor(() => expect(requests.read("/system")).toBe(1));

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
        await vi.waitFor(() => expect(requests.read("/system")).toBe(1));

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
        await vi.waitFor(() => expect(requests.read("/system")).toBe(1));
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

describe("buildDateOf, historyOf and visibilityOf", () => {
    const originalUrl = window.location.href;

    afterEach(() => {
        window.history.replaceState(null, "", originalUrl);
    });

    it("reads the page's build stamp the stager writes, and null without one", () => {
        expect(STAGER_SOURCE).toContain('<meta name="build-date" content="{build_date}">');
        expect(CODEGEN_SOURCE).toContain('"BuildDate": _BUILD_DATE');
        expect(buildDateOf(document)).toBeNull();
        const meta = document.createElement("meta");
        meta.name = "build-date";
        meta.content = "2026-01-01T00:00:00Z";
        document.head.append(meta);
        try {
            expect(buildDateOf(document)).toBe("2026-01-01T00:00:00Z");
            meta.content = "";
            expect(buildDateOf(document)).toBeNull();
        } finally {
            meta.remove();
        }
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

describe("the entries' page stamp", () => {
    const originalFetch = window.fetch;
    const PAGE_BUILD = "2026-01-01T00:00:00Z";
    const BUILD_GROUP = { key: "build", label: "Build", fields: [{ key: "BuildDate", label: "Build Date", kind: "readonly", path: ["build", "BuildDate"] }] };
    const ENTRY_DEFS = { ...DEFS, sections: [...DEFS.sections, { key: "system", label: "System", rest: { get: "/system" }, pollGroup: "settings", groups: [BUILD_GROUP] }] };
    const DEVICE_BUILD = { BuildDate: "2026-02-02T00:00:00Z" };
    const SAMPLES = {
        measurements: {}, sensorsConfig: {}, networkingConfig: {}, systemConfig: { build: DEVICE_BUILD }, notificationConfig: {},
        status: { networking: {}, system: {}, sensors: {}, notification: {} }, errcount: {},
    };
    // Each entry with the files it fetches: the production one asks the device itself, the prototype its mock backend.
    const ENTRIES = [
        { entry: "js/main.js", startApp: startProductionApp, files: { "definitions.json": ENTRY_DEFS, "/measurements": {}, "/status": {}, "/system": { build: DEVICE_BUILD } } },
        { entry: "js/app.js", startApp: startPrototypeApp, files: { "../build/generated_src/definitions/index.json": { devices: ["fixture-device"] }, "../build/generated_src/definitions/fixture-device.json": ENTRY_DEFS, "../mockdata/samples.json": SAMPLES } },
    ];
    /** @type {(() => void)[]} */
    const cleanups = [];

    afterEach(() => {
        for (const cleanup of cleanups.splice(0).reverse()) {
            cleanup();
        }
        window.fetch = originalFetch;
    });

    for (const { entry, startApp, files } of ENTRIES) {
        it(`${entry} reloads once its device reports another build than the page's own stamp: a reflash before the first watch`, async () => {
            const meta = document.createElement("meta");
            meta.name = "build-date";
            meta.content = PAGE_BUILD;
            document.head.append(meta);
            cleanups.push(() => meta.remove());
            window.fetch = vi.fn((/** @type {RequestInfo | URL} */ input) => {
                const body = /** @type {Record<string, unknown>} */ (files)[String(input)];
                return Promise.resolve(body === undefined ? new Response("not found", { status: 404 }) : new Response(JSON.stringify(body), { status: 200 }));
            });
            const real = /** @type {typeof import("../js/shell.js")} */ (await vi.importActual("../js/shell.js"));
            const reload = vi.fn();
            vi.mocked(startShell).mockImplementationOnce((options) => real.startShell({ ...options, reload }));
            const elements = buildPageElements();
            cleanups.push(() => {
                for (const el of Object.values(elements)) {
                    el.remove();
                }
            });

            const stop = await startApp(elements);
            cleanups.push(stop);

            expect(elements.errorBannerEl.dataset.shown).toBe("false");
            await vi.waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
        });
    }
});
