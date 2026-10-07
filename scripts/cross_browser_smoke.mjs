// Standalone (non-Vitest) cross-browser smoke check: boots the twin of every device of devices/*.toml in
// turn and drives that device's real site through WebKitGTK, Firefox, Edge and Playwright's Chromium.
// Run: `node scripts/cross_browser_smoke.mjs`. See SPECIFICATION.md Part H.7 ("Cross-browser coverage").

import { spawn } from "node:child_process";
import { existsSync, readdirSync, readFileSync, rmSync } from "node:fs";
import net from "node:net";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { drainChildOutput } from "../tests_js/_memory_markers.js";
import { pickProbe, webDriverFailure } from "./_cross_browser_probe.mjs";

/** @typedef {import("./_cross_browser_probe.mjs").Probe} Probe */
/** @typedef {import("./_cross_browser_probe.mjs").ProbeDefinitions} ProbeDefinitions */

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const TOOLCHAIN_DIR = process.env.PICO_TOOLCHAIN_DIR || path.join(homedir(), "pico-toolchain");
const MICROPYTHON_BIN = path.join(TOOLCHAIN_DIR, "micropython", "ports", "unix", "build-standard", "micropython");
// Every device's module, wiring plan and definitions come from build/generated_src/ and its site from
// build/generated_html/<device>/ (SPECIFICATION.md Part L.2); `npm run build:site` writes both.
/** @param {string} device */
function micropythonPath(device) {
    return `build/generated_src:src:digital_twin:ext:build/generated_html/${device}:.frozen`;
}
const HOST = "127.0.0.1";
// Distinct from every other fixed port this repo already uses for a twin/integration run - see
// tests_js/_live_twin_command.js's own comment for the full enumeration this continues (19481,
// 19482 already taken by that file and _live_matrix_command.js).
const PORT = 19420;
// Every browser loads the site through a counting proxy on the next port up, never the twin directly.
const PROXY_PORT = 19421;
const TWIN_URL = `http://${HOST}:${PORT}/`;
const SITE_URL = `http://${HOST}:${PROXY_PORT}/`;
// @tunable l0.live_twin_ready_timeout_ms = 20000
const READY_TIMEOUT_MS = 20000;
// @tunable l0.live_twin_shutdown_timeout_ms = 15000
const SHUTDOWN_TIMEOUT_MS = 15000;
// @tunable l0.smoke_h1_wait_ms = 10000
const H1_WAIT_MS = 10000;
// The connections one page load may open, counted per engine at the proxy (SPECIFICATION.md H.7):
// a higher count, or none at all, fails that engine's check.
// @tunable web.connections_per_page_load = 2
const CONNECTIONS_PER_PAGE_LOAD = 2;

const CROSS_BROWSER_DIR = process.env.CROSS_BROWSER_TOOLCHAIN_DIR || path.join(homedir(), "cross-browser-toolchain");
const FIREFOX_BIN = path.join(CROSS_BROWSER_DIR, "mamba_root", "envs", "ff", "bin", "firefox");
const GECKODRIVER_BIN = path.join(CROSS_BROWSER_DIR, "mamba_root", "envs", "ff", "bin", "geckodriver");
const WEBKIT_DRIVER_BIN = "/usr/bin/WebKitWebDriver";
const EDGE_BIN = "/usr/bin/microsoft-edge-stable";
const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium"; // same dev-sandbox path vitest.config.js already special-cases

const USAGE = `Usage: node scripts/cross_browser_smoke.mjs [-h | --help]
Boots the twin of every device of devices/*.toml in turn and drives its site through every installed
engine (WebKitGTK, Firefox, Edge, Playwright's Chromium) at two viewports (SPECIFICATION.md H.7).
Environment:
  PICO_TOOLCHAIN_DIR           the MicroPython toolchain (default: ~/pico-toolchain)
  CROSS_BROWSER_TOOLCHAIN_DIR  Firefox and geckodriver (default: ~/cross-browser-toolchain)
Exit codes: 0 every check passed; 1 a check failed, a twin logged an allocation failure, or nothing ran; 2 a usage error.`;

