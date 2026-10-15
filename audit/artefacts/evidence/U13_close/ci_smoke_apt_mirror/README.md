# web-cross-browser-smoke cancelled on 2949ed9 (U12's push): the runner's apt mirror, not a test

Run 37643676687 (pull_request, 2949ed9): every job green except `web-cross-browser-smoke`, cancelled at its 25-minute
`timeout-minutes` inside "Install WebKit, Edge, and Firefox+geckodriver"; "Run cross-browser smoke check" never started.
`step_timings.txt` has every step of the same job in three runs of the day:

| run | Install Playwright OS deps | Install WebKit, Edge, Firefox | job |
|---|---|---|---|
| 37595858830 (08:49) | 13 s | 9 s | success |
| 37638089345 (14:40) | 4 min 55 s | 18 min 16 s | success |
| 37643676687 (15:29) | 6 min 10 s | > 18 min 29 s, cancelled | cancelled |

Log tail of the cancelled step (job 112871025004, read through the GitHub MCP job-log tool): `54 newly installed ...
Need to get 43.4 MB of archives`, then `Get:n http://azure.archive.ubuntu.com/ubuntu ...` lines at a few seconds per
10-200 kB package (e.g. `gstreamer1.0-plugins-good` 2236 kB from 15:38:45 to 15:43:03), the last `Get:54 ...
libwebkit2gtk-4.1-0 ... [25.5 MB]` at 15:45:15, then `##[error]The operation was canceled.` at 15:54:40.

The provider's status page could not be read from this session (egress-blocked), so the flake rule's "provider
confirms an outage" half is unmet and this is not called a flake. One re-run of the job with no code change passed
(run attempt 2: the two apt steps 14 s and 12 s, the smoke check 4 min 25 s, green). The exposure itself is OF-48 (U28).
