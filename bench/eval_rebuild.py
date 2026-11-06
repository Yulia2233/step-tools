#!/usr/bin/env python3
"""Can the surface be rebuilt from the derived construction parameters alone?

For every derived sweep/loft line of a case: build the surface the line describes (loft through the listed sections; pipe the
profile along a spline interpolating the rail) and measure the largest distance from points on the group's target faces to
it, relative to the bbox diagonal. Uses OCC directly, independent of SimpleCADAPI's loft/sweep defaults.

  python -I bench/eval_rebuild.py [--cases ...] [--workers 8]
"""
import argparse, json, math, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def wire_of(sec):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeWire
    from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt
    o, n = np.asarray(sec["o"], float), np.asarray(sec["n"], float)
    if "circle" in sec:
        c = gp_Circ(gp_Ax2(gp_Pnt(*o), gp_Dir(*n)), float(sec["circle"]))
        return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(c).Edge()).Wire()
    if "loop" in sec:
        from OCP.GC import GC_MakeArcOfCircle
        x = np.asarray(sec["x"], float)
        y = np.cross(n, x)
        W = lambda u, v: gp_Pnt(*(o + x * u + y * v))
        mk = BRepBuilderAPI_MakeWire()
        cur = sec["loop"]["s"]
        for sg in sec["loop"]["e"]:
            if sg[0] == "L":
                mk.Add(BRepBuilderAPI_MakeEdge(W(*cur), W(sg[1], sg[2])).Edge())
                cur = sg[1:3]
            else:
                cx, cy, ex, ey, sd = sg[1:6]
                a0 = math.atan2(cur[1] - cy, cur[0] - cx)
                a1 = math.atan2(ey - cy, ex - cx)
                if sd > 0 and a1 <= a0:
                    a1 += 2 * math.pi
                if sd < 0 and a1 >= a0:
                    a1 -= 2 * math.pi
                am = (a0 + a1) / 2
                R = math.hypot(cur[0] - cx, cur[1] - cy)
                arc = GC_MakeArcOfCircle(W(*cur), W(cx + R * math.cos(am), cy + R * math.sin(am)), W(ex, ey)).Value()
                mk.Add(BRepBuilderAPI_MakeEdge(arc).Edge())
                cur = [ex, ey]
        return mk.Wire()
    if "bspline" in sec:
        from OCP.Geom import Geom_BSplineCurve
        from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal
        from OCP.TColgp import TColgp_Array1OfPnt
        bs = sec["bspline"]
        x = np.asarray(sec["x"], float)
        y = np.cross(n, x)
        P = TColgp_Array1OfPnt(1, len(bs["poles"]))
        for k, (u, v) in enumerate(bs["poles"]):
            P.SetValue(k + 1, gp_Pnt(*(o + x * u + y * v)))
        K = TColStd_Array1OfReal(1, len(bs["knots"]))
        M = TColStd_Array1OfInteger(1, len(bs["mult"]))
        for k, (kv, mv) in enumerate(zip(bs["knots"], bs["mult"])):
            K.SetValue(k + 1, float(kv))
            M.SetValue(k + 1, int(mv))
        if "w" in bs:
            Wt = TColStd_Array1OfReal(1, len(bs["w"]))
            for k, w in enumerate(bs["w"]):
                Wt.SetValue(k + 1, float(w))
            c = Geom_BSplineCurve(P, Wt, K, M, int(bs["deg"]), bool(bs.get("periodic")))
        else:
            c = Geom_BSplineCurve(P, K, M, int(bs["deg"]), bool(bs.get("periodic")))
        return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(c).Edge()).Wire()
    if "through" in sec or "spline" in sec:
        from OCP.GeomAPI import GeomAPI_Interpolate
        from OCP.TColgp import TColgp_HArray1OfPnt
        x = np.asarray(sec["x"], float)
        y = np.cross(n, x)
        pts2 = sec.get("through") or sec.get("spline")
        arr = TColgp_HArray1OfPnt(1, len(pts2))
        for k, (u, v) in enumerate(pts2):
            arr.SetValue(k + 1, gp_Pnt(*(o + x * u + y * v)))
        it = GeomAPI_Interpolate(arr, True, 1e-7)
        it.Perform()
        return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(it.Curve()).Edge()).Wire()
    if "poly" in sec:
        x = np.asarray(sec["x"], float)
        y = np.cross(n, x)
        poly = BRepBuilderAPI_MakePolygon()
        for u, v in sec["poly"]:
            poly.Add(gp_Pnt(*(o + x * u + y * v)))
        poly.Close()
        return poly.Wire()
    return None