// Loaded only after the arguments are read, so --help answers on a checkout with no node_modules.
/** @type {typeof import("playwright")} */
let playwright;

const WEBKIT_DRIVER_PORT = 4444;
const GECKODRIVER_PORT = 4445;

// One probe well above the site's 640px breakpoint and one well below. WebKit and Firefox have
// no device-emulation API over plain WebDriver, so these are real window resizes - no touch
// synthesis, no mobile UA; only Chromium/Edge get Playwright's fuller `devices` emulation.

// Both headless engines also enforce a minimum window width - requesting 393px comes back
// around 447-500px - so MOBILE_VIEWPORT is a request, not a guarantee, and the check below
// asserts only that the result is still under the breakpoint.
const DESKTOP_VIEWPORT = { width: 1280, height: 900 };
const MOBILE_VIEWPORT = { width: 393, height: 852 };
const RESPONSIVE_BREAKPOINT_PX = 640;

/** The derived device set: sorted devices/*.toml stems minus the zz_test_ fixtures, as tests_scripts/_devices.py. */
function derivedDevices() {
    return readdirSync(path.join(REPO_ROOT, "devices"))
        .filter((name) => name.endsWith(".toml") && !name.startsWith("zz_test_"))
        .map((name) => name.slice(0, -".toml".length))
        .sort();
}

/** @param {string} device */
function definitionsPath(device) {
    return path.join(REPO_ROOT, "build", "generated_src", "definitions", `${device}.json`);
}

/** @param {string} device */
function sitePath(device) {
    return path.join(REPO_ROOT, "build", "generated_html", device, "frozen_html.py");
}

/** @param {number} ms */
function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

/** @param {string} url @param {number} timeoutMs */
async function waitUntilServing(url, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        try {
            // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
            const res = await fetch(url);
            if (res.status === 200 || res.status === 404) {
                return; // 404 still proves something is listening and answering HTTP (WebDriver root)
            }
        } catch {
            // Not up yet - keep polling.
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        await sleep(250);
    }
    throw new Error(`nothing answered ${url} within ${timeoutMs}ms`);
}

/** @typedef {{reset: () => void, count: () => number, close: () => Promise<void>}} CountingProxy */

/** A TCP proxy in front of the twin that counts every connection a browser opens through it. @returns {Promise<CountingProxy>} */
function startCountingProxy() {
    let opened = 0;
    /** @type {Set<net.Socket>} */
    const sockets = new Set();
    const server = net.createServer((client) => {
        opened += 1;
        const upstream = net.connect(PORT, HOST);
        const close = () => {
            client.destroy();
            upstream.destroy();
            sockets.delete(client);
            sockets.delete(upstream);
        };
        sockets.add(client);
        sockets.add(upstream);
        for (const socket of [client, upstream]) {
            socket.on("error", close);
            socket.on("close", close);
        }
        client.pipe(upstream);
        upstream.pipe(client);
    });
    return new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(PROXY_PORT, HOST, () => {
            resolve({
                reset: () => {
                    opened = 0;
                },
                count: () => opened,
                close: () => new Promise((done) => {
                    for (const socket of sockets) {
                        socket.destroy();
                    }
                    server.close(() => done());
                }),
            });
        });
    });
}

/** Fails a check whose page load opened more connections than registered, or none through the proxy. @param {string} device @param {string} engine @param {CountingProxy} proxy */
function checkPageLoadConnections(device, engine, proxy) {
    const opened = proxy.count();
    console.log(`connections per page load (${device} ${engine}): ${opened}`);
    if (opened === 0 || opened > CONNECTIONS_PER_PAGE_LOAD) {
        throw new Error(`the page load opened ${opened} connection(s) through the proxy; 1 to ${CONNECTIONS_PER_PAGE_LOAD} are registered for it`);
    }
}

