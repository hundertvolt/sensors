/**
 * Single-flight request coordinator (WEBSITE_PLAN.md §4 "Poll coordination").
 * One shared instance is the sole source of truth for "is a request in flight" - the
 * measurements/status group and the settings/config group must never be polled concurrently
 * (the device has very few available sockets), so every fetch in the app - live polls and
 * config-form submits alike - goes through here rather than calling fetch() directly.
 */

/**
 * Default per-request timeout (WEBSITE_PLAN.md §4 "Poll coordination"): the single-flight queue
 * must never wait forever on one hung connection - the device has very few available sockets, so
 * a stuck request has to eventually free the queue for the next one instead of wedging the whole
 * app's polling permanently.
 */
export const DEFAULT_TIMEOUT_MS = 15000;

class PollManager {
    /** @type {Promise<void>} */
    #queue = Promise.resolve();

    /** @type {number} */
    #activeCount = 0;

    /**
     * Run one HTTP request, queued behind any request already in flight. The queue only advances
     * once the response body has been fully read - the closest a browser fetch() lets us get to
     * "the connection has fully closed" before letting the next request start. A request that
     * hangs past `timeoutMs` aborts (freeing the underlying connection) and rejects, so the queue
     * is never stuck waiting on a connection that will never resolve on its own.
     * @param {string} url
     * @param {RequestInit} [init]
     * @param {number} [timeoutMs]
     * @returns {Promise<{ok: boolean, status: number, body: unknown}>}
     */
    request(url, init, timeoutMs = DEFAULT_TIMEOUT_MS) {
        const run = async () => {
            this.#activeCount += 1;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
            const timedOut = new Promise((_resolve, reject) => {
                controller.signal.addEventListener(
                    "abort",
                    () => reject(new Error(`Request to ${url} timed out after ${timeoutMs}ms`)),
                    { once: true },
                );
            });
            try {
                const response = await Promise.race([fetch(url, { ...init, signal: controller.signal }), timedOut]);
                const text = await response.text();
                const body = text.length > 0 ? JSON.parse(text) : null;
                return { ok: response.ok, status: response.status, body };
            } finally {
                clearTimeout(timeoutId);
                this.#activeCount -= 1;
            }
        };

        const scheduled = this.#queue.then(run, run);
        this.#queue = scheduled.then(
            () => undefined,
            () => undefined,
        );
        return scheduled;
    }

    /** @returns {boolean} true while a request is in flight. */
    get isBusy() {
        return this.#activeCount > 0;
    }
}

export const pollManager = new PollManager();

/**
 * Self-scheduling poll loop: waits for one request to fully resolve before scheduling the next
 * one `intervalMs` later, so a slow response never causes overlapping polls (unlike
 * setInterval). Returns a stop function.
 * @param {() => Promise<void>} pollOnce
 * @param {number} intervalMs
 * @returns {() => void}
 */
export function startPolling(pollOnce, intervalMs) {
    let stopped = false;
    let timeoutId = /** @type {ReturnType<typeof setTimeout> | undefined} */ (undefined);

    const tick = async () => {
        if (stopped) {
            return;
        }
        try {
            await pollOnce();
        } catch (error) {
            console.error("Poll failed:", error);
        }
        if (!stopped) {
            timeoutId = setTimeout(tick, intervalMs);
        }
    };

    void tick();

    return () => {
        stopped = true;
        if (timeoutId !== undefined) {
            clearTimeout(timeoutId);
        }
    };
}