def surface_of(line):
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell, BRepOffsetAPI_ThruSections
    if line["op"] == "loft":
        ws = [wire_of(s) for s in line.get("sections", [])]
        if len(ws) < 2 or any(w is None for w in ws):
            return None
        ts = BRepOffsetAPI_ThruSections(False, False, 1e-6)
        for w in ws:
            ts.AddWire(w)
        ts.Build()
        return ts.Shape() if ts.IsDone() else None
    prof = line.get("profile")
    rail = line.get("rail")
    if not prof or not rail or wire_of(prof) is None:
        return None
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.GeomAPI import GeomAPI_PointsToBSpline
    from OCP.TColgp import TColgp_Array1OfPnt
    from OCP.gp import gp_Pnt
    if line.get("rail_line"):
        e = BRepBuilderAPI_MakeEdge(gp_Pnt(*rail[0]), gp_Pnt(*rail[-1])).Edge()
    else:
        from OCP.GeomAPI import GeomAPI_Interpolate
        from OCP.TColgp import TColgp_HArray1OfPnt
        arr = TColgp_HArray1OfPnt(1, len(rail))
        for k, p in enumerate(rail):
            arr.SetValue(k + 1, gp_Pnt(*p))
        it = GeomAPI_Interpolate(arr, bool(line.get("rail_closed")), 1e-7)
        it.Perform()
        e = BRepBuilderAPI_MakeEdge(it.Curve()).Edge()
    spine = BRepBuilderAPI_MakeWire(e).Wire()
    best = None
    modes = ("corrected", "frenet") if line.get("frame") is None else (("frenet",) if line["frame"].startswith("frenet") else ("corrected",))
    for mode in modes:
        ps = BRepOffsetAPI_MakePipeShell(spine)
        if mode == "frenet":
            ps.SetMode(True)
        ps.Add(wire_of(prof), False, False)
        try:
            ps.Build()
        except Exception:
            continue
        if ps.IsDone():
            best = best or []
            best.append(ps.Shape())
    return best


def deviation(points, shape):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.gp import gp_Pnt
    worst = 0.0
    for p in points:
        d = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(*p)).Vertex(), shape)
        d.Perform()
        worst = max(worst, d.Value() if d.IsDone() else 1e9)
    return worst


def one(case):
    sys.path.insert(0, str(ROOT / "cand"))
    import geomnorm, pipeline, stepir
    out = pipeline.run(HERE / "data" / case / "orig.step")
    infos, newid = stepir.build_ir.last_infos, stepir.build_ir.last_newid
    from simplecadapi.inspect import brep
    m = brep.load_step_rbrepmodel(path=str(HERE / "data" / case / "orig.step"))
    head = json.loads(out["lines"][0])
    bb = np.asarray(head["bbox"], float)
    diag = float(np.linalg.norm(bb[1] - bb[0]))
    res = []
    for l in (json.loads(x) for x in out["lines"] if '"derived":"op"' in x):
        if l["op"] not in ("loft", "sweep"):
            continue
        members = [k for k, inf in enumerate(infos) if newid.get(k) in set(l["faces"])]
        pts = []
        for k in members:
            s = geomnorm.samples(geomnorm._face_of(m, k), diag)
            if s is not None:
                pts += s[0][:: max(1, len(s[0]) // 20)].tolist()
        shp = surface_of(l)
        if shp is None:
            res.append({"op": l["op"], "built": False})
            continue
        shapes = shp if isinstance(shp, list) else [shp]
        dev = min(deviation(pts, s) for s in shapes) / diag
        res.append({"op": l["op"], "built": True, "dev": dev})
    return case, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    cases = a.cases or sorted(p.name for p in (HERE / "data").iterdir() if (p / "orig.step").exists())
    import multiprocessing as mp
    with ProcessPoolExecutor(a.workers, mp_context=mp.get_context("spawn")) as ex:
        rs = list(ex.map(one, cases))
    for op in ("sweep", "loft"):
        xs = [r for _, rr in rs for r in rr if r["op"] == op]
        devs = [r["dev"] for r in xs if r.get("built")]
        q = np.round(np.quantile(devs, [0.5, 0.75, 0.9]), 4).tolist() if devs else None
        print(f"{op.upper()}: lines {len(xs)}  rebuilt {len(devs)}  dev/diag q50/q75/q90 {q}  "
              f"<0.5%: {sum(d < 0.005 for d in devs)}  <2%: {sum(d < 0.02 for d in devs)}")
    worst = sorted(((r["dev"], c, r["op"]) for c, rr in rs for r in rr if r.get("built")), reverse=True)[:8]
    print("worst:", [(c, o, round(d, 4)) for d, c, o in worst])
    print("not built:", [(c, r["op"]) for c, rr in rs for r in rr if not r.get("built")][:10])


if __name__ == "__main__":
    main()
