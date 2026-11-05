#!/usr/bin/env python3
"""Validate one generated part directory. Run with python -I. Prints one JSON line."""
import ast, json, subprocess, sys
from collections import Counter
from pathlib import Path

import os
PY = Path(os.environ.get("SIMPLECAD_PYTHON", "python3"))     # interpreter with SimpleCADAPI 2.2.5 that runs the generated model.py
FORBID_NAMES = {"load_step_rshape", "load_step_rbrepmodel", "load_brep_region_rsolid", "load_brep_region_rshell", "copy_step_region_rpath",
                "read_step", "import_step", "OCP", "cadquery", "build123d", "trimesh", "FreeCAD"}
KIND_API = {"sweep_spline": "sweep_rsolid", "sweep_planar_spline": "sweep_rsolid", "sweep_mixed_rail": "sweep_rsolid",
            "loft_noncongruent": "loft_rsolid", "loft_ruled": "loft_rsolid", "revolve_spline": "revolve_rsolid", "extrude_spline": "extrude_rsolid"}


def validate(d, kind):
    d = Path(d)
    res = {"dir": str(d), "ok": False, "why": []}
    src = d / "model.py"
    if not src.exists():
        res["why"].append("no model.py")
        return res
    tree = ast.parse(src.read_text())
    calls = Counter()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id in FORBID_NAMES:
            res["why"].append(f"forbidden name {n.id}")
        if isinstance(n, ast.Attribute) and n.attr in FORBID_NAMES:
            res["why"].append(f"forbidden attr {n.attr}")
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mod = getattr(n, "module", None) or ""
            names = [a.name for a in n.names]
            for x in [mod] + names:
                if x.split(".")[0] in FORBID_NAMES:
                    res["why"].append(f"forbidden import {x}")
        if isinstance(n, ast.Try):
            res["why"].append("try/except")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "scad":
            calls[n.func.attr] += 1
    res["calls"] = dict(calls)
    if KIND_API[kind] not in calls:
        res["why"].append(f"does not call {KIND_API[kind]}")
    if "make_part_rpart" not in calls:
        res["why"].append("no make_part_rpart")
    step = d / "model.step"
    if step.exists():
        step.unlink()
    r = subprocess.run([str(PY), "model.py"], cwd=d, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not step.exists():
        res["why"].append("run failed: " + (r.stderr or r.stdout)[-300:])
        return res
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_Reader
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    rd = STEPControl_Reader()
    if rd.ReadFile(str(step)) != IFSelect_RetDone:
        res["why"].append("STEP unreadable")
        return res
    rd.TransferRoots()
    shape = rd.OneShape()
    ex, ns = TopExp_Explorer(shape, TopAbs_SOLID), 0
    while ex.More():
        ns += 1
        ex.Next()
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, g)
    res["solids"], res["volume"], res["valid"] = ns, g.Mass(), BRepCheck_Analyzer(shape).IsValid()
    if ns != 1:
        res["why"].append(f"{ns} solids")
    if not res["valid"]:
        res["why"].append("BRepCheck invalid")
    if res["volume"] <= 1e-6:
        res["why"].append("no volume")
    from simplecadapi.inspect import brep
    m = brep.load_step_rbrepmodel(path=str(step))
    types = Counter(m.describe_entity(f"face:{i}")["geometry"]["type"] for i in range(len(m.faces)))
    res["face_types"] = dict(types)
    freeform = sum(v for k, v in types.items() if k not in ("PLANE", "CYLINDER", "CONE", "SPHERE", "TORUS"))
    res["freeform_faces"] = freeform
    if freeform == 0:
        res["why"].append("no free-form face in the result")
    res["ok"] = not res["why"]
    return res


if __name__ == "__main__":
    print(json.dumps(validate(sys.argv[1], sys.argv[2])))
