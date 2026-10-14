// Server-side Vitest Commands API module backing tests_js/live-backend.test.js: spawns the twin
// and drives a real Playwright page against it directly (Vitest's own browser-mode `page` has no
// API for navigating to an external origin - vitest-dev/vitest#7875). See SPECIFICATION.md Part H.7.

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { connect } from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { drainChildOutput } from "./_memory_markers.js";
import { readIntConst } from "./_source_constants.js";
import { HOST, READY_TIMEOUT_MS, SHUTDOWN_TIMEOUT_MS, holdTwinPorts, makeConfigDir, removeConfigDir, requireInterpreter, spawnTwin, stopTwin, twinVerdict, waitUntilServing } from "./_twin_process.js";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// Clear of every fixed port and band tests/, tests_scripts/, scripts/ and digital_twin/ bind (the
// full map is in SPECIFICATION.md Part E.1): a twin tier running on the same host at the same time
// would otherwise refuse this one's bind. 19482 is _live_matrix_command.js's, in one `npm test` run.
const PORT = 19481;
// @tunable l0.live_twin_section_wait_ms = 10000
const SECTION_WAIT_MS = 10000;
// @tunable l0.live_twin_tab_wait_ms = 20000
const TAB_WAIT_MS = 20000;
// The page's own request timeout (pinned equal to the server's outer cap by test_request_timeout_ceiling.py) and its
// longest retry wait: a tab or a recovery taking longer than these is the page's failure, not the network's.
const POLL_MANAGER_SOURCE = readFileSync(path.join(REPO_ROOT, "js", "poll-manager.js"), "utf8");
const OUTER_CAP_MS = readIntConst(POLL_MANAGER_SOURCE, "DEFAULT_TIMEOUT_MS");
const POLL_BACKOFF_MAX_MS = readIntConst(POLL_MANAGER_SOURCE, "POLL_BACKOFF_MAX_MS");

/**
 * Whether anything accepts a connection on the twin's port; a listener whose queue is full still holds it.
 * @returns {Promise<boolean>}
 */
function portAnswers() {
    return new Promise((resolve) => {
        const socket = connect({ host: HOST, port: PORT });
        socket.setTimeout(SHUTDOWN_TIMEOUT_MS);
        socket.once("connect", () => {
            socket.destroy();
            resolve(true);
        });
        socket.once("timeout", () => {
            socket.destroy();
            resolve(true);
        });
        socket.once("error", () => {
            resolve(false);
        });
    });
}

/**
 * Throws while the twin's port still answers: a twin this check did not start would serve its page and readiness
 * polls, and the check would test that twin as its own (SPECIFICATION.md Part H.7: one twin at a time).
 * @param {string} device
 * @param {string} when
 */
async function assertPortFree(device, when) {
    if (await portAnswers()) {
        throw new Error(`${HOST}:${PORT} still answers ${when} ${device}'s twin: another twin holds the port, and this check would test that one instead of its own`);
    }
}

/**
 * The parts of a device's generated definitions these commands read (the full shape: js/definitions.js, whose DOM
 * types this Node program does not load).
 * @typedef {{landingSection: string, sections: {key: string, rest: {get: string}, groups: {fields?: {key: string, max?: number}[]}[]}[]}} LiveDefinitions
 */

/**
 * @param {string} device
 * @returns {LiveDefinitions} the device's generated definitions, as its site inlines them
 */
function definitionsOf(device) {
    return JSON.parse(readFileSync(path.join(REPO_ROOT, "build", "generated_src", "definitions", `${device}.json`), "utf8"));
}

/**
 * `promise` itself, marked handled: a wait started before the step it watches must not reject unhandled when an
 * earlier step throws and the page closes first.
 * @template T
 * @param {Promise<T>} promise
 * @returns {Promise<T>}
 */
function settledLater(promise) {
    promise.catch(() => { /* observed where it is awaited; this only keeps an early rejection from going unhandled */ });
    return promise;
}