// Every spawned child is tracked from creation until stopProcess() or a signal handler reaps it:
// Node's synchronous crash on an unhandled ChildProcess 'error' happens outside every try/catch
// here, skipping the cleanup and leaking whatever else runs. Part H.7 has the overall design.
/** @type {Set<import("node:child_process").ChildProcess>} */
const activeProcesses = new Set();

/** @param {import("node:child_process").ChildProcess} proc @param {string} label */
function trackProcess(proc, label) {
    activeProcesses.add(proc);
    proc.on("error", (err) => {
        console.error(`${label} process failed to spawn/run: ${err.message}`);
    });
    return proc;
}

/** @param {string} device */
function spawnTwin(device) {
    return trackProcess(
        spawn(
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
                "",
                "--scd30-state-path",
                "",
            ],
            // Both streams are drained: an undrained pipe blocks the child; the drained text is scanned for the memory markers.
            { cwd: REPO_ROOT, env: { ...process.env, MICROPYPATH: micropythonPath(device), TZ: "UTC" }, stdio: ["ignore", "pipe", "pipe"] },
        ),
        `${device} twin`,
    );
}

/** @param {import("node:child_process").ChildProcess} proc @param {NodeJS.Signals} [signal] */
async function stopProcess(proc, signal = "SIGINT") {
    activeProcesses.delete(proc);
    if (proc.exitCode !== null || proc.signalCode !== null) {
        return;
    }
    proc.kill(signal);
    await Promise.race([
        new Promise((resolve) => {
            proc.once("exit", resolve);
        }),
        sleep(SHUTDOWN_TIMEOUT_MS).then(() => proc.kill("SIGKILL")),
    ]);
}

// Both drivers need a real X display even headless - confirmed for WebKitGTK, and geckodriver
// is wrapped the same way for consistency.

// Xvfb is spawned directly rather than through `xvfb-run`, which is a layer this file cannot
// reliably tear down: an earlier version sent SIGINT to the wrapper's PID and left both Xvfb
// and the driver running, found with pgrep after a run. Spawning it here gives a real handle.
let nextDisplayNumber = 90;

/** @returns {{display: string, xvfbProc: import("node:child_process").ChildProcess}} */
function spawnVirtualDisplay() {
    nextDisplayNumber += 1;
    const display = `:${nextDisplayNumber}`;
    const xvfbProc = trackProcess(spawn("Xvfb", [display, "-screen", "0", "1280x1024x24", "-nolisten", "tcp"], { stdio: ["ignore", "ignore", "pipe"] }), "Xvfb");
    return { display, xvfbProc };
}

/** @param {string} display @param {number} timeoutMs */
async function waitForVirtualDisplay(display, timeoutMs) {
    const lockFile = `/tmp/.X${display.slice(1)}-lock`;
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        if (existsSync(lockFile)) {
            return;
        }
        // eslint-disable-next-line no-await-in-loop -- sequential polling
        await sleep(100);
    }
    throw new Error(`Xvfb never created ${lockFile} within ${timeoutMs}ms`);
}

// --- Minimal raw W3C WebDriver HTTP client - used for WebKitWebDriver and geckodriver, neither of
// which Playwright can drive directly (see this file's own header comment). ---

/** @param {string} base @param {object} capabilities @returns {Promise<string>} */
async function wdCreateSession(base, capabilities) {
    const res = await fetch(`${base}/session`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ capabilities: { alwaysMatch: capabilities } }) });
    const body = /** @type {{value?: {sessionId?: string}}} */ (await res.json());
    if (body.value?.sessionId === undefined) {
        throw new Error(`WebDriver session creation failed: ${JSON.stringify(body)}`);
    }
    return body.value.sessionId;
}

/** @param {string} base @param {string} sid */
async function wdDeleteSession(base, sid) {
    await fetch(`${base}/session/${sid}`, { method: "DELETE" }).catch(() => { /* teardown is best-effort - a dead driver is not a smoke-check failure */ });
}

