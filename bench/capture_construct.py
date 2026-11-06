#!/usr/bin/env python3
"""Ground truth for construction parameters: re-run a case's model.py with sweep/loft/helical calls wrapped and record the
rail (sampled path) and the profiles/sections they were given. Run with the SimpleCADAPI 2.2.5 python (the cases' version).

  $SIMPLECAD_PYTHON -I bench/capture_construct.py case-201 [case-202 ...]   -> bench/construct_gt/<case>.json
"""
import json, os, runpy, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sample_shape_edges(shape, n=24):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    out = []
    ex = TopExp_Explorer(shape, TopAbs_EDGE)
    while ex.More():
        c = BRepAdaptor_Curve(TopoDS.Edge_s(ex.Current()))
        a, b = c.FirstParameter(), c.LastParameter()
        out.append([[c.Value(a + (b - a) * k / (n - 1)).X(), c.Value(a + (b - a) * k / (n - 1)).Y(), c.Value(a + (b - a) * k / (n - 1)).Z()]
                    for k in range(n)])
        ex.Next()
    return out


def occ(obj):
    for attr in ("wrapped", "_shape", "shape", "occ_shape"):
        v = getattr(obj, attr, None)
        if v is not None and hasattr(v, "IsNull"):
            return v
    for name in dir(obj):
        if name.startswith("__"):
            continue
        try:
            v = getattr(obj, name)
        except Exception:
            continue
        if hasattr(v, "IsNull") and hasattr(v, "ShapeType"):
            return v
    return None


def area_of(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    g = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape, g)
    c = g.CentreOfMass()
    return g.Mass(), [c.X(), c.Y(), c.Z()]


def main():
    import simplecadapi as scad
    for case in sys.argv[1:]:
        calls = []
        orig = {k: getattr(scad, k) for k in ("sweep_rsolid", "loft_rsolid", "helical_sweep_rsolid", "twisted_sweep_rsolid")}

        def wrap(name):
            f = orig[name]

            def g(*a, **kw):
                rec = {"op": name, "kw": {k: (list(v) if isinstance(v, tuple) else v) for k, v in kw.items() if isinstance(v, (int, float, str, bool)) or (isinstance(v, tuple) and all(isinstance(x, (int, float)) for x in v))}}
                path = kw.get("path") if "path" in kw else (a[1] if name == "sweep_rsolid" and len(a) > 1 else None)
                prof = kw.get("profile") if "profile" in kw else (a[0] if a and name != "loft_rsolid" else None)
                profs = kw.get("profiles") if "profiles" in kw else (a[0] if a and name == "loft_rsolid" else None)
                try:
                    if path is not None:
                        rec["path"] = sample_shape_edges(occ(path))
                    if prof is not None:
                        s = occ(prof)
                        rec["profile_edges"] = sample_shape_edges(s, 12)
                        if s.ShapeType().name.endswith("FACE"):
                            rec["profile_area"], rec["profile_centroid"] = area_of(s)
                    if profs is not None:
                        rec["sections"] = [sample_shape_edges(occ(p), 12) for p in profs]
                except Exception as e:
                    rec["capture_error"] = repr(e)[:200]
                calls.append(rec)
                return f(*a, **kw)
            return g
        for k in orig:
            setattr(scad, k, wrap(k))
        src = HERE / "data" / case / "model.py"
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "model.py"
            dst.write_text(src.read_text())
            try:
                ns = runpy.run_path(str(dst), run_name="gt_capture")
                ns["build"]()
                status = "ok"
            except Exception as e:
                status = "error: " + repr(e)[:200]
        for k, f in orig.items():
            setattr(scad, k, f)
        (HERE / "construct_gt").mkdir(exist_ok=True)
        json.dump({"case": case, "status": status, "calls": calls}, open(HERE / "construct_gt" / f"{case}.json", "w"))
        print(case, status, [c["op"] for c in calls], [list(c.keys()) for c in calls][:1])


if __name__ == "__main__":
    main()
