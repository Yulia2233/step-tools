#!/usr/bin/env python3
"""Computational-geometry success rate of a STEP -> IR candidate (cand/pipeline.py), on the 200-part tail-solid benchmark.

  envs/cad214/bin/python -I bench/eval_geom.py [--cases case-001 ...] [--workers 8] [--variants orig,split,nurbs,splitnurbs]

Every part exists in four forms - the original, `split` (periodic faces cut at the seam, large faces cut by area),
`nurbs` (every face converted to a B-spline surface) and `splitnurbs` - and the answer key is exact:
  * the parent (original) face of every variant face, found geometrically        -> merging
  * the true carrier of every parent face (plane / cylinder / cone / sphere / torus) -> NURBS re-recognition
  * which modelling operation created every face, and which two faces a fillet or chamfer rounded
    (from re-running the construction code, bench/data/*/gt_ops.json)              -> origin / blend facts
The candidate is scored only on what is visible in the IR text it returns. Nothing in the score depends on how it works.

Printed (one number per line, last match wins for ar.py):
  SCORE            dev-split quality x token factor   <- the optimisation target
  TEST_SCORE       the same on the held-out families (a guard against fitting the dev families, not a target)
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import signal
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
CAND = ROOT / "cand"
TOKENIZER = ROOT.parent / "envs" / "tok" / "tokenizer.json"
VARIANTS = ("orig", "split", "nurbs", "splitnurbs")
ANALYTIC = ("PLANE", "CYLINDER", "CONE", "SPHERE", "TORUS")
IR_TO_SDK = {"PLANE": "PLANE", "CYL": "CYLINDER", "CONE": "CONE", "SPHERE": "SPHERE", "TORUS": "TORUS"}
SDK_TO_IR = {v: k for k, v in IR_TO_SDK.items()}
WEIGHTS = {"stability": 0.30, "merge": 0.15, "analytic": 0.20, "origin": 0.20, "blend": 0.15}
TIMEOUT = 240


# ----------------------------------------------------------------------------------------------------- bench integrity
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_manifest():
    mf = HERE / "MANIFEST.json"
    if not mf.exists():
        sys.exit("bench/MANIFEST.json missing")
    bad = [k for k, h in json.load(open(mf))["files"].items() if not (HERE / k).exists() or sha(HERE / k) != h]
    if bad:
        sys.exit(f"benchmark data differs from MANIFEST.json ({len(bad)} files, e.g. {bad[:3]}); refusing to score")


# ----------------------------------------------------------------------------------------------------- dev / test split
def splits():
    """Families are split, not parts: ten variants of one family never straddle dev and test."""
    fam = {}
    for d in sorted(DATA.iterdir()):
        if (d / "design.json").exists():
            j = json.load(open(d / "design.json"))
            fam.setdefault((j["group"], j["family"]), []).append(d.name)
    out = {}
    for g in sorted({k[0] for k in fam}):
        for n, k in enumerate(sorted(k for k in fam if k[0] == g)):
            for c in fam[k]:
                out[c] = "dev" if n % 2 == 0 else "test"
    return out


# ----------------------------------------------------------------------------------------------------- carriers
def unit(v):
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def gt_carrier(g):
    """Canonical carrier of an SDK face description (geometry dict), or None for free-form faces."""
    t, p = g["type"], g["parameters"]
    if t == "PLANE":
        n = unit(p["normal"])
        return {"t": "PLANE", "n": n, "d": float(n @ np.asarray(p["origin"], float))}
    if t == "CYLINDER":
        return {"t": "CYLINDER", "p": np.asarray(p["axis"]["point"], float), "d": unit(p["axis"]["direction"]), "r": float(p["radius"])}
    if t == "CONE":
        return {"t": "CONE", "p": np.asarray(p["apex"], float), "d": unit(p["axis"]["direction"]),
                "a": math.radians(abs(float(p["semi_angle_degrees"])))}
    if t == "SPHERE":
        return {"t": "SPHERE", "p": np.asarray(p["center"], float), "r": float(p["radius"])}
    if t == "TORUS":
        return {"t": "TORUS", "p": np.asarray(p["axis"]["point"], float), "d": unit(p["axis"]["direction"]),
                "R": float(p["major_radius"]), "r": float(p["minor_radius"])}
    return None


def rec_carrier(rec):
    """Canonical carrier of an IR face record (the inverse of gt_carrier), or None."""
    t = rec.get("t")
    try:
        if t == "PLANE":
            n = unit(rec["n"])
            return {"t": "PLANE", "n": n, "d": float(n @ np.asarray(rec["o"], float))}
        if t == "CYL":
            return {"t": "CYLINDER", "p": np.asarray(rec["p"], float), "d": unit(rec["d"]), "r": float(rec["r"])}
        if t == "CONE":
            ang = math.radians(abs(float(rec["ang"])))
            d, p, r = unit(rec["d"]), np.asarray(rec["p"], float), float(rec["r"])
            return {"t": "CONE", "p": p, "d": d, "a": ang, "r": r, "apex_from_p": True}
        if t == "SPHERE":
            return {"t": "SPHERE", "p": np.asarray(rec["p"], float), "r": float(rec["r"])}
        if t == "TORUS":
            return {"t": "TORUS", "p": np.asarray(rec["p"], float), "d": unit(rec["d"]), "R": float(rec["r"]), "r": float(rec["r2"])}
    except (KeyError, TypeError, ValueError):
        return None
    return None


def line_dist(p, q, d):
    w = np.asarray(p, float) - np.asarray(q, float)
    return float(np.linalg.norm(w - float(w @ d) * d))


def carrier_equal(a, b, ptol, atol=2e-6):
    """Same surface (not just the same kind). `a` is canonical truth; `b` may come from an IR record."""
    if a is None or b is None or a["t"] != b["t"]:
        return False
    t = a["t"]
    par = lambda x, y: 1.0 - abs(float(x @ y)) <= atol
    if t == "PLANE":
        s = 1.0 if float(a["n"] @ b["n"]) >= 0 else -1.0
        return par(a["n"], b["n"]) and abs(a["d"] - s * b["d"]) <= ptol
    if t == "CYLINDER":
        return par(a["d"], b["d"]) and abs(a["r"] - b["r"]) <= ptol and line_dist(b["p"], a["p"], a["d"]) <= ptol
    if t == "SPHERE":
        return abs(a["r"] - b["r"]) <= ptol and float(np.linalg.norm(a["p"] - b["p"])) <= ptol
    if t == "TORUS":
        return (par(a["d"], b["d"]) and abs(a["R"] - b["R"]) <= ptol and abs(a["r"] - b["r"]) <= ptol
                and line_dist(b["p"], a["p"], a["d"]) <= ptol)
    if t == "CONE":
        if not par(a["d"], b["d"]) or abs(a["a"] - b["a"]) > math.radians(0.1):
            return False
        return any(float(np.linalg.norm(x - y)) <= ptol * 5 for x in cone_apexes(a) for y in cone_apexes(b))
    return False


def cone_apexes(c):
    """Possible apexes of a canonical cone carrier: its own `p` when that is the apex, else both candidates from a
    reference point on the axis with radius `r` (the IR record form leaves the growth direction open)."""
    if "apex_from_p" not in c:
        return [c["p"]]
    h = c["r"] / math.tan(c["a"]) if c["a"] > 1e-6 else 0.0
    return [c["p"] - h * c["d"], c["p"] + h * c["d"]]


def carrier_dev(c, pts):
    """Largest distance of sample points to the carrier c - an independent check of an analytic claim."""
    P = np.asarray(pts, float)
    t = c["t"]
    if t == "PLANE":
        return float(np.max(np.abs((P - c["n"] * c["d"]) @ c["n"])))
    if t == "CYLINDER":
        v = P - c["p"]
        rho = np.linalg.norm(v - np.outer(v @ c["d"], c["d"]), axis=1)
        return float(np.max(np.abs(rho - c["r"])))
    if t == "SPHERE":
        return float(np.max(np.abs(np.linalg.norm(P - c["p"], axis=1) - c["r"])))
    if t == "TORUS":
        v = P - c["p"]
        z = v @ c["d"]
        rho = np.linalg.norm(v - np.outer(z, c["d"]), axis=1)
        return float(np.max(np.abs(np.sqrt((rho - c["R"]) ** 2 + z ** 2) - c["r"])))
    if t == "CONE":
        if "apex_from_p" in c:
            h = c["r"] / math.tan(c["a"]) if c["a"] > 1e-6 else 0.0
            best = 1e9
            for apex in (c["p"] - h * c["d"], c["p"] + h * c["d"]):
                v = P - apex
                z = v @ c["d"]
                rho = np.linalg.norm(v - np.outer(z, c["d"]), axis=1)
                best = min(best, float(np.max(np.abs(rho * math.cos(c["a"]) - np.abs(z) * math.sin(c["a"])))))
            return best
        v = P - c["p"]
        z = v @ c["d"]
        rho = np.linalg.norm(v - np.outer(z, c["d"]), axis=1)
        return float(np.max(np.abs(rho * math.cos(c["a"]) - np.abs(z) * math.sin(c["a"]))))
    return 1e9



ORIGIN_FREEFORM = {"loft": "loft", "sweep": "sweep", "gordon": "skin"}          # non-rigid operations -> the name that earns full credit
ORIGIN_RIGID = {"revolve": ("revolve", False), "helical_sweep": ("helical", False), "twisted_sweep": ("helical", True),
                "spline_extrude": ("extrude", False)}          # (claim that earns full credit, does a bare "freeform" earn half?)
ORIGIN_NONRIGID_NAMES = {"loft", "sweep", "skin"}


def parent_of_group(cover, gid):
    """The single original face an IR group stands for, or None when it merges several."""
    ps = cover.get(gid, set())
    return next(iter(ps)) if len(ps) == 1 else None

# ----------------------------------------------------------------------------------------------------- IR parsing
def parse_ir(lines):
    head, recs, derived = None, {}, []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            j = json.loads(ln)
        except ValueError:
            continue
        if "derived" in j:
            derived.append(j)
        elif "unit" in j and head is None:
            head = j
        elif "id" in j and "t" in j:
            recs[j["id"]] = j
    return head, recs, derived


class Model:
    """simplecadapi model of one STEP with the per-face facts the scorer needs, loaded once."""

    def __init__(self, path):
        from simplecadapi.inspect import brep
        self.m = brep.load_step_rbrepmodel(path=str(path))
        self.n = len(self.m.faces)
        self.geo = [self.m.describe_entity(f"face:{i}")["geometry"] for i in range(self.n)]
        self.adj = [sorted(int(q.split(":")[1]) for q in self.m.describe_entity(f"face:{i}")["adjacency"]["neighboring_faces"])
                    for i in range(self.n)]
        self.carrier = [gt_carrier(g) for g in self.geo]
        bb = self.m.summary["bounding_box"] if hasattr(self.m, "summary") and isinstance(self.m.summary, dict) and "bounding_box" in self.m.summary else None
        self._diag = None
        self._pts = {}

    def diag(self):
        if self._diag is None:
            P = np.array([g["centroid"] for g in self.geo], float)
            self._diag = float(np.linalg.norm(P.max(0) - P.min(0))) or 1.0
        return self._diag

    def face_points(self, i):
        if i not in self._pts:
            sys.path.insert(0, str(HERE))
            import build_variants as bv
            from OCP.TopoDS import TopoDS
            f = self.m.resolve_entity(f"face:{i}")
            f = TopoDS.Face_s(f[-1] if isinstance(f, tuple) else f)
            self._pts[i] = bv.interior_points(f, 6)
        return self._pts[i]


# ----------------------------------------------------------------------------------------------------- scoring one variant
def timed(fn, *a):
    def h(*_):
        raise TimeoutError("pipeline timeout")
    old = signal.signal(signal.SIGALRM, h)
    signal.alarm(TIMEOUT)
    try:
        return fn(*a)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def natural_pairs(orig):
    """Adjacent original faces that already share one carrier: merging them is legitimate, so it is not scored."""
    out = set()
    tol = max(1e-3, 1e-5 * orig.diag())
    for a in range(orig.n):
        for b in orig.adj[a]:
            if b > a and orig.carrier[a] is not None and carrier_equal(orig.carrier[a], orig.carrier[b], tol):
                out.add((a, b))
    return out


def score_variant(case, variant, orig, var, parent, out, fm_orig_recs, tok, gt_ops):
    """Counts for one (part, variant) from the candidate's output. All counts are plain integers so they can be pooled."""
    lines, fm = out["lines"], {int(k): int(v) for k, v in out["face_map"].items()}
    head, recs, derived = parse_ir(lines)
    c = defaultdict(int)
    c["n_tokens"] = len(tok.encode("\n".join(lines)).ids)
    c["n_records"] = len(recs)
    c["n_faces"] = var.n
    ptol = max(1e-3, 1e-5 * var.diag())
    IMPL = -1

    def group(u):
        k = fm.get(u)
        return k if k in recs else IMPL

    # --- merge ---------------------------------------------------------------------------------------------------
    nat = natural_pairs(orig)
    ids = [u for u in range(var.n) if parent.get(u) is not None]
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            u, v = ids[x], ids[y]
            same = parent[u] == parent[v]
            gu, gv = group(u), group(v)
            merged = (gu == gv) and (gu != IMPL or same)
            if same and merged:
                c["m_tp"] += 1
            elif same:
                c["m_fn"] += 1
            elif merged and (min(parent[u], parent[v]), max(parent[u], parent[v])) not in nat:
                c["m_fp"] += 1

    # --- analytic --------------------------------------------------------------------------------------------------
    for u in ids:
        pc = orig.carrier[parent[u]]
        g = group(u)
        rec = recs.get(g)
        if pc is not None:
            if variant not in ("nurbs", "splitnurbs"):
                continue
            if rec is None:
                ok = fm_orig_recs is not None and fm_orig_recs["impl"].get(parent[u], False)
            else:
                ok = carrier_equal(pc, rec_carrier(rec), ptol)
            c["a_tp" if ok else "a_fn"] += 1
            c["a_tp_" + pc["t"] if ok else "a_fn_" + pc["t"]] += 1
        else:
            claimed = rec is not None and rec.get("t") in IR_TO_SDK
            if claimed:
                rc = rec_carrier(rec)
                pts = var.face_points(u)
                verified = rc is not None and pts and carrier_dev(rc, pts) <= max(2e-3, 2e-5 * var.diag())
                c["a_fp" if not verified else "a_tn_verified"] += 1
            else:
                c["a_tn"] += 1

    # --- origin / blend facts from the derived lines ----------------------------------------------------------------
    if gt_ops is not None and gt_ops.get("sdk_rebuild") == "ok":
        gf = {f["i"]: f for f in gt_ops["faces"]}
        claims = defaultdict(set)          # IR id -> operation names claimed for it
        blend_of = {}                      # IR id -> blend line
        for dl in derived:
            kind = dl.get("derived")
            if kind == "op" and dl.get("op"):
                for i in dl.get("faces", []):
                    claims[i].add(str(dl["op"]))
            elif kind == "freeform":
                for i in dl.get("faces", []):
                    claims[i].add("freeform")
            elif kind == "origin" and dl.get("op"):
                for i in dl.get("faces", []):
                    claims[i].add(str(dl["op"]))
            elif kind in ("blend", "fillet", "chamfer"):
                faces = dl.get("faces", [])
                btw = dl.get("between") or []
                grouped = len(btw) == len(faces) and len(faces) > 0 and all(isinstance(x, list) for x in btw)
                for idx, i in enumerate(faces):
                    entry = dict(dl)
                    if grouped:
                        entry["between"] = btw[idx]
                    blend_of[i] = entry
                for i in dl.get("corners", []):            # corner patches of a fillet chain: blend faces without a pair
                    blend_of.setdefault(i, {**dl, "between": []})
        rigid = {"extrude", "revolve", "helical"}
        # which variant faces fall in which IR group, and which original faces each IR group covers
        cover = defaultdict(set)
        for u in ids:
            cover[group(u)].add(parent[u])
        for u in ids:
            f = gf.get(parent[u])
            if f is None:
                continue
            g = group(u)
            cl = claims.get(g, set())
            org = f.get("origin")
            curved = f.get("type") != "PLANE"
            n0, s0 = c["o_n"], c["o_score"]
            if org in ORIGIN_FREEFORM and curved:
                c["o_n"] += 1
                if cl & rigid:
                    pass                                                 # a rigid-motion claim on a face no such motion sweeps
                elif ORIGIN_FREEFORM[org] in cl:
                    c["o_score"] += 2                                    # the right non-rigid operation (loft/sweep/skin)
                elif "freeform" in cl:
                    c["o_score"] += 1                                    # at least "no rigid motion made this"
            elif org in ORIGIN_RIGID and curved:
                c["o_n"] += 1
                want, half_if_freeform = ORIGIN_RIGID[org]
                if want in cl and "freeform" not in cl and not (cl & ORIGIN_NONRIGID_NAMES):
                    c["o_score"] += 2
                elif half_if_freeform and "freeform" in cl and want not in cl:
                    c["o_score"] += 1
            elif "freeform" in cl and org not in ("ambiguous", "unknown", "primitive"):
                c["o_fp"] += 1                                           # flagged free-form but a rigid operation or a blend made it
            if c["o_n"] > n0:
                c["od_n_" + str(org)] += c["o_n"] - n0
                c["od_s_" + str(org)] += c["o_score"] - s0
            # blend
            is_blend = org in ("fillet", "chamfer")
            line = blend_of.get(g)
            if is_blend:
                c["b_n"] += 1
                if line is not None:
                    c["b_hit"] += 1
                    sup = (f.get("blend") or {}).get("supports")
                    btw = line.get("between") or []
                    # each `between` entry must resolve to one support: an IR id that has a record and whose group
                    # contains the support face, or an inline carrier ({"t":"PLANE","n":..,"o":..} in IR-record form)
                    # equal to the support's surface. An id with no record (a face the IR leaves implied) does not resolve.
                    def hits(e, sp):
                        if isinstance(e, dict):
                            return orig.carrier[sp] is not None and carrier_equal(orig.carrier[sp], rec_carrier(e), ptol)
                        return e in recs and sp in cover.get(e, ())
                    if (sup and len(btw) == 2 and btw[0] != btw[1]
                            and ((hits(btw[0], sup[0]) and hits(btw[1], sup[1]))
                                 or (hits(btw[0], sup[1]) and hits(btw[1], sup[0])))):
                        c["b_support"] += 1
                        rad = (f.get("blend") or {}).get("radius_or_dist")
                        if org == "chamfer" or rad is None or line.get("r") is None or abs(float(line["r"]) - float(rad)) <= 0.03 * float(rad) + 1e-3:
                            c["b_ok"] += 1
            elif line is not None:
                c["b_fp"] += 1

    # --- stability signature multiset (filled by caller, needs the orig records) --------------------------------------
    out["_recs"], out["_derived"] = recs, derived
    return c


