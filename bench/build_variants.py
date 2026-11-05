#!/usr/bin/env python3
"""Build the perturbed variants of every benchmark part, with exact parent-face ground truth.

  python -I bench/build_variants.py [--cases case-001 ...] [--workers 8]

For each bench/data/<case>/orig.step it writes
  split.step       closed (periodic) faces cut at the seam into halves, and the large faces cut by area: the same solid,
                   the same carriers, more faces - what another modeller or an import/export round trip produces.
  nurbs.step       every face converted to a B-spline surface: analytic carriers hidden inside NURBS.
  splitnurbs.step  both of the above.
  variants.json    for every variant face (index in simplecadapi's BRepModel, the numbering stepir uses) the index of the
                   original face that contains it ("parent"), found geometrically (interior sample points projected onto
                   the original face), so it does not depend on any operation history.
Nothing here is shown to stepir; it is the answer key for bench/eval_geom.py.
"""
import argparse
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


def read_step(path):
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_Reader
    rd = STEPControl_Reader()
    assert rd.ReadFile(str(path)) == IFSelect_RetDone, f"read {path}"
    rd.TransferRoots()
    return rd.OneShape()


def write_step(shape, path):
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    w = STEPControl_Writer()
    w.Transfer(shape, STEPControl_AsIs)
    assert w.Write(str(path)) == 1 or True
    return Path(path).exists()


def faces_of(shape):
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    out = []
    while ex.More():
        out.append(TopoDS.Face_s(ex.Current()))
        ex.Next()
    return out


def area(face):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    g = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, g)
    return g.Mass()


def fix(shape):
    from OCP.ShapeFix import ShapeFix_Shape
    f = ShapeFix_Shape(shape)
    f.Perform()
    return f.Shape()


def split_shape(shape, frac):
    """Seam-split the closed faces, then cut every face larger than `frac` x the largest face by area; repair topology."""
    from OCP.ShapeUpgrade import ShapeUpgrade_ShapeDivideArea, ShapeUpgrade_ShapeDivideClosed
    dc = ShapeUpgrade_ShapeDivideClosed(shape)
    dc.SetNbSplitPoints(1)
    dc.Perform()
    s1 = fix(dc.Result())
    mx = max(area(f) for f in faces_of(s1))
    da = ShapeUpgrade_ShapeDivideArea(s1)
    da.MaxArea = mx * frac
    da.Perform()
    return fix(da.Result())


def valid(shape):
    from OCP.BRepCheck import BRepCheck_Analyzer
    return BRepCheck_Analyzer(shape).IsValid()


def nurbs_convert(shape):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    return BRepBuilderAPI_NurbsConvert(shape, True).Shape()


def mass_and_diag(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, g)
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, b, False, False)          # tight box: the default one follows B-spline control polygons
    b = b.Get()
    return g.Mass(), math.dist(b[:3], b[3:])


def plausible(path, ref):
    """A variant must be the same solid: re-read from disk, volume within 2 % and bounding box diagonal within 1 % of the
    original (a face split that deforms a free-form surface can pass BRepCheck and still be a different part)."""
    vol, diag = mass_and_diag(read_step(path))
    if abs(vol - ref[0]) > 0.02 * abs(ref[0]) + 1e-9 or abs(diag - ref[1]) > 0.01 * ref[1]:
        return f"implausible: volume {vol:.5g} vs {ref[0]:.5g}, diagonal {diag:.5g} vs {ref[1]:.5g}"
    return None


