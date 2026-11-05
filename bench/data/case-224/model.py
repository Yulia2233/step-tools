from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: rounded-grip-section (build, profile=geometry) ----
    a = scad.make_line_redge(start=(-3.0, -2.5, 0.0), end=(3.0, -2.5, 0.0))
    b = scad.make_three_point_arc_redge(start=(3.0, -2.5, 0.0), middle=(3.707106781, -2.207106781, 0.0), end=(4.0, -1.5, 0.0))
    c = scad.make_line_redge(start=(4.0, -1.5, 0.0), end=(4.0, 1.5, 0.0))
    d = scad.make_three_point_arc_redge(start=(4.0, 1.5, 0.0), middle=(3.707106781, 2.207106781, 0.0), end=(3.0, 2.5, 0.0))
    e = scad.make_line_redge(start=(3.0, 2.5, 0.0), end=(-3.0, 2.5, 0.0))
    f = scad.make_three_point_arc_redge(start=(-3.0, 2.5, 0.0), middle=(-3.707106781, 2.207106781, 0.0), end=(-4.0, 1.5, 0.0))
    g = scad.make_line_redge(start=(-4.0, 1.5, 0.0), end=(-4.0, -1.5, 0.0))
    h = scad.make_three_point_arc_redge(start=(-4.0, -1.5, 0.0), middle=(-3.707106781, -2.207106781, 0.0), end=(-3.0, -2.5, 0.0))
    section = scad.make_wire_from_edges_rwire(edges=[a, b, c, d, e, f, g, h])
    profile = scad.make_face_from_wire_rface(wire=section, normal=(0.0, 0.0, 1.0))

    # ---- feature: straight-to-spatial-spline-rail (build, profile=geometry) ----
    lead = scad.make_line_redge(start=(0.0, 0.0, 0.0), end=(0.0, 0.0, 7.0))
    bend = scad.make_spline_redge(control_points=[[0.0, 0.0, 7.0], [0.0, 0.0, 14.0], [5.0, 2.0, 22.0], [11.0, 4.0, 27.0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[lead, bend])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: softened-grip-entry-rim (modify, profile=geometry) ----
    rim = scad.ql.edges().where(scad.ql.and_(scad.ql.prop('geom.center.z', '>=', -0.001), scad.ql.prop('geom.center.z', '<=', 0.001))).exactly(8)
    edges = rim.resolve(result)
    print('Entry rim edges:', len(edges))
    result = scad.fillet_rsolid(solid=result, edges=edges, radius=0.35)
    print('Finished volume:', result.get_volume())

    return scad.make_part_rpart(part_id='part', body=result, name='Curved ergonomic actuator grip')

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
