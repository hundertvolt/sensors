// Standalone (non-Vitest) cross-browser smoke check: boots the real digital twin, then drives the
// real production website through three engines Vitest's own Playwright-only browser mode can't
// reach - WebKitGTK (real WebKit), real Firefox (Gecko), and real Microsoft Edge (Blink, but a
// genuinely different Chromium-family build/UA than the Playwright Chromium the rest of tests_js/
// already covers) - plus Playwright's own Chromium, included here too so every engine goes through
// the exact same check. Each engine is driven at both a desktop-sized and a mobile-sized (iPhone-
// ish) viewport: nav to the live site -> open the nav drawer -> go to Sensors -> edit one field ->
// Apply -> confirm the real backend validated it and the UI reflects it. See WEBSITE_PLAN.md §7
// ("Cross-browser coverage") for why this exists and the "Coverage depth"/"Test architecture"
// decisions behind its deliberately narrow scope (one field, not the full PUT matrix; raw WebDriver
// HTTP, not a second Vitest browser provider).
//
// WebKit/Firefox are driven via their own real W3C WebDriver servers (WebKitWebDriver/
// geckodriver) over plain HTTP - Playwright itself can only automate Chromium-family browsers
// (attaching to any real installed build via `executablePath`) plus its own specially patched
// Firefox/WebKit builds, which this project's network policy can't download (see WEBSITE_PLAN.md
// §7). Edge is Chromium-family, so it's driven the same way the rest of tests_js/ already drives
// Chromium: Playwright's own `chromium.launch({executablePath})`.
//
// Preconditions this script assumes are already met (same as tests_js/_live_twin_command.js):
// the MicroPython Unix port is built, and `scripts/build_website.sh wozi` has already produced
// frozen_modules/frozen_html.py. scripts/setup_cross_browser_toolchain.sh installs the three
// browser engines themselves. Any engine whose binary isn't found is skipped with a clear message
// (not a hard failure) - CI's web-cross-browser-smoke job always installs all three via that
// script, so a skip there would itself be the real bug; a local run without them just gets partial
// coverage.
//
// Run: node scripts/cross_browser_smoke.mjs

import { spawn } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, devices } from "playwright";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const TOOLCHAIN_DIR = process.env.PICO_TOOLCHAIN_DIR || path.join(homedir(), "pico-toolchain");
const MICROPYTHON_BIN = path.join(TOOLCHAIN_DIR, "micropython", "ports", "unix", "build-standard", "micropython");
const MICROPYPATH = "src:digital_twin:ext:frozen_modules:.frozen";
const HOST = "127.0.0.1";
// Distinct from every other fixed port this repo already uses for a twin/integration run - see
// tests_js/_live_twin_command.js's own comment for the full enumeration this continues (19411,
// 19412 already taken by that file and _live_matrix_command.js).
const PORT = 19420;
const TWIN_URL = `http://${HOST}:${PORT}/`;
const READY_TIMEOUT_MS = 20000;
const SHUTDOWN_TIMEOUT_MS = 15000;

const CROSS_BROWSER_DIR = process.env.CROSS_BROWSER_TOOLCHAIN_DIR || path.join(homedir(), "cross-browser-toolchain");
const FIREFOX_BIN = path.join(CROSS_BROWSER_DIR, "mamba_root", "envs", "ff", "bin", "firefox");
const GECKODRIVER_BIN = path.join(CROSS_BROWSER_DIR, "mamba_root", "envs", "ff", "bin", "geckodriver");
const WEBKIT_DRIVER_BIN = "/usr/bin/WebKitWebDriver";
const EDGE_BIN = "/usr/bin/microsoft-edge-stable";
const SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium"; // same dev-sandbox path vitest.config.js already special-cases

const WEBKIT_DRIVER_PORT = 4444;
const GECKODRIVER_PORT = 4445;

