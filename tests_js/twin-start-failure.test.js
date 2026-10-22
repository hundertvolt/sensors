// The live commands stop waiting for a twin the moment it failed to spawn or exited, naming why,
// rather than timing out with no cause (tests_js/_twin_start_failure.js).
import { describe, expect, test } from "vitest";
import { twinStartFailure } from "./_twin_start_failure.js";

describe("twinStartFailure", () => {
    test("a running twin is no failure", () => {
        expect(twinStartFailure({ spawnError: null, exitCode: null, signalCode: null })).toBeNull();
    });

    test("a spawn error is named with its message", () => {
        expect(twinStartFailure({ spawnError: new Error("spawn micropython ENOENT"), exitCode: null, signalCode: null })).toBe("the digital twin failed to start: spawn micropython ENOENT");
    });

    test("an exit before serving names its code and signal", () => {
        expect(twinStartFailure({ spawnError: null, exitCode: 1, signalCode: null })).toBe("the digital twin exited before serving (exit code 1, signal none)");
        expect(twinStartFailure({ spawnError: null, exitCode: null, signalCode: "SIGKILL" })).toBe("the digital twin exited before serving (exit code none, signal SIGKILL)");
    });
});