/** @param {string} base @param {string} sid @param {string} url */
async function wdNavigate(base, sid, url) {
    await wdCommand(`${base}/session/${sid}/url`, { url }, "navigation");
}

/** @param {string} base @param {string} sid @param {number} width @param {number} height */
async function wdSetWindowRect(base, sid, width, height) {
    await wdCommand(`${base}/session/${sid}/window/rect`, { width, height }, "window resize");
}

/** @param {string} base @param {string} sid @param {string} script @returns {Promise<unknown>} */
async function wdExecute(base, sid, script) {
    return await wdCommand(`${base}/session/${sid}/execute/sync`, { script, args: [] }, "script execution");
}

/** @param {string} url @param {object} payload @param {string} what @returns {Promise<unknown>} */
async function wdCommand(url, payload, what) {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const body = /** @type {{value?: unknown}} */ (await res.json().catch(() => ({})));
    const failure = webDriverFailure(res.status, body);
    if (failure !== null) {
        throw new Error(`WebDriver ${what} failed: ${failure}`);
    }
    return body.value;
}

// Every selector is scoped by the probe's card: a page can carry two instances of one driver, whose
// cards share field keys.
/** @param {Probe} probe @param {string} attribute */
function probeSelector(probe, attribute) {
    return `[data-group-key="${probe.groupKey}"] [${attribute}="${probe.fieldKey}"]`;
}

// The nav click runs alone, not folded into the field fill: renderSection() swaps the section in
// asynchronously, so a script that clicks and immediately queries can find the field null on both
// engines. Its own script/poll pair, since execute/sync cannot await an in-page Promise anyway.
/** @param {Probe} probe */
function navToProbeSectionScript(probe) {
    return `
        document.getElementById("hamburger-button").click();
        const link = [...document.querySelectorAll("[data-section-key]")].find((a) => a.dataset.sectionKey === "${probe.sectionKey}");
        link.click();
    `;
}

/** @param {Probe} probe */
function fieldPresentScript(probe) {
    return `return document.querySelector('${probeSelector(probe, "data-field-key")}') !== null;`;
}

/** @param {Probe} probe @param {number} probeValue */
function fillAndApplyScript(probe, probeValue) {
    return `
        const input = document.querySelector('${probeSelector(probe, "data-field-key")}');
        input.value = "${probeValue}";
        input.dispatchEvent(new Event("input", { bubbles: true }));
        let el = input, card = null;
        while (el) {
            if (el.querySelector && el.querySelector(".apply-button")) { card = el; break; }
            el = el.parentElement;
        }
        card.querySelector(".apply-button").click();
        return { title: document.title, innerWidth: window.innerWidth };
    `;
}

/** @param {Probe} probe */
function readAppliedResultScript(probe) {
    return `
        const w = document.querySelector('${probeSelector(probe, "data-field-wrapper-key")}');
        const c = document.querySelector('${probeSelector(probe, "data-current-value-for")}');
        return { applyStatus: w ? w.dataset.applyStatus : null, caption: c ? c.textContent : null };
    `;
}

/**
 * Polls `readFn` (a zero-arg async function returning a plain value) until `isReady` accepts its
 * result, or throws after `timeoutMs`. Shared by both the "has the target field rendered yet"
 * wait and the "has the apply status attribute appeared yet" wait below.
 * @template T
 * @param {() => Promise<T>} readFn
 * @param {(value: T) => boolean} isReady
 * @param {number} timeoutMs
 * @param {string} timeoutMessage
 * @returns {Promise<T>}
 */
async function pollUntil(readFn, isReady, timeoutMs, timeoutMessage) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
        const value = await readFn();
        if (isReady(value)) {
            return value;
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        await sleep(200);
    }
    throw new Error(timeoutMessage);
}

/**
 * @param {{device: string, engine: string, viewport: "desktop" | "mobile", probe: Probe, probeValue: number, proxy: CountingProxy, driverProcessFactory: (display: string) => import("node:child_process").ChildProcess, driverBase: string, driverPort: number, capabilities: object}} opts
 */