/**
 * A live check's own clock. Vitest never cancels a command whose test timed out, so a check that outlived its test
 * kept its twin on the port into the next tests; a check's waits end one twin stop before its test's timeout instead.
 * @param {number} testTimeoutMs the calling test's own timeout
 */
function checkClock(testTimeoutMs) {
    const deadline = Date.now() + testTimeoutMs - SHUTDOWN_TIMEOUT_MS;
    let at = "starting";
    let over = false;
    return {
        /** @param {string} step what the check does next, named when its time runs out */
        step(step) {
            at = step;
        },
        /** Marks the check's teardown begun: a step still running after it opens nothing new. */
        end() {
            over = true;
        },
        isOver: () => over,
        /**
         * @template T
         * @param {Promise<T>} body the check's steps
         * @returns {Promise<T>} `body`, or a rejection naming the step it was in once its time is up
         */
        async within(body) {
            /** @type {ReturnType<typeof setTimeout> | undefined} */
            let timer;
            /** @type {Promise<never>} */
            const late = new Promise((_resolve, reject) => {
                timer = setTimeout(() => {
                    reject(new Error(`still ${at} when its test's ${testTimeoutMs}ms were up, less the ${SHUTDOWN_TIMEOUT_MS}ms kept for stopping its twin`));
                }, Math.max(0, deadline - Date.now()));
            });
            try {
                return await Promise.race([settledLater(body), late]);
            } finally {
                clearTimeout(timer);
            }
        },
        /**
         * @param {import("playwright").BrowserContext} context the Commands API's context, whose browser opens the check's own
         * @returns {Promise<import("playwright").BrowserContext>} the check's own context, closed at once if the check ended first
         */
        async newContext(context) {
            const browser = context.browser();
            if (browser === null) {
                throw new Error("the Commands API's context has no browser to open the check's own context in");
            }
            const own = await browser.newContext();
            if (over) {
                await own.close().catch(() => { /* best-effort teardown - a context already gone is fine */ });
                throw new Error("the check ended while its browser context opened");
            }
            return own;
        },
    };
}

/**
 * Closes the check's own browser context within one twin stop. Closing the context disposes it with every page in it, where a
 * page's own close waits for its target to detach: Chrome 153's headless shell never detaches a page closed just as a second
 * failed navigation commits its error page, and the check's pages then kept loading the next twin.
 * @param {import("playwright").BrowserContext[]} contexts the check's own context, once it has opened
 * @param {import("playwright").Page[]} pages its pages, named when the close outlasts the bound
 * @returns {Promise<Error | null>} why the close was still pending at that bound, or null
 */
async function closeContext(contexts, pages) {
    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let timer;
    const closed = Promise.all(contexts.map((own) => own.close().catch(() => { /* best-effort teardown - a context already gone is fine */ }))).then(() => null);
    /** @type {Promise<"late">} */
    const late = new Promise((resolve) => {
        timer = setTimeout(() => {
            resolve("late");
        }, SHUTDOWN_TIMEOUT_MS);
    });
    try {
        if (await Promise.race([closed, late]) === null) {
            return null;
        }
    } finally {
        clearTimeout(timer);
    }
    const tabs = pages.map((page, index) => `tab ${index + 1} (${page.url()}, isClosed ${page.isClosed()})`);
    return new Error(`its browser context was still closing ${SHUTDOWN_TIMEOUT_MS}ms after the check ended: ${tabs.join("; ")}; Chromium's page targets then: ${await pageTargets(/** @type {import("playwright").BrowserContext} */ (contexts[0]))}`);
}

/**
 * Chromium's own list of page targets (url, attached), asked over a browser-level CDP session within one section wait.
 * @param {import("playwright").BrowserContext} context
 * @returns {Promise<string>}
 */
