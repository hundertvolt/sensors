// tests_js/_micropypath.js, the JS reader of the one MICROPYPATH definition: the twin layout as scripts/micropypath.toml
// states it, a text without the line refused by its file's name, and a device's own site in place of frozen_modules.
import { commands } from "vitest/browser";
import { describe, expect, it } from "vitest";
import { LAYOUT_FILE, twinLayout, withSite } from "./_micropypath.js";

describe("the MICROPYPATH layout reader", () => {
    it("reads the twin layout of scripts/micropypath.toml exactly as the file states it", async () => {
        const text = await commands.readFile(LAYOUT_FILE);
        const twin = twinLayout(text, LAYOUT_FILE);
        expect(text.split("\n")).toContain(`twin = "${twin}"`);
        expect(twin.split(":")).toEqual(expect.arrayContaining(["digital_twin", "ext", "frozen_modules"]));
        expect(twin.split(":")).not.toContain("tests");
        expect(twin.split(":").at(-1)).toBe(".frozen");
    });

    it("refuses a text without a twin line, naming the file", () => {
        expect(() => twinLayout('unit = "src:tests:.frozen"\n', "fixture.toml")).toThrow(/fixture\.toml has no twin = "\.\.\." line/u);
        expect(() => twinLayout('# twin = "src:.frozen"\n', "fixture.toml")).toThrow(/fixture\.toml/u);
    });

    it("puts a device's own built site in place of the frozen_modules entry, and refuses a layout without one", async () => {
        const site = "build/generated_html/fixture-device";
        const twin = twinLayout(await commands.readFile(LAYOUT_FILE), LAYOUT_FILE).split(":");
        expect(withSite(twin.join(":"), site).split(":")).toEqual(twin.map((entry) => (entry === "frozen_modules" ? site : entry)));
        expect(withSite("src:frozen_modules:.frozen", site)).toBe(`src:${site}:.frozen`);
        expect(() => withSite("src:ext:.frozen", site)).toThrow(/frozen_modules/u);
    });
});
