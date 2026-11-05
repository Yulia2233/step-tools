from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: spatial-curved-grip (build, profile=geometry) ----
    profile_sketch = scad.make_sketch_rsketch(name='rounded_grip_section', plane='XY')
    for point_id, x, y in [('a', -2.2, -2.0), ('b', 2.2, -2.0), ('c', 3.0, -1.2), ('d', 3.0, 1.2), ('e', 2.2, 2.0), ('f', -2.2, 2.0), ('g', -3.0, 1.2), ('h', -3.0, -1.2), ('br', 2.2, -1.2), ('tr', 2.2, 1.2), ('tl', -2.2, 1.2), ('bl', -2.2, -1.2)]:
        profile_sketch = scad.add_point_rsketch(sketch=profile_sketch, point_id=point_id, x=x, y=y)
    profile_sketch = scad.add_line_rsketch(sketch=profile_sketch, entity_id='bottom', start='a', end='b')
    profile_sketch = scad.add_arc_rsketch(sketch=profile_sketch, entity_id='bottom_right', start='b', end='c', center='br')
    profile_sketch = scad.add_line_rsketch(sketch=profile_sketch, entity_id='right', start='c', end='d')
    profile_sketch = scad.add_arc_rsketch(sketch=profile_sketch, entity_id='top_right', start='d', end='e', center='tr')
    profile_sketch = scad.add_line_rsketch(sketch=profile_sketch, entity_id='top', start='e', end='f')
    profile_sketch = scad.add_arc_rsketch(sketch=profile_sketch, entity_id='top_left', start='f', end='g', center='tl')
    profile_sketch = scad.add_line_rsketch(sketch=profile_sketch, entity_id='left', start='g', end='h')
    profile_sketch = scad.add_arc_rsketch(sketch=profile_sketch, entity_id='bottom_left', start='h', end='a', center='bl')
    profile = scad.make_face_from_sketch_rface(sketch=profile_sketch)
    rail_edge = scad.make_spline_redge(control_points=[[0.0, 0.0, 0.0], [0.0, 0.0, 5.0], [2.0, 1.0, 10.0], [6.0, 4.0, 15.0], [10.0, 3.0, 20.0], [13.0, 0.0, 24.0], [14.0, -2.0, 27.0]], degree=3, knots=[0.0, 0.25, 0.5, 0.75, 1.0], multiplicities=[4, 1, 1, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    return scad.make_part_rpart(part_id='part', body=result, name='Spatial curved instrument grip')

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