async function pageTargets(context) {
    const browser = context.browser();
    if (browser === null) {
        return "(no browser)";
    }
    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let timer;
    const asked = (async () => {
        const cdp = await browser.newBrowserCDPSession();
        const { targetInfos } = await cdp.send("Target.getTargets");
        await cdp.detach();
        return targetInfos.filter((info) => info.type === "page").map((info) => `${info.url} attached=${info.attached}`).join(", ");
    })();
    /** @type {Promise<string>} */
    const late = new Promise((resolve) => {
        timer = setTimeout(() => {
            resolve(`(no answer within ${SECTION_WAIT_MS}ms)`);
        }, SECTION_WAIT_MS);
    });
    try {
        return await Promise.race([settledLater(asked).catch((err) => `(asking failed: ${String(err)})`), late]);
    } finally {
        clearTimeout(timer);
    }
}

/**
 * Applies `value` to the System page's DebugLevel and waits for the Apply to settle (the button enabled again: the
 * PUT and its post-write GET done), returning the field's result status.
 * @param {import("playwright").Page} page
 * @param {number} value
 * @returns {Promise<string | null>}
 */
async function applyDebugLevel(page, value) {
    const input = page.locator('[data-field-key="DebugLevel"]');
    const card = page.locator("[data-group-key]").filter({ has: input });
    await input.fill(String(value));
    await card.locator(".apply-button").click();
    await card.locator(".apply-button:enabled").waitFor({ timeout: SECTION_WAIT_MS });
    return page.locator('[data-field-wrapper-key="DebugLevel"]').getAttribute("data-apply-status");
}

// Delegated to buildgen rather than re-parsed here, so a key left out falls back to src/'s own
// default exactly as the build does. package.json's "pretest" hook already needs uv on PATH.
const CEILING_SCRIPT = "import sys; from pathlib import Path; from buildgen.validate import device_max_connections; print(device_max_connections(Path(sys.argv[1]), Path(sys.argv[2])))";

/**
 * The admission ceiling `devices/<device>.toml` builds, as buildgen itself resolves it.
 * @param {string} device
 * @param {string} [devicesDir] - the TOML directory, overridable for tests
 * @returns {number}
 */
export function configuredMaxConnections(device, devicesDir = path.join(REPO_ROOT, "devices")) {
    const tomlPath = path.join(devicesDir, `${device}.toml`);
    const out = execFileSync("uv", ["run", "--quiet", "python", "-c", CEILING_SCRIPT, tomlPath, path.join(REPO_ROOT, "src")], { cwd: REPO_ROOT, encoding: "utf8" });
    const ceiling = Number(out.trim());
    if (!Number.isInteger(ceiling) || ceiling < 1) {
        throw new Error(`buildgen resolved no usable max_connections for ${tomlPath}: ${JSON.stringify(out)}`);
    }
    return ceiling;
}

/**
 * Applies a DebugLevel other than the twin's own, then the same value again: the first answer must be exactly
 * "valid", the identical resubmit exactly "unchanged" (a stored field, SPECIFICATION.md Part H.4).
 * @param {{context: import("playwright").BrowserContext}} ctx
 * @param {string} device a devices/<device>.toml stem, booted from its own generated module and site
 * @param {number} testTimeoutMs the calling test's own timeout (checkClock())
 * @returns {Promise<{titleHasSensorStation: boolean, deviceName: string, firstStatus: string | null, resubmitStatus: string | null}>}
 */
