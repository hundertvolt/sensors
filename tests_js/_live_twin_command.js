// Server-side Vitest Commands API module backing tests_js/live-backend.test.js: spawns the twin
// and drives a real Playwright page against it directly (Vitest's own browser-mode `page` has no
// API for navigating to an external origin - vitest-dev/vitest#7875). See SPECIFICATION.md Part H.7.

import { execFileSync, spawn } from "node:child_process";
import { existsSync, readFileSync, rmSync } from "node:fs";
import { connect } from "node:net";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { drainChildOutput } from "./_memory_markers.js";
import { readIntConst } from "./_source_constants.js";
import { twinStartFailure } from "./_twin_start_failure.js";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const TOOLCHAIN_DIR = process.env.PICO_TOOLCHAIN_DIR || path.join(homedir(), "pico-toolchain");
const MICROPYTHON_BIN = path.join(TOOLCHAIN_DIR, "micropython", "ports", "unix", "build-standard", "micropython");
const HOST = "127.0.0.1";
// Clear of every fixed port and band tests/, tests_scripts/, scripts/ and digital_twin/ bind (the
// full map is in SPECIFICATION.md Part E.1): a twin tier running on the same host at the same time
// would otherwise refuse this one's bind. 19482 is _live_matrix_command.js's, in one `npm test` run.
const PORT = 19481;
// @tunable l0.live_twin_ready_timeout_ms = 20000
const READY_TIMEOUT_MS = 20000;
// @tunable l0.live_twin_shutdown_timeout_ms = 15000
const SHUTDOWN_TIMEOUT_MS = 15000;
// @tunable l0.live_twin_section_wait_ms = 10000
const SECTION_WAIT_MS = 10000;
// @tunable l0.live_twin_tab_wait_ms = 20000
const TAB_WAIT_MS = 20000;
// The page's own request timeout (pinned equal to the server's outer cap by test_request_timeout_ceiling.py) and its
// longest retry wait: a tab or a recovery taking longer than these is the page's failure, not the network's.
const POLL_MANAGER_SOURCE = readFileSync(path.join(REPO_ROOT, "js", "poll-manager.js"), "utf8");
const OUTER_CAP_MS = readIntConst(POLL_MANAGER_SOURCE, "DEFAULT_TIMEOUT_MS");
const POLL_BACKOFF_MAX_MS = readIntConst(POLL_MANAGER_SOURCE, "POLL_BACKOFF_MAX_MS");
const MISSING_INTERPRETER = `MicroPython Unix port not built at ${MICROPYTHON_BIN} - run 'uv run toolchain/setup_toolchain.py setup' first (CI's web-unit-tests job does this automatically)`;
/** @type {WeakMap<import("node:child_process").ChildProcess, Error>} */
const spawnErrors = new WeakMap();

/** @param {number} ms */
function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

/**
 * @param {import("node:child_process").ChildProcess} proc
 * @param {number} timeoutMs
 */
async function waitUntilServing(proc, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        const failure = twinStartFailure({ spawnError: spawnErrors.get(proc) ?? null, exitCode: proc.exitCode, signalCode: proc.signalCode });
        if (failure !== null) {
            throw new Error(failure);
        }
        try {
            // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
            const res = await fetch(`http://${HOST}:${PORT}/`);
            if (res.status === 200) {
                return;
            }
        } catch {
            // Not up yet - keep polling.
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        await sleep(250);
    }
    throw new Error(`digital twin never started serving on ${HOST}:${PORT} within ${timeoutMs}ms`);
}

/**
 * build/generated_src first: sensortask_<device>.py exists only there (SPECIFICATION.md Part L.2),
 * generated with the device's own site (build/generated_html/<device>) by package.json's "pretest"
 * hooks, so a twin never serves another device's site.
 * @param {string} device
 */
function spawnTwin(device) {
    const micropypath = `build/generated_src:src:digital_twin:ext:build/generated_html/${device}:.frozen`;
    const proc = spawn(
        MICROPYTHON_BIN,
        [
            "digital_twin/run_generic_integration.py",
            "--module",
            `sensortask_${device}`,
            "--wiring-plan",
            path.join(REPO_ROOT, "build", "generated_src", `sensortask_${device}_wiring_plan.json`),
            "--device",
            device,
            "--host",
            HOST,
            "--port",
            String(PORT),
            "--fram-state-path",
            "", // in-memory only - see digital_twin/README.md's "FRAM persistence" section for this convention
            "--scd30-state-path",
            "", // same convention, "SCD30 persistence" section
        ],
        {
            cwd: REPO_ROOT,
            env: { ...process.env, MICROPYPATH: micropypath, TZ: "UTC" },
            // Both streams are drained: an undrained pipe blocks the child; the drained text is scanned for the memory markers.
            stdio: ["ignore", "pipe", "pipe"],
        },
    );
    // An unhandled ChildProcess 'error' event crashes the whole Node/Vitest process, skipping this
    // file's try/finally: the listener keeps the error for waitUntilServing() to name.
    proc.on("error", (err) => { spawnErrors.set(proc, err); });
    return proc;
}

