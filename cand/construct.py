#!/usr/bin/env python3
"""Construction parameters of free-form face groups: what a modeller needs to rebuild a sweep or a loft, not just its name.

  sweep: the rail (points the profile's centroid passes through, in order) and the profile (the plane section at the rail's
         start). A swept surface is S(s, t) = M(t) P(s): every section iso-curve is a rigid copy of the first, so the rigid
         transforms M(t) between successive sections (Kabsch on corresponding samples) carry the profile along the rail.
  loft:  the sections the surface passes through: plane sections at the two ends and at the interior knots of the lofting
         direction (an interpolating loft through N sections puts a knot at every section).

Sections are plane sections of the whole face group (a profile is usually split over several faces), chained into closed
loops and summarised as a circle or a simplified polygon in a local frame; the full chains are available on demand.
"""
from __future__ import annotations

import math

import numpy as np

import geomnorm
import sdk_ocp

K_RAIL = 13           # rail stations
M_SEC = 48            # samples per iso-curve
MAX_POLY = 14         # vertices of a simplified section kept in the base IR
MAX_LOFT_SECTIONS = 8


def _face(model, i):
    return geomnorm._face_of(model, i)


def _uv_bounds(face):
    from OCP.BRepTools import BRepTools
    return BRepTools.UVBounds_s(face)


def iso_points(face, family, params, m=M_SEC):
    """Points on iso-curves of the face's surface inside its UV box: family 'u' = curves of constant u (running along v)."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    ad = BRepAdaptor_Surface(face)
    u0, u1, v0, v1 = _uv_bounds(face)
    out = []
    for t in params:
        if family == "u":
            pts = [ad.Value(t, v0 + (v1 - v0) * k / (m - 1)) for k in range(m)]
        else:
            pts = [ad.Value(u0 + (u1 - u0) * k / (m - 1), t) for k in range(m)]
        out.append(np.array([[p.X(), p.Y(), p.Z()] for p in pts]))
    return out


def _family_stats(face, family, k=7):
    u0, u1, v0, v1 = _uv_bounds(face)
    a, b = (u0, u1) if family == "u" else (v0, v1)
    curves = iso_points(face, family, [a + (b - a) * j / (k - 1) for j in range(k)])
    D = [np.linalg.norm(c[:, None] - c[None], axis=2) for c in curves]
    scale = max(float(D[0].max()), 1e-12)
    congr = max(float(np.abs(d - D[0]).max()) for d in D[1:]) / scale
    plan = 0.0
    for c in curves:
        cc = c - c.mean(0)
        plan = max(plan, float(np.linalg.svd(cc, compute_uv=False)[-1]) / scale)
    return congr, plan


def section_normal(C, tangent, diag):
    """Normal of the plane a section curve lies in. A curve that is (nearly) a straight line - one side of a polygonal
    profile - does not fix its plane; the plane is then the one through the line that is most nearly perpendicular to the
    rail tangent, and a non-planar curve also falls back to the tangent."""
    t = np.asarray(tangent, float)
    t = t / (np.linalg.norm(t) or 1.0)
    cc = C - C.mean(0)
    _, sv, vt = np.linalg.svd(cc, full_matrices=False)
    if sv[2] > 1e-3 * diag:                       # not planar
        return t
    if sv[1] <= 1e-3 * diag:                      # a straight line
        u = vt[0]
        n = t - float(t @ u) * u
        return n / (np.linalg.norm(n) or 1.0)
    n = vt[2]
    return n if float(n @ t) >= 0 else -n


def loft_section_family(face, diag, k=7):
    """Which iso family of a lofted face are its sections. In order: the family whose curves close (a whole section on one
    face); else the family of straight segments when the other is curved (the sides of polygonal sections - a straight
    curve has no plane of its own); else the planar family whose planes stay parallel (sections of a loft are parallel or
    nearly, while planar generatrices, e.g. through coaxial circles, lie in planes turning about the axis); ties go to the
    curves of constant v, OCC's loft convention (u runs along the section)."""
    u0, u1, v0, v1 = _uv_bounds(face)
    info = {}
    for fam, (a, b) in (("u", (u0, u1)), ("v", (v0, v1))):
        curves = iso_points(face, fam, [a + (b - a) * j / (k - 1) for j in range(k)])
        closed = all(np.linalg.norm(c[0] - c[-1]) <= 1e-4 * diag for c in curves)
        ns, plan, straight = [], 0.0, True
        for c in curves:
            _, sv, vt = np.linalg.svd(c - c.mean(0), full_matrices=False)
            plan = max(plan, float(sv[2]) / max(float(sv[0]), 1e-12))
            if sv[1] > 1e-6 * diag:
                straight = False
                ns.append(vt[2])
        spread = max((1 - abs(float(ns[0] @ n)) for n in ns[1:]), default=0.0) if ns else 1.0
        info[fam] = (closed, plan, spread, straight)
    if info["u"][0] != info["v"][0]:
        return "u" if info["u"][0] else "v"
    if info["u"][3] != info["v"][3]:
        return "u" if info["u"][3] else "v"
    pu, pv = info["u"][1] < 1e-3, info["v"][1] < 1e-3
    if pu and pv and abs(info["u"][2] - info["v"][2]) > 1e-6:
        return "u" if info["u"][2] < info["v"][2] else "v"
    if pu != pv:
        return "u" if pu else "v"
    return "v"


