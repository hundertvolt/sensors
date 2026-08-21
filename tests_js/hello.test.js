import { describe, expect, it } from "vitest";
import { renderHello } from "../js/hello.js";

describe("renderHello", () => {
    it("sets textContent on a real DOM element", () => {
        const target = document.createElement("p");
        document.body.appendChild(target);

        const result = renderHello(target, "wozi");

        expect(result).toBe("Hello, wozi!");
        expect(target.textContent).toBe("Hello, wozi!");

        target.remove();
    });
});
