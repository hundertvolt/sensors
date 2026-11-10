// The launch frame the live command modules and the smoke share (SPECIFICATION.md Part H.7): the Unix-port probe, the
// twin layout, one device's twin on a given port with its own site, readiness, shutdown, the captive-DNS port lock each
// twin holds while it runs, and the verdict read from a stopped twin's output.

import { execFileSync, spawn } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { LAYOUT_FILE, twinLayout, withSite } from "./_micropypath.js";
import { acquirePortLock } from "./_port_lock.js";
import { twinStartFailure } from "./_twin_start_failure.js";

export const HOST = "127.0.0.1";
export const READY_TIMEOUT_MS = 20000;
export const SHUTDOWN_TIMEOUT_MS = 15000;
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// The twin layout of the one MICROPYPATH definition, read once.
export const MICROPYPATH = twinLayout(readFileSync(path.join(REPO_ROOT, LAYOUT_FILE), "utf8"), LAYOUT_FILE);
/** The marker pair every memory gate matches, from its one definition (scripts/test.sh and scripts/_twin_process.py read it too). */
export const MEMORY_ERROR_MARKERS = /** @type {string[]} */ (JSON.parse(readFileSync(path.join(REPO_ROOT, "scripts", "memory_markers.json"), "utf8")));
const MISSING_INTERPRETER = "MicroPython Unix port not built - run 'uv run toolchain/setup_toolchain.py setup' first (CI's web-unit-tests job does this automatically)";
/** @type {string | undefined} the standard binary the probe named, once asked */
let interpreter;
// Every twin's captive DNS binds this product-fixed port, so a twin runs only while its runner holds the port's lock.
const DNS_PORT = 53;
const LOCK_RUNNER = "the vitest live tier";
const CONFIG_DIR_PREFIX = path.join(tmpdir(), "sensors-live-");
const RUNNER = "digital_twin/run_generic_integration.py";
/** @type {WeakMap<import("node:child_process").ChildProcess, Error>} */
const spawnErrors = new WeakMap();
/** @type {WeakMap<import("node:child_process").ChildProcess, () => void>} */
const lockReleases = new WeakMap();
/** @type {WeakMap<import("node:child_process").ChildProcess, string>} */
const stopFiles = new WeakMap();
let launched = 0; // the twins this process spawned, which names each one's stop file

/**
 * `start()`'s process, or the lock released again when it throws, so a failed launch leaves no port held.
 * @param {() => void} release
 * @param {() => import("node:child_process").ChildProcess} start
 * @returns {import("node:child_process").ChildProcess}
 */
function spawnOrRelease(release, start) {
    try {
        return start();
    } catch (err) {
        release();
        throw err;
    }
}

/**
 * Stops one twin: its stop file, then SIGKILL past the shutdown bound, returning only once it has exited.
 * @param {import("node:child_process").ChildProcess} proc
 * @param {string} stopFile the runner's --stop-file, which spawnTwin() gave it
 */