async function runViaRawWebDriver({ device, engine, viewport, probe, probeValue, proxy, driverProcessFactory, driverBase, driverPort, capabilities }) {
    const label = `${device} ${engine} (${viewport})`;
    const { display, xvfbProc } = spawnVirtualDisplay();
    let driverProc;
    let driverStderr = "";
    /** @type {string | undefined} */
    let sid;
    try {
        await waitForVirtualDisplay(display, READY_TIMEOUT_MS);
        driverProc = driverProcessFactory(display);
        driverProc.stderr?.on("data", (chunk) => {
            driverStderr += chunk.toString();
        });
        await waitUntilServing(`http://127.0.0.1:${driverPort}/status`, READY_TIMEOUT_MS);
        sid = await wdCreateSession(driverBase, capabilities);

        const target = viewport === "mobile" ? MOBILE_VIEWPORT : DESKTOP_VIEWPORT;
        await wdSetWindowRect(driverBase, sid, target.width, target.height);
        proxy.reset();
        await wdNavigate(driverBase, sid, SITE_URL);
        checkPageLoadConnections(device, engine, proxy);
        const readyTitle = await pollUntil(
            () => /** @type {Promise<string>} */ (wdExecute(driverBase, /** @type {string} */ (sid), "return document.title;")),
            (t) => typeof t === "string" && t.includes("Sensor Station"),
            READY_TIMEOUT_MS,
            "page never reached \"Sensor Station\" title",
        );
        if (!readyTitle.includes("Sensor Station")) {
            throw new Error(`unexpected page title: ${readyTitle}`);
        }

        await wdExecute(driverBase, sid, navToProbeSectionScript(probe));
        await pollUntil(() => wdExecute(driverBase, /** @type {string} */ (sid), fieldPresentScript(probe)), (present) => present === true, 5000, `${probe.groupKey}.${probe.fieldKey} field never rendered after navigating to ${probe.sectionKey}`);

        const fillResult = /** @type {{title: string, innerWidth: number}} */ (await wdExecute(driverBase, sid, fillAndApplyScript(probe, probeValue)));
        if (viewport === "mobile" && fillResult.innerWidth >= RESPONSIVE_BREAKPOINT_PX) {
            throw new Error(`requested a mobile viewport but window.innerWidth was ${fillResult.innerWidth}px (>= ${RESPONSIVE_BREAKPOINT_PX}px breakpoint)`);
        }

        // Waits for BOTH data-apply-status, set as the PUT resolves, and the caption, which a
        // separate slightly later GET updates. Polling only the attribute raced ahead of the
        // caption during this file's own development, reading the previous check's stale value.
        const expectedCaption = `Current value: ${probeValue}`;
        const applied = await pollUntil(
            () => /** @type {Promise<{applyStatus: string | null, caption: string | null}>} */ (wdExecute(driverBase, /** @type {string} */ (sid), readAppliedResultScript(probe))),
            (r) => r.applyStatus !== null && r.applyStatus !== undefined && r.caption === expectedCaption,
            10000,
            `apply status/caption never settled within 10s (last seen: ${JSON.stringify(await wdExecute(driverBase, /** @type {string} */ (sid), readAppliedResultScript(probe)))})`,
        );
        if (applied.applyStatus !== "valid") {
            throw new Error(`expected applyStatus "valid", got ${JSON.stringify(applied.applyStatus)}`);
        }
        return { label, ok: true };
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return { label, ok: false, detail: `${message}${driverStderr ? `\n--- driver stderr ---\n${driverStderr}` : ""}` };
    } finally {
        if (sid) {
            await wdDeleteSession(driverBase, sid);
        }
        if (driverProc) {
            await stopProcess(driverProc);
        }
        // SIGKILL, not SIGINT: Xvfb does not reliably exit on SIGINT within SHUTDOWN_TIMEOUT_MS
        // once a driver has connected to it, and it has no graceful-shutdown state worth waiting
        // for - unlike the twin's own FRAM/SCD30 flush, stopProcess()'s other caller.
        await stopProcess(xvfbProc, "SIGKILL");
    }
}