/** @param {import("node:child_process").ChildProcess} proc */
async function stopTwin(proc) {
    if (proc.pid === undefined || proc.exitCode !== null || proc.signalCode !== null) {
        return; // never started (waitUntilServing() names its spawn error) or already gone
    }
    const exited = new Promise((resolve) => {
        proc.once("exit", resolve);
    });
    // SIGINT, not SIGTERM/kill('SIGTERM'): run_generic_integration.py's own graceful-shutdown path
    // (FRAM/SCD30 flush) only runs on KeyboardInterrupt - a plain SIGTERM would skip it, same
    // reasoning as scripts/_digital_twin_ci_suite.py's own _shutdown().
    proc.kill("SIGINT");
    // The SIGKILL fallback timer is cleared once the child is gone. A plain Promise.race leaves
    // the setTimeout pending, and a pending timer keeps Node's event loop alive - which showed up
    // as Vitest's "something prevents Vite server from exiting" on every live-twin run.
    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let killTimer;
    try {
        await Promise.race([
            exited,
            new Promise((resolve) => {
                killTimer = setTimeout(() => {
                    proc.kill("SIGKILL");
                    resolve(undefined);
                }, SHUTDOWN_TIMEOUT_MS);
            }),
        ]);
    } finally {
        clearTimeout(killTimer);
    }
    await exited; // a killed twin still holds the port until it has exited, and the next check needs it free
}

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
 * The command's verdict once its twins have stopped: an allocation-failure marker or a restart sign anywhere in a
 * twin's output fails it (SPECIFICATION.md Part I.4(e)), quoting the lines, even when the check itself passed.
 * @param {string} what the command, for the message
 * @param {ReturnType<typeof drainChildOutput>[]} outputs every twin the command started, in order
 * @param {unknown} failure what the check itself threw, or null
 * @param {boolean} drained whether every output stream closed, so the scans saw everything
 */
