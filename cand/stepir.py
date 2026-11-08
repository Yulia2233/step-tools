#!/usr/bin/env python3
"""STEP -> compact inspector IR (JSONL, one face per line), version 3 (SimpleCADAPI inspector only).

Built exclusively on simplecadapi.inspect.brep (load_step_rbrepmodel, describe_entity,
inspect_face_boundaries_rdescriptor, inspect_step_rsummary); numpy is used for frame arithmetic only.

Input representation for the STEP->SimpleCADAPI model. Raw STEP text of real parts is 60K-230K Qwen tokens;
this IR keeps what is needed to write a feature-tree program: faces, analytic carriers, ordered boundary
loops in a face-local 2D frame (chain-encoded), extrusion (prism) structure, rounded numbers.

Line 1  : global header (unit, bbox, volume, area, counts, surface type histogram, #implied faces).
Lines 2+: one face each, ids stable within the file (sorted canonically), gaps = implied faces.

Planar face loops (local frame: origin o, x axis x, y = n x x, n outward):
  loop = {"s":[x,y], "e":[seg,...]}  chain from start point;  or {"c":[cx,cy,r]} for a full circle
  seg  = ["L",x,y] line to (x,y) | ["A",cx,cy,x,y,s] arc to (x,y) about centre (cx,cy), s=+1 ccw/-1 cw
         ["E",cx,cy,a,b,ux,uy,x,y,s] ellipse arc | ["S",deg,x,y,[mx,my]] spline to (x,y) via its centroid
  "rect":[u0,v0,u1,v1] replaces loops when the face is a single axis-aligned rectangle.
Prism structure: a cap face carries "ext":{"to":id_of_opposite_cap,"h":height}; the opposite cap is emitted
  with "twin":id (no loops: identical loops, translated by -h*n), and all lateral faces (planes parallel to n,
  cylinders with axis parallel to n) between the pair are omitted (implied by the loops).
  "cut":1 in ext: the caps face each other, i.e. they bound REMOVED material (slot/pocket); the twin then lies at
  +h*n and the loops swept along +n by h are the removed prism.
Non-planar faces: carrier parameters (p point, d axis, r radius, r2, ang, u/v ranges in degrees or length,
  cc=1 convex / 0 concave) and "adj" neighbour ids when few.
"""
import argparse
import json
import math
import os
import sys
from collections import Counter

import numpy as np
from simplecadapi.inspect import brep

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # python -I does not put the script's directory on the path
import geomnorm  # noqa: E402

NDIG = int(os.environ.get("STEPIR_NDIG", "4"))
ENDCAPS = os.environ.get("STEPIR_ENDCAPS", "0") == "1"   # cylinders/cones: explicit end-circle centres instead of p + v*d
TOL = 2e-3
DIAG = [1.0]            # bbox diagonal of the part being converted (edge recognition tolerances scale with it)


def r(x, n=None):
    n = NDIG if n is None else n
    v = round(float(x), n)
    if v == 0:
        return 0
    return int(v) if v == int(v) and abs(v) < 1e9 else v


def canon_frame(n):
    nx, ny, nz = n
    up = (0.0, 0.0, 1.0) if abs(nz) < 0.9 else (0.0, 1.0, 0.0)
    x = np.array([up[1] * nz - up[2] * ny, up[2] * nx - up[0] * nz, up[0] * ny - up[1] * nx])
    x = x / (np.linalg.norm(x) or 1.0)
    y = np.cross(np.asarray(n), x)
    return x, y



def reversed_face(model, index):
    """True when the face is stored reversed (its outward normal opposes the carrier normal => concave carrier)."""
    return geomnorm._face_of(model, index).Orientation().name.endswith("REVERSED")


SURF = {"PLANE": "PLANE", "CYLINDER": "CYL", "CONE": "CONE", "SPHERE": "SPHERE", "TORUS": "TORUS",
        "BSPLINE": "BSPL", "BEZIER": "BEZ"}
RANK = {"PLANE": 0, "CYL": 1, "CONE": 2, "SPHERE": 3, "TORUS": 4}


class Frame:
    def __init__(self, origin, n):
        self.o = np.asarray(origin, float)
        self.n = np.asarray(n, float)
        self.x, self.y = canon_frame(self.n)

    def to2d(self, p):
        d = np.asarray(p, float) - self.o
        return [float(d @ self.x), float(d @ self.y)]


def edge_seg(model, rec, frame):
    """Edge occurrence record -> (start_list, segment_or_None, circle_or_None)."""
    gt = rec["geometry_type"]
    start, end = np.asarray(rec["start"], float), np.asarray(rec["end"], float)
    P = (lambda p: [r(c) for c in frame.to2d(p)]) if frame else (lambda p: [r(c) for c in p])
    if gt == "LINE":
        return P(start), ["L"] + P(end), None
    ed = model.describe_entity(rec["entity_id"])["geometry"]
    par = ed["parameters"]
    closed = bool(ed.get("closed")) or float(np.linalg.norm(start - end)) < 1e-7
    fwd = rec["orientation"] == "FORWARD"
    if gt not in ("CIRCLE", "ELLIPSE"):
        rg = geomnorm.recognize_edge(model, rec, DIAG[0])
        if rg is not None and rg["kind"] == "LINE":
            return P(start), ["L"] + P(end), None
        if rg is not None:
            gt, fwd, closed = "CIRCLE", True, rg["closed"]
            par = {"center": rg["center"], "radius": rg["radius"], "axis_direction": rg["axis"]}
    if gt == "CIRCLE":
        cen = np.asarray(par["center"], float)
        rad = float(par["radius"])
        if closed:
            return None, None, ["C"] + P(cen) + [r(rad)]
        axis = np.asarray(par["axis_direction"], float)
        sense_axis = 1 if fwd else -1  # +1: traversal runs ccw about the circle axis
        if frame:
            s = sense_axis * (1 if float(axis @ frame.n) > 0 else -1)
            return P(start), ["A"] + P(cen) + P(end) + [s], None
        return P(start), ["A"] + P(cen) + P(end) + [sense_axis] + [r(c, 4) for c in axis], None
    if gt == "ELLIPSE":
        cen = np.asarray(par["center"], float)
        axis = np.asarray(par["axis_direction"], float)
        xdir = np.asarray(par["x_direction"], float)
        sense_axis = 1 if fwd else -1
        if frame:
            s = sense_axis * (1 if float(axis @ frame.n) > 0 else -1)
            u = [float(xdir @ frame.x), float(xdir @ frame.y)]
            return P(start), ["E"] + P(cen) + [r(par["major_radius"]), r(par["minor_radius"]), r(u[0], 4), r(u[1], 4)] + P(end) + [s], None
        return P(start), ["E"] + P(cen) + [r(par["major_radius"]), r(par["minor_radius"])] + P(end) + [sense_axis], None
    if frame:                                   # a planar loop spline: its exact poles when there are few
        bs = geomnorm.edge_bspline(model, rec)
        if bs is not None:
            poles, deg, kn, mu, w = bs
            seg = ["B", deg, [P(q) for q in poles[1:]]]
            opt = {}
            if len(kn) > 2:
                opt.update(k=[r(x, 6) for x in kn], m=mu)
            if w is not None:
                opt["w"] = [r(x, 6) for x in w]
            if opt:
                seg.append(opt)
            cen = ed.get("centroid", rec["start"])
            return P(start), ["S", par.get("degree", 0) if isinstance(par, dict) else 0] + P(end) + [P(cen), {"exact": seg}], None
    cen = ed.get("centroid", rec["start"])
    deg = par.get("degree", 0) if isinstance(par, dict) else 0
    return P(start), ["S", deg] + P(end) + [P(cen)], None


