"""Fault-planting driver: one fault per throwaway copy of a frozen snapshot, the named tests run on it, red/green recorded.

Commands: snapshot WORKTREE SNAP | check SNAP | run SNAP RESUME [--only ID,...] [--stop FILE] | table RESUME | selftest. The plant set is
plant_set.PLANTS; nothing planted is ever written outside /dev/shm/cfr_plant, and the snapshot is verified unchanged.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plant_set import PLANTS  # noqa: E402

S = Path("/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad")
NS = str(S / "u24/ns_xdg.sh")
MP = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
PY = str(S / "wt-base/.venv/bin/python")
NODE_BIN = "/root/pico-toolchain/node/node-v24.22.1-linux-x64/bin"
NODE_MODULES = S / "wt-base/node_modules"
COPY_ROOT = Path("/dev/shm/cfr_plant")
UNIT_PATH = "build/generated_src:src:tests:frozen_modules:.frozen"
EXCLUDE = {".git", "arduino", "audit", "legacy", "datasheets", "node_modules", ".venv", ".mypy_cache", ".ruff_cache", "typings", "__pycache__", ".pytest_cache"}
MARKERS = ("MemoryError", "memory allocation failed")
RUN_TIMEOUT_S = 300
FAIL_RE = re.compile(r"^(FAIL|ABORT) |^FAILED |^E  |\bfailed\b|Traceback|✗|×")


def _manifest(root: Path) -> dict[str, str]:
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def snapshot(worktree: Path, snap: Path) -> None:
    if snap.exists():
        sys.exit(f"{snap} exists: remove it first")
    shutil.copytree(worktree, snap, symlinks=True, ignore=lambda _d, names: [n for n in names if n in EXCLUDE])
    (snap.parent / (snap.name + ".manifest.json")).write_text(json.dumps(_manifest(snap)))
    print(f"snapshot {snap}: {len(_manifest(snap))} files")


def _apply(root: Path, edit: dict) -> str:
    path = root / edit["file"]
    text = path.read_text(encoding="utf-8")
    if "append" in edit:
        path.write_text(text + edit["append"], encoding="utf-8")
        return f"{edit['file']}:EOF + {edit['append'].strip()!r}"
    lines = text.split("\n")
    hits = [i for i, line in enumerate(lines) if re.search(edit["match"], line)]
    want = edit.get("count", 1)
    if len(hits) != want:
        raise ValueError(f"{edit['file']}: {edit['match']!r} matches {len(hits)} lines, expected {want}")
    i = hits[edit.get("nth", 0)]
    old = lines[i]
    if "sub" in edit:
        new = re.sub(edit["sub"][0], edit["sub"][1], old, count=1)
        if new == old:
            raise ValueError(f"{edit['file']}:{i + 1}: sub changed nothing")
        lines[i] = new
    else:
        indent = re.match(r"\s*", old).group(0) + " " * edit.get("indent", 0)
        lines[i + 1:i + 1] = [indent + s for s in edit["insert"]]
    path.write_text("\n".join(lines), encoding="utf-8")
    return f"{edit['file']}:{i + 1}: {old.strip()}"


def check(snap: Path) -> None:
    ids = set()
    for p in PLANTS:
        if p["id"] in ids:
            sys.exit(f"duplicate id {p['id']}")
        ids.add(p["id"])
        work = Path("/dev/shm/cfr_check")
        for e in p.get("edits", []):
            shutil.rmtree(work, ignore_errors=True)
            (work / e["file"]).parent.mkdir(parents=True)
            shutil.copy2(snap / e["file"], work / e["file"])
            print(f"{p['id']:34} {_apply(work, e)[:150]}")
        shutil.rmtree(work, ignore_errors=True)
        for t in p["tests"]:
            if not (snap / t["file"]).exists():
                sys.exit(f"{p['id']}: {t['file']} missing")
    print(f"{len(PLANTS)} plants checked")


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def _ns(cmd: list[str], cwd: Path, env: dict[str, str], log: Path, timeout_s: float = RUN_TIMEOUT_S) -> tuple[int, bool, float]:
    # Its own session, so a timeout kills the whole group (unshare, the namespace script, nice, the interpreter), and
    # a member still alive once the leader is reaped is killed and fails the run (rc 125): nothing outlives a run.
    t0 = time.monotonic()
    with log.open("w") as fh:
        proc = subprocess.Popen(["unshare", "-n", NS, "nice", "-n", "19", *cmd], cwd=cwd, env=env, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            rc, timed_out = proc.wait(timeout=timeout_s), False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            rc, timed_out = 124, True
    for _ in range(50):
        if not _group_alive(proc.pid):
            break
        time.sleep(0.1)
    else:
        os.killpg(proc.pid, signal.SIGKILL)
        with log.open("a") as fh:
            fh.write("plant.py: a process of this run outlived it and was killed\n")
        rc = 125
    return rc, timed_out, round(time.monotonic() - t0, 2)


def _strays() -> list[str]:
    # Every process whose working directory is under COPY_ROOT: none may exist between plants.
    found = []
    for proc in Path("/proc").iterdir():
        try:
            if proc.name.isdigit() and os.readlink(proc / "cwd").startswith(str(COPY_ROOT)):
                found.append(proc.name)
        except OSError:
            continue
    return found


def selftest() -> None:
    # A run that leaves a background child and outlives its timeout: the group kill must leave nothing behind.
    COPY_ROOT.mkdir(parents=True, exist_ok=True)
    log = COPY_ROOT / "selftest.log"
    rc, timed_out, _ = _ns(["sh", "-c", "sleep 300 & sleep 300"], COPY_ROOT, dict(os.environ), log, timeout_s=2)
    assert (rc, timed_out) == (124, True), (rc, timed_out)
    rc, timed_out, _ = _ns(["sh", "-c", "sleep 300 > /dev/null 2>&1 & exit 0"], COPY_ROOT, dict(os.environ), log, timeout_s=10)
    assert (rc, timed_out) == (125, False), (rc, timed_out)
    log.unlink()
    assert _strays() == [], _strays()
    print("selftest: a timed-out run and a run leaving a child both leave no process behind")


def _summary(log: Path) -> tuple[list[str], str, int]:
    text = log.read_text(errors="replace")
    lines = text.splitlines()
    fails = [ln[:200] for ln in lines if FAIL_RE.search(ln) and "PASS " not in ln][:6]
    tail = next((ln for ln in reversed(lines) if re.search(r"passed|failed|Tests? ", ln)), lines[-1] if lines else "")
    return fails, tail[:200], sum(text.count(m) for m in MARKERS)


def _run_test(copy: Path, t: dict, logdir: Path, pid: str) -> list[dict]:
    env = dict(os.environ, TZ="UTC", PATH=f"{NODE_BIN}:{os.environ['PATH']}")
    env.pop("TEST_DEVICE", None)
    runs = []
    level = t["level"]
    if level in ("mp", "mp_gate"):
        for stage in ("-1", "32768"):
            runner = [t["file"]] if stage == "-1" else ["tests/_threshold_runner.py", t["file"], stage]
            dev = [f"TEST_DEVICE={t['device']}"] if t.get("device") else []
            log = logdir / f"{pid}.{Path(t['file']).stem}.{stage}.log"
            rc, to, secs = _ns(["env", "-u", "TEST_DEVICE", f"MICROPYPATH={UNIT_PATH}", *dev, MP, "-X", "heapsize=16M", *runner], copy, env, log)
            fails, tail, markers = _summary(log)
            run = {"file": t["file"], "stage": stage, "rc": rc, "timed_out": to, "secs": secs, "fails": fails, "tail": tail, "markers": markers}
            if level == "mp_gate":
                gate_dir = copy / ".gate"
                gate_dir.mkdir(exist_ok=True)
                fn = "eval \"$(sed -n '/^_flag_memory_errors() {/,/^}/p' scripts/test.sh)\"; _flag_memory_errors plant \"$1\""
                subprocess.run(["bash", "-c", f"results_dir={gate_dir}; {fn}", "bash", str(log)], cwd=copy, check=False)
                run["gate_red"] = (gate_dir / "plant.memerr").exists() or (gate_dir / "plant.noverdict").exists()
                shutil.rmtree(gate_dir)
            runs.append(run)
    elif level == "host":
        log = logdir / f"{pid}.{Path(t['file']).stem}.log"
        rc, to, secs = _ns([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", *t.get("args", []), t["file"]], copy, dict(env, PYTHONPATH="scripts"), log)
        fails, tail, markers = _summary(log)
        runs.append({"file": t["file"], "stage": "host", "rc": rc, "timed_out": to, "secs": secs, "fails": fails, "tail": tail, "markers": markers})
    elif level == "js":
        (copy / "node_modules").symlink_to(NODE_MODULES)
        log = logdir / f"{pid}.{Path(t['file']).stem}.log"
        rc, to, secs = _ns([str(NODE_MODULES / ".bin/vitest"), "run", t["file"]], copy, env, log)
        fails, tail, markers = _summary(log)
        runs.append({"file": t["file"], "stage": "js", "rc": rc, "timed_out": to, "secs": secs, "fails": fails, "tail": tail, "markers": markers})
        (copy / "node_modules").unlink()
    elif level == "twin_gate":
        for stage in ("-1", "32768"):
            log = logdir / f"{pid}.twingate.{stage}.log"
            rc, to, secs = _ns([PY, str(Path(__file__).resolve().parent / "plant_twin_gate.py"), MP, stage, str(logdir / f"{pid}.twin.{stage}.out")], copy, env, log)
            fails, tail, markers = _summary(log)
            runs.append({"file": "twin gate", "stage": stage, "rc": rc, "timed_out": to, "secs": secs, "fails": fails, "tail": tail, "markers": markers})
    return runs


def _red(run: dict) -> bool:
    return run["rc"] != 0 or run.get("gate_red", False)


def run(snap: Path, resume: Path, only: "set[str] | None", stop: Path) -> None:
    done = {json.loads(line)["id"] for line in resume.read_text().splitlines()} if resume.exists() else set()
    base_manifest = json.loads((snap.parent / (snap.name + ".manifest.json")).read_text())
    logdir = resume.parent / "plant_logs"
    logdir.mkdir(exist_ok=True)
    for p in PLANTS:
        if p["id"] in done or (only and p["id"] not in only) or not p["tests"]:
            continue
        if stop.exists():
            print("stop file present: stopping")
            break
        copy = COPY_ROOT / re.sub(r"[^A-Za-z0-9_.-]", "_", p["id"])
        shutil.rmtree(copy, ignore_errors=True)
        COPY_ROOT.mkdir(parents=True, exist_ok=True)
        shutil.copytree(snap, copy, symlinks=True)
        sites = [_apply(copy, e) for e in p.get("edits", [])]
        if any(e["file"].startswith(("src/", "buildgen/", "devices/")) for e in p.get("edits", [])):
            gen = subprocess.run([PY, "scripts/_generate_sensortask_modules.py"], cwd=copy, capture_output=True, text=True, check=False)
            if gen.returncode != 0:
                sites.append(f"generate rc={gen.returncode}: {(gen.stdout + gen.stderr)[-300:]}")
        runs = []
        for t in p["tests"]:
            runs += _run_test(copy, t, logdir, re.sub(r"[^A-Za-z0-9_.-]", "_", p["id"]))
        shutil.rmtree(copy)
        removed = not copy.exists()
        touched = {e["file"] for e in p.get("edits", [])}
        unchanged = all(hashlib.sha256((snap / f).read_bytes()).hexdigest() == base_manifest[f] for f in touched if f in base_manifest)
        strays = _strays()
        if strays:
            sys.exit(f"{p['id']}: processes {strays} outlived the plant's run")
        rec = {"id": p["id"], "sites": sites, "red": any(_red(r) for r in runs), "runs": runs, "copy_removed": removed, "source_unchanged": unchanged, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with resume.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(f"{p['id']}: {'RED' if rec['red'] else 'green'} {[(r['stage'], r['rc'], r['secs']) for r in runs]} removed={removed} unchanged={unchanged}", flush=True)
    final = _manifest(snap) == base_manifest
    print(f"snapshot unchanged at the end: {final}")


def table(resume: Path) -> None:
    for line in resume.read_text().splitlines():
        r = json.loads(line)
        reds = sorted({(x["file"], x["stage"]) for x in r["runs"] if _red(x)})
        fails = sorted({f for x in r["runs"] for f in x["fails"] if f.startswith(("FAIL", "ABORT", "FAILED"))})[:3]
        print(f"{r['id']}\t{'RED' if r['red'] else 'GREEN'}\t{reds}\t{fails}\t{any(x['timed_out'] for x in r['runs'])}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["snapshot", "check", "run", "table", "selftest"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--only", default="")
    ap.add_argument("--stop", default=str(S / "u35/laneC/cfr/STOP"))
    a = ap.parse_args()
    if a.cmd == "snapshot":
        snapshot(Path(a.args[0]), Path(a.args[1]))
    elif a.cmd == "check":
        check(Path(a.args[0]))
    elif a.cmd == "run":
        run(Path(a.args[0]), Path(a.args[1]), set(a.only.split(",")) if a.only else None, Path(a.stop))
    elif a.cmd == "selftest":
        selftest()
    else:
        table(Path(a.args[0]))


if __name__ == "__main__":
    main()
