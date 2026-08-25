/**
 * Single-flight request coordinator - every fetch in the app goes through the one shared
 * instance below rather than calling fetch() directly. See WEBSITE_PLAN.md §4 "Poll
 * coordination" for why, and §10 session 3 for the per-request timeout's own rationale.
 */

/** Default per-request timeout; see WEBSITE_PLAN.md §10 session 3. */
export const DEFAULT_TIMEOUT_MS = 15000;

/**
 * fetch() bounded by an AbortController timeout, freeing the connection and rejecting instead of
 * waiting forever on a hung one. Used by `PollManager.request()` below and directly by one-off
 * startup fetches outside the single-flight queue (`definitions.js`/`app.js`) that still need the
 * same never-hang guarantee.
 * @param {string} url
 * @param {RequestInit} [init]
 * @param {number} [timeoutMs]
 * @returns {Promise<Response>}
 */
export async function fetchWithTimeout(url, init, timeoutMs = DEFAULT_TIMEOUT_MS) {
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
        return await Promise.race([fetch(url, { ...init, signal: controller.signal }), timedOut]);
    } finally {
        clearTimeout(timeoutId);
    }
}

class PollManager {
    /** @type {Promise<void>} */
    #queue = Promise.resolve();

    /** @type {number} */
    #activeCount = 0;

    /** @returns {boolean} true while a request is in flight. */
    get isBusy() {
        return this.#activeCount > 0;
    }

    /**
     * Run one HTTP request, queued behind any request already in flight. See WEBSITE_PLAN.md §4
     * "Poll coordination" for the timeout/queue-advance rationale.
     * @param {string} url
     * @param {RequestInit} [init]
     * @param {number} [timeoutMs]
     * @returns {Promise<{ok: boolean, status: number, body: unknown}>}
     */
    request(url, init, timeoutMs = DEFAULT_TIMEOUT_MS) {
        const run = async () => {
            this.#activeCount += 1;
            try {
                const response = await fetchWithTimeout(url, init, timeoutMs);
                let text;
                try {
                    text = await response.text();
                } catch (error) {
                    // The connection dropped mid-stream, after headers but before the full body
                    // arrived - a genuine transmission error, not a request the server rejected.
                    throw new Error(`Connection to ${url} was interrupted while reading the response`, { cause: error });
                }
                let body;
                try {
                    body = text.length > 0 ? JSON.parse(text) : null;
                } catch (error) {
                    // A non-empty but unparseable body - a truncated/corrupted transmission, or a
                    // non-JSON response from something other than this app's own backend.
                    throw new Error(`Response from ${url} was not valid JSON (likely a corrupted or truncated transmission)`, { cause: error });
                }
                return { ok: response.ok, status: response.status, body };
            } finally {
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
            // Defensive only: today tick() is only ever invoked by void tick() below (stopped
            // starts false) or by the setTimeout scheduled just below, itself gated on !stopped -
            // kept in case a future caller invokes tick() directly.
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