export async function runLiveBackendSmoke({ context }, device, testTimeoutMs) {
    const clock = checkClock(testTimeoutMs);
    requireInterpreter();

    await assertPortFree(device, "before starting");
    const configDir = makeConfigDir(); // the run's own config, removed once its twin stopped
    const proc = spawnTwin({ device, port: PORT, configDir });
    const output = drainChildOutput(proc);

    /** @type {import("playwright").BrowserContext[]} */
    const contexts = [];
    /** @type {import("playwright").Page[]} */
    const pages = [];
    /** @returns {Promise<{titleHasSensorStation: boolean, deviceName: string, firstStatus: string | null, resubmitStatus: string | null}>} */
    async function check() {
        clock.step("booting its twin");
        await waitUntilServing(proc, PORT, READY_TIMEOUT_MS);
        clock.step("reading GET /system");
        const system = /** @type {{DebugLevel?: unknown}} */ (await (await fetch(`http://${HOST}:${PORT}/system`)).json());
        const field = definitionsOf(device).sections.flatMap((section) => section.groups).flatMap((group) => group.fields ?? []).find((candidate) => candidate.key === "DebugLevel");
        if (typeof system.DebugLevel !== "number" || typeof field?.max !== "number") {
            throw new Error(`GET /system answered DebugLevel ${JSON.stringify(system.DebugLevel)}, or the definitions name no DebugLevel bound`);
        }
        const value = system.DebugLevel < field.max ? system.DebugLevel + 1 : system.DebugLevel - 1;

        clock.step("loading its page");
        const own = await clock.newContext(context);
        contexts.push(own);
        const page = await own.newPage();
        pages.push(page);
        const consoleMessages = [];
        page.on("console", (msg) => consoleMessages.push(`[console:${msg.type()}] ${msg.text()}`));
        page.on("pageerror", (err) => consoleMessages.push(`[pageerror] ${err.message}`));
        const gotoRes = await page.goto(`http://${HOST}:${PORT}/`);
        consoleMessages.push(`[goto] status=${gotoRes?.status()} url=${gotoRes?.url()}`);
        try {
            await page.waitForSelector('[data-section-key="system"]', { timeout: SECTION_WAIT_MS });
        } catch (err) {
            const html = await page.content();
            throw new Error(`${err instanceof Error ? err.message : String(err)}\n--- console ---\n${consoleMessages.join("\n")}\n--- html (first 2000 chars) ---\n${html.slice(0, 2000)}`, { cause: err });
        }

        const titleHasSensorStation = (await page.title()).includes("Sensor Station");
        const deviceName = (await page.locator("#device-name").textContent())?.trim() ?? "";

        clock.step("applying DebugLevel");
        // The nav is a slide-in drawer (SPECIFICATION.md Part H.4): its links take a click only once the
        // hamburger has opened it.
        await page.locator("#hamburger-button").click();
        await page.locator('[data-section-key="system"]').click();
        await page.locator('[data-field-key="DebugLevel"]').waitFor();
        const firstStatus = await applyDebugLevel(page, value);
        const resubmitStatus = await applyDebugLevel(page, value);
        return { titleHasSensorStation, deviceName, firstStatus, resubmitStatus };
    }

    /** @type {Awaited<ReturnType<typeof check>> | undefined} */
    let checked;
    /** @type {unknown} */
    let failure = null;
    try {
        checked = await clock.within(check());
    } catch (err) {
        failure = err;
    } finally {
        clock.end();
        for (const page of pages) {
            page.removeAllListeners();
        }
        const [unclosed] = await Promise.all([closeContext(contexts, pages), stopTwin(proc)]);
        failure ??= unclosed;
        removeConfigDir(configDir);
    }
    twinVerdict(`live-backend smoke check for ${device}`, [output], failure, await output.closed(SHUTDOWN_TIMEOUT_MS));
    if (checked === undefined) {
        throw new Error(`live-backend smoke check for ${device} ended with no result`);
    }
    return checked;
}

/**
 * Records every page's requests in flight. A reload waits on `settled()` until the other tabs have nothing left on the
 * network (agent, 2026-10-13; SPECIFICATION.md Part H.7.1: a follow-up into a full ceiling is refused until it has
 * drained), and the reset probe names what they had open when a reload still fails.
 * @param {import("playwright").Page[]} pages
 */