def settle_splines(loops, exact):
    """Planar loop splines carry their exact form until it is known whether it is needed: written as ["B", ...] in the
    loops whose index is in `exact` (their walls are implied, so the loop must say everything) or when it costs no more
    than the short form
    (a Bezier of at most 4 poles, about the size of ["S", ...]); otherwise the short ["S", ...] form stays."""
    out = []
    for i, lp in enumerate(loops):
        if "e" not in lp or not any(len(sg) == 6 and sg[0] == "S" for sg in lp["e"]):
            out.append(lp)
            continue
        e = []
        for sg in lp["e"]:
            if sg[0] == "S" and len(sg) == 6:
                b = sg[5]["exact"]
                e.append(b if i in exact or (len(b) == 3 and len(b[2]) <= 3) else sg[:5])
            else:
                e.append(sg)
        out.append({**lp, "e": e})
    return out


def seg_end(sg):
    """End point of a loop segment: ["L",x,y] | ["A",cx,cy,x,y,s] | ["E",cx,cy,a,b,ux,uy,x,y,s] | ["S",deg,x,y,[mx,my]] |
    ["B",deg,[[x,y],...]] (exact B-spline: poles after the start, the last one is the end)."""
    if sg[0] == "B":
        return list(sg[2][-1])
    return list(sg[{"L": 1, "A": 3, "E": 7, "S": 2}.get(sg[0], 1):][:2])


def coalesce(start, segs):
    """Merge consecutive collinear lines and consecutive arcs of one circle (cyclically). A neighbour's split shows up in a
    loop as an extra vertex on a straight edge or as a circle cut in two arcs, which says nothing about the shape."""
    def end_of(s):
        return s[1:3] if s[0] == "L" else s[3:5] if s[0] == "A" else None

    if len(segs) < 2 or any(end_of(s) is None for s in segs):
        return start, segs
    pts = [start] + [end_of(s) for s in segs]
    items = [{"t": s[0], "a": pts[k], "b": pts[k + 1], "s": s} for k, s in enumerate(segs)]

    def mergeable(A, B):
        if A["t"] != B["t"]:
            return False
        if A["t"] == "L":
            d1, d2 = (A["b"][0] - A["a"][0], A["b"][1] - A["a"][1]), (B["b"][0] - B["a"][0], B["b"][1] - B["a"][1])
            n1, n2 = float(np.hypot(*d1)), float(np.hypot(*d2))
            return (n1 > 0 and n2 > 0 and abs(d1[0] * d2[1] - d1[1] * d2[0]) <= 1e-6 * n1 * n2
                    and d1[0] * d2[0] + d1[1] * d2[1] > 0)
        a, b = A["s"], B["s"]
        return a[5] == b[5] and abs(a[1] - b[1]) <= 1e-3 and abs(a[2] - b[2]) <= 1e-3

    def join(A, B):
        s = ["L", B["b"][0], B["b"][1]] if A["t"] == "L" else ["A", A["s"][1], A["s"][2], B["b"][0], B["b"][1], A["s"][5]]
        return {"t": A["t"], "a": A["a"], "b": B["b"], "s": s}

    changed = True
    while changed and len(items) >= 2:
        changed = False
        for i in range(len(items)):
            j = (i + 1) % len(items)
            if mergeable(items[i], items[j]):
                m = join(items[i], items[j])
                items = items[:i] + [m] + items[j + 1:] if j > i else [m] + items[1:i]
                changed = True
                break
    return items[0]["a"], [it["s"] for it in items]


def loop_points(loops, fr):
    """World points that identify a planar face's boundary: loop vertices and circle centres - independent of how the
    boundary happens to be cut into edges."""
    out = []
    world = lambda uv: fr.o + fr.x * float(uv[0]) + fr.y * float(uv[1])
    for lp in loops:
        if "c" in lp:
            out.append(world(lp["c"][:2]))
            continue
        out.append(world(lp["s"]))
        for sg in lp["e"]:
            out.append(world(seg_end(sg)))
    return out


def face_loops_raw(model, loops_raw, frame):
    out, pts = [], []
    for lp in loops_raw:
        start, segs, circle = None, [], None
        for rec in lp["edges"]:
            pts.append(rec["start"])
            pts.append(rec["end"])
            s0, seg, circ = edge_seg(model, rec, frame)
            if circ is not None:
                circle = circ
            else:
                if start is None:
                    start = s0
                segs.append(seg)
        if circle is None and segs and frame is not None:
            start, segs = coalesce(start, segs)
            if len(segs) == 1 and segs[0][0] == "A" and np.hypot(segs[0][3] - start[0], segs[0][4] - start[1]) < 1e-6:
                cx, cy = segs[0][1], segs[0][2]
                circle = ["C", cx, cy, r(float(np.hypot(start[0] - cx, start[1] - cy)))]
                segs = []
        if circle is not None and not segs:
            out.append({"c": circle[1:]})
        else:
            out.append({"s": start, "e": segs})
    return out, pts


def face_loops(model, face_id, frame):
    b = brep.inspect_face_boundaries_rdescriptor(model_or_path=model, face_id=face_id, compact=True)
    return face_loops_raw(model, [b["outer"]] + list(b.get("inner", [])), frame)


def rect_of(loop):
    if "e" not in loop or len(loop["e"]) != 4 or any(s[0] != "L" for s in loop["e"]):
        return None
    pts = [loop["s"]] + [s[1:3] for s in loop["e"]]
    us = sorted({p[0] for p in pts})
    vs = sorted({p[1] for p in pts})
    if len(us) != 2 or len(vs) != 2:
        return None
    return [us[0], vs[0], us[1], vs[1]]


