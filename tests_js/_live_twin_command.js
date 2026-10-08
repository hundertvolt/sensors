// Server-side Vitest Commands API module backing tests_js/live-backend.test.js: spawns the twin
// and drives a real Playwright page against it directly (Vitest's own browser-mode `page` has no
// API for navigating to an external origin - vitest-dev/vitest#7875). See SPECIFICATION.md Part H.7.

import { execFileSync, spawn } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { drainChildOutput } from "./_memory_markers.js";
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
    if (proc.exitCode !== null || proc.signalCode !== null) {
        return;
    }
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
            new Promise((resolve) => {
                proc.once("exit", resolve);
            }),
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
}

/**
 * The command's verdict once its twin has stopped: an allocation-failure marker anywhere in the twin's
 * output fails it (SPECIFICATION.md Part I.4(e)), quoting the lines, even when the check itself passed.
 * @param {string} what the command, for the message
 * @param {ReturnType<typeof drainChildOutput>} output
 * @param {unknown} failure what the check itself threw, or null
 * @param {boolean} drained whether both output streams closed, so the scan saw everything
 */
function twinVerdict(what, output, failure, drained) {
    const marked = output.markerLines();
    const checkFailed = failure === null ? "" : `\n(the check itself also failed: ${failure instanceof Error ? failure.message : String(failure)})`;
    const cause = failure === null ? undefined : { cause: failure };
    if (marked.length > 0) {
        throw new Error(`${what}: the twin logged an allocation failure:\n${marked.join("\n")}${checkFailed}`, cause);
    }
    if (!drained) {
        throw new Error(`${what}: the twin's output did not close within ${SHUTDOWN_TIMEOUT_MS}ms of it stopping, so the allocation-failure scan is incomplete${checkFailed}`, cause);
    }
    if (failure !== null) {
        const message = failure instanceof Error ? failure.message : String(failure);
        throw new Error(`${what} failed: ${message}\n--- twin output ---\n${output.text()}`, cause);
    }
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
 * @param {{context: import("playwright").BrowserContext}} ctx
 * @param {string} device a devices/<device>.toml stem, booted from its own generated module and site
 * @returns {Promise<{skipped: true, reason: string} | {skipped: false, titleHasSensorStation: boolean, deviceName: string, debugLevelApplyStatus: string | null}>}
 */
export async function runLiveBackendSmoke({ context }, device) {
    if (!existsSync(MICROPYTHON_BIN)) {
        return {
            skipped: true,
            reason: `MicroPython Unix port not built at ${MICROPYTHON_BIN} - run 'uv run toolchain/setup_toolchain.py setup' first (CI's web-unit-tests job does this automatically)`,
        };
    }

    // Fresh state every run, mirroring scripts/_digital_twin_ci_suite.py's own "clean" step -
    // FRAM/SCD30 are already in-memory-only above; config/ is the one thing that still persists
    // to a fixed path by default (run_generic_integration.py exposes no --cfg-path flag).
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });

    const proc = spawnTwin(device);
    const output = drainChildOutput(proc);

    let livePage;
    /** @type {{skipped: false, titleHasSensorStation: boolean, deviceName: string, debugLevelApplyStatus: string | null} | undefined} */
    let checked;
    /** @type {unknown} */
    let failure = null;
    try {
        await waitUntilServing(proc, READY_TIMEOUT_MS);

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

        // The nav is a slide-in drawer (SPECIFICATION.md Part H.4), off-screen/hidden until the
        // hamburger button opens it - the section links exist in the DOM immediately (confirmed
        // above via waitForSelector) but aren't clickable until the drawer is actually open.
        await livePage.locator("#hamburger-button").click();
        await livePage.locator('[data-section-key="system"]').click();
        const debugLevelInput = livePage.locator('[data-field-key="DebugLevel"]');
        await debugLevelInput.waitFor();
        await debugLevelInput.fill("4");
        const card = livePage.locator("[data-group-key]").filter({ has: debugLevelInput });
        await card.locator(".apply-button").click();

        const fieldWrapper = livePage.locator('[data-field-wrapper-key="DebugLevel"]');
        let debugLevelApplyStatus = null;
        const attrDeadline = Date.now() + 10000;
        while (debugLevelApplyStatus === null && Date.now() < attrDeadline) {
            // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
            debugLevelApplyStatus = await fieldWrapper.getAttribute("data-apply-status");
            if (debugLevelApplyStatus === null) {
                // eslint-disable-next-line no-await-in-loop -- same reasoning as above
                await sleep(200);
            }
        }

        checked = { skipped: false, titleHasSensorStation, deviceName, debugLevelApplyStatus };
    } catch (err) {
        failure = err;
    } finally {
        if (livePage) {
            livePage.removeAllListeners();
            await livePage.close().catch(() => { /* best-effort teardown - a page already gone is fine */ });
        }
        await stopTwin(proc);
    }
    twinVerdict(`live-backend smoke check for ${device}`, output, failure, await output.closed(SHUTDOWN_TIMEOUT_MS));
    if (checked === undefined) {
        throw new Error(`live-backend smoke check for ${device} ended with no result`);
    }
    return checked;
}