function trackInFlight(pages) {
    /** @type {Map<import("playwright").Request, number>[]} */
    const open = pages.map(() => new Map());
    /** @type {(() => boolean)[]} */
    let waiters = [];
    const notify = () => {
        waiters = waiters.filter((settle) => !settle());
    };
    for (const [index, page] of pages.entries()) {
        const mine = /** @type {Map<import("playwright").Request, number>} */ (open[index]);
        page.on("request", (request) => {
            mine.set(request, Date.now());
            notify();
        });
        page.on("requestfinished", (request) => {
            mine.delete(request);
            notify();
        });
        page.on("requestfailed", (request) => {
            mine.delete(request);
            notify();
        });
    }
    /**
     * @param {number} except the reloading tab
     * @param {Set<import("playwright").Request>} held requests kept in the browser, never sent to the twin
     */
    const quiet = (except, held) => open.every((mine, index) => index === except || [...mine.keys()].every((request) => held.has(request)));
    return {
        notify,
        /**
         * @param {number} except
         * @param {Set<import("playwright").Request>} held
         * @returns {string[]} each other tab's requests still in flight, with their age, the held ones marked
         */
        describe: (except, held) => open.flatMap((mine, index) => (index === except ? [] : [...mine].map(([request, since]) => `tab ${index + 1} ${request.method()} ${new URL(request.url()).pathname} (${Date.now() - since}ms${held.has(request) ? ", held" : ""})`))),
        /**
         * @param {number} except
         * @param {Set<import("playwright").Request>} held
         * @param {number} timeoutMs
         * @returns {Promise<boolean>} true once every request the other tabs still have in flight is a held one, false
         * if that is not so within `timeoutMs`
         */
        async settled(except, held, timeoutMs) {
            /** @type {ReturnType<typeof setTimeout> | undefined} */
            let timer;
            /** @type {(() => boolean) | undefined} */
            let settle;
            /** @type {Promise<boolean>} */
            const drained = new Promise((resolve) => {
                settle = () => {
                    if (!quiet(except, held)) {
                        return false;
                    }
                    resolve(true);
                    return true;
                };
                if (!settle()) {
                    waiters.push(settle);
                }
            });
            /** @type {Promise<boolean>} */
            const late = new Promise((resolve) => {
                timer = setTimeout(() => {
                    resolve(false);
                }, Math.max(0, timeoutMs));
            });
            try {
                return await Promise.race([drained, late]);
            } finally {
                clearTimeout(timer);
                waiters = waiters.filter((waiter) => waiter !== settle);
            }
        },
    };
}

/**
 * Keeps every new request of `pages` in the browser until `release()`, so those tabs open no connection while another
 * tab reloads: Playwright's routing, not Chromium's frozen lifecycle state, which left a headless page's timers running
 * (agent, 2026-10-13).
 * @param {import("playwright").Page[]} pages
 * @param {() => void} onHeld called after each request it holds
 */
async function holdRequests(pages, onHeld) {
    /** @type {import("playwright").Route[]} */
    const routes = [];
    /** @type {Set<import("playwright").Request>} */
    const held = new Set();
    /** @param {import("playwright").Route} route */
    const hold = (route) => {
        routes.push(route);
        held.add(route.request());
        onHeld();
    };
    await Promise.all(pages.map((page) => page.route("**/*", hold)));
    return {
        held,
        async release() {
            await Promise.all(pages.map((page) => page.unroute("**/*", hold).catch(() => { /* a closed page holds nothing */ })));
            await Promise.all(routes.map((route) => route.continue().catch(() => { /* its page closed or its request was aborted */ })));
        },
    };
}

/**
 * The first value under `key` anywhere in `value`, or undefined.
 * @param {unknown} value
 * @param {string} key
 * @returns {unknown}
 */
function findKey(value, key) {
    if (typeof value !== "object" || value === null) {
        return undefined;
    }
    if (key in value) {
        return /** @type {Record<string, unknown>} */ (value)[key];
    }
    return Object.values(value).map((inner) => findKey(inner, key)).find((found) => found !== undefined);
}

/**
 * The twin's own count of connections it dropped (GET /status's HTTPDropped), for the reset probe: one read within a
 * section wait, its failure reported in place of the count.
 * @returns {Promise<string>}
 */
async function droppedCount() {
    try {
        const response = await fetch(`http://${HOST}:${PORT}/status`, { signal: AbortSignal.timeout(SECTION_WAIT_MS) });
        const dropped = findKey(await response.json(), "HTTPDropped");
        return dropped === undefined ? `(no HTTPDropped in GET /status, HTTP ${response.status})` : String(dropped);
    } catch (err) {
        return `(GET /status failed: ${err instanceof Error ? err.message : String(err)})`;
    }
}

