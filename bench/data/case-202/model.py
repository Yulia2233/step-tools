from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: freeform-conduit-envelope (build, profile=geometry) ----
    profile_sketch = scad.make_sketch_rsketch(name='rectangular_conduit_section', plane='XY')
    profile_sketch = scad.add_point_rsketch(sketch=profile_sketch, point_id='a', x=-12.0, y=-10.0)
    profile_sketch = scad.add_point_rsketch(sketch=profile_sketch, point_id='b', x=12.0, y=-10.0)
    profile_sketch = scad.add_point_rsketch(sketch=profile_sketch, point_id='c', x=12.0, y=10.0)
    profile_sketch = scad.add_point_rsketch(sketch=profile_sketch, point_id='d', x=-12.0, y=10.0)
    profile_sketch = scad.add_line_rsketch(sketch=profile_sketch, entity_id='ab', start='a', end='b')
    profile_sketch = scad.add_line_rsketch(sketch=profile_sketch, entity_id='bc', start='b', end='c')
    profile_sketch = scad.add_line_rsketch(sketch=profile_sketch, entity_id='cd', start='c', end='d')
    profile_sketch = scad.add_line_rsketch(sketch=profile_sketch, entity_id='da', start='d', end='a')
    profile_wire = scad.make_wire_from_sketch_rwire(sketch=profile_sketch)
    profile = scad.make_face_from_wire_rface(wire=profile_wire, normal=(0, 0, 1))
    rail_edge = scad.make_spline_redge(control_points=[[0, 0, 0], [0, 0, 12], [4, 0, 26], [7, 3, 40], [6, 5, 54], [3, 3, 68], [0, 0, 80]], degree=3, knots=[0.0, 0.25, 0.5, 0.75, 1.0], multiplicities=[4, 1, 1, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: longitudinal-cable-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=3.0, height=110.0, bottom_face_center=(0, 0, -15), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Freeform rectangular cable conduit')

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
