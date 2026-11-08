#!/usr/bin/env python3
"""Compare two STEPIR candidates on real parts: IR size, implied faces, relief lines, and an independent check of every
implied face (verify_implied.py), one subprocess per part.

  OLD=<cand dir> NEW=<cand dir> python3 cmp_run.py parts.txt <out dir> [workers]      (TAGS=new to run only NEW)

Writes <out>/<tag>__<part>.ir and <out>/results.jsonl ({tag, part, chars, base_chars, faces, implied, relief, prism, B, S,
types, sec, verify}). Run with the SimpleCADAPI 2.2.7 Python in PY (default envs/sca227). Token counts: cmp_tokens.py.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = os.environ.get("PY", str(ROOT / "envs/sca227/bin/python"))
CANDS = {"old": os.environ.get("OLD", str(HERE.parent / "cand")), "new": os.environ.get("NEW", str(HERE.parent / "cand"))}


def job(tag, part, out):
    o = out / f"{tag}__{Path(part).stem}.ir"
    try:
        r = subprocess.run([PY, "-I", str(HERE / "cmp_one.py"), CANDS[tag], part, str(o)], capture_output=True, text=True, timeout=600)
        res = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {"error": (r.stderr.strip().splitlines() or ["?"])[-1][:200]}
    except Exception as e:  # noqa: BLE001
        res = {"error": repr(e)[:200]}
    if tag == "new" and "error" not in res:
        try:
            r = subprocess.run([PY, "-I", str(HERE / "verify_implied.py"), CANDS[tag], part], capture_output=True, text=True, timeout=900)
            res["verify"] = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception as e:  # noqa: BLE001
            res["verify"] = {"error": repr(e)[:200]}
    return {"tag": tag, "part": Path(part).stem, **res}


def main():
    parts = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    jobs = [(t, p) for p in parts for t in os.environ.get("TAGS", "old,new").split(",")]
    with ThreadPoolExecutor(workers) as ex, open(out / "results.jsonl", "w") as fh:
        for r in ex.map(lambda a: job(a[0], a[1], out), jobs):
            fh.write(json.dumps(r) + "\n")
            fh.flush()


if __name__ == "__main__":
    main()
