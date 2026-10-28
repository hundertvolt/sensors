"""Standing rules over .github/workflows/ci.yml and its composite actions, read as text (no pyyaml): gating, web
filter, pins, composite actions, derived device matrices, values reaching `run:` only via `env:`, executable scripts,
bounded installs, the Playwright cache's runner identity, the apt cache around each install (B.10.1)."""

import re
from pathlib import Path

from _repo_scan import git_lines

_REPO = Path(__file__).resolve().parent.parent
_CI = _REPO / ".github" / "workflows" / "ci.yml"
_ACTIONS = _REPO / ".github" / "actions"
_TOOLCHAIN_ACTION = _ACTIONS / "setup-micropython-toolchain" / "action.yml"
_UV_SYNC_ACTION = _ACTIONS / "uv-sync" / "action.yml"
_TOOLCHAIN_USES = "uses: ./.github/actions/setup-micropython-toolchain"
_UV_SYNC_USES = "uses: ./.github/actions/uv-sync"
_PLAYWRIGHT_ACTION = _ACTIONS / "playwright-chromium" / "action.yml"
_APT_RESTORE_ACTION = _ACTIONS / "apt-cache-restore" / "action.yml"
_APT_SAVE_ACTION = _ACTIONS / "apt-cache-save" / "action.yml"
_PLAYWRIGHT_USES = "uses: ./.github/actions/playwright-chromium"
_APT_RESTORE_USES = "uses: ./.github/actions/apt-cache-restore"
_APT_SAVE_USES = "uses: ./.github/actions/apt-cache-save"
_WEB_TEST_JOBS = ("web-unit-tests", "web-put-matrix", "web-coverage", "web-cross-browser-smoke")
_APT_PACKAGES = 'versions["toolchain"]["apt_packages"]'
_CACHE_ACTION = re.compile(r"uses: actions/cache(?:/restore|/save)?@(\S+)")
_SUCCESS_GATED = "success-gated on purpose"
# CLAUDE.md's carriers: each needs a job for order or cache reuse only, so a red job before it never skips it.
_ORDER_ONLY = ("unit-tests", "unit-tests-gc-threshold", "firmware-build-verify", "web-unit-tests")
# Everything the web tier's tests read: the site and its tooling, the live twin's backend, the Python environment and CI.
_WEB_INPUTS = (
    "html/**", "js/**", "tests_js/**", "mockdata/**", "scripts/**", "src/**", "buildgen/**", "devices/**", "digital_twin/**",
    "toolchain/**", "ext/**", "package.json", "package-lock.json", "eslint.config.js", "tsconfig*.json", "vitest.config.js",
    ".htmlvalidate.json", ".stylelintrc.json", ".nvmrc", "pyproject.toml", "uv.lock", ".github/workflows/ci.yml", ".github/actions/**",
    "tests_scripts/test_html_validate_config.py",
)
_TOOLCHAIN_INPUTS = ("toolchain/versions.toml", "toolchain/setup_toolchain.py", "toolchain/micropython_overrides.py")
_GATING_RUNS = ("scripts/test.sh", "npm run test", "node scripts/cross_browser_smoke.mjs", "scripts/run_digital_twin_ci.sh", "uv run pytest")
_BUILD_BLOCK = ("setup_toolchain.py setup", "build-standard/micropython", "_unix_port.sh ensure")
_DEVICE_MATRIX = "${{ fromJSON(needs.devices.outputs.list) }}"
_SHA_PIN = re.compile(r"@[0-9a-f]{40} # v\d+\.\d+\.\d+$")
_JOB_KEY = re.compile(r"^  ([a-z][\w-]*):$", re.MULTILINE)
_ENV_PREFIX = re.compile(r"^(?:[A-Z_][A-Z0-9_]*=\S*\s+)+")
_HTML_VALIDATE_CHECK = "tests_scripts/test_html_validate_config.py"
_IDENT_ID = re.compile(r"^\s+(?:- )?id: ident$", re.MULTILINE)
# A repo script a `run:` line runs as a command: at a line start, after `$(`, `;`, `&`, `|`, `(` or `sudo`, past any VAR=value.
_SCRIPT_COMMAND = re.compile(r"(?:^|[;&|(]|\$\(|\bsudo\s)\s*(?:[A-Z_][A-Z0-9_]*=\S*\s+)*(?:\./)?(scripts/[\w./-]+)")


