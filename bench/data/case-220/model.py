from pathlib import Path

import simplecadapi as scad
from simplecadapi import ql


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: rounded-duct-section (profile, profile=geometry) ----
    profile_edges = [
        scad.make_line_redge(start=(-24, -4, -5), end=(-24, 4, -5)),
        scad.make_three_point_arc_redge(start=(-24, 4, -5), middle=(-24, 5.4142, -4.4142), end=(-24, 6, -3)),
        scad.make_line_redge(start=(-24, 6, -3), end=(-24, 6, 3)),
        scad.make_three_point_arc_redge(start=(-24, 6, 3), middle=(-24, 5.4142, 4.4142), end=(-24, 4, 5)),
        scad.make_line_redge(start=(-24, 4, 5), end=(-24, -4, 5)),
        scad.make_three_point_arc_redge(start=(-24, -4, 5), middle=(-24, -5.4142, 4.4142), end=(-24, -6, 3)),
        scad.make_line_redge(start=(-24, -6, 3), end=(-24, -6, -3)),
        scad.make_three_point_arc_redge(start=(-24, -6, -3), middle=(-24, -5.4142, -4.4142), end=(-24, -4, -5)),
    ]
    profile_wire = scad.make_wire_from_edges_rwire(edges=profile_edges)
    profile = scad.make_face_from_wire_rface(wire=profile_wire, normal=(1, 0, 0))

    # ---- feature: planar-spline-duct-rail (path, profile=geometry) ----
    rail = scad.make_spline_redge(
        control_points=[[-24, 0, 0], [-14, 8, 0], [-5, 8, 0], [5, -8, 0], [14, -8, 0], [24, 0, 0]],
        degree=3, knots=[0.0, 0.33, 0.66, 1.0], multiplicities=[4, 1, 1, 4],
    )
    rail_wire = scad.make_wire_from_edges_rwire(edges=[rail])

    # ---- feature: swept-rounded-duct (build, profile=geometry) ----
    result = scad.sweep_rsolid(profile=profile, path=rail_wire, is_frenet=True)

    # ---- feature: softened-inlet-rim (modify, profile=geometry) ----
    inlet_edges = ql.edges().where(ql.and_(
        ql.prop('geom.length', '>=', 7.9),
        ql.prop('geom.length', '<=', 8.1),
        ql.prop('geom.center.z', '>=', 4.9),
        ql.prop('geom.center.z', '<=', 5.1),
    )).exactly(2)
    result = scad.fillet_rsolid(solid=result, edges=inlet_edges, radius=0.7)
    return scad.make_part_rpart(part_id='part', body=result, name='Planar spline swept duct')


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