// Desktop-sized probe (well above the site's own 640px responsive breakpoint - html/style.css) and
// a mobile-ish one (well below it). WebKit/Firefox have no device-emulation API over plain
// WebDriver, so these are real window resizes, not true device emulation (no touch synthesis,
// no mobile UA) - Playwright's own `devices` presets give Chromium/Edge the fuller emulation
// (see runChromiumFamily() below). Both headless WebKit and headless Firefox enforce their own
// minimum window width below a certain point (confirmed directly - requesting 393px back real
// numbers around 447-500px), so MOBILE_VIEWPORT is a request, not a guarantee; the check below
// only asserts the resulting width is still under the responsive breakpoint, not an exact value.
const DESKTOP_VIEWPORT = { width: 1280, height: 900 };
const MOBILE_VIEWPORT = { width: 393, height: 852 };
const RESPONSIVE_BREAKPOINT_PX = 640;

const PROBE_FIELD = "MeasInt";

/** @param {number} ms */
function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

/** @param {number} timeoutMs */
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

function spawnTwin() {
    return spawn(
        MICROPYTHON_BIN,
        ["digital_twin/run_wozi_integration.py", "--host", HOST, "--port", String(PORT), "--fram-state-path", "", "--scd30-state-path", ""],
        { cwd: REPO_ROOT, env: { ...process.env, MICROPYPATH, TZ: "UTC" }, stdio: ["ignore", "ignore", "pipe"] },
    );
}

/** @param {import("node:child_process").ChildProcess} proc @param {NodeJS.Signals} [signal] */
async function stopProcess(proc, signal = "SIGINT") {
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

// WebKitWebDriver/geckodriver both need a real X display even in "headless" use (confirmed
// directly for WebKitGTK; geckodriver's `-headless` Firefox arg was kept wrapped the same way for
// consistency - see runFirefox()'s own comment). Spawns Xvfb itself directly, rather than via the
// `xvfb-run` wrapper script: a wrapper process is an extra layer this file can't reliably tear
// down - confirmed directly (an earlier version used `xvfb-run -a <driver>` and SIGINT to the
// wrapper's own PID left both Xvfb and the driver binary itself still running afterward, a real
// leak found by checking `pgrep` after a run, not by inspection). Spawning Xvfb here directly
// gives this file a real handle to kill explicitly instead.
let nextDisplayNumber = 90;

/** @returns {{display: string, xvfbProc: import("node:child_process").ChildProcess}} */
function spawnVirtualDisplay() {
    nextDisplayNumber += 1;
    const display = `:${nextDisplayNumber}`;
    const xvfbProc = spawn("Xvfb", [display, "-screen", "0", "1280x1024x24", "-nolisten", "tcp"], { stdio: ["ignore", "ignore", "pipe"] });
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
        // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
        await sleep(100);
    }
    throw new Error(`Xvfb never created ${lockFile} within ${timeoutMs}ms`);
}

// --- Minimal raw W3C WebDriver HTTP client - used for WebKitWebDriver and geckodriver, neither of
// which Playwright can drive directly (see this file's own header comment). ---

/** @param {string} base @param {object} capabilities */
async function wdCreateSession(base, capabilities) {
    const res = await fetch(`${base}/session`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ capabilities: { alwaysMatch: capabilities } }) });
    const body = await res.json();
    if (body.value?.sessionId === undefined) {
        throw new Error(`WebDriver session creation failed: ${JSON.stringify(body)}`);
    }
    return body.value.sessionId;
}

/** @param {string} base @param {string} sid */
async function wdDeleteSession(base, sid) {
    await fetch(`${base}/session/${sid}`, { method: "DELETE" }).catch(() => {});
}

/** @param {string} base @param {string} sid @param {string} url */
async function wdNavigate(base, sid, url) {
    await fetch(`${base}/session/${sid}/url`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url }) });
}

/** @param {string} base @param {string} sid @param {number} width @param {number} height */
async function wdSetWindowRect(base, sid, width, height) {
    await fetch(`${base}/session/${sid}/window/rect`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ width, height }) });
}

