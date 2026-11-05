from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: oval-grip-section (sketch, profile=geometry) ----
    section = scad.make_spline_redge(
        control_points=[[0, 0, 4.0], [0, 3.0, 2.8], [0, 4.2, 0], [0, 3.0, -2.8], [0, 0, -4.0], [0, -3.0, -2.8], [0, -4.2, 0], [0, -3.0, 2.8]],
        degree=3, periodic=True)
    section_wire = scad.make_wire_from_edges_rwire(edges=[section])
    profile = scad.make_face_from_wire_rface(wire=section_wire, normal=(-1, 0, 0))

    # ---- feature: straight-to-spline-rail (path, profile=geometry) ----
    rail_start = scad.make_line_redge(start=(0, 0, 0), end=(20, 0, 0))
    rail_curve = scad.make_spline_redge(
        control_points=[[20, 0, 0], [30, 0, 0], [40, 5, 1], [51, 10, 0]],
        degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_start, rail_curve])

    # ---- feature: swept-oval-handle (build, profile=geometry) ----
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=False)

    # ---- feature: rounded-start-rim (modify, profile=geometry) ----
    start_rim = scad.ql.edges().where(scad.ql.and_(
        scad.ql.prop('geom.center.x', '>=', -0.1),
        scad.ql.prop('geom.center.x', '<=', 0.1))).exactly(1)
    result = scad.fillet_rsolid(solid=result, edges=start_rim, radius=0.5)

    return scad.make_part_rpart(part_id='part', body=result, name='Freeform swept grip handle')

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