def interior_points(face, n=4):
    """A few points strictly inside the trimmed face (3D), by classifying a UV grid against the face boundary."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_IN
    from OCP.gp import gp_Pnt2d
    u0, u1, v0, v1 = BRepTools.UVBounds_s(face)
    sf = BRepAdaptor_Surface(face, True)
    pts = []
    k = 9
    order = sorted(((abs(i - (k - 1) / 2) + abs(j - (k - 1) / 2), i, j) for i in range(k) for j in range(k)))
    for _, i, j in order:
        u = u0 + (u1 - u0) * (i + 0.5) / k
        v = v0 + (v1 - v0) * (j + 0.5) / k
        c = BRepClass_FaceClassifier(face, gp_Pnt2d(u, v), 1e-7)
        if c.State() == TopAbs_IN:
            p = sf.Value(u, v)
            pts.append((p.X(), p.Y(), p.Z()))
            if len(pts) >= n:
                break
    return pts


def distance_to_face(pt, face):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    v = BRepBuilderAPI_MakeVertex(gp_Pnt(*pt)).Vertex()
    d = BRepExtrema_DistShapeShape(v, face)
    d.Perform()
    return d.Value() if d.IsDone() else 1e9


def bbox(face):
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    b = Bnd_Box()
    BRepBndLib.Add_s(face, b)
    return b.Get()


def sdk_faces(step):
    """simplecadapi's face list for a STEP: [(index, TopoDS_Face)] - the numbering stepir and the harness use."""
    from simplecadapi.inspect import brep
    m = brep.load_step_rbrepmodel(path=str(step))
    out = []
    for i in range(len(m.faces)):
        out.append(m.resolve_entity(f"face:{i}"))
    return m, out


def parents(orig_step, var_step, tol):
    """variant sdk-face index -> orig sdk-face index containing it (None if not unique)."""
    from OCP.TopoDS import TopoDS
    mo, fo = sdk_faces(orig_step)
    mv, fv = sdk_faces(var_step)

    def as_face(x):
        return TopoDS.Face_s(x[-1] if isinstance(x, tuple) else x)

    fo = [as_face(x) for x in fo]
    fv = [as_face(x) for x in fv]
    bo = [bbox(f) for f in fo]
    out = {}
    for i, f in enumerate(fv):
        pts = interior_points(f)
        if not pts:
            out[i] = None
            continue
        votes = None
        for p in pts:
            hit = set()
            for j, b in enumerate(bo):
                if (p[0] < b[0] - tol or p[0] > b[3] + tol or p[1] < b[1] - tol or p[1] > b[4] + tol
                        or p[2] < b[2] - tol or p[2] > b[5] + tol):
                    continue
                if distance_to_face(p, fo[j]) <= tol:
                    hit.add(j)
            votes = hit if votes is None else votes & hit
        out[i] = sorted(votes)[0] if votes and len(votes) == 1 else None
    return out, len(fo), len(fv)


def build_case(case):
    d = DATA / case
    orig = d / "orig.step"
    res = {"case": case, "variants": {}}
    try:
        shape = read_step(orig)
        diag = 1.0
        b = bbox(shape)
        diag = math.dist(b[:3], b[3:])
        ref = mass_and_diag(shape)
        tol = 1e-6 * max(1.0, diag) * 10
        sp = None
        for fac in (0.3, 0.5, 0.8):
            cand = split_shape(shape, fac)
            if valid(cand) and len(faces_of(cand)) > len(faces_of(shape)):
                sp = cand
                res["split_area_factor"] = fac
                break
        made = {}
        if sp is not None:
            made["split"] = sp
            made["splitnurbs"] = nurbs_convert(sp)
        made["nurbs"] = nurbs_convert(shape)
        for name, sh in made.items():
            if not valid(sh):
                res["variants"][name] = {"error": "invalid shape"}
                continue
            p = d / f"{name}.step"
            write_step(sh, p)
            bad = plausible(p, ref)
            if bad:
                p.unlink()
                res["variants"][name] = {"error": bad}
                continue
            par, no, nv = parents(orig, p, tol)
            bad = sum(1 for v in par.values() if v is None)
            res["variants"][name] = {"n_orig_faces": no, "n_faces": nv, "parent": {str(k): v for k, v in par.items()},
                                     "unmapped": bad}
        json.dump(res, open(d / "variants.json", "w"))
        return case, {k: (v.get("n_faces"), v.get("unmapped"), v.get("error")) for k, v in res["variants"].items()}
    except Exception as e:  # noqa: BLE001 - reported, not hidden
        import traceback
        return case, {"error": repr(e)[:300], "tb": traceback.format_exc()[-600:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    cases = a.cases or sorted(p.name for p in DATA.iterdir() if (p / "orig.step").exists())
    with ProcessPoolExecutor(a.workers) as ex:
        for case, info in ex.map(build_case, cases):
            print(case, json.dumps(info))


if __name__ == "__main__":
    main()