/**
 * Opens the page and waits for its shell, within `timeoutMs`.
 * @param {import("playwright").Page} page
 * @param {number} timeoutMs
 * @returns {Promise<string | null>} null once loaded, else why not
 */
async function loadPage(page, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    try {
        await page.goto(`http://${HOST}:${PORT}/`, { timeout: timeoutMs });
        await page.waitForSelector("[data-section-key]", { timeout: Math.max(1, deadline - Date.now()) });
        const deviceName = (await page.locator("#device-name").textContent())?.trim() ?? "";
        return deviceName === "" ? "the page loaded but named no device" : null;
    } catch (err) {
        return err instanceof Error ? err.message.split("\n")[0] ?? err.message : String(err);
    }
}

/**
 * Reloads tab `index` once the other tabs have drained, holding them meanwhile. Drain and reload share one TAB_WAIT_MS
 * slot; the drain gets at most its first TAB_WAIT_MS - SECTION_WAIT_MS, so the reload keeps at least one section wait,
 * and a drain still open then fails naming every request the other tabs had in flight (agent, 2026-10-13).
 * @param {import("playwright").Page[]} pages
 * @param {number} index the tab to reload
 * @param {ReturnType<typeof trackInFlight>} tracker
 * @param {ReturnType<typeof checkClock>} clock
 * @param {number} firstPassEnded when the tab's first pass failed
 * @returns {Promise<string | null>} null once loaded, else why not
 */
async function reloadAfterDrain(pages, index, tracker, clock, firstPassEnded) {
    clock.step(`waiting for the other tabs to drain before reloading tab ${index + 1}`);
    const drainFrom = Date.now();
    const slotEnd = drainFrom + TAB_WAIT_MS;
    const hold = await holdRequests(pages.filter((_, other) => other !== index), tracker.notify);
    try {
        const drained = await tracker.settled(index, hold.held, slotEnd - SECTION_WAIT_MS - Date.now());
        if (!drained) {
            return `tab ${index + 1}: not reloaded, the other tabs had not drained ${Date.now() - drainFrom}ms into its ${TAB_WAIT_MS}ms reload slot; their requests in flight then: ${tracker.describe(index, hold.held).join(", ")}`;
        }
        clock.step(`reloading tab ${index + 1}`);
        const reloadAt = Date.now();
        const retry = await loadPage(/** @type {import("playwright").Page} */ (pages[index]), slotEnd - reloadAt);
        if (retry === null) {
            return null;
        }
        const open = tracker.describe(index, hold.held).join(", ") || "none";
        return `tab ${index + 1} on its reload: ${retry} [reset probe: the reload began ${reloadAt - firstPassEnded}ms after its first-pass failure, ${reloadAt - drainFrom}ms of them waiting for the drain, and failed after ${Date.now() - reloadAt}ms; the other tabs' requests in flight then: ${open}]`;
    } finally {
        await hold.release();
    }
}

/**
 * A full connection ceiling of real-browser tabs against one live twin, all navigating at once: each load completes
 * or fails at the connection level within the page's own request cap, and every tab that did not load then loads on one
 * reload of its own, made after the others drain and while they are held (SPECIFICATION.md Parts H.7, H.7.1; agent, 2026-10-13).
 * @param {{context: import("playwright").BrowserContext}} ctx
 * @param {string} device a devices/<device>.toml stem; its own ceiling sizes the tab count
 * @param {number} testTimeoutMs the calling test's own timeout (checkClock())
 * @returns {Promise<{tabs: number, loadedFirstPass: number, loadedAfterRetry: number, failures: string[]}>}
 */
