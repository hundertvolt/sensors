# The cross-browser smoke's connection count (U8's first CI run, 01e8e3e)

CI's `web-cross-browser-smoke` failed: Chromium, Firefox and Edge counted 3 connections per page load against the
registered 2 (`web.connections_per_page_load`), WebKit 2 (job 112578744662). The proxy counted every connection until
the check ran, after the page had made its first data request.

- `connprobe.mjs`, `connprobe_chromium.json`: a logging proxy in front of a wozi twin, Chromium at both viewports: three
  connections, `GET /`, `GET /js/app.js`, `GET /measurements`, one request each (the device serves one request per
  connection). The page's own footprint (H.7: the document and its script) is 2; the third is the first data request,
  which `web.poll_interval_ms` governs.
- The smoke now records each connection's first request line and counts the page's own connections apart from its data
  requests. `local_smoke_run1/2_before_speculative.log`: with that count, 1 of 12 checks per run still found 3 of the
  page's own, the third carrying no request at all (named in the failure message, which now lists every connection):
  Chromium's speculative spare socket, on 3 of 36 page loads, never two.
- The fix counts that socket on its own (`l0.smoke_speculative_connections_max` = 1, printed every check) and keeps
  the page's own requests at the registered 2. `local_smoke_after_fix.log`: 12/12. Firefox, WebKit and Edge run in CI.
