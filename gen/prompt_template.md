You are writing ONE SimpleCADAPI part script for a CAD benchmark. Output: `model.py` in your cwd, and the STEP it exports, `model.step`, next to it.

Task `{id}` ({kind}), overall size about {size_mm} mm, units mm:
1. Main body: {spec}
2. Then: {finish}.

Rules (all checked by a script afterwards; a failed check means the part is discarded):
- Use ONLY the public SimpleCADAPI API (`import simplecadapi as scad`). No OCP/CadQuery/build123d/FreeCAD, no reading any STEP/BREP file, no mesh libraries, no `try/except` fallbacks.
- Interpreter that must run it: `{python}` (SimpleCADAPI 2.2.5). Run `cd <cwd> && <interpreter> model.py`; it must export `model.step`. Docs: ~/.codex/skills/simplecadapi/SKILL.md and its references/ (read the exact API page before using an API; spline edges are `scad.make_spline_redge(control_points=..., degree=..., knots=..., multiplicities=...)` - see the example).
- Follow EXACTLY the file layout of the example scripts (read them; they are the only other files you may read besides the docs): `{examples}/case-006/model.py` (sweep), `{examples}/case-020/model.py` (loft), `{examples}/case-001/model.py` (spline edges, and the `__main__` export block at its end - copy that block unchanged). Feature tree: `# ---- feature: <slug> (<role>, profile=geometry) ----` blocks, keyword arguments for every SDK call, numeric literals only (no formulas, no helper functions or classes; `for` over literal lists is fine), `scad.make_part_rpart(part_id='part', body=result, name='...')` at the end.
- The result must be ONE valid closed solid with positive volume. Dimensions are your design choice; make the part look like a plausible real component (a handle, duct, bracket, cover, nozzle, ...), different from a trivial toy.
- Edge/face selection for fillet/chamfer must use QL predicates (see the docs), never index enumeration.
- The main body's defining surface must really be what the task says (free-form where it says free-form): after you export, check it, e.g. by looking at the face types the SDK inspector reports (`from simplecadapi.inspect import brep; m=brep.load_step_rbrepmodel(path='model.step')`, then `m.describe_entity('face:0')['geometry']['type']`). A free-form face shows as BSPLINE or EXTRUSION or similar, NOT CYLINDER/TORUS/CONE/PLANE.
- Keep the script under 90 lines. Finish promptly once `model.step` exists and the checks above pass. Do not write any other files except `model.py`, `model.step` (and what the SDK writes).
{retry}
