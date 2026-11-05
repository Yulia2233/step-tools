#!/usr/bin/env python3
"""Run the generation tasks through codex, validate each result with validate.py, retry failures with the reason appended.

  python3 run_queue.py --parallel 6 [--limit N]
"""
import argparse, json, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import os
HERE = Path(__file__).resolve().parent
CODEX = os.environ.get("CODEX_BIN", "codex")                       # codex CLI
PY = Path(os.environ.get("VALIDATE_PYTHON", "python3"))           # interpreter with SimpleCADAPI 2.1.4 + OCP (runs validate.py)
SIMPLECAD_PYTHON = os.environ.get("SIMPLECAD_PYTHON", "python3")  # SimpleCADAPI 2.2.5, runs the generated model.py
EXAMPLES = os.environ.get("STEP_TOOLS_EXAMPLES", str(HERE.parent / "bench" / "data"))
lock = threading.Lock()
state = {"rate_limited": 0}


def log(msg):
    with lock:
        print(time.strftime("%H:%M:%S"), msg, flush=True)


def run_task(t, tries=3, timeout=2400):
    d = HERE / "gen" / t["id"]
    d.mkdir(parents=True, exist_ok=True)
    vf = d / "validation.json"
    if vf.exists() and json.load(open(vf)).get("ok"):
        return t["id"], "cached"
    retry = ""
    for k in range(tries):
        prompt = (HERE / "prompt_template.md").read_text().format(retry=retry, python=SIMPLECAD_PYTHON, examples=EXAMPLES, **t)
        (d / "prompt.md").write_text(prompt)
        t0 = time.time()
        try:
            with open(d / "events.jsonl", "w") as ev, open(d / "stderr.log", "w") as er:
                subprocess.run([CODEX, "exec", "-m", "gpt-6.1-sol", "--skip-git-repo-check", "-s", "workspace-write", "-C", str(d), "--json",
                                "-o", str(d / "last_message.txt"), "-"], input=prompt, text=True, stdout=ev, stderr=er, timeout=timeout)
        except subprocess.TimeoutExpired:
            log(f"{t['id']} timeout")
        err = (d / "stderr.log").read_text()[-3000:] + (d / "events.jsonl").read_text()[-3000:]
        if "429" in err or "Too Many Requests" in err or "rate limit" in err.lower():
            with lock:
                state["rate_limited"] += 1
            log(f"{t['id']} rate limited, backing off")
            time.sleep(120)
        r = subprocess.run([str(PY), "-I", str(HERE / "validate.py"), str(d), t["kind"]], capture_output=True, text=True, timeout=900)
        try:
            v = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            v = {"ok": False, "why": ["validator crashed: " + r.stderr[-200:]]}
        json.dump(v, open(vf, "w"))
        log(f"{t['id']} try {k + 1}: {'OK' if v['ok'] else 'FAIL ' + '; '.join(v['why'])[:140]} ({time.time() - t0:.0f}s)")
        if v["ok"]:
            return t["id"], "ok"
        retry = "\nYour previous attempt failed these checks: " + "; ".join(v["why"])[:600] + ". Fix them.\n"
    return t["id"], "failed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", nargs="*")
    a = ap.parse_args()
    tasks = json.load(open(HERE / "tasks.json"))
    if a.ids:
        tasks = [t for t in tasks if t["id"] in a.ids]
    if a.limit:
        tasks = tasks[:a.limit]
    with ThreadPoolExecutor(a.parallel) as ex:
        res = list(ex.map(run_task, tasks))
    import collections
    print(collections.Counter(s for _, s in res), "rate-limit hits:", state["rate_limited"])


if __name__ == "__main__":
    main()
