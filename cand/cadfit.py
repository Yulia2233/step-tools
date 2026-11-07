#!/usr/bin/env python3
"""Which operation generated each face? Measure it, don't guess.

  cadfit.py part.step                      what operation each face came from, and the face groups one operation explains
  cadfit.py part.step --test revolve --axis 0,0,1 --point 0,0,0 --faces 3,7,11
  cadfit.py part.step --test extrude --dir 0,0,1 --faces 2,4,5
  cadfit.py part.step --test helical --axis 0,0,1 --point 0,0,0 --pitch 8 --faces 9

Every generating operation SimpleCADAPI offers is a one-parameter rigid motion applied to a profile: `extrude_rsolid`
translates it, `revolve_rsolid` rotates it, `helical_sweep_rsolid` screws it. Such a motion is a twist (c, w) - linear
part c, angular part w - whose velocity at a point is v(x) = c + w x x. A surface is swept by that motion exactly when
the velocity is tangent to it everywhere, i.e. for every surface point

    n . c + (x cross n) . w = 0

which is ONE LINEAR EQUATION in the six unknowns (c, w). So "what made this face" is not a guess: stack the equation
over sampled points, and the null space of the resulting 6x6 matrix is the set of motions that could have swept it.
The residual says how well, and the NULLITY says how ambiguous the answer is - a cylinder honestly admits both a
translation (extrude) and a rotation (revolve), and this reports both instead of inventing a preference. The ambiguity
is then resolved the way a person resolves it: pick the motion that explains the most faces at once.

Point/normal samples are exact (surface D1 at the triangulation's UV nodes), not facet approximations, so the residual
measures the geometry rather than the mesh.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cadthreads  # noqa: E402
import sdk_ocp  # noqa: E402
cadthreads.limit()
import numpy as np  # noqa: E402

os.environ.setdefault("STEPIR_NDIG", "4")
TOL = 3.0e-4            # residual below this (normalised by the bbox diagonal) counts as "this motion explains the face"; exact sweeps fit to ~1e-9, a lofted twist to >7e-4
GAP = 10.0              # the first REJECTED motion must violate the face this many times harder, or the face cannot tell
MAX_PTS = 400           # samples per face; more does not change the fit, the equation is heavily over-determined


def samples(face, deflection):
    """Exact points and unit normals on one face, taken at its triangulation's UV nodes and triangle centroids."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopLoc import TopLoc_Location
    BRepMesh_IncrementalMesh(face, deflection, False, 8.0, True)
    tri = BRep_Tool.Triangulation_s(face, TopLoc_Location())
    if tri is None or not tri.HasUVNodes():
        return None
    uv = np.array([[tri.UVNode(i).X(), tri.UVNode(i).Y()] for i in range(1, tri.NbNodes() + 1)])
    mid = np.array([[(uv[a - 1] + uv[b - 1] + uv[c - 1]) / 3.0
                     for a, b, c in [tri.Triangle(i).Get()]][0] for i in range(1, tri.NbTriangles() + 1)])
    uv = np.vstack([uv, mid]) if len(mid) else uv
    if len(uv) > MAX_PTS:
        uv = uv[np.linspace(0, len(uv) - 1, MAX_PTS).astype(int)]
    ad = BRepAdaptor_Surface(face)
    from OCP.gp import gp_Pnt, gp_Vec
    pts, nrm = [], []
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    for u, v in uv:
        ad.D1(float(u), float(v), p, du, dv)
        n = np.cross([du.X(), du.Y(), du.Z()], [dv.X(), dv.Y(), dv.Z()])
        ln = float(np.linalg.norm(n))
        if ln < 1e-12:
            continue                      # a degenerate corner (pole of a sphere/cone): no normal there
        pts.append([p.X(), p.Y(), p.Z()])
        nrm.append(n / ln)
    if len(pts) < 6:
        return None
    return np.asarray(pts), np.asarray(nrm)