def match_records(ra, rb, ptol):
    """Greedy one-to-one matching of IR records by carrier (and area), for the stability score."""
    used = set()
    tp = 0
    for ia, a in ra.items():
        ca = rec_carrier(a)
        for ib, b in rb.items():
            if ib in used or a.get("t") != b.get("t"):
                continue
            if ca is not None:
                ok = carrier_equal(ca, rec_carrier(b), ptol)
            else:
                ba, bb = a.get("bb"), b.get("bb")
                ok = ba is not None and bb is not None and np.max(np.abs(np.asarray(ba, float) - np.asarray(bb, float))) <= ptol * 20
            if ok and abs(float(a.get("A", 0)) - float(b.get("A", 0))) <= 0.02 * max(float(a.get("A", 0)), 1.0) + 0.05:
                used.add(ib)
                tp += 1
                break
    return tp


def run_case(job):
    case, variants = job
    sys.path.insert(0, str(CAND))
    sys.path.insert(0, str(HERE))
    from tokenizers import Tokenizer
    import pipeline
    tok = Tokenizer.from_file(str(TOKENIZER))
    d = DATA / case
    res = {"case": case, "split": None, "variants": {}, "errors": []}
    try:
        orig = Model(d / "orig.step")
        vj = json.load(open(d / "variants.json"))["variants"]
        gt_ops = json.load(open(d / "gt_ops.json")) if (d / "gt_ops.json").exists() else None
    except Exception as e:  # noqa: BLE001
        res["errors"].append(f"setup: {e!r}"[:200])
        return res
    outs, models = {}, {}
    for v in variants:
        if v != "orig" and (v not in vj or "error" in vj[v]):
            continue
        t0 = time.time()
        try:
            # the candidate gets one STEP in an empty directory: it cannot see the answer key or the construction code
            with tempfile.TemporaryDirectory(prefix="geom-") as tmp:
                shutil.copy(d / f"{v}.step", Path(tmp) / "part.step")
                outs[v] = timed(pipeline.run, Path(tmp) / "part.step")
        except Exception as e:  # noqa: BLE001 - a crash is a failed variant, counted and reported
            res["errors"].append(f"{v}: {type(e).__name__}: {str(e)[:120]}")
            continue
        outs[v]["_secs"] = time.time() - t0
    fm_orig = None
    if "orig" in outs:
        h, r0, _ = parse_ir(outs["orig"]["lines"])
        fmo = {int(k): int(x) for k, x in outs["orig"]["face_map"].items()}
        fm_orig = {"impl": {i: fmo.get(i) not in r0 for i in range(orig.n)}}
    for v, out in outs.items():
        try:
            var = orig if v == "orig" else Model(d / f"{v}.step")
            parent = {i: i for i in range(orig.n)} if v == "orig" else {int(k): p for k, p in vj[v]["parent"].items()}
            c = score_variant(case, v, orig, var, parent, out, fm_orig, tok, gt_ops)
            recs, derived = out.pop("_recs"), out.pop("_derived")
            c["secs"] = out.get("_secs", 0.0)
            res["variants"][v] = {"counts": dict(c), "recs": {k: {kk: vv for kk, vv in r.items() if kk in ("t", "A", "bb", "o", "n", "p", "d", "r", "r2", "ang")}
                                                              for k, r in recs.items()}}
            out["_ok"] = True
        except Exception as e:  # noqa: BLE001
            import traceback
            res["errors"].append(f"score {v}: {e!r}"[:160] + traceback.format_exc()[-300:])
    # stability: candidate on a variant vs candidate on the original
    if "orig" in res["variants"]:
        ptol = max(1e-3, 1e-5 * orig.diag())
        r0 = {int(k): r for k, r in res["variants"]["orig"]["recs"].items()}
        for v, rv in res["variants"].items():
            if v == "orig":
                continue
            rr = {int(k): r for k, r in rv["recs"].items()}
            tp = match_records(r0, rr, ptol)
            rv["counts"]["s_tp"], rv["counts"]["s_a"], rv["counts"]["s_b"] = tp, len(r0), len(rr)
    for v in res["variants"].values():
        v.pop("recs", None)
    return res