/** @param {string} base @param {string} sid @param {string} script */
async function wdExecute(base, sid, script) {
    const res = await fetch(`${base}/session/${sid}/execute/sync`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ script, args: [] }) });
    const body = await res.json();
    if (body.value && typeof body.value === "object" && "error" in body.value) {
        throw new Error(`WebDriver script execution failed: ${JSON.stringify(body.value)}`);
    }
    return body.value;
}

// The nav-to-Sensors click, run alone (not combined with the field fill below): renderSection()
// swaps the visible section in asynchronously (a real fetch-then-render, not a synchronous DOM
// swap), so a script that clicks the nav link and immediately queries for the target field in the
// same synchronous execution can genuinely find it still null - confirmed directly (both WebKit
// and Firefox failed exactly this way before this was split into a poll, see git history). Kept as
// its own tiny script/poll pair rather than folded into an `await` inside one execute/sync call,
// since WebDriver's execute/sync has no way to await an in-page Promise across the wire anyway.
const NAV_TO_SENSORS_SCRIPT = `
    document.getElementById("hamburger-button").click();
    const link = [...document.querySelectorAll("[data-section-key]")].find((a) => a.dataset.sectionKey === "sensors");
    link.click();
`;

function fieldPresentScript() {
    return `return document.querySelector('[data-field-key="${PROBE_FIELD}"]') !== null;`;
}

function fillAndApplyScript(probeValue) {
    return `
        const input = document.querySelector('[data-field-key="${PROBE_FIELD}"]');
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

function readAppliedResultScript() {
    return `
        const w = document.querySelector('[data-field-wrapper-key="${PROBE_FIELD}"]');
        const c = document.querySelector('[data-current-value-for="${PROBE_FIELD}"]');
        return { applyStatus: w ? w.dataset.applyStatus : null, caption: c ? c.textContent : null };
    `;
}

/**
 * Polls `readFn` (a zero-arg async function returning a plain value) until `isReady` accepts its
 * result, or throws after `timeoutMs`. Shared by both the "has the target field rendered yet"
 * wait and the "has the apply status attribute appeared yet" wait below.
 * @param {() => Promise<unknown>} readFn
 * @param {(value: unknown) => boolean} isReady
 * @param {number} timeoutMs
 * @param {string} timeoutMessage
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
 * @param {{engine: string, viewport: "desktop" | "mobile", probeValue: number, driverProcessFactory: (display: string) => import("node:child_process").ChildProcess, driverBase: string, driverPort: number, capabilities: object}} opts
 */
async function runViaRawWebDriver({ engine, viewport, probeValue, driverProcessFactory, driverBase, driverPort, capabilities }) {
    const label = `${engine} (${viewport})`;
    const { display, xvfbProc } = spawnVirtualDisplay();
    let driverProc;
    let driverStderr = "";
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
        await wdNavigate(driverBase, sid, TWIN_URL);
        const readyTitle = await pollUntil(() => wdExecute(driverBase, sid, "return document.title;"), (t) => typeof t === "string" && t.includes("Sensor Station"), READY_TIMEOUT_MS, "page never reached \"Sensor Station\" title");
        if (!readyTitle.includes("Sensor Station")) {
            throw new Error(`unexpected page title: ${readyTitle}`);
        }

        await wdExecute(driverBase, sid, NAV_TO_SENSORS_SCRIPT);
        await pollUntil(() => wdExecute(driverBase, sid, fieldPresentScript()), (present) => present === true, 5000, `${PROBE_FIELD} field never rendered after navigating to Sensors`);

        const fillResult = await wdExecute(driverBase, sid, fillAndApplyScript(probeValue));
        if (viewport === "mobile" && fillResult.innerWidth >= RESPONSIVE_BREAKPOINT_PX) {
            throw new Error(`requested a mobile viewport but window.innerWidth was ${fillResult.innerWidth}px (>= ${RESPONSIVE_BREAKPOINT_PX}px breakpoint)`);
        }

        // Waits for BOTH data-apply-status (set as soon as the PUT resolves) AND the caption
        // (only updated by a separate, slightly later GET round trip - render.js's own
        // onApplied() -> fetchOnce(), see this file's header comment) to settle - polling only
        // the former was confirmed to race ahead of the caption in this file's own development,
        // reading back the previous check's stale value instead of this one's freshly-applied one.
        const expectedCaption = `Current value: ${probeValue}`;
        const applied = await pollUntil(
            () => wdExecute(driverBase, sid, readAppliedResultScript()),
            (r) => r.applyStatus !== null && r.applyStatus !== undefined && r.caption === expectedCaption,
            10000,
            `apply status/caption never settled within 10s (last seen: ${JSON.stringify(await wdExecute(driverBase, sid, readAppliedResultScript()))})`,
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
        // SIGKILL, not SIGINT: confirmed directly that Xvfb doesn't reliably exit on SIGINT within
        // SHUTDOWN_TIMEOUT_MS once a client (the driver process) has connected to it, and there's
        // no graceful-shutdown state worth waiting for here anyway (unlike the real digital twin's
        // own FRAM/SCD30 flush-on-SIGINT - see stopProcess()'s other caller, stopTwin-equivalent
        // spawnTwin() above).
        await stopProcess(xvfbProc, "SIGKILL");
    }
}

function runWebKit(viewport, probeValue) {
    return runViaRawWebDriver({
        engine: "WebKit",
        viewport,
        probeValue,
        driverProcessFactory: (display) => spawn(WEBKIT_DRIVER_BIN, [`--port=${WEBKIT_DRIVER_PORT}`], { env: { ...process.env, DISPLAY: display }, stdio: ["ignore", "ignore", "pipe"] }),
        driverBase: `http://127.0.0.1:${WEBKIT_DRIVER_PORT}`,
        driverPort: WEBKIT_DRIVER_PORT,
        capabilities: {},
    });
}