def rows(pts, nrm, origin, scale):
    """One row per sample: the coefficients of n.c + (x cross n).w = 0, in normalised coordinates."""
    x = (pts - origin) / scale
    return np.hstack([nrm, np.cross(x, nrm)])


def nullspace(A, n_pts):
    """Eigenvalues of A^T A (ascending) and their directions: the motions that sweep the face, best first."""
    w, V = np.linalg.eigh(A.T @ A / max(n_pts, 1))
    return np.sqrt(np.maximum(w, 0.0)), V.T          # residual_k = sqrt(mean squared violation) for direction V[k]


def classify(twist, origin, scale):
    """Name the motion a twist (c, w) stands for, in the part's own units."""
    c, w = np.asarray(twist[:3], float), np.asarray(twist[3:], float)
    nw = float(np.linalg.norm(w))
    if nw < 1e-6:
        d = c / max(float(np.linalg.norm(c)), 1e-12)
        return {"op": "extrude", "dir": [round(float(v), 5) for v in d]}
    axis = w / nw
    point = origin + scale * np.cross(w, c) / (nw * nw)
    pitch = 2.0 * np.pi * float(np.dot(c, w)) / (nw * nw) * scale
    rec = {"axis": [round(float(v), 5) for v in axis], "point": [round(float(v), 4) for v in point]}
    if abs(pitch) < 1e-3 * scale:
        return {"op": "revolve", **rec}
    if abs(pitch) > 10.0 * scale:
        # a screw whose pitch dwarfs the part is a translation with numerical noise in the rotation, not a helix
        d = c / max(float(np.linalg.norm(c)), 1e-12)
        return {"op": "extrude", "dir": [round(float(v), 5) for v in d], "degenerate_screw": True}
    return {"op": "helical", **rec, "pitch": round(pitch, 4)}


def same_motion(a, b, scale, deg=2.0, rel=0.02):
    """Two fitted motions are the same operation when their axes agree in direction AND in position.

    Rounded coordinates are not enough to merge them: two fits of one real axis come back a fraction of a degree apart
    and print as different numbers, which is how a part with one turned feature ends up listed as six revolutions.
    """
    if a["op"] != b["op"]:
        return False
    da, db = a.get("axis") or a.get("dir"), b.get("axis") or b.get("dir")
    if abs(abs(float(np.dot(unit(da), unit(db)))) - 1.0) > (np.radians(deg) ** 2) / 2:
        return False
    if "point" in a and "point" in b:
        w = np.asarray(a["point"], float) - np.asarray(b["point"], float)
        d = unit(da)
        if float(np.linalg.norm(w - np.dot(w, d) * d)) > rel * scale:      # parallel but offset axes are different
            return False
    if "pitch" in a and "pitch" in b and abs(a["pitch"] - b["pitch"]) > rel * scale:
        return False
    return True


def residual_of(twist, A, n_pts):
    return float(np.sqrt(np.mean((A @ np.asarray(twist, float)) ** 2))) if n_pts else float("inf")


def twist_of(spec, origin, scale):
    """The twist a named hypothesis stands for, normalised the same way the rows are."""
    op = spec["op"]
    if op == "extrude":
        d = np.asarray(spec["dir"], float)
        return np.hstack([d / np.linalg.norm(d), [0, 0, 0]])
    a = np.asarray(spec["axis"], float)
    a = a / np.linalg.norm(a)
    p = (np.asarray(spec["point"], float) - origin) / scale
    c = np.cross(p, a) + (float(spec.get("pitch", 0.0)) / scale / (2 * np.pi)) * a
    t = np.hstack([c, a])
    return t / np.linalg.norm(t)