/** @param {string} device @param {"desktop" | "mobile"} viewport @param {Probe} probe @param {number} probeValue @param {CountingProxy} proxy */
function runWebKit(device, viewport, probe, probeValue, proxy) {
    return runViaRawWebDriver({
        device,
        engine: "WebKit",
        viewport,
        probe,
        probeValue,
        proxy,
        driverProcessFactory: (display) => trackProcess(spawn(WEBKIT_DRIVER_BIN, [`--port=${WEBKIT_DRIVER_PORT}`], { env: { ...process.env, DISPLAY: display }, stdio: ["ignore", "ignore", "pipe"] }), "WebKitWebDriver"),
        driverBase: `http://127.0.0.1:${WEBKIT_DRIVER_PORT}`,
        driverPort: WEBKIT_DRIVER_PORT,
        capabilities: {},
    });
}

/** @param {string} device @param {"desktop" | "mobile"} viewport @param {Probe} probe @param {number} probeValue @param {CountingProxy} proxy */
function runFirefox(device, viewport, probe, probeValue, proxy) {
    return runViaRawWebDriver({
        device,
        engine: "Firefox",
        viewport,
        probe,
        probeValue,
        proxy,
        // Given a real DISPLAY, `-headless` Firefox still uses it rather than requiring it be
        // unset - confirmed directly (harmless either way; kept for consistency with the WebKit
        // path above rather than special-casing Firefox's own process/env setup).
        driverProcessFactory: (display) => trackProcess(spawn(GECKODRIVER_BIN, ["--port", String(GECKODRIVER_PORT), "--binary", FIREFOX_BIN], { env: { ...process.env, DISPLAY: display }, stdio: ["ignore", "ignore", "pipe"] }), "geckodriver"),
        driverBase: `http://127.0.0.1:${GECKODRIVER_PORT}`,
        driverPort: GECKODRIVER_PORT,
        capabilities: { "moz:firefoxOptions": { args: ["-headless"] } },
    });
}

/**
 * Polls until `wrapperLocator`'s `data-apply-status` AND `captionLocator`'s text both settle,
 * mirroring pollUntil() above. Both are needed: the attribute is set as the PUT resolves, while
 * the caption waits on a separate later GET, so polling the attribute alone read stale text.
 * @param {import("playwright").Locator} wrapperLocator
 * @param {import("playwright").Locator} captionLocator
 * @param {string} expectedCaption
 * @param {number} timeoutMs
 */