async function stopProcess(proc, stopFile) {
    if (proc.pid === undefined || proc.exitCode !== null || proc.signalCode !== null) {
        return; // never started (waitUntilServing() names its spawn error) or already gone
    }
    const exited = new Promise((resolve) => {
        proc.once("exit", resolve);
    });
    // The stop file ends the runner on main()'s clean path, as scripts/_twin_process.py's shutdown() does: an interrupt
    // the Unix port loses at an `async with` body's end leaves a twin serving until it is killed (SPECIFICATION.md F.6.1).
    writeFileSync(stopFile, "");
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
 * Holds the captive-DNS port for one stretch that boots twins more than once (a restart): twins the stretch spawns
 * take it again within this process, so another runner cannot take it between them.
 * @returns {() => void} the release
 */
export function holdTwinPorts() {
    return acquirePortLock(DNS_PORT, LOCK_RUNNER);
}

/**
 * The standard Unix-port binary, as scripts/_unix_port.sh's check names it (asked once, building nothing), or an error
 * carrying the probe's own words: the live tier needs the binary, and a run without it fails, never skips.
 * @returns {string}
 */
export function requireInterpreter() {
    if (interpreter === undefined) {
        try {
            interpreter = execFileSync("bash", ["scripts/_unix_port.sh", "check", "standard"], { cwd: REPO_ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
        } catch (err) {
            const said = /** @type {{stderr?: unknown}} */ (err).stderr;
            throw new Error(`${MISSING_INTERPRETER} (the probe said: ${typeof said === "string" ? said.trim() : String(err)})`, { cause: err });
        }
    }
    return interpreter;
}

/**
 * A fresh config directory for one command's twins: its own, under the OS temp directory, never the manual run's
 * digital_twin/config/, which no command touches. With its trailing separator, as the runner's --config-dir takes it.
 * @returns {string}
 */
export function makeConfigDir() {
    return mkdtempSync(CONFIG_DIR_PREFIX) + path.sep;
}

/**
 * Each entry beside config directory `dir` whose path extends the directory's own: a file the twin named by appending to
 * a directory given without its trailing separator (src/asy_config_manager.py config_filename()) lands there.
 * @param {string} dir
 * @returns {string[]}
 */
export function besideConfigDir(dir) {
    const own = path.resolve(dir);
    const parent = path.dirname(own);
    return readdirSync(parent).map((name) => path.join(parent, name)).filter((entry) => entry !== own && entry.startsWith(own));
}

/**
 * Removes a directory makeConfigDir() made, and refuses any other.
 * @param {string} dir
 */
export function removeConfigDir(dir) {
    if (!path.resolve(dir).startsWith(CONFIG_DIR_PREFIX)) {
        throw new Error(`refusing to remove ${dir}: not a config directory makeConfigDir() made`);
    }
    rmSync(dir, { recursive: true, force: true });
}

/** @param {number} ms */
export function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

/**
 * Boots `device`'s twin on `port` under the captive-DNS lock: build/generated_src first, sensortask_<device>.py's one
 * home (SPECIFICATION.md Part L.2), its own site (build/generated_html/<device>, package.json's "pretest" hooks), the
 * caller's config directory (makeConfigDir()), the rest in memory.
 * @param {{device: string, port: number, configDir: string}} twin
 * @returns {import("node:child_process").ChildProcess}
 */
export function spawnTwin({ device, port, configDir }) {
    launched += 1; // a stop file per twin: a restarted twin's stop runs beside its predecessor's repeated stopTwin()
    const stopFile = path.join(tmpdir(), `sensors-twin-stop-${process.pid}-${launched}`);
    const args = [
        RUNNER,
        "--module",
        `sensortask_${device}`,
        "--wiring-plan",
        path.join(REPO_ROOT, "build", "generated_src", `sensortask_${device}_wiring_plan.json`),
        "--device",
        device,
        "--host",
        HOST,
        "--port",
        String(port),
        "--fram-state-path",
        "", // in-memory only - see digital_twin/README.md's "FRAM persistence" section for this convention
        "--scd30-state-path",
        "", // same convention, "SCD30 persistence" section
        "--mem-backup-state-path",
        "", // the watchdog scratch registers, likewise
        "--stop-file",
        stopFile,
        "--config-dir",
        configDir,
    ];
    // The device's own built site in place of the unit tier's shared copy, so a twin never serves another device's site.
    /** @type {NodeJS.ProcessEnv} */
    const env = { ...process.env, MICROPYPATH: withSite(MICROPYPATH, `build/generated_html/${device}`), TZ: "UTC" };
    // scripts/test.sh's own address for each of its file jobs: a caller's would bind the twin's captive DNS off HOST, which
    // the port lock below assumes (scripts/_twin_process.py's twin_env drops it too; agent, 2026-10-28).
    delete env.TEST_TWIN_HOST;
    const bin = requireInterpreter();
    rmSync(stopFile, { force: true }); // an earlier process's, left by a run killed before its stop, would end this one at once
    const release = acquirePortLock(DNS_PORT, LOCK_RUNNER);
    const proc = spawnOrRelease(release, () => spawn(bin, args, {
        cwd: REPO_ROOT,
        env,
        // Both streams are drained: an undrained pipe blocks the child; the drained text is scanned for the memory markers.
        stdio: ["ignore", "pipe", "pipe"],
    }));
    lockReleases.set(proc, release);
    stopFiles.set(proc, stopFile);
    // An unhandled ChildProcess 'error' event crashes the whole Node/Vitest process, skipping the
    // caller's try/finally: the listener keeps the error for waitUntilServing() to name.
    proc.on("error", (err) => { spawnErrors.set(proc, err); });
    return proc;
}

/**
 * Stops a twin and, once it has exited, releases the captive-DNS lock its spawn took.
 * @param {import("node:child_process").ChildProcess} proc
 */
export async function stopTwin(proc) {
    const stopFile = /** @type {string} */ (stopFiles.get(proc)); // every twin comes from spawnTwin()
    try {
        await stopProcess(proc, stopFile);
    } finally {
        rmSync(stopFile, { force: true });
        lockReleases.get(proc)?.();
        lockReleases.delete(proc);
    }
}

/**
 * The verdict once a command's twins have stopped: an allocation-failure marker or a restart sign anywhere in a
 * twin's output fails it (SPECIFICATION.md Part I.4(e)), quoting the lines, even when the check itself passed.
 * @param {string} what the command, for the message
 * @param {ReturnType<typeof import("./_memory_markers.js").drainChildOutput>[]} outputs every twin it started, in order
 * @param {unknown} failure what the check itself threw, or null
 * @param {boolean} drained whether every output stream closed, so the scans saw everything
 */
export function twinVerdict(what, outputs, failure, drained) {
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
 * Waits until the twin answers on `port`, naming a spawn error or an early exit at once rather than waiting it out.
 * @param {import("node:child_process").ChildProcess} proc
 * @param {number} port
 * @param {number} timeoutMs
 */
export async function waitUntilServing(proc, port, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        const failure = twinStartFailure({ spawnError: spawnErrors.get(proc) ?? null, exitCode: proc.exitCode, signalCode: proc.signalCode });
        if (failure !== null) {
            throw new Error(failure);
        }
        try {
            // eslint-disable-next-line no-await-in-loop -- sequential polling: each probe waits for the one before
            const res = await fetch(`http://${HOST}:${port}/`);
            if (res.status === 200) {
                return;
            }
        } catch {
            // Not up yet - keep polling.
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        await sleep(250);
    }
    throw new Error(`digital twin never started serving on ${HOST}:${port} within ${timeoutMs}ms`);
}