def kabsch(P, Q):
    """R, T with Q ~ R P + T."""
    cp, cq = P.mean(0), Q.mean(0)
    H = (P - cp).T @ (Q - cq)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T)) or 1.0
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    return R, cq - R @ cp


# ----------------------------------------------------------------------------------------------------- plane sections
def section_loops(model, faces, origin, normal, diag, per_edge=16):
    """Closed loops (ordered 3D points) where the plane cuts the given faces."""
    from OCP.BRep import BRep_Builder
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.gp import gp_Dir, gp_Pln, gp_Pnt
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS, TopoDS_Compound
    comp = TopoDS_Compound()
    bb = BRep_Builder()
    bb.MakeCompound(comp)
    for i in faces:
        bb.Add(comp, _face(model, i))
    sec = BRepAlgoAPI_Section(comp, gp_Pln(gp_Pnt(*map(float, origin)), gp_Dir(*map(float, normal))), True)
    if not sec.IsDone():
        return []
    edges = []
    ex = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
    while ex.More():
        c = BRepAdaptor_Curve(TopoDS.Edge_s(ex.Current()))
        a, b = c.FirstParameter(), c.LastParameter()
        pts = np.array([[c.Value(a + (b - a) * k / (per_edge - 1)).X(), c.Value(a + (b - a) * k / (per_edge - 1)).Y(),
                         c.Value(a + (b - a) * k / (per_edge - 1)).Z()] for k in range(per_edge)])
        edges.append(pts)
        ex.Next()
    tol = 1e-3 * diag
    loops, used = [], [False] * len(edges)
    for s in range(len(edges)):
        if used[s]:
            continue
        used[s] = True
        chain = [edges[s]]
        while np.linalg.norm(chain[-1][-1] - chain[0][0]) > tol:
            end = chain[-1][-1]
            nxt = None
            for j, e in enumerate(edges):
                if used[j]:
                    continue
                if np.linalg.norm(e[0] - end) <= tol:
                    nxt = e
                elif np.linalg.norm(e[-1] - end) <= tol:
                    nxt = e[::-1]
                if nxt is not None:
                    used[j] = True
                    break
            if nxt is None:
                break
            chain.append(nxt)
        if np.linalg.norm(chain[-1][-1] - chain[0][0]) <= tol and sum(len(c) - 1 for c in chain) >= 3:
            loops.append(chain)
    return loops


def _frame(n):
    import stepir
    x, y = stepir.canon_frame(np.asarray(n, float))
    return np.asarray(x, float), np.asarray(y, float)


def _poly_area_centroid(P2):
    x, y = P2[:, 0], P2[:, 1]
    xs, ys = np.roll(x, -1), np.roll(y, -1)
    cr = x * ys - xs * y
    A = cr.sum() / 2.0
    if abs(A) < 1e-12:
        return 0.0, P2.mean(0)
    cx = ((x + xs) * cr).sum() / (6 * A)
    cy = ((y + ys) * cr).sum() / (6 * A)
    return A, np.array([cx, cy])


def _simplify(P2, tol):
    """Douglas-Peucker on a closed polygon."""
    def dp(pts):
        if len(pts) < 3:
            return pts
        a, b = pts[0], pts[-1]
        ab = b - a
        L = float(np.linalg.norm(ab))
        d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / L if L > 1e-12 else np.linalg.norm(pts - a, axis=1)
        k = int(np.argmax(d))
        if d[k] <= tol:
            return np.vstack([a, b])
        return np.vstack([dp(pts[:k + 1])[:-1], dp(pts[k:])])
    far = int(np.argmax(np.linalg.norm(P2 - P2[0], axis=1)))
    ring = np.vstack([P2, P2[:1]])
    out = np.vstack([dp(ring[:far + 1])[:-1], dp(ring[far:])[:-1]])
    return out                                        # starts at P2[0], keeps its orientation


N_SPLINE = 16


def max_turn(P):
    """Largest turning angle between consecutive chords of a closed polyline (corners show up as large turns)."""
    d = np.roll(P, -1, axis=0) - P
    d = d[np.linalg.norm(d, axis=1) > 1e-12]
    a = np.arctan2(d[:, 1], d[:, 0])
    t = np.abs((np.roll(a, -1) - a + np.pi) % (2 * np.pi) - np.pi)
    return float(t.max()) if len(t) else 0.0


