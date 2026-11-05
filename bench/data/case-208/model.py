from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: l-section-guide-profile (build, profile=geometry) ----
    profile_sketch = scad.make_sketch_rsketch(name='guide_section', plane='XY')
    for point_id, x, y in [('a', -4.0, -3.0), ('b', 4.0, -3.0), ('c', 4.0, 0.0), ('d', 0.0, 0.0), ('e', 0.0, 4.0), ('f', -4.0, 4.0)]:
        profile_sketch = scad.add_point_rsketch(sketch=profile_sketch, point_id=point_id, x=x, y=y)
    for entity_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('de', 'd', 'e'), ('ef', 'e', 'f'), ('fa', 'f', 'a')]:
        profile_sketch = scad.add_line_rsketch(sketch=profile_sketch, entity_id=entity_id, start=start, end=end)
    profile = scad.make_face_from_sketch_rface(sketch=profile_sketch)

    # ---- feature: spatial-spline-guide (build, profile=geometry) ----
    rail_edge = scad.make_spline_redge(control_points=[(0.0, 0.0, 0.0), (0.0, 0.0, 6.0), (1.2, 0.5, 12.0), (-0.8, 1.0, 18.0), (0.5, -0.5, 24.0), (0.0, 0.0, 30.0)], degree=3, knots=[0.0, 1.0, 2.0, 3.0], multiplicities=[4, 1, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=False)

    # ---- feature: longitudinal-cable-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=0.65, height=36.0, bottom_face_center=(-2.0, -1.0, -3.0), axis=(0.0, 0.0, 1.0))
    result = scad.cut_rsolid(*[result, bore], skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Spatial L-section cable guide')

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