def load(path):
    from simplecadapi.inspect import brep
    import stepir
    lines = stepir.build_ir(str(path))
    fmap = getattr(stepir.build_ir, "last_face_map", {})            # original face index -> IR id
    head = json.loads(lines[0])
    bb = np.asarray(head["bbox"], float)
    scale = float(np.linalg.norm(bb[1] - bb[0])) or 1.0
    origin = bb.mean(axis=0)
    model = brep.load_step_rbrepmodel(path=str(path))
    types = {}
    for ln in lines[1:]:
        if ln.strip():
            r = json.loads(ln)
            types[r["id"]] = r["t"]
    per = {}
    for i, face in enumerate(sdk_ocp.faces(model)):
        if i not in fmap:
            continue
        s = samples(face, max(scale * 1e-4, 1e-6))
        if s is None:
            continue
        pts, nrm = s
        per[fmap[i]] = rows(pts, nrm, origin, scale)
    return {"part": Path(path).name, "scale": scale, "origin": origin, "rows": per, "types": types}


def describe(N, res, origin, scale):
    """What the null space of one face means, in operations.

    The DIMENSION of the null space is itself the answer to "how sure can anyone be":
      0  no rigid motion sweeps this face at all - it came from a loft, a sweep along a curved rail, or a spline patch;
      1  exactly one motion sweeps it (cone, torus, a general surface of revolution) - decisive evidence;
      2  a cylinder: translation along its axis, rotation about it, and every screw between, all sweep it. The AXIS is
         certain, the operation is not - saying "extrude" here would be inventing a preference the geometry does not have;
      >=3 a plane or a sphere: far too many motions sweep it to be evidence of anything.
    """
    k = int((res <= TOL).sum())
    r0 = round(float(res[0]), 6)
    # A small, nearly flat patch is swept - to within tolerance - by half the motions there are, because its equations are
    # all nearly the same equation. That is a fact about the patch, not an answer about the part, so say so: unless the
    # first REJECTED motion violates the face much harder than the accepted ones, this face simply cannot tell.
    if k < 6 and not (res[k] > GAP * max(res[k - 1] if k else 0.0, TOL)):
        return {"nullity": k, "decisive": False, "ill_conditioned": True, "residual": r0, "ops": [],
                "note": "face too small or too flat to identify its motion (no clear gap in the fit)"}
    if k == 0:
        return {"nullity": 0, "decisive": False, "ops": [], "residual": r0,
                "note": "no rigid motion sweeps this face: loft / sweep along a curved rail / spline patch"}
    N = np.asarray(list(res_dirs(N, k)))                             # k x 6, the motions that sweep it
    if k == 1:
        return {"nullity": 1, "decisive": True, "residual": r0,
                "ops": [classify(N[0], origin, scale)]}
    # a combination of the null-space motions whose angular part vanishes is a pure translation: the face is then a
    # prism/cylinder along it. Those combinations are the left null space of the angular block.
    Nw, Nc = N[:, 3:], N[:, :3]
    w, V = np.linalg.eigh(Nw @ Nw.T)
    coef = [V[:, i] for i in range(len(w)) if w[i] < 1e-12]
    dirs = [unit(c @ Nc) for c in coef]
    if k == 2 and len(dirs) == 1:
        a = dirs[0]
        rot = next((classify(v, origin, scale) for v in N if np.linalg.norm(v[3:]) > 1e-8), None)
        pt = rot.get("point") if rot else None
        return {"nullity": 2, "decisive": True, "residual": r0, "axis": [round(float(x), 5) for x in a],
                "ops": [{"op": "extrude", "dir": [round(float(x), 5) for x in a]},
                        {"op": "revolve", "axis": [round(float(x), 5) for x in a], "point": pt},
                        {"op": "helical", "axis": [round(float(x), 5) for x in a], "point": pt, "pitch": "any"}],
                "note": "cylindrical: the axis is certain, the operation is not"}
    return {"nullity": k, "decisive": False, "residual": r0, "ops": [],
            "note": "too many motions sweep this face (plane or sphere) to tell which operation made it"}


def res_dirs(A, k):
    res, dirs = nullspace(A, len(A))
    return dirs[:k]


def unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def face_ops(part):
    out = {}
    for fid, A in part["rows"].items():
        res, _ = nullspace(A, len(A))
        d = describe(A, res, part["origin"], part["scale"])
        out[fid] = {"t": part["types"].get(fid), **d}
    return out


