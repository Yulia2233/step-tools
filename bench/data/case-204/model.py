from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: freeform-offset-grip (build, profile=geometry) ----
    sketch = scad.make_sketch_rsketch(name='rounded_grip', plane='XY')
    for point_id, x, y in [('a', -6.0, -6.0), ('b', 6.0, -6.0), ('c', 9.0, -3.0), ('d', 9.0, 3.0), ('e', 6.0, 6.0), ('f', -6.0, 6.0), ('g', -9.0, 3.0), ('h', -9.0, -3.0), ('br', 6.0, -3.0), ('tr', 6.0, 3.0), ('tl', -6.0, 3.0), ('bl', -6.0, -3.0)]:
        sketch = scad.add_point_rsketch(sketch=sketch, point_id=point_id, x=x, y=y)
    for entity_id, start, end in [('bottom', 'a', 'b'), ('right', 'c', 'd'), ('top', 'e', 'f'), ('left', 'g', 'h')]:
        sketch = scad.add_line_rsketch(sketch=sketch, entity_id=entity_id, start=start, end=end)
    for entity_id, start, end, center in [('round_br', 'b', 'c', 'br'), ('round_tr', 'd', 'e', 'tr'), ('round_tl', 'f', 'g', 'tl'), ('round_bl', 'h', 'a', 'bl')]:
        sketch = scad.add_arc_rsketch(sketch=sketch, entity_id=entity_id, start=start, end=end, center=center)
    profile = scad.make_face_from_sketch_rface(sketch=sketch)
    rail_edge = scad.make_spline_redge(control_points=[(0.0, 0.0, 0.0), (0.0, 0.0, 26.0), (24.0, 12.0, 52.0), (34.0, -6.0, 72.0)], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: rectangular-mounting-foot (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=36.0, height=24.0, depth=6.0, bottom_face_center=(0.0, 0.0, -3.0))
    result = scad.union_rsolid(*[result, flange])

    # ---- feature: mounting-bolt-pair (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=2.2, height=10.0, bottom_face_center=(-13.0, 0.0, -5.0), axis=(0.0, 0.0, 1.0))
    bolt_1 = scad.make_cylinder_rsolid(radius=2.2, height=10.0, bottom_face_center=(13.0, 0.0, -5.0), axis=(0.0, 0.0, 1.0))
    result = scad.cut_rsolid(*[result, bolt_0, bolt_1], skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Freeform offset equipment grip')

if __name__ == "__main__":
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from simplecadapi.exporter.step import export_product_package_to_step
    with TemporaryDirectory(prefix="tail-solid-export-") as scratch:
        product = build()
        package = Path(scratch) / "product.scadpkg"
        scad.capture(product, package, include_scene=False)
        export_product_package_to_step(data=package,
            output_path=Path(__file__).with_suffix(".step"))
