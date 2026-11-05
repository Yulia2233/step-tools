#!/usr/bin/env python3
"""Stage 1 of build_gt_ops (run with the SDK 2.2.5 python that produced the cases).

  gt_ops_stage1.py <case_dir> <scratch_dir>

Re-runs model.py from a scratch copy with the shape-creating SDK operations wrapped. Every top-level call (calls nested
inside another wrapped call are ignored) is recorded in order, and its output shape (plus the input shape for
extrude / fillet / chamfer) is written as a BREP file. Stage 2 (cad214 python) matches the faces of orig.step back to
the operation that introduced their carrier. Nothing in the SDK or in model.py is modified.
"""
import functools
import importlib.util
import inspect
import json
import shutil
import sys
from pathlib import Path

import simplecadapi as scad
from OCP.BRepTools import BRepTools
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer

CREATORS = [
    "make_box_rsolid", "make_cylinder_rsolid", "make_cone_rsolid", "make_sphere_rsolid",
    "extrude_rsolid", "revolve_rsolid", "loft_rsolid", "sweep_rsolid", "twisted_sweep_rsolid",
    "helical_sweep_rsolid", "make_gordon_surface_rface", "fillet_rsolid", "chamfer_rsolid",
]
BOOLEANS = ["union_rsolid", "cut_rsolid", "intersect_rsolid"]
INPUT_ARG = {"extrude_rsolid": "profile", "revolve_rsolid": "profile", "fillet_rsolid": "solid", "chamfer_rsolid": "solid",
             "sweep_rsolid": "profile", "twisted_sweep_rsolid": "profile"}


def shape_of(x):
    return getattr(x, "wrapped", None)


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def main():
    case_dir, scratch = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if scratch.exists():
        shutil.rmtree(scratch)
    (scratch / "src").mkdir(parents=True)
    shutil.copy(case_dir / "model.py", scratch / "src" / "model.py")
    records, counts, depth = [], {}, [0]

    def wrap(name):
        orig = getattr(scad, name)
        sig = inspect.signature(orig)

        @functools.wraps(orig)
        def w(*a, **k):
            top = depth[0] == 0
            depth[0] += 1
            try:
                out = orig(*a, **k)
            finally:
                depth[0] -= 1
            counts[name] = counts.get(name, 0) + 1
            if not top:
                return out
            idx = len(records)
            rec = {"k": idx, "op": name, "args": {}}
            try:
                bound = sig.bind(*a, **k)
                bound.apply_defaults()
                for key in ("radius", "distance", "angle", "height", "pitch", "twist_angle", "ruled", "is_frenet"):
                    if key in bound.arguments:
                        v = bound.arguments[key]
                        rec["args"][key] = num(v) if not isinstance(v, (bool, str)) else v
                for key in ("direction", "axis", "origin", "dir", "center"):
                    if key in bound.arguments and bound.arguments[key] is not None:
                        rec["args"][key] = [num(c) for c in bound.arguments[key]]
                inp = INPUT_ARG.get(name)
                if inp and inp in bound.arguments:
                    s = shape_of(bound.arguments[inp])
                    if s is not None:
                        f = scratch / f"op{idx:03d}_in.brep"
                        BRepTools.Write_s(s, str(f))
                        rec["in"] = f.name
            except Exception as e:
                rec["bind_error"] = repr(e)[:200]
            s = shape_of(out)
            if s is None:
                rec["error"] = "no wrapped shape in result"
            else:
                f = scratch / f"op{idx:03d}_out.brep"
                BRepTools.Write_s(s, str(f))
                rec["out"] = f.name
            records.append(rec)
            return out
        return w

    for n in CREATORS + BOOLEANS:
        if hasattr(scad, n):
            setattr(scad, n, wrap(n))

    spec = importlib.util.spec_from_file_location("gtcase", scratch / "src" / "model.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.build()
    body = res.part.body.wrapped
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(body, props)
    vol = props.Mass()
    props2 = GProp_GProps()
    BRepGProp.SurfaceProperties_s(body, props2)
    nf = 0
    ex = TopExp_Explorer(body, TopAbs_FACE)
    while ex.More():
        nf += 1
        ex.Next()
    for r in records:
        if r["op"] in BOOLEANS:
            r.pop("args", None)
    json.dump({"case": case_dir.name, "records": [r for r in records if r["op"] not in BOOLEANS],
               "counts": counts, "final": {"volume": vol, "area": props2.Mass(), "faces_raw_enum": nf}},
              open(scratch / "stage1.json", "w"))
    print("ok", case_dir.name, len(records))


if __name__ == "__main__":
    main()