function twinVerdict(what, outputs, failure, drained) {
    const marked = outputs.flatMap((output) => output.markerLines());
    const reset = outputs.flatMap((output) => output.resetLines());
    const checkFailed = failure === null ? "" : `\n(the check itself also failed: ${failure instanceof Error ? failure.message : String(failure)})`;
    const cause = failure === null ? undefined : { cause: failure };
    if (marked.length > 0) {
        throw new Error(`${what}: the twin logged an allocation failure:\n${marked.join("\n")}${checkFailed}`, cause);
    }
    if (reset.length > 0) {
        throw new Error(`${what}: the twin reset itself, so the page talked to a device that was not running:\n${reset.join("\n")}${checkFailed}`, cause);
    }
    if (!drained) {
        throw new Error(`${what}: the twin's output did not close within ${SHUTDOWN_TIMEOUT_MS}ms of it stopping, so the allocation-failure scan is incomplete${checkFailed}`, cause);
    }
    if (failure !== null) {
        const message = failure instanceof Error ? failure.message : String(failure);
        throw new Error(`${what} failed: ${message}\n--- twin output ---\n${outputs.map((output) => output.text()).join("--- restarted twin ---\n")}`, cause);
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
 * @returns {Promise<{skipped: true, reason: string} | {skipped: false, titleHasSensorStation: boolean, deviceName: string, firstStatus: string | null, resubmitStatus: string | null}>}
 */
export async function runLiveBackendSmoke({ context }, device) {
    if (!existsSync(MICROPYTHON_BIN)) {
        return { skipped: true, reason: MISSING_INTERPRETER };
    }

    // Fresh state every run, mirroring scripts/_digital_twin_ci_suite.py's own "clean" step -
    // FRAM/SCD30 are already in-memory-only above; config/ is the one thing that still persists
    // to a fixed path by default (run_generic_integration.py exposes no --cfg-path flag).
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });

    await assertPortFree(device, "before starting");
    const proc = spawnTwin(device);
    const output = drainChildOutput(proc);

    let livePage;
    /** @type {{skipped: false, titleHasSensorStation: boolean, deviceName: string, firstStatus: string | null, resubmitStatus: string | null} | undefined} */
    let checked;
    /** @type {unknown} */
    let failure = null;
    try {
        await waitUntilServing(proc, READY_TIMEOUT_MS);
        const system = /** @type {{DebugLevel?: unknown}} */ (await (await fetch(`http://${HOST}:${PORT}/system`)).json());
        const field = definitionsOf(device).sections.flatMap((section) => section.groups).flatMap((group) => group.fields ?? []).find((candidate) => candidate.key === "DebugLevel");
        if (typeof system.DebugLevel !== "number" || typeof field?.max !== "number") {
            throw new Error(`GET /system answered DebugLevel ${JSON.stringify(system.DebugLevel)}, or the definitions name no DebugLevel bound`);
        }
        const value = system.DebugLevel < field.max ? system.DebugLevel + 1 : system.DebugLevel - 1;

        livePage = await context.newPage();
        const consoleMessages = [];
        livePage.on("console", (msg) => consoleMessages.push(`[console:${msg.type()}] ${msg.text()}`));
        livePage.on("pageerror", (err) => consoleMessages.push(`[pageerror] ${err.message}`));
        const gotoRes = await livePage.goto(`http://${HOST}:${PORT}/`);
        consoleMessages.push(`[goto] status=${gotoRes?.status()} url=${gotoRes?.url()}`);
        try {
            await livePage.waitForSelector('[data-section-key="system"]', { timeout: SECTION_WAIT_MS });
        } catch (err) {
            const html = await livePage.content();
            throw new Error(`${err instanceof Error ? err.message : String(err)}\n--- console ---\n${consoleMessages.join("\n")}\n--- html (first 2000 chars) ---\n${html.slice(0, 2000)}`, { cause: err });
        }

        const titleHasSensorStation = (await livePage.title()).includes("Sensor Station");
        const deviceName = (await livePage.locator("#device-name").textContent())?.trim() ?? "";

        // The nav is a slide-in drawer (SPECIFICATION.md Part H.4): its links take a click only once the
        // hamburger has opened it.
        await livePage.locator("#hamburger-button").click();
        await livePage.locator('[data-section-key="system"]').click();
        await livePage.locator('[data-field-key="DebugLevel"]').waitFor();
        const firstStatus = await applyDebugLevel(livePage, value);
        const resubmitStatus = await applyDebugLevel(livePage, value);

        checked = { skipped: false, titleHasSensorStation, deviceName, firstStatus, resubmitStatus };
    } catch (err) {
        failure = err;
    } finally {
        if (livePage) {
            livePage.removeAllListeners();
            await livePage.close().catch(() => { /* best-effort teardown - a page already gone is fine */ });
        }
        await stopTwin(proc);
    }
    twinVerdict(`live-backend smoke check for ${device}`, [output], failure, await output.closed(SHUTDOWN_TIMEOUT_MS));
    if (checked === undefined) {
        throw new Error(`live-backend smoke check for ${device} ended with no result`);
    }
    return checked;
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
 * A full connection ceiling of real-browser tabs against one live twin, all navigating at once: each load completes
 * or fails at the connection level within the page's own request cap, and every tab that did not load then loads
 * on one reload of its own (SPECIFICATION.md Part H.7).
 * @param {{context: import("playwright").BrowserContext}} ctx
 * @param {string} device a devices/<device>.toml stem; its own ceiling sizes the tab count
 * @returns {Promise<{skipped: true, reason: string} | {skipped: false, tabs: number, loadedFirstPass: number, loadedAfterRetry: number, failures: string[]}>}
 */
export async function runLiveBackendConcurrentTabs({ context }, device) {
    if (!existsSync(MICROPYTHON_BIN)) {
        return { skipped: true, reason: MISSING_INTERPRETER };
    }
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });

    const tabs = configuredMaxConnections(device);
    await assertPortFree(device, "before starting");
    const proc = spawnTwin(device);
    const output = drainChildOutput(proc);

    /** @type {import("playwright").Page[]} */
    const pages = [];
    /** @type {{skipped: false, tabs: number, loadedFirstPass: number, loadedAfterRetry: number, failures: string[]} | undefined} */
    let checked;
    /** @type {unknown} */
    let failure = null;
    try {
        await waitUntilServing(proc, READY_TIMEOUT_MS);
        for (let i = 0; i < tabs; i += 1) {
            // eslint-disable-next-line no-await-in-loop -- pages are CREATED sequentially and NAVIGATED together below; that is what makes the loads concurrent rather than the setup
            pages.push(await context.newPage());
        }
        const firstPass = await Promise.all(pages.map((page) => loadPage(page, OUTER_CAP_MS + 5000)));
        const failures = firstPass.flatMap((reason, index) => (reason === null ? [] : [`tab ${index + 1}: ${reason}`]));
        let loadedAfterRetry = firstPass.filter((reason) => reason === null).length;
        for (const [index, reason] of firstPass.entries()) {
            if (reason !== null) {
                // eslint-disable-next-line no-await-in-loop -- one reload at a time: recovery, not another burst
                const retry = await loadPage(/** @type {import("playwright").Page} */ (pages[index]), TAB_WAIT_MS);
                if (retry === null) {
                    loadedAfterRetry += 1;
                } else {
                    failures.push(`tab ${index + 1} on its reload: ${retry}`);
                }
            }
        }
        checked = { skipped: false, tabs, loadedFirstPass: firstPass.filter((reason) => reason === null).length, loadedAfterRetry, failures };
    } catch (err) {
        failure = err;
    } finally {
        await Promise.all(pages.map((page) => page.close().catch(() => { /* best-effort teardown - a page already gone is fine */ })));
        await stopTwin(proc);
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
 * @returns {Promise<{skipped: true, reason: string} | {skipped: false, bannerShown: boolean, recovered: boolean, reloaded: boolean}>}
 */
export async function runLiveBackendRestartRecovery({ context }, device) {
    if (!existsSync(MICROPYTHON_BIN)) {
        return { skipped: true, reason: MISSING_INTERPRETER };
    }
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });
    const defs = definitionsOf(device);
    const landingGet = defs.sections.find((section) => section.key === defs.landingSection)?.rest.get ?? "";
    const answered = (/** @type {import("playwright").Response} */ response) => response.url() === `http://${HOST}:${PORT}${landingGet}` && response.status() === 200;
    const banner = (/** @type {"true" | "false"} */ shown) => `#app-main .error-banner[data-shown="${shown}"]`;

    await assertPortFree(device, "before starting");
    const procs = [spawnTwin(device)];
    const outputs = [drainChildOutput(/** @type {import("node:child_process").ChildProcess} */ (procs[0]))];
    /** @type {import("playwright").Page | undefined} */
    let page;
    /** @type {{skipped: false, bannerShown: boolean, recovered: boolean, reloaded: boolean} | undefined} */
    let checked;
    /** @type {unknown} */
    let failure = null;
    try {
        await waitUntilServing(/** @type {import("node:child_process").ChildProcess} */ (procs[0]), READY_TIMEOUT_MS);
        page = await context.newPage();
        const firstPoll = settledLater(page.waitForResponse(answered, { timeout: SECTION_WAIT_MS }));
        await page.goto(`http://${HOST}:${PORT}/`);
        await firstPoll;
        await page.evaluate(() => {
            /** @type {Record<string, unknown>} */ (/** @type {unknown} */ (globalThis)).liveRestartMarker = "kept";
        });
        const urlBefore = page.url();

        await stopTwin(/** @type {import("node:child_process").ChildProcess} */ (procs[0]));
        await assertPortFree(device, "after stopping");
        const bannerShown = await page.locator(banner("true")).waitFor({ timeout: SECTION_WAIT_MS }).then(() => true, () => false);

        const recoveredPoll = settledLater(page.waitForResponse(answered, { timeout: READY_TIMEOUT_MS + POLL_BACKOFF_MAX_MS }));
        const restarted = spawnTwin(device);
        procs.push(restarted);
        outputs.push(drainChildOutput(restarted));
        await waitUntilServing(restarted, READY_TIMEOUT_MS);
        // A hidden banner is display: none, so it is waited for as attached, never as visible.
        const recovered = await recoveredPoll.then(() => page?.locator(banner("false")).waitFor({ state: "attached", timeout: SECTION_WAIT_MS })).then(() => true, () => false);
        const marker = await page.evaluate(() => /** @type {Record<string, unknown>} */ (/** @type {unknown} */ (globalThis)).liveRestartMarker);
        checked = { skipped: false, bannerShown, recovered, reloaded: page.url() !== urlBefore || marker !== "kept" };
    } catch (err) {
        failure = err;
    } finally {
        if (page) {
            await page.close().catch(() => { /* best-effort teardown - a page already gone is fine */ });
        }
        await Promise.all(procs.map((proc) => stopTwin(proc)));
    }
    const drained = await Promise.all(outputs.map((output) => output.closed(SHUTDOWN_TIMEOUT_MS)));
    twinVerdict(`live-backend restart-recovery check for ${device}`, outputs, failure, drained.every(Boolean));
    if (checked === undefined) {
        throw new Error(`live-backend restart-recovery check for ${device} ended with no result`);
    }
    return checked;
}
