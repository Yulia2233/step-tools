from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: l-section-sweep (build, profile=geometry) ----
    sketch = scad.make_sketch_rsketch(name='l_section', plane='XY')
    sketch = scad.add_point_rsketch(sketch=sketch, point_id='p0', x=0.0, y=0.0)
    sketch = scad.add_point_rsketch(sketch=sketch, point_id='p1', x=14.0, y=0.0)
    sketch = scad.add_point_rsketch(sketch=sketch, point_id='p2', x=14.0, y=4.0)
    sketch = scad.add_point_rsketch(sketch=sketch, point_id='p3', x=5.0, y=4.0)
    sketch = scad.add_point_rsketch(sketch=sketch, point_id='p4', x=5.0, y=14.0)
    sketch = scad.add_point_rsketch(sketch=sketch, point_id='p5', x=0.0, y=14.0)
    sketch = scad.add_line_rsketch(sketch=sketch, entity_id='e0', start='p0', end='p1')
    sketch = scad.add_line_rsketch(sketch=sketch, entity_id='e1', start='p1', end='p2')
    sketch = scad.add_line_rsketch(sketch=sketch, entity_id='e2', start='p2', end='p3')
    sketch = scad.add_line_rsketch(sketch=sketch, entity_id='e3', start='p3', end='p4')
    sketch = scad.add_line_rsketch(sketch=sketch, entity_id='e4', start='p4', end='p5')
    sketch = scad.add_line_rsketch(sketch=sketch, entity_id='e5', start='p5', end='p0')
    profile_wire = scad.make_wire_from_sketch_rwire(sketch=sketch)
    profile = scad.make_face_from_wire_rface(wire=profile_wire, normal=(0, 0, 1))
    rail_edge = scad.make_spline_redge(control_points=[[0, 0, 0], [0, 0, 16], [5, 3, 34], [13, -4, 53], [20, 2, 72]], degree=3, knots=[0.0, 0.5, 1.0], multiplicities=[4, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=False)

    # ---- feature: rectangular-base-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=34.0, height=30.0, depth=6.0, bottom_face_center=(0, 0, -4.0))
    result = scad.union_rsolid(result, flange)

    # ---- feature: flange-bolt-holes (subtract, profile=geometry) ----
    hole_left = scad.make_cylinder_rsolid(radius=2.2, height=8.0, bottom_face_center=(-12.0, 0.0, -5.0), axis=(0, 0, 1))
    hole_right = scad.make_cylinder_rsolid(radius=2.2, height=8.0, bottom_face_center=(12.0, 0.0, -5.0), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, hole_left, hole_right, skip_non_intersecting=False)
    return scad.make_part_rpart(part_id='part', body=result, name='Curved L-section mounting duct')

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
