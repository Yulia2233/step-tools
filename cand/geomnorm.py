#!/usr/bin/env python3
"""Geometry normalisation for the STEP IR: re-recognise what a B-rep says in the wrong words.

A face stored as a B-spline can be a plane, cylinder, cone, sphere or torus; the IR should say so. Everything here is
measured on exact surface samples (point + normal from the surface's first derivatives), never guessed from names, and
every tolerance scales with the part's bounding-box diagonal.

  recognize_face(model, index, diag, origin) -> carrier fields for stepir's face info, or None when the face is free-form
"""
from __future__ import annotations

import math

import numpy as np

import cadthreads  # noqa: F401  (bounds the kernel thread pool)
import sdk_ocp

TOL_REL = 1e-5          # max distance of any sample to the fitted carrier, relative to the bbox diagonal
AXIS_TOL = 2.0e-3       # twist-residual threshold of cadfit: a revolution axis exists when the normals meet one line


def _face_of(model, index):
    return sdk_ocp.face(model, index)


def samples(face, diag, want=8):
    """Interior points and OUTWARD unit normals of a face (exact D1 at triangulation nodes and triangle centroids)."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.gp import gp_Pnt, gp_Vec
    from OCP.TopLoc import TopLoc_Location
    ad = BRepAdaptor_Surface(face)
    flip = -1.0 if face.Orientation().name.endswith("REVERSED") else 1.0
    pts, nrm = [], []
    for defl in (diag * 1e-4, diag * 3e-5):          # a finer mesh of a big free-form face costs minutes; the grid fallback covers the rest
        BRepMesh_IncrementalMesh(face, defl, False, 8.0, True)
        tri = BRep_Tool.Triangulation_s(face, TopLoc_Location())
        if tri is None or not tri.HasUVNodes():
            continue
        uv = [(tri.UVNode(i).X(), tri.UVNode(i).Y()) for i in range(1, tri.NbNodes() + 1)]
        for i in range(1, tri.NbTriangles() + 1):
            a, b, c = tri.Triangle(i).Get()
            uv.append(tuple((np.asarray(uv[a - 1]) + np.asarray(uv[b - 1]) + np.asarray(uv[c - 1])) / 3.0))
        if len(uv) > 400:
            uv = [uv[k] for k in np.linspace(0, len(uv) - 1, 400).astype(int)]
        p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
        pts, nrm = [], []
        for u, v in uv:
            ad.D1(float(u), float(v), p, du, dv)
            n = np.cross([du.X(), du.Y(), du.Z()], [dv.X(), dv.Y(), dv.Z()])
            ln = float(np.linalg.norm(n))
            if ln < 1e-12:
                continue
            pts.append([p.X(), p.Y(), p.Z()])
            nrm.append(flip * n / ln)
        if len(pts) >= want:
            break
    if len(pts) < 6:
        pts, nrm = _grid_samples(face, ad, flip)
    if len(pts) < 6:
        return None
    return np.asarray(pts), np.asarray(nrm)


def _grid_samples(face, ad, flip, k=11):
    """Fallback when the triangulation gives nothing: a UV grid over the face's parameter box, kept where it is inside."""
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.BRepTools import BRepTools
    from OCP.gp import gp_Pnt, gp_Pnt2d, gp_Vec
    from OCP.TopAbs import TopAbs_IN
    u0, u1, v0, v1 = BRepTools.UVBounds_s(face)
    pts, nrm = [], []
    p, du, dv = gp_Pnt(), gp_Vec(), gp_Vec()
    for i in range(k):
        for j in range(k):
            u, v = u0 + (u1 - u0) * (i + 0.5) / k, v0 + (v1 - v0) * (j + 0.5) / k
            if BRepClass_FaceClassifier(face, gp_Pnt2d(u, v), 1e-7).State() != TopAbs_IN:
                continue
            ad.D1(u, v, p, du, dv)
            n = np.cross([du.X(), du.Y(), du.Z()], [dv.X(), dv.Y(), dv.Z()])
            ln = float(np.linalg.norm(n))
            if ln > 1e-12:
                pts.append([p.X(), p.Y(), p.Z()])
                nrm.append(flip * n / ln)
    return pts, nrm


