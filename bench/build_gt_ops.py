#!/usr/bin/env python3
"""Per-face operation provenance for the tail-solid200 cases.

  build_gt_ops.py [--cases case-001 case-002 ...] [--workers 8] [--keep-scratch]

Run with a python that has SimpleCADAPI 2.1.4 + OCP (and set SIMPLECAD_PYTHON for stage 1). For each bench/data/<case>/:
  stage 1 (SDK 2.2.5 python, gt_ops_stage1.py): re-run model.py with the creating operations wrapped, dump each call's output
          shape (and the input shape of extrude/fillet/chamfer) as BREP;
  stage 2 (here): load orig.step with the cad214 BRep loader (the face index stepir uses) and match every face to the
          operation(s) that introduced its carrier by point-to-surface distance (final-face sample points vs the untrimmed
          carrier surface of every operation output face). Boolean trimming never changes a carrier, so this is exact.
          Blend faces additionally get the two pre-blend faces they round (`supports`).
Writes bench/data/<case>/gt_ops.json and bench/data/GT_OPS_REPORT.md (failures are listed, never skipped silently).
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "data"
PY225 = Path(os.environ.get("SIMPLECAD_PYTHON", "python3"))      # interpreter with SimpleCADAPI 2.2.5 (the version that wrote the cases)
SCRATCH = Path("/tmp/gt_ops_stage1")
TOL = 1e-5            # point-to-carrier distance, mm (coordinates are ~30 mm; STEP carries doubles)
REL = 1e-6            # rebuild-vs-STEP volume / area agreement

PRIMS = {"make_box_rsolid", "make_cylinder_rsolid", "make_cone_rsolid", "make_sphere_rsolid"}
CLASS = {"make_box_rsolid": "primitive", "make_cylinder_rsolid": "primitive", "make_cone_rsolid": "primitive",
         "make_sphere_rsolid": "primitive", "extrude_rsolid": "extrude", "revolve_rsolid": "revolve",
         "loft_rsolid": "loft", "sweep_rsolid": "sweep", "twisted_sweep_rsolid": "twisted_sweep",
         "helical_sweep_rsolid": "helical_sweep", "make_gordon_surface_rface": "gordon",
         "fillet_rsolid": "fillet", "chamfer_rsolid": "chamfer"}


# classes of operation that produce the same carrier geometry (a surface of revolution can be a primitive, a revolve, a
# swept circle ...); geometry alone cannot separate them
EQUIV = {"CYLINDER": ["primitive", "extrude", "revolve", "sweep", "loft"], "CONE": ["primitive", "revolve", "loft"],
         "TORUS": ["revolve", "sweep"], "SPHERE": ["primitive", "revolve"]}


def _ocp():
    global BRep_Tool, BRepAdaptor_Surface, BRepTools, BRepClass_FaceClassifier, gp_Pnt, gp_Pnt2d, TopAbs_FACE, TopAbs_EDGE
    global TopAbs_IN, TopAbs_ON, TopExp_Explorer, TopExp, TopoDS, GeomAPI_ProjectPointOnSurf, BRepMesh_IncrementalMesh
    global TopTools_IndexedDataMapOfShapeListOfShape, BRepExtrema_DistShapeShape, BRepBuilderAPI_MakeVertex, TopLoc_Location
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepTools import BRepTools
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.gp import gp_Pnt, gp_Pnt2d
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_IN, TopAbs_ON
    from OCP.TopExp import TopExp_Explorer, TopExp
    from OCP.TopoDS import TopoDS
    from OCP.GeomAPI import GeomAPI_ProjectPointOnSurf
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.TopLoc import TopLoc_Location


def faces_of(shape):
    out, ex = [], TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        f = TopoDS.Face_s(ex.Current())
        if not any(f.IsSame(g) for g in out):
            out.append(f)
        ex.Next()
    return out


def read_brep(path):
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRep import BRep_Builder
    s = TopoDS_Shape()
    BRepTools.Read_s(s, str(path), BRep_Builder())
    return s


def adaptor_type(face):
    return str(BRepAdaptor_Surface(face).GetType()).split(".")[-1].replace("GeomAbs_", "")


def face_points(face, n=7):
    """Points that lie on `face` (inside its trimmed domain), ~n*n of them; falls back to mesh nodes."""
    ad = BRepAdaptor_Surface(face, True)
    u0, u1, v0, v1 = ad.FirstUParameter(), ad.LastUParameter(), ad.FirstVParameter(), ad.LastVParameter()
    pts = []
    if all(math.isfinite(x) and abs(x) < 1e7 for x in (u0, u1, v0, v1)):
        for m in (n, 15, 31):
            pts = []
            for a in np.linspace(0.08, 0.92, m):
                for b in np.linspace(0.08, 0.92, m):
                    uv = gp_Pnt2d(u0 + a * (u1 - u0), v0 + b * (v1 - v0))
                    c = BRepClass_FaceClassifier(face, uv, 1e-7)
                    if c.State() == TopAbs_IN:
                        p = ad.Value(uv.X(), uv.Y())
                        pts.append((p.X(), p.Y(), p.Z()))
            if len(pts) >= 6:
                break
    if len(pts) < 6:
        BRepMesh_IncrementalMesh(face, 0.05, False, 0.3, False)
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            tr = loc.Transformation()
            for i in range(1, tri.NbNodes() + 1):
                p = tri.Node(i).Transformed(tr)
                pts.append((p.X(), p.Y(), p.Z()))
            step = max(1, len(pts) // 40)
            pts = pts[::step]
    return pts


class Carrier:
    __slots__ = ("surf", "type", "face")

    def __init__(self, face):
        self.face = face
        self.surf = BRep_Tool.Surface_s(face)
        self.type = adaptor_type(face)


def on_carrier(pts, car, tol=TOL):
    for (x, y, z) in pts:
        pr = GeomAPI_ProjectPointOnSurf(gp_Pnt(x, y, z), car.surf)
        if pr.NbPoints() == 0 or pr.LowerDistance() > tol:
            return False
    return True


def match_any(pts, ftype, cars, strict_type=True):
    hit = []
    for idx, c in enumerate(cars):
        if strict_type and c.type != ftype:
            continue
        if on_carrier(pts, c):
            hit.append(idx)
    return hit


def edge_mid(edge):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    c = BRepAdaptor_Curve(edge)
    p = c.Value(0.5 * (c.FirstParameter() + c.LastParameter()))
    return p


def edges_with_faces(shape):
    from OCP.TopAbs import TopAbs_EDGE as E, TopAbs_FACE as F
    mp = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape, E, F, mp)
    out = []
    for i in range(1, mp.Extent() + 1):
        e = TopoDS.Edge_s(mp.FindKey(i))
        fs = [TopoDS.Face_s(x) for x in mp.FindFromIndex(i)]
        out.append((e, fs))
    return out


def point_edge_dist(p, edge):
    v = BRepBuilderAPI_MakeVertex(p).Vertex()
    d = BRepExtrema_DistShapeShape(v, edge)
    return d.Value() if d.IsDone() else 1e9


def same_face(a, b):
    return a.IsSame(b)


def stage2(case, scratch):
    from simplecadapi.inspect import brep
    cdir = DATA / case
    st1 = json.load(open(scratch / "stage1.json"))
    model = brep.load_step_rbrepmodel(path=str(cdir / "orig.step"))
    summ = brep.inspect_step_rsummary(path=str(cdir / "orig.step"))
    nf = len(model.faces)
    fin = st1["final"]
    chk = {"volume": [fin["volume"], summ["volume"]], "area": [fin["area"], summ["surface_area"]],
           "faces": [fin["faces_raw_enum"], nf]}
    ok = (abs(fin["volume"] - summ["volume"]) <= REL * abs(summ["volume"]) and
          abs(fin["area"] - summ["surface_area"]) <= REL * abs(summ["surface_area"]) and fin["faces_raw_enum"] == nf)
    ops_called = [{"op": k, "n": v} for k, v in sorted(st1["counts"].items())]
    if not ok:
        return {"case": case, "sdk_rebuild": "rebuild_mismatch", "n_faces": nf, "ops_called": ops_called, "check": chk,
                "faces": []}
    # --- final faces
    ffaces = [model.faces[i] for i in range(nf)]
    ftype = [model.describe_entity(f"face:{i}")["geometry"]["type"] for i in range(nf)]
    fadj = [sorted(int(q.split(":")[1]) for q in model.describe_entity(f"face:{i}")["adjacency"]["neighboring_faces"])
            for i in range(nf)]
    fpts = [face_points(f) for f in ffaces]
    fad = [adaptor_type(f) for f in ffaces]
    # --- op outputs
    recs = st1["records"]
    for r in recs:
        r["out_shape"] = read_brep(scratch / r["out"]) if r.get("out") else None
        r["in_shape"] = read_brep(scratch / r["in"]) if r.get("in") else None
        r["out_faces"] = faces_of(r["out_shape"]) if r["out_shape"] is not None else []
        r["out_cars"] = [Carrier(f) for f in r["out_faces"]]
    # introduced carriers per op (indices into out_cars)
    for r in recs:
        op, cars = r["op"], r["out_cars"]
        r["introduced"] = list(range(len(cars)))
        r["inherit"] = {}
        if r["in_shape"] is not None and op in ("fillet_rsolid", "chamfer_rsolid", "extrude_rsolid", "revolve_rsolid",
                                                 "sweep_rsolid", "twisted_sweep_rsolid"):
            in_faces = faces_of(r["in_shape"])
            in_cars = [Carrier(f) for f in in_faces]
            new = []
            for j, c in enumerate(cars):
                pts = face_points(c.face, 5)
                same = match_any(pts, c.type, in_cars)
                if op in ("fillet_rsolid", "chamfer_rsolid"):
                    if not same:
                        new.append(j)
                elif same:
                    r["inherit"][j] = ("same", same[0])
                    if c.type == "Plane":
                        new.append(j)      # a profile plane (sketch plane) is not introduced by any other wrapped op
                else:
                    new.append(j)
            if op in ("fillet_rsolid", "chamfer_rsolid"):
                r["introduced"] = new
            else:
                # extrude/revolve/sweep of a Face: a spline output face may be a translated/moved copy of the profile
                keep = []
                for j in new:
                    c = cars[j]
                    if op == "extrude_rsolid" and c.type not in ("Plane", "Cylinder", "Cone", "Sphere", "Torus") and \
                            c.type not in ("SurfaceOfExtrusion",) and r["args"].get("direction") and r["args"].get("distance"):
                        d = np.asarray(r["args"]["direction"], float)
                        d = d / (np.linalg.norm(d) or 1.0) * float(r["args"]["distance"])
                        pts = face_points(c.face, 5)
                        moved = False
                        for sgn in (1.0, -1.0):
                            q = [(x - sgn * d[0], y - sgn * d[1], z - sgn * d[2]) for (x, y, z) in pts]
                            h = match_any(q, c.type, in_cars)
                            if h:
                                r["inherit"][j] = ("translate", h[0])
                                moved = True
                                break
                        if moved:
                            continue
                    keep.append(j)
                r["introduced"] = keep
    # --- match each final face
    out_faces = []
    pool = []   # (rec index, car index)
    for ri, r in enumerate(recs):
        for j in r["introduced"]:
            pool.append((ri, j))
    for i in range(nf):
        pts = fpts[i]
        hits = []
        for strict in (True, False):
            for (ri, j) in pool:
                c = recs[ri]["out_cars"][j]
                if strict and c.type != fad[i]:
                    continue
                if on_carrier(pts, c):
                    hits.append((ri, j))
            if hits:
                break
        out_faces.append({"hits": hits})
    # --- origin labels
    def origin_for(i):
        hits = out_faces[i]["hits"]
        ops = []
        for ri, j in hits:
            op = recs[ri]["op"]
            if op not in ops:
                ops.append(op)
        classes = []
        for op in ops:
            c = CLASS[op]
            if op == "extrude_rsolid" and fad[i] == "SurfaceOfExtrusion":
                c = "spline_extrude"
            if c not in classes:
                classes.append(c)
        return ops, classes
    # translate-inherited faces: a hit on the 'translate' source's introducing carriers is handled via recs[ri]['inherit'];
    # here we look for final faces that match the translated carrier (hits come from `pool` which excludes them), so test them.
    for ri, r in enumerate(recs):
        for j, (kind, src) in r["inherit"].items():
            if kind != "translate":
                continue
            c = r["out_cars"][j]
            for i in range(nf):
                if fad[i] == c.type and not out_faces[i]["hits"] and on_carrier(fpts[i], c):
                    # label with the profile's own origin: find the op that introduced the source carrier
                    src_car = None
                    for pj, rr in enumerate(recs[:ri]):
                        for jj in rr["introduced"]:
                            if rr["op"] == "make_gordon_surface_rface":
                                src_car = (pj, jj)
                    out_faces[i]["hits"] = [(src_car[0], src_car[1])] if src_car else []
                    out_faces[i]["via_extrude"] = r["op"]
    res_faces = []
    for i in range(nf):
        ops, classes = origin_for(i)
        t = ftype[i]
        entry = {"i": i, "type": t}
        if not classes:
            entry.update(origin="unknown", origin_ops=[], note="no operation output carries this carrier")
        elif len(classes) == 1:
            entry.update(origin=classes[0], origin_ops=ops)
        else:
            entry.update(origin="ambiguous", origin_ops=ops, candidates=classes)
        entry["actual_origin"] = classes[0] if len(classes) == 1 else None
        if out_faces[i].get("via_extrude"):
            entry["origin_ops"] = ops + [out_faces[i]["via_extrude"]]
        act = entry["actual_origin"]
        if t in EQUIV and act not in (None, "fillet", "chamfer"):
            entry["equivalent_origins"] = EQUIV[t]
            if t in ("CYLINDER", "SPHERE") or (t == "TORUS" and act == "sweep"):
                entry["origin"] = "ambiguous"
                entry["candidates"] = EQUIV[t]
        res_faces.append(entry)
    # --- blend supports
    for i in range(nf):
        e = res_faces[i]
        if e["actual_origin"] not in ("fillet", "chamfer"):
            continue
        blend_hits = [(ri, j) for ri, j in out_faces[i]["hits"] if recs[ri]["op"] in ("fillet_rsolid", "chamfer_rsolid")]
        supports_all, notes, radii = [], [], []
        for ri, j in blend_hits:
            r = recs[ri]
            radius = r["args"].get("radius") if r["op"] == "fillet_rsolid" else r["args"].get("distance")
            radii.append(radius)
            sup, note = blend_supports(r, j, i, ffaces, fpts, fad, fadj, radius)
            supports_all.append(sup)
            if note:
                notes.append(note)
        sup = supports_all[0] if supports_all and all(s == supports_all[0] for s in supports_all) else None
        rad = radii[0] if radii and all(x == radii[0] for x in radii) else None
        e["blend"] = {"kind": e["actual_origin"], "radius_or_dist": rad, "supports": sup,
                      "support_note": "; ".join(dict.fromkeys(notes)) if sup is None else ""}
    return {"case": case, "sdk_rebuild": "ok", "n_faces": nf, "ops_called": ops_called, "check": chk, "faces": res_faces}


def blend_supports(r, jnew, final_i, ffaces, fpts, fad, fadj, radius):
    """Two pre-blend faces the blend face (output face jnew of op r) rounds, as final-face indices."""
    S_in, S_out = r["in_shape"], r["out_shape"]
    if S_in is None:
        return None, "no input shape recorded"
    in_faces = faces_of(S_in)
    in_cars = [Carrier(f) for f in in_faces]
    out_edges = edges_with_faces(S_out)
    out_edge_shapes = [e for e, _ in out_edges]
    in_edges = edges_with_faces(S_in)
    # S_in edges that vanish in S_out = the edges that were rounded
    removed = []
    for e, fs in in_edges:
        if len(fs) != 2:
            continue
        mid = edge_mid(e)
        if min((point_edge_dist(mid, oe) for oe in out_edge_shapes), default=1e9) > 1e-6:
            removed.append((e, fs))
    N = r["out_faces"][jnew]
    reach = 2.0 * float(radius or 1.0) + 1e-3
    pairs = []
    for e, fs in removed:
        mid = edge_mid(e)
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex as MV
        dv = BRepExtrema_DistShapeShape(MV(mid).Vertex(), N)
        if not dv.IsDone() or dv.Value() > reach:
            continue
        ia = [k for k, f in enumerate(in_faces) if f.IsSame(fs[0])]
        ib = [k for k, f in enumerate(in_faces) if f.IsSame(fs[1])]
        if ia and ib:
            pairs.append(tuple(sorted((ia[0], ib[0]))))
    pairs = sorted(set(pairs))
    if len(pairs) != 1:
        return None, f"{len(pairs)} candidate pre-blend face pairs near the blend face"
    a, b = pairs[0]
    res = []
    for k in (a, b):
        cands = [j for j in fadj[final_i] if fad[j] == in_cars[k].type and on_carrier(fpts[j], in_cars[k])]
        if len(cands) != 1:
            return None, f"pre-blend face {k} has {len(cands)} adjacent final faces with its carrier"
        res.append(cands[0])
    return sorted(res), ""


def run_case(case, keep=False):
    t0 = time.time()
    scratch = SCRATCH / case
    try:
        _ocp()
        p = subprocess.run([str(PY225), "-I", str(HERE / "gt_ops_stage1.py"), str(DATA / case), str(scratch)],
                           capture_output=True, text=True, timeout=600)
        if p.returncode != 0:
            raise RuntimeError("stage1 failed: " + (p.stderr or p.stdout)[-400:])
        out = stage2(case, scratch)
        json.dump(out, open(DATA / case / "gt_ops.json", "w"), separators=(",", ":"))
        if not keep:
            shutil.rmtree(scratch, ignore_errors=True)
        return case, "ok" if out["sdk_rebuild"] == "ok" else out["sdk_rebuild"], time.time() - t0, \
            json.dumps(out.get("check")) if out["sdk_rebuild"] != "ok" else ""
    except Exception as e:
        import traceback
        err = traceback.format_exc()[-600:]
        json.dump({"case": case, "sdk_rebuild": "error", "error": err, "faces": []}, open(DATA / case / "gt_ops.json", "w"))
        return case, "error", time.time() - t0, err


def report(results):
    faces, orig, blend, stat = [], {}, {"n": 0, "solved": 0}, {}
    amb = {}
    for c in sorted(os.listdir(DATA)):
        f = DATA / c / "gt_ops.json"
        if not f.exists():
            continue
        d = json.load(open(f))
        stat[d["sdk_rebuild"]] = stat.get(d["sdk_rebuild"], 0) + 1
        for e in d.get("faces", []):
            k = (e["type"], e["origin"])
            orig[k] = orig.get(k, 0) + 1
            if "blend" in e:
                blend["n"] += 1
                blend["solved"] += e["blend"]["supports"] is not None
    tot = sum(orig.values())
    lines = ["# GT_OPS_REPORT", "", f"cases by status: {stat}", f"faces labelled: {tot}", "",
             "## origin x type (faces)", "", "| origin | " + " | ".join(sorted({t for t, _ in orig})) + " | total |",
             "|---|" + "---|" * (len({t for t, _ in orig}) + 1)]
    types = sorted({t for t, _ in orig})
    for o in sorted({o for _, o in orig}):
        row = [orig.get((t, o), 0) for t in types]
        lines.append(f"| {o} | " + " | ".join(map(str, row)) + f" | {sum(row)} |")
    lines += ["", f"blend faces: {blend['n']}, supports resolved: {blend['solved']}", "", "## failures", ""]
    bad = [r for r in results if r[1] != "ok"]
    lines += [f"- {c}: {s} {m[:300]}" for c, s, _, m in bad] or ["(none)"]
    (DATA / "GT_OPS_REPORT.md").write_text("\n".join(lines) + "\n")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--keep-scratch", action="store_true")
    a = ap.parse_args()
    cases = a.cases or sorted(c for c in os.listdir(DATA) if c.startswith("case-"))
    t0 = time.time()
    if len(cases) == 1 or a.workers == 1:
        results = [run_case(c, a.keep_scratch) for c in cases]
    else:
        with ProcessPoolExecutor(a.workers) as ex:
            results = list(ex.map(run_case, cases, [a.keep_scratch] * len(cases)))
    print(report(results) if not a.cases else "\n".join(f"{c} {s} {t:.1f}s {m[:200]}" for c, s, t, m in results))
    print(f"done {len(cases)} cases in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
