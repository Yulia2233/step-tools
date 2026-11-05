#!/usr/bin/env python3
"""Independent checks of bench/data/*/gt_ops.json (different methods from build_gt_ops.py).

  check_gt_ops.py            (run with the SimpleCADAPI 2.1.4 python)

A. every blend face with plane supports: geometric consistency from SDK-reported carriers only
     chamfer plane : normal lies between the support normals and is parallel to their intersection line
     fillet cylinder: axis parallel to the supports' intersection line and at distance = radius from both support planes
B. counterfactual rebuild of sampled cases: model.py with asserts dropped and fillet/chamfer replaced by identity; the faces
   of orig.step whose carrier does not exist in that no-blend body must be exactly the faces labelled fillet/chamfer
C. sampled cases, loft/gordon/twisted/helical/spline_extrude/revolve faces: the face's sample points lie on a *trimmed* output
   face of the operation it was attributed to (BRepExtrema shape distance, not surface projection)
"""
import ast
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_gt_ops as G  # noqa: E402

DATA, PY225 = G.DATA, G.PY225


class Drop(ast.NodeTransformer):
    def visit_Assert(self, node):
        return ast.Pass()

    def visit_Call(self, node):
        self.generic_visit(node)
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in ("fillet_rsolid", "chamfer_rsolid"):
            for kw in node.keywords:
                if kw.arg == "solid":
                    return kw.value
            return node.args[0]
        return node


