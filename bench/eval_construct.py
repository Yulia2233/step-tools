#!/usr/bin/env python3
"""How well do the construction parameters (derived sweep/loft lines) match the code that built the part?

  python -I bench/eval_construct.py [--cases ...] [--workers 8]

Ground truth: bench/construct_gt/<case>.json (capture_construct.py: the path and profile given to sweep_rsolid, the
sections given to loft_rsolid). For every case whose candidate IR has a derived sweep or loft line:
  sweep  rail_err  = largest distance from the IR rail points to the true path, / bbox diagonal
         prof_area = |IR profile area / true profile area - 1|
  loft   n_ok      = IR section count equals the true section count
         end_area  = |IR end-section area / true end-section area - 1| (both ends)
         ends_off  = distance between IR and true end-section planes' centres, / diag
Also counts free-form sweeps/lofts in the truth that got no derived line at all (missed).
"""
import argparse, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def chain(pieces, tol):
    pieces = [np.asarray(p, float) for p in pieces]
    used = [False] * len(pieces)
    loops = []
    for s in range(len(pieces)):
        if used[s]:
            continue
        used[s] = True
        ch = [pieces[s]]
        while np.linalg.norm(ch[-1][-1] - ch[0][0]) > tol:
            end, nxt = ch[-1][-1], None
            for j, e in enumerate(pieces):
                if not used[j] and np.linalg.norm(e[0] - end) <= tol:
                    nxt = e
                elif not used[j] and np.linalg.norm(e[-1] - end) <= tol:
                    nxt = e[::-1]
                if nxt is not None:
                    used[j] = True
                    break
            if nxt is None:
                break
            ch.append(nxt)
        loops.append(np.vstack([c[:-1] for c in ch]) if len(ch) > 1 else ch[0][:-1])
    return loops


def plane_area(L):
    c = L.mean(0)
    _, _, vt = np.linalg.svd(L - c, full_matrices=False)
    x, y = vt[0], vt[1]
    P = np.c_[(L - c) @ x, (L - c) @ y]
    a = P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]
    return abs(a.sum()) / 2.0, L.mean(0)


def section_truth(edges, diag):
    loops = chain(edges, 1e-3 * diag)
    big = max(loops, key=lambda L: plane_area(L)[0])
    return plane_area(big)


def dist_to_polyline(p, P):
    best = 1e18
    for a, b in zip(P[:-1], P[1:]):
        ab = b - a
        t = np.clip(float((p - a) @ ab) / max(float(ab @ ab), 1e-18), 0, 1)
        best = min(best, float(np.linalg.norm(p - (a + t * ab))))
    return best


def one(case):
    sys.path.insert(0, str(ROOT / "cand"))
    import pipeline
    gt = json.load(open(HERE / "construct_gt" / f"{case}.json"))
    out = pipeline.run(HERE / "data" / case / "orig.step")
    head = json.loads(out["lines"][0])
    bb = np.asarray(head["bbox"], float)
    diag = float(np.linalg.norm(bb[1] - bb[0]))
    lines = [json.loads(l) for l in out["lines"] if '"derived":"op"' in l]
    sw = [l for l in lines if l["op"] == "sweep"]
    lo = [l for l in lines if l["op"] == "loft"]
    types = {json.loads(l)["id"]: json.loads(l)["t"] for l in out["lines"][1:] if '"id"' in l}
    free = sum(1 for t in types.values() if t in ("BSPL", "BEZ", "OTHER"))
    res = {"case": case, "sweep": [], "loft": [], "missed": []}
    for call in gt["calls"]:
        if call["op"] == "sweep_rsolid" and "path" in call:
            path = np.vstack([np.asarray(e) for e in call["path"]])
            cand = [l for l in sw if "rail" in l]
            if not cand:
                if free:
                    res["missed"].append("sweep")
                continue
            best = None
            for l in cand:
                R = np.asarray(l["rail"], float)
                err = max(dist_to_polyline(p, path) for p in R) / diag
                pa = None
                if l.get("profile") and call.get("profile_area"):
                    pa = abs(l["profile"]["area"] / call["profile_area"] - 1)
                if best is None or err < best[0]:
                    best = (err, pa)
            res["sweep"].append({"rail_err": best[0], "prof_area": best[1]})
        elif call["op"] == "loft_rsolid" and "sections" in call:
            truth = [section_truth([np.asarray(e) for e in s], diag) for s in call["sections"]]
            cand = [l for l in lo if l.get("sections")]
            if not cand:
                if free:
                    res["missed"].append("loft")
                continue
            def end_gap(l):
                o = [np.asarray(x["o"], float) for x in l["sections"]]
                return min(np.linalg.norm(o[0] - truth[0][1]) + np.linalg.norm(o[-1] - truth[-1][1]),
                           np.linalg.norm(o[-1] - truth[0][1]) + np.linalg.norm(o[0] - truth[-1][1]))
            l = min(cand, key=end_gap)                     # the IR loft whose ends sit where this loft's ends are
            S = l["sections"]
            ends = []
            for (ta, tc), s in ((truth[0], None), (truth[-1], None)):
                j = min(range(len(S)), key=lambda j: np.linalg.norm(np.asarray(S[j]["o"]) - tc))
                ends.append((abs(S[j]["area"] / ta - 1) if ta > 0 else None, float(np.linalg.norm(np.asarray(S[j]["o"]) - tc)) / diag))
            res["loft"].append({"n_ok": len(S) == len(truth), "n": [len(S), len(truth)],
                                "end_area": max(e[0] for e in ends if e[0] is not None), "ends_off": max(e[1] for e in ends)})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    cases = a.cases or sorted(p.stem for p in (HERE / "construct_gt").glob("*.json")
                              if any(c["op"] in ("sweep_rsolid", "loft_rsolid") for c in json.load(open(p))["calls"]))
    import multiprocessing as mp
    with ProcessPoolExecutor(a.workers, mp_context=mp.get_context("spawn")) as ex:
        rs = list(ex.map(one, cases))
    sw = [x for r in rs for x in r["sweep"]]
    lo = [x for r in rs for x in r["loft"]]
    miss = [(r["case"], m) for r in rs for m in r["missed"]]
    q = lambda v: np.round(np.quantile(v, [0.5, 0.9, 1.0]), 4).tolist() if v else None
    print(f"SWEEPS with a rail: {len(sw)}  rail_err/diag q50/q90/max {q([x['rail_err'] for x in sw])}"
          f"  profile area err {q([x['prof_area'] for x in sw if x['prof_area'] is not None])}"
          f"  rail_err<1%: {sum(x['rail_err'] < 0.01 for x in sw)}")
    print(f"LOFTS with sections: {len(lo)}  count right {sum(x['n_ok'] for x in lo)}  end area err {q([x['end_area'] for x in lo])}"
          f"  end centre off/diag {q([x['ends_off'] for x in lo])}")
    print(f"MISSED (free-form faces present, no derived line): {len(miss)} {miss[:10]}")
    bad = sorted([(x["rail_err"], r["case"]) for r in rs for x in r["sweep"]], reverse=True)[:6]
    print("worst sweeps:", [(c, round(e, 4)) for e, c in bad])
    badl = [(r["case"], x["n"], round(x["end_area"], 3)) for r in rs for x in r["loft"] if not x["n_ok"] or x["end_area"] > 0.05][:8]
    print("loft issues:", badl)


if __name__ == "__main__":
    main()
