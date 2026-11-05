from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: hexagonal-rail-profile (profile, profile=geometry) ----
    section_sketch = scad.make_sketch_rsketch(name='rail_section', plane={'origin': (0, 0, 0), 'x_axis': (0, 1, 0), 'y_axis': (0, 0, 1)})
    section_sketch = scad.add_point_rsketch(sketch=section_sketch, point_id='p0', x=-5.0, y=0.0)
    section_sketch = scad.add_point_rsketch(sketch=section_sketch, point_id='p1', x=-2.5, y=4.33)
    section_sketch = scad.add_point_rsketch(sketch=section_sketch, point_id='p2', x=2.5, y=4.33)
    section_sketch = scad.add_point_rsketch(sketch=section_sketch, point_id='p3', x=5.0, y=0.0)
    section_sketch = scad.add_point_rsketch(sketch=section_sketch, point_id='p4', x=2.5, y=-4.33)
    section_sketch = scad.add_point_rsketch(sketch=section_sketch, point_id='p5', x=-2.5, y=-4.33)
    section_sketch = scad.add_line_rsketch(sketch=section_sketch, entity_id='side0', start='p0', end='p1')
    section_sketch = scad.add_line_rsketch(sketch=section_sketch, entity_id='side1', start='p1', end='p2')
    section_sketch = scad.add_line_rsketch(sketch=section_sketch, entity_id='side2', start='p2', end='p3')
    section_sketch = scad.add_line_rsketch(sketch=section_sketch, entity_id='side3', start='p3', end='p4')
    section_sketch = scad.add_line_rsketch(sketch=section_sketch, entity_id='side4', start='p4', end='p5')
    section_sketch = scad.add_line_rsketch(sketch=section_sketch, entity_id='side5', start='p5', end='p0')
    section_face = scad.make_face_from_sketch_rface(sketch=section_sketch)

    # ---- feature: straight-to-spline-rail-sweep (build, profile=geometry) ----
    lead_edge = scad.make_line_redge(start=(0, 0, 0), end=(22, 0, 0))
    curve_edge = scad.make_spline_redge(control_points=[[22, 0, 0], [36, 0, 0], [49, 4, 0], [61, 15, 0], [72, 25, 0]], degree=3, knots=[0.0, 0.5, 1.0], multiplicities=[4, 1, 4])
    rail_path = scad.make_wire_from_edges_rwire(edges=[lead_edge, curve_edge])
    result = scad.sweep_rsolid(profile=section_face, path=rail_path, is_frenet=False)

    # ---- feature: integral-mounting-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=8.0, height=8.0, bottom_face_center=(10.0, 0.0, 3.5), axis=(0, 0, 1))
    result = scad.union_rsolid(result, boss)

    # ---- feature: blind-boss-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=3.2, height=5.0, bottom_face_center=(10.0, 0.0, 6.5), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Spline rail with mounting boss')

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
