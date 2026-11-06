#!/usr/bin/env python3
"""Fillet and chamfer regions, found on the IR's own faces (after surface recognition and merging), not on the SDK's
hints - so a blend stored as B-spline, or cut in pieces, is found exactly like a clean one.

  detect(model, infos, live, newid, by_ir) -> [{"faces": [IR ids], "kind", "carrier", "radius", "angle_deg", "between": [id | carrier],
                                                 "how", "selectable"}]

`between` is what `shared_boundary` needs: the two faces whose common edge the blend rounded. An entry is the IR id of a face
that has a record, or - for a face the IR leaves implied (a prism side wall) - the face's own carrier written in IR-record form,
so it can be used without reconstructing anything.
"""
from __future__ import annotations

import math

import numpy as np

import geomnorm

ANG_TOL = 1.0            # degrees: "parallel", "perpendicular", "coaxial"
MAX_ARC = math.radians(170.0)
CHAMFER_LARGE = 0.08    # bevel setback / bbox diagonal above which it is as likely a design face as an edge break (real labelled parts: chamfers median 0.013, false bevels median 0.039)
CONE_EDGE_BREAK = 0.3     # conical chamfer: radial extent / radius of the coaxial cylinder it breaks. Real chamfer-labelled parts: median 0.06, 90th pct 0.27; cones on parts without chamfers: median 0.63


def _unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def _rep(infos, q):
    return infos[q].get("dead", q)


def _members(inf):
    return inf.get("members") or [inf["i"]]


def _normal_at(face, pt):
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepLProp import BRepLProp_SLProps
    from OCP.gp import gp_Pnt
    from OCP.ShapeAnalysis import ShapeAnalysis_Surface
    uv = ShapeAnalysis_Surface(BRep_Tool.Surface_s(face)).ValueOfUV(gp_Pnt(*pt), 1e-7)
    pr = BRepLProp_SLProps(BRepAdaptor_Surface(face), uv.X(), uv.Y(), 1, 1e-9)
    if not pr.IsNormalDefined():
        return None
    n = pr.Normal()
    return (-1.0 if face.Orientation().name.endswith("REVERSED") else 1.0) * np.array([n.X(), n.Y(), n.Z()])


def tangent_length(model, ma, mb, cache):
    """Total length of the edges two face groups share along which their surfaces meet tangentially (G1)."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GCPnts import GCPnts_AbscissaPoint
    from OCP.TopoDS import TopoDS
    total = 0.0
    for a in ma:
        for b in mb:
            key = (min(a, b), max(a, b))
            if key not in cache:
                ea = set(model.describe_entity(f"face:{a}")["adjacency"]["edges"])
                eb = set(model.describe_entity(f"face:{b}")["adjacency"]["edges"])
                length = 0.0
                for eid in sorted(ea & eb):
                    e = model.resolve_entity(eid)
                    c = BRepAdaptor_Curve(TopoDS.Edge_s(e[-1] if isinstance(e, tuple) else e))
                    fa, fb = geomnorm._face_of(model, a), geomnorm._face_of(model, b)
                    ok = True
                    for t in np.linspace(c.FirstParameter(), c.LastParameter(), 5)[1:-1]:
                        q = c.Value(float(t))
                        na, nb = _normal_at(fa, (q.X(), q.Y(), q.Z())), _normal_at(fb, (q.X(), q.Y(), q.Z()))
                        if na is None or nb is None or float(na @ nb) < 1 - 1e-5:
                            ok = False
                            break
                    if ok:
                        length += float(GCPnts_AbscissaPoint.Length_s(c))
                cache[key] = length
            total += cache[key]
    return total


def carrier_of(inf):
    """A face's carrier written the way an IR record writes it (used inline for supports the IR leaves implied)."""
    t = inf["name"]
    if t == "PLANE":
        return {"t": "PLANE", "o": [round(float(x), 4) for x in inf["o"]], "n": [round(float(x), 4) for x in inf["n"]]}
    rec = {"t": t, "p": [round(float(x), 4) for x in inf["p"]]}
    if "dirv" in inf:
        rec["d"] = [round(float(x), 4) for x in inf["dirv"]]
    if inf.get("rad") is not None:
        rec["r"] = round(float(inf["rad"]), 4)
    if inf.get("rad2") is not None:
        rec["r2"] = round(float(inf["rad2"]), 4)
    if inf.get("ang") is not None:
        rec["ang"] = round(math.degrees(inf["ang"]), 2)
    return rec


def _ref(infos, q, newid, by_ir):
    r = _rep(infos, q)
    ident = newid[r]
    return ident if ident in by_ir else carrier_of(infos[r])


