#!/usr/bin/env python3
"""On-demand observation of a part, by IR face id: what is too big or too speculative to print in the base IR.

  stepir_query.py part.step face 12        one face: its record, members, neighbours, and for a spline the full control net
  stepir_query.py part.step evidence 12    which rigid motions sweep the face (cadfit): nullity, residual, candidate operations
  stepir_query.py part.step axis           coaxial face clusters with their exact (z, r) meridian profiles
  stepir_query.py part.step neighbours 12  adjacent faces with the angle between the surfaces along the shared edge

The base IR carries what the model must read every time (carriers, loops, prism structure, blends with their supports, the
free-form marker, evidenced operations). This carries what it asks for when it needs it: a spline's control net costs
thousands of tokens and is read for one face at a time; a meridian is recomputable from the carriers.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stepir  # noqa: E402
import stepir_ops  # noqa: E402
import geomnorm  # noqa: E402


def _load(path):
    lines = stepir.build_ir(str(path))
    recs = {j["id"]: j for j in (json.loads(x) for x in lines[1:] if x.strip())}
    return lines, recs, stepir.build_ir.last_infos, stepir.build_ir.last_newid


def _net(B):
    nu, nv = B.NbUPoles(), B.NbVPoles()
    rational = bool(B.IsURational() or B.IsVRational())
    return {"degree": [B.UDegree(), B.VDegree()], "rational": rational,
            "control_points": [[[round(B.Pole(i, j).X(), 4), round(B.Pole(i, j).Y(), 4), round(B.Pole(i, j).Z(), 4)]
                                for j in range(1, nv + 1)] for i in range(1, nu + 1)],
            "weights": [[round(B.Weight(i, j), 6) for j in range(1, nv + 1)] for i in range(1, nu + 1)] if rational else None,
            "u_knots": [[round(B.UKnot(k), 6), B.UMultiplicity(k)] for k in range(1, B.NbUKnots() + 1)],
            "v_knots": [[round(B.VKnot(k), 6), B.VMultiplicity(k)] for k in range(1, B.NbVKnots() + 1)]}


def _curve(c):
    P, cdef = geomnorm._curve_def(c)
    out = {"degree": cdef["deg"], "poles": [[round(float(x), 4) for x in p] for p in P],
           "knots": [[round(k, 6), m] for k, m in zip(cdef["knots"], cdef["mult"])]}
    if "w" in cdef:
        out["weights"] = [round(x, 6) for x in cdef["w"]]
    if cdef.get("periodic"):
        out["periodic"] = True
    return out


def carrier(S):
    """Exact description of a non-analytic carrier: a B-spline's control net; a surface of revolution / linear extrusion
    as its axis or direction plus the exact generating curve; an offset surface as the offset plus its basis; anything
    else converted to a B-spline net (marked converted)."""
    from OCP.Geom import (Geom_BSplineSurface, Geom_OffsetSurface, Geom_RectangularTrimmedSurface,
                          Geom_SurfaceOfLinearExtrusion, Geom_SurfaceOfRevolution)
    from OCP.GeomConvert import GeomConvert
    while isinstance(S, Geom_RectangularTrimmedSurface):
        S = S.BasisSurface()
    if isinstance(S, Geom_BSplineSurface):
        return {"type": "bspline", **_net(S)}
    if isinstance(S, Geom_SurfaceOfRevolution):
        ax = S.Axis()
        return {"type": "revolution", "axis": [round(ax.Direction().X(), 6), round(ax.Direction().Y(), 6), round(ax.Direction().Z(), 6)],
                "point": [round(ax.Location().X(), 4), round(ax.Location().Y(), 4), round(ax.Location().Z(), 4)],
                "generator": _curve(S.BasisCurve())}
    if isinstance(S, Geom_SurfaceOfLinearExtrusion):
        d = S.Direction()
        return {"type": "extrusion", "direction": [round(d.X(), 6), round(d.Y(), 6), round(d.Z(), 6)],
                "generator": _curve(S.BasisCurve())}
    if isinstance(S, Geom_OffsetSurface):
        return {"type": "offset", "offset": round(S.Offset(), 6), "basis": carrier(S.BasisSurface())}
    try:
        return {"type": type(S).__name__, "converted": True, **_net(GeomConvert.SurfaceToBSplineSurface_s(S))}
    except Exception as e:  # noqa: BLE001 - say what the carrier is even when it cannot be converted
        return {"type": type(S).__name__, "error": f"{type(e).__name__}: {str(e)[:120]}"}


def face(path, ir_id):
    import sdk_ocp
    from simplecadapi.inspect import brep
    lines, recs, infos, newid = _load(path)
    members = [k for k, v in newid.items() if v == ir_id]
    out = {"ir_id": ir_id, "record": recs.get(ir_id), "sdk_faces": members}
    if not members:
        out["note"] = "no face has this IR id"
        return out
    rep = next((k for k in members if "dead" not in infos[k]), members[0])
    if out["record"] is None:
        out["note"] = "implied face (no record of its own): a prism or loop-prism wall, rebuilt from the loop it sweeps"
        inf = infos[rep]
        if inf["name"] == "PLANE":
            out["carrier"] = {"t": "PLANE", "o": [round(float(c), 4) for c in inf["o"]], "n": [round(float(c), 6) for c in inf["n"]]}
        elif inf["name"] == "CYL":
            out["carrier"] = {"t": "CYL", "p": [round(float(c), 4) for c in inf["p"]], "d": [round(float(c), 6) for c in inf["dirv"]],
                              "r": round(float(inf["rad"]), 4)}
    if infos[rep]["name"] in ("BSPL", "BEZ", "OTHER", "REV", "EXT") or out["record"] is None:
        model = brep.load_step_rbrepmodel(path=str(path))
        out["spline_carriers"] = [{"sdk_face": m, **carrier(sdk_ocp.surface(sdk_ocp.face(model, m)))} for m in members
                                  if infos[m]["name"] not in ("PLANE", "CYL", "CONE", "SPHERE", "TORUS")]
    return out


def evidence(path, ir_id):
    import cadfit
    lines, recs, infos, newid = _load(path)
    rec = recs.get(ir_id) or {}
    if rec.get("t") in ("REV", "EXT"):
        op = "revolve" if rec["t"] == "REV" else "extrude"
        return {"ir_id": ir_id, "decisive": True, "from_carrier": True, "ops": [{"op": op, **({"axis": rec["d"], "point": rec["p"]} if op == "revolve" else {"dir": rec["d"]})}],
                "note": "the face is stored as a surface of %s; its motion is exact, no fit needed" % ("revolution" if op == "revolve" else "linear extrusion")}
    part = cadfit.load(str(path))
    if ir_id not in part["rows"]:
        return {"ir_id": ir_id, "note": "no samples for this face"}
    A = part["rows"][ir_id]
    res, V = cadfit.nullspace(A, len(A))
    d = cadfit.describe(V, res, part["origin"], part["scale"])
    d["singular_values"] = [float(f"{x:.3e}") for x in res]
    return {"ir_id": ir_id, **d}


def axis(path):
    return stepir_ops.analyse(str(path))["axes"]


def neighbours(path, ir_id):
    from simplecadapi.inspect import brep
    import blends
    lines, recs, infos, newid = _load(path)
    model = brep.load_step_rbrepmodel(path=str(path))
    rep = next(k for k, v in newid.items() if v == ir_id and "dead" not in infos[k])
    cache, out = {}, []
    for q in sorted({infos[x].get("dead", x) for x in infos[rep]["adj"]} - {rep}):
        L = blends.tangent_length(model, blends._members(infos[rep]), blends._members(infos[q]), cache)
        out.append({"ir_id": newid[q], "type": infos[q]["name"], "tangent_edge_length": round(L, 4)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step")
    ap.add_argument("what", choices=["face", "evidence", "axis", "neighbours"])
    ap.add_argument("ir_id", nargs="?", type=int)
    a = ap.parse_args()
    if a.what == "axis":
        res = axis(a.step)
    else:
        if a.ir_id is None:
            ap.error(f"{a.what} needs an IR face id")
        res = {"face": face, "evidence": evidence, "neighbours": neighbours}[a.what](a.step, a.ir_id)
    print(json.dumps(res, ensure_ascii=False, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


if __name__ == "__main__":
    main()
