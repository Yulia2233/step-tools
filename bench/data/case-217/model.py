from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: planar-s-rail (build, profile=geometry) ----
    rail_edge = scad.make_spline_redge(control_points=[[-34.0, 0.0, 0.0], [-24.0, 19.0, 0.0], [-12.0, 23.0, 0.0], [12.0, -23.0, 0.0], [24.0, -19.0, 0.0], [34.0, 0.0, 0.0]], degree=3, knots=[0.0, 1.0, 2.0, 3.0], multiplicities=[4, 1, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    profile = scad.make_circle_rface(center=(-34.0, 0.0, 0.0), radius=5.0, normal=(1.0, 0.0, 0.0))
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: end-rim-chamfers (modify, profile=geometry) ----
    rim_edges = scad.ql.edges().where(scad.ql.and_(
        scad.ql.prop('geom.length', '>=', 31.0),
        scad.ql.prop('geom.length', '<=', 32.0),
    )).exactly(2)
    result = scad.chamfer_rsolid(solid=result, edges=rim_edges, distance=0.5)

    return scad.make_part_rpart(part_id='part', body=result, name='Planar spline swept handle')

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