def _edge_points_between(model, ma, mb, n=7):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS
    pts = []
    for a in ma:
        ea = set(model.describe_entity(f"face:{a}")["adjacency"]["edges"])
        for b in mb:
            for eid in sorted(ea & set(model.describe_entity(f"face:{b}")["adjacency"]["edges"])):
                e = model.resolve_entity(eid)
                c = BRepAdaptor_Curve(TopoDS.Edge_s(e[-1] if isinstance(e, tuple) else e))
                pts += [[c.Value(t).X(), c.Value(t).Y(), c.Value(t).Z()] for t in np.linspace(c.FirstParameter(), c.LastParameter(), n)]
    return np.asarray(pts)


def _rolling_radius(model, members, diag):
    """Radius of a constant-radius rolling-ball blend stored as a spline: one principal curvature is 1/r everywhere."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepLProp import BRepLProp_SLProps
    from OCP.BRepTools import BRepTools
    ks = []
    for m in members:
        face = geomnorm._face_of(model, m)
        u0, u1, v0, v1 = BRepTools.UVBounds_s(face)
        ad = BRepAdaptor_Surface(face)
        for u in np.linspace(u0, u1, 7)[1:-1]:
            for v in np.linspace(v0, v1, 7)[1:-1]:
                pr = BRepLProp_SLProps(ad, float(u), float(v), 2, 1e-9)
                if pr.IsCurvatureDefined():
                    ks.append(max(abs(pr.MaxCurvature()), abs(pr.MinCurvature())))
    if len(ks) < 8:
        return None
    ks = np.asarray(ks)
    if ks.mean() <= 0 or ks.std() > 0.02 * ks.mean() or 1.0 / ks.mean() > 0.05 * diag:
        return None
    return float(1.0 / ks.mean())


def _chamfer_distances(model, infos, k, supports):
    """Setback of a planar bevel on each support: distance from the edge the two supports would have met along (the line
    where their planes intersect) to the bevel's edge on that support."""
    A, B = infos[supports[0]], infos[supports[1]]
    if A["name"] != "PLANE" or B["name"] != "PLANE":
        return None
    d = np.cross(A["n"], B["n"])
    if np.linalg.norm(d) < 1e-9:
        return None
    d = d / np.linalg.norm(d)
    M = np.array([A["n"], B["n"], d])
    p0 = np.linalg.solve(M, np.array([A["d"], B["d"], 0.0]))
    out = []
    for g in supports:
        P = _edge_points_between(model, _members(infos[k]), _members(infos[g]))
        if not len(P):
            return None
        w = P - p0
        out.append(float(np.median(np.linalg.norm(w - np.outer(w @ d, d), axis=1))))
    return out