def vkey(p):
    return (round(float(p[0]), 2), round(float(p[1]), 2), round(float(p[2]), 2))


def _cap_segments(cap, loops):
    """World-space line segments and (centre, radius) arcs of a planar cap's loops."""
    fr = cap["frame"]
    world = lambda uv: fr.o + fr.x * float(uv[0]) + fr.y * float(uv[1])
    lines, arcs = [], []
    for lp in loops or []:
        if "c" in lp:
            arcs.append((world(lp["c"][:2]), float(lp["c"][2])))
            continue
        cur = lp["s"]
        for sg in lp["e"]:
            if sg[0] == "L":
                lines.append((world(cur), world(sg[1:3])))
                cur = sg[1:3]
            elif sg[0] == "A":
                arcs.append((world(sg[1:3]), float(np.linalg.norm(np.asarray(sg[1:3], float) - np.asarray(cur, float)))))
                cur = sg[3:5]
            else:
                cur = seg_end(sg)
    return lines, arcs


def _band(loops):
    """A planar face bounded by straight lines only (one loop): what the sweep of a straight edge looks like."""
    return bool(loops) and len(loops) == 1 and "e" in loops[0] and all(sg[0] == "L" for sg in loops[0]["e"])


def _swept(face, cap, lines, arcs, face_loops=None):
    """True when the lateral face is the sweep of one of the cap's loop edges (so the IR can drop it)."""
    tol = TOL * max(1.0, float(np.max(np.abs(cap["o"]))))
    if face["name"] == "PLANE":
        if face_loops is not None and not _band(face_loops):
            return False                                   # an arc or a hole in it: not the band swept from one edge
        # the plane must contain a cap edge AND the face must be the band swept from it: every boundary point, moved along
        # the cap normal into the cap plane, lies on that edge (a coplanar face of another shape is no side of this prism)
        n, o, na = face["n"], face["o"], np.asarray(cap["n"], float)
        P = [np.asarray(q, float) for q in face["pts"]]
        for p0, p1 in lines:
            if abs(float(n @ (p0 - o))) > tol or abs(float(n @ (p1 - o))) > tol:
                continue
            e = p1 - p0
            L2 = float(e @ e)
            ok = True
            for q in P:
                w = q - p0
                w = w - na * float(w @ na)
                t = min(1.0, max(0.0, float(w @ e) / L2)) if L2 > 0 else 0.0
                if float(np.linalg.norm(w - t * e)) > 10 * tol:
                    ok = False
                    break
            if ok:
                return True
        return False
    if face["name"] == "CYL":
        d = np.asarray(face["dirv"], float)
        d = d / (np.linalg.norm(d) or 1.0)
        for c, rad in arcs:
            w = c - face["p"]
            if np.linalg.norm(w - d * float(w @ d)) <= tol and abs(rad - float(face["rad"])) <= TOL * max(1.0, rad):
                return True
    return False


def _straight_between(infos, a, b, n):
    """Every face that touches both caps must be a straight sweep along n (a plane containing n, or a cylinder whose axis
    is n); otherwise two congruent caps are joined by something else - a helix, a loft, a twist - and are not a prism."""
    rep = lambda q: infos[q].get("dead", q)
    ra, rb = rep(a), rep(b)
    bridges = 0
    for k, inf in enumerate(infos):
        if "dead" in inf or k in (ra, rb):
            continue
        nb = {rep(q) for q in inf["adj"]}
        if ra in nb and rb in nb:
            bridges += 1
            if inf["name"] == "PLANE" and abs(float(inf["n"] @ n)) <= 1e-4:
                continue
            if inf["name"] == "CYL" and abs(abs(float(np.asarray(inf["dirv"]) @ n) / (np.linalg.norm(inf["dirv"]) or 1.0)) - 1.0) <= 1e-5:
                continue
            return False
    if bridges == 0:                                       # two faces nothing joins are no prism
        return False
    # every face across an edge of either cap must run straight along n: opposite walls of a hex socket are bounded by the
    # other walls at 60 degrees, and extruding one wall's outline to the other would be a box, not the socket
    for cap in (ra, rb):
        for q in {rep(x) for x in infos[cap]["adj"]} - {ra, rb}:
            inf = infos[q]
            if inf["name"] == "PLANE" and abs(float(inf["n"] @ n)) <= 1e-4:
                continue
            if inf["name"] == "CYL" and abs(abs(float(np.asarray(inf["dirv"]) @ n) / (np.linalg.norm(inf["dirv"]) or 1.0)) - 1.0) <= 1e-5:
                continue
            if inf["name"] == "PLANE" and abs(abs(float(inf["n"] @ n)) - 1.0) <= 1e-6:
                continue                                   # a parallel face beside the cap (a step), not a side
            return False
    return True


def detect_prisms(infos, order, loops=None):
    """Cap pairs of extrusions and the lateral faces they imply.

    A face is dropped from the IR only if it is the sweep of an edge of an accepted cap's loops; accepted caps are never
    dropped, and a pair is rejected when one of its caps was already dropped as another prism's lateral face. So every
    implied face can be rebuilt from the IR.
    """
    loops = loops or {}
    planar = [k for k in order if infos[k]["name"] == "PLANE"]
    cands = []                                   # (a, b, shift): first partner of every planar face, as before
    for a in planar:
        if len(infos[a]["pts"]) < 1:
            continue
        na = infos[a]["n"]
        for b in planar:
            if b == a:
                continue
            nb = infos[b]["n"]
            if not np.allclose(na, -nb, atol=1e-6):
                continue
            shift = -infos[b]["d"] - infos[a]["d"]
            if abs(shift) < 1e-6:
                continue
            vexp = {vkey(np.asarray(p) + na * shift) for p in infos[a]["pts"]}
            if vexp != {vkey(p) for p in infos[b]["pts"]}:
                continue
            if abs(infos[a]["area"] - infos[b]["area"]) > 1e-3 * max(1.0, infos[a]["area"]):
                continue
            cands.append((a, b, shift))
            break
    cands.sort(key=lambda c: (-float(f"{infos[c[0]]['area']:.4g}"), order.index(c[0])))   # main bodies claim their side faces first
    ext, twin, implied, used = {}, {}, set(), set()
    for a, b, shift in cands:
        if {a, b} & (used | implied):
            continue
        na = infos[a]["n"]
        if not _straight_between(infos, a, b, na):
            continue
        oa, ob = infos[a]["d"], -infos[b]["d"]
        lines, arcs = _cap_segments(infos[a], loops.get(a))
        lat = set()
        for k in order:
            if k in (a, b) or k in used:
                continue
            inf = infos[k]
            if inf["name"] == "PLANE":
                if abs(float(inf["n"] @ na)) > 1e-4:
                    continue
            elif inf["name"] == "CYL":
                if abs(abs(float(np.asarray(inf["dirv"]) @ na)) - 1.0) > 1e-5:
                    continue
            else:
                continue
            if not inf["pts"]:
                continue
            if all(abs(float(np.asarray(p) @ na) - oa) <= TOL or abs(float(np.asarray(p) @ na) - ob) <= TOL
                   for p in inf["pts"]) and _swept(inf, infos[a], lines, arcs, loops.get(k)):
                lat.add(k)
        ext[a] = (b, abs(shift), shift > 0)
        twin[b] = a
        implied |= lat
        used |= {a, b}
    return ext, twin, implied