def resample(P, n):
    ring = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(ring, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    targets = np.linspace(0, s[-1], n, endpoint=False)
    return np.c_[np.interp(targets, s, ring[:, 0]), np.interp(targets, s, ring[:, 1])]


def _pts(loop):
    """All points of a loop given as a list of pieces (each piece's last point is the next piece's first)."""
    if isinstance(loop, np.ndarray):
        return loop
    return np.vstack([np.asarray(p)[:-1] for p in loop])


def _seg2d(P2, tol):
    """A 2D piece as a line ["L", x, y] or an arc ["A", cx, cy, x, y, s] (s=+1 counter-clockwise), else None."""
    a, b = P2[0], P2[-1]
    ab = b - a
    L = float(np.linalg.norm(ab))
    if L > tol:
        d = np.abs(ab[0] * (P2[:, 1] - a[1]) - ab[1] * (P2[:, 0] - a[0])) / L
        if d.max() <= tol:
            return ["L", b[0], b[1]]
    if len(P2) >= 4:
        M = np.c_[2 * P2, np.ones(len(P2))]
        sol = np.linalg.lstsq(M, (P2 ** 2).sum(1), rcond=None)[0]
        c = sol[:2]
        R = math.sqrt(max(float(sol[2]) + float(c @ c), 0.0))
        if R > tol and np.abs(np.linalg.norm(P2 - c, axis=1) - R).max() <= tol:
            v = P2 - c
            turn = float(np.sum(v[:-1, 0] * v[1:, 1] - v[:-1, 1] * v[1:, 0]))
            return ["A", c[0], c[1], b[0], b[1], 1 if turn > 0 else -1]
    return None


def _encode_chain(pieces2d, tol):
    """The loop as the same chain encoding planar faces use, when every piece is a line or a circular arc."""
    segs = []
    for P2 in pieces2d:
        sg = _seg2d(P2, tol)
        if sg is None:
            return None
        segs.append(sg)
    r3 = lambda v: round(float(v), 4)
    out = []
    for sg in segs:
        out.append([sg[0]] + [r3(v) for v in sg[1:-1]] + [sg[-1]] if sg[0] == "A" else ["L", r3(sg[1]), r3(sg[2])])
    return {"s": [r3(pieces2d[0][0][0]), r3(pieces2d[0][0][1])], "e": out}


def _bspline2d(curve, o, x, y, n, diag):
    """Exact B-spline definition of a planar closed curve, poles in the section frame."""
    from OCP.Geom import Geom_BSplineCurve
    from OCP.GeomConvert import GeomConvert
    b = curve if isinstance(curve, Geom_BSplineCurve) else GeomConvert.CurveToBSplineCurve_s(curve)
    P = np.array([[b.Pole(k).X(), b.Pole(k).Y(), b.Pole(k).Z()] for k in range(1, b.NbPoles() + 1)]) - o
    if np.abs(P @ n).max() > 1e-6 * diag:
        return None
    out = {"deg": b.Degree(), "poles": [[round(float(p @ x), 4), round(float(p @ y), 4)] for p in P],
           "knots": [round(float(b.Knot(k)), 6) for k in range(1, b.NbKnots() + 1)],
           "mult": [int(b.Multiplicity(k)) for k in range(1, b.NbKnots() + 1)]}
    if b.IsRational():
        out["w"] = [round(float(b.Weight(k)), 6) for k in range(1, b.NbPoles() + 1)]
    if b.IsPeriodic():
        out["periodic"] = 1
    return out


MAX_BSPLINE_POLES = 40


def summarize_section(loops, normal, diag, exact=None):
    """Section summary in its own plane: centroid `o`, normal `n`, area, and the outer loop, in order of preference:
    `circle` (radius); `loop` - the planar-face chain encoding, when every piece is a line or an arc; `bspline` - the exact
    curve when the section is one closed iso-curve of a single face (`exact`); `poly` (simplified polygon, corners kept);
    `through` (points a periodic interpolating spline passes through, evenly spaced by arc length). Holes are counted."""
    if not loops:
        return None
    n = np.asarray(normal, float)
    n = n / np.linalg.norm(n)
    x, y = _frame(n)
    best = None
    for L in loops:
        P = _pts(L)
        P2 = np.c_[(P - P.mean(0)) @ x, (P - P.mean(0)) @ y]
        A, _ = _poly_area_centroid(P2)
        if best is None or abs(A) > abs(best[1]):
            best = (L, A)
    L, A = best
    P = _pts(L)
    o0 = P.mean(0)
    P2 = np.c_[(P - o0) @ x, (P - o0) @ y]
    _, c2 = _poly_area_centroid(P2)
    o = o0 + x * c2[0] + y * c2[1]
    out = {"o": [round(float(v), 4) for v in o], "n": [round(float(v), 4) for v in n], "area": round(abs(float(A)), 3)}
    ccw = _poly_area_centroid(P2 - c2)[0] >= 0
    Q = P2 - c2
    if not ccw:
        Q = Q[::-1]
    rr = np.linalg.norm(Q, axis=1)
    tol = 2e-4 * diag
    if rr.mean() > 0 and np.abs(rr - rr.mean()).max() <= tol:
        out["circle"] = round(float(rr.mean()), 4)
    else:
        out["x"] = [round(float(v), 4) for v in x]
        pieces = [np.c_[(np.asarray(p) - o) @ x, (np.asarray(p) - o) @ y] for p in (L if isinstance(L, list) else [L])]
        if not ccw:
            pieces = [p[::-1] for p in pieces[::-1]]
        start = int(np.argmax([p[0][0] - 1e-9 * p[0][1] for p in pieces]))   # one seam rule for all sections
        pieces = pieces[start:] + pieces[:start]
        enc = _encode_chain(pieces, tol) if isinstance(L, list) and len(pieces) <= 4 * MAX_POLY else None
        if enc is not None:
            out["loop"] = enc
        else:
            bs = _bspline2d(exact, o, x, y, n, diag) if exact is not None else None
            if bs is not None and len(bs["poles"]) <= MAX_BSPLINE_POLES:
                if not ccw:
                    out["reversed"] = 1                     # the exact curve runs clockwise about n
                out["bspline"] = bs
            else:
                Q = np.roll(Q, -int(np.argmax(Q[:, 0] - 1e-9 * Q[:, 1])), axis=0)
                simp = _simplify(Q, 1e-3 * diag)
                if len(simp) <= MAX_POLY:
                    out["poly"] = [[round(float(a), 3), round(float(b), 3)] for a, b in simp]
                elif max_turn(Q) < math.radians(25):
                    out["through"] = [[round(float(a), 3), round(float(b), 3)] for a, b in resample(Q, N_SPLINE)]
                else:
                    simp = _simplify(Q, 2e-3 * diag)
                    if len(simp) <= 2 * MAX_POLY:
                        out["poly"] = [[round(float(a), 3), round(float(b), 3)] for a, b in simp]
                    else:
                        out.pop("x")
                        out["bbox"] = [round(float(Q[:, 0].max() - Q[:, 0].min()), 3), round(float(Q[:, 1].max() - Q[:, 1].min()), 3)]
    if len(loops) > 1:
        out["holes"] = len(loops) - 1
    return out


# ----------------------------------------------------------------------------------------------------- groups
def components(ids, adjacency):
    ids = set(ids)
    seen, out = set(), []
    for s in sorted(ids):
        if s in seen:
            continue
        stack, comp = [s], []
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            comp.append(k)
            stack += [q for q in adjacency.get(k, ()) if q in ids and q not in seen]
        out.append(sorted(comp))
    return out


def chain(pieces, diag):
    """Ordered closed loops from polyline pieces that meet end to start (either orientation)."""
    tol = 1e-3 * diag
    pieces = [np.asarray(p, float) for p in pieces if len(p) >= 2]
    used = [False] * len(pieces)
    loops = []
    for s0 in range(len(pieces)):
        if used[s0]:
            continue
        used[s0] = True
        ch = [pieces[s0]]
        while np.linalg.norm(ch[-1][-1] - ch[0][0]) > tol:
            end, nxt = ch[-1][-1], None
            for j, e in enumerate(pieces):
                if used[j]:
                    continue
                if np.linalg.norm(e[0] - end) <= tol:
                    nxt = e
                elif np.linalg.norm(e[-1] - end) <= tol:
                    nxt = e[::-1]
                if nxt is not None:
                    used[j] = True
                    break
            if nxt is None:
                break
            ch.append(nxt)
        if np.linalg.norm(ch[-1][-1] - ch[0][0]) <= tol:
            loops.append(ch)
    return loops


class Face:
    """One member face seen as S(s, t): t along the rail / lofting direction, s around the section."""

    def __init__(self, model, idx, diag, op):
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        self.idx = idx
        f = _face(model, idx)
        if op == "sweep":
            cu, _ = _family_stats(f, "u")
            cv, _ = _family_stats(f, "v")
            fam = "u" if cu <= cv else "v"
        else:
            fam = loft_section_family(f, diag)
        u0, u1, v0, v1 = _uv_bounds(f)
        self.fam = fam
        self.ra, self.rb, self.sa, self.sb = (u0, u1, v0, v1) if fam == "u" else (v0, v1, u0, u1)
        self.ad = BRepAdaptor_Surface(f)
        self.face = f

    def iso_curve(self, t):
        from OCP.BRep import BRep_Tool
        S = BRep_Tool.Surface_s(self.face)
        try:
            return S.UIso(float(t)) if self.fam == "u" else S.VIso(float(t))
        except Exception:                                  # noqa: BLE001
            return None

    def curve(self, t, m=M_SEC):
        pts = [self.ad.Value(t, self.sa + (self.sb - self.sa) * k / (m - 1)) if self.fam == "u"
               else self.ad.Value(self.sa + (self.sb - self.sa) * k / (m - 1), t) for k in range(m)]
        return np.array([[p.X(), p.Y(), p.Z()] for p in pts])


def _shared_edge_points(model, a, b, n=9):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS
    ea = set(model.describe_entity(f"face:{a}")["adjacency"]["edges"])
    eb = set(model.describe_entity(f"face:{b}")["adjacency"]["edges"])
    out = []
    for eid in sorted(ea & eb):
        e = sdk_ocp.resolve(model, eid)
        c = BRepAdaptor_Curve(TopoDS.Edge_s(e[-1] if isinstance(e, tuple) else e))
        out += [[c.Value(t).X(), c.Value(t).Y(), c.Value(t).Z()] for t in np.linspace(c.FirstParameter(), c.LastParameter(), n)]
    return np.asarray(out)


def _seg_dist(p, A, B):
    AB = B - A
    t = np.clip(np.einsum("ij,ij->i", p - A, AB) / np.maximum(np.einsum("ij,ij->i", AB, AB), 1e-30), 0, 1)
    return float(np.min(np.linalg.norm(A + AB * t[:, None] - p, axis=1)))


def _on_curve(P, curves, tol):
    """Every point of P lies on one of the polylines (distance to segments, not to samples)."""
    return all(min(_seg_dist(p, C[:-1], C[1:]) for C in curves) <= tol for p in P)


class Group:
    """A layer of side-by-side faces sharing the rail parameter t (a sweep or loft gives all faces around one segment of the
    path the same t). Faces stacked end to end along the path - a rail made of several edges, a loft through more than two
    sections built ruled or in spans - form separate layers."""

    def __init__(self, faces, diag):
        self.diag = diag
        self.members = faces
        self.a = max(f.ra for f in faces)
        self.b = min(f.rb for f in faces)
        self.complete = True

    def pieces(self, t, m=M_SEC):
        return [f.curve(t, m) for f in self.members]

    def section(self, t):
        pcs = self.pieces(t)
        return chain(pcs, self.diag), np.vstack(pcs)


def layers(model, sdk_faces, diag, op):
    """Split a free-form group into layers of side-by-side faces, ordered along the path."""
    F = {i: Face(model, i, diag, op) for i in sdk_faces}
    side = {i: set() for i in sdk_faces}
    for a in sdk_faces:
        for b in sdk_faces:
            if b <= a:
                continue
            P = _shared_edge_points(model, a, b)
            if not len(P):
                continue
            fa = F[a]
            ends = [fa.curve(fa.ra, 200), fa.curve(fa.rb, 200)]
            if not _on_curve(P, ends, 1e-3 * diag):      # not a section boundary: they lie side by side
                side[a].add(b)
                side[b].add(a)
    seen, groups = set(), []
    for s0 in sdk_faces:
        if s0 in seen:
            continue
        stack, comp = [s0], []
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            comp.append(F[k])
            stack += list(side[k] - seen)
        groups.append(Group(comp, diag))
    if len(groups) > 1:                                    # order along the path: walk from the end layer outward
        cen = [np.vstack(g.pieces((g.a + g.b) / 2, 8)).mean(0) for g in groups]
        d = np.array([[np.linalg.norm(x - y) for y in cen] for x in cen])
        start = int(np.argmax(d.max(1)))
        order, left = [start], set(range(len(groups))) - {start}
        while left:
            nxt = min(left, key=lambda j: d[order[-1], j])
            order.append(nxt)
            left.remove(nxt)
        groups = [groups[k] for k in order]
    return groups


def _section_at(group, t, tangent, diag):
    loops, pts = group.section(t)
    n = section_normal(pts, tangent, diag)
    exact = None
    if len(group.members) == 1 and len(loops) == 1 and len(loops[0]) == 1:
        exact = group.members[0].iso_curve(t)
    return summarize_section(loops, n, diag, exact) if loops else None, pts, n


def _layer_rail(g, anchor_from=None):
    ts = [g.a + (g.b - g.a) * k / (K_RAIL - 1) for k in range(K_RAIL)]
    P = [np.vstack(g.pieces(t)) for t in ts]
    return ts, P


def fit_helix(rail, diag):
    """A rail that is a helix: axis from the tangents (they keep a constant angle to it), radius and centre from the
    projection, pitch from height against unwrapped angle. Returns make_helix_rwire's arguments, or None."""
    P = np.asarray(rail, float)
    if len(P) < 6:
        return None
    T = np.diff(P, axis=0)
    T = T / np.linalg.norm(T, axis=1, keepdims=True)
    a = np.linalg.svd(T - T.mean(0))[2][-1]
    e1, e2 = geomnorm._basis(a)
    xy = np.c_[P @ e1, P @ e2]
    M = np.c_[2 * xy, np.ones(len(xy))]
    sol = np.linalg.lstsq(M, (xy ** 2).sum(1), rcond=None)[0]
    cx, cy = sol[0], sol[1]
    R = math.sqrt(max(float(sol[2]) + cx * cx + cy * cy, 0.0))
    if R < 1e-6 * diag or np.abs(np.hypot(xy[:, 0] - cx, xy[:, 1] - cy) - R).max() > 2e-3 * diag:
        return None
    th = np.unwrap(np.arctan2(xy[:, 1] - cy, xy[:, 0] - cx))
    z = P @ a
    k, z0 = np.polyfit(th, z, 1)
    if np.abs(k * th + z0 - z).max() > 2e-3 * diag or abs(th[-1] - th[0]) < math.pi or abs(k) < 1e-9:
        return None
    if k < 0:                                              # axis points the way the helix climbs
        a, k, th = -a, -k, -th
        e1, e2 = geomnorm._basis(a)
        xy = np.c_[P @ e1, P @ e2]
        sol = np.linalg.lstsq(np.c_[2 * xy, np.ones(len(xy))], (xy ** 2).sum(1), rcond=None)[0]
        cx, cy = sol[0], sol[1]
        th = np.unwrap(np.arctan2(xy[:, 1] - cy, xy[:, 0] - cx))
    zs = P @ a
    centre = e1 * cx + e2 * cy + a * float(zs[0])
    hand = "Right" if th[-1] > th[0] else "Left"
    return {"axis": [round(float(v), 4) for v in a], "centre": [round(float(v), 4) for v in centre], "radius": round(R, 4),
            "pitch": round(2 * math.pi * k, 4), "height": round(float(zs[-1] - zs[0]), 4), "hand": hand}


def rail_frames(rail):
    """Tangent, Frenet normal and a rotation-minimising normal at each rail point, on the spline that interpolates the
    points with chord-length parameters (what make_interpolated_spline_redge builds)."""
    from OCP.GeomAPI import GeomAPI_Interpolate
    from OCP.TColStd import TColStd_HArray1OfReal
    from OCP.TColgp import TColgp_HArray1OfPnt
    from OCP.gp import gp_Pnt, gp_Vec
    n = len(rail)
    arr = TColgp_HArray1OfPnt(1, n)
    for k, p in enumerate(rail):
        arr.SetValue(k + 1, gp_Pnt(*map(float, p)))
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(rail, axis=0), axis=1))]
    s = s / s[-1]
    par = TColStd_HArray1OfReal(1, n)
    for k in range(n):
        par.SetValue(k + 1, float(s[k]))
    it = GeomAPI_Interpolate(arr, par, False, 1e-9)
    it.Perform()
    c = it.Curve()
    T, N = [], []
    for u in s:
        p, d1, d2 = gp_Pnt(), gp_Vec(), gp_Vec()
        c.D2(float(u), p, d1, d2)
        t = np.array([d1.X(), d1.Y(), d1.Z()])
        t /= np.linalg.norm(t)
        a = np.array([d2.X(), d2.Y(), d2.Z()])
        nn = a - (a @ t) * t
        T.append(t)
        N.append(nn / np.linalg.norm(nn) if np.linalg.norm(nn) > 1e-9 else None)
    R = [None] * n                                         # double-reflection rotation-minimising frame
    return np.array(T), N


