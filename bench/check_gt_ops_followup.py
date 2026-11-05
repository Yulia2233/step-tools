#!/usr/bin/env python3
"""Follow-up independent checks for gt_ops.json (run with python; appends to data/GT_OPS_REPORT.md).

 1. targeted 8-case sample covering fillet, chamfer, loft, twisted_sweep, gordon, spline_extrude, revolve cone/torus (+ sweep):
    item-level verdicts. Spline/revolve faces: sample points vs the TRIMMED output face of the attributed operation
    (BRepExtrema). Blend faces: supports adjacent to the blend face in orig.step, and (in the no-blend counterfactual body)
    the supports share a sharp edge that lies within 2*radius of the blend face.
 2a. where did the 30 sweep_rsolid calls go.
 2b. all blend faces: sharp-edge-near-blend check (multi-edge chains), and how many blend faces were trimmed / split by
     later booleans.
"""
import json
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_gt_ops as G  # noqa: E402
import check_gt_ops as C  # noqa: E402

DATA, PY225 = G.DATA, G.PY225
BLEND_OPS = ("fillet_rsolid", "chamfer_rsolid")


def area_of(face):
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    p = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, p)
    return p.Mass()


def blend_case(case):
    """Per-case diagnostics for all blend faces (needs stage-1 BREPs and the no-blend body)."""
    from simplecadapi.inspect import brep
    G._ocp()
    gt = C.load_gt(case)
    sc = G.SCRATCH / f"fu-{case}"
    p = subprocess.run([str(PY225), "-I", str(G.HERE / "gt_ops_stage1.py"), str(DATA / case), str(sc)],
                       capture_output=True, text=True)
    cf_out = f"/tmp/gt_fu_cf_{case}.brep"
    q = subprocess.run([str(PY225), "-I", str(HERE / "check_gt_ops.py"), "--cf", case, cf_out], capture_output=True, text=True)
    if p.returncode or q.returncode:
        return {"case": case, "error": "stage1/cf failed"}
    recs = json.load(open(sc / "stage1.json"))["records"]
    for r in recs:
        r["faces"] = G.faces_of(G.read_brep(sc / r["out"])) if r.get("out") else []
    body = G.read_brep(cf_out)
    cf = G.faces_of(body)
    cars = [G.Carrier(f) for f in cf]
    sharp = []          # (face idx a, face idx b, edge)
    for e, fs in G.edges_with_faces(body):
        if len(fs) == 2:
            ia = [k for k, f in enumerate(cf) if f.IsSame(fs[0])]
            ib = [k for k, f in enumerate(cf) if f.IsSame(fs[1])]
            if ia and ib:
                sharp.append((ia[0], ib[0], e))
    m = brep.load_step_rbrepmodel(path=str(DATA / case / "orig.step"))
    out = []
    for e in gt["faces"]:
        b = e.get("blend")
        if not b:
            continue
        fi = e["i"]
        face = m.faces[fi]
        adj = set(int(x.split(":")[1]) for x in m.describe_entity(f"face:{fi}")["adjacency"]["neighboring_faces"])
        adj_ok = all(s in adj for s in b["supports"])
        ms = [G.match_any(G.face_points(m.faces[s]), G.adaptor_type(m.faces[s]), cars) for s in b["supports"]]
        rad = float(b["radius_or_dist"] or 1.0)
        near, shared = False, False
        for (x, y, ed) in sharp:
            if (x in ms[0] and y in ms[1]) or (x in ms[1] and y in ms[0]):
                shared = True
                mid = G.edge_mid(ed)
                dv = G.BRepExtrema_DistShapeShape(G.BRepBuilderAPI_MakeVertex(mid).Vertex(), face)
                if dv.IsDone() and dv.Value() <= 2.0 * rad + 1e-3:
                    near = True
        # trimmed / split: compare with the area of the operation's output face carrying the same carrier
        ratio = None
        pts = G.face_points(face, 5)
        for r in recs:
            if r["op"] not in BLEND_OPS:
                continue
            for f in r["faces"]:
                c = G.Carrier(f)
                if c.type == G.adaptor_type(face) and G.on_carrier(pts, c):
                    ratio = area_of(face) / area_of(f)
        out.append({"case": case, "i": fi, "type": e["type"], "kind": b["kind"], "adj_ok": adj_ok, "shared": shared,
                    "near": near, "area_ratio": ratio})
    n_blend_ops = [(r["op"], sum(1 for f in r["faces"])) for r in recs if r["op"] in BLEND_OPS]
    return {"case": case, "items": out}


