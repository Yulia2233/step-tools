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
    if rec.get("t") in ("CYL", "CONE", "TORUS", "SPHERE") and "d" in rec and "p" in rec:
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

    Each carrier contributes its meridian exactly, no sampling: a cylinder is a segment at constant radius, a cone a sloped
    segment between its end radii, a torus an arc of its minor radius, a plane perpendicular to the axis a radial segment.
    z is measured along the cluster axis from its point, r is the distance from the axis.
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
        v = f.get("v") or [0, 0]
        if t == "CYL":
            r = float(f["r"])
            segs.append({"face": fid, "kind": "line", "z": [round(z0 + float(v[0]), 4), round(z0 + float(v[1]), 4)],
                         "r": [round(r, 4), round(r, 4)]})
        elif t == "CONE":
            # r is the radius at the face's own p and v is the axial range around it, but the IR does not fix which way the
            # radius grows along +v. Take the magnitude, and mark the segment when the two conventions disagree in sign so a
            # consumer knows the end radii are the candidates, not a settled answer.
            ang = np.radians(float(f.get("ang", 0.0)))
            r0, za, zb = float(f["r"]), float(v[0]), float(v[1])
            ra, rb = r0 + za * np.tan(ang), r0 + zb * np.tan(ang)
            seg = {"face": fid, "kind": "line", "z": [round(z0 + za, 4), round(z0 + zb, 4)],
                   "r": [round(abs(ra), 4), round(abs(rb), 4)], "half_angle": f.get("ang")}
            if ra < 0 or rb < 0:
                seg["sign_unresolved"] = True      # the parameterisation ran past the apex: direction of growth unknown
            segs.append(seg)
        elif t == "TORUS":
            segs.append({"face": fid, "kind": "arc", "centre_r": round(float(f["r"]), 4), "centre_z": round(z0, 4),
                         "arc_r": round(float(f.get("r2", 0.0)), 4)})
        elif t == "SPHERE":
            segs.append({"face": fid, "kind": "arc", "centre_r": 0.0, "centre_z": round(z0, 4),
                         "arc_r": round(float(f["r"]), 4)})
    segs.sort(key=lambda s: s.get("z", [s.get("centre_z", 0)])[0] if "z" in s else s.get("centre_z", 0))
    return segs


SWEEP_TOL = 2.5e-3       # relative change of the iso-curves' distance matrix below which they are rigid copies of one profile


def classify_freeform(model, freeform_ids, infos, newid):
    """Name the likely generating operation of faces that no rigid motion sweeps: a profile carried along a curved rail keeps
    its shape (sweep), sections that change shape are a loft."""
    import geomnorm
    groups = {}
    for ident in freeform_ids:
        rep = next((k for k, v in newid.items() if v == ident and "dead" not in infos[k]), None)
        if rep is None or infos[rep]["name"] not in ("BSPL", "BEZ"):
            continue
        err = geomnorm.section_congruence(model, rep)
        if err is None:
            continue
        groups.setdefault("sweep" if err <= SWEEP_TOL else "loft", []).append(ident)
    return [{"op": op, "faces": sorted(ids)} for op, ids in groups.items()]


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
    blends_found = blends.detect(model, infos, live, newid, by_ir)
    blend_ids = {f for b in blends_found for f in b["faces"]}
    blends_out = blends_found
    axes = detect_axes(recs, scale)
    for c in axes:
        c["meridian"] = meridian_of(c, by_ir)
    out = {"part": Path(path).name, "n_faces": head["counts"]["face"], "types": head.get("types", {}),
           "scale": round(scale, 4), "blends": blends_out,
           "blend_faces": sum(len(b["faces"]) for b in blends_out),
           "selectable_blends": sum(1 for b in blends_out if b["selectable"]),
           "axes": axes}
    if with_fit:
        # Which operation swept which face - asked only of the faces where the question has an answer. A plane is swept
        # by a three-parameter family of motions, so it agrees with almost any claim; a fillet face was not swept by the
        # base operation at all, it was added afterwards. Both would pad every group with faces that support nothing, so
        # the evidence is taken from the curved, non-blend faces and the rest is reported as a count.
        import cadfit
        part = cadfit.load(str(path))
        skip = {f for b in blends_out for f in b["faces"]} | {i for i, r in by_ir.items() if r.get("t") == "PLANE"}
        part["rows"] = {f: A for f, A in part["rows"].items() if f not in skip}
        fo = cadfit.face_ops(part)
        out["ops"] = cadfit.groups(part, fo)
        out["freeform"] = sorted(f for f, v in fo.items() if v["nullity"] == 0)
        out["origin"] = classify_freeform(model, out["freeform"], infos, newid)
        out["fit_skipped"] = {"blend_faces": len(skip & {f for b in blends_out for f in b["faces"]}),
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


EVIDENCE_TYPES = {"CONE", "TORUS", "SPHERE", "BSPL", "BEZ", "OTHER"}


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
        rec = {"derived": "blend", "faces": b["faces"], "kind": b["kind"], "carrier": b["carrier"],
               "between": b["between"]}
        if b.get("radius") is not None:
            rec["r"] = b["radius"]
        if b.get("angle_deg") is not None:
            rec["ang"] = b["angle_deg"]
        if not b["selectable"]:
            rec["uncertain"] = True
        extra.append(json.dumps(rec, separators=(",", ":"), ensure_ascii=False))
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
        extra.append(json.dumps({"derived": "op", "op": g["op"], "faces": g["faces"]}, separators=(",", ":")))
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