function runFirefox(viewport, probeValue) {
    return runViaRawWebDriver({
        engine: "Firefox",
        viewport,
        probeValue,
        // Given a real DISPLAY, `-headless` Firefox still uses it rather than requiring it be
        // unset - confirmed directly (harmless either way; kept for consistency with the WebKit
        // path above rather than special-casing Firefox's own process/env setup).
        driverProcessFactory: (display) => spawn(GECKODRIVER_BIN, ["--port", String(GECKODRIVER_PORT), "--binary", FIREFOX_BIN], { env: { ...process.env, DISPLAY: display }, stdio: ["ignore", "ignore", "pipe"] }),
        driverBase: `http://127.0.0.1:${GECKODRIVER_PORT}`,
        driverPort: GECKODRIVER_PORT,
        capabilities: { "moz:firefoxOptions": { args: ["-headless"] } },
    });
}

/**
 * Polls until `wrapperLocator`'s `data-apply-status` AND `captionLocator`'s text both settle to
 * their expected post-apply values, mirroring pollUntil() above. Both are needed, not just the
 * first: `data-apply-status` is set as soon as the PUT resolves, but the caption only updates via
 * a separate, slightly later GET round trip (render.js's own onApplied() -> fetchOnce(), see this
 * file's header comment) - polling only the attribute was confirmed to race ahead of the caption
 * in this file's own development, reading back the *previous* check's stale caption instead of
 * this one's freshly-applied value.
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

/** @param {"chromium" | "edge"} which @param {"desktop" | "mobile"} viewport @param {number} probeValue */
async function runChromiumFamily(which, viewport, probeValue) {
    const label = `${which === "edge" ? "Edge" : "Chromium"} (${viewport})`;
    const executablePath = which === "edge" ? EDGE_BIN : (existsSync(SANDBOX_CHROMIUM) ? SANDBOX_CHROMIUM : undefined);
    let browser;
    try {
        browser = await chromium.launch(executablePath ? { executablePath } : {});
        const context = await browser.newContext(viewport === "mobile" ? { ...devices["iPhone 15"] } : {});
        const page = await context.newPage();
        await page.goto(TWIN_URL);
        await page.waitForSelector("h1", { timeout: 10000 });

        const clickOrTap = viewport === "mobile" ? "tap" : "click";
        await page.locator("#hamburger-button")[clickOrTap]();
        await page.locator('[data-section-key="sensors"]').first()[clickOrTap]();
        const input = page.locator(`[data-field-key="${PROBE_FIELD}"]`);
        await input.waitFor();

        await input.fill(String(probeValue));
        const card = input.locator("xpath=ancestor::*[.//button[contains(@class,'apply-button')]][1]");
        await card.locator(".apply-button")[clickOrTap]();

        const wrapper = page.locator(`[data-field-wrapper-key="${PROBE_FIELD}"]`);
        const caption = page.locator(`[data-current-value-for="${PROBE_FIELD}"]`);
        const applyStatus = await pollForAppliedResult(wrapper, caption, `Current value: ${probeValue}`, 10000);
        if (applyStatus !== "valid") {
            throw new Error(`expected applyStatus "valid", got ${JSON.stringify(applyStatus)}`);
        }
        return { label, ok: true };
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return { label, ok: false, detail: message };
    } finally {
        await browser?.close().catch(() => {});
    }
}

