"""OCP views of the entities of a `simplecadapi.inspect.brep` model, for any SDK version.

Up to 2.2.6 the SDK computed with OCP, so `model.faces[i]` and `model.resolve_entity(...)` were OCP shapes. From 2.2.7 it
computes with its own compiled OpenCASCADE and those are `simplecadapi._cpp` shapes, which OCP functions reject. The
geometry code here is written against OCP (needs the `verify` extra on 2.2.7: `pip install "simplecadapi[verify]"`).

The root shape is converted ONCE (OpenCASCADE binary format, bit-exact) and re-indexed with `TopExp.MapShapes`, the same
call the SDK uses for its `face:i` / `edge:i` ids, so ids agree and shared edges stay shared between faces. Converting
entities one by one would copy each face with its own edges and break the sharing that adjacency code relies on.
"""
from __future__ import annotations

_KINDS = {"body": "TopAbs_SOLID", "face": "TopAbs_FACE", "edge": "TopAbs_EDGE", "vertex": "TopAbs_VERTEX"}
_CAST = {"body": "Solid_s", "face": "Face_s", "edge": "Edge_s", "vertex": "Vertex_s"}


def is_ocp(shape):
    return type(shape).__module__.startswith("OCP")


def to_ocp(shape):
    """An OCP shape for an OCP shape (itself) or a raw `simplecadapi._cpp` OCCT shape (a copy)."""
    if is_ocp(shape):
        return shape
    import simplecadapi._cpp as native
    from simplecadapi._glue import bridge
    return bridge.native_to_ocp(native._from_occt(shape))


def _maps(model):
    cached = model.__dict__.get("_stepir_ocp")
    if cached is not None:
        return cached
    from OCP import TopAbs
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS
    root = to_ocp(model.root)
    out = {}
    for kind, enum in _KINDS.items():
        m = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(root, getattr(TopAbs, enum), m)
        cast = getattr(TopoDS, _CAST[kind])
        out[kind] = [cast(m.FindKey(i)) for i in range(1, m.Extent() + 1)]
    if len(out["face"]) != len(model.faces) or len(out["edge"]) != len(model.edges):
        raise RuntimeError("OCP re-indexing disagrees with the SDK's entity ids")
    model.__dict__["_stepir_ocp"] = out
    return out


def faces(model):
    return _maps(model)["face"]


def face(model, index):
    return _maps(model)["face"][index]


def resolve(model, entity_id):
    """`model.resolve_entity` with an OCP shape: (kind, index, shape)."""
    kind, index = entity_id.split(":")
    return kind, int(index), _maps(model)[kind][int(index)]
