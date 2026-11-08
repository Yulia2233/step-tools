#!/usr/bin/env python3
"""Independent check of the faces a STEPIR leaves out ("implied"): every one must lie on the sweep of a loop the IR prints.

  python verify_implied.py <cand dir> part.step [part.step ...]      (prints one JSON line per part)

The IR claims that a face without a record is a wall of a prism (`ext`/`twin`) or of a loop prism (`prism`): the loop of
the holding face swept along its normal. Here every implied B-rep face is meshed and each mesh node is checked against
those sweeps, rebuilt from the printed IR text alone (local frame o/n/x, loop segments; B segments evaluated exactly,
S segments as the polyline through start, centroid and end, so their deviation is only indicative). Reports per part the
number of implied faces, how many have all nodes within tolerance, and the worst deviation.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
import stepir      # noqa: E402
import sdk_ocp     # noqa: E402


def bspline_points(start, sg, n=48):
    deg, poles = sg[1], [start] + sg[2]
    opt = sg[3] if len(sg) > 3 else {}
    P = np.asarray(poles, float)
    w = np.asarray(opt.get("w", [1.0] * len(P)), float)
    if "k" in opt:
        kn = [k for k, m in zip(opt["k"], opt["m"]) for _ in range(m)]
    else:
        kn = [0.0] * (deg + 1) + [1.0] * (deg + 1)
    from scipy.interpolate import BSpline
    H = np.hstack([P * w[:, None], w[:, None]])
    ts = np.linspace(kn[deg], kn[len(kn) - deg - 1], n)
    Q = BSpline(np.asarray(kn), H, deg)(ts)
    return Q[:, :2] / Q[:, 2:3]


def outline(lp, n=96):
    """Dense 2D points of a loop."""
    if "c" in lp:
        cx, cy, r = lp["c"]
        t = np.linspace(0, 2 * math.pi, 4 * n)
        return np.c_[cx + r * np.cos(t), cy + r * np.sin(t)], True
    cur = np.asarray(lp["s"], float)
    out, exact = [cur[None]], True
    for sg in lp["e"]:
        end = np.asarray(stepir.seg_end(sg), float)
        if sg[0] == "L":
            out.append(cur + np.linspace(0, 1, n)[:, None] * (end - cur))
        elif sg[0] == "A":
            c = np.asarray(sg[1:3], float)
            a0, a1 = math.atan2(*(cur - c)[::-1]), math.atan2(*(end - c)[::-1])
            s = sg[5]
            if s > 0 and a1 <= a0:
                a1 += 2 * math.pi
            if s < 0 and a1 >= a0:
                a1 -= 2 * math.pi
            r = float(np.linalg.norm(cur - c))
            t = np.linspace(a0, a1, n)
            out.append(np.c_[c[0] + r * np.cos(t), c[1] + r * np.sin(t)])
        elif sg[0] == "B":
            out.append(bspline_points(cur.tolist(), sg, n))
        elif sg[0] == "E":
            c, a, b, U, s = np.asarray(sg[1:3], float), float(sg[3]), float(sg[4]), np.asarray(sg[5:7], float), sg[9]
            U = U / (np.linalg.norm(U) or 1.0)
            V = np.array([-U[1], U[0]])
            ang = lambda q: math.atan2(float((q - c) @ V) / b, float((q - c) @ U) / a)
            t0, t1 = ang(cur), ang(end)
            if s > 0 and t1 <= t0:
                t1 += 2 * math.pi
            if s < 0 and t1 >= t0:
                t1 -= 2 * math.pi
            t = np.linspace(t0, t1, 4 * n)
            out.append(c + np.outer(a * np.cos(t), U) + np.outer(b * np.sin(t), V))
        elif sg[0] == "S":
            m = np.asarray(sg[4], float)
            out.append(np.vstack([cur + np.linspace(0, 1, n // 2)[:, None] * (m - cur), m + np.linspace(0, 1, n // 2)[:, None] * (end - m)]))
            exact = False
        else:
            out.append(np.vstack([cur, end]))
            exact = False
        cur = end
    return np.vstack(out), exact


def sweeps(recs):
    out = []
    for j in recs.values():
        if j.get("t") != "PLANE":
            continue
        o, n, x = (np.asarray(j[k], float) for k in ("o", "n", "x"))
        y = np.cross(n, x)
        loops = j.get("loops") or ([{"s": [j["rect"][0], j["rect"][1]], "e": [["L", j["rect"][2], j["rect"][1]], ["L", j["rect"][2], j["rect"][3]],
                                                                            ["L", j["rect"][0], j["rect"][3]], ["L", j["rect"][0], j["rect"][1]]]}] if "rect" in j else [])
        if "ext" in j:
            h = float(j["ext"]["h"])
            for lp in loops:
                pts, ex = outline(lp)
                out.append((o, n, x, y, pts, ex, (0.0, h) if j["ext"].get("cut") else (-h, 0.0)))
        for i, _to, dz in j.get("prism", []):
            pts, ex = outline(loops[i])
            out.append((o, n, x, y, pts, ex, (min(0.0, dz), max(0.0, dz))))
    return out


def seg_dist(pts, u, v):
    """Distance from (u, v) to the polyline through pts."""
    a, b = pts[:-1], pts[1:]
    ab = b - a
    q = np.array([u, v])
    t = np.clip(np.einsum("ij,ij->i", q - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-30), 0.0, 1.0)
    return float(np.min(np.linalg.norm(a + t[:, None] * ab - q, axis=1)))


def nodes(face, defl):
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopLoc import TopLoc_Location
    BRepMesh_IncrementalMesh(face, defl, False, 0.3, True)
    loc = TopLoc_Location()
    tri = BRep_Tool.Triangulation_s(face, loc)
    if tri is None:
        return np.zeros((0, 3))
    T = loc.Transformation()
    return np.array([[q.X(), q.Y(), q.Z()] for q in (tri.Node(i).Transformed(T) for i in range(1, tri.NbNodes() + 1))])


def check(path):
    from simplecadapi.inspect import brep
    lines = stepir.build_ir(str(path))
    head = json.loads(lines[0])
    recs = {j["id"]: j for j in (json.loads(l) for l in lines[1:])}
    fmap = stepir.build_ir.last_face_map
    diag = float(np.linalg.norm(np.subtract(head["bbox"][1], head["bbox"][0])))
    model = brep.load_step_rbrepmodel(path=str(path))
    sw = sweeps(recs)
    tol = 2e-3 + 1e-5 * diag
    res = {"part": Path(path).name, "implied": 0, "ok": 0, "worst": 0.0, "worst_exact": 0.0, "bad": []}
    for k, ir in fmap.items():
        if ir in recs:
            continue
        res["implied"] += 1
        P = nodes(sdk_ocp.face(model, k), 1e-3 * diag)
        worst, worst_exact = 0.0, 0.0
        for p in P:
            best, best_ex = 1e18, False
            for o, n, x, y, pts, ex, (z0, z1) in sw:
                w = p - o
                z = float(w @ n)
                if z < z0 - tol or z > z1 + tol:
                    continue
                d = seg_dist(pts, float(w @ x), float(w @ y))
                if d < best:
                    best, best_ex = d, ex
            worst = max(worst, best)
            if best_ex:
                worst_exact = max(worst_exact, best)
        res["worst"] = max(res["worst"], worst)
        res["worst_exact"] = max(res["worst_exact"], worst_exact)
        if worst <= max(tol, 2e-3 * diag):
            res["ok"] += 1
        else:
            res["bad"].append([ir, round(worst, 4)])
    res["worst"], res["worst_exact"] = round(res["worst"], 5), round(res["worst_exact"], 5)
    res["bad"] = res["bad"][:10]
    return res


if __name__ == "__main__":
    for p in sys.argv[2:]:
        try:
            print(json.dumps(check(p)), flush=True)
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"part": Path(p).name, "error": f"{type(e).__name__}: {e}"[:300]}), flush=True)