def _ukey(n):
    """One sign for a direction and its opposite, so parallel planes share it."""
    n = np.asarray(n, float)
    return n if n[int(np.argmax(np.abs(n)))] > 0 else -n


def _straight_along(infos, k, u):
    """The face - every member of a merged group - is a straight sweep along u: a plane containing u, or a cylinder or a
    linear extrusion whose direction is u."""
    for m in infos[k].get("members", [k]):
        inf = infos[m]
        if inf["name"] == "PLANE":
            if abs(float(inf["n"] @ u)) > 1e-4:
                return False
        elif inf["name"] in ("CYL", "EXT"):
            d = np.asarray(inf["dirv"], float)
            if abs(abs(float(d @ u)) / (np.linalg.norm(d) or 1.0) - 1.0) > 1e-5:
                return False
        else:
            return False
    return True


def detect_loop_prisms(infos, order, loops, skip, diag):
    """Loops of two parallel planar faces joined by straight walls: a boss, a pocket, a through cut, a text or logo outline
    extruded between two levels. Like a prism's side faces, those walls follow from the loop and the offset, so they are
    implied; the second face's copy of the loop is written as a reference to the first.

    A loop pair is accepted only when every segment of the loop has a wall through both of its ends that is a straight sweep
    along the normal (plane, cylinder or linear extrusion, checked on every merged member) and every wall runs from one
    level to the other, touching nothing but the two loops.
    Returns (links, implied, pairs): links[k] = [(i, k2, i2, dz), ...] for the face holding the loop (dz: offset of face k2
    along k's outward normal); pairs: one dict per accepted pair (for relief grouping)."""
    rep = lambda q: infos[q].get("dead", q)
    pos = {k: j for j, k in enumerate(order)}
    adjrep = {k: {rep(q) for q in infos[k]["adj"]} - {k} for k in order}
    tp = max(2e-3, 2e-5 * diag)                   # same point: loop vertices come from rounded local coordinates
    buckets, info = {}, {}
    for k in order:
        inf = infos[k]
        if inf["name"] != "PLANE" or k in skip or not loops.get(k):
            continue
        fr, u = inf["frame"], _ukey(inf["n"])
        world = lambda uv: fr.o + fr.x * float(uv[0]) + fr.y * float(uv[1])
        flat = lambda p: p - u * float(p @ u)
        for i, lp in enumerate(loops[k]):
            if "c" in lp:
                c = flat(world(lp["c"][:2]))
                segs, verts, kind = [("C", None, None, c, float(lp["c"][2]))], np.array([c]), ("c", round(float(lp["c"][2]), 2))
            elif "e" in lp:
                if any(sg[0] == "S" and len(sg) != 6 for sg in lp["e"]):
                    continue                      # a spline without its exact form: the walls could not be rebuilt
                pts = [lp["s"]] + [seg_end(sg) for sg in lp["e"]]
                verts = np.array([flat(world(p)) for p in pts[:-1]])      # the last end is the start again
                segs = []
                for j, sg in enumerate(lp["e"]):
                    c, rad = None, None
                    if sg[0] == "A":
                        c, rad = flat(world(sg[1:3])), float(np.hypot(pts[j][0] - sg[1], pts[j][1] - sg[2]))
                    segs.append((sg[0], j, j + 1, c, rad))
                kind = ("e", len(lp["e"]))
            else:
                continue
            info[(k, i)] = {"segs": segs, "verts": verts, "level": float(fr.o @ u), "u": u, "circle": kind[0] == "c"}
            buckets.setdefault((tuple(np.round(u, 3)), kind), []).append((k, i))

    def same_outline(a, b):
        va, vb = info[a]["verts"], info[b]["verts"]
        if float(np.linalg.norm(va.mean(0) - vb.mean(0))) > tp or abs(float(info[a]["u"] @ info[b]["u"]) - 1.0) > 1e-6:
            return False
        d = np.linalg.norm(va[:, None] - vb[None], axis=2)
        return float(d.min(1).max()) <= tp and float(d.min(0).max()) <= tp

    cands = []
    for lst in buckets.values():
        for x in range(len(lst)):
            for y in range(x + 1, len(lst)):
                a, b = lst[x], lst[y]
                dl = abs(info[b]["level"] - info[a]["level"])
                if a[0] != b[0] and dl > TOL and same_outline(a, b):
                    cands.append((dl, pos[a[0]], pos[b[0]], a, b))
    cands.sort()
    used, implied, links, pairs = set(), set(), {}, []
    for _, _, _, a, b in cands:
        if a in used or b in used:
            continue
        ka, kb = a[0], b[0]
        u, la, lb = info[a]["u"], info[a]["level"], info[b]["level"]
        tol = TOL * max(1.0, abs(la), abs(lb))
        verts, segs = info[a]["verts"], info[a]["segs"]
        good = {}                                 # wall -> indices of the loop vertices it touches
        for q in sorted(adjrep[ka] & adjrep[kb]):
            if q in skip or q in implied or not infos[q]["pts"] or not _straight_along(infos, q, u):
                continue
            if infos[q]["name"] == "PLANE" and not _band(loops.get(q)):
                continue                          # a planar wall with an arc or a hole is not one segment's sweep
            top = set()
            for p in infos[q]["pts"]:
                p = np.asarray(p, float)
                s = float(p @ u)
                if abs(s - la) > tol and abs(s - lb) > tol:
                    break
                f = p - u * s
                if info[a]["circle"]:
                    if abs(float(np.linalg.norm(f - verts[0])) - segs[0][4]) > max(tp, 1e-3 * segs[0][4]):
                        break
                    continue
                dv = np.linalg.norm(verts - f, axis=1)
                j = int(np.argmin(dv))
                if float(dv[j]) > tp:
                    break
                top.add(j)
            else:
                good[q] = top
        cover = set()
        nv = len(verts)
        for kind, j0, j1, c, rad in segs:
            if kind != "C":
                j0, j1 = j0 % nv, j1 % nv
            # a straight wall that touches both levels and both ends of the segment is bounded by that very edge: its
            # sweep (a recognised arc of a short spline may disagree with the wall's own cylinder fit; both fit the edge)
            hit = next((q for q, top in good.items() if kind == "C" or (j0 in top and j1 in top)), None)
            if hit is None:
                cover = None
                break
            cover.add(hit)
        if not cover:
            continue
        holder, other = (a, b) if pos[ka] < pos[kb] else (b, a)
        n_h = np.asarray(infos[holder[0]]["n"], float)
        dz = (info[other]["level"] - info[holder]["level"]) * (1.0 if float(n_h @ u) > 0 else -1.0)
        links.setdefault(holder[0], []).append((holder[1], other[0], other[1], dz))
        implied |= cover
        used |= {a, b}
        pairs.append({"a": a, "b": b, "walls": sorted(cover), "u": u, "levels": (la, lb),
                      "same_side": float(np.asarray(infos[ka]["n"]) @ np.asarray(infos[kb]["n"])) > 0,
                      "curved": any(sg[0] in ("B", "S", "E") for sg in (loops[ka][a[1]].get("e") or [])),
                      "outer": {a: a[1] == 0, b: b[1] == 0}})
    return links, implied, pairs


