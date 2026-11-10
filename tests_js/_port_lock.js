// Node side of scripts/_port_lock.sh: one runner per product-fixed port at a time, the holder's own process and its
// descendants pass - the same flock(2) on the same file, its runner and pid lines, message and owner chain.
// probePortLock() is the Commands API probe behind tests_js/port-lock.test.js; no runner calls it.

import { spawn, spawnSync } from "node:child_process";
import { accessSync, closeSync, constants, mkdtempSync, openSync, readFileSync, rmSync, statSync, writeFileSync, writeSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const PROBE_WAIT_MS = 10000;

// The probe's two actors: take one port, print what the lock and the chain say, then hold, run a child actor, or exit;
// a node actor with dropHeld first forgets the ports its chain lists.
const NODE_ACTOR = `
import { spawnSync } from "node:child_process";
import path from "node:path";
const { acquirePortLock } = await import(process.env.LOCK_MODULE_URL);
const spec = JSON.parse(process.env.LOCK_ACTOR);
if (spec.dropHeld) {
    delete process.env.SENSORS_PORT_LOCKS_HELD;
}
const file = path.join(process.env.XDG_RUNTIME_DIR, "sensors-port-" + spec.port + ".flock");
const held = () => spawnSync("flock", ["-n", file, "true"]).status !== 0;
try {
    const release = acquirePortLock(spec.port, spec.runner);
    console.log("took " + process.pid + " held=" + process.env.SENSORS_PORT_LOCKS_HELD + " owner=" + process.env.SENSORS_PORT_LOCK_OWNER);
    if (spec.twice) {
        acquirePortLock(spec.port, spec.runner)();
        const afterInner = held();
        release();
        console.log("after inner " + afterInner + " after outer " + held());
    }
    if (spec.then) {
        const then = spec.then;
        const env = { ...process.env, LOCK_ACTOR: JSON.stringify(then), LOCK_PORT: String(then.port), LOCK_RUNNER: then.runner, LOCK_THEN: then.then ? JSON.stringify(then.then) : "", LOCK_HOLD: "" };
        const child = then.lang === "bash"
            ? spawnSync("bash", ["-c", process.env.LOCK_BASH_SRC], { env, stdio: "inherit" })
            : spawnSync(process.execPath, ["--input-type=module", "-e", process.env.LOCK_NODE_SRC], { env, stdio: "inherit" });
        console.log("then " + child.status);
        process.exitCode = child.status ?? 1;
    }
    if (spec.hold) {
        setInterval(() => {}, 1000);
    }
} catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    process.exitCode = 1;
}
`;
const BASH_ACTOR = `
source scripts/_port_lock.sh
trap port_lock_release_all EXIT
port_lock_take "$LOCK_PORT" "$LOCK_RUNNER"
echo "took $$ held=$SENSORS_PORT_LOCKS_HELD owner=$SENSORS_PORT_LOCK_OWNER"
if [ -n "\${LOCK_THEN:-}" ]; then
    LOCK_ACTOR="$LOCK_THEN" LOCK_THEN="" node --input-type=module -e "$LOCK_NODE_SRC"
    rc=$?
    echo "then $rc"
    exit "$rc"
fi
if [ -n "\${LOCK_HOLD:-}" ]; then
    while :; do sleep 0.1; done
fi
`;

/**
 * @param {string} item
 * @param {string | undefined} list a space-separated list, as the chain variables hold them
 * @returns {boolean}
 */
function isListed(item, list) {
    return (list ?? "").split(" ").includes(item);
}

/**
 * The environment one probe actor starts with: a private lock root, the two actor sources, and either no chain or
 * the one given, so a holder of the outer run can never let an actor pass.
 * @param {string} root
 * @param {{owner: string, held: string} | undefined} inherit
 * @returns {NodeJS.ProcessEnv}
 */
function actorEnv(root, inherit) {
    /** @type {NodeJS.ProcessEnv} */
    const env = { ...process.env };
    delete env.SENSORS_PORT_LOCK_OWNER;
    delete env.SENSORS_PORT_LOCKS_HELD;
    return {
        ...env,
        ...(inherit === undefined ? {} : { SENSORS_PORT_LOCK_OWNER: inherit.owner, SENSORS_PORT_LOCKS_HELD: inherit.held }),
        XDG_RUNTIME_DIR: root,
        PATH: `${path.dirname(process.execPath)}:${process.env.PATH ?? ""}`,
        LOCK_MODULE_URL: pathToFileURL(fileURLToPath(import.meta.url)).href,
        LOCK_NODE_SRC: NODE_ACTOR,
        LOCK_BASH_SRC: BASH_ACTOR,
    };
}

/**
 * The lock file's runner and pid lines, "" for either it lacks.
 * @param {string} file
 * @returns {[string, string]}
 */
function holderOf(file) {
    /** @type {string[]} */
    let lines = [];
    try {
        lines = readFileSync(file, "utf8").split("\n");
    } catch {
        // Unreadable: no holder named.
    }
    return [lines[0] ?? "", lines[1] ?? ""];
}

/**
 * Collects an actor's output until it exits, killing its group past the probe's bound.
 * @param {import("node:child_process").ChildProcess} proc
 * @param {(stdout: string) => boolean} [enough] resolves early, the actor still running, once its output satisfies it
 * @returns {Promise<{code: number | null, stdout: string, stderr: string}>}
 */
function settle(proc, enough) {
    return new Promise((resolve) => {
        const out = { stdout: "", stderr: "" };
        const finish = () => resolve({ code: proc.exitCode, ...out });
        const timer = setTimeout(() => {
            stopGroup(proc);
            out.stderr += `\nthe actor did not settle within ${PROBE_WAIT_MS}ms`;
            finish();
        }, PROBE_WAIT_MS);
        proc.stdout?.on("data", (chunk) => {
            out.stdout += String(chunk);
            if (enough?.(out.stdout)) {
                clearTimeout(timer);
                finish();
            }
        });
        proc.stderr?.on("data", (chunk) => {
            out.stderr += String(chunk);
        });
        proc.once("close", () => {
            clearTimeout(timer);
            finish();
        });
    });
}

/**
 * Starts one probe actor in its own process group, so stopping it also stops whatever it started.
 * @param {{lang: "node" | "bash", port: number, runner: string, twice?: boolean, dropHeld?: boolean, then?: object}} spec
 * @param {NodeJS.ProcessEnv} env
 * @param {boolean} hold
 * @returns {import("node:child_process").ChildProcess}
 */
function startActor(spec, env, hold) {
    const own = { ...spec, hold };
    const actorEnvironment = { ...env, LOCK_ACTOR: JSON.stringify(own), LOCK_PORT: String(spec.port), LOCK_RUNNER: spec.runner, LOCK_THEN: spec.then ? JSON.stringify(spec.then) : "", LOCK_HOLD: hold ? "1" : "" };
    const [command, args] = spec.lang === "bash" ? ["bash", ["-c", BASH_ACTOR]] : [process.execPath, ["--input-type=module", "-e", NODE_ACTOR]];
    return spawn(command, args, { cwd: REPO_ROOT, env: actorEnvironment, detached: true, stdio: ["ignore", "pipe", "pipe"] });
}

/**
 * Stops a probe actor's whole process group.
 * @param {import("node:child_process").ChildProcess} proc
 */
function stopGroup(proc) {
    if (proc.pid !== undefined && proc.exitCode === null && proc.signalCode === null) {
        try {
            process.kill(-proc.pid, "SIGTERM");
        } catch {
            // Already gone.
        }
    }
}

/**
 * Holds `port` for `runner` until the returned release (or this process's exit), or throws naming the holder: flock(2)
 * through a `flock` child given the descriptor, so the lock stays with this process's open file. Its own process and
 * any process whose inherited chain lists the holder and the port pass without taking it.
 * @param {number} port
 * @param {string} runner
 * @returns {() => void} the release: a no-op for a lock this process did not take
 */
export function acquirePortLock(port, runner) {
    if (!Number.isInteger(port) || port < 1 || port > 65535 || runner === "") {
        throw new Error(`acquirePortLock(port, runner) needs a port 1-65535 and a runner name, not ${JSON.stringify(port)} ${JSON.stringify(runner)}`);
    }
    const root = process.env.XDG_RUNTIME_DIR || "/tmp";
    try {
        accessSync(root, constants.W_OK);
        if (!statSync(root).isDirectory()) {
            throw new Error("not a directory");
        }
    } catch {
        throw new Error(`acquirePortLock: the lock root ${root} is not a writable directory`);
    }
    const file = path.join(root, `sensors-port-${port}.flock`);
    const own = String(process.pid);
    const fd = openSync(file, constants.O_RDWR | constants.O_CREAT);
    const took = spawnSync("flock", ["-n", "3"], { stdio: ["ignore", "ignore", "pipe", fd] });
    if (took.error !== undefined) {
        closeSync(fd);
        throw new Error(`flock (util-linux) is not on PATH - tests_js/_port_lock.js holds ${file} with it`, { cause: took.error });
    }
    if (took.status !== 0) {
        closeSync(fd);
        const [holder, pid] = holderOf(file);
        if (pid === own || (isListed(pid, process.env.SENSORS_PORT_LOCK_OWNER) && isListed(String(port), process.env.SENSORS_PORT_LOCKS_HELD))) {
            return () => { /* its own process, or the ancestor that took it, releases it */ };
        }
        throw new Error(`port ${port} is held by ${holder || "an unnamed runner"} (pid ${pid || "unknown"}) - run the suites one after the other (CLAUDE.md)`);
    }
    writeSync(fd, `${runner}\n${own}\n`, 0); // in place, as the shell library writes it
    process.env.SENSORS_PORT_LOCKS_HELD = isListed(String(port), process.env.SENSORS_PORT_LOCKS_HELD) ? process.env.SENSORS_PORT_LOCKS_HELD : [process.env.SENSORS_PORT_LOCKS_HELD, port].filter(Boolean).join(" ");
    process.env.SENSORS_PORT_LOCK_OWNER = isListed(own, process.env.SENSORS_PORT_LOCK_OWNER) ? process.env.SENSORS_PORT_LOCK_OWNER : [process.env.SENSORS_PORT_LOCK_OWNER, own].filter(Boolean).join(" ");
    let open = true;
    return () => {
        if (open) {
            open = false;
            closeSync(fd);
        }
    };
}

/**
 * The Commands API probe: on a private lock root, optionally plants a dead holder's lock or starts a live holder,
 * runs the taker to its end, and reports its exit, output, the lock file's holder and whether the lock is free afterwards.
 * @param {unknown} _context Vitest's injected command context (unused)
 * @param {{holder?: Parameters<typeof startActor>[0], taker: Parameters<typeof startActor>[0], inherit?: {owner: string, held: string}, plant?: {port: number, pid: "dead" | "", runner: string}}} args
 * @returns {Promise<{holderPid: number | null, code: number | null, stdout: string, stderr: string, lock: {runner: string, pid: string}, freeAfterTaker: boolean}>}
 */
export async function probePortLock(_context, { holder, taker, inherit, plant }) {
    const root = mkdtempSync(path.join(tmpdir(), "sensors-port-lock-"));
    /** @type {import("node:child_process").ChildProcess | undefined} */
    let held;
    try {
        if (plant !== undefined) {
            writeFileSync(path.join(root, `sensors-port-${plant.port}.flock`), `${plant.runner}\n${plant.pid === "dead" ? `${spawnSync("true").pid}\n` : ""}`);
        }
        let holderPid = null;
        if (holder !== undefined) {
            held = startActor(holder, actorEnv(root, undefined), true);
            const started = await settle(held, (stdout) => /^took \d+/mu.test(stdout));
            holderPid = Number(/^took (?<pid>\d+)/mu.exec(started.stdout)?.groups?.pid ?? Number.NaN);
            if (!Number.isInteger(holderPid)) {
                throw new Error(`the ${holder.lang} holder never took its lock: ${started.stderr}`);
            }
        }
        const ran = await settle(startActor(taker, actorEnv(root, inherit), false));
        const file = path.join(root, `sensors-port-${taker.port}.flock`);
        const [runner, pid] = holderOf(file);
        return { holderPid, ...ran, lock: { runner, pid }, freeAfterTaker: spawnSync("flock", ["-n", file, "true"]).status === 0 };
    } finally {
        if (held !== undefined) {
            stopGroup(held);
            await settle(held);
        }
        rmSync(root, { recursive: true, force: true });
    }
}
