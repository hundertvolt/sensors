// The JS gates' marker pair and output drain (tests_js/_memory_markers.js): both spellings are found,
// the suite's own injection wording is not, and trimming the kept tail never drops a marker line.
import { describe, expect, test } from "vitest";
import { MEMORY_ERROR_MARKERS, createOutputDrain, memoryMarkerLines } from "./_memory_markers.js";

describe("memoryMarkerLines", () => {
    test("is the canonical pair every other gate holds", () => {
        expect(MEMORY_ERROR_MARKERS).toEqual(["MemoryError", "memory allocation failed"]);
    });

    test("finds both spellings and quotes each whole line", () => {
        const text = "boot ok\nTraceback: MemoryError: \n[E] SYSTEM: memory allocation failed, allocating 64 bytes\nserving";
        expect(memoryMarkerLines(text)).toEqual(["Traceback: MemoryError: ", "[E] SYSTEM: memory allocation failed, allocating 64 bytes"]);
    });

    test("ignores the suite's own injection wording", () => {
        expect(memoryMarkerLines("[E] SGP40: simulated allocation failure\n")).toEqual([]);
    });
});

describe("createOutputDrain", () => {
    test("keeps a marker line that the bounded tail has since trimmed away", () => {
        const drain = createOutputDrain(64);
        drain.feed("stdout", "[E] NTP: memory allocation failed, allocating 32 bytes\n");
        for (let i = 0; i < 20; i += 1) {
            drain.feed("stdout", `ordinary line ${i}\n`);
        }
        expect(drain.text()).not.toContain("memory allocation failed");
        expect(drain.text()).toMatch(/^\[\d+ earlier characters dropped\]\n/u);
        expect(drain.markerLines()).toEqual(["[E] NTP: memory allocation failed, allocating 32 bytes"]);
    });

    test("finds a marker split across chunks, and one still without its newline", () => {
        const drain = createOutputDrain();
        drain.feed("stderr", "[E] WIFI: memory alloc");
        drain.feed("stdout", "unrelated\n");
        drain.feed("stderr", "ation failed\nMemoryError at exit");
        expect(drain.markerLines()).toEqual(["[E] WIFI: memory allocation failed", "MemoryError at exit"]);
    });

    test("finds a marker straddling the break of a line longer than the whole tail", () => {
        const drain = createOutputDrain(64);
        drain.feed("stdout", `${"x".repeat(60)}memory alloc`);
        drain.feed("stdout", "ation failed and more\n");
        expect(drain.markerLines()).toHaveLength(1);
        expect(drain.markerLines()[0]).toContain("memory allocation failed");
    });

    test("keeps lines from both streams whole and in arrival order", () => {
        const drain = createOutputDrain();
        drain.feed("stdout", "a1\na2-");
        drain.feed("stderr", "b1\n");
        drain.feed("stdout", "end\n");
        expect(drain.text()).toBe("a1\nb1\na2-end\n");
    });

    test("counts the marker lines beyond its quoting bound rather than dropping them unseen", () => {
        const drain = createOutputDrain();
        for (let i = 0; i < 60; i += 1) {
            drain.feed("stdout", `MemoryError ${i}\n`);
        }
        const lines = drain.markerLines();
        expect(lines).toHaveLength(51);
        expect(lines.at(-1)).toBe("[10 more marker lines not quoted]");
    });
});