RELIEF_MAX_DEPTH = 0.03   # relief features are shallow: height / depth at most this fraction of the bbox diagonal


def relief_groups(infos, order, pairs, diag):
    """Shallow raised or sunk outlines on a planar face - lettering, logos, labels - from the loop pairs.

    Pairs between two same-facing planes at the same two levels form one group. A pair whose upper face holds the loop as
    its outer loop is a boss (the upper face stands on the lower one), one whose lower face holds it as its outer loop is a
    pocket; the group is an emboss if bosses are the majority, else an engrave. `on` is the largest face of the base level
    (lower for emboss, upper for engrave), `faces` the group's other faces (tops or floors, and islands such as the inside of
    an O), `walls` the implied walls. A group counts as relief only if it is shallow, its feature faces are small next to
    `on`, and it has spline outlines - a stepped rim, a row of pockets or a rectangular boss is not relief."""
    groups = {}
    for pr in pairs:
        if not pr["same_side"]:
            continue
        lo, hi = sorted(pr["levels"])
        if hi - lo > RELIEF_MAX_DEPTH * diag:
            continue
        groups.setdefault((tuple(np.round(pr["u"], 4)), round(lo, 3), round(hi, 3)), []).append(pr)
    out = []
    for (u, lo, hi), prs in groups.items():
        if not any(pr["curved"] for pr in prs):
            continue
        uu = np.asarray(u, float)
        up = lambda x: float(infos[x[0]]["o"] @ uu) > (lo + hi) / 2
        boss = sum(1 for pr in prs for x in (pr["a"], pr["b"]) if up(x) and pr["outer"][x])
        pocket = sum(1 for pr in prs for x in (pr["a"], pr["b"]) if not up(x) and pr["outer"][x])
        faces = {x[0] for pr in prs for x in (pr["a"], pr["b"])}
        high = {x[0] for pr in prs for x in (pr["a"], pr["b"]) if up(x)}
        kind, base, feat = ("emboss", faces - high, high) if boss >= pocket else ("engrave", high, faces - high)
        on = max(base, key=lambda k: infos[k]["area"])
        if sum(infos[k]["area"] for k in feat) > 0.5 * infos[on]["area"]:
            continue
        out.append({"kind": kind, "on": on, "h": hi - lo, "faces": sorted(faces - {on}, key=order.index),
                    "walls": sorted({q for pr in prs for q in pr["walls"]}), "loops": len(prs)})
    return out


def _signed_offset(host, p):
    """Signed distance of p from the host face's carrier, positive on the outside of the material; None if not analytic."""
    p = np.asarray(p, float)
    name = host["name"]
    if name == "PLANE":
        return float(host["n"] @ p) - float(host["d"])
    if name not in ("CYL", "CONE", "SPHERE", "TORUS") or host.get("cc") is None:
        return None
    sgn = 1.0 if host["cc"] else -1.0
    c = np.asarray(host["p"], float)
    if name == "SPHERE":
        return sgn * (float(np.linalg.norm(p - c)) - float(host["rad"]))
    d = np.asarray(host["dirv"], float)
    d = d / (np.linalg.norm(d) or 1.0)
    w = p - c
    z = float(w @ d)
    rho = float(np.linalg.norm(w - z * d))
    if name == "CYL":
        return sgn * (rho - float(host["rad"]))
    if name == "CONE":
        a = float(host["ang"])
        return sgn * (rho - (float(host["rad"]) + z * math.tan(a))) * math.cos(a)
    return sgn * (float(np.hypot(rho - float(host["rad"]), z)) - float(host["rad2"]))


def relief_islands(infos, order, taken, diag, max_faces=200):
    """Shallow details that the loop pairs do not explain, e.g. on a curved face: a connected set of faces whose only
    neighbour outside the set is one face H, all within RELIEF_MAX_DEPTH of H's carrier, together smaller than H. Text
    engraved into or imprinted on a cylindrical or domed face shows up like this (an imprinted label is a single face whose
    only neighbour is H, at zero depth). A set of several faces counts only with a free-form or extruded-spline face among
    them (lettering walls) and only when H carries at least two such sets (letters come several; one island is a tab or a
    boss), so an ordinary shallow pocket or blind hole is not taken for relief; a single face with depth is a flat. One group per host face; the base IR has no loops for curved faces,
    so the outlines themselves are not in it (stepir_query face <id>)."""
    rep = lambda q: infos[q].get("dead", q)
    adj = {k: {rep(q) for q in infos[k]["adj"]} - {k} for k in order}
    out, seen = [], set(taken)
    for h in order:
        H = infos[h]
        if H["name"] not in ("PLANE", "CYL", "CONE", "SPHERE", "TORUS"):
            continue
        faces, offs, multi = [], [], 0
        for s in sorted(adj[h] - seen, key=order.index):
            if s in seen:
                continue
            comp, stack, ok = {s}, [s], True
            while stack and ok:
                x = stack.pop()
                for y in adj[x] - {h}:
                    if y in comp:
                        continue
                    if y in seen or len(comp) >= max_faces:
                        ok = False
                        break
                    comp.add(y)
                    stack.append(y)
            if not ok or sum(infos[k]["area"] for k in comp) > 0.25 * H["area"]:
                continue
            o = [_signed_offset(H, p) for k in comp for p in list(infos[k]["pts"]) + [infos[k]["g"]["centroid"]]]
            if not o or any(x is None for x in o):
                continue
            depth = max(abs(x) for x in o)
            if len(comp) == 1:
                if depth > 1e-4 * diag:          # one face with depth is a flat or a cut (it would need walls), not relief
                    continue
            elif depth > RELIEF_MAX_DEPTH * diag or not any(infos[k]["name"] in ("BSPL", "BEZ", "EXT") for k in comp):
                continue                          # lettering has spline walls; a blind hole or pocket does not
            else:
                multi += 1
            seen |= comp
            faces += sorted(comp, key=order.index)
            offs += o
        if multi == 1 and len(faces) > 1:         # one raised or sunk island is a feature (a tab, a boss); letters come several
            seen -= set(faces)
            faces = [f for f in faces if len(adj[f] - {h}) == 0 and max(abs(_signed_offset(H, p) or 0) for p in infos[f]["pts"]) <= 1e-4 * diag]
            seen |= set(faces)
            offs = [0.0] if faces else []
        if faces:
            depth = max(abs(x) for x in offs)
            mean = float(np.mean(offs))
            kind = "imprint" if depth <= 1e-4 * diag else "emboss" if mean > 0 else "engrave"
            out.append({"kind": kind, "on": h, "h": depth, "faces": faces, "walls": [], "loops": None})
    return out


