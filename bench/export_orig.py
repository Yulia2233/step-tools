#!/usr/bin/env python3
"""Regenerate bench/data/<case>/orig.step from each case's model.py (the ground-truth construction code).

  SIMPLECAD_PYTHON=/path/to/python-with-SimpleCADAPI-2.2.5 python3 bench/export_orig.py [--cases case-001 ...]

Each model.py exports `model.step` next to itself; this renames it to orig.step. Then run build_variants.py, build_gt_ops.py and
make_manifest.py (in that order) to complete the benchmark.
"""
import argparse, os, subprocess, sys
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
PY = os.environ.get("SIMPLECAD_PYTHON", sys.executable)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="*")
    a = ap.parse_args()
    bad = []
    for d in sorted(DATA.glob("case-*")):
        if a.cases and d.name not in a.cases:
            continue
        r = subprocess.run([PY, "model.py"], cwd=d, capture_output=True, text=True, timeout=600)
        step = d / "model.step"
        if r.returncode != 0 or not step.exists():
            bad.append(d.name)
            print(d.name, "FAILED", (r.stderr or r.stdout)[-200:])
            continue
        step.replace(d / "orig.step")
        print(d.name, "ok")
    print("failed:", bad)


if __name__ == "__main__":
    main()