def boundary_points(face, per_edge=16):
    """Points along every boundary edge of a face: they carry the face's true extent (interior samples undershoot it)."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    out = []
    ex = TopExp_Explorer(face, TopAbs_EDGE)
    while ex.More():
        c = BRepAdaptor_Curve(TopoDS.Edge_s(ex.Current()))
        a, b = c.FirstParameter(), c.LastParameter()
        for t in np.linspace(a, b, per_edge):
            q = c.Value(float(t))
            out.append([q.X(), q.Y(), q.Z()])
        ex.Next()
    return np.asarray(out) if out else np.zeros((0, 3))


# ----------------------------------------------------------------------------------------------------- fits
def _fit_plane(P, N, tol):
    c = P.mean(0)
    n = np.linalg.svd(P - c)[2][2]
    if np.abs((P - c) @ n).max() > tol or (np.abs(N @ n) < 1 - 1e-6).any():
        return None
    if float(N.mean(0) @ n) < 0:
        n = -n
    return {"kind": "PLANE", "n": n, "d": float(c @ n)}


def _fit_sphere(P, N, tol):
    A, b = np.zeros((3, 3)), np.zeros(3)
    for p, n in zip(P, N):
        M = np.eye(3) - np.outer(n, n)
        A += M
        b += M @ p
    try:
        c = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        return None
    rr = np.linalg.norm(P - c, axis=1)
    r = float(rr.mean())
    if r < 1e-9 or np.abs(rr - r).max() > tol:
        return None
    return {"kind": "SPHERE", "c": c, "r": r}


def _fit_revolution(P, N, tol, diag, origin):
    """Cylinder / cone / torus: the normals of a surface of revolution all meet its axis. cadfit's twist equation
    n.c + (x cross n).w = 0 over the samples has a rotation in its null space exactly then; its axis is (w, c).
    A narrow patch leaves several near-null directions, so each of the smallest few is tried and the meridian test
    below (a few 1e-5 of the part, on every sample) decides."""
    import cadfit
    A = cadfit.rows(P, N, origin, diag)
    res, V = cadfit.nullspace(A, len(P))
    for t in V[:3]:
        c, w = t[:3], t[3:]
        nw = float(np.linalg.norm(w))
        if nw < 1e-3:
            continue
        a = w / nw
        q = origin + diag * np.cross(w, c) / (nw * nw)
        fit = _meridian(P, a, q, tol)
        if fit is not None:
            return fit
    return None


def _meridian(P, a, q, tol):
    v = P - q
    z = v @ a
    rho = np.linalg.norm(v - np.outer(z, a), axis=1)
    r = float(rho.mean())
    if r > 1e-9 and np.abs(rho - r).max() <= tol:
        return {"kind": "CYL", "q": q, "a": a, "r": r}
    M = np.c_[np.ones_like(z), z]
    sol = np.linalg.lstsq(M, rho, rcond=None)[0]
    if np.abs(M @ sol - rho).max() <= tol and abs(sol[1]) > 1e-6:
        return {"kind": "CONE", "q": q, "a": a, "apex_z": float(-sol[0] / sol[1]), "tan": float(sol[1])}
    Mx = np.c_[2 * z, 2 * rho, np.ones_like(z)]
    s = np.linalg.lstsq(Mx, z * z + rho * rho, rcond=None)[0]
    zc, rc = float(s[0]), float(s[1])
    r2 = math.sqrt(max(float(s[2]) + zc * zc + rc * rc, 0.0))
    if r2 > 1e-9 and rc > 1e-9 and np.abs(np.sqrt((z - zc) ** 2 + (rho - rc) ** 2) - r2).max() <= tol:
        return {"kind": "TORUS", "q": q, "a": a, "zc": zc, "R": rc, "r2": r2}
    return None


def _arc(angles):
    """Start and span (radians) of the smallest arc covering the given angles on a circle."""
    s = np.sort(np.mod(angles, 2 * math.pi))
    gaps = np.diff(np.r_[s, s[0] + 2 * math.pi])
    k = int(np.argmax(gaps))
    start = float(s[(k + 1) % len(s)])
    return start, float(2 * math.pi - gaps[k])


def _basis(a):
    e1 = np.cross(a, [1.0, 0.0, 0.0] if abs(a[0]) < 0.9 else [0.0, 1.0, 0.0])
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(a, e1)


def recognize_face(model, index, diag, origin):
    """Carrier of a free-form-looking face if it is in fact analytic: fields named like stepir's face info
    (name, p, dirv, rad, rad2, ang, cc, ref, ur, vr, n, d, o), else None."""
    face = _face_of(model, index)
    s = samples(face, diag)
    if s is None:
        return None
    P, N = s
    tol = TOL_REL * diag
    fit = _fit_plane(P, N, tol) or _fit_sphere(P, N, tol) or _fit_revolution(P, N, tol, diag, origin)
    if fit is None:
        return None
    B = boundary_points(face)
    PB = np.vstack([P, B]) if len(B) else P
    centroid = P.mean(0)
    out = {}
    kind = fit["kind"]
    if kind == "PLANE":
        n = fit["n"]
        out.update(name="PLANE", n=n, d=fit["d"], o=n * fit["d"])
        return out
    if kind == "SPHERE":
        c = fit["c"]
        out.update(name="SPHERE", p=c, rad=fit["r"], dirv=np.array([0.0, 0.0, 1.0]))
        out["cc"] = 1 if float(np.mean(np.einsum("ij,ij->i", N, P - c))) > 0 else 0
        v = PB - c
        rr = np.linalg.norm(v, axis=1)
        lon = np.arctan2(v[:, 1], v[:, 0])
        lat = np.arcsin(np.clip(v[:, 2] / np.maximum(rr, 1e-12), -1, 1))
        out["ur"] = (0.0, _arc(lon)[1])
        out["vr"] = (float(lat.min()), float(lat.max()))
        return out
    q, a = fit["q"], fit["a"]
    e1, e2 = _basis(a)
    v = PB - q
    z = v @ a
    rho_vec = v - np.outer(z, a)
    ang = np.arctan2(rho_vec @ e2, rho_vec @ e1)
    span = _arc(ang)[1]
    radial = (P - q) - np.outer((P - q) @ a, a)
    radial_u = radial / np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-12)
    cm = centroid - q
    cm = cm - float(cm @ a) * a
    out["ur"] = (0.0, span)
    if kind == "CYL":
        out.update(name="CYL", p=q + a * float(z.min()), dirv=a, rad=fit["r"])
        out["vr"] = (0.0, float(z.max() - z.min()))
        out["cc"] = 1 if float(np.mean(np.einsum("ij,ij->i", N, radial_u))) > 0 else 0
    elif kind == "CONE":
        t = fit["tan"]
        d = a if t > 0 else -a                    # +d is the direction in which the radius grows from the apex
        apex = q + a * fit["apex_z"]
        h = (PB - apex) @ d
        h0 = float(h.min())
        alpha = math.atan(abs(t))
        out.update(name="CONE", p=apex + d * h0, dirv=d, rad=h0 * abs(t), ang=alpha)
        out["vr"] = (0.0, float((h.max() - h0) / math.cos(alpha)))
        out["cc"] = 1 if float(np.mean(np.einsum("ij,ij->i", N, radial_u))) > 0 else 0
    else:
        zc, R, r2 = fit["zc"], fit["R"], fit["r2"]
        out.update(name="TORUS", p=q + a * zc, dirv=a, rad=R, rad2=r2)
        zt = z - zc
        phi = np.arctan2(zt, np.linalg.norm(rho_vec, axis=1) - R)
        out["vr"] = (_arc(phi)[0], _arc(phi)[0] + _arc(phi)[1])
        tube = radial_u * (np.linalg.norm(radial, axis=1, keepdims=True) - R) + np.outer((P - q) @ a - zc, a)
        out["cc"] = 1 if float(np.mean(np.einsum("ij,ij->i", N, tube))) > 0 else 0
    rn = float(np.linalg.norm(cm))
    if rn > 0.05 * max(out.get("rad") or 1.0, 1e-9):
        out["ref"] = cm / rn
    return out


# ----------------------------------------------------------------------------------------------------- edges
def recognize_edge(model, rec, diag):
    """A B-spline boundary edge that is really a line or a circular arc: {"kind": "LINE"} or
    {"kind": "CIRCLE", "center", "radius", "axis", "closed"} with `axis` chosen so that the traversal start -> end
    of this occurrence runs counter-clockwise about it. None when the edge is a genuine curve."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS
    e = sdk_ocp.resolve(model, rec["entity_id"])
    c = BRepAdaptor_Curve(TopoDS.Edge_s(e[-1] if isinstance(e, tuple) else e))
    ts = np.linspace(c.FirstParameter(), c.LastParameter(), 17)
    pts = np.array([[q.X(), q.Y(), q.Z()] for q in (c.Value(float(t)) for t in ts)])
    start, end = np.asarray(rec["start"], float), np.asarray(rec["end"], float)
    if np.linalg.norm(pts[0] - start) > np.linalg.norm(pts[-1] - start):
        pts = pts[::-1]                                  # follow the occurrence's direction of travel
    tol = TOL_REL * diag
    closed = float(np.linalg.norm(start - end)) < 1e-7
    chord = pts[-1] - pts[0]
    L = float(np.linalg.norm(chord))
    if not closed and L > 1e-9:
        u = chord / L
        w = pts - pts[0]
        if np.abs(w - np.outer(w @ u, u)).max() <= tol:
            return {"kind": "LINE"}
    ctr = pts.mean(0)
    n0 = np.linalg.svd(pts - ctr)[2][2]
    if np.abs((pts - ctr) @ n0).max() > tol:
        return None
    e1, e2 = _basis(n0)
    xy = np.c_[(pts - ctr) @ e1, (pts - ctr) @ e2]
    M = np.c_[2 * xy, np.ones(len(xy))]
    s = np.linalg.lstsq(M, (xy ** 2).sum(1), rcond=None)[0]
    r = math.sqrt(max(float(s[2]) + s[0] ** 2 + s[1] ** 2, 0.0))
    if r < 1e-9 or np.abs(np.hypot(xy[:, 0] - s[0], xy[:, 1] - s[1]) - r).max() > tol:
        return None
    center = ctr + e1 * s[0] + e2 * s[1]
    d = pts - center
    turn = float(np.sum(np.cross(d[:-1], d[1:]) @ n0))
    return {"kind": "CIRCLE", "center": center, "radius": r, "axis": n0 if turn >= 0 else -n0, "closed": closed}