def _action_steps(path: Path) -> "list[str]":
    text = path.read_text(encoding="utf-8")
    return _steps(text[text.index("\n  steps:\n") :], 4)


def _ci() -> str:
    return _CI.read_text(encoding="utf-8")


def _comments(job: str) -> "list[str]":
    # Comment lines inside the job: a comment above the next job's key (indent 2) belongs to that one's header.
    return [line.strip() for line in job.splitlines() if line.startswith("    ") and line.strip().startswith("#")]


def _description(path: Path) -> str:
    found = re.search(r"^description: >\n((?:  .*\n)*)", path.read_text(encoding="utf-8"), re.MULTILINE)
    assert found, f"{path.relative_to(_REPO)} has no folded description: block"
    return found.group(1)


def _field(job: str, name: str) -> str:
    # A job-level scalar (`if`, `needs`, `timeout-minutes`), or "".
    found = re.search(rf"^    {name}: (.*)$", job, re.MULTILINE)
    return found.group(1) if found else ""


def _jobs() -> "dict[str, str]":
    # Each job's text from its key line to the next job's key line.
    text = _ci()
    body = text[text.index("\njobs:\n") :]
    keys = list(_JOB_KEY.finditer(body))
    jobs = {key.group(1): body[key.start() : keys[i + 1].start() if i + 1 < len(keys) else len(body)] for i, key in enumerate(keys)}
    # A floor: a reshaped file that parses into no jobs, or not into jobs, must fail every rule rather than pass it empty.
    assert {"web-changes", "devices", "unit-tests"} <= set(jobs) and all("runs-on:" in job for job in jobs.values()), sorted(jobs)
    return jobs


def _needs(job: str) -> "list[str]":
    return [name.strip() for name in _field(job, "needs").strip("[]").split(",") if name.strip()]


def _run_lines(step: str) -> "list[str]":
    # The command lines of a step's `run:`, a block scalar's lines dedented, a single line as given.
    found = re.search(r"^([ ]*(?:- )?)run: (.*)$", step, re.MULTILINE)
    if not found:
        return []
    if found.group(2).strip() not in {"|", ">"}:
        return [found.group(2).strip()]
    rest = step[found.end() + 1 :].splitlines()
    indent = len(found.group(1))
    body = []
    for line in rest:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line.strip())
    return [line for line in body if line and not line.startswith("#")]


def _step_lines(step: str) -> "list[str]":
    # A step's lines stripped and its comments dropped, so one step at two indents compares equal.
    return [line.strip() for line in step.splitlines() if line.strip() and not line.strip().startswith("#")]


def _steps(text: str, indent: int) -> "list[str]":
    # Each list item at that indent (`      - ` in a job, `    - ` in a composite action), with its body.
    starts = [m.start() for m in re.finditer(rf"^{' ' * indent}- ", text, re.MULTILINE)]
    return [text[start : starts[i + 1] if i + 1 < len(starts) else len(text)] for i, start in enumerate(starts)]


def _strategy(job: str) -> str:
    found = re.search(r"^    strategy:\n((?:      .*\n)*)", job, re.MULTILINE)
    return found.group(1) if found else ""