async function pollForAppliedResult(wrapperLocator, captionLocator, expectedCaption, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    let lastStatus = null;
    let lastCaption = null;
    while (Date.now() < deadline) {
        // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
        [lastStatus, lastCaption] = await Promise.all([wrapperLocator.getAttribute("data-apply-status"), captionLocator.textContent()]);
        if (lastStatus !== null && lastCaption === expectedCaption) {
            return lastStatus;
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        await sleep(200);
    }
    throw new Error(`apply status/caption never settled within ${timeoutMs}ms (last seen: status=${JSON.stringify(lastStatus)} caption=${JSON.stringify(lastCaption)})`);
}

/** @param {"chromium" | "edge"} which @param {string} device @param {"desktop" | "mobile"} viewport @param {Probe} probe @param {number} probeValue @param {CountingProxy} proxy */
async function runChromiumFamily(which, device, viewport, probe, probeValue, proxy) {
    const engine = which === "edge" ? "Edge" : "Chromium";
    const label = `${device} ${engine} (${viewport})`;
    /** @type {string | undefined} */
    let executablePath;
    if (which === "edge") {
        executablePath = EDGE_BIN;
    } else if (existsSync(SANDBOX_CHROMIUM)) {
        executablePath = SANDBOX_CHROMIUM;
    }
    let browser;
    try {
        browser = await playwright.chromium.launch(executablePath ? { executablePath } : {});
        const context = await browser.newContext(viewport === "mobile" ? { ...playwright.devices["iPhone 15"] } : {});
        const page = await context.newPage();
        proxy.reset();
        await page.goto(SITE_URL);
        checkPageLoadConnections(device, engine, proxy);
        await page.waitForSelector("h1", { timeout: H1_WAIT_MS });

        const clickOrTap = viewport === "mobile" ? "tap" : "click";
        await page.locator("#hamburger-button")[clickOrTap]();
        await page.locator(`[data-section-key="${probe.sectionKey}"]`).first()[clickOrTap]();
        const input = page.locator(probeSelector(probe, "data-field-key"));
        await input.waitFor();

        await input.fill(String(probeValue));
        const card = input.locator("xpath=ancestor::*[.//button[contains(@class,'apply-button')]][1]");
        await card.locator(".apply-button")[clickOrTap]();

        const wrapper = page.locator(probeSelector(probe, "data-field-wrapper-key"));
        const caption = page.locator(probeSelector(probe, "data-current-value-for"));
        const applyStatus = await pollForAppliedResult(wrapper, caption, `Current value: ${probeValue}`, 10000);
        if (applyStatus !== "valid") {
            throw new Error(`expected applyStatus "valid", got ${JSON.stringify(applyStatus)}`);
        }
        return { label, ok: true };
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return { label, ok: false, detail: message };
    } finally {
        await browser?.close().catch(() => { /* teardown is best-effort - a dead browser is not a smoke-check failure */ });
    }
}

// A local Ctrl-C or SIGTERM would otherwise skip every try/finally below, Node terminating
// immediately on both, orphaning whatever is in activeProcesses. Harmless in CI, where the VM
// is reclaimed anyway, and a real leak for local development.
for (const sig of /** @type {const} */ (["SIGINT", "SIGTERM"])) {
    process.on(sig, () => {
        console.error(`\nReceived ${sig} - killing ${activeProcesses.size} still-running process(es) before exit.`);
        for (const proc of activeProcesses) {
            proc.kill("SIGKILL");
        }
        process.exit(1);
    });
}

/**
 * Boots one device's twin and runs every available (engine, viewport) check against it.
 * @param {string} device
 * @param {Probe} probe
 * @param {{name: string, run: (device: string, viewport: "desktop" | "mobile", probe: Probe, probeValue: number, proxy: CountingProxy) => Promise<{label: string, ok: boolean, detail?: string}>}[]} engines
 * @param {{value: number}} counter
 * @param {{label: string, ok: boolean, detail?: string}[]} results
 */
async function smokeDevice(device, probe, engines, counter, results) {
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });
    const twin = spawnTwin(device);
    const output = drainChildOutput(twin);
    let failed = false;
    /** @type {CountingProxy | undefined} */
    let proxy;
    try {
        await waitUntilServing(TWIN_URL, READY_TIMEOUT_MS);
        proxy = await startCountingProxy();
        for (const engine of engines) {
            for (const viewport of /** @type {const} */ (["desktop", "mobile"])) {
                // One counter across every device and check, so no two checks against a twin ever
                // write the same value and mistake each other's write for their own.
                const probeValue = probe.min + 1 + (counter.value % (probe.max - probe.min - 1));
                counter.value += 1;
                // eslint-disable-next-line no-await-in-loop -- deliberate: one browser/engine at a time
                const result = await engine.run(device, viewport, probe, probeValue, proxy);
                results.push(result);
                console.log(`${result.ok ? "PASS" : "FAIL"} ${result.label}`);
                if (!result.ok) {
                    failed = true;
                    console.error(result.detail);
                }
            }
        }
    } catch (err) {
        failed = true;
        const message = err instanceof Error ? err.message : String(err);
        results.push({ label: `${device} twin`, ok: false, detail: message });
        console.error(`FAIL ${device} twin: ${message}`);
    } finally {
        await proxy?.close();
        await stopProcess(twin);
    }
    // The memory gate (SPECIFICATION.md Part I.4(e)): a marker fails the device even when every check passed.
    const drained = await output.closed(SHUTDOWN_TIMEOUT_MS);
    const marked = output.markerLines();
    if (marked.length > 0 || !drained) {
        failed = true;
        const detail = marked.length > 0 ? `logged an allocation failure:\n${marked.join("\n")}` : `output did not close within ${SHUTDOWN_TIMEOUT_MS}ms of it stopping, so the allocation-failure scan is incomplete`;
        results.push({ label: `${device} twin`, ok: false, detail });
        console.error(`FAIL ${device} twin: ${detail}`);
    }
    if (failed) {
        console.error(`\n--- ${device} twin output ---\n${output.text()}`);
    }
}