# ----------------------------------------------------------------------------------------------------- aggregation
def f1(tp, fp, fn):
    return 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 1.0


def aggregate(results, part, base):
    S = defaultdict(float)
    toks, toks_orig, nvar = [], [], 0
    for r in results:
        if r["split"] != part:
            continue
        for v, d in r["variants"].items():
            c = d["counts"]
            for k, x in c.items():
                S[k] += x
            nvar += 1
            toks.append(c["n_tokens"])
            if v == "orig":
                toks_orig.append(c["n_tokens"])
    m = {}
    m["stability"] = 2 * S["s_tp"] / (S["s_a"] + S["s_b"]) if (S["s_a"] + S["s_b"]) else 0.0
    m["merge"] = f1(S["m_tp"], S["m_fp"], S["m_fn"])
    rec = S["a_tp"] / (S["a_tp"] + S["a_fn"]) if (S["a_tp"] + S["a_fn"]) else 1.0
    spec = S["a_tn"] + S["a_tn_verified"]
    spec = spec / (spec + S["a_fp"]) if (spec + S["a_fp"]) else 1.0
    m["analytic_recall"], m["analytic_spec"], m["analytic"] = rec, spec, 0.5 * (rec + spec)
    m["origin"] = S["o_score"] / (2 * S["o_n"] + S["o_fp"]) if (2 * S["o_n"] + S["o_fp"]) else float("nan")
    m["blend"] = S["b_ok"] / (S["b_n"] + S["b_fp"]) if (S["b_n"] + S["b_fp"]) else float("nan")
    m["blend_hit"] = S["b_hit"] / S["b_n"] if S["b_n"] else float("nan")
    m["blend_support"] = S["b_support"] / S["b_n"] if S["b_n"] else float("nan")
    m["blend_fp"] = S["b_fp"]
    m["tok_mean"] = float(np.mean(toks)) if toks else 0.0
    m["tok_orig"] = float(np.mean(toks_orig)) if toks_orig else 0.0
    m["tok_rel"] = m["tok_mean"] / base["tok_orig"] if base else 1.0
    m["tok_rel_orig"] = m["tok_orig"] / base["tok_orig"] if base else 1.0
    parts = {k: m[k] for k in WEIGHTS if not math.isnan(m[k])}
    wsum = sum(WEIGHTS[k] for k in parts)
    m["quality"] = sum(WEIGHTS[k] * parts[k] for k in parts) / wsum if wsum else 0.0
    m["tokf"] = min(1.0, 1.25 / m["tok_rel"], 1.15 / m["tok_rel_orig"]) if base and m["tok_rel"] > 0 and m["tok_rel_orig"] > 0 else 1.0
    m["score"] = m["quality"] * m["tokf"]
    m["n_variants"] = nvar
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--write-baseline", action="store_true", help="freeze the token reference from this run (done once, before init)")
    ap.add_argument("--no-manifest", action="store_true")
    ap.add_argument("--json", help="dump per-case results here")
    a = ap.parse_args()
    if not a.no_manifest:
        check_manifest()
    sp = splits()
    cases = a.cases or sorted(sp)
    variants = tuple(a.variants.split(","))
    import multiprocessing as mp
    t0 = time.time()
    results = []
    with ProcessPoolExecutor(a.workers, mp_context=mp.get_context("spawn")) as ex:
        for r in ex.map(run_case, [(c, variants) for c in cases], chunksize=1):
            r["split"] = sp.get(r["case"], "dev")
            results.append(r)
    basef = HERE / "baseline.json"
    base = json.load(open(basef)) if basef.exists() and not a.write_baseline else None
    if a.write_baseline:
        tk = [r["variants"]["orig"]["counts"]["n_tokens"] for r in results if "orig" in r["variants"]]
        json.dump({"tok_orig": float(np.mean(tk)), "n_orig": len(tk), "pipeline": "stepir.build_ir + stepir_ops.augment(fit)"}, open(basef, "w"))
        base = json.load(open(basef))
    errs = [(r["case"], e) for r in results for e in r["errors"]]
    dev, test = aggregate(results, "dev", base), aggregate(results, "test", base)
    for name, key in (("SCORE", "score"),):
        print(f"{name}: {dev[key]:.5f}")
    print(f"TEST_SCORE: {test['score']:.5f}")
    for k in ("quality", "tokf", "stability", "merge", "analytic", "analytic_recall", "analytic_spec", "origin", "blend", "blend_hit", "blend_support", "blend_fp", "tok_mean", "tok_rel", "tok_rel_orig"):
        print(f"{k.upper()}: {dev[k]:.5f}")
    for k in ("quality", "stability", "merge", "analytic", "origin", "blend", "tok_rel"):
        print(f"TEST_{k.upper()}: {test[k]:.5f}")
    S = defaultdict(float)
    for r in results:
        if r["split"] == "dev":
            for d in r["variants"].values():
                for k, x in d["counts"].items():
                    if k.startswith("od_"):
                        S[k] += x
    for org in sorted({k[5:] for k in S if k.startswith("od_n_")}):
        print(f"ORIGIN_{org.upper()}: {S['od_s_' + org] / (2 * S['od_n_' + org]):.4f} (n={int(S['od_n_' + org])})")
    print(f"ERRORS: {len(errs)}")
    print(f"SECONDS: {time.time() - t0:.1f}")
    for c, e in errs[:8]:
        print(f"  error {c}: {e[:200]}")
    if a.json:
        json.dump(results, open(a.json, "w"))


if __name__ == "__main__":
    main()
