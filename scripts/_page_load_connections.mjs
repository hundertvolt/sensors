// Sorts the connections one page load opened by their first request: the document and its assets are the page's
// own (SPECIFICATION.md H.7), any other path is a data request the page then makes, and a connection that carried
// no request is a browser's speculative spare socket, counted on its own because it still holds a device slot.

/**
 * @param {(string | null)[]} firstRequests each connection's first request line, or null when it sent none
 * @returns {{page: number, speculative: number, data: number}}
 */
export function classifyConnections(firstRequests) {
    let page = 0;
    let speculative = 0;
    let data = 0;
    for (const line of firstRequests) {
        if (line === null) {
            speculative += 1;
            continue;
        }
        const path = (line.split(" ")[1] ?? "").split("?")[0] ?? "";
        if (path === "/" || /\.[A-Za-z0-9]+$/.test(path)) {
            page += 1;
        } else {
            data += 1;
        }
    }
    return { page, speculative, data };
}