def test_every_needs_edge_is_read_ungated_or_stated_success_gated() -> None:
    # A needs: edge success-gates its job by default: kept only where the job reads the needed job's output or result,
    # or says so in a comment; an edge for order or cache reuse carries `!cancelled()` (CLAUDE.md). fail-fast never counts.
    problems = []
    for name, job in _jobs().items():
        condition = _field(job, "if")
        stated = any(_SUCCESS_GATED in comment.lower() for comment in _comments(job))
        for needed in _needs(job):
            read = re.search(rf"needs\.{re.escape(needed)}\.(?:outputs|result)\b", condition + _strategy(job))
            if not (read or "!cancelled()" in condition or stated):
                problems.append(f"{name} needs {needed}: add `!cancelled()` to its if:, or a comment inside the job saying it is {_SUCCESS_GATED!r} and why")
    assert not problems, "\n".join(problems)


def test_the_order_only_jobs_carry_not_cancelled_and_the_twin_e2e_stays_gated() -> None:
    jobs = _jobs()
    missing = [name for name in _ORDER_ONLY if "!cancelled()" not in _field(jobs[name], "if")]
    assert not missing, f"these jobs need their predecessor for order or cache only - add `!cancelled()` to their if: {missing}"
    twin = jobs["digital-twin-e2e"]
    assert "unit-tests" in _needs(twin), "digital-twin-e2e must need unit-tests: fail-fast is its stated intent"
    assert "!cancelled()" not in _field(twin, "if"), "digital-twin-e2e is success-gated on purpose - drop `!cancelled()` from its if:"


def test_the_web_filter_lists_every_input_and_compares_against_the_last_green_commit() -> None:
    job = _jobs()["web-changes"]
    listed = re.findall(r"^\s+- '([^']+)'$", job[job.index("filters: |") :], re.MULTILINE)
    missing = [path for path in _WEB_INPUTS if path not in listed]
    assert not missing, f"web-changes: the web filter misses {missing} - a change there would not run the web tier"
    base = re.search(r"^\s+base: (.*)$", job, re.MULTILINE)
    assert base and "steps.base.outputs.sha" in base.group(1), "web-changes: the filter's base: must read steps.base.outputs.sha (the last green commit)"
    output = re.search(r"^      web: (.*)$", job, re.MULTILINE)
    assert output and "github.event_name == 'push'" in output.group(1) and "steps.base.outputs.sha == ''" in output.group(1) and "'true'" in output.group(1), (
        "web-changes: with no green run found on a push, the web output must fall back to 'true'"
    )
    (step,) = [s for s in _steps(job, 6) if re.search(r"^\s+id: base$", s, re.MULTILINE)]
    assert "github.event_name == 'push'" in step, "web-changes: the base step runs on a push only (a pull_request ignores base)"
    run = "\n".join(_run_lines(step))
    assert "${{" not in run, "web-changes: the base step's values reach its run: through env: only"
    assert re.search(r"\$\(timeout \S+ gh api .*\|\| sha=\"\"$", run, re.MULTILINE), "web-changes: bound the gh lookup and fall back to an empty sha, so a hung API never fails the job"