# ----------------------------------------------------------------------------------------------------- merging faces
ANALYTIC_NAMES = (("PLANE", "CYL", "CONE", "SPHERE", "TORUS"))
FREEFORM_NAMES = (("BSPL", "BEZ", "OTHER", "REV", "EXT"))

def _par(a, b):
    return 1.0 - abs(float(np.dot(a, b))) <= 1e-8


def _axis_dist(p, q, d):
    w = np.asarray(p, float) - np.asarray(q, float)
    return float(np.linalg.norm(w - float(w @ d) * d))


def _cone_apex(f):
    """The apex. With the radius growing along +d (the convention of the SDK and of recognize_face): radius(z) = rad + z tan(ang),
    so it vanishes at z = -rad / tan(ang) from p. Unique - two cones with mirrored apex candidates are different cones."""
    d = np.asarray(f["dirv"], float)
    d = d / np.linalg.norm(d)
    return np.asarray(f["p"], float) - (float(f["rad"]) / math.tan(f["ang"]) if f.get("ang") else 0.0) * d


def same_carrier(a, b, diag):
    """Two face infos lie on one and the same surface (not just the same kind of surface)."""
    if a["name"] != b["name"]:
        return False
    t, tol = a["name"], 2e-5 * diag
    if t == "PLANE":
        return float(a["n"] @ b["n"]) >= 1 - 1e-8 and abs(a["d"] - b["d"]) <= tol
    if a.get("cc") != b.get("cc"):
        return False
    if t == "SPHERE":
        return abs(a["rad"] - b["rad"]) <= tol and float(np.linalg.norm(a["p"] - b["p"])) <= tol
    da, db = np.asarray(a["dirv"], float), np.asarray(b["dirv"], float)
    da, db = da / np.linalg.norm(da), db / np.linalg.norm(db)
    if not _par(da, db):
        return False
    if t == "CYL":
        return abs(a["rad"] - b["rad"]) <= tol and _axis_dist(b["p"], a["p"], da) <= tol
    if t == "TORUS":
        return (abs(a["rad"] - b["rad"]) <= tol and abs(a["rad2"] - b["rad2"]) <= tol
                and float(np.linalg.norm((a["p"] - b["p"]) - float((a["p"] - b["p"]) @ da) * da)) <= tol
                and abs(float((a["p"] - b["p"]) @ da)) <= tol)
    if t == "CONE":
        if abs(a["ang"] - b["ang"]) > 1e-4:
            return False
        return float(np.linalg.norm(_cone_apex(a) - _cone_apex(b))) <= 5 * tol
    return False


