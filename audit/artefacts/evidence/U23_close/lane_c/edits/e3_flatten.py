import pathlib, sys
p = pathlib.Path(sys.argv[1])
lines = p.read_text().split("\n")
heads = {
    '        describe("the DNS fallback\'s Clear", () => {': ("DNS fallback Clear: ", "CLEAR"),
    '        describe("the Altitude warning", () => {': ("the Altitude warning ", "ALTITUDE"),
    '        describe("reads the device\'s values before deciding what changed", () => {': ("", "REFRESH"),
}
out = []
i = 0
while i < len(lines):
    line = lines[i]
    if line in heads:
        prefix, tag = heads[line]
        # find the matching close at the same indent
        j = i + 1
        while lines[j] != "        });":
            j += 1
        body = lines[i + 1 : j]
        for b in body:
            b2 = b[4:] if b.startswith("            ") else b
            if prefix and b2.startswith('        it("'):
                b2 = '        it("' + prefix + b2[len('        it("'):]
            if prefix and b2.startswith('        it.each('):
                pass
            out.append(b2)
        i = j + 1
        continue
    out.append(line)
    i += 1
s = "\n".join(out)
# The two block-local fixtures need distinct names once flattened into one scope.
s = s.replace('''        /** @type {import("../js/definitions.js").Section} */
        const section = {
            key: "networking",
            label: "Networking",
            rest: { get: "/networking", put: "/networking" },
            pollGroup: "settings",
            groups: [{ key: "dns", label: "DNS", submit: true, fields: [{ key: "DNSFallback", label: "DNS Fallback", kind: "string", shape: "ipv4List", clearable: true }] }],
        };
        const defs = withSection(section);
        const data = { ...DATA, networkingConfig: { DNSFallback: "1.1.1.1" } };
''', '''        /** @type {import("../js/definitions.js").Section} */
        const DNS_SECTION = {
            key: "networking",
            label: "Networking",
            rest: { get: "/networking", put: "/networking" },
            pollGroup: "settings",
            groups: [{ key: "dns", label: "DNS", submit: true, fields: [{ key: "DNSFallback", label: "DNS Fallback", kind: "string", shape: "ipv4List", clearable: true }] }],
        };
        const DNS_DATA = { ...DATA, networkingConfig: { DNSFallback: "1.1.1.1" } };
''')
s = s.replace('''                uninstall = installMockFetch(defs, data);''', '''                uninstall = installMockFetch(withSection(DNS_SECTION), DNS_DATA);''')
s = s.replace('''            uninstall = installMockFetch(defs, data);''', '''            uninstall = installMockFetch(withSection(DNS_SECTION), DNS_DATA);''')
s = s.replace('''            stop = renderSection(defs, section, main);
            await waitFor(() => main.querySelector("[data-clear-for]") !== null);''', '''            stop = renderSection(withSection(DNS_SECTION), DNS_SECTION, main);
            await waitFor(() => main.querySelector("[data-clear-for]") !== null);''')
s = s.replace('''        /** @type {import("../js/definitions.js").Section} */
        const section = {
            ...getSection("sensors"),
            groups: [
                {
                    key: "SCD30",
                    label: "SCD30",
                    submit: true,
                    fields: [
                        { key: "AmbPres", label: "Ambient Pressure", unit: "hPa", kind: "number", alwaysExecuted: true },
                        { key: "Altitude", label: "Altitude", unit: "m", kind: "number", ignoredWhenSet: "AmbPres" },
                    ],
                },
            ],
        };
''', '''        /** @type {import("../js/definitions.js").Section} */
        const ALTITUDE_SECTION = {
            ...getSection("sensors"),
            groups: [
                {
                    key: "SCD30",
                    label: "SCD30",
                    submit: true,
                    fields: [
                        { key: "AmbPres", label: "Ambient Pressure", unit: "hPa", kind: "number", alwaysExecuted: true },
                        { key: "Altitude", label: "Altitude", unit: "m", kind: "number", ignoredWhenSet: "AmbPres" },
                    ],
                },
            ],
        };
''')
s = s.replace('''        ])("is %s", async (_title, baseline, pressureTyped, altitudeSteps, shown) => {
            uninstall = installMockFetch(withSection(section), { ...DATA, sensorsConfig: { SCD30: { AmbPres: baseline, Altitude: 0 } } });
            const main = mount();
            stop = renderSection(withSection(section), section, main);''', '''        ])("the Altitude warning is %s", async (_title, baseline, pressureTyped, altitudeSteps, shown) => {
            uninstall = installMockFetch(withSection(ALTITUDE_SECTION), { ...DATA, sensorsConfig: { SCD30: { AmbPres: baseline, Altitude: 0 } } });
            const main = mount();
            stop = renderSection(withSection(ALTITUDE_SECTION), ALTITUDE_SECTION, main);''')
p.write_text(s)
