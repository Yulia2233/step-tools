#!/usr/bin/env python3
"""Freeze the benchmark: sha256 of every data file the scorer reads. eval_geom.py refuses to score if any differs."""
import hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent
files = {}
for pat in ("data/*/orig.step", "data/*/split.step", "data/*/nurbs.step", "data/*/splitnurbs.step", "data/*/variants.json",
            "data/*/gt_ops.json", "data/*/design.json", "data/*/model.py", "baseline.json"):
    for p in sorted(HERE.glob(pat)):
        files[str(p.relative_to(HERE))] = hashlib.sha256(p.read_bytes()).hexdigest()
tok = HERE.parent.parent / "envs" / "tok" / "tokenizer.json"
json.dump({"n_files": len(files), "files": files}, open(HERE / "MANIFEST.json", "w"), indent=0, sort_keys=True)
print(len(files), "files frozen; tokenizer sha", hashlib.sha256(tok.read_bytes()).hexdigest()[:12])