def add_cut_flags(ir_text):
    """Upgrade an IR produced before the "cut" flag existed (idempotent; same result as re-running build_ir).

    A cap pair whose outward normals face each other bounds removed material: the twin lies at +h*n from the cap.
    """
    lines = ir_text.rstrip("\n").split("\n")
    recs = [json.loads(x) for x in lines[1:]]
    byid = {j["id"]: j for j in recs}
    out = [lines[0]]
    for j in recs:
        e = j.get("ext")
        if e and "cut" not in e and e["to"] in byid:
            b = byid[e["to"]]
            if sum((ob - oa) * na for ob, oa, na in zip(b["o"], j["o"], j["n"])) > 0:
                e["cut"] = 1
        out.append(json.dumps(j, separators=(",", ":")))
    return "\n".join(out) + "\n"


CANON_CYL = os.environ.get("STEPIR_CANON_CYL", "1") == "1"


def canon_axes(ir_text):
    """IR v5 (idempotent text transform, also applied to IRs stored before it existed): every cylinder states its axis
    segment directly - d points along its dominant axis in the positive sense, p is the START point of the segment and
    v = [0, length], so a cylinder/hole reads as make_cylinder_rsolid(bottom_face_center=p, axis=d, height=v[1])."""
    lines = ir_text.rstrip("\n").split("\n")
    out = [lines[0]]
    for line in lines[1:]:
        if '"t":"CYL"' in line:
            j = json.loads(line)
            if "p" in j and "d" in j and "v" in j:
                d = np.asarray(j["d"], float)
                v0, v1 = float(j["v"][0]), float(j["v"][1])
                if d[int(np.argmax(np.abs(d)))] < 0:
                    d, v0, v1 = -d, -v1, -v0
                j["p"] = [r(c) for c in np.asarray(j["p"], float) + d * v0]
                j["d"] = [r(c, 4) for c in d]
                j["v"] = [0, r(v1 - v0)]
            line = json.dumps(j, separators=(",", ":"))
        out.append(line)
    return "\n".join(out) + "\n"


def _ext_planar(inf, gen, out):
    """An extrusion generator that lies in one plane across the direction d is written as 2D poles `uv` in the frame
    (p, x, y = d x x) - the sketch to extrude - with its knots scaled to [0, 1]; otherwise unchanged (3D poles)."""
    d = np.asarray(inf["dirv"], float)
    d = d / (np.linalg.norm(d) or 1.0)
    P = np.asarray(gen["poles"], float)
    o = np.asarray(inf["p"], float)
    if float(np.abs((P - o) @ d).max()) > 1e-6 * DIAG[0]:
        return gen
    x, y = canon_frame(d)
    out["x"] = [r(c, 4) for c in x]
    k = np.asarray(gen["knots"], float)
    a, b = float(k[0]), float(k[-1])
    span = (b - a) or 1.0
    g = {kk: v for kk, v in gen.items() if kk != "poles"}
    g["uv"] = [[float((q - o) @ x), float((q - o) @ y)] for q in P]
    g["knots"] = [(float(t) - a) / span for t in k]
    g["t"] = [(float(t) - a) / span for t in gen["t"]]
    return g


def swept_record(inf):
    """IR fields of a surface of revolution (REV) or linear extrusion (EXT): the motion and the exact generating curve.

    REV: `p`,`d` axis; `span` degrees of rotation; `gen` = the generator in the meridian plane spanned by `d` and `e`:
         `zr` its B-spline poles as (z along d from p, r along e), `deg`, `knots`, `mult`, optional `w`, `t` the used range.
    EXT: `d` direction, `v` the extrusion range along d; `gen` the generator: 2D poles `uv` in the frame (p, x, d x x) when
         it lies in a plane across d (knots then scaled to [0, 1]), else 3D `poles`; and its spline data.
    A generator with more than MAX_GEN_POLES poles is left to the query tool (`gen` then only carries `n` and `deg`)."""
    gen = inf["gen"]
    n = len(gen.get("zr") or gen.get("poles"))
    out = {}
    if inf["name"] == "REV":
        out["e"] = [r(c, 4) for c in inf["e"]]
        out["span"] = r(math.degrees(inf["ur"][1] - inf["ur"][0]), 1)
    else:
        out["v"] = [r(inf["ext_v"][0]), r(inf["ext_v"][1])]
        gen = _ext_planar(inf, gen, out)
    if n > geomnorm.MAX_GEN_POLES:
        out["gen"] = {"n": n, "deg": gen["deg"], "more": "stepir_query face"}
        return out
    g = {"deg": gen["deg"]}
    if "zr" in gen:
        g["zr"] = [[r(a), r(b)] for a, b in gen["zr"]]
    elif "uv" in gen:
        g["uv"] = [[r(a), r(b)] for a, b in gen["uv"]]
    else:
        g["poles"] = [[r(c) for c in p] for p in gen["poles"]]
    g["knots"] = [r(x, 6) for x in gen["knots"]]
    g["mult"] = gen["mult"]
    if "w" in gen:
        g["w"] = [r(x, 6) for x in gen["w"]]
    if gen.get("periodic"):
        g["periodic"] = 1
    g["t"] = [r(x, 6) for x in gen["t"]]
    out["gen"] = g
    return out