/**
 * Parallel real-browser tabs against one live twin: the tier exercising the connection ceiling from
 * a real browser rather than a socket loop. Every tab navigates at once (SPECIFICATION.md Part H.7).
 * @param {{context: import("playwright").BrowserContext}} ctx
 * @param {string} device a devices/<device>.toml stem; its own ceiling sizes the tab count
 * @returns {Promise<{skipped: true, reason: string} | {skipped: false, tabs: number, loaded: number, deviceNames: string[]}>}
 */
export async function runLiveBackendConcurrentTabs({ context }, device) {
    if (!existsSync(MICROPYTHON_BIN)) {
        return {
            skipped: true,
            reason: `MicroPython Unix port not built at ${MICROPYTHON_BIN} - run 'uv run toolchain/setup_toolchain.py setup' first (CI's web-unit-tests job does this automatically)`,
        };
    }
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });

    // Half the ceiling, so it is never exceeded: a tab fetches index.html then app.js and poll-manager
    // serialises its REST calls, so a tab holds one slot, two while a finished one is still releasing.
    const tabs = Math.max(1, Math.floor(configuredMaxConnections(device) / 2));
    const proc = spawnTwin(device);
    const output = drainChildOutput(proc);

    /** @type {import("playwright").Page[]} */
    const pages = [];
    /** @type {string[] | undefined} */
    let deviceNames;
    /** @type {unknown} */
    let failure = null;
    try {
        await waitUntilServing(proc, READY_TIMEOUT_MS);
        for (let i = 0; i < tabs; i += 1) {
            // eslint-disable-next-line no-await-in-loop -- pages are CREATED sequentially and NAVIGATED together below; that is what makes the loads concurrent rather than the setup
            pages.push(await context.newPage());
        }
        deviceNames = await Promise.all(pages.map(async (page) => {
            await page.goto(`http://${HOST}:${PORT}/`);
            await page.waitForSelector('[data-section-key="system"]', { timeout: TAB_WAIT_MS });
            return (await page.locator("#device-name").textContent())?.trim() ?? "";
        }));
    } catch (err) {
        failure = err;
    } finally {
        await Promise.all(pages.map((page) => page.close().catch(() => { /* best-effort teardown - a page already gone is fine */ })));
        await stopTwin(proc);
    }
    twinVerdict(`live-backend concurrent-tab check for ${device}`, output, failure, await output.closed(SHUTDOWN_TIMEOUT_MS));
    if (deviceNames === undefined) {
        throw new Error(`live-backend concurrent-tab check for ${device} ended with no result`);
    }
    return { skipped: false, tabs, loaded: deviceNames.length, deviceNames };
}