def _edge_points(model, rec, n=9):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS
    e = sdk_ocp.resolve(model, rec["entity_id"])
    c = BRepAdaptor_Curve(TopoDS.Edge_s(e[-1] if isinstance(e, tuple) else e))
    return np.array([[q.X(), q.Y(), q.Z()] for q in (c.Value(float(t)) for t in np.linspace(c.FirstParameter(), c.LastParameter(), n))])


def union_boundary(model, members, diag):
    """Boundary loops of the union of adjacent faces, as inspect_face_boundaries-style loops ({"edges": [...]}), outer first.

    An edge that two members share (or that one member meets twice, a seam) is interior and disappears; the remaining
    directed edges chain end-to-start into loops. None when they do not close, so the caller can refuse to merge."""
    from simplecadapi.inspect import brep
    occ, count = [], {}
    for i in members:
        b = brep.inspect_face_boundaries_rdescriptor(model_or_path=model, face_id=f"face:{i}", compact=True)
        for lp in [b["outer"]] + list(b.get("inner", [])):
            for rec in lp["edges"]:
                occ.append(rec)
                count[rec["entity_id"]] = count.get(rec["entity_id"], 0) + 1
    keep = [r for r in occ if count[r["entity_id"]] == 1]
    tol = 1e-5 * diag
    unused = list(range(len(keep)))
    loops = []
    while unused:
        first = unused.pop(0)
        loop = [keep[first]]
        while float(np.linalg.norm(np.asarray(loop[-1]["end"], float) - np.asarray(loop[0]["start"], float))) > tol:
            cur = np.asarray(loop[-1]["end"], float)
            best, bd = None, tol
            for u in unused:
                dd = float(np.linalg.norm(np.asarray(keep[u]["start"], float) - cur))
                if dd <= bd:
                    best, bd = u, dd
            if best is None:
                return None
            unused.remove(best)
            loop.append(keep[best])
        loops.append(loop)
    if not loops:
        return None

    def size(loop):
        P = np.vstack([_edge_points(model, r) for r in loop])
        return float(np.linalg.norm(P.max(0) - P.min(0)))

    loops.sort(key=lambda lp: -size(lp))
    return [{"edges": lp} for lp in loops]


