/**
 * Single-flight request coordinator - every fetch in the app goes through the one shared
 * instance below rather than calling fetch() directly. See SPECIFICATION.md Part H.4's "Poll
 * coordination" row for why, and for the per-request timeout's own rationale.
 */

/** Per-request timeout; see the "Per-request timeout value" row of SPECIFICATION.md Part H.4. */
// @tunable web.outer_cap_s = 15000
const DEFAULT_TIMEOUT_MS = 15000;

/** Longest wait between retries of a failing poll. */
// @tunable web.poll_backoff_max_ms = 60000
const POLL_BACKOFF_MAX_MS = 60000;

/** @typedef {{isHidden: () => boolean, onChange: (cb: () => void) => () => void}} Visibility */

/** @type {Visibility} */
const ALWAYS_VISIBLE = {
    isHidden: () => false,
    onChange: () => () => { /* an always-visible source never changes */ },
};

class PollManager {
    /** @type {Promise<void>} */
    #queue = Promise.resolve();

    /**
     * Run one HTTP request, queued behind any request already in flight. See SPECIFICATION.md
     * Part H.4's "Poll coordination" row for the timeout/queue-advance rationale.
     * @param {string} url
     * @param {RequestInit} [init]
     * @param {number} [timeoutMs]
     * @param {AbortSignal} [signal] ends the request, queued or in flight
     * @param {AbortSignal} [queueSignal] drops the request while it waits its turn; once sent, it no longer ends it
     * @returns {Promise<{ok: boolean, status: number, body: unknown}>}
     */
    request(url, init, timeoutMs = DEFAULT_TIMEOUT_MS, signal = undefined, queueSignal = undefined) {
        const run = async () => {
            if (signal?.aborted || queueSignal?.aborted) {
                throw new DOMException("Aborted", "AbortError");
            }
            const { ok, status, text } = await fetchTextWithTimeout(url, init, timeoutMs, signal);
            let body;
            try {
                body = text.length > 0 ? JSON.parse(text) : null;
            } catch (error) {
                if (!ok) {
                    // A non-ok answer that is not JSON (a plain static server's 404 page): its status is the failure.
                    return { ok, status, body: null };
                }
                // A non-empty but unparseable body - a truncated/corrupted transmission, or a
                // non-JSON response from something other than this app's own backend.
                throw new Error(`Response from ${url} was not valid JSON (likely a corrupted or truncated transmission)`, { cause: error });
            }
            return { ok, status, body };
        };

        const scheduled = this.#queue.then(run, run);
        this.#queue = scheduled.then(
            () => undefined,
            () => undefined,
        );
        return scheduled;
    }
}

/**
 * fetch() bounded by one timeout covering the whole request, body included.
 * @param {string} url
 * @param {RequestInit | undefined} init
 * @param {number} timeoutMs
 * @param {AbortSignal | undefined} signal
 * @returns {Promise<{ok: boolean, status: number, text: string}>}
 */
async function fetchTextWithTimeout(url, init, timeoutMs, signal) {
    const timeout = new AbortController();
    const timeoutId = setTimeout(() => timeout.abort(), timeoutMs);
    const combined = signal === undefined ? timeout.signal : AbortSignal.any([timeout.signal, signal]);
    // Each await also races the abort itself, so a fetch() or body read that ignores its signal still ends.
    /** @type {() => void} */
    let onAbort = () => { /* replaced below, before any await */ };
    /** @type {Promise<never>} */
    const aborted = new Promise((_resolve, reject) => {
        onAbort = () => reject(combined.reason);
        combined.addEventListener("abort", onAbort, { once: true });
    });
    try {
        const response = await Promise.race([fetch(url, { ...init, signal: combined }), aborted]);
        let text;
        try {
            text = await Promise.race([response.text(), aborted]);
        } catch (error) {
            if (combined.aborted) {
                throw error;
            }
            // The connection dropped mid-stream, after headers but before the full body
            // arrived - a genuine transmission error, not a request the server rejected.
            throw new Error(`Connection to ${url} was interrupted while reading the response`, { cause: error });
        }
        return { ok: response.ok, status: response.status, text };
    } catch (error) {
        if (timeout.signal.aborted) {
            throw new Error(`Request to ${url} timed out after ${timeoutMs}ms`, { cause: error });
        }
        throw error;
    } finally {
        clearTimeout(timeoutId);
        combined.removeEventListener("abort", onAbort);
    }
}

export const pollManager = new PollManager();

/**
 * Self-scheduling poll loop: the next tick is scheduled only after pollOnce() settles, `intervalMs`
 * later, or after a failure min(intervalMs * 2^(k-1), POLL_BACKOFF_MAX_MS) for the k-th consecutive
 * failure; nothing runs while the page is hidden, and one tick runs on becoming visible.
 * @param {() => Promise<void>} pollOnce
 * @param {number} intervalMs
 * @param {{visibility?: Visibility, onError?: (error: unknown) => void, stopAfterSuccess?: boolean}} [options]
 * @returns {() => void}
 */
export function startPolling(pollOnce, intervalMs, options = {}) {
    const { visibility = ALWAYS_VISIBLE, onError, stopAfterSuccess = false } = options;
    let stopped = false;
    let inFlight = false;
    let failures = 0;
    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let timeoutId;
    const unsubscribe = visibility.onChange(() => {
        if (stopped) {
            return;
        }
        if (visibility.isHidden()) {
            clearTimeout(timeoutId);
            timeoutId = undefined;
        } else if (!inFlight && timeoutId === undefined) {
            tick();
        }
    });

    function stop() {
        if (!stopped) {
            stopped = true;
            clearTimeout(timeoutId);
            unsubscribe();
        }
    }

    async function tick() {
        timeoutId = undefined;
        inFlight = true;
        let succeeded = false;
        try {
            await pollOnce();
            succeeded = true;
            failures = 0;
        } catch (error) {
            if (intervalMs * 2 ** (failures - 1) < POLL_BACKOFF_MAX_MS) {
                failures += 1;
            }
            onError?.(error);
        } finally {
            inFlight = false;
            if (succeeded && stopAfterSuccess) {
                stop();
            } else if (!stopped && !visibility.isHidden()) {
                const delayMs = failures === 0 ? intervalMs : Math.min(intervalMs * 2 ** (failures - 1), POLL_BACKOFF_MAX_MS);
                timeoutId = setTimeout(tick, delayMs);
            }
        }
    }

    if (!visibility.isHidden()) {
        tick();
    }
    return stop;
}