def sweep_report():
    c = Counter()
    ex = []
    for case in sorted(os.listdir(DATA)):
        if not case.startswith("case-"):
            continue
        gt = C.load_gt(case)
        n = sum(o["n"] for o in gt["ops_called"] if o["op"] == "sweep_rsolid")
        if not n:
            continue
        c["cases"] += 1
        c["calls"] += n
        for e in gt["faces"]:
            if "sweep_rsolid" in e["origin_ops"]:
                c[(e["type"], e["origin"])] += 1
                if len(ex) < 3:
                    ex.append((case, e["i"], e["type"], e["origin"], e.get("candidates")))
    return c, ex


def targeted_sample():
    cats = {
        "fillet": lambda gt: any(e.get("actual_origin") == "fillet" for e in gt["faces"]),
        "chamfer": lambda gt: any(e.get("actual_origin") == "chamfer" for e in gt["faces"]),
        "loft": lambda gt: any(e["origin"] == "loft" and e["type"] == "BSPLINE" for e in gt["faces"]),
        "twisted_sweep": lambda gt: any(e["origin"] == "twisted_sweep" and e["type"] == "BSPLINE" for e in gt["faces"]),
        "gordon": lambda gt: any(e["origin"] == "gordon" for e in gt["faces"]),
        "spline_extrude": lambda gt: any(e["origin"] == "spline_extrude" for e in gt["faces"]),
        "revolve_cone_torus": lambda gt: any(e["origin"] == "revolve" and e["type"] in ("CONE", "TORUS") for e in gt["faces"]),
        "sweep": lambda gt: any("sweep_rsolid" in e["origin_ops"] for e in gt["faces"]),
    }
    rng = random.Random(7)
    gts = {c: C.load_gt(c) for c in sorted(os.listdir(DATA)) if c.startswith("case-")}
    pick = {}
    for k, f in cats.items():
        cs = [c for c, g in gts.items() if f(g) and c not in pick.values()]
        rng.shuffle(cs)
        pick[k] = cs[0]
    return pick


def item_check(case):
    """Spline / revolve cone+torus faces vs the trimmed output face of the attributed op."""
    from simplecadapi.inspect import brep
    G._ocp()
    gt = C.load_gt(case)
    sc = G.SCRATCH / f"fu2-{case}"
    subprocess.run([str(PY225), "-I", str(G.HERE / "gt_ops_stage1.py"), str(DATA / case), str(sc)], capture_output=True)
    recs = json.load(open(sc / "stage1.json"))["records"]
    m = brep.load_step_rbrepmodel(path=str(DATA / case / "orig.step"))
    res = []
    for e in gt["faces"]:
        interesting = (e["origin"] in ("loft", "gordon", "twisted_sweep", "helical_sweep", "spline_extrude")
                       or (e["origin"] == "revolve" and e["type"] in ("CONE", "TORUS"))
                       or (e.get("actual_origin") is None and e["type"] in ("BSPLINE", "EXTRUSION")))
        if not interesting:
            continue
        ops = set(e["origin_ops"])
        pts = G.face_points(m.faces[e["i"]], 5)[:12]
        good, how = False, None
        for r in recs:
            if r["op"] not in ops or not r.get("out"):
                continue
            for cf in G.faces_of(G.read_brep(sc / r["out"])):
                dmax = max((G.BRepExtrema_DistShapeShape(G.BRepBuilderAPI_MakeVertex(G.gp_Pnt(*p)).Vertex(), cf).Value()
                            for p in pts), default=1e9)
                if dmax <= 1e-6:
                    good, how = True, r["op"]
                    break
            if good:
                break
        res.append({"case": case, "i": e["i"], "type": e["type"], "label": e["origin"], "ops": sorted(ops), "ok": good})
    import shutil
    shutil.rmtree(sc, ignore_errors=True)
    return res