def test_every_third_party_action_is_pinned_to_a_commit_with_its_version() -> None:
    unpinned = []
    for path in (_CI, *_ACTIONS.glob("*/action.yml")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            used = re.search(r"uses: (\S+.*)$", line)
            if used and not used.group(1).startswith(("actions/", "./")) and not _SHA_PIN.search(line):
                unpinned.append(f"{path.relative_to(_REPO)}:{number}: {used.group(1)}")
    assert not unpinned, f"pin each to its tag's commit with a `# vX.Y.Z` comment: {unpinned}"


def test_the_checkout_stays_shallow_and_without_submodules() -> None:
    text = _ci()
    assert not re.search(r"^\s+(?:fetch-depth|submodules):", text, re.MULTILINE), "ci.yml: remove fetch-depth/submodules - CI checks out shallow and datasheet-free"


def test_no_test_step_hides_its_result_behind_continue_on_error() -> None:
    hidden: list[str] = []
    seen: set[str] = set()
    for name, job in _jobs().items():
        for step in _steps(job, 6):
            commands = [_ENV_PREFIX.sub("", line) for line in _run_lines(step)]
            seen.update(prefix for prefix in _GATING_RUNS for command in commands if command.startswith(prefix))
            if any(command.startswith(_GATING_RUNS) for command in commands) and re.search(r"^\s+continue-on-error:", step, re.MULTILINE):
                hidden.append(f"{name}: {commands[0]}")
    assert seen == set(_GATING_RUNS), f"the scan found no step running {sorted(set(_GATING_RUNS) - seen)} - it has stopped reading the steps"
    assert not hidden, f"a test step's result gates - remove continue-on-error from: {hidden}"


def test_every_value_reaches_a_run_through_env() -> None:
    # An expression expanded inside the script text is zizmor's template injection; env: passes it as data.
    found = []
    for path in (_CI, *_ACTIONS.glob("*/action.yml")):
        text = path.read_text(encoding="utf-8")
        found += [f"{path.relative_to(_REPO)}: {line}" for step in _steps(text, 6 if path == _CI else 4) for line in _run_lines(step) if "${{" in line]
    assert not found, f"pass each value through the step's env: and read the variable: {found}"


def test_the_toolchain_action_keys_on_every_input_and_names_every_caller() -> None:
    key = re.search(r"^\s+key: (.*)$", _TOOLCHAIN_ACTION.read_text(encoding="utf-8"), re.MULTILINE)
    missing = [part for part in (*_TOOLCHAIN_INPUTS, "steps.ident.outputs.id") if not key or part not in key.group(1)]
    problems = [f"the toolchain cache key misses {missing}: a change there would restore stale binaries"] if missing else []
    jobs = _jobs()
    callers = {name for name, job in jobs.items() if _TOOLCHAIN_USES in job}
    named = set(re.findall(r"[a-z][\w-]*", _description(_TOOLCHAIN_ACTION))) & set(jobs)
    if named != callers:
        problems.append(f"the toolchain action's description names {sorted(named)}, but its callers are {sorted(callers)}")
    repeated = [name for name, job in jobs.items() if any(part in job for part in _BUILD_BLOCK)]
    if repeated:
        problems.append(f"these jobs repeat the build-if-missing block - pass `build-unix-port: 'true'` to the action instead: {repeated}")
    assert not problems, "\n".join(problems)


def test_the_toolchain_action_syncs_first_and_builds_through_the_one_probe() -> None:
    steps = _action_steps(_TOOLCHAIN_ACTION)
    assert steps[0].startswith(f"    - {_UV_SYNC_USES}"), "the toolchain action's first step is the uv-sync action, so every caller syncs first"
    builds = [step for step in steps if "inputs.build-unix-port" in step]
    assert len(builds) == 1, "the toolchain action has no single step gated on its build-unix-port input"
    run = "\n".join(_run_lines(builds[0]))
    assert "scripts/_unix_port.sh ensure standard" in run, "the build step builds through scripts/_unix_port.sh ensure standard"
    # A restored cache carries no file capabilities, and every twin binds the local NTP responder's port 123.
    assert "setcap 'cap_net_bind_service=+ep'" in run, "the build step grants the binary cap_net_bind_service"
    web = [name for name, job in _jobs().items() if name.startswith("web-") and _TOOLCHAIN_USES in job and "build-unix-port: 'true'" not in job]
    assert not web, f"these web jobs boot a twin no step of theirs builds - pass `build-unix-port: 'true'`: {web}"


def test_every_job_running_uv_or_a_script_syncs_first_through_an_action() -> None:
    late = []
    for name, job in _jobs().items():
        synced = False
        for step in _steps(job, 6):
            synced = synced or _UV_SYNC_USES in step or _TOOLCHAIN_USES in step
            if not synced and any(re.search(r"\buv\b|\bscripts/", line) for line in _run_lines(step)):
                late.append(f"{name}: {_run_lines(step)[0]}")
                break
    assert not late, f"run the uv-sync action (or the toolchain action) before these steps: {late}"
    assert "pip install uv" not in _ci(), "ci.yml installs uv itself - the uv-sync action installs the pinned one"


def test_both_device_matrices_are_derived_from_the_devices_job() -> None:
    # A literal list would let a new device generate, build and pass locally while CI kept the old set.
    text = _ci()
    matrices = re.findall(r"^\s+device: (.*)$", text, re.MULTILINE)
    assert matrices == [_DEVICE_MATRIX, _DEVICE_MATRIX], f"digital-twin-e2e and firmware-build-verify read `device: {_DEVICE_MATRIX}`, found {matrices}"
    run = "\n".join(line for step in _steps(_jobs()["devices"], 6) for line in _run_lines(step))
    assert "devices/*.toml" in run and "zz_test_" in run, "the devices job globs devices/*.toml and skips the zz_test_ fixtures, as tests_scripts/_devices.py"
    assert "exit 1" in run, "the devices job fails on an empty set rather than run no device"


def test_the_cross_browser_smoke_requires_every_engine() -> None:
    steps = [line for job in _jobs().values() for step in _steps(job, 6) for line in _run_lines(step) if line.startswith("node scripts/cross_browser_smoke.mjs")]
    assert steps == ["node scripts/cross_browser_smoke.mjs --require-all-engines"], f"in CI a missing engine fails the smoke: {steps}"
    key = re.search(r"^\s+key: (cross-browser-firefox-.*)$", _ci(), re.MULTILINE)
    assert key and "hashFiles('scripts/setup_cross_browser_toolchain.sh')" in key.group(1) and "steps.month.outputs.month" in key.group(1), (
        "the floating Firefox's cache key rolls with the installer and monthly, or a cached Firefox ages unseen"
    )


def test_the_web_lint_job_validates_every_built_page() -> None:
    runs = [line for step in _steps(_jobs()["web-lint-and-typecheck"], 6) for line in _run_lines(step)]
    assert "npm run lint:html:built" in runs, "web-lint-and-typecheck: add a step running npm run lint:html:built"


def test_the_web_lint_job_runs_the_html_validate_config_check_required() -> None:
    # The unit-test jobs install no node_modules, so the check skips there: this job installs them and requires it.
    steps = _steps(_jobs()["web-lint-and-typecheck"], 6)
    runs = ["\n".join(_run_lines(step)) for step in steps]
    install = next((i for i, run in enumerate(runs) if run == "npm ci"), len(steps))
    checks = [i for i, step in enumerate(steps) if _HTML_VALIDATE_CHECK in runs[i] and re.search(r'^\s+HTML_VALIDATE_REQUIRED: "1"$', step, re.MULTILINE)]
    assert checks and checks[0] > install, f'web-lint-and-typecheck: after npm ci, run {_HTML_VALIDATE_CHECK} with env: HTML_VALIDATE_REQUIRED: "1"'


def test_every_script_a_run_calls_as_a_command_is_executable_in_git() -> None:
    # CI's checkout takes each file's mode from git, so a script a step runs as a command needs 100755 in the index there.
    called = set()
    for path in (_CI, *_ACTIONS.glob("*/action.yml")):
        steps = [step for job in _jobs().values() for step in _steps(job, 6)] if path == _CI else _action_steps(path)
        called |= {(path.name if path == _CI else path.parent.name, found) for step in steps for line in _run_lines(step) for found in _SCRIPT_COMMAND.findall(line)}
    assert any(script == "scripts/test.sh" for _, script in called), f"the command scan found no `scripts/test.sh` call - it reads nothing: {sorted(called)}"
    modes = {}
    for script in {script for _, script in called}:
        entry = git_lines("ls-files", "-s", "--", script)
        modes[script] = entry[0].split()[0] if entry else "untracked"
    wrong = sorted(f"{where}: {script} ({modes[script]})" for where, script in called if modes[script] != "100755")
    assert not wrong, f"these steps run a script as a command that git does not mark executable - `git update-index --chmod=+x` it, or run it through its interpreter: {wrong}"


def test_every_job_budget_is_tagged() -> None:
    untagged = []
    for name, job in _jobs().items():
        found = re.search(r"^    # @tunable ci\.(\w+)_timeout_min = (\d+)\n    timeout-minutes: (\d+)$", job, re.MULTILINE)
        if not found or found.group(1) != name.replace("-", "_") or found.group(2) != found.group(3):
            untagged.append(name)
    assert not untagged, f"tag each job's timeout-minutes with `# @tunable ci.<job>_timeout_min = <n>` directly above it: {untagged}"


def test_every_playwright_install_is_bounded_and_retried_by_apt() -> None:
    # A stalled runner mirror otherwise holds the job to its own limit and it ends cancelled, naming nothing. A composite
    # step takes no timeout-minutes, so the shared action's install holds its tagged bound through `timeout`.
    jobs = _jobs()
    problems = [f"{name}: installs Playwright itself - call the playwright-chromium action" for name, job in jobs.items() if "npx playwright install" in job]
    users = sorted(name for name, job in jobs.items() if _PLAYWRIGHT_USES in job)
    if users != sorted(_WEB_TEST_JOBS):
        problems.append(f"the playwright-chromium action's callers are {users}, the web jobs that test are {sorted(_WEB_TEST_JOBS)}")
    steps = _action_steps(_PLAYWRIGHT_ACTION)
    runs = ["\n".join(_run_lines(step)) for step in steps]
    bound = [i for i, run in enumerate(runs) if "/etc/apt/apt.conf.d/" in run and "Acquire::Retries" in run and "Acquire::http::Timeout" in run]
    installs = [i for i, run in enumerate(runs) if "npx playwright" in run and "--dry-run" not in run]
    if len(installs) != 1 or len(bound) != 1 or bound[0] > installs[0] or re.search(r"^\s+if:", steps[bound[0]], re.MULTILINE):
        problems.append(f"playwright-chromium: one install step, after an unconditional apt retry and timeout step (installs at {installs}, the bound at {bound})")
    bounds = [i for i, step in enumerate(steps) if re.search(r"^\s+id: bound$", step, re.MULTILINE)]
    tagged = len(bounds) == 1 and re.search(r"^\s+# @tunable ci\.playwright_install_timeout_min = (\d+)\n\s+limit_min=\1$", steps[bounds[0]], re.MULTILINE)
    for i in installs:
        reads = "LIMIT_MIN: ${{ steps.bound.outputs.min }}" in steps[i] and 'timeout "${LIMIT_MIN}m" npx playwright' in runs[i]
        if not (tagged and bounds[0] < i and reads) or "continue-on-error" in steps[i]:
            problems.append('playwright-chromium: the install runs under `timeout "${LIMIT_MIN}m"` from the bound step, tagged ci.playwright_install_timeout_min, and gates')
    assert not problems, "\n".join(problems)


def test_every_playwright_cache_keys_on_the_runner_identity_the_toolchain_action_computes() -> None:
    # A browser restored under another runner image or C library fails at launch; a key read before its step is empty.
    ident = [_step_lines(step) for step in _action_steps(_TOOLCHAIN_ACTION) if _IDENT_ID.search(step)]
    assert len(ident) == 1, "the toolchain action must hold exactly one `id: ident` step, the identity every Playwright cache copies"
    problems = [f"{name}: caches ~/.cache/ms-playwright itself - the playwright-chromium action holds the one cache" for name, job in _jobs().items() if "path: ~/.cache/ms-playwright" in job]
    steps = _action_steps(_PLAYWRIGHT_ACTION)
    idents = [i for i, step in enumerate(steps) if _IDENT_ID.search(step)]
    caches = [i for i, step in enumerate(steps) if "path: ~/.cache/ms-playwright" in step]
    assert caches, "the playwright-chromium action caches no ~/.cache/ms-playwright: a reshaped action must fail this rule rather than pass it empty"
    if [_step_lines(steps[i]) for i in idents] != ident:
        problems.append("playwright-chromium: its one identity step must be the toolchain action's, text unchanged")
    for i in caches:
        key = re.search(r"^\s+key: (.*)$", steps[i], re.MULTILINE)
        if not key or "${{ steps.ident.outputs.id }}" not in key.group(1):
            problems.append("playwright-chromium: the browser cache key misses `${{ steps.ident.outputs.id }}` - a runner-image change would restore a stale browser")
        if not idents or idents[0] > i:
            problems.append("playwright-chromium: no identity step before the browser cache")
    assert not problems, "\n".join(problems)


def _uses_index(steps: "list[str]", uses: str) -> "list[int]":
    return [i for i, step in enumerate(steps) if uses in step]


def test_the_apt_cache_runs_around_every_apt_install() -> None:
    # The mirror check and package cache before apt fetches, the save right after the install whatever came next.
    problems = []
    firmware = _steps(_jobs()["firmware-build-verify"], 6)
    runs = ["\n".join(_run_lines(step)) for step in firmware]
    listed = [i for i, run in enumerate(runs) if _APT_PACKAGES in run and "ensure_apt_packages" not in run]
    installs = [i for i, run in enumerate(runs) if f"st.ensure_apt_packages({_APT_PACKAGES}" in run]
    restore, save = _uses_index(firmware, _APT_RESTORE_USES), _uses_index(firmware, _APT_SAVE_USES)
    if not (len(listed) == len(restore) == len(installs) == len(save) == 1 and listed[0] < restore[0] < installs[0] and save[0] == installs[0] + 1):
        problems.append(f"firmware-build-verify: list the install's packages, then apt-cache-restore, the install, and apt-cache-save right after it (at {listed}, {restore}, {installs}, {save})")
    else:
        if "packages: ${{ steps.apt-packages.outputs.list }}" not in firmware[restore[0]] or not re.search(r"^\s+id: apt-packages$", firmware[listed[0]], re.MULTILINE):
            problems.append("firmware-build-verify: apt-cache-restore's packages are the apt-packages step's list")
        if "if: ${{ !cancelled() }}" not in firmware[save[0]] or "key: ${{ steps.apt.outputs.key }}" not in firmware[save[0]]:
            problems.append("firmware-build-verify: apt-cache-save runs `if: ${{ !cancelled() }}` on apt-cache-restore's key")
    steps = _action_steps(_PLAYWRIGHT_ACTION)
    installs = [i for i, step in enumerate(steps) if "npx playwright" in step and "--dry-run" not in step]
    restore, save = _uses_index(steps, _APT_RESTORE_USES), _uses_index(steps, _APT_SAVE_USES)
    if not (len(restore) == len(installs) == len(save) == 1 and restore[0] < installs[0] and save[0] == installs[0] + 1 and "if: ${{ !cancelled() }}" in steps[save[0]]):
        problems.append("playwright-chromium: apt-cache-restore before the install, apt-cache-save right after it with `if: ${{ !cancelled() }}`")
    elif "playwright-deps: chromium" not in steps[restore[0]]:
        problems.append("playwright-chromium: apt-cache-restore plans Playwright's own chromium list")
    smoke = _jobs()["web-cross-browser-smoke"]
    if "always-check: 'true'" not in smoke:
        problems.append("web-cross-browser-smoke: pass always-check: 'true' - its WebKit install fetches from the same mirror list after the package cache")
    found = [re.search(r"^\s+path: (.*)$", step, re.MULTILINE) for path in (_APT_RESTORE_ACTION, _APT_SAVE_ACTION) for step in _action_steps(path) if "uses: actions/cache/" in step]
    paths = {match.group(1) if match else "(none)" for match in found}
    if len(found) != 2 or len(paths) != 1:
        problems.append(f"the apt cache's restore and save name different paths, so a save is never restored: {sorted(paths)}")
    assert not problems, "\n".join(problems)


def test_every_mirror_check_sizes_its_rate_on_its_own_fetching_bound() -> None:
    # The required rate is the bytes left over the bound of the step that fetches them: tool.apt_step_timeout_s for the
    # firmware set's download attempts, ci.playwright_install_timeout_min for Playwright's install.
    problems = []
    firmware = _steps(_jobs()["firmware-build-verify"], 6)
    listed = [step for step in firmware if re.search(r"^\s+id: apt-packages$", step, re.MULTILINE)]
    restore = [step for step in firmware if _APT_RESTORE_USES in step]
    if len(listed) != 1 or 'print(f"bound-s={st._APT_STEP_TIMEOUT_S}")' not in listed[0]:
        problems.append("firmware-build-verify: the apt-packages step prints bound-s from setup_toolchain's _APT_STEP_TIMEOUT_S")
    if len(restore) != 1 or "bound-s: ${{ steps.apt-packages.outputs.bound-s }}" not in restore[0] or "bound-from: tool.apt_step_timeout_s" not in restore[0]:
        problems.append("firmware-build-verify: apt-cache-restore takes bound-s from apt-packages and names tool.apt_step_timeout_s")
    steps = _action_steps(_PLAYWRIGHT_ACTION)
    restore = [step for step in steps if _APT_RESTORE_USES in step]
    bound = [step for step in steps if re.search(r"^\s+id: bound$", step, re.MULTILINE)]
    if len(bound) != 1 or 's=%s\\n\' "$limit_min" "$((limit_min * 60))"' not in bound[0]:
        problems.append("playwright-chromium: the bound step outputs the install's minutes and their seconds")
    if len(restore) != 1 or "bound-s: ${{ steps.bound.outputs.s }}" not in restore[0] or "bound-from: ci.playwright_install_timeout_min" not in restore[0]:
        problems.append("playwright-chromium: apt-cache-restore takes bound-s from the bound step and names ci.playwright_install_timeout_min")
    check = [step for step in _action_steps(_APT_RESTORE_ACTION) if "ci_apt_cache.py check" in step]
    if len(check) != 1 or '--bound-s "$BOUND_S" --bound-from "$BOUND_FROM"' not in check[0] or "BOUND_S: ${{ inputs.bound-s }}" not in check[0]:
        problems.append("apt-cache-restore: the check passes its bound-s and bound-from inputs to ci_apt_cache.py check")
    assert not problems, "\n".join(problems)


def test_no_apt_cache_step_can_fail_a_job() -> None:
    # A failed check, restore, save or list edit warns and carries on; only the real install's own failure gates.
    loud = [f"{path.parent.name}: {step.splitlines()[0].strip()}" for path in (_APT_RESTORE_ACTION, _APT_SAVE_ACTION) for step in _action_steps(path) if not re.search(r"^\s+continue-on-error: true$", step, re.MULTILINE)]
    firmware = [step for step in _steps(_jobs()["firmware-build-verify"], 6) if re.search(r"^\s+id: apt-packages$", step, re.MULTILINE)]
    loud += [f"firmware-build-verify: {step.splitlines()[0].strip()}" for step in firmware if "continue-on-error: true" not in step]
    assert firmware, "firmware-build-verify has no apt-packages step: a reshaped job must fail this rule rather than pass it empty"
    assert not loud, f"give these steps `continue-on-error: true` (and a ::warning:: where they fail): {loud}"


def test_every_cache_action_is_one_tag() -> None:
    # actions/cache and its restore and save sub-actions come from one release, as zizmor's ref-pin policy lets them.
    tags = {(path.relative_to(_REPO).as_posix(), tag) for path in (_CI, *_ACTIONS.glob("*/action.yml")) for tag in _CACHE_ACTION.findall(path.read_text(encoding="utf-8"))}
    assert len({tag for _, tag in tags}) == 1, f"pin every actions/cache, actions/cache/restore and actions/cache/save to one tag: {sorted(tags)}"