export async function runLiveBackendConcurrentTabs({ context }, device, testTimeoutMs) {
    const clock = checkClock(testTimeoutMs);
    requireInterpreter();
    const tabs = configuredMaxConnections(device);
    await assertPortFree(device, "before starting");
    const configDir = makeConfigDir();
    const proc = spawnTwin({ device, port: PORT, configDir });
    const output = drainChildOutput(proc);

    /** @type {import("playwright").BrowserContext[]} */
    const contexts = [];
    /** @type {import("playwright").Page[]} */
    const pages = [];
    /** @returns {Promise<{tabs: number, loadedFirstPass: number, loadedAfterRetry: number, failures: string[]}>} */
    async function check() {
        clock.step("booting its twin");
        await waitUntilServing(proc, PORT, READY_TIMEOUT_MS);
        clock.step("opening its tabs");
        const own = await clock.newContext(context);
        contexts.push(own);
        for (let i = 0; i < tabs; i += 1) {
            // eslint-disable-next-line no-await-in-loop -- pages are CREATED sequentially and NAVIGATED together below; that is what makes the loads concurrent rather than the setup
            pages.push(await own.newPage());
        }
        clock.step("loading every tab at once");
        const tracker = trackInFlight(pages);
        /** @type {number[]} */
        const firstPassEnded = pages.map(() => 0);
        const firstPass = await Promise.all(pages.map((page, index) => loadPage(page, OUTER_CAP_MS + 5000).then((reason) => {
            firstPassEnded[index] = Date.now();
            return reason;
        })));
        const failures = firstPass.flatMap((reason, index) => (reason === null ? [] : [`tab ${index + 1}: ${reason}`]));
        let loadedAfterRetry = firstPass.filter((reason) => reason === null).length;
        let reloadsFailed = 0;
        for (const [index, reason] of firstPass.entries()) {
            if (reason !== null) {
                // eslint-disable-next-line no-await-in-loop -- one reload at a time, each with the other tabs held
                const retry = await reloadAfterDrain(pages, index, tracker, clock, firstPassEnded[index] ?? 0);
                if (retry === null) {
                    loadedAfterRetry += 1;
                } else {
                    reloadsFailed += 1;
                    failures.push(retry);
                }
            }
        }
        if (reloadsFailed > 0) {
            failures.push(`[reset probe: the twin's HTTPDropped after the check: ${await droppedCount()}]`);
        }
        return { tabs, loadedFirstPass: firstPass.filter((reason) => reason === null).length, loadedAfterRetry, failures };
    }

    /** @type {Awaited<ReturnType<typeof check>> | undefined} */
    let checked;
    /** @type {unknown} */
    let failure = null;
    try {
        checked = await clock.within(check());
    } catch (err) {
        failure = err;
    } finally {
        clock.end();
        const [unclosed] = await Promise.all([closeContext(contexts, pages), stopTwin(proc)]);
        failure ??= unclosed;
        removeConfigDir(configDir);
    }
    twinVerdict(`live-backend concurrent-tab check for ${device}`, [output], failure, await output.closed(SHUTDOWN_TIMEOUT_MS));
    if (checked === undefined) {
        throw new Error(`live-backend concurrent-tab check for ${device} ended with no result`);
    }
    return checked;
}

/**
 * Opens the landing section, stops the twin once a poll has answered, waits for the section's banner, restarts the
 * twin on the same port and config, and watches the page recover by itself within the boot time and the longest
 * retry wait; `reloaded` is true when the page reloaded instead (the build did not change, so it must not).
 * @param {{context: import("playwright").BrowserContext}} ctx
 * @param {string} device a devices/<device>.toml stem
 * @param {number} testTimeoutMs the calling test's own timeout (checkClock())
 * @returns {Promise<{bannerShown: boolean, recovered: boolean, reloaded: boolean}>}
 */