def detect_frame(rail, P, diag):
    """Which frame carries the profile: Frenet (it turns with the rail's curvature) or rotation-minimising (no twist about the
    tangent). Compared on the profile's own in-plane direction, carried by rigid fits between stations; None when the
    profile is round (the frame does not matter) or the rail is straight."""
    T, N = rail_frames(np.asarray(rail, float))
    if any(n is None for n in N[1:-1]):
        return None
    c0 = P[0] - P[0].mean(0)
    _, sv, vt = np.linalg.svd(c0, full_matrices=False)
    if sv[1] > 0.97 * sv[0]:                              # round-ish profile: orientation unobservable
        return None
    x0 = vt[0] - (vt[0] @ T[0]) * T[0]
    x0 /= np.linalg.norm(x0)
    b0 = np.cross(T[0], N[0])
    fa, fb = x0 @ N[0], x0 @ b0
    xr = x0.copy()
    err_f, err_r = [], []
    for k in range(1, len(P)):
        Rk, _ = kabsch(P[0], P[k])
        xk = Rk @ x0
        xk -= (xk @ T[k]) * T[k]
        xk /= np.linalg.norm(xk)
        pf = fa * N[k] + fb * np.cross(T[k], N[k])
        v1 = np.asarray(rail[k], float) - np.asarray(rail[k - 1], float)       # double reflection step
        c1 = v1 @ v1
        rl = xr - (2 / c1) * (v1 @ xr) * v1
        tl = T[k - 1] - (2 / c1) * (v1 @ T[k - 1]) * v1
        v2 = T[k] - tl
        c2 = v2 @ v2
        xr = rl - (2 / c2) * (v2 @ rl) * v2 if c2 > 1e-18 else rl
        xr -= (xr @ T[k]) * T[k]
        xr /= np.linalg.norm(xr)
        ang = lambda a, b: float(np.degrees(np.arccos(np.clip(abs(a @ b), -1, 1))))
        err_f.append(ang(xk, pf))
        err_r.append(ang(xk, xr))
    ef, er = float(np.max(err_f)), float(np.max(err_r))
    return {"frame": "frenet" if ef < er else "fixed", "err_deg": round(min(ef, er), 1), "uncertain": min(ef, er) > 10.0}


