from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: rounded-grip-section (build, profile=geometry) ----
    lower = scad.make_line_redge(start=(-5, -4.5, 0), end=(5, -4.5, 0))
    lower_right = scad.make_three_point_arc_redge(start=(5, -4.5, 0), middle=(6.414213562373095, -3.914213562373095, 0), end=(7, -2.5, 0))
    right = scad.make_line_redge(start=(7, -2.5, 0), end=(7, 2.5, 0))
    upper_right = scad.make_three_point_arc_redge(start=(7, 2.5, 0), middle=(6.414213562373095, 3.914213562373095, 0), end=(5, 4.5, 0))
    upper = scad.make_line_redge(start=(5, 4.5, 0), end=(-5, 4.5, 0))
    upper_left = scad.make_three_point_arc_redge(start=(-5, 4.5, 0), middle=(-6.414213562373095, 3.914213562373095, 0), end=(-7, 2.5, 0))
    left = scad.make_line_redge(start=(-7, 2.5, 0), end=(-7, -2.5, 0))
    lower_left = scad.make_three_point_arc_redge(start=(-7, -2.5, 0), middle=(-6.414213562373095, -3.914213562373095, 0), end=(-5, -4.5, 0))
    section_wire = scad.make_wire_from_edges_rwire(edges=[lower, lower_right, right, upper_right, upper, upper_left, left, lower_left])
    section = scad.make_face_from_wire_rface(wire=section_wire, normal=(0, 0, 1))

    # ---- feature: mixed-rail-curved-grip (build, profile=geometry) ----
    straight_rail = scad.make_line_redge(start=(0, 0, 0), end=(0, 0, 16))
    curved_rail = scad.make_spline_redge(control_points=[[0, 0, 16], [0, 0, 30], [13, 2, 42], [25, 5, 52]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[straight_rail, curved_rail])
    result = scad.sweep_rsolid(profile=section, path=rail, is_frenet=True)

    # ---- feature: softened-base-rim (modifier, profile=geometry) ----
    base_edges = scad.ql.edges().where(predicate=scad.ql.prop(path='geom.center.z', op='>=', value_=-0.001)).where(predicate=scad.ql.prop(path='geom.center.z', op='<=', value_=0.001)).where(predicate=scad.ql.prop(path='geom.length', op='>', value_=9.9)).exactly(count=2)
    result = scad.fillet_rsolid(solid=result, edges=base_edges, radius=0.7)

    return scad.make_part_rpart(part_id='part', body=result, name='Curved ergonomic lever grip')

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
