#!/usr/bin/env python3
"""Candidate entry point scored by bench/eval_geom.py: STEP -> the IR text an LLM would be shown, plus the face map.

  run(step_path) -> {"lines": [json-line strings: header, face records, derived lines],
                     "face_map": {simplecadapi face index: IR id}}

An IR id that has no record among `lines` is an *implied* face (omitted because a prism's loops determine it).
The harness reads only `lines` and `face_map`; every claim it scores must be visible in `lines`.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("STEPIR_NDIG", "4")

import stepir          # noqa: E402
import stepir_ops      # noqa: E402


def run(path):
    path = str(path)
    lines = stepir.build_ir(path)
    fmap = {int(k): int(v) for k, v in stepir.build_ir.last_face_map.items()}
    facts = stepir_ops.analyse(path, with_fit=True, lines=lines)
    lines = stepir_ops.augment(lines, facts)
    return {"lines": lines, "face_map": fmap}