async function main() {
    const args = process.argv.slice(2);
    if (args.includes("-h") || args.includes("--help")) {
        console.log(USAGE);
        process.exit(0);
    }
    if (args.length > 0) {
        console.error(`error: unknown argument ${JSON.stringify(args[0])}\n${USAGE}`);
        process.exit(2);
    }
    playwright = await import("playwright");
    if (!existsSync(MICROPYTHON_BIN)) {
        console.error(`MicroPython Unix port not built at ${MICROPYTHON_BIN} - run 'uv run toolchain/setup_toolchain.py setup' first.`);
        process.exit(1);
    }

    // Every device's probe is picked before any twin boots, so a missing build or a device with no
    // probe-able field fails the run at once, naming the device.
    /** @type {{device: string, probe: Probe}[]} */
    const plan = [];
    for (const device of derivedDevices()) {
        if (!existsSync(definitionsPath(device)) || !existsSync(sitePath(device))) {
            console.error(`${device}: no generated definitions or site under build/ - run 'npm run build:site' first.`);
            process.exit(1);
        }
        plan.push({ device, probe: pickProbe(/** @type {ProbeDefinitions} */ (JSON.parse(readFileSync(definitionsPath(device), "utf8")))) });
    }

    /** @type {{name: string, available: boolean, run: (device: string, viewport: "desktop" | "mobile", probe: Probe, probeValue: number, proxy: CountingProxy) => Promise<{label: string, ok: boolean, detail?: string}>}[]} */
    const engines = [
        { name: "WebKit", available: existsSync(WEBKIT_DRIVER_BIN), run: runWebKit },
        { name: "Firefox", available: existsSync(FIREFOX_BIN) && existsSync(GECKODRIVER_BIN), run: runFirefox },
        { name: "Edge", available: existsSync(EDGE_BIN), run: (device, viewport, probe, probeValue, proxy) => runChromiumFamily("edge", device, viewport, probe, probeValue, proxy) },
        { name: "Chromium", available: true, run: (device, viewport, probe, probeValue, proxy) => runChromiumFamily("chromium", device, viewport, probe, probeValue, proxy) },
    ];
    for (const engine of engines.filter((e) => !e.available)) {
        console.warn(`SKIP ${engine.name}: binary not found (run scripts/setup_cross_browser_toolchain.sh)`);
    }
    const available = engines.filter((e) => e.available);

    /** @type {{label: string, ok: boolean, detail?: string}[]} */
    const results = [];
    const counter = { value: 0 };
    for (const { device, probe } of plan) {
        console.log(`\n${device}: probing ${probe.sectionKey} / ${probe.groupKey} / ${probe.fieldKey}`);
        // eslint-disable-next-line no-await-in-loop -- one twin at a time: every twin binds the one PORT
        await smokeDevice(device, probe, available, counter, results);
    }

    const ran = results.length;
    const failed = results.filter((r) => !r.ok).length;
    console.log(`\n${ran - failed}/${ran} cross-browser smoke checks passed.`);
    if (ran === 0) {
        console.error("No device or no engine was available - nothing was actually checked.");
        process.exit(1);
    }
    if (failed > 0) {
        process.exit(1);
    }
}

await main();