def merge_groups(model, infos, diag):
    """Merge adjacent faces that lie on one surface into a single face info (in place).

    The representative keeps the lowest face index and absorbs the others, which are marked {"dead": rep}. Returns the
    number of faces absorbed."""
    n = len(infos)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a in range(n):
        ia = infos[a]
        if ia["name"] not in ANALYTIC_NAMES + FREEFORM_NAMES:
            continue
        for b in ia["adj"]:
            ib = infos[b]
            if b <= a or find(a) == find(b):
                continue
            if ia["name"] in FREEFORM_NAMES:
                same = ib["name"] in FREEFORM_NAMES and smooth_across(model, a, b, diag)
            else:
                same = same_carrier(ia, ib, diag)
            if same:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
    groups = {}
    for k in range(n):
        groups.setdefault(find(k), []).append(k)
    absorbed = 0
    for rep, members in groups.items():
        if len(members) < 2:
            continue
        loops = union_boundary(model, members, diag)
        if loops is None:
            continue
        r0 = infos[rep]
        area = sum(infos[m]["area"] for m in members)
        adj = sorted({q for m in members for q in infos[m]["adj"]} - set(members))
        r0["loops_raw"] = loops
        if r0["name"] in FREEFORM_NAMES:
            bbs = [np.asarray(infos[m]["bb"], float) for m in members if infos[m].get("bb")]
            if bbs:
                r0["bb"] = [[round(float(x), 4) for x in np.min([b[0] for b in bbs], axis=0)],
                            [round(float(x), 4) for x in np.max([b[1] for b in bbs], axis=0)]]
        elif r0["name"] != "PLANE":
            ur, vr = merged_extents(model, r0, members, diag)
            r0["ur"], r0["vr"] = ur, vr
            if "ref" in r0 or any("ref" in infos[m] for m in members):
                cs = sum(np.asarray(infos[m]["g"]["centroid"], float) * infos[m]["area"] for m in members) / area
                q = np.asarray(r0["p"], float)
                d0 = np.asarray(r0["dirv"], float) / np.linalg.norm(r0["dirv"])
                v = cs - q
                v = v - float(v @ d0) * d0
                nv = float(np.linalg.norm(v))
                if nv > 0.05 * float(r0.get("rad") or 1.0):
                    r0["ref"] = v / nv
                else:
                    r0.pop("ref", None)
        r0["area"], r0["adj"], r0["members"] = area, adj, members
        for m in members:
            if m != rep:
                infos[m]["dead"] = rep
                absorbed += 1
    return absorbed