def canon_cone(inf):
    """One convention for every cone, native or recognised: `p` is the point on the axis level with the face's narrow end,
    `dirv` points the way the radius grows, `rad` is the radius there, `ang` the half-angle (> 0), `vr` = (0, slant length).

    A STEP cone is P(u, v) = O + (R + v sin a) (cos u X + sin u Y) + v cos a Z with a signed half-angle a and any v range,
    so p + v d with the native numbers can put the narrow end on either side and even report a negative radius."""
    a = float(inf["ang"])
    z = np.asarray(inf["dirv"], float)
    z = z / (np.linalg.norm(z) or 1.0)
    v0, v1 = float(inf["vr"][0]), float(inf["vr"][1])
    rho = lambda v: float(inf["rad"]) + v * math.sin(a)
    vs, vb = (v0, v1) if abs(rho(v0)) <= abs(rho(v1)) else (v1, v0)
    axial = (vb - vs) * math.cos(a)
    d = z if axial >= 0 else -z
    inf["p"] = np.asarray(inf["p"], float) + z * (vs * math.cos(a))
    inf["dirv"], inf["rad"], inf["ang"] = d, abs(rho(vs)), abs(a)
    inf["vr"] = (0.0, abs(v1 - v0))


def build_ir(path):
    model = brep.load_step_rbrepmodel(path=str(path))
    summ = brep.inspect_step_rsummary(path=str(path))
    nf = len(model.faces)
    bbs = np.asarray(summ["bounding_box"]["min"], float), np.asarray(summ["bounding_box"]["max"], float)
    diag = float(np.linalg.norm(bbs[1] - bbs[0])) or 1.0
    DIAG[0] = diag
    centre = (bbs[0] + bbs[1]) / 2.0
    infos = []
    for i in range(nf):
        d = model.describe_entity(f"face:{i}")
        g = d["geometry"]
        p = g["parameters"]
        name = SURF.get(g["type"], "OTHER")
        nrm = np.asarray(g["normal_at_center"], float)
        inf = {"i": i, "name": name, "area": g["area"], "adj": [int(q.split(":")[1]) for q in d["adjacency"]["neighboring_faces"]], "g": g}
        if name == "PLANE":
            o = np.asarray(p["origin"], float)
            n = nrm / (np.linalg.norm(nrm) or 1.0)
            dd = float(n @ o)
            inf.update(n=n, d=dd, o=n * dd)
        elif name in ("CYL", "CONE", "TORUS"):
            ax = p["axis"]
            inf.update(p=np.asarray(ax["point"], float), dirv=np.asarray(ax["direction"], float), rad=p.get("radius", p.get("major_radius", p.get("reference_radius"))))
            c = np.asarray(g["centroid"], float)
            dv = inf["dirv"] / (np.linalg.norm(inf["dirv"]) or 1.0)
            rv = c - inf["p"] - float((c - inf["p"]) @ dv) * dv
            rr = float(np.linalg.norm(rv))
            if rr > 0.05 * float(inf["rad"] or 1.0):
                inf["ref"] = rv / rr
            inf["cc"] = 0 if reversed_face(model, i) else 1
            if name == "CONE":
                inf["ang"] = math.radians(p["semi_angle_degrees"]) if "semi_angle_degrees" in p else None
            if name == "TORUS":
                inf["rad2"] = p.get("minor_radius")
        elif name == "SPHERE":
            inf.update(p=np.asarray(p["center"], float), rad=p["radius"], dirv=np.asarray(p.get("axis_direction", [0, 0, 1]), float))
            inf["cc"] = 0 if reversed_face(model, i) else 1
        inf["ur"], inf["vr"] = p.get("u_range"), p.get("v_range")
        if name == "CONE" and inf.get("ang") is not None and inf.get("vr"):
            canon_cone(inf)
        if name in ("BSPL", "BEZ", "OTHER"):
            rec = geomnorm.recognize_face(model, i, diag, centre)
            if rec is None and g["type"] in ("REVOLUTION", "EXTRUSION"):
                rec = geomnorm.swept_carrier(model, i, g, diag)
            if g["type"] == "BSPLINE" and (rec is None or rec["name"] not in ("PLANE", "CYL")):
                # an exact straight extrusion is not a cone, sphere or torus that happens to fit within tolerance (a wall
                # extruded from a nearly circular spline fits a cone of 0.02 degrees)
                ruled = geomnorm.ruled_extrusion(model, i, g, diag)
                rec = ruled or rec
            elif g["type"] == "BSPLINE" and rec["name"] == "CYL":
                ruled = geomnorm.ruled_extrusion(model, i, g, diag)
                if ruled is not None and abs(abs(float(np.dot(ruled["dirv"], rec["dirv"]))) - 1.0) > 1e-6:
                    rec = ruled
            if rec is not None:
                inf.update(rec)
                name = inf["name"]
        if name in ("BSPL", "BEZ", "OTHER"):
            inf["bb"] = [[r(c) for c in d["bounding_box"]["min"]], [r(c) for c in d["bounding_box"]["max"]]]
            inf["deg"] = [p.get("u_degree"), p.get("v_degree")]
            inf["poles"] = [p.get("u_pole_count"), p.get("v_pole_count")]
        infos.append(inf)

    def sort_key(inf):
        rk = RANK.get(inf["name"], 9)
        if inf["name"] == "PLANE":
            return (rk, tuple(round(float(c), 2) for c in inf["n"]), round(inf["d"], 3), -round(inf["area"], 2))
        if "dirv" in inf:
            return (rk, round(float(inf.get("rad") or 0), 3), tuple(round(float(c), 2) for c in inf["dirv"]), -round(inf["area"], 2))
        return (rk, 0, (), -round(inf["area"], 2))

    geomnorm.merge_groups(model, infos, diag)
    live = [k for k in range(nf) if "dead" not in infos[k]]
    order = sorted(live, key=lambda k: sort_key(infos[k]))
    newid = {k: j for j, k in enumerate(order)}
    for k in range(nf):
        if "dead" in infos[k]:
            newid[k] = newid[infos[k]["dead"]]
    # loops (needs frames for planar faces) and boundary points
    loops_cache = {}
    for k in order:
        inf = infos[k]
        fid = f"face:{inf['i']}"
        raw = inf.get("loops_raw")
        if inf["name"] == "PLANE":
            fr = Frame(inf["o"], inf["n"])
            loops, pts = face_loops_raw(model, raw, fr) if raw else face_loops(model, fid, fr)
            inf["frame"] = fr
            pts = loop_points(loops, fr)
        elif inf["name"] in ("BSPL", "BEZ", "OTHER"):
            loops, pts = face_loops_raw(model, raw, None) if raw else face_loops(model, fid, None)
        else:                                    # analytic and REV/EXT faces: the carrier and its ranges say where they are
            loops = None
            if raw is None:
                raw = [brep.inspect_face_boundaries_rdescriptor(model_or_path=model, face_id=fid, compact=True)]
                raw = [raw[0]["outer"]] + list(raw[0].get("inner", []))
            pts = []
            for lp in raw:
                for rec in lp["edges"]:
                    pts.append(rec["start"])
                    pts.append(rec["end"])
        loops_cache[k] = loops
        inf["pts"] = pts
    ext, twin, implied = detect_prisms(infos, order, loops_cache)
    links, implied2, pairs = detect_loop_prisms(infos, order, loops_cache, set(ext) | set(twin) | implied, diag)
    implied |= implied2
    for k, lst in links.items():                 # the second face's copy of a linked loop becomes a reference
        for i, k2, i2, dz in lst:
            loops_cache[k2] = list(loops_cache[k2])
            loops_cache[k2][i2] = {"same": [newid[k], i]}
    relief = relief_groups(infos, order, pairs, diag)
    relief += relief_islands(infos, order, {f for g in relief for f in g["faces"] + g["walls"] + [g["on"]]}, diag)
    types = Counter(infos[k]["name"] for k in live)
    bb = summ["bounding_box"]
    header = {"unit": "mm", "bbox": [[r(c) for c in bb["min"]], [r(c) for c in bb["max"]]], "vol": r(summ["volume"], 2),
              "area": r(summ["surface_area"], 2), "solids": len(model.bodies), "counts": {"face": len(live), "edge": summ["edge_count"]}, "types": dict(types),
              "implied": len(implied)}
    if relief:                                   # faces that only carry shallow lettering / logos (see relief lines)
        rf = [f for g in relief for f in g["faces"] + g["walls"]]
        header["relief"] = {"faces": len(rf), "types": dict(Counter(infos[f]["name"] for f in rf))}
    lines = [json.dumps(header, separators=(",", ":"))]
    for j, k in enumerate(order):
        if k in implied:
            continue
        inf = infos[k]
        rec = {"id": j, "t": inf["name"], "A": r(inf["area"], 2)}
        if inf["name"] == "PLANE":
            fr = inf["frame"]
            rec.update(o=[r(c) for c in inf["o"]], n=[r(c, 4) for c in inf["n"]], x=[r(c, 4) for c in fr.x])
            if k in twin:
                rec["twin"] = newid[twin[k]]
            else:
                if k in ext:
                    rec["ext"] = {"to": newid[ext[k][0]], "h": r(ext[k][1])}
                    if ext[k][2]:
                        rec["ext"]["cut"] = 1
                loops = settle_splines(loops_cache[k], {i for i, *_ in links.get(k, [])})
                rects = [rect_of(l) for l in loops]
                if len(loops) == 1 and rects[0] is not None:
                    rec["rect"] = rects[0]
                else:
                    rec["loops"] = loops
                if k in links:
                    rec["prism"] = [[i, newid[k2], r(dz)] for i, k2, i2, dz in sorted(links[k])]
        else:
            if "p" in inf:
                rec["p"] = [r(c) for c in inf["p"]]
            if "dirv" in inf:
                rec["d"] = [r(c, 4) for c in inf["dirv"]]
            if inf.get("rad") is not None:
                rec["r"] = r(inf["rad"])
            if inf.get("rad2") is not None:
                rec["r2"] = r(inf["rad2"])
            if inf.get("ang") is not None:
                rec["ang"] = r(math.degrees(inf["ang"]), 2)
            if ENDCAPS and inf["name"] in ("CYL", "CONE") and inf.get("vr"):
                dv = np.asarray(inf["dirv"], float)
                dv = dv / (np.linalg.norm(dv) or 1.0)
                v0, v1 = inf["vr"]
                if inf["name"] == "CYL":
                    z0, z1, r0, r1 = v0, v1, inf["rad"], inf["rad"]
                else:
                    a_ = inf["ang"]
                    z0, z1 = v0 * math.cos(a_), v1 * math.cos(a_)
                    r0, r1 = inf["rad"] + v0 * math.sin(a_), inf["rad"] + v1 * math.sin(a_)
                rec["c0"] = [r(c) for c in inf["p"] + dv * z0]
                rec["c1"] = [r(c) for c in inf["p"] + dv * z1]
                if inf["name"] == "CONE":
                    rec["r0"], rec["r1"] = r(r0), r(r1)
                    rec.pop("r", None)
                rec.pop("p", None)
            if inf["name"] in ("CYL", "CONE", "SPHERE", "TORUS"):
                lin = inf["name"] in ("CYL", "CONE")
                ur, vr = inf["ur"], inf["vr"]
                if ur:
                    span = math.degrees(ur[1] - ur[0])
                    if span > 360.0:                          # a face that winds round its axis more than once (a helical strip)
                        rec["wraps"] = r(span / 360.0, 2)
                        span = 360.0
                    rec["span"] = r(span, 1)
                    if "ref" in inf and span < 359.0:
                        rec["ref"] = [r(c, 4) for c in inf["ref"]]
                if vr and not ("c0" in rec):
                    rec["v"] = [r(vr[0]), r(vr[1])] if lin else [r(math.degrees(vr[0]), 1), r(math.degrees(vr[1]), 1)]
                rec["cc"] = inf["cc"]
            elif inf["name"] in ("REV", "EXT"):
                rec.update(swept_record(inf))
            else:
                rec["bb"] = inf["bb"]
                rec["deg"] = inf["deg"]
                rec["poles"] = inf["poles"]
                rec["loops"] = loops_cache[k]
            adj = sorted({newid[q] for q in inf["adj"]} - {newid[k]})
            if 0 < len(adj) <= 6:
                rec["adj"] = adj
        lines.append(json.dumps(rec, separators=(",", ":")))
    if CANON_CYL:
        lines = canon_axes("\n".join(lines)).rstrip("\n").split("\n")
    build_ir.last_infos, build_ir.last_live, build_ir.last_newid = infos, live, newid
    build_ir.last_relief = [{"kind": g["kind"], "on": newid[g["on"]], "h": r(g["h"]), "faces": [newid[f] for f in g["faces"]],
                             "walls": len(g["walls"]), **({"loops": g["loops"]} if g["loops"] else {})} for g in relief]
    build_ir.last_face_map = dict(newid)      # original face index -> IR id, for tools that need to join with the B-rep
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step")
    ap.add_argument("--out")
    a = ap.parse_args()
    text = "\n".join(build_ir(a.step)) + "\n"
    if a.out:
        open(a.out, "w").write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