def detect(model, infos, live, newid, by_ir, diag=None):
    cache = {}
    found = {}                                             # rep -> blend record
    nbrs = {k: sorted({_rep(infos, q) for q in infos[k]["adj"]} - {k}) for k in live}
    if diag is None:
        diag = 1.0

    def tangents(k):
        f = infos[k]
        tang = {}
        for g in nbrs[k]:
            if infos[g]["name"] == f["name"] and f["name"] != "BSPL":
                continue
            L = tangent_length(model, _members(f), _members(infos[g]), cache)
            if L > 0:
                tang[g] = L
        return tang

    # ---- fillets: round faces (analytic, or a spline of constant radius) tangent to two different supports --------------
    for k in live:
        f = infos[k]
        if f["name"] in ("CYL", "TORUS"):
            arc = (f["ur"][1] - f["ur"][0]) if f["name"] == "CYL" and f.get("ur") else (f["vr"][1] - f["vr"][0]) if f.get("vr") else 0.0
            if arc >= MAX_ARC:
                continue
            tang = tangents(k)
            if len(tang) < 2 or (f["name"] == "CYL" and sum(infos[g]["name"] == "PLANE" for g in tang) < 2):
                continue
            rad = f["rad"] if f["name"] == "CYL" else f["rad2"]
            found[k] = {"kind": "fillet", "carrier": f["name"], "radius": float(rad), "tang": tang}
        elif f["name"] in ("BSPL", "BEZ"):
            tang = tangents(k)
            # a constant-radius spline strip between two free-form faces is as likely a rounded corner of a swept or lofted
            # profile; a blend proper rounds an edge of at least one analytic face
            if len(tang) < 2 or not any(infos[g]["name"] in ("PLANE", "CYL", "CONE", "SPHERE", "TORUS") for g in tang):
                continue
            rad = _rolling_radius(model, _members(f), diag)
            if rad is not None:
                found[k] = {"kind": "fillet", "carrier": "SPLINE", "radius": rad, "tang": tang}

    # ---- chamfers: a narrow plane between two planes, a small cone between a plane and a coaxial cylinder -------------
    ctol = math.cos(math.radians(ANG_TOL))
    for k in live:
        f = infos[k]
        if k in found:
            continue
        if f["name"] == "PLANE":
            cands = [g for g in nbrs[k] if infos[g]["name"] == "PLANE" and 0.10 < abs(float(f["n"] @ infos[g]["n"])) < ctol]
            best, err = None, 1e9
            for x in range(len(cands)):
                for y in range(x + 1, len(cands)):
                    a, b = infos[cands[x]], infos[cands[y]]
                    if abs(float(a["n"] @ b["n"])) >= ctol or f["area"] > 0.75 * min(a["area"], b["area"]):
                        continue
                    e = float(np.linalg.norm(_unit(a["n"] + b["n"]) - f["n"]))
                    if e < err:
                        best, err = (cands[x], cands[y]), e
            if best:
                found[k] = {"kind": "chamfer", "carrier": "planar_bevel", "supports": sorted(best), "uncertain": err >= 0.15}
        elif f["name"] == "CONE":
            d = _unit(f["dirv"])
            planes = [g for g in nbrs[k] if infos[g]["name"] == "PLANE" and abs(float(infos[g]["n"] @ d)) >= ctol]
            cyls = [g for g in nbrs[k] if infos[g]["name"] == "CYL" and abs(float(_unit(infos[g]["dirv"]) @ d)) >= ctol
                    and float(np.linalg.norm((np.asarray(infos[g]["p"], float) - np.asarray(f["p"], float))
                                             - float((np.asarray(infos[g]["p"], float) - np.asarray(f["p"], float)) @ d) * d))
                    <= 1e-4 * max(1.0, abs(float(f["rad"])))]
            extent = abs(float(f["vr"][1] - f["vr"][0])) * math.sin(f["ang"]) if f.get("vr") else 0.0
            cyls = [g for g in cyls if extent <= CONE_EDGE_BREAK * abs(float(infos[g]["rad"]))]
            if planes and cyls:
                L = abs(float(f["vr"][1] - f["vr"][0]))
                found[k] = {"kind": "chamfer", "carrier": "conical_bevel", "supports": [cyls[0], planes[0]],
                            "dist": [round(L * math.cos(f["ang"]), 4), round(L * math.sin(f["ang"]), 4)]}

    blends = set(found)
    # ---- supports: the two faces the blend rounds - original faces first, other blend patches only when needed -------
    for k, b in found.items():
        if b["kind"] != "fillet":
            continue
        tang = b.pop("tang")
        orig = sorted((g for g in tang if g not in blends), key=lambda g: -tang[g])
        rest = sorted((g for g in tang if g in blends), key=lambda g: -tang[g])
        b["supports"] = (orig + rest)[:2]
        if len(orig) < 2:
            b["on_blend"] = True                           # rounds an edge of an earlier blend: build that one first
    for k, b in found.items():
        if b["kind"] == "chamfer" and b["carrier"] == "planar_bevel":
            dd = _chamfer_distances(model, infos, k, b["supports"])
            if dd:
                b["dist"] = [round(x, 4) for x in dd]

    # ---- corner patches: a sphere (or torus) where blends of its radius meet -----------------------------------------
    corners = {}
    for k in live:
        f = infos[k]
        if k in found or f["name"] not in ("SPHERE", "TORUS"):
            continue
        rk = f["rad"] if f["name"] == "SPHERE" else f.get("rad2")
        touching = [g for g in nbrs[k] if g in found and found[g]["kind"] == "fillet"
                    and abs(found[g]["radius"] - float(rk or 0)) <= 1e-3 * max(1.0, found[g]["radius"])]
        if len(touching) >= 2:
            corners[k] = touching

    # ---- one operation per kind and size ---------------------------------------------------------------------------
    def size_key(b):
        if b["kind"] == "fillet":
            return ("fillet", round(b["radius"], 3))
        d = b.get("dist")
        return ("chamfer", tuple(sorted(round(x, 3) for x in d)) if d else ("?", b["carrier"]))
    groups = {}
    for k in sorted(found, key=lambda k: newid[k]):
        groups.setdefault(size_key(found[k]), []).append(k)
    res = []
    for key, ks in groups.items():
        b0 = found[ks[0]]
        rec = {"kind": b0["kind"], "faces": [newid[k] for k in ks],
               "between": [[_ref(infos, g, newid, by_ir) for g in found[k]["supports"]] for k in ks],
               "carriers": sorted({found[k]["carrier"] for k in ks})}
        if b0["kind"] == "fillet":
            rec["radius"] = round(b0["radius"], 4)
        elif b0.get("dist"):
            rec["dist"] = list(key[1]) if len(set(key[1])) > 1 else key[1][0]
        big = b0["kind"] == "chamfer" and b0.get("dist") and max(b0["dist"]) > CHAMFER_LARGE * diag
        unc = [newid[k] for k in ks if found[k].get("uncertain") or len(found[k]["supports"]) < 2 or big]
        if unc:
            rec["uncertain"] = unc
        after = [newid[k] for k in ks if found[k].get("on_blend")]
        if after:
            rec["on_blend"] = after
        cs = sorted(newid[c] for c, t in corners.items() if set(t) & set(ks))
        if cs:
            rec["corners"] = cs
        res.append(rec)
    return res