export async function runLiveBackendRestartRecovery({ context }, device, testTimeoutMs) {
    const clock = checkClock(testTimeoutMs);
    requireInterpreter();
    const defs = definitionsOf(device);
    const landingGet = defs.sections.find((section) => section.key === defs.landingSection)?.rest.get ?? "";
    const answered = (/** @type {import("playwright").Response} */ response) => response.url() === `http://${HOST}:${PORT}${landingGet}` && response.status() === 200;
    const banner = (/** @type {"true" | "false"} */ shown) => `#app-main .error-banner[data-shown="${shown}"]`;

    await assertPortFree(device, "before starting");
    const releasePorts = holdTwinPorts(); // held across both boots, so no other runner takes the port between them
    const configDir = makeConfigDir(); // one config across both boots: the restart finds what the first boot wrote
    const procs = [spawnTwin({ device, port: PORT, configDir })];
    const outputs = [drainChildOutput(/** @type {import("node:child_process").ChildProcess} */ (procs[0]))];
    /** @type {import("playwright").BrowserContext[]} */
    const contexts = [];
    /** @type {import("playwright").Page[]} */
    const pages = [];
    /** @returns {Promise<{bannerShown: boolean, recovered: boolean, reloaded: boolean}>} */
    async function check() {
        clock.step("booting its twin");
        await waitUntilServing(/** @type {import("node:child_process").ChildProcess} */ (procs[0]), PORT, READY_TIMEOUT_MS);
        clock.step("loading its page");
        const own = await clock.newContext(context);
        contexts.push(own);
        const page = await own.newPage();
        pages.push(page);
        const firstPoll = settledLater(page.waitForResponse(answered, { timeout: SECTION_WAIT_MS }));
        await page.goto(`http://${HOST}:${PORT}/`);
        await firstPoll;
        await page.evaluate(() => {
            /** @type {Record<string, unknown>} */ (/** @type {unknown} */ (globalThis)).liveRestartMarker = "kept";
        });
        const urlBefore = page.url();

        clock.step("stopping its twin");
        await stopTwin(/** @type {import("node:child_process").ChildProcess} */ (procs[0]));
        await assertPortFree(device, "after stopping");
        clock.step("waiting for the banner");
        const bannerShown = await page.locator(banner("true")).waitFor({ timeout: SECTION_WAIT_MS }).then(() => true, () => false);

        const recoveredPoll = settledLater(page.waitForResponse(answered, { timeout: READY_TIMEOUT_MS + POLL_BACKOFF_MAX_MS }));
        if (clock.isOver()) {
            throw new Error("the check ended before its twin's restart"); // a step that outlasted the check starts no twin
        }
        clock.step("restarting its twin");
        const restarted = spawnTwin({ device, port: PORT, configDir });
        procs.push(restarted);
        outputs.push(drainChildOutput(restarted));
        await waitUntilServing(restarted, PORT, READY_TIMEOUT_MS);
        clock.step("waiting for the page to recover");
        // A hidden banner is display: none, so it is waited for as attached, never as visible.
        const recovered = await recoveredPoll.then(() => page.locator(banner("false")).waitFor({ state: "attached", timeout: SECTION_WAIT_MS })).then(() => true, () => false);
        const marker = await page.evaluate(() => /** @type {Record<string, unknown>} */ (/** @type {unknown} */ (globalThis)).liveRestartMarker);
        return { bannerShown, recovered, reloaded: page.url() !== urlBefore || marker !== "kept" };
    }

    /** @type {Awaited<ReturnType<typeof check>> | undefined} */
    let checked;
    /** @type {unknown} */
    let failure = null;
    try {
        checked = await clock.within(check());
    } catch (err) {
        failure = err;
    } finally {
        clock.end();
        try {
            const [unclosed] = await Promise.all([closeContext(contexts, pages), ...procs.map((proc) => stopTwin(proc))]);
            failure ??= unclosed;
        } finally {
            releasePorts();
            removeConfigDir(configDir);
        }
    }
    const drained = await Promise.all(outputs.map((output) => output.closed(SHUTDOWN_TIMEOUT_MS)));
    twinVerdict(`live-backend restart-recovery check for ${device}`, outputs, failure, drained.every(Boolean));
    if (checked === undefined) {
        throw new Error(`live-backend restart-recovery check for ${device} ended with no result`);
    }
    return checked;
}
