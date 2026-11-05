from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    ql = scad.ql

    # ---- feature: ergonomic-spline-grip-profile (build, profile=geometry) ----
    edge_0 = scad.make_spline_redge(control_points=[[-30.0, -12.0, 0.0], [-31.0, 0.0, 0.0], [-28.0, 13.0, 0.0]], degree=2, knots=[0.0, 1.0], multiplicities=[3, 3])
    edge_1 = scad.make_spline_redge(control_points=[[-28.0, 13.0, 0.0], [0.0, 22.0, 0.0], [28.0, 13.0, 0.0]], degree=2, knots=[0.0, 1.0], multiplicities=[3, 3])
    edge_2 = scad.make_spline_redge(control_points=[[28.0, 13.0, 0.0], [31.0, 0.0, 0.0], [30.0, -12.0, 0.0]], degree=2, knots=[0.0, 1.0], multiplicities=[3, 3])
    edge_3 = scad.make_spline_redge(control_points=[[30.0, -12.0, 0.0], [0.0, -23.0, 0.0], [-30.0, -12.0, 0.0]], degree=2, knots=[0.0, 1.0], multiplicities=[3, 3])
    profile = scad.make_wire_from_edges_rwire(edges=[edge_0, edge_1, edge_2, edge_3])

    # ---- feature: straight-extruded-grip-body (build, profile=geometry) ----
    result = scad.extrude_rsolid(profile=profile, direction=(0.0, 0.0, 1.0), distance=36.0)

    # ---- feature: corner-seam-chamfers (modify, profile=geometry) ----
    seam_edges = ql.edges().where(ql.and_(
        ql.prop("geom.length", ">=", 35.9),
        ql.prop("geom.length", "<=", 36.1),
        ql.prop("geom.center.z", ">=", 17.9),
        ql.prop("geom.center.z", "<=", 18.1),
    )).exactly(4)
    result = scad.chamfer_rsolid(solid=result, edges=seam_edges, distance=0.8)

    return scad.make_part_rpart(part_id='part', body=result, name='Spline-sided ergonomic grip')

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