def loop_centroid(g, t, diag):
    """Area centroid of the closed section of a layer at t: the profile's centroid carried to that station. Needs no
    point correspondence between stations, unlike a rigid fit."""
    loops, pts = g.section(t)
    if not loops:
        return None
    L = max((_pts(l) for l in loops), key=len)
    c0 = L.mean(0)
    _, _, vt = np.linalg.svd(L - c0, full_matrices=False)
    x, y = vt[0], vt[1]
    A, c2 = _poly_area_centroid(np.c_[(L - c0) @ x, (L - c0) @ y])
    return c0 + x * c2[0] + y * c2[1] if abs(A) > 0 else None


def sweep_params(model, sdk_faces, diag):
    """Rail and profile of a swept face group (sdk_faces: all B-rep faces of the group, the largest first)."""
    L = layers(model, sdk_faces, diag, "sweep")
    rail, prof, partial = [], None, False
    for li, g in enumerate(L):
        ts, P = _layer_rail(g)
        # orient the layer so it continues from the previous one
        if rail:
            if np.linalg.norm(P[-1].mean(0) - rail[-1]) < np.linalg.norm(P[0].mean(0) - rail[-1]):
                ts, P = ts[::-1], P[::-1]
            if np.linalg.norm(P[0].mean(0) - ref_end.mean(0)) > 0.02 * diag:
                partial = True                            # the next layer does not continue this one (a run-out face)
                break
        if li == 0:
            prof, _, _ = _section_at(g, ts[0], P[1].mean(0) - P[0].mean(0), diag)
            anchor = np.asarray(prof["o"], float) if prof else P[0].mean(0)
            ref = P[0]
        else:                                             # carry the anchor across the junction
            R, T = kabsch(ref_end, P[0])
            anchor = R @ anchor_end + T
            ref = P[0]
        pts = []
        for t, Pk in zip(ts, P):
            c = loop_centroid(g, t, diag) if prof else None
            if c is None:                                 # loop does not close: carry the anchor rigidly
                R, T = kabsch(ref, Pk)
                c = R @ anchor + T
            pts.append(c)
        ref_end, anchor_end = P[-1], pts[-1] if li == 0 else pts[-1]
        anchor_end = pts[-1]
        ref_end = P[-1]
        rail += pts if not rail else pts[1:]
    rail = np.array(rail)
    if float(np.linalg.norm(np.diff(rail, axis=0), axis=1).sum()) < 1e-3 * diag:
        return None                                       # no motion: no recipe, only the label
    if prof is None:                                      # open section (a thread flank): only a helix is worth stating
        hx = fit_helix(rail, diag)
        return {"helix": hx} if hx else None
    out = {"rail": [[round(float(v), 3) for v in p] for p in rail], "profile": prof}
    if partial:
        out["rail_partial"] = True
    hx = fit_helix(rail, diag)
    if hx:
        out.pop("rail")
        out["helix"] = hx
    if len(L) == 1 and len(rail) >= 4:
        try:
            fr = detect_frame(rail, _layer_rail(L[0])[1], diag)
        except Exception:                                 # noqa: BLE001 - a frame hint is optional
            fr = None
        if fr:
            out["frame"] = fr["frame"] + ("?" if fr["uncertain"] else "")
    if len(L) > 1:
        out["rail_segments"] = len(L)
    if float(np.linalg.norm(rail[0] - rail[-1])) <= 1e-4 * diag:
        out["rail_closed"] = True
    chord = rail[-1] - rail[0]
    if np.linalg.norm(chord) > 0:
        u = chord / np.linalg.norm(chord)
        w = rail - rail[0]
        if np.abs(w - np.outer(w @ u, u)).max() <= 1e-4 * diag:
            out["rail"] = [out["rail"][0], out["rail"][-1]]
            out["rail_line"] = True
    return out


