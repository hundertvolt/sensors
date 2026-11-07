// The allocation-failure marker pair the unit, twin, flash/bench and JS gates all match (CLAUDE.md's
// memory rule, SPECIFICATION.md Part I.4(e)), the twin's restart signs, and the drain a JS gate reads a
// twin's output through. Pure, no Node built-ins: tsconfig.json checks it as browser code.

export const MEMORY_ERROR_MARKERS = ["MemoryError", "memory allocation failed"];

// machine.reset() raises SimulatedResetError in the twin (digital_twin/machine.py), and the task supervisor logs
// "reboot triggered" before it: a live command whose twin printed either has not tested a running device.
export const TWIN_RESET_MARKERS = ["SimulatedResetError", "reboot triggered"];

// A child's kept output tail, in characters; trimming it never drops a marker line (scanned first).
export const OUTPUT_TAIL_CHARS = 256 * 1024;
const MARKER_LINES_QUOTED = 50;
const MARKER_OVERLAP = Math.max(...[...MEMORY_ERROR_MARKERS, ...TWIN_RESET_MARKERS].map((marker) => marker.length)) - 1;

/**
 * Every line of `text` holding any of `markers`, whole.
 * @param {string} text
 * @param {string[]} markers
 * @returns {string[]}
 */
function linesWith(text, markers) {
    return text.split("\n").filter((line) => markers.some((marker) => line.includes(marker)));
}

/**
 * The lines holding any of `markers`, quoted up to a bound and counted beyond it, never dropped unseen.
 * @param {string[]} markers
 */
function markedLineLog(markers) {
    /** @type {string[]} */
    const quoted = [];
    let unquoted = 0;
    return {
        /** @param {string} lines complete lines */
        add(lines) {
            for (const line of linesWith(lines, markers)) {
                if (quoted.length < MARKER_LINES_QUOTED) {
                    quoted.push(line);
                } else {
                    unquoted += 1;
                }
            }
        },
        /** @param {string[]} unfinished the lines still without their newline, scanned too */
        lines(unfinished) {
            const all = [...quoted, ...unfinished.flatMap((rest) => linesWith(rest, markers))];
            return unquoted > 0 ? [...all, `[${unquoted} more marker lines not quoted]`] : all;
        },
    };
}

/**
 * Every line of `text` holding either memory marker, whole.
 * @param {string} text
 * @returns {string[]}
 */
export function memoryMarkerLines(text) {
    return linesWith(text, MEMORY_ERROR_MARKERS);
}

/**
 * Every line of `text` holding either restart sign, whole.
 * @param {string} text
 * @returns {string[]}
 */
export function resetMarkerLines(text) {
    return linesWith(text, TWIN_RESET_MARKERS);
}

/**
 * A bounded, line-complete record of a child's output streams: complete lines join one tail in
 * arrival order, and each is scanned for both marker kinds before the tail is trimmed.
 * @param {number} [limit]
 */
export function createOutputDrain(limit = OUTPUT_TAIL_CHARS) {
    /** @type {Map<string, string>} */
    const partial = new Map();
    const memory = markedLineLog(MEMORY_ERROR_MARKERS);
    const reset = markedLineLog(TWIN_RESET_MARKERS);
    let tail = "";
    let dropped = 0;

    /** @param {string} lines complete lines, each ending in "\n" */
    function keep(lines) {
        memory.add(lines);
        reset.add(lines);
        tail += lines;
        if (tail.length > limit) {
            const cut = tail.indexOf("\n", tail.length - limit);
            const keepFrom = cut === -1 ? tail.length : cut + 1;
            dropped += keepFrom;
            tail = tail.slice(keepFrom);
        }
    }

    return {
        /** @param {string} stream @param {string} chunk */
        feed(stream, chunk) {
            const text = (partial.get(stream) ?? "") + chunk;
            const cut = text.lastIndexOf("\n");
            if (cut === -1 && text.length <= limit) {
                partial.set(stream, text);
                return;
            }
            // A line longer than the whole tail is broken rather than held back unbounded; the break
            // carries a marker's length minus one forward, so no marker can straddle it unseen.
            const end = cut === -1 ? text.length - MARKER_OVERLAP : cut + 1;
            keep(cut === -1 ? `${text.slice(0, end)}\n` : text.slice(0, end));
            partial.set(stream, text.slice(end));
        },
        /** @returns {string} the kept tail, a trim stated rather than silent, then any unfinished lines */
        text() {
            const unfinished = [...partial.values()].filter((rest) => rest !== "").map((rest) => `${rest}\n`).join("");
            return `${dropped > 0 ? `[${dropped} earlier characters dropped]\n` : ""}${tail}${unfinished}`;
        },
        /** @returns {string[]} every memory-marker line seen, unfinished lines included, an overflow counted */
        markerLines() {
            return memory.lines([...partial.values()]);
        },
        /** @returns {string[]} every restart-sign line seen, the same way */
        resetLines() {
            return reset.lines([...partial.values()]);
        },
    };
}

/**
 * Drains a child's stdout and stderr into one createOutputDrain(): an undrained pipe blocks the
 * child, and the drained text is what the memory gate scans. `closed(ms)` is true once both streams
 * have closed, so a verdict never reads output the child had not finished writing.
 * @param {{stdout: ReadableText | null, stderr: ReadableText | null}} child
 */
export function drainChildOutput(child) {
    const drain = createOutputDrain();
    /** @type {Promise<void>[]} */
    const ends = [];
    for (const [name, stream] of /** @type {const} */ ([["stdout", child.stdout], ["stderr", child.stderr]])) {
        if (stream !== null) {
            stream.setEncoding("utf8");
            stream.on("data", (chunk) => {
                drain.feed(name, String(chunk));
            });
            ends.push(new Promise((resolve) => {
                stream.on("close", () => {
                    resolve();
                });
            }));
        }
    }
    const allClosed = Promise.all(ends);
    return {
        ...drain,
        /** @param {number} timeoutMs @returns {Promise<boolean>} */
        async closed(timeoutMs) {
            /** @type {ReturnType<typeof setTimeout> | undefined} */
            let timer;
            const timedOut = new Promise((resolve) => {
                timer = setTimeout(() => {
                    resolve(false);
                }, timeoutMs);
            });
            try {
                return await Promise.race([allClosed.then(() => true), timedOut]) === true;
            } finally {
                clearTimeout(timer);
            }
        },
    };
}

/**
 * @typedef {{setEncoding(encoding: "utf8"): unknown, on(event: "data", listener: (chunk: unknown) => void): unknown, on(event: "close", listener: () => void): unknown}} ReadableText
 */