# ----------------------------------------------------------------------------------------------------- free-form faces
def _surface_state(face, pt):
    """Unit normal (outward), mean and Gaussian curvature of a face's surface at the 3D point nearest to `pt`."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepLProp import BRepLProp_SLProps
    from OCP.gp import gp_Pnt
    from OCP.ShapeAnalysis import ShapeAnalysis_Surface
    uv = ShapeAnalysis_Surface(BRep_Tool.Surface_s(face)).ValueOfUV(gp_Pnt(*pt), 1e-7)
    pr = BRepLProp_SLProps(BRepAdaptor_Surface(face), uv.X(), uv.Y(), 2, 1e-9)
    if not (pr.IsNormalDefined() and pr.IsCurvatureDefined()):
        return None
    n = pr.Normal()
    flip = -1.0 if face.Orientation().name.endswith("REVERSED") else 1.0
    return flip * np.array([n.X(), n.Y(), n.Z()]), pr.MeanCurvature(), pr.GaussianCurvature()


def smooth_across(model, a, b, diag):
    """Are free-form faces a and b one surface cut in two? Along every edge they share, the surface must continue with the
    same normal and the same curvature (G2) - a crease or a blend between two different surfaces cannot do that."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS
    ea = set(model.describe_entity(f"face:{a}")["adjacency"]["edges"])
    eb = set(model.describe_entity(f"face:{b}")["adjacency"]["edges"])
    shared = sorted(ea & eb)
    if not shared:
        return False
    fa, fb = _face_of(model, a), _face_of(model, b)
    for eid in shared:
        e = sdk_ocp.resolve(model, eid)
        c = BRepAdaptor_Curve(TopoDS.Edge_s(e[-1] if isinstance(e, tuple) else e))
        for t in np.linspace(c.FirstParameter(), c.LastParameter(), 7)[1:-1]:
            q = c.Value(float(t))
            sa, sb = _surface_state(fa, (q.X(), q.Y(), q.Z())), _surface_state(fb, (q.X(), q.Y(), q.Z()))
            if sa is None or sb is None:
                return False
            if float(sa[0] @ sb[0]) < 1 - 1e-7:
                return False
            k = 1.0 / max(diag * 1e-3, 1e-9)
            if abs(sa[1] - sb[1]) > 1e-4 * (1 + abs(sa[1])) or abs(sa[2] - sb[2]) > 1e-4 * (1 + abs(sa[2])) + 1e-9 * k:
                return False
    return True


def merged_extents(model, info, members, diag):
    """u/v ranges of a merged analytic face, measured on all members in the representative's own frame (a member may
    carry the mirror-image axis or angle convention, so ranges cannot simply be combined)."""
    pts = []
    for m in members:
        face = _face_of(model, m)
        s = samples(face, diag)
        if s is not None:
            pts.append(s[0])
        b = boundary_points(face)
        if len(b):
            pts.append(b)
    P = np.vstack(pts)
    name = info["name"]
    if name == "SPHERE":
        v = P - np.asarray(info["p"], float)
        rr = np.linalg.norm(v, axis=1)
        lon = np.arctan2(v[:, 1], v[:, 0])
        lat = np.arcsin(np.clip(v[:, 2] / np.maximum(rr, 1e-12), -1, 1))
        return (0.0, _arc(lon)[1]), (float(lat.min()), float(lat.max()))
    a = np.asarray(info["dirv"], float)
    a = a / np.linalg.norm(a)
    q = np.asarray(info["p"], float)
    e1, e2 = _basis(a)
    v = P - q
    z = v @ a
    rho_vec = v - np.outer(z, a)
    span = _arc(np.arctan2(rho_vec @ e2, rho_vec @ e1))[1]
    if name == "CYL":
        return (0.0, span), (float(z.min()), float(z.max()))
    if name == "CONE":
        alpha = info["ang"]
        return (0.0, span), (float(z.min() / math.cos(alpha)), float(z.max() / math.cos(alpha)))
    phi = np.arctan2(z, np.linalg.norm(rho_vec, axis=1) - float(info["rad"]))
    start, vspan = _arc(phi)
    return (0.0, span), (start, start + vspan)


# ----------------------------------------------------------------------------------------------------- loft or sweep
def section_congruence(model, index, K=6, M=32):
    """How far the iso-curve families of a B-spline face are from being rigid copies of one curve.

    A swept surface is S(s, t) = M(t) P(s): along the rail every iso-curve is the same profile moved rigidly, so the
    pairwise-distance matrix of points on it (rigid-invariant) does not change from one iso-curve to the next. A loft
    changes shape between its sections. Returns the smaller of the two families' relative changes (None if the face is not
    a B-spline surface); ~1e-6 for a sweep, 1e-2 and up for a loft."""
    from OCP.BRep import BRep_Tool
    from OCP.Geom import Geom_BSplineSurface
    S = sdk_ocp.surface(_face_of(model, index))
    if not isinstance(S, Geom_BSplineSurface):
        return None
    u1, u2, v1, v2 = S.Bounds()
    best = None
    for family in ("u", "v"):
        mats = []
        for k in range(K):
            if family == "u":
                c, (a, b) = S.UIso(u1 + (u2 - u1) * (k + 0.5) / K), (v1, v2)
            else:
                c, (a, b) = S.VIso(v1 + (v2 - v1) * (k + 0.5) / K), (u1, u2)
            P = np.array([[q.X(), q.Y(), q.Z()] for q in (c.Value(float(x)) for x in np.linspace(a, b, M))])
            mats.append(np.linalg.norm(P[:, None] - P[None], axis=2))
        err = max(float(np.abs(m - mats[0]).max()) for m in mats[1:]) / max(float(mats[0].max()), 1e-12)
        best = err if best is None else min(best, err)
    return best


