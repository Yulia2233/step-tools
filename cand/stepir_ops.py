#!/usr/bin/env python3
"""Operation-level facts for a STEP part, expressed in IR face ids: which faces are blends, which faces each blend sits
between, and which faces share an axis.

  stepir_ops.py part.step [--json]

Why. The IR describes faces one at a time; whether a face came from `fillet_rsolid` or is a real cylindrical feature is a
property of the face AND its neighbours. Measured on 27B v2: on parts with any free-form face the build rate is 4 % (83 % on
prismatic parts), and the largest single error is `ql.edge.resolve` - an edge selection that matched nothing, i.e. the model
guessing which edges carry a blend. These facts are what it would need in order not to guess.

Sources, in order of trust:
  * `brep.inspect_manufacturing_hints_rdescriptor` - the SDK's own fillet/chamfer region candidates, with carrier type,
    radius, and the tangent boundary edges. Planar chamfers are only visible here: the IR omits `adj` for planar faces.
  * `model.describe_entity(face:i)["adjacency"]` - full face adjacency, including planes.
  * `stepir.build_ir.last_face_map` - the IR renumbering, so every id below is an IR id and can be quoted in a prompt.

A blend's `between` is its adjacent faces that are not themselves blends: those are the two faces whose shared boundary is
the edge that was rounded, which is exactly the argument `shared_boundary` takes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("STEPIR_NDIG", "4")
TOL_ANG = 1e-3
TOL_REL = 2e-3


def unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def axis_of(rec):
    if rec.get("t") in ("CYL", "CONE", "TORUS", "SPHERE", "REV") and "d" in rec and "p" in rec:
        return unit(rec["d"]), np.asarray(rec["p"], float)
    return None


def dist_between_axes(a, b):
    (da, pa), (_, pb) = a, b
    w = pb - pa
    return float(np.linalg.norm(w - np.dot(w, da) * da))


def detect_axes(recs, scale):
    """Faces whose carriers lie on one axis: one bored, turned or revolved feature rather than unrelated surfaces."""
    items = [(r["id"], axis_of(r)) for r in recs]
    items = [(i, a) for i, a in items if a is not None]
    clusters = []
    for i, (d, p) in items:
        for c in clusters:
            if abs(abs(float(np.dot(d, c["dir"]))) - 1.0) <= TOL_ANG and \
                    dist_between_axes((c["dir"], c["point"]), (d, p)) <= TOL_REL * scale:
                c["faces"].append(i)
                break
        else:
            clusters.append({"dir": d, "point": p, "faces": [i]})
    return [{"dir": [round(float(x), 4) for x in c["dir"]], "point": [round(float(x), 4) for x in c["point"]],
             "faces": sorted(c["faces"])}
            for c in sorted(clusters, key=lambda c: -len(c["faces"])) if len(c["faces"]) >= 2]


def meridian_of(cluster, by_ir):
    """The (z, r) profile of an axis cluster: the section you would sketch and revolve to rebuild it.

    z is measured along the cluster's `dir` from its `point` (world point + z * dir is the station on the axis); r is the
    distance from the axis. Each carrier contributes its exact meridian, read from its IR record:
      CYL    straight segment at constant r between its axial ends
      CONE   straight segment from (z0, r) to (z0 + s L cos a, r + L sin a): L is the SLANT length v[1], a the half-angle
      TORUS  arc of the tube circle (centre (z_c, R), radius r2) between the record's angular limits
      SPHERE arc of the great circle between the record's latitude limits
    where s = +1 when the face's own axis points along the cluster's dir and -1 otherwise.
    """
    d = unit(cluster["dir"])
    p0 = np.asarray(cluster["point"], float)
    segs = []
    for fid in cluster["faces"]:
        f = by_ir.get(fid)
        if f is None or "p" not in f:
            continue
        t = f["t"]
        z0 = float(np.dot(np.asarray(f["p"], float) - p0, d))
        s = 1.0 if "d" not in f or float(np.dot(unit(f["d"]), d)) >= 0 else -1.0
        v = f.get("v") or [0, 0]
        if t == "CYL":
            r = abs(float(f["r"]))
            za, zb = z0 + s * float(v[0]), z0 + s * float(v[1])
            segs.append({"face": fid, "kind": "line", "z": [round(za, 4), round(zb, 4)], "r": [round(r, 4), round(r, 4)]})
        elif t == "CONE":
            a = np.radians(float(f.get("ang", 0.0)))
            L = float(v[1]) - float(v[0])
            r0 = float(f["r"]) + float(v[0]) * np.sin(a)
            za = z0 + s * float(v[0]) * np.cos(a)
            segs.append({"face": fid, "kind": "line", "z": [round(za, 4), round(za + s * L * np.cos(a), 4)],
                         "r": [round(r0, 4), round(r0 + L * np.sin(a), 4)], "half_angle": f.get("ang")})
        elif t == "TORUS":
            R, r2 = float(f["r"]), float(f.get("r2", 0.0))
            seg = {"face": fid, "kind": "arc", "centre": [round(z0, 4), round(R, 4)], "arc_r": round(r2, 4)}
            if len(v) == 2:
                ends = [(z0 + s * r2 * np.sin(np.radians(x)), R + r2 * np.cos(np.radians(x))) for x in v]
                seg["from"], seg["to"] = [[round(a_, 4), round(b_, 4)] for a_, b_ in ends]
            segs.append(seg)
        elif t == "REV":
            seg = {"face": fid, "kind": "spline", "gen": f.get("gen")}
            if s < 0 or float(np.dot(np.asarray(f["p"], float) - p0, d)) != 0:
                seg["z_shift"], seg["z_sign"] = round(z0, 4), int(s)
            segs.append(seg)
        elif t == "SPHERE":
            R = float(f["r"])
            seg = {"face": fid, "kind": "arc", "centre": [round(z0, 4), 0.0], "arc_r": round(R, 4)}
            if len(v) == 2:
                ends = [(z0 + s * R * np.sin(np.radians(x)), R * np.cos(np.radians(x))) for x in v]
                seg["from"], seg["to"] = [[round(a_, 4), round(b_, 4)] for a_, b_ in ends]
            segs.append(seg)
    def key(g):
        if "z" in g:
            return min(g["z"])
        if "centre" in g:
            return min(g.get("from", [g["centre"][0]])[0], g.get("to", [g["centre"][0]])[0])
        return g.get("z_shift", 0.0)
    segs.sort(key=key)
    return _chain_meridian(segs)


def _ends(sg):
    if "z" in sg:
        return [sg["z"][0], sg["r"][0]], [sg["z"][1], sg["r"][1]]
    if "from" in sg:
        return list(sg["from"]), list(sg["to"])
    return None


def _flip(sg):
    if "z" in sg:
        sg["z"], sg["r"] = sg["z"][::-1], sg["r"][::-1]
    elif "from" in sg:
        sg["from"], sg["to"] = sg["to"], sg["from"]


def _chain_meridian(segs, rel=2e-3):
    """Order the meridian as one walk: every segment starts where the previous one ends (a segment is flipped when it was
    listed backwards), and endpoints that differ only by rounding are made identical."""
    ends = [_ends(s) for s in segs]
    if not segs or any(e is None for e in ends):
        return segs
    span = max(1.0, max(abs(v) for e in ends for p in e for v in p))
    tol = rel * span
    out = [segs[0]]
    left = segs[1:]
    if len(left) and min(np.hypot(*(np.subtract(_ends(segs[0])[0], q))) for s in left for q in _ends(s)) < \
            min(np.hypot(*(np.subtract(_ends(segs[0])[1], q))) for s in left for q in _ends(s)):
        _flip(out[0])                                     # walk away from the end that has no neighbour
    while left:
        end = _ends(out[-1])[1]
        best, bd, flip = None, 1e18, False
        for s in left:
            a, b = _ends(s)
            da, db = float(np.hypot(*np.subtract(a, end))), float(np.hypot(*np.subtract(b, end)))
            if min(da, db) < bd:
                best, bd, flip = s, min(da, db), db < da
        left.remove(best)
        if flip:
            _flip(best)
        if bd <= tol:                                     # same point up to rounding: share it
            a = _ends(best)[0]
            m = [round((a[0] + end[0]) / 2, 4), round((a[1] + end[1]) / 2, 4)]
            for s, which in ((out[-1], 1), (best, 0)):
                if "z" in s:
                    s["z"][which], s["r"][which] = m[0], m[1]
                else:
                    s["to" if which == 1 else "from"] = m
        else:
            best["gap"] = round(bd, 4)                     # not connected to the previous segment
        out.append(best)
    return out


def carrier_ops(by_ir):
    """Surfaces of revolution / extrusion carry their motion in the carrier itself: no fit needed, and none is trusted."""
    groups = {}
    for i, r in sorted(by_ir.items()):
        if r.get("t") == "REV":
            key = ("revolve", tuple(round(x, 4) for x in r["d"]), tuple(round(x, 3) for x in r["p"]))
        elif r.get("t") == "EXT":
            key = ("extrude", tuple(round(x, 4) for x in r["d"]), None)
        else:
            continue
        groups.setdefault(key, []).append(i)
    out = []
    for (op, d, p), faces in groups.items():
        g = {"op": op, "faces": faces, "residual": 0.0, "first_explained_here": faces, "from_carrier": True}
        if op == "revolve":
            g["axis"], g["point"] = list(d), list(p)
        else:
            g["dir"] = list(d)
        out.append(g)
    return out


SWEEP_TOL = 2.5e-3       # relative change of the iso-curves' distance matrix below which they are rigid copies of one profile


def classify_freeform(model, freeform_ids, infos, newid, adjacency, diag):
    """Name the likely generating operation of faces that no rigid motion sweeps - a profile carried along a curved rail keeps
    its shape (sweep), sections that change shape are a loft - and give each connected group its construction parameters."""
    import construct
    import geomnorm
    kind = {}
    for ident in freeform_ids:
        rep = next((k for k, v in newid.items() if v == ident and "dead" not in infos[k]), None)
        if rep is None or infos[rep]["name"] not in ("BSPL", "BEZ"):
            continue
        err = geomnorm.section_congruence(model, rep)
        if err is not None:
            kind[ident] = "sweep" if err <= SWEEP_TOL else "loft"
    out = []
    for op in ("sweep", "loft"):
        for comp in construct.components([i for i, k in kind.items() if k == op], adjacency):
            g = {"op": op, "faces": comp}
            c = construct.group_construction(model, infos, newid, op, set(comp), diag)
            if c:
                g.update(c)
            out.append(g)
    return out


def analyse(path, with_fit=False, lines=None):
    """`lines`: the IR already built by stepir.build_ir for this path (its face numbering is then shared, not rebuilt)."""
    from simplecadapi.inspect import brep
    import stepir
    if lines is None:
        lines = stepir.build_ir(str(path))
    fmap = getattr(stepir.build_ir, "last_face_map", {})          # original face index -> IR id
    head = json.loads(lines[0])
    recs = [json.loads(l) for l in lines[1:] if l.strip()]
    by_ir = {r["id"]: r for r in recs}
    bb = np.asarray(head["bbox"], float)
    scale = float(np.linalg.norm(bb[1] - bb[0])) or 1.0

    model = brep.load_step_rbrepmodel(path=str(path))
    adjacency = {}
    for i in range(len(model.faces)):
        if i not in fmap:
            continue
        nb = model.describe_entity(f"face:{i}")["adjacency"]["neighboring_faces"]
        adjacency[fmap[i]] = sorted(fmap[int(q.split(":")[1])] for q in nb if int(q.split(":")[1]) in fmap)

    import blends
    infos, live, newid = stepir.build_ir.last_infos, stepir.build_ir.last_live, stepir.build_ir.last_newid
    blends_found = blends.detect(model, infos, live, newid, by_ir, scale)
    blend_ids = {f for b in blends_found for f in b["faces"] + b.get("corners", [])}
    blends_out = blends_found
    axes = detect_axes(recs, scale)
    for c in axes:
        c["meridian"] = meridian_of(c, by_ir)
        c["z_is_measured_from"] = "point, along dir"
    out = {"part": Path(path).name, "n_faces": head["counts"]["face"], "types": head.get("types", {}),
           "scale": round(scale, 4), "blends": blends_out,
           "blend_faces": len(blend_ids),
           "axes": axes}
    if with_fit:
        # Which operation swept which face - asked only of the faces where the question has an answer. A plane is swept
        # by a three-parameter family of motions, so it agrees with almost any claim; a fillet face was not swept by the
        # base operation at all, it was added afterwards. Both would pad every group with faces that support nothing, so
        # the evidence is taken from the curved, non-blend faces and the rest is reported as a count.
        import cadfit
        part = cadfit.load(str(path))
        skip = blend_ids | {i for i, r in by_ir.items() if r.get("t") in ("PLANE", "REV", "EXT")}
        part["rows"] = {f: A for f, A in part["rows"].items() if f not in skip}
        fo = cadfit.face_ops(part)
        out["ops"] = cadfit.groups(part, fo)
        out["ops"] += carrier_ops(by_ir)
        out["freeform"] = sorted(f for f, v in fo.items() if v["nullity"] == 0)
        out["origin"] = classify_freeform(model, out["freeform"], infos, newid, adjacency, scale)
        out["fit_skipped"] = {"blend_faces": len(skip & blend_ids),
                              "planes": sum(1 for i, r in by_ir.items() if r.get("t") == "PLANE")}
    return out


LEGEND_OPS = """附加的派生信息（由 B-rep 分析确定性给出，不是猜测）：
`{"derived":"blend",...}` 一个倒角/圆角区域：`faces` 是它在上表中的面号，`kind` 为 fillet 或 chamfer，
`carrier` 是载体类型（CYLINDER/TORUS 用 fillet_rsolid，planar_bevel 用 chamfer_rsolid），`r` 是圆角半径，
`between` 是它所圆滑的**那两个面**——在重建时先把这两个面造出来，取它们的共享边，再倒角，不要去猜坐标。
`{"derived":"axis",...}` 一组共轴的面：`dir`/`point` 是公共轴，`faces` 是落在该轴上的面。
一个轴簇通常对应一个回转/镗孔/凸台特征，应当用同一个操作一次性建出来。
`meridian` 是该轴簇的**子午轮廓**：沿轴的 (z, r) 分段（line 给两端的 z 与 r，arc 给圆心 (centre_z, centre_r) 与半径 arc_r），
由各载体精确算出、未经采样。要用 `revolve_rsolid` 时，这就是你该画的那条截面线，不必自己从面表反推。
`{"derived":"op",...}` **这一组面是由哪个操作扫出来的**，由运动学拟合测得而非猜测：
SimpleCADAPI 的每个生成操作都是对轮廓施加一个单参数刚体运动——`extrude_rsolid` 平移、`revolve_rsolid` 旋转、
`helical_sweep_rsolid` 螺旋。一个面由该运动扫出，当且仅当运动的速度场处处与该面相切，这是关于 (c, w) 的线性方程，
解出来就是答案。`op` 为 extrude 时给 `dir`，为 revolve/helical 时给 `axis`/`point`（helical 另给 `pitch`）；
`faces` 是该运动能扫出的全部面，`residual` 是最大残差（已按包围盒对角线归一，0 表示精确）。
注意：**同一组面可能同时被多个操作扫出**（圆柱面既可拉伸也可回转，长方体在三个方向上都是棱柱），
列出的都是真的，选哪个由你决定；`first_explained_here` 标出该操作第一次解释到的面，据此挑一组互补的操作即可覆盖全件。
`{"derived":"freeform",...}` 这些面**没有任何刚体运动能扫出**，所以它们不可能来自 extrude/revolve/helical_sweep，
只能来自 `loft_rsolid`、沿曲线轨道的 `sweep_rsolid` 或样条曲面。不要再试图用拉伸去凑它们。"""


EVIDENCE_TYPES = {"CONE", "TORUS", "SPHERE", "BSPL", "BEZ", "OTHER", "REV", "EXT"}


def _line_x(p1, p2, q1, q2):
    d1, d2 = np.asarray(p2, float) - p1, np.asarray(q2, float) - q1
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return None
    w = np.asarray(q1, float) - p1
    s = (w[0] * d2[1] - w[1] * d2[0]) / den
    return np.asarray(p1, float) + s * d1


def sharp_loops(rec, cyls):
    """The planar loops with every arc that is the trace of a fillet cylinder (axis along the face normal, same radius,
    same centre) replaced by the corner its two neighbouring lines meet at: the outline before the edge was rounded."""
    if "loops" not in rec:
        return None
    o, n, x = (np.asarray(rec[k], float) for k in ("o", "n", "x"))
    y = np.cross(n, x)
    marks = []
    for c in cyls:
        d = unit(c["d"])
        if abs(abs(float(d @ n)) - 1.0) > 1e-6:
            continue
        w = np.asarray(c["p"], float) - o
        marks.append((float(w @ x), float(w @ y), float(c["r"])))
    if not marks:
        return None
    out, changed = [], False
    for lp in rec["loops"]:
        if "e" not in lp:
            out.append(lp)
            continue
        pts = [list(lp["s"])] + [sg[1:3] if sg[0] == "L" else sg[3:5] for sg in lp["e"]]
        segs = list(lp["e"])
        k = len(segs)
        drop = set()
        new_end = {}
        for i, sg in enumerate(segs):
            if sg[0] != "A":
                continue
            if not any(abs(sg[1] - mx) <= 1e-3 and abs(sg[2] - my) <= 1e-3 and
                       abs(float(np.hypot(pts[i][0] - sg[1], pts[i][1] - sg[2])) - mr) <= 1e-3 for mx, my, mr in marks):
                continue
            ip, inx = (i - 1) % k, (i + 1) % k
            if segs[ip][0] != "L" or segs[inx][0] != "L" or ip in drop or inx in drop:
                continue
            cp = _line_x(pts[ip], pts[i], pts[i + 1], pts[inx + 1])
            if cp is None:
                continue
            drop.add(i)
            new_end[ip] = [round(float(cp[0]), 4), round(float(cp[1]), 4)]
        if not drop:
            out.append(lp)
            continue
        changed = True
        start = list(lp["s"])
        e2 = []
        for i, sg in enumerate(segs):
            if i in drop:
                continue
            e2.append(["L"] + new_end[i] if i in new_end else sg)
        if (k - 1) in new_end:                             # the last segment now ends at a new corner: the loop starts there
            start = new_end[k - 1]
        if 0 in drop:
            start = new_end.get(k - 1, start)
        out.append({"s": start, "e": e2})
    return out if changed else None


def augment(lines, facts):
    """The IR with the derived facts appended as extra lines, in the same JSON-lines shape.

    Only facts that cannot be re-read from the face records are written. A cylinder is swept by an extrusion AND a revolution,
    a plane by almost anything: those say nothing, so an `op` line must explain at least one cone, torus, sphere or spline face,
    and lists only the faces that carry evidence. The meridian of an axis cluster is computed from the carriers on request
    (stepir_query.py), not stored."""
    types = {}
    for ln in lines[1:]:
        if ln.strip():
            j = json.loads(ln)
            types[j["id"]] = j["t"]
    extra = []
    for b in facts["blends"]:
        rec = {"derived": b["kind"]}
        if b["kind"] == "fillet":
            rec["r"] = b["radius"]
        elif b.get("dist") is not None:
            rec["d"] = b["dist"]
        rec["faces"] = b["faces"]
        rec["between"] = b["between"]
        for k in ("corners", "on_blend", "uncertain"):
            if b.get(k):
                rec[k] = b[k]
        extra.append(json.dumps(rec, separators=(",", ":"), ensure_ascii=False))
    recs = {}
    for ln in lines[1:]:
        if ln.strip():
            j = json.loads(ln)
            recs[j["id"]] = j
    cyls = [recs[f] for b in facts["blends"] if b["kind"] == "fillet" for f in b["faces"]
            if recs.get(f, {}).get("t") == "CYL"]
    for fid, rec in recs.items():
        if rec.get("t") == "PLANE" and cyls:
            sl = sharp_loops(rec, cyls)
            if sl:
                extra.append(json.dumps({"derived": "sharp", "face": fid, "loops": sl}, separators=(",", ":")))
    for g in facts.get("ops", []):
        if g["residual"] > 1e-3 and not g.get("first_explained_here"):
            continue
        ev = [f for f in g["faces"] if types.get(f) in EVIDENCE_TYPES]
        if not ev:
            continue
        rec = {"derived": "op", "op": g["op"], "faces": ev}
        if g["residual"] > 1e-6:
            rec["residual"] = g["residual"]
        if g["residual"] > 1e-3:
            rec["approximate"] = True
        for k in ("dir", "axis", "point", "pitch"):
            if k in g:
                rec[k] = g[k]
        extra.append(json.dumps(rec, separators=(",", ":"), ensure_ascii=False))
    for g in facts.get("origin", []):
        rec = {"derived": "op", "op": g["op"], "faces": g["faces"]}
        for k in ("rail", "rail_line", "rail_closed", "rail_partial", "frame", "helix", "profile", "sections", "ruled_or_spans"):
            if g.get(k) not in (None, [], {}):
                rec[k] = g[k]
        extra.append(json.dumps(rec, separators=(",", ":")))
    if facts.get("freeform"):
        extra.append(json.dumps({"derived": "freeform", "faces": facts["freeform"]},
                                separators=(",", ":"), ensure_ascii=False))
    for ax in facts["axes"]:
        extra.append(json.dumps({"derived": "axis", "dir": ax["dir"], "point": ax["point"], "faces": ax["faces"]},
                                separators=(",", ":"), ensure_ascii=False))
    return list(lines) + extra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--augment", action="store_true", help="print the IR with the derived lines appended")
    ap.add_argument("--fit", action="store_true", help="also fit the generating operation of every face (cadfit)")
    a = ap.parse_args()
    import stepir
    lines = stepir.build_ir(a.target)             # built once: the derived facts quote this numbering
    facts = analyse(a.target, with_fit=a.fit, lines=lines)
    if a.augment:
        print("\n".join(augment(lines, facts)))
    else:
        print(json.dumps(facts, ensure_ascii=False, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


if __name__ == "__main__":
    main()
