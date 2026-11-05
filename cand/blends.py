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


def detect(model, infos, live, newid, by_ir):
    cache = {}
    out, blend_reps = [], set()
    area_of = lambda r: infos[r]["area"]
    nbrs = {k: sorted({_rep(infos, q) for q in infos[k]["adj"]} - {k}) for k in live}

    # ---- fillets: analytic round faces tangent to two different supports ----------------------------------------------
    for k in live:
        f = infos[k]
        if f["name"] not in ("CYL", "TORUS"):
            continue
        arc = (f["ur"][1] - f["ur"][0]) if f["name"] == "CYL" and f.get("ur") else (f["vr"][1] - f["vr"][0]) if f.get("vr") else 0.0
        if arc >= MAX_ARC:
            continue
        tang = {}
        for g in nbrs[k]:
            if infos[g]["name"] == f["name"]:
                continue
            L = tangent_length(model, _members(f), _members(infos[g]), cache)
            if L > 0:
                tang[g] = L
        if len(tang) < 2:
            continue
        if f["name"] == "CYL" and sum(infos[g]["name"] == "PLANE" for g in tang) < 2:
            continue
        pick = sorted(tang, key=lambda g: -tang[g])[:2]
        rad = f["rad"] if f["name"] == "CYL" else f["rad2"]
        out.append({"rep": k, "kind": "fillet", "carrier": "CYLINDER" if f["name"] == "CYL" else "TORUS", "radius": round(float(rad), 4),
                    "supports": pick, "how": "tangent_edges"})
        blend_reps.add(k)

    # ---- chamfers: a narrow plane bisecting two planes, a cone between a plane and a coaxial cylinder -------------------
    ctol = math.cos(math.radians(ANG_TOL))
    for k in live:
        f = infos[k]
        if k in blend_reps:
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
                # equal-distance chamfers bisect their supports; unequal ones (distance + angle) do not, but are chamfers too
                ang = math.degrees(math.acos(max(-1.0, min(1.0, float(infos[best[0]]["n"] @ infos[best[1]]["n"])))))
                out.append({"rep": k, "kind": "chamfer", "carrier": "planar_bevel", "angle_deg": round(ang, 2),
                            "supports": sorted(best), "how": f"normal_bisector(err={err:.3f})" if err < 0.15 else f"neighbour_planes(err={err:.3f})",
                            "selectable": err < 0.15})
                blend_reps.add(k)
        elif f["name"] == "CONE":
            d = _unit(f["dirv"])
            planes = [g for g in nbrs[k] if infos[g]["name"] == "PLANE" and abs(float(infos[g]["n"] @ d)) >= ctol]
            cyls = [g for g in nbrs[k] if infos[g]["name"] == "CYL" and abs(float(_unit(infos[g]["dirv"]) @ d)) >= ctol
                    and float(np.linalg.norm((np.asarray(infos[g]["p"], float) - np.asarray(f["p"], float))
                                             - float((np.asarray(infos[g]["p"], float) - np.asarray(f["p"], float)) @ d) * d))
                    <= 1e-4 * max(1.0, abs(float(f["rad"])))]
            # an edge break is small against the hole or boss it breaks; a cone as wide as the bore is the countersink itself
            extent = abs(float(f["vr"][1] - f["vr"][0])) * math.sin(f["ang"]) if f.get("vr") else 0.0
            cyls = [g for g in cyls if extent <= CONE_EDGE_BREAK * abs(float(infos[g]["rad"]))]
            if planes and cyls:
                out.append({"rep": k, "kind": "chamfer", "carrier": "conical_bevel", "supports": [cyls[0], planes[0]], "how": "coaxial_cylinder_and_plane",
                            "angle_deg": round(math.degrees(f["ang"]), 2)})
                blend_reps.add(k)

    res = []
    for b in out:
        k = b["rep"]
        rec = {"faces": [newid[k]], "kind": b["kind"], "carrier": b["carrier"], "between": [_ref(infos, g, newid, by_ir) for g in b["supports"]],
               "how": b["how"], "selectable": b.get("selectable", True)}
        if "radius" in b:
            rec["radius"] = b["radius"]
        if "angle_deg" in b:
            rec["angle_deg"] = b["angle_deg"]
        rec["between_kinds"] = [infos[g]["name"] for g in b["supports"]]
        res.append(rec)
    return res