# ----------------------------------------------------------------------------------------------------- swept carriers
MAX_GEN_POLES = 24       # longer generators go to the on-demand query, the base IR gets a pole count


def _curve_def(c):
    """Exact B-spline definition of a curve (converted when it is not already a B-spline)."""
    from OCP.Geom import Geom_BSplineCurve
    from OCP.GeomConvert import GeomConvert
    b = c if isinstance(c, Geom_BSplineCurve) else GeomConvert.CurveToBSplineCurve_s(c)
    poles = np.array([[b.Pole(k).X(), b.Pole(k).Y(), b.Pole(k).Z()] for k in range(1, b.NbPoles() + 1)])
    out = {"deg": b.Degree(), "knots": [float(b.Knot(k)) for k in range(1, b.NbKnots() + 1)],
           "mult": [int(b.Multiplicity(k)) for k in range(1, b.NbKnots() + 1)]}
    if b.IsRational():
        out["w"] = [float(b.Weight(k)) for k in range(1, b.NbPoles() + 1)]
    if b.IsPeriodic():
        out["periodic"] = True
    return poles, out


def swept_carrier(model, index, geometry, diag):
    """A surface of revolution or of linear extrusion, with its exact generating curve.

    REV: the generator lies in a plane through the axis, so its poles are written as (z, r) in that plane - the very sketch
    revolve_rsolid needs. EXT: the generator's 3D poles and the extrusion direction. Returns face-info fields or None."""
    from OCP.BRep import BRep_Tool
    t = geometry["type"]
    S = sdk_ocp.surface(_face_of(model, index))
    if not hasattr(S, "BasisCurve"):
        return None
    P, cdef = _curve_def(S.BasisCurve())
    par = geometry["parameters"]
    if t == "REVOLUTION":
        q = np.asarray(par["axis"]["point"], float)
        a = np.asarray(par["axis"]["direction"], float)
        a = a / np.linalg.norm(a)
        v = P - q
        z = v @ a
        radial = v - np.outer(z, a)
        k = int(np.argmax(np.linalg.norm(radial, axis=1)))
        e = radial[k] / (np.linalg.norm(radial[k]) or 1.0)
        off = float(np.abs(radial @ np.cross(a, e)).max())
        out = {"name": "REV", "p": q, "dirv": a, "rad": None, "e": e}
        span = float(par["u_range"][1] - par["u_range"][0])
        out["ur"] = (0.0, span)
        gen = dict(cdef)
        if off <= 1e-6 * diag:
            gen["zr"] = [[float(x), float(y)] for x, y in zip(z, radial @ e)]
        else:
            gen["poles"] = P.tolist()
        gen["t"] = [float(par["v_range"][0]), float(par["v_range"][1])]
        out["gen"] = gen
        return out
    if t == "EXTRUSION":
        dvec = np.asarray(par["direction"], float)
        dvec = dvec / np.linalg.norm(dvec)
        gen = dict(cdef)
        gen["poles"] = P.tolist()
        gen["t"] = [float(par["u_range"][0]), float(par["u_range"][1])]
        return {"name": "EXT", "dirv": dvec, "p": P[0], "rad": None, "gen": gen,
                "ext_v": (float(par["v_range"][0]), float(par["v_range"][1]))}
    return None