def loft_params(model, sdk_faces, diag):
    """Sections a lofted face group passes through. Within a layer they are evenly spaced, as many as the surface has control
    points in the lofting direction (an interpolating loft through N sections has N, so lofting through them again
    reproduces it); between layers (ruled lofts, spans) the shared boundaries are the original sections themselves."""
    from OCP.BRep import BRep_Tool
    from OCP.Geom import Geom_BSplineSurface
    L = layers(model, sdk_faces, diag, "loft")
    stations = []                                         # (layer, t)
    for li, g in enumerate(L):
        S = sdk_ocp.surface(g.members[0].face)
        npoles = 2
        if isinstance(S, Geom_BSplineSurface):
            npoles = S.NbUPoles() if g.members[0].fam == "u" else S.NbVPoles()
        k = max(2, min(npoles, MAX_LOFT_SECTIONS))
        ts = [g.a + (g.b - g.a) * j / (k - 1) for j in range(k)]
        if stations:
            prev = np.vstack(stations[-1][0].pieces(stations[-1][1], 8)).mean(0)
            if np.linalg.norm(np.vstack(g.pieces(ts[-1], 8)).mean(0) - prev) < np.linalg.norm(np.vstack(g.pieces(ts[0], 8)).mean(0) - prev):
                ts = ts[::-1]
            ts = ts[1:]                                   # the shared boundary is already listed
        stations += [(g, t) for t in ts]
    cen = [np.vstack(g.pieces(t, 8)).mean(0) for g, t in stations]
    secs = []
    for j, (g, t) in enumerate(stations):
        tang = cen[min(j + 1, len(cen) - 1)] - cen[max(j - 1, 0)]
        s_, _, _ = _section_at(g, t, tang, diag)
        if s_ is not None:
            secs.append(s_)
    span_ok = all((g.b - g.a) >= 0.5 * max(f.rb - f.ra for f in g.members) for g in L)
    if len(secs) >= 2:                                    # the sections must actually spread along the loft
        nn = np.asarray(secs[0]["n"], float)
        hs = [float(np.asarray(x["o"], float) @ nn) for x in secs]
        ext = np.vstack([geomnorm.boundary_points(_face(model, i)) for i in sdk_faces]) @ nn
        if max(hs) - min(hs) < 0.3 * float(ext.max() - ext.min()):
            span_ok = False
    if len(secs) < len(stations) or len(secs) < 2 or not span_ok:
        alt = plane_stations(model, sdk_faces, L, diag)
        if alt and len(alt) >= len(secs):
            return {"sections": alt, "by_planes": True}
    out = {"sections": secs}
    if len(L) > 1:
        out["ruled_or_spans"] = len(L)
    if len(secs) < len(stations):
        out["sections_missing"] = len(stations) - len(secs)
    return out