async function main() {
    if (!existsSync(MICROPYTHON_BIN)) {
        console.error(`MicroPython Unix port not built at ${MICROPYTHON_BIN} - run 'uv run toolchain/setup_toolchain.py setup' first.`);
        process.exit(1);
    }

    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });
    const twin = spawnTwin();
    let twinStderr = "";
    twin.stderr?.on("data", (chunk) => {
        twinStderr += chunk.toString();
    });

    /** @type {{label: string, ok: boolean, detail?: string}[]} */
    const results = [];
    try {
        await waitUntilServing(TWIN_URL, READY_TIMEOUT_MS);

        const engines = [
            { name: "WebKit", available: existsSync(WEBKIT_DRIVER_BIN), run: runWebKit },
            { name: "Firefox", available: existsSync(FIREFOX_BIN) && existsSync(GECKODRIVER_BIN), run: runFirefox },
            { name: "Edge", available: existsSync(EDGE_BIN), run: (viewport, probeValue) => runChromiumFamily("edge", viewport, probeValue) },
            { name: "Chromium", available: true, run: (viewport, probeValue) => runChromiumFamily("chromium", viewport, probeValue) },
        ];

        // Every (engine, viewport) check gets its own probe value, never reused - each check reads
        // back its own just-applied value, so two checks racing/interleaving against the one shared
        // twin backend can never mistake one another's write for their own (confirmed necessary
        // directly: an earlier version reused the same value across engines and briefly masked a
        // real timing bug elsewhere in this file's own development).
        let nextProbeValue = 30;
        for (const engine of engines) {
            if (!engine.available) {
                console.warn(`SKIP ${engine.name}: binary not found (run scripts/setup_cross_browser_toolchain.sh)`);
                continue;
            }
            for (const viewport of /** @type {const} */ (["desktop", "mobile"])) {
                nextProbeValue += 1;
                // eslint-disable-next-line no-await-in-loop -- deliberate: one browser/engine at a time
                const result = await engine.run(viewport, nextProbeValue);
                results.push(result);
                console.log(`${result.ok ? "PASS" : "FAIL"} ${result.label}`);
                if (!result.ok) {
                    console.error(result.detail);
                }
            }
        }
    } finally {
        await stopProcess(twin);
    }

    const ran = results.length;
    const failed = results.filter((r) => !r.ok).length;
    console.log(`\n${ran - failed}/${ran} cross-browser smoke checks passed.`);
    if (ran === 0) {
        console.error("No engine was available at all - nothing was actually checked.");
        process.exit(1);
    }
    if (failed > 0) {
        console.error(`\n--- twin stderr ---\n${twinStderr}`);
        process.exit(1);
    }
}

await main();