def groups(part, fo, max_pairs=40000):
    """Motions that sweep several faces at once: one such motion is one modelling operation.

    Seeds come from PAIRS of faces, never single ones. A face on its own is often too small to name its own motion - its
    equations are all nearly the same equation, so half the motions there are fit it to within tolerance - but two faces
    lying apart pin a motion down between them even when neither could alone. A pair is used as a seed only when its
    combined system has a one-dimensional null space with a clear gap, i.e. it determines exactly one motion. Each such
    motion is then scored on every face of the part, and the motions are taken greedily by how much they explain.
    """
    ids = sorted(part["rows"])
    pairs = [(i, j) for a, i in enumerate(ids) for j in ids[a + 1:]]
    step = max(1, len(pairs) // max_pairs)
    cand = []
    for i, j in pairs[::step]:
        A = np.vstack([part["rows"][i], part["rows"][j]])
        res, dirs = nullspace(A, len(A))
        if res[0] <= TOL and res[1] > GAP * max(res[0], TOL):        # the pair determines exactly one motion
            cand.append((dirs[0], (i, j)))
    seen, scored = set(), []
    for t, seed in cand:
        cover = [f for f, A in part["rows"].items() if residual_of(t, A, len(A)) <= TOL]
        if len(cover) < 2:
            continue
        key = tuple(sorted(cover))
        if key in seen:
            continue
        seen.add(key)
        worst = max(residual_of(t, part["rows"][f], len(part["rows"][f])) for f in cover)
        scored.append((len(cover), -worst, t, cover, seed, worst))
    scored.sort(key=lambda s: (-s[0], s[1]))
    # Report every distinct motion, not just the ones a greedy cover happens to need: a box really is a prism along all
    # three of its axes, and a detector that names two of them is hiding a third that is just as true. Duplicates are
    # merged on the motion itself (same operation, axis and location), not on the face set.
    out, claimed = [], set()
    for _, _, t, cover, seed, worst in scored:
        m = classify(t, part["origin"], part["scale"])
        if len(out) >= 8 or any(same_motion(m, o, part["scale"]) for o in out):
            continue
        out.append({**m, "faces": sorted(cover), "determined_by": list(seed),
                    "first_explained_here": sorted(f for f in cover if f not in claimed),
                    "residual": round(float(worst), 6)})
        claimed.update(cover)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--test", choices=["extrude", "revolve", "helical"])
    ap.add_argument("--axis"), ap.add_argument("--point"), ap.add_argument("--dir"), ap.add_argument("--pitch", type=float, default=0.0)
    ap.add_argument("--faces", help="comma-separated IR face ids; default: every face")
    a = ap.parse_args()
    part = load(a.target)
    pick = [int(x) for x in a.faces.split(",")] if a.faces else sorted(part["rows"])
    if a.test:
        spec = {"op": a.test, "pitch": a.pitch}
        if a.test == "extrude":
            spec["dir"] = [float(x) for x in a.dir.split(",")]
        else:
            spec["axis"] = [float(x) for x in a.axis.split(",")]
            spec["point"] = [float(x) for x in (a.point or "0,0,0").split(",")]
        t = twist_of(spec, part["origin"], part["scale"])
        per = {f: round(residual_of(t, part["rows"][f], len(part["rows"][f])), 6) for f in pick if f in part["rows"]}
        ok = sorted(f for f, r in per.items() if r <= TOL)
        print(json.dumps({"hypothesis": spec, "tolerance": TOL, "explained": ok,
                          "rejected": sorted(set(per) - set(ok)), "residual_per_face": per,
                          "verdict": "consistent" if len(ok) == len(per) else
                                     ("partly consistent" if ok else "rejected")}, ensure_ascii=False))
        return
    fo = face_ops(part)
    print(json.dumps({"part": part["part"], "faces": {str(k): fo[k] for k in sorted(fo)},
                      "groups": groups(part, fo)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