def plane_stations(model, sdk_faces, L, diag):
    """Fallback when the faces do not line up into layers: if the sections are parallel planes, cut the whole group with
    evenly spaced parallel planes (count = control points along the lofting direction, at least 3)."""
    from OCP.BRep import BRep_Tool
    from OCP.Geom import Geom_BSplineSurface
    f0 = L[0].members[0]
    c = f0.curve((f0.ra + f0.rb) / 2)
    _, sv, vt = np.linalg.svd(c - c.mean(0), full_matrices=False)
    if sv[1] <= 1e-6 * diag:                                    # a straight piece: use the lofting direction instead
        n = f0.curve(f0.rb).mean(0) - f0.curve(f0.ra).mean(0)
    else:
        n = vt[2]
    n = n / np.linalg.norm(n)
    pts = np.vstack([geomnorm.boundary_points(_face(model, i)) for i in sdk_faces])
    h = pts @ n
    lo, hi = float(h.min()), float(h.max())
    if hi - lo <= 1e-6 * diag:
        return None
    npoles = 3
    for i in sdk_faces:
        S = sdk_ocp.surface(_face(model, i))
        if isinstance(S, Geom_BSplineSurface):
            npoles = max(npoles, min(S.NbUPoles(), S.NbVPoles()))
    k = max(3, min(npoles, MAX_LOFT_SECTIONS))
    inset = 1e-3 * (hi - lo)
    out = []
    for j in range(k):
        hj = lo + inset + (hi - lo - 2 * inset) * j / (k - 1)
        base = pts[np.argmin(np.abs(h - hj))]
        o = base + (hj - float(base @ n)) * n
        loops = section_loops(model, sdk_faces, o, n, diag)
        s_ = summarize_section(loops, n, diag)
        if s_ is not None:
            out.append(s_)
    return out


def group_construction(model, infos, newid, op, ir_faces, diag):
    """Construction parameters of one connected free-form group (ir ids) with its operation name."""
    members = []
    for k, inf in enumerate(infos):
        if "dead" not in inf and newid.get(k) in ir_faces:
            members += list(inf.get("members") or [k])
    members.sort(key=lambda m: -float(infos[m]["area"]))
    if not members:
        return None
    try:
        return sweep_params(model, members, diag) if op == "sweep" else loft_params(model, members, diag)
    except Exception:                                        # noqa: BLE001 - a construction hint is optional, never a crash
        return None