def cf_run(case, out):
    """Executed under the 2.2.5 python: rebuild with blends removed and write the body as BREP."""
    import importlib.util
    import shutil
    import tempfile
    from OCP.BRepTools import BRepTools
    d = Path(tempfile.mkdtemp(prefix="cf-"))
    src = ast.fix_missing_locations(Drop().visit(ast.parse((DATA / case / "model.py").read_text())))
    (d / "model.py").write_text(ast.unparse(src))
    spec = importlib.util.spec_from_file_location("cf", d / "model.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    body = m.build().part.body.wrapped
    BRepTools.Write_s(body, str(out))
    shutil.rmtree(d, ignore_errors=True)


def load_gt(case):
    return json.load(open(DATA / case / "gt_ops.json"))


def check_A():
    from simplecadapi.inspect import brep
    tot = {"chamfer_plane": [0, 0], "fillet_cyl": [0, 0], "untestable": 0}
    bad = []
    for c in sorted(os.listdir(DATA)):
        if not c.startswith("case-"):
            continue
        gt = load_gt(c)
        if not any("blend" in e for e in gt["faces"]):
            continue
        m = brep.load_step_rbrepmodel(path=str(DATA / c / "orig.step"))
        geo = {}

        def g(i):
            if i not in geo:
                geo[i] = m.describe_entity(f"face:{i}")["geometry"]
            return geo[i]
        for e in gt["faces"]:
            b = e.get("blend")
            if not b:
                continue
            a_, b_ = b["supports"]
            ga, gb, gn = g(a_), g(b_), g(e["i"])
            if gn["type"] == "PLANE" and ga["type"] == "PLANE" and gb["type"] == "PLANE":
                na, nb, nc = (np.asarray(x["normal_at_center"], float) for x in (ga, gb, gn))
                na, nb, nc = (v / np.linalg.norm(v) for v in (na, nb, nc))
                ok = abs(float(nc @ np.cross(na, nb))) < 1e-4 and nc @ na > 0 and nc @ nb > 0
                tot["chamfer_plane"][0] += ok
                tot["chamfer_plane"][1] += 1
                if not ok:
                    bad.append((c, e["i"], "chamfer"))
            elif gn["type"] == "CYLINDER" and ga["type"] == "PLANE" and gb["type"] == "PLANE":
                ax = gn["parameters"]["axis"]
                d = np.asarray(ax["direction"], float)
                d /= np.linalg.norm(d)
                p = np.asarray(ax["point"], float)
                na, nb = (np.asarray(x["normal_at_center"], float) for x in (ga, gb))
                na, nb = na / np.linalg.norm(na), nb / np.linalg.norm(nb)
                oa, ob = (np.asarray(x["parameters"]["origin"], float) for x in (ga, gb))
                r = float(gn["parameters"]["radius"])
                ok = (np.linalg.norm(np.cross(d, np.cross(na, nb))) < 1e-4 and abs(abs(float(na @ (p - oa))) - r) < 1e-3
                      and abs(abs(float(nb @ (p - ob))) - r) < 1e-3)
                tot["fillet_cyl"][0] += ok
                tot["fillet_cyl"][1] += 1
                if not ok:
                    bad.append((c, e["i"], "fillet"))
            else:
                tot["untestable"] += 1
    return tot, bad


def sample_cases():
    want = ["fillet_rsolid", "chamfer_rsolid", "loft_rsolid", "sweep_rsolid", "revolve_rsolid", "twisted_sweep_rsolid",
            "helical_sweep_rsolid", "make_gordon_surface_rface"]
    rng = random.Random(20261105)
    pick = []
    for w in want:
        cs = [c for c in sorted(os.listdir(DATA)) if c.startswith("case-") and
              any(o["op"] == w for o in load_gt(c)["ops_called"])]
        rng.shuffle(cs)
        for c in cs:
            if c not in pick:
                pick.append(c)
                break
    return pick


def check_B(cases):
    from simplecadapi.inspect import brep
    G._ocp()
    res = {}
    for c in cases:
        gt = load_gt(c)
        labelled = {e["i"] for e in gt["faces"] if e["actual_origin"] in ("fillet", "chamfer")}
        out = Path(f"/tmp/gt_cf_{c}.brep")
        p = subprocess.run([str(PY225), "-I", str(Path(__file__).resolve()), "--cf", c, str(out)], capture_output=True,
                           text=True)
        if p.returncode != 0:
            res[c] = ("cf-run-failed", (p.stderr or p.stdout)[-200:])
            continue
        cf_faces = G.faces_of(G.read_brep(out))
        cars = [G.Carrier(f) for f in cf_faces]
        m = brep.load_step_rbrepmodel(path=str(DATA / c / "orig.step"))
        nonblend_missing = set()
        for i in range(len(m.faces)):
            f = m.faces[i]
            pts = G.face_points(f)
            if not G.match_any(pts, G.adaptor_type(f), cars):
                nonblend_missing.add(i)
        res[c] = ("ok", len(labelled), len(nonblend_missing), sorted(labelled ^ nonblend_missing))
    return res


def check_C(cases):
    from simplecadapi.inspect import brep
    G._ocp()
    out = {}
    for c in cases:
        gt = load_gt(c)
        sc = G.SCRATCH / f"chk-{c}"
        p = subprocess.run([str(PY225), "-I", str(G.HERE / "gt_ops_stage1.py"), str(DATA / c), str(sc)], capture_output=True,
                           text=True)
        if p.returncode != 0:
            out[c] = ("stage1-failed",)
            continue
        recs = json.load(open(sc / "stage1.json"))["records"]
        m = brep.load_step_rbrepmodel(path=str(DATA / c / "orig.step"))
        n_ok = n_all = 0
        miss = []
        for e in gt["faces"]:
            if e["origin"] not in ("loft", "gordon", "twisted_sweep", "helical_sweep", "spline_extrude", "revolve"):
                continue
            ops = set(e["origin_ops"])
            pts = G.face_points(m.faces[e["i"]], 5)[:12]
            good = False
            for r in recs:
                if r["op"] not in ops or not r.get("out"):
                    continue
                for cf in G.faces_of(G.read_brep(sc / r["out"])):
                    dmax = 0.0
                    for (x, y, z) in pts:
                        v = G.BRepBuilderAPI_MakeVertex(G.gp_Pnt(x, y, z)).Vertex()
                        d = G.BRepExtrema_DistShapeShape(v, cf)
                        dmax = max(dmax, d.Value() if d.IsDone() else 1e9)
                    if dmax <= 1e-6:
                        good = True
                        break
                if good:
                    break
            n_all += 1
            n_ok += good
            if not good:
                miss.append(e["i"])
        out[c] = (n_ok, n_all, miss)
        import shutil
        shutil.rmtree(sc, ignore_errors=True)
    return out


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--cf":
        return cf_run(sys.argv[2], sys.argv[3])
    cases = sample_cases()
    print("sampled cases:", cases)
    tot, bad = check_A()
    print("A (all blends, geometric consistency):", tot, "failures:", bad[:10])
    print("B (counterfactual no-blend rebuild):")
    for c, r in check_B(cases).items():
        print("  ", c, r)
    print("C (trimmed-face distance):")
    for c, r in check_C(cases).items():
        print("  ", c, r)


if __name__ == "__main__":
    main()