def ruled_extrusion(model, index, geometry, diag):
    """A B-spline face that is a straight extrusion of one curve: degree 1 with two pole rows in one parameter direction,
    the second row the first moved by one constant vector, equal weights. That is exactly a surface of linear extrusion
    (text and logo walls extruded from spline outlines are stored this way), so it gets the same EXT fields as
    swept_carrier: the exact generating curve, the direction, and the extrusion range. Returns face-info fields or None."""
    from OCP.Geom import Geom_BSplineSurface
    S = sdk_ocp.surface(_face_of(model, index))
    if not isinstance(S, Geom_BSplineSurface):
        return None
    nu, nv = S.NbUPoles(), S.NbVPoles()
    P = np.array([[[S.Pole(i, j).X(), S.Pole(i, j).Y(), S.Pole(i, j).Z()] for j in range(1, nv + 1)] for i in range(1, nu + 1)])
    W = np.array([[S.Weight(i, j) for j in range(1, nv + 1)] for i in range(1, nu + 1)])
    par = geometry["parameters"]
    for lin in ("v", "u"):
        if lin == "v":
            if S.VDegree() != 1 or nv != 2 or S.IsVPeriodic():
                continue
            rows, w = (P[:, 0], P[:, 1]), (W[:, 0], W[:, 1])
            deg, periodic = S.UDegree(), S.IsUPeriodic()
            knots = [(float(S.UKnot(k)), int(S.UMultiplicity(k))) for k in range(1, S.NbUKnots() + 1)]
            a0, a1 = float(S.VKnot(1)), float(S.VKnot(S.NbVKnots()))
            crange, lrange = par["u_range"], par["v_range"]
        else:
            if S.UDegree() != 1 or nu != 2 or S.IsUPeriodic():
                continue
            rows, w = (P[0], P[1]), (W[0], W[1])
            deg, periodic = S.VDegree(), S.IsVPeriodic()
            knots = [(float(S.VKnot(k)), int(S.VMultiplicity(k))) for k in range(1, S.NbVKnots() + 1)]
            a0, a1 = float(S.UKnot(1)), float(S.UKnot(S.NbUKnots()))
            crange, lrange = par["v_range"], par["u_range"]
        T = rows[1] - rows[0]
        t = T.mean(0)
        L = float(np.linalg.norm(t))
        if L <= 1e-7 * diag or float(np.abs(T - t).max()) > TOL_REL * diag or float(np.abs(w[0] - w[1]).max()) > 1e-9:
            continue
        s = lambda x: (float(x) - a0) / (a1 - a0) * L
        gen = {"deg": deg, "knots": [k for k, _ in knots], "mult": [m for _, m in knots], "poles": rows[0].tolist(),
               "t": [float(crange[0]), float(crange[1])]}
        if float(np.abs(w[0] - 1.0).max()) > 1e-12:
            gen["w"] = [float(x) for x in w[0]]
        if periodic:
            gen["periodic"] = True
        return {"name": "EXT", "dirv": t / L, "p": rows[0][0], "rad": None, "gen": gen, "ext_v": (s(lrange[0]), s(lrange[1]))}
    return None


MAX_SEG_POLES = 64       # planar loop splines with more poles stay in the short ["S", ...] form only (exact net: stepir_query face)


def edge_bspline(model, rec):
    """Exact B-spline of an edge occurrence, oriented from its start to its end: (poles Nx3, deg, knots normalised to
    [0, 1], mult, weights or None), or None when it has more than MAX_SEG_POLES poles."""
    from OCP.BRep import BRep_Tool
    from OCP.Geom import Geom_BSplineCurve, Geom_TrimmedCurve
    from OCP.GeomConvert import GeomConvert
    _, _, e = sdk_ocp.resolve(model, rec["entity_id"])
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    c = BRep_Tool.Curve_s(e, 0.0, 0.0)         # with the edge's location applied
    if c is None:
        return None
    ad = BRepAdaptor_Curve(e)
    f, l = ad.FirstParameter(), ad.LastParameter()
    b = c if isinstance(c, Geom_BSplineCurve) and not c.IsPeriodic() and abs(c.FirstParameter() - f) < 1e-12 \
        and abs(c.LastParameter() - l) < 1e-12 else GeomConvert.CurveToBSplineCurve_s(Geom_TrimmedCurve(c, f, l))
    n = b.NbPoles()
    if n > MAX_SEG_POLES:
        return None
    P = np.array([[b.Pole(k).X(), b.Pole(k).Y(), b.Pole(k).Z()] for k in range(1, n + 1)])
    w = np.array([b.Weight(k) for k in range(1, n + 1)]) if b.IsRational() else None
    kn = np.array([b.Knot(k) for k in range(1, b.NbKnots() + 1)], float)
    mu = [int(b.Multiplicity(k)) for k in range(1, b.NbKnots() + 1)]
    kn = (kn - kn[0]) / ((kn[-1] - kn[0]) or 1.0)
    start = np.asarray(rec["start"], float)
    if float(np.linalg.norm(P[-1] - start)) < float(np.linalg.norm(P[0] - start)):     # reversed occurrence
        P, kn, mu = P[::-1], (1.0 - kn)[::-1], mu[::-1]
        w = w[::-1] if w is not None else None
    return P, b.Degree(), kn.tolist(), mu, (w.tolist() if w is not None else None)