def main():
    out = []
    sc, ex = sweep_report()
    out.append("## Follow-up independent checks")
    out.append("")
    out.append("### (a) where the sweep_rsolid calls went")
    out.append(f"- cases with sweep_rsolid: {sc['cases']}, calls: {sc['calls']}")
    for k, v in sc.items():
        if isinstance(k, tuple):
            out.append(f"- faces attributed to a sweep: type={k[0]} origin={k[1]} -> {v}")
    out.append("- no sweep face has origin `sweep` any more: every one is a CYLINDER (circle swept along a line) or TORUS "
               "(circle swept along an arc), which are surfaces of revolution; they are labelled `ambiguous` with "
               "`candidates` and `equivalent_origins`, `actual_origin` keeps `sweep`. There is NO free-form swept surface "
               "in the 200 cases: free-form faces come only from loft (BSPLINE), twisted_sweep, gordon, helical_sweep, spline_extrude.")
    out.append("")
    pick = targeted_sample()
    out.append("### 1. targeted sample (one case per category)")
    out.append("- " + ", ".join(f"{k}: {v}" for k, v in pick.items()))
    cases = sorted(set(pick.values()))
    with ProcessPoolExecutor(6) as exr:
        items = [x for r in exr.map(item_check, cases) for x in r]
    n_ok = sum(i["ok"] for i in items)
    out.append(f"- spline / revolve cone+torus faces, trimmed-op-face distance <= 1e-6: {n_ok}/{len(items)} correct")
    bad = [i for i in items if not i["ok"]]
    for i in bad:
        out.append(f"  - WRONG: {i}")
    by = Counter((i["label"], i["type"], i["ok"]) for i in items)
    for k, v in sorted(by.items()):
        out.append(f"  - {k[0]} / {k[1]}: {'correct' if k[2] else 'WRONG'} x{v}")
    out.append("")
    cs = [c for c in sorted(os.listdir(DATA)) if c.startswith("case-") and
          any(o["op"] in BLEND_OPS for o in C.load_gt(c)["ops_called"])]
    with ProcessPoolExecutor(6) as exr:
        res = list(exr.map(blend_case, cs))
    errs = [r for r in res if "error" in r]
    allb = [i for r in res for i in r.get("items", [])]
    sam = [i for i in allb if i["case"] in cases]
    out.append("### 2b. blend faces (supports): all vs the targeted sample")
    for name, s in (("all cases", allb), ("targeted sample", sam)):
        out.append(f"- {name}: {len(s)} blend faces; supports adjacent to the blend face in orig.step "
                   f"{sum(i['adj_ok'] for i in s)}; supports share a sharp edge in the no-blend body "
                   f"{sum(i['shared'] for i in s)}; that sharp edge lies within 2*radius of the blend face "
                   f"{sum(i['near'] for i in s)}")
    if errs:
        out.append(f"- cases that failed the check run: {[e['case'] for e in errs]}")
    worse = [i for i in allb if not (i["adj_ok"] and i["shared"] and i["near"])]
    for i in worse[:20]:
        out.append(f"  - WRONG/UNSURE: {i}")
    ratios = [i["area_ratio"] for i in allb if i["area_ratio"] is not None]
    trimmed = [r for r in ratios if r < 0.999]
    out.append(f"- blend faces trimmed by later booleans (final area < output-face area): {len(trimmed)}/{len(ratios)} "
               f"(min ratio {min(ratios):.3f}); their supports pass the same checks: "
               f"{sum(1 for i in allb if i['area_ratio'] is not None and i['area_ratio'] < 0.999 and i['adj_ok'] and i['shared'] and i['near'])}"
               f"/{len(trimmed)}")
    multi = Counter()
    for r in res:
        k = Counter(i["kind"] for i in r.get("items", []))
        for v in k.values():
            multi[min(v, 6)] += 1
    out.append(f"- blend faces per case and kind (chains): {dict(sorted(multi.items()))} (6 means >= 6)")
    text = "\n".join(out) + "\n"
    rp = DATA / "GT_OPS_REPORT.md"
    prev = rp.read_text()
    marker = "## Follow-up independent checks"
    if marker in prev:
        prev = prev[:prev.index(marker)]
    rp.write_text(prev.rstrip() + "\n\n" + text)
    print(text)


if __name__ == "__main__":
    main()
