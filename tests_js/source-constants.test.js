// Tests tests_js/_source_constants.js: each reader finds the constants the tests read from real modules, and throws
// on a name a module does not declare.
import { describe, expect, it } from "vitest";
import definitionsSource from "../js/definitions.js?raw";
import mockServerSource from "../js/mock-server.js?raw";
import pollManagerSource from "../js/poll-manager.js?raw";
import { readIntConst, readObjectConst } from "./_source_constants.js";

describe("readIntConst", () => {
    it("reads a module's integer constants", () => {
        expect(readIntConst(definitionsSource, "SUPPORTED_SCHEMA_MAJOR")).toBe(1);
        expect(readIntConst(pollManagerSource, "DEFAULT_TIMEOUT_MS")).toBeGreaterThan(0);
    });

    it("reads the poll loop's back-off ceiling", () => {
        expect(readIntConst(pollManagerSource, "POLL_BACKOFF_MAX_MS")).toBeGreaterThan(0);
    });

    it("reads a negative literal and takes no expression or nested declaration", () => {
        expect(readIntConst("const A = -3;\n", "A")).toBe(-3);
        expect(() => readIntConst("const A = 2 ** 3;\n", "A")).toThrow("no const A in source");
        expect(() => readIntConst("function f() {\n    const A = 1;\n}\n", "A")).toThrow("no const A in source");
    });

    it("throws on a name the module does not declare", () => {
        expect(() => readIntConst(definitionsSource, "NO_SUCH_CONSTANT")).toThrow("no const NO_SUCH_CONSTANT in source");
    });
});

describe("readObjectConst", () => {
    it("reads the mock's envelope code table", () => {
        const codes = readObjectConst(mockServerSource, "STANDARD_CODES");
        expect(codes["0"]).toBe("Command executed");
        expect(codes["404"]).toBe("Not found");
    });

    it("reads every code of a table spread over lines, without evaluating it", () => {
        const source = 'const T = {\n    0: "zero",\n    413: "Payload too large",\n};\n';
        expect(readObjectConst(source, "T")).toEqual({ 0: "zero", 413: "Payload too large" });
    });

    it("throws on a name the module does not declare", () => {
        expect(() => readObjectConst(mockServerSource, "NO_SUCH_TABLE")).toThrow("no const NO_SUCH_TABLE in source");
    });
});
